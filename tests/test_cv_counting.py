"""T9 CV counting: event aggregation → counts.csv (timestamp,class,in,out) without ultralytics/torch, graceful
message when the CV libraries are missing, and counts.csv flowing through the `cv` connector into the warehouse."""
import csv
import importlib.util
import json
import subprocess
import sys
from datetime import datetime

import pytest


@pytest.fixture(scope="module")
def count(kit_root):
    spec = importlib.util.spec_from_file_location("cv_count", kit_root / "scenarios/cv_counting/count.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# tiny synthetic crossing log: 2 cars in + 1 motorcycle out in minute 0, 1 car out in minute 2, a bus (filtered out)
EVENTS = [(3.0, "car", "in"), (10.5, "car", "in"), (59.9, "motorcycle", "out"), (130.0, "car", "out"), (20.0, "bus", "in")]


def test_parsers(count):
    import argparse
    assert count.parse_every("60s") == 60 and count.parse_every("15m") == 900 and count.parse_every("1h") == 3600 and count.parse_every("90") == 90
    with pytest.raises(argparse.ArgumentTypeError):
        count.parse_every("soon")
    assert count.parse_line("0,360,1280,360") == (0, 360, 1280, 360)
    for bad in ("1,2,3", "a,b,c,d", "5,5,5,5"):
        with pytest.raises(argparse.ArgumentTypeError):
            count.parse_line(bad)


def test_aggregate_zero_fills_and_filters(count):
    rows = count.aggregate(EVENTS, 60, ["car", "motorcycle"], duration=240)
    assert len(rows) == 4 * 2  # 4 one-minute bins × 2 classes, bus filtered out
    by = {(r["timestamp"], r["class"]): (r["in"], r["out"]) for r in rows}
    assert by[("00:00:00", "car")] == (2, 0)
    assert by[("00:00:00", "motorcycle")] == (0, 1)
    assert by[("00:02:00", "car")] == (0, 1)
    assert by[("00:03:00", "car")] == (0, 0)
    assert sum(r["in"] + r["out"] for r in rows) == 4


def test_aggregate_wall_clock_and_validation(count):
    rows = count.aggregate(EVENTS[:2], 60, None, start=datetime(2026, 11, 20, 7, 0, 0))
    assert rows == [{"timestamp": "2026-11-20T07:00:00", "class": "car", "in": 2, "out": 0}]
    assert count.aggregate([], 60) == []
    with pytest.raises(ValueError):
        count.aggregate([(1.0, "car", "sideways")], 60)
    with pytest.raises(ValueError):
        count.aggregate([(-1.0, "car", "in")], 60)


def test_cli_events_to_counts_csv(kit_root, tmp_path):
    ev = tmp_path / "events.csv"
    with open(ev, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t", "class", "direction"])
        w.writerows(EVENTS)
    out = tmp_path / "counts.csv"
    r = subprocess.run([sys.executable, str(kit_root / "scenarios/cv_counting/count.py"), "--events", str(ev), "--out", str(out),
                        "--every", "1m", "--classes", "car,motorcycle", "--start", "2026-11-20T07:00:00", "--license", "synthetic"],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    with open(out, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0]) == ["timestamp", "class", "in", "out"]
    assert {(x["timestamp"], x["class"], x["in"], x["out"]) for x in rows} >= {("2026-11-20T07:00:00", "car", "2", "0"), ("2026-11-20T07:02:00", "car", "0", "1")}
    meta = json.loads((tmp_path / "counts.csv.meta.json").read_text(encoding="utf-8"))
    assert meta["events"] == 5 and meta["license"] == "synthetic" and meta["every_s"] == 60


def test_cli_video_without_cv_libs_is_graceful(kit_root, tmp_path, count):
    if not count.missing_deps():
        pytest.skip("ultralytics + supervision installed — real video path not exercised here (needs a sample video)")
    fake = tmp_path / "cam.mp4"
    fake.write_bytes(b"\x00")
    r = subprocess.run([sys.executable, str(kit_root / "scenarios/cv_counting/count.py"), "--video", str(fake), "--out", str(tmp_path / "c.csv")],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 2
    assert "pip install ultralytics supervision" in r.stderr and "Traceback" not in r.stderr
    assert not (tmp_path / "c.csv").exists()


def test_counts_csv_through_cv_connector(count, tmp_path):
    from vlkit.de.flow import run_flow
    from vlkit.de.sources import Source
    from vlkit.de.warehouse import Warehouse
    out = tmp_path / "counts.csv"
    events = [(t * 7.0, ("car", "motorcycle")[t % 2], ("in", "out")[t % 3 == 0]) for t in range(120)]
    count.write_counts(count.aggregate(events, 60, ["car", "motorcycle"], start=datetime(2026, 11, 20, 7, 0)), out)
    wh = Warehouse(tmp_path / "wh.duckdb", lake=tmp_path / "lake")
    try:
        s = run_flow("cam", [Source("cam1", "cv", str(out))], out_root=tmp_path / "out", wh=wh)
        assert s["bronze"] == ["bronze.cam__cam1"]
        n = wh.sql('SELECT SUM("in") + SUM("out") AS n FROM silver.cam__cam1')
        assert int(n["n"].iloc[0]) == 120
    finally:
        wh.close()


def test_video_path_with_real_supervision_and_fake_detector(count, tmp_path, monkeypatch):
    """Runs the real supervision VideoInfo / frame generator / LineZone (+ whichever ByteTrack is installed) on a
    synthetic clip; only YOLO is replaced by a threshold detector. Skipped unless supervision + PyAV are installed."""
    sv = pytest.importorskip("supervision")
    av = pytest.importorskip("av")
    import types

    import numpy as np
    w, h, fps = 320, 240, 10
    clip = tmp_path / "syn.mp4"
    c = av.open(str(clip), "w")
    st = c.add_stream("mpeg4", rate=fps)
    st.width, st.height, st.pix_fmt = w, h, "yuv420p"
    for f in range(100):  # one box moving down across y=120 at ~5 s
        img = np.zeros((h, w, 3), np.uint8)
        y = int(10 + f * 2.2)
        img[y:y + 30, 140:180] = 255
        for p in st.encode(av.VideoFrame.from_ndarray(img, format="rgb24")):
            c.mux(p)
    for p in st.encode():
        c.mux(p)
    c.close()

    def detect(frame):
        ys = np.nonzero((frame[:, 140:180, 0] > 128).any(axis=1))[0]
        return np.array([[140, ys.min(), 180, ys.max()]], float) if len(ys) else np.zeros((0, 4))

    class Res:
        def __init__(self, frame, track):
            self.xyxy, self.track = detect(frame), track

    class YOLO:
        names = {0: "person", 2: "car"}

        def __init__(self, path):
            pass

        def __call__(self, frame, **kw):
            return [Res(frame, False)]

        def track(self, frame, **kw):
            return [Res(frame, True)]

    monkeypatch.setitem(sys.modules, "ultralytics", types.SimpleNamespace(YOLO=YOLO))
    monkeypatch.setattr(sv.Detections, "from_ultralytics", classmethod(lambda cls, r: sv.Detections(
        xyxy=r.xyxy, confidence=np.full(len(r.xyxy), 0.9), class_id=np.full(len(r.xyxy), 2),
        tracker_id=np.ones(len(r.xyxy), int) if r.track else None)))
    events, meta = count.video_events(clip, (0, 120, 320, 120), ["car"], 2, "fake.pt", 0.3, progress=False)
    assert [(cls, d) for _, cls, d in events] == [("car", "out")]
    assert 4.0 <= events[0][0] <= 6.0 and meta["fps"] == fps and meta["line"] == [0, 120, 320, 120]

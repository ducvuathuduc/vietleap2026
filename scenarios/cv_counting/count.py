#!/usr/bin/env python3
"""From observation to data — count objects crossing a line in a video → counts.csv (timestamp,class,in,out).

Detection: ultralytics YOLOv8n (CPU is fine) · Tracking: ByteTrack (supervision / Roboflow trackers / ultralytics built-in,
whichever is installed) · Counting: supervision LineZone.

    python scenarios/cv_counting/count.py --video cam.mp4 --out counts.csv \
        --line 0,360,1280,360 --classes car,motorcycle,bus,truck,person --every 60s --stride 3 \
        --start 2026-11-20T07:00:00 --license "CC BY 4.0, <url>"

    # no video / no ultralytics: aggregate crossing events you already have (or a synthetic test file)
    python scenarios/cv_counting/count.py --events events.csv --out counts.csv --every 60s
    #   events.csv columns: t (seconds from video start), class, direction (in|out)

Optional deps (not in requirements.txt — torch is large):  pip install ultralytics supervision
The YOLO weights (yolov8n.pt, ~6 MB) download on first use; pre-download before the contest.
Privacy: only counts are written — no frames, crops or faces are stored.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_CLASSES = "car,motorcycle,bus,truck,bicycle,person"
INSTALL_HINT = (
    "Thiếu thư viện thị giác máy tính: {missing}.\n"
    "Cài (một lần, cần mạng, ~1 GB vì có PyTorch):  pip install ultralytics supervision\n"
    "Không cài được? Dùng --events <file.csv> (cột t,class,direction) để tổng hợp sự kiện đếm có sẵn,\n"
    "hoặc nạp thẳng counts.csv vào pipeline: python de.py file counts.csv --serve"
)


# ----------------------------------------------------------------------------- pure helpers (tested)

def parse_every(s: str) -> int:
    """'60s' / '1m' / '15min' / '1h' / '90' → seconds (> 0)."""
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(s|sec|m|min|h)?\s*", str(s).lower())
    if not m:
        raise argparse.ArgumentTypeError(f"--every không hợp lệ: {s!r} (vd. 60s, 15m, 1h)")
    v = float(m.group(1)) * {"s": 1, "sec": 1, None: 1, "m": 60, "min": 60, "h": 3600}[m.group(2)]
    if v <= 0:
        raise argparse.ArgumentTypeError("--every phải > 0")
    return int(round(v))


def parse_line(s: str) -> tuple[int, int, int, int]:
    parts = [p.strip() for p in str(s).split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("--line cần 4 số: x1,y1,x2,y2 (pixel)")
    try:
        x1, y1, x2, y2 = (int(float(p)) for p in parts)
    except ValueError:
        raise argparse.ArgumentTypeError("--line cần 4 số: x1,y1,x2,y2 (pixel)")
    if (x1, y1) == (x2, y2):
        raise argparse.ArgumentTypeError("--line: hai điểm phải khác nhau")
    return x1, y1, x2, y2


def bin_label(t: float, every: int, start: datetime | None) -> str:
    """Start of the time bin containing t seconds: ISO datetime if --start is given, else elapsed HH:MM:SS."""
    b = int(t // every) * every
    if start is not None:
        return (start + timedelta(seconds=b)).isoformat(timespec="seconds")
    return f"{b // 3600:02d}:{b % 3600 // 60:02d}:{b % 60:02d}"


def aggregate(events, every: int, classes: list[str] | None = None, duration: float | None = None,
              start: datetime | None = None) -> list[dict]:
    """Crossing events (t_seconds, class, 'in'|'out') → one row per time bin × class with zero-filled counts.

    Bins cover [0, duration) when the video length is known, else up to the last event. Unknown directions and
    negative times are rejected (ValueError) rather than silently dropped."""
    counts: dict[tuple[int, str], list[int]] = defaultdict(lambda: [0, 0])
    seen_cls: list[str] = list(classes or [])
    last_t = 0.0
    for t, cls, direction in events:
        t = float(t)
        if t < 0 or not math.isfinite(t):
            raise ValueError(f"thời điểm không hợp lệ: {t}")
        d = str(direction).strip().lower()
        if d not in ("in", "out"):
            raise ValueError(f"direction phải là in/out, nhận {direction!r}")
        cls = str(cls).strip()
        if classes and cls not in classes:
            continue
        if cls not in seen_cls:
            seen_cls.append(cls)
        counts[(int(t // every), cls)][0 if d == "in" else 1] += 1
        last_t = max(last_t, t)
    span = duration if duration and duration > 0 else (last_t + 1e-9 if counts else 0)
    n_bins = max(1, math.ceil(span / every)) if (counts or duration) else 0
    rows = []
    for b in range(n_bins):
        for cls in seen_cls:
            i, o = counts.get((b, cls), [0, 0])
            rows.append({"timestamp": bin_label(b * every, every, start), "class": cls, "in": i, "out": o})
    return rows


def write_counts(rows: list[dict], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["timestamp", "class", "in", "out"])
        w.writeheader()
        w.writerows(rows)


def read_events(path: Path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        need = {"t", "class", "direction"}
        if not r.fieldnames or not need <= {c.strip() for c in r.fieldnames}:
            raise SystemExit(f"{path}: cần các cột {sorted(need)}, có {r.fieldnames}")
        for row in r:
            yield float(row["t"]), row["class"], row["direction"]


# ----------------------------------------------------------------------------- video → events (ultralytics + supervision)

def missing_deps() -> list[str]:
    import importlib.util
    return [m for m in ("ultralytics", "supervision") if importlib.util.find_spec(m) is None]


def make_tracker(sv, fps: float):
    """ByteTrack, wherever this install has it. supervision < 0.27 ships `sv.ByteTrack`; newer releases moved it to
    Roboflow `trackers` (`ByteTrackTracker`); otherwise ultralytics' built-in ByteTrack (`model.track`) is used.
    Returns (name, update_fn or None) — None means "let ultralytics track"."""
    if hasattr(sv, "ByteTrack"):
        t = sv.ByteTrack(frame_rate=max(1, round(fps)))
        return "supervision.ByteTrack", t.update_with_detections
    try:
        from trackers import ByteTrackTracker
        t = ByteTrackTracker(frame_rate=max(1.0, float(fps)))
        return "trackers.ByteTrackTracker", t.update
    except ImportError:
        return "ultralytics ByteTrack (bytetrack.yaml)", None


def video_events(video: Path, line, classes: list[str], stride: int, model_path: str, conf: float, progress: bool = True):
    """(t_seconds, class, direction) for every tracked object crossing the line, plus video/run metadata."""
    import supervision as sv
    from ultralytics import YOLO

    info = sv.VideoInfo.from_video_path(str(video))
    fps = float(info.fps or 25)
    model = YOLO(model_path)
    names = {int(k): v for k, v in model.names.items()}
    ids = [k for k, v in names.items() if v in classes]
    unknown = [c for c in classes if c not in names.values()]
    if unknown:
        print(f"[cảnh báo] lớp không có trong model: {unknown}; có: {sorted(names.values())}", file=sys.stderr)
    if line is None:  # default: horizontal line across the middle
        line = (0, info.height // 2, info.width, info.height // 2)
    zone = sv.LineZone(start=sv.Point(line[0], line[1]), end=sv.Point(line[2], line[3]))
    tracker_name, update = make_tracker(sv, fps / stride)
    events = []
    total = info.total_frames or 0
    for k, frame in enumerate(sv.get_video_frames_generator(str(video), stride=stride)):
        frame_idx = k * stride
        if update is not None:
            res = model(frame, conf=conf, classes=ids or None, verbose=False)[0]
            det = update(sv.Detections.from_ultralytics(res))
        else:
            res = model.track(frame, persist=True, tracker="bytetrack.yaml", conf=conf, classes=ids or None, verbose=False)[0]
            det = sv.Detections.from_ultralytics(res)
        if len(det) == 0 or det.tracker_id is None:
            continue
        crossed_in, crossed_out = zone.trigger(det)
        t = frame_idx / fps
        for j in range(len(det)):
            cls = names.get(int(det.class_id[j]), str(det.class_id[j])) if det.class_id is not None else "object"
            if crossed_in[j]:
                events.append((t, cls, "in"))
            if crossed_out[j]:
                events.append((t, cls, "out"))
        if progress and total and k % 200 == 0:
            print(f"  khung {frame_idx}/{total} · {len(events)} lượt qua vạch", file=sys.stderr)
    meta = {"fps": fps, "width": info.width, "height": info.height, "total_frames": total,
            "duration_s": (total / fps) if total else None, "line": list(line), "tracker": tracker_name}
    return events, meta


# ----------------------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--video", type=Path, help="video file (mp4/avi/mov/mkv)")
    src.add_argument("--events", type=Path, help="CSV of crossing events: t (s), class, direction (in|out)")
    ap.add_argument("--out", type=Path, default=Path("counts.csv"), help="output counts.csv (default ./counts.csv)")
    ap.add_argument("--line", type=parse_line, default=None, help="counting line x1,y1,x2,y2 in pixels (default: horizontal middle)")
    ap.add_argument("--classes", default=DEFAULT_CLASSES, help=f"COCO class names (default {DEFAULT_CLASSES})")
    ap.add_argument("--every", type=parse_every, default=60, help="bin size: 60s, 15m, 1h (default 60s)")
    ap.add_argument("--stride", type=int, default=3, help="process every n-th frame (default 3; higher = faster, may miss fast objects)")
    ap.add_argument("--model", default="yolov8n.pt", help="YOLO weights (default yolov8n.pt, auto-download ~6 MB)")
    ap.add_argument("--conf", type=float, default=0.3, help="detection confidence threshold (default 0.3)")
    ap.add_argument("--start", type=datetime.fromisoformat, default=None,
                    help="wall-clock time of the first frame, e.g. 2026-11-20T07:00:00 (else timestamps are elapsed HH:MM:SS)")
    ap.add_argument("--duration", type=float, default=None, help="--events mode: video length in seconds (zero-fills trailing bins)")
    ap.add_argument("--license", default="", help="licence/source note of the video, saved in <out>.meta.json")
    a = ap.parse_args(argv)
    if a.stride < 1:
        ap.error("--stride phải ≥ 1")
    classes = [c.strip() for c in a.classes.split(",") if c.strip()]

    if a.video is not None:
        if not a.video.exists():
            print(f"Không tìm thấy video: {a.video}", file=sys.stderr)
            return 1
        miss = missing_deps()
        if miss:
            print(INSTALL_HINT.format(missing=", ".join(miss)), file=sys.stderr)
            return 2
        events, vmeta = video_events(a.video, a.line, classes, a.stride, a.model, a.conf)
        duration = vmeta["duration_s"]
        source = {"video": a.video.name, **vmeta, "model": a.model, "counter": "supervision.LineZone",
                  "stride": a.stride, "conf": a.conf}
    else:
        if not a.events.exists():
            print(f"Không tìm thấy file sự kiện: {a.events}", file=sys.stderr)
            return 1
        events = list(read_events(a.events))
        duration = a.duration
        source = {"events": a.events.name}

    rows = aggregate(events, a.every, classes, duration=duration, start=a.start)
    write_counts(rows, a.out)
    meta = {**source, "classes": classes, "every_s": a.every, "start": a.start.isoformat() if a.start else None,
            "events": len(events), "rows": len(rows), "license": a.license,
            "created": datetime.now().astimezone().isoformat(timespec="seconds")}
    Path(str(a.out) + ".meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    tot_in = sum(r["in"] for r in rows)
    tot_out = sum(r["out"] for r in rows)
    print(f"{a.out}: {len(rows)} dòng · {len(events)} lượt qua vạch (vào {tot_in}, ra {tot_out})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

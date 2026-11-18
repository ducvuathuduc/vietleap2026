"""Tests for Gap #6: time-watermark / cursor incremental ingestion in connectors & flow."""
import json

import httpx
import pandas as pd


def test_ingest_api_watermark_injects_param_and_advances(tmp_path):
    from vlkit.de.connectors import ingest_api, read_watermark, write_watermark
    from vlkit.de.sources import Source

    wm_file = tmp_path / "wm.json"
    seen_params = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_params.append(dict(request.url.params))
        since = int(request.url.params.get("since", "2020"))
        rows = [{"year": y, "val": y * 10} for y in range(2021, 2025) if y > since]
        return httpx.Response(200, json={"items": rows})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    src = Source(
        name="macro",
        kind="api",
        uri="https://example.org/api/series",
        options={
            "records_path": "items",
            "watermark_col": "year",
            "watermark_param": "since",
            "watermark_file": str(wm_file),
            "cache": False,
        },
    )

    r1 = ingest_api(src, client=client)
    assert len(r1.frames["macro"]) == 4
    assert "since" not in seen_params[0]
    write_watermark(wm_file, "2024", "year", "2026-11-18T10:00:00+07:00")
    assert read_watermark(wm_file) == "2024"

    r2 = ingest_api(src, client=client)
    assert seen_params[1]["since"] == "2024"
    assert r2.frames["macro"].empty


def test_run_flow_incremental_with_watermark_filters_new_rows(tmp_path):
    from vlkit.de.flow import run_flow
    from vlkit.de.sources import Source
    from vlkit.de.warehouse import Warehouse

    csv_path = tmp_path / "series.csv"
    pd.DataFrame([
        {"period": "2024-01", "val": 1.0},
        {"period": "2024-02", "val": 2.0},
    ]).to_csv(csv_path, index=False)

    wh = Warehouse(tmp_path / "wh.duckdb", lake=tmp_path / "lake")
    try:
        src = Source("ts", "file", str(csv_path), options={"watermark_col": "period"})
        s1 = run_flow("wm_demo", [src], out_root=tmp_path / "out", wh=wh, mode="incremental")
        assert s1["load"]["inserted"] == 2
        wm_file = tmp_path / "lake" / "_watermarks" / "wm_demo__ts.json"
        assert json.loads(wm_file.read_text(encoding="utf-8"))["watermark"] == "2024-02"

        # Re-run unchanged file -> 0 inserted, reuses existing bronze table
        s2 = run_flow("wm_demo", [src], out_root=tmp_path / "out", wh=wh, mode="incremental")
        assert s2["load"]["inserted"] == 0
        assert s2["steps"][0]["watermark"]["from"] == "2024-02"

        # Add 2024-03 upstream -> only 1 new row inserted
        pd.DataFrame([
            {"period": "2024-01", "val": 1.0},
            {"period": "2024-02", "val": 2.0},
            {"period": "2024-03", "val": 3.0},
        ]).to_csv(csv_path, index=False)
        s3 = run_flow("wm_demo", [src], out_root=tmp_path / "out", wh=wh, mode="incremental")
        assert s3["load"]["inserted"] == 1
        assert json.loads(wm_file.read_text(encoding="utf-8"))["watermark"] == "2024-03"
        assert wh.sql("SELECT count(*) AS n FROM bronze.wm_demo__ts")["n"][0] == 3
    finally:
        wh.close()

"""TinyFish agent reader: saved run payload -> silver rows, plus the per-run budget/time guard."""
import json
from pathlib import Path

from vlkit.ratewatch.ingest.readers.tinyfish import rows_from_payload, run_agent_queue

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ratewatch" / "tinyfish"
RUN = "rw-20261120T1400"
SEEN = "2026-11-20T14:00:00+07:00"
URL = "https://hdbank.com.vn/vi/ca-nhan/tiet-kiem/lai-suat"


def payload() -> dict:
    return json.loads((FIXTURES / "HDBank_20261120.json").read_text(encoding="utf-8"))


def rows_for(payload_dict, **kw):
    params = {"bank_code": "HDB", "source_url": URL, "run_id": RUN, "observed_at": SEEN,
              "raw_sha256": "tf-sha"}
    params.update(kw)
    return rows_from_payload(payload_dict, **params)


def test_agent_payload_becomes_rows_with_page_effective_date():
    rows = rows_for(payload())
    rates = {(r["channel"], r["term_months"]): r["rate_pct"] for r in rows}
    assert rates[("counter", 1)] == 3.5
    assert rates[("online", 1)] == 4.2
    assert rates[("counter", 6)] == 4.9
    assert rates[("online", 24)] == 5.0
    assert {r["sheet_date"].isoformat() for r in rows} == {"2026-10-19"}
    assert all(r["reader"] == "tinyfish" and r["tier"] == "" for r in rows)
    assert all(r["source_url"] == URL and r["raw_sha256"] == "tf-sha" for r in rows)


def test_two_printed_products_do_not_become_two_rows_with_the_same_key():
    rows = rows_for(payload())
    counter_12 = [r for r in rows if r["channel"] == "counter" and r["term_months"] == 12]
    assert len(counter_12) == 1
    assert counter_12[0]["rate_pct"] == 5.2  # the plain board rate, not the "loại 1" promotional quote


def test_standard_board_wins_over_a_savings_plan_product():
    payload = {"status": "COMPLETED", "result": {"rates": [
        {"channel": "counter", "term_months": 3, "rate_pct": 2.95,
         "product_name": "Gom lộc phát tài tại quầy - KHCN"},
        {"channel": "counter", "term_months": 3, "rate_pct": 4.2,
         "product_name": "Lãi suất Tiết kiệm/ tiền gửi có kỳ hạn VND - KHCN"},
    ]}}
    assert [(r["term_months"], r["rate_pct"]) for r in rows_for(payload)] == [(3, 4.2)]


def test_impossible_values_are_dropped():
    bad = {"result": {"page_effective_date": "", "rates": [
        {"channel": "counter", "term_months": 1, "rate_pct": 0},
        {"channel": "counter", "term_months": 2, "rate_pct": 30},
        {"channel": "counter", "term_months": -3, "rate_pct": 4.0},
        {"channel": "corporate", "term_months": 6, "rate_pct": 4.0},
        {"channel": "online", "term_months": 6, "rate_pct": 5.0},
    ]}}
    rows = rows_for(bad)
    assert [(r["channel"], r["term_months"], r["rate_pct"]) for r in rows] == [("online", 6, 5.0)]
    assert rows[0]["sheet_date"] is None


def test_failed_or_empty_run_yields_no_rows():
    assert rows_for({"status": "FAILED", "result": {"rates": [{"channel": "counter", "term_months": 1, "rate_pct": 4.0}]}}) == []
    assert rows_for({"status": "COMPLETED", "result": {"rates": []}}) == []


def test_cache_hit_is_reported_as_free(monkeypatch):
    from vlkit.de import tinyfish as tf
    from vlkit.ratewatch.ingest.readers.tinyfish import run_bank_agent

    monkeypatch.setattr(tf, "run_goal", lambda *a, **kw: tf.TinyFishOutcome(
        status="ok", source="u", run_id="r1", records=[{"rates": []}], steps=12, cost_usd=0.192,
        message="[tinyfish] cache hit for u (no run, no spend)"))
    outcome = run_bank_agent({"code": "VCB", "name_vi": "Vietcombank", "rate_page": "https://example.test/"})
    assert outcome["cost_usd"] == 0.0 and outcome["cached"] is True


def test_budget_and_time_cap_stop_the_queue_before_spending_more():
    calls = []

    def fake_run(bank, deadline_s):
        calls.append((bank["code"], deadline_s))
        return {"status": "ok", "records": [], "cost_usd": 0.6, "steps": 10, "run_id": "r1", "message": ""}

    banks = [{"code": c} for c in ("VCB", "BIDV", "CTG", "AGB")]
    outcomes, log = run_agent_queue(banks, run_fn=fake_run, max_usd=1.0, deadline_s=360.0, max_seconds=600.0,
                                    max_workers=1, clock=lambda: 0.0)
    assert [c[0] for c in calls] == ["VCB", "BIDV"]
    assert log["stopped"] == "budget"
    assert log["usd"] == 1.2
    assert set(outcomes) == {"VCB", "BIDV"}


def test_time_cap_stops_the_queue():
    calls = []

    def fake_run(bank, deadline_s):
        calls.append(bank["code"])
        return {"status": "ok", "records": [], "cost_usd": 0.1, "steps": 2, "run_id": "r1", "message": ""}

    now = iter([0.0, 700.0])
    outcomes, log = run_agent_queue([{"code": "VCB"}, {"code": "BIDV"}], run_fn=fake_run, max_usd=5.0,
                                    deadline_s=360.0, max_seconds=60.0, max_workers=1, clock=lambda: next(now))
    assert calls == [] and outcomes == {}
    assert log["stopped"] == "time"

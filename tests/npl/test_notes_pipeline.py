"""Quality gates, the harvest of one link list and one whole incremental notes run (no network, no PDFs)."""

import json

import pandas as pd
import pytest

from vlkit.npl.ingest import notes_gates, notes_runner, notes_vision
from vlkit.npl.ingest.extra_landing import Fetcher, write_silver
from vlkit.npl.ingest.files import atomic

LOANS = """BÁO CÁO TÀI CHÍNH HỢP NHẤT
Đơn vị tính: Triệu VND
Cho vay khách hàng      130     1.000.000   900.000
"""
GROUPS = """Thuyết minh
Đơn vị tính: Triệu VND
Nợ đủ tiêu chuẩn        980.000   950.000
Nợ cần chú ý             10.000     9.000
Nợ dưới tiêu chuẩn        4.000     3.000
Nợ nghi ngờ               3.000     2.000
Nợ có khả năng mất vốn    3.000     1.000
"""
MOVEMENT = """Thuyết minh
Đơn vị tính: Triệu VND
Số dư đầu kỳ            100.000
Số trích lập trong kỳ    12.000
Số sử dụng trong kỳ       8.000
Số dư cuối kỳ           104.000
"""


GROUPS_TABLE = [["Nợ đủ tiêu chuẩn", "980.000", "950.000"],
                ["Nợ cần chú ý", "10.000", "9.000"],
                ["Nợ dưới tiêu chuẩn", "4.000", "3.000"],
                ["Nợ nghi ngờ", "3.000", "2.000"],
                ["Nợ có khả năng mất vốn", "3.000", "1.000"]]
LOANS_TABLE = [["Chỉ tiêu", "Mã số", "Năm nay", "Năm trước"],
               ["Cho vay khách hàng", "130", "1.000.000", "900.000"]]


def fixtures(content):
    """(page texts, table grid) of a statement whose provision charge is 12bn in Q1 and 22bn in Q2 (YTD)."""
    charge, used = ("22.000", "18.000") if b"q2" in content else ("12.000", "8.000")
    movement = MOVEMENT.replace("12.000", charge).replace("8.000", used)
    movement_table = [["Số dư đầu kỳ", "100.000"], ["Số trích lập trong kỳ", charge],
                      ["Số sử dụng trong kỳ", used], ["Số dư cuối kỳ", "104.000"]]
    return [LOANS, GROUPS, movement], [(1, LOANS_TABLE), (2, GROUPS_TABLE), (3, movement_table)]



class Response:
    def __init__(self, status=200, content=b"ok"):
        self.status_code = status
        self.content = content
        self.text = content.decode()

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class Client:
    def __init__(self, pages):
        self.pages = pages
        self.requested = []

    def get(self, url):
        self.requested.append(url)
        if url.endswith("/robots.txt"):
            return Response(content=b"User-agent: *\nAllow: /\n")
        return Response(content=self.pages[url])


def fake_fetcher(pages):
    client = Client(pages)
    return Fetcher(lake=None, run_id="notes-test", client=client, sleep=lambda seconds: None), client


def values(**overrides):
    base = {"loans_customer": 1000.0, "group_1_current": 900.0, "group_2_watch": 50.0,
            "group_3_substandard": 20.0, "group_4_doubtful": 20.0, "group_5_loss": 10.0,
            "provision_opening": 100.0, "provision_charge": 50.0, "provision_used_writeoff": 20.0,
            "provision_closing": 130.0}
    base.update(overrides)
    return base


def test_the_three_gates_pass_on_a_consistent_statement():
    gates, summary = notes_gates.run_gates(pd.DataFrame([
        {"bank": "VCB", "period": "2025Q2", "field": field, "basis": "point", "value_vnd_bn": value}
        for field, value in values().items()]), vendor={("VCB", "2025Q2"): 5.0})
    assert list(gates["status"]) == ["pass", "pass", "pass"]
    assert summary == {"gates": 3, "pass": 3, "fail": 0, "skipped": 0}


def test_a_group_total_that_does_not_reach_the_loan_total_fails_the_first_gate():
    gate = notes_gates.groups_gate(values(group_2_watch=70.0))          # groups sum 1,020 vs loans 1,000
    assert gate["status"] == "fail" and gate["value"] == pytest.approx(0.02)


def test_a_roll_forward_that_does_not_close_fails_the_second_gate():
    gate = notes_gates.rollforward_gate(values(provision_closing=120.0))   # 100 + 50 - 20 = 130, not 120
    assert gate["status"] == "fail" and gate["threshold"] == 0.01


def test_our_npl_ratio_more_than_ten_basis_points_from_the_vendor_fails_the_third_gate():
    assert notes_gates.npl_gate(values(), 5.0)["status"] == "pass"          # ours 5.0%, vendor 5.0%
    fail = notes_gates.npl_gate(values(), 5.30)                            # 30 bp apart
    assert fail["status"] == "fail" and fail["value"] == pytest.approx(-30.0, abs=1e-6)


def test_a_gate_without_its_inputs_is_skipped_not_passed():
    gate = notes_gates.groups_gate({"loans_customer": 1000.0})
    assert gate["status"] == "skipped"
    roll = notes_gates.rollforward_gate({"provision_closing": 130.0})
    assert roll["status"] == "skipped"


class FakeVision:
    """Two models answering the same page with one reading each (the scan path of the runner)."""

    def __init__(self, payload_a, payload_b):
        self.payloads = {notes_vision.MODEL_A: payload_a, notes_vision.MODEL_B: payload_b}
        self.cost_usd = 0.0

    def read(self, png, prompt, model):
        return self.payloads[model]


def test_harvest_reads_a_text_layer_twice_grades_it_and_derives_quarterly_flows(tmp_path, monkeypatch):
    links = pd.DataFrame([
        {"bank": "VCB", "period": "2025Q1", "statement_type": "consolidated", "url": "https://x.test/q1.pdf",
         "found_by": "html", "found_at": "now"},
        {"bank": "VCB", "period": "2025Q2", "statement_type": "consolidated", "url": "https://x.test/q2.pdf",
         "found_by": "html", "found_at": "now"}])
    fetcher, client = fake_fetcher({"https://x.test/q1.pdf": b"%PDF-q1", "https://x.test/q2.pdf": b"%PDF-q2"})
    monkeypatch.setattr(notes_runner, "page_texts", lambda content: fixtures(content)[0])
    monkeypatch.setattr(notes_runner, "page_tables", lambda content: fixtures(content)[1])
    frame, gates, stats = notes_runner.harvest(tmp_path, links, fetcher, "notes-test", vision=object(),
                                               vendor={("VCB", "2025Q1"): 1.0, ("VCB", "2025Q2"): 1.0})
    assert stats["fetched"] == 2 and stats["read"] == 2
    loans = frame[(frame["period"] == "2025Q2") & (frame["field"] == "loans_customer")].iloc[0]
    assert loans["value_vnd_bn"] == 1000.0 and loans["grade"] == "verified" and loans["page"] == 1
    quarterly = frame[(frame["period"] == "2025Q2") & (frame["field"] == "provision_charge")
                      & (frame["basis"] == "quarterly")]
    assert quarterly["value_vnd_bn"].iloc[0] == 10.0
    assert set(gates["status"]) == {"pass"}
    assert (tmp_path / "bronze/notes/store").exists()            # the PDF is cached in bronze for the next run


def test_harvest_uses_two_vision_reads_when_the_pdf_is_a_scan(tmp_path, monkeypatch):
    links = pd.DataFrame([{"bank": "VCB", "period": "2025Q2", "statement_type": "consolidated",
                           "url": "https://x.test/scan.pdf", "found_by": "html", "found_at": "now"}])
    fetcher, _ = fake_fetcher({"https://x.test/scan.pdf": b"%PDF-scan"})
    monkeypatch.setattr(notes_runner, "page_texts", lambda content: [""])
    monkeypatch.setattr(notes_runner, "page_png", lambda content, page: b"png")
    vision = FakeVision({"values": {"loans_customer": 1000.0, "group_2_watch": 50.0}},
                        {"values": {"loans_customer": 1000.0, "group_2_watch": 50.0}})
    frame, _, stats = notes_runner.harvest(tmp_path, links, fetcher, "notes-test", vision=vision)
    graded = dict(zip(frame["field"], frame["grade"]))
    assert graded["loans_customer"] == "verified" and graded["group_2_watch"] == "verified"
    assert stats["fetched"] == 1


def test_a_scan_without_the_vision_reader_reports_the_gap_instead_of_rows(tmp_path, monkeypatch):
    links = pd.DataFrame([{"bank": "VCB", "period": "2025Q2", "statement_type": "consolidated",
                           "url": "https://x.test/scan.pdf", "found_by": "html", "found_at": "now"}])
    fetcher, _ = fake_fetcher({"https://x.test/scan.pdf": b"%PDF-scan"})
    monkeypatch.setattr(notes_runner, "page_texts", lambda content: [""])
    frame, gates, stats = notes_runner.harvest(tmp_path, links, fetcher, "notes-test", vision=None,
                                               use_vision=False)
    assert len(frame) == 0 and len(gates) == 0
    assert "no text layer" in json.dumps(stats["errors"])


def test_run_notes_writes_silver_gates_run_log_and_watermark_then_skips_the_same_bank_quarter(tmp_path, monkeypatch):
    write_silver(tmp_path, notes_runner.LINKS, pd.DataFrame([
        {"bank": "VCB", "period": "2025Q1", "statement_type": "consolidated", "url": "https://x.test/q1.pdf",
         "found_by": "html", "found_at": "now"},
        {"bank": "VCB", "period": "2025Q2", "statement_type": "consolidated", "url": "https://x.test/q2.pdf",
         "found_by": "html", "found_at": "now"}]))
    fetcher, client = fake_fetcher({"https://x.test/q1.pdf": b"%PDF-q1", "https://x.test/q2.pdf": b"%PDF-q2"})
    monkeypatch.setattr(notes_runner, "page_texts", lambda content: fixtures(content)[0])
    monkeypatch.setattr(notes_runner, "page_tables", lambda content: fixtures(content)[1])
    log = notes_runner.run_notes(lake=tmp_path, banks=["VCB"], periods=["2025Q1", "2025Q2"],
                                 fetcher=fetcher, vision=object(), use_vision=False)
    assert log["silver"]["rows"] > 0 and log["silver"]["verified_share"] == 1.0
    silver = pd.read_parquet(tmp_path / "silver/notes_bank_quarter.parquet")
    assert set(silver["bank"]) == {"VCB"} and set(silver["period"]) == {"2025Q1", "2025Q2"}
    assert list(silver.columns) == notes_runner.SILVER_COLUMNS
    gates = pd.read_csv(tmp_path / "silver/notes_gate.csv")
    status = dict(zip(gates["gate"], gates["status"]))
    assert status["groups_sum_to_loans"] == "pass" and status["provision_rollforward"] == "pass"
    assert status["npl_vs_vendor"] == "skipped"      # no vendor panel in this lake: skipped, never passed
    assert (tmp_path / "run_log" / f"{log['run_id']}.json").exists()
    marks = json.loads((tmp_path / "state/watermarks.json").read_text(encoding="utf-8"))
    assert marks["notes_bank_quarter"] == "2025Q2" and marks["notes_bank_last"] == {"VCB": "2025Q2"}
    fetched_before = len(client.requested)
    second = notes_runner.run_notes(lake=tmp_path, banks=["VCB"], periods=["2025Q1", "2025Q2"],
                                    fetcher=fetcher, vision=object(), use_vision=False)
    assert second["datasets"]["notes"]["skipped_done"] == 2 and len(client.requested) == fetched_before
    assert second["silver"]["rows"] == log["silver"]["rows"]


def test_an_empty_run_writes_no_silver_and_leaves_the_watermark_alone(tmp_path):
    fetcher, client = fake_fetcher({})
    log = notes_runner.run_notes(lake=tmp_path, banks=["ZZZ"], periods=["2025Q2"], fetcher=fetcher,
                                 vision=object(), use_vision=False)
    assert log["links"]["rows"] == 0 and log["silver"]["rows"] == 0
    assert not (tmp_path / "silver/notes_bank_quarter.parquet").exists()
    assert not (tmp_path / "state/watermarks.json").exists()
    assert client.requested == []                      # no invented page, no network


def test_merge_keeps_the_better_grade_when_a_bank_quarter_is_read_again():
    def row(grade, value):
        return {"bank": "VCB", "period": "2025Q2", "field": "loans_customer", "basis": "point",
                "value_vnd_bn": value, "page": 1, "source_url": "https://x.test/a.pdf", "reader": "text",
                "grade": grade, "raw_sha256": "sha"}
    merged = notes_runner.merge_silver(pd.DataFrame([row("verified", 100.0)]),
                                       pd.DataFrame([row("single", 101.0)]))
    assert len(merged) == 1 and merged.iloc[0]["value_vnd_bn"] == 100.0 and merged.iloc[0]["grade"] == "verified"


def test_coverage_reports_fields_and_verified_share_per_bank_quarter():
    frame = pd.DataFrame([
        {"bank": "VCB", "period": "2025Q2", "field": "loans_customer", "grade": "verified"},
        {"bank": "VCB", "period": "2025Q2", "field": "group_2_watch", "grade": "single"}])
    table = notes_runner.coverage(frame)
    assert table.iloc[0].to_dict() == {"bank": "VCB", "period": "2025Q2", "fields": 2, "verified_share": 0.5}

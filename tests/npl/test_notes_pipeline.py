"""Quality gates, the harvest of one link list and one whole incremental notes run (no network, no PDFs)."""

import json

import pandas as pd
import pytest

from vlkit.npl.ingest import notes_gates, notes_links, notes_runner, notes_vision
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
        {"bank": "VCB", "period": "2025Q2", "field": field, "basis": "point", "value_vnd_bn": value,
         "unit": "trieu"}
        for field, value in values().items()]), vendor={("VCB", "2025Q2"): 5.0})
    assert list(gates["status"]) == ["pass", "pass", "pass", "pass"]
    assert summary == {"gates": 4, "pass": 4, "fail": 0, "skipped": 0}


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
    """The scan path: a locator answer for the thumbnail prompt, one reading per model for the page prompts."""

    def __init__(self, payload_a, payload_b, located=(1,)):
        self.payloads = {notes_vision.MODEL_A: payload_a, notes_vision.MODEL_B: payload_b}
        self.located = list(located)
        self.cost_usd = 0.0
        self.calls = []

    def read(self, png, prompt, model, schema=None):
        self.calls.append(model)
        if "balance_sheet_pages" in prompt:
            return {"classification_pages": self.located, "provision_pages": [], "balance_sheet_pages": []}
        return self.payloads[model]


def test_harvest_reads_a_text_layer_twice_grades_it_and_derives_quarterly_flows(tmp_path, monkeypatch):
    links = pd.DataFrame([
        {"bank": "VCB", "period": "2025Q1", "statement_type": "consolidated", "url": "https://x.test/q1.pdf",
         "found_by": "html", "found_at": "now"},
        {"bank": "VCB", "period": "2025Q2", "statement_type": "consolidated", "url": "https://x.test/q2.pdf",
         "found_by": "html", "found_at": "now"}])
    fetcher, client = fake_fetcher({"https://x.test/q1.pdf": b"%PDF-q1", "https://x.test/q2.pdf": b"%PDF-q2"})
    monkeypatch.setattr(notes_runner, "fast_page_texts", lambda content: fixtures(content)[0])
    monkeypatch.setattr(notes_runner, "page_tables", lambda content, only=None: fixtures(content)[1])
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
    monkeypatch.setattr(notes_runner, "fast_page_texts", lambda content: ["", ""])
    monkeypatch.setattr(notes_runner, "render_strip", lambda content, pages, **kwargs: b"strip")
    monkeypatch.setattr(notes_runner, "render_pages", lambda content, pages, scale=2.0: {page: b"png" for page in pages})
    vision = FakeVision({"values": {"loans_customer": 1000.0, "group_2_watch": 50.0}},
                        {"values": {"loans_customer": 1000.0, "group_2_watch": 50.0}}, located=(2,))
    frame, _, stats = notes_runner.harvest(tmp_path, links, fetcher, "notes-test", vision=vision)
    graded = dict(zip(frame["field"], frame["grade"]))
    assert graded["loans_customer"] == "verified" and graded["group_2_watch"] == "verified"
    assert stats["fetched"] == 1 and stats["vision_calls"] == 3   # one locator call + two reads


def test_a_scan_without_the_vision_reader_reports_the_gap_instead_of_rows(tmp_path, monkeypatch):
    links = pd.DataFrame([{"bank": "VCB", "period": "2025Q2", "statement_type": "consolidated",
                           "url": "https://x.test/scan.pdf", "found_by": "html", "found_at": "now"}])
    fetcher, _ = fake_fetcher({"https://x.test/scan.pdf": b"%PDF-scan"})
    monkeypatch.setattr(notes_runner, "fast_page_texts", lambda content: [""])
    frame, gates, stats = notes_runner.harvest(tmp_path, links, fetcher, "notes-test", vision=None,
                                               use_vision=False)
    assert len(frame) == 0 and len(gates) == 0
    assert "no text layer" in json.dumps(stats["errors"])


def test_run_notes_writes_silver_gates_run_log_and_watermark_then_skips_the_same_bank_quarter(tmp_path, monkeypatch):
    write_silver(tmp_path, "bank_quarter.parquet", pd.DataFrame([
        {"ticker": "VCB", "period": period, "npl": 0.01} for period in ("2025Q1", "2025Q2")]))
    write_silver(tmp_path, notes_runner.LINKS, pd.DataFrame([
        {"bank": "VCB", "period": "2025Q1", "statement_type": "consolidated", "url": "https://x.test/q1.pdf",
         "found_by": "vietstock_static", "found_at": "now", "http_status": 200},
        {"bank": "VCB", "period": "2025Q2", "statement_type": "consolidated", "url": "https://x.test/q2.pdf",
         "found_by": "vietstock_static", "found_at": "now", "http_status": 200}]))
    fetcher, client = fake_fetcher({"https://x.test/q1.pdf": b"%PDF-q1", "https://x.test/q2.pdf": b"%PDF-q2"})
    monkeypatch.setattr(notes_runner, "fast_page_texts", lambda content: fixtures(content)[0])
    monkeypatch.setattr(notes_runner, "page_tables", lambda content, only=None: fixtures(content)[1])
    log = notes_runner.run_notes(lake=tmp_path, banks=["VCB"], periods=["2025Q1", "2025Q2"],
                                 fetcher=fetcher, vision=object(), use_vision=False)
    assert log["silver"]["rows"] > 0 and log["silver"]["verified_share"] == 1.0
    silver = pd.read_parquet(tmp_path / "silver/notes_bank_quarter.parquet")
    assert set(silver["bank"]) == {"VCB"} and set(silver["period"]) == {"2025Q1", "2025Q2"}
    assert list(silver.columns) == notes_runner.SILVER_COLUMNS
    gates = pd.read_csv(tmp_path / "silver/notes_gate.csv")
    status = dict(zip(gates["gate"], gates["status"]))
    assert status["groups_sum_to_loans"] == "pass" and status["provision_rollforward"] == "pass"
    assert status["npl_vs_vendor"] == "pass"        # the vendor panel prints the ratio as a fraction, read as percent
    assert status["unit_scale"] == "pass"
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
                "value_vnd_bn": value, "page": 1, "source_url": "https://x.test/a.pdf",
                "statement_type": "consolidated", "unit": "trieu", "reader": "text", "grade": grade,
                "raw_sha256": "sha"}
    merged = notes_runner.merge_silver(pd.DataFrame([row("verified", 100.0)]),
                                       pd.DataFrame([row("single", 101.0)]))
    assert len(merged) == 1 and merged.iloc[0]["value_vnd_bn"] == 100.0 and merged.iloc[0]["grade"] == "verified"


def test_coverage_reports_fields_and_verified_share_per_bank_quarter():
    frame = pd.DataFrame([
        {"bank": "VCB", "period": "2025Q2", "field": "loans_customer", "grade": "verified"},
        {"bank": "VCB", "period": "2025Q2", "field": "group_2_watch", "grade": "single"}])
    table = notes_runner.coverage(frame)
    assert table.iloc[0].to_dict() == {"bank": "VCB", "period": "2025Q2", "fields": 2, "verified_share": 0.5}


def test_vietstock_urls_follow_the_verified_naming_and_keep_the_statement_type():
    rows = notes_links.vietstock_quarter_urls("VCB", "2026Q3")
    assert rows[0] == ("https://static2.vietstock.vn/data/HOSE/2026/BCTC/VN/QUY%203/"
                       "VCB_Baocaotaichinh_Q3_2026_Hopnhat.pdf", "consolidated")
    assert [statement_type for _, statement_type in rows] == ["consolidated", "separate", "separate"]
    annual = notes_links.vietstock_annual_urls("VCB", 2025)
    assert annual[0][0].endswith("/NAM/VCB_Baocaotaichinh_2025_Hopnhat.pdf")
    assert not annual[0][0].endswith(".pdf.pdf")


def test_a_probe_keeps_every_head_and_only_a_pdf_answer_becomes_a_link():
    asked = []

    def probe(url):
        asked.append(url)
        if "Hopnhat" in url and "/HOSE/" in url:
            return 200, "application/pdf"
        if "Congtyme" in url:
            return 200, "application/pdf"
        return 404, "text/html"

    probes, hits = notes_links.probe_statement(probe, "VCB", "2026Q3", found_at="now")
    assert len(asked) == 3 and len(probes) == 3                     # consolidated + two separate namings, one exchange
    assert [row["http_status"] for row in probes] == [200, 200, 404]
    assert [row["statement_type"] for row in hits] == ["consolidated", "separate"]
    assert {row["found_by"] for row in probes} == {"vietstock_static"}


def test_a_quarter_missing_on_hose_is_looked_for_on_the_other_exchanges():
    def probe(url):
        return (200, "application/pdf") if "/UPCOM/" in url else (404, "text/html")

    probes, hits = notes_links.probe_statement(probe, "BAB", "2025Q3", found_at="now")
    assert len(hits) == 3 and all("/UPCOM/" in row["url"] for row in hits)      # the three UPCOM namings
    assert len(probes) == 9                                                      # 3 HOSE + 3 HNX 404s, then 3 UPCOM hits


def test_discover_writes_the_probe_log_to_silver_and_does_not_reprobe_a_hit(tmp_path):
    def probe(url):
        return (200, "application/pdf") if "Hopnhat" in url else (404, "text/html")

    registry, stats = notes_runner.discover(tmp_path, ["VCB"], ["2025Q2"], probe, "notes-test",
                                            annual_years=(2025,))
    assert stats["hits"] >= 1 and stats["probes"] >= 3
    saved = pd.read_csv(tmp_path / "silver/notes_links.csv")
    assert set(saved["found_by"]) == {"vietstock_static"} and (saved["http_status"] == 404).any()
    again, stats_again = notes_runner.discover(tmp_path, ["VCB"], ["2025Q2"],
                                              lambda url: (_ for _ in ()).throw(AssertionError(url)),
                                              "notes-test-2")
    assert stats_again["probes"] == 0                       # the 200 consolidated link is already known
    assert len(again) == len(registry)


def test_the_locator_maps_a_thumbnail_grid_to_absolute_pages(tmp_path, monkeypatch):
    class Vision:
        cost_usd = 0.0

        def __init__(self):
            self.calls = 0

        def read(self, png, prompt, model, schema=None):
            assert schema is not None                   # the locator must pass its own schema
            self.calls += 1
            return {"classification_pages": [11, 12, 999], "provision_pages": [13], "balance_sheet_pages": [2]}

    monkeypatch.setattr(notes_runner, "render_strip", lambda content, pages, **kwargs: b"strip")
    vision = Vision()
    pages, errors = notes_runner.locate_table_pages(b"pdf", vision, total=20)
    assert pages == [2, 11, 12, 13]                          # 999 dropped; classification, provision, balance sheet
    assert errors == {} and vision.calls == 4                # 20 pages / 6 per strip


def test_a_fragment_run_writes_rows_to_json_and_leaves_silver_alone(tmp_path, monkeypatch):
    write_silver(tmp_path, notes_runner.LINKS, pd.DataFrame([
        {"bank": "VCB", "period": "2025Q2", "statement_type": "consolidated", "url": "https://x.test/q2.pdf",
         "found_by": "vietstock_static", "found_at": "now", "http_status": 200}]))
    fetcher, _ = fake_fetcher({"https://x.test/q2.pdf": b"%PDF-q2"})
    monkeypatch.setattr(notes_runner, "fast_page_texts", lambda content: fixtures(content)[0])
    monkeypatch.setattr(notes_runner, "page_tables", lambda content, only=None: [])
    fragment = tmp_path / "out/fragment-vcb.json"
    log = notes_runner.run_notes(lake=tmp_path, banks=["VCB"], periods=["2025Q2"], fetcher=fetcher,
                                 vision=object(), use_vision=False, fragment=fragment)
    payload = json.loads(fragment.read_text(encoding="utf-8"))
    assert payload["rows"] and payload["stats"]["fetched"] == 1
    assert not (tmp_path / "silver/notes_bank_quarter.parquet").exists()
    assert log["fragment"] == str(fragment)
    frame, gates = notes_runner.merge_fragments([fragment])
    assert len(frame) == len(payload["rows"]) and set(frame.columns) == set(notes_runner.SILVER_COLUMNS)
    merge = notes_runner.merge_fragment_dir(tmp_path, fragment.parent, "notes-merge-test")
    assert merge["datasets"]["notes_merge"]["fragments"] == 1
    # this fragment only read one page, so the protective gates cannot pass: it is quarantined, not published
    assert merge["silver"]["rows"] == 0
    quarantine = pd.read_parquet(tmp_path / "silver/notes_quarantine.parquet")
    assert len(quarantine) == len(frame) and set(quarantine["bank"]) == {"VCB"}
    silver = pd.read_parquet(tmp_path / "silver/notes_bank_quarter.parquet")
    assert len(silver) == 0 and set(silver.columns) == set(notes_runner.SILVER_COLUMNS)


def test_the_choice_of_a_loans_page_is_driven_by_the_group_total():
    def reading(field, value, page):
        return {"field": field, "value_vnd_bn": value, "page": page, "reader": "vision_a"}
    readings = [reading("loans_customer", 1000.0, 16), reading("loans_customer", 1000000.0, 58),
                reading("loans_customer", 1000.0, 16),
                reading("group_1_current", 900.0, 30), reading("group_2_watch", 50.0, 30),
                reading("group_3_substandard", 20.0, 30), reading("group_4_doubtful", 20.0, 30),
                reading("group_5_loss", 10.0, 30)]
    rows = {row["field"]: row for row in notes_runner.collect(readings, "VCB", "2025Q2", "u", "sha")}
    assert rows["loans_customer"]["value_vnd_bn"] == 1000.0 and rows["loans_customer"]["page"] == 16
    assert rows["group_2_watch"]["page"] == 30
    assert rows["loans_customer"]["grade"] == "verified"          # two readers on page 16, not one


def test_the_choice_of_a_provision_closing_is_driven_by_the_roll_forward():
    def reading(field, value, page):
        return {"field": field, "value_vnd_bn": value, "page": page, "reader": "vision_a"}
    readings = [reading("provision_closing", 130.0, 20), reading("provision_closing", 999.0, 16),
                reading("provision_opening", 100.0, 20), reading("provision_charge", 50.0, 20),
                reading("provision_used_writeoff", 20.0, 20)]
    rows = {row["field"]: row for row in notes_runner.collect(readings, "VCB", "2025Q2", "u", "sha")}
    assert rows["provision_closing"]["value_vnd_bn"] == 130.0 and rows["provision_closing"]["page"] == 20
    assert rows["provision_opening"]["page"] == 20


def test_the_vendor_npl_ratio_is_read_as_a_fraction_and_reported_in_percent(tmp_path):
    write_silver(tmp_path, "bank_quarter.parquet", pd.DataFrame([
        {"ticker": "VCB", "period": "2026Q3", "npl": 0.007058},
        {"ticker": "TCB", "period": "2025Q2", "npl": 0.0115}]))
    vendor = notes_runner.vendor_npl(tmp_path)
    assert vendor[("VCB", "2026Q3")] == pytest.approx(0.7058) and vendor[("TCB", "2025Q2")] == pytest.approx(1.15)


def test_a_provision_balance_whose_coverage_is_implausible_loses_to_the_plausible_page():
    def reading(field, value, page):
        return {"field": field, "value_vnd_bn": value, "page": page, "reader": "vision_a"}
    readings = [reading("group_3_substandard", 20000.0, 39), reading("group_4_doubtful", 10000.0, 39),
                reading("group_5_loss", 5000.0, 39),
                reading("provision_closing", 31168.0, 16),            # coverage 517%: plausible
                reading("provision_closing", 31.2, 40),               # coverage 0.5%: a unit slip on the page
                reading("provision_opening", 25.0, 40), reading("provision_charge", 6.2, 40),
                reading("provision_used_writeoff", 0.0, 40)]
    rows = {row["field"]: row for row in notes_runner.collect(readings, "VCB", "2026Q3", "u", "sha")}
    assert rows["provision_closing"]["value_vnd_bn"] == 31168.0


def test_a_movement_table_on_a_page_whose_closing_has_the_wrong_unit_is_dropped_not_half_emitted():
    def reading(field, value, page):
        return {"field": field, "value_vnd_bn": value, "page": page, "reader": "vision_a"}
    readings = [reading("group_3_substandard", 20000.0, 39), reading("group_4_doubtful", 10000.0, 39),
                reading("group_5_loss", 5000.0, 39),
                reading("provision_closing", 31168.0, 16),
                reading("provision_closing", 31.2, 40), reading("provision_opening", 25.0, 40),
                reading("provision_charge", 6.2, 40), reading("provision_used_writeoff", 0.0, 40)]
    rows = {row["field"]: row for row in notes_runner.collect(readings, "VCB", "2026Q3", "u", "s")}
    assert rows["provision_closing"]["page"] == 16
    assert "provision_opening" not in rows and "provision_charge" not in rows
    gate = notes_gates.rollforward_gate(notes_gates.values_of(list(rows.values())))
    assert gate["status"] == "skipped"            # missing inputs are skipped, never a false pass or fail


def test_the_groups_3_5_total_is_emitted_as_a_derived_row_only_when_all_three_sit_on_one_page():
    def reading(field, value, page, grade_reader="vision_a"):
        return {"field": field, "value_vnd_bn": value, "page": page, "reader": grade_reader}
    readings = [reading("group_3_substandard", 20.0, 39), reading("group_4_doubtful", 15.0, 39),
                reading("group_5_loss", 5.0, 39), reading("group_4_doubtful", 15.0, 41)]
    rows = {row["field"]: row for row in notes_runner.collect(readings, "VCB", "2025Q2", "u", "sha")}
    assert rows["groups_3_5"]["value_vnd_bn"] == 40.0 and rows["groups_3_5"]["page"] == 39
    assert rows["groups_3_5"]["reader"] == "derived" and rows["groups_3_5"]["grade"] == "single"
    only_two = [reading("group_3_substandard", 20.0, 39), reading("group_5_loss", 5.0, 39)]
    assert "groups_3_5" not in {row["field"] for row in notes_runner.collect(only_two, "VCB", "2025Q2", "u", "s")}


def test_gate_rows_accumulate_per_bank_quarter_instead_of_being_overwritten(tmp_path):
    def fragment(bank, period, gate_status):
        rows = [{"bank": bank, "period": period, "field": "loans_customer", "basis": "point",
                 "value_vnd_bn": 1000.0, "page": 1, "source_url": "https://x.test/a.pdf",
                 "statement_type": "consolidated", "unit": "trieu", "reader": "text", "grade": "single",
                 "raw_sha256": "sha"},
                {"bank": bank, "period": period, "field": "group_1_current", "basis": "point",
                 "value_vnd_bn": 1000.0, "page": 1, "source_url": "https://x.test/a.pdf",
                 "statement_type": "consolidated", "unit": "trieu", "reader": "text", "grade": "single",
                 "raw_sha256": "sha"}]
        gates = [{"bank": bank, "period": period, "gate": gate, "status": gate_status,
                  "detail": "", "value": None, "threshold": None}
                 for gate in ("groups_sum_to_loans", "npl_vs_vendor", "unit_scale")]
        return {"rows": rows, "gates": gates, "stats": {}}

    (tmp_path / "fragA").mkdir()
    (tmp_path / "fragB").mkdir()
    (tmp_path / "fragA/one.json").write_text(__import__("json").dumps(fragment("VCB", "2025Q2", "pass")), encoding="utf-8")
    notes_runner.merge_fragment_dir(tmp_path, tmp_path / "fragA", "run1")
    (tmp_path / "fragB/two.json").write_text(__import__("json").dumps(fragment("STB", "2025Q3", "pass")), encoding="utf-8")
    notes_runner.merge_fragment_dir(tmp_path, tmp_path / "fragB", "run2")
    gates = pd.read_csv(tmp_path / "silver/notes_gate.csv")
    assert set(gates["bank"]) == {"VCB", "STB"}          # the second run did not wipe the first bank's gates
    silver = pd.read_parquet(tmp_path / "silver/notes_bank_quarter.parquet")
    assert set(silver["bank"]) == {"VCB", "STB"}


def _row(bank, period, unit, value=1000.0):
    return {"bank": bank, "period": period, "field": "loans_customer", "basis": "point",
            "value_vnd_bn": value, "page": 1, "source_url": "https://x.test/a.pdf",
            "statement_type": "consolidated", "unit": unit, "reader": "vision_a,vision_b",
            "grade": "verified", "raw_sha256": "sha"}


def _gates(bank, period, status):
    return [{"bank": bank, "period": period, "gate": gate, "status": status, "detail": "", "value": None,
             "threshold": None} for gate in ("groups_sum_to_loans", "npl_vs_vendor", "unit_scale")]


def test_a_fresh_read_beats_the_stale_quarantined_copy_of_the_same_grade(tmp_path):
    stale = tmp_path / "stale"
    stale.mkdir()
    (stale / "a.json").write_text(json.dumps({"rows": [_row("TCB", "2025Q3", "unknown", 766.7)],
                                              "gates": _gates("TCB", "2025Q3", "fail"), "stats": {}}),
                                  encoding="utf-8")
    notes_runner.merge_fragment_dir(tmp_path, stale, "run1")
    assert set(pd.read_parquet(tmp_path / "silver/notes_quarantine.parquet")["bank"]) == {"TCB"}
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    (fresh / "b.json").write_text(json.dumps({"rows": [_row("TCB", "2025Q3", "trieu", 766700.0)],
                                              "gates": _gates("TCB", "2025Q3", "pass"), "stats": {}}),
                                  encoding="utf-8")
    notes_runner.merge_fragment_dir(tmp_path, fresh, "run2")
    silver = pd.read_parquet(tmp_path / "silver/notes_bank_quarter.parquet")
    assert silver.iloc[0]["unit"] == "trieu" and silver.iloc[0]["value_vnd_bn"] == 766700.0
    assert len(pd.read_parquet(tmp_path / "silver/notes_quarantine.parquet")) == 0


def test_run_notes_upserts_gates_and_quarantines_bank_quarters_that_do_not_pass(tmp_path, monkeypatch):
    write_silver(tmp_path, "bank_quarter.parquet", pd.DataFrame([
        {"ticker": bank, "period": "2025Q1", "npl": 0.01} for bank in ("VCB", "MBB")]))
    write_silver(tmp_path, notes_runner.LINKS, pd.DataFrame([
        {"bank": bank, "period": "2025Q1", "statement_type": "consolidated",
         "url": f"https://x.test/{bank}.pdf", "found_by": "vietstock_static", "found_at": "now",
         "http_status": 200} for bank in ("VCB", "MBB")]))
    fetcher, _ = fake_fetcher({"https://x.test/VCB.pdf": b"%PDF-vcb", "https://x.test/MBB.pdf": b"%PDF-mbb"})
    monkeypatch.setattr(notes_runner, "fast_page_texts", lambda content: fixtures(content)[0])
    monkeypatch.setattr(notes_runner, "page_tables", lambda content, only=None: fixtures(content)[1])
    for bank in ("VCB", "MBB"):
        notes_runner.run_notes(lake=tmp_path, banks=[bank], periods=["2025Q1"], fetcher=fetcher,
                               vision=object(), use_vision=False)
    gates = pd.read_csv(tmp_path / "silver/notes_gate.csv")
    assert set(gates["bank"]) == {"VCB", "MBB"}          # the second run did not wipe the first bank's gates
    silver = pd.read_parquet(tmp_path / "silver/notes_bank_quarter.parquet")
    assert set(silver["bank"]) == {"VCB", "MBB"}
    marks = json.loads((tmp_path / "state/watermarks.json").read_text(encoding="utf-8"))
    assert marks["notes_bank_last"] == {"VCB": "2025Q1", "MBB": "2025Q1"}


def test_run_notes_keeps_a_bank_quarter_whose_unit_line_is_unreadable_out_of_silver(tmp_path, monkeypatch):
    write_silver(tmp_path, notes_runner.LINKS, pd.DataFrame([
        {"bank": "VCB", "period": "2025Q1", "statement_type": "consolidated", "url": "https://x.test/q1.pdf",
         "found_by": "vietstock_static", "found_at": "now", "http_status": 200}]))
    fetcher, _ = fake_fetcher({"https://x.test/q1.pdf": b"%PDF-q1"})
    monkeypatch.setattr(notes_runner, "fast_page_texts",
                        lambda content: [page.replace("Đơn vị tính: Triệu VND\n", "") for page in fixtures(content)[0]])
    monkeypatch.setattr(notes_runner, "page_tables", lambda content, only=None: [])
    notes_runner.run_notes(lake=tmp_path, banks=["VCB"], periods=["2025Q1"], fetcher=fetcher,
                           vision=object(), use_vision=False)
    quarantine = pd.read_parquet(tmp_path / "silver/notes_quarantine.parquet")
    assert set(quarantine["bank"]) == {"VCB"} and "unknown" in set(quarantine["unit"])
    silver = pd.read_parquet(tmp_path / "silver/notes_bank_quarter.parquet")
    assert len(silver) == 0


def test_the_npl_gate_tolerance_is_ten_basis_points_not_ten_hundredths():
    # the gap is reported in bp (x100), so a 5 bp miss passes and an 11 bp miss fails: comparing bp with 0.10
    # made the gate ten times stricter than the brief and failed CTG 2025Q4 at -2.9 bp
    assert notes_gates.npl_gate(values(), 5.05)["status"] == "pass"
    assert notes_gates.npl_gate(values(), 4.95)["status"] == "pass"
    assert notes_gates.npl_gate(values(), 5.11)["status"] == "fail"
    assert notes_gates.npl_gate(values(), 5.05)["threshold"] == 10.0


def test_a_text_layer_with_no_readable_label_falls_back_to_the_vision_reader(tmp_path, monkeypatch):
    # MBB's PDFs carry a text layer whose font has no ToUnicode map, so it extracts to U+FFFD and no label matches:
    # returning zero rows there loses a bank that a scan read would have read
    links = pd.DataFrame([{"bank": "MBB", "period": "2025Q2", "statement_type": "consolidated",
                           "url": "https://x.test/broken.pdf", "found_by": "html", "found_at": "now"}])
    fetcher, _ = fake_fetcher({"https://x.test/broken.pdf": b"%PDF-broken"})
    monkeypatch.setattr(notes_runner, "fast_page_texts", lambda content: ["\ufffd\ufffd " * 120, "\ufffd" * 300])
    monkeypatch.setattr(notes_runner, "render_strip", lambda content, pages, **kwargs: b"strip")
    monkeypatch.setattr(notes_runner, "render_pages", lambda content, pages, scale=2.0: {page: b"png" for page in pages})
    vision = FakeVision({"values": {"loans_customer": 1000.0}}, {"values": {"loans_customer": 1000.0}}, located=(2,))
    frame, _, stats = notes_runner.harvest(tmp_path, links, fetcher, "notes-test", vision=vision)
    assert set(frame["field"]) == {"loans_customer"} and frame.iloc[0]["grade"] == "verified"
    assert stats["vision_calls"] == 3 and "falling back to vision" in json.dumps(stats["errors"])

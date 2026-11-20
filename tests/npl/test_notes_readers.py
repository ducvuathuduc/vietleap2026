"""Readers of the notes pages: number/unit handling, the two text readers, the vision JSON and link names."""

import json

from vlkit.npl.ingest import notes_contract as contract
from vlkit.npl.ingest import notes_links, notes_text, notes_vision

LOANS_PAGE = """BÁO CÁO TÀI CHÍNH HỢP NHẤT
Đơn vị tính: Triệu VND
TÀI SẢN
Cho vay khách hàng      130     1.234.567   1.100.000
"""

GROUPS_PAGE = """Thuyết minh báo cáo tài chính
Đơn vị tính: Triệu VND
Phân loại nợ vay theo nhóm
Nợ đủ tiêu chuẩn                    1.100.000   1.000.000
Nợ cần chú ý                           80.000      70.000
Nợ dưới tiêu chuẩn                     20.000      15.000
Nợ nghi ngờ                            10.000       8.000
Nợ có khả năng mất vốn                  5.000       3.000
"""

MOVEMENT_PAGE = """Thuyết minh báo cáo tài chính
Đơn vị tính: Triệu VND
Biến động dự phòng rủi ro cho vay khách hàng
Số dư đầu kỳ                           30.000
Số trích lập trong kỳ                   12.000
Số sử dụng trong kỳ                      8.000
Số dư cuối kỳ                           34.000
"""


def test_numbers_and_units_follow_the_vietnamese_format():
    assert contract.parse_number("1.234.567") == 1234567
    assert contract.parse_number("(1.234)") == -1234
    assert contract.parse_number("1.234,5") == 1234.5
    assert contract.parse_number("abc") is None
    assert contract.unit_scale("Đơn vị tính: Triệu VND") == 0.001
    assert contract.unit_scale("Đơn vị: tỷ đồng") == 1.0
    assert contract.unit_scale("Đơn vị tính: Nghìn đồng") == 1e-6
    assert contract.unit_scale("no unit line") == 1.0


def test_text_reader_reads_loans_groups_and_the_provision_movement():
    found = notes_text.read_text([LOANS_PAGE, GROUPS_PAGE, MOVEMENT_PAGE])
    assert found["loans_customer"] == {"value_vnd_bn": 1234.567, "page": 1, "reader": "text"}
    assert found["group_2_watch"]["value_vnd_bn"] == 80.0
    assert found["group_5_loss"]["value_vnd_bn"] == 5.0
    assert found["provision_opening"]["value_vnd_bn"] == 30.0
    assert found["provision_charge"]["value_vnd_bn"] == 12.0
    assert found["provision_used_writeoff"]["value_vnd_bn"] == 8.0
    assert found["provision_closing"] == {"value_vnd_bn": 34.0, "page": 3, "reader": "text"}
    assert all(item["page"] in (1, 2, 3) for item in found.values())


def test_table_reader_skips_the_ma_so_column_and_uses_the_page_unit():
    tables = [(1, [["Chỉ tiêu", "Mã số", "Năm nay", "Năm trước"],
                   ["Cho vay khách hàng", "130", "1.234.567", "1.100.000"]])]
    found = notes_text.read_tables(tables, scales={1: 0.001})
    assert found["loans_customer"] == {"value_vnd_bn": 1234.567, "page": 1, "reader": "table"}


def test_two_readers_agreeing_is_verified_one_reader_is_single_and_disagreement_is_contested():
    assert contract.grade([("text", 100.0), ("table", 100.0)]) == ("verified", 100.0)
    assert contract.grade([("text", 100.0)]) == ("single", 100.0)
    grade, value = contract.grade([("text", 100.0), ("vision_a", 130.0)])
    assert grade == "contested" and value == 100.0
    assert contract.grade([]) == (None, None)


def test_ytd_flows_become_quarters_while_balances_stay_as_printed():
    rows = [
        {"bank": "VCB", "period": "2025Q1", "field": "provision_charge", "basis": "ytd", "value_vnd_bn": 5.0},
        {"bank": "VCB", "period": "2025Q2", "field": "provision_charge", "basis": "ytd", "value_vnd_bn": 12.0},
        {"bank": "VCB", "period": "2025Q3", "field": "provision_charge", "basis": "ytd", "value_vnd_bn": 30.0},
        {"bank": "VCB", "period": "2025Q4", "field": "provision_charge", "basis": "ytd", "value_vnd_bn": 40.0},
        {"bank": "VCB", "period": "2025Q2", "field": "loans_customer", "basis": "point", "value_vnd_bn": 9.0},
    ]
    out = contract.to_quarterly(rows)
    quarterly = {row["period"]: row["value_vnd_bn"] for row in out if row["basis"] == "quarterly"}
    assert quarterly == {"2025Q1": 5.0, "2025Q2": 7.0, "2025Q3": 18.0, "2025Q4": 10.0}
    assert len([row for row in out if row["basis"] == "ytd"]) == 4               # the printed rows are kept
    assert all(row["basis"] == "point" for row in out if row["field"] == "loans_customer")


def test_a_quarter_without_its_preceding_quarter_gets_no_derived_value():
    rows = [{"bank": "VCB", "period": "2025Q3", "field": "provision_charge", "basis": "ytd", "value_vnd_bn": 30.0}]
    assert [row["basis"] for row in contract.to_quarterly(rows)] == ["ytd"]


VISION_B = {"page_label": "Thuyết minh - trang 24", "unit_printed": "Đơn vị tính: Triệu VND",
            "period_label": "Quý 2 năm 2025",
            "lines": [{"label": "Nợ cần chú ý", "numbers": ["80.000", "70.000"]},
                      {"label": "Số dư cuối kỳ", "numbers": ["34.000"]}],
            "values": {"group_2_watch": 80.0}}


def test_vision_json_is_parsed_from_a_fence_and_transcribed_lines_are_scaled():
    reply = "```json\n" + json.dumps(VISION_B, ensure_ascii=False) + "\n```"
    payload = notes_vision.parse_json(reply)
    assert payload["values"] == {"group_2_watch": 80.0}
    assert notes_vision.read_line_numbers(payload)["provision_closing"] == 34.0
    assert notes_vision.parse_json("no json here") is None


def test_page_numbers_survive_the_way_a_model_writes_them():
    payload = {"classification_pages": ["p12", "page 13", 14, "n/a"],
               "provision_pages": ["15"], "balance_sheet_pages": ["p2"]}
    assert notes_vision.pages_from_locate(payload, allowed=range(1, 20)) == ({12, 13, 14}, {15}, {2})


def test_vision_values_only_accept_known_fields():
    payload = {"values": {"group_2_watch": 80.0, "made_up_field": 1.0, "loans_customer": None,
                          "provision_charge": "12.5"}}
    assert notes_vision.payload_values(payload) == {"group_2_watch": 80.0, "provision_charge": 12.5}


def test_links_read_quarter_and_statement_type_from_the_file_name():
    html = ('<a href="/files/VCB_BCTC_hopnhat_2024_Q3.pdf">tai ve</a>'
            '<a href="https://x.test/BCTC_rieng_2025_quy-2.pdf">tai ve</a>'
            '<a href="/files/lich-hop.pdf">lich</a>')
    rows = notes_links.rows_from_page("VCB", html, "https://x.test/page")
    assert sorted((row["period"], row["statement_type"]) for row in rows) == [("2024Q3", "consolidated"),
                                                                            ("2025Q2", "separate")]
    frame = notes_links.prefer_consolidated(rows + [
        {"bank": "VCB", "period": "2024Q3", "statement_type": "separate",
         "url": "https://x.test/rieng.pdf", "found_by": "agent", "found_at": "now"}])
    assert list(frame["statement_type"]) == ["consolidated", "separate"]


def test_agent_records_become_links_only_when_they_name_a_quarter_and_a_url():
    records = [{"period": "2025Q1", "statement_type": "consolidated", "pdf_url": "https://x.test/a.pdf"},
               {"period": "unknown", "statement_type": "unknown", "pdf_url": "https://x.test/b.pdf"},
               {"period": "2025Q2", "statement_type": "consolidated", "pdf_url": ""}]
    rows = notes_links.rows_from_agent("BID", records, found_at="now")
    assert [(row["period"], row["url"]) for row in rows] == [("2025Q1", "https://x.test/a.pdf")]

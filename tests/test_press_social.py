from __future__ import annotations

from pathlib import Path

from tools.press import social_rss

FIXTURES = Path(__file__).parent / "fixtures" / "press"


def test_parse_feed_and_weekly_rows():
    entries = social_rss.parse_feed((FIXTURES / "vnexpress_kinh_doanh.rss").read_bytes(), "vnexpress")
    assert len(entries) == 3
    rows = social_rss.weekly_rows(entries)
    assert rows
    weeks = {r["week"] for r in rows}
    assert "2026-W47" in weeks
    banking = [r for r in rows if r["sector"] == "banking"]
    assert banking and banking[0]["article_count"] >= 1
    assert banking[0]["top_5_keywords"]


def test_sector_keyword_map():
    assert social_rss.sector_for("Ngân hàng tăng lãi suất huy động") == "banking"
    assert social_rss.sector_for("Giá căn hộ TP.HCM giảm") == "real_estate"
    assert social_rss.sector_for("Khối ngoại bán ròng chứng khoán") == "capital_market"
    assert social_rss.sector_for("Vốn FDI đăng ký tăng") == "fdi"
    assert social_rss.sector_for("Giải ngân đầu tư công") == "public_investment"
    assert social_rss.sector_for("Chỉ số giá tiêu dùng CPI") == "macro"
    assert social_rss.sector_for("Tin không liên quan") == "other"

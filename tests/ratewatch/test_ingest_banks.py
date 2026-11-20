"""banks.yaml: every reachable Vietnamese commercial bank, unreadable ones kept with a reason."""
from pathlib import Path

from vlkit.ratewatch.ingest.banks import load_banks

ROOT = Path(__file__).resolve().parents[2]
BANKS = ROOT / "scenarios" / "ratewatch" / "banks.yaml"


def test_every_commercial_bank_is_listed_once():
    banks = load_banks(BANKS)
    codes = [b["code"] for b in banks]
    assert len(banks) == 34 and len(set(codes)) == 34  # 33 banks + the VCBNeo digital brand
    assert {"VCB", "BIDV", "CTG", "AGB", "TCB", "MBB", "ACB", "VPB", "STB", "HDB", "OCB", "VCBNEO"} <= set(codes)
    assert len([b for b in banks if b["ownership"] == "state"]) == 7


def test_required_fields_and_vi_names_with_diacritics():
    for bank in load_banks(BANKS):
        for field in ("code", "name_vi", "name_en", "ownership", "website", "rate_page", "robots",
                      "status", "notes"):
            assert bank.get(field), (bank["code"], field)
        assert "methods" in bank
        if bank["status"] == "readable":
            assert bank["methods"], bank["code"]
        assert bank["website"].startswith("https://")
        assert bank["rate_page"].startswith("https://")
        assert bank["ownership"] in ("state", "joint_stock", "digital_brand")
        assert set(bank["methods"]) <= {"aggregator", "bank_pdf", "bank_html", "tinyfish"}
        assert bank["robots"] in ("allow", "blocked", "unknown")
        assert bank["status"] in ("readable", "unreadable")
        assert any(ord(ch) > 127 for ch in bank["name_vi"]), bank["code"]


def test_unreadable_banks_carry_the_evidence():
    unreadable = [b for b in load_banks(BANKS) if b["status"] == "unreadable"]
    assert len(unreadable) == 10
    for bank in unreadable:
        assert bank["reason"].strip(), bank["code"]
        assert "aggregator" not in bank["methods"], bank["code"]
    assert {"SCB", "NCB", "KLB", "SGB", "GPB", "OCEAN", "CBB", "BVB", "PGB", "BVBANK"} == {
        b["code"] for b in unreadable}


def test_aggregator_names_map_to_one_code():
    seen = {}
    for bank in load_banks(BANKS):
        for name in bank.get("agg_names") or []:
            assert name not in seen, name
            seen[name] = bank["code"]
    assert seen["Vietinbank"] == "CTG"
    assert seen["An Binh Bank"] == "ABB"
    assert seen["VCB Neo"] == "VCBNEO"


def test_column_hints_name_a_channel_and_a_zero_based_column():
    for bank in load_banks(BANKS):
        for key in ("html", "pdf"):
            hint = bank.get(key)
            if not hint:
                continue
            assert hint["channel"] in ("counter", "online"), bank["code"]
            assert isinstance(hint["rate_column"], int) and 0 <= hint["rate_column"] <= 8, bank["code"]
            assert isinstance(hint.get("tier", ""), str)

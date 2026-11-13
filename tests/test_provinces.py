"""Province normaliser and 63→34 merger map (Resolution 202/2025/QH15)."""
import csv

import pytest

from vlkit.vn import PROVINCES_63, normalize_province, to_new_province


@pytest.mark.parametrize("raw,canon", [
    ("TP.HCM", "Hồ Chí Minh"), ("TP HCM", "Hồ Chí Minh"), ("Ho Chi Minh City", "Hồ Chí Minh"), ("Sài Gòn", "Hồ Chí Minh"),
    ("Quận 1, TP. Hồ Chí Minh", "Hồ Chí Minh"),
    ("Ha Noi", "Hà Nội"), ("HN", "Hà Nội"), ("Thủ đô Hà Nội", "Hà Nội"),
    ("Tỉnh Bình Dương", "Bình Dương"), ("Thành phố Đà Nẵng", "Đà Nẵng"),
    ("Hue", "Thừa Thiên Huế"), ("Thừa Thiên - Huế", "Thừa Thiên Huế"),
    ("tinh dak lak", "Đắk Lắk"), ("Bà Rịa–Vũng Tàu", "Bà Rịa - Vũng Tàu"),
    ("Hoà Bình", "Hòa Bình"), ("Thanh Hoá", "Thanh Hóa"), ("Khánh Hoà", "Khánh Hòa"),  # old vs new tone placement
])
def test_normalize_spellings(raw, canon):
    assert normalize_province(raw) == canon


@pytest.mark.parametrize("raw", ["Narnia", "", "   ", None, 12])
def test_normalize_unknown(raw):
    assert normalize_province(raw) is None


def test_all_63_round_trip():
    assert len(PROVINCES_63) == 63
    for p in PROVINCES_63:
        assert normalize_province(p) == p


@pytest.mark.parametrize("old,new", [
    ("Bình Dương", "Hồ Chí Minh"), ("Bà Rịa - Vũng Tàu", "Hồ Chí Minh"), ("Hồ Chí Minh", "Hồ Chí Minh"),
    ("Hà Nội", "Hà Nội"), ("Quảng Nam", "Đà Nẵng"), ("Ninh Thuận", "Khánh Hòa"), ("Kiên Giang", "An Giang"),
    ("Long An", "Tây Ninh"), ("Bình Phước", "Đồng Nai"), ("Hải Dương", "Hải Phòng"), ("Thái Bình", "Hưng Yên"),
    ("Hà Giang", "Tuyên Quang"), ("Hòa Bình", "Phú Thọ"), ("Thừa Thiên Huế", "Huế"),
])
def test_merger_map(old, new):
    assert to_new_province(old) == new


def test_merger_csv_complete(kit_root):
    rows = list(csv.DictReader(open(kit_root / "engine/vlkit/resources/province_63_to_34.csv", encoding="utf-8")))
    olds = {r["old_province"] for r in rows}
    assert olds == set(PROVINCES_63), sorted(set(PROVINCES_63) ^ olds)
    assert len({r["new_province"] for r in rows}) == 34
    for p in PROVINCES_63:
        assert to_new_province(p) is not None


def test_to_new_province_none():
    assert to_new_province(None) is None


def test_already_normalised_province_columns_are_not_resuffixed(tmp_path):
    """Gold OBT already carries 'X__province'; the insight loader must not create 'X__province__province'."""
    import pandas as pd
    from vlkit.loader import load_and_clean
    df = pd.DataFrame({"Tỉnh/TP": ["Hà Nội", "TP.HCM", "Đà Nẵng"] * 20,
                       "Tỉnh/TP__province": ["Hà Nội", "Hồ Chí Minh", "Đà Nẵng"] * 20,
                       "Giá": list(range(60))})
    p = tmp_path / "x.csv"
    df.to_csv(p, index=False)
    out = load_and_clean(p)
    cols = out.df.columns
    assert not any(c.endswith("__province__province") for c in cols), list(cols)

"""Create a deliberately messy Vietnamese property CSV to stress-test parsing.
Ground truth (so we can check the engine): price/m² depends on province tier and property type; area has a negative
effect on price/m²; rent ≈ 0.35%/month of price. Mess: UTF-16 + tab delimiter, 2 title rows, VN number formats
('2,5 tỷ', '850 triệu', '3 tỷ 200 triệu', 'Thỏa thuận'), province spelling variants, dd/mm/yyyy dates, duplicates,
an empty column, outliers."""
import random
from pathlib import Path
import numpy as np

rng = np.random.default_rng(7); random.seed(7)
PROV = {"Hồ Chí Minh": (["TP.HCM", "TP Hồ Chí Minh", "Ho Chi Minh", "thành phố Hồ Chí Minh", "HCM"], 95e6),
        "Hà Nội": (["Hà Nội", "Ha Noi", "TP. Hà Nội", "Hanoi"], 90e6),
        "Đà Nẵng": (["Đà Nẵng", "Da Nang", "TP Đà Nẵng"], 60e6),
        "Bình Dương": (["Tỉnh Bình Dương", "Binh Duong", "Bình Dương"], 35e6),
        "Cần Thơ": (["Cần Thơ", "Can Tho", "TP Cần Thơ"], 30e6),
        "Hải Phòng": (["Hải Phòng", "Hai Phong"], 40e6)}
TYPE = {"Căn hộ chung cư": 1.0, "Nhà phố": 1.35, "Đất nền": 0.8, "Biệt thự": 1.6}


def vn_money(v):
    r = rng.random()
    if r < 0.03:
        return "Thỏa thuận"
    if v >= 1e9:
        ty = int(v // 1e9); tr = int((v % 1e9) // 1e6)
        if r < 0.3 and tr:
            return f"{ty} tỷ {tr} triệu"
        return f"{v / 1e9:.2f}".replace(".", ",") + " tỷ"
    return f"{v / 1e6:,.0f}".replace(",", ".") + " triệu"


rows = []
for i in range(2500):
    prov = random.choices(list(PROV), weights=[30, 28, 12, 12, 8, 10])[0]
    t = random.choice(list(TYPE))
    area = float(np.clip(rng.lognormal(4.3, 0.45), 25, 600))
    ppm2 = PROV[prov][1] * TYPE[t] * (area / 80) ** -0.15 * rng.lognormal(0, 0.25)
    if rng.random() < 0.01:
        ppm2 *= 30  # data-entry outliers
    price = ppm2 * area
    rent = price * 0.0035 * rng.lognormal(0, 0.15)
    income = rng.lognormal(np.log(22e6), 0.4)
    d, m, y = random.randint(1, 28), random.randint(1, 12), random.choice([2023, 2024, 2025])
    area_s = random.choice([f"{area:.0f} m²", f"{area:.0f}m2", f"{area:.1f}".replace(".", ",") + " m2"])
    rows.append([f"BDS{i:05d}", f"{d:02d}/{m:02d}/{y}", random.choice(PROV[prov][0]), t, area_s, vn_money(price),
                 f"{rent / 1e6:.1f}".replace(".", ",") + random.choice([" triệu", " tr"]), f"{income / 1e6:.0f} triệu", "",
                 random.choice(["Sổ hồng", "Sổ đỏ", "Đang chờ sổ", "Hợp đồng mua bán"])])
rows += random.sample(rows, 40)  # exact duplicates
hdr = ["Mã tin", "Ngày đăng", "Tỉnh/TP", "Loại BĐS", "Diện tích", "Giá bán", "Giá thuê/tháng", "Thu nhập hộ/tháng", "Ghi chú", "Pháp lý"]
lines = ["BÁO CÁO TIN ĐĂNG BẤT ĐỘNG SẢN (dữ liệu mô phỏng)", "Nguồn: tổng hợp nội bộ, cập nhật 12/2025", "\t".join(hdr)]
lines += ["\t".join(map(str, r)) for r in rows]
out = Path(__file__).parent.parent / "data/practice/synthetic_messy_bds.csv"
out.write_text("\n".join(lines), encoding="utf-16")
print(out, len(rows))

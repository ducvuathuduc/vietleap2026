"""Build a firm × quarter practice workbook from ThaiDat/Vietnamese-Financial-Data (2021 statements of ~1,000 VN listed firms).
Source: https://github.com/ThaiDat/Vietnamese-Financial-Data (items as rows × tickers as columns, one file per quarter)
Sector/exchange: https://github.com/youngsu-park-69/vietnam-stock-data (vietnam_companies.csv)
Output: data/practice/vn_firms_2021.xlsx with one sheet per quarter (exercises multi-sheet stacking)."""
from pathlib import Path
import pandas as pd

RAW = Path(__file__).parent.parent / "data/raw/vnfin"
IS_ITEMS = {"3. Doanh thu thuần (1)-(2)": "Doanh thu thuần", "4. Giá vốn hàng bán": "Giá vốn hàng bán",
            "5. Lợi nhuận gộp (3)-(4)": "Lợi nhuận gộp", "9. Chi phí bán hàng": "Chi phí bán hàng",
            "10. Chi phí quản lý doanh nghiệp": "Chi phí quản lý DN", "-Trong đó: Chi phí lãi vay": "Chi phí lãi vay",
            "19. Lợi nhuận sau thuế thu nhập doanh nghiệp (15)-(18)": "Lợi nhuận sau thuế"}
BS_ITEMS = {"TỔNG CỘNG TÀI SẢN": "Tổng cộng tài sản", "A. Nợ phải trả": "Nợ phải trả", "B. Nguồn vốn chủ sở hữu": "Vốn chủ sở hữu",
            "IV. Tổng hàng tồn kho": "Hàng tồn kho", "I. Tiền và các khoản tương đương tiền": "Tiền và tương đương tiền"}


def block(path, items):
    d = pd.read_excel(path)
    d = d.drop_duplicates(subset="ID", keep="first").set_index("ID")  # first block = non-financial template
    return d.loc[[k for k in items if k in d.index]].rename(index=items).T


comp = pd.read_csv(RAW / "vietnam_companies.csv")[["symbol", "sector1_vn", "exchange"]].rename(
    columns={"symbol": "Mã CK", "sector1_vn": "Ngành", "exchange": "Sàn"})
out = Path(__file__).parent.parent / "data/practice/vn_firms_2021.xlsx"
with pd.ExcelWriter(out) as xw:
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        t = block(RAW / f"IS_{q}_2021.xlsx", IS_ITEMS).join(block(RAW / f"BS_{q}_2021.xlsx", BS_ITEMS), how="inner")
        t = t.dropna(subset=["Doanh thu thuần", "Tổng cộng tài sản"])
        t.index.name = "Mã CK"
        t = t.reset_index().merge(comp, on="Mã CK", how="left")
        t.insert(1, "Kỳ báo cáo", f"{q} 2021")
        t.to_excel(xw, sheet_name=f"{q}_2021", index=False)
        print(q, t.shape)
print(out)

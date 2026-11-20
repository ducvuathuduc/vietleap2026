"""Build NPL gold data and reports from local Silver CSV or Parquet."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb
import pandas as pd

from .model import BASES, KEY, THRESHOLDS, build_signals, calibrate_npl, derive_credit_quality
from .regression import run_regressions
from .warehouse import write_gold

DATA_DICTIONARY = """# Từ điển dữ liệu chất lượng tín dụng

## Silver (CSV UTF-8 hoặc Parquet)

| Cột | Ý nghĩa |
|---|---|
| bank_code, period, basis | Khóa gồm mã ngân hàng, quý lịch YYYYQn và phạm vi báo cáo hợp nhất (consolidated) hoặc riêng lẻ (separate). |
| loans_vnd_bn (L) | Dư nợ cho vay khách hàng cuối quý, tỷ VND. |
| group2_vnd_bn (G2) | Dư nợ nhóm 2 cuối quý, tỷ VND. |
| npl_vnd_bn (N) | Dư nợ nhóm 3–5 cuối quý, tỷ VND. |
| provision_vnd_bn (P) | Số dư dự phòng cho vay cuối quý, tỷ VND. |
| writeoff_vnd_bn (W), writeoff_basis | Số nợ xóa, tỷ VND, trong quý (quarter) hoặc lũy kế từ đầu năm (ytd). |
| source_url, page | URL báo cáo và số hoặc ký hiệu trang. |
| extracted_by, extracted_at, raw_sha256 | Người hoặc phương pháp trích xuất, thời điểm trích xuất ISO 8601 kèm múi giờ, SHA-256 của tệp gốc. |

## Gold DuckDB

| Bảng hoặc view | Hạt dữ liệu và nội dung |
|---|---|
| gold.dim_bank | Một dòng mỗi mã ngân hàng. |
| gold.dim_period | Một dòng mỗi quý lịch, gồm năm, số quý và cờ cuối quý. |
| gold.dim_source | Một dòng mỗi bộ thuộc tính nguồn trích xuất, khóa source_id. |
| gold.fact_credit_quality | Một dòng mỗi ngân hàng, quý và phạm vi báo cáo. Lưu số gốc, tỷ lệ dẫn xuất, nguồn và missing_fields (tên từng ô Silver thiếu). |
| gold.fact_signal | Một dòng mỗi ngân hàng, quý và tín hiệu đã kích hoạt. Lưu phạm vi báo cáo và câu tiếng Việt, tiếng Anh. |
| gold.v_credit_quality | Dữ kiện tín dụng cùng kỳ và nguồn trích xuất. |
| gold.v_signal | Tín hiệu kèm thay đổi các tỷ lệ và khóa nguồn. |

| Cột dẫn xuất | Công thức |
|---|---|
| npl_ratio | N / L |
| g2_ratio | G2 / L |
| coverage | P / N, đơn vị lần |
| broad_problem_ratio | (N + G2) / L |
| writeoff_q_vnd_bn | W nếu báo theo quý hoặc là quý 1. Với YTD ở quý 2–4, lấy W trừ lũy kế đã biết đến quý trước trong cùng năm. Lũy kế có thể được tính từ các quý rời. |
| writeoff_ratio | W quy về quý / L quý trước |
| writeoff_ratio_annualised | 4 × writeoff_ratio, quy năm tuyến tính |
| npl_formation | (N hiện tại − N quý trước + W quy về quý) / L quý trước |
| npl_numerator_effect | (N hiện tại − N quý trước) / L quý trước |
| npl_loan_growth_effect | N hiện tại × (1 / L hiện tại − 1 / L quý trước) |
| loan_growth, lagged_coverage | L hiện tại / L quý trước − 1, và coverage quý trước |
| delta_* | Tỷ lệ hiện tại trừ tỷ lệ quý trước. Hai phần numerator và loan growth cộng lại bằng delta_npl_ratio. |

Tỷ lệ lưu dưới dạng phân số (0,01 = 1%). Số dư và số xóa nợ phải hữu hạn, không âm.
L phải đủ bao quát N + G2. npl_ratio, g2_ratio và broad_problem_ratio nằm trong [0, 1].
Coverage và tỷ lệ xóa nợ có thể lớn hơn 1. NPL formation có thể âm.
Mẫu số bằng 0, thiếu đầu vào hoặc thiếu quý liền trước cho kết quả rỗng ở phép tính phụ thuộc.
YTD giảm so với lũy kế đã biết làm kiểm tra thất bại. YTD thiếu mốc quý trước để lại W quý rỗng.

## Tín hiệu và hồi quy

Mỗi lần chạy dùng một phạm vi báo cáo cho tín hiệu và hồi quy (mặc định consolidated).
Toàn bộ phạm vi báo cáo hợp lệ được giữ trong bảng dữ kiện tín dụng. Phép so sánh theo quý
chỉ dùng quý liền kề của cùng ngân hàng và phạm vi. Tín hiệu S2 và S4 thường cần ba quý
dư nợ để so sánh hai tỷ lệ dùng dư nợ đầu quý.

Các ngưỡng mặc định bằng 0. Mỗi tùy chọn `--threshold-{npl,g2,writeoff,coverage,formation}`
là mức thay đổi tuyệt đối tối thiểu, theo phân số hoặc số lần với coverage. S1–S4 cần NPL
giảm vượt ngưỡng và chỉ số tương ứng thay đổi đúng hướng, vượt ngưỡng. S5 cần NPL và nhóm 2
giảm vượt ngưỡng, mức tăng tỷ lệ xóa nợ và mức giảm coverage nằm trong ngưỡng cho phép.
Mỗi quy tắc chỉ kích hoạt khi có đủ các đầu vào của quy tắc đó.

Hồi quy dùng thay đổi tỷ lệ NPL theo điểm phần trăm. Tỷ lệ xóa nợ, thay đổi tỷ lệ nhóm 2,
tăng trưởng dư nợ và coverage trễ giữ nguyên đơn vị trong bảng dữ kiện. Báo cáo hồi quy
gồm OLS gộp, OLS hiệu ứng cố định theo ngân hàng, và ước lượng lại hiệu ứng cố định khi
lần lượt bỏ từng ngân hàng. Sai số chuẩn cụm theo ngân hàng và khoảng tin cậy t 95%.
Các mô hình dùng quan sát đủ đầu vào. Báo cáo ghi trạng thái khi mẫu quá nhỏ hoặc ma trận thiếu hạng.

Đối chiếu tùy chọn `--fiin-reference` nhận CSV có bank_code, period, basis và npl_ratio
dưới dạng phân số. `--fiin-tolerance` là sai số tuyệt đối tối đa, cùng đơn vị.
Chỉ các khóa được cung cấp mới được đối chiếu, và mọi khóa đó phải có tỷ lệ tính được.
"""

ERD = """erDiagram
    dim_bank ||--o{ fact_credit_quality : bank_code
    dim_period ||--o{ fact_credit_quality : period
    dim_source |o--o{ fact_credit_quality : source_id
    fact_credit_quality ||--o{ fact_signal : "bank_code, period, basis"
    dim_bank {
        string bank_code PK
    }
    dim_period {
        string period PK
        int quarter
        int year
        boolean is_quarter_end
    }
    dim_source {
        bigint source_id PK
        string source_url
        string page
        string extracted_by
        string extracted_at
        string raw_sha256
    }
    fact_credit_quality {
        string bank_code PK, FK
        string period PK, FK
        string basis PK
        bigint source_id FK
    }
    fact_signal {
        string bank_code PK, FK
        string period PK, FK
        string signal PK
        string basis FK
    }
"""


def _read_silver(path):
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    if path.suffix.lower() == ".parquet":
        with duckdb.connect() as con:
            return con.read_parquet(str(path)).df()
    raise ValueError("Silver input must be CSV or Parquet")


def run_pipeline(silver, out, *, basis="consolidated", thresholds=None, reference=None, tolerance=None):
    """Validate and stage all artifacts before publishing them to the output directory."""
    if (reference is None) != (tolerance is None):
        raise ValueError("FiinQuant reference and tolerance must be supplied together")
    credit = derive_credit_quality(_read_silver(Path(silver)))
    if reference is not None:
        calibrate_npl(credit, reference, tolerance=tolerance)
    signals = build_signals(credit, basis=basis, thresholds=thresholds)
    regression = run_regressions(credit, basis=basis)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".npl-", dir=out) as folder:
        stage = Path(folder)
        write_gold(stage / "npl.duckdb", credit, signals)
        signals.to_csv(stage / "signals.csv", index=False, encoding="utf-8")
        (stage / "regression.json").write_text(
            json.dumps(regression, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8",
        )
        (stage / "data_dictionary.md").write_text(DATA_DICTIONARY, encoding="utf-8")
        (stage / "erd.mmd").write_text(ERD, encoding="utf-8")
        for artifact in stage.iterdir():
            artifact.replace(out / artifact.name)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--silver", type=Path, help="Silver CSV or Parquet file")
    inputs.add_argument("--real", type=Path, help="D1 Silver directory for the seven-model analysis")
    parser.add_argument("--out", required=True, type=Path, help="Gold output directory")
    parser.add_argument("--basis", choices=BASES, default="consolidated", help="Signal and regression basis")
    for metric in THRESHOLDS:
        parser.add_argument(f"--threshold-{metric}", type=float, default=0.0)
    parser.add_argument("--fiin-reference", type=Path, help="CSV with bank_code, period, basis, npl_ratio")
    parser.add_argument("--fiin-tolerance", type=float, help="Maximum absolute difference in NPL fractions")
    args = parser.parse_args(argv)
    reference = None
    try:
        if args.real is not None:
            from .real_pipeline import run_real

            run_real(args.real, args.out)
            return
        if args.fiin_reference is not None:
            references = pd.read_csv(args.fiin_reference, dtype={name: str for name in KEY})
            reference = references.set_index(KEY, verify_integrity=True)["npl_ratio"].to_dict()
        run_pipeline(
            args.silver, args.out, basis=args.basis, reference=reference, tolerance=args.fiin_tolerance,
            thresholds={metric: getattr(args, f"threshold_{metric}") for metric in THRESHOLDS},
        )
    except (KeyError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()

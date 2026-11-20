# RateWatch fixtures (trimmed, real reads)

Every file is a trimmed copy of a real response saved during the 20/11/2026 research runs (see
`~/.kiro/herdr-tasks/vietleap-4/X-TF/`). No numbers were invented; only irrelevant rows/blocks were cut.

- `aggregator_20261120.html` — `https://laisuattietkiem.vn/`, fetched 20/11/2026 13:19 +07 (3 bank blocks kept: Agribank, Vietinbank, OCB; page stamp `20.11.2026`).
- `pdf/Sacombank_20261020.txt` — `https://www.sacombank.com.vn/content/dam/sacombank/files/cong-cu/lai-suat/tien-gui/khcn/SACOMBANK_LAISUATNIEMYETTAIQUAY_KHCN_VIE.pdf`, sheet date printed `20.10.2026`, text extracted with pdfplumber on 20/11/2026.
- `pdf/OCB_20261106.txt` — `https://webocb-api.ocb.com.vn/Resources/Files/20261106091027_3-06.11.2026-bang-lai-suat-tien-gui-khcnvn-web-vnd.pdf`, sheet date printed `06/11/2026`, fetched 20/11/2026.
- `pdf/VietBank_20261019.txt` — `https://static.vietbank.com.vn/web/vietbank-nguon/ban-le/cap-nhat-lai-suat/lai-suat-khcn-19102026.pdf`, sheet date printed `19/10/2026`, fetched 20/11/2026.
- `html/OCB_20261120.html` — `https://ocb.com.vn/vi/cong-cu/lai-suat`, fetched 20/11/2026 13:19 +07 (the `Kỳ hạn | Tiền gửi có kỳ hạn | Tiết kiệm thông thường | Tiết kiệm Online` table only; the page prints no effective date).
- `html/VietinBank_20261120.html` — `https://www.vietinbank.vn/ca-nhan/cong-cu-tien-ich/lai-suat-khcn`, fetched 20/11/2026 13:19 +07 (VND/USD/EUR table only; the only date string on the page is an unrelated `Ngày 17/7/2024`).
- `tinyfish/HDBank_20261120.json` — TinyFish agent run `781cb22a-264a-45a3-a7c6-2e6182f5c664` on `https://hdbank.com.vn/vi/ca-nhan/tiet-kiem/lai-suat`, COMPLETED 20/11/2026 13:16 +07, `page_effective_date` `2026-10-19`, terms 1/2/3/6/12/24 kept.

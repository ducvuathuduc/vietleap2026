# T2 follow-up 1 from Kiro
Your T2 files are now ported into the main checkout (C:\Users\dieut\Desktop\Money\vietleap, branch feat/ratewatch) and all 66
tests/ratewatch tests pass there. Kiro ran the live non-rate ingest from the main checkout (network works there):
run rw-20261120T1436: interbank 7, central_fx 1, sbv_credit 20, sbv_deposit 20, fiin_quarter 258, fiin_market 5960 records, 418 s.
Failures: omo "ValueError: Bảng NHNN thiếu ngày quan sát"; cpi_index "ValueError: Không tìm thấy bản tin CPI mới trong danh mục".
The raw responses are saved (read them, no network needed):
  C:\Users\dieut\Desktop\Money\vietleap\data\lake\ratewatch\bronze\omo\rw-20261120T1436\b31cb93ffc134caf8dbb.bin (+ .meta.json)
  C:\Users\dieut\Desktop\Money\vietleap\data\lake\ratewatch\bronze\cpi_index\rw-20261120T1436\1ea5741316fe91c27ac0.bin (+ .meta.json)
Do, in your worktree (Kiro ports again):
1. Fix the OMO parser and the CPI release discovery against these real responses (systematic-debugging: reproduce with a test that
   loads a trimmed copy of each response as a fixture, then fix). If CPI YoY is only in the release text, parse the YoY sentence and
   keep the release URL as the citation.
2. A failed optional source must not block publish: ingest returns exit 2 for partial success with the per-source errors in the run log;
   the snapshot carries per-source freshness/status, and a quality gate shows "warn" with the reason.
3. Keep the Sacombank calibration gate exactly as it is (it correctly blocked a T1 parsing error; pi fixes T1).
4. Add `geo` to the snapshot from data/lake/ratewatch/gold/geo_provinces.json (CONTRACT.md section D, M1 already wrote it; module
   engine/vlkit/ratewatch/geo/ exists in the main checkout: copy nothing from it, only read its output file path via a CLI flag --geo).
Acceptance in your worktree with the main venv: pytest -q tests/ratewatch (your files) exit 0; transform+publish on fixtures exit 0.
List every file you changed in your final message. Do not commit.
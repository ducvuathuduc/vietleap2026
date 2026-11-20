# I-SAVE — DONE
**Best concept — A "Hóa đơn 12 tháng"** (datasets, join keys, scores, crowding URLs: `IDEAS.md`): one 500 m VND sum receipted
across counter deposit / online deposit / physical SJC gold / cash dollars at the household's horizon; no premium screen, no break-even calculator; concept B ("Đô la trong tủ") folded in as its sharpest line.
**First real number** (verified quotes, computed today): buying SJC at BTMC's ask and selling at its bid costs **4.173 % = 20.9 m
VND per 500 m** (≈8 months of a 6.47 % deposit). After that toll, cash dollars held 12 months = **−2.08 % real** median and beat
CPI in only **3/15** windows; gold beat CPI **14/21** (12 m), **16/17** (24 m), **14/14** (36 m). Counter 12 m deposits (8 banks
posting both channels): median **5.50 %** vs CPI **+5.03 % YoY** = **+0.47 % real**, online 6.47 % = **+1.44 % real**; Sacombank's
own verified PDF shows a **1.40 pp** same-bank gap = 7.0 m VND per 500 m per year.
**Crowding verdict:** category crowded (webgia.com/lai-suat, laisuattietkiem.vn, timo.vn, simplize.vn, tools.finhay.com.vn,
giavang.com.vn, bank blogs on online-vs-counter); no tool found publishes the observed-outcome receipt (after-spread, CPI-deflated win rates by holding period + the per-bank channel bill in VND). Survives, but never pitch it as a rate table.
**Main risk:** the counter-vs-online headline rests on one fully verified PDF (Sacombank); Agribank/BIDV rows are `agent_only_unconfirmed`; no official deposit-rate history exists, so the deposit leg is a snapshot, not a series.
**Verification, fresh 20/11/2026 ~12:35 ICT:** `python verify.py` → exit 0, 9/9 PASS (`verify.out`); repo `git status --porcelain` → 0 lines; samples `samples\gold_fx_pull.csv` (39 real dates), `windows_12m.csv`, `horizon_real_returns.csv`.
**Not done:** full daily BTMC backfill (≈2.9 h), daily FX backfill, rate history, VN30 leg, deeper academic search.

# REPORT — R-SUPPLY (research, no repo changes)

STATUS: DONE. Deliverables: `SUPPLY.md` (199 lines, sections 1–5), `REPORT.md`, samples in `samples\{fiin,vn,intl,mine}\`, worker detail in `partial_vn.md` / `partial_intl.md`.

Acceptance checks (all run fresh, this session):
- FiinQuantX 0.1.73 introspected + live calls: `introspect.py` exit 0; `fiin_calls.py`, `fiin_calls2.py` ran to completion, `fiin_calls3.py` cut by a 180 s timeout at the streaming `OrderBook` call (documented, §1.1 row 23) → 24 entry points mapped, 38 samples ≤20 rows, `results*.json` holds timings/errors.
- VN probe: `python vn_probe.py` exit 0 on re-run → 29 URLs, status + sample in `vn_probe.json` / `samples\mine\`.
- Intl endpoints re-verified by me (curl batch, 14/14 answered) + worker `calllog.txt`.
- `git status --porcelain` in vietleap → 0 lines (repo untouched). No sample >1 MB. No packages installed.

Top 5 "unusual but real" combinations:
1. SJC premium: BTMC JSON (SJC sell 13.42 m/lượng) × Yahoo GC=F (3,528.4 USD/oz) × USDVND 25,705 → world parity 109.35 m → **+22.7 % premium** (19.9 % at VCB 25,940). Join: date.
2. Province firm formation (NSO PXWeb V05.02, 70 provinces × 9 y) × listed issuers via FiinQuant `taxCode` prefix (10/10 verified) × HDX COD-AB 34 `adm1_pcode` × GDL SHDI (6 regions). Join: pcode / 2-digit prefix.
3. VNINDEX PE/PB (261 daily rows, PE 14.10) × SJC premium × foreign net (FPT Nov −1.92 tn VND). Deposit-rate leg **dropped**: no usable free source today (webgia serves decoy cells).
4. Foreign flow vs dong + gold premium (VCB XML 25,530/25,940 monthly net, room 48.99 %). Join: month.
5. Hazard micro-geography: ticker→province→centroid × Open-Meteo flood (26.99→300.30 m³/s) × PM2.5 × WorldPop 100 m. Join: adm1_pcode.

Did not do: TinyFish runs (0 USD spent — plain HTTP sufficed); social-insurance site blocked by TLS; NSO PXWeb POST query still returns the table list, not cells (2–4 h).
Risks: geoBoundaries ADM1 is 64 units from 2008 — use HDX `adm1_pcode`; GDL serves 6 regions, not provinces; FiinQuant raw data stays internal per partner terms.

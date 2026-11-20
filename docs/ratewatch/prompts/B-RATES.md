# B-RATES Build the real deposit-rate panel: every bank, both channels, today, plus any honest history
Repo (read/run only): C:\Users\dieut\Desktop\Money\vietleap
Data work with real calls, not product code. Do NOT edit the repo.

## Context
- Read C:\Users\dieut\.kiro\herdr-tasks\vietleap-4\CONTEST.md and your own ..\D-UNLOCK\UNLOCK.md and ..\I-SAVE\IDEAS.md.
- The owner fixed the area to finance and banking in Vietnam. Two leading questions need this panel: (a) the counter vs online
  deposit-rate gap (who loses by saving at the counter), and (b) whether banks that pay more are riskier.

## Do (write RATES.md)
1. Today's panel for every commercial bank you can reach (target >= 25 of the ~30 banks: state-owned, large and small joint-stock,
   including those missing from D-UNLOCK): individual VND deposits, terms 1/3/6/9/12/18/24/36 months, counter AND online channel,
   effective date on the page, source URL. TinyFetch/raw HTML first, TinyFish for client-rendered pages, bank PDFs where published.
   Second reader for every number (TinyFetch text, PDF text, or a second TinyFish run with a different prompt). Label each row
   verified / agent_only. Save samples\rates_panel_today.csv.
2. History: find honest sources for 2021-2026 bank-level deposit rates: Internet Archive CDX snapshots of bank rate pages or rate PDFs
   (web.archive.org/cdx/search/cdx?url=...), bank PDF archives, monthly press tables (VnExpress/CafeF/Vietstock) that list rates by
   bank. Test 3 banks x 4 dates each; report what works, depth, and effort for a full backfill. Save samples\rates_history_sample.csv.
3. First real numbers from today's panel: median online-minus-counter gap by term, number of banks with a gap, largest gaps; the
   cross-bank spread of 12-month online rates (min/median/max) and which banks sit at the top.

## Rules
- Cite URL + access time; never invent numbers; negative claims need the exact URL and response.
- Respect robots.txt, delays >= 2 s, no captcha/login bypass, never print secrets. TinyFish budget USD 6 (log run id, steps, cost).
- No repo edits, no git writes, do not kill processes you did not start, do not install into the repo .venv.
- Timebox: 40 minutes. Write RATES.md and REPORT.md (max 15 lines) in THIS folder.
# YOLO real-run checklist (optional, P3) — fill with measured values only

| Item | Value |
|---|---|
| Video URL | [NEEDS CLARIFICATION: choose a CC BY / CC0 clip ≤ 2 min] |
| Licence / attribution | |
| Duration (s), resolution | |
| Command | `python scenarios/cv_counting/count.py --video <v.mp4> --every 15s --stride 3 --license "<licence>" --out out/cv/counts.csv` |
| ultralytics / supervision versions (`pip show`) | |
| Processing time (s) and fps | |
| Manual count (30 s window, class, in/out) vs tool | |
| Difference % (target ≤ 15%) | |
| Ingest: `python de.py run <tmp sources.yaml with kind: cv>` status | |
| Dashboard shows counts by time bin? | |
| Notes (AGPL caveat acknowledged in submission? `--events` fallback?) | |

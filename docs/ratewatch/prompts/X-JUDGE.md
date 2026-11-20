# X-JUDGE Red-team the final concept as the judging panel, using the World Bank judge's own workshop material
Repo (read only): C:\Users\dieut\Desktop\Money\vietleap
## Context
- Read ..\CONTEST.md, ..\BA.md (the concept), ..\V-LAW\LAW.md, ..\V-MACRO\MACRO.md, ..\V-CURVE\CURVE.md.
- Judge Sacha Dray's workshop material: https://github.com/sachadray/hackathon-dashboard (README, docs/index.html slides with
  speaker notes, docs/handout.html, prompts/). Key rules there: a dashboard is one screen answering a recurring question for a specific
  reader against a benchmark so they can decide; four questions (level, benchmark, trend, decision); anatomy (headline with numbers,
  three key numbers, controls, one main chart, detail table, source/date/method); responsible AI (trace every number, recompute three by
  hand, explain every chart without AI, keep private data out of prompts and public pages, say where AI helped); quality checks
  (parts vs totals, calibrate on a known value, flag disagreeing datasets). Read the material yourself.
## Do (write JUDGE.md)
1. Score the concept against each of Dray's rules and the official rubric (Product 40, Presentation 40, Teamwork 20). Be harsh.
2. List the 25 hardest questions the five judges would ask (Dray, Pham Thai Binh, Nguyen Ngoc Phuong Trang of Shinhan, Tuan Chu,
   Doan Vu Nguyen), each with the best honest answer we can give from the verified findings, or "HOLE" if we cannot answer.
3. For each HOLE: the smallest change to the concept, data or method that closes it by 21/11 13:00.
4. The planned extras: on-device OCR of a savings book, an AI planner with Langfuse traces, live charts in chat, an MCP endpoint.
   For each: does it help the reader decide, or is it decoration? Does it break "keep private data out of the prompt"? Keep / change / cut.
5. Write the one-sentence headline and the four answers (level, benchmark, trend, decision) the main screen should show, using only
   numbers already verified in the task folders (cite the file).
## Timebox: 40 minutes. Write JUDGE.md and REPORT.md (max 15 lines) in THIS folder.
## Rules
- Real calls only; cite URL + access time (Asia/Saigon); mark [verified]/[inferred]. Never invent numbers. Negative claims need the
  exact URL and response. Respect robots.txt, delays >= 2 s, no captcha/login bypass, never print secrets.
- No repo edits, no git writes, do not kill processes you did not start, no npm build, do not install into the repo .venv.
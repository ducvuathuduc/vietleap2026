# X-JUDGE — red team of "Lãi Suất Hôm Nay" (BA.md, 20/11/2026 12:40)

Panel standard: Sacha Dray's workshop, read this session, plus the guidebook rubric in `../CONTEST.md` (Product 40, Presentation 40, Teamwork 20). Concept judged: `../BA.md`. Numbers below are only those already marked verified in the task folders, or arithmetic on those cells done in this session and shown. `[verified]` = in a cited task file or in a response this session. `[inferred]` = how a judge will use that fact. Asia/Saigon.

**Score as the concept is written: 31/100.** Product 15/40. Presentation 12/40. Teamwork 4/20. A judge who has just taught this workshop will treat the national curve, the 6.25% median and the chatbot as the pitch, and those three are the parts we cannot defend.

## 0. What was read this session

Workshop repo https://github.com/sachadray/hackathon-dashboard (tree sha `99085a6cde668723a76b12bfcc75094ece259ab4`).

| Clock | HTTP | Bytes | URL |
| --- | --- | --- | --- |
| 13:11:25 | 200 | 30,190 | https://github.com/robots.txt — `User-agent: *` disallows `/*/raw/` on github.com |
| 13:11:27 | 404 | 14 | https://raw.githubusercontent.com/robots.txt — no rules published |
| 13:11:29 | 200 | 3,804 | https://raw.githubusercontent.com/sachadray/hackathon-dashboard/HEAD/README.md |
| 13:11:32 | 200 | 41,445 | …/HEAD/docs/handout.html |
| 13:11:34 | 200 | 57,300 | …/HEAD/docs/index.html (34 slides, speaker notes in `<aside class="notes">`) |
| 13:12:16 | 200 | 9,125 | …/HEAD/prompts/handson.md |
| 13:12:18 | 200 | 1,945 | …/HEAD/prompts/claude-code.md |
| 13:12:21 | 200 | 9,773 | …/HEAD/prompts/replicate-land.md |
| 13:12:23 | 200 | 8,788 | …/HEAD/prompts/replicate-pfm.md |
| 13:14:41 | 404 | 106 | https://api.github.com/robots.txt |

The file tree was fetched from `api.github.com` before that last robots check. The robots URL itself is a 404, so no disallow was missed. Files were taken from `raw.githubusercontent.com`, not from `github.com/*/raw/`. Slides: https://sachadray.github.io/hackathon-dashboard/ . Handout: …/handout.html . Prompts: …/prompts.html .

Rules used, from the slides (not from memory):

- A dashboard is one screen that answers a recurring question for a named reader, against a benchmark, so they can decide (slide 8, notes 6:30–7:45). If an element can disappear without changing the decision, remove it.
- Four sentences before any chart: level, benchmark, trend, decision (slide 9). The decision is the headline (slide 10).
- Anatomy: headline with numbers, three key numbers, controls, one main chart, one detail table, source/date/method (slide 10).
- Quality checks: parts against totals, calibrate on a known value, flag datasets that disagree (slide 13 notes; `prompts/handson.md` QUALITY CHECKS).
- Responsible AI: trace every number, recompute three by hand, explain every chart with no AI in the room, keep private data out of the prompt and off public pages, say where AI helped (slide 30).
- Day-2 instruction he will remember because he said it: one working screen by noon, one teammate whose only job is to break the numbers (slide 29).

Hand checks this session, simple-interest formula in `../V-CURVE/CURVE.md` §3, `f = 2×[(1+r12)/(1+r6/2)−1]`:

- OCB online 6.00% then 6.30% → **6.4078%**, which CURVE rounds to 6.41%.
- Sacombank counter, under 500 triệu, 5.70% then 5.40% → **4.9587%**, which CURVE rounds to 4.96%.
- VietinBank 3.00% then 5.40% → **7.6847%**. MACRO prints 7.685%; CURVE prints 7.68% and says do not quote it. Same cell, three roundings.
- Ten 5-month→6-month jumps printed in CURVE §2, ACB's 0.00 included: mean **0.895**, `statistics.median` **1.10**. CURVE's "median +1.15 pp (mean 0.90)" matches 1.15 only if ACB is dropped, and that mean is then 0.99, not 0.90. Quote the bank, not that median.
- Ceiling count in `../V-CURVE/samples/curve_today.csv`: 19 of 45 quotes at 1–5 months equal 4.75 when the Sacombank ≥2 tỷ tier is excluded (that tier is another 5 quotes, all at 4.75). Matches CURVE §2.

## 1. Dray's rules, applied to BA.md

**One screen, one reader, one recurring question, one benchmark. Fail.** BA names judges-as-savers, households, and SBV/DIV staff, and four jobs (plan, break-even, safety, policy). The recurrence is the word "hôm nay". The two dual-read sheets are dated 20/10/2026 and 06/11/2026 (`../V-CURVE/CURVE.md` §1). A page the reader must scroll across a planner, a national curve and a policy view is the report he told the room to refuse (slide 8).

**Four questions written first. Fail.** BA never writes level / benchmark / trend / decision. Section 5 below is that quartet. Without it the build is a monitoring page (slide 9 notes: if you cannot fill the fourth, you do not have a decision tool).

**Anatomy. Fail.** Wow 1 is every bank on one chart. That is the data dump (slide 8). There is no headline with a number the team can recompute. Controls are real and useful (amount, horizon, channel) and they are the part to keep. Source, date and method belong in the footer; `../V-LAW/LAW.md` §5 already lists the sentences. BA does not put them on the screen.

**Responsible AI. Fail on four of the five lines.**

- Trace: the task folders trace cells. BA still leads with 5.20–7.00% and a 6.25% median from `../B-RATES/RATES.md`, where 268 of 289 rows have one reader.
- Recompute three by hand: not in the concept. The three to recompute in the pitch are 6.4078%, 4.9587%, and 350,000,000 (the cap, not a calculation).
- Explain the chart with no model in the room: possible for the two verified curves. Not possible for a Nelson-Siegel factor or a chat-drawn chart.
- Private data: the planned Langfuse trace and a passbook photo put personal financial data in a prompt. `../V-LAW/LAW.md` §4.2. Detail in section 4.
- Say where AI helped: missing. The guidebook requires an AI-use record (`../CONTEST.md`).

**Quality checks. Fail.**

- Parts vs totals: 8 banks and 110 rows do not add up to household deposits of 11,434,266 tỷ (`../V-MACRO/MACRO.md` §2). Nothing in the folders is a bank-level deposit stock.
- Calibrate: the cap and the 4.75% ceiling match the Công báo and the SBV scan (`../V-LAW/LAW.md` §§1–2). There is no SBV monthly average for November 2026 to calibrate a "market rate" against. MACRO §2: the official monthly rate file is not a contiguous series.
- Disagreeing datasets: BA still prints the BIDV 1.85 pp gap and the Sacombank 1.40 pp gap. V-CURVE did not read a BIDV household sheet (the PDF on offer is the corporate sheet of 16/12/2025). I-SAVE's Sacombank PDF cell (7.00% online vs 5.60% counter, same printed date 20/10/2026) is not the cell V-CURVE graded verified (counter, under 500 triệu, 12-month 5.40%). OCB counter is already `contested` inside CURVE (page 5.90/6.20 vs its PDF 5.73/5.83 at 6/12 months). Slide 13 says flag that. The concept averages past it.

## 2. Official rubric

**Product — 15/40.**

- Question (5/8). A household choosing a term and a split is inside "data to decision". The written question also asks what the ceiling and the cap "cost". No folder contains that cost in đồng. `../V-MACRO/MACRO.md` §4: Taichinh, WebGiá, Timo, Simplize and Calc.vn already show rate tables; Timo already discusses 6 months versus 12 months and does not print a renewal threshold. The only unoccupied sentence is that threshold, on a named sheet, next to the cap.
- Data (4/8). Luật 111, Thông tư 05/2026, Quyết định 2411 and two dual-read sheets are the right evidence. The concept's opening numbers are the wrong evidence. Big-4 household sheets were not read (`../V-CURVE/CURVE.md` §1). Shinhan is not in `../V-CURVE/banks.tsv`.
- Methods (3/8). The simple-interest break-even matches the way the sheets print interest, and it matches BA's own formula. Nelson-Siegel, a cross-bank regression of rate on risk, and any point forecast do not match a one-day posted panel. MACRO's verdict is that the forecast method is none.
- A product that works (1/8). BA is a concept. The repo a judge can open today is the macro monitor, which `../DECISION.md` already set aside because it looks like everyone else's dashboard.
- Documentation (2/8). The task folders are the check trail Dray asked for. The required open file with edit history, data limits, AI use and who-did-what does not exist (`../CONTEST.md`).

**Presentation — 12/40.**

The break-even card (wow 3) and the cap (wow 4) can be said in one sentence and defended. Wow 1 and wow 2 cannot. Pitch order in BA puts the indefensible chart first and the chatbot second. Slide 30: "the AI did it" is not an answer. The English script and the short Vietnamese close required by the guidebook are unwritten, so the 40 presentation points are mostly still unearned. Twelve points is the credit for having two sentences that survive a question.

**Teamwork — 4/20.**

`../CONTEST.md`: teammates' disciplines are unknown. `../DECISION.md` item 2 is still open (names, disciplines, team name). Slide 29 asks for three roles, including one sceptic. No folder records those roles. Four points is for a research trail that is internally consistent across LAW, CURVE and MACRO. It is not evidence that every member contributed.

## 3. Twenty-five questions

Each answer is what we can say from the folders. **HOLE** means we cannot. The change is the smallest one that can be done before 21/11 13:00 on the laptop we have. "Change" means a cut or a label, not a new model.

### Dray

1. **Who is the reader, and what do they decide on this one screen?** HOLE. BA has three audiences and four jobs. **Change:** one line at the top of the doc and of the page — a household with a VND balance and a date the money is needed, deciding the term at one named bank and whether the balance sits inside 350 triệu. The policy page leaves the demo path.

2. **What did you calibrate on?** The cap 350,000,000 and the ceiling 4.75% are calibrated on the gazette (`../V-LAW/LAW.md`). The 6.25% median is not a known official value. HOLE if that median, or 5.20%, or 7.00%, is on the screen. **Change:** delete every B-RATES aggregate from the script. Footnote the forward as `2×[(1.063)/(1.03)−1] = 0.064078`.

3. **Which way is the rate moving?** There is no forecast (`../V-MACRO/MACRO.md` §5). The two verified sheets point opposite ways: OCB's break-even 6.41% is above today's 6.00%; Sacombank's 4.96% is below today's 5.70%. HOLE for Nelson-Siegel or a national trend line. **Change:** cut the Nelson-Siegel fit from the build. The trend tile is those two break-evens, labelled "phép tính trên tờ niêm yết, không phải lãi suất kỳ tới", with the sheet dates.

4. **Do your banks add up to 11,434,266 tỷ?** HOLE. No bank deposit stock was joined. August 2026 household deposits, +10.63% year-to-date, are a system total from the SBV JSON (`../V-MACRO/MACRO.md` §2), and the October 2025 methodology break means that figure is not a growth rate to splice onto 2024. **Change:** chart title "lãi suất niêm yết đã đọc". The system total sits in the footnote and is not a sum of the chart.

5. **Your median kink is +1.15 percentage points. A spreadsheet says +1.10.** HOLE, and he will do this one. Ten jumps in CURVE §2, including ACB at 0.00, median 1.10, mean 0.895 (this session). **Change:** the spoken kink is OCB online, 4.75% to 6.00%, **+1.25 pp**, grade verified. ACB's flat 4.00% through 6 months is the sentence that the ceiling does not bend every curve (`../V-CURVE/CURVE.md` §2).

### Nguyễn Ngọc Phương Trang

6. **Put Shinhan, Vietcombank, BIDV and Agribank on the chart.** HOLE. CURVE §1: Vietcombank and Agribank are client-rendered with no PDF; BIDV's PDF in hand is the corporate sheet of 16/12/2025; Shinhan is absent from `banks.tsv`. **Change:** the demo names two banks. A last-minute agent run that returns one unverified big-4 row stays off the headline. Grade `agent_only` is a table label, not a wow.

7. **Sacombank's own PDF shows 7.00% online and 5.60% at the counter, a 1.40 pp gap. Why is your verified 12-month cell 5.40%?** HOLE. I-SAVE calls 7.00 vs 5.60 verified on the PDF dated 20/10/2026 (`../I-SAVE/IDEAS.md` §2). V-CURVE's later read of a sheet with that date grades the counter tier under 500 triệu as verified at 5.40% for 12 months, and the tier from 2 tỷ as `agent_only` at 5.60%. The online 7.00% is not in the CURVE table. The folders disagree on tier and channel, and nobody reconciled them. **Change:** the pitch uses the verified tier only. The 1.40 pp sentence comes out. An online column returns only after a second reader on that exact column.

8. **Are you giving investment advice? Is a certificate of deposit a security?** Answer, with the limit LAW already printed. Comparing posted deposit rates and computing a forward is outside Luật Chứng khoán 54/2019 Điều 4 khoản 32, provided the screen does not recommend buying, selling or holding a security (`../V-LAW/LAW.md` §4.1, reproduced text; the Công báo PDF of Luật 54 was not opened). A certificate of deposit is an insured deposit under Luật 111 Điều 17. The footer is LAW §5 item 8, including the ban on writing the forward as if the bank had posted it. The imperative "nên khoá 12 tháng" is the line that fails this question.

9. **When does insurance pay, and does a current account count?** Answer. Thông tư 05/2026/TT-NHNN Điều 3: 350,000,000 đồng of principal and interest, one person, one participating institution, from 13/7/2026. Payout only on the events in Luật 111 Điều 21 (approved bankruptcy; SBV finds a foreign branch unable to pay; or the special-control triggers). "Ngân hàng gặp sự cố" is the wrong sentence. Insured: VND deposits of an individual — demand, term, savings, certificates — except Điều 18. Foreign-currency deposits are outside Điều 17. Policy banks (`ngân hàng chính sách`) do not participate; that sentence is not about Agribank. A debt at the same institution nets off (Điều 23). Quyết định 32/2021's 125 triệu expired on 13/7/2026 (Nghị định 280/2026 Điều 36 khoản 2 điểm c). Do not print 125 triệu as the current cap. `../V-LAW/LAW.md` §§1 and 5.

10. **Is this rate today's, and may you republish the sheet?** The date half is an answer: print `page_effective_date`. It is blank for VietinBank, ACB and MSB, and CURVE refused to guess. HOLE on each bank's website terms; no folder records that check. **Change:** footer "ngày in trên tờ, không phải ngày mở sổ". Banks with a blank sheet date leave the demo. FiinQuant raw stays off the page (`../CONTEST.md`). Do not claim the curve updates every morning until that morning's run has two readers.

### Phạm Thái Bình

11. **Does the higher rate compensate for a riskier bank?** HOLE. No regression was run. The live market number in MACRO §3 is the level-2 bank-sector price-to-book, 1.254277 on 18/11/2026 and 1.248028 on 19/11/2026, which is not a deposit-rate cross-section. R-SUPPLY has Vietcombank 2024 NPL 0.96%, LDR 80.8%, NIM 2.86% (`../R-SUPPLY/SUPPLY.md` §1.1) and CURVE has no Vietcombank deposit rate, so the pair cannot be shown. **Change:** delete the risk scatter. One spoken fact we do have: the insurance premium is 0.15%/year, flat, paid by the bank (0.1% for quỹ tín dụng nhân dân from the Q4 2026 collection quarter), Thông tư 04/2026 (`../V-LAW/LAW.md` §1). The insurer is not pricing this bank's risk into the household's rate.

12. **Your 19.06% means four-fifths of deposits are uninsured. Yes?** Answer the trap. Do not say that. DIV, citing SBV, on a pre-issuance page: at 31/12/2025 the insured stock was 10.02 million tỷ đồng and 138.69 million depositor records; the 350 triệu option would fully cover 93.68% of those records and 19.06% of that value (`../B-POLICY/POLICY.md` §3). The page is not a recount after 13/7/2026. 138.69 million is above the World Bank 2025 population of 101,598,527, so the unit is records, not people. "Value fully covered" is not "share of đồng inside the cap": the 80.94% complement still contains the insured first 350 triệu of large accounts. HOLE for the đồng-weighted insured share. **Change:** use the words "giá trị được bảo hiểm toàn bộ", cite the pre-issuance limit, and leave the đồng share unstated. There is no microdata to recompute it tonight.

13. **I have 500 triệu at one bank. What do I do?** The cap rule is an answer. A VND-maximising split across named banks is a HOLE: we do not have two verified sheets at a 500 triệu tier. Sacombank's higher tier starts at 2 tỷ and is `agent_only`. Interest counts toward the 350 triệu, so depositing the full 350 triệu at OCB's 6.30% does not leave the interest inside the cap. A full-year simple illustration is 350,000,000×0.063 = 22,050,000, and the principal that keeps principal-plus-interest inside the cap is 350,000,000/1.063 = 329,256,820. That illustration uses a 365-day year the sheet did not confirm. **Change:** demo persona 300 triệu, under the cap, for the term decision. Second line, no bank name: a 500 triệu balance at one institution has an uninsured excess once principal and interest exceed 350 triệu. No optimiser.

14. **Where is the sustainable-finance question?** Answer. We do not have an ESG metric, and inventing one fails the trace rule. The number that belongs to his institute is the coverage asymmetry in question 12. If he wants a climate or green-credit decision, this product does not answer it. Say that in the first minute.

15. **Quỹ tín dụng nhân dân are capped at 5.25%, not 4.75%. Did you draw 4.75% on them?** The law is an answer: Quyết định 2411 Điều 1, 0.5% on demand and under 1 month; 4.75% from 1 month to under 6 months; 5.25% for quỹ tín dụng nhân dân and tổ chức tài chính vi mô; terms of 6 months and longer have no ceiling in Thông tư 48 Điều 3 khoản 2 (`../V-LAW/LAW.md` §2). The data is a HOLE: no such sheet was read. A later ceiling decision is still not ruled out by an exhaustive Công báo search (LAW report). **Change:** the reference line is labelled "trần 4,75%/năm cho tổ chức nhận tiền gửi thông thường; quỹ tín dụng nhân dân và tổ chức tài chính vi mô: 5,25%. QĐ 2411, hiệu lực 20/11/2024".

### Tuấn Chu

16. **Is the kink a causal estimate of the ceiling?** Answer: no. Zero of those 45 quotes sit above 4.75% (`../V-CURVE/CURVE.md` §2). That is consistent with the cap binding on the cells we read. MACRO and CURVE both say a one-day cross-section does not estimate the causal effect. **Change:** the caption is "niêm yết đúng trần". It is not "trần làm người gửi mất X đồng".

17. **Eight banks, two of them read twice, the big four missing. What population is this?** HOLE for any sentence that says "thị trường" or "mọi ngân hàng". 22 of 110 rows are verified (Sacombank counter under 500 triệu, PDF plus agent; OCB online, table plus PDF). The other 88 are `agent_only` (`../V-CURVE/REPORT.md`). **Change:** say the counts as written in that report. External validity stops at the banks whose cells are on the slide.

18. **Will OCB pay 6.41% in six months?** Answer: no. 6.41% is the second-leg simple rate that ties a 6.00% deposit and a renewal against a 12-month lock at 6.30%, using half-year fractions. It is not a posted rate and not an expectation (`../V-MACRO/MACRO.md` §5; `../V-LAW/LAW.md` §3). The screen calls it a phép tính.

19. **VietinBank's own page implies 7.68%. Why hide the most dramatic number?** Answer. The 6-month cell is 3.00% and the 12-month cell is 5.40%, one reader, no sheet date (`../V-CURVE/CURVE.md` §1 and §3). The forward is an artefact of a 2.10% short end. Hand check 7.6847%. It may sit in the detail table as `agent_only`, with that sentence. It is not the headline. Same treatment for the compounding variant of the formula, which CURVE computes about 0.15 pp higher and which the sheets do not use.

20. **Your formula treats six months as half a year. The sheet says actual days over 365.** Answer on the formula: both BA and CURVE use the half-year simple form, and CURVE cites a BIDV day-count note while also saying BIDV's household numbers were not read. HOLE for a đồng interest figure. **Change:** the main screen shows percentage points. If a persona needs đồng, the label is "ước tính 365 ngày, chưa phải lịch trả lãi của ngân hàng", and the number is not called the bank's payout.

### Đoàn Vũ Nguyên

21. **Why is this not the 1-tỷ tax notch? That is a public-finance decision.** The substance is an answer. `../DECISION.md` (11:35) recommends the notch and records that there is no microdata, so no bunching estimate and no headcount inside the notch. BA (12:40) switches to deposits. A household can act tomorrow on a posted rate and a statutory cap; the notch cannot be sized. HOLE: the switch is not written in the document the guidebook will grade. **Change:** ten lines — the question we did not build, the missing microdata, and the decision a household can still execute.

22. **What is the incidence of the ceiling, in đồng?** HOLE. No count of balances in the 1-to-under-6-month band (`../B-POLICY/POLICY.md` §2). A 1.25 pp gap on one sheet is not a national transfer. **Change:** no national cost in đồng on the slide or in the script.

23. **The same DIV page says 2.8 times GDP per capita, against a global 3.3 times and 47% of value. Are we under-insured?** Answer only the page. Those comparators are DIV's sentence about the pre-issuance assessment (`../B-POLICY/POLICY.md` §3). We did not recompute GDP per capita. **Change:** if 2.8× is shown, it is quoted as DIV's sentence with the URL already in POLICY.md, next to "chưa phải số đo sau 13/7/2026". It is not "Việt Nam bảo hiểm một nửa mức thế giới".

24. **Household deposits +10.63%, credit +10.19%. What should the State Bank do?** Answer: the product does not say. August 2026, SBV JSON: household deposits 11,434,266 tỷ, +10.63% year-to-date; credit 20,489,434 tỷ, +10.19%; organisation deposits 6,337,186 tỷ, +2.54% (`../V-MACRO/MACRO.md` §2). They are context for why the household stock matters. Interbank on 17/11/2026, overnight 4.9% (`../V-MACRO/MACRO.md` §1), and the 19/11 open-market table, gross won 2,713.20 tỷ at 4.50%, stay in a context strip. VIRA's 2,714 tỷ and its net-injection figure are a different source; they are not added to the SBV row.

25. **The pitch is in English. Who speaks, and where is the Vietnamese close?** HOLE. Guidebook: English presentation, short Vietnamese summary, filenames `TeamName_*` (`../CONTEST.md`). Team name and speakers are open (`../DECISION.md`). **Change:** a 90-second English opening that is the headline in section 5, a 30-second Vietnamese restatement of the same four lines, and one person whose job before noon is to recompute 6.4078%, 4.9587% and the 350,000,000 cap on a spreadsheet. That is the teamwork points still available. It is also slide 29.

## 4. Planned extras

Test used: slide 8 (does the reader decide differently if this disappears?) and slide 30 (private data in the prompt or on a public page).

| Extra | Decision? | Private data? | Call |
| --- | --- | --- | --- |
| On-device OCR of a savings book | No. The decision needs amount, term, bank, channel. Those can be typed. A misread that becomes a "rate" fails the trace rule. | Yes if the image, an account number or a name reaches a prompt, a log, a trace or the projector. Nghị định 356/2025 Điều 4 điểm i and điểm k cover an identity photo and customer financial data (`../V-LAW/LAW.md` §4.2). On-device does not help once the demo screen shows the page. | **Cut.** |
| AI planner with Langfuse traces | Only if every number is a tool call on the verified snapshot. A free-text answer will reintroduce 7% and the 6.25% median. The formula card already decides. | Langfuse Cloud is EU, US or Japan (`../V-TECH/TECH.md` §2). Luật 91 Điều 20: the app sending an identifiable balance abroad is a cross-border transfer; the small-firm exemption does not cover Điều 20; the exemption for a person sending their own data does not cover the app sending it (`../V-LAW/LAW.md` §4.2). A public trace URL publishes the prompt (`../V-TECH/TECH.md` §2). | **Change.** Scripted persona, no name, no account number, no photo. Tools only. Mask before export. No public trace. If that is not true by noon, the planner is not in the pitch. |
| Live charts in the chat | No. The one chart is already the decision. A second series drawn in the chat is a number that skipped the snapshot. | Safe only when the chat never sees an identifier. The chart itself is the leak if the model improvises a rate. | **Cut.** If a chat remains, it returns the cited cell and a link to the chart on the screen. |
| MCP endpoint | No in the room. The judges will not call it. | Safe only as the same public snapshot, with citations, no FiinQuant raw, no user balance. | **Cut** for the demo. The hours go to the script and the sceptic. |

## 5. The screen

Reader: a household with VND savings and a date the money is needed.

Three key numbers: **4,75%** (the ceiling, and OCB's 1–5 month rate), **6,41%** (OCB's break-even), **350 triệu** (the cap).

Controls: amount, the date the money is needed, and a bank/channel pair limited to rows in `curve_today.csv`. Default pair: OCB online. Second pair, on the same chart, only when the user asks: Sacombank counter, under 500 triệu.

One chart: those posted tenors, one line, a horizontal mark at 4.75%, the 6-month and 12-month points labelled. Not 30 banks.

Detail table: the verified rows, then `agent_only` rows with that word visible. OCB counter stays `contested` and off the chart. Sheet date in the row. Blank sheet date: the row is out of the demo.

Footer, from LAW §5: Quyết định 2411, Thông tư 05/2026 Điều 3, Luật 111 Điều 21, the sheet URL, the sheet date, the read time, and the sentence that a forward is a phép tính, not a posted rate and not advice under Luật 54/2019 Điều 4 khoản 32.

**Headline, one sentence, Vietnamese, decision first:**

Trên biểu OCB online đề ngày 06/11/2026, kỳ 1–5 tháng đứng ở trần 4,75%/năm, kỳ 6 tháng là 6,00%/năm và kỳ 12 tháng là 6,30%/năm; gửi 6 tháng rồi gửi tiếp chỉ hoà hoặc hơn khoản khoá 12 tháng khi lãi suất kỳ 6 tháng lần sau từ 6,41%/năm trở lên.

**Level.** OCB online, sheet 06/11/2026, grade verified (table and PDF): 4.75% at 1–5 months, 6.00% at 6 and 9 months, 6.30% at 12 months (`../V-CURVE/CURVE.md` §1). The second verified sheet, shown when the user switches bank: Sacombank counter, under 500 triệu, printed 20/10/2026, 4.50% at 1–5 months, 5.70% at 6 and 9 months, 5.40% at 12 months. System context, in the footnote only: household deposits August 2026, 11,434,266 tỷ đồng, +10.63% so với cuối năm (`../V-MACRO/MACRO.md` §2).

**Benchmark.** Ceiling 4.75%/năm from 1 month to under 6 months, Quyết định 2411/QĐ-NHNN Điều 1, in force 20/11/2024 (`../V-LAW/LAW.md` §2). OCB online sits on it. The Sacombank tier sits 0.25 pp under it. Cap 350,000,000 đồng of principal and interest, one person, one institution, from 13/7/2026 (`../V-LAW/LAW.md` §1). SBV's pre-issuance assessment, not a July recount: 93.68% of depositor records fully covered and 19.06% of value fully covered, on the 31/12/2025 stock (`../B-POLICY/POLICY.md` §3).

**Trend.** No forecast. OCB's own sheet implies a second 6-month rate of 6.41%/năm to tie the 12-month lock (hand check this session 6.4078%). Sacombank's verified tier implies 4.96%/năm (hand check 4.9587%), which is below the 5.70% that sheet already posts, because 12 months at 5.40% sit below 6 months at 5.70%. The two verified curves do not share a direction (`../V-CURVE/CURVE.md` §3). VietinBank's 7.68% stays out.

**Decision.** Money that can stay six months at OCB online earns 6.00% instead of the 4.75% posted at five months, a gap of 1.25 pp on that sheet. Money aimed at twelve months at Sacombank's counter, under 500 triệu, is worse off locked at 5.40% than placed for six months at 5.70%, unless the renewal prints under 4.96%. A balance whose principal plus interest at one institution exceeds 350 triệu has an excess that Thông tư 05 does not cover, and payment of the insured part waits for Luật 111 Điều 21.

## 6. Order of work before 13:00

1. Rewrite the spoken pitch to section 5. Remove 6.25%, 7.00%, 5.20%, the 1.85 pp BIDV gap, the 1.40 pp Sacombank gap, the median kink, Nelson-Siegel, and the national curve.
2. One HTML screen with the anatomy in section 5. Sheet dates visible. Grades visible.
3. The ten-line note on the tax notch (question 21) and the English plus Vietnamese script (question 25).
4. One sceptic recomputes the three numbers on a spreadsheet and tries to put BIDV on the chart. The chart does not gain BIDV.
5. Extras: cut OCR, chat charts and MCP. The planner ships only under the constraints in section 4.

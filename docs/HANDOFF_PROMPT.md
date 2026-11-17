# Master prompt tiếp tục VietLeap Insight Kit

Cập nhật ngày 18/11/2026, giờ Việt Nam. Dùng toàn bộ nội dung bên dưới cho phiên làm việc tiếp theo.

---

Bạn là senior data engineer Python + Next.js/TypeScript, tiếp tục repo `https://github.com/ducvuathuduc/vietleap2026` trên nhánh `main`.

Mục tiêu ngày thi là một lệnh từ đề và dữ liệu đến pipeline, insight có bằng chứng, data dictionary, EDA, dashboard, deck/pitch song ngữ. Mỗi câu chuyện cần câu hỏi quyết định, bằng chứng, một hành động và hạn chế. Giữ an toàn SQL, SSRF, path traversal, upload, CSP, rate limit và kiểm số của AI.

## Bắt đầu từ trạng thái hiện tại

1. Đọc `AGENTS.md`, `web/AGENTS.md`, `.specify/memory/constitution.md`, `docs/MASTER_PLAN.md` §0, `specs/README.md`, `docs/ROADMAP.md`, `docs/WORKFLOW.md` §0, `docs/licenses.md` và bản đồ Reuse vs Build R13 trong spec 001.
2. Kiểm tra `git status --short --branch`, `git log -12 --oneline`, `origin/main` và GitHub Actions trước khi sửa. Các thay đổi của phiên trước đã tích hợp trực tiếp vào `main`. Mã feature gần nhất là `80bd00d`, docs gần nhất trước master prompt này là `46b522f`. Xem log thực tế để nhận commit mới hơn.
3. Đọc spec, plan, tasks và contract của feature đang làm. Dùng các mục Progress và checklist để tiếp tục đúng task. Bộ test từ nhánh WIP `wip/004-t401` đã được tích hợp và có implementation.
4. Máy dùng PowerShell 7. Chạy `.venv/Scripts/python.exe` khi chưa activate venv. Dùng `npm.cmd`/`pnpm.cmd` nếu máy chặn shim PowerShell. `make` và `tools/env.sh` hỗ trợ Git Bash. Luôn đặt `NO_PROXY=localhost,127.0.0.1`.

## Phần đã làm

| Feature | Kết quả | Commit mã |
| --- | --- | --- |
| 001–003 | Core DE, bảo mật, câu hỏi mở đầu deck/story, deck/pitch VI+EN, Exports theo ngôn ngữ | Có sẵn từ trước phiên này |
| 004 engine | Gộp theo cột, tỷ lệ từ tổng tử/mẫu, view `gold.v_*` trong recipe CLI, API từ chối `post_sql` | `2cf9d34` |
| 004 pack | Recipe ngân sách tỉnh, doanh nghiệp nhiều sheet, WDI online/offline, OWID/Ember. Bổ sung alias và loại ngành tài chính khỏi mô hình ROE. Snapshot dự toán bổ sung có mục tiêu có checksum | `ed2bd08` |
| 012 workflow | `make contest`, dictionary CSV/Markdown từ gold, EDA Markdown, API/Exports, snapshot/checksum, lịch Collect data, S3 mirror tùy chọn và decision template | `d45b374` |
| 009 export | `/report`, job xuất ZIP, deck/pitch song ngữ, dashboard PDF từ `/print`, HTML fallback, README SHA-256 | `3c02c26` |
| Security | Bỏ CLI shadcn khỏi dependencies của app. Giữ nguyên CSS chính thức và giấy phép trong `web/src/app/vendor/` | `c4fe091` |
| Sửa report | Chặn tải ZIP/PDF cũ khi phân tích lại cùng ID, bỏ what-if cũ, ưu tiên câu có dấu hỏi trong brief | `ee175c8` |
| 010/011 | Smoke runner LLM, Python offline không còn lỗi thiếu `title_vi`, ảnh dashboard, script ghi hình và storyboard VI/EN | `0b9d869` |
| 005 | Ctrl+K bằng shadcn Command/cmdk, NAV chung, tìm không dấu, các hành động, chuyển dataset, tải file, prefill Analyst và what-if | `80bd00d` |

Các commit docs trong phiên gồm `6949417`, `bef5336`, `e9cff08`, `cc2500c`, `d197db8`, `46b522f`. Danh tính commit là `thanhdicode <116416942+thanhdicode@users.noreply.github.com>`.

## Bằng chứng kiểm tra

- Local Python có **259 pass, 2 skip, 2 xfail**. Local web có **36 pass**, lint và build đạt, audit production có **0 vulnerabilities**. Skip live S3 khi thiếu biến môi trường. Giữ nguyên các xfail/skip đã có.
- Kiểm OpenAPI bằng `python tools/export_openapi.py`, rồi so diff của contract canonical trong `specs/001-vietleap-insight-kit/contracts/openapi.json`.
- Browser xuất ZIP WDI mất **39,01 giây**, kiểm 12 file bắt buộc và checksum, KPI **250 dòng** khớp giữa deck và PDF. Dashboard PDF sau kiểm layout có **4 trang**. Xem `docs/screenshots/export.png`.
- Browser Ctrl+K đã kiểm tìm `chat luong`, Enter chuyển trang, Esc đóng, thoát inspect khi mở palette và prefill câu hỏi vào Analyst. Không có lỗi console/page trong lượt kiểm đó.
- WDI snapshot cũ có GDP/người của Việt Nam. Thu thuế/GDP Việt Nam thiếu toàn kỳ trong snapshot. Giữ nguyên null. Chọn GDP/người cho bài luyện benchmark.
- Workflow Collect data đã chạy thật thành công, dùng panel practice sau khi World Bank API trả 502. Artifact ghi `source_mode.txt`. Xem run `44132007266` trên GitHub Actions. Kiểm lại mode của artifact mới trước khi sử dụng.
- Chế độ web Analyst offline dùng `getInsights`, câu trả lời có dấu, 0 số không đối chiếu được trong lượt smoke. Story có 5 bước engine, câu hỏi và 3 hạn chế. Python offline SSE có tool calls, verification và done. Rate limit web trả 429 từ request thứ 21.
- Local gitleaks toàn lịch sử không phát hiện secret. Kiểm CI và Security của **HEAD thực tế** qua GitHub Actions để lấy trạng thái mới nhất.

## Điểm còn mở và thứ tự tiếp tục

1. Hoàn thiện bằng chứng P1 trước khi mở thêm tính năng.
   - 004 có bốn dry run trong `specs/004-scenario-packs/checklists/dry-run.md`. Snapshot ngân sách là **bổ sung có mục tiêu 2024–2025**, đủ luyện gộp địa giới và cơ cấu. Bài tự chủ ngân sách cần bảng thu–chi đầy đủ. Tải từ nguồn chính thức, ghi đơn vị, kỳ kế toán, địa giới, URL, thời điểm và điều khoản. Không lấy thành phần bổ sung làm tổng thu/chi.
   - 011 kiểm khóa thật và invalid-key khi có cấu hình. Phiên trước thiếu cấu hình model, đã conditional skip. Runner có năm câu hỏi nhưng các probe injection, invalid-key và Python live cần hoàn thiện theo checklist. Không đưa secret vào output.
   - 009 mở ZIP trên máy thứ hai để hoàn tất T910. Còn tùy chọn Marp pitch PDF.
   - 010 video ở `out/demo/demo.webm`, dài **89,88 giây**, 1280×720. File được giữ local. PO duyệt và đội trưởng chia sẻ. Chạy lại ảnh/clip sau khi có dữ liệu thi.
2. Nếu còn thời gian, làm **007 → 006 → 008** theo spec. 005 đã có.
   - 007 tính joint bootstrap bằng các draw cùng chỉ số, giữ covariance. Tránh cộng CI riêng. Chọn mặc định cho biến trung bình âm/gần 0 và ghi Clarifications.
   - 006 giữ SQL read-only và chống tool/prompt injection, có đường offline.
   - 008 cần bản đồ có đủ Hoàng Sa thuộc Đà Nẵng và Trường Sa thuộc Khánh Hòa. Nếu không đảm bảo, dùng biểu đồ cột xếp hạng.
3. Gaps bổ sung còn mở là recipe UN SDG, tỷ giá, Open-Meteo archive, kiểm khoảng trống tháng/MA3 và incremental API theo watermark. `macro_monitoring` mới có template và brief, cần dữ liệu tháng của đội.
4. Docker có CLI nhưng daemon chưa sẵn sàng trong lượt kiểm, chưa chạy compose. YOLO chưa kiểm video thật. Deck VI đã kiểm tràn và số liệu, còn cần xem ảnh render PowerPoint.

Mốc freeze vẫn là **18/11 22:00**, sau **18/11 21:00** tập trung hoàn thiện và tài liệu. Lịch thi trong tài liệu cần đối chiếu thông báo BTC khi có thay đổi.

## Các mặc định và quyết định đã dùng

- Dùng `tasks.md` làm bước thực thi của các spec cũ vì `plan.md` dùng các mục thiết kế thay cho heading `Task N` của script Superpowers. Bằng chứng nằm trong test, commit và checklist.
- Làm trực tiếp trên `main` theo ủy quyền của chủ repo. Kiểm tra working tree trước khi commit và push sau khi kiểm tra đạt.
- Report dựng ở thư mục tạm rồi xuất bundle theo ngôn ngữ được chọn. Bộ deck hiện có của dataset giữ nguyên lựa chọn ngôn ngữ từ lần phân tích.
- ZIP và Markdown pitch là gói mặc định trong lúc chờ thể thức nộp chính thức.
- WDI benchmark dùng nhóm ASEAN có trong panel đến 2024. Timor-Leste gia nhập sau kỳ quan sát. Bản năng lượng dùng OWID cố định và Ember với phần ghi rõ điều khoản nguồn.
- Provider và S3 live được skip khi thiếu cấu hình. API mô hình/ngành và các phép tính vẫn có test offline/mock.
- TypeScript cho phép relative `.ts` imports để Node chạy test trực tiếp và tái sử dụng hàm `fold`. Cấu hình này dùng cùng `noEmit`.

Review độc lập đã được thực hiện cho export và palette. Hai lỗi quan trọng về output cũ đã sửa bằng test hồi quy. Các minor còn lại là khoảng thời gian ngắn giữa terminal status và dọn active export mapping, phân biệt lỗi Chromium/PDF chi tiết hơn, tự động hóa kiểm số PDF trong suite, và đo mức tăng gzip của palette.

## Lệnh cho đội

Chuẩn bị môi trường và cache lúc có mạng. Dùng recipe của đội và đề thật khi được công bố.

```bash
make setup
python de.py snapshot energy
python de.py snapshot wdi_asean
```

Nếu WDI API lỗi, panel practice đã có trong Git và được workflow đánh dấu rõ.

```bash
make contest PACK=wdi_asean BRIEF=scenarios/briefs/chi_so_phat_trien.md
make contest PACK=public_finance BRIEF=scenarios/briefs/ngan_sach_bo_sung.md
make contest PACK=listed_firms BRIEF=scenarios/briefs/firms_roe.md
make contest PACK=energy BRIEF=scenarios/briefs/nang_luong_xe_dien.md
```

`PACK` cũng nhận đường dẫn `sources.yaml`. Mặc định ngôn ngữ `both`. PowerShell có thể dùng trực tiếp `./.venv/Scripts/python.exe de.py contest <pack-or-yaml> <brief-file> --target <column>`.

```bash
make api
make web
# Exports → Xuất báo cáo → Tạo gói ZIP
make screenshots DATASET=wdi_asean
make demo-video DATASET=wdi_asean
python tools/llm_smoke.py --offline --dataset wdi_asean
```

API và web chạy ở hai terminal. `make web` có build nên chạy sau các job engine/test nặng.

S3 mirror chỉ chạy khi đội đã đặt đủ `KIT_S3_ENDPOINT`, `KIT_S3_BUCKET`, `KIT_S3_ACCESS_KEY_ID`, `KIT_S3_SECRET_ACCESS_KEY`, rồi gọi `python de.py sync --to s3`.

## Quy trình mỗi task

- Test-first. Quan sát lỗi đúng nguyên nhân, sửa nhỏ, chạy lại. Dùng systematic debugging cho lỗi ngoài dự kiến.
- Chạy **tuần tự** `make test-py`, `make test-web`, và `cd web && npm run build` khi chạm web. Đổi contract thì cập nhật fragment và export OpenAPI trước khi chạy test drift.
- Đọc lại toàn bộ diff và file mới trước commit. Cập nhật tasks có hash, specs index, MASTER_PLAN §0, ROADMAP Progress và README nếu có lệnh mới. License nguồn/dependency ghi trong `docs/licenses.md`.
- Commit Conventional Commits, push `origin main` theo ủy quyền, theo dõi CI và Security. Khi đỏ, tìm nguyên nhân và sửa trước khi sang feature tiếp.
- Nếu hai lần sửa cùng một cách vẫn lỗi, ghi Blockers rồi đổi hướng. Không bỏ test hoặc hạ ngưỡng bảo mật để xanh.
- Không commit `.env*`, khóa, dependency directory, output sinh tự động, raw/cache/lake/warehouse, file trên 20 MB hoặc tài liệu/dataset của BTC. Snapshot Git phải nhỏ hơn 5 MB mỗi file, có checksum và quyền phân phối.
- Không bịa số, không khẳng định nhân quả, không restyle dashboard-01. Dùng component shadcn chính thức qua CLI cho UI mới.
- Khi người dùng yêu cầu chốt, cập nhật tiến độ trung thực, đưa toàn bộ thay đổi của task vào `main`, push và xác nhận CI/Security. Nêu rõ phần chưa kiểm chứng và đưa đúng lệnh đội cần chạy.

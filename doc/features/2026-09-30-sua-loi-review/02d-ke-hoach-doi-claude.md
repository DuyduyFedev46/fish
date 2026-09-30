# Kế hoạch đội Claude: rà lại phần AGY làm + sửa lỗi P8
> Claude (điều phối) · 2026-09-30 · Duy yêu cầu 30/09: đội Claude thay AGY, và rà lại **toàn bộ** phần AGY đã làm.
> Phiếu giao việc từng lô P8 vẫn là `02c-giao-viec.md`. File này ghi **ai làm gì, theo thứ tự nào, kiểm ở đâu**,
> và prompt để Duy dán vào phiên Claude Code mới (cuối file).

## Đội
| Vai | Agent | Model | Việc |
|---|---|---|---|
| Điều phối | phiên chính | Opus 5.5 | giao việc, **tự chạy lại lệnh kiểm chứng**, đọc migration, gộp báo cáo, commit + push |
| BE | `be-dev` | Sonnet 5.5 | story BE theo TDD, bắt đầu từ test tái hiện đỏ |
| FE | `fe-dev` | Sonnet 5.5 | story FE, kèm spec Playwright |
| Tech Lead | `techlead` | Opus | rà code AGY (bước A); review diff từng lô P8 trước QA |
| QA | `qa-tester` | Sonnet 5.5 | kiểm lại AC P1–P7 bằng chạy thật (bước A); QA từng lô P8 |
| Pháp lý | `legal-vn` | Opus | chỉ khi có câu chữ cho khách hoặc câu hỏi PII (vd tìm SĐT ở CSKH) |

Test tái hiện R1–R6 nằm ở `repro/` (cách chạy: `repro/README.md`).

---

## Bước A — Rà lại toàn bộ phần AGY làm (P1–P7, chỉ đọc code sản phẩm)
Phạm vi: commit `5d26d95..75e5dd3` (82 commit, ~62k dòng). Ba báo cáo `doc/features/2026-09-30-review-p1-p7/` mới
**lấy mẫu**; bước này kiểm **mọi AC** và mọi file. Lỗi đã có story P8 thì không ghi lại (chỉ ghi "trùng SR-xx").

Đầu ra: `doc/features/2026-09-30-ra-soat-agy/` gồm `A1-code.md`, `A2…A5-<hồ sơ>.md`, và `bao-cao-tong.md` do điều phối gộp.

### A1 · `techlead` — rà code (song song với A2–A5)
Đọc `git diff 5d26d95 75e5dd3 -- backend/ frontend/ erp-console/ adapter/`, theo từng app:
- **Phân quyền:** mọi view/action mới có `permission_classes` đúng tầng; không endpoint nào `AllowAny` ngoài `/api/public/`.
- **Rò giá vốn:** serializer, AuditLog `changes`/`note`, CSV/export, lệnh AI. Kiểm cả khoá tiền **chia được cho kg**.
- **Rò PII:** serializer, log (`logger.*`, `print`), prompt AI, `localStorage`/URL phía FE, response không `no-store`.
- **Chứng từ:** không có `.delete()` trên chứng từ, không `update()` hàng loạt vượt service, migration chỉ thêm.
- **Chất lượng test:** test không assert, `assert True`, mock luôn trả đúng, test bị `skip`, test chỉ kiểm status 200.
- **Chất lượng code:** `except Exception: pass` nuốt lỗi, logic tiền/kho bị chép hai nơi, TODO/FIXME, code chết, spike còn sót,
  hard-code secret/URL, N+1 query rõ ràng ở danh sách.
- **Lệch thiết kế:** so với `02b-tech-design.md` từng hồ sơ; các mục đã ghi "Lệch thiết kế" trong `03-dev-notes.md` có hợp lý không.
- **Nghi ngờ chưa xác minh** trong 3 báo cáo review (§3 bảo mật, "Nghi ngờ" tiền-kho-AI): xác minh đến cùng, ghi đúng/sai.

### A2–A5 · `qa-tester` — kiểm lại AC bằng chạy thật (4 agent song song, mỗi agent một hồ sơ)
| Agent | Hồ sơ | Cổng Playwright |
|---|---|---|
| A2 | `2026-09-28-sua-loi-bao-mat` + `2026-09-28-khung-go-live` | frontend 3101, erp 3201 |
| A3 | `2026-09-28-ai-digital-worker` | 3102 / 3202 |
| A4 | `2026-09-28-cskh-xac-nhan-in-tem` | 3103 / 3203 |
| A5 | `2026-09-28-cms-viet-bai` | 3104 / 3204 |

Mỗi agent:
1. Lấy mọi AC trong `02-stories.md` (không chỉ các AC 04-qa-report ghi PASS). Với từng AC: tìm test đang có phủ nó → đọc test
   xem **có thật sự kiểm** AC không → chạy. Không có test hoặc test yếu → viết test mới rồi chạy.
2. AC FE: Playwright hoặc ảnh chụp trình duyệt, 375×667 khi AC nói mobile. Bảng "AC thiếu bằng chứng" trong
   `review-cms-golive-fe-qa.md` là việc bắt buộc.
3. Mỗi AC nghiệp vụ thêm một ca ngoài đường thuận (xem `.claude/agents/qa-tester.md`).
4. Chỉ chạy test của app mình (`manage.py test apps.<app>`) để không tranh DB/cổng với agent khác.
5. Test mới **xanh** → để trong repo (`backend/apps/*/tests/test_ra_soat_*.py`, `*/e2e/ra-soat-*.spec.ts`), coi như bù bằng chứng.
   Test mới **đỏ** (lỗi thật) → **không** để trong `backend/`/`e2e/`; chép vào `doc/features/2026-09-30-ra-soat-agy/repro/`.
6. Ghi `A<n>-<hồ sơ>.md`: bảng AC × (✅ chạy thật / ❌ lỗi / ⏸ không chạy được + lý do / "trùng SR-xx"), bằng chứng từng dòng.

### A6 · điều phối — gộp và chốt
1. Tự chạy lệnh kiểm chứng đầy đủ (dưới) sau khi các agent thêm test: suite phải xanh.
2. Gộp `bao-cao-tong.md`: lỗi mới đánh mã `RA-01…`, mức Critical/High/Medium/Low, bước tái hiện, file, đề xuất sửa.
3. Lỗi mới **không tự sửa**: cần story Duy duyệt. Ghi đề xuất gom thành P9 (hoặc thêm vào lô P8 chưa làm nếu cùng file
   và cùng loại). Có **Critical** → ghi rõ ở đầu báo cáo và vẫn chạy tiếp P8 (P8 đã duyệt, không phụ thuộc).
4. Commit `Rà soát P1–P7 (AGY): <n> AC kiểm lại, <n> lỗi mới, bù <n> test` + push main.

---

## Bước B — P8 sửa lỗi, từng lô
### Vòng một lô
```
git pull → kiểm chứng gốc → be-dev ∥ fe-dev → điều phối chạy lại kiểm chứng
→ techlead review → qa-tester → (REJECTED: giao lại dev) → APPROVED → commit + push main → ☑ 02c
```
Điều phối không đánh "xong" khi chưa dán output lệnh kiểm chứng trong lượt đó.

### Thứ tự và điểm kiểm riêng
| Lô | Song song | Test tái hiện giao kèm | Điều phối tự kiểm thêm | Dừng hỏi Duy khi |
|---|---|---|---|---|
| 1 | be-dev (SR-01, SR-03) ∥ fe-dev (SR-02) | R1 (AI chốt lô bán rồi, job kẹt); SR-01 chưa có repro → be-dev viết test quét trước | `npm ci` sạch ở cả hai FE; quét AuditLog không còn khoá tiền lọt | `@types/node ^22` kéo > 5 file sửa type |
| 2 | be-dev (SR-04+05 cùng commit, SR-06) ∥ fe-dev (SR-07) | — | test quét PII thấy retrieve chạy > 0 lần; `sessionStorage` không có giá mua | quét thấy PII ngoài `customer`/dashboard |
| 3 | be-dev; fe-dev nhỏ (SR-09) | R2, R3, R4, R5 | chạy lại repro 2 lần (job chạy lặp) | — |
| 4 | be-dev | R6 | đọc file migration (chỉ `CreateModel`); `backfill_credit_notes` dry-run trên DB test | migration có thay đổi ngoài 2 model mới; lệch làm tròn BR-BH-15 |
| 5 | be-dev ∥ fe-dev | — | đọc migration; dashboard không còn tên/4 số cuối SĐT với mọi Group | test cũ ngoài S04 đỏ vì bỏ ngoại lệ EXPIRED |
| — | **Báo Duy: đã mở chặn deploy staging** (chỉ deploy khi Duy yêu cầu) | | | |
| 6 | be-dev ∥ fe-dev ∥ qa-tester (Playwright bù) | — | `check-ai-chunks.mjs` exit 0 | — |
| 7 | be-dev ∥ fe-dev | — | build hai FE sau khi xoá spike | — |
| Cuối | `techlead` đối chiếu mã BM/F/RA trong các báo cáo → bảng "đã sửa / còn" ở `bao-cao-tong.md` | | | |

## Lệnh kiểm chứng
```bash
cd backend && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py test \
  && DJANGO_DEBUG=1 env -u DATABASE_URL .venv/bin/python manage.py makemigrations --check --dry-run
cd frontend && npm ci && npx tsc --noEmit && npm run build
cd erp-console && npm ci && npx tsc --noEmit && npm run build && npm test
```
Phiên mới chưa có `.venv`: `cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, rồi
`DJANGO_DEBUG=1 .venv/bin/python manage.py collectstatic --noinput` (test admin cần). Không chạy test song song
(`--parallel` lỗi pickle). Trước SR-02, `erp-console` cần `--legacy-peer-deps` để cài; ghi rõ khi dùng.

## Không làm
Không deploy, không đụng DB staging/production, không chạy `backfill_credit_notes --apply` (chỉ Duy), không sửa
`doc/decisions.md` và `02*.md` đã duyệt, không force-push, không commit `.env`/bí mật/dữ liệu khách thật. AGY tạm dừng.

## Chi phí dự kiến
Code và test chạy Sonnet 5.5 ($2/$10 mỗi triệu token); Opus chỉ dùng cho điều phối và review. Bước A tốn nhất ở 4 agent
QA (mỗi hồ sơ 30–240 AC). P8 mỗi lô thường 3–4 lượt subagent; lô bị REJECTED thêm 1–2 lượt.

---

## Prompt cho Duy dán (phiên Claude Code mới, repo `fish`, nhánh `main`)

**Prompt 1 — chạy hết (bước A rồi P8 Lô 1→7):**
```
Làm theo doc/features/2026-09-30-sua-loi-review/02d-ke-hoach-doi-claude.md, đọc CLAUDE.md trước.
Chạy Bước A (rà lại toàn bộ phần AGY làm, A1–A5 song song, A6 gộp + commit), rồi Bước B: P8 Lô 1 → 7 theo đúng
vòng một lô, mỗi lô QA APPROVED thì commit + push main. Tự chạy lệnh kiểm chứng, dán kết quả, không tin báo cáo
subagent. Gặp điểm dừng trong 02c/02d thì ghi lại, bỏ qua lô đó nếu các lô sau không phụ thuộc, không thì dừng.
Không deploy. Xong thì báo: lỗi mới từ bước A (mức, 1 dòng), lô nào xong, lô nào dừng và vì sao, việc Duy cần làm.
```

**Prompt 2 — chỉ rà soát (bước A):**
```
Làm Bước A trong doc/features/2026-09-30-sua-loi-review/02d-ke-hoach-doi-claude.md (đọc CLAUDE.md trước):
rà lại toàn bộ phần AGY làm, A1–A5 song song, A6 gộp bao-cao-tong.md, commit + push main. Không sửa code sản phẩm.
```

**Prompt 3 — làm tiếp (khi phiên trước dừng giữa chừng):**
```
Tiếp tục kế hoạch doc/features/2026-09-30-sua-loi-review/02d-ke-hoach-doi-claude.md: git pull, xem bước A đã có
bao-cao-tong.md chưa và lô P8 nào đã ☑ trong 02c-giao-viec.md, làm tiếp phần còn lại theo đúng quy trình.
```

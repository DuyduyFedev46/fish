# Giao việc — P8 Sửa lỗi review P1–P7
> Claude (Tech Lead) · 2026-09-30 · Trạng thái: **SẴN SÀNG CODE (Duy 30/09)**
> Người hiện thực: Gemini CLI / Antigravity theo `AGENTS.md`, lệnh `/lam-tinh-nang 2026-09-30-sua-loi-review`.
> Nhánh làm việc: `main` (không dùng `wip/autosave`).

## Điều kiện đầu vào
- `02-stories.md`: ĐÃ DUYỆT (Duy 30/09) · `02b-tech-design.md`: ĐÃ DUYỆT (Duy 30/09)
- P7 đã xong (xem `doc/ke-hoach-tong.md`). **Chặn deploy staging tới khi Lô 1–5 xong.**
- Trước Lô 1: `git pull`; chạy lệnh kiểm chứng BE một lần, ghi số test gốc vào `03-dev-notes.md`.
- Điều phối viên đính kèm mã R1–R6 (test tái hiện của review, ở `repro/` cùng hồ sơ — cách chạy trong `repro/README.md`) khi giao Lô 1, 3, 4 — nếu không có
  file đó thì viết lại theo mô tả "Tái hiện" trong `review-tien-kho-ai.md` và 02b §7.
- Mỗi lô tuần tự, một lô một lượt. Lô 4 và Lô 5 có migration — không chạy song song với hồ sơ khác.

## Lô
| ☐/☑ | Lô | Story | BE / FE | Được sửa (thư mục/file) | Không được đụng | Commit |
|---|---|---|---|---|---|---|
| ☑ | 1 | SR-01, SR-02, SR-03 | BE ∥ FE | `backend/apps/common/cost_keys.py`; `backend/apps/accounts/audit/tests/` (test mới); `backend/apps/ai/execution/safety.py`; `backend/apps/ai/management/commands/run_due_ai_actions.py`; `backend/apps/ai/execution/tests/` (test mới); `erp-console/package.json`, `erp-console/package-lock.json` (chỉ `@types/node`); `frontend/package*.json` chỉ khi `npm ci` cũng lỗi; `03-dev-notes.md` | mọi `migrations/`, `models/`, `cancel_expired_batch`, bản ghi `AuditLog`, phiên bản `next`/`react`/`vitest`/`vite`/`typescript`, `doc/decisions.md`, `02*.md` | `fa4fc37` |
| ☑ | 2 | SR-04 + SR-05 (**cùng commit**), SR-06, SR-07 | BE ∥ FE | `backend/apps/ai/policy/rules.py`, `backend/apps/ai/execution/scrub.py` (chỉ khi cần bỏ cả nhánh), `backend/apps/ai/registry/discovery.py`, `backend/apps/ai/execution/pipeline.py` (chỉ bước 6), `backend/apps/ai/registry/tests/`, `backend/apps/ai/execution/tests/`; `backend/apps/sales/orders/scope.py` (mới), `backend/apps/sales/orders/api.py` (chỉ `get_queryset`), `backend/apps/sales/orders/next_steps.py` (chỉ khối lọc guidance), `backend/apps/ai/actions/services.py` (chỉ khối lọc escalate), `backend/apps/sales/orders/tests/`; `erp-console/features/purchasing/components/NhapLoForm.tsx`, `erp-console/features/purchasing/components/draftStorage.ts` (+ test), hàm logout ở `erp-console/features/auth/`, `erp-console/e2e/` (spec mới); `03-dev-notes.md` | `migrations/`, `models/`, serializer đơn/khách, `SCRUB_FREE_TEXT_KEYS`, danh sách cấm registry, `doc/decisions.md`, `02*.md` | `f6dffb1` |
| ☑ | 3 | SR-08, SR-09, SR-10, SR-11 | BE (+ FE nhỏ SR-09) | `backend/apps/inventory/batches/services.py` (chỉ `check_cancel_expired_batch`, `publish_batch`, hàm đếm đơn mở tách ra), `backend/apps/inventory/batches/next_steps.py` (chỉ `missing` của `cancel_expired`), `backend/apps/delivery/cskh/services.py` (chỉ `record_call`), `backend/apps/sales/payments/auto_confirm.py` (chỉ `_escalate_to_chu` + bộ lọc quét), test mới ở `backend/apps/inventory/batches/tests/`, `backend/apps/delivery/tests/`, `backend/apps/sales/payments/tests/`; `erp-console/features/cskh/` (chỉ xử lý 409 `STALE_STATE` + nút Tải lại); `03-dev-notes.md` | `close_batch`/`check_close_batch` (Lô 5), `cancel_receipt`, `auto_cancel_overdue`, `migrations/`, `models/`, `doc/decisions.md`, `02*.md` | `97ce2f9` |
| ☑ | 4 | SR-12, SR-13, SR-14 | BE | `backend/apps/sales/models/credit_notes.py` (mới), `backend/apps/sales/models/__init__.py` (re-export), `backend/apps/sales/migrations/` (**1 file mới**), `backend/apps/sales/credit_notes/` (mới: `services.py`, `README.md`, `tests/`), `backend/apps/sales/orders/services.py` (chỉ `cancel_paid_order` + docstring), `backend/apps/sales/orders/timeline.py` (thêm sự kiện), `backend/apps/sales/refunds/services.py` (chỉ docstring `confirm_refund`/module), `backend/apps/sales/admin.py` (Admin chỉ đọc), `backend/apps/sales/management/commands/backfill_credit_notes.py` (mới), `backend/apps/reports/services.py` (`batch_pnl` phần doanh thu, `period_pnl`, docstring), `backend/apps/reports/dashboard_api.py` (chỉ `revenue_today`), `backend/apps/reports/tests/`, `backend/apps/sales/README.md`, `backend/apps/reports/README.md`; `doc/business-process-spec.md` (**chỉ** BR-HT-06, BR-HT-10 mới, BR-BC-03, BR-BC-04, bảng "Lãi lỗ theo lô" — văn bản đúng 02b §4.6); `03-dev-notes.md` | `SalesInvoice`/`SalesInvoiceLine`/`SalesInvoiceLineBatch` (không đổi field, không đổi status), migration cũ, `Refund` model, `cskh/services.py`, `doc/decisions.md`, `02*.md` | `f2de55c` |
| ☑ | 5 | SR-15, SR-16, SR-17 | BE ∥ FE | `backend/apps/inventory/models/` (thêm `BatchSupplierReturn`, choice `SUPPLIER_RETURN`), `backend/apps/inventory/migrations/` (**1 file mới**), `backend/apps/inventory/batches/services.py` (`check_close_batch`, `check_cancel_expired_batch`, `cancel_expired_batch` thêm `confirm_qty`, `return_batch_to_supplier` mới), `backend/apps/inventory/batches/api.py` (action mới + `confirm_qty`), `backend/apps/inventory/batches/serializers.py` (input serializer mới), `backend/apps/inventory/batches/next_steps.py`, `backend/apps/inventory/batches/tests/`, test S04 cũ (**chỉ** assert cho phép chốt EXPIRED còn tồn), `backend/apps/delivery/attention_api.py` (khoá mới + điều kiện 403), `backend/apps/reports/services.py` (`batch_pnl`: trả NCC, F11), `backend/apps/reports/dashboard_api.py` (bỏ `customer`, `phone_last4`), `backend/apps/reports/tests/`, `backend/apps/common/cost_keys.py` (nếu Lô 1 chưa có khoá NCC), `backend/apps/inventory/admin.py` (chỉ đọc); `erp-console/features/inventory/`, `erp-console/features/overview/`, `erp-console/e2e/`; `doc/business-process-spec.md` (**chỉ** BR-LO-04, BR-LO-07 mới, BR-MH-08 mới, BR-BC-04 phần NCC, E-10 — văn bản 02b §5.6); `03-dev-notes.md` | quyền mới/migration Group, `landed_unit_cost`/`recompute_landed_cost`, `period_pnl`, `cancel_receipt`, `doc/decisions.md`, `02*.md` | `84eafe4` |
| ☑ | 6 | SR-18, SR-19, SR-20, SR-21 | BE ∥ FE ∥ QA | `backend/apps/content/entries/services.py`, `backend/apps/content/body/sanitize.py`, `backend/apps/content/public/serializers.py`, `backend/apps/content/**/tests/`; `erp-console/app/(console)/content/edit/page.tsx` (chỉ đọc `version` + mở panel lịch sử chỉ đọc), `erp-console/features/content/` (mock phiên bản), `erp-console/features/guidance/components/`, `erp-console/features/ai/messages.ts`, `erp-console/features/ai/runtime/messages.ts` (mới), `erp-console/scripts/check-ai-chunks.mjs` (mới); `frontend/e2e/`, `erp-console/e2e/` (spec QA); `03-dev-notes.md`, `04-qa-report.md` | Tiptap/thư viện mới, API công khai khác, `AiAssistantGate` (chỉ đọc context), `doc/decisions.md`, `02*.md` | `2af87b0` |
| ☐ | 7 | SR-22, SR-23, SR-24 | BE ∥ FE | BE: `backend/apps/ai/actions/services.py` (BM-05, F10), `backend/apps/ai/execution/scrub.py` (BM-07), `backend/apps/ai/execution/pipeline.py` (F07), `backend/apps/delivery/cskh/services.py` (chỉ `escalate_expired_windows`), `backend/apps/sales/payments/auto_confirm.py` (F12), `backend/apps/sales/orders/api.py` + `backend/apps/sales/customers/api.py` (chỉ thêm `NoStoreMixin`), `backend/config/settings.py` (chỉ tách hàm đọc cờ F5), test tương ứng. FE: `frontend/features/content/safeHref.ts` (+test), `frontend/features/content/components/ArticleBody.tsx`, `ItemCard.tsx`, `frontend/features/content/mock.ts`, `frontend/features/checkout/components/`, `frontend/features/site/api.ts`, `frontend/lib/api.ts` (chỉ gộp `getSiteInfo`), xoá `erp-console/app/ai-spike/` + `erp-console/spikes/dw02/`, `erp-console/app/print/label/page.tsx`, `frontend/e2e/`. Doc: `doc/ops/moi-truong.md` (F13); `03-dev-notes.md` | chuyển `content/edit/page.tsx` sang features (để sau), barrel `features/guidance/index.ts` (để sau), `migrations/`, `doc/decisions.md`, `02*.md` | — |

## Mỗi lô: điều kiện xong
- **TDD**: mỗi story có test tái hiện chạy **đỏ trước khi sửa** — dán output đỏ (tên test + dòng lỗi) rồi output xanh vào `03-dev-notes.md`.
- Lệnh kiểm chứng (dán output tóm tắt vào `03-dev-notes.md`, chạy trong đúng lượt báo xong):
  ```bash
  cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
  cd frontend && rm -rf node_modules && npm ci && npx tsc --noEmit && npm run build
  cd erp-console && rm -rf node_modules && npm ci && npx tsc --noEmit && npm run build && npm test
  ```
  `npm ci` phải sạch **không** `--legacy-peer-deps` ở cả `frontend` và `erp-console` (từ Lô 1 trở đi, mọi lô).
  Lô 4, 5: thêm `.venv/bin/python manage.py migrate` trên DB test sạch + đọc lại file migration sinh ra (chỉ `CreateModel`/`AlterField` choices).
  Lô 6: thêm `node erp-console/scripts/check-ai-chunks.mjs` (exit 0).
- Test bắt buộc: ma trận Group trong từng story (`chu`, `quan_ly`, `nv_kho`, `nv_giao`, `cskh`, khách); không rò giá vốn (quét JSON bằng token
  nhóm thiếu `view_costprice`); không rò dữ liệu cá nhân (sentinel PII giả); toàn bộ suite cũ xanh, chỉ sửa đúng assert story nêu tên.
- **Siết QA (review 30/09):**
  - AC phía FE phải có **bằng chứng chạy thật**: Playwright/e2e (ưu tiên) hoặc ảnh chụp từ trình duyệt kèm các bước thao tác. **Không** chấm
    PASS bằng đọc code hay trích số dòng. AC FE không có bằng chứng = FAIL.
  - Mỗi lô có **ca biên/ngoại lệ**, ghi rõ trong `04-qa-report.md`: dữ liệu đã từng bán (lô có phân bổ bán, hoá đơn cũ), màn hình cũ (bấm trên
    dữ liệu đã đổi phía server), chạy job 2 lần, tranh chấp hai thao tác (thứ tự A→B và B→A).
  - Test quét PII/giá vốn phải chứng minh nó thực sự gọi được endpoint (đếm số response 200 > 0), không xanh giả vì lỗi 4xx/5xx.
  - Ảnh chụp và fixture chỉ dùng dữ liệu giả.
- QA APPROVED (`04-qa-report.md`, mục theo lô) → commit tiếng Việt có mã lô + mã story (vd `P8 Lô 1: SR-01 lọc loss_amount, SR-02 npm ci, SR-03 AI chốt lô`) →
  `git push origin main` → đánh ☑ + mã commit ở bảng trên và ở `doc/ke-hoach-tong.md`.

## Điểm dừng hỏi Duy
- Contract/thiết kế không khớp code → ghi "Lệch thiết kế" trong `03-dev-notes.md`, dừng lô.
- Bất kỳ việc nào đụng tiền, giá vốn, phân quyền ngoài phạm vi story.
- SR-02: `@types/node ^22` kéo theo lỗi type cần sửa > 5 file, hoặc `frontend` cũng lỗi peer → ghi và dừng.
- SR-04: test quét tìm thấy PII ở lệnh khác ngoài `customer`/dashboard → dừng, báo (có thể cần allowlist).
- Lô 4: `makemigrations` sinh thay đổi ngoài 2 model mới → dừng. `invoice.amount` ≠ Σ dòng (làm tròn BR-BH-15) làm test lô lệch → ghi, không tự
  đổi công thức.
- Lô 4 SR-14: **không chạy `--apply` trên staging/production** — chỉ Duy chạy (xem dưới).
- Lô 5: test cũ ngoài test S04 bị đỏ vì bỏ ngoại lệ EXPIRED → dừng, liệt kê.

## Việc của Duy sau khi deploy (không phải code)
- Sau deploy Lô 4 lên staging: `manage.py backfill_credit_notes` (dry-run) → xem danh sách → quyết định `--apply`. Lặp lại trên production khi duyệt.
  *(Cập nhật 30/09 theo Duy: chứng từ lập bù ghi vào **kỳ chạy lệnh**, kỳ cũ và lô đã chốt **không đổi số**. Lưu ý: KPI "doanh thu hôm nay" trên dashboard ngày chạy `--apply` sẽ bị trừ toàn bộ số lập bù, có thể âm — nên chạy vào cuối ngày hoặc báo trước người xem dashboard.)*
- Sau Lô 7: đặt biến môi trường theo `doc/ops/moi-truong.md` (staging `AI_PRODUCTION_READY=1`, production giữ `0`/`C`).

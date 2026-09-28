# Giao việc — AI của tôi: nhân viên số, lệnh tự sinh từ API, hướng dẫn theo chứng từ
> Claude (Tech Lead) · 2026-09-28 · Trạng thái: **SẴN SÀNG CODE (Duy duyệt 28/09 — chạy toàn bộ kế hoạch)**
> Người hiện thực: Gemini CLI / Antigravity theo `AGENTS.md`, lệnh `/lam-tinh-nang 2026-09-28-ai-digital-worker` (`.agents/workflows/lam-tinh-nang.md`).
> Nhánh làm việc: `main` (chỉ sau khi hồ sơ `2026-09-28-sua-loi-bao-mat` đã merge `wip/autosave` → `main` ở cuối Lô 2 của nó). `git pull --ff-only origin main` trước mỗi lô.

## Điều kiện đầu vào
- `02-stories.md`: ĐÃ DUYỆT (Duy 28/09, DW-01…DW-27) · `02b-tech-design.md`: ĐÃ DUYỆT (Duy 28/09) · `01-analysis.md`: ĐÃ DUYỆT (28/09) · pháp lý `01c-phap-ly.md`.
- **Việc phải xong trước:** hồ sơ `doc/features/2026-09-28-sua-loi-bao-mat/` ở trạng thái **XONG** (L-1 chốt lô, L-3 lọc giá vốn nhật ký, L-5 throttle, L-6 tra đơn) và đã push `main`. Kiểm: `git log --oneline origin/main | grep -i "sửa lỗi bảo mật"` có commit merge; `backend/apps/inventory/batches/tests/test_l1_close_batch.py` tồn tại trên `main`. Chưa có → **dừng, báo Duy**.
- Trước lô đầu tiên của mỗi phase: chạy lệnh kiểm chứng BE + FE một lần trên `main`, ghi **số test gốc** và bảng **First Load JS** của `erp-console` (`npm run build`) vào `03-dev-notes.md` mục "Mốc trước phase".
- Hồ sơ cũ `2026-09-27-ai-native-erp`: S01/S03 đã code (registry + nhật ký), **S08 runtime đang dở** (gói `@wllama/wllama` chưa cài, `erp-console/features/ai/runtime/wllama.ts` là khung). DW-14 và DW-16 nghiệm thu với LLMock; DW-02 đo model thật bằng harness riêng (Lô 0).
- Không migration nào trong hồ sơ này đổi nghĩa field cũ. Mọi migration sinh bằng `makemigrations` (số thứ tự lấy theo lá hiện tại, **không** tự đặt số cứng — các hồ sơ CSKH/CMS/vai trò có thể chen migration `accounts` trước).

## Phase (Duy chốt 28/09)
| Phase | Lô | Chạy khi | Môi trường bật |
|---|---|---|---|
| P1 | Hồ sơ `sua-loi-bao-mat` | Đang làm | — |
| **P2** | **Lô 1** (DW-03…06, Tiếp theo · Đã làm) **∥ Lô 0** spike (DW-01, DW-02) | Sau P1 XONG | Lô 1: mọi môi trường (không phụ thuộc AI). Lô 0: không đổi hành vi production |
| **P3** | **Lô 2 → Lô 3 → Lô 4** | Lô 0 **đạt** + Lô 1 ☑ | `AI_ENABLED=false` mặc định; ghi chỉ mức C (`AI_WRITE_LEVELS_ALLOWED=C`) |
| P4–P6 | Hồ sơ CSKH, CMS, khung go-live (ngoài file này) | — | — |
| **P7** | **Lô 5 → Lô 6** (cuối cùng) | Sau CSKH/CMS/go-live | **Chỉ staging** tới khi xong S-L1…S-L4. Code mặc định `AI_WRITE_LEVELS_ALLOWED=C`, `AI_PRODUCTION_READY=false`; staging đặt `B` lúc deploy (việc của Duy, không phải của dev) |

## Mặc định và làm rõ thiết kế áp vào giao việc này
Câu hỏi PO (🟡, lấy theo đề xuất; Duy lật được bằng cách sửa dòng này trước khi đổi SẴN SÀNG CODE):

| # | Mặc định dùng để code | Lô |
|---|---|---|
| 🟡 V-DW1 | DW-26 chạy bằng **job Hệ thống** (`actor_kind=system`) **có công tắc riêng của Chủ**, mặc định đóng, chỉ mở được ở staging khi `AI_PRODUCTION_READY=false`. Công tắc là một khoá trong `AiPolicyVersion.red_zone_open` (`"system.auto_confirm_exact_match"`), không cần migration. Hỏi lại Duy một dòng ở đầu Lô 6b trước khi code DW-26. | 6b |
| 🟡 V-DW2 | Huỷ phiếu nhập: người tạo phiếu (phiếu của mình) + `quan_ly`, `chu` (mọi phiếu); chỉ khi mọi lô của phiếu còn DRAFT. | 5a |
| 🟡 V-DW3 | Quyền Tầng 2 mới `inventory.cancel_expired_batch`, chỉ `chu`. | 1c |
| 🟡 V-DW4 | "Tắt AI của tôi" = lệnh ghi rơi về C, lệnh đọc vẫn chạy. | 3b |

Tech Lead làm rõ (không đổi hướng 02b; dev bám theo, lệch thì ghi "Lệch thiết kế"):

| # | Làm rõ | Căn cứ |
|---|---|---|
| TL-1 | **`tao_phieu_hoan` (`sales.refund.create_refund`) trần C ép**, theo 02b §3 (quyền `sales.create_refund`). Bỏ phương án "B cho ca tất định" của 01-analysis §5 dòng 10 (nằm ở "Để sau" của 02-stories). Test: PUT my-config lên B → 400 `BR-AI-19`. | 02b §3, 02-stories "Để sau" |
| TL-2 | Index AuditLog `(model_name, object_id, created_at)` làm ở **Lô 1a** (DW-03 cần cho dòng thời gian), migration `accounts` riêng; 3 field AI của 02b §7.4 làm ở **Lô 3a** bằng migration `accounts` kế tiếp. Tên `accounts/0008_*` trong 02b/DW-11 chỉ là tên dự kiến. | DW-03, DW-11, 02b §7.5 |
| TL-3 | DW-06 **có** migration (02b §7.5 ghi "Lô H0 không migration" là trước khi PO chốt quyền mới): `inventory` AlterModelOptions thêm `cancel_expired_batch` + data migration `accounts` gán `chu` (mẫu `accounts/0006_grant_change_item_image.py`, có `revoke`). | DW-06, V-DW3 |
| TL-4 | DW-06-AC1 "dòng lỗ hết hạn": `reports.services.batch_pnl` thêm **hai khoá hiển thị** `expired_qty`, `expired_cost` (= kg xuất huỷ `WRITE_OFF` do huỷ lô × `landed_unit_cost`), **không cộng vào `total_cost`/`profit`**. Lý do: `purchase_cost` đã tính trên toàn bộ `qty_received`; code hiện có đang cộng thêm `shrinkage_cost`, `damage_cost` theo cách có dấu hiệu tính hai lần (`backend/apps/reports/services.py:46-65`). Lỗi này ghi là **L-10, hỏi Duy riêng**, không sửa trong hồ sơ này. **Cập nhật 28/09 (Duy duyệt L-10):** BR-BC-04 sửa thành lãi/lỗ = doanh thu − (giá mua + chi phí phân bổ), hao hụt/hàng hỏng chỉ hiển thị; sửa ở Lô 3 hồ sơ `2026-09-28-sua-loi-bao-mat` (S06). `expired_qty`/`expired_cost` chỉ hiển thị của DW-06 **nhất quán** với công thức mới (kg hết hạn đã nằm trong `purchase_cost`). Lô 1c chỉ bắt đầu khi Lô 3 đó ☑ trên `main` (cùng sửa `batch_pnl`); khi đó `total_cost` = `purchase_cost + allocated_cost` và test DW-06-AC1 "`profit` không đổi" bám số sau S06. | bất biến 1, "Chủ giữ việc đổi con số lời lỗ" |
| TL-5 | DW-17-AC3 (gửi lại cùng `idempotency_key`): thêm field `PurchaseReceipt.idempotency_key` `CharField(64, null=True, blank=True)` + `UniqueConstraint(created_by, idempotency_key)` có điều kiện `idempotency_key__isnull=False` → migration `purchasing` mới. Lý do (bất biến 8): form tại cảng gửi lại khi mất mạng, không được tạo phiếu thứ hai. | DW-17, 02b §2.5 |
| TL-6 | DW-18: `PurchaseReceipt.Status` chưa có `CANCELLED` → thêm choice `CANCELLED = "CANCELLED", "Đã huỷ"` (vừa `max_length=10`) → migration `purchasing` AlterField. | DW-18 (bất biến 8) |
| TL-7 | FE chưa có trình chạy unit test. **Lô 2** thêm `vitest` (devDependency) + script `"test": "vitest run"` trong `erp-console/package.json`; chỉ dùng cho `features/ai/commands/` và `features/guidance/`. Không thêm thư viện nào khác. | DW-09-AC2 |
| TL-8 | Thiết bị: Duy code bằng Antigravity trên **Mac**. Spike on-device (DW-02) **đo trên máy tham chiếu Android/Windows ≥ 8 GB** (Q4 27/09). Phần đo trên Mac là **số sơ bộ**; phần cần máy thật đánh dấu **"Duy chạy"** (Lô 0 bên dưới). | DW-02, 02b §13 |
| TL-9 | DoD 6 "First Load JS không tăng quá 1 KB": áp cho **code AI** (Lô 0, 2–6). Khối guidance Lô 1 là tính năng thường (chạy khi AI tắt) → không áp trần 1 KB nhưng phải ghi số trước/sau vào `03-dev-notes.md`; route không có khối (vd `/catalog`, `/staff`) phải không đổi. | DoD 6, BR-AI-17 |
| TL-10 | Kỷ luật `required_perms` (DW-08) phủ **19** `@action`: 18 hiện có + `cancel-expired` của DW-06. Từ Lô 2 trở đi mọi `@action` mới (nhập lô, huỷ phiếu nhập, CSKH, CMS…) phải qua test này. | DW-08, 02b §2.7 |

## Lô
Mỗi lô: `be-dev` ∥ `fe-dev` (nếu có cả hai) → tự kiểm → QA → commit + push `main`. Lô con (1a, 1b…) mỗi lô 1–3 story, QA và commit riêng.

| ☐/☑ | Lô | Phase | Story | BE / FE | Được sửa (thư mục/file) | Không được đụng | Commit |
|---|---|---|---|---|---|---|---|
| ☑ | 0-BE | P2 | DW-01 | BE (spike) | `backend/spikes/__init__.py`, `backend/spikes/dw01/` (mới: code spike, test tên `spike_*.py`), `doc/features/2026-09-28-ai-digital-worker/research/02-spike-be.md`, `research/dw01-index.json` (chỉ id/title/kind/group/keywords), `03-dev-notes.md` | toàn bộ `backend/apps/`, `backend/config/`, mọi `migrations/`, `frontend/`, `erp-console/` | `cd74f0f` |
| ☑ | 0-FE | P2 | DW-02 | FE (spike) | `erp-console/spikes/dw02/` (mới: BM25 `.mjs`, harness, `index.json` chép từ DW-01), `erp-console/app/ai-spike/page.tsx` (mới, chỉ hiện khi build có `NEXT_PUBLIC_AI_SPIKE=1`), `research/03-spike-fe.md`, `research/cau-mau-50.json` (50 câu giả + lệnh đúng), `03-dev-notes.md` | `erp-console/features/**` (kể cả `features/ai/runtime/` của S08), `package.json`, `package-lock.json`, `next.config.mjs`, `backend/` | `cd74f0f` |
| ☑ | 1a | P2 | DW-03 | BE ∥ FE | BE: `backend/apps/common/guidance/` (mới), `backend/apps/sales/orders/next_steps.py` (mới), `sales/orders/timeline.py`, `sales/orders/services.py` (chỉ `available_actions` + tách `check_*`), `sales/orders/serializers.py` (chỉ `get_available_actions`), `backend/apps/accounts/models.py` (chỉ `AuditLog.Meta.indexes`), migration `accounts` mới (index), `backend/config/api_urls.py` (route guidance), `backend/config/settings.py` (thêm `AI_ENABLED` nếu chưa có, mặc định `false`), test mới. FE: `erp-console/features/guidance/` (mới), `features/orders/components/OrderDetailView.tsx`, `features/orders/types.ts` | `features/ai/**`, `shared/lib/http.ts`, `apps/ai/**`, `apps/common/audit.py`, `accounts/audit/*` (L-3 đã sửa), migration cũ, test cũ (chỉ thêm) | `5ef773b` |
| ☑ | 1b | P2 | DW-04, DW-05 | BE ∥ FE | BE: `backend/apps/sales/refunds/{next_steps,timeline}.py` (mới), `sales/refunds/services.py` (chỉ `refund_available_actions` + `check_*`), `backend/apps/sales/payments/{next_steps,timeline}.py` (mới), `sales/payments/services.py` (chỉ `payment_available_actions` + `check_*`), `backend/apps/inventory/batches/{next_steps,timeline}.py` (mới), `inventory/batches/services.py` (**chỉ tách** `check_close_batch` ra khỏi `close_batch` đã sửa ở L-1, không đổi hành vi), `apps/common/guidance/` (đăng ký loại mới), `settings.py` (thêm `GUIDANCE_REFUND_WARNING_DAYS=25`), test mới. FE: `features/guidance/`, `features/orders/components/{RefundView,PaymentView}.tsx`, `features/inventory/components/BatchDetailSheet.tsx` (mới), `features/inventory/components/InventoryScreen.tsx` (mở sheet), `features/inventory/{api,mock,types}.ts` | như 1a + `test_l1_close_batch.py` (không sửa), thứ tự FEFO `sellable_batches` | `ea6f2da` |
| ☑ | 1c | P2 | DW-06 | BE ∥ FE | BE: `inventory/batches/services.py` (thêm `cancel_expired_batch` + `check_cancel_expired_batch`), `inventory/batches/api.py` (action `cancel-expired`), `inventory/models/batches.py` (chỉ `Meta.permissions`), migration `inventory` mới + migration `accounts` mới (gán `chu`), `inventory/batches/next_steps.py`, `backend/apps/reports/services.py` (chỉ `batch_pnl` thêm `expired_qty`/`expired_cost` theo TL-4), serializer/test báo cáo tương ứng. FE: `features/inventory/components/BatchDetailSheet.tsx`, `features/inventory/{api,mock,types}.ts`, `features/guidance/` | như 1b + `total_cost`/`profit` của `batch_pnl`, `period_pnl` | `c0c4272` |
| ☑ | 2 | P3 | DW-07, DW-08 ∥ DW-09 | BE ∥ FE | BE: `backend/apps/ai/declare.py`, `apps/ai/registry/` (mới; chuyển code spike DW-01 vào đây rồi xoá `backend/spikes/dw01/`), `apps/ai/policy/` (mới: `rules.py`, `effective.py` bản chưa có cấu hình người dùng), route `ai/commands/index/` + `ai/commands/<id>/` trong `config/api_urls.py`, `apps/common/api.py` (`BusinessModelPermissions` cưỡng chế `required_perms`, mixin qua `DocumentViewSet`), khai `required_perms`/docstring trên 19 action ở `accounts/staff/api.py`, `common/api.py`, `delivery/api.py`, `inventory/{batches,returns,stocktake}/api.py`, `purchasing/receipts/api.py`, `sales/{orders,payments,refunds}/api.py`; `inventory/batches/serializers.py` (`BatchListQuery`) + `get_queryset` lọc; `settings.py` (biến Phụ lục A dùng ở lô này); file snapshot id lệnh. FE: `erp-console/features/ai/commands/` (mới: `index.ts`, `search.ts`, `budget.ts`, `planner.ts`, test `*.test.ts`), `features/ai/mock.ts` (thêm chỉ mục giả ~20 lệnh), `features/ai/types.ts` (thêm kiểu, **chưa** xoá kiểu cũ), `erp-console/package.json` + `package-lock.json` (chỉ `vitest` + script `test`, TL-7); xoá `erp-console/app/ai-spike/` và `erp-console/spikes/` | `apps/ai/commands/` (registry S01 + `GET /api/commands/catalog/` **giữ y JSON cũ**, 7 test `test_catalog.py` xanh), `features/ai/runtime/`, `features/ai/commands.ts` cũ, mọi `migrations/`, thân nghiệp vụ của action (chỉ thêm khai báo) | đang commit |
| ☐ | 3a | P3 | DW-10, DW-11 | BE ∥ FE | BE: `apps/ai/models/` (mới: `config.py`, `policy.py`, `actions.py`), migration `ai/0001_initial`, `ai/0002_grant_manage_ai_policy`, migration `accounts` mới (3 field AI, TL-2), `apps/ai/execution/` (mới: `pipeline.py`, `dispatch.py`, `scrub.py`, `api.py`), `apps/ai/actions/` (mới), `apps/common/audit.py` (contextvar `ai_audit_scope`, chữ ký `record_audit` không đổi), `accounts/models.py` (3 field AuditLog), `apps/ai/admin.py` (chỉ đọc), `config/api_urls.py`, `settings.py`; `inventory/stocktake/` chỉ khi cần cho H6 (DW-11-AC6). FE: `features/ai/actions/` (mới, màn "Việc AI"), `features/ai/commands/call.ts`, `features/ai/{types,mock}.ts`, route mới `erp-console/app/(console)/ai/actions/page.tsx`, menu trong `app/(console)/layout.tsx` (chỉ thêm mục) | `record_audit` chữ ký, dữ liệu `AuditLog` cũ, `apps/ai/commands/` (chưa xoá), `features/ai/runtime/` | — |
| ☐ | 3b | P3 | DW-12, DW-13 | BE ∥ FE | BE: `apps/ai/settings/` (mới: `services.py`, `api.py`, `serializers.py`, test), `apps/ai/policy/effective.py` (đọc cấu hình + chính sách), `config/api_urls.py`. FE: `features/ai/settings/` (AI của tôi), `features/ai/policy/` (tắt khẩn + xem cấu hình; **chưa** phần vùng đỏ/trần), route `app/(console)/ai/{settings,policy}/page.tsx`, menu | Endpoint sửa cấu hình người khác (không được tạo — DW-12-AC8), phần `red_zone`/`caps` ghi (Lô 5a/6a) | — |
| ☐ | 3c | P3 | DW-14, DW-15 (+ DW-16 nếu S08 xong) | BE ∥ FE | BE: `apps/common/guidance/` (trường `ai` của bước), xoá `apps/ai/commands/{registry,api,serializers}.py` + `tests/test_catalog.py` + route `commands/catalog/` (DW-15), chuyển ý `test_registry.py` sang registry tự sinh; `keywords` (tên lệnh cũ) trên view theo Phụ lục B. FE: `features/ai/components/AiAssistantPanel.tsx`, `features/ai/commands/`, `features/guidance/` (nút "Để AI làm", "Tóm tắt"), xoá `getCommandCatalog`/`CommandSpec`/mock catalog/`features/ai/commands.ts` | `features/ai/runtime/` (S08 là hồ sơ 27/09; chỉ gọi, không sửa) | — |
| ☐ | 4 | P3 | DW-17 | BE ∥ FE | BE: `purchasing/receipts/{api,serializers,services}.py` (action `nhap-lo`, `NhapLoInput`, `NhapLoOutput`, `create_and_submit_receipt`), `purchasing/models/receipts.py` (chỉ `idempotency_key` + constraint, TL-5), migration `purchasing` mới, test. FE: `features/purchasing/` (mới) + route `app/(console)/purchasing/page.tsx` (thay nội dung cũ nếu là placeholder), `features/ai/` chỉ phần gọi descriptor cho form | `PurchaseReceiptLine.rate` nghĩa cũ, Django Admin nhập lô (giữ song song) | — |
| ☐ | 5a | P7 | DW-18, DW-20 | BE ∥ FE | BE: `purchasing/receipts/{api,services}.py` (action `cancel`), `purchasing/models/receipts.py` (choice `CANCELLED`, TL-6), migration `purchasing` mới, `inventory/batches/services.py` (chỉ hàm huỷ lô DRAFT do phiếu huỷ + bút toán đảo), `apps/ai/settings/` (PUT `caps`), `apps/ai/policy/`. FE: `features/purchasing/` (nút Huỷ), `features/ai/policy/` (trần) | Xoá dòng sổ kho / phiếu (chỉ bút toán đảo), `.env*` | — |
| ☐ | 5b | P7 | DW-19, DW-21 | BE ∥ FE | BE: `apps/ai/execution/` (mức B, ngưỡng, hạn mức ngày, hạ mức), `apps/ai/actions/` (undo, huỷ lịch), management command mới `apps/ai/management/commands/run_due_ai_actions.py`, `settings.py`. FE: `features/ai/actions/` (thông báo "AI đã ghi", đếm ngược hoàn tác/lịch), `features/ai/settings/` (chọn B khi env cho phép) | Tạo Cloud Scheduler / cron thật (việc deploy của Duy), `_force_auth_user` dùng ngoài job | — |
| ☐ | 5c | P7 | DW-22, DW-23 | BE ∥ FE | BE: `apps/ai/actions/` (escalate, nhắc quá hạn trong job), `apps/ai/report/` (mới) + route. FE: `features/ai/actions/` (tab "Được chuyển", nút "Nhờ" trên `features/guidance/`), `features/ai/report/` (mới) + route | Gửi thông báo ra kênh ngoài ERP (H14) | — |
| ☐ | 6a | P7 | DW-24, DW-25 | BE ∥ FE | BE: `apps/ai/policy/` (công tắc vùng đỏ), `apps/ai/settings/`, luật tất định chốt lô trong `apps/ai/execution/` dùng `check_close_batch`. FE: `features/ai/policy/` (phần vùng đỏ) | `close_batch` (chỉ gọi, không sửa), `AI_PRODUCTION_READY` mặc định | — |
| ☐ | 6b | P7 | DW-27, DW-26 | BE | `apps/ai/execution/` (luật `confirm_refund` luôn hạ C + chuyển việc), job mới cho DW-26 trong `apps/sales/payments/` (**dùng service ghi tiền hiện có**, không viết đường ghi tiền mới), `apps/ai/policy/` (công tắc V-DW1) | Đường xác nhận thanh toán hiện có (chỉ gọi), `adapter/`, `raw_payload` | — |

Luôn **không được đụng** ở mọi lô: `doc/decisions.md`, `01-analysis.md`, `02-stories.md`, `02b-tech-design.md`, `02c-giao-viec.md` (trừ ô ☐/☑ + mã commit), migration đã có, `.env*`, `frontend/` (Shop), `adapter/`, `firebase*.json`, test cũ (chỉ thêm; sửa có chủ đích phải ghi lý do trong `03-dev-notes.md`). Không deploy, không `gcloud`/`firebase deploy`, không đụng DB staging/production.

## Lệnh kiểm chứng chung (dán output tóm tắt vào `03-dev-notes.md` mỗi lô)
```bash
cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
cd erp-console && ./node_modules/.bin/tsc --noEmit && npm run build          # ghi bảng First Load JS
cd erp-console && npm test                                                  # từ Lô 2 (vitest)
grep -rn 'fields = "__all__"' backend/apps                                  # phải rỗng
grep -rnE "console\.(log|info|debug)|localStorage" erp-console/features/guidance erp-console/features/ai/commands erp-console/features/ai/actions erp-console/features/ai/settings erp-console/features/ai/policy   # phải rỗng (được phép console.error không kèm dữ liệu)
git status --short                                                          # không .env, DB, ảnh chụp, khoá
```
Lô có migration thêm: `manage.py migrate` rồi `manage.py migrate <app> <migration trước>` rồi `migrate` lại trên DB dev cục bộ (không staging/production) — dán output.

## Test bắt buộc chung (mọi lô có BE)
- **Ma trận Group 02b §11.3** bằng token từng Group `chu`, `quan_ly`, `nv_kho`, `nv_giao` (fixture `apps/common/tests/fixtures.py`); thêm `cskh` khi Group đó có trên `main` (trước đó dùng Group fixture tạo trong test, DW-12-AC10). Mỗi endpoint mới: happy path, 403 thiếu quyền (dữ liệu không đổi), 401 chưa đăng nhập, 400 `BusinessError` có mã BR.
- **Không rò giá vốn:** gọi bằng `quan_ly`/`nv_kho`/`nv_giao`, assert không có khoá `purchase_rate`, `landed_unit_cost`, `rate`, `unit_cost`, `profit`, `margin`, `cogs` ở **mọi độ sâu** và chuỗi JSON không chứa con số giá vốn mẫu (vd `987654.3210`).
- **Không rò PII:** fixture dùng PII giả chuẩn ("Khach Thu Nghiem", "0900000123", "1 Duong Gia, Q.Test", nội dung CK giả); assert chuỗi không có trong response, `AiAction`, `AuditLog.detail/changes` mới ghi, log (`assertLogs`) — **với cả `chu`** cho endpoint guidance và lệnh AI.
- **AI tắt vẫn chạy:** `override_settings(AI_ENABLED=False)` cho mọi màn/endpoint nghiệp vụ của lô (BR-AI-10); `/api/ai/commands/*` → 410, guidance → 200.
- **Test kỷ luật tự đăng ký** (từ Lô 2): `test_moi_custom_action_co_required_perms`, `test_required_perms_khop_require_perm`, `test_action_ghi_co_docstring_tieng_viet`, `test_id_lenh_on_dinh`, `test_form_only_bao_cao`, `test_feature_moi_khong_khai_gi` (02b §11.2) chạy xanh ở **mọi lô sau Lô 2**.
- Mỗi AC có ít nhất 1 test tự động, tên/ docstring ghi mã `DW-xx-ACy`.

---

## Lô 0 — Spike (P2, song song Lô 1; không đổi hành vi production)

### 0-BE · DW-01 (be-dev)
- Code spike ở `backend/spikes/dw01/` (package thường, **không** vào `INSTALLED_APPS`): `serializer_to_schema` thử nghiệm, duyệt `get_resolver()`, dispatch trong tiến trình (02b §4.3). Test đặt tên `spike_*.py` để `manage.py test` mặc định **không** chạy.
- Đầu ra: `research/02-spike-be.md` (tổng số lệnh sau lọc §3, số `form_only`, kiểu field chưa hỗ trợ, phân bố `schema_tokens_est`, id lệnh thật đối chiếu Phụ lục B, `schema_tokens_est` của `nhap_lo` dựng thử từ ví dụ 02b §2.5) và `research/dw01-index.json` (chỉ `id,title,kind,group,keywords` — không PII, không giá vốn).
- Lệnh kiểm chứng:
  ```bash
  cd backend && .venv/bin/python manage.py test spikes.dw01 --pattern="spike_*.py" -v 2
  cd backend && .venv/bin/python manage.py test          # số test = mốc gốc, không đổi
  git diff --stat origin/main -- backend/apps backend/config   # phải rỗng
  ```
- Test bắt buộc: DW-01-AC2 chạy lại `inventory/batches/tests/test_api.py` + test API đơn hàng qua dispatch → cùng mã HTTP, cùng JSON, cùng số dòng AuditLog; AC3 `nv_kho` không có `purchase_rate`/`landed_unit_cost`; AC4 user bị vô hiệu (BR-PQ-19) bị chặn cùng mã.
- Xong khi: báo cáo đủ AC1–AC6; tiêu chí **đạt/không đạt** ghi rõ từng dòng.

### 0-FE · DW-02 (fe-dev + Duy)
- Harness: `erp-console/spikes/dw02/` + trang `erp-console/app/ai-spike/page.tsx` nằm **ngoài** `(console)` (không cần đăng nhập, không gọi backend). Trang chỉ nạp harness (`next/dynamic`) khi build có `NEXT_PUBLIC_AI_SPIKE=1`; build thường hiện "Không có trang này". Chỉ mục lấy từ `spikes/dw02/index.json` (chép `research/dw01-index.json`). wllama nạp bằng import động `webpackIgnore` từ CDN như khung S08 (`features/ai/runtime/wllama.ts`) — **không** `npm i`, không sửa `features/ai/runtime/`. GGUF qua `NEXT_PUBLIC_AI_MODEL_GGUF_URL` (Hugging Face).
- Bộ 50 câu giả `research/cau-mau-50.json` (câu tiếng Việt + id lệnh đúng + args đúng), không dữ liệu thật.
- **Phân việc theo máy (TL-8):**

  | Đo | Máy dev (Mac, fe-dev làm) | Máy tham chiếu Android/Windows ≥ 8 GB (**Duy chạy**) |
  |---|---|---|
  | AC3 recall@3/@5, `margin` top-1/top-2 (BM25 bỏ dấu) | ✓ số chính thức (không phụ thuộc máy): `node erp-console/spikes/dw02/recall.mjs` | — |
  | AC1 tỉ lệ chọn đúng N = 3/5 (E2B/E4B, 2048/4096) | ✓ số sơ bộ | ✓ chạy lại 50 câu E2B ở 2048 để xác nhận; **độ trễ token đầu, RAM đỉnh** |
  | AC2 args qua serializer (`nhap_lo`, `inventory.batch.list`) | ✓ sinh args; kiểm bằng serializer ở backend dev (`manage.py shell` gọi `is_valid`) | — |
  | AC4 kích thước prompt bằng tokenizer Gemma thật | ✓ số chính thức (tokenizer tất định) | — |
  | AC4 200 lượt liên tiếp ở 2048 và 4096, crash tab, rò bộ nhớ worker | — | ✓ (Android: `adb reverse tcp:3100 tcp:3100` rồi mở `http://localhost:3100/ai-spike/` trên Chrome điện thoại để có secure context; Windows: clone repo, `NEXT_PUBLIC_AI_SPIKE=1 npm run dev`) |

  fe-dev viết sẵn trong `research/03-spike-fe.md` mục "Hướng dẫn Duy chạy" (lệnh, bấm gì, chép số nào vào đâu) và để trống cột máy tham chiếu.
- Lệnh kiểm chứng:
  ```bash
  node erp-console/spikes/dw02/recall.mjs                        # in recall@3, recall@5, margin
  cd erp-console && ./node_modules/.bin/tsc --noEmit && npm run build   # build thường: bảng First Load JS các route cũ không đổi
  cd erp-console && NEXT_PUBLIC_AI_SPIKE=1 npm run dev                  # chạy harness trên Mac
  ```
- Xong khi: `03-spike-fe.md` có số Mac + số máy tham chiếu (Duy điền) và bảng §5.3 đề xuất cập nhật.

### Lô 0 — điều kiện xong + điểm dừng
- Tiêu chí đạt: 100% lệnh đọc có schema; schema `nhap_lo` ≤ 450 token; dispatch khớp 100%; chọn đúng ≥ 90% ở N ≤ 5; args hợp lệ ≥ 90%; recall@5 ≥ 95%; 0 crash, không prompt > 80% n_ctx.
- **Không đạt bất kỳ tiêu chí nào → dừng, không mở Lô 2** (DW-01-AC5, DW-02-AC5). Claude (Tech Lead) cập nhật 02b trước, PO chỉnh con số AC.
- Không QA APPROVED theo nghĩa thường: qa-tester chỉ kiểm AC6 (không PII, không ghi prompt ra console/file) và `git diff` không đụng code sản phẩm. Commit: `Lô 0 AI: DW-01 spike BE, DW-02 spike FE (số Mac)`; số máy tham chiếu commit sau khi Duy điền.

---

## Lô 1 — Tiếp theo · Đã làm (P2, không phụ thuộc AI)
Contract: 02b §6.7 `GET /api/guidance/<loại>/<id>/`, loại `order | refund | payment | batch`. Không nằm dưới `/api/ai/`, **không bao giờ trả 410**. Quyền = T1 `view_<model>` + scope T3 **giống hệt** API chi tiết tương ứng (gọi cùng `get_queryset`/`get_object`), không mở `/api/audit-logs/` cho NV kho/NV giao. Trường `ai` của bước luôn `null` ở Lô 1 (lớp AI chưa có). FE mock theo contract (`features/guidance/mock.ts`), 3 trạng thái tải/lỗi-có-thử-lại/rỗng; lỗi khối không làm hỏng phần còn lại của màn.

### 1a · DW-03 (dựng khung)
- BE: `apps/common/guidance/` gồm `steps.py` (`NextStep`, `Missing`), `reasons.py` (câu "vì sao" theo mã BR, không số tiền), khung dòng thời gian, `api.py` (đăng ký loại), README. Đơn: `sales/orders/next_steps.py`; `available_actions` tính lại từ `next_steps` (`[s.key for s in steps if s.allowed]`). Sửa L-4: dòng `actor_kind=ai` hiện "AI của <tên hiển thị>" + mức, không phải "Hệ thống"; `config_version` chỉ khi người xem có `ai.manage_ai_policy` (quyền chưa tồn tại → không bao giờ có ở lô này). `related`/`timeline` gộp đơn, hoá đơn, phiếu giao, phiếu hoàn (Q-M16).
- Migration: `accounts` AddIndex `(model_name, object_id, created_at)` (TL-2).
- FE: `features/guidance/components/` (khối Tiếp theo + Đã làm) gắn vào `OrderDetailView.tsx`; bấm thao tác bị 400 → hiện thông điệp + mã BR, tải lại khối đúng 1 lần (AC8).
- Test bắt buộc: **so `available_actions` cũ = mới** trên fixture đơn mọi trạng thái × 4 Group, chạy **trước** khi đổi (chụp kết quả cũ thành hằng số test) và sau; mỗi bước `allowed=true` gọi thao tác thật không 400 (AC2); AC5 PII với token `chu`; AC6 giá vốn; AC7 403/404 cùng mã API chi tiết; AC9 AI tắt; AC10 quét `reasons.py`; AC11 FE lỗi mạng/500. Test cũ `test_s10_api.py`, `test_s14_cancel_paid_order.py` xanh không sửa.
- Commit: `Lô 1a AI: DW-03 khối Tiếp theo · Đã làm trên đơn (+L-4)`.

### 1b · DW-04, DW-05
- BE: phiếu hoàn + giao dịch lệch (`payment`) + lô. Cảnh báo phiếu hoàn gần hạn đọc `GUIDANCE_REFUND_WARNING_DAYS` (mặc định 25). Lô: bước hệ thống "chuyển Cận hạn" dùng `BATCH_NEAR_EXPIRY_DAYS`; dòng thời gian = AuditLog + `StockLedgerEntry` + mốc trạng thái; khoá giá vốn và câu có số chỉ cho người có `view_costprice` (dùng bộ lọc `apps/common/cost_keys.py` của L-3, **không** viết danh sách khoá thứ hai).
- **`check_close_batch`**: tách nguyên văn các phép kiểm L-1 khỏi `close_batch` (service gọi `check_close_batch` rồi raise phần tử đầu). `test_l1_close_batch.py` phải xanh **không sửa**. Nếu vì lý do nào L-1 chưa có trên `main` khi Duy cho chạy lô này: bước "Chốt lô" luôn `allowed=false`, `missing` = "Chủ chốt lô trên màn lô cũ", ghi nợ trong `03-dev-notes.md` (DW-05 phụ thuộc cứng).
- FE: khối trên `RefundView.tsx`, `PaymentView.tsx`; `BatchDetailSheet.tsx` mới mở từ `InventoryScreen.tsx` (màn lô hiện chưa có chi tiết).
- Test bắt buộc: DW-04-AC3 và DW-05-AC2 (so `available_actions` cũ = mới; bước `allowed=true` chạy không 400; gọi thẳng `close` nhận 400 BR-LO-04 cùng thông điệp với `missing`); DW-04-AC4 `raw_payload`/nội dung CK/tên người chuyển giả không có trong response token `chu`; DW-05-AC3/AC4 `quan_ly`, `nv_kho` thấy "Chủ đã chốt lô" không số, `chu` thấy số; DW-05-AC5 `nv_giao` 403; DW-05-AC6 PII trong dòng sổ kho; AI tắt.
- Commit: `Lô 1b AI: DW-04 phiếu hoàn + giao dịch lệch, DW-05 lô`.

### 1c · DW-06
- BE: `POST /api/inventory/batches/<pk>/cancel-expired/` theo contract DW-06; service `cancel_expired_batch(*, batch, actor)` trong `transaction.atomic` + `select_for_update()` **trước** mọi phép kiểm, ghi `StockLedgerEntry` `WRITE_OFF` âm đúng tồn còn lại (append-only), `status=CANCELLED`, `record_audit`. Quyền Tầng 2 `inventory.cancel_expired_batch` (V-DW3) — `require_perm` trong thân action. `batch_pnl` thêm `expired_qty`, `expired_cost` **không đổi `total_cost`/`profit`** (TL-4). Guidance lô: EXPIRED → bước "Huỷ lô" (`allowed` theo quyền); CANCELLED → bước kế "Chốt lô".
- Migration: `inventory` AlterModelOptions (thêm permission) + `accounts` data migration gán `chu`, có `revoke` (TL-3). Kiểm migrate xuống/lên.
- FE: nút "Huỷ lô" trên `BatchDetailSheet.tsx` chỉ hiện khi bước `cancel_expired` `allowed=true`; hộp xác nhận nêu mã lô + số kg (không số tiền); chặn bấm đúp.
- Test bắt buộc: AC1 (sổ kho 1 dòng, AuditLog 1 dòng, `batch_pnl.expired_cost` = kg × `landed_unit_cost`, `profit` **không đổi** so với trước huỷ); AC2 SELLING/NEAR_EXPIRY → 400 BR-LO-03, không đổi; AC3 hai request tranh nhau → đúng 1 thành công (dùng `TransactionTestCase` + 2 thread, hoặc gọi service 2 lần sau khi lần 1 xong và assert lần 2 400 + chứng minh `select_for_update` bằng test khoá như L-1); AC4 `quan_ly`/`nv_kho`/`nv_giao` 403, khách 401; AC5 `quan_ly` xem timeline không số; AC6 guidance; AC7 AI tắt; test migration: `chu` có quyền, 3 Group còn lại không.
- Commit: `Lô 1c AI: DW-06 Chủ huỷ lô quá hạn (BR-LO-03)`.

### Lô 1 — điều kiện xong
- Lệnh kiểm chứng chung + `cd backend && .venv/bin/python manage.py test apps.common apps.sales apps.inventory apps.reports apps.accounts`.
- QA APPROVED (`04-qa-report.md` mục Lô 1a/1b/1c): kiểm từng AC bằng token từng Group; E2E Python ở `erp-console/e2e/` (mới `dw03_dw06_guidance.py`) chạy với `NEXT_PUBLIC_USE_MOCK=1`: khối hiện đủ khi guidance lỗi/500 thì màn vẫn dùng được; ảnh chụp chỉ dữ liệu giả.
- Bảng First Load JS trước/sau (TL-9).

---

## Lô 2 — Tự đăng ký lệnh + chỉ mục + chọn lệnh 2 bước (P3)
Chỉ mở khi Lô 0 **đạt** (hoặc Duy đã quyết phương án khác) và Lô 1 ☑.
- BE DW-07 → DW-08: registry tự sinh (02b §2), luật chặn tất định `apps/ai/policy/rules.py` (02b §3, hằng số trong code), `effective_level` bản không cấu hình (AI_ENABLED, cấm, quyền thật qua `permission_classes` + `required_perms`, `max_level`, env `AI_WRITE_LEVELS_ALLOWED` mặc định `C`). Endpoint index/descriptor theo 02b §6.2 (410 khi `AI_ENABLED=false`; 404 `COMMAND_UNKNOWN` cùng thân cho "không có"/"không quyền"). `BusinessModelPermissions` cưỡng chế `required_perms` **trước** thân action, 403 **cùng thân** như `require_perm` cũ. `list_query_serializer` cho lô (`item_code`, `status`) dùng chung cho màn lô, giữ thứ tự FEFO.
- FE DW-09 (mock theo contract 02b §6.2, chỉ mục giả ~20 lệnh, và bộ 150 lệnh giả cho test ngân sách): `index.ts` (giữ trong bộ nhớ, tải lại khi đổi `index_version`), `search.ts` (BM25 từ spike, `margin`/K theo kết quả DW-02), `budget.ts`, `planner.ts` chạy LLMock; chunk AI lazy, route không AI không tăng > 1 KB.
- Test bắt buộc: DW-07-AC1 snapshot id lệnh; **AC2 `test_feature_moi_khong_khai_gi`** (02b §11.2); AC3 danh sách chặn + tập `red_zone` đúng bằng các action có `close_batch`/`confirm_refund`/`confirm_payment_manual`; AC4 ma trận 4 Group; AC5 `output_fields` giá vốn; AC6 PII; AC7 ngân sách; **AC8 `assertNumQueries`/bắt SQL chỉ bảng `auth_*`/`ai_*`**; AC9 410 + 7 test `test_catalog.py` xanh nguyên; AC10 lọc lô. DW-08-AC1…AC7 (bỏ khai một action thử → fail in tên; số test ≥ mốc; 403 cùng thân). DW-09-AC2 vitest: 50 câu × n_ctx 2048/4096, mọi prompt ≤ 80% n_ctx, lượt A ≤ 5 tên, lượt B ≤ 1/2 schema, không id ngoài top-K; AC7 không `console`/`localStorage`/URL.
- Kiểm chứng thêm: `cd erp-console && npm test`; `grep -rn "ai.manage_ai_policy\|/api/ai/" backend/apps/ai/policy/rules.py` có trong danh sách cấm.
- Commit: `Lô 2 AI: DW-07 lệnh tự sinh + chỉ mục, DW-08 required_perms + test kỷ luật, DW-09 chọn lệnh 2 bước`.

## Lô 3 — Mức C + AI của tôi + tắt khẩn (P3). Env mọi môi trường: `AI_WRITE_LEVELS_ALLOWED=C`
### 3a · DW-10, DW-11
- Model + migration theo 02b §7.1–7.3 (`AiConfigVersion`, `AiPolicyVersion`, `AiAction`; `default_permissions = ()`; không API sửa/xoá; Admin chỉ đọc) + `ai/0002` gán `manage_ai_policy` cho `chu` (có rollback) + migration `accounts` 3 field AI (TL-2). `call` theo 02b §4.2 (đọc A, ghi C; throttle `AI_CALL_RATE`), dispatch 02b §4.3, lọc kết quả `scrub.py` (PII đệ quy kể cả `chu`, chữ tự do, giá vốn lưới hai, cắt 20 dòng/3.000 ký tự). `actions` confirm (nonce + `viewed_at` ≥ `AI_CONFIRM_MIN_SECONDS`, chạy bằng token người duyệt) / reject. Contextvar audit reset trong `finally`.
- FE: màn "Việc AI" (`/ai/actions`), `call.ts`.
- Test bắt buộc: DW-10-AC2/AC3 **quét toàn registry** mọi lệnh đọc × 4 Group (+`cskh` fixture) trên fixture PII giả; AC4 chữ tự do; AC5 IDOR `nv_giao`; AC7 idempotency; AC10 contextvar không dính sang request UI; DW-11-AC3 (3 giây, đã quyết, hết hạn — chứng từ không đổi); AC6 H6 kiểm kê; AC7 `args_preview` không `rate` với người thiếu `view_costprice`; AC8 `target` chỉ loại + mã; AC9 AI tắt: confirm 410, reject/GET chạy.
- Commit: `Lô 3a AI: DW-10 lệnh đọc mức A, DW-11 nháp C + Việc AI`.
### 3b · DW-12, DW-13
- Contract 02b §6.5, §6.6 (chỉ `global_mode`, kill theo user, xem cấu hình; **chưa** `red_zone`/`caps` ghi). Phiên bản append-only, `select_for_update` + `base_version` → 409. V-DW4: kill → lệnh ghi về C, lệnh đọc vẫn chạy. Không có endpoint sửa cấu hình người khác (PUT `/api/ai/policy/users/<id>/config/` → 405).
- Test bắt buộc: DW-12-AC2 hiệu lực tức thì; AC4 H1; AC5 đổi Group; AC7 vùng đỏ `choices=["OFF","C"]`; **AC10 grep code lớp AI không so tên Group** (`grep -rnE "\"(chu|quan_ly|nv_kho|nv_giao|cskh)\"" backend/apps/ai --include=*.py | grep -v tests` rỗng, trừ migration `ai/0002`); DW-13-AC5 migration chỉ gán `chu`, rollback gỡ; AC7 append-only.
- Commit: `Lô 3b AI: DW-12 AI của tôi, DW-13 tắt khẩn + chính sách`.
### 3c · DW-14, DW-15 (+ DW-16 khi S08 xong)
- DW-14 với LLMock; trường `ai` của bước guidance = `effective_level` (cùng hàm chỉ mục). DW-15 xoá registry S01 + catalog theo 02b §9.1 bước 2–3 và Phụ lục B; `test_registry.py` giữ ý chuyển đích. DW-16 chỉ làm khi S08 runtime chạy được; không thì ghi nợ, không chặn commit 3c.
- Test bắt buộc: DW-14-AC4 payload gửi LLMock không khoá giá vốn; AC5 không PII; AC7 máy không model không đẩy cloud; DW-15-AC1 `GET /api/commands/catalog/` 404; AC2 đối chiếu 12 lệnh cũ × 4 Group; AC4.
- Commit: `Lô 3c AI: DW-14 chat qua call + Để AI làm, DW-15 gỡ catalog cũ`.

## Lô 4 — Nhập lô trên ERP (P3) · DW-17
- Action `nhap-lo` + `create_and_submit_receipt` theo 02b §2.5 + `idempotency_key` (TL-5). Lệnh AI tự sinh trần C, `locked_reason=AI_UNDO_MISSING` (chưa có action huỷ). Form FE dùng chung action; nháp cục bộ xoá sau khi gửi thành công, không lưu dữ liệu nhạy cảm vào `localStorage` ngoài nháp form của chính phiếu (không có PII khách).
- Test bắt buộc: AC1–AC8; AC2 atomic (lỗi dòng 2 → không phiếu, không lô); AC3 gửi lại cùng key → 1 phiếu; AC5 `rate` chỉ với `chu`; AC6 `call` → nháp, DB không đổi, duyệt → phiếu + AuditLog `proposal_ref`; test kỷ luật DW-08 xanh với action mới.
- Commit: `Lô 4 AI: DW-17 nhập lô mua tại cảng trên ERP`.

---

## Lô 5 — Mức B (P7, CHỈ STAGING tới khi S-L1…S-L4 xong)
Mọi AC mức B đều có ca **production → bị chặn** (`AI_WRITE_LEVELS_ALLOWED=C` → không có B trong `choices`, PUT B → 400 `BR-AI-27`; `AI_PRODUCTION_READY=false` → PUT trần > C → 400 `BR-AI-27`). Dev **không** đổi env staging/production; ghi nhắc Duy đặt `AI_WRITE_LEVELS_ALLOWED=B` cho staging lúc deploy trong `03-dev-notes.md`.
### 5a · DW-18, DW-20
- DW-18: `POST /api/purchasing/receipts/<pk>/cancel/`, BR-MH-07 (PA — Duy ghi vào spec/decisions khi nghiệm thu, dev không sửa `decisions.md`), V-DW2; huỷ = trạng thái + bút toán đảo, không xoá dòng; `atomic` + `select_for_update` trên phiếu và các lô. Sau khi có action → descriptor `nhap_lo` `max_level=B`, hết `AI_UNDO_MISSING`.
- DW-20: PUT `caps` theo 02b §6.6; ngưỡng hiệu lực = min(user, Chủ).
- Test: DW-18-AC4 huỷ phiếu song song publish lô → đúng 1 thành công; AC3 `nv_kho` khác người tạo 403; DW-20-AC3 production 400 BR-AI-27; AC5 số âm.
- Commit: `Lô 5a AI: DW-18 huỷ phiếu nhập (BR-MH-07), DW-20 trần của Chủ`.
### 5b · DW-19, DW-21
- B hoàn tác trạng thái: view + `AiAction` + AuditLog trong một `atomic` (H5). B trì hoãn: `SCHEDULED`, job `run_due_ai_actions` (management command, idempotent, `select_for_update(skip_locked=True)`, chạy lại bước 2–7 lúc tới hạn). `_force_auth_user` chỉ gọi trong job. **Không** tạo lịch chạy thật (Cloud Scheduler là việc deploy của Duy).
- Test: DW-19-AC5 các lý do hạ mức; AC6 ép AuditLog lỗi → rollback; AC7 lệnh "trần C ép" (kể cả `sales.refund.create_refund`, TL-1) PUT B → 400; DW-21-AC3 thu hồi trong cửa sổ; AC5 hai tiến trình job → view gọi đúng 1 lần; AC6 không đường HTTP tới `_force_auth_user`; AC7 log chỉ id lệnh + mã chứng từ.
- Commit: `Lô 5b AI: DW-19 mức B + hoàn tác, DW-21 trì hoãn ghi + job`.
### 5c · DW-22, DW-23
- Báo cáo ngày (`ai.manage_ai_policy`), escalate + nút "Nhờ" (contract DW-23), việc chờ khách > 2 giờ đẩy `chu`, việc tiền nhắc 12 giờ — chỉ trong ERP (Q-M11), không gửi kênh ngoài.
- Test: DW-22-AC1 đếm đúng từng cột; AC3 403; AC4 PII; DW-23-AC2 định tuyến Group theo quyền (không so tên Group trong code — dùng quyền để tìm Group); AC4 lọc giá vốn theo người nhận.
- Commit: `Lô 5c AI: DW-22 báo cáo AI cuối ngày, DW-23 chuyển việc + Nhờ`.

## Lô 6 — Vùng đỏ (P7, cuối cùng, CHỈ STAGING)
### 6a · DW-24, DW-25
- Công tắc theo **quyền** (`inventory.close_batch`, `sales.confirm_refund`, `sales.confirm_payment_manual`); đóng công tắc → cấu hình về C ngay, việc SCHEDULED về PENDING. DW-25 luật tất định dùng `check_close_batch` (L-1) + 7 ngày không chi phí mới + kiểm kê duyệt sau lần xuất cuối + không việc chờ; trì hoãn `AI_RED_ZONE_DELAY_MINUTES` (30); hạn mức `AI_DAILY_LIMIT_RED_ZONE` (10).
- Test: DW-24-AC3 production 400; AC4 đóng công tắc; AC6 action thử dùng quyền `close_batch` tự theo công tắc; DW-25-AC4 đơn mới giữ lô trong cửa sổ → không chốt, PENDING + chuyển Chủ; AC6 `quan_ly` 404.
- Commit: `Lô 6a AI: DW-24 công tắc vùng đỏ, DW-25 AI chốt lô trì hoãn`.
### 6b · DW-27, DW-26
- DW-27: `sales.refund.confirm` luôn hạ C `AI_NO_EVIDENCE` + tạo việc chuyển; `bank_txn_ref` từ model không bao giờ ghi tự động.
- DW-26 (Could, V-DW1 — **hỏi lại Duy một dòng trước khi code**): job Hệ thống khớp tuyệt đối bằng code, gọi **đúng service ghi tiền hiện có**, công tắc riêng mặc định đóng, production không chạy; không đường nào đưa `raw_payload`/nội dung CK vào model; log chỉ mã GD + mã đơn.
- Test: DW-26-AC2 mọi ca không khớp → chuyển `chu`; AC3 `assertLogs` không có nội dung CK; AC5 production; DW-27-AC2.
- Commit: `Lô 6b AI: DW-27 xác nhận hoàn luôn chuyển Chủ, DW-26 khớp tuyệt đối`.

---

## Mỗi lô: điều kiện xong
- Lệnh kiểm chứng chung + lệnh riêng của lô (dán output tóm tắt vào `03-dev-notes.md`, có số test thật).
- Test bắt buộc chung (ma trận Group, không rò giá vốn, không rò PII kể cả với `chu`, AI tắt vẫn chạy, test kỷ luật tự đăng ký từ Lô 2) + AC mã `DW-xx-ACy` của lô.
- `03-dev-notes.md` không còn mục "Lệch thiết kế" mở.
- QA APPROVED (`04-qa-report.md`, mục theo mã lô).
- Commit tiếng Việt có mã lô + mã story → `git push origin main`; đánh dấu ☑ + mã commit ở bảng Lô.
- Sau mỗi lô có BE, báo Claude để review (02b §16) trước khi Duy nghiệm thu phase.

## Điểm dừng hỏi Duy
- Phase chưa được Duy đổi **SẴN SÀNG CODE** → không bắt đầu lô của phase đó.
- Hồ sơ `sua-loi-bao-mat` chưa XONG/chưa merge `main`; `git pull --ff-only` thất bại; xung đột merge.
- Spike Lô 0 không đạt tiêu chí → dừng trước Lô 2 (Claude sửa 02b, PO sửa AC). Số máy tham chiếu chưa có → Lô 2 BE được làm, **Lô 2 FE chờ** (DW-02-AC5).
- `available_actions` mới khác cũ trên fixture (DW-03-AC2, DW-04-AC3) hoặc một bước `allowed=true` mà thao tác thật trả 400 → "Lệch thiết kế", dừng lô.
- Tách `check_close_batch` làm đỏ `test_l1_close_batch.py` hay bất kỳ test cũ nào ngoài chủ đích.
- Cần đổi `total_cost`/`profit`/công thức lãi lỗ (TL-4; L-10 đã sửa ở hồ sơ sửa lỗi Lô 3, không sửa lại ở đây), đụng tiền, giá vốn, phân quyền ngoài phạm vi story; cần quyền Tầng 2 mới ngoài `cancel_expired_batch` và `manage_ai_policy`.
- Cần thêm dependency ngoài `vitest` (vd cài `@wllama/wllama` — thuộc S08), cần `CACHES`/Redis, hoặc harness CDN của DW-02 không chạy được.
- Migration xung đột với hồ sơ khác (CSKH/CMS/vai trò) hoặc `makemigrations --check` không sạch.
- Bất kỳ việc gì làm B/A chạy được ở production, cần đổi env staging/production, cần lịch chạy job thật.
- Đầu Lô 6b: xác nhận V-DW1 trước DW-26.
- Contract/thiết kế không khớp code → ghi "Lệch thiết kế" trong `03-dev-notes.md`, dừng lô; Claude chốt (Việc 2 Tech Lead).

## Ghi chú liên hồ sơ (điều phối viên thêm 28/09, từ 02b CSKH và CMS)
- **Lô 2 — danh sách "cấm hẳn" của lệnh tự sinh** phải có sẵn các tiền tố sau dù endpoint chưa tồn tại: `/api/public/` (site-info, nội dung công khai — CMS/go-live), `/api/cskh/` (dữ liệu cá nhân khách — CSKH), mọi đường dẫn kết thúc `/label/` và `/label/print/` (tem có tên/SĐT/địa chỉ). Test kỷ luật tự đăng ký (DW-08) thêm ca: route mới dưới các tiền tố này không bao giờ vào chỉ mục.
- Khi lệnh AI tạo/sửa bài CMS thì đặt `Entry.source="ai"` (02b CMS). Thêm một ca CMS vào test "feature mới không khai gì" (§11.2) khi hồ sơ CMS đã có code.

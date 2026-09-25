# ERP console "nối thật" — Dev notes

---

## Lô L1 — S1, S2 (BE) · 2026-09-24

### Kết quả kiểm chứng
- `cd backend && .venv/bin/python manage.py test` → **Ran 86 tests, OK** (mốc trước: 66; +9 test S1, +11 test S2).
- `manage.py makemigrations --check --dry-run` → `No changes detected`. **Không có migration** (không đổi schema).

### File đã sửa / thêm
| File | Thay đổi |
|---|---|
| `backend/apps/inventory/services.py` | + `sellable_batches(*, item=None, on_date=None)`; `allocate_fifo` dùng nó. + `update_batch_statuses(*, today=None)` và helper `_target_status`, `_status_audit_action` |
| `backend/apps/catalog/pricing.py` | `_simple_sellable` dùng `sellable_batches` (Shop catalog/detail, BUNDLE theo thành phần) |
| `backend/apps/inventory/management/__init__.py`, `.../commands/__init__.py` | mới (package) |
| `backend/apps/inventory/management/commands/update_batch_status.py` | command mới |
| `backend/apps/inventory/tests/test_s1_expiry.py` | test S1-AC1…AC6 + C1 |
| `backend/apps/inventory/tests/test_s2_batch_status_job.py` | test S2-AC1…AC7 |

### Endpoint / contract
Không có endpoint mới, không đổi contract. `GET /api/shop/catalog/` và `/api/shop/catalog/{code}/` giữ nguyên JSON; chỉ `sellable_qty` giờ không tính lô quá hạn. `POST /api/shop/orders/` không đổi (field lạ như `batch`, `batch_id` bị bỏ qua, S1-AC6).

### Rule đã cài
- **BR-LO-02 (S1)**: "lô bán được" = `status ∈ {SELLING, NEAR_EXPIRY}` **và** `expiry_date >= timezone.localdate()` (TIME_ZONE = `Asia/Ho_Chi_Minh`). `expiry_date` là **ngày cuối còn bán** (C1). Lọc ở tầng truy vấn, không phụ thuộc job S2. Nguồn chung: `apps.inventory.services.sellable_batches`.
- **C1 (đơn giữ chỗ trước nửa đêm)**: job S2 **không nhả giữ chỗ** và `confirm_payment`/`issue_invoice` không kiểm hạn lô. Đơn giữ chỗ lúc 23:50 thanh toán lúc 00:10 vẫn PROCESSING, trừ kho đúng lô dù lô đã EXPIRED (test `test_s1_c1_...`).
- **S2 job `update_batch_status`** (BR-LO-01/02/06, BR-HV-02, BR-PQ-04/07). Chỉ xét lô DRAFT/SELLING/NEAR_EXPIRY/SOLD_OUT. EXPIRED/CANCELLED/CLOSED không đụng (S2-AC6, BR-LO-05). Bảng chuyển:

  | Điều kiện (hôm nay giờ VN) | Trạng thái đích | AuditLog `action` |
  |---|---|---|
  | `expiry_date < hôm nay`, lô DRAFT/SELLING/NEAR_EXPIRY, hoặc SOLD_OUT còn tồn | EXPIRED | `batch_expired` |
  | SOLD_OUT, tồn 0, đã quá hạn | giữ nguyên | — |
  | DRAFT chưa quá hạn | giữ nguyên | — |
  | `qty_available = 0` và `qty_reserved = 0` | SOLD_OUT | `batch_sold_out` |
  | `expiry_date <= hôm nay + BATCH_NEAR_EXPIRY_DAYS` | NEAR_EXPIRY | `batch_near_expiry` (hoặc `batch_back_in_stock` nếu từ SOLD_OUT) |
  | còn lại | SELLING | `batch_selling` (hoặc `batch_back_in_stock` nếu từ SOLD_OUT) |

  AuditLog: `actor=None`, `changes={"status": {"from": ..., "to": ...}}`, `note="update_batch_status <ngày>"`. Idempotent: chỉ ghi khi trạng thái đích khác hiện tại (S2-AC5). Mỗi lô xử lý trong transaction riêng với `select_for_update`, kiểm lại trạng thái sau khi khoá. Ngưỡng đọc từ `settings.BATCH_NEAR_EXPIRY_DAYS` (env, mặc định 14).
- Output command: `Đã cập nhật N lô (EXPIRED=1, NEAR_EXPIRY=2).` hoặc `Đã cập nhật 0 lô (không đổi).`
- **S2-AC7**: không có endpoint nào kích job (test gọi các URL đoán được → 403/404/405, lô không đổi, không AuditLog). Phần `PATCH status` → 400 `BR-PQ-14` thuộc **S3**, chưa làm ở lô này.

### Lịch chạy — đề xuất deploy (CHƯA chạy, chờ Duy duyệt)
Theo mẫu job `cangca-ttl` (Cloud Run Job + Cloud Scheduler), cùng image với `cangca-api`:
```bash
# 1) Cloud Run Job (cùng image/env/Cloud SQL như cangca-ttl)
gcloud run jobs create cangca-batch-status \
  --project keolai-63ec1 --region asia-southeast1 \
  --image asia-southeast1-docker.pkg.dev/keolai-63ec1/cangca/api:<tag mới> \
  --command python --args manage.py,update_batch_status \
  --set-cloudsql-instances keolai-63ec1:asia-southeast1:cangca-loc-db \
  --set-env-vars <copy từ job cangca-ttl: DATABASE_URL, DJANGO_SECRET_KEY, BATCH_NEAR_EXPIRY_DAYS=14…> \
  --max-retries 1 --task-timeout 300s

# 2) Cloud Scheduler 00:05 giờ VN hằng ngày
gcloud scheduler jobs create http cangca-batch-status-trigger \
  --project keolai-63ec1 --location asia-southeast1 \
  --schedule "5 0 * * *" --time-zone "Asia/Ho_Chi_Minh" \
  --http-method POST \
  --uri "https://asia-southeast1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/keolai-63ec1/jobs/cangca-batch-status:run" \
  --oauth-service-account-email <SA đang dùng cho cangca-ttl-trigger>
```
Kiểm tra sau deploy: `gcloud run jobs execute cangca-batch-status --wait` hai lần liền; lần 2 phải in `Đã cập nhật 0 lô`.

### Còn nợ / giả định
1. **Dashboard** (`apps/reports/dashboard_api.py`) chưa dùng `sellable_batches`: `ACTIVE_BATCH` gồm cả DRAFT, cảnh báo cận hạn tính cả lô đã quá hạn. Để nguyên vì S8-AC1 đòi số trùng bản cũ; nên quyết khi làm S24/S8 (khối "Cần chú ý" nên tách "Quá hạn còn tồn", E-10).
2. Không thêm Celery beat entry cho job này (production không dùng Celery, dùng Cloud Scheduler). Nếu cần chạy bằng Celery beat ở môi trường khác thì thêm task gọi `update_batch_statuses`.
3. `BusinessError` chưa có trường `code` (S3). Lỗi thiếu tồn vẫn là thông điệp cũ "Không đủ tồn khả dụng… (BR-BH-02)".
4. Giả định: lô SOLD_OUT có hàng hoàn tái nhập **sau** khi đã quá hạn → EXPIRED (không bán lại). Lô NEAR_EXPIRY mà hạn bị lùi xa hơn ngưỡng → trở về SELLING (`batch_selling`). Story không nêu hai trường hợp này.
5. Lô EXPIRED còn giữ chỗ (đơn C1): job không nhả. Nếu đơn đó hết TTL thì `cancel_expired_orders` nhả như thường; phần tồn còn lại chờ Chủ huỷ (S27).

---

## Lô L2 — S3, S4, S5 (BE) · 2026-09-24

### Kết quả kiểm chứng
- `cd backend && .venv/bin/python manage.py test` → **Ran 142 tests, OK** (mốc trước: 86; +56 test L2).
- `manage.py makemigrations --check --dry-run` → `No changes detected`. **Không có migration** (không đổi schema, không đổi quyền Group).
- `cd adapter && .venv/bin/python -m pytest -q` → **10 passed**. Adapter **không sửa**: lỗi từ Django chỉ đọc `response.text`, thêm key `code` không ảnh hưởng.
- `frontend/lib/api.ts` đọc `body.detail`, vẫn có. Không sửa `frontend/`.

### File đã sửa / thêm
| File | Thay đổi |
|---|---|
| `backend/apps/common/exceptions.py` | `BusinessError(message, code=None)`. `code` tường minh, hoặc tự lấy mã `BR-XX-nn` đầu tiên trong thông điệp, không có thì `"BUSINESS_ERROR"` |
| `backend/apps/common/api.py` | `exception_handler` trả `{"detail","code"}`. `BusinessModelPermissions`: GET/HEAD đòi `view_*`; method không có handler → 405 (sau kiểm đăng nhập). Mới: `reject_protected_fields`, `ProtectedFieldsMixin` (`locked_fields`, `actor_fields`), `DocumentViewSet` (không DELETE), `has_full_delivery_scope`, `FULL_SCOPE_GROUPS` |
| `backend/apps/inventory/api.py`, `serializers.py` | Batch, StockEntry, StockReconciliation, ReturnToStock → `DocumentViewSet` + field khoá/người ghi; `created_by`, `decision` read-only |
| `backend/apps/inventory/services.py` | `publish_batch` raise với `code="BR-MH-05"` |
| `backend/apps/delivery/api.py`, `serializers.py` | DeliveryNote → `DocumentViewSet`, khoá 5 field, dùng `has_full_delivery_scope` (thay `PRIVILEGED_GROUPS`) |
| `backend/apps/purchasing/api.py`, `serializers.py` | PurchaseReceipt, PurchaseInvoice, PurchaseCost → `DocumentViewSet`; `created_by` read-only, ghi theo người đăng nhập |
| `backend/apps/sales/api.py`, `serializers.py` | `SalesOrderViewSet.get_queryset`, `CustomerViewSet.get_queryset` lọc theo phiếu giao (S5). `refunds/create/` chặn `created_by`/`confirmed_by`. `Refund.created_by` read-only |
| `backend/apps/sales/shop_api.py`, `internal_api.py` | Hai chỗ tự bắt `BusinessError` giờ trả thêm `code` |
| `backend/apps/common/tests/` (mới) | `fixtures.py`, `test_s3_locked_fields.py` (29), `test_s4_actor_fields.py` (16), `test_s5_scope_nv_giao.py` (11) |

### Contract thực tế
**Lỗi nghiệp vụ (mọi endpoint):** HTTP 400
```json
{"detail": "Trường landed_unit_cost chỉ đổi qua thao tác nghiệp vụ, không sửa trực tiếp (BR-PQ-14).", "code": "BR-PQ-14"}
```
- Nhiều field khoá trong một request thì `detail` liệt kê hết: `"Trường status, qty_available chỉ đổi qua…"`.
- BR-PQ-16: `{"detail": "Trường created_by do hệ thống ghi theo người đăng nhập, không gửi từ client (BR-PQ-16).", "code": "BR-PQ-16"}`.
- Lỗi không có mã BR trong thông điệp → `"code": "BUSINESS_ERROR"`. FE nên coi đây là "lỗi chung", không rẽ nhánh theo nó.
- Lỗi validate của DRF (thiếu field, sai kiểu) **giữ định dạng cũ** `{"<field>": ["…"]}`, không có `code`. 401/403/404/405 giữ `{"detail": "…"}` của DRF.
- Nếu request vừa có field khoá (BR-PQ-14) vừa có `created_by` thì báo BR-PQ-14 trước.

**Field khoá (POST/PUT/PATCH gửi lên → 400 BR-PQ-14):**
| Endpoint | Field khoá | Field người ghi (→ 400 BR-PQ-16, hệ thống tự ghi) | DELETE |
|---|---|---|---|
| `inventory/batches` | `status`, `qty_received`, `qty_available`, `qty_reserved`, `purchase_rate`, `landed_unit_cost`, `expiry_date`, `closed_at`, `closed_by` | — | 405 |
| `delivery/notes` | `status`, `assigned_to`, `failed_attempts`, `completed_at`, `sales_invoice` (PATCH được mỗi `note`) | — | 405 |
| `inventory/returns` | `status`, `decision`, `approved_by` | `created_by` | 405 |
| `inventory/reconciliations` | `status`, `approved_by`, `approved_at` | `created_by` | 405 |
| `purchasing/receipts` | `status` | `created_by` | 405 |
| `purchasing/invoices` | — | `created_by` | 405 |
| `purchasing/costs` | — | `created_by` | 405 |
| `inventory/stock-entries` | — | `created_by` | 405 |
| `sales/refunds/create/` | (action) | `created_by`, `confirmed_by` | 405 (read-only) |
| `sales/orders`, `sales/invoices`, `sales/payments`, `sales/refunds` | read-only: PATCH/PUT/DELETE/POST lên router → 405 | | |

`POST /api/inventory/reconciliations/` (S4-AC1), body `{"count_date": "2026-09-24", "note": "kiểm cuối ngày"}` → 201:
```json
{"id": 12, "count_date": "2026-09-24", "status": "DRAFT", "created_by": 7, "approved_by": null, "approved_at": null, "note": "kiểm cuối ngày", "lines": []}
```

**Phạm vi NV giao (S5):** `GET /api/sales/orders/`, `/api/sales/orders/{id}/`, `/api/sales/customers/`, `/api/sales/customers/{id}/`. Người chỉ thuộc `nv_giao` thấy đơn có phiếu giao `assigned_to = mình`, khách của các đơn đó. Ngoài phạm vi → **404**. Thuộc `chu`/`quan_ly`/`nv_kho` hoặc superuser → thấy hết (kiêm nhiệm = hợp quyền, BR-PQ-09). JSON không đổi.

### Rule đã cài
- **BR-PQ-14** (S3): field trạng thái/tồn/giá vốn/người phụ trách không đổi được qua sửa chung. Chặn ở tầng API bằng 400 có liệt kê field, **sau** kiểm quyền Tầng 1 (thiếu `change_batch` → 403 trước, S3-AC6). Thêm lớp thứ hai: các field đó `read_only` trong serializer.
- **BR-PQ-10** (S3-AC4): chứng từ không có route DELETE. `BusinessModelPermissions` trả **405 cho mọi người đã đăng nhập** khi view không có handler cho method, kể cả người thiếu `delete_*`. Trước đây DELETE lô bởi `chu` gây 500 (`ProtectedError`).
- **BR-PQ-16** (S4): `created_by` luôn = `request.user`. Client gửi (kể cả id của chính mình) → 400, không tạo. PATCH đổi `created_by` cũng 400. Nhờ vậy BR-KK-02 có nghĩa thật: `ql1` tự tạo rồi tự duyệt kiểm kê → 400 `BR-KK-02` (S4-AC3).
- **Tầng 3 dòng NV giao** (S5, spec §1.6, BR-PQ-12): như mục Contract. Đổi người giao là mất quyền xem ngay (S5-AC5).
- **Mã lỗi `code`** (S3-AC5): áp cho `exception_handler` chung, Shop `POST /api/shop/orders/` và webhook nội bộ.

### Lệch so với story (cần PO/QA biết)
1. **S2-AC7 / S3-AC1 / S3-AC3 và quyền seed:** `quan_ly` và `nv_kho` chỉ có `view_batch` (chỉ `chu` có `change_batch`). Vì vậy NV kho `PATCH` lô → **403** (đúng S3-AC6: quyền trước field), **không phải** 400 như S2-AC7 viết. Test S2-AC7 kiểm cả hai: nv_kho → 403; người có `change_batch` → 400 `BR-PQ-14`; lô không đổi, không AuditLog. Test S3-AC1/AC3 cấp thêm `change_batch` cho `ql1` đúng như Given "Quản lý có change_batch". **Không** đổi seed quyền Group.
2. **S3-AC3:** `Batch` không có field `note`. Test dùng `supplier` và `received_date` (không khoá) → 200.
3. **S4, lệch với lời giao việc:** lời giao việc nói "client gửi `created_by` bị bỏ qua", còn story S4-AC2 (đã duyệt) nói **400 BR-PQ-16**. Tôi làm theo story: trả 400.
4. **Thêm ngoài danh sách (theo bất biến #3, BR-PQ-16):** `inventory/stock-entries` và `purchasing/invoices` cũng không DELETE được và tự ghi `created_by`. `refunds/create/` chặn cả `confirmed_by`.
5. **Sửa lỗ Tầng 1 phát hiện khi làm S5:** `BusinessModelPermissions` trước đây **không** kiểm `view_*` cho GET, dù docstring nói có (DRF mặc định `perms_map["GET"] = []`). Hậu quả: user không thuộc Group nào, hoặc NV giao, đọc được `sales/invoices`, `sales/payments`, `inventory/batches`… Giờ GET đòi `view_<model>`. Ảnh hưởng:
   - NV giao giờ bị 403 ở mọi endpoint mà seed không cấp `r`, trừ `sales/customers`, `sales/orders`, `delivery/notes`, `inventory/returns`.
   - NV kho bị 403 ở `sales/refunds`, `sales/payments`, `purchasing/invoices`, `purchasing/costs`, `catalog/price-lists|item-prices|pricing-rules`.
   - Console cũ (`erp-console/legacy`) chỉ gọi `auth/token` và `dashboard/summary` (view riêng, `IsAuthenticated`), nên không bị ảnh hưởng. **FE console mới:** menu/màn phải theo quyền (S6 `permissions`), đừng gọi endpoint mà vai không có `view_*`.

### Còn nợ / giả định
1. `PATCH purchasing/costs/{id}` (chỉ `chu` có `change_purchasecost`) vẫn sửa được `amount`/`allocation_method` mà không phân bổ lại giá vốn, không AuditLog. Story S3 không đưa vào danh sách khoá. Đề xuất khoá khi làm S32/S33 (điều chỉnh bằng chứng từ âm).
2. `PATCH inventory/batches` vẫn đổi được `item`, `supplier`, `warehouse`, `received_date` (không nằm trong danh sách khoá). Đổi `item` của lô đang có tồn là chuyển tồn giữa mặt hàng mà không có AuditLog. Đề xuất PO thêm `item` (có thể cả `warehouse`) vào danh sách khoá BR-PQ-14. Thực tế hiện chỉ `chu` có `change_batch`.
3. `PATCH purchasing/invoices/{id}` sửa được `amount`, `is_paid`. Chỉ `chu` có quyền; để S31 quyết.
4. `inventory/returns` POST vẫn tạo phiếu không qua service `return_to_warehouse`: không kiểm trạng thái phiếu giao, không AuditLog. Đó là việc của S22. Lô này chỉ khoá `status`/`decision`/`approved_by` và ghi `created_by`.
5. `ReturnToStockViewSet.approve` vẫn gán `decision` từ body trước khi gọi service. Đây là đường action hợp lệ (có AuditLog trong `apply_return`); để S23 đưa vào service.
6. Phần lớn `BusinessError` cũ chưa truyền `code` tường minh; chúng dựa vào mã BR có trong thông điệp. Lỗi không có mã → `BUSINESS_ERROR`. Chỉ `publish_batch` được gán `BR-MH-05`. Story sau cần `code` riêng thì truyền `code=` khi raise.
7. Về TDD: phần trả `code` ở webhook nội bộ (`internal_api.py`) được sửa trước khi có test. Test `test_s3_ac5_webhook_noi_bo_loi_nghiep_vu_co_code` được viết sau và xanh ngay. Các phần còn lại đều RED trước (38 test đỏ đúng lý do ở lần chạy đầu).

---

## Lô tái cấu trúc BE — chia module theo tính năng (chen giữa L2 và L3) · 2026-09-24

Duy yêu cầu chia source theo module tính năng và giải thích file cấu hình. **Không đổi hành vi**, không đổi URL, không có migration mới.

### Kết quả kiểm chứng
- `manage.py test`: **Ran 142 tests, OK**. Tên 142 hàm test trùng khớp trước và sau (so bằng `diff`).
- Thời gian suite: trước **~40–42 s** (`Ran 142 tests in 41.7s`, 46,6 s tính cả khởi động). Sau khi sửa: **6,3 s** (8,1 s tính cả khởi động).
- `makemigrations --check --dry-run`: `No changes detected`. `manage.py check`: không có lỗi.
- Đã dump route + ViewSet + permission_classes + serializer fields + locked/actor fields + model (label, db_table, permissions, fields) trước và sau refactor. Hai bản giống hệt nhau (328 dòng).
- Celery vẫn đăng ký task tên cũ `apps.sales.tasks.cancel_expired_orders` (beat schedule không đổi).
- `adapter`: `pytest -q` → 10 passed (adapter không bị sửa).
- Grep không còn chỗ nào import `apps.<app>.services/api/serializers/shop_api/internal_api` hay `apps.catalog.pricing` (file) kiểu cũ.

### Cấu trúc mới (đường dẫn cũ → mới)
| Cũ | Mới |
|---|---|
| `sales/services.py` | `sales/orders/services.py` (create_order, giá/ưu đãi, cancel_unpaid_expired, cancel_paid_order) · `sales/payments/services.py` (confirm_payment, issue_invoice) · `sales/refunds/services.py` · `sales/customers/services.py` (gộp khách theo SĐT, tách từ create_order) · `sales/utils.py` (làm tròn tiền, sinh mã) |
| `sales/api.py`, `serializers.py`, `shop_api.py`, `internal_api.py`, `tasks.py` | `sales/{orders,payments,refunds,customers}/api.py` + `serializers.py`; `orders/shop_api.py`; `payments/internal_api.py`; `orders/tasks.py` |
| `inventory/services.py` | `inventory/batches/services.py` (sinh lô, FIFO, giữ chỗ, publish/close, recompute_landed_cost, job trạng thái) · `stock/services.py` (record_movement) · `stocktake/services.py` · `returns/services.py` |
| `purchasing/services.py` | `purchasing/receipts/services.py` (submit_receipt) · `costs/services.py` (record_purchase_cost) |
| `catalog/pricing.py`, `shop_api.py` | `catalog/pricing/services.py` (effective_price) · `catalog/items/services.py` (sellable_qty) · `catalog/items/shop_api.py` |
| `<app>/models.py` (catalog, purchasing, inventory, sales) | `<app>/models/<tính_năng>.py` + `models/__init__.py` gom lại. Giữ app_label, tên model, db_table |
| `<app>/tests/` (sales, inventory, purchasing) | `tests/` trong từng module. `sales/orders/tests/base.py` và `inventory/batches/tests/base.py` chứa dữ liệu nền dùng chung |

README: `backend/README.md` (sơ đồ module + bảng file cấu hình), 8 README app, 13 README module, và `accounts/staff/`, `accounts/auth/` (chỗ chừa cho L5–L6).

### Chỗ quyết định khác gợi ý
1. **`cancel_paid_order` để ở `orders/`, không đưa sang `refunds/`.** Hàm này đổi trạng thái đơn và endpoint là `sales/orders/{id}/cancel/`. Việc hoàn tiền là sổ riêng (BR-HT-05/06).
2. **`SalesInvoice` và `issue_invoice` để ở `payments/`**, vì hoá đơn chỉ sinh ra khi tiền về. Model của nó nằm trong file riêng `models/invoices.py`.
3. **`Supplier` để chung `purchasing/receipts/`.** Nó chỉ là CRUD phục vụ phiếu nhập, chưa đáng thành module riêng.
4. **`BundleLine` (công thức combo) để ở `catalog/items/`, không để ở `pricing/`.** Combo là một loại mặt hàng (item_type=BUNDLE) và `ItemSerializer` lồng công thức. `pricing/` chỉ gồm bảng giá, giá niêm yết và ưu đãi.
5. **`recompute_landed_cost` để ở `inventory/batches/`, không để ở `purchasing/costs/`.** Hàm này sửa field của lô, nên `costs` gọi sang `batches`.
6. **`Warehouse` tách thành `models/warehouses.py`**, API nằm ở `stock/`. Tách như vậy để tránh import vòng giữa `models/batches.py` và `models/stock.py`.
7. **Module không có nghiệp vụ thì không tạo `services.py` rỗng.** Hiện chỉ có `purchasing/invoices/` (chỉ CRUD). Ba thư mục `purchasing/invoices/tests/`, `catalog/pricing/tests/`, `sales/customers/tests/` còn rỗng. Phần của chúng đang được test ở `apps/common/tests` (S3/S4/S5) và `sales/orders/tests`, README từng module có ghi rõ.
8. **Test S3/S4/S5 của L2 giữ ở `apps/common/tests/`.** Chúng kiểm cơ chế dùng chung (`DocumentViewSet`, khoá field, phạm vi nv_giao) trên nhiều app cùng lúc.
9. **`apps/sales/tasks.py` vẫn còn** nhưng chỉ có 1 dòng re-export, vì Celery `autodiscover_tasks()` chỉ tìm `apps.<app>.tasks`. Task giữ `name="apps.sales.tasks.cancel_expired_orders"`.
10. Các lớp test bị tách theo module nên có tên lớp mới (vd `TTLAndRefundTests` → `orders.TTLAndCancelTests` + `refunds.RefundTests`, `InventoryServiceTests` → 4 lớp). Tên hàm test giữ nguyên. Riêng `test_shop_catalog_has_price_no_cost` chuyển sang `catalog/items/tests/test_shop_api.py`.
11. Mock trong `test_s3_ac5_webhook_noi_bo_loi_nghiep_vu_co_code` đổi đích patch thành `apps.sales.payments.services.confirm_payment`. Hành vi test giữ nguyên.

### Test chậm — nguyên nhân & cách sửa
- Đo bằng cProfile trên `apps.common` (56 test): hàm `pbkdf2_hmac` bị gọi 136 lần, tốn ~0,62 s/lần, chiếm khoảng 80% thời gian. Nguồn là `User.objects.create_user(password=…)` trong `common/tests/fixtures.make_user`, và fixture này được dùng dày ở test L2.
- Sửa `config/settings.py`: `TESTING = sys.argv[1] == "test"`. Chỉ khi đó mới đặt `PASSWORD_HASHERS = [MD5PasswordHasher]`. Khi chạy thường (gunicorn/runserver), hasher vẫn là PBKDF2. Đã kiểm bằng `django.setup()` ngoài test: `PBKDF2PasswordHasher`, `TESTING=False`.

### Còn nợ / lưu ý
1. `.claude/skills/*` (caveve-domain, django-drf-patterns) còn nhắc đường dẫn cũ `apps/inventory/tests/test_api.py`, `apps/sales/tests/test_services.py`, `apps/<app>/services.py`. Nằm ngoài phạm vi BE nên chưa sửa; nên cập nhật sang `apps/inventory/batches/tests/test_api.py`, `apps/sales/orders/tests/test_services.py`.
2. Có một số import thừa từ trước, không do lô này sinh ra: `sales/admin.py` (`SalesOrderLineBatch`, `SalesInvoiceLineBatch`) và `common/tests/test_s4_actor_fields.py` (`Decimal`). Chưa đụng tới.
3. `manage.py check --deploy` (DEBUG=0) báo 3 cảnh báo có từ trước (HSTS/SSL redirect…). Cloud Run đã kết thúc TLS ở proxy, nên việc này để lúc rà bảo mật.
4. L5 (staff) / L6 (auth) viết vào `apps/accounts/staff/`, `apps/accounts/auth/` theo cấu trúc module. Test phải nằm ở `tests/` của module để `manage.py test` tìm thấy (mỗi thư mục cần có `__init__.py`).

---

## Lô L3 — S7 (FE): khung ERP console Next.js · 2026-09-24

### Kết quả kiểm chứng
- `cd erp-console && npx tsc --noEmit` → sạch.
- `npm run build` → sạch, 16 trang tĩnh ra `out/` (S7-AC8). `NEXT_PUBLIC_USE_MOCK=1 npm run build` → cũng sạch.
- Bản build thật **không chứa code mock** (grep `demo1234`/`mock-token`/`__caveMock` trong `out/_next` = 0 file). `out/` hiện tại là bản build thật, không phải mock.
- E2E Playwright trên bản build mock phục vụ tĩnh (`python3 -m http.server 3101`, đã tắt sau khi chạy): **25/25 PASS**, không lỗi console. Kịch bản: `erp-console/e2e/s7_shell.py`.

| AC | Kết quả |
|---|---|
| S7-AC1 | `loc` → `/overview/`; menu 9 mục: Tổng quan, Đơn & tiền, Giao hàng, Kho & lô, Mua hàng, Kiểm kê, Báo cáo lãi lỗ, Danh mục & giá, Nhân sự · Nhật ký |
| S7-AC2 | `giao1` → `/my-deliveries/`; menu chỉ "Việc giao của tôi" |
| S7-AC3 | `giao1` mở `/reports` → "Bạn không có quyền xem mục này"; log request mock chỉ có `GET /api/auth/me/` |
| S7-AC4 | sai mật khẩu và `nghi1` (đã nghỉ) → "Sai tài khoản/mật khẩu hoặc tài khoản đã ngừng hoạt động.", vẫn ở màn đăng nhập |
| S7-AC5 | `admin` (không Group) → `/no-role/`, không menu, không cột phải; gõ `/overview/` vẫn bị đưa về |
| S7-AC6 | token bị thu hồi → về `/login/?next=/purchasing/` kèm thông báo; nháp còn; `loc` đăng nhập lại thì về đúng trang, nháp còn; `giao1` đăng nhập thì nháp bị xoá và vào trang của `giao1` |
| S7-AC7 | 360×640: không cuộn ngang (login, trang, ngăn kéo), menu đáy 4 mục + "Thêm", nút ☰, cột phải là ngăn kéo, mọi nút/link ≥ 44px. 1280×800: 3 cột |

Ảnh chụp (`doc/features/2026-09-24-erp-console-noi-that/shots/`): `s7-desktop-1280-chu.png`, `s7-mobile-360-kho1.png`, `s7-mobile-360-login.png`, `s7-mobile-360-menu.png`, `s7-mobile-360-rightrail.png`.

### Cấu trúc (Duy yêu cầu: chia theo module tính năng)
```
erp-console/
  app/            chỉ route, mỏng: page.tsx import 1 màn từ features/ hoặc shared/
    (console)/    nhóm route cần đăng nhập; layout = ConsoleGate → Shell; 10 thư mục = 10 mục menu
    login/ no-role/ page.tsx layout.tsx not-found.tsx
  features/auth/  api.ts mock.ts types.ts session.ts README.md
                  components/ AuthProvider ConsoleGate LoginScreen NoRoleScreen RootRedirect ViewGuard
  shared/lib/     http.ts token.ts nav.ts drafts.ts useDraft.ts format.ts
  shared/ui/      Shell RightRail Icon StateBox Placeholder ThemeToggle themeScript NotFoundScreen globals.css
  e2e/            s7_shell.py
  legacy/         index.html (bản HTML cũ, chép nguyên; xoá ở S8)
  README.md       sơ đồ thư mục + bảng giải thích từng file cấu hình + lệnh
```
Quy tắc: `shared/` không import `features/` (đã kiểm bằng grep); module không import chéo, chỉ qua `shared/` hoặc `features/auth`; không có barrel `index.ts`; alias `@/`.

### Hàm/API mới
- `shared/lib/http.ts`: `apiFetch<T>(path, {method, body, auth, signal, mock})`. Tự gắn `Authorization: Token`. Chế độ mock chạy `mock(req)` của module rồi đi qua **cùng** nhánh xử lý status. 401 (khi đã gửi token) → về đăng nhập, giữ nháp. 403 → tải lại `me`. Lỗi → `ApiError(detail, status, code)`. Ngoài ra: `Paginated<T>`, `mockRequestLog`.
- `features/auth/api.ts`: `login()` (`POST /api/auth/token/`, 400 → thông điệp S7-AC4), `getMe()` (`GET /api/auth/me/`), `logoutRemote()` (`POST /api/auth/logout/` của S46: gọi thử, lỗi thì bỏ qua).
- `shared/lib/nav.ts`: bảng menu ↔ quyền, `visibleNav`, `canView`, `homePath`, `safeNext`.
- `shared/lib/useDraft.ts`: `useDraft(ownerId, formKey, initial)` → `[value, setValue, clear, restored]`.
- `AuthProvider` tải lại `me` khi mở app, khi quay lại tab sau ≥ 5 phút, và khi nhận 403 (làm sẵn phần khung của S47).
- Mock (`features/auth/mock.ts`, mật khẩu `demo1234`): `loc`, `ql1`, `kho1` (nv_kho + nv_giao), `giao1`, `admin` (không Group), `nghi1` (đã nghỉ). Trong DevTools: `window.__caveMock.log`, `.clearLog()`, `.expire()`.

### Cách S8 cắm vào
Tạo `features/overview/{api.ts,mock.ts,types.ts,components/OverviewScreen.tsx,README.md}`. Trong `app/(console)/overview/page.tsx` thay `<Placeholder view="overview" />` bằng `<OverviewScreen />` và giữ `<ViewGuard>`. Cột phải nhận `activity` và `assistant` qua props của `Shell` (truyền từ `ConsoleGate`). Ba trạng thái dùng `shared/ui/StateBox`. Tiền/kg dùng `shared/lib/format`.

### Lệch contract / chỗ cần BE, PO chốt
1. **Tên quyền Tổng quan:** story ghi `reports.view_dashboard` ("BE chốt ở S6"). Backend hiện **không có** quyền này. FE hiện "Tổng quan" khi có `reports.view_dashboard` **hoặc** thuộc `chu`/`quan_ly`/`nv_kho`. BE chốt tên nào thì chỉ sửa một dòng trong `shared/lib/nav.ts`.
2. **"Đơn & tiền" với NV giao:** bảng S7 chỉ ghi `sales.view_salesorder`. NV giao có quyền này (để xem đơn của phiếu mình, S5), nhưng S7-AC2 đòi menu `giao1` chỉ có "Việc giao của tôi". FE ẩn "Đơn & tiền" với người **chỉ** thuộc `nv_giao`. `kho1` (nv_kho + nv_giao) vẫn thấy.
3. **S7-AC1 "menu hiện đủ các mục":** Chủ không thuộc `nv_giao`, nên không có "Việc giao của tôi" (theo đúng bảng). Chủ thấy 9/10 mục.
4. **Danh sách `permissions` trong mock** là phỏng đoán theo Group (ví dụ `delivery.view_deliverynote`, `inventory.view_stockreconciliation`, `catalog.view_item`, `accounts.manage_staff`, `reports.view_profitreport`). Khi S6 xong, cần so với `get_all_permissions()` thật, nhất là quyền nv_kho (BE L2 ghi nv_kho bị 403 ở một số endpoint).
5. **Đăng nhập lỗi:** DRF `obtain_auth_token` trả 400 `non_field_errors` cho cả sai mật khẩu lẫn `is_active=False`. FE gộp cả hai thành một thông điệp (đúng AC4). Không phân biệt được hai trường hợp, và cũng không nên.
6. `POST /api/auth/logout/` (S46) chưa có ở BE. FE gọi thử, 404 thì bỏ qua và vẫn xoá token trên máy. Đăng xuất chủ động xoá nháp trên máy (S46-AC1).

### Còn nợ / lưu ý
1. **Chưa có package-lock.json, `node_modules` là symlink** `erp-console/node_modules → ../frontend/node_modules`. Lý do: ổ đĩa máy dev đầy (còn khoảng 140–380 MB), `npm install` báo ENOSPC. Hai app dùng cùng phiên bản (next 14.2.35, react 18.3.1, typescript 5.9). Khi có chỗ trống: `rm node_modules && npm install` trong `erp-console/` để có lock file riêng.
2. **S7-AC6 mới kiểm ở tầng lưu nháp** (localStorage + chủ nháp + điều hướng). Console chưa có form thật nào dùng `useDraft`, nên phần "form mở lại đủ nội dung" kiểm lại ở form đầu tiên (S28/S41).
3. **Build để deploy phải set `NEXT_PUBLIC_API_BASE`** (URL Cloud Run `cangca-api`). Không set thì bản build gọi `http://localhost:8000`. Chưa tạo `.env.production` (không được tự sửa file env production). Chỉ có `.env.example`.
4. `firebase.json` đã đổi `public` → `out`. **Chưa deploy.** Site `cangca-erp` vẫn đang chạy bản HTML cũ. Nếu deploy bây giờ thì Tổng quan/Đơn/Kho chỉ còn khung chờ, nên phải đợi S8 xong.
5. `public/index.html` đã chuyển sang `legacy/index.html` (chép nguyên, kiểm `cmp` trùng khớp). `public/` phải bỏ vì Next.js sẽ chép nó vào `out/` và đè lên trang `/`.
6. Font (Google Fonts, Material Symbols) nạp từ CDN như bản cũ. `.mi` có `width:1em; overflow:hidden` nên khi font chưa tải xong, chữ tên icon không làm tràn ngang ở 360px.

---

## Lô L3–L4 — S6, S9 (BE) · 2026-09-24

### Kết quả kiểm chứng
- `cd backend && .venv/bin/python manage.py test` → **Ran 175 tests, OK** (~5–6,5 s). Mốc trước 142, thêm 33 test: S6 16, S9 17.
- `makemigrations --check --dry-run` → `No changes detected`. `manage.py check` → không có lỗi.
- 2 migration mới (đọc lại ở mục Migration). Đã chạy thử trên SQLite nháp: migrate tới cuối → Group giữ `view_dashboard` là `chu, nv_kho, quan_ly`; lùi về `accounts 0002` → rỗng; migrate lại vẫn chạy được.
- Adapter không sửa nên không chạy lại pytest. Không sửa `frontend/`, `erp-console/`.
- RED trước GREEN: S6 lần đầu đỏ 15/16 (route 404, dashboard 200, thiếu quyền; test `405` đỏ vì 404). Thông điệp 401 tiếng Việt đỏ 3 test rồi mới sửa. S9 lần đầu đỏ 16/17. Test còn lại (`nguoi_khong_phai_staff_khong_vao_admin`) xanh ngay vì Django đã chặn sẵn, giữ lại làm test quyền.

### File đã sửa / thêm
| File | Thay đổi |
|---|---|
| `backend/apps/accounts/auth/services.py` (mới) | `describe_user(user)`, `home_for(groups)`: nghiệp vụ "tôi là ai" |
| `backend/apps/accounts/auth/api.py` (mới) | `MeView` (`GET`, `IsAuthenticated`) |
| `backend/apps/accounts/auth/tests/test_s6_me.py` (mới) | 16 test S6 + quyết định `view_dashboard` |
| `backend/config/api_urls.py` | thêm `path("auth/me/", MeView.as_view())` |
| `backend/apps/common/api.py` | `exception_handler`: 401 (`NotAuthenticated`/`AuthenticationFailed`) → `detail` = `"Thông tin xác thực không hợp lệ."` (`UNAUTHORIZED_DETAIL`) |
| `backend/apps/reports/models.py` | `ProfitReport.Meta.permissions` thêm `("view_dashboard", "Xem Tổng quan vận hành")` |
| `backend/apps/reports/dashboard_api.py` | `DashboardSummaryView`: `IsAuthenticated` → `CanViewDashboard` (đòi `reports.view_dashboard`) |
| `backend/apps/reports/migrations/0002_view_dashboard_permission.py` (sinh tự động) | `AlterModelOptions` thêm quyền. Model `managed=False` nên **không đụng bảng** |
| `backend/apps/accounts/migrations/0003_grant_view_dashboard.py` (viết tay) | data migration gán quyền cho `chu`, `quan_ly`, `nv_kho`, có hàm lùi |
| `backend/apps/common/admin.py` (mới) | `LockedFieldsAdminMixin` (S9) |
| `backend/apps/{inventory,delivery,purchasing,sales}/admin.py` | gắn mixin + `locked_fields` / `actor_fields` / `superuser_only_add`. `CostHidingMixin` lọc thêm field giá vốn ra khỏi `readonly_fields` |
| `backend/apps/common/tests/test_s9_admin_locked_fields.py` (mới) | 17 test S9 |
| README: `backend/README.md`, `apps/accounts/README.md`, `apps/accounts/auth/README.md`, `apps/common/README.md`, `apps/reports/README.md` | cập nhật module, quyền mới, số test |

### Quyết định 1 — quyền Tổng quan: **tạo `reports.view_dashboard`**
- Chọn tạo quyền thật thay vì dựa vào tiêu chí Group. Lý do: menu theo `permissions` như các mục khác, Chủ đổi được bằng Group mà không phải sửa code. Quan trọng hơn, backend **chặn thật**: trước đây `/api/dashboard/summary/` chỉ cần `IsAuthenticated`, nên NV giao và người không thuộc Group nào vẫn đọc được doanh thu hôm nay, đơn gần đây và tồn theo lô (BR-PQ-12).
- Gán cho: `chu`, `quan_ly`, `nv_kho`. `nv_giao` không có.
- **Đổi hành vi endpoint:** `GET /api/dashboard/summary/` giờ **403** với người chỉ thuộc `nv_giao` hoặc không thuộc Group nào; chưa đăng nhập vẫn 401. JSON trả về của người có quyền **không đổi**. Console cũ (`legacy/index.html`) với tài khoản NV giao sẽ nhận 403 **khi BE này được deploy**. Theo S7 thì NV giao vốn không được thấy Tổng quan.
- **FE sửa 1 dòng** `erp-console/shared/lib/nav.ts` (mục Tổng quan):
  `visible: (me) => has(me, "reports.view_dashboard"),` (bỏ `|| inGroup(me, "chu", "quan_ly", "nv_kho")`).
- Chỗ PO/doc cần cập nhật (BE không sửa `doc/`): thêm `reports.view_dashboard` vào bảng §1.5 của `business-process-spec.md`.

### Contract thực tế `GET /api/auth/me/`
- Header `Authorization: Token <token>` (Session cũng được). Chỉ có `GET`; method khác trả 405.
- Key cố định: `id, username, display_name, phone, groups, permissions, can_view_cost, can_view_profit, home`. **Chưa có** `group_labels` / `capabilities` (để S47).
- `groups`: thứ tự cố định `chu, quan_ly, nv_kho, nv_giao` (Group lạ xếp sau, theo tên).
- `permissions` = `sorted(user.get_all_permissions())`, gồm cả quyền gán riêng cho user.
- `display_name` lấy từ `StaffProfile.display_name`. Nếu trống hoặc không có hồ sơ thì dùng `first_name last_name`, rồi đến `username`. `phone` lấy từ `StaffProfile.phone`, không có hồ sơ thì là `""`.
- `can_view_cost` = `inventory.view_costprice`; `can_view_profit` = `reports.view_profitreport`.
- `home`: không có Group → `"no-role"`; **chỉ** thuộc `nv_giao` → `"my-deliveries"`; còn lại → `"dashboard"`. Superuser không có Group vẫn là `"no-role"` (S47-AC5), dù `permissions` của superuser là toàn bộ quyền.
- 401 (không token, token sai hoặc đã xoá, user `is_active=False`) cho **mọi** API: `{"detail": "Thông tin xác thực không hợp lệ."}`. Trước đây DRF trả tiếng Anh ("Authentication credentials were not provided.", "Invalid token.") hoặc "Người dùng không còn hoạt động, hoặc đã bị xoá.". Giờ dùng một thông điệp chung, không tiết lộ lý do.

JSON thật (dữ liệu seed migration, SQLite nháp; `id`/tên/SĐT do tôi tạo hồ sơ thử):

`chu` (`loc`):
```json
{"id": 1, "username": "loc", "display_name": "Lộc", "phone": "0909123456", "groups": ["chu"], "permissions": ["accounts.add_staffprofile", "accounts.change_staffprofile", "accounts.delete_staffprofile", "accounts.manage_staff", "accounts.view_auditlog", "accounts.view_staffprofile", "auth.add_group", "auth.add_user", "auth.change_group", "auth.change_user", "auth.delete_group", "auth.delete_user", "auth.view_group", "auth.view_user", "catalog.add_bundleline", "catalog.add_item", "catalog.add_itemgroup", "catalog.add_itemprice", "catalog.add_pricelist", "catalog.add_pricingrule", "catalog.change_bundleline", "catalog.change_item", "catalog.change_itemgroup", "catalog.change_itemprice", "catalog.change_pricelist", "catalog.change_pricingrule", "catalog.delete_bundleline", "catalog.delete_item", "catalog.delete_itemgroup", "catalog.delete_itemprice", "catalog.delete_pricelist", "catalog.delete_pricingrule", "catalog.view_bundleline", "catalog.view_item", "catalog.view_itemgroup", "catalog.view_itemprice", "catalog.view_pricelist", "catalog.view_pricingrule", "delivery.add_deliverynote", "delivery.change_deliverynote", "delivery.delete_deliverynote", "delivery.view_deliverynote", "inventory.add_batch", "inventory.add_returntostock", "inventory.add_stockentry", "inventory.add_stockreconciliation", "inventory.add_stockreconciliationline", "inventory.add_warehouse", "inventory.approve_returntostock", "inventory.approve_stockreconciliation", "inventory.change_batch", "inventory.change_returntostock", "inventory.change_stockentry", "inventory.change_stockreconciliation", "inventory.change_stockreconciliationline", "inventory.change_warehouse", "inventory.close_batch", "inventory.delete_batch", "inventory.delete_returntostock", "inventory.delete_stockentry", "inventory.delete_stockreconciliation", "inventory.delete_stockreconciliationline", "inventory.delete_warehouse", "inventory.publish_batch", "inventory.view_batch", "inventory.view_costprice", "inventory.view_returntostock", "inventory.view_stockentry", "inventory.view_stockledgerentry", "inventory.view_stockreconciliation", "inventory.view_stockreconciliationline", "inventory.view_warehouse", "purchasing.add_purchasecost", "purchasing.add_purchasecostallocation", "purchasing.add_purchaseinvoice", "purchasing.add_purchasereceipt", "purchasing.add_purchasereceiptline", "purchasing.add_supplier", "purchasing.change_purchasecost", "purchasing.change_purchasecostallocation", "purchasing.change_purchaseinvoice", "purchasing.change_purchasereceipt", "purchasing.change_purchasereceiptline", "purchasing.change_supplier", "purchasing.delete_purchasecost", "purchasing.delete_purchasecostallocation", "purchasing.delete_purchaseinvoice", "purchasing.delete_purchasereceipt", "purchasing.delete_purchasereceiptline", "purchasing.delete_supplier", "purchasing.view_purchasecost", "purchasing.view_purchasecostallocation", "purchasing.view_purchaseinvoice", "purchasing.view_purchasereceipt", "purchasing.view_purchasereceiptline", "purchasing.view_supplier", "reports.view_dashboard", "reports.view_profitreport", "sales.add_customer", "sales.add_paymenttransaction", "sales.add_refund", "sales.cancel_paid_order", "sales.change_customer", "sales.change_paymenttransaction", "sales.change_refund", "sales.change_salesinvoice", "sales.change_salesorder", "sales.confirm_payment_manual", "sales.confirm_refund", "sales.create_refund", "sales.delete_customer", "sales.delete_paymenttransaction", "sales.delete_refund", "sales.view_customer", "sales.view_paymenttransaction", "sales.view_refund", "sales.view_salesinvoice", "sales.view_salesinvoiceline", "sales.view_salesinvoicelinebatch", "sales.view_salesorder", "sales.view_salesorderline", "sales.view_salesorderlinebatch"], "can_view_cost": true, "can_view_profit": true, "home": "dashboard"}
```

`quan_ly` (`ql1`):
```json
{"id": 2, "username": "ql1", "display_name": "Chị Hạnh", "phone": "0909000111", "groups": ["quan_ly"], "permissions": ["accounts.view_staffprofile", "auth.view_user", "catalog.view_bundleline", "catalog.view_item", "catalog.view_itemgroup", "catalog.view_itemprice", "catalog.view_pricelist", "catalog.view_pricingrule", "delivery.add_deliverynote", "delivery.change_deliverynote", "delivery.view_deliverynote", "inventory.add_stockentry", "inventory.add_stockreconciliation", "inventory.add_stockreconciliationline", "inventory.approve_returntostock", "inventory.approve_stockreconciliation", "inventory.change_stockentry", "inventory.change_stockreconciliation", "inventory.change_stockreconciliationline", "inventory.publish_batch", "inventory.view_batch", "inventory.view_returntostock", "inventory.view_stockentry", "inventory.view_stockledgerentry", "inventory.view_stockreconciliation", "inventory.view_stockreconciliationline", "inventory.view_warehouse", "purchasing.add_purchasereceipt", "purchasing.add_purchasereceiptline", "purchasing.add_supplier", "purchasing.change_purchasereceipt", "purchasing.change_purchasereceiptline", "purchasing.change_supplier", "purchasing.view_purchaseinvoice", "purchasing.view_purchasereceipt", "purchasing.view_purchasereceiptline", "purchasing.view_supplier", "reports.view_dashboard", "sales.add_customer", "sales.add_refund", "sales.cancel_paid_order", "sales.change_customer", "sales.change_refund", "sales.create_refund", "sales.view_customer", "sales.view_paymenttransaction", "sales.view_refund", "sales.view_salesinvoice", "sales.view_salesinvoiceline", "sales.view_salesorder", "sales.view_salesorderline"], "can_view_cost": false, "can_view_profit": false, "home": "dashboard"}
```

`nv_kho` + `nv_giao` (`kho1`). Mọi quyền của `nv_giao` đều nằm trong `nv_kho`, nên người **chỉ** thuộc `nv_kho` nhận đúng danh sách này, với `groups: ["nv_kho"]`:
```json
{"id": 3, "username": "kho1", "display_name": "Anh Tâm", "phone": "0909000222", "groups": ["nv_kho", "nv_giao"], "permissions": ["accounts.view_staffprofile", "auth.view_user", "catalog.view_bundleline", "catalog.view_item", "catalog.view_itemgroup", "delivery.add_deliverynote", "delivery.change_deliverynote", "delivery.view_deliverynote", "inventory.add_returntostock", "inventory.add_stockentry", "inventory.add_stockreconciliation", "inventory.add_stockreconciliationline", "inventory.change_stockentry", "inventory.change_stockreconciliation", "inventory.change_stockreconciliationline", "inventory.view_batch", "inventory.view_returntostock", "inventory.view_stockentry", "inventory.view_stockledgerentry", "inventory.view_stockreconciliation", "inventory.view_stockreconciliationline", "inventory.view_warehouse", "purchasing.add_purchasereceipt", "purchasing.add_purchasereceiptline", "purchasing.change_purchasereceipt", "purchasing.change_purchasereceiptline", "purchasing.view_purchasereceipt", "purchasing.view_purchasereceiptline", "purchasing.view_supplier", "reports.view_dashboard", "sales.view_customer", "sales.view_salesinvoice", "sales.view_salesinvoiceline", "sales.view_salesorder", "sales.view_salesorderline"], "can_view_cost": false, "can_view_profit": false, "home": "dashboard"}
```

`nv_giao` (`giao1`):
```json
{"id": 4, "username": "giao1", "display_name": "Anh Phúc", "phone": "0909000333", "groups": ["nv_giao"], "permissions": ["accounts.view_staffprofile", "auth.view_user", "delivery.change_deliverynote", "delivery.view_deliverynote", "inventory.add_returntostock", "inventory.view_returntostock", "sales.view_customer", "sales.view_salesorder", "sales.view_salesorderline"], "can_view_cost": false, "can_view_profit": false, "home": "my-deliveries"}
```

Không Group (`moi1`, không có hồ sơ):
```json
{"id": 5, "username": "moi1", "display_name": "moi1", "phone": "", "groups": [], "permissions": [], "can_view_cost": false, "can_view_profit": false, "home": "no-role"}
```

**So với mock FE (`erp-console/features/auth/mock.ts`):** mọi quyền trong mock đều có thật (máy so: tập "mock có mà thật không có" rỗng ở cả 4 vai). Mock chỉ là tập con: `loc` 31/122, `ql1` 22/51, `kho1` 13/35, `giao1` 3/9. Điểm FE cần biết:
1. **`nv_kho` có `catalog.view_item`** (mock không có). Với `nav.ts` hiện tại, `kho1` sẽ thấy menu **"Danh mục & giá"**. Nhưng `nv_kho` **không có** `view_itemprice` / `view_pricelist` / `view_pricingrule`, nên gọi giá sẽ bị 403. FE chọn một trong hai: chỉ hiện phần mặt hàng, hoặc đổi điều kiện mục thành `catalog.view_itemprice`. Cần PO chốt.
2. `nv_kho` có thêm `sales.view_salesinvoice`, `sales.view_customer`, `purchasing.view_supplier`, `inventory.view_stockentry`, `inventory.view_warehouse`. Không có `sales.view_refund` và `sales.view_paymenttransaction` (khớp mock).
3. Tên quyền Tầng 2 trong mock đều đúng codename thật.

### S9 — khoá field trong Django Admin
Người **không phải superuser** (kể cả `chu`): các field dưới đây là chỉ đọc, Django bỏ qua giá trị gửi lên trong POST. **Superuser** sửa được, nhưng mọi thay đổi ở các field này ghi `AuditLog(action="admin_edit", changes={field: {"from", "to"}})`. FK ghi theo id; Decimal ghi dạng chuỗi như người nhập.

| Admin | Field khoá (`locked_fields`) | Người ghi (`actor_fields`, tự ghi theo người đăng nhập khi tạo) | Tạo tay (người thường) |
|---|---|---|---|
| Lô | `status, qty_received, qty_available, qty_reserved, purchase_rate, landed_unit_cost, expiry_date, closed_at, closed_by` (trùng S3) | — | **không** (lô chỉ sinh từ phiếu nhập) |
| Phiếu giao | `status, assigned_to, failed_attempts, completed_at, sales_invoice` (trùng S3) | — | **không** |
| Hàng hoàn | `status, decision, approved_by` | `created_by` | có |
| Kiểm kê | `status, approved_by, approved_at` | `created_by` | có |
| Phiếu nhập | `status` | `created_by` | có |
| Phiếu hoàn | `status, amount, is_partial, sales_invoice, bank_txn_ref, confirmed_by, confirmed_at` | `created_by` | **không** |
| Đơn | `status, total_amount, customer, booked_expires_at` | — | không (có từ trước, BR-PQ-11) |
| Hoá đơn bán | `status, amount, sales_order, customer, issued_at, payment_txn_ref, payment_method` | — | không (có từ trước) |
| Giao dịch thanh toán | `bank_txn_id, sales_order, amount, match_status, source, raw_payload, received_at` | — | **không** |
| Mặt hàng, giá niêm yết, NCC, bảng giá, ưu đãi | không khoá (S9-AC5) | | |

- Không rò giá vốn qua chỉ đọc: `CostHidingMixin.get_readonly_fields` bỏ `purchase_rate` và `landed_unit_cost` với người thiếu `view_costprice`. Có test `test_s9_ac1_quan_ly_khong_thay_gia_von_trong_form_chi_doc`.
- Superuser tạo mới trong Admin **không** ghi AuditLog. Chỉ ghi khi sửa bản ghi đã có (AC3 chỉ nói về sửa).

### Rule đã cài
- **BR-PQ-09** (S6): quyền = hợp các Group. Menu dựa trên `permissions`, `home` tính theo Group.
- **BR-PQ-01 / Q5** (S6-AC5): `is_active=False` → token cũ trả 401 ngay ở mọi API. DRF `TokenAuthentication` đã chặn sẵn, có test khoá lại hành vi này. Không hết hạn theo thời gian.
- **BR-PQ-12**: `/api/dashboard/summary/` đòi `reports.view_dashboard`.
- **BR-PQ-14** (S9): Admin không còn là cửa sau với người không phải superuser.
- **BR-PQ-05** (S9-AC3): superuser sửa field khoá thì có AuditLog `admin_edit`.
- **BR-PQ-16** (S9, phần Admin): người thường tạo chứng từ trong Admin → `created_by` = mình, không chọn được người khác.

### Migration
- `reports/0002_view_dashboard_permission.py` (sinh tự động): chỉ `AlterModelOptions`. `ProfitReport` có `managed=False`, nên **không có DDL**. Permission row được tạo ở `post_migrate` và ở 0003.
- `accounts/0003_grant_view_dashboard.py` (viết tay theo mẫu 0002): gọi `create_permissions` cho app `reports`, sau đó `group.permissions.add` cho `chu`, `quan_ly`, `nv_kho`. Hàm lùi gỡ quyền khỏi 3 Group. Idempotent (`add` 2 lần không tạo trùng). Lý do phải gán riêng cho `chu`: 0002 chỉ gán các quyền đã có tại thời điểm 0002 chạy.

### Lệch so với story / quyết định cần PO biết
1. **Ngoài S6:** thông điệp 401 được đặt chung cho mọi API (theo contract S6). Trước đây là tiếng Anh hoặc câu dịch của DRF.
2. **Ngoài S6:** `/api/dashboard/summary/` bị khoá bằng quyền mới (xem Quyết định 1). Đây là thay đổi hành vi endpoint cũ.
3. **S9, thêm ngoài AC:** người không phải superuser không tạo tay được Lô, Phiếu giao, Phiếu hoàn, Giao dịch thanh toán trong Admin. Lý do: các field bắt buộc đều đã khoá; nếu cho tạo tay thì chính là cửa sau đặt tồn/tiền. Riêng Hoá đơn bán và Đơn đã bị chặn từ trước.
4. **S9-AC2 "đơn":** khoá thêm cả `SalesInvoice` (hoá đơn bán) vì đây là chứng từ tiền của đơn. `delivery_address` và `phone` của đơn vẫn sửa được (sửa thông tin liên hệ).

### Còn nợ / giả định
1. **Rò giá vốn trong Admin, có từ trước, chưa sửa:** inline `PurchaseReceiptLine` trong Admin phiếu nhập hiện cột `rate` (giá mua) cho mọi staff có quyền xem phiếu nhập, kể cả `quan_ly`/`nv_kho` nếu được bật `is_staff`. Việc này thuộc S30 (ẩn giá mua), nhưng nên sửa sớm. Hiện tại chỉ an toàn nếu không bật `is_staff` cho quan_ly/nv_kho.
2. Admin chưa khoá: `PurchaseCost.amount/allocation_method` (đổi giá vốn mà không phân bổ lại), `PurchaseInvoice.amount/is_paid`, `StockEntry.qty_change`, các dòng inline kiểm kê (`system_qty`, `difference_qty`). AC2 không liệt kê các field này; nên xử lý cùng S31/S32/S33/S34. Hiện chỉ `chu` có quyền sửa chúng.
3. Superuser sửa `landed_unit_cost` trong Admin chỉ ghi AuditLog, **không** tính lại gì (đường cứu hộ đúng nghĩa).
4. `group_labels` / `capabilities` (S47) chưa làm.
5. Cần cập nhật `business-process-spec.md` §1.5 thêm `reports.view_dashboard` (BE không sửa `doc/`).
6. Deploy: phải chạy `migrate` (2 migration mới). Chưa deploy.

---

## Lô L5 — S41, S42 (BE) · 2026-09-24

### Kết quả kiểm chứng
- `cd backend && .venv/bin/python manage.py test` → **Ran 240 tests, OK** (~9 s). Mốc trước 175, thêm 65: S41 API 37, S41-AC8 Admin 4, S42 20, vá rò `rate` trong Admin 4.
- `makemigrations --check --dry-run` → `No changes detected` (**không có migration mới**). `manage.py check` → không có lỗi.
- RED trước GREEN: lần chạy đầu 61/65 đỏ (route 404, admin mở được, `rate` hiện). 4 test xanh ngay là test 401 (DRF chặn sẵn) và `test_chu_van_thay_rate`, giữ lại làm test chặn hồi quy.
- Một test tôi sửa sau khi chạy: S41-AC10 ban đầu cấm chuỗi `password` xuất hiện ở bất kỳ đâu trong JSON, nhưng contract có action `"reset_password"`. Đổi thành cấm key `"password"` / `"token"`, cấm hash mật khẩu và giá trị token thật.
- Adapter, `frontend/`, `erp-console/` không sửa.

### File đã sửa / thêm
| File | Thay đổi |
|---|---|
| `backend/apps/accounts/staff/services.py` (mới) | `create_staff`, `update_profile`, `set_groups`, `deactivate`, `reactivate`, `reset_password`, `available_actions`; `StaffPermissionError` (BR-PQ-17 → 403) |
| `backend/apps/accounts/staff/api.py` (mới) | `StaffViewSet` + `CanManageStaff` (`accounts.manage_staff`) |
| `backend/apps/accounts/staff/serializers.py` (mới) | `staff_item()`: JSON tường minh |
| `backend/apps/accounts/staff/tests/` (mới) | `helpers.py`, `test_s41_staff.py`, `test_s42_staff.py`, `test_s41_admin.py` |
| `backend/config/api_urls.py` | `router.register("staff", StaffViewSet, basename="staff")` |
| `backend/apps/accounts/admin.py` | Gỡ `UserAdmin`/`GroupAdmin` mặc định, đăng ký lại với `SuperuserOnlyAdminMixin`; `UserAdmin.save_related` ghi AuditLog `staff_groups_change` |
| `backend/apps/common/exceptions.py` | `BusinessError.http_status = 400` (lớp con đặt được 403) |
| `backend/apps/common/api.py` | `exception_handler` dùng `exc.http_status` thay vì cố định 400. Hành vi cũ không đổi |
| `backend/apps/accounts/auth/services.py` | `_sorted_groups` → `sorted_groups` (public, staff dùng lại). Không đổi hành vi |
| `backend/apps/purchasing/admin.py` | `PurchaseReceiptLineInline` + `CostHidingMixin(cost_fields=("rate",))`; người thiếu `view_costprice` không thêm dòng trong Admin |
| `backend/apps/purchasing/models/receipts.py` | `PurchaseReceiptLine.__str__` bỏ `@ rate` (không cần migration) |
| `backend/apps/purchasing/receipts/tests/test_admin_rate_hidden.py` (mới) | 4 test không rò `rate` |
| README: `backend/README.md`, `apps/accounts/README.md`, `apps/accounts/staff/README.md` | module mới, số test |

### Contract thực tế
Mọi endpoint: `Authorization: Token …` (Session cũng được), đòi `accounts.manage_staff` (seed chỉ `chu` có). Chưa đăng nhập → 401 `{"detail": "Thông tin xác thực không hợp lệ."}`; thiếu quyền → 403 `{"detail": "Bạn không được cấp quyền để thực hiện hành động này."}` (câu của DRF, không có `code`). Lỗi nghiệp vụ → `{"detail", "code"}`. Field lạ trong body của mọi action → 400 `BR-PQ-08` `"Trường không được phép: …"`.

```
GET   /api/staff/?is_active=true|false      (bỏ trống = tất cả; sắp theo username)
200 [{"id":2,"username":"kho1","display_name":"Anh Tâm","phone":"0909000222","groups":["nv_kho"],
      "is_active":true,"last_login":null,"available_actions":["edit","set_groups","reset_password","deactivate"]},
     {"id":1,"username":"loc","display_name":"Lộc","phone":"0909123456","groups":["chu"],
      "is_active":true,"last_login":null,"available_actions":["edit"]}]
GET   /api/staff/{id}/                       → 200 một dòng như trên
POST  /api/staff/  {"username","display_name","phone","groups","password"}
201 {"id":20,"username":"giao4","display_name":"Anh Năm","phone":"0909333444","groups":["nv_giao"],
     "is_active":true,"last_login":null,"available_actions":["edit","set_groups","reset_password","deactivate"]}
PATCH /api/staff/{id}/  {"display_name"?, "phone"?}   → 200 một dòng
PUT   /api/staff/{id}/groups/  {"groups":["nv_giao","nv_kho"]}
200 {"groups":["nv_kho","nv_giao"],"added":["nv_kho"],"removed":[]}
POST  /api/staff/{id}/deactivate/      {}                   → 200 {"is_active": false}
POST  /api/staff/{id}/reactivate/      {}                   → 200 {"is_active": true}
POST  /api/staff/{id}/reset-password/  {"new_password":"…"} → 200 {}
PUT /api/staff/{id}/, DELETE /api/staff/{id}/  → 405 (người có manage_staff); 403 với người không có quyền
```
Ghi chú contract:
- `display_name`: lấy `StaffProfile.display_name`, trống thì dùng `first_name last_name`, rồi `username` (giống `/api/auth/me/`). `phone` là `""` khi user chưa có hồ sơ (vd `admin`).
- `groups` luôn theo thứ tự `chu, quan_ly, nv_kho, nv_giao`, kể cả trong `added`/`removed`. Client gửi thứ tự nào cũng được.
- `last_login` là ISO theo giờ VN (`+07:00`) hoặc `null`.
- `available_actions` tính theo **người đang xem**: chính mình → `["edit"]`. Đã nghỉ → `["edit","reactivate"]`. Tài khoản Chủ khi người xem không phải Chủ/superuser → `[]`. Tài khoản superuser khi người xem không phải superuser → `[]`. Chủ đang làm cuối cùng → không có `deactivate`.
- Danh sách gồm **mọi** User, kể cả `admin`/superuser không có hồ sơ (tài khoản này hiện `available_actions: []` với Chủ không phải superuser).
- `POST` trả về **đủ một dòng** (bộ key lớn hơn contract, vẫn có `id, username, groups, is_active`). `PATCH` cũng trả về một dòng.
- `PATCH` cho user chưa có hồ sơ: phải có `phone`, và hệ thống tạo `StaffProfile`.

Lỗi (thông điệp thật):
| Tình huống | HTTP | `code` | `detail` |
|---|---|---|---|
| Thiếu/rỗng SĐT (tạo, PATCH) | 400 | BR-PQ-08 | `Số điện thoại là bắt buộc.` |
| Username trùng (không phân biệt hoa thường) | 400 | BR-PQ-08 | `Tên đăng nhập đã tồn tại.` |
| Username rỗng / có dấu cách hoặc ký tự lạ | 400 | BR-PQ-08 | `Tên đăng nhập là bắt buộc.` / `Tên đăng nhập chỉ gồm chữ, số và @ . + - _ (không dấu cách).` |
| Mật khẩu yếu (Django validator, tiếng Việt, nối bằng dấu cách) | 400 | BR-PQ-08 | vd `Mật khẩu quá ngắn. Nó phải chứa ít nhất 8 ký tự. Mật khẩu này quá phổ biến.` |
| Mật khẩu rỗng | 400 | BR-PQ-08 | `Mật khẩu là bắt buộc.` |
| Nhóm lạ / `groups` không phải mảng | 400 | BR-PQ-08 | `Nhóm không tồn tại: admin. Chỉ dùng: chu, quan_ly, nv_kho, nv_giao.` / `Danh sách nhóm phải là mảng tên nhóm.` |
| Tự đổi nhóm của mình (kể cả superuser) | 400 | BR-PQ-17 | `Không thể tự đổi nhóm của chính mình.` |
| Tự cho nghỉ mình | 400 | BR-PQ-17 | `Không thể tự cho nghỉ chính mình.` |
| Tự đặt lại mật khẩu mình qua endpoint này | 400 | BR-PQ-17 | `Không tự đặt lại mật khẩu của mình ở đây — dùng Đổi mật khẩu.` |
| Không phải Chủ/superuser mà thêm/bỏ nhóm `chu` (kể cả khi tạo) | 403 | BR-PQ-17 | `Chỉ Chủ mới gán hoặc bỏ nhóm Chủ.` |
| Không phải Chủ/superuser mà đụng tài khoản Chủ (sửa, đổi nhóm khác, nghỉ, làm lại, đặt MK) | 403 | BR-PQ-17 | `Chỉ Chủ mới thao tác trên tài khoản Chủ.` |
| Không phải superuser mà đụng tài khoản superuser | 403 | BR-PQ-17 | `Chỉ superuser mới thao tác trên tài khoản superuser.` |
| Bỏ `chu` của Chủ đang làm cuối cùng | 400 | BR-PQ-18 | `Phải còn ít nhất một Chủ đang làm.` |
| Cho nghỉ Chủ đang làm cuối cùng | 400 | BR-PQ-18 | `Không thể cho nghỉ Chủ cuối cùng.` |
| Còn phiếu DELIVERING | 400 | BR-GH-08 | `Còn 2 phiếu Đang giao (GH-INV-DH01-A1B2C, GH-INV-DH02-…) — xử lý trước khi cho nghỉ.` (mã phiếu thật `GH-…`, sắp theo mã; story ghi mẫu `PG-…`) |
| Cho nghỉ người đã nghỉ / làm lại người đang làm | 400 | BR-PQ-01 | `Tài khoản này đã nghỉ.` / `Tài khoản này đang làm.` |

Thứ tự kiểm: quyền `manage_staff` (403) → tự thao tác (400) → nhóm lạ (400) → BR-PQ-17 thẩm quyền (403) → BR-PQ-18 (400) → BR-GH-08 (400).

### Rule đã cài
- **BR-PQ-08**: tạo tài khoản bắt buộc SĐT; username duy nhất; mật khẩu qua `AUTH_PASSWORD_VALIDATORS` (thông điệp tiếng Việt vì `LANGUAGE_CODE="vi"`). User mới có `is_staff=False` và không phải superuser. Không có đường API nào đặt `is_staff`/`is_superuser`.
- **BR-PQ-17**: như bảng lỗi. Tính "là Chủ" theo Group `chu` hiện tại của người thao tác.
- **BR-PQ-18**: "Chủ đang làm" = User `is_active=True` thuộc Group `chu` (superuser không thuộc `chu` **không** tính). Khoá `select_for_update` các dòng Chủ đang làm trước khi kiểm, nên hai thao tác đồng thời không cùng bỏ được Chủ cuối.
- **BR-PQ-01 / Q5 / C8**: cho nghỉ → `is_active=False`, `StaffProfile.status=INACTIVE`, xoá Token → lần gọi kế tiếp 401. Session Admin cũng chết vì Django không nhận user inactive. Đặt lại mật khẩu → xoá Token; session chết theo hash mật khẩu. Cho làm lại **không** cấp token: người đó phải đăng nhập lại bằng mật khẩu cũ.
- **BR-PQ-02**: không xoá User (DELETE 405). Chứng từ cũ vẫn giữ FK tới người đó.
- **BR-PQ-03**: đổi nhóm không động tới chứng từ cũ (có test).
- **BR-PQ-04**: AuditLog `staff_create` (username/display_name/phone/groups từ → tới), `staff_update` (chỉ field đổi), `staff_groups_change` (`{"groups": {"from", "to"}}`, chỉ ghi khi có thay đổi), `staff_deactivate` / `staff_reactivate` (`is_active` từ → tới, note số token thu), `staff_password_reset` (không có `changes`, note "Đặt lại mật khẩu; thu hồi N token"). Không log nào chứa mật khẩu hoặc hash (có test).
- **BR-GH-08**: không cho nghỉ người còn phiếu `DELIVERING`.
- **S41-AC8 (Admin)**: trang User/Group trong Django Admin **chỉ superuser** được xem/sửa/thêm/xoá, và menu cũng ẩn. Lý do: Chủ có `auth.change_user`/`change_group`; nếu mở Admin thì Chủ tự bật `is_superuser` hoặc sửa quyền Group được, tức là cửa sau vượt BR-PQ-17. Ngoại lệ: ô autocomplete chọn người ở form khác (vd Hồ sơ nhân viên) vẫn chạy cho người có `auth.view_user`. Superuser đổi nhóm trong Admin → AuditLog `staff_groups_change` (note "Đổi nhóm trong Django Admin.").

### Vá rò giá vốn trong Admin (nợ #1 của L3–L4, ưu tiên cao)
- Inline dòng phiếu nhập: cột `rate` bị loại khỏi form (cả input lẫn tiêu đề "Đơn giá mua") với người thiếu `inventory.view_costprice`. Họ cũng không thêm dòng mới trong Admin, vì `rate` bắt buộc mà họ không được thấy; nếu cho thêm thì sẽ lỗi 500. Nhập hàng vẫn đi qua API. POST cố gửi `rate` → DB không đổi (có test).
- `PurchaseReceiptLine.__str__` trước đây là `"CA01 × 12.5kg @ 81234.56"`. Chuỗi này hiện ở mỗi dòng inline và trong `AuditLog.object_repr`, nên cũng là đường rò. Nay là `"CA01 × 12.5kg"`.
- `chu` vẫn thấy và sửa `rate` như cũ.

### Lệch so với story / giả định cần PO biết
1. **Mở rộng BR-PQ-17 (tôi đặt, cần PO xác nhận):**
   (a) Chỉ superuser thao tác trên tài khoản superuser. Nếu không, Chủ (không phải superuser) đặt lại mật khẩu `admin` rồi đăng nhập Admin bằng quyền superuser.
   (b) Không tự đặt lại mật khẩu của mình qua `reset-password`, vì endpoint này không hỏi mật khẩu cũ. Tự đổi mật khẩu thuộc S46.
   (c) Người không phải Chủ không sửa hồ sơ (PATCH) và không cho làm lại tài khoản Chủ.
2. `POST /api/staff/` trả về một dòng đầy đủ thay vì chỉ 4 key. Đây là bộ key lớn hơn contract, FE không phải đổi gì.
3. Cho nghỉ hoặc làm lại lần hai → 400 (`BR-PQ-01`), không idempotent 200. Mục đích là FE biết trạng thái đã đổi ở máy khác.
4. Lỗi 403 do thiếu `manage_staff` là câu mặc định của DRF (không có `code`). 403 do BR-PQ-17 có `code`.
5. `BusinessError` có thêm `http_status`; handler chung dùng nó. Mọi lỗi nghiệp vụ cũ vẫn 400.

### Còn nợ / giả định
1. **S42-AC1 "không có trong `GET /api/delivery/couriers/`"**: endpoint này **chưa tồn tại** (thuộc S18). Khi làm S18 phải lọc `is_active=True`. Test S42 hiện chỉ kiểm 401, token bị xoá và chứng từ cũ còn giữ người giao.
2. Superuser đổi nhóm trong Admin **không** bị chặn BR-PQ-17/18 (đường cứu hộ, giống S9). Chỉ ghi AuditLog. Thêm hoặc bỏ nhóm qua trang Group (sửa `user_set`) không đi qua `UserAdmin.save_related`, nên không có log `staff_groups_change`. Trang Group chỉ superuser mở được.
3. SĐT chỉ kiểm bắt buộc và ≤ 20 ký tự, không kiểm định dạng. Cần PO chốt định dạng.
4. Cần cập nhật `business-process-spec.md` §1 thêm BR-PQ-17, BR-PQ-18 (C9 đã duyệt; BE không sửa `doc/`).
5. S46 (đăng xuất thu token, tự đổi mật khẩu) và S47 (`group_labels`/`capabilities`) chưa làm.
6. Không có migration mới. Chưa deploy.

---

## Lô L4 — S8 (FE): Tổng quan, Đơn, Kho & lô trên console mới · 2026-09-24

### Kết quả kiểm chứng
- `cd erp-console && ./node_modules/.bin/tsc --noEmit` → sạch. `npm run build` → sạch, 16 trang tĩnh. `NEXT_PUBLIC_USE_MOCK=1 npm run build` → cũng sạch.
- Bản build thật **không chứa code mock**: grep `demo1234` / `__caveMock` / dữ liệu seed (`Ghe Tư Hải`) trong `out/_next` ra 0 file. `out/` hiện tại là bản build thật.
- E2E Playwright chạy trên bản build mock phục vụ tĩnh (`http.server` 3101 và bản cũ ở 3102; **đã tắt cả hai**):
  - `e2e/s8_views.py` (mới): **43/43 PASS**.
  - `e2e/s7_shell.py` chạy lại để kiểm hồi quy: **25/25 PASS**.

| AC | Kết quả |
|---|---|
| S8-AC1 | **So thật với bản cũ.** Kịch bản lấy đúng JSON mock mà console mới nhận (`__caveMock.dashboardJson`), bơm vào `legacy/index.html` bằng `page.route` (chặn API Cloud Run), rồi so từng ô. KPI (4 ô), 8 đơn gần nhất, bảng lô, 6 cảnh báo cận hạn, 8 dòng sổ kho, màn Đơn (trừ cột đếm lùi vì phụ thuộc giờ) và màn Kho & lô đều **trùng**. So sánh đã chuẩn hoá định dạng: `₫ 1.092.000` ↔ `1.092.000 ₫`, `18.5 kg` ↔ `18,5 kg`, `09-28` ↔ `28/09` |
| S8-AC2 | `ql1`: Tổng quan và Kho & lô không có cột giá vốn, KPI "Giá trị tồn kho" hiện "—" kèm "cần quyền xem giá vốn". JSON mock (dựng theo BE) không có key `unit_cost`. **Phía BE xem mục Lệch 1–2** |
| S8-AC3 | `loc`: có cột "Giá vốn/kg" có tiền ở Tổng quan và Kho & lô |
| S8-AC4 | Mock trả 500 → "Không tải được dữ liệu, thử lại." kèm nút **Thử lại**, menu vẫn còn (không trắng trang). Hết lỗi rồi bấm Thử lại thì hiện số liệu. Nếu đã có số mà làm mới bị lỗi: giữ số cũ và hiện dải báo lỗi |
| S8-AC5 | `giao1` gõ `/overview/`, `/inventory/`, `/orders/` → "Bạn không có quyền xem mục này". Log request mock chỉ có `GET /api/auth/me/`. Tab "Hoạt động" báo không có quyền và không gọi API |
| S8-AC6 | `firebase.json` trỏ `out`. README ghi lệnh build/deploy. **`legacy/` CHƯA xoá**: lệnh xoá bị hệ thống quyền chặn (xoá file không hoàn tác được) → cần Duy/lead chạy hoặc cho phép |
| Thêm | Tìm phía máy, bỏ dấu ("ca thu" → 2 lô Cá thu), tìm được theo 4 số cuối SĐT, "Không khớp tìm kiếm", nút xoá tìm. Làm mới gọi lại đúng 1 request. Chuyển Tổng quan → Kho & lô → tab Hoạt động **không** phát thêm request (cache chung). Trạng thái rỗng. Trợ lý hiện "đang được nối, sắp có" (đã bỏ phần trả lời bằng regex). Menu `ql1`/`kho1` đúng theo quyền thật. 360px: không cuộn ngang ở cả 3 màn và ngăn kéo, mọi nút/link/ô nhập ≥ 44px. 1280px: bảng không cuộn ngang (kể cả 8 cột của Chủ) |

Ảnh chụp (`doc/features/2026-09-24-erp-console-noi-that/shots/`): `s8-desktop-1280-overview-chu.png`, `s8-desktop-1280-orders-chu.png`, `s8-desktop-1280-inventory-chu.png`, `s8-desktop-1280-inventory-quanly.png`, `s8-mobile-360-overview.png`, `s8-mobile-360-orders.png`, `s8-mobile-360-inventory.png`, `s8-mobile-360-activity.png`, `s8-mobile-360-error.png`.

### Cấu trúc / file
Ba module theo tính năng. Mỗi module có `api.ts`, `mock.ts`, `types.ts`, `components/` và `README.md`. Page chỉ bọc `<ViewGuard>` rồi render màn của module.
| File | Làm gì |
|---|---|
| `features/overview/` | `OverviewScreen` (toolbar, KPI, 8 đơn, cận hạn, bảng lô), `KpiTiles`; `getOverview()`, `filterRecentOrders()`, `filterBatches()` |
| `features/orders/` | `OrdersScreen` (8 đơn, 4 số cuối SĐT, giữ chỗ còn lại đếm lùi mỗi 30 s theo `expires_at` của BE); `getOrders()`, `filterOrders()` |
| `features/inventory/` | `InventoryScreen`, `ActivityFeed` (tab "Hoạt động" = 8 dòng sổ kho); `getInventory()`, `getActivity()`, `filterBatches()` |
| `shared/lib/dashboardSummary.ts` | contract đầy đủ `GET /api/dashboard/summary/` (kiểu khớp JSON `DashboardSummaryView`), khoá cache theo user |
| `shared/lib/dashboardSummary.mock.ts` | seed mock tính **giống BE**: KPI tính trên toàn bộ seed, 8 đơn, ≤20 lô hoạt động FIFO, ≤6 cận hạn, 8 dòng sổ kho, `unit_cost` theo quyền, 403 khi thiếu `reports.view_dashboard`. Chế độ `localStorage.cave_erp_mock_dashboard = fail/empty`. Chỉ được import từ `features/*/mock.ts` |
| `shared/lib/useResource.ts` | cache đọc nhỏ: cùng key thì 1 request đang bay; dùng lại trong 30 s; `reload()` cập nhật mọi nơi đang dùng; hết theo dõi khi unmount |
| `shared/lib/search.ts`, `status.ts`, `format.ts` (+`timeHM`, `dayMonth`, `remaining`), `http.ts` (+`loadErrorText`) | tìm bỏ dấu; màu/icon trạng thái; định dạng; câu lỗi khi tải |
| `shared/ui/ResourceView.tsx`, `Toolbar.tsx`, `StatusChip.tsx`, `EmptyRow.tsx`, `globals.css` | 3 trạng thái; ô tìm + Làm mới + "Cập nhật hh:mm"; chip; dòng rỗng; CSS S8 (bảng thành thẻ 2 cột khi < 640 px, bảng gọn khi vùng giữa hẹp) |
| `app/(console)/{overview,orders,inventory}/page.tsx` | thay `Placeholder` bằng màn của module |
| `app/(console)/layout.tsx`, `features/auth/components/ConsoleGate.tsx`, `shared/ui/RightRail.tsx` | tầng app ghép `<ActivityFeed/>` vào cột phải (auth không import module khác). RightRail chỉ mount một tab khi được mở lần đầu, nên không gọi API khi chưa ai xem |
| `shared/lib/nav.ts` | Tổng quan: `visible: (me) => has(me, "reports.view_dashboard")` (theo BE S6). Ghi chú cho Danh mục & giá: menu hiện khi có `catalog.view_item`, phần giá chờ `catalog.view_itemprice` (S38/S39) |
| `features/auth/mock.ts` | `GROUP_PERMS` **chép nguyên** `permissions` thật của `/api/auth/me/` theo từng Group (mục "Lô L3–L4"). Bỏ `group_labels` khỏi `me` mock vì BE chưa trả (S47) |
| `e2e/s8_views.py` (mới), `e2e/s7_shell.py` | kịch bản S8. Cả hai bỏ qua log "Failed to fetch RSC payload": đây là prefetch của Next bị huỷ khi kịch bản `goto` giữa chừng (server ghi BrokenPipe, `index.txt` vẫn trả 200), không phải lỗi app |
| `README.md` (erp-console) | sơ đồ thêm 3 module và file shared mới, cách thêm module, `legacy/` chờ xoá |

Quyết định: một endpoint dùng cho 3 module và cột phải, nên contract và seed để ở `shared/`. Mỗi module vẫn có `api.ts`/`mock.ts` riêng và chỉ khai kiểu phần nó đọc (`Pick<>`). Khi S10/S25 đổi sang endpoint riêng, chỉ sửa module đó.

### Endpoint & quyền
- S8 chỉ gọi `GET /api/dashboard/summary/`. Endpoint này cần `reports.view_dashboard` (BE S6); các vai `chu`/`quan_ly`/`nv_kho` đều có. Không gọi endpoint danh sách nào khác.
- Việc tiếp theo cần quyền: S10 `GET /api/orders/` cần `sales.view_salesorder`. S25 danh sách lô cần `inventory.view_batch`, sổ kho cần `inventory.view_stockledgerentry`.
- Màn Đơn / Kho & lô tạm đọc từ dashboard. Người có `view_salesorder`/`view_batch` mà **không** có `view_dashboard` (chỉ xảy ra khi gán quyền lẻ) sẽ nhận 403 và thấy thông điệp quyền của BE. Tab Hoạt động kiểm cả hai quyền nên không gọi API thừa.

### Lệch contract / cần BE, PO biết
1. **BE — `kpis.inventory_value` vẫn trả cho MỌI người** (`dashboard_api.py`, không kiểm `can_cost`). Số này = tổng tồn × `landed_unit_cost`, tức là con số suy ra từ giá vốn. S8-AC2 yêu cầu "response không có key giá vốn". FE đã ẩn (hiện "—"), nhưng BE nên bỏ key này hoặc trả `null` khi `can_cost=false`. Mock đang giữ y như BE hiện tại.
2. **BE — chưa có test** khoá việc thiếu `unit_cost` / `inventory_value` với Quản lý. S8-AC2 nói "test BE sẵn có", nhưng `test_s6_me.py` chỉ kiểm 200/403/401 của dashboard.
3. Định dạng khác bản cũ, **số giữ nguyên**: tiền `1.092.000 ₫` (cũ `₫ 1.092.000`), kg `18,5 kg` (cũ `18.5 kg`), hạn `28/09` (cũ `09-28`). Đã bỏ đường sparkline ở ô doanh thu vì bản cũ vẽ cứng, không phải dữ liệu. Chưa làm badge số trên menu (đơn chờ, số lô).
4. Màn "Đơn & tiền" vẫn chỉ có **8 đơn gần nhất** như bản cũ. Danh sách đầy đủ là S10.
5. `legacy/index.html` (cũ) **không có `<meta charset>`**. Nó chạy đúng trên Firebase nhờ header UTF-8. Kịch bản so sánh phải ép UTF-8.

### Còn nợ
1. **Xoá `erp-console/legacy/`** (S8-AC6). Hệ thống quyền chặn lệnh xoá, cần Duy/lead chạy. Sau khi xoá thì bỏ dòng "chờ xoá" trong `erp-console/README.md` và câu nhắc trong comment đầu `shared/ui/globals.css` / `themeScript.ts`. Kịch bản AC1 cần một bản cũ để so (biến `LEGACY_BASE`), không có thì tự bỏ qua. Bản sao tạm dùng lần này nằm trong scratchpad phiên làm việc, không nằm trong repo.
2. Chưa deploy (`cangca-erp` vẫn chạy bản HTML cũ). Build deploy phải set `NEXT_PUBLIC_API_BASE`. BE có `reports.view_dashboard` cũng phải deploy **cùng lúc hoặc trước**; nếu không, JSON `me` cũ không có quyền này và menu Tổng quan sẽ ẩn.
3. Chưa chạy trên backend thật (chỉ chạy mock). Khi có BE chạy máy mình: đăng nhập `ql1`, kiểm tab Network cho S8-AC2.

---

## Lô L6 — S46, S47 (BE) + vá rò giá vốn Tổng quan · 2026-09-24

### Kết quả kiểm chứng
- `cd backend && .venv/bin/python manage.py test` → **Ran 291 tests, OK** (~10 s). Mốc trước 240, thêm 51: S46 32, S47 15, vá rò Tổng quan 4. Sửa 1 test cũ `test_s6_ac1_dung_dung_cac_key_contract` (thêm 2 key S47 vào tập key mong đợi; key S6 giữ nguyên).
- `makemigrations --check --dry-run` → `No changes detected` (**không có migration**). `manage.py check` → không lỗi.
- RED trước GREEN: lần đầu 45 đỏ (route 404, thiếu key, `inventory_value` lộ cho Quản lý/NV kho). Test xanh ngay: `test_l6_chu_van_thay_gia_von`, `test_l6_nv_giao_403_chua_dang_nhap_401`, `test_s47_chua_dang_nhap_401`, `test_s46_ac1_khong_dung_token_cua_nguoi_khac` (giữ làm test chặn hồi quy). Test session `test_s46_ac2_session_giu_phien_sau_khi_tu_doi` đã thử bỏ `update_session_auth_hash` → đỏ, trả lại → xanh.
- Adapter, `frontend/`, `erp-console/` không sửa.

### File đã sửa / thêm
| File | Thay đổi |
|---|---|
| `backend/apps/accounts/auth/services.py` | `GROUP_LABELS`, `CAPABILITY_LABELS`; `describe_user` thêm `group_labels`, `capabilities`; `logout(user)`, `change_own_password(user, old_password, new_password)` |
| `backend/apps/accounts/auth/api.py` | `LogoutView`, `ChangePasswordView` |
| `backend/config/api_urls.py` | `auth/logout/`, `auth/change-password/` |
| `backend/apps/reports/dashboard_api.py` | `kpis.inventory_value` chỉ tính và chỉ có key khi có `inventory.view_costprice` |
| `backend/apps/accounts/auth/tests/test_s46_logout_password.py` (mới) | 32 test |
| `backend/apps/accounts/auth/tests/test_s47_me_labels.py` (mới) | 15 test |
| `backend/apps/reports/tests/test_dashboard_cost_leak.py` (mới) | 4 test |
| `backend/apps/accounts/auth/tests/test_s6_me.py` | tập key contract + 2 key S47 |
| README: `backend/README.md`, `apps/accounts/README.md`, `apps/accounts/auth/README.md`, `apps/reports/README.md` | endpoint mới, số test |

### Contract thực tế
Mọi endpoint: `Authorization: Token …` (Session cũng được). Chưa đăng nhập / token sai / đã thu / user đã nghỉ → 401 `{"detail": "Thông tin xác thực không hợp lệ."}`. Không cần quyền nào ngoài đăng nhập (ai cũng tự đăng xuất / tự đổi mật khẩu được, kể cả người chưa thuộc Group nào và superuser).

```
POST /api/auth/logout/   {}            → 204 (body rỗng). GET → 405.
```
- Xoá **mọi** token của người đó (C8: một token mỗi người → mọi máy văng). Đăng nhập bằng session (Admin) thì session cũng bị đóng.
- Gọi lại bằng token đã thu → 401. FE đang bỏ qua lỗi của lệnh này, nên không sao.
- Ghi AuditLog `logout` (actor = chính người đó, note "Đăng xuất; thu hồi N token."). Đây là phần thêm ngoài AC.

```
POST /api/auth/change-password/  {"old_password": "…", "new_password": "…"}
200 {"token": "9f1c…"}                      // token mới; mọi token cũ đã xoá
400 {"code": "AUTH_OLD_PASSWORD",  "detail": "Mật khẩu hiện tại không đúng."}          // sai hoặc thiếu old_password
400 {"code": "AUTH_WEAK_PASSWORD", "detail": "Mật khẩu quá ngắn. Nó phải chứa ít nhất 8 ký tự."}   // xem ghi chú
400 {"code": "AUTH_WEAK_PASSWORD", "detail": "Mật khẩu mới là bắt buộc."}              // rỗng / không phải chuỗi
400 {"code": "BR-PQ-17", "detail": "Trường không được phép: username. Chỉ đổi được mật khẩu của chính bạn."}
401 chưa đăng nhập · GET → 405
```
- Thứ tự kiểm: field lạ (BR-PQ-17) → mật khẩu hiện tại → độ mạnh mật khẩu mới. Sai cả hai thì báo `AUTH_OLD_PASSWORD`.
- Lỗi thì **không đổi gì**: mật khẩu cũ và token cũ vẫn dùng được (S46-AC3).
- Thành công: máy A dùng token trong JSON trả về. Máy B (cùng token cũ) → 401 ở lần gọi kế tiếp. Người đăng nhập bằng session vẫn giữ phiên hiện tại (`update_session_auth_hash`), và cũng nhận token mới.
- AuditLog `password_change_self` (actor = obj = chính người đó, không có `changes`, note "Tự đổi mật khẩu; thu hồi N token, cấp token mới."). Có test cấm mật khẩu cũ/mới, hash, token cũ/mới xuất hiện trong log.

```
GET /api/auth/me/   — giữ nguyên 9 key S6, thêm 2 key:
"group_labels": [{"code": "nv_kho", "label": "Nhân viên kho"}, {"code": "nv_giao", "label": "Nhân viên giao"}],
"capabilities": [{"code": "inventory.publish_batch", "label": "Mở bán lô"}, …]
```
- `group_labels`: cùng thứ tự với `groups` (`chu, quan_ly, nv_kho, nv_giao`). Nhãn: Chủ, Quản lý, Nhân viên kho, Nhân viên giao. Group lạ → nhãn là tên gốc. Không Group → `[]`.
- `capabilities`: quyền Tầng 2 người đó **đang có** (tính từ `get_all_permissions`, nên luôn là tập con của `permissions`; quyền gán riêng cho user cũng hiện; superuser có đủ). Thứ tự cố định:

| # | `code` | `label` |
|---|---|---|
| 1 | `inventory.publish_batch` | Mở bán lô |
| 2 | `sales.cancel_paid_order` | Huỷ đơn đã thanh toán |
| 3 | `sales.create_refund` | Tạo phiếu hoàn |
| 4 | `inventory.approve_returntostock` | Duyệt hàng hoàn |
| 5 | `inventory.approve_stockreconciliation` | Duyệt kiểm kê |
| 6 | `inventory.close_batch` | Chốt lô |
| 7 | `purchasing.add_purchasecost` | Nhập chi phí mua |
| 8 | `sales.confirm_refund` | Xác nhận đã hoàn tiền |
| 9 | `sales.confirm_payment_manual` | Xác nhận thanh toán thủ công |
| 10 | `accounts.manage_staff` | Quản lý nhân viên |
| 11 | `inventory.view_costprice` | Xem giá vốn |
| 12 | `reports.view_profitreport` | Xem báo cáo lãi lỗ |
| 13 | `reports.view_dashboard` | Xem Tổng quan |

  Theo seed: `chu` → đủ 13; `quan_ly` → 1–5 + 13; `nv_kho` → chỉ 13; `nv_giao` → `[]`.
- Tính lại mỗi lần gọi `me`: Chủ đổi nhóm → lần gọi `me` kế tiếp (cùng token) đã đổi, không cần đăng nhập lại (S47-AC2/AC3, có test).
- S47-AC4: người thiếu `view_costprice` không có `inventory.view_costprice` (và `reports.view_profitreport`) trong `capabilities`; `can_view_cost=false`.
- S47-AC5: superuser không Group → `group_labels: []`, `home: "no-role"` (như S6). `capabilities` của superuser vẫn đủ 13 vì superuser có mọi quyền. FE phải dựa vào `home`/`groups` để hiện màn "chưa được phân quyền", không dựa vào `capabilities`.

### Vá rò giá vốn `GET /api/dashboard/summary/` (coordinator giao thêm, ưu tiên cao)
- **Lỗi:** `kpis.inventory_value` (Σ `qty_available × landed_unit_cost`) được trả cho **mọi** người có `reports.view_dashboard`, gồm cả `quan_ly` và `nv_kho` (không có `view_costprice`). Vi phạm bất biến #1, S8-AC2.
- **Sửa:** chỉ tính và chỉ có key `inventory_value` khi có `inventory.view_costprice`. Thiếu quyền → **không có key** (không null). `batches[].unit_cost` đã ẩn đúng từ trước. `alerts`, `activity` (sổ kho), `recent_orders` không có field giá vốn (đã quét).
- **Test** (`apps/reports/tests/test_dashboard_cost_leak.py`): Quản lý, NV kho, NV kho + giao → quét đệ quy mọi key JSON, không có key nào trong `{inventory_value, unit_cost, landed_unit_cost, purchase_rate, rate, cost, cogs, profit, margin, gross_profit}`. Chuỗi giá vốn thật (`81234.56`, `812345.6`) cũng không xuất hiện trong body. `kpis` của Quản lý còn đúng 4 key. Chủ vẫn thấy `inventory_value` và `unit_cost`. NV giao 403, chưa đăng nhập 401.
- **FE cần biết:** `kpis.inventory_value` có thể **vắng mặt**. Type phải là optional; ô KPI "Giá trị tồn" chỉ hiện khi có key (hoặc khi `me.can_view_cost`).

### Rule đã cài
- **BR-PQ-12 / C8** (S46-AC1): đăng xuất thu token thật ở server. Mọi máy của người đó văng.
- **BR-PQ-04** (S46-AC2): AuditLog `password_change_self`, không chứa mật khẩu/hash/token.
- **BR-PQ-17** (S46-AC5): change-password chỉ đổi của `request.user`. Không có tham số chọn người; gửi thêm field (`username`, `user`, …) → 400.
- **BR-PQ-08**: mật khẩu mới qua `AUTH_PASSWORD_VALIDATORS` (≥ 8 ký tự, không giống tên đăng nhập, không phổ biến, không toàn số), thông điệp tiếng Việt.
- **BR-PQ-09** (S47): nhãn nhóm + việc được làm = hợp các Group.
- **BR-PQ-15 / bất biến #1**: `capabilities` không lộ `view_costprice` cho người không có; Tổng quan không lộ `inventory_value`.

### Lệch so với story / giả định cần PO biết
1. **`detail` của `AUTH_WEAK_PASSWORD`**: story ghi một câu cố định ("Mật khẩu mới phải có ít nhất 8 ký tự và không quá giống tên đăng nhập."). BE trả **thông điệp thật của Django** (tiếng Việt, nối bằng dấu cách), vd `Mật khẩu quá ngắn. Nó phải chứa ít nhất 8 ký tự.` hoặc `Mật khẩu này quá phổ biến.`. Lý do: câu cố định sai với trường hợp "quá phổ biến"/"toàn số". `code` đúng contract; FE hiện `detail` nguyên văn là được. Giống cách `reset-password` (S41) đang làm.
2. **`capabilities` có thêm `reports.view_dashboard` và `purchasing.add_purchasecost`**. Contract ghi "chỉ quyền Tầng 2 (Meta.permissions tuỳ biến)". `view_dashboard` là `Meta.permissions` (tạo ở S6). `add_purchasecost` không phải `Meta.permissions` nhưng nằm trong bảng spec §1.5. Vì vậy danh sách của Quản lý là 5 việc AC1 **cộng** "Xem Tổng quan". Nếu màn "Quyền của tôi" chỉ muốn 5 dòng, FE lọc bỏ `reports.view_dashboard`, hoặc PO chốt để BE bỏ.
3. **Nhãn** lấy từ bảng trong code (`CAPABILITY_LABELS`), không lấy tên Permission trong DB (vd DB ghi "Publish lô ra Shop", "Xác nhận đã hoàn tiền (tiền rời tài khoản)"). Làm vậy để không phải thêm migration đổi tên quyền. Có test: thêm `Meta.permissions` mới mà quên nhãn thì test đỏ.
4. **Thêm ngoài AC:** đăng xuất ghi AuditLog `logout`. Đăng xuất cũng đóng session Django nếu người đó đăng nhập bằng session.
5. Đổi mật khẩu mới trùng mật khẩu cũ: **cho phép** (story không nói). Nếu cần chặn thì thêm mã lỗi mới.

### Còn nợ / giả định
1. **Chưa giới hạn số lần thử** (throttle) cho `change-password` và `auth/token/`. Kẻ cầm máy đang đăng nhập có thể dò mật khẩu cũ. Nên thêm DRF throttle (vd 5 lần/phút/người) ở lô sau. Cần PO chốt ngưỡng.
2. FE (không sửa ở lô này): `erp-console/shared/lib/dashboardSummary.ts:29` khai `inventory_value: number` → nên đổi `inventory_value?: number`. Mock `dashboardSummary.mock.ts` (dòng 8, 227) đang trả key này cho mọi người, ghi chú "giữ y như thật" giờ đã sai: phải bỏ key khi `can_cost=false`. `KpiTiles.tsx:48` đã chỉ đọc khi `canCost`, nên màn hình không vỡ.
3. Không có migration. Chưa deploy. Đây là mốc deploy 1 theo kế hoạch lô (chờ Duy duyệt). Sau deploy làm theo "Ghi chú vận hành (sau L6)" trong `02-stories.md`.
4. Cần cập nhật `business-process-spec.md` §1.5 thêm `reports.view_dashboard` (nợ từ L3–L4; BE không sửa `doc/`).

---

## Lô L5–L6 — S41, S42, S46, S47 (FE) · 2026-09-24

Khớp theo contract **thật** của BE L5 (`/api/staff/`) và BE L6 (logout, change-password, `group_labels`/`capabilities`, vá `inventory_value`).

### Kết quả kiểm chứng
- `cd erp-console && ./node_modules/.bin/tsc --noEmit` → sạch. `npm run build` → sạch, 17 trang tĩnh (thêm `/account/`). `NEXT_PUBLIC_USE_MOCK=1 npm run build` → cũng sạch.
- Bản build thật **không chứa mock**: grep `demo1234|__caveMock|mock-token|beDetail|GH-INV-DH01|Ghe Tư Hải` trong `out/` = 0 file.
- **Trên backend THẬT** (Django `runserver` với DB SQLite tạm trong scratchpad, không động vào `backend/db.sqlite3`; seed 5 tài khoản; bản build thật của console): `e2e/s41_s47_real.py` **30/30 PASS**. Kịch bản không gõ câu lỗi nào: nó bắt response thật rồi so với chữ UI hiện ra (UI = `detail` BE nguyên văn), và kiểm `code`.
- Trên bản build mock: `e2e/s41_s47_staff.py` **69/69 PASS**. Hồi quy `e2e/s7_shell.py` **không FAIL**, `e2e/s8_views.py` **36/36 PASS** (AC1 so bản cũ bỏ qua vì không có `LEGACY_BASE`; thêm kiểm `kpis.inventory_value` vắng với Quản lý).
- Đã tắt mọi server (Django 8000, tĩnh 3101/3102).

| AC | Kết quả (BE thật = R, mock = M) |
|---|---|
| S41-AC1 | R+M: tạo `giao4` nhóm `nv_giao` → 201; màn "Đã tạo" hiện tên đăng nhập + mật khẩu tạm để đọc cho nhân viên; M: `giao4` đăng nhập → Việc giao của tôi |
| S41-AC3 | R+M: bỏ `nv_giao` của `kho1` → PUT 200 `removed:["nv_giao"]`; `kho1` đăng nhập lại không còn menu "Việc giao của tôi" |
| S41-AC4 | R+M: username trùng, thiếu SĐT, mật khẩu yếu → 400 `BR-PQ-08`, UI hiện đúng `detail` BE (mật khẩu yếu là câu Django thật). Form `noValidate` để lỗi luôn đến từ BE |
| S41-AC6 / S42-AC7 | M: `ql9` (manage_staff, không thuộc Chủ) xem tài khoản Chủ → không có nút nào (`available_actions: []`); gán Chủ cho `kho1` → 403 BR-PQ-17 nguyên văn |
| S41-AC7 | M: `sa1` (superuser + Quản lý) bỏ Chủ của `loc` → 400 BR-PQ-18 nguyên văn; Chủ cuối cùng không có nút "Cho nghỉ" |
| S41-AC9 | R+M: Quản lý không có menu, gõ `/staff/` bị chặn và không gọi `/api/staff/`; R: gọi thẳng → 403 |
| S41-AC10 | R: JSON thật không có key `password`/`token` |
| S42-AC1 | R+M: cho `giao1` nghỉ (có bước xác nhận) → 200; token máy của `giao1` → 401; `giao1` không đăng nhập được, chuyển sang lọc "Đã nghỉ" |
| S42-AC2 | M: cho làm lại → `giao1` đăng nhập bằng mật khẩu cũ |
| S42-AC3 | R+M: đặt lại mật khẩu `kho1` → 200; token máy kho → 401; mật khẩu mới vào được |
| S42-AC4 | M: `giao2` còn 2 phiếu → 400 BR-GH-08 nguyên văn, vẫn đang làm |
| S46-AC1 | R+M: Đăng xuất → `POST /api/auth/logout/` 204; token cũ → 401; nháp trên máy bị xoá |
| S46-AC2 | R+M: `kho1` đổi mật khẩu ở máy A → token mới thay trên máy, làm tiếp; token máy B → 401 |
| S46-AC3 | R+M: sai mật khẩu hiện tại → `AUTH_OLD_PASSWORD`; mật khẩu mới 6 ký tự → `AUTH_WEAK_PASSWORD` (detail Django nguyên văn); token cũ vẫn dùng được |
| S47-AC1 | R: danh sách việc = `capabilities` BE, nhóm = `group_labels` BE. Quản lý = 5 việc §1.5 + "Xem Tổng quan"; có tên, SĐT (`tel:`), nút Đổi mật khẩu, Đăng xuất |
| S47-AC2 | M: Chủ thêm lại `nv_giao` cho `kho1` → `kho1` bấm "Tải lại quyền" → menu "Việc giao của tôi" hiện, không đăng nhập lại (tự tải lại khi quay lại tab ≥ 5 phút đã có từ S7) |
| S47-AC3 | M: gỡ `manage_staff` của `ql9` khi đang mở màn → bấm thao tác → 403 → tải lại `me`, hiện dải "Quyền của bạn vừa thay đổi", màn Nhân viên ẩn, menu mất mục. 403 do luật (BR-PQ-17) mà quyền không đổi thì **không** báo |
| S47-AC4 | R+M: Quản lý không có `inventory.view_costprice` trong `capabilities`, "Xem giá vốn: Không" |
| S7-AC6 (form thật) | R+M: form tạo tài khoản đang gõ, token hỏng → 401 → đăng nhập lại cùng người → form mở lại đủ tên đăng nhập, tên, SĐT, nhóm (mật khẩu cố ý không lưu, xem Lệch 2) |
| Mobile | 360×640: không cuộn ngang ở Nhân viên, chi tiết, đổi nhóm, form tạo, Tài khoản của tôi; mọi nút/link/ô chọn nhóm ≥ 44 px |

Ảnh (`shots/`): BE thật `real-s41-desktop-1280-staff.png`, `real-s41-mobile-360-staff.png`, `real-s42-mobile-360-detail.png`, `real-s47-desktop-1280-account-chu.png`, `real-s47-desktop-1280-account-quanly.png`, `real-s47-mobile-360-account.png`; mock `s41-desktop-1280-create-restored.png`, `s41-desktop-1280-confirm-chu.png`, `s42-desktop-1280-confirm-deactivate.png`, `s47-desktop-1280-perm-changed.png`, `s41-mobile-360-*.png`, `s42-mobile-360-detail.png`, `s46-mobile-360-change-password.png`, `s47-mobile-360-account.png`.

### Trang / component / hàm
| File | Làm gì |
|---|---|
| `features/staff/` (mới) | `StaffScreen` (lọc Đang làm/Đã nghỉ/Tất cả, tìm bỏ dấu, SĐT `tel:`), `StaffDetail` (nút theo `available_actions`; sửa hồ sơ, đổi nhóm, đặt lại MK, cho nghỉ/làm lại; xác nhận khi cho nghỉ và khi thêm/bỏ nhóm Chủ), `StaffCreateForm` (giữ nháp `staff:create`), `GroupPicker`, `PasswordField` (nút tạo ngẫu nhiên); `api.ts`: `listStaff`, `createStaff`, `updateStaff`, `setStaffGroups`, `deactivateStaff`, `reactivateStaff`, `resetStaffPassword`; `messages.ts` |
| `features/auth/` | `changePassword()` (api), `AccountScreen` (route `/account/`), `ChangePasswordForm`; `AuthProvider`: `changePassword` (thay token mới), `permNotice` (S47-AC3), bỏ qua 401 của request đang bay khi chính mình đăng xuất; `ConsoleGate`: dải báo quyền đổi; mock: kho người dùng lưu localStorage, logout/change-password/`group_labels`/`capabilities` theo BE L6 |
| `shared/ui/Shell.tsx` | tên người dùng ở chân menu là link tới "Tài khoản của tôi" |
| `shared/ui/Sheet.tsx` (mới) | hộp thoại: tấm trượt đáy trên điện thoại, hộp giữa màn từ 640 px; Esc/nền để đóng, khoá khi đang gửi |
| `shared/lib/messages.ts` (mới) | **mọi** thông điệp lỗi/thông báo FE tự sinh (mất mạng, 5xx, hết phiên, quyền đổi, kiểm tại máy). `http.ts`, auth, StateBox, RightRail đã chuyển sang dùng |
| `shared/lib/beErrors.mock.ts` (mới) | bảng mã lỗi + `detail` của BE chép từ contract L5/L6 — chỉ mock import; E2E mock đọc câu mong đợi từ đây qua `__caveMock` |
| `shared/lib/nav.ts`, `groups.ts` (mới) | hằng `PERM` (tên quyền), `GROUP` (mã nhóm), `ACCOUNT_HREF`; `groups.ts` = mã + nhãn nhóm (khớp `GROUP_LABELS` BE) |
| `shared/lib/dashboardSummary*.ts`, `KpiTiles.tsx` | `inventory_value?` optional; mock bỏ key khi thiếu `view_costprice` (theo BE L6) |
| `e2e/s41_s47_staff.py`, `e2e/s41_s47_real.py` (mới), `e2e/s8_views.py` | kịch bản mock, kịch bản backend thật, thêm 1 kiểm AC2 |

### Lệch contract / cần BE, PO biết
1. **BE — `last_login` luôn `null` khi đăng nhập bằng token.** Thấy trên BE thật: `kho1` đã đăng nhập console mà `/api/staff/` vẫn trả `last_login: null`. `obtain_auth_token` của DRF không gọi `update_last_login`. Cột "Đăng nhập gần nhất" vì vậy luôn trống. Đề xuất BE: gọi `django.contrib.auth.models.update_last_login` trong view lấy token.
2. **Mật khẩu không lưu vào nháp** (form tạo tài khoản). S7-AC6 ghi "đủ nội dung đã gõ". FE cố ý bỏ ô mật khẩu tạm để mật khẩu không nằm trong localStorage, và báo rõ "nhập lại mật khẩu". Cần PO xác nhận.
3. **Chưa có endpoint danh sách nhóm + nhãn.** `/api/staff/` chỉ trả mã nhóm, nên FE phải giữ bảng nhãn/mô tả nhóm ở một chỗ (`shared/lib/groups.ts`, khớp `GROUP_LABELS` BE). Muốn bỏ hẳn phần viết cứng này thì BE cần thêm `GET /api/staff/groups/` → `[{code, label}]` (hoặc `group_labels` trong mỗi dòng).
4. **"Quyền của tôi" hiện cả "Xem Tổng quan"** (BE L6 trả 6 việc cho Quản lý). Coordinator chốt hiện bình thường.
5. Tên menu vẫn là "Nhân sự · Nhật ký" (theo bảng S7), không phải "Nhân viên".
6. S47-AC2 "quay lại tab sau 5 phút" chưa kiểm tự động (phải giả thời gian). Cơ chế đã có từ S7. Kịch bản kiểm bằng nút "Tải lại quyền" và bằng cách đăng nhập lại.

### Hướng Duy nêu trong lúc làm: bỏ viết cứng, bỏ dần mock
- **Đã làm:** không còn chuỗi lỗi/mã lỗi/tên quyền viết tại chỗ trong component (xem `messages.ts`, `PERM`/`GROUP`, `beErrors.mock.ts`). Lỗi nghiệp vụ luôn là `detail` BE nguyên văn. Có kịch bản chạy trên **backend thật** (`s41_s47_real.py`), không so với chuỗi gõ tay.
- **Chưa làm, cần Duy chốt:** gỡ hẳn mock (`features/*/mock.ts`, `dashboardSummary.mock.ts`, nhánh mock trong `http.ts`, `NEXT_PUBLIC_USE_MOCK`). Việc này đụng cả 3 module S8, kịch bản s7/s8, quy tắc trong README và skill `nextjs-shop-patterns`. Đề xuất: (a) dựng một lệnh seed dữ liệu dev ở BE (`manage.py seed_dev`) và một script chạy E2E trên Django thật; (b) chuyển s7/s8 sang BE thật; (c) rồi xoá mock. Phần (a) nằm ở `backend/`, cần BE làm.

### Còn nợ
1. Chưa deploy. Build deploy phải set `NEXT_PUBLIC_API_BASE`; BE L5/L6 phải lên cùng lúc hoặc trước.
2. S46-AC1 "xoá lịch sử trợ lý": chưa có trợ lý (S45). Khi làm S45 phải xoá cả lịch sử trợ lý lúc đăng xuất.
3. `erp-console/legacy/` vẫn còn (chờ Duy).

---

## Sửa nhỏ — last_login (BE) · 2026-09-24
- **Lỗi:** `obtain_auth_token` của DRF không gọi `update_last_login` → `/api/staff/` luôn trả `last_login: null` (mục "Lệch contract" số 1 của L5–L6 FE).
- **Sửa:** `LoginTokenView` mới trong `backend/apps/accounts/auth/api.py` (kế thừa `ObtainAuthToken`, cùng serializer) gọi `update_last_login` sau khi xác thực thành công; `config/api_urls.py` trỏ `auth/token/` sang view này. Path, JSON `{"token": ...}`, mã lỗi 400 `non_field_errors` giữ nguyên; người `is_active=False` vẫn bị từ chối; sai mật khẩu không ghi `last_login`.
- **Test:** `backend/apps/accounts/auth/tests/test_login_last_login.py` (5 test; test set `last_login` đỏ trước khi sửa). Toàn bộ backend 296 test OK; `makemigrations --check` không có thay đổi; `check` sạch. Không có migration, chưa deploy.

---

## Lô L6b (BE) — S48 (phần BE), D1 seed_demo gỡ/thêm lại, QA Q1 · 2026-09-24

### Kết quả kiểm chứng
- `cd backend && .venv/bin/python manage.py test` → **Ran 328 tests, OK** (mốc 296; +14 S48, +13 D1, +5 Q1).
- `manage.py makemigrations --check --dry-run` → `No changes detected`; `manage.py check` → 0 issue.
- Chạy tay trên SQLite nháp (scratchpad, không đụng `db.sqlite3`): `migrate` → `bootstrap_masterdata` → `seed_demo` ×2 (không nhân đôi) → `--remove --dry-run` → `--remove` (gỡ 52 bản ghi; "Kho chính", "Bán lẻ" của bootstrap còn nguyên) → `seed_demo` lại được → `--remove` lại được.
- Test S48 đỏ trước khi cài (200 thay vì 403, thiếu key); Q1 đỏ đúng lý do (`IntegrityError` → 500) trước khi sửa.

### Migration (2, cùng app `accounts`)
| Migration | Nội dung | Lý do schema |
|---|---|---|
| `0004_staffprofile_must_change_password` | `StaffProfile.must_change_password` BooleanField default False | S48 / BR-PQ-19. `AddField` default False → mọi hồ sơ cũ = False (S48-AC7, không ép người đang dùng) |
| `0005_demorecord` | model mới `DemoRecord(content_type, object_id, created_at)`, unique (content_type, object_id), chỉ quyền `view` | D1. Demo nằm ở ~11 model (Item, ItemPrice, Customer, Batch, sổ kho, đơn, dòng đơn, HĐ, phiếu giao do signal sinh…) không có trường đánh dấu chung; `seed_demo` dùng get_or_create nên tiền tố mã không phân biệt được bản ghi thật trùng mã. Sổ riêng ghi đúng bản ghi seed **tạo ra** → nhận diện chắc chắn, không thêm cột vào 11 bảng nghiệp vụ |

### File đã sửa / thêm
| File | Thay đổi |
|---|---|
| `backend/apps/accounts/models.py` | + `StaffProfile.must_change_password`; + model `DemoRecord` |
| `backend/apps/accounts/auth/authentication.py` | **mới** — `TokenAuthentication`/`SessionAuthentication` bọc của DRF + chặn BR-PQ-19; `must_change_password(user)`; `MustChangePassword` (403) |
| `backend/config/settings.py` | `DEFAULT_AUTHENTICATION_CLASSES` trỏ 2 lớp bọc trên |
| `backend/apps/common/api.py` | `exception_handler`: APIException có `render_code` → `{"detail","code"}` |
| `backend/apps/accounts/auth/api.py` | `allow_must_change_password = True` cho token, me, logout, change-password |
| `backend/apps/accounts/auth/services.py` | `describe_user` + key `must_change_password`; `change_own_password` tắt cờ |
| `backend/apps/accounts/staff/services.py` | `create_staff` bật cờ + bắt `IntegrityError` (savepoint) → 400 BR-PQ-08, `_username_taken`; `reset_password` bật cờ; `_lock_target_and_chus` thay `_lock_active_chus` trong `set_groups`/`deactivate` |
| `backend/apps/accounts/demo/services.py` | **mới** — `mark_demo`, `track_demo_creations`, `remove_demo(dry_run)` |
| `backend/apps/accounts/management/commands/seed_demo.py` | ghi sổ khi seed; `--remove`, `--dry-run`, `--adopt-legacy`; `adopt_legacy()` |
| Test | `accounts/auth/tests/test_s48_must_change_password.py` (mới), `accounts/staff/tests/test_q1_concurrency.py` (mới), `accounts/demo/tests/test_d1_seed_demo.py` (mới); `test_s6_me.py`, `test_s47_me_labels.py`: tập key `me` thêm `must_change_password` |
| README | `backend/README.md` (ngoại lệ BR-PQ-10 cho demo), `apps/accounts/README.md`, `auth/README.md`, `staff/README.md` |

### Contract thực tế
```
GET /api/auth/me/
200 {..., "must_change_password": true}      // key mới; superuser luôn false; không có StaffProfile → false

Khi cờ bật (tài khoản vừa được Chủ tạo, hoặc vừa được Chủ/superuser đặt lại mật khẩu):
GET/POST/PUT/PATCH mọi API DRF khác (vd /api/sales/orders/, /api/staff/, /api/dashboard/summary/)
403 {"detail": "Bạn cần đặt mật khẩu mới trước khi dùng hệ thống (BR-PQ-19).",
     "code": "AUTH_MUST_CHANGE_PASSWORD"}
Được miễn: POST /api/auth/token/, GET /api/auth/me/, POST /api/auth/logout/, POST /api/auth/change-password/

POST /api/auth/change-password/ {"old_password": "<mật khẩu tạm>", "new_password": "…"}
200 {"token": "<mới>"}                        // cờ → false; me trả must_change_password=false

POST /api/staff/  (username trùng do 2 request đồng thời, request thua)
400 {"code": "BR-PQ-08", "detail": "Tên đăng nhập đã tồn tại."}   // trước đây 500
```
POST `/api/staff/` 201 và `reset-password` 200 **không đổi JSON**; chỉ thêm tác dụng bật cờ.

Lệnh (không phải API):
```
manage.py seed_demo                              → "Seed xong: 6 mặt hàng · 6 lô · 6 đơn · 3 hoá đơn."
manage.py seed_demo --remove [--dry-run]         → "Đã gỡ 52 bản ghi demo (catalog.item: 6, …)."
                                                   + "Giữ lại N bản ghi demo vì dữ liệu thật đang dùng:" + từng dòng
manage.py seed_demo --remove --adopt-legacy      → nhận demo seed bằng bản cũ rồi gỡ
```

### Rule đã cài
- **BR-PQ-19 (mới, S48)**: Chủ tạo tài khoản (S41) hoặc đặt lại mật khẩu (S42) → `must_change_password=True`; người đó tự đổi (S46) → False; tự đổi khi cờ đang tắt không bật cờ. Khi True mọi API nghiệp vụ 403 `AUTH_MUST_CHANGE_PASSWORD` trừ token/me/logout/change-password. Superuser không bị ép. Chặn ở lớp xác thực DRF (không phải permission) vì nhiều view tự khai `permission_classes` → permission mặc định không phủ hết.
- **D1 / ngoại lệ BR-PQ-10**: `seed_demo` đánh dấu mọi bản ghi nó tạo mới qua `post_save` trong lúc chạy (bắt được cả phiếu giao do signal hoá đơn sinh); bản ghi thật get_or_create dùng lại (kho, bảng giá, mặt hàng trùng mã, khách trùng SĐT) **không** bị đánh dấu. `--remove` xoá từng bản ghi đánh dấu chỉ khi mọi thứ Django sẽ xoá/sửa theo (CASCADE, fast-delete, SET_NULL) cũng là demo và không bản ghi thật nào PROTECT nó; lặp nhiều lượt để tự tìm thứ tự. Bản ghi demo đang được dữ liệu thật dùng → giữ lại, in lý do, vẫn giữ dấu (lần sau gỡ tiếp). AuditLog không bao giờ bị đánh dấu/gỡ; mỗi lần gỡ ghi AuditLog `demo_remove` (actor = Hệ thống).
- **`--adopt-legacy`**: chỉ nhận theo chữ ký chính xác của bộ demo: mặt hàng (mã + tên) và giá (đúng đơn giá seed), nhà cung cấp (3 tên), lô (mã + mặt hàng + NCC) và bút toán nhập "Nhập lô …", khách (SĐT + tên), đơn (mã + SĐT) + dòng đơn + HĐ (mã HD-…) + phiếu giao. **Không** nhận tên chung "Kho chính", "Bán lẻ", nhóm "Hải sản".
- **Q1**: `create_staff` bọc `create_user` trong savepoint, `IntegrityError` → 400 BR-PQ-08, không tạo hồ sơ/AuditLog. `set_groups`, `deactivate` khoá **một lần** `SELECT … FOR UPDATE ORDER BY pk` gồm người đích + mọi Chủ đang làm → mọi thao tác đụng Chủ xin khoá cùng thứ tự, hai Chủ cho nghỉ nhau cùng lúc thì request sau chờ (không deadlock), BR-PQ-18 kiểm trên dữ liệu đã khoá.

### Còn nợ / giả định
- **Production đã seed bằng bản cũ** → sau khi deploy, `seed_demo --remove` một mình không gỡ gì (chưa có sổ). Chạy `seed_demo --remove --adopt-legacy --dry-run` xem danh sách trước, rồi bỏ `--dry-run`. Nhóm "Hải sản" (legacy) sẽ còn lại — xoá tay qua Admin nếu không dùng.
- `--adopt-legacy` vẫn có rủi ro nhỏ: một mặt hàng THẬT trùng **cả** mã lẫn tên với bộ demo (vd `CA-THU` "Cá thu") mà chưa có lô/đơn/giá nào khác tham chiếu sẽ bị gỡ. Vì vậy là cờ tuỳ chọn + có `--dry-run`.
- `track_demo_creations` nghe `post_save` của cả tiến trình: không chạy `seed_demo` bên trong tiến trình web đang phục vụ request (chạy như Cloud Run Job / lệnh riêng là đúng).
- BR-PQ-19 không phủ **Django Admin** (đăng nhập session, không qua DRF). Nhân viên `is_staff` có cờ vẫn vào Admin được bằng mật khẩu tạm. Nếu cần: thêm middleware cho `/admin/`.
- `reset_password` cho tài khoản **không có** StaffProfile (tạo tay qua Admin) không bật được cờ (không có chỗ lưu). Tài khoản tạo qua S41 luôn có hồ sơ.
- Q1: kiểm thứ tự khoá chỉ qua helper/spy (SQLite không có FOR UPDATE). Chưa có `TransactionTestCase` trên Postgres. Trùng username chỉ khác hoa/thường gửi đồng thời vẫn có thể tạo được cả hai (DB `auth_user` không có unique không phân biệt hoa thường — không đổi bảng của Django).
- FE (S48-AC2…AC5): cần đọc `must_change_password` trong `me` → chỉ mở màn "Đặt mật khẩu mới"; bắt 403 `code=AUTH_MUST_CHANGE_PASSWORD` ở mọi API → chuyển sang màn đó. Mã BR-PQ-19 cần thêm vào `business-process-spec.md` §1 (không sửa `doc/` ở lượt này).
- Chưa deploy; cần chạy `migrate` (0004, 0005) khi deploy.

---

## Lô L6b (FE) — S48 (phần FE), D1 bật/tắt mock, QA Q2 (e2e chập chờn) · 2026-09-24

Khớp contract **thật** của "Lô L6b (BE)" ở trên: `me.must_change_password`; 403 `{"detail": "Bạn cần đặt mật khẩu mới trước khi dùng hệ thống (BR-PQ-19).", "code": "AUTH_MUST_CHANGE_PASSWORD"}`; miễn token/me/logout/change-password; change-password thành công thì cờ về false. Mock chép đúng câu và mã này.

### Kết quả kiểm chứng
- `cd erp-console && ./node_modules/.bin/tsc --noEmit` → sạch. `npm run build` → exit 0, 18 trang tĩnh (thêm `/set-password/`). `NEXT_PUBLIC_USE_MOCK=1 npm run build` → cũng sạch.
- Bản build thật **không chứa mock**: grep `demo1234|__caveMock|mock-token|beDetail|setMockGate(|cave_erp_mock|GH-INV-DH01` và câu "Chế độ mock" / detail mock trong `out/` = 0 file. `out/` hiện là bản build thật mặc định.
- E2E trên bản build mock (tĩnh, 127.0.0.1:3101):
  - `e2e/s48_password.py` (mới): **37/37 PASS**.
  - `e2e/s41_s47_staff.py`: **71/71 PASS, chạy 3 lần liên tiếp đều 71/71** (+1 lần chạy thử trước đó cũng 71/71).
  - Hồi quy `e2e/s7_shell.py` **25/25 PASS**, `e2e/s8_views.py` **36/36 PASS** (AC1 so bản cũ bỏ qua vì không truyền `LEGACY_BASE`).
- E2E trên **backend thật** (Django `runserver` 127.0.0.1:8000, SQLite tạm trong scratchpad: `migrate` → `bootstrap_masterdata` → seed 5 tài khoản; seed lại trước mỗi lần chạy; `backend/db.sqlite3` không bị đụng, mtime vẫn 13/09; console bản build thật trỏ `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000`, phục vụ tĩnh :3102): `e2e/s41_s47_real.py` **39/39 PASS, 3 lần**.
- Mọi lệnh server/build/script chạy qua `to.sh <giây>` (perl `alarm`, máy không có `timeout`), kill theo PID. Cuối cùng `lsof -iTCP -sTCP:LISTEN` trên 3000/3100–3102/8000/8765: không còn gì.

| AC | Kết quả (M = mock, R = BE thật) |
|---|---|
| S48-AC1 | M+R: `me.must_change_password=true` → chỉ mở `/set-password/`, không menu; gõ `/overview/`, `/inventory/` bị đưa về, không gọi API nghiệp vụ. R: API khác của `giao4`/`kho1` → 403 `AUTH_MUST_CHANGE_PASSWORD`. M: cờ bật giữa phiên → bấm Làm mới → 403 → console chuyển sang màn đặt mật khẩu, không báo "quyền vừa thay đổi" |
| S48-AC2 | M+R: nhập mật khẩu cũ + mới + nhập lại → `POST change-password` 200 → `me` tải lại, cờ false → vào home (NV kho → Tổng quan, NV giao → Việc giao của tôi) |
| S48-AC3 | M+R: "Nhập lại" khác → "Hai mật khẩu không khớp." dưới ô, **không có request** (kiểm bằng log mock và bắt request thật) ở 4 form: đặt mật khẩu mới, tự đổi, tạo tài khoản, đặt lại |
| S48-AC4 | M: mọi ô mật khẩu có nút mắt 44×44, `aria-pressed`, bấm → hiện, bấm lại → ẩn; ô mới và ô nhập lại hiện/ẩn cùng nhau; gợi ý quy tắc (≥8 ký tự, không toàn số, không giống tên đăng nhập, không quá phổ biến) hiện trước khi gửi và cập nhật khi gõ; đăng nhập không có ô nhập lại/gợi ý |
| S48-AC5 | M+R: nháp form tạo tài khoản giữ tên, SĐT, nhóm, **không** có mật khẩu (kiểm cả chuỗi mật khẩu lẫn key `password` trong localStorage); tải lại/401 → form nhắc nhập lại mật khẩu |
| S48-AC6 | M+R: tự đổi xong đăng nhập lại → thẳng home (cờ không bật lại); Chủ đặt lại → cờ bật lại; M: superuser `admin` bị gắn cờ vẫn không bị ép (vào `/no-role/`) |
| Q2 | Sửa thời điểm áp nháp (xem dưới); `s41_s47_staff.py` 3/3 lần 71/71; `s41_s47_real.py` 3/3 lần 39/39 |
| Mobile | 360×640: đăng nhập, đặt mật khẩu mới, form tạo tài khoản, chi tiết, Tài khoản của tôi không cuộn ngang, mọi nút/ô ≥ 44px |

Ảnh (`shots/`): `s48-mobile-360-set-password.png`, `s48-mobile-360-login.png`, `s48-desktop-1280-set-password.png` (mock), `real-s48-desktop-1280-set-password.png` (BE thật), `s41-desktop-1280-create-restored.png` (chụp lại, form có ô nhập lại).

### Trang / component / hàm
| File | Làm gì |
|---|---|
| `shared/ui/PasswordInput.tsx` (mới) | **Ô mật khẩu dùng chung** cho mọi form: nút mắt 44×44 (chữ trong `sr-only`, không dùng `aria-label` để `getByLabel("Mật khẩu")` chỉ trúng ô nhập), `rules` (gợi ý quy tắc sống), `error` (lỗi của ô, `aria-invalid`), `shown`/`onShownChange` (2 ô hiện/ẩn cùng nhau), `extra` (nút phụ). Không tự lưu gì |
| `shared/lib/passwordRules.ts` (mới) | `PASSWORD_MIN_LENGTH = 8`, `passwordChecks()` — chỉ để gợi ý, không chặn gửi; BE kiểm thật |
| `shared/lib/messages.ts` | `passwordMismatch` = "Hai mật khẩu không khớp."; chữ nút mắt, gợi ý quy tắc, chữ màn đặt mật khẩu mới |
| `shared/lib/nav.ts` | `Viewer.must_change_password?`, `SET_PASSWORD_HREF`; `homePath()` trả `/set-password/` khi còn cờ |
| `shared/lib/http.ts` | handler 403 nhận `code`; `setMockGate()` (chỉ mock) — cổng chung chạy trước mọi endpoint mock, mô phỏng lớp xác thực BE |
| `shared/lib/useDraft.ts` | **Sửa Q2**: đọc nháp ĐỒNG BỘ ở lần render đầu (khi đã biết chủ nháp); chủ nháp đến muộn thì áp đúng 1 lần và bỏ qua nếu người dùng đã gõ. Hết cảnh `setValue(nháp)` chạy sau khi đã điền form |
| `features/auth/components/SetPasswordScreen.tsx` + `app/set-password/page.tsx` (mới) | màn "Đặt mật khẩu mới" (card như đăng nhập, nút Đăng xuất "Không phải bạn?") |
| `features/auth/components/ChangePasswordForm.tsx` | dùng `PasswordInput`, ô nhập lại + gợi ý, `mustChange` (nhãn "Lưu mật khẩu mới", gợi ý "mật khẩu tạm Chủ vựa đưa") |
| `features/auth/components/AuthProvider.tsx` | 403 `AUTH_MUST_CHANGE_PASSWORD` → bật cờ trên máy + tải lại `me` (không báo đổi quyền); `changePassword` tải lại `me` sau khi thay token |
| `ConsoleGate.tsx`, `NoRoleScreen.tsx`, `LoginScreen.tsx` | còn cờ → chuyển `/set-password/` (ưu tiên trước "chưa phân quyền"); đăng nhập dùng `PasswordInput` |
| `features/auth/types.ts`, `mock.ts` | `Me.must_change_password?`, `MUST_CHANGE_PASSWORD_CODE`; mock: cờ theo người dùng, `kho5` seed còn mật khẩu tạm, superuser không bị ép, change-password tắt cờ, cổng 403 |
| `features/staff/components/PasswordField.tsx` | cặp ô mật khẩu tạm + "Nhập lại …" + "Tạo ngẫu nhiên" (điền cả hai, hiện chữ) |
| `StaffCreateForm.tsx`, `StaffDetail.tsx` | lệch → báo, không gọi API; nút "Tạo tài khoản" chỉ khoá khi đang gửi (bấm là gửi POST; tên trống thì BE báo `Tên đăng nhập là bắt buộc.`) |
| `StaffScreen.tsx` | `aria-busy` trên bảng khi đang tải lại — để e2e chờ điều kiện, không bấm vào dòng sắp vẽ lại |
| `features/staff/mock.ts` | tạo tài khoản / đặt lại mật khẩu bật cờ |
| `shared/lib/beErrors.mock.ts` | `AUTH_MUST_CHANGE_PASSWORD` (403, câu BE thật) |
| `e2e/s48_password.py` (mới), `s41_s47_staff.py`, `s41_s47_real.py`, `s7_shell.py`, `s8_views.py` | S48; bỏ hết `wait_for_timeout`: chờ URL / phần tử / nháp đã ghi (`wait_for_function` đọc localStorage) / `aria-busy` hết / `document.fonts` xong; context `reduced_motion="reduce"`; `s41_s47_real.py` không đọc body response `me` lúc reload nữa (Q2 dòng 226) mà hỏi thẳng API |
| `README.md` (erp-console), `features/auth/README.md`, `features/staff/README.md` | D1: bảng bật/tắt mock (`NEXT_PUBLIC_USE_MOCK`) và dữ liệu demo BE (`manage.py seed_demo [--remove] [--dry-run]`, `--adopt-legacy`); S48; quy ước e2e không ngủ |

### Q2 — nguyên nhân và cách sửa
- **"Bấm Tạo tài khoản không phát POST"**: `useDraft` cũ khởi tạo bằng giá trị rỗng rồi mới áp nháp trong `useEffect`; nút "Tạo tài khoản" khoá khi tên đăng nhập trống. Nếu hộp thoại/ô được điền trong khe giữa hai lần render (hoặc nháp đến muộn đè lên), Playwright gặp nút đang khoá → chờ hết 30 s, không có POST. Sửa: nháp đọc đồng bộ ở render đầu, không bao giờ đè lên chữ đã gõ; nút chỉ khoá khi đang gửi (lỗi dữ liệu để BE báo nguyên văn). Kịch bản chờ nháp đã ghi bằng điều kiện thay vì ngủ 700 ms.
- **"Dòng `giao2` bị detached lúc bấm"**: danh sách tải lại sau mỗi thao tác. Bảng có `aria-busy` khi đang tải; `open_staff` chờ hết `aria-busy` rồi mới bấm.
- **`info.value.json()` "No resource with given identifier"** (`s41_s47_real.py`): bỏ đọc body của response bị thay khi reload; gọi `GET /api/auth/me/` bằng `ctx.request` với token của máy.

### Lệch contract / cần BE, PO biết
1. **Gợi ý quy tắc là bản chép tay** của `AUTH_PASSWORD_VALIDATORS` (≥ 8 ký tự, không toàn số, không giống tên đăng nhập; "không quá phổ biến" ghi "máy chủ kiểm khi gửi" vì FE không có danh sách 20 000 mật khẩu). BE đổi độ dài tối thiểu thì sửa `PASSWORD_MIN_LENGTH`. Muốn bỏ chép tay: BE thêm endpoint trả danh sách quy tắc + nhãn.
2. **Danh sách nhân viên chưa cho biết ai còn mật khẩu tạm** (contract `/api/staff/` không có `must_change_password`). Chủ không thấy "chưa đổi mật khẩu". Nếu cần: BE thêm key vào mỗi dòng, FE hiện chip.
3. **Nút "Tạo tài khoản" không còn khoá khi tên đăng nhập trống** (trước đây khoá). Bấm là gửi, BE trả `Tên đăng nhập là bắt buộc.` (BR-PQ-08). Làm vậy để "bấm là gửi POST" (Q2) và lỗi luôn đến từ BE.
4. **Ô mật khẩu tạm mặc định ẩn** (trước đây hiện chữ để Chủ đọc). Chủ bấm mắt hoặc "Tạo ngẫu nhiên" (tự hiện) để đọc; màn "Đã tạo"/"Đã đặt lại" vẫn hiện mật khẩu. Cần PO xác nhận nếu muốn mặc định hiện.
5. BR-PQ-19 không phủ Django Admin (BE đã ghi); console không liên quan.

### Còn nợ
1. `erp-console/legacy/` vẫn còn — **không xoá** ở lô này theo yêu cầu (xoá ở mốc deploy 1, D2).
2. Chưa deploy. Build deploy phải set `NEXT_PUBLIC_API_BASE`, không set `NEXT_PUBLIC_USE_MOCK`; BE L6b (migrate 0004, 0005) phải lên cùng lúc hoặc trước — nếu FE lên trước, `me` không có key thì FE coi như `false` (không ép ai).
3. `business-process-spec.md` §1 cần thêm BR-PQ-19 (nợ chung với BE).
4. Seed tài khoản cho `s41_s47_real.py` vẫn là script ngoài repo (5 tài khoản, mật khẩu chung) — mô tả ở đầu file kịch bản; nên chuyển thành lệnh BE (`seed_dev`) như đã đề xuất ở L5–L6.

---

## Sửa lỗi QA lần 2 (BE) — B2, B5, B4, B3, N3 · 2026-09-24

### Kết quả kiểm chứng
- `cd backend && .venv/bin/python manage.py test` → **Ran 345 tests, OK** (mốc 328; +11 B2/B5, +5 B3/B4, +1 N3, 0 test xoá).
- `makemigrations --check --dry-run` → `No changes detected` · `manage.py check` → 0 issue · `adapter pytest -q` → 10 passed.
- Test đỏ đúng lý do trước khi sửa: B2 (giá/sổ kho/dòng đơn bị gỡ nửa chừng, Shop trả `price: null`), B5 (phiếu `DELIVERING`/`READY` đã gán bị gỡ), B4 (200 thay vì 400), B3 (Admin 200 thay vì 403), N3 (`IntegrityError` → 500).
- Chạy lại kịch bản QA bằng **bản sao** `runA.sh`/`runB.sh` (thư mục `scratchpad/d1-fix/`, không ghi đè `d1/` của QA; B chạy trên bản sao `r2_legacy.sqlite3`):
  - A: dry-run và lần chạy thật in **y hệt** (gỡ 41, giữ 8 kèm lý do). `cmp.py`: 24/24 bản ghi thật không mất, không đổi trường (sau gỡ, và sau seed lại + gỡ). `LO-0921` còn bút toán "Nhập lô LO-0921", Σ sổ kho = 27 = `qty_received`. `ItemPrice` của `GHE-XANH`, `MUC-ONG` còn; `GET /api/shop/catalog/` có `GHE-XANH` 310000 / 26 kg bán được.
  - B: dry-run và lần chạy thật in y hệt (gỡ 29, giữ 22). Mọi bản ghi bị gỡ đều thuộc chữ ký demo (đã liệt kê từng cái); 0 bản ghi còn lại bị đổi trường. `DH-2609-116` (thanh toán thật `REAL-TXN-777`) còn đủ 1 dòng, Σ dòng = `total_amount`. `GH-QA-1` (READY) và `GH-QA-2` (DELIVERING) còn, cùng cả cụm HĐ/đơn/dòng/phiếu giao demo của chúng. Catalog có `CA-THU` 165000 (tồn bán được = 0 vì lô thật `LO-QA-EXP` của QA đã hết hạn — dữ liệu kịch bản, không phải lỗi).

### File đã sửa / thêm
| File | Thay đổi |
|---|---|
| `backend/apps/accounts/demo/services.py` | `remove_demo` tính tập giữ theo bao đóng: `REFERENCE_FIELDS`, `_parents`, `_close_over_parts`, `_delete_pass` (gỡ thử trong savepoint, kẹt → `_Blocked` → hoàn tác, giữ, tính lại), `_blocked_reason`, `_fresh`; đọc sổ theo `pk` cho thứ tự in ổn định |
| `backend/apps/accounts/management/commands/seed_demo.py` | B5: `adopt_legacy` chỉ nhận phiếu giao `PREPARING` + chưa gán người giao; tiêu đề danh sách giữ lại nói rõ cả lý do "một phần / phụ thuộc" |
| `backend/apps/accounts/auth/services.py` | B4: mật khẩu mới trùng mật khẩu hiện tại → `BusinessError` `AUTH_WEAK_PASSWORD` |
| `backend/apps/accounts/auth/middleware.py` | **mới** — B3: `AdminMustChangePasswordMiddleware` |
| `backend/config/settings.py` | thêm middleware trên, ngay sau `AuthenticationMiddleware` |
| `backend/apps/sales/payments/internal_api.py` | N3: validate `received_at` trước khi ghi → 400 `WEBHOOK_INVALID_INPUT` |
| Test | `accounts/demo/tests/test_d1_seed_demo.py` (+`B2ClosureTests` 5, `B2LegacyClosureTests` 3, `B5AdoptDeliveryNoteTests` 3 + helper `children_snapshot` kiểm "không cha nào còn sống mà mất con"); `accounts/auth/tests/test_qa2_fixes.py` (mới: B4 ×1, B3 ×4); `sales/payments/tests/test_internal_api.py` (+N3); `common/tests/test_s3_locked_fields.py`: payload S3-AC5 thêm `received_at` (test vẫn kiểm đúng điều cũ: lỗi nghiệp vụ webhook có `code`) |
| README | `apps/accounts/README.md`, `apps/accounts/auth/README.md` |

Không có migration mới.

### Contract thực tế
```
POST /api/auth/change-password/ {"old_password": X, "new_password": X}      // mới == hiện tại
400 {"detail": "Mật khẩu mới phải khác mật khẩu hiện tại.", "code": "AUTH_WEAK_PASSWORD"}
    // không đổi gì: mật khẩu, cờ must_change_password, token cũ giữ nguyên

GET /admin/… (session, is_staff, còn cờ must_change_password, không phải superuser)
403 text/html: "Bạn cần đặt mật khẩu mới trên ERP console (cửa sổ đăng nhập nhân viên) trước khi
    dùng trang quản trị (BR-PQ-19)." + nút Đăng xuất. /admin/login/ và /admin/logout/ vẫn mở.

POST /api/internal/payments/sepay-webhook/  (thiếu / rỗng / sai định dạng / ngày không tồn tại ở received_at)
400 {"detail": "Thiếu hoặc sai received_at (ISO 8601).", "code": "WEBHOOK_INVALID_INPUT"}
    // không tạo PaymentTransaction, đơn không đổi. Đủ trường → hành vi như cũ (adapter luôn gửi ISO 8601).
```
`seed_demo --remove [--dry-run] [--adopt-legacy]`: in `Giữ lại N bản ghi demo (dữ liệu thật đang dùng, hoặc là một phần / phụ thuộc bản ghi đang giữ):` rồi từng dòng `<mô tả> — <lý do>`; lý do một trong ba: `đang được dữ liệu thật dùng: …` · `là một phần của «X» đang được giữ` · `phụ thuộc bản ghi demo đang được giữ: …`. Dry-run đi đúng đường chạy thật rồi rollback → danh sách giống hệt.

### Rule đã cài
- **D1 / BR-PQ-10 (ngoại lệ demo) + bất biến 4 (sổ kho, `*LineBatch` append-only)** — tập giữ lại là bao đóng, lặp tới điểm bất động:
  1. *Chiều xuôi*: gỡ thử toàn bộ demo không bị giữ trong savepoint; bản ghi nào không gỡ được (dữ liệu thật PROTECT/CASCADE tới nó, hoặc gỡ nó kéo theo bản ghi đang giữ) → hoàn tác lượt thử, đưa vào tập giữ.
  2. *Chiều ngược*: bản ghi demo có FK "một phần của" trỏ tới bản ghi đang giữ → giữ. "Một phần" = **mọi FK trừ** `REFERENCE_FIELDS` (FK tham chiếu danh mục: lô→mặt hàng/NCC/kho, dòng→mặt hàng, đơn/HĐ→khách, giá→bảng giá, mặt hàng→nhóm, phiếu nhập→NCC/kho, `component_item`, `pricing_rule`…). Mặc định là "một phần" để model mới thêm sau này thiên về giữ (an toàn), không thiên về xoá.
  Hệ quả: giá của mặt hàng bị giữ, sổ kho/giữ chỗ/phân bổ của lô bị giữ, dòng + hoá đơn + phiếu giao + thanh toán của đơn bị giữ đều giữ; chứng từ (đơn/HĐ/phiếu) giữ cả cụm hoặc gỡ cả cụm. Lô demo của mặt hàng bị giữ, đơn demo bán mặt hàng bị giữ vẫn gỡ được (chỉ tham chiếu).
- **B5**: `--adopt-legacy` chỉ nhận phiếu giao ở trạng thái chưa bắt đầu (`PREPARING`, `assigned_to` rỗng). Phiếu khác coi như dữ liệu thật → PROTECT hoá đơn → cả cụm HĐ/đơn giữ nguyên và được báo trong "Giữ lại" (lý do nêu mã phiếu).
- **BR-PQ-19**: mật khẩu mới phải khác mật khẩu hiện tại (B4); phủ Django Admin (B3), superuser không bị ép.

### Còn nợ / giả định
- Lô demo bị giữ (vd `LO-0921` có đơn thật giữ chỗ) vẫn ở trạng thái đang bán với tồn demo — Shop có thể bán tiếp tồn đó cho khách thật. Không tự đổi trạng thái (không có AC, và đổi trạng thái lô là việc nghiệp vụ). Người chạy đọc danh sách "Giữ lại", rồi đóng lô trên ERP nếu cần; lần `--remove` sau, khi hết dữ liệu thật dùng, sẽ gỡ nốt.
- Bao đóng làm giữ nhiều hơn trước (kịch bản B: giữ 22 thay vì 8), vì mỗi phiếu giao thật trên hoá đơn demo giữ cả cụm đơn/HĐ/khách/mặt hàng/giá. Đây là hướng an toàn theo yêu cầu.
- `REFERENCE_FIELDS` là danh sách tay: thêm FK "tham chiếu danh mục" mới mà quên khai thì kết quả chỉ là giữ nhiều hơn, không xoá nhầm.
- B3 trả 403 (không chuyển hướng) vì ERP console là site riêng, BE không biết URL; trang có nút Đăng xuất. Nếu muốn chuyển hướng, cần thêm setting URL console.
- N3: thêm mã lỗi `WEBHOOK_INVALID_INPUT`; hai lỗi 400 cũ (thiếu `bank_txn_id`, sai `amount`) giữ nguyên JSON cũ, không có `code`.
- Chưa deploy, chưa commit.

---

## Sửa theo code review (BE) — trước deploy 1 · 2026-09-24

### Kết quả kiểm chứng
- `cd backend && .venv/bin/python manage.py test` → **Ran 369 tests, OK** (mốc 345; +24 test mới, 0 test xoá; 1 assertion B2 cập nhật — xem R4).
- `makemigrations --check --dry-run` → `No changes detected` · `manage.py check` → 0 issue · `cd adapter && .venv/bin/python -m pytest -q` → 10 passed.
- Mọi test mới chạy đỏ đúng lý do trước khi sửa: R1 (`NaN`/`Infinity` → 500 `InvalidOperation`, `-5`/`0` → 200 ghi UNDERPAID/UNMATCHED), R3 (`compare_digest` không được gọi), R5 (gửi lại không `order_code` → `matched:false`; `bank_txn_id` 101 ký tự → 200/500), R2 (DEBUG mặc định `True`, không báo lỗi thiếu key), R4 (đơn BOOKED 0 phân bổ, lô giữ 4/3 kg không thuộc đơn nào, hoá đơn 0 dòng, COGS = 0, job TTL không nhả), R6 (đếm 5 thay vì 2, thiếu `near_expiry_days`), R7 (12 lần `reverse()` cho 4 request).

### File đã sửa / thêm
| File | Thay đổi |
|---|---|
| `backend/apps/sales/payments/internal_api.py` | R1 `_parse_amount` (hữu hạn, > 0, từ chối list/dict/bool); R3 `_token_ok` = `hmac.compare_digest` trên bytes UTF-8, token chưa cấu hình → luôn 401; R5 giới hạn `bank_txn_id` ≤ 100 (lấy từ `max_length` của model), gửi lại mã GD đã có mà thiếu/sai `order_code` → trả kết quả đã ghi (`_existing_response`); mọi lỗi 400 của webhook nay có `code` |
| `backend/config/settings.py` | R2: `DEBUG` mặc định `"0"`; `TESTING` dời lên đầu; DEBUG tắt + `DJANGO_SECRET_KEY` thiếu/rỗng/bằng key dev/bằng placeholder `.env.example` → `ImproperlyConfigured` (trừ `manage.py test`) |
| `backend/.env.example`, `backend/README.md` | R2: ghi rõ dev phải có `DJANGO_DEBUG=1` |
| `backend/.env` | **mới, chỉ máy dev** (đã có trong `.gitignore`/`.dockerignore`): `DJANGO_DEBUG=1` — để `manage.py check`/`runserver` trong venv hiện tại vẫn chạy |
| `backend/apps/accounts/auth/middleware.py` | R7: `_admin_urls()` tính (prefix, {login, logout}, logout) một lần, cache ở module; reset khi `ROOT_URLCONF` đổi (signal `setting_changed`, chỉ trong test). Hành vi B3 giữ nguyên |
| `backend/apps/reports/dashboard_api.py` | R6: cận hạn = `sellable_batches(on_date=today)` ∩ `expiry_date ≤ today + N`; cờ `near_expiry` từng dòng lô dùng cùng tiêu chí; thêm `near_expiry_days` |
| `backend/apps/accounts/management/commands/seed_demo.py` | R4: xem dưới |
| `backend/apps/accounts/demo/services.py` | R4: thêm `is_demo(obj)` |
| `backend/apps/sales/payments/services.py` | R4: `confirm_payment(..., invoice_code=None)` → `issue_invoice(..., code=None)`; mặc định vẫn tự sinh `INV-…` (chỉ seed_demo truyền mã) |
| Test | `sales/payments/tests/test_internal_api.py` (+`ReviewWebhookFixTests` ×8); `common/tests/test_settings_security.py` (mới, ×5, chạy settings trong tiến trình con, bỏ qua `.env`); `accounts/auth/tests/test_qa2_fixes.py` (+R7 ×1); `reports/tests/test_dashboard_cost_leak.py` (+R6 ×2); `accounts/demo/tests/test_d1_seed_demo.py` (+`R4SeedConsistencyTests` ×8) |

Không có migration mới. Không đổi model.

### Contract thực tế
```
POST /api/internal/payments/sepay-webhook/   (X-Internal-Token)
  token sai / rỗng / không ASCII / server chưa cấu hình token
  → 401 {"detail": "Sai service token."}
  amount thiếu / rỗng / không phải số / NaN / Infinity / ≤ 0 / list / dict
  → 400 {"detail": "Số tiền (amount) không hợp lệ — phải là số hữu hạn lớn hơn 0.", "code": "WEBHOOK_INVALID_INPUT"}
  bank_txn_id thiếu → 400 {"detail": "Thiếu bank_txn_id.", "code": "WEBHOOK_INVALID_INPUT"}
  bank_txn_id > 100 ký tự → 400 {"detail": "bank_txn_id dài quá 100 ký tự.", "code": "WEBHOOK_INVALID_INPUT"}
  received_at sai → 400 {"detail": "Thiếu hoặc sai received_at (ISO 8601).", "code": "WEBHOOK_INVALID_INPUT"}   (như N3)
    // mọi lỗi 400: không tạo PaymentTransaction, đơn không đổi
  gửi lại bank_txn_id đã có, thiếu/sai order_code
  → 200 {"matched": <match_status == MATCHED>, "order_status": <trạng thái đơn đã khớp | null>, "match_status": "MATCHED|UNDERPAID|ORPHAN|UNMATCHED"}
    // trước đây: {"matched": false, "order_status": null} dù giao dịch đã khớp
  lần đầu, không khớp đơn → 200 {"matched": false, "order_status": null}   (không đổi)

GET /api/dashboard/summary/
  thêm key cấp gốc: "near_expiry_days": 14        // = settings.BATCH_NEAR_EXPIRY_DAYS
  kpis.near_expiry, alerts[], batches[].near_expiry: chỉ lô bán được (SELLING/NEAR_EXPIRY và
  expiry_date ≥ hôm nay) có expiry_date ≤ hôm nay + near_expiry_days. Lô quá hạn / DRAFT không tính.
  Các key cũ giữ nguyên; `kpis` giữ đúng 4 key cho người thiếu view_costprice (không lộ giá vốn).
```
Ví dụ:
```json
{"as_of": "2026-09-24T10:00:00+07:00", "near_expiry_days": 14,
 "user": {"username": "ql1", "can_cost": false},
 "kpis": {"revenue_today": 1610000.0, "pending_orders": 4, "booked_soon": 1, "near_expiry": 3},
 "recent_orders": [], "batches": [], "alerts": [], "activity": []}
```
Adapter không cần đổi: đã chặn `transferAmount ≤ 0` ở schema và không retry 4xx.

### Rule đã cài
- **R1 / BR-TT-03/05** — số tiền webhook là `Decimal` hữu hạn > 0, kiểm trước khi ghi hàng chờ.
- **R2** — an toàn mặc định: production không thể khởi động với DEBUG bật do quên biến, hay với key dev. Dockerfile `collectstatic` đã đặt `DJANGO_DEBUG=1` lúc build nên không bị ảnh hưởng; Cloud Run đã có `DJANGO_DEBUG=0` + `DJANGO_SECRET_KEY`.
- **R3** — so token hằng thời gian.
- **R5 / BR-TT-03** — idempotent theo `bank_txn_id` ở cả nhánh không khớp đơn: trả đúng kết quả đã ghi.
- **R6 / BR-LO-01/02, S1** — cảnh báo cận hạn dùng nguồn duy nhất `sellable_batches`.
- **R4 / BR-BH-02/03/04/06, BR-TT-06, D1** — `seed_demo` tạo dữ liệu qua service thật:
  - Lô: `qty_received = qty_available` ban đầu + bút toán RECEIPT; tồn/giữ chỗ không khai tay nữa mà sinh ra từ đơn (`LO-0918` nhập 67 → bán 4 + 2 → tồn 61; `LO-0907` nhập 37, giữ 3; `LO-0903` nhập 28, giữ 6; `LO-0921` nhập 29 → bán 2 → 27; `LO-0922` 40, giữ 5 rồi nhả). Số "còn bán được" hiển thị giữ như bản cũ.
  - Đơn: tạo BOOKED + dòng + `batches.reserve` + `SalesOrderLineBatch` trên **lô demo của mặt hàng** (không FIFO sang lô thật — demo không được giữ chỗ trên dữ liệu thật; lô trùng mã mà không phải demo → bỏ qua đơn, in cảnh báo).
  - Đơn PROCESSING/PAID/COMPLETED: `confirm_payment` với giao dịch `DEMO-<mã đơn>` (MATCHED) → `issue_invoice` mã `HD-…` (giữ mã cũ cho D1/B5): hoá đơn đủ dòng, `SalesInvoiceLineBatch` (unit_cost = landed_unit_cost), bút toán SALE, phiếu giao do signal; sau đó đặt trạng thái hiển thị (PAID/COMPLETED).
  - Đơn AUTO_CANCELLED: giữ chỗ rồi `batches.release` như job TTL; `booked_expires_at` = 20 phút trước.
  - Mỗi đơn trong savepoint riêng: thiếu tồn / mã HĐ hay mã GD đã bị dùng → bỏ qua đơn đó, in cảnh báo, không hỏng cả lượt seed. Đơn đã có mã → không đụng (idempotent).
  - `--adopt-legacy` nhận thêm: `SalesOrderLineBatch`/`SalesInvoiceLineBatch` trên lô demo của đơn/HĐ demo, `PaymentTransaction` `DEMO-<mã>`, bút toán SALE có `reference` = mã HĐ demo trên lô demo. Bản seed cũ (không có các bản ghi này) vẫn nhận/gỡ như trước.
  - Test D1/B2/B5 chạy lại toàn bộ, xanh. Một assertion B2 (`test_b2_lo_demo_co_don_that_giu_cho_so_kho_con_nguyen`) cũ so Σ sổ kho với `qty_received` — chỉ đúng khi lô chưa bán; nay so Σ sổ kho với `qty_available` và Σ RECEIPT với `qty_received` (vẫn kiểm "sổ kho còn nguyên").

### Còn nợ / giả định
- `near_expiry_days` đặt ở **cấp gốc** của response (không nằm trong `kpis`) vì `kpis` có contract khoá đúng 4 key (test L6). FE đọc `summary.near_expiry_days`.
- Lỗi "thiếu `bank_txn_id`" và "sai `amount`" nay có thêm `code: WEBHOOK_INVALID_INPUT` (thêm key, không đổi `detail` của thiếu `bank_txn_id`; `detail` của `amount` đổi câu chữ).
- Dữ liệu demo **đã có** trên một DB (bản seed trước) không tự sửa khi chạy lại `seed_demo` (đơn đã có mã → bỏ qua). Muốn có bộ demo nhất quán: `seed_demo --remove` (DB seed bằng bản cũ chưa có sổ: thêm `--adopt-legacy`) rồi `seed_demo`. Việc này trên production cần Duy duyệt.
- Phiếu giao của đơn demo COMPLETED vẫn ở `PREPARING` như bản cũ (B5: `--adopt-legacy` chỉ nhận phiếu chưa bắt đầu). Không có trong phạm vi review.
- Máy dev khác cần `.env` có `DJANGO_DEBUG=1` (đã ghi ở README/.env.example), nếu không Django dừng với thông báo rõ.
- Chưa deploy, chưa commit.

## Sửa theo code review (FE) — trước deploy 1 · 2026-09-24

Chỉ sửa `erp-console/`. Không đổi contract BE ngoài key `near_expiry_days` (BE R6 ở trên).

### 1. Menu Đơn / Kho & lô đòi thêm `reports.view_dashboard` (BR-PQ-12, S7-AC3, S8-AC5)
- `shared/lib/nav.ts`: `orders` = `sales.view_salesorder` **và** `reports.view_dashboard` (và không chỉ-nv_giao); `inventory` = `inventory.view_batch` **và** `reports.view_dashboard`. Hai màn đang đọc tạm `/api/dashboard/summary/`. Có ghi chú `TODO(S10)` / `TODO(S25)`: khi có endpoint riêng thì bỏ điều kiện dashboard. Menu, `ViewGuard`, `homePath` và `LoginScreen` cùng dùng `canView` nên tự khớp; tab "Hoạt động" (`features/inventory/components/ActivityFeed.tsx`) nay chỉ gọi `canView(me, "inventory")`.
- 403 thiếu quyền ổn định không còn làm gọi lại /me mãi: `shared/lib/http.ts` truyền thêm `"METHOD path"` cho handler 403; `features/auth/components/AuthProvider.tsx` nhớ những request đã 403 mà tải lại `me` thấy quyền **không đổi**, rồi trong 60 giây (`STABLE_FORBIDDEN_MS`) không gọi /me cho đúng request đó nữa. Request khác bị 403 vẫn tải lại `me` như cũ (S47-AC3 vẫn đạt). Bộ nhớ này xoá khi quyền đổi, khi đăng nhập hoặc đăng xuất.
- Mock (chỉ để thử): `MockUser.denied_perms` (patchUser) giả lập admin gỡ một quyền khỏi Group ở BE; `__caveMock.dashboard("forbidden")` cho summary luôn trả 403 (giả lập luật FE/BE lệch nhau).

### 2. Xác nhận sau khi đặt mật khẩu mới (S48-AC2)
- Lỗi cũ: `changePassword` chờ `loadMe` xong, cờ tắt, màn chuyển đi trước khi kịp `setDone`, nên câu xác nhận không bao giờ hiện.
- Cách sửa: khi người dùng **đang bị ép** đổi mật khẩu, `AuthProvider.changePassword` đặt `passwordNotice = MSG.mustChangeDone` **trước** khi tải lại `me`. Sau đó `ConsoleGate` hiện `.alert-box.ok.pw-done-notice` (có nút đóng 44×44) ở đầu màn home theo vai (Tổng quan / Việc giao). Thông báo mất khi đăng nhập hoặc đăng xuất. Tự đổi mật khẩu ở S46 (không bị ép) thì không có thông báo này. `SetPasswordScreen` bỏ state `done` không dùng tới.
- Câu `MSG.mustChangeDone` đổi thành "Đã đặt mật khẩu mới. Lần sau đăng nhập bằng mật khẩu này." (bỏ "Đang mở màn làm việc…" vì lúc câu hiện thì màn đã mở).

### 3. Số ngày cận hạn lấy từ BE
- `shared/lib/dashboardSummary.ts`: thêm `near_expiry_days?: number` ở **cấp gốc** của `DashboardSummary`, khớp BE R6 (`kpis` giữ 4 key). Thêm hàm `nearExpiryDays(data)`: nếu thiếu hoặc không hợp lệ thì trả `null`.
- `features/overview/components/KpiTiles.tsx`: ô "Lô cận hạn" ghi "trong N ngày tới" theo BE; BE cũ chưa có key thì ghi "lô sắp hết hạn dùng", không bịa ra số 14.
- Mock `shared/lib/dashboardSummary.mock.ts`: trả `near_expiry_days: 14` ở cấp gốc; mode `"nodays"` bỏ key này. Tiêu chí cận hạn làm theo BE R6: chỉ tính lô SELLING/NEAR_EXPIRY còn hạn (≥ hôm nay) và hạn ≤ hôm nay + N; lô DRAFT không tính. Vì vậy số KPI cận hạn của mock giảm 1 (lô DRAFT `L0923-SO01` không còn tính).
- Lệch contract: lúc đầu FE đọc tạm cả `kpis.near_expiry_days`. Điều phối báo BE đặt ở cấp gốc nên đã sửa theo, không còn chỗ lệch.

### Kiểm
- `./node_modules/.bin/tsc --noEmit` → sạch. `npm run build` (build thật, không có `NEXT_PUBLIC_USE_MOCK`) → sạch. Trong `out/` không có `__caveMock`, `cave_erp_mock`, `demo1234`, `mock-token-`, `mockRequestLog` hay dữ liệu seed.
- E2E trên build mock phục vụ tĩnh ở cổng 3101 (đã kill, lsof 3100/3101 sạch): `s8_views` **46/46**, `s48_password` **41/41**, `s7_shell` **25/25**, `s41_s47_staff` **72/72**.
- Ca mới:
  - `s8_views`:
    - #3: có key → "trong 14 ngày tới"; key nằm ở cấp gốc, không trong `kpis`; `kpis` của ql1 đúng 4 key; mode `nodays` → không ghi số ngày.
    - #1: 403 ổn định, đi lại 4 màn bằng menu → có gọi summary nhưng không gọi /me, không hiện perm-notice.
    - #1: kho1 bị gỡ `reports.view_dashboard` → menu không có Tổng quan / Đơn / Kho & lô, vào về Giao hàng; gõ `/orders/`, `/inventory/` → ViewGuard chặn, chỉ gọi /me 1 lần; tab Hoạt động không gọi summary.
  - `s48_password` (#2): kho5 và giao6 đặt mật khẩu xong thấy `.pw-done-notice` với đúng `MSG.mustChangeDone`; đóng được; đăng nhập lại không còn thông báo.
  - `s41_s47_staff`: tự đổi mật khẩu ở S46 không hiện thông báo này.
- Ảnh: `shots/review/review-mobile-360-password-done-overview.png` (360: thông báo + "trong 14 ngày tới", không cuộn ngang), `shots/review/review-desktop-1280-kho1-no-dashboard.png`. Ảnh các bộ e2e chạy lại cũng ghi vào `shots/review/`.

### Còn nợ
- Khi S10 / S25 có endpoint riêng: bỏ điều kiện `reports.view_dashboard` ở `nav.ts` (theo TODO) và sửa lại ca "kho1 thiếu view_dashboard" trong `s8_views`.
- Mốc 60 giây chống gọi /me lặp đang cứng ở FE (`STABLE_FORBIDDEN_MS`). Đây là tham số giao diện, không phải tham số nghiệp vụ.
- Chưa commit, chưa deploy.

## UI1–UI2 (FE) — design system + khung ERP, đăng nhập, đặt mật khẩu, no-role · 2026-09-24

Chỉ đổi giao diện: không đổi nghiệp vụ, contract API, luồng hay câu chữ nghiệp vụ. Không mã BR mới.

### UI1: design system
- Tra `ui-ux-pro-max` (`search.py … --design-system`, `-d google-fonts`, `-d ux`): gợi ý "Minimalism & Swiss" cho dashboard SaaS; font có subset `vietnamese` (Inter, Be Vietnam Pro, JetBrains Mono, IBM Plex Mono). Lấy phần hướng (Restrained, AA, reduced-motion); **không** lấy màu cam CTA và font Calistoga mà script gợi ý vì trái hướng Duy đã chốt (1 màu nhấn xanh biển, tinh gọn).
- `impeccable context` chạy được (binary tải từ GitHub releases, **không bật hooks**). Không có công cụ hỏi đáp trong phiên subagent → không phỏng vấn được: `PRODUCT.md` viết từ `doc/URD.md` + skill `caveve-ui`, mục suy luận có đánh dấu **(suy luận)**, cần Duy xác nhận. Hướng hình ảnh do brief ghim sẵn (Linear/Notion) nên không chạy vòng `concept-seed`. Không tạo sidecar `.impeccable/design.json`.
- **`DESIGN.md` (gốc repo)**, dùng chung ERP/Shop/app: màu light + dark (bảng đo tương phản), Inter + JetBrains Mono (đủ dấu tiếng Việt), thang chữ cố định 11–24px + ô nhập 16px, khoảng cách bước 4px, bo góc 4–14px, 4 mức bóng, chuyển động (120/180/240ms, `--ease-out`, `--ease-drawer`), focus ring, z-index, trạng thái, Do/Don't.
- **`PRODUCT.md` (gốc repo)**: sự thật sản phẩm cho impeccable. Ghi vào `README.md` gốc và `erp-console/README.md`.
- **`erp-console/shared/ui/tokens.css`**: file duy nhất có mã màu. Nạp trước `globals.css` ở `app/layout.tsx`.
- `globals.css` viết lại toàn bộ bằng `var(--…)`, giữ nguyên mọi tên class (e2e bám class). Kiểm: `grep -rnE '#[0-9a-fA-F]{3,8}\b|rgba?\(' app features shared` ngoài `tokens.css` = **0**; `style={{` = **0** (bỏ 5 chỗ inline ở NoRole, NotFound, ConsoleGate).
- `theme-color` của trình duyệt không còn viết cứng ở `layout.tsx`: `themeScript.ts` đọc token `--canvas`, đồng bộ khi tải trang, khi máy đổi sáng/tối và khi bấm nút đổi giao diện (`ThemeToggle` gọi `syncThemeColor()`).
- `.num` (tiền, kg) đổi từ IBM Plex Mono sang Inter `tabular-nums`; mono chỉ còn cho mã (mã đơn, tên đăng nhập, mật khẩu tạm).

### UI2: khung ERP + màn ngoài console
- **Shell** (`shared/ui/Shell.tsx`, CSS): 3 cột ≥1024px (240 · nội dung · 320), menu trái nền `sidebar`, mục đang chọn `accent-soft` + icon đặc; topbar 56px trùng hàng với đầu cột phải; menu đáy 60px + safe-area, mục đang chọn có viên nền sau icon; ngăn kéo trượt 240ms `--ease-drawer`, đóng vẫn có chuyển động (visibility trễ). Thêm liên kết "Bỏ qua menu, tới nội dung" (`.skip-link`, hiện khi focus), `<main tabIndex=-1>`, `nav` có `aria-label`.
- **RightRail**: tab gạch chân accent; tab có `id`, tabpanel có `aria-labelledby`.
- **LoginScreen / SetPasswordScreen**: điện thoại (<480px) form nằm thẳng trên nền trắng, căn trên (tay cái, bàn phím không che); ≥480px thành thẻ giữa màn trên nền `sidebar`. Không đổi markup/luồng.
- **NoRoleScreen, NotFoundScreen**: cùng khung thẻ với đăng nhập (logo, icon, tiêu đề, câu, nút). NoRole: nút đăng xuất có trạng thái đang gửi ("Đang đăng xuất…").
- **AccountScreen**: khối người dùng thành đầu trang (không đóng khung, tránh thẻ lồng thẻ), dòng phụ "tên đăng nhập · SĐT"; giữ class `.who-card`.
- **ConsoleGate**: màn lỗi /me dùng `.fullscreen-stack` thay inline style.
- **PasswordInput**: chỉ CSS — nút mắt 44×44 trong ô, bấm có phản hồi, đang hiện chữ thì icon màu accent; quy tắc mật khẩu đổi màu mượt.
- **Sheet** (dùng ở Tài khoản của tôi): giữ Tab trong hộp thoại (focus trap); tấm trượt đáy trên điện thoại, hộp `scale(.97)→1` trên desktop.
- `emil-design-eng`: `:active scale(.97)` cho nút, `.94` cho nút icon; hover chỉ trong `@media (hover:hover)`; chỉ animate transform/opacity/màu, không `transition: all`; `prefers-reduced-motion` bỏ trượt/phóng, icon tải quay chậm.
- `mobile-native`: `100dvh`, ô nhập 16px trên máy cảm ứng (14px khi `pointer: fine`), `-webkit-tap-highlight-color: transparent` (đã có phản hồi `:active`), `touch-action: manipulation`, safe-area cho topbar/menu đáy/ngăn kéo/màn đăng nhập/tấm trượt, `overscroll-behavior`.
- Vì `globals.css` dùng chung nên màn S8/S41 (Tổng quan, Đơn, Kho, Nhân sự) cũng đổi theo token (màu, chữ, bảng, chip); làm lại bố cục các màn đó là UI3/UI4.

### E2E (mock, `NEXT_PUBLIC_USE_MOCK=1` build + `http.server`, server đã tắt, `lsof` sạch)
- `s7_shell` 25/25 · `s8_views` 46/46 · `s41_s47_staff` 72/72 · `s48_password` 41/41 — **184/184 PASS**.
- Sửa e2e (không nới kiểm tra): `s41_s47_staff.py` trước khi `patchUser('ql9', {extra_perms: []})` chờ `window.__caveMock.pending() === 0`. Lý do: 403 `CHU_GROUP_ONLY` ngay trước đó làm console tải lại `/me`; mock trả lời sau 250ms và đọc dữ liệu lúc trả lời, nên nếu đổi quyền khi `/me` còn bay thì màn Nhân viên bị ẩn trước khi mở `giao2` (đua thời gian của kịch bản, không phải lỗi app). Thêm `pending()` vào `window.__caveMock` ở nhánh mock của `shared/lib/http.ts` (bản build thật không có: `grep __caveMock|demo1234|Chế độ mock out/` = 0).
- Hai lỗi layout e2e bắt được và đã sửa: ô tìm cao 42px (trả lại 44px), nút phân đoạn `.seg` cao 38px (trả lại `--tap`).

### Kiểm khác
- `tsc --noEmit` sạch; `npm run build` thật sạch, `out/` không chứa code mock (build cuối cùng là bản thật).
- `impeccable detect --json` trên các file đã sửa: `[]`.
- `fixing-accessibility` cho Shell, RightRail, Login, SetPassword, NoRole, Account, PasswordInput, Sheet: đã sửa skip link, tên `nav`, liên kết tab ↔ panel, focus trap hộp thoại. Tương phản: mọi cặp chữ/nền trong `DESIGN.md` đo ≥ 4.5:1 cả light và dark; viền ô nhập ≥ 3:1.
- Ảnh TRƯỚC/SAU ở `shots/ui/` (`before-*` chụp trước khi sửa, `after-*` sau): `login`, `set-password`, `no-role`, `shell-overview`, `account` ở 360 + 1280 × light + dark, thêm `shell-menu` (ngăn kéo menu) ở 360.

### Còn nợ
- `PRODUCT.md` có mục **(suy luận)**: Duy xác nhận/sửa.
- Nút đăng nhập bị tắt khi chưa nhập đủ (hành vi cũ, S7) chưa có câu giải thích; giữ nguyên vì không đổi luồng.
- Ngăn kéo menu trên điện thoại chưa chuyển focus vào trong khi mở (Esc và bấm nền vẫn đóng được).
- Shop (`frontend/`) chưa dùng token của `DESIGN.md` (ngoài phạm vi lô này).
- UI3 (Tổng quan, Đơn, Kho), UI4 (Nhân sự, form, sheet), UI5 (review) chưa làm.
- Chưa commit, chưa deploy.

## UI3 (FE) — Tổng quan, Đơn, Kho & lô · 2026-09-25

Chỉ giao diện: không đổi contract API, luồng, quyền hay dữ liệu hiển thị (cột, số, nhãn trạng thái của BE giữ nguyên). Không mã BR mới.
Giá vốn vẫn chỉ hiện khi `user.can_cost` (cột "Giá vốn/kg", KPI giá trị tồn); e2e AC2/AC3 xanh.
Hướng theo nhận xét điều phối: bỏ "lưới thẻ đóng khung", làm phẳng kiểu Linear/Notion. `impeccable context` + đọc `craft-floor`/`operate`/`polish`; `impeccable detect --json` trên mọi file đã sửa: `[]`.

### Đã làm
- **KPI** (`features/overview/components/KpiTiles.tsx`): bỏ 4 hộp viền → một dải phẳng `dl.kpis` trong `.kpi-band` (container query): kẻ mảnh trên/dưới, chia cột bằng đường 1 px; một hàng 4 cột khi vùng chứa ≥ 600 px, lưới 2×2 kẻ mảnh khi hẹp. Nhãn 12 `ink-3`, số 20/24 px tabular-nums, đơn vị nhỏ `ink-3`, phụ chú 12. Màu chỉ khi cần chú ý: "N sắp hết giữ chỗ" (hổ phách + icon), số lô cận hạn > 0 tô hổ phách. Bỏ icon trang trí ở nhãn. Giữ `.tile[data-kpi] .val/.foot` (e2e bám).
- **Tổng quan** (`OverviewScreen.tsx`): thứ tự Dải số liệu → **Cần chú ý** (cận hạn, lên trước trên điện thoại; ≥1400 px nằm cột phải) → Đơn hàng gần đây → Tồn kho theo lô. Khối phẳng `.sect` thay `.panel`. "Cần chú ý" là danh sách dòng phẳng, icon màu trạng thái (không ô vuông tô nền); không có lô cận hạn → dòng xanh "Không có lô cận hạn.".
- **Bảng** (`table.data` trong `.dt-wrap`, dùng ở 3 màn): hàng ~44 px ngăn đường mảnh, số căn phải tabular + đơn vị `ink-3` (`shared/ui/Figure`), mã đơn/lô mono 12 `ink-3`, tên (khách/mặt hàng) 500 `ink`, hover hàng `surface-2` (chỉ `hover:hover`, 120 ms), **header dính** khi cuộn (`--z-sticky`, bù đúng lề trên `.content` qua `--content-pt`). Bỏ viền trái màu `strip-warn/crit` và icon cá trang trí; hạn dùng cận hạn/quá hạn tô chữ hổ phách/đỏ.
- **Trạng thái dạng chấm + chữ** (`shared/ui/StatusChip.tsx` → `.status`): chấm 8 px + `status_label`; `warn`/`crit` tô cả chữ, `mute` là chấm rỗng. Viên thuốc `.chip` giữ nguyên cho Nhân sự/Tài khoản.
- **Danh sách gọn khi hẹp**: container query `@container dt (max-width:639px)` (điện thoại và cột giữa 1024–1279 px) → mỗi hàng 2 dòng: tên + số chính; mã · thông tin phụ (nhãn ngắn `data-m-label`: "Giữ chỗ còn", "NCC", "Vốn/kg", "Hạn", "Giữ") · trạng thái bên phải. Ô rỗng ẩn (`m-hide`). Không card lồng card. 640–959 px vùng chứa: lề ô 8 px, ô chữ xuống dòng, không cuộn ngang (đo 360→1920 px, Chủ + Quản lý: bảng luôn vừa khung, `scrollWidth` = viewport).
- **Trạng thái**: tải = **khung chờ đúng hình** (`shared/ui/Skeleton.tsx`: dải KPI + khối bảng, `role=status` + chữ ẩn "Đang tải dữ liệu…", pulse 1.4 s, đứng yên khi giảm chuyển động) qua prop mới `skeleton` của `ResourceView`; rỗng = icon + tiêu đề + câu hướng dẫn + hành động ("Làm mới danh sách" ở Đơn; "Mở Mua hàng" ở bảng lô nếu có quyền xem Mua hàng); tìm không khớp = câu gợi ý + nút "Hiện tất cả"; lỗi = icon nền `crit-soft` + câu + "Thử lại"; 403 từ API = icon khoá (vẫn có "Thử lại", e2e Review #1); 403 ViewGuard = `.empty` phẳng, không còn hộp viền.
- a11y (`fixing-accessibility`): `th scope="col"`; `dl/dt/dd` cho số liệu + tiêu đề ẩn "Số liệu hôm nay"; chấm trạng thái `aria-hidden`, chữ luôn có; "Xem tất cả" có tên đủ nghĩa "Xem tất cả đơn hàng"; khung chờ `aria-busy`; tương phản: `ink-3`/`warn`/`crit` trên `canvas` đều ≥ 4.5:1 cả light/dark (theo bảng DESIGN.md). Vùng bấm 360 px ≥ 44 px (e2e).
- `emil-design-eng`/`baseline-ui`: chỉ animate màu nền hàng và mũi tên liên kết (nhích 2 px, `--ease-out`, tắt khi giảm chuyển động); không `transition: all`; không gradient/bóng; z-index theo token.

### Dùng chung mới (cho UI4 dùng lại) — `shared/ui/`
- `Figure.tsx` (số + đơn vị), `Skeleton.tsx` (`SkeletonScreen`, `SkeletonKpis`, `SkeletonTable`), `ResourceView` prop `skeleton`, `ErrorBox` prop `icon`, `EmptyRow` prop `hint` / `action` / `onClearSearch` (tương thích ngược: Nhân sự không phải sửa).
- CSS: `.sect/.sect-h`, `.dt-wrap > table.data` + class ô `m-title m-fig m-status m-hide data-m-label`, `.status`, `.fig/.unit`, `.state-ic/.state-title`, `.calm`, `.crit-text`, `.sk*`. Token mới `--z-sticky:5` (`tokens.css`), biến `--content-pt` trên `.content`. `DESIGN.md` thêm mục Status dot, KPI strip, Data table, Section, khung chờ.
- Không đổi: `.panel`, `.table-wrap`, `table.cards`, `.chip` (Nhân sự vẫn dùng). Bỏ CSS chỉ 3 màn này dùng: `.delta`, `.prod`, `.strip-warn/.strip-crit`, ô vuông `.alert .ai`. `.empty` (ViewGuard/Placeholder) nay phẳng, không viền.

### E2E (mock build + `http.server`, server đã tắt, `lsof` cổng 3111/3112 sạch)
- `s7_shell` 25/25 · `s8_views` 46/46; hồi quy `s41_s47_staff` 72/72 · `s48_password` 41/41.
- Sửa `e2e/s8_views.py` (không nới): (1) kiểm rỗng đổi từ "đếm 2 lần 'Chưa có dữ liệu'" sang kiểm đúng câu trong từng bảng ("Chưa có đơn nào" trong `ov-orders`, "Chưa có lô nào đang hoạt động" trong `ov-batches`, `exact=True`); (2) phần so với bản cũ (AC1, chỉ chạy khi có `LEGACY_BASE`) bỏ chữ của icon `.mi` ở **cả** bản cũ lẫn mới trước khi so ô/cận hạn, vì UI3 bỏ icon trang trí trong ô.

### Kiểm khác
- `tsc --noEmit` sạch; `npm run build` **thật** sạch (build cuối là bản thật; `grep __caveMock|demo1234|Chế độ mock out/` = 0).
- `grep -rnE '#[0-9a-fA-F]{3,8}\b|rgba?\(' app features shared` ngoài `tokens.css` = 0; `style={{` = 0.
- Ảnh `shots/ui/`: `ui3-before-{overview,orders,inventory}-{360,1280}-{light,dark}` (chụp trước khi sửa) và `ui3-after-*` cùng bộ; thêm trạng thái ở `ui3-after-`: `overview-empty-*`, `overview-fail-*`, `overview-forbidden-*` (403 API), `inventory-loading-*` (khung chờ), `orders-nomatch-*`, `inventory-403-*` (ViewGuard, giao1) — 360 + 1280 light.

### Còn nợ
- Danh sách gọn trên điện thoại ẩn `thead` → trình đọc màn hình không còn đọc tên cột cho ô không có `data-m-label` (mã, kho) — như bản `table.cards` trước; UI5 cân nhắc thêm nhãn ẩn.
- Hành động rỗng "Mở Mua hàng" dẫn tới màn Mua hàng đang là khung chờ (S-sau); đổi thành "Nhập lô" khi màn đó xong.
- `ActivityFeed` (tab Hoạt động cột phải) chưa làm lại (ngoài 3 màn), vẫn theo token.
- Chưa commit, chưa deploy.

## UI4 (FE) — Nhân sự + Tài khoản của tôi · 2026-09-25

Chỉ giao diện: không đổi contract API, luồng, `available_actions`, thông điệp BE hay mã BR. Không mã BR mới. Làm song song
với UI3: **không sửa** `shared/ui/*`, `globals.css`, `tokens.css`; kiểu riêng ở CSS module của feature, chỉ dùng token có sẵn.
Skill: `caveve-ui`, `impeccable` (`context` + craft-floor + polish, không bật hooks), `emil-design-eng`, `baseline-ui`, `fixing-accessibility`.
Không có công cụ hỏi đáp trong phiên subagent → không phỏng vấn được; brief của lô đủ chi tiết nên làm theo brief.

### Kết quả kiểm chứng
- `tsc --noEmit` sạch; `npm run build` **thật** (không mock) sạch trong repo, `out/` không có code mock (`__caveMock|demo1234|Chế độ mock` = 0).
- E2E mock (bản build mock trong scratchpad, `http.server` :3107): `s41_s47_staff` **72/72**, `s48_password` **41/41**, `s7_shell` 25/25, `s8_views` 46/46.
- E2E **backend thật**: Django `runserver` 127.0.0.1:8017, SQLite tạm trong scratchpad (`migrate` → `bootstrap_masterdata` → seed 5 tài khoản), console build thật `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8017` phục vụ :3108: `s41_s47_real` **39/39**. `backend/db.sqlite3` không đụng (mtime vẫn 13/09).
- `impeccable detect --json` trên các file đã sửa: `[]`. Grep hex/`rgba(` trong `features/staff`, `features/auth`, `app/(console)/{staff,account}` = **0**; `style={{` = 0.
- Mọi server (3107, 3108, 8017) đã tắt, `lsof` sạch.

### Trang / component đã sửa
- **Danh sách nhân viên** (`features/staff/components/StaffScreen.tsx`): bảng → danh sách hàng thoáng kiểu Linear trong một khung: avatar chữ cái (chữ đầu của **tên riêng**, từ cuối: "Anh Phúc" → P), tên + tên đăng nhập (mono), nhãn nhóm nhẹ (`surface-2` + viền mảnh, không dùng màu nhấn), trạng thái = chấm + chữ (đang làm: chấm đặc `good`; đã nghỉ: vòng rỗng xám, hàng mờ tên), đăng nhập gần nhất, nút gọi (`tel:`). Container query: khung ≥600px thành 4 cột (người · nhóm · trạng thái+giờ · SĐT), hẹp hơn thì 2 dòng + icon gọi 44×44. Đầu khung "9 người · đang làm" / "3 / 9 người khớp". Thanh trên: phân đoạn lọc gọn + "Thêm nhân viên"; ≥1240px một hàng lọc · tìm · thêm, 640–1239px tìm xuống hàng 2. Đang tải lần đầu = khung xương 5 hàng (`aria-busy`, `role=status`); rỗng = icon + tiêu đề + câu + một hành động ("Xoá tìm kiếm" / "Xem người đang làm"); lỗi = `ResourceView` (Thử lại); 403 = `ViewGuard` như cũ.
- **Tấm bên** (`features/auth/components/SideSheet.tsx` + `overlay.module.css`): bọc `shared/ui/Sheet` (giữ focus trap, Esc, bấm nền, `busy`) — ≥768px là tấm phải cao hết màn (480px, trượt từ phải 240ms `--ease-drawer`), dưới 768px là tấm trượt đáy; **đóng có chuyển động ra** 180ms (ra nhanh hơn vào), bật giảm chuyển động thì đóng ngay. Nội dung có thể tự đóng qua `close()` (lưu xong vẫn có chuyển động ra).
- **Chi tiết** (`StaffDetail.tsx`): tự render tấm, **tiêu đề đổi theo bước** ("Đổi nhóm · Anh Tâm"). Đầu: avatar + tên đăng nhập + trạng thái; thuộc tính kiểu Notion (SĐT, Nhóm, Đăng nhập gần nhất); thao tác dạng nhóm hàng như trang cài đặt, "Cho nghỉ" tách riêng màu `crit` + câu hậu quả. Đổi chế độ: nội dung vào nhẹ (opacity + 4px), **focus chuyển** vào ô đầu / nút an toàn của bước mới, quay lại thì focus về đúng nút thao tác vừa bấm (`useFocusOnSwap`).
- **Xác nhận nguy hiểm** (`parts.tsx` `DangerConfirm`): icon tròn (`crit-soft`; thêm/tạo Chủ dùng `warn-soft`), tiêu đề câu hỏi ("Cho Anh Tâm (kho1) nghỉ?", "Cấp quyền Chủ?", "Gỡ quyền Chủ?", "Tạo tài khoản thuộc nhóm Chủ?"), hậu quả dạng danh sách (giữ nguyên câu cũ), nút an toàn focus trước và `aria-describedby` tới hậu quả, nút xác nhận `btn danger solid`. Lỗi BE (BR-GH-08, BR-PQ-17/18…) hiện nguyên văn ngay trên thanh nút.
- **Form tạo / sửa / đặt lại** : một cột, nhãn trên ô, gợi ý dưới ô (`aria-describedby`), dấu `*` cho ô bắt buộc (`aria-hidden`, ô có `required`), 3 phần ngăn bằng đường mảnh; **thanh nút dính đáy tấm** (tay cái), máy tính căn phải. Lỗi "Hai mật khẩu không khớp" tại ô (như cũ); lỗi BE nguyên văn ngay trên nút gửi, tự cuộn tới. Đổi nhóm có dòng tóm tắt thay đổi "Thêm: … · Bỏ: …" / "Chưa đổi gì." (`aria-live`), giải thích vì sao nút Lưu đang tắt.
- **Chọn nhóm** (`GroupPicker.tsx`): thẻ ô chọn gọn (56px, chọn = viền `accent` + nền `accent-soft`, nhấn `scale(.99)`, vòng focus trên thẻ khi ô được focus bằng phím). Giữ `.check-row` để e2e đo vùng bấm.
- **Mật khẩu tạm** (`PasswordField.tsx`, `CopyButton.tsx`): dòng công cụ dưới ô: "Tạo ngẫu nhiên" + "Sao chép" (phản hồi "Đã chép" + dấu tích 1,6s, màu `good`; báo trình đọc màn hình qua `role=status`; không có clipboard thì thử `execCommand`, vẫn không được thì "Không chép được"). Tạo xong / đặt lại xong: khối **Credentials** (tên đăng nhập, mật khẩu, mỗi dòng nút "Chép", thêm "Chép cả hai") thay ô `.secret`.
- **Thông báo nổi** (`features/auth/components/Toast.tsx`): kết quả thao tác hiện ở đáy (trên menu đáy ở điện thoại, giữa đáy ở máy tính), vào `translateY(8px) scale(.98)` 180ms, tự ẩn sau 6s, **dừng đếm khi rê chuột/focus/tab bị ẩn**, có nút đóng; chỉ hiện khi tấm đã đóng. Giữ lớp `.alert-box.ok`.
- **Tài khoản của tôi** (`AccountScreen.tsx` + `account.module.css`): trang một cột tối đa 720px kiểu trang cài đặt: đầu trang người dùng (avatar, tên, tên đăng nhập mono, SĐT, nhãn nhóm), rồi 3 phần tiêu đề + nhóm hàng: "Việc bạn được làm" (danh sách dấu tích, 2 cột từ 520px; Xem giá vốn / Xem báo cáo lãi lỗ = chấm + Có/Không), "Mục bạn thấy trên menu" (icon + tên, 2 cột; chân: câu giải thích + "Tải lại quyền"), "Mật khẩu và đăng xuất" (hàng cài đặt: icon, tên, hậu quả, nút; Đăng xuất là nút `danger`, đang gửi "Đang đăng xuất…"). Đổi mật khẩu mở trong tấm bên; `ChangePasswordForm` **không đổi** (dùng chung với màn S48).
- Micro-interaction (`emil-design-eng`): chỉ animate transform/opacity/màu nền nhỏ; hover chỉ trong `@media (hover:hover)`; hàng danh sách nhấn = `surface-3`; mọi thời lượng 120–240ms; `prefers-reduced-motion` tắt trượt (luật chung ở globals + SideSheet đóng ngay).
- Placeholder ô tìm rút gọn "Tìm tên, SĐT, nhóm…" (bản cũ bị cắt trên 360px); tìm theo tên đăng nhập vẫn chạy.

### E2E: đổi móc, không nới kiểm tra
`s41_s47_staff.py`, `s48_password.py`, `s41_s47_real.py`: `table.staff-table tbody tr` → `ul.staff-list > li`; `.rowbtn` → `.staff-open`; `.chip.info` → `.group-tag`; `.action-list button` → `.staff-actions button`; `.alert-box.warn` (xác nhận) → `.confirm-danger`; `.kv.yn` → `.perm-yn`; `.who-card .chip` → `.who-card .group-tag`; `.secret` "giao4 · Songbien2026" → hai kiểm chính xác `.cred-username` = "giao4" và `.cred-password` = "Songbien2026". Nút mở hàng có tên truy cập "Tên, tên đăng nhập" (nhóm/trạng thái là `aria-describedby`) để không trùng tên với nút lọc "Đang làm".

### Ảnh (`shots/ui/`)
`ui4-before-{staff-list,staff-create,staff-detail,account}-{360,1280}-{light,dark}` (chụp trước khi sửa) và `ui4-after-*` cùng bộ; thêm `ui4-after-staff-{confirm,groups}-*`, `ui4-after-flow-{pwtools-360-light,created-1280-dark,toast-360-light,confirm-err-1280-dark}`, `ui4-after-staff-list-800-light`. Ảnh account "after" chụp khung cao hơn (1500/1100px) để thấy hết trang.

### Đề xuất cho component/token dùng chung (không tự sửa, chủ `shared/ui` quyết)
- Đưa `SideSheet` (biến thể `side` của `Sheet`, có chuyển động ra) và `Toast` lên `shared/ui`; thêm token `--z-toast` (hiện Toast dùng `--z-scrim`).
- Có thể xoá luật globals không còn màn nào dùng sau UI4: `.rowbtn`, `.row-off`, `.secret`, `.action-list`, `.groups-pick`, `.staff-detail`, `.kv.yn`, `.who-text/.who-meta` (kiểm grep trước khi xoá — UI3 có thể dùng `.kv`).
- Nhãn nhóm (`.tag`) và chấm trạng thái đang chép ở `staff.module.css` và `account.module.css`: gom thành component chung nếu màn khác cần.

### Lệch contract / cần BE biết
- Không lệch contract. Lỗi BE `{code, detail}` không có tên trường (`code` là mã BR, vd BR-PQ-08 dùng cho cả SĐT, tên đăng nhập, mật khẩu) → FE không gắn được lỗi vào đúng ô mà không đoán; hiện nguyên văn ngay trên nút gửi. Nếu muốn lỗi tại ô: BE thêm `field` vào body lỗi.

### Còn nợ
- Ngăn kéo menu điện thoại (Shell, UI2) vẫn chưa chuyển focus vào trong khi mở — ngoài phạm vi UI4.
- Nút "Đặt lại mật khẩu" tắt khi chưa nhập đủ hai ô chỉ có `title` giải thích (hành vi cũ).
- Chưa commit, chưa deploy.

## UI5 (FE) — soát & đánh bóng · 2026-09-25

Chỉ giao diện trên toàn `erp-console/`: không đổi contract API, luồng, quyền, dữ liệu hiển thị hay thông điệp BE. Không mã BR mới.
Giá vốn vẫn chỉ hiện khi `user.can_cost` (e2e S8-AC2/AC3 xanh). Phiên bị ngắt một lần vì giới hạn (rate limit) lúc mới dựng
`impeccable context`; điều phối xác nhận chưa có file nào bị sửa, làm lại từ bước 1.

**Cách chấm.** `impeccable context` (binary đã có, **không bật hooks**) → `impeccable audit` (5 trục, file:dòng) + `impeccable critique`
(10 heuristic Nielsen) + `web-design-guidelines` (quy tắc tải mới từ `vercel-labs/web-interface-guidelines`) + `fixing-accessibility`
+ `mobile-native` + `fixing-motion-performance` + `emil-design-eng`. Critique chạy **một ngữ cảnh** (phiên subagent không có công cụ
tạo subagent → không tách được Assessment A/B như playbook đòi: *degraded run*, ghi rõ). Không có công cụ hỏi đáp → không phỏng vấn,
làm theo brief. Bằng chứng máy: `impeccable detect --json` trên `app features shared`; kịch bản đo tự viết (scratchpad `ui5/shots.py`):
mỗi màn × 360/1280 × sáng/tối đo cuộn ngang, vùng bấm < 44 px (360), phần tử bấm được không tên, ô nhập < 16 px, phần tử tràn phải;
và `ui5/a11y.py` kiểm hành vi (ngăn kéo, tab, lỗi tại ô, nhãn cột ẩn). Màn chấm: đăng nhập, đặt mật khẩu mới, chưa phân quyền, 404,
khung/menu/ngăn kéo/cột phải (Ghi chú · Trợ lý · Hoạt động), Tổng quan, Đơn, Kho & lô, Nhân sự + chi tiết + xác nhận + tạo,
Tài khoản của tôi, trạng thái tải/rỗng/lỗi/403.

### Bảng phát hiện TRƯỚC khi sửa (mức: Cao = P1, Trung = P2, Thấp = P3; dòng = trước khi sửa)

| # | Mức | Nguồn | File:dòng | Phát hiện | Sau UI5 |
|---|---|---|---|---|---|
| 1 | Cao | fixing-a11y · WCAG 2.4.3 | `shared/ui/Shell.tsx:86,157` | Ngăn kéo menu (< 768) và cột phải (< 1024) mở mà focus vẫn ở nút ☰; Tab đi ra nội dung phía sau; đóng không trả focus; ngăn kéo menu không có nút đóng (người dùng trình đọc màn hình trên điện thoại khó bấm Esc) | Sửa |
| 2 | Cao | fixing-a11y ("disabled submit must explain why") · WIG Forms | `features/auth/components/LoginScreen.tsx:108`, `ChangePasswordForm.tsx:109`, `features/staff/components/StaffDetail.tsx:~304` | Nút Đăng nhập / Đổi mật khẩu / Lưu mật khẩu mới / Đặt lại mật khẩu bị tắt khi thiếu ô, không nói lý do (chỉ `title` ở Đặt lại) | Sửa |
| 3 | Cao | fixing-a11y · WCAG 1.3.1 | `shared/ui/globals.css:273-287` | Bảng dạng hàng (vùng chứa < 640 px) ẩn `thead` → trình đọc màn hình mất tên cột cho ô không có `data-m-label` (mã, khách, kho, SĐT, trạng thái…) | Sửa |
| 4 | Trung | DESIGN.md "màu trạng thái phải có nghĩa" · UI3 nợ | `features/inventory/components/ActivityFeed.tsx:52`, `globals.css:297-307` | Tab Hoạt động: mọi phát sinh xuất tô **đỏ** `crit` (bán hàng bình thường trông như lỗi), icon xe tải cho cả kiểm kê/huỷ; giờ không có ngày (23:52 hôm qua lẫn 00:51 hôm nay); mã lô đậm, không mono như bảng; số kg lẫn trong câu, không căn | Sửa |
| 5 | Trung | critique (H4, H8) · brief | `shared/ui/RightRail.tsx:101,115-121` | Tab "Hoạt động" xuống 2 dòng ở 360 px; tab Trợ lý là hộp viền chữ (`.hintbox`) — "sắp có" chưa rõ, trông như lỗi chưa xong | Sửa |
| 6 | Trung | fixing-a11y (keyboard) | `shared/ui/RightRail.tsx:89` | `role=tablist` không có phím ← → Home End, cả 3 tab đều trong thứ tự Tab | Sửa |
| 7 | Trung | critique H4 (nhất quán) | `globals.css:337-369`, `staff.module.css:123-127`, `ActivityFeed.tsx:27,41`, `StateBox.tsx:32` | 4 kiểu rỗng/lỗi khác nhau: `.empty` (ô 48, tiêu đề 17), bảng `.state` (ô 40, tiêu đề 14), Nhân sự (ô 44, tiêu đề 15), cột phải (icon trần); lỗi không có tiêu đề | Sửa |
| 8 | Trung | critique H4 | `staff.module.css:25-37`, `StaffScreen.tsx:196-207` | Danh sách Nhân sự đóng khung + đầu khung 12 px riêng, trong khi Tổng quan/Đơn/Kho phẳng với `.sect-h` | Sửa |
| 9 | Trung | nextjs-shop-patterns (module không import ruột module khác) · UI4 đề xuất | `features/staff/components/StaffScreen.tsx:10-11`, `StaffDetail.tsx:10`, `overlay.module.css:44` | `SideSheet`, `Toast` nằm trong `features/auth` nhưng `staff` import vào; Toast mượn `--z-scrim` | Sửa |
| 10 | Trung | audit Theming (trùng lặp) | `staff.module.css:81-89`, `account.module.css:15-20,47-48` | Nhãn nhóm `.tag` và chấm trạng thái chép 2–3 nơi | Sửa |
| 11 | Trung | audit Integrity (CSS chết) | `globals.css:182-185,192,203-209,309-329,421-431,444,451-452,459-462,466-472,478` | ~25 lớp không còn màn nào dùng: `.panel*`, `.table-wrap`, `table.cards` + `.strip-*`, `.chip*`, `.chips`, `.rowbtn*`, `.row-off`, `.tel`, `.secret`, `.groups-pick`, `.kv*`, `.kv.yn`, `.action-list`, `.staff-detail`, `.confirm`, `.account-head`, `.who-text/.who-meta`, `.screen-actions`, `td.wide`, `.hintbox` (đã grep TSX trước khi xoá) | Sửa |
| 12 | Trung | mobile-native §7 | `globals.css:49,57,82,104` | `viewport-fit=cover` nhưng khung/ngăn kéo không chừa `safe-area-inset-left/right` khi xoay ngang | Sửa |
| 13 | Thấp | mobile-native §1 | `globals.css` 15 chỗ, 2 CSS module | Hover chỉ gác `(hover:hover)`, chưa `and (pointer:fine)` | Sửa |
| 14 | Thấp | mobile-native §8 | `globals.css:13-14` | Nhấn giữ nút / mục menu bôi chọn chữ | Sửa |
| 15 | Thấp | mobile-native · WIG Touch | `globals.css:92` | Thân cột phải thiếu `safe-area-inset-bottom`, thiếu `overscroll-behavior: contain` | Sửa |
| 16 | Thấp | fixing-a11y | `Shell.tsx:227` | Nền mờ (scrim) là nút vào được bằng Tab | Sửa (`tabIndex=-1`) |
| 17 | Thấp | WIG Forms | `shared/ui/Toolbar.tsx:29` | Ô tìm thiếu `name` | Sửa |
| 18 | Thấp | detector `overused-font` | `app/layout.tsx:30` | Inter | **Dương tính giả**: Inter do brief ghim trong `DESIGN.md` (đủ dấu tiếng Việt); giữ |
| 19 | Thấp | WIG Navigation & State | `StaffScreen.tsx`, `RightRail.tsx` | Bộ lọc Nhân sự / tab cột phải không lên URL | Không sửa: đổi luồng/URL ngoài phạm vi "chỉ giao diện" |
| 20 | Thấp | WIG Locale | mã đơn/lô/tên đăng nhập | Chưa `translate="no"` | Không sửa (rải nhiều file, lợi ích nhỏ cho công cụ nội bộ) |
| 21 | Thấp | fixing-a11y (semantics) | `Shell.tsx:96-115` | Mục menu trái là chuỗi `<a>` dưới nhãn nhóm `div`, không phải `ul/li` | Không sửa (`nav` có tên, `aria-current` đúng; đổi markup đụng móc e2e `.nav a`) |

Đo máy TRƯỚC khi sửa (72 ảnh chụp): 360 px không có cuộn ngang, vùng bấm < 44 px, phần tử không tên hay ô nhập < 16 px ở bất kỳ màn
nào; 1280 px chỉ có vùng bấm 34–40 px đúng thiết kế chuột (`--tap: 40px` từ 768 px). Không `transition: all`; chuyển động chỉ
transform/opacity/màu phần tử nhỏ (fixing-motion-performance: không vi phạm); `prefers-reduced-motion` giữ đổi trạng thái.

### Điểm TRƯỚC / SAU

| Thang | Trước | Sau | Ghi chú |
|---|---|---|---|
| impeccable audit — Accessibility | 2 | 4 | #1, #2, #3, #6, #16 |
| — Performance | 4 | 4 | không đổi (không thêm chuyển động; khung chờ Nhân sự dùng `.sk` chung) |
| — Responsive | 3 | 4 | #5 (tab 360), #12, #13, #14, #15 |
| — Theming | 3 | 4 | #4 (màu trạng thái sai nghĩa), #9 (`--z-toast`), #10 |
| — Implementation Integrity | 3 | 4 | #7, #8, #11; detector chỉ còn dương tính giả Inter |
| **audit tổng** | **15/20 (Good)** | **20/20 (Excellent)** | |
| critique Nielsen (degraded, một ngữ cảnh) | 28/40 | 33/40 | H4 nhất quán 2→4, H5 phòng lỗi 3→4 (lỗi tại ô thay nút tắt), H1 trạng thái 3→4 (sổ kho có ngày, "Sắp có" rõ), H7 linh hoạt 2→3 (phím tab); H10 trợ giúp giữ 2 |
| Số phát hiện mức Cao / Trung / Thấp | 3 / 9 / 9 | **0 / 0 / 4** | 4 thấp còn lại: #18 dương tính giả, #19–#21 ghi lý do không sửa |
| web-design-guidelines (file:dòng) | 11 | 3 | còn #19, #20, #21 |

### Đã sửa — trang / component
- **`shared/ui/useDrawerFocus.ts` (mới)** + `Shell.tsx`: ngăn kéo menu (< 768) và cột phải (< 1024) mở → focus vào mục đang chọn / tab đang chọn (thử ở khung hình kế tiếp vì ngăn kéo vừa đổi `visibility`), giữ Tab/Shift+Tab trong ngăn kéo, đóng (Esc, nền, nút) → focus về đúng nút đã mở. Thêm nút **"Đóng menu"** trong ngăn kéo menu (chỉ điện thoại). Nền mờ `tabIndex=-1`.
- **Nút gửi không tắt vì thiếu ô** (`LoginScreen`, `ChangePasswordForm` — dùng cho cả S46 và S48 —, đặt lại mật khẩu ở `StaffDetail` qua prop mới `missing` của `features/staff/components/PasswordField`): bấm khi còn ô trống → câu lỗi ngay dưới ô (`aria-invalid`, `aria-describedby`, nói cách sửa: "Nhập tên tài khoản của bạn.", "Nhập mật khẩu hiện tại."…), focus vào ô đó, không gọi API; gõ lại thì lỗi tắt. Nút chỉ tắt khi đang gửi (+ `aria-busy`). Câu mới ở `shared/lib/messages.ts` (`needUsername`, `needPassword`, `needOldPassword`, `needNewPassword`, `needAgainPassword`, `needField`, `needFieldAgain`). Hành vi "Hai mật khẩu không khớp → không gọi API" (S48-AC3) giữ nguyên.
- **Bảng dạng hàng** (Tổng quan ×2, Đơn, Kho & lô): mỗi ô có `data-label` = tên cột; trong container query < 640 px CSS đọc thành nhãn **ẩn** (`::before` 1 px, `clip-path`) — cây truy cập Chromium đọc `row "Mã đơn: DH-240924-010 Khách: Khách lẻ Giá trị: 546.000 ₫ Trạng thái: Giữ chỗ"`, vẫn giữ vai trò row/cell; `textContent` ô không đổi (e2e so ô với bản cũ vẫn khớp).
- **Cột phải** (`RightRail.tsx`): tab chỉ chữ, `white-space:nowrap` (360 px không còn xuống dòng); phím ← → Home End + roving tabindex; tablist có tên. Tab **Trợ lý** chưa nối → khung "sắp có": ô icon, tiêu đề "Trợ lý vận hành" + nhãn **Sắp có** (`accent-soft`), câu cũ giữ nguyên (e2e bám), "Ví dụ câu bạn sẽ hỏi được:" + 2 câu chữ trơn (không khung để khỏi trông như nút). Thân cột có safe-area đáy + `overscroll-behavior: contain`. Ô icon trạng thái trong cột phải dùng `surface-3` (nền cột = `surface-2`, không thì mất ô).
- **Tab Hoạt động** (`features/inventory/components/ActivityFeed.tsx`) làm lại theo DESIGN.md: nhóm theo ngày ("Hôm nay", "Hôm qua", dd/mm, theo giờ máy); mỗi dòng icon tròn **trung tính** theo loại (`RECEIPT` hộp, `SALE` túi, `RETURN_RESTOCK`, `CANCEL_RESTORE`, `RECONCILE`, `WRITE_OFF`); chỉ "hạch toán lỗ / huỷ" tô hổ phách; dòng 1 = loại + số kg có dấu tabular căn phải, dòng 2 = mã lô mono `ink-3` + giờ. Giữ `ol.feed > li.fev` với `p` (chữ theo thứ tự mã lô · loại · số kg) + `time` như e2e so bản cũ; rỗng/không quyền dùng kiểu trạng thái chung (câu "Bạn không có quyền xem sổ kho." giữ nguyên).
- **Một kiểu rỗng/lỗi/403**: ô icon 40 px `surface-2`, tiêu đề 15/600, một câu 13 `ink-2`, một hành động — áp cho `.empty` (ViewGuard 403, Placeholder), `.state` trong bảng, rỗng Nhân sự (chuyển sang `.state` chung), cột phải. `ErrorBox`: câu lỗi thành tiêu đề (`p.state-title`) thay `span` trơn.
- **Nhân sự** (`StaffScreen.tsx`, `staff.module.css`): danh sách phẳng như các bảng — `section.sect` + `.sect-h` "Nhân viên · 9 người · đang làm", hàng ngăn đường mảnh, tràn 12 px hai bên, không khung; khung chờ dùng vạch `.sk` chung. Nhãn nhóm và chấm trạng thái (`parts.tsx` `GroupTags`/`StatusLine`, `AccountScreen` `YesNo`) dùng `.tags/.tag` và `.status good|mute` chung ở `globals.css`; xoá bản chép trong 2 CSS module. Giữ mọi móc e2e (`ul.staff-list > li`, `.staff-open`, `.group-tag`, `section[aria-busy]`).
- **Dùng chung**: `SideSheet.tsx`, `Toast.tsx`, `overlay.module.css` chuyển `features/auth/components/` → **`shared/ui/`** (import ở Nhân sự, Tài khoản đổi theo); token mới **`--z-toast: 50`** (`tokens.css`, trên ngăn kéo 40/41, dưới hộp thoại 60) cho Toast. README console/auth/staff cập nhật.
- **CSS chết** xoá khỏi `globals.css` (bảng #11; grep từng lớp trong TSX trước khi xoá). `globals.css` 530 → ~490 dòng.
- **mobile-native (360)**: `.app` chừa safe-area trái/phải khi xoay ngang, ngăn kéo trái/phải chừa cạnh tương ứng; hover gác `(hover:hover) and (pointer:fine)` ở globals + 2 CSS module; `user-select:none` chỉ trên nút / mục menu / tab; `100dvh`, ô nhập 16 px trên cảm ứng, vùng bấm 44 px — đo lại 360 px: không cuộn ngang, không vùng bấm nhỏ, không ô nhập < 16 px.
- **Chuyển động** (`emil-design-eng`, `fixing-motion-performance`): không thêm animation; không `transition: all`; mọi chuyển động vẫn chỉ transform/opacity/màu phần tử nhỏ; ngăn kéo/tấm vẫn 240/180 ms `--ease-drawer`/`--ease-out`; giảm chuyển động giữ đổi trạng thái.
- `Toolbar`: ô tìm có `name="q"`. **`DESIGN.md`**: z-index thêm toast; mục Chips → **Tag**; Section áp cho mọi màn danh sách (ngoại lệ trang cài đặt); bảng dạng hàng có nhãn cột ẩn; cột phải (tab chữ, phím, "Sắp có"), ngăn kéo (focus), mục mới **Sổ kho**; một kiểu rỗng/lỗi/403; nút gửi không tắt vì thiếu ô; hover `pointer:fine`; safe-area trái/phải.

### Kiểm chứng
- `tsc --noEmit` sạch; `npm run build` **thật** (không mock) sạch trong repo; `out/` không chứa `__caveMock|demo1234|Chế độ mock` (0 file).
- `grep -rnE '#[0-9a-fA-F]{3,8}\b|rgba?\(' app features shared` ngoài `tokens.css` = **0**; `style={{` = **0**.
- `impeccable detect --json` (app, features, shared): trước 1, sau 1 — cùng một dương tính giả `overused-font` (Inter, ghim trong DESIGN.md).
- E2E mock (bản build mock trong scratchpad `ui5/mocksrc`, `http.server` 3121): `s7_shell` **25/25** · `s8_views` **46/46** · `s41_s47_staff` **72/72** · `s48_password` **41/41**. Không sửa kịch bản e2e nào.
- E2E **backend thật**: Django `runserver` 127.0.0.1:8017 trên SQLite tạm `scratchpad/ui5/realbe.sqlite3` (`migrate` → `bootstrap_masterdata` → seed 5 tài khoản), console build thật `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8017` ở `scratchpad/ui5/realsrc` phục vụ 3108: `s41_s47_real` **39/39**. `backend/db.sqlite3` không đụng (mtime vẫn 13/09).
- Kiểm hành vi a11y mới (`scratchpad/ui5/a11y.py`, 360 px, mock): **19/19** — nút Đăng nhập bật khi trống, lỗi tại ô + focus (tài khoản, mật khẩu), lỗi tắt khi gõ; nhãn cột ẩn "Mã đơn: " (`::before` 1 px, textContent không đổi); menu mở → focus mục đang chọn, 25 lần Tab không ra khỏi ngăn kéo, Shift+Tab ở trong, Esc/nút "Đóng menu" → focus về ☰; cột phải mở → focus tab đang chọn, → và End chuyển tab, chỉ 1 tab trong thứ tự Tab, Esc → focus về nút mở; Đổi mật khẩu và Đặt lại mật khẩu: nút bật, lỗi tại ô + focus.
- Server có giới hạn thời gian (`perl alarm`, máy không có `timeout`), đã kill theo PID; `lsof` 3121/3108/8017 sạch.

### Ảnh (`shots/ui/`)
`ui5-before-*` (chụp trước khi sửa) và `ui5-after-*` cho mọi màn × 360 + 1280 × sáng + tối: `login`, `set-password`, `no-role`,
`overview`, `shell-menu` (chỉ 360), `rail-notes` (chỉ 360, ngăn kéo), `rail-ai`, `rail-feed`, `orders`, `inventory`, `staff`, `staff-detail`,
`staff-confirm`, `staff-create`, `account`, `stateempty`, `statefail`, `stateloading` (khung chờ), `state403` (giao1 mở Kho & lô),
và `notfound` (chỉ `after`: trang 404 của bản build; lần chụp `before` trỏ nhầm trang 404 của `http.server` nên đã bỏ).
72 ảnh `before` + 76 ảnh `after`.

### Lệch contract / cần BE, PO biết
- Không lệch contract, không đổi request nào.
- Dòng "Hôm nay/Hôm qua" ở sổ kho tính theo giờ máy người dùng từ `at` (ISO) BE trả — cùng cách `timeHM` đang làm.

### Còn nợ
- #19 (bộ lọc/tab lên URL), #20 (`translate="no"` cho mã), #21 (menu trái thành `ul/li`) — mức thấp, ghi lý do ở bảng trên.
- Critique chạy một ngữ cảnh (không tách 2 subagent như playbook impeccable) — nếu cần chấm độc lập, chạy lại ở phiên có công cụ subagent.
- Chưa kiểm trên máy thật (mobile-native: safe-area khi xoay ngang, kẹt hover, nhấn giữ) — đã kiểm bằng giả lập Chromium 360 px cảm ứng.
- Nút "Thêm nhân viên" chưa có trong trạng thái rỗng "Chưa có nhân viên nào đang làm" (câu hướng dẫn chỉ tới nút trên đầu màn); thêm nút thứ hai trùng tên sẽ phá `get_by_role` của e2e.
- `PRODUCT.md` mục **(suy luận)** vẫn chờ Duy xác nhận (nợ từ UI1).
- Chưa commit, chưa deploy.

## Sửa lỗi Low sau QA lần 5 (điều phối viên, 2026-09-25)
- **B10:** dark `--accent-hover` đổi `#3D7CE6` → `#285FC4` (chữ trắng 5.96:1, đạt AA) ở `erp-console/shared/ui/tokens.css` (2 chỗ) và `DESIGN.md`.
- **B11:** `features/overview/components/OverviewScreen.tsx`: nhãn "Cần chú ý" đếm theo `kpis.near_expiry`, không theo `alerts.length` (BE giới hạn 6 dòng).
- Kiểm: `tsc` sạch; e2e `s8_views` (mock) 46/46; build thật không chứa mock.

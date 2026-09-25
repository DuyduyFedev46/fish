# Cá Về — Backend (Django core)

Lõi hệ thống mua – bán – quản lý kho cho vựa cá. **Django làm 100% lõi** (ORM,
migration, Admin, API DRF). FastAPI (`../adapter/`) chỉ là adapter mỏng nhận webhook bên thứ 3.

Tài liệu nguồn: `../doc/` — `URD.md` (yêu cầu), `business-process-spec.md`
(quy trình P-01…P-10 + business rule `BR-*`), `decisions.md` (quyết định đã chốt).

## Chạy dev

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # BẮT BUỘC: DJANGO_DEBUG=1 cho dev (DEBUG mặc định tắt, thiếu SECRET_KEY sẽ dừng); để trống DATABASE_URL = dùng SQLite
python manage.py migrate        # tạo bảng + seed 4 Group phân quyền (migration accounts.0002)
python manage.py bootstrap_masterdata   # tạo Kho chính + bảng giá Bán lẻ
python manage.py createsuperuser
python manage.py runserver      # /admin/ và /api/
```

Chạy test: `python manage.py test` (291 test, ~10 giây). Một module:
`python manage.py test apps.sales.orders`. Sản phẩm dùng **PostgreSQL** (`DATABASE_URL=postgres://…`).

## Cấu trúc thư mục — chia theo MODULE TÍNH NĂNG

```
backend/
  config/                  cấu hình Django (không chứa nghiệp vụ) — xem bảng "File cấu hình" bên dưới
  apps/<miền>/             1 app Django = 1 miền nghiệp vụ; mỗi app có README.md riêng
    models/                bảng dữ liệu, tách file theo tính năng (__init__.py gom lại cho Django)
    <tính_năng>/           services.py (nghiệp vụ) · api.py (endpoint) · serializers.py (JSON) · tests/ · README.md
    management/commands/   lệnh chạy tay/cron (Django bắt buộc để ở đây) — chỉ gọi services của module
    migrations/ admin.py apps.py
```

Quy tắc: nghiệp vụ chỉ nằm trong `services.py`; `api.py` chỉ nhận input → kiểm quyền → gọi service → trả JSON.
Module gọi module khác **qua services** của module đó. Route tập trung ở `config/api_urls.py`.

### Sơ đồ module

| Miền (app) | Module | Quy trình | Endpoint chính (`/api/…`) |
|---|---|---|---|
| `catalog` | `items/` | P-01 | `catalog/items/`, `catalog/item-groups/`, `catalog/bundle-lines/`; Shop `shop/catalog/` |
| | `pricing/` | P-01 | `catalog/price-lists/`, `catalog/item-prices/`, `catalog/pricing-rules/` |
| `purchasing` | `receipts/` | P-02 | `purchasing/suppliers/`, `purchasing/receipts/` (+ `submit`) |
| | `invoices/` | P-02 | `purchasing/invoices/` |
| | `costs/` | P-03 | `purchasing/costs/` |
| `inventory` | `batches/` | P-04 | `inventory/batches/` (+ `publish`, `close`) |
| | `stock/` | nền P-04…P-09 | `inventory/warehouses/`, `inventory/ledger/`, `inventory/stock-entries/` |
| | `stocktake/` | P-09 | `inventory/reconciliations/` (+ `approve`) |
| | `returns/` | P-08 | `inventory/returns/` (+ `approve`) |
| `sales` | `orders/` | P-05, P-07 (huỷ đơn) | Shop `shop/orders/`; `sales/orders/` (+ `cancel`) |
| | `payments/` | P-05 | `internal/payments/sepay-webhook/`; `sales/invoices/` (+ `confirm-payment`), `sales/payments/` |
| | `refunds/` | P-07 | `sales/refunds/` (+ `create`, `confirm`) |
| | `customers/` | P-05 (7.1) | `sales/customers/` |
| `delivery` | (phẳng) | P-06, P-08 | `delivery/notes/` (+ `status`) |
| `reports` | (phẳng) | P-10 | `reports/batch/{batch_id}/`, `reports/period/`, `dashboard/summary/` |
| `accounts` | `auth/`, `staff/` | §1 Phân quyền | `auth/token/`, `auth/me/`, `auth/logout/`, `auth/change-password/`; `staff/` (+ `groups`, `deactivate`, `reactivate`, `reset-password`) |
| `common` | (phẳng) | dùng chung | — (phân quyền, ẩn giá vốn, `BusinessError`, AuditLog) |

### File cấu hình — mỗi file làm gì

| File | Giải thích dễ hiểu |
|---|---|
| `manage.py` | Cửa vào để gõ lệnh quản trị: chạy server, chạy test, tạo bảng (`migrate`), chạy job tay. |
| `config/settings.py` | "Bảng công tắc" của cả hệ thống: kết nối DB, danh sách app, bảo mật, ngưỡng nghiệp vụ (TTL, cận hạn…) đọc từ `.env`. |
| `config/urls.py` | Chia đường dẫn gốc: `/admin/` (trang quản trị), `/api/` (dữ liệu cho web/app). |
| `config/api_urls.py` | Danh bạ API: mỗi đường dẫn `/api/...` trỏ tới màn xử lý nào trong module nào. |
| `config/celery.py` | Bật "người làm việc nền" Celery để chạy job định kỳ (vd tự huỷ đơn quá hạn giữ chỗ mỗi phút). |
| `config/asgi.py`, `config/wsgi.py` | Chỗ máy chủ web (gunicorn trên Cloud Run) cắm vào để chạy ứng dụng; gần như không bao giờ sửa. |
| `Dockerfile` | Công thức đóng gói backend thành 1 "hộp" chạy được trên Cloud Run (cài thư viện, gom file tĩnh, chạy gunicorn). |
| `.dockerignore` | Danh sách thứ KHÔNG bỏ vào hộp khi đóng gói (môi trường ảo, DB thử, file `.env` bí mật, tài liệu). |
| `requirements.txt` | Danh sách thư viện Python cần cài (Django, DRF, Postgres, Celery…) kèm phiên bản. |
| `.env.example` | Mẫu các biến cấu hình (mật khẩu, DB, ngưỡng nghiệp vụ); sao thành `.env` rồi điền giá trị thật — không commit `.env`. |

## Phân quyền 3 tầng (§1)

- **Tầng 1 — CRUD/model**: `auth.Permission` + 4 Group `chu` / `quan_ly` / `nv_kho`
  / `nv_giao` (cộng dồn). Gán trong data migration `accounts/migrations/0002`.
- **Tầng 2 — hành động tuỳ biến** (`Meta.permissions`): `publish_batch`,
  `close_batch`, `approve_stockreconciliation`, `approve_returntostock`,
  `cancel_paid_order`, `create_refund`, `confirm_refund`,
  `confirm_payment_manual`, `view_costprice`, `view_profitreport`,
  `manage_staff`, `view_dashboard` (+ builtin `add_purchasecost`).
- **Tầng 3 — phạm vi dòng & cột**: serializer ẩn giá vốn (`CostFieldSerializerMixin`,
  `apps/common/api.py`) + `get_queryset` lọc dòng (nv_giao chỉ thấy phiếu/đơn/khách của mình).
  Test rò giá vốn: `apps/inventory/batches/tests/test_api.py`.

Ranh giới Chủ ↔ Quản lý: Quản lý được uỷ *mọi thứ làm khách phải chờ*; Chủ giữ
*mọi thứ làm tiền rời túi hoặc đổi con số lời lỗ*.

## Bất biến đã cài ở tầng model

- `SalesOrder`/`SalesInvoice`: `default_permissions=("view","change")` → **không ai
  tạo tay được** (BR-PQ-11), chỉ Hệ thống tạo.
- Chứng từ **không xoá** — `delete_*` gần như không cấp; huỷ bằng trạng thái (BR-PQ-10).
  **Ngoại lệ duy nhất (D1):** `manage.py seed_demo --remove` được xoá bản ghi **demo** — chỉ
  bản ghi có trong sổ `accounts.DemoRecord` (do chính `seed_demo` ghi khi tạo). Không bao giờ
  xoá dữ liệu thật, không xoá lan (CASCADE) sang dữ liệu thật; bản ghi demo đang được dữ liệu
  thật dùng thì giữ lại và báo ra. AuditLog không bao giờ bị gỡ. Chạy thử: `--remove --dry-run`.
  DB đã seed bằng bản cũ (chưa có sổ): thêm `--adopt-legacy` (nhận theo chữ ký mã + tên/SĐT).
- FK người dùng trỏ `User` với `on_delete=PROTECT` (BR-PQ-02).
- `AuditLog`, `StockLedgerEntry`, `*LineBatch`: `default_permissions=("view",)` — append-only.
- Field nhạy cảm (`Batch.purchase_rate`, `Batch.landed_unit_cost`,
  `PurchaseReceiptLine.rate`, `*LineBatch.unit_cost`): chỉ `view_costprice`.

## Tham số cấu hình (không hard-code) — `.env` / `settings.py`

`BATCH_DEFAULT_SHELF_LIFE_DAYS` (90), `BATCH_NEAR_EXPIRY_DAYS` (14),
`SALES_ORDER_TTL_MINUTES` (30), `DELIVERY_MAX_FAILED_ATTEMPTS` (2),
`COLD_CHAIN_MAX_HOURS` (6 — câu hỏi mở #3, cần Lộc cho số thật),
`TTL_JOB_HEALTH_GRACE_MINUTES` (5), `INTERNAL_SERVICE_TOKEN` (adapter → Django).

Riêng khi chạy `manage.py test`, `settings.py` đổi băm mật khẩu sang MD5 cho nhanh
(chỉ nhánh test; production vẫn PBKDF2).

## Job nền

- Huỷ đơn quá TTL (BR-BH-03/04): Celery task `apps.sales.tasks.cancel_expired_orders`
  (code ở `apps/sales/orders/tasks.py`) chạy mỗi phút; fallback cron `manage.py cancel_expired_orders`;
  giám sát `manage.py check_ttl_job_health` (exit 1 = nghi job chết).
- Trạng thái lô theo hạn (BR-LO-01/02/06): `manage.py update_batch_status` (đề xuất 00:05 giờ VN).

```bash
celery -A config worker -l info          # worker (cần Redis)
celery -A config beat -l info            # scheduler
```
Không có broker: `CELERY_TASK_ALWAYS_EAGER=1`.

## Còn lại (hạ tầng/nghiệp vụ)

- Sinh mã VietQR SePay thật (hiện stub `_vietqr_stub` ở `apps/sales/orders/shop_api.py`).
- Trả lời câu hỏi mở nghiệp vụ trong `../doc/` (ngưỡng chuỗi lạnh, combo thực tế…).

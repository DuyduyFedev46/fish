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

Chạy test: `python manage.py test` (536 test, ~30 giây). Một module:
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
| `sales` | `orders/` | P-05, P-07 (huỷ đơn) | Shop `shop/orders/`; `sales/orders/` (lọc/tìm/chi tiết + `cancel`, `confirm-payment`) |
| | `payments/` | P-05 | `internal/payments/sepay-webhook/` (cũ), `internal/payments/sepay-ipn/` (P3, Cổng SePay); Shop `shop/orders/{code}/checkout/` (P1); `sales/invoices/` (chỉ đọc), `sales/payments/`; service xác nhận tay cho `sales/orders/{id}/confirm-payment` |
| | `refunds/` | P-07 | `sales/refunds/` (+ `create`, `confirm`) |
| | `customers/` | P-05 (7.1) | `sales/customers/` |
| `delivery` | (phẳng) + `confirmation/` (gọi xác nhận đơn, CSKH) | P-06, P-08 | `delivery/notes/` (+ `status`), `confirmation/queue/`, `confirmation/search/` (alias cũ `cskh/queue/`, `cskh/search/` đã gỡ ở Lô 5, trả 404) |
| `reports` | (phẳng) | P-10 | `reports/batch/{batch_id}/`, `reports/period/`, `dashboard/summary/` |
| `accounts` | `auth/`, `staff/`, `capabilities/`, `audit/` | §1 Phân quyền | `auth/token/`, `auth/me/`, `auth/logout/`, `auth/change-password/`; `staff/` (+ `groups`, `deactivate`, `reactivate`, `reset-password`); `staff/groups/` + `staff/groups/{code}/` + `staff/groups/{code}/capabilities/` (ma trận phân quyền, chỉ Chủ ghi); `audit-logs/?actor=` |
| `content` | `categories/`, `entries/`, `images/`, `body/`, `public/` | P-11 | `content/categories/`, `content/entries/`; công khai `public/content/` |
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

- **Tầng 1 — CRUD/model**: `auth.Permission` + 4 Group `owner` / `manager` / `warehouse_staff`
  / `delivery_staff` (cộng dồn). Gán trong data migration `accounts/migrations/0002`.
- **Tầng 2 — hành động tuỳ biến** (`Meta.permissions`): `publish_batch`,
  `close_batch`, `approve_stockreconciliation`, `approve_returntostock`,
  `cancel_paid_order`, `create_refund`, `confirm_refund`,
  `confirm_payment_manual`, `view_costprice`, `view_profitreport`,
  `manage_staff`, `view_dashboard` (+ builtin `add_purchasecost`).
- **Tầng 3 — phạm vi dòng & cột**: serializer ẩn giá vốn (`CostFieldSerializerMixin`,
  `apps/common/api.py`) + `get_queryset` lọc dòng (delivery_staff chỉ thấy phiếu/đơn/khách của mình).
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

## Dữ liệu giả cho e2e — `manage.py seed_qa`

Bộ dữ liệu giả CỐ ĐỊNH, TẤT ĐỊNH để các e2e chạy trên backend thật khỏi cứng mã/id của phiên QA cũ.
Lệnh **riêng**, không phải `seed_demo --qa`: `seed_demo` được phép chạy trên production và có sổ `DemoRecord`
(`seed_demo --remove` gỡ theo sổ), trộn QA vào đó sẽ đưa dữ liệu giả vào luồng production và làm `--remove` kéo
theo dữ liệu QA. Code ở `apps/accounts/qa_fixture/` (`build.py` dữ liệu, `reset.py`, `guard.py` cổng chặn).

```bash
cd backend
export DJANGO_DEBUG=1 DATABASE_URL=sqlite:////tmp/e2e.sqlite3     # DB tạm, KHÔNG dùng DB thật
.venv/bin/python manage.py migrate && .venv/bin/python manage.py bootstrap_masterdata
QA_PASSWORD='mật-khẩu-tự-chọn' .venv/bin/python manage.py seed_qa  # dựng (idempotent) + in bảng mã → id
.venv/bin/python manage.py seed_qa --reset                         # xoá đúng bản ghi QA
```

- **Bảng mã → id** in ra màn hình và ghi `/tmp/seed_qa_ids.json` (đổi bằng `--manifest`): khoá `users`, `customers`,
  `items`, `batches`, `orders`, `invoices`, `delivery_notes`, `payments`, `refunds`, `returns`, `receipts`,
  `stocktakes`, `call_scripts`. Kịch bản e2e đọc tệp này thay vì cứng id.
- **Không commit** tệp bảng mã (`/tmp/seed_qa_ids.json`) và đừng đặt `--manifest` vào trong repo: tuy chỉ chứa id, mã và SĐT giả, nó là đầu ra của một lần chạy.
- **Mật khẩu** các tài khoản `qa_…` lấy từ env `QA_PASSWORD` (bắt buộc, không mặc định, không in ra).
- **Tài khoản:** `qa_owner`, `qa_manager`, `qa_warehouse`, `qa_courier1`, `qa_courier2`, `qa_cs1`, `qa_cs2`,
  tổ hợp `qa_warehouse_courier` (K+G), `qa_warehouse_cs` (K+C), `qa_nogroup` (không nhóm), `qa_superuser`.
- **Đơn** `QA-SO-01…17` đủ trạng thái (giữ chỗ, tự huỷ, đã thanh toán, đang xử lý, hoàn tất, huỷ có `cancel_note`,
  hoàn tất sau chuyển bù, chuyển thiếu); **phiếu giao** `QA-GH-nn` đủ trạng thái (gồm FAILED giao2 và CANCELLED giao1/giao2);
  phiếu hoàn tiền PENDING/REFUNDED/FAILED; hàng hoàn Nháp/Đã duyệt/Đã huỷ; phiếu nhập Nháp/Ghi nhận/Huỷ;
  kiểm kê Nháp + Chờ duyệt; lô `QA-LO-01…08` (đang bán, cận hạn, quá hạn 6,5 kg, nháp, đã chốt, hết hàng, đã huỷ);
  khoản tiền về ORPHAN/UNMATCHED/OVERPAID/MANUAL có nhãn nghi trùng; kịch bản gọi; Nhật ký đủ người/hệ thống/AI.
- **Dữ liệu cá nhân hoàn toàn giả:** SĐT `09000000nn`, tên "Khách QA Giả nn", địa chỉ "QA-Địa chỉ giả…".
- **Cổng chặn:** `SEPAY_ENV=PRODUCTION` luôn bị từ chối. Chỉ chạy khi `DJANGO_DEBUG=1` VÀ (SQLite hoặc tên DB/host có `staging`). DB giống production
  (PostgreSQL tên `postgres`, hoặc tên/host có `prod` không có `staging`) bị từ chối, **không cờ nào mở được**.
  `--allow-non-local` chỉ nới điều kiện DEBUG/loại DB (vd Postgres dev trên máy).
- **Idempotent:** chạy lại không nhân đôi. `--reset` chỉ xoá đối tượng mang mã `QA-`, đúng 20 khách giả (đủ SĐT và tên "Khách QA Giả") và Nhật ký gắn với đối tượng QA; không xoá theo người làm. Tài khoản `qa_…` còn bị dữ liệu ngoài QA tham chiếu thì giữ lại, vô hiệu hoá (`is_active=False`) và báo trong `kept`. Ngoại lệ có chủ đích của BR-PQ-10/06, chỉ cho dữ liệu QA.
- Hạn giữ chỗ của `QA-SO-01/02/13` tính từ lúc seed (25, 3, 20 phút): đừng chạy `cancel_expired_orders` giữa chừng.

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

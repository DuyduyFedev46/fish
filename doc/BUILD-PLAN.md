# Build Plan — Cảng cá Lộc (Phase 2 → 6)

Tài liệu điều phối. Là **hợp đồng (contract)** để nhiều subagent build song song mà
không đụng nhau. Nguồn nghiệp vụ: `URD.md`, `business-process-spec.md`, `decisions.md`.
Nền đã có: `backend/` (Phase 1 — data model, đã migrate + check sạch).

## Nguyên tắc điều phối

1. **File-disjoint**: mỗi agent SỞ HỮU một tập file rời nhau. Không agent nào sửa
   file của agent khác. Model (`*/models.py`) và migration đã đóng băng ở Phase 1 —
   agent KHÔNG sửa model trừ khi task nói rõ (nếu cần field mới → báo, không tự thêm).
2. **Substrate trước**: `apps/common/` + inventory service primitives do điều phối
   viên viết trước, mọi agent import từ đó.
3. **Contract đóng băng**: chữ ký hàm service và endpoint API dưới đây là chuẩn.
   Agent code đúng chữ ký này; lệch phải báo, không tự đổi.
4. **Test bắt buộc**: mỗi agent giao kèm test (`pytest`/Django `TestCase`) cho phần mình.

## Sóng thực thi (waves)

| Wave | Việc | Ai | Phụ thuộc |
|---|---|---|---|
| 0 | `apps/common/` + inventory primitives + inventory ops | điều phối | Phase 1 |
| 1a | sales services (đặt/giữ chỗ/TTL/hoá đơn/hoàn tiền) | Agent A | Wave 0 |
| 1b | purchasing services (nhập lô/landed cost) | Agent B | Wave 0 |
| 1c | delivery + reports services | Agent C | Wave 0 |
| 1d | Next.js frontend (Landing + Shop) | Agent FE | chỉ contract API |
| 1e | FastAPI adapter (webhook SePay) | Agent ADP | chỉ contract nội bộ |
| 2 | DRF API toàn bộ app (serializer tách Group + scope dòng) | Agent API | Wave 1a–c |
| 3 | Celery + beat + job huỷ TTL + giám sát | Agent CELERY | Wave 1a |
| 4 | Tích hợp, chạy full test, vá seam | điều phối | tất cả |

---

## Bản đồ sở hữu file

| Agent | Sở hữu (được tạo/sửa) | Chỉ đọc |
|---|---|---|
| Wave 0 | `apps/common/*`, `apps/inventory/services.py`, `apps/inventory/tests/*` | models |
| A (sales) | `apps/sales/services.py`, `apps/sales/tests/*` | inventory/common services |
| B (purchasing) | `apps/purchasing/services.py`, `apps/purchasing/tests/*` | inventory/common services |
| C (deliv/report) | `apps/delivery/services.py`, `apps/reports/services.py`, tests 2 app | sales/inventory services |
| API | `apps/*/serializers.py`, `apps/*/api.py`, `config/api_urls.py`, `apps/*/tests/test_api.py` | services |
| FE | `frontend/**` | contract |
| ADP | `adapter/**` | contract |
| CELERY | `config/celery.py`, `apps/sales/tasks.py`, `apps/*/monitoring.py`, sửa `config/settings.py` (chỉ khối CELERY) | sales services |

---

## Contract A — Service layer (Python)

Tất cả service là **hàm thuần trong transaction**, ghi `AuditLog` cho hành động Tầng 2,
ghi `StockLedgerEntry` cho mọi biến động kho. Lỗi nghiệp vụ → raise `BusinessError`
(từ `apps.common.exceptions`). Actor truyền vào là `User` hoặc `None` (= Hệ thống).

### `apps/common/` (Wave 0)
```python
# exceptions.py
class BusinessError(Exception): ...            # lỗi vi phạm business rule

# audit.py
def record_audit(action, *, actor=None, obj=None, changes=None, note=""): ...
    # ghi 1 dòng AuditLog (append-only). obj -> model_name/object_id/object_repr.

# actors.py
SYSTEM = None   # quy ước actor=None nghĩa là Hệ thống (BR-PQ-07)
```

### `apps/inventory/services.py` (Wave 0)
```python
def create_batch(*, item, supplier, warehouse, received_date, qty, purchase_rate,
                 shelf_life_days=None, actor=None) -> Batch: ...
    # sinh batch_id, tính expiry_date, landed_unit_cost khởi tạo = purchase_rate,
    # status=DRAFT, ghi StockLedgerEntry RECEIPT (+qty), set qty_available=qty.

def record_movement(*, batch, qty_change, movement_type, reference="", actor=None): ...
    # append StockLedgerEntry + cập nhật batch.qty_available (không âm).

def allocate_fifo(*, item, qty) -> list[tuple[Batch, Decimal]]: ...
    # trả list (batch, kg) theo FIFO ngày nhập, chỉ lô SELLING/NEAR_EXPIRY còn
    # sellable (qty_available - qty_reserved). Raise BusinessError nếu không đủ.

def reserve(*, batch, qty): ...     # tăng qty_reserved (giữ chỗ)
def release(*, batch, qty): ...     # giảm qty_reserved (nhả)

def publish_batch(*, batch, actor): ...   # DRAFT->SELLING, cần perm publish_batch (kiểm ở API)
def close_batch(*, batch, actor): ...     # ->CLOSED, kiểm BR-LO-04, ghi audit close_batch
def recompute_landed_cost(*, batch, actor=None): ...  # (giá mua + Σ phân bổ)/qty_received; audit BR-GV-03

def apply_reconciliation(*, reconciliation, approver): ...  # duyệt kiểm kê -> điều chỉnh tồn (BR-KK)
def apply_return(*, return_to_stock, approver): ...         # RESTOCK cộng lô gốc / WRITE_OFF hạch toán lỗ
```

### `apps/sales/services.py` (Agent A)
```python
def create_order(*, customer_phone, customer_name, delivery_address, phone,
                 lines: list[dict]) -> SalesOrder: ...
    # lines item: {"item_code": str, "qty": Decimal}. Hệ thống tạo (BR-PQ-11).
    # - gộp/khởi tạo Customer theo phone (7.1)
    # - lấy giá ItemPrice hiệu lực (BR-DM-02); áp 1 PricingRule lợi nhất (BR-DM-08)
    # - BUNDLE: nổ BundleLine, giữ chỗ ĐỒNG THỜI mọi thành phần (BR-BH-07), snapshot công thức
    # - allocate_fifo + reserve mỗi thành phần; tạo SalesOrderLine + SalesOrderLineBatch
    # - status=BOOKED, booked_expires_at = now + SALES_ORDER_TTL_MINUTES
    # - không đủ tồn -> BusinessError (BR-BH-02)

def confirm_payment(*, order, bank_txn_id, amount, received_at, source="WEBHOOK",
                    raw_payload=None, actor=None) -> PaymentTransaction: ...
    # idempotent theo bank_txn_id (BR-TT-03). amount<total -> UNDERPAID chờ Chủ (BR-TT-04).
    # order đã huỷ -> ORPHAN chờ Chủ (BR-TT-05). Khớp đủ -> issue_invoice + status PAID/PROCESSING.

def issue_invoice(*, order, txn_ref, issued_at) -> SalesInvoice: ...
    # chuyển reservation->tồn thật: release + record_movement SALE(-qty) mỗi lô;
    # tạo SalesInvoice + SalesInvoiceLine + SalesInvoiceLineBatch (unit_cost=ảnh chụp landed_unit_cost).
    # Ghi doanh thu tại issued_at (BR-TT-06). Đây là NGUỒN báo cáo giá vốn (BR-BH-06).

def cancel_unpaid_expired(*, now=None) -> int: ...  # job TTL: BOOKED quá hạn -> AUTO_CANCELLED + release. Idempotent (BR-BH-04)
def cancel_paid_order(*, order, actor, reason=""): ...  # hoàn kho lô gốc + (gọi refund nếu cần). audit cancel_paid_order
def create_refund(*, invoice, amount, is_partial, reason, actor) -> Refund: ...  # PENDING. audit create_refund. BR-HT-04 không vượt đã thu
def confirm_refund(*, refund, bank_txn_ref, actor) -> Refund: ...  # ->REFUNDED, bắt buộc bank_txn_ref (BR-HT-03), đảo doanh thu (BR-HT-06). audit confirm_refund
```

### `apps/purchasing/services.py` (Agent B)
```python
def submit_receipt(*, receipt, actor) -> list[Batch]: ...
    # mỗi PurchaseReceiptLine -> inventory.create_batch (BR-MH-01), gán line.batch,
    # receipt.status=SUBMITTED. Cho sửa shelf_life xuống, không lên (BR-MH-02).

def record_purchase_cost(*, cost_type, amount, allocation_method, incurred_date,
                         allocations: list[dict], actor) -> PurchaseCost: ...
    # allocations: [{"batch_id": str, ...}] hoặc tự phân bổ theo kg/giá trị trên danh
    # sách lô. Tạo PurchaseCost + PurchaseCostAllocation, gọi inventory.recompute_landed_cost.
    # Chặn lô đã chốt (BR-GV-02). Cần perm add_purchasecost (kiểm ở API).
```

### `apps/delivery/services.py` (Agent C)
```python
def create_delivery_note(*, invoice) -> DeliveryNote: ...   # khi đơn PAID/PROCESSING, status=PREPARING
def advance_status(*, note, to_status, actor): ...          # theo state machine P-06 (BR-GH-05 hoàn tất là 1 chiều)
def mark_failed(*, note, actor): ...                        # failed_attempts++, >= DELIVERY_MAX_FAILED_ATTEMPTS -> nhắc (BR-GH-04)
def return_to_warehouse(*, note, batch, qty, actor) -> ReturnToStock: ...  # tạo phiếu hàng hoàn (chờ duyệt, BR-HV-02)
```

### `apps/reports/services.py` (Agent C)
```python
def batch_pnl(*, batch) -> dict: ...     # doanh thu từ lô − (giá mua + chi phí + hao hụt + hàng hỏng). Nguồn sự thật. Nhãn "tạm tính" nếu chưa chốt (BR-BC-05)
def period_pnl(*, year, month) -> dict: ...  # doanh thu ghi nhận − giá vốn ghi nhận − hoàn tiền trong kỳ (BR-BC-03)
```

---

## Contract B — HTTP API (DRF, Agent API)

Base `/api/`. Auth nội bộ (nhân viên/Chủ): SessionAuth. Shop (khách): công khai,
không đăng nhập (guest). Trả JSON. Lỗi nghiệp vụ → 400 `{"detail": "..."}`.

### Shop API (công khai — cho Next.js, Agent FE build theo đây)
```
GET  /api/shop/catalog/            -> [{item_code,name,group,item_type,unit:"Kg",price,sellable_qty}]
     # sellable_qty = tồn khả dụng (tồn sổ − giữ chỗ); BUNDLE tính min theo thành phần (BR-DM-06)
GET  /api/shop/catalog/{item_code}/ -> {..., bundle_components?:[{item_code,name,qty_per_bundle}]}
POST /api/shop/orders/             body {customer:{phone,name},delivery_address,phone,items:[{item_code,qty}]}
     -> 201 {order_code, total_amount, vietqr:{payload,amount,content}, booked_expires_at}
     # content chuyển khoản mang order_code (BR-TT-01)
GET  /api/shop/orders/{order_code}/?phone_last4=1234
     -> {order_code, status, status_label, lines:[...], delivery:{status}} | 404
     # tra cứu bằng mã đơn + 4 số cuối SĐT (7.1)
```
VietQR: Phase này trả payload tĩnh giả lập `{"payload":"<chuỗi>","amount":N,"content":"<order_code>"}`
(tích hợp SePay thật là việc của adapter/khoá SePay sau). FE hiển thị QR từ payload.

### API nội bộ (SessionAuth + phân quyền — back-office)
CRUD/list theo model qua ViewSet. Tầng 2 = action riêng; Tầng 3 = serializer tách + scope:
```
POST /api/inventory/batches/{id}/publish/         perm publish_batch
POST /api/inventory/batches/{id}/close/           perm close_batch
POST /api/inventory/reconciliations/{id}/approve/ perm approve_stockreconciliation
POST /api/inventory/returns/{id}/approve/         body {decision} perm approve_returntostock
POST /api/purchasing/receipts/{id}/submit/        (tạo lô)
POST /api/purchasing/costs/                        perm add_purchasecost
POST /api/sales/orders/{id}/cancel/               perm cancel_paid_order
POST /api/sales/invoices/{id}/confirm-payment/    perm confirm_payment_manual (E-05)
POST /api/sales/refunds/                           perm create_refund
POST /api/sales/refunds/{id}/confirm/             perm confirm_refund
POST /api/delivery/notes/{id}/status/             body {to_status}  (nv_giao chỉ phiếu của mình)
GET  /api/reports/batch/{batch_id}/               perm view_profitreport
GET  /api/reports/period/?year=&month=            perm view_profitreport
```
**Tầng 3 — CHỐNG RÒ RỈ GIÁ VỐN (spec 1.6, rủi ro số 1):** field nhạy cảm
(`landed_unit_cost`, `purchase_rate`, `rate` mua, `unit_cost` bán) CHỈ xuất hiện trong
serializer khi `request.user.has_perm('inventory.view_costprice')`. KHÔNG dùng
`fields='__all__'` chung. Test bắt buộc: gọi API bằng token `nv_kho`/`nv_giao` xác
nhận response KHÔNG chứa các field đó (BR-PQ-13). Scope dòng: `nv_giao` chỉ thấy
DeliveryNote/SalesOrder gán cho mình (`get_queryset`).

### API cho adapter (Agent ADP gọi vào — nội bộ, xác thực service token)
```
POST /api/internal/payments/sepay-webhook/   header X-Internal-Token: <INTERNAL_SERVICE_TOKEN>
     body {bank_txn_id, order_code, amount, received_at, raw:{...}}
     -> 200 {matched: bool, order_status}   # gọi sales.confirm_payment (idempotent)
```

---

## Contract C — FastAPI adapter (`adapter/`, Agent ADP)

Lớp mỏng, KHÔNG đụng DB. Nhận webhook SePay → validate/transform → POST vào
`/api/internal/payments/sepay-webhook/` của Django kèm `X-Internal-Token`.
```
POST /webhook/sepay   (payload SePay) -> map sang body nội bộ -> gọi Django -> trả 200
GET  /healthz
```
Cấu hình qua env: `DJANGO_INTERNAL_URL`, `INTERNAL_SERVICE_TOKEN`, `SEPAY_WEBHOOK_SECRET`.
Có test dùng `httpx`/`respx` mock Django. `adapter/requirements.txt` riêng.

## Contract D — Next.js frontend (`frontend/`, Agent FE)

Next.js (App Router) + TypeScript. Hai mặt tiền TÁCH BIỆT:
- **Landing** `/` — giới thiệu, SEO (metadata), không giao dịch, có nút dẫn sang Shop.
- **Shop** `/shop` — bảng giá (GET catalog), trang mặt hàng, giỏ hàng (client state),
  checkout (POST orders) → hiện VietQR + đếm ngược TTL, trang tra cứu đơn
  `/shop/orders` (mã đơn + 4 số cuối SĐT).
Gọi API qua biến env `NEXT_PUBLIC_API_BASE`. Không phí giao hàng (BR-BH-10).
Đọc contract Shop API ở trên. Có thể mock khi API chưa chạy. Đơn giản, sạch, responsive.

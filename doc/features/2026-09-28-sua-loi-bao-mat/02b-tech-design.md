# Thiết kế kỹ thuật — Sửa lỗi bảo mật có sẵn
> Claude (Tech Lead) · 2026-09-28 · Trạng thái: **ĐÃ DUYỆT (Duy 28/09)** · §7 S06 (L-10) thêm ngày 28/09, Duy duyệt
> Story: `02-stories.md` (S01–S05). Không model mới, **không migration**, không đổi contract FE ngoài thông điệp lỗi.
> Dòng code tham chiếu theo nhánh `wip/autosave` tại commit `9648b07`.

## 1. S01 — Lọc khoá giá vốn khỏi nhật ký (L-3)

**Chỗ sửa**
| File | Dòng | Việc |
|---|---|---|
| `backend/apps/common/cost_keys.py` (mới) | — | Danh sách khoá + hàm lọc, dùng chung (sau này khối "Đã làm" của hồ sơ AI dùng lại) |
| `backend/apps/accounts/audit/serializers.py` | 10, 26 | `audit_item(row, *, can_view_cost)`; `changes` đi qua hàm lọc khi `can_view_cost=False` |
| `backend/apps/accounts/audit/api.py` | 42 (`get`) | Tính `can_view_cost = request.user.has_perm(VIEW_COSTPRICE_PERM)` **một lần**, truyền vào `audit_item` |

**Cách sửa**
```python
# apps/common/cost_keys.py
from apps.common.api import VIEW_COSTPRICE_PERM

# Khoá mang giá vốn / giá mua / lãi lỗ trong mọi JSON tự do (AuditLog.changes, sau này guidance).
# Quy ước: giá BÁN khi ghi audit dùng khoá khác ("price", "sell_rate", "amount"), không dùng "rate".
COST_KEYS = frozenset({
    "purchase_rate", "landed_unit_cost", "unit_cost", "rate",          # Batch, PurchaseReceiptLine, *LineBatch
    "allocated_amount", "purchase_cost", "allocated_cost", "total_cost",  # PurchaseCost / batch_pnl
    "shrinkage_cost", "damage_cost", "cogs", "profit",
})

def can_view_cost(user) -> bool:
    return bool(user and user.has_perm(VIEW_COSTPRICE_PERM))

def redact_cost(value):
    """Trả BẢN SAO đã bỏ mọi khoá thuộc COST_KEYS ở mọi độ sâu (dict lồng, list). Không sửa input."""
    if isinstance(value, dict):
        return {k: redact_cost(v) for k, v in value.items() if k not in COST_KEYS}
    if isinstance(value, list):
        return [redact_cost(v) for v in value]
    return value
```
- Bỏ hẳn khoá (không thay bằng `"***"`) → contract `changes` giữ kiểu dict; FE (`erp-console/features/audit/…`) chỉ đếm số khoá, không phải sửa.
- `note` không lọc: quy ước ghi (docstring `record_audit`) — **không đưa số giá vốn vào `note`**. Bổ sung một dòng vào docstring
  `apps/common/audit.py` nhắc quy ước này và trỏ tới `COST_KEYS`.
- **Không sửa dữ liệu `AuditLog`** (append-only). Không đổi `record_audit`.
- Đã rà mọi `record_audit(..., changes=...)` (grep 28/09): chỉ 3 nguồn có giá vốn — `inventory/batches/services.py:166-169`
  (`close_batch`), `:189-192` (`recompute_landed_cost`), `common/admin.py:47` (`admin_edit`, khi superuser sửa `Batch.purchase_rate`/
  `landed_unit_cost` — khoá ở `inventory/admin.py:58-61`). `purchasing/` hiện không ghi audit; `PurchaseReceiptLine.rate` chỉ sửa qua
  inline Admin (không audit). Các khoá tiền khác (`amount`, `refund_amount`, `paid_total`, `total_amount`, `bank_amount`) là tiền
  **bán/thu**, không phải giá vốn → giữ.
- `sales/orders/timeline.py` đọc `changes` nhưng chỉ lấy khoá cụ thể của đơn/phiếu giao/phiếu hoàn (không có giá vốn) → không đổi.

**Test bắt buộc** (`backend/apps/accounts/audit/tests/test_l3_cost_redaction.py`, `backend/apps/common/tests/test_cost_keys.py`)
- S01-AC1…AC4 bằng token `chu`, `quan_ly`, `quan_ly`+perm `inventory.view_costprice` (dùng `make_user(..., perms=...)`), superuser,
  `nv_kho`, `nv_giao`, khách. Dòng mẫu tạo bằng **service thật**: `recompute_landed_cost`, `close_batch` (sau S04 cần kiểm kê — dựng đủ
  điều kiện) và `record_audit("admin_edit", changes={"purchase_rate": {...}, "landed_unit_cost": {...}, "status": {...}})`.
- Assert `quan_ly`: duyệt đệ quy toàn bộ `changes` không có khoá nào ∈ `COST_KEYS`; `json.dumps(resp.json())` không chứa `987654.3210`.
- Unit: dict lồng 3 tầng, list chứa dict, input không bị đổi (so với bản sao trước khi gọi).

## 2. S02 — Tra đơn Shop (L-6)

**Chỗ sửa**: `backend/apps/sales/orders/shop_api.py:59-71` (`ShopOrderLookupView.get`), `backend/apps/sales/payments/shop_api.py:20-23`.

**Cách sửa**
```python
LOOKUP_NOT_FOUND = "Không tìm thấy đơn với mã và số điện thoại này."   # dùng chung, export từ orders/shop_api.py
LOOKUP_BAD_LAST4 = "Vui lòng nhập đúng 4 số cuối số điện thoại."
_LAST4 = re.compile(r"\d{4}")

phone_last4 = request.query_params.get("phone_last4", "")
if not _LAST4.fullmatch(phone_last4):                       # kiểm TRƯỚC khi đọc DB → không lộ mã đơn tồn tại
    return Response({"detail": LOOKUP_BAD_LAST4}, status=400)
order = SalesOrder.objects.select_related("customer").filter(code=order_code).first()
digits = re.sub(r"\D", "", order.phone) if order else ""
if order is None or len(digits) < 4 or digits[-4:] != phone_last4:
    return Response({"detail": LOOKUP_NOT_FOUND}, status=404)
```
- Dùng `re.fullmatch` với `\d{4}` (không dùng `str.isdigit()` — nhận cả chữ số Unicode). Không `strip()`; FE đã trim.
- `payments/shop_api.py`: thay "Không tìm thấy đơn." bằng `LOOKUP_NOT_FOUND` (import từ `apps.sales.orders.shop_api`). Không đòi
  4 số ở checkout (P1-AC6 giữ nguyên, ghi "việc sau").
- Response 200 giữ nguyên tập khoá; FE Shop không phải sửa (`frontend/lib/api.ts:127-137` coi 404 là "không thấy", form đã chặn khác 4 số).

**Test bắt buộc** (thêm vào `backend/apps/sales/orders/tests/test_shop_api.py` hoặc file mới `test_l6_lookup.py`)
- S02-AC1: 5 giá trị sai định dạng × {mã có thật, mã không có} → 400, body giống hệt nhau.
- S02-AC2: `resp_khong_co.json() == resp_sai_so.json()` và cùng 404.
- S02-AC3: `set(resp.json()) == {...7 khoá...}`; `customer`/`phone`/`name`/`delivery_address` không có.
- S02-AC4: SĐT lưu có dấu cách / `+84`.
- S02-AC5: checkout mã không tồn tại → 404 `LOOKUP_NOT_FOUND`.
- Test cũ `test_shop_api.py:55` (`0000` → 404) phải vẫn xanh.

## 3. S03 — Throttle endpoint công khai (L-5)

**Chỗ sửa**
| File | Việc |
|---|---|
| `backend/apps/common/throttling.py` (mới) | Lớp throttle đọc mức từ `settings.CAVEVE_THROTTLE_RATES` **lúc chạy** |
| `backend/config/settings.py:183-197` | `CAVEVE_THROTTLE_RATES` từ env; `REST_FRAMEWORK["NUM_PROXIES"]` |
| `backend/apps/common/api.py:109` (`exception_handler`) | `Throttled` → 429 `{"detail": "...", "code": "throttled"}`, giữ `Retry-After` |
| `backend/apps/sales/orders/shop_api.py` | `ShopOrderCreateView.throttle_classes`, `ShopOrderLookupView.throttle_classes` |
| `backend/apps/sales/payments/shop_api.py` | `ShopOrderCheckoutView.throttle_classes` |
| `backend/apps/accounts/auth/api.py:25` | `LoginTokenView.throttle_classes` |

**Mức mặc định** (env ghi đè; giá trị rỗng/`off` = tắt scope; khi `TESTING` mọi scope mặc định `None`)
| Scope | Endpoint | Khoá đếm | Env | Mặc định |
|---|---|---|---|---|
| `shop_lookup_ip` | `GET /api/shop/orders/<mã>/` | IP | `THROTTLE_SHOP_LOOKUP_IP` | `20/min` |
| `shop_lookup_order` | như trên | mã đơn (upper) | `THROTTLE_SHOP_LOOKUP_ORDER` | `10/hour` |
| `shop_order_create` | `POST /api/shop/orders/` | IP | `THROTTLE_SHOP_ORDER_CREATE` | `20/hour` |
| `shop_checkout` | `POST /api/shop/orders/<mã>/checkout/` | IP | `THROTTLE_SHOP_CHECKOUT` | `30/hour` |
| `login_ip` | `POST /api/auth/token/` | IP | `THROTTLE_LOGIN_IP` | `10/min` |
| `login_user` | như trên | sha256(username.lower()) | `THROTTLE_LOGIN_USER` | `30/hour` |

**Cách sửa**
```python
# apps/common/throttling.py
class SettingsRateThrottle(SimpleRateThrottle):
    """Đọc mức từ settings.CAVEVE_THROTTLE_RATES MỖI request (override_settings có hiệu lực).
    Không dùng DEFAULT_THROTTLE_RATES: SimpleRateThrottle.THROTTLE_RATES bị gán lúc import."""
    def get_rate(self):
        return (getattr(settings, "CAVEVE_THROTTLE_RATES", {}) or {}).get(self.scope)
    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}   # IP

class ShopLookupIpThrottle(SettingsRateThrottle):     scope = "shop_lookup_ip"
class ShopLookupOrderThrottle(SettingsRateThrottle):  scope = "shop_lookup_order"   # ident = view.kwargs["order_code"].upper()
class ShopOrderCreateThrottle(SettingsRateThrottle):  scope = "shop_order_create"
class ShopCheckoutThrottle(SettingsRateThrottle):     scope = "shop_checkout"
class LoginIpThrottle(SettingsRateThrottle):          scope = "login_ip"
class LoginUserThrottle(SettingsRateThrottle):        scope = "login_user"          # ident = sha256(username.strip().lower()); thiếu username → None (không đếm)
```
- Settings: `_rate(name, default)` trả `None` nếu env là `""`/`off`/`0`; `CAVEVE_THROTTLE_RATES = {scope: None for ...} if TESTING else {...}`.
- `REST_FRAMEWORK["NUM_PROXIES"] = int(os.getenv("DRF_NUM_PROXIES", "1"))` → DRF lấy IP **cuối** của `X-Forwarded-For` (do Google
  Front End của Cloud Run thêm), client không giả được. Không có XFF (test) → dùng `REMOTE_ADDR`.
- Cache: dùng cache mặc định (không khai `CACHES` → `LocMemCache`). Chấp nhận đếm theo từng worker (ghi "việc sau"). **Không** thêm
  `CACHES`/Redis trong lô này.
- 429: trong `exception_handler`, nhánh `isinstance(exc, Throttled)`: gọi `drf_exception_handler` để giữ header `Retry-After`, rồi
  thay `response.data = {"detail": f"Bạn thao tác quá nhanh. Vui lòng thử lại sau {ceil(exc.wait or 1)} giây.", "code": "throttled"}`.
- **Không** đặt `DEFAULT_THROTTLE_CLASSES` toàn cục (S03-AC5: back-office không bị throttle).
- Không log IP, username, SĐT ở bất kỳ nhánh nào.

**Test bắt buộc** (`backend/apps/common/tests/test_l5_throttle.py`)
- Mỗi scope: `@override_settings(CAVEVE_THROTTLE_RATES={...: "3/min"})`, `cache.clear()` ở `setUp`/`tearDown`; request thứ N+1 → 429,
  body đúng 2 khoá `detail`/`code`, có `Retry-After`.
- `shop_lookup_order`: 4 request với `REMOTE_ADDR` khác nhau cùng mã đơn → lần 4 bị 429.
- `shop_order_create`/`login`: đếm `SalesOrder.objects.count()`/`Token.objects.count()` trước-sau request bị chặn bằng nhau.
- XFF giả: `HTTP_X_FORWARDED_FOR="1.1.1.1, 9.9.9.9"` rồi `"2.2.2.2, 9.9.9.9"` → đếm chung.
- Back-office: `chu` gọi `GET /api/audit-logs/` 50 lần với mức shop đặt `1/min` → không có 429.
- Không bật throttle: suite cũ xanh (chính là lệnh kiểm chứng tổng).

## 4. S04 — `close_batch` (L-1)

**Chỗ sửa**: `backend/apps/inventory/batches/services.py:148-170`. API (`inventory/batches/api.py:37-38`) không đổi.

**Cách sửa** (thứ tự kiểm cố định, mọi phép kiểm trên bản ghi đã khoá)
```python
OPEN_ORDER_STATUSES = ("BOOKED", "PAID", "PROCESSING")   # dùng SalesOrder.Status.*

@transaction.atomic
def close_batch(*, batch, actor):
    batch = Batch.objects.select_for_update().get(pk=batch.pk)
    if batch.is_closed: raise BusinessError("Lô đã chốt.", code="BR-LO-05")
    # (1) tồn = 0 hoặc lô EXPIRED/CANCELLED — giữ nguyên điều kiện cũ, code="BR-LO-04"
    # (2) qty_reserved > 0 → BR-LO-04
    # (3) số đơn mở: SalesOrderLineBatch.objects.filter(batch=batch,
    #        order_line__order__status__in=OPEN_ORDER_STATUSES).values("order_line__order").distinct().count() > 0
    #     → BusinessError(f"Còn {n} đơn đang mở tham chiếu lô, chưa chốt được (BR-LO-04).", code="BR-LO-04")
    # (4) ReturnToStock(batch=batch, status=DRAFT).exists() → BR-LO-04 (lô chốt không nhận hàng hoàn — BR-LO-05)
    # (5) Purchase Invoice (giữ nguyên logic cũ, thêm code="BR-LO-04")
    # (6) kiểm kê: StockReconciliationLine(batch=batch, reconciliation__status=APPROVED).exists() là bắt buộc,
    #     và StockReconciliationLine(batch=batch, reconciliation__status=DRAFT).exists() là chặn → code="BR-KK-05"
    ... cập nhật status/closed_at/closed_by, record_audit như cũ ...
```
- Import model sales **trong hàm** (tránh vòng import inventory ↔ sales), hoặc import `apps.sales.models` ở đầu nếu không vòng — dev kiểm.
- Thông điệp chỉ có số lượng đơn, **không** mã khách/tên/SĐT.
- Thứ tự (1) trước (3) để test cũ `common/tests/test_s3_locked_fields.py:355-361` (lô SELLING còn tồn → `BR-LO-04`) vẫn đúng.
- Cố ý giữ: lô `EXPIRED` còn tồn vẫn chốt được như cũ (L-2 chưa có service huỷ — "việc sau").
- Định nghĩa "đã kiểm kê" (BR-KK-05, PA) chọn mức đơn giản: có ≥ 1 phiếu **đã duyệt** chứa lô và không có phiếu **nháp** chứa lô. Không
  so thời điểm với chuyển động kho cuối — nếu Duy muốn chặt hơn thì làm ở hồ sơ AI Lô 1 (`check_close_batch`).

**Test bắt buộc** (`backend/apps/inventory/batches/tests/test_l1_close_batch.py`)
- AC1: ba trạng thái mở × chặn; ba trạng thái đóng × không chặn (đơn dựng bằng `create_order`/fixture có sẵn ở `sales/orders/tests/base.py`).
- AC2: `qty_reserved>0`; `ReturnToStock` DRAFT.
- AC3: không phiếu; chỉ phiếu DRAFT; phiếu APPROVED + phiếu DRAFT khác cùng chứa lô.
- AC4: happy path qua API bằng `chu`; chốt lần 2 → 400.
- AC5: sau khi chốt, `allocate_fefo(item=..., qty=...)` không trả lô đó; assert `close_batch` được bọc atomic (vd `mock.patch` `Batch.objects.select_for_update` được gọi, hoặc kiểm `transaction.get_connection().in_atomic_block` trong hàm giả).
- AC6: `quan_ly`/`nv_kho`/`nv_giao` → 403, `batch.status` không đổi; khách → 401; body 400 không có `landed_unit_cost`/`purchase_rate`.
- **Sửa test cũ có chủ đích**: `apps/inventory/batches/tests/test_services.py:66-80` (`test_publish_and_close_batch`) phải thêm phiếu
  kiểm kê APPROVED cho lô trước khi chốt (đổi nghiệp vụ theo BR-KK-05). Ghi vào `03-dev-notes.md`. Không sửa test cũ nào khác.

## 5. S05 — noindex staging

**Chỗ sửa**: `frontend/firebase.staging.json`, `erp-console/firebase.staging.json`, thêm 1 dòng vào `doc/ops/moi-truong.md` (mục Deploy).

**Cách sửa**: thêm vào mảng `hosting.headers` (ERP chưa có mảng này → tạo):
```json
{ "source": "**", "headers": [{ "key": "X-Robots-Tag", "value": "noindex, nofollow" }] }
```
- Chọn header theo **file deploy** thay vì biến build: production deploy bằng `firebase.json` nên không thể dính nhầm, kể cả khi build nhầm
  biến. Không thêm `robots.txt` Disallow cho staging (Disallow làm Google không đọc được `noindex`, URL vẫn có thể hiện).
- **Không** sửa `frontend/firebase.json`, `erp-console/firebase.json`, `frontend/app/layout.tsx`, `erp-console/app/layout.tsx`.
- Kiểm: `node -e 'JSON.parse(require("fs").readFileSync("firebase.staging.json"))'` ở hai app; `git diff --exit-code frontend/firebase.json
  erp-console/firebase.json`; build hai app. `curl -sI` chỉ chạy được **sau** khi Duy deploy staging.

## 6. Rủi ro hồi quy

| Rủi ro | Cơ chế chặn | Test bắt |
|---|---|---|
| Lọc audit bỏ nhầm khoá không nhạy cảm (`rate` là giá bán ở chỗ khác) | Quy ước khoá bán ≠ `rate`; hiện không có audit ghi giá bán | S01 unit + AC2 "khoá `status` còn" |
| Rò giá vốn qua `note` trong tương lai | Quy ước trong docstring `record_audit` | Review code; khối "Đã làm" (hồ sơ AI) dùng lại `redact_cost` |
| Throttle làm vỡ test cũ / chặn khách thật chung IP (NAT nhà mạng) | `TESTING` → tắt; mức qua env, nới được không cần deploy code | Suite cũ xanh; S03-AC3 |
| `NUM_PROXIES` sai trên Cloud Run → mọi khách chung một IP hoặc giả được IP | Mặc định 1 (GFE thêm 1 IP); env `DRF_NUM_PROXIES` | Test XFF; sau deploy staging Duy thử 2 máy khác mạng không chặn nhau |
| `close_batch` chặt hơn → Chủ không chốt được lô cũ chưa kiểm kê | Có đường tạo + duyệt kiểm kê (Admin + `POST /api/inventory/reconciliations/<id>/approve/`) | S04-AC3/AC4 |
| Vòng import inventory ↔ sales | Import trong hàm | Suite + `makemigrations --check` |
| 404/400 tra đơn đổi thông điệp → FE hiện sai | FE coi 404 = không thấy; form chặn khác 4 số | QA thử Shop mock + staging |
| Header noindex lọt production | Chỉ sửa `*.staging.json` | `git diff --exit-code` hai `firebase.json` |
| S06 đổi nhầm `period_pnl` hoặc khoá response lô | Chỉ sửa 1 dòng `total_cost` + docstring trong `batch_pnl` | `period_pnl` test cũ xanh; S06-AC5 assert đúng 14 khoá |
| S06 làm lộ lãi lỗ cho người thiếu quyền | Không đụng `reports/api.py` (`require_perm` giữ nguyên) | S06-AC6 `test_api.py` mới |

## 7. S06 — Lãi lỗ theo lô không tính hai lần (L-10) · thêm 28/09, Duy duyệt

**Chỗ sửa**: `backend/apps/reports/services.py` hàm `batch_pnl` (dòng 23-83). `reports/api.py`, `config/api_urls.py`, `period_pnl`,
`dashboard_api.py` **không đổi**. Không model, không migration, không FE.

**Cách sửa** (một dòng logic, còn lại là docstring)
```python
    # BR-BC-04 (sửa 2026-09-28, Duy duyệt): purchase_cost đã tính trên toàn bộ qty_received, gồm cả kg hao hụt/hỏng
    # → shrinkage_cost/damage_cost chỉ để HIỂN THỊ số tiền mất, KHÔNG cộng vào total_cost.
    total_cost = purchase_cost + allocated_cost
    profit = revenue - total_cost
```
- Giữ nguyên cách tính `shrinkage_qty/cost`, `damage_qty/cost` (theo `landed_unit_cost` hiện hành), `provisional`, thứ tự và tên 14 khoá.
- Sửa docstring module + `batch_pnl`: công thức mới, ghi rõ hao hụt/hàng hỏng "chỉ hiển thị, đã nằm trong giá mua" (tránh người sau cộng lại).
- `doc/BUILD-PLAN.md:147`: sửa chú thích `batch_pnl` thành `doanh thu từ lô − (giá mua + chi phí phân bổ); hao hụt/hàng hỏng trả riêng,
  không cộng (BR-BC-04 sửa 28/09)`. `backend/apps/reports/README.md` nếu có nêu công thức thì sửa cùng ý (hiện không nêu — dev kiểm).
- Vì sao không đổi `period_pnl`: giá vốn kỳ = Σ `qty × unit_cost` ảnh chụp của phần **đã bán** (BR-BC-02), vốn không có khoản hao hụt/hỏng
  → không tính hai lần. Việc kỳ không phản ánh tiền mất do hao hụt là câu hỏi khác (ghi "Việc sau" L-11 trong `02-stories.md`).
- Tương thích với hồ sơ AI: DW-06 (TL-4) thêm `expired_qty`/`expired_cost` **chỉ hiển thị** — cùng nguyên tắc; sau S06 số khoá thành 16 ở hồ
  sơ đó, không mâu thuẫn AC5 ở đây (AC5 chốt contract tại thời điểm Lô 3).

**Rủi ro bắt buộc**
| Rủi ro | Cơ chế chặn | Test bắt |
|---|---|---|
| Rò giá vốn/lãi lỗ | Không đổi view; `require_perm("reports.view_profitreport")` ở `BatchPnlView` | AC6: 3 Group → 403, JSON không có khoá `landed_unit_cost`/`purchase_cost`/`profit`; khách 401 |
| Rò dữ liệu cá nhân | Response lô không có field khách; test chỉ dùng `Customer` giả (`0900000002`) như test cũ | review diff |
| Đổi nhầm hình dạng response (FE/AI lệnh `bao_cao_lo` bám theo) | Không thêm/bớt khoá | AC5 `assertEqual(set(result), {14 khoá})` |
| Chứng từ/xoá dữ liệu | Hàm chỉ đọc | — |

**Test bắt buộc**
- `backend/apps/reports/tests/test_services.py` (thêm test, dùng `setUp` sẵn hoặc lô riêng 100 kg × 100.000 không phân bổ cho AC1):
  - `test_batch_pnl_duy_example_shrinkage_not_double_counted` — AC1, profit 3.500.000.
  - `test_batch_pnl_damage_shown_not_added_to_total_cost` — phiếu hỏng `WRITE_OFF APPROVED` 5 kg + phiếu `DRAFT` 2 kg: `damage_qty`=5,
    `total_cost` = `purchase_cost + allocated_cost`.
  - `test_batch_pnl_total_cost_invariant_under_losses` — AC3: gọi trước và sau khi thêm hao hụt + hàng hỏng, `total_cost`/`profit` bằng nhau.
  - `test_batch_pnl_keys_unchanged` — AC5, đúng 14 khoá.
  - `test_batch_pnl_not_provisional_when_closed` (có sẵn) + thêm assert lô `CLOSED` cùng công thức (AC4).
- `backend/apps/reports/tests/test_api.py` (**mới**, dùng `apps/common/tests/fixtures.py` `make_user`/`client_for`/`make_master`): AC6 `chu`
  200 + 14 khoá; `quan_ly`/`nv_kho`/`nv_giao` 403 và `resp.json()` không có **khoá** `profit`, `landed_unit_cost`, `purchase_cost`
  (so khoá, không so chuỗi — thông điệp 403 chứa chữ `view_profitreport`); khách 401; mã lô
  không tồn tại 404.
- **Sửa test cũ có chủ đích (duy nhất)**: `apps/reports/tests/test_services.py::ReportsServiceTests::test_batch_pnl_computes_profit_with_shrinkage_and_damage`
  (dòng 112-113): `total_cost` `8610000` → `8200000`, `profit` `-1410000` → `-1000000`, sửa chú thích "lỗ vì lô chưa bán hết" giữ nguyên.
  Lý do: test đang khoá công thức sai BR-BC-04 cũ. Các assert khác trong test đó (`shrinkage_cost` 164.000, `damage_cost` 246.000…) giữ nguyên.
  Ghi vào `03-dev-notes.md`. Không sửa test cũ nào khác; `period_pnl` và `test_d1_seed_demo.py` (chỉ dùng `period_pnl`) phải xanh nguyên.

## 8. Review
_(Tech Lead điền sau khi lô QA APPROVED: REVIEW PASS / REVIEW FAIL kèm file:dòng.)_

"""
P1 (BR-TT-01, 13, 14, 17): máy chủ lập tham số thanh toán cổng SePay (hosted checkout) cho
một đơn Giữ chỗ còn TTL. KHÔNG đụng `PaymentTransaction` — chỉ tính/ký tham số để Shop FE
chuyển hướng khách sang trang SePay (form POST). Việc xác nhận đã trả tiền là việc của
IPN (P2/P3).

BR-TT-13: khoá bí mật (`settings.SEPAY_SECRET_KEY`) CHỈ dùng để TÍNH chữ ký ở đây,
KHÔNG BAO GIỜ nằm trong response, log, hay đi xuống trình duyệt.

Thuật toán ký + tên field lấy NGUYÊN VĂN theo SDK chính thức của SePay
(github.com/sepayvn/sepay-pg-node, `src/checkout.ts` + `src/types.ts`, đọc trực tiếp mã
nguồn — không còn là giả định): tên field `merchant` (không phải `merchant_id`),
`operation="PURCHASE"`, `payment_method` ("BANK_TRANSFER" = VietQR, V1 chỉ dùng giá trị
này), chữ ký = HMAC-SHA256 trên chuỗi nối "key=value" (bỏ key rỗng/None) THEO ĐÚNG THỨ TỰ
field của form, rồi mã hoá BASE64 (không phải hex). Vì thứ tự quyết định chữ ký,
`build_checkout_params` trả `fields`: MẢNG CÓ THỨ TỰ `[{"name":.., "value":..}, …]` (đã gồm
`signature` ở cuối) — đây là NGUỒN CHÍNH để FE dựng form POST; các key top-level khác chỉ
để tiện đọc/tương thích ngược, không dùng để tự ráp form.
"""
import base64
import hashlib
import hmac
import unicodedata

from django.conf import settings
from django.db import transaction

from apps.common.exceptions import BusinessError
from apps.sales.models import SalesOrder
from apps.sales.utils import money_str, money_vnd, now as _now

CURRENCY = "VND"
BOOKING_CODE = "BR-TT-17"

MSG_EXPIRED = "Đơn đã hết hạn giữ hàng, vui lòng đặt lại."
MSG_CANCELLED = "Đơn đã huỷ."
MSG_ALREADY_PAID = "Đơn đã thanh toán."

# BR-TT-01 (Duy chốt 2026-09-26): V1 chỉ VietQR — CHỈ dùng giá trị này, không cho chọn khác.
OPERATION_PURCHASE = "PURCHASE"
PAYMENT_METHOD_BANK_TRANSFER = "BANK_TRANSFER"

# Thứ tự CHÍNH XÁC của field trên form checkout SDK SePay (`src/checkout.ts`). Chữ ký ký
# trên chuỗi ghép THEO ĐÚNG THỨ TỰ NÀY — sai thứ tự = sai chữ ký. V1 không dùng nhóm
# `agreement_*` (thanh toán định kỳ) hay `env`/`customer_id`/`order_id`; các key đó bị bỏ
# qua tự động vì không có giá trị (None).
FIELD_ORDER = [
    "merchant", "env", "operation", "payment_method", "order_amount", "currency",
    "order_invoice_number", "order_description", "customer_id", "agreement_id",
    "agreement_name", "agreement_type", "agreement_payment_frequency",
    "agreement_amount_per_payment", "success_url", "error_url", "cancel_url", "order_id",
]


def _checkout_url_and_env():
    """BR-TT-14: URL cổng + môi trường là cấu hình, đổi bằng `SEPAY_ENV`, không sửa code."""
    env = (getattr(settings, "SEPAY_ENV", "") or "SANDBOX").strip().upper()
    if env == "PRODUCTION":
        return settings.SEPAY_CHECKOUT_URL_PRODUCTION, "PRODUCTION"
    return settings.SEPAY_CHECKOUT_URL_SANDBOX, "SANDBOX"


def _return_urls(order_code):
    """
    BR-TT-12: cả 3 URL quay về đều trỏ về TRANG TRA ĐƠN của Shop — trang này tự đọc trạng
    thái thật trong hệ thống (KHÔNG suy ra "đã thanh toán" chỉ vì khách được đưa về
    success_url). V1 dùng chung 1 trang cho cả 3 kết quả; FE tự phân biệt qua query string
    nếu cần hiển thị khác nhau.
    """
    base = (getattr(settings, "SHOP_BASE_URL", "") or "").rstrip("/")
    target = f"{base}/shop/orders?code={order_code}"
    return {
        "success_url": f"{target}&result=success",
        "cancel_url": f"{target}&result=cancel",
        "error_url": f"{target}&result=error",
    }


def _no_diacritics(text):
    """Bỏ dấu tiếng Việt, giữ nguyên hoa/thường — dùng cho `order_description`."""
    s = unicodedata.normalize("NFD", text)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D")


def _order_description(order_invoice_number):
    """`order_description` là field BẮT BUỘC của SDK — không dấu (vd 'Thanh toan don <mã>')."""
    return _no_diacritics(f"Thanh toan don {order_invoice_number}")


def _signature_string(values):
    """
    NGUYÊN VĂN thuật toán SDK chính thức (sepayvn/sepay-pg-node, `src/checkout.ts`): duyệt
    field THEO ĐÚNG THỨ TỰ `FIELD_ORDER`, bỏ qua key không có mặt hoặc giá trị None, mỗi
    field thành `"key=value"`, nối bằng `","`.
    """
    parts = []
    for key in FIELD_ORDER:
        value = values.get(key)
        if value is None:
            continue
        parts.append(f"{key}={value}")
    return ",".join(parts)


def _sign(message):
    """HMAC-SHA256 rồi BASE64 (KHÔNG phải hex) — đúng `src/checkout.ts` của SDK chính thức."""
    secret = (getattr(settings, "SEPAY_SECRET_KEY", "") or "").encode("utf-8")
    digest = hmac.new(secret, message.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def _check_bookable(order, now):
    """BR-TT-17: chỉ lập tham số cho đơn Giữ chỗ còn TTL."""
    if order.status == SalesOrder.Status.AUTO_CANCELLED:
        raise BusinessError(MSG_EXPIRED, code=BOOKING_CODE)
    if order.status == SalesOrder.Status.CANCELLED:
        raise BusinessError(MSG_CANCELLED, code=BOOKING_CODE)
    if order.status != SalesOrder.Status.BOOKED:
        raise BusinessError(MSG_ALREADY_PAID, code=BOOKING_CODE)
    if order.booked_expires_at is not None and order.booked_expires_at < now:
        raise BusinessError(MSG_EXPIRED, code=BOOKING_CODE)


def _order_invoice_number(order, attempt):
    """
    Q5 (đối chiếu adapter `strip_order_retry_suffix`): lần 1 gửi đúng `order.code`; từ lần 2
    thêm hậu tố `-<n>` — đúng định dạng adapter đã cài sẵn để bóc lại mã gốc.
    """
    return order.code if attempt <= 1 else f"{order.code}-{attempt}"


def build_checkout_params(*, order, now=None):
    """
    Lập bộ tham số thanh toán cho `order` (P1-AC1). Gọi được nhiều lần cho CÙNG đơn còn
    Giữ chỗ (P1-AC5, thanh toán lại) — luôn cùng số tiền (đã đóng băng lúc tạo đơn,
    BR-BH-08); từ lần gọi thứ 2 thêm hậu tố lần thử vào `order_invoice_number` (Q5).
    Raise `BusinessError` (BR-TT-17) nếu đơn hết hạn/đã huỷ/đã thanh toán.

    Response KHÔNG chứa bất kỳ thông tin khách nào (tên/SĐT/địa chỉ) — P1-AC6.
    """
    now = now or _now()
    with transaction.atomic():
        o = SalesOrder.objects.select_for_update().get(pk=order.pk)
        _check_bookable(o, now)
        o.checkout_attempts += 1
        o.save(update_fields=["checkout_attempts"])
        attempt = o.checkout_attempts

    # P5-AC3 (BR-BH-15): phòng đơn cũ còn tổng lẻ xu (tạo trước khi BR-BH-15 có hiệu lực) —
    # làm tròn NGUYÊN ĐỒNG theo đúng quy tắc BR-BH-15 khi lập tham số, KHÔNG sửa lại
    # `order.total_amount` đã lưu (chứng từ không đổi ngược, bất biến #3/#8).
    order_amount_str = money_str(money_vnd(o.total_amount))
    order_invoice_number = _order_invoice_number(o, attempt)
    order_description = _order_description(order_invoice_number)

    checkout_url, environment = _checkout_url_and_env()
    urls = _return_urls(o.code)
    merchant = getattr(settings, "SEPAY_MERCHANT_ID", "") or ""

    values = {
        "merchant": merchant,
        "operation": OPERATION_PURCHASE,
        "payment_method": PAYMENT_METHOD_BANK_TRANSFER,
        "order_amount": order_amount_str,
        "currency": CURRENCY,
        "order_invoice_number": order_invoice_number,
        "order_description": order_description,
        "success_url": urls["success_url"],
        "error_url": urls["error_url"],
        "cancel_url": urls["cancel_url"],
    }
    signature = _sign(_signature_string(values))

    # `fields`: NGUỒN CHÍNH cho FE — mảng CÓ THỨ TỰ, gồm cả `signature` ở cuối (SDK yêu cầu
    # form POST đúng thứ tự field).
    fields = [{"name": key, "value": values[key]} for key in FIELD_ORDER if key in values]
    fields.append({"name": "signature", "value": signature})

    return {
        "gateway": "SEPAY",
        "environment": environment,
        "checkout_url": checkout_url,
        "fields": fields,
        # Top-level: tiện đọc/tương thích ngược — KHÔNG dùng để tự ráp lại form (dùng `fields`).
        "merchant": merchant,
        "operation": OPERATION_PURCHASE,
        "payment_method": PAYMENT_METHOD_BANK_TRANSFER,
        "order_invoice_number": order_invoice_number,
        "order_amount": order_amount_str,
        "currency": CURRENCY,
        "order_description": order_description,
        "success_url": urls["success_url"],
        "cancel_url": urls["cancel_url"],
        "error_url": urls["error_url"],
        "signature": signature,
    }

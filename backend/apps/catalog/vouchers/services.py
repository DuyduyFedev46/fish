"""
Mã giảm giá (SHOP-3b-01, 3b-03, 3b-04; BR-DM-17…24, quyết định Duy 10/10) — NGHIỆP VỤ, không đọc request.

- `normalize_code`          : bỏ khoảng trắng, IN HOA ("cave 10" -> "CAVE10").
- `evaluate_voucher`        : MỘT hàm tính giảm dùng chung cho kiểm mã công khai và tạo đơn (02b §3.8).
- `allocate_whole_vnd`      : chia số giảm vào từng dòng, nguyên đồng, tổng khớp tuyệt đối.
- `create/update/disable/enable_voucher` : ERP, ghi AuditLog; sửa theo hướng có lợi cho khách (BR-DM-22).

Lượt dùng (giữ/dùng/nhả) ở `apps.sales.orders.voucher_redemptions`. Không có đường xoá mã (bất biến 3).
Không dữ liệu cá nhân ở đây (bất biến 9): mã là công khai, giới hạn theo TỔNG lượt, không theo SĐT.
"""
import re
from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
from django.db.models import Count, F, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.catalog.models import Voucher
from apps.common.audit import note_marker, record_audit
from apps.common.exceptions import BusinessError
from apps.common.pii import has_long_digit_run
from apps.sales.utils import money_str

CODE_RE = re.compile(r"^[A-Z0-9]{4,20}$")
NAME_MAX = 120
TERMS_MAX = 300
NOTE_MAX = 200
ZERO = Decimal("0")
ONE = Decimal("1")

# Lý do kiểm mã (02b §3.8).
REASON_INVALID = "INVALID"
REASON_EXPIRED = "EXPIRED"
REASON_USED_UP = "USED_UP"
REASON_MIN_ORDER = "MIN_ORDER"
REASON_BETTER_PROMO = "BETTER_PROMO"

STATUS_RUNNING = "running"
STATUS_SCHEDULED = "scheduled"
STATUS_PAUSED = "paused"
STATUS_EXPIRED = "expired"
STATUS_USED_UP = "used_up"
STATUS_VALUES = (STATUS_RUNNING, STATUS_SCHEDULED, STATUS_PAUSED, STATUS_EXPIRED, STATUS_USED_UP)

VALIDATION = "VALIDATION"
FIELD_LOCKED = "FIELD_LOCKED"
UNFAVORABLE_CHANGE = "UNFAVORABLE_CHANGE"
UNFAVORABLE_DETAIL = "Mã đang chạy chỉ sửa được theo hướng có lợi cho khách. Tắt mã này và tạo mã mới."
LOCKED_DETAIL = "Mã đã bắt đầu chạy nên không đổi được trường này. Tắt mã này và tạo mã mới."


def normalize_code(raw) -> str:
    """BR-DM-17: khách gõ "cave 10" hay "Cave10" đều là `CAVE10`."""
    return re.sub(r"\s+", "", str(raw or "")).upper()


# --- Lượt dùng và trạng thái ---------------------------------------------------------------------------------

def committed_count(voucher) -> int:
    """Lượt giữ + đã dùng. LUÔN đếm bằng truy vấn mới (sau khi khoá mã, 02b §2.2)."""
    from apps.sales.models import VoucherRedemption

    held_or_used = [VoucherRedemption.State.HELD, VoucherRedemption.State.USED]
    return VoucherRedemption.objects.filter(voucher_id=voucher.pk, state__in=held_or_used).count()


def voucher_status(voucher, *, now, committed) -> str:
    """Thứ tự ưu tiên: paused, expired, used_up, scheduled, còn lại running (02b §3.9)."""
    if not voucher.is_active:
        return STATUS_PAUSED
    if now >= voucher.ends_at:
        return STATUS_EXPIRED
    if committed >= voucher.total_uses:
        return STATUS_USED_UP
    if now < voucher.starts_at:
        return STATUS_SCHEDULED
    return STATUS_RUNNING


# --- Tính giảm ------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class VoucherEvaluation:
    valid: bool
    reason_code: str | None
    discount: Decimal           # số tiền giảm nguyên đồng nếu hợp lệ, ngược lại 0
    missing_amount: Decimal | None
    terms_visible: bool         # `terms` có trong kết quả hay không (02b §3.8)


def compute_discount(voucher, subtotal) -> Decimal:
    """
    AMOUNT -> `value`; PERCENT -> `subtotal × value / 100` chặn `max_discount`; rồi chặn `subtotal × VOUCHER_MAX_PERCENT / 100`
    (BR-DM-21); LÀM TRÒN XUỐNG nguyên đồng; luôn chừa lại ít nhất 1 đồng để tổng sau giảm > 0.
    """
    subtotal = Decimal(subtotal)
    if voucher.kind == Voucher.Kind.PERCENT:
        discount = subtotal * voucher.value / Decimal("100")
        if voucher.max_discount is not None:
            discount = min(discount, voucher.max_discount)
    else:
        discount = Decimal(voucher.value)
    discount = min(discount, subtotal * Decimal(settings.VOUCHER_MAX_PERCENT) / Decimal("100"))
    discount = min(discount, subtotal - ONE)
    return max(discount, ZERO).quantize(ONE, rounding=ROUND_DOWN)


def evaluate_voucher(*, voucher, subtotal, auto_discount, now, committed) -> VoucherEvaluation:
    """
    Dùng chung cho `POST /api/shop/vouchers/check/` và tạo đơn (02b §3.8). `voucher=None` = không có mã.
    `subtotal` là tổng GỘP trước mọi giảm giá (V-03). `auto_discount` là ưu đãi tự động (PricingRule) đang áp.
    Thứ tự lý do: INVALID, EXPIRED, USED_UP, MIN_ORDER, BETTER_PROMO (hoà cũng là BETTER_PROMO, BR-DM-18).
    """
    if voucher is None or not voucher.is_active or now < voucher.starts_at:
        return VoucherEvaluation(False, REASON_INVALID, ZERO, None, False)
    if now >= voucher.ends_at:
        return VoucherEvaluation(False, REASON_EXPIRED, ZERO, None, False)
    if committed >= voucher.total_uses:
        return VoucherEvaluation(False, REASON_USED_UP, ZERO, None, False)
    subtotal = Decimal(subtotal)
    if subtotal < voucher.min_order_amount:
        return VoucherEvaluation(False, REASON_MIN_ORDER, ZERO, voucher.min_order_amount - subtotal, True)
    discount = compute_discount(voucher, subtotal)
    if discount <= ZERO:
        return VoucherEvaluation(False, REASON_INVALID, ZERO, None, False)
    if Decimal(auto_discount) >= discount:
        return VoucherEvaluation(False, REASON_BETTER_PROMO, ZERO, None, True)
    return VoucherEvaluation(True, None, discount, None, True)


def allocate_whole_vnd(discount, gross_amounts):
    """
    Chia `discount` (nguyên đồng) vào từng dòng theo tỉ lệ thành tiền gộp: mỗi dòng LÀM TRÒN XUỐNG nguyên đồng,
    phần dư dồn dòng cuối, không dòng nào vượt gộp của nó (phần thừa trả về các dòng còn chỗ). Tổng luôn bằng `discount`.
    Ví dụ 300000 / 256000, giảm 50000 -> [26978, 23022]. Trả list Decimal cùng thứ tự `gross_amounts`.
    """
    discount = Decimal(discount)
    gross = [Decimal(g) for g in gross_amounts]
    total = sum(gross, ZERO)
    if not gross or total <= ZERO or discount <= ZERO:
        return [ZERO for _ in gross]
    shares = [(discount * g / total).quantize(ONE, rounding=ROUND_DOWN) for g in gross]
    shares[-1] = discount - sum(shares[:-1], ZERO)
    # Không dòng nào giảm quá gộp của nó: chuyển phần thừa sang dòng còn chỗ.
    for i in range(len(shares) - 1, -1, -1):
        cap = gross[i].quantize(ONE, rounding=ROUND_DOWN)
        if shares[i] > cap:
            extra, shares[i] = shares[i] - cap, cap
            for j in range(len(shares)):
                room = gross[j].quantize(ONE, rounding=ROUND_DOWN) - shares[j]
                move = min(room, extra)
                if move > ZERO:
                    shares[j] += move
                    extra -= move
    return shares


# --- Kiểm tra dữ liệu ERP --------------------------------------------------------------------------------------

def _validation_error(fields: dict) -> BusinessError:
    return BusinessError("Thông tin mã giảm giá chưa hợp lệ.", code=VALIDATION, extra={"fields": fields})


def _decimal(value, fields, key, message):
    if value is None or isinstance(value, bool) or str(value).strip() == "":
        fields[key] = message
        return None
    try:
        number = Decimal(str(value).strip())
    except InvalidOperation:
        fields[key] = message
        return None
    if not number.is_finite():
        fields[key] = message
        return None
    return number


def _datetime(value, fields, key):
    parsed = parse_datetime(value.strip()) if isinstance(value, str) else None
    if parsed is None:
        fields[key] = "Nhập ngày giờ hợp lệ."
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)  # giờ máy chủ = Asia/Ho_Chi_Minh
    return parsed


EDITABLE = (
    "code", "name", "kind", "value", "max_discount", "min_order_amount", "starts_at", "ends_at", "total_uses",
    "customer_terms",
)


def _clean_all(values: dict, *, instance=None) -> dict:
    """Kiểm MỘT bộ giá trị đầy đủ (tạo mới hoặc sau khi trộn với bản đang lưu). Trả dict đã chuẩn hoá hoặc ném VALIDATION."""
    fields: dict = {}
    out: dict = {}

    code = normalize_code(values.get("code"))
    if not CODE_RE.match(code):
        fields["code"] = "Mã gồm 4 đến 20 chữ cái không dấu hoặc số, không có khoảng trắng."
    elif has_long_digit_run(code):
        fields["code"] = "Mã không được chứa dãy 9 chữ số liền (giống số điện thoại)."
    else:
        taken = Voucher.objects.filter(code=code)
        if instance is not None:
            taken = taken.exclude(pk=instance.pk)
        if taken.exists():
            fields["code"] = "Mã này đã có. Chọn mã khác."
    out["code"] = code

    name = str(values.get("name") or "").strip()
    if not name or len(name) > NAME_MAX:
        fields["name"] = f"Nhập tên chương trình (tối đa {NAME_MAX} ký tự)."
    out["name"] = name

    kind = values.get("kind")
    if kind not in Voucher.Kind.values:
        fields["kind"] = "Chọn kiểu giảm: số tiền hoặc phần trăm."
    out["kind"] = kind

    value = _decimal(values.get("value"), fields, "value", "Nhập mức giảm.")
    max_discount = None
    raw_max = values.get("max_discount")
    if kind == Voucher.Kind.PERCENT:
        if value is not None:
            if value <= ZERO or value > Decimal(settings.VOUCHER_MAX_PERCENT):
                fields["value"] = f"Phần trăm giảm phải lớn hơn 0 và tối đa {settings.VOUCHER_MAX_PERCENT:f}%."
        max_discount = _decimal(raw_max, fields, "max_discount", "Mã phần trăm bắt buộc có trần giảm bằng tiền.")
        if max_discount is not None and (max_discount <= ZERO or max_discount != max_discount.to_integral_value()):
            fields["max_discount"] = "Trần giảm phải là số tiền nguyên đồng lớn hơn 0."
    elif kind == Voucher.Kind.AMOUNT:
        if value is not None and (value <= ZERO or value != value.to_integral_value()):
            fields["value"] = "Số tiền giảm phải là số nguyên đồng lớn hơn 0."
    out["value"] = value
    out["max_discount"] = max_discount if kind == Voucher.Kind.PERCENT else None

    min_order = values.get("min_order_amount")
    min_order = ZERO if min_order in (None, "") else _decimal(min_order, fields, "min_order_amount", "Nhập đơn tối thiểu.")
    if min_order is not None and (min_order < ZERO or min_order != min_order.to_integral_value()):
        fields["min_order_amount"] = "Đơn tối thiểu phải là số tiền nguyên đồng, từ 0 trở lên."
    out["min_order_amount"] = min_order

    starts_at, ends_at = values.get("starts_at"), values.get("ends_at")
    if not hasattr(starts_at, "tzinfo"):
        starts_at = _datetime(starts_at, fields, "starts_at")
    if not hasattr(ends_at, "tzinfo"):
        ends_at = _datetime(ends_at, fields, "ends_at")
    if starts_at and ends_at and starts_at >= ends_at:
        fields["ends_at"] = "Giờ kết thúc phải sau giờ bắt đầu."
    out["starts_at"], out["ends_at"] = starts_at, ends_at

    total_uses = values.get("total_uses")
    try:
        total_uses = int(Decimal(str(total_uses).strip()))
        if total_uses < 1 or Decimal(str(values.get("total_uses")).strip()) != total_uses:
            raise ValueError
    except (InvalidOperation, ValueError, TypeError):
        fields["total_uses"] = "Tổng lượt phải là số nguyên từ 1 trở lên."
        total_uses = None
    out["total_uses"] = total_uses

    terms = str(values.get("customer_terms") or "").strip()
    if len(terms) > TERMS_MAX:
        fields["customer_terms"] = f"Tối đa {TERMS_MAX} ký tự."
    elif has_long_digit_run(terms):
        fields["customer_terms"] = "Không ghi số điện thoại hay dãy số dài trong điều kiện cho khách."
    out["customer_terms"] = terms

    if fields:
        raise _validation_error(fields)
    return out


def _audit_value(value):
    """Tiền ghi nhật ký cùng một dạng với API ("10", "300000"), không phụ thuộc Decimal vừa nhập hay vừa đọc từ DB."""
    return money_str(value) if isinstance(value, Decimal) else value


def _audit_values(voucher) -> dict:
    return {
        key: _audit_value(getattr(voucher, key))
        for key in ("code", "name", "kind", "value", "max_discount", "min_order_amount", "starts_at", "ends_at",
                    "total_uses")
    }


# --- ERP: tạo, sửa, tắt, bật ------------------------------------------------------------------------------------

@transaction.atomic
def create_voucher(*, actor, data) -> Voucher:
    """SHOP-3b-01 AC1–AC3, BR-DM-17, 21. `customer_terms` chỉ để hiện cho khách nên không vào nhật ký."""
    clean = _clean_all(data)
    voucher = Voucher.objects.create(created_by=actor, **clean)
    record_audit(
        "create_voucher", actor=actor, obj=voucher,
        changes={key: {"from": None, "to": value} for key, value in _audit_values(voucher).items()},
    )
    return voucher


def _same(current, sent):
    if isinstance(current, Decimal):
        try:
            return current == Decimal(str(sent))
        except InvalidOperation:
            return False
    if hasattr(current, "tzinfo"):
        parsed = parse_datetime(sent) if isinstance(sent, str) else sent
        return parsed is not None and (timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed) == current
    if isinstance(current, int):
        try:
            return current == int(Decimal(str(sent)))
        except InvalidOperation:
            return False
    return current == sent


@transaction.atomic
def update_voucher(*, voucher, actor, data, now=None) -> Voucher:
    """
    BR-DM-22. TRƯỚC `starts_at`: sửa tự do mọi trường trừ `code`, `kind` (khoá vĩnh viễn -> FIELD_LOCKED).
    TỪ `starts_at`: `name` tuỳ ý; `ends_at` chỉ lùi về sau; `total_uses` chỉ tăng; `min_order_amount` chỉ giảm;
    `value`, `max_discount` chỉ tăng; trường khác -> FIELD_LOCKED; ngược hướng -> UNFAVORABLE_CHANGE.
    """
    now = now or timezone.now()
    voucher = Voucher.objects.select_for_update().get(pk=voucher.pk)
    started = now >= voucher.starts_at
    sent = {key: data[key] for key in EDITABLE if key in data}
    if "is_active" in data and bool(data["is_active"]) != voucher.is_active:
        sent["is_active"] = data["is_active"]
    if "code" in sent:
        sent["code"] = normalize_code(sent["code"])
    changed = {
        key: value for key, value in sent.items()
        if key == "is_active" or not _same(getattr(voucher, key), value)
    }
    if not changed:
        return voucher

    if "is_active" in changed:
        raise BusinessError(
            "Dùng nút Tắt mã hoặc Bật lại mã, không sửa trạng thái ở đây.", code=FIELD_LOCKED,
            extra={"fields": ["is_active"]},
        )
    always_locked = {"code", "kind"}
    locked = [k for k in changed if k in always_locked]
    if started:
        locked += [k for k in changed if k not in always_locked and k not in
                   {"name", "ends_at", "total_uses", "min_order_amount", "value", "max_discount"}]
    if locked:
        raise BusinessError(LOCKED_DETAIL, code=FIELD_LOCKED, extra={"fields": sorted(set(locked))})

    merged = {key: getattr(voucher, key) for key in EDITABLE}
    merged.update(changed)
    clean = _clean_all(merged, instance=voucher)

    if started:
        unfavorable = []
        if "ends_at" in changed and clean["ends_at"] < voucher.ends_at:
            unfavorable.append("ends_at")
        if "total_uses" in changed and clean["total_uses"] < voucher.total_uses:
            unfavorable.append("total_uses")
        if "min_order_amount" in changed and clean["min_order_amount"] > voucher.min_order_amount:
            unfavorable.append("min_order_amount")
        if "value" in changed and clean["value"] < voucher.value:
            unfavorable.append("value")
        if "max_discount" in changed and (voucher.max_discount is None or clean["max_discount"] is None
                                          or clean["max_discount"] < voucher.max_discount):
            unfavorable.append("max_discount")
        if unfavorable:
            raise BusinessError(UNFAVORABLE_DETAIL, code=UNFAVORABLE_CHANGE, extra={"fields": unfavorable})

    changes = {}
    for key in changed:
        if key == "customer_terms":
            changes[key] = {"changed": True}  # chữ hiển thị cho khách, không chép vào nhật ký
            setattr(voucher, key, clean[key])
            continue
        changes[key] = {"from": _audit_value(getattr(voucher, key)), "to": _audit_value(clean[key])}
        setattr(voucher, key, clean[key])
    voucher.save(update_fields=[*changed, "updated_at"])
    record_audit("update_voucher", actor=actor, obj=voucher, changes=changes)
    return voucher


@transaction.atomic
def disable_voucher(*, voucher, actor, reason_code, note="") -> Voucher:
    """BR-DM-22: `reason` bắt buộc; OTHER bắt buộc `note`. Mã không bị xoá; đơn đang giữ lượt vẫn giữ giá đóng băng."""
    note = str(note or "").strip()
    fields = {}
    if reason_code not in Voucher.DisabledReason.values:
        fields["reason"] = "Chọn lý do tắt mã."
    elif reason_code == Voucher.DisabledReason.OTHER and not note:
        fields["note"] = "Ghi rõ lý do khác."
    if len(note) > NOTE_MAX:
        fields["note"] = f"Tối đa {NOTE_MAX} ký tự."
    elif has_long_digit_run(note):
        fields["note"] = "Không ghi số điện thoại hay số tài khoản vào ghi chú."
    if fields:
        raise _validation_error(fields)
    voucher = Voucher.objects.select_for_update().get(pk=voucher.pk)
    if not voucher.is_active:
        return voucher  # idempotent: giữ lý do đã ghi lần đầu
    voucher.is_active = False
    voucher.disabled_reason = reason_code
    voucher.disabled_note = note
    voucher.save(update_fields=["is_active", "disabled_reason", "disabled_note", "updated_at"])
    record_audit(
        "disable_voucher", actor=actor, obj=voucher,
        changes={"is_active": {"from": True, "to": False}, "reason_code": reason_code, "note_marker": note_marker(note)},
    )
    return voucher


@transaction.atomic
def enable_voucher(*, voucher, actor, now=None) -> Voucher:
    """V-12: bật lại được khi còn hạn và còn lượt; hết hạn -> EXPIRED, hết lượt -> USED_UP."""
    now = now or timezone.now()
    voucher = Voucher.objects.select_for_update().get(pk=voucher.pk)
    if voucher.is_active:
        return voucher
    if now >= voucher.ends_at:
        raise BusinessError("Mã đã hết hạn, không bật lại được. Tạo mã mới.", code=REASON_EXPIRED)
    if committed_count(voucher) >= voucher.total_uses:
        raise BusinessError("Mã đã hết lượt, không bật lại được. Tạo mã mới.", code=REASON_USED_UP)
    voucher.is_active = True
    voucher.disabled_reason = ""
    voucher.disabled_note = ""
    voucher.save(update_fields=["is_active", "disabled_reason", "disabled_note", "updated_at"])
    record_audit(
        "enable_voucher", actor=actor, obj=voucher, changes={"is_active": {"from": False, "to": True}},
    )
    return voucher


# --- Truy vấn cho ERP -----------------------------------------------------------------------------------------

def with_counts(queryset):
    """Gắn `used_count`, `held_count` (đếm một lần bằng JOIN, không N+1)."""
    from apps.sales.models import VoucherRedemption

    return queryset.annotate(
        used_count=Count("redemptions", filter=Q(redemptions__state=VoucherRedemption.State.USED)),
        held_count=Count("redemptions", filter=Q(redemptions__state=VoucherRedemption.State.HELD)),
    )


def filter_by_status(queryset, status, *, now):
    """`queryset` đã qua `with_counts`. Lọc theo đúng thứ tự ưu tiên của `voucher_status`."""
    if status == STATUS_PAUSED:
        return queryset.filter(is_active=False)
    queryset = queryset.filter(is_active=True)
    if status == STATUS_EXPIRED:
        return queryset.filter(ends_at__lte=now)
    queryset = queryset.filter(ends_at__gt=now)
    if status == STATUS_USED_UP:
        return queryset.filter(used_count__gte=F("total_uses") - F("held_count"))
    queryset = queryset.exclude(used_count__gte=F("total_uses") - F("held_count"))
    if status == STATUS_SCHEDULED:
        return queryset.filter(starts_at__gt=now)
    return queryset.filter(starts_at__lte=now)  # running

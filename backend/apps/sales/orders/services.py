"""
Đơn hàng (P-05 giữ chỗ, TTL; P-07 huỷ đơn đã thanh toán) — TÀI CHÍNH + KHO.

Chữ ký hàm bám BUILD-PLAN.md "Contract A". Biến động kho đi qua
inventory.batches/stock services (không viết lại chọn lô FEFO/giữ chỗ/sổ). Lỗi nghiệp vụ ->
BusinessError. actor=None nghĩa là Hệ thống.

- create_order          : 7.1 gộp Customer theo phone (customers.services); BR-DM-02 giá
                          ItemPrice hiệu lực; BR-DM-08 áp DUY NHẤT 1 PricingRule lợi nhất;
                          BR-BH-05/06 FEFO + phân bổ lô; BR-BH-07 BUNDLE giữ chỗ đồng thời
                          mọi thành phần; BR-BH-08/DM-07 đóng băng giá & công thức.
- cancel_unpaid_expired : job TTL BR-BH-03/04 — idempotent, actor=None.
- cancel_paid_order     : hoàn kho lô gốc (CANCEL_RESTORE), audit (BR-HT-05).
"""
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.catalog.items import services as catalog_stock
from apps.catalog.models import Item, ItemPrice, PricingRule
from apps.catalog.pricing.services import effective_price as listed_price
from apps.common.audit import note_marker, record_audit
from apps.common.exceptions import BusinessError
from apps.common.pii import has_long_digit_run
from apps.delivery.models import DeliveryNote
from apps.inventory.batches import services as batches
from apps.inventory.models import Batch, StockLedgerEntry
from apps.inventory.stock import services as stock
from apps.sales.credit_notes import services as credit_note_services
from apps.sales.customers import services as customers
from apps.sales.models import SalesOrder, SalesOrderLine, SalesOrderLineBatch
from apps.sales.orders.consent import resolve_privacy_consent
from apps.sales.orders.shop_errors import LEVEL_OUT, LEVEL_SHORT, InvalidQtyError, OutOfStockError
from apps.sales.utils import ZERO
from apps.sales.utils import gen_code as _gen_code
from apps.sales.utils import money as _q
from apps.sales.utils import money_str
from apps.sales.utils import money_vnd as _q_vnd
from apps.sales.utils import now as _now


# --- giá & ưu đãi -----------------------------------------------------------

def _effective_price(item, on_date):
    """
    Giá bán lấy từ ItemPrice hiệu lực tại on_date (BR-DM-02):
    valid_from <= on_date <= valid_upto (valid_upto None = vô hạn).
    Ưu tiên bảng giá mặc định; trong cùng bảng lấy khoảng hiệu lực mới nhất.
    """
    price = (
        ItemPrice.objects.filter(item=item, valid_from__lte=on_date)
        .filter(Q(valid_upto__isnull=True) | Q(valid_upto__gte=on_date))
        .order_by("-price_list__is_default", "-valid_from", "-id")
        .first()
    )
    if price is None:
        raise BusinessError(
            f"Không có giá niêm yết hiệu lực cho {item.code} tại {on_date} (BR-DM-02)."
        )
    return price.rate


def _rule_discount(rule, base):
    """Số tiền giảm của một rule trên `base` (đã làm tròn, không vượt base)."""
    if rule.discount_type == PricingRule.DiscountType.PERCENT:
        d = _q(base * rule.discount_value / Decimal("100"))
    else:  # AMOUNT
        d = _q(rule.discount_value)
    return min(d, _q(base))


def _rule_active(rule, on_date):
    if not rule.is_active:
        return False
    if rule.valid_from and on_date < rule.valid_from:
        return False
    if rule.valid_upto and on_date > rule.valid_upto:
        return False
    return True


def _best_pricing_rule(lines_data, on_date):
    """
    BR-DM-08: nhiều PricingRule cùng khớp -> áp DUY NHẤT rule có lợi nhất cho khách,
    KHÔNG cộng dồn. Trả (rule, {line_index: discount_amount}) hoặc None.

    lines_data: list[dict] mỗi phần tử {"item": Item, "qty": Decimal, "gross": Decimal}.
    - Rule ITEM: khớp dòng có item trùng và qty >= min_qty; giảm trên gross của dòng đó.
    - Rule ORDER: khớp khi tổng gross >= min_amount; giảm trên tổng, phân bổ theo tỉ lệ gross.
    """
    gross_total = sum((ld["gross"] for ld in lines_data), ZERO)
    if gross_total <= ZERO:
        return None

    candidates = []  # (total_discount, rule.pk, rule, {idx: discount})
    for rule in PricingRule.objects.all():
        if not _rule_active(rule, on_date):
            continue

        if rule.apply_on == PricingRule.ApplyOn.ITEM:
            per_line = {}
            for idx, ld in enumerate(lines_data):
                if ld["item"].pk != rule.item_id:
                    continue
                if rule.min_qty is not None and ld["qty"] < rule.min_qty:
                    continue
                d = _rule_discount(rule, ld["gross"])
                if d > ZERO:
                    per_line[idx] = d
            total = sum(per_line.values(), ZERO)
            if total > ZERO:
                candidates.append((total, rule.pk, rule, per_line))

        else:  # ORDER
            if rule.min_amount is None or gross_total < rule.min_amount:
                continue
            total = _rule_discount(rule, gross_total)
            if total <= ZERO:
                continue
            per_line = _distribute(total, lines_data, gross_total)
            candidates.append((total, rule.pk, rule, per_line))

    if not candidates:
        return None
    # Lợi nhất cho khách = giảm nhiều nhất; hoà thì rule pk nhỏ hơn (ổn định).
    best = max(candidates, key=lambda c: (c[0], -c[1]))
    return best[2], best[3]


def _distribute(total, lines_data, gross_total):
    """Phân bổ `total` (giảm giá theo đơn) về từng dòng theo tỉ lệ gross; dư dồn dòng cuối."""
    per_line = {}
    allocated = ZERO
    n = len(lines_data)
    for idx, ld in enumerate(lines_data):
        if idx == n - 1:
            per_line[idx] = _q(total - allocated)
        else:
            share = _q(total * ld["gross"] / gross_total)
            per_line[idx] = share
            allocated += share
    return per_line


def _bundle_components(item, line_qty):
    """
    Nổ BUNDLE thành [(component_item, qty_kg)] theo BundleLine (định mức × số combo).
    Trả thêm snapshot công thức để đóng băng trên dòng đơn (BR-BH-08 / BR-DM-07).
    """
    bundle_lines = list(item.bundle_lines.select_related("component"))
    if not bundle_lines:
        raise BusinessError(f"Combo {item.code} chưa có công thức thành phần.")
    components = []
    snapshot = {"item_type": "BUNDLE", "components": []}
    for bl in bundle_lines:
        comp_qty = bl.qty_per_bundle * line_qty
        components.append((bl.component, comp_qty))
        snapshot["components"].append(
            {
                "component_code": bl.component.code,
                "component_name": bl.component.name,
                "qty_per_bundle": str(bl.qty_per_bundle),
            }
        )
    return components, snapshot


# --- SHOP-2-02: kiểm số lượng và tồn trước khi giữ chỗ -----------------------------------

BR_NOT_ENOUGH_STOCK = "BR-BH-02"


def _resolve_lines(lines):
    """[(raw_line, item hoặc None, qty Decimal)] — mã không tồn tại cho item = None (xử lý như hết hàng)."""
    codes = {raw["item_code"] for raw in lines}
    items = {it.code: it for it in Item.objects.filter(code__in=codes)}
    return [(raw, items.get(raw["item_code"]), Decimal(str(raw["qty"]))) for raw in lines]


def _check_line_quantities(resolved):
    """BR-BH-22: liệt kê MỌI dòng sai mức tối thiểu/bước, trước khi ghi DB hay giữ chỗ."""
    bad = []
    for raw, item, qty in resolved:
        if item is not None and not catalog_stock.validate_line_qty(item, qty):
            min_qty, qty_step = catalog_stock.qty_rule(item)
            bad.append(
                {"item_code": item.code, "min_qty": money_str(min_qty), "qty_step": money_str(qty_step)}
            )
    if bad:
        raise InvalidQtyError(bad)


def _demand_parts(item, qty):
    """[(thành phần, kg cần)] của một dòng; None nếu combo chưa có công thức (không bán được)."""
    if not item.is_bundle:
        return [(item, qty)]
    lines = list(item.bundle_lines.select_related("component"))
    if not lines:
        return None
    return [(bl.component, bl.qty_per_bundle * qty) for bl in lines]


def _out_of_stock_lines(resolved, today):
    """
    BR-BH-24: các dòng không đủ hàng, chỉ gồm mã hàng và mức "out" | "short" (không số kg, không mã lô).
    Cộng nhu cầu kg THEO THÀNH PHẦN của mọi dòng (SIMPLE = chính nó; BUNDLE = định mức × số combo) rồi so với
    tồn bán được của thành phần. Món ngưng bán, không giá hiệu lực hoặc không có mã -> "out".
    """
    per_line = []        # (item_code, item hoặc None, parts hoặc None)
    demand = {}          # pk thành phần -> [thành phần, tổng kg cần]
    for raw, item, qty in resolved:
        sellable = item is not None and item.is_active and listed_price(item, today) is not None
        parts = _demand_parts(item, qty) if sellable else None
        per_line.append((raw["item_code"], item, parts))
        for component, kg in parts or ():
            demand.setdefault(component.pk, [component, ZERO])[1] += kg
    shortage = {
        pk for pk, (component, kg) in demand.items() if kg > catalog_stock.simple_sellable_qty(component)
    }
    result = []
    for code, item, parts in per_line:
        if parts is None:
            result.append({"item_code": code, "stock_level": LEVEL_OUT})
        elif any(component.pk in shortage for component, _kg in parts):
            level = LEVEL_OUT if catalog_stock.stock_level(item) == catalog_stock.STOCK_OUT else LEVEL_SHORT
            result.append({"item_code": code, "stock_level": level})
    return result


# --- P-05: tạo đơn (giữ chỗ) ------------------------------------------------

def create_order(
    *,
    customer_phone,
    customer_name,
    delivery_address,
    phone,
    lines,
    privacy_consent=None,
    client_request_id=None,
):
    """
    Tạo đơn ở trạng thái BOOKED — do Hệ thống tạo (BR-PQ-11). TẤT CẢ trong 1 transaction:
    thiếu tồn 1 thành phần bất kỳ -> cả đơn fail (BR-BH-02/07).

    lines: list[{"item_code": str, "qty": Decimal}]. `qty` của combo là SỐ COMBO (nguyên), của món thường là kg.

    Lỗi Shop có cấu trúc (02b §3.3, đều xảy ra trước khi ghi DB hoặc giữ chỗ, rollback cả đơn):
    `InvalidQtyError` (BR-BH-22), `PolicyChanged` (BR-BH-17) rồi `OutOfStockError` (BR-BH-24).

    `client_request_id` (BR-BH-27): ghi vào đơn; unique ở DB. Hai request cùng mã: request sau bị chặn ở unique index
    và nhận `IntegrityError` — `place_order` bắt NGOÀI `atomic` này và trả đơn đã có.
    """
    if not delivery_address:
        raise BusinessError("Địa chỉ giao bắt buộc (BR-BH-09).")
    if not lines:
        raise BusinessError("Đơn hàng phải có ít nhất một dòng.")

    # BR-BH-22: kiểm số lượng ở máy chủ, trước giữ chỗ và trước mọi ghi DB.
    resolved = _resolve_lines(lines)
    _check_line_quantities(resolved)

    # Kiểm tra đồng ý chính sách bảo mật trước khi giữ chỗ hoặc ghi DB (GL-03, BR-BH-17)
    policy_version = resolve_privacy_consent(privacy_consent)

    today = timezone.localdate()
    now = _now()

    with transaction.atomic():
        # BR-BH-24: kiểm đủ hàng theo thành phần trước khi ghi gì (chưa khoá; `reserve` bên dưới mới là nguồn quyết định).
        out_of_stock = _out_of_stock_lines(resolved, today)
        if out_of_stock:
            raise OutOfStockError(out_of_stock)

        # 7.1 — gộp/khởi tạo Customer theo số điện thoại (khoá tự nhiên).
        customer = customers.get_or_create_by_phone(
            phone=customer_phone, name=customer_name, default_address=delivery_address,
        )

        order = SalesOrder.objects.create(
            code=_gen_code("SO", SalesOrder),
            customer=customer,
            status=SalesOrder.Status.BOOKED,
            delivery_address=delivery_address,
            phone=phone or customer_phone,
            total_amount=ZERO,
            booked_expires_at=now
            + timezone.timedelta(minutes=settings.SALES_ORDER_TTL_MINUTES),
            privacy_consent_at=timezone.now() if policy_version else None,
            privacy_policy_version=policy_version,
            client_request_id=client_request_id,
        )

        # Bước 1: dựng dữ liệu dòng + giá (đóng băng), chưa áp ưu đãi.
        lines_data = []
        for raw, item, qty in resolved:
            rate = _effective_price(item, today)  # BR-DM-02 (BUNDLE dùng giá độc lập, BR-DM-04)
            gross = _q(qty * rate)
            lines_data.append({"item": item, "qty": qty, "rate": rate, "gross": gross})

        # Bước 2: chọn DUY NHẤT 1 PricingRule lợi nhất (BR-DM-08).
        best = _best_pricing_rule(lines_data, today)
        rule = None
        per_line_discount = {}
        if best is not None:
            rule, per_line_discount = best

        # Bước 3: tạo dòng đơn + giữ chỗ từng thành phần (FEFO, BR-BH-05). Thiếu tồn -> rollback cả đơn.
        total = ZERO
        for idx, ld in enumerate(lines_data):
            item = ld["item"]
            discount = per_line_discount.get(idx, ZERO)
            amount = _q(ld["gross"] - discount)

            if item.is_bundle:
                components, snapshot = _bundle_components(item, ld["qty"])
            else:
                components, snapshot = [(item, ld["qty"])], {}

            order_line = SalesOrderLine.objects.create(
                order=order,
                item=item,
                qty=ld["qty"],
                rate=ld["rate"],
                bundle_snapshot=snapshot,
                pricing_rule=rule if discount > ZERO else None,
                discount_amount=discount,
                amount=amount,
            )

            # BR-BH-07: giữ chỗ ĐỒNG THỜI mọi thành phần. Vì cùng transaction, thiếu 1
            # thành phần -> BusinessError -> rollback toàn bộ đơn.
            for component_item, comp_qty in components:
                try:
                    allocation = batches.allocate_fefo(item=component_item, qty=comp_qty)
                    for batch, take in allocation:
                        batches.reserve(batch=batch, qty=take)  # khoá lô, người sau thua (BR-BH-02)
                        fresh = Batch.objects.get(pk=batch.pk)
                        SalesOrderLineBatch.objects.create(
                            order_line=order_line,
                            batch=batch,
                            component_item=component_item,
                            qty=take,
                            unit_cost=fresh.landed_unit_cost,  # ảnh chụp giá vốn lúc đặt
                        )
                except OutOfStockError:
                    raise
                except BusinessError as exc:
                    if exc.code != BR_NOT_ENOUGH_STOCK:
                        raise
                    # Thua đua lúc giữ chỗ: ném lỗi theo từng dòng (rollback cả đơn), không lộ lô hay số kg.
                    level = (
                        LEVEL_OUT
                        if catalog_stock.stock_level(item) == catalog_stock.STOCK_OUT
                        else LEVEL_SHORT
                    )
                    raise OutOfStockError([{"item_code": item.code, "stock_level": level}]) from None
            total += amount

        # BR-BH-15 (Q6): tổng đơn là số NGUYÊN ĐỒNG, half-up — dòng đơn vẫn giữ 2 chữ số
        # thập phân (_q) như trước; chỉ tổng cuối cùng làm tròn để khớp số gửi cổng SePay.
        order.total_amount = _q_vnd(total)
        order.save(update_fields=["total_amount"])

    return order


def find_by_client_request_id(client_request_id):
    if client_request_id is None:
        return None
    return SalesOrder.objects.filter(client_request_id=client_request_id).first()


def place_order(*, client_request_id=None, **kwargs):
    """
    Tạo đơn Shop chống trùng (BR-BH-27). Trả `(order, created)`; `created=False` khi `client_request_id` đã có đơn
    (kể cả hai request song song: request thua đua nhận `IntegrityError` ngoài transaction rồi đọc đơn đã commit).
    Gửi lại KHÔNG giữ chỗ hay lượt thêm. Request đầu rollback (hết hàng...) thì request sau chạy bình thường.
    """
    existing = find_by_client_request_id(client_request_id)
    if existing is not None:
        return existing, False
    try:
        return create_order(client_request_id=client_request_id, **kwargs), True
    except IntegrityError:
        existing = find_by_client_request_id(client_request_id)
        if existing is None:
            raise
        return existing, False


# --- P-05: job TTL nhả giữ chỗ ----------------------------------------------

def cancel_unpaid_expired(*, now=None):
    """
    Quét đơn BOOKED quá booked_expires_at -> AUTO_CANCELLED + nhả mọi giữ chỗ.
    IDEMPOTENT (BR-BH-04): chạy lại không huỷ nhầm đơn đã xử lý. Actor = Hệ thống (None).
    Trả số đơn đã huỷ trong lần chạy này.
    """
    now = now or _now()
    cancelled = 0
    expired_ids = list(
        SalesOrder.objects.filter(
            status=SalesOrder.Status.BOOKED, booked_expires_at__lt=now
        ).values_list("pk", flat=True)
    )
    for pk in expired_ids:
        with transaction.atomic():
            o = SalesOrder.objects.select_for_update().get(pk=pk)
            if o.status != SalesOrder.Status.BOOKED:
                continue  # đã bị xử lý bởi lần chạy khác — idempotent
            for line in o.lines.all():
                for res in line.batch_allocations.select_related("batch"):
                    batches.release(batch=res.batch, qty=res.qty)
            o.status = SalesOrder.Status.AUTO_CANCELLED
            o.save(update_fields=["status"])
            record_audit("cancel_unpaid_expired", actor=None, obj=o)
            cancelled += 1
    return cancelled


# --- P-07: huỷ đơn đã thanh toán --------------------------------------------

# S14 (BR-GH-07): lý do huỷ đơn đã thanh toán. OTHER bắt buộc `note` đi kèm (kiểm ở API).
CANCEL_REASON_LABELS = {
    "CUSTOMER_CHANGED_MIND": "Khách đổi ý",
    "DAMAGED_WHEN_PACKING": "Hàng hư lúc soạn hàng",
    "GIVE_UP_AFTER_FAILED": "Giao thất bại, không giao lại",
    "UNREACHABLE": "Không liên lạc được khách",
    "OTHER": "Lý do khác",
}
CANCEL_REASON_CODES = set(CANCEL_REASON_LABELS)

SYSTEM_CANCEL_REASON_CODES = {
    "UNREACHABLE_AUTO": "Hệ thống tự huỷ: không liên lạc được khách",
}
ALL_CANCEL_REASON_CODES = set(CANCEL_REASON_LABELS) | set(SYSTEM_CANCEL_REASON_CODES)

# Trạng thái phiếu giao còn giữ hàng TẠI KHO — huỷ ở đây thì hoàn kho được ngay.
_STOCK_STILL_IN_WAREHOUSE = (
    DeliveryNote.Status.CONFIRMING,
    DeliveryNote.Status.PREPARING,
    DeliveryNote.Status.READY,
)


CANCEL_NOTE_MAX = 200


def _cancel_audit_note(reason_code, cancel_note):
    """Nhật ký chỉ ghi nhãn lý do + "có ghi chú"; chữ gốc ở `SalesOrder.cancel_note` (bất biến 9)."""
    if not reason_code:
        return ""
    text = f"Huỷ đơn: {CANCEL_REASON_LABELS.get(reason_code, 'Không rõ')}"
    marker = note_marker(cancel_note)
    return f"{text} · {marker}" if marker else text


def cancel_paid_order(*, order, actor, reason="", reason_code="", cancel_note=""):
    """
    Huỷ đơn đã thanh toán (BR-HT-05, BR-GH-07): chặn khi phiếu giao đang Đang giao
    (BR-GH-07) hoặc đã Hoàn tất (BR-GH-05, không quay lui — chỉ còn cách lập phiếu hoàn).

    Hoàn kho về ĐÚNG lô gốc theo SalesInvoiceLineBatch (record_movement CANCEL_RESTORE
    +qty) CHỈ khi hàng còn ở kho (phiếu Soạn hàng/Chờ lấy hàng). Phiếu Giao thất bại thì
    hàng đang ở người giao hoặc chờ duyệt hàng hoàn (P-08) — KHÔNG hoàn kho ở đây, để tránh
    cộng kho hai lần khi hàng hoàn đó sau này được duyệt nhập lại (Q8b).

    Kho và tiền là hai sổ tách nhau — hoàn tiền đi riêng qua create_refund/confirm_refund.
    Doanh thu đảo bằng chứng từ đảo (BR-HT-10) lập NGAY tại thời điểm huỷ, trong cùng
    transaction (lỗi thì cả lần huỷ rollback); hoá đơn gốc giữ nguyên ISSUED (BR-HT-06).
    Phiếu hoàn chỉ là dòng tiền, không đảo doanh thu. Trả dict {"order", "stock_restored", "delivery_note"}.

    Tham số `reason` không còn được dùng (chữ lý do nay là `cancel_note`, lưu ở đơn); giữ lại chỉ để
    các nơi gọi cũ (chủ yếu test) không vỡ. Luồng sản phẩm không truyền nữa.
    """
    cancel_note = (cancel_note or "").strip()
    if len(cancel_note) > CANCEL_NOTE_MAX:
        raise BusinessError(f"Ghi chú huỷ tối đa {CANCEL_NOTE_MAX} ký tự.", code="BR-GH-19")
    if has_long_digit_run(cancel_note):
        raise BusinessError("Không ghi SĐT hay số tài khoản vào ghi chú huỷ.", code="BR-GH-19")
    with transaction.atomic():
        o = SalesOrder.objects.select_for_update().get(pk=order.pk)
        if o.status == SalesOrder.Status.COMPLETED:
            # W37 S2: đơn đã Hoàn tất (giao xong thắng cuộc đua) — không quay lui, chỉ còn phiếu hoàn.
            raise BusinessError(
                "Đơn đã giao hoàn tất — chỉ còn cách lập phiếu hoàn tiền.", code="BR-GH-05",
            )
        if o.status not in (SalesOrder.Status.PAID, SalesOrder.Status.PROCESSING):
            raise BusinessError("Chỉ huỷ được đơn đã thanh toán / đang xử lý (P-07).")
        invoice = getattr(o, "invoice", None)
        if invoice is None:
            raise BusinessError("Đơn đã thanh toán nhưng chưa có hoá đơn — không thể hoàn kho.")

        note = (
            DeliveryNote.objects.select_for_update()
            .filter(sales_invoice=invoice)
            .order_by("-id")
            .first()
        )
        if note is not None:
            if note.status == DeliveryNote.Status.DELIVERING:
                raise BusinessError(
                    "Phiếu giao đang Đang giao — báo giao thất bại trước khi huỷ.",
                    code="BR-GH-07",
                )
            if note.status == DeliveryNote.Status.COMPLETED:
                raise BusinessError(
                    "Đơn đã giao hoàn tất — chỉ còn cách lập phiếu hoàn tiền.", code="BR-GH-05",
                )

        stock_restored = note is None or note.status in _STOCK_STILL_IN_WAREHOUSE
        if stock_restored:
            for inv_line in invoice.lines.all():
                for silb in inv_line.batch_allocations.select_related("batch"):
                    stock.record_movement(
                        batch=silb.batch,
                        qty_change=silb.qty,  # +qty: hoàn về lô gốc (BR-HV-01 tinh thần)
                        movement_type=StockLedgerEntry.MovementType.CANCEL_RESTORE,
                        reference=f"cancel {o.code}",
                        actor=actor,
                    )

        old_status = o.status
        o.status = SalesOrder.Status.CANCELLED
        o.cancel_note = cancel_note
        o.save(update_fields=["status", "cancel_note"])

        if note is not None:
            note.status = DeliveryNote.Status.CANCELLED
            note.save(update_fields=["status"])
            from apps.delivery.confirmation import services as confirmation_services
            confirmation_services.close_task_on_cancel(note)

        record_audit(
            "cancel_paid_order", actor=actor, obj=o,
            changes={
                "status": {"from": old_status, "to": o.status},
                "stock_restored": stock_restored,
                "reason_code": reason_code,
            },
            note=_cancel_audit_note(reason_code, cancel_note),
        )
        credit_note_services.issue_cancel_credit_note(
            invoice=invoice, actor=actor, reason_code=reason_code,
            stock_restored=stock_restored,
        )
    return {"order": o, "stock_restored": stock_restored, "delivery_note": note}


# --- S10: thao tác được phép trên đơn (luật + quyền) --------------------------

def available_actions(*, order, user):
    """
    Danh sách thao tác `user` làm được trên `order` Ở TRẠNG THÁI HIỆN TẠI (quy ước contract
    `available_actions`). Tính lại từ next_steps của khối guidance (02c Lô 1a, DW-03).
    """
    from apps.sales.orders.next_steps import get_order_next_steps

    steps = get_order_next_steps(order=order, user=user)
    return [s.key for s in steps if s.allowed]


def _cancellable_delivery_status(invoice):
    """BR-GH-07/05: không cho huỷ khi phiếu giao đang Đang giao hoặc đã Hoàn tất/Đã huỷ."""
    notes = list(invoice.delivery_notes.all())  # Meta.ordering = -created_at,-id -> mới nhất trước
    if not notes:
        return True
    return notes[0].status not in (
        DeliveryNote.Status.DELIVERING, DeliveryNote.Status.COMPLETED, DeliveryNote.Status.CANCELLED,
    )



# --- nội bộ -----------------------------------------------------------------

def update_delivery_address(order: SalesOrder, address: str) -> None:
    """
    Cập nhật địa chỉ giao hàng của đơn (CS-12, 02b §4.5).
    Chỉ ghi đè delivery_address trên SalesOrder, không sửa phone hay Customer.
    """
    clean_address = (address or "").strip()
    if not clean_address:
        raise BusinessError("Địa chỉ giao hàng không được để trống.", code="INVALID_INPUT")
    if len(clean_address) > 500:
        raise BusinessError("Địa chỉ giao hàng không được vượt quá 500 ký tự.", code="INVALID_INPUT")

    order.delivery_address = clean_address
    order.save(update_fields=["delivery_address"])


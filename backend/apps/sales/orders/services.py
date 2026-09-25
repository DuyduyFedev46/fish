"""
Đơn hàng (P-05 giữ chỗ, TTL; P-07 huỷ đơn đã thanh toán) — TÀI CHÍNH + KHO.

Chữ ký hàm bám BUILD-PLAN.md "Contract A". Biến động kho đi qua
inventory.batches/stock services (không viết lại FIFO/giữ chỗ/sổ). Lỗi nghiệp vụ ->
BusinessError. actor=None nghĩa là Hệ thống.

- create_order          : 7.1 gộp Customer theo phone (customers.services); BR-DM-02 giá
                          ItemPrice hiệu lực; BR-DM-08 áp DUY NHẤT 1 PricingRule lợi nhất;
                          BR-BH-05/06 FIFO + phân bổ lô; BR-BH-07 BUNDLE giữ chỗ đồng thời
                          mọi thành phần; BR-BH-08/DM-07 đóng băng giá & công thức.
- cancel_unpaid_expired : job TTL BR-BH-03/04 — idempotent, actor=None.
- cancel_paid_order     : hoàn kho lô gốc (CANCEL_RESTORE), audit (BR-HT-05).
"""
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.catalog.models import Item, ItemPrice, PricingRule
from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError
from apps.inventory.batches import services as batches
from apps.inventory.models import Batch, StockLedgerEntry
from apps.inventory.stock import services as stock
from apps.sales.customers import services as customers
from apps.sales.models import SalesOrder, SalesOrderLine, SalesOrderLineBatch
from apps.sales.utils import ZERO
from apps.sales.utils import gen_code as _gen_code
from apps.sales.utils import money as _q
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


# --- P-05: tạo đơn (giữ chỗ) ------------------------------------------------

def create_order(*, customer_phone, customer_name, delivery_address, phone, lines):
    """
    Tạo đơn ở trạng thái BOOKED — do Hệ thống tạo (BR-PQ-11). TẤT CẢ trong 1 transaction:
    thiếu tồn 1 thành phần bất kỳ -> cả đơn fail (BR-BH-02/07).

    lines: list[{"item_code": str, "qty": Decimal}].
    """
    if not delivery_address:
        raise BusinessError("Địa chỉ giao bắt buộc (BR-BH-09).")
    if not lines:
        raise BusinessError("Đơn hàng phải có ít nhất một dòng.")

    today = timezone.localdate()
    now = _now()

    with transaction.atomic():
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
        )

        # Bước 1: dựng dữ liệu dòng + giá (đóng băng), chưa áp ưu đãi.
        lines_data = []
        for raw in lines:
            item = _get_item(raw["item_code"])
            qty = Decimal(str(raw["qty"]))
            if qty <= ZERO:
                raise BusinessError(f"Số lượng dòng {item.code} phải > 0.")
            rate = _effective_price(item, today)  # BR-DM-02 (BUNDLE dùng giá độc lập, BR-DM-04)
            gross = _q(qty * rate)
            lines_data.append({"item": item, "qty": qty, "rate": rate, "gross": gross})

        # Bước 2: chọn DUY NHẤT 1 PricingRule lợi nhất (BR-DM-08).
        best = _best_pricing_rule(lines_data, today)
        rule = None
        per_line_discount = {}
        if best is not None:
            rule, per_line_discount = best

        # Bước 3: tạo dòng đơn + giữ chỗ từng thành phần (FIFO). Thiếu tồn -> rollback cả đơn.
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
                allocation = batches.allocate_fifo(item=component_item, qty=comp_qty)
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
            total += amount

        order.total_amount = _q(total)
        order.save(update_fields=["total_amount"])

    return order


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

def cancel_paid_order(*, order, actor, reason=""):
    """
    Huỷ đơn đã thanh toán (BR-HT-05): hoàn kho về ĐÚNG lô gốc theo SalesInvoiceLineBatch
    (record_movement CANCEL_RESTORE +qty). Kho và tiền là hai sổ tách nhau — hoàn tiền
    đi riêng qua create_refund/confirm_refund. Doanh thu KHÔNG đảo ở đây (BR-HT-06:
    đảo tại thời điểm tạo phiếu hoàn, vào kỳ phát sinh hoàn).
    """
    with transaction.atomic():
        o = SalesOrder.objects.select_for_update().get(pk=order.pk)
        if o.status not in (SalesOrder.Status.PAID, SalesOrder.Status.PROCESSING):
            raise BusinessError("Chỉ huỷ được đơn đã thanh toán / đang xử lý (P-07).")
        invoice = getattr(o, "invoice", None)
        if invoice is None:
            raise BusinessError("Đơn đã thanh toán nhưng chưa có hoá đơn — không thể hoàn kho.")

        for inv_line in invoice.lines.all():
            for silb in inv_line.batch_allocations.select_related("batch"):
                stock.record_movement(
                    batch=silb.batch,
                    qty_change=silb.qty,  # +qty: hoàn về lô gốc (BR-HV-01 tinh thần)
                    movement_type=StockLedgerEntry.MovementType.CANCEL_RESTORE,
                    reference=f"cancel {o.code}",
                    actor=actor,
                )

        o.status = SalesOrder.Status.CANCELLED
        o.save(update_fields=["status"])
        record_audit(
            "cancel_paid_order", actor=actor, obj=o,
            changes={"status": {"from": SalesOrder.Status.PROCESSING, "to": o.status}},
            note=reason,
        )
    return o


# --- S10: thao tác được phép trên đơn (luật + quyền) --------------------------

def available_actions(*, order, user):
    """
    Danh sách thao tác `user` làm được trên `order` Ở TRẠNG THÁI HIỆN TẠI (quy ước contract
    `available_actions`). BE tính cả luật lẫn quyền; console chỉ đọc để hiện nút.

    - confirm_payment: đơn Giữ chỗ/Tự huỷ (BR-TT-08) + `sales.confirm_payment_manual` (BR-TT-07).
    - cancel         : đơn PAID/PROCESSING đã có hoá đơn (P-07) + `sales.cancel_paid_order`.
    - create_refund  : có hoá đơn, còn tiền chưa hoàn (BR-HT-04) + `sales.create_refund`.
    """
    from apps.sales.payments.services import MANUAL_CONFIRMABLE_STATUSES
    from apps.sales.refunds.services import refundable_amount

    actions = []
    invoice = getattr(order, "invoice", None)
    if (order.status in MANUAL_CONFIRMABLE_STATUSES
            and user.has_perm("sales.confirm_payment_manual")):
        actions.append("confirm_payment")
    if (order.status in (SalesOrder.Status.PAID, SalesOrder.Status.PROCESSING)
            and invoice is not None and user.has_perm("sales.cancel_paid_order")):
        actions.append("cancel")
    if (invoice is not None and user.has_perm("sales.create_refund")
            and refundable_amount(invoice=invoice) > ZERO):
        actions.append("create_refund")
    return actions


# --- nội bộ -----------------------------------------------------------------

def _get_item(item_code):
    try:
        return Item.objects.get(code=item_code)
    except Item.DoesNotExist:
        raise BusinessError(f"Không tìm thấy mặt hàng: {item_code}.")

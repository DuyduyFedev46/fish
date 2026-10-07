"""
Bộ dữ liệu giả CỐ ĐỊNH, TẤT ĐỊNH cho e2e chạy trên backend thật (`manage.py seed_qa`).

Quy ước (xem backend/README.md, mục seed_qa):
- Mọi mã có tiền tố `QA-` (đơn `QA-SO-nn`, hoá đơn `QA-HD-nn`, phiếu giao `QA-GH-nn`, lô `QA-LO-nn`, mặt hàng
  `QA-xxx`, giao dịch `QA-TXN-…`); tài khoản `qa_…`. Nhờ vậy `--reset` nhận ra đúng bản ghi QA (reset.py).
- Dữ liệu cá nhân HOÀN TOÀN GIẢ (bất biến 9): SĐT `09000000nn`, tên "Khách QA Giả nn", địa chỉ ghi rõ là giả.
- Cùng DB trống chạy hai lần cho cùng bảng mã → id; chạy lần hai không nhân đôi (mỗi kịch bản bỏ qua nếu mã đã có).
- Đi đúng đường nghiệp vụ khi được: giữ chỗ (`batches.reserve`), thanh toán (`payments.confirm_payment`,
  sinh hoá đơn + phân bổ lô + bút toán SALE + phiếu giao qua signal), huỷ đơn (`cancel_paid_order`), phiếu hoàn
  (`refunds.*`). Trạng thái phiếu giao và việc gọi xác nhận được đặt thẳng vì không có đường nghiệp vụ ngắn.
- Không đụng bản ghi không phải QA. Kho/bảng giá/nhóm hàng dùng chung (get_or_create theo tên) không bị reset xoá.

Giá vốn trong dữ liệu là số giả; không đưa dữ liệu thật vào đây.
"""
from datetime import timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.utils import timezone

from apps.accounts import roles
from apps.accounts.models import AuditLog, StaffProfile
from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.common.audit import record_audit
from apps.delivery.confirmation import call_scripts
from apps.delivery.models import CallScript, ConfirmationTask, CustomerCall, DeliveryNote
from apps.inventory.batches import services as batch_services
from apps.inventory.returns import services as return_services
from apps.inventory.models import (
    Batch,
    ReturnToStock,
    StockLedgerEntry,
    StockReconciliation,
    StockReconciliationLine,
    Warehouse,
)
from apps.purchasing.models import PurchaseReceipt, PurchaseReceiptLine, Supplier
from apps.sales.models import (
    Customer,
    PaymentTransaction,
    Refund,
    SalesInvoice,
    SalesOrder,
    SalesOrderLine,
    SalesOrderLineBatch,
)
from apps.sales.orders import services as order_services
from apps.sales.payments import services as payment_services
from apps.sales.refunds import services as refund_services

PREFIX = "QA-"
USER_PREFIX = "qa_"
PHONE_PREFIX = "09000000"
CALL_SCRIPT_PREFIX = "[QA] "
CUSTOMER_NAME_PREFIX = "Khách QA Giả"
SECTION_GROUP_NAME = "Hải sản"

# username, các Group, là superuser, tên hiển thị. Tổ hợp: K+G (kho + giao), K+C (kho + gọi xác nhận).
USERS = [
    ("qa_owner", [roles.OWNER], False, "QA Chủ vựa (giả)"),
    ("qa_manager", [roles.MANAGER], False, "QA Quản lý (giả)"),
    ("qa_warehouse", [roles.WAREHOUSE_STAFF], False, "QA Thủ kho (giả)"),
    ("qa_courier1", [roles.DELIVERY_STAFF], False, "QA Giao 1 (giả)"),
    ("qa_courier2", [roles.DELIVERY_STAFF], False, "QA Giao 2 (giả)"),
    ("qa_cs1", [roles.CUSTOMER_SERVICE], False, "QA Gọi xác nhận 1 (giả)"),
    ("qa_cs2", [roles.CUSTOMER_SERVICE], False, "QA Gọi xác nhận 2 (giả)"),
    ("qa_warehouse_courier", [roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF], False, "QA Kho+Giao (giả)"),
    ("qa_warehouse_cs", [roles.WAREHOUSE_STAFF, roles.CUSTOMER_SERVICE], False, "QA Kho+Gọi (giả)"),
    ("qa_nogroup", [], False, "QA Không nhóm (giả)"),
    ("qa_superuser", [], True, "QA Superuser (giả)"),
]

# code, tên, giá bán, giá vốn/kg (số giả)
ITEMS = [
    ("QA-CA", "Cá QA (giả)", 100000, 70000),
    ("QA-TOM", "Tôm QA (giả)", 200000, 150000),
    ("QA-MUC", "Mực QA (giả)", 150000, 100000),
    ("QA-GHE", "Ghẹ QA (giả)", 180000, 120000),
]

SUPPLIER_NAMES = ["QA-NCC Cảng Giả A", "QA-NCC Cảng Giả B"]

# batch_id, item, nhà cung cấp, nhập kg, tồn kg, ngày nhập (cách đây), hạn (còn, âm = quá hạn), status
BATCHES = [
    ("QA-LO-01", "QA-CA", 0, 500, 500, 3, 10, Batch.Status.SELLING),
    ("QA-LO-02", "QA-MUC", 1, 50, 50, 5, 1, Batch.Status.NEAR_EXPIRY),
    ("QA-LO-03", "QA-GHE", 0, Decimal("6.5"), Decimal("6.5"), 9, -2, Batch.Status.EXPIRED),
    ("QA-LO-04", "QA-CA", 1, 40, 40, 0, 15, Batch.Status.DRAFT),
    ("QA-LO-05", "QA-TOM", 0, 300, 300, 2, 9, Batch.Status.SELLING),
    ("QA-LO-06", "QA-TOM", 1, 20, 20, 20, -10, Batch.Status.CLOSED),
    ("QA-LO-07", "QA-MUC", 0, 30, 0, 12, 3, Batch.Status.SOLD_OUT),
    ("QA-LO-08", "QA-GHE", 1, 10, 0, 15, -5, Batch.Status.CANCELLED),
]
# Mặt hàng -> lô SELLING dùng cho các đơn.
ORDER_BATCH = {"QA-CA": "QA-LO-01", "QA-TOM": "QA-LO-05"}

CANCEL_NOTE_1 = "QA-huỷ đơn: khách đổi ý (giả)"
CANCEL_NOTE_2 = "QA-huỷ đơn: hàng hư lúc soạn (giả)"
FAKE_ADDRESS = "QA-Địa chỉ giả số {n}, đường Thử Nghiệm"


def order_code(n):
    return f"QA-SO-{n:02d}"


def invoice_code(n):
    return f"QA-HD-{n:02d}"


def note_code(n):
    return f"QA-GH-{n:02d}"


def txn_id(n, suffix=""):
    return f"QA-TXN-{n:02d}{('-' + suffix) if suffix else ''}"


def fake_phone(n):
    return f"{PHONE_PREFIX}{n:02d}"


class QaSeed:
    """Dựng bộ dữ liệu QA. Dùng: `QaSeed(password=...).run()` -> manifest (dict mã → id)."""

    def __init__(self, *, password, now=None):
        self.password = password
        self.now = now or timezone.now()
        self.today = timezone.localdate()
        self.users = {}
        self.items = {}
        self.batches = {}
        self.suppliers = []
        self.customers = {}
        self.orders = {}
        self.notes = {}
        self.payments = {}
        self.refunds = {}
        self.receipts = {}
        self.stocktakes = {}
        self.returns = {}
        self.scripts = {}
        self.warnings = []

    # ------------------------------------------------------------------ chạy
    @transaction.atomic
    def run(self):
        self._users()
        self._catalog()
        self._batches()
        self._scenarios()
        self._returns()
        self._receipts()
        self._stocktakes()
        self._call_scripts()
        self._audit_samples()
        return self.manifest()

    # ------------------------------------------------------------- tài khoản
    def _users(self):
        user_model = get_user_model()
        for username, group_names, is_super, display in USERS:
            user, created = user_model.objects.get_or_create(
                username=username, defaults={"is_active": True},
            )
            user.is_superuser = is_super
            user.is_staff = is_super
            user.is_active = True
            user.set_password(self.password)
            user.save()
            user.groups.set(Group.objects.filter(name__in=group_names))
            profile, _ = StaffProfile.objects.get_or_create(
                user=user,
                defaults={"phone": f"0900000{900 + len(self.users):03d}"[:10], "display_name": display},
            )
            if profile.must_change_password or profile.status != StaffProfile.Status.ACTIVE:
                profile.must_change_password = False
                profile.status = StaffProfile.Status.ACTIVE
                profile.save(update_fields=["must_change_password", "status"])
            self.users[username] = user

    # ---------------------------------------------------------------- danh mục
    def _catalog(self):
        self.warehouse = Warehouse.objects.order_by("id").first() or Warehouse.objects.create(name="Kho chính")
        price_list = (PriceList.objects.filter(is_default=True).first()
                      or PriceList.objects.order_by("id").first()
                      or PriceList.objects.create(name="Bán lẻ", is_default=True))
        group, _ = ItemGroup.objects.get_or_create(name=SECTION_GROUP_NAME)
        for code, name, price, _cost in ITEMS:
            item, _ = Item.objects.get_or_create(
                code=code,
                defaults=dict(name=name, item_group=group, item_type=Item.ItemType.SIMPLE,
                              shelf_life_in_days=15, is_active=True),
            )
            self.items[code] = item
            if not ItemPrice.objects.filter(price_list=price_list, item=item).exists():
                ItemPrice.objects.create(price_list=price_list, item=item, rate=Decimal(price),
                                         valid_from=self.today - timedelta(days=30))
        self.rates = {code: Decimal(price) for code, _n, price, _c in ITEMS}
        self.costs = {code: Decimal(cost) for code, _n, _p, cost in ITEMS}
        for sname in SUPPLIER_NAMES:
            sup, _ = Supplier.objects.get_or_create(
                name=sname, defaults={"phone": "0900000990", "note": "QA-nhà cung cấp giả"})
            self.suppliers.append(sup)
        for n in range(1, 21):
            self.customers[n], _ = Customer.objects.get_or_create(
                phone=fake_phone(n),
                defaults=dict(name=f"{CUSTOMER_NAME_PREFIX} {n:02d}", default_address=FAKE_ADDRESS.format(n=n)),
            )

    def _batches(self):
        for batch_id, icode, sidx, qty_in, qty_stock, ago, left, status in BATCHES:
            cost = self.costs[icode]
            batch, created = Batch.objects.get_or_create(
                batch_id=batch_id,
                defaults=dict(
                    item=self.items[icode], supplier=self.suppliers[sidx], warehouse=self.warehouse,
                    received_date=self.today - timedelta(days=ago),
                    expiry_date=self.today + timedelta(days=left),
                    qty_received=Decimal(qty_in), qty_available=Decimal(qty_stock),
                    qty_reserved=Decimal("0"), purchase_rate=cost, landed_unit_cost=cost, status=status,
                ),
            )
            if created:
                StockLedgerEntry.objects.create(
                    batch=batch, movement_type=StockLedgerEntry.MovementType.RECEIPT,
                    qty_change=Decimal(qty_in), reference=f"Nhập lô {batch_id}",
                )
                # Lô tạo sẵn ở tồn thấp hơn số nhập: bút toán bù để tổng sổ = tồn (sổ nhập xuất, kiểm kê).
                gap = Decimal(qty_stock) - Decimal(qty_in)
                if gap:
                    StockLedgerEntry.objects.create(
                        batch=batch, qty_change=gap,
                        movement_type=(StockLedgerEntry.MovementType.WRITE_OFF
                                       if status == Batch.Status.CANCELLED
                                       else StockLedgerEntry.MovementType.SALE),
                        reference="QA-bút toán bù cho lô dựng sẵn",
                    )
                if status == Batch.Status.CLOSED:
                    Batch.objects.filter(pk=batch.pk).update(
                        closed_at=self.now, closed_by=self.users["qa_owner"])
                    batch.refresh_from_db()
            self.batches[batch_id] = batch

    # --------------------------------------------------------- đơn + kịch bản
    def _book(self, n, icode, qty, ttl_minutes=None):
        """Đơn BOOKED + giữ chỗ lô SELLING của mặt hàng (như seed_demo). Trả đơn, hoặc None nếu đã có."""
        code = order_code(n)
        existing = SalesOrder.objects.filter(code=code).first()
        if existing is not None:
            self.orders[n] = existing
            return None
        qty = Decimal(qty)
        rate = self.rates[icode]
        amount = rate * qty
        customer = self.customers[n]
        order = SalesOrder.objects.create(
            code=code, customer=customer, status=SalesOrder.Status.BOOKED,
            delivery_address=customer.default_address, phone=customer.phone, total_amount=amount,
            booked_expires_at=(self.now + timedelta(minutes=ttl_minutes)
                               if ttl_minutes is not None else None),
        )
        line = SalesOrderLine.objects.create(order=order, item=self.items[icode], qty=qty,
                                             rate=rate, amount=amount)
        batch = self.batches[ORDER_BATCH[icode]]
        reserved = batch_services.reserve(batch=batch, qty=qty)
        SalesOrderLineBatch.objects.create(order_line=line, batch=batch, component_item=self.items[icode],
                                           qty=qty, unit_cost=reserved.landed_unit_cost)
        self.orders[n] = order
        return order

    def _pay(self, order, n, *, minutes_ago=30):
        """Thanh toán khớp đủ → hoá đơn QA-HD-nn + phiếu giao (signal), đổi mã phiếu thành QA-GH-nn."""
        payment_services.confirm_payment(
            order=order, bank_txn_id=txn_id(n), amount=order.total_amount,
            received_at=self.now - timedelta(minutes=minutes_ago),
            source=PaymentTransaction.Source.WEBHOOK, raw_payload={"qa_seed": True},
            invoice_code=invoice_code(n),
        )
        return self._adopt_note(n)

    def _adopt_note(self, n):
        # Hoá đơn sinh qua đường khác (chuyển bù, xác nhận tay) có mã tự sinh → đổi sang mã QA cố định.
        SalesInvoice.objects.filter(sales_order__code=order_code(n)).update(code=invoice_code(n))
        note = DeliveryNote.objects.get(sales_invoice__code=invoice_code(n))
        DeliveryNote.objects.filter(pk=note.pk).update(code=note_code(n))
        note.refresh_from_db()
        self.notes[n] = note
        return note

    def _set_order_status(self, order, status):
        SalesOrder.objects.filter(pk=order.pk).update(status=status)
        order.refresh_from_db()

    def _confirm_note(self, note, *, status, courier=None):
        """Phiếu đã gọi xác nhận xong (việc gọi DONE, có một cuộc gọi của qa_cs1), rồi đặt trạng thái."""
        cs1 = self.users["qa_cs1"]
        DeliveryNote.objects.filter(pk=note.pk).update(
            status=status, confirmed_at=self.now, confirmed_by=cs1,
            assigned_to=self.users[courier] if courier else None,
        )
        ConfirmationTask.objects.filter(note=note).update(state=ConfirmationTask.State.DONE)
        CustomerCall.objects.create(note=note, result=CustomerCall.Result.CONFIRMED,
                                    note_text="QA-gọi xác nhận (giả)", created_by=cs1)
        note.refresh_from_db()

    def _scenarios(self):
        owner = self.users["qa_owner"]

        # 01, 02: giữ chỗ (còn lâu / sắp hết giờ).
        self._book(1, "QA-CA", 2, ttl_minutes=25)
        self._book(2, "QA-TOM", 1, ttl_minutes=3)

        # 03: tự huỷ (đã nhả giữ chỗ) + tiền về muộn ORPHAN có phiếu hoàn FAILED.
        o = self._book(3, "QA-CA", 2, ttl_minutes=-20)
        if o is not None:
            batch_services.release(batch=self.batches["QA-LO-01"], qty=o.lines.first().qty)
            self._set_order_status(o, SalesOrder.Status.AUTO_CANCELLED)
            p = payment_services.confirm_payment(
                order=o, bank_txn_id=txn_id(3, "LATE"), amount=o.total_amount,
                received_at=self.now - timedelta(minutes=5), raw_payload={"qa_seed": True})
            self.payments["orphan_with_refund"] = p
            refund, _ = refund_services.create_refund_for_payment(
                payment=p, amount=p.amount, reason="QA-tiền về muộn (giả)", actor=owner,
                request_id=uuid5(NAMESPACE_URL, "caveve-qa/refund/failed"))
            refund_services.mark_refund_failed(refund=refund, reason="QA-sai số tài khoản (giả)", actor=owner)
            PaymentTransaction.objects.filter(pk=p.pk).update(
                duplicate_warning=payment_services.DUPLICATE_MANUAL_WARNING)
        # 17: tự huỷ + tiền về muộn ORPHAN (không phiếu hoàn).
        o = self._book(17, "QA-TOM", 1, ttl_minutes=-30)
        if o is not None:
            batch_services.release(batch=self.batches["QA-LO-05"], qty=o.lines.first().qty)
            self._set_order_status(o, SalesOrder.Status.AUTO_CANCELLED)
            p = payment_services.confirm_payment(
                order=o, bank_txn_id=txn_id(17, "LATE"), amount=o.total_amount,
                received_at=self.now - timedelta(minutes=8), raw_payload={"qa_seed": True})
            PaymentTransaction.objects.filter(pk=p.pk).update(
                duplicate_warning=payment_services.DUPLICATE_MANUAL_WARNING)
            self.payments["orphan"] = p

        # 04: ĐÃ THANH TOÁN, phiếu chờ gọi xác nhận (việc PENDING).
        o = self._book(4, "QA-CA", 2)
        if o is not None:
            self._pay(o, 4)
            self._set_order_status(o, SalesOrder.Status.PAID)
        # 05: PROCESSING, phiếu Đang soạn hàng.
        o = self._book(5, "QA-TOM", 1)
        if o is not None:
            self._confirm_note(self._pay(o, 5), status=DeliveryNote.Status.PREPARING)
        # 06: Chờ lấy hàng, giao1.
        o = self._book(6, "QA-CA", 3)
        if o is not None:
            self._confirm_note(self._pay(o, 6), status=DeliveryNote.Status.READY, courier="qa_courier1")
        # 07: Đang giao, giao1.
        o = self._book(7, "QA-TOM", 2)
        if o is not None:
            note = self._pay(o, 7)
            self._confirm_note(note, status=DeliveryNote.Status.DELIVERING, courier="qa_courier1")
            DeliveryNote.objects.filter(pk=note.pk).update(delivery_started_at=self.now - timedelta(minutes=20))
        # 08: Hoàn tất, giao xong (giao1).
        o = self._book(8, "QA-CA", 2)
        if o is not None:
            note = self._pay(o, 8, minutes_ago=300)
            self._confirm_note(note, status=DeliveryNote.Status.COMPLETED, courier="qa_courier1")
            DeliveryNote.objects.filter(pk=note.pk).update(
                completed_at=self.now - timedelta(minutes=60),
                delivery_started_at=self.now - timedelta(minutes=120))
            self._set_order_status(o, SalesOrder.Status.COMPLETED)
        # 09: giao thất bại (giao2), đơn vẫn PROCESSING.
        o = self._book(9, "QA-CA", 2)
        if o is not None:
            note = self._pay(o, 9)
            self._confirm_note(note, status=DeliveryNote.Status.FAILED, courier="qa_courier2")
            DeliveryNote.objects.filter(pk=note.pk).update(
                failed_attempts=1, failure_reason=DeliveryNote.FailureReason.NOT_MET,
                failed_at=self.now - timedelta(minutes=15),
                delivery_started_at=self.now - timedelta(minutes=50))

        # 10: HUỶ có cancel_note, phiếu CANCELLED gán giao1, phiếu hoàn PENDING.
        o = self._book(10, "QA-TOM", 1)
        if o is not None:
            note = self._pay(o, 10)
            self._confirm_note(note, status=DeliveryNote.Status.PREPARING)
            order_services.cancel_paid_order(order=o, actor=owner, reason_code="CUSTOMER_CHANGED_MIND",
                                             cancel_note=CANCEL_NOTE_1)
            DeliveryNote.objects.filter(pk=note.pk).update(assigned_to=self.users["qa_courier1"])
            self.refunds["pending"] = refund_services.create_refund(
                invoice=o.invoice, amount=o.total_amount, is_partial=False, actor=owner,
                reason="QA-hoàn tiền đơn huỷ (giả)",
                request_id=uuid5(NAMESPACE_URL, "caveve-qa/refund/pending"))
        # 11: HUỶ có cancel_note, phiếu CANCELLED gán giao2, phiếu hoàn REFUNDED; việc gọi báo hoàn tiền.
        o = self._book(11, "QA-CA", 2)
        if o is not None:
            note = self._pay(o, 11)
            self._confirm_note(note, status=DeliveryNote.Status.READY)
            order_services.cancel_paid_order(order=o, actor=owner, reason_code="DAMAGED_WHEN_PACKING",
                                             cancel_note=CANCEL_NOTE_2)
            DeliveryNote.objects.filter(pk=note.pk).update(assigned_to=self.users["qa_courier2"])
            refund = refund_services.create_refund(
                invoice=o.invoice, amount=o.total_amount, is_partial=False, actor=owner,
                reason="QA-hoàn tiền đơn huỷ (giả)",
                request_id=uuid5(NAMESPACE_URL, "caveve-qa/refund/refunded"))
            refund = refund_services.confirm_refund(refund=refund, bank_txn_ref="QA-REFUND-TXN-01", actor=owner)
            ConfirmationTask.objects.filter(note=note).update(
                state=ConfirmationTask.State.REFUND_CALL, refund=refund)
            self.refunds["refunded"] = refund

        # 12: HOÀN TẤT sau CHUYỂN BÙ (hai khoản thiếu cộng lại đủ, Chủ xác nhận), giao2.
        o = self._book(12, "QA-TOM", 2)
        if o is not None:
            half = o.total_amount / 2
            for suffix in ("A", "B"):
                p = payment_services.confirm_payment(
                    order=o, bank_txn_id=txn_id(12, suffix), amount=half,
                    received_at=self.now - timedelta(minutes=90 if suffix == "A" else 40),
                    raw_payload={"qa_seed": True})
            payment_services.resolve_payment(payment=p, action="CONFIRM_ORDER", actor=owner,
                                             note="QA-khách chuyển bù (giả)")
            note = self._adopt_note(12)
            self._confirm_note(note, status=DeliveryNote.Status.COMPLETED, courier="qa_courier2")
            DeliveryNote.objects.filter(pk=note.pk).update(completed_at=self.now - timedelta(minutes=10))
            self._set_order_status(o, SalesOrder.Status.COMPLETED)
        # 13: giữ chỗ + một khoản CHUYỂN THIẾU còn mở.
        o = self._book(13, "QA-CA", 2, ttl_minutes=20)
        if o is not None:
            payment_services.confirm_payment(
                order=o, bank_txn_id=txn_id(13, "SHORT"), amount=o.total_amount * Decimal("0.4"),
                received_at=self.now - timedelta(minutes=4), raw_payload={"qa_seed": True})

        # 14: việc gọi ESCALATED (3 cuộc không nghe máy của qa_cs1).
        o = self._book(14, "QA-CA", 1)
        if o is not None:
            note = self._pay(o, 14)
            cs1 = self.users["qa_cs1"]
            for _ in range(3):
                CustomerCall.objects.create(note=note, result=CustomerCall.Result.UNREACHABLE,
                                            note_text="QA-không nghe máy (giả)", created_by=cs1)
            ConfirmationTask.objects.filter(note=note).update(
                state=ConfirmationTask.State.ESCALATED,
                escalation_reason=ConfirmationTask.EscalationReason.UNREACHABLE, attempts=3,
                first_unreachable_at=self.now - timedelta(hours=5),
                last_unreachable_at=self.now - timedelta(hours=1), escalated_at=self.now - timedelta(hours=1))
        # 15: việc gọi CALLBACK (hẹn gọi lại).
        o = self._book(15, "QA-TOM", 1)
        if o is not None:
            note = self._pay(o, 15)
            CustomerCall.objects.create(note=note, result=CustomerCall.Result.CALLBACK,
                                        note_text="QA-hẹn gọi lại (giả)", created_by=self.users["qa_cs2"],
                                        callback_at=self.now + timedelta(hours=2))
            ConfirmationTask.objects.filter(note=note).update(
                state=ConfirmationTask.State.CALLBACK, callback_at=self.now + timedelta(hours=2))

        # 16: xác nhận TAY (MANUAL) rồi IPN cùng số tiền về sau → OVERPAID có nhãn nghi trùng.
        o = self._book(16, "QA-CA", 1)
        if o is not None:
            payment_services.confirm_payment_manual(
                order=o, bank_txn_id=txn_id(16, "MANUAL"), amount=o.total_amount, actor=owner)
            self._adopt_note(16)
            dup = payment_services.confirm_payment(
                order=o, bank_txn_id=txn_id(16, "IPN"), amount=o.total_amount,
                received_at=self.now - timedelta(minutes=2), raw_payload={"qa_seed": True})
            if not dup.duplicate_warning:
                PaymentTransaction.objects.filter(pk=dup.pk).update(
                    duplicate_warning=payment_services.DUPLICATE_MANUAL_WARNING)

        # Khoản không khớp đơn (UNMATCHED) có nhãn nghi trùng.
        unmatched, created = payment_services.record_unmatched_payment(
            bank_txn_id=txn_id(90, "UNMATCHED"), amount=Decimal("123000"),
            received_at=self.now - timedelta(minutes=12), source=PaymentTransaction.Source.WEBHOOK,
            raw_payload={"qa_seed": True})
        if created:
            PaymentTransaction.objects.filter(pk=unmatched.pk).update(
                duplicate_warning=payment_services.DUPLICATE_MANUAL_WARNING)

        # Nạp lại vào bảng mã (dùng cả cho lần chạy lại: kịch bản đã có thì không dựng lại).
        for n in range(1, 18):
            order = SalesOrder.objects.filter(code=order_code(n)).first()
            if order is None:
                continue
            self.orders[n] = order
            note = DeliveryNote.objects.filter(code=note_code(n)).first()
            if note is not None:
                self.notes[n] = note

    # -------------------------------------------------- hàng hoàn, nhập, kiểm kê
    def _returns(self):
        note = self.notes.get(9)
        specs = [
            ("QA-RETURN-DRAFT", ReturnToStock.Status.DRAFT, ReturnToStock.Decision.PENDING),
            ("QA-RETURN-APPROVED", ReturnToStock.Status.APPROVED, ReturnToStock.Decision.RESTOCK),
            ("QA-RETURN-CANCELLED", ReturnToStock.Status.CANCELLED, ReturnToStock.Decision.PENDING),
        ]
        for text, status, decision in specs:
            if ReturnToStock.all_objects.filter(note=text).exists():
                self.returns[text] = ReturnToStock.all_objects.get(note=text)
                continue
            approved = status == ReturnToStock.Status.APPROVED
            rt = ReturnToStock.all_objects.create(
                delivery_note=note, batch=self.batches["QA-LO-01"], qty=Decimal("1.000"),
                left_warehouse_at=self.now - timedelta(hours=3), returned_at=self.now - timedelta(hours=1),
                decision=decision,
                status=ReturnToStock.Status.DRAFT if approved else status,
                created_by=self.users["qa_courier2"], note=text)
            if approved:  # đi qua service để có bút toán RETURN_RESTOCK và cộng tồn
                return_services.apply_return(return_to_stock=rt, approver=self.users["qa_manager"])
                rt.refresh_from_db()
            self.returns[text] = rt

    def _receipts(self):
        specs = [
            ("QA-RECEIPT-DRAFT", PurchaseReceipt.Status.DRAFT, [("QA-CA", 10, 70000, None)]),
            ("QA-RECEIPT-SUBMITTED", PurchaseReceipt.Status.SUBMITTED,
             [("QA-CA", 500, 70000, "QA-LO-01"), ("QA-TOM", 300, 150000, "QA-LO-05")]),
            ("QA-RECEIPT-CANCELLED", PurchaseReceipt.Status.CANCELLED, [("QA-MUC", 5, 100000, None)]),
        ]
        for text, status, lines in specs:
            existing = PurchaseReceipt.objects.filter(note=text).first()
            if existing is not None:
                self.receipts[text] = existing
                continue
            receipt = PurchaseReceipt.objects.create(
                supplier=self.suppliers[0], warehouse=self.warehouse,
                received_date=self.today - timedelta(days=2), status=status,
                created_by=self.users["qa_warehouse"], note=text)
            for icode, qty, rate, batch_id in lines:
                PurchaseReceiptLine.objects.create(
                    receipt=receipt, item=self.items[icode], qty=Decimal(qty), rate=Decimal(rate),
                    batch=self.batches[batch_id] if batch_id else None)
            self.receipts[text] = receipt

    def _stocktakes(self):
        batch = Batch.objects.get(pk=self.batches["QA-LO-01"].pk)
        for text, status in (("QA-STOCKTAKE-DRAFT", StockReconciliation.Status.DRAFT),
                             ("QA-STOCKTAKE-SUBMITTED", StockReconciliation.Status.SUBMITTED)):
            existing = StockReconciliation.objects.filter(note=text).first()
            if existing is not None:
                self.stocktakes[text] = existing
                continue
            sheet = StockReconciliation.objects.create(
                count_date=self.today, status=status, created_by=self.users["qa_warehouse"], note=text)
            StockReconciliationLine.objects.create(
                reconciliation=sheet, batch=batch, system_qty=batch.qty_available,
                counted_qty=batch.qty_available - 1, difference_qty=Decimal("-1"), reason="QA-hao hụt giả")
            self.stocktakes[text] = sheet

    # ------------------------------------------------------ kịch bản gọi, nhật ký
    def _call_scripts(self):
        owner = self.users["qa_owner"]
        for situation in CallScript.Situation.values:
            existing = CallScript.objects.filter(situation=situation).first()
            if existing is None:
                existing = call_scripts.create_script(
                    actor=owner, situation=situation,
                    content=f"{CALL_SCRIPT_PREFIX}Kịch bản giả cho tình huống {situation}.")
            elif not existing.content.startswith(CALL_SCRIPT_PREFIX):
                self.warnings.append(f"Kịch bản gọi {situation} đã có (không phải QA), giữ nguyên.")
                continue
            self.scripts[situation] = existing

    def _audit_samples(self):
        """Vài dòng Nhật ký đủ loại tác nhân (người / hệ thống / AI) và nhiều hành động."""
        if AuditLog.objects.filter(note__startswith="QA-audit-").exists():
            return
        batch = self.batches["QA-LO-06"]
        order = self.orders.get(8)
        users = self.users
        record_audit("publish_batch", actor=users["qa_manager"], obj=self.batches["QA-LO-01"],
                     changes={"status": {"from": "DRAFT", "to": "SELLING"}}, note="QA-audit-01")
        record_audit("close_batch", actor=users["qa_owner"], obj=batch,
                     changes={"status": {"from": "SELLING", "to": "CLOSED"}}, note="QA-audit-02")
        if order is not None:
            record_audit("confirm_payment_manual", actor=users["qa_owner"], obj=order,
                         changes={"status": {"from": "BOOKED", "to": "PROCESSING"}}, note="QA-audit-03")
        record_audit("cancel_expired_orders", actor=None, obj=None,
                     changes={"cancelled": 2}, note="QA-audit-04")  # Hệ thống (job TTL)
        record_audit("create_refund", actor=users["qa_owner"], actor_kind="ai",
                     ai_actor=users["qa_owner"], proposal_ref="QA-PROP-01",
                     changes={"amount": {"to": "100000"}}, note="QA-audit-05")  # AI thay Chủ
        record_audit("create_user", actor=users["qa_owner"], obj=users["qa_cs2"],
                     changes={"groups": ["customer_service"]}, note="QA-audit-06")

    # ---------------------------------------------------------------- bảng mã → id
    def manifest(self):
        def ids(mapping, key=lambda k: k):
            return {key(k): v.pk for k, v in mapping.items()}

        orders = {order_code(n): {"id": o.pk, "status": o.status} for n, o in sorted(self.orders.items())}
        notes = {}
        for n, note in sorted(self.notes.items()):
            note.refresh_from_db()
            notes[note.code] = {"id": note.pk, "status": note.status, "order": order_code(n),
                                "assigned_to": note.assigned_to.username if note.assigned_to_id else None}
        payments = {p.bank_txn_id: {"id": p.pk, "match_status": p.match_status,
                                    "resolution_status": p.resolution_status}
                    for p in PaymentTransaction.objects.filter(bank_txn_id__startswith=PREFIX).order_by("id")}
        refunds = {f"QA-REFUND-{r.status}": {"id": r.pk, "status": r.status}
                   for r in Refund.objects.filter(reason__startswith=PREFIX).order_by("id")}
        invoices = {i.code: i.pk for i in SalesInvoice.objects.filter(code__startswith=PREFIX).order_by("id")}
        return {
            "password_env": "QA_PASSWORD",
            "users": {u: obj.pk for u, obj in self.users.items()},
            "customers": {c.phone: c.pk for c in self.customers.values()},
            "items": ids(self.items),
            "batches": {b: {"id": obj.pk, "status": obj.status} for b, obj in self.batches.items()},
            "orders": orders,
            "invoices": invoices,
            "delivery_notes": notes,
            "payments": payments,
            "refunds": refunds,
            "returns": ids(self.returns),
            "receipts": ids(self.receipts),
            "stocktakes": ids(self.stocktakes),
            "call_scripts": ids(self.scripts),
            "warnings": self.warnings,
        }

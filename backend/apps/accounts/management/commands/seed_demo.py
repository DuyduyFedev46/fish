"""
Dữ liệu demo (D1, Duy 2026-09-24) — thêm được, gỡ sạch được, thêm lại được.

    manage.py seed_demo                          # thêm (idempotent, get_or_create theo mã)
    manage.py seed_demo --remove [--dry-run]     # gỡ CHỈ bản ghi demo (sổ DemoRecord)
    manage.py seed_demo --remove --adopt-legacy  # nhận cả demo seed bằng bản cũ (chưa có sổ)

Mọi bản ghi lệnh này TẠO MỚI (kể cả do signal sinh, vd phiếu giao) được ghi vào sổ
`accounts.DemoRecord`; bản ghi thật trùng mã được dùng lại nhưng KHÔNG bị đánh dấu. Gỡ demo là
ngoại lệ có chủ đích của BR-PQ-10 (chứng từ không xoá) — chỉ cho bản ghi trong sổ; bản ghi demo
đang được dữ liệu thật dùng thì giữ lại và báo ra. Xem apps/accounts/demo/services.py.

R4 (code review trước deploy 1): dữ liệu demo tự nhất quán — lô nhập kèm bút toán RECEIPT; đơn
giữ chỗ qua `inventory.batches.reserve` + `SalesOrderLineBatch` (tồn giữ chỗ = Σ phân bổ của đơn
BOOKED, job TTL nhả đúng); đơn đã thanh toán đi qua `payments.confirm_payment` (giao dịch MATCHED
→ hoá đơn đủ dòng + phân bổ lô + bút toán SALE, BR-BH-06/BR-TT-06); đơn tự huỷ đã nhả giữ chỗ.
Demo chỉ giữ chỗ trên LÔ DEMO của mặt hàng (không phân bổ FEFO sang lô thật) và không bao giờ đụng lô thật.
"""
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.demo import services as demo
from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.common.exceptions import BusinessError
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, StockLedgerEntry, Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import (
    Customer,
    PaymentTransaction,
    SalesInvoice,
    SalesOrder,
    SalesOrderLine,
    SalesOrderLineBatch,
)
from apps.sales.payments import services as payment_services

ITEMS = [
    # code, name, giá bán, giá vốn/kg, shelf_life
    ("CA-THU", "Cá thu", 165000, 124000, 20),
    ("TOM-SU-1", "Tôm sú loại 1", 420000, 342000, 12),
    ("MUC-ONG", "Mực ống", 235000, 168000, 10),
    ("CA-HOI-NU", "Cá hồi Na Uy", 390000, 285000, 8),
    ("GHE-XANH", "Ghẹ xanh", 310000, 218000, 9),
    ("BACH-TUOC", "Bạch tuộc", 280000, 196000, 14),
]
# batch_id, item_code, supplier, nhập kg, nhập cách đây (ngày), hạn còn (ngày), status.
# Tồn/giữ chỗ KHÔNG khai tay (R4): tính ra từ đơn bên dưới — vd LO-0918 nhập 67, bán 4+2 → tồn 61;
# LO-0903 nhập 28, đơn BOOKED giữ 6 → còn bán 22.
BATCHES = [
    ("LO-0912", "CA-HOI-NU", "NK Đại Dương", 18, 3, 1, Batch.Status.NEAR_EXPIRY),
    ("LO-0907", "MUC-ONG", "Tàu cá Long Hải", 37, 6, 2, Batch.Status.NEAR_EXPIRY),
    ("LO-0903", "TOM-SU-1", "Vựa Ba Hòn", 28, 8, 3, Batch.Status.NEAR_EXPIRY),
    # F1 (FEFO): LO-0915 nhập TRƯỚC LO-0918 nhưng hạn MUỘN hơn -> FEFO xuất LO-0918 trước (FIFO
    # thì ngược lại). Đặt trước LO-0918 để đơn demo cá thu vẫn đi LO-0918 (batch_by_item = lô cuối).
    ("LO-0915", "CA-THU", "Vựa Ba Hòn", 25, 5, 12, Batch.Status.SELLING),
    ("LO-0918", "CA-THU", "Tàu cá Long Hải", 67, 1, 8, Batch.Status.SELLING),
    ("LO-0921", "GHE-XANH", "Vựa Ba Hòn", 29, 1, 6, Batch.Status.SELLING),
    ("LO-0922", "BACH-TUOC", "NK Đại Dương", 40, 1, 10, Batch.Status.SELLING),
]
# code, tên khách, sđt, item, kg, status, hạn giữ chỗ so với lúc seed (phút; âm = đã hết, None nếu
# không), có thanh toán + hoá đơn hôm nay
ORDERS = [
    ("DH-2609-118", "Chị Hồng", "0903338472", "CA-THU", 4, SalesOrder.Status.PROCESSING, None, True),
    ("DH-2609-117", "Anh Dũng", "0938451930", "GHE-XANH", 2, SalesOrder.Status.PAID, None, True),
    ("DH-2609-116", "Quán Bảy Cua", "0912002201", "TOM-SU-1", 6, SalesOrder.Status.BOOKED, 9, False),
    ("DH-2609-119", "Chị Lan", "0977106655", "MUC-ONG", 3, SalesOrder.Status.BOOKED, 22, False),
    ("DH-2609-115", "Chị Mai", "0908773040", "CA-THU", 2, SalesOrder.Status.COMPLETED, None, True),
    ("DH-2609-114", "Anh Sơn", "0931229182", "BACH-TUOC", 5, SalesOrder.Status.AUTO_CANCELLED, -20, False),
]


def invoice_code(order_code):
    return order_code.replace("DH", "HD")


def demo_txn_id(order_code):
    """Mã giao dịch ngân hàng giả của đơn demo đã thanh toán."""
    return f"DEMO-{order_code}"


class Command(BaseCommand):
    help = "Thêm (mặc định) hoặc gỡ (--remove) dữ liệu demo — chỉ dữ liệu demo."

    def add_arguments(self, parser):
        parser.add_argument("--remove", action="store_true",
                            help="Gỡ dữ liệu demo đã đánh dấu (không đụng dữ liệu thật).")
        parser.add_argument("--dry-run", action="store_true",
                            help="Cùng --remove: chỉ liệt kê, không xoá.")
        parser.add_argument("--adopt-legacy", action="store_true",
                            help="Cùng --remove: nhận diện demo seed bằng bản cũ theo chữ ký "
                                 "chính xác (mã + tên/SĐT) trước khi gỡ.")

    def handle(self, *args, **opts):
        if opts["remove"]:
            return self._remove(dry_run=opts["dry_run"], adopt=opts["adopt_legacy"])
        if opts["dry_run"] or opts["adopt_legacy"]:
            self.stderr.write("--dry-run / --adopt-legacy chỉ dùng cùng --remove.")
            return
        with demo.track_demo_creations():
            self._seed()

    @transaction.atomic
    def _remove(self, *, dry_run, adopt):
        if adopt:
            adopt_legacy()
        result = demo.remove_demo(dry_run=dry_run)
        total = sum(result["deleted"].values())
        prefix = "Chạy thử (không xoá gì): " if dry_run else ""
        detail = ", ".join(f"{k}: {v}" for k, v in sorted(result["deleted"].items()))
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}Đã gỡ {total} bản ghi demo" + (f" ({detail})." if detail else ".")))
        if result["kept"]:
            self.stdout.write(self.style.WARNING(
                f"Giữ lại {len(result['kept'])} bản ghi demo (dữ liệu thật đang dùng, hoặc là "
                f"một phần / phụ thuộc bản ghi đang giữ):"))
            for desc, reason in result["kept"]:
                self.stdout.write(f"  - {desc} — {reason}")
        if dry_run:
            transaction.set_rollback(True)  # adopt-legacy cũng hoàn tác

    @transaction.atomic
    def _seed(self):
        today = timezone.localdate()
        now = timezone.now()

        wh = Warehouse.objects.order_by("id").first() or Warehouse.objects.create(name="Kho chính")
        pl = PriceList.objects.filter(is_default=True).first() or PriceList.objects.order_by("id").first()
        if pl is None:
            pl = PriceList.objects.create(name="Bán lẻ", is_default=True)
        grp, _ = ItemGroup.objects.get_or_create(name="Hải sản")

        items = {}
        for code, name, price, cost, shelf in ITEMS:
            it, _ = Item.objects.get_or_create(
                code=code,
                defaults=dict(name=name, item_group=grp, item_type=Item.ItemType.SIMPLE,
                              shelf_life_in_days=shelf, is_active=True),
            )
            items[code] = it
            ItemPrice.objects.get_or_create(
                price_list=pl, item=it, valid_from=today - timedelta(days=30),
                defaults=dict(rate=Decimal(price)),
            )

        suppliers = {}
        for sname in sorted({b[2] for b in BATCHES}):
            suppliers[sname], _ = Supplier.objects.get_or_create(name=sname)

        cost_by_item = {code: cost for code, _, _, cost, _ in ITEMS}
        batch_by_item = {}
        for bid, icode, sname, qty, nago, hleft, status in BATCHES:
            b, created = Batch.objects.get_or_create(
                batch_id=bid,
                defaults=dict(
                    item=items[icode], supplier=suppliers[sname], warehouse=wh,
                    received_date=today - timedelta(days=nago),
                    expiry_date=today + timedelta(days=hleft),
                    qty_received=Decimal(qty), qty_available=Decimal(qty),
                    qty_reserved=Decimal("0"),
                    purchase_rate=Decimal(cost_by_item[icode]),
                    landed_unit_cost=Decimal(cost_by_item[icode]),
                    status=status,
                ),
            )
            if created:
                StockLedgerEntry.objects.create(
                    batch=b, movement_type=StockLedgerEntry.MovementType.RECEIPT,
                    qty_change=Decimal(qty), reference=f"Nhập lô {bid}",
                )
            batch_by_item[icode] = b

        price_by_item = {code: price for code, _, price, _, _ in ITEMS}
        for spec in ORDERS:
            code, cname, phone, icode, qty, status, ttl_min, has_inv = spec
            cust, _ = Customer.objects.get_or_create(
                phone=phone, defaults=dict(name=cname, default_address="TP.HCM"))
            if SalesOrder.objects.filter(code=code).exists():
                continue  # idempotent: đơn (demo hoặc thật trùng mã) đã có → không đụng
            skip = self._skip_reason(spec, batch_by_item[icode])
            if skip:
                self.stdout.write(self.style.WARNING(f"Bỏ qua đơn demo {code}: {skip}."))
                continue
            try:
                with transaction.atomic():
                    self._seed_order(spec, customer=cust, item=items[icode],
                                     batch=batch_by_item[icode],
                                     rate=Decimal(price_by_item[icode]), now=now)
            except BusinessError as exc:
                self.stdout.write(self.style.WARNING(f"Bỏ qua đơn demo {code}: {exc}"))

        self.stdout.write(self.style.SUCCESS(
            f"Seed xong: {Item.objects.count()} mặt hàng · {Batch.objects.count()} lô · "
            f"{SalesOrder.objects.count()} đơn · {SalesInvoice.objects.count()} hoá đơn."))

    @staticmethod
    def _skip_reason(spec, batch):
        code, *_rest, has_inv = spec
        if not demo.is_demo(batch):
            return f"lô {batch.batch_id} là dữ liệu thật — demo không giữ chỗ/bán trên lô thật"
        if has_inv and SalesInvoice.objects.filter(code=invoice_code(code)).exists():
            return f"mã hoá đơn {invoice_code(code)} đã dùng"
        if has_inv and PaymentTransaction.objects.filter(bank_txn_id=demo_txn_id(code)).exists():
            return f"mã giao dịch {demo_txn_id(code)} đã dùng"
        return ""

    @staticmethod
    def _seed_order(spec, *, customer, item, batch, rate, now):
        """
        Một đơn demo đi đúng đường nghiệp vụ (R4): tạo đơn BOOKED + giữ chỗ lô (như
        orders.create_order, nhưng chỉ định lô demo) → thanh toán khớp qua confirm_payment
        (hoá đơn + SALE + phân bổ lô) hoặc nhả giữ chỗ khi tự huỷ.
        """
        code, _cname, phone, _icode, qty, status, ttl_min, has_inv = spec
        qty = Decimal(qty)
        amount = rate * qty
        order = SalesOrder.objects.create(
            code=code, customer=customer, status=SalesOrder.Status.BOOKED,
            delivery_address="TP.HCM", phone=phone, total_amount=amount,
            booked_expires_at=now + timedelta(minutes=ttl_min) if ttl_min is not None else None,
        )
        line = SalesOrderLine.objects.create(order=order, item=item, qty=qty, rate=rate,
                                             amount=amount)
        reserved = batch_services.reserve(batch=batch, qty=qty)  # BR-BH-02, raise nếu thiếu
        SalesOrderLineBatch.objects.create(order_line=line, batch=batch, component_item=item,
                                           qty=qty, unit_cost=reserved.landed_unit_cost)
        if has_inv:
            payment_services.confirm_payment(
                order=order, bank_txn_id=demo_txn_id(code), amount=amount, received_at=now,
                source=PaymentTransaction.Source.WEBHOOK, raw_payload={"demo": True},
                invoice_code=invoice_code(code),
            )
        elif status == SalesOrder.Status.AUTO_CANCELLED:
            batch_services.release(batch=batch, qty=qty)  # như job TTL (BR-BH-03/04)
        if status != SalesOrder.Status.BOOKED:
            SalesOrder.objects.filter(pk=order.pk).update(status=status)


DEMO_BATCH_IDS = [b[0] for b in BATCHES]


def adopt_legacy():
    """
    Đánh dấu demo cho dữ liệu seed bằng bản cũ (trước khi có sổ DemoRecord) — chỉ khi khớp CHÍNH
    XÁC chữ ký của bộ dữ liệu trên (mã + tên / SĐT / nhà cung cấp). Không bao giờ nhận tên chung
    (Kho chính, bảng giá Bán lẻ, nhóm "Hải sản") vì dễ trùng dữ liệu thật. Bản ghi được nhận mà
    đang bị dữ liệu thật dùng vẫn được `remove_demo` giữ lại.
    """
    from apps.delivery.models import DeliveryNote

    mark = demo.mark_demo
    price_by_item = {code: Decimal(price) for code, _, price, _, _ in ITEMS}
    for code, name, *_ in ITEMS:
        for item in Item.objects.filter(code=code, name=name):
            mark(item)
            for ip in ItemPrice.objects.filter(item=item, rate=price_by_item[code]):
                mark(ip)
    for sname in sorted({b[2] for b in BATCHES}):
        for sup in Supplier.objects.filter(name=sname):
            mark(sup)
    for bid, icode, sname, *_ in BATCHES:
        for b in Batch.objects.filter(batch_id=bid, item__code=icode, supplier__name=sname):
            mark(b)
            for entry in b.ledger_entries.filter(
                movement_type=StockLedgerEntry.MovementType.RECEIPT, reference=f"Nhập lô {bid}"
            ):
                mark(entry)
    for code, cname, phone, *_ in ORDERS:
        for cust in Customer.objects.filter(phone=phone, name=cname):
            mark(cust)
        for order in SalesOrder.objects.filter(code=code, phone=phone):
            mark(order)
            for line in order.lines.all():
                mark(line)
                for alloc in line.batch_allocations.filter(batch__batch_id__in=DEMO_BATCH_IDS):
                    mark(alloc)  # R4: giữ chỗ demo
            for pay in PaymentTransaction.objects.filter(sales_order=order,
                                                         bank_txn_id=demo_txn_id(code)):
                mark(pay)
            for inv in SalesInvoice.objects.filter(sales_order=order, code=invoice_code(code)):
                mark(inv)
                for line in inv.lines.all():
                    mark(line)
                    for alloc in line.batch_allocations.filter(
                        batch__batch_id__in=DEMO_BATCH_IDS
                    ):
                        mark(alloc)  # R4: phân bổ lô đã bán
                for entry in StockLedgerEntry.objects.filter(
                    movement_type=StockLedgerEntry.MovementType.SALE, reference=inv.code,
                    batch__batch_id__in=DEMO_BATCH_IDS,
                ):
                    mark(entry)  # R4: bút toán SALE của hoá đơn demo
                # B5 (QA lần 2): chỉ nhận phiếu giao CHƯA BẮT ĐẦU (Soạn hàng, chưa gán người
                # giao) như lúc seed sinh ra. Phiếu đã gán/đang giao/đã giao coi là dữ liệu thật →
                # hoá đơn của nó (và cả cụm đơn/HĐ/phiếu giao) được giữ nguyên.
                for dn in DeliveryNote.objects.filter(
                    sales_invoice=inv, status=DeliveryNote.Status.PREPARING,
                    assigned_to__isnull=True,
                ):
                    mark(dn)

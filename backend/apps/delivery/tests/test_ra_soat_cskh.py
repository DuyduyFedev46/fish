"""
Rà soát A4 (doc/features/2026-09-30-sua-loi-review/02d-ke-hoach-doi-claude.md) cho hồ sơ
`2026-09-28-cskh-xac-nhan-in-tem`.

Bổ sung ca kiểm tra NGOÀI ĐƯỜNG THUẬN mà 04-qa-report.md chỉ ghi "code audit" (đọc code),
chưa có test tự động thật sự thực thi:

- CS-08-AC6 (tranh chấp Quản lý quyết định >< job tự huỷ chạy cùng lúc): trước đây chỉ có
  đánh giá tĩnh về thứ tự khoá dòng (`select_for_update`). Test này tái hiện đúng kịch bản
  "hai bên tranh 1 đơn": job tự huỷ thắng trước (do trong test đơn giản hoá thành chạy tuần tự,
  vì SQLite không hỗ trợ khoá dòng đa luồng thật) rồi Quản lý gọi `decide()` sau — phải nhận
  409 STALE_STATE và KHÔNG tạo thêm huỷ/hoàn tiền/AuditLog lần hai. Đồng thời kiểm chiều ngược
  lại: Quản lý quyết định trước thì job chạy sau phải bỏ qua (đã có ở CS-08-AC4, test lại ở đây
  cho đủ cặp tranh chấp hai chiều).
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.common.exceptions import ConflictError
from apps.common.tests.fixtures import make_user
from apps.delivery.cskh import services as cskh_services
from apps.delivery.models import ConfirmationTask, DeliveryNote
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import Refund, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.payments import services as payment_services


class CS08AC6RaceConditionTests(TestCase):
    """CS-08-AC6: 'Đúng một bên thắng (khoá dòng). Job thua thì bỏ qua; API thua thì 409 STALE_STATE.'"""

    def setUp(self):
        self.wh = Warehouse.objects.create(name="Kho chính")
        self.sup = Supplier.objects.create(name="Tàu cá Long Hải")
        self.pl = PriceList.objects.create(name="Bán lẻ", is_default=True)
        grp = ItemGroup.objects.create(name="Hải sản")
        self.item = Item.objects.create(code="CA-THU", name="Cá thu", item_group=grp)
        today = timezone.localdate()
        ItemPrice.objects.create(
            price_list=self.pl, item=self.item, rate=Decimal("150000"),
            valid_from=today - timedelta(days=1),
        )
        self.batch = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh,
            received_date=today, qty=Decimal("100"), purchase_rate=Decimal("110000"),
        )
        batch_services.publish_batch(batch=self.batch, actor=None)
        self.ql = make_user("ql1", "quan_ly")

    def _create_escalated_order(self, escalated_at):
        order = order_services.create_order(
            customer_phone="0900000123",
            customer_name="Khách Thử A",
            delivery_address="Số 1 Đường Thử, P. Thử, Lâm Đồng",
            phone="0900000123",
            lines=[{"item_code": self.item.code, "qty": Decimal("2")}],
        )
        payment_services.confirm_payment(
            order=order,
            bank_txn_id="TXN-RACE-01",
            amount=order.total_amount,
            received_at=timezone.now(),
        )
        order.refresh_from_db()
        note = DeliveryNote.objects.get(sales_invoice__sales_order=order)
        task = ConfirmationTask.objects.get(note=note)
        task.state = ConfirmationTask.State.ESCALATED
        task.escalation_reason = ConfirmationTask.EscalationReason.UNREACHABLE
        task.escalated_at = escalated_at
        task.save()
        return order, note, task

    @override_settings(CSKH_AUTO_CANCEL_ENABLED=True)
    def test_cs08_ac6_job_wins_then_manager_decide_gets_stale_state(self):
        """Job tự huỷ chạy (thắng) trước; Quản lý `decide()` gọi sau trên cùng task phải nhận STALE_STATE,
        KHÔNG được huỷ đơn lần hai, không tạo phiếu hoàn thứ hai, không thêm AuditLog `order_auto_cancelled`."""
        t0 = timezone.now().replace(hour=9, minute=25, second=0, microsecond=0)
        order, note, task = self._create_escalated_order(t0)

        t_job = t0 + timedelta(minutes=31)
        res = cskh_services.auto_cancel_overdue(now=t_job)
        self.assertEqual(res["cancelled"], 1, "Job phải thắng và huỷ đơn trước")

        order.refresh_from_db()
        note.refresh_from_db()
        task.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.CANCELLED)
        self.assertEqual(task.state, ConfirmationTask.State.REFUND_CALL)
        refund_count_after_job = Refund.objects.filter(sales_invoice=order.invoice).count()
        self.assertEqual(refund_count_after_job, 1)

        # Quản lý đến sau, không biết job đã chạy, cố quyết định trên cùng task -> phải thua (409 STALE_STATE)
        with self.assertRaises(ConflictError) as ctx:
            cskh_services.decide(
                task.pk, self.ql, "CANCEL",
                reason_code="MANAGER_TOO_LATE", now=t_job + timedelta(minutes=1),
            )
        self.assertEqual(ctx.exception.code, "STALE_STATE")

        # Không có huỷ/hoàn lần hai, không thêm AuditLog order_auto_cancelled thứ hai
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.CANCELLED)
        self.assertEqual(
            Refund.objects.filter(sales_invoice=order.invoice).count(), 1,
            "Quản lý thua cuộc đua không được tạo thêm phiếu hoàn",
        )
        self.assertEqual(
            AuditLog.objects.filter(action="order_auto_cancelled", object_id=str(order.pk)).count(), 1,
        )

    @override_settings(CSKH_AUTO_CANCEL_ENABLED=True)
    def test_cs08_ac6_manager_wins_then_job_skips(self):
        """Chiều ngược lại: Quản lý quyết định (giao luôn) trước; job tự huỷ chạy sau trên cùng task phải bỏ
        qua, không huỷ đơn đã được Quản lý xử lý (khớp CS-08-AC4, kiểm lại như một cặp tranh chấp hai chiều)."""
        t0 = timezone.now().replace(hour=9, minute=25, second=0, microsecond=0)
        order, note, task = self._create_escalated_order(t0)

        # Quản lý thắng, quyết định trước khi job kịp chạy
        result = cskh_services.decide(
            task.pk, self.ql, "DELIVER_WITHOUT_CONFIRM",
            reason="Khách quen, địa chỉ đã giao nhiều lần", now=t0 + timedelta(minutes=5),
        )
        self.assertEqual(result["note_status"], "PREPARING")

        note.refresh_from_db()
        task.refresh_from_db()
        self.assertEqual(note.status, DeliveryNote.Status.PREPARING)
        self.assertEqual(task.state, ConfirmationTask.State.DONE)

        # Job chạy sau (thua) -> phải bỏ qua hoàn toàn, đơn vẫn PROCESSING/không bị huỷ
        t_job = t0 + timedelta(minutes=31)
        res = cskh_services.auto_cancel_overdue(now=t_job)
        self.assertEqual(res["cancelled"], 0)
        self.assertEqual(res["blocked"], 0)

        order.refresh_from_db()
        self.assertNotEqual(order.status, SalesOrder.Status.CANCELLED)
        self.assertEqual(Refund.objects.filter(sales_invoice=order.invoice).count(), 0)
        self.assertFalse(AuditLog.objects.filter(action="order_auto_cancelled", object_id=str(order.pk)).exists())

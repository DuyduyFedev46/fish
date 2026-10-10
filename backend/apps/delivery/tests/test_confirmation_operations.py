"""
Kiểm thử tự động Lô 4 CSKH: Hoàn thiện vận hành (2026-09-28-cskh-xac-nhan-in-tem).
Bao phủ:
- CS-12: Đổi địa chỉ hoặc người nhận khi gọi (BR-GH-15, BR-BH-14, vô hiệu tem)
- CS-13: Khách muốn huỷ / đổi món (WANT_CANCEL, WANT_CHANGE, không tự huỷ)
- CS-14: In lại tem, huỷ tem giấy (BR-GH-16, BR-GH-17, BR-GH-07)
- CS-15: "Cần chú ý" cho việc gọi và tem (GET /api/dashboard/attention/)
- Bất biến 1 (không rò giá vốn) & Bất biến 9 (không rò PII)
"""
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.common.cost_keys import COST_KEYS
from apps.common.exceptions import BusinessError
from apps.common.tests.fixtures import client_for, make_user
from apps.delivery.confirmation import services as confirmation_services
from apps.delivery.labels import services as label_services
from apps.delivery.models import ConfirmationTask, CustomerCall, DeliveryNote, LabelPrint
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, StockLedgerEntry, Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import Customer, Refund, SalesInvoice, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.payments import services as payment_services
from apps.accounts import roles


class ConfirmationL4BaseTestCase(TestCase):
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

        self.chu = make_user("chu1", roles.OWNER)
        self.ql = make_user("ql1", roles.MANAGER)
        self.cs1 = make_user("cs1", roles.CUSTOMER_SERVICE)
        self.kho = make_user("kho1", roles.WAREHOUSE_STAFF)
        self.giao = make_user("giao1", roles.DELIVERY_STAFF)

    def _create_order_with_confirmation(self, *, phone="0900000123", name="Khách Thử A", qty=Decimal("2")):
        order = order_services.create_order(
            customer_phone=phone,
            customer_name=name,
            delivery_address="Số 1 Đường Thử, P. Thử, Lâm Đồng",
            phone=phone,
            lines=[{"item_code": self.item.code, "qty": qty}],
        )
        payment_services.confirm_payment(
            order=order,
            bank_txn_id=f"TXN-{uuid.uuid4().hex[:8]}",
            amount=order.total_amount,
            received_at=timezone.now(),
        )
        order.refresh_from_db()
        note = DeliveryNote.objects.get(sales_invoice__sales_order=order)
        task = ConfirmationTask.objects.get(note=note)
        return order, note, task


class TestCS12ChangeRecipient(ConfirmationL4BaseTestCase):
    def test_cs12_ac1_change_address_and_recipient(self):
        """Phiếu CONFIRMING: cs1 đổi địa chỉ + người nhận -> SalesOrder đổi address; phone/Customer giữ nguyên; AuditLog chỉ tên field."""
        order, note, task = self._create_order_with_confirmation()
        customer = order.customer
        old_customer_addr = customer.default_address

        client_cs1 = client_for(self.cs1)
        resp = client_cs1.post(
            f"/api/confirmation/queue/{note.pk}/recipient/",
            {
                "delivery_address": "Số 2 Đường Thử, P. Thử, Lâm Đồng",
                "recipient_name": "Người Nhận Hộ",
                "recipient_phone": "0900000456",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(set(data["changed"]), {"delivery_address", "recipient_name", "recipient_phone"})
        self.assertFalse(data["label_invalidated"])

        order.refresh_from_db()
        note.refresh_from_db()
        customer.refresh_from_db()

        self.assertEqual(order.delivery_address, "Số 2 Đường Thử, P. Thử, Lâm Đồng")
        self.assertEqual(order.phone, "0900000123")  # Không đổi
        self.assertEqual(customer.default_address, old_customer_addr)  # Không đổi
        self.assertEqual(note.recipient_name, "Người Nhận Hộ")
        self.assertEqual(note.recipient_phone, "0900000456")

        audit = AuditLog.objects.filter(action="recipient_changed", object_id=str(note.pk)).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor, self.cs1)
        self.assertEqual(audit.changes, {"fields": ["delivery_address", "recipient_name", "recipient_phone"]})
        self.assertNotIn("Số 2 Đường Thử", str(audit.changes))
        self.assertNotIn("0900000456", str(audit.changes))

    def test_cs12_ac2_confirmed_changed(self):
        """Ghi kết quả CONFIRMED_CHANGED -> phiếu PREPARING, task DONE."""
        order, note, task = self._create_order_with_confirmation()
        client_cs1 = client_for(self.cs1)
        resp = client_cs1.post(
            f"/api/confirmation/queue/{note.pk}/calls/",
            {"result": "CONFIRMED_CHANGED", "note": "Đã đổi địa chỉ"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        note.refresh_from_db()
        task.refresh_from_db()
        self.assertEqual(note.status, DeliveryNote.Status.PREPARING)
        self.assertEqual(task.state, ConfirmationTask.State.DONE)

    def test_cs12_ac3_label_invalidated_when_address_changed(self):
        """Phiếu PREPARING đã in tem lần 1 -> Đổi địa chỉ -> label_invalidated=True, tem lần 1 có superseded_at, to_void=[1]."""
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="CONFIRMED")
        note.refresh_from_db()

        # Kho in tem lần 1
        lp, dup = label_services.record_print(note, self.kho)
        self.assertEqual(lp.print_no, 1)

        # CSKH đổi địa chỉ
        client_cs1 = client_for(self.cs1)
        resp = client_cs1.post(
            f"/api/confirmation/queue/{note.pk}/recipient/",
            {"delivery_address": "Số 99 Đường Mới, P. Mới, Đà Lạt"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["label_invalidated"])

        lp.refresh_from_db()
        self.assertIsNotNone(lp.superseded_at)

        # Xem chi tiết phiếu giao qua API
        client_kho = client_for(self.kho)
        resp_note = client_kho.get(f"/api/delivery/notes/{note.pk}/")
        self.assertEqual(resp_note.status_code, 200)
        label_info = resp_note.json()["label"]
        self.assertEqual(label_info["to_void"], [1])
        self.assertEqual(label_info["needs_void"], 1)

    def test_cs12_ac4_blocked_when_ready_or_delivering(self):
        """Phiếu READY hoặc DELIVERING -> Đổi -> 400 BR-GH-15."""
        order, note, task = self._create_order_with_confirmation()
        note.status = DeliveryNote.Status.READY
        note.save(update_fields=["status"])

        client_ql = client_for(self.ql)
        resp = client_ql.post(
            f"/api/confirmation/queue/{note.pk}/recipient/",
            {"delivery_address": "Số 3 Đường Thử"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-GH-15")

        note.status = DeliveryNote.Status.DELIVERING
        note.save(update_fields=["status"])
        resp2 = client_ql.post(
            f"/api/confirmation/queue/{note.pk}/recipient/",
            {"delivery_address": "Số 3 Đường Thử"},
            format="json",
        )
        self.assertEqual(resp2.status_code, 400)
        self.assertEqual(resp2.json()["code"], "BR-GH-15")

    def test_cs12_ac5_validation_errors(self):
        """recipient_phone không phải 10 số bắt đầu bằng 0 -> 400 BR-BH-14; delivery_address rỗng -> 400."""
        order, note, task = self._create_order_with_confirmation()
        client_cs1 = client_for(self.cs1)

        # SĐT sai (9 số)
        resp = client_cs1.post(
            f"/api/confirmation/queue/{note.pk}/recipient/",
            {"recipient_phone": "091234567"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-BH-14")

        # Địa chỉ rỗng
        resp2 = client_cs1.post(
            f"/api/confirmation/queue/{note.pk}/recipient/",
            {"delivery_address": "   "},
            format="json",
        )
        self.assertEqual(resp2.status_code, 400)
        self.assertEqual(resp2.json()["code"], "INVALID_INPUT")

    def test_cs12_ac6_shop_lookup_with_original_phone(self):
        """Sau khi đổi người nhận hộ, khách tra đơn bằng 4 số cuối SĐT cũ -> vẫn tra được 200."""
        order, note, task = self._create_order_with_confirmation(phone="0900000123")
        confirmation_services.change_recipient(
            task.pk, self.cs1, recipient_name="Người Hộ", recipient_phone="0988888999"
        )
        client = client_for(None)
        resp = client.get(f"/api/shop/orders/{order.code}/?phone_last4=0123")
        self.assertEqual(resp.status_code, 200)

    def test_cs12_ac7_no_old_address_in_audit_or_logs(self):
        """Tìm chuỗi địa chỉ cũ trong AuditLog -> không có (thu tối thiểu)."""
        order, note, task = self._create_order_with_confirmation()
        old_addr = order.delivery_address
        confirmation_services.change_recipient(task.pk, self.cs1, delivery_address="Địa chỉ hoàn toàn mới số 99")

        audits = AuditLog.objects.filter(object_id=str(note.pk))
        for a in audits:
            self.assertNotIn(old_addr, str(a.changes))
            self.assertNotIn(old_addr, a.note or "")

    def test_cs12_ac8_label_prints_recipient_name_and_masked_phone(self):
        """Có người nhận hộ -> mở tem (CS-11) in tên và SĐT người nhận hộ đã che."""
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="CONFIRMED")
        note.refresh_from_db()
        confirmation_services.change_recipient(
            task.pk, self.cs1, recipient_name="Cô Ba Nhận Giúp", recipient_phone="0911223344"
        )

        client_kho = client_for(self.kho)
        resp = client_kho.get(f"/api/delivery/notes/{note.pk}/label/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["recipient_name"], "Cô Ba Nhận Giúp")
        self.assertEqual(data["recipient_phone_masked"], "xxxxxx3344")

    def test_cs12_ac9_permissions(self):
        """kho1, giao1 gọi POST recipient -> 403."""
        order, note, task = self._create_order_with_confirmation()
        for u in (self.kho, self.giao):
            c = client_for(u)
            resp = c.post(
                f"/api/confirmation/queue/{note.pk}/recipient/",
                {"recipient_name": "Người Nhận"},
                format="json",
            )
            self.assertEqual(resp.status_code, 403)


class TestCS13CustomerCancellationAndChange(ConfirmationL4BaseTestCase):
    def test_cs13_ac1_want_cancel_escalates_without_deadline(self):
        """cs1 ghi WANT_CANCEL -> task ESCALATED, nhãn 'Khách muốn huỷ', decide_deadline=None."""
        order, note, task = self._create_order_with_confirmation()
        client_cs1 = client_for(self.cs1)
        resp = client_cs1.post(
            f"/api/confirmation/queue/{note.pk}/calls/",
            {"result": "WANT_CANCEL", "note": "Khách đổi ý không lấy nữa"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        task.refresh_from_db()
        self.assertEqual(task.state, ConfirmationTask.State.ESCALATED)
        self.assertEqual(task.escalation_reason, ConfirmationTask.EscalationReason.WANT_CANCEL)

        # Xem qua hàng chờ CSKH
        resp_q = client_cs1.get(f"/api/confirmation/queue/{note.pk}/")
        self.assertEqual(resp_q.status_code, 200)
        data = resp_q.json()
        self.assertEqual(data["escalation_label"], "Khách muốn huỷ đơn")
        self.assertIsNone(data["decide_deadline"])

    def test_cs13_ac2_manager_cancels_want_cancel_order(self):
        """Quản lý decide CANCEL trên đơn WANT_CANCEL -> đơn CANCELLED, hoàn kho, suggest_refund_amount."""
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="WANT_CANCEL")

        client_ql = client_for(self.ql)
        resp = client_ql.post(
            f"/api/confirmation/queue/{note.pk}/decide/",
            {"decision": "CANCEL", "reason_code": "CUSTOMER_CHANGED_MIND", "reason": "Khách xác nhận huỷ"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["note_status"], "CANCELLED")
        self.assertEqual(data["suggest_refund_amount"], str(int(order.total_amount)))

        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.CANCELLED)

    def test_cs13_ac3_want_change_escalates(self):
        """cs1 ghi WANT_CHANGE -> ESCALATED, nhãn 'Khách muốn đổi món' (T37), decide_deadline=None."""
        order, note, task = self._create_order_with_confirmation()
        client_cs1 = client_for(self.cs1)
        resp = client_cs1.post(
            f"/api/confirmation/queue/{note.pk}/calls/",
            {"result": "WANT_CHANGE", "note": "Muốn đổi sang mực lá"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        task.refresh_from_db()
        self.assertEqual(task.state, ConfirmationTask.State.ESCALATED)
        self.assertEqual(task.escalation_reason, ConfirmationTask.EscalationReason.WANT_CHANGE)

        resp_q = client_cs1.get(f"/api/confirmation/queue/{note.pk}/")
        data = resp_q.json()
        self.assertEqual(data["escalation_label"], "Khách muốn đổi món")
        self.assertIsNone(data["decide_deadline"])

    def test_cs13_ac4_cs1_cannot_cancel_sales_order(self):
        """cs1 gọi POST /api/sales/orders/{id}/cancel -> 403."""
        order, note, task = self._create_order_with_confirmation()
        client_cs1 = client_for(self.cs1)
        resp = client_cs1.post(f"/api/sales/orders/{order.pk}/cancel/", {"reason": "Huỷ"})
        self.assertEqual(resp.status_code, 403)

    def test_cs13_ac5_cs1_cannot_modify_order_lines(self):
        """cs1 gửi sửa dòng hàng / số kg của đơn -> 405/403."""
        order, note, task = self._create_order_with_confirmation()
        client_cs1 = client_for(self.cs1)
        resp = client_cs1.patch(f"/api/sales/orders/{order.pk}/", {"lines": []})
        self.assertIn(resp.status_code, (403, 405))


class TestCS14LabelReprintAndVoid(ConfirmationL4BaseTestCase):
    def test_cs14_ac1_reprint_label_invalidates_previous_and_sets_to_void(self):
        """Tem lần 1 đã in -> NV kho bấm 'In lại' -> print_no=2, is_reprint=True; tem lần 1 có superseded_at, to_void=[1]."""
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="CONFIRMED")
        note.refresh_from_db()

        client_kho = client_for(self.kho)
        # In lần 1
        resp1 = client_kho.post(f"/api/delivery/notes/{note.pk}/label/print/")
        self.assertEqual(resp1.status_code, 201)
        self.assertEqual(resp1.json()["print_no"], 1)

        # In lần 2 (In lại)
        resp2 = client_kho.post(f"/api/delivery/notes/{note.pk}/label/print/")
        self.assertEqual(resp2.status_code, 201)
        data2 = resp2.json()
        self.assertEqual(data2["print_no"], 2)
        self.assertTrue(data2["is_reprint"])

        lp1 = note.label_prints.get(print_no=1)
        self.assertIsNotNone(lp1.superseded_at)

        resp_detail = client_kho.get(f"/api/delivery/notes/{note.pk}/")
        label_info = resp_detail.json()["label"]
        self.assertEqual(label_info["valid_print_no"], 2)
        self.assertEqual(label_info["to_void"], [1])

        audit = AuditLog.objects.filter(action="label_reprinted", object_id=str(note.pk)).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.changes["print_no"], 2)

    def test_cs14_ac2_void_label(self):
        """Bấm 'Đã huỷ tem' lần 1 -> voided_at/by lưu, AuditLog label_voided, hết nhắc to_void=[]."""
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="CONFIRMED")
        note.refresh_from_db()
        label_services.record_print(note, self.kho)
        label_services.record_print(note, self.kho)  # In lần 2 -> lần 1 cần huỷ

        client_kho = client_for(self.kho)
        resp_void = client_kho.post(
            f"/api/delivery/notes/{note.pk}/label/void/",
            {"print_no": 1},
            format="json",
        )
        self.assertEqual(resp_void.status_code, 200)
        data = resp_void.json()
        self.assertEqual(data["print_no"], 1)
        self.assertFalse(data["already"])
        self.assertIsNotNone(data["voided_at"])

        lp1 = note.label_prints.get(print_no=1)
        self.assertIsNotNone(lp1.voided_at)
        self.assertEqual(lp1.voided_by, self.kho)

        audit = AuditLog.objects.filter(action="label_voided", object_id=str(note.pk)).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.changes["print_no"], 1)

        # Xem lại chi tiết phiếu: to_void rỗng
        resp_detail = client_kho.get(f"/api/delivery/notes/{note.pk}/")
        self.assertEqual(resp_detail.json()["label"]["to_void"], [])

    def test_cs14_ac3_cancelled_order_marks_all_labels_to_void(self):
        """Đơn có tem lần 1 bị huỷ -> get_label trả valid_print_no=None, to_void=[1]."""
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="CONFIRMED")
        note.refresh_from_db()
        label_services.record_print(note, self.kho)

        order_services.cancel_paid_order(order=order, actor=self.ql, reason="Huỷ")
        note.refresh_from_db()

        client_kho = client_for(self.kho)
        resp = client_kho.get(f"/api/delivery/notes/{note.pk}/")
        label_info = resp.json()["label"]
        self.assertIsNone(label_info["valid_print_no"])
        self.assertEqual(label_info["to_void"], [1])

    def test_cs14_ac4_cannot_void_valid_active_label(self):
        """Tem lần 2 đang hiệu lực, đơn còn hoạt động -> void lần 2 -> 400 BR-GH-16."""
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="CONFIRMED")
        note.refresh_from_db()
        label_services.record_print(note, self.kho)
        label_services.record_print(note, self.kho)  # In lần 2

        client_kho = client_for(self.kho)
        resp = client_kho.post(
            f"/api/delivery/notes/{note.pk}/label/void/",
            {"print_no": 2},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-GH-16")

    def test_cs14_ac5_void_already_voided_is_idempotent(self):
        """Lần 1 đã huỷ -> void lần 1 lại -> 200 already: True, không thêm AuditLog."""
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="CONFIRMED")
        note.refresh_from_db()
        label_services.record_print(note, self.kho)
        label_services.record_print(note, self.kho)
        label_services.void_label(note, self.kho, print_no=1)
        audit_count = AuditLog.objects.filter(action="label_voided").count()

        client_kho = client_for(self.kho)
        resp = client_kho.post(
            f"/api/delivery/notes/{note.pk}/label/void/",
            {"print_no": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["already"])
        self.assertEqual(AuditLog.objects.filter(action="label_voided").count(), audit_count)

    def test_cs14_ac6_cannot_reprint_on_cancelled_order(self):
        """Đơn CANCELLED -> 'In lại' -> 400 BR-GH-07."""
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="CONFIRMED")
        note.refresh_from_db()
        label_services.record_print(note, self.kho)

        order_services.cancel_paid_order(order=order, actor=self.ql, reason="Huỷ")
        note.refresh_from_db()

        client_kho = client_for(self.kho)
        resp = client_kho.post(f"/api/delivery/notes/{note.pk}/label/print/")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["code"], "BR-GH-07")

    def test_cs14_ac7_permissions(self):
        """cs1, giao1 gọi label/print hoặc label/void -> 403."""
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="CONFIRMED")
        note.refresh_from_db()
        for u in (self.cs1, self.giao):
            c = client_for(u)
            self.assertEqual(c.post(f"/api/delivery/notes/{note.pk}/label/print/").status_code, 403)
            self.assertEqual(c.post(f"/api/delivery/notes/{note.pk}/label/void/", {"print_no": 1}).status_code, 403)



class TestCS15DashboardAttention(ConfirmationL4BaseTestCase):
    def test_cs15_ac1_owner_sees_all_6_keys(self):
        """Chủ gọi GET /api/dashboard/attention/ -> có đủ 6 khoá + expired_batches_open (P8 Lô 5, BR-LO-07); không còn khoá `cskh_*` (P8b Lô 5)."""
        client_chu = client_for(self.chu)
        resp = client_chu.get("/api/dashboard/attention/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        expected_keys = {
            "confirmation_queue_waiting", "confirmation_escalated", "confirmation_auto_cancel_blocked",
            "refund_calls_open", "labels_not_printed", "labels_to_void",
            "expired_batches_open",
        }
        self.assertEqual(set(data.keys()), expected_keys)

    def test_cs15_ac2_confirmation_queue_waiting_threshold(self):
        """Phiếu PENDING trả tiền 61 phút trước -> tính vào confirmation_queue_waiting; 59 phút -> không tính."""
        order, note, task = self._create_order_with_confirmation()
        inv = note.sales_invoice

        now = timezone.now()
        # Đơn trả 59 phút trước (< 60')
        inv.issued_at = now - timedelta(minutes=59)
        inv.save(update_fields=["issued_at"])

        client_chu = client_for(self.chu)
        resp1 = client_chu.get("/api/dashboard/attention/")
        self.assertEqual(resp1.json()["confirmation_queue_waiting"], 0)

        # Đơn trả 61 phút trước (>= 60')
        inv.issued_at = now - timedelta(minutes=61)
        inv.save(update_fields=["issued_at"])

        resp2 = client_chu.get("/api/dashboard/attention/")
        self.assertEqual(resp2.json()["confirmation_queue_waiting"], 1)

    def test_cs15_ac3_labels_not_printed_threshold(self):
        """Phiếu PREPARING xác nhận 16 phút trước, chưa in -> labels_not_printed=1; 14 phút -> 0."""
        order, note, task = self._create_order_with_confirmation()
        confirmation_services.record_call(task.pk, self.cs1, result="CONFIRMED")
        note.refresh_from_db()

        now = timezone.now()
        note.confirmed_at = now - timedelta(minutes=14)
        note.save(update_fields=["confirmed_at"])

        client_chu = client_for(self.chu)
        resp1 = client_chu.get("/api/dashboard/attention/")
        self.assertEqual(resp1.json()["labels_not_printed"], 0)

        note.confirmed_at = now - timedelta(minutes=16)
        note.save(update_fields=["confirmed_at"])

        resp2 = client_chu.get("/api/dashboard/attention/")
        self.assertEqual(resp2.json()["labels_not_printed"], 1)

    def test_cs15_ac4_permissions_filter_keys(self):
        """cs1: chỉ confirmation_queue_waiting, refund_calls_open. kho1: chỉ labels_not_printed, labels_to_void. ql: cả 6."""
        client_cs1 = client_for(self.cs1)
        resp_cs1 = client_cs1.get("/api/dashboard/attention/")
        self.assertEqual(resp_cs1.status_code, 200)
        self.assertEqual(set(resp_cs1.json().keys()), {"confirmation_queue_waiting", "refund_calls_open"})

        client_kho = client_for(self.kho)
        resp_kho = client_kho.get("/api/dashboard/attention/")
        self.assertEqual(resp_kho.status_code, 200)
        self.assertEqual(set(resp_kho.json().keys()), {"labels_not_printed", "labels_to_void"})

        client_ql = client_for(self.ql)
        resp_ql = client_ql.get("/api/dashboard/attention/")
        self.assertEqual(resp_ql.status_code, 200)
        self.assertEqual(len(resp_ql.json().keys()), 6)  # khoá `cskh_*` cũ đã gỡ ở Lô 5

    def test_cs15_ac5_delivery_staff_forbidden(self):
        """giao1 gọi -> 403."""
        client_giao = client_for(self.giao)
        resp = client_giao.get("/api/dashboard/attention/")
        self.assertEqual(resp.status_code, 403)

    def test_cs15_ac6_no_cost_or_pii_keys(self):
        """Attention response không có khoá giá vốn (Bất biến 1) hay PII (Bất biến 9)."""
        client_chu = client_for(self.chu)
        data = client_chu.get("/api/dashboard/attention/").json()
        forbidden_keys = COST_KEYS | {"customer", "phone", "address", "name", "recipient"}
        for k in data.keys():
            self.assertNotIn(k, forbidden_keys)

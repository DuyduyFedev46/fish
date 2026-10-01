"""
Kiểm thử tự động toàn diện Lô 2 CSKH (2026-09-28-cskh-xac-nhan-in-tem).
Bao phủ:
- CS-04: Tạo phiếu CONFIRMING + ConfirmationTask PENDING, huỷ hoàn kho, chống trùng
- CS-05: Hàng chờ CSKH, claim khoá mềm, che PII ngoài scope, tìm kiếm POST + throttle
- CS-06: Ghi kết quả cuộc gọi, BR-GH-19 kiểm PII ghi chú, unconfirm chặn BR-GH-16, đổi người nhận
- CS-11: In tem 100x150 mm, không rò giá vốn / tiền, chặn khi chưa xác nhận hoặc đã huỷ, idempotent
- Bất biến 1 & Bất biến 9, Header Cache-Control: no-store
"""
import datetime
from decimal import Decimal
import uuid

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.common.exceptions import BusinessError
from apps.common.tests.fixtures import client_for, confirm_note_for_test, make_user
from apps.delivery.confirmation import services as confirmation_services
from apps.delivery.labels import services as label_services
from apps.delivery.models import ConfirmationTask, CustomerCall, DeliveryNote, LabelPrint
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, StockLedgerEntry, Warehouse
from apps.purchasing.models import Supplier
from apps.sales.models import Customer, SalesInvoice, SalesInvoiceLine, SalesOrder
from apps.sales.models.invoices import SalesInvoiceLineBatch
from apps.sales.orders import services as order_services
from apps.sales.payments import services as payment_services
from apps.accounts import roles


class ConfirmationL2BaseTestCase(TestCase):
    def setUp(self):
        # Master data
        self.wh = Warehouse.objects.create(name="Kho chính")
        self.sup = Supplier.objects.create(name="Tàu cá Long Hải")
        self.pl = PriceList.objects.create(name="Bán lẻ", is_default=True)
        grp = ItemGroup.objects.create(name="Hải sản")

        self.item = Item.objects.create(code="CA-THU", name="Cá thu", item_group=grp)
        today = timezone.localdate()
        ItemPrice.objects.create(
            price_list=self.pl, item=self.item, rate=Decimal("150000"),
            valid_from=today - datetime.timedelta(days=1),
        )
        self.batch = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh,
            received_date=today, qty=Decimal("100"), purchase_rate=Decimal("110000"),
        )
        batch_services.publish_batch(batch=self.batch, actor=None)

        # Users
        self.chu = make_user("chu1", roles.OWNER)
        self.ql = make_user("ql1", roles.MANAGER)
        self.cs1 = make_user("cs1", roles.CUSTOMER_SERVICE)
        self.cs2 = make_user("cs2", roles.CUSTOMER_SERVICE)
        self.kho = make_user("kho1", roles.WAREHOUSE_STAFF)
        self.giao = make_user("giao1", roles.DELIVERY_STAFF)

    def _create_paid_order(self, code="DH-TEST-01", phone="0901112233", qty="2"):
        """Tạo đơn và thanh toán, trả về (order, invoice, note, task)."""
        order = order_services.create_order(
            customer_phone=phone,
            customer_name=f"Khách {code}",
            delivery_address="123 Nguyễn Huệ, Q1, TP.HCM",
            phone=phone,
            lines=[{"item_code": self.item.code, "qty": Decimal(qty)}],
        )
        if code:
            SalesOrder.objects.filter(pk=order.pk).update(code=code)
            order.refresh_from_db()
        payment_services.confirm_payment(
            order=order,
            bank_txn_id=f"TXN-{code}",
            amount=order.total_amount,
            received_at=timezone.now(),
        )
        order.refresh_from_db()
        invoice = order.invoice
        note = invoice.delivery_notes.get()
        task = getattr(note, "confirmation", None)
        return order, invoice, note, task


class CS04StartConfirmationTests(ConfirmationL2BaseTestCase):
    def test_cs04_ac1_signal_creates_note_confirming_and_task_pending(self):
        """CS-04-AC1: Hoá đơn ISSUED -> tự động tạo DeliveryNote CONFIRMING + ConfirmationTask PENDING."""
        order, invoice, note, task = self._create_paid_order("DH-CS04-1", "0901234567")
        self.assertEqual(note.status, DeliveryNote.Status.CONFIRMING)
        self.assertIsNotNone(task)
        self.assertEqual(task.state, ConfirmationTask.State.PENDING)
        self.assertEqual(task.attempts, 0)

    def test_cs04_ac3_idempotent_ipn_does_not_duplicate(self):
        """CS-04-AC3: Gọi start_confirmation lần 2 trên cùng hoá đơn -> không sinh thêm."""
        order, invoice, note, task = self._create_paid_order("DH-CS04-2", "0901234568")
        note2, task2 = confirmation_services.start_confirmation(invoice)
        self.assertEqual(note.pk, note2.pk)
        self.assertEqual(task.pk, task2.pk)
        self.assertEqual(DeliveryNote.objects.filter(sales_invoice=invoice).count(), 1)
        self.assertEqual(ConfirmationTask.objects.filter(note=note).count(), 1)

    def test_cs04_ac5_cancel_paid_order_when_confirming_restores_stock(self):
        """CS-04-AC5: Huỷ đơn khi phiếu ở CONFIRMING -> hoàn kho về đúng lô gốc, ConfirmationTask sang DONE."""
        order, invoice, note, task = self._create_paid_order("DH-CS04-3", "0901234569", qty="3")
        self.batch.refresh_from_db()
        available_before = self.batch.qty_available

        res = order_services.cancel_paid_order(
            order=order, actor=self.ql, reason="Khách đổi ý", reason_code="CUSTOMER_CHANGED_MIND"
        )
        self.assertTrue(res["stock_restored"])
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, available_before + Decimal("3"))

        note.refresh_from_db()
        task.refresh_from_db()
        self.assertEqual(note.status, DeliveryNote.Status.CANCELLED)
        self.assertEqual(task.state, ConfirmationTask.State.DONE)
        self.assertTrue(
            StockLedgerEntry.objects.filter(
                batch=self.batch, movement_type=StockLedgerEntry.MovementType.CANCEL_RESTORE
            ).exists()
        )


class CS05QueueAndSearchTests(ConfirmationL2BaseTestCase):
    def test_cs05_ac1_queue_list_default_and_ordering(self):
        """CS-05-AC1: Mặc định trả PENDING + CALLBACK hợp lệ, sắp theo paid_at tăng."""
        o1, _, n1, _ = self._create_paid_order("DH-Q1", "0901111111")
        o2, _, n2, _ = self._create_paid_order("DH-Q2", "0902222222")

        client = client_for(self.cs1)
        resp = client.get("/api/confirmation/queue/")
        self.assertEqual(resp.status_code, 200)
        results = resp.json().get("results", [])
        self.assertGreaterEqual(len(results), 2)
        note_ids = [r["note_id"] for r in results]
        self.assertIn(n1.pk, note_ids)
        self.assertIn(n2.pk, note_ids)

    def test_cs05_ac3_ac4_claim_task_soft_lock_and_expiry(self):
        """CS-05-AC3, AC4: Claim khoá mềm trong CONFIRMATION_CLAIM_MINUTES, trả 409 khi người khác giữ."""
        _, _, n1, t1 = self._create_paid_order("DH-CLAIM", "0903333333")
        client1 = client_for(self.cs1)
        client2 = client_for(self.cs2)

        # cs1 claim
        resp1 = client1.post(f"/api/confirmation/queue/{n1.pk}/claim/")
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp1.json()["claimed_by"]["id"], self.cs1.pk)

        # cs2 claim -> 409 CLAIMED
        resp2 = client2.post(f"/api/confirmation/queue/{n1.pk}/claim/")
        self.assertEqual(resp2.status_code, 409)
        self.assertEqual(resp2.json()["code"], "CLAIMED")
        self.assertIn("xử lý", resp2.json()["detail"])

        # Sau khi hết hạn (chỉnh claimed_until về quá khứ) -> cs2 claim thành công
        t1.refresh_from_db()
        t1.claimed_until = timezone.now() - datetime.timedelta(minutes=1)
        t1.save(update_fields=["claimed_until"])

        resp2_retry = client2.post(f"/api/confirmation/queue/{n1.pk}/claim/")
        self.assertEqual(resp2_retry.status_code, 200)
        self.assertEqual(resp2_retry.json()["claimed_by"]["id"], self.cs2.pk)

    def test_cs05_ac5_in_scope_and_pii_masking(self):
        """CS-05-AC5: Ngoài phạm vi thì customer_name/address/phone=None, chỉ có phone_masked."""
        # Tạo đơn và chuyển sang READY (ngoài scope CSKH nếu chưa gọi)
        _, _, n1, t1 = self._create_paid_order("DH-SCOPE", "0904444555")
        confirm_note_for_test(n1)
        n1.status = DeliveryNote.Status.READY
        n1.save(update_fields=["status"])
        t1.state = ConfirmationTask.State.DONE
        t1.save(update_fields=["state"])

        client = client_for(self.cs1)
        # Xem queue với state=DONE (hoặc gọi search)
        resp = client.get(f"/api/confirmation/queue/?state=DONE")
        results = [r for r in resp.json().get("results", []) if r["note_id"] == n1.pk]
        if results:
            row = results[0]
            self.assertFalse(row["in_scope"])
            self.assertIsNone(row["customer_name"])
            self.assertIsNone(row["phone"])
            self.assertIsNone(row["address"])
            self.assertEqual(row["phone_masked"], "09xx xxx 555")

    def test_cs05_ac6_search_endpoint(self):
        """CS-05-AC6: Search chỉ nhận POST (GET 405), tìm SĐT đủ số, tìm mã đơn, chặn SĐT một phần."""
        _, _, n1, _ = self._create_paid_order("DH-SRCH-01", "0908889999")
        client = client_for(self.cs1)

        # GET -> 405
        resp_get = client.get("/api/confirmation/search/?q=0908889999")
        self.assertEqual(resp_get.status_code, 405)

        # POST tìm SĐT đầy đủ
        resp_phone = client.post("/api/confirmation/search/", {"q": "0908889999"}, format="json")
        self.assertEqual(resp_phone.status_code, 200)
        results = resp_phone.json().get("results", [])
        self.assertTrue(any(r["note_id"] == n1.pk for r in results))

        # POST tìm mã đơn
        resp_code = client.post("/api/confirmation/search/", {"q": "DH-SRCH-01"}, format="json")
        self.assertEqual(resp_code.status_code, 200)
        self.assertTrue(any(r["note_id"] == n1.pk for r in resp_code.json().get("results", [])))

        # POST tìm SĐT một phần (< 9 số) -> 400 INVALID_QUERY
        resp_short = client.post("/api/confirmation/search/", {"q": "090888"}, format="json")
        self.assertEqual(resp_short.status_code, 400)
        self.assertEqual(resp_short.json()["code"], "INVALID_QUERY")

    @override_settings(CAVEVE_THROTTLE_RATES={"customer_search": "2/min"})
    def test_cs05_search_throttling(self):
        """CS-05-AC6: Throttle customer_search trả 429 khi vượt ngưỡng."""
        client = client_for(self.cs1)
        r1 = client.post("/api/confirmation/search/", {"q": "0908889999"}, format="json")
        r2 = client.post("/api/confirmation/search/", {"q": "0908889999"}, format="json")
        r3 = client.post("/api/confirmation/search/", {"q": "0908889999"}, format="json")
        self.assertEqual(r3.status_code, 429)

    def test_cs05_headers_and_permissions(self):
        """CS-05: Cache-Control: no-store và chặn người thiếu quyền."""
        client = client_for(self.cs1)
        resp = client.get("/api/confirmation/queue/")
        self.assertEqual(resp.headers.get("Cache-Control"), "no-store")

        kho_client = client_for(self.kho)
        self.assertEqual(kho_client.get("/api/confirmation/queue/").status_code, 403)
        self.assertEqual(kho_client.post("/api/confirmation/search/", {"q": "0908889999"}, format="json").status_code, 403)


class CS06RecordCallAndUnconfirmTests(ConfirmationL2BaseTestCase):
    def test_cs06_ac1_ac2_confirmed_advances_to_preparing_and_idempotent(self):
        """CS-06-AC1, AC2: Ghi CONFIRMED -> note sang PREPARING, task DONE, idempotent request_id."""
        _, _, note, task = self._create_paid_order("DH-CALL-01", "0901234567")
        client = client_for(self.cs1)
        req_id = str(uuid.uuid4())

        # Cuộc gọi xác nhận lần đầu
        resp = client.post(
            f"/api/confirmation/queue/{note.pk}/calls/",
            {"result": "CONFIRMED", "note": "Giao sau 17h", "request_id": req_id},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["note_status"], "PREPARING")
        self.assertIsNone(data["confirm_state"])
        self.assertFalse(data["duplicate"])

        note.refresh_from_db()
        task.refresh_from_db()
        self.assertEqual(note.status, DeliveryNote.Status.PREPARING)
        self.assertEqual(note.confirmed_by_id, self.cs1.pk)
        self.assertEqual(task.state, ConfirmationTask.State.DONE)

        # Gửi lại cùng request_id -> 200 duplicate=True
        resp_dup = client.post(
            f"/api/confirmation/queue/{note.pk}/calls/",
            {"result": "CONFIRMED", "note": "Giao sau 17h", "request_id": req_id},
            format="json",
        )
        self.assertEqual(resp_dup.status_code, 200)
        self.assertTrue(resp_dup.json()["duplicate"])
        self.assertEqual(CustomerCall.objects.filter(note=note).count(), 1)

    def test_cs06_ac3_callback_schedule(self):
        """CS-06-AC3: Ghi CALLBACK -> task sang CALLBACK, hẹn giờ tương lai."""
        _, _, note, task = self._create_paid_order("DH-CALL-02", "0901234568")
        client = client_for(self.cs1)
        future_time = timezone.now() + datetime.timedelta(hours=2)

        resp = client.post(
            f"/api/confirmation/queue/{note.pk}/calls/",
            {"result": "CALLBACK", "callback_at": future_time.isoformat()},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        task.refresh_from_db()
        self.assertEqual(task.state, ConfirmationTask.State.CALLBACK)
        self.assertIsNotNone(task.callback_at)

        # callback_at quá khứ -> 400 INVALID_INPUT
        past_time = timezone.now() - datetime.timedelta(hours=1)
        resp_bad = client.post(
            f"/api/confirmation/queue/{note.pk}/calls/",
            {"result": "CALLBACK", "callback_at": past_time.isoformat()},
            format="json",
        )
        self.assertEqual(resp_bad.status_code, 400)

    def test_cs06_ac4_ac5_unreachable_retry_interval_and_escalate(self):
        """CS-06-AC4, AC5: Chưa đủ 10 phút báo BR-GH-13, đủ 3 lần chuyển ESCALATED."""
        _, _, note, task = self._create_paid_order("DH-CALL-03", "0901234569")
        client = client_for(self.cs1)

        # Lần 1: UNREACHABLE -> attempts=1
        r1 = client.post(f"/api/confirmation/queue/{note.pk}/calls/", {"result": "UNREACHABLE"}, format="json")
        self.assertEqual(r1.status_code, 201)
        task.refresh_from_db()
        self.assertEqual(task.attempts, 1)
        self.assertEqual(task.state, ConfirmationTask.State.PENDING)

        # Gọi tiếp ngay -> 400 BR-GH-13
        r_too_soon = client.post(f"/api/confirmation/queue/{note.pk}/calls/", {"result": "UNREACHABLE"}, format="json")
        self.assertEqual(r_too_soon.status_code, 400)
        self.assertEqual(r_too_soon.json()["code"], "BR-GH-13")

        # Chỉnh last_unreachable_at lùi 11 phút để gọi lần 2
        task.last_unreachable_at = timezone.now() - datetime.timedelta(minutes=11)
        task.save(update_fields=["last_unreachable_at"])
        r2 = client.post(f"/api/confirmation/queue/{note.pk}/calls/", {"result": "UNREACHABLE"}, format="json")
        self.assertEqual(r2.status_code, 201)

        # Chỉnh lùi 11 phút để gọi lần 3 -> chuyển ESCALATED
        task.refresh_from_db()
        task.last_unreachable_at = timezone.now() - datetime.timedelta(minutes=11)
        task.save(update_fields=["last_unreachable_at"])
        r3 = client.post(f"/api/confirmation/queue/{note.pk}/calls/", {"result": "UNREACHABLE"}, format="json")
        self.assertEqual(r3.status_code, 201)

        task.refresh_from_db()
        self.assertEqual(task.attempts, 3)
        self.assertEqual(task.state, ConfirmationTask.State.ESCALATED)
        self.assertEqual(task.escalation_reason, ConfirmationTask.EscalationReason.UNREACHABLE)

    def test_cs06_ac6_pii_blocking_br_gh_19(self):
        """CS-06-AC6: Chặn SĐT hoặc STK trong ghi chú (BR-GH-19)."""
        _, _, note, _ = self._create_paid_order("DH-PII", "0901234570")
        client = client_for(self.cs1)

        bad_notes = [
            "Khách gọi lại số 0900.000.999",
            "SĐT phụ: 0900 000 999",
            "Chuyển qua số +84900000999",
            "STK Vietcombank: 101234567890",
            "A" * 201,  # vượt 200 ký tự
        ]
        for bn in bad_notes:
            resp = client.post(f"/api/confirmation/queue/{note.pk}/calls/", {"result": "CALLBACK", "note": bn}, format="json")
            self.assertEqual(resp.status_code, 400)
            self.assertIn(resp.json()["code"], ("BR-GH-19", "INVALID_INPUT"))

    def test_cs06_ac8_unconfirm_and_blocked_if_label_printed(self):
        """CS-06-AC8: Huỷ xác nhận PREPARING -> CONFIRMING, chặn BR-GH-16 khi tem đã in."""
        _, _, note, task = self._create_paid_order("DH-UNCONFIRM", "0901234571")
        client = client_for(self.cs1)

        # Xác nhận đơn
        client.post(f"/api/confirmation/queue/{note.pk}/calls/", {"result": "CONFIRMED"}, format="json")
        note.refresh_from_db()
        self.assertEqual(note.status, DeliveryNote.Status.PREPARING)

        # In tem
        label_services.record_print(note, self.kho)
        self.assertTrue(note.label_prints.exists())

        # Thử huỷ xác nhận khi tem đã in -> 400 BR-GH-16
        resp_blocked = client.post(f"/api/confirmation/queue/{note.pk}/unconfirm/", {"reason": "Nhầm đơn"}, format="json")
        self.assertEqual(resp_blocked.status_code, 400)
        self.assertEqual(resp_blocked.json()["code"], "BR-GH-16")

        # Huỷ tem đi để thử huỷ xác nhận thành công
        note.label_prints.all().delete()
        resp_ok = client.post(f"/api/confirmation/queue/{note.pk}/unconfirm/", {"reason": "Nhầm đơn"}, format="json")
        self.assertEqual(resp_ok.status_code, 200)
        note.refresh_from_db()
        task.refresh_from_db()
        self.assertEqual(note.status, DeliveryNote.Status.CONFIRMING)
        self.assertEqual(task.state, ConfirmationTask.State.PENDING)

    def test_cs06_change_recipient(self):
        """CS-06: Đổi thông tin người nhận hộ, vô hiệu tem cũ nếu đã in."""
        _, _, note, _ = self._create_paid_order("DH-RECIP", "0901234572")
        client = client_for(self.cs1)

        resp = client.post(
            f"/api/confirmation/queue/{note.pk}/recipient/",
            {"recipient_name": "Anh Ba Nhận Hộ", "recipient_phone": "0988776655"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(set(resp.json()["changed"]), {"recipient_name", "recipient_phone"})
        note.refresh_from_db()
        self.assertEqual(note.recipient_name, "Anh Ba Nhận Hộ")
        self.assertEqual(note.recipient_phone, "0988776655")

        # Kiểm tra AuditLog không rò PII (Bất biến 9, X-AC2)
        from apps.accounts.models import AuditLog
        audit = AuditLog.objects.filter(action="recipient_changed", object_id=str(note.pk)).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.changes, {"fields": ["recipient_name", "recipient_phone"]})
        self.assertNotIn("0988776655", str(audit.changes))
        self.assertNotIn("Anh Ba Nhận Hộ", str(audit.changes))



class CS11LabelPrintTests(ConfirmationL2BaseTestCase):
    def test_cs11_ac1_preview_label_data_no_cost_no_amount(self):
        """CS-11-AC1, AC4: Xem trước tem giao hàng, SĐT che, tuyệt đối không có giá tiền hay giá vốn."""
        _, _, note, _ = self._create_paid_order("DH-LBL-01", "0905556666", qty="2")
        confirm_note_for_test(note)

        client = client_for(self.kho)
        resp = client.get(f"/api/delivery/notes/{note.pk}/label/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["note_code"], note.code)
        self.assertEqual(data["order_code"], "DH-LBL-01")
        self.assertEqual(data["print_no"], 1)
        self.assertEqual(data["barcode_value"], f"{note.code}.1")
        self.assertEqual(data["recipient_phone_masked"], "09xx xxx 666")
        self.assertEqual(data["paid_text"], "ĐÃ THANH TOÁN – không thu thêm")
        self.assertEqual(data["total_kg"], "2.000")

        # Bất biến: không có khoá tiền hay giá vốn
        for forbidden in ("total_amount", "amount", "price", "rate", "cost", "unit_cost", "profit"):
            self.assertNotIn(forbidden, data)

    def test_cs11_ac2_record_print_and_idempotent(self):
        """CS-11-AC2: Ghi nhận in tem, idempotent theo request_id, lần 2 đánh dấu is_reprint."""
        _, _, note, _ = self._create_paid_order("DH-LBL-02", "0905556667")
        confirm_note_for_test(note)
        client = client_for(self.kho)
        req_id = str(uuid.uuid4())

        # Lần 1: in mới
        r1 = client.post(f"/api/delivery/notes/{note.pk}/label/print/", {"request_id": req_id}, format="json")
        self.assertEqual(r1.status_code, 201)
        d1 = r1.json()
        self.assertEqual(d1["print_no"], 1)
        self.assertFalse(d1["is_reprint"])
        self.assertFalse(d1["duplicate"])

        # Gửi lại cùng request_id -> 200 duplicate=True
        r1_dup = client.post(f"/api/delivery/notes/{note.pk}/label/print/", {"request_id": req_id}, format="json")
        self.assertEqual(r1_dup.status_code, 200)
        self.assertTrue(r1_dup.json()["duplicate"])

        # In lần 2 (khác request_id) -> print_no=2, is_reprint=True
        r2 = client.post(f"/api/delivery/notes/{note.pk}/label/print/", {"request_id": str(uuid.uuid4())}, format="json")
        self.assertEqual(r2.status_code, 201)
        d2 = r2.json()
        self.assertEqual(d2["print_no"], 2)
        self.assertTrue(d2["is_reprint"])

    def test_cs11_ac3_cannot_print_if_confirming_or_cancelled(self):
        """CS-11-AC3: Chặn in tem khi phiếu ở CONFIRMING (BR-GH-09) hoặc CANCELLED (BR-GH-07)."""
        _, _, note, _ = self._create_paid_order("DH-LBL-03", "0905556668")
        client = client_for(self.kho)

        # Phiếu đang ở CONFIRMING -> 400 BR-GH-09
        self.assertEqual(note.status, DeliveryNote.Status.CONFIRMING)
        r_get = client.get(f"/api/delivery/notes/{note.pk}/label/")
        self.assertEqual(r_get.status_code, 400)
        self.assertEqual(r_get.json()["code"], "BR-GH-09")

        r_post = client.post(f"/api/delivery/notes/{note.pk}/label/print/", {}, format="json")
        self.assertEqual(r_post.status_code, 400)
        self.assertEqual(r_post.json()["code"], "BR-GH-09")

        # Huỷ phiếu -> 400 BR-GH-07
        note.status = DeliveryNote.Status.CANCELLED
        note.save(update_fields=["status"])
        r_cancel = client.get(f"/api/delivery/notes/{note.pk}/label/")
        self.assertEqual(r_cancel.status_code, 400)
        self.assertEqual(r_cancel.json()["code"], "BR-GH-07")

    def test_cs11_permissions_and_cache_control(self):
        """CS-11: Cần quyền delivery.print_label và có header Cache-Control: no-store."""
        _, _, note, _ = self._create_paid_order("DH-LBL-04", "0905556669")
        confirm_note_for_test(note)

        # nv_kho có print_label -> 200, có Cache-Control: no-store
        kho_client = client_for(self.kho)
        resp = kho_client.get(f"/api/delivery/notes/{note.pk}/label/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("Cache-Control"), "no-store")

        # nv_giao thiếu print_label -> 403
        giao_client = client_for(self.giao)
        self.assertEqual(giao_client.get(f"/api/delivery/notes/{note.pk}/label/").status_code, 403)
        self.assertEqual(giao_client.post(f"/api/delivery/notes/{note.pk}/label/print/").status_code, 403)

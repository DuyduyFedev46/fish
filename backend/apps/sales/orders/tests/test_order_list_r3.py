"""
ERP theo design, Lô 3 — R3 (02b §3.8) + số điện thoại đủ (02b §3.7), phần `apps/sales/orders`.

Contract:
    GET /api/sales/orders/                   mỗi dòng có `reason: {"code","label"} | null`
    GET /api/sales/orders/?customer=<id>     chỉ người có quyền xem danh bạ khách (Chủ, Quản lý) -> 403 với người khác
    GET /api/sales/orders/?batch=<pk>        đơn có dòng giữ chỗ/phân bổ từ lô đó

Tất cả dữ liệu là giả. BR liên quan: BR-BH-03 (tự huỷ quá hạn), BR-HT-05 (huỷ đơn đã thanh toán),
BR-TT-04 (thiếu tiền), BR-GH-04 (giao thất bại), BR-PQ-12/15, bất biến 9.
"""
from decimal import Decimal

from django.utils import timezone

from apps.accounts import roles
from apps.common.tests.fixtures import client_for, make_user
from apps.delivery.models import DeliveryNote
from apps.sales.models import Customer, PaymentTransaction, SalesCreditNote, SalesOrder
from apps.sales.orders import services as order_services
from apps.sales.orders.tests.test_s10_api import SENSITIVE_KEYS, OrderApiBase, find_keys

PHONE_A = "0900000123"
PHONE_B = "0900000456"


class R3Base(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.owner = make_user("t_owner", roles.OWNER)
        self.manager = make_user("t_manager", roles.MANAGER)
        self.warehouse_staff = make_user("t_warehouse", roles.WAREHOUSE_STAFF)
        self.courier = make_user("t_courier", roles.DELIVERY_STAFF)
        self.customer_service = make_user("t_customer_service", roles.CUSTOMER_SERVICE)

    def _order_for(self, phone, name):
        return self._order(phone=phone, name=name)

    def _get(self, user, query=""):
        return client_for(user).get(f"/api/sales/orders/{query}")

    def _row(self, user, order):
        rows = self._get(user).json()["results"]
        return next(r for r in rows if r["id"] == order.pk)


class OrderReasonTests(R3Base):
    def test_ed09_ac1_reason_is_null_for_normal_order(self):
        order = self._paid_order(phone=PHONE_A)
        self.assertIsNone(self._row(self.owner, order)["reason"])

    def test_ed09_ac1_auto_cancelled_shows_reservation_expired(self):
        order = self._order(phone=PHONE_A)
        SalesOrder.objects.filter(pk=order.pk).update(status=SalesOrder.Status.AUTO_CANCELLED)
        self.assertEqual(
            self._row(self.owner, order)["reason"],
            {"code": "AUTO_CANCELLED", "label": "Hết giờ giữ chỗ"},
        )

    def test_ed09_ac1_cancelled_label_comes_from_credit_note_reason_code(self):
        order = self._paid_order(phone=PHONE_A)
        order_services.cancel_paid_order(
            order=order, actor=self.owner, reason="Khách đổi ý", reason_code="CUSTOMER_CHANGED_MIND",
        )
        self.assertEqual(
            self._row(self.manager, order)["reason"],
            {"code": "CUSTOMER_CHANGED_MIND", "label": "Khách đổi ý"},
        )

    def test_ed09_ac1_cancelled_does_not_leak_free_text_note(self):
        """Ghi chú huỷ là chữ tự do (có thể chứa SĐT): chỉ nhãn theo mã, không bao giờ ghi chú."""
        order = self._paid_order(phone=PHONE_A)
        order_services.cancel_paid_order(
            order=order, actor=self.owner, reason="Khác — gọi 0900000999 báo huỷ", reason_code="OTHER",
        )
        raw = self._get(self.owner).content.decode()
        self.assertNotIn("0900000999", raw)
        self.assertEqual(self._row(self.owner, order)["reason"], {"code": "OTHER", "label": "Khác"})

    def test_ed09_ac1_unknown_reason_code_is_not_echoed(self):
        """L2: mã lạ (kể cả chữ tự do lọt vào DB) không bao giờ ra API; chỉ nhãn chung."""
        order = self._paid_order(phone=PHONE_A)
        order_services.cancel_paid_order(
            order=order, actor=self.owner, reason="x", reason_code="CUSTOMER_CHANGED_MIND",
        )
        SalesCreditNote.objects.filter(sales_invoice__sales_order=order).update(reason_code="goi 0900000999")
        raw = self._get(self.owner).content.decode()
        self.assertNotIn("0900000999", raw)
        self.assertEqual(
            self._row(self.owner, order)["reason"], {"code": "CANCELLED", "label": "Đã huỷ"},
        )

    def test_ed09_ac1_system_auto_cancel_has_own_label(self):
        order = self._paid_order(phone=PHONE_A)
        order_services.cancel_paid_order(
            order=order, actor=None, reason="auto", reason_code="UNREACHABLE_AUTO",
        )
        reason = self._row(self.owner, order)["reason"]
        self.assertEqual(reason["code"], "UNREACHABLE_AUTO")
        self.assertEqual(reason["label"], "Hệ thống tự huỷ — không liên lạc được")

    def test_ed11_ac1_open_underpaid_payment_shows_underpaid(self):
        order = self._order(phone=PHONE_A)
        PaymentTransaction.objects.create(
            bank_txn_id="FTTEST0001", sales_order=order, amount=Decimal("1000"),
            match_status=PaymentTransaction.MatchStatus.UNDERPAID,
            resolution_status=PaymentTransaction.ResolutionStatus.OPEN,
            received_at=timezone.now(),
        )
        self.assertEqual(
            self._row(self.owner, order)["reason"],
            {"code": "UNDERPAID", "label": "Chuyển thiếu tiền"},
        )

    def test_ed11_ac1_resolved_underpaid_payment_has_no_reason(self):
        order = self._order(phone=PHONE_A)
        PaymentTransaction.objects.create(
            bank_txn_id="FTTEST0002", sales_order=order, amount=Decimal("1000"),
            match_status=PaymentTransaction.MatchStatus.UNDERPAID,
            resolution_status=PaymentTransaction.ResolutionStatus.RESOLVED,
            received_at=timezone.now(),
        )
        self.assertIsNone(self._row(self.owner, order)["reason"])

    def test_ed09_ac1_failed_delivery_note_has_reason(self):
        order = self._paid_order(phone=PHONE_A)
        DeliveryNote.objects.filter(sales_invoice__sales_order=order).update(
            status=DeliveryNote.Status.FAILED,
        )
        reason = self._row(self.owner, order)["reason"]
        self.assertIsNotNone(reason)
        self.assertTrue(reason["code"])
        self.assertTrue(reason["label"])

    def test_r3_query_count_does_not_grow_with_order_count(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        client = client_for(self.owner)
        o1 = self._paid_order(phone=PHONE_A, txn="FTQ1")
        order_services.cancel_paid_order(
            order=o1, actor=self.owner, reason="x", reason_code="CUSTOMER_CHANGED_MIND",
        )
        client.get("/api/sales/orders/")  # làm nóng cache quyền của user để hai lần đo ngang nhau
        with CaptureQueriesContext(connection) as one:
            client.get("/api/sales/orders/")
        for i in range(4):
            o = self._paid_order(phone=f"090000{i:04d}", txn=f"FTQ2{i}")
            order_services.cancel_paid_order(
                order=o, actor=self.owner, reason="x", reason_code="CUSTOMER_CHANGED_MIND",
            )
        with CaptureQueriesContext(connection) as five:
            client.get("/api/sales/orders/")
        self.assertEqual(len(five.captured_queries), len(one.captured_queries))


class OrderCustomerFilterTests(R3Base):
    def setUp(self):
        super().setUp()
        self.order_a = self._order_for(PHONE_A, "Khách Thử A")
        self.order_b = self._order_for(PHONE_B, "Khách Thử B")
        self.cust_a = Customer.objects.get(phone=PHONE_A)

    def test_ed13_customer_filter_returns_only_that_customers_orders(self):
        for user in (self.owner, self.manager):
            resp = self._get(user, f"?customer={self.cust_a.pk}")
            self.assertEqual(resp.status_code, 200, resp.content)
            self.assertEqual([r["id"] for r in resp.json()["results"]], [self.order_a.pk])

    def test_ed13_customer_filter_combines_with_status(self):
        resp = self._get(self.owner, f"?customer={self.cust_a.pk}&status=PAID")
        self.assertEqual(resp.json()["count"], 0)

    def test_ed13_customer_filter_other_groups_403(self):
        for user in (self.warehouse_staff, self.courier, self.customer_service):
            resp = self._get(user, f"?customer={self.cust_a.pk}")
            self.assertEqual(resp.status_code, 403, user.username)
            self.assertNotIn(PHONE_A, resp.content.decode())

    def test_ed13_customer_filter_anonymous_401(self):
        resp = client_for(None).get(f"/api/sales/orders/?customer={self.cust_a.pk}")
        self.assertEqual(resp.status_code, 401)

    def test_ed13_customer_filter_invalid_value_400(self):
        for raw in ("abc", "1.5", "-1", "", "9223372036854775808", "99999999999999999999999", "０１２", "9" * 5000):
            resp = self._get(self.owner, f"?customer={raw}")
            if raw == "":
                self.assertEqual(resp.status_code, 200)  # tham số rỗng = không lọc (quy ước như `status`, `q`)
                continue
            self.assertEqual(resp.status_code, 400, raw)
            self.assertEqual(resp.json()["code"], "INVALID_FILTER")

    def test_ed13_customer_filter_int64_max_is_accepted(self):
        resp = self._get(self.owner, "?customer=9223372036854775807")
        self.assertEqual((resp.status_code, resp.json()["count"]), (200, 0))

    def test_ed13_customer_filter_unknown_id_returns_empty(self):
        resp = self._get(self.owner, "?customer=999999")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 0)

    def test_ed13_customer_filter_no_cost_leak(self):
        for user in (self.owner, self.manager):
            body = self._get(user, f"?customer={self.cust_a.pk}").json()
            self.assertEqual(find_keys(body, SENSITIVE_KEYS), set())


class OrderBatchFilterTests(R3Base):
    def setUp(self):
        super().setUp()
        from apps.catalog.models import Item, ItemGroup, ItemPrice
        from apps.inventory.batches import services as batch_services

        grp = ItemGroup.objects.get(name="Hải sản")
        self.item2 = Item.objects.create(code="CUA-1", name="Cua gạch", item_group=grp)
        ItemPrice.objects.create(
            price_list=self.pl, item=self.item2, rate=Decimal("300000"),
            valid_from=timezone.localdate() - __import__("datetime").timedelta(days=1),
        )
        self.batch2 = batch_services.create_batch(
            item=self.item2, supplier=self.sup, warehouse=self.wh,
            received_date=timezone.localdate(), qty=Decimal("50"), purchase_rate=Decimal("200000"),
        )
        batch_services.publish_batch(batch=self.batch2, actor=None)
        self.batch2.refresh_from_db()
        self.order_shrimp = self._order(phone=PHONE_A)
        self.order_crab = order_services.create_order(
            customer_phone=PHONE_B, customer_name="Khách Thử B", delivery_address="[Địa chỉ giao]",
            phone=PHONE_B, lines=[{"item_code": "CUA-1", "qty": Decimal("1")}],
        )

    def test_ed06_batch_filter_returns_only_orders_of_that_batch(self):
        resp = self._get(self.warehouse_staff, f"?batch={self.batch.pk}")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual([r["id"] for r in resp.json()["results"]], [self.order_shrimp.pk])
        resp = self._get(self.owner, f"?batch={self.batch2.pk}")
        self.assertEqual([r["id"] for r in resp.json()["results"]], [self.order_crab.pk])

    def test_ed06_batch_filter_multi_line_order_appears_once(self):
        order = order_services.create_order(
            customer_phone=PHONE_A, customer_name="Khách Thử A", delivery_address="[Địa chỉ giao]",
            phone=PHONE_A,
            lines=[{"item_code": "TOM-SU-1", "qty": Decimal("1")}, {"item_code": "TOM-SU-1", "qty": Decimal("2")}],
        )
        body = self._get(self.owner, f"?batch={self.batch.pk}").json()
        ids = [r["id"] for r in body["results"]]
        self.assertEqual(ids.count(order.pk), 1)
        self.assertEqual(body["count"], len(set(ids)))

    def test_ed06_batch_filter_groups_with_full_scope(self):
        for user in (self.owner, self.manager, self.warehouse_staff):
            self.assertEqual(self._get(user, f"?batch={self.batch.pk}").status_code, 200, user.username)

    def test_ed06_batch_filter_courier_sees_only_own_notes_orders(self):
        """Tầng 3 vẫn áp: nv giao không dùng lọc lô để thấy đơn người khác."""
        resp = self._get(self.courier, f"?batch={self.batch.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 0)

    def test_ed06_batch_filter_anonymous_401_and_no_permission_403(self):
        self.assertEqual(client_for(None).get(f"/api/sales/orders/?batch={self.batch.pk}").status_code, 401)
        nobody = make_user("r3_nobody")
        self.assertEqual(self._get(nobody, f"?batch={self.batch.pk}").status_code, 403)

    def test_ed06_batch_filter_invalid_value_400(self):
        for raw in ("abc", "1.5", "-3", "9223372036854775808", "99999999999999999999999", "０１２", "9" * 5000):
            resp = self._get(self.owner, f"?batch={raw}")
            self.assertEqual(resp.status_code, 400, raw)
            self.assertEqual(resp.json()["code"], "INVALID_FILTER")

    def test_ed06_batch_filter_unknown_id_returns_empty(self):
        resp = self._get(self.owner, "?batch=999999")
        self.assertEqual((resp.status_code, resp.json()["count"]), (200, 0))

    def test_ed06_batch_filter_no_cost_leak(self):
        for user in (self.warehouse_staff, self.manager, self.owner):
            raw = self._get(user, f"?batch={self.batch.pk}").json()
            self.assertEqual(find_keys(raw, SENSITIVE_KEYS), set(), user.username)


class OrderPhoneFullTests(R3Base):
    """02b §3.7: ERP trả SĐT đủ cho người trong phạm vi; người ngoài phạm vi không có số."""

    def test_s37_order_list_returns_full_phone_for_owner_manager_warehouse(self):
        order = self._order(phone=PHONE_A, name="Khách Thử A")
        for user in (self.owner, self.manager, self.warehouse_staff):
            row = self._row(user, order)
            self.assertEqual(row["customer_phone"], PHONE_A, user.username)
            self.assertEqual(row["customer_name"], "Khách Thử A")

    def test_s37_order_detail_returns_full_phone(self):
        order = self._order(phone=PHONE_A, name="Khách Thử A")
        body = client_for(self.owner).get(f"/api/sales/orders/{order.pk}/").json()
        self.assertEqual(body["customer"]["phone"], PHONE_A)

    def test_s37_courier_sees_phone_only_for_in_scope_order(self):
        order = self._paid_order(phone=PHONE_A)
        other = self._paid_order(phone=PHONE_B, txn="FT2626799990")
        note = DeliveryNote.objects.get(sales_invoice__sales_order=order)
        note.assigned_to = self.courier
        note.save(update_fields=["assigned_to"])
        resp = self._get(self.courier)
        self.assertEqual([r["id"] for r in resp.json()["results"]], [order.pk])
        self.assertEqual(resp.json()["results"][0]["customer_phone"], PHONE_A)
        self.assertNotIn(PHONE_B, resp.content.decode())
        self.assertEqual(client_for(self.courier).get(f"/api/sales/orders/{other.pk}/").status_code, 404)

    def test_s37_courier_phone_hidden_after_window_expires(self):
        """SR-PII-02: phiếu đã kết thúc quá cửa sổ -> không còn số đủ trong danh sách."""
        import datetime

        from django.utils import timezone

        order = self._paid_order(phone=PHONE_A)
        note = DeliveryNote.objects.get(sales_invoice__sales_order=order)
        DeliveryNote.objects.filter(pk=note.pk).update(
            assigned_to=self.courier, status=DeliveryNote.Status.COMPLETED,
            completed_at=timezone.now() - datetime.timedelta(days=30),
        )
        resp = self._get(self.courier)
        self.assertNotIn(PHONE_A, resp.content.decode())

    def test_s37_customer_service_out_of_scope_sees_nothing(self):
        self._order(phone=PHONE_A)
        resp = self._get(self.customer_service)
        self.assertEqual(resp.json()["count"], 0)
        self.assertNotIn(PHONE_A, resp.content.decode())

    def test_s37_order_list_is_no_store(self):
        resp = self._get(self.owner)
        self.assertEqual(resp["Cache-Control"], "no-store")

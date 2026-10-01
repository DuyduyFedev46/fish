"""
ERP theo design, Lô 3 — R3 (02b §3.8): `GET /api/sales/refunds/?month=YYYY-MM` (+ `status` có sẵn)
và SĐT đủ cho người được xem phiếu hoàn (02b §3.7). Dữ liệu giả. BR-HT-07, bất biến 9.

`month` lọc theo ngày tạo phiếu (`created_at`) tính theo giờ Việt Nam (GMT+7).
"""
import datetime
from decimal import Decimal

from apps.accounts import roles
from apps.common.tests.fixtures import client_for, make_user
from apps.sales.models import Refund
from apps.sales.orders.tests.test_s10_api import SENSITIVE_KEYS, OrderApiBase, find_keys
from apps.sales.refunds import services as refund_services

PHONE_A = "0900000123"
VN = datetime.timezone(datetime.timedelta(hours=7))


class RefundMonthFilterTests(OrderApiBase):
    def _refund(self, phone, txn, created_at):
        order = self._paid_order(phone=phone, txn=txn)
        refund, _ = refund_services.create_invoice_refund(
            invoice=order.invoice, amount=Decimal("100000"), is_partial=True,
            reason="Khách đổi ý", actor=self.manager,
        )
        Refund.objects.filter(pk=refund.pk).update(created_at=created_at)
        return refund

    def setUp(self):
        super().setUp()
        self.owner = make_user("t_owner", roles.OWNER)
        self.manager = make_user("t_manager", roles.MANAGER)
        self.warehouse_staff = make_user("t_warehouse", roles.WAREHOUSE_STAFF)
        self.courier = make_user("t_courier", roles.DELIVERY_STAFF)
        self.sep = self._refund(PHONE_A, "FTM1", datetime.datetime(2026, 9, 15, 10, 0, tzinfo=VN))
        self.oct = self._refund("0900000456", "FTM2", datetime.datetime(2026, 10, 1, 0, 30, tzinfo=VN))
        self.sep_end = self._refund("0900000789", "FTM3", datetime.datetime(2026, 9, 30, 23, 59, tzinfo=VN))

    def _ids(self, query, user=None):
        resp = client_for(user or self.owner).get(f"/api/sales/refunds/{query}")
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        rows = body["results"] if isinstance(body, dict) else body
        return {r["id"] for r in rows}

    def test_ed12_ac1_filter_by_month_in_vietnam_time(self):
        self.assertEqual(self._ids("?month=2026-09"), {self.sep.pk, self.sep_end.pk})
        # 00:30 ngày 01/10 GMT+7 (= 17:30 UTC ngày 30/09) vẫn là tháng 10 theo giờ VN
        self.assertEqual(self._ids("?month=2026-10"), {self.oct.pk})
        self.assertEqual(self._ids("?month=2026-08"), set())

    def test_ed12_ac1_december_and_february_do_not_break(self):
        self.assertEqual(self._ids("?month=2026-12"), set())
        self.assertEqual(self._ids("?month=2026-02"), set())

    def test_ed12_ac1_combines_with_status(self):
        self.assertEqual(self._ids("?month=2026-09&status=REFUNDED"), set())
        self.assertEqual(self._ids("?month=2026-09&status=PENDING"), {self.sep.pk, self.sep_end.pk})

    def test_ed12_ac1_no_month_keeps_old_behavior(self):
        self.assertEqual(self._ids(""), {self.sep.pk, self.oct.pk, self.sep_end.pk})
        self.assertEqual(self._ids("?month="), {self.sep.pk, self.oct.pk, self.sep_end.pk})

    def test_ed12_ac1_invalid_month_400(self):
        for raw in (
            "2026-13", "2026-00", "2026-9", "09-2026", "abc", "2026-09-01", "2026/09",
            "9999-12", "0001-01",  # M1: đúng dạng nhưng ngoài biên năm, trước đây 500
            "2026-+1", "2026- 1", "+026-10",  # L1: int() dễ dãi
            "２０２６-10", "2026-１0",  # L1: chữ số toàn độ rộng (Unicode)
            "1999-12", "2101-01",
        ):
            resp = client_for(self.owner).get(f"/api/sales/refunds/?month={raw}")
            self.assertEqual(resp.status_code, 400, raw)
            self.assertEqual(resp.json()["code"], "INVALID_FILTER", raw)

    def test_ed12_month_accepts_boundary_years(self):
        for raw in ("2000-01", "2100-12"):
            self.assertEqual(client_for(self.owner).get(f"/api/sales/refunds/?month={raw}").status_code, 200, raw)

    def test_ed12_permissions_by_group_and_anonymous(self):
        for user in (self.owner, self.manager):
            self.assertEqual(client_for(user).get("/api/sales/refunds/?month=2026-09").status_code, 200)
        customer_service = make_user("t_customer_service", roles.CUSTOMER_SERVICE)
        for user in (self.warehouse_staff, self.courier, customer_service):
            resp = client_for(user).get("/api/sales/refunds/?month=2026-09")
            self.assertEqual(resp.status_code, 403, user.username)
            self.assertNotIn(PHONE_A, resp.content.decode())
        self.assertEqual(client_for(None).get("/api/sales/refunds/?month=2026-09").status_code, 401)

    def test_ed12_no_cost_leak(self):
        for user in (self.owner, self.manager):
            raw = client_for(user).get("/api/sales/refunds/?month=2026-09").json()
            self.assertEqual(find_keys(raw, SENSITIVE_KEYS), set())

    def test_s37_full_phone_for_owner_manager_and_no_store(self):
        for user in (self.owner, self.manager):
            resp = client_for(user).get("/api/sales/refunds/?month=2026-09")
            phones = {r["customer_phone"] for r in resp.json()["results"]}
            self.assertIn(PHONE_A, phones)
            self.assertEqual(resp["Cache-Control"], "no-store")
        detail = client_for(self.owner).get(f"/api/sales/refunds/{self.sep.pk}/")
        self.assertEqual(detail.json()["customer_phone"], PHONE_A)
        self.assertEqual(detail["Cache-Control"], "no-store")

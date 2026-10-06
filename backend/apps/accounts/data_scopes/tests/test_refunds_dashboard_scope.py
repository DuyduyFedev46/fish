"""
C1 (review Lô 3, điều kiện cho Lô 5): phạm vi D1 cho phiếu hoàn tiền (cửa phụ có tên, SĐT khách) và bảng điều hành
(`recent_orders`, `pending_orders`, `booked_soon`, `revenue_today`). BR-PQ-33/35/37, SR-PII-02, bất biến 1 và 9. 02b §1.5.

Mặc định (Chủ, Quản lý, NV kho = `all`) không đổi gì: mốc PV-01 giữ nguyên. Khác `all` thì dòng ngoài D1 là 404 / không đếm.
"""
from apps.accounts import roles
from apps.sales.models import Refund

from .test_orders_invoices_scope import ScopeSceneBase, grant, set_scope

REFUNDS = "/api/sales/refunds/"
DASHBOARD = "/api/dashboard/summary/"


class RefundScopeTests(ScopeSceneBase):
    def refund(self, label):
        return self.scene.refunds[label]

    def ids(self, label, **params):
        response = self.get(label, REFUNDS, **params)
        self.assertEqual(response.status_code, 200)
        return {row["id"] for row in response.json()["results"]}

    def test_c1_default_all_groups_see_every_refund(self):
        everyone = {r.pk for r in self.scene.refunds.values()}
        self.assertEqual(self.ids("owner"), everyone)
        self.assertEqual(self.ids("manager"), everyone)

    def test_c1_narrowed_manager_sees_only_refunds_of_orders_in_d1(self):
        set_scope(roles.MANAGER, "orders", "assigned_deliveries")
        self.assertEqual(self.ids("manager"), set())  # Quản lý không có phiếu giao gán cho mình
        other = self.refund("refund_other_order")
        self.assertEqual(self.get("manager", f"{REFUNDS}{other.pk}/").status_code, 404)

    def test_c1_courier_with_refund_view_sees_only_own_orders_refund_and_masked_by_window(self):
        grant(roles.DELIVERY_STAFF, "sales.view_refund")
        own, other = self.refund("refund_courier_order"), self.refund("refund_other_order")
        self.assertEqual(self.ids("courier"), {own.pk})
        self.assertEqual(self.get("courier", f"{REFUNDS}{other.pk}/").status_code, 404)
        detail = self.get("courier", f"{REFUNDS}{own.pk}/").json()
        self.assertTrue(detail["customer_name"])
        self.assertIsNone(detail["customer_hidden_reason"])
        # Đơn của phiếu giao đã kết thúc quá 7 ngày: có dòng nhưng tên, SĐT bị ẩn theo cửa sổ.
        old = Refund.objects.create(
            sales_invoice=self.scene.invoices["invoice_of_order_ended_8_days"], amount=1000, status=Refund.Status.PENDING,
            created_by=self.scene.users["owner"])
        expired = self.get("courier", f"{REFUNDS}{old.pk}/").json()
        self.assertIsNone(expired["customer_name"])
        self.assertIsNone(expired["customer_phone"])
        self.assertEqual(expired["customer_hidden_reason"], "expired")

    def test_c1_refund_without_order_is_hidden_when_d1_is_narrow(self):
        from apps.sales.models import PaymentTransaction

        from django.utils import timezone

        txn = PaymentTransaction.objects.create(
            bank_txn_id="FT-C1-ORPHAN", amount=1000, match_status=PaymentTransaction.MatchStatus.UNMATCHED,
            received_at=timezone.now())
        orphan = Refund.objects.create(
            payment_transaction=txn, amount=1000, status=Refund.Status.PENDING, created_by=self.scene.users["owner"])
        self.assertIn(orphan.pk, self.ids("manager"))  # D1 = all: thấy như hôm nay
        set_scope(roles.MANAGER, "orders", "assigned_deliveries")
        self.assertNotIn(orphan.pk, self.ids("manager"))

    def test_c1_gate_and_unauthenticated(self):
        self.assertEqual(self.get("courier", REFUNDS).status_code, 403)
        from rest_framework.test import APIClient

        self.assertEqual(APIClient().get(REFUNDS).status_code, 401)

    def test_c1_refund_bodies_have_no_personal_data_when_v2_off(self):
        from apps.accounts.data_scopes.tests.test_orders_invoices_scope import revoke

        revoke(roles.MANAGER, "sales.view_order_customer_info")
        text = self.get("manager", REFUNDS).content.decode()
        self.assertNotIn("Khách Giả", text)
        self.assertNotIn("0900000", text)


class DashboardScopeTests(ScopeSceneBase):
    def summary(self, label):
        response = self.get(label, DASHBOARD)
        self.assertEqual(response.status_code, 200, label)
        return response.json()

    def test_c1_default_all_matches_today(self):
        for label in ("owner", "manager", "warehouse_staff"):
            body = self.summary(label)
            self.assertEqual(body["kpis"]["pending_orders"], 15, label)
            self.assertEqual(body["kpis"]["revenue_today"], 200000, label)
            self.assertEqual(len(body["recent_orders"]), 8, label)

    def test_c1_narrowed_group_counts_only_orders_in_d1(self):
        grant(roles.DELIVERY_STAFF, "reports.view_dashboard")
        body = self.summary("courier")
        self.assertEqual(body["kpis"]["pending_orders"], 5)  # 5 đơn PROCESSING của phiếu gán cho NV giao; đơn huỷ không tính
        self.assertEqual(body["kpis"]["revenue_today"], 100000)  # chỉ hoá đơn của đơn trong phạm vi
        own_codes = {self.scene.orders[label].code for label in (
            "order_assigned_courier", "order_failed_courier", "order_ended_3_days", "order_ended_7_days_inside",
            "order_ended_8_days", "order_cancelled_courier")}
        self.assertTrue({row["code"] for row in body["recent_orders"]} <= own_codes)
        self.assertEqual(body["kpis"]["booked_soon"], 0)

    def test_c1_narrowed_manager_loses_other_orders_from_dashboard(self):
        set_scope(roles.MANAGER, "orders", "assigned_deliveries")
        body = self.summary("manager")
        self.assertEqual(body["kpis"]["pending_orders"], 0)
        self.assertEqual(body["kpis"]["revenue_today"], 0)
        self.assertEqual(body["recent_orders"], [])

    def test_c1_revenue_subtracts_only_credit_notes_in_scope(self):
        from apps.sales.models import SalesCreditNote
        from apps.sales.models import SalesInvoice

        invoice = self.scene.invoices["invoice_of_order_assigned_other"]
        SalesCreditNote.objects.create(
            code="DC-C1", source_key="cancel:c1", sales_invoice=invoice, issued_at=invoice.issued_at, amount=40000,
            stock_restored=True)
        self.assertEqual(self.summary("manager")["kpis"]["revenue_today"], 160000)
        grant(roles.DELIVERY_STAFF, "reports.view_dashboard")
        self.assertEqual(self.summary("courier")["kpis"]["revenue_today"], 100000)  # phiếu đảo của đơn khác không trừ

    def test_c1_dashboard_has_no_customer_data_or_cost_for_courier(self):
        grant(roles.DELIVERY_STAFF, "reports.view_dashboard")
        text = self.get("courier", DASHBOARD).content.decode()
        self.assertNotIn("Khách Giả", text)
        self.assertNotIn("0900000", text)
        self.assertNotIn("unit_cost", text)
        self.assertNotIn("inventory_value", text)

    def test_c1_gate_and_unauthenticated(self):
        self.assertEqual(self.get("courier", DASHBOARD).status_code, 403)
        from rest_framework.test import APIClient

        self.assertEqual(APIClient().get(DASHBOARD).status_code, 401)

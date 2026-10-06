"""
W37 L2 (S5): hoàn tiền cho đơn đã Hoàn tất, đơn giữ Hoàn tất. BR-BH-20, BR-HT-01/02/04, BR-BC-03/06, BR-GH-05,
BR-PQ (Tầng 2). Dữ liệu giả (SĐT 0900000xxx).
"""
import datetime
import uuid

from django.utils import timezone

from apps.common.tests.fixtures import client_for
from apps.delivery.tests.test_order_completion import CompletionBase
from apps.reports.tests.financial_snapshot import financial_snapshot
from apps.sales.models import Refund, SalesCreditNote, SalesOrder

CREATE_URL = "/api/sales/refunds/create/"


class RefundCompletedOrderTests(CompletionBase):
    def _completed(self, paid_days_ago=0):
        order, note = self._processing()
        self._complete(self.courier, note)
        order.refresh_from_db()
        if paid_days_ago:
            order.invoice.issued_at = timezone.now() - datetime.timedelta(days=paid_days_ago)
            order.invoice.save(update_fields=["issued_at"])
        self.assertEqual(order.status, SalesOrder.Status.COMPLETED)
        return order

    def _create(self, user, order, amount, **extra):
        data = {"sales_invoice": order.invoice.pk, "amount": str(amount), "reason": "Khách khiếu nại chất lượng",
                "request_id": str(uuid.uuid4())}
        data.update(extra)
        return client_for(user).post(CREATE_URL, data, format="json")

    def _confirm(self, user, refund):
        return client_for(user).post(f"/api/sales/refunds/{refund.pk}/confirm/", {"bank_txn_ref": "FT2626700001"},
                                     format="json")

    def _status(self, order):
        return SalesOrder.objects.values_list("status", flat=True).get(pk=order.pk)

    def test_s5_ac1_manager_creates_pending_refund_order_stays_completed(self):
        order = self._completed()
        resp = self._create(self.manager, order, "200000", is_partial=True)
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["status"], "PENDING")
        self.assertEqual(self._status(order), "COMPLETED")

    def test_s5_ac2_confirm_keeps_completed_and_prior_period_numbers_unchanged(self):
        order = self._completed(paid_days_ago=40)  # hoá đơn ở tháng trước
        refund_id = self._create(self.manager, order, "200000", is_partial=True).json()["id"]
        before = financial_snapshot(self.owner)
        resp = self._confirm(self.owner, Refund.objects.get(pk=refund_id))
        self.assertEqual(resp.status_code, 200, resp.content)
        after = financial_snapshot(self.owner)
        self.assertEqual(self._status(order), "COMPLETED")
        refund = Refund.objects.get(pk=refund_id)
        self.assertEqual(refund.status, Refund.Status.REFUNDED)
        confirmed = timezone.localtime(refund.confirmed_at)
        current_key = f"{confirmed.year}-{confirmed.month:02d}"
        for source in ("period_service", "period_api"):
            for key, numbers in before[source].items():
                if key != current_key:
                    self.assertEqual(numbers, after[source][key], f"{source} {key} (kỳ cũ) đổi số")
            self.assertNotEqual(before[source][current_key], after[source][current_key])  # kỳ hiện tại nhận số hoàn
        self.assertEqual(before["batch_service"].keys(), after["batch_service"].keys())

    def test_s5_ac3_full_refund_keeps_completed_no_refunded_order_status(self):
        order = self._completed()
        refund_id = self._create(self.manager, order, order.invoice.amount, is_partial=False).json()["id"]
        self.assertEqual(self._confirm(self.owner, Refund.objects.get(pk=refund_id)).status_code, 200)
        self.assertEqual(self._status(order), "COMPLETED")
        self.assertNotIn("REFUNDED", {value for value, _ in SalesOrder.Status.choices})

    def test_s5_ac4_over_refund_rejected_with_br_ht_04(self):
        order = self._completed()
        first = self._create(self.manager, order, "400000", is_partial=True)
        self.assertEqual(first.status_code, 201, first.content)
        count = Refund.objects.count()
        second = self._create(self.manager, order, str(order.invoice.amount - 400000 + 1), is_partial=True)
        self.assertEqual(second.status_code, 400, second.content)
        self.assertEqual(second.json()["code"], "BR-HT-04")
        self.assertEqual(Refund.objects.count(), count)

    def test_s5_ac5_cancel_completed_order_rejected_with_br_gh_05(self):
        order = self._completed()
        for user in (self.owner, self.manager):
            resp = client_for(user).post(
                f"/api/sales/orders/{order.pk}/cancel/", {"reason_code": "CUSTOMER_CHANGED_MIND"}, format="json",
            )
            self.assertEqual(resp.status_code, 400, resp.content)
            self.assertEqual(resp.json()["code"], "BR-GH-05")
        self.assertEqual(self._status(order), "COMPLETED")
        self.assertEqual(SalesCreditNote.objects.count(), 0)

    def test_s5_ac6_courier_and_warehouse_cannot_create_refund(self):
        order = self._completed()
        for user in (self.courier, self.kho, self.nobody):  # naming: allow - thuộc tính fixture cũ của OrderApiBase
            resp = self._create(user, order, "100000", is_partial=True)
            self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(Refund.objects.count(), 0)
        self.assertEqual(self._create(None, order, "100000").status_code, 401)

    def test_s5_ac7_manager_cannot_confirm_refund(self):
        order = self._completed()
        refund_id = self._create(self.manager, order, "100000", is_partial=True).json()["id"]
        resp = self._confirm(self.manager, Refund.objects.get(pk=refund_id))
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(Refund.objects.get(pk=refund_id).status, Refund.Status.PENDING)

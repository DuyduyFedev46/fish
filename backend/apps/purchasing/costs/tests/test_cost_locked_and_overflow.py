"""
Lô bổ sung A (BE phần 2), quyết định Duy 02/10.

#14: chi phí đã phân bổ vào giá vốn lô thì PATCH/PUT `amount`, `allocations`, `allocation_method` -> 400
`COST_ALLOCATED_LOCKED`; `note`, `incurred_date`, `cost_type` vẫn sửa được.
N3: `POST costs/` làm giá vốn/kg vượt 10 chữ số nguyên -> 400 theo `allocations`, không 500, không ghi gì.
Mọi dữ liệu là giả.
"""
from decimal import Decimal

from apps.common.tests.fixtures import client_for
from apps.accounts.models import AuditLog
from apps.inventory.models import Batch
from apps.purchasing.models import PurchaseCost, PurchaseCostAllocation

from .test_cost_list import URL, CostListBase

LOCKED_MESSAGE = "Chi phí đã phân bổ vào giá vốn lô nên không sửa được số tiền. Liên hệ Chủ để xử lý."


class CostAllocatedLockedTests(CostListBase):
    def setUp(self):
        super().setUp()
        self.batch = self.make_batch("10")
        self.cost = self.make_cost(amount="100000", batches=[self.batch])
        self.url = f"{URL}{self.cost.pk}/"
        self.landed_before = Batch.objects.get(pk=self.batch.pk).landed_unit_cost

    def assert_locked(self, response):
        self.assertEqual(response.status_code, 400, response.content)
        body = response.json()
        self.assertEqual(body["code"], "COST_ALLOCATED_LOCKED")
        self.assertEqual(body["detail"], LOCKED_MESSAGE)

    def assert_unchanged(self):
        cost = PurchaseCost.objects.get(pk=self.cost.pk)
        self.assertEqual(cost.amount, Decimal("100000"))
        self.assertEqual(cost.allocation_method, "BY_QTY")
        self.assertEqual(PurchaseCostAllocation.objects.filter(purchase_cost=cost).count(), 1)
        self.assertEqual(Batch.objects.get(pk=self.batch.pk).landed_unit_cost, self.landed_before)

    def test_ac14_patch_amount_is_400_locked(self):
        self.assert_locked(client_for(self.owner).patch(self.url, {"amount": "1"}, format="json"))
        self.assert_unchanged()

    def test_ac14_patch_allocation_method_is_400_locked(self):
        self.assert_locked(client_for(self.owner).patch(self.url, {"allocation_method": "BY_VALUE"}, format="json"))
        self.assert_unchanged()

    def test_ac14_patch_allocations_is_400_locked(self):
        resp = client_for(self.owner).patch(self.url, {"allocations": []}, format="json")
        self.assert_locked(resp)
        self.assert_unchanged()

    def test_ac14_put_with_amount_is_400_locked(self):
        resp = client_for(self.owner).put(
            self.url, {"cost_type": "ICE", "amount": "5", "allocation_method": "BY_QTY",
                       "incurred_date": "2026-09-28"}, format="json")
        self.assert_locked(resp)
        self.assert_unchanged()

    def test_ac14_note_and_incurred_date_still_editable(self):
        resp = client_for(self.owner).patch(
            self.url, {"note": "Ghi chú mới", "incurred_date": "2026-09-27"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        cost = PurchaseCost.objects.get(pk=self.cost.pk)
        self.assertEqual(cost.note, "Ghi chú mới")
        self.assertEqual(cost.incurred_date.isoformat(), "2026-09-27")
        self.assert_unchanged()

    def test_ac14_other_roles_403_not_400(self):
        for user in (self.manager, self.warehouse_staff, self.courier, self.customer_service):
            resp = client_for(user).patch(self.url, {"amount": "1"}, format="json")
            self.assertEqual(resp.status_code, 403, (user.username, resp.content))
            self.assertNotIn("COST_ALLOCATED_LOCKED", resp.content.decode())
        self.assert_unchanged()

    def test_ac14_locked_response_does_not_leak_cost_figures(self):
        body = client_for(self.owner).patch(self.url, {"amount": "1"}, format="json").content.decode()
        for key in ("landed_unit_cost", "purchase_rate", "unit_cost", "100000"):
            self.assertNotIn(key, body)

    def test_ac14_locked_patch_writes_no_audit_row(self):
        count = AuditLog.objects.count()
        client_for(self.owner).patch(self.url, {"amount": "1"}, format="json")
        self.assertEqual(AuditLog.objects.count(), count)


class CostLandedOverflowTests(CostListBase):
    def post(self, amount, batch):
        return client_for(self.owner).post(URL, {
            "cost_type": "TRANSPORT", "amount": amount, "allocation_method": "BY_QTY",
            "incurred_date": "2026-09-28", "allocations": [{"batch": batch.pk}],
        }, format="json")

    def test_n3_landed_cost_over_ten_integer_digits_is_400_by_allocations(self):
        batch = self.make_batch("1")  # 1 kg: ~10^12 đ chi phí/kg > 10 chữ số nguyên của giá vốn
        before = Batch.objects.get(pk=batch.pk).landed_unit_cost
        resp = self.post("999999999999", batch)
        self.assertEqual(resp.status_code, 400, resp.content)
        body = resp.json()
        self.assertEqual(body["code"], "COST_LANDED_OVERFLOW")
        self.assertIn("allocations", body)
        self.assertTrue(body["allocations"])
        self.assertEqual(PurchaseCost.objects.count(), 0)
        self.assertEqual(PurchaseCostAllocation.objects.count(), 0)
        self.assertEqual(Batch.objects.get(pk=batch.pk).landed_unit_cost, before)

    def test_n3_amount_over_twelve_digits_is_400_by_amount(self):
        batch = self.make_batch("1")
        resp = self.post("9999999999999", batch)
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertIn("amount", resp.json())
        self.assertEqual(PurchaseCost.objects.count(), 0)

    def test_n3_missing_or_garbage_amount_is_400_by_amount(self):
        batch = self.make_batch("1")
        for bad in (None, "abc", "NaN"):
            resp = self.post(bad, batch)
            self.assertEqual(resp.status_code, 400, (bad, resp.content))
            self.assertIn("amount", resp.json())
        self.assertEqual(PurchaseCost.objects.count(), 0)

    def test_n3_normal_cost_still_201(self):
        batch = self.make_batch("10")
        resp = self.post("100000", batch)
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(PurchaseCost.objects.count(), 1)

    def test_n3_non_owner_403(self):
        batch = self.make_batch("1")
        resp = client_for(self.warehouse_staff).post(URL, {
            "cost_type": "ICE", "amount": "9999999999999", "allocation_method": "BY_QTY",
            "incurred_date": "2026-09-28", "allocations": [{"batch": batch.pk}]}, format="json")
        self.assertEqual(resp.status_code, 403)

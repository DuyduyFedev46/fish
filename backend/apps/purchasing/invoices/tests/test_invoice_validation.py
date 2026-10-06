"""
TL12-sup, TL12-paid, QA12-N3 (Lô 17a, A5): luật ghi hoá đơn mua (BR-MH-03, BR-MH-04). Dữ liệu giả.

400 `AMOUNT_NOT_POSITIVE` · `INVOICE_SUPPLIER_MISMATCH` · `PAID_AT_REQUIRED` · `PAID_AT_IN_FUTURE` · `PAID_AT_WHEN_UNPAID`.
Luật kiểm trên giá trị đã gộp (PATCH đè lên dòng cũ). PATCH không gửi `is_paid`/`paid_at` thì bỏ qua luật paid_at,
để dòng cũ `is_paid=True, paid_at=NULL` vẫn sửa được số tiền.
"""
import datetime
from decimal import Decimal

from django.utils import timezone

from apps.purchasing.models import PurchaseInvoice

from .test_invoice_list import URL, InvoiceListBase


class InvoiceValidationBase(InvoiceListBase):
    def paid_payload(self, **extra):
        payload = {
            "supplier": self.supplier.pk, "amount": "500000.00", "is_paid": True, "invoice_date": "2026-10-01",
            "paid_at": (timezone.now() - datetime.timedelta(hours=1)).isoformat(),
        }
        payload.update(extra)
        return payload

    def post(self, payload, user=None):
        return self.client_for(user or self.owner).post(URL, payload, format="json")

    def patch(self, invoice, payload, user=None):
        return self.client_for(user or self.owner).patch(f"{URL}{invoice.pk}/", payload, format="json")

    @staticmethod
    def client_for(user):
        from apps.common.tests.fixtures import client_for
        return client_for(user)

    def assert_rejected(self, response, code):
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(response.json().get("code"), code, response.json())
        self.assertNotIn("BR-", response.json()["detail"])  # câu lỗi tiếng Việt, không có mã BR


class InvoiceCreateRulesTests(InvoiceValidationBase):
    def test_a5_valid_paid_invoice_is_created(self):
        response = self.post(self.paid_payload())
        self.assertEqual(response.status_code, 201, response.content)

    def test_a5_amount_zero_or_negative_is_rejected_and_nothing_created(self):
        for amount in ("0", "0.00", "-5"):
            self.assert_rejected(self.post(self.paid_payload(amount=amount)), "AMOUNT_NOT_POSITIVE")
        self.assertEqual(PurchaseInvoice.objects.count(), 0)

    def test_a5_receipt_of_another_supplier_is_rejected_and_nothing_created(self):
        receipt = self.make_receipt(supplier=self.other_supplier)
        self.assert_rejected(self.post(self.paid_payload(receipt=receipt.pk)), "INVOICE_SUPPLIER_MISMATCH")
        self.assertEqual(PurchaseInvoice.objects.count(), 0)

    def test_a5_receipt_of_same_supplier_is_accepted(self):
        receipt = self.make_receipt(supplier=self.supplier)
        self.assertEqual(self.post(self.paid_payload(receipt=receipt.pk)).status_code, 201)

    def test_a5_paid_without_paid_at_is_rejected(self):
        payload = self.paid_payload()
        del payload["paid_at"]
        self.assert_rejected(self.post(payload), "PAID_AT_REQUIRED")
        self.assert_rejected(self.post(self.paid_payload(paid_at=None)), "PAID_AT_REQUIRED")

    def test_a5_paid_at_one_minute_in_future_is_rejected_past_is_accepted(self):
        future = (timezone.now() + datetime.timedelta(minutes=1)).isoformat()
        self.assert_rejected(self.post(self.paid_payload(paid_at=future)), "PAID_AT_IN_FUTURE")
        past = (timezone.now() - datetime.timedelta(minutes=1)).isoformat()
        self.assertEqual(self.post(self.paid_payload(paid_at=past)).status_code, 201)

    def test_a5_unpaid_with_paid_at_is_rejected_unpaid_without_is_accepted(self):
        self.assert_rejected(self.post(self.paid_payload(is_paid=False)), "PAID_AT_WHEN_UNPAID")
        payload = self.paid_payload(is_paid=False, paid_at=None)
        self.assertEqual(self.post(payload).status_code, 201)

    def test_a5_cancelled_receipt_code_unchanged(self):
        from apps.purchasing.models import PurchaseReceipt
        receipt = self.make_receipt()
        PurchaseReceipt.objects.filter(pk=receipt.pk).update(status=PurchaseReceipt.Status.CANCELLED)
        response = self.post(self.paid_payload(receipt=receipt.pk))  # câu lỗi cũ có mã BR-MH-07, giữ nguyên
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "RECEIPT_CANCELLED")


class InvoicePatchRulesTests(InvoiceValidationBase):
    def legacy_invoice(self):
        """Dòng cũ: đã trả nhưng không có `paid_at` (dữ liệu trước khi có luật)."""
        invoice = self.make_invoice()
        PurchaseInvoice.objects.filter(pk=invoice.pk).update(paid_at=None)
        invoice.refresh_from_db()
        return invoice

    def test_a5_patch_amount_only_on_legacy_paid_row_without_paid_at_is_200(self):
        invoice = self.legacy_invoice()
        response = self.patch(invoice, {"amount": "750000.00"})
        self.assertEqual(response.status_code, 200, response.content)
        invoice.refresh_from_db()
        self.assertEqual(invoice.amount, Decimal("750000.00"))
        self.assertIsNone(invoice.paid_at)

    def test_a5_patch_amount_zero_is_rejected_and_row_unchanged(self):
        invoice = self.make_invoice()
        self.assert_rejected(self.patch(invoice, {"amount": "0"}), "AMOUNT_NOT_POSITIVE")
        invoice.refresh_from_db()
        self.assertEqual(invoice.amount, Decimal("1000000.00"))

    def test_a5_patch_marking_paid_needs_paid_at(self):
        invoice = self.make_invoice(is_paid=False)
        self.assert_rejected(self.patch(invoice, {"is_paid": True}), "PAID_AT_REQUIRED")
        ok = self.patch(invoice, {"is_paid": True, "paid_at": (timezone.now() - datetime.timedelta(hours=2)).isoformat()})
        self.assertEqual(ok.status_code, 200, ok.content)

    def test_a5_patch_unpaid_on_row_that_has_paid_at_is_rejected_unless_cleared(self):
        invoice = self.make_invoice()  # đã trả, có paid_at
        self.assert_rejected(self.patch(invoice, {"is_paid": False}), "PAID_AT_WHEN_UNPAID")
        self.assertEqual(self.patch(invoice, {"is_paid": False, "paid_at": None}).status_code, 200)

    def test_a5_patch_paid_at_in_future_is_rejected(self):
        invoice = self.make_invoice()
        future = (timezone.now() + datetime.timedelta(minutes=1)).isoformat()
        self.assert_rejected(self.patch(invoice, {"paid_at": future}), "PAID_AT_IN_FUTURE")

    def test_a5_patch_to_receipt_of_other_supplier_is_rejected(self):
        invoice = self.make_invoice()
        receipt = self.make_receipt(supplier=self.other_supplier)
        self.assert_rejected(self.patch(invoice, {"receipt": receipt.pk}), "INVOICE_SUPPLIER_MISMATCH")
        self.assert_rejected(self.patch(invoice, {"supplier": self.other_supplier.pk, "receipt": self.make_receipt().pk}),
                             "INVOICE_SUPPLIER_MISMATCH")

    def test_a5_other_roles_get_403_and_row_unchanged(self):
        invoice = self.make_invoice()
        for user in (self.manager, self.warehouse_staff, self.courier):
            self.assertEqual(self.patch(invoice, {"amount": "1.00"}, user=user).status_code, 403, user.username)
            self.assertEqual(self.post(self.paid_payload(), user=user).status_code, 403, user.username)
        invoice.refresh_from_db()
        self.assertEqual(invoice.amount, Decimal("1000000.00"))

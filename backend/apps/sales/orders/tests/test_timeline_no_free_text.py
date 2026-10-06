"""
Duy quyết 03/10 #3 — dòng thời gian không chép chữ người dùng tự gõ (bất biến 9) và tiền viết "đ" (UI-RULES §1.6).

Nhãn chỉ có: lý do dạng mã chuẩn đã map sang nhãn, mã chứng từ, số kg, số tiền, người làm.
Lý do "Khác" tự gõ chỉ hiện "Lý do khác". Dữ liệu giả.
"""
from decimal import Decimal

from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.common.audit import record_audit
from apps.common.formatting import format_vnd_ui
from apps.common.tests.fixtures import client_for
from apps.inventory.batches.timeline import build_batch_timeline
from apps.sales.models import PaymentTransaction
from apps.sales.orders.tests.test_s10_api import OrderApiBase
from apps.sales.payments.timeline import build_payment_timeline
from apps.sales.refunds import services as refund_services
from apps.sales.refunds.timeline import build_refund_timeline

MARK = "GHI-CHU-TU-DO-XYZ"
FAKE_PHONE = "0900000321"
FREE = f"{MARK} gọi {FAKE_PHONE}"


class TimelineLabelsNoFreeTextTests(OrderApiBase):
    def setUp(self):
        super().setUp()
        self.owner = self.chu  # naming: allow - tên thuộc tính của OrderApiBase dùng chung
        self.manager = self.ql  # naming: allow - tên thuộc tính của OrderApiBase dùng chung

    def _cancel(self, order, code, note=""):
        return client_for(self.manager).post(
            f"/api/sales/orders/{order.pk}/cancel/", {"reason_code": code, "note": note}, format="json",
        )

    def _all_labels(self, order, refund):
        events = []
        events += client_for(self.owner).get(f"/api/sales/orders/{order.pk}/").json()["timeline"]
        events += client_for(self.owner).get(f"/api/guidance/order/{order.pk}/").json()["timeline"]
        labels = [e["label"] for e in events]
        labels += [e.label for e in build_refund_timeline(refund)]
        pay = order.payments.first()
        labels += [e.label for e in build_payment_timeline(pay)]
        labels += [e.label for e in build_batch_timeline(self.batch, viewer=self.owner)]
        return labels

    def _scenario(self, code="OTHER"):
        order = self._paid_order()
        self.assertEqual(self._cancel(order, code, MARK).status_code, 200)  # ghi chú huỷ chặn SĐT (BR-GH-19)
        refund, _ = refund_services.create_invoice_refund(
            invoice=order.invoice, amount=Decimal("100000"), is_partial=True, reason=FREE, actor=self.manager,
        )
        refund_services.mark_refund_failed(refund=refund, reason=FREE, actor=self.owner)
        pay = order.payments.first()
        record_audit(
            "resolve_payment", actor=self.owner, obj=pay, note=FREE,
            changes={"resolution": PaymentTransaction.Resolution.CONFIRMED},
        )
        record_audit("close_batch", actor=self.owner, obj=self.batch, note=FREE,
                     changes={"landed_unit_cost": {"final": "180000"}})
        return order, refund

    def test_d3_no_label_contains_free_text_or_phone(self):
        order, refund = self._scenario()
        for label in self._all_labels(order, refund):
            self.assertNotIn(MARK, label)
            self.assertNotIn(FAKE_PHONE, label)
        body = client_for(self.owner).get(f"/api/sales/orders/{order.pk}/").json()
        self.assertNotIn(MARK, str(body["timeline"]))  # chữ ghi chú huỷ chỉ ở `cancel_note`, không vào timeline

    def test_d3_no_label_contains_dong_sign(self):
        order, refund = self._scenario()
        labels = self._all_labels(order, refund)
        self.assertTrue(labels)
        for label in labels:
            self.assertNotIn("₫", label)

    def test_d3_money_written_with_d_and_space(self):
        order, refund = self._scenario()
        labels = self._all_labels(order, refund)
        self.assertTrue(any("540.000 đ" in label for label in labels), labels)
        self.assertTrue(any("100.000 đ" in label for label in labels), labels)

    def test_d3_other_reason_shows_generic_label_only(self):
        order, _ = self._scenario("OTHER")
        rows = client_for(self.owner).get(f"/api/sales/orders/{order.pk}/").json()["timeline"]
        cancelled = next(r for r in rows if r["kind"] == "cancelled")
        self.assertEqual(cancelled["label"], "Huỷ đơn, hoàn hàng về lô gốc — lý do: Lý do khác")

    def test_d3_standard_reason_code_maps_to_label_without_note(self):
        order = self._paid_order()
        self.assertEqual(self._cancel(order, "DAMAGED_WHEN_PACKING", "1321").status_code, 200)
        rows = client_for(self.owner).get(f"/api/sales/orders/{order.pk}/").json()["timeline"]
        cancelled = next(r for r in rows if r["kind"] == "cancelled")
        self.assertEqual(
            cancelled["label"], "Huỷ đơn, hoàn hàng về lô gốc — lý do: Hàng hư lúc soạn hàng",
        )

    def test_d3_refund_failed_line_has_no_reason(self):
        order, refund = self._scenario()
        rows = client_for(self.owner).get(f"/api/sales/orders/{order.pk}/").json()["timeline"]
        failed = next(r for r in rows if r["kind"] == "refund_failed")
        self.assertEqual(failed["label"], "Phiếu hoàn 100.000 đ chuyển thất bại")
        own = [e.label for e in build_refund_timeline(refund)]
        self.assertIn("Lập phiếu hoàn tiền 100.000 đ", own)
        self.assertIn("Báo thất bại", own)

    def test_d3_payment_resolution_uses_label_not_code_or_note(self):
        order, _ = self._scenario()
        labels = [e.label for e in build_payment_timeline(order.payments.first())]
        self.assertIn("Xử lý khoản tiền về (Đã xác nhận đơn)", labels)

    def test_d3_format_vnd_ui(self):
        self.assertEqual(format_vnd_ui(Decimal("280000")), "280.000 đ")
        self.assertEqual(format_vnd_ui(None), "—")

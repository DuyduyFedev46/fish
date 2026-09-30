from apps.delivery import services as delivery_services
from apps.delivery.cskh import services as cskh_services
from apps.delivery.models import DeliveryNote
from apps.delivery.tests.test_cskh_l2 import CskhL2BaseTestCase
from apps.sales.orders import services as order_services


class A1AdvanceStatusRace(CskhL2BaseTestCase):
    def test_stale_note_overwrites_cancelled(self):
        order, invoice, note, task = self._create_paid_order("DH-R1", "0900000003")
        cskh_services.record_call(task.pk, self.cs1, result="CONFIRMED")
        stale = DeliveryNote.objects.get(pk=note.pk)          # kho mở phiếu: PREPARING
        order_services.cancel_paid_order(order=order, actor=self.ql, reason="x", reason_code="CUSTOMER_CHANGED_MIND")
        note.refresh_from_db(); print("\nafter cancel:", note.status)
        delivery_services.advance_status(note=stale, to_status="READY", actor=self.kho)
        note.refresh_from_db(); print("after kho READY on stale:", note.status)
        self.assertEqual(note.status, DeliveryNote.Status.CANCELLED)

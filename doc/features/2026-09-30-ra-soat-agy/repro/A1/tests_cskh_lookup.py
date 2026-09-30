from apps.common.tests.fixtures import client_for
from apps.delivery.models import ConfirmationTask
from apps.delivery.tests.test_cskh_l2 import CskhL2BaseTestCase


class A1CskhLookupTests(CskhL2BaseTestCase):
    def test_legacy_note_resolves_to_other_order_task(self):
        # Phiếu cũ (trước P4) không có task; task pk=... trùng id phiếu cũ
        a_order, _, a_note, a_task = self._create_paid_order("DH-A", "0900000001")
        b_order, _, b_note, b_task = self._create_paid_order("DH-B", "0900000002")
        # Mô phỏng: phiếu A là phiếu cũ không có task; task của B mang pk = id phiếu A
        a_task.delete(); b_task.delete()
        ConfirmationTask.objects.create(pk=a_note.pk, note=b_note, state="PENDING")
        resp = client_for(self.ql).get(f"/api/cskh/queue/{a_note.pk}/")
        print("\nstatus", resp.status_code, "order_code", resp.json().get("order_code"), "expected DH-A")
        self.assertNotEqual(resp.json().get("order_code"), "DH-B")

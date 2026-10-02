"""
TL5-BE1: `get_object` của hàng chờ gọi xác nhận chỉ tra theo `note_id` (contract `/api/confirmation/queue/<note_id>/`).
Trước đây tra `Q(note_id=val) | Q(pk=val)` nên khi `pk` của task này trùng `note_id` của task khác,
lệnh ghi có thể rơi vào nhầm chứng từ. Dữ liệu dùng SĐT và địa chỉ giả.
"""
import uuid

from apps.accounts import roles
from apps.common.tests.fixtures import client_for, make_user
from apps.delivery.models import ConfirmationTask, DeliveryNote
from apps.delivery.tests.test_confirmation_queue_and_labels import ConfirmationL2BaseTestCase

BASE = "/api/confirmation/queue"


class ConfirmationLookupByNoteIdTests(ConfirmationL2BaseTestCase):
    def setUp(self):
        super().setUp()
        _, _, self.note_a, self.task_a = self._create_paid_order("DH-LOOK-A", "0901000001")
        _, _, self.note_b, self.task_b = self._create_paid_order("DH-LOOK-B", "0901000002")
        # Ép va chạm: pk task A == note_id của B; task B dời sang pk lớn (không trùng note nào).
        free_pk = max(self.note_a.pk, self.note_b.pk, self.task_a.pk, self.task_b.pk) + 1000
        ConfirmationTask.objects.filter(pk=self.task_b.pk).update(id=free_pk)
        ConfirmationTask.objects.filter(pk=self.task_a.pk).update(id=self.note_b.pk)
        self.task_a = ConfirmationTask.objects.get(note=self.note_a)
        self.task_b = ConfirmationTask.objects.get(note=self.note_b)
        assert self.task_a.pk == self.note_b.pk  # tiền đề của kịch bản va chạm
        self.manager = make_user("manager_lookup", roles.MANAGER)
        self.client = client_for(self.cs1)

    def _reload(self):
        self.task_a.refresh_from_db()
        self.task_b.refresh_from_db()

    def test_tl5_be1_retrieve_returns_note_b_not_task_a(self):
        res = self.client.get(f"{BASE}/{self.note_b.pk}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["note_id"], self.note_b.pk)

    def test_tl5_be1_claim_affects_only_b(self):
        res = self.client.post(f"{BASE}/{self.note_b.pk}/claim/")
        self.assertEqual(res.status_code, 200)
        self._reload()
        self.assertEqual(self.task_b.claimed_by_id, self.cs1.pk)
        self.assertIsNone(self.task_a.claimed_by_id)

    def test_tl5_be1_calls_affect_only_b(self):
        res = self.client.post(
            f"{BASE}/{self.note_b.pk}/calls/",
            {"result": "UNREACHABLE", "request_id": str(uuid.uuid4())},
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        self._reload()
        self.assertEqual(self.task_b.attempts, 1)
        self.assertEqual(self.task_a.attempts, 0)
        self.assertFalse(self.note_a.calls.exists())
        self.assertEqual(self.note_b.calls.count(), 1)

    def test_tl5_be1_recipient_change_affects_only_b(self):
        res = client_for(self.manager).post(
            f"{BASE}/{self.note_b.pk}/recipient/",
            {"recipient_name": "Người Nhận Giả"},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.note_a.refresh_from_db()
        self.note_b.refresh_from_db()
        self.assertEqual(self.note_b.recipient_name, "Người Nhận Giả")
        self.assertNotEqual(self.note_a.recipient_name, "Người Nhận Giả")

    def test_tl5_be1_decide_affects_only_b(self):
        ConfirmationTask.objects.filter(pk__in=[self.task_a.pk, self.task_b.pk]).update(
            state=ConfirmationTask.State.ESCALATED
        )
        res = client_for(self.manager).post(
            f"{BASE}/{self.note_b.pk}/decide/",
            {"decision": "DELIVER_WITHOUT_CONFIRM", "reason": "Khách quen"},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.note_a.refresh_from_db()
        self.note_b.refresh_from_db()
        self._reload()
        self.assertEqual(self.note_a.status, DeliveryNote.Status.CONFIRMING)
        self.assertEqual(self.task_a.state, ConfirmationTask.State.ESCALATED)
        self.assertNotEqual(self.note_b.status, DeliveryNote.Status.CONFIRMING)

    def test_tl5_be1_unknown_id_is_404_on_every_route(self):
        unknown = self.task_b.pk + 5000  # không là note_id cũng không là pk task nào
        self.assertFalse(DeliveryNote.objects.filter(pk=unknown).exists())
        self.assertEqual(self.client.get(f"{BASE}/{unknown}/").status_code, 404)
        self.assertEqual(self.client.post(f"{BASE}/{unknown}/claim/").status_code, 404)
        self.assertEqual(
            self.client.post(f"{BASE}/{unknown}/calls/", {"result": "UNREACHABLE"}, format="json").status_code, 404
        )
        self.assertEqual(
            client_for(self.manager).post(f"{BASE}/{unknown}/decide/", {"decision": "CANCEL"}, format="json").status_code, 404
        )

    def test_tl5_be1_pk_that_is_not_a_note_id_is_404(self):
        """pk của task B không phải note_id nào: trước đây vẫn tìm ra B, nay phải 404."""
        self.assertFalse(DeliveryNote.objects.filter(pk=self.task_b.pk).exists())
        self.assertEqual(self.client.get(f"{BASE}/{self.task_b.pk}/").status_code, 404)
        self.assertEqual(self.client.post(f"{BASE}/{self.task_b.pk}/claim/").status_code, 404)
        self._reload()
        self.assertIsNone(self.task_b.claimed_by_id)

    def test_tl5_be1_out_of_scope_note_is_404(self):
        """Phiếu đã DONE và cs1 chưa gọi: ngoài phạm vi, 404 và không ghi gì."""
        ConfirmationTask.objects.filter(pk=self.task_b.pk).update(state=ConfirmationTask.State.DONE)
        DeliveryNote.objects.filter(pk=self.note_b.pk).update(status=DeliveryNote.Status.PREPARING)
        self.assertEqual(self.client.get(f"{BASE}/{self.note_b.pk}/").status_code, 404)
        self.assertEqual(self.client.post(f"{BASE}/{self.note_b.pk}/claim/").status_code, 404)
        self._reload()
        self.assertIsNone(self.task_b.claimed_by_id)
        self.assertIsNone(self.task_a.claimed_by_id)

    def test_tl5_be1_non_numeric_id_is_404(self):
        self.assertEqual(self.client.get(f"{BASE}/abc/").status_code, 404)

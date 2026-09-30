"""
P8 Lô 7 — SR-22 / BM-05: `confirm`/`reject` dùng chung bộ lọc của `retrieve`.
Người ngoài phạm vi (không phải chủ việc, không cùng `assignee_group` của việc ESCALATED, không có
`ai.manage_ai_policy`) nhận 404 và trạng thái việc không đổi. Dữ liệu giả.
"""
import datetime

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.ai.models import AiAction
from apps.common.tests.fixtures import client_for, make_user
from apps.accounts import roles


@override_settings(AI_ENABLED=True)
class Bm05ScopeTests(TestCase):
    def setUp(self):
        self.chu = make_user("bm05_chu", roles.OWNER)
        self.ql = make_user("bm05_ql", roles.MANAGER)
        self.kho = make_user("bm05_kho", roles.WAREHOUSE_STAFF)
        self.giao = make_user("bm05_giao", roles.DELIVERY_STAFF)
        self.clients = {u.username: client_for(u) for u in (self.chu, self.ql, self.kho, self.giao)}

    def _action(self, *, owner, status=AiAction.Status.PENDING, assignee_group="", viewed=False):
        return AiAction.objects.create(
            command="purchasing.purchasereceipt.submit",
            kind=AiAction.Kind.WRITE,
            level=AiAction.Level.C,
            status=status,
            owner=owner,
            assignee_group=assignee_group,
            target_model="purchasereceipt",
            target_id="1",
            args={},
            expires_at=timezone.now() + datetime.timedelta(minutes=15),
            viewed_at=(timezone.now() - datetime.timedelta(seconds=10)) if viewed else None,
        )

    def _post(self, user, action, verb):
        return self.clients[user.username].post(f"/api/ai/actions/{action.pk}/{verb}/", {}, format="json")

    # --- reject ---------------------------------------------------------------
    def test_bm05_nv_giao_reject_viec_cua_chu_404_trang_thai_khong_doi(self):
        act = self._action(owner=self.chu)
        res = self._post(self.giao, act, "reject")
        self.assertEqual(res.status_code, 404, res.content)
        self.assertEqual(res.json()["code"], "NOT_FOUND")
        act.refresh_from_db()
        self.assertEqual(act.status, AiAction.Status.PENDING)
        self.assertIsNone(act.decided_by)

    def test_bm05_nv_kho_reject_viec_cua_nv_khac_404(self):
        act = self._action(owner=self.giao)
        res = self._post(self.kho, act, "reject")
        self.assertEqual(res.status_code, 404, res.content)
        act.refresh_from_db()
        self.assertEqual(act.status, AiAction.Status.PENDING)

    def test_bm05_chu_viec_reject_viec_cua_chinh_minh_200(self):
        act = self._action(owner=self.giao)
        res = self._post(self.giao, act, "reject")
        self.assertEqual(res.status_code, 200, res.content)
        act.refresh_from_db()
        self.assertEqual(act.status, AiAction.Status.REJECTED)
        self.assertEqual(act.decided_by, self.giao)

    def test_bm05_escalated_cung_assignee_group_vao_duoc_bo_loc_khong_404(self):
        """Việc ESCALATED cho nhóm quan_ly: quan_ly qua được bộ lọc (không 404). Nghiệp vụ hiện tại chỉ cho
        quyết định việc PENDING nên trả 409 AI_ACTION_ALREADY_DECIDED, trạng thái không đổi (không thuộc BM-05)."""
        act = self._action(owner=self.kho, status=AiAction.Status.ESCALATED, assignee_group=roles.MANAGER)
        res = self._post(self.ql, act, "reject")
        self.assertNotEqual(res.status_code, 404, res.content)
        act.refresh_from_db()
        self.assertEqual(act.status, AiAction.Status.ESCALATED)

    def test_bm05_escalated_khac_group_reject_404(self):
        act = self._action(owner=self.kho, status=AiAction.Status.ESCALATED, assignee_group=roles.MANAGER)
        res = self._post(self.giao, act, "reject")
        self.assertEqual(res.status_code, 404, res.content)
        act.refresh_from_db()
        self.assertEqual(act.status, AiAction.Status.ESCALATED)

    def test_bm05_assignee_group_chi_co_hieu_luc_khi_escalated(self):
        """PENDING có assignee_group trùng nhưng không phải ESCALATED, không phải chủ việc -> 404 (đúng như retrieve)."""
        act = self._action(owner=self.kho, status=AiAction.Status.PENDING, assignee_group=roles.DELIVERY_STAFF)
        res = self._post(self.giao, act, "reject")
        self.assertEqual(res.status_code, 404, res.content)

    def test_bm05_quyen_manage_ai_policy_reject_viec_bat_ky_200(self):
        act = self._action(owner=self.giao)
        res = self._post(self.chu, act, "reject")
        self.assertEqual(res.status_code, 200, res.content)
        act.refresh_from_db()
        self.assertEqual(act.status, AiAction.Status.REJECTED)

    def test_bm05_khach_chua_dang_nhap_401(self):
        from rest_framework.test import APIClient
        act = self._action(owner=self.chu)
        res = APIClient().post(f"/api/ai/actions/{act.pk}/reject/", {}, format="json")
        self.assertEqual(res.status_code, 401)
        act.refresh_from_db()
        self.assertEqual(act.status, AiAction.Status.PENDING)

    # --- confirm --------------------------------------------------------------
    def test_bm05_nv_giao_confirm_viec_cua_chu_404_trang_thai_khong_doi(self):
        act = self._action(owner=self.chu, viewed=True)
        res = self._post(self.giao, act, "confirm")
        self.assertEqual(res.status_code, 404, res.content)
        self.assertEqual(res.json()["code"], "NOT_FOUND")
        act.refresh_from_db()
        self.assertEqual(act.status, AiAction.Status.PENDING)
        self.assertIsNone(act.decided_by)
        self.assertIsNone(act.executed_at)

    def test_bm05_confirm_ngoai_pham_vi_khong_ro_ton_tai_giong_id_khong_co(self):
        """Việc ngoài phạm vi và việc không tồn tại trả cùng một thông điệp (không lộ sự tồn tại)."""
        act = self._action(owner=self.chu, viewed=True)
        res_out = self._post(self.giao, act, "confirm")
        res_missing = self.clients[self.giao.username].post(
            "/api/ai/actions/00000000-0000-0000-0000-000000000000/confirm/", {}, format="json"
        )
        self.assertEqual(res_out.status_code, 404)
        self.assertEqual(res_missing.status_code, 404)
        self.assertEqual(res_out.json(), res_missing.json())

    def test_bm05_confirm_van_chay_cho_chu_viec_trong_pham_vi(self):
        """Đối chứng (không xanh giả): chủ việc confirm -> không bị 404 (đi qua bộ lọc tới nghiệp vụ)."""
        act = self._action(owner=self.kho, viewed=True)
        res = self._post(self.kho, act, "confirm")
        # Chứng từ đích của fixture không tồn tại nên nghiệp vụ có thể trả 404 riêng; mã NOT_FOUND
        # của bộ lọc phạm vi việc AI thì không được xuất hiện.
        self.assertNotEqual(res.json().get("code"), "NOT_FOUND", res.content)

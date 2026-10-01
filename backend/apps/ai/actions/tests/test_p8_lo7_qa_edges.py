"""
QA P8 Lô 7 — ca ngoài đường thuận cho SR-22 (BM-05, F10). Chỉ dữ liệu giả.

BM-05: chứng minh `confirm`/`reject` và `retrieve` cùng một phạm vi (đối chiếu từng cặp user x việc), đếm số
response thành công để không xanh giả; màn hình cũ (việc đã đổi trạng thái); hai người thao tác tranh chấp A->B / B->A.
F10: hoàn tác một việc mức B ĐÃ LÀM THẬT khi AI tắt (chủ việc, quá `undo_until`, người khác, hoàn tác 2 lần,
lô đã mở bán, chủ việc bị rút quyền).
"""
import datetime

from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.ai.models import AiAction, AiConfigVersion
from apps.ai.registry.discovery import get_registry
from apps.catalog.models import Item, ItemGroup
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import PurchaseReceipt, Supplier
from apps.ai import command_groups
from apps.accounts import roles

GROUPS = (roles.OWNER, roles.MANAGER, roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF)
COST_MARKERS = ("80000", "purchase_rate", "landed_unit_cost", "unit_cost", "rate")


@override_settings(AI_ENABLED=True)
class QaBm05ScopeParityTests(TestCase):
    def setUp(self):
        self.users = {g: make_user(f"qa7_{g}", g) for g in GROUPS}
        self.users["kho2"] = make_user("qa7_kho2", roles.WAREHOUSE_STAFF)
        self.clients = {k: client_for(u) for k, u in self.users.items()}

    def _act(self, owner, status=AiAction.Status.PENDING, assignee_group=""):
        return AiAction.objects.create(
            command="purchasing.purchasereceipt.submit", kind=AiAction.Kind.WRITE, level=AiAction.Level.C,
            status=status, owner=owner, assignee_group=assignee_group, target_model="purchasereceipt",
            target_id="1", args={}, expires_at=timezone.now() + datetime.timedelta(minutes=15),
            viewed_at=timezone.now() - datetime.timedelta(seconds=10),
        )

    def test_qa_bm05_reject_confirm_cung_pham_vi_voi_retrieve_moi_cap_user_x_viec(self):
        """Với MỌI cặp (user, việc): retrieve 200 <=> reject/confirm không bị 404 phạm vi. Đếm 200 và 404 > 0."""
        n200 = n404 = 0
        kinds = {
            "own_kho": lambda: self._act(self.users[roles.WAREHOUSE_STAFF]),
            "own_giao": lambda: self._act(self.users[roles.DELIVERY_STAFF]),
            "own_chu": lambda: self._act(self.users[roles.OWNER]),
            "esc_ql": lambda: self._act(self.users[roles.WAREHOUSE_STAFF], AiAction.Status.ESCALATED, roles.MANAGER),
            "esc_giao": lambda: self._act(self.users[roles.WAREHOUSE_STAFF], AiAction.Status.ESCALATED, roles.DELIVERY_STAFF),
            "esc_chu": lambda: self._act(self.users[roles.WAREHOUSE_STAFF], AiAction.Status.ESCALATED, roles.OWNER),
        }
        for uname, cli in self.clients.items():
            for kname, mk in kinds.items():
                for verb in ("reject", "confirm"):
                    act = mk()
                    ret = cli.get(f"/api/ai/actions/{act.pk}/")
                    res = cli.post(f"/api/ai/actions/{act.pk}/{verb}/", {}, format="json")
                    in_scope = ret.status_code == 200
                    if in_scope:
                        n200 += 1
                        self.assertNotEqual(res.status_code, 404, f"{uname}/{kname}/{verb} lệch phạm vi: {res.content}")
                    else:
                        n404 += 1
                        self.assertEqual(ret.status_code, 404, f"{uname}/{kname}")
                        self.assertEqual(res.status_code, 404, f"{uname}/{kname}/{verb}: {res.content}")
                        act.refresh_from_db()
                        self.assertEqual(act.status, AiAction.Status.PENDING if act.assignee_group == "" else
                                         AiAction.Status.ESCALATED, "ngoài phạm vi nhưng trạng thái bị đổi")
                        self.assertIsNone(act.decided_by, "ngoài phạm vi nhưng có người quyết")
        self.assertGreater(n200, 20)
        self.assertGreater(n404, 20)

    def test_qa_bm05_quan_ly_khong_co_manage_ai_policy_nen_khong_quyet_viec_cua_nv_kho(self):
        act = self._act(self.users[roles.WAREHOUSE_STAFF])
        self.assertEqual(self.clients[roles.MANAGER].post(f"/api/ai/actions/{act.pk}/reject/", {}, format="json").status_code, 404)
        # chu (manage_ai_policy) thì quyết được việc của người khác
        self.assertEqual(self.clients[roles.OWNER].post(f"/api/ai/actions/{act.pk}/reject/", {}, format="json").status_code, 200)

    def test_qa_bm05_man_hinh_cu_viec_da_bi_tu_choi_roi_bam_confirm_van_o_trong_pham_vi_409(self):
        act = self._act(self.users[roles.WAREHOUSE_STAFF])
        self.assertEqual(self.clients[roles.WAREHOUSE_STAFF].post(f"/api/ai/actions/{act.pk}/reject/", {}, format="json").status_code, 200)
        res = self.clients[roles.WAREHOUSE_STAFF].post(f"/api/ai/actions/{act.pk}/confirm/", {}, format="json")
        self.assertIn(res.status_code, (409, 400, 410), res.content)
        act.refresh_from_db()
        self.assertEqual(act.status, AiAction.Status.REJECTED)
        # reject 2 lần (job/bấm đúp): không ghi AuditLog thứ hai
        res2 = self.clients[roles.WAREHOUSE_STAFF].post(f"/api/ai/actions/{act.pk}/reject/", {}, format="json")
        self.assertIn(res2.status_code, (409, 400, 410), res2.content)
        self.assertEqual(AuditLog.objects.filter(proposal_ref=str(act.pk), action__startswith="reject").count(), 1)

    def test_qa_bm05_tranh_chap_hai_nguoi_a_roi_b_va_b_roi_a_chi_mot_nguoi_thang(self):
        # A -> B : chu quyết trước, chủ việc (kho) đến sau
        a = self._act(self.users[roles.WAREHOUSE_STAFF])
        self.assertEqual(self.clients[roles.OWNER].post(f"/api/ai/actions/{a.pk}/reject/", {}, format="json").status_code, 200)
        r = self.clients[roles.WAREHOUSE_STAFF].post(f"/api/ai/actions/{a.pk}/reject/", {}, format="json")
        self.assertNotEqual(r.status_code, 200, r.content)
        a.refresh_from_db()
        self.assertEqual((a.status, a.decided_by), (AiAction.Status.REJECTED, self.users[roles.OWNER]))
        # B -> A : chủ việc trước, chu đến sau
        b = self._act(self.users[roles.WAREHOUSE_STAFF])
        self.assertEqual(self.clients[roles.WAREHOUSE_STAFF].post(f"/api/ai/actions/{b.pk}/reject/", {}, format="json").status_code, 200)
        r = self.clients[roles.OWNER].post(f"/api/ai/actions/{b.pk}/reject/", {}, format="json")
        self.assertNotEqual(r.status_code, 200, r.content)
        b.refresh_from_db()
        self.assertEqual((b.status, b.decided_by), (AiAction.Status.REJECTED, self.users[roles.WAREHOUSE_STAFF]))

    def test_qa_bm05_404_giong_het_id_khong_ton_tai_ca_reject_va_confirm(self):
        act = self._act(self.users[roles.OWNER])
        missing = "00000000-0000-0000-0000-000000000001"
        for verb in ("reject", "confirm"):
            a = self.clients[roles.DELIVERY_STAFF].post(f"/api/ai/actions/{act.pk}/{verb}/", {}, format="json")
            b = self.clients[roles.DELIVERY_STAFF].post(f"/api/ai/actions/{missing}/{verb}/", {}, format="json")
            self.assertEqual((a.status_code, a.json()), (b.status_code, b.json()))
            self.assertNotIn(str(act.pk), a.content.decode())

    def test_qa_bm05_chua_dang_nhap_401(self):
        act = self._act(self.users[roles.WAREHOUSE_STAFF])
        for verb in ("reject", "confirm", "undo"):
            self.assertEqual(client_for(None).post(f"/api/ai/actions/{act.pk}/{verb}/", {}, format="json").status_code, 401)


class _NhapLoBase(TestCase):
    """Dựng lệnh nhap_lo mức B thật để có việc DONE thật (không mock registry)."""

    def setUp(self):
        self.kho = make_user("qa7f10_kho", roles.WAREHOUSE_STAFF)
        self.kho2 = make_user("qa7f10_kho2", roles.WAREHOUSE_STAFF)
        self.giao = make_user("qa7f10_giao", roles.DELIVERY_STAFF)
        self.chu = make_user("qa7f10_chu", roles.OWNER)
        self.c = {n: client_for(getattr(self, a)) for n, a in (("kho", "kho"), ("kho2", "kho2"), ("giao", "giao"), (roles.OWNER, "chu"))}
        g = ItemGroup.objects.create(name="Cá biển")
        self.item = Item.objects.create(code="CA-QA7", name="Cá ngừ", item_group=g, shelf_life_in_days=60, is_active=True)
        self.sup = Supplier.objects.create(name="Đầu mối giả", is_active=True)
        self.wh = Warehouse.objects.create(name="Kho giả")
        AiConfigVersion.objects.create(
            user=self.kho, version=1, group_levels={command_groups.PURCHASING: {"read": "A", "write": "B"}},
            overrides={"purchasing.purchasereceipt.receive_batches": "B"},
            limits={"purchasing.purchasereceipt.receive_batches": {"kg": "150", "vnd": "30000000"}}, created_by=self.kho,
        )
        get_registry().build(force=True)

    def _make_done(self):
        payload = {"args": {
            "supplier": self.sup.id, "received_date": timezone.now().date().isoformat(), "warehouse": self.wh.id,
            "lines": [{"item_code": self.item.code, "qty": "50.000", "rate": "80000.00", "shelf_life_days": 30}],
        }}
        with override_settings(AI_ENABLED=True, AI_WRITE_LEVELS_ALLOWED="B"):
            res = self.c["kho"].post("/api/ai/commands/purchasing.purchasereceipt.receive_batches/call/", payload, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.data["outcome"], "done", res.data)
        return AiAction.objects.get(pk=res.data["action_id"])

    def _undo(self, who, act, **settings_kw):
        with override_settings(**settings_kw):
            return self.c[who].post(f"/api/ai/actions/{act.pk}/undo/", {}, format="json")


class QaF10UndoRealWhenAiOffTests(_NhapLoBase):
    def test_qa_f10_ai_tat_chu_viec_hoan_tac_viec_da_lam_that_phieu_va_lo_bi_huy(self):
        act = self._make_done()
        res = self._undo("kho", act, AI_ENABLED=False)
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["outcome"], "undone")
        act.refresh_from_db()
        self.assertEqual(act.status, AiAction.Status.UNDONE)
        self.assertEqual(PurchaseReceipt.objects.get().status, PurchaseReceipt.Status.CANCELLED)
        self.assertEqual(Batch.objects.get().status, Batch.Status.CANCELLED)
        # chứng từ KHÔNG bị xoá (bất biến 3), AuditLog có ghi
        self.assertEqual(PurchaseReceipt.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(action=f"undo_{act.command}").count(), 1)

    def test_qa_f10_ai_tat_hoan_tac_hai_lan_lan_hai_400_khong_ghi_audit_them(self):
        act = self._make_done()
        self.assertEqual(self._undo("kho", act, AI_ENABLED=False).status_code, 200)
        r2 = self._undo("kho", act, AI_ENABLED=False)
        self.assertEqual(r2.status_code, 400, r2.content)
        self.assertEqual(r2.json()["code"], "AI_CANNOT_UNDO")
        self.assertEqual(AuditLog.objects.filter(action=f"undo_{act.command}").count(), 1)

    def test_qa_f10_ai_tat_qua_undo_until_410_khong_huy_gi(self):
        act = self._make_done()
        AiAction.objects.filter(pk=act.pk).update(undo_until=timezone.now() - datetime.timedelta(seconds=1))
        res = self._undo("kho", act, AI_ENABLED=False)
        self.assertEqual(res.status_code, 410, res.content)
        self.assertEqual(res.json()["code"], "AI_UNDO_WINDOW_CLOSED")
        act.refresh_from_db()
        self.assertEqual(act.status, AiAction.Status.DONE)
        self.assertEqual(PurchaseReceipt.objects.get().status, PurchaseReceipt.Status.SUBMITTED)

    def test_qa_f10_ai_tat_undo_until_vua_het_va_vua_con_bien(self):
        act = self._make_done()
        AiAction.objects.filter(pk=act.pk).update(undo_until=timezone.now() + datetime.timedelta(seconds=30))
        self.assertEqual(self._undo("kho", act, AI_ENABLED=False).status_code, 200)

    def test_qa_f10_ai_tat_nguoi_khac_khong_hoan_tac_duoc_403_khong_doi_gi(self):
        act = self._make_done()
        for who in ("kho2", "giao"):
            res = self._undo(who, act, AI_ENABLED=False)
            self.assertEqual(res.status_code, 403, f"{who}: {res.content}")
        act.refresh_from_db()
        self.assertEqual(act.status, AiAction.Status.DONE)
        self.assertEqual(PurchaseReceipt.objects.get().status, PurchaseReceipt.Status.SUBMITTED)
        self.assertEqual(client_for(None).post(f"/api/ai/actions/{act.pk}/undo/", {}, format="json").status_code, 401)

    def test_qa_f10_ai_tat_chu_co_manage_ai_policy_hoan_tac_duoc(self):
        act = self._make_done()
        res = self._undo(roles.OWNER, act, AI_ENABLED=False)
        self.assertEqual(res.status_code, 200, res.content)

    def test_qa_f10_lo_da_mo_ban_thi_400_br_mh_07_viec_van_done_ai_tat(self):
        act = self._make_done()
        Batch.objects.update(status=Batch.Status.SELLING)
        res = self._undo("kho", act, AI_ENABLED=False)
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(res.json()["code"], "BR-MH-07")
        act.refresh_from_db()
        self.assertEqual(act.status, AiAction.Status.DONE)
        self.assertEqual(AuditLog.objects.filter(action=f"undo_{act.command}").count(), 0)

    def test_qa_f10_chu_viec_bi_rut_quyen_403_viec_van_done(self):
        """Hoàn tác giờ đi qua view của action huỷ: bị rút `change_purchasereceipt` thì không huỷ được (03b)."""
        act = self._make_done()
        from django.contrib.auth.models import Group
        self.kho.groups.clear()
        self.kho = type(self.kho).objects.get(pk=self.kho.pk)
        self.c["kho"] = client_for(self.kho)
        res = self._undo("kho", act, AI_ENABLED=False)
        self.assertIn(res.status_code, (403,), res.content)
        act.refresh_from_db()
        self.assertEqual(act.status, AiAction.Status.DONE)
        self.assertEqual(PurchaseReceipt.objects.get().status, PurchaseReceipt.Status.SUBMITTED)

    def test_qa_f10_ai_bat_van_hoan_tac_duoc_doi_chung(self):
        act = self._make_done()
        self.assertEqual(self._undo("kho", act, AI_ENABLED=True).status_code, 200)

    def test_qa_f10_audit_va_result_khong_lo_gia_von(self):
        act = self._make_done()
        res = self._undo("kho", act, AI_ENABLED=False)
        blob = res.content.decode()
        for row in AuditLog.objects.filter(proposal_ref=str(act.pk)):
            blob += f"{row.note}|{row.changes}"
        for marker in ("80000", "purchase_rate", "landed_unit_cost"):
            self.assertNotIn(marker, blob)

    def test_qa_f10_viec_da_undone_hoac_pending_khong_hoan_tac_400(self):
        act = self._make_done()
        AiAction.objects.filter(pk=act.pk).update(status=AiAction.Status.PENDING)
        res = self._undo("kho", act, AI_ENABLED=False)
        self.assertEqual(res.status_code, 400, res.content)

"""
QA P8 Lô 2 — ma trận Group x hành động cho SR-05/SR-06 và ca ngoài đường thuận. Dữ liệu chỉ là giả.
"""
import json

from django.test import override_settings

from apps.accounts.models import AuditLog
from apps.ai.models import AiAction
from apps.common.tests.fixtures import client_for, make_user
from apps.delivery.models import DeliveryNote

from .test_p8_scope import OrderScopeBase

PII = ("Khách Giả A", "0900000201", "0900000202", "Số 1 Đường Giả")


class GuidanceMatrix(OrderScopeBase):
    def test_ma_tran_guidance_5_group_x_2_don_x_khach(self):
        note = self._note(self.in_order)
        note.assigned_to = self.giao
        note.save(update_fields=["assigned_to"])
        expect = {
            # (user, in_order, out_order)
            "chu": (200, 200), "ql": (200, 200), "kho": (200, 200),
            "giao": (200, 404), "giao2": (404, 404), "cskh": (200, 404), "direct": (404, 404),
        }
        for name, (want_in, want_out) in expect.items():
            user = getattr(self, name)
            self.assertEqual(self.guidance(user, self.in_order).status_code, want_in, f"{name} in")
            self.assertEqual(self.guidance(user, self.out_order).status_code, want_out, f"{name} out")
        self.assertEqual(client_for(None).get(f"/api/guidance/order/{self.in_order.code}/").status_code, 401)
        self.assertEqual(client_for(None).get(f"/api/guidance/order/{self.out_order.code}/").status_code, 401)

    def test_404_khong_phan_biet_ton_tai_va_ngoai_pham_vi(self):
        """Chống dò mã: đơn có thật ngoài phạm vi và mã không tồn tại cho cùng status + cùng body (trừ không lặp mã)."""
        a = self.guidance(self.cskh, self.out_order)
        b = client_for(self.cskh).get("/api/guidance/order/KHONG-CO-DON-NAY/")
        self.assertEqual(a.status_code, 404)
        self.assertEqual(b.status_code, 404)
        self.assertEqual(a.json(), b.json())
        self.assertNotIn("KHONG-CO-DON-NAY", b.content.decode())

    def test_guidance_theo_id_so_cung_ton_trong_pham_vi(self):
        """Tra theo pk số (nhánh isdigit) không vòng qua phạm vi."""
        res = client_for(self.cskh).get(f"/api/guidance/order/{self.out_order.pk}/")
        self.assertEqual(res.status_code, 404)
        res = client_for(self.giao).get(f"/api/guidance/order/{self.in_order.pk}/")
        self.assertEqual(res.status_code, 404)  # chưa gán cho giao
        self.assertEqual(client_for(self.cskh).get(f"/api/guidance/order/{self.in_order.pk}/").status_code, 200)

    def test_danh_sach_don_khong_doi_giua_cac_nhom(self):
        """Danh sách đơn: chu/ql/kho thấy cả 2, cskh chỉ đơn trong phạm vi, giao chỉ đơn gán mình (SR-06-AC4)."""
        note = self._note(self.in_order)
        note.assigned_to = self.giao
        note.save(update_fields=["assigned_to"])

        def ids(u):
            r = client_for(u).get("/api/sales/orders/")
            self.assertEqual(r.status_code, 200)
            return {x["id"] for x in r.json()["results"]}

        both = {self.in_order.pk, self.out_order.pk}
        for u in (self.chu, self.ql, self.kho):
            self.assertEqual(ids(u), both)
        self.assertEqual(ids(self.cskh), {self.in_order.pk})
        self.assertEqual(ids(self.giao), {self.in_order.pk})
        self.assertEqual(ids(self.giao2), set())


class EscalateMatrix(OrderScopeBase):
    def _esc(self, user, order, step_key):
        return client_for(user).post(
            "/api/ai/actions/escalate/",
            {"doc_type": "order", "doc_id": order.code, "step_key": step_key}, format="json",
        )

    def _blocked_step(self, user, order):
        data = client_for(user).get(f"/api/guidance/order/{order.code}/").json()
        for s in data.get("next_steps", []):
            if not s.get("allowed"):
                return s["key"]
        return None

    def test_escalate_matrix_ngoai_pham_vi_404_khong_tao_gi(self):
        before_a, before_l = AiAction.objects.count(), AuditLog.objects.count()
        for user in (self.cskh, self.giao, self.giao2, self.direct):
            res = self._esc(user, self.out_order, "confirm_payment_manual")
            self.assertEqual(res.status_code, 404, f"{user.username}: {res.content[:200]}")
            self.assertNotIn(self.out_order.code, res.content.decode())
        self.assertEqual(AiAction.objects.count(), before_a)
        self.assertEqual(AuditLog.objects.count(), before_l)

    def test_escalate_chu_khong_bi_chan_boi_pham_vi_va_khong_pii(self):
        """Chủ có quyền tự làm -> BR-AI-25 (400) chứ không 404; body không PII."""
        res = self._esc(self.chu, self.out_order, "confirm_payment_manual")
        self.assertIn(res.status_code, (400, 201), res.content[:300])
        self.assertNotEqual(res.status_code, 404)
        for s in PII:
            self.assertNotIn(s, res.content.decode())

    def test_escalate_trong_pham_vi_201_hai_lan_va_khong_lo_pii(self):
        step = self._blocked_step(self.cskh, self.in_order)
        if step is None:
            self.skipTest("cskh không có bước bị chặn trên đơn trong phạm vi (fixture)")
        r1 = self._esc(self.cskh, self.in_order, step)
        self.assertEqual(r1.status_code, 201, r1.content[:300])
        r2 = self._esc(self.cskh, self.in_order, step)
        # Bấm lại: không được 500; ghi nhận hành vi (201 thêm việc hoặc 4xx chống trùng).
        self.assertLess(r2.status_code, 500, r2.content[:300])
        blob = json.dumps(list(AiAction.objects.values("args", "target_id")), ensure_ascii=False, default=str)
        blob += json.dumps(list(AuditLog.objects.values("note", "changes")), ensure_ascii=False, default=str)
        for s in PII:
            self.assertNotIn(s, blob)
        print("QA-LO2 escalate lần 2 ->", r2.status_code, "AiAction cùng bước:",
              AiAction.objects.filter(target_id=self.in_order.code, args__step_key=step).count())

    def test_escalate_loi_khac_khong_lo_exception_ra_response(self):
        """Nhánh Exception chung: provider ném lỗi lạ -> 400 thông điệp cố định, không in exception."""
        from unittest import mock
        boom = RuntimeError("SECRET-PII-Khách Giả A 0900000201")
        with mock.patch("apps.common.guidance.api.get_guidance_provider", return_value=mock.Mock(side_effect=boom)):
            with self.assertLogs("apps.ai.actions.services", level="WARNING") as cm:
                res = self._esc(self.cskh, self.in_order, "x")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["code"], "DOC_NOT_FOUND")
        self.assertNotIn("SECRET", res.content.decode())
        self.assertNotIn("SECRET", "\n".join(cm.output))
        self.assertNotIn("0900000201", "\n".join(cm.output))
        self.assertIn("RuntimeError", "\n".join(cm.output))


@override_settings(AI_ENABLED=True)
class Sr05Matrix(OrderScopeBase):
    def _call(self, user, cmd, body):
        return client_for(user).post(f"/api/ai/commands/{cmd}/call/", body, format="json")

    def test_batch_retrieve_theo_group(self):
        from apps.inventory.models import Batch
        b = Batch.objects.first()
        results, leaks = {}, {}
        for name in ("chu", "ql", "kho", "giao", "cskh", "direct"):
            r = self._call(getattr(self, name), "inventory.batch.retrieve", {"args": {}, "target_id": str(b.pk)})
            results[name] = r.status_code
            self.assertLess(r.status_code, 500, f"{name}")
            if r.status_code == 200:
                raw = r.content.decode()
                leaks[name] = [k for k in ("purchase_rate", "landed_unit_cost", "110000") if k in raw]
        self.assertEqual(results["chu"], 200)
        print("QA-LO2 batch.retrieve theo Group:", results, "rò-giá-vốn:", leaks)
        for name, found in leaks.items():
            if name != "chu":
                self.assertEqual(found, [], f"{name} thấy giá vốn qua AI batch.retrieve: {found}")
        r = client_for(None).post("/api/ai/commands/inventory.batch.retrieve/call/",
                                  {"args": {}, "target_id": str(b.pk)}, format="json")
        self.assertIn(r.status_code, (401, 403))

    def test_batch_retrieve_target_khong_ton_tai_404_khong_ai_action(self):
        before = AiAction.objects.count()
        r = self._call(self.chu, "inventory.batch.retrieve", {"args": {}, "target_id": "999999"})
        self.assertEqual(r.status_code, 404, r.content[:200])
        self.assertEqual(AiAction.objects.count(), before)

    def test_batch_retrieve_thieu_target_id_400(self):
        r = self._call(self.chu, "inventory.batch.retrieve", {"args": {}})
        self.assertEqual(r.status_code, 400, r.content[:200])
        self.assertEqual(r.json()["code"], "BR-AI-01")

    def test_batch_pnl_va_guidance_qua_ai_khong_500(self):
        from apps.inventory.models import Batch
        b = Batch.objects.first()
        for name in ("chu", "ql", "kho", "giao", "cskh"):
            for cmd, tid in (("reports.batch_pnl", str(b.pk)), ("reports.batch_pnl", b.batch_id),
                             ("common.guidance", self.in_order.code)):
                r = self._call(getattr(self, name), cmd, {"args": {}, "target_id": tid})
                self.assertLess(r.status_code, 500, f"{name} {cmd} -> {r.status_code}")

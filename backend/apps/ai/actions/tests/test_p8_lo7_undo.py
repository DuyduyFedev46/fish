"""
P8 Lô 7 — SR-22 / F10: `undo_ai_action` dispatch đúng action trong `undo="cancel_action:<act>"`,
không có đường hoàn tác -> 400 AI_CANNOT_UNDO, và cho phép hoàn tác khi AI_ENABLED=false
(hoàn tác là việc rút lại, không phải AI làm thêm). Dữ liệu giả.
"""
import datetime
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import viewsets

from apps.ai.execution.dispatch import DispatchResult
from apps.ai.models import AiAction
from apps.ai.registry.spec import CommandSpec
from apps.common.tests.fixtures import client_for, make_user


class _FakeView(viewsets.ViewSet):
    def foo(self, request, pk=None):  # pragma: no cover - chỉ để hasattr
        raise NotImplementedError


class _FakeRegistry:
    def __init__(self, spec):
        self._spec = spec

    def get(self, _cmd):
        return self._spec


def _spec(undo, view_cls=_FakeView):
    return CommandSpec(
        id="test.fake.make", title="Lệnh giả", kind="write", method="POST",
        path="/api/test/fake/make/", action="make", detail=False, view_cls=view_cls,
        required_perms=("purchasing.add_purchasereceipt",), max_level="B", undo=undo,
    )


@override_settings(AI_ENABLED=True)
class F10UndoDispatchTests(TestCase):
    def setUp(self):
        self.kho = make_user("f10_kho", "nv_kho")
        self.client = client_for(self.kho)

    def _done_b(self, target_id="77"):
        return AiAction.objects.create(
            command="test.fake.make", kind=AiAction.Kind.WRITE, level=AiAction.Level.B,
            status=AiAction.Status.DONE, owner=self.kho, target_model="fake", target_id=target_id,
            args={}, result_ref={"model": "fake", "id": int(target_id)},
            executed_at=timezone.now(), undo_until=timezone.now() + datetime.timedelta(minutes=10),
        )

    def _undo(self, act):
        return self.client.post(f"/api/ai/actions/{act.pk}/undo/", {}, format="json")

    def test_f10_cancel_action_foo_goi_dung_foo_khong_goi_cancel_receipt(self):
        act = self._done_b()
        spec = _spec("cancel_action:foo")
        with mock.patch("apps.ai.actions.services.get_registry", return_value=_FakeRegistry(spec)), \
             mock.patch("apps.ai.actions.services.dispatch_command",
                        return_value=DispatchResult({"id": 77}, 200)) as disp, \
             mock.patch("apps.purchasing.receipts.services.cancel_receipt") as cancel_receipt:
            res = self._undo(act)
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["outcome"], "undone")
        cancel_receipt.assert_not_called()
        self.assertEqual(disp.call_count, 1)
        called_spec = disp.call_args.args[0]
        self.assertEqual(called_spec.action, "foo")
        self.assertTrue(called_spec.detail)
        self.assertEqual(disp.call_args.kwargs["target_id"], "77")
        self.assertEqual(disp.call_args.kwargs["user"], self.kho)
        act.refresh_from_db()
        self.assertEqual(act.status, AiAction.Status.UNDONE)

    def test_f10_action_huy_khong_co_tren_view_400_khong_doi_trang_thai(self):
        act = self._done_b()
        spec = _spec("cancel_action:bar")  # _FakeView không có `bar`
        with mock.patch("apps.ai.actions.services.get_registry", return_value=_FakeRegistry(spec)), \
             mock.patch("apps.ai.actions.services.dispatch_command") as disp:
            res = self._undo(act)
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(res.json()["code"], "AI_CANNOT_UNDO")
        disp.assert_not_called()
        act.refresh_from_db()
        self.assertEqual(act.status, AiAction.Status.DONE)

    def test_f10_khong_co_duong_hoan_tac_400(self):
        for undo in ("", "defer"):
            with self.subTest(undo=undo):
                act = self._done_b()
                with mock.patch("apps.ai.actions.services.get_registry", return_value=_FakeRegistry(_spec(undo))), \
                     mock.patch("apps.ai.actions.services.dispatch_command") as disp:
                    res = self._undo(act)
                self.assertEqual(res.status_code, 400, res.content)
                self.assertEqual(res.json()["code"], "AI_CANNOT_UNDO")
                disp.assert_not_called()
                act.refresh_from_db()
                self.assertEqual(act.status, AiAction.Status.DONE)

    def test_f10_lenh_khong_con_trong_registry_400_khong_mac_dinh_huy_phieu(self):
        """Trước đây `"nhap_lo" in command` là đường dự phòng; nay lệnh mất khỏi registry -> 400."""
        act = self._done_b()
        act.command = "purchasing.purchasereceipt.nhap_lo"
        act.save(update_fields=["command"])
        with mock.patch("apps.ai.actions.services.get_registry", return_value=_FakeRegistry(None)), \
             mock.patch("apps.purchasing.receipts.services.cancel_receipt") as cancel_receipt:
            res = self._undo(act)
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(res.json()["code"], "AI_CANNOT_UNDO")
        cancel_receipt.assert_not_called()

    def test_f10_loi_tu_action_huy_duoc_giu_ma_va_khong_doi_trang_thai(self):
        act = self._done_b()
        spec = _spec("cancel_action:foo")
        err = DispatchResult({"detail": "Lô đã mở bán.", "code": "BR-MH-07"}, 400, is_error=True)
        with mock.patch("apps.ai.actions.services.get_registry", return_value=_FakeRegistry(spec)), \
             mock.patch("apps.ai.actions.services.dispatch_command", return_value=err):
            res = self._undo(act)
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(res.json()["code"], "BR-MH-07")
        act.refresh_from_db()
        self.assertEqual(act.status, AiAction.Status.DONE)

    def test_f10_nguoi_ngoai_khong_hoan_tac_duoc_403(self):
        act = self._done_b()
        other = client_for(make_user("f10_giao", "nv_giao"))
        with mock.patch("apps.ai.actions.services.get_registry", return_value=_FakeRegistry(_spec("cancel_action:foo"))), \
             mock.patch("apps.ai.actions.services.dispatch_command") as disp:
            res = other.post(f"/api/ai/actions/{act.pk}/undo/", {}, format="json")
        self.assertEqual(res.status_code, 403, res.content)
        disp.assert_not_called()


class F10UndoWhenAiDisabledTests(TestCase):
    """Hoàn tác khi AI_ENABLED=false (Chủ tắt AI sau khi AI đã ghi): vẫn rút lại được, không 410."""

    def setUp(self):
        self.kho = make_user("f10b_kho", "nv_kho")
        self.client = client_for(self.kho)

    def test_f10_ai_tat_huy_lich_van_duoc(self):
        act = AiAction.objects.create(
            command="inventory.batch.close", kind=AiAction.Kind.WRITE, level=AiAction.Level.B,
            status=AiAction.Status.SCHEDULED, owner=self.kho, target_model="batch", target_id="1", args={},
            execute_after=timezone.now() + datetime.timedelta(minutes=5),
            undo_until=timezone.now() + datetime.timedelta(minutes=5),
        )
        with override_settings(AI_ENABLED=False):
            res = self.client.post(f"/api/ai/actions/{act.pk}/undo/", {}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["outcome"], "cancelled")
        act.refresh_from_db()
        self.assertEqual(act.status, AiAction.Status.CANCELLED)

    def test_f10_ai_tat_viec_khong_ton_tai_404_khong_phai_410(self):
        with override_settings(AI_ENABLED=False):
            res = self.client.post(
                "/api/ai/actions/00000000-0000-0000-0000-000000000000/undo/", {}, format="json"
            )
        self.assertEqual(res.status_code, 404, res.content)
        self.assertEqual(res.json()["code"], "NOT_FOUND")

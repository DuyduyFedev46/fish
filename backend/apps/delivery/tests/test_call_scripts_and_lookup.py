"""
Lô 5 CSKH, phần BE: CS-17 (tra mã tem), CS-18 (kịch bản gọi). Hồ sơ 2026-09-28-cskh-xac-nhan-in-tem.
Dữ liệu dùng SĐT và địa chỉ giả. Không có phần nào gọi AI (X-AC5).
"""
import json

from django.test import override_settings

from apps.accounts import roles
from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import client_for, confirm_note_for_test, make_user
from apps.delivery.labels import services as label_services
from apps.delivery.models import CallScript, DeliveryNote
from apps.delivery.tests.test_confirmation_queue_and_labels import ConfirmationL2BaseTestCase

LOOKUP = "/api/delivery/notes/lookup/"
SCRIPTS = "/api/confirmation/scripts/"
QUEUE = "/api/confirmation/queue"

PII_KEYS = (
    "customer_name", "phone", "address", "recipient_name", "recipient_phone", "recipient_phone_masked",
    "phone_masked", "delivery_address", "total_amount", "rate", "amount", "unit_cost",
)


def _all_keys(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from _all_keys(v)
    elif isinstance(value, list):
        for v in value:
            yield from _all_keys(v)


class RoleAliasTestCase(ConfirmationL2BaseTestCase):
    """Đặt tên vai bằng tiếng Anh cho test mới; fixture cũ của lớp cha giữ tên tiếng Việt."""

    def setUp(self):
        super().setUp()
        self.owner, self.manager, self.warehouse, self.courier = self.chu, self.ql, self.kho, self.giao  # naming: allow - trỏ tới fixture cũ của ConfirmationL2BaseTestCase


class LookupTests(RoleAliasTestCase):
    def setUp(self):
        super().setUp()
        _, _, self.note, _ = self._create_paid_order("DH-LK-1", "0901000111")
        confirm_note_for_test(self.note, self.cs1)
        label_services.record_print(self.note, self.warehouse)
        self.code1 = f"{self.note.code}.1"

    def test_cs17_ac1_valid_label_no_warning(self):
        res = client_for(self.warehouse).get(LOOKUP, {"code": self.code1})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {
            "note_id": self.note.pk, "status": "PREPARING", "print_no": 1, "valid_print_no": 1, "warning": None,
        })

    def test_cs17_ac1_owner_and_manager_allowed(self):
        for user in (self.owner, self.manager):
            self.assertEqual(client_for(user).get(LOOKUP, {"code": self.code1}).status_code, 200)

    def test_cs17_ac2_old_label_warns_br_gh_16(self):
        label_services.record_print(self.note, self.warehouse, reason="REPRINT")
        res = client_for(self.warehouse).get(LOOKUP, {"code": self.code1})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["print_no"], 1)
        self.assertEqual(body["valid_print_no"], 2)
        self.assertEqual(body["warning"], "BR-GH-16")
        ok = client_for(self.warehouse).get(LOOKUP, {"code": f"{self.note.code}.2"}).json()
        self.assertIsNone(ok["warning"])

    def test_cs17_ac3_cancelled_note_warns_br_gh_07(self):
        DeliveryNote.objects.filter(pk=self.note.pk).update(status=DeliveryNote.Status.CANCELLED)
        res = client_for(self.warehouse).get(LOOKUP, {"code": self.code1})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["status"], "CANCELLED")
        self.assertEqual(body["warning"], "BR-GH-07")
        self.assertIsNone(body["valid_print_no"])

    def test_cs17_ac4_unknown_code_404(self):
        c = client_for(self.warehouse)
        self.assertEqual(c.get(LOOKUP, {"code": "GH-KHONG-CO-1.1"}).status_code, 404)
        self.assertEqual(c.get(LOOKUP, {"code": f"{self.note.code}.9"}).status_code, 404)

    def test_cs17_ac4_bad_format_400(self):
        c = client_for(self.warehouse)
        for bad in ("", "abc", "GH-X", "gh-hd-1.1", "GH-HD-1.", "GH-HD-1.1234", "0901000111"):
            res = c.get(LOOKUP, {"code": bad})
            self.assertEqual(res.status_code, 400, bad)
            self.assertEqual(res.json()["code"], "INVALID_INPUT")
        self.assertEqual(c.get(LOOKUP).status_code, 400)

    def test_cs17_l1_out_of_scope_note_404_and_needs_view_perm(self):
        """Người giao được cấp thêm print_label vẫn chỉ tra được phiếu của mình (Tầng 3)."""
        from django.contrib.auth.models import Permission

        extra = make_user("giao_print", roles.DELIVERY_STAFF, perms=("delivery.print_label",))
        res = client_for(extra).get(LOOKUP, {"code": self.code1})
        self.assertEqual(res.status_code, 404)
        DeliveryNote.objects.filter(pk=self.note.pk).update(assigned_to=extra)
        self.assertEqual(client_for(extra).get(LOOKUP, {"code": self.code1}).status_code, 200)
        # thiếu view_deliverynote -> 403
        extra.groups.clear()
        extra.user_permissions.add(Permission.objects.get(codename="print_label"))
        extra = type(extra).objects.get(pk=extra.pk)
        self.assertEqual(client_for(extra).get(LOOKUP, {"code": self.code1}).status_code, 403)

    def test_cs17_ac5_forbidden_roles_403_and_anonymous_401(self):
        for user in (self.cs1, self.courier):
            self.assertEqual(client_for(user).get(LOOKUP, {"code": self.code1}).status_code, 403)
        self.assertEqual(client_for(None).get(LOOKUP, {"code": self.code1}).status_code, 401)

    def test_cs17_no_personal_data_no_price(self):
        res = client_for(self.warehouse).get(LOOKUP, {"code": self.code1})
        self.assertEqual(set(res.json()), {"note_id", "status", "print_no", "valid_print_no", "warning"})
        text = res.content.decode()
        for fake in ("0901000111", "Nguyễn Huệ", "Khách DH-LK-1", "DH-LK-1"):
            self.assertNotIn(fake, text)
        # Cả lỗi cũng không lặp lại dữ liệu đã gửi lên
        bad = client_for(self.warehouse).get(LOOKUP, {"code": "0901000111"})
        self.assertNotIn("0901000111", bad.content.decode())

    def test_cs17_no_store_header(self):
        res = client_for(self.warehouse).get(LOOKUP, {"code": self.code1})
        self.assertIn("no-store", res.headers.get("Cache-Control", ""))

    def test_cs17_does_not_break_note_detail_route(self):
        res = client_for(self.warehouse).get(f"/api/delivery/notes/{self.note.pk}/")
        self.assertEqual(res.status_code, 200)

    @override_settings(AI_ENABLED=False)
    def test_x_ac5_lookup_with_ai_disabled(self):
        self.assertEqual(client_for(self.warehouse).get(LOOKUP, {"code": self.code1}).status_code, 200)


class CallScriptApiTests(RoleAliasTestCase):
    def _create(self, user, situation="FIRST_ORDER", content="Chào anh/chị, em gọi từ Cá Về xác nhận đơn.", **extra):
        return client_for(user).post(
            SCRIPTS, {"situation": situation, "content": content, **extra}, format="json"
        )

    def test_cs18_ac1_owner_creates(self):
        res = self._create(self.owner)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json(), {
            "situation": "FIRST_ORDER", "situation_label": "Khách mua lần đầu",
            "content": "Chào anh/chị, em gọi từ Cá Về xác nhận đơn.", "is_active": True,
        })
        self.assertEqual(CallScript.objects.get().updated_by, self.owner)

    def test_cs18_ac4_forbidden_write_for_other_roles(self):
        for user in (self.manager, self.cs1, self.warehouse, self.courier):
            self.assertEqual(self._create(user).status_code, 403, user.username)
        self.assertEqual(self._create(None).status_code, 401)
        self.assertEqual(CallScript.objects.count(), 0)

    def test_cs18_ac4_patch_forbidden_for_manager_and_cs(self):
        self._create(self.owner)
        for user in (self.manager, self.cs1):
            res = client_for(user).patch(f"{SCRIPTS}FIRST_ORDER/", {"is_active": False}, format="json")
            self.assertEqual(res.status_code, 403, user.username)
        self.assertTrue(CallScript.objects.get().is_active)

    def test_cs18_ac4_read_roles(self):
        self._create(self.owner)
        for user in (self.owner, self.manager, self.cs1):
            res = client_for(user).get(SCRIPTS)
            self.assertEqual(res.status_code, 200, user.username)
            self.assertEqual(len(res.json()["results"]), 1)
        for user in (self.warehouse, self.courier):
            self.assertEqual(client_for(user).get(SCRIPTS).status_code, 403, user.username)
        self.assertEqual(client_for(None).get(SCRIPTS).status_code, 401)

    def test_cs18_ac2_inactive_hidden_from_readers_visible_to_owner(self):
        self._create(self.owner)
        res = client_for(self.owner).patch(f"{SCRIPTS}FIRST_ORDER/", {"is_active": False}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()["is_active"])
        self.assertEqual(client_for(self.cs1).get(SCRIPTS).json()["results"], [])
        self.assertEqual(len(client_for(self.owner).get(SCRIPTS).json()["results"]), 1)

    def test_cs18_ac3_content_empty_or_too_long_400(self):
        for bad in ("", "   ", "x" * 2001):
            res = self._create(self.owner, content=bad)
            self.assertEqual(res.status_code, 400)
        self.assertEqual(self._create(self.owner, content="x" * 2000).status_code, 201)
        res = client_for(self.owner).patch(f"{SCRIPTS}FIRST_ORDER/", {"content": ""}, format="json")
        self.assertEqual(res.status_code, 400)
        res = client_for(self.owner).patch(f"{SCRIPTS}FIRST_ORDER/", {"content": "y" * 2001}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_cs18_l2_non_object_body_400(self):
        self.assertEqual(client_for(self.owner).post(SCRIPTS, [1], format="json").status_code, 400)
        self._create(self.owner)
        res = client_for(self.owner).patch(f"{SCRIPTS}FIRST_ORDER/", [1], format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["code"], "INVALID_INPUT")

    def test_cs18_l3_concurrent_duplicate_is_business_error(self):
        """Hai request cùng tình huống: bên thua đua (IntegrityError) nhận BusinessError, không 500."""
        from unittest import mock

        from django.db import IntegrityError

        from apps.common.exceptions import BusinessError
        from apps.delivery.confirmation import call_scripts

        with mock.patch.object(CallScript.objects, "create", side_effect=IntegrityError("dup")):
            with self.assertRaises(BusinessError):
                call_scripts.create_script(actor=self.owner, situation="GENERAL", content="Nội dung")

    def test_cs18_invalid_situation_and_duplicate_400(self):
        self.assertEqual(self._create(self.owner, situation="NOPE").status_code, 400)
        self.assertEqual(self._create(self.owner).status_code, 201)
        self.assertEqual(self._create(self.owner).status_code, 400)

    def test_cs18_patch_unknown_situation_404(self):
        res = client_for(self.owner).patch(f"{SCRIPTS}COMBO/", {"is_active": False}, format="json")
        self.assertEqual(res.status_code, 404)

    def test_cs18_no_delete(self):
        self._create(self.owner)
        res = client_for(self.owner).delete(f"{SCRIPTS}FIRST_ORDER/")
        self.assertEqual(res.status_code, 405)
        self.assertEqual(CallScript.objects.count(), 1)

    def test_cs18_script_rejects_personal_data(self):
        res = self._create(self.owner, content="Gọi số 0901000111 để hỏi")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["code"], "BR-GH-19")
        self.assertEqual(CallScript.objects.count(), 0)

    def test_cs18_audit_log_on_create_and_update(self):
        self._create(self.owner)
        client_for(self.owner).patch(f"{SCRIPTS}FIRST_ORDER/", {"is_active": False}, format="json")
        logs = AuditLog.objects.filter(model_name="delivery.CallScript").order_by("id")
        self.assertEqual([l.action for l in logs], ["create_callscript", "update_callscript"])
        self.assertEqual(logs[0].actor, self.owner)
        detail = json.dumps(logs[1].changes, ensure_ascii=False)
        self.assertNotIn("Chào anh/chị", detail)  # không chép nội dung vào nhật ký
        self.assertIn("is_active", detail)

    def test_cs18_response_has_no_personal_data(self):
        self._create(self.owner)
        keys = set(_all_keys(client_for(self.cs1).get(SCRIPTS).json()))
        for k in PII_KEYS:
            self.assertNotIn(k, keys)

    def test_cs18_permissions_seeded_per_matrix(self):
        def has(user, codename):
            return user.has_perm(f"delivery.{codename}")
        for codename in ("view_callscript", "add_callscript", "change_callscript"):
            self.assertTrue(has(self.owner, codename))
        self.assertTrue(has(self.manager, "view_callscript"))
        self.assertTrue(has(self.cs1, "view_callscript"))
        for user in (self.manager, self.cs1, self.warehouse, self.courier):
            self.assertFalse(has(user, "add_callscript"))
            self.assertFalse(has(user, "change_callscript"))
        for user in (self.warehouse, self.courier):
            self.assertFalse(has(user, "view_callscript"))
        self.assertFalse(has(self.owner, "delete_callscript"))

    @override_settings(AI_ENABLED=False)
    def test_x_ac5_scripts_with_ai_disabled(self):
        self.assertEqual(self._create(self.owner).status_code, 201)
        self.assertEqual(client_for(self.cs1).get(SCRIPTS).status_code, 200)


class CallScriptInQueueDetailTests(RoleAliasTestCase):
    def setUp(self):
        super().setUp()
        for situation, content, active in (
            ("FIRST_ORDER", "Khách mới: giới thiệu cách rã đông.", True),
            ("RETURNING", "Khách quen: hỏi lần trước ăn có ngon không.", True),
            ("COMBO", "Combo: nhắc bảo quản ngăn đá.", True),
            ("GENERAL", "Nhớ cảm ơn khách.", True),
        ):
            CallScript.objects.create(situation=situation, content=content, is_active=active, updated_by=self.owner)
        self.order, _, self.note, _ = self._create_paid_order("DH-SC-1", "0902000222")

    def _scripts(self, user=None, note=None):
        res = client_for(user or self.cs1).get(f"{QUEUE}/{(note or self.note).pk}/")
        self.assertEqual(res.status_code, 200)
        return res.json()["scripts"]

    def test_cs18_ac1_first_order_customer_sees_first_order_and_general(self):
        scripts = self._scripts()
        self.assertEqual([s["situation"] for s in scripts], ["FIRST_ORDER", "GENERAL"])
        self.assertEqual(set(scripts[0]), {"situation", "situation_label", "content"})
        self.assertEqual(scripts[0]["situation_label"], "Khách mua lần đầu")

    def test_cs18_ac2_inactive_script_not_shown(self):
        CallScript.objects.filter(situation="FIRST_ORDER").update(is_active=False)
        self.assertEqual([s["situation"] for s in self._scripts()], ["GENERAL"])

    def test_cs18_returning_customer_gets_returning_not_first(self):
        from apps.sales.models import SalesOrder
        # Đơn khác của cùng khách đã hoàn tất
        other, _, _, _ = self._create_paid_order("DH-SC-0", "0902000222")
        SalesOrder.objects.filter(pk=other.pk).update(status=SalesOrder.Status.COMPLETED)
        SalesOrder.objects.filter(pk=self.order.pk).update(status=SalesOrder.Status.PROCESSING)
        scripts = [s["situation"] for s in self._scripts()]
        self.assertEqual(scripts, ["RETURNING", "GENERAL"])

    def test_cs18_combo_line_adds_combo_script(self):
        line = self.order.lines.first()
        type(line).objects.filter(pk=line.pk).update(bundle_snapshot={"lines": [{"item": "CA-THU", "qty": "1"}]})
        scripts = [s["situation"] for s in self._scripts()]
        self.assertEqual(scripts, ["FIRST_ORDER", "COMBO", "GENERAL"])

    def test_cs18_manager_also_sees_scripts_in_detail(self):
        self.assertEqual(len(self._scripts(user=self.manager)), 2)

    def test_cs18_detail_scripts_empty_without_view_perm_is_not_leaked(self):
        # Người xem được chi tiết nhưng không có view_callscript (Chủ vẫn có) -> không có khoá ngoài quyền
        from django.contrib.auth.models import Group, Permission

        Group.objects.get(name=roles.CUSTOMER_SERVICE).permissions.remove(
            Permission.objects.get(codename="view_callscript")
        )
        user = type(self.cs1).objects.get(pk=self.cs1.pk)
        res = client_for(user).get(f"{QUEUE}/{self.note.pk}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["scripts"], [])

    def test_cs18_detail_scripts_have_no_extra_personal_data(self):
        body = client_for(self.cs1).get(f"{QUEUE}/{self.note.pk}/").json()
        scripts_text = json.dumps(body["scripts"], ensure_ascii=False)
        for fake in ("0902000222", "Nguyễn Huệ", "Khách DH-SC-1"):
            self.assertNotIn(fake, scripts_text)

    @override_settings(AI_ENABLED=False)
    def test_x_ac5_detail_with_ai_disabled(self):
        self.assertEqual(len(self._scripts()), 2)

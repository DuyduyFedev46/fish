"""
Duy quyết 03/10 #8: xoá (ẩn) phiếu hàng hoàn về kho từ màn chi tiết — `POST /api/inventory/returns/{id}/delete/`.

Luật "không xoá chứng từ" (BR-PQ-10, bất biến 3) giữ nguyên: đây là XOÁ MỀM (`deleted_at`, `deleted_by`), dòng vẫn nằm
trong DB và AuditLog vẫn giữ. Chỉ Chủ hoặc superuser; chỉ phiếu Chờ duyệt hoặc Đã huỷ. Phiếu đã xoá biến khỏi danh sách,
chi tiết (404), số đã hoàn, dòng thời gian đơn, guidance, báo cáo. Dữ liệu giả.
"""
from django.contrib.auth.models import User

from apps.accounts import roles
from apps.accounts.models import AuditLog
from apps.common.tests.fixtures import client_for
from apps.inventory.models import ReturnToStock, StockLedgerEntry
from apps.inventory.returns.creation import returned_qty_by_batch

from .base import NOTE_WITH_PHONE, PHONE_SENTINEL, URL, ReturnsApiBase

DELETE_CODE = "RETURN_DELETE_NOT_ALLOWED"


class SoftDeleteReturnTests(ReturnsApiBase):
    def setUp(self):
        super().setUp()
        self.rt = self.make_return(self.note, "4", self.courier, NOTE_WITH_PHONE)
        self.url = f"{URL}{self.rt.pk}/delete/"

    def delete(self, user, url=None):
        return client_for(user).post(url or self.url, {}, format="json")

    def cancel_it(self):
        resp = client_for(self.manager).post(f"{URL}{self.rt.pk}/cancel/", {}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)

    # --- hành vi ---
    def test_d8_owner_deletes_cancelled_return(self):
        self.cancel_it()
        resp = self.delete(self.owner)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["status"], "deleted")
        row = ReturnToStock.all_objects.get(pk=self.rt.pk)  # xoá mềm: dòng vẫn còn
        self.assertIsNotNone(row.deleted_at)
        self.assertEqual(row.deleted_by, self.owner)

    def test_d8_owner_deletes_pending_return(self):
        self.assertEqual(self.delete(self.owner).status_code, 200)
        self.assertTrue(ReturnToStock.all_objects.get(pk=self.rt.pk).deleted_at)

    def test_d8_superuser_can_delete(self):
        root = User.objects.create_superuser("u_root", password="x")
        self.assertEqual(self.delete(root).status_code, 200)

    def test_d8_approved_return_is_400_with_code_and_vietnamese_message(self):
        client_for(self.manager).post(f"{URL}{self.rt.pk}/approve/", {"decision": "RESTOCK"}, format="json")
        resp = self.delete(self.owner)
        self.assertEqual(resp.status_code, 400, resp.content)
        body = resp.json()
        self.assertEqual(body["code"], DELETE_CODE)
        self.assertEqual(body["detail"], "Phiếu hàng hoàn đã duyệt (đã nhập lại kho hoặc ghi lỗ) không xoá được (BR-PQ-10).")
        self.assertIsNone(ReturnToStock.all_objects.get(pk=self.rt.pk).deleted_at)

    # --- phân quyền ---
    def test_d8_others_get_403_and_data_unchanged(self):
        self.cancel_it()
        for user in (self.manager, self.warehouse_staff, self.courier, self.customer_service, self.no_group):
            resp = self.delete(user)
            self.assertEqual(resp.status_code, 403, f"{user.username}: {resp.content}")
        self.assertEqual(self.delete(None).status_code, 401)
        self.assertIsNone(ReturnToStock.all_objects.get(pk=self.rt.pk).deleted_at)
        self.assertFalse(AuditLog.objects.filter(action="delete_returntostock").exists())

    def test_d8_other_courier_gets_403_not_404(self):
        # Kiểm quyền Chủ trước phạm vi dòng: không lộ phiếu có tồn tại hay không.
        self.assertEqual(self.delete(self.other_courier).status_code, 403)

    # --- sau khi xoá ---
    def test_d8_after_delete_detail_404_list_hidden_and_returned_qty_freed(self):
        self.assertEqual(returned_qty_by_batch(self.note), {self.batch.pk: self.rt.qty})
        self.assertEqual(self.delete(self.owner).status_code, 200)
        self.assertEqual(client_for(self.owner).get(f"{URL}{self.rt.pk}/").status_code, 404)
        listed = client_for(self.owner).get(URL).json()["results"]
        self.assertNotIn(self.rt.pk, [r["id"] for r in listed])
        self.assertEqual(returned_qty_by_batch(self.note), {})
        self.assertEqual(self.note.returns.count(), 0)
        self.assertEqual(client_for(self.owner).get(f"/api/guidance/return/{self.rt.pk}/").status_code, 404)

    def test_d8_deleted_return_disappears_from_order_timeline(self):
        def kinds():
            body = client_for(self.owner).get(f"/api/sales/orders/{self.order.pk}/").json()
            return [r["kind"] for r in body["timeline"]]

        from apps.delivery import services as delivery_services
        from apps.delivery.models import DeliveryNote

        delivery_services.mark_failed(note=self.note, actor=self.courier)
        rt = delivery_services.return_to_warehouse(
            note=self.note, batch=self.batch, qty=self.rt.qty, actor=self.courier,
        )
        self.assertIn("return_to_warehouse", kinds())
        self.assertEqual(DeliveryNote.objects.get(pk=self.note.pk).returns.count(), 2)
        self.assertEqual(self.delete(self.owner, f"{URL}{rt.pk}/delete/").status_code, 200)
        self.assertNotIn("return_to_warehouse", kinds())

    def test_d8_delete_writes_audit_without_personal_data_and_audit_survives(self):
        self.assertEqual(self.delete(self.owner).status_code, 200)
        audit = AuditLog.objects.get(action="delete_returntostock", object_id=str(self.rt.pk))
        self.assertEqual(audit.actor, self.owner)
        self.assertNotIn(PHONE_SENTINEL, f"{audit.changes} {audit.note} {audit.object_repr}")
        self.assertNotIn("Nguyễn Thử", f"{audit.changes} {audit.note} {audit.object_repr}")

    def test_d8_second_delete_is_404(self):
        self.assertEqual(self.delete(self.owner).status_code, 200)
        self.assertEqual(self.delete(self.owner).status_code, 404)

    def test_d8_delete_does_not_touch_stock(self):
        self.cancel_it()
        self.batch.refresh_from_db()
        before = self.batch.qty_available
        entries = StockLedgerEntry.objects.count()
        self.delete(self.owner)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_available, before)
        self.assertEqual(StockLedgerEntry.objects.count(), entries)

    def test_d8_http_delete_verb_still_not_allowed(self):
        self.assertEqual(client_for(self.owner).delete(f"{URL}{self.rt.pk}/").status_code, 405)

    # --- available_actions ---
    def test_d8_available_actions_has_delete_only_for_owner_on_valid_status(self):
        def actions(user):
            return client_for(user).get(f"{URL}{self.rt.pk}/").json()["available_actions"]

        self.assertIn("delete", actions(self.owner))  # Chờ duyệt
        self.assertNotIn("delete", actions(self.manager))
        self.assertNotIn("delete", actions(self.courier))
        self.cancel_it()
        self.assertIn("delete", actions(self.owner))  # Đã huỷ
        self.assertNotIn("delete", actions(self.manager))
        approved = self.make_return(self.note, "1", self.courier)
        client_for(self.manager).post(f"{URL}{approved.pk}/approve/", {"decision": "RESTOCK"}, format="json")
        got = client_for(self.owner).get(f"{URL}{approved.pk}/").json()["available_actions"]
        self.assertNotIn("delete", got)
        self.assertNotIn("approve", got)

    def test_d8_list_rows_carry_available_actions(self):
        row = client_for(self.owner).get(URL).json()["results"][0]
        self.assertIn("delete", row["available_actions"])

    def test_tl8f_l3_owner_without_add_returntostock_has_no_delete_action_and_post_is_403(self):
        """TL8F-L3: Chủ bị tắt "Ghi hàng hoàn" thì `available_actions` không còn `delete` và POST `delete/` là 403."""
        from django.contrib.auth.models import Group, Permission

        perm = Permission.objects.get(content_type__app_label="inventory", codename="add_returntostock")
        Group.objects.get(name=roles.OWNER).permissions.remove(perm)
        owner = User.objects.get(pk=self.owner.pk)  # bỏ cache quyền
        detail = client_for(owner).get(f"{URL}{self.rt.pk}/").json()
        self.assertNotIn("delete", detail["available_actions"])
        row = [r for r in client_for(owner).get(URL).json()["results"] if r["id"] == self.rt.pk][0]
        self.assertNotIn("delete", row["available_actions"])
        self.assertEqual(self.delete(owner).status_code, 403)
        self.assertIsNone(ReturnToStock.all_objects.get(pk=self.rt.pk).deleted_at)


class SoftDeleteReviewTests(ReturnsApiBase):
    """Review TL-D8-M1, L1, L2 (BR-PQ-10, BR-LO-04). Dữ liệu giả."""

    def setUp(self):
        super().setUp()
        self.rt = self.make_return(self.note, "4", self.courier, NOTE_WITH_PHONE)
        self.url = f"{URL}{self.rt.pk}/delete/"

    def delete(self):
        return client_for(self.owner).post(self.url, {}, format="json")

    # M1: câu lỗi không dẫn vào ngõ cụt
    def test_d8_m1_approved_message_has_no_dead_end(self):
        client_for(self.manager).post(f"{URL}{self.rt.pk}/approve/", {"decision": "WRITE_OFF"}, format="json")
        resp = self.delete()
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json()["detail"],
            "Phiếu hàng hoàn đã duyệt (đã nhập lại kho hoặc ghi lỗ) không xoá được (BR-PQ-10).",
        )

    # L1: race, request đến sau thấy phiếu đã bị xoá
    def test_d8_l1_service_on_already_deleted_return_is_409_not_500(self):
        from apps.common.exceptions import ConflictError
        from apps.inventory.returns import services
        stale = ReturnToStock.objects.get(pk=self.rt.pk)
        self.assertEqual(self.delete().status_code, 200)
        with self.assertRaises(ConflictError) as ctx:
            services.delete_return(return_to_stock=stale, actor=self.owner)
        self.assertEqual(ctx.exception.code, "STALE_STATE")

    def _stale_post(self, action_name, user, payload=None):
        """Giả lập race: get_object trả bản cũ trong khi phiếu đã bị xoá mềm."""
        from unittest import mock
        from apps.inventory.returns.api import ReturnToStockViewSet
        stale = ReturnToStock.objects.get(pk=self.rt.pk)
        self.assertEqual(self.delete().status_code, 200)
        with mock.patch.object(ReturnToStockViewSet, "get_object", return_value=stale):
            return client_for(user).post(f"{URL}{self.rt.pk}/{action_name}/", payload or {}, format="json")

    def _assert_stale_409(self, name, payload):
        resp = self._stale_post(name, self.owner, payload)
        self.assertEqual(resp.status_code, 409, resp.content)
        self.assertEqual(resp.json()["code"], "STALE_STATE")

    def test_d8_l1_stale_approve_is_409(self):
        self._assert_stale_409("approve", {"decision": "RESTOCK"})

    def test_d8_l1_stale_cancel_is_409(self):
        self._assert_stale_409("cancel", {})

    def test_d8_l1_stale_delete_is_409(self):
        self._assert_stale_409("delete", {})

    # L2: hành vi sau xoá
    def test_d8_l2_approve_cancel_patch_after_delete_are_404(self):
        self.assertEqual(self.delete().status_code, 200)
        c = client_for(self.owner)
        self.assertEqual(c.post(f"{URL}{self.rt.pk}/approve/", {"decision": "RESTOCK"}, format="json").status_code, 404)
        self.assertEqual(c.post(f"{URL}{self.rt.pk}/cancel/", {}, format="json").status_code, 404)
        self.assertEqual(c.patch(f"{URL}{self.rt.pk}/", {"note": "x"}, format="json").status_code, 404)

    def test_d8_l2_delete_draft_lifts_close_batch_blocks(self):
        from apps.ai.execution.safety import check_ai_close_batch_conditions
        from apps.inventory.batches.services import check_close_batch
        marker = "phiếu hàng hoàn đang chờ duyệt"
        self.batch.refresh_from_db()
        self.assertTrue(any(marker in m.text for m in check_close_batch(self.batch)))
        ok, info = check_ai_close_batch_conditions(self.batch)
        self.assertFalse(ok)
        self.assertEqual(self.delete().status_code, 200)
        self.batch.refresh_from_db()
        self.assertFalse(any(marker in m.text for m in check_close_batch(self.batch)))
        ok, info = check_ai_close_batch_conditions(self.batch)
        self.assertNotIn(marker, (info or {}).get("text", ""))

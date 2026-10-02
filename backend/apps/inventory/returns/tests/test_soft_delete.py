"""
Duy quyết 03/10 #8: xoá (ẩn) phiếu hàng hoàn về kho từ màn chi tiết — `POST /api/inventory/returns/{id}/delete/`.

Luật "không xoá chứng từ" (BR-PQ-10, bất biến 3) giữ nguyên: đây là XOÁ MỀM (`deleted_at`, `deleted_by`), dòng vẫn nằm
trong DB và AuditLog vẫn giữ. Chỉ Chủ hoặc superuser; chỉ phiếu Chờ duyệt hoặc Đã huỷ. Phiếu đã xoá biến khỏi danh sách,
chi tiết (404), số đã hoàn, dòng thời gian đơn, guidance, báo cáo. Dữ liệu giả.
"""
from django.contrib.auth.models import User

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
        self.assertEqual(body["detail"], "Phiếu đã cộng vào tồn kho. Huỷ phiếu trước rồi mới xoá được.")
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

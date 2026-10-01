"""
Lô 2 (R2, 02b §3.8): provider guidance "chỉ dòng thời gian" cho receipt, stocktake, return, delivery,
item, supplier, customer, staff qua GET /api/guidance/<loại>/<id>/.

Quyền đọc = quyền xem chính đối tượng đó (T1 view_<model> + T3 scope). Dòng thời gian không chứa
tên/SĐT/địa chỉ/ghi chú tự do của khách, không `changes` thô, không `object_repr` (bất biến 1, 9).
Toàn bộ dữ liệu là giả.
"""
import datetime
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts import roles
from apps.catalog.models import Item, ItemGroup
from apps.common.audit import record_audit
from apps.common.tests.fixtures import (
    client_for,
    make_batch,
    make_master,
    make_order_with_note,
    make_user,
)
from apps.inventory.models import ReturnToStock, StockReconciliation
from apps.purchasing.models import PurchaseReceipt
from apps.sales.models import Customer

FAKE_NAME = "Khách Thử A"
FAKE_PHONE = "0900000123"
FAKE_ADDRESS = "[Địa chỉ giao] Hẻm 9 Cảng Thử"
FAKE_FREE_TEXT = "Khách dặn gọi cổng sau Thử"


def _assert_no_personal_data(testcase, response):
    body = response.content.decode()
    for secret in (FAKE_NAME, FAKE_PHONE, FAKE_ADDRESS, FAKE_FREE_TEXT, "Khách DH"):
        testcase.assertNotIn(secret, body)


class AuditTimelineBase(TestCase):
    def setUp(self):
        self.owner = make_user("tl_owner", roles.OWNER)
        self.manager = make_user("tl_manager", roles.MANAGER)
        self.warehouse = make_user("tl_kho", roles.WAREHOUSE_STAFF)
        self.courier = make_user("tl_giao", roles.DELIVERY_STAFF)
        self.clients = {
            "owner": client_for(self.owner),
            "manager": client_for(self.manager),
            "warehouse": client_for(self.warehouse),
            "courier": client_for(self.courier),
            "anonymous": client_for(None),
        }
        self.item, self.supplier, self.warehouse_obj = make_master()

    def get(self, who, doc_type, doc_id):
        return self.clients[who].get(f"/api/guidance/{doc_type}/{doc_id}/")

    def assert_timeline_shape(self, res):
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()
        self.assertEqual(data["next_steps"], [])
        self.assertEqual(data["warnings"], [])
        self.assertIn("timeline", data)
        self.assertIn("doc", data)
        for event in data["timeline"]:
            self.assertEqual(set(event), {"at", "kind", "label", "doc", "actor"})
        return data


class ReceiptTimelineTests(AuditTimelineBase):
    def setUp(self):
        super().setUp()
        self.receipt = PurchaseReceipt.objects.create(
            supplier=self.supplier, warehouse=self.warehouse_obj,
            received_date=timezone.localdate(), created_by=self.warehouse,
        )
        record_audit(
            "cancel_purchase_receipt", actor=self.warehouse, obj=self.receipt,
            note=f"Nhà cung cấp {FAKE_NAME}, 1 lô", changes={"phone": FAKE_PHONE},
        )

    def test_r2_receipt_happy_path_actor_is_staff(self):
        data = self.assert_timeline_shape(self.get("manager", "receipt", self.receipt.pk))
        self.assertEqual(data["doc"]["type"], "receipt")
        self.assertEqual(data["doc"]["code"], f"PR-{self.receipt.pk}")
        self.assertEqual(data["doc"]["status"], "DRAFT")
        self.assertGreaterEqual(len(data["timeline"]), 2)
        self.assertTrue(all(e["actor"]["display"] for e in data["timeline"]))
        _assert_no_personal_data(self, self.get("manager", "receipt", self.receipt.pk))

    def test_r2_receipt_forbidden_403_and_401(self):
        self.assertEqual(self.get("courier", "receipt", self.receipt.pk).status_code, 403)
        self.assertEqual(self.get("anonymous", "receipt", self.receipt.pk).status_code, 401)

    def test_r2_receipt_missing_404_without_echoing_id(self):
        res = self.get("owner", "receipt", "987654")
        self.assertEqual(res.status_code, 404)
        self.assertNotIn("987654", res.content.decode())
        self.assertEqual(self.get("owner", "receipt", "abc").status_code, 404)

    def test_r2_receipt_does_not_leak_cost(self):
        res = self.get("warehouse", "receipt", self.receipt.pk)
        body = res.content.decode()
        for key in ("rate", "purchase_rate", "landed_unit_cost", "purchase_amount"):
            self.assertNotIn(f'"{key}"', body)


class StocktakeTimelineTests(AuditTimelineBase):
    def setUp(self):
        super().setUp()
        self.rec = StockReconciliation.objects.create(
            count_date=timezone.localdate(), created_by=self.warehouse, note=FAKE_FREE_TEXT,
        )
        record_audit("approve_stockreconciliation", actor=self.manager, obj=self.rec)

    def test_r2_stocktake_happy_path(self):
        data = self.assert_timeline_shape(self.get("owner", "stocktake", self.rec.pk))
        self.assertEqual(data["doc"]["code"], f"KK-{self.rec.pk}")
        labels = [e["label"] for e in data["timeline"]]
        self.assertTrue(any("duyệt" in x.lower() for x in labels), labels)
        _assert_no_personal_data(self, self.get("owner", "stocktake", self.rec.pk))

    def test_r2_stocktake_forbidden_403_and_401(self):
        self.assertEqual(self.get("courier", "stocktake", self.rec.pk).status_code, 403)
        self.assertEqual(self.get("anonymous", "stocktake", self.rec.pk).status_code, 401)

    def test_r2_stocktake_404(self):
        self.assertEqual(self.get("owner", "stocktake", "987654").status_code, 404)


class ReturnTimelineTests(AuditTimelineBase):
    def setUp(self):
        super().setUp()
        batch = make_batch(self.item, self.supplier, self.warehouse_obj)
        self.rt = ReturnToStock.objects.create(
            batch=batch, qty=Decimal("2.000"), created_by=self.courier, note=FAKE_FREE_TEXT,
        )
        record_audit("return_to_warehouse", actor=self.courier, obj=self.rt, note="Chờ duyệt (BR-HV-02).")

    def test_r2_return_happy_path(self):
        data = self.assert_timeline_shape(self.get("warehouse", "return", self.rt.pk))
        self.assertEqual(data["doc"]["code"], f"RT-{self.rt.pk}")
        _assert_no_personal_data(self, self.get("warehouse", "return", self.rt.pk))

    def test_r2_return_forbidden_403_and_401(self):
        # API hiện tại cho delivery_staff đọc hàng hoàn (view_returntostock) nên dùng user không nhóm nào.
        self.clients["nobody"] = client_for(make_user("tl_nobody_rt"))
        self.assertEqual(self.get("anonymous", "return", self.rt.pk).status_code, 401)
        self.assertEqual(self.get("nobody", "return", self.rt.pk).status_code, 403)

    def test_r2_return_404(self):
        self.assertEqual(self.get("owner", "return", "987654").status_code, 404)


class DeliveryTimelineTests(AuditTimelineBase):
    def setUp(self):
        super().setUp()
        self.order, self.customer, self.note = make_order_with_note(
            "SO-TL-001", FAKE_PHONE, assigned_to=self.courier,
        )
        self.customer.name = FAKE_NAME
        self.customer.default_address = FAKE_ADDRESS
        self.customer.save()
        record_audit(
            "delivery_mark_failed", actor=self.courier, obj=self.note,
            changes={"failure_note": FAKE_FREE_TEXT, "phone": FAKE_PHONE},
            note=FAKE_ADDRESS,
        )
        record_audit(
            "recipient_changed", actor=self.manager, obj=self.note,
            changes={"fields": ["recipient_name", "recipient_phone"]},
        )
        self.other_courier = make_user("tl_giao2", roles.DELIVERY_STAFF)
        self.clients["other_courier"] = client_for(self.other_courier)

    def test_r2_delivery_happy_path_assigned_courier(self):
        res = self.get("courier", "delivery", self.note.pk)
        data = self.assert_timeline_shape(res)
        self.assertEqual(data["doc"]["code"], self.note.code)
        self.assertGreaterEqual(len(data["timeline"]), 3)
        _assert_no_personal_data(self, res)

    def test_r2_delivery_manager_sees_it_without_customer_data(self):
        res = self.get("manager", "delivery", self.note.pk)
        self.assert_timeline_shape(res)
        _assert_no_personal_data(self, res)

    def test_r2_delivery_other_courier_cannot_see_someone_elses_note(self):
        self.assertEqual(self.get("other_courier", "delivery", self.note.pk).status_code, 404)

    def test_r2_delivery_forbidden_403_and_401(self):
        nobody = make_user("tl_nobody")
        self.clients["nobody"] = client_for(nobody)
        self.assertEqual(self.get("nobody", "delivery", self.note.pk).status_code, 403)
        self.assertEqual(self.get("anonymous", "delivery", self.note.pk).status_code, 401)

    def test_r2_delivery_404(self):
        self.assertEqual(self.get("owner", "delivery", "987654").status_code, 404)


class ItemTimelineTests(AuditTimelineBase):
    def setUp(self):
        super().setUp()
        record_audit("item_image_replace", actor=self.manager, obj=self.item, changes={"image_id": [1, 2]})

    def test_r2_item_happy_path(self):
        data = self.assert_timeline_shape(self.get("manager", "item", self.item.pk))
        self.assertEqual(data["doc"]["code"], self.item.code)
        self.assertEqual(len(data["timeline"]), 1)

    def test_r2_item_forbidden_403_and_401(self):
        nobody = make_user("tl_nobody_item")
        self.clients["nobody"] = client_for(nobody)
        self.assertEqual(self.get("nobody", "item", self.item.pk).status_code, 403)
        self.assertEqual(self.get("anonymous", "item", self.item.pk).status_code, 401)

    def test_r2_item_404(self):
        self.assertEqual(self.get("owner", "item", "987654").status_code, 404)


class SupplierTimelineTests(AuditTimelineBase):
    def test_r2_supplier_happy_path(self):
        record_audit("supplier_update", actor=self.owner, obj=self.supplier)
        self.assert_timeline_shape(self.get("owner", "supplier", self.supplier.pk))

    def test_r2_supplier_forbidden_403_and_401(self):
        self.assertEqual(self.get("courier", "supplier", self.supplier.pk).status_code, 403)
        self.assertEqual(self.get("anonymous", "supplier", self.supplier.pk).status_code, 401)

    def test_r2_supplier_404(self):
        self.assertEqual(self.get("owner", "supplier", "987654").status_code, 404)


class CustomerTimelineTests(AuditTimelineBase):
    def setUp(self):
        super().setUp()
        self.customer = Customer.objects.create(
            phone=FAKE_PHONE, name=FAKE_NAME, default_address=FAKE_ADDRESS, note=FAKE_FREE_TEXT,
        )
        # Bất chấp quy ước ghi log, test cố tình nhét dữ liệu khách vào audit để chứng minh API không phản chiếu.
        record_audit(
            "update_customer", actor=self.manager, obj=self.customer,
            changes={"phone": FAKE_PHONE, "name": FAKE_NAME, "default_address": FAKE_ADDRESS},
            note=f"{FAKE_NAME} {FAKE_PHONE}",
        )

    def test_r2_customer_manager_200_without_personal_data(self):
        res = self.get("manager", "customer", self.customer.pk)
        data = self.assert_timeline_shape(res)
        self.assertEqual(data["doc"]["code"], f"KH-{self.customer.pk}")
        _assert_no_personal_data(self, res)
        self.assertNotIn("object_repr", res.content.decode())

    def test_r2_customer_owner_200(self):
        self.assertEqual(self.get("owner", "customer", self.customer.pk).status_code, 200)

    def test_r2_customer_warehouse_403(self):
        res = self.get("warehouse", "customer", self.customer.pk)
        self.assertEqual(res.status_code, 403)
        _assert_no_personal_data(self, res)

    def test_r2_customer_courier_403_even_for_own_note_customer(self):
        make_order_with_note("SO-TL-002", "0900000456", assigned_to=self.courier)
        own = Customer.objects.get(phone="0900000456")
        res = self.get("courier", "customer", own.pk)
        self.assertEqual(res.status_code, 403)

    def test_r2_customer_anonymous_401(self):
        self.assertEqual(self.get("anonymous", "customer", self.customer.pk).status_code, 401)

    def test_r2_customer_404(self):
        res = self.get("owner", "customer", "987654")
        self.assertEqual(res.status_code, 404)

    def test_r2_customer_response_is_no_store(self):
        res = self.get("manager", "customer", self.customer.pk)
        self.assertIn("no-store", res.headers.get("Cache-Control", ""))


class StaffTimelineTests(AuditTimelineBase):
    def setUp(self):
        super().setUp()
        record_audit(
            "staff_update", actor=self.owner, obj=self.warehouse,
            changes={"phone": [FAKE_PHONE, "0900000999"]},
        )
        record_audit("staff_groups_change", actor=self.owner, obj=self.warehouse)

    def test_r2_staff_owner_200(self):
        res = self.get("owner", "staff", self.warehouse.pk)
        data = self.assert_timeline_shape(res)
        self.assertEqual(data["doc"]["code"], self.warehouse.username)
        self.assertEqual(len(data["timeline"]), 2)
        self.assertNotIn(FAKE_PHONE, res.content.decode())
        self.assertNotIn("0900000999", res.content.decode())

    def test_r2_staff_without_manage_staff_403_and_401(self):
        self.assertEqual(self.get("manager", "staff", self.warehouse.pk).status_code, 403)
        self.assertEqual(self.get("warehouse", "staff", self.warehouse.pk).status_code, 403)
        self.assertEqual(self.get("anonymous", "staff", self.warehouse.pk).status_code, 401)

    def test_r2_staff_timeline_omits_logout_and_login_rows(self):
        record_audit("logout", actor=self.warehouse, obj=self.warehouse, note="Đăng xuất; thu hồi 1 token.")
        record_audit("login", actor=self.warehouse, obj=self.warehouse)
        data = self.get("owner", "staff", self.warehouse.pk).json()
        self.assertEqual(len(data["timeline"]), 2)
        self.assertNotIn("logout", {e["kind"] for e in data["timeline"]})
        self.assertNotIn("login", {e["kind"] for e in data["timeline"]})
        self.assertFalse(data["timeline_truncated"])

    def test_r2_staff_404(self):
        self.assertEqual(self.get("owner", "staff", "987654").status_code, 404)


class TimelineCapTests(AuditTimelineBase):
    """M1: timeline chỉ lấy N dòng AuditLog mới nhất, kèm `timeline_truncated`."""

    @override_settings(GUIDANCE_TIMELINE_MAX_ROWS=5)
    def test_r2_timeline_is_capped_to_newest_rows(self):
        for i in range(8):
            record_audit("staff_update", actor=self.owner, obj=self.warehouse)
        record_audit("staff_groups_change", actor=self.owner, obj=self.warehouse)  # mới nhất
        data = self.get("owner", "staff", self.warehouse.pk).json()
        self.assertEqual(len(data["timeline"]), 5)
        self.assertTrue(data["timeline_truncated"])
        self.assertEqual(data["timeline"][-1]["kind"], "staff_groups_change")  # giữ dòng mới nhất, cũ → mới
        ats = [e["at"] for e in data["timeline"]]
        self.assertEqual(ats, sorted(ats))

    @override_settings(GUIDANCE_TIMELINE_MAX_ROWS=5)
    def test_r2_timeline_exactly_at_limit_is_not_truncated(self):
        for _ in range(5):
            record_audit("staff_update", actor=self.owner, obj=self.warehouse)
        data = self.get("owner", "staff", self.warehouse.pk).json()
        self.assertEqual(len(data["timeline"]), 5)
        self.assertFalse(data["timeline_truncated"])

    def test_r2_default_cap_is_200(self):
        from apps.common.guidance.audit_timeline import timeline_max_rows

        self.assertEqual(timeline_max_rows(), 200)

    @override_settings(GUIDANCE_TIMELINE_MAX_ROWS=3)
    def test_r2_logout_noise_does_not_consume_the_cap(self):
        record_audit("staff_update", actor=self.owner, obj=self.warehouse)
        for _ in range(10):
            record_audit("logout", actor=self.warehouse, obj=self.warehouse)
        data = self.get("owner", "staff", self.warehouse.pk).json()
        self.assertEqual([e["kind"] for e in data["timeline"]], ["staff_update"])
        self.assertFalse(data["timeline_truncated"])


class UnknownDocTypeTests(AuditTimelineBase):
    def test_r2_unknown_type_404_fixed_code(self):
        res = self.get("owner", "khong_co", "1")
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json()["code"], "GUIDANCE_TYPE_UNKNOWN")
        self.assertNotIn("khong_co", res.content.decode())  # L5: không lặp lại input

    def test_r2_group_type_is_registered(self):
        # Lô 14 đăng ký `group`: loại chứng từ không còn là "không hỗ trợ" (nhóm id lạ → 404 thường).
        response = self.get("owner", "group", "987654")
        self.assertEqual(response.status_code, 404)
        self.assertNotEqual(response.json().get("code"), "GUIDANCE_TYPE_UNKNOWN")

    def test_r2_existing_types_still_work(self):
        self.assertEqual(self.get("owner", "batch", "987654").status_code, 404)

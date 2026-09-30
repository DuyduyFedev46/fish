"""
QA P8 Lô 1 — SR-01: ca NGOÀI đường thuận do QA bổ sung (không trùng test của dev).
Dữ liệu giả. Lô 10 kg, giá mua 81234 đ/kg (loss_amount = 812340).
"""
import datetime
import json
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.catalog.models import Item, ItemGroup
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.batches import services as batch_services
from apps.inventory.models import Batch, Warehouse
from apps.purchasing.models import Supplier
from apps.accounts import roles

AUDIT_URL = "/api/audit-logs/"


class P8Lo1QaSr01Edges(TestCase):
    def setUp(self):
        g = ItemGroup.objects.create(name="Cá biển")
        self.item = Item.objects.create(code="CA01", name="Cá nục giả", item_group=g,
                                        shelf_life_in_days=60, is_active=True)
        self.sup = Supplier.objects.create(name="Cảng Giả", is_active=True)
        self.wh = Warehouse.objects.create(name="Kho giả")
        self.chu = make_user("chu_qa1", roles.OWNER)
        self.ql = make_user("ql_qa1", roles.MANAGER)
        self.kho = make_user("kho_qa1", roles.WAREHOUSE_STAFF)
        self.batch = batch_services.create_batch(
            item=self.item, supplier=self.sup, warehouse=self.wh,
            received_date=timezone.localdate() - datetime.timedelta(days=70),
            qty=Decimal("10"), purchase_rate=Decimal("81234"),
        )
        batch_services.publish_batch(batch=self.batch, actor=None)
        Batch.objects.filter(pk=self.batch.pk).update(status=Batch.Status.EXPIRED)
        batch_services.cancel_expired_batch(batch=Batch.objects.get(pk=self.batch.pk), actor=self.chu)

    def test_qa_filter_actor_kind_va_action_khac_van_khong_lo(self):
        """Mọi biến thể lọc (actor_kind/action) của quan_ly: không đường vòng lộ loss_amount."""
        c = client_for(self.ql)
        for params in ({}, {"actor_kind": "user"}, {"actor_kind": "system"}, {"actor_kind": "ai"},
                       {"action": "cancel_expired_batch"}, {"action": "recompute_landed_cost"}):
            r = c.get(AUDIT_URL, params)
            self.assertEqual(r.status_code, 200, params)
            self.assertNotIn("loss_amount", json.dumps(r.json()["results"]), params)
            self.assertNotIn("812340", json.dumps([[x["changes"], x["note"]] for x in r.json()["results"]]), params)

    def test_qa_khong_co_route_chi_tiet_hay_ghi(self):
        """Không có GET /audit-logs/<id>/ (đường vòng lộ bản gốc) và không ghi/sửa/xoá."""
        row = AuditLog.objects.get(action="cancel_expired_batch")
        c = client_for(self.chu)
        self.assertEqual(c.get(f"{AUDIT_URL}{row.pk}/").status_code, 404)
        for m in ("post", "put", "patch", "delete"):
            r = getattr(c, m)(AUDIT_URL, {}, format="json")
            self.assertEqual(r.status_code, 405, m)
        self.assertTrue(AuditLog.objects.filter(pk=row.pk).exists())
        self.assertIn("loss_amount", AuditLog.objects.get(pk=row.pk).changes)

    def test_qa_guidance_lo_nhan_khong_so_voi_ql_va_kho_co_so_voi_chu(self):
        """Đường đọc thứ hai của cùng dòng audit (timeline lô): quan_ly/nv_kho không thấy số lỗ."""
        blobs = {}
        for name, u in ((roles.OWNER, self.chu), ("ql", self.ql), ("kho", self.kho)):
            r = client_for(u).get(f"/api/guidance/batch/{self.batch.pk}/")
            blobs[name] = (r.status_code, json.dumps(r.json(), ensure_ascii=False) if r.status_code == 200 else "")
        self.assertEqual(blobs[roles.OWNER][0], 200)
        self.assertEqual(blobs["ql"][0], 200)  # chống xanh giả: quan_ly phải gọi được
        self.assertIn("Chủ đã huỷ lô", blobs["ql"][1])
        self.assertIn("Huỷ lô quá hạn (lỗ", blobs[roles.OWNER][1])
        for name in ("ql", "kho"):
            if blobs[name][0] == 200:
                self.assertNotIn("812340", blobs[name][1].replace(".", "").replace(",", ""), name)
                self.assertNotIn("loss_amount", blobs[name][1], name)

    @override_settings(AI_ENABLED=True)
    def test_qa_ai_registry_khong_co_lenh_doc_nhat_ky_lo_gia_von(self):
        """AI registry: nếu có lệnh đọc audit-log, kết quả của quan_ly không chứa loss_amount."""
        idx = client_for(self.ql).get("/api/ai/commands/index/")
        self.assertEqual(idx.status_code, 200)
        ids = [c.get("id") for c in json.loads(json.dumps(idx.json())).get("commands", [])] \
            if isinstance(idx.json(), dict) else []
        self.assertGreater(len(ids), 0, "index rỗng -> test vô nghĩa")
        audit_cmds = [i for i in ids if i and "audit" in i.lower()]
        for cid in audit_cmds:
            r = client_for(self.ql).post(f"/api/ai/commands/{cid}/call/", {"args": {}}, format="json")
            self.assertNotIn("loss_amount", r.content.decode())
            self.assertNotIn("812340", r.content.decode())

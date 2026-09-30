"""
S01 — Nhật ký hành động không lộ giá vốn (L-3, bất biến 1, BR-PQ-13, BR-GV-03).
Test AC1 đến AC6.
"""
import json
from decimal import Decimal
from django.test import TestCase

from apps.accounts.models import AuditLog
from apps.common.audit import record_audit
from apps.common.cost_keys import COST_KEYS
from apps.common.tests.fixtures import client_for, make_user
from apps.accounts import roles

AUDIT_URL = "/api/audit-logs/"


class AuditLogCostRedactionTests(TestCase):
    def setUp(self):
        self.chu = make_user("chu_l3", roles.OWNER)
        self.ql = make_user("ql_l3", roles.MANAGER)
        self.kho = make_user("kho_l3", roles.WAREHOUSE_STAFF)
        self.giao = make_user("giao_l3", roles.DELIVERY_STAFF)

        # Dòng mẫu 1: recompute_landed_cost
        self.row_recompute = record_audit(
            "recompute_landed_cost",
            actor=self.chu,
            changes={
                "landed_unit_cost": {"from": "111111.1111", "to": "987654.3210"},
                "status": {"from": "DRAFT", "to": "APPROVED"},
            },
        )
        # Dòng mẫu 2: admin_edit
        self.row_admin = record_audit(
            "admin_edit",
            actor=self.chu,
            changes={
                "purchase_rate": {"from": "50000", "to": "60000"},
                "landed_unit_cost": {"from": "55000", "to": "65000"},
                "status": {"from": "DRAFT", "to": "PUBLISHED"},
            },
        )
        # Dòng mẫu 3: close_batch
        self.row_close = record_audit(
            "close_batch",
            actor=self.chu,
            changes={
                "status": {"from": "SELLING", "to": "CLOSED"},
                "unit_cost": {"from": "70000", "to": "70000"},
            },
        )

    def test_s01_ac1_chu_thay_du_gia_von(self):
        client = client_for(self.chu)
        resp = client.get(AUDIT_URL, {"action": "recompute_landed_cost"})
        self.assertEqual(resp.status_code, 200)
        results = resp.json()["results"]
        self.assertEqual(len(results), 1)
        changes = results[0]["changes"]
        self.assertIn("landed_unit_cost", changes)
        self.assertEqual(
            changes["landed_unit_cost"],
            {"from": "111111.1111", "to": "987654.3210"},
        )
        self.assertIn("status", changes)

    def test_s01_ac2_quan_ly_khong_thay_gia_von(self):
        client = client_for(self.ql)
        resp = client.get(AUDIT_URL)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Kiểm tra sâu mọi dòng và mọi dictionary
        def check_no_cost_keys(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    self.assertNotIn(
                        k,
                        COST_KEYS,
                        f"Khoá giá vốn {k} bị rò rỉ trong output của quan_ly!",
                    )
                    check_no_cost_keys(v)
            elif isinstance(node, list):
                for item in node:
                    check_no_cost_keys(item)

        for row in data["results"]:
            check_no_cost_keys(row["changes"])

        # Chuỗi JSON không chứa con số giá vốn mẫu
        content = json.dumps(data)
        self.assertNotIn("987654.3210", content)
        self.assertNotIn("111111.1111", content)
        self.assertNotIn("55000", content)
        self.assertNotIn("65000", content)

        # Nhưng các khoá không nhạy cảm cùng dòng (vd status) vẫn còn
        by_action = {r["action"]: r["changes"] for r in data["results"]}
        self.assertIn("status", by_action["recompute_landed_cost"])
        self.assertIn("status", by_action["admin_edit"])
        self.assertIn("status", by_action["close_batch"])

    def test_s01_ac3_quan_ly_co_quyen_view_costprice_thay_gia_von(self):
        ql_with_perm = make_user("ql_perm", roles.MANAGER, perms=["inventory.view_costprice"])
        client = client_for(ql_with_perm)
        resp = client.get(AUDIT_URL, {"action": "recompute_landed_cost"})
        self.assertEqual(resp.status_code, 200)
        changes = resp.json()["results"][0]["changes"]
        self.assertIn("landed_unit_cost", changes)
        self.assertEqual(
            changes["landed_unit_cost"],
            {"from": "111111.1111", "to": "987654.3210"},
        )

        # Superuser cũng thấy
        superuser = make_user("super", perms=[])
        superuser.is_superuser = True
        superuser.save()
        resp_su = client_for(superuser).get(AUDIT_URL, {"action": "recompute_landed_cost"})
        self.assertEqual(resp_su.status_code, 200)
        self.assertIn("landed_unit_cost", resp_su.json()["results"][0]["changes"])

    def test_s01_ac4_phan_quyen_giu_nguyen_va_loc_action(self):
        for user, expected in ((self.kho, 403), (self.giao, 403)):
            resp = client_for(user).get(AUDIT_URL)
            self.assertEqual(resp.status_code, expected)
        resp_anon = client_for(None).get(AUDIT_URL)
        self.assertEqual(resp_anon.status_code, 401)

        # Lọc action vẫn chạy
        resp = client_for(self.ql).get(AUDIT_URL, {"action": "admin_edit"})
        self.assertEqual(resp.status_code, 200)
        results = resp.json()["results"]
        self.assertTrue(results)
        self.assertTrue(all(r["action"] == "admin_edit" for r in results))

    def test_s01_ac5_du_lieu_auditlog_khong_bi_sua_trong_db(self):
        # Kiểm chứng append-only: dữ liệu trong DB không bị thay đổi sau khi API được gọi
        row_before = AuditLog.objects.get(pk=self.row_recompute.pk)
        self.assertIn("landed_unit_cost", row_before.changes)

        client_for(self.ql).get(AUDIT_URL)

        row_after = AuditLog.objects.get(pk=self.row_recompute.pk)
        self.assertEqual(row_before.changes, row_after.changes)
        self.assertIn("landed_unit_cost", row_after.changes)

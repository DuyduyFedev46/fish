"""
S03 — AuditLog actor `ai:<user>` + endpoint nhật ký GET /api/audit-logs/.

Nguồn: 02b-tech-design mục 3 (contract S03) + 4.1/4.4; 02-stories S03-AC1…AC5;
BR-AI-08/09/14, bất biến 3 (append-only), 5 (audit bắt buộc), 8 (migration), 9 (không PII).
Dữ liệu trong test toàn bộ là giả (DoD 5).
"""
import json
from decimal import Decimal

from django.contrib.auth.models import Group, Permission
from django.db.models import ProtectedError
from django.test import TestCase

from apps.accounts.models import AuditLog
from apps.common.audit import record_audit
from apps.common.tests.fixtures import client_for, make_user
from apps.sales.orders.tests.test_s10_api import OrderApiBase
from apps.sales.refunds import services as refund_services
from apps.accounts import roles

AUDIT_URL = "/api/audit-logs/"


class AuditLogModelTests(TestCase):
    def setUp(self):
        self.kho = make_user("kho1", roles.WAREHOUSE_STAFF)
        self.chu = make_user("chu1", roles.OWNER)

    def test_s03_ac1_schema_3_field_moi_va_mac_dinh(self):
        log = AuditLog.objects.create(action="x")
        self.assertEqual(log.actor_kind, "user")  # default
        self.assertIsNone(log.ai_actor)
        self.assertEqual(log.proposal_ref, "")

    def test_s03_ac1_record_audit_dong_ai(self):
        log = record_audit(
            "propose_nhap_lo", actor_kind="ai", ai_actor=self.kho,
            note="P-9", proposal_ref="P-9",
        )
        self.assertEqual(log.actor_kind, "ai")
        self.assertIsNone(log.actor)  # dòng AI không gán actor user (BR-PQ-07)
        self.assertEqual(log.ai_actor, self.kho)
        self.assertEqual(log.proposal_ref, "P-9")
        self.assertIn(f"ai:{self.kho.get_username()}", str(log))

    def test_s03_record_audit_actor_none_la_system(self):
        log = record_audit("cancel_expired_orders")
        self.assertEqual(log.actor_kind, "system")
        self.assertIsNone(log.actor)

    def test_s03_record_audit_user_mac_dinh(self):
        log = record_audit("close_batch", actor=self.chu)
        self.assertEqual(log.actor_kind, "user")
        self.assertEqual(log.actor, self.chu)

    def test_s03_record_audit_proposal_ref_mac_dinh_rong(self):
        log = record_audit("close_batch", actor=self.chu)
        self.assertEqual(log.proposal_ref, "")

    def test_s03_ac3_fk_user_protect_khong_xoa_duoc(self):
        record_audit("propose_nhap_lo", actor_kind="ai", ai_actor=self.kho)
        with self.assertRaises(ProtectedError):
            self.kho.delete()


class AuditLogPermTests(TestCase):
    def test_s03_perm_view_auditlog_gan_cho_chu_va_quan_ly(self):
        perm = Permission.objects.get(content_type__app_label="accounts", codename="view_auditlog")
        for name in (roles.OWNER, roles.MANAGER):
            self.assertIn(perm, Group.objects.get(name=name).permissions.all(), name)
        for name in (roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF):
            self.assertNotIn(perm, Group.objects.get(name=name).permissions.all(), name)


class AuditLogListApiTests(TestCase):
    def setUp(self):
        self.chu = make_user("chu1", roles.OWNER)
        self.ql = make_user("ql1", roles.MANAGER)
        self.kho = make_user("kho1", roles.WAREHOUSE_STAFF)
        self.giao = make_user("giao1", roles.DELIVERY_STAFF)

        self.row_user = record_audit(
            "close_batch", actor=self.ql,
            changes={"status": {"from": "SELLING", "to": "CLOSED"}},
        )
        self.row_system = record_audit("cancel_expired_orders")
        self.row_ai = record_audit(
            "propose_nhap_lo", actor_kind="ai", ai_actor=self.kho,
            proposal_ref="P-1", note="P-1",
        )

    def test_s03_ac5_phan_quyen_doc_nhat_ky(self):
        for user, expected in (
            (self.chu, 200), (self.ql, 200), (self.kho, 403), (self.giao, 403),
        ):
            resp = client_for(user).get(AUDIT_URL)
            self.assertEqual(resp.status_code, expected, resp.content)
        resp = client_for(None).get(AUDIT_URL)  # chưa đăng nhập → 401
        self.assertEqual(resp.status_code, 401)

    def test_s03_ac2_ai_hien_thi_ai_ten_user(self):
        body = client_for(self.chu).get(AUDIT_URL).json()
        by_id = {row["id"]: row for row in body["results"]}
        ai = by_id[self.row_ai.id]
        self.assertEqual(ai["actor_kind"], "ai")
        self.assertEqual(ai["actor_display"], f"ai:{self.kho.get_username()}")
        self.assertEqual(ai["ai_actor"], self.kho.id)
        self.assertEqual(ai["proposal_ref"], "P-1")
        self.assertEqual(ai["action"], "propose_nhap_lo")
        user_row = by_id[self.row_user.id]
        self.assertEqual(user_row["actor_kind"], "user")
        self.assertEqual(user_row["actor_display"], self.ql.get_username())
        system_row = by_id[self.row_system.id]
        self.assertEqual(system_row["actor_kind"], "system")
        self.assertEqual(system_row["actor_display"], "system")

    def test_s03_loc_theo_action_va_actor_kind(self):
        resp = client_for(self.chu).get(AUDIT_URL, {"actor_kind": "ai"})
        rows = resp.json()["results"]
        self.assertTrue(rows)
        self.assertTrue(all(r["actor_kind"] == "ai" for r in rows))
        resp = client_for(self.chu).get(AUDIT_URL, {"action": "close_batch"})
        rows = resp.json()["results"]
        self.assertEqual({r["id"] for r in rows}, {self.row_user.id})

    def test_s03_phan_trang_20_dong_theo_quy_uoc(self):
        for i in range(25):
            record_audit(f"action_{i}", actor=self.ql)
        body = client_for(self.chu).get(AUDIT_URL).json()
        self.assertEqual(body["count"], 28)  # 25 + 3 dòng setUp
        self.assertEqual(len(body["results"]), 20)
        self.assertIsNotNone(body["next"])
        self.assertIsNone(body["previous"])
        page2 = client_for(self.chu).get(AUDIT_URL, {"page": 2}).json()
        self.assertEqual(len(page2["results"]), 8)

    def test_s03_ac3_append_only_khong_sua_khong_xoa(self):
        client = client_for(self.chu)
        for method in ("post", "put", "patch", "delete"):
            resp = getattr(client, method)(AUDIT_URL, {}, format="json")
            self.assertEqual(resp.status_code, 405, f"{method} → {resp.status_code}")
        # Không có route chi tiết → không thể UPDATE/DELETE một dòng.
        resp = client.delete(f"{AUDIT_URL}{self.row_user.id}/")
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(AuditLog.objects.filter(pk=self.row_user.pk).exists())

    def test_s03_contract_du_cac_field(self):
        rows = client_for(self.chu).get(AUDIT_URL).json()["results"]
        self.assertTrue(rows)
        expected = {
            "id", "actor_kind", "actor_display", "ai_actor", "action", "model_name",
            "object_id", "object_repr", "changes", "note", "proposal_ref", "created_at",
        }
        for row in rows:
            self.assertEqual(set(row), expected)


class AuditLogNoPiiTests(OrderApiBase):
    """S03-AC4 (PII): dòng audit đụng đơn chỉ chứa mã chứng từ — không tên/SĐT/địa chỉ khách."""

    PHONE = "0909000111"  # SĐT giả (DoD 5)
    NAME = "Chị Hoa"
    ADDRESS = "12 Lê Lợi, Vũng Tàu"

    def test_s03_ac4_audit_khong_chua_du_lieu_ca_nhan_khach(self):
        order = self._paid_order(phone=self.PHONE)
        refund_services.create_refund(
            invoice=order.invoice, amount=Decimal("10000"), is_partial=False,
            reason="Hàng hư", actor=self.chu,
        )
        row = AuditLog.objects.filter(action="create_refund").latest("id")
        blob = json.dumps(
            {"changes": row.changes, "note": row.note, "object_repr": row.object_repr},
            default=str,
        )
        for pii in (self.PHONE, self.NAME, self.ADDRESS):
            self.assertNotIn(pii, blob)
        # Endpoint nhật ký trả nguyên văn — không field nào chứa dữ liệu cá nhân.
        rows = client_for(self.chu).get(AUDIT_URL, {"action": "create_refund"}).json()["results"]
        self.assertTrue(rows)
        for r in rows:
            dumped = json.dumps(r, default=str)
            for pii in (self.PHONE, self.NAME, self.ADDRESS):
                self.assertNotIn(pii, dumped)

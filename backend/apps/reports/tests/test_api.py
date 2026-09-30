"""
Test phân quyền API báo cáo lãi lỗ theo lô: GET /api/reports/batch/<batch_id>/ (S06-AC6).
Bất biến #1: Không rò giá vốn và lãi lỗ cho người dùng thiếu quyền reports.view_profitreport.
"""
from decimal import Decimal

from django.test import TestCase

from apps.common.tests.fixtures import client_for, make_batch, make_master, make_user
from apps.accounts import roles


class BatchPnlApiTests(TestCase):
    EXPECTED_KEYS = {
        "batch_id", "provisional", "qty_received", "qty_sold", "landed_unit_cost",
        "revenue", "purchase_cost", "allocated_cost", "shrinkage_qty", "shrinkage_cost",
        "damage_qty", "damage_cost", "expired_qty", "expired_cost", "total_cost", "profit",
        "reversed_qty", "reversed_revenue",  # P8 Lô 4 (BR-HT-10)
        "supplier_return_qty", "supplier_refund_amount",  # P8 Lô 5 (BR-MH-08)
    }
    SENSITIVE_COST_KEYS = {"profit", "landed_unit_cost", "purchase_cost", "total_cost", "allocated_cost"}

    def setUp(self):
        item, sup, wh = make_master()
        self.batch = make_batch(item, sup, wh, qty="20")
        self.batch.landed_unit_cost = Decimal("85000")
        self.batch.save(update_fields=["landed_unit_cost"])
        self.url = f"/api/reports/batch/{self.batch.batch_id}/"

    def test_chu_can_view_batch_pnl(self):
        """Chủ sở hữu quyền view_profitreport -> 200, đủ 20 khoá (thêm expired_qty, expired_cost theo TL-4; reversed_qty/revenue theo P8 Lô 4; supplier_return_qty/refund theo Lô 5)."""
        user = make_user("chu1", roles.OWNER)
        resp = client_for(user).get(self.url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(set(data.keys()), self.EXPECTED_KEYS)
        self.assertEqual(len(data), 20)
        self.assertEqual(data["batch_id"], self.batch.batch_id)

    def test_non_owner_groups_forbidden_and_no_cost_keys(self):
        """quan_ly, nv_kho, nv_giao -> 403, body lỗi không có khoá giá vốn/lãi lỗ."""
        for username, group in [("ql1", roles.MANAGER), ("kho1", roles.WAREHOUSE_STAFF), ("giao1", roles.DELIVERY_STAFF)]:
            user = make_user(username, group)
            resp = client_for(user).get(self.url)
            self.assertEqual(resp.status_code, 403, f"Group {group} phải nhận 403")
            data = resp.json()
            # So sánh khoá trong response JSON lỗi, đảm bảo không có khoá giá vốn/lãi lỗ
            body_keys = set(data.keys()) if isinstance(data, dict) else set()
            self.assertEqual(
                body_keys & self.SENSITIVE_COST_KEYS,
                set(),
                f"Group {group} không được rò rỉ khoá giá vốn",
            )

    def test_anonymous_user_unauthorized(self):
        """Khách chưa đăng nhập -> 401 Unauthorized."""
        resp = client_for(None).get(self.url)
        self.assertEqual(resp.status_code, 401)

    def test_non_existent_batch_returns_404(self):
        """Mã lô không tồn tại -> 404 Not Found."""
        user = make_user("chu2", roles.OWNER)
        resp = client_for(user).get("/api/reports/batch/BATCH-NONEXISTENT/")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("detail", resp.json())

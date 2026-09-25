"""
Vá rò giá vốn ở `GET /api/dashboard/summary/` (lô L6) · bất biến #1, BR-PQ-15, S8-AC2.

Quy ước contract: field giá vốn mà người xem thiếu `inventory.view_costprice` thì **không có
key** trong JSON (không null, không "—"). `kpis.inventory_value` = Σ qty × landed_unit_cost.
"""
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.common.tests.fixtures import client_for, make_batch, make_master, make_user

URL = "/api/dashboard/summary/"
COST_KEYS = {"inventory_value", "unit_cost", "landed_unit_cost", "purchase_rate", "rate",
             "cost", "cogs", "profit", "margin", "gross_profit"}


def all_keys(value):
    if isinstance(value, dict):
        keys = set(value)
        for v in value.values():
            keys |= all_keys(v)
        return keys
    if isinstance(value, list):
        return set().union(*(all_keys(v) for v in value)) if value else set()
    return set()


class DashboardCostLeakTests(TestCase):
    def setUp(self):
        item, sup, wh = make_master()
        batch = make_batch(item, sup, wh, qty="10")
        batch.landed_unit_cost = Decimal("81234.56")
        batch.save(update_fields=["landed_unit_cost"])

    def test_l6_quan_ly_va_nv_kho_khong_co_key_gia_von(self):
        for user in (make_user("ql1", "quan_ly"), make_user("kho1", "nv_kho"),
                     make_user("kho2", "nv_kho", "nv_giao")):
            resp = client_for(user).get(URL)
            self.assertEqual(resp.status_code, 200, user.username)
            body = resp.json()
            self.assertEqual(all_keys(body) & COST_KEYS, set(), user.username)
            self.assertNotIn("inventory_value", body["kpis"])
            self.assertTrue(body["batches"], "phải có lô để kiểm dòng")
            self.assertNotIn("812345.6", resp.content.decode())  # 10 × 81234.56
            self.assertNotIn("81234.56", resp.content.decode())

    def test_l6_chu_van_thay_gia_von(self):
        body = client_for(make_user("loc", "chu")).get(URL).json()
        self.assertEqual(body["kpis"]["inventory_value"], 812345.6)
        self.assertEqual(body["batches"][0]["unit_cost"], 81234.56)

    def test_l6_kpi_khac_van_du_cho_quan_ly(self):
        body = client_for(make_user("ql1", "quan_ly")).get(URL).json()
        self.assertEqual(set(body["kpis"]),
                         {"revenue_today", "pending_orders", "booked_soon", "near_expiry"})

    def test_l6_nv_giao_403_chua_dang_nhap_401(self):
        self.assertEqual(client_for(make_user("giao1", "nv_giao")).get(URL).status_code, 403)
        self.assertEqual(APIClient().get(URL).status_code, 401)


class R6DashboardNearExpiryTests(TestCase):
    """R6 (code review): cận hạn chỉ tính lô BÁN ĐƯỢC (cùng tiêu chí S1 `sellable_batches`:
    SELLING/NEAR_EXPIRY và expiry_date >= hôm nay) — loại lô đã quá hạn (job chưa chạy) và lô
    DRAFT. Thêm `near_expiry_days` (= settings.BATCH_NEAR_EXPIRY_DAYS) để FE hiện đúng số ngày."""

    def setUp(self):
        from datetime import timedelta

        from django.utils import timezone

        from apps.inventory.models import Batch
        item, sup, wh = make_master()
        today = timezone.localdate()

        def lot(status, days_left):
            b = make_batch(item, sup, wh, qty="5")
            b.status = status
            b.expiry_date = today + timedelta(days=days_left)
            b.save(update_fields=["status", "expiry_date"])
            return b

        self.ok = lot(Batch.Status.NEAR_EXPIRY, 2)          # cận hạn thật
        self.hom_nay = lot(Batch.Status.SELLING, 0)         # hạn = hôm nay: còn bán (C1)
        self.qua_han = lot(Batch.Status.NEAR_EXPIRY, -1)    # đã quá hạn, job chưa chạy
        self.qua_han2 = lot(Batch.Status.SELLING, -3)
        self.nhap = lot(Batch.Status.DRAFT, 1)              # chưa publish
        self.xa = lot(Batch.Status.SELLING, 60)             # còn xa hạn
        self.user = make_user("ql1", "quan_ly")

    def test_r6_dem_va_canh_bao_chi_lo_ban_duoc(self):
        from django.test import override_settings
        with override_settings(BATCH_NEAR_EXPIRY_DAYS=7):
            body = client_for(self.user).get(URL).json()
        self.assertEqual(body["kpis"]["near_expiry"], 2)
        self.assertEqual({a["batch_id"] for a in body["alerts"]},
                         {self.ok.batch_id, self.hom_nay.batch_id})
        self.assertTrue(all(a["days_left"] >= 0 for a in body["alerts"]))
        flags = {r["batch_id"]: r["near_expiry"] for r in body["batches"]}
        self.assertFalse(flags.get(self.qua_han.batch_id, False))
        self.assertFalse(flags.get(self.nhap.batch_id, False))
        self.assertTrue(flags[self.ok.batch_id])

    def test_r6_tra_near_expiry_days_theo_settings(self):
        from django.test import override_settings
        with override_settings(BATCH_NEAR_EXPIRY_DAYS=7):
            body = client_for(self.user).get(URL).json()
        self.assertEqual(body["near_expiry_days"], 7)
        with override_settings(BATCH_NEAR_EXPIRY_DAYS=1):
            body = client_for(self.user).get(URL).json()
        self.assertEqual(body["near_expiry_days"], 1)
        self.assertEqual(body["kpis"]["near_expiry"], 1)  # chỉ lô hạn hôm nay (≤ hôm nay + 1)
        # Key mới không kéo theo giá vốn với quản lý.
        self.assertEqual(all_keys(body) & COST_KEYS, set())

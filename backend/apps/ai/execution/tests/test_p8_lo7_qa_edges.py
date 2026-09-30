"""
QA P8 Lô 7 — ca ngoài đường thuận cho SR-22 BM-07 (scrub giá vốn) và F07 (mốc ngày giờ VN). Chỉ dữ liệu giả.
"""
import datetime
from unittest import mock
from zoneinfo import ZoneInfo

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, override_settings

from apps.ai.execution.scrub import scrub_data
from apps.ai.models import AiAction, AiConfigVersion
from apps.ai.registry.discovery import get_registry
from apps.catalog.models import Item, ItemGroup
from apps.common.cost_keys import COST_KEYS
from apps.common.tests.fixtures import client_for, make_batch, make_master, make_user
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier

VN = ZoneInfo("Asia/Ho_Chi_Minh")
URL = "/api/ai/commands/purchasing.purchasereceipt.nhap_lo/call/"


def _keys(obj, acc=None):
    acc = set() if acc is None else acc
    if isinstance(obj, dict):
        for k, v in obj.items():
            acc.add(str(k).lower())
            _keys(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _keys(v, acc)
    return acc


class QaBm07Tests(TestCase):
    PAYLOAD = {
        "results": [
            {"batch_id": "B1", "purchase_rate": "80000", "landed_unit_cost": "82000", "qty": "5",
             "nested": {"profit": "1", "cogs": "2", "loss_amount": "3", "margin": "4", "expired_cost": "5"}},
        ],
        "customer_phone": "0900000111",
    }

    def test_qa_bm07_ma_tran_group_chi_chu_thay_gia_von_pii_luon_bi_bo(self):
        expect_cost = {"chu": True, "quan_ly": False, "nv_kho": False, "nv_giao": False, "cskh": False}
        for g, sees in expect_cost.items():
            with self.subTest(group=g):
                u = make_user(f"qa7bm07_{g}", g)
                keys = _keys(scrub_data(self.PAYLOAD, user=u, is_ai_read=False))
                got = bool(keys & COST_KEYS)
                self.assertEqual(got, sees, f"{g}: keys={keys & COST_KEYS}")
                self.assertNotIn("customer_phone", keys)
                self.assertIn("batch_id", keys)  # không lọc nhầm khoá thường

    def test_qa_bm07_view_profitreport_don_le_va_view_costprice_don_le(self):
        pnl = make_user("qa7_pnl", perms=("reports.view_profitreport",))
        self.assertFalse(_keys(scrub_data(self.PAYLOAD, user=pnl, is_ai_read=False)) & COST_KEYS)
        cost = make_user("qa7_cost", perms=("inventory.view_costprice",))
        self.assertTrue(_keys(scrub_data(self.PAYLOAD, user=cost, is_ai_read=False)) & COST_KEYS)
        self.assertFalse(_keys(scrub_data(self.PAYLOAD, user=AnonymousUser(), is_ai_read=False)) & COST_KEYS)
        self.assertFalse(_keys(scrub_data(self.PAYLOAD, user=None, is_ai_read=False)) & COST_KEYS)

    def test_qa_bm07_khoa_viet_hoa_va_khong_sua_input(self):
        u = make_user("qa7_kho_case", "nv_kho")
        import copy
        data = {"Purchase_Rate": "1", "UNIT_COST": "2", "ok": "3"}
        snap = copy.deepcopy(data)
        out = scrub_data(data, user=u, is_ai_read=False)
        self.assertEqual(out, {"ok": "3"})
        self.assertEqual(data, snap)

    def test_qa_bm07_that_qua_endpoint_period_pnl_user_chi_co_view_profitreport_khong_thay_khoa_gia_von(self):
        item, sup, wh = make_master()
        batch = make_batch(item, sup, wh)
        pnl = make_user("qa7_pnl2", perms=("reports.view_profitreport",))
        chu = make_user("qa7_chu_pnl", "chu")
        today = datetime.date.today().isoformat()
        body = {"args": {"year": datetime.date.today().year, "month": datetime.date.today().month}}
        with override_settings(AI_ENABLED=True):
            res_pnl = client_for(pnl).post("/api/ai/commands/reports.period_pnl/call/", body, format="json")
            res_chu = client_for(chu).post("/api/ai/commands/reports.period_pnl/call/", body, format="json")
        self.assertEqual(res_chu.status_code, 200, res_chu.content[:400])
        chu_keys = _keys(res_chu.json())
        self.assertTrue(chu_keys & COST_KEYS, f"đối chứng: Chủ phải thấy khoá giá vốn, thấy: {sorted(chu_keys)}")
        if res_pnl.status_code == 200:
            self.assertFalse(_keys(res_pnl.json()) & COST_KEYS, sorted(_keys(res_pnl.json()) & COST_KEYS))
        else:
            self.assertIn(res_pnl.status_code, (403, 404), res_pnl.content[:300])


@override_settings(AI_ENABLED=True, AI_WRITE_LEVELS_ALLOWED="B")
class QaF07BoundaryTests(TestCase):
    def setUp(self):
        self.kho = make_user("qa7f07_kho", "nv_kho")
        self.client = client_for(self.kho)
        group = ItemGroup.objects.create(name="Cá biển")
        self.item = Item.objects.create(code="CA-QF07", name="Cá ngừ", item_group=group, shelf_life_in_days=60, is_active=True)
        self.sup = Supplier.objects.create(name="Đầu mối giả", is_active=True)
        self.wh = Warehouse.objects.create(name="Kho giả")
        AiConfigVersion.objects.create(
            user=self.kho, version=1, group_levels={"thu_mua": {"read": "A", "write": "B"}},
            overrides={"purchasing.purchasereceipt.nhap_lo": "B"},
            limits={"purchasing.purchasereceipt.nhap_lo": {"kg": "150", "vnd": "30000000"}}, created_by=self.kho,
        )
        get_registry().build(force=True)

    def _seed(self, n, when):
        ids = [AiAction.objects.create(
            command="purchasing.purchasereceipt.nhap_lo", kind=AiAction.Kind.WRITE,
            status=AiAction.Status.DONE, level=AiAction.Level.B, owner=self.kho).pk for _ in range(n)]
        AiAction.objects.filter(pk__in=ids).update(created_at=when)

    def _call(self, now_vn):
        payload = {"args": {
            "supplier": self.sup.id, "received_date": now_vn.date().isoformat(), "warehouse": self.wh.id,
            "lines": [{"item_code": self.item.code, "qty": "20.000", "rate": "80000.00", "shelf_life_days": 30}]}}
        with mock.patch("django.utils.timezone.now", return_value=now_vn.astimezone(datetime.timezone.utc)):
            return self.client.post(URL, payload, format="json")

    def test_qa_f07_23h59_vn_viec_00h00_01s_cung_ngay_van_tinh(self):
        self._seed(20, datetime.datetime(2026, 9, 30, 0, 0, 1, tzinfo=VN))
        res = self._call(datetime.datetime(2026, 9, 30, 23, 59, tzinfo=VN))
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.data["downgrade_reason"]["code"], "AI_DAILY_LIMIT")

    def test_qa_f07_viec_23h59_hom_qua_khong_tinh_sang_hom_nay(self):
        self._seed(20, datetime.datetime(2026, 9, 29, 23, 59, 59, tzinfo=VN))
        res = self._call(datetime.datetime(2026, 9, 30, 0, 1, tzinfo=VN))
        self.assertEqual(res.data["outcome"], "done", res.data)

    def test_qa_f07_viec_dung_00h00_00s_duoc_tinh_bien_gte(self):
        self._seed(20, datetime.datetime(2026, 9, 30, 0, 0, 0, tzinfo=VN))
        res = self._call(datetime.datetime(2026, 9, 30, 12, 0, tzinfo=VN))
        self.assertEqual(res.data["downgrade_reason"]["code"], "AI_DAILY_LIMIT")

    def test_qa_f07_mien_gio_00h07_vn_khong_bi_sot_viec_luc_06h30_vn_tren_ma_utc_cu(self):
        # 20 việc lúc 06:30 VN; gọi lúc 08:00 VN cùng ngày: mốc UTC cũ (07:00 VN) bỏ sót. Đây là ca dev đã có; kèm
        # ca 06:59 VN/07:01 VN để chứng minh không còn cạnh 07:00.
        self._seed(20, datetime.datetime(2026, 9, 30, 6, 59, tzinfo=VN))
        res = self._call(datetime.datetime(2026, 9, 30, 7, 1, tzinfo=VN))
        self.assertEqual(res.data["downgrade_reason"]["code"], "AI_DAILY_LIMIT")

    def test_qa_f07_du_lieu_nguoi_khac_khong_tinh_vao_han_muc_cua_toi(self):
        other = make_user("qa7f07_other", "nv_kho")
        ids = [AiAction.objects.create(
            command="purchasing.purchasereceipt.nhap_lo", kind=AiAction.Kind.WRITE,
            status=AiAction.Status.DONE, level=AiAction.Level.B, owner=other).pk for _ in range(20)]
        AiAction.objects.filter(pk__in=ids).update(created_at=datetime.datetime(2026, 9, 30, 6, 30, tzinfo=VN))
        res = self._call(datetime.datetime(2026, 9, 30, 8, 0, tzinfo=VN))
        self.assertEqual(res.data["outcome"], "done", res.data)

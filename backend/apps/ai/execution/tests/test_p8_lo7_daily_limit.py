"""
P8 Lô 7 — SR-22 / F07: mốc "đầu ngày" của hạn mức AI/ngày theo giờ VN (Asia/Ho_Chi_Minh), không phải 00:00 UTC.
Dữ liệu giả.
"""
import datetime
from unittest import mock
from zoneinfo import ZoneInfo

from django.test import TestCase, override_settings

from apps.ai.models import AiAction, AiConfigVersion
from apps.ai.registry.discovery import get_registry
from apps.catalog.models import Item, ItemGroup
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier

VN = ZoneInfo("Asia/Ho_Chi_Minh")
URL = "/api/ai/commands/purchasing.purchasereceipt.nhap_lo/call/"


@override_settings(AI_ENABLED=True, AI_WRITE_LEVELS_ALLOWED="B")
class F07DailyLimitBoundaryTests(TestCase):
    def setUp(self):
        self.kho = make_user("f07_kho", "nv_kho")
        self.client = client_for(self.kho)
        group = ItemGroup.objects.create(name="Cá biển")
        self.item = Item.objects.create(code="CA-F07", name="Cá ngừ", item_group=group,
                                        shelf_life_in_days=60, is_active=True)
        self.sup = Supplier.objects.create(name="Đầu mối giả", is_active=True)
        self.wh = Warehouse.objects.create(name="Kho giả")
        AiConfigVersion.objects.create(
            user=self.kho, version=1,
            group_levels={"thu_mua": {"read": "A", "write": "B"}},
            overrides={"purchasing.purchasereceipt.nhap_lo": "B"},
            limits={"purchasing.purchasereceipt.nhap_lo": {"kg": "150", "vnd": "30000000"}},
            created_by=self.kho,
        )
        get_registry().build(force=True)

    def _seed(self, n, when_vn):
        ids = []
        for _ in range(n):
            a = AiAction.objects.create(
                command="purchasing.purchasereceipt.nhap_lo", kind=AiAction.Kind.WRITE,
                status=AiAction.Status.DONE, level=AiAction.Level.B, owner=self.kho,
            )
            ids.append(a.pk)
        AiAction.objects.filter(pk__in=ids).update(created_at=when_vn)

    def _call(self, now_vn):
        payload = {"args": {
            "supplier": self.sup.id, "received_date": now_vn.date().isoformat(), "warehouse": self.wh.id,
            "lines": [{"item_code": self.item.code, "qty": "20.000", "rate": "80000.00", "shelf_life_days": 30}],
        }}
        with mock.patch("django.utils.timezone.now", return_value=now_vn.astimezone(datetime.timezone.utc)):
            return self.client.post(URL, payload, format="json")

    def test_f07_viec_luc_0630_gio_vn_hom_nay_van_tinh_vao_han_muc_ngay(self):
        """8:00 VN (01:00 UTC): 20 việc tạo lúc 06:30 VN cùng ngày phải bị tính -> hạ xuống C AI_DAILY_LIMIT.
        Mốc sai 00:00 UTC (= 07:00 VN) bỏ sót các việc trước 07:00 VN."""
        now = datetime.datetime(2026, 9, 30, 8, 0, tzinfo=VN)
        self._seed(20, datetime.datetime(2026, 9, 30, 6, 30, tzinfo=VN))
        res = self._call(now)
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.data["outcome"], "proposal")
        self.assertEqual(res.data["downgrade_reason"]["code"], "AI_DAILY_LIMIT")

    def test_f07_viec_toi_qua_gio_vn_khong_tinh_sang_hom_sau(self):
        """06:30 VN (23:30 UTC hôm trước): 20 việc lúc 20:00 VN HÔM QUA không tính vào hôm nay -> vẫn mức B."""
        now = datetime.datetime(2026, 9, 30, 6, 30, tzinfo=VN)
        self._seed(20, datetime.datetime(2026, 9, 29, 20, 0, tzinfo=VN))
        res = self._call(now)
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.data["outcome"], "done", res.data)
        self.assertEqual(res.data["level"], "B")

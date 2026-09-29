"""
Test suite cho Story DW-20: Chủ đặt trần ngưỡng và hạn mức ngày cho lệnh AI (caps).
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status

from apps.ai.models.policy import AiPolicyVersion
from apps.catalog.models import Item, ItemGroup
from apps.common.tests.fixtures import client_for, make_user
from apps.inventory.models import Warehouse
from apps.purchasing.models import Supplier

User = get_user_model()


class PolicyCapsTests(TestCase):
    def setUp(self):
        self.g = ItemGroup.objects.create(name="Cá")
        self.item1 = Item.objects.create(code="CA01", name="Cá nục", item_group=self.g, shelf_life_in_days=60, is_active=True)
        self.sup = Supplier.objects.create(name="Cảng cá Phan Thiết", is_active=True)
        self.wh = Warehouse.objects.create(name="Kho chính")

        self.u_chu = make_user("chu_caps", "chu")
        self.u_quanly = make_user("ql_caps", "quan_ly")
        self.u_kho = make_user("kho_caps", "nv_kho")

        self.client_chu = client_for(self.u_chu)
        self.client_quanly = client_for(self.u_quanly)
        self.client_kho = client_for(self.u_kho)

    def test_dw20_ac1_vuot_tran_cua_chu_bi_tu_choi_400(self):
        """DW-20-AC1: Chủ PUT caps {kg: 200, vnd: 30000000, daily: 20} -> NV kho PUT ngưỡng 250kg -> 400 BR-AI-19."""
        # Chủ đặt caps
        res_chu = self.client_chu.put(
            "/api/ai/policy/",
            {
                "base_version": 0,
                "caps": {
                    "purchasing.purchasereceipt.nhap_lo": {
                        "kg": 200,
                        "vnd": 30000000,
                        "daily": 20,
                    }
                },
                "acknowledge_responsibility": True,
            },
            format="json",
        )
        self.assertEqual(res_chu.status_code, status.HTTP_200_OK)

        # NV kho PUT limits 250 kg -> 400 BR-AI-19 "vượt trần của Chủ"
        res_kho = self.client_kho.put(
            "/api/ai/my-config/",
            {
                "base_version": 0,
                "limits": {
                    "purchasing.purchasereceipt.nhap_lo": {
                        "kg": "250",
                        "vnd": "20000000",
                    }
                },
                "acknowledge_responsibility": True,
            },
            format="json",
        )
        self.assertEqual(res_kho.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_kho.json().get("code"), "BR-AI-19")
        errors = res_kho.json().get("errors", {})
        self.assertIn("vượt trần của Chủ", errors.get("purchasing.purchasereceipt.nhap_lo", ""))

    @override_settings(AI_ENABLED=True)
    def test_dw20_ac2_nguong_hieu_luc_la_min_va_ha_c_khi_call(self):
        """DW-20-AC2: NV kho đặt 150kg, Chủ hạ trần 100kg -> call phiếu 120kg -> hạ C (ngưỡng hiệu lực = min)."""
        # Chủ đặt trần ban đầu 200 kg
        self.client_chu.put(
            "/api/ai/policy/",
            {
                "base_version": 0,
                "caps": {"purchasing.purchasereceipt.nhap_lo": {"kg": 200, "vnd": 30000000, "daily": 20}},
                "acknowledge_responsibility": True,
            },
            format="json",
        )

        # NV kho đặt ngưỡng 150 kg (hợp lệ <= 200)
        res_kho = self.client_kho.put(
            "/api/ai/my-config/",
            {
                "base_version": 0,
                "limits": {"purchasing.purchasereceipt.nhap_lo": {"kg": "150", "vnd": "20000000"}},
                "acknowledge_responsibility": True,
            },
            format="json",
        )
        self.assertEqual(res_kho.status_code, status.HTTP_200_OK)

        # Chủ hạ trần còn 100 kg
        p_latest = AiPolicyVersion.objects.order_by("-version").first()
        res_chu2 = self.client_chu.put(
            "/api/ai/policy/",
            {
                "base_version": p_latest.version,
                "caps": {"purchasing.purchasereceipt.nhap_lo": {"kg": 100, "vnd": 30000000, "daily": 20}},
                "acknowledge_responsibility": True,
            },
            format="json",
        )
        self.assertEqual(res_chu2.status_code, status.HTTP_200_OK)

        # NV kho call lệnh nhập phiếu 120 kg (> 100 kg trần Chủ) -> hạ C kèm downgrade_reason
        call_payload = {
            "args": {
                "supplier": self.sup.pk,
                "received_date": "2026-09-28",
                "lines": [{"item_code": "CA01", "qty": "120.000", "rate": "80000.00"}],
            }
        }
        res_call = self.client_kho.post(
            "/api/ai/commands/purchasing.purchasereceipt.nhap_lo/call/",
            call_payload,
            format="json",
        )
        self.assertEqual(res_call.status_code, status.HTTP_200_OK)
        data = res_call.json()
        self.assertEqual(data["outcome"], "proposal")
        self.assertEqual(data["level"], "C")
        self.assertIsNotNone(data["downgrade_reason"])
        self.assertEqual(data["downgrade_reason"]["code"], "AI_LIMIT_KG")
        self.assertIn("Vượt trần của Chủ", data["downgrade_reason"]["text"])

    @override_settings(AI_PRODUCTION_READY=False)
    def test_dw20_ac3_production_chan_dat_tran_lon_hon_c(self):
        """DW-20-AC3: AI_PRODUCTION_READY=False -> Chủ PUT trần max_level > C -> 400 BR-AI-27."""
        res = self.client_chu.put(
            "/api/ai/policy/",
            {
                "base_version": 0,
                "caps": {"purchasing.purchasereceipt.nhap_lo": {"max_level": "B", "kg": 200}},
                "acknowledge_responsibility": True,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json().get("code"), "BR-AI-27")

    def test_dw20_ac4_quan_ly_put_caps_bi_403(self):
        """DW-20-AC4: quan_ly gọi PUT policy (caps) -> 403."""
        res = self.client_quanly.put(
            "/api/ai/policy/",
            {
                "base_version": 0,
                "caps": {"purchasing.purchasereceipt.nhap_lo": {"kg": 100}},
                "acknowledge_responsibility": True,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_dw20_ac5_so_am_hoac_khong_phai_so_bi_400(self):
        """DW-20-AC5: Số âm hoặc không phải số -> 400, không phiên bản mới."""
        ver_before = AiPolicyVersion.objects.count()
        # Số âm
        res = self.client_chu.put(
            "/api/ai/policy/",
            {
                "base_version": 0,
                "caps": {"purchasing.purchasereceipt.nhap_lo": {"kg": -50}},
                "acknowledge_responsibility": True,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(AiPolicyVersion.objects.count(), ver_before)

        # Không phải số
        res2 = self.client_chu.put(
            "/api/ai/policy/",
            {
                "base_version": 0,
                "caps": {"purchasing.purchasereceipt.nhap_lo": {"kg": "abc"}},
                "acknowledge_responsibility": True,
            },
            format="json",
        )
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(AiPolicyVersion.objects.count(), ver_before)

    @override_settings(AI_ENABLED=False)
    def test_dw20_ac6_ai_tat_put_caps_van_chay(self):
        """DW-20-AC6: AI_ENABLED=False -> PUT caps vẫn chạy bình thường."""
        res = self.client_chu.put(
            "/api/ai/policy/",
            {
                "base_version": 0,
                "caps": {"purchasing.purchasereceipt.nhap_lo": {"kg": 150, "vnd": 20000000, "daily": 10}},
                "acknowledge_responsibility": True,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        p = AiPolicyVersion.objects.order_by("-version").first()
        self.assertIsNotNone(p)
        self.assertEqual(p.caps["purchasing.purchasereceipt.nhap_lo"]["kg"], 150)

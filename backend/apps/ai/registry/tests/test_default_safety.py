"""
Test feature mới không khai gì (DW-07-AC2, 02b §11.2).
Đảm bảo an toàn mặc định tuyệt đối: chỉ hiện với Group có quyền, lọc giá vốn & PII, mức C, form_only=true.
"""
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import include, path
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from apps.ai.policy.effective import effective_level
from apps.ai.policy.rules import COST_KEYS, SCRUB_FREE_TEXT_KEYS, SCRUB_PII_KEYS, is_force_c_action, is_red_zone_action
from apps.ai.registry.discovery import CommandRegistry
from apps.ai.registry.schema import get_serializer_output_fields, serializer_to_schema
from apps.common.api import BusinessModelPermissions, CostFieldSerializerMixin
from apps.common.tests.fixtures import make_user
from apps.inventory.models import Batch
from apps.sales.models import SalesOrder
from apps.ai import command_groups
from apps.accounts import roles


class DummyBatchSerializer(CostFieldSerializerMixin, serializers.ModelSerializer):
    sensitive_fields = ("purchase_rate", "landed_unit_cost")
    note = serializers.CharField(required=False)

    class Meta:
        model = Batch
        fields = [
            "id", "batch_id", "qty_available", "purchase_rate", "landed_unit_cost", "note",
        ]


class DummyFeatureViewSet(viewsets.ModelViewSet):
    """ViewSet thử nghiệm hoàn toàn KHÔNG KHAI BÁO bất kỳ metadata AI nào (02b §11.2)."""
    queryset = Batch.objects.all()
    serializer_class = DummyBatchSerializer
    permission_classes = [BusinessModelPermissions]

    @action(detail=True, methods=["post"])
    def do_something_manual(self, request, pk=None):
        # Đọc request.data tay, không khai serializer đầu vào
        data = request.data
        return Response({"status": "ok", "got": data.get("note")})


dummy_router = DefaultRouter()
dummy_router.register("test-dummy-feature", DummyFeatureViewSet, basename="dummybatch")

urlpatterns = [
    path("api/", include(dummy_router.urls)),
]


@override_settings(AI_ENABLED=True)
class DefaultSafetyTestCase(TestCase):
    def setUp(self):
        self.user_chu = make_user("chu_safety", roles.OWNER)
        self.user_kho = make_user("kho_safety", roles.WAREHOUSE_STAFF)
        self.user_giao = make_user("giao_safety", roles.DELIVERY_STAFF)

    def test_dw07_ac2_feature_moi_khong_khai_gi_an_toan_mac_dinh(self):
        """DW-07-AC2: ViewSet mới không khai gì tự động an toàn ở mọi tiêu chí."""
        # 1. Tạo CommandRegistry riêng cho dummy routes
        with override_settings(ROOT_URLCONF=__name__):
            reg = CommandRegistry()
            reg.build(force=True)
            specs = {s.id: s for s in reg.get_specs()}

            self.assertIn("ai.batch.list", specs)
            self.assertIn("ai.batch.retrieve", specs)
            self.assertIn("ai.batch.create", specs)
            self.assertIn("ai.batch.do_something_manual", specs)

            spec_list = specs["ai.batch.list"]
            spec_action = specs["ai.batch.do_something_manual"]

            # (1) Mặc định: sensitivity=cao, channel=local
            self.assertEqual(spec_list.sensitivity, command_groups.SENSITIVITY_HIGH)
            self.assertEqual(spec_list.channel, "local")
            self.assertEqual(spec_action.sensitivity, command_groups.SENSITIVITY_HIGH)
            self.assertEqual(spec_action.channel, "local")

            # (1b) Quyền xem: chỉ hiện với Group có view_batch
            self.assertEqual(effective_level(self.user_chu, spec_list), "A")
            self.assertEqual(effective_level(self.user_kho, spec_list), "A")
            # nv_giao không có view_batch -> OFF
            self.assertEqual(effective_level(self.user_giao, spec_list), "OFF")

            # (2) Lệnh ghi: level=C, max_level=C
            lvl_create_chu = effective_level(self.user_chu, specs["ai.batch.create"])
            self.assertEqual(lvl_create_chu, "C")
            self.assertEqual(specs["ai.batch.create"].max_level, "C")

            # (3) Lệnh đọc: output_fields không có khoá PII, không note (chữ tự do)
            raw_fields = get_serializer_output_fields(DummyBatchSerializer)
            clean_fields_kho = [
                f for f in raw_fields
                if f not in SCRUB_PII_KEYS and f not in COST_KEYS
            ]
            self.assertNotIn("purchase_rate", clean_fields_kho)
            self.assertNotIn("landed_unit_cost", clean_fields_kho)

            # (4) Action đọc request.data tay -> form_only=True
            self.assertTrue(spec_action.form_only, "Action đọc request.data tay phải có form_only=True")

            # (5) Thêm required_perms=("sales.confirm_refund",) -> tự thành vùng đỏ
            self.assertTrue(is_red_zone_action(("sales.confirm_refund",)))
            # Thêm quyền Tầng 2 lạ -> trần C ép
            self.assertTrue(is_force_c_action(("inventory.some_unknown_action",)))

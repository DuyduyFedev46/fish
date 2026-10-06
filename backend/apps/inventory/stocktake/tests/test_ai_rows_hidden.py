"""Lô dọn chữ AI (A8, 02b 2.3) — "người sửa gần nhất" của phiếu kiểm kê bỏ dòng AI khi AI tắt. Dữ liệu giả."""
from django.test import override_settings

from apps.common.audit import record_audit
from apps.inventory.models import StockReconciliation
from apps.inventory.stocktake import services as stocktake_services

from .base import URL, StocktakeApiBase


class LastEditorAiFlagTests(StocktakeApiBase):
    def setUp(self):
        super().setUp()
        rec = StockReconciliation.objects.create(count_date=self.today, created_by=self.warehouse_staff)
        record_audit("create_stockreconciliation", actor=self.warehouse_staff, obj=rec)
        record_audit("update_stockreconciliation", actor_kind="ai", ai_actor=self.manager, obj=rec)  # mới nhất
        self.rec = rec

    def _names(self):
        api = self.api(self.warehouse_staff)
        row = api.get(URL).json()["results"][0]
        detail = api.get(f"{URL}{self.rec.pk}/").json()
        return row["updated_by_name"], detail["updated_by_name"], stocktake_services._last_editor_name(self.rec)

    @override_settings(AI_ENABLED=False)
    def test_off_last_editor_is_latest_non_ai_row(self):
        for name in self._names():
            self.assertEqual(name, "Kho Thử")
            self.assertNotIn("AI", name)

    @override_settings(AI_ENABLED=True)
    def test_on_last_editor_is_ai(self):
        for name in self._names():
            self.assertEqual(name, "AI của Quản Lý Thử")

    @override_settings(AI_ENABLED=False)
    def test_off_serializer_never_prints_ai_even_if_annotation_says_ai(self):
        from apps.inventory.stocktake.serializers import StockReconciliationSerializer as S

        obj = self.rec
        obj.last_actor_kind, obj.last_ai_actor_username, obj.last_ai_actor_display_name = "ai", "x", "Y"
        obj.last_actor_username = obj.last_actor_display_name = None
        self.assertEqual(S().get_updated_by_name(obj), "Hệ thống")

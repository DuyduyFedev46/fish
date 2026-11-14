"""FISH-66 D6: API tải/nhập file không được bộ dò lệnh AI đăng ký thành lệnh (analysis §9)."""
from django.test import TestCase
from rest_framework.parsers import JSONParser
from rest_framework.views import APIView

from apps.ai.registry.discovery import CommandRegistry


class NoAiCommandForItemFilesTests(TestCase):
    def test_registry_has_no_command_for_item_file_routes(self):
        registry = CommandRegistry()
        registry.build(force=True)
        offending = [
            spec.path for spec in registry.get_specs()
            if "/catalog/items/export" in spec.path or "/catalog/items/import" in spec.path
        ]
        self.assertEqual(offending, [])

    def test_item_file_views_are_plain_apiviews_without_json_parser(self):
        from apps.catalog.item_files import api

        for name in ("ItemExportView", "ItemExportTemplateView"):
            view = getattr(api, name)
            self.assertTrue(issubclass(view, APIView))
            self.assertFalse(any(issubclass(p, JSONParser) for p in view.parser_classes), name)

    def test_item_viewset_has_no_export_action(self):
        from apps.catalog.items.api import ItemViewSet

        self.assertFalse(hasattr(ItemViewSet, "export"))

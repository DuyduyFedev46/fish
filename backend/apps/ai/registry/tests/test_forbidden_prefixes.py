"""
Chỉ mục lệnh AI không được chứa route của việc gọi xác nhận đơn (P8b Lô 3, rủi ro R1, bất biến 9).

Hàng đợi gọi xác nhận trả tên, SĐT, địa chỉ khách. Route cũ `/api/cskh/` và route mới `/api/confirmation/`
đều phải nằm trong `FORBIDDEN_PREFIXES` để registry bỏ qua; tiền tố cũ giữ vĩnh viễn (phòng thủ nhiều lớp).
"""
from unittest import mock

from django.test import TestCase
from django.urls import get_resolver

from apps.ai.policy import rules
from apps.ai.policy.rules import FORBIDDEN_PREFIXES, is_url_forbidden
from apps.ai.registry.discovery import CommandRegistry, _clean_path, _collect_routes, get_registry

CUSTOMER_DATA_PREFIXES = ("/api/cskh/", "/api/confirmation/")


class ForbiddenPrefixesTests(TestCase):
    def test_both_confirmation_prefixes_are_forbidden(self):
        for prefix in CUSTOMER_DATA_PREFIXES:
            self.assertIn(prefix, FORBIDDEN_PREFIXES)
            self.assertTrue(is_url_forbidden(f"{prefix}queue/"))
            self.assertTrue(is_url_forbidden(f"{prefix}search/"))

    def test_registry_has_no_command_under_confirmation_prefixes(self):
        specs = get_registry().get_specs()
        self.assertGreater(len(specs), 0, "Phải quét được registry thật (không rỗng).")
        offenders = [s.id for s in specs if s.path.startswith(CUSTOMER_DATA_PREFIXES)]
        self.assertEqual(offenders, [])
        # Không lệnh nào có tên/đường dẫn của hàng đợi xác nhận dù route đi đường nào.
        self.assertEqual([s.id for s in specs if "confirmationtask" in s.id.lower()], [])

    def test_sweep_sees_the_confirmation_routes_so_the_assertion_above_is_meaningful(self):
        """Route xác nhận có thật trong URLconf (quét > 0), nhưng registry vẫn bỏ qua."""
        routes = []
        _collect_routes(get_resolver().url_patterns, prefix="", routes=routes)
        paths = [_clean_path(pattern) for pattern, _cb, _args in routes]
        for prefix in CUSTOMER_DATA_PREFIXES:
            hits = [p for p in paths if p.startswith(prefix)]
            self.assertGreater(len(hits), 0, f"URLconf phải có route dưới {prefix}")

    def test_guard_is_what_keeps_the_routes_out_of_the_index(self):
        """Bỏ tiền tố khỏi danh sách cấm thì route xác nhận lọt vào chỉ mục: chứng minh test có răng."""
        for prefix in CUSTOMER_DATA_PREFIXES:
            allowed = tuple(p for p in rules.FORBIDDEN_PREFIXES if p != prefix)
            with mock.patch.object(rules, "FORBIDDEN_PREFIXES", allowed):
                registry = CommandRegistry()
                registry.build(force=True)
                leaked = [s.path for s in registry.get_specs() if s.path.startswith(prefix)]
            self.assertGreater(len(leaked), 0, f"Thiếu {prefix} trong danh sách cấm thì phải thấy lệnh lọt vào chỉ mục.")

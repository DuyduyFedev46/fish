"""
Chỉ mục lệnh AI không được chứa route của việc gọi xác nhận đơn (P8b Lô 3, rủi ro R1, bất biến 9).

Hàng đợi gọi xác nhận trả tên, SĐT, địa chỉ khách. Route `/api/confirmation/` và tên cũ `/api/cskh/` đều phải nằm trong
`FORBIDDEN_PREFIXES` để registry bỏ qua. Route `/api/cskh/` đã gỡ ở P8b Lô 5 nhưng tiền tố GIỮ VĨNH VIỄN trong danh sách cấm
(phòng thủ nhiều lớp: ai thêm lại route tên cũ thì AI vẫn không thấy).
"""
from unittest import mock

from django.test import TestCase
from django.urls import get_resolver

from apps.ai.policy import rules
from apps.ai.policy.rules import FORBIDDEN_PREFIXES, is_url_forbidden
from apps.ai.registry.discovery import CommandRegistry, _clean_path, _collect_routes, get_registry

REMOVED_PREFIX = "/api/cskh/"  # tên cũ, route đã gỡ ở Lô 5; tiền tố vẫn bị cấm
LIVE_PREFIX = "/api/confirmation/"
CUSTOMER_DATA_PREFIXES = (REMOVED_PREFIX, LIVE_PREFIX)


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
        """Route xác nhận có thật trong URLconf (quét > 0), nhưng registry vẫn bỏ qua; tên cũ không còn route nào."""
        routes = []
        _collect_routes(get_resolver().url_patterns, prefix="", routes=routes)
        paths = [_clean_path(pattern) for pattern, _cb, _args in routes]
        hits = [p for p in paths if p.startswith(LIVE_PREFIX)]
        self.assertGreater(len(hits), 0, f"URLconf phải có route dưới {LIVE_PREFIX}")
        self.assertEqual([p for p in paths if p.startswith(REMOVED_PREFIX)], [], "route tên cũ đã gỡ ở Lô 5")

    def test_guard_is_what_keeps_the_routes_out_of_the_index(self):
        """Bỏ tiền tố khỏi danh sách cấm thì route xác nhận lọt vào chỉ mục: chứng minh test có răng."""
        allowed = tuple(p for p in rules.FORBIDDEN_PREFIXES if p != LIVE_PREFIX)
        with mock.patch.object(rules, "FORBIDDEN_PREFIXES", allowed):
            registry = CommandRegistry()
            registry.build(force=True)
            leaked = [s.path for s in registry.get_specs() if s.path.startswith(LIVE_PREFIX)]
        self.assertGreater(len(leaked), 0, f"Thiếu {LIVE_PREFIX} trong danh sách cấm thì phải thấy lệnh lọt vào chỉ mục.")

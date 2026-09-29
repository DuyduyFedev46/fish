"""
Kiểm tra an toàn: không đường tắt, không bypass quyền (CMS-01-AC4, §3.3 02b-tech-design).
"""
from pathlib import Path
from django.conf import settings
from django.test import SimpleTestCase
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.permissions import AllowAny

from apps.content.permissions import ContentPermissions


def iter_urls(patterns, prefix=""):
    for p in patterns:
        if isinstance(p, URLPattern):
            full_pattern = prefix + str(p.pattern)
            yield full_pattern, p.callback
        elif isinstance(p, URLResolver):
            yield from iter_urls(p.url_patterns, prefix + str(p.pattern))


class NoShortcutTests(SimpleTestCase):
    def test_cms_01_ac4_no_shortcut_in_routes(self):
        """
        CMS-01-AC4:
        - Route api/content/**: permission_classes chứa ContentPermissions, không AllowAny; action ghi có required_perms
        - Route api/public/content/**: http_method_names ⊆ {get, head, options}
        - Không pattern nào chứa content dưới api/internal/
        """
        resolver = get_resolver()
        all_routes = list(iter_urls(resolver.url_patterns))

        content_routes = []
        for path_pattern, callback in all_routes:
            clean_path = path_pattern.replace("^", "").lstrip("/")
            if "internal/" in clean_path and "content" in clean_path:
                self.fail(f"Phát hiện route content dưới internal/: {clean_path}")

            if clean_path.startswith("api/content/"):
                content_routes.append((clean_path, callback))
            elif clean_path.startswith("api/public/content/"):
                view_class = getattr(callback, "cls", None)
                if view_class:
                    allowed = set(m.lower() for m in getattr(view_class, "http_method_names", []))
                    safe_methods = {"get", "head", "options"}
                    self.assertTrue(
                        allowed.issubset(safe_methods),
                        f"Route public {clean_path} có method ghi không an toàn: {allowed - safe_methods}",
                    )

        self.assertTrue(len(content_routes) > 0, "Phải có ít nhất 1 route api/content/")

        for clean_path, callback in content_routes:
            view_class = getattr(callback, "cls", None)
            if not view_class:
                continue

            perm_classes = getattr(view_class, "permission_classes", [])
            self.assertTrue(
                any(issubclass(p, ContentPermissions) for p in perm_classes),
                f"Route {clean_path} thiếu ContentPermissions trong {perm_classes}",
            )
            self.assertNotIn(
                AllowAny,
                perm_classes,
                f"Route {clean_path} không được dùng AllowAny",
            )

            actions_dict = getattr(callback, "actions", {})
            for method, action_name in actions_dict.items():
                if method.lower() in ("post", "put", "patch", "delete"):
                    action_func = getattr(view_class, action_name, None)
                    if action_func and action_name not in ("create", "update", "partial_update", "destroy"):
                        func_kwargs = getattr(action_func, "kwargs", {})
                        required_perms = getattr(action_func, "required_perms", None) or func_kwargs.get("required_perms")
                        self.assertTrue(
                            bool(required_perms),
                            f"Custom action ghi {action_name} trên {clean_path} phải khai required_perms",
                        )

    def test_cms_01_ac4_no_service_token_or_custom_header_in_content_code(self):
        """Không view/service content nào đọc header bỏ qua quyền hoặc INTERNAL_SERVICE_TOKEN."""
        content_dir = Path(settings.BASE_DIR) / "apps" / "content"
        forbidden_strings = ["INTERNAL_SERVICE_TOKEN", "HTTP_X_"]

        for py_file in content_dir.glob("**/*.py"):
            # Bỏ qua thư mục tests
            if "tests" in py_file.parts:
                continue
            text = py_file.read_text(encoding="utf-8")
            for forbidden in forbidden_strings:
                self.assertNotIn(
                    forbidden,
                    text,
                    f"Tệp {py_file} chứa chuỗi nguy cơ tạo backdoor/đường tắt: {forbidden}",
                )

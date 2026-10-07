"""
D-3 (Duy chốt 08/10, câu 6) — người không thuộc nhóm nào và không phải superuser bị 403 `AUTH_NO_ROLE`
ở mọi API ERP, kể cả khi được gán quyền trực tiếp. Chừa: đăng nhập, me, logout, đổi mật khẩu và các view
`AllowAny` (Shop, public, internal). Superuser không nhóm vào như Chủ (câu 1).

Dùng token thật (như console), vì `force_authenticate` bỏ qua lớp xác thực. Chặn ở lớp xác thực
nên quét được mọi route, kể cả view tự khai `permission_classes`. Dữ liệu giả.
"""
import re

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.test import APIClient

from apps.accounts import roles
from apps.accounts.auth.authentication import MUST_CHANGE_PASSWORD_CODE, _is_public_view
from apps.accounts.models import StaffProfile
from apps.common.tests.fixtures import make_order_with_note, make_user
from apps.sales.models import SalesOrder

CODE = "AUTH_NO_ROLE"
ME = "/api/auth/me/"
CHANGE = "/api/auth/change-password/"
LOGOUT = "/api/auth/logout/"
LOGIN = "/api/auth/token/"
EXEMPT_PATHS = (ME, CHANGE, LOGOUT, LOGIN)
FAKE_PHONE = "0900000000"


def token_client(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


def iter_routes(patterns=None, prefix=""):
    """Sinh (path mẫu, view class) cho mọi route DRF."""
    patterns = get_resolver().url_patterns if patterns is None else patterns
    for pattern in patterns:
        text = prefix + str(pattern.pattern)
        if isinstance(pattern, URLResolver):
            yield from iter_routes(pattern.url_patterns, text)
        elif isinstance(pattern, URLPattern):
            view_cls = getattr(pattern.callback, "cls", None) or getattr(pattern.callback, "view_class", None)
            if view_cls is None or not hasattr(view_cls, "authentication_classes"):
                continue
            if "drf_format_suffix" in text:
                continue
            path = re.sub(r"<(?:\w+:)?\w+>", "1", text)
            path = re.sub(r"\(\?P<\w+>[^)]*\)", "1", path)
            path = re.sub(r"[\^$]", "", path).replace("\\.", ".")
            if "?" in path or "(" in path:
                continue
            if not path.startswith("/"):
                path = "/" + path
            if path.startswith("/api/"):
                yield path, view_cls


def is_exempt(view_cls):
    perms = getattr(view_cls, "permission_classes", [])
    return bool(getattr(view_cls, "allow_without_group", False)) or (
        bool(perms) and all(p is AllowAny for p in perms)
    )


class NoRoleGateTests(TestCase):
    def setUp(self):
        self.no_role = User.objects.create_user("no_role_fake", password="x")
        # Có quyền gán trực tiếp vẫn bị chặn (D-3).
        self.no_role.user_permissions.add(
            *Permission.objects.filter(codename__in=("view_salesorder", "view_refund", "view_deliverynote"))
        )
        self.client_no_role = token_client(self.no_role)

    def test_no_role_user_gets_403_auth_no_role_on_every_erp_route(self):
        gated = 0
        for path, view_cls in iter_routes():
            if is_exempt(view_cls):
                continue
            resp = self.client_no_role.get(path)
            with self.subTest(path=path):
                self.assertEqual(resp.status_code, 403, path)
                self.assertEqual(resp.json().get("code"), CODE, path)
                gated += 1
        self.assertGreater(gated, 40)  # chốt: quét thật sự phủ router

    def test_403_body_has_no_personal_data(self):
        body = self.client_no_role.get("/api/sales/orders/").content.decode()
        self.assertNotIn(FAKE_PHONE, body)
        self.assertEqual(set(self.client_no_role.get("/api/sales/orders/").json()), {"detail", "code"})

    def test_no_role_user_is_still_allowed_login_me_logout_change_password(self):
        me = self.client_no_role.get(ME)
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["home"], "no-role")
        # đổi mật khẩu: qua được cổng (sai mật khẩu cũ là 400, không phải 403)
        resp = self.client_no_role.post(CHANGE, {"old_password": "sai", "new_password": "Moi-mat-khau-2026"}, format="json")
        self.assertNotEqual(resp.status_code, 403)
        login = APIClient().post(LOGIN, {"username": "no_role_fake", "password": "x"}, format="json")
        self.assertEqual(login.status_code, 200)
        self.assertEqual(self.client_no_role.post(LOGOUT).status_code, 204)

    def test_exempt_paths_are_not_gated(self):
        for path, view_cls in iter_routes():
            if path in EXEMPT_PATHS:
                with self.subTest(path=path):
                    self.assertTrue(is_exempt(view_cls))

    def test_allow_any_views_are_not_gated_even_with_token_of_no_role_user(self):
        seen = 0
        for path, view_cls in iter_routes():
            if is_exempt(view_cls) and path not in EXEMPT_PATHS:
                resp = self.client_no_role.get(path)
                with self.subTest(path=path):
                    self.assertNotEqual(resp.json().get("code") if resp.status_code == 403 else None, CODE)
                seen += 1
        self.assertGreater(seen, 3)  # có Shop/public để kiểm

    def test_user_with_any_group_passes_the_gate(self):
        for role in (roles.OWNER, roles.MANAGER, roles.WAREHOUSE_STAFF, roles.DELIVERY_STAFF, roles.CUSTOMER_SERVICE):
            client = token_client(make_user(f"u_{role}", role))
            resp = client.get("/api/dashboard/summary/")
            with self.subTest(role=role):
                self.assertFalse(resp.status_code == 403 and resp.json().get("code") == CODE)

    def test_superuser_without_group_passes_the_gate(self):
        admin = User.objects.create_superuser("admin_fake", password="x")
        resp = token_client(admin).get("/api/sales/orders/")
        self.assertEqual(resp.status_code, 200)

    def test_group_removal_takes_effect_immediately(self):
        user = make_user("was_owner", roles.OWNER)
        client = token_client(user)
        self.assertEqual(client.get("/api/sales/orders/").status_code, 200)
        user.groups.clear()
        resp = client.get("/api/sales/orders/")
        self.assertEqual((resp.status_code, resp.json().get("code")), (403, CODE))

    def test_unauthenticated_is_still_401(self):
        self.assertEqual(APIClient().get("/api/sales/orders/").status_code, 401)

    def test_session_auth_no_role_user_gets_403_auth_no_role(self):
        client = APIClient()
        client.force_login(self.no_role)  # phiên (Session), không phải token
        resp = client.get("/api/sales/orders/")
        self.assertEqual((resp.status_code, resp.json().get("code")), (403, CODE))

    def test_no_role_user_with_temp_password_gets_must_change_password_first(self):
        StaffProfile.objects.update_or_create(user=self.no_role, defaults={"must_change_password": True})
        resp = self.client_no_role.get("/api/sales/orders/")
        self.assertEqual((resp.status_code, resp.json().get("code")), (403, MUST_CHANGE_PASSWORD_CODE))

    def test_no_role_user_cannot_post_cancel_and_order_is_unchanged(self):
        order, _customer, _note = make_order_with_note("DH-NOROLE", FAKE_PHONE)
        self.no_role.user_permissions.add(Permission.objects.get(codename="cancel_paid_order"))
        resp = self.client_no_role.post(
            f"/api/sales/orders/{order.pk}/cancel/", {"reason_code": "OTHER", "note": "x"}, format="json"
        )
        self.assertEqual((resp.status_code, resp.json().get("code")), (403, CODE))
        order.refresh_from_db()
        self.assertEqual(order.status, SalesOrder.Status.PROCESSING)


class NoViewOverridesGetPermissionsTests(TestCase):
    def test_no_api_view_overrides_get_permissions(self):
        """`_is_public_view` chỉ đọc `permission_classes` ở cấp class. View nào override `get_permissions`
        có thể mở công khai mà cổng không thấy → cấm; cần thì sửa `_is_public_view` cùng lúc."""
        from rest_framework.views import APIView

        offenders = sorted(
            {path for path, cls in iter_routes() if cls.get_permissions is not APIView.get_permissions}
        )
        self.assertEqual(offenders, [])
        self.assertTrue(_is_public_view(type("V", (), {"permission_classes": [AllowAny]})))

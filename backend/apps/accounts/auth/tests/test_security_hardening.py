"""
Đợt sửa bảo mật gấp 15/11 (không đổi nghiệp vụ): đăng nhập, token, đổi mật khẩu, Admin.

Mã: H-1 (Admin), B4 (kiểu username), B6 (khoá theo cặp), B8 (đổi mật khẩu), M-3 (hạn token).
"""
import datetime
import re

from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts import roles

PASSWORD = "Ca-ve-Dung-2026!"
LOGIN_URL = "/api/auth/token/"


def _make_user(username="kho_sec"):
    user = User.objects.create_user(username, password=PASSWORD)
    user.groups.add(Group.objects.get(name=roles.WAREHOUSE_STAFF))
    return user


class TokenExpiryTests(TestCase):
    """M-3/B12: token ERP có hạn AUTH_TOKEN_TTL_HOURS; đăng nhập lại cấp token mới."""

    def setUp(self):
        cache.clear()
        self.user = _make_user()

    def _age(self, token, hours):
        Token.objects.filter(pk=token.pk).update(created=timezone.now() - datetime.timedelta(hours=hours))

    def _me(self, key):
        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION=f"Token {key}")
        return api.get("/api/auth/me/")

    @override_settings(AUTH_TOKEN_TTL_HOURS=12)
    def test_token_older_than_ttl_is_401(self):
        token = Token.objects.create(user=self.user)
        self._age(token, 13)
        self.assertEqual(self._me(token.key).status_code, 401)

    @override_settings(AUTH_TOKEN_TTL_HOURS=12)
    def test_token_within_ttl_is_ok(self):
        token = Token.objects.create(user=self.user)
        self._age(token, 11)
        self.assertEqual(self._me(token.key).status_code, 200)

    @override_settings(AUTH_TOKEN_TTL_HOURS=12)
    def test_login_again_within_ttl_reuses_token(self):
        # máy thứ hai đăng nhập cùng tài khoản không làm văng máy thứ nhất; hạn vẫn tính từ lúc cấp lần đầu
        api = APIClient()
        first = api.post(LOGIN_URL, {"username": "kho_sec", "password": PASSWORD}, format="json").json()["token"]
        second = api.post(LOGIN_URL, {"username": "kho_sec", "password": PASSWORD}, format="json").json()["token"]
        self.assertEqual(first, second)
        self.assertEqual(self._me(first).status_code, 200)
        self.assertEqual(Token.objects.filter(user=self.user).count(), 1)
        self._age(Token.objects.get(key=first), 13)
        self.assertEqual(self._me(first).status_code, 401)

    @override_settings(AUTH_TOKEN_TTL_HOURS=12)
    def test_login_replaces_expired_token(self):
        old = Token.objects.create(user=self.user)
        self._age(old, 100)
        key = APIClient().post(LOGIN_URL, {"username": "kho_sec", "password": PASSWORD}, format="json").json()["token"]
        self.assertNotEqual(key, old.key)
        self.assertEqual(self._me(key).status_code, 200)

    def test_logout_deletes_token(self):
        key = APIClient().post(LOGIN_URL, {"username": "kho_sec", "password": PASSWORD}, format="json").json()["token"]
        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION=f"Token {key}")
        self.assertEqual(api.post("/api/auth/logout/").status_code, 204)
        self.assertFalse(Token.objects.filter(key=key).exists())
        self.assertEqual(self._me(key).status_code, 401)


@override_settings(CAVEVE_THROTTLE_RATES={"login_ip": "1000/min", "login_user": "1000/hour"})
class LoginInputTests(TestCase):
    """B4: username/password không phải chuỗi -> 400, không 500."""

    def setUp(self):
        cache.clear()
        _make_user()

    def test_non_string_username_is_400(self):
        for bad in (123, {"a": 1}, ["x"], None, True, 1.5):
            with self.subTest(username=bad):
                r = APIClient().post(LOGIN_URL, {"username": bad, "password": "x"}, format="json")
                self.assertEqual(r.status_code, 400, r.content)

    def test_non_string_password_is_400(self):
        for bad in (123, {"a": 1}, ["x"], None):
            with self.subTest(password=bad):
                r = APIClient().post(LOGIN_URL, {"username": "kho_sec", "password": bad}, format="json")
                self.assertEqual(r.status_code, 400, r.content)

    def test_non_dict_body_is_400(self):
        r = APIClient().post(LOGIN_URL, ["x"], format="json")
        self.assertEqual(r.status_code, 400, r.content)


class LoginThrottleKeyTests(TestCase):
    """B6/L-3: khoá theo cặp (username, IP); người ngoài không khoá được Chủ từ IP khác."""

    def setUp(self):
        cache.clear()
        _make_user("chu_sec")

    def _login(self, password, ip):
        return APIClient().post(
            LOGIN_URL, {"username": "chu_sec", "password": password}, format="json", REMOTE_ADDR=ip
        )

    @override_settings(CAVEVE_THROTTLE_RATES={"login_ip": "100/min", "login_user": "3/hour"})
    def test_attacker_ip_cannot_lock_owner_on_other_ip(self):
        for _ in range(6):
            self._login("sai", "10.9.9.9")
        r = self._login(PASSWORD, "10.1.1.1")  # Chủ đăng nhập từ IP khác
        self.assertEqual(r.status_code, 200, r.content)

    @override_settings(CAVEVE_THROTTLE_RATES={"login_ip": "100/min", "login_user": "3/hour"})
    def test_same_ip_same_username_is_throttled(self):
        codes = [self._login("sai", "10.9.9.9").status_code for _ in range(5)]
        self.assertEqual(codes[:3], [400, 400, 400])
        self.assertEqual(codes[3], 429)

    @override_settings(CAVEVE_THROTTLE_RATES={"login_ip": "2/min", "login_user": "100/hour"})
    def test_ip_throttle_still_applies(self):
        codes = [self._login("sai", "10.9.9.9").status_code for _ in range(3)]
        self.assertEqual(codes[2], 429)

    def test_default_rates_have_pair_limit(self):
        from apps.common.tests.throttle_defaults import default_throttle_rates
        rates = default_throttle_rates()
        self.assertTrue(rates["login_user"])
        self.assertTrue(rates["change_password"])


class ChangePasswordThrottleTests(TestCase):
    """B8: đổi mật khẩu bị throttle theo người dùng, chặn dò old_password."""

    def setUp(self):
        cache.clear()
        self.user = _make_user("doi_mk")
        self.key = APIClient().post(
            LOGIN_URL, {"username": "doi_mk", "password": PASSWORD}, format="json"
        ).json()["token"]

    def _change(self, old):
        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION=f"Token {self.key}")
        return api.post("/api/auth/change-password/", {"old_password": old, "new_password": "Mat-khau-Moi-2026!"}, format="json")

    @override_settings(CAVEVE_THROTTLE_RATES={"change_password": "3/hour"})
    def test_old_password_guessing_is_throttled(self):
        codes = [self._change(f"sai{i}").status_code for i in range(3)]
        self.assertEqual(codes, [400, 400, 400])
        self.assertEqual(self._change(PASSWORD).status_code, 429)


def _csrf(html):
    return re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html).group(1)


class AdminLoginThrottleTests(TestCase):
    """H-1: /admin/login/ có giới hạn tần suất như /api/auth/token/."""

    def setUp(self):
        cache.clear()
        User.objects.create_superuser("root_sec", password=PASSWORD)

    def _post(self, client, password, ip="10.2.2.2"):
        token = _csrf(client.get("/admin/login/", REMOTE_ADDR=ip).content.decode())
        return client.post(
            "/admin/login/",
            {"username": "root_sec", "password": password, "csrfmiddlewaretoken": token,
             "next": "/admin/"},
            REMOTE_ADDR=ip,
        )

    @override_settings(CAVEVE_THROTTLE_RATES={"login_ip": "100/min", "login_user": "3/hour"})
    def test_wrong_password_flood_gets_429_even_with_right_password(self):
        c = Client(enforce_csrf_checks=True)
        codes = [self._post(c, f"sai{i}").status_code for i in range(3)]
        self.assertEqual(codes, [200, 200, 200])
        self.assertEqual(self._post(c, PASSWORD).status_code, 429)

    @override_settings(CAVEVE_THROTTLE_RATES={"login_ip": "100/min", "login_user": "3/hour"})
    def test_other_ip_can_still_log_in(self):
        c = Client(enforce_csrf_checks=True)
        for i in range(5):
            self._post(c, f"sai{i}", ip="10.9.9.9")
        self.assertEqual(self._post(Client(enforce_csrf_checks=True), PASSWORD, ip="10.1.1.1").status_code, 302)

    @override_settings(CAVEVE_THROTTLE_RATES={"login_ip": "2/min", "login_user": "100/hour"})
    def test_ip_limit_applies_to_admin_login(self):
        c = Client(enforce_csrf_checks=True)
        codes = [self._post(c, f"sai{i}").status_code for i in range(3)]
        self.assertEqual(codes[2], 429)

"""Dựng dữ liệu dùng chung cho test S41/S42 (quản lý nhân viên)."""
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.accounts.models import AuditLog, StaffProfile
from apps.common.tests.fixtures import client_for, make_user  # noqa: F401 (re-export)

LIST_URL = "/api/staff/"
ME_URL = "/api/auth/me/"
TOKEN_URL = "/api/auth/token/"
UNAUTHORIZED = {"detail": "Thông tin xác thực không hợp lệ."}
STRONG_PASSWORD = "CaVe-Kho-2026!"


def detail_url(user, suffix=""):
    return f"{LIST_URL}{user.pk}/{suffix}"


def staff_user(username, *groups, phone="0909000000", display_name="", perms=()):
    user = make_user(username, *groups, perms=perms)
    StaffProfile.objects.create(user=user, phone=phone, display_name=display_name)
    return User.objects.get(pk=user.pk)


def token_client(user):
    """Client giả lập một máy đã đăng nhập bằng token (như console)."""
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


def login(username, password):
    """POST /api/auth/token/ → (status, token|None)."""
    resp = APIClient().post(TOKEN_URL, {"username": username, "password": password}, format="json")
    return resp.status_code, resp.json().get("token")


def group_names(user):
    return sorted(User.objects.get(pk=user.pk).groups.values_list("name", flat=True))


def audits(action):
    return AuditLog.objects.filter(action=action)

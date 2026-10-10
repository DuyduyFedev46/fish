"""Dựng dữ liệu dùng chung cho test ma trận phân quyền (B4). Dữ liệu toàn bộ là giả."""
from django.contrib.auth.models import Group, User

from apps.accounts import roles
from apps.accounts.staff.tests.helpers import staff_user, token_client  # noqa: F401 (re-export)

LIST_URL = "/api/staff/groups/"


def detail_url(code):
    return f"{LIST_URL}{code}/"


def put_url(code):
    return f"{LIST_URL}{code}/capabilities/"


def group_perms(code):
    """Tập `app_label.codename` hiện có của Group, đọc thẳng từ DB."""
    group = Group.objects.get(name=code)
    return {f"{p.content_type.app_label}.{p.codename}" for p in group.permissions.select_related("content_type")}


def make_staff(username, *groups, display_name=""):
    return staff_user(username, *groups, display_name=display_name or username.title())


def reload(user):
    return User.objects.get(pk=user.pk)  # bỏ cache quyền của instance


ALL_CODES = list(roles.ALL_ROLES)


def put_caps(client, code, changes=None, **body):
    """PUT `/capabilities/` kèm `version` lấy từ GET gần nhất của nhóm (PV-10, 02b §2.3). `body` thêm vào thân (vd `scopes`)."""
    if "version" not in body:
        got = client.get(detail_url(code))
        body["version"] = got.json().get("version", "1") if got.status_code == 200 else "1"
    if changes is not None:
        body["capabilities"] = changes
    return client.put(put_url(code), body, format="json")

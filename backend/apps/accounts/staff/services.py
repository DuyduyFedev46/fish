"""
Nghiệp vụ quản lý nhân viên (S41, S42 · UC-23) — BR-PQ-01/02/03/08/09, BR-PQ-17, BR-PQ-18, BR-GH-08.

- Tài khoản = `User` + `StaffProfile` (SĐT bắt buộc). Không bao giờ xoá User (BR-PQ-02).
- BR-PQ-17 (chống tự nâng quyền): không ai tự đổi nhóm / tự cho nghỉ / tự đặt lại mật khẩu của
  mình qua đây; chỉ người thuộc `chu` hoặc superuser mới gán/bỏ nhóm `chu` và thao tác trên tài
  khoản thuộc `chu`; chỉ superuser thao tác trên tài khoản superuser.
- BR-PQ-18: luôn còn ≥ 1 tài khoản đang làm (`is_active`) thuộc `chu`.
- Cho nghỉ / đặt lại mật khẩu thu hồi token ngay (C8: một token mỗi người → mọi máy văng).
- Mọi thay đổi ghi AuditLog; nội dung log không bao giờ chứa mật khẩu.
"""
from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from rest_framework.authtoken.models import Token

from apps.accounts.auth.services import ROLE_ORDER, sorted_groups
from apps.accounts.models import StaffProfile
from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError

CHU = "chu"
INPUT_CODE = "BR-PQ-08"
SELF_CODE = "BR-PQ-17"
LAST_CHU_CODE = "BR-PQ-18"
DELIVERING_CODE = "BR-GH-08"
USERNAME_TAKEN = "Tên đăng nhập đã tồn tại."


class StaffPermissionError(BusinessError):
    """Vi phạm BR-PQ-17 do người thao tác thiếu thẩm quyền → API trả 403 (không phải 400)."""

    http_status = 403

    def __init__(self, message):
        super().__init__(message, code=SELF_CODE)


# --- truy vấn / tiện ích ---------------------------------------------------------


def group_names(user):
    return sorted_groups(user.groups.values_list("name", flat=True))


def is_chu(user) -> bool:
    return user.groups.filter(name=CHU).exists()


def actor_is_owner(actor) -> bool:
    """Chủ hoặc superuser — người được đụng nhóm `chu` / tài khoản Chủ (BR-PQ-17)."""
    return bool(actor.is_superuser or is_chu(actor))


def active_chu_ids():
    return set(User.objects.filter(is_active=True, groups__name=CHU).values_list("pk", flat=True))


def _profile(user):
    return StaffProfile.objects.filter(user=user).first()


def _check_can_touch(actor, target):
    """BR-PQ-17: tài khoản Chủ chỉ Chủ/superuser thao tác; tài khoản superuser chỉ superuser."""
    if target.is_superuser and not actor.is_superuser:
        raise StaffPermissionError("Chỉ superuser mới thao tác trên tài khoản superuser.")
    if is_chu(target) and not actor_is_owner(actor):
        raise StaffPermissionError("Chỉ Chủ mới thao tác trên tài khoản Chủ.")


def _resolve_groups(names):
    if not isinstance(names, (list, tuple)) or not all(isinstance(n, str) for n in names):
        raise BusinessError("Danh sách nhóm phải là mảng tên nhóm.", code=INPUT_CODE)
    names = list(dict.fromkeys(names))
    found = {g.name: g for g in Group.objects.filter(name__in=names)}
    unknown = [n for n in names if n not in found]
    if unknown:
        raise BusinessError(
            f"Nhóm không tồn tại: {', '.join(unknown)}. Chỉ dùng: {', '.join(ROLE_ORDER)}.",
            code=INPUT_CODE,
        )
    return [found[n] for n in names]


def _clean_text(value, *, field, max_length):
    if value is None:
        return ""
    if not isinstance(value, str):
        raise BusinessError(f"Trường {field} phải là chuỗi.", code=INPUT_CODE)
    value = value.strip()
    if len(value) > max_length:
        raise BusinessError(f"Trường {field} dài quá {max_length} ký tự.", code=INPUT_CODE)
    return value


def _clean_phone(phone):
    phone = _clean_text(phone, field="phone", max_length=20)
    if not phone:
        raise BusinessError("Số điện thoại là bắt buộc.", code=INPUT_CODE)
    return phone


def _check_password(password, user):
    if not isinstance(password, str) or not password:
        raise BusinessError("Mật khẩu là bắt buộc.", code=INPUT_CODE)
    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        raise BusinessError(" ".join(exc.messages), code=INPUT_CODE) from None


def _lock_target_and_chus(user):
    """
    Khoá MỘT lần, theo thứ tự cố định (pk tăng dần): người bị thao tác + mọi Chủ đang làm.

    Trước đây khoá người đích trước rồi mới khoá các Chủ → hai Chủ cho nghỉ nhau cùng lúc
    khoá chéo nhau (deadlock, QA Q1). Nay mọi thao tác đụng Chủ đều xin khoá cùng thứ tự nên
    request sau chờ request trước xong (BR-PQ-18 kiểm trên dữ liệu đã khoá).
    Trả (danh sách pk đã khoá, bản User đích mới đọc).
    """
    ids = sorted(active_chu_ids() | {user.pk})
    locked = list(User.objects.select_for_update().filter(pk__in=ids).order_by("pk"))
    target = next(u for u in locked if u.pk == user.pk)
    return [u.pk for u in locked], target


def _username_taken(username) -> bool:
    return User.objects.filter(username__iexact=username).exists()


def _revoke_tokens(user) -> int:
    count, _ = Token.objects.filter(user=user).delete()
    return count


# --- S41 -----------------------------------------------------------------------------


@transaction.atomic
def create_staff(*, actor, username, password, phone, display_name="", groups=()):
    username = _clean_text(username, field="username", max_length=150)
    if not username:
        raise BusinessError("Tên đăng nhập là bắt buộc.", code=INPUT_CODE)
    try:
        UnicodeUsernameValidator()(username)
    except ValidationError:
        raise BusinessError(
            "Tên đăng nhập chỉ gồm chữ, số và @ . + - _ (không dấu cách).", code=INPUT_CODE
        ) from None
    if _username_taken(username):
        raise BusinessError(USERNAME_TAKEN, code=INPUT_CODE)
    phone = _clean_phone(phone)
    display_name = _clean_text(display_name, field="display_name", max_length=150)
    group_objs = _resolve_groups(groups)
    if any(g.name == CHU for g in group_objs) and not actor_is_owner(actor):
        raise StaffPermissionError("Chỉ Chủ mới gán hoặc bỏ nhóm Chủ.")
    _check_password(password, User(username=username))

    try:
        # Savepoint: hai request cùng username vượt qua bước kiểm trên cùng lúc → request thua
        # gặp unique của DB. Trả 400 BR-PQ-08 thay vì 500 (QA Q1); không tạo gì thêm.
        with transaction.atomic():
            user = User.objects.create_user(username=username, password=password)
    except IntegrityError:
        raise BusinessError(USERNAME_TAKEN, code=INPUT_CODE) from None
    user.groups.set(group_objs)
    # BR-PQ-19: mật khẩu do Chủ đặt là mật khẩu tạm → người đó phải tự đổi lần đầu.
    StaffProfile.objects.create(
        user=user, phone=phone, display_name=display_name, must_change_password=True
    )
    record_audit(
        "staff_create", actor=actor, obj=user,
        changes={
            "username": {"from": None, "to": username},
            "display_name": {"from": None, "to": display_name},
            "phone": {"from": None, "to": phone},
            "groups": {"from": [], "to": group_names(user)},
        },
    )
    return user


@transaction.atomic
def update_profile(*, actor, user, **fields):
    """Sửa hồ sơ (display_name, phone). Chưa có StaffProfile thì tạo."""
    _check_can_touch(actor, user)
    profile = _profile(user)
    new = {}
    if "display_name" in fields:
        new["display_name"] = _clean_text(
            fields["display_name"], field="display_name", max_length=150
        )
    if "phone" in fields:
        new["phone"] = _clean_phone(fields["phone"])
    if profile is None:
        if "phone" not in new:
            raise BusinessError("Số điện thoại là bắt buộc.", code=INPUT_CODE)
        profile = StaffProfile(user=user, phone="", display_name="")
        old = {"display_name": None, "phone": None}
    else:
        old = {"display_name": profile.display_name, "phone": profile.phone}
    changes = {k: {"from": old[k], "to": v} for k, v in new.items() if old[k] != v}
    for key, value in new.items():
        setattr(profile, key, value)
    profile.save()
    if changes:
        record_audit("staff_update", actor=actor, obj=user, changes=changes)
    return user


@transaction.atomic
def set_groups(*, actor, user, groups):
    """Thay toàn bộ tập nhóm (PUT). Trả (groups, added, removed) theo thứ tự vai."""
    _locked, user = _lock_target_and_chus(user)
    if user.pk == actor.pk:
        raise BusinessError("Không thể tự đổi nhóm của chính mình.", code=SELF_CODE)
    group_objs = _resolve_groups(groups)
    before = group_names(user)
    after = sorted_groups(g.name for g in group_objs)
    added = [g for g in after if g not in before]
    removed = [g for g in before if g not in after]
    if not actor_is_owner(actor) and CHU in added + removed:
        raise StaffPermissionError("Chỉ Chủ mới gán hoặc bỏ nhóm Chủ.")
    _check_can_touch(actor, user)
    if CHU in removed and user.is_active:
        if not (active_chu_ids() - {user.pk}):
            raise BusinessError("Phải còn ít nhất một Chủ đang làm.", code=LAST_CHU_CODE)
    if added or removed:
        user.groups.set(group_objs)
        record_audit(
            "staff_groups_change", actor=actor, obj=user,
            changes={"groups": {"from": before, "to": after}},
        )
    return after, added, removed


# --- S42 -----------------------------------------------------------------------------


def _set_profile_status(user, status):
    StaffProfile.objects.filter(user=user).update(status=status)


@transaction.atomic
def deactivate(*, actor, user):
    """Cho nghỉ: is_active=False + xoá token (mọi máy 401 ngay). Không xoá tài khoản."""
    from apps.delivery.models import DeliveryNote

    _locked, user = _lock_target_and_chus(user)
    if user.pk == actor.pk:
        raise BusinessError("Không thể tự cho nghỉ chính mình.", code=SELF_CODE)
    _check_can_touch(actor, user)
    if not user.is_active:
        raise BusinessError("Tài khoản này đã nghỉ.", code="BR-PQ-01")
    if is_chu(user):
        if not (active_chu_ids() - {user.pk}):
            raise BusinessError("Không thể cho nghỉ Chủ cuối cùng.", code=LAST_CHU_CODE)
    delivering = list(
        DeliveryNote.objects.filter(assigned_to=user, status=DeliveryNote.Status.DELIVERING)
        .order_by("code").values_list("code", flat=True)
    )
    if delivering:
        raise BusinessError(
            f"Còn {len(delivering)} phiếu Đang giao ({', '.join(delivering)}) — "
            "xử lý trước khi cho nghỉ.",
            code=DELIVERING_CODE,
        )
    user.is_active = False
    user.save(update_fields=["is_active"])
    _set_profile_status(user, StaffProfile.Status.INACTIVE)
    revoked = _revoke_tokens(user)
    record_audit(
        "staff_deactivate", actor=actor, obj=user,
        changes={"is_active": {"from": True, "to": False}},
        note=f"Thu hồi {revoked} token đăng nhập.",
    )
    return user


@transaction.atomic
def reactivate(*, actor, user):
    """Cho làm lại: is_active=True; đăng nhập lại bằng mật khẩu cũ (không cấp token sẵn)."""
    user = User.objects.select_for_update().get(pk=user.pk)
    _check_can_touch(actor, user)
    if user.is_active:
        raise BusinessError("Tài khoản này đang làm.", code="BR-PQ-01")
    user.is_active = True
    user.save(update_fields=["is_active"])
    _set_profile_status(user, StaffProfile.Status.ACTIVE)
    record_audit(
        "staff_reactivate", actor=actor, obj=user,
        changes={"is_active": {"from": False, "to": True}},
    )
    return user


@transaction.atomic
def reset_password(*, actor, user, new_password):
    """Chủ đặt lại mật khẩu cho người khác; thu token cũ. Tự đổi của mình → S46 (cần mật khẩu cũ)."""
    user = User.objects.select_for_update().get(pk=user.pk)
    if user.pk == actor.pk:
        raise BusinessError(
            "Không tự đặt lại mật khẩu của mình ở đây — dùng Đổi mật khẩu.", code=SELF_CODE
        )
    _check_can_touch(actor, user)
    _check_password(new_password, user)
    user.set_password(new_password)
    user.save(update_fields=["password"])
    # BR-PQ-19: mật khẩu Chủ đặt là tạm → bật lại cờ (tài khoản chưa có hồ sơ thì không có cờ).
    StaffProfile.objects.filter(user=user).update(must_change_password=True)
    revoked = _revoke_tokens(user)
    record_audit(
        "staff_password_reset", actor=actor, obj=user,
        note=f"Đặt lại mật khẩu; thu hồi {revoked} token đăng nhập.",
    )
    return user


# --- hiển thị ------------------------------------------------------------------------


def available_actions(*, actor, user, active_chus) -> list:
    """Nút console được hiện cho `actor` trên dòng `user` (backend vẫn chặn lại khi gọi)."""
    user_groups = {g.name for g in user.groups.all()}
    if user.is_superuser and not actor.is_superuser:
        return []
    if CHU in user_groups and not actor_is_owner(actor):
        return []
    if user.pk == actor.pk:
        return ["edit"]
    if not user.is_active:
        return ["edit", "reactivate"]
    actions = ["edit", "set_groups", "reset_password"]
    if not (CHU in user_groups and not (active_chus - {user.pk})):
        actions.append("deactivate")
    return actions

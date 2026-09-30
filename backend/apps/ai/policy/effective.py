"""
Hàm tính mức hiệu lực effective_level(user, spec) (02b §4.1, DW-07, DW-12, DW-13).
Dùng chung cho chỉ mục, call, guidance và màn cấu hình.
"""
from django.conf import settings
from django.test import RequestFactory

from apps.ai import command_groups


LEVEL_ORDER = {"OFF": 0, "C": 1, "B": 2, "A": 3}
_rf = RequestFactory()


def min_level(*levels: str) -> str:
    valid = [lvl for lvl in levels if lvl in LEVEL_ORDER]
    if not valid:
        return "OFF"
    return min(valid, key=lambda l: LEVEL_ORDER[l])


def effective_level(user, spec, *, config_version=None, policy_version=None) -> str:
    """
    Tính mức tự chủ hiệu lực của user đối với command spec.
    Trả về: "OFF" | "C" | "B" | "A"
    """
    # 1. AI tắt toàn cục
    if not getattr(settings, "AI_ENABLED", False):
        return "OFF"

    # 2. User phải được xác thực
    if not (user and user.is_authenticated):
        return "OFF"

    # 3. Lệnh bị cấm tất định
    if getattr(spec, "is_forbidden", False):
        return "OFF"

    # 4. Kiểm tra quyền Tầng 1 (permission_classes của View)
    view_cls = getattr(spec, "view_cls", None)
    if view_cls:
        method = getattr(spec, "method", "GET").upper()
        path = getattr(spec, "path", "/")
        req_func = getattr(_rf, method.lower(), _rf.get)
        fake_req = req_func(path)
        fake_req.user = user

        try:
            view_inst = view_cls()
            action_name = getattr(spec, "action", None) or "get"
            view_inst.action = action_name
            view_inst.request = fake_req
            view_inst.args = ()
            view_inst.kwargs = {}
            view_inst.format_kwarg = None

            method_name = method.lower()
            if not hasattr(view_inst, method_name):
                setattr(view_inst, method_name, getattr(view_inst, action_name, lambda *a, **k: None))

            for perm_cls in getattr(view_cls, "permission_classes", ()):
                perm = perm_cls()
                if not perm.has_permission(fake_req, view_inst):
                    return "OFF"
        except Exception:
            return "OFF"

    # 5. Kiểm tra quyền Tầng 2 (required_perms)
    required_perms = getattr(spec, "required_perms", ())
    if required_perms:
        for p in required_perms:
            if not user.has_perm(p):
                return "OFF"

    # 6. Đọc chính sách Chủ (AiPolicyVersion)
    global_mode = "on"
    red_zone_open = {}
    caps = {}
    try:
        from apps.ai.models.policy import AiPolicyVersion
        if policy_version is not None:
            policy = policy_version
        else:
            policy = AiPolicyVersion.objects.order_by("-version").first()
        if policy:
            global_mode = policy.global_mode
            red_zone_open = policy.red_zone_open or {}
            caps = policy.caps or {}
    except Exception:
        pass

    # Nếu Chủ tắt khẩn toàn cục (DW-13-AC2):
    if global_mode == "off":
        return "OFF"

    # 7. Đọc cấu hình người dùng (AiConfigVersion)
    killed = False
    overrides = {}
    group_levels = {}
    try:
        from apps.ai.models.config import AiConfigVersion
        if config_version is not None:
            config = config_version
        else:
            config = AiConfigVersion.objects.filter(user=user).order_by("-version").first()
        if config:
            killed = config.killed
            overrides = config.overrides or {}
            group_levels = config.group_levels or {}
    except Exception:
        pass

    spec_id = getattr(spec, "id", "")
    spec_group = getattr(spec, "group", command_groups.PURCHASING)
    is_read = (getattr(spec, "kind", "read") == "read")

    # Xác định mức cấu hình của user
    if spec_id in overrides:
        user_level = overrides[spec_id]
    else:
        if is_read:
            user_level = group_levels.get(spec_group, {}).get("read", "A")
        else:
            user_level = group_levels.get(spec_group, {}).get("write", "C")

    if user_level == "OFF":
        return "OFF"

    # Lệnh đọc:
    if is_read:
        return "A" if user_level == "A" else "OFF"

    # Lệnh ghi:
    # 7.1 Trần môi trường (mặc định C)
    env_max = getattr(settings, "AI_WRITE_LEVELS_ALLOWED", "C")

    # 7.2 Trần spec
    if getattr(spec, "red_zone", False):
        # Kiểm tra xem quyền có trong red_zone_open của policy không
        # Nếu chưa mở -> trần C (DW-12-AC7, DW-24)
        is_open = False
        for p in required_perms:
            if red_zone_open.get(p, False):
                is_open = True
                break
        spec_cap = getattr(spec, "max_level", "B") if is_open else "C"
    elif getattr(spec, "force_c", False):
        spec_cap = "C"
    else:
        spec_cap = getattr(spec, "max_level", "") or "C"

    # 7.3 Trần từ policy Chủ:
    if global_mode == "c_only":
        policy_cap = "C"
    else:
        cmd_cap = caps.get(spec_id, {}).get("max_level")
        policy_cap = cmd_cap if cmd_cap else "A"

    # 7.4 Tắt AI của tôi (killed=true):
    # V-DW4: lệnh ghi rơi về C, lệnh đọc vẫn chạy
    if killed:
        user_level = min_level(user_level, "C")

    return min_level(user_level, spec_cap, env_max, policy_cap)

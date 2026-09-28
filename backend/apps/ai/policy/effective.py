"""
Hàm tính mức hiệu lực effective_level(user, spec) (02b §4.1, DW-07).
Dùng chung cho chỉ mục, call, guidance và màn cấu hình.
"""
from django.conf import settings
from django.test import RequestFactory


LEVEL_ORDER = {"OFF": 0, "C": 1, "B": 2, "A": 3}
_rf = RequestFactory()


def min_level(*levels: str) -> str:
    valid = [lvl for lvl in levels if lvl in LEVEL_ORDER]
    if not valid:
        return "OFF"
    return min(valid, key=lambda l: LEVEL_ORDER[l])


def effective_level(user, spec) -> str:
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

    # 6. Lệnh đọc: trả về A
    if getattr(spec, "kind", "read") == "read":
        return "A"

    # 7. Lệnh ghi:
    # Lấy trần từ env (mặc định "C")
    env_max = getattr(settings, "AI_WRITE_LEVELS_ALLOWED", "C")

    # Trần của spec:
    # Nếu thuộc red_zone hoặc trần C ép -> tối đa C
    if getattr(spec, "red_zone", False) or getattr(spec, "force_c", False):
        spec_cap = "C"
    else:
        spec_cap = getattr(spec, "max_level", "") or "C"

    # Mức hiệu lực cho ghi = min(spec_cap, env_max)
    return min_level(spec_cap, env_max)

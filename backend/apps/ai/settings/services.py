"""
Service xử lý nghiệp vụ cấu hình AI của tôi (DW-12, 02b §6.5).
"""
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.test import RequestFactory

from apps.ai.models.config import AiConfigVersion
from apps.ai.models.policy import AiPolicyVersion
from apps.ai import command_groups
from apps.ai.registry import get_registry, legacy_ids
from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError


_rf = RequestFactory()


def get_cap_for_command(caps: dict, cmd_id: str) -> dict | None:
    if not caps or not isinstance(caps, dict):
        return None
    # R5: trần lưu theo khoá cũ (phiên bản đã ghim) vẫn là trần của lệnh đã đổi id.
    caps = legacy_ids.normalize_command_keys(caps)
    cmd_id = legacy_ids.normalize_command_id(cmd_id)
    if cmd_id in caps and isinstance(caps[cmd_id], dict):
        return caps[cmd_id]
    alias = cmd_id.split(".")[-1]
    if alias in caps and isinstance(caps[alias], dict):
        return caps[alias]
    for k, v in caps.items():
        if isinstance(v, dict) and (k == cmd_id or k.endswith(f".{cmd_id}") or cmd_id.endswith(f".{k}")):
            return v
    return None


def user_has_spec_permission(user, spec) -> bool:
    """Kiểm tra quyền Tầng 1 và Tầng 2 của user đối với command spec."""
    if not (user and user.is_authenticated):
        return False
    if getattr(spec, "is_forbidden", False):
        return False

    # Tầng 2
    required_perms = getattr(spec, "required_perms", ())
    for p in required_perms:
        if not user.has_perm(p):
            return False

    # Tầng 1
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
                    return False
        except Exception:
            return False

    return True


def get_user_config_data(user) -> dict:
    """Lấy dữ liệu cấu hình AI của tôi theo contract 02b §6.5."""
    ai_enabled = getattr(settings, "AI_ENABLED", False)

    policy = AiPolicyVersion.objects.order_by("-version").first()
    global_mode = policy.global_mode if policy else "on"
    red_zone_open = policy.red_zone_open if policy else {}

    latest_config = AiConfigVersion.objects.filter(user=user).order_by("-version").first()
    version = latest_config.version if latest_config else 0
    killed = latest_config.killed if latest_config else False
    updated_at = latest_config.created_at.isoformat() if latest_config else None
    group_levels = legacy_ids.normalize_group_levels(latest_config.group_levels) if latest_config else {}
    overrides = legacy_ids.normalize_command_keys(latest_config.overrides) if latest_config else {}
    limits = legacy_ids.normalize_command_keys(latest_config.limits) if latest_config else {}

    env_write_max = getattr(settings, "AI_WRITE_LEVELS_ALLOWED", "C")
    write_choices = ["OFF", "C"] if env_write_max == "C" else ["OFF", "C", "B"]

    group_definitions = [
        (command_groups.PURCHASING, "Thu mua"),
        (command_groups.SALES, "Bán hàng"),
        (command_groups.CUSTOMER_SERVICE, "CSKH"),
    ]

    registry = get_registry()
    all_specs = registry.get_specs()

    groups_data = []
    for grp_key, grp_label in group_definitions:
        grp_cfg = group_levels.get(grp_key, {})
        default_read = grp_cfg.get("read", "A")
        default_write = grp_cfg.get("write", "C")

        grp_commands = []
        for spec in all_specs:
            if spec.group != grp_key:
                continue
            if not user_has_spec_permission(user, spec):
                continue

            is_read = (spec.kind == "read")
            if is_read:
                choices = ["OFF", "A"]
                max_level = "A"
                red_zone = False
                locked_reason = None
                cmd_limits = None
                if spec.id in overrides:
                    level = overrides[spec.id]
                    source = "override"
                elif grp_key in group_levels and "read" in grp_cfg:
                    level = default_read
                    source = "group"
                else:
                    level = "A"
                    source = "default"
            else:
                choices = list(write_choices)
                max_level = getattr(spec, "max_level", "C")
                red_zone = bool(getattr(spec, "red_zone", False))
                locked_reason = None
                if red_zone:
                    is_rz_open = any(
                        red_zone_open.get(p, False)
                        for p in getattr(spec, "required_perms", ())
                    )
                    if is_rz_open:
                        locked_reason = None
                        choices = list(write_choices)
                        max_level = getattr(spec, "max_level", "B") or "B"
                    else:
                        locked_reason = {"code": "BR-AI-18", "text": "Chủ chưa mở vùng đỏ cho lệnh này"}
                        choices = ["OFF", "C"]
                        max_level = "C"
                elif getattr(spec, "undo_missing", False):
                    locked_reason = {"code": "AI_UNDO_MISSING", "text": "Chưa có nghiệp vụ huỷ chứng từ"}

                cmd_limits = limits.get(spec.id, None)
                if spec.id in overrides:
                    level = overrides[spec.id]
                    source = "override"
                elif grp_key in group_levels and "write" in grp_cfg:
                    level = default_write
                    source = "group"
                else:
                    level = "C"
                    source = "default"

            grp_commands.append({
                "id": spec.id,
                "title": spec.title,
                "kind": spec.kind,
                "level": level,
                "source": source,
                "choices": choices,
                "max_level": max_level,
                "locked_reason": locked_reason,
                "red_zone": red_zone,
                "limits": cmd_limits,
                "supports_limits": bool(getattr(spec, "limits", None)),
            })

        groups_data.append({
            "group": grp_key,
            "label": grp_label,
            "read_level": default_read,
            "write_level": default_write,
            "commands": grp_commands,
        })

    return {
        "ai_enabled": ai_enabled,
        "version": version,
        "killed": killed,
        "updated_at": updated_at,
        "global_mode": global_mode,
        "write_levels_allowed": write_choices,
        "groups": groups_data,
    }


def update_user_config(
    user,
    *,
    base_version: int,
    groups: dict,
    overrides: dict,
    limits: dict | None = None,
    acknowledge_responsibility: bool = False,
    created_by=None,
    note: str = "",
) -> AiConfigVersion:
    """Cập nhật cấu hình AI của tôi (DW-12-AC2, AC3, AC4)."""
    if not acknowledge_responsibility:
        raise BusinessError(
            "Bạn phải xác nhận chịu trách nhiệm cho cấu hình AI.",
            code="BR-AI-14",
            status_code=400,
        )

    # R5: client cũ còn gửi khoá cũ; chuẩn hoá sang khoá mới TRƯỚC khi kiểm và lưu phiên bản.
    groups = legacy_ids.normalize_group_levels(groups)
    overrides = legacy_ids.normalize_command_keys(overrides)
    limits = legacy_ids.normalize_command_keys(limits)

    registry = get_registry()
    env_write_max = getattr(settings, "AI_WRITE_LEVELS_ALLOWED", "C")
    valid_write_levels = {"OFF", "C"} if env_write_max == "C" else {"OFF", "C", "B"}
    valid_read_levels = {"OFF", "A"}

    with transaction.atomic():
        latest = AiConfigVersion.objects.select_for_update().filter(user=user).order_by("-version").first()
        current_version = latest.version if latest else 0

        if base_version != current_version:
            raise BusinessError(
                "Cấu hình đã thay đổi ở phiên khác.",
                code="AI_CONFIG_CONFLICT",
                status_code=409,
                details={"current_version": current_version},
            )

        errors = {}

        latest_policy = AiPolicyVersion.objects.order_by("-version").first()
        policy_caps = latest_policy.caps if latest_policy else {}
        policy_rz = latest_policy.red_zone_open if latest_policy else {}

        # Validate overrides
        for cmd_id, lvl in (overrides or {}).items():
            spec = registry.get_spec(cmd_id)
            if not spec or not user_has_spec_permission(user, spec):
                errors[cmd_id] = "Lệnh ngoài quyền của bạn"
                continue

            if spec.kind == "read":
                if lvl not in valid_read_levels:
                    errors[cmd_id] = "Mức không hợp lệ cho lệnh đọc"
            else:
                if lvl == "B":
                    # DW-24: Nếu là lệnh vùng đỏ, kiểm tra công tắc Chủ
                    if getattr(spec, "red_zone", False):
                        is_rz_open = any(
                            policy_rz.get(p, False)
                            for p in getattr(spec, "required_perms", ())
                        )
                        if not is_rz_open:
                            errors[cmd_id] = "Chủ chưa mở vùng đỏ cho lệnh này"
                            continue
                    else:
                        is_forced_c = getattr(spec, "force_c", False) or getattr(spec, "max_level", "C") == "C" or cmd_id == "sales.refund.create_refund"
                        if is_forced_c:
                            errors[cmd_id] = f"Lệnh {cmd_id} bị giới hạn trần tối đa là C."
                            continue

                    # DW-19-AC2: Khi env_write_max == "C" (production), chặn user gửi mức B
                    if env_write_max == "C":
                        raise BusinessError(
                            "Môi trường hiện tại không hỗ trợ mức tự thực thi B.",
                            code="BR-AI-27",
                            status_code=400,
                        )

                if lvl not in valid_write_levels:
                    errors[cmd_id] = f"Vượt trần: tối đa {env_write_max}"
                elif getattr(spec, "red_zone", False) and lvl not in {"OFF", "C"}:
                    is_rz_open = any(
                        policy_rz.get(p, False)
                        for p in getattr(spec, "required_perms", ())
                    )
                    if not is_rz_open:
                        errors[cmd_id] = "Chủ chưa mở vùng đỏ cho lệnh này"

        # Validate group levels
        for grp_key, grp_cfg in (groups or {}).items():
            if not isinstance(grp_cfg, dict):
                continue
            r_lvl = grp_cfg.get("read")
            w_lvl = grp_cfg.get("write")
            if r_lvl and r_lvl not in valid_read_levels:
                errors[f"groups.{grp_key}.read"] = "Mức đọc không hợp lệ"
            if w_lvl and w_lvl not in valid_write_levels:
                if w_lvl == "B" and env_write_max == "C":
                    raise BusinessError(
                        "Môi trường hiện tại không hỗ trợ mức tự thực thi B.",
                        code="BR-AI-27",
                        status_code=400,
                    )
                errors[f"groups.{grp_key}.write"] = f"Vượt trần: tối đa {env_write_max}"

        # Validate limits theo caps của Chủ (DW-20-AC1)
        latest_policy = AiPolicyVersion.objects.order_by("-version").first()
        policy_caps = latest_policy.caps if latest_policy else {}
        for cmd_id, lim in (limits or {}).items():
            if not isinstance(lim, dict):
                continue
            cap = get_cap_for_command(policy_caps, cmd_id)
            if cap:
                if "kg" in lim and "kg" in cap and lim["kg"] is not None and cap["kg"] is not None:
                    try:
                        if Decimal(str(lim["kg"])) > Decimal(str(cap["kg"])):
                            errors[cmd_id] = "vượt trần của Chủ"
                    except Exception:
                        errors[cmd_id] = "Giá trị giới hạn kg không hợp lệ"
                if "vnd" in lim and "vnd" in cap and lim["vnd"] is not None and cap["vnd"] is not None:
                    try:
                        if Decimal(str(lim["vnd"])) > Decimal(str(cap["vnd"])):
                            errors[cmd_id] = "vượt trần của Chủ"
                    except Exception:
                        errors[cmd_id] = "Giá trị giới hạn vnd không hợp lệ"

        if errors:
            detail_msg = next(iter(errors.values())) if len(errors) == 1 else "Dữ liệu cấu hình không hợp lệ."
            raise BusinessError(
                detail_msg,
                code="BR-AI-19",
                status_code=400,
                details={"errors": errors},
            )

        new_version = current_version + 1
        changes = []
        old_overrides = legacy_ids.normalize_command_keys(latest.overrides) if latest else {}
        for k, new_val in (overrides or {}).items():
            old_val = old_overrides.get(k, "default")
            if old_val != new_val:
                changes.append({"scope": "override", "key": k, "from": old_val, "to": new_val})

        new_config = AiConfigVersion.objects.create(
            user=user,
            version=new_version,
            group_levels=groups or {},
            overrides=overrides or {},
            limits=limits or {},
            killed=latest.killed if latest else False,
            created_by=created_by or user,
            note=note,
        )

        record_audit(
            actor=created_by or user,
            action="ai_config_update",
            target_model="AiConfigVersion",
            target_id=new_version,
            changes=changes,
            actor_kind="user",
        )

        return new_config


def _killed_by_owner(user) -> bool:
    """
    BR-AI-22: lần tắt đang hiệu lực của `user` có do người giữ `ai.manage_ai_policy` (Chủ) làm không.

    "Đang hiệu lực" = chuỗi phiên bản `killed=True` liên tiếp tính từ phiên bản `killed=False` gần nhất.
    Trong chuỗi đó chỉ cần MỘT phiên bản do Chủ tạo là khoá; nhân viên lưu cấu hình (PUT) khi đang tắt
    chỉ sinh thêm phiên bản `killed=True` do chính họ tạo nên không làm mất khoá. Không cần field mới.
    """
    versions = AiConfigVersion.objects.filter(user=user)
    last_enabled = versions.filter(killed=False).order_by("-version").first()
    run = versions.filter(killed=True).select_related("created_by")
    if last_enabled:
        run = run.filter(version__gt=last_enabled.version)
    return any(
        v.created_by_id != user.id and v.created_by.has_perm("ai.manage_ai_policy") for v in run
    )


def kill_user_config(user, *, killed: bool, created_by=None, note: str = "") -> AiConfigVersion:
    """
    Tắt / Bật lại AI của user (DW-12-AC6, DW-13-AC3).

    BR-AI-22 (Duy chốt 30/09): AI do Chủ tắt thì chỉ người giữ `ai.manage_ai_policy` bật lại được;
    nhân viên tự tắt thì tự bật lại được.
    """
    actor = created_by or user
    with transaction.atomic():
        latest = AiConfigVersion.objects.select_for_update().filter(user=user).order_by("-version").first()
        current_version = latest.version if latest else 0

        if not killed and latest and latest.killed and not actor.has_perm("ai.manage_ai_policy"):
            if _killed_by_owner(user):
                raise BusinessError(
                    "Chủ đã tắt AI của bạn — chỉ Chủ bật lại được.",
                    code="BR-AI-22",
                    status_code=403,
                )
        new_version = current_version + 1

        new_config = AiConfigVersion.objects.create(
            user=user,
            version=new_version,
            group_levels=latest.group_levels if latest else {},
            overrides=latest.overrides if latest else {},
            limits=latest.limits if latest else {},
            killed=killed,
            created_by=created_by or user,
            note=note or ("Tắt AI của tôi" if killed else "Bật lại AI của tôi"),
        )

        record_audit(
            actor=created_by or user,
            action="ai_config_kill",
            target_model="AiConfigVersion",
            target_id=new_version,
            changes=[{"key": "killed", "from": latest.killed if latest else False, "to": killed}],
            actor_kind="user",
        )

        return new_config

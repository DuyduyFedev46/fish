"""
Services xử lý chính sách AI của Chủ (DW-13, 02b §6.6).
"""
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.ai.models.config import AiConfigVersion
from apps.ai.models.policy import AiPolicyVersion
from apps.ai.policy.effective import effective_level
from apps.ai.registry import get_registry
from apps.ai.settings.services import kill_user_config, user_has_spec_permission
from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError


User = get_user_model()


def get_policy_data() -> dict:
    """Lấy dữ liệu chính sách AI theo contract 02b §6.6."""
    latest = AiPolicyVersion.objects.order_by("-version").first()
    version = latest.version if latest else 0
    global_mode = latest.global_mode if latest else "on"
    red_zone_open = latest.red_zone_open if latest else {}
    caps = latest.caps if latest else {}

    env = "production" if not getattr(settings, "DEBUG", True) else "staging"
    production_ready = getattr(settings, "AI_PRODUCTION_READY", False)

    red_zone_definitions = [
        {
            "perm": "inventory.close_batch",
            "label": "Chốt lô",
            "open": red_zone_open.get("inventory.close_batch", False),
            "commands": ["inventory.batch.close"],
            "can_do": "Chỉ lô đủ điều kiện BR-LO-04 + kiểm kê đã duyệt + 7 ngày không có chi phí mới",
            "cannot_do": "Biết chi phí phụ còn về hay không",
            "legal_note": "Chủ chịu trách nhiệm về số liệu kho và chốt giá vốn lô.",
            "delay_minutes": 30,
        },
        {
            "perm": "sales.confirm_refund",
            "label": "Xác nhận hoàn tiền",
            "open": red_zone_open.get("sales.confirm_refund", False),
            "commands": ["sales.refund.confirm"],
            "can_do": "Soát xét phiếu hoàn tiền theo quy định",
            "cannot_do": "Tự động chuyển tiền ngoài ngân hàng",
            "legal_note": "Chủ xác nhận giao dịch tiền thật.",
            "delay_minutes": 0,
        },
        {
            "perm": "sales.confirm_payment_manual",
            "label": "Xác nhận thanh toán tay",
            "open": red_zone_open.get("sales.confirm_payment_manual", False),
            "commands": ["sales.salesorder.confirm_payment", "sales.paymenttransaction.resolve"],
            "can_do": "Khớp giao dịch ngân hàng vào đơn hàng",
            "cannot_do": "Xác minh sao kê ngoài hệ thống",
            "legal_note": "Chịu trách nhiệm về việc khớp tiền.",
            "delay_minutes": 0,
        },
    ]

    registry = get_registry()
    all_specs = registry.get_specs()

    users_list = []
    # DW-13-AC8: users chỉ tên hiển thị, Group, số lệnh theo mức; không có PII khách hay giá vốn
    for u in User.objects.filter(is_active=True).order_by("id"):
        cfg = AiConfigVersion.objects.filter(user=u).order_by("-version").first()
        u_killed = cfg.killed if cfg else False
        u_ver = cfg.version if cfg else 0

        counts = {"A": 0, "B": 0, "C": 0, "OFF": 0}
        for spec in all_specs:
            if user_has_spec_permission(u, spec):
                lvl = effective_level(u, spec, config_version=cfg, policy_version=latest)
                counts[lvl] = counts.get(lvl, 0) + 1

        users_list.append({
            "user_id": u.id,
            "display_name": u.get_full_name() or u.username,
            "groups": [g.name for g in u.groups.all()],
            "killed": u_killed,
            "config_version": u_ver,
            "counts": counts,
        })

    return {
        "version": version,
        "global_mode": global_mode,
        "env": env,
        "production_ready": production_ready,
        "red_zone": red_zone_definitions,
        "caps": caps,
        "users": users_list,
    }


def update_policy(
    *,
    base_version: int,
    global_mode: str | None = None,
    red_zone: dict | None = None,
    caps: dict | None = None,
    acknowledge_responsibility: bool = False,
    created_by,
    note: str = "",
) -> AiPolicyVersion:
    """Cập nhật chính sách AI của Chủ (DW-13-AC1, AC2, AC6)."""
    if not acknowledge_responsibility:
        raise BusinessError(
            "Bạn phải xác nhận chịu trách nhiệm cho chính sách AI.",
            code="BR-AI-14",
            status_code=400,
        )

    with transaction.atomic():
        latest = AiPolicyVersion.objects.select_for_update().order_by("-version").first()
        current_version = latest.version if latest else 0

        if base_version != current_version:
            raise BusinessError(
                "Chính sách AI đã thay đổi ở phiên khác.",
                code="AI_POLICY_CONFLICT",
                status_code=409,
                details={"current_version": current_version},
            )

        # DW-20-AC5: Kiểm tra caps không âm và hợp lệ
        if caps:
            if not isinstance(caps, dict):
                raise BusinessError("Dữ liệu trần (caps) phải là dict.", code="BR-AI-19", status_code=400)
            for cmd_id, cap_cfg in caps.items():
                if not isinstance(cap_cfg, dict):
                    raise BusinessError("Cấu hình trần cho từng lệnh phải là dict.", code="BR-AI-19", status_code=400)
                for field_name in ("kg", "vnd", "daily"):
                    val = cap_cfg.get(field_name)
                    if val is not None:
                        try:
                            dec_val = Decimal(str(val))
                            if dec_val < 0:
                                raise ValueError("Số âm")
                        except Exception:
                            raise BusinessError(
                                f"Giá trị {field_name} của {cmd_id} phải là số không âm.",
                                code="BR-AI-19",
                                status_code=400,
                            )

        # Kiểm tra BR-AI-27: production chưa có S-L1...S-L4 mà mở vùng đỏ hoặc trần > C
        production_ready = getattr(settings, "AI_PRODUCTION_READY", False)
        if not production_ready:
            if red_zone and any(bool(v) for v in red_zone.values()):
                raise BusinessError(
                    "Production chưa hỗ trợ tự thực thi.",
                    code="BR-AI-27",
                    status_code=400,
                )
            if caps:
                for cmd_id, cap_cfg in caps.items():
                    if isinstance(cap_cfg, dict) and cap_cfg.get("max_level") in {"B", "A"}:
                        raise BusinessError(
                            "Production chưa hỗ trợ tự thực thi.",
                            code="BR-AI-27",
                            status_code=400,
                        )

        new_version = current_version + 1
        mode = global_mode or (latest.global_mode if latest else "on")
        if red_zone is not None:
            rz = {**(latest.red_zone_open if latest and latest.red_zone_open else {}), **red_zone}
        else:
            rz = latest.red_zone_open if latest else {}
        cp = caps if caps is not None else (latest.caps if latest else {})

        changes = []
        if latest and latest.global_mode != mode:
            changes.append({"key": "global_mode", "from": latest.global_mode, "to": mode})

        # DW-24-AC4: Xác định các quyền vùng đỏ bị đóng
        closed_perms = set()
        for p, is_op in rz.items():
            if not is_op:
                closed_perms.add(p)
        if latest and latest.red_zone_open:
            for p, prev_op in latest.red_zone_open.items():
                if prev_op and not rz.get(p, False):
                    closed_perms.add(p)
                if prev_op != rz.get(p, False):
                    changes.append({"key": f"red_zone.{p}", "from": prev_op, "to": rz.get(p, False)})
        elif rz:
            for p, is_op in rz.items():
                changes.append({"key": f"red_zone.{p}", "from": False, "to": is_op})

        if closed_perms:
            from apps.ai.registry import get_registry
            from apps.ai.models import AiAction
            registry = get_registry()
            affected_cmd_ids = set()
            for s in registry.get_specs():
                if any(p in closed_perms for p in getattr(s, "required_perms", ())):
                    affected_cmd_ids.add(s.id)

            if affected_cmd_ids:
                # 1. Cấu hình người dùng: hạ override B về C ngay
                for u in User.objects.filter(is_active=True):
                    cfg = AiConfigVersion.objects.filter(user=u).order_by("-version").first()
                    if cfg and cfg.overrides:
                        has_change = False
                        new_overrides = dict(cfg.overrides)
                        for cmd_id in affected_cmd_ids:
                            if new_overrides.get(cmd_id) in ("B", "A"):
                                new_overrides[cmd_id] = "C"
                                has_change = True
                        if has_change:
                            AiConfigVersion.objects.create(
                                user=u,
                                version=cfg.version + 1,
                                group_levels=cfg.group_levels,
                                overrides=new_overrides,
                                limits=cfg.limits,
                                killed=cfg.killed,
                                created_by=created_by,
                                note="Hạ mức C do Chủ đóng công tắc vùng đỏ",
                            )

                # 2. Việc SCHEDULED: chuyển sang PENDING mức C ngay lập tức
                scheduled_acts = AiAction.objects.filter(
                    status=AiAction.Status.SCHEDULED,
                    command__in=affected_cmd_ids,
                )
                for act in scheduled_acts:
                    act.status = AiAction.Status.PENDING
                    act.level = AiAction.Level.C
                    act.downgrade_reason = {
                        "code": "AI_RED_ZONE_CLOSED",
                        "text": "Chủ đã đóng công tắc vùng đỏ",
                    }
                    act.save(update_fields=["status", "level", "downgrade_reason"])
                    record_audit(
                        f"downgrade_{act.command}",
                        actor=created_by,
                        actor_kind="user",
                        proposal_ref=str(act.id),
                        note="Chủ đóng công tắc vùng đỏ, việc xếp lịch chuyển về đề xuất C",
                    )

        new_policy = AiPolicyVersion.objects.create(
            version=new_version,
            global_mode=mode,
            red_zone_open=rz,
            caps=cp,
            created_by=created_by,
            note=note,
        )

        record_audit(
            actor=created_by,
            action="ai_policy_update",
            target_model="AiPolicyVersion",
            target_id=new_version,
            changes=changes,
            actor_kind="user",
        )

        return new_policy


def kill_user_by_admin(admin_user, target_user, *, killed: bool, note: str = "") -> AiConfigVersion:
    """Chủ tắt / mở lại AI của một nhân viên (DW-13-AC3)."""
    return kill_user_config(
        target_user,
        killed=killed,
        created_by=admin_user,
        note=note or ("Chủ tắt AI của nhân viên" if killed else "Chủ mở lại AI của nhân viên"),
    )

"""
Nghiệp vụ duyệt, từ chối hành động AI (02b §4.4, §4.5, DW-11).
"""
import dataclasses
import datetime
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.common.audit import record_audit, set_ai_audit_scope
from apps.common.exceptions import BusinessError
from apps.ai.execution.dispatch import dispatch_command
from apps.ai.models import AiAction
from apps.ai.registry.discovery import get_registry


def visible_actions_for(user):
    """
    Phạm vi việc AI mà `user` được thấy/quyết định (P8 SR-22 / BM-05). Cùng luật với `retrieve`:
    chủ việc, hoặc việc ESCALATED cho đúng nhóm của mình, hoặc có `ai.manage_ai_policy` (thấy hết).
    Ngoài phạm vi -> caller trả 404 (không lộ việc có tồn tại).
    """
    if user.has_perm("ai.manage_ai_policy"):
        return AiAction.objects.all()
    user_groups = set(user.groups.values_list("name", flat=True))
    return AiAction.objects.filter(
        Q(owner=user) | Q(status=AiAction.Status.ESCALATED, assignee_group__in=user_groups)
    )


@transaction.atomic
def confirm_ai_action(*, action_id: str, user, confirm_nonce: str | None = None, request=None):
    """
    Duyệt và thực thi một đề xuất AI (mức C).
    - AI_ENABLED=false -> 410 AI_DISABLED (DW-11-AC9).
    - Kiểm tra trạng thái: PENDING, chưa hết hạn 15 phút, chưa bị từ chối/duyệt trước đó (DW-11-AC3).
    - V5 (BR-AI-14): Phải mở xem chi tiết (viewed_at) và đủ ít nhất AI_CONFIRM_MIN_SECONDS (3 giây).
    - H1/BR-AI-04: Người duyệt phải có đủ quyền 3 tầng của lệnh (DW-11-AC5).
    - H6/BR-KK-02: Kiểm kê - người duyệt không được là chủ AI đã nhập số kiểm kê (DW-11-AC6).
    - Chạy view bằng token/user của NGƯỜI DUYỆT.
    - Ghi AuditLog actor_kind="user", actor=người duyệt, proposal_ref=id (DW-11-AC2).
    """
    # 1. Kiểm tra AI_ENABLED
    if not getattr(settings, "AI_ENABLED", False):
        raise BusinessError("Hệ thống AI đang tắt.", code="AI_DISABLED", status_code=410)

    # 2. Lấy AiAction có khoá select_for_update
    # BM-05: cùng bộ lọc với retrieve; ngoài phạm vi -> 404, trạng thái không đổi.
    action = (
        visible_actions_for(user).select_for_update()
        .filter(id=action_id)
        .first()
    )
    if not action:
        raise BusinessError("Không tìm thấy hành động AI.", code="NOT_FOUND", status_code=404)

    # 3. Kiểm tra trạng thái
    if action.status != AiAction.Status.PENDING:
        if action.status in (AiAction.Status.CONFIRMED, AiAction.Status.REJECTED):
            raise BusinessError("Hành động đã được quyết định.", code="AI_ACTION_ALREADY_DECIDED", status_code=409)
        raise BusinessError(f"Hành động ở trạng thái {action.status}, không thể duyệt.", code="AI_ACTION_NOT_PENDING", status_code=409)

    now = timezone.now()
    if action.expires_at and now > action.expires_at:
        action.status = AiAction.Status.EXPIRED
        action.save(update_fields=["status"])
        raise BusinessError("Hành động đã hết hạn duyệt.", code="AI_ACTION_EXPIRED", status_code=410)

    # 4. Kiểm tra mở xem chi tiết & thời gian xem tối thiểu (V5, BR-AI-14)
    if not action.viewed_at:
        raise BusinessError("Chưa mở xem chi tiết trước khi xác nhận.", code="BR-AI-14", status_code=400)

    min_seconds = getattr(settings, "AI_CONFIRM_MIN_SECONDS", 3)
    seconds_viewed = (now - action.viewed_at).total_seconds()
    if seconds_viewed < min_seconds:
        raise BusinessError(
            f"Cần xem xét kỹ ít nhất {min_seconds} giây trước khi xác nhận.",
            code="BR-AI-14",
            status_code=400,
        )

    # 5. Lấy spec từ registry
    spec = get_registry().get(action.command)
    if not spec:
        raise BusinessError("Lệnh không tồn tại trong hệ thống.", code="COMMAND_UNKNOWN", status_code=404)

    # 6. Kiểm tra quyền của người duyệt (user)
    if spec.required_perms:
        missing_perms = [p for p in spec.required_perms if not user.has_perm(p)]
        if missing_perms:
            raise BusinessError(
                "Bạn không có quyền thực thi lệnh này.",
                code="BR-AI-04",
                status_code=403,
            )

    # 7. Kiểm tra H6: BR-KK-02 (kiểm kê không được tự duyệt cho AI của mình)
    if (
        "stockreconciliation" in action.command
        or "approve_stockreconciliation" in spec.required_perms
    ):
        if action.owner_id == user.id:
            raise BusinessError(
                "Người duyệt không được là người nhập hoặc chủ AI đã nhập số kiểm kê.",
                code="BR-KK-02",
                status_code=400,
            )

    # 8. Thực thi lệnh trong ngữ cảnh audit của người duyệt
    with set_ai_audit_scope(
        ai_actor=None,
        level=action.level,
        config_version=action.config_version,
        policy_version=action.policy_version,
        action_ref=str(action.id),
        is_proposal=False,
    ):
        dispatch_res = dispatch_command(
            spec,
            user=user,
            args=action.args,
            target_id=action.target_id,
            request_origin=request,
        )

    if dispatch_res.is_error:
        data = dispatch_res.data
        if isinstance(data, dict):
            detail = data.get("detail", "Thao tác thực thi thất bại.")
            code = data.get("code", "BUSINESS_ERROR")
        else:
            detail = str(data)
            code = "AI_DISPATCH_FAILED"
        raise BusinessError(detail, code=code, status_code=dispatch_res.status_code)

    # 9. Cập nhật trạng thái AiAction
    action.status = AiAction.Status.CONFIRMED
    action.decided_by = user
    action.decided_at = timezone.now()
    action.executed_at = timezone.now()
    action.save()

    # 10. Ghi AuditLog xác nhận
    record_audit(
        f"confirm_{spec.id}",
        actor=user,
        actor_kind="user",
        proposal_ref=str(action.id),
        note=f"Duyệt thực thi đề xuất AI {action.id}",
    )

    return {"outcome": "done", "result": dispatch_res.data}


@transaction.atomic
def reject_ai_action(*, action_id: str, user, reason_code: str = "", request=None):
    """
    Từ chối một đề xuất AI (DW-11-AC4).
    Chứng từ không đổi, AiAction -> REJECTED, ghi AuditLog.
    """
    # BM-05: cùng bộ lọc với retrieve; ngoài phạm vi -> 404, trạng thái không đổi.
    action = (
        visible_actions_for(user).select_for_update()
        .filter(id=action_id)
        .first()
    )
    if not action:
        raise BusinessError("Không tìm thấy hành động AI.", code="NOT_FOUND", status_code=404)

    if action.status != AiAction.Status.PENDING:
        raise BusinessError("Hành động đã được quyết định.", code="AI_ACTION_ALREADY_DECIDED", status_code=409)

    action.status = AiAction.Status.REJECTED
    action.decided_by = user
    action.decided_at = timezone.now()
    action.save()

    record_audit(
        f"reject_{action.command}",
        actor=user,
        actor_kind="user",
        proposal_ref=str(action.id),
        note=f"Từ chối đề xuất AI {action.id}. Lý do: {reason_code or 'Không'}",
    )

    return {"outcome": "rejected", "action_id": str(action.id)}


@transaction.atomic
def undo_ai_action(*, action_id: str, user, request=None) -> dict:
    """
    Hoàn tác hành động AI mức B (DW-19, DW-21).

    P8 SR-22 / F10: hoàn tác là rút lại việc AI đã làm nên vẫn cho phép khi AI_ENABLED=false
    (không còn 410 AI_DISABLED). Hành động huỷ lấy từ `undo="cancel_action:<act>"` của lệnh; không có
    đường hoàn tác thì 400 AI_CANNOT_UNDO, không được đánh dấu UNDONE khi chưa làm gì.
    """
    action = (
        AiAction.objects.select_for_update()
        .filter(id=action_id)
        .first()
    )
    if not action:
        raise BusinessError("Không tìm thấy hành động AI.", code="NOT_FOUND", status_code=404)

    # Phân quyền: chỉ owner hoặc người có quyền ai.manage_ai_policy
    if action.owner_id != user.id and not user.has_perm("ai.manage_ai_policy"):
        raise BusinessError("Bạn không có quyền hoàn tác hành động này.", code="PERMISSION_DENIED", status_code=403)

    now = timezone.now()

    # Trường hợp 1: Huỷ lịch (DW-21-AC4)
    if action.status == AiAction.Status.SCHEDULED:
        if action.undo_until and now > action.undo_until:
            raise BusinessError("Đã quá thời gian huỷ lịch.", code="AI_UNDO_WINDOW_CLOSED", status_code=410)

        action.status = AiAction.Status.CANCELLED
        action.decided_by = user
        action.decided_at = now
        action.save(update_fields=["status", "decided_by", "decided_at"])

        record_audit(
            f"cancel_schedule_{action.command}",
            actor=user,
            actor_kind="user",
            proposal_ref=str(action.id),
            note=f"Huỷ lịch thực thi lệnh AI {action.id}",
        )

        return {"outcome": "cancelled", "action_id": str(action.id)}

    # Trường hợp 2: Hoàn tác hành động mức B đã thực hiện (DW-19-AC3, AC4)
    if action.status == AiAction.Status.DONE and action.level == AiAction.Level.B:
        if not action.undo_until or now > action.undo_until:
            raise BusinessError("Thời gian hoàn tác đã đóng.", code="AI_UNDO_WINDOW_CLOSED", status_code=410)

        spec = get_registry().get(action.command)
        undo_attr = getattr(spec, "undo", "") or ""
        cancel_act = undo_attr.split(":", 1)[1].strip() if undo_attr.startswith("cancel_action:") else ""
        view_cls = getattr(spec, "view_cls", None)
        if not cancel_act or view_cls is None or not hasattr(view_cls, cancel_act):
            raise BusinessError(
                "Hành động này không có cách hoàn tác tự động.", code="AI_CANNOT_UNDO", status_code=400
            )

        # Tìm target_id
        target_id = None
        if action.result_ref and isinstance(action.result_ref, dict):
            target_id = action.result_ref.get("id")
        if not target_id:
            target_id = action.target_id

        # Gọi đúng action huỷ khai báo trên lệnh (không mặc định huỷ phiếu nhập). Quyền 3 tầng do chính
        # view của action huỷ kiểm tra theo người hoàn tác; lỗi nghiệp vụ (vd BR-MH-07) giữ nguyên mã.
        undo_spec = dataclasses.replace(
            spec, action=cancel_act, method="POST", detail=True, required_perms=()
        )
        result = dispatch_command(
            undo_spec, user=user, args={}, target_id=str(target_id) if target_id is not None else None,
            request_origin=request,
        )
        if result.is_error:
            data = result.data if isinstance(result.data, dict) else {}
            raise BusinessError(
                str(data.get("detail") or "Không hoàn tác được hành động này."),
                code=str(data.get("code") or "AI_CANNOT_UNDO"),
                status_code=result.status_code or 400,
            )

        action.status = AiAction.Status.UNDONE
        action.decided_by = user
        action.decided_at = now
        action.save(update_fields=["status", "decided_by", "decided_at"])

        record_audit(
            f"undo_{action.command}",
            actor=user,
            actor_kind="user",
            proposal_ref=str(action.id),
            note=f"Hoàn tác hành động AI {action.id}",
        )

        return {"outcome": "undone", "action_id": str(action.id)}

    raise BusinessError(f"Hành động ở trạng thái {action.status}, không thể hoàn tác.", code="AI_CANNOT_UNDO", status_code=400)


def find_assignee_group_for_step(step: dict, spec=None) -> str:
    """
    Định tuyến Group nhận việc theo quyền (DW-23-AC2).
    Không so sánh hardcode tên Group trong code; dùng quyền để tìm Group có thẩm quyền.
    """
    from django.contrib.auth.models import Group, Permission

    # 1. Dò theo required_perms của spec lệnh
    if spec and getattr(spec, "required_perms", None):
        for perm_str in spec.required_perms:
            if "." in perm_str:
                app_label, codename = perm_str.split(".", 1)
                matching_groups = set(
                    Group.objects.filter(
                        permissions__content_type__app_label=app_label,
                        permissions__codename=codename,
                    ).values_list("name", flat=True)
                )
                if "quan_ly" in matching_groups:
                    return "quan_ly"
                if "chu" in matching_groups:
                    return "chu"
                if matching_groups:
                    return list(matching_groups)[0]

    # 2. Dò theo trường who của step nếu có
    who_list = [w.lower() for w in step.get("who", [])]
    if any("quản lý" in w for w in who_list):
        return "quan_ly"
    if any("chủ" in w for w in who_list):
        return "chu"

    return "chu"


def escalate_guidance_step(*, doc_type: str, doc_id: str, step_key: str, user) -> dict:
    """
    Chuyển việc cho người/nhóm có quyền (DW-23, contract 02-stories DW-23).
    POST /api/ai/actions/escalate/ {"doc_type", "doc_id", "step_key"}
    -> 201 {"action_id", "assignee_group"}
    """
    import logging

    from django.core.exceptions import PermissionDenied
    from django.http import Http404
    from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied

    from apps.common.guidance.api import get_guidance_provider
    from apps.ai.registry.discovery import get_registry

    logger = logging.getLogger(__name__)

    if not doc_type or not doc_id or not step_key:
        raise BusinessError("Thiếu tham số chứng từ hoặc bước cần nhờ.", code="INVALID_PARAMS", status_code=400)

    provider = get_guidance_provider(doc_type)
    if provider is None:
        raise BusinessError(f"Không hỗ trợ loại chứng từ: {doc_type}.", code="GUIDANCE_TYPE_UNKNOWN", status_code=400)

    try:
        data = provider(doc_id=str(doc_id), user=user)
    except (Http404, PermissionDenied, DRFPermissionDenied):
        # SR-06-AC2: 404 (ngoài phạm vi/không có) và 403 (thiếu quyền xem) đi thẳng ra API,
        # không bị đổi thành 400 (DRF exception handler dựng body chung).
        raise
    except Exception as exc:  # noqa: BLE001
        # Không in nguyên văn exception ra response (có thể chứa dữ liệu từ DB — bất biến 9).
        logger.warning("escalate: không nạp được chứng từ type=%s err=%s", doc_type, type(exc).__name__)
        raise BusinessError("Không thể nạp chứng từ.", code="DOC_NOT_FOUND", status_code=400)

    next_steps = data.get("next_steps", [])
    target_step = None
    for s in next_steps:
        s_key = s.key if hasattr(s, "key") else s.get("key")
        if s_key == step_key:
            target_step = s
            break

    if target_step is None:
        raise BusinessError(f"Bước '{step_key}' không tồn tại trên chứng từ.", code="STEP_NOT_FOUND", status_code=400)

    is_allowed = target_step.allowed if hasattr(target_step, "allowed") else target_step.get("allowed")
    if is_allowed:
        raise BusinessError("Bạn đã có quyền tự thực hiện bước này.", code="BR-AI-25", status_code=400)

    command_id = target_step.command if hasattr(target_step, "command") else target_step.get("command")
    registry = get_registry()
    spec = registry.get(command_id) if command_id else None

    step_dict = {
        "key": step_key,
        "who": target_step.who if hasattr(target_step, "who") else target_step.get("who", []),
        "command": command_id,
        "label": target_step.label if hasattr(target_step, "label") else target_step.get("label", ""),
    }

    target_group = find_assignee_group_for_step(step_dict, spec)

    action = AiAction.objects.create(
        command=command_id or f"{doc_type}.{step_key}",
        kind=AiAction.Kind.WRITE,
        level=AiAction.Level.C,
        status=AiAction.Status.ESCALATED,
        owner=user,
        assignee_group=target_group,
        target_model=doc_type,
        target_id=str(doc_id),
        args={
            "doc_type": doc_type,
            "doc_id": str(doc_id),
            "step_key": step_key,
            "label": step_dict["label"],
        },
    )

    record_audit(
        f"escalate_{action.command}",
        actor=user,
        actor_kind="user",
        proposal_ref=str(action.id),
        note=f"Chuyển việc {step_dict['label']} ({doc_type} #{doc_id}) cho nhóm {target_group}",
    )

    return {
        "action_id": str(action.id),
        "assignee_group": target_group,
    }



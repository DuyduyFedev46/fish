"""
Nghiệp vụ duyệt, từ chối hành động AI (02b §4.4, §4.5, DW-11).
"""
import datetime
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.common.audit import record_audit, set_ai_audit_scope
from apps.common.exceptions import BusinessError
from apps.ai.execution.dispatch import dispatch_command
from apps.ai.models import AiAction
from apps.ai.registry.discovery import get_registry


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
    action = (
        AiAction.objects.select_for_update()
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
    action = (
        AiAction.objects.select_for_update()
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

"""
Management command: Chạy các việc AI mức B đã lên lịch tới hạn (DW-21, 02b §4.2).
Idempotent, select_for_update(skip_locked=True).
"""
import datetime
import logging
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.common.audit import record_audit, set_ai_audit_scope
from apps.ai.execution.dispatch import dispatch_command
from apps.ai.models import AiAction, AiConfigVersion
from apps.ai.policy.effective import effective_level
from apps.ai.registry.discovery import get_registry

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Chạy các hành động AI mức B (trì hoãn ghi) tới hạn (DW-21)"

    def handle(self, *args, **options):
        now = timezone.now()

        # DW-21-AC8: Nếu AI tắt toàn cục lúc tới hạn -> hạ về C (PENDING)
        if not getattr(settings, "AI_ENABLED", False):
            due_actions = AiAction.objects.filter(
                status=AiAction.Status.SCHEDULED,
                execute_after__lte=now,
            )
            count = 0
            for act in due_actions:
                with transaction.atomic():
                    locked = (
                        AiAction.objects.select_for_update(skip_locked=True)
                        .filter(pk=act.pk, status=AiAction.Status.SCHEDULED)
                        .first()
                    )
                    if not locked:
                        continue
                    locked.status = AiAction.Status.PENDING
                    locked.level = AiAction.Level.C
                    locked.downgrade_reason = {
                        "code": "AI_DISABLED",
                        "text": "Hệ thống AI đang tắt",
                    }
                    locked.save(update_fields=["status", "level", "downgrade_reason"])
                    count += 1
            self.stdout.write(f"AI_ENABLED is False: downgraded {count} scheduled actions to PENDING.")
            return

        due_actions = AiAction.objects.filter(
            status=AiAction.Status.SCHEDULED,
            execute_after__lte=now,
        ).order_by("execute_after")

        registry = get_registry()
        executed_count = 0
        downgraded_count = 0

        for act in due_actions:
            # DW-21-AC5: select_for_update(skip_locked=True) để đảm bảo idempotent giữa nhiều tiến trình
            with transaction.atomic():
                locked_action = (
                    AiAction.objects.select_for_update(skip_locked=True)
                    .filter(pk=act.pk, status=AiAction.Status.SCHEDULED)
                    .first()
                )
                if not locked_action:
                    continue

                owner = locked_action.owner
                spec = registry.get(locked_action.command)

                # DW-21-AC3: Kiểm tra lại các điều kiện
                should_downgrade = False
                downgrade_text = "Cấu hình AI đã thay đổi"

                if not owner.is_active:
                    should_downgrade = True
                    downgrade_text = "Tài khoản người dùng đã bị khoá"
                elif not spec:
                    should_downgrade = True
                    downgrade_text = "Lệnh không còn tồn tại trong hệ thống"
                else:
                    # Kiểm tra tắt khẩn cá nhân
                    user_cfg = AiConfigVersion.objects.filter(user=owner).order_by("-version").first()
                    if user_cfg and user_cfg.killed:
                        should_downgrade = True
                        downgrade_text = "AI cá nhân của người dùng đã bị tắt khẩn"
                    else:
                        current_lvl = effective_level(owner, spec)
                        if current_lvl != "B":
                            should_downgrade = True
                            downgrade_text = "Mức tự chủ của lệnh không còn là B"

                if should_downgrade:
                    locked_action.status = AiAction.Status.PENDING
                    locked_action.level = AiAction.Level.C
                    locked_action.downgrade_reason = {
                        "code": "AI_LEVEL_REVOKED",
                        "text": downgrade_text,
                    }
                    locked_action.save(update_fields=["status", "level", "downgrade_reason"])
                    downgraded_count += 1
                    # DW-21-AC7: Log chỉ in id lệnh + mã action
                    logger.info("Downgraded action=%s cmd=%s reason=AI_LEVEL_REVOKED", locked_action.id, locked_action.command)
                    continue

                # DW-25-AC4: Nếu là lệnh chốt lô, kiểm tra lại điều kiện sàn trước khi gọi view
                if locked_action.command == "inventory.batch.close" or (spec and getattr(spec, "required_perms", None) and "inventory.close_batch" in spec.required_perms):
                    from apps.inventory.models import Batch
                    from apps.ai.execution.safety import check_ai_close_batch_conditions
                    b_target = None
                    t_id = locked_action.target_id
                    if t_id:
                        if str(t_id).isdigit():
                            b_target = Batch.objects.filter(pk=int(t_id)).first()
                        if not b_target:
                            b_target = Batch.objects.filter(batch_id=str(t_id)).first()
                    ok, close_reason = check_ai_close_batch_conditions(b_target, current_action_id=locked_action.id)
                    if not ok:
                        # DW-25-AC4: Không chốt, về PENDING/ESCALATED + chuyển việc Chủ
                        locked_action.status = AiAction.Status.ESCALATED
                        locked_action.assignee_group = "chu"
                        locked_action.downgrade_reason = close_reason
                        locked_action.save(update_fields=["status", "assignee_group", "downgrade_reason"])
                        record_audit(
                            f"escalate_{locked_action.command}",
                            actor=None,
                            actor_kind="ai",
                            ai_actor=owner,
                            ai_level="B",
                            proposal_ref=str(locked_action.id),
                            note="Lô không còn đủ điều kiện chốt, chuyển việc cho Chủ",
                        )
                        logger.info("Escalated action=%s cmd=%s reason=CONDITIONS_NOT_MET", locked_action.id, locked_action.command)
                        continue

                # Mọi điều kiện đạt: gọi view qua dispatch_command
                with set_ai_audit_scope(
                    ai_actor=owner,
                    level="B",
                    config_version=locked_action.config_version,
                    policy_version=locked_action.policy_version,
                    action_ref=str(locked_action.id),
                ):
                    dispatch_res = dispatch_command(
                        spec,
                        user=owner,
                        args=locked_action.args,
                        target_id=locked_action.target_id,
                    )

                if dispatch_res.is_error:
                    # DW-23-AC2: Gặp BusinessError -> ESCALATED cho chủ AI hoặc Group có quyền
                    target_group = "chu"
                    if spec:
                        owner_has_perm = True
                        if getattr(spec, "required_perms", None):
                            owner_has_perm = all(owner.has_perm(p) for p in spec.required_perms)

                        if owner_has_perm:
                            owner_groups = list(owner.groups.values_list("name", flat=True))
                            target_group = owner_groups[0] if owner_groups else "chu"
                        else:
                            from apps.ai.actions.services import find_assignee_group_for_step
                            target_group = find_assignee_group_for_step({}, spec=spec)

                    locked_action.status = AiAction.Status.ESCALATED
                    locked_action.assignee_group = target_group
                    locked_action.save(update_fields=["status", "assignee_group"])

                    with set_ai_audit_scope(
                        ai_actor=owner,
                        level="C",
                        config_version=locked_action.config_version,
                        policy_version=locked_action.policy_version,
                        action_ref=str(locked_action.id),
                    ):
                        record_audit(
                            f"escalate_{locked_action.command}",
                            actor=None,
                            actor_kind="ai",
                            ai_actor=owner,
                            proposal_ref=str(locked_action.id),
                            note=f"Lệnh AI gặp lỗi {dispatch_res.status_code}, chuyển việc cho nhóm {target_group}",
                        )
                    logger.warning("Escalated action=%s cmd=%s to group=%s code=%s", locked_action.id, locked_action.command, target_group, dispatch_res.status_code)
                else:
                    result_ref = None
                    if isinstance(dispatch_res.data, dict) and "id" in dispatch_res.data:
                        result_ref = {
                            "model": locked_action.target_model,
                            "id": dispatch_res.data.get("id"),
                        }

                    locked_action.status = AiAction.Status.DONE
                    locked_action.executed_at = timezone.now()
                    locked_action.result_ref = result_ref
                    locked_action.save(update_fields=["status", "executed_at", "result_ref"])

                    # Ghi AuditLog execute_<spec.id>
                    with set_ai_audit_scope(
                        ai_actor=owner,
                        level="B",
                        config_version=locked_action.config_version,
                        policy_version=locked_action.policy_version,
                        action_ref=str(locked_action.id),
                    ):
                        record_audit(
                            f"execute_{spec.id}",
                            actor=None,
                            actor_kind="ai",
                            ai_actor=owner,
                            proposal_ref=str(locked_action.id),
                            note=f"Job thực thi lệnh AI {spec.title} tới hạn",
                        )

                    executed_count += 1
                    # DW-21-AC7: Log chỉ in id lệnh + mã action
                    logger.info("Executed action=%s cmd=%s", locked_action.id, locked_action.command)

        # DW-23-AC3: Quét các việc chờ quá 2 giờ -> đẩy lên 'chu'
        two_hours_ago = now - datetime.timedelta(hours=2)
        overdue_actions = AiAction.objects.filter(
            status=AiAction.Status.PENDING,
            created_at__lte=two_hours_ago,
        ).exclude(assignee_group="chu")

        overdue_escalated_count = 0
        for overdue_act in overdue_actions:
            with transaction.atomic():
                locked_overdue = (
                    AiAction.objects.select_for_update(skip_locked=True)
                    .filter(pk=overdue_act.pk, status=AiAction.Status.PENDING)
                    .first()
                )
                if not locked_overdue:
                    continue
                locked_overdue.status = AiAction.Status.ESCALATED
                locked_overdue.assignee_group = "chu"
                locked_overdue.save(update_fields=["status", "assignee_group"])

                # Ghi AuditLog không có PII/giá vốn
                record_audit(
                    f"escalate_overdue_{locked_overdue.command}",
                    actor=None,
                    actor_kind="system",
                    proposal_ref=str(locked_overdue.id),
                    note=f"Việc AI #{locked_overdue.id} quá hạn 2 giờ, chuyển cho Chủ vựa",
                )
                overdue_escalated_count += 1
                logger.info("Overdue action=%s cmd=%s escalated to chu", locked_overdue.id, locked_overdue.command)

        self.stdout.write(f"Finished: executed {executed_count}, downgraded {downgraded_count}, overdue escalated {overdue_escalated_count}.")

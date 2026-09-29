"""
Giám sát sức khoẻ job xử lý thời hạn CSKH (02b §5.2).
Exit code 1 nếu phát hiện:
1. Task PENDING quá first_unreachable_at + W + 10' mà chưa chuyển ESCALATED
2. (Khi CSKH_AUTO_CANCEL_ENABLED=1) Task ESCALATED quá escalated_at + D + 10' mà chưa tự huỷ
"""
from datetime import timedelta
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.delivery.models import ConfirmationTask, DeliveryNote

logger = logging.getLogger("cangca.delivery.cskh")


class Command(BaseCommand):
    help = "Kiểm tra sức khoẻ của job xử lý thời hạn CSKH (exit 1 nếu job có dấu hiệu chết)."

    def add_arguments(self, parser):
        parser.add_argument("--grace-minutes", type=int, default=10, help="Số phút trễ cho phép (mặc định 10).")

    def handle(self, *args, **options):
        now = timezone.now()
        grace = options.get("grace_minutes", 10)

        window_mins = getattr(settings, "CSKH_UNREACHABLE_WINDOW_MINUTES", 30)
        decision_mins = getattr(settings, "CSKH_MANAGER_DECISION_MINUTES", 30)
        auto_cancel_enabled = getattr(settings, "CSKH_AUTO_CANCEL_ENABLED", False)

        # 1. Kiểm tra task PENDING bị quá hạn chuyển Quản lý
        pending_cutoff = now - timedelta(minutes=window_mins + grace)
        stale_pending = ConfirmationTask.objects.filter(
            state=ConfirmationTask.State.PENDING,
            attempts__gte=1,
            first_unreachable_at__isnull=False,
            first_unreachable_at__lt=pending_cutoff,
            note__status=DeliveryNote.Status.CONFIRMING,
        ).count()

        if stale_pending > 0:
            msg = (
                f"CẢNH BÁO: Có {stale_pending} task CSKH PENDING quá hạn "
                f">{window_mins + grace} phút chưa được chuyển Quản lý (job process_cskh_deadlines có thể đã chết)."
            )
            logger.error(msg)
            self.stderr.write(self.style.ERROR(msg))
            raise SystemExit(1)

        # 2. Kiểm tra task ESCALATED bị quá hạn tự huỷ (khi cờ tự huỷ bật)
        if auto_cancel_enabled:
            escalated_cutoff = now - timedelta(minutes=decision_mins + grace)
            stale_escalated = ConfirmationTask.objects.filter(
                state=ConfirmationTask.State.ESCALATED,
                escalation_reason__in=(
                    ConfirmationTask.EscalationReason.UNREACHABLE,
                    ConfirmationTask.EscalationReason.WRONG_NUMBER,
                ),
                auto_cancel_blocked_code="",
                escalated_at__isnull=False,
                escalated_at__lt=escalated_cutoff,
                note__status=DeliveryNote.Status.CONFIRMING,
            ).count()

            if stale_escalated > 0:
                msg = (
                    f"CẢNH BÁO: Có {stale_escalated} task CSKH ESCALATED quá hạn "
                    f">{decision_mins + grace} phút chưa được tự huỷ."
                )
                logger.error(msg)
                self.stderr.write(self.style.ERROR(msg))
                raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("Job CSKH deadlines khoẻ (không có task quá hạn tồn đọng)."))

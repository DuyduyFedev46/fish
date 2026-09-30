"""
API "Cần chú ý" cho việc gọi và tem (CS-15, 02b §4.5, §5).
Endpoint: GET /api/dashboard/attention/
Khoá theo quyền người gọi.
"""
from datetime import timedelta
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.delivery.models import ConfirmationTask, DeliveryNote, LabelPrint
from apps.inventory.models import Batch


class DashboardAttentionView(APIView):
    """
    GET /api/dashboard/attention/
    Trả về số việc đang chờ xử lý theo từng phân quyền:
    - confirm_with_customer: cskh_queue_waiting, refund_calls_open
    - decide_unconfirmed: cskh_escalated, cskh_auto_cancel_blocked
    - print_label: labels_not_printed, labels_to_void
    - inventory.cancel_expired_batch (Chủ): expired_batches_open — số lô Quá hạn còn tồn (BR-LO-07, SR-15)
    Không có quyền nào trong 4 quyền trên -> 403.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        has_confirm = user.has_perm("delivery.confirm_with_customer")
        has_decide = user.has_perm("delivery.decide_unconfirmed")
        has_print = user.has_perm("delivery.print_label")
        has_expired = user.has_perm("inventory.cancel_expired_batch")

        if not (has_confirm or has_decide or has_print or has_expired):
            raise PermissionDenied("Bạn không có quyền xem thông tin chú ý.")

        now = timezone.now()
        res = {}

        # 1. Nhóm CSKH (confirm_with_customer)
        if has_confirm:
            queue_alert_mins = getattr(settings, "CSKH_QUEUE_ALERT_MINUTES", 60)
            queue_cutoff = now - timedelta(minutes=queue_alert_mins)
            cskh_queue_waiting = ConfirmationTask.objects.filter(
                state=ConfirmationTask.State.PENDING,
                note__status=DeliveryNote.Status.CONFIRMING,
                attempts=0,
                note__sales_invoice__issued_at__lte=queue_cutoff,
            ).count()

            refund_calls_open = ConfirmationTask.objects.filter(
                state=ConfirmationTask.State.REFUND_CALL,
            ).count()

            res["cskh_queue_waiting"] = cskh_queue_waiting
            res["refund_calls_open"] = refund_calls_open

        # 2. Nhóm Quản lý (decide_unconfirmed)
        if has_decide:
            cskh_escalated = ConfirmationTask.objects.filter(
                state=ConfirmationTask.State.ESCALATED,
            ).count()

            cskh_auto_cancel_blocked = ConfirmationTask.objects.exclude(
                auto_cancel_blocked_code="",
            ).count()

            res["cskh_escalated"] = cskh_escalated
            res["cskh_auto_cancel_blocked"] = cskh_auto_cancel_blocked

        # 3. Nhóm Kho (print_label)
        if has_print:
            label_alert_mins = getattr(settings, "LABEL_UNPRINTED_ALERT_MINUTES", 15)
            label_cutoff = now - timedelta(minutes=label_alert_mins)
            labels_not_printed = DeliveryNote.objects.filter(
                status=DeliveryNote.Status.PREPARING,
                confirmed_at__isnull=False,
                confirmed_at__lte=label_cutoff,
                label_prints__isnull=True,
            ).count()

            # Tem cần huỷ: chưa void VÀ (đơn CANCELLED hoặc tem đã superseded)
            labels_to_void = LabelPrint.objects.filter(
                voided_at__isnull=True,
            ).filter(
                Q(note__status=DeliveryNote.Status.CANCELLED) | Q(superseded_at__isnull=False)
            ).count()

            res["labels_not_printed"] = labels_not_printed
            res["labels_to_void"] = labels_to_void

        # 4. Lô quá hạn còn tồn (Chủ, BR-LO-07): chỉ đếm, không trả tiền/giá vốn.
        if has_expired:
            res["expired_batches_open"] = Batch.objects.filter(
                status=Batch.Status.EXPIRED, qty_available__gt=0,
            ).count()

        return Response(res, status=status.HTTP_200_OK)

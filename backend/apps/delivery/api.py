"""
API nội bộ — giao hàng. Tầng 3 phạm vi dòng: nv_giao chỉ thấy & sửa phiếu được gán
cho mình (get_queryset lọc, không phải ẩn ở giao diện — BR-PQ-12).
"""
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.api import BusinessModelPermissions, DocumentViewSet, has_full_delivery_scope

from . import services
from .models import DeliveryNote
from .serializers import DeliveryNoteSerializer

class DeliveryNoteViewSet(DocumentViewSet):
    queryset = DeliveryNote.objects.select_related("sales_invoice", "assigned_to").all()
    serializer_class = DeliveryNoteSerializer
    permission_classes = [BusinessModelPermissions]
    custom_perm_actions = ("set_status",)
    # BR-PQ-14 / BR-GH-06: trạng thái & người giao chỉ đổi qua action nghiệp vụ.
    locked_fields = ("status", "assigned_to", "failed_attempts", "completed_at", "sales_invoice")

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if has_full_delivery_scope(user):
            return qs
        return qs.filter(assigned_to=user)  # nv_giao: chỉ phiếu của mình

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action == "list":
            # S14-AC2: lọc theo trạng thái (nhiều, cách dấu phẩy) — CANCELLED không nằm
            # trong nhóm trạng thái hoạt động nên tự vắng mặt khi FE lọc PREPARING,...
            statuses = [
                s.strip() for s in self.request.query_params.get("status", "").split(",") if s.strip()
            ]
            if statuses:
                queryset = queryset.filter(status__in=statuses)
        return queryset

    @action(detail=True, methods=["post"], url_path="status")
    def set_status(self, request, pk=None):
        note = self.get_object()  # đã bị get_queryset lọc theo phạm vi
        to_status = request.data.get("to_status")
        needs_decision = None
        if to_status == DeliveryNote.Status.FAILED:
            # BR-GH-04: mark_failed trả (note, needs_decision) — không gán thẳng tuple
            # vào serializer (B-DELIVERY-MARKFAILED, 04-qa-report.md).
            note, needs_decision = services.mark_failed(note=note, actor=request.user)
        else:
            note = services.advance_status(note=note, to_status=to_status, actor=request.user)
        data = self.get_serializer(note).data
        if needs_decision is not None:
            data["needs_decision"] = needs_decision
        return Response(data)

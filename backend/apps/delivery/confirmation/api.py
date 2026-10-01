"""
API CSKH: Hàng chờ gọi xác nhận, claim, ghi kết quả, huỷ xác nhận, tìm kiếm (2026-09-28-cskh-xac-nhan-in-tem).
Tuân thủ:
- Bất biến 1: Không tính toán hay trả về giá vốn
- Bất biến 9: Phân quyền theo ma trận, che SĐT và ẩn danh ngoài phạm vi, NoStoreMixin
- Chống trùng lặp theo request_id
"""
from datetime import datetime
import re
from django.db.models import Q
from django.http import Http404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.api import NoStoreMixin
from apps.common.exceptions import BusinessError
from apps.common.pii import mask_phone, normalize_phone
from apps.common.throttling import CustomerSearchThrottle
from apps.delivery.confirmation import services as confirmation_services
from apps.delivery.confirmation.scope import note_in_customer_service_scope
from apps.delivery.confirmation.serializers import (
    ConfirmationQueueDetailSerializer,
    ConfirmationQueueItemSerializer,
)
from apps.delivery.models import ConfirmationTask, DeliveryNote


class ConfirmationQueuePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ConfirmationQueueViewSet(NoStoreMixin, viewsets.GenericViewSet):
    """
    ViewSet quản lý hàng chờ CSKH (02b §4.3).
    Hỗ trợ lookup qua note_id hoặc id.
    """
    lookup_field = "note_id"
    pagination_class = ConfirmationQueuePagination
    permission_classes = [IsAuthenticated]
    required_perms: tuple = ()

    def get_queryset(self):
        return ConfirmationTask.objects.select_related(
            "note",
            "note__sales_invoice",
            "note__sales_invoice__sales_order",
            "note__sales_invoice__sales_order__customer",
            "claimed_by",
            "refund",
        )

    def get_object(self):
        lookup_val = self.kwargs.get(self.lookup_field) or self.kwargs.get("pk")
        try:
            val_int = int(lookup_val)
        except (ValueError, TypeError):
            raise Http404("Mục chờ gọi không hợp lệ.")

        task = self.get_queryset().filter(Q(note_id=val_int) | Q(pk=val_int)).first()
        if not task:
            raise Http404("Không tìm thấy mục chờ gọi.")
        return task

    def list(self, request, *args, **kwargs):
        """
        Danh sách hàng chờ CSKH:
        - Mặc định: phiếu CONFIRMING có task PENDING hoặc (CALLBACK và callback_at <= now).
        - Nếu có ?state=: lọc theo state chỉ định.
        """
        if not request.user.has_perm("delivery.confirm_with_customer"):
            raise PermissionDenied("Bạn không có quyền truy cập hàng chờ CSKH.")

        now = timezone.now()
        state = request.query_params.get("state")
        qs = self.get_queryset()

        if state:
            state = state.strip().upper()
            qs = qs.filter(state=state)
            if state in (ConfirmationTask.State.PENDING, ConfirmationTask.State.CALLBACK):
                qs = qs.order_by("note__sales_invoice__issued_at", "id")
            elif state == ConfirmationTask.State.ESCALATED:
                qs = qs.order_by("escalated_at", "id")
            elif state == ConfirmationTask.State.REFUND_CALL:
                qs = qs.order_by("auto_cancelled_at", "created_at", "id")
            else:
                qs = qs.order_by("-updated_at", "-id")
        else:
            # Mặc định: phiếu CONFIRMING có PENDING hoặc (CALLBACK có callback_at <= now)
            qs = qs.filter(
                note__status=DeliveryNote.Status.CONFIRMING,
            ).filter(
                Q(state=ConfirmationTask.State.PENDING)
                | (Q(state=ConfirmationTask.State.CALLBACK) & Q(callback_at__lte=now))
            ).order_by("note__sales_invoice__issued_at", "id")

        page = self.paginate_queryset(qs)
        serializer = ConfirmationQueueItemSerializer(
            page if page is not None else qs,
            many=True,
            context={"request": request, "now": now},
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response({"results": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        """
        Chi tiết mục chờ gọi. Nếu CSKH ngoài phạm vi thì trả 404 (02b §3.2).
        """
        if not request.user.has_perm("delivery.confirm_with_customer"):
            raise PermissionDenied("Bạn không có quyền xem chi tiết đơn CSKH.")

        task = self.get_object()
        now = timezone.now()

        # Kiểm tra Tầng 3 phạm vi dữ liệu cá nhân
        if not note_in_customer_service_scope(request.user, task.note, now=now):
            raise Http404("Không tìm thấy mục chờ gọi trong phạm vi của bạn.")

        serializer = ConfirmationQueueDetailSerializer(
            task, context={"request": request, "now": now}
        )
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="claim")
    def claim(self, request, *args, **kwargs):
        """
        CSKH nhận đơn để xử lý gọi (khoá mềm).
        """
        if not request.user.has_perm("delivery.confirm_with_customer"):
            raise PermissionDenied("Bạn không có quyền nhận xử lý đơn CSKH.")

        task = self.get_object()
        now = timezone.now()
        if not note_in_customer_service_scope(request.user, task.note, now=now):
            raise Http404("Không tìm thấy mục chờ gọi trong phạm vi của bạn.")

        updated_task = confirmation_services.claim_task(task.pk, request.user, now=now)
        display_name = updated_task.claimed_by.get_full_name() or updated_task.claimed_by.username
        return Response(
            {
                "claimed_by": {"id": updated_task.claimed_by_id, "display_name": display_name},
                "claimed_until": updated_task.claimed_until.isoformat(),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="calls")
    def calls(self, request, *args, **kwargs):
        """
        Ghi kết quả cuộc gọi.
        """
        if not request.user.has_perm("delivery.confirm_with_customer"):
            raise PermissionDenied("Bạn không có quyền ghi kết quả cuộc gọi.")

        task = self.get_object()
        now = timezone.now()
        if not note_in_customer_service_scope(request.user, task.note, now=now):
            raise Http404("Không tìm thấy mục chờ gọi trong phạm vi của bạn.")

        data = request.data or {}
        result = data.get("result")
        note_text = data.get("note", "")
        raw_callback_at = data.get("callback_at")
        request_id = data.get("request_id")

        if not result:
            raise BusinessError("Kết quả gọi bắt buộc.", code="INVALID_INPUT")

        callback_at = None
        if raw_callback_at:
            try:
                callback_at = datetime.fromisoformat(str(raw_callback_at).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                raise BusinessError("Giờ hẹn gọi lại không đúng định dạng ISO.", code="INVALID_INPUT")

        call, duplicate = confirmation_services.record_call(
            task.pk,
            request.user,
            result=result,
            note_text=note_text,
            callback_at=callback_at,
            request_id=request_id,
            now=now,
        )

        # Lấy trạng thái mới nhất
        task.refresh_from_db()
        task.note.refresh_from_db()

        confirm_state = None if task.state == ConfirmationTask.State.DONE else task.state
        resp_data = {
            "call_id": call.pk,
            "note_status": task.note.status,
            "confirm_state": confirm_state,
            "attempts": task.attempts,
            "duplicate": duplicate,
        }
        resp_status = status.HTTP_200_OK if duplicate else status.HTTP_201_CREATED
        return Response(resp_data, status=resp_status)

    @action(detail=True, methods=["post"], url_path="unconfirm")
    def unconfirm(self, request, *args, **kwargs):
        """
        Huỷ xác nhận phiếu PREPARING -> CONFIRMING khi chưa in tem.
        """
        if not request.user.has_perm("delivery.confirm_with_customer"):
            raise PermissionDenied("Bạn không có quyền huỷ xác nhận đơn.")

        task = self.get_object()
        now = timezone.now()
        if not note_in_customer_service_scope(request.user, task.note, now=now):
            raise Http404("Không tìm thấy mục chờ gọi trong phạm vi của bạn.")

        # Chỉ người đã xác nhận hoặc có decide_unconfirmed mới được huỷ
        has_decide = request.user.has_perm("delivery.decide_unconfirmed")
        is_confirmer = task.note.confirmed_by_id == request.user.pk
        if not (is_confirmer or has_decide):
            raise PermissionDenied("Chỉ người đã xác nhận hoặc Quản lý mới được huỷ xác nhận.")

        reason = request.data.get("reason", "") if request.data else ""
        note, updated_task = confirmation_services.unconfirm(task.pk, request.user, reason=reason)

        return Response(
            {
                "note_status": note.status,
                "confirm_state": updated_task.state,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="recipient")
    def recipient(self, request, *args, **kwargs):
        """
        Đổi thông tin người nhận hàng hộ và địa chỉ giao hàng (CS-12, 02b §4.5).
        """
        if not request.user.has_perm("delivery.change_recipient"):
            raise PermissionDenied("Bạn không có quyền đổi thông tin nhận hàng.")

        task = self.get_object()
        now = timezone.now()
        if not note_in_customer_service_scope(request.user, task.note, now=now):
            raise Http404("Không tìm thấy mục chờ gọi trong phạm vi của bạn.")

        data = request.data or {}
        delivery_address = data.get("delivery_address")
        recipient_name = data.get("recipient_name")
        recipient_phone = data.get("recipient_phone")

        res = confirmation_services.change_recipient(
            task.pk,
            request.user,
            delivery_address=delivery_address,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
        )
        return Response({
            "changed": res["changed"],
            "label_invalidated": res.get("label_invalidated", False),
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="decide")
    def decide(self, request, *args, **kwargs):
        """
        Quản lý quyết định cho đơn ESCALATED (CS-07, 02b §4.4).
        Quyền: delivery.decide_unconfirmed.
        """
        if not request.user.has_perm("delivery.decide_unconfirmed"):
            raise PermissionDenied("Bạn không có quyền quyết định đơn không xác nhận.")

        task = self.get_object()
        now = timezone.now()
        if not note_in_customer_service_scope(request.user, task.note, now=now):
            raise Http404("Không tìm thấy mục chờ gọi trong phạm vi của bạn.")

        data = request.data or {}
        decision = data.get("decision")
        if not decision:
            raise BusinessError("Quyết định bắt buộc.", code="INVALID_INPUT")

        reason = data.get("reason", "")
        reason_code = data.get("reason_code", "")
        note = data.get("note", "")
        raw_until = data.get("until")

        until = None
        if raw_until:
            try:
                until = datetime.fromisoformat(str(raw_until).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                raise BusinessError("Giờ gia hạn không đúng định dạng ISO.", code="INVALID_INPUT")

        res = confirmation_services.decide(
            task.pk,
            request.user,
            decision=decision,
            reason=reason,
            until=until,
            reason_code=reason_code,
            note=note,
            now=now,
        )
        return Response(res, status=status.HTTP_200_OK)


class CustomerSearchView(NoStoreMixin, APIView):
    """
    Tìm kiếm nhanh đơn hàng cho CSKH (02b §4.3).
    - Chỉ nhận POST (GET trả 405)
    - Throttle customer_search
    - Chống rò PII ngoài phạm vi
    """
    throttle_classes = [CustomerSearchThrottle]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        raise MethodNotAllowed("GET")

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm("delivery.confirm_with_customer"):
            raise PermissionDenied("Bạn không có quyền tìm kiếm đơn CSKH.")

        raw_q = (request.data.get("q") if request.data else "") or ""
        raw_q = str(raw_q).strip()
        if not raw_q:
            raise BusinessError("Nhập đủ số điện thoại hoặc đúng mã đơn.", code="INVALID_QUERY")

        norm_phone = normalize_phone(raw_q)
        digits_only = re.sub(r"\D", "", raw_q)

        # 1. Nếu có >= 9 chữ số -> tìm đúng SĐT
        if len(norm_phone) >= 9 and norm_phone.isdigit():
            notes = list(
                DeliveryNote.objects.select_related(
                    "sales_invoice", "sales_invoice__sales_order", "sales_invoice__sales_order__customer"
                ).filter(
                    Q(sales_invoice__sales_order__phone=norm_phone)
                    | Q(recipient_phone=norm_phone)
                ).order_by("-created_at", "-id")[:20]
            )
        else:
            # Nếu người dùng gõ chuỗi chữ số nhưng < 9 chữ số -> báo lỗi INVALID_QUERY
            if digits_only and len(digits_only) < 9 and not (raw_q.upper().startswith("DH") or raw_q.upper().startswith("SO")):
                raise BusinessError("Nhập đủ số điện thoại hoặc đúng mã đơn.", code="INVALID_QUERY")

            # Ngược lại: tìm theo mã đơn (không phân biệt hoa thường)
            notes = list(
                DeliveryNote.objects.select_related(
                    "sales_invoice", "sales_invoice__sales_order", "sales_invoice__sales_order__customer"
                ).filter(
                    sales_invoice__sales_order__code__iexact=raw_q
                ).order_by("-created_at", "-id")[:20]
            )

        now = timezone.now()
        results = []
        for note in notes:
            order = getattr(note.sales_invoice, "sales_order", None)
            if not order:
                continue
            in_scope = note_in_customer_service_scope(request.user, note, now=now)
            customer = getattr(order, "customer", None)
            order_phone = order.phone or (customer.phone if customer else "")
            actual_phone = note.recipient_phone or order_phone

            item = {
                "note_id": note.pk,
                "order_code": order.code,
                "status_label": note.get_status_display(),
                "in_scope": in_scope,
            }
            if in_scope:
                item["customer_name"] = note.recipient_name or (customer.name if customer else "")
                item["phone"] = actual_phone
            else:
                item["phone_masked"] = mask_phone(actual_phone)

            results.append(item)

        return Response({"results": results}, status=status.HTTP_200_OK)

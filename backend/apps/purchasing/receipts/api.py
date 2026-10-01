from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.ai.declare import AiMeta
from apps.common.api import BusinessModelPermissions, DocumentViewSet, require_perm
from apps.purchasing.models import PurchaseReceipt, Supplier

from . import services
from .serializers import (
    ReceivedBatchOutput,
    ReceiveBatchesInput,
    PurchaseReceiptSerializer,
    SupplierSerializer,
)


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [BusinessModelPermissions]


class PurchaseReceiptViewSet(DocumentViewSet):
    queryset = PurchaseReceipt.objects.prefetch_related("lines").all()
    serializer_class = PurchaseReceiptSerializer
    permission_classes = [BusinessModelPermissions]
    custom_perm_actions = ("submit", "receive_batches", "cancel")
    locked_fields = ("status",)  # BR-PQ-14: ghi nhận qua action submit
    actor_fields = ("created_by",)  # BR-PQ-16

    @action(detail=True, methods=["post"], required_perms=("purchasing.change_purchasereceipt",))
    def submit(self, request, pk=None):
        """Xác nhận phiếu nhập hàng và sinh các lô cá tương ứng."""
        # Sinh lô từ các dòng nhập (cần quyền change phiếu — Tầng 1 đã chặn).
        require_perm(request.user, "purchasing.change_purchasereceipt")
        batches = services.submit_receipt(receipt=self.get_object(), actor=request.user)
        return Response(
            {"receipt": self.get_serializer(self.get_object()).data,
             "batches_created": [b.batch_id for b in batches]}
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="cancel",
        required_perms=("purchasing.change_purchasereceipt",),
    )
    def cancel(self, request, pk=None):
        """Huỷ phiếu nhập kho khi mọi lô còn Nháp (BR-MH-07)."""
        require_perm(request.user, "purchasing.change_purchasereceipt")
        receipt = self.get_object()
        services.cancel_receipt(receipt=receipt, actor=request.user)
        return Response({"id": receipt.id, "status": "CANCELLED"}, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        url_path="receive-batches",
        required_perms=("purchasing.add_purchasereceipt", "purchasing.change_purchasereceipt"),
        input_serializer=ReceiveBatchesInput,
        ai=AiMeta(
            title="Nhập lô mua tại cảng",
            keywords=("nhập lô", "nhập hàng", "mua cá"),
            max_level="B",
            undo="cancel_action:cancel",
            limits={"lines[].qty": "kg", "lines[].amount": "vnd"},
        ),
    )
    def receive_batches(self, request):
        """Nhập lô mua tại cảng — mỗi dòng sinh một lô (BR-MH-01)."""
        require_perm(request.user, "purchasing.add_purchasereceipt")
        require_perm(request.user, "purchasing.change_purchasereceipt")
        serializer = ReceiveBatchesInput(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        receipt, batches = services.create_and_submit_receipt(
            **serializer.validated_data,
            actor=request.user,
        )
        receipt_data = PurchaseReceiptSerializer(receipt, context=self.get_serializer_context()).data
        batches_data = ReceivedBatchOutput(batches, many=True, context=self.get_serializer_context()).data
        return Response(
            {"receipt": receipt_data, "batches": batches_data},
            status=status.HTTP_201_CREATED,
        )

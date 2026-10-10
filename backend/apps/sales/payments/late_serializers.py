"""
Input của `POST /api/sales/payments/record-late/` (#15, BR-TT-18).

Các CharField lỏng để service kiểm và trả lỗi BR-TT-18 thống nhất (khoá lỗi trùng tên ô), theo mẫu
`ReturnToSupplierInput`. KHÔNG có field ghi chú, nguồn, loại khoản hay đơn: khoá lạ bị bỏ qua (bất biến 9).
"""
from rest_framework import serializers


class RecordLatePaymentInput(serializers.Serializer):
    bank_txn_id = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="Mã GD ngân hàng (FT…)")
    amount = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="Số tiền (đ)")
    received_at = serializers.CharField(required=False, allow_blank=True, allow_null=True, help_text="Giờ nhận, ISO 8601")
    order_code = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, help_text="Mã đơn Đã huỷ/Tự huỷ; bỏ trống = không gắn đơn",
    )
    acknowledge_possible_duplicate = serializers.BooleanField(
        required=False, default=False, help_text="Đã đối chiếu sao kê, đây là khoản khác",
    )

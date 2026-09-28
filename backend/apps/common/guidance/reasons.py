"""
Bảng câu "vì sao" theo mã BR (BR-AI-32) cho Tiếp theo · Đã làm.

Bất biến:
- Mỗi mã BR có đúng 1 câu soạn sẵn.
- Tuyệt đối không chứa số tiền ở bất kỳ câu nào (DW-03-AC10).
"""

REASONS: dict[str, str] = {
    # Thanh toán
    "BR-TT-07": "Thanh toán tay cần Chủ xác nhận để đảm bảo đối soát ngân hàng",
    "BR-TT-05": "Đơn không ở trạng thái có thể xác nhận thanh toán",
    "BR-TT-08": "Đơn quá hạn giữ chỗ cần đối soát trước khi khôi phục hoặc huỷ",
    # Bán hàng & Đơn hàng
    "BR-BH-04": "Hệ thống tự động huỷ đơn quá hạn giữ chỗ để nhả hàng cho khách khác",
    "BR-GH-07": "Không thể huỷ đơn khi hàng đang giao hoặc đã hoàn tất",
    # Hoàn tiền
    "BR-HT-03": "Cần mã giao dịch chuyển khoản trước khi xác nhận hoàn tiền",
    "BR-HT-04": "Chỉ tạo phiếu hoàn khi hoá đơn còn khoản có thể hoàn",
    "BR-HT-07": "Chỉ Chủ vựa mới có quyền xác nhận hoàn tiền",
    "BR-HT-08": "Phiếu hoàn đã được xử lý hoặc không còn ở trạng thái chờ",
    # Quản lý kho & Lô
    "BR-LO-02": "Lô hết hạn sẽ tự động chuyển sang trạng thái Quá hạn",
    "BR-LO-03": "Chỉ huỷ được lô khi đã ở trạng thái Quá hạn",
    "BR-LO-04": "Lô chỉ chốt khi không còn đơn mở và phiếu chờ xử lý",
    "BR-LO-05": "Lô đã chốt không thể thay đổi trạng thái",
    "BR-LO-06": "Lô gần hết hạn sẽ tự động chuyển trạng thái Cận hạn",
    "BR-KK-05": "Lô phải được kiểm kê và duyệt trước khi chốt",
    # Phân quyền & AI
    "BR-PQ-12": "Người dùng không đủ quyền thực hiện thao tác này",
    "BR-AI-28": "Bước tiếp theo cần thực hiện theo quy trình chuẩn",
    "BR-AI-29": "Điều kiện nghiệp vụ chưa thoả mãn để thực hiện thao tác",
    "BR-AI-30": "Dòng thời gian ghi nhận các sự kiện chính của chứng từ",
    "BR-AI-32": "Lý do được chuẩn hoá theo quy tắc nghiệp vụ",
    "BR-AI-33": "Cảnh báo chứng từ cần được lưu ý xử lý",
}


def get_reason(code: str, default: str = "") -> str:
    """Lấy câu giải thích chuẩn theo mã BR."""
    return REASONS.get(code, default or f"Theo quy tắc nghiệp vụ {code}")

// Thông báo của màn Danh mục (kết quả thao tác, trạng thái) — MỘT chỗ, component không viết chuỗi tại chỗ.
// Lỗi nghiệp vụ (định dạng, dung lượng, quyền, xung đột…) KHÔNG ở đây: UI hiện nguyên văn `detail` BE trả
// (BR-DM-10/11/12/16, BR-PQ-12) — xem shared/lib/messages.ts `errorText()`.

export const CATALOG_MSG = {
  uploaded: (name: string) => `Đã lưu ảnh cho ${name}.`,
  noImagePermissionHint: "Cần Chủ vựa cấp quyền đổi ảnh mặt hàng.",
  privacyReminder: "Không chụp bảng giá, hoá đơn, tên đầu mối.",
  chooseFile: "Chọn ảnh hoặc chụp bằng camera",
  changeFile: "Chọn ảnh khác",
  dropHint: "JPEG, PNG hoặc WebP, tối đa 10 MB.",
  /** A2-AC12: mất mạng giữa chừng — phân biệt ApiError status 0 (xem shared/lib/http.ts loadErrorText). */
  networkDrop: "Tải ảnh chưa xong, ảnh cũ vẫn giữ nguyên.",
  emptyTitle: "Chưa có mặt hàng nào",
  emptyHint: "Mặt hàng được tạo ở Mua hàng hoặc dữ liệu ban đầu sẽ hiện ở đây.",
  emptyFilteredTitle: "Không còn mặt hàng thiếu ảnh",
  emptyFilteredHint: "Mọi mặt hàng đang bán đều đã có ảnh — bỏ bộ lọc để xem toàn bộ danh mục.",
  imageOf: (name: string) => `Ảnh mặt hàng ${name}`,
  illustrationLabel: "Ảnh minh hoạ",
  lowResWarning: "Ảnh nhỏ hơn 600 px, trên Shop có thể bị mờ.",
} as const;

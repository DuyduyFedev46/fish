/**
 * Chữ tạm của trang chủ (banner, dải cam kết). Chỉ dùng câu "ĐÃ ĐỐI CHIẾU" của 06-marketing C5/H*.
 * KHÔNG có "Cân đúng" (S-18, SHOP-1-06 AC9) và không hứa phí giao. SHOP-5-03 chuyển phần này sang CMS rồi xoá file.
 */

export const HOME_BANNER = {
  eyebrow: "Từ cảng về bếp nhà bạn",
  title: "Mua theo lô tại cảng",
  /** Câu phụ chỉ hiện ở máy tính. */
  subtitle: "Hải sản cấp đông, mua theo lô tại cảng.",
  buttonDesktop: "Xem hàng đang có",
  buttonMobile: "Xem hàng",
};

export const HOME_PAYMENT_TILE = {
  eyebrow: "Chuyển khoản quét mã QR",
  title: "Tiền về đủ là đơn tự xác nhận",
  note: "Quét bằng app ngân hàng của bạn",
};

export type HomeCommitment = {
  key: string;
  icon: "snowflake" | "truck" | "qr";
  /** Tiêu đề ngắn (điện thoại chỉ hiện tiêu đề). */
  title: string;
  /** Mô tả (chỉ hiện ở máy tính). */
  detail: string;
  /** true: ô chỉ có ở điện thoại. */
  mobileOnly?: boolean;
};

// Điện thoại 3 ô, máy tính 2 ô (02a §7.3; 02b §9). Ô thứ ba của điện thoại là ô thanh toán.
export const HOME_COMMITMENTS: HomeCommitment[] = [
  { key: "lot", icon: "snowflake", title: "Cấp đông theo lô", detail: "Mua tại cảng, mỗi lô có hạn dùng riêng" },
  { key: "delivery", icon: "truck", title: "Giao tận nhà", detail: "Trả một lần qua mã QR, không thu thêm khi giao" },
  { key: "qr", icon: "qr", title: "Quét mã QR", detail: "", mobileOnly: true },
];

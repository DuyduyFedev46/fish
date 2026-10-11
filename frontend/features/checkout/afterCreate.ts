/**
 * SHOP-FIX-01: sau khi tạo đơn ở form đặt hàng. Thuần TypeScript để test không cần build.
 * `pay=failed` chỉ là cờ báo mở cổng lỗi (không chứa dữ liệu cá nhân).
 */
export const OPEN_FAILED_MESSAGE = "Chưa mở được trang thanh toán. Thử lại.";

/** Địa chỉ trang đơn; `openFailed` thì kèm cờ để D1 hiện câu lỗi và nút "Thanh toán". */
export function orderUrl(orderCode: string, openFailed: boolean): string {
  const base = `/shop/orders/?code=${encodeURIComponent(orderCode)}`;
  return openFailed ? `${base}&pay=failed` : base;
}

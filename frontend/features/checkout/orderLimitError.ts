// Ba mã lỗi giới hạn khi đặt đơn (đợt rà soát bảo mật 15/11). Câu hiển thị lấy từ `detail` máy chủ trả về,
// không có thì dùng câu dự phòng. Hàm thuần, không gọi API.

export const ORDER_LIMIT_CODES = ["ORDER_LINE_TOO_LARGE", "ORDER_TOO_LARGE", "TOO_MANY_OPEN_ORDERS"] as const;

export const ORDER_LIMIT_FALLBACK = "Đơn vượt giới hạn đặt online, vui lòng gọi hotline để được hỗ trợ";

export function isOrderLimitCode(code: string | undefined | null): boolean {
  return !!code && (ORDER_LIMIT_CODES as readonly string[]).includes(code);
}

/** Câu tiếng Việt cho mã giới hạn đơn; `null` nếu không phải ba mã này. */
export function orderLimitMessage(code: string | undefined | null, detail: string | undefined | null): string | null {
  if (!isOrderLimitCode(code)) return null;
  const text = (detail ?? "").trim();
  return text || ORDER_LIMIT_FALLBACK;
}

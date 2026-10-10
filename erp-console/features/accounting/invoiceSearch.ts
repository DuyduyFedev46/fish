// Ô tìm Hoá đơn bán (Lô 17b G6, QA12-N5): chỉ gửi chuỗi giống MÃ (hoá đơn, đơn) lên BE. Dãy từ 9 chữ số (giống số điện thoại) không bao giờ
// rời máy: tìm bằng GET đưa chuỗi vào URL và access log, mà số điện thoại khách là dữ liệu cá nhân (bất biến 9). Giống ô tra tem ở Giao hàng.

export const INVOICE_SEARCH_PII_MESSAGE = "Ô này chỉ tìm theo mã hoá đơn hoặc mã đơn, không tìm theo số điện thoại.";

/** Dãy chữ số từ `minLen` trở lên (bỏ qua dấu cách . - _ / giữa các số). */
export function looksLikePhone(text: string, minLen = 9): boolean {
  return new RegExp(`\\d{${minLen},}`).test(text.replace(/[\s.\-_/]/g, ""));
}

/** `term` = chuỗi được phép gửi ("" nếu bị chặn); `blocked` = báo câu cảnh báo dưới ô. */
export function invoiceSearchTerm(raw: string): { term: string; blocked: boolean } {
  const t = raw.trim();
  return looksLikePhone(t) ? { term: "", blocked: true } : { term: t, blocked: false };
}

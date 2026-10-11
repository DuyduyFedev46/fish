// Mã giảm giá khách đã áp, lưu cùng giỏ trong trình duyệt (COMPONENTS #48 mục 7). Chỉ lưu CHUỖI MÃ (vd. một mã công khai),
// không lưu số tiền giảm (máy chủ tính lại mỗi lần) và không bao giờ có tên, SĐT hay địa chỉ (bất biến 9).
// SHOP-3b-05.

const KEY = "cart_voucher_code_v1";

export function readVoucherCode(): string | null {
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw && /^[A-Z0-9]{1,20}$/.test(raw) ? raw : null;
  } catch {
    return null;
  }
}

export function writeVoucherCode(code: string): void {
  try {
    window.localStorage.setItem(KEY, code);
  } catch {
    // Không lưu được: mã chỉ sống trong phiên trang này.
  }
}

export function clearVoucherCode(): void {
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    // bỏ qua
  }
}

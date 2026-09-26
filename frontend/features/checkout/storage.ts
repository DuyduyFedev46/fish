// Nhớ tạm mã đơn + 4 số cuối SĐT trong phiên trình duyệt (sessionStorage), để khách quay
// về từ cổng thanh toán không phải gõ lại số điện thoại trên trang tra đơn (spec §7.1,
// PA). Dữ liệu không nhạy cảm (chỉ 4 số cuối), và tự mất khi đóng tab.

const STORAGE_KEY = "cangcaloc_last_order_contact_v1";

type StoredContact = { order_code: string; phone_last4: string };

export function rememberOrderContact(orderCode: string, phoneLast4: string): void {
  if (typeof window === "undefined") return;
  try {
    const value: StoredContact = { order_code: orderCode, phone_last4: phoneLast4 };
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } catch {
    // sessionStorage không khả dụng — khách sẽ tự gõ lại, không chặn luồng chính.
  }
}

export function recallOrderContact(orderCode: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const value = JSON.parse(raw) as StoredContact;
    if (value.order_code !== orderCode) return null;
    return value.phone_last4;
  } catch {
    return null;
  }
}

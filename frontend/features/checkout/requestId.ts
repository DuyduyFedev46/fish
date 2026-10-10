// Mã yêu cầu đặt đơn (`client_request_id`, BR-BH-27): chống tạo đơn trùng khi mất mạng hoặc bấm đúp.
// Sinh một lần khi mở /shop/checkout/, giữ trong sessionStorage kèm "vân tay" giỏ để F5 giữa chừng không sinh mã mới;
// đổi giỏ thì sinh mã mới; xoá khi tạo đơn thành công. Chỉ chứa UUID và vân tay (mã hàng + số lượng), không dữ liệu khách.

const KEY = "cangcaloc_checkout_request_v1";

type Stored = { id: string; cart_fingerprint: string };

/** UUID v4. `crypto.randomUUID` chỉ có trong ngữ cảnh an toàn (HTTPS, localhost); thiếu thì tự dựng từ `getRandomValues`. */
export function newUuid(): string {
  const c = typeof crypto !== "undefined" ? crypto : undefined;
  if (c && typeof c.randomUUID === "function") return c.randomUUID();
  const bytes = new Uint8Array(16);
  if (c && typeof c.getRandomValues === "function") c.getRandomValues(bytes);
  else for (let i = 0; i < 16; i++) bytes[i] = Math.floor(Math.random() * 256);
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/** Vân tay của giỏ: mã hàng và số lượng, đã sắp xếp. Đổi giỏ thì khác vân tay. */
export function cartFingerprint(items: { item_code: string; qty: string }[]): string {
  return [...items]
    .map((i) => `${i.item_code}:${i.qty}`)
    .sort()
    .join("|");
}

function read(): Stored | null {
  try {
    const raw = window.sessionStorage.getItem(KEY);
    if (!raw) return null;
    const v = JSON.parse(raw) as Partial<Stored>;
    return typeof v.id === "string" && typeof v.cart_fingerprint === "string" ? (v as Stored) : null;
  } catch {
    return null;
  }
}

function write(value: Stored): void {
  try {
    window.sessionStorage.setItem(KEY, JSON.stringify(value));
  } catch {
    // sessionStorage không dùng được: mã chỉ sống trong bộ nhớ của lần gọi này.
  }
}

/** Mã đang giữ cho giỏ này; chưa có hoặc giỏ đã đổi thì sinh mới. */
export function getRequestId(fingerprint: string): string {
  const stored = typeof window === "undefined" ? null : read();
  if (stored && stored.cart_fingerprint === fingerprint) return stored.id;
  const fresh = { id: newUuid(), cart_fingerprint: fingerprint };
  if (typeof window !== "undefined") write(fresh);
  return fresh.id;
}

/** Sinh mã mới ngay (đặt lại không dùng mã giảm giá, 3b). */
export function renewRequestId(fingerprint: string): string {
  const fresh = { id: newUuid(), cart_fingerprint: fingerprint };
  if (typeof window !== "undefined") write(fresh);
  return fresh.id;
}

/** Xoá sau khi tạo đơn thành công (201 hoặc 200). */
export function clearRequestId(): void {
  try {
    window.sessionStorage.removeItem(KEY);
  } catch {
    // bỏ qua
  }
}

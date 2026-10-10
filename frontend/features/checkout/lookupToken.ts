// Mã tra đơn (`lookup_token`, 02b §3.4.1 và §1.7): chữ ký của máy chủ, chỉ chứa mã đơn và mốc giờ, KHÔNG chứa SĐT, tên hay địa chỉ.
// Giữ trong sessionStorage (tự mất khi đóng tab) với khoá tiếng Anh, tối đa 5 đơn; không có "đơn gần đây" trong localStorage.
// Token không bao giờ nằm trên URL.

const KEY = "cangcaloc_order_tokens_v1";
/** Khoá cũ lưu 4 số cuối SĐT (bản Shop trước lô 3+4): xoá đi khi trang đơn mở (02b §1.7). */
const LEGACY_KEY = "cangcaloc_last_order_contact_v1";
const MAX_TOKENS = 5;

type TokenMap = Record<string, string>;

function read(): TokenMap {
  try {
    const raw = window.sessionStorage.getItem(KEY);
    if (!raw) return {};
    const v = JSON.parse(raw) as unknown;
    if (!v || typeof v !== "object" || Array.isArray(v)) return {};
    const out: TokenMap = {};
    for (const [k, val] of Object.entries(v as Record<string, unknown>)) {
      if (typeof val === "string" && val) out[k] = val;
    }
    return out;
  } catch {
    return {};
  }
}

function write(map: TokenMap): void {
  try {
    window.sessionStorage.setItem(KEY, JSON.stringify(map));
  } catch {
    // sessionStorage không dùng được: khách sẽ nhập lại SĐT, không chặn luồng chính.
  }
}

export function saveLookupToken(orderCode: string, token: string): void {
  if (typeof window === "undefined" || !orderCode || !token) return;
  const map = read();
  delete map[orderCode]; // đưa đơn này về cuối (mới nhất)
  map[orderCode] = token;
  const keys = Object.keys(map);
  for (const old of keys.slice(0, Math.max(0, keys.length - MAX_TOKENS))) delete map[old];
  write(map);
}

export function readLookupToken(orderCode: string): string | null {
  if (typeof window === "undefined") return null;
  return read()[orderCode] ?? null;
}

/** Token hết hạn hoặc bị từ chối (401): xoá mục đó. */
export function removeLookupToken(orderCode: string): void {
  if (typeof window === "undefined") return;
  const map = read();
  if (!(orderCode in map)) return;
  delete map[orderCode];
  write(map);
}

/** Dọn khoá cũ có 4 số cuối SĐT. */
export function clearLegacyContact(): void {
  try {
    window.sessionStorage.removeItem(LEGACY_KEY);
  } catch {
    // bỏ qua
  }
}

/**
 * Link Facebook của shop (FB-01). File thuần TypeScript, không import gì (test bằng `scripts/test-facebook.mjs`).
 * Chỉ nhận `https://` với host facebook.com, www.facebook.com, m.facebook.com, fb.com, fb.me.
 * Chuỗi khác (chữ giữ chỗ như "[Link fanpage Facebook]", "javascript:...") không phải link: UI hiện chữ thường.
 */
const FACEBOOK_HOSTS = ["facebook.com", "www.facebook.com", "m.facebook.com", "fb.com", "fb.me"];

export function facebookHrefOf(raw?: string | null): string | undefined {
  const v = (raw ?? "").trim();
  if (!v || v.length > 2000 || /[\s\u0000-\u001f\u007f-\u009f]/.test(v)) return undefined;
  if (!/^https:\/\//i.test(v)) return undefined;
  let url: URL;
  try {
    url = new URL(v);
  } catch {
    return undefined;
  }
  if (url.protocol !== "https:" || url.username || url.password) return undefined;
  return FACEBOOK_HOSTS.includes(url.hostname.toLowerCase()) ? v : undefined;
}

/** Chữ hiển thị khi giá trị khác rỗng nhưng không phải link hợp lệ; rỗng thì undefined (ẩn dòng). */
export function facebookPlainTextOf(raw?: string | null): string | undefined {
  const v = (raw ?? "").trim();
  if (!v || facebookHrefOf(v)) return undefined;
  return v;
}

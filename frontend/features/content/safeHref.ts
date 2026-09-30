/**
 * Kiểm tra href an toàn chống XSS / open-redirect cho nội dung bài viết công khai
 * (§6.3 02b-tech-design, CMS-13-AC3, SR-23 F2).
 *
 * Luật này được chép NGUYÊN sang bản ERP (`erp-console/features/content/editor/safeHref.ts`, SR-23 F2); hai app
 * không import chéo nhau nên sửa một bên phải sửa bên kia. Cả hai chạy chung bộ 40 payload
 * (`scripts/test-safe-href.mjs` ở Shop, `safeHref.test.ts` ở ERP):
 *  - bỏ khoảng trắng đầu/cuối; rỗng hoặc dài hơn 2000 ký tự -> từ chối;
 *  - có khoảng trắng hoặc ký tự điều khiển (kể cả DEL và C1 0x80-0x9F) BÊN TRONG -> từ chối (chặn "java\tscript:");
 *  - neo trong trang bắt đầu bằng "#" -> nhận;
 *  - đường dẫn nội bộ bắt đầu bằng "/" nhưng KHÔNG được là "//..." hoặc "/\..." (protocol-relative);
 *  - còn lại phải có giao thức tường minh, chỉ nhận https:, http:, mailto:, tel:. Href không có giao thức
 *    (ví dụ "abc", "\\evil.example" mà trình duyệt hiểu là "//evil.example") bị từ chối.
 *
 * File thuần TypeScript, không import gì, để `scripts/test-safe-href.mjs` chạy được không cần build.
 */

const SAFE_PROTOCOLS = ["https:", "http:", "mailto:", "tel:"];
const MAX_HREF_LENGTH = 2000;
const SCHEME_RE = /^([a-z][a-z0-9+.-]*):/i;

export function isSafeHref(href?: string): boolean {
  if (typeof href !== "string") return false;
  const clean = href.trim();
  if (!clean || clean.length > MAX_HREF_LENGTH) return false;

  // Khoảng trắng / ký tự điều khiển bên trong (kể cả tab, xuống dòng, NUL, DEL, C1).
  for (let i = 0; i < clean.length; i++) {
    const code = clean.charCodeAt(i);
    if (code <= 32 || (code >= 127 && code <= 159)) return false;
  }

  // Neo trong trang.
  if (clean.startsWith("#")) return true;

  // Đường dẫn nội bộ: cấm "//host" và "/\host".
  if (clean.startsWith("/")) {
    return !(clean[1] === "/" || clean[1] === "\\");
  }

  // Còn lại phải có giao thức tường minh và nằm trong danh sách trắng.
  const match = SCHEME_RE.exec(clean);
  if (!match) return false;
  return SAFE_PROTOCOLS.includes(`${match[1].toLowerCase()}:`);
}

/** Link ra ngoài (http/https) -> mở tab mới kèm `rel="nofollow noopener noreferrer"`. */
export function isExternalLink(href?: string): boolean {
  if (typeof href !== "string") return false;
  return /^https?:/i.test(href.trim());
}

/** Link nội bộ của Shop (đường dẫn "/..." hoặc neo "#...") -> dùng `next/link`. */
export function isInternalLink(href?: string): boolean {
  if (typeof href !== "string") return false;
  const clean = href.trim();
  return clean.startsWith("/") || clean.startsWith("#");
}

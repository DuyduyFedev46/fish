/**
 * Kiểm tra href an toàn chống XSS / open-redirect cho nội dung bài viết
 * (§6.1 / §6.2 02b-tech-design, CMS-13-AC3, SR-23 F2).
 *
 * Chép NGUYÊN luật của Shop (`frontend/features/content/safeHref.ts`); hai app không import chéo nhau
 * nên nếu sửa một bên phải sửa bên kia. Cả hai chạy chung bộ 40 payload (`safeHref.test.ts` ở đây,
 * `frontend/scripts/test-safe-href.mjs` ở Shop).
 *
 *  - bỏ khoảng trắng đầu/cuối; rỗng hoặc dài hơn 2000 ký tự -> từ chối;
 *  - có khoảng trắng hoặc ký tự điều khiển (kể cả DEL và C1 0x80-0x9F) BÊN TRONG -> từ chối
 *    (chặn "java\tscript:");
 *  - neo trong trang bắt đầu bằng "#" -> nhận;
 *  - đường dẫn nội bộ bắt đầu bằng "/" nhưng KHÔNG được là "//..." hoặc "/\..." (protocol-relative);
 *  - còn lại phải có giao thức tường minh, chỉ nhận https:, http:, mailto:, tel:.
 *
 * Bản cũ đem href không có giao thức cho `new URL(...)` phân giải theo https nên nhận nhầm "abc" và
 * "\\evil.example" (trình duyệt hiểu là "//evil.example"), và bỏ sót ký tự điều khiển C1.
 *
 * File thuần TypeScript, không import gì.
 */

const SAFE_PROTOCOLS = ["https:", "http:", "mailto:", "tel:"];
const MAX_HREF_LENGTH = 2000;
const SCHEME_PATTERN = /^([a-z][a-z0-9+.-]*):/i;

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
  const match = SCHEME_PATTERN.exec(clean);
  if (!match) return false;
  return SAFE_PROTOCOLS.includes(`${match[1].toLowerCase()}:`);
}

/** Link ra ngoài (http/https) -> Shop mở tab mới kèm `rel="nofollow noopener noreferrer"`. Giữ song song với Shop. */
export function isExternalLink(href?: string): boolean {
  if (typeof href !== "string") return false;
  return /^https?:/i.test(href.trim());
}

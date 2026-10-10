// Tiêu đề tab và thẻ robots cho trang CMS dựng phía trình duyệt (/pages/?slug=, /blog/?slug=) — QA lô 2 L3.
// Static export không có metadata theo slug, nên đặt lúc chạy. Luôn giữ đúng MỘT thẻ <meta name="robots">.

const BRAND = "Cá Về";
const OWNED_ATTR = "data-content-robots";

export const NOT_FOUND_TITLE = `Không tìm thấy trang | ${BRAND}`;
export const GONE_TITLE = `Trang này không còn trên web | ${BRAND}`;
export const LOAD_ERROR_TITLE = `Chưa tải được trang | ${BRAND}`;

/** Ghép hậu tố thương hiệu, không lặp khi tiêu đề CMS đã có "Cá Về" (QA lô 1 L2). */
export function withBrand(title: string): string {
  const clean = title.trim();
  if (!clean) return BRAND;
  return clean.includes(BRAND) ? clean : `${clean} | ${BRAND}`;
}

/** Đặt tiêu đề tab; `noindex` = true thì có đúng một thẻ robots "noindex", false thì gỡ thẻ do module này thêm. */
export function setPageMeta({ title, noindex }: { title: string; noindex: boolean }): void {
  if (typeof document === "undefined") return;
  document.title = title;
  const existing = Array.from(document.head.querySelectorAll('meta[name="robots"]'));
  if (noindex) {
    const [first, ...rest] = existing;
    rest.forEach((el) => el.remove());
    const meta = first ?? document.createElement("meta");
    meta.setAttribute("name", "robots");
    meta.setAttribute("content", "noindex");
    meta.setAttribute(OWNED_ATTR, "1");
    if (!first) document.head.appendChild(meta);
  } else {
    existing.filter((el) => el.hasAttribute(OWNED_ATTR)).forEach((el) => el.remove());
  }
}

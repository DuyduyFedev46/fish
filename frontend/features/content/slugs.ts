// Slug trang CMS là dữ liệu, giữ tiếng Việt (decisions 2026-10-11). URL Shop tiếng Anh: `/pages/?slug=`, `/blog/?slug=`.

export const CONTACT_SLUG = "lien-he";
export const HOW_TO_BUY_SLUG = "cach-mua-hang";
export const SHIPPING_SLUG = "giao-hang"; // naming: allow - slug trang CMS là dữ liệu, giữ tiếng Việt (decisions 2026-10-11)
export const RETURNS_SLUG = "doi-tra";

export const policyHref = (slug: string) => `/pages/?slug=${encodeURIComponent(slug)}`;
export const postHref = (slug: string) => `/blog/?slug=${encodeURIComponent(slug)}`;
export const categoryHref = (slug: string) => `/blog/?category=${encodeURIComponent(slug)}`;

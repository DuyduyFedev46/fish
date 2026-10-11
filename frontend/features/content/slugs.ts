// Slug trang CMS là dữ liệu, giữ tiếng Việt (decisions 2026-10-11). URL Shop tiếng Anh: `/pages/?slug=`, `/blog/?slug=`.

export const CONTACT_SLUG = "lien-he";
export const HOW_TO_BUY_SLUG = "cach-mua-hang";
export const SHIPPING_SLUG = "giao-hang"; // naming: allow - slug trang CMS là dữ liệu, giữ tiếng Việt (decisions 2026-10-11)
export const RETURNS_SLUG = "doi-tra";

export const policyHref = (slug: string) => `/pages/?slug=${encodeURIComponent(slug)}`;
export const postHref = (slug: string) => `/blog/?slug=${encodeURIComponent(slug)}`;
export const categoryHref = (slug: string) => `/blog/?category=${encodeURIComponent(slug)}`;

// Hai trang cố định của trang chủ (SHOP-5-03; 02b §3.7.2): không ở footer, Lộc sửa ở màn Nội dung ERP.
export const HOME_BANNER_SLUG = "home-banner";
export const HOME_COMMITMENTS_SLUG = "home-commitments";

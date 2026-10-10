/**
 * Đích điều hướng dùng chung của khung Shop (header, thanh đáy, footer).
 * Nút giỏ (header, thanh đáy, CartBar, MiniCart) đi tới trang giỏ hàng riêng (SHOP-2-06 AC9).
 */
export const CART_HREF = "/shop/cart/";
export const CATALOG_HREF = "/shop/";
export const ORDERS_HREF = "/shop/orders/";
export const KITCHEN_HREF = "/blog/";
export const ABOUT_HREF = "/about/";
export const HOW_TO_BUY_HREF = "/pages/?slug=cach-mua-hang";
export const CONTACT_HREF = "/pages/?slug=lien-he";

/** Đường dẫn trang nhóm hàng: combo lọc theo loại, còn lại theo slug nhóm. */
export function groupHref(slug: string): string {
  return slug === "combo" ? "/shop/?type=combo" : `/shop/?group=${encodeURIComponent(slug)}`;
}

/** Chuẩn hoá số điện thoại cho href="tel:" (chỉ giữ chữ số và dấu +). */
export function telHref(phone: string): string {
  return `tel:${phone.replace(/[^\d+]/g, "")}`;
}

/** Đích nút "Liên hệ chúng tôi": gọi hotline nếu có số hợp lệ, không thì trang Liên hệ (không bao giờ ẩn nút). */
export function contactTarget(hotline?: string | null): string {
  return hotline ? telHref(hotline) : CONTACT_HREF;
}

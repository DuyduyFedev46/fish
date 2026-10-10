/**
 * Đích điều hướng dùng chung của khung Shop (header, thanh đáy, footer).
 * Lô 1: giỏ chưa có trang riêng nên nút giỏ đi tới /shop/checkout/ (SHOP-1-03 AC8); lô 2 đổi thành /shop/cart/.
 */
export const CART_HREF = "/shop/checkout/";
export const CATALOG_HREF = "/shop/";
export const ORDERS_HREF = "/shop/orders/";
export const KITCHEN_HREF = "/bai-viet/";
export const ABOUT_HREF = "/gioi-thieu/"; // naming: allow - URL công khai của Shop
export const HOW_TO_BUY_HREF = "/trang/?slug=cach-mua-hang";
export const CONTACT_HREF = "/trang/?slug=lien-he";

/** Đường dẫn trang nhóm hàng: combo lọc theo loại, còn lại theo slug nhóm. */
export function groupHref(slug: string): string {
  return slug === "combo" ? "/shop/?type=combo" : `/shop/?group=${encodeURIComponent(slug)}`;
}

/** Chuẩn hoá số điện thoại cho href="tel:" (chỉ giữ chữ số và dấu +). */
export function telHref(phone: string): string {
  return `tel:${phone.replace(/[^\d+]/g, "")}`;
}

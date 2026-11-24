// Cờ bật và đếm lỗi tìm địa chỉ qua máy chủ Cá Về (SHOP-3-04, 02b §1.9b.5, BR-BH-29).
// Phương án A không giữ API key ở trình duyệt, không nạp thư viện bản đồ và không gọi Geolocation.

import type { SiteInfoResponse } from "@/features/site/types";

const MAX_SEARCH_FAILURES = 2;
let failures = 0;

/** Nút "Tìm địa chỉ" chỉ hiện khi `site-info.address_search_enabled === true` (02b §1.9b.5, Q-5). */
export function isAddressSearchEnabled(info: SiteInfoResponse | null | undefined): boolean {
  return info?.address_search_enabled === true;
}

/** Ghi nhận một lần lỗi 503 (`ADDRESS_SEARCH_UNAVAILABLE`) hoặc mất mạng khi tìm/lấy chi tiết địa chỉ. */
export function recordAddressSearchFailure(): void {
  failures += 1;
}

/** Đã lỗi từ hai lần trong phiên: các lần bấm sau mở thẳng hộp thoại C5 (02b §1.9b.5, SHOP-3-04 AC5). */
export function searchGaveUp(): boolean {
  return failures >= MAX_SEARCH_FAILURES;
}

/** Nên mở thẳng hộp thoại C5 thay vì mở hộp tìm địa chỉ khi đã lỗi hai lần trong phiên. */
export function shouldOpenFallbackDirectly(): boolean {
  return searchGaveUp();
}

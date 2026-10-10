import { fetchPublicEntry } from "./api";
import { RETURNS_SLUG, SHIPPING_SLUG, policyHref } from "./slugs";

/**
 * Tóm tắt chính sách cho dòng "Giao hàng:" và "Đổi trả:" ở trang chi tiết món (SHOP-5-04 AC5, 06-marketing F5).
 * Lấy `excerpt` của trang CMS `giao-hang`, `doi-tra`. Trang chưa có, đã gỡ, lỗi mạng hoặc chưa có tóm tắt
 * thì trả `null` cho dòng đó để màn ẩn dòng. Không bao giờ ném lỗi.
 * Dùng ở `features/catalog/components/ItemDetailScreen.tsx` (fe-dev gắn).
 */
export interface PolicySummaryLine {
  text: string;
  href: string;
}

export interface PolicySummaries {
  shipping: PolicySummaryLine | null;
  returns: PolicySummaryLine | null;
}

async function summaryOf(slug: string): Promise<PolicySummaryLine | null> {
  try {
    const entry = await fetchPublicEntry(slug);
    const text = (entry.excerpt ?? "").trim();
    return text ? { text, href: policyHref(slug) } : null;
  } catch {
    return null;
  }
}

let cache: Promise<PolicySummaries> | null = null;

export function getPolicySummaries(): Promise<PolicySummaries> {
  if (!cache) {
    cache = Promise.all([summaryOf(SHIPPING_SLUG), summaryOf(RETURNS_SLUG)]).then(([shipping, returns]) => ({
      shipping,
      returns,
    }));
  }
  return cache;
}

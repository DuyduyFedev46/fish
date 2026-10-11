import { ApiError } from "@/lib/types";
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

/** `transient`: lỗi mạng hoặc máy chủ, kết quả `null` chỉ dùng cho lần này, không giữ cache. */
interface SummaryResult {
  line: PolicySummaryLine | null;
  transient: boolean;
}

async function summaryOf(slug: string): Promise<SummaryResult> {
  try {
    const entry = await fetchPublicEntry(slug);
    const text = (entry.excerpt ?? "").trim();
    return { line: text ? { text, href: policyHref(slug) } : null, transient: false };
  } catch (err) {
    // 404/410: trang chưa có hoặc đã gỡ -> chắc chắn ẩn dòng. Lỗi khác (mạng, 5xx) -> ẩn lần này, lần sau thử lại.
    const gone = err instanceof ApiError && (err.status === 404 || err.status === 410);
    return { line: null, transient: !gone };
  }
}

let cache: Promise<PolicySummaries> | null = null;

/** Review lô 3+4, L3: chỉ giữ cache khi cả hai trang có câu trả lời chắc chắn; lỗi mạng thì lần gọi sau tải lại. */
export function getPolicySummaries(): Promise<PolicySummaries> {
  if (cache) return cache;
  const promise = Promise.all([summaryOf(SHIPPING_SLUG), summaryOf(RETURNS_SLUG)]).then(([shipping, returns]) => {
    if ((shipping.transient || returns.transient) && cache === promise) cache = null;
    return { shipping: shipping.line, returns: returns.line };
  });
  cache = promise;
  return promise;
}

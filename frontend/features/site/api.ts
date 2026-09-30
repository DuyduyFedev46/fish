import { apiFetch } from "@/lib/api";
// KHÔNG import tĩnh "./mock" (xem lib/api.ts): nhánh mock nạp động để bản build thật không mang seed.
import type { FooterLinkItem, PrivacyPolicyResponse, SiteInfoResponse } from "./types";

// Một nguồn `getSiteInfo` duy nhất cho toàn Shop (SR-23 F10; trước đây còn một bản ở lib/api.ts).
// Footer pháp lý (root layout), màn thanh toán và thông báo CSKH đều gọi hàm này; gom lại để một
// lần xem trang chỉ tốn 1 request `/api/public/site-info/` (backend cũng cho cache 5 phút).
// Lỗi thì bỏ cache để lần gọi sau thử lại.
const SITE_INFO_TTL_MS = 5 * 60 * 1000;
let siteInfoCache: { at: number; promise: Promise<SiteInfoResponse> } | null = null;

async function fetchSiteInfo(): Promise<SiteInfoResponse> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "1") {
    const m = await import("./mock");
    return m.mockSiteInfo();
  }
  return apiFetch<SiteInfoResponse>("/api/public/site-info/");
}

export function getSiteInfo(): Promise<SiteInfoResponse> {
  const now = Date.now();
  if (siteInfoCache && now - siteInfoCache.at < SITE_INFO_TTL_MS) return siteInfoCache.promise;
  const promise = fetchSiteInfo();
  siteInfoCache = { at: now, promise };
  promise.catch(() => {
    if (siteInfoCache && siteInfoCache.promise === promise) siteInfoCache = null;
  });
  return promise;
}

export async function getFooterLinks(): Promise<FooterLinkItem[]> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "1") {
    const m = await import("./mock");
    return m.mockFooterLinks();
  }
  return apiFetch<FooterLinkItem[]>("/api/public/content/footer-links/");
}

export async function getPrivacyPolicy(): Promise<PrivacyPolicyResponse> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "1") {
    const m = await import("./mock");
    return m.mockPrivacyPolicy();
  }
  return apiFetch<PrivacyPolicyResponse>("/api/public/content/pages/by-role/privacy/");
}

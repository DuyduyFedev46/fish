import { apiFetch } from "@/lib/api";
// KHÔNG import tĩnh "./mock" (xem lib/api.ts): nhánh mock nạp động để bản build thật không mang seed.
import type { FooterLinkItem, PrivacyPolicyResponse, SiteInfoResponse } from "./types";

export async function getSiteInfo(): Promise<SiteInfoResponse> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "1") {
    const m = await import("./mock");
    return m.mockSiteInfo();
  }
  return apiFetch<SiteInfoResponse>("/api/public/site-info/");
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

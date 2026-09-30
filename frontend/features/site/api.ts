import { apiFetch } from "@/lib/api";
import { mockFooterLinks, mockPrivacyPolicy, mockSiteInfo } from "./mock";
import type { FooterLinkItem, PrivacyPolicyResponse, SiteInfoResponse } from "./types";

export async function getSiteInfo(): Promise<SiteInfoResponse> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "1") return mockSiteInfo();
  return apiFetch<SiteInfoResponse>("/api/public/site-info/");
}

export async function getFooterLinks(): Promise<FooterLinkItem[]> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "1") return mockFooterLinks();
  return apiFetch<FooterLinkItem[]>("/api/public/content/footer-links/");
}

export async function getPrivacyPolicy(): Promise<PrivacyPolicyResponse> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "1") return mockPrivacyPolicy();
  return apiFetch<PrivacyPolicyResponse>("/api/public/content/pages/by-role/privacy/");
}

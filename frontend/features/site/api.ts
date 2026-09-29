import { apiFetch, USE_MOCK } from "@/lib/api";
import { mockFooterLinks, mockPrivacyPolicy, mockSiteInfo } from "./mock";
import type { FooterLinkItem, PrivacyPolicyResponse, SiteInfoResponse } from "./types";

export async function getSiteInfo(): Promise<SiteInfoResponse> {
  if (USE_MOCK) return mockSiteInfo();
  return apiFetch<SiteInfoResponse>("/api/public/site-info/");
}

export async function getFooterLinks(): Promise<FooterLinkItem[]> {
  if (USE_MOCK) return mockFooterLinks();
  return apiFetch<FooterLinkItem[]>("/api/public/content/footer-links/");
}

export async function getPrivacyPolicy(): Promise<PrivacyPolicyResponse> {
  if (USE_MOCK) return mockPrivacyPolicy();
  return apiFetch<PrivacyPolicyResponse>("/api/public/content/pages/by-role/privacy/");
}

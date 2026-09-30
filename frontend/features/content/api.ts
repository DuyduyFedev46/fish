import { apiFetch } from "@/lib/api";
import type {
  FooterLink,
  PageByRoleResponse,
  PublicCategory,
  PublicEntryDetail,
  PublicEntryListResponse,
} from "./types";
import {
  mockGetFooterLinks,
  mockGetPageByRole,
  mockGetPublicCategories,
  mockGetPublicEntries,
  mockGetPublicEntry,
} from "./mock";

export async function fetchPublicEntry(slug: string): Promise<PublicEntryDetail> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "1") {
    return mockGetPublicEntry(slug);
  }
  return apiFetch<PublicEntryDetail>(`/api/public/content/entries/${encodeURIComponent(slug)}/`);
}

export async function fetchPublicEntries(params?: {
  category?: string;
  page?: number;
}): Promise<PublicEntryListResponse> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "1") {
    return mockGetPublicEntries(params);
  }
  const query = new URLSearchParams();
  if (params?.category) query.set("category", params.category);
  if (params?.page) query.set("page", params.page.toString());
  const qStr = query.toString() ? `?${query.toString()}` : "";
  return apiFetch<PublicEntryListResponse>(`/api/public/content/entries/${qStr}`);
}

export async function fetchPublicCategories(): Promise<PublicCategory[]> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "1") {
    return mockGetPublicCategories();
  }
  return apiFetch<PublicCategory[]>("/api/public/content/categories/");
}

export async function fetchPageByRole(role: string): Promise<PageByRoleResponse> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "1") {
    return mockGetPageByRole(role);
  }
  return apiFetch<PageByRoleResponse>(`/api/public/content/pages/by-role/${encodeURIComponent(role)}/`);
}

export async function fetchFooterLinks(): Promise<FooterLink[]> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "1") {
    return mockGetFooterLinks();
  }
  return apiFetch<FooterLink[]>("/api/public/content/footer-links/");
}


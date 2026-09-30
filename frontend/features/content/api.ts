import { apiFetch } from "@/lib/api";
import type {
  FooterLink,
  PageByRoleResponse,
  PublicCategory,
  PublicEntryDetail,
  PublicEntryListResponse,
} from "./types";
// KHÔNG import tĩnh "./mock" (xem lib/api.ts): nhánh mock nạp động để bản build thật không mang seed.

export async function fetchPublicEntry(slug: string): Promise<PublicEntryDetail> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "1") {
    const m = await import("./mock");
    return m.mockGetPublicEntry(slug);
  }
  return apiFetch<PublicEntryDetail>(`/api/public/content/entries/${encodeURIComponent(slug)}/`);
}

export async function fetchPublicEntries(params?: {
  category?: string;
  page?: number;
}): Promise<PublicEntryListResponse> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "1") {
    const m = await import("./mock");
    return m.mockGetPublicEntries(params);
  }
  const query = new URLSearchParams();
  if (params?.category) query.set("category", params.category);
  if (params?.page) query.set("page", params.page.toString());
  const qStr = query.toString() ? `?${query.toString()}` : "";
  return apiFetch<PublicEntryListResponse>(`/api/public/content/entries/${qStr}`);
}

export async function fetchPublicCategories(): Promise<PublicCategory[]> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "1") {
    const m = await import("./mock");
    return m.mockGetPublicCategories();
  }
  return apiFetch<PublicCategory[]>("/api/public/content/categories/");
}

export async function fetchPageByRole(role: string): Promise<PageByRoleResponse> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "1") {
    const m = await import("./mock");
    return m.mockGetPageByRole(role);
  }
  return apiFetch<PageByRoleResponse>(`/api/public/content/pages/by-role/${encodeURIComponent(role)}/`);
}

export async function fetchFooterLinks(): Promise<FooterLink[]> {
  if (process.env.NEXT_PUBLIC_USE_MOCK === "1") {
    const m = await import("./mock");
    return m.mockGetFooterLinks();
  }
  return apiFetch<FooterLink[]>("/api/public/content/footer-links/");
}


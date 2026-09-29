import { apiFetch, USE_MOCK } from "@/lib/api";
import type {
  PublicCategory,
  PublicEntryDetail,
  PublicEntryListResponse,
} from "./types";
import {
  mockGetPublicCategories,
  mockGetPublicEntries,
  mockGetPublicEntry,
} from "./mock";

export async function fetchPublicEntry(slug: string): Promise<PublicEntryDetail> {
  if (USE_MOCK) {
    return mockGetPublicEntry(slug);
  }
  return apiFetch<PublicEntryDetail>(`/api/public/content/entries/${encodeURIComponent(slug)}/`);
}

export async function fetchPublicEntries(params?: {
  category?: string;
  page?: number;
}): Promise<PublicEntryListResponse> {
  if (USE_MOCK) {
    return mockGetPublicEntries(params);
  }
  const query = new URLSearchParams();
  if (params?.category) query.set("category", params.category);
  if (params?.page) query.set("page", params.page.toString());
  const qStr = query.toString() ? `?${query.toString()}` : "";
  return apiFetch<PublicEntryListResponse>(`/api/public/content/entries/${qStr}`);
}

export async function fetchPublicCategories(): Promise<PublicCategory[]> {
  if (USE_MOCK) {
    return mockGetPublicCategories();
  }
  return apiFetch<PublicCategory[]>("/api/public/content/categories/");
}

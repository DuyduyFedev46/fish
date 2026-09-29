import { apiFetch } from "@/shared/lib/http";
import type {
  CategoryCreatePayload,
  CategoryUpdatePayload,
  ContentCategory,
  ContentCounts,
  ContentEntryListItem,
} from "./types";
import {
  mockCreateCategory,
  mockGetEntryCounts,
  mockListCategories,
  mockListEntries,
  mockUpdateCategory,
} from "./mock";

const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";

export async function fetchCategories(signal?: AbortSignal): Promise<ContentCategory[]> {
  return apiFetch<ContentCategory[]>("/api/content/categories/", {
    signal,
    mock: isMock ? () => ({ status: 200, body: mockListCategories() }) : undefined,
  });
}

export async function createCategory(
  payload: CategoryCreatePayload
): Promise<ContentCategory> {
  return apiFetch<ContentCategory>("/api/content/categories/", {
    method: "POST",
    body: JSON.stringify(payload),
    mock: isMock ? () => ({ status: 201, body: mockCreateCategory(payload) }) : undefined,
  });
}

export async function updateCategory(
  id: number,
  payload: CategoryUpdatePayload
): Promise<ContentCategory> {
  return apiFetch<ContentCategory>(`/api/content/categories/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
    mock: isMock ? () => ({ status: 200, body: mockUpdateCategory(id, payload) }) : undefined,
  });
}

export async function fetchEntries(
  params?: {
    status?: string;
    kind?: string;
    category?: number;
    page?: number;
  },
  signal?: AbortSignal
): Promise<{ count: number; results: ContentEntryListItem[] }> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.kind) query.set("kind", params.kind);
  if (params?.category) query.set("category", String(params.category));
  if (params?.page) query.set("page", String(params.page));

  const qs = query.toString();
  const url = `/api/content/entries/${qs ? `?${qs}` : ""}`;

  return apiFetch<{ count: number; results: ContentEntryListItem[] }>(url, {
    signal,
    mock: isMock ? () => ({ status: 200, body: mockListEntries(params) }) : undefined,
  });
}

export async function fetchEntryCounts(
  params?: { kind?: string },
  signal?: AbortSignal
): Promise<ContentCounts> {
  const query = new URLSearchParams();
  if (params?.kind) query.set("kind", params.kind);
  const qs = query.toString();
  const url = `/api/content/entries/counts/${qs ? `?${qs}` : ""}`;

  return apiFetch<ContentCounts>(url, {
    signal,
    mock: isMock ? () => ({ status: 200, body: mockGetEntryCounts() }) : undefined,
  });
}

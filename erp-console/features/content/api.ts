import { apiFetch, apiUpload } from "@/shared/lib/http";
import type {
  CategoryCreatePayload,
  CategoryUpdatePayload,
  ContentCategory,
  ContentCounts,
  ContentEntryDetail,
  ContentEntryListItem,
  ContentImage,
  EntryCreatePayload,
  EntryDiscardPayload,
  EntryPublishPayload,
  EntryPublishResponse,
  EntryUnpublishPayload,
  EntryUpdatePayload,
  GoliveStatusResponse,
} from "./types";
import {
  mockCreateCategory,
  mockCreateEntry,
  mockDeleteEntry,
  mockDiscardChanges,
  mockGetEntry,
  mockGetEntryCounts,
  mockGetGoliveStatus,
  mockListCategories,
  mockListEntries,
  mockPublishEntry,
  mockUnpublishEntry,
  mockUpdateCategory,
  mockUpdateEntry,
  mockUpdateImageAlt,
  mockUploadEntryImage,
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

export async function getEntry(id: number, signal?: AbortSignal): Promise<ContentEntryDetail> {
  return apiFetch<ContentEntryDetail>(`/api/content/entries/${id}/`, {
    signal,
    mock: isMock ? () => ({ status: 200, body: mockGetEntry(id) }) : undefined,
  });
}

export async function createEntry(payload: EntryCreatePayload): Promise<ContentEntryDetail> {
  return apiFetch<ContentEntryDetail>("/api/content/entries/", {
    method: "POST",
    body: payload,
    mock: isMock ? () => ({ status: 201, body: mockCreateEntry(payload) }) : undefined,
  });
}

export async function updateEntry(
  id: number,
  payload: EntryUpdatePayload
): Promise<ContentEntryDetail> {
  return apiFetch<ContentEntryDetail>(`/api/content/entries/${id}/`, {
    method: "PATCH",
    body: payload,
    mock: isMock ? () => ({ status: 200, body: mockUpdateEntry(id, payload) }) : undefined,
  });
}

export async function deleteEntry(id: number): Promise<void> {
  return apiFetch<void>(`/api/content/entries/${id}/`, {
    method: "DELETE",
    mock: isMock
      ? () => {
          mockDeleteEntry(id);
          return { status: 204, body: null };
        }
      : undefined,
  });
}

export async function uploadEntryImage(
  entryId: number,
  file: File,
  alt?: string,
  onProgress?: (percent: number) => void
): Promise<ContentImage> {
  const formData = new FormData();
  formData.append("file", file);
  if (alt) formData.append("alt", alt);

  return apiUpload<ContentImage>(`/api/content/entries/${entryId}/images/`, formData, {
    onProgress,
    mock: isMock
      ? () => ({
          status: 201,
          body: mockUploadEntryImage(entryId, file, alt),
        })
      : undefined,
  });
}

export async function updateImageAlt(imageId: number, alt: string): Promise<ContentImage> {
  return apiFetch<ContentImage>(`/api/content/images/${imageId}/`, {
    method: "PATCH",
    body: { alt },
    mock: isMock ? () => ({ status: 200, body: mockUpdateImageAlt(imageId, alt) }) : undefined,
  });
}

export async function publishEntry(
  id: number,
  payload: EntryPublishPayload
): Promise<EntryPublishResponse> {
  return apiFetch<EntryPublishResponse>(`/api/content/entries/${id}/publish/`, {
    method: "POST",
    body: payload,
    mock: isMock ? () => ({ status: 200, body: mockPublishEntry(id, payload) }) : undefined,
  });
}

export async function unpublishEntry(
  id: number,
  payload: EntryUnpublishPayload
): Promise<ContentEntryDetail> {
  return apiFetch<ContentEntryDetail>(`/api/content/entries/${id}/unpublish/`, {
    method: "POST",
    body: payload,
    mock: isMock ? () => ({ status: 200, body: mockUnpublishEntry(id, payload) }) : undefined,
  });
}

export async function discardChanges(
  id: number,
  payload: EntryDiscardPayload
): Promise<ContentEntryDetail> {
  return apiFetch<ContentEntryDetail>(`/api/content/entries/${id}/discard-changes/`, {
    method: "POST",
    body: payload,
    mock: isMock ? () => ({ status: 200, body: mockDiscardChanges(id, payload) }) : undefined,
  });
}

export async function fetchGoliveStatus(signal?: AbortSignal): Promise<GoliveStatusResponse> {
  return apiFetch<GoliveStatusResponse>("/api/content/golive-status/", {
    signal,
    mock: isMock ? () => ({ status: 200, body: mockGetGoliveStatus() }) : undefined,
  });
}




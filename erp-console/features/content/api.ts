import { apiFetch, apiUpload, type Paginated } from "@/shared/lib/http";
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
  ContentEntryVersionDetail,
  ContentEntryVersionListItem,
  EntryRestorePayload,
  EntryReturnPayload,
  EntryReturnResponse,
  EntrySubmitPayload,
  EntrySubmitResponse,
} from "./types";
import {
  mockCreateCategory,
  mockCreateEntry,
  mockDeleteEntry,
  mockDiscardChanges,
  mockFetchEntryVersions,
  mockGetEntry,
  mockGetEntryCounts,
  mockGetEntryVersion,
  mockGetGoliveStatus,
  mockListCategories,
  mockListEntries,
  mockPublishEntry,
  mockRestoreEntryVersion,
  mockReturnEntry,
  mockSubmitEntry,
  mockUnpublishEntry,
  mockUpdateCategory,
  mockUpdateEntry,
  mockUpdateImageAlt,
  mockUploadEntryImage,
} from "./mock";

// Điều kiện mock viết nguyên văn tại từng chỗ dùng (không gán ra biến): bundler mới cắt nhánh mock khỏi bản build thật.
export async function fetchCategories(signal?: AbortSignal): Promise<ContentCategory[]> {
  return apiFetch<ContentCategory[]>("/api/content/categories/", {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => ({ status: 200, body: mockListCategories() }) : undefined,
  });
}

export async function createCategory(
  payload: CategoryCreatePayload
): Promise<ContentCategory> {
  return apiFetch<ContentCategory>("/api/content/categories/", {
    method: "POST",
    body: payload,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? (req) => ({ status: 201, body: mockCreateCategory(req.body as CategoryCreatePayload) }) : undefined,
  });
}

export async function updateCategory(
  id: number,
  payload: CategoryUpdatePayload
): Promise<ContentCategory> {
  return apiFetch<ContentCategory>(`/api/content/categories/${id}/`, {
    method: "PATCH",
    body: payload,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? (req) => ({ status: 200, body: mockUpdateCategory(id, req.body as CategoryUpdatePayload) }) : undefined,
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
): Promise<Paginated<ContentEntryListItem>> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.kind) query.set("kind", params.kind);
  if (params?.category) query.set("category", String(params.category));
  if (params?.page) query.set("page", String(params.page));

  const qs = query.toString();
  const url = `/api/content/entries/${qs ? `?${qs}` : ""}`;

  return apiFetch<Paginated<ContentEntryListItem>>(url, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => ({ status: 200, body: mockListEntries(params) }) : undefined,
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
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => ({ status: 200, body: mockGetEntryCounts() }) : undefined,
  });
}

export async function getEntry(id: number, signal?: AbortSignal): Promise<ContentEntryDetail> {
  return apiFetch<ContentEntryDetail>(`/api/content/entries/${id}/`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => ({ status: 200, body: mockGetEntry(id) }) : undefined,
  });
}

export async function createEntry(payload: EntryCreatePayload): Promise<ContentEntryDetail> {
  return apiFetch<ContentEntryDetail>("/api/content/entries/", {
    method: "POST",
    body: payload,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => ({ status: 201, body: mockCreateEntry(payload) }) : undefined,
  });
}

export async function updateEntry(
  id: number,
  payload: EntryUpdatePayload
): Promise<ContentEntryDetail> {
  return apiFetch<ContentEntryDetail>(`/api/content/entries/${id}/`, {
    method: "PATCH",
    body: payload,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => ({ status: 200, body: mockUpdateEntry(id, payload) }) : undefined,
  });
}

export async function deleteEntry(id: number): Promise<void> {
  return apiFetch<void>(`/api/content/entries/${id}/`, {
    method: "DELETE",
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1"
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
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1"
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
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => ({ status: 200, body: mockUpdateImageAlt(imageId, alt) }) : undefined,
  });
}

export async function publishEntry(
  id: number,
  payload: EntryPublishPayload
): Promise<EntryPublishResponse> {
  return apiFetch<EntryPublishResponse>(`/api/content/entries/${id}/publish/`, {
    method: "POST",
    body: payload,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => ({ status: 200, body: mockPublishEntry(id, payload) }) : undefined,
  });
}

export async function unpublishEntry(
  id: number,
  payload: EntryUnpublishPayload
): Promise<ContentEntryDetail> {
  return apiFetch<ContentEntryDetail>(`/api/content/entries/${id}/unpublish/`, {
    method: "POST",
    body: payload,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => ({ status: 200, body: mockUnpublishEntry(id, payload) }) : undefined,
  });
}

export async function discardChanges(
  id: number,
  payload: EntryDiscardPayload
): Promise<ContentEntryDetail> {
  return apiFetch<ContentEntryDetail>(`/api/content/entries/${id}/discard-changes/`, {
    method: "POST",
    body: payload,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => ({ status: 200, body: mockDiscardChanges(id, payload) }) : undefined,
  });
}

export async function fetchGoliveStatus(signal?: AbortSignal): Promise<GoliveStatusResponse> {
  return apiFetch<GoliveStatusResponse>("/api/content/golive-status/", {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => ({ status: 200, body: mockGetGoliveStatus() }) : undefined,
  });
}

export interface ShopCatalogItem {
  item_code: string;
  name: string;
  price?: number;
  sellable_qty?: number;
}

export async function fetchShopCatalog(): Promise<ShopCatalogItem[]> {
  return apiFetch<ShopCatalogItem[]>("/api/shop/catalog/", {
    auth: false,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => ({
      status: 200,
      body: [
        { item_code: "CA-THU-1KG", name: "Cá thu Phan Thiết 1kg", price: 250000, sellable_qty: 10 },
        { item_code: "CA-BOP-1KG", name: "Cá bớp cắt khoanh 1kg", price: 280000, sellable_qty: 5 },
        { item_code: "TOM-SU-1KG", name: "Tôm sú Cà Mau 1kg", price: 320000, sellable_qty: 8 },
        { item_code: "MUC-ONG-1KG", name: "Mực ống Phan Thiết 1kg", price: 220000, sellable_qty: 12 },
      ],
    }) : undefined,
  });
}

export async function submitEntry(
  id: number,
  payload: EntrySubmitPayload
): Promise<EntrySubmitResponse> {
  return apiFetch<EntrySubmitResponse>(`/api/content/entries/${id}/submit/`, {
    method: "POST",
    body: payload,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => ({ status: 200, body: mockSubmitEntry(id, payload) }) : undefined,
  });
}

export async function returnEntry(
  id: number,
  payload: EntryReturnPayload
): Promise<EntryReturnResponse> {
  return apiFetch<EntryReturnResponse>(`/api/content/entries/${id}/return/`, {
    method: "POST",
    body: payload,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => ({ status: 200, body: mockReturnEntry(id, payload) }) : undefined,
  });
}

export async function fetchEntryVersions(
  id: number,
  signal?: AbortSignal
): Promise<ContentEntryVersionListItem[]> {
  return apiFetch<ContentEntryVersionListItem[]>(`/api/content/entries/${id}/versions/`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => ({ status: 200, body: mockFetchEntryVersions(id) }) : undefined,
  });
}

export async function getEntryVersion(
  id: number,
  versionNo: number,
  signal?: AbortSignal
): Promise<ContentEntryVersionDetail> {
  return apiFetch<ContentEntryVersionDetail>(`/api/content/entries/${id}/versions/${versionNo}/`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => ({ status: 200, body: mockGetEntryVersion(id, versionNo) }) : undefined,
  });
}

export async function restoreEntryVersion(
  id: number,
  versionNo: number,
  payload: EntryRestorePayload
): Promise<ContentEntryDetail> {
  return apiFetch<ContentEntryDetail>(`/api/content/entries/${id}/versions/${versionNo}/restore/`, {
    method: "POST",
    body: payload,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => ({ status: 200, body: mockRestoreEntryVersion(id, versionNo, payload) }) : undefined,
  });
}





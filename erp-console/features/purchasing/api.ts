import { apiFetch, type Paginated } from "@/shared/lib/http";
import { mockCancelPurchaseReceipt, mockListSuppliers, mockSubmitNhapLo } from "./mock";
import type { CancelPurchaseReceiptResponse, NhapLoPayload, NhapLoResponse, Supplier } from "./types";

export async function fetchSuppliers(signal?: AbortSignal): Promise<Supplier[]> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  const res = await apiFetch<Paginated<Supplier>>("/api/purchasing/suppliers/", {
    signal,
    mock: isMock ? mockListSuppliers : undefined,
  });
  return res.results || [];
}

export async function submitNhapLo(
  payload: NhapLoPayload,
  signal?: AbortSignal
): Promise<NhapLoResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<NhapLoResponse>("/api/purchasing/receipts/nhap-lo/", {
    method: "POST",
    body: payload,
    signal,
    mock: isMock ? mockSubmitNhapLo : undefined,
  });
}

export async function cancelPurchaseReceipt(
  receiptId: number,
  signal?: AbortSignal
): Promise<CancelPurchaseReceiptResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<CancelPurchaseReceiptResponse>(
    `/api/purchasing/receipts/${receiptId}/cancel/`,
    {
      method: "POST",
      body: {},
      signal,
      mock: isMock ? mockCancelPurchaseReceipt : undefined,
    }
  );
}

export const DRAFT_STORAGE_KEY = "cave_draft_nhap_lo";

export function getNhapLoDraft(): Record<string, unknown> | null {
  if (typeof window === "undefined" && typeof localStorage === "undefined") return null;
  try {
    const raw = (typeof window !== "undefined" ? window.localStorage : localStorage).getItem(
      DRAFT_STORAGE_KEY
    );
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveNhapLoDraft(data: Record<string, unknown>): void {
  if (typeof window === "undefined" && typeof localStorage === "undefined") return;
  try {
    (typeof window !== "undefined" ? window.localStorage : localStorage).setItem(
      DRAFT_STORAGE_KEY,
      JSON.stringify(data)
    );
  } catch {
    // ignore
  }
}

export function clearNhapLoDraft(): void {
  if (typeof window === "undefined" && typeof localStorage === "undefined") return;
  try {
    (typeof window !== "undefined" ? window.localStorage : localStorage).removeItem(
      DRAFT_STORAGE_KEY
    );
  } catch {
    // ignore
  }
}

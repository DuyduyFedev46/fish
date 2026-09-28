import { apiFetch } from "@/shared/lib/http";
import {
  mockGetDeliveryNoteDetail,
  mockListDeliveryNotes,
  mockPostDeliveryNoteStatus,
} from "./mock";
import type {
  DeliveryListResponse,
  DeliveryNoteDetail,
} from "./types";

export async function fetchDeliveryNotes(
  params: {
    status?: string;
    completed_from?: string;
    page?: number;
  },
  signal?: AbortSignal
): Promise<DeliveryListResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.completed_from) query.set("completed_from", params.completed_from);
  if (params.page) query.set("page", String(params.page));

  const qs = query.toString();
  const url = `/api/delivery/notes/${qs ? `?${qs}` : ""}`;

  return apiFetch<DeliveryListResponse>(url, {
    signal,
    mock: isMock ? mockListDeliveryNotes : undefined,
  });
}

export async function fetchDeliveryNoteDetail(
  id: number,
  signal?: AbortSignal
): Promise<DeliveryNoteDetail> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<DeliveryNoteDetail>(`/api/delivery/notes/${id}/`, {
    signal,
    mock: isMock ? mockGetDeliveryNoteDetail : undefined,
  });
}

export type PackDeliveryNoteResponse = DeliveryNoteDetail & {
  already?: boolean;
};

export async function packDeliveryNote(
  id: number,
  fromStatus = "PREPARING",
  signal?: AbortSignal
): Promise<PackDeliveryNoteResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<PackDeliveryNoteResponse>(`/api/delivery/notes/${id}/status/`, {
    method: "POST",
    body: {
      to_status: "READY",
      from_status: fromStatus,
    },
    signal,
    mock: isMock ? mockPostDeliveryNoteStatus : undefined,
  });
}

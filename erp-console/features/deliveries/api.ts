import { apiFetch } from "@/shared/lib/http";
import {
  mockGetDeliveryLabel,
  mockGetDeliveryNoteDetail,
  mockListDeliveryNotes,
  mockPostDeliveryLabelPrint,
  mockPostDeliveryNoteStatus,
} from "./mock";
import type {
  DeliveryListResponse,
  DeliveryNoteDetail,
  LabelData,
  PrintDeliveryLabelResponse,
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

export async function fetchDeliveryLabel(
  id: number,
  printNo?: number,
  signal?: AbortSignal
): Promise<LabelData> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  const qs = printNo ? `?print_no=${printNo}` : "";
  return apiFetch<LabelData>(`/api/delivery/notes/${id}/label/${qs}`, {
    signal,
    mock: isMock ? (req) => mockGetDeliveryLabel(req, id, printNo) : undefined,
  });
}

export async function printDeliveryLabel(
  id: number,
  requestId?: string,
  signal?: AbortSignal
): Promise<PrintDeliveryLabelResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  const reqId =
    requestId ||
    (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : undefined);
  return apiFetch<PrintDeliveryLabelResponse>(`/api/delivery/notes/${id}/label/print/`, {
    method: "POST",
    body: { request_id: reqId },
    signal,
    mock: isMock ? (req) => mockPostDeliveryLabelPrint(req, id) : undefined,
  });
}


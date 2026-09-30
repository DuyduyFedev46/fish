import { ApiError, apiFetch } from "@/shared/lib/http";
import type {
  ConfirmationQueueDetail,
  ConfirmationQueueResponse,
  CustomerSearchResponse,
  ClaimTaskResponse,
  RecordCallPayload,
  RecordCallResponse,
  UnconfirmPayload,
  UnconfirmResponse,
  ChangeRecipientPayload,
  ChangeRecipientResponse,
  DecidePayload,
  DecideResponse,
} from "./types";
import {
  mockClaimConfirmationTask,
  mockGetConfirmationDetail,
  mockGetConfirmationQueue,
  mockRecordConfirmationCall,
  mockSearchCustomers,
  mockUnconfirm,
  mockChangeRecipient,
  mockDecideConfirmation,
} from "./mock";

export async function fetchConfirmationQueue(
  params?: {
    state?: string;
    page?: number;
  },
  signal?: AbortSignal
): Promise<ConfirmationQueueResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  const query = new URLSearchParams();
  if (params?.state) query.set("state", params.state);
  if (params?.page) query.set("page", String(params.page));

  const qs = query.toString();
  const url = `/api/cskh/queue/${qs ? `?${qs}` : ""}`;

  return apiFetch<ConfirmationQueueResponse>(url, {
    signal,
    mock: isMock ? mockGetConfirmationQueue : undefined,
  });
}

export async function fetchConfirmationDetail(
  noteId: number,
  signal?: AbortSignal
): Promise<ConfirmationQueueDetail> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<ConfirmationQueueDetail>(`/api/cskh/queue/${noteId}/`, {
    signal,
    mock: isMock ? (req) => mockGetConfirmationDetail(req, noteId) : undefined,
  });
}

export async function claimConfirmationTask(
  noteId: number,
  signal?: AbortSignal
): Promise<ClaimTaskResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<ClaimTaskResponse>(`/api/cskh/queue/${noteId}/claim/`, {
    method: "POST",
    body: {},
    signal,
    mock: isMock ? (req) => mockClaimConfirmationTask(req, noteId) : undefined,
  });
}

export async function recordConfirmationCall(
  noteId: number,
  payload: RecordCallPayload,
  signal?: AbortSignal
): Promise<RecordCallResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<RecordCallResponse>(`/api/cskh/queue/${noteId}/calls/`, {
    method: "POST",
    body: payload,
    signal,
    mock: isMock ? (req) => mockRecordConfirmationCall(req, noteId, payload) : undefined,
  });
}

export async function unconfirmDelivery(
  noteId: number,
  payload: UnconfirmPayload,
  signal?: AbortSignal
): Promise<UnconfirmResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<UnconfirmResponse>(`/api/cskh/queue/${noteId}/unconfirm/`, {
    method: "POST",
    body: payload,
    signal,
    mock: isMock ? (req) => mockUnconfirm(req, noteId, payload) : undefined,
  });
}

export async function changeRecipient(
  noteId: number,
  payload: ChangeRecipientPayload,
  signal?: AbortSignal
): Promise<ChangeRecipientResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<ChangeRecipientResponse>(`/api/cskh/queue/${noteId}/recipient/`, {
    method: "POST",
    body: payload,
    signal,
    mock: isMock ? (req) => mockChangeRecipient(req, noteId, payload) : undefined,
  });
}

/**
 * Tìm kiếm đơn/phiếu trong CSKH. Bắt buộc dùng POST body (Bất biến 9: không để SĐT lên URL).
 */
export async function searchCustomers(
  q: string,
  signal?: AbortSignal
): Promise<CustomerSearchResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<CustomerSearchResponse>("/api/cskh/search/", {
    method: "POST",
    body: { q },
    signal,
    mock: isMock ? (req) => mockSearchCustomers(req, q) : undefined,
  });
}

export async function decideConfirmation(
  noteId: number,
  payload: DecidePayload,
  signal?: AbortSignal
): Promise<DecideResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<DecideResponse>(`/api/cskh/queue/${noteId}/decide/`, {
    method: "POST",
    body: payload,
    signal,
    mock: isMock ? (req) => mockDecideConfirmation(req, noteId, payload) : undefined,
  });
}


/** 409 `STALE_STATE` (SR-09): màn hình đã cũ — đơn/phiếu đổi trạng thái sau khi mở (vd job tự huỷ đã chạy). */
export function isStaleStateError(err: unknown): err is ApiError {
  return err instanceof ApiError && err.status === 409 && err.code === "STALE_STATE";
}

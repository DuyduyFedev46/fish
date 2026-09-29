import { apiFetch } from "@/shared/lib/http";
import type {
  CskhQueueDetail,
  CskhQueueResponse,
  CskhSearchResponse,
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
  mockClaimCskhTask,
  mockGetCskhDetail,
  mockGetCskhQueue,
  mockRecordCskhCall,
  mockSearchCskh,
  mockUnconfirm,
  mockChangeRecipient,
  mockDecideCskh,
} from "./mock";

export async function fetchCskhQueue(
  params?: {
    state?: string;
    page?: number;
  },
  signal?: AbortSignal
): Promise<CskhQueueResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  const query = new URLSearchParams();
  if (params?.state) query.set("state", params.state);
  if (params?.page) query.set("page", String(params.page));

  const qs = query.toString();
  const url = `/api/cskh/queue/${qs ? `?${qs}` : ""}`;

  return apiFetch<CskhQueueResponse>(url, {
    signal,
    mock: isMock ? mockGetCskhQueue : undefined,
  });
}

export async function fetchCskhDetail(
  noteId: number,
  signal?: AbortSignal
): Promise<CskhQueueDetail> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<CskhQueueDetail>(`/api/cskh/queue/${noteId}/`, {
    signal,
    mock: isMock ? (req) => mockGetCskhDetail(req, noteId) : undefined,
  });
}

export async function claimCskhTask(
  noteId: number,
  signal?: AbortSignal
): Promise<ClaimTaskResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<ClaimTaskResponse>(`/api/cskh/queue/${noteId}/claim/`, {
    method: "POST",
    body: {},
    signal,
    mock: isMock ? (req) => mockClaimCskhTask(req, noteId) : undefined,
  });
}

export async function recordCskhCall(
  noteId: number,
  payload: RecordCallPayload,
  signal?: AbortSignal
): Promise<RecordCallResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<RecordCallResponse>(`/api/cskh/queue/${noteId}/calls/`, {
    method: "POST",
    body: payload,
    signal,
    mock: isMock ? (req) => mockRecordCskhCall(req, noteId, payload) : undefined,
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
export async function searchCskh(
  q: string,
  signal?: AbortSignal
): Promise<CskhSearchResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<CskhSearchResponse>("/api/cskh/search/", {
    method: "POST",
    body: { q },
    signal,
    mock: isMock ? (req) => mockSearchCskh(req, q) : undefined,
  });
}

export async function decideCskh(
  noteId: number,
  payload: DecidePayload,
  signal?: AbortSignal
): Promise<DecideResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<DecideResponse>(`/api/cskh/queue/${noteId}/decide/`, {
    method: "POST",
    body: payload,
    signal,
    mock: isMock ? (req) => mockDecideCskh(req, noteId, payload) : undefined,
  });
}


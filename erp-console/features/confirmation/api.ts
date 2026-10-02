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
  const query = new URLSearchParams();
  if (params?.state) query.set("state", params.state);
  if (params?.page) query.set("page", String(params.page));

  const qs = query.toString();
  const url = `/api/confirmation/queue/${qs ? `?${qs}` : ""}`;

  return apiFetch<ConfirmationQueueResponse>(url, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockGetConfirmationQueue : undefined,
  });
}

/** Các trạng thái việc của tab "Tất cả" (BE không có state=ALL nên FE gộp 4 danh sách). */
export const ALL_QUEUE_STATES = ["PENDING", "CALLBACK", "ESCALATED", "REFUND_CALL"] as const;

/**
 * Tab "Tất cả": BE chưa có `state=ALL` (02b) nên gộp 4 lần gọi `state=X` cùng số trang, sắp theo giờ trả tiền tăng dần (đơn trả tiền sớm nhất, chờ lâu nhất, lên đầu); dòng chưa có giờ trả tiền (`paid_at` null) xuống cuối.
 * Trang vượt quá của một trạng thái (404 của DRF) coi như hết dòng của trạng thái đó. Lệch hợp đồng: ghi ở 03-dev-notes.
 */
export async function fetchConfirmationQueueAll(page = 1, signal?: AbortSignal): Promise<ConfirmationQueueResponse> {
  const parts = await Promise.all(
    ALL_QUEUE_STATES.map((state) =>
      fetchConfirmationQueue({ state, page }, signal).catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 404 && page > 1) return { count: 0, next: null, previous: null, results: [] } as ConfirmationQueueResponse;
        throw err;
      }),
    ),
  );
  const results = parts.flatMap((p) => p.results).sort((a, b) => {
    if (a.paid_at === b.paid_at) return 0;
    if (a.paid_at === null) return 1;
    if (b.paid_at === null) return -1;
    return a.paid_at.localeCompare(b.paid_at);
  });
  return {
    count: parts.reduce((n, p) => n + p.count, 0),
    next: parts.some((p) => p.next) ? `page=${page + 1}` : null,
    previous: null,
    results,
  };
}

export async function fetchConfirmationDetail(
  noteId: number,
  signal?: AbortSignal
): Promise<ConfirmationQueueDetail> {
  return apiFetch<ConfirmationQueueDetail>(`/api/confirmation/queue/${noteId}/`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? (req) => mockGetConfirmationDetail(req, noteId) : undefined,
  });
}

export async function claimConfirmationTask(
  noteId: number,
  signal?: AbortSignal
): Promise<ClaimTaskResponse> {
  return apiFetch<ClaimTaskResponse>(`/api/confirmation/queue/${noteId}/claim/`, {
    method: "POST",
    body: {},
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? (req) => mockClaimConfirmationTask(req, noteId) : undefined,
  });
}

export async function recordConfirmationCall(
  noteId: number,
  payload: RecordCallPayload,
  signal?: AbortSignal
): Promise<RecordCallResponse> {
  return apiFetch<RecordCallResponse>(`/api/confirmation/queue/${noteId}/calls/`, {
    method: "POST",
    body: payload,
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? (req) => mockRecordConfirmationCall(req, noteId, payload) : undefined,
  });
}

export async function unconfirmDelivery(
  noteId: number,
  payload: UnconfirmPayload,
  signal?: AbortSignal
): Promise<UnconfirmResponse> {
  return apiFetch<UnconfirmResponse>(`/api/confirmation/queue/${noteId}/unconfirm/`, {
    method: "POST",
    body: payload,
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? (req) => mockUnconfirm(req, noteId, payload) : undefined,
  });
}

export async function changeRecipient(
  noteId: number,
  payload: ChangeRecipientPayload,
  signal?: AbortSignal
): Promise<ChangeRecipientResponse> {
  return apiFetch<ChangeRecipientResponse>(`/api/confirmation/queue/${noteId}/recipient/`, {
    method: "POST",
    body: payload,
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? (req) => mockChangeRecipient(req, noteId, payload) : undefined,
  });
}

/**
 * Tìm kiếm đơn/phiếu trong CSKH. Bắt buộc dùng POST body (Bất biến 9: không để SĐT lên URL).
 */
export async function searchCustomers(
  q: string,
  signal?: AbortSignal
): Promise<CustomerSearchResponse> {
  return apiFetch<CustomerSearchResponse>("/api/confirmation/search/", {
    method: "POST",
    body: { q },
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? (req) => mockSearchCustomers(req, q) : undefined,
  });
}

export async function decideConfirmation(
  noteId: number,
  payload: DecidePayload,
  signal?: AbortSignal
): Promise<DecideResponse> {
  return apiFetch<DecideResponse>(`/api/confirmation/queue/${noteId}/decide/`, {
    method: "POST",
    body: payload,
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? (req) => mockDecideConfirmation(req, noteId, payload) : undefined,
  });
}


/** 409 `STALE_STATE` (SR-09): màn hình đã cũ — đơn/phiếu đổi trạng thái sau khi mở (vd job tự huỷ đã chạy). */
export function isStaleStateError(err: unknown): err is ApiError {
  return err instanceof ApiError && err.status === 409 && err.code === "STALE_STATE";
}

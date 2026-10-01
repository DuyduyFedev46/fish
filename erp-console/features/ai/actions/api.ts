import { apiFetch, type Paginated } from "@/shared/lib/http";
import type { AiActionDetail, AiActionRow } from "../types";
import {
  mockConfirmAiAction,
  mockEscalateStep,
  mockFetchAiActionCounts,
  mockFetchAiActionDetail,
  mockFetchAiActions,
  mockRejectAiAction,
  mockUndoAiAction,
} from "./mock";

// Điều kiện mock viết nguyên văn tại từng chỗ dùng (không gán ra biến) để bundler cắt nhánh mock khỏi bản build thật.
// Seed và bộ xử lý mock nằm ở ./mock.ts.

export type FetchAiActionsParams = {
  status?: string;
  scope?: "mine" | "all";
  page?: number;
  /** R1: loại chứng từ đích, vd "purchasing.purchasereceipt" (BE chấp nhận cả "purchasereceipt"). Có `target_id` thì BẮT BUỘC có cái này. */
  target_model?: string;
  /** R1: mã chứng từ đích; nhiều mã cách nhau bằng dấu phẩy (tối đa theo BE). Phiếu/lô dùng id số, đơn dùng mã SO…. */
  target_id?: string;
};

/** R1: số đề xuất theo loại chứng từ đích — `{ "purchasing.purchasereceipt": 2 }`. */
export type AiActionCounts = { by_target_model: Record<string, number> };

export async function fetchAiActions(
  params: FetchAiActionsParams = {},
  signal?: AbortSignal
): Promise<Paginated<AiActionRow>> {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.scope) qs.set("scope", params.scope);
  if (params.page) qs.set("page", String(params.page));
  if (params.target_model) qs.set("target_model", params.target_model);
  if (params.target_id) qs.set("target_id", params.target_id);
  const query = qs.toString();

  const page = await apiFetch<Paginated<AiActionRow>>(`/api/ai/actions/${query ? `?${query}` : ""}`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => mockFetchAiActions(params) : undefined,
  });
  return { ...page, results: page.results ?? [] };
}

/** R1: GET /api/ai/actions/counts/ — đếm đề xuất đang chờ theo loại chứng từ (chip "AI đề xuất" ở danh sách, dòng ở Tổng quan). */
export async function fetchAiActionCounts(
  params: { status?: string; scope?: "mine" | "all" } = {},
  signal?: AbortSignal
): Promise<AiActionCounts> {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.scope) qs.set("scope", params.scope);
  const query = qs.toString();
  const res = await apiFetch<AiActionCounts>(`/api/ai/actions/counts/${query ? `?${query}` : ""}`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => mockFetchAiActionCounts(params) : undefined,
  });
  return { by_target_model: res?.by_target_model ?? {} };
}

export async function fetchAiActionDetail(
  id: string,
  signal?: AbortSignal
): Promise<AiActionDetail> {
  return apiFetch<AiActionDetail>(`/api/ai/actions/${encodeURIComponent(id)}/`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => mockFetchAiActionDetail(id) : undefined,
  });
}

export async function confirmAiAction(
  id: string,
  confirmNonce?: string,
  signal?: AbortSignal
): Promise<{ outcome: string; result: unknown }> {
  return apiFetch<{ outcome: string; result: unknown }>(
    `/api/ai/actions/${encodeURIComponent(id)}/confirm/`,
    {
      method: "POST",
      body: { confirm_nonce: confirmNonce },
      signal,
      mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => mockConfirmAiAction(id) : undefined,
    }
  );
}

export async function rejectAiAction(
  id: string,
  reasonCode: string = "",
  signal?: AbortSignal
): Promise<{ outcome: string; action_id: string }> {
  return apiFetch<{ outcome: string; action_id: string }>(
    `/api/ai/actions/${encodeURIComponent(id)}/reject/`,
    {
      method: "POST",
      body: { reason_code: reasonCode },
      signal,
      mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => mockRejectAiAction(id) : undefined,
    }
  );
}

export async function undoAiAction(
  id: string,
  signal?: AbortSignal
): Promise<{ outcome: string; action_id: string }> {
  return apiFetch<{ outcome: string; action_id: string }>(
    `/api/ai/actions/${encodeURIComponent(id)}/undo/`,
    {
      method: "POST",
      body: {},
      signal,
      mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => mockUndoAiAction(id) : undefined,
    }
  );
}

export interface EscalatePayload {
  doc_type: string;
  doc_id: string | number;
  step_key: string;
}

export interface EscalateResponse {
  action_id: string;
  assignee_group: string;
}

export async function escalateStep(
  payload: EscalatePayload,
  signal?: AbortSignal
): Promise<EscalateResponse> {
  return apiFetch<EscalateResponse>("/api/ai/actions/escalate/", {
    method: "POST",
    body: payload,
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => mockEscalateStep(payload) : undefined,
  });
}

import { apiFetch, type Paginated } from "@/shared/lib/http";
import type { AiActionDetail, AiActionRow } from "../types";
import {
  mockConfirmAiAction,
  mockEscalateStep,
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
};

export async function fetchAiActions(
  params: FetchAiActionsParams = {},
  signal?: AbortSignal
): Promise<Paginated<AiActionRow>> {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.scope) qs.set("scope", params.scope);
  if (params.page) qs.set("page", String(params.page));
  const query = qs.toString();

  return apiFetch<Paginated<AiActionRow>>(`/api/ai/actions/${query ? `?${query}` : ""}`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? () => mockFetchAiActions(params) : undefined,
  });
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

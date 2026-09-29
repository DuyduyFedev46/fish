import { apiFetch, type MockRequest, type Paginated } from "@/shared/lib/http";
import type { AiActionDetail, AiActionRow } from "../types";

export type FetchAiActionsParams = {
  status?: string;
  scope?: "mine" | "all";
  page?: number;
};

export const mockAiActions: Paginated<AiActionRow> = {
  count: 3,
  next: null,
  previous: null,
  results: [
    {
      id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      command: "purchasing.purchasereceipt.submit",
      title: "Xác nhận phiếu nhập hàng",
      level: "C",
      status: "PENDING",
      owner_display: "AI của Lộc",
      created_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
      expires_at: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
      execute_after: null,
      undo_until: null,
      target: { type: "purchasereceipt", code: "PR-260928-01" },
      args_preview: { item_code: "CA-001", qty: "10.000" },
      downgrade_reason: null,
      result_ref: null,
    },
    {
      id: "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      command: "inventory.batch.close",
      title: "Chốt lô cá thu CA01",
      level: "B",
      status: "SCHEDULED",
      owner_display: "AI của Lộc",
      created_at: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
      expires_at: null,
      execute_after: new Date(Date.now() + 12 * 60 * 1000).toISOString(),
      undo_until: new Date(Date.now() + 12 * 60 * 1000).toISOString(),
      target: { type: "batch", code: "CA01-260928-AB12C" },
      args_preview: { batch_id: "CA01-260928-AB12C" },
      downgrade_reason: null,
      result_ref: null,
    },
    {
      id: "c3d4e5f6-a7b8-9012-cdef-123456789012",
      command: "purchasing.purchasereceipt.nhap_lo",
      title: "Nhập lô mua tại cảng",
      level: "B",
      status: "DONE",
      owner_display: "AI của Kho",
      created_at: new Date(Date.now() - 3 * 60 * 1000).toISOString(),
      expires_at: null,
      execute_after: null,
      undo_until: new Date(Date.now() + 7 * 60 * 1000).toISOString(),
      target: { type: "purchasereceipt", code: "PR-260928-02" },
      args_preview: { supplier: 1, lines: [{ item_code: "CA-001", qty: "50.000" }] },
      downgrade_reason: null,
      result_ref: { model: "purchasing.purchasereceipt", id: 102 },
      assignee_group: null,
    },
    {
      id: "d4e5f6a7-b8c9-0123-cdef-123456789013",
      command: "inventory.batch.close",
      title: "Chốt lô cá thu CA02",
      level: "C",
      status: "ESCALATED",
      owner_display: "AI của Kho",
      created_at: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
      expires_at: null,
      execute_after: null,
      undo_until: null,
      target: { type: "batch", code: "CA02-260928-XY34Z" },
      args_preview: { batch_id: "CA02-260928-XY34Z" },
      downgrade_reason: null,
      result_ref: null,
      assignee_group: "chu",
    },
  ],
};

export async function fetchAiActions(
  params: FetchAiActionsParams = {},
  signal?: AbortSignal
): Promise<Paginated<AiActionRow>> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.scope) qs.set("scope", params.scope);
  if (params.page) qs.set("page", String(params.page));
  const query = qs.toString();

  const mockHandler = (_req: MockRequest) => {
    let filtered = [...mockAiActions.results];
    if (params.status) {
      const allowed = params.status.split(",").map((s) => s.trim());
      filtered = filtered.filter((act) => allowed.includes(act.status));
    }
    return {
      status: 200,
      body: {
        count: filtered.length,
        next: null,
        previous: null,
        results: filtered,
      },
    };
  };

  return apiFetch<Paginated<AiActionRow>>(`/api/ai/actions/${query ? `?${query}` : ""}`, {
    signal,
    mock: isMock ? mockHandler : undefined,
  });
}

export async function fetchAiActionDetail(
  id: string,
  signal?: AbortSignal
): Promise<AiActionDetail> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  const mockDetail: AiActionDetail = {
    ...(mockAiActions.results.find((a) => a.id === id) || mockAiActions.results[0]),
    id,
    viewed_at: new Date().toISOString(),
    confirm_nonce: "mock-nonce-123",
  };

  return apiFetch<AiActionDetail>(`/api/ai/actions/${encodeURIComponent(id)}/`, {
    signal,
    mock: isMock ? (_req: MockRequest) => ({ status: 200, body: mockDetail }) : undefined,
  });
}

export async function confirmAiAction(
  id: string,
  confirmNonce?: string,
  signal?: AbortSignal
): Promise<{ outcome: string; result: unknown }> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<{ outcome: string; result: unknown }>(
    `/api/ai/actions/${encodeURIComponent(id)}/confirm/`,
    {
      method: "POST",
      body: { confirm_nonce: confirmNonce },
      signal,
      mock: isMock
        ? (_req: MockRequest) => {
            const target = mockAiActions.results.find((a) => a.id === id);
            if (target) {
              target.status = "CONFIRMED";
            }
            return { status: 200, body: { outcome: "done", result: { ok: true } } };
          }
        : undefined,
    }
  );
}

export async function rejectAiAction(
  id: string,
  reasonCode: string = "",
  signal?: AbortSignal
): Promise<{ outcome: string; action_id: string }> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<{ outcome: string; action_id: string }>(
    `/api/ai/actions/${encodeURIComponent(id)}/reject/`,
    {
      method: "POST",
      body: { reason_code: reasonCode },
      signal,
      mock: isMock
        ? (_req: MockRequest) => {
            const target = mockAiActions.results.find((a) => a.id === id);
            if (target) {
              target.status = "REJECTED";
            }
            return { status: 200, body: { outcome: "rejected", action_id: id } };
          }
        : undefined,
    }
  );
}

export function mockUndoAiAction(id: string): { status: number; body: { outcome: string; action_id: string } } {
  const target = mockAiActions.results.find((a) => a.id === id);
  if (target) {
    if (target.status === "SCHEDULED") {
      target.status = "CANCELLED";
    } else {
      target.status = "UNDONE";
    }
  }
  return {
    status: 200,
    body: { outcome: "undone", action_id: id },
  };
}

export async function undoAiAction(
  id: string,
  signal?: AbortSignal
): Promise<{ outcome: string; action_id: string }> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<{ outcome: string; action_id: string }>(
    `/api/ai/actions/${encodeURIComponent(id)}/undo/`,
    {
      method: "POST",
      body: {},
      signal,
      mock: isMock ? (_req: MockRequest) => mockUndoAiAction(id) : undefined,
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
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<EscalateResponse>("/api/ai/actions/escalate/", {
    method: "POST",
    body: payload,
    signal,
    mock: isMock
      ? (_req: MockRequest) => {
          const actionId = `esc-${Date.now()}`;
          const newAction: AiActionRow = {
            id: actionId,
            command: `${payload.doc_type}.${payload.step_key}`,
            title: `Nhờ hỗ trợ bước ${payload.step_key}`,
            level: "C",
            status: "ESCALATED",
            owner_display: "AI của Bạn",
            created_at: new Date().toISOString(),
            expires_at: null,
            execute_after: null,
            undo_until: null,
            target: { type: payload.doc_type, code: String(payload.doc_id) },
            args_preview: { step_key: payload.step_key },
            downgrade_reason: null,
            result_ref: null,
            assignee_group: "chu",
          };
          mockAiActions.results.unshift(newAction);
          mockAiActions.count += 1;
          return {
            status: 201,
            body: { action_id: actionId, assignee_group: "chu" },
          };
        }
      : undefined,
  });
}



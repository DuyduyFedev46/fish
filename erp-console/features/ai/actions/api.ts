import { apiFetch, type MockRequest, type Paginated } from "@/shared/lib/http";
import type { AiActionRow } from "../types";

export type FetchAiActionsParams = {
  status?: string;
  scope?: "mine" | "all";
  page?: number;
};

const mockAiActions: Paginated<AiActionRow> = {
  count: 1,
  next: null,
  previous: null,
  results: [
    {
      id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      command: "purchasing.purchasereceipt.submit",
      title: "Xác nhận phiếu nhập hàng",
      kind: "write",
      level: "C",
      status: "PENDING",
      owner_display: "AI của Lộc",
      created_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
      execute_after: null,
      undo_until: null,
      viewed_at: null,
      target: { type: "purchasereceipt", code: "PR-260928-01" },
      args_preview: { item_code: "CA-001", qty: "10.000" },
      downgrade_reason: null,
      confirm_nonce: "mock-nonce-123",
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

  return apiFetch<Paginated<AiActionRow>>(`/api/ai/actions/${query ? `?${query}` : ""}`, {
    signal,
    mock: isMock ? (_req: MockRequest) => ({ status: 200, body: mockAiActions }) : undefined,
  });
}

export async function fetchAiActionDetail(
  id: string,
  signal?: AbortSignal
): Promise<AiActionRow> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  const mockDetail: AiActionRow = {
    ...mockAiActions.results[0],
    id,
    viewed_at: new Date().toISOString(),
  };

  return apiFetch<AiActionRow>(`/api/ai/actions/${encodeURIComponent(id)}/`, {
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
      body: JSON.stringify({ confirm_nonce: confirmNonce }),
      signal,
      mock: isMock
        ? (_req: MockRequest) => ({ status: 200, body: { outcome: "done", result: { ok: true } } })
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
      body: JSON.stringify({ reason_code: reasonCode }),
      signal,
      mock: isMock
        ? (_req: MockRequest) => ({ status: 200, body: { outcome: "rejected", action_id: id } })
        : undefined,
    }
  );
}

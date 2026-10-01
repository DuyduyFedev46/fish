// Dữ liệu và bộ xử lý MOCK của màn Việc AI + nút "Nhờ" (chỉ dùng khi NEXT_PUBLIC_USE_MOCK=1).
// Tách khỏi api.ts để bản build thật không mang seed (api.ts được màn nghiệp vụ import tĩnh vì nút "Nhờ" — SR-20/F6-1).
// api.ts chỉ tham chiếu file này bên trong nhánh `process.env.NEXT_PUBLIC_USE_MOCK === "1"` nên bundler cắt được.

import type { Paginated } from "@/shared/lib/http";
import { ROLE } from "@/shared/lib/roles";
import { RECEIVE_BATCHES_COMMAND_ID } from "../commandGroups";
import type { AiActionDetail, AiActionRow } from "../types";
import type { EscalatePayload } from "./api";

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
      command: RECEIVE_BATCHES_COMMAND_ID,
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
      assignee_group: ROLE.owner,
    },
  ],
};

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

export function mockFetchAiActions(params: { status?: string }) {
  let filtered = [...mockAiActions.results];
  if (params.status) {
    const allowed = params.status.split(",").map((s) => s.trim());
    filtered = filtered.filter((act) => allowed.includes(act.status));
  }
  return {
    status: 200,
    body: { count: filtered.length, next: null, previous: null, results: filtered },
  };
}

export function mockFetchAiActionDetail(id: string) {
  const detail: AiActionDetail = {
    ...(mockAiActions.results.find((a) => a.id === id) || mockAiActions.results[0]),
    id,
    viewed_at: new Date().toISOString(),
    confirm_nonce: "mock-nonce-123",
  };
  return { status: 200, body: detail };
}

export function mockConfirmAiAction(id: string) {
  const target = mockAiActions.results.find((a) => a.id === id);
  if (target) target.status = "CONFIRMED";
  return { status: 200, body: { outcome: "done", result: { ok: true } } };
}

export function mockRejectAiAction(id: string) {
  const target = mockAiActions.results.find((a) => a.id === id);
  if (target) target.status = "REJECTED";
  return { status: 200, body: { outcome: "rejected", action_id: id } };
}

export function mockEscalateStep(payload: EscalatePayload) {
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
    assignee_group: ROLE.owner,
  };
  mockAiActions.results.unshift(newAction);
  mockAiActions.count += 1;
  return { status: 201, body: { action_id: actionId, assignee_group: ROLE.owner } };
}

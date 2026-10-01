import { apiFetch, type MockRequest } from "@/shared/lib/http";
import { RECEIVE_BATCHES_COMMAND_ID } from "../commandGroups";
import { isSameCommand } from "../legacyIds";
import type { CallRequest, CallResponse } from "../types";

export async function callCommand(
  commandId: string,
  request: CallRequest = {},
  signal?: AbortSignal
): Promise<CallResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  const mockHandler = (_req: MockRequest) => {
    const isList = commandId.endsWith(".list");
    const isScheduled =
      commandId.includes("scheduled") ||
      commandId.endsWith(".defer") ||
      (request.args && (request.args as Record<string, unknown>)._defer === true);
    const isLevelBWrite =
      isSameCommand(commandId, RECEIVE_BATCHES_COMMAND_ID) ||
      commandId.includes(".b_action") ||
      (request.args && (request.args as Record<string, unknown>)._level === "B");

    if (isList) {
      const mockResponse: CallResponse = {
        outcome: "done",
        level: "A",
        action_id: "mock-action-read-12345",
        result: {
          rows: [{ id: 1, code: "MOCK-01", name: "Dữ liệu mẫu" }],
          total: 1,
          truncated: false,
        },
        downgrade_reason: null,
      };
      return { status: 200, body: mockResponse };
    }

    if (isScheduled) {
      const mockResponse: CallResponse = {
        outcome: "scheduled",
        level: "B",
        action_id: "mock-action-scheduled-12345",
        execute_after: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
        undo_until: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
        downgrade_reason: null,
        preview: {
          target: { type: "document", code: String(request.target_id || "1") },
        },
      };
      return { status: 200, body: mockResponse };
    }

    if (isLevelBWrite) {
      const mockResponse: CallResponse = {
        outcome: "done",
        level: "B",
        action_id: "mock-action-b-uuid-12345",
        result: {
          ok: true,
          receipt: { id: 101, code: "PR-260928-02", status: "SUBMITTED" },
        },
        undo_until: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
        downgrade_reason: null,
        preview: {
          target: { type: "purchasereceipt", code: "PR-260928-02" },
        },
      };
      return { status: 200, body: mockResponse };
    }

    const mockResponse: CallResponse = {
      outcome: "proposal",
      level: "C",
      action_id: "mock-action-uuid-12345",
      result: {
        rows: [{ id: 1, code: "MOCK-01", name: "Dữ liệu mẫu" }],
        total: 1,
        truncated: false,
      },
      expires_at: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
      downgrade_reason: null,
      preview: {
        target: { type: "document", code: String(request.target_id || "1") },
      },
    };
    return { status: 200, body: mockResponse };
  };

  return apiFetch<CallResponse>(`/api/ai/commands/${encodeURIComponent(commandId)}/call/`, {
    method: "POST",
    body: request,
    signal,
    mock: isMock ? mockHandler : undefined,
  });

}

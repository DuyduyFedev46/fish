import { apiFetch, type MockRequest } from "@/shared/lib/http";
import type { CallRequest, CallResponse } from "../types";

export async function callCommand(
  commandId: string,
  request: CallRequest = {},
  signal?: AbortSignal
): Promise<CallResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  const mockHandler = (_req: MockRequest) => {
    const mockResponse: CallResponse = {
      outcome: commandId.endsWith(".list") ? "done" : "proposal",
      level: commandId.endsWith(".list") ? "A" : "C",
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
    body: JSON.stringify(request),
    signal,
    mock: isMock ? mockHandler : undefined,
  });
}

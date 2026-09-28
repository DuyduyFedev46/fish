// Kênh thực thi lệnh (S02) — mọi thực thi nghiệp vụ (từ UI hay AI) đi qua một kênh duy nhất.
// BOUNDARY (C.2): file này KHÔNG được import gì từ runtime/ · voice/ · chat/ — chỉ gọi HTTP.
// Lô 1–2: chat LLMock chưa gọi kênh này; dành cho S02 UI (đề xuất → xác nhận) ở lô sau.

import { apiFetch } from "@/shared/lib/http";
import { mockConfirmProposal, mockExecute, mockGetProposal, mockPropose } from "./mock";
import type { ExecuteRequest, ExecuteResponse, ProposeRequest, ProposeResponse, Proposal } from "./types";

const useMock = () => process.env.NEXT_PUBLIC_USE_MOCK === "1";

/** POST /api/commands/execute/ — kênh AI + lệnh cần xác nhận → trả đề xuất thay vì thực thi (S02-AC2). */
export function executeCommand(req: ExecuteRequest, signal?: AbortSignal): Promise<ExecuteResponse | ProposeResponse> {
  return apiFetch<ExecuteResponse | ProposeResponse>("/api/commands/execute/", {
    method: "POST",
    body: req,
    signal,
    mock: useMock() ? mockExecute : undefined,
  });
}

/** POST /api/commands/propose/ — sinh bản nháp chờ xác nhận (TTL 15 phút). */
export function proposeCommand(req: ProposeRequest, signal?: AbortSignal): Promise<ProposeResponse> {
  return apiFetch<ProposeResponse>("/api/commands/propose/", {
    method: "POST",
    body: req,
    signal,
    mock: useMock() ? mockPropose : undefined,
  });
}

/** GET /api/commands/proposals/<id>/ */
export function getProposal(id: number, signal?: AbortSignal): Promise<Proposal> {
  return apiFetch<Proposal>(`/api/commands/proposals/${id}/`, {
    signal,
    mock: useMock() ? mockGetProposal : undefined,
  });
}

/** POST /api/commands/proposals/<id>/confirm/ — kênh ui, người xác nhận (BR-AI-06). */
export function confirmProposal(id: number, signal?: AbortSignal): Promise<ExecuteResponse> {
  return apiFetch<ExecuteResponse>(`/api/commands/proposals/${id}/confirm/`, {
    method: "POST",
    body: { channel: "ui" },
    signal,
    mock: useMock() ? mockConfirmProposal : undefined,
  });
}

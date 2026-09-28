// API module AI — endpoints Lô 1–3 (S05 status, S03 audit-logs do features/audit gọi).
// BOUNDARY (C.2): file này KHÔNG được import gì từ runtime/ · voice/ · chat/ — chỉ gọi HTTP qua shared/lib/http.

import { apiFetch, type Paginated } from "@/shared/lib/http";
import { mockStatus, mockAuditLogs } from "./mock";
import type { AiStatus, AuditLogParams, AuditLogRow } from "./types";

/** GET /api/ai/status/ — luôn 200 kể cả AI tắt; lỗi mạng → gate coi như tắt (S05-AC5 fail-closed). */
export function getAiStatus(signal?: AbortSignal): Promise<AiStatus> {
  return apiFetch<AiStatus>("/api/ai/status/", {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStatus : undefined,
  });
}

/** GET /api/audit-logs/ — màn Nhật ký hoạt động (S03). Mock Lô 1 đặt ở features/ai/mock.ts theo phân công. */
export function getAuditLogs(params: AuditLogParams, page = 1, signal?: AbortSignal): Promise<Paginated<AuditLogRow>> {
  const qs = new URLSearchParams();
  if (params.actor_kind) qs.set("actor_kind", params.actor_kind);
  if (params.action?.trim()) qs.set("action", params.action.trim());
  if (page > 1) qs.set("page", String(page));
  const s = qs.toString();
  return apiFetch<Paginated<AuditLogRow>>(`/api/audit-logs/${s ? `?${s}` : ""}`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockAuditLogs : undefined,
  });
}

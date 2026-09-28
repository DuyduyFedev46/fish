// API module AI — endpoints Lô 1–2 (S01 catalog, S05 status, S03 audit-logs do features/audit gọi).
// BOUNDARY (C.2): file này KHÔNG được import gì từ runtime/ · voice/ · chat/ — chỉ gọi HTTP qua shared/lib/http.
// Khi BE Lô 1 xong: bỏ mock audit-logs (features/audit/api.ts chuyển sang mock riêng hoặc bỏ mock).

import { apiFetch, type Paginated } from "@/shared/lib/http";
import { mockCatalog, mockStatus, mockAuditLogs } from "./mock";
import type { AiStatus, AuditLogParams, AuditLogRow, CommandCatalog } from "./types";

/** GET /api/ai/status/ — luôn 200 kể cả AI tắt; lỗi mạng → gate coi như tắt (S05-AC5 fail-closed). */
export function getAiStatus(signal?: AbortSignal): Promise<AiStatus> {
  return apiFetch<AiStatus>("/api/ai/status/", {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockStatus : undefined,
  });
}

/** GET /api/commands/catalog/ — đã lọc theo quyền người gọi (S01-AC2). */
export function getCommandCatalog(signal?: AbortSignal): Promise<CommandCatalog> {
  return apiFetch<CommandCatalog>("/api/commands/catalog/", {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockCatalog : undefined,
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

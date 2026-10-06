// API module audit — GET /api/audit-logs/ (S03; thêm `?actor=` ở R16). Chỉ đọc: nhật ký không có sửa/xoá (BR-PQ-06).

import { apiFetch, type Paginated } from "@/shared/lib/http";
import { mockAuditLogs } from "./mock";
import type { AuditLogParams, AuditLogRow } from "./types";

/** GET /api/audit-logs/?page=&actor_kind=&action=&actor= — mới nhất trước. Thiếu quyền → 403. */
export function getAuditLogs(params: AuditLogParams, page = 1, signal?: AbortSignal): Promise<Paginated<AuditLogRow>> {
  const qs = new URLSearchParams();
  if (params.actor_kind) qs.set("actor_kind", params.actor_kind);
  if (params.action?.trim()) qs.set("action", params.action.trim());
  if (params.actor) qs.set("actor", String(params.actor));
  if (page > 1) qs.set("page", String(page));
  const s = qs.toString();
  return apiFetch<Paginated<AuditLogRow>>(`/api/audit-logs/${s ? `?${s}` : ""}`, {
    signal,
    mock: process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockAuditLogs : undefined,
  });
}

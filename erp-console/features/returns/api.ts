// API module Hàng hoàn (ED-26) — contract BE Lô 9 (R9): backend/apps/inventory/returns/api.py.
//   GET  /api/inventory/returns/?status=&month=&page=   (20 dòng/trang; người giao chỉ thấy phiếu của phiếu giao gán cho mình)
//   GET  /api/inventory/returns/{id}/                    (phiếu người khác của người giao → 404)
//   POST /api/inventory/returns/                         {delivery_note, batch, qty, note?}  (batch = id lô, KHÔNG phải mã lô)
//   POST /api/inventory/returns/{id}/approve/            {decision: RESTOCK | WRITE_OFF}      (cần inventory.approve_returntostock; đã duyệt → 409 STALE_STATE)
//   POST /api/inventory/returns/{id}/cancel/            body rỗng: huỷ phiếu còn Chờ duyệt (Lô bổ sung A #8). Quyền: người duyệt/người sửa, hoặc người tạo
//                                                        phiếu huỷ phiếu của mình; đã duyệt/đã huỷ → 409 STALE_STATE
//   POST /api/inventory/returns/{id}/delete/            body rỗng: xoá mềm phiếu Nháp/Đã huỷ, chỉ Chủ (#8); 200 {status:"deleted"}, 400 RETURN_DELETE_NOT_ALLOWED, 409 STALE_STATE
//   GET  /api/guidance/return/{id}/                      chỉ dùng `timeline`
// Hộp F2m lấy phiếu giao và dòng hàng qua hàm công khai của module Giao hàng (fetchDeliveryNotes / fetchDeliveryNoteDetail),
// không đọc ruột module đó. Mọi dữ liệu nhập (ghi chú) chỉ đi trong thân request, không vào URL, storage hay log.

import { fetchDeliveryNoteDetail, fetchDeliveryNotes } from "@/features/deliveries/api";
import type { DeliveryNoteItem } from "@/features/deliveries/types";
import type { GuidanceData } from "@/features/guidance/types";
import { apiFetch, type Paginated } from "@/shared/lib/http";
import { mockReturnsApi } from "./mock";
import type { ApproveDecision, CreateReturnBody, ReturnItem, ReturnListParams, ReturnableLine } from "./types";

const BASE = "/api/inventory/returns/";
const MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "1" ? mockReturnsApi : undefined;

export function returnListQuery(params: ReturnListParams, page: number): string {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.month) qs.set("month", params.month);
  if (page > 1) qs.set("page", String(page));
  const s = qs.toString();
  return s ? `?${s}` : "";
}

export function listReturns(params: ReturnListParams, page = 1, signal?: AbortSignal): Promise<Paginated<ReturnItem>> {
  return apiFetch<Paginated<ReturnItem>>(BASE + returnListQuery(params, page), { signal, mock: MOCK });
}

export function getReturn(id: number, signal?: AbortSignal): Promise<ReturnItem> {
  return apiFetch<ReturnItem>(`${BASE}${id}/`, { signal, mock: MOCK });
}

export function createReturn(body: CreateReturnBody): Promise<ReturnItem> {
  return apiFetch<ReturnItem>(BASE, { method: "POST", body, mock: MOCK });
}

export function approveReturn(id: number, decision: ApproveDecision): Promise<ReturnItem> {
  return apiFetch<ReturnItem>(`${BASE}${id}/approve/`, { method: "POST", body: { decision }, mock: MOCK });
}

/** Huỷ phiếu hàng hoàn còn Chờ duyệt. Phiếu đã xử lý → 409 STALE_STATE ("hãy tải lại"). */
export function cancelReturn(id: number): Promise<ReturnItem> {
  return apiFetch<ReturnItem>(`${BASE}${id}/cancel/`, { method: "POST", body: {}, mock: MOCK });
}

/** Xoá phiếu hàng hoàn (xoá mềm, #8): chỉ Chủ, chỉ phiếu Nháp hoặc Đã huỷ. Đã duyệt → 400 RETURN_DELETE_NOT_ALLOWED; vừa bị xoá/đổi → 409 STALE_STATE; xoá rồi → 404. */
export function deleteReturn(id: number): Promise<{ status: "deleted"; id: number }> {
  return apiFetch<{ status: "deleted"; id: number }>(`${BASE}${id}/delete/`, { method: "POST", body: {}, mock: MOCK });
}

/** Dòng thời gian của phiếu (guidance `return`, chỉ timeline). */
export function getReturnTimeline(id: number, signal?: AbortSignal): Promise<GuidanceData> {
  return apiFetch<GuidanceData>(`/api/guidance/return/${id}/`, { signal, mock: MOCK });
}

const NOTE_PAGES_MAX = 5;

/**
 * Phiếu giao đang giao hoặc giao thất bại mà người dùng được nhập hàng hoàn (BE đã lọc theo phạm vi người xem).
 * Dừng ở NOTE_PAGES_MAX trang; còn trang sau thì `truncated` = true để hộp báo "Chỉ hiện n phiếu giao gần nhất" (TL9-L6).
 */
export async function listReturnableNotes(signal?: AbortSignal): Promise<{ notes: DeliveryNoteItem[]; truncated: boolean }> {
  const notes: DeliveryNoteItem[] = [];
  let truncated = false;
  for (let page = 1; page <= NOTE_PAGES_MAX; page++) {
    const res = await fetchDeliveryNotes({ status: "DELIVERING,FAILED", page }, signal);
    notes.push(...res.results);
    if (!res.next) break;
    if (page === NOTE_PAGES_MAX) truncated = true;
  }
  return { notes, truncated };
}

/** Dòng hàng của một phiếu giao: mặt hàng, lô, số kg đã giao, `batch_pk`, `returned_qty` (BE Lô 9). */
export async function getNoteLines(id: number, signal?: AbortSignal): Promise<ReturnableLine[]> {
  const detail = await fetchDeliveryNoteDetail(id, signal);
  return detail.lines as ReturnableLine[];
}

import { apiFetch } from "@/shared/lib/http";
import {
  mockGetDeliverers,
  mockGetDeliveryLabel,
  mockGetDeliveryNoteDetail,
  mockListDeliveryNotes,
  mockPostDeliveryAssign,
  mockPostDeliveryLabelPrint,
  mockPostDeliveryLabelVoid,
  mockPostDeliveryNoteStatus,
} from "./mock";
import type {
  AssignDeliveryResponse,
  Deliverer,
  DeliveryFailureReason,
  DeliveryListResponse,
  DeliveryNoteDetail,
  DeliveryNoteItem,
  LabelData,
  LabelPrintReason,
  PrintDeliveryLabelResponse,
  VoidLabelResponse,
} from "./types";

export async function fetchDeliveryNotes(
  params: {
    status?: string;
    completed_from?: string;
    /** `me` = chỉ phiếu gán cho mình (Việc giao của tôi); số = id người giao (chỉ vai đủ phạm vi). */
    assigned_to?: string;
    page?: number;
  },
  signal?: AbortSignal
): Promise<DeliveryListResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.completed_from) query.set("completed_from", params.completed_from);
  if (params.assigned_to) query.set("assigned_to", params.assigned_to);
  if (params.page) query.set("page", String(params.page));

  const qs = query.toString();
  const url = `/api/delivery/notes/${qs ? `?${qs}` : ""}`;

  return apiFetch<DeliveryListResponse>(url, {
    signal,
    mock: isMock ? mockListDeliveryNotes : undefined,
  });
}

export async function fetchDeliveryNoteDetail(
  id: number,
  signal?: AbortSignal
): Promise<DeliveryNoteDetail> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<DeliveryNoteDetail>(`/api/delivery/notes/${id}/`, {
    signal,
    mock: isMock ? mockGetDeliveryNoteDetail : undefined,
  });
}

export type PackDeliveryNoteResponse = DeliveryNoteDetail & {
  already?: boolean;
};

export async function packDeliveryNote(
  id: number,
  fromStatus = "PREPARING",
  signal?: AbortSignal
): Promise<PackDeliveryNoteResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<PackDeliveryNoteResponse>(`/api/delivery/notes/${id}/status/`, {
    method: "POST",
    body: {
      to_status: "READY",
      from_status: fromStatus,
    },
    signal,
    mock: isMock ? mockPostDeliveryNoteStatus : undefined,
  });
}

export async function fetchDeliveryLabel(
  id: number,
  printNo?: number,
  signal?: AbortSignal
): Promise<LabelData> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  const qs = printNo ? `?print_no=${printNo}` : "";
  return apiFetch<LabelData>(`/api/delivery/notes/${id}/label/${qs}`, {
    signal,
    mock: isMock ? (req) => mockGetDeliveryLabel(req, id, printNo) : undefined,
  });
}

export async function printDeliveryLabel(
  id: number,
  requestId?: string,
  signal?: AbortSignal,
  reason?: LabelPrintReason
): Promise<PrintDeliveryLabelResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  const reqId =
    requestId ||
    (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : undefined);
  return apiFetch<PrintDeliveryLabelResponse>(`/api/delivery/notes/${id}/label/print/`, {
    method: "POST",
    body: reason ? { request_id: reqId, reason } : { request_id: reqId },
    signal,
    mock: isMock ? (req) => mockPostDeliveryLabelPrint(req, id) : undefined,
  });
}

export async function voidDeliveryLabel(
  id: number,
  printNo: number,
  signal?: AbortSignal
): Promise<VoidLabelResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<VoidLabelResponse>(`/api/delivery/notes/${id}/label/void/`, {
    method: "POST",
    body: { print_no: printNo },
    signal,
    mock: isMock ? (req) => mockPostDeliveryLabelVoid(req, id) : undefined,
  });
}



/** Trả về phiếu theo bản danh sách (không có dòng hàng, SĐT): màn tải lại chi tiết sau khi đổi trạng thái. */
export type DeliveryStatusResponse = DeliveryNoteItem & { already?: boolean; needs_decision?: boolean };

async function postStatus(id: number, body: Record<string, unknown>, signal?: AbortSignal): Promise<DeliveryStatusResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<DeliveryStatusResponse>(`/api/delivery/notes/${id}/status/`, {
    method: "POST",
    body,
    signal,
    mock: isMock ? mockPostDeliveryNoteStatus : undefined,
  });
}

/** READY → DELIVERING (nhận hàng đi giao; cũng dùng để giao lại phiếu FAILED). `from_status` chặn thao tác trên bản đã cũ. */
export function startDelivery(id: number, fromStatus: string, signal?: AbortSignal): Promise<DeliveryStatusResponse> {
  return postStatus(id, { to_status: "DELIVERING", from_status: fromStatus }, signal);
}

/** DELIVERING → COMPLETED. */
export function completeDelivery(id: number, signal?: AbortSignal): Promise<DeliveryStatusResponse> {
  return postStatus(id, { to_status: "COMPLETED", from_status: "DELIVERING" }, signal);
}

/**
 * B5: DELIVERING → FAILED. `failure_reason` bắt buộc; "Khác" bắt buộc `failure_note`; ghi chú tối đa 200 ký tự và
 * không được chứa dãy 9 chữ số trở lên (400 `DELIVERY_FAILURE_*`). Ghi chú là chữ tự do: không log, không lưu máy.
 */
export function reportDeliveryFailure(
  id: number,
  input: { reason: DeliveryFailureReason; note?: string },
  signal?: AbortSignal
): Promise<DeliveryStatusResponse> {
  const body: Record<string, unknown> = { to_status: "FAILED", from_status: "DELIVERING", failure_reason: input.reason };
  if (input.note && input.note.trim()) body.failure_note = input.note.trim();
  return postStatus(id, body, signal);
}

/** B6: người giao đang làm kèm số phiếu đang giao / chờ lấy (cần quyền giao người). Mảng thường, không phân trang. */
export async function fetchDeliverers(signal?: AbortSignal): Promise<Deliverer[]> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<Deliverer[]>("/api/delivery/deliverers/", { signal, mock: isMock ? mockGetDeliverers : undefined });
}

/**
 * B6: giao / đổi người giao. `expectedAssignedTo` = người giao màn đang hiển thị (null = chưa có); lệch → 409 `STALE_STATE`
 * (màn hiện ConflictBanner). Cùng người → 200 kèm `already: true`.
 */
export async function assignDeliveryNote(
  id: number,
  input: { assignedTo: number; expectedAssignedTo: number | null },
  signal?: AbortSignal
): Promise<AssignDeliveryResponse> {
  const isMock = process.env.NEXT_PUBLIC_USE_MOCK === "1";
  return apiFetch<AssignDeliveryResponse>(`/api/delivery/notes/${id}/assign/`, {
    method: "POST",
    body: { assigned_to: input.assignedTo, expected_assigned_to: input.expectedAssignedTo },
    signal,
    mock: isMock ? mockPostDeliveryAssign : undefined,
  });
}

"use client";

// Gửi form theo UI-RULES §6.6: lỗi → GIỮ NGUYÊN giá trị đã nhập (state do màn giữ, hook không đụng tới), alert đỏ đầu form,
// nút chính đổi thành "Thử lại"; đang gửi thì chặn bấm đúp (kể cả hai lần bấm trong cùng một khung hình).
// Xung đột phiên bản (STALE_STATE / STALE_VERSION / 409 có updated_at: người khác vừa sửa) KHÔNG hiện alert đỏ mà đưa vào `conflict` để màn bật ConflictBanner.
// Không ghi dữ liệu người dùng nhập vào log/localStorage/URL — hook chỉ giữ thông điệp lỗi.

import { useCallback, useRef, useState } from "react";
import { ApiError } from "@/shared/lib/http";

export type SubmitConflict = { updatedAt?: string; updatedByName?: string };

export type SubmitState = {
  /** Đang gửi. */
  submitting: boolean;
  /** Thông điệp lỗi (đã dịch) của lần gửi gần nhất; null = chưa lỗi. */
  error: string | null;
  /** Lỗi theo từng trường (400 DRF `{ field: ["…"] }`), khoá = tên trường BE. */
  fieldErrors: Record<string, string>;
  /** Lần gửi gần nhất lỗi → nút chính hiện "Thử lại". */
  failed: boolean;
  /** Có xung đột phiên bản (409 / STALE_STATE). */
  conflict: SubmitConflict | null;
};

const IDLE: SubmitState = { submitting: false, error: null, fieldErrors: {}, failed: false, conflict: null };

const CONFLICT_CODES = new Set(["STALE_STATE", "STALE_VERSION"]);

/**
 * Xung đột PHIÊN BẢN (người khác vừa sửa bản ghi này): `code` là STALE_STATE / STALE_VERSION, hoặc 409 có `updated_at` trong thân.
 * Các 409 khác (CLAIMED, CONTENT_WARNINGS, AI_ACTION_ALREADY_DECIDED, POLICY_CHANGED…) là lỗi thường: hiện câu lý do của BE (02b §2.3).
 */
export function isConflictError(err: unknown): boolean {
  if (!(err instanceof ApiError)) return false;
  if (err.code && CONFLICT_CODES.has(err.code)) return true;
  const d = err.details && typeof err.details === "object" ? (err.details as Record<string, unknown>) : null;
  return err.status === 409 && typeof d?.updated_at === "string";
}

/** Lấy `updated_at` / `updated_by_name` (nếu BE kèm) từ thân lỗi; không có thì trả object rỗng. */
export function conflictOf(err: unknown): SubmitConflict {
  const d = err instanceof ApiError && err.details && typeof err.details === "object" ? (err.details as Record<string, unknown>) : {};
  return {
    updatedAt: typeof d.updated_at === "string" ? d.updated_at : undefined,
    updatedByName: typeof d.updated_by_name === "string" ? d.updated_by_name : undefined,
  };
}

/** Gom lỗi theo trường từ thân 400 của DRF; bỏ qua khoá không phải chuỗi/mảng chuỗi. */
export function fieldErrorsOf(err: unknown): Record<string, string> {
  if (!(err instanceof ApiError) || err.status !== 400 || !err.details || typeof err.details !== "object") return {};
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(err.details as Record<string, unknown>)) {
    const first = Array.isArray(v) ? v[0] : v;
    if (typeof first === "string" && first.trim()) out[k] = first;
  }
  return out;
}

/** Nhãn nút chính: "Thử lại" sau một lần gửi lỗi, không thì nhãn nói rõ việc. */
export function primaryLabel(label: string, failed: boolean): string {
  return failed ? "Thử lại" : label;
}

/** Trạng thái sau khi một lần gửi ném lỗi `err` (hàm thuần để vitest; hook chỉ gọi lại). */
export function stateAfterError(err: unknown): SubmitState {
  if (isConflictError(err)) return { submitting: false, error: null, fieldErrors: {}, failed: true, conflict: conflictOf(err) };
  const message = err instanceof Error && err.message ? err.message : "Chưa lưu được. Kiểm tra mạng rồi bấm lại.";
  return { submitting: false, error: message, fieldErrors: fieldErrorsOf(err), failed: true, conflict: null };
}

export function useSubmit<T>(run: () => Promise<T>, opts: { onSuccess?: (result: T) => void } = {}) {
  const [state, setState] = useState<SubmitState>(IDLE);
  const inFlight = useRef(false);
  const runRef = useRef(run);
  runRef.current = run;
  const onSuccessRef = useRef(opts.onSuccess);
  onSuccessRef.current = opts.onSuccess;

  const submit = useCallback(async (): Promise<boolean> => {
    if (inFlight.current) return false; // chặn bấm đúp
    inFlight.current = true;
    setState((s) => ({ ...s, submitting: true, error: null, fieldErrors: {}, conflict: null }));
    try {
      const result = await runRef.current();
      setState(IDLE);
      onSuccessRef.current?.(result);
      return true;
    } catch (err) {
      setState(stateAfterError(err));
      return false;
    } finally {
      inFlight.current = false;
    }
  }, []);

  const reset = useCallback(() => setState(IDLE), []);
  return { ...state, submit, reset };
}

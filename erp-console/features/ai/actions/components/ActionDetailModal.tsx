"use client";

import React, { useEffect, useState } from "react";
import type { AiActionDetail, AiActionRow } from "../../types";

interface ActionDetailModalProps {
  action: AiActionDetail | AiActionRow | null;
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (actionId: string, nonce?: string) => Promise<void>;
  onReject: (actionId: string) => Promise<void>;
  onUndo?: (actionId: string) => Promise<void>;
  isSubmitting?: boolean;
}

export function ActionDetailModal({
  action,
  isOpen,
  onClose,
  onConfirm,
  onReject,
  onUndo,
  isSubmitting = false,
}: ActionDetailModalProps) {
  const [countdown, setCountdown] = useState<number>(3);
  const [scheduledSeconds, setScheduledSeconds] = useState<number>(0);
  const [undoSeconds, setUndoSeconds] = useState<number>(0);

  useEffect(() => {
    if (isOpen && action) {
      setCountdown(3);
      const timer = setInterval(() => {
        setCountdown((prev) => (prev > 0 ? prev - 1 : 0));
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [isOpen, action?.id]);

  useEffect(() => {
    if (isOpen && action?.status === "SCHEDULED" && action.execute_after) {
      const calc = () =>
        Math.max(0, Math.floor((new Date(action.execute_after!).getTime() - Date.now()) / 1000));
      setScheduledSeconds(calc());
      const timer = setInterval(() => {
        setScheduledSeconds(calc());
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [isOpen, action?.status, action?.execute_after]);

  useEffect(() => {
    if (isOpen && action?.undo_until && (action.status === "DONE" || action.status === "CONFIRMED")) {
      const calc = () =>
        Math.max(0, Math.floor((new Date(action.undo_until!).getTime() - Date.now()) / 1000));
      setUndoSeconds(calc());
      const timer = setInterval(() => {
        setUndoSeconds(calc());
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [isOpen, action?.status, action?.undo_until]);

  if (!isOpen || !action) {
    return null;
  }

  const isPending = action.status === "PENDING";
  const isScheduled = action.status === "SCHEDULED";
  const canUndo =
    (action.status === "DONE" || action.status === "CONFIRMED") &&
    action.undo_until &&
    undoSeconds > 0;

  const formatMmSs = (sec: number) => {
    const m = Math.floor(sec / 60).toString().padStart(2, "0");
    const s = (sec % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  const handleCancelScheduled = async () => {
    if (!confirm("Bạn có chắc chắn muốn huỷ lịch thực thi thao tác này?")) return;
    if (onUndo) {
      await onUndo(action.id);
    }
  };

  const handleUndoDone = async () => {
    if (!confirm("Bạn có chắc chắn muốn hoàn tác thao tác này? Chứng từ liên quan sẽ chuyển trạng thái Đã huỷ.")) return;
    if (onUndo) {
      await onUndo(action.id);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl dark:bg-gray-800">
        <div className="flex items-center justify-between border-b pb-3 dark:border-gray-700">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Chi tiết việc AI
            </h3>
            <span className="inline-block mt-1 rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900 dark:text-blue-200">
              {action.owner_display}
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          >
            ✕
          </button>
        </div>

        <div className="mt-4 space-y-4 text-sm text-gray-600 dark:text-gray-300">
          <div>
            <span className="font-medium text-gray-700 dark:text-gray-200">Lệnh:</span>{" "}
            <span className="font-semibold text-gray-900 dark:text-gray-100">{action.title}</span> (
            <code className="text-xs">{action.command}</code>)
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <span className="font-medium text-gray-700 dark:text-gray-200">Mức tự chủ:</span>{" "}
              <span className="font-semibold">{action.level}</span>
            </div>
            <div>
              <span className="font-medium text-gray-700 dark:text-gray-200">Trạng thái:</span>{" "}
              <span
                className={`rounded px-2 py-0.5 font-medium text-xs ${
                  action.status === "SCHEDULED"
                    ? "bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300"
                    : action.status === "PENDING"
                    ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                    : action.status === "DONE" || action.status === "CONFIRMED"
                    ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                    : action.status === "CANCELLED" || action.status === "REJECTED"
                    ? "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                    : "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200"
                }`}
              >
                {action.status === "SCHEDULED" ? "ĐÃ LÊN LỊCH (SCHEDULED)" : action.status}
              </span>
            </div>
          </div>

          {action.target && action.target.code && (
            <div>
              <span className="font-medium text-gray-700 dark:text-gray-200">Chứng từ đích:</span>{" "}
              <span className="font-mono">{action.target.type} #{action.target.code}</span>
            </div>
          )}

          {action.expires_at && isPending && (
            <div className="text-xs text-amber-600 dark:text-amber-400">
              Hết hạn duyệt lúc: {new Date(action.expires_at).toLocaleTimeString("vi-VN")}
            </div>
          )}

          {isScheduled && action.execute_after && (
            <div className="rounded-md border border-purple-200 bg-purple-50 p-2.5 text-xs text-purple-900 dark:border-purple-800 dark:bg-purple-950 dark:text-purple-200">
              <span className="font-semibold">Dự kiến tự thực thi sau:</span>{" "}
              <span className="font-mono font-bold">{formatMmSs(scheduledSeconds)}</span> (lúc{" "}
              {new Date(action.execute_after).toLocaleTimeString("vi-VN")})
            </div>
          )}

          {canUndo && (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
              <span className="font-semibold">Thời hạn hoàn tác còn lại:</span>{" "}
              <span className="font-mono font-bold">{formatMmSs(undoSeconds)}</span> (trước{" "}
              {new Date(action.undo_until!).toLocaleTimeString("vi-VN")})
            </div>
          )}

          <div>
            <span className="font-medium text-gray-700 dark:text-gray-200">Tham số thực hiện:</span>
            <pre className="mt-1 max-h-40 overflow-auto rounded bg-gray-50 p-2 font-mono text-xs dark:bg-gray-900">
              {JSON.stringify(action.args_preview, null, 2)}
            </pre>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3 border-t pt-4 dark:border-gray-700">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-700"
          >
            Đóng
          </button>

          {isPending && (
            <>
              <button
                type="button"
                onClick={() => onReject(action.id)}
                disabled={isSubmitting}
                className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-950"
              >
                Từ chối
              </button>
              <button
                type="button"
                onClick={() => onConfirm(action.id, "confirm_nonce" in action ? (action as AiActionDetail).confirm_nonce : undefined)}
                disabled={countdown > 0 || isSubmitting}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300 dark:disabled:bg-blue-900"
              >
                {countdown > 0
                  ? `Chờ xem xét (${countdown}s)`
                  : isSubmitting
                  ? "Đang thực thi..."
                  : "Đồng ý thực thi"}
              </button>
            </>
          )}

          {isScheduled && onUndo && (
            <button
              type="button"
              onClick={handleCancelScheduled}
              disabled={isSubmitting}
              className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
            >
              {isSubmitting ? "Đang huỷ..." : "Huỷ lịch"}
            </button>
          )}

          {canUndo && onUndo && (
            <button
              type="button"
              onClick={handleUndoDone}
              disabled={isSubmitting}
              className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50"
            >
              {isSubmitting ? "Đang hoàn tác..." : "Hoàn tác"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

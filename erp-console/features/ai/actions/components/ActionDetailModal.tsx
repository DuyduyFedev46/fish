"use client";

import React, { useEffect, useState } from "react";
import type { AiActionRow } from "../../types";

interface ActionDetailModalProps {
  action: AiActionRow | null;
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (actionId: string, nonce?: string) => Promise<void>;
  onReject: (actionId: string) => Promise<void>;
  isSubmitting?: boolean;
}

export function ActionDetailModal({
  action,
  isOpen,
  onClose,
  onConfirm,
  onReject,
  isSubmitting = false,
}: ActionDetailModalProps) {
  const [countdown, setCountdown] = useState<number>(3);

  useEffect(() => {
    if (isOpen && action) {
      setCountdown(3);
      const timer = setInterval(() => {
        setCountdown((prev) => (prev > 0 ? prev - 1 : 0));
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [isOpen, action?.id]);

  if (!isOpen || !action) {
    return null;
  }

  const isPending = action.status === "PENDING";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl dark:bg-gray-800">
        <div className="flex items-center justify-between border-b pb-3 dark:border-gray-700">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Chi tiết đề xuất AI
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
              <span className="rounded bg-gray-100 px-2 py-0.5 font-medium text-gray-800 dark:bg-gray-700 dark:text-gray-200">
                {action.status}
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
                onClick={() => onConfirm(action.id, action.confirm_nonce)}
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
        </div>
      </div>
    </div>
  );
}

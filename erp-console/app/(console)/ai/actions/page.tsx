"use client";

import { useEffect, useState, useCallback } from "react";
import { ViewGuard } from "@/features/auth/components/ViewGuard";
import { useAuth } from "@/features/auth/components/AuthProvider";
import { fetchAiActions, confirmAiAction, rejectAiAction, undoAiAction } from "@/features/ai/actions/api";
import { ActionDetailModal } from "@/features/ai/actions/components/ActionDetailModal";
import type { AiActionRow } from "@/features/ai/types";
import { Icon } from "@/shared/ui/Icon";
import { Loading } from "@/shared/ui/StateBox";

export default function AiActionsPage() {
  return (
    <ViewGuard view="ai-actions">
      <AiActionsContent />
    </ViewGuard>
  );
}

function AiActionsContent() {
  const { me } = useAuth();
  const [activeTab, setActiveTab] = useState<"pending" | "scheduled" | "history">("pending");
  const [scope, setScope] = useState<"mine" | "all">("mine");
  const [actions, setActions] = useState<AiActionRow[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAction, setSelectedAction] = useState<AiActionRow | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const canManageAll = me?.permissions?.includes("ai.manage_ai_policy") ?? false;

  const loadActions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let statusFilter = "PENDING";
      if (activeTab === "scheduled") {
        statusFilter = "SCHEDULED";
      } else if (activeTab === "history") {
        statusFilter = "CONFIRMED,REJECTED,EXPIRED,DONE,CANCELLED,UNDONE";
      }

      const res = await fetchAiActions({
        status: statusFilter,
        scope: canManageAll ? scope : "mine",
      });
      setActions(res.results || []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Không thể tải danh sách việc AI.");
    } finally {
      setLoading(false);
    }
  }, [activeTab, scope, canManageAll]);

  useEffect(() => {
    loadActions();
  }, [loadActions]);

  const handleConfirm = async (actionId: string, nonce?: string) => {
    setIsSubmitting(true);
    try {
      await confirmAiAction(actionId, nonce);
      setFeedback({ type: "success", text: "Đã duyệt và thực thi thành công đề xuất AI!" });
      setSelectedAction(null);
      await loadActions();
    } catch (err: unknown) {
      setFeedback({ type: "error", text: err instanceof Error ? err.message : "Thực thi thất bại." });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async (actionId: string) => {
    setIsSubmitting(true);
    try {
      await rejectAiAction(actionId, "USER_REJECTED");
      setFeedback({ type: "success", text: "Đã từ chối đề xuất AI." });
      setSelectedAction(null);
      await loadActions();
    } catch (err: unknown) {
      setFeedback({ type: "error", text: err instanceof Error ? err.message : "Từ chối thất bại." });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUndo = async (actionId: string) => {
    setIsSubmitting(true);
    try {
      await undoAiAction(actionId);
      setFeedback({
        type: "success",
        text: "Đã hoàn tác thao tác thành công. Chứng từ liên quan đã chuyển trạng thái Đã huỷ.",
      });
      if (selectedAction?.id === actionId) {
        setSelectedAction((prev) =>
          prev
            ? {
                ...prev,
                status: prev.status === "SCHEDULED" ? "CANCELLED" : "UNDONE",
              }
            : null
        );
      }
      await loadActions();
    } catch (err: unknown) {
      setFeedback({ type: "error", text: err instanceof Error ? err.message : "Hoàn tác thất bại." });
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatCountdown = (isoString?: string | null) => {
    if (!isoString) return "";
    const diff = Math.max(0, Math.floor((new Date(isoString).getTime() - Date.now()) / 1000));
    const m = Math.floor(diff / 60).toString().padStart(2, "0");
    const s = (diff % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  return (
    <div className="space-y-6 p-4 md:p-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
            Việc AI
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Duyệt, huỷ lịch và kiểm tra các hành động do AI đề xuất hoặc tự động thực hiện.
          </p>
        </div>

        {canManageAll && (
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-500">Phạm vi:</span>
            <div className="inline-flex rounded-lg border p-1 dark:border-gray-700">
              <button
                type="button"
                onClick={() => setScope("mine")}
                className={`rounded px-3 py-1 text-xs font-medium ${
                  scope === "mine"
                    ? "bg-blue-600 text-white"
                    : "text-gray-600 hover:text-gray-900 dark:text-gray-300"
                }`}
              >
                Của tôi
              </button>
              <button
                type="button"
                onClick={() => setScope("all")}
                className={`rounded px-3 py-1 text-xs font-medium ${
                  scope === "all"
                    ? "bg-blue-600 text-white"
                    : "text-gray-600 hover:text-gray-900 dark:text-gray-300"
                }`}
              >
                Tất cả (Chủ)
              </button>
            </div>
          </div>
        )}
      </div>

      {feedback && (
        <div
          className={`flex items-center justify-between rounded-lg p-3 text-sm ${
            feedback.type === "success"
              ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200"
              : "bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-200"
          }`}
        >
          <span>{feedback.text}</span>
          <button
            type="button"
            onClick={() => setFeedback(null)}
            className="text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-700">
        <button
          type="button"
          onClick={() => setActiveTab("pending")}
          className={`border-b-2 px-4 py-2 text-sm font-medium ${
            activeTab === "pending"
              ? "border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400"
              : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-400"
          }`}
        >
          Chờ duyệt ({actions.filter((a) => a.status === "PENDING").length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("scheduled")}
          className={`border-b-2 px-4 py-2 text-sm font-medium ${
            activeTab === "scheduled"
              ? "border-purple-600 text-purple-600 dark:border-purple-400 dark:text-purple-400"
              : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-400"
          }`}
        >
          Đã lên lịch ({actions.filter((a) => a.status === "SCHEDULED").length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("history")}
          className={`border-b-2 px-4 py-2 text-sm font-medium ${
            activeTab === "history"
              ? "border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400"
              : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 dark:text-gray-400"
          }`}
        >
          Đã xử lý
        </button>
      </div>

      {/* List */}
      {loading ? (
        <div className="py-12">
          <Loading label="Đang tải danh sách việc AI..." />
        </div>
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-center text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          {error}
        </div>
      ) : actions.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 py-12 text-center text-gray-500 dark:border-gray-700">
          <Icon name="smart_toy" className="mx-auto mb-2 text-3xl opacity-40" />
          <p>Không có việc AI nào trong danh sách.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900">
          <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
            <thead className="bg-gray-50 text-xs font-semibold uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-400">
              <tr>
                <th className="px-4 py-3">Hành động</th>
                <th className="px-4 py-3">Tác nhân</th>
                <th className="px-4 py-3">Chứng từ đích</th>
                <th className="px-4 py-3">Trạng thái</th>
                <th className="px-4 py-3">Thời gian tạo / Lịch</th>
                <th className="px-4 py-3 text-right">Chi tiết</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {actions.map((act) => (
                <tr
                  key={act.id}
                  onClick={() => setSelectedAction(act)}
                  className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50"
                >
                  <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">
                    {act.title}
                  </td>
                  <td className="px-4 py-3">
                    <span className="rounded bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                      {act.owner_display}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">
                    {act.target?.type ? `${act.target.type} #${act.target.code}` : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${
                        act.status === "PENDING"
                          ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
                          : act.status === "SCHEDULED"
                          ? "bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300"
                          : act.status === "CONFIRMED" || act.status === "DONE"
                          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                          : act.status === "REJECTED" || act.status === "CANCELLED"
                          ? "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                          : "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300"
                      }`}
                    >
                      {act.status === "SCHEDULED" ? "ĐÃ LÊN LỊCH" : act.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {act.status === "SCHEDULED" && act.execute_after ? (
                      <span className="font-mono text-purple-700 dark:text-purple-300">
                        Chạy sau: {formatCountdown(act.execute_after)}
                      </span>
                    ) : (
                      new Date(act.created_at).toLocaleString("vi-VN")
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      className="rounded border px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-100 dark:border-gray-700 dark:text-gray-200"
                    >
                      Xem
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal */}
      <ActionDetailModal
        action={selectedAction}
        isOpen={Boolean(selectedAction)}
        onClose={() => setSelectedAction(null)}
        onConfirm={handleConfirm}
        onReject={handleReject}
        onUndo={handleUndo}
        isSubmitting={isSubmitting}
      />
    </div>
  );
}

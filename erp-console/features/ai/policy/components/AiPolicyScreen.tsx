"use client";

import React, { useEffect, useState } from "react";
import { getAiPolicy, getUserAiConfig, killUserAi, updateAiPolicy } from "../api";
import { AiPolicy, AiPolicyUserSummary, MyConfig } from "../../types";

export default function AiPolicyScreen() {
  const [policy, setPolicy] = useState<AiPolicy | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form state
  const [globalMode, setGlobalMode] = useState<"on" | "c_only" | "off">("on");
  const [ack, setAck] = useState(false);

  // User config viewer modal
  const [viewingUser, setViewingUser] = useState<AiPolicyUserSummary | null>(null);
  const [viewingConfig, setViewingConfig] = useState<MyConfig | null>(null);
  const [modalLoading, setModalLoading] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getAiPolicy();
      setPolicy(data);
      setGlobalMode(data.global_mode);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Không thể tải chính sách AI.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSavePolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!policy) return;
    if (!ack) {
      setError("Bạn phải xác nhận chịu trách nhiệm cho chính sách AI (BR-AI-14).");
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      const updated = await updateAiPolicy({
        base_version: policy.version,
        global_mode: globalMode,
        acknowledge_responsibility: true,
      });
      setPolicy(updated);
      setSuccess(`Đã cập nhật chính sách AI phiên bản v${updated.version}.`);
      setAck(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Lỗi khi lưu chính sách AI.");
    } finally {
      setSaving(false);
    }
  };

  const handleToggleUserKill = async (user: AiPolicyUserSummary) => {
    const targetKilled = !user.killed;
    if (
      !confirm(
        targetKilled
          ? `Bạn có chắc muốn tắt AI của nhân viên "${user.display_name}"?`
          : `Bật lại AI cho nhân viên "${user.display_name}"?`
      )
    ) {
      return;
    }

    try {
      setActionLoading(user.user_id);
      setError(null);
      await killUserAi(user.user_id, targetKilled);
      await loadData();
      setSuccess(
        targetKilled
          ? `Đã tắt AI của ${user.display_name}.`
          : `Đã mở lại AI cho ${user.display_name}.`
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Lỗi khi cập nhật trạng thái nhân viên.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleViewUserConfig = async (user: AiPolicyUserSummary) => {
    try {
      setViewingUser(user);
      setModalLoading(true);
      const cfg = await getUserAiConfig(user.user_id);
      setViewingConfig(cfg);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Không thể xem cấu hình.");
      setViewingUser(null);
    } finally {
      setModalLoading(false);
    }
  };

  if (loading) {
    return <div className="p-6 text-sm text-gray-500">Đang tải chính sách AI của Chủ...</div>;
  }

  if (!policy) {
    return (
      <div className="p-6">
        <div className="p-4 bg-red-50 text-red-700 rounded-md border border-red-200">
          {error || "Không có quyền truy cập hoặc không tìm thấy dữ liệu."}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="border-b pb-4">
        <h1 className="text-2xl font-bold text-gray-900">Chính sách AI (Chủ vựa)</h1>
        <p className="text-sm text-gray-500 mt-1">
          Phiên bản chính sách: <span className="font-semibold text-gray-700">v{policy.version}</span>
          <span className="ml-3 px-2 py-0.5 text-xs bg-gray-100 rounded text-gray-600 uppercase font-mono">
            Môi trường: {policy.env}
          </span>
        </p>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
        </div>
      )}

      {success && (
        <div className="p-3 bg-green-50 border border-green-200 rounded text-green-700 text-sm">
          {success}
        </div>
      )}

      {/* Chế độ toàn cục */}
      <form onSubmit={handleSavePolicy} className="bg-white border rounded-lg p-5 shadow-sm space-y-4">
        <h2 className="text-base font-semibold text-gray-900">Chế độ hoạt động toàn cục</h2>
        <p className="text-xs text-gray-500">
          Thiết lập giới hạn mức tự chủ áp dụng cho toàn bộ nhân viên trong hệ thống.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <label
            className={`border rounded-lg p-3 cursor-pointer flex flex-col justify-between transition ${
              globalMode === "on"
                ? "border-blue-500 bg-blue-50 ring-1 ring-blue-500"
                : "border-gray-200 hover:bg-gray-50"
            }`}
          >
            <div className="flex items-center gap-2">
              <input
                type="radio"
                name="globalMode"
                value="on"
                checked={globalMode === "on"}
                onChange={() => setGlobalMode("on")}
                className="text-blue-600 focus:ring-blue-500"
              />
              <span className="font-semibold text-xs text-gray-900">Bình thường (ON)</span>
            </div>
            <p className="text-[11px] text-gray-500 mt-2">
              Cho phép AI chạy theo cấu hình phân quyền của từng nhân viên.
            </p>
          </label>

          <label
            className={`border rounded-lg p-3 cursor-pointer flex flex-col justify-between transition ${
              globalMode === "c_only"
                ? "border-amber-500 bg-amber-50 ring-1 ring-amber-500"
                : "border-gray-200 hover:bg-gray-50"
            }`}
          >
            <div className="flex items-center gap-2">
              <input
                type="radio"
                name="globalMode"
                value="c_only"
                checked={globalMode === "c_only"}
                onChange={() => setGlobalMode("c_only")}
                className="text-amber-600 focus:ring-amber-500"
              />
              <span className="font-semibold text-xs text-amber-900">Chỉ mức C (C_ONLY)</span>
            </div>
            <p className="text-[11px] text-gray-500 mt-2">
              Bắt buộc mọi thao tác ghi phải soạn nháp để duyệt, không cho phép tự thực thi.
            </p>
          </label>

          <label
            className={`border rounded-lg p-3 cursor-pointer flex flex-col justify-between transition ${
              globalMode === "off"
                ? "border-red-500 bg-red-50 ring-1 ring-red-500"
                : "border-gray-200 hover:bg-gray-50"
            }`}
          >
            <div className="flex items-center gap-2">
              <input
                type="radio"
                name="globalMode"
                value="off"
                checked={globalMode === "off"}
                onChange={() => setGlobalMode("off")}
                className="text-red-600 focus:ring-red-500"
              />
              <span className="font-semibold text-xs text-red-900">Tắt khẩn cấp (OFF)</span>
            </div>
            <p className="text-[11px] text-gray-500 mt-2">
              Ngừng toàn bộ lệnh AI trên mọi thiết bị ngay lập tức.
            </p>
          </label>
        </div>

        <div className="pt-2 border-t flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <label className="flex items-start gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={ack}
              onChange={(e) => setAck(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-xs text-gray-700">
              Tôi chịu trách nhiệm cho quyết định thay đổi chính sách toàn cục này (BR-AI-14).
            </span>
          </label>

          <button
            type="submit"
            disabled={saving || !ack}
            className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 rounded shadow-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {saving ? "Đang lưu..." : "Cập nhật chính sách"}
          </button>
        </div>
      </form>

      {/* Danh sách nhân viên */}
      <div className="bg-white border rounded-lg overflow-hidden shadow-sm">
        <div className="bg-gray-50 px-4 py-3 border-b flex justify-between items-center">
          <h2 className="text-base font-semibold text-gray-800">Cấu hình AI của nhân viên</h2>
          <span className="text-xs text-gray-500">{policy.users.length} nhân viên</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-gray-50 border-b text-gray-600 font-medium">
              <tr>
                <th className="px-4 py-2.5">Nhân viên</th>
                <th className="px-4 py-2.5">Vai trò</th>
                <th className="px-4 py-2.5">Phiên bản</th>
                <th className="px-4 py-2.5">Thống kê lệnh</th>
                <th className="px-4 py-2.5">Trạng thái</th>
                <th className="px-4 py-2.5 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {policy.users.map((u) => (
                <tr key={u.user_id} className="hover:bg-gray-50 transition">
                  <td className="px-4 py-3 font-medium text-gray-900">{u.display_name}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {u.groups.length > 0 ? u.groups.join(", ") : "—"}
                  </td>
                  <td className="px-4 py-3 font-mono text-gray-700">v{u.config_version}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex gap-1.5 font-mono text-[11px]">
                      <span className="text-blue-600 font-semibold" title="Mức A (đọc)">
                        A:{u.counts.A}
                      </span>
                      <span className="text-purple-600 font-semibold" title="Mức C (nháp)">
                        C:{u.counts.C}
                      </span>
                      <span className="text-gray-400" title="Đã tắt">
                        OFF:{u.counts.OFF}
                      </span>
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {u.killed ? (
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-red-100 text-red-800">
                        ĐÃ TẮT
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-green-100 text-green-800">
                        HOẠT ĐỘNG
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right space-x-2">
                    <button
                      type="button"
                      onClick={() => handleViewUserConfig(u)}
                      className="text-xs text-blue-600 hover:underline font-medium"
                    >
                      Xem cấu hình
                    </button>
                    <button
                      type="button"
                      onClick={() => handleToggleUserKill(u)}
                      disabled={actionLoading === u.user_id}
                      className={`text-xs font-medium ${
                        u.killed
                          ? "text-green-600 hover:text-green-800"
                          : "text-red-600 hover:text-red-800"
                      }`}
                    >
                      {actionLoading === u.user_id
                        ? "..."
                        : u.killed
                        ? "Mở lại"
                        : "Tắt khẩn"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal chỉ đọc cấu hình nhân viên (DW-13-AC4) */}
      {viewingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden">
            <div className="px-5 py-3 border-b flex justify-between items-center bg-gray-50">
              <div>
                <h3 className="font-semibold text-sm text-gray-900">
                  Cấu hình AI của: {viewingUser.display_name}
                </h3>
                <p className="text-xs text-gray-500 font-mono">
                  Phiên bản v{viewingConfig?.version ?? viewingUser.config_version} (chỉ đọc)
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setViewingUser(null);
                  setViewingConfig(null);
                }}
                className="text-gray-400 hover:text-gray-600 text-lg"
              >
                ✕
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-4 text-xs">
              {modalLoading ? (
                <div className="text-gray-500">Đang tải...</div>
              ) : viewingConfig ? (
                viewingConfig.groups.map((grp) => (
                  <div key={grp.group} className="border rounded p-3 space-y-2">
                    <div className="font-semibold text-gray-800">{grp.label}</div>
                    {grp.commands.length === 0 ? (
                      <div className="text-gray-400 italic">Không có lệnh.</div>
                    ) : (
                      <ul className="divide-y divide-gray-100">
                        {grp.commands.map((cmd) => (
                          <li key={cmd.id} className="py-1.5 flex justify-between items-center">
                            <div>
                              <span className="font-medium text-gray-800">{cmd.title}</span>
                              <span className="ml-2 font-mono text-[10px] text-gray-400">
                                {cmd.id}
                              </span>
                            </div>
                            <span className="font-mono font-semibold px-2 py-0.5 bg-gray-100 rounded">
                              {cmd.level}
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))
              ) : (
                <div className="text-gray-500">Không có dữ liệu.</div>
              )}
            </div>

            <div className="px-5 py-3 bg-gray-50 border-t flex justify-end">
              <button
                type="button"
                onClick={() => {
                  setViewingUser(null);
                  setViewingConfig(null);
                }}
                className="px-4 py-1.5 text-xs font-semibold bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

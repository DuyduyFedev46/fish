"use client";

import React, { useEffect, useState } from "react";
import { getAiPolicy, getUserAiConfig, killUserAi, updateAiPolicy } from "../api";
import { AiPolicy, AiPolicyUserSummary, MyConfig } from "../../types";
import { RECEIVE_BATCHES_COMMAND_ID } from "../../commandGroups";
import { buildCapsForSave } from "../caps";
import { groupLabel } from "@/shared/lib/groups";

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
  const [redZoneState, setRedZoneState] = useState<Record<string, boolean>>({});
  const [capsState, setCapsState] = useState<{
    receive_kg: string;
    receive_vnd: string;
    receive_daily: string;
  }>({
    receive_kg: "",
    receive_vnd: "",
    receive_daily: "",
  });

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

      const rzInit: Record<string, boolean> = {};
      (data.red_zone || []).forEach((rz) => {
        rzInit[rz.perm] = rz.open;
      });
      setRedZoneState(rzInit);

      const receiveBatchesCap = data.caps?.[RECEIVE_BATCHES_COMMAND_ID] || {};
      setCapsState({
        receive_kg: receiveBatchesCap.kg != null ? String(receiveBatchesCap.kg) : "",
        receive_vnd: receiveBatchesCap.vnd != null ? String(receiveBatchesCap.vnd) : "",
        receive_daily: receiveBatchesCap.daily != null ? String(receiveBatchesCap.daily) : "",
      });
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

    const kgNum = capsState.receive_kg.trim() ? Number(capsState.receive_kg) : null;
    const vndNum = capsState.receive_vnd.trim() ? Number(capsState.receive_vnd) : null;
    const dailyNum = capsState.receive_daily.trim() ? Number(capsState.receive_daily) : null;

    if (
      (kgNum !== null && (isNaN(kgNum) || kgNum < 0)) ||
      (vndNum !== null && (isNaN(vndNum) || vndNum < 0)) ||
      (dailyNum !== null && (isNaN(dailyNum) || dailyNum < 0))
    ) {
      setError("Các giá trị trần lệnh (kg, VNĐ, số lần/ngày) phải là số không âm (DW-20-AC5).");
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      // Ghi bằng id MỚI (Lô 4b), bỏ khoá cũ của cùng lệnh nếu BE còn trả (xem ../caps.ts).
      const newCaps = buildCapsForSave(policy.caps, {
        kg: kgNum !== null ? String(kgNum) : null,
        vnd: vndNum !== null ? String(vndNum) : null,
        daily: dailyNum !== null ? dailyNum : null,
      });

      const updated = await updateAiPolicy({
        base_version: policy.version,
        global_mode: globalMode,
        red_zone: redZoneState,
        caps: newCaps,
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

        {/* DW-20: Trần lệnh ghi của Chủ (Caps) */}
        <div className="pt-4 border-t space-y-3">
          <div>
            <h3 className="text-sm font-semibold text-gray-900">
              Trần lệnh ghi của Chủ (Caps)
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Đặt giới hạn an toàn tối đa cho các lệnh ghi dữ liệu của AI. Khi nhân viên gọi lệnh vượt trần, hệ thống tự động hạ về mức C (soạn nháp để duyệt) thay vì tự động thực thi.
            </p>
          </div>

          <div className="border rounded-lg p-4 bg-gray-50/50 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="font-semibold text-xs text-gray-800">
                  Nhập lô mua tại cảng
                </span>
                <span className="ml-2 font-mono text-[10px] text-gray-500">
                  {RECEIVE_BATCHES_COMMAND_ID}
                </span>
              </div>
              <span className="text-[11px] px-2 py-0.5 bg-blue-50 text-blue-700 rounded border border-blue-200 font-medium">
                Mức tối đa: B
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-[11px] font-medium text-gray-700 mb-1">
                  Trần khối lượng mỗi lần (kg)
                </label>
                <input
                  type="number"
                  min="0"
                  step="any"
                  placeholder="Không giới hạn"
                  value={capsState.receive_kg}
                  onChange={(e) =>
                    setCapsState((prev) => ({ ...prev, receive_kg: e.target.value }))
                  }
                  className="w-full text-xs px-2.5 py-1.5 border rounded border-gray-300 focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white"
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-gray-700 mb-1">
                  Trần giá trị mỗi lần (VNĐ)
                </label>
                <input
                  type="number"
                  min="0"
                  step="1000"
                  placeholder="Không giới hạn"
                  value={capsState.receive_vnd}
                  onChange={(e) =>
                    setCapsState((prev) => ({ ...prev, receive_vnd: e.target.value }))
                  }
                  className="w-full text-xs px-2.5 py-1.5 border rounded border-gray-300 focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white"
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-gray-700 mb-1">
                  Hạn mức số lần trong ngày
                </label>
                <input
                  type="number"
                  min="0"
                  step="1"
                  placeholder="Không giới hạn"
                  value={capsState.receive_daily}
                  onChange={(e) =>
                    setCapsState((prev) => ({ ...prev, receive_daily: e.target.value }))
                  }
                  className="w-full text-xs px-2.5 py-1.5 border rounded border-gray-300 focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white"
                />
              </div>
            </div>
          </div>
        </div>

        {/* DW-24: Công tắc vùng đỏ (Red Zone) của Chủ */}
        <div className="pt-4 border-t space-y-3">
          <div>
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-900">
                Công tắc vùng đỏ (Red Zone) của Chủ
              </h3>
              <span className="text-[11px] font-mono text-gray-500">
                Chỉ mở được ở Staging
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-0.5">
              Các nghiệp vụ quan trọng liên quan đến chốt sổ và giao dịch tiền. Mặc định luôn ở mức C (soạn nháp). Khi Chủ mở công tắc, lệnh được phép cấu hình mức B theo cơ chế trì hoãn ghi.
            </p>
          </div>

          <div className="space-y-3">
            {policy.red_zone.map((rz) => {
              const isOpen = redZoneState[rz.perm] ?? rz.open;
              return (
                <div
                  key={rz.perm}
                  className={`border rounded-lg p-4 transition ${
                    isOpen ? "bg-amber-50/40 border-amber-300" : "bg-gray-50/50 border-gray-200"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-xs text-gray-900">{rz.label}</span>
                        <span className="font-mono text-[10px] text-gray-500">{rz.perm}</span>
                        {isOpen ? (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-green-100 text-green-800">
                            ĐANG MỞ (B)
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-gray-200 text-gray-700">
                            ĐANG ĐÓNG (C)
                          </span>
                        )}
                        {rz.delay_minutes > 0 && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700 border border-blue-200">
                            Trì hoãn {rz.delay_minutes} phút
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-gray-600">
                        <span className="font-medium text-gray-700">Lệnh phụ trách:</span>{" "}
                        <code className="bg-gray-100 px-1 py-0.5 rounded text-gray-800 font-mono text-[10px]">
                          {rz.commands.join(", ")}
                        </code>
                      </div>
                    </div>

                    <label className="flex items-center gap-2 cursor-pointer select-none shrink-0">
                      <input
                        type="checkbox"
                        checked={isOpen}
                        onChange={(e) =>
                          setRedZoneState((prev) => ({
                            ...prev,
                            [rz.perm]: e.target.checked,
                          }))
                        }
                        className="h-4 w-4 rounded border-gray-300 text-amber-600 focus:ring-amber-500"
                      />
                      <span className="text-xs font-medium text-gray-800">
                        {isOpen ? "Mở công tắc" : "Đóng công tắc"}
                      </span>
                    </label>
                  </div>

                  {/* Chi tiết can_do, cannot_do, legal_note */}
                  <div className="mt-3 pt-3 border-t border-gray-200/80 grid grid-cols-1 md:grid-cols-3 gap-2.5 text-[11px]">
                    <div className="bg-white/80 p-2.5 rounded border border-gray-100">
                      <span className="font-semibold text-emerald-700 block mb-0.5">
                        ✓ AI được phép:
                      </span>
                      <span className="text-gray-600 leading-relaxed">{rz.can_do}</span>
                    </div>
                    <div className="bg-white/80 p-2.5 rounded border border-gray-100">
                      <span className="font-semibold text-rose-700 block mb-0.5">
                        ✕ AI KHÔNG được:
                      </span>
                      <span className="text-gray-600 leading-relaxed">{rz.cannot_do}</span>
                    </div>
                    <div className="bg-white/80 p-2.5 rounded border border-gray-100">
                      <span className="font-semibold text-amber-800 block mb-0.5">
                        ⚖ Pháp lý & Trách nhiệm:
                      </span>
                      <span className="text-gray-600 leading-relaxed">{rz.legal_note}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
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
                    {u.groups.length > 0 ? u.groups.map(groupLabel).join(", ") : "—"}
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

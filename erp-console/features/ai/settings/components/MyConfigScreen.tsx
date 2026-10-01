"use client";

import React, { useEffect, useState } from "react";
import { getMyConfig, killMyConfig, updateMyConfig } from "../api";
import type { MyConfig } from "../../types";
import { buildMyConfigPayload, readLimitInputs, type LimitInputs } from "../payload";
import { commandChoices, describeSaveError, displayLevel, limitFieldsOf } from "../levels";
import { dateTimeFull } from "@/shared/lib/format";

export default function MyConfigScreen() {
  const [config, setConfig] = useState<MyConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [killing, setKilling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form state
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [limits, setLimits] = useState<LimitInputs>({});
  const [ack, setAck] = useState(false);

  // Dựng lại ô nhập từ cấu hình BE vừa trả (lúc tải và sau khi lưu), để ô khớp với phiên bản đang có.
  const applyConfig = (data: MyConfig) => {
    setConfig(data);
    const initialOverrides: Record<string, string> = {};
    const initialLimits: LimitInputs = {};
    data.groups.forEach((grp) => {
      grp.commands.forEach((cmd) => {
        if (cmd.source === "override") {
          initialOverrides[cmd.id] = cmd.level;
        }
        if (cmd.limits) {
          initialLimits[cmd.id] = readLimitInputs(cmd.limits);
        }
      });
    });
    setOverrides(initialOverrides);
    setLimits(initialLimits);
  };

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      applyConfig(await getMyConfig());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Không thể tải cấu hình AI.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleLevelChange = (cmdId: string, level: string) => {
    setOverrides((prev) => ({
      ...prev,
      [cmdId]: level,
    }));
  };

  const handleLimitChange = (cmdId: string, field: "kg" | "vnd", val: string) => {
    setLimits((prev) => ({
      ...prev,
      [cmdId]: {
        ...(prev[cmdId] || {}),
        [field]: val,
      },
    }));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!config) return;
    if (!ack) {
      setError("Bạn phải xác nhận chịu trách nhiệm cho cấu hình AI (BR-AI-14).");
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      // BE thay thế toàn bộ cấu hình mỗi lần lưu: thân phải mang đủ nhóm, mức từng lệnh và ngưỡng (xem ../payload.ts).
      const payload = buildMyConfigPayload(config, { overrides, limits });
      try {
        const updated = await updateMyConfig(payload);
        applyConfig(updated);
        setSuccess(`Đã lưu cấu hình AI phiên bản v${updated.version}.`);
        setAck(false);
      } catch (err: unknown) {
        // Nêu rõ lệnh nào gây lỗi (BR-AI-19, BR-AI-27) thay vì chỉ câu chung của BE.
        setError(describeSaveError(err, config, payload));
      }
    } finally {
      setSaving(false);
    }
  };

  const handleToggleKill = async () => {
    if (!config) return;
    const targetKilled = !config.killed;
    if (
      !confirm(
        targetKilled
          ? "Bạn có chắc muốn tắt AI của mình? Mọi lệnh ghi sẽ rơi về mức nháp C."
          : "Bật lại AI của bạn?"
      )
    ) {
      return;
    }

    try {
      setKilling(true);
      setError(null);
      await killMyConfig(targetKilled);
      await loadData();
      setSuccess(targetKilled ? "Đã tắt AI của bạn." : "Đã bật lại AI.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Lỗi khi cập nhật trạng thái AI.");
    } finally {
      setKilling(false);
    }
  };

  if (loading) {
    return <div className="p-6 text-sm text-gray-500">Đang tải cấu hình AI...</div>;
  }

  if (!config) {
    return (
      <div className="p-6">
        <div className="p-4 bg-red-50 text-red-700 rounded-md border border-red-200">
          {error || "Không tìm thấy cấu hình."}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI của tôi</h1>
          <p className="text-sm text-gray-500 mt-1">
            Phiên bản: <span className="font-semibold text-gray-700">v{config.version}</span>
            {config.updated_at && (
              <span className="ml-2 text-xs">
                (cập nhật: {dateTimeFull(config.updated_at)})
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleToggleKill}
            disabled={killing}
            className={`px-3 py-1.5 text-xs font-semibold rounded shadow-sm border transition ${
              config.killed
                ? "bg-green-600 text-white border-green-700 hover:bg-green-700"
                : "bg-red-50 text-red-700 border-red-300 hover:bg-red-100"
            }`}
          >
            {killing
              ? "Đang xử lý..."
              : config.killed
              ? "Bật lại AI của tôi"
              : "Tắt khẩn AI của tôi"}
          </button>
        </div>
      </div>

      {/* Băng thông báo nếu AI tắt toàn cục */}
      {!config.ai_enabled && (
        <div className="p-3 bg-amber-50 border border-amber-300 rounded text-amber-800 text-xs font-medium">
          Hệ thống AI hiện đang tắt toàn cục (AI_ENABLED=false). Cấu hình của bạn vẫn được lưu trữ.
        </div>
      )}

      {/* Thông báo nếu AI bị killed */}
      {config.killed && (
        <div className="p-3 bg-red-50 border border-red-300 rounded text-red-800 text-xs font-medium">
          AI của bạn đang ở trạng thái TẮT. Mọi lệnh ghi sẽ được chuyển thành nháp (mức C) để bạn duyệt thủ công.
        </div>
      )}

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

      {/* Danh sách các nhóm lệnh */}
      <form onSubmit={handleSave} className="space-y-6">
        {config.groups.map((grp) => (
          <div key={grp.group} className="bg-white border rounded-lg overflow-hidden shadow-sm">
            <div className="bg-gray-50 px-4 py-3 border-b flex justify-between items-center">
              <h2 className="text-base font-semibold text-gray-800">{grp.label}</h2>
              <span className="text-xs text-gray-500">
                {grp.commands.length} lệnh trong quyền của bạn
              </span>
            </div>
            {grp.commands.length === 0 ? (
              <div className="p-4 text-xs text-gray-400 italic">
                Bạn không có quyền thao tác các lệnh thuộc nhóm này.
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {grp.commands.map((cmd) => {
                  // Mức hiệu lực hiển thị: B không giữ được (môi trường chỉ cho C, vùng đỏ đóng...) thì hiện C, không rơi về OFF.
                  const currentLevel = displayLevel(config, cmd, overrides[cmd.id] || cmd.level);
                  const allowedChoices = commandChoices(config, cmd, currentLevel);
                  const limitFields = limitFieldsOf(cmd);
                  return (
                    <div
                      key={cmd.id}
                      className="p-4 flex flex-col gap-3 hover:bg-gray-50 transition"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-sm text-gray-900">{cmd.title}</span>
                            <span
                              className={`px-1.5 py-0.5 text-[10px] font-mono rounded uppercase ${
                                cmd.kind === "read"
                                  ? "bg-blue-50 text-blue-700 border border-blue-200"
                                  : "bg-purple-50 text-purple-700 border border-purple-200"
                              }`}
                            >
                              {cmd.kind === "read" ? "Đọc" : "Ghi"}
                            </span>
                            {cmd.red_zone && (
                              <span className="px-1.5 py-0.5 text-[10px] font-medium bg-red-100 text-red-800 rounded">
                                Vùng đỏ
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-gray-500 font-mono">{cmd.id}</p>
                          {cmd.locked_reason && (
                            <p className="text-xs text-amber-700">
                              Lưu ý: {cmd.locked_reason.text} ({cmd.locked_reason.code})
                            </p>
                          )}
                        </div>

                        <div className="flex items-center gap-2">
                          <label className="text-xs text-gray-600 font-medium">Mức tự chủ:</label>
                          <select
                            value={currentLevel}
                            onChange={(e) => handleLevelChange(cmd.id, e.target.value)}
                            className="text-xs border rounded px-2.5 py-1.5 bg-white font-medium focus:ring-1 focus:ring-blue-500"
                          >
                            {allowedChoices.map((choice) => (
                              <option key={choice} value={choice}>
                                {choice === "OFF"
                                  ? "Tắt (OFF)"
                                  : choice === "A"
                                  ? "Mức A (Tự đọc)"
                                  : choice === "C"
                                  ? "Mức C (Soạn nháp)"
                                  : choice === "B"
                                  ? "Mức B (Tự ghi + hoàn tác)"
                                  : choice}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>

                      {/* Hiển thị cấu hình ngưỡng nếu lệnh hỗ trợ limits */}
                      {limitFields.length > 0 && currentLevel === "B" && (
                        <div className="mt-2 rounded-md border border-gray-200 bg-gray-50 p-3 text-xs">
                          <span className="font-semibold text-gray-700">Ngưỡng tự ghi an toàn:</span>
                          <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {limitFields.includes("kg") && (
                              <div>
                                <label className="block text-gray-600 mb-1" htmlFor={`limit-kg-${cmd.id}`}>
                                  Giới hạn kg mỗi lần (không vượt trần của Chủ; để trống nếu không đặt)
                                </label>
                                <input
                                  id={`limit-kg-${cmd.id}`}
                                  type="number"
                                  min="0"
                                  value={limits[cmd.id]?.kg || ""}
                                  onChange={(e) => handleLimitChange(cmd.id, "kg", e.target.value)}
                                  placeholder="Nhập số kg"
                                  className="w-full rounded border px-2.5 py-1 bg-white"
                                />
                              </div>
                            )}
                            {limitFields.includes("vnd") && (
                              <div>
                                <label className="block text-gray-600 mb-1" htmlFor={`limit-vnd-${cmd.id}`}>
                                  Giới hạn tiền mỗi lần, VNĐ (không vượt trần của Chủ; để trống nếu không đặt)
                                </label>
                                <input
                                  id={`limit-vnd-${cmd.id}`}
                                  type="number"
                                  min="0"
                                  value={limits[cmd.id]?.vnd || ""}
                                  onChange={(e) => handleLimitChange(cmd.id, "vnd", e.target.value)}
                                  placeholder="Nhập số tiền VNĐ"
                                  className="w-full rounded border px-2.5 py-1 bg-white"
                                />
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}

        {/* Cam kết trách nhiệm */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-4">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={ack}
              onChange={(e) => setAck(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-xs text-gray-700 leading-relaxed">
              Tôi xác nhận chịu hoàn toàn trách nhiệm cho mọi hành động và thao tác mà AI thực hiện
              thay mặt tôi theo cấu hình này (BR-AI-14).
            </span>
          </label>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={saving || !ack}
              className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 rounded shadow-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {saving ? "Đang lưu..." : "Lưu cấu hình"}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

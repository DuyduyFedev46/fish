"use client";

import { useEffect, useState, useCallback } from "react";
import { fetchDailyAiReport } from "../api";
import type { AiDailyReport } from "../../types";
import { Icon } from "@/shared/ui/Icon";
import { Loading } from "@/shared/ui/StateBox";
import { timeHMS, todayInVietnam } from "@/shared/lib/format";

export function AiDailyReportScreen() {
  const todayStr = todayInVietnam();
  const [selectedDate, setSelectedDate] = useState<string>(todayStr);
  const [report, setReport] = useState<AiDailyReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadReport = useCallback(async (date: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchDailyAiReport(date);
      setReport(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Không thể tải báo cáo AI của ngày.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadReport(selectedDate);
  }, [selectedDate, loadReport]);

  // Tính tổng các chỉ số
  const totals = report?.by_user.reduce(
    (acc, u) => ({
      A: acc.A + u.A,
      B: acc.B + u.B,
      C_confirmed: acc.C_confirmed + u.C_confirmed,
      C_expired: acc.C_expired + u.C_expired,
      undone: acc.undone + u.undone,
      escalated: acc.escalated + u.escalated,
    }),
    { A: 0, B: 0, C_confirmed: 0, C_expired: 0, undone: 0, escalated: 0 }
  ) || { A: 0, B: 0, C_confirmed: 0, C_expired: 0, undone: 0, escalated: 0 };

  const totalActions = report?.items.length || 0;

  return (
    <div className="space-y-6 p-4 md:p-6">
      {/* Tiêu đề & Chọn ngày */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-gray-100">
            Báo cáo AI cuối ngày
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Tổng hợp hoạt động của các trợ lý AI theo người dùng, hoàn tác, chuyển việc và quá hạn (DW-22).
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label htmlFor="report-date-picker" className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Ngày báo cáo:
          </label>
          <input
            id="report-date-picker"
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100"
          />
          <button
            type="button"
            onClick={() => loadReport(selectedDate)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
            title="Làm mới báo cáo"
          >
            <Icon name="refresh" />
            <span>Tải lại</span>
          </button>
        </div>
      </div>

      {loading ? (
        <div className="py-16">
          <Loading label="Đang tải dữ liệu báo cáo AI..." />
        </div>
      ) : error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-center text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          {error}
        </div>
      ) : (
        <div className="space-y-6">
          {/* KPI Cards */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-gray-900">
              <span className="text-xs font-medium text-gray-500">Tổng hành động</span>
              <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">{totalActions}</p>
            </div>
            <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-4 shadow-sm dark:border-blue-900 dark:bg-blue-950/20">
              <span className="text-xs font-medium text-blue-700 dark:text-blue-300">Mức A (Đọc)</span>
              <p className="mt-1 text-2xl font-bold text-blue-800 dark:text-blue-200">{totals.A}</p>
            </div>
            <div className="rounded-xl border border-purple-200 bg-purple-50/50 p-4 shadow-sm dark:border-purple-900 dark:bg-purple-950/20">
              <span className="text-xs font-medium text-purple-700 dark:text-purple-300">Mức B (Tự ghi)</span>
              <p className="mt-1 text-2xl font-bold text-purple-800 dark:text-purple-200">{totals.B}</p>
            </div>
            <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-4 shadow-sm dark:border-emerald-900 dark:bg-emerald-950/20">
              <span className="text-xs font-medium text-emerald-700 dark:text-emerald-300">Mức C (Duyệt)</span>
              <p className="mt-1 text-2xl font-bold text-emerald-800 dark:text-emerald-200">{totals.C_confirmed}</p>
            </div>
            <div className="rounded-xl border border-rose-200 bg-rose-50/50 p-4 shadow-sm dark:border-rose-900 dark:bg-rose-950/20">
              <span className="text-xs font-medium text-rose-700 dark:text-rose-300">Đã hoàn tác</span>
              <p className="mt-1 text-2xl font-bold text-rose-800 dark:text-rose-200">{totals.undone}</p>
            </div>
            <div className="rounded-xl border border-orange-200 bg-orange-50/50 p-4 shadow-sm dark:border-orange-900 dark:bg-orange-950/20">
              <span className="text-xs font-medium text-orange-700 dark:text-orange-300">Được chuyển</span>
              <p className="mt-1 text-2xl font-bold text-orange-800 dark:text-orange-200">{totals.escalated}</p>
            </div>
          </div>

          {/* Bảng theo người dùng (by_user) */}
          <div className="rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900">
            <div className="border-b border-gray-200 px-4 py-3 dark:border-gray-800">
              <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">
                Thống kê theo nhân sự
              </h2>
            </div>
            {report?.by_user.length === 0 ? (
              <p className="p-6 text-center text-sm text-gray-500">Không có dữ liệu trong ngày {selectedDate}.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                  <thead className="bg-gray-50 text-xs font-semibold uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                    <tr>
                      <th className="px-4 py-3">Nhân sự</th>
                      <th className="px-4 py-3 text-center">Mức A</th>
                      <th className="px-4 py-3 text-center">Mức B</th>
                      <th className="px-4 py-3 text-center">Mức C đã duyệt</th>
                      <th className="px-4 py-3 text-center">Mức C hết hạn</th>
                      <th className="px-4 py-3 text-center">Đã hoàn tác</th>
                      <th className="px-4 py-3 text-center">Được chuyển</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                    {report?.by_user.map((u) => (
                      <tr key={u.user_id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30">
                        <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">
                          {u.display_name}
                        </td>
                        <td className="px-4 py-3 text-center font-mono">{u.A}</td>
                        <td className="px-4 py-3 text-center font-mono text-purple-700 dark:text-purple-300 font-semibold">{u.B}</td>
                        <td className="px-4 py-3 text-center font-mono text-emerald-700 dark:text-emerald-300">{u.C_confirmed}</td>
                        <td className="px-4 py-3 text-center font-mono text-gray-500">{u.C_expired}</td>
                        <td className="px-4 py-3 text-center font-mono text-rose-700 dark:text-rose-300">{u.undone}</td>
                        <td className="px-4 py-3 text-center font-mono text-orange-700 dark:text-orange-300">{u.escalated}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Bảng chi tiết hành động (items) */}
          <div className="rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900">
            <div className="border-b border-gray-200 px-4 py-3 dark:border-gray-800">
              <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">
                Nhật ký việc AI trong ngày
              </h2>
            </div>
            {report?.items.length === 0 ? (
              <p className="p-6 text-center text-sm text-gray-500">Không có hành động nào phát sinh trong ngày {selectedDate}.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                  <thead className="bg-gray-50 text-xs font-semibold uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                    <tr>
                      <th className="px-4 py-3">Thời gian</th>
                      <th className="px-4 py-3">Tác nhân</th>
                      <th className="px-4 py-3">Lệnh AI</th>
                      <th className="px-4 py-3 text-center">Mức</th>
                      <th className="px-4 py-3">Trạng thái</th>
                      <th className="px-4 py-3">Chứng từ tham chiếu</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                    {report?.items.map((it) => (
                      <tr key={it.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30">
                        <td className="px-4 py-3 text-xs text-gray-500 font-mono">
                          {timeHMS(it.created_at)}
                        </td>
                        <td className="px-4 py-3 font-medium text-gray-800 dark:text-gray-200">
                          {it.owner_display}
                        </td>
                        <td className="px-4 py-3">
                          <span className="font-semibold text-gray-900 dark:text-gray-100">{it.title}</span>
                          <span className="block text-xs font-mono text-gray-400">{it.command}</span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className="font-mono font-semibold">{it.level}</span>
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${
                              it.status === "DONE" || it.status === "CONFIRMED"
                                ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                                : it.status === "UNDONE"
                                ? "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                                : it.status === "ESCALATED"
                                ? "bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300"
                                : it.status === "EXPIRED"
                                ? "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                                : "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300"
                            }`}
                          >
                            {it.status === "UNDONE"
                              ? "ĐÃ HOÀN TÁC"
                              : it.status === "ESCALATED"
                              ? "ĐƯỢC CHUYỂN"
                              : it.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-mono text-xs">
                          {it.target ? `${it.target.type} #${it.target.code}` : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

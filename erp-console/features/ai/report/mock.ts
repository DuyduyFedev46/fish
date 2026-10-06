// Mock "Báo cáo AI cuối ngày" — CHỈ dùng khi NEXT_PUBLIC_USE_MOCK=1 (bản build thật loại bỏ file này).
// Dữ liệu GIẢ, không có tên/SĐT thật. Từ 3 ngày trước trở về trước báo cáo rỗng (để thử trạng thái rỗng);
// `__caveMock.aiReportFail(true)` làm báo cáo trả lỗi 500 (để thử trạng thái lỗi).

import type { MockRequest, MockResponse } from "@/shared/lib/http";
import { todayInVietnam } from "@/shared/lib/format";
import { RECEIVE_BATCHES_COMMAND_ID } from "../commandGroups";
import type { AiDailyReport } from "../types";

let failing = false;

function dayDiff(from: string, to: string): number {
  return Math.round((Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / 86_400_000);
}

function buildReport(date: string): AiDailyReport {
  if (dayDiff(date, todayInVietnam()) >= 3) return { date, by_user: [], items: [] };
  const at = (hm: string) => `${date}T${hm}:00+07:00`;
  return {
    date,
    // Khớp với `items` bên dưới: 6 việc. Việc "Nhập lô" của Chủ là mức B rồi bị hoàn tác nên nằm ở cả cột B lẫn
    // "Đã hoàn tác" (đúng như BE đếm) — vì vậy "Tổng việc AI" lấy theo số dòng nhật ký (6), không cộng sáu cột (7).
    by_user: [
      { user_id: 1, display_name: "Chủ vựa (demo)", A: 0, B: 1, C_confirmed: 0, C_expired: 0, undone: 1, escalated: 0 },
      { user_id: 2, display_name: "Kho 1 (demo)", A: 0, B: 2, C_confirmed: 0, C_expired: 0, undone: 0, escalated: 1 },
      { user_id: 3, display_name: "Quản lý 1 (demo)", A: 1, B: 0, C_confirmed: 1, C_expired: 0, undone: 0, escalated: 0 },
    ],
    items: [
      {
        id: "rpt-2",
        command: "inventory.batch.close",
        title: "Chốt lô cá",
        level: "C",
        status: "ESCALATED",
        owner_display: "Kho 1 (demo)",
        created_at: at("17:42"),
        target: { type: "batch", code: "CA01-260928-AB" },
        result_ref: null,
      },
      {
        id: "rpt-3",
        command: RECEIVE_BATCHES_COMMAND_ID,
        title: "Nhập lô mua tại cảng",
        level: "B",
        status: "UNDONE",
        owner_display: "Chủ vựa (demo)",
        created_at: at("16:10"),
        target: { type: "purchasereceipt", code: "PR-260928-02" },
        result_ref: { model: "purchasereceipt", id: 102 },
      },
      {
        id: "rpt-4",
        command: "sales.refund.create",
        title: "Lập phiếu hoàn",
        level: "C",
        status: "CONFIRMED",
        owner_display: "Quản lý 1 (demo)",
        created_at: at("14:05"),
        target: { type: "refund", code: "RF-034" },
        result_ref: null,
      },
      {
        id: "rpt-1",
        command: RECEIVE_BATCHES_COMMAND_ID,
        title: "Nhập lô mua tại cảng",
        level: "B",
        status: "DONE",
        owner_display: "Kho 1 (demo)",
        created_at: at("09:15"),
        target: { type: "purchasereceipt", code: "PR-260928-01" },
        result_ref: { model: "purchasereceipt", id: 101 },
      },
      {
        id: "rpt-6",
        command: "inventory.batch.create",
        title: "Tạo mới batch", // tên tự sinh của BE: màn phải hiện "Tạo lô cá" (commandLabels.ts)
        level: "B",
        status: "DONE",
        owner_display: "Kho 1 (demo)",
        created_at: at("09:14"),
        target: null,
        result_ref: null,
      },
      {
        id: "rpt-5",
        command: "inventory.batch.list",
        title: "Xem tồn kho theo lô",
        level: "A",
        status: "DONE",
        owner_display: "Quản lý 1 (demo)",
        created_at: at("09:12"),
        target: null,
        result_ref: null,
      },
    ],
  };
}

export function mockDailyReport(req: MockRequest): MockResponse {
  if (failing) return { status: 500, body: { detail: "Máy chủ báo cáo đang bận.", code: "SERVER_ERROR" } };
  const date = new URL(req.path, "http://mock.local").searchParams.get("date") || todayInVietnam();
  return { status: 200, body: buildReport(date) };
}

if (process.env.NEXT_PUBLIC_USE_MOCK === "1" && typeof window !== "undefined") {
  const w = window as unknown as { __caveMock?: Record<string, unknown> };
  w.__caveMock = {
    ...(w.__caveMock || {}),
    aiReportFail: (v: boolean) => {
      failing = v;
      return failing;
    },
  };
}

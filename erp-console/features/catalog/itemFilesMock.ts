// Mock tải file Excel mặt hàng (FISH-66 S3, S4) — CHỈ chạy khi NEXT_PUBLIC_USE_MOCK=1. Theo contract 02b §3.2–3.3.
// Dữ liệu GIẢ (không dữ liệu thật, không giá vốn). File trả về chỉ là chữ thô đặt tên .xlsx, không mở được bằng Excel:
// mục đích là thử đường tải, tên file, số món, lỗi.
//
// Luật mock (mô phỏng BE):
//  - Cần catalog.view_item, không thì 403. Có catalog.view_itemprice thì file 17 cột, không (NV kho) thì 14 cột.
//  - item_type sai (khác SIMPLE|BUNDLE) hoặc is_active/has_image sai (khác 1|0) -> 400 INVALID_FILTER.
//  - Bộ lọc không khớp món nào -> vẫn 200, X-Row-Count 0 (S3-AC7).
// Công cụ thử trong DevTools: window.__caveMock.itemFiles("ok" | "fail" | "forbidden") — lưu localStorage (chỉ tên chế độ).

import { mockRequireUser, MOCK_UNAUTHORIZED } from "@/features/auth/mock";
import { todayInVietnam, timeHM } from "@/shared/lib/format";
import type { MockDownloadBody, MockRequest, MockResponse } from "@/shared/lib/http";
import { CATALOG_PERM as P } from "./permissions";

const MODE_KEY = "cave_erp_mock_item_files_mode";
type Mode = "ok" | "fail" | "forbidden";
const MODES: readonly Mode[] = ["fail", "forbidden"];
function mode(): Mode {
  try {
    const v = typeof window === "undefined" ? null : window.localStorage.getItem(MODE_KEY);
    return MODES.includes(v as Mode) ? (v as Mode) : "ok";
  } catch {
    return "ok";
  }
}

const XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
const COLUMNS_BASE = [
  "Mã hàng", "Tên", "Nhóm hàng", "Loại", "Đơn vị", "Đang kinh doanh", "Hạn dùng mặc định (ngày)", "Quản lý theo lô",
  "Có hạn dùng", "Ghi chú ngắn", "Quy cách", "Bảo quản", "Nguồn hàng", "Mô tả",
];
const COLUMNS_PRICE = ["Giá bán hiện hành", "Giá mới", "Ngày áp dụng giá mới"];

type FakeRow = { code: string; name: string; group: number; type: "SIMPLE" | "BUNDLE"; active: boolean; hasImage: boolean };
const ROWS: FakeRow[] = [
  { code: "CA-THU", name: "Cá thu một nắng", group: 3, type: "SIMPLE", active: true, hasImage: true },
  { code: "TOM-SU", name: "Tôm sú size 30", group: 5, type: "SIMPLE", active: true, hasImage: true },
  { code: "MUC-ONG", name: "Mực ống làm sạch", group: 6, type: "SIMPLE", active: false, hasImage: false },
  { code: "CB-HAI-SAN", name: "Combo hải sản gia đình", group: 9, type: "BUNDLE", active: true, hasImage: false },
];

const err = (status: number, code: string, detail: string): MockResponse => ({ status, body: { detail, code } });

function badFilter(query: URLSearchParams): MockResponse | null {
  const type = query.get("item_type");
  if (type && type !== "SIMPLE" && type !== "BUNDLE") return err(400, "INVALID_FILTER", "Tham số item_type có giá trị không hợp lệ.");
  for (const key of ["is_active", "has_image"]) {
    const v = query.get(key);
    if (v && v !== "1" && v !== "0") return err(400, "INVALID_FILTER", `Tham số ${key} có giá trị không hợp lệ.`);
  }
  const group = query.get("item_group");
  if (group && !/^\d+$/.test(group)) return err(400, "INVALID_FILTER", "Tham số item_group có giá trị không hợp lệ.");
  return null;
}

function stamp(): string {
  const now = new Date();
  return `${todayInVietnam(now).replace(/-/g, "")}-${timeHM(now).replace(":", "")}`;
}

function file(filename: string, columns: string[], lines: string[][]): MockResponse {
  const body: MockDownloadBody = {
    filename,
    rowCount: lines.length,
    contentType: XLSX,
    content: [columns, ...lines].map((l) => l.join("\t")).join("\n"),
  };
  return { status: 200, body };
}

export function mockItemFilesApi(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!me.permissions.includes(P.viewItem) || mode() === "forbidden") return err(403, "FORBIDDEN", "Thiếu quyền: catalog.view_item");
  if (mode() === "fail") return err(500, "SERVER_ERROR", "Máy chủ đang bận. Thử lại sau.");
  const [pathname, qs = ""] = req.path.split("?");
  const query = new URLSearchParams(qs);
  const columns = me.permissions.includes(P.viewItemPrice) ? [...COLUMNS_BASE, ...COLUMNS_PRICE] : COLUMNS_BASE;
  const pad = (cells: string[]) => [...cells, ...Array(Math.max(0, columns.length - cells.length)).fill("")];

  if (pathname === "/api/catalog/items/export-template/") {
    return file("mau-hang-ban.xlsx", columns, [pad(["VD-001", "Cá ví dụ", "Nhóm ví dụ", "Mặt hàng thường", "Kg", "Có", "365", "Có", "Có"])]);
  }
  if (pathname !== "/api/catalog/items/export/") return err(404, "NOT_FOUND", "Không tìm thấy endpoint.");

  const bad = badFilter(query);
  if (bad) return bad;
  const group = query.get("item_group");
  const active = query.get("is_active");
  const type = query.get("item_type");
  const image = query.get("has_image");
  const hit = ROWS.filter(
    (r) =>
      (!group || String(r.group) === group) &&
      (!active || r.active === (active === "1")) &&
      (!type || r.type === type) &&
      (!image || r.hasImage === (image === "1")),
  );
  return file(`hang-ban-${stamp()}.xlsx`, columns, hit.map((r) => pad([r.code, r.name])));
}

if (process.env.NEXT_PUBLIC_USE_MOCK === "1" && typeof window !== "undefined") {
  const w = window as unknown as { __caveMock?: Record<string, unknown> };
  w.__caveMock = {
    ...(w.__caveMock || {}),
    itemFiles: (m: Mode) => {
      if (m === "ok") window.localStorage.removeItem(MODE_KEY);
      else window.localStorage.setItem(MODE_KEY, m);
      return `Tải file mặt hàng (mock): chế độ ${m}`;
    },
  };
}

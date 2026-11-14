// Mock tải và nhập file Excel mặt hàng (FISH-66 S3–S6) — CHỈ chạy khi NEXT_PUBLIC_USE_MOCK=1. Theo contract 02b §3.2–3.6.
// Dữ liệu GIẢ (không dữ liệu thật, không giá vốn).
//
// Luật mock nhập file (02b §10):
//  - Cần đủ 4 quyền IMPORT_PERMS, không thì 403.
//  - Preview chọn tình huống theo tên file hoặc chế độ __caveMock.itemFiles(mode):
//      * chứa "error" hoặc mode="rowErrors" -> 400 IMPORT_INVALID_ROWS
//      * chứa "nochange" hoặc mode="noChanges" -> 200 has_changes=false
//      * chứa "bad" -> 400 IMPORT_INVALID_FILE
//      * chứa "stale" hoặc mode="dataChanged" -> commit trả 409 IMPORT_DATA_CHANGED
//      * chứa "expired" hoặc mode="expired" -> commit trả 410 IMPORT_PREVIEW_EXPIRED
//      * còn lại -> 200 hợp lệ (đổi giá, món mới, món sửa, ẩn/hiện, cảnh báo cột chỉ đọc).
//  - Commit lần 2 cùng preview_token hoặc mode="alreadyApplied" -> 409 IMPORT_ALREADY_APPLIED.

import { mockRequireUser, MOCK_UNAUTHORIZED } from "@/features/auth/mock";
import { todayInVietnam, timeHM } from "@/shared/lib/format";
import type { MockDownloadBody, MockRequest, MockResponse } from "@/shared/lib/http";
import { CATALOG_PERM as P, IMPORT_PERMS } from "./permissions";
import type { ImportLimits, ImportPreviewResponse } from "./itemFilesTypes";

const MODE_KEY = "cave_erp_mock_item_files_mode";
export type ItemFilesMockMode =
  | "ok"
  | "fail"
  | "forbidden"
  | "rowErrors"
  | "noChanges"
  | "dataChanged"
  | "expired"
  | "alreadyApplied";

const MODES: readonly ItemFilesMockMode[] = [
  "fail",
  "forbidden",
  "rowErrors",
  "noChanges",
  "dataChanged",
  "expired",
  "alreadyApplied",
];

function mode(): ItemFilesMockMode {
  try {
    const v = typeof window === "undefined" ? null : window.localStorage.getItem(MODE_KEY);
    return MODES.includes(v as ItemFilesMockMode) ? (v as ItemFilesMockMode) : "ok";
  } catch {
    return "ok";
  }
}

const appliedTokens = new Set<string>();

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

const MOCK_LIMITS: ImportLimits = {
  max_rows: 1000,
  max_bytes: 2097152,
  preview_ttl_minutes: 30,
};

const err = (status: number, code: string, detail: string, extra?: Record<string, unknown>): MockResponse => ({
  status,
  body: { detail, code, ...(extra || {}) },
});

function hasAllImportPerms(perms: readonly string[]): boolean {
  return IMPORT_PERMS.every((p) => perms.includes(p));
}

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

function extractUploadedFile(body: unknown): File | null {
  if (typeof FormData !== "undefined" && body instanceof FormData) {
    const f = body.get("file");
    return f instanceof File ? f : null;
  }
  return null;
}

function extractPreviewToken(body: unknown): string {
  if (typeof FormData !== "undefined" && body instanceof FormData) {
    const t = body.get("preview_token");
    return typeof t === "string" ? t : "";
  }
  if (body && typeof body === "object" && "preview_token" in body) {
    const t = (body as Record<string, unknown>).preview_token;
    return typeof t === "string" ? t : "";
  }
  return "";
}

function buildValidPreview(tokenSuffix: string): ImportPreviewResponse {
  const expires = new Date(Date.now() + 30 * 60 * 1000).toISOString();
  return {
    preview_token: `mock-preview-${tokenSuffix}`,
    expires_at: expires,
    has_changes: true,
    summary: {
      total_rows: 200,
      created: 1,
      updated: 1,
      price_changed: 4,
      visibility_changed: 1,
      unchanged: 195,
      will_show_on_shop: 1,
      will_hide_from_shop: 1,
    },
    rows: [
      {
        row: 3,
        code: "CA-01",
        action: "update",
        name: "Cá thu cắt khúc",
        item_group: "Cá biển",
        changes: [
          { field: "name", label: "Tên", old: "Cá thu", new: "Cá thu cắt khúc" },
          { field: "spec", label: "Quy cách", old: "Khúc 300g", new: "Khúc giữa 350g, hút chân không" },
        ],
        price: null,
        is_active_after: true,
        shop_state: "selling",
      },
      {
        row: 4,
        code: "TOM-02",
        action: "update",
        name: "Tôm sú",
        item_group: "Tôm",
        changes: [],
        price: {
          old: "278000",
          new: "265000",
          valid_from: "2026-11-15",
          change_amount: "-13000",
          change_percent: "-4.7",
          flags: [],
        },
        is_active_after: true,
        shop_state: "selling",
      },
      {
        row: 17,
        code: "CA-07",
        action: "update",
        name: "Cá thu một nắng",
        item_group: "Cá biển",
        changes: [],
        price: {
          old: "185000",
          new: "18500",
          valid_from: "2026-11-14",
          change_amount: "-166500",
          change_percent: "-90.0",
          flags: ["check_zeros", "large_change"],
        },
        is_active_after: true,
        shop_state: "selling",
      },
      {
        row: 23,
        code: "MUC-03",
        action: "update",
        name: "Mực lá",
        item_group: "Mực",
        changes: [],
        price: {
          old: "240000",
          new: "320000",
          valid_from: "2026-11-10",
          change_amount: "80000",
          change_percent: "33.3",
          flags: ["large_change", "backdated"],
        },
        is_active_after: false,
        shop_state: "hidden",
      },
      {
        row: 30,
        code: "GHE-01",
        action: "update",
        name: "Ghẹ xanh",
        item_group: "Cua ghẹ",
        changes: [{ field: "is_active", label: "Đang kinh doanh", old: "Có", new: "Không" }],
        price: null,
        is_active_after: false,
        shop_state: "will_hide",
      },
      {
        row: 201,
        code: "MUC-09",
        action: "create",
        name: "Mực ống",
        item_group: "Mực",
        changes: [],
        price: {
          old: null,
          new: "180000",
          valid_from: "2026-11-14",
          change_amount: null,
          change_percent: null,
          flags: [],
        },
        is_active_after: true,
        shop_state: "will_show",
      },
    ],
    warnings: [
      {
        row: 12,
        code: "CA-03",
        column: "Giá bán hiện hành",
        message: "Cột Giá bán hiện hành chỉ để xem, không đổi giá. Muốn đổi giá, ghi vào cột Giá mới.",
      },
    ],
    limits: MOCK_LIMITS,
  };
}

export function mockItemFilesApi(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  const [pathname, qs = ""] = req.path.split("?");
  const currentMode = mode();

  // ---- Các endpoint nhập file Excel (S5, S6) ----
  if (pathname.startsWith("/api/catalog/items/import/")) {
    if (!hasAllImportPerms(me.permissions) || currentMode === "forbidden") {
      return err(403, "FORBIDDEN", "Thiếu quyền nhập mặt hàng từ Excel.");
    }
    if (currentMode === "fail") {
      return err(500, "SERVER_ERROR", "Máy chủ đang bận. Thử lại sau.");
    }
    if (pathname === "/api/catalog/items/import/limits/") {
      return { status: 200, body: MOCK_LIMITS };
    }
    if (pathname === "/api/catalog/items/import/preview/") {
      const f = extractUploadedFile(req.body);
      const fname = (f?.name || "").toLowerCase();
      if (!f || (!fname.endsWith(".xlsx") && !fname.includes("bad"))) {
        return err(
          400,
          "IMPORT_INVALID_FILE",
          "Chỉ nhận file .xlsx. Trong Excel chọn Lưu thành → Sổ làm việc Excel (.xlsx).",
          { reason: "not_xlsx", limits: MOCK_LIMITS },
        );
      }
      if (fname.includes("bad")) {
        return err(
          400,
          "IMPORT_INVALID_FILE",
          "Thiếu cột Giá mới. Tải file mẫu để lấy đúng tên cột.",
          { reason: "missing_columns", columns: ["Giá mới"], limits: MOCK_LIMITS },
        );
      }
      if (fname.includes("error") || currentMode === "rowErrors") {
        return err(400, "IMPORT_INVALID_ROWS", "File có 5 lỗi ở 4 dòng. Chưa ghi gì.", {
          error_count: 5,
          error_row_count: 4,
          errors_truncated: false,
          errors: [
            { row: 5, code: "TOM-02", column: "Giá mới", message: "Giá phải là số nguyên đồng lớn hơn 0." },
            { row: 8, code: "TOM-05", column: "Nhóm hàng", message: "Nhóm \"Tôm hùmm\" chưa có. Tạo nhóm ở ERP trước hoặc sửa đúng tên nhóm." },
            { row: 9, code: "CA-01", column: "Mã hàng", message: "Mã CA-01 lặp ở dòng 9 và 12. Mỗi mã chỉ ghi một dòng." },
            { row: 12, code: "CA-01", column: "Mã hàng", message: "Mã CA-01 lặp ở dòng 9 và 12. Mỗi mã chỉ ghi một dòng." },
            { row: 14, code: "CA-09", column: "Mô tả", message: "Không ghi nhà cung cấp, tên tàu hay ngày nhập lô trong thông tin món." },
          ],
          limits: MOCK_LIMITS,
        });
      }
      if (fname.includes("nochange") || currentMode === "noChanges") {
        const emptyPreview: ImportPreviewResponse = {
          preview_token: null,
          expires_at: null,
          has_changes: false,
          summary: {
            total_rows: 4,
            created: 0,
            updated: 0,
            price_changed: 0,
            visibility_changed: 0,
            unchanged: 4,
            will_show_on_shop: 0,
            will_hide_from_shop: 0,
          },
          rows: [],
          warnings: [],
          limits: MOCK_LIMITS,
        };
        return { status: 200, body: emptyPreview };
      }
      const suffix = fname.includes("stale") ? "stale" : fname.includes("expired") ? "expired" : "ok";
      return { status: 200, body: buildValidPreview(suffix) };
    }
    if (pathname === "/api/catalog/items/import/commit/") {
      const token = extractPreviewToken(req.body);
      if (!token) {
        return err(400, "IMPORT_PREVIEW_INVALID", "File khác với file đã xem trước. Bấm Xem trước lại.");
      }
      if (appliedTokens.has(token) || currentMode === "alreadyApplied") {
        return err(409, "IMPORT_ALREADY_APPLIED", "Lượt nhập này đã ghi rồi.", {
          created: 1,
          updated: 1,
          price_changed: 4,
          visibility_changed: 1,
        });
      }
      if (token.endsWith("stale") || currentMode === "dataChanged") {
        return err(
          409,
          "IMPORT_DATA_CHANGED",
          "Mặt hàng vừa được sửa sau lúc bạn xem trước. Chưa ghi gì. Bấm Xem trước lại để so với dữ liệu mới.",
        );
      }
      if (token.endsWith("expired") || currentMode === "expired") {
        return err(
          410,
          "IMPORT_PREVIEW_EXPIRED",
          "Phiên xem trước đã hết hạn. Chưa ghi gì. Bấm Xem trước lại.",
        );
      }
      appliedTokens.add(token);
      return {
        status: 200,
        body: {
          created: 1,
          updated: 1,
          price_changed: 4,
          visibility_changed: 1,
          codes: ["CA-01", "CA-07", "GHE-01", "MUC-03", "MUC-09", "TOM-02"],
        },
      };
    }
    return err(404, "NOT_FOUND", "Không tìm thấy endpoint.");
  }

  // ---- Các endpoint tải file Excel (S3, S4) ----
  if (!me.permissions.includes(P.viewItem) || currentMode === "forbidden") {
    return err(403, "FORBIDDEN", "Thiếu quyền: catalog.view_item");
  }
  if (currentMode === "fail") return err(500, "SERVER_ERROR", "Máy chủ đang bận. Thử lại sau.");
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
    itemFiles: (m: ItemFilesMockMode) => {
      appliedTokens.clear();
      if (m === "ok") window.localStorage.removeItem(MODE_KEY);
      else window.localStorage.setItem(MODE_KEY, m);
      return `Tải/nhập file mặt hàng (mock): chế độ ${m}`;
    },
  };
}

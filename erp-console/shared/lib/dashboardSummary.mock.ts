// Dữ liệu seed mock cho GET /api/dashboard/summary/ — CHỈ được import từ features/<x>/mock.ts
// (các file đó chỉ được dùng khi NEXT_PUBLIC_USE_MOCK=1, nên bản build thật không chứa file này).
//
// Dựng JSON theo ĐÚNG cách DashboardSummaryView tính (backend/apps/reports/dashboard_api.py):
//  - near_expiry_days = NEAR_DAYS ở CẤP GỐC, không trong kpis (key mới, code review trước deploy 1; mode "nodays" bỏ key như BE cũ).
//  - KPI tính trên TOÀN BỘ seed (11 đơn, 13 lô), không chỉ phần cắt ra hiển thị.
//  - recent_orders = 8 đơn mới nhất; batches = lô DRAFT/SELLING/NEAR_EXPIRY theo received_date, tối đa 20;
//    alerts = lô bán được (SELLING/NEAR_EXPIRY, hạn ≥ hôm nay) có hạn ≤ hôm nay+14, hạn gần trước, tối đa 6; activity = 8 dòng sổ kho mới nhất.
//  - `unit_cost` và `kpis.inventory_value` chỉ có key khi can_cost (BE L6 đã vá rò; thiếu quyền → không có key).
//  - Mốc ngày/giờ tính theo "bây giờ" để cận hạn / giữ chỗ luôn có ý nghĩa.
//
// Công cụ thử trong DevTools (chỉ có ở mock):
//   window.__caveMock.dashboard("fail" | "empty" | "ok" | "nodays" | "forbidden") — 500 / rỗng / bình thường /
//     thiếu near_expiry_days / luôn 403 (lưu qua reload)
//   window.__caveMock.dashboardJson("loc")                — JSON mock đúng như người đó nhận (e2e so với bản cũ)

import type { MockResponse } from "./http";
import type {
  BatchStatus,
  DashboardBatch,
  DashboardSummary,
  LedgerActivity,
  MovementType,
  OrderStatus,
  RecentOrder,
} from "./dashboardSummary";

const MODE_KEY = "cave_erp_mock_dashboard";
const NEAR_DAYS = 14;
const ACTIVE: BatchStatus[] = ["SELLING", "NEAR_EXPIRY", "DRAFT"];
const SELLABLE: BatchStatus[] = ["SELLING", "NEAR_EXPIRY"];
const PENDING: OrderStatus[] = ["BOOKED", "PAID", "PROCESSING"];

const ORDER_LABEL: Record<OrderStatus, string> = {
  BOOKED: "Giữ chỗ",
  PAID: "Đã thanh toán",
  PROCESSING: "Đang xử lý",
  COMPLETED: "Hoàn tất",
  CANCELLED: "Đã huỷ",
  AUTO_CANCELLED: "Tự huỷ (quá TTL)",
};
const BATCH_LABEL: Record<BatchStatus, string> = {
  DRAFT: "Nháp",
  SELLING: "Đang bán",
  NEAR_EXPIRY: "Cận hạn",
  SOLD_OUT: "Hết hàng",
  EXPIRED: "Quá hạn",
  CANCELLED: "Đã huỷ",
  CLOSED: "Đã chốt",
};
const MOVE_LABEL: Record<MovementType, string> = {
  RECEIPT: "Nhập lô",
  SALE: "Bán ra",
  RETURN_RESTOCK: "Hàng hoàn tái nhập",
  RECONCILE: "Điều chỉnh kiểm kê",
  WRITE_OFF: "Hạch toán lỗ / huỷ",
  CANCEL_RESTORE: "Hoàn kho do huỷ đơn",
};

const KHO_LANH = "Kho lạnh Bến Đá";
const KHO_MAT = "Kho mát chợ Vũng Tàu";

// [batch_id, item, warehouse, supplier, qty_available, qty_reserved, nhận (ngày trước), hạn (ngày tới), status, landed_unit_cost]
type SeedBatch = [string, string, string, string, number, number, number, number, BatchStatus, number];
const BATCHES: SeedBatch[] = [
  ["L0914-CT01", "Cá thu phi lê", KHO_LANH, "Ghe Tư Hải", 18.5, 2, 10, 4, "NEAR_EXPIRY", 182000],
  ["L0915-MU02", "Mực lá câu", KHO_LANH, "Vựa Bà Năm", 12, 1.5, 9, 1, "NEAR_EXPIRY", 236500],
  ["L0916-TS01", "Tôm sú size 20", KHO_LANH, "Tàu Phước Lộc 07", 25.25, 0, 8, 9, "SELLING", 312000],
  ["L0917-CB01", "Cá bớp cắt khúc", KHO_LANH, "Ghe Tư Hải", 30, 4, 7, 21, "SELLING", 158000],
  ["L0918-GX01", "Ghẹ xanh", KHO_MAT, "Vựa Bà Năm", 9.8, 0.8, 6, 2, "SELLING", 265000],
  ["L0918-CH01", "Cá hồng đỏ", KHO_LANH, "Tàu Phước Lộc 07", 22.4, 0, 6, 25, "SELLING", 142500],
  ["L0919-CN01", "Cá ngừ đại dương loin", KHO_LANH, "Tàu Phước Lộc 07", 41.75, 6.5, 5, 30, "SELLING", 205000],
  ["L0920-CC01", "Cá chim trắng", KHO_LANH, "Ghe Tư Hải", 16, 0, 4, 12, "SELLING", 176000],
  ["L0921-MU03", "Mực ống", KHO_LANH, "Vựa Bà Năm", 0, 0, 3, 18, "SOLD_OUT", 198000],
  ["L0921-CT02", "Cá thu nguyên con", KHO_LANH, "Ghe Tư Hải", 35, 3, 3, 28, "SELLING", 149000],
  ["L0922-TS02", "Tôm sú size 30", KHO_LANH, "Tàu Phước Lộc 07", 20, 0, 2, 26, "DRAFT", 268000],
  ["L0923-SO01", "Sò điệp", KHO_MAT, "Vựa Bà Năm", 14.2, 0, 1, 5, "DRAFT", 88000],
  ["L0901-CB00", "Cá bớp cắt khúc", KHO_LANH, "Ghe Tư Hải", 0, 0, 23, -2, "CLOSED", 151000],
];

// [code, customer ("" = Khách lẻ), phone, total, status, phút trước, hạn giữ chỗ còn (phút) | null]
type SeedOrder = [string, string, string, number, OrderStatus, number, number | null];
const ORDERS: SeedOrder[] = [
  ["DH-240924-011", "Chị Mai (Q.1)", "0903118822", 1_092_000, "BOOKED", 22, 6],
  ["DH-240924-010", "", "0937004561", 546_000, "BOOKED", 9, 21],
  ["DH-240924-009", "Nhà hàng Biển Xanh", "0282204455", 4_860_000, "PAID", 48, null],
  ["DH-240924-008", "Anh Khoa", "0918772310", 780_000, "PROCESSING", 95, null],
  ["DH-240924-007", "Cô Thuý", "0909556677", 1_415_000, "COMPLETED", 180, null],
  ["DH-240924-006", "", "0977123450", 312_000, "AUTO_CANCELLED", 240, null],
  ["DH-240924-005", "Quán Ốc Tám", "0985661234", 2_236_000, "PROCESSING", 300, null],
  ["DH-240924-004", "Chị Ngân", "0903998877", 928_000, "CANCELLED", 420, null],
  ["DH-240923-018", "Anh Bình", "0912345098", 1_640_000, "COMPLETED", 1_200, null],
  ["DH-240923-017", "Nhà hàng Hải Âu", "0283221100", 6_210_000, "PAID", 1_300, null],
  ["DH-240923-016", "", "0966440022", 459_000, "COMPLETED", 1_420, null],
];

// [batch_id, type, qty_change, reference, phút trước]
type SeedLedger = [string, MovementType, number, string, number];
const LEDGER: SeedLedger[] = [
  ["L0923-SO01", "RECEIPT", 14.2, "PN-240924-02", 35],
  ["L0919-CN01", "SALE", -3.5, "HD-240924-009", 47],
  ["L0917-CB01", "SALE", -2.25, "HD-240924-008", 94],
  ["L0918-GX01", "CANCEL_RESTORE", 1.2, "DH-240924-004", 110],
  ["L0914-CT01", "RECONCILE", -0.4, "KK-240924-01", 150],
  ["L0901-CB00", "WRITE_OFF", -1.1, "LO-HUY-0901", 200],
  ["L0921-CT02", "SALE", -5, "HD-240924-005", 298],
  ["L0922-TS02", "RECEIPT", 20, "PN-240922-01", 330],
  ["L0916-TS01", "RETURN_RESTOCK", 0.8, "HV-240921-01", 2_000],
];

const REVENUE_TODAY = 9_291_000; // tổng hoá đơn ISSUED hôm nay (không suy ra từ seed đơn)

function localIsoDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}
function addDays(base: Date, days: number): Date {
  const d = new Date(base.getFullYear(), base.getMonth(), base.getDate());
  d.setDate(d.getDate() + days);
  return d;
}

/**
 * "nodays" = như "ok" nhưng KHÔNG có key near_expiry_days (BE cũ) — kiểm FE ẩn số ngày.
 * "forbidden" = luôn 403 dù có quyền (giả lập luật FE/BE lệch nhau) — kiểm 403 ổn định không làm /me bị gọi lặp.
 */
export type MockDashboardMode = "ok" | "fail" | "empty" | "nodays" | "forbidden";

export function mockDashboardMode(): MockDashboardMode {
  try {
    const v = window.localStorage.getItem(MODE_KEY);
    return v === "fail" || v === "empty" || v === "nodays" || v === "forbidden" ? v : "ok";
  } catch {
    return "ok";
  }
}

export function buildDashboardSummaryMock(
  user: { username: string; can_cost: boolean },
  mode: MockDashboardMode = "ok",
  now: Date = new Date()
): DashboardSummary {
  const today = addDays(now, 0);
  const nearCutoff = addDays(now, NEAR_DAYS);
  const empty = mode === "empty";

  const allBatches = (empty ? [] : BATCHES).map((b, i) => ({
    id: i + 1,
    batch_id: b[0],
    item: b[1],
    warehouse: b[2],
    supplier: b[3],
    qty_available: b[4],
    qty_reserved: b[5],
    received: addDays(now, -b[6]),
    expiry: addDays(now, b[7]),
    status: b[8],
    cost: b[9],
  }));
  const active = allBatches.filter((b) => ACTIVE.includes(b.status));
  // BE R6 (code review trước deploy 1): cận hạn = lô BÁN ĐƯỢC (SELLING/NEAR_EXPIRY, hạn ≥ hôm nay) có hạn ≤ hôm nay + N;
  // DRAFT / quá hạn không tính. Cờ near_expiry từng dòng lô dùng cùng tiêu chí.
  const isNear = (b: { status: BatchStatus; expiry: Date }) =>
    SELLABLE.includes(b.status) && b.expiry >= today && b.expiry <= nearCutoff;
  const near = active.filter(isNear);

  const batches: DashboardBatch[] = [...active]
    .sort((a, b) => a.received.getTime() - b.received.getTime() || a.id - b.id)
    .slice(0, 20)
    .map((b) => {
      const row: DashboardBatch = {
        batch_id: b.batch_id,
        item: b.item,
        warehouse: b.warehouse,
        supplier: b.supplier,
        qty_available: b.qty_available,
        qty_reserved: b.qty_reserved,
        received_date: localIsoDate(b.received),
        expiry_date: localIsoDate(b.expiry),
        status: b.status,
        status_label: BATCH_LABEL[b.status],
        near_expiry: isNear(b),
      };
      if (user.can_cost) row.unit_cost = b.cost;
      return row;
    });

  const orders = (empty ? [] : ORDERS).map((o, i) => ({
    id: i + 1,
    code: o[0],
    customer: o[1],
    phone: o[2],
    total: o[3],
    status: o[4],
    created: new Date(now.getTime() - o[5] * 60000),
    expires: o[6] === null ? null : new Date(now.getTime() + o[6] * 60000),
  }));
  const recent_orders: RecentOrder[] = [...orders]
    .sort((a, b) => b.created.getTime() - a.created.getTime() || b.id - a.id)
    .slice(0, 8)
    .map((o) => ({
      code: o.code,
      customer: o.customer || "Khách lẻ",
      phone_last4: o.phone.slice(-4),
      amount: o.total,
      status: o.status,
      status_label: ORDER_LABEL[o.status],
      expires_at: o.expires ? o.expires.toISOString() : null,
    }));

  const activity: LedgerActivity[] = (empty ? [] : LEDGER)
    .map((e, i) => ({ id: i + 1, e, at: new Date(now.getTime() - e[4] * 60000) }))
    .sort((a, b) => b.at.getTime() - a.at.getTime() || b.id - a.id)
    .slice(0, 8)
    .map(({ e, at }) => ({
      type: e[1],
      type_label: MOVE_LABEL[e[1]],
      batch_id: e[0],
      qty_change: e[2],
      reference: e[3],
      at: at.toISOString(),
    }));

  const inventoryValue = active.reduce((s, b) => s + b.qty_available * b.cost, 0);

  return {
    as_of: now.toISOString(),
    ...(mode === "nodays" ? {} : { near_expiry_days: NEAR_DAYS }),
    user: { username: user.username, can_cost: user.can_cost },
    kpis: {
      revenue_today: empty ? 0 : REVENUE_TODAY,
      pending_orders: orders.filter((o) => PENDING.includes(o.status)).length,
      booked_soon: orders.filter(
        (o) => o.status === "BOOKED" && o.expires && o.expires.getTime() <= now.getTime() + 10 * 60000
      ).length,
      near_expiry: near.length,
      ...(user.can_cost ? { inventory_value: Math.round(inventoryValue * 100) / 100 } : {}),
    },
    recent_orders,
    batches,
    alerts: [...near]
      .sort((a, b) => a.expiry.getTime() - b.expiry.getTime())
      .slice(0, 6)
      .map((b) => ({
        batch_id: b.batch_id,
        item: b.item,
        expiry_date: localIsoDate(b.expiry),
        days_left: Math.round((b.expiry.getTime() - today.getTime()) / 86_400_000),
        qty: b.qty_available,
      })),
    activity,
  };
}

/**
 * Response mock cho người dùng đã xác thực (module gọi sau khi kiểm token bằng mockRequireUser).
 * Như BE (S6, CanViewDashboard): thiếu reports.view_dashboard → 403 (DRF, LANGUAGE_CODE=vi).
 */
export function dashboardSummaryMockResponse(user: {
  username: string;
  can_cost: boolean;
  can_view_dashboard: boolean;
}): MockResponse {
  if (!user.can_view_dashboard || mockDashboardMode() === "forbidden") {
    return { status: 403, body: { detail: "Bạn không có quyền để thực hiện thao tác này." } };
  }
  const mode = mockDashboardMode();
  // Django 500 trả trang HTML → apiFetch không đọc được JSON → body null.
  if (mode === "fail") return { status: 500, body: null };
  return { status: 200, body: buildDashboardSummaryMock(user, mode) };
}

if (process.env.NEXT_PUBLIC_USE_MOCK === "1" && typeof window !== "undefined") {
  const w = window as unknown as { __caveMock?: Record<string, unknown> };
  w.__caveMock = {
    ...(w.__caveMock || {}),
    dashboard: (mode: MockDashboardMode) => {
      window.localStorage.setItem(MODE_KEY, mode);
      return `Dashboard mock: ${mode}`;
    },
    dashboardJson: (username: string) =>
      buildDashboardSummaryMock({ username, can_cost: username === "loc" }, mockDashboardMode()),
  };
}

// Mock Báo cáo lãi lỗ (ED-32) — chỉ dùng khi NEXT_PUBLIC_USE_MOCK=1. Dữ liệu bịa, không có thông tin khách.
// Response trả tiền/kg dạng number như BE thật (xem asWire); api.ts chuẩn hoá về chuỗi.
// Quyền như BE: cả hai endpoint chỉ cho reports.view_profitreport (Chủ), vai khác nhận 403.
// Số liệu kỳ khớp công thức của BE: revenue/cogs ĐÃ trừ phần đảo, profit = revenue − cogs − refunds; kỳ cách đây quá 3 tháng thì trống.
// Danh sách lô: 24 lô (hơn một trang 20 dòng) phát sinh ở tháng này và tháng trước, vài lô lỗ, vài lô tạm tính.
//   window.__caveMock.reports("ok" | "fail")  — đổi chế độ để kiểm trạng thái lỗi.
import type { MockRequest, MockResponse } from "@/shared/lib/http";
import { todayInVietnam } from "@/shared/lib/format";
import { MOCK_UNAUTHORIZED, mockRequireUser } from "@/features/auth/mock";
import { formatDecimal, parseDecimal, subDecimal } from "./decimal";
import type { BatchReportRow, PeriodReport } from "./types";

const PAGE_SIZE = 20;
const FORBIDDEN: MockResponse = { status: 403, body: { detail: "Bạn không có quyền để thực hiện thao tác này." } };
const bad = (detail: string): MockResponse => ({ status: 400, body: { detail } });
const SERVER_ERROR: MockResponse = { status: 500, body: { detail: "Có lỗi xảy ra phía máy chủ." } };

type Mode = "ok" | "fail";
let mode: Mode = "ok";

const params = (path: string) => new URLSearchParams(path.split("?")[1] ?? "");

/** Số tháng cách tháng hiện tại (giờ VN): 0 = tháng này. */
function monthsAgo(year: number, month: number): number {
  const [y, m] = todayInVietnam().split("-").map(Number);
  return (y * 12 + m) - (year * 12 + month);
}

// ---- Kỳ ----
// [doanh thu hoá đơn, giá vốn hoá đơn, chứng từ đảo, giá vốn đảo, hoàn tiền, số hoá đơn, số phiếu hoàn] theo số tháng trước.
const PERIOD_SEEDS: Record<number, [string, string, string, string, string, number, number]> = {
  0: ["18450000", "12310000", "850000", "560000", "250000", 14, 1],
  1: ["24600000", "16200000", "0", "0", "0", 21, 0],
  2: ["9800000", "11900000", "0", "0", "400000", 9, 1], // lỗ
  3: ["15200000", "10100000", "0", "0", "0", 12, 0],
};

function periodOf(year: number, month: number): PeriodReport {
  const seed = PERIOD_SEEDS[monthsAgo(year, month)];
  if (!seed) {
    return { year, month, revenue: "0.00", cogs: "0.00", credit_notes: "0.00", cogs_reversed: "0.00", refunds: "0.00", profit: "0.00", invoice_count: 0, refund_count: 0 };
  }
  const [gross, grossCogs, creditNotes, cogsReversed, refunds, invoices, refundCount] = seed;
  const revenue = subDecimal(gross, creditNotes) ?? "0";
  const cogs = subDecimal(grossCogs, cogsReversed) ?? "0";
  const profit = subDecimal(subDecimal(revenue, cogs) ?? "0", refunds) ?? "0";
  const money = (v: string) => formatDecimal(parseDecimal(v) ?? BigInt(0)) + ".00";
  return {
    year,
    month,
    revenue: money(revenue),
    cogs: money(cogs),
    credit_notes: money(creditNotes),
    cogs_reversed: money(cogsReversed),
    refunds: money(refunds),
    profit: money(profit),
    invoice_count: invoices,
    refund_count: refundCount,
  };
}

// ---- Lô ----
// [mã lô, mặt hàng, tháng trước, đã chốt?, kg nhập, kg bán, giá mua/kg, doanh thu, chi phí phân bổ, kg hao hụt, kg hỏng, kg quá hạn, kg trả NCC, tiền NCC hoàn, kg đảo, doanh thu đảo]
type BatchSeed = [string, string, number, boolean, number, number, number, number, number, number, number, number, number, number, number, number];
const BATCH_SEEDS: BatchSeed[] = [
  ["LO-0924-A", "Cá thu nguyên con", 0, false, 120, 74.5, 95000, 8_940_000, 420_000, 2, 0, 0, 0, 0, 0, 0],
  ["LO-0924-B", "Cá ngừ đại dương", 0, false, 80, 31, 130000, 4_650_000, 300_000, 0, 1.5, 0, 0, 0, 0, 0],
  ["LO-0924-C", "Mực ống tươi", 0, false, 60, 12, 180000, 2_400_000, 150_000, 0, 0, 0, 0, 0, 0, 0],
  ["LO-0924-D", "Tôm sú size 30", 0, false, 40, 18, 250000, 5_850_000, 220_000, 0.5, 0, 0, 2, 380_000, 2, 650_000],
  ["LO-0924-E", "Cá bớp phi lê", 0, false, 50, 4, 140000, 780_000, 90_000, 0, 0, 0, 0, 0, 0, 0],
  ["LO-0924-F", "Ghẹ xanh", 0, false, 30, 9, 210000, 2_160_000, 130_000, 0, 0, 0, 0, 0, 0, 0],
  ["LO-0924-G", "Cá mú đỏ", 0, false, 25, 6, 320000, 2_100_000, 110_000, 0, 0, 0, 0, 0, 0, 0],
  ["LO-0924-H", "Cá chẽm", 0, false, 70, 22, 110000, 3_080_000, 180_000, 1, 0, 0, 0, 0, 0, 0],
  ["LO-0924-I", "Mực nang", 0, false, 35, 8, 190000, 1_840_000, 100_000, 0, 0, 0, 0, 0, 0, 0],
  ["LO-0924-K", "Cá hồng", 0, false, 45, 14, 120000, 2_100_000, 95_000, 0, 0, 0, 0, 0, 0, 0],
  ["LO-0924-L", "Sò điệp", 0, false, 20, 3, 160000, 540_000, 60_000, 0, 0, 0, 0, 0, 0, 0],
  ["LO-0924-M", "Cá đuối", 0, false, 28, 5, 70000, 400_000, 40_000, 0, 0, 0, 0, 0, 0, 0],
  ["LO-0824-A", "Cá thu nguyên con", 1, true, 100, 100, 90000, 12_000_000, 380_000, 3, 0, 0, 0, 0, 0, 0],
  ["LO-0824-B", "Cá ngừ đại dương", 1, true, 90, 88, 125000, 13_200_000, 340_000, 1, 0, 0, 0, 0, 0, 0],
  ["LO-0824-C", "Mực ống tươi", 1, true, 55, 55, 175000, 11_000_000, 200_000, 0, 0, 0, 0, 0, 0, 0],
  ["LO-0824-D", "Tôm sú size 30", 1, true, 40, 40, 240000, 11_200_000, 260_000, 0, 0, 0, 0, 0, 0, 0],
  ["LO-0824-E", "Cá bớp phi lê", 1, true, 60, 52, 135000, 8_320_000, 120_000, 0, 0, 5, 0, 0, 0, 0],
  ["LO-0824-F", "Ghẹ xanh", 1, true, 30, 30, 205000, 7_500_000, 150_000, 0, 0, 0, 0, 0, 0, 0],
  ["LO-0824-G", "Cá mú đỏ", 1, true, 20, 11, 310000, 4_620_000, 90_000, 0, 2, 0, 0, 0, 0, 0],
  ["LO-0824-H", "Cá chẽm", 1, true, 75, 60, 105000, 5_400_000, 210_000, 2, 0, 0, 0, 0, 0, 0], // lỗ
  ["LO-0824-I", "Cá hồng", 1, true, 50, 30, 115000, 3_000_000, 100_000, 0, 0, 0, 0, 0, 0, 0], // lỗ
  ["LO-0824-K", "Mực nang", 1, false, 33, 10, 185000, 2_300_000, 90_000, 0, 0, 0, 0, 0, 0, 0],
  ["LO-0824-L", "Sò điệp", 1, true, 18, 18, 150000, 3_960_000, 70_000, 0, 0, 0, 0, 0, 0, 0],
  ["LO-0824-M", "Cá đuối", 1, true, 25, 20, 65000, 1_600_000, 40_000, 0, 0, 0, 0, 0, 0, 0],
];

type Seeded = { ago: number; row: BatchReportRow };

function batchRows(): Seeded[] {
  return BATCH_SEEDS.map(([code, item, ago, closed, received, sold, rate, revenue, allocated, shrink, damage, expired, returned, refund, reversedQty, reversedRevenue], index) => {
    const purchase = received * rate;
    const landed = Math.round(rate + allocated / received);
    const d = (n: number) => String(Math.round(n * 100) / 100);
    const totalCost = purchase + allocated - refund;
    const net = revenue - reversedRevenue;
    const row: BatchReportRow = {
      id: index + 1,
      batch_id: code,
      provisional: !closed,
      item_name: item,
      status: closed ? "CLOSED" : sold >= received ? "SOLD_OUT" : "SELLING",
      status_label: closed ? "Đã chốt" : sold >= received ? "Hết hàng" : "Đang bán",
      qty_received: d(received),
      qty_sold: d(sold - reversedQty),
      landed_unit_cost: `${landed}.00`,
      revenue: `${net}.00`,
      reversed_qty: d(reversedQty),
      reversed_revenue: `${reversedRevenue}.00`,
      purchase_cost: `${purchase}.00`,
      allocated_cost: `${allocated}.00`,
      shrinkage_qty: d(shrink),
      shrinkage_cost: `${Math.round(shrink * landed)}.00`,
      damage_qty: d(damage),
      damage_cost: `${Math.round(damage * landed)}.00`,
      expired_qty: d(expired),
      expired_cost: `${Math.round(expired * landed)}.00`,
      supplier_return_qty: d(returned),
      supplier_refund_amount: `${refund}.00`,
      total_cost: `${totalCost}.00`,
      profit: `${net - totalCost}.00`,
    };
    // `ago` (tháng phát sinh) chỉ để lọc, không nằm trong response.
    return { ago, row };
  });
}

/**
 * BE thật trả tiền và kg của hai endpoint báo cáo là JSON number (DRF đổi Decimal thành float), không phải chuỗi.
 * Mock đổi mọi giá trị chuỗi dạng số sang number ở ranh giới response để e2e chạy đúng shape thật (TL12-FE-H1).
 */
function asWire<T extends object>(row: T): Record<string, unknown> {
  return Object.fromEntries(Object.entries(row).map(([k, v]) => [k, typeof v === "string" && /^-?\d+(\.\d+)?$/.test(v) ? Number(v) : v]));
}

let cache: Seeded[] | null = null;
const rows = () => (cache ??= batchRows());

export function mockPeriodReport(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!me.can_view_profit) return FORBIDDEN;
  if (mode === "fail") return SERVER_ERROR;
  const q = params(req.path);
  const year = Number(q.get("year"));
  const month = Number(q.get("month"));
  if (!Number.isInteger(year) || !Number.isInteger(month) || month < 1 || month > 12) return bad("Cần tham số year & month.");
  return { status: 200, body: asWire(periodOf(year, month)) };
}

export function mockBatchReport(req: MockRequest): MockResponse {
  const me = mockRequireUser(req);
  if (!me) return MOCK_UNAUTHORIZED;
  if (!me.can_view_profit) return FORBIDDEN;
  if (mode === "fail") return SERVER_ERROR;
  const q = params(req.path);
  let list = rows();
  const month = q.get("month");
  if (month) {
    if (!/^\d{4}-\d{2}$/.test(month)) return bad("Tham số month phải có dạng YYYY-MM.");
    const [y, m] = month.split("-").map(Number);
    const ago = monthsAgo(y, m);
    list = list.filter((r) => r.ago === ago);
  }
  const state = q.get("state");
  if (state) {
    if (state !== "closed" && state !== "provisional") return bad("Tham số state chỉ nhận closed hoặc provisional.");
    list = list.filter((r) => (state === "closed" ? !r.row.provisional : r.row.provisional));
  }
  const page = Math.max(1, Number(q.get("page")) || 1);
  const start = (page - 1) * PAGE_SIZE;
  return {
    status: 200,
    body: {
      count: list.length,
      next: start + PAGE_SIZE < list.length ? `?page=${page + 1}` : null,
      previous: page > 1 ? `?page=${page - 1}` : null,
      results: list.slice(start, start + PAGE_SIZE).map((r) => {
        // BE không trả khoá số `id` (FE tự gán).
        const { id: _id, ...wire } = r.row;
        return asWire(wire);
      }),
    },
  };
}

if (process.env.NEXT_PUBLIC_USE_MOCK === "1" && typeof window !== "undefined") {
  const w = window as unknown as { __caveMock?: Record<string, unknown> };
  w.__caveMock = {
    ...(w.__caveMock || {}),
    reports: (m: Mode) => {
      mode = m;
      return `Báo cáo lãi lỗ (mock): chế độ ${m}`;
    },
  };
}

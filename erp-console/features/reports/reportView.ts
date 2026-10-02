// Logic hiển thị của Báo cáo lãi lỗ (ED-32): hàm thuần, có test. Tiền cộng trừ qua ./decimal.ts (không số thực).
import { vnd } from "@/shared/lib/format";
import { absDecimal, addDecimal, parseDecimal, ratioOf, signOf, subDecimal } from "./decimal";

const ZERO = BigInt(0);
import type { BatchReportRow, PeriodReport } from "./types";

/** Tiền có dấu: âm hiện "−1.250.000 đ" (dấu trừ thật), dương và 0 hiện như `vnd`. */
export function signedVnd(value: string | null | undefined): string {
  if (signOf(value) === -1) return `−${vnd(absDecimal(value as string))}`;
  return vnd(value);
}

/** "pos" lãi · "neg" lỗ · "zero" hoà vốn · "none" thiếu số. Dùng để tô màu và đọc cho trình đọc màn hình. */
export function profitTone(value: string | null | undefined): "pos" | "neg" | "zero" | "none" {
  const s = signOf(value);
  return s === null ? "none" : s < 0 ? "neg" : s > 0 ? "pos" : "zero";
}

/** Kỳ không có giao dịch nào: không hoá đơn, không hoàn tiền, mọi số tiền bằng 0 (ED-32-AC2: hiện trạng thái trống, không số 0 giả). */
export function periodIsEmpty(p: PeriodReport): boolean {
  if (p.invoice_count > 0 || p.refund_count > 0) return false;
  return [p.revenue, p.cogs, p.credit_notes, p.cogs_reversed, p.refunds, p.profit].every((v) => signOf(v) === 0);
}

export type BreakdownRow = {
  key: string;
  label: string;
  /** Số hiển thị có dấu (trừ là âm). */
  amount: string;
  /** 0..1, độ dài thanh so với dòng lớn nhất. */
  share: number;
  kind: "plus" | "minus" | "total";
};

/**
 * "Cấu thành lãi" của kỳ. BE trả `revenue` đã trừ chứng từ đảo và `cogs` đã trừ phần đảo, nên dựng lại số gộp:
 * doanh thu hoá đơn = revenue + credit_notes; giá vốn hàng bán = cogs + cogs_reversed.
 * Cộng các dòng (không tính dòng "Lãi/lỗ kỳ") ra đúng `profit`.
 */
export function profitBreakdown(p: PeriodReport): BreakdownRow[] {
  const grossRevenue = addDecimal(p.revenue, p.credit_notes) ?? p.revenue;
  const grossCogs = addDecimal(p.cogs, p.cogs_reversed) ?? p.cogs;
  const neg = (v: string) => subDecimal("0", v) ?? v;
  const lines: { key: string; label: string; amount: string; kind: BreakdownRow["kind"] }[] = [
    { key: "revenue", label: "Doanh thu hoá đơn", amount: grossRevenue, kind: "plus" },
    { key: "credit_notes", label: "Trừ doanh thu đơn huỷ", amount: neg(p.credit_notes), kind: "minus" },
    { key: "cogs", label: "Giá vốn hàng bán", amount: neg(grossCogs), kind: "minus" },
    { key: "cogs_reversed", label: "Giá vốn đảo lại", amount: p.cogs_reversed, kind: "plus" },
    { key: "refunds", label: "Hoàn tiền", amount: neg(p.refunds), kind: "minus" },
    { key: "profit", label: "Lãi/lỗ kỳ", amount: p.profit, kind: "total" },
  ];
  // Thanh dài nhất = dòng có |số| lớn nhất (thường là doanh thu hoá đơn).
  const scale = lines.reduce((max, l) => ((parseDecimal(absDecimal(l.amount)) ?? ZERO) > (parseDecimal(max) ?? ZERO) ? absDecimal(l.amount) : max), "0");
  return lines.map((l) => ({ ...l, share: ratioOf(l.amount, scale) }));
}

/** Tháng đang chọn "2026-09" → {year, month}. */
export function parseMonthKey(key: string): { year: number; month: number } {
  const [year, month] = key.split("-").map(Number);
  return { year, month };
}

/** Tháng liền trước của "2026-01" là "2025-12". */
export function previousMonthKey(key: string): string {
  const { year, month } = parseMonthKey(key);
  const idx = year * 12 + (month - 1) - 1;
  return `${Math.floor(idx / 12)}-${String((idx % 12) + 1).padStart(2, "0")}`;
}

/** 12 tháng gần nhất tính từ ngày `today` (YYYY-MM-DD, giờ VN), mới nhất trước. Không có "Mọi tháng": báo cáo luôn theo một tháng. */
export function reportMonthOptions(today: string, n = 12): { value: string; label: string }[] {
  const [y, m] = today.split("-").map(Number);
  return Array.from({ length: n }, (_, i) => {
    const idx = y * 12 + (m - 1) - i;
    const year = Math.floor(idx / 12);
    const month = (idx % 12) + 1;
    return { value: `${year}-${String(month).padStart(2, "0")}`, label: `Tháng ${month}/${year}` };
  });
}

/** Nhãn "Tháng 9/2026" từ khoá "2026-09". */
export function monthLabel(key: string): string {
  const { year, month } = parseMonthKey(key);
  return `Tháng ${month}/${year}`;
}

export type DetailLine = { key: string; label: string; value: string; kind?: "total" | "note"; locked?: boolean };

/**
 * Chi tiết một lô. Hao hụt, hàng hỏng, quá hạn chỉ là số tiền mất để THAM KHẢO: BE đã tính chúng trong giá mua
 * (không cộng vào tổng chi phí), nên tách thành nhóm riêng, không xếp lẫn với các khoản cấu thành lãi/lỗ.
 */
export function batchDetail(row: BatchReportRow, kgText: (v: string) => string): { composition: DetailLine[]; reference: DetailLine[] } {
  const composition: DetailLine[] = [
    { key: "received", label: "Đã nhập", value: kgText(row.qty_received) },
    { key: "purchase", label: "Giá mua", value: vnd(row.purchase_cost), locked: true },
    { key: "allocated", label: "Chi phí phân bổ", value: vnd(row.allocated_cost), locked: true },
    { key: "supplier_refund", label: "Tiền nhà cung cấp hoàn", value: vnd(row.supplier_refund_amount), locked: true },
    { key: "total_cost", label: "Tổng chi phí", value: vnd(row.total_cost), kind: "total", locked: true },
    { key: "sold", label: "Đã bán", value: kgText(row.qty_sold) },
    { key: "revenue", label: "Doanh thu", value: vnd(row.revenue), locked: true },
    ...(signOf(row.reversed_revenue) === 0 ? [] : [{ key: "reversed", label: `Đã trừ doanh thu đơn huỷ (${kgText(row.reversed_qty)})`, value: vnd(row.reversed_revenue), locked: true }]),
    { key: "profit", label: "Lãi/lỗ", value: signedVnd(row.profit), kind: "total" as const, locked: true },
  ];
  const reference: DetailLine[] = [
    { key: "shrinkage", label: `Hao hụt kiểm kê (${kgText(row.shrinkage_qty)})`, value: vnd(row.shrinkage_cost), locked: true },
    { key: "damage", label: `Hàng hỏng, huỷ bỏ (${kgText(row.damage_qty)})`, value: vnd(row.damage_cost), locked: true },
    { key: "expired", label: `Quá hạn huỷ (${kgText(row.expired_qty)})`, value: vnd(row.expired_cost), locked: true },
    { key: "supplier_return", label: "Trả nhà cung cấp", value: kgText(row.supplier_return_qty) },
  ];
  return { composition, reference };
}

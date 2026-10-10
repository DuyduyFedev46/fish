/**
 * So giỏ trong trình duyệt với catalog hiện hành (SHOP-2-06): đổi giá, món hết, số lượng lẻ từ Shop cũ.
 * File thuần TypeScript, chỉ import lib/quantity (test bằng `scripts/test-cart-reconcile.mjs`).
 */
import { isValidQty, parseQtyRule, snapUp, type QtyRule } from "@/lib/quantity";

export type ReconcileEntry = { item_code: string; name: string; unit: "kg" | "combo"; price: string; qty: number };
export type ReconcileItem = {
  item_code: string;
  price: string;
  stock_level: "in" | "low" | "out";
  min_qty: string;
  qty_step: string;
  unit: "kg" | "combo";
};

export type ReconciledLine = {
  entry: ReconcileEntry;
  /** Số lượng đã làm tròn lên mức hợp lệ. */
  qty: number;
  qtyAdjusted: boolean;
  status: "ok" | "price-changed" | "out";
  /** Giá hiện hành (giá lúc thêm nếu chưa có catalog). */
  unitPrice: string;
  previousUnitPrice?: string;
  rule: QtyRule;
};

export type Reconciled = {
  lines: ReconciledLine[];
  adjustedCount: number;
  outCount: number;
  priceChangedCount: number;
  /** Tạm tính các món còn hàng theo giá hiện hành (số nguyên đồng). */
  subtotal: number;
};

/**
 * `catalog` null = chưa so được giá (đang tải hoặc lỗi): giữ giá cũ, chỉ chỉnh số lượng.
 * Món không còn trong catalog (ngưng bán, mất giá) coi như đã hết.
 */
export function reconcileCart(entries: ReconcileEntry[], catalog: ReconcileItem[] | null): Reconciled {
  const byCode = new Map((catalog ?? []).map((i) => [i.item_code, i]));
  let adjustedCount = 0;
  let outCount = 0;
  let priceChangedCount = 0;
  let subtotal = 0;

  const lines = entries.map((entry): ReconciledLine => {
    const item = byCode.get(entry.item_code);
    const rule = item ? parseQtyRule(item.min_qty, item.qty_step, item.unit) : parseQtyRule(1, undefined, entry.unit);
    const qty = isValidQty(entry.qty, rule) ? entry.qty : snapUp(entry.qty, rule);
    const qtyAdjusted = qty !== entry.qty;
    if (qtyAdjusted) adjustedCount += 1;

    let status: ReconciledLine["status"] = "ok";
    let unitPrice = entry.price;
    let previousUnitPrice: string | undefined;
    if (catalog) {
      if (!item || item.stock_level === "out") {
        status = "out";
      } else {
        unitPrice = item.price;
        if (Number(item.price) !== Number(entry.price)) {
          status = "price-changed";
          previousUnitPrice = entry.price;
        }
      }
    }
    if (status === "out") outCount += 1;
    else subtotal += Math.round((Number(unitPrice) || 0) * qty);
    if (status === "price-changed") priceChangedCount += 1;
    return { entry, qty, qtyAdjusted, status, unitPrice, previousUnitPrice, rule };
  });

  return { lines, adjustedCount, outCount, priceChangedCount, subtotal };
}

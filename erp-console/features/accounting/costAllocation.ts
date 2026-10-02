// Chia chi phí mua vào các lô (F1d, AC4). Hàm thuần: không React, không API.
// Chia theo số kg hoặc theo giá trị (kg x giá mua) theo tỷ lệ, làm tròn xuống đồng, phần dư đồng dồn vào lô cuối
// để tổng các phần luôn đúng bằng số tiền gốc. Chủ vẫn sửa tay từng lô; khi đó tổng có thể lệch và nút Lưu bị khoá.
import { vnd } from "@/shared/lib/format";
import type { CostTargetBatch } from "./types";

export type AllocationMethod = "BY_QTY" | "BY_VALUE";

function weightOf(b: CostTargetBatch, method: AllocationMethod): number {
  const qty = Number(b.qty);
  if (!Number.isFinite(qty) || qty <= 0) return 0;
  if (method === "BY_QTY") return qty;
  const rate = Number(b.rate);
  return Number.isFinite(rate) && rate > 0 ? qty * rate : 0;
}

/** Chia `total` đồng cho các lô theo `method`. Tổng trả về luôn bằng `total` (khi có ít nhất một lô có trọng số). */
export function splitCost(total: number, batches: CostTargetBatch[], method: AllocationMethod): number[] {
  if (batches.length === 0) return [];
  const weights = batches.map((b) => weightOf(b, method));
  const sum = weights.reduce((a, b) => a + b, 0);
  if (!Number.isFinite(total) || total <= 0) return batches.map(() => 0);
  if (sum <= 0) {
    // Không lô nào có trọng số (vd giá mua bằng 0): chia đều.
    const base = Math.floor(total / batches.length);
    return batches.map((_, i) => (i === batches.length - 1 ? total - base * (batches.length - 1) : base));
  }
  const parts = weights.map((w) => Math.floor((total * w) / sum));
  const used = parts.slice(0, -1).reduce((a, b) => a + b, 0);
  parts[parts.length - 1] = total - used;
  return parts;
}

export type AllocationCheck = {
  /** Tổng các phần đã chia. */
  allocated: number;
  /** total - allocated: dương = còn thiếu, âm = đang thừa. */
  difference: number;
  ok: boolean;
  message: string | null;
};

/** AC4: tổng tiền chia phải bằng tổng chi phí. Câu báo nói rõ số cần có và số lệch. */
export function checkAllocation(total: number | null, parts: (number | null)[]): AllocationCheck {
  const allocated = parts.reduce<number>((a, p) => a + (p ?? 0), 0);
  if (total === null || total <= 0) return { allocated, difference: 0, ok: false, message: null };
  const difference = total - allocated;
  if (difference === 0) return { allocated, difference, ok: true, message: null };
  const how = difference > 0 ? `còn thiếu ${vnd(difference)}` : `đang thừa ${vnd(-difference)}`;
  return { allocated, difference, ok: false, message: `Tổng tiền chia phải bằng ${vnd(total)}, ${how}.` };
}

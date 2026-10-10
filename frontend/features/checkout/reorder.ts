/**
 * "Mua lại" / "Đặt lại đơn này" (02b §6.5): dựng giỏ từ các dòng của đơn. Chỉ mã hàng, tên, đơn vị, số lượng và giá hiện tại
 * từ catalog; KHÔNG mang theo mã giảm giá. File thuần TypeScript, không import gì (test bằng scripts/test-order-state.mjs).
 */
export type ReorderLine = { item_code: string; name: string; unit: "kg" | "combo"; qty: string; amount: string };
export type ReorderCatalogItem = { item_code: string; name: string; unit: "kg" | "combo"; price: string; stock_level: "in" | "low" | "out" };
export type ReorderCartEntry = { item_code: string; name: string; unit: "kg" | "combo"; price: string; qty: number };

/**
 * Trả giỏ mới: món của đơn được ĐẶT đúng số lượng (không cộng dồn với giỏ cũ), món khác trong giỏ giữ nguyên.
 * Món không còn trong catalog hoặc đã hết thì bỏ qua (giỏ sẽ báo). Chưa có catalog (lỗi mạng) thì suy giá từ thành tiền / số lượng.
 */
export function mergeOrderIntoCart(
  prev: ReorderCartEntry[],
  lines: ReorderLine[],
  catalog: ReorderCatalogItem[] | null
): ReorderCartEntry[] {
  const byCode = new Map((catalog ?? []).map((i) => [i.item_code, i]));
  const incoming: ReorderCartEntry[] = [];
  for (const l of lines) {
    const qty = Number(l.qty);
    if (!Number.isFinite(qty) || qty <= 0) continue;
    const item = byCode.get(l.item_code);
    if (catalog && (!item || item.stock_level === "out")) continue;
    const price = item ? item.price : String(Math.round(Number(l.amount) / qty) || 0);
    incoming.push({ item_code: l.item_code, name: item?.name ?? l.name, unit: item?.unit ?? l.unit, price, qty });
  }
  const codes = new Set(incoming.map((i) => i.item_code));
  return [...prev.filter((e) => !codes.has(e.item_code)), ...incoming];
}

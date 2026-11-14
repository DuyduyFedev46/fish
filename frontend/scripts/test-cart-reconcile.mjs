#!/usr/bin/env node
// Test cho features/cart/reconcile.ts (so giỏ với catalog: đổi giá, món hết, số lượng lẻ). Cùng kiểu test-quantity.mjs.
//   node scripts/test-cart-reconcile.mjs
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const root = resolve(fileURLToPath(import.meta.url), "..", "..");
const tr = (f) =>
  ts.transpileModule(readFileSync(`${root}/${f}`, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
  }).outputText;
const b64 = (js) => `data:text/javascript;base64,${Buffer.from(js).toString("base64")}`;
const quantityUrl = b64(tr("lib/quantity.ts"));
const mod = await import(b64(tr("features/cart/reconcile.ts").replace('"@/lib/quantity"', `"${quantityUrl}"`)));
const textUrl = b64(tr("lib/text.ts"));
const view = await import(
  b64(
    tr("features/catalog/catalogView.ts")
      .replace('"@/lib/text"', `"${textUrl}"`)
  )
);
const text = await import(textUrl);

let n = 0;
let fail = 0;
function eq(name, got, want) {
  n++;
  const g = JSON.stringify(got);
  const w = JSON.stringify(want);
  if (g !== w) {
    fail++;
    console.log(`SAI  ${name}: được ${g}, cần ${w}`);
  }
}

const item = (code, price, level, unit = "kg") => ({
  item_code: code, price, stock_level: level, unit, min_qty: "1", qty_step: unit === "kg" ? "0.5" : "1",
  item_type: unit === "kg" ? "SIMPLE" : "BUNDLE", name: code, group: { slug: "ca", name: "Cá" },
});
const entry = (code, price, qty, unit = "kg") => ({ item_code: code, name: code, unit, price, qty });

// giá đổi
let r = mod.reconcileCart([entry("A", "265000", 1)], [item("A", "278000", "in")]);
eq("giá đổi: trạng thái", r.lines[0].status, "price-changed");
eq("giá đổi: giá cũ", r.lines[0].previousUnitPrice, "265000");
eq("giá đổi: tổng theo giá mới", r.subtotal, 278000);
// món hết không tính vào tổng
r = mod.reconcileCart([entry("A", "100000", 1), entry("B", "290000", 1)], [item("A", "100000", "in"), item("B", "290000", "out")]);
eq("hết: đếm", r.outCount, 1);
eq("hết: tổng chỉ món còn hàng", r.subtotal, 100000);
// món không còn trong catalog coi như hết
r = mod.reconcileCart([entry("Z", "1000", 1)], [item("A", "1", "in")]);
eq("mất khỏi catalog = hết", r.lines[0].status, "out");
// số lượng lẻ làm tròn lên
r = mod.reconcileCart([entry("A", "10000", 0.3), entry("B", "10000", 1.2), entry("C", "10000", 1.5)], [item("A", "10000", "in"), item("B", "10000", "in"), item("C", "10000", "in")]);
eq("0,3 -> 1", r.lines[0].qty, 1);
eq("1,2 -> 1,5", r.lines[1].qty, 1.5);
eq("1,5 giữ", r.lines[2].qty, 1.5);
eq("đếm chỉnh", r.adjustedCount, 2);
// combo nguyên
r = mod.reconcileCart([entry("K", "50000", 1.5, "combo")], [item("K", "50000", "in", "combo")]);
eq("combo 1,5 -> 2", r.lines[0].qty, 2);
// chưa có catalog: giữ giá, vẫn chỉnh số lượng theo mặc định 0,5 kg, không báo hết
r = mod.reconcileCart([entry("A", "10000", 0.3), entry("B", "10000", 0.5)], null);
eq("chưa có catalog: ok", r.lines[0].status, "ok");
eq("chưa có catalog: 0,3 -> 0,5", r.lines[0].qty, 0.5);
eq("chưa có catalog: 0,5 giữ 0,5", r.lines[1].qty, 0.5);
// catalog có min_qty = "0.5"
const item05 = (code, price, level) => ({ ...item(code, price, level), min_qty: "0.5" });
r = mod.reconcileCart([entry("A", "10000", 0.3), entry("B", "10000", 0.5)], [item05("A", "10000", "in"), item05("B", "10000", "in")]);
eq("catalog min_qty=0,5: 0,3 -> 0,5", r.lines[0].qty, 0.5);
eq("catalog min_qty=0,5: 0,5 giữ nguyên", r.lines[1].qty, 0.5);
eq("catalog min_qty=0,5: đếm chỉnh = 1", r.adjustedCount, 1);

// GUI-12: chỉ ghi số lượng đã chỉnh vào giỏ khi đã có catalog thật (loadState "ready")
const lazy = mod.reconcileCart([entry("A", "10000", 0.3), entry("B", "10000", 0.5)], null);
eq("GUI-12 chưa có catalog (loading/error): không ghi gì vào giỏ", mod.qtyFixesToPersist(lazy, false), null);
eq("GUI-12 0,5 kg luôn giữ 0,5 khi chưa có catalog", lazy.lines[1].qty, 0.5);
const real = mod.reconcileCart([entry("A", "10000", 0.3), entry("B", "10000", 0.5)], [item05("A", "10000", "in"), item05("B", "10000", "in")]);
eq("GUI-12 có catalog: ghi 0,3 -> 0,5", mod.qtyFixesToPersist(real, true), [["A", 0.5], ["B", 0.5]]);
const clean = mod.reconcileCart([entry("B", "10000", 0.5)], [item05("B", "10000", "in")]);
eq("GUI-12 có catalog, không số lẻ: không ghi", mod.qtyFixesToPersist(clean, true), null);
eq("GUI-12 combo chưa có catalog: tối thiểu 1", mod.reconcileCart([entry("K", "5", 1, "combo")], null).lines[0].qty, 1);

// catalogView
const cat = [item("A", "300", "out"), item("B", "200", "in"), item("C", "100", "low")];
cat[1].name = "Mực ống"; cat[2].name = "Tôm sú"; cat[0].name = "Cá bớp";
const f = (o) => view.filterAndSort(cat, { q: "", group: "", type: "", sort: "default", ...o }).map((i) => i.item_code);
eq("mặc định: hết xuống cuối", f({}), ["B", "C", "A"]);
eq("giá tăng, hết vẫn cuối", f({ sort: "price_asc" }), ["C", "B", "A"]);
eq("giá giảm, hết vẫn cuối", f({ sort: "price_desc" }), ["B", "C", "A"]);
eq("tìm không dấu", f({ q: "muc" }), ["B"]);
eq("tìm đ", text.foldVietnamese("Đông Lạnh"), "dong lanh");
eq("giống SĐT", text.looksLikePhone("0900000001"), true);
eq("từ khoá thường", text.looksLikePhone("cá thu 2"), false);

console.log(`test-cart-reconcile: ${n - fail}/${n} đạt, ${fail} sai`);
process.exit(fail ? 1 : 0);

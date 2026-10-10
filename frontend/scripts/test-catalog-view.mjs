#!/usr/bin/env node
// Test cho tìm kiếm và danh mục: lib/text.ts, features/catalog/{catalogView,recentSearches}.ts.
// SHOP-2-03 AC2 (món hết luôn cuối), SHOP-2-04 AC1, AC3, AC4 (không lưu chuỗi giống SĐT). Cùng kiểu test-cart-reconcile.mjs.
//   node scripts/test-catalog-view.mjs
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
const textUrl = b64(tr("lib/text.ts"));
const text = await import(textUrl);
const view = await import(b64(tr("features/catalog/catalogView.ts").replace('"@/lib/text"', `"${textUrl}"`)));
const recent = await import(b64(tr("features/catalog/recentSearches.ts").replace('"@/lib/text"', `"${textUrl}"`)));

let n = 0;
let fail = 0;
function eq(name, got, want) {
  n++;
  if (JSON.stringify(got) !== JSON.stringify(want)) {
    fail++;
    console.log(`SAI  ${name}: được ${JSON.stringify(got)}, cần ${JSON.stringify(want)}`);
  }
}

const item = (code, name, price, level) => ({
  item_code: code, name, price, stock_level: level, unit: "kg", item_type: "SIMPLE", min_qty: "1", qty_step: "0.5",
  group: { slug: "ca", name: "Cá" },
});
const cat = [item("A", "Cá bớp", "300000", "out"), item("B", "Mực ống làm sạch", "200000", "in"), item("C", "Tôm sú", "100000", "low"), item("D", "Hoàng đế", "900000", "out")];
const f = (o) => view.filterAndSort(cat, { q: "", group: "", type: "", sort: "default", ...o }).map((i) => i.item_code);

// 2-03 AC2: món hết luôn cuối, dù sắp xếp kiểu nào
eq("mặc định: hết cuối", f({}), ["B", "C", "A", "D"]);
eq("giá tăng: hết cuối", f({ sort: "price_asc" }), ["C", "B", "A", "D"]);
eq("giá giảm: hết cuối", f({ sort: "price_desc" }), ["B", "C", "D", "A"]);
// 2-04 AC1: tìm không dấu
eq("muc khớp Mực ống", f({ q: "muc" }), ["B"]);
eq("hoang de khớp Hoàng đế", f({ q: "hoang de" }), ["D"]);
eq("fold đ", text.foldVietnamese("Đông Lạnh"), "dong lanh");
// 2-04 AC4: không lưu chuỗi giống SĐT
eq("SĐT liền", text.looksLikePhone("0900000001"), true);
eq("SĐT có khoảng trắng", text.looksLikePhone("090 000 0001"), true);
eq("SĐT +84", text.looksLikePhone("+84 900 000 001"), true);
eq("từ khoá thường", text.looksLikePhone("cá thu 2"), false);
eq("addRecent bỏ SĐT", recent.addRecent(["mực"], "0900000001"), ["mực"]);
eq("addRecent bỏ SĐT có cách", recent.addRecent(["mực"], "090 000 0001"), ["mực"]);
eq("addRecent bỏ chuỗi quá dài", recent.addRecent(["mực"], "x".repeat(41)), ["mực"]);
eq("addRecent nhận 40 ký tự", recent.addRecent([], "x".repeat(40)).length, 1);
// 2-04 AC3: tối đa 5, mới nhất đầu, bỏ trùng
let list = [];
for (const t of ["mực", "tôm", "cá thu", "hến", "ghẹ", "combo"]) list = recent.addRecent(list, t);
eq("tối đa 5, mới nhất đầu", list, ["combo", "ghẹ", "hến", "cá thu", "tôm"]);
eq("trùng không dấu đưa lên đầu", recent.addRecent(list, "HEN"), ["HEN", "combo", "ghẹ", "cá thu", "tôm"]);
// parseRecent
eq("parse hỏng", recent.parseRecent("{không phải json"), []);
eq("parse không phải mảng", recent.parseRecent('{"a":1}'), []);
eq("parse rỗng", recent.parseRecent(null), []);
eq("parse bỏ SĐT, số, chuỗi rỗng", recent.parseRecent(JSON.stringify(["mực", "0900000001", 5, "", "tôm"])), ["mực", "tôm"]);
eq("parse giữ tối đa 5", recent.parseRecent(JSON.stringify(["a", "b", "c", "d", "e", "f", "g"])).length, 5);

console.log(`test-catalog-view: ${n - fail}/${n} đạt, ${fail} sai`);
process.exit(fail ? 1 : 0);

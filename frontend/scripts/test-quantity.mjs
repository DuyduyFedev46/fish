#!/usr/bin/env node
// Unit test cho lib/quantity.ts (luật số lượng BR-BH-22, G4). Không thêm thư viện: dùng `typescript`
// đã có để chuyển .ts -> JS rồi nạp bằng data: URL (giống test-format.mjs).
//
//   node scripts/test-quantity.mjs [đường-dẫn-quantity.ts]
//
// Thoát 0 nếu mọi ca đạt, 1 nếu có ca sai.

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const root = resolve(fileURLToPath(import.meta.url), "..", "..");
const target = resolve(process.argv[2] || `${root}/lib/quantity.ts`);

const js = ts.transpileModule(readFileSync(target, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
}).outputText;
const mod = await import(`data:text/javascript;base64,${Buffer.from(js).toString("base64")}`);

let n = 0;
let fail = 0;
function eq(name, fn, want) {
  n++;
  let got;
  try {
    got = typeof fn === "function" ? fn() : fn;
  } catch (e) {
    got = `THROW ${e && e.message}`;
  }
  if (JSON.stringify(got) !== JSON.stringify(want)) {
    fail++;
    console.log(`SAI  ${name}: muốn ${JSON.stringify(want)}, được ${JSON.stringify(got)}`);
  }
}

const kg = mod.parseQtyRule("1", "0.5", "kg");
const combo = mod.parseQtyRule("1", "1", "combo");

// --- đọc luật từ API ---
eq("parseQtyRule kg", kg, { minQty: 1, step: 0.5 });
eq("parseQtyRule combo", combo, { minQty: 1, step: 1 });
eq("parseQtyRule thiếu -> mặc định kg", mod.parseQtyRule(undefined, null), { minQty: 1, step: 0.5 });
eq("parseQtyRule thiếu -> mặc định combo", mod.parseQtyRule("", "", "combo"), { minQty: 1, step: 1 });
eq("parseQtyRule rác", mod.parseQtyRule("abc", "-1"), { minQty: 1, step: 0.5 });

// --- G4: số lượng hợp lệ ---
for (const q of [1, 1.5, 2, 2.5, 10])
  eq(`isValidQty kg ${q}`, () => mod.isValidQty(q, kg), true);
for (const q of [0, 0.5, 0.3, 1.25, 1.1, -1, NaN])
  eq(`isValidQty kg ${q} không hợp lệ`, () => mod.isValidQty(q, kg), false);
for (const q of [1, 2, 3]) eq(`isValidQty combo ${q}`, () => mod.isValidQty(q, combo), true);
for (const q of [0, 1.5, 0.5, 2.5]) eq(`isValidQty combo ${q} không hợp lệ`, () => mod.isValidQty(q, combo), false);

// --- tăng / giảm theo bước ---
eq("stepUp 1 -> 1,5", () => mod.stepUp(1, kg), 1.5);
eq("stepUp 1,5 -> 2", () => mod.stepUp(1.5, kg), 2);
eq("stepUp combo 1 -> 2", () => mod.stepUp(1, combo), 2);
eq("stepDown 2 -> 1,5", () => mod.stepDown(2, kg), 1.5);
eq("stepDown 1,5 -> 1", () => mod.stepDown(1.5, kg), 1);
eq("stepDown 1 kg -> null (mở hộp thoại bỏ món, không về 0,5)", () => mod.stepDown(1, kg), null);
eq("stepDown 1 combo -> null", () => mod.stepDown(1, combo), null);
eq("stepDown combo 3 -> 2", () => mod.stepDown(3, combo), 2);
// 0,1 + 0,2 kiểu số thực không được lệch
eq("stepUp không sinh số lẻ thừa", () => mod.stepUp(0.3, { minQty: 0.1, step: 0.1 }), 0.4);

// --- làm tròn lên (giỏ cũ có số lẻ) ---
eq("snapUp 0,3 -> 1", () => mod.snapUp(0.3, kg), 1);
eq("snapUp 1,1 -> 1,5", () => mod.snapUp(1.1, kg), 1.5);
eq("snapUp 1,5 giữ nguyên", () => mod.snapUp(1.5, kg), 1.5);
eq("snapUp 2,01 -> 2,5", () => mod.snapUp(2.01, kg), 2.5);
eq("snapUp combo 1,2 -> 2", () => mod.snapUp(1.2, combo), 2);
eq("snapUp NaN -> tối thiểu", () => mod.snapUp(NaN, kg), 1);

// --- chuỗi gửi máy chủ / hiển thị ---
eq("qtyToApiString 1", () => mod.qtyToApiString(1), "1");
eq("qtyToApiString 1,5", () => mod.qtyToApiString(1.5), "1.5");
eq("qtyToApiString 2.0", () => mod.qtyToApiString(2.0), "2");
eq("qtyToApiString combo 3", () => mod.qtyToApiString(3), "3");
eq("formatQty 1,5", () => mod.formatQty(1.5), "1,5");
eq("formatQty 2", () => mod.formatQty(2), "2");

console.log(`\ntest-quantity: ${n - fail}/${n} đạt, ${fail} sai (${target.replace(root + "/", "")})`);
process.exit(fail ? 1 : 0);

#!/usr/bin/env node
// Test cho features/checkout/orderLimitError.ts (ba mã lỗi giới hạn đơn).  node scripts/test-order-limit.mjs
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const root = resolve(fileURLToPath(import.meta.url), "..", "..");
const js = ts.transpileModule(readFileSync(`${root}/features/checkout/orderLimitError.ts`, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
}).outputText;
const m = await import(`data:text/javascript;base64,${Buffer.from(js).toString("base64")}`);

let n = 0;
let fail = 0;
function eq(name, got, want) {
  n += 1;
  if (got !== want) {
    fail += 1;
    console.error(`FAIL ${name}: got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`);
  }
}

for (const code of ["ORDER_LINE_TOO_LARGE", "ORDER_TOO_LARGE", "TOO_MANY_OPEN_ORDERS"]) {
  eq(`${code} dùng detail máy chủ`, m.orderLimitMessage(code, "Câu từ máy chủ."), "Câu từ máy chủ.");
  eq(`${code} detail rỗng -> dự phòng`, m.orderLimitMessage(code, "  "), m.ORDER_LIMIT_FALLBACK);
  eq(`${code} không detail -> dự phòng`, m.orderLimitMessage(code, undefined), m.ORDER_LIMIT_FALLBACK);
}
eq("mã khác -> null", m.orderLimitMessage("INVALID_QTY", "x"), null);
eq("không mã -> null", m.orderLimitMessage(undefined, "x"), null);
eq("câu dự phòng", m.ORDER_LIMIT_FALLBACK, "Đơn vượt giới hạn đặt online, vui lòng gọi hotline để được hỗ trợ");

console.log(`${n - fail}/${n} đạt`);
process.exit(fail ? 1 : 0);

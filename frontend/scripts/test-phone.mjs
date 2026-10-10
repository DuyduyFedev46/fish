#!/usr/bin/env node
// Unit test cho lib/phone.ts (hotline hợp lệ). Dùng `typescript` đã có, giống test-format.mjs.
//   node scripts/test-phone.mjs
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const root = resolve(fileURLToPath(import.meta.url), "..", "..");
const target = resolve(process.argv[2] || `${root}/lib/phone.ts`);
const js = ts.transpileModule(readFileSync(target, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
}).outputText;
const mod = await import(`data:text/javascript;base64,${Buffer.from(js).toString("base64")}`);

let n = 0;
let fail = 0;
function eq(name, got, want) {
  n++;
  if (got !== want) {
    fail++;
    console.log(`SAI  ${name}: muốn ${JSON.stringify(want)}, được ${JSON.stringify(got)}`);
  }
}

eq("số thường", mod.validHotline("0900000000"), "0900000000");
eq("có khoảng trắng", mod.validHotline("0900 000 000"), "0900 000 000");
eq("có +84", mod.validHotline("+84 900 000 000"), "+84 900 000 000");
eq("1900 xxxx giữ chỗ", mod.validHotline("1900 xxxx"), undefined);
eq("[hotline]", mod.validHotline("[hotline]"), undefined);
eq("có chữ X hoa", mod.validHotline("1900 XXXX"), undefined);
eq("quá ngắn", mod.validHotline("1900"), undefined);
eq("quá dài", mod.validHotline("1234567890123456"), undefined);
eq("dấu + giữa chuỗi", mod.validHotline("090+0000000"), undefined);
eq("có chữ cái lẫn số", mod.validHotline("0900abc000"), undefined);
eq("rỗng", mod.validHotline(""), undefined);
eq("null", mod.validHotline(null), undefined);
eq("undefined", mod.validHotline(undefined), undefined);
eq("cắt khoảng trắng đầu cuối", mod.validHotline("  0900000000 "), "0900000000");
eq("pickHotline bỏ giữ chỗ lấy số sau", mod.pickHotline("1900 xxxx", "0900000000"), "0900000000");
eq("pickHotline ưu tiên số đầu hợp lệ", mod.pickHotline("0911111111", "0900000000"), "0911111111");
eq("pickHotline không có số hợp lệ", mod.pickHotline(null, "1900 xxxx"), undefined);

console.log(`\ntest-phone: ${n - fail}/${n} đạt, ${fail} sai`);
process.exit(fail ? 1 : 0);

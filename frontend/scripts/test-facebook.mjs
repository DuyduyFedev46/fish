#!/usr/bin/env node
// Unit test cho lib/facebook.ts và zaloNumberOf trong lib/phone.ts (FB-01). node scripts/test-facebook.mjs
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const root = resolve(fileURLToPath(import.meta.url), "..", "..");
async function load(file) {
  const js = ts.transpileModule(readFileSync(`${root}/${file}`, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
  }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(js).toString("base64")}`);
}
const fb = await load("lib/facebook.ts");
const phone = await load("lib/phone.ts");

let n = 0;
let fail = 0;
function eq(name, got, want) {
  n++;
  if (got !== want) {
    fail++;
    console.log(`SAI  ${name}: muốn ${JSON.stringify(want)}, được ${JSON.stringify(got)}`);
  }
}

for (const u of [
  "https://facebook.com/cave",
  "https://www.facebook.com/profile.php?id=1",
  "https://m.facebook.com/cave",
  "https://fb.com/cave",
  "https://fb.me/cave",
  "  https://www.facebook.com/cave  ",
])
  eq(`hợp lệ ${u}`, fb.facebookHrefOf(u), u.trim());
for (const u of [
  "[Link fanpage Facebook]",
  "javascript:alert(1)",
  "http://facebook.com/cave",
  "https://evil.example/facebook.com",
  "https://facebook.com.evil.example/x",
  "https://user@facebook.com/x",
  "https://notfacebook.com/x",
  "//facebook.com/x",
  "",
  "   ",
  null,
  undefined,
])
  eq(`không hợp lệ ${u}`, fb.facebookHrefOf(u), undefined);
eq("chữ giữ chỗ", fb.facebookPlainTextOf(" [Link fanpage Facebook] "), "[Link fanpage Facebook]");
eq("javascript là chữ", fb.facebookPlainTextOf("javascript:alert(1)"), "javascript:alert(1)");
eq("link thật không là chữ", fb.facebookPlainTextOf("https://fb.me/x"), undefined);
eq("rỗng ẩn", fb.facebookPlainTextOf(""), undefined);
eq("null ẩn", fb.facebookPlainTextOf(null), undefined);

eq("zalo số", phone.zaloNumberOf("0373850884"), "0373850884");
eq("zalo link", phone.zaloNumberOf("https://zalo.me/0373850884"), "0373850884");
eq("zalo chữ giữ chỗ", phone.zaloNumberOf("[số Zalo]"), undefined);
eq("zalo null", phone.zaloNumberOf(null), undefined);

console.log(fail === 0 ? `OK ${n} ca` : `${fail}/${n} ca SAI`);
process.exit(fail === 0 ? 0 : 1);

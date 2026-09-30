#!/usr/bin/env node
// Unit test cho features/content/safeHref.ts (SR-23 F2). Không thêm thư viện: dùng `typescript`
// đã có trong devDependencies để chuyển file .ts sang JS rồi nạp bằng data: URL.
//
//   node scripts/test-safe-href.mjs [đường-dẫn-safeHref.ts]
//
// Không đối số -> kiểm file thật trong repo. Có đối số -> kiểm bản khác (dùng để chứng minh
// test ĐỎ trên bản cũ). Thoát 0 nếu mọi ca đạt, 1 nếu có ca sai.

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const root = resolve(fileURLToPath(import.meta.url), "..", "..");
const target = resolve(process.argv[2] || `${root}/features/content/safeHref.ts`);

const js = ts.transpileModule(readFileSync(target, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
}).outputText;
const mod = await import(`data:text/javascript;base64,${Buffer.from(js).toString("base64")}`);
const { isSafeHref, isExternalLink } = mod;

// [mô tả, chuỗi vào, kết quả mong đợi của isSafeHref]
const LONG_OK = "/bai-viet?slug=" + "a".repeat(1900);
const TOO_LONG = "https://caveve.vn/" + "a".repeat(2000);

const CASES = [
  // --- hợp lệ ---
  ["https", "https://caveve.vn/shop", true],
  ["http", "http://example.com/item", true],
  ["mailto", "mailto:hotro@caveve.vn", true],
  ["tel", "tel:0900000000", true],
  ["đường dẫn nội bộ", "/shop", true],
  ["đường dẫn nội bộ có query", "/bai-viet?slug=ca-thu", true],
  ["neo trong trang", "#muc-2", true],
  ["https viết hoa + khoảng trắng đầu/cuối (được trim)", "  HTTPS://caveve.vn  ", true],
  ["nội bộ dưới 2000 ký tự", LONG_OK, true],
  // --- nguy hiểm ---
  ["javascript:", "javascript:alert(1)", false],
  ["JAVASCRIPT: viết hoa", "JAVASCRIPT:alert(1)", false],
  ["JaVaScRiPt: xen kẽ hoa thường", "jAvAsCrIpT:alert(document.cookie)", false],
  ["vbscript: có khoảng trắng đầu", " vbscript:msgbox(1)", false],
  ["data:", "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==", false],
  ["protocol-relative //", "//evil.example/phish", false],
  ["/\\ (gạch chéo rồi gạch ngược)", "/\\evil.example", false],
  ["\\\\ gạch ngược ở đầu", "\\\\evil.example", false],
  ["\\host gạch ngược đơn ở đầu", "\\evil.example", false],
  ["tab xen giữa giao thức", "java\tscript:alert(1)", false],
  ["xuống dòng xen giữa giao thức", "java\nscript:alert(1)", false],
  ["ký tự NUL đầu chuỗi", "\u0000javascript:alert(1)", false],
  ["ký tự điều khiển 0x01 đầu chuỗi", "\u0001javascript:alert(1)", false],
  ["khoảng trắng bên trong URL", "https://caveve.vn/a b", false],
  ["ký tự điều khiển C1 (0x85)", "https://caveve.vn/\u0085x", false],
  ["file:", "file:///etc/passwd", false],
  ["ftp:", "ftp://example.com/a", false],
  ["blob:", "blob:https://caveve.vn/abc", false],
  ["không có giao thức, không có gạch chéo", "abc", false],
  ["quá 2000 ký tự", TOO_LONG, false],
  ["chuỗi rỗng", "", false],
  ["chỉ khoảng trắng", "   ", false],
  ["undefined", undefined, false],
  ["null", null, false],
  ["số (không phải chuỗi)", 123, false],
];

let fail = 0;
let n = 0;
for (const [label, input, expected] of CASES) {
  n += 1;
  let got;
  try {
    got = isSafeHref(input);
  } catch (e) {
    got = `NÉM LỖI: ${e && e.message}`;
  }
  const ok = got === expected;
  if (!ok) fail += 1;
  console.log(`${ok ? "PASS" : "FAIL"}  isSafeHref  ${label}  ->  ${got}  (mong đợi ${expected})`);
}

// isExternalLink: chỉ http/https mới mở tab mới kèm rel.
for (const [label, input, expected] of [
  ["https là link ngoài", "https://caveve.vn/x", true],
  ["HTTP viết hoa là link ngoài", "HTTP://caveve.vn/x", true],
  ["đường dẫn nội bộ không phải link ngoài", "/shop", false],
  ["mailto không mở tab mới", "mailto:a@b.vn", false],
  ["tel không mở tab mới", "tel:0900000000", false],
  ["undefined", undefined, false],
]) {
  n += 1;
  const got = isExternalLink(input);
  const ok = got === expected;
  if (!ok) fail += 1;
  console.log(`${ok ? "PASS" : "FAIL"}  isExternalLink  ${label}  ->  ${got}  (mong đợi ${expected})`);
}

console.log(`\ntest-safe-href: ${n - fail}/${n} đạt, ${fail} sai (${target.replace(root + "/", "")})`);
process.exit(fail ? 1 : 0);

#!/usr/bin/env node
// Unit test cho lib/format.ts (P8 Lô 8, SR-25). Không thêm thư viện: dùng `typescript` đã có để
// chuyển .ts -> JS rồi nạp bằng data: URL (giống test-safe-href.mjs).
//
//   node scripts/test-format.mjs [đường-dẫn-format.ts]
//   TZ=America/New_York node scripts/test-format.mjs
//   TZ=UTC node scripts/test-format.mjs
//
// Không đối số -> kiểm file thật. Có đối số -> kiểm bản khác (chứng minh ĐỎ trên bản cũ).
// Thoát 0 nếu mọi ca đạt, 1 nếu có ca sai.

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const root = resolve(fileURLToPath(import.meta.url), "..", "..");
const target = resolve(process.argv[2] || `${root}/lib/format.ts`);

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
  if (got !== want) {
    fail++;
    console.log(`SAI  ${name}: muốn ${JSON.stringify(want)}, được ${JSON.stringify(got)}`);
  }
}

// --- tiền (AC1, RA-01) ---
eq("formatVnd chuỗi Decimal API", () => mod.formatVnd("260000.00"), "260.000 ₫");
eq("formatVnd số nguyên", () => mod.formatVnd(260000), "260.000 ₫");
eq("formatVnd chuỗi nguyên", () => mod.formatVnd("65000"), "65.000 ₫");
eq("formatVnd làm tròn", () => mod.formatVnd("259999.6"), "260.000 ₫");
eq("formatVnd 0", () => mod.formatVnd(0), "0 ₫");
eq("formatVnd triệu", () => mod.formatVnd("1250000.00"), "1.250.000 ₫");
eq("formatVnd null", () => mod.formatVnd(null), "—");
eq("formatVnd undefined", () => mod.formatVnd(undefined), "—");
eq("formatVnd chuỗi rỗng", () => mod.formatVnd(""), "—");
eq("formatVnd chữ rác", () => mod.formatVnd("abc"), "—");
eq("formatVnd NaN", () => mod.formatVnd(NaN), "—");
eq("formatKg chuỗi", () => mod.formatKg("2.500"), "2,5 kg");
eq("formatKg rác", () => mod.formatKg("x"), "—");

// --- ngày giờ (AC2, AC4): mọi ca phải đúng dù TZ máy là gì ---
eq("formatDateTime UTC 17:30 ngày 30/09 -> 00:30 ngày 01/10 VN", () => mod.formatDateTime("2026-09-30T17:30:00Z"), "01/10 00:30");
eq("formatDateTime có offset -05:00", () => mod.formatDateTime("2026-09-30T12:30:00-05:00"), "01/10 00:30");
eq("formatDateTime giữa ngày", () => mod.formatDateTime("2026-09-30T03:05:00Z"), "30/09 10:05");
eq("formatDateTime nửa đêm VN không ra 24:", () => mod.formatDateTime("2026-09-30T17:00:00Z"), "01/10 00:00");
eq("formatDateTime rác", () => mod.formatDateTime("không phải ngày"), "—");
eq("formatDateTime null", () => mod.formatDateTime(null), "—");
eq("formatDate qua ngày mới VN", () => mod.formatDate("2026-12-31T20:00:00Z"), "01/01/2027");
eq("formatTime", () => mod.formatTime("2026-09-30T17:30:00Z"), "00:30");
eq("formatDateOnly", () => mod.formatDateOnly("2026-10-28"), "28/10/2026");
eq("formatDateOnly rác", () => mod.formatDateOnly("28/10"), "—");
eq("todayInVietnam 17:30Z = ngày hôm sau ở VN", () => mod.todayInVietnam(new Date("2026-09-30T17:30:00Z")), "2026-10-01");
eq("todayInVietnam 16:59Z còn trong ngày", () => mod.todayInVietnam(new Date("2026-09-30T16:59:00Z")), "2026-09-30");
eq("currentYearInVietnam 31/12 20:00Z = năm sau ở VN", () => mod.currentYearInVietnam(new Date("2026-12-31T20:00:00Z")), 2027);

console.log(`\ntest-format: ${n - fail}/${n} đạt, ${fail} sai (TZ=${process.env.TZ || "mặc định"}, ${target.replace(root + "/", "")})`);
process.exit(fail ? 1 : 0);

// SR-25 AC3: mọi định dạng ngày giờ đi qua shared/lib/format.ts (luôn Asia/Ho_Chi_Minh). Test quét mã nguồn để
// không ai quay lại `toLocale*String` theo giờ máy hoặc cắt chuỗi ISO (`slice(11, 16)`).
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = path.resolve(__dirname, "../..");
const DIRS = ["app", "features", "shared"];

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const p = path.join(dir, name);
    if (statSync(p).isDirectory()) walk(p, out);
    else if (/\.(ts|tsx)$/.test(name)) out.push(p);
  }
  return out;
}

const FILES = DIRS.flatMap((d) => walk(path.join(ROOT, d))).filter(
  (f) => !/\.test\.tsx?$/.test(f) && !f.endsWith(path.join("shared", "lib", "format.ts")),
);

const FORBIDDEN: [string, RegExp][] = [
  ["toLocaleDateString", /\.toLocaleDateString\(/],
  ["toLocaleTimeString", /\.toLocaleTimeString\(/],
  ["Intl.DateTimeFormat", /Intl\.DateTimeFormat/],
  ["Date#toLocaleString", /new Date\([^)]*\)\s*\.toLocaleString\(/],
  ["cắt giờ từ chuỗi ISO", /\.slice\(11, ?16\)/],
  ["ngày UTC làm 'hôm nay'", /toISOString\(\)\.slice\(0, ?10\)/],
  // L8-3: các đường vòng khác để lấy ngày giờ theo giờ máy.
  ["getHours/getMinutes/getSeconds/getDay", /\.get(Hours|Minutes|Seconds|Milliseconds|Day)\(/],
  ["getDate/getMonth/getFullYear", /\.get(Date|Month|FullYear)\(/],
  ["setHours/setDate/setMonth/setFullYear…", /\.set(Hours|Minutes|Seconds|Milliseconds|Date|Month|FullYear)\(/],
  ["toISOString().split/slice/substring/substr làm ngày", /toISOString\(\)\s*\.(split|slice|substring|substr)\(/],
  ["toDateString/toTimeString", /\.to(Date|Time)String\(/],
  ["toLocaleString (mọi loại; số → dùng số/vnd/kg trong format.ts)", /\.toLocaleString\(/],
  ["tiền hậu tố 'đ' tự viết tay (dùng vnd() / money() trong format.ts)", /\d\s?đ(?![a-zà-ỹ])|["'`]\s?đ["'`]|\}\s?đ(?![a-zà-ỹ])/i],
];

describe("SR-25: không định dạng ngày giờ theo giờ máy", () => {
  it("quét được file nguồn", () => {
    expect(FILES.length).toBeGreaterThan(100);
  });
  for (const [label, re] of FORBIDDEN) {
    it(`không dùng ${label} ngoài shared/lib/format.ts`, () => {
      const hits = FILES.flatMap((f) =>
        readFileSync(f, "utf8")
          .split("\n")
          .map((line, i) => ({ f, i: i + 1, line }))
          .filter(({ line }) => !/^\s*(\/\/|\*|\/\*)/.test(line) && re.test(line))
          .map(({ f, i }) => `${path.relative(ROOT, f)}:${i}`),
      );
      expect(hits).toEqual([]);
    });
  }
});

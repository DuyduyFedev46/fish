#!/usr/bin/env node
// Kiểm bản build thật không mang dữ liệu/mã mock (Lô 6, M5-1b).
//
// Cách dùng (sau `NEXT_PUBLIC_USE_MOCK=0 npm run build`):
//   node scripts/check-no-mock.mjs [thư-mục-build=out]
//
// Tự đọc các file `mock*.ts` (lib/, features/*/) để lấy chuỗi seed đặc trưng — mã đơn demo,
// mã mặt hàng, khoá localStorage mock, SĐT giả 0900000xxx, mật khẩu demo, tên trong dữ liệu mẫu —
// rồi tìm trong mọi file của thư mục build. Thấy bất kỳ chuỗi nào -> in ra file + chuỗi, exit 1.
// Không cần thêm chuỗi bằng tay: thêm seed vào mock*.ts là được quét tự động.

import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(fileURLToPath(import.meta.url), "..", "..");
const buildDir = resolve(root, process.argv[2] || "out");

function walk(dir, pred, acc = []) {
  for (const name of readdirSync(dir)) {
    if (name === "node_modules" || name === ".next" || name === "out" || name === "e2e") continue;
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) walk(p, pred, acc);
    else if (pred(name, p)) acc.push(p);
  }
  return acc;
}

const mockFiles = [
  ...walk(root, (n) => /^mock[^/]*\.ts$/.test(n)),
  // Component giả lập cổng thanh toán (chỉ dùng ở mock) — lấy nhãn hiển thị đặc trưng.
  ...walk(root, (n) => /^Mock.*\.tsx$/.test(n)),
];
if (mockFiles.length === 0) {
  console.error("check-no-mock: không tìm thấy file mock*.ts nào — script hỏng?");
  process.exit(2);
}

const seeds = new Map(); // chuỗi -> nguồn
const add = (s, why, file) => {
  if (s && s.length >= 6 && !seeds.has(s)) seeds.set(s, `${why} (${relative(root, file)})`);
};

for (const file of mockFiles) {
  const src = readFileSync(file, "utf8");
  for (const m of src.matchAll(/["'`](cangcaloc_[a-z0-9_]+)["'`]/g)) add(m[1], "khoá storage mock", file);
  for (const m of src.matchAll(/\b(DH-DEMO\w*)/g)) add(m[1], "mã đơn demo", file);
  for (const m of src.matchAll(/item_code:\s*["']([A-Z0-9-]{4,})["']/g)) add(m[1], "mã mặt hàng mẫu", file);
  for (const m of src.matchAll(/["'](0900000\d*)["']/g)) add(m[1], "SĐT giả", file);
  // Mật khẩu demo: chỉ chuỗi GÁN cho khoá tên đúng là password/mat_khau (`password: "x"`, `PASSWORD = "x"`),
  // không bắt chuỗi đứng sau dấu phẩy ("reset_password", "deactivate" là tên hành động, không phải mật khẩu).
  for (const m of src.matchAll(/(?<![A-Za-z0-9_])(?:password|mat_khau|mật khẩu)["']?\s*[:=]\s*["']([^"']{4,})["']/gi))
    add(m[1], "mật khẩu demo", file);
  // Mật khẩu kiểu demo1234 xuất hiện ở đâu trong file mock cũng là seed (không phụ thuộc tên khoá).
  for (const m of src.matchAll(/["'](demo\d{3,}\w*)["']/gi)) add(m[1], "mật khẩu demo", file);
  // Tên có khoảng trắng = chữ hiển thị của dữ liệu mẫu ("Cá basa phi lê"); bỏ tên field kỹ thuật ("currency").
  for (const m of src.matchAll(/\bname:\s*["']([^"']*\s[^"']*)["']/g)) add(m[1], "tên trong dữ liệu mẫu", file);
  for (const m of src.matchAll(/mock-gateway-tag">([^<{]{8,})</g)) add(m[1].trim(), "nhãn cổng giả lập", file);
}

if (!statSafe(buildDir)) {
  console.error(`check-no-mock: không có thư mục build: ${buildDir} (chạy npm run build trước)`);
  process.exit(2);
}
function statSafe(p) {
  try {
    return statSync(p).isDirectory();
  } catch {
    return false;
  }
}

const built = walk(buildDir, (n) => /\.(js|html|txt|json|css|map)$/.test(n));
const hits = [];
for (const file of built) {
  const text = readFileSync(file, "utf8");
  for (const [seed, why] of seeds) {
    if (text.includes(seed)) hits.push({ file: relative(root, file), seed, why });
  }
}

console.log(`check-no-mock: ${mockFiles.length} file mock, ${seeds.size} chuỗi seed, ${built.length} file build (${relative(root, buildDir)}/)`);
if (hits.length) {
  for (const h of hits) console.log(`  LỌT MOCK  ${h.file}\n            "${h.seed}" — ${h.why}`);
  console.log(`check-no-mock: ĐỎ — ${hits.length} chỗ lọt seed mock vào bản build.`);
  process.exit(1);
}
console.log("check-no-mock: XANH — không thấy seed mock nào trong bản build.");

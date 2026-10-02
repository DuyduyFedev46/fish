#!/usr/bin/env node
// Kiểm tra sau `npm run build`: màn nghiệp vụ KHÔNG được tải code AI khi AI tắt (BR-AI-17, DW-09-AC8, SR-20).
//
// Đọc `.next/app-build-manifest.json`, với các route nghiệp vụ trong TARGETS và 2 layout, liệt kê từng chunk JS
// rồi tìm chuỗi đặc trưng của runtime AI: `new Worker`, `wllama`, `/call/`.
// Có chunk chứa các chuỗi này -> in ra route + chunk + chuỗi trùng và thoát mã 1.
// Cuối cùng in bảng "First Load JS" (tổng byte chưa nén của các chunk JS) để ghi vào 03-dev-notes.md.
//
// Chạy:  node erp-console/scripts/check-ai-chunks.mjs   (hoặc `node scripts/check-ai-chunks.mjs` trong erp-console)

import { existsSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const nextDir = path.join(root, ".next");
const manifestPath = path.join(nextDir, "app-build-manifest.json");

// Mỗi mục: [khóa trong manifest, tên hiển thị]. Layout chung đứng đầu vì mọi màn đều tải nó (F13).
const TARGETS = [
  ["/layout", "layout gốc"],
  ["/(console)/layout", "layout console"],
  ["/(console)/orders/page", "/orders"],
  ["/(console)/orders/payments/page", "/orders/payments"],
  ["/(console)/orders/refunds/page", "/orders/refunds"],
  // Trang chi tiết có AiDocBlockGate (Lô 3): phải xanh dù có khối AI nhẹ; runtime nặng chỉ nạp động khi chạm khung hỏi.
  ["/(console)/orders/detail/page", "/orders/detail"],
  ["/(console)/orders/payments/detail/page", "/orders/payments/detail"],
  ["/(console)/orders/refunds/detail/page", "/orders/refunds/detail"],
  // Khách hàng (Lô 6): không có khối AI, dữ liệu cá nhân không đưa cho AI — phải xanh, không kéo runtime AI.
  ["/(console)/customers/page", "/customers"],
  ["/(console)/customers/detail/page", "/customers/detail"],
  ["/(console)/inventory/page", "/inventory"],
  ["/(console)/deliveries/page", "/deliveries"],
  ["/(console)/deliveries/detail/page", "/deliveries/detail"],
  ["/(console)/confirmation/page", "/confirmation"],
  ["/(console)/confirmation/detail/page", "/confirmation/detail"],
  ["/(console)/my-deliveries/page", "/my-deliveries"],
  ["/(console)/returns/page", "/returns"],
  ["/(console)/returns/detail/page", "/returns/detail"],
  ["/(console)/stocktake/page", "/stocktake"],
  ["/(console)/stocktake/new/page", "/stocktake/new"],
  ["/(console)/stocktake/edit/page", "/stocktake/edit"],
  ["/(console)/stocktake/detail/page", "/stocktake/detail"],
  ["/print/label/page", "/print/label"],
  ["/(console)/inventory/detail/page", "/inventory/detail"],
  ["/(console)/ledger/page", "/ledger"],
  // Mua hàng (Lô 10): danh sách + form nhập lô + chi tiết phiếu (có khối AI nhẹ) + form chi phí. Dữ liệu mua là giá vốn, không đưa AI trên máy.
  ["/(console)/purchasing/page", "/purchasing"],
  ["/(console)/purchasing/new/page", "/purchasing/new"],
  ["/(console)/purchasing/detail/page", "/purchasing/detail"],
  ["/(console)/purchasing/costs/new/page", "/purchasing/costs/new"],
  // Nhà cung cấp (Lô 11): trang chi tiết có AiDocBlockGate (purchasing.supplier); danh sách không có AI. Cả hai phải xanh.
  ["/(console)/suppliers/page", "/suppliers"],
  ["/(console)/suppliers/detail/page", "/suppliers/detail"],
  // Kế toán (Lô 12): Báo cáo lãi lỗ, Hoá đơn bán, Hoá đơn mua và chi phí phụ. Không có khối AI, phải xanh.
  ["/(console)/reports/page", "/reports"],
  ["/(console)/accounting/sales-invoices/page", "/accounting/sales-invoices"],
  ["/(console)/accounting/purchase-invoices/page", "/accounting/purchase-invoices"],
];

// Chuỗi đặc trưng của code AI chạy trên máy (worker, thư viện wllama, gọi lệnh AI).
const FORBIDDEN = [
  ["new Worker", /new Worker/],
  ["wllama", /wllama/i],
  ["/call/", /\/call\//],
];

if (!existsSync(manifestPath)) {
  console.error(`Không thấy ${path.relative(process.cwd(), manifestPath)} — hãy chạy "npm run build" trước.`);
  process.exit(2);
}

const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
const pages = manifest.pages ?? {};
const cache = new Map(); // chunk -> { size, hits[] }

function inspect(chunk) {
  if (cache.has(chunk)) return cache.get(chunk);
  const file = path.join(nextDir, chunk);
  let info = { size: 0, hits: [] };
  if (existsSync(file)) {
    const text = readFileSync(file, "utf8");
    info = {
      size: statSync(file).size,
      hits: FORBIDDEN.filter(([, re]) => re.test(text)).map(([name]) => name),
    };
  }
  cache.set(chunk, info);
  return info;
}

const problems = [];
const rows = [];

for (const [key, label] of TARGETS) {
  const chunks = pages[key];
  if (!chunks) {
    problems.push(`Không thấy route "${key}" trong manifest — đường dẫn đổi tên? Cập nhật TARGETS.`);
    continue;
  }
  const js = chunks.filter((c) => c.endsWith(".js"));
  let total = 0;
  for (const chunk of js) {
    const { size, hits } = inspect(chunk);
    total += size;
    if (hits.length > 0) {
      problems.push(`${label}: chunk ${chunk} chứa ${hits.map((h) => `"${h}"`).join(", ")}`);
    }
  }
  rows.push({ label, chunks: js.length, total });
}

const kb = (n) => `${(n / 1024).toFixed(1)} kB`;
console.log("First Load JS (chưa nén, cộng các chunk trong app-build-manifest)");
console.log("| Route | Số chunk | Dung lượng |");
console.log("|---|---|---|");
for (const r of rows) console.log(`| ${r.label} | ${r.chunks} | ${kb(r.total)} |`);

if (problems.length > 0) {
  console.error("\nĐỎ: code AI còn nằm trong chunk màn nghiệp vụ (BR-AI-17):");
  for (const p of problems) console.error(`  - ${p}`);
  process.exit(1);
}

const layoutCount = TARGETS.filter(([key]) => key.endsWith("/layout")).length;
console.log(`\nXANH: ${TARGETS.length - layoutCount} màn nghiệp vụ và ${layoutCount} layout (tổng ${TARGETS.length} mục) không chứa \`new Worker\`, \`wllama\`, \`/call/\`.`);

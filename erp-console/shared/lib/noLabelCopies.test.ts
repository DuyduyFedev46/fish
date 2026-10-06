// Lô áp tên chuẩn (02b mục 3.2): quét mã nguồn ERP, không được còn chữ cũ của nhóm A (doc/thuat-ngu-va-trang-thai.md mục 4).
// Chữ chuẩn chỉ viết ở shared/lib/enums.ts; nơi khác lấy từ ENUMS. Mock cũng bị quét nên mock lệch chữ là đỏ.
// Chỉ xét phần mã (bỏ comment). Mã luật "BR-" nằm trong mock lỗi và trường `br` nên do e2e bắt trên chữ hiển thị.
import { readdirSync, readFileSync, statSync } from "fs";
import path from "path";
import { describe, expect, it } from "vitest";

const ROOT = path.resolve(__dirname, "../..");

/** TODO Pha B: bỏ khỏi danh sách này sau khi W37 L3 gộp và các file được sửa (02b mục 4). */
const PHASE_B_FILES = new Set([
  "features/audit/auditModel.ts",
  "features/audit/mock.ts",
  "features/orders/orderDetailModel.ts",
  "features/orders/components/OrderDetailScreen.tsx",
]);
/** Không thuộc lô này: phần AI (lô dọn chữ AI) và permissions (nhánh F1 đang giữ). */
const SKIP_PREFIXES = ["features/ai/", "features/permissions/"];

const FORBIDDEN: Array<string | RegExp> = [
  // Từ tiếng Anh: so theo ranh giới từ để không bắt tên hàm/biến (PublishBatchModal, onPublish...).
  /\bTTL\b/, /\bWebhook\b/, /\bSandbox\b/, /\bProduction\b/, /\bPublish\b/, /— chờ Chủ(?! hoặc)/, // chỉ cấm đuôi nhãn "— chờ Chủ"; câu "chờ Chủ hoặc Quản lý duyệt" là lời văn hợp lệ
  "Khớp — đã xác nhận", "Về sau khi đơn tự huỷ", "Hư khi đóng hàng",
  "Hư hỏng khi soạn hàng", "Bỏ sau khi giao thất bại", "Bỏ giao sau khi thất bại", "chưa hiện thực", "Hàng hoàn về kho",
  "Trả hàng về kho", "trả về kho", "hàng về kho:", "phiếu hàng về kho", "đảo doanh thu", "hoá đơn điều chỉnh", "phiếu giảm trừ",
  "Phiếu hoàn chờ chuyển", /phiếu hoàn(?! tiền)/i, "Tạo phiếu hoàn", "Thử hoàn lại", "hạch toán", "Huỷ bỏ, ghi lỗ",
  "Mục chờ gọi CSKH", "Phiếu giao hàng", "Giao dịch thanh toán", "Phiếu nhập kho", "Phiếu điều chỉnh kho", "Trả NCC",
  "Trả lô về nhà cung cấp", "Giao không xác nhận", "Gia hạn thêm", "Gia hạn giao", "Bỏ qua bước", "Cần gọi ngay",
  "Xác nhận thanh toán thủ công", "Giao phiếu cho người giao", "Gán phiếu giao", "Đóng gói phiếu giao", "Điều khoản mua hàng",
  "Đổi trả hoàn tiền", "Combo dạng gói", "Khách muốn đổi món –",
];

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    if (name === "node_modules" || name === ".next" || name === "out") continue;
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) walk(full, out);
    else if (/\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name) && !full.includes(`${path.sep}testing${path.sep}`)) out.push(full);
  }
  return out;
}

/** Bỏ comment khối (giữ nguyên số dòng) và comment cuối dòng (không đụng "https://"). */
function stripComments(src: string): string {
  return src.replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, "")).replace(/(^|[^:"'`\w])\/\/.*$/gm, "$1");
}

describe("không còn chữ cũ của nhóm A trong mã nguồn ERP (02b 3.2)", () => {
  const files = ["features", "shared", "app"]
    .flatMap((d) => walk(path.join(ROOT, d)))
    .map((f) => path.relative(ROOT, f).split(path.sep).join("/"))
    .filter((f) => !PHASE_B_FILES.has(f) && !SKIP_PREFIXES.some((p) => f.startsWith(p)));

  it("quét được nhiều file", () => {
    expect(files.length).toBeGreaterThan(100);
  });

  it("không file nào chứa chữ cấm", () => {
    const hits: string[] = [];
    for (const f of files) {
      const code = stripComments(readFileSync(path.join(ROOT, f), "utf8"));
      code.split("\n").forEach((line, i) => {
        for (const bad of FORBIDDEN) {
          if (typeof bad === "string" ? line.includes(bad) : bad.test(line)) hits.push(`${f}:${i + 1} «${String(bad)}»`);
        }
      });
    }
    expect(hits).toEqual([]);
  });
});

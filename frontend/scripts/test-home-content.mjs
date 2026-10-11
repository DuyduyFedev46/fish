#!/usr/bin/env node
// Test cho khối trang chủ từ CMS (SHOP-5-03, 02b §3.7.2) và cache khi lỗi mạng (review lô 3+4, L3):
//   features/home/homeBlocks.ts · features/home/homeContent.ts · features/content/policySummary.ts
//   node scripts/test-home-content.mjs
// Không thêm thư viện: chuyển .ts sang JS bằng `typescript` rồi nạp qua data: URL; API được thay bằng bản giả.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const root = resolve(fileURLToPath(import.meta.url), "..", "..");
const tr = (f) =>
  ts.transpileModule(readFileSync(`${root}/${f}`, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
  }).outputText;
const b64 = (js) => `data:text/javascript;base64,${Buffer.from(js).toString("base64")}`;

// Bản giả: ApiError giống lib/types.ts; fetchPublicEntry đọc kịch bản từ globalThis.
const typesUrl = b64(`export class ApiError extends Error {
  constructor(message, status, code, data) { super(message); this.status = status; this.code = code; this.data = data; }
}`);
const apiUrl = b64(`export async function fetchPublicEntry(slug) {
  globalThis.__calls.push(slug);
  return globalThis.__fetch(slug);
}`);
const slugsUrl = b64(tr("features/content/slugs.ts"));
const wire = (js) =>
  js
    .replaceAll('"@/lib/types"', `"${typesUrl}"`)
    .replaceAll('"@/features/content/api"', `"${apiUrl}"`)
    .replaceAll('"./api"', `"${apiUrl}"`)
    .replaceAll('"@/features/content/slugs"', `"${slugsUrl}"`)
    .replaceAll('"./slugs"', `"${slugsUrl}"`);

const blocks = await import(b64(tr("features/home/homeBlocks.ts")));
const { ApiError } = await import(typesUrl);

let n = 0;
let fail = 0;
function eq(name, got, want) {
  n++;
  if (JSON.stringify(got) !== JSON.stringify(want)) {
    fail++;
    console.log(`SAI  ${name}: được ${JSON.stringify(got)}, cần ${JSON.stringify(want)}`);
  }
}

const h2 = (text) => ({ type: "heading", level: 2, text });
const p = (...children) => ({ type: "paragraph", children });
const t = (text, extra = {}) => ({ text, ...extra });

// ---- Banner ----
const seeded = {
  blocks: [h2("Mua theo lô tại cảng"), p(t("Hải sản cấp đông, giá theo kg, mua từ 1 kg.")), p(t("Xem hàng đang có", { href: "/shop/" }))],
};
eq("banner nạp sẵn", blocks.parseBanner(seeded), [
  { title: "Mua theo lô tại cảng", subtitle: "Hải sản cấp đông, giá theo kg, mua từ 1 kg.", button: { label: "Xem hàng đang có", href: "/shop/" }, image: null },
]);
eq("banner rỗng", blocks.parseBanner({ blocks: [] }), []);
eq("banner null", blocks.parseBanner(null), []);
eq("banner body hỏng", blocks.parseBanner({ blocks: "x" }), []);
eq("bỏ khối trước tiêu đề đầu", blocks.parseBanner({ blocks: [p(t("lạc")), h2("A")] }).map((s) => s.title), ["A"]);
eq("heading cấp 3 không thành slide", blocks.parseBanner({ blocks: [{ type: "heading", level: 3, text: "B" }, p(t("x"))] }), []);
eq(
  "tối đa 3 slide",
  blocks.parseBanner({ blocks: [h2("1"), h2("2"), h2("3"), h2("4")] }).map((s) => s.title),
  ["1", "2", "3"]
);
eq("link ngoài không thành nút", blocks.parseBanner({ blocks: [h2("A"), p(t("Mua", { href: "https://x.vn" }))] })[0].button, null);
eq("link // không thành nút", blocks.parseBanner({ blocks: [h2("A"), p(t("Mua", { href: "//evil.vn" }))] })[0].button, null);
eq("javascript: không thành nút", blocks.parseBanner({ blocks: [h2("A"), p(t("Mua", { href: "javascript:alert(1)" }))] })[0].button, null);
eq(
  "đoạn có chữ ngoài link không thành nút, cũng không làm câu phụ",
  blocks.parseBanner({ blocks: [h2("A"), p(t("Bấm "), t("đây", { href: "/shop/" }))] })[0],
  { title: "A", subtitle: "", button: null, image: null }
);
eq(
  "ảnh nền chỉ nhận http(s)",
  blocks.parseBanner({
    blocks: [h2("A"), { type: "image", alt: "Ảnh minh hoạ", urls: { sm: "", md: "", lg: "https://cdn.vn/a.jpg" } }],
  })[0].image,
  { src: "https://cdn.vn/a.jpg", alt: "Ảnh minh hoạ" }
);
eq(
  "ảnh data: bị bỏ",
  blocks.parseBanner({ blocks: [h2("A"), { type: "image", alt: "", urls: { lg: "data:image/png;base64,AA" } }] })[0].image,
  null
);

// ---- Dải chữ ----
eq("dải chữ gọn khoảng trắng", blocks.stripTextOf("  Hải sản   cấp đông "), "Hải sản cấp đông");
eq("dải chữ rỗng", blocks.stripTextOf(""), "");
eq("dải chữ không phải chuỗi", blocks.stripTextOf(null), "");
eq("dự phòng 1 kg", blocks.fallbackStripText("1"), "Hải sản cấp đông theo lô · mua từ 1 kg · giao tận nhà");
eq("dự phòng 0,5 kg", blocks.fallbackStripText("0.5"), "Hải sản cấp đông theo lô · mua từ 0,5 kg · giao tận nhà");
eq("dự phòng 1.50 -> 1,5", blocks.fallbackStripText("1.50"), "Hải sản cấp đông theo lô · mua từ 1,5 kg · giao tận nhà");
eq("dự phòng thiếu số -> ẩn", blocks.fallbackStripText(undefined), "");
eq("dự phòng số lạ -> ẩn", blocks.fallbackStripText("abc"), "");

// ---- Cam kết ----
const li = (title, detail) => [t(title, { marks: ["bold"] }), t(` ${detail}`)];
const commitBody = {
  blocks: [
    {
      type: "list",
      ordered: false,
      items: [
        li("Cấp đông theo lô", "Mua tại cảng, mỗi lô có hạn dùng riêng."),
        li("Giao tận nhà", "Đã gồm giao hàng ở Phan Thiết, không trả thêm khi nhận hàng."),
        li("Quét mã QR", "Chuyển khoản bằng app ngân hàng."),
      ],
    },
  ],
};
eq("cam kết nạp sẵn", blocks.parseCommitments(commitBody), [
  { title: "Cấp đông theo lô", detail: "Mua tại cảng, mỗi lô có hạn dùng riêng.", icon: "snowflake" },
  { title: "Giao tận nhà", detail: "Đã gồm giao hàng ở Phan Thiết, không trả thêm khi nhận hàng.", icon: "truck" },
  { title: "Quét mã QR", detail: "Chuyển khoản bằng app ngân hàng.", icon: "qr" },
]);
eq("mục không đậm bị bỏ", blocks.parseCommitments({ blocks: [{ type: "list", items: [[t("thường")], li("A", "b")] }] }).map((c) => c.title), ["A"]);
eq("bỏ dấu nối đầu mô tả", blocks.parseCommitments({ blocks: [{ type: "list", items: [li("A", ": mô tả")] }] })[0].detail, "mô tả");
eq(
  "tối đa 4 mục",
  blocks.parseCommitments({ blocks: [{ type: "list", items: [1, 2, 3, 4, 5].map((i) => li(`M${i}`, "x")) }] }).length,
  4
);
eq("không có list", blocks.parseCommitments({ blocks: [p(t("x"))] }), []);
eq("icon thanh toán", blocks.commitmentIcon("Thanh toán chuyển khoản"), "qr");
eq("icon khác", blocks.commitmentIcon("Đổi trả rõ ràng"), "check");
eq("hằng số ô", [blocks.MOBILE_COMMITMENTS, blocks.DESKTOP_COMMITMENTS], [3, 2]);

// ---- Cache (homeContent, policySummary): giữ khi 404/410 hoặc có trang; bỏ khi lỗi mạng ----
globalThis.__calls = [];
const home = await import(b64(wire(tr("features/home/homeContent.ts"))));
let mode = "network";
globalThis.__fetch = async (slug) => {
  if (mode === "network") throw new TypeError("Failed to fetch");
  if (mode === "gone") throw new ApiError("Không tìm thấy", 404);
  return { slug, excerpt: "Tóm tắt " + slug, body: { type: "doc", blocks: [] } };
};
let threw = false;
try {
  await home.loadHomeBanner();
} catch {
  threw = true;
}
eq("lỗi mạng -> ném lỗi", threw, true);
mode = "ok";
eq("lần sau tải lại sau lỗi mạng", (await home.loadHomeBanner())?.slug, "home-banner");
await home.loadHomeBanner();
eq("có trang -> cache (2 request cho 3 lần gọi)", globalThis.__calls.filter((s) => s === "home-banner").length, 2);
mode = "gone";
eq("404 -> null", await home.loadHomeCommitments(), null);
await home.loadHomeCommitments();
eq("404 -> cache", globalThis.__calls.filter((s) => s === "home-commitments").length, 1);

globalThis.__calls = [];
const summary = await import(b64(wire(tr("features/content/policySummary.ts"))));
mode = "network";
eq("tóm tắt lỗi mạng -> ẩn dòng", await summary.getPolicySummaries(), { shipping: null, returns: null });
mode = "ok";
eq("tóm tắt: lần sau tải lại (L3)", (await summary.getPolicySummaries()).shipping?.text, "Tóm tắt giao-hang");
const before = globalThis.__calls.length;
await summary.getPolicySummaries();
eq("tóm tắt: có trang -> cache", globalThis.__calls.length, before);

console.log(`test-home-content: ${n - fail}/${n} đạt, ${fail} sai`);
process.exit(fail ? 1 : 0);

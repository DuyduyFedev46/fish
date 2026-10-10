#!/usr/bin/env node
// Test cho features/checkout/orderState.ts (trạng thái đơn + result -> màn, đồng hồ giữ hàng). Cùng kiểu test-cart-reconcile.mjs.
//   node scripts/test-order-state.mjs
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const root = resolve(fileURLToPath(import.meta.url), "..", "..");
const js = ts.transpileModule(readFileSync(`${root}/features/checkout/orderState.ts`, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
}).outputText;
const m = await import(`data:text/javascript;base64,${Buffer.from(js).toString("base64")}`);
const load = async (file) =>
  import(
    `data:text/javascript;base64,${Buffer.from(
      ts.transpileModule(readFileSync(`${root}/${file}`, "utf8"), {
        compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
      }).outputText
    ).toString("base64")}`
  );
const rules = await load("features/checkout/formRules.ts");
const reorder = await load("features/checkout/reorder.ts");

let n = 0;
let fail = 0;
function eq(name, got, want) {
  n++;
  const g = JSON.stringify(got);
  const w = JSON.stringify(want);
  if (g !== w) {
    fail++;
    console.log(`SAI  ${name}: được ${g}, cần ${w}`);
  }
}

const T0 = Date.UTC(2026, 9, 11, 3, 0, 0);
const MIN = 60 * 1000;
const at = (order, result, waitedMs = null) =>
  m.screenFor(order, result, { now: T0 + (waitedMs ?? 0), pendingSince: waitedMs === null ? null : T0 });
const pick = (d) => [d.screen, d.banner, d.pollMs];

// parsePaymentResult
eq("result success", m.parsePaymentResult("success"), "success");
eq("result lạ", m.parsePaymentResult("hack"), null);
eq("result null", m.parsePaymentResult(null), null);

// awaiting_payment
eq("D1", pick(at({ state: "awaiting_payment" }, null)), ["payment", null, null]);
eq("D2 cancel", pick(at({ state: "awaiting_payment" }, "cancel")), ["payment_retry", null, null]);
eq("D2 error", pick(at({ state: "awaiting_payment" }, "error")), ["payment_retry", null, null]);
eq("D3 vừa mở", pick(at({ state: "awaiting_payment", payment_pending_minutes: 5 }, "success", 0)), ["pending", null, 5000]);
eq("D3 chưa tới ngưỡng", pick(at({ state: "awaiting_payment", payment_pending_minutes: 5 }, "success", 4 * MIN + 59000)), ["pending", null, 5000]);
eq("D3 đúng ngưỡng", pick(at({ state: "awaiting_payment", payment_pending_minutes: 5 }, "success", 5 * MIN)), ["pending_slow", null, 30000]);
eq("D3 quá ngưỡng", pick(at({ state: "awaiting_payment", payment_pending_minutes: 5 }, "success", 9 * MIN)), ["pending_slow", null, 30000]);
eq("D3 ngưỡng mặc định 5", pick(at({ state: "awaiting_payment" }, "success", 6 * MIN)), ["pending_slow", null, 30000]);
eq("D3 chưa có mốc chờ", pick(at({ state: "awaiting_payment", payment_pending_minutes: 5 }, "success", null)), ["pending", null, 5000]);

// hết giờ
eq("D4 hộp thoại, không result", pick(at({ state: "hold_expired" }, null)), ["expired_dialog", null, 5000]);
eq("D4 hộp thoại, result success", pick(at({ state: "hold_expired" }, "success")), ["expired_dialog", null, 5000]);
eq("D4 trang", pick(at({ state: "expired" }, "success")), ["expired_page", null, null]);

// huỷ
eq("E2", pick(at({ state: "cancelled" }, null)), ["cancelled", null, null]);
eq("E2 tiền về sau", pick(at({ state: "cancelled", late_payment: true }, null)), ["cancelled_late", null, null]);
eq("E2 bỏ qua result", pick(at({ state: "cancelled" }, "success")), ["cancelled", null, null]);

// đã trả
eq("E1 vừa trả", pick(at({ state: "preparing" }, "success")), ["order", "paid_success", null]);
eq("E1 mở lại link cũ cancel", pick(at({ state: "preparing" }, "cancel")), ["order", "already_paid", null]);
eq("E1 mở lại link cũ error", pick(at({ state: "delivering" }, "error")), ["order", "already_paid", null]);
eq("E1 không result", pick(at({ state: "delivering" }, null)), ["order", null, null]);
eq("E5 huỷ một phần", pick(at({ state: "preparing", cancel_notice: { scope: "partial" } }, null)), ["order_partial_cancel", null, null]);
eq("E1 notice full không phải E5", pick(at({ state: "preparing", cancel_notice: { scope: "full" } }, null)), ["order", null, null]);
eq("E4", pick(at({ state: "delivery_failed" }, "success")), ["delivery_failed", null, null]);
eq("E3", pick(at({ state: "completed" }, "cancel")), ["delivered", null, null]);

// màn thanh toán
eq("isPaymentScreen D1", m.isPaymentScreen("payment"), true);
eq("isPaymentScreen D4 hộp thoại", m.isPaymentScreen("expired_dialog"), true);
eq("isPaymentScreen E1", m.isPaymentScreen("order"), false);
eq("isPaymentScreen D3", m.isPaymentScreen("pending"), false);

// đồng hồ
const serverNow = new Date(T0).toISOString();
eq("offset máy chạy nhanh 2 phút", m.clockOffsetMs(serverNow, T0 + 2 * MIN), -2 * MIN);
eq("offset thiếu server_now", m.clockOffsetMs(undefined, T0), 0);
eq("offset hỏng", m.clockOffsetMs("rác", T0), 0);
const expires = new Date(T0 + 30 * MIN).toISOString();
eq("còn lại bù lệch", m.remainingMs(expires, T0 + 2 * MIN + 10 * MIN, -2 * MIN), 20 * MIN);
eq("còn lại không âm", m.remainingMs(expires, T0 + 40 * MIN, 0), 0);
eq("còn lại hạn hỏng", m.remainingMs("rác", T0, 0), null);
eq("còn lại thiếu hạn", m.remainingMs(null, T0, 0), null);
eq("effective: hết giờ", m.effectiveState("awaiting_payment", 0), "hold_expired");
eq("effective: còn giờ", m.effectiveState("awaiting_payment", 1000), "awaiting_payment");
eq("effective: không có hạn", m.effectiveState("awaiting_payment", null), "awaiting_payment");
eq("effective: state khác", m.effectiveState("preparing", 0), "preparing");

// định dạng
eq("mm:ss 29:42", m.formatRemaining(29 * MIN + 42 * 1000), "29:42");
eq("mm:ss làm tròn lên", m.formatRemaining(41500), "00:42");
eq("mm:ss 0", m.formatRemaining(0), "00:00");
eq("mm:ss âm", m.formatRemaining(-5), "00:00");
eq("nhãn phút giây", m.remainingLabel(18 * MIN + 24000), "Còn 18 phút 24 giây");
eq("nhãn tròn phút", m.remainingLabel(5 * MIN), "Còn 5 phút");
eq("nhãn dưới phút", m.remainingLabel(42000), "Còn 42 giây");
eq("đã chờ", m.formatWaited(4000), "0:04");
eq("đã chờ phút", m.formatWaited(65000), "1:05");

// timeline
const baseOrder = { placed_at: "2026-10-11T03:00:00Z", paid_at: "2026-10-11T03:04:00Z", delivered_at: null };
const stepStates = (state) => m.buildOrderTimeline({ ...baseOrder, state }).map((s) => s.state).join(",");
eq("timeline preparing", stepStates("preparing"), "done,done,current,upcoming,upcoming");
eq("timeline delivering", stepStates("delivering"), "done,done,done,current,upcoming");
eq("timeline failed", stepStates("delivery_failed"), "done,done,done,failed,upcoming");
eq("timeline completed", stepStates("completed"), "done,done,done,done,done");
eq("timeline huỷ: không có", m.buildOrderTimeline({ ...baseOrder, state: "cancelled" }), []);
eq("timeline chờ trả: không có", m.buildOrderTimeline({ ...baseOrder, state: "awaiting_payment" }), []);
eq(
  "timeline giờ chỉ ở 3 mốc",
  m.buildOrderTimeline({ ...baseOrder, delivered_at: "2026-10-11T08:00:00Z", state: "completed" }).map((s) => s.time ?? null),
  ["2026-10-11T03:00:00Z", "2026-10-11T03:04:00Z", null, null, "2026-10-11T08:00:00Z"]
);

// form
eq("SĐT 0900000001", rules.validPhone("0900000001"), true);
eq("SĐT +84 900 000 001", rules.validPhone("+84 900 000 001"), true);
eq("SĐT 84900000001", rules.validPhone("84900000001"), true);
eq("SĐT 0900.000.001", rules.validPhone("0900.000.001"), true);
eq("SĐT thiếu số", rules.validPhone("09123"), false);
eq("SĐT 11 số", rules.validPhone("09000000011"), false);
eq("SĐT không bắt đầu 0", rules.validPhone("9000000001"), false);
eq("SĐT chữ", rules.validPhone("09000000ab"), false);
eq("chuẩn hoá +84", rules.normalizeVnPhone("+84 900 000 001"), "0900000001");
eq("tên rỗng", rules.validName("   "), false);
eq("tên ok", rules.validName(" Nguyễn Văn A "), true);
eq("tên quá dài", rules.validName("a".repeat(101)), false);
eq("địa chỉ rỗng", rules.validAddress(" "), false);
eq("địa chỉ quá dài", rules.validAddress("a".repeat(501)), false);
eq(
  "form trống: 4 lỗi đúng thứ tự",
  rules.errorSummary(rules.validateForm({ name: "", phone: "", address: "", consent: false }, true)).map((e) => e.fieldId),
  ["f-name", "f-phone", "f-addr", "f-consent"]
);
eq(
  "form chưa tick đồng ý",
  rules.validateForm({ name: "A", phone: "0900000001", address: "1 Đường Thử", consent: false }, true),
  { consent: "Đánh dấu đồng ý ở trên để đặt hàng." }
);
eq(
  "form không bắt đồng ý",
  rules.validateForm({ name: "A", phone: "0900000001", address: "1 Đường Thử", consent: false }, false),
  {}
);

// mua lại
const catalog = [
  { item_code: "A", name: "Mực ống", unit: "kg", price: "180000", stock_level: "in" },
  { item_code: "B", name: "Cua", unit: "kg", price: "950000", stock_level: "out" },
];
const orderLines = [
  { item_code: "A", name: "Mực ống", unit: "kg", qty: "1.5", amount: "270000" },
  { item_code: "B", name: "Cua", unit: "kg", qty: "1", amount: "950000" },
];
eq(
  "mua lại: đặt đúng số lượng, bỏ món hết",
  reorder.mergeOrderIntoCart([{ item_code: "A", name: "Mực ống", unit: "kg", price: "1", qty: 5 }], orderLines, catalog),
  [{ item_code: "A", name: "Mực ống", unit: "kg", price: "180000", qty: 1.5 }]
);
eq(
  "mua lại: giữ món khác trong giỏ",
  reorder.mergeOrderIntoCart([{ item_code: "Z", name: "Z", unit: "kg", price: "1", qty: 1 }], orderLines.slice(0, 1), catalog).map((e) => e.item_code),
  ["Z", "A"]
);
eq(
  "mua lại: chưa có catalog thì suy giá",
  reorder.mergeOrderIntoCart([], orderLines.slice(0, 1), null),
  [{ item_code: "A", name: "Mực ống", unit: "kg", price: "180000", qty: 1.5 }]
);
eq("mua lại: món không còn trong catalog", reorder.mergeOrderIntoCart([], [{ ...orderLines[0], item_code: "Q" }], catalog), []);

console.log(`test-order-state: ${n - fail}/${n} đạt`);
process.exit(fail ? 1 : 0);

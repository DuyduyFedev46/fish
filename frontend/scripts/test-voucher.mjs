#!/usr/bin/env node
// Test cho features/cart/voucherView.ts (chuẩn hoá mã, câu lỗi, dòng điều kiện của mã giảm giá, SHOP-3b-05).
//   node scripts/test-voucher.mjs
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
const formatUrl = b64(tr("lib/format.ts"));
const m = await import(b64(tr("features/cart/voucherView.ts").replace('"@/lib/format"', `"${formatUrl}"`)));

let n = 0;
let fail = 0;
function eq(name, got, want) {
  n++;
  if (JSON.stringify(got) !== JSON.stringify(want)) {
    fail++;
    console.log(`SAI  ${name}: được ${JSON.stringify(got)}, cần ${JSON.stringify(want)}`);
  }
}

// Chuẩn hoá chữ gõ
eq("in hoa", m.normalizeVoucherInput("cave10"), "CAVE10");
eq("bỏ khoảng trắng", m.normalizeVoucherInput(" ca ve 10 "), "CAVE10");
eq("cắt 20", m.normalizeVoucherInput("A".repeat(30)).length, 20);

// Lý do -> loại lỗi
for (const r of ["INVALID", "EXPIRED", "MIN_ORDER", "USED_UP", "BETTER_PROMO"]) eq(`reason ${r}`, m.reasonToKind(r), r);
eq("reason lạ", m.reasonToKind("???"), "INVALID");
eq("reason null", m.reasonToKind(null), "INVALID");

// Câu lỗi (COMPONENTS #48 mục 10)
eq("msg INVALID", m.voucherMessage("INVALID"), "Mã không đúng hoặc đã hết hạn.");
eq("msg EXPIRED", m.voucherMessage("EXPIRED"), "Mã không đúng hoặc đã hết hạn.");
eq("msg MIN_ORDER", m.voucherMessage("MIN_ORDER", "300000"), "Đơn cần từ 300.000đ để dùng mã này.");
eq("msg USED_UP", m.voucherMessage("USED_UP"), "Mã đã hết lượt dùng.");
eq("msg BETTER_PROMO", m.voucherMessage("BETTER_PROMO"), "Ưu đãi đang áp đã có lợi hơn mã này.");
eq("msg NETWORK", m.voucherMessage("NETWORK"), "Chưa kiểm được mã.");
eq("BETTER_PROMO là thông tin", m.isInfoKind("BETTER_PROMO"), true);
eq("MIN_ORDER là lỗi", m.isInfoKind("MIN_ORDER"), false);

// Dòng điều kiện: hạn theo giờ VN (16:59Z = 23:59 +07), không số lượt còn
const pct = { kind: "PERCENT", value: "10", max_discount: "100000", min_order_amount: "300000", ends_at: "2026-10-31T16:59:00Z", customer_terms: "" };
eq("terms %", m.describeTerms(pct), "Giảm 10%, tối đa 100.000đ · Đơn từ 300.000đ · Hạn 23:59 31/10 · Số lượt có hạn");
eq("terms đồng, không đơn tối thiểu", m.describeTerms({ ...pct, kind: "AMOUNT", value: "50000", max_discount: null, min_order_amount: "0" }), "Giảm 50.000đ · Hạn 23:59 31/10 · Số lượt có hạn");
eq("terms có lời của Cá Về", m.describeTerms({ ...pct, customer_terms: "Chỉ đơn trên web" }), "Giảm 10%, tối đa 100.000đ · Đơn từ 300.000đ · Hạn 23:59 31/10 · Số lượt có hạn. Chỉ đơn trên web");
eq("đoạn đầy đủ không lặp dấu chấm", m.describeTermsFull({ ...pct, customer_terms: "Chỉ đơn trên web." }), "Giảm 10%, tối đa 100.000đ · Đơn từ 300.000đ · Hạn 23:59 31/10 · Số lượt có hạn. Chỉ đơn trên web. Không áp dụng cùng ưu đãi khác; Cá Về tự chọn mức có lợi hơn cho bạn.");
eq("không lộ số lượt còn", /còn \d|lượt còn/i.test(m.describeTerms(pct)), false);

// Đơn tối thiểu cho câu MIN_ORDER: terms trước, không có thì tạm tính + còn thiếu
eq("minOrder từ terms", m.minOrderOf({ terms: { min_order_amount: "300000" }, subtotal: "256000", missing_amount: "44000" }), "300000");
eq("minOrder từ số còn thiếu", m.minOrderOf({ terms: null, subtotal: "256000", missing_amount: "44000" }), "300000");
eq("minOrder không biết", m.minOrderOf({ terms: null, subtotal: "256000", missing_amount: null }), null);

// Giỏ rỗng thì xoá mã (B1 QA 3b)
eq("giỏ rỗng đã nạp -> xoá", m.shouldClearVoucher(true, 0), true);
eq("giỏ rỗng chưa nạp -> chưa xoá", m.shouldClearVoucher(false, 0), false);
eq("giỏ có món -> giữ", m.shouldClearVoucher(true, 2), false);
eq("BETTER_PROMO kèm số", m.voucherMessage("BETTER_PROMO", null, "60000"), "Ưu đãi đang áp (−60.000đ) đã có lợi hơn mã này.");

// B2 QA lô 7: luôn gửi mã đã áp, kể cả khi chưa kiểm lại xong
eq("gửi mã của hook", m.voucherCodeToSend("CAVE10", "CAVE10", false), "CAVE10");
eq("hook chưa nạp thì lấy mã đã lưu", m.voucherCodeToSend(null, "CAVE10", false), "CAVE10");
eq("không có mã", m.voucherCodeToSend(null, null, false), undefined);
eq("đặt không dùng mã", m.voucherCodeToSend("CAVE10", "CAVE10", true), undefined);

// Vân tay dòng: không phụ thuộc thứ tự
eq("itemsKey", m.itemsKey([{ item_code: "B", qty: "1" }, { item_code: "A", qty: "1.5" }]), m.itemsKey([{ item_code: "A", qty: "1.5" }, { item_code: "B", qty: "1" }]));

console.log(`${n - fail}/${n} ca đạt`);
process.exit(fail ? 1 : 0);

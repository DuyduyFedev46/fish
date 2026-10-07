import { describe, expect, it } from "vitest";
import { ApiError } from "@/shared/lib/http";
import { mockOrdersApi, mockPaymentsApi, mockRefundsApi } from "./mock";
import { isLateEntry, paymentTimeline } from "./orderDetailModel";
import {
  bookedOrderIdOf,
  buildLateBody,
  checkReceivedAt,
  checkTxnId,
  existingPaymentIdOf,
  hasDuplicateWarning,
  normalizeTxnId,
  nowForInput,
  similarOf,
} from "./latePayment";
import type { OrderListItem, PaymentQueueItem, RecordLatePaymentResult } from "./types";

describe("mã giao dịch (BR-TT-18)", () => {
  it("chuẩn hoá như BE: bỏ khoảng trắng, in hoa", () => {
    expect(normalizeTxnId(" ft 2610 0300001 ")).toBe("FT26100300001");
  });
  it("rỗng, quá dài, ký tự lạ (chữ có dấu, @, khoảng trắng đã bỏ)", () => {
    expect(checkTxnId("   ")).toBe("missing");
    expect(checkTxnId("A".repeat(101))).toBe("tooLong");
    expect(checkTxnId("Nguyễn Văn A")).toBe("badChars");
    expect(checkTxnId("0900000321@x")).toBe("badChars");
    expect(checkTxnId("ft26100300001")).toBeNull();
    expect(checkTxnId("FT-26.10/03_1")).toBeNull();
  });
});

describe("giờ nhận (giờ Việt Nam)", () => {
  const now = new Date("2026-10-07T03:00:00Z"); // 10:00 giờ VN
  it("thiếu / sai dạng", () => {
    expect(checkReceivedAt("", now)).toBe("missing");
    expect(checkReceivedAt("hôm qua", now)).toBe("missing");
  });
  it("không cho giờ tương lai (quá 5 phút)", () => {
    expect(checkReceivedAt("2026-10-07T10:03", now)).toBeNull();
    expect(checkReceivedAt("2026-10-07T10:30", now)).toBe("future");
    expect(checkReceivedAt("2026-10-06T23:59", now)).toBeNull();
  });
  it("giá trị ban đầu là giờ VN hiện tại, không phải giờ máy", () => {
    expect(nowForInput(now)).toBe("2026-10-07T10:00");
  });
});

describe("buildLateBody", () => {
  it("chỉ 5 khoá; đổi giờ VN sang ISO; mã đơn rỗng thì bỏ khoá; không có ghi chú", () => {
    const body = buildLateBody({ txn: " ft 1 ", amount: "350000", receivedAt: "2026-10-03T10:29", orderCode: "  ", ack: false });
    expect(body).toEqual({ bank_txn_id: "FT1", amount: "350000", received_at: "2026-10-03T03:29:00.000Z" });
    expect(Object.keys(body)).not.toContain("note");
  });
  it("có mã đơn + đã tick", () => {
    const body = buildLateBody({ txn: "FT1", amount: "1", receivedAt: "2026-10-03T10:29", orderCode: " SO-1 ", ack: true });
    expect(body.order_code).toBe("SO-1");
    expect(body.acknowledge_possible_duplicate).toBe(true);
  });
});

describe("đọc thân lỗi BE", () => {
  it("409 nghi trùng → khoản giống", () => {
    const err = new ApiError("x", 409, "LATE_PAYMENT_POSSIBLE_DUPLICATE", {
      similar_payment_id: 7,
      similar_bank_txn_id: "FT7",
      similar_received_at: "2026-10-03T03:00:00Z",
    });
    expect(similarOf(err)).toEqual({ id: 7, bank_txn_id: "FT7", received_at: "2026-10-03T03:00:00Z" });
    expect(similarOf(new ApiError("x", 409, "OTHER", {}))).toBeNull();
  });
  it("400 đơn Giữ chỗ → order_id; 400 trùng mã → existing_payment_id", () => {
    expect(bookedOrderIdOf(new ApiError("x", 400, "LATE_PAYMENT_ORDER_BOOKED", { order_id: 88 }))).toBe(88);
    expect(bookedOrderIdOf(new ApiError("x", 400, "BR-TT-18", {}))).toBeNull();
    expect(existingPaymentIdOf(new ApiError("x", 400, "BR-TT-03", { existing_payment_id: 37 }))).toBe(37);
  });
  it("nhãn nghi trùng", () => {
    expect(hasDuplicateWarning({ duplicate_warning: "Nghi trùng" })).toBe(true);
    expect(hasDuplicateWarning({ duplicate_warning: "  " })).toBe(false);
    expect(hasDuplicateWarning({})).toBe(false);
  });
});

describe("dòng thời gian khoản tiền: payment_recorded_late", () => {
  it("khoản MANUAL ORPHAN/UNMATCHED hiện 'Ghi tay tiền về muộn …' kèm tiền và mã GD", () => {
    const row = { received_at: "2026-10-03T03:29:00Z", resolved_at: null, resolved_by: null, source: "MANUAL", match_status: "ORPHAN", amount: "350000", bank_txn_id: "FT26100300001" };
    expect(isLateEntry(row)).toBe(true);
    expect(paymentTimeline(row).map((e) => e.label)).toEqual(["Ghi tay tiền về muộn 350.000 đ (mã GD FT26100300001)"]);
  });
  it("khoản webhook vẫn là 'Nhận khoản tiền'", () => {
    const row = { received_at: "2026-10-03T03:29:00Z", resolved_at: null, resolved_by: null, source: "WEBHOOK", match_status: "ORPHAN", amount: "1", bank_txn_id: "FT1" };
    expect(isLateEntry(row)).toBe(false);
    expect(paymentTimeline(row)[0].label).toBe("Nhận khoản tiền");
  });
});

// ---- Mock theo contract BE (mỗi test dùng mã GD riêng; kho mock nằm trong bộ nhớ) ----
const tok = (u: string) => `mock-token-${u}-${Date.now() + 1000}`;
const hoursAgoIso = (h: number) => new Date(Date.now() - h * 3600_000).toISOString();
function late(user: string, body: Record<string, unknown>) {
  return mockPaymentsApi({ method: "POST", path: "/api/sales/payments/record-late/", token: tok(user), body });
}
function orderCodeOf(status: string): { id: number; code: string } {
  const r = mockOrdersApi({ method: "GET", path: `/api/sales/orders/?status=${status}`, token: tok("loc") });
  const o = (r.body as { results: OrderListItem[] }).results[0];
  return { id: o.id, code: o.code };
}
const base = (txn: string, extra: Record<string, unknown> = {}) => ({ bank_txn_id: txn, amount: "350000", received_at: hoursAgoIso(1), ...extra });

describe("mock record-late (BR-TT-18)", () => {
  it("quyền: Quản lý / NV kho 403, chưa đăng nhập 401", () => {
    expect(late("ql1", base("FTQ1")).status).toBe(403);
    expect(late("kho1", base("FTQ1")).status).toBe(403);
    expect(mockPaymentsApi({ method: "POST", path: "/api/sales/payments/record-late/", token: null, body: base("FTQ1") }).status).toBe(401);
  });

  it("LP-AC1: đơn Tự huỷ → 201 ORPHAN gắn đơn; mã GD chuẩn hoá; đơn không đổi", () => {
    const o = orderCodeOf("AUTO_CANCELLED");
    const r = late("loc", base(" ft a1 ", { order_code: o.code.toLowerCase(), note: "GHI-CHU-TU-DO gọi 0900000321" }));
    expect(r.status).toBe(201);
    const body = r.body as RecordLatePaymentResult;
    expect(body.duplicate).toBe(false);
    expect(body.payment).toMatchObject({ bank_txn_id: "FTA1", match_status: "ORPHAN", source: "MANUAL", resolution_status: "OPEN", duplicate_warning: "" });
    expect(body.payment.order?.code).toBe(o.code);
    expect(body.payment.order?.status).toBe("AUTO_CANCELLED");
    expect(body.payment.available_actions).toContain("refund");
    expect(JSON.stringify(r.body)).not.toContain("GHI-CHU");
  });

  it("LP-AC3: không mã đơn → UNMATCHED, có attach_to_order + refund", () => {
    const r = late("loc", base("FTU1", { amount: "181000" }));
    expect(r.status).toBe(201);
    const p = (r.body as RecordLatePaymentResult).payment;
    expect(p.match_status).toBe("UNMATCHED");
    expect(p.order).toBeNull();
    expect(p.available_actions).toEqual(["attach_to_order", "refund"]);
  });

  it("LP-AC4: gửi lại đúng khoản → 200 duplicate:true; LP-AC5: cùng mã khác tiền → 400 BR-TT-03 kèm id", () => {
    const first = late("loc", base("FTD1", { amount: "182000" }));
    const again = late("loc", base("FTD1", { amount: "182000" }));
    expect(again.status).toBe(200);
    expect(again.body).toMatchObject({ duplicate: true, payment: { id: (first.body as RecordLatePaymentResult).payment.id } });
    const other = late("loc", base("FTD1", { amount: "999000" }));
    expect(other.status).toBe(400);
    expect(other.body).toMatchObject({ code: "BR-TT-03", existing_payment_id: (first.body as RecordLatePaymentResult).payment.id });
  });

  it("LP-AC6/7/8: lỗi theo khoá ô", () => {
    expect(late("loc", base("", {})).body).toMatchObject({ code: "BR-TT-18", bank_txn_id: expect.any(String) });
    expect(late("loc", base("Nguyễn A")).body).toMatchObject({ code: "BR-TT-18", bank_txn_id: expect.any(String) });
    for (const amount of ["0", "-1", "abc", "", "0.004", "1000000000000"]) {
      const r = late("loc", { ...base("FTE1"), amount });
      expect([r.status, (r.body as Record<string, unknown>).code]).toEqual([400, "BR-TT-18"]);
      expect((r.body as Record<string, unknown>).amount).toEqual(expect.any(String));
    }
    expect(late("loc", { ...base("FTE1"), received_at: "không phải ngày" }).body).toMatchObject({ received_at: expect.any(String) });
    expect(late("loc", { ...base("FTE1"), received_at: new Date(Date.now() + 3600_000).toISOString() }).body).toMatchObject({ received_at: expect.any(String) });
  });

  it("LP-AC9/10: mã đơn không có / Giữ chỗ (kèm order_id) / đã thanh toán", () => {
    expect(late("loc", base("FTO1", { order_code: "SO-KHONG-CO" })).body).toMatchObject({ code: "LATE_PAYMENT_ORDER_NOT_FOUND", order_code: expect.any(String) });
    const booked = orderCodeOf("BOOKED");
    expect(late("loc", base("FTO1", { order_code: booked.code })).body).toMatchObject({ code: "LATE_PAYMENT_ORDER_BOOKED", order_id: booked.id });
    const paid = orderCodeOf("PAID");
    expect(late("loc", base("FTO1", { order_code: paid.code })).body).toMatchObject({ code: "LATE_PAYMENT_ORDER_PAID" });
  });

  it("LP-AC11 + LP-AC13: nghi trùng 409 → ack 201 có nhãn → phiếu hoàn bắt cờ xác nhận", () => {
    const a = late("loc", base("FTN1", { amount: "123000" }));
    expect(a.status).toBe(201);
    const b = late("loc", base("FTN2", { amount: "123000" }));
    expect(b.status).toBe(409);
    expect(b.body).toMatchObject({ code: "LATE_PAYMENT_POSSIBLE_DUPLICATE", similar_bank_txn_id: "FTN1", similar_payment_id: (a.body as RecordLatePaymentResult).payment.id });
    const c = late("loc", base("FTN2", { amount: "123000", acknowledge_possible_duplicate: true }));
    expect(c.status).toBe(201);
    const p = (c.body as RecordLatePaymentResult).payment as PaymentQueueItem;
    expect(p.duplicate_warning).not.toBe("");

    const refund = (extra: Record<string, unknown>) =>
      mockRefundsApi({
        method: "POST",
        path: "/api/sales/refunds/create/",
        token: tok("loc"),
        body: { payment_transaction: p.id, amount: "123000", reason: "Khách chuyển nhầm", request_id: "11111111-1111-4111-8111-111111111111", ...extra },
      });
    const blocked = refund({});
    expect(blocked.status).toBe(409);
    expect(blocked.body).toMatchObject({ code: "PAYMENT_DUPLICATE_WARNING", detail: p.duplicate_warning });
    expect(refund({ acknowledge_duplicate_warning: true }).status).toBe(201);
  });
});

describe("mock record-late: giờ nhận tiền (Lô 17b-BE, TL15-L2)", () => {
  const rec = (received_at: string) =>
    mockPaymentsApi({ method: "POST", path: "/api/sales/payments/record-late/", body: { bank_txn_id: `FTX${Math.round(Math.random() * 1e9)}`, amount: "412345", received_at }, token: `mock-token-loc-${Date.now() + 60_000}` });
  it("chỉ có ngày → 400 BR-TT-18 khoá received_at; quá 400 ngày → 400; hôm qua → 200", () => {
    const dateOnly = rec("2026-10-03");
    expect(dateOnly.status).toBe(400);
    expect(dateOnly.body).toMatchObject({ code: "BR-TT-18", received_at: expect.stringContaining("gồm cả ngày và giờ") });
    const old = rec(new Date(Date.now() - 401 * 86_400_000).toISOString());
    expect(old.status).toBe(400);
    expect(old.body).toMatchObject({ code: "BR-TT-18", received_at: expect.stringContaining("cũ quá 400 ngày") });
    expect(rec(new Date(Date.now() - 86_400_000).toISOString()).status).toBe(201);
  });
});

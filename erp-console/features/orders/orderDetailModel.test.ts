import { describe, expect, it } from "vitest";
import {
  BLOCKED_CANCEL_BOOKED,
  BLOCKED_CANCEL_DELIVERING,
  confirmPaymentToast,
  customerLinkHref,
  effectiveOrderStatus,
  holdInfo,
  orderActionPlan,
  orderPath,
  orderTimeline,
  paymentActionPlan,
  paymentTimeline,
  refundActionPlan,
  refundPath,
  refundTimeline,
} from "./orderDetailModel";

const plan = (status: string, actions: string[], extra: { deliveryStatus?: string | null; canCancel?: boolean; canViewAudit?: boolean } = {}) =>
  orderActionPlan({ status, actions, deliveryStatus: extra.deliveryStatus ?? null, canCancel: extra.canCancel ?? true, canViewAudit: extra.canViewAudit ?? true });

describe("orderActionPlan (ED-09-AC3/AC4)", () => {
  it("BOOKED: nút chính Xác nhận đã nhận tiền; Huỷ đơn mờ kèm lý do", () => {
    const p = plan("BOOKED", ["confirm_payment"]);
    expect(p.primary?.label).toBe("Xác nhận đã nhận tiền");
    const cancel = p.menu.find((m) => m.key === "cancel");
    expect(cancel?.blockedReason).toBe(BLOCKED_CANCEL_BOOKED);
  });
  it("Quản lý (không confirm_payment, không quyền huỷ): không có nút chính, không có mục Huỷ đơn", () => {
    const p = plan("BOOKED", [], { canCancel: false });
    expect(p.primary).toBeNull();
    expect(p.menu.some((m) => m.key === "cancel")).toBe(false);
  });
  it("PAID và PROCESSING Soạn hàng: Huỷ đơn là nút chính màu đỏ", () => {
    for (const [st, d] of [["PAID", null], ["PROCESSING", "PREPARING"]] as const) {
      const p = plan(st, ["cancel"], { deliveryStatus: d });
      expect(p.primary).toMatchObject({ key: "cancel", label: "Huỷ đơn", danger: true });
    }
  });
  it("PROCESSING Đang giao: không nút chính, Huỷ đơn mờ kèm lý do báo giao thất bại trước", () => {
    const p = plan("PROCESSING", [], { deliveryStatus: "DELIVERING" });
    expect(p.primary).toBeNull();
    expect(p.menu.find((m) => m.key === "cancel")?.blockedReason).toBe(BLOCKED_CANCEL_DELIVERING);
  });
  it("COMPLETED: nút chính Lập phiếu hoàn", () => {
    expect(plan("COMPLETED", ["create_refund"]).primary?.label).toBe("Lập phiếu hoàn");
  });
  it("AUTO_CANCELLED tiền về muộn: Xác nhận đã nhận tiền; không có mục Huỷ đơn mờ", () => {
    const p = plan("AUTO_CANCELLED", ["confirm_payment"]);
    expect(p.primary?.key).toBe("confirm_payment");
    expect(p.menu.some((m) => m.key === "cancel")).toBe(false);
  });
  it("luôn có Sao chép mã đơn; Xem nhật ký chỉ khi có quyền", () => {
    expect(plan("PAID", ["cancel"]).menu.map((m) => m.key)).toEqual(expect.arrayContaining(["copy_code", "audit"]));
    expect(plan("PAID", ["cancel"], { canViewAudit: false }).menu.some((m) => m.key === "audit")).toBe(false);
    expect(plan("PAID", [], { canViewAudit: false }).menu.some((m) => m.key === "copy_code")).toBe(true);
  });
});

describe("orderPath", () => {
  it("đơn huỷ kết thúc bằng Đã huỷ sau bước đã qua", () => {
    expect(orderPath({ status: "AUTO_CANCELLED" })).toEqual({ current: "BOOKED", badEnd: { label: "Đã huỷ", after: "BOOKED" } });
    expect(orderPath({ status: "CANCELLED", deliveryStatus: "PREPARING" }).badEnd?.after).toBe("PREPARING");
  });
  it("đơn đang đi: bước theo trạng thái giao", () => {
    expect(orderPath({ status: "PROCESSING", deliveryStatus: "DELIVERING" }).current).toBe("DELIVERING");
    expect(orderPath({ status: "COMPLETED" })).toEqual({ current: "COMPLETED", badEnd: null });
  });
});

describe("giữ chỗ (ED-09-AC5)", () => {
  const until = "2026-10-01T10:00:00Z";
  const end = Date.parse(until);
  it("đếm lùi mm:ss, và mốc tự huỷ là trường riêng", () => {
    const h = holdInfo("BOOKED", until, end - (2 * 60 + 5) * 1000);
    expect(h).toMatchObject({ over: false, left: "02:05", until });
  });
  it("hết giờ: over và chip đổi sang Đã huỷ mà không cần tải lại", () => {
    expect(holdInfo("BOOKED", until, end + 1)?.over).toBe(true);
    expect(effectiveOrderStatus("BOOKED", until, end + 1)).toBe("AUTO_CANCELLED");
    expect(effectiveOrderStatus("BOOKED", until, end - 1000)).toBe("BOOKED");
  });
  it("trạng thái khác BOOKED hoặc thiếu mốc: không có giữ chỗ", () => {
    expect(holdInfo("PAID", until, 0)).toBeNull();
    expect(holdInfo("BOOKED", null, 0)).toBeNull();
    expect(effectiveOrderStatus("PAID", until, end + 1)).toBe("PAID");
  });
});

describe("customerLinkHref (ED-09-AC8)", () => {
  it("chỉ khi có id khách và có quyền", () => {
    expect(customerLinkHref(7, true)).toBe("/customers/detail/?id=7");
    expect(customerLinkHref(7, false)).toBeNull();
    expect(customerLinkHref(undefined, true)).toBeNull();
  });
});

describe("khoản tiền và phiếu hoàn", () => {
  it("paymentActionPlan: thao tác đầu là nút chính, rỗng (Quản lý) thì không nút", () => {
    expect(paymentActionPlan(["attach_to_order", "refund"]).primary?.label).toBe("Gắn vào đơn");
    expect(paymentActionPlan(["confirm_order", "refund"]).menu.map((m) => m.label)).toEqual(["Lập phiếu hoàn"]);
    expect(paymentActionPlan([])).toEqual({ primary: null, menu: [] });
  });
  it("refundActionPlan: Xác nhận / Chuyển lại chính, Báo chuyển thất bại trong …", () => {
    expect(refundActionPlan(["confirm", "mark_failed"])).toMatchObject({ primary: { label: "Xác nhận đã hoàn tiền" }, menu: [{ key: "mark_failed" }] });
    expect(refundActionPlan(["retry"]).primary?.label).toBe("Chuyển lại");
    expect(refundActionPlan([])).toEqual({ primary: null, menu: [] });
  });
  it("refundPath: Thất bại kết thúc đỏ", () => {
    expect(refundPath("FAILED").badEnd?.label).toBe("Thất bại");
    expect(refundPath("REFUNDED").current).toBe("REFUNDED");
  });
});

describe("dòng thời gian", () => {
  it("đơn: dùng timeline của BE, mới nhất trước", () => {
    const t = orderTimeline({
      timeline: [
        { at: "2026-10-01T01:00:00Z", kind: "order_placed", label: "A", actor_display: "Hệ thống" },
        { at: "2026-10-01T03:00:00Z", kind: "payment_received", label: "B" },
      ],
      created_at: undefined,
      invoice: null,
      payments: [],
    });
    expect(t.map((e) => e.label)).toEqual(["B", "A"]);
    expect(t[1].actor).toBe("Hệ thống");
  });
  it("đơn: BE cũ không có timeline thì ghép từ mốc giờ", () => {
    const t = orderTimeline({
      created_at: "2026-10-01T01:00:00Z",
      invoice: { id: 1, code: "HD", issued_at: "2026-10-01T02:00:00Z" },
      payments: [{ id: 1, bank_txn_id: "X", amount: "1", match_status: "MATCHED", received_at: "2026-10-01T01:30:00Z" }],
    });
    expect(t).toHaveLength(3);
    expect(t[0].at).toBe("2026-10-01T02:00:00Z");
  });
  it("khoản tiền và phiếu hoàn: chỉ lấy tên người xử lý khi là chuỗi", () => {
    expect(paymentTimeline({ received_at: "2026-10-01T01:00:00Z", resolved_at: "2026-10-01T02:00:00Z", resolved_by: 5 }).every((e) => !e.actor)).toBe(true);
    const r = refundTimeline({ created_at: "2026-10-01T01:00:00Z", confirmed_at: "2026-10-01T02:00:00Z", created_by: "loc", confirmed_by: null });
    expect(r.map((e) => e.label)).toEqual(["Xác nhận đã hoàn tiền", "Lập phiếu hoàn"]);
    expect(r[1].actor).toBe("loc");
  });
});

describe("confirmPaymentToast", () => {
  it("PAID = thành công, không có địa chỉ trong câu", () => {
    const t = confirmPaymentToast({ result: "PAID", duplicate: false, order_status: "PAID" }, "SO261001-AB12CD");
    expect(t.kind).toBe("success");
    expect(t.message).toContain("SO261001-AB12CD");
  });
  it("thiếu / mồ côi / trùng = cảnh báo", () => {
    expect(confirmPaymentToast({ result: "UNDERPAID", duplicate: false, order_status: "BOOKED", paid_total: "100000", missing: "50000" }, "X").kind).toBe("warn");
    expect(confirmPaymentToast({ result: "ORPHAN", duplicate: false, order_status: "AUTO_CANCELLED" }, "X").kind).toBe("warn");
    expect(confirmPaymentToast({ result: "PAID", duplicate: true, order_status: "PAID" }, "X").kind).toBe("warn");
  });
  it("chuyển thừa ghi thêm số thừa", () => {
    expect(confirmPaymentToast({ result: "PAID", duplicate: false, order_status: "PAID", overpaid_amount: "10000" }, "X").message).toContain("10.000");
  });
});

import { describe, expect, it } from "vitest";
import { mockDeliveryNotes, mockPostDeliveryNoteStatus } from "./mock";
import { completeToast, isOrderCancelledError, orderCancelledMessage, ORDER_CANCELLED_TEXT } from "./deliveryUi";
import { ApiError } from "@/shared/lib/http";

// W37 S1/S2 phía mock Giao hàng: giao xong trả `order_status` theo BR-BH-18; phiếu/đơn đã huỷ trả 400 BR-GH-24.
const req = (path: string, body: unknown) => ({ method: "POST" as const, path, body, token: `mock-token-ql1-${Date.now() + 1000}` });
const post = (id: number, body: Record<string, unknown>) => mockPostDeliveryNoteStatus(req(`/api/delivery/notes/${id}/status/`, body));
type Body = { status: string; order_status?: string | null; code?: string; detail?: string; current_status?: string };

describe("mock status: order_status (S1)", () => {
  it("giao xong phiếu duy nhất của đơn → order_status COMPLETED", () => {
    const res = post(33, { to_status: "COMPLETED", from_status: "DELIVERING" });
    expect(res.status).toBe(200);
    expect((res.body as Body).order_status).toBe("COMPLETED");
  });

  it("còn phiếu khác của cùng đơn chưa xong → order_status PROCESSING", () => {
    const a = mockDeliveryNotes().find((n) => n.id === 36)!;
    const extra = { ...a, id: 990, code: "GH-TEST-0990", status: "DELIVERING" as const, order: a.order };
    mockDeliveryNotes().push(extra);
    try {
      const res = post(36, { to_status: "COMPLETED", from_status: "DELIVERING" });
      expect((res.body as Body).order_status).toBe("PROCESSING");
    } finally {
      mockDeliveryNotes().splice(mockDeliveryNotes().indexOf(extra), 1);
    }
  });

  it("báo thất bại: đơn vẫn PROCESSING", () => {
    const res = post(39, { to_status: "FAILED", from_status: "DELIVERING", failure_reason: "NOT_MET" });
    expect(res.status).toBe(200);
    expect((res.body as Body).order_status).toBe("PROCESSING");
  });
});

describe("mock status: BR-GH-24 (S2)", () => {
  it("phiếu CANCELLED: giao xong, nhận đi giao, báo thất bại đều 400 BR-GH-24, không phải 409", () => {
    for (const body of [
      { to_status: "COMPLETED", from_status: "DELIVERING" },
      { to_status: "DELIVERING", from_status: "READY" },
      { to_status: "FAILED", from_status: "DELIVERING", failure_reason: "NOT_MET" },
    ]) {
      const res = post(47, body);
      expect(res.status).toBe(400);
      expect(res.body).toMatchObject({ code: "BR-GH-24", detail: "Đơn đã huỷ — mang hàng về kho.", current_status: "CANCELLED" });
    }
  });
});

describe("deliveryUi: BR-GH-24 và toast", () => {
  it("nhận theo code, không theo HTTP status", () => {
    expect(isOrderCancelledError(new ApiError("x", 400, "BR-GH-24"))).toBe(true);
    expect(isOrderCancelledError(new ApiError("x", 409, "STALE_STATE"))).toBe(false);
    expect(isOrderCancelledError(new ApiError("x", 400))).toBe(false);
  });
  it("hiện đúng detail của BE, thiếu thì dùng câu chuẩn", () => {
    expect(orderCancelledMessage(new ApiError("Đơn đã huỷ — mang hàng về kho.", 400, "BR-GH-24"))).toBe(ORDER_CANCELLED_TEXT);
    expect(orderCancelledMessage(null)).toBe(ORDER_CANCELLED_TEXT);
  });
  it("toast: order_status COMPLETED thì nói đơn đã hoàn tất", () => {
    expect(completeToast("COMPLETED", "Đã giao xong.")).toBe("Đã giao xong. Đơn đã hoàn tất.");
    expect(completeToast("PROCESSING", "Đã giao xong.")).toBe("Đã giao xong.");
    expect(completeToast(undefined, "Đã giao xong.")).toBe("Đã giao xong.");
  });
  it("BR-GH-24 không nằm trong CONFLICT_CODES (không bật ConflictBanner)", async () => {
    const { isConflictError } = await import("@/shared/ui/form/useSubmit");
    expect(isConflictError(new ApiError("x", 400, "BR-GH-24"))).toBe(false);
  });
});

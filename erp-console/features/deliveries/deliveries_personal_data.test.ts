import { describe, it, expect } from "vitest";
import { mockGetDeliveryNoteDetail, mockListDeliveryNotes } from "./mock";
import type { DeliveryListResponse, DeliveryNoteDetail } from "./types";

// SR-PII-02: phiếu COMPLETED của giao1 đã quá 7 ngày -> BE trả null ở customer_name/address/note/recipient_name.
// Phiếu 40 trong mock là phiếu như vậy; phiếu 41 (giao1, hoàn tất hôm qua) vẫn đủ dữ liệu.
const OLD_ID = 40;

function tokenFor(username: string): string {
  return `mock-token-${username}-${Date.now() + 1000}`;
}
function list(username: string) {
  const res = mockListDeliveryNotes({ url: "/api/delivery/notes/?status=COMPLETED", token: tokenFor(username) });
  return (res.body as DeliveryListResponse).results;
}

describe("Deliveries mock: dữ liệu khách của NV giao theo thời hạn 7 ngày", () => {
  it("giao1: phiếu cũ có customer_name/address/note = null, mã phiếu và số kg vẫn có", () => {
    const old = list("giao1").find((n) => n.id === OLD_ID);
    expect(old).toBeDefined();
    expect(old!.customer_name).toBeNull();
    expect(old!.address).toBeNull();
    expect(old!.note).toBeNull();
    expect(old!.code).toBeTruthy();
    expect(old!.total_kg).toBeTruthy();
  });

  it("giao1: chi tiết phiếu cũ có recipient_name = null", () => {
    const res = mockGetDeliveryNoteDetail({ url: `/api/delivery/notes/${OLD_ID}/`, token: tokenFor("giao1") });
    const body = res.body as DeliveryNoteDetail;
    expect(body.customer_name).toBeNull();
    expect(body.recipient_name).toBeNull();
  });

  it("giao1: phiếu hoàn tất hôm qua vẫn đủ dữ liệu; chỉ thấy phiếu gán cho mình", () => {
    const rows = list("giao1");
    const recent = rows.find((n) => n.id === 41);
    expect(recent?.customer_name).toBe("Khách Thử I");
    expect(recent?.address).toBeTruthy();
    expect(rows.every((n) => n.assigned_to === 4)).toBe(true);
  });

  it("Chủ vẫn thấy đủ dữ liệu của phiếu cũ", () => {
    const old = list("loc").find((n) => n.id === OLD_ID);
    expect(old).toBeDefined();
    expect(old!.customer_name).toBeTruthy();
    expect(old!.address).toBeTruthy();
  });

  it("cs2 (cskh + nv_giao, không có chủ/quản lý/NV kho): phiếu cũ bị ẩn, phiếu mới đủ, chỉ thấy phiếu gán cho mình", () => {
    const rows = list("cs2");
    const old = rows.find((n) => n.id === 42);
    expect(old?.customer_name).toBeNull();
    expect(old?.address).toBeNull();
    expect(rows.find((n) => n.id === 43)?.customer_name).toBe("Khách Thử L");
    expect(rows.every((n) => n.assigned_to === 12)).toBe(true);
  });

  it("kho1 (nv_kho + nv_giao) có đủ phạm vi: thấy mọi phiếu và dữ liệu khách của phiếu cũ", () => {
    const rows = list("kho1");
    expect(rows.find((n) => n.id === OLD_ID)?.customer_name).toBeTruthy();
    expect(rows.some((n) => n.assigned_to !== 3)).toBe(true);
  });
});

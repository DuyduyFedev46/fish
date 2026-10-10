// PV-13-AC2: mốc nửa đêm theo giờ VN cho câu "Phiếu tạo từ hôm trước".
import { describe, expect, it } from "vitest";
import { isOwnReceiptFromEarlierDay } from "./receiptScope";

// 23:50 VN ngày 09/10 = 16:50Z ngày 09/10. 00:10 VN ngày 10/10 = 17:10Z ngày 09/10.
const CREATED = "2026-10-09T16:50:00Z";
const row = { created_by: 4, created_at: CREATED };

describe("isOwnReceiptFromEarlierDay", () => {
  it("phiếu tạo 23:50 hôm trước, xem lúc 00:10 hôm nay (giờ VN) → true", () => {
    expect(isOwnReceiptFromEarlierDay(row, 4, new Date("2026-10-09T17:10:00Z"))).toBe(true);
  });
  it("cùng ngày VN (xem lúc 23:55 cùng ngày) → false", () => {
    expect(isOwnReceiptFromEarlierDay(row, 4, new Date("2026-10-09T16:55:00Z"))).toBe(false);
  });
  it("ngày UTC khác nhưng cùng ngày VN → false", () => {
    // tạo 06:00 VN = 23:00Z hôm trước theo UTC; xem 20:00 VN cùng ngày VN
    expect(isOwnReceiptFromEarlierDay({ created_by: 4, created_at: "2026-10-09T23:00:00Z" }, 4, new Date("2026-10-10T13:00:00Z"))).toBe(false);
  });
  it("phiếu của người khác → false dù từ hôm trước", () => {
    expect(isOwnReceiptFromEarlierDay(row, 9, new Date("2026-10-09T17:10:00Z"))).toBe(false);
  });
  it("thiếu người lập hoặc thiếu me → false", () => {
    expect(isOwnReceiptFromEarlierDay({ created_by: null, created_at: CREATED }, 4, new Date("2026-10-11T00:00:00Z"))).toBe(false);
    expect(isOwnReceiptFromEarlierDay(row, undefined, new Date("2026-10-11T00:00:00Z"))).toBe(false);
  });
  it("ngày tạo không hợp lệ → false", () => {
    expect(isOwnReceiptFromEarlierDay({ created_by: 4, created_at: "" }, 4)).toBe(false);
  });
});

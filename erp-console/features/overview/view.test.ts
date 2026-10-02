// ED-08: phần thuần của màn Tổng quan.
import { describe, expect, it } from "vitest";
import { aiZoneOf, attentionRows, expiryLine, nearExpiryLabel, orderLine, revenueLabel, summarizeProposals, zonesText } from "./view";

describe("nhãn thẻ", () => {
  it("Doanh thu theo ngày Việt Nam của mốc dữ liệu", () => {
    expect(revenueLabel("2026-10-01T02:42:00Z")).toBe("Doanh thu 01/10/2026");
    // 17:30 UTC ngày 30/09 đã là 00:30 ngày 01/10 ở Việt Nam
    expect(revenueLabel("2026-09-30T17:30:00Z")).toBe("Doanh thu 01/10/2026");
  });
  it("thiếu hoặc sai mốc → hôm nay", () => {
    expect(revenueLabel(null)).toBe("Doanh thu hôm nay");
    expect(revenueLabel("không phải ngày")).toBe("Doanh thu hôm nay");
  });
  it("Lô cận hạn ghi số ngày khi BE trả", () => {
    expect(nearExpiryLabel(14)).toBe("Lô cận hạn (14 ngày tới)");
    expect(nearExpiryLabel(null)).toBe("Lô cận hạn");
  });
});

describe("attentionRows", () => {
  it("chỉ lấy khoá có số > 0, đúng thứ tự và đường dẫn", () => {
    const rows = attentionRows({ expired_batches_open: 2, confirmation_queue_waiting: 0, refund_calls_open: 4, labels_to_void: 1 });
    expect(rows.map((r) => r.key)).toEqual(["expired_batches_open", "refund_calls_open", "labels_to_void"]);
    expect(rows[0]).toMatchObject({ text: "2 lô quá hạn còn tồn", href: "/inventory/?status=EXPIRED", crit: true });
    expect(rows[1].crit).toBe(false);
  });
  it("không có khoá nào (người không có quyền) → rỗng", () => {
    expect(attentionRows({})).toEqual([]);
  });
});

describe("expiryLine", () => {
  it("số ngày còn lại", () => {
    expect(expiryLine(4)).toBe("Còn 4 ngày tới hạn");
    expect(expiryLine(0)).toBe("Hết hạn hôm nay");
  });
});

describe("đề xuất AI theo khu", () => {
  it("map loại chứng từ về khu", () => {
    expect(aiZoneOf("purchasing.purchasereceipt")).toBe("purchasing");
    expect(aiZoneOf("sales.paymenttransaction")).toBe("orders");
    expect(aiZoneOf("inventory.batch")).toBe("inventory");
    expect(aiZoneOf("catalog.item")).toBeNull();
  });
  it("gom số theo khu, tổng gồm cả loại ngoài khu", () => {
    const s = summarizeProposals({ "purchasing.purchasereceipt": 1, "sales.salesorder": 1, "inventory.batch": 1, "catalog.item": 2 });
    expect(s.total).toBe(5);
    expect(zonesText(s)).toBe("Mua hàng 1 · Đơn & tiền 1 · Kho & lô 1");
  });
  it("rỗng hoặc số xấu → tổng 0, không khu", () => {
    expect(summarizeProposals({})).toEqual({ total: 0, zones: [] });
    expect(summarizeProposals({ "inventory.batch": -1, "sales.refund": Number.NaN }).total).toBe(0);
  });
});

describe("orderLine", () => {
  const now = Date.parse("2026-10-01T03:00:00Z");
  it("đơn Giữ chỗ còn hạn: có mốc đếm ngược, không có lý do", () => {
    expect(orderLine("BOOKED", "2026-10-01T03:10:00Z", now)).toEqual({ status: "BOOKED", reason: null, holdUntil: "2026-10-01T03:10:00Z" });
  });
  it("đơn Giữ chỗ quá mốc → Đã huỷ ngay + lý do, hết đếm ngược", () => {
    expect(orderLine("BOOKED", "2026-10-01T02:50:00Z", now)).toEqual({ status: "AUTO_CANCELLED", reason: "Hết giờ giữ chỗ", holdUntil: null });
  });
  it("đơn đã huỷ sẵn từ BE cũng có lý do; đơn khác không có", () => {
    expect(orderLine("AUTO_CANCELLED", null, now).reason).toBe("Hết giờ giữ chỗ");
    expect(orderLine("PAID", null, now)).toEqual({ status: "PAID", reason: null, holdUntil: null });
  });
});

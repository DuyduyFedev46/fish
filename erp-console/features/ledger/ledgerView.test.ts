import { describe, expect, it } from "vitest";
import { actorOf, badDateRange, batchFromSearch, filterLedgerRows, signedKg } from "./ledgerView";
import type { LedgerEntry } from "./types";

const row = (over: Partial<LedgerEntry>): LedgerEntry => ({
  id: 1,
  batch: 1,
  batch_code: "L0908-CT00",
  item: 1,
  item_name: "Cá thu",
  warehouse: 1,
  warehouse_name: "Kho lạnh Bến Đá",
  movement_type: "SALE",
  type_label: "Bán ra",
  qty_change: "-3.500",
  balance_after: "16.500",
  reference: "order:5",
  reference_display: "DH-0005",
  reference_link: { kind: "order", id: 5 },
  created_at: "2026-10-01T03:00:00Z",
  created_by: null,
  created_by_name: "",
  ...over,
});

describe("signedKg", () => {
  it("nhập có dấu +, xuất có dấu trừ, số lẻ theo kiểu Việt", () => {
    expect(signedKg("14.200")).toBe("+14,2 kg");
    expect(signedKg("-3.500")).toBe("-3,5 kg");
    expect(signedKg("abc")).toBe("—");
  });
});

describe("actorOf", () => {
  it("không có người làm → Hệ thống", () => {
    expect(actorOf(row({}))).toBe("Hệ thống");
    expect(actorOf(row({ created_by_name: "Hà" }))).toBe("Hà");
  });
});

describe("bộ lọc", () => {
  it("?batch= chỉ nhận số nguyên dương", () => {
    expect(batchFromSearch("?batch=12")).toBe("12");
    for (const bad of ["?batch=abc", "?batch=0", "?batch=-1", "?batch=1;drop", ""]) expect(batchFromSearch(bad)).toBe("");
  });
  it("khoảng ngày sai thứ tự", () => {
    expect(badDateRange("2026-10-02", "2026-10-01")).toBe(true);
    expect(badDateRange("2026-10-01", "2026-10-01")).toBe(false);
    expect(badDateRange("", "2026-10-01")).toBe(false);
  });
  it("tìm không phân biệt dấu trên các dòng đã tải", () => {
    const rows = [row({}), row({ id: 2, item_name: "Mực ống", batch_code: "L0921-MU03", created_by_name: "Hà" })];
    expect(filterLedgerRows(rows, "muc").map((r) => r.id)).toEqual([2]);
    expect(filterLedgerRows(rows, "dh-0005").map((r) => r.id)).toEqual([1, 2]);
    expect(filterLedgerRows(rows, "")).toHaveLength(2);
  });
});

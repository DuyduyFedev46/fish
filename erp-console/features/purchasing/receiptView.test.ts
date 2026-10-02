import { describe, expect, it } from "vitest";
import type { Me } from "@/features/auth/types";
import { cancelBlockReason, canCancelReceipt, filterReceiptRows, idFromSearch, nextReceiptStep, receiptAbility, receiptDoneLabels, receiptPathOf, receiptTotals } from "./receiptView";
import type { ReceiptDetail, ReceiptRow } from "./types";

const me = (over: Partial<Me>): Me => ({
  id: 7,
  username: "u",
  display_name: "U",
  phone: "",
  groups: [],
  permissions: [],
  can_view_cost: false,
  can_view_profit: false,
  home: "dashboard",
  ...over,
});

const row = (over: Partial<ReceiptRow>): ReceiptRow => ({
  id: 1,
  code: "PR-1",
  supplier: 1,
  supplier_name: "Ghe Tư Hải",
  warehouse: 1,
  warehouse_name: "Kho lạnh Bến Đá",
  received_date: "2026-10-01",
  status: "SUBMITTED",
  status_label: "Đã ghi nhận",
  created_by: 7,
  created_by_name: "",
  created_at: "2026-10-01T01:00:00Z",
  note: "",
  items_summary: "Cá thu",
  line_count: 1,
  total_qty: "10.000",
  batch_codes: ["THU-261001-1"],
  invoice: null,
  ...over,
});

describe("receiptPathOf", () => {
  it("phiếu huỷ = kết thúc xấu sau Nháp", () => {
    expect(receiptPathOf("CANCELLED")).toEqual({ current: "DRAFT", badEnd: { label: "Đã huỷ", after: "DRAFT" } });
    expect(receiptPathOf("SUBMITTED")).toEqual({ current: "SUBMITTED", badEnd: null });
  });
});

describe("receiptAbility", () => {
  it("giá mua, chi phí chỉ khi can_view_cost", () => {
    const owner = receiptAbility(me({ can_view_cost: true, permissions: ["purchasing.view_purchasecost", "purchasing.add_purchasecost", "purchasing.add_purchaseinvoice"] }));
    expect(owner.viewCost && owner.viewCosts && owner.addCost && owner.addInvoice).toBe(true);
    const manager = receiptAbility(me({ permissions: ["purchasing.view_purchaseinvoice", "purchasing.add_purchasereceipt"] }));
    expect(manager.viewCost).toBe(false);
    expect(manager.viewCosts).toBe(false);
    expect(manager.addCost).toBe(false);
    expect(manager.viewInvoices).toBe(true);
    expect(manager.addInvoice).toBe(false);
  });
  it("có quyền thêm chi phí mà không có can_view_cost vẫn không mở form", () => {
    expect(receiptAbility(me({ permissions: ["purchasing.add_purchasecost"] })).addCost).toBe(false);
  });
});

describe("canCancelReceipt", () => {
  const perms = ["purchasing.change_purchasereceipt"];
  it("người lập được huỷ phiếu của mình", () => {
    expect(canCancelReceipt(me({ permissions: perms, groups: ["warehouse_staff"] }), row({ created_by: 7 }))).toBe(true);
  });
  it("NV kho không huỷ phiếu người khác; Quản lý/Chủ thì được", () => {
    expect(canCancelReceipt(me({ permissions: perms, groups: ["warehouse_staff"] }), row({ created_by: 1 }))).toBe(false);
    expect(canCancelReceipt(me({ permissions: perms, groups: ["manager"] }), row({ created_by: 1 }))).toBe(true);
    expect(canCancelReceipt(me({ permissions: perms, groups: ["owner"] }), row({ created_by: 1 }))).toBe(true);
  });
  it("thiếu quyền change → không", () => {
    expect(canCancelReceipt(me({ permissions: [], groups: ["manager"] }), row({ created_by: 7 }))).toBe(false);
  });
});

describe("cancelBlockReason", () => {
  const detail = (over: Partial<ReceiptDetail>): ReceiptDetail => ({ ...row({}), lines: [], ...over });
  it("khớp luật chặn của BE", () => {
    expect(cancelBlockReason(detail({}))).toBeUndefined();
    expect(cancelBlockReason(detail({ status: "CANCELLED" }))).toBe("Phiếu đã huỷ.");
    expect(cancelBlockReason(detail({ invoice: { id: 3 } }))).toBe("Phiếu đã có hoá đơn mua.");
    expect(
      cancelBlockReason(
        detail({ costs: [{ id: 1, cost_type: "ICE", cost_type_label: "Đá", allocation_method: "BY_QTY", allocation_method_label: "Theo số kg", incurred_date: "2026-10-01", amount: "1", allocated_amount: "1", batch_count: 1 }] }),
      ),
    ).toBe("Phiếu đã có chi phí mua chia vào lô.");
    const moved = detail({
      lines: [{ id: 1, item: 1, item_code: "THU", item_name: "Cá thu", qty: "1", shelf_life_days: 5, batch: 2, batch_code: "THU-1", batch_status: "SELLING", expiry_date: null }],
    });
    expect(cancelBlockReason(moved)).toBe("Lô THU-1 đã đổi trạng thái, không còn Nháp.");
  });
});

describe("nextReceiptStep / receiptDoneLabels", () => {
  const can = { submit: true, addInvoice: true };
  it("Nháp → ghi nhận; Đã ghi nhận chưa hoá đơn → thêm hoá đơn; còn lại null", () => {
    expect(nextReceiptStep(row({ status: "DRAFT" }), can)).toBe("Ghi nhận phiếu và nhập lô");
    expect(nextReceiptStep(row({ status: "SUBMITTED" }), can)).toBe("Thêm hoá đơn mua");
    expect(nextReceiptStep(row({ status: "SUBMITTED", invoice: { id: 1 } }), can)).toBeNull();
    expect(nextReceiptStep(row({ status: "CANCELLED" }), can)).toBeNull();
    expect(nextReceiptStep(row({ status: "SUBMITTED" }), { submit: true, addInvoice: false })).toBeNull();
  });
  it("việc đã làm", () => {
    expect(receiptDoneLabels(row({ status: "DRAFT" }))).toEqual(["Lập phiếu"]);
    expect(receiptDoneLabels(row({ status: "SUBMITTED", invoice: { id: 1 } }))).toEqual(["Lập phiếu", "Ghi nhận phiếu", "Có hoá đơn mua"]);
  });
});

describe("filterReceiptRows / idFromSearch", () => {
  it("tìm không phân biệt dấu, theo mã phiếu, nhà cung cấp, mã lô", () => {
    const rows = [row({ id: 1, code: "PR-1" }), row({ id: 2, code: "PR-2", supplier_name: "Vựa Bà Năm", batch_codes: ["BAC-1"] })];
    expect(filterReceiptRows(rows, "ba nam").map((r) => r.id)).toEqual([2]);
    expect(filterReceiptRows(rows, "pr-1").map((r) => r.id)).toEqual([1]);
    expect(filterReceiptRows(rows, "bac").map((r) => r.id)).toEqual([2]);
    expect(filterReceiptRows(rows, "  ")).toHaveLength(2);
  });
  it("?id= rác → null", () => {
    expect(idFromSearch("12")).toBe(12);
    for (const bad of ["", "abc", "-3", "0", "1.5", "12345678901", null, undefined]) expect(idFromSearch(bad)).toBeNull();
  });
});

describe("receiptTotals", () => {
  it("đếm phiếu, cộng kg, bỏ kg của phiếu đã huỷ", () => {
    expect(receiptTotals([{ total_qty: "10.500", status: "SUBMITTED" }, { total_qty: "5", status: "DRAFT" }, { total_qty: "99", status: "CANCELLED" }])).toEqual({ count: 3, qty: 15.5 });
    expect(receiptTotals([])).toEqual({ count: 0, qty: 0 });
  });
});

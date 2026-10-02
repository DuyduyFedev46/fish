import { describe, expect, it } from "vitest";
import type { ReceiptRow } from "@/features/purchasing/types";
import { mergeReceiptPage, receiptOptionLabel, receiptOptions } from "./receiptOptions";
import { suggestedAmount } from "./money";

const receipt = (id: number): ReceiptRow => ({ id, code: `PR-${id}`, supplier: 1, supplier_name: "Vựa mẫu", received_date: "2026-09-24" }) as ReceiptRow;

describe("mergeReceiptPage (Tải thêm)", () => {
  it("nối trang kế sau trang đầu, giữ thứ tự", () => {
    const page1 = Array.from({ length: 20 }, (_, i) => receipt(100 - i));
    const page2 = [receipt(80), receipt(79)];
    const all = mergeReceiptPage(page1, page2);
    expect(all).toHaveLength(22);
    expect(all[20].id).toBe(80);
  });
  it("phiếu trùng giữa hai trang không thêm lần hai", () => {
    expect(mergeReceiptPage([receipt(5), receipt(4)], [receipt(4), receipt(3)]).map((r) => r.id)).toEqual([5, 4, 3]);
  });
  it("chưa có trang nào thì lấy trang mới", () => {
    expect(mergeReceiptPage(null, [receipt(1)])).toHaveLength(1);
  });
});

describe("receiptOptions", () => {
  it("luôn có lựa chọn rỗng đứng đầu và nhãn có mã, nhà cung cấp, ngày", () => {
    const o = receiptOptions([receipt(7)], null, "", "Không gắn phiếu nhập");
    expect(o[0]).toEqual({ value: "", label: "Không gắn phiếu nhập" });
    expect(o[1]).toEqual({ value: "7", label: receiptOptionLabel(receipt(7)) });
    expect(o[1].label).toBe("PR-7 · Vựa mẫu · 24/09/2026");
  });
  it("phiếu đang chọn nằm ngoài các trang đã tải vẫn có trong danh sách", () => {
    const o = receiptOptions([receipt(7)], receipt(55), "55", "Chọn");
    expect(o.map((x) => x.value)).toEqual(["", "55", "7"]);
  });
  it("không thêm hai lần khi phiếu đang chọn đã nằm trong các trang đã tải", () => {
    const o = receiptOptions([receipt(7), receipt(55)], receipt(55), "55", "Chọn");
    expect(o.filter((x) => x.value === "55")).toHaveLength(1);
  });
  it("đã bỏ chọn thì không giữ phiếu cũ", () => {
    expect(receiptOptions([receipt(7)], receipt(55), "", "Chọn").map((x) => x.value)).toEqual(["", "7"]);
  });
});

describe("suggestedAmount (làm tròn .50)", () => {
  it("1.650.000,50 làm tròn lên 1.650.001, không cắt cụt", () => {
    expect(suggestedAmount("1650000.50")).toBe("1.650.001");
    expect(suggestedAmount(1650000.5)).toBe("1.650.001");
  });
  it("dưới .50 làm tròn xuống", () => {
    expect(suggestedAmount("1650000.49")).toBe("1.650.000");
  });
  it("trống, 0 hoặc sai dạng thì không gợi ý", () => {
    expect(suggestedAmount(null)).toBe("");
    expect(suggestedAmount(undefined)).toBe("");
    expect(suggestedAmount("0.00")).toBe("");
    expect(suggestedAmount("abc")).toBe("");
  });
});

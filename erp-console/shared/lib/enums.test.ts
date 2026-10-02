// Bảng enum ↔ nhãn (enum-map.md, UI-RULES §1.5). Mã lạ hiện đúng mã gốc (ED-02-AC4).
import { describe, expect, it } from "vitest";
import { deliveryLabelText, ENUMS, enumLabel, enumOf, EMPTY_ENUM } from "@/shared/lib/enums";

describe("enumOf", () => {
  it("mã lạ hiện đúng mã gốc, chip trung tính (ED-02-AC4)", () => {
    expect(enumOf(ENUMS.salesOrderStatus, "NEW_FANCY_STATE")).toEqual({ label: "NEW_FANCY_STATE", tone: "mute" });
    expect(enumLabel(ENUMS.salesOrderStatus, "NEW_FANCY_STATE")).toBe("NEW_FANCY_STATE");
    expect(enumLabel(ENUMS.salesOrderStatus, "XYZ")).toBe("XYZ");
    expect(enumLabel(ENUMS.itemActive, "maybe")).toBe("maybe");
    expect(enumLabel(ENUMS.stockMovementType, 42)).toBe("42");
  });

  it("null, undefined, chuỗi rỗng -> dấu gạch ngang, không phải 'Không rõ'", () => {
    for (const v of [null, undefined, ""]) {
      expect(enumOf(ENUMS.salesOrderStatus, v)).toEqual(EMPTY_ENUM);
    }
    expect(EMPTY_ENUM.label).toBe("—");
  });

  it("AUTO_CANCELLED hiện là Đã huỷ (lý do ở cột riêng)", () => {
    expect(enumLabel(ENUMS.salesOrderStatus, "AUTO_CANCELLED")).toBe("Đã huỷ");
    expect(enumLabel(ENUMS.salesOrderStatus, "CANCELLED")).toBe("Đã huỷ");
  });

  it("Kiểm kê: Nháp, Chờ duyệt, Đã duyệt; Phiếu hoàn có thêm Đã huỷ (Lô bổ sung A #6, #8)", () => {
    expect(enumLabel(ENUMS.stockReconciliationStatus, "DRAFT")).toBe("Nháp");
    expect(enumLabel(ENUMS.stockReconciliationStatus, "SUBMITTED")).toBe("Chờ duyệt");
    expect(enumLabel(ENUMS.stockReconciliationStatus, "APPROVED")).toBe("Đã duyệt");
    expect(enumLabel(ENUMS.returnToStockStatus, "CANCELLED")).toBe("Đã huỷ");
  });

  it("hai nhãn WRITE_OFF khác nhau theo ngữ cảnh", () => {
    expect(enumLabel(ENUMS.stockMovementType, "WRITE_OFF")).toBe("Ghi lỗ, huỷ hàng");
    expect(enumLabel(ENUMS.returnToStockDecision, "WRITE_OFF")).toBe("Huỷ bỏ, ghi lỗ");
  });

  it("bảng boolean tra bằng true/false", () => {
    expect(enumLabel(ENUMS.itemActive, true)).toBe("Đang kinh doanh");
    expect(enumLabel(ENUMS.itemActive, false)).toBe("Đang ẩn");
    expect(enumLabel(ENUMS.supplierActive, false)).toBe("Ngừng hợp tác");
  });

  it("mức AI và chế độ AI toàn cục", () => {
    expect(enumLabel(ENUMS.aiLevel, "OFF")).toBe("Tắt");
    expect(enumLabel(ENUMS.aiLevel, "A")).toBe("Tự đọc");
    expect(enumLabel(ENUMS.aiLevel, "C")).toBe("Hỏi trước khi làm");
    expect(enumLabel(ENUMS.aiLevel, "B")).toBe("Tự ghi");
    expect(enumLabel(ENUMS.aiGlobalMode, "on")).toBe("Bật");
    expect(enumLabel(ENUMS.aiGlobalMode, "c_only")).toBe("Luôn hỏi trước");
    expect(enumLabel(ENUMS.aiGlobalMode, "off")).toBe("Tắt");
  });

  it("lý do giao thất bại (B5) đủ 5 giá trị", () => {
    expect(Object.keys(ENUMS.deliveryFailureReason).sort()).toEqual(["DAMAGED", "NOT_MET", "OTHER", "REFUSED", "WRONG_ADDRESS"]);
  });

  it("mọi bảng: nhãn không rỗng, không lộ mã thô dạng HOA_GẠCH", () => {
    for (const [name, table] of Object.entries(ENUMS)) {
      for (const [key, entry] of Object.entries(table)) {
        expect(entry.label.trim(), `${name}.${key}`).not.toBe("");
        expect(entry.label, `${name}.${key}`).not.toMatch(/^[A-Z]+(_[A-Z]+)+$/);
      }
    }
  });
});

describe("deliveryLabelText", () => {
  it("chưa in / đã in kèm số lần", () => {
    expect(deliveryLabelText(0).label).toBe("Chưa in tem");
    expect(deliveryLabelText(null).label).toBe("Chưa in tem");
    expect(deliveryLabelText(1).label).toBe("Đã in (lần 1)");
    expect(deliveryLabelText(3).label).toBe("Đã in (lần 3)");
  });
});

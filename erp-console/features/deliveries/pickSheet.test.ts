import { describe, expect, it } from "vitest";
import { MOCK_DELIVERY_NOTES, mockGetDeliveryNoteDetail } from "./mock";
import { PICK_SHEET_HREF, canOpenPickSheet, pickSheetBlock, toPickSheet } from "./pickSheet";
import type { DeliveryNoteDetail } from "./types";

// CS-16: phiếu soạn nội bộ. Dữ liệu khách trong mock là chữ bịa.
describe("CS-16: toPickSheet bỏ dữ liệu khách và giá (AC2, AC3)", () => {
  const note = MOCK_DELIVERY_NOTES.find((n) => n.id === 31)!;
  const sheet = toPickSheet(note);

  it("giữ mã phiếu, dòng hàng, kg, mã lô, hạn dùng", () => {
    expect(sheet.note_code).toBe("GH-HD-0031-PREP");
    expect(sheet.total_kg).toBe("3.500");
    expect(sheet.lines).toEqual([
      { item_name: "Tôm sú loại 1", batch_id: "TOM-SU-1-260920-AB12C", expiry_date: "2027-09-20", qty_kg: "2.500" },
      { item_name: "Mực lá Phan Thiết", batch_id: "MUC-LA-260925-CD34E", expiry_date: "2027-09-25", qty_kg: "1.000" },
    ]);
  });

  it("không còn tên, SĐT, địa chỉ, người nhận hộ, ghi chú đơn, mã đơn, giá", () => {
    const detail = mockGetDeliveryNoteDetail({ url: "/api/delivery/notes/31/", token: `mock-token-loc-${Date.now() + 1000}` }).body as DeliveryNoteDetail;
    expect(detail.phone).toBeTruthy(); // chi tiết API CÓ dữ liệu khách...
    const text = JSON.stringify(toPickSheet(detail));
    expect(text).not.toContain("Khách Thử"); // ...nhưng phiếu soạn thì không
    expect(text).not.toContain("Đường Thử");
    expect(text).not.toContain(detail.phone as string);
    expect(text).not.toContain("Giao trước 11h");
    expect(text).not.toContain("DH-260928");
    expect(Object.keys(sheet).sort()).toEqual(["lines", "note_code", "status", "total_kg"]);
    for (const l of sheet.lines) expect(Object.keys(l).sort()).toEqual(["batch_id", "expiry_date", "item_name", "qty_kg"]);
  });
});

describe("CS-16-AC4: quyền mở phiếu soạn", () => {
  it("in tem hoặc đóng gói thì được", () => {
    expect(canOpenPickSheet(["delivery.print_label"])).toBe(true);
    expect(canOpenPickSheet(["delivery.pack_deliverynote"])).toBe(true);
  });
  it("NV giao (đọc được chi tiết phiếu của mình) và CSKH thì không", () => {
    expect(canOpenPickSheet(["delivery.view_deliverynote", "delivery.change_deliverynote", "sales.view_salesorder"])).toBe(false);
    expect(canOpenPickSheet(["delivery.view_deliverynote", "delivery.confirm_with_customer", "delivery.change_recipient"])).toBe(false);
    expect(canOpenPickSheet([])).toBe(false);
  });
});

describe("CS-16: trạng thái phiếu", () => {
  it("chỉ Soạn hàng được in; đơn huỷ báo đỏ; chưa xác nhận báo vàng", () => {
    expect(pickSheetBlock("PREPARING")).toBeNull();
    expect(pickSheetBlock("CANCELLED")?.kind).toBe("error");
    expect(pickSheetBlock("CONFIRMING")?.kind).toBe("warn");
    expect(pickSheetBlock("READY")?.kind).toBe("warn");
  });
  it("đường dẫn chỉ mang id phiếu", () => {
    expect(PICK_SHEET_HREF(31)).toBe("/print/pick-sheet/?note=31");
  });
});

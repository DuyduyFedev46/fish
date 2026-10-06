// Lô 15 QA: tên việc AI phải là tiếng Việt, không hiện mã lệnh hay tên model tiếng Anh.
import { describe, expect, it } from "vitest";
import { commandLabel } from "./commandLabels";

describe("commandLabel", () => {
  it("title BE là câu dài hay có mã BR: dùng nhãn trong bảng", () => {
    expect(commandLabel("inventory.batch.close", "Chốt sổ lô cá sau khi bán hết hoặc quá hạn đã kiểm kê.")).toBe("Chốt lô cá");
    expect(commandLabel("sales.salesorder.confirm_payment", "Xác nhận thanh toán thủ công cho đơn hàng (BR-TT-07/08).")).toBe("Xác nhận thanh toán tay");
  });

  it("lệnh ngoài bảng mà title BE đã là tiếng Việt gọn: giữ title BE", () => {
    expect(commandLabel("sales.salesinvoice.list", "Xem danh sách đơn bán")).toBe("Xem danh sách đơn bán");
  });

  it("id lạ nhưng đối tượng và hành động đã biết: ghép tiếng Việt, không giữ 'batch'", () => {
    expect(commandLabel("inventory.batch.create", "Tạo mới batch")).toBe("Tạo lô cá");
    expect(commandLabel("inventory.batch.list", "Xem danh sách batch")).toBe("Xem danh sách lô cá");
    expect(commandLabel("catalog.pricelist.retrieve", "Xem chi tiết pricelist")).toBe("Xem chi tiết bảng giá");
  });

  it("id ngắn trong nhật ký cũ (sales.order.confirm, inventory.batch.inspect)", () => {
    expect(commandLabel("sales.order.confirm", "Xác nhận order")).toBe("Xác nhận đơn hàng");
    expect(commandLabel("inventory.batch.inspect", "")).toBe("Kiểm tra lô cá");
  });

  it("id hoàn toàn lạ: dùng title BE nếu ngắn và là tiếng Việt, ngược lại nhãn chung", () => {
    expect(commandLabel("foo.bar.baz", "Làm việc lạ")).toBe("Làm việc lạ");
    expect(commandLabel("foo.bar.baz", "GET /api/guidance/<loại>/<id>/")).toBe("Thao tác AI");
    expect(commandLabel("foo.bar.baz", "Tạo mới bundleline")).toBe("Thao tác AI");
    expect(commandLabel("foo.bar.baz", "Create something")).toBe("Thao tác AI");
    expect(commandLabel(undefined, undefined)).toBe("Thao tác AI");
  });

  it("không bao giờ trả mã lệnh thô", () => {
    for (const id of ["inventory.batch.inspect", "x.y.z", "reports.period_pnl", "purchasing.purchasereceipt.receive_batches"]) {
      expect(commandLabel(id, id)).not.toContain(".");
    }
  });
});

// P8b Lô 4b: GIÁ TRỊ các hằng khớp contract BE Lô 4a (tên tiếng Anh). Đây là hợp đồng với BE (`me.groups`, `me.home`,
// `group`/`sensitivity`/id lệnh của /api/ai/commands/), nên viết thẳng chuỗi để đổi nhầm giá trị là test đỏ.
import { describe, expect, it } from "vitest";
import { COMMAND_GROUP, RECEIVE_BATCHES_COMMAND_ID, SENSITIVITY } from "@/features/ai/commandGroups";
import { GROUP_CODES, GROUP_LABEL } from "./groups";
import { HOME_CONFIRMATION_QUEUE, ROLE } from "./roles";

describe("giá trị hằng khớp BE Lô 4a", () => {
  it("ROLE là 5 tên Group tiếng Anh", () => {
    expect(ROLE).toEqual({
      owner: "owner",
      manager: "manager",
      warehouseStaff: "warehouse_staff",
      deliveryStaff: "delivery_staff",
      customerService: "customer_service",
    });
  });

  it("thứ tự và nhãn nhóm đi theo tên mới", () => {
    expect([...GROUP_CODES]).toEqual(["owner", "manager", "warehouse_staff", "delivery_staff", "customer_service"]);
    expect(GROUP_LABEL["warehouse_staff"]).toBe("Nhân viên kho");
    expect(GROUP_LABEL["customer_service"]).toBe("Nhân viên gọi xác nhận"); // Duy 08/10 câu 13: bỏ chữ CSKH trên giao diện
  });

  it("me.home của người vào hàng đợi gọi xác nhận là confirmation-queue", () => {
    expect(HOME_CONFIRMATION_QUEUE).toBe("confirmation-queue");
  });

  it("nhóm lệnh AI và mức nhạy cảm là tên tiếng Anh", () => {
    expect(COMMAND_GROUP).toEqual({ purchasing: "purchasing", sales: "sales", customerService: "customer_service" });
    expect(SENSITIVITY).toEqual({ high: "high", medium: "medium", low: "low" });
  });

  it("id lệnh nhập lô là receive_batches", () => {
    expect(RECEIVE_BATCHES_COMMAND_ID).toBe("purchasing.purchasereceipt.receive_batches");
  });
});

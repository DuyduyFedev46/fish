// P8b Lô 4b: GIÁ TRỊ các hằng khớp contract BE Lô 4a (tên tiếng Anh). Đây là hợp đồng với BE (`me.groups`, `me.home`,
// `group`/`sensitivity`/id lệnh của /api/ai/commands/), nên viết thẳng chuỗi để đổi nhầm giá trị là test đỏ.
import { describe, expect, it } from "vitest";
import { COMMAND_GROUP, RECEIVE_BATCHES_COMMAND_ID, SENSITIVITY } from "@/features/ai/commandGroups";
import { normalizeCommandId } from "@/features/ai/legacyIds";
import { GROUP_CODES, GROUP_LABEL } from "./groups";
import { HOME_CONFIRMATION_QUEUE, ROLE, normalizeHome, normalizeRole } from "./roles";

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
    expect(GROUP_LABEL["customer_service"]).toBe("CSKH");
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

describe("lớp chuẩn hoá vẫn nhận tên cũ (gỡ ở Lô 5) và trả tên mới", () => {
  it("tên Group cũ -> tên mới", () => {
    expect(normalizeRole("chu")).toBe("owner");
    expect(normalizeRole("quan_ly")).toBe("manager");
    expect(normalizeRole("nv_kho")).toBe("warehouse_staff");
    expect(normalizeRole("nv_giao")).toBe("delivery_staff");
    expect(normalizeRole("cskh")).toBe("customer_service");
  });

  it("me.home và id lệnh cũ -> mới", () => {
    expect(normalizeHome("cskh-queue")).toBe("confirmation-queue");
    expect(normalizeCommandId("purchasing.purchasereceipt.nhap_lo")).toBe("purchasing.purchasereceipt.receive_batches");
  });
});

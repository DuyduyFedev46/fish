import { describe, expect, it } from "vitest";
import { objectLabelOf } from "./objectLabel";
import type { DataScopeRow, RegistryItem } from "./types";

const scopes = [{ key: "invoices", label: "Hoá đơn bán" }] as DataScopeRow[];
const registry = [
  { key: "view_order_customer_info", label: "Xem thông tin khách trên đơn, hoá đơn, phiếu hoàn tiền", section: "Bán hàng", owner_only: false, requires: [] },
  { key: "invoices", label: "Nhãn registry không được thắng", section: "Bán hàng", owner_only: false, requires: [] },
] as RegistryItem[];

describe("objectLabelOf", () => {
  it("việc V2 → nhãn registry, không lộ khoá thô", () => {
    expect(objectLabelOf("view_order_customer_info", scopes, registry)).toBe("Xem thông tin khách trên đơn, hoá đơn, phiếu hoàn tiền");
  });
  it("đối tượng phạm vi (invoices) → nhãn data_scopes trước registry", () => {
    expect(objectLabelOf("invoices", scopes, registry)).toBe("Hoá đơn bán");
  });
  it("khoá lạ hoặc dữ liệu chưa tải → chữ chung tiếng Việt, không có khoá thô", () => {
    expect(objectLabelOf("view_khong_ro", scopes, registry)).toBe("một phạm vi dữ liệu");
    expect(objectLabelOf("view_khong_ro", undefined, undefined)).not.toContain("view_");
  });
});

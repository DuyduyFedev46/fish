// PV-14-AC1..AC4: dòng của khối "Dữ liệu bạn xem được" + mock `data_scopes` khớp bảng 02b §6.1.3.
import { describe, expect, it } from "vitest";
import { buildMockDataScopes } from "./mock";
import { dataScopeView } from "./dataScopeView";
import type { DataScopeRow, Me } from "./types";

const row = (key: string, value: string, via: string | null, label = key): DataScopeRow => ({ key, label, value, value_label: value === "none" ? "Không xem" : `Giá trị ${value}`, via_group: via });
const labels = [{ code: "delivery_staff", label: "Nhân viên giao" }];

describe("dataScopeView", () => {
  it("thiếu data_scopes (BE cũ) hoặc rỗng → missing", () => {
    expect(dataScopeView({}).state).toBe("missing");
    expect(dataScopeView({ data_scopes: [] }).state).toBe("missing");
  });

  it("có nhóm → 'theo nhóm {nhãn}'; dùng group_labels trước, thiếu thì tra bảng nhóm", () => {
    const v = dataScopeView({ data_scopes: [row("orders", "assigned_deliveries", "delivery_staff"), row("receipts", "all", "warehouse_staff")], group_labels: labels });
    expect(v.state === "ok" && v.lines.map((l) => l.note)).toEqual(["theo nhóm Nhân viên giao", "theo nhóm Nhân viên kho"]);
  });

  it("'none' → mờ, không chữ phụ (kể cả via_group lạ)", () => {
    const v = dataScopeView({ data_scopes: [row("invoices", "none", null), row("audit_log", "none", "owner")] });
    expect(v.state === "ok" && v.lines.every((l) => l.muted && l.note === null)).toBe(true);
  });

  it("không nhóm, giá trị khác none, không phải superuser → 'theo quyền gán riêng'", () => {
    const v = dataScopeView({ data_scopes: [row("orders", "all", null)] });
    expect(v.state === "ok" && v.lines[0].note).toBe("theo quyền gán riêng");
  });

  it("superuser → cờ superuser, dòng rộng nhất không chữ phụ", () => {
    const v = dataScopeView({ data_scopes: [row("orders", "all", null)], is_superuser: true });
    expect(v.state === "ok" && v.superuser).toBe(true);
    expect(v.state === "ok" && v.lines[0].note).toBeNull();
  });
});

describe("mock data_scopes theo bảng mặc định", () => {
  const perms = (p: string[]) => p;
  const value = (rows: DataScopeRow[], key: string) => rows.find((r) => r.key === key)?.value;
  const ALL = [
    "sales.view_salesorder", "sales.view_salesinvoice", "delivery.view_deliverynote", "delivery.confirm_with_customer",
    "inventory.view_returntostock", "purchasing.view_purchasereceipt", "sales.view_customer", "accounts.view_auditlog",
  ];

  it("luôn đủ 8 dòng, 5 khoá mỗi dòng, đúng thứ tự", () => {
    const rows = buildMockDataScopes({ groups: ["owner"], is_superuser: false }, perms(ALL));
    expect(rows.map((r) => r.key)).toEqual(["orders", "invoices", "deliveries", "confirmation", "returns", "receipts", "customers", "audit_log"]);
    rows.forEach((r) => expect(Object.keys(r).sort()).toEqual(["key", "label", "value", "value_label", "via_group"]));
  });

  it("NV giao: đơn gán cho tôi, hoá đơn/phiếu nhập/nhật ký không xem", () => {
    const rows = buildMockDataScopes({ groups: ["delivery_staff"], is_superuser: false }, perms(["sales.view_salesorder", "delivery.view_deliverynote", "inventory.view_returntostock", "sales.view_customer"]));
    expect(rows.map((r) => r.value)).toEqual(["assigned_deliveries", "none", "assigned", "none", "assigned_deliveries", "none", "assigned_deliveries", "none"]);
    expect(value(rows, "orders")).toBe("assigned_deliveries");
    expect(rows[0].via_group).toBe("delivery_staff");
  });

  it("NV kho kiêm NV giao: lấy rộng nhất, đúng nhóm cho từng dòng", () => {
    const rows = buildMockDataScopes({ groups: ["warehouse_staff", "delivery_staff"], is_superuser: false }, perms(ALL));
    expect(value(rows, "orders")).toBe("all");
    expect(rows[0].via_group).toBe("warehouse_staff");
    expect(value(rows, "customers")).toBe("assigned_deliveries");
    expect(rows.find((r) => r.key === "customers")?.via_group).toBe("delivery_staff");
  });

  it("không nhóm → cả 8 dòng none; superuser → rộng nhất, via_group null", () => {
    expect(buildMockDataScopes({ groups: [], is_superuser: false }, perms(ALL)).every((r) => r.value === "none" && r.value_label === "Không xem" && r.via_group === null)).toBe(true);
    const su = buildMockDataScopes({ groups: [], is_superuser: true }, perms(ALL));
    expect(value(su, "confirmation")).toBe("all_pending");
    expect(su.every((r) => r.via_group === null)).toBe(true);
  });

  it("CSKH: đơn assigned_or_confirmation, gọi xác nhận pending_or_called_recently; Chủ: có via owner", () => {
    const cs = buildMockDataScopes({ groups: ["customer_service"], is_superuser: false }, perms(["sales.view_salesorder", "delivery.confirm_with_customer", "delivery.view_deliverynote"]));
    expect(value(cs, "orders")).toBe("assigned_or_confirmation");
    expect(value(cs, "confirmation")).toBe("pending_or_called_recently");
    expect(value(cs, "deliveries")).toBe("none");
    const ow = buildMockDataScopes({ groups: ["owner"], is_superuser: false }, perms(ALL));
    expect(ow.every((r) => r.via_group === "owner")).toBe(true);
  });
});

// Kiểm kiểu: Me.data_scopes dùng được như mảng DataScopeRow.
const _typecheck: Pick<Me, "data_scopes"> = { data_scopes: [] };
void _typecheck;

import { describe, expect, it } from "vitest";
import { actionLabel, actorInitial, actorName, approverOf, buildApproverMap, changeSummary, matchesLocal, UNKNOWN_ACTION } from "./auditModel";
import type { AuditLogRow } from "./types";

const row = (over: Partial<AuditLogRow>): AuditLogRow => ({
  id: 1,
  actor_kind: "user",
  actor_display: "loc",
  ai_actor: null,
  action: "create",
  model_name: "x",
  object_id: null,
  object_repr: null,
  changes: null,
  note: null,
  proposal_ref: null,
  created_at: "2026-09-27T10:00:00+07:00",
  ...over,
});

describe("actionLabel", () => {
  it("dịch mã thật của BE", () => {
    expect(actionLabel("publish_batch")).toBe("Mở bán lô");
    expect(actionLabel("staff_groups_change")).toBe("Đổi nhóm quyền");
  });
  it("mã lạ không lộ mã kỹ thuật", () => {
    expect(actionLabel("zzz_unknown")).toBe(UNKNOWN_ACTION);
  });
});

describe("tên người làm", () => {
  it("dòng AI bỏ tiền tố ai:", () => {
    expect(actorName(row({ actor_kind: "ai", actor_display: "ai:kho1" }))).toBe("kho1");
    expect(actorInitial(row({ actor_kind: "ai", actor_display: "ai:kho1" }))).toBe("K");
  });
  it("dòng hệ thống ghi Hệ thống", () => {
    expect(actorName(row({ actor_kind: "system", actor_display: "system" }))).toBe("Hệ thống");
  });
});

describe("người duyệt", () => {
  const rows = [
    row({ id: 3, actor_kind: "ai", actor_display: "ai:kho1", action: "propose", proposal_ref: "P-1" }),
    row({ id: 2, actor_kind: "user", actor_display: "loc", action: "confirm_proposal", proposal_ref: "P-1" }),
    row({ id: 1, actor_kind: "ai", actor_display: "ai:kho1", action: "propose", proposal_ref: "P-2" }),
  ];
  const map = buildApproverMap(rows);
  it("tìm theo mã đề xuất", () => {
    expect(approverOf(rows[0], map)).toBe("loc");
  });
  it("không có dòng duyệt trong các dòng đã tải → null", () => {
    expect(approverOf(rows[2], map)).toBeNull();
  });
  it("dòng của người không có người duyệt", () => {
    expect(approverOf(rows[1], map)).toBeNull();
  });
});

describe("changeSummary: W11 dịch trạng thái theo model_name (T23, T29, T47)", () => {
  it("FAILED của phiếu giao là Giao thất bại, của phiếu hoàn tiền là Hoàn thất bại", () => {
    expect(changeSummary({ status: ["DELIVERING", "FAILED"] }, "delivery.DeliveryNote")).toEqual(["Trạng thái: Đang giao → Giao thất bại"]);
    expect(changeSummary({ status: ["PENDING", "FAILED"] }, "sales.Refund")).toEqual(["Trạng thái: Chờ hoàn tiền → Hoàn thất bại"]);
  });
  it("DRAFT của phiếu hàng hoàn là Chờ duyệt, của lô là Nháp", () => {
    expect(changeSummary({ status: ["DRAFT", "APPROVED"] }, "inventory.ReturnToStock")).toEqual(["Trạng thái: Chờ duyệt → Đã duyệt"]);
    expect(changeSummary({ status: ["DRAFT", "SELLING"] }, "inventory.Batch")).toEqual(["Trạng thái: Nháp → Đang bán"]);
  });
  it("COMPLETED của phiếu giao là Đã giao, của đơn là Hoàn tất", () => {
    expect(changeSummary({ status: ["DELIVERING", "COMPLETED"] }, "delivery.DeliveryNote")).toEqual(["Trạng thái: Đang giao → Đã giao"]);
    expect(changeSummary({ status: ["PROCESSING", "COMPLETED"] }, "sales.SalesOrder")).toEqual(["Trạng thái: Đang xử lý → Hoàn tất"]);
  });
  it("model lạ hoặc thiếu: không đoán, không in trạng thái", () => {
    expect(changeSummary({ status: ["BOOKED", "PAID"] })).toEqual([]);
    expect(changeSummary({ status: ["BOOKED", "PAID"] }, "x.Unknown")).toEqual([]);
  });
});

describe("changeSummary (danh sách trắng)", () => {
  it("trạng thái dạng cặp và dạng from/to", () => {
    expect(changeSummary({ status: ["BOOKED", "PAID"] }, "sales.SalesOrder")).toEqual(["Trạng thái: Giữ chỗ → Đã thanh toán"]);
    expect(changeSummary({ status: { from: "PENDING", to: "REFUNDED" } }, "sales.Refund")).toEqual(["Trạng thái: Chờ hoàn tiền → Đã hoàn tiền"]);
  });
  it("số tiền và giá bán có đơn vị đ", () => {
    expect(changeSummary({ amount: { to: 125000 } })).toEqual(["Số tiền: → 125.000 đ"]);
    expect(changeSummary({ price: [110000, 115000] })[0]).toBe("Giá bán: 110.000 đ → 115.000 đ");
  });
  it("nhóm quyền dùng nhãn tiếng Việt", () => {
    expect(changeSummary({ groups: { from: ["warehouse_staff"], to: ["warehouse_staff", "delivery_staff"] } })).toEqual([
      "Nhóm quyền: Nhân viên kho → Nhân viên kho, Nhân viên giao",
    ]);
  });
  it("KHÔNG in giá vốn/lãi, tên, SĐT hay JSON thô", () => {
    const out = changeSummary({
      unit_cost: [41000, 42000],
      purchase_rate: { from: 1, to: 2 },
      profit: { to: 99999 },
      customer_name: ["Nguyễn Văn A", "B"],
      phone: { to: "0900000000" },
      fields: ["address"],
    });
    expect(out).toEqual([]);
  });
  it("giá trị lạ trong khoá được phép không bị in ra", () => {
    expect(changeSummary({ status: ["X", "Họ tên khách"] })).toEqual([]);
    expect(changeSummary({ amount: { to: "Nguyễn" } })).toEqual([]);
  });
  it("null / mảng / rỗng", () => {
    expect(changeSummary(null)).toEqual([]);
    expect(changeSummary([] as unknown as Record<string, unknown>)).toEqual([]);
    expect(changeSummary({})).toEqual([]);
  });
});

describe("matchesLocal", () => {
  const r = row({ object_repr: "SO-20260927-038", proposal_ref: "P-011", created_at: "2026-09-27T23:30:00+07:00" });
  it("tìm theo mã chứng từ hoặc mã đề xuất, không phân biệt hoa thường", () => {
    expect(matchesLocal(r, { query: "so-2026", from: "", to: "" })).toBe(true);
    expect(matchesLocal(r, { query: "p-011", from: "", to: "" })).toBe(true);
    expect(matchesLocal(r, { query: "xyz", from: "", to: "" })).toBe(false);
  });
  it("khoảng ngày theo giờ VN (23:30 ngày 27 vẫn là ngày 27)", () => {
    expect(matchesLocal(r, { query: "", from: "2026-09-27", to: "2026-09-27" })).toBe(true);
    expect(matchesLocal(r, { query: "", from: "2026-09-28", to: "" })).toBe(false);
    expect(matchesLocal(r, { query: "", from: "", to: "2026-09-26" })).toBe(false);
  });
});

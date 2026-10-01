import { describe, expect, it } from "vitest";
import type { AiActionDetail, AiActionRow } from "../types";
import { changesOf, readyAtOf, toProposalView, waitLeft } from "./docBlockModel";

const row = (over: Partial<AiActionRow> = {}): AiActionRow => ({
  id: "a1", command: "x", title: "Xác nhận phiếu nhập hàng", level: "C", status: "PENDING", owner_display: "AI của Lộc",
  created_at: "2026-10-01T01:00:00Z", expires_at: null, execute_after: null, undo_until: null, target: null,
  args_preview: { item_code: "CA-001", qty: "10.000", customer_name: "Khách mẫu", phone: "0900000123", note: "" },
  downgrade_reason: null, result_ref: null, ...over,
});

describe("changesOf", () => {
  it("chỉ hiện khoá có nhãn, bỏ giá trị trống, không lộ tên/SĐT khách", () => {
    const out = changesOf(row().args_preview);
    expect(out).toEqual([
      { label: "Mã hàng", after: "CA-001" },
      { label: "Số lượng", after: "10 kg" },
    ]);
    expect(JSON.stringify(out)).not.toMatch(/Khách|0900/);
  });
  it("QA B1: note (chữ tự do) và mọi trường chữ tự do không bao giờ hiện, kể cả khi chứa SĐT giả", () => {
    const out = changesOf({ item_code: "CA-001", qty: "1", note: "Giao cho Khách Mẫu, SĐT 0900000123", reason: "gọi 0900000123", description: "địa chỉ 1 Đường Mẫu", address: "1 Đường Mẫu" });
    expect(out.map((c) => c.label)).toEqual(["Mã hàng", "Số lượng"]);
    expect(JSON.stringify(out)).not.toMatch(/0900000123|Khách Mẫu|Đường Mẫu/);
  });
  it("QA B2: số lượng có đơn vị kg, dấu phẩy thập phân; tiền có đ", () => {
    expect(changesOf({ qty: "10.000" })).toEqual([{ label: "Số lượng", after: "10 kg" }]);
    expect(changesOf({ quantity: "18.500" })).toEqual([{ label: "Số lượng", after: "18,5 kg" }]);
    expect(changesOf({ qty: 2 })).toEqual([{ label: "Số lượng", after: "2 kg" }]);
    expect(changesOf({ refund_amount: "540000.00" })).toEqual([{ label: "Số tiền hoàn", after: "540.000 đ" }]);
  });
  it("số lượng không phải số thì bỏ, không hiện chuỗi thô", () => expect(changesOf({ qty: "abc" })).toEqual([]));
  it("không hiện giá vốn dù có trong args_preview", () => {
    expect(changesOf({ item_code: "CA-001", unit_cost: "1000", landed_unit_cost: "1200", purchase_rate: "900" })).toEqual([{ label: "Mã hàng", after: "CA-001" }]);
  });
  it("null → rỗng", () => expect(changesOf(null)).toEqual([]));
});

describe("đếm ngược Đồng ý (BR-AI-14)", () => {
  it("chưa biết thời điểm → chờ đủ 3 giây", () => expect(waitLeft(undefined, 0)).toBe(3));
  it("làm tròn lên và không âm", () => {
    expect(waitLeft(2500, 1000)).toBe(2);
    expect(waitLeft(1000, 5000)).toBe(0);
  });
  it("ưu tiên viewable_from của BE, không có thì lúc xem + 3 giây", () => {
    const d = { ...row(), viewable_from: "2026-10-01T01:00:05Z" } as AiActionDetail;
    expect(readyAtOf(d, 0)).toBe(Date.parse("2026-10-01T01:00:05Z"));
    expect(readyAtOf(row() as AiActionDetail, 1000)).toBe(4000);
  });
});

describe("toProposalView", () => {
  it("PENDING có thời gian chờ; ESCALATED hiện nhóm nhận việc bằng nhãn", () => {
    expect(toProposalView(row(), 2)?.waitSeconds).toBe(2);
    const esc = toProposalView(row({ status: "ESCALATED", assignee_group: "owner" }), 3);
    expect(esc?.state).toBe("ESCALATED");
    expect(esc?.assigneeGroup).toBe("Chủ");
    expect(esc?.waitSeconds).toBe(0);
  });
  it("trạng thái khác không vẽ", () => expect(toProposalView(row({ status: "DONE" }), 0)).toBeNull());
});

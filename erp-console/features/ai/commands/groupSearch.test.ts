// P8b Lô 4b: khoá nhóm lệnh đã đổi sang tiếng Anh, bộ tìm lệnh không được mất các từ "thu mua", "bán hàng".
// Dữ liệu giả, dựng theo hình dạng /api/ai/commands/ (title và keywords tiếng Việt có dấu, group tiếng Anh).
import { describe, expect, it } from "vitest";
import { COMMAND_GROUP, RECEIVE_BATCHES_COMMAND_ID } from "../commandGroups";
import type { AiCommandIndexItem } from "../types";
import { searchCommands } from "./search";

function cmd(id: string, title: string, group: string, keywords: string[] = []): AiCommandIndexItem {
  return { id, title, group, kind: "write", level: "A", screens: [], keywords } as AiCommandIndexItem;
}

const INDEX: AiCommandIndexItem[] = [
  cmd(RECEIVE_BATCHES_COMMAND_ID, "Nhập lô mua tại cảng", COMMAND_GROUP.purchasing, ["nhập lô", "nhập hàng", "cảng"]),
  cmd("purchasing.supplier.create", "Thêm nhà cung cấp", COMMAND_GROUP.purchasing, ["nhà cung cấp"]),
  cmd("sales.salesorder.cancel", "Huỷ đơn bán", COMMAND_GROUP.sales, ["huỷ đơn"]),
  cmd("sales.refund.create_refund", "Tạo phiếu hoàn tiền", COMMAND_GROUP.sales, ["hoàn tiền"]),
  cmd("sales.customer.list", "Danh sách khách", COMMAND_GROUP.customerService, ["khách"]),
  cmd("sales.confirmation.claim", "Nhận cuộc gọi xác nhận", COMMAND_GROUP.customerService, ["gọi xác nhận"]),
];

const ids = (q: string, index = INDEX) => searchCommands(q, index, { limit: 5 }).candidates.map((c) => c.command.id);

describe("bộ tìm lệnh AI sau khi nhóm đổi sang tiếng Anh", () => {
  it("'nhập lô' đưa lệnh receive_batches lên đầu", () => {
    expect(ids("nhập lô")[0]).toBe(RECEIVE_BATCHES_COMMAND_ID);
  });

  it("'thu mua' khớp nhãn nhóm: mọi lệnh nhóm purchasing nằm trong top-5", () => {
    const top = ids("thu mua");
    expect(top).toContain(RECEIVE_BATCHES_COMMAND_ID);
    expect(top).toContain("purchasing.supplier.create");
  });

  it("'bán hàng' khớp nhãn nhóm: các lệnh nhóm sales nằm trong top-5", () => {
    const top = ids("bán hàng");
    expect(top).toContain("sales.salesorder.cancel");
    expect(top).toContain("sales.refund.create_refund");
  });

  it("'cskh' tìm ra lệnh nhóm customer_service", () => {
    const top = ids("cskh");
    expect(top).toContain("sales.customer.list");
    expect(top).toContain("sales.confirmation.claim");
  });
});

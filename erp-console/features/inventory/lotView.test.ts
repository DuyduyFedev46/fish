import { describe, expect, it } from "vitest";
import type { Me } from "@/features/auth/types";
import {
  batchAbility,
  closeBlockReason,
  doneLabels,
  expiredBlockReason,
  filterBatchRows,
  idFromSearch,
  isLotStateError,
  isStaleLotError,
  kgToInput,
  newRequestId,
  parseKgInput,
  pathOf,
  statusFromSearch,
  stepLacksPermission,
  stepReason,
  stripRuleCodes,
} from "./lotView";
import type { BatchApiRow } from "./types";

const me = (over: Partial<Me>): Me => ({
  id: 1,
  username: "x",
  display_name: "X",
  phone: "",
  groups: [],
  permissions: [],
  can_view_cost: false,
  can_view_profit: false,
  home: "dashboard",
  ...over,
});

const lot = (over: Partial<BatchApiRow>): BatchApiRow => ({
  id: 1,
  batch_id: "L0908-CT00",
  item: 1,
  item_code: "CT00",
  item_name: "Cá thu",
  supplier: 1,
  supplier_name: "Vựa Ba Hải",
  warehouse: 1,
  warehouse_name: "Kho lạnh Bến Đá",
  received_date: "2026-09-20",
  expiry_date: "2026-09-30",
  qty_received: "20.000",
  qty_available: "6.500",
  qty_reserved: "0.000",
  qty_sellable: "6.500",
  status: "EXPIRED",
  status_label: "Quá hạn",
  closed_at: null,
  receipt: null,
  ...over,
});

describe("batchAbility", () => {
  it("Chủ: huỷ tồn, trả nhà cung cấp, chốt, xem giá vốn", () => {
    const a = batchAbility(me({ groups: ["owner"], permissions: ["inventory.close_batch", "inventory.cancel_expired_batch", "inventory.view_costprice"], can_view_cost: true, can_view_profit: true }));
    expect(a).toMatchObject({ cancelExpired: true, returnToSupplier: true, close: true, viewCost: true, viewProfit: true });
  });
  it("Quyền huỷ/trả tính theo quyền BE trả, không theo tên nhóm owner", () => {
    const a = batchAbility(me({ groups: ["owner"], permissions: ["inventory.close_batch"] }));
    expect(a).toMatchObject({ cancelExpired: false, returnToSupplier: false });
  });
  it("Quản lý: mở bán được, KHÔNG chốt, KHÔNG huỷ tồn, KHÔNG giá vốn, KHÔNG lãi lỗ", () => {
    const a = batchAbility(me({ groups: ["manager"], permissions: ["inventory.publish_batch", "inventory.view_batch"] }));
    expect(a).toMatchObject({ publish: true, close: false, cancelExpired: false, returnToSupplier: false, viewCost: false, viewProfit: false });
  });
  it("NV kho: chỉ xem", () => {
    const a = batchAbility(me({ groups: ["warehouse_staff"], permissions: ["inventory.view_batch", "inventory.view_stockledgerentry"] }));
    expect(a).toMatchObject({ publish: false, close: false, cancelExpired: false, viewLedger: true, viewOrders: false, viewCost: false });
  });
});

describe("pathOf", () => {
  it("Quá hạn / Đã huỷ là kết thúc xấu sau Cận hạn", () => {
    expect(pathOf("EXPIRED")).toEqual({ current: "NEAR_EXPIRY", badEnd: { label: "Quá hạn", after: "NEAR_EXPIRY" } });
    expect(pathOf("CANCELLED").badEnd?.label).toBe("Đã huỷ");
  });
  it("trạng thái thường tô đúng bước", () => {
    expect(pathOf("SELLING")).toEqual({ current: "SELLING", badEnd: null });
  });
});

describe("lý do bị chặn", () => {
  it("huỷ tồn / trả nhà cung cấp", () => {
    expect(expiredBlockReason(lot({}))).toBeUndefined();
    expect(expiredBlockReason(lot({ status: "SELLING" }))).toBe("Lô chưa quá hạn.");
    expect(expiredBlockReason(lot({ status: "CLOSED" }))).toBe("Lô đã chốt.");
    expect(expiredBlockReason(lot({ qty_available: "0.000" }))).toBe("Lô không còn tồn.");
    expect(expiredBlockReason(lot({ qty_reserved: "1.500" }))).toBe("Còn 1,5 kg đang giữ chỗ.");
  });
  it("chốt lô: còn tồn thì chặn, hết tồn thì dùng lý do của khối Tiếp theo (bỏ mã BR)", () => {
    expect(closeBlockReason(lot({ status: "SELLING", qty_available: "18.500" }))).toBe("Lô còn 18,5 kg.");
    expect(closeBlockReason(lot({ status: "SOLD_OUT", qty_available: "0.000" }))).toBeUndefined();
    expect(closeBlockReason(lot({ status: "SOLD_OUT", qty_available: "0.000" }), "Thiếu hoá đơn mua. (BR-LO-04)")).toBe("Thiếu hoá đơn mua.");
    expect(closeBlockReason(lot({ status: "CLOSED", qty_available: "0.000" }))).toBe("Lô đã chốt.");
  });
  it("stripRuleCodes bỏ mọi mã BR", () => {
    expect(stripRuleCodes("Lô còn tồn (BR-LO-04).")).toBe("Lô còn tồn.");
    expect(stripRuleCodes("BR-PQ-12 Chỉ Chủ")).toBe("Chỉ Chủ");
  });
  it("guidance: BR-PQ-12 = thiếu quyền (ẩn mục), lý do khác thì hiện", () => {
    const step = { missing: [{ code: "BR-PQ-12", text: "Chỉ Chủ." }, { code: "BR-LO-04", text: "Còn tồn." }] };
    expect(stepLacksPermission(step)).toBe(true);
    expect(stepReason(step)).toBe("Còn tồn.");
    expect(stepLacksPermission(undefined)).toBe(false);
  });
});

describe("đọc dữ liệu nhập", () => {
  it("?id= chỉ nhận số nguyên dương", () => {
    expect(idFromSearch("12")).toBe(12);
    for (const bad of [null, "", "0", "-3", "abc", "1.5", "12abc", "1".repeat(12), "<script>"]) expect(idFromSearch(bad)).toBeNull();
  });
  it("?status= chỉ nhận trạng thái có thật", () => {
    expect(statusFromSearch("?status=EXPIRED")).toBe("EXPIRED");
    expect(statusFromSearch("?status=HACK")).toBe("");
    expect(statusFromSearch("")).toBe("");
  });
  it("số kg", () => {
    expect(parseKgInput("3,5")).toBe(3.5);
    expect(parseKgInput("3.125")).toBe(3.125);
    expect(parseKgInput("3.1234")).toBeNull();
    expect(parseKgInput("abc")).toBeNull();
    expect(parseKgInput("-1")).toBeNull();
    expect(kgToInput(18.5)).toBe("18,5");
  });
  it("request_id là UUID v4 và đổi mỗi lần", () => {
    const a = newRequestId();
    expect(a).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    expect(newRequestId()).not.toBe(a);
  });
});

describe("tìm trong danh sách", () => {
  const rows = [lot({}), lot({ id: 2, batch_id: "L0921-MU03", item_name: "Mực ống", supplier_name: "Vựa Tư", warehouse_name: "Kho mát chợ Vũng Tàu" })];
  it("không phân biệt dấu, tìm theo mã, mặt hàng, nhà cung cấp, kho", () => {
    expect(filterBatchRows(rows, "muc ong").map((r) => r.id)).toEqual([2]);
    expect(filterBatchRows(rows, "l0908").map((r) => r.id)).toEqual([1]);
    expect(filterBatchRows(rows, "vung tau").map((r) => r.id)).toEqual([2]);
    expect(filterBatchRows(rows, "  ")).toHaveLength(2);
  });
});

describe("doneLabels", () => {
  it("nhãn ngắn, không lặp, bỏ loại lạ, theo thứ tự thời gian", () => {
    const out = doneLabels([
      { kind: "published", at: "2026-09-21T01:00:00Z" },
      { kind: "batch_created", at: "2026-09-20T01:00:00Z" },
      { kind: "published", at: "2026-09-22T01:00:00Z" },
      { kind: "weird", at: "2026-09-23T01:00:00Z" },
    ]);
    expect(out).toEqual(["Nhập lô", "Mở bán"]);
  });
});

describe("isStaleLotError (L2: chỉ mời Tải lại tồn khi số liệu cũ thật)", () => {
  it.each([
    ["BR-MH-05", "Mở bán: Chỉ publish được lô đang ở trạng thái Nháp."],
    ["BR-LO-03", "Huỷ phần tồn: Chỉ huỷ được lô Quá hạn."],
    ["BR-LO-04", "Chốt lô: Chốt lô yêu cầu tồn = 0 hoặc đã huỷ phần còn lại."],
    ["BR-LO-05", "Trả nhà cung cấp, Huỷ: Lô đã chốt."],
    ["BR-KK-05", "Chốt lô: Lô phải được kiểm kê và duyệt trước khi chốt."],
    ["BR-LO-07", "Trả nhà cung cấp: Chỉ xác nhận trả NCC cho lô Quá hạn còn tồn."],
    ["BR-LO-07", "Còn 5 kg đang giữ chỗ của 2 đơn — chờ đơn thanh toán hoặc hết hạn giữ chỗ rồi huỷ."],
  ])("sai trạng thái lô %s là số liệu cũ (%s)", (code, message) => {
    expect(isStaleLotError(code, message)).toBe(true);
  });
  it.each(["BR-MH-05", "BR-LO-03", "BR-LO-04", "BR-LO-05", "BR-KK-05"])("%s là lỗi sai trạng thái lô (khoá nút chính)", (code) => {
    expect(isLotStateError(code)).toBe(true);
  });
  it("tồn lệch (BR-MH-08, BR-LO-07) không khoá nút chính: còn sửa số rồi gửi lại được", () => {
    expect(isLotStateError("BR-MH-08")).toBe(false);
    expect(isLotStateError("BR-LO-07")).toBe(false);
    expect(isLotStateError(undefined)).toBe(false);
  });
  it("trạng thái/tồn đổi: BR-MH-05, BR-LO-04, BR-LO-07", () => {
    expect(isStaleLotError("BR-MH-05", "Chỉ publish được lô đang ở trạng thái Nháp.")).toBe(true);
    expect(isStaleLotError("BR-LO-04", "Lô còn lượng giữ chỗ chưa giải phóng.")).toBe(true);
    expect(isStaleLotError("BR-LO-07", "Tồn đã đổi (4,5 kg) — tải lại.")).toBe(true);
  });
  it("BR-MH-08: chỉ khi vượt tồn", () => {
    expect(isStaleLotError("BR-MH-08", "Số kg trả phải lớn hơn 0 và không vượt tồn 4,5 kg.")).toBe(true);
    expect(isStaleLotError("BR-MH-08", "Mã yêu cầu đã được dùng cho lô khác.")).toBe(false);
    expect(isStaleLotError("BR-MH-08", "Tiền NCC hoàn phải là số không âm, tối đa 2 chữ số thập phân.")).toBe(false);
    expect(isStaleLotError("BR-MH-08", "Ghi chú tối đa 500 ký tự.")).toBe(false);
  });
  it("lỗi nhập sai hoặc không mã thì không mời", () => {
    expect(isStaleLotError("BR-LO-07", "Số kg xác nhận không hợp lệ.")).toBe(false);
    expect(isStaleLotError(undefined, "Lỗi máy chủ")).toBe(false);
    expect(isStaleLotError("OTHER", "x")).toBe(false);
  });
});

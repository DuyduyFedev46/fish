// P8b Lô 4b: lưu trần lệnh Nhập lô luôn gửi id mới, không để lại khoá cũ.
import { describe, expect, it } from "vitest";
import { RECEIVE_BATCHES_COMMAND_ID } from "../commandGroups";
import { buildCapsForSave } from "./caps";

const NEXT = { kg: "300", vnd: null, daily: 10 };
const OLD_ID = "purchasing.purchasereceipt.nhap_lo";

describe("buildCapsForSave", () => {
  it("BE trả id mới: ghi đè đúng khoá đó, giữ lệnh khác", () => {
    const out = buildCapsForSave({ [RECEIVE_BATCHES_COMMAND_ID]: { kg: "200", max_level: "B" }, "sales.x.y": { kg: "5" } }, NEXT);
    expect(Object.keys(out).sort()).toEqual([RECEIVE_BATCHES_COMMAND_ID, "sales.x.y"].sort());
    expect(out[RECEIVE_BATCHES_COMMAND_ID]).toEqual({ kg: "300", vnd: null, daily: 10, max_level: "B" });
    expect(out["sales.x.y"]).toEqual({ kg: "5" });
  });

  it("BE còn trả id cũ: gửi id MỚI, không còn khoá cũ, giữ giá trị phụ của khoá cũ", () => {
    const out = buildCapsForSave({ [OLD_ID]: { kg: "200", max_level: "B" } }, NEXT);
    expect(Object.keys(out)).toEqual([RECEIVE_BATCHES_COMMAND_ID]);
    expect(out[RECEIVE_BATCHES_COMMAND_ID]).toEqual({ kg: "300", vnd: null, daily: 10, max_level: "B" });
  });

  it("chưa có trần nào: tạo khoá mới", () => {
    expect(buildCapsForSave(null, NEXT)).toEqual({ [RECEIVE_BATCHES_COMMAND_ID]: NEXT });
  });
});

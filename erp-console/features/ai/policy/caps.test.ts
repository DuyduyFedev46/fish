// P8b Lô 4b, 5: lưu trần lệnh Nhập lô gửi đúng id `receive_batches` (không còn xử lý id cũ).
import { describe, expect, it } from "vitest";
import { RECEIVE_BATCHES_COMMAND_ID } from "../commandGroups";
import { buildCapsForSave } from "./caps";

const NEXT = { kg: "300", vnd: null, daily: 10 };

describe("buildCapsForSave", () => {
  it("BE trả id mới: ghi đè đúng khoá đó, giữ lệnh khác", () => {
    const out = buildCapsForSave({ [RECEIVE_BATCHES_COMMAND_ID]: { kg: "200", max_level: "B" }, "sales.x.y": { kg: "5" } }, NEXT);
    expect(Object.keys(out).sort()).toEqual([RECEIVE_BATCHES_COMMAND_ID, "sales.x.y"].sort());
    expect(out[RECEIVE_BATCHES_COMMAND_ID]).toEqual({ kg: "300", vnd: null, daily: 10, max_level: "B" });
    expect(out["sales.x.y"]).toEqual({ kg: "5" });
  });

  it("chưa có trần nào: tạo khoá mới", () => {
    expect(buildCapsForSave(null, NEXT)).toEqual({ [RECEIVE_BATCHES_COMMAND_ID]: NEXT });
  });
});

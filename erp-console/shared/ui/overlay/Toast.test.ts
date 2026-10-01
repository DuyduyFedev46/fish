// Toast: tuỳ chọn `duration` của người gọi được tôn trọng (techlead L1).
import { describe, expect, it } from "vitest";
import { makeToastItem, toastDuration } from "@/shared/ui/overlay/Toast";

describe("toastDuration", () => {
  it("mặc định theo loại: lỗi lâu hơn cảnh báo, cảnh báo lâu hơn thành công", () => {
    expect(toastDuration("success")).toBe(6000);
    expect(toastDuration("warn")).toBe(8000);
    expect(toastDuration("error")).toBe(10000);
  });
  it("người gọi truyền duration thì dùng đúng số đó", () => {
    expect(toastDuration("success", 1500)).toBe(1500);
    expect(toastDuration("error", 30000)).toBe(30000);
  });
  it("duration không hợp lệ (0, âm, NaN) -> về mặc định theo loại", () => {
    expect(toastDuration("warn", 0)).toBe(8000);
    expect(toastDuration("warn", -5)).toBe(8000);
    expect(toastDuration("warn", Number.NaN)).toBe(8000);
  });
});

describe("makeToastItem", () => {
  it("lưu duration và undo của người gọi vào mục thông báo", () => {
    const undo = () => undefined;
    const item = makeToastItem(7, "success", "Đã huỷ đơn", { undo, duration: 2500 });
    expect(item).toMatchObject({ id: 7, kind: "success", message: "Đã huỷ đơn", duration: 2500 });
    expect(item.undo).toBe(undo);
  });
  it("không truyền tuỳ chọn thì duration để trống (dùng mặc định theo loại)", () => {
    expect(makeToastItem(1, "error", "Lỗi").duration).toBeUndefined();
  });
});

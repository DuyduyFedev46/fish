import { describe, expect, it } from "vitest";
import { isDeliveryFinished } from "./orderCompletion";

describe("isDeliveryFinished (BR-BH-18)", () => {
  it("không có phiếu nào thì chưa xong", () => {
    expect(isDeliveryFinished([])).toBe(false);
  });
  it("một phiếu COMPLETED thì xong", () => {
    expect(isDeliveryFinished(["COMPLETED"])).toBe(true);
  });
  it("còn một phiếu chưa COMPLETED thì chưa xong", () => {
    for (const s of ["CONFIRMING", "PREPARING", "READY", "DELIVERING", "FAILED"]) {
      expect(isDeliveryFinished(["COMPLETED", s])).toBe(false);
    }
  });
  it("bỏ phiếu CANCELLED khi xét", () => {
    expect(isDeliveryFinished(["CANCELLED", "COMPLETED"])).toBe(true);
    expect(isDeliveryFinished(["CANCELLED", "DELIVERING"])).toBe(false);
  });
  it("mọi phiếu đều CANCELLED thì chưa xong", () => {
    expect(isDeliveryFinished(["CANCELLED", "CANCELLED"])).toBe(false);
  });
});

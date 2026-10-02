import { describe, expect, it } from "vitest";
import { currentMonth, legacyOrderRedirect, presetRange, recentMonths, reasonText } from "./filters";
import { overRefundMax } from "./refund";
import { parseId } from "./useIdParam";

// 2026-10-01 20:00 UTC = 2026-10-02 03:00 giờ Việt Nam.
const NOW = Date.parse("2026-10-01T20:00:00Z");

describe("presetRange theo giờ Việt Nam", () => {
  it("hôm nay lấy ngày Việt Nam, không phải ngày UTC", () => {
    expect(presetRange("today", "", "", NOW)).toEqual({ date_from: "2026-10-02", date_to: "2026-10-02" });
  });
  it("7 ngày và 30 ngày gồm cả hôm nay", () => {
    expect(presetRange("7d", "", "", NOW).date_from).toBe("2026-09-26");
    expect(presetRange("30d", "", "", NOW).date_from).toBe("2026-09-03");
  });
  it("tuỳ chọn lấy đúng hai ô; tất cả thì rỗng", () => {
    expect(presetRange("custom", "2026-09-01", "2026-09-05", NOW)).toEqual({ date_from: "2026-09-01", date_to: "2026-09-05" });
    expect(presetRange("all", "x", "y", NOW)).toEqual({ date_from: "", date_to: "" });
  });
});

describe("reasonText", () => {
  it("ưu tiên nhãn BE; đơn tự huỷ không có reason → Hết giờ giữ chỗ", () => {
    expect(reasonText({ label: "Khách đổi ý" }, "CANCELLED")).toBe("Khách đổi ý");
    expect(reasonText(null, "AUTO_CANCELLED")).toBe("Hết giờ giữ chỗ");
    expect(reasonText(null, "PAID")).toBeNull();
  });
});

describe("tháng", () => {
  it("currentMonth theo giờ Việt Nam", () => {
    expect(currentMonth(new Date(NOW))).toBe("2026-10");
  });
  it("recentMonths: mới → cũ, qua năm", () => {
    const m = recentMonths(new Date("2026-02-10T00:00:00Z"), 4);
    expect(m.map((x) => x.value)).toEqual(["2026-02", "2026-01", "2025-12", "2025-11"]);
    expect(m[0].label).toBe("Tháng 02/2026");
  });
});

describe("legacyOrderRedirect", () => {
  it("?order=<id>&open=refund → trang chi tiết mở hộp hoàn", () => {
    expect(legacyOrderRedirect("?order=12&open=refund")).toBe("/orders/detail/?id=12&open=refund");
    expect(legacyOrderRedirect("?order=12")).toBe("/orders/detail/?id=12");
  });
  it("không hợp lệ → null", () => {
    expect(legacyOrderRedirect("")).toBeNull();
    expect(legacyOrderRedirect("?order=abc")).toBeNull();
    expect(legacyOrderRedirect("?order=0")).toBeNull();
    expect(legacyOrderRedirect("?order=1;drop")).toBeNull();
  });
});

describe("parseId", () => {
  it("chỉ nhận số nguyên dương", () => {
    expect(parseId("?id=7")).toBe(7);
    expect(parseId("?id=0")).toBeNull();
    expect(parseId("?id=-3")).toBeNull();
    expect(parseId("?id=1.5")).toBeNull();
    expect(parseId("?id=0901234567890123")).toBeNull();
    expect(parseId("")).toBeNull();
  });
});

describe("overRefundMax (F2c)", () => {
  it("vượt mức còn hoàn được thì true; bằng hoặc thiếu số thì false", () => {
    expect(overRefundMax("400000", "390000")).toBe(true);
    expect(overRefundMax("390000", "390000")).toBe(false);
    expect(overRefundMax("", "390000")).toBe(false);
  });
});

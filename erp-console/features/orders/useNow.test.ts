import { describe, expect, it } from "vitest";
import { holdLeftText, mmss } from "./useNow";

describe("holdLeftText (L5: ô đếm ngược tự giữ đồng hồ)", () => {
  const until = "2026-10-02T03:00:00Z";
  const end = new Date(until).getTime();
  it("đơn Giữ chỗ còn giờ: mm:ss", () => {
    expect(holdLeftText("BOOKED", until, end - 65_000)).toBe("01:05");
  });
  it("qua mốc: 00:00, không âm", () => {
    expect(holdLeftText("BOOKED", until, end + 5_000)).toBe("00:00");
  });
  it("không phải Giữ chỗ hoặc thiếu mốc: null", () => {
    expect(holdLeftText("PAID", until, end - 1000)).toBeNull();
    expect(holdLeftText("BOOKED", null, end)).toBeNull();
  });
});

describe("mmss", () => {
  it("đếm lùi và đánh dấu hết giờ", () => {
    expect(mmss("2026-10-02T03:00:00Z", new Date("2026-10-02T02:59:00Z").getTime())?.text).toBe("01:00");
    expect(mmss("2026-10-02T03:00:00Z", new Date("2026-10-02T03:00:01Z").getTime())?.over).toBe(true);
    expect(mmss(null, 0)).toBeNull();
  });
});

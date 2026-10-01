import { describe, expect, it } from "vitest";
import { lookupHref, toLookupCard } from "./lookups";
import { mockLookup } from "./mockLookups";

const KINDS = ["batch", "item", "delivery", "order"] as const;

describe("toLookupCard", () => {
  it("không bao giờ lộ giá vốn hay dữ liệu cá nhân của khách", () => {
    for (const kind of KINDS) {
      const raw = mockLookup(kind, 1).body as Record<string, unknown>;
      const card = toLookupCard(kind, 1, raw);
      const text = JSON.stringify(card);
      expect(text).not.toContain("123456"); // landed_unit_cost
      expect(text).not.toContain("Khách mẫu");
      expect(text).not.toContain("0900000");
      expect(text).not.toContain("Địa chỉ mẫu");
      expect(text).not.toContain("Người nhận mẫu");
    }
  });
  it("lô: hiện mã lô, tồn còn bán, kho", () => {
    const card = toLookupCard("batch", 7, mockLookup("batch", 7).body as Record<string, unknown>);
    expect(card.title).toBe("CA01-261001-AB12C");
    expect(card.rows.map((r) => r.label)).toEqual(expect.arrayContaining(["Mặt hàng", "Còn bán", "Kho"]));
  });
  it("trang đầy đủ trỏ đúng route chi tiết", () => {
    expect(lookupHref("batch", 7)).toBe("/inventory/detail/?id=7");
    expect(lookupHref("order", "SO1")).toBe("/orders/detail/?id=SO1");
  });
  it("thiếu dữ liệu → bỏ dòng, không in 'undefined'", () => {
    const card = toLookupCard("order", 9, {});
    expect(card.title).toBe("Đơn 9");
    expect(JSON.stringify(card)).not.toContain("undefined");
  });
});

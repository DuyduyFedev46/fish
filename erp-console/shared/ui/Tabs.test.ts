// Tabs: `?tab=` đọc/ghi (ED-01-AC4). Phần chạy với history thật (pushState, Back) kiểm ở e2e/ed_batch1_shell.py.
import { describe, expect, it } from "vitest";
import { tabFromSearch, tabHref } from "@/shared/ui/Tabs";

const KEYS = ["all", "pay", "ref"];

describe("tabFromSearch", () => {
  it("đọc khoá hợp lệ từ ?tab=", () => {
    expect(tabFromSearch("?tab=pay", KEYS, "all")).toBe("pay");
  });
  it("thiếu, rỗng, khoá lạ hoặc rác -> tab mặc định", () => {
    for (const s of ["", "?", "?tab=", "?tab=xyz", "?tab=<script>", "?other=pay", "?tab=PAY"]) {
      expect(tabFromSearch(s, KEYS, "all"), s).toBe("all");
    }
  });
});

describe("tabHref", () => {
  const at = (search: string, hash = "") => ({ pathname: "/inventory/", search, hash });

  it("chọn tab khác mặc định -> thêm ?tab=", () => {
    expect(tabHref(at(""), "pay", "all")).toBe("/inventory/?tab=pay");
  });
  it("chọn tab mặc định -> bỏ ?tab=, không để dấu ? thừa", () => {
    expect(tabHref(at("?tab=pay"), "all", "all")).toBe("/inventory/");
  });
  it("giữ nguyên tham số khác và #hash", () => {
    expect(tabHref(at("?q=ca&tab=pay", "#top"), "ref", "all")).toBe("/inventory/?q=ca&tab=ref#top");
    expect(tabHref(at("?q=ca&tab=pay"), "all", "all")).toBe("/inventory/?q=ca");
  });
  it("chỉ ghi khoá tab, không ghi gì khác vào URL", () => {
    expect(tabHref(at(""), "pay", "all")).not.toMatch(/phone|name|address/i);
  });
});

describe("tham số tab tuỳ chọn (một trang có hai thanh tab)", () => {
  it("đọc/ghi đúng tên tham số, không đụng ?tab=", () => {
    expect(tabFromSearch("?status=resolved", ["open", "resolved"], "open", "status")).toBe("resolved");
    expect(tabFromSearch("?tab=resolved", ["open", "resolved"], "open", "status")).toBe("open");
    const loc = { pathname: "/orders/payments/", search: "?tab=x", hash: "" };
    expect(tabHref(loc, "resolved", "open", "status")).toBe("/orders/payments/?tab=x&status=resolved");
    expect(tabHref({ ...loc, search: "?status=resolved" }, "open", "open", "status")).toBe("/orders/payments/");
  });
});

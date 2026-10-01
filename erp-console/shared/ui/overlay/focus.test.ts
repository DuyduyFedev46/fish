import { describe, expect, it } from "vitest";
import { trapTarget } from "./focus";

const contains = (items: string[], root: string) => (el: string | null) => el !== null && (el === root || items.includes(el));

describe("trapTarget (giữ Tab trong hộp thoại)", () => {
  const items = ["a", "b", "c"];
  const has = contains(items, "box");

  it("Tab ở phần tử cuối → quay về đầu", () => {
    expect(trapTarget(items, "c", "box", false, has)).toBe("a");
  });
  it("Shift+Tab ở phần tử đầu (hoặc ở chính hộp) → nhảy xuống cuối", () => {
    expect(trapTarget(items, "a", "box", true, has)).toBe("c");
    expect(trapTarget(items, "box", "box", true, has)).toBe("c");
  });
  it("giữa vùng → để trình duyệt tự đi", () => {
    expect(trapTarget(items, "b", "box", false, has)).toBeNull();
    expect(trapTarget(items, "b", "box", true, has)).toBeNull();
  });
  it("focus đang lạc ra ngoài hộp → kéo về phần tử đầu", () => {
    expect(trapTarget(items, "outside", "box", false, has)).toBe("a");
    expect(trapTarget(items, null, "box", true, has)).toBe("a");
  });
  it("hộp không có phần tử bấm được → giữ ở chính hộp", () => {
    expect(trapTarget([], null, "box", false, contains([], "box"))).toBe("box");
  });
});

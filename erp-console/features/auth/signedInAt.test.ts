import { beforeEach, describe, expect, it, vi } from "vitest";
import { SIGNED_IN_KEY, forgetSignedIn, readSignedIn, rememberSignedIn } from "./signedInAt";

// Môi trường test là node (không có jsdom) → dựng localStorage giả tối thiểu.
const store = new Map<string, string>();
const fake = {
  getItem: (k: string) => store.get(k) ?? null,
  setItem: (k: string, v: string) => void store.set(k, v),
  removeItem: (k: string) => void store.delete(k),
};

describe("signedInAt", () => {
  beforeEach(() => {
    store.clear();
    vi.stubGlobal("window", { localStorage: fake });
  });

  it("nhớ mốc giờ ISO rồi đọc lại đúng", () => {
    rememberSignedIn(new Date("2026-10-01T00:58:00.000Z"));
    expect(readSignedIn()).toBe("2026-10-01T00:58:00.000Z");
  });

  it("chỉ lưu mốc giờ, không có dữ liệu nào khác", () => {
    rememberSignedIn();
    expect([...store.keys()]).toEqual([SIGNED_IN_KEY]);
    expect(store.get(SIGNED_IN_KEY)).toMatch(/^\d{4}-\d{2}-\d{2}T/);
  });

  it("đăng xuất thì xoá", () => {
    rememberSignedIn();
    forgetSignedIn();
    expect(readSignedIn()).toBeNull();
  });

  it("chuỗi lạ (bị sửa tay) coi như không có", () => {
    store.set(SIGNED_IN_KEY, "không phải ngày");
    expect(readSignedIn()).toBeNull();
  });

  it("không có localStorage (chế độ riêng tư) thì bỏ qua, không ném lỗi", () => {
    vi.stubGlobal("window", {
      localStorage: {
        getItem: () => {
          throw new Error("blocked");
        },
        setItem: () => {
          throw new Error("blocked");
        },
        removeItem: () => {
          throw new Error("blocked");
        },
      },
    });
    expect(() => rememberSignedIn()).not.toThrow();
    expect(() => forgetSignedIn()).not.toThrow();
    expect(readSignedIn()).toBeNull();
  });
});

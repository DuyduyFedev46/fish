// Lô 17b TL15-L4: mọi đường kết thúc phiên xoá cả token lẫn mốc giờ đăng nhập.
import { readFileSync } from "node:fs";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getToken, setToken } from "@/shared/lib/token";
import { endSession } from "./session";
import { readSignedIn, rememberSignedIn } from "./signedInAt";

const store = new Map<string, string>();
const fake = {
  getItem: (k: string) => store.get(k) ?? null,
  setItem: (k: string, v: string) => void store.set(k, v),
  removeItem: (k: string) => void store.delete(k),
};

describe("endSession", () => {
  beforeEach(() => {
    store.clear();
    vi.stubGlobal("window", { localStorage: fake });
  });

  it("xoá token và mốc giờ đăng nhập", () => {
    setToken("t");
    rememberSignedIn();
    endSession();
    expect(getToken()).toBeNull();
    expect(readSignedIn()).toBeNull();
  });

  it("AuthProvider không còn xoá token trần (401, Đăng xuất, đăng nhập lỗi đều qua endSession)", () => {
    const src = readFileSync(new URL("./components/AuthProvider.tsx", import.meta.url), "utf8");
    expect(src).not.toMatch(/setToken\(null\)/);
    expect((src.match(/endSession\(\)/g) ?? []).length).toBeGreaterThanOrEqual(3);
  });
});

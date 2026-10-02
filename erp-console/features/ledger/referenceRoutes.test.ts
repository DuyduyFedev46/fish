import { existsSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { REFERENCE_ROUTES, referenceHref } from "./referenceRoutes";

const APP = path.resolve(__dirname, "../../app/(console)");

describe("referenceHref", () => {
  it("mọi route đánh dấu ready có trang thật (không link chết)", () => {
    for (const r of REFERENCE_ROUTES.filter((x) => x.ready)) {
      expect(existsSync(path.join(APP, r.page, "page.tsx")), r.page).toBe(true);
    }
  });
  it("lô → trang chi tiết lô; loại chưa có trang → null (hiện chữ thường)", () => {
    expect(referenceHref({ kind: "batch", id: 7 })).toBe("/inventory/detail/?id=7");
    expect(referenceHref({ kind: "weird", id: 7 })).toBeNull();
    expect(referenceHref(null)).toBeNull();
  });
  it("id không hợp lệ → null", () => {
    expect(referenceHref({ kind: "batch", id: 0 })).toBeNull();
    expect(referenceHref({ kind: "batch", id: 1.5 })).toBeNull();
  });
});

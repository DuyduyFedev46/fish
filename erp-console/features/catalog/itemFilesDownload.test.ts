// FISH-66 S3, S4: tải file Excel mặt hàng — đọc header, lỗi không trả blob hỏng, quyền nhập, đường dẫn tải.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { exportItemsPath } from "./itemFilesApi";
import { catalogAbility, CATALOG_PERM, IMPORT_PERMS } from "./permissions";
import { EMPTY_ITEM_PARAMS } from "./types";

beforeEach(() => {
  vi.resetModules();
});
afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

const XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

describe("header của file tải", () => {
  it("đọc tên file từ Content-Disposition (dạng thường và dạng filename*)", async () => {
    const { filenameFromDisposition } = await import("@/shared/lib/http");
    expect(filenameFromDisposition('attachment; filename="hang-ban-20261114-1530.xlsx"')).toBe("hang-ban-20261114-1530.xlsx");
    expect(filenameFromDisposition("attachment; filename*=UTF-8''h%C3%A0ng-b%C3%A1n.xlsx")).toBe("hàng-bán.xlsx");
    expect(filenameFromDisposition(null)).toBeNull();
    expect(filenameFromDisposition("attachment")).toBeNull();
  });

  it("đọc X-Row-Count: số nguyên không âm, còn lại là null", async () => {
    const { rowCountFromHeader } = await import("@/shared/lib/http");
    expect(rowCountFromHeader("4")).toBe(4);
    expect(rowCountFromHeader("0")).toBe(0);
    expect(rowCountFromHeader(null)).toBeNull();
    expect(rowCountFromHeader("")).toBeNull();
    expect(rowCountFromHeader("abc")).toBeNull();
    expect(rowCountFromHeader("-1")).toBeNull();
  });
});

describe("apiDownload chế độ thật", () => {
  it("200: trả blob, tên file và số món từ header", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "0");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("bytes", { status: 200, headers: { "Content-Disposition": 'attachment; filename="mau-hang-ban.xlsx"', "X-Row-Count": "1", "Content-Type": XLSX } })),
    );
    const { apiDownload } = await import("@/shared/lib/http");
    const file = await apiDownload("/api/catalog/items/export-template/");
    expect(file.filename).toBe("mau-hang-ban.xlsx");
    expect(file.rowCount).toBe(1);
    expect(file.blob.size).toBeGreaterThan(0);
  });

  it("thiếu header: dùng tên dự phòng, số món null", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "0");
    vi.stubGlobal("fetch", vi.fn(async () => new Response("bytes", { status: 200, headers: { "Content-Type": XLSX } })));
    const { apiDownload } = await import("@/shared/lib/http");
    const file = await apiDownload("/x/", { fallbackName: "hang-ban.xlsx" });
    expect(file.filename).toBe("hang-ban.xlsx");
    expect(file.rowCount).toBeNull();
  });

  it("L3: 200 nhưng Content-Type là text/html (proxy lỗi) thì ném ApiError, không lưu file hỏng", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "0");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("<html>proxy error</html>", { status: 200, headers: { "Content-Type": "text/html; charset=utf-8" } })),
    );
    const { apiDownload, ApiError } = await import("@/shared/lib/http");
    await expect(apiDownload("/x/")).rejects.toBeInstanceOf(ApiError);
  });

  it("500: ném ApiError, không trả blob (S3-AC9)", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "0");
    vi.stubGlobal("fetch", vi.fn(async () => new Response("<html>lỗi</html>", { status: 500 })));
    const { apiDownload, ApiError } = await import("@/shared/lib/http");
    const error = await apiDownload("/x/").catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as InstanceType<typeof ApiError>).status).toBe(500);
  });

  it("200 nhưng thân rỗng: coi là lỗi, không lưu file rỗng", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "0");
    vi.stubGlobal("fetch", vi.fn(async () => new Response("", { status: 200 })));
    const { apiDownload, ApiError } = await import("@/shared/lib/http");
    await expect(apiDownload("/x/")).rejects.toBeInstanceOf(ApiError);
  });

  it("400 INVALID_FILTER giữ mã lỗi và câu của BE", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "0");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ code: "INVALID_FILTER", detail: "Tham số item_type có giá trị không hợp lệ." }), { status: 400 })),
    );
    const { apiDownload } = await import("@/shared/lib/http");
    const error = await apiDownload("/x/").catch((e) => e);
    expect(error.status).toBe(400);
    expect(error.code).toBe("INVALID_FILTER");
    expect(error.message).toBe("Tham số item_type có giá trị không hợp lệ.");
  });

  it("403 giữ status 403", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "0");
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: "Thiếu quyền: catalog.view_item" }), { status: 403 })));
    const { apiDownload } = await import("@/shared/lib/http");
    const error = await apiDownload("/x/").catch((e) => e);
    expect(error.status).toBe(403);
  });

  it("mất mạng: ApiError status 0", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK", "0");
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("Failed to fetch"))));
    const { apiDownload } = await import("@/shared/lib/http");
    const error = await apiDownload("/x/").catch((e) => e);
    expect(error.status).toBe(0);
  });
});

describe("đường dẫn tải danh sách", () => {
  it("không bộ lọc: đường dẫn trần", () => {
    expect(exportItemsPath(EMPTY_ITEM_PARAMS)).toBe("/api/catalog/items/export/");
  });
  it("gửi đúng bộ lọc máy chủ, không có page", () => {
    const path = exportItemsPath({ group: "3", type: "SIMPLE", active: "1", hasImage: "0" });
    expect(path).toBe("/api/catalog/items/export/?item_group=3&item_type=SIMPLE&is_active=1&has_image=0");
    expect(path).not.toContain("page=");
  });
});

describe("quyền nhập Excel", () => {
  const all = [...IMPORT_PERMS];
  it("đúng 4 chuỗi quyền của 02b §3.1", () => {
    expect([...IMPORT_PERMS]).toEqual(["catalog.add_item", "catalog.change_item", "catalog.add_itemprice", "catalog.change_itemprice"]);
  });
  it("đủ cả 4 thì được nhập", () => {
    expect(catalogAbility(all).canImport).toBe(true);
  });
  it("thiếu bất kỳ quyền nào thì không được nhập", () => {
    for (const missing of all) {
      expect(catalogAbility(all.filter((p) => p !== missing)).canImport).toBe(false);
    }
  });
  it("Quản lý và NV kho (chỉ xem) không được nhập", () => {
    expect(catalogAbility([CATALOG_PERM.viewItem, CATALOG_PERM.viewItemPrice]).canImport).toBe(false);
    expect(catalogAbility([CATALOG_PERM.viewItem]).canImport).toBe(false);
  });
});

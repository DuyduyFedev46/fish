import { describe, expect, it } from "vitest";
import { canView, GROUP, PERM, visibleNav, type Viewer } from "@/shared/lib/nav";
import {
  mockCreateCategory,
  mockGetEntryCounts,
  mockListCategories,
  mockListEntries,
  mockUpdateCategory,
} from "./mock";

describe("CMS-01 & CMS-02 Console Tests", () => {
  it("CMS-01-AC6: NV kho không thấy mục Nội dung trong menu và không có quyền xem", () => {
    const nvKhoUser: Viewer = {
      groups: [GROUP.nvKho],
      permissions: [PERM.viewDashboard, PERM.viewBatch, PERM.viewItem],
      can_view_profit: false,
      home: "dashboard",
    };

    const nav = visibleNav(nvKhoUser);
    expect(nav.some((item) => item.key === "content")).toBe(false);
    expect(nav.some((item) => item.key === "content-categories")).toBe(false);
    expect(canView(nvKhoUser, "content")).toBe(false);
    expect(canView(nvKhoUser, "content-categories")).toBe(false);
  });

  it("CMS-01-AC7: Quản lý thấy mục Nội dung trong menu và có quyền xem", () => {
    const quanLyUser: Viewer = {
      groups: [GROUP.quanLy],
      permissions: [
        PERM.viewDashboard,
        PERM.viewSalesOrder,
        PERM.viewContentEntry,
        PERM.publishContentEntry,
      ],
      can_view_profit: false,
      home: "dashboard",
    };

    const nav = visibleNav(quanLyUser);
    expect(nav.some((item) => item.key === "content")).toBe(true);
    expect(nav.some((item) => item.key === "content-categories")).toBe(true);
    expect(canView(quanLyUser, "content")).toBe(true);
    expect(canView(quanLyUser, "content-categories")).toBe(true);
  });

  it("CMS-02: mock chuyên mục hoạt động đúng nghiệp vụ (thứ tự, tạo slug tiếng Việt, cập nhật)", () => {
    const cats = mockListCategories();
    expect(cats.length).toBeGreaterThan(0);
    // Kiểm tra sắp xếp theo order
    for (let i = 0; i < cats.length - 1; i++) {
      expect(cats[i].order).toBeLessThanOrEqual(cats[i + 1].order);
    }

    // Tạo chuyên mục mới
    const newCat = mockCreateCategory({
      name: "Cá biển tươi sống",
      description: "Các loại cá đánh bắt trong ngày",
      order: 10,
    });
    expect(newCat.slug).toBe("ca-bien-tuoi-song");
    expect(newCat.is_active).toBe(true);
    expect(newCat.published_count).toBe(0);

    // Cập nhật chuyên mục
    const updated = mockUpdateCategory(newCat.id, {
      name: "Cá biển tươi ngon",
      is_active: false,
    });
    expect(updated.name).toBe("Cá biển tươi ngon");
    expect(updated.slug).toBe("ca-bien-tuoi-song"); // Slug không đổi khi đổi tên
    expect(updated.is_active).toBe(false);
  });

  it("mock danh sách bài và đếm trạng thái", () => {
    const entries = mockListEntries();
    expect(Array.isArray(entries.results)).toBe(true);

    const counts = mockGetEntryCounts();
    expect(counts).toHaveProperty("draft");
    expect(counts).toHaveProperty("pending_review");
    expect(counts).toHaveProperty("published");
    expect(counts).toHaveProperty("unpublished");
  });
});

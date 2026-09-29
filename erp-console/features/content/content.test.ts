import { describe, expect, it } from "vitest";
import { canView, GROUP, PERM, visibleNav, type Viewer } from "@/shared/lib/nav";
import {
  mockCreateCategory,
  mockCreateEntry,
  mockDeleteEntry,
  mockGetEntry,
  mockGetEntryCounts,
  mockListCategories,
  mockListEntries,
  mockUpdateCategory,
  mockUpdateEntry,
  mockUpdateImageAlt,
  mockUploadEntryImage,
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

  describe("CMS-03 & CMS-05: Soạn nháp và Quản lý ảnh bài viết", () => {
    it("CMS-03-AC1, AC2: Tạo bài nháp để trống slug -> tự sinh slug tiếng Việt chuẩn, status=draft, row_version=1", () => {
      const entry = mockCreateEntry({
        kind: "post",
        title: "Cách rã đông cá thu tươi ngon!!",
        category: 1,
      });

      expect(entry.id).toBeGreaterThan(0);
      expect(entry.status).toBe("draft");
      expect(entry.slug).toBe("cach-ra-dong-ca-thu-tuoi-ngon");
      expect(entry.row_version).toBe(1);
      expect(entry.published_version).toBeNull();
      expect(entry.first_published_at).toBeNull();
    });

    it("CMS-03-AC3: Trùng slug -> quăng lỗi BR-ND-04", () => {
      const created = mockCreateEntry({
        kind: "post",
        title: "Bài kiểm tra trùng slug",
        slug: "bai-kiem-tra-trung-slug",
      });
      expect(created.slug).toBe("bai-kiem-tra-trung-slug");

      expect(() => {
        mockCreateEntry({
          kind: "post",
          title: "Bài trùng",
          slug: "bai-kiem-tra-trung-slug",
        });
      }).toThrowError();
    });

    it("CMS-03-AC7: Xung đột sửa trùng STALE_VERSION khi row_version không khớp", () => {
      const entry = mockCreateEntry({
        kind: "post",
        title: "Bài kiểm tra xung đột",
      });

      // Lưu lần đầu thành công -> row_version tăng lên 2
      const updated = mockUpdateEntry(entry.id, {
        row_version: entry.row_version,
        title: "Tiêu đề sửa lần 1",
      });
      expect(updated.row_version).toBe(2);

      // Lưu lại với row_version cũ (1) -> báo STALE_VERSION
      expect(() => {
        mockUpdateEntry(entry.id, {
          row_version: 1,
          title: "Tiêu đề sửa lần 2 bị chậm",
        });
      }).toThrowError(/STALE_VERSION/);
    });

    it("CMS-03-AC8: Xoá nháp chưa từng đăng thành công", () => {
      const entry = mockCreateEntry({
        kind: "post",
        title: "Bài nháp cần xoá",
      });
      expect(mockGetEntry(entry.id)).toBeDefined();

      mockDeleteEntry(entry.id);
      expect(() => mockGetEntry(entry.id)).toThrowError();
    });

    it("CMS-03-AC9: Xoá bài đã từng đăng -> từ chối lỗi BR-ND-02", () => {
      const entry = mockCreateEntry({
        kind: "post",
        title: "Bài đã từng đăng",
      });
      // Giả lập bài đã từng xuất bản
      entry.published_version = 1;
      entry.first_published_at = new Date().toISOString();

      expect(() => {
        mockDeleteEntry(entry.id);
      }).toThrowError(/BR-ND-02/);
    });

    it("CMS-05-AC3, AC4: Tải ảnh, alt mặc định theo tiêu đề bài, sửa alt và trần 20 ảnh", () => {
      const entry = mockCreateEntry({
        kind: "post",
        title: "Cá nục hấp hành gừng",
      });

      // Tải ảnh không truyền alt -> alt lấy theo tiêu đề bài
      const fakeFile = new File(["dummy"], "ca.jpg", { type: "image/jpeg" });
      const img1 = mockUploadEntryImage(entry.id, fakeFile);
      expect(img1.id).toBeGreaterThan(0);
      expect(img1.alt).toBe("Cá nục hấp hành gừng");
      expect(img1.urls.sm).toContain(".webp");

      // Cập nhật alt ảnh
      const updatedImg = mockUpdateImageAlt(img1.id, "Đĩa cá nục sau khi hấp chín");
      expect(updatedImg.alt).toBe("Đĩa cá nục sau khi hấp chín");

      // Nạp thêm 19 ảnh để đủ 20 ảnh
      for (let i = 0; i < 19; i++) {
        mockUploadEntryImage(entry.id, fakeFile, `Ảnh số ${i + 2}`);
      }
      expect(mockGetEntry(entry.id).images.length).toBe(20);

      // Tải ảnh thứ 21 -> lỗi BR-ND-07
      expect(() => {
        mockUploadEntryImage(entry.id, fakeFile, "Ảnh thứ 21");
      }).toThrowError(/BR-ND-07/);
    });
  });
});


import { describe, expect, it } from "vitest";
import { canView, GROUP, PERM, visibleNav, type Viewer } from "@/shared/lib/nav";
import {
  mockCreateCategory,
  mockCreateEntry,
  mockDeleteEntry,
  mockDiscardChanges,
  mockGetEntry,
  mockGetEntryCounts,
  mockGetGoliveStatus,
  mockListCategories,
  mockListEntries,
  mockPublishEntry,
  mockUnpublishEntry,
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

    it("CMS-07 & CMS-08: Đăng bài, xác nhận checklist 5 mục, cảnh báo an toàn và acknowledge_warnings", () => {
      const entry = mockCreateEntry({
        kind: "post",
        title: "Kinh nghiệm chọn cá thu ngon",
        category: 1,
        excerpt: "Bí quyết chọn cá tươi ngon mắt trong mang đỏ.",
      });

      // Tạo ảnh và gán cover
      const fakeFile = new File(["dummy"], "cov.jpg", { type: "image/jpeg" });
      const img = mockUploadEntryImage(entry.id, fakeFile, "Đĩa cá thu");
      mockUpdateEntry(entry.id, {
        row_version: entry.row_version,
        cover_image: img.id,
        body: {
          type: "doc",
          blocks: [
            {
              type: "paragraph",
              children: [{ text: "Liên hệ tư vấn mua cá qua 0912 345 678 giá mua cảng tốt nhất." }],
            },
          ],
        },
      });

      const updated = mockGetEntry(entry.id);

      // 1. Publish khi chưa xác nhận checklist -> 400 BR-ND-13
      expect(() => {
        mockPublishEntry(entry.id, {
          row_version: updated.row_version,
          checklist_confirmed: false,
        });
      }).toThrowError(/BR-ND-13/);

      // 2. Publish khi có cảnh báo SĐT / giá vốn và acknowledge_warnings=false -> 409 CONTENT_WARNINGS
      try {
        mockPublishEntry(entry.id, {
          row_version: updated.row_version,
          checklist_confirmed: true,
          acknowledge_warnings: false,
        });
        expect.unreachable("Phải ném lỗi CONTENT_WARNINGS");
      } catch (err: any) {
        expect(err.code).toBe("CONTENT_WARNINGS");
        expect(err.warnings.length).toBeGreaterThan(0);
        expect(err.warnings.some((w: any) => w.type === "phone_like")).toBe(true);
        expect(err.warnings.some((w: any) => w.type === "cost_keyword")).toBe(true);
      }

      // 3. Publish với acknowledge_warnings=true -> Thành công 200, status=published, slug_locked=true
      const pubRes = mockPublishEntry(entry.id, {
        row_version: updated.row_version,
        checklist_confirmed: true,
        acknowledge_warnings: true,
      });

      expect(pubRes.status).toBe("published");
      expect(pubRes.version).toBe(1);
      expect(pubRes.public_url).toContain("/bai-viet?slug=");

      const finalEntry = mockGetEntry(entry.id);
      expect(finalEntry.status).toBe("published");
      expect(finalEntry.slug_locked).toBe(true);
      expect(finalEntry.row_version).toBe(updated.row_version + 1);

      // 4. Publish lại với row_version cũ -> 409 STALE_VERSION
      expect(() => {
        mockPublishEntry(entry.id, {
          row_version: updated.row_version,
          checklist_confirmed: true,
        });
      }).toThrowError(/STALE_VERSION/);
    });
  });

  describe("CMS-12 & CMS-10: Gỡ bài viết và Huỷ thay đổi nháp", () => {
    it("CMS-12: Gỡ bài viết đã xuất bản, kiểm tra lý do và bất biến", () => {
      // 1. Tạo và đăng 1 bài viết
      const entry = mockCreateEntry({
        kind: "post",
        title: "Bài viết để gỡ thử",
        category: 1,
        excerpt: "Tóm tắt bài viết",
      });
      const fakeFile = new File(["dummy"], "cov.jpg", { type: "image/jpeg" });
      const img = mockUploadEntryImage(entry.id, fakeFile, "Ảnh bìa");
      mockUpdateEntry(entry.id, {
        row_version: entry.row_version,
        cover_image: img.id,
        body: {
          type: "doc",
          blocks: [{ type: "paragraph", children: [{ text: "Nội dung chuẩn" }] }],
        },
      });
      const published = mockPublishEntry(entry.id, {
        row_version: 2,
        checklist_confirmed: true,
        acknowledge_warnings: true,
      });
      expect(published.status).toBe("published");

      // 2. Gỡ bài với row_version cũ -> STALE_VERSION 409
      expect(() => {
        mockUnpublishEntry(entry.id, {
          row_version: 1,
          reason: "wrong_content",
        });
      }).toThrowError(/STALE_VERSION/);

      // 3. Gỡ bài với lý do không hợp lệ -> BR-ND-15
      expect(() => {
        mockUnpublishEntry(entry.id, {
          row_version: 3,
          reason: "invalid_reason" as any,
        });
      }).toThrowError(/BR-ND-15/);

      // 4. Gỡ bài thành công với lý do 'wrong_content'
      const unpubRes = mockUnpublishEntry(entry.id, {
        row_version: 3,
        reason: "wrong_content",
      });
      expect(unpubRes.status).toBe("unpublished");
      expect(unpubRes.return_reason).toBe("wrong_content");
      expect(unpubRes.row_version).toBe(4);

      // 5. Gỡ bài khi bài không ở trạng thái published -> 400 BR-ND-01
      expect(() => {
        mockUnpublishEntry(entry.id, {
          row_version: 4,
          reason: "wrong_content",
        });
      }).toThrowError(/BR-ND-01/);

      // 6. Gỡ trang go-live có page_role -> 400 BR-ND-16
      const goLivePage = mockCreateEntry({
        kind: "page",
        title: "Chính sách bảo mật",
        excerpt: "Cam kết bảo mật thông tin khách hàng Cá Về",
      });
      mockUpdateEntry(goLivePage.id, {
        row_version: goLivePage.row_version,
        page_role: "privacy",
        body: {
          type: "doc",
          blocks: [{ type: "paragraph", children: [{ text: "Nội dung điều khoản bảo mật chi tiết." }] }],
        },
      });
      mockPublishEntry(goLivePage.id, {
        row_version: 2,
        checklist_confirmed: true,
        acknowledge_warnings: true,
      });
      expect(() => {
        mockUnpublishEntry(goLivePage.id, {
          row_version: 3,
          reason: "wrong_content",
        });
      }).toThrowError(/BR-ND-16/);
    });

    it("CMS-10: Sửa nháp bài đang đăng và huỷ thay đổi (discard_changes)", () => {
      // 1. Tạo và đăng 1 bài viết
      const entry = mockCreateEntry({
        kind: "post",
        title: "Bài viết gốc trước khi sửa",
        category: 1,
        excerpt: "Tóm tắt gốc",
      });
      const fakeFile = new File(["dummy"], "cov.jpg", { type: "image/jpeg" });
      const img = mockUploadEntryImage(entry.id, fakeFile, "Ảnh bìa gốc");
      mockUpdateEntry(entry.id, {
        row_version: entry.row_version,
        cover_image: img.id,
        body: {
          type: "doc",
          blocks: [{ type: "paragraph", children: [{ text: "Nội dung gốc phiên bản 1" }] }],
        },
      });
      mockPublishEntry(entry.id, {
        row_version: 2,
        checklist_confirmed: true,
        acknowledge_warnings: true,
      });

      // 2. Sửa nháp tiêu đề và nội dung của bài đang đăng
      const updated = mockUpdateEntry(entry.id, {
        row_version: 3,
        title: "Tiêu đề nháp mới đã bị sửa",
        body: {
          type: "doc",
          blocks: [{ type: "paragraph", children: [{ text: "Nội dung nháp mới" }] }],
        },
      });
      expect(updated.title).toBe("Tiêu đề nháp mới đã bị sửa");
      expect(updated.has_unpublished_changes).toBe(true);

      // 3. Huỷ thay đổi với row_version cũ -> STALE_VERSION 409
      expect(() => {
        mockDiscardChanges(entry.id, {
          row_version: 2,
        });
      }).toThrowError(/STALE_VERSION/);

      // 4. Huỷ thay đổi thành công -> nạp lại tiêu đề và nội dung gốc, has_unpublished_changes = false
      const discarded = mockDiscardChanges(entry.id, {
        row_version: 4,
      });
      expect(discarded.title).toBe("Bài viết gốc trước khi sửa");
      expect(discarded.has_unpublished_changes).toBe(false);
      expect(discarded.row_version).toBe(5);

      // 5. Thử gọi discard_changes trên bài nháp chưa từng đăng -> 400 BR-ND-01
      const draftOnly = mockCreateEntry({
        kind: "post",
        title: "Bài nháp chưa từng đăng",
      });
      expect(() => {
        mockDiscardChanges(draftOnly.id, {
          row_version: draftOnly.row_version,
        });
      }).toThrowError(/BR-ND-01/);
    });
  });

  describe("CMS-15 Console Tests", () => {
    it("CMS-15-AC7: mockGetGoliveStatus trả đúng danh sách vai trò bắt buộc go-live chưa có bài đăng", () => {
      const status = mockGetGoliveStatus();
      expect(Array.isArray(status.missing_roles)).toBe(true);
      const required = ["privacy", "terms", "refund", "seller_info"];
      for (const r of status.missing_roles) {
        expect(required).toContain(r);
      }
    });
  });
});





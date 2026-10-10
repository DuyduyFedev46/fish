import { describe, expect, it } from "vitest";
import { canView, PERM, visibleNav, type Viewer } from "@/shared/lib/nav";
import { ROLE } from "@/shared/lib/roles";
import { clearDraft, loadDraft, saveDraft } from "@/shared/lib/drafts";
import { warningsOf } from "./contentModel";
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
  mockFetchShopCatalog,
  mockSubmitEntry,
  mockReturnEntry,
  mockFetchEntryVersions,
  mockGetEntryVersion,
  mockRestoreEntryVersion,
  mockOtherEdit,
  mockUseRawBody,
} from "./mock";
import { itemsFromShopCatalog } from "./shopCatalog";
import { bodyToTiptap, tiptapToBody } from "./editor/convert";

describe("CMS-01 & CMS-02 Console Tests", () => {
  it("CMS-01-AC6: NV kho không thấy mục Nội dung trong menu và không có quyền xem", () => {
    const nvKhoUser: Viewer = {
      groups: [ROLE.warehouseStaff],
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
      groups: [ROLE.manager],
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
      // Dùng bài đã đăng có sẵn trong dữ liệu mẫu (mockCreateEntry trả bản sao nên không sửa trực tiếp được).
      const published = mockListEntries({ status: "published" }).results[0];
      expect(published).toBeDefined();

      expect(() => {
        mockDeleteEntry(published.id);
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
        // BE đặt danh sách cảnh báo ở `details.warnings`, không ở chính đối tượng lỗi.
        const warnings = warningsOf(err);
        expect(warnings.length).toBeGreaterThan(0);
        expect(warnings.some((w) => w.type === "phone_like")).toBe(true);
        expect(warnings.some((w) => w.type === "cost_keyword")).toBe(true);
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
      expect(unpubRes.row_version).toBe(4);
      // Giống máy chủ thật: chỉ trả { status, row_version }, lý do đọc lại từ chi tiết bài.
      expect(Object.keys(unpubRes).sort()).toEqual(["row_version", "status"]);
      expect(mockGetEntry(entry.id).return_reason).toBe("wrong_content");

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

  describe("CMS-06 Console Tests", () => {
    it("CMS-06-AC1: mockFetchShopCatalog trả {groups, items} đúng 02b §3.1, không rò giá vốn, không số kg tồn", () => {
      const data = mockFetchShopCatalog();
      expect(Array.isArray(data)).toBe(false);
      expect(Array.isArray(data.groups)).toBe(true);
      const items = itemsFromShopCatalog(data);
      expect(items.length).toBeGreaterThan(0);
      const forbidden = ["unit_cost", "purchase_rate", "cost", "landed_cost", "sellable_qty"];
      for (const it of items) {
        expect(typeof it.item_code).toBe("string");
        expect(typeof it.name).toBe("string");
        expect(typeof it.price).toBe("string");
        expect(["in", "low", "out"]).toContain(it.stock_level);
        for (const f of forbidden) {
          expect(f in it).toBe(false);
        }
      }
    });

    it("H1 review lô 1: itemsFromShopCatalog đọc .items của {groups, items}", () => {
      const items = itemsFromShopCatalog({
        groups: [{ slug: "muc", name: "Mực", item_count: 1 }],
        items: [{ item_code: "MUC-ONG", name: "Mực ống", item_type: "SIMPLE", unit: "kg", price: "278000", stock_level: "low", group: { slug: "muc", name: "Mực" } }],
      });
      expect(items.map((it) => it.item_code)).toEqual(["MUC-ONG"]);
    });

    it("H1 review lô 1: phản hồi sai hình dạng (mảng cũ, thiếu items, null) -> ném lỗi để hộp chọn hiện lỗi, không vỡ", () => {
      expect(() => itemsFromShopCatalog([{ item_code: "A", name: "B" }])).toThrow();
      expect(() => itemsFromShopCatalog({ groups: [] })).toThrow();
      expect(() => itemsFromShopCatalog(null)).toThrow();
    });
  });

  describe("CMS-09, CMS-11 & CMS-04: Vòng đời duyệt, Lịch sử phiên bản & Tự lưu nháp", () => {
    it("CMS-09: Gửi duyệt bài viết (submitEntry) -> pending_review và Trả về nháp (returnEntry) với lý do", () => {
      // 1. Tạo bài nháp đầy đủ điều kiện
      const entry = mockCreateEntry({
        kind: "post",
        title: "Bài viết để gửi duyệt",
        category: 1,
        excerpt: "Tóm tắt bài viết gửi duyệt",
      });
      const fakeFile = new File(["dummy"], "cov.jpg", { type: "image/jpeg" });
      const img = mockUploadEntryImage(entry.id, fakeFile, "Ảnh bìa gửi duyệt");
      mockUpdateEntry(entry.id, {
        row_version: entry.row_version,
        cover_image: img.id,
        body: {
          type: "doc",
          blocks: [{ type: "paragraph", children: [{ text: "Nội dung đạt chuẩn kiểm duyệt" }] }],
        },
      });

      // 2. Gửi duyệt khi chưa nạp đủ điều kiện -> ném lỗi nếu thiếu trường (BR-ND-03)
      // Thử submit với row_version cũ -> STALE_VERSION
      expect(() => {
        mockSubmitEntry(entry.id, {
          row_version: 1,
        });
      }).toThrowError(/STALE_VERSION/);

      // 3. Gửi duyệt thành công với row_version hiện tại (2)
      const submitRes = mockSubmitEntry(entry.id, {
        row_version: 2,
      });
      expect(submitRes.status).toBe("pending_review");
      expect(submitRes.row_version).toBe(3);

      const entryAfterSubmit = mockGetEntry(entry.id);
      expect(entryAfterSubmit.status).toBe("pending_review");

      // 4. Submit lại khi đã ở pending_review -> từ chối BR-ND-01
      expect(() => {
        mockSubmitEntry(entry.id, {
          row_version: 3,
        });
      }).toThrowError(/BR-ND-01/);

      // 5. Trả về nháp với lý do không hợp lệ -> BR-ND-15
      expect(() => {
        mockReturnEntry(entry.id, {
          row_version: 3,
          reason: "invalid_reason" as any,
        });
      }).toThrowError(/BR-ND-15/);

      // 6. Trả về nháp thành công với lý do 'missing_info'
      const returnRes = mockReturnEntry(entry.id, {
        row_version: 3,
        reason: "missing_info",
      });
      expect(returnRes.status).toBe("draft");
      expect(returnRes.return_reason).toBe("missing_info");
      expect(returnRes.row_version).toBe(4);

      const entryAfterReturn = mockGetEntry(entry.id);
      expect(entryAfterReturn.status).toBe("draft");
      expect(entryAfterReturn.return_reason).toBe("missing_info");
    });

    it("CMS-11: Lịch sử phiên bản (fetchEntryVersions) không trả body, và khôi phục (restoreEntryVersion)", () => {
      // 1. Tạo bài viết
      const entry = mockCreateEntry({
        kind: "post",
        title: "Bài viết phiên bản gốc",
        category: 1,
        excerpt: "Tóm tắt bản 1",
      });
      const fakeFile = new File(["dummy"], "cov.jpg", { type: "image/jpeg" });
      const img = mockUploadEntryImage(entry.id, fakeFile, "Ảnh bìa");
      mockUpdateEntry(entry.id, {
        row_version: entry.row_version,
        cover_image: img.id,
        body: {
          type: "doc",
          blocks: [{ type: "paragraph", children: [{ text: "Nội dung phiên bản 1 ban đầu" }] }],
        },
      });

      // Xuất bản phiên bản 1
      mockPublishEntry(entry.id, {
        row_version: 2,
        checklist_confirmed: true,
        acknowledge_warnings: true,
      });

      // Sửa và xuất bản phiên bản 2
      mockUpdateEntry(entry.id, {
        row_version: 3,
        title: "Bài viết phiên bản 2 đã cập nhật",
        body: {
          type: "doc",
          blocks: [{ type: "paragraph", children: [{ text: "Nội dung phiên bản 2 mới hơn" }] }],
        },
      });
      mockPublishEntry(entry.id, {
        row_version: 4,
        checklist_confirmed: true,
        acknowledge_warnings: true,
      });

      // 2. Lấy danh sách lịch sử phiên bản
      const versions = mockFetchEntryVersions(entry.id);
      expect(versions.length).toBe(2);
      expect(versions[0].version).toBe(2); // Giảm dần theo version
      expect(versions[1].version).toBe(1);

      // CMS-11-AC1: Danh sách phiên bản tuyệt đối không chứa field 'body'
      for (const v of versions) {
        expect("body" in v).toBe(false);
        expect(v.title).toBeDefined();
        expect(v.published_at).toBeDefined();
      }

      // 3. Lấy chi tiết phiên bản 1
      const detailV1 = mockGetEntryVersion(entry.id, 1);
      expect(detailV1.version).toBe(1);
      expect(detailV1.title).toBe("Bài viết phiên bản gốc");
      expect(detailV1.body).toBeDefined();

      // 4. Khôi phục phiên bản 1
      const restoreRes = mockRestoreEntryVersion(entry.id, 1, {
        row_version: 5,
      });
      expect(restoreRes.title).toBe("Bài viết phiên bản gốc");
      expect(restoreRes.has_unpublished_changes).toBe(true);
      expect(restoreRes.restored_from).toBe(1);
      expect(restoreRes.row_version).toBe(6);

      const restoredEntry = mockGetEntry(entry.id);
      expect(restoredEntry.title).toBe("Bài viết phiên bản gốc");
      expect(restoredEntry.has_unpublished_changes).toBe(true);
      expect(restoredEntry.restored_from).toBe(1);
    });

    it("CMS-04: Lưu và xoá nháp cục bộ qua drafts helper", () => {
      const store = new Map<string, string>();
      const fakeStorage = {
        getItem: (k: string) => store.get(k) ?? null,
        setItem: (k: string, v: string) => { store.set(k, String(v)); },
        removeItem: (k: string) => { store.delete(k); },
        clear: () => { store.clear(); },
        key: (i: number) => Array.from(store.keys())[i] ?? null,
        get length() { return store.size; },
      };
      const origWindow = (globalThis as any).window;
      (globalThis as any).window = { localStorage: fakeStorage };

      try {
        const formKey = "test_content_entry_999";
        const owner = 42;
        const payload = {
          title: "Nháp tạm thời khi mất mạng",
          slug: "nhap-tam-thoi",
        };

        saveDraft(formKey, owner, payload);
        const loaded = loadDraft<typeof payload>(formKey, owner);
        expect(loaded).toBeDefined();
        expect(loaded?.title).toBe("Nháp tạm thời khi mất mạng");

        clearDraft(formKey);
        const loadedAfterClear = loadDraft<typeof payload>(formKey, owner);
        expect(loadedAfterClear).toBeNull();
      } finally {
        (globalThis as any).window = origWindow;
      }
    });
  });
});

describe("Lô 16 sửa lỗi QA: mở bài không phải là đã sửa", () => {
  it("B16-2: thân bài máy chủ dạng chưa chuẩn hoá khác bản Tiptap trả ra, nên màn soạn phải so theo bản chuẩn hoá", () => {
    expect(mockUseRawBody(42)).toBe(true);
    const raw = mockGetEntry(42).body;
    const normalized = tiptapToBody(bodyToTiptap(raw));
    // Premise của lỗi: sau khi qua trình soạn thảo, thân bài không còn giống từng byte với bản máy chủ.
    expect(JSON.stringify(normalized)).not.toBe(JSON.stringify(raw));
    // Chuẩn hoá lần hai không đổi nữa (ổn định), nên chỉ cần bỏ qua lần phát "update" khi nạp.
    expect(JSON.stringify(tiptapToBody(bodyToTiptap(normalized)))).toBe(JSON.stringify(normalized));
  });

  it("B16-3: người khác sửa thì row_version và tiêu đề đổi", () => {
    const before = mockGetEntry(42);
    const v = mockOtherEdit(42, "Tiêu đề do người khác sửa");
    expect(v).toBe(before.row_version + 1);
    expect(mockGetEntry(42).title).toBe("Tiêu đề do người khác sửa");
  });
});


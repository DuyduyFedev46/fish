# Ghi chú phát triển — CMS viết bài

- **Nhánh làm việc**: `main`
- **Số test gốc BE**: 907 test(s) (chạy lúc bắt đầu Lô 1: `manage.py test` passed 100%, 0 issues).
- **Số test sau Lô 1**: 920 test(s) (tăng 13 test: 2 test `apps.common.tests.test_business_error_extra`, 11 test `apps.content.tests`).

---

## Lô 1: CMS-01 Phân quyền & CMS-02 Quản lý chuyên mục

### Kế hoạch & Thực hiện
1. **Hạ tầng lỗi `BusinessError.extra` (§8.1 `02b-tech-design`)**:
   - `backend/apps/common/exceptions.py`: đảm bảo `self.extra = dict(extra or {})`.
   - `backend/apps/common/api.py`: cập nhật `exception_handler` để merge `exc.extra` vào response payload; `detail` và `code` luôn thắng các khoá trùng trong `extra`.
   - Test: `backend/apps/common/tests/test_business_error_extra.py` (2 tests passed 100%).
2. **App `apps/content`**:
   - Khởi tạo app `content`: `apps.py`, `__init__.py`, `admin.py`, `README.md`.
   - Cấu hình `backend/config/settings.py`: thêm `"apps.content"` vào `INSTALLED_APPS` và khối hằng số `CONTENT_*` (`CONTENT_TITLE_MAX`, `CONTENT_DESCRIPTION_MAX`, `CONTENT_MAX_IMAGES_PER_ENTRY`, `CONTENT_LIST_PAGE_SIZE`, `CONTENT_PUBLIC_CACHE_SECONDS`, `CONTENT_COST_KEYWORDS`, `CONTENT_PHONE_ALLOWLIST`, `CONTENT_IMAGE_WIDTHS`, `CONTENT_MAX_BLOCKS`, `CONTENT_BODY_MAX_CHARS`, `CONTENT_MAX_IMAGE_UPLOADS_PER_ENTRY`).
   - Cập nhật `backend/.env.example` và `backend/README.md`.
   - Models (`backend/apps/content/models/`):
     - `Category`: `name`, `name_key` (unique, normalized bỏ dấu/chữ thường), `slug` (unique), `description`, `order`, `is_active`, `created_at`, `updated_at`. `default_permissions = ("view", "add", "change")` (không `delete` -> 405 khi gọi DELETE).
     - `Entry`: mô hình lưu bản đang soạn (hỗ trợ FK cho category, published_version, cover_image, page_role constraints).
     - `EntryVersion`: bản chụp append-only, chặn `save`/`delete`/`update` khi đã tạo (CMS-10-AC5).
     - `ContentImage`: lưu ảnh bài viết.
   - Migrations:
     - `0001_initial.py`: tạo bảng dữ liệu và quan hệ FK.
     - `0002_grant_content_perms.py`: data migration cấp 8 quyền `content.*` cho Group `chu` và `quan_ly`; revoke khi rollback.
     - Đã kiểm tra `migrate content zero` và `migrate` lại sạch sẽ trên SQLite dev.
   - Quyền (`backend/apps/content/permissions.py`):
     - `ContentPermissions`: T1 model permissions cho CRUD; T2 kiểm tra `required_perms` trên `@action` (fail-closed nếu thiếu khai báo).
   - Module Chuyên mục (`backend/apps/content/categories/`):
     - `services.py`: `create_category` (tên duy nhất bỏ dấu `BR-ND-04`, slug tự sinh), `update_category` (đổi tên giữ nguyên slug CMS-02-AC3, ngừng dùng chặn khi còn bài `status=published` `BR-ND-02` kèm `entries` $\le 5$ và `total` CMS-02-AC4).
     - `serializers.py`: `CategorySerializer` với `published_count`.
     - `api.py`: `CategoryViewSet` hỗ trợ GET, POST, PATCH; chặn PUT và DELETE -> 405 MethodNotAllowed.
   - Module Bài viết (`backend/apps/content/entries/`):
     - `serializers.py`: `EntryListSerializer`.
     - `api.py`: `EntryViewSet` danh sách bài viết (phân trang `StandardPagination`) + custom action `@action(detail=False, methods=["get"], required_perms=("content.view_entry",)) def counts`.
   - Routing:
     - `backend/config/api_urls.py`: đăng ký `content/categories` và `content/entries` vào router.
3. **Frontend ERP Console**:
   - `erp-console/shared/lib/nav.ts`:
     - Thêm `content` và `content-categories` vào `ViewKey`.
     - Thêm các quyền `viewContentEntry`, `publishContentEntry`, `addCategory`, `changeCategory` vào `PERM`.
     - Thêm mục "Nội dung" (`/content/`) và menu con "Chuyên mục" (`/content/categories/`) vào `NAV` (chỉ hiện khi có `content.view_entry`).
   - `erp-console/features/content/`:
     - `types.ts`: định nghĩa các interface `ContentCategory`, `ContentEntryListItem`, `ContentCounts`, v.v.
     - `mock.ts`: mock dữ liệu theo đúng JSON contract §8 `02b-tech-design`.
     - `api.ts`: API client cho categories và entries (kèm mock fallback khi `USE_MOCK=1`).
     - `content.module.css`: style cho màn hình CMS.
     - `components/ContentListScreen.tsx`: màn hình danh sách bài viết với bộ lọc trạng thái (Nháp, Chờ duyệt, Đã đăng, Đã gỡ) kèm badge đếm số lượng, và bộ lọc loại (Bài viết, Trang).
     - `components/CategoriesScreen.tsx`: quản lý chuyên mục (thêm, sửa đổi tên giữ slug, ngừng dùng kèm popup cảnh báo `BR-ND-02` liệt kê bài viết nếu còn bài published).
   - Routes:
     - `erp-console/app/(console)/content/page.tsx`: bọc bởi `<ViewGuard view="content">`.
     - `erp-console/app/(console)/content/categories/page.tsx`: bọc bởi `<ViewGuard view="content-categories">`.
   - Tests:
     - `erp-console/features/content/content.test.ts`: 4 vitest tests passed 100%.

### Sửa test cũ do thêm quyền/app mới
Theo quy tắc tại `02c-giao-viec.md` (§27):
1. `backend/apps/accounts/auth/services.py`:
   - Thêm nhãn `"content.publish_entry": "Đăng bài viết và trang"` vào `CAPABILITY_LABELS` (do `Entry` khai báo custom permission `publish_entry` trong `Meta.permissions`).
2. `backend/apps/accounts/auth/tests/test_s47_me_labels.py`:
   - Thêm `"content.publish_entry"` vào danh sách capability mong đợi của Quản lý trong `test_s47_ac1_quan_ly_nhan_nhom_va_viec_theo_spec_1_5` (do migration `0002_grant_content_perms.py` cấp quyền này cho Group `quan_ly` theo CMS-01-AC1).
3. `backend/apps/ai/registry/tests/snapshots/commands_index_snapshot.json`:
   - Cập nhật thêm 5 command ID mới của app `content` (`content.category.create`, `content.category.list`, `content.category.partial_update`, `content.entry.counts`, `content.entry.list`) do cơ chế tự động khám phá lệnh AI từ router DRF (DW-07, CMS-01-Q10).

### Kết quả kiểm chứng Lô 1
```bash
# 1. Backend tests và makemigrations check:
cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
# Output: Ran 920 tests in 83.7s -> OK. No changes detected.

# 2. Content tests:
cd backend && .venv/bin/python manage.py test apps.content
# Output: Ran 11 tests in 0.45s -> OK.

# 3. ERP Console tests & build:
cd erp-console && npm test -- --run
# Output: 6 test files passed, 46 tests passed (100%).
cd erp-console && npx tsc --noEmit && npm run build
# Output: Compiled successfully, Generating static pages (29/29) -> OK.

# 4. Frontend tests & build:
cd frontend && npx tsc --noEmit && npm run build
# Output: Compiled successfully, Generating static pages (8/8) -> OK.

# 5. Kiểm tra migration app khác:
git status --porcelain -- backend/apps | grep "/migrations/" | grep -v "apps/content/migrations/"
# Output: rỗng (không có migration app khác).
```

### Lệch thiết kế
*(Không có)*

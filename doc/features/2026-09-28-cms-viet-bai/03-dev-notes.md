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

---

## Lô 2: CMS-03 Soạn và lưu nháp bài/trang & CMS-05 Ảnh trong bài và ảnh bìa giữ tỉ lệ

### Kế hoạch & Thực hiện
1. **Backend**:
   - `backend/apps/catalog/images/processing.py`:
     - Thêm dataclass `ProcessedRatioImage` và hàm `process_image_keep_ratio` (giữ tỉ lệ 4:3, sai số $\le 1$px, loại bỏ EXIF/GPS, xuất 3 cỡ WebP sm/md/lg).
     - Không sửa đổi bất kỳ hàm cũ nào trong `catalog/images/`.
   - `backend/apps/content/body/slug.py`:
     - `slugify_vi`: chuẩn hoá chữ thường, bỏ dấu, gạch nối, chống gạch nối đôi hoặc ở đầu/cuối.
     - `suggest_unique_slug`: gợi ý `<base>-<n nhỏ nhất >= 2 còn trống>`.
   - `backend/apps/content/body/sanitize.py`:
     - `normalize_body`: chuẩn hoá danh sách trắng 15 payload XSS (§6.3 `02b-tech-design`), idempotent (`normalize(normalize(x)) == normalize(x)`), giữ chữ `<` dạng text, giới hạn ký tự và khối.
   - `backend/apps/content/images/`:
     - `services.py`: `upload_content_image` (kiểm tra định dạng JPEG/PNG/WebP, dung lượng $\le 10$MB `BR-DM-10`, trần 20 ảnh `BR-ND-07`, trần 100 uploads trong đời bài, loại bỏ EXIF), `update_image_alt` (tối đa 200 ký tự).
     - `serializers.py`: `ContentImageSerializer` xuất các URL sm/md/lg.
     - `api.py`: `EntryImageUploadView` (POST tải ảnh lên bài viết), `ContentImageViewSet` (PATCH sửa alt ảnh).
   - `backend/apps/content/entries/`:
     - `services.py`: `save_draft` (chặn 409 `STALE_VERSION` khi `row_version` lệch, tính `draft_hash`, kiểm tra slug trùng `BR-ND-04`), `delete_draft` (chỉ cho phép xoá nháp chưa từng đăng `published_version is None and first_published_at is None`, nếu đã đăng chặn 400 `BR-ND-02`).
     - `serializers.py`: `EntryDetailSerializer` (đầy đủ các trường chi tiết theo §8.3).
     - `api.py`: `EntryViewSet` hỗ trợ CRUD nháp bài viết / trang.
   - `backend/apps/content/permissions.py`:
     - Bổ sung hỗ trợ APIView có thuộc tính `required_perms`.
   - `backend/config/api_urls.py`:
     - Đăng ký router `content/images` và route `content/entries/<int:pk>/images/`.
   - `backend/apps/ai/registry/tests/snapshots/commands_index_snapshot.json`:
     - Cập nhật thêm 3 lệnh mới tự sinh từ router DRF: `content.entry.create`, `content.entry.partial_update`, `content.entry.retrieve`.
   - Tests backend:
     - `apps.content.body.tests` (8 tests), `apps.content.images.tests` (5 tests), `apps.content.entries.tests.test_draft` (11 tests), `apps.catalog.images` (47 tests).
     - Toàn bộ backend test suite: 933 tests passed 100%.

2. **Frontend ERP Console**:
   - Cài đặt thư viện Tiptap 2.x: `@tiptap/react`, `@tiptap/pm`, `@tiptap/starter-kit`, `@tiptap/extension-link`.
   - `erp-console/shared/lib/http.ts`:
     - Thêm hàm `apiUpload` hỗ trợ upload multipart/form-data với XMLHttpRequest `onprogress` để theo dõi tiến trình upload (CMS-05-AC8), hỗ trợ token và mock mode.
   - `erp-console/features/content/types.ts`:
     - Bổ sung đầy đủ types: `ContentImage`, `BodyDoc`, `Block`, `InlineNode`, `ContentEntryDetail`, `EntryCreatePayload`, `EntryUpdatePayload`.
   - `erp-console/features/content/mock.ts`:
     - Bổ sung mock cho `getEntry`, `createEntry`, `updateEntry` (STALE_VERSION 409), `deleteEntry` (BR-ND-02), `uploadEntryImage` (BR-ND-07 trần 20 ảnh), `updateImageAlt`.
   - `erp-console/features/content/api.ts`:
     - Bổ sung API client methods cho entry và image upload.
   - `erp-console/features/content/editor/`:
     - `convert.ts`: `tiptapToBody`, `bodyToTiptap`, `safeHref` loại bỏ toàn bộ HTML lạ/XSS.
     - `CaveImageExtension.ts`: custom Tiptap node extension cho khối ảnh Cá Về.
     - `TiptapEditor.tsx` & `TiptapEditor.module.css`: editor tải lười, thanh công cụ touch target $\ge 44\times 44$px, drop script/iframe khi paste HTML.
     - `ImageUploader.tsx` & `ImageUploader.module.css`: tải ảnh từ camera/thư viện (CMS-05-AC8), thanh tiến trình, hiển thị danh sách ảnh, chèn vào bài, đặt làm ảnh bìa, sửa alt, xử lý lỗi mất mạng (CMS-05-AC6).
   - `erp-console/app/(console)/content/edit/page.tsx` & `edit.module.css`:
     - Màn hình soạn thảo bài/trang bọc bởi `ViewGuard` và `Suspense`.
     - Xử lý xung đột 409 `STALE_VERSION`: hiện cảnh báo và nút tải bản mới, **không xoá** nội dung đang gõ (CMS-03-AC7).
     - Xoá nháp: chỉ hiện nút xoá khi bài chưa từng đăng (CMS-03-AC8, CMS-03-AC9).
     - Responsive mobile: 375x667 không cuộn ngang, touch target $\ge 44\times 44$px (CMS-03-AC13).
   - `erp-console/features/content/components/ContentListScreen.tsx`:
     - Thêm nút "Viết bài mới", "Tạo trang", link dòng bảng sang `/content/edit/?id=...`.
   - Tests:
     - `convert.test.ts` (5 tests), `content.test.ts` (10 tests) -> 57 vitest tests passed 100%.

### Kết quả kiểm chứng Lô 2
```bash
# 1. Backend tests và makemigrations check:
cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
# Output: Ran 933 tests in 78.8s -> OK. No changes detected.

# 2. Content tests:
cd backend && .venv/bin/python manage.py test apps.content
# Output: Ran 24 tests in 1.48s -> OK.

# 3. ERP Console tests & build:
cd erp-console && npm test
# Output: 7 test files passed, 57 tests passed (100%).
cd erp-console && npx tsc --noEmit && npm run build
# Output: Compiled successfully, Generating static pages (30/30) -> OK.

# 4. Kiểm tra dangerouslySetInnerHTML:
grep -rn "dangerouslySetInnerHTML" frontend/features/content frontend/app/bai-viet frontend/app/trang erp-console/features/content erp-console/app/\(console\)/content
# Output: rỗng (không sử dụng dangerouslySetInnerHTML).

# 5. Kiểm tra migration app khác:
git status --porcelain -- backend/apps | grep "/migrations/" | grep -v "apps/content/migrations/"
# Output: rỗng.
```

### Lệch thiết kế
*(Không có)*

---

## Lô 3: CMS-07 Đăng bài viết / trang, CMS-08 Cảnh báo SĐT / giá vốn / mặt hàng hết, CMS-13 Bài viết Shop công khai

### Kế hoạch & Thực hiện
1. **Backend**:
   - `backend/apps/common/throttling.py`: Thêm `PublicContentThrottle` với scope `public_content` (60 req/phút).
   - `backend/config/settings.py`: Thêm `"public_content": "60/minute"` vào `_DEFAULT_THROTTLE_RATES`.
   - `backend/apps/content/models/entries.py`: Thêm `@property def slug_locked(self) -> bool` dựa trên `first_published_at is not None`.
   - `backend/apps/content/body/scan.py`: Máy quét an toàn nội dung `scan_entry_warnings` phát hiện SĐT (10-11 chữ số, che dạng `09xx xxx 678` trong snippet, bỏ qua `CONTENT_PHONE_ALLOWLIST` và các ca không báo nhầm CMS-08-AC3), phát hiện từ khoá giá vốn không phân biệt hoa thường/dấu, phát hiện thẻ mặt hàng không khả dụng.
   - `backend/apps/content/entries/services.py`:
     - `missing_fields`: kiểm tra thiếu tiêu đề, body, cover_image (bài viết bắt buộc có alt), category, excerpt.
     - `compute_description`: tự tính SEO description từ excerpt <= 160 ký tự tại từ cuối, bỏ dấu câu treo.
     - `publish_entry`: kiểm tra `row_version` (409 STALE_VERSION), kiểm tra không thay đổi (BR-ND-05), kiểm tra missing fields (400 BR-ND-03), kiểm tra checklist_confirmed (400 BR-ND-13), cảnh báo CONTENT_WARNINGS (409), tạo `EntryVersion` append-only, cập nhật status=published, first_published_at, last_published_at, row_version + 1, ghi AuditLog 1 dòng `content_publish` hoặc `content_republish` chỉ chứa `entry_id, version, kind` + `warnings_acknowledged`.
   - `backend/apps/content/entries/api.py`: Thêm action `publish` trên `EntryViewSet` với `@action(detail=True, methods=["post"], required_perms=("content.publish_entry",))`.
   - `backend/apps/content/public/`:
     - `serializers.py`: `public_body` (Lớp 1b chuẩn hoá bỏ image_id, tính URLs sm/md/lg qua storage), `PublicEntryDetailSerializer`, `PublicEntryListSerializer`, `PublicCategorySerializer`. Không dùng ModelSerializer, dict dựng tường minh, không chứa khoá cấm.
     - `api.py`: `PublicEntryListView` (12 bài/trang, Cache-Control public max-age <= 60), `PublicEntryDetailView` (404 NOT_FOUND giống hệt cho nháp và không tồn tại, 410 GONE cho unpublished), `PublicCategoryListView`, `PublicPageByRoleView`, `PublicFooterLinksView`. Tất cả AllowAny, chỉ GET/HEAD/OPTIONS.
   - `backend/config/api_urls.py`: Đăng ký router `public/content/entries`, `public/content/categories`, `public/content/pages/by-role/<role>/`, `public/content/footer-links/`.
   - `backend/apps/ai/registry/tests/snapshots/commands_index_snapshot.json`: Thêm `content.entry.publish` theo thứ tự alphabet.

2. **ERP Console**:
   - `erp-console/features/content/types.ts`: Thêm `ContentWarning`, `EntryPublishPayload`, `EntryPublishResponse`.
   - `erp-console/features/content/api.ts` & `mock.ts`: Thêm `publishEntry` và mock tương ứng (kiểm tra checklist, cảnh báo CONTENT_WARNINGS, STALE_VERSION, BR-ND-03).
   - `erp-console/app/(console)/content/edit/page.tsx` & `edit.module.css`:
     - Thêm nút "Đăng bài" bên cạnh "Lưu nháp".
     - Modal Checklist 5 mục tự kiểm (BR-ND-13): Đã đọc lại bài, Không chứa giá vốn nội bộ, Không lộ SĐT cá nhân, Ảnh rõ nét có alt, Thẻ món sẵn hàng.
     - Modal Cảnh báo (409 CONTENT_WARNINGS): Liệt kê các cảnh báo và nút "Tôi đã kiểm tra, vẫn đăng" (`acknowledge_warnings: true`).

3. **Frontend Shop Web**:
   - `frontend/lib/api.ts`: Thêm `export` cho `apiFetch`, an toàn parse lỗi 404 và 410.
   - `frontend/features/content/types.ts`: Khai báo types công khai không chứa ID nội bộ.
   - `frontend/features/content/safeHref.ts`: Hàm kiểm tra link an toàn chống XSS.
   - `frontend/features/content/mock.ts`: Mock dữ liệu cho Shop web.
   - `frontend/features/content/api.ts`: Gọi `/api/public/content/entries/`, `/api/public/content/categories/`.
   - `frontend/features/content/components/ArticleBody.tsx`: Render an toàn toàn bộ BodyDoc thuần JSX (heading, paragraph, quote, list, image lazy, item_card), không dùng `dangerouslySetInnerHTML`.
   - `frontend/app/bai-viet/page.tsx` & `bai-viet.module.css`: Trang bài viết tĩnh bọc trong `<Suspense>`, xử lý chi tiết bài viết, danh sách bài viết, 404, 410 ("Bài này không còn trên web"), lỗi kết nối mạng.

### Kết quả kiểm chứng Lô 3
```bash
# 1. Backend tests và makemigrations check:
cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
# Output: Ran 955 tests in 90.4s -> OK. No changes detected.

# 2. Content tests:
cd backend && .venv/bin/python manage.py test apps.content
# Output: Ran 38 tests in 2.1s -> OK.

# 3. ERP Console tests & build:
cd erp-console && npm test
# Output: 7 test files passed, 58 tests passed (100%).
cd erp-console && npx tsc --noEmit && npm run build
# Output: Compiled successfully, Generating static pages (30/30) -> OK.

# 4. Frontend Shop Web typecheck & build:
cd frontend && npx tsc --noEmit && NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-staging-675411800433.asia-southeast1.run.app npm run build
# Output: Compiled successfully, Generating static pages (9/9) -> OK.

# 5. Kiểm tra dangerouslySetInnerHTML:
grep -rn "dangerouslySetInnerHTML" frontend/features/content frontend/app/bai-viet erp-console/features/content
# Output: rỗng (0 vi phạm).

# 6. Kiểm tra migration app khác:
git status --porcelain -- backend/apps | grep "/migrations/" | grep -v "apps/content/migrations/"
# Output: rỗng.
```

### Lệch thiết kế
*(Không có)*

---

## Lô 4: CMS-12 Gỡ bài viết / trang & CMS-10 Sửa nháp bài đang đăng & huỷ thay đổi

### Những gì đã làm
1. **Backend**:
   - `backend/apps/content/entries/services.py`:
     - `UNPUBLISH_REASONS = {"wrong_price", "complaint", "out_of_season", "wrong_content", "other"}`.
     - Hiện thực `unpublish_entry`: kiểm tra `row_version` (409 STALE_VERSION), kiểm tra `status == "published"` (400 BR-ND-01), kiểm tra `reason` hợp lệ (400 BR-ND-15), chặn gỡ trang go-live có `page_role` (400 BR-ND-16), cập nhật `status = "unpublished"`, `return_reason = clean_reason`, ghi AuditLog 1 dòng `content_unpublish` (`entry_id, version, reason`), không ghi tiêu đề/chữ bài.
     - Hiện thực `discard_changes`: nạp lại nội dung từ `published_version`, `draft_hash = published_version.content_hash`, `row_version += 1`, không ghi AuditLog, trả về instance `entry`.
   - `backend/apps/content/entries/api.py`:
     - Thêm action `@action(detail=True, methods=["post"], required_perms=("content.publish_entry",)) def unpublish`.
     - Thêm action `@action(detail=True, methods=["post"], url_path="discard-changes", required_perms=("content.change_entry",)) def discard_changes` trả về `Response(EntryDetailSerializer(entry, ...).data)`.
     - Cập nhật `custom_perm_actions = ("counts", "publish", "unpublish", "discard_changes")`.
   - `backend/apps/content/public/api.py`:
     - Gán header `Cache-Control: public, max-age=60` khi trả về mã 410 GONE (CMS-12-AC3).
   - `backend/apps/ai/registry/tests/snapshots/commands_index_snapshot.json`:
     - Đã thêm `content.entry.discard_changes` và `content.entry.unpublish` theo alphabet.
   - `backend/apps/content/tests/test_unpublish_discard.py`:
     - 13 test cases bao quát đầy đủ CMS-12 (AC1..AC7) và CMS-10 (AC1..AC6), append-only test cho `EntryVersion`, phân quyền 3 vai trò và `Cache-Control`.

2. **Frontend ERP Console**:
   - `erp-console/features/content/types.ts`:
     - Thêm `UnpublishReason`, `EntryUnpublishPayload`, `EntryDiscardPayload`.
   - `erp-console/features/content/api.ts` & `mock.ts`:
     - Thêm `unpublishEntry` và `discardChanges` gọi đúng `/discard-changes/`.
     - Mock hỗ trợ lưu `_published_snapshot`, khôi phục bản nháp và gỡ bài.
   - `erp-console/features/content/components/ContentListScreen.tsx`:
     - Hiển thị badge vàng "Có thay đổi chưa đăng" khi `item.has_unpublished_changes` (CMS-10-AC6).
   - `erp-console/app/(console)/content/edit/page.tsx` & `edit.module.css`:
     - Thêm nút "Gỡ bài" khi bài đang `published`: modal chọn lý do gỡ bài (`wrong_price`, `complaint`, `out_of_season`, `wrong_content`, `other`). Chặn gỡ trang go-live kèm thông báo thân thiện.
     - Khi `has_unpublished_changes = true`: hiển thị banner cảnh báo và nút "Huỷ thay đổi" (gọi `discardChanges`), nạp lại toàn bộ dữ liệu vào form mượt mà.
   - `erp-console/features/content/content.test.ts`:
     - Bổ sung đầy đủ unit tests cho CMS-12 và CMS-10.

### Kết quả kiểm chứng Lô 4
```bash
# 1. Content tests:
cd backend && .venv/bin/python manage.py test apps.content
# Output: Ran 60 tests in 3.127s -> OK.

# 2. Makemigrations check:
cd backend && .venv/bin/python manage.py makemigrations --check --dry-run
# Output: No changes detected.

# 3. ERP Console tests & build:
cd erp-console && npm test
# Output: 7 test files passed, 60 tests passed (100%).
cd erp-console && npx tsc --noEmit && npm run build
# Output: Compiled successfully, Generating static pages (30/30) -> OK.

# 4. Frontend Shop Web typecheck & build:
cd frontend && npx tsc --noEmit && npm run build
# Output: Compiled successfully, Generating static pages (9/9) -> OK.

# 5. Kiểm tra dangerouslySetInnerHTML:
grep -rn "dangerouslySetInnerHTML" frontend/features/content frontend/app/bai-viet erp-console/features/content
# Output: rỗng (0 vi phạm).
```

### Lệch thiết kế
*(Không có)*

---

## Lô 5: CMS-15 Trang nội dung và phiên bản có hiệu lực

### Những gì đã làm
1. **Backend**:
   - `backend/apps/content/entries/services.py`:
     - Khai báo `GOLIVE_PAGE_ROLES = ("privacy", "terms", "refund", "seller_info")`.
     - Trong `save_draft`:
       - Kiểm tra `page_role` hợp lệ thuộc `GOLIVE_PAGE_ROLES` (400 `BR-ND-16`).
       - Kiểm tra không đặt trùng `page_role` với trang khác (400 `BR-ND-16`, CMS-15-AC2).
       - TD-3: Nếu bài `status == "published"` và `page_role` có giá trị, cấm bỏ hoặc đổi `page_role` (400 `BR-ND-16`).
       - CMS-15-AC8: Nếu request có `page_role`, `show_in_footer`, `footer_order` mà user thiếu quyền `content.publish_entry` -> từ chối 403 `BR-PQ-12` trước khi lưu, không field nào của request được cập nhật.
     - Trong `unpublish_entry`: kiểm tra `entry.page_role is not None` trước khi kiểm tra lý do gỡ -> 400 `BR-ND-16` "Trang bắt buộc go-live chỉ sửa và đăng lại (BR-ND-16)." (CMS-15-AC3).
     - Thêm hàm `effective_version(role: str, at: Any = None) -> EntryVersion | None` (CMS-15-AC4).
     - Thêm hàm `current_policy_version(role: str) -> EntryVersion | None` (GL-03).
     - Thêm hàm `golive_missing_roles() -> list[str]` (CMS-15-AC7).
   - `backend/apps/content/entries/api.py`:
     - Thêm `GoliveStatusView(APIView)`: `permission_classes = [ContentPermissions]`, `required_perms = ("content.view_entry",)`, `parser_classes = []` (tránh tự sinh nhầm thành lệnh AI ghi), GET gọi `golive_missing_roles()` trả `{"missing_roles": [...]}` (CMS-15-AC7, AC9).
   - `backend/config/api_urls.py`:
     - Đăng ký `path("content/golive-status/", GoliveStatusView.as_view(), name="content-golive-status")`.
   - `backend/apps/content/public/api.py`:
     - `PublicPageByRoleView`: trả đúng 5 khoá contract (`slug`, `title`, `version`, `version_id`, `effective_from`), `effective_from` dùng `timezone.localtime(version.published_at).isoformat()`, gán `Cache-Control: public, max-age=60`. Không rò rỉ bất kỳ khoá cấm nào (Bất biến 1, 9).
     - `PublicFooterLinksView`: chỉ lọc trang `status == "published"` có `show_in_footer=True`, sắp xếp theo `footer_order`, chỉ trả `title` và `slug`, gán `Cache-Control: public, max-age=60`.
   - `backend/apps/content/tests/test_pages_policy.py`:
     - 10 test cases tự động bao quát toàn bộ CMS-15 (AC1..AC9) và TD-3, quét khoá cấm qua `assert_no_forbidden_keys`.

2. **Frontend ERP Console**:
   - `erp-console/features/content/types.ts`:
     - Thêm `GoliveStatusResponse`, `FooterLink`, `PageByRoleResponse`.
   - `erp-console/features/content/api.ts` & `mock.ts`:
     - Thêm `fetchGoliveStatus()` và `mockGetGoliveStatus()`.
   - `erp-console/features/content/components/ContentListScreen.tsx`:
     - Gọi `fetchGoliveStatus()`, hiển thị Banner màu vàng cảnh báo "Thiếu trang bắt buộc go-live: ..." khi `missingRoles.length > 0` (CMS-15-AC7).
   - `erp-console/app/(console)/content/edit/page.tsx`:
     - Form cho `kind === "page"`: cấu hình `page_role` (dropdown), `show_in_footer` (checkbox), `footer_order` (input number).
     - Khoá dropdown đổi vai trò khi `status === "published" && pageRole` (TD-3).
     - Ẩn nút "Gỡ bài" khi `status === "published" && pageRole` (CMS-15-AC3).
   - `erp-console/features/content/content.test.ts`:
     - Bổ sung unit test cho `mockGetGoliveStatus` (CMS-15-AC7).

3. **Frontend Shop Web**:
   - `frontend/features/content/types.ts`:
     - Thêm `FooterLink`, `PageByRoleResponse`.
   - `frontend/features/content/api.ts` & `mock.ts`:
     - Thêm `fetchPageByRole(role)` và `fetchFooterLinks()`.
   - `frontend/app/trang/page.tsx` & `trang.module.css`:
     - Trang tĩnh `/trang/?slug=...` bọc trong `<Suspense>`.
     - Hiển thị "Có hiệu lực từ dd/mm/yyyy" (CMS-15-AC1).
     - Render thân bài bằng `ArticleBody` an toàn, không sử dụng `dangerouslySetInnerHTML`.
     - Xử lý đầy đủ 404, 410 ("Trang này không còn trên web"), lỗi kết nối mạng.

### Kết quả kiểm chứng Lô 5
```bash
# 1. Content tests (bao gồm test_pages_policy.py):
cd backend && .venv/bin/python manage.py test apps.content
# Output: Ran 70 tests in 3.730s -> OK.

# 2. Toàn bộ backend tests và makemigrations check:
cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
# Output: Ran 979 tests in 75.285s -> OK. No changes detected.

# 3. ERP Console tests & build:
cd erp-console && npm test
# Output: 7 test files passed, 61 tests passed (100%).
cd erp-console && npx tsc --noEmit && npm run build
# Output: Compiled successfully, Generating static pages (30/30) -> OK.

# 4. Frontend Shop Web typecheck & build:
cd frontend && npx tsc --noEmit && NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-staging-675411800433.asia-southeast1.run.app npm run build
# Output: Compiled successfully, Generating static pages (10/10) -> OK.

# 5. Kiểm tra dangerouslySetInnerHTML:
grep -rn "dangerouslySetInnerHTML" frontend/features/content frontend/app/bai-viet frontend/app/trang erp-console/features/content
# Output: rỗng (0 vi phạm).

# 6. Kiểm tra migration app khác:
git status --porcelain -- backend/apps | grep "/migrations/" | grep -v "apps/content/migrations/"
# Output: rỗng.
```

### Lệch thiết kế
*(Không có)*

---

## Lô 6: CMS-06 Thẻ mặt hàng & CMS-14 Danh sách công khai / khối Bài mới

### Kế hoạch & Thực hiện
1. **Backend**:
   - `backend/apps/content/body/sanitize.py`:
     - Kiểm tra khối `item_card`: khi `strict=True`, kiểm tra `Item.objects.filter(code=item_code).exists()`. Nếu không tồn tại -> raise `BusinessError("Mặt hàng không tồn tại (BR-ND-10).", code="BR-ND-10")` (CMS-06-AC2).
     - Khi `strict=False` (lúc `public_body`): không tra DB, chỉ kiểm dạng regex `ITEM_CODE_RE`.
   - `backend/apps/content/body/scan.py`:
     - Cải tiến quét `item_unavailable`: kiểm tra `is_active=True` và `effective_price(item) is not None` từ `apps.catalog.pricing.services`. Nếu không khả dụng -> cảnh báo `{"type": "item_unavailable", "item_code": code}` (CMS-06-AC6).
   - `backend/apps/content/public/api.py`:
     - `PublicEntryListView`: Lọc `status="published"`, `kind="post"` (loại trừ nháp và trang tĩnh). Phân trang 12 bài/trang (`CONTENT_LIST_PAGE_SIZE = 12`). Hỗ trợ lọc theo `category`. Sắp xếp mới nhất trước. Trang vượt quá giới hạn -> trả 404 (CMS-14-AC6).
     - `PublicCategoryListView`: Chỉ trả các chuyên mục `is_active=True` có ít nhất 1 bài Đã đăng (`status="published"`, `kind="post"`).
   - `backend/apps/content/tests/test_item_card_and_public_list.py`:
     - Bổ sung 7 test case kiểm tra toàn diện CMS-06 và CMS-14 (AC1, AC2, AC5, AC6, AC7).

2. **ERP Console**:
   - `erp-console/features/content/editor/ItemCardExtension.ts`:
     - Extension Tiptap node `itemCard` cho phép chèn và hiển thị thẻ mặt hàng trên trình soạn thảo.
   - `erp-console/features/content/api.ts` & `mock.ts`:
     - Thêm `ShopCatalogItem` và `fetchShopCatalog()`, `mockFetchShopCatalog()` gọi catalog công khai không lộ giá vốn.
   - `erp-console/features/content/editor/TiptapEditor.tsx` & `TiptapEditor.module.css`:
     - Thêm nút "🛒 Mặt hàng" trên toolbar.
     - Modal tìm kiếm mặt hàng theo tên/mã (CMS-06-AC1: gõ "thu" -> ra mặt hàng khớp).
     - Thêm phương thức `insertItemCard` trên `TiptapEditorHandle`.
   - `erp-console/features/content/content.test.ts`:
     - Thêm unit test kiểm tra `mockFetchShopCatalog()` không rò rỉ giá vốn hay khoá cấm.

3. **Frontend Shop Web**:
   - `frontend/features/content/types.ts`:
     - Bổ sung `count`, `next`, `previous` cho `PublicEntryListResponse`.
   - `frontend/features/content/components/ItemCard.tsx` & `ItemCard.module.css`:
     - Nhận `itemCode` và `postSlug`.
     - Tải mặt hàng qua `getCatalogItem(itemCode)`.
     - Hiển thị giá bán hiện hành lấy lúc xem (CMS-06-AC3).
     - Nút "Xem giá & đặt" dẫn sang `/shop/item/?code=...&utm_source=caveve_web&utm_medium=bai_viet&utm_campaign=<slug>`, không tham số thừa (CMS-06-AC4).
     - Khi mặt hàng ẩn / hết hàng / lỗi API -> hiện "Tạm hết hàng", nút dẫn về `/shop` kèm UTM (CMS-06-AC5).
   - `frontend/features/content/components/ArticleBody.tsx`:
     - Render `<ItemCard>` khi gặp block `item_card`.
   - `frontend/features/content/components/LatestPosts.tsx` & `LatestPosts.module.css`:
     - Hiển thị khối "Cẩm nang & Mẹo hay từ vựa" gồm 3 bài mới nhất và link "Xem tất cả" (CMS-14-AC3).
     - Khi API lỗi hoặc tắt -> ẩn hoàn toàn khối này (CMS-14-AC4).
   - `frontend/app/page.tsx`:
     - Chèn khối `<LatestPosts />` vào trang chủ Landing.
   - `frontend/app/bai-viet/page.tsx` & `bai-viet.module.css`:
     - Hỗ trợ lọc theo `chuyen-muc` query param (CMS-14-AC2).
     - Bộ lọc tabs chuyên mục, khi không có bài hiện "Chưa có bài".
     - Khối phân trang 12 bài/trang (CMS-14-AC1).
     - Truyền `postSlug={entry.slug}` vào `ArticleBody`.

### Kết quả kiểm chứng Lô 6
```bash
# 1. Content tests (bao gồm test_item_card_and_public_list.py):
cd backend && .venv/bin/python manage.py test apps.content
# Output: Ran 78 tests in 3.938s -> OK.

# 2. Toàn bộ backend tests và makemigrations check:
cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
# Output: Ran 987 tests in 81.899s -> OK. No changes detected.

# 3. ERP Console tests & build:
cd erp-console && npm test
# Output: 7 test files passed, 62 tests passed (100%).
cd erp-console && npx tsc --noEmit && npm run build
# Output: Compiled successfully, Generating static pages (30/30) -> OK.

# 4. Frontend Shop Web typecheck & build với staging API env:
cd frontend && npx tsc --noEmit && NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-staging-675411800433.asia-southeast1.run.app npm run build
# Output: Compiled successfully, Generating static pages (10/10) -> OK.

# 5. Kiểm tra dangerouslySetInnerHTML:
grep -rn "dangerouslySetInnerHTML" frontend/features/content frontend/app/bai-viet frontend/app/trang erp-console/features/content
# Output: rỗng (0 vi phạm).

# 6. Kiểm tra migration app khác:
git status --porcelain -- backend/apps | grep "/migrations/" | grep -v "apps/content/migrations/"
# Output: rỗng.
```

### Lệch thiết kế
*(Không có)*

---

## Lô 7: Vòng đời duyệt, Lịch sử phiên bản & Tự lưu nháp

### Các Story hoàn thành
- **CMS-09**: Gửi duyệt và trả về bài viết / trang (`submit`, `return`, AuditLog `content_submit`, `content_return`, phân quyền ND-01 vs ND-02).
- **CMS-11**: Lịch sử phiên bản & Khôi phục (`versions/`, `restore/`, AuditLog `content_restore_version`, danh sách ẩn `body`, khôi phục bản cũ thành bản nháp đang soạn).
- **CMS-04**: Tự lưu nháp cục bộ dùng `shared/lib/drafts.ts` khi rớt mạng / offline (chu kỳ 10s idle, cảnh báo offline, khôi phục khi mở lại).

### Kế hoạch & Thực hiện
1. **Backend**:
   - `backend/apps/content/entries/services.py`:
     - `submit_entry`: kiểm tra `status == "draft"`, kiểm tra `can_publish_check`, quét cảnh báo SĐT/giá vốn (`acknowledge_warnings=False` -> raise `CONTENT_WARNINGS`), chuyển `status = "pending_review"`, tăng `row_version`, ghi AuditLog `content_submit` với actor và version (CMS-09-AC2).
     - `return_entry`: chỉ cho phép khi `status == "pending_review"`, kiểm tra `reason` thuộc `RETURN_REASONS = {"missing_info", "wrong_content", "legal_risk", "other"}` (sai -> 400 `BR-ND-15`), chuyển `status = "draft"`, lưu `return_reason`, tăng `row_version`, ghi AuditLog `content_return` (CMS-09-AC5).
     - `restore_entry_version`: nạp bản ghi `EntryVersion(version=version_no)`, sao chép các trường nội dung (`title`, `slug`, `excerpt`, `seo_title`, `seo_description`, `category`, `cover_image`, `body`) vào bài viết đang soạn, đặt `restored_from = version_no`, `has_unpublished_changes = True`, tăng `row_version`, ghi AuditLog `content_restore_version` khi xuất bản (CMS-11-AC2, AC3).
   - `backend/apps/content/entries/serializers.py`:
     - `EntryVersionListSerializer`: chỉ gồm `version`, `published_at`, `published_by_name`, `title`, `restored_from`. Tuyệt đối không chứa trường `body` (CMS-11-AC1).
     - `EntryVersionDetailSerializer`: gồm đầy đủ trường để xem chi tiết hoặc khôi phục.
     - `EntryReturnSerializer`: xác thực `reason` thuộc `RETURN_REASONS`.
     - `EntrySubmitSerializer`: xác thực `row_version`, `acknowledge_warnings`.
   - `backend/apps/content/entries/api.py`:
     - Khai báo 5 action: `submit`, `return_action`, `versions`, `version_detail`, `restore_version` trên `EntryViewSet`.
     - Gắn quyền Tầng 2 thông qua `custom_perm_actions`:
       - `submit`: `content.change_entry`
       - `return_action`: `content.publish_entry`
       - `versions`, `version_detail`: `content.view_entry`
       - `restore_version`: `content.change_entry`
   - `backend/apps/content/tests/test_lifecycle_and_versions.py`:
     - 10 test case toàn diện kiểm thử vòng đời duyệt, phân quyền, cảnh báo, lịch sử phiên bản và khôi phục.

2. **ERP Console**:
   - `erp-console/features/content/types.ts`:
     - Thêm `ReturnReason`, `EntrySubmitPayload`, `EntrySubmitResponse`, `EntryReturnPayload`, `EntryReturnResponse`, `EntryRestorePayload`, `ContentEntryVersionListItem`, `ContentEntryVersionDetail`.
   - `erp-console/features/content/mock.ts`:
     - Bổ sung `mockSubmitEntry`, `mockReturnEntry`, `mockFetchEntryVersions`, `mockGetEntryVersion`, `mockRestoreEntryVersion`, quản lý `MOCK_VERSIONS_DB`.
   - `erp-console/features/content/api.ts`:
     - Xuất các hàm API tương ứng: `submitEntry`, `returnEntry`, `fetchEntryVersions`, `getEntryVersion`, `restoreEntryVersion`.
   - `erp-console/app/(console)/content/edit/edit.module.css`:
     - Bổ sung CSS cho `.submitBtn`, `.returnBtn`, `.historyBtn`, `.saveStatusText`, `.bannerPending`, `.versionList`, `.restoreActionBtn`.
   - `erp-console/app/(console)/content/edit/page.tsx`:
     - TopBar:
       - User chỉ có ND-01 không có quyền đăng -> nút "Gửi duyệt" (`submitEntry`).
       - Quản lý / Chủ có quyền đăng -> nút "Đăng bài" và nút "Trả về nháp" (`returnEntry`) khi bài đang ở trạng thái `pending_review`.
       - Nút "📜 Lịch sử" mở modal danh sách phiên bản (`showHistoryModal`).
       - Nhãn trạng thái tự lưu `saveStatus` hiển thị trực quan (Đã lưu / Đang tự lưu / Chưa lưu, đang giữ trên máy).
     - Banner "⏳ Đang chờ duyệt" hiển thị khi `status === "pending_review"` kèm lý do trả về trước đó nếu có.
     - Modal Trả về nháp (`showReturnModal`) cho phép chọn lý do chuẩn `RETURN_REASON_OPTIONS`.
     - Modal Lịch sử phiên bản (`showHistoryModal`) hiển thị danh sách các phiên bản đã xuất bản và nút "Khôi phục phiên bản này".
     - Hook tự lưu nháp sau 10s idle và lưu cục bộ qua `shared/lib/drafts.ts` khi rớt mạng / offline.
   - `erp-console/features/content/content.test.ts`:
     - Bổ sung 3 test case kiểm thử toàn diện submit, return, fetch versions, restore version và drafts localStorage.

### Kết quả kiểm chứng Lô 7
```bash
# 1. Content tests (bao gồm test_lifecycle_and_versions.py):
cd backend && .venv/bin/python manage.py test apps.content
# Output: Ran 88 tests in 3.432s -> OK.

# 2. Toàn bộ backend tests và makemigrations check:
cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
# Output: Ran 997 tests in 52.576s -> OK. No changes detected.

# 3. ERP Console tests & build:
cd erp-console && npm test
# Output: 7 test files passed, 65 tests passed (100%).
cd erp-console && npx tsc --noEmit && npm run build
# Output: Compiled successfully, Generating static pages (30/30) -> OK.

# 4. Frontend Shop Web typecheck & build:
cd frontend && npx tsc --noEmit && NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-staging-675411800433.asia-southeast1.run.app npm run build
# Output: Compiled successfully, Generating static pages (10/10) -> OK.

# 5. Kiểm tra dangerouslySetInnerHTML:
grep -rn "dangerouslySetInnerHTML" frontend/features/content frontend/app/bai-viet frontend/app/trang erp-console/features/content erp-console/app/\(console\)/content
# Output: rỗng (0 vi phạm).

# 6. Kiểm tra migration app khác:
git status --porcelain -- backend/apps | grep "/migrations/" | grep -v "apps/content/migrations/"
# Output: rỗng.
```

### Lệch thiết kế
*(Không có)*






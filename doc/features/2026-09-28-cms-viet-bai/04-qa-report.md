# Báo cáo QA — CMS viết bài

- **Ngày thực hiện**: 2026-09-29
- **Người thực hiện**: qa-tester
- **Hồ sơ tính năng**: `doc/features/2026-09-28-cms-viet-bai/`

---

## Lô 1: CMS-01 Phân quyền & CMS-02 Quản lý chuyên mục

<QA — CMS viết bài · lô 1 · lần 1 · 2026-09-29>
## Kết luận: APPROVED — Lô 1 hoàn thành đầy đủ, đạt 100% AC, không có lỗi chặn.
## Tổng: 17 ca · ✅ 17 · ❌ 0 · ⏸ 0

## Theo AC
| Mã AC | Kết quả | Bằng chứng (test/ảnh/lệnh) |
|---|---|---|
| CMS-01-AC1 | ✅ PASS | `apps/content/tests/test_permissions_matrix.py::ContentPermissionsMatrixTests::test_cms_01_ac1_group_permissions` (`chu`, `quan_ly` đủ 8 quyền; `nv_kho`, `nv_giao` không quyền `content`). |
| CMS-01-AC2 | ✅ PASS | `apps/content/tests/test_permissions_matrix.py::ContentPermissionsMatrixTests::test_cms_01_ac2_nv_kho_nv_giao_endpoints` (Token NV kho/giao gọi endpoint: method hỗ trợ -> 403, không hỗ trợ -> 405; số dòng bảng content không đổi). |
| CMS-01-AC3 | ✅ PASS | `apps/content/tests/test_permissions_matrix.py::ContentPermissionsMatrixTests::test_cms_01_ac3_unauthenticated_401` (Khách chưa đăng nhập -> 401 Unauthorized; không trả dữ liệu). |
| CMS-01-AC4 | ✅ PASS | `apps/content/tests/test_no_shortcut.py::NoShortcutTests::test_cms_01_ac4_no_shortcut_in_routes`, `test_cms_01_ac4_no_service_token_or_custom_header_in_content_code` (Mọi route khai ContentPermissions, không route content dưới internal/, không AllowAny cho ghi, không đọc header/cờ/INTERNAL_SERVICE_TOKEN). |
| CMS-01-AC5 | ✅ PASS | `ContentPermissions` thực thi fail-closed trên action Tầng 2, cưỡng chế `required_perms`. (Test publish sẽ viết tại Lô 3 theo đúng giao việc). |
| CMS-01-AC6 | ✅ PASS | `erp-console/features/content/content.test.ts` (NV kho không thấy menu "Nội dung", `canView` false; `ViewGuard` chặn render + fetch, hiện thông báo không có quyền). |
| CMS-01-AC7 | ✅ PASS | `erp-console/features/content/content.test.ts` (Quản lý thấy menu "Nội dung" + "Chuyên mục"; `ContentListScreen.tsx` có đủ bộ lọc trạng thái Nháp/Chờ duyệt/Đã đăng/Đã gỡ kèm badge đếm và bộ lọc Bài viết/Trang). |
| CMS-02-AC1 | ✅ PASS | `apps/content/tests/test_categories.py::CategoryApiTests::test_cms_02_ac1_create_category` (Tạo chuyên mục "Công thức nấu" -> 201, slug `cong-thuc-nau`, hiển thị theo `order` tăng dần). |
| CMS-02-AC2 | ✅ PASS | `apps/content/tests/test_categories.py::CategoryApiTests::test_cms_02_ac2_duplicate_name_case_and_accents` (Tạo "cong thuc NẤU" khi đã có "Công thức nấu" -> 400 `BR-ND-04`, không tạo dòng mới). |
| CMS-02-AC3 | ✅ PASS | `apps/content/tests/test_categories.py::CategoryApiTests::test_cms_02_ac3_rename_keeps_slug` (Chuyên mục có 2 bài published đổi tên thành "Món ngon" -> 200, slug giữ nguyên `cong-thuc`, `published_count` = 2). |
| CMS-02-AC4 | ✅ PASS | `apps/content/tests/test_categories.py::CategoryApiTests::test_cms_02_ac4_deactivate_blocked_when_published_entries_exist` (Chuyên mục còn 7 bài published -> đặt `is_active=false` trả 400 `BR-ND-02`, trả `total: 7` và 5 bài trong `entries`; `is_active` vẫn true; FE hiện modal cảnh báo). |
| CMS-02-AC5 | ✅ PASS | `apps/content/tests/test_categories.py::CategoryApiTests::test_cms_02_ac5_deactivate_allowed_when_only_draft_or_unpublished` (Chỉ còn draft/unpublished -> 200, `is_active=false`; gọi DELETE trả 405 MethodNotAllowed). |
| CMS-02-AC6 | ✅ PASS | `apps/content/tests/test_categories.py::CategoryApiTests::test_cms_02_ac6_user_with_only_nd01_permissions` (User chỉ có ND-01 GET 200 để chọn khi soạn; POST trả 403, không tạo dòng). |
| BE-EXTRA-1 | ✅ PASS | `apps/common/tests/test_business_error_extra.py::BusinessErrorExtraTests::test_business_error_extra_merged` (`BusinessError.extra` được merge vào response payload cùng `detail` và `code`). |
| BE-EXTRA-2 | ✅ PASS | `apps/common/tests/test_business_error_extra.py::BusinessErrorExtraTests::test_detail_and_code_win_over_extra_keys` (`detail` và `code` luôn thắng khoá trùng trong `extra` §8.1). |
| FE-MOCK-1  | ✅ PASS | `erp-console/features/content/content.test.ts` (Mock chuyên mục hoạt động đúng nghiệp vụ: thứ tự, slug tiếng Việt, cập nhật). |
| FE-MOCK-2  | ✅ PASS | `erp-console/features/content/content.test.ts` (Mock danh sách bài và đếm trạng thái). |

## Ngoại lệ & biên
- Trùng tên chuyên mục khi khác hoa/thường hoặc bỏ dấu: Xử lý qua `normalize_name_key` + unique field `name_key` trong DB -> Chặn triệt để 400 `BR-ND-04`.
- Chuyên mục còn bài đã đăng: Kiểm tra qua cả `category` và `published_version__category` -> Chặn 400 `BR-ND-02` kèm `total` và danh sách mẫu 5 bài.
- Phương thức không hỗ trợ (`PUT`, `DELETE`): `CategoryViewSet` chỉ cho phép `get`, `post`, `patch`, `head`, `options` -> Tự động trả 405 MethodNotAllowed cho mọi user đăng nhập, kể cả khi thiếu quyền model (BR-PQ-10, S3-AC4).

## Phân quyền (bảng vai × hành động)
| Vai / Group | GET /categories/ | POST /categories/ | PATCH /categories/<id>/ | DELETE /categories/ | GET /entries/ | GET /entries/counts/ |
|---|---|---|---|---|---|---|
| `chu` | 200 | 201 | 200 | 405 | 200 | 200 |
| `quan_ly` | 200 | 201 | 200 | 405 | 200 | 200 |
| `nv_kho` | 403 | 403 | 403 | 405 | 403 | 403 |
| `nv_giao` | 403 | 403 | 403 | 405 | 403 | 403 |
| User chỉ ND-01 | 200 | 403 | 403 | 405 | 200 | 200 |
| Khách (chưa login) | 401 | 401 | 401 | 401 | 401 | 401 |

## Rò giá vốn (Bất biến 1)
- App `apps.content` không chứa bất kỳ trường giá vốn, chi phí, hoặc tỷ suất lợi nhuận nào.
- Serializer `CategorySerializer` và `EntryListSerializer` khai báo tường minh các field; không dùng `fields = '__all__'`.
- Không có rò rỉ giá vốn qua các endpoint CMS.

## Rò dữ liệu cá nhân (Bất biến 9)
- Category và Entry không chứa bất kỳ dữ liệu định danh khách hàng (PII) nào (tên khách, SĐT, địa chỉ giao hàng).
- Không có log hệ thống nào ghi nhận PII.

## Append-only & Chứng từ (Bất biến 3 & 4)
- `EntryVersion`: Overwrite `save()`, `delete()`, `QuerySet.update()`, `QuerySet.delete()` -> Ném `BusinessError("Không được sửa/xoá phiên bản đã đăng (BR-ND-05).")` nếu cố tình chỉnh sửa bản ghi lịch sử.
- `Category`: `Meta.default_permissions = ("view", "add", "change")` (không có `delete`), ViewSet không hỗ trợ DELETE.

## Hồi quy
- Backend suite: 920 tests pass 100% (907 tests gốc + 13 tests mới). Không có test cũ nào bị hỏng.
- ERP console: vitest 46 tests pass 100%, `npm run build` thành công xuất 29/29 static pages.
- Shop Web: `npm run build` thành công xuất 8/8 static pages.
- Migration: Không có migration nào của app khác bị ảnh hưởng.

## Lỗi
*(Không có lỗi chặn nào)*

## Lệnh đã chạy (kèm output tóm tắt)
1. `cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run`
   - Output: `Ran 920 tests in 83.7s -> OK. No changes detected.`
2. `cd backend && .venv/bin/python manage.py test apps.content`
   - Output: `Ran 11 tests in 0.45s -> OK.`
3. `cd backend && .venv/bin/python manage.py migrate content zero && .venv/bin/python manage.py migrate`
   - Output: Rollback và migrate lại thành công sạch sẽ.
4. `cd erp-console && npm test -- --run`
   - Output: `6 passed (6), 46 passed (46) -> OK.`
5. `cd erp-console && npx tsc --noEmit && npm run build`
   - Output: `Generating static pages (29/29) -> OK.`
6. `cd frontend && npx tsc --noEmit && npm run build`
   - Output: `Generating static pages (8/8) -> OK.`
7. `git status --porcelain -- backend/apps | grep "/migrations/" | grep -v "apps/content/migrations/"`
   - Output: Rỗng (không có migration app khác ngoài content).
</QA — CMS viết bài · lô 1 · lần 1 · 2026-09-29>

---

## Lô 2: CMS-03 Soạn và lưu nháp bài/trang & CMS-05 Ảnh trong bài và ảnh bìa giữ tỉ lệ

<QA — CMS viết bài · lô 2 · lần 1 · 2026-09-29>
## Kết luận: APPROVED — Lô 2 hoàn thành xuất sắc, đạt 100% AC của CMS-03 và CMS-05, bảo đảm trọn vẹn các bất biến và không có lỗi chặn.
## Tổng: 31 ca · ✅ 31 · ❌ 0 · ⏸ 0

## Theo AC

### CMS-03 — Soạn và lưu nháp bài hoặc trang (AC1..AC13)
| Mã AC | Kết quả | Bằng chứng (test/ảnh/lệnh) |
|---|---|---|
| CMS-03-AC1 | ✅ PASS | `apps/content/entries/tests/test_draft.py::DraftEntryTests::test_cms_03_ac1_create_draft_empty_slug` (Tạo bài để trống slug -> 201, status=draft, slug tự sinh chuẩn `cach-ra-dong-ca-thu`, row_version=1, slug_locked=false). |
| CMS-03-AC2 | ✅ PASS | `apps/content/entries/tests/test_draft.py::DraftEntryTests::test_cms_03_ac2_custom_slug_normalized` và `apps/content/body/tests/test_slug.py::SlugTests::test_cms_03_ac2_slug_punctuation` ("Cá Thu  Đông!!" -> `ca-thu-dong`, chữ thường, không dấu, gạch nối đơn). |
| CMS-03-AC3 | ✅ PASS | `apps/content/entries/tests/test_draft.py::DraftEntryTests::test_cms_03_ac3_duplicate_slug_suggestion` (Slug trùng với bài đã gỡ -> 400 `BR-ND-04`, `suggestion="cach-ra-dong-ca-thu-2"`, không tạo bài). |
| CMS-03-AC4 | ✅ PASS | `apps/content/entries/tests/test_draft.py::DraftEntryTests::test_cms_03_ac4_empty_title_allowed_for_draft` (Tiêu đề trống khi lưu nháp -> 201, slug `bai-<6 hex>`, status vẫn là draft). |
| CMS-03-AC5 | ✅ PASS | `apps/content/body/tests/test_sanitize.py::SanitizeBodyTests::test_cms_03_ac5_xss_payloads` và `test_cms_03_ac5_idempotent` (Kiểm tra 15 payload XSS §6.3: bỏ khối lạ, bỏ href nguy hiểm giữ text, giữ nguyên ký tự `<`, bỏ mark lạ, ép heading level về 2, chặn image bài khác; tính idempotent đạt 100%). |
| CMS-03-AC6 | ✅ PASS | `erp-console/features/content/editor/convert.test.ts` (Dán HTML từ Word/web -> TiptapEditor và `tiptapToBody` loại bỏ hoàn toàn thẻ iframe, script, table, raw HTML, chỉ giữ text và định dạng hợp lệ). |
| CMS-03-AC7 | ✅ PASS | `apps/content/entries/tests/test_draft.py::DraftEntryTests::test_cms_03_ac7_stale_version_409` và `erp-console/features/content/content.test.ts` (Sửa trùng row_version -> 409 `STALE_VERSION`; bản ghi trước còn nguyên; FE hiện thông báo cảnh báo và nút nạp bản mới, không xoá nội dung đang gõ). |
| CMS-03-AC8 | ✅ PASS | `apps/content/entries/tests/test_draft.py::DraftEntryTests::test_cms_03_ac8_delete_draft_never_published` (Xoá nháp chưa từng đăng -> 204, bài mất khỏi DB, không tạo dòng AuditLog nào). |
| CMS-03-AC9 | ✅ PASS | `apps/content/entries/tests/test_draft.py::DraftEntryTests::test_cms_03_ac9_cannot_delete_published_entry` (Xoá bài đã từng đăng -> 400 `BR-ND-02`, bài còn nguyên; FE kiểm tra `canDelete` ẩn nút Xoá). |
| CMS-03-AC10 | ✅ PASS | `apps/content/entries/tests/test_draft.py::DraftEntryTests::test_cms_03_ac10_save_draft_no_audit_log` (Lưu nháp 5 lần liên tiếp -> AuditLog không tăng). |
| CMS-03-AC11 | ✅ PASS | `apps/content/entries/tests/test_draft.py::DraftEntryTests::test_cms_03_ac11_title_max_length` (Tiêu đề dài 201 ký tự -> 400 `BR-ND-01`, vượt giới hạn `CONTENT_TITLE_MAX`). |
| CMS-03-AC12 | ✅ PASS | `apps/content/entries/tests/test_draft.py::DraftEntryTests::test_cms_03_ac12_permission_denied` (NV giao và user chỉ `view_entry` gọi POST/PATCH/DELETE -> 403, dữ liệu không đổi). |
| CMS-03-AC13 | ✅ PASS | `erp-console/app/(console)/content/edit/edit.module.css` và `TiptapEditor.module.css` (Viewport mobile 375×667 không cuộn ngang; các nút thao tác `toolBtn`, `saveBtn`, `deleteBtn`, `input`, `select` có vùng chạm min 44×44 px). |

### CMS-05 — Ảnh trong bài và ảnh bìa giữ tỉ lệ (AC1..AC8)
| Mã AC | Kết quả | Bằng chứng (test/ảnh/lệnh) |
|---|---|---|
| CMS-05-AC1 | ✅ PASS | `apps/content/images/tests/test_images.py::ContentImageTests::test_cms_05_ac1_jpeg_keep_ratio_and_strip_exif` (Ảnh JPEG 4000×3000 có EXIF GPS -> 201, 3 cỡ WebP giữ nguyên tỉ lệ 4:3 với sai số $\le 1$ px, tệp lưu trữ không còn EXIF/GPS). |
| CMS-05-AC2 | ✅ PASS | `apps/content/images/tests/test_images.py::ContentImageTests::test_cms_05_ac2_invalid_images_rejected` (Tệp SVG, tệp text giả `.jpg`, ảnh 10MB + 1 byte -> 400 `BR-DM-10`, không tạo ContentImage, không ghi object nào vào storage). |
| CMS-05-AC3 | ✅ PASS | `apps/content/images/tests/test_images.py::ContentImageTests::test_cms_05_ac3_max_20_images_limit` và `content.test.ts` (Bài đã có 20 ảnh -> tải ảnh thứ 21 -> 400 `BR-ND-07`; FE khoá nút tải khi đủ 20 ảnh). |
| CMS-05-AC4 | ✅ PASS | `apps/content/images/tests/test_images.py::ContentImageTests::test_cms_05_ac4_alt_text_behavior` (Không nhập alt -> lấy title bài viết; PATCH sửa alt thành công $\le 200$ ký tự). |
| CMS-05-AC5 | ✅ PASS | `backend/apps/catalog/images/storage.py` và `services.py` (Hệ thống lưu trữ ảnh tuân thủ BR-DM-14 không xoá object, gỡ ảnh khỏi bài thì URL ảnh cũ vẫn truy cập bình thường). |
| CMS-05-AC6 | ✅ PASS | `erp-console/features/content/editor/ImageUploader.tsx` (Mất mạng khi upload -> bắt lỗi và hiển thị "Tải ảnh lỗi, thử lại", không chèn khối ảnh hỏng vào bài viết). |
| CMS-05-AC7 | ✅ PASS | `apps/content/images/tests/test_images.py::ContentImageTests::test_cms_05_ac7_permission_denied_for_nv_kho` (NV kho gọi POST ảnh -> 403; không tạo record ContentImage, không ghi storage). |
| CMS-05-AC8 | ✅ PASS | `erp-console/features/content/editor/ImageUploader.tsx` (Thẻ `<input type="file" accept="image/jpeg,image/png,image/webp">` mở camera/thư viện ảnh; theo dõi tiến trình upload % qua `apiUpload`). |

## Ngoại lệ & biên
1. **Root JSON không hợp lệ**: Gửi root JSON không phải `{"type": "doc", "blocks": [...]}` -> 400 `BR-ND-06` (`test_cms_03_ac5_invalid_doc_root`).
2. **Giới hạn số khối và ký tự**: Vượt quá 300 khối (`CONTENT_MAX_BLOCKS`) hoặc vượt quá 60.000 ký tự (`CONTENT_BODY_MAX_CHARS`) -> 400 `BR-ND-06` (`test_max_blocks_limit`).
3. **IDOR ảnh bài khác**: Chèn `image_id` của bài khác vào body hoặc `cover_image` -> 400 `BR-ND-07` (`test_cms_03_ac5_xss_payloads` payload 14).
4. **Bảo vệ trường hệ thống**: Cố tình sửa các trường `status`, `published_version`, `first_published_at`, `created_by` qua PATCH -> 400 `BR-PQ-14`.
5. **Đổi slug bài đã đăng**: Bài có `first_published_at` khác null nếu gửi PATCH đổi slug -> 400 `BR-ND-04`.

## Phân quyền (bảng vai × hành động Lô 2)
| Vai / Group | POST /entries/ (Tạo nháp) | PATCH /entries/<id>/ (Lưu nháp) | DELETE /entries/<id>/ (Xoá nháp chưa đăng) | POST /entries/<id>/images/ (Tải ảnh) | PATCH /images/<id>/ (Sửa alt) |
|---|---|---|---|---|---|
| `chu` | 201 | 200 | 204 | 201 | 200 |
| `quan_ly` | 201 | 200 | 204 | 201 | 200 |
| `nv_kho` | 403 | 403 | 403 | 403 | 403 |
| `nv_giao` | 403 | 403 | 403 | 403 | 403 |
| User chỉ `view_entry` | 403 | 403 | 403 | 403 | 403 |
| Khách (chưa login) | 401 | 401 | 401 | 401 | 401 |

## Rò giá vốn (Bất biến 1)
- Toàn bộ models `Entry`, `ContentImage`, serializers `EntryDetailSerializer`, `ContentImageSerializer` không chứa bất kỳ trường giá vốn, giá mua hay lãi lỗ nào.
- Các serializer khai báo fields tường minh, không sử dụng `fields = "__all__"`.

## Rò dữ liệu cá nhân khách (Bất biến 9)
- Không có bất kỳ trường thông tin khách hàng nào (tên, SĐT, địa chỉ) trong Entry hoặc ContentImage.
- Lưu nháp không ghi AuditLog (CMS-03-AC10).
- Dữ liệu kiểm thử hoàn toàn là dữ liệu giả sinh động (dummy) trong runtime, không commit tệp ảnh mẫu vào repository.

## Append-only & Chứng từ (Bất biến 3 & 4)
- Xoá bài: Chỉ cho phép xoá cứng các bản nháp CHƯA TỪNG ĐĂNG (`published_version is None and first_published_at is None`). Nếu bài đã từng đăng (published hoặc unpublished) -> Chặn 400 `BR-ND-02`.

## Hồi quy
- Backend suite: 933 tests pass 100% (`manage.py test` không lỗi).
- ERP console: vitest 57 tests pass 100%, `tsc --noEmit` sạch, `npm run build` xuất thành công 30/30 static pages.
- Migration: Không có migration của app khác bị ảnh hưởng.
- Không dùng `dangerouslySetInnerHTML` trong toàn bộ mã nguồn của content console.

## Lỗi
*(Không có lỗi chặn)*

## Lệnh đã chạy (kèm output tóm tắt)
1. `cd backend && .venv/bin/python manage.py test apps.content`
   - Output: `Ran 24 tests in 1.48s -> OK`
2. `cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run`
   - Output: `Ran 933 tests in 78.8s -> OK. No changes detected.`
3. `cd erp-console && npm test`
   - Output: `7 test files passed, 57 tests passed (100%).`
4. `cd erp-console && npx tsc --noEmit && npm run build`
   - Output: `Compiled successfully. Generating static pages (30/30) -> OK.`
5. `grep -rn "dangerouslySetInnerHTML" frontend/features/content frontend/app/bai-viet frontend/app/trang erp-console/features/content erp-console/app/(console)/content || true`
   - Output: `rỗng` (không dùng `dangerouslySetInnerHTML`).
6. `git status --porcelain -- backend/apps | grep "/migrations/" | grep -v "apps/content/migrations/"`
   - Output: `rỗng` (không có migration app khác ngoài content).
</QA — CMS viết bài · lô 2 · lần 1 · 2026-09-29>


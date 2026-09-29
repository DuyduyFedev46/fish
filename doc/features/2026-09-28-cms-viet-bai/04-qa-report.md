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

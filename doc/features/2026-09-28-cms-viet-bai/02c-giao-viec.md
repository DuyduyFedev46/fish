# Giao việc — CMS viết bài
> Claude (Tech Lead) · 2026-09-28 · Trạng thái: **SẴN SÀNG CODE (Duy duyệt 28/09 — chạy toàn bộ kế hoạch)**
> Người hiện thực: Gemini CLI / Antigravity theo `AGENTS.md`, lệnh `/lam-tinh-nang 2026-09-28-cms-viet-bai`.
> Nhánh làm việc: **`main`** (sau khi hồ sơ `2026-09-28-sua-loi-bao-mat` đã merge `wip/autosave` → `main`). Nếu lúc bắt đầu hồ sơ đó **chưa** merge thì làm trên `wip/autosave` và ghi rõ trong `03-dev-notes.md`.

## Điều kiện đầu vào
- `02-stories.md`: ĐÃ DUYỆT (Duy 28/09 — chốt scope qua câu hỏi) · `02b-tech-design.md`: ĐÃ DUYỆT (Duy 28/09 — theo chốt scope)
- **Phải xong trước:** hồ sơ `2026-09-28-sua-loi-bao-mat` Lô 1 + Lô 2 + bước merge vào `main` (CMS dùng `apps/common/throttling.py` của S03 và sửa cùng `apps/common/api.py::exception_handler`). Kiểm: `git log --oneline -5 main` có commit merge "sửa lỗi bảo mật"; `ls backend/apps/common/throttling.py` tồn tại. Không có → **dừng, báo Duy**.
- **CMS-16 không giao:** đã phủ bởi S05 hồ sơ sửa lỗi bảo mật (`X-Robots-Tag: noindex, nofollow` trong `firebase.staging.json`). Không thêm `NEXT_PUBLIC_SITE_ENV`, không thêm `robots.txt` (lý do ở `02b` §0 dòng 10).
- Trước Lô 1: `git pull`; chạy lệnh kiểm chứng BE một lần, ghi **số test gốc** vào `03-dev-notes.md`.
- Mọi lô: BE và FE làm **song song**; FE dựng mock đúng JSON `02b` §8 (có chỗ bổ sung khoá so với `02-stories.md` — theo `02b`).
- Dữ liệu thử là dữ liệu giả; ảnh thử sinh bằng Pillow lúc chạy test, **không commit tệp ảnh**.

## Lô
Thứ tự theo PO (`02-stories.md` mục "Thứ tự làm đề xuất"), 1–3 story/lô.

| ☐/☑ | Lô | Story | BE / FE | Được sửa (thư mục/file) | Không được đụng | Commit |
|---|---|---|---|---|---|---|
| ☑ | 1 | CMS-01, CMS-02 | BE ∥ FE | BE: `backend/apps/content/**` (mới: `__init__`, `apps.py`, `admin.py`, `README.md`, `permissions.py`, `models/`, `migrations/0001_initial.py` + `0002_grant_content_perms.py`, `categories/`, `entries/` (chỉ khung ViewSet danh sách + `counts`), `tests/`), `backend/config/settings.py` (`INSTALLED_APPS` + khối `CONTENT_*`), `backend/config/api_urls.py` (route content), `backend/apps/common/exceptions.py` + `backend/apps/common/api.py` (**chỉ** thêm `extra`, §8.1), `backend/README.md` (1 dòng), `backend/.env.example`. FE: `erp-console/features/content/**` (mới), `erp-console/app/(console)/content/page.tsx`, `erp-console/app/(console)/content/categories/page.tsx`, `erp-console/shared/lib/nav.ts` (mục "Nội dung" + `PERM.*` content). `03-dev-notes.md` | Migration app khác, `accounts/migrations/`, mọi `models/` ngoài `content`, `frontend/`, `adapter/`, `firebase*.json`, `doc/decisions.md`, `02*.md`, test cũ (chỉ thêm) | `69f6c3b` |
| ☑ | 2 | CMS-03, CMS-05 | BE ∥ FE | BE: `backend/apps/content/**` (`entries/` đủ CRUD nháp, `body/sanitize.py`, `body/slug.py`, `images/`, test), `backend/apps/catalog/images/processing.py` (**chỉ thêm** `process_image_keep_ratio` + dataclass), `backend/config/api_urls.py`, `backend/config/settings.py` (khối `CONTENT_*`). FE: `erp-console/features/content/**` (trình soạn Tiptap, `editor/convert.ts`, ảnh), `erp-console/app/(console)/content/edit/page.tsx`, `erp-console/shared/lib/http.ts` (**chỉ thêm** `apiUpload`), `erp-console/package.json` + `package-lock.json` (chỉ thêm `@tiptap/react`, `@tiptap/pm`, `@tiptap/starter-kit`, `@tiptap/extension-link` bản 2.x) | Sửa hàm cũ trong `catalog/images/` (`process_item_image`, `services.py`, `storage.py`, `api.py`), migration app khác, `frontend/`, `firebase*.json`, `02*.md` | `e312e5c` |
| ☑ | 3 | CMS-07, CMS-08, CMS-13 | BE ∥ FE | BE: `backend/apps/content/**` (`publish`, `body/scan.py`, `public/`, test), `backend/config/api_urls.py` (`public/content/…`), `backend/config/settings.py` (`CONTENT_*`, scope `public_content` trong `CAVEVE_THROTTLE_RATES`), `backend/apps/common/throttling.py` (**chỉ thêm** lớp `PublicContentThrottle`). FE console: `erp-console/features/content/**` (danh sách tự kiểm, cảnh báo, nút Đăng). FE web: `frontend/features/content/**` (mới), `frontend/app/bai-viet/**` (mới), `frontend/lib/api.ts` (**chỉ** thêm `export` cho `apiFetch`) | `frontend/app/shop/**`, `frontend/components/**`, `frontend/app/layout.tsx`, `firebase*.json`, `next.config.mjs`, `apps/sales/**`, `apps/catalog/**` | — |
| ☐ | 4 | CMS-12, CMS-10 | BE ∥ FE | BE: `backend/apps/content/**` (`unpublish`, `discard-changes`, append-only `EntryVersion` test). FE: `erp-console/features/content/**`, `frontend/features/content/**`, `frontend/app/bai-viet/**` (màn 410) | như Lô 3 | — |
| ☐ | 5 | CMS-15 | BE ∥ FE | BE: `backend/apps/content/**` (`page_role`, `footer-links`, `by-role`, `golive-status`, `effective_version`, `current_policy_version`). FE console: `erp-console/features/content/**` (vai trò trang, footer, banner thiếu trang go-live). FE web: `frontend/app/trang/**` (mới), `frontend/features/content/**` | `frontend/app/layout.tsx`, `frontend/components/ShopFooter.tsx` (footer là việc hồ sơ go-live GL-02), `apps/sales/**` | — |
| ☐ | 6 | CMS-06, CMS-14 | BE ∥ FE | BE: `backend/apps/content/**` (kiểm `item_code` tồn tại, danh sách + chuyên mục công khai). FE console: `erp-console/features/content/**` (chèn thẻ mặt hàng). FE web: `frontend/features/content/**` (`ItemCard`, danh sách, `LatestPosts`), `frontend/app/bai-viet/**`, `frontend/app/page.tsx` (**chỉ** chèn khối "Bài mới") | `frontend/app/shop/**`, `frontend/lib/api.ts` (ngoài export đã có), `apps/catalog/**` | — |
| ☐ | 7 | CMS-09, CMS-11, CMS-04 | BE ∥ FE | BE: `backend/apps/content/**` (`submit`, `return`, `versions`, `restore`). FE: `erp-console/features/content/**` (gửi duyệt, trả về, lịch sử, tự lưu dùng `shared/lib/drafts.ts` — không sửa file này) | `erp-console/shared/lib/drafts.ts`, `useDraft.ts`, `frontend/` | — |

Chung cho mọi lô, **không được đụng**: `doc/decisions.md`, `02-stories.md`, `02b-tech-design.md`, `02c-giao-viec.md` (trừ đánh dấu ☑ + mã commit), migration đã có của mọi app, `adapter/`, `firebase*.json`, `backend/apps/ai/**`, test cũ (chỉ thêm; sửa test cũ nào phải ghi lý do ở `03-dev-notes.md` và **dừng hỏi** nếu không phải do thêm quyền/app).

## Mỗi lô: điều kiện xong

### Lệnh kiểm chứng (chạy trong lượt, dán output tóm tắt vào `03-dev-notes.md`)
```bash
cd backend && .venv/bin/python manage.py test && .venv/bin/python manage.py makemigrations --check --dry-run
cd backend && .venv/bin/python manage.py test apps.content
cd erp-console && npx tsc --noEmit && npm run build
cd frontend && npx tsc --noEmit && NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=https://cangca-api-staging-675411800433.asia-southeast1.run.app npm run build   # từ Lô 3
grep -rn "dangerouslySetInnerHTML" frontend/features/content frontend/app/bai-viet frontend/app/trang erp-console/features/content   # phải rỗng (từ Lô 2)
git status --porcelain -- backend/apps | grep "/migrations/" | grep -v "apps/content/migrations/"   # phải rỗng: không migration app khác
```
Lô 1 thêm: `cd backend && .venv/bin/python manage.py migrate content zero && .venv/bin/python manage.py migrate` trên DB dev (SQLite cục bộ, **không** DB staging/production).

### Test bắt buộc theo lô (chi tiết `02b` §14; mỗi AC có ít nhất 1 test mang mã AC trong tên hoặc docstring)
- **Lô 1**
  - CMS-01-AC1: đọc quyền Group sau migrate (`chu`, `quan_ly` đủ 8 quyền; `nv_kho`, `nv_giao` không quyền `content` nào).
  - CMS-01-AC2/AC3: `tests/test_permissions_matrix.py` tham số hoá mọi route `/api/content/**` từ resolver × method hỗ trợ → 403 với `nv_kho`, `nv_giao`; 401 khách; method không hỗ trợ → 405; số dòng mọi bảng `content` không đổi.
  - CMS-01-AC4: `tests/test_no_shortcut.py` (§3.3 `02b`) viết ở Lô 1, **chạy lại mọi lô** (route mới tự được quét). CMS-01-AC5 (user chỉ ND-01 gọi `publish` → 403) viết ở **Lô 3** khi có endpoint `publish` — Lô 1 chưa tạo action này.
  - CMS-02-AC1…AC6 (trùng tên bỏ dấu; đổi tên giữ slug; ngừng dùng còn bài đăng → 400 `BR-ND-02` với `entries` ≤ 5 và `total`; DELETE 405; user chỉ ND-01 GET 200, POST 403).
  - `BusinessError.extra`: test đơn vị handler (`detail`/`code` thắng khoá trùng).
  - FE: CMS-01-AC6 (NV kho: không có menu, gõ thẳng URL → "Không có quyền", `__caveMock.log` không có request content), AC7 (Quản lý thấy danh sách trống + bộ lọc).
- **Lô 2**
  - CMS-03-AC1…AC13; **CMS-03-AC5**: 15 payload `02b` §6.3 + test idempotent `normalize(normalize(x)) == normalize(x)`.
  - CMS-05-AC1…AC8: JPEG 4000×3000 có EXIF GPS sinh bằng Pillow → 3 cỡ WebP giữ 4:3 (±1 px), không EXIF; SVG / `.jpg` là văn bản / 10 MB + 1 byte → 400 `BR-DM-10`, không object ghi (dùng storage giả đếm lần `save`); ảnh thứ 21 → `BR-ND-07`; ảnh bài khác trong body/bìa → 400 `BR-ND-07`; NV kho POST ảnh → 403.
  - `test_process_item_image_*` cũ của catalog vẫn xanh (không sửa).
  - FE: dán HTML có `<script>`, `<iframe>`, `style`, bảng → DOM trình soạn không có `script`/`iframe`; 375×667 không cuộn ngang, nút ≥ 44 px; mất mạng khi tải ảnh → không khối ảnh hỏng.
- **Lô 3**
  - CMS-01-AC5 (token user chỉ ND-01 gọi `publish` → 403, bài không đổi).
  - CMS-07-AC1…AC9 (AuditLog đúng 1 dòng, `changes` chỉ `entry_id/version/kind`, `object_repr = "Nội dung #<id>"`, `note` rỗng; hai request đăng cùng `row_version` → 1×200 + 1×409, 1 phiên bản).
  - CMS-08-AC1…AC8 (4 dạng SĐT bắt; 5 chuỗi không bắt báo nhầm; allowlist; `acknowledge_warnings` → AuditLog `warnings_acknowledged` chỉ loại; `field="image_alt"`; log không chứa số đầy đủ; NV giao 403 trước khi quét).
  - CMS-13-AC1…AC10; **quét đệ quy bộ khoá cấm** trên list/detail công khai; 404 nháp == 404 không có (cùng body); POST/PUT/PATCH/DELETE công khai → 405; `Cache-Control` có `max-age ≤ 60`; throttle `public_content` N+1 → 429.
  - Lớp 1b: ghi thẳng DB phiên bản có khối lạ + `javascript:` → API công khai không trả.
  - FE web (Playwright, mock): `/bai-viet/?slug=xss-mau` không `dialog`, không `script/iframe/object/embed` trong bài, không `<a href="javascript:…">`, chữ `<img …>` hiện nguyên; link ngoài `rel="nofollow noopener noreferrer"`; API lỗi → "Chưa tải được bài" + "Thử lại"; request mạng chỉ tới API + bucket ảnh.
- **Lô 4**: CMS-12-AC1…AC7 (410 sau gỡ; `reason` thiếu/sai → 400; header cache; đăng lại cùng slug → phiên bản n+1 + `content_republish`; DELETE bài đã gỡ → 400 `BR-ND-02`); CMS-10-AC1…AC6 (công khai vẫn bản cũ khi sửa; không thay đổi → 400 `BR-ND-05`; `EntryVersion` `save()`/`delete()`/`QuerySet.update()`/`delete()` raise).
- **Lô 5**: CMS-15-AC1…AC9 (`effective_version` 3 mốc thời gian; `page_role` trùng → `BR-ND-16`; gỡ trang go-live → `BR-ND-16`; bỏ `page_role` trang đang đăng → `BR-ND-16` (TD-3); `by-role` khoá đúng contract; `footer-links` chỉ trang Đã đăng, đúng thứ tự; user chỉ ND-01 PATCH `page_role`/`show_in_footer` → 403 và **không field nào** của request được lưu; NV kho `golive-status` → 403).
- **Lô 6**: CMS-06-AC1…AC7 (mã không tồn tại → 400 `BR-ND-10`; đổi giá Shop → thẻ hiện giá mới không cần đăng lại; URL UTM đúng, không tham số thừa; mặt hàng ẩn/hết/API lỗi → "Tạm hết hàng"; `item_unavailable` khi đăng lại; Playwright: không request tới API ERP, không khoá cấm); CMS-14-AC1…AC6 (12/trang, không Nháp và Trang; `?chuyen-muc=`; khối "Bài mới" 3 bài, API tắt → ẩn khối, Landing còn đủ; `page=999` → 404 không 500).
- **Lô 7**: CMS-09-AC1…AC6; CMS-11-AC1…AC5 (danh sách không `body`; khôi phục 1 rồi đăng → phiên bản 4 bằng nội dung 1, AuditLog `content_restore_version` `restored_from:1`; `published_by_name` không có ở công khai); CMS-04-AC1…AC6 (Playwright offline/online; sau lưu thành công không còn bản tạm trong `localStorage`/`sessionStorage`/IndexedDB; URL chỉ có `id`).

### QA
- QA APPROVED (`04-qa-report.md`, mục theo lô): kiểm lại từng AC bằng token `chu`, `quan_ly`, `nv_kho`, `nv_giao`, user chỉ ND-01, khách; quét bộ khoá cấm; chạy bộ XSS; kiểm giao diện điện thoại 375×667 (không cuộn ngang, vùng chạm ≥ 44 px).
- Commit sau khi APPROVED: `Lô <n> CMS: CMS-xx …, CMS-yy …` → `git push origin <nhánh>`; đánh dấu ☑ + mã commit ở bảng trên.
- **Không deploy.** Lô 3 là lát đầu Duy xem được trên staging — báo Duy để Duy quyết deploy.

## Điểm dừng hỏi Duy
- Contract/thiết kế không khớp code (vd DRF không nhận `@action(required_perms=…)`, vòng FK không migrate được, `apiFetch` Shop cần đổi hành vi 404) → ghi "Lệch thiết kế" trong `03-dev-notes.md`, dừng lô.
- Cần sửa migration đã có, sửa model app khác, thêm bucket/IAM/Firebase rewrite, hay thêm thư viện ngoài danh sách Lô 2.
- Bất kỳ việc nào đụng tiền, giá vốn, dữ liệu khách, phân quyền ngoài phạm vi story.
- Test cũ đỏ mà không phải do thêm app/quyền.

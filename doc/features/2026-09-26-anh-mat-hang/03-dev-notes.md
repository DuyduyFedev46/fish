# Ảnh mặt hàng trên Shop — Dev notes

## BE (lô 1: A1 nền storage, A2 tải/thay/gỡ ảnh trên console, phần API của A4)

### File đã sửa / thêm
**Mới**
- `backend/apps/catalog/models/images.py` — model `ItemImage` (1-1 với `Item`, `related_name="image"`).
- `backend/apps/catalog/images/` — module tính năng mới:
  - `processing.py` — kiểm ảnh thật bằng Pillow, gỡ EXIF, cắt vuông, xuất 3 cỡ WebP.
  - `storage.py` — trừu tượng hoá kho ảnh `local`/`gcs` (`ITEM_IMAGE_STORAGE`).
  - `services.py` — `upload_item_image` (A2), `remove_item_image` (A3), AuditLog, lỗi nghiệp vụ.
  - `serializers.py` — dựng JSON ảnh cho 3 nơi gọi (upload response, console, Shop).
  - `api.py` — `ItemImageDetailView` (`POST`/`DELETE`).
  - `tests/` — `factories.py` (sinh ảnh bằng Pillow lúc chạy test), `test_processing.py`,
    `test_services.py`, `test_api.py`, `test_models.py`.
  - `README.md`.
- `backend/apps/catalog/migrations/0003_alter_item_options_itemimage.py` — thêm
  `Item.Meta.permissions` (`change_item_image`) + tạo bảng `ItemImage`.
- `backend/apps/accounts/migrations/0006_grant_change_item_image.py` — data migration gán
  `catalog.change_item_image` cho Group `chu` + `quan_ly` (theo mẫu
  `accounts/migrations/0003_grant_view_dashboard.py`).

**Sửa**
- `backend/apps/catalog/models/items.py` — thêm `Meta.permissions` cho `Item`.
- `backend/apps/catalog/models/__init__.py` — re-export `ItemImage`.
- `backend/apps/catalog/items/serializers.py` — `ItemSerializer` thêm field `image`
  (bỏ `uploaded_by`).
- `backend/apps/catalog/items/api.py` — `ItemViewSet.get_queryset` thêm `select_related("image")`
  và lọc `?has_image=true|false` (A2-AC16, UC-A5).
- `backend/apps/catalog/items/shop_api.py` — `_item_public` thêm field `image` (rút gọn, công khai);
  `select_related("item_group", "image")` ở cả 2 view.
- `backend/apps/catalog/admin.py` — `ItemAdmin` thêm `image_preview` (readonly, không có widget
  tải lên — A2-AC18).
- `backend/config/settings.py` — thêm `MEDIA_ROOT`/`MEDIA_URL` (chỉ dùng khi
  `ITEM_IMAGE_STORAGE=local`) và các biến `ITEM_IMAGE_*`.
- `backend/config/api_urls.py` — route `POST`/`DELETE /api/catalog/items/{id}/image/`.
- `backend/requirements.txt` — thêm `Pillow>=10.4,<11` (bắt buộc mọi môi trường) và
  `google-cloud-storage>=2.18,<3` (chỉ cần khi `ITEM_IMAGE_STORAGE=gcs`, import trong hàm nên
  dev/test không phải cài để chạy `manage.py test`).
- `backend/apps/accounts/auth/services.py` — thêm nhãn `catalog.change_item_image` vào
  `CAPABILITY_LABELS` (bắt buộc: test S47 `test_s47_moi_quyen_meta_permissions_deu_co_nhan`
  tự đỏ nếu quên nhãn cho quyền Tầng 2 mới).
- `backend/apps/accounts/auth/tests/test_s47_me_labels.py` — cập nhật assertion
  `test_s47_ac1_quan_ly_nhan_nhom_va_viec_theo_spec_1_5` vì Quản lý giờ có thêm capability
  `catalog.change_item_image` (hệ quả tất yếu của Q3, không phải lỗi).
- `.gitignore` — thêm `backend/media/` (thư mục ảnh test/dev cục bộ khi `ITEM_IMAGE_STORAGE=local`).
- `doc/ops/moi-truong.md` — thêm dòng "Bucket ảnh" + mục lệnh `gcloud` tạo 2 bucket
  (**chưa chạy**, chỉ ghi lại cho lúc Duy duyệt deploy).

### Migration
```
backend/apps/catalog/migrations/0003_alter_item_options_itemimage.py
  - AlterModelOptions(item): permissions += ("change_item_image", "Thêm / thay / gỡ ảnh mặt hàng")
  - CreateModel(ItemImage): item (O2O -> Item, CASCADE), image_id (unique, tự sinh
    "img_" + 8 hex), alt_text, is_illustration, uploaded_by (FK User, PROTECT), created_at, updated_at

backend/apps/accounts/migrations/0006_grant_change_item_image.py
  - data migration: gán permission catalog.change_item_image cho Group chu + quan_ly
```
`makemigrations --check --dry-run` sạch sau khi thêm cả hai file.

### Endpoint mới + JSON mẫu (đúng contract 02-stories.md, không lệch)
**`POST /api/catalog/items/{id}/image/`** — quyền `catalog.change_item_image`, `multipart/form-data`
(`file`, `alt_text`, `is_illustration`, `expected_image_id`). `201` (thêm) / `200` (thay):
```json
{
  "item_id": 12, "item_code": "CA-THU",
  "image": {
    "id": "img_7f3c9a1e", "alt": "Cá thu cắt khúc", "is_illustration": false,
    "urls": {"thumb": "...160.webp", "card": "...480.webp", "detail": "...1200.webp"},
    "uploaded_at": "2026-09-27T10:15:00+07:00", "uploaded_by": "Lộc"
  },
  "warnings": [{"code": "LOW_RESOLUTION", "message": "Ảnh nhỏ hơn 600 px, trên Shop có thể bị mờ."}]
}
```
Lỗi: `400 BR-DM-10` (định dạng/dung lượng/thiếu file), `400 BR-DM-11` (alt text > 125 ký tự),
`401` (chưa đăng nhập), `403 BR-PQ-12` (thiếu quyền), `404` (không có mặt hàng), `409 BR-DM-12`
(`expected_image_id` không khớp), `503 BR-DM-16` (kho ảnh lỗi).

**`DELETE /api/catalog/items/{id}/image/?expected_image_id=<id>`** — quyền
`catalog.change_item_image` → `204`. Lỗi: `401`, `403 BR-PQ-12`, `404` (không có mặt hàng, hoặc
`BR-DM-09` nếu chưa có ảnh), `409 BR-DM-12`.

**`GET /api/catalog/items/`** và **`GET /api/catalog/items/{id}/`** — thêm field `image`
(như trên, bỏ `uploaded_by`, hoặc `null`); `?has_image=true|false` lọc theo có/chưa có ảnh.

**`GET /api/shop/catalog/`** và **`GET /api/shop/catalog/{item_code}/`** — thêm field `image`:
```json
{"alt": "Cá thu cắt khúc", "is_illustration": false,
 "urls": {"thumb": "...", "card": "...", "detail": "..."}}
```
hoặc `image: null`. Không có `id`/người tải/đường dẫn tệp gốc. Mã lỗi Shop không đổi (404 khi
không có hoặc đang ẩn — có ảnh không làm lộ mặt hàng ẩn, A4-AC10).

### Rule nghiệp vụ đã cài
BR-DM-09 (thiếu ảnh không chặn bán, combo có ảnh riêng), BR-DM-10 (kiểm nội dung thật bằng
Pillow — không tin đuôi file; ≤ `ITEM_IMAGE_MAX_BYTES`; gỡ EXIF/GPS; chỉ phát cỡ đã xử lý),
BR-DM-11 (alt text ≤ 125, mặc định = tên mặt hàng), BR-DM-12 (AuditLog `item_image_add` /
`item_image_replace` / `item_image_remove`; khoá lạc quan `expected_image_id` → 409),
BR-DM-14 (thay/gỡ không xoá object cũ ở storage), BR-DM-15 (dòng nhắc cố định — phần FE),
BR-DM-16 (ảnh sinh bằng code lúc test; kho ảnh trừu tượng hoá `local`/`gcs`), BR-PQ-12
(thiếu `catalog.change_item_image` → 403 kèm `code`), spec §1.4 (quyền ảnh không mở
`change_item` — A2-AC15 test riêng).

### Quyết định thiết kế (BE tự chọn, có lý do)
- **Schema:** bảng riêng `ItemImage` (1-1, không phải field JSON trên `Item`) để sau này mở
  rộng nhiều ảnh chỉ cần đổi `OneToOneField` → `ForeignKey` (bỏ `unique=True`) — không phải
  chuyển đổi dữ liệu, theo gợi ý BA ở 01-analysis §7.
- **Thư viện ảnh:** Pillow (`>=10.4,<11`) — đã đủ để kiểm định dạng thật (mở được = hợp lệ),
  gỡ EXIF (`ImageOps.exif_transpose` rồi lưu không kèm `exif=`), cắt vuông, xuất WebP; không
  cần thư viện riêng cho HEIC/SVG vì Pillow không mở được các định dạng này → tự nhiên bị từ
  chối (BR-DM-10) mà không cần danh sách đuôi file.
- **Thư viện kho ảnh:** `google-cloud-storage` — import **bên trong hàm** (`storage.py`) nên
  máy dev/CI không cần cài để chạy `manage.py test` (A1-AC6). `ITEM_IMAGE_STORAGE` mặc định
  `local` — dev/test ghi vào `MEDIA_ROOT`, không gọi mạng.
  Test kho ảnh lỗi (A2-AC11/503) mock trực tiếp `LocalItemImageStorage.save` hoặc dùng
  `FakeStorage` (dependency injection qua tham số `storage=` của service).
- **AuditLog:** dùng `apps.common.audit.record_audit` sẵn có, `obj=item` (không phải
  `ItemImage`) — vì AuditLog gắn với mặt hàng dễ tra cứu hơn gắn với bản ghi ảnh (bản ghi ảnh
  bị ghi đè khi thay ảnh, id ảnh cũ chỉ còn trong `changes`).
- **`uploaded_by` hiển thị tên:** tái dùng `StaffProfile.display_name` (mẫu có sẵn ở
  `apps.accounts.auth.services.describe_user`), fallback về username.

### Việc còn nợ / giả định
- **A1 hạ tầng thật (bucket GCS, IAM, budget billing):** ghi lệnh `gcloud` vào
  `doc/ops/moi-truong.md`, **chưa chạy** — theo đúng yêu cầu "không gcloud/không deploy".
  `ITEM_IMAGE_BUCKET`/`ITEM_IMAGE_PUBLIC_BASE_URL` production/staging chưa được đặt trên
  Cloud Run; `ITEM_IMAGE_STORAGE` vẫn `local` mặc định cho tới khi bucket tồn tại.
- **A2 phần FE console** (màn Danh mục, nút Tải/Thay/Gỡ, thông báo lỗi mạng AC12, dòng nhắc
  BR-DM-15): không thuộc phạm vi BE lô này.
- **A3 (gỡ ảnh)** đã làm đủ luôn (rẻ, dùng chung endpoint `DELETE`) dù lô 1 chỉ yêu cầu ưu
  tiên A1/A2/A4 — mọi AC A3-AC1..AC6 đã có test xanh.
- **A4 phần FE** (lưới/trang chi tiết Shop, khung mặc định, nhãn "Ảnh minh hoạ", mock 3 trạng
  thái): không thuộc phạm vi BE.
- **A5** (ảnh thu nhỏ giỏ/checkout): không làm, thuộc FE lô 2.
- **Django Admin (A2-AC18):** chỉ preview readonly (ảnh + alt + nhãn minh hoạ), chưa hiện
  cảnh báo LOW_RESOLUTION hay ngày tải — không bắt buộc theo AC, để đơn giản.
- **`ITEM_IMAGE_SIZE_BUDGET` (60 KB/15 KB, Q7):** hard-code trong `processing.py`
  (`SIZE_BUDGET_BYTES`), không đưa vào env vì 02-stories.md chỉ liệt kê `ITEM_IMAGE_SIZES`
  (số px) là tham số cấu hình được — dung lượng chỉ là mức nén kỹ thuật để đạt mục tiêu đó.
- **Dọn ảnh cũ sau 30 ngày (BR-DM-14):** ngoài phạm vi (đã ghi ở 02-stories.md "Để sau").

### Sửa lỗi QA lô 1 (04-qa-report.md, 2026-09-27)
- **B2 — `uploaded_at`/`uploaded_by` không phản ánh lần thay gần nhất.**
  `apps/catalog/images/serializers.py::serialize_item_image` dùng `image.created_at`
  (thời điểm TẠO, không đổi khi thay ảnh) thay vì `image.updated_at` (auto_now, được ghi lại
  mỗi lần thay — `services.upload_item_image` đã liệt kê `"updated_at"` trong
  `update_fields` từ trước). `uploaded_by` vốn đã đúng ở tầng service (`current.uploaded_by =
  actor` khi thay ảnh) — kiểm lại và xác nhận không có lỗi ở đây, chỉ `uploaded_at` sai.
  Sửa: đổi sang `image.updated_at`.
- **B3 — `uploaded_at` xuất theo UTC (`+00:00`) thay vì giờ VN (`+07:00`, contract
  02-stories.md).** DB lưu UTC (`USE_TZ=True`); gọi `.isoformat()` trực tiếp trên datetime
  aware trả về tzinfo UTC. Sửa: bọc qua `django.utils.timezone.localtime(...)` (dùng
  `TIME_ZONE=Asia/Ho_Chi_Minh` đã cấu hình sẵn) trước khi `.isoformat()`.
- **TDD:** thêm 2 test RED trước khi sửa ở
  `apps/catalog/images/tests/test_api.py::UploadItemImageApiTests`:
  `test_b2_thay_anh_cap_nhat_uploaded_at_va_uploaded_by_theo_lan_gan_nhat` (so sánh NGHIÊM
  NGẶT `uploaded_at` giữa lần tạo và lần thay, cộng `uploaded_by` đổi đúng người) và
  `test_b3_uploaded_at_theo_gio_vn_offset_0700` (assert chuỗi kết thúc `"+07:00"`). Cả hai đỏ
  đúng lý do trước khi sửa `serializers.py`, xanh sau khi sửa.
- File đổi thêm cho fix này: `backend/apps/catalog/images/serializers.py` (sửa),
  `backend/apps/catalog/images/tests/test_api.py` (2 test mới). Không đổi contract, không
  migration mới.

### Test
```
cd backend && .venv/bin/python manage.py test
→ Ran 634 tests in ~30s — OK (0 failure).
  (baseline trước lô 1: 582 → lô 1: 632 → sau fix B2/B3: 634, +2 test)
cd backend && .venv/bin/python manage.py makemigrations --check --dry-run
→ No changes detected
```
Không có thay đổi ở `adapter/` nên không chạy `pytest` ở đó.

## FE (lô 1: A2 màn Danh mục console, A4 ảnh Shop)

Làm song song với BE bằng mock (`NEXT_PUBLIC_USE_MOCK=1`). Đối chiếu lại contract thật ở mục
"Endpoint mới + JSON mẫu" phía trên sau khi BE xong — **khớp 100%, không có chỗ lệch** cần báo.

### erp-console — A2 (màn Danh mục tối thiểu)

**Mới**
- `erp-console/features/catalog/types.ts` — `CatalogItem`, `CatalogItemImage`,
  `UploadedItemImage`, `UploadImageResponse`, `UploadImageInput`, `ImageFilter`.
- `erp-console/features/catalog/api.ts` — `listItems(filter)` (`GET /api/catalog/items/`,
  `?has_image=`), `filterItems` (lọc tên/mã phía máy), `uploadItemImage(itemId, input)`
  (`POST /api/catalog/items/{id}/image/`, multipart).
- `erp-console/features/catalog/mock.ts` — seed 6 mặt hàng đủ 3 trạng thái ảnh (có ảnh/`null`/ảnh
  lỗi) theo đúng yêu cầu contract "FE dựng mock theo đây". Kiểm **thật** trên tệp đã chọn: đọc
  byte đầu để biết JPEG/PNG/WebP thật (bắt được `.txt` đổi đuôi `.jpg`, giống cách Pillow của BE
  từ chối định dạng lạ), đọc kích thước thật bằng `createImageBitmap` để phát cảnh báo
  `LOW_RESOLUTION` (< 600px, A2-AC6). Ảnh mẫu là SVG data URI **sinh lúc chạy** — không commit
  tệp ảnh (quy ước 2026-09-25). Mã thử lỗi qua tên tệp (`loi-luu-tru` → 503, `mat-mang` → rớt
  mạng status 0) và qua alt text (`TEST_CONFLICT` → 409) — ghi rõ trong comment đầu file.
- `erp-console/features/catalog/messages.ts` — chuỗi UI riêng màn Danh mục.
- `erp-console/features/catalog/catalog.module.css` — danh sách hàng thoáng kiểu Nhân sự/Kho +
  tấm tải ảnh.
- `erp-console/features/catalog/components/ItemThumb.tsx` — ảnh thu nhỏ 44px, lỗi tải
  (`onError`) hoặc `null` → khung mặc định (icon Material Symbols `set_meal`, không phải tệp
  ảnh riêng).
- `erp-console/features/catalog/components/ImageUploadSheet.tsx` — tấm tải/thay ảnh: xem trước
  bằng blob URL của tệp vừa chọn, ô alt text, checkbox "Ảnh minh hoạ", dòng nhắc BR-DM-15 cố
  định, đủ trạng thái đang gửi/lỗi định dạng-dung lượng/503/rớt mạng (nút đổi thành "Thử lại",
  giữ nguyên tệp)/409 (nút "Tải lại" → đóng tấm + tải lại danh sách), chặn bấm đúp.
- `erp-console/features/catalog/components/CatalogScreen.tsx` — màn chính: bộ lọc "Tất cả /
  Chưa có ảnh" (`?has_image=false`, UC-A5), tìm kiếm, danh sách, nút Tải/Thay ảnh **chỉ hiện**
  khi `me.permissions` có `catalog.change_item_image` (A2-AC14), toast kết quả (gộp cảnh báo
  LOW_RESOLUTION nếu có).

**Sửa**
- `erp-console/shared/lib/http.ts` — `sendReal` nhận `body` là `FormData`: không tự gắn
  `Content-Type` (để trình duyệt gắn boundary), không `JSON.stringify`. Thay đổi additive, không
  ảnh hưởng các module JSON hiện có.
- `erp-console/shared/lib/nav.ts` — thêm `PERM.changeItemImage = "catalog.change_item_image"`.
- `erp-console/features/auth/mock.ts` — thêm `catalog.change_item_image` vào `GROUP_PERMS.chu`
  và `GROUP_PERMS.quan_ly` (khớp data migration BE `0006_grant_change_item_image`), **không**
  thêm cho `nv_kho`/`nv_giao`.
- `erp-console/shared/lib/beErrors.mock.ts` — thêm nhóm lỗi
  `CATALOG_IMAGE_FORBIDDEN/BAD_FORMAT/TOO_LARGE/MISSING_FILE/ALT_TOO_LONG/CONFLICT/STORAGE_ERROR`,
  `CATALOG_ITEM_NOT_FOUND` — copy đúng `code`/`detail` trong contract A2.
- `erp-console/app/(console)/catalog/page.tsx` — thay `<Placeholder>` bằng `<CatalogScreen>`
  (vẫn bọc `<ViewGuard view="catalog">`, cần `catalog.view_item`).

**Chưa làm (ngoài phạm vi lô này theo brief)**: nút "Gỡ ảnh" (A3) — dù BE đã xong endpoint
`DELETE …/image/`, phần console gọi nó thuộc lô 2 theo 02-stories.md. A5 (ảnh trong giỏ/checkout
console — không áp dụng, console không có giỏ hàng).

### frontend/ (Shop) — A4

**Mới**
- `frontend/components/ItemImageFrame.tsx` — ảnh mặt hàng dùng chung cho lưới (`size="card"`) và
  trang chi tiết (`size="detail"`). `image: null` hoặc ảnh lỗi (`onError`) → khung mặc định vẽ
  bằng **SVG nội tuyến trong component** (không phải tệp `<img>`), `role="img"` +
  `aria-label={tên mặt hàng}`, hiện kèm tên nhóm. `srcSet` chỉ gồm `thumb`+`card` ở lưới (không
  tải bản `detail`, A4-AC3) và `card`+`detail` ở trang chi tiết. `width`/`height` cố định +
  khung vuông CSS (`aspect-ratio: 1/1`) chống nhảy bố cục. `loading="lazy"` ở lưới,
  `loading="eager"` ở chi tiết (giá/tồn không chờ ảnh — A4-AC4). Nhãn "Ảnh minh hoạ" đè góc dưới
  trái khi `is_illustration`.

**Sửa**
- `frontend/lib/types.ts` — thêm `ItemImageUrls`, `ItemImage`; `CatalogItem` thêm field
  `image: ItemImage | null`.
- `frontend/lib/mock.ts` — mỗi mặt hàng mẫu có `image` khớp 1 trong 3 trạng thái: có ảnh (SVG
  data URI sinh lúc chạy, không commit tệp ảnh), `null`, ảnh lỗi (data URI không giải mã được —
  test khung mặc định mà không cần mạng thật, tránh phụ thuộc việc sandbox có internet hay
  không). Combo có ảnh riêng, combo còn lại `image: null` để thấy rõ **không** mượn ảnh thành
  phần (A4-AC8).
- `frontend/components/CatalogGrid.tsx` — thêm `<ItemImageFrame>` trong `<Link>` bọc ảnh
  (`aria-hidden` + `tabIndex={-1}` vì đã có `<Link>` tên mặt hàng trỏ cùng đích — tránh 2 điểm
  dừng Tab trùng nhau cho bàn phím/trình đọc màn hình).
- `frontend/app/shop/item/page.tsx` — thêm `<ItemImageFrame size="detail">` đầu thẻ chi tiết.
- `frontend/app/globals.css` — thêm `.item-image*`, `.item-card-media`, `.item-detail-card
  .item-image-detail`; dùng token màu sẵn có (`--color-bg`, `--color-muted`, `--color-border`),
  không thêm mã hex mới.
- `doc/BUILD-PLAN.md` — mục Shop API thêm field `image` cho 2 endpoint catalog.

### Đối chiếu contract
Không có chỗ lệch: response `GET /api/shop/catalog*` và `GET/POST /api/catalog/items*` BE làm
đúng như bảng "Endpoint mới + JSON mẫu" ở trên, khớp type/mock FE đã dựng trước đó.

### Kiểm đã chạy
```
cd erp-console && ./node_modules/.bin/tsc --noEmit && npm run build   # sạch
cd frontend && npx tsc --noEmit && npm run build                       # sạch
```
Chạy `NEXT_PUBLIC_USE_MOCK=1 npm run dev` cả 2 app, dùng Playwright (Python) chụp mobile 375px +
desktop 1280px, kiểm bằng tay các trạng thái: danh sách có/không quyền ảnh (tài khoản `loc` vs
`kho1`), lọc "Chưa có ảnh", xem trước ảnh đã chọn, tải thành công kèm cảnh báo LOW_RESOLUTION,
lỗi định dạng giả (`.txt` đổi đuôi `.jpg`), lỗi 503, rớt mạng (status 0, nút đổi "Thử lại"), xung
đột 409 (nút "Tải lại"), Shop hiện đúng ảnh/khung mặc định/nhãn minh hoạ ở cả lưới và chi tiết.
Ảnh chụp: `doc/features/2026-09-26-anh-mat-hang/shots/a2-*.png`,
`doc/features/2026-09-26-anh-mat-hang/shots/a4-*.png`. Tắt server dev sau khi xong (không còn
tiến trình `next dev` chạy nền).

### Việc còn nợ FE
- **A3 console (nút "Gỡ ảnh")** — BE đã xong `DELETE`, FE để lô 2 theo đúng phạm vi được giao.
- **A5 (ảnh thu nhỏ giỏ/checkout Shop)** — Could, chưa làm (ngoài brief lô 1).
- **Tên nhóm hàng ở console**: contract A2 chỉ trả `item_group` là ID số (không có tên) — màn
  Danh mục hiện tạm "Nhóm #<id>". Cần BE bổ sung tên nhóm (hoặc endpoint `item-groups`) khi làm
  S38 (sửa tên/nhóm/hạn dùng/ẩn-hiện).
- **Chưa chạy thử với BE thật** (BE báo đã xong 632 test xanh) — FE mới kiểm bằng mock; nên chạy
  lại `NEXT_PUBLIC_USE_MOCK=0` trỏ vào `cangca-api` cục bộ trước khi QA để chắc chắn kiểu dữ liệu
  thật (đặc biệt `uploaded_at` ISO có timezone, `image.id` dạng `img_xxxxxxxx`) khớp UI.

## FE — sửa B1 (QA REJECTED lô 1, 04-qa-report.md) · 2026-09-27

**Lỗi gốc:** `erp-console/features/catalog/api.ts` khai `listItems(): Promise<CatalogItem[]>` và đọc
thẳng response, nhưng `GET /api/catalog/items/` dùng `DEFAULT_PAGINATION_CLASS` toàn cục của BE nên
trả `{count,next,previous,results}`. `mockListItems` cũ cũng trả mảng trần nên FE "khớp contract"
khi tự kiểm bằng mock nhưng sập ngay khi nối BE thật, với **mọi vai trò** — đúng như QA tái hiện.

### Sửa
- `erp-console/shared/lib/usePagedList.ts` — **chuyển** từ `features/orders/usePagedList.ts` lên
  `shared/lib/` (dùng chung được cho `catalog`, đúng luật `nextjs-shop-patterns`: "module không import
  vào ruột module khác"). `features/orders/useOrderList.ts`,
  `features/orders/components/{PaymentQueueScreen,RefundQueueScreen}.tsx` đổi import sang đường dẫn
  mới — hành vi Đơn & tiền / hàng chờ thanh toán / phiếu hoàn không đổi.
- `erp-console/features/catalog/api.ts` — `listItems(filter, page)` giờ trả
  `Promise<Paginated<CatalogItem>>` (giống `features/orders/api.ts`), `?has_image=` **và** `?page=`
  đều lọc/phân trang **phía server**.
- `erp-console/features/catalog/useCatalogList.ts` (mới) — bọc `usePagedList<CatalogItem, ImageFilter>`,
  giống `useOrderList.ts`.
- `erp-console/features/catalog/mock.ts` — `mockListItems` trả đúng hình dạng phân trang thật
  (`{count,next,previous,results}`, `PAGE_SIZE=4` **cố ý nhỏ** để "Tải thêm" luyện được ngay cả với
  seed 6 mặt hàng) — để lỗi hình dạng như B1 không lọt qua lần kiểm mock nữa.
- `erp-console/features/catalog/components/CatalogScreen.tsx` — thay `useResource` bằng
  `useCatalogList`; thêm khối "Tải thêm" (giống Đơn & tiền) khi `hasMore`; tìm kiếm phía máy chỉ áp
  dụng trên các trang **đã tải** (ghi rõ trong UI khi không khớp mà còn trang sau); tải ảnh thành công
  giờ `list.patch(item.id, {image})` sửa đúng dòng tại chỗ thay vì tải lại cả trang.
- `erp-console/app/(console)/error.tsx` (mới) — error boundary tối thiểu cho route `(console)`, theo
  gợi ý QA. Đặt cùng thư mục với `layout.tsx` (`ConsoleGate`/Shell) nên khi MỘT màn lỗi, menu/topbar
  vẫn dùng được, chỉ vùng nội dung hiện "Màn này gặp lỗi" + nút "Thử lại" (`reset()`).
- **Tiện thể sửa gap đã ghi ở lần trước:** BE thật trả kèm `group_name` (không chỉ `item_group` ID
  như mẫu JSON rút gọn của 02-stories.md) — `CatalogItem.group_name` thêm vào `types.ts`, `mock.ts`
  seed đủ field, `CatalogScreen.tsx` hiện tên nhóm thật thay vì "Nhóm #<id>".

### Kiểm bằng BE thật (đúng hướng dẫn `erp-console/e2e/a2_catalog_real.py`)
Dựng DB QA tạm (`/tmp/qa_b1.sqlite3`, `ITEM_IMAGE_STORAGE=local`), `migrate` +
`bootstrap_masterdata` + `seed_demo` (6 mặt hàng, không ảnh) + script `manage.py shell` tạo 3 tài
khoản `loc`(chu)/`quanly1`(quan_ly)/`kho1`(nv_kho), `must_change_password=False`. Chạy
`manage.py runserver 127.0.0.1:8000` và `erp-console` với
`NEXT_PUBLIC_API_BASE=http://localhost:8000 NEXT_PUBLIC_USE_MOCK=0 npm run dev -- -p 3100`.
```
cd erp-console && BASE=http://localhost:3100 API=http://localhost:8000 python3 e2e/a2_catalog_real.py
→ 6/6 pass (trước khi sửa: 0/3 tài khoản qua, đúng như QA mô tả)
```
Xác nhận thêm bằng tay: `?has_image=false` trả đúng 5/6 sau khi tải ảnh cho 1 mặt hàng qua UI thật
(không mock) — nút đổi "Tải ảnh"→"Thay ảnh" ngay, toast hiện, không tải lại trang. `curl` trực tiếp
API xác nhận response thật đúng hình `{count,next,previous,results}`.
Ảnh: `shots/qa-fix-a2-catalog-real-be-mobile.png` (6/6 mặt hàng, cột "Hải sản" = `group_name` thật),
`shots/qa-fix-a2-upload-real-be-success-mobile.png` (upload ảnh thật qua BE thật thành công).
Ảnh mock "Tải thêm": `shots/qa-fix-a2-mock-loadmore-before.png` (4/6) →
`shots/qa-fix-a2-mock-loadmore-after.png` (6/6, không trùng dòng).
Đã tắt hết `runserver`/`next dev`, xoá `/tmp/qa_b1.sqlite3` và `backend/media/` (thư mục test cục
bộ, đã có trong `.gitignore`) sau khi xong — không còn tiến trình nào chạy nền, `git status` sạch.

### Ghi nhận thêm (không sửa — ngoài phạm vi frontend/erp-console)
- **Ảnh không tải được khi chạy BE local `ITEM_IMAGE_STORAGE=local`:** `ITEM_IMAGE_PUBLIC_BASE_URL`
  mặc định tính ra `http://localhost:8000/media/item-images` (`backend/config/settings.py:151`),
  nhưng `LocalItemImageStorage` lưu file ở `MEDIA_ROOT/items/...` (thiếu tiền tố `item-images/`) —
  **và** `config/urls.py` không có route phục vụ `MEDIA_ROOT` nên `/media/...` luôn `404` dù đúng
  đường dẫn. Đây là lý do QA phải tự dựng `python -m http.server` để thử ảnh khi kiểm B1 lô 1. Ảnh
  chụp `qa-fix-a2-upload-real-be-success-mobile.png` cho thấy FE xử lý đúng: ảnh 404 →
  `ItemThumb`/`ItemImageFrame` tự chuyển sang khung mặc định (không vỡ, không crash) — hành vi ĐÚNG
  theo A2/A4, chỉ là môi trường dev cục bộ chưa phục vụ được ảnh thật. Không sửa vì thuộc `backend/`
  — BE nên cân nhắc thêm route `static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)` khi
  `DEBUG`/`ITEM_IMAGE_STORAGE=local`, và bỏ tiền tố `item-images` lệch giữa settings mặc định và
  storage thật (hoặc đổi storage ghi đúng theo tiền tố đó).

### Kiểm tra cuối
```
cd erp-console && ./node_modules/.bin/tsc --noEmit && npm run build   # sạch (đã build lại sau mọi sửa)
cd frontend && npx tsc --noEmit && npm run build                       # sạch (không đổi gì thêm ở Shop)
```

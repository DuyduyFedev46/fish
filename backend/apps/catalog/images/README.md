# catalog/images — Ảnh mặt hàng (A1/A2/A3/A4, BR-DM-09..16)

Mỗi mặt hàng đúng **1 ảnh** (Q2, model `ItemImage` 1-1 với `Item`, `related_name="image"`).
Không phải chứng từ (BR-PQ-10 không áp dụng) — thay/gỡ chỉ đổi bản ghi, KHÔNG xoá object
cũ ở kho ảnh (BR-DM-14).

| File | Làm gì |
|---|---|
| `processing.py` | Pillow: kiểm định dạng thật (JPEG/PNG/WebP, cấm SVG/GIF/PDF/HEIC), gỡ EXIF/GPS (xoay đúng chiều trước), cắt vuông 1:1 giữa, xuất 3 cỡ WebP, không phóng to |
| `storage.py` | Trừu tượng hoá kho ảnh: `local` (dev/test, ghi `MEDIA_ROOT`) / `gcs` (staging/prod, `google-cloud-storage`, import trong hàm) qua `ITEM_IMAGE_STORAGE` |
| `services.py` | `upload_item_image` (thêm/thay, A2), `remove_item_image` (gỡ, A3): validate, khoá lạc quan `expected_image_id`, AuditLog |
| `serializers.py` | Dựng JSON ảnh cho 3 nơi: response upload (đủ field), console list/detail (bỏ `uploaded_by`), Shop (chỉ `alt`/`is_illustration`/`urls`) |
| `api.py` | `ItemImageDetailView`: `POST`/`DELETE /api/catalog/items/{id}/image/`, quyền `catalog.change_item_image` |

## Quyền (Q3, Tầng 2)
`catalog.change_item_image` khai ở `Item.Meta.permissions`, gán cho `owner` + `manager`
bằng data migration `apps/accounts/migrations/0006_grant_change_item_image.py` (theo mẫu
`0003_grant_view_dashboard.py`). KHÔNG mở `change_item` — Quản lý vẫn 403 khi sửa tên,
hạn dùng, ẩn/hiện, giá qua endpoint khác (spec §1.4). `warehouse_staff`/`delivery_staff` chỉ xem
(`catalog.view_item`, đã có).

## Cấu hình (env, không hard-code)
`ITEM_IMAGE_STORAGE` (`local` mặc định dev/test | `gcs`), `ITEM_IMAGE_BUCKET`,
`ITEM_IMAGE_PUBLIC_BASE_URL` (mặc định suy ra từ bucket khi `gcs`), `ITEM_IMAGE_MAX_BYTES`
(mặc định 10 485 760), `ITEM_IMAGE_MIN_SIDE_WARN` (mặc định 600),
`ITEM_IMAGE_SIZE_THUMB/CARD/DETAIL` (mặc định 160/480/1200). Xem `doc/ops/moi-truong.md`
cho tên bucket production/staging và lệnh `gcloud` tạo bucket + IAM (BE ghi, chưa chạy —
chỉ chạy khi Duy duyệt deploy).

## Test
`tests/factories.py` sinh ảnh BẰNG CODE lúc chạy test (Pillow) — không commit tệp ảnh
(quy ước 2026-09-25, BR-DM-16). `tests/test_processing.py` (xử lý ảnh, không đụng DB),
`tests/test_services.py` (nghiệp vụ, `FakeStorage` giả lập kho ảnh kể cả lỗi ghi),
`tests/test_api.py` (contract HTTP, phân quyền 401/403/`BR-PQ-12`, khoá lạc quan 409,
không rò giá vốn).

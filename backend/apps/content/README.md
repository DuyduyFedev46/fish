# P-11 Nội dung & CMS (apps.content)

App quản lý nội dung: bài viết hướng dẫn nấu ăn, tin mùa vụ, và các trang chính sách bắt buộc go-live.

## Module
- `categories/`: Chuyên mục bài viết (tạo, sắp xếp, ngừng dùng BR-ND-02, BR-ND-04)
- `entries/`: Bài viết và Trang nội dung (bản đang soạn, vòng đời CMS-03..CMS-12)
- `images/`: Quản lý ảnh bài viết (giữ tỉ lệ, tối đa 20 ảnh/bài BR-ND-07)
- `body/`: Xử lý thân bài (chuẩn hoá danh sách trắng chống XSS hai lớp, cảnh báo SĐT/giá vốn, sinh slug tiếng Việt)
- `public/`: API công khai cho khách đọc bài (AllowAny, GET-only, có throttle, không rò giá vốn và PII)

## Quyền
- ND-01: `content.view_entry`, `content.add_entry`, `content.change_entry`, `content.delete_entry`, `content.view_category`
- ND-02: `content.publish_entry`
- ND-03: `content.add_category`, `content.change_category`
Gán cho `owner` và `manager`; `warehouse_staff` và `delivery_staff` không có quyền.

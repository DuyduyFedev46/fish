# address_search — Tìm địa chỉ trên Shop qua máy chủ Cá Về

```mermaid
flowchart TD
  A["Khách gõ ít nhất 2 chữ ở hộp tìm địa chỉ"] --> B{"Máy chủ đã có khoá VietMap?"}
  B -- "chưa" --> C["Trả báo bận 503, khách gõ địa chỉ trực tiếp"]
  B -- "có" --> D["Máy chủ hỏi gợi ý VietMap, không lưu và không ghi nhật ký chữ gõ"]
  D -- "VietMap lỗi hoặc quá giờ" --> C
  D -- "thành công" --> E["Trả tối đa 6 gợi ý gồm mã, tiêu đề, dòng phụ"]
  E --> F["Khách chọn một gợi ý"]
  F --> G["Máy chủ lấy chi tiết địa điểm, bỏ toạ độ"]
  G --> H{"Tên tỉnh và phường khớp đúng một dòng danh mục?"}
  H -- "khớp" --> I["Trả số nhà tên đường kèm gợi ý phường"]
  H -- "không khớp hoặc trùng tên" --> J["Trả số nhà tên đường, gợi ý rỗng để khách tự chọn phường"]
```

Module thực hiện phương án A của `02b-tech-design.md` §1.9b (story `SHOP-3-04`, bất biến 9):

- `vietmap.py`: gọi `autocomplete/v4` và `place/v4` của VietMap bằng `urllib` trong thư viện chuẩn với host/đường dẫn cố định, bỏ hoàn toàn toạ độ (`lat`, `lng`) và mã riêng VietMap, chỉ ghi nhật ký mã trạng thái khi lỗi.
- `matching.py`: đối chiếu tên tỉnh, quận/huyện (`legacy`), phường/xã từ VietMap sang mã danh mục tĩnh `administrative_units` bằng `fold_text`; chỉ gợi ý khi khớp duy nhất 1 đơn vị.
- `shop_api.py`: hai endpoint công khai chỉ nhận `POST` thân JSON (`/api/shop/address-search/`, `/api/shop/address-place/`), giới hạn tần suất `shop_address_search` theo IP.

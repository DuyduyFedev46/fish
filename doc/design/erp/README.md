# Thiết kế ERP máy tính (đã duyệt 01/10/2026)

- Canvas gốc: https://claude.ai/code/artifact/ab9d37bb-9aba-449b-a71f-bccf97ca1f26 (bản xem trực quan, có tương tác).
- `screens/*.dc.html`: HTML tĩnh, style inline. Mở bằng trình duyệt để xem (icon/font cần mạng; thẻ `<sc-if>`/`{{…}}` là cú pháp canvas, bỏ qua). Dev đọc cấu trúc, khoảng cách, màu, chữ từ HTML.
- **Luật bắt buộc: `UI-RULES.md`.** Trạng thái/enum: `enum-map.md`.
- Popup (`ERP-F*` có lớp phủ) = màn cha + hộp thoại ở cuối file. Form trang = trang riêng có thanh nút dưới.
- Dữ liệu trên thiết kế là dữ liệu giả. Số điện thoại vẽ dạng che `…0273`, nhưng khi code thì **hiển thị đủ** cho người có quyền (UI-RULES §1.8).
- Mã lô trên thiết kế (`L0914-CT01`) là mẫu rút gọn; code dùng định dạng thật `<mã hàng>-<yymmdd>-<5 HEX>`. Mã khác đã theo code.

## Danh mục màn (theo nghiệp vụ, mỗi hàng một đối tượng: danh sách → chi tiết → form → popup)

### 2 · ERP · Vào hệ thống
**Đăng nhập & tổng quan**

| File | Màn | Loại |
|---|---|---|
| `ERP-W4f-Dang-nhap.dc.html` | Đăng nhập (máy tính) | Màn |
| `ERP-W4g-Dat-mat-khau.dc.html` | Đặt mật khẩu mới (máy tính) | Màn |
| `ERP-W4h-Khong-co-quyen.dc.html` | Không có quyền (máy tính) | Màn |
| `ERP-D1-Tong-quan.dc.html` | Tổng quan (máy tính) | Màn |

### 3 · ERP · Hàng hoá & kho
**Phiếu nhập: danh sách → chi tiết → nhập lô → hoá đơn → chi phí phụ**

| File | Màn | Loại |
|---|---|---|
| `ERP-W2a-Mua-hang.dc.html` | Mua hàng (máy tính) | Màn |
| `ERP-W2b-Chi-tiet-phieu-nhap.dc.html` | Chi tiết phiếu nhập (máy tính) | Màn |
| `ERP-F1a-Nhap-lo-tai-cang.dc.html` | Form · Nhập lô tại cảng | Form trang |
| `ERP-F1c-Them-hoa-don-mua.dc.html` | Form · Thêm hoá đơn mua | Popup |
| `ERP-F1d-Them-chi-phi-phu.dc.html` | Form · Thêm chi phí phụ | Form trang |

**Nhà cung cấp**

| File | Màn | Loại |
|---|---|---|
| `ERP-W5c-Nha-cung-cap.dc.html` | Nhà cung cấp | Màn |
| `ERP-W5d-Chi-tiet-nha-cung-cap.dc.html` | Chi tiết nhà cung cấp | Màn |
| `ERP-F1b-Them-nha-cung-cap.dc.html` | Form · Thêm nhà cung cấp | Popup |

**Lô & tồn kho**

| File | Màn | Loại |
|---|---|---|
| `ERP-D3-Kho-lo.dc.html` | Kho & lô (máy tính) | Màn |
| `ERP-W2f-Chi-tiet-lo.dc.html` | Chi tiết lô | Màn |
| `ERP-F1e-Mo-ban-lo.dc.html` | Form · Mở bán lô | Popup |
| `ERP-F1g-Tra-nha-cung-cap.dc.html` | Form · Trả nhà cung cấp | Popup |
| `ERP-F1h-Huy-phan-ton.dc.html` | Form · Huỷ phần tồn, ghi lỗ | Popup |
| `ERP-F1i-Chot-lo.dc.html` | Form · Chốt lô | Popup |
| `ERP-W5k-Dieu-chinh-ton.dc.html` | Điều chỉnh tồn (máy tính) | Màn |
| `ERP-F1j-Dieu-chinh-ton.dc.html` | Form · Điều chỉnh tồn | Popup |
| `ERP-W5l-Kho.dc.html` | Kho (máy tính) | Màn |
| `ERP-F3m-Them-kho.dc.html` | Form · Thêm kho | Popup |

**Hàng hoàn về kho**

| File | Màn | Loại |
|---|---|---|
| `ERP-W5e-Hang-hoan-ve-kho.dc.html` | Hàng hoàn về kho | Màn |
| `ERP-W5f-Chi-tiet-hang-hoan.dc.html` | Chi tiết hàng hoàn | Màn |
| `ERP-F2m-Nhap-hang-hoan-ve-kho.dc.html` | Form · Nhập hàng hoàn về kho | Popup |
| `ERP-F2n-Duyet-hang-hoan.dc.html` | Form · Duyệt hàng hoàn | Popup |

**Kiểm kê**

| File | Màn | Loại |
|---|---|---|
| `ERP-W2c-Kiem-ke.dc.html` | Kiểm kê (máy tính) | Màn |
| `ERP-W2g-Chi-tiet-kiem-ke.dc.html` | Chi tiết phiếu kiểm kê | Màn |
| `ERP-F1f-Nhap-so-kiem-ke.dc.html` | Form · Nhập số kiểm kê | Form trang |

**Sổ nhập xuất**

| File | Màn | Loại |
|---|---|---|
| `ERP-W5i-So-nhap-xuat.dc.html` | Sổ nhập xuất (máy tính) | Màn |

**Mặt hàng, giá & ưu đãi**

| File | Màn | Loại |
|---|---|---|
| `ERP-W2d-Danh-muc-gia.dc.html` | Danh mục & giá (máy tính) | Màn |
| `ERP-W2h-Chi-tiet-mat-hang.dc.html` | Chi tiết mặt hàng | Màn |
| `ERP-F1k-Them-mat-hang.dc.html` | Form · Thêm mặt hàng | Form trang |
| `ERP-F1n-Anh-mat-hang.dc.html` | Form · Ảnh mặt hàng | Popup |
| `ERP-W5o-Bang-gia.dc.html` | Bảng giá (máy tính) | Màn |
| `ERP-F1l-Dat-gia-moi.dc.html` | Form · Đặt giá mới | Popup |
| `ERP-W5h-Uu-dai.dc.html` | Ưu đãi (máy tính) | Màn |
| `ERP-F1m-Tao-uu-dai.dc.html` | Form · Tạo ưu đãi giảm giá | Form trang |
| `ERP-W5m-Nhom-hang.dc.html` | Nhóm hàng (máy tính) | Màn |
| `ERP-F1o-Them-nhom-hang.dc.html` | Form · Thêm nhóm hàng | Popup |

### 4 · ERP · Bán hàng
**Đơn hàng: danh sách → chi tiết → thao tác**

| File | Màn | Loại |
|---|---|---|
| `ERP-D2-Don-tien.dc.html` | Đơn & tiền (máy tính) | Màn |
| `ERP-D2b-Chi-tiet-don.dc.html` | Chi tiết đơn (máy tính) | Màn |
| `ERP-D2c-Thao-tac-theo-trang-thai.dc.html` | Thao tác theo trạng thái đơn | Màn |
| `ERP-F2a-Xac-nhan-da-nhan-tien.dc.html` | Form · Xác nhận đã nhận tiền | Popup |
| `ERP-F2b-Huy-don.dc.html` | Form · Huỷ đơn | Popup |
| `ERP-F2c-Lap-phieu-hoan.dc.html` | Form · Lập phiếu hoàn | Popup |
| `ERP-F2e-Xac-nhan-don-du-tien.dc.html` | Form · Xác nhận đơn đã đủ tiền | Popup |

**Khách hàng**

| File | Màn | Loại |
|---|---|---|
| `ERP-W5a-Khach-hang.dc.html` | Khách hàng | Màn |
| `ERP-W5b-Chi-tiet-khach-hang.dc.html` | Chi tiết khách hàng | Màn |

**Gọi xác nhận**

| File | Màn | Loại |
|---|---|---|
| `ERP-W1c-Goi-xac-nhan.dc.html` | Gọi xác nhận | Màn |
| `ERP-W1c2-Chi-tiet-goi-xac-nhan.dc.html` | Chi tiết gọi xác nhận | Màn |
| `ERP-F2h-Ghi-ket-qua-goi.dc.html` | Form · Ghi kết quả gọi xác nhận | Popup |
| `ERP-F2i-Hen-goi-lai.dc.html` | Form · Hẹn gọi lại | Popup |
| `ERP-F2j-Doi-nguoi-nhan-dia-chi.dc.html` | Form · Đổi người nhận / địa chỉ | Popup |
| `ERP-F2k-Quyet-dinh-don-chua-xac-nhan.dc.html` | Form · Quyết định đơn chưa xác nhận được | Popup |

**Khoản tiền chờ xử lý**

| File | Màn | Loại |
|---|---|---|
| `ERP-W1a-Hang-cho-thanh-toan.dc.html` | Hàng chờ thanh toán | Màn |
| `ERP-W1a2-Chi-tiet-khoan-tien.dc.html` | Chi tiết khoản tiền | Màn |
| `ERP-F2d-Gan-khoan-tien-vao-don.dc.html` | Form · Gắn khoản tiền vào đơn | Popup |

**Phiếu hoàn**

| File | Màn | Loại |
|---|---|---|
| `ERP-W1b-Phieu-hoan.dc.html` | Phiếu hoàn chờ chuyển | Màn |
| `ERP-W1b2-Chi-tiet-phieu-hoan.dc.html` | Chi tiết phiếu hoàn | Màn |
| `ERP-F2f-Xac-nhan-da-hoan-tien.dc.html` | Form · Xác nhận đã hoàn tiền | Popup |
| `ERP-F2g-Bao-chuyen-that-bai.dc.html` | Form · Báo chuyển thất bại | Popup |

### 5 · ERP · Giao hàng
**Phiếu giao**

| File | Màn | Loại |
|---|---|---|
| `ERP-W1d-Giao-hang.dc.html` | Giao hàng | Màn |
| `ERP-W1d2-Chi-tiet-phieu-giao.dc.html` | Chi tiết phiếu giao | Màn |
| `ERP-F2o-Giao-cho-nguoi-giao.dc.html` | Form · Giao cho người giao | Popup |
| `ERP-W2e-In-tem.dc.html` | In tem giao hàng (máy tính) | Màn |

**Việc giao của tôi**

| File | Màn | Loại |
|---|---|---|
| `ERP-W1e-Viec-giao-cua-toi.dc.html` | Việc giao của tôi | Màn |
| `ERP-F2l-Bao-giao-that-bai.dc.html` | Form · Báo giao thất bại | Popup |

### 6 · ERP · Kế toán
**Báo cáo & hoá đơn**

| File | Màn | Loại |
|---|---|---|
| `ERP-W3a-Bao-cao-lai-lo.dc.html` | Báo cáo lãi lỗ | Màn |
| `ERP-W5j-Hoa-don-ban.dc.html` | Hoá đơn bán (máy tính) | Màn |
| `ERP-W5g-Hoa-don-mua.dc.html` | Hoá đơn mua | Màn |
| `ERP-W5g2-Chi-phi-phu.dc.html` | Chi phí phụ | Màn |

### 7 · ERP · Website
**Bài viết**

| File | Màn | Loại |
|---|---|---|
| `ERP-W3b-Noi-dung.dc.html` | Nội dung | Màn |
| `ERP-W3c-Viet-bai.dc.html` | Viết bài | Màn |
| `ERP-F3l-Thiet-lap-bai-viet.dc.html` | Form · Thiết lập bài viết | Form trang |
| `ERP-F3i-Tra-ve-nhap.dc.html` | Form · Trả về nháp | Popup |
| `ERP-F3j-Go-bai.dc.html` | Form · Gỡ bài | Popup |
| `ERP-F3k-Kiem-tra-truoc-khi-dang.dc.html` | Form · Kiểm tra trước khi đăng | Popup |

**Chuyên mục**

| File | Màn | Loại |
|---|---|---|
| `ERP-W3d-Chuyen-muc.dc.html` | Chuyên mục | Màn |
| `ERP-F3h-Them-chuyen-muc.dc.html` | Form · Thêm chuyên mục | Popup |

### 8 · ERP · Quản trị
**Nhân viên**

| File | Màn | Loại |
|---|---|---|
| `ERP-W3e-Nhan-su.dc.html` | Nhân sự | Màn |
| `ERP-W3g-Chi-tiet-nhan-vien.dc.html` | Chi tiết nhân viên | Màn |
| `ERP-F3a-Them-nhan-vien.dc.html` | Form · Thêm nhân viên | Popup |
| `ERP-F3b-Tao-tai-khoan-Chu.dc.html` | Form · Tạo tài khoản nhóm Chủ | Popup |
| `ERP-F3c-Sua-ho-so-nhan-vien.dc.html` | Form · Sửa hồ sơ nhân viên | Popup |
| `ERP-F3d-Doi-nhom.dc.html` | Form · Đổi nhóm | Popup |
| `ERP-F3e-Dat-lai-mat-khau.dc.html` | Form · Đặt lại mật khẩu | Popup |
| `ERP-F3f-Cho-nghi-viec.dc.html` | Form · Cho nghỉ việc | Popup |

**Phân quyền & nhật ký**

| File | Màn | Loại |
|---|---|---|
| `ERP-W3h-Phan-quyen.dc.html` | Phân quyền | Màn |
| `ERP-W3i-Chi-tiet-nhom-quyen.dc.html` | Chi tiết nhóm quyền | Màn |
| `ERP-W3f-Nhat-ky-hoat-dong.dc.html` | Nhật ký hoạt động | Màn |

**AI**

| File | Màn | Loại |
|---|---|---|
| `ERP-W4c-Chinh-sach-AI.dc.html` | Chính sách AI (máy tính) | Màn |
| `ERP-W4d-Bao-cao-AI.dc.html` | Báo cáo AI cuối ngày (máy tính) | Màn |
| `ERP-W4b-AI-cua-toi.dc.html` | AI của tôi (máy tính) | Màn |

**Tài khoản của tôi**

| File | Màn | Loại |
|---|---|---|
| `ERP-W4e-Tai-khoan.dc.html` | Tài khoản của tôi (máy tính) | Màn |
| `ERP-F3g-Doi-mat-khau.dc.html` | Form · Đổi mật khẩu | Popup |

### 9 · ERP · Trạng thái trống, đang tải, lỗi, thông báo

| File | Màn | Loại |
|---|---|---|
| `ERP-W6a-Danh-sach-trong.dc.html` | Trạng thái · Danh sách trống | Trạng thái |
| `ERP-W6b-Tim-khong-thay.dc.html` | Trạng thái · Tìm không thấy | Trạng thái |
| `ERP-W6c-Dang-tai.dc.html` | Trạng thái · Đang tải | Trạng thái |
| `ERP-W6d-Mat-mang.dc.html` | Trạng thái · Mất mạng | Trạng thái |
| `ERP-W6e-Luu-that-bai.dc.html` | Trạng thái · Lưu thất bại | Trạng thái |
| `ERP-W6f-Xung-dot.dc.html` | Trạng thái · Xung đột khi sửa | Trạng thái |
| `ERP-W6g-404.dc.html` | Trạng thái · Không tìm thấy trang | Trạng thái |
| `ERP-W6h-Loi-chung.dc.html` | Trạng thái · Lỗi chung | Trạng thái |
| `ERP-W6i-Thong-bao.dc.html` | Trạng thái · Thông báo | Trạng thái |


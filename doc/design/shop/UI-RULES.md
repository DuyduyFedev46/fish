# Luật UI/UX Shop Cá Về (thiết kế 06/10/2026)

> Bắt buộc cho mọi màn Shop công khai (`frontend/`). Thiết kế mẫu nằm ở `screens/*.dc.html`.
> Khi code lệch luật này thì sửa code, không sửa luật. Muốn đổi luật thì hỏi Duy.
> Luật chung vẫn áp dụng: `DESIGN.md` (token), skill `caveve-ui`, bất biến 9 (dữ liệu cá nhân) trong skill `caveve-domain`.

## 1. Hiển thị hàng hoá
1. **Giá theo kg**: dòng giá ghi `278.000đ` rồi `/ kg`, số dùng `tabular-nums`. Combo ghi `/ combo`.
2. **Số lượng**: tối thiểu **1 kg**, bước **0,5 kg**. Combo tối thiểu 1 combo, bước 1. Nút "Thêm 1 kg" bấm xong đổi thành bộ tăng giảm.
   Bớt xuống dưới 1 kg thì mở popup xác nhận bỏ món, không tự xoá.
3. **Tồn kho** chỉ có 3 mức: Còn hàng (không cần nhãn) · **Sắp hết** (nhãn hổ phách trên ảnh) · **Hết hàng**.
   **Không bao giờ hiện số kg còn lại**, kể cả trong popup báo không đủ hàng.
4. **Hết hàng**: ảnh mờ, giá vẫn hiện, nút mua thay bằng **"Liên hệ chúng tôi"** (`tel:` hotline; ở trang chi tiết thêm "Nhắn Zalo"). Món hết luôn xếp cuối danh sách.
5. **Không hiện ngày nhập lô**, mã lô hay giá vốn.
6. Ảnh chưa có thì dùng khung xám kèm icon theo nhóm (cá, tôm, mực, cua, combo). Ảnh minh hoạ thì gắn nhãn "Ảnh minh hoạ".

## 2. Đơn hàng và thanh toán
1. Form đặt hàng chỉ gồm **Họ và tên · Số điện thoại · Địa chỉ giao hàng (một ô) · ô đồng ý chính sách quyền riêng tư**. Không có hoá đơn điện tử.
2. **Địa chỉ một ô**: một `<textarea>` 2 dòng. Bên phải có nút "Bản đồ" mở Google Maps để tìm, ghim rồi tự điền vào ô. Khách vẫn sửa tay được.
   Script Google Maps chỉ nạp khi khách bấm "Bản đồ". Không lưu toạ độ.
3. **Phí giao** không có trong hệ thống. Chỉ ghi "Phí giao: Báo khi xác nhận đơn".
4. **Giữ hàng 30 phút** bắt đầu khi bấm "Đặt hàng" (không phải khi thêm vào giỏ). Màn thanh toán có đồng hồ đếm ngược, dưới 5 phút thì chuyển màu hổ phách.
5. Thanh toán duy nhất là **chuyển khoản VietQR qua cổng SePay**. Thanh toán xong thì vào thẳng **trang đơn hàng** (cũng là trang tra cứu), trên cùng có banner "Thanh toán thành công".
6. **Không hiện chữ "hoàn tiền"** trên Shop. Đơn huỷ sau khi khách đã trả tiền ghi "Cá Về sẽ gọi cho bạn" kèm hotline.
7. Mã đơn hiển thị đúng định dạng code (`SO…`), font mono hoặc `tabular-nums`.

## 3. Dữ liệu cá nhân (bất biến 9)
1. Trang đơn hàng và trang tra cứu là **công khai**: **không hiện tên, số điện thoại, địa chỉ người nhận**.
2. Tra đơn bằng mã đơn + số điện thoại. Khi không tìm thấy thì báo chung "Không tìm thấy đơn khớp mã và số điện thoại.", **không nói ô nào sai**, không gắn `aria-invalid` cho từng ô.
3. Không có form liên hệ. Trang Liên hệ chỉ có hotline, Zalo, email, địa chỉ kinh doanh, giờ làm việc.
4. Không gắn analytics, pixel hay widget chat bên thứ ba khi Duy chưa duyệt. Google Maps là ngoại lệ đã duyệt.

## 4. Bố cục
1. **Bố cục bán lẻ kiểu Long Châu**:
   - header màu thương hiệu, ô tìm kiếm lớn;
   - menu nhóm hàng; banner; lưới icon nhóm;
   - các hàng sản phẩm có nút "Chọn mua".
   Màu và chữ vẫn theo token `DESIGN.md`.
2. **Mobile-first**: thiết kế ở 390 px, phải chạy ở 360 px mà không cuộn ngang. Bản máy tính 1280 px, nội dung nằm trong container `max-width: 1200px`.
3. **Header** (đặc tả từng link: `screens/HeaderFooter-*.dc.html`):
   - H1, header trang chủ: nền thương hiệu, logo, hotline, tra cứu đơn, giỏ có badge, ô tìm, chip tìm nhiều.
   - H2, khi cuộn hoặc ở trang danh mục: nền trắng, cao 56 px.
   - H3, trang con: nút quay lại, tiêu đề, giỏ.
   - H4, các bước đặt hàng: chỉ có nút quay lại và tiêu đề. Không logo, không giỏ, không menu.
   - Máy tính: header 2 tầng (H1); Giỏ, Đặt hàng, Thanh toán dùng header rút gọn.
4. **Badge giỏ là số món**, không phải tổng kg. Ẩn badge khi giỏ có 0 món.
5. **Thanh điều hướng đáy** (điện thoại) gồm Trang chủ · Danh mục · Giỏ hàng · Đơn hàng. Chỉ hiện ở Trang chủ, Danh mục, Góc bếp.
6. **Footer đầy đủ** (F1) gồm:
   - gọi và Zalo;
   - nhóm Mua hàng, nhóm Chính sách (5 link), nhóm Về Cá Về;
   - dải pháp lý (tên doanh nghiệp, MST, địa chỉ, giấy chứng nhận ĐKKD, logo Bộ Công Thương).
   Điện thoại hiện dạng nhóm thu gọn. Giỏ, Đặt hàng, Thanh toán dùng **footer rút gọn** (F2).

## 5. Popup
1. Điện thoại: **bottom sheet** (có thanh kéo) cho danh sách lựa chọn, **dialog giữa màn** cho xác nhận, **toast** (nền tối, `role="status"`) cho phản hồi nhanh.
2. Máy tính: mọi popup là **hộp thoại giữa màn** rộng 440–480 px, có nút X. Gợi ý tìm kiếm là dropdown dưới ô tìm.
3. Popup có `role="dialog" aria-modal="true"`, giữ tiêu điểm bên trong, đóng bằng Esc, trả tiêu điểm về nút đã mở nó. Lớp phủ `rgba(23,23,28,0.48)`.
4. Việc phá huỷ (bỏ món, huỷ đơn) dùng nút đỏ, có bước xác nhận.

## 6. Câu chữ
1. **Gọn**: mỗi màn chỉ có tiêu đề, **một câu cần thiết** và nút. Không dòng chú thích nhỏ giải thích, không mã luật, không chữ kỹ thuật.
2. Tiếng Việt đời thường, xưng "bạn". Nút là động từ rõ: "Thêm 1 kg", "Xem giỏ", "Đặt hàng", "Thanh toán lại", "Liên hệ chúng tôi".
3. Lỗi phải nói cách sửa: "Số điện thoại cần 10 chữ số, bắt đầu bằng 0", "Đơn chưa được tạo. Kiểm tra mạng rồi thử lại."
4. Không hứa điều hệ thống chưa làm, như "báo khi có hàng", "giao trong ngày", "miễn phí giao", "về cảng mỗi ngày".

## 7. Trạng thái bắt buộc
| Trạng thái | Cách hiện | Màn mẫu |
|---|---|---|
| Đang tải | khung xương, header và bộ lọc vẫn hiện, `aria-busy` | A8, DesktopLoading |
| Rỗng hoặc tìm không thấy | icon, tiêu đề, chip gợi ý, "Liên hệ chúng tôi" | A5, B4, DesktopNotFound |
| Mất mạng | "Chưa tải được hàng" kèm nút "Thử lại" | A6, DesktopOffline |
| Gửi lỗi | giữ nguyên dữ liệu đã nhập, popup "Thử lại", không tạo đơn trùng | C4 |
| Nhập sai | khối "Còn N chỗ cần sửa" có link nhảy tới ô, viền đỏ, một dòng lỗi dưới ô | C2 |
| Đổi giá hoặc hết hàng trong giỏ | banner hổ phách, giá cũ gạch ngang, món hết không tính vào tổng | B3 |

## 8. Truy cập và chuyển động
1. Vùng chạm ≥ 44 px. Ô nhập dùng font 16 px để iOS không tự phóng to. Có `:focus-visible` rõ ràng.
2. Nút chỉ có icon thì có `aria-label`, ghi rõ tên món nếu liên quan ("Thêm 0,5 kg Mực ống làm sạch").
3. Giỏ cập nhật thì đọc qua `aria-live="polite"`. Menu đang chọn có `aria-current`.
4. Tương phản đạt AA. Chuyển động 120–250 ms, ease-out. Tôn trọng `prefers-reduced-motion`. Không dùng `transition: all`.

## 9. Token
- Dùng token trong `DESIGN.md`, không hard-code mã màu hex trong component.
- Màu nhấn `#1F66D1`. Màu xanh đậm `#0E3A73` dùng cho banner và footer; **cần thêm token `brand-deep` vào `DESIGN.md` ở lô 1**.
- Font Inter (400/500/600). Bo góc: thẻ 10–12 px, nút 8 px hoặc tròn.

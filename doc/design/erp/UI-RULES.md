# Luật UI/UX ERP Cá Về (Duy chốt 30/09–01/10/2026)

> Bắt buộc cho mọi màn ERP máy tính. Thiết kế mẫu: `doc/design/erp/*.dc.html`. Enum & nhãn trạng thái: `enum-map.md`.
> Khi code lệch luật này → sửa code, không sửa luật. Muốn đổi luật → hỏi Duy.
> Phạm vi đã duyệt: **ERP máy tính** (1280–1440 px). Shop và ERP điện thoại chưa duyệt.

## 1. Dữ liệu hiển thị
1. **Mỗi ô / mỗi trường chỉ một giá trị.** Không ghi chú xám, dòng phụ, mô tả chồng dưới một thông tin khác.
   Thông tin phụ (lý do, ghi chú, số điện thoại, vai trò…) → **cột riêng** (bảng) hoặc **trường riêng** (trang chi tiết).
   Ngoại lệ duy nhất: dòng "Tiếp theo / Đã làm" trong khối thanh trạng thái.
2. **Chip trạng thái dùng một bộ nhãn chuẩn, không chú thích bên trong.** Ví dụ đơn tự huỷ hiện chip "Đã huỷ",
   cột "Lý do" ghi "Hết giờ giữ chỗ". Không "Tự huỷ (quá TTL)", không "Đang xử lý · Soạn hàng".
3. **Trạng thái và lựa chọn lấy theo enum database** (`enum-map.md`). Không bịa trạng thái DB không có.
   Ưu tiên nhãn FE đã có; nhãn trong code vi phạm luật §3 thì giữ nghĩa, dùng chữ thân thiện.
4. **Mã chứng từ đúng định dạng code**: đơn `SO<yymmdd>-<6 HEX>`, hoá đơn `INV…`, phiếu giao `GH-<mã hoá đơn>-<5 HEX>`;
   chứng từ không có số thì hiện `#<id>`. Mã dùng font mono.
5. **Thời gian luôn đủ ngày giờ** `dd/mm/yyyy hh:mm` (ví dụ `01/10/2026 09:32`). Không "hôm nay", "hôm qua", "5 phút trước".
   Đếm ngược (giữ chỗ) được phép, đặt ở cột/trường riêng.
6. **Số tiền, số kg**: `tabular-nums`, căn phải trong bảng; tiền có "đ", kg dùng dấu phẩy thập phân (`18,5 kg`).
7. **Giá vốn / lãi lỗ / tiền nhà cung cấp**: chỉ một **icon khoá nhỏ** cạnh nhãn hoặc giá trị. Không câu giải thích
   ("Giá vốn chỉ Chủ thấy"). Người không có quyền: ẩn hẳn cột/trường (backend vẫn là lớp chặn).
8. **Số điện thoại trong ERP hiển thị đủ** cho người có quyền xem. Màn Khách hàng chỉ hiện với quyền "Xem khách hàng"
   (mặc định Chủ + Quản lý, Chủ bật thêm được trong Phân quyền).

## 2. Bố cục khung
1. **Sidebar trái thu gọn được** (240 px ↔ 60 px chỉ icon, có tooltip). Menu theo nghiệp vụ, mục hiện theo quyền:
   - (không tiêu đề) Tổng quan
   - **Bán hàng**: Đơn & tiền · Khách hàng · Gọi xác nhận · Giao hàng · Việc giao của tôi
   - **Hàng hoá & kho**: Mua hàng · Nhà cung cấp · Kho & lô · Hàng hoàn về kho · Kiểm kê · Sổ nhập xuất · Danh mục & giá
   - **Kế toán**: Báo cáo lãi lỗ · Hoá đơn bán · Hoá đơn mua & chi phí
   - **Website**: Nội dung
   - **Quản trị**: Nhân sự · Phân quyền · Nhật ký hoạt động · Chính sách AI · Báo cáo AI
2. **Topbar**: tên màn bên trái; ô tìm (⌘K) + avatar bên phải. Bấm avatar → menu: Tài khoản của tôi · AI của tôi · Đăng xuất.
   **Không có nút "Làm mới"**, không nút đăng xuất rời.
3. Màn có nhiều loại dữ liệu cùng chỗ → **tab** dưới topbar, tab đang chọn gạch dưới màu nhấn `#1F66D1`
   (Danh mục & giá: Mặt hàng | Bảng giá | Ưu đãi | Nhóm hàng; Kho & lô: Tồn theo lô | Điều chỉnh tồn | Kho;
   Hoá đơn mua & chi phí: Hoá đơn mua | Chi phí phụ).

## 3. Câu chữ
1. Tiếng Việt đời thường, động từ rõ. **Không mã luật** (BR-…), không giải thích luật trên màn.
2. **Cấm thuật ngữ / viết tắt**: TTL, FEFO, hạch toán, thực thi, vùng đỏ, Mức A/B/C, NCC, NV, SĐT, STK, excerpt, slug, footer…
   Viết: nhà cung cấp, nhân viên, số điện thoại, số tài khoản, tóm tắt, đường dẫn, chân trang.
3. **Không chữ thừa**: không "Bước x/5" (trùng thanh trạng thái), không "cần người duyệt", không "Giá vốn chỉ Chủ thấy".
4. **Một việc một tên** (dùng đúng các chữ này ở nút, menu, nhật ký):

| Dùng | Không dùng |
|---|---|
| Xác nhận đã nhận tiền | Xác nhận thanh toán tay / thủ công, Xác nhận tiền về tay |
| Lập phiếu hoàn | Tạo phiếu hoàn, Báo hoàn tiền |
| Xác nhận đã hoàn tiền | Xác nhận đã chuyển |
| Lập phiếu kiểm kê | Tạo phiếu kiểm kê |
| Ghi lỗ, huỷ hàng · Huỷ bỏ, ghi lỗ | Hạch toán lỗ |
| Tắt trợ lý | Tắt khẩn |
| Đồng ý | Đồng ý thực thi |
| Khách hàng · Số điện thoại · Tổng số kg · Số tiền hoàn | Khách · SĐT · Tổng kg / Tổng khối lượng · Tổng hoàn |
| Đếm được (kg) · Tồn trên hệ thống (kg) · Thay đổi (kg) | Thực đếm · Tồn sổ · Biến động |
| Lấy … từ lô | Phân bổ … từ lô |
| Chờ duyệt | Chưa duyệt |
| Cài đặt | Cấu hình |

5. Thông báo lỗi nói cách sửa ("Nhập số kg lớn hơn 0.", "Chưa lưu được. Kiểm tra mạng rồi bấm lại.").

## 4. Màn danh sách
1. Bảng **full width, không panel bên phải**. Bấm dòng → mở **trang chi tiết** (không trượt panel).
2. Thanh lọc trên bảng: ô tìm, lọc trạng thái, khoảng ngày (tuỳ màn). Nút tạo mới ở góc phải tiêu đề.
3. Cột trạng thái = chip chuẩn; cột Lý do / Ghi chú riêng.
4. Danh sách đơn: **Mã đơn · Khách hàng · Trạng thái · Giao hàng · Lý do · Tổng tiền · Thời gian**.
5. AI trên danh sách: một thanh mảnh "**AI** · Có n đề xuất: …" + chip "AI đề xuất" trên dòng liên quan (cột riêng
   hoặc cùng hàng với mã, không chồng dưới). **AI không phải menu riêng**, không có màn "Việc AI".

## 5. Trang chi tiết (mẫu: Chi tiết đơn)
1. **Header**: ← tên danh sách · tiêu đề (mã mono nếu là chứng từ) · chip trạng thái · bên phải: nút thao tác chính
   rồi nút "…". **Không dòng xám dưới tiêu đề** (thông tin đó vào phần Thông tin).
2. **Thanh trạng thái** (chỉ đối tượng có vòng đời trạng thái): dải bước hình mũi tên kiểu Salesforce; bước đã qua
   nền xanh nhạt có ✓; bước hiện tại nền `#1F66D1` chữ trắng; kết thúc xấu (huỷ, thất bại) màu đỏ. Ngay dưới, trong
   cùng khối: **"→ Tiếp theo: …" bên trái**, **"Đã làm: ✓ … ✓ …" bên phải**. Đối tượng không có trạng thái (nhóm quyền,
   khách hàng, mặt hàng) không có thanh này.
3. **Thao tác đi theo trạng thái**: nút chính trên header; thao tác hiếm hoặc đang bị chặn nằm trong "…". Mục bị
   chặn hiện mờ, **lý do ngắn nằm cạnh** (không nằm dưới), ví dụ "Chốt lô · Lô còn 18,5 kg."
4. **Thông tin**: lưới 2 cột trường (nhãn nhỏ trên, giá trị dưới). Rê chuột hiện **bút chì** để sửa tại chỗ;
   trường chỉ đọc có icon khoá; trường trỏ tới đối tượng khác là **link**, sửa thì mở popup của đối tượng đó.
5. **Cột phải**: khối **Trợ lý AI** (người/giờ đề xuất, việc đề xuất, thay đổi trước → sau, nút Từ chối / Đồng ý,
   chip câu hỏi nhanh, **ô chat + nút gửi**), rồi **Dòng thời gian** (mỗi dòng: thời gian | việc). Trang chi tiết khách
   hàng **không có** Trợ lý AI; không đưa dữ liệu cá nhân của khách cho AI.

## 6. Form & popup
1. **Form ngắn (≤ 6 trường) và xác nhận = hộp thoại nổi trên đúng màn mở ra nó** (nền màn cha mờ).
   **Form dài / nhiều dòng** (nhập lô, kiểm kê, chi phí phụ, thêm mặt hàng, ưu đãi, thiết lập bài viết) = **trang riêng**
   có thanh nút cố định ở đáy.
2. Nhãn nằm trên ô, `*` đỏ cho bắt buộc. **Đơn vị trong ô** (`kg`, `đ`, `ngày`) hoặc trong nhãn. **Không chữ gợi ý xám
   dưới ô** (trừ màn đăng nhập/đặt mật khẩu). Lỗi: viền đỏ + một dòng đỏ dưới ô, nói cách sửa.
3. Ngữ cảnh trong form (đơn nào, lô nào, còn hoàn được bao nhiêu) → **khối tóm tắt**, mỗi dòng một cặp nhãn–giá trị.
   Cảnh báo quan trọng → một alert ngắn (vàng/đỏ) đầu form, chỉ khi thật cần.
4. **Nút**: [phụ … chính], nút chính bên phải, **nhãn nói rõ việc** và số tiền nếu có ("Lập phiếu hoàn 380.000 đ",
   "Xác nhận đã nhận 340.000 đ"). Việc phá huỷ (huỷ đơn, gỡ bài, cho nghỉ) = nút đỏ. Nút lui = "Quay lại" hoặc "Huỷ".
5. Việc không hoàn tác được → luôn có bước xác nhận (popup), nêu hậu quả bằng khối tóm tắt.
6. Gửi lỗi → giữ nguyên giá trị đã nhập, alert đỏ đầu form, nút chính đổi thành "Thử lại".

## 7. Trạng thái đặc biệt (mọi màn phải có)
| Trạng thái | Cách hiện |
|---|---|
| Danh sách trống | icon + tiêu đề ("Chưa có phiếu hoàn nào chờ chuyển") + 1 câu khi nào sẽ có |
| Tìm không thấy | "Không tìm thấy … khớp với <từ khoá>" + nút "Xoá tìm kiếm" |
| Đang tải | khung xương (skeleton) trong bảng, header & bộ lọc vẫn hiện |
| Mất mạng | banner "Mất kết nối. Đang thử lại…" + nút Thử lại; dữ liệu cũ mờ đi, ghi "Dữ liệu lúc dd/mm/yyyy hh:mm" |
| Lưu thất bại | xem §6.6 |
| Người khác vừa sửa | banner vàng dưới header: "Phiếu vừa được <tên> sửa lúc …. Tải lại để xem bản mới." + nút Tải lại |
| 404 / lỗi chung | nằm trong khung app (có sidebar): "Không tìm thấy trang này" / "Có lỗi xảy ra" + nút Về Tổng quan / Thử lại |
| Thông báo | toast góc dưới phải: thành công (có "Hoàn tác" nếu được), cảnh báo, lỗi; có nút đóng |
| Không có quyền | ẩn menu/nút; vào thẳng URL → màn "Không có quyền" |

## 8. Phân quyền trên giao diện
1. Menu và nút hiện theo quyền thật của người dùng (ma trận ở màn Phân quyền), không hard-code theo tên nhóm.
2. Việc chỉ Chủ làm được hiện icon khoá trong ma trận; các việc khác bật/tắt theo nhóm.
3. "Xem khách hàng" là một quyền riêng.

## 9. Token
Inter (chữ), JetBrains Mono (mã), Material Symbols (icon). Màu nhấn `#1F66D1`; viền `#E4E4E9`; chữ phụ `#4E4E58` / `#686874`;
nền `#FBFBFC`; chip: tốt (xanh lá), cảnh báo (hổ phách), lỗi (đỏ), thông tin (xanh), trung tính (xám). Bo góc 6–10 px.
Dùng token trong `DESIGN.md` / `erp-console/shared/ui/tokens.css`, không hard-code.

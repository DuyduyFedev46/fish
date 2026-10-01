# Làm lại giao diện ERP (máy tính) theo bộ thiết kế — User stories
> PO · 01/10/2026 · Nguồn: `01-analysis.md` (ĐÃ DUYỆT) · Luật UI: `doc/design/erp/UI-RULES.md` · Enum: `doc/design/erp/enum-map.md`
> Trạng thái: **ĐÃ DUYỆT (Duy duyệt 01/10/2026 qua chat: làm hết theo design ERP máy tính)**

## Mục tiêu & thước đo
Đưa `erp-console/` về đúng bộ thiết kế ERP máy tính đã duyệt, bổ sung backend B1–B6.
- 105/105 file `doc/design/erp/screens/*.dc.html` có màn tương ứng; QA đối chiếu từng file (bảng "Design" của mỗi story).
- Test quét chữ cấm (UI-RULES §3.2, chuỗi `BR-`, `DH-`, "hôm nay", "hôm qua", "phút trước") trên text hiển thị: 0 kết quả.
- 0 lỗi rò giá vốn, 0 lỗi rò dữ liệu cá nhân của khách (test bằng token Quản lý, Nhân viên kho, Nhân viên giao, CSKH).

## Phạm vi
Trong: mọi màn trong `doc/design/erp/screens/` (danh sách, chi tiết, form, popup, trạng thái W6*), backend B1–B6.
Ngoài: Shop khách mua, ERP điện thoại (`ERP-M*`), đổi quy tắc nghiệp vụ, đổi enum DB.

## Quy ước dùng trong file này
**Vai:** Chủ · Quản lý · Nhân viên kho · Nhân viên giao · CSKH. Quyền mặc định của từng vai lấy theo ma trận ở `ERP-W3h-Phan-quyen`; FE luôn đọc quyền thật (UI-RULES §8.1), không so tên nhóm.

**Nguyên tắc khi thiết kế lệch code** (01-analysis §4): code/DB thắng về dữ liệu, trạng thái và mã chứng từ; thiết kế thắng về bố cục và câu chữ. Các chỗ lệch đã thấy:
- `ERP-D1` ghi "Hết giữ chỗ sau 12 phút" trong cột Lý do. Khi code: đếm ngược để ở cột riêng.
- Thiết kế che số điện thoại "…0412". Khi code: hiện đủ cho người có quyền (quyết định 14).
- Mã lô, mã phiếu nhập và mã phiếu kiểm kê trên thiết kế (`L0914-CT01`, `PR-92`, `KK-13`) là minh hoạ. Khi code: dùng mã thật trong DB, chứng từ không có số thì hiện `#<id>` (§1.4).

**Bộ kiểm chung G1–G10.** Mọi story FE có màn đều phải đạt. QA kiểm trên từng màn của story, không ghi lại trong từng bảng AC.

| Mã | Kiểm | Nguồn |
|---|---|---|
| G1 | Mỗi ô bảng hoặc trường chỉ có một giá trị, không có dòng xám chồng bên dưới | UI-RULES §1.1 |
| G2 | Mốc sự kiện hiện dạng `dd/mm/yyyy hh:mm` theo giờ Việt Nam. Ngày thuần (hạn dùng, ngày hoá đơn) hiện dạng `dd/mm/yyyy`. Không dùng thời gian tương đối | §1.5 |
| G3 | Chip trạng thái dùng đúng nhãn ở cột "Artboard" của enum-map, không có chú thích trong chip, lý do để ở cột hoặc trường riêng | §1.2, §1.3 |
| G4 | Mã chứng từ đúng định dạng code, dùng font mono | §1.4 |
| G5 | Tiền viết dạng `390.000 đ`, kg viết dạng `18,5 kg`, dùng tabular-nums và căn phải trong bảng | §1.6 |
| G6 | Giá vốn, lãi lỗ và tiền nhà cung cấp chỉ có icon khoá. Người không có quyền: cột hoặc trường không có trong DOM, response API không có key đó | §1.7, bất biến 1 |
| G7 | Không có chữ trong danh sách cấm §3.2, không có mã BR, dùng đúng tên việc theo bảng §3.4 | §3 |
| G8 | Danh sách có đủ các trạng thái trống, tìm không thấy, đang tải và lỗi theo ED-03 | §7 |
| G9 | Menu và nút hiện theo quyền thật. Vào thẳng URL khi không có quyền thì ra màn "Không có quyền" | §7, §8 |
| G10 | Tên, số điện thoại và địa chỉ của khách không nằm trong URL, `localStorage`, `console` hay request gửi Trợ lý AI | bất biến 9 |

**Definition of Done** (chung, không lặp lại trong story): test BE xanh; `tsc --noEmit` và `npm run build` của erp-console sạch; QA report APPROVED (có ca ngoài đường thuận, có ảnh so với file design); không rò giá vốn hay dữ liệu cá nhân; doc cập nhật nếu đổi rule.

---

# A. Khung chung

## ED-01 — Khung app: sidebar, topbar, menu avatar, tab · Must · FE
**Là** người dùng ERP, **tôi muốn** menu theo nghiệp vụ, chỉ hiện việc tôi được làm, **để** tìm đúng màn mà không lạc.
Design: sidebar và topbar có trong mọi file; tab ở `ERP-D3`, `ERP-W2d`, `ERP-W5g`. Ưu tiên Must vì mọi story khác dựng trên khung này.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-01-AC1 | Chủ đã đăng nhập | mở một màn bất kỳ | Sidebar có đủ nhóm và mục theo thứ tự §2.1, mục đang mở được tô. Topbar có tên màn bên trái, ô tìm (⌘K) và avatar bên phải. Không có nút "Làm mới" và không có nút Đăng xuất rời | |
| ED-01-AC2 | Sidebar đang mở rộng (240 px) | bấm nút thu gọn, rồi tải lại trang | Sidebar còn 60 px, chỉ hiện icon, rê chuột thấy tooltip tên mục. Trạng thái thu gọn vẫn giữ sau khi tải lại | |
| ED-01-AC3 | Đang ở một màn bất kỳ | bấm avatar | Menu có đúng 3 mục: Tài khoản của tôi · AI của tôi · Đăng xuất. Bấm Đăng xuất thì phiên bị xoá và app về màn Đăng nhập | |
| ED-01-AC4 | Màn có tab (Kho & lô, Danh mục & giá, Hoá đơn mua & chi phí) | bấm sang tab khác rồi bấm Back của trình duyệt | Tab đang chọn có gạch dưới màu nhấn. URL đổi theo tab, nên Back quay về đúng tab trước | |
| ED-01-AC5 (quyền) | Nhân viên giao đăng nhập | xem sidebar | Chỉ có mục "Việc giao của tôi" (theo `ERP-F2l`). Không có Tổng quan, Kế toán hay Quản trị trong DOM. Sau khi đăng nhập, app vào thẳng Việc giao của tôi | BR-PQ-12 |
| ED-01-AC6 (quyền) | Chủ tắt quyền "Xem khách hàng" của nhóm Quản lý | Quản lý tải lại app | Mục Khách hàng biến mất mà không phải sửa code (menu dựng từ quyền trong `auth/me`) | |

## ED-02 — Định dạng dữ liệu và bộ nhãn dùng chung · Must · FE
**Là** dev FE, **tôi muốn** một chỗ duy nhất để định dạng thời gian, tiền, kg, chip, mã chứng từ và ô giá vốn, **để** mọi màn đạt G1–G7 mà không phải sửa lẻ từng màn.
Design: `enum-map.md` cùng mọi file. Ưu tiên Must vì G2–G7 phụ thuộc story này.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-02-AC1 | Mốc `2026-10-01T02:32:00Z` | định dạng | Ra `01/10/2026 09:32`. Ngày `2026-10-05` ra `05/10/2026` | |
| ED-02-AC2 | Tiền `390000` và kg `18.5` | định dạng | Ra `390.000 đ` và `18,5 kg`. Không dùng float để tính tiền | bất biến 7 |
| ED-02-AC3 | Mọi giá trị enum có trong enum-map | lấy nhãn chip | Mỗi giá trị đều có nhãn (unit test duyệt hết bảng). `AUTO_CANCELLED` ra "Đã huỷ". `WRITE_OFF` ra "Ghi lỗ, huỷ hàng". `ReturnToStock.decision WRITE_OFF` ra "Huỷ bỏ, ghi lỗ". Mức AI ra Tắt · Tự đọc · Hỏi trước khi làm · Tự ghi. Chế độ AI ra Bật · Luôn hỏi trước · Tắt | |
| ED-02-AC4 (lỗi) | API trả về giá trị enum lạ | hiện chip | Hiện chip trung tính ghi đúng mã gốc. Không tự đặt nhãn | §1.3 |
| ED-02-AC5 (giá vốn) | Người dùng không có `view_costprice` | render ô hoặc cột giá vốn | Ô hoặc cột không render, không còn khoảng trống, không có câu giải thích. Người có quyền thấy giá trị kèm icon khoá | bất biến 1 |
| ED-02-AC6 | Toàn bộ text hiển thị của erp-console | chạy test quét chữ cấm | Không có chữ trong danh sách §3.2, không có `BR-`, không có `DH-`, không có chữ trong cột "Không dùng" của §3.4 | |

## ED-03 — Trạng thái đặc biệt: trống, tải, lỗi, xung đột, thông báo · Must · FE
**Là** người dùng, **tôi muốn** biết rõ màn đang trống, đang tải hay đang lỗi và cách xử lý, **để** không bấm mò.
Design: `ERP-W6a` đến `ERP-W6i`, `ERP-W4h`. Ưu tiên Must vì G8 phụ thuộc story này.

| Mã | Given | When | Then |
|---|---|---|---|
| ED-03-AC1 | Danh sách không có dòng nào | mở màn | Có icon, tiêu đề riêng của màn và một câu nói khi nào sẽ có dữ liệu (ví dụ "Chưa có phiếu hoàn nào chờ chuyển") |
| ED-03-AC2 | Đã gõ từ khoá mà không khớp dòng nào | xem bảng | Hiện "Không tìm thấy … khớp với <từ khoá>" và nút "Xoá tìm kiếm". Bấm nút thì bảng hiện lại đầy đủ |
| ED-03-AC3 | API đang tải | xem màn | Bảng hiện khung xương (skeleton). Header và bộ lọc vẫn hiện, không bị nhảy bố cục |
| ED-03-AC4 (lỗi) | Mất mạng khi đã có dữ liệu cũ | xem màn | Có banner "Mất kết nối. Đang thử lại…" kèm nút Thử lại. Dữ liệu cũ mờ đi, kèm dòng "Dữ liệu lúc dd/mm/yyyy hh:mm" |
| ED-03-AC5 (lỗi) | Người khác vừa sửa bản ghi (API trả mã xung đột, Tech Lead chốt mã ở 02b) | tôi bấm Lưu | Banner vàng dưới header: "Phiếu vừa được <tên> sửa lúc …. Tải lại để xem bản mới." kèm nút Tải lại. Bản của người kia không bị ghi đè |
| ED-03-AC6 | URL không tồn tại, hoặc lỗi 5xx | mở URL | Màn lỗi nằm trong khung app (vẫn có sidebar): "Không tìm thấy trang này" kèm nút Về Tổng quan, hoặc "Có lỗi xảy ra" kèm nút Thử lại |
| ED-03-AC7 | Một thao tác vừa thành công, cảnh báo hoặc lỗi | xem góc dưới phải | Toast đúng loại, có nút đóng. Nút "Hoàn tác" chỉ có khi thao tác hoàn tác được. Nội dung toast không có số điện thoại hay địa chỉ của khách |
| ED-03-AC8 (quyền) | Nhân viên kho | mở thẳng URL Báo cáo lãi lỗ | Ra màn "Không có quyền" (`ERP-W4h`). Không hiện số liệu nào của báo cáo |

## ED-04 — Mẫu màn danh sách và trang chi tiết · Must · FE
**Là** người dùng, **tôi muốn** mọi danh sách và trang chi tiết bố trí giống Chi tiết đơn, **để** học một lần là dùng được mọi màn.
Design: `ERP-D2`, `ERP-D2b`, `ERP-D2c` là mẫu chuẩn. Ưu tiên Must vì 30 story màn dùng lại mẫu này.

| Mã | Given | When | Then |
|---|---|---|---|
| ED-04-AC1 | Một danh sách | bấm một dòng | Mở trang chi tiết riêng có URL riêng, không trượt panel. Bấm "←" thì về danh sách, còn nguyên bộ lọc |
| ED-04-AC2 | Thanh lọc | lọc theo trạng thái và khoảng ngày | Bảng full width, có "Đang hiện x / y". Trạng thái và ngày nằm trong URL. Từ khoá tìm không đưa vào URL (G10) |
| ED-04-AC3 | Trang chi tiết | xem header | Header gồm: ← tên danh sách · tiêu đề (mã mono) · chip · nút chính · nút "…". Dưới tiêu đề không có dòng xám (§5.1) |
| ED-04-AC4 | Đối tượng có vòng đời | xem thanh trạng thái | Bước đã qua có ✓ trên nền xanh nhạt, bước hiện tại nền màu nhấn, kết thúc xấu màu đỏ. "→ Tiếp theo" ở bên trái, "Đã làm" ở bên phải, lấy từ API `guidance/`. Đối tượng không có vòng đời (khách hàng, mặt hàng, nhóm quyền) thì không có thanh này (§5.2) |
| ED-04-AC5 | Mục trong "…" bị chặn vì trạng thái | mở "…" | Mục mờ, lý do ngắn ở cùng dòng (ví dụ "Chốt lô · Lô còn 18,5 kg."). Bấm vào không gọi API |
| ED-04-AC6 (quyền) | Người dùng không có quyền làm một việc | mở "…" hoặc xem header | Việc đó bị **ẩn hẳn**, không hiện mờ. Mờ kèm lý do chỉ dùng khi bị chặn vì trạng thái (§5.3, §7) |
| ED-04-AC7 | Khối Thông tin | rê chuột lên các trường | Trường sửa được (theo quyền) hiện bút chì để sửa tại chỗ, có Lưu và Huỷ. Trường chỉ đọc có icon khoá. Trường trỏ tới đối tượng khác là link, mở popup xem nhanh có nút "Đóng" và "Mở trang …" (như `ERP-D2b`) |
| ED-04-AC8 | Đối tượng có đề xuất AI | xem cột phải | Khối Trợ lý AI có: người và giờ đề xuất, việc đề xuất, thay đổi trước → sau, nút Từ chối / Đồng ý, chip câu hỏi nhanh, ô chat và nút gửi. Bấm Đồng ý gọi API AI action. Kết quả hiện ở Dòng thời gian. Khi không có đề xuất, vẫn còn ô chat |
| ED-04-AC9 (giá vốn) | Đề xuất AI có giá trị giá vốn, người xem là Quản lý | xem khối AI | Không có giá trị giá vốn trong phần trước → sau. Response API cũng không có giá trị đó |
| ED-04-AC10 (dữ liệu cá nhân) | Tôi đang ở trang chi tiết đơn | gửi câu hỏi trong ô chat AI | Request gửi đi không có tên, số điện thoại hay địa chỉ của khách |
| ED-04-AC11 | Danh sách có n > 0 đề xuất AI | xem màn | Có thanh mảnh "AI · Có n đề xuất: …", và chip "AI đề xuất" ở cột riêng trên đúng dòng. Khi n = 0 thì không có thanh. Không có menu "Việc AI" (§4.5) |
| ED-04-AC12 | Dòng thời gian | xem | Mỗi dòng gồm thời gian (G2) và việc, mới nhất ở trên cùng hoặc dưới cùng theo file design |

## ED-05 — Mẫu form: hộp thoại và trang form · Must · FE
**Là** người dùng, **tôi muốn** form ngắn hiện ngay trên màn đang làm và form dài có trang riêng, **để** không mất ngữ cảnh.
Design: mọi file `ERP-F*`, `ERP-W6e`. Ưu tiên Must vì 40 form và popup dùng lại mẫu này.

| Mã | Given | When | Then |
|---|---|---|---|
| ED-05-AC1 | Form có tối đa 6 trường, hoặc là bước xác nhận | mở form | Form là hộp thoại nổi trên đúng màn cha ghi trong file design, nền màn cha mờ. Focus nằm trong hộp thoại, Esc đóng hộp thoại. Đóng xong thì về đúng màn cha, giữ nguyên vị trí cuộn và bộ lọc |
| ED-05-AC2 | Form dài (nhập lô, kiểm kê, chi phí phụ, thêm mặt hàng, ưu đãi, thiết lập bài viết) | mở form | Form là trang riêng, có thanh nút cố định ở đáy, header có "←" về màn cha |
| ED-05-AC3 | Trường bắt buộc để trống | bấm nút chính | Ô có viền đỏ và một dòng đỏ dưới ô nói cách sửa ("Nhập số kg lớn hơn 0."). Nhãn nằm trên ô, `*` màu đỏ, đơn vị nằm trong ô. Không có chữ gợi ý xám dưới ô, trừ màn Đăng nhập và Đặt mật khẩu |
| ED-05-AC4 | Mọi form | xem thanh nút | Thứ tự [nút phụ … nút chính], nút chính bên phải. Nhãn nói rõ việc và có số tiền nếu có ("Lập phiếu hoàn 380.000 đ"). Việc phá huỷ dùng nút đỏ. Nút lui chỉ dùng "Quay lại" hoặc "Huỷ". Popup xem nhanh dùng "Đóng" |
| ED-05-AC5 (lỗi) | API trả lỗi khi gửi | xem form | Các giá trị đã nhập còn nguyên. Đầu form có alert đỏ. Nút chính đổi thành "Thử lại" (`ERP-W6e`) |
| ED-05-AC6 (lỗi) | Bấm nút chính 2 lần liên tiếp | đang gửi | Nút bị khoá trong lúc gửi, API chỉ nhận 1 request |
| ED-05-AC7 | Việc không hoàn tác được (chốt lô, cho nghỉ việc, gỡ bài…) | bấm nút chính | Luôn có bước xác nhận, nêu hậu quả bằng khối tóm tắt, mỗi dòng một cặp nhãn–giá trị (§6.3, §6.5) |

## ED-06 — Đăng nhập và các màn trong menu avatar · Must · FE
**Là** nhân viên, **tôi muốn** đăng nhập, đổi mật khẩu và chỉnh AI của mình, **để** tự lo tài khoản mà không cần nhờ Chủ.
Design: `ERP-W4f`, `ERP-W4g`, `ERP-W4e`, `ERP-F3g`, `ERP-W4b`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-06-AC1 | Đang ở màn Đăng nhập | nhập sai mật khẩu | Một dòng lỗi chung, không cho biết tên đăng nhập có tồn tại hay không | |
| ED-06-AC2 | API báo tài khoản phải đặt mật khẩu mới | đăng nhập | Vào màn Đặt mật khẩu mới (`ERP-W4g`) trước. Chưa đặt xong thì không vào được màn khác | BR-PQ-17 |
| ED-06-AC3 | Đang ở Tài khoản của tôi | bấm Đổi mật khẩu, nhập sai mật khẩu cũ | Hộp thoại nổi trên màn Tài khoản, báo lỗi dưới ô mật khẩu cũ. Đổi đúng thì có toast thành công | |
| ED-06-AC4 | Đang ở AI của tôi | chọn một mức AI cao hơn mức Chủ cho phép | Mức đó mờ, có lý do ngắn ở cạnh. Có nút "Tắt trợ lý", không dùng chữ "Tắt khẩn" | |
| ED-06-AC5 (quyền) | Vai bất kỳ | mở 3 màn trên | Chỉ thấy dữ liệu của chính mình. Không có đường nào xem tài khoản của người khác | |

## ED-07 — Tìm nhanh ⌘K theo mã chứng từ · Could · FE
**Là** Quản lý, **tôi muốn** gõ mã đơn, phiếu giao hoặc lô để mở ngay, **để** không phải lọc tay. Ưu tiên Could vì thiết kế chỉ vẽ ô tìm, chưa vẽ kết quả (xem câu hỏi Q6).
Design: ô tìm trên topbar ở mọi file.

| Mã | Given | When | Then |
|---|---|---|---|
| ED-07-AC1 | Đang ở một màn bất kỳ | bấm ⌘K hoặc Ctrl+K, gõ đúng `SO260930-1F4A2C` rồi Enter | Mở Chi tiết đơn đó |
| ED-07-AC2 (lỗi) | Gõ một mã không có | Enter | Hiện "Không tìm thấy … khớp với <mã>" |
| ED-07-AC3 (quyền) | Nhân viên giao gõ mã phiếu giao của người khác | Enter | Báo không tìm thấy, giống trường hợp mã không có | 

---

# B. Tổng quan

## ED-08 — Tổng quan · Must · FE
**Là** Chủ, **tôi muốn** đầu ngày thấy ngay việc cần chú ý, **để** xử lý trước khi khách phải chờ.
Design: `ERP-D1`. API có sẵn: `dashboard/summary/`, `dashboard/attention/`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-08-AC1 | Chủ | mở Tổng quan | Có các thẻ: Doanh thu ngày dd/mm/yyyy · Đơn chờ xử lý · Sắp hết giữ chỗ · Lô cận hạn (14 ngày tới) · Giá trị tồn kho theo giá vốn (icon khoá) | |
| ED-08-AC2 | Bảng Đơn hàng gần đây | xem | Mã dạng `SO…` (không có `DH-`). Trạng thái là chip, cột Lý do riêng. Đếm ngược giữ chỗ nằm ở cột riêng, không gộp vào Lý do | §1.4, §1.5 |
| ED-08-AC3 | Khối "Cần chú ý" có lô cận hạn hoặc quá hạn và đề xuất AI theo khu | bấm một dòng | Mở đúng màn (chi tiết lô, hoặc màn có đề xuất) | |
| ED-08-AC4 (giá vốn) | Quản lý (không có `view_costprice`) | mở Tổng quan | Không có thẻ Giá trị tồn kho, không có cột Giá vốn/kg. Response `dashboard/summary/` không có các key đó | bất biến 1 |
| ED-08-AC5 (quyền) | Nhân viên giao | mở URL Tổng quan | Ra màn "Không có quyền" | |

---

# C. Bán hàng

## ED-09 — Đơn & tiền: danh sách và chi tiết đơn · Must · FE
**Là** Quản lý, **tôi muốn** xem đơn theo trạng thái và biết bước tiếp theo, **để** đơn không bị kẹt.
Design: `ERP-D2`, `ERP-D2b`, `ERP-D2c`. Story này là mẫu chuẩn cho ED-04.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-09-AC1 | Danh sách đơn | xem | Cột đúng §4.4: Mã đơn · Khách hàng · Trạng thái · Giao hàng · Lý do · Tổng tiền · Thời gian. Đơn `AUTO_CANCELLED` có chip "Đã huỷ" và Lý do "Hết giờ giữ chỗ" | §1.2 |
| ED-09-AC2 | Đơn ở từng trạng thái | mở chi tiết | Thanh trạng thái gồm Giữ chỗ → Đã thanh toán → Soạn hàng → Đang giao → Hoàn tất. Đơn huỷ thì bước cuối "Đã huỷ" màu đỏ | |
| ED-09-AC3 | Đơn ở từng trạng thái (bảng 1 của `ERP-D2c`) | xem header | Nút chính khớp bảng 1: Giữ chỗ → "Xác nhận đã nhận tiền"; Đã thanh toán và Đang xử lý/Soạn hàng → "Huỷ đơn" (đỏ); Đang xử lý/Đang giao → không có nút chính; Hoàn tất → "Lập phiếu hoàn"; Đã huỷ (tiền về muộn) → "Xác nhận đã nhận tiền" | BR-BH, BR-HT |
| ED-09-AC4 | Đơn ở từng trạng thái (bảng 2 của `ERP-D2c`) | mở "…" | Các mục khớp bảng 2. Giữ chỗ: "Huỷ đơn" mờ, lý do "Đơn chưa thanh toán sẽ tự huỷ khi hết giờ giữ chỗ.". Đang giao: "Huỷ đơn" mờ, lý do "Đơn đang giao: báo giao thất bại trước rồi mới huỷ được.". Đơn nào cũng có "Sao chép mã đơn" và "Xem nhật ký của đơn" | BR-GH-07 |
| ED-09-AC5 | Đơn Giữ chỗ | xem Thông tin | "Còn giữ chỗ" (đếm ngược) và "Tự huỷ lúc" dd/mm/yyyy hh:mm là hai trường riêng. Hết giờ thì chip đổi, không cần tải lại | bất biến 6 |
| ED-09-AC6 (giá vốn) | Quản lý mở chi tiết đơn | xem bảng "Hàng & phân bổ lô" | Không có cột Giá vốn/kg. Response API không có `unit_cost`. Popup xem nhanh Lô cũng không có Giá vốn/kg | bất biến 1 |
| ED-09-AC7 (quyền) | Quản lý | mở đơn Giữ chỗ | Không có nút "Xác nhận đã nhận tiền". Gọi thẳng `POST sales/orders/{id}/confirm-payment` thì nhận 403 | `confirm_payment_manual` |
| ED-09-AC8 (dữ liệu cá nhân) | Người không có quyền "Xem khách hàng" | xem trường Khách hàng | Tên hiện dạng chữ thường, không có link hay popup xem nhanh khách. Người có quyền xem đơn thấy số điện thoại người nhận đầy đủ (quyết định 14) | bất biến 9 |
| ED-09-AC9 (quyền) | Nhân viên giao | mở URL một đơn không thuộc phiếu giao của mình | Ra màn "Không tìm thấy trang này" (API trả 404) | BR-PQ-12 |

## ED-10 — Thao tác trên đơn: nhận tiền, huỷ, hoàn, đổi người nhận · Must · FE
**Là** Chủ hoặc Quản lý, **tôi muốn** làm các việc với đơn ngay trên trang đơn, **để** không phải mở màn khác.
Design: `ERP-F2a`, `ERP-F2b`, `ERP-F2c`, `ERP-F2j`. Tất cả là hộp thoại nổi trên Chi tiết đơn.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-10-AC1 | Chủ, đơn Giữ chỗ | Xác nhận đã nhận tiền | Khối tóm tắt có đơn và số tiền cần thu. Nút ghi "Xác nhận đã nhận 390.000 đ". Thành công thì chip đổi thành "Đã thanh toán", Dòng thời gian có dòng mới, hiện toast | BR-TT |
| ED-10-AC2 | Quản lý, đơn Đã thanh toán | Huỷ đơn | Lý do chọn từ Khách đổi ý · Hư khi đóng hàng · Bỏ sau khi giao thất bại · Khác. Nút "Huỷ đơn" màu đỏ, có bước xác nhận hậu quả. Huỷ xong thì gợi ý "Lập phiếu hoàn" | BR-HT, BR-GH-07 |
| ED-10-AC3 (lỗi) | Lập phiếu hoàn | nhập số tiền lớn hơn "Còn hoàn được" | Ô báo lỗi "Nhập tối đa <số> đ.". Nút chính bị khoá | BR-HT |
| ED-10-AC4 | Phiếu giao đã in tem | Đổi người nhận / địa chỉ | Có alert vàng đầu form: lưu xong phải in lại tem. Không cho đổi khi phiếu đang ở Đang giao trở đi | BR-GH |
| ED-10-AC5 (dữ liệu cá nhân) | Đổi địa chỉ thành công | xem toast, AuditLog và console | Toast không có địa chỉ. AuditLog chỉ ghi "ai đổi thông tin nhận của đơn nào", không chép địa chỉ hay số điện thoại | bất biến 9, BR-PQ-04 |
| ED-10-AC6 (quyền) | Nhân viên kho và CSKH | mở chi tiết đơn | Không có Huỷ đơn và Lập phiếu hoàn. Gọi API thì nhận 403 | `cancel_paid_order`, `create_refund` |

## ED-11 — Hàng chờ thanh toán và chi tiết khoản tiền · Must · FE
**Là** Chủ, **tôi muốn** xử lý tiền về thiếu, thừa, lạc đơn, **để** đơn nào cũng khớp sao kê.
Design: `ERP-W1a`, `ERP-W1a2`, `ERP-F2d`, `ERP-F2e`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-11-AC1 | Danh sách | xem | Loại khoản tiền dùng nhãn FE ngắn (Khớp · Thiếu tiền · Về sau khi đơn tự huỷ · Không khớp đơn · Chuyển thừa). Tình trạng xử lý là cột riêng (Chờ xử lý / Đã xử lý) | §1.3 |
| ED-11-AC2 | Khoản Không khớp đơn | Gắn khoản tiền vào đơn (hộp thoại trên Chi tiết khoản tiền) | Chọn đơn, xem khối tóm tắt, bấm nút chính. Khoản chuyển sang "Đã xử lý · Đã gắn vào đơn" | BR-TT |
| ED-11-AC3 | Khoản Thiếu tiền, khách đã chuyển bù | Xác nhận đơn đã đủ tiền | Nút có số tiền. Đơn chuyển sang Đã thanh toán | BR-TT |
| ED-11-AC4 (lỗi) | Khoản tiền đã được xử lý ở tab khác | bấm Gắn | Banner xung đột theo ED-03-AC5. Không xử lý lần hai | |
| ED-11-AC5 (quyền) | Quản lý | mở màn | Không có nút Gắn hay Xác nhận. Gọi `sales/payments/{id}/resolve` thì nhận 403 | `confirm_payment_manual` |
| ED-11-AC6 (dữ liệu cá nhân) | Nội dung chuyển khoản có tên người chuyển | xem màn, console, request AI | Chỉ hiện trên màn cho người có quyền. Không có trong console hay request AI | bất biến 9 |

## ED-12 — Phiếu hoàn · Must · FE
**Là** Chủ, **tôi muốn** thấy các phiếu hoàn chờ chuyển và ghi kết quả chuyển, **để** khách nhận lại tiền đúng hạn.
Design: `ERP-W1b`, `ERP-W1b2`, `ERP-F2f`, `ERP-F2g`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-12-AC1 | Danh sách | xem | Chip dùng Chờ hoàn · Đã hoàn · Thất bại. Cột "Số tiền hoàn" (không viết "Tổng hoàn"). Danh sách trống hiện "Chưa có phiếu hoàn nào chờ chuyển" | §3.4 |
| ED-12-AC2 | Phiếu Chờ hoàn | Xác nhận đã hoàn tiền | Hộp thoại trên Chi tiết phiếu hoàn có khối tóm tắt, nút "Xác nhận đã hoàn 380.000 đ". Thành công thì chip đổi thành "Đã hoàn" | BR-HT |
| ED-12-AC3 (lỗi) | Chuyển khoản bị ngân hàng trả lại | Báo chuyển thất bại | Chip đổi thành "Thất bại", lý do nằm ở trường riêng. Phiếu không bị xoá | BR-PQ-10 |
| ED-12-AC4 (quyền) | Quản lý | mở phiếu Chờ hoàn | Không có "Xác nhận đã hoàn tiền". Gọi API thì nhận 403 | `confirm_refund` |

## ED-13 — [B2] Quyền "Xem khách hàng" và API khách có số liệu mua · Must · BE
**Là** Chủ, **tôi muốn** quyền xem khách là một quyền riêng và danh sách khách có số đơn, tổng mua, số đơn huỷ, **để** chỉ người cần mới thấy dữ liệu khách.
Bối cảnh: 01-analysis B2, quyết định 13 và 14. Model `Customer` đã có `name`, `phone`, `default_address`, `note`, nên **không thêm field**. Chỉ thêm quyền và các trường tính toán.

**Contract dự kiến** (Tech Lead chốt tên quyền ở 02b. Django đã tạo sẵn `sales.view_customer`; nếu dùng quyền này thì phải gỡ nó khỏi các nhóm không được xem):
```
GET /api/sales/customers/?search=&ordering=-last_order_at&page=1
200 {"count":126,"results":[{"id":12,"name":"Khách Thử A","phone":"0900000412",
  "order_count":6,"total_spent":"2140000","last_order_at":"2026-10-01T09:32:00+07:00","note":"Giao trước 11 giờ"}]}
GET /api/sales/customers/12/
200 {...như trên, "default_address":"[Địa chỉ giao]","first_order_at":"2026-08-12T10:14:00+07:00",
  "cancelled_order_count":1,
  "orders":[{"code":"SO261001-4B7E20","status":"BOOKED","total":"390000","created_at":"…"}],
  "refunds":[{"order_code":"SO260911-7F9A02","status":"REFUNDED","amount":"380000","created_at":"…"}]}
PATCH /api/sales/customers/12/ {"name":"…","phone":"…","default_address":"…","note":"…"} → 200
403 {"detail":"Bạn không có quyền xem khách hàng."}   404 khi ngoài phạm vi
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-13-AC1 | Migration chạy trên DB mới | kiểm quyền | Nhóm `chu` và `quan_ly` có quyền Xem khách hàng. `nv_kho`, `nv_giao` và CSKH không có | quyết định 13 |
| ED-13-AC2 | Khách có 6 đơn, trong đó 1 đơn CANCELLED và 1 đơn AUTO_CANCELLED | GET danh sách | `order_count`=6, `cancelled_order_count`=2. `total_spent` chỉ cộng đơn đã thanh toán và chưa huỷ, trừ số tiền đã hoàn. Kiểu Decimal dạng chuỗi. `last_order_at` là đơn mới nhất | bất biến 7 |
| ED-13-AC3 (quyền) | Token Nhân viên kho, Nhân viên giao, CSKH | GET danh sách hoặc chi tiết | Nhận 403, body không có dữ liệu khách | bất biến 9 |
| ED-13-AC4 (quyền) | Quản lý không có quyền sửa khách | PATCH | Nhận 403, dữ liệu không đổi | BR-PQ |
| ED-13-AC5 (dữ liệu cá nhân) | PATCH đổi số điện thoại thành công | đọc AuditLog và log | AuditLog ghi người sửa, mã khách và tên trường đã đổi. Không có giá trị số điện thoại hay địa chỉ trong AuditLog, logger hay Sentry | bất biến 9, BR-PQ-04 |
| ED-13-AC6 (lỗi) | PATCH số điện thoại trùng với khách khác | gửi | Nhận 400 "Số điện thoại này đã thuộc khách khác.", không đổi dữ liệu | |
| ED-13-AC7 | Chạy test hồi quy | các màn giao hàng và gọi xác nhận | Vẫn lấy được tên và số điện thoại người nhận qua API phiếu giao, không cần quyền Xem khách hàng | BR-PQ-12 |

## ED-14 — Khách hàng: danh sách và chi tiết · Must · FE
**Là** Chủ, **tôi muốn** xem lịch sử mua của từng khách, **để** chăm khách quen và xử lý khiếu nại.
Design: `ERP-W5a`, `ERP-W5b`. Phụ thuộc ED-13 (FE dựng mock theo contract ED-13).

| Mã | Given | When | Then |
|---|---|---|---|
| ED-14-AC1 | Danh sách | xem | Cột Khách hàng · Số điện thoại (hiện đủ) · Số đơn · Tổng đã mua · Đơn gần nhất · Ghi chú. Mặc định sắp "Đơn gần nhất mới trước". Không có thanh AI |
| ED-14-AC2 | Chi tiết khách | xem | Header có "Sửa thông tin" và "…". **Không có** thanh trạng thái, **không có** khối Trợ lý AI. Thông tin gồm: Tên, Số điện thoại, Địa chỉ giao mặc định, Ghi chú (sửa được); Khách từ, Số đơn, Tổng đã mua, Đơn huỷ (chỉ đọc, có icon khoá). Có bảng Đơn hàng, bảng Phiếu hoàn và Dòng thời gian |
| ED-14-AC3 (lỗi) | Lưu số điện thoại trùng | Lưu | Viền đỏ dưới ô, ghi đúng câu lỗi của API. Giá trị đã nhập còn nguyên |
| ED-14-AC4 (quyền) | Quản lý bị Chủ tắt quyền Xem khách hàng | mở URL `/khach-hang/12` | Ra màn "Không có quyền". Menu Khách hàng bị ẩn |
| ED-14-AC5 (dữ liệu cá nhân) | Tìm theo số điện thoại | gõ vào ô tìm | URL không chứa từ khoá. Không có `console.log` dữ liệu khách. Không lưu gì vào `localStorage` (G10) |

## ED-15 — Gọi xác nhận · Must · FE
**Là** CSKH, **tôi muốn** biết đơn nào cần gọi trước và ghi kết quả nhanh, **để** kho soạn đúng đơn đã chốt.
Design: `ERP-W1c`, `ERP-W1c2`, `ERP-F2h`, `ERP-F2i`, `ERP-F2k`. API có sẵn: `cskh/queue`, `cskh/search`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-15-AC1 | Danh sách | xem | Bộ lọc gồm Cần gọi ngay · Hẹn gọi lại · Cần quyết định · Gọi báo hoàn tiền · Chờ gọi · Tất cả. Chip theo `ConfirmTask.state`, với REFUND_CALL là "Gọi báo hoàn tiền". Lý do chuyển quyết định ở cột riêng | §1.2 |
| ED-15-AC2 | CSKH mở một việc gọi | Ghi kết quả gọi | Lựa chọn: Đã xác nhận · Hẹn gọi lại · Không nghe máy · Sai số điện thoại · Khách muốn đổi món · Khách muốn huỷ đơn · Đã báo hoàn tiền. Lưu xong thì Dòng thời gian có dòng mới | BR-GH |
| ED-15-AC3 (lỗi) | Hẹn gọi lại | chọn thời điểm đã qua | Báo lỗi "Chọn thời điểm sau dd/mm/yyyy hh:mm.", không lưu | |
| ED-15-AC4 | Việc ở trạng thái Cần quyết định, người mở là Quản lý | Quyết định đơn chưa xác nhận được | Lựa chọn: Giao không xác nhận · Gia hạn thêm · Huỷ đơn (Huỷ đơn dùng nút đỏ, có xác nhận) | BR-GH |
| ED-15-AC5 (quyền) | CSKH | mở việc Cần quyết định | Không có nút Quyết định. Gọi API thì nhận 403. Nhân viên kho không thấy menu Gọi xác nhận | |
| ED-15-AC6 (dữ liệu cá nhân) | Người có quyền gọi | xem | Số điện thoại hiện đủ và có nút gọi. Kết quả gọi ghi vào AuditLog không chép số điện thoại | bất biến 9 |

## ED-16 — [B6] Gán và đổi người giao cho phiếu giao · Must · BE
**Là** Quản lý, **tôi muốn** giao phiếu cho người giao, thấy mỗi người đang giao bao nhiêu phiếu, **để** chia việc đều.
Bối cảnh: 01-analysis B6. Field `DeliveryNote.assigned_to` đã có nhưng đang khoá, chỉ đổi được qua action nghiệp vụ (BR-PQ-14). Cần action mới và quyền Tầng 2 mới (đề xuất tên `assign_deliverynote`), vì Nhân viên giao đang có `change_deliverynote` để báo kết quả giao.

**Contract dự kiến:**
```
GET /api/delivery/shippers/
200 [{"id":21,"name":"Anh Phúc","delivering_count":0},{"id":22,"name":"Anh Lâm","delivering_count":2}]
POST /api/delivery/notes/{id}/assign/  {"assigned_to":21}
200 {...phiếu giao..., "assigned_to":21, "assigned_to_name":"Anh Phúc"}
400 {"detail":"Phiếu đang giao, không đổi người giao được."}
400 {"assigned_to":["Người này không thuộc nhóm Nhân viên giao hoặc đã nghỉ."]}
403 {"detail":"Bạn không có quyền giao việc cho người giao."}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-16-AC1 | Phiếu ở Chờ xác nhận, Soạn hàng hoặc Chờ lấy hàng, người làm là Quản lý | assign cho Anh Phúc | Nhận 200. Anh Phúc thấy phiếu trong danh sách của mình. AuditLog ghi "ai giao phiếu nào cho ai" | BR-GH-01, BR-PQ-04 |
| ED-16-AC2 | Phiếu đã giao cho Anh Lâm | đổi sang Anh Phúc | Anh Lâm gọi GET phiếu thì nhận 404. Anh Phúc thấy phiếu | BR-PQ-12 |
| ED-16-AC3 (lỗi) | Phiếu ở Đang giao, Hoàn tất hoặc Đã huỷ theo đơn | assign | Nhận 400, người giao không đổi. Trường hợp phiếu Giao thất bại: xem câu hỏi Q7 | BR-GH |
| ED-16-AC4 (lỗi) | `assigned_to` là người đã nghỉ hoặc không ở nhóm `nv_giao` | assign | Nhận 400 | |
| ED-16-AC5 | Anh Lâm có 2 phiếu Đang giao và 1 phiếu Hoàn tất | GET shippers | `delivering_count`=2. Danh sách chỉ có người đang làm thuộc nhóm `nv_giao`. Response không có số điện thoại nhân viên | |
| ED-16-AC6 (quyền) | Token Nhân viên giao, Nhân viên kho, CSKH | assign | Nhận 403, dữ liệu không đổi | BR-PQ |

## ED-17 — Giao hàng: danh sách, chi tiết phiếu giao, in tem, giao cho người giao · Must · FE
**Là** Nhân viên kho hoặc Quản lý, **tôi muốn** đưa phiếu giao qua các bước soạn, in tem, gán người giao, **để** hàng ra cửa đúng lúc.
Design: `ERP-W1d`, `ERP-W1d2`, `ERP-W2e`, `ERP-F2o`. Phụ thuộc ED-16 (B6) và ED-18 (hiện lý do thất bại).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-17-AC1 | Danh sách | xem | Chip theo `DeliveryNote.status`. Cột Tem ghi "Chưa in tem" hoặc "Đã in (lần N)". Người giao là cột riêng | §1.1 |
| ED-17-AC2 | Phiếu Soạn hàng | xem chi tiết | Thanh trạng thái: Chờ xác nhận → Soạn hàng → Chờ lấy hàng → Đang giao → Hoàn tất. Tiếp theo: "In tem, đóng gói, rồi bấm Đã đóng gói…". Nút chính là "In tem" và "Đã đóng gói" | BR-GH |
| ED-17-AC3 | Phiếu chưa in tem | mở "…" | "In lại tem" mờ, lý do "Chưa in tem lần nào.". Có "Huỷ xác nhận đơn" (lý do "Đưa đơn về Gọi xác nhận.") và "Huỷ đơn" (lý do "Mở đơn để huỷ và hoàn tiền cho khách.") | |
| ED-17-AC4 | Quản lý sửa trường Người giao | mở Giao cho người giao | Hộp thoại nổi trên Chi tiết phiếu giao. Mỗi người là một dòng có cột "Đang giao n phiếu". Nút "Giao phiếu". Thành công thì trường Người giao đổi, hiện toast | BR-GH-01 |
| ED-17-AC5 | Phiếu Giao thất bại | xem chi tiết | Lý do giao thất bại, Ghi chú và Lần giao thất bại là 3 trường riêng. Bước cuối của thanh trạng thái màu đỏ | BR-GH-04 |
| ED-17-AC6 | In tem (`ERP-W2e`) | in lại | Phải chọn lý do in lại. Tem cũ bị huỷ. Tình trạng tem thành "Đã in (lần 2)" | BR-GH |
| ED-17-AC7 (giá vốn) | Nhân viên kho | xem bảng "Hàng soạn theo lô" | Bảng chỉ có Mặt hàng · Kho · Lô xuất · Hạn dùng · Số kg, không có cột tiền vốn | bất biến 1 |
| ED-17-AC8 (quyền) | Nhân viên kho | xem trường Người giao | Không có bút chì sửa. Nhân viên giao không có menu Giao hàng | BR-PQ |

## ED-18 — [B5] Lý do giao thất bại · Must · BE
**Là** Quản lý, **tôi muốn** biết vì sao giao thất bại, **để** quyết định giao lại hay huỷ.
Bối cảnh: 01-analysis B5. Hiện `mark_failed` không nhận lý do. Thêm field vào `DeliveryNote` (lý do có trong 01-analysis, đã được duyệt) và migration. Đề xuất mã rule mới **BR-GH-mới** "Báo giao thất bại phải có lý do". Tech Lead lấy số kế tiếp khi ghi vào spec.

Enum đề xuất `FailReason`: `CUSTOMER_ABSENT` Không gặp khách · `REFUSED` Khách từ chối nhận · `WRONG_ADDRESS` Sai địa chỉ · `DAMAGED` Hàng hư khi giao · `OTHER` Khác.

**Contract dự kiến** (mở rộng action đang có):
```
POST /api/delivery/notes/{id}/status/
{"to_status":"FAILED","from_status":"DELIVERING","failed_reason":"CUSTOMER_ABSENT","failed_note":"Gọi 3 lần không nghe máy"}
200 {...,"status":"FAILED","failed_attempts":1,"failed_reason":"CUSTOMER_ABSENT",
     "failed_reason_label":"Không gặp khách","failed_note":"Gọi 3 lần không nghe máy","needs_decision":false}
400 {"failed_reason":["Chọn lý do giao thất bại."]}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-18-AC1 | Phiếu Đang giao của Anh Phúc | Anh Phúc báo FAILED có lý do | Nhận 200. Phiếu lưu lý do và ghi chú, `failed_attempts` tăng 1. AuditLog ghi mã lý do | BR-GH-04, BR-GH-mới |
| ED-18-AC2 (lỗi) | Thiếu `failed_reason` hoặc giá trị không có trong enum | gửi | Nhận 400, trạng thái không đổi | BR-GH-mới |
| ED-18-AC3 | Phiếu thất bại lần 2 | GET chi tiết | Trả lý do của lần gần nhất. Dòng thời gian (AuditLog) có lý do của từng lần | BR-GH-04 |
| ED-18-AC4 (quyền) | Anh Lâm báo thất bại cho phiếu của Anh Phúc | gửi | Nhận 404, không đổi dữ liệu | BR-PQ-12 |
| ED-18-AC5 (dữ liệu cá nhân) | Ghi chú có thể chứa số điện thoại hay địa chỉ | báo thất bại | AuditLog, logger và Sentry chỉ ghi mã phiếu và mã lý do, không chép `failed_note` | bất biến 9 |
| ED-18-AC6 | Client cũ gọi `to_status=FAILED` không có lý do | trong thời gian chuyển đổi | Vẫn nhận 400. FE cũ và mới được deploy cùng lúc (ghi rủi ro) | |

## ED-19 — Việc giao của tôi · Must · FE
**Là** Nhân viên giao, **tôi muốn** thấy phiếu của mình theo việc cần làm và báo kết quả nhanh, **để** giao xong chuyến không rối.
Design: `ERP-W1e`, `ERP-F2l` (dùng hộp thoại ở cuối file, có 5 lý do). Phụ thuộc ED-18.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-19-AC1 | Anh Phúc có phiếu ở nhiều trạng thái | mở màn | Các nhóm theo thứ tự: Đang giao · Chờ lấy hàng · Giao thất bại · Đã xong. Mỗi thẻ gồm Người nhận, Đơn, Địa chỉ, Số kg, Hàng, mỗi trường một giá trị. Đơn đã thanh toán có dòng "Đã thanh toán, không thu thêm" | BR-GH |
| ED-19-AC2 | Phiếu Chờ lấy hàng | bấm "Đã lấy hàng, bắt đầu giao" | Phiếu chuyển sang Đang giao, thời điểm "Bắt đầu giao" được ghi | BR-GH |
| ED-19-AC3 | Phiếu Đang giao | bấm "Giao thất bại" | Hộp thoại "Báo giao thất bại" nổi trên Việc giao của tôi. Khối tóm tắt: Phiếu giao, Đơn, Khách hàng, Bắt đầu giao. Lý do* là một trong 5 lựa chọn. Ghi chú không bắt buộc. Nút: Quay lại · Báo giao thất bại | BR-GH-04 |
| ED-19-AC4 (lỗi) | Chưa chọn lý do | bấm Báo giao thất bại | Ô Lý do viền đỏ, báo "Chọn lý do giao thất bại.". Không gọi API | |
| ED-19-AC5 | Phiếu Giao thất bại | xem thẻ | Lý do · Lần thất bại · Lúc là 3 trường riêng. Có nút Giao lại và Mang hàng về kho | BR-HV |
| ED-19-AC6 (quyền) | Anh Phúc | mở URL phiếu của Anh Lâm | Ra màn "Không tìm thấy trang này" | BR-PQ-12 |
| ED-19-AC7 (dữ liệu cá nhân) | Thẻ phiếu | xem | Số điện thoại hiện đủ trên nút gọi (quyết định 14). Không lưu dữ liệu khách vào `localStorage` để dùng offline | bất biến 9 |

---

# D. Hàng hoá & kho

## ED-20 — Mua hàng: danh sách, chi tiết phiếu nhập, nhập lô tại cảng, thêm chi phí phụ · Must · FE
**Là** Nhân viên kho, **tôi muốn** nhập lô ngay tại cảng, **để** hàng lên hệ thống trước khi về kho.
Design: `ERP-W2a`, `ERP-W2b`, `ERP-F1a` (trang riêng), `ERP-F1d` (trang riêng, mở từ phiếu nhập).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-20-AC1 | Danh sách | xem | Chip Nháp · Đã ghi nhận · Đã huỷ. Mã phiếu theo §1.4. Cột Tiền mua có icon khoá | BR-MH |
| ED-20-AC2 | Nhập lô tại cảng | thêm 3 dòng (mặt hàng, số kg, giá mua/kg, hạn dùng) rồi lưu | Lô được tạo, toast hiện. Bấm lưu 2 lần chỉ tạo 1 phiếu (gửi `idempotency_key`) | BR-MH, BR-LO |
| ED-20-AC3 (lỗi) | Số kg bằng 0 | lưu | Ô báo "Nhập số kg lớn hơn 0.", giữ nguyên các dòng khác | BR-MH |
| ED-20-AC4 | Chủ thêm chi phí phụ cho phiếu | chia theo số kg mà tổng phần chia lệch tổng tiền | Alert đỏ "Tổng tiền chia phải bằng 1.200.000 đ, còn thiếu 50.000 đ.". Nút "Lưu chi phí" bị khoá | BR-GV |
| ED-20-AC5 (giá vốn) | Nhân viên kho đã lưu phiếu | mở lại chi tiết phiếu | Không thấy giá mua, tiền mua hay giá vốn. Response API không có `rate` (Nhân viên kho được nhập giá mua nhưng không đọc lại được) | bất biến 1 |
| ED-20-AC6 (quyền) | Quản lý và Nhân viên kho | xem chi tiết phiếu | Không có "Thêm chi phí phụ". Gọi `purchasing/costs` thì nhận 403 | `add_purchasecost` |

## ED-21 — [B3] Số liệu tổng hợp nhà cung cấp · Must · BE
**Là** Chủ, **tôi muốn** thấy mỗi nhà cung cấp đã bán cho vựa bao nhiêu phiếu, bao nhiêu tiền và lần gần nhất khi nào, **để** chọn mối mua.
Bối cảnh: 01-analysis B3. `Supplier` đã đủ field, không thêm field mới. Chỉ thêm trường tính toán và các danh sách liên quan.

**Contract dự kiến:**
```
GET /api/purchasing/suppliers/?search=&is_active=true
200 [{"id":7,"name":"Ghe Tư Hải","supplier_type":"INDIVIDUAL","phone":"0900000907","is_active":true,
      "note":"…","receipt_count":4,"last_receipt_at":"2026-09-29T05:40:00+07:00","total_purchase_amount":"14326000"}]
GET /api/purchasing/suppliers/7/
200 {...,"receipts":[{"id":103,"received_at":"…","item_names":["Cá bớp cắt khúc"],"qty_kg":"12.000","amount":"1896000","status":"DRAFT"}],
     "selling_batches":[{"batch_id":"…","item_name":"Cá thu phi lê","qty_available":"18.500","expiry_date":"2026-10-05","status":"NEAR_EXPIRY"}]}
```
Người không có `view_costprice`: không có key `total_purchase_amount` và `receipts[].amount`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-21-AC1 | Nhà cung cấp có 3 phiếu Đã ghi nhận, 1 phiếu Nháp, 1 phiếu Đã huỷ | GET | Số phiếu, tổng tiền và lần gần nhất tính theo quy tắc chốt ở câu hỏi Q4. Mặc định: chỉ tính phiếu Đã ghi nhận. Tiền là Decimal | BR-MH, bất biến 7 |
| ED-21-AC2 (giá vốn) | Token Nhân viên kho | GET danh sách và chi tiết | Nhận 200 nhưng không có `total_purchase_amount` và `amount` | bất biến 1 |
| ED-21-AC3 (lỗi) | Nhà cung cấp chưa có phiếu nào | GET | `receipt_count`=0, `last_receipt_at`=null, `total_purchase_amount`="0" | |
| ED-21-AC4 (quyền) | Token Nhân viên giao, CSKH | GET | Nhận 403 | BR-PQ |
| ED-21-AC5 | Danh sách có 50 nhà cung cấp | GET | Số câu query không tăng theo số dòng (test `assertNumQueries`) | |

## ED-22 — Nhà cung cấp: danh sách, chi tiết, thêm · Must · FE
Design: `ERP-W5c`, `ERP-W5d`, `ERP-F1b`. Phụ thuộc ED-21.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-22-AC1 | Danh sách | xem | Chip Đang hợp tác / Ngừng hợp tác. Loại là Cá nhân / Doanh nghiệp. Có cột Số phiếu nhập, Lần nhập gần nhất, Tổng tiền mua (icon khoá) | |
| ED-22-AC2 | Chi tiết | xem | Không có thanh trạng thái. Thông tin gồm Tên, Loại, Số điện thoại, Ghi chú (sửa được) và khối Mua hàng (chỉ đọc). Có bảng Phiếu nhập, bảng Lô đang bán, Dòng thời gian. "…" có "Ngừng hợp tác" và "Xem nhật ký" | |
| ED-22-AC3 | Thêm nhà cung cấp (hộp thoại trên danh sách) | lưu | Dòng mới hiện trong danh sách, có toast | |
| ED-22-AC4 (lỗi) | Bỏ trống Tên | lưu | Ô Tên viền đỏ, báo "Nhập tên nhà cung cấp." | |
| ED-22-AC5 | Ngừng hợp tác | xác nhận | Chip đổi. Nhà cung cấp không còn trong danh sách chọn của form Nhập lô. Bản ghi không bị xoá | BR-PQ-10 |
| ED-22-AC6 (giá vốn) | Nhân viên kho | xem danh sách và chi tiết | Không có cột hay trường Tổng tiền mua, Tiền mua | bất biến 1 |

## ED-23 — Kho & lô: tồn theo lô và chi tiết lô · Must · FE
**Là** Quản lý, **tôi muốn** thấy lô nào sắp hết hạn, đã giữ chỗ bao nhiêu, **để** đẩy hàng kịp.
Design: `ERP-D3` (tab Tồn theo lô), `ERP-W2f`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-23-AC1 | Danh sách | xem | Có tab Tồn theo lô · Điều chỉnh tồn · Kho. Chip theo `Batch.status`. Tồn và Giữ chỗ là hai cột số kg riêng. Hạn dùng là ngày thuần | BR-LO |
| ED-23-AC2 | Chi tiết lô Cận hạn | xem | Thanh trạng thái: Nháp → Đang bán → Cận hạn → Hết hàng → Đã chốt (Quá hạn và Đã huỷ màu đỏ). Có các bảng Nhập xuất của lô, Đơn lấy hàng từ lô và khối AI | BR-LO |
| ED-23-AC3 | Lô Cận hạn còn 18,5 kg | mở "…" | "Trả nhà cung cấp" và "Huỷ phần tồn, ghi lỗ" mờ, lý do "Lô chưa quá hạn.". "Chốt lô" mờ, lý do "Lô còn 18,5 kg." | BR-LO |
| ED-23-AC4 (giá vốn) | Quản lý | xem chi tiết lô | Không có Giá mua/kg, Chi phí phụ/kg, Giá vốn/kg. Response `inventory/batches/{id}` không có `purchase_rate`, `landed_unit_cost` | bất biến 1 |
| ED-23-AC5 (quyền) | Nhân viên giao | mở URL Kho & lô | Ra màn "Không có quyền" | BR-PQ |

## ED-24 — Thao tác lô: mở bán, trả nhà cung cấp, huỷ phần tồn, chốt lô · Must · FE
Design: `ERP-F1e`, `ERP-F1g`, `ERP-F1h`, `ERP-F1i`. Tất cả là hộp thoại nổi trên Chi tiết lô.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-24-AC1 | Lô Nháp, người làm là Quản lý | Mở bán lô | Có khối tóm tắt (giá Shop, số kg). Lô chuyển sang Đang bán | BR-LO, `publish_batch` |
| ED-24-AC2 | Lô Quá hạn | Trả nhà cung cấp hoặc Huỷ phần tồn, ghi lỗ | Có bước xác nhận nêu hậu quả. Sổ nhập xuất có dòng "Trả nhà cung cấp" hoặc "Ghi lỗ, huỷ hàng" | BR-LO, BR-KK |
| ED-24-AC3 (lỗi) | Lô Hết hàng nhưng chưa có hoá đơn mua | mở "…" | "Chốt lô" mờ kèm lý do. Gọi API chốt lô thì nhận 400 | BR-GV |
| ED-24-AC4 | Chủ chốt lô | xác nhận | Khối tóm tắt có lãi lỗ lô (icon khoá). Thao tác không hoàn tác được nên có bước xác nhận | BR-LO, BR-BC |
| ED-24-AC5 (quyền) | Quản lý | xem "…" của lô Hết hàng | Không có mục Chốt lô | `close_batch` |
| ED-24-AC6 (quyền) | Nhân viên kho | xem lô Nháp | Không có nút Mở bán lô | `publish_batch` |

## ED-25 — Điều chỉnh tồn và Kho · Should · FE
Design: `ERP-W5k`, `ERP-F1j`, `ERP-W5l`, `ERP-F3m`. Ưu tiên Should vì ít dùng hằng ngày.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-25-AC1 | Tab Điều chỉnh tồn | xem | Mục đích là Nhập vật tư / Điều chỉnh. Lý do ở cột riêng | |
| ED-25-AC2 (lỗi) | Form Điều chỉnh tồn (hộp thoại) | bỏ trống Lý do | Báo "Nhập lý do điều chỉnh." | |
| ED-25-AC3 | Tab Kho | Thêm kho | Chọn Kho hoặc Nhóm kho. Kho mới hiện trong danh sách | |
| ED-25-AC4 (quyền) | Nhân viên giao, CSKH | mở tab | Ra màn "Không có quyền" | BR-PQ |

## ED-26 — Hàng hoàn về kho · Must · FE
Design: `ERP-W5e`, `ERP-W5f`, `ERP-F2m`, `ERP-F2n`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-26-AC1 | Danh sách | xem | Chip Chờ duyệt / Đã duyệt. Quyết định (Chờ quyết định · Tái nhập · Huỷ bỏ, ghi lỗ) ở cột riêng. Có cột "Ghi chú", không có cột "Lý do" | §1.3 |
| ED-26-AC2 | Nhân viên kho | Nhập hàng hoàn về kho (hộp thoại trên danh sách) | Phiếu mới ở trạng thái Chờ duyệt | BR-HV |
| ED-26-AC3 | Quản lý | Duyệt hàng hoàn: chọn Tái nhập | Chip đổi thành Đã duyệt. Sổ nhập xuất có dòng "Hàng hoàn tái nhập" | BR-HV |
| ED-26-AC4 (lỗi) | Phiếu đã được người khác duyệt | bấm Duyệt | Banner xung đột (ED-03-AC5) | |
| ED-26-AC5 (quyền) | Nhân viên kho | mở phiếu Chờ duyệt | Không có nút Duyệt. Gọi API thì nhận 403 | BR-PQ |

## ED-27 — [B1] Gửi được số đếm kiểm kê · Must · BE
**Là** Nhân viên kho, **tôi muốn** nhập số đếm theo từng lô qua API, **để** màn Kiểm kê chạy được.
Bối cảnh: 01-analysis B1. Hiện serializer để `lines` chỉ đọc. Không thêm field mới. `system_qty` và `difference_qty` do server tính, client gửi lên thì bỏ qua.

**Contract dự kiến** (tên trường phiếu theo model, Tech Lead chốt ở 02b):
```
POST /api/inventory/reconciliations/
{"warehouse":3,"posting_date":"2026-10-01","note":"Đếm lại tủ đông số 2",
 "lines":[{"batch":41,"counted_qty":"18.300","reason":"Hao hụt đông lạnh"}]}
201 {"id":15,"status":"DRAFT","lines":[{"id":88,"batch":41,"batch_code":"…","item_name":"Cá thu phi lê",
     "system_qty":"18.500","counted_qty":"18.300","difference_qty":"-0.200","reason":"Hao hụt đông lạnh"}]}
PATCH /api/inventory/reconciliations/15/  {"lines":[...]}   → thay toàn bộ dòng, chỉ khi DRAFT
400 {"lines":[{"counted_qty":["Nhập số kg từ 0 trở lên."]}]}
400 {"detail":"Phiếu đã duyệt, không sửa được."}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-27-AC1 | Nhân viên kho, lô có tồn hệ thống 18,5 kg | POST một dòng đếm 18,3 | Nhận 201, `system_qty`=18.500 (server tự chụp lúc nhập), `difference_qty`=-0.200, trạng thái DRAFT. Kho không đổi khi phiếu chưa duyệt | BR-KK-01 |
| ED-27-AC2 (lỗi) | Dòng có chênh lệch dương mà không có lý do | gửi | Nhận 400 | BR-KK-04 |
| ED-27-AC3 (lỗi) | Phiếu APPROVED | PATCH | Nhận 400, dữ liệu không đổi | BR-PQ-10 |
| ED-27-AC4 (lỗi) | `counted_qty` âm, hoặc lô không thuộc kho của phiếu, hoặc 1 lô lặp 2 dòng | gửi | Nhận 400, thông điệp tiếng Việt chỉ đúng dòng sai | BR-KK |
| ED-27-AC5 (quyền) | Token Nhân viên giao, CSKH | POST | Nhận 403 | BR-PQ |
| ED-27-AC6 (giá vốn) | Token Nhân viên kho | GET phiếu | Không có giá trị tiền của chênh lệch (nếu API có trả giá trị này) | bất biến 1 |

## ED-28 — Kiểm kê: danh sách, chi tiết, nhập số kiểm kê · Must · FE
Design: `ERP-W2c`, `ERP-W2g`, `ERP-F1f` (trang riêng). Phụ thuộc ED-27.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-28-AC1 | Danh sách | xem | Chip Chờ duyệt / Đã duyệt. Nút tạo mới ghi "Lập phiếu kiểm kê" | §3.4 |
| ED-28-AC2 | Nhập số kiểm kê | xem bảng | Cột: Lô · Mặt hàng · Tồn trên hệ thống (kg) · Đếm được (kg)* · Chênh lệch (kg) · Lý do. Chênh lệch tự tính ngay khi gõ | §3.4 |
| ED-28-AC3 | Có dòng chưa nhập số đếm | bấm "Lưu nháp" | Lưu được. Bấm "Gửi duyệt" thì báo dòng còn thiếu. Cả hai nút đều không tạo trạng thái mới, phiếu vẫn là Chờ duyệt | §1.3 |
| ED-28-AC4 (lỗi) | Dòng lệch 4,25 kg chưa chọn lý do | Gửi duyệt | Báo "Chọn lý do cho lô lệch 4,25 kg." dưới dòng đó. Phạm vi bắt buộc lý do theo câu hỏi Q3 | BR-KK-04 |
| ED-28-AC5 | Quản lý | Duyệt trên Chi tiết kiểm kê | Chip đổi thành Đã duyệt. Sổ nhập xuất có dòng "Điều chỉnh kiểm kê" | BR-KK |
| ED-28-AC6 (quyền) | Nhân viên kho | mở phiếu Chờ duyệt | Không có nút Duyệt | BR-KK |

## ED-29 — Sổ nhập xuất · Should · FE
Design: `ERP-W5i`. Ưu tiên Should vì là màn tra cứu.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-29-AC1 | Sổ | xem | Cột: Thời gian · Loại · Lô · Mặt hàng · Thay đổi (kg) · Tồn sau (kg) · Chứng từ · Người làm. WRITE_OFF hiện "Ghi lỗ, huỷ hàng". Người làm là "Hệ thống" khi không có người thao tác | BR-PQ-11 |
| ED-29-AC2 | Lọc theo khoảng ngày, lô, loại, kho | áp dụng | "Đang hiện x / y dòng" đúng với bộ lọc | |
| ED-29-AC3 | Mọi dòng | xem | Không có nút sửa hay xoá (sổ chỉ ghi thêm) | bất biến 4 |
| ED-29-AC4 (quyền) | Nhân viên giao | mở URL | Ra màn "Không có quyền" | |

## ED-30 — Danh mục & giá: mặt hàng · Must · FE
Design: `ERP-W2d` (tab Mặt hàng), `ERP-W2h`, `ERP-F1k` (trang riêng), `ERP-F1n`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-30-AC1 | Danh sách | xem | Có tab Mặt hàng · Bảng giá · Ưu đãi · Nhóm hàng. Loại là Mặt hàng thường / Combo. Trạng thái là Đang kinh doanh / Đang ẩn | BR-DM |
| ED-30-AC2 | Chi tiết mặt hàng | xem | Không có thanh trạng thái. Bảng lịch sử giá không có cột Trạng thái hay Ghi chú (enum-map) | |
| ED-30-AC3 | Thêm mặt hàng loại Combo | lưu khi chưa có dòng công thức | Báo "Thêm ít nhất một mặt hàng vào công thức." | BR-DM |
| ED-30-AC4 (lỗi) | Đổi ảnh mặt hàng (hộp thoại) | tải ảnh sai định dạng hoặc quá dung lượng | Báo lỗi nói rõ định dạng và dung lượng cho phép. Ảnh cũ giữ nguyên | |
| ED-30-AC5 (giá vốn) | Quản lý | xem chi tiết mặt hàng | Không có giá vốn các lô | bất biến 1 |

## ED-31 — Danh mục & giá: bảng giá, ưu đãi, nhóm hàng · Must · FE
Design: `ERP-W5o`, `ERP-F1l`, `ERP-W5h`, `ERP-F1m` (trang riêng), `ERP-W5m`, `ERP-F1o`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-31-AC1 | Chủ | Đặt giá mới (hộp thoại trên Bảng giá) có ngày bắt đầu | Giá mới hiện trong bảng. Giá cũ có ngày kết thúc. Bảng giá không có cột Trạng thái | BR-DM |
| ED-31-AC2 | Tạo ưu đãi | chọn Theo mặt hàng (mua ≥ N kg) hoặc Theo đơn (tổng ≥ M đồng), Giảm số tiền hoặc Giảm phần trăm | Lưu được. Chip là Đang bật / Đã tắt | BR-DM |
| ED-31-AC3 (lỗi) | Giảm phần trăm lớn hơn 100, hoặc ngày kết thúc trước ngày bắt đầu | lưu | Ô báo lỗi nói cách sửa | |
| ED-31-AC4 | Thêm nhóm hàng | lưu | Nhóm mới có trong danh sách chọn của form Thêm mặt hàng | |
| ED-31-AC5 (quyền) | Quản lý | mở Bảng giá | Không có "Đặt giá mới". Gọi API thì nhận 403 (theo `ERP-W3h`, Sửa giá bán chỉ có Chủ) | BR-DM, BR-PQ |

---

# E. Kế toán

## ED-32 — Báo cáo lãi lỗ · Must · FE
Design: `ERP-W3a`. API có sẵn: `reports/period/`, `reports/batch/{id}/`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-32-AC1 | Chủ | chọn kỳ | Doanh thu, giá vốn và lãi gộp khớp API, tiền là Decimal, các số liệu có icon khoá | BR-BC |
| ED-32-AC2 | Kỳ không có giao dịch | chọn | Hiện trạng thái trống (ED-03-AC1), không hiện số 0 giả | |
| ED-32-AC3 (quyền) | Quản lý, Nhân viên kho | mở URL | Ra màn "Không có quyền". API trả 403 | `view_profitreport` |

## ED-33 — Hoá đơn bán · Should · FE
Design: `ERP-W5j`. Ưu tiên Should vì là màn tra cứu, hoá đơn do hệ thống tạo.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-33-AC1 | Danh sách | xem | Cột: Mã hoá đơn (`INV…`) · Đơn · Khách hàng · Ngày xuất · Số tiền · Giá vốn (khoá) · Lãi gộp (khoá) · Trạng thái (Đã xuất / Đã huỷ). Bấm dòng mở Chi tiết đơn tương ứng | |
| ED-33-AC2 | Mọi vai | xem màn | Không có nút tạo hoá đơn | BR-PQ-11 |
| ED-33-AC3 (giá vốn) | Quản lý | xem | Không có cột Giá vốn và Lãi gộp. Response không có các key đó | bất biến 1 |
| ED-33-AC4 (quyền) | Nhân viên kho, Nhân viên giao | mở URL | Ra màn "Không có quyền" | |

## ED-34 — Hoá đơn mua và chi phí phụ · Should · FE
Design: `ERP-W5g` (tab Hoá đơn mua), `ERP-W5g2` (tab Chi phí phụ), `ERP-F1c`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-34-AC1 | Tab Hoá đơn mua | xem | Mã hiện `#<id>`. Trạng thái Đã trả tiền / Chưa trả tiền. "Trả lúc" là cột riêng. Số tiền có icon khoá | §1.4 |
| ED-34-AC2 | Thêm hoá đơn mua (hộp thoại trên danh sách) | bật "Đã trả tiền" | Hiện ô "Trả lúc" (dd/mm/yyyy hh:mm). Lưu xong dòng mới có trong bảng | BR-MH-04 |
| ED-34-AC3 (lỗi) | Bỏ trống Số tiền hoặc Ngày hoá đơn | lưu | Ô báo lỗi | |
| ED-34-AC4 | Tab Chi phí phụ | xem | Loại là Đá · Vận chuyển · Bốc vác · Khác. Cách chia là Theo số kg / Theo giá trị | BR-GV |
| ED-34-AC5 (giá vốn) | Nhân viên kho | mở màn | Không có cột Số tiền. Tab Chi phí phụ ẩn. API không trả số tiền | bất biến 1, BR-PQ-16 |

---

# F. Website

## ED-35 — Nội dung: danh sách, viết bài, thiết lập, kiểm tra, trả về nháp, gỡ bài · Should · FE
Design: `ERP-W3b`, `ERP-W3c`, `ERP-F3l` (trang riêng), `ERP-F3k`, `ERP-F3i`, `ERP-F3j`. Ưu tiên Should vì không chặn bán hàng.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-35-AC1 | Danh sách | xem | Chip Nháp · Chờ duyệt · Đã đăng · Đã gỡ. Loại là Bài viết / Trang. Bài do AI viết có chip "AI" ở cột riêng | |
| ED-35-AC2 | Thiết lập bài viết | xem nhãn | Dùng chữ "Đường dẫn", "Tóm tắt", "Chân trang", không dùng slug, excerpt, footer | §3.2 |
| ED-35-AC3 | Chủ bấm Đăng | Kiểm tra trước khi đăng | Hộp thoại liệt kê các mục chưa đạt. Còn mục chưa đạt thì nút Đăng bị khoá | |
| ED-35-AC4 | Chủ, bài Chờ duyệt | Trả về nháp | Lý do chọn từ Thiếu thông tin, hình ảnh · Nội dung chưa chuẩn, cần sửa · Rủi ro pháp lý, bản quyền · Khác | |
| ED-35-AC5 | Chủ, bài Đã đăng | Gỡ bài | Nút đỏ, có lý do (Giá chưa đúng · Khiếu nại / rủi ro pháp lý · Hết mùa vụ · Nội dung chưa chuẩn · Khác). Bài chuyển sang Đã gỡ, không bị xoá | BR-PQ-10 |
| ED-35-AC6 (quyền) | Quản lý | mở bài | Viết và sửa được, không có nút Đăng hay Gỡ bài | |

## ED-36 — Chuyên mục · Should · FE
Design: `ERP-W3d`, `ERP-F3h`.

| Mã | Given | When | Then |
|---|---|---|---|
| ED-36-AC1 | Danh sách | xem | Chip Đang hoạt động / Ngừng dùng |
| ED-36-AC2 | Thêm chuyên mục (hộp thoại) | lưu | Chuyên mục mới có trong danh sách chọn của Thiết lập bài viết |
| ED-36-AC3 (lỗi) | Tên trùng với chuyên mục đã có | lưu | Ô báo lỗi |
| ED-36-AC4 (quyền) | Nhân viên kho | mở URL | Ra màn "Không có quyền" |

---

# G. Quản trị

## ED-37 — Nhân sự: danh sách, chi tiết, thêm nhân viên, tạo tài khoản Chủ · Must · FE
Design: `ERP-W3e`, `ERP-W3g`, `ERP-F3a`, `ERP-F3b`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-37-AC1 | Danh sách | xem | Lọc Đang làm · Đã nghỉ · Tất cả. Chip Đang làm / Đã nghỉ (không có "Mới tạo"). Nhóm là cột riêng | |
| ED-37-AC2 | Chủ | Thêm nhân viên (hộp thoại) | Tạo được tài khoản, chọn nhóm, tài khoản phải đặt mật khẩu ở lần đăng nhập đầu | BR-PQ-17 |
| ED-37-AC3 | Chủ | Tạo tài khoản nhóm Chủ | Có bước xác nhận riêng, nêu hậu quả (người này có toàn quyền) | BR-PQ-08 |
| ED-37-AC4 (lỗi) | Tên đăng nhập trùng | lưu | Ô báo lỗi, giá trị đã nhập còn nguyên | |
| ED-37-AC5 (quyền) | Quản lý | mở Nhân sự | Ra màn "Không có quyền", hoặc chỉ xem nếu ma trận cho phép. Không có nút Thêm. API trả 403 | `manage_staff` |

## ED-38 — Thao tác hồ sơ nhân viên: sửa, đổi nhóm, đặt lại mật khẩu, cho nghỉ · Must · FE
Design: `ERP-F3c`, `ERP-F3d`, `ERP-F3e`, `ERP-F3f`. Tất cả là hộp thoại nổi trên Chi tiết nhân viên.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-38-AC1 | Chủ | Đổi nhóm | Nhóm mới có hiệu lực từ lần gọi API kế tiếp. Dòng thời gian có dòng ghi việc đổi nhóm | BR-PQ-04 |
| ED-38-AC2 | Chủ | Đặt lại mật khẩu | Người đó phải đặt mật khẩu mới ở lần đăng nhập kế tiếp | BR-PQ-17 |
| ED-38-AC3 | Nhân viên giao đang có phiếu Đang giao | Cho nghỉ việc | Khối tóm tắt nêu số phiếu đang gán. Nút đỏ. Tài khoản bị khoá đăng nhập nhưng không bị xoá | BR-PQ-10, BR-GH-08 |
| ED-38-AC4 (lỗi) | Chủ tự cho mình nghỉ, hoặc đổi nhóm làm hệ thống không còn ai là Chủ | xác nhận | Bị chặn, có lý do | BR-PQ-18 |
| ED-38-AC5 (quyền) | Quản lý | xem chi tiết nhân viên | Không có các nút trên | `manage_staff` |

## ED-39 — [B4] Ma trận phân quyền đọc/ghi qua API · Must · BE
**Là** Chủ, **tôi muốn** bật/tắt từng việc cho từng nhóm trên màn, **để** không phải nhờ dev mỗi lần giao việc.
Bối cảnh: 01-analysis B4 ("kiểm lại nếu chưa có"). Nếu API đã có thì story này chỉ còn việc bổ sung test hợp đồng cho các AC dưới đây. Mỗi "việc" trên màn là một tập permission Django; bảng ánh xạ do Tech Lead ghi ở 02b. Việc "Chỉ Chủ" lấy theo `doc/decisions.md`: `close_batch`, `add_purchasecost`, `confirm_refund`, `confirm_payment_manual`, `manage_staff`, chính sách AI. Riêng Xem giá vốn và Xem lãi lỗ: xem câu hỏi Q2.

**Contract dự kiến:**
```
GET /api/permissions/matrix/
200 {"groups":[{"key":"quan_ly","name":"Quản lý","member_count":2,"updated_at":"…","updated_by":"Lộc"}],
     "actions":[{"key":"view_customer","label":"Xem khách hàng","area":"Bán hàng","owner_only":false}],
     "grants":{"quan_ly":["view_order","view_customer"]},
     "scopes":{"nv_giao":{"order":"assigned"}}}
PATCH /api/permissions/matrix/ {"group":"quan_ly","action":"view_customer","allowed":false}
200 {...ma trận mới...}
400 {"detail":"Việc này chỉ Chủ làm được."}   403 khi không có manage_staff
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-39-AC1 | Chủ | GET | Trả 5 nhóm (Chủ, Quản lý, Nhân viên kho, Nhân viên giao, CSKH) và quyền hiện tại khớp DB | BR-PQ |
| ED-39-AC2 | Chủ tắt Xem khách hàng của Quản lý | PATCH rồi Quản lý gọi `sales/customers` | Quản lý nhận 403. AuditLog ghi "Lộc tắt việc Xem khách hàng của nhóm Quản lý" | BR-PQ-04, quyết định 13 |
| ED-39-AC3 (lỗi) | Bật một việc có `owner_only` cho nhóm khác | PATCH | Nhận 400, không đổi dữ liệu | decisions 2026 (ranh Chủ ↔ Quản lý) |
| ED-39-AC4 (lỗi) | Sửa quyền của nhóm Chủ | PATCH | Nhận 400. Nhóm Chủ luôn có đủ quyền | BR-PQ |
| ED-39-AC5 (quyền) | Token Quản lý | PATCH | Nhận 403 | `manage_staff` |

## ED-40 — Phân quyền: ma trận và chi tiết nhóm quyền · Must · FE
Design: `ERP-W3h`, `ERP-W3i`. Phụ thuộc ED-39.

| Mã | Given | When | Then |
|---|---|---|---|
| ED-40-AC1 | Chủ | xem ma trận | Các việc chia theo khu Bán hàng · Hàng hoá & kho · Kế toán · Website · Quản trị. Việc "Chỉ Chủ" có icon khoá và không tick được ở nhóm khác. Nhân viên giao có ô "Được gán" ở các việc có giới hạn phạm vi |
| ED-40-AC2 | Chi tiết nhóm Quản lý | xem | Không có thanh trạng thái. Có Thông tin nhóm, bảng Thành viên (Họ tên · Tên đăng nhập · Nhóm khác · Trạng thái · Thêm vào lúc), bảng Việc được làm, bảng Phạm vi dữ liệu và Dòng thời gian |
| ED-40-AC3 | Chủ bật hoặc tắt một việc | bấm ô | Lưu ngay, có toast kèm "Hoàn tác". Dòng thời gian có dòng mới |
| ED-40-AC4 (lỗi) | Lưu thất bại | bấm ô | Ô trở về giá trị cũ, có toast lỗi |
| ED-40-AC5 (quyền) | Quản lý | mở URL Phân quyền | Ra màn "Không có quyền" |

## ED-41 — Nhật ký hoạt động · Should · FE
Design: `ERP-W3f`. API có sẵn: `audit-logs/`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-41-AC1 | Danh sách | xem | Cột người làm có loại Người / AI / Hệ thống. Thời gian theo G2. Tên việc dùng đúng §3.4 | BR-PQ-05 |
| ED-41-AC2 | Lọc theo người, loại, khoảng ngày | áp dụng | Kết quả đúng với bộ lọc | |
| ED-41-AC3 (dữ liệu cá nhân) | Nhật ký có việc đổi địa chỉ | xem | Chi tiết không có địa chỉ hay số điện thoại | bất biến 9 |
| ED-41-AC4 (quyền) | Vai không có quyền xem nhật ký (theo câu hỏi Q1) | mở URL | Ra màn "Không có quyền" | |

## ED-42 — Chính sách AI và Báo cáo AI · Should · FE
Design: `ERP-W4c`, `ERP-W4d`. API có sẵn: `ai/policy/*`, `ai/report/daily/`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| ED-42-AC1 | Chủ | đổi chế độ chung | Có 3 lựa chọn Bật · Luôn hỏi trước · Tắt. Không dùng chữ "Tắt khẩn" hay "Mức A/B/C" | §3.2 |
| ED-42-AC2 | Chủ | đổi mức AI của một người | Mức của người đó không vượt chế độ chung. Có phiên bản lịch sử | |
| ED-42-AC3 | Báo cáo AI cuối ngày | xem | Trạng thái của việc AI dùng nhãn `AiAction.status`. Thời gian theo G2 | |
| ED-42-AC4 (giá vốn) | Báo cáo AI nhắc tới giá vốn | Quản lý xem (nếu được xem) | Không có giá trị giá vốn | bất biến 1 |
| ED-42-AC5 (quyền) | Quản lý | mở Chính sách AI | Ra màn "Không có quyền" | `manage_ai_policy` |

---

## Thứ tự làm đề xuất

| Đợt | Story | Ai làm | Lý do |
|---|---|---|---|
| 1 | ED-02 → ED-01 → ED-05 → ED-04 → ED-03 | FE | Khung và mẫu chung. Mọi màn khác dựng trên đợt này |
| 1 (song song) | ED-27 (B1), ED-13 (B2), ED-21 (B3), ED-39 (B4), ED-18 (B5), ED-16 (B6) | BE | Đã có contract nên FE dựng mock được. Làm xong trước khi FE tới màn cần |
| 2 | ED-06, ED-08, ED-09, ED-10, ED-11, ED-12 | FE | Luồng tiền của đơn, quan trọng nhất |
| 3 | ED-14, ED-15, ED-17, ED-19 | FE | Cần B2, B5, B6 |
| 4 | ED-20, ED-22, ED-23, ED-24, ED-26, ED-28 | FE | Luồng kho. ED-22 cần B3, ED-28 cần B1 |
| 5 | ED-30, ED-31, ED-32, ED-25, ED-29 | FE | Danh mục, lãi lỗ, các màn tra cứu |
| 6 | ED-37, ED-38, ED-40 | FE | Quản trị, ED-40 cần B4 |
| 7 | ED-33, ED-34, ED-35, ED-36, ED-41, ED-42 | FE | Các story Should |
| 8 | ED-07 | FE | Could, chờ Duy trả lời Q6 |

## Rủi ro / phụ thuộc
- **B2 có thể làm hỏng màn giao hàng**: nếu gỡ `view_customer` khỏi `nv_giao`, màn nào đang đọc `sales/customers` sẽ lỗi. ED-13-AC7 bắt lỗi này, Tech Lead rà ở 02b.
- **B5 đổi contract** `status/`: FE và BE phải deploy cùng lúc (ED-18-AC6).
- **Xung đột khi sửa** (ED-03-AC5) cần API trả mã xung đột. Tech Lead chốt cơ chế (theo `updated_at` hay version). Màn nào API chưa hỗ trợ thì ghi rõ ở 02b, không giả lập.
- Thiết kế còn dữ liệu minh hoạ lệch code (mã `DH-`, mã lô, số điện thoại bị che). Đã nêu nguyên tắc ở đầu file, QA không bắt lỗi "khác thiết kế" ở những điểm này.
- Khối lượng lớn (42 story). Mỗi lô trong `02c-giao-viec.md` nên chỉ gồm 3–5 story FE để QA kiểm được bằng chạy thật.

## Để sau (ngoài phạm vi)
- ERP điện thoại (`ERP-M*`), giỏ hàng dạng ngăn kéo của Shop.
- Tìm toàn cục theo tên hoặc số điện thoại khách (đụng dữ liệu cá nhân, cần Duy duyệt riêng).
- Trang chi tiết hoá đơn bán và hoá đơn mua (thiết kế chưa vẽ).

## Câu hỏi cho Duy
- **Q1.** Nhật ký hoạt động: thiết kế chỉ cho Chủ xem, code hiện cho cả Quản lý. Giữ như code (mặc định) hay đổi theo thiết kế?
- **Q2.** Xem giá vốn và Xem báo cáo lãi lỗ: thiết kế không khoá, nghĩa là Chủ bật được cho nhóm khác. `decisions.md` xếp hai quyền này vào nhóm "Chủ giữ". Khoá "Chỉ Chủ" (mặc định) hay cho bật?
- **Q3.** Kiểm kê: thiết kế bắt chọn lý do cho mọi dòng lệch, kể cả hụt. BR-KK-04 chỉ bắt khi dư. Giữ BR-KK-04 (mặc định) hay siết theo thiết kế?
- **Q4.** Nhà cung cấp: Số phiếu, Tổng tiền mua và Lần nhập gần nhất có tính phiếu Nháp không? Số trên thiết kế đang cộng cả phiếu Nháp. Mặc định: chỉ tính phiếu Đã ghi nhận.
- **Q5.** Hộp thoại Báo giao thất bại có ô "Mang hàng về kho". Gộp luôn vào một bước, hay giữ nút "Mang hàng về kho" riêng như màn Việc giao của tôi (mặc định)?
- **Q6.** Ô tìm ⌘K: chỉ tìm theo mã chứng từ (mặc định), hay cần tìm theo tên mặt hàng hoặc lô?
- **Q7.** Phiếu Giao thất bại có cho đổi người giao trước khi giao lại không? Mặc định là có, vì đây là việc làm khách phải chờ nên Quản lý được làm.

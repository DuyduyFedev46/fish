# Rà soát giao diện ERP so với board thiết kế · 03/10/2026

Phạm vi: chỉ **hình thức** (chức năng đã có QA riêng). Không sửa code.
Nguồn so sánh: `doc/design/erp/screens/*.dc.html` (board, mở bằng Playwright `file://`) với bản mock build từ `main` (HEAD 00c67f4, có Lô 16 và thẻ Dòng thời gian mới e2e7b54), 1440x1000, giao diện sáng, đăng nhập mock `loc`, `ql1`, `kho1`, `giao1`, `giao2` (dữ liệu giả).
Ảnh: `shots/audit/board-<mã>.png` và `shots/audit/app-<mã>.png` (cùng thư mục với file này, tính từ `doc/features/2026-10-01-erp-theo-design/`).
Bỏ qua theo lời Duy: toàn chiều rộng (không còn là lệch), khác biệt dữ liệu, phần template `{{...}}`. Không rà Lô 15 (Tổng quan, AI, Nhật ký).

## Tổng kết

| Mức | Số lệch (đã gộp theo nhóm gốc) |
|---|---|
| Cao | 13 |
| Vừa | 21 |
| Thấp | 6 |
| Tổng | 40 |

Đã so sánh 61 cặp ảnh board/app (liệt kê ở cuối). Chưa so sánh bằng ảnh app: F1c, F1e, F1g–F1i, F1n, F1o, F2b, F2c, F2e–F2g, F2i–F2k, F2m–F2o, F3b–F3f, F3m (chỉ có ảnh board; xem mục "Chưa kiểm").

## Nhóm gốc, xếp theo mức ảnh hưởng (sửa một chỗ, hết nhiều màn)

| Nhóm | Component dùng chung nghi gây lệch | Màn bị ảnh hưởng | Mức |
|---|---|---|---|
| A | Khối danh sách (thẻ bọc bảng) + vị trí nút chính ở `PageHeader`/thanh lọc | 20+ màn danh sách | Cao |
| B | `shared/ui/detail/*` (`InfoGrid`, `DetailPage`, `.sectionH` bị chép lại ở từng module, `AiBlockFrame`) | 12 màn chi tiết | Cao |
| C | `shared/ui/form/FormPage` | F1a, F1d, F1f, F1k, F1m | Cao |
| D | `shared/ui/Modal` + `Field`/`.control` | mọi popup F* | Vừa |
| E | Khung đăng nhập (auth shell) | W4f, W4g, W4h | Vừa |
| F | Che số điện thoại (cần PO quyết) | W5a, W5b, W5c, W3e | Vừa |
| G | Màn theo vai (giao hàng, nhãn) | W1e, W2e | Cao |
| H | Nút chính thiếu icon `add` | W5g, W5g2, v.v. | Thấp |
| I | Ma trận quyền (Phân quyền) | W3h, W3i | Cao |
| J | Thanh KPI/báo cáo lãi lỗ | W3a | Cao |
| K | Trang Nội dung (Lô 16) | W3b, W3c, W3d | Cao |
| L | Trang Tài khoản của tôi | W4e | Vừa |

## Nhóm A — Màn danh sách thiếu thẻ có đầu 44px

Board: thẻ trắng, viền, bo góc, đầu thẻ 44px chứa tiêu đề + bộ đếm ("Đơn hàng · 128"), thanh tab/lọc ngay dưới đầu, nút chính nằm cùng hàng tab/lọc, chân bảng có phân trang. App: bảng đặt trần, không đầu thẻ, nút chính nằm một hàng riêng phía trên tab, tiêu đề cột dùng chữ mono, ô ngày là input native, nút "Tải thêm" thay phân trang.

| Màn | Board | Khối | Lệch | Mức | Component nghi ngờ | Ảnh |
|---|---|---|---|---|---|---|
| Đơn & tiền | D2 | Danh sách | Thiếu thanh AI; không đầu thẻ 44px + bộ đếm; dùng nút phân đoạn thay vì dropdown; thiếu số đếm trên tab; tiêu đề cột "Mã đơn" dạng mono; "Tải thêm"; SĐT hiện đủ | Cao | list card / `PageHeader` / `AiBar` (chỉ render khi count>0) | board-D2, app-D2 |
| Chi tiết đơn | D2b | Hàng & phân bổ lô, Thanh toán, Giao hàng, Dòng thời gian | Khối "Hàng & phân bổ lô" tách thành 2 bảng có tiêu đề caps ngoài thẻ; THANH TOÁN/GIAO HÀNG không tách caps trong thẻ; đầu AI viết caps; tiêu đề topbar bị thay bằng tên màn con | Cao | `InfoGrid`, `AiBlockFrame`, `.sectionH` (module orders) | board-D2b, app-D2b |
| Đơn & tiền (tab Hàng chờ thanh toán, Phiếu hoàn chờ chuyển, v.v.) | W1a, W1a2, W1b, W1b2, W1c, W1c2, W1d, W1d2 | Danh sách | Cùng mẫu A; W1b thiếu 3 thẻ KPI phía trên; W1d khác bộ cột | Cao | list card + `Tabs` | board-W1a… app-W1a… |
| Khách hàng | W2a | Danh sách | Mẫu A (nút chính riêng hàng, không đầu thẻ, mono) | Vừa | list card | board-W2a, app-W2a |
| Nhà cung cấp | W2c | Danh sách | Mẫu A | Vừa | list card | board-W2c, app-W2c |
| Giao hàng | W2d | Danh sách | Mẫu A, ô ngày native, "Tải thêm" | Vừa | list card, `DateField` | board-W2d, app-W2d |
| Mua hàng, Nhập lô | W5a | Danh sách | Mẫu A; SĐT NCC hiện đủ (board che) | Vừa | list card | board-W5a, app-W5a |
| Kho & lô | W5c, W5e | Danh sách | Mẫu A; cột thừa/thiếu; bộ lọc khác | Vừa | list card | board-W5c, board-W5e, app-W5c, app-W5e |
| Hàng hoàn về kho | W5g, W5g2 | Danh sách | Mẫu A; nút chính thiếu icon cộng; chip "Nhóm kho" khác màu; W5g2 dùng chip xám cho loại chi phí | Vừa | list card, `Chip` | board-W5g, board-W5g2, app-W5g, app-W5g2 |
| Kiểm kê, Sổ nhập xuất, Danh mục & giá, Hoá đơn | W5h, W5i, W5j, W5k, W5l, W5m, W5o | Danh sách | Mẫu A (nút chính riêng hàng, không đầu thẻ + bộ đếm, mono, ô ngày native, "Tải thêm"); W5k thiếu nút chính "Điều chỉnh tồn" (cũng ở F1j) | Vừa | list card | board-W5h…W5o, app-W5h…W5o, board-F1j, app-F1j |
| Cảnh báo/Quyền chọn | D3 | Danh sách | Mẫu A | Vừa | list card | board-D3, app-D3 |
| Nội dung (danh sách bài) | W3e | Danh sách | Mẫu A; SĐT hiện đủ | Vừa | list card | board-W3e, app-W3e |

## Nhóm B — Màn chi tiết: thẻ chia khối, `.sectionH` nằm ngoài thẻ

Board: mỗi khối là một thẻ có đầu 44px chứa tiêu đề (sentence case, đậm); cột phải có "Trợ lý AI" và "Dòng thời gian"; nút thao tác ở đầu trang. App: `InfoGrid` là thẻ có tiêu đề caps cỡ xs (không đầu 44px), một số khối dùng `.sectionH` caps nằm NGOÀI thẻ (chép lại ở orders, customers, suppliers, staff, permissions, catalog), thiếu rail AI và nút thao tác.

| Màn | Board | Khối | Lệch | Mức | Component nghi ngờ | Ảnh |
|---|---|---|---|---|---|---|
| Chi tiết Khách hàng | W2b | Thông tin, Dòng nhập | Thẻ caps không đầu; tiêu đề ngoài thẻ; thiếu rail AI + nút hành động; bảng "Dòng nhập" bị cắt ngang | Cao | `InfoGrid`, `.sectionH` | board-W2b, app-W2b |
| Chi tiết NCC | W2f | Khối thông tin | Như trên | Vừa | `InfoGrid`, `.sectionH` | board-W2f, app-W2f |
| Chi tiết Lô | W5b | Thông tin lô | Như trên; SĐT và địa chỉ hiện đủ (board che) | Cao | `InfoGrid`, `.sectionH` | board-W5b, app-W5b |
| Chi tiết Phiếu nhập | W5d | Khối thông tin | Như trên | Vừa | `InfoGrid`, `.sectionH` | board-W5d, app-W5d |
| Chi tiết Hoàn kho | W5f | Khối thông tin | Như trên | Vừa | `InfoGrid` | board-W5f, app-W5f |
| Chi tiết Nhân sự | W2g, W2h | Khối thông tin | Như trên | Vừa | `InfoGrid`, `.sectionH` | board-W2g, board-W2h, app-W2g, app-W2h |
| Chi tiết nhóm/nhân sự | W3g | Khối thông tin | Không so sánh được: mock id=5 là `admin` (không nhóm). Áp mẫu B theo quan sát cùng component | Thấp | `InfoGrid` | board-W3g, app-W3g |
| Chi tiết Chủ | W3i | Thông tin nhóm, Thành viên, Phạm vi dữ liệu, Lịch sử | App: tiêu đề caps ngoài thẻ, đoạn dẫn giải, bảng "Việc được làm" dùng nhãn "Được làm" thay ô bật; board là thẻ có đầu "Thông tin nhóm / Thành viên / Phạm vi dữ liệu / Dòng thời gian". Chủ khác nhóm Quản lý nên chỉ so khung | Cao | `InfoGrid`, `.sectionH`, ma trận (nhóm I) | board-W3i, app-W3i |

## Nhóm C — Màn biểu mẫu (`FormPage`)

Board: thẻ trắng có đầu từng khối, ô nhập 36px, công tắc/radio, thanh hành động dính đáy. App: cột 720px không thẻ, ô nhập native cao ~46px (`--tap`), checkbox/select thay công tắc/radio, thanh hành động không dính đúng chỗ (`bottom: calc(-1 * var(--space-6))`).

| Màn | Board | Lệch | Mức | Component nghi ngờ | Ảnh |
|---|---|---|---|---|---|
| Mẫu form chung | F1a, F1f, F1k, F1m | Không có thẻ chia khối; ô nhập 46px thay 36px; checkbox/select thay switch/radio; thanh hành động chưa dính đáy | Cao | `FormPage`, `Field` | board-F1a, board-F1f, board-F1k, board-F1m, app-… |
| Nhập lô (wizard) | F1d | Luồng khác (board chia bước trong thẻ; app form dài một cột) | Cao | `FormPage` | board-F1d, app-F1d |

## Nhóm D — Popup (`Modal`, `Field`)

| Màn | Board | Lệch | Mức | Component nghi ngờ | Ảnh |
|---|---|---|---|---|---|
| Popup chung | F1b, F1l, F2a, F2h, F3a | Rộng ~520px (board 560 hoặc 640); căn giữa dọc (board neo cạnh trên); ô nhập 46px (board 36px); khối tóm tắt nền xám (board thẻ có viền); select/checkbox (board radio/switch) | Vừa | `Modal`, `Field` | board-F1b, app-F1b, board-F2a, app-F2a, board-F2h, app-F2h, board-F3a, app-F3a |
| Đặt lại mật khẩu | F3a | Thiếu ô mật khẩu mới theo board | Vừa | `Modal` | board-F3a, app-F3a |
| Ngày giờ | F1l | Ô ngày và giờ xếp dọc (board cùng hàng) | Thấp | `Field` | board-F1l, app-F1l |

## Nhóm E — Khung đăng nhập

| Màn | Board | Lệch | Mức | Component nghi ngờ | Ảnh |
|---|---|---|---|---|---|
| Đăng nhập, Đặt mật khẩu, Không có vai | W4f, W4g, W4h | Nền `#F3F4F6` + thẻ đổ bóng (board `#FAFAFA` + thẻ chỉ viền); padding lớn hơn; W4h nút "Đăng xuất" full width | Vừa | auth shell | board-W4f, board-W4g, board-W4h, app-… |

## Nhóm G — Màn theo vai

| Màn | Board | Lệch | Mức | Ảnh |
|---|---|---|---|---|
| Việc giao của tôi | W1e | Board là master-detail với 4 KPI; app là một cột 640px | Cao | board-W1e, app-W1e-giao1, app-W1e-giao2 |
| Nhãn | W2e | Board có hai nhãn so sánh; app có một nhãn | Vừa | board-W2e, app-W2e |

## Nhóm I — Phân quyền (ma trận)

| Màn | Board | Khối | Lệch | Mức | Ảnh |
|---|---|---|---|---|---|
| Danh sách nhóm | W3h | Thẻ danh sách nhóm | Board: thẻ có đầu, tên thành viên, "Sửa lần cuối", mũi tên. App: tiêu đề caps ngoài thẻ, đoạn dẫn giải, cột khác | Cao | board-W3h, app-W3h |
| Ma trận quyền | W3h, W3i | Việc được làm | Board: thẻ có đầu + ô tìm "Tìm việc", công tắc, ổ khoá cho việc "Chỉ Chủ". App: chip "Được gán/Tất cả khách/Chỉ Chủ", công tắc bật tắt khác kiểu, hàng thừa/thiếu | Cao | board-W3h, app-W3h, board-W3i, app-W3i |

## Nhóm J — Báo cáo lãi lỗ

| Màn | Board | Khối | Lệch | Mức | Ảnh |
|---|---|---|---|---|---|
| Báo cáo lãi lỗ | W3a | Toàn màn | Board: dải 7 ô KPI, điều khiển tháng dạng phân đoạn, các thẻ có đầu, rail phải "Chi tiết lô" + AI. App: dropdown, lưới KPI 3x2, màu thanh khác kèm icon khoá lớn, tiêu đề lô và tab nằm ngoài thẻ, không có rail | Cao | board-W3a, app-W3a |

## Nhóm K — Nội dung (Lô 16)

| Màn | Board | Khối | Lệch | Mức | Ảnh |
|---|---|---|---|---|---|
| Soạn bài | W3b, W3c | Banner, trình soạn, rail phải | Banner cao hơn, thứ tự khác; thiếu thanh AI và khối AI; ô nhập của trình soạn nằm trên nền trần (board gói trong một thẻ); rail phải không có đầu 44px, nội dung chỉ đọc thay vì ô nhập; thiếu nút "Chèn thẻ"; khối "Ảnh trong bài" bố cục khác | Cao | board-W3b, app-W3b, board-W3c, app-W3c, app-W3c0 |
| Đăng bài | W3d | Hộp xác nhận | Không có ngăn kéo; nút lớn hơn board | Vừa | board-W3d, app-W3d |

## Nhóm L — Tài khoản của tôi (W4e)

| Khối | Lệch | Mức | Ảnh |
|---|---|---|---|
| Đầu trang | Board: một dải ngang gồm avatar, tên, Tên đăng nhập, Số điện thoại, Vai trò (chip). App: avatar và tên xếp dọc, SĐT dạng liên kết, chip "Chủ" xám (board chip xanh "Chủ vựa") | Vừa | board-W4e, app-W4e |
| Việc bạn được làm | Board: danh sách một thẻ + hai hàng "Xem giá vốn/báo cáo lãi lỗ" nhãn Có. App: lưới 2 cột có đường kẻ ô, thêm đoạn dẫn giải, nhãn "Có" dạng chấm xanh thay chip | Thấp | board-W4e, app-W4e |
| Mục bạn thấy trên menu | Board: chip nhỏ. App: lưới icon + tên (kèm Hàng chờ thanh toán, Phiếu hoàn…), chân thẻ dài | Thấp | board-W4e, app-W4e |
| Bảo mật & đăng nhập | Board: có dòng "Phiên đăng nhập" ("Máy này"), "AI của tôi/Mở cài đặt AI", mỗi dòng một thẻ nhỏ với nút viền. App: chỉ "Mật khẩu" và "Đăng xuất" kèm đoạn mô tả dài, thiếu 2 dòng kể trên | Vừa | board-W4e, app-W4e |
| Đổi mật khẩu | Board: ngăn kéo bên phải, có checklist yêu cầu mật khẩu. App: chưa chụp trạng thái này | Chưa kiểm | — |
| Tiêu đề khối | Tiêu đề ngoài thẻ (`.sectionH` kiểu sentence case lớn) | Thấp | board-W4e, app-W4e |

## Nhóm F — Che số điện thoại (cần PO quyết)

W5a, W5c, W3e hiện số điện thoại đầy đủ; W5b hiện cả số điện thoại và địa chỉ. Board hiển thị che ("…0412"). Đây vừa là lệch giao diện vừa liên quan bất biến 9 (dữ liệu cá nhân): đề nghị PO quyết hiển thị theo board hay giữ theo quyền xem hiện có.

## Nhóm H — Nút chính thiếu icon

W5g và W5g2 dùng nút chính không có icon cộng như board. Mức Thấp.

## Lưu ý và giới hạn

- Thanh AI/khối AI không hiện ở app có thể do dữ liệu mock (`AiBar` chỉ render khi count>0); đã bật cờ `cave_erp_mock_ai=on` nhưng không chắc đủ. Không chấm riêng.
- W3g, W3i không so sánh được trọn vẹn (mock id=5 là `admin`; W3i xem nhóm Chủ, board là Quản lý).
- Chi tiết Hàng chờ (id=40) trong mock báo "Không tìm thấy trang này"; dùng id=36 và 41.
- F2b ("Huỷ đơn") không chụp được vì mục bị khoá với đơn chưa thanh toán (phụ thuộc dữ liệu).
- Topbar thay tiêu đề màn bằng tên màn con ở mọi trang chi tiết (xem D2b); chưa tách thành dòng riêng vì cùng gốc `PageHeader`.

## Chưa kiểm (chỉ có ảnh board)

F1c, F1e, F1g, F1h, F1i, F1n, F1o, F2b, F2c, F2e, F2f, F2g, F2i, F2j, F2k, F2m, F2n, F2o, F3b, F3c, F3d, F3e, F3f, F3m, cộng F3h–F3l (Nội dung) và popup đổi mật khẩu của W4e. Dự đoán chịu cùng lệch nhóm D (`Modal`/`Field`) nhưng chưa có bằng chứng ảnh app: ghi ⏸, không ghi ✅.

## Danh sách cặp đã so sánh

D2, D2b, D3, W1a, W1a2, W1b, W1b2, W1c, W1c2, W1d, W1d2, W1e, W2a, W2b, W2c, W2d, W2e, W2f, W2g, W2h, W3a, W3b, W3c, W3d, W3e, W3g, W3h, W3i, W4e, W4f, W4g, W4h, W5a, W5b, W5c, W5d, W5e, W5f, W5g, W5g2, W5h, W5i, W5j, W5k, W5l, W5m, W5o, F1a, F1b, F1d, F1f, F1j, F1k, F1l, F1m, F2a, F2d, F2h, F2l, F3a, F3g.

> **03/10 — Duy quyết nhóm F:** giữ hiện đủ SĐT (đúng ý PO, không theo board). Không sửa.

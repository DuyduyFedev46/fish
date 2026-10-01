# QA — ERP theo design

## Lô 1 — FE (khung ERP + mẫu danh sách) · lần 1 · 2026-10-02

### Kết luận: REJECTED — 3 lỗi Medium chặn (B1 banner mất mạng thiếu Thử lại/"Dữ liệu lúc"/làm mờ; B2 nút "Về Tổng quan" của 404 dẫn người giao vào màn "Không có quyền"; B3 bảng có cột khoá làm trang cuộn ngang ở 360 px). Phần còn lại đạt.

### Tổng: 204 ca QA mới + bộ có sẵn · ✅ 195 · ❌ 9 · ⏸ 6 mục

- Kịch bản QA mới (chạy thật trên bản build MOCK, cổng 3101, và khung thử cổng 3102):
  - `qa_ed_batch1_roles.py` 47/48 (1 lỗi có sẵn từ gốc, ngoài lô).
  - `qa_ed_batch1_shell.py` 93/99 (6 ca đỏ, xem B1, B2, B5, B6, B7).
  - `qa_ed_batch1_template.py` 64/66 (2 ca đỏ, xem B3, B5).
- Bộ có sẵn của dev và hồi quy: `ed_batch1_shell` 56/56, `s7_shell` 24/24, `s8_views` 43/44, `s12_s13_queue` 97/99, `s14_s16` 42/42, `s41_s47` 72/72, `s48` 41/41. Các ca đỏ của `s8`, `s12` và `s10_s11` là lỗi có sẵn, xem mục riêng cuối báo cáo.
- `npm ci` sạch (không `--legacy-peer-deps`), `npx tsc --noEmit` 0 lỗi, `npx vitest run` 298/298, `NEXT_PUBLIC_USE_MOCK=1 npm run build` xanh. `python3 scripts/check_naming.py` OK, không vi phạm mới.
- Số màu cứng (hex/rgb) ngoài `tokens.css`: HEAD 35, working tree 35, không tăng. Tôi đếm bằng cách khác với dev (dev ghi 553), nên chỉ kết luận "không tăng".

Cách chứng minh ca giao diện:
- Khung (sidebar, topbar, avatar, ⌘K, 404, lỗi, mất mạng): chạy trình duyệt thật trên bản MOCK.
- Mẫu danh sách, Tabs, AiBar, Chip, Toast, ErrorScreen, NotFoundScreen: chưa màn nào dùng. Tôi dựng khung thử `erp-console/e2e/qa_harness_ed_batch1/` (vite build, dùng đúng `globals.css` và `tokens.css` của app, chỉ giả `next/link` và `next/navigation`) và chạy Playwright trên đó. Đây là bằng chứng chạy thật ở mức thành phần. Việc nối vào từng màn nằm ở Lô 3 trở đi.

## Theo AC

| Mã AC | Kết quả | Bằng chứng |
|---|---|---|
| ED-01-AC1 (menu đủ nhóm, thứ tự §2.1, mục đang mở được tô; topbar tên màn / ⌘K / avatar) | ✅ một phần, ⏸ phần "đủ mục" | Chạy thật, 5 vai (`qa_ed_batch1_roles.py`): thứ tự và nhóm đúng theo §2.1 chép độc lập; topbar trái-sang-phải là tên màn, ô tìm, avatar. Mock `loc` chỉ có 11 mục vì cờ `soon` ẩn Khách hàng, Nhà cung cấp, Hàng hoàn, Sổ nhập xuất, Hoá đơn, Phân quyền và vì mock thiếu perm `confirm_with_customer`, `manage_ai_policy`. Không kiểm "đủ 22 mục" được. |
| ED-01-AC2 (thu gọn 240 -> 60, tooltip, giữ sau tải lại) | ✅ | Đo 240/60 px, tải lại vẫn thu gọn, đổi màn không tải lại vẫn thu gọn, mọi mục có `title` + `aria-label`, bằng bàn phím (Enter). 8 giá trị rác trong `cave_ui_sidebar` (HTML, rỗng, 20 000 ký tự...) đều về mở rộng, menu đủ. Ảnh: `shots/lot1/sidebar-collapsed-1440.png`. Tooltip chỉ là `title` gốc của trình duyệt (xem ghi chú Low). |
| ED-01-AC3 (avatar: 3 mục, Đăng xuất xoá phiên) | ✅ (loc) · ⚠ (giao1) | Chạy thật bằng bàn phím: Enter/Space/ArrowDown mở, ArrowUp/Down quay vòng, Home/End, Esc đóng và trả focus về nút, Tab và bấm ra ngoài đóng. Đăng xuất: token xoá, vào lại `/orders/` bị đưa về Đăng nhập, Back không lộ khung. Người giao (`giao1`) chỉ thấy 2 mục (không có "AI của tôi"), lệch chữ "đúng 3 mục" của AC, dev-notes #3 đã ghi, cần PO chốt (xem B8). |
| ED-01-AC4 (tab, Back) | ⏸ | Tab thuộc từng màn (Lô 3+). Hộp Tabs đã chạy ở khung thử: ArrowRight/Left/Home/End, roving tabindex, aria-selected, số đếm 0 thì ẩn. `useTabParam` và Back chưa có màn dùng nên chưa kiểm. |
| ED-01-AC5 (giao: chỉ "Việc giao của tôi") | ✅ | `giao1`: menu chỉ 1 mục, không có Tổng quan, Đơn & tiền, Giao hàng, Nhật ký (không có trong DOM); tự vào `/my-deliveries/`; vào thẳng 20 URL khác đều bị chặn hoặc về trang của mình; ⌘K chỉ có 1 mục. |
| ED-01-AC6 (tắt quyền thì mục biến mất, không sửa code) | ✅ | `patchUser` đổi `denied_perms` / `extra_perms` rồi tải lại: mục biến mất / hiện ra. Màn tương ứng trả "Không có quyền" khi vào thẳng URL. |
| ED-02-AC1, AC2 (ngày, tiền, kg) | ✅ | Vitest 298/298 (`format.test`, `noLocalTime.test`) + trình duyệt: mốc `03:30Z` ra `02/10/2026 10:30` dù máy giả lập múi giờ New York; `540000` ra `540.000 đ`. Quét 13 màn thật: không có ISO, `₫`, giờ 12h, `null`, `NaN`. |
| ED-02-AC3, AC4 (nhãn enum, enum lạ) | ✅ | Vitest `enums.test`. Trình duyệt: chip `BOOKED` -> "Giữ chỗ", `AUTO_CANCELLED` -> "Đã huỷ", không lộ mã. |
| ED-02-AC5 (giá vốn) | ✅ | Khung thử: không có quyền thì tiêu đề "Giá vốn" và số `300.000` không có trong DOM. Có quyền thì tiêu đề có icon khoá và chữ đọc "(cột giới hạn quyền xem)". |
| ED-02-AC6 (quét chữ cấm) | ✅ | Vitest `personalData.test`, `removedAliases.test`, `englishNames.test`. Không đọc code để chấm: đây là test chạy. |
| ED-03-AC1 (danh sách trống) | ✅ | Khung thử: icon + tiêu đề riêng + 1 câu. Header cột và bộ lọc vẫn hiện. Ảnh `vs-template-empty-1440.png`. |
| ED-03-AC2 (không tìm thấy + Xoá tìm kiếm) | ✅ | Gõ chuỗi giả có tên + SĐT: ra "Không tìm thấy đơn hàng khớp với “…”"; bấm Xoá tìm kiếm thì đủ 4 dòng, ô tìm trống. Từ khoá có HTML được thoát, từ khoá 400 ký tự không vỡ bố cục. Từ khoá không vào URL, localStorage, sessionStorage. |
| ED-03-AC3 (đang tải, skeleton) | ✅ | Khung xương, `aria-busy`, "Đang tải dữ liệu…" cho trình đọc màn hình; header cột và bộ lọc hiện; vị trí tiêu đề, tab, lọc, đầu bảng giữa "đang tải" và "có dữ liệu" lệch ≤ 2 px. Lưu ý: thanh AI chỉ hiện khi `count>0`, màn nào chưa biết số đề xuất khi đang tải sẽ làm bảng nhảy xuống ~52 px (do màn quyết định, ghi để Lô 3). |
| ED-03-AC4 (mất mạng: banner + Thử lại + mờ + "Dữ liệu lúc") | ❌ | Chạy thật `context.set_offline(True)` trên `/orders/`: banner "Mất kết nối. Đang thử lại…" có (role=alert, nằm dưới topbar). KHÔNG có nút Thử lại, KHÔNG có "Dữ liệu lúc dd/mm/yyyy hh:mm", dữ liệu KHÔNG mờ. Xem B1. Ảnh `vs-offline-1440.png`. Mờ ở mức bảng (`stale`) chạy đúng ở khung thử (opacity 0,55). |
| ED-03-AC5 (xung đột) | ⏸ | Ngoài lô 1 (cần mã xung đột từ BE ở 02b). |
| ED-03-AC6 (404 và lỗi chung trong khung) | ✅ (loc) · ❌ (giao1 nút về) | 404: có sidebar + topbar, nút "Về Tổng quan", URL lồng `/orders/abc/` cũng ra 404 trong khung, chưa đăng nhập thì về Đăng nhập. Lỗi chung: gây lỗi vẽ thật (ép `toLocaleString` ném lỗi) -> "Có lỗi xảy ra" trong khung, menu vẫn đi tiếp được, không in chi tiết lỗi ra màn, "Thử lại" vẽ lại đúng khi hết lỗi. Người giao bấm "Về Tổng quan" ở 404 thì vào màn "Không có quyền" (B2). Ảnh `vs-404-1440.png`, `vs-error-1440.png`. |
| ED-03-AC7 (toast) | ✅ | Khung thử: góc dưới phải, success=`status`, error=`alert`, nút đóng, "Hoàn tác" chỉ khi truyền `undo` và bấm thì gọi `undo` rồi đóng, 6 toast liên tiếp chỉ giữ 4, `aria-live=polite`. Đồng hồ giả: success tự ẩn ~6 s, error ~10 s, rê chuột thì dừng đếm. Ảnh `vs-toast-stack-1440.png`. |
| ED-03-AC8 (kho vào Báo cáo lãi lỗ) | ✅ | `kho1` vào thẳng `/reports/`: ra "Không có quyền", không thấy số liệu nào, màn báo cáo không được dựng (không có lời gọi API báo cáo trong log mock). |
| ED-04-AC1, AC2 (dòng -> chi tiết; thanh lọc, "Đang hiện x / y") | ✅ một phần · ⏸ phần URL | Khung thử: bấm ô bất kỳ của dòng đi tới `/orders/2/`; ô đầu là `<a>` thật; bấm nút trong dòng không điều hướng. "Đang hiện 4 / 4 đơn" cập nhật khi lọc. "Trạng thái và ngày nằm trong URL" và "Back còn nguyên bộ lọc": FilterBar không tự ghi URL, việc này thuộc từng màn (Lô 3+), chưa kiểm. |
| ED-04-AC11 (thanh AI) | ✅ | Khung thử: "AI · Có 2 đề xuất: …" + nút Xem khi n=2; n=0 thì không vẽ. |
| G1 (menu 6 nhóm/vai) | ✅ | Ma trận 5 vai, xem mục Phân quyền. |
| G2 (ngày giờ) | ✅ | Trình duyệt, xem ED-02-AC1. |
| G3 (tiền "đ") | ✅ có ghi chú | Mock FE ra "đ". BE thật trả `vnd_display` dạng "₫" (dev-notes #9, chưa chốt). Khi nối BE thật sẽ lộ hai ký hiệu. |
| G4 (một ô một giá trị) | ⏸ | Thuộc từng màn. |
| G5 (không `Làm mới`, không sáng/tối ở topbar) | ✅ | Topbar và danh sách: không có "Làm mới", không nút sáng/tối, không nút Đăng xuất rời. |
| G7 (giá vốn ẩn, không chừa chỗ) | ✅ | Xem ED-02-AC5. |
| G8 (4 trạng thái của danh sách) | ✅ | Xem ED-03-AC1..AC3 và lỗi: bảng lỗi có role=alert + Thử lại gọi lại hàm tải. |
| G9 (quyền, chặn URL) | ✅ trong lô · ❌ có sẵn ngoài lô | `ViewGuard` chặn 21 URL đúng theo từng vai, menu và guard nhất quán. Ngoại lệ có sẵn: `/ai/policy/` không có ViewGuard (xem mục lỗi có sẵn). |
| G10 (dữ liệu cá nhân) | ✅ | ⌘K gõ 4 tên, 3 SĐT và 2 mã đơn giả lấy từ màn Đơn: không ra mục nào, không gọi API, không ghi vào storage (trừ kho mock `cave_erp_mock_*` của chính bản mock), không vào URL. Khoá `cave_ui_sidebar` chỉ chứa `collapsed`/`open`. Ảnh và báo cáo chỉ có dữ liệu giả. Lưu ý B7 (Low). |

## Ngoại lệ và biên

| Ca | Kết quả |
|---|---|
| `cave_ui_sidebar` rác (`<img onerror>`, rỗng, `collapsed ` có khoảng trắng, `null`, `undefined`, `{}`, `1`, 20 000 ký tự) | ✅ về mở rộng, không vỡ |
| `collapsed` trong storage rồi bóp cửa sổ còn 360 px | ✅ ngăn kéo vẫn đủ chữ, rộng > 200 px |
| Bấm đúp, Esc, Tab trong menu avatar | ✅ |
| Đăng xuất rồi bấm Back / vào lại URL cũ | ✅ không lộ khung hoặc dữ liệu |
| 404 cho `loc`, `giao1`, người chưa đăng nhập; URL lạ lồng nhau | ✅ (nút về của `giao1` đỏ, B2) |
| Lỗi vẽ rồi đổi màn bằng menu; Thử lại khi hết lỗi | ✅ |
| Mất mạng rồi có mạng lại: banner tự tắt | ✅ |
| Từ khoá tìm có HTML / quá dài / chứa tên + SĐT | ✅ |
| Toast: 6 cái liên tiếp, rê chuột, tab ẩn, Hoàn tác | ✅ |
| Cuộn ngang 1280 và 1440: 15 màn của `loc`, 1 màn của `giao1`, cả khi thu gọn sidebar | ✅ |
| 360 px: `loc` 6 màn, `kho1` 2 màn, `giao1` 1 màn không cuộn ngang; có menu đáy và ngăn kéo; `giao1` (1 mục) không có menu đáy | ✅ |
| 360 px: bảng khung thử có cột khoá | ❌ B3 |
| 768 và 1024 px (thông tin thêm) | ✅ không cuộn ngang |

## Phân quyền (menu mock; so với UI-RULES §2.1)

Mock chưa có đủ quyền mới nên mọi vai là tập con của §2.1, thứ tự và nhóm đúng. Ô "vào thẳng URL" kiểm 21 đường dẫn mỗi vai; kết quả trùng với menu, không có màn nào mở được mà menu giấu (trừ `/ai/policy/` có sẵn).

| Vai | Số mục | Mục thấy | Đúng kỳ vọng |
|---|---|---|---|
| `loc` (Chủ) | 11 | Tổng quan, Đơn & tiền, Giao hàng, Mua hàng, Kho & lô, Kiểm kê, Danh mục & giá, Báo cáo lãi lỗ, Nội dung, Nhân sự, Nhật ký hoạt động | ✅ (tập con, xem ED-01-AC1) |
| `ql1` (Quản lý) | 10 | như trên, thêm Gọi xác nhận, bớt Báo cáo lãi lỗ và Nhân sự | ✅ |
| `kho1` (Kho) | 8 | Tổng quan, Đơn & tiền, Giao hàng, Việc giao của tôi, Mua hàng, Kho & lô, Kiểm kê, Danh mục & giá. Không có Báo cáo lãi lỗ, Nhân sự, Nhật ký | ✅ (đã kiểm ED-03-AC8) |
| `giao1` (Giao) | 1 | Việc giao của tôi | ✅ |
| `cs2` (CSKH thuần, `patchUser`) | 4 | Đơn & tiền, Gọi xác nhận, Giao hàng, Việc giao của tôi | ✅ |
| Chưa đăng nhập | 0 | tất cả URL về Đăng nhập, không lộ khung | ✅ |
| `kho5` (bắt đặt mật khẩu) | | bị giữ ở màn đặt mật khẩu, không thấy menu | ✅ |
| `admin` (không có vai) | | không có mục nào, vào URL thì "Không có quyền" | ✅ |

## Rò giá vốn

- Không phát hiện. Khung thử: cột Giá vốn không có trong DOM khi người xem thiếu quyền; có thì có icon khoá. Không có khoá mới nào ghi vào AuditLog hay API trong lô này (lô FE thuần), nên không có tiền ÷ kg để tính ngược.

## Rò dữ liệu cá nhân

- ⌘K không tìm theo tên, SĐT, mã đơn, không gọi API, không ghi từ khoá đi đâu. Ô tìm của FilterBar cũng không ghi vào URL hay storage.
- Console trình duyệt: không có tên, SĐT, địa chỉ trong các lượt chạy bình thường. Ngoại lệ Low B7: khi một màn ném lỗi, React ghi thông điệp lỗi gốc ra console.
- Ảnh trong `shots/lot1/` chỉ dùng dữ liệu giả của mock và khung thử.

## Hồi quy

- Mở bằng menu mới các màn cũ: Tổng quan, Đơn & tiền, Hàng chờ thanh toán, Phiếu hoàn chờ chuyển, Giao hàng, Mua hàng, Kho & lô, Kiểm kê, Danh mục & giá, Báo cáo, Nội dung, Nhân sự, Nhật ký, AI của tôi, Tài khoản: đều mở được, không lỗi console.
- `/orders/` trên 1440 px thấy 3 tab (dev-notes #7 đã được xử lý; chuyển tab mở đúng `/orders/payments/` và `/orders/refunds/`). Ảnh `shots/lot1/orders-tabs-desktop-1440.png`.
- `s7_shell` 24/24, `s14_s16` 42/42, `s41_s47` 72/72, `s48` 41/41, `ed_batch1_shell` 56/56.

## Chấm theo UI-RULES (mục áp dụng cho lô 1)

| Mục | Điểm | Ghi chú |
|---|---|---|
| §1.3 nhãn enum, không lộ mã | Đạt | |
| §1.5 ngày dd/mm/yyyy hh:mm, GMT+7 | Đạt | đúng cả khi máy ở múi giờ khác |
| §1.6 tiền "đ", không số lẻ | Đạt có ghi chú | "₫" của BE thật chưa thống nhất với "đ" của FE |
| §1.7 khoá giá vốn | Đạt | |
| §2.1 menu 6 nhóm, thứ tự | Đạt (tập con) | thiếu mục do cờ `soon` và mock |
| §2.2 topbar, avatar, bàn phím | Đạt | `giao1` chỉ 2 mục (B8) |
| §3 / T3 thu gọn sidebar | Đạt | tooltip chỉ là `title` gốc |
| §4 danh sách (thứ tự khối, căn phải, mono, chip, tạo mới góc phải) | Đạt, Low B4 | tiêu đề cột bị IN HOA khác bản thiết kế |
| §6.4 màn 404, lỗi chung | Đạt, Low B5 | thứ tự nút và icon khác bản thiết kế |
| §7 mất mạng | Không đạt | B1 |
| §7 toast | Đạt | khớp bản thiết kế `W6i` |
| T4 (360 px: ngăn kéo, menu đáy, không cuộn ngang) | Không đạt một phần | B3 |
| T5 (⌘K chỉ nhảy menu, không tìm khách) | Đạt | placeholder "Tìm màn hình…" khác "Tìm đơn, lô, mặt hàng…" của bản thiết kế, chấp nhận theo T5 |

## Lỗi

### B1 — Banner mất mạng của khung thiếu Thử lại, "Dữ liệu lúc", làm mờ · Medium · ED-03-AC4
- Tái hiện: đăng nhập `loc` -> `/orders/` -> `context.set_offline(True)` (hoặc ngắt mạng thật).
- Mong đợi (02-stories, UI-RULES §7, `W6d`): banner "Mất kết nối. Đang thử lại…" kèm nút Thử lại; dữ liệu cũ mờ đi; dòng "Dữ liệu lúc dd/mm/yyyy hh:mm".
- Thực tế: chỉ có chữ "Mất kết nối. Đang thử lại…". Không nút, không giờ, dữ liệu rõ nét. `Shell` gắn `<OfflineBanner />` không truyền `onRetry` và `asOf`; không màn nào gọi `useOffline()` hay đặt `is-stale`.
- Ảnh hưởng: người dùng mất mạng không biết số liệu đang xem cũ từ lúc nào và không có nút để thử lại. Cần cơ chế để màn đăng ký `asOf` và `onRetry` cho dải toàn cục (context), hoặc gắn dải trong `ListPage`.
- Ca: `qa_ed_batch1_shell.py` ("banner có nút Thử lại", "banner ghi Dữ liệu lúc", "dữ liệu cũ mờ đi").

### B2 — Nút "Về Tổng quan" ở 404 / lỗi chung dẫn người giao vào "Không có quyền" · Medium · ED-03-AC6 (G9)
- Tái hiện: đăng nhập `giao1` -> vào `/khong-co-man-nay/` -> bấm "Về Tổng quan".
- Mong đợi: về trang chủ của người đó (`homePath`, với người giao là "Việc giao của tôi").
- Thực tế: `NotFoundScreen` và `ErrorScreen` mặc định `homeHref="/overview/"`; người giao không có quyền màn đó nên thấy "Bạn không có quyền xem mục này. Nếu cần dùng mục này, hãy nhờ Chủ vựa cấp quyền". Nút phục hồi chính của họ dẫn tới một thông báo lỗi.
- Ảnh hưởng: nhân viên giao, vai dùng điện thoại nhiều nhất, gặp ngõ cụt khi lỡ URL. Gợi ý: truyền `homePath(me)` từ `app/not-found.tsx` và `app/(console)/error.tsx`.
- Ảnh: `shots/lot1/404-giao1-1440.png`.

### B3 — Bảng có cột khoá làm cả trang cuộn ngang ở 360 px · Medium · T4 / G-bố cục
- Tái hiện: khung thử `?m=rows&locked=1`, viewport 360 px (hoặc bất kỳ `DataTable` có cột `locked: true` trên điện thoại): `document.documentElement.scrollWidth` = 577-622 > 360. Không có cột khoá thì 360 (đạt).
- Nguyên nhân: `<span class="sr-only"> (cột giới hạn quyền xem)</span>` trong `<th>` có `position:absolute` nhưng vùng `.lt-scroll{overflow-x:auto}` không phải khối chứa (không `position:relative`) nên nó thoát khỏi vùng cuộn, nằm ngoài viền phải của bảng rộng hơn màn hình. Thêm `.lt-scroll{position:relative}` (đã thử nạp thêm CSS này trong trình duyệt: scrollWidth về 360).
- Ảnh hưởng: chủ và quản lý (người có quyền giá vốn) xem mọi bảng có cột giá vốn, lãi lỗ, tiền nhà cung cấp trên điện thoại sẽ bị trang trượt ngang. Chưa màn nào dùng cột khoá nên chưa thấy ở sản phẩm, nhưng sẽ phát sinh từ Lô 3.
- Ca: `qa_ed_batch1_template.py` ("T4 360px (CÓ cột giá vốn/khoá)").

### B4 — Tiêu đề cột của bảng mới bị IN HOA, khác bản thiết kế · Low · ED-04
- Quy tắc cũ `thead th{text-transform:uppercase; letter-spacing:...}` (globals.css dòng 239) đè lên `table.lt th`. Bản thiết kế `ERP-D2` viết hoa chữ đầu ("Mã đơn", "Khách"). Thêm `text-transform:none; letter-spacing:normal` vào `table.lt th`.
- Ảnh: `vs-template-rows-1440.png`.

### B5 — Màn lỗi chung lệch bản thiết kế · Low · ED-03-AC6
- Thứ tự nút: bản thiết kế `W6h` là "Về Tổng quan" rồi "Thử lại" (chính, màu nhấn ở bên phải); bản thật ngược lại. Icon bản thật xám, bản thiết kế đỏ nhạt. Nội dung dưới tiêu đề khác ("…báo kỹ thuật kèm giờ…" so với "Bấm Thử lại, hoặc quay về…"). Cần PO/UI chốt theo bên nào.
- Ảnh: `vs-error-1440.png`.

### B6 — Đóng hộp ⌘K bằng Esc làm mất focus (rơi về BODY) · Low · a11y
- Người dùng bàn phím phải Tab lại từ đầu trang. Nên trả focus về nút ô tìm hoặc phần tử đang focus trước đó.

### B7 — Console vẫn nhận nội dung lỗi khi màn ném lỗi · Low · G10
- `app/(console)/error.tsx` ghi chú "KHÔNG ghi nội dung lỗi ra console", và code của nó đúng như vậy. Tuy nhiên React production vẫn ghi thông điệp lỗi gốc (ví dụ `Error: ... SECRET-NAME-0901` do QA giả lập) ra `console.error` và `window.onerror`. Điều này khiến dòng ghi chú nói quá, không phải lỗi mã. Rủi ro chỉ khi có đoạn code ném thông điệp chứa tên/SĐT khách (chưa thấy). Đề nghị sửa ghi chú và quy ước không đặt dữ liệu khách vào thông điệp `Error`.

### B8 — Menu avatar của người giao chỉ 2 mục (cần PO chốt) · Low · ED-01-AC3
- AC viết "đúng 3 mục". `giao1` không có view `ai-settings` nên không có "AI của tôi" (dev-notes #3). ED-06-AC5 có thể mâu thuẫn. Chờ Duy/PO chốt trước khi tính là lỗi.

## Có sẵn từ gốc, không tính vào lô này

| Mục | Mô tả | Giao cho |
|---|---|---|
| P1 | `/ai/policy/` (`app/(console)/ai/policy/page.tsx`) không có `ViewGuard`: mọi vai (kho, giao, CSKH) đều vào được. Vi phạm G9. File không bị sửa ở lô 1 (đã so với HEAD). Mức Medium-High khi nối BE thật; trong mock chưa lộ dữ liệu nhạy cảm. | Lô 15 (hoặc sửa nhanh một dòng) |
| P2 | `s8_views` 360 px `/inventory/`: vùng bấm 84x20 px ở mã lô | đã ghi dev-notes #10 |
| P3 | `s12_s13_queue` 360 px: nút "Làm mới" 88x28, "Thực hiện" 79x25 (còn nút "Làm mới" ở màn cũ) | dev-notes #10 |
| P4 | `s10_s11_orders`: ca BR-TT-03 báo "(BR-TT-03)" lặp lại trong thông điệp lỗi, lộ mã nội bộ | dev-notes #10 |
| P5 | `DESIGN.md` còn mô tả 3 cột và nút sáng/tối (dev-notes) | tài liệu |
| P6 | Tooltip khi thu gọn sidebar chỉ là thuộc tính `title` (chờ ~1 s, không hiện trên cảm ứng); chấp nhận ở lô 1 theo mô tả "tooltip bằng title" trong CSS | ghi nhận |

## ⏸ Chưa kiểm được (và vì sao)

1. ED-01-AC1 "đủ 22 mục" cho Chủ: mock thiếu perm và màn `soon` bị ẩn.
2. ED-01-AC4 (tab theo URL, Back), ED-04-AC2 (lọc nằm trong URL), ED-04-AC1 phần "Back còn nguyên bộ lọc": chưa màn nào nối.
3. ED-03-AC5 (xung đột): cần BE.
4. G4 (một ô một giá trị): thuộc từng màn.
5. Chạy trên BE thật: lô này chỉ chạy bản MOCK.
6. Hiển thị trong dark mode: bản thiết kế bỏ nút sáng/tối ở topbar, không kiểm.

## Lệnh đã chạy (output tóm tắt)

```
cd erp-console && rm -rf node_modules && npm ci            -> sạch, không --legacy-peer-deps
npx tsc --noEmit                                           -> 0 lỗi
npx vitest run                                             -> 29 file, 298/298
NEXT_PUBLIC_USE_MOCK=1 npm run build                       -> xanh
(cd out && python3 -m http.server 3101 &)
python3 e2e/ed_batch1_shell.py                             -> 56/56
python3 e2e/s7_shell.py                                    -> 24/24
python3 e2e/s8_views.py                                    -> 43/44 (P2 có sẵn)
python3 e2e/s12_s13_queue.py                               -> 97/99 (P3 có sẵn)
BASE=http://127.0.0.1:3101 python3 e2e/s14_s16_cancel_refund.py -> 42/42
python3 e2e/s41_s47_staff.py                               -> 72/72
python3 e2e/s48_password.py                                -> 41/41
python3 e2e/s10_s11_orders.py                              -> dừng ở ca BR-TT-03 (P4 có sẵn)
python3 e2e/qa_ed_batch1_roles.py                          -> 47/48 (P1 có sẵn)
SHOTS=<shots/lot1> python3 e2e/qa_ed_batch1_shell.py       -> 93/99
node_modules/.bin/vite build --config e2e/qa_harness_ed_batch1/vite.config.mjs
(cd e2e/qa_harness_ed_batch1/dist && python3 -m http.server 3102 &)
SHOTS=<shots/lot1> python3 e2e/qa_ed_batch1_template.py    -> 64/66
python3 scripts/check_naming.py                            -> OK, không vi phạm mới
pkill -f "http.server 310[12]"
```

Tệp QA mới (đều trong `erp-console/e2e/`): `qa_ed_batch1_common.py`, `qa_ed_batch1_roles.py`, `qa_ed_batch1_shell.py`, `qa_ed_batch1_template.py`, `qa_harness_ed_batch1/` (khung thử; thư mục `dist/` sinh khi build, không commit).
Ảnh (dữ liệu giả, cạnh bản thiết kế): `doc/features/2026-10-01-erp-theo-design/shots/lot1/` (`vs-*.png` là ảnh ghép thật | thiết kế; có `sidebar-open`, `sidebar-collapsed`, `avatar-menu-open`, `404`, `error`, `offline`, `template-*`, `toast-stack`, `drawer-360`, `orders-tabs-desktop`).

### Lô 1 — FE vòng 2 · lần 2 · 2026-10-02

#### Kết luận: APPROVED — B1, B2, B3, B4, B5, B6, H1, H2 và toast `duration` đều đã đạt trên trình duyệt thật; không còn lỗi chặn. Chỉ còn các lỗi có sẵn từ gốc (P1, P3, `console.error` của React production) và vài ghi nhận Low.

#### Tổng: 99 ca QA vòng 2 mới + bộ có sẵn · ✅ tất cả ca của lô · ❌ 0 lỗi mới · ⏸ 3 mục (xem cuối)

- Kịch bản QA mới `erp-console/e2e/qa_ed_batch1_round2.py`: **99/99** (chạy trên app mock cổng 3101 và khung thử cổng 3102).
- Các kịch bản yêu cầu chạy lại:
  - `ed_batch1_shell` 56/56
  - `ed_shell_fixes` 21/21
  - `s7_shell` 24/24
  - `s12_s13_queue` 97/99 (2 ca đỏ là P3: nút "Làm mới" 88x28 và "Thực hiện" 79x25 trong `GuidancePanel`, có sẵn từ gốc)
  - `qa_ed_batch1_shell` 98/99 (1 ca đỏ là `console.error` do chính React production ghi, B7 cũ, không phải lỗi mã)
  - `qa_ed_batch1_roles` 47/48 (1 ca đỏ là P1, `/ai/policy/` không có ViewGuard, có sẵn từ gốc)
  - `qa_ed_batch1_template` 66/66 (vòng 1 là 64/66)
- `rm -rf node_modules && npm ci` sạch (không `--legacy-peer-deps`), `tsc --noEmit` 0 lỗi, `vitest run` 34 file / 329 test đạt, `NEXT_PUBLIC_USE_MOCK=1 npm run build` xanh, `python3 scripts/check_naming.py` OK.
- Tôi **không sửa code sản phẩm**. Tôi chỉ thêm `qa_ed_batch1_round2.py` và thêm hai chế độ vào khung thử `e2e/qa_harness_ed_batch1/main.tsx` (`?m=enums` cho H1, hai nút toast có `duration` cho L1).
- Đã tắt cả hai server (3101, 3102).

#### Theo mục đã sửa

| Mục | Kết quả | Bằng chứng (chạy trình duyệt thật) |
|---|---|---|
| B1 mất mạng (ED-03-AC4) | ✅ | Trên `/orders/` thật: dải "Mất kết nối. Đang thử lại… Dữ liệu lúc dd/mm/yyyy hh:mm" + nút Thử lại + nội dung mờ (opacity hiệu dụng ≈ 0,55); dải KHÔNG bị mờ và nằm dưới topbar. Mốc "Dữ liệu lúc" là giờ VN (lệch ≤ 3 phút so với giờ VN hiện tại). Có mạng lại thì hết dải và hết mờ. Cũng đạt trên Danh mục & giá và Nhật ký hoạt động (cùng `usePagedList`). Ảnh `vs2-offline-1440.png` (cạnh board W6d), `r2-offline-orders-1440.png`. |
| B2 "Về …" theo vai (ED-03-AC6) | ✅ | 404: `giao1` thấy "Về Việc giao của tôi" và bấm vào `/my-deliveries/`; `loc`, `ql1`, `kho1` thấy "Về Tổng quan" và về `/overview/`; URL lồng `/orders/abc/` cũng đúng; `cs2` (CSKH thuần) có nút "Về …" về trang chính của vai, không vào "Không có quyền". Màn lỗi chung của `giao1` (ép lỗi vẽ thật): nút "Về Việc giao của tôi" trỏ `/my-deliveries/`, không có "Về Tổng quan"; hết lỗi thì Thử lại vẽ lại đúng. Chưa đăng nhập vào URL lạ thì về Đăng nhập, không lộ khung. Ảnh `vs2-404-giao1-1440.png`, `r2-error-giao1-1440.png`. |
| B3 cuộn ngang 360 px | ✅ | Khung thử, bảng có cột khoá: `scrollWidth` ≤ 360 ở 360 px và 320 px, cả khi mờ (`stale`) và không mờ; bảng tự cuộn trong khung riêng; cột khoá vẫn có icon khoá và chữ đọc. Không có quyền thì không có cột "Giá vốn" và không có số `300.000` trong DOM. Ảnh `r2-locked-360.png`. |
| B4 tiêu đề cột | ✅ | Computed style của `th`: `text-transform:none`, `letter-spacing:normal`; chữ "Mã đơn". Ảnh `vs2-template-rows-1440.png`. |
| B5 màn lỗi chung | ✅ | Thứ tự nút trái sang phải là "Về …" rồi "Thử lại" (nút chính); câu "Màn này chưa tải được. Nếu vẫn lỗi, báo kỹ thuật kèm giờ dd/mm/yyyy hh:mm"; icon đỏ nhạt; không in stack/chi tiết lỗi. Khớp board W6h. Ảnh `vs2-error-1440.png`. |
| B6 Esc đóng ⌘K | ✅ | Mở/đóng 5 lần bằng nút, Esc ngay khi vừa mở, Ctrl+K từ ô nhập, đóng bằng bấm nền: focus không bao giờ rơi về BODY, Esc rồi Tab vẫn đi tiếp được. Hồi quy: gõ "kho" + Enter tới `/inventory/`. |
| H1 enum lạ (ED-02-AC4) | ✅ | Khung thử `?m=enums`: `BOOKED` hiện "Giữ chỗ" (chip warn); `NEW_FANCY_STATE` hiện đúng mã gốc trong chip xám; `paid` (sai hoa/thường) hiện `paid`, không đoán nhãn; `""`, `null`, `undefined` hiện "—" không có chip; trang không có "Không rõ", "undefined" hay "null". Ảnh `r2-enums-1440.png`. |
| H2 Back/Forward giữa các tab (ED-01-AC4) | ✅ | Khung thử `?m=tabparam`: đổi tab nhanh 4 lần không chờ, mỗi lần thêm đúng 1 bước lịch sử; Back ×4 đi đúng ngược (all, ref, pay, all), Forward ×4 đi đúng xuôi (pay, ref, all, ref), URL luôn khớp tab. Bấm lại tab đang chọn không thêm lịch sử. Đổi bằng phím Home/End rồi Back đúng. Tải lại giữ tab. `?tab=` rác (`<script>`, `constructor`, `__proto__`, rỗng, `ALL`, `pay%20`) thì về tab đầu, không vỡ. Giữ các tham số khác trên URL (`foo=1`). Không ghi vào localStorage/sessionStorage. Không lỗi console. Ảnh `r2-tabparam-1280.png`. |
| L1 toast `duration` | ✅ | `success` với `duration=1500` tự ẩn sau ≈1,5 s (mặc định 6 s); `error` với `duration=20000` còn sau 11 s (mặc định 10 s đã qua) và tự ẩn ≈20 s; không truyền `duration` thì vẫn ≈6 s. |

#### Ca ngoài đường thuận đã chạy
- Bấm Back nhiều lần giữa các tab, đổi tab nhanh, Back sau khi đổi bằng bàn phím, tải lại giữa chừng (H2).
- Mất mạng rồi có mạng lại, lật 4 vòng liên tiếp; bấm Thử lại đúp rồi bấm tiếp; đang mất mạng đổi màn bằng menu rồi quay lại `/orders/` (đăng ký lại đúng "Dữ liệu lúc" và Thử lại); mất mạng trên 3 màn danh sách khác nhau (B1).
- Mở/đóng ⌘K liên tiếp, Esc ngay khi vừa mở (B6).
- 404 và lỗi vẽ thật với 5 vai (B2); 320 px thêm vào 360 px (B3).

#### Hồi quy: menu theo 5 vai
Số mục bằng đúng vòng 1: `loc` 11, `ql1` 10, `kho1` 8, `giao1` 1 ("Việc giao của tôi", tự vào `/my-deliveries/`); `cs2` 4; chưa đăng nhập, `kho5` bắt đặt mật khẩu và `admin` không có vai đều đúng như cũ (`qa_ed_batch1_roles` 47/48, chỉ đỏ P1). `s7_shell`, `ed_batch1_shell` đạt đủ.

#### Rò giá vốn / dữ liệu cá nhân
Không phát hiện. Khung thử: cột giá vốn không có trong DOM khi thiếu quyền. `?tab=` chỉ ghi khoá tab, không ghi gì vào storage. Ảnh và log chỉ dùng dữ liệu giả của mock và khung thử. Lô này FE thuần nên không có khoá mới ghi vào AuditLog hay API.

#### Ghi nhận Low (không chặn)
- L-a: Màn không đăng ký nguồn (ví dụ Tổng quan) khi mất mạng có dải và làm mờ nội dung nhưng chỉ có chữ "Mất kết nối. Đang thử lại…", không "Dữ liệu lúc" và không Thử lại. Đúng thiết kế ("màn đăng ký"), nhưng từng màn ở Lô 3 trở đi cần đăng ký qua `usePagedList` / `ListPage` hoặc `useOfflineRegistration`.
- L-b: ⌘K mở rồi gõ ngay trong cùng một khung hình (≈16 ms, nhanh hơn người) thì chữ đầu có thể mất vì focus vào ô nhập qua `requestAnimationFrame`. Người thật không gặp; ghi để biết.
- L-c: `Chip`/`useTabParam` chưa màn thật nào dùng, nên H1/H2 chỉ có bằng chứng ở mức khung thử. Việc nối vào màn nằm ở Lô 3 trở đi.

#### ⏸ Chưa kiểm
1. ED-01-AC1 "đủ 22 mục" cho Chủ: mock thiếu perm và màn `soon` bị ẩn (như vòng 1).
2. ED-03-AC5 (xung đột) và chạy trên BE thật: ngoài lô FE này.
3. B8 (menu avatar `giao1` chỉ 2 mục): chờ PO chốt, dev đã báo không làm.

#### Lỗi có sẵn từ gốc (không tính vào lô này)
P1 `/ai/policy/` không có ViewGuard (Lô 15); P3 vùng bấm 360 px của `GuidancePanel` ("Làm mới" 88x28, "Thực hiện" 79x25); `console.error` của React production khi màn ném lỗi (B7 cũ, ghi chú trong `error.tsx` đã sửa).

#### Lệnh đã chạy
```
cd erp-console && rm -rf node_modules && npm ci          -> sạch, không --legacy-peer-deps
./node_modules/.bin/tsc --noEmit                         -> 0 lỗi
npx vitest run                                           -> 34 file, 329/329
NEXT_PUBLIC_USE_MOCK=1 npm run build                     -> xanh
node_modules/.bin/vite build --config e2e/qa_harness_ed_batch1/vite.config.mjs
(cd out && python3 -m http.server 3101 &); (cd e2e/qa_harness_ed_batch1/dist && python3 -m http.server 3102 &)
python3 e2e/ed_batch1_shell.py                           -> 56/56
python3 e2e/ed_shell_fixes.py                            -> 21/21
python3 e2e/s7_shell.py                                  -> 24/24
python3 e2e/s12_s13_queue.py                             -> 97/99 (P3 có sẵn)
python3 e2e/qa_ed_batch1_shell.py                        -> 98/99 (console.error React production)
python3 e2e/qa_ed_batch1_roles.py                        -> 47/48 (P1 có sẵn)
python3 e2e/qa_ed_batch1_template.py                     -> 66/66
SHOTS=<shots/lot1> python3 e2e/qa_ed_batch1_round2.py    -> 99/99
python3 scripts/check_naming.py                          -> OK, không vi phạm mới
pkill -f "http.server 310[12]"
```
Ảnh dữ liệu giả, cạnh bản thiết kế: `doc/features/2026-10-01-erp-theo-design/shots/lot1/` (`vs2-offline-1440`, `vs2-error-1440`, `vs2-404-giao1-1440`, `vs2-template-rows-1440`; thêm `r2-*`).

---

## BE Lô 2, 3, 4, 6, 7 · lần 1 · 2026-10-02

**Cách kiểm:** dựng backend thật (`runserver 127.0.0.1:8765`, SQLite tạm `qa.sqlite3` do script seed dữ liệu giả, không đụng DB staging/production, không đọc `*.env`). Gọi HTTP thật bằng token từng nhóm `owner`, `manager`, `warehouse_staff`, `delivery_staff`, `customer_service` và không token. Script nằm ở scratchpad (`qa_lot2.py`, `qa_lot3.py`, `qa_lot4.py`, `qa_lot6.py`, `qa_lot7.py`). Toàn bộ SĐT/tên/địa chỉ là dữ liệu giả (`0900000xxx`, `[Địa chỉ giao giả]`).
Mã giá vốn: quét JSON mọi endpoint với token `manager`/`warehouse_staff` theo 21 khoá `COST_KEYS` và theo số mồi `77777` (giá vốn giả) — không thấy rò.

### Kết luận theo lô

| Lô | Phạm vi | Kết luận | Lý do một dòng |
|---|---|---|---|
| 2 | R1 lọc hành động AI + `counts`; R2 `GET /api/guidance/<type>/<id>/` | **APPROVED (có điều kiện)** | Không lỗi mới. Nợ N1 (ghi chú tự do lọt vào nhãn timeline) đã được dev ghi và chờ Duy quyết; theo bảng mức lỗi N1 là Critical nên **phải chốt trước khi lên production**. |
| 3 | R3 `reason`, lọc `customer`/`batch`, `month` hoàn tiền, SĐT đầy đủ, bỏ lý do hoàn khỏi timeline đơn | **APPROVED (có điều kiện)** | Cùng N1. 3 lỗi Low (khoảng trắng trong tham số). |
| 4 | B5 lý do giao thất bại; B6 gán/đổi người giao, `deliverers`; R4 | **APPROVED** | 231/232, ca còn lại là giả tượng SQLite (⏸ chờ Postgres). Không lỗi chặn. |
| 6 | B2 quyền `sales.view_customer_list`, `customer-directory` | **APPROVED (có điều kiện)** | Không lỗi chặn. SĐT nằm trong URL `?q=` nên vào log máy chủ (L6-N2), cần Duy quyết. |
| 7 | R5 lô hàng, R6 sổ kho, R7 kho, R7b nhập/xuất tay | **REJECTED** | L7-B1 (Medium): PUT/PATCH sửa được bút toán tồn kho, không audit, không ảnh hưởng sổ. Sửa một dòng (`http_method_names`). Lỗi có sẵn ở HEAD nhưng nằm trong phạm vi R7b nên vẫn chặn theo bảng mức lỗi; điều phối viên có thể quyết ghi nhận nếu muốn commit lô khác trước. |

### Số liệu

Chạy HTTP thật sau khi sửa lại các kỳ vọng sai của script: Lô 2 210/212, Lô 3 124/128, Lô 4 231/232, Lô 6 164/167, Lô 7 215/222. Tổng 961 ca HTTP: 944 pass, 17 chưa pass. Phân loại 17 ca: 6 lỗi thật (nợ N1 ×3, L7-B1 ×2 ca PUT/PATCH, L6-N2), 7 lỗi Low, 4 là giả tượng SQLite hoặc lỗi script, không tính lỗi sản phẩm (B6-RACE, POST kho đồng thời, và 1 ca "audit" của Lô 6 do script khớp tên trường `note`, thực tế `changes` chỉ chứa tên trường).
Suite backend đầy đủ: `manage.py test` → **2295 test OK** (125 s).

### Lô 2 — R1, R2

| AC | Kết quả | Bằng chứng |
|---|---|---|
| R1 lọc `?action=`, `?status=`, `counts` | PASS | `qa_lot2.py`: lọc đúng, `counts` khớp danh sách, tham số rác trả 400, không 500 |
| R1 phân quyền | PASS | `owner`/`manager` 200; `warehouse_staff`/`delivery_staff`/`customer_service` 403; không token 401 |
| R2 timeline order/receipt/delivery/refund/customer/batch | PASS | mỗi loại gọi thật bằng token đủ nhóm; 404 cho id không có; IDOR (id của đơn khác, delivery của shipper khác) bị chặn theo scope |
| R2 `Cache-Control: no-store` trên delivery, customer | PASS | kiểm header từng response |
| R2 không lộ giá vốn | PASS | quét `COST_KEYS` + số mồi, token manager/kho: 0 khoá |
| R2 không lộ SĐT/tên/địa chỉ giả cắm trong ghi chú | **FAIL (N1)** | xem N1 |
| R2 ca ngoài đường thuận | PASS | loại không hợp lệ (`/api/guidance/xyz/1/`), id `0`, âm, `99999999999999999999`, chữ Ả Rập, `%00`; đều 404/400 |

### Lô 3 — R3

| AC | Kết quả | Bằng chứng |
|---|---|---|
| R3 `reason` trong cây huỷ/hoàn | PASS | `qa_lot3.py` |
| Lọc đơn `?customer=`, `?batch=` (+ gộp với `q`, `status`) | PASS | kết quả đúng; tham số rác `abc`, `-1`, `1e9`, `9999999999999999999` → 400 `INVALID_FILTER` hoặc rỗng, không 500 |
| Lọc hoàn tiền `?month=YYYY-MM` | PASS | đúng kỳ, `2026-13`, `2026-1`, `abc` → 400 |
| SĐT đầy đủ chỉ cho nhóm có quyền | PASS | `owner`/`manager` thấy; kho/giao theo scope; không token 401 |
| Timeline đơn không còn lý do hoàn | PASS | lý do hoàn không xuất hiện trong timeline đơn |
| Timeline đơn không ghép ghi chú tự do khi huỷ đơn đã thu | **FAIL (N1)** | nhãn có "— lý do: …" kèm SĐT giả |
| Hạng Low: `customer=%201`, `month=%202026-10`, `2026-10%20` | FAIL (Low) | trả 200 thay vì 400: tham số được cắt khoảng trắng rồi chấp nhận |

### Lô 4 — B5, B6, R4

| AC | Kết quả | Bằng chứng |
|---|---|---|
| B5 lý do giao thất bại (`NOT_MET`...), ghi chú | PASS | `qa_lot4.py`; thiếu lý do 400; lý do lạ 400; bấm đúp: `[200, 400, 400, 400]` |
| B5 ghi chú thất bại chặn SĐT | PASS | SĐT dạng liền/cách/chấm bị 400 |
| B6 gán/đổi người giao, danh sách `deliverers` | PASS | owner/manager 200; kho/giao/CSKH 403; không token 401; người giao không thuộc nhóm `delivery_staff` 400; phiếu `COMPLETED`/`CANCELLED` 400 |
| B6 AuditLog | PASS | `assign_deliverynote` có `{"assigned_to": {"from": null, "to": 4}}` (chỉ khoá `id`, không tên/SĐT) |
| B6 đua: hai người cùng đổi | ⏸ | trên SQLite cả hai nhận 200 vì `select_for_update` là no-op. Mã đúng mẫu; cần chạy lại trên Postgres |
| R4 | PASS | theo `qa_lot4.py` |
| Giao nhận: shipper chỉ thấy phiếu của mình, cửa sổ 7 ngày | PASS | phiếu 30 ngày trước → 404 với `delivery_staff` |

### Lô 6 — B2

| AC | Kết quả | Bằng chứng |
|---|---|---|
| Quyền `sales.view_customer_list` cấp cho `owner`, `manager` | PASS | `migrate delivery 0004`/`sales 0011` (lùi) thu quyền: cả hai nhóm rỗng; `migrate` (tiến) cấp lại đúng 2 nhóm, các nhóm khác không đổi |
| `GET /api/sales/customer-directory/` | PASS | owner/manager 200; kho/giao/CSKH 403; không token 401 |
| Danh sách/chi tiết không lộ giá vốn | PASS | quét `COST_KEYS` |
| `Cache-Control: no-store` | PASS | có trên danh sách, chi tiết |
| Phân trang, tìm kiếm, tham số rác | PASS | `page_size` rác, `ordering` lạ → 400, không 500 |
| Audit `update_customer` không chứa PII | PASS | `changes` chỉ có `{"fields": ["name","note"]}` (tên trường, không giá trị). Ca tự động báo FAIL do script khớp chữ `note`; đã xác nhận bằng tay |
| Chi tiết `id='١'` → 404 | FAIL (Low) | trả 200 (khách 1): Django coi chữ số Ả Rập là số |
| SĐT trong URL `?q=` không vào log | **FAIL (L6-N2)** | xem L6-N2 |

### Lô 7 — R5, R6, R7, R7b

| AC | Kết quả | Bằng chứng |
|---|---|---|
| R5 lô hàng (lọc, phân trang, `scope`) | PASS | `qa_lot7.py` |
| R5 không lộ giá vốn cho manager/kho | PASS | quét `COST_KEYS` |
| R6 sổ kho (`ledger`, lọc `item`, tham chiếu) | PASS | 14 dòng, lọc `item=1` 11 dòng; `reference_link` đúng cho đơn/phiếu nhập |
| R6 tham chiếu lạ không đẩy chuỗi tự do | FAIL (Low) | dòng cũ có text tự do chứa SĐT giả vẫn bị trả nguyên ở `reference_display` |
| R6 `reference_link` stocktake không tồn tại là null | FAIL (Low) | trả `{'kind':'stocktake','id':9999}` |
| R7 kho (tạo, đổi tên, trùng tên, `is_group`) | PASS (có Low) | trùng tên trả 400 `WAREHOUSE_NAME_DUPLICATE`; xem Low bên dưới |
| R7 POST đồng thời cùng tên chỉ tạo 1 kho | ⏸ | SQLite: `[201,400×6,500]`, đúng 1 kho nhưng 1 lần 500 "database is locked" (giả tượng). Cần Postgres |
| R7b nhập/xuất tay: xem, tạo, phân quyền | PASS | GET: owner/manager/kho 200, giao/CSKH 403, không token 401; POST giao/CSKH 403; POST bút toán cũ trả 201 nhưng không đổi tồn, không ghi sổ (quyết định D-1) |
| R7b bút toán không sửa được | **FAIL (L7-B1)** | PUT 400 nhưng PATCH 200 |

### Phân quyền (BE, HTTP thật)

| Hành động | owner | manager | warehouse_staff | delivery_staff | customer_service | không token |
|---|---|---|---|---|---|---|
| R1 AI actions | 200 | 200 | 403 | 403 | 403 | 401 |
| R2 guidance order/refund/customer | 200 | 200 | 403 | 403 | 403 | 401 |
| R2 guidance delivery | 200 | 200 | 403 | 200 (phiếu của mình) | 403 | 401 |
| B6 gán người giao | 200 | 200 | 403 | 403 | 403 | 401 |
| B5 báo giao thất bại | 200 | 200 | 403 | 200 (phiếu của mình) | 403 | 401 |
| customer-directory | 200 | 200 | 403 | 403 | 403 | 401 |
| R5 lô / R6 sổ kho | 200 | 200 | 200 | 403 | 403 | 401 |
| R7 kho: GET | 200 | 200 | 200 | 403 | 403 | 401 |
| R7 kho: POST/PATCH | 200 | 403 | 403 | 403 | 403 | 401 |
| R7b stock-entries: GET | 200 | 200 | 200 | 403 | 403 | 401 |
| R7b stock-entries: POST | 200/201 | chưa ghi riêng | chưa ghi riêng | 403 | 403 | 401 |

Ghi chú: guidance/customer cho `delivery_staff` trả 403 trong khi detail API trả 200 (chặt hơn, an toàn). Bảng thể hiện kết quả quan sát được; ô ghi 200 (phiếu của mình) có thêm ca IDOR sang phiếu người khác → 404.

### Rò giá vốn
Quét 21 khoá `COST_KEYS` + số mồi 77777 trên mọi endpoint của 5 lô với token manager/kho/giao: **không rò** (owner có `unit_cost` ở chi tiết đơn là đúng quyền). Khoá mới ghi vào AuditLog (`assigned_to`, `fields`, `status`) và qua API (`reference_link`, `counts`, `deliverers`) chỉ chứa id/trạng thái, không tính ngược được giá vốn.

### Rò dữ liệu cá nhân
- API/HTML công khai: không thuộc phạm vi các lô này, không có thay đổi.
- Ghi chú/lý do cắm SĐT `0900000999` rồi quét timeline, audit, danh sách, AI: **lọt ở nhãn timeline** do N1 (xem dưới). Audit, AI, danh sách: không lọt.
- Group không cần: `customer-directory` 403 với kho/giao/CSKH.
- `no-store`: có trên endpoint dữ liệu khách.
- Log máy chủ: có SĐT khi tìm bằng `?q=<SĐT>` (L6-N2).
- Ảnh/report chỉ dùng dữ liệu giả.

### Hồi quy
Suite đầy đủ 2295 test OK. `makemigrations --check --dry-run` → "No changes detected" (có cảnh báo content.W001 thiếu cấu hình SELLER_*, đã có từ trước). `scripts/check_naming.py` → OK, không vi phạm mới (1 file giảm vi phạm, chưa khoá bằng `--update`). Migration lùi/tiến trên bản sao DB: sạch, quyền thu rồi cấp lại đúng.

### Lỗi

#### N1 — Ghi chú tự do (có SĐT) lọt vào nhãn timeline đơn/hoàn · Critical theo bảng mức lỗi (đã ghi là nợ, chờ Duy) · Lô 2 và 3
- Tái hiện: owner gọi `POST` huỷ đơn đã thu (`cancel_paid_order`) với `note` = "khách gọi lại số 0900000999 giao [Địa chỉ giao giả]" (BE không chặn). Rồi `GET /api/guidance/order/<id>/` và timeline đơn → nhãn "Huỷ đơn, hoàn hàng về lô gốc — lý do: khách gọi lại số 0900000999 …". Tương tự `mark_refund_failed` note và `Refund.reason` trong `GET /api/guidance/refund/<id>/` ("Tạo phiếu hoàn 100.000 ₫ — khách gọi lại số 0900000999 giao [Địa chỉ giao giả]").
- Mong đợi: nhãn timeline không ghép văn bản tự do; hoặc ghi chú huỷ bị chặn SĐT như `failure_note` của B5.
- Ảnh hưởng: chỉ người có quyền xem đơn/hoàn thấy; dữ liệu đã nằm sẵn ở đơn. Nhưng bất biến 9 coi PII trong log/timeline là Critical nếu nhãn đi tiếp tới AI hoặc nhật ký. Đề xuất: bỏ phần "— lý do: …" khỏi nhãn, hoặc chạy bộ lọc SĐT lúc nhận ghi chú.

#### L7-B1 — PUT/PATCH sửa được bút toán nhập/xuất tay · Medium · R7b
- Tái hiện: `PATCH /api/inventory/stock-entries/<id>/` token `owner` hoặc `warehouse_staff` với `{"qty_change":"999","reason":"sửa"}` → 200, `qty_change` và `reason` đổi; sổ kho không đổi, `AuditLog` không có dòng.
- Mong đợi: chứng từ không sửa được (405). Thực tế: PATCH 200 (PUT thiếu trường trả 400; PUT đủ trường chưa thử riêng, nhưng cùng `UpdateModelMixin` nên nhiều khả năng cũng sửa được).
- Ảnh hưởng: sai lệch giữa bút toán và sổ kho (tồn kho/chứng từ). Có sẵn ở HEAD, thuộc phạm vi R7b.
- Sửa gợi ý: `http_method_names = ["get", "post", "head", "options"]` cho `StockEntryViewSet`.

#### L6-N2 — SĐT khách nằm trong URL `?q=` và log máy chủ · Medium · cần Duy quyết · Lô 6
- Tái hiện: `GET /api/sales/customer-directory/?q=0900000101` bằng token owner; dòng log runserver chứa nguyên SĐT.
- Mong đợi: SĐT không có trong URL/log (bất biến 9: log, URL không chứa dữ liệu cá nhân). Đây là cách tìm kiếm đã quy ước trong thiết kế (R-search), không thể đổi mà không đổi API (POST tìm kiếm hoặc băm SĐT).
- Ảnh hưởng: log nginx/Cloud Run lưu SĐT thật khi thủ kho/chủ tìm khách.

#### Lỗi Low (ghi nhận, không chặn)
- L3-a: `customer=%201`, `month=%202026-10`, `2026-10%20` được chấp nhận (cắt khoảng trắng) thay vì 400.
- L6-a: `customer-directory/١/` (chữ số Ả Rập) trả khách 1.
- L7-a: dòng sổ kho cũ có `reference` tự do bị trả nguyên ở `reference_display`.
- L7-b: `reference_link` cho stocktake không tồn tại không null.
- L7-c: tạo kho thiếu `name` trả 400 không kèm `code` `WAREHOUSE_NAME_REQUIRED`.
- L7-d: tên NFD (`Kho đông lạnh` dạng tổ hợp) hoặc chen ký tự rộng-không của tên đã có không bị coi là trùng.
- L7-e: PATCH kho không ghi AuditLog; `is_group` đổi được trên kho đã có lô.
- L4-a: chống SĐT trong `failure_note` bị lách bằng chữ chen giữa số (`09aa00aa00aa555`).
- L4-b: định dạng giờ lẫn lộn (`+07:00` ở danh sách khách, `Z` ở đơn chi tiết).

### ⏸ Chưa kiểm được
- Ba ca đồng thời cần Postgres (không có trên máy QA): tạo kho cùng tên, đổi khách cùng lúc, đổi người giao cùng lúc (B6-RACE). SQLite không có khoá hàng nên kết quả vô nghĩa. Mã dùng đúng mẫu `select_for_update`; QA trên staging (Postgres) nên chạy `qa_lot4.py`/`qa_lot7.py` lại.
- Không động đến Lô 8, 9, 10.

### Lệnh đã chạy
```
cd backend && .venv/bin/python manage.py test                -> 2295 test OK (125 s)
QA_DB=<tmp>.sqlite3 runserver 127.0.0.1:8765 (qa_settings)    -> seed bằng qa_seed.py (dữ liệu giả)
python3 qa_lot2.py                                           -> 210/212 (2 = N1)
python3 qa_lot3.py                                           -> 124/128 (1 = N1, 3 Low)
python3 qa_lot4.py                                           -> 231/232 (1 = giả tượng SQLite)
python3 qa_lot6.py                                           -> 164/167 (1 Low, 1 lỗi script, 1 L6-N2)
python3 qa_lot7.py                                           -> 215/222 (L7-B1 x2, 4 Low, 1 giả tượng SQLite)
migrate delivery 0004 / sales 0011 rồi migrate               -> sạch, quyền thu rồi cấp lại cho owner+manager
manage.py makemigrations --check --dry-run                   -> No changes detected
python3 scripts/check_naming.py                              -> OK, không phát sinh vi phạm mới
pkill -f "runserver 127.0.0.1:8765"
```

---

## BE Lô 8, 9, 10 · lần 1 · 2026-10-02

**Cách kiểm:** dựng backend thật (`runserver 127.0.0.1:8765`, SQLite tạm `qa810.sqlite3` do `qa810_seed.py` dựng dữ liệu giả: 10 tài khoản đủ 5 nhóm + hai quản lý + hai thủ kho + một tài khoản không nhóm, 2 kho, 7 lô, 4 phiếu nhập, 3 hoá đơn mua, 2 khoản chi phí phụ, 6 phiếu giao với 3 người giao khác nhau). Không đụng DB staging/production, không đọc `*.env`. Gọi HTTP thật bằng token từng nhóm và không token. Giá nhập mồi `77777`, `66666`, `55555`, `123457`, chi phí mồi `987654`, `424242`, SĐT giả `0900000999`. Script ở scratchpad: `qa_lot8.py` (179 ca), `qa_lot9.py` (256 ca), `qa_lot10.py` (190 ca); trợ giúp `qa810_http.py`, `qa810_order.py` (tạo đơn + thanh toán bằng service), `qa810_ai.py` (dispatch AI thật trong tiến trình).

### Kết luận theo lô

| Lô | Phạm vi | Kết luận | Lý do một dòng |
|---|---|---|---|
| 8 | B1 (ED-27), R8 (ED-28 phía BE) Kiểm kê | **APPROVED (có điều kiện)** | 179/179 ca HTTP. Không lỗi chặn. Điều kiện của techlead giữ nguyên: **Duy phải xác nhận BR-KK-09 phương án B** trước khi lên production (QA chỉ xác nhận hệ thống làm đúng phương án B). Hai điểm Low/ghi nhận N8-1, N8-2. |
| 9 | R9 Hàng hoàn (ED-26) | **APPROVED** | 256/256 ca HTTP. Không lỗi chặn; hai điểm Low (403 thay vì 404 khi sửa phiếu người khác, định dạng số trong lỗi vượt kg). |
| 10 | R10 Phiếu nhập (ED-20) | **APPROVED** | 184/190, 6 ca còn lại: 4 là giả tượng của script (chuỗi `55555`/`91919` nằm trong số tiền hoá đơn hợp lệ `555551.00`, `919190.00`), 2 là Low. |

### Số liệu

Tổng 625 ca HTTP thật: **619 pass**, 6 không pass (4 giả tượng script, 2 Low), 0 lỗi chặn. Lô 9 lần chạy đầu 248/254 do lỗi script (dùng chung phiếu giao cho các ca biên, `note` kiểu số tạo phiếu thừa); sau khi sửa script và dựng lại DB sạch: 256/256. Lô 8 lần chạy đầu 172/177 do script khớp sổ kho gồm cả dòng nhập lô và do luồng xác nhận AI cần mở xem 3 giây; sau khi sửa script: 179/179. Không sửa mã sản phẩm.

Suite backend đầy đủ `manage.py test`: **2438 test OK** (134 s). Lần chạy đầu của tôi trong cùng phiên báo 3 ERROR ở `apps.ai.registry.tests.test_p8_pii_sweep` và `test_p8_qa_lo2_sweep` ("Object of type date is not JSON serializable" trong `truncate_read_result`). Chạy lại riêng hai tệp đó: OK; chạy lại toàn bộ: 2438 OK. Quét tay mọi lệnh AI đọc bằng token owner/manager/kho trên dữ liệu QA: không có 5xx. Khả năng cao là lô khác (Lô 11, 13) đang sửa file dở lúc đó. Không thuộc Lô 8, 9, 10, nhưng điều phối viên nên chạy lại `manage.py test` ngay trước khi commit.

### Lô 8 — B1, R8 Kiểm kê

| Mã AC / ca | Kết quả | Bằng chứng (`qa_lot8.py`, HTTP thật) |
|---|---|---|
| ED-27-AC1 tạo kèm dòng: 201, `system_qty` do server chụp, `difference_qty` tính, DRAFT, kho chưa đổi | PASS | tồn 30 đếm 28,5 → `system_qty` 30.000, `difference_qty` -1.500; client gửi `system_qty=999` bị bỏ qua; sổ kho không có dòng RECONCILE |
| ED-27-AC2 đếm nhiều hơn sổ không lý do: 400 `BR-KK-04` | PASS | 400 `BR-KK-04` kèm `line_index`; lý do toàn khoảng trắng cũng 400; có lý do → 201; lỗi một dòng thì không tạo phiếu (rollback) |
| ED-27-AC3 phiếu APPROVED: sửa dòng/ghi chú bị chặn | PASS | `POST …/lines/` và `PATCH` sau duyệt → 400 `RECON_NOT_DRAFT`, dữ liệu không đổi |
| ED-27-AC4 đếm âm, lô trùng, lô đã chốt, lô không tồn tại, batch lạ | PASS | 400 `RECON_LINE_INVALID` kèm `line_index`, tiếng Việt, không chép lại giá trị; `batch` = `abc`, `0`, `-3`, `True`, `None`, `1.5`, `1e3`, chữ số Ả Rập, 30 chữ số → 400, không 500 |
| ED-27-AC5 quyền | PASS | tạo/sửa dòng: owner, manager, kho 201/200; giao, CSKH, không nhóm 403; không token 401. Duyệt: owner, manager; kho/giao/CSKH 403 |
| ED-27-AC6 giá vốn | PASS | quét 22 khoá `COST_KEYS` + số mồi, token owner/manager/kho, mọi trang list và chi tiết: 0 khoá, 0 số mồi, không khoá nào có chữ amount/price/cost/rate/value |
| Thay toàn bộ dòng (`POST …/lines/`) với `expected_updated_at` | PASS | đúng bản: 200, chụp lại `system_qty`; thiếu → 400 `EXPECTED_UPDATED_AT_REQUIRED`; sai định dạng (`hôm qua`, thiếu múi giờ, số, mảng, rỗng) → 400 `EXPECTED_UPDATED_AT_INVALID`, không 500 |
| 409 `STALE_STATE` (ngoài đường thuận: màn hình cũ, hai người sửa) | PASS | bản cũ → 409 kèm `updated_at` mới và `updated_by_name` (tên nhân viên, ví dụ "Quản Lý Thử"); không đổi dữ liệu; sửa ghi chú cũng làm màn hình cũ lỗi thời; thay bằng `[]` hoặc lô trùng → 400 và giữ nguyên dòng cũ (rollback) |
| BR-KK-02 người nhập không duyệt được | PASS | manager tạo rồi tự duyệt → 400 `BR-KK-02`, tồn không đổi; `approve_blocked_reason.code="BR-KK-02"`, `available_actions` không có `approve` nhưng có `edit_lines`; owner và manager2 thấy `approve` |
| BR-KK-08 người đã sửa số đếm không duyệt được | PASS | kho tạo, owner sửa dòng, owner duyệt → 400 `BR-KK-08`; `approve_blocked_reason.code="BR-KK-08"`; manager (chưa đụng) duyệt → 200, tồn bQ 20 → 18, sổ kho đúng một dòng RECONCILE -2, audit `approve_stockreconciliation` |
| **BR-KK-09** tồn 50, đếm 48, bán 5, duyệt | PASS (theo phương án B) | đơn thật 5 kg Mực QA + thanh toán: tồn 45; owner duyệt → **43**, sổ kho RECONCILE -2; dòng giữ `system_qty` 50/`difference_qty` -2. Ca thứ hai: chụp tồn 43 đếm 44 có lý do, bán thêm 4 (39), duyệt → 40 |
| `RECON_EMPTY` | PASS | duyệt phiếu rỗng → 400 `RECON_EMPTY`, vẫn DRAFT |
| `RECON_STOCK_INSUFFICIENT` + rollback | PASS | phiếu 2 dòng (bP -1, bK -40), bán thêm 35 kg rồi duyệt → 400 `RECON_STOCK_INSUFFICIENT` kèm `line_index=1`; phiếu vẫn DRAFT, **dòng 0 không ghi sổ**, không có audit approve, `approved_by` trống; thông điệp không chứa giá/SĐT; đếm lại (replace) rồi duyệt được |
| Duyệt lần 2 / lần 3 | PASS (có N8-1) | 400, tồn không đổi, sổ kho vẫn 1 dòng, audit approve đúng 1 |
| AI tạo phiếu không gửi được `lines` (M1) | PASS | dispatch AI thật dưới `ai_audit_scope` với `args.lines` có 1 dòng → 201, **0 dòng**; audit chỉ `{"line_count": 0}`; duyệt phiếu đó → `RECON_EMPTY` |
| Lọc, phân trang | PASS | `status` đơn/nhiều giá trị, `warehouse`, `date_from`, `date_to`; `status=XYZ`, `warehouse=abc/-1/0`, ngày sai (`2026-02-30`) → 400 `INVALID_FILTER`; chuỗi SQLi trong `status` → 400; `page=9999` → 404; không 500 |
| Không xoá chứng từ, field khoá | PASS | `DELETE` (owner và kho) → 405; gửi `status`/`created_by`/`approved_by` khi tạo hoặc PATCH → 400 (BR-PQ-14/16) |
| AuditLog | PASS | `create_stockreconciliation`, `update_reconciliation_lines`, `update_stockreconciliation`, `approve_stockreconciliation` đều có; `changes` chỉ có `line_count`/`fields` |
| Migration `inventory.0005_stockreconciliation_updated_at` | PASS | trên bản sao DB đã có 18 phiếu: lùi về 0004 rồi tiến lại, 0 phiếu có `updated_at` rỗng |
| ⏸ Hai người sửa dòng / duyệt cùng lúc | ⏸ | cần Postgres (xem cuối) |

### Lô 9 — R9 Hàng hoàn

| Mã AC / ca | Kết quả | Bằng chứng (`qa_lot9.py`, HTTP thật) |
|---|---|---|
| ED-26 tạo phiếu hoàn, đường thuận | PASS | người giao A tạo cho phiếu giao của mình → 201 DRAFT/PENDING, `created_by` = chính A (client không quyết), `outside_minutes` đo được; kho chưa đổi trước khi duyệt; body đủ 22 khoá, không khoá lạ |
| Phạm vi người giao, IDOR | PASS | B tạo cho phiếu của A, phiếu chưa gán, phiếu của B khi là A, phiếu không tồn tại: đều **404 cùng thông điệp** (không phân biệt "của người khác" và "không tồn tại"); không phiếu hoàn nào được tạo từ các ca IDOR; list/chi tiết/guidance/dòng thời gian của A: B 404 hoặc không thấy |
| Không vượt kg đã giao | PASS | đã hoàn 2 + 3.001 > 5 → 400 `RETURN_QTY_EXCEEDS` kèm `delivered_qty`, `already_returned_qty`; lấp đầy đúng biên 3.000 → 201, thêm 0.001 → 400; 0, âm, `NaN`, `1e3`, quá 3 chữ số thập phân → 400 |
| Bấm đúp / hai lần liên tiếp | PASS | 3 lần liền 2.5 kg trên phiếu còn 3 kg → `[201, 400, 400]` (tuần tự; đồng thời thật ⏸) |
| Duyệt lần 2 → 409 | PASS | 409 `STALE_STATE`, tồn không đổi; PATCH phiếu đã duyệt → 400 `RETURN_NOT_EDITABLE`; PUT đổi qty → 400 |
| BR-HV-04 lô đã chốt | PASS | duyệt vào lô CLOSED → 400, `decision` **không được lưu** (vẫn PENDING + DRAFT), tồn không đổi |
| Phân quyền | PASS | đọc: owner/manager/kho/giao 200, CSKH/không nhóm 403, không token 401. Tạo: owner, kho 201; manager 403 (không có quyền tạo, đúng contract); giao 201 trên phiếu của mình; CSKH 403. Duyệt: owner, manager 200; kho, giao, CSKH, không nhóm 403; không token 401; kho không đổi sau các lần duyệt bị cấm |
| `note` có SĐT giả không lọt ra ngoài API hàng hoàn | PASS | note chứa `0900000999` + địa chỉ giả: chỉ owner và người giao A thấy ở API hàng hoàn; B không thấy ở list (mọi trang) và chi tiết 404; không có trong AuditLog, AiAction, sổ kho (`reference` của cả owner/manager/kho), dòng thời gian/guidance của return và delivery cho mọi vai, và **log máy chủ** |
| Phân trang, lọc | PASS | `page` biên, `page_size` rác, lọc `status`/`decision`/`delivery_note`/`date`; 27 ca tham số sai → 400 `INVALID_FILTER`, không 500; phân trang giữ phạm vi người giao |
| `Cache-Control: no-store` | PASS | có trên list, chi tiết, POST 400, 401 |
| Giá vốn | PASS | owner/manager/kho/giao/…: không `COST_KEYS`, không số mồi trong list và chi tiết |
| AuditLog | PASS | `return_to_warehouse` mỗi lần tạo, `approve_returntostock` mỗi lần duyệt, không khoá giá vốn |
| ⏸ Hai phiếu cùng tranh phần kg còn lại / hai người duyệt cùng lúc | ⏸ | cần Postgres |

### Lô 10 — R10 Phiếu nhập

| Mã AC / ca | Kết quả | Bằng chứng (`qa_lot10.py`, HTTP thật) |
|---|---|---|
| ED-20 danh sách và chi tiết | PASS | phân trang 20, sắp xếp `-received_date,-id`, `items_summary`, `total_qty`, `batch_codes`, `invoice`; detail id chữ → 404; id không có → 404 |
| ED-20-AC5 không lộ giá vốn cho manager/kho | PASS | 30 ca quét: `rate`, `purchase_amount`, `landed_unit_cost`, `costs`, `allocated_amount` và mọi `COST_KEYS` vắng ở manager và kho (list, chi tiết, từng id, từng trang), số mồi `66666`, `55555` (giá nhập), `987654`, `424242` (chi phí phụ) vắng. Owner thấy `purchase_amount`, `rate`, `costs` (đúng quyền) |
| D-3 manager thấy `invoices[].amount`, kho không có `invoices[]` | PASS | manager: `invoices` có `amount` (`555551.00`, `444442.00`), `is_paid`; kho: không có `invoices` (và không có khoá `amount`); list: kho/manager chỉ có `invoice: {id}` |
| Lọc sai → 400 | PASS (có Low) | 63 ca: `status=XYZ`, `supplier=abc/0/-1`, `month=2026-13/abc`, `date_from=abc`, `has_invoice=maybe` → 400 `INVALID_FILTER`; lọc đúng trả đúng tập |
| Phân quyền | PASS | owner/manager/kho 200; giao/CSKH/không nhóm 403; không token 401 |
| Ghi (`PurchaseReceiptSerializer` giữ nguyên) | PASS | tạo/sửa như trước, giao/CSKH 403; không DELETE (405); phiếu `SUBMITTED` không sửa được; không sinh khoá giá vốn ở phản hồi ghi của kho |
| AuditLog | PASS | không có khoá giá vốn/PII |

### Phân quyền (BE, HTTP thật)

| Hành động | owner | manager | warehouse_staff | delivery_staff | customer_service | không token |
|---|---|---|---|---|---|---|
| R8 kiểm kê: GET list/chi tiết | 200 | 200 | 200 | 403 | 403 | 401 |
| B1 tạo phiếu / `POST …/lines/` / PATCH ghi chú | 201/200 | 201/200 | 201/200 | 403 | 403 | 401 |
| Duyệt kiểm kê | 200 | 200 | 403 | 403 | 403 | 401 |
| Duyệt, người đã nhập hoặc sửa số | 400 BR-KK-02/08 | 400 BR-KK-02/08 | (không có quyền) | 403 | 403 | 401 |
| DELETE kiểm kê | 405 | 405 | 405 | 403 | 403 | 401 |
| R9 hàng hoàn: GET | 200 | 200 | 200 | 200 (phiếu của mình) | 403 | 401 |
| R9 tạo phiếu hoàn | 201 | 403 | 201 | 201 (phiếu của mình), 404 phiếu người khác | 403 | 401 |
| R9 PATCH ghi chú | 200 | chưa ghi riêng | chưa ghi riêng | 403 | 403 | 401 |
| R9 duyệt hoàn | 200 | 200 | 403 | 403 | 403 | 401 |
| R10 phiếu nhập: GET | 200 | 200 | 200 | 403 | 403 | 401 |
| R10 thấy `purchase_amount`/`rate`/`costs` | có | không | không | n/a | n/a | n/a |
| R10 thấy `invoices[].amount` | có | có (D-3) | không có `invoices[]` | n/a | n/a | n/a |

### Rò giá vốn
Quét JSON (mọi mức lồng nhau) của cả ba lô với token owner/manager/kho/giao theo 22 khoá `COST_KEYS` (đã có `purchase_amount`) và số mồi giá nhập, chi phí phụ: **không rò** cho người thiếu quyền. Kiểm kê không có trường tiền nào (chỉ kg). Khoá mới trong AuditLog (`line_count`, `fields`, `assigned_to`...) và qua API (`approve_blocked_reason`, `updated_by_name`, `available_actions`, `warehouse_names`, tổng kg) chỉ là số đếm/kg/tên nhân viên, không tính ngược ra giá vốn được. Ghi nhận thông tin (không phải lỗi): manager có thể suy ra đơn giá nhập từ `invoices[].amount ÷ tổng kg`; D-3 cho phép đúng việc này và API `/api/purchasing/invoices/` đã trả sẵn cho manager từ trước.

### Rò dữ liệu cá nhân
- API công khai/HTML Shop: không thuộc phạm vi ba lô, không đổi.
- Kiểm kê: phản hồi chỉ có tên hiển thị của nhân viên; SĐT/tên/địa chỉ của khách mua đơn bán giữa chừng (`0900000555`, "Khách Thử") không xuất hiện trong list/chi tiết của owner, manager, kho; AuditLog chỉ `line_count`/`fields`; log máy chủ không có SĐT.
- Hàng hoàn: `note` cắm SĐT và địa chỉ giả chỉ thấy ở API hàng hoàn cho người có quyền và đúng phạm vi; không lọt vào AuditLog, AiAction, sổ kho, timeline/guidance, log máy chủ; có `no-store`.
- Phiếu nhập: nhà cung cấp là doanh nghiệp, không có dữ liệu khách; không tên/SĐT/địa chỉ khách trong JSON.
- Ảnh và report chỉ dùng dữ liệu giả.

### Hồi quy
Suite đầy đủ **2438 test OK**. `makemigrations --check --dry-run` → "No changes detected". `scripts/check_naming.py` → OK, không phát sinh vi phạm mới. Các luồng liền kề: tạo đơn + thanh toán (dùng để bán giữa chừng trong BR-KK-09) chạy đúng; giao nhận và guidance của người giao không đổi; `/api/purchasing/invoices/` và sổ kho vẫn như cũ.

### Lỗi

Không có lỗi Critical/High/Medium trong ba lô.

#### N8-1 — Duyệt kiểm kê lần hai trả mã chung `BUSINESS_ERROR`, không phải `RECON_NOT_DRAFT` · Low · ED-27 / BR-PQ-10
- Tái hiện: duyệt phiếu KK thành công, rồi `POST /api/inventory/reconciliations/<id>/approve/` lần nữa bằng owner.
- Mong đợi (03-dev-notes, bảng mã lỗi và dòng "Duyệt đồng thời"): `RECON_NOT_DRAFT`. Hàng hoàn dùng 409 `STALE_STATE` cho cùng tình huống, cũng ghi để "đồng nhất với kiểm kê".
- Thực tế: 400 `{"detail":"Phiếu kiểm kê đã được duyệt.","code":"BUSINESS_ERROR"}`. Hành vi an toàn (tồn không đổi, sổ kho 1 dòng, 1 audit approve), chỉ FE không phân biệt được bằng mã. Gợi ý: đổi `apply_reconciliation` dùng `RECON_NOT_DRAFT` (một dòng) hoặc sửa dev-notes.

#### N8-2 — Chủ AI không bao giờ xác nhận được đề xuất AI cho bất kỳ lệnh kiểm kê nào · Low (có sẵn, ngoài diff Lô 8) · M1
- Tái hiện: owner `POST /api/ai/commands/inventory.stockreconciliation.create/call/` → 200 `proposal` mức C. Mở `GET /api/ai/actions/<id>/`, chờ 3 giây, `POST …/confirm/` → 400 `BR-KK-02` "Người duyệt không được là người nhập hoặc chủ AI đã nhập số kiểm kê".
- Nguyên nhân: `apps/ai/actions/services.py` bước 7 (H6) chặn mọi lệnh có chữ `stockreconciliation` khi `action.owner_id == user.id`, kể cả `create`/`replace_lines`, vốn không phải lệnh duyệt. File này không nằm trong diff Lô 8.
- Ảnh hưởng: lệnh AI `create` kiểm kê không thể thực thi qua luồng xác nhận (chỉ người khác nhận leo thang mới xác nhận được). An toàn về nghiệp vụ (không vượt quyền), nhưng M1 chỉ kiểm được qua dispatch trực tiếp. Đề nghị Tech Lead quyết: giới hạn H6 vào lệnh `approve`.

#### Lỗi Low khác (ghi nhận, không chặn)
- L9-a: `PATCH`/`approve` hàng hoàn của phiếu người giao khác trả **403** (người giao không có `change_returntostock`), không phải 404 như dev-notes ghi. Không rò: phiếu có thật và phiếu không tồn tại cho cùng 403, cùng thân thư. Chỉ là lệch tài liệu.
- L9-b: lỗi `RETURN_QTY_EXCEEDS` trả `delivered_qty` là `"5"` và `already_returned_qty` là `"0.00200000000000000"` thay vì 3 chữ số thập phân như các trường khác.
- L10-a: `?status=DRAFT,,` (dấu phẩy thừa) được chấp nhận, trả 200 thay vì 400 (tương tự `status=DRAFT,,` của kiểm kê).
- L10-b: `GET /api/purchasing/receipts/%D9%A1/` (chữ số Ả Rập) trả phiếu 1 thay vì 404; cùng loại với L6-a.
- N8-3 (thông tin): `GET` kiểm kê không có `Cache-Control: no-store`; `note` kiểm kê là chữ tự do của nhân viên. Contract không yêu cầu (chỉ hàng hoàn có), nên không tính lỗi; nếu muốn đồng nhất bất biến 9 thì thêm `NoStoreMixin`.

### ⏸ Chưa kiểm được
Máy QA không có Postgres; `select_for_update` là no-op trên SQLite nên các ca đua cho kết quả vô nghĩa. Cần chạy lại trên staging (Postgres):
- Lô 8: hai người cùng `POST …/lines/` với cùng `expected_updated_at` (kỳ vọng một 200, một 409); hai người cùng duyệt một phiếu (một 200, một lỗi, tồn đổi một lần).
- Lô 9: hai phiếu hoàn cùng lúc tranh phần kg còn lại (kỳ vọng tổng không vượt kg đã giao); hai người cùng duyệt một phiếu hoàn.
- Phía FE của ED-26, ED-28, ED-20: ngoài phạm vi lượt này (chưa có FE cho các lô BE này).

### Lệnh đã chạy
```
cd backend && .venv/bin/python manage.py test                        -> 2438 test OK (134 s); lần đầu 3 ERROR AI sweep thoáng qua (lô khác đang sửa), chạy lại OK
.venv/bin/python manage.py test apps.ai.registry.tests.test_p8_pii_sweep apps.ai.registry.tests.test_p8_qa_lo2_sweep -> OK
qa810_reset.sh (migrate + bootstrap_masterdata + qa810_seed.py)        -> seed ok
qa810_serve.sh (runserver 127.0.0.1:8765, SQLite tạm, AI_ENABLED=True)
python3 qa_lot10.py                                                   -> 184/190 (4 giả tượng script, 2 Low)
python3 qa_lot9.py                                                    -> 256/256 (DB sạch, sau khi sửa script)
python3 qa_lot8.py                                                    -> 179/179 (DB sạch, sau khi sửa script)
qa810_ai.py (dispatch AI create có lines, trong tiến trình)          -> 201, 0 dòng
migrate inventory 0004 rồi migrate inventory trên bản sao DB QA        -> sạch, 18 phiếu, 0 updated_at rỗng
manage.py makemigrations --check --dry-run                            -> No changes detected
python3 scripts/check_naming.py                                       -> OK, không vi phạm mới
pkill -f "runserver 127.0.0.1:8765"
```


## BE Lô 11, 13 · lần 1 · 2026-10-02

**Cách kiểm:** dựng backend thật (`runserver 127.0.0.1:8766`, SQLite tạm `qa1113.sqlite3` do `qa1113_seed.py` dựng dữ liệu giả: 9 tài khoản đủ 5 nhóm + hai quản lý + hai thủ kho + một tài khoản không nhóm; 6 mặt hàng QA01–QA06 (QA04 chưa giá, QA05 ngừng bán, QA06 combo, QA03 có ảnh); 3 ưu đãi, trong đó một ưu đãi cũ sai dữ liệu 150%; 5 nhà cung cấp, S1 có 3 phiếu Đã ghi nhận + 1 Nháp + 1 Đã huỷ). Không đụng DB staging/production. Gọi HTTP thật bằng token từng nhóm và không token. Số tiền mồi `77777`, `12345.67`, `0.01`, `66666`, `55555`, `424242`, `123457`, SĐT giả `0900000555`/`0900000999`. Script ở scratchpad: `qa_lot11.py` (307 ca), `qa_lot13.py` (465 ca), cùng `qa1113_inproc.py` / `qa1113_inproc13.py` (đếm truy vấn, du hành thời gian múi giờ VN, DELETE ưu đãi đã dùng), `qa1113_race.py` (6 POST song song cùng tên), `qa1113_ai.py`, `qa1113_aihttp.py` (lệnh AI thật).

### Kết luận theo lô

| Lô | Phạm vi | Kết luận | Lý do một dòng |
|---|---|---|---|
| 11 | B3 (ED-21) Nhà cung cấp | **REJECTED** | 306/307 ca HTTP (ca fail là Low). **B11-1 (Medium, chặn):** hai yêu cầu cùng lúc tạo cùng một tên nhà cung cấp đều thành công (trùng tên), dù AC "tên trùng 400" và "bấm đúp" yêu cầu chặn. Tái hiện được trên SQLite, không cần Postgres. |
| 13 | R14 (ED-30/ED-31 phía BE) Danh mục và giá | **REJECTED** | 465/465 ca HTTP pass, nhưng 2 lỗi Medium ngoài đường thuận: **B13-1** `DELETE` ưu đãi đã dùng ở đơn trả 500 (ProtectedError chưa được bắt); **B13-2** giá bán `0` được chấp nhận (Shop sẽ hiện giá 0). Thêm B13-3 (Medium/Low) cần PO/techlead quyết. |

### Số liệu

- HTTP thật: Lô 11 **306/307**, Lô 13 **465/465**; cộng ca trong tiến trình (du hành thời gian, đếm truy vấn, AI, đua tranh) và các ca thủ công ghi ở mục lỗi.
- `manage.py test` toàn bộ: **2591 test OK** (124 s) ở lần chạy cuối. Lần chạy đầu trong phiên này có 1 test đỏ `test_r2_group_type_not_registered_yet` (Lô 14 vừa đăng ký loại hướng dẫn `group` ở `apps/accounts/capabilities/next_steps.py`); đến lần chạy cuối cùng test này đã xanh (Lô 14 sửa test trong lúc tôi kiểm). Không có đỏ nào thuộc Lô 11, 13.
- Adapter: `adapter/.venv/bin/python -m pytest` -> **68 passed**. (Dùng python hệ thống thì thiếu `respx`; đây là lỗi môi trường, không phải lỗi mã.)
- `makemigrations --check --dry-run` -> No changes detected. `check_naming.py` -> không vi phạm mới.
- Không sửa mã sản phẩm.

### Lô 11 — B3 Nhà cung cấp

| Mã AC / ca | Kết quả | Bằng chứng (`qa_lot11.py`, HTTP thật) |
|---|---|---|
| ED-21-AC1 `receipt_count`, `last_received_at`, `purchase_total` chỉ tính phiếu Đã ghi nhận | PASS | S1: 3 SUBMITTED + Nháp + Đã huỷ -> đếm 3, tổng bằng Σ làm tròn(kg × giá) từng dòng (mẫu `93939.00` = 2 × 46969.50 khớp kỳ vọng); phiếu Nháp/Đã huỷ không vào số liệu; đổi trạng thái phiếu rồi gọi lại thì số đổi đúng |
| ED-21-AC2 giá vốn | PASS | 72 ca quét `COST_KEYS` + số mồi: `purchase_total` chỉ có ở owner. manager và kho: 200 nhưng 0 khoá giá vốn, 0 số mồi trong list, chi tiết, dòng thời gian. Lưu ý contract dùng tên `purchase_total` (story ghi `total_purchase_amount`), `purchase_total` đã nằm trong `COST_KEYS` |
| ED-21-AC3 NCC chưa có phiếu | PASS | `receipt_count=0`, `last_received_at=null`, tổng `0.00` |
| ED-21-AC4 quyền đọc | PASS | owner, manager, kho 200; giao, CSKH, không nhóm 403; không token 401 (28 ca) |
| ED-21-AC5 số truy vấn không tăng theo số dòng | PASS | 5 NCC: 8/7/7 truy vấn (owner/manager/kho); 50 NCC: 8/7/7. Trang 1 có đúng 50 dòng, `count` 50 |
| Ghi: POST/PATCH owner, manager 201/200; kho, giao, CSKH 403; không token 401 | PASS | 30 ca |
| Tên trùng -> 400 (tuần tự) | PASS | 10 ca: trùng hoa/thường, khoảng trắng đầu/cuối, dấu tiếng Việt khác nhau thì coi là khác; đổi tên trùng NCC khác -> 400; đổi tên về chính nó, đổi hoa thường của chính nó -> 200 |
| Dữ liệu vào xấu | PASS | 12 ca POST 400 (tên rỗng, toàn khoảng trắng, quá dài, SĐT sai định dạng...), không 500 |
| DELETE/PUT -> 405 kể cả owner và manager (chứng từ không bị xoá) | PASS | 31 ca (mọi nhóm + không token) |
| Ngừng hợp tác (`is_active=false`) | PASS | 3 ca: tắt/bật được, NCC đã tắt vẫn thấy số liệu cũ |
| Lọc, phân trang | PASS | 25 ca lọc đúng; 17 ca giá trị xấu -> 400 `INVALID_FILTER` không phản hồi lại giá trị; `page` biên |
| AuditLog | PASS | `supplier_create`/`supplier_update`, `changes={"fields":[...]}` chỉ chứa tên trường; 10 ca không chứa SĐT, 2 ca không chứa giá vốn |
| Dữ liệu cá nhân | PASS | SĐT NCC giả không có trong AuditLog, log máy chủ (ngoại trừ URL tìm `?q=` do chính tôi gửi, xem N11-2), kết quả lệnh AI qua `scrub_data` |
| Lệnh AI `purchasing.supplier.*` | PASS | `list/retrieve/create/partial_update` chạy qua HTTP AI thật; `purchase_total` bị scrub với người không có `view_costprice` |
| Bấm đúp tuần tự | PASS | `[201, 400]` |
| **Hai yêu cầu đồng thời cùng tên** | **FAIL** | **B11-1** |
| `id` Ả Rập `%D9%A1` ở URL chi tiết | Low | N11-1 |

### Lô 13 — R14 Danh mục và giá

| Mã AC / ca | Kết quả | Bằng chứng (`qa_lot13.py`, HTTP thật + `qa1113_inproc13.py`) |
|---|---|---|
| ED-30 danh sách/chi tiết mặt hàng có `current_price` đúng | PASS | 108 ca đọc theo nhóm: owner, manager, kho, giao... `current_price` đúng theo bảng giá mặc định (BR-DM-02); bảng giá "Sỉ" mới hơn không ảnh hưởng |
| ED-30-AC5 giá vốn | PASS | 42 ca quét `COST_KEYS`: không khoá giá vốn, không số mồi ở item, item-group, price-list, pricing-rules cho mọi vai |
| `current_price` vắng với kho | PASS | kho không có `catalog.view_itemprice` -> không có khoá `current_price` trong list và chi tiết (còn manager/owner có) |
| ED-31-AC5 ghi giá/ưu đãi chỉ owner | PASS | 121 ca: POST/PATCH/DELETE item-prices, price-lists, pricing-rules theo từng nhóm; manager, kho, giao, CSKH 403, không token 401 |
| ED-31-AC1 đặt giá mới tự đóng giá cũ | PASS | giá cũ `valid_upto = D+4`, chỉ một giá mở; sổ giá không bị xoá |
| BR-DM-03 chồng lấn -> 400 | PASS | 12 ca: cùng ngày bắt đầu với giá tương lai/hiện hành, chen vào giữa, PATCH vào khoảng cũ, đổi mặt hàng sang chỗ chồng đều 400 `BR-DM-03`; thông điệp nói cách sửa |
| Cắt đuôi (mất giá sau ngày kết thúc) -> 400 | PASS | giá chen `D+2..D+3` khi giá cũ kéo đến `D+4` -> 400; chen khớp đuôi `D+2..D+4` trước giá tương lai `D+5` -> 201 và liền mạch |
| `valid_upto < valid_from` -> 400 theo field | PASS | cả POST và PATCH |
| Bấm đúp tuần tự | PASS | `[201, 400]`, một giá mở |
| Giá Shop trước/sau ngày hiệu lực (giờ VN) | PASS | du hành thời gian quanh 00:00 VN / 17:00 UTC: Shop chi tiết, Shop danh sách, ERP chi tiết, ERP danh sách và `_effective_price` của đơn đều khớp nhau ở mọi mốc |
| Shop không lộ giá vốn, dữ liệu cá nhân | PASS | 2 ca |
| Shop: mặt hàng chưa giá / ngừng bán | PASS | danh sách không có QA04, QA05; chi tiết hàng chưa giá vẫn 200 với `price=null` (hành vi có từ trước, ghi N13-4) |
| ED-31-AC2/AC3 tạo ưu đãi và dữ liệu xấu | PASS | `PERCENT > 100`, âm, `FIXED` quá lớn, ngày kết thúc trước ngày bắt đầu, thiếu mặt hàng khi `apply_on=ITEM`... đều 400 tiếng Việt, 43 ca |
| Tắt ưu đãi cũ sai dữ liệu (150%) | PASS | `{is_active:false}` -> 200; bật lại khi vẫn sai -> 400; `{is_active:false, name}` hoặc kèm `discount_value:150` -> 400 (không miễn kiểm); sửa lại 20% hợp lệ rồi bật được |
| ED-31-AC4 thêm nhóm hàng | PASS | có trong danh sách chọn |
| `has_image` giá trị xấu -> 400 | PASS | 31 ca lọc xấu, `has_image=abc`, `maybe`, `2`... -> 400 `INVALID_FILTER` |
| Số truy vấn | PASS | 7 mặt hàng: 10/10/9 (owner/manager/kho); 52 mặt hàng: 9/9/8; item-groups, pricing-rules, item-prices 7 truy vấn mỗi cái |
| AuditLog | PASS | `create_itemprice`, `close_itemprice`, `update_itemprice` dùng khoá `sell_rate`, không có `rate`; không có giá vốn, không có SĐT |
| ⏸ Hai người đặt giá cùng lúc cho cùng mặt hàng | ⏸ | `select_for_update` là no-op trên SQLite, cần Postgres |
| **Ưu đãi đã dùng ở đơn: DELETE** | **FAIL** | **B13-1** |
| **Giá bán `0`** | **FAIL** | **B13-2** |

### Phân quyền (HTTP thật)

| Hành động | owner | manager | warehouse_staff | delivery_staff | customer_service | không nhóm | không token |
|---|---|---|---|---|---|---|---|
| GET suppliers (list, detail) | 200 | 200 | 200 | 403 | 403 | 403 | 401 |
| `purchase_total` trong body | có | không | không | n/a | n/a | n/a | n/a |
| POST/PATCH suppliers | 201/200 | 201/200 | 403 | 403 | 403 | 403 | 401 |
| DELETE/PUT suppliers | 405 | 405 | 403 | 403 | 403 | 403 | 401 |
| GET items, item-groups | 200 | 200 | 200 | theo Tầng 1 hiện có | theo Tầng 1 hiện có | 403 | 401 |
| `current_price` trong item | có | có | không | n/a | n/a | n/a | n/a |
| POST/PATCH/DELETE item-prices, pricing-rules | 2xx | 403 | 403 | 403 | 403 | 403 | 401 |

### Rò giá vốn

Không rò. Quét đệ quy mọi khoá JSON theo `COST_KEYS` cộng số mồi trên mọi trang list/chi tiết/dòng thời gian của suppliers, items, item-groups, price-lists, item-prices, pricing-rules và Shop với owner, manager, kho: manager và kho 0 khoá, 0 số mồi (`purchase_total` và `purchase_amount` đã vào `COST_KEYS`). `purchase_total` ÷ kg tính ngược ra giá nhập, nên đúng là giới hạn owner. AuditLog `changes` chỉ có tên trường (`fields`), `sell_rate` là giá bán chứ không phải giá vốn. Qua AI: lệnh `purchasing.supplier.*` bị `scrub_data` bỏ khoá giá vốn khi thiếu `view_costprice`.

### Rò dữ liệu cá nhân

Không rò. SĐT NCC giả và SĐT/địa chỉ khách giả (tạo đơn thật dùng ưu đãi): không có trong body API công khai và Shop, AuditLog, kết quả AI, log máy chủ (dòng log duy nhất chứa SĐT là URL `?q=<SĐT>` do chính script tìm kiếm gửi, xem N11-2). `Cache-Control` không thay đổi so với trước.

### Hồi quy

Full `manage.py test` 2591 OK, adapter 68 OK, migration sạch, naming sạch. Quét tay các lô liền kề (Lô 8, 9, 10 vẫn chạy trên cùng cấu hình): không 5xx. Giá của đơn hiện hữu không đổi: `_effective_price` của đơn và giá ERP/Shop khớp ở mọi mốc thời gian.

### Lỗi

#### B11-1 — Hai yêu cầu đồng thời tạo trùng tên nhà cung cấp · Medium (chặn) · ED-21 "tên trùng 400" + bấm đúp
- **Bước tái hiện:** `python3 qa1113_race.py` (hoặc tay): gửi 6 `POST /api/purchasing/suppliers/` song song với cùng `{"name": "NCC Đua Tranh <n>"}` bằng token owner, 15 vòng với tên khác nhau mỗi vòng.
- **Mong đợi:** đúng 1 yêu cầu 201, các yêu cầu còn lại 400 (tên trùng).
- **Thực tế:** 9/15 vòng có từ 2 tới 5 dòng trùng tên trong DB (nhiều yêu cầu cùng 201). Tương tự với `PATCH` đổi tên. Kiểm trùng làm bằng `casefold` trong Python và model không có ràng buộc duy nhất, nên không có gì chặn khi hai yêu cầu cùng qua bước kiểm. Không phải lỗi riêng của SQLite.
- **Ảnh hưởng:** danh sách NCC có hai dòng cùng tên; số liệu tổng hợp (số phiếu, tổng tiền) bị chia đôi theo hai bản ghi. Người dùng bấm đúp nút Lưu là đủ để dính.
- **Đề xuất cho BE:** khoá tuần tự khi kiểm trùng (ví dụ `pg_advisory_xact_lock` theo hash tên đã chuẩn hoá, hoặc cột `name_key` đã casefold có `UniqueConstraint`), và test song song trên Postgres.

#### B13-1 — `DELETE` ưu đãi đã được đơn dùng trả 500 · Medium (chặn) · ED-31 (ngoại lệ: dữ liệu đã từng bán)
- **Bước tái hiện:** tạo đơn 6 kg QA01 để ưu đãi "Mua 5kg giảm 10% QA" áp vào dòng đơn (`SalesOrderLine.pricing_rule`, `on_delete=PROTECT`), rồi `DELETE /api/catalog/pricing-rules/<id>/` bằng token owner.
- **Mong đợi:** 4xx có thông điệp tiếng Việt ("Ưu đãi đã dùng ở đơn hàng, hãy tắt thay vì xoá") hoặc 405.
- **Thực tế:** HTTP **500**, `ProtectedError ... referenced through protected foreign keys: 'SalesOrderLine.pricing_rule'` (qua HTTP thật trên `runserver`, DEBUG nên trả trang lỗi; production sẽ là 500 chung). Dữ liệu không bị mất nhờ PROTECT.
- **Ảnh hưởng:** owner bấm Xoá thấy lỗi hệ thống thay vì lời hướng dẫn; 500 sinh log và cảnh báo. Gắn với N13-3: ưu đãi chưa dùng lại xoá cứng được (204).
- **Đề xuất:** bắt `ProtectedError` -> 409/400 hướng dẫn tắt; cân nhắc 405 cho `DELETE` pricing-rules như các chứng từ khác, vì đã có `is_active`.

#### B13-2 — Giá bán `0` được chấp nhận · Medium (chặn) · ED-31-AC3 / BR-DM
- **Bước tái hiện:** owner `POST /api/catalog/item-prices/` với `{"item": <QA03>, "price_list": <mặc định>, "rate": "0", "valid_from": <D+61>}`.
- **Mong đợi:** 400 "Giá bán phải lớn hơn 0" (cùng tinh thần "đặt giá âm -> 400").
- **Thực tế:** 201. Đến ngày hiệu lực, Shop chi tiết trả `price="0.00"`, Shop danh sách cũng hiện 0.00: khách đặt hàng với giá 0 (bán lỗ toàn phần). Nguyên nhân: `ItemPrice.rate` chỉ có `MinValueValidator(0)`.
- **Ảnh hưởng:** một lỗi gõ nhầm của owner biến thành đơn giá 0 đồng. Chưa tới mức mất tiền tự động vì cần owner đặt, nhưng không có chặn nào.
- **Đề xuất:** `rate > 0` ở serializer và service `set_item_price`/`update_item_price`; nếu muốn tặng quà thì dùng ưu đãi.

#### N13-3 — Điểm cần PO/techlead quyết · Medium hoặc Low · ED-31
- `min_qty` của ưu đãi nhận số âm hoặc 0 (model không có validator): ưu đãi "mua >= -3 kg" áp cho mọi dòng.
- `DELETE` item-price và pricing-rule chưa dùng -> 204 (xoá cứng lịch sử giá/ưu đãi). Nếu coi lịch sử giá là chứng từ thì nên 405 và dùng `valid_upto`/`is_active`.
- Nhóm hàng có thể chọn chính nó làm nhóm cha (200).
- Chưa tính thành lỗi chặn vì AC chưa viết các trường hợp này, nhưng đề nghị techlead chốt cùng lúc sửa B13-1, B13-2.

#### Ghi nhận Low / thông tin
- **N11-1 (Low):** `GET /api/purchasing/suppliers/%D9%A1/` (chữ số Ả Rập "١") trả 200 trên chi tiết (Python `int()` chấp nhận). Ca duy nhất không pass của Lô 11; không rò dữ liệu, chỉ nên chuẩn hoá `lookup_value_regex=[0-9]+` nếu muốn chặt.
- **N11-2 (Low):** tìm NCC bằng SĐT dùng `?q=<SĐT>` nên SĐT nằm trong URL/access log. SĐT NCC (doanh nghiệp) không phải dữ liệu khách nên không phải Critical; khuyến nghị gom về POST hoặc che trong access log.
- **N11-3 (info):** `last_received_at` lấy theo `created_at` của phiếu (đúng 02b), không phải `received_date`; phiếu nhập hồi tố sẽ hiện ngày tạo.
- **N13-4 (info, có từ trước):** Shop chi tiết hàng chưa có giá vẫn 200, `price=null`.
- **N13-5 (info):** `rate="1e3"` được chấp nhận và hiểu là 1000; cho phép giá hiệu lực lùi ngày quá khứ (không đóng giá nào, vẫn một giá mở).

### ⏸ Chưa kiểm được
- Hai người đặt giá/duyệt cùng lúc trên Postgres (`select_for_update`): no-op trên SQLite. B11-1 cũng nên có test song song trên Postgres sau khi sửa.
- Không có ca FE trong lần kiểm này (chỉ BE).

### Lệnh đã chạy (output tóm tắt)
```
bash qa1113_reset.sh                                       -> migrate + bootstrap_masterdata + seed dữ liệu giả
bash qa1113_serve.sh (runserver 127.0.0.1:8766 --noreload)
python3 qa_lot11.py                                        -> 307 ca, 306 pass, 1 Low (N11-1)
python3 qa_lot13.py                                        -> 465/465 pass (sau khi chuyển các ca đổi trạng thái sang QA03 và dựng lại DB)
python qa1113_inproc.py                                    -> truy vấn NCC 5 dòng: 8/7/7, 50 dòng: 8/7/7; trang 1 có 50 dòng
python qa1113_inproc13.py                                  -> du hành thời gian: 5 đường tính giá khớp; truy vấn items 10/10/9 -> 9/9/8; DELETE ưu đãi đã dùng -> ProtectedError
curl -X DELETE .../api/catalog/pricing-rules/<đã dùng>/    -> HTTP 500 (ProtectedError)
python3 qa1113_race.py                                     -> 9/15 vòng sinh tên trùng (B11-1)
manage.py test (backend, toàn bộ)                          -> Ran 2591 tests OK (124 s)
adapter/.venv/bin/python -m pytest                         -> 68 passed
manage.py makemigrations --check --dry-run                 -> No changes detected
python3 scripts/check_naming.py                            -> OK, không vi phạm mới
pkill -f "runserver 127.0.0.1:8766"
```

---

## BE Lô 11, 12, 13, 14 (đợt 2) · 2026-10-02

Chạy thật trên server `runserver` + SQLite tạm, dữ liệu giả, token từng vai (owner, manager, manager2 = manager + `manage_staff` gán riêng, extra = chỉ `manage_staff`+`view_auditlog` gán riêng, kho, kho2, viewer = kho + `view_customer_list` gán riêng, giao A/B, CSKH, không nhóm) và ca chưa đăng nhập. Không PASS bằng đọc code. Không sửa code sản phẩm.

### Kết luận theo lô
| Lô | Kết luận | Lý do một dòng |
|---|---|---|
| **11** | **APPROVED** | B11-1 đã sửa: 6 POST song song cùng tên cho đúng 1 thành công, PATCH đổi trùng tên cũng bị chặn; 35 vòng đua không còn bản trùng. Còn N11-1 (Low). |
| **12** | **APPROVED** | 392/392 ca; không rò giá vốn, không rò dữ liệu cá nhân; D-3 đúng; `customer_name` chỉ theo `view_customer_list`. Còn 1 điểm cần Duy chốt (ED-33-AC4). |
| **13** | **APPROVED** | B13-1, B13-2, N13-3 đều đã sửa và có bằng chứng chạy thật (DELETE 405 kể cả ưu đãi đã dùng trong đơn). |
| **14** | **APPROVED** | 585/585 ca; không vượt quyền, không cấp được việc "Chỉ Chủ", hiệu lực ngay, audit chỉ có mã. Ca đồng thời cần Postgres ⏸. |

### Tổng: ca có kịch bản (HTTP thật) · 1908 · ✅ 1907 · ❌ 1 (Low) · ⏸ 6 mục
(Lô 11: 307 · Lô 12: 392 · Lô 13: 465 + 151 + 8 du hành thời gian · Lô 14: 585. Chưa tính các ca thủ công: tranh chấp tên 35 vòng, phân trang 25 hoá đơn, lệnh AI theo vai, đếm truy vấn.)

### Theo AC / yêu cầu
| Mã | Kết quả | Bằng chứng |
|---|---|---|
| Lô 11 · B11-1 tên NCC trùng khi đồng thời | ✅ đã sửa | `qa1214_race11.py`: 6 POST song song cùng tên (và biến thể hoa/thường, khoảng trắng) → đúng 1 thành công, còn lại 400 (`SUPPLIER_NAME_TAKEN` hoặc lỗi trường `name`); 15+10+10 vòng, 0 bản trùng. PATCH đổi sang tên trùng song song: cùng kết quả. |
| Lô 11 · chạy lại cả script cũ | ✅ 306/307 | `qa_lot11.py`; ca lệch duy nhất là N11-1 (Low, có từ lần 1). |
| Lô 13 · B13-1 DELETE ưu đãi đã dùng | ✅ đã sửa | DELETE `/pricing-rules/<id đã dùng trong đơn>/` → 405 (trước: 500). Mọi vai đăng nhập → 405, chưa đăng nhập → 401. |
| Lô 13 · DELETE bảng giá / giá mặt hàng | ✅ | 405 mọi vai; dòng còn nguyên trong DB. |
| Lô 13 · B13-2 `rate` ≤ 0 | ✅ đã sửa | `rate` 0, -1, "0.00", "-0.0001" → 400; `PERCENT=0` → 400. |
| Lô 13 · N13-3 `min_qty`/`discount_value` ≤ 0 | ✅ đã sửa | 0, âm → 400; số dương nhỏ nhất vẫn nhận. |
| Lô 13 · N13-3 nhóm hàng chọn chính nó/con/cháu làm cha | ✅ đã sửa | cả 3 trường hợp 400; chọn nhánh khác hợp lệ → 200. |
| Lô 13 · chạy lại cả script cũ | ✅ | `qa_lot13.py` 465/465 (đã đổi kỳ vọng DELETE 403→405, PERCENT 0→400), `qa_lot13b.py` 151/151, du hành thời gian 8/8. |
| R11 hoá đơn mua · D-3 | ✅ | manager thấy `amount`; kho/giao/CSKH 403; chưa đăng nhập 401. Lọc `is_paid`, `supplier`, `month` đúng số SQL; lọc sai → 400. |
| R12 chi phí lô | ✅ | chỉ owner xem; manager và 3 vai còn lại 403, thân 403 không có số tiền. |
| R13 hoá đơn bán · giá vốn | ✅ | owner thấy `cogs`/`gross_profit`/`totals.gross_profit`; manager, kho: không có các khoá này, `totals` chỉ `amount`. |
| R13 · `customer_name` | ✅ | chỉ người có `sales.view_customer_list` (owner, manager, viewer). Kho: `null` (khoá vẫn có). Tắt `view_customers` của manager qua ma trận → `null` ngay. `q` không tìm theo tên khách. `Cache-Control: no-store`. |
| R13 · lọc, trang | ✅ | `status`, `date_from/to`, `q`, phân trang 20 dòng/25 hoá đơn; sai dạng → 400 `INVALID_FILTER`. |
| R15 `reports/batches` | ✅ | chỉ owner; mọi vai khác 403; lọc `month`, `state` đúng SQL; sai → 400. |
| R15 `period` | ✅ | `invoice_count`, `refund_count` khớp SQL; khoá cũ giữ nguyên số. |
| R15 · lệnh AI `reports.batch_pnl_list` | ✅ | chỉ owner thấy/gọi; vai khác bị từ chối. |
| ED-39-AC1 đọc ma trận | ✅ | owner 200 (5 nhóm đúng thứ tự, 25 việc mỗi nhóm, 9 việc "Chỉ Chủ" khớp danh sách); manager/kho/giao/CSKH/không nhóm 403; chưa đăng nhập 401. |
| ED-39-AC2 hiệu lực ngay | ✅ | cùng token manager: `customer-directory` 200 → 403 ngay sau khi Chủ tắt `view_customers`; `/auth/me/` bỏ quyền; `orders` 200 → 403 khi tắt `view_orders`; bật lại → trở về, DB về nguyên trạng. |
| ED-39-AC3 người không phải Chủ không ghi được | ✅ | 9 vai × 6 nhóm × 3 thân (~160 ca): manager, manager2, extra, kho, giao, CSKH, không nhóm → 403, chưa đăng nhập 401; quyền nhóm trong DB và AuditLog không đổi. |
| ED-39-AC4 nhóm Chủ khoá | ✅ | 6 kiểu thân vào `owner` → 400 `GROUP_LOCKED`. |
| BR-PQ-32 việc "Chỉ Chủ" | ✅ | 9 việc × 4 nhóm bật → 400 `BR-PQ-32`; lẫn việc hợp lệ cũng không áp (tất cả hoặc không gì); không audit. Khoá lạ (`view_costprice`, `inventory.view_costprice`, `reports.view_profitreport`, `accounts.manage_staff`, rỗng, khoảng trắng, hoa/thường…) → 400 `INPUT_NOT_ALLOWED`. Bật hết việc thường cho CSKH → không có quyền owner-only nào xuất hiện. |
| `requires` (M1) | ✅ | tắt `deliver` khi `pack_print` bật → 400 `CAPABILITY_REQUIRES`; bật `pack_print` khi `deliver` tắt → 400; đổi cả hai cùng yêu cầu thì qua; trạng thái `partial` xử lý đúng (tắt `deliver` khi `pack_print` partial → 400; bật lại partial → đủ quyền). |
| `scopes.customers` (M2) | ✅ | động: kho bật `view_customers` → "Tất cả khách" và `customer-directory` 200; tắt → "Không xem" và 403; manager tắt → "Không xem"; khớp 200/403 cả 5 nhóm. |
| ED-39-AC5 audit + timeline | ✅ | `change_group_capabilities` (22 dòng): `changes` chỉ `{khoá việc: {from,to}}`, `note` rỗng; PUT không đổi gì không ghi; đổi 3 việc ghi đúng 1 dòng; timeline "Bật/Tắt việc …" và "Thêm/Bớt … nhóm" (chạy qua `PUT /api/staff/<id>/groups/`); `last_changed_*` điền; người nghỉ: list không đếm, detail có `is_active:false`. |
| R2 guidance `group` | ✅ | `/api/guidance/group/<pk>/` owner 200, `next_steps` rỗng; vai khác 403; chưa đăng nhập 401; pk lạ/chữ/âm/quá lớn → 404, không 500. |
| R16 `audit-logs?actor=` | ✅ | owner/manager 200; kho, giao, CSKH 403; chưa đăng nhập 401. Tập id trả về = tập id SQL (đủ, chỉ của người đó); id không tồn tại → 200 rỗng; trống → không lọc; ghép `action`, `actor_kind` khớp SQL; 24 giá trị sai (chữ, 0, âm, thập phân, khoảng trắng, `+1`, Unicode, quá int64, 5000 chữ số, SQL, HTML…) → 400 `INVALID_FILTER`, không lặp lại giá trị. POST/PUT/PATCH/DELETE → 405. |

### Ngoại lệ và biên (đã chạy)
- Đồng thời: tên NCC (xem trên). Trên SQLite 4 PUT song song trên cùng nhóm: 1 thành công, 3 trả 500 "database is locked" (SQLite chỉ cho một người ghi; `select_for_update` là no-op) → **không tính lỗi, ⏸ chạy lại trên Postgres**. Trạng thái cuối vẫn on/off sạch, không dở dang (khối `atomic`).
- Bấm đúp / PUT lặp: PUT cùng nội dung hai lần → 200 cả hai, chỉ 1 dòng audit.
- Thân hỏng (23 kiểu + 7 thân thô: JSON cụt, byte lạ, 100 KB, form-encoded, 5000 khoá) → 400/415, không 500, DB không đổi.
- Nhóm lạ (`chu`, `quan_ly`, `OWNER`, `Manager`, khoảng trắng, `..`, `%00`, số lớn) → 404 `GROUP_NOT_FOUND`, không 500; PUT cũng 404.
- Dữ liệu đã có sẵn lệch (đã cấp `confirm_payment_manual` cho kho ngoài băng): Chủ tắt → gỡ được, audit ghi on→off.
- Chứng từ không bị xoá: DELETE bảng giá/ưu đãi/giá hàng → 405; AuditLog không có đường ghi/xoá (405), số dòng không giảm.

### Phân quyền (Lô 14, ghi ma trận)
| Hành động | owner | manager | manager2 (+manage_staff riêng) | extra (chỉ manage_staff riêng) | kho | giao | CSKH | không nhóm | chưa ĐN |
|---|---|---|---|---|---|---|---|---|---|
| GET `/api/staff/groups/…`, guidance `group` | 200 | 403 | 200* | 200* | 403 | 403 | 403 | 403 | 401 |
| PUT `…/capabilities/` | 200/400 theo luật | 403 | 403 | 403 | 403 | 403 | 403 | 403 | 401 |
| GET `/api/audit-logs/?actor=` | 200 | 200 | 200 | 200 | 403 | 403 | 403 | 403 | 401 |
| GET `reports/batches`, `purchasing/costs` | 200 | 403 | | | 403 | 403 | 403 | | 401 |
| GET `purchasing/invoices` | 200 | 200 | | | 403 | 403 | 403 | | 401 |
| GET `sales/invoices` (có `customer_name`) | 200 có | 200 có | | | 200 `null` | 403 | 403 | | 401 |

\* theo thiết kế: quyền đọc là `accounts.manage_staff`; người được gán trực tiếp đọc được, nhưng ghi vẫn 403 (đã chạy). Không phải lỗi.

### Rò giá vốn
Quét `COST_KEYS` + số mồi (91919…) cho mọi vai không phải owner trên toàn bộ phản hồi 200/403/401 của Lô 12 và 14: **không có**. Khoá việc của registry (`view_cost`, `set_price`, `view_profit`…) **không** nằm trong `COST_KEYS` và chỉ là tên việc, không có số tiền/kg → không tính ngược ra giá vốn. Audit `changes` chỉ `{from,to}` dạng on/off (kiểm: không có số ≥ 4 chữ số). Hoá đơn bán: `cogs`, `gross_profit` chỉ cho `view_costprice`. CSKH được bật hết việc thường vẫn không đọc được `reports/batches` / `purchasing/costs` (403).

### Rò dữ liệu cá nhân
- Gài SĐT/email/ghi chú nhân viên giả vào DB và 6 khách giả: không xuất hiện trong `members`, timeline, guidance, audit, 403 body. `members` chỉ gồm `id`, `display_name`, `username`, `other_groups`, `is_active`, `added_at`.
- `sales/invoices`: chỉ có tên khách (không SĐT, không địa chỉ) và chỉ cho người có `view_customer_list`; chi tiết hoá đơn không có tên.
- Log server (1358 dòng): không có tên/SĐT khách ngoài URL `?q=` do chính script thăm dò.
- Không có lệnh AI nào chạm `/api/staff/groups/` hay `/api/audit-logs/` (danh sách lệnh AI đã quét).

### Hồi quy
`manage.py test` toàn bộ (song song 4): **Ran 2642 tests, OK** (con số của điều phối viên, tôi tự chạy lại). `adapter` pytest 68 passed. `makemigrations --check --dry-run`: No changes detected. `check_naming`: OK, không vi phạm mới. Script Lô 11 (307) và Lô 13 (465 + 151) cũ chạy lại: không hồi quy.

### Lỗi
Không có lỗi Critical, High hoặc Medium trong Lô 11, 12, 13, 14.

#### Ghi nhận Low / thông tin (không chặn)
- **N11-1 (Low, còn từ lần 1):** `GET /api/purchasing/suppliers/%D9%A1/` (chữ số Ả Rập) trả 200. Đề nghị `lookup_value_regex=[0-9]+`.
- **N12-1 (cần Duy chốt, ED-33-AC4):** story nói kho thấy "Không có quyền" ở màn Hoá đơn bán, BE theo 02b cho kho 200 (không có `customer_name`, không có giá vốn). Không rò gì; chỉ là lệch story. BE đã ghi trong dev-notes.
- **N12-2 (info, hiệu năng):** `reports/batches` owner ≈ 34 truy vấn/trang (≈ 7 mỗi lô); dev-notes đã nêu.
- **N12-3 (info):** `supplier=1%20`, `date_from=%0A…` được cắt khoảng trắng và trả 200; `period?month=13` trả 200 với số 0 (có từ trước, ngoài diff).
- **N13-5 (info):** giảm 100% cho đơn tổng 0 đồng; `rate="1e3"` hiểu là 1000.
- **N14-1 (info):** tắt `view_orders` hoặc `deliver` của NV giao làm hỏng màn hình của họ; BE không cấm (quyết định của Chủ, FE hỏi xác nhận) và `scopes.orders` cố định theo bảng.
- **N14-2 (info):** `scopes.customers` của `delivery_staff` là "Được gán" trong khi `customer-directory` 403: đúng (họ chỉ thấy khách qua phiếu giao được gán).
- **N-pre (có từ trước, ngoài diff, không chặn):** `PATCH /api/purchasing/costs/{id}/ {"amount":"1"}` bởi owner trả 200, không tính lại phân bổ và không ghi AuditLog. Đề nghị lô sau.

### ⏸ Chưa kiểm được
1. Tranh chấp tên NCC khi nhiều tiến trình (Postgres, `pg_advisory_xact_lock(7110001)`): SQLite chỉ dùng `RLock` trong một tiến trình.
2. Hai người đặt giá cùng lúc (`select_for_update` no-op trên SQLite).
3. Hai PUT ma trận cùng lúc trên cùng nhóm: SQLite trả 500 "database is locked", cần chạy trên Postgres để xác nhận `select_for_update` tuần tự hoá.
4. `_membership_events` (lookup `changes__groups__…__icontains`) trên Postgres: chỉ chạy SQLite.
5. FE của 4 lô này (chưa có trong đợt này).
6. Thời gian phản hồi thật trên Postgres cho `reports/batches`.

### Lệnh đã chạy (output tóm tắt)
```
qa1113_reset.sh + qa1113_serve.sh (8766) / qa1214_reset.sh + qa1214_serve.sh (8767), runserver --noreload, SQLite tạm
python3 qa_lot11.py          -> 306/307 (N11-1)
python3 qa1214_race11.py     -> tranh chấp tên NCC: 0 bản trùng sau 35 vòng; PATCH song song OK
python3 qa_lot13.py          -> 465/465
python3 qa_lot13b.py         -> 151/151
python  qa1113_inproc13.py   -> du hành thời gian 8/8; DELETE ưu đãi đã dùng -> 405
python3 qa_lot12.py          -> 392/392 (+ qa12_page.py phân trang, qa1214_ai.py lệnh AI theo vai, qa1214_q.py số truy vấn)
python3 qa_lot14.py          -> 585/585
manage.py test --parallel 4  -> Ran 2642 tests OK (40 s)
adapter/.venv/bin/python -m pytest -> 68 passed
manage.py makemigrations --check --dry-run -> No changes detected
python3 scripts/check_naming.py -> OK
pkill runserver 8766 và 8767
```
Script nằm trong scratchpad của phiên (không đưa vào repo).

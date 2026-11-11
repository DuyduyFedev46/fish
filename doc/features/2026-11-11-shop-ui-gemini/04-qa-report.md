# 04 · Báo cáo QA (Gemini CLI — Shop UI)

> Nhánh: `gemini/shop-ui` · Kiểm thử thực tế trên trình duyệt Chromium (Playwright) ở 360 px và 1280 px với BE Django + SQLite tạm. Dữ liệu cá nhân 100% giả.

## GUI-01 — Mã giảm giá khi kiểm bị lỗi mạng

| Tiêu chí | Cách kiểm | Kết quả | Ảnh bằng chứng |
|---|---|---|---|
| Chặn mạng `/api/shop/vouchers/check/` ngay từ giỏ (chưa áp được mã), đặt đơn: số tiền ở tóm tắt bằng số tiền trang thanh toán (360 + 1280) | `page.route("**/api/shop/vouchers/check/", abort)` → nhập mã ở giỏ báo `"Chưa kiểm được mã"` → sang `/shop/checkout/` tóm tắt `165.000đ` → đặt đơn → trang thanh toán `165.000đ` | **PASS** (360 px & 1280 px) | `shots/flow/05-cart-360.png`, `shots/flow/09-payment-360.png` |
| Đã áp mã ở giỏ, sang `/shop/checkout/` bị chặn mạng `/api/shop/vouchers/check/`: hiện dòng nhỏ `"Mã X · sẽ kiểm khi đặt"` ở khối tóm tắt (360 + 1280) | Áp mã `FLOW…` ở giỏ (`−16.500đ`) → bật `route.abort` cho `/api/shop/vouchers/check/` → vào `/shop/checkout/` đợi hết debounce kiểm mã → kiểm DOM + nhìn ảnh chụp | **PASS** (360 px & 1280 px) | `shots/gui-01/35-checkout-voucher-pending-360.png`, `shots/gui-01/35-checkout-voucher-pending-1280.png` |
| Đặt đơn khi đang ở trạng thái `"Mã X · sẽ kiểm khi đặt"`: mã vẫn gửi lên máy chủ, trang thanh toán hiện đúng số tiền giảm thật (ngoài đường thuận) | Điền form dữ liệu giả → bấm `"Đặt hàng"` → mở trang thanh toán `/shop/orders/?code=…` → kiểm dòng giảm giá `−16.500đ` và cần thanh toán `148.500đ` | **PASS** (360 px & 1280 px) | `shots/gui-01/35b-payment-voucher-applied-360.png`, `shots/gui-01/35b-payment-voucher-applied-1280.png` |
| Hồi quy bất biến (không rò giá vốn, không rò dữ liệu cá nhân, không mã hex rời, không cuộn ngang, axe-core 360) | Chạy `run_shop_e2e.py --suite general_rules --suite full_flow` + `check_naming.py` | **PASS** (`general_rules`: 132/132, `full_flow`: 109/109) | — |

## GUI-02 — Hộp "mã hết hiệu lực" (B8) gạch rồi in lại cùng một số

| Tiêu chí | Cách kiểm | Kết quả | Ảnh bằng chứng |
|---|---|---|---|
| Ca có giảm (đã lấy được `quote` từ máy chủ trước khi mã bị tắt): vẫn gạch giá giảm cũ rồi in tổng chưa giảm đúng như màn `B8*` | Áp mã ở giỏ → sang `/shop/checkout/` đợi hiện `Mã giảm giá (…) −16.500đ` → tắt mã qua API → bấm `"Đặt hàng"` → kiểm `<del>` = `148.500đ`, `<strong>` = `165.000đ` | **PASS** (360 px & 1280 px) | `shots/gui-02/36-b8-with-quote-360.png`, `shots/gui-02/36-b8-with-quote-1280.png` |
| Ca chưa từng kiểm được `quote` (ngoài đường thuận: chặn mạng `/api/shop/vouchers/check/` ở đặt hàng rồi mã bị tắt): ẩn `<del>`, chỉ hiện tổng `165.000đ` | Áp mã ở giỏ → chặn `/api/shop/vouchers/check/` → vào `/shop/checkout/` → tắt mã qua API → bấm `"Đặt hàng"` → kiểm `dialog del` count = `0`, chỉ còn `<strong>165.000đ</strong>` | **PASS** (360 px & 1280 px) | `shots/gui-02/36b-b8-without-quote-360.png`, `shots/gui-02/36b-b8-without-quote-1280.png` |
| Bấm `"Đặt hàng không dùng mã"` từ hộp B8 không `quote` | Click nút chính trong dialog → đơn tạo thành công với giá gốc `165.000đ` | **PASS** (360 px & 1280 px) | — |
| Hồi quy bất biến | `run_shop_e2e.py --suite general_rules --suite full_flow` | **PASS** (`general_rules`: 132/132, `full_flow`: 115/115) | — |


## GUI-03 — Dọn state chết ở giỏ và sửa thụt lề `hotline`

| Tiêu chí | Cách kiểm | Kết quả | Ảnh bằng chứng |
|---|---|---|---|
| `tsc`, build tĩnh (`USE_MOCK=0`), toàn bộ `test-*.mjs` xanh | Chạy đủ chuỗi lệnh mục 4 `GEMINI.md` + `check_naming.py` | **PASS** (9/9 bộ test đơn vị xanh, 0 lỗi TS) | — |
| Giỏ có món hết hàng & món đổi giá (ngoài đường thuận — màn B3 / DE11): vẫn hiện cảnh báo đỏ `"Bỏ món đã hết để đặt hàng."` và chặn sang bước nhận hàng | Dựng giỏ có `TOM-SU-1` hết hàng + `CA-THU` đổi giá trên trình duyệt 360 px và 1280 px, kiểm ảnh chụp thực tế | **PASS** (360 px & 1280 px) | `shots/gui-03/b3-cart-blocked-360.png`, `shots/gui-03/b3-cart-blocked-1280.png` |
| Hồi quy bất biến | `run_shop_e2e.py --suite general_rules --suite full_flow --suite design_screens` | **PASS** (`general_rules`: 132/132, `full_flow`: 115/115) | — |

# 04 · Báo cáo QA (Gemini CLI — Shop UI)

> Nhánh: `gemini/shop-ui` · Kiểm thử thực tế trên trình duyệt Chromium (Playwright) ở 360 px và 1280 px với BE Django + SQLite tạm. Dữ liệu cá nhân 100% giả.

## GUI-01 — Mã giảm giá khi kiểm bị lỗi mạng

| Tiêu chí | Cách kiểm | Kết quả | Ảnh bằng chứng |
|---|---|---|---|
| Chặn mạng `/api/shop/vouchers/check/` ngay từ giỏ (chưa áp được mã), đặt đơn: số tiền ở tóm tắt bằng số tiền trang thanh toán (360 + 1280) | `page.route("**/api/shop/vouchers/check/", abort)` → nhập mã ở giỏ báo `"Chưa kiểm được mã"` → sang `/shop/checkout/` tóm tắt `165.000đ` → đặt đơn → trang thanh toán `165.000đ` | **PASS** (360 px & 1280 px) | `shots/flow/05-cart-360.png`, `shots/flow/09-payment-360.png` |
| Đã áp mã ở giỏ, sang `/shop/checkout/` bị chặn mạng `/api/shop/vouchers/check/`: hiện dòng nhỏ `"Mã X · sẽ kiểm khi đặt"` ở khối tóm tắt (360 + 1280) | Áp mã `FLOW…` ở giỏ (`−16.500đ`) → bật `route.abort` cho `/api/shop/vouchers/check/` → vào `/shop/checkout/` đợi hết debounce kiểm mã → kiểm DOM + nhìn ảnh chụp | **PASS** (360 px & 1280 px) | `shots/gui-01/35-checkout-voucher-pending-360.png`, `shots/gui-01/35-checkout-voucher-pending-1280.png` |
| Đặt đơn khi đang ở trạng thái `"Mã X · sẽ kiểm khi đặt"`: mã vẫn gửi lên máy chủ, trang thanh toán hiện đúng số tiền giảm thật (ngoài đường thuận) | Điền form dữ liệu giả → bấm `"Đặt hàng"` → mở trang thanh toán `/shop/orders/?code=…` → kiểm dòng giảm giá `−16.500đ` và cần thanh toán `148.500đ` | **PASS** (360 px & 1280 px) | `shots/gui-01/35b-payment-voucher-applied-360.png`, `shots/gui-01/35b-payment-voucher-applied-1280.png` |
| Hồi quy bất biến (không rò giá vốn, không rò dữ liệu cá nhân, không mã hex rời, không cuộn ngang, axe-core 360) | Chạy `run_shop_e2e.py --suite general_rules --suite full_flow` + `check_naming.py` | **PASS** (`general_rules`: 132/132, `full_flow`: 109/109) | — |

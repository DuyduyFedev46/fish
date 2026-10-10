# QA — Shop lô 1 (khung chung) · lần 1 và lần 2 · 2026-10-11 (kết luận mới nhất: mục "Lần 2" cuối file)
## Kết luận: REJECTED — 2 lỗi Medium chặn (chữ "Phí giao" trong CMS; hotline giữ chỗ "1900 xxxx" hiện cho khách); phần còn lại đạt.
Nhánh `shop/lo-1-khung-chung`, code chưa commit. Dữ liệu toàn giả (SĐT 0900000001/0900000009, tên "Nguyễn Văn A"), DB SQLite tạm trong scratchpad.

## Môi trường chạy thật
- BE: `DATABASE_URL=sqlite:///<scratchpad>/qa.sqlite3 SEPAY_ENV=SANDBOX`, `migrate`, `seed_demo`, `seed_qa`, thêm món QA (combo, sắp hết, còn 1,5 kg, hết) bằng shell, `load_shop_content --author qa_owner --publish` (chạy 2 lần), `runserver :8765`.
- FE: `npm ci` (không legacy-peer-deps) + `npx tsc --noEmit` sạch; build `NEXT_PUBLIC_USE_MOCK=0 NEXT_PUBLIC_API_BASE=http://localhost:8765` phục vụ tĩnh :3765 (404 trả `404.html` như Firebase). Build thứ hai `NEXT_PUBLIC_UI_PREVIEW=1 NEXT_PUBLIC_USE_MOCK=1` phục vụ :3766.
- Playwright Chromium 360 và 1280 px. Ảnh: `shots/lo1-qa/`.

## Tổng: 52 ca · ✅ 48 · ❌ 2 · ⏸ 2 (+ 3 ghi nhận Low)

## Theo AC
| Mã AC | KQ | Bằng chứng |
|---|---|---|
| 1-01 AC1 token/DESIGN.md | ✅ | `git diff DESIGN.md`: 0 dòng xoá; G7 trên file lô chạm sạch |
| 1-01 AC2 Inter, 0 request fonts.g* | ✅ | computed font `__Inter…`; 0 request `fonts.googleapis/gstatic` ở 10 trang × 2 khổ |
| 1-01 AC3 dark | ✅ | `color_scheme=dark`: body `rgb(251,251,252)`, `color-scheme: light` |
| 1-01 AC4 badge ở `/`, `/bai-viet/`, `/trang/?slug=doi-tra` | ✅ | giỏ 2 dòng: aria-label "Giỏ hàng, 2 món", badge "2" cả 3 trang + `/shop/` |
| 1-01 AC5 badge = số món, giỏ 0 | ✅ | 1,5 kg + 2 kg → "2"; giỏ `[]` → không có chữ badge (chỉ còn `span` slot rỗng trong BottomNav) |
| 1-01 AC6 localStorage | ✅ | khoá `cangcaloc_cart_v1` chỉ mã, tên món, giá, đơn vị, số lượng |
| 1-01 AC7 giỏ hỏng `{"x":` | ✅ | `/` không lỗi console/pageerror, badge ẩn |
| 1-01 AC8 reduced-motion | ✅ | nhấn nút: reduce → `transform: none`; no-preference → `scale(0.97)` |
| 1-02 AC1,3,4 `/ui-preview/` + G5 | ✅ | `popup.py`: Dialog xác nhận (B2), Dialog cảnh báo, BottomSheet (C3), FullscreenSheet: `role=dialog` `aria-modal=true`, Tab/Shift+Tab 20 lần không ra ngoài, Esc đóng, tiêu điểm về nút mở; 360 và 1280. Toast `role=status`, tiêu điểm giữ ở nút, tự ẩn ~3,15 s, toast sau thay toast trước |
| 1-02 AC2 build không cờ | ✅ | `/ui-preview/` ở build chính: trả 404.html |
| 1-02 G5 rộng hộp thoại máy tính | ✅ | Dialog 440 px, BottomSheet 480 px (1280); 297/345 px ở 360 |
| 1-02 AC5 vùng chạm ≥ 44 px, focus-visible | ✅ | 0 phần tử header/BottomNav/footer < 44 px ở 360; outline 2 px |
| 1-02 AC6–9 | ✅ | `test-format/quantity/safe-href` 33+45+40 đạt; grep `sellable\|qty_available` trong components: 0; package.json không đổi |
| 1-03 AC1 H1 | ✅ | logo `aria-label="Cá Về — trang chủ"`, `tel:`, "Tra cứu đơn", giỏ, ô tìm; không có "Tìm nhiều" |
| 1-03 AC2 H2 | ✅ | cuộn 700 px: header trắng `position: fixed`, cao 56 px (`home-scrolled-H2-360.png`) |
| 1-03 AC3 H3 quay lại | ✅ | mở thẳng `/shop/item/?code=MUC-ONG` → "Quay lại" về `/shop/` |
| 1-03 AC4 H4 | ✅ | `/shop/checkout/`: chỉ "Quay lại giỏ hàng", logo, "Cần hỗ trợ?" (xem Low L2) |
| 1-03 AC5 menu máy tính | ⏸ | header 2 tầng, menu 1 cấp, hotline chữ, nút Tìm: ✅. `aria-current` của nhóm: `/shop/?group=hai-san` vẫn `null` vì trang `/shop/` cũ chưa đọc `group` (code có sẵn, lô 2 nối). Chưa kiểm được ở lô 1 |
| 1-03 AC6 tìm | ✅ | gõ "mực" → `/shop/?q=m%E1%BB%B1c`; ô rỗng không điều hướng |
| 1-03 AC7 API lỗi | ✅ | site-info 500 + footer-links 500 + catalog abort: header hiện, không nút gọi, 0 pageerror (nhưng xem B2) |
| 1-03 AC8 đích giỏ | ✅ | `/shop/checkout/` |
| 1-04 AC1–4 BottomNav | ✅ | 360: có ở `/`, `/shop/`, `/bai-viet/`, `/shop/orders/`; không có ở item, checkout, `/trang/`; 1280: không có; cuối trang `/` footer không bị che (`home-bottom-nav-overlap-360.png`) |
| 1-05 AC1 footer F1 | ✅ | nhóm Chính sách = đúng 6 mục `footer-links` theo thứ tự API (đổi trả, giao hàng, thanh toán, quyền riêng tư, "Điều kiện giao dịch chung", khiếu nại); đủ nhóm Mua hàng/Về Cá Về/dải pháp lý |
| 1-05 AC2 MST/Zalo/thông báo | ✅ | MST trống: không dòng MST; không nút Zalo; 0 ảnh/link Bộ Công Thương trong footer |
| 1-05 AC3 thu gọn | ✅ | "Chính sách" `<summary>` mở `false → true` khi bấm (hộp `<details>`, không phải `aria-expanded` thuộc tính; xem L3) |
| 1-05 AC4 F2 | ✅ | checkout: 3 link `target=_blank rel=noopener` + chữ "(mở tab mới)" |
| 1-05 AC5 năm VN | ⏸ | hiện 2026 đúng; chưa giả lập 2027-01-01 00:30 GMT+7 |
| 1-05 AC6 footer-links 500 | ✅ | nhóm Chính sách ẩn, còn Mua hàng + Về Cá Về |
| 1-05 AC7 / G8 | ✅ | `grep SiteLegalFooter`: 0 |
| 1-06 AC1–2,4 | ✅ | `/`: banner, lưới nhóm (14 món), "Đang có hàng", "Combo nấu nhanh" (khi có BUNDLE), Góc bếp, dải cam kết; thẻ `280.000đ / kg`, `450.000đ / combo`; "Chọn mua" → `/shop/item/?code=…`, giỏ vẫn `[]`. Ảnh `home-*-360/1280.png`, `home-with-combo-*` |
| 1-06 AC3,12 món < 1 kg / hết | ✅ | QA-OUT, QA-GHE (hết), QA-ONE (còn 1,5 rồi đặt hết) không có trong hàng; QA-LOW hiện "Sắp hết" |
| 1-06 AC5 ô nhóm | ✅ | `/shop/?group=hai-san` (ô "Tất cả" → `/shop/`) |
| 1-06 AC6 tải | ✅ | catalog chậm 2 s: `aria-busy="true"` (`home-loading-360.png`) |
| 1-06 AC7 lỗi + thử lại | ✅ | "Chưa tải được hàng" + "Thử lại": bấm xong hiện hàng, URL không đổi (không tải lại trang) |
| 1-06 AC8 rỗng | ✅ | entries trả 0 bài: h2 "Góc bếp" biến mất |
| 1-06 AC9 "Cân đúng" | ✅ | 0 kết quả trong HTML 10 trang |
| 1-07 AC1,2,3,5 | ✅/⏸ | staging `--publish`: 3 chuyên mục, 10 trang, 5 bài, tất cả `published`, bài có ảnh bìa; lần 2: "tạo 0, không đổi 15, lỗi 0" (không trùng). AC2 (production → Nháp), AC4, AC6: ⏸ không chạy (đã có test BE trong 3657 test xanh) |
| 1-08 AC1–3,5 | ✅ | `/gioi-thieu/` nội dung từ API, nút "Xem hàng đang có", footer; 3 thẻ giá thật `/ kg`; API 404 → "Không tìm thấy bài này" + "Về trang chủ" (`gioi-thieu-404-360.png`); không "hút chân không/Cân đúng/ngay tại cảng" |
| 1-08 AC4 | ✅ | `grep "Vào Shop"`: 0; e2e landing trỏ `/gioi-thieu/` |
| 1-09 AC1 404 | ✅ | h1, 2 nút, footer, title "Không tìm thấy trang — Cá Về", `robots=noindex` (xem L1) |
| 1-09 AC2,3 metadata | ✅ | `/` title 46, mô tả 130; `/gioi-thieu/` 41, 143; không ngoặc vuông; không "Lô mới/miễn phí giao/tươi sống" |
| Chữ cấm toàn Shop | ❌ | B1 |
| Hotline | ❌ | B2 |
| 2-01 AC1–3,7 catalog | ✅ | `GET /api/shop/catalog/` + `/<code>/`: `in/low/out`, combo `unit:combo min 1 step 1`; quét mọi khoá + chuỗi: không `sellable_qty`, `on_hand`, giá vốn, mã lô, số kg tồn, PII; combo/low/out đều đúng |
| 2-02 AC1–3 | ✅ | 0,5 / 0,3 / 1,25 / 1,3 / 0 / -1 kg và combo 1,5 / 0 / -1 → `400 INVALID_QTY`, kèm `min_qty`,`qty_step`; đặt 2 kg món còn 1,5 + món hết → `OUT_OF_STOCK` `lines:[{short},{out}]`, không có số, "kg", mã lô, PII; đặt đúng 1,5 kg → 201, đặt lần nữa → `out`; 201 chỉ có `order_code,total_amount,booked_expires_at` |
| 2-02 AC6 log | ✅ | log `runserver` (36 dòng): không chứa tên, SĐT, địa chỉ giả |
| G1 | ✅ | regex `/còn\s*[\d.,]+\s*(kg|combo)/i`: 0 trong HTML 10 trang và JSON |
| G2 | ✅ | lô 1 không thu dữ liệu khách; localStorage chỉ có giỏ; console sạch; log BE sạch |
| G3 | ✅ | quét khoá cấm (`purchase_rate`, `unit_cost`, `batch_*`, `rate`, `margin`, `profit`): 0 |
| G4 | ✅ | BE 2-02 chạy thật như trên; FE N/A (lô 1) |
| G6 | ✅ | `scrollWidth` = 360 / 1280 ở 10 trang (home, gioi-thieu, 404, item, checkout, shop, bai-viet, 2 trang CMS, orders). So thiết kế: `design-Home` khớp (`Lệch`: xem L1) |
| G7 | ⏸ | file lô chạm: 0 hex, 0 `transition: all`. Toàn `grep` còn hex ở `app/shop/orders/OrderLookup.tsx` (lô 4 xoá) và `features/content/components/ItemCard.module.css` (lô 5), không do lô 1 sửa; ghi nhận L4 |
| G8 | ✅ | `SiteLegalFooter`, `ItemImageFrame`, `#0a6e8c`, `#e8912c`: 0 kết quả |

## Ngoại lệ & biên đã chạy
Giỏ hỏng; dark; reduced-motion; site-info/footer-links 500; catalog đứt mạng → thử lại; catalog chậm; không bài viết; `gioi-thieu` 404; combo; món sắp hết, hết, vừa hết sau đơn trước (đơn thứ hai cho cùng món); lệnh nạp 2 lần; 404 thật; build không cờ preview.

## Phân quyền / Rò giá vốn / Rò dữ liệu cá nhân / Hồi quy
- Phân quyền: lô 1 không có endpoint mới cho Group; `POST`/`PATCH` catalog đã có test BE xanh.
- Rò giá vốn: ✅ (G3). Rò dữ liệu cá nhân: ✅ (G2).
- Hồi quy: `manage.py test` toàn bộ **Ran 3657 tests, OK (skipped=9)**; `adapter pytest`: 68 passed; `check_naming.py`: OK, không vi phạm mới.

## Lỗi
### B1 — Chữ "Phí giao" trong trang CMS "Cách mua hàng" · Medium · AC chữ cấm (BR-BH-30, UI-RULES §2.3), SHOP-1-07
Tái hiện: nạp `load_shop_content`, mở `/trang/?slug=cach-mua-hang`.
Mong đợi: không có chữ "Phí giao". Thực tế: tiêu đề FAQ "Phí giao tính thế nào?" (`backend/apps/content/management/shop_content/pages.json` dòng 23).
Sửa: **mkt-brand** (đổi thành "Giao hàng có tốn thêm phí không?" hoặc tương đương, kèm bản 06-marketing).

### B2 — Hotline giữ chỗ "1900 xxxx" hiện cho khách như số gọi được · Medium · SHOP-1-03 AC1/AC7, SHOP-1-05, 02b §6.5
Tái hiện: chạy BE không đặt `SELLER_PHONE` (hoặc mock site-info `seller.phone=null`, `confirmation_policy.hotline="1900 xxxx"` là mặc định BE) và mở `/`.
Mong đợi: không có số thì ẩn nút gọi (AC7). Thực tế: header, nút "Gọi 1900 xxxx", dòng Hotline hiện 3 chỗ, link `tel:1900 `.
Ảnh hưởng: khách thấy số giả ở staging/production nếu quên cấu hình.
Sửa: **fe-dev** (chỉ nhận số hợp lệ, không chứa `x`; làm trong `ShopFrame.tsx`). Có thể kèm **be-dev** đổi mặc định hotline thành rỗng.

## Ghi nhận Low (không chặn)
- L1 Lệch thiết kế: `/khong-co-trang-nay/` ở 360 px dùng header H3 (quay lại + giỏ, không logo, không BottomNav); `X1-NotFound404` có logo "Cá Về" + tìm + giỏ + BottomNav. Chữ và nút đúng.
- L2 `<title>` của `/shop/item/`, `/shop/checkout/`, `/trang/` bị lặp "… | Cá Về" ("Shop — Cá Về | Cá Về"); `/404` ghi một lỗi console "Failed to load resource 404" (do HTTP 404 của chính trang, như Firebase).
- L3 Nhóm Chính sách dùng `<details>/<summary>` (mở/đóng đúng), AC3 ghi `aria-expanded` nhưng không có thuộc tính này.
- L4 Hex còn ở 2 file không thuộc lô 1 (xem G7).

## Lệnh đã chạy
`npm ci` (OK) · `npx tsc --noEmit` (exit 0) · `npm run build` ×3 (mock=0 có API, preview, mock=0 khôi phục): Compiled OK, `check-no-mock` XANH · `test-format` 33/33, `test-quantity` 45/45, `test-safe-href` 40/40 · `manage.py test`: 3657 OK · `adapter pytest`: 68 passed · `check_naming.py`: OK · script Playwright (trang, trạng thái lỗi, popup, toast, API, đặt đơn) trong scratchpad.
Đã dọn: tiến trình :8765/:3765/:3766, `backend/media/content/11–15`, `/tmp/seed_qa_ids.json`; `frontend/out` được build lại với `NEXT_PUBLIC_USE_MOCK=0`.

---

# Lần 2 · 2026-10-11 (sau sửa B1, B2, Low, review fix)
## Kết luận: APPROVED — B1 và B2 xanh trên BE thật; 0 lỗi chặn. Còn 1 Low (title lặp ở `/shop/*`).
Tổng lần 2: 22 ca · ✅ 21 · ❌ 1 (Low, không chặn) · ⏸ 0.

Môi trường: BE thật (SQLite tạm; `load_shop_content --publish` chạy lại với `pages.json` mới: "cập nhật 2, không đổi 13, lỗi 0"), FE build `USE_MOCK=0` API `:8765` phục vụ tĩnh, ERP build `USE_MOCK=0` API `:8765` phục vụ tĩnh `:3661`, đăng nhập `qa_owner` (dữ liệu giả). `npm ci` + `tsc --noEmit` exit 0 + build OK.

| Hạng mục | KQ | Bằng chứng |
|---|---|---|
| B1 chữ "Phí giao" | ✅ | quét HTML 10 trang: chỉ còn "hoàn tiền" ở tên trang chính sách; `/trang/?slug=cach-mua-hang` hết "Phí giao"; `grep "Phí giao" shop_content/`: 0 |
| B2 có `SELLER_PHONE` | ✅ | 360 và 1280: `tel:0900000009`, 0 chữ "xxxx" |
| B2 không `SELLER_PHONE` (BE vẫn trả hotline mặc định "1900 xxxx") | ✅ | 360 và 1280: 0 link `tel:`, 0 chữ "Hotline", 0 "xxxx", 0 lỗi trang |
| B2 mock site-info | ✅ | (null,"1900 xxxx") ẩn; ("","0900000007") hiện; (null,null) ẩn; ("abc","1900 1234") rơi về hotline `tel:19001234`; `test-phone` 17/17 |
| 404 ở 360/1280 theo X1 | ✅ | `404-360.png`: header logo "Cá Về" + tìm + giỏ, BottomNav, footer; `404-1280.png`: header 2 tầng, EmptyState trong thẻ; `noindex`; `scrollWidth` 360/1280 |
| Title `/trang/` | ✅ | "Chính sách đổi trả và hoàn tiền — Cá Về", "Điều kiện giao dịch chung — Cá Về" |
| Title `/shop/*` | ❌ Low | `/shop/`, `/shop/item/`, `/shop/checkout/`, `/shop/orders/` vẫn "Shop hải sản cấp đông \| Cá Về \| Cá Về" (lặp hậu tố). Không chặn; fe-dev bỏ hậu tố trong tiêu đề trang (lô 2) |
| POST qty `"1e30"` | ✅ | `400 INVALID_QTY` (không 500); thêm `-1e30`, `1e-3`, `1e30000`, số JSON `1e30`, combo `1e30` → `INVALID_QTY`; `NaN`, `Infinity`, `0x10` → `400 VALIDATION`; `1E5` → `OUT_OF_STOCK`; `1.0` và `" 1 "` → 201. 0 Traceback, 0 SĐT/tên trong log BE |
| e2e `ra-soat-a2-golive.py` (viết lại) | ✅ | trên build thật `:3765`: 3 lần liên tiếp **57 PASS / 0 FAIL**. Lần chạy đầu sau khi bật server có 4 FAIL (GL-01-AC2 trang nội dung ×3, GL-04-AC2), không lặp lại ở 3 lần sau; ghi nhận là nhiễu do máy chủ tĩnh thử nghiệm (reset kết nối), không tái hiện |
| ERP "Chèn thẻ mặt hàng" chế độ thật | ✅ | `qa_owner` → `/content/edit/?new=1` → nút "Chèn thẻ mặt hàng": liệt kê 14 món từ `{groups, items}`, không giá, không số kg; lọc "combo" còn 1 món; chọn thì chèn và đóng hộp; 0 lỗi console (`erp-insert-item-card-real-1280.png`) |
| Hồi quy trang chủ, `/gioi-thieu/`, footer | ✅ | 10 trang × 2 khổ: `scrollWidth` 360/1280, 0 request fonts.g*, header H2 sau cuộn, "Chính sách" mở `false → true`, tìm "mực", badge, giỏ hỏng, dark. Các dòng "Failed to load resource" ban đầu do tôi lỡ dọn ảnh bìa tạm; dựng lại thì 0 lỗi |
| Hồi quy popup `/ui-preview/` | ✅ | build preview: 4 hộp (Dialog xác nhận, cảnh báo, BottomSheet, FullscreenSheet) `aria-modal`, Tab/Shift+Tab 20 lần không ra ngoài, Esc đóng, trả tiêu điểm (360/1280; 440/480 px máy tính); toast `role=status`, ẩn ~3,15 s; build thường không có `/ui-preview/` |
| Script FE | ✅ | `test-phone` 17/17, `test-format` 33/33, `test-quantity` 45/45, `test-safe-href` 40/40, `check-no-mock` XANH |

Dọn xong: tiến trình `:8765/:3765/:3766/:3661`, `backend/media/content/11–15`, `/tmp/seed_qa_ids.json`. `frontend/out` là build `NEXT_PUBLIC_USE_MOCK=0` (API `localhost:8000`), không có `ui-preview`. `erp-console/out` (gitignore) hiện là bản build `USE_MOCK=0` API `:8765` dùng cho lần kiểm này; build lại nếu cần.

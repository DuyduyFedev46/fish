# Shop làm lại từ đầu theo thiết kế 06/10: user stories
> PO · 2026-10-11 · Nguồn: `01-analysis.md` (ĐÃ DUYỆT 10/10: nhóm A §11.1 + V-01…V-12) · Trạng thái: **ĐÃ DUYỆT** 11/10 (Duy giao tự duyệt theo khuyến nghị: đồng ý kéo 1-07/1-08 lên lô 1, `/ui-preview/` chỉ bật bằng cờ build, giỏ có món hết thì chặn "Đặt hàng" tới khi khách bỏ món — techlead được đổi ở 02b)
> Nhánh `shop/lo-0-quyet-dinh`. Đầu vào thêm: `00-product-brief.md` (lát MVP, đổi lô S-09 đã duyệt), `05-phap-ly.md`, `06-marketing.md`, `doc/decisions.md` mục 2026-10-10 (tối),
> `doc/design/shop/` (README, UI-RULES, PLAN, COMPONENTS mục "Ánh xạ màn → component", DOI-CHIEU-CODE §4 BE-1…BE-11, HUONG-DAN-CODE §6).
> Mã BR dùng theo `01-analysis.md` §7.2 (BR-DM-17…25, BR-BH-22…30, BR-TT-19, BR-HT-12, BR-ND-20/21). **Không** dùng BR-BH-18/19 cũ của PLAN.
> Contract API trong file này là **dự kiến** để FE dựng mock. `techlead` chốt ở `02b-tech-design.md`; lệch thì 02b thắng, PO sửa AC theo.

---

## Mục tiêu và thước đo
Khách mua trọn vòng trên Shop mới (xem → giỏ → đặt → trả QR → trang đơn) mà không thấy số kg tồn, giá vốn hay dữ liệu cá nhân của ai. Lộc không phải bán lẻ dưới 1 kg,
và phát được mã giảm giá có trần, lượt, hạn từ ERP.
Thước đo (đọc DB production, không analytics, theo `00-product-brief.md` §1.2): **tỷ lệ đơn đã trả tiền** (chính) · tỷ lệ giữ chỗ hết hạn (canh chừng 1) · tiền giảm do mã ÷ doanh thu gộp (canh chừng 2, từ 3b).
Số gốc là 4 tuần đầu sau go-live.

## Phạm vi
**Trong:** khung chung, nhóm màn A–F ở 360/390 px và 1280 px, `/` là trang chủ Shop, `/gioi-thieu/` dựng mới · contract API Shop mới (mức tồn, đơn vị, tối thiểu/bước, slug nhóm, field mặt hàng, lỗi có cấu trúc,
chống trùng, tra đơn POST + mã tra đơn, mốc giờ, nhãn lý do huỷ) · mã giảm giá (Shop + màn ERP) · màn ERP field mặt hàng và slug nhóm · nạp nội dung CMS, mở rộng CMS (banner, `page_role` mới, site-info).
**Ngoài (V1):** theo `01-analysis.md` §5.2 (phí ship, HĐĐT trên Shop, tiến độ hoàn tiền trên Shop, khách tự huỷ, chip "Tìm nhiều", "Lô mới về", nhiều ảnh, menu hai cấp, dark mode,
mã riêng từng khách, lưu toạ độ, "Vị trí của tôi", tiền tố `CV`, màn D5 riêng, analytics/pixel/chat, kiểm vùng giao tự động BR-BH-12).

## Người làm
`be-dev` (backend, adapter) · `fe-dev` (frontend Shop, erp-console) · `mkt-brand` (full stack phần nội dung/CMS: app `content`, lệnh nạp nội dung, site-info, trang `/gioi-thieu/`, `/trang/`, `/bai-viet/`, 404, SEO;
**không** đụng tiền, giá vốn, kho, đơn, thanh toán) · `qa-tester` (lô 7). "cả hai" = be-dev ∥ fe-dev theo contract.

## Definition of Done (chung, không lặp lại trong từng story)
Lệnh kiểm chứng `HUONG-DAN-CODE.md` §6 chạy sạch (điều phối viên tự chạy lại, dán output vào `03-dev-notes.md`): `npm ci && npx tsc --noEmit && npm run build && node scripts/check-no-mock.mjs`,
`test-format`, `test-safe-href`; BE `manage.py test apps.catalog apps.sales apps.content` thấy dòng "Ran … OK" + `makemigrations --check --dry-run` sạch; ERP `tsc --noEmit && npm run build` khi lô có ERP;
`python3 scripts/check_naming.py` exit 0 · `techlead` review diff · `qa-tester` APPROVED (`04-qa-report.md`, không PASS bằng đọc code) · BR/spec cập nhật nếu đổi rule (điều phối, không phải dev).

---

## AC bắt buộc chung cho mọi lô (mã `G1…G8`, QA ghi dạng "SHOP-2 G3")

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| **G1** Không số kg tồn | Dữ liệu staging có món còn 2,7 kg, món còn 0,6 kg, combo ráp được 2 bộ | (BE) gọi mọi endpoint `/api/shop/*`, `/api/public/*` lô chạm · (FE) mở mọi màn của lô | JSON không có khoá `sellable_qty`, `available_qty`, `stock_qty`, `qty_available`, `on_hand` hay số kg tồn ở bất kỳ khoá nào; chữ trên trang (kể cả popup C3, `aria-label`) không khớp regex `/còn\s*[\d.,]+\s*(kg|combo)/i` | BR-BH-01, 23, 24 |
| **G2** Không rò dữ liệu cá nhân | Đơn giả: tên `Nguyễn Văn A`, SĐT `0900000001`, địa chỉ `1 Đường Thử, Phường Mẫu` | Gọi mọi API công khai lô chạm; đọc `localStorage`, `sessionStorage`, URL, console trình duyệt, log BE của lần chạy test | Không chỗ nào chứa 3 chuỗi trên (kể cả SĐT dạng `+84900000001`, `900000001`); log chỉ có mã đơn và SĐT đã che. Test và ảnh chụp chỉ dùng dữ liệu giả | Bất biến 9, BR-BH-25, 26 |
| **G3** Không rò giá vốn | Như G1 | Như G1; với ERP: gọi API mới bằng user `manager` không có `view_costprice` | Không có khoá `purchase_rate`, `landed_unit_cost`, `unit_cost`, `rate`, `batch_id`, `batch_code`, `margin`, `profit`; câu lỗi không chứa mã lô; serializer liệt kê field tường minh (không `__all__`) | Bất biến 1 |
| **G4** Tối thiểu 1 kg, chặn cả FE và BE | Món kg `min_qty=1`, `qty_step=0.5`; combo bước 1 | (FE) bấm "−" khi đang ở 1 kg hoặc 1 combo · (BE) gọi thẳng `POST /api/shop/orders/` với `0.5`, `0.3`, `1.25` kg, `1.5` combo, `0` combo | FE mở dialog bỏ món (B2), không bao giờ hiện 0,5 kg hay số lẻ ngoài bước; BE trả `400 INVALID_QTY`, không tạo đơn, không giữ chỗ. Lô không có đường đổi số lượng ghi "G4: N/A, lý do…" trong `03-dev-notes.md` và QA chạy lại phần BE để chắc không lùi | BR-BH-22 |
| **G5** Popup | Mọi Dialog, BottomSheet, FullscreenSheet của lô | Mở bằng bàn phím; nhấn Tab rồi Shift+Tab 20 lần; nhấn Esc | Có `role="dialog"` + `aria-modal="true"`; tiêu điểm không ra khỏi popup; Esc đóng; tiêu điểm trả về nút đã mở. Toast là `role="status"`, không cướp tiêu điểm. Máy tính: hộp thoại rộng 440–480 px | UI-RULES §5 |
| **G6** Ảnh chụp so thiết kế | Mọi màn và ca lỗi của lô (cột "Màn thiết kế" của từng story) | Chụp ở **360 px** và **1280 px** | Lưu `shots/lo-<n>/<tên màn>-360.png`, `-1280.png`, đặt cạnh file `screens/*.dc.html`; ở 360 px `document.documentElement.scrollWidth ≤ 360`; chỗ khác thiết kế phải thuộc bảng "Chỗ đã chuẩn hoá" của COMPONENTS, không thì ghi "Lệch thiết kế" | UI-RULES §4.2 |
| **G7** Không mã hex rời | — | `grep -rnE "#[0-9A-Fa-f]{6}" frontend/components frontend/app frontend/features \| grep -v globals.css` và `grep -rn "transition: all" frontend/` | Cả hai ra 0 dòng (ERP: lệnh tương tự cho file lô sửa) | UI-RULES §9 |
| **G8** Xoá code Shop cũ lô thay thế | Danh sách "Xoá" ghi ở đầu mỗi lô | `grep -rn` từng tên trong danh sách ở `frontend/` (và `backend/` nếu có) | 0 kết quả ngoài `doc/`; e2e cũ trỏ route hoặc chữ cũ của lô đã sửa hoặc xoá trong chính lô; không còn hai bản cùng chạy | S-09a |

---

# LÔ 1 · Khung chung (FE ∥ mkt-brand) · chạy song song với BE lô 2

**Xoá trong lô (G8):** Landing ở `frontend/app/page.tsx` · `ShopHeader`/`ShopFooter` bản cũ (viết lại cùng tên) · `features/site/components/SiteLegalFooter.tsx` (+ `.module.css`) và chỗ gắn ở `app/layout.tsx` ·
`components/ItemImageFrame.tsx` (thay bằng `components/catalog/ImageFrame.tsx`) · biến màu cũ `#0a6e8c`, `#e8912c` và mọi token Shop cũ trong `globals.css` · `components/ContactButton.tsx` nếu không còn chỗ dùng · phần e2e trỏ landing ở `/` (`ra_soat_cms14_landing.py`) và footer cũ (`ra-soat-a2-golive.py`).
**fe-dev được sửa:** `frontend/app/layout.tsx`, `app/page.tsx`, `app/shop/layout.tsx`, `app/globals.css`, `components/ShopHeader.*`, `components/ShopFooter.*`, `components/BottomNav.*`, `components/LogoSlot.*`, `components/CartContext.tsx`,
mới `components/ui/*`, `components/catalog/{PriceTag,ImageFrame,CategoryTile,ProductCard}.*`, `components/search/SearchBox.*`, mới `app/ui-preview/page.tsx`, `DESIGN.md` (chỉ thêm token), `frontend/e2e/*` liên quan.
**fe-dev không đụng:** `lib/api.ts`, `lib/types.ts`, `features/checkout/*`, `backend/`. **mkt-brand được sửa:** `backend/apps/content/**` (lệnh nạp), `app/gioi-thieu/*`, `app/not-found.tsx`, khối `metadata` của `app/page.tsx` (sau khi SHOP-1-06 xong).
**G4 ở lô 1:** N/A, lô không tạo đường thêm hàng mới (nút "Chọn mua" dẫn sang trang chi tiết). QA vẫn chạy phần BE của G4 khi BE lô 2 đã vào.

## SHOP-1-01 · Nền giao diện: token, font, giỏ ở gốc, badge số món · Must · fe-dev
**Là** Khách, **tôi muốn** mọi trang Shop dùng chung màu, chữ và giỏ hàng, **để** đi từ trang chủ sang Góc bếp vẫn thấy đúng số món trong giỏ.
Bối cảnh: COMPONENTS §1 (bảng biến CSS), "Token cần thêm vào DESIGN.md"; DOI-CHIEU L-18, L-21; Q-UX-1 (chỉ giao diện sáng, D8). Màn: `CMP-1-Tokens`, `Home`, `DesktopHome`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | — | Đọc `app/globals.css` và `git diff DESIGN.md` | `:root` khai đủ biến bảng COMPONENTS §1 (nền, viền, chữ, nhấn, `brand-deep*`, trạng thái, lớp phủ, bo góc, bóng, khoảng cách, chiều cao, chuyển động, z-index); diff `DESIGN.md` chỉ có dòng **thêm** cho 14 token mới, không dòng xoá/sửa | UI-RULES §9 |
| AC2 | Trình duyệt sạch cache | Mở `/` và ghi log mạng | Chữ dùng Inter (computed `font-family` bắt đầu bằng Inter); **0** request tới `fonts.googleapis.com` hoặc `fonts.gstatic.com` | `05-phap-ly.md` §1.1 |
| AC3 | Trình duyệt giả lập `prefers-color-scheme: dark` | Mở `/` | Nền `body` vẫn là `--canvas` (#FBFBFC); `color-scheme: light` | D8 |
| AC4 | Giỏ có 1 món (thêm ở `/shop/` bản hiện có) | Mở `/`, `/bai-viet/`, `/trang/?slug=doi-tra` | Cả ba trang đều hiện badge giỏ "1" (CartProvider ở `app/layout.tsx`, không còn ở `app/shop/layout.tsx`) | UI-RULES §4.4 |
| AC5 | Giỏ có 2 món: 1,5 kg + 2 kg | Nhìn badge giỏ | Badge là **"2"** (số món, không phải 3,5); giỏ 0 món thì không có phần tử badge trong DOM | UI-RULES §4.4 |
| AC6 (dữ liệu) | Giỏ có món | Đọc toàn bộ `localStorage` | Khoá giỏ chỉ chứa mã hàng, số lượng, giá lúc thêm (và tên món); không có khoá nào chứa tên, SĐT, địa chỉ người | Bất biến 9 |
| AC7 (lỗi) | `localStorage` khoá giỏ bị ghi chuỗi hỏng `{"x":` | Mở `/` | Trang không lỗi, giỏ coi như rỗng, badge ẩn, console không có lỗi chưa bắt | |
| AC8 | `prefers-reduced-motion: reduce` | Bấm nút bất kỳ | Không có `transform: scale` khi nhấn; đổi màu vẫn có | UI-RULES §8.4 |

## SHOP-1-02 · Bộ component nền và trang xem thử · Must · fe-dev
**Là** fe-dev và QA, **tôi muốn** một bộ component trình bày dùng lại được và một trang xem thử, **để** các lô sau lắp màn nhanh và QA kiểm được popup trước khi có màn thật dùng nó.
Bối cảnh: COMPONENTS #1, 2, 3 (chip header), 5, 12 (biến thể `rail`, `row`), 14, 17, 18, 37–47, Icon (Q-UX-2: SVG nét gom ở `components/ui/Icon.tsx`). Component nhận dữ liệu qua props, không gọi API, không đọc `localStorage` (COMPONENTS §3).
Không thêm thư viện; hộp thoại dùng `<dialog>` + `showModal()`. Màn: `CMP-2-Buttons`, `CMP-4-Product`, `CMP-6-Navigation`, `CMP-7-Overlay-Feedback`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Build có `NEXT_PUBLIC_UI_PREVIEW=1` | Mở `/ui-preview/` | Trang hiện mọi biến thể × trạng thái của Button, IconButton (+CartBadge), Chip, TextLink, Dialog, BottomSheet, FullscreenSheet, Popover, Toast, Banner, EmptyState, ErrorState, Skeleton (+`ProductCardSkeleton`), Spinner, PriceTag, ImageFrame, CategoryTile, ProductCard `rail`/`row` | |
| AC2 (quyền/ẩn) | Build **không** có `NEXT_PUBLIC_UI_PREVIEW` (như production) | Mở `/ui-preview/` | Hiện trang 404, không có component xem thử trong HTML | |
| AC3 | Dialog, BottomSheet, FullscreenSheet ở `/ui-preview/` | Chạy kiểm G5 | Đạt G5; lớp phủ dùng `--overlay`; BottomSheet có thanh kéo, mép trên bo `--radius-sheet` | UI-RULES §5 |
| AC4 | Toast | Kích hoạt toast | `role="status"`, tự ẩn sau 3000 ms (±200), tiêu điểm vẫn ở nút đã bấm; hai toast liên tiếp thì toast sau thay toast trước | |
| AC5 | Khổ 360 px | Đo mọi nút, IconButton, link trong component | Vùng chạm ≥ 44×44 px (chip 40 có vùng mở rộng 44); `:focus-visible` có viền 2 px màu `--focus` | UI-RULES §8.1 |
| AC6 | PriceTag `price="278000"`, `unit="kg"` / `unit="combo"` | Render | Chữ đúng `278.000đ / kg` và `278.000đ / combo`, có `tabular-nums` | UI-RULES §1.1 |
| AC7 | ImageFrame không có ảnh, nhóm `shrimp` / ảnh lỗi tải | Render | Khung `--surface-2` + icon nhóm tôm; ảnh lỗi thì rơi về khung này; ảnh minh hoạ có nhãn "Ảnh minh hoạ"; giữ `srcSet`/`sizes` như `ItemImageFrame` cũ | UI-RULES §1.6 |
| AC8 (dữ liệu) | — | `grep -rn "sellable\|qty_available" frontend/components` | 0 kết quả. Kiểu props ProductCard chỉ nhận `stockLevel: 'in' \| 'low' \| 'out'`, không có prop số kg | BR-BH-23 |
| AC9 | — | `git diff frontend/package.json` | Không thêm dependency nào | HUONG-DAN-CODE §7 |

## SHOP-1-03 · Header H1–H4, logo và ô tìm · Must · fe-dev
**Là** Khách, **tôi muốn** thấy header kiểu bán lẻ có ô tìm, gọi, tra đơn và giỏ, **để** tìm hàng và quay về giỏ từ bất kỳ trang nào.
Bối cảnh: COMPONENTS #10 (chỉ SearchBox, gợi ý ở lô 2), #30, #37; UI-RULES §4.3 (bỏ chip "Tìm nhiều", D); D10 menu nhóm một cấp; D12 chưa có logo thì chữ "Cá Về"; L-30.
Màn: `HeaderFooter-Mobile`, `HeaderFooter-Desktop`, `Home`, `DesktopHome`, `Main`, `Product`, `Cart`, `Checkout`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | site-info có hotline | Mở `/` ở 360 px | H1 nền thương hiệu: chữ "Cá Về" là link `/` (`aria-label` "Cá Về — trang chủ"), nút gọi `tel:<hotline>`, link "Tra cứu đơn" `/shop/orders/`, nút giỏ có badge, ô tìm. **Không** có chip "Tìm nhiều" trong DOM | D12, UI-RULES §4.3 |
| AC2 | Trang chủ ở 360 px | Cuộn xuống quá header | Header đổi sang H2 nền trắng, cao 56 px, dính đầu trang | |
| AC3 | Mở `/shop/item/?code=X` trực tiếp (không có lịch sử) | Bấm nút quay lại H3 | Về `/shop/`; có lịch sử thì `history.back()` | |
| AC4 | Mở `/shop/checkout/` | Nhìn header | H4: chỉ nút quay lại và tiêu đề; không logo, không giỏ, không menu | UI-RULES §4.3 |
| AC5 | 1280 px, catalog có 4 nhóm | Mở `/` | Header 2 tầng; menu nhóm **một cấp** lấy từ catalog; số hotline hiện thành chữ đọc được; nút "Tìm" nền `--brand-deep`; nhóm đang xem có `aria-current="page"` | D10, L-30 |
| AC6 | Gõ "mực" vào ô tìm | Nhấn Enter hoặc "Tìm" | Đi tới `/shop/?q=m%E1%BB%B1c`; ô rỗng thì không điều hướng | |
| AC7 (lỗi) | API site-info lỗi 500 / catalog lỗi mạng | Mở `/` | Header vẫn hiện; nút gọi ẩn khi không có hotline; menu nhóm ẩn khi catalog lỗi; không vỡ bố cục | |
| AC8 | Giỏ có món, lô 2 chưa xong | Bấm nút giỏ | Đi tới `/shop/checkout/` (đích tạm); lô 2 đổi thành `/shop/cart/` (SHOP-2-06 AC9) | |

## SHOP-1-04 · Thanh điều hướng đáy (BottomNav) · Must · fe-dev
**Là** Khách dùng điện thoại, **tôi muốn** thanh đáy Trang chủ · Danh mục · Giỏ hàng · Đơn hàng, **để** chuyển trang bằng một ngón tay.
Bối cảnh: COMPONENTS #31; D9 (thêm trang tra cứu đơn, bật ở lô 4); Q-UX-6. Màn: `Home`, `Main`, `A0-Loading`, `G1-KitchenList`, `HeaderFooter-Mobile`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | 360 px | Mở `/`, `/shop/`, `/bai-viet/` | BottomNav hiện, 4 mục đúng thứ tự, mục đang ở có `aria-current="page"`, mục Giỏ có badge số món | D9 |
| AC2 | 360 px | Mở `/shop/item/?code=X`, `/shop/checkout/`, `/trang/?slug=doi-tra` | Không có BottomNav | UI-RULES §4.5 |
| AC3 | ≥ 768 px | Mở `/` | Không có BottomNav | |
| AC4 | 360 px, cuộn tới cuối trang `/` | Nhìn nội dung cuối | Footer không bị thanh đáy che (khoảng đệm = `--h-bottom-nav` + `env(safe-area-inset-bottom)`) | |

## SHOP-1-05 · Footer F1/F2 gộp dải pháp lý · Must · fe-dev
**Là** Khách, **tôi muốn** footer có cách liên hệ, các trang chính sách và thông tin người bán, **để** tin được nơi mình chuyển tiền.
Bối cảnh: COMPONENTS #32; UI-RULES §4.6; §9.2 điểm 3 của analysis (nhóm "Chính sách" lấy từ `footer-links`); BR-ND-18 (sửa: trường trống thì ẩn khối); D12 (biểu tượng thông báo chỉ khi có link); S-22 tên trang `terms`.
Màn: `HeaderFooter-Mobile`, `HeaderFooter-Desktop`, `Home`, `DesktopHome`, `Cart`, `DesktopCart`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | CMS có các trang `show_in_footer` | Mở `/` ở 1280 px | F1 có: nhóm liên hệ (gọi), nhóm Mua hàng, nhóm **Chính sách lấy đúng danh sách `GET /api/public/content/footer-links/`** (tên hiện theo tiêu đề CMS, trang `terms` là "Điều kiện giao dịch chung"), nhóm Về Cá Về (Giới thiệu `/gioi-thieu/`, Góc bếp `/bai-viet/`, Liên hệ `/trang/?slug=lien-he`), dải pháp lý | BR-ND-18, 19 |
| AC2 | site-info `seller.tax_code` rỗng, chưa có trường `zalo` và link thông báo website | Mở `/` | Dòng MST ẩn hẳn (không chữ "Đang chờ", không nhãn trống); nút Zalo ẩn; **không** có biểu tượng Bộ/Sở Công Thương | BR-ND-18, D12 |
| AC3 | 360 px | Mở `/`, bấm tiêu đề nhóm "Chính sách" | Nhóm thu gọn mặc định, bấm thì mở, `aria-expanded` đổi `false → true` | |
| AC4 | Mở `/shop/checkout/` | Nhìn footer | F2 rút gọn theo `HeaderFooter-*`; link chính sách mở tab mới (`target="_blank"`, `rel="noopener"`, có chữ ẩn "mở tab mới") | |
| AC5 | Ngày hệ thống 2027-01-01 00:30 giờ VN | Mở `/` | Dòng © hiện 2027 (`currentYearInVietnam()`, không hard-code) | GMT+7 |
| AC6 (lỗi) | `footer-links` lỗi 500 | Mở `/` | Footer vẫn hiện các nhóm còn lại, nhóm Chính sách ẩn, không lỗi console chưa bắt | |
| AC7 (xoá) | — | `grep -rn SiteLegalFooter frontend/` | 0 kết quả; root layout không còn gắn footer pháp lý riêng | S-09a |

## SHOP-1-06 · Trang chủ Shop ở `/` (A1) · Must · fe-dev
**Là** Khách, **tôi muốn** vào `/` là thấy ngay hàng đang bán theo nhóm, **để** chọn mua mà không phải qua trang giới thiệu.
Bối cảnh: decisions 10/10 (`/` là trang chủ Shop); D7 bỏ "Lô mới về"; COMPONENTS "Ánh xạ" dòng A1. Dữ liệu dùng catalog **hiện có**; lô 2 nối `stock_level`, slug nhóm.
Chữ banner và dải cam kết lô này lấy **bản an toàn** ở `06-marketing.md` C5 (chỉ dòng "ĐÃ ĐỐI CHIẾU"), để tạm trong một file nội dung `features/home/content.ts`; SHOP-5-03 chuyển sang CMS.
**Chặn một phần bởi S-18:** câu "Cân đúng số kg bạn đặt" và cam kết 3 "Cân đúng, tính đúng" **không** hiện cho tới khi Duy/Lộc trả lời. Phần còn lại làm ngay.
Màn: `Home`, `DesktopHome`, `A0-Loading`, `DesktopLoading`, `A6-Offline`, `DesktopOffline`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Catalog staging có món SIMPLE và BUNDLE | Mở `/` | Có banner (slide 1), lưới nhóm (CategoryTile + số món mỗi nhóm đếm từ catalog), hàng "Đang có hàng" (ProductCard `rail`), hàng "Combo nấu nhanh" (chỉ BUNDLE), khối Góc bếp (bài mới nhất), dải cam kết 2 mục, footer F1, BottomNav. **Không** có ô "Lô mới về" | D7 |
| AC2 | Món SIMPLE giá 278000, combo giá 450000 | Nhìn thẻ | Thẻ SIMPLE ghi `278.000đ / kg`, combo ghi `450.000đ / combo`; không thẻ nào hiện số kg tồn | BR-DM-01, G1 |
| AC3 | Món có tồn bán được < 1 kg | Mở `/` | Món không nằm trong hàng "Đang có hàng" | BR-BH-23 |
| AC4 | — | Bấm "Chọn mua" trên thẻ | Đi tới `/shop/item/?code=<mã>`; không thêm vào giỏ ở bước này | |
| AC5 | Bấm một ô nhóm | — | Đi tới `/shop/` (đích tạm); SHOP-2-03 AC10 đổi thành `/shop/?group=<slug>` | |
| AC6 (tải) | Mạng chậm (giả lập 3G) | Mở `/` | Header và lưới khung xương hiện trong lúc tải, `aria-busy="true"` trên vùng hàng | UI-RULES §7 |
| AC7 (lỗi) | Catalog lỗi mạng | Mở `/` | Vùng hàng hiện "Chưa tải được hàng" + nút "Thử lại"; bấm "Thử lại" khi mạng có lại thì hiện hàng, không tải lại cả trang | UI-RULES §7 |
| AC8 (rỗng) | Không có bài viết đã đăng | Mở `/` | Khối Góc bếp ẩn hẳn | |
| AC9 (claim) | — | Tìm chữ "Cân đúng" trong HTML `/` | 0 kết quả khi S-18 chưa trả lời | BR-DM-25, BR-ND-21 |

## SHOP-1-07 · Lệnh nạp nội dung CMS (bản đầu) · Must · mkt-brand
**Là** Lộc, **tôi muốn** nội dung chữ của thiết kế được nạp sẵn vào CMS bằng một lệnh chạy lại được, **để** staging có đủ trang chính sách, liên hệ, cách mua, giới thiệu và tôi sửa ở màn Nội dung ERP.
Bối cảnh: decisions 10/10 (nạp CMS; staging đăng luôn toàn bộ, production để Nháp); analysis §9.1; `06-marketing.md` C1–C4; BR-ND-21. Lệnh đặt ở `backend/apps/content/management/commands/` (tên tiếng Anh, ví dụ `load_shop_content`).
Lô 1 nạp các vai trò trang **đang có** (`privacy`, `terms`, `refund`, `seller_info`) và trang thường (`cach-mua-hang`, `lien-he`, `gioi-thieu`, `giao-hang`, `thanh-toan`, `khieu-nai`). SHOP-5-02 gắn vai trò mới cho 3 trang sau.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | DB trống nội dung, môi trường staging (`--publish` hoặc biến môi trường staging) | Chạy lệnh | Tạo 3 chuyên mục Góc bếp, 10 trang, 5 bài (bài cá nục **không** nạp khi S-23 chưa trả lời); tất cả ở trạng thái **Đã đăng**; bài Góc bếp có ảnh bìa tạm gắn nhãn "Ảnh minh hoạ" | decisions 10/10, BR-ND-03 |
| AC2 | Môi trường production (mặc định, không cờ) | Chạy lệnh | Mọi trang, bài ở trạng thái **Nháp**; không trang nào đăng | decisions 10/10 |
| AC3 (idempotent) | Đã chạy lệnh một lần, Lộc sửa tay trang `lien-he` | Chạy lại lệnh | Không tạo bản trùng (khớp theo slug và `page_role`); trang đã sửa tay **không** bị ghi đè (lệnh in "bỏ qua: đã sửa"), trừ khi có cờ `--overwrite` | |
| AC4 (lỗi) | Thân bài chứa SĐT không thuộc `CONTENT_PHONE_ALLOWLIST` | Chạy lệnh | Lệnh dừng ở trang đó, báo slug và lý do, các trang khác vẫn nạp; exit code ≠ 0 | BR-ND (lọc SĐT) |
| AC5 (claim) | — | Tìm trong dữ liệu nạp các chữ "hút chân không", "cấp đông ngay tại cảng", "Cân đúng", "tươi sống", "miễn phí giao" | 0 kết quả (S-18 chưa trả lời) | BR-ND-21, BR-BH-30 |
| AC6 (quyền) | — | Chạy lệnh trỏ vào DB production mà không có cờ xác nhận `--environment production` | Lệnh từ chối chạy | |
| AC7 | Trang chính sách có chỗ `[Do legal-vn soạn]` | Nạp | Chữ được thay bằng câu ở `05-phap-ly.md` khi đã có; ô `[…]` còn lại giữ nguyên dấu ngoặc để dễ tìm | BR-ND-21 |
| AC8 (dữ liệu) | — | Đọc toàn bộ file nguồn của lệnh | Không có SĐT, tên, địa chỉ người thật; hotline lấy từ settings, không viết cứng | Bất biến 9 |

## SHOP-1-08 · Trang giới thiệu `/gioi-thieu/` dựng mới · Must · mkt-brand
**Là** Khách mới, **tôi muốn** đọc một trang giới thiệu Cá Về mua ở đâu, giao thế nào, **để** quyết định có tin mua không.
Bối cảnh: decisions 10/10 (landing chuyển `/gioi-thieu/`, dựng mới); analysis §9.1 cách (a): trang CMS `gioi-thieu` dạng bài đọc với chữ `06-marketing.md` C2.3; các phần nhiều khối (hero, thẻ bước, khối giá có thẻ hàng) theo 02b, có thể bổ sung ở SHOP-5-03.
**Chặn một phần bởi S-18** (sơ chế, cấp đông, đóng gói, "cân đúng") và **S-08** (`[khu vực giao]`): dùng bản đã bỏ claim, ô khu vực ẩn cho tới khi có. Màn: `Landing`, `LandingMobile`.
Dùng component của SHOP-1-02/03/05 (phụ thuộc).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Trang CMS `gioi-thieu` đã đăng | Mở `/gioi-thieu/` | Hiện header `full`, nội dung đọc từ `GET /api/public/content/entries/gioi-thieu/` (không viết cứng chữ trong code), nút "Xem hàng đang có" → `/shop/`, footer F1 | BR-ND-21 |
| AC2 | Khối "giá có thẻ hàng" | Mở trang | Thẻ hàng lấy giá thật từ catalog, đơn vị `/ kg` hoặc `/ combo`, không số kg tồn | G1 |
| AC3 (lỗi) | Trang CMS chưa đăng (404) | Mở `/gioi-thieu/` | Hiện trạng thái "Không tìm thấy bài này" của `06-marketing.md` C7 với nút "Về trang chủ"; không màn trắng | |
| AC4 | Link cũ trong bài viết, e2e trỏ landing ở `/` | `grep -rn` "Vào Shop" và các link landing cũ | Link "Vào Shop" cũ trỏ `/`; e2e `ra_soat_cms14_landing.py` sửa sang `/gioi-thieu/` | S-09a |
| AC5 (claim) | — | Tìm "hút chân không", "Cân đúng", "ngay tại cảng" trong HTML | 0 kết quả khi S-18 chưa trả lời | BR-DM-25 |

## SHOP-1-09 · Trang 404 và metadata SEO `/`, `/gioi-thieu/` · Should · mkt-brand
**Là** Khách gõ nhầm link, **tôi muốn** một trang 404 có lối về, **để** không bị kẹt. **Là** Duy, **tôi muốn** tiêu đề và mô tả tìm kiếm đúng, **để** Shop hiện tử tế trên Google.
Bối cảnh: D11 (chữ 404 và SEO `/` ở code); `06-marketing.md` C7, C8. **Chặn một phần bởi S-08:** mô tả `/` có `[khu vực giao]` → dùng bản không có cụm này cho tới khi có. Màn: `X1-NotFound404`, `DesktopNotFound404`.
Sửa khối `metadata` của `app/page.tsx` sau khi SHOP-1-06 xong (không sửa phần thân trang).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | — | Mở `/khong-co-trang-nay/` | Hiện header, EmptyState "Không tìm thấy trang này" + câu "Link có thể đã cũ hoặc gõ nhầm." + nút "Về trang chủ" (`/`) và "Xem hàng đang có" (`/shop/`), footer F1; `<title>` "Không tìm thấy trang — Cá Về"; có `<meta name="robots" content="noindex">` | D11 |
| AC2 | — | Đọc `<head>` của `/` và `/gioi-thieu/` | `title` ≤ 60 ký tự, `description` ≤ 160 ký tự, đúng chữ C8 (bỏ `[khu vực giao]` khi S-08 chưa có); không chứa ngoặc vuông | D11 |
| AC3 | — | Tìm "Lô mới", "miễn phí giao", "tươi sống" trong metadata | 0 kết quả | UI-RULES §6.4 |

---

# LÔ 2 · Danh mục, chi tiết, giỏ (BE ∥ FE)

**Xoá trong lô (G8):** `components/CatalogGrid.tsx`, `components/AddToCartControl.tsx`, phần giỏ trong `features/checkout/components/CheckoutScreen.tsx` (dòng giỏ, +/− theo 1 kg; được phép sửa file này **chỉ** để gỡ phần giỏ, S-09a),
khoá `sellable_qty` khỏi `catalog/items/shop_api.py`, `lib/types.ts`, `lib/mock.ts`; dòng phụ đề "tồn kho hiển thị là…" ở `app/shop/page.tsx`; câu lỗi lộ mã lô `inventory/batches/services.py` khi trả về Shop; e2e cũ đọc "Còn X kg".
**Phụ thuộc:** FE dựng mock theo contract SHOP-2-01/02 ngay; nối API thật khi BE xong.

## SHOP-2-01 · Catalog công khai trả mức tồn, đơn vị, tối thiểu, bước, slug nhóm · Must · be-dev
**Là** Lộc, **tôi muốn** API Shop chỉ cho biết món còn, sắp hết hay hết, **để** đối thủ không đọc được tồn kho theo giờ; **là** Khách, **tôi muốn** biết món bán theo kg hay combo và mua tối thiểu bao nhiêu.
Bối cảnh: BE-1; DOI-CHIEU L-04, L-06, L-20; V-01 (ngưỡng "Sắp hết" < 3 kg, < 3 combo); settings `SHOP_MIN_QTY_KG=1`, `SHOP_QTY_STEP_KG=0.5`, `SHOP_LOW_STOCK_KG=3`, `SHOP_LOW_STOCK_COMBO=3` (bất biến 7).
`ItemGroup.slug` duy nhất + data migration tự sinh từ tên (bỏ dấu, `-`, trùng thì thêm `-2`).

**Contract dự kiến**
```
GET /api/shop/catalog/  → 200
{ "groups": [{"slug":"muc","name":"Mực","item_count":4}],
  "items": [{ "item_code":"MUC-ONG","name":"Mực ống làm sạch","item_type":"SIMPLE","unit":"kg",
              "price":"278000","stock_level":"low","min_qty":"1","qty_step":"0.5",
              "group":{"slug":"muc","name":"Mực"},"short_note":"","image":{…}|null }] }
GET /api/shop/catalog/<item_code>/ → 200  (như trên + "description","spec","storage","origin" (chuỗi, có thể ""),
              "bundle_components":[{"item_code","name","qty_per_bundle":"0.5","unit":"kg"}])   // combo: unit "combo", min_qty "1", qty_step "1"
            → 404 {"code":"ITEM_NOT_FOUND","detail":"Không tìm thấy món này."}   // không tồn tại, ngưng bán, hoặc không có giá hiệu lực
```
`short_note`, `spec`, `storage`, `origin` trả `""` cho tới SHOP-2b-01 (giữ contract ổn định cho FE).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Món SIMPLE còn 5 kg / 2,5 kg / 0,9 kg / 0 kg | Gọi catalog | `stock_level` lần lượt `in` / `low` / `out` / `out` | BR-BH-23 |
| AC2 | Combo ráp được 5 / 2 / 0 bộ; combo có 1 thành phần hết | Gọi catalog | `in` / `low` / `out` / `out`; `unit:"combo"`, `min_qty:"1"`, `qty_step:"1"` | BR-DM-01, 06, BR-BH-23 |
| AC3 | Món còn 0,9 kg sổ, 0 kg đang giữ chỗ | Gọi catalog | `out` (dưới mức tối thiểu 1 kg) | BR-BH-23 (D Q4) |
| AC4 | Đổi `SHOP_LOW_STOCK_KG=5` trong test | Món còn 4 kg | `low` (đọc từ settings, không hard-code) | Bất biến 7 |
| AC5 | Nhóm "Cá thu" và "Cá Thu" (trùng sau bỏ dấu) | Chạy migration | Slug `ca-thu` và `ca-thu-2`, không lỗi unique; migration chạy ngược được | Bất biến 8 |
| AC6 | Món ngưng bán / mã không tồn tại | `GET /api/shop/catalog/<code>/` | `404 ITEM_NOT_FOUND`, không lộ lý do nội bộ | |
| AC7 (G1, G3) | Dữ liệu G1 | Gọi cả hai endpoint | Không có `sellable_qty` hay số kg tồn; không có trường giá vốn, mã lô; test nằm trong `catalog/items/tests/` | BR-BH-01, bất biến 1 |
| AC8 (quyền) | Khách chưa đăng nhập | Gọi `PATCH /api/shop/catalog/…` hoặc `POST` | `405`/`403`, không đổi dữ liệu | BR-PQ |

## SHOP-2-02 · Kiểm số lượng khi tạo đơn và lỗi hết hàng có cấu trúc · Must · be-dev
**Là** Lộc, **tôi muốn** máy chủ từ chối đơn dưới 1 kg, không đúng bước 0,5 kg hoặc combo lẻ, **để** không phải cân lẻ; **là** Khách, **tôi muốn** biết món nào hết lúc đặt mà không ai thấy số kg kho.
Bối cảnh: BE-3, BE-10; DOI-CHIEU L-03, L-05. Kiểm trong `create_order`, trước giữ chỗ, cùng giao dịch.

**Contract dự kiến** (`POST /api/shop/orders/`, body giữ như hiện tại)
```
400 {"code":"INVALID_QTY","detail":"Số lượng không hợp lệ.","lines":[{"item_code":"MUC-ONG","min_qty":"1","qty_step":"0.5"}]}
400 {"code":"OUT_OF_STOCK","detail":"Một số món vừa hết hàng.","lines":[{"item_code":"MUC-ONG","stock_level":"out"},{"item_code":"TOM-SU","stock_level":"short"}]}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Món kg | Đặt `1`, `1.5`, `2`, `10.5` kg | Tạo đơn bình thường | BR-BH-22 |
| AC2 (lỗi) | Món kg / combo | Đặt `0.5`, `0.3`, `1.25`, `0` kg; `1.5`, `0`, `-1` combo | `400 INVALID_QTY` liệt kê đúng dòng sai; **không** tạo `SalesOrder`, **không** tạo bản ghi giữ chỗ, **không** ghi `StockLedgerEntry` | BR-BH-22 |
| AC3 (lỗi) | Món còn 1,5 kg; khách đặt 2 kg; món khác hết | Tạo đơn | `400 OUT_OF_STOCK`, `lines` có `short` và `out`; chuỗi JSON **không** chứa số `1.5`, `0.5`, chữ "kg", mã lô | BR-BH-24, G1, G3 |
| AC4 (đồng thời) | Món còn đúng 2 kg; 2 request đặt 2 kg cùng lúc | Gửi song song | Đúng 1 đơn tạo, request kia `OUT_OF_STOCK`; tổng giữ chỗ không vượt tồn | BR-BH-01, 02 |
| AC5 | Đổi `SHOP_QTY_STEP_KG=1` trong test | Đặt 1,5 kg | `INVALID_QTY` (đọc settings) | Bất biến 7 |
| AC6 (log) | Request lỗi có SĐT trong body | Đọc log của test | Log không chứa SĐT, tên, địa chỉ, không có nguyên `request.data` | Bất biến 9 |

## SHOP-2-03 · Danh mục A2: lọc nhóm, sắp xếp, tìm, thêm theo bước · Must · fe-dev
**Là** Khách, **tôi muốn** lọc theo nhóm, sắp xếp theo giá, tìm theo tên và bấm "Thêm 1 kg" ngay trên thẻ, **để** gom đủ món nhanh.
Bối cảnh: COMPONENTS #3 (chip lọc), #4, #6, #12 `grid`, #13, #15, #16, #21, #22, #33–35, #42; UI-RULES §1, §7; Q-UX-6 (CartBar nằm trên BottomNav khi giỏ có món). FE lọc/sắp xếp/tìm tại chỗ trên catalog đã tải.
Route `/shop/?q=&group=<slug>&type=combo&sort=price_asc|price_desc`.
Màn: `Main`, `DesktopCategory`, `A4-Toast`, `DesktopToast`, `A5-NotFound`, `DesktopNotFound`, `A6-Offline`, `DesktopOffline`, `A0-Loading`, `DesktopLoading`, `B2-RemoveConfirm`, `DesktopRemoveConfirm`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Catalog mock theo contract SHOP-2-01 | Mở `/shop/?group=muc` | Chỉ món nhóm Mực; chip "Mực" (điện thoại) / mục cột lọc (máy tính) có `aria-current`; đếm món đúng | |
| AC2 | — | Chọn "Giá ↑" | Thứ tự giá tăng; món `out` **luôn ở cuối** dù sắp xếp kiểu nào | UI-RULES §1.4 |
| AC3 | Thẻ món kg còn hàng | Bấm "Thêm 1 kg" | Giỏ thêm 1 kg; nút đổi thành bộ tăng giảm hiện "1 kg", tiêu điểm dời vào bộ tăng giảm; Toast "Đã thêm vào giỏ" có link "Xem giỏ" (máy tính: MiniCart); `aria-live` báo | BR-BH-22 |
| AC4 | Bộ tăng giảm ở 1 kg | Bấm "+" rồi "+" | 1,5 kg rồi 2 kg (bước `qty_step` từ API) | BR-BH-22 |
| AC5 (G4) | Bộ tăng giảm ở 1 kg (nút trái là icon thùng rác) | Bấm nút trái | Mở Dialog B2 "Bỏ món này?"; "Bỏ" thì xoá khỏi giỏ, "Giữ lại" thì giữ 1 kg; không bao giờ hiện 0,5 kg | BR-BH-22, UI-RULES §1.2 |
| AC6 | Combo | Bấm "Thêm 1 combo", "+" | 1 combo, 2 combo; nút ghi "combo", không ghi "kg" | BR-DM-01 |
| AC7 | Món `low` / `out` | Nhìn thẻ | `low`: nhãn "Sắp hết" hổ phách trên ảnh. `out`: ảnh mờ, giá vẫn hiện, nút "Liên hệ chúng tôi" `tel:<hotline>` thay nút mua | BR-BH-23 |
| AC8 (rỗng) | `?q=xyz` không khớp / nhóm rỗng | Mở trang | EmptyState tìm không thấy (A5) với chip gợi ý nhóm và "Liên hệ chúng tôi" | |
| AC9 (lỗi) | Catalog lỗi mạng | Mở `/shop/` | ErrorState "Chưa tải được hàng" + "Thử lại"; header và bộ lọc vẫn hiện | UI-RULES §7 |
| AC10 | Trang chủ (SHOP-1-06) | Bấm ô nhóm | Đi tới `/shop/?group=<slug>` | |
| AC11 | Giỏ có món, 360 px | Mở `/shop/` | CartBar "N món · tổng tạm · Xem giỏ" nằm **trên** BottomNav; giỏ trống chỉ có BottomNav | Q-UX-6 |
| AC12 | Trang chủ ProductCard `rail` | Mở `/` sau khi nối API | Thẻ hiện nhãn tồn theo `stock_level`; món `out` không có ở hàng "Đang có hàng" | BR-BH-23 |

## SHOP-2-04 · Gợi ý khi gõ tìm (A9) · Should · fe-dev
**Là** Khách, **tôi muốn** thấy tối đa 5 món khớp ngay khi gõ, **để** khỏi gõ hết tên. Bối cảnh: D13; COMPONENTS #10 (combobox + listbox cả hai khổ). Tìm gần đây lưu `localStorage` khoá tiếng Anh (`shop_recent_searches_v1`).
Màn: `A8-SearchSuggest`, `DesktopSearchSuggest`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Catalog có "Mực ống làm sạch" | Gõ "muc" (không dấu) | Gợi ý có món này; tối đa 5 dòng; mỗi dòng tên + giá `/ kg` hoặc `/ combo`, **không** số kg tồn | D13, G1 |
| AC2 | Gợi ý đang mở | Phím ↓ ↓ Enter | Mở chi tiết món thứ hai; `aria-activedescendant` đổi theo; Esc đóng gợi ý, tiêu điểm ở ô tìm | |
| AC3 | Đã tìm "mực", "tôm" | Bấm vào ô tìm trống | "Tìm gần đây" hiện 2 từ; `localStorage` chỉ chứa các từ đã tìm, tối đa 5 | Bất biến 9 |
| AC4 (lỗi) | Gõ chuỗi giống SĐT `0900000001` | Nhấn Enter | Không lưu chuỗi này vào "Tìm gần đây" | Bất biến 9 |

## SHOP-2-05 · Chi tiết món A3, món hết A7, chi tiết combo A10 · Must · fe-dev
**Là** Khách, **tôi muốn** xem giá, chọn nhanh số kg, đọc quy cách, bảo quản, nguồn hàng, **để** biết mình mua gì.
Bối cảnh: COMPONENTS dòng A3/A7/A10; Q-UX-7 (câu A7 "Món này đang hết. Liên hệ để hỏi khi nào có hàng."); L-22 (một ảnh, ẩn bộ đếm); AUDIT §1.1 (link chia sẻ tới món đã ngưng bán).
Khối Quy cách / Bảo quản / Nguồn hàng / Mô tả chỉ hiện khi field có chữ (điền ở SHOP-2b-01). Màn: `Product`, `DesktopProduct`, `A7-OutOfStock`, `DesktopOutOfStock`, `A9-ComboDetail`, `DesktopComboDetail`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Món kg còn hàng | Mở `/shop/item/?code=MUC-ONG` | Tên, mã hàng, giá chi tiết 24/600 `accent-text`, nút chọn nhanh 1 / 1,5 / 2 / 3 kg, bộ tăng giảm bước 0,5, "Tạm tính" = giá × số kg, nút "Thêm vào giỏ"; bộ đếm ảnh ẩn khi 1 ảnh | BR-BH-22 |
| AC2 | `spec` rỗng, `storage` có chữ | Mở trang | Khối Quy cách ẩn hẳn, khối Bảo quản hiện | |
| AC3 | Món `out` | Mở trang | Nhãn "Hết hàng" (nền `--surface-3`, chữ `--ink-2`), ảnh mờ, Banner info câu Q-UX-7, nút "Liên hệ chúng tôi" (`tel:`) và "Nhắn Zalo" (ẩn khi site-info chưa có Zalo); không có nút mua | BR-BH-23 |
| AC4 | Combo | Mở trang combo | Đơn vị "combo", bảng thành phần (tên + kg mỗi combo), câu "Nếu một món hết, combo tạm ngưng", bộ tăng giảm bước 1 | BR-DM-01, 06 |
| AC5 (lỗi) | `?code=KHONG-CO` hoặc món ngưng bán (404) | Mở trang | Trạng thái "Không tìm thấy món này" + nút "Xem hàng đang có"; không màn trắng | AUDIT §1.1 |
| AC6 (G4) | Bộ tăng giảm ở 1 kg | Bấm "−" | Nút "−" tắt ở mức tối thiểu trên trang chi tiết (chưa vào giỏ nên không hỏi bỏ món); không xuống 0,5 kg | BR-BH-22 |

## SHOP-2-06 · Giỏ hàng `/shop/cart/` (B1–B4) · Must · fe-dev
**Là** Khách, **tôi muốn** một trang giỏ riêng, thấy giá đổi hoặc món vừa hết trước khi đặt, **để** không bất ngờ ở bước trả tiền.
Bối cảnh: COMPONENTS #19–23; UI-RULES §2.3 đã sửa theo BR-BH-30 (không dòng "Phí giao", câu "Đã gồm giao hàng…"); AUDIT câu 17 (tự loại hay chặn món hết: theo 02b; mặc định PO: món hết **không tính vào tổng và chặn "Đặt hàng"** tới khi khách bỏ món đó).
Giỏ tải lại catalog khi mở để so giá. Đổi type `CartLine` trong `CartContext` thành `CartEntry`.
Màn: `Cart`, `DesktopCart`, `B2-RemoveConfirm`, `DesktopRemoveConfirm`, `B3-CartChanged`, `DesktopCartChanged`, `B4-CartEmpty`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Giỏ 2 món | Mở `/shop/cart/` | CheckoutSteps bước 1, dòng món (ảnh, tên, đơn vị, bộ tăng giảm `sm`, thành tiền), Tạm tính, Tổng 24/600; dưới Tổng có đúng câu "Đã gồm giao hàng. Bạn trả một lần, không trả thêm khi nhận hàng."; **không** có chữ "Phí giao" | BR-BH-30 |
| AC2 (G4) | Dòng ở 1 kg | Bấm nút thùng rác | Dialog B2; "Bỏ" xoá dòng, badge giảm 1 | BR-BH-22 |
| AC3 (lỗi) | Giá trong giỏ 278000, catalog nay 290000 | Mở giỏ | Banner hổ phách B3; giá cũ gạch ngang, giá mới; tổng tính theo giá mới | UI-RULES §7 |
| AC4 (lỗi) | Một món trong giỏ nay `out` | Mở giỏ | Dòng món đánh dấu hết, không tính vào tổng; nút "Đặt hàng" báo "Bỏ món đã hết để đặt hàng" khi bấm; bỏ món xong thì đặt được | BR-BH-23 |
| AC5 (rỗng) | Giỏ trống | Mở `/shop/cart/` | EmptyState giỏ trống (B4) + nút "Xem hàng đang có" | |
| AC6 (lỗi) | Giỏ cũ trong `localStorage` có 0,3 kg hoặc 1,2 kg (từ Shop cũ) | Mở giỏ | Số lượng làm tròn **lên** mức hợp lệ gần nhất (1 kg, 1,5 kg) và Banner báo "Số lượng đã chỉnh theo mức bán"; không tự xoá món | BR-BH-22 |
| AC7 (lỗi) | Tải lại giá lỗi mạng | Mở giỏ | Banner "Chưa cập nhật được giá. Thử lại"; nút "Đặt hàng" vẫn bấm được (máy chủ kiểm lại giá lúc đặt) | AUDIT câu 17 |
| AC8 | Bấm "Đặt hàng" | — | Sang `/shop/checkout/` | |
| AC9 | Header, BottomNav, CartBar, MiniCart | Bấm giỏ | Đi tới `/shop/cart/` (thay đích tạm SHOP-1-03 AC8) | |
| AC10 (xoá) | — | `grep -rn "CatalogGrid\|AddToCartControl" frontend/` | 0 kết quả; `CheckoutScreen` không còn phần dòng giỏ | S-09a |

---

# LÔ 2b · Thông tin mặt hàng và slug nhóm trong ERP (BE + fe-dev ERP) · song song FE lô 2

**Xoá trong lô (G8):** không có code Shop cũ bị thay; ERP sửa tại chỗ. G4: N/A (không đổi số lượng). G6 áp cho màn ERP ở 360/1280 (không có file thiết kế ERP: so với `ItemForm` hiện có, ghi "không có thiết kế").

## SHOP-2b-01 · Chủ/Quản lý nhập Ghi chú ngắn, Quy cách, Bảo quản, Nguồn hàng, Mô tả · Must · cả hai (be-dev + fe-dev ERP)
**Là** Lộc, **tôi muốn** nhập thông tin món trong ERP, **để** trang chi tiết Shop không trống lúc go-live.
Bối cảnh: BE-2; UC-H; V-04 (cách rã đông viết trong Bảo quản, không thêm field); V-05 (ai đang có quyền sửa mặt hàng thì sửa được, không mở thêm quyền); BR-DM-25.
Migration `Item` thêm `short_note` (≤ 60 ký tự), `spec`, `storage`, `origin` (`blank=True`). ERP: `erp-console` màn `ItemForm` hiện có.
**Chặn một phần bởi S-18, S-19:** chỉ chặn **dữ liệu** Lộc nhập (câu sơ chế, số giờ rã đông), không chặn code.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Chủ đăng nhập ERP | Mở mặt hàng, nhập 5 trường, Lưu | Lưu thành công; `GET /api/shop/catalog/<code>/` trả đúng chữ; thẻ Shop hiện `short_note`; A3 hiện 4 khối | BR-DM-25 |
| AC2 (lỗi) | Nhập `Gọi 0900000001` vào Mô tả | Lưu | API trả 400 "Không ghi số điện thoại trong thông tin món."; ERP hiện lỗi dưới ô; không lưu | BR-DM-25, bất biến 9 |
| AC3 (lỗi) | Nhập chuỗi chứa giá (`250.000đ`, `250k`) hoặc mã lô định dạng hệ thống | Lưu | 400 nêu đúng lý do; không lưu | BR-DM-25, bất biến 1 |
| AC4 (lỗi) | `short_note` 61 ký tự | Lưu | 400, ERP đếm ký tự còn lại | |
| AC5 (quyền) | NV kho, NV giao, NV gọi xác nhận | Gọi `PATCH` API mặt hàng với 5 trường | 403, không đổi dữ liệu; nút sửa không hiện trên ERP | BR-PQ, V-05 |
| AC6 | Sửa thành công | Đọc AuditLog | Có dòng sửa mặt hàng như sửa hiện có (ai, lúc nào, trường nào) | BR-PQ-04 |
| AC7 (G3) | User không có `view_costprice` | Mở màn mặt hàng | Không thấy giá vốn (giữ nguyên hành vi hiện có, test không lùi) | Bất biến 1 |

## SHOP-2b-02 · Sửa slug nhóm hàng trong ERP · Should · cả hai (be-dev + fe-dev ERP)
**Là** Lộc, **tôi muốn** sửa đường dẫn nhóm (slug), **để** link nhóm dễ đọc. Bối cảnh: UC-H; `ItemGroupList`/`ItemGroupModal`. Đổi slug làm link cũ hỏng: chấp nhận ở V1 (🟢).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Nhóm "Cá thu" slug `ca-thu` | Đổi thành `ca-thu-dong` | Lưu; `/shop/?group=ca-thu-dong` lọc đúng; AuditLog ghi trước → sau | BR-PQ-04 |
| AC2 (lỗi) | Slug đã có ở nhóm khác / rỗng / có dấu, khoảng trắng, chữ hoa | Lưu | 400 nêu lý do; không lưu; ERP giữ chữ đã nhập | |
| AC3 (quyền) | User không có quyền sửa nhóm | Gọi API | 403 | BR-PQ |

---

# LÔ 3 + 4 · Đặt hàng, thanh toán, trang đơn = trang tra cứu (BE ∥ FE) · **merge vào `main` cùng một lần** (S-09c)

**Xoá trong lô (G8):** `features/checkout/components/CheckoutScreen.tsx` (lô 3), `PaymentPanel.tsx`, `OrderPaymentPanel.tsx`, `app/shop/orders/OrderLookup.tsx`, `components/CountdownTimer.tsx` (lô 4) ·
BE: `GET /api/shop/orders/<code>/?phone_last4=` và mọi chỗ dùng (`lib/api.ts`, `features/checkout/storage.ts` khoá `phone_last4`) · khối `refund{…}` và câu "sẽ được hoàn trong vòng N ngày" trong `customer_notices.py` ·
e2e cũ dùng 4 số cuối (`order_lookup_*.py`, `qa_sepay_checkout.py` phần tra đơn).
**Điểm dừng:** API key Google Maps (Duy + techlead); mọi việc đổi trạng thái đơn.

## SHOP-3-01 · Tạo đơn trả dòng món, mã tra đơn, chống trùng · Must · be-dev
**Là** Khách, **tôi muốn** bấm "Thử lại" khi mạng chập chờn mà không tạo hai đơn, và vào thẳng trang đơn sau khi đặt, **để** không bị giữ hàng gấp đôi hay mất màn thanh toán khi tải lại.
Bối cảnh: BE-4; BR-BH-25, 27; L-11; V-02 (mã tra đơn sống 30 ngày, tham số); V-06 (chuẩn hoá SĐT `+84`/`84`/khoảng trắng → 10 số bắt đầu 0, lưu dạng chuẩn); giữ đồng ý chính sách (`policy_version_id`, BR-BH-17).
Migration `SalesOrder.client_request_id` (UUID, unique, null).

**Contract dự kiến**
```
POST /api/shop/orders/
{ "client_request_id":"6f1c…uuid", "customer":{"name":"…","phone":"…"}, "delivery_address":"…",
  "items":[{"item_code":"MUC-ONG","qty":"1.5"}], "consent":{"accepted":true,"policy_version_id":12} }      // giữ tên field consent hiện có
→ 201 { "order_code":"SO261011-AB12CD","status":"BOOKED","total_amount":"417000",
        "booked_expires_at":"2026-10-11T03:30:00Z","server_now":"2026-10-11T03:00:00Z","hold_minutes":30,
        "lines":[{"item_code":"MUC-ONG","name":"Mực ống làm sạch","unit":"kg","qty":"1.5","amount":"417000"}],
        "lookup_token":"<ký bằng khoá máy chủ, chỉ chứa mã đơn + hạn>" }
→ 200 (cùng client_request_id đã tạo đơn) cùng body đơn cũ
→ 400 {"code":"VALIDATION","fields":{"phone":"Số điện thoại cần 10 chữ số, bắt đầu bằng 0"}} · 400 INVALID_QTY · 400 OUT_OF_STOCK (SHOP-2-02)
→ 409 POLICY_CHANGED (giữ) · 429 (giữ throttle) · trạng thái "Shop tạm chưa nhận đơn" (giữ GL-03-AC5)
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Giỏ hợp lệ | Tạo đơn | 201 đủ field trên; `booked_expires_at` = tạo + `SALES_ORDER_TTL_MINUTES`; `lines[].unit` là `kg`/`combo` | BR-BH-03, 25 |
| AC2 (trùng) | Đã tạo đơn với `client_request_id` X | Gửi lại đúng body với X (kể cả 2 request song song) | Đúng **1** `SalesOrder`, 1 bộ giữ chỗ; lần sau trả 200 cùng `order_code` | BR-BH-27 |
| AC3 | SĐT nhập `+84 900 000 001` | Tạo đơn | Lưu `0900000001`; tra đơn bằng `0900000001` hay `+84900000001` đều khớp (SHOP-3-02) | V-06 |
| AC4 (lỗi) | SĐT `12345`, địa chỉ rỗng, chưa tick đồng ý | Tạo đơn | 400 `VALIDATION` liệt kê đúng ô; không tạo đơn | BR-BH-09, 17 |
| AC5 (token) | `lookup_token` nhận được | Giải mã bằng công cụ base64 (không có khoá) | Không đọc ra tên, SĐT, địa chỉ; chỉ có mã đơn + hạn; sửa 1 ký tự thì máy chủ từ chối | BR-BH-25 |
| AC6 (G2) | Dữ liệu G2 | Đọc response 201 và log | Response **không** chứa tên, SĐT, địa chỉ khách; log chỉ có mã đơn | Bất biến 9 |

## SHOP-3-02 · Tra đơn bằng POST (mã + SĐT đầy đủ hoặc mã tra đơn), gỡ đường 4 số cuối · Must · be-dev
**Là** Khách, **tôi muốn** xem đơn bằng mã đơn và số điện thoại đã đặt, **để** theo dõi đơn; **là** Lộc, **tôi muốn** người lạ chỉ biết mã đơn thì không xem được.
Bối cảnh: BE-5; BR-BH-25, 26; analysis §6.1 (bảng trạng thái → màn); L-14, L-16. Không trả người nhận (decisions 10/10).

**Contract dự kiến**
```
POST /api/shop/orders/lookup/   {"order_code":"SO…","phone":"0900000001"}  |  {"order_code":"SO…","token":"…"}
→ 200 { "order_code","status","status_label","placed_at","paid_at","delivered_at","booked_expires_at","server_now","hold_minutes",
        "delivery":{"step":"preparing|delivering|delivered|failed|null","step_label"},
        "lines":[{"item_code","name","unit","qty","amount"}], "subtotal","discount":{"source":"promo|voucher|null","code":null,"amount":"0"},
        "total_amount", "confirmation":{…như hiện có…}, "cancel_notice":null|{…SHOP-4-05…}, "late_payment":false, "lookup_token":"<mới>" }
→ 404 {"code":"ORDER_NOT_FOUND","detail":"Không tìm thấy đơn khớp mã và số điện thoại."}   // sai mã, sai SĐT, sai token: cùng một câu
→ 401 {"code":"TOKEN_EXPIRED"}   → 429
GET /api/shop/orders/<code>/?phone_last4=…  → 404 (đã gỡ route)
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Đơn `SO…` SĐT `0900000001` | POST với SĐT đúng / với token đúng | 200 đủ field; trả `lookup_token` mới | BR-BH-25, 26 |
| AC2 (lỗi) | Mã đúng SĐT sai; mã sai SĐT đúng; token của đơn khác | POST | Cả ba trả **cùng** `404 ORDER_NOT_FOUND`, cùng câu, thời gian phản hồi không lộ ô nào sai | BR-BH-25 |
| AC3 (lỗi) | Token quá 30 ngày (giả lập giờ) | POST với token | `401 TOKEN_EXPIRED` | V-02 |
| AC4 (giới hạn) | Cùng IP gửi 11 lần sai trong 1 phút (theo throttle hiện có) / cùng mã đơn sai nhiều lần | POST | Lần vượt ngưỡng trả 429 | BR-BH-25 |
| AC5 (G2) | Dữ liệu G2 | POST đúng | JSON không chứa tên, SĐT (mọi dạng), địa chỉ, ghi chú nhân viên, mã lô, ngày nhập | BR-BH-26, bất biến 9 |
| AC6 | Đơn đã thanh toán, đã giao | POST | `placed_at`, `paid_at`, `delivered_at` là ISO UTC, khớp `created_at`, giao dịch MATCHED, `DeliveryNote.completed_at` | BR-BH-26 |
| AC7 (gỡ) | — | `GET /api/shop/orders/SO…/?phone_last4=0001` | 404; `grep -rn phone_last4 backend/ frontend/` ra 0 ngoài migration/doc | S-09b |
| AC8 (log) | Request tra đơn | Đọc log | Chỉ có mã đơn và SĐT đã che (`09xx xxx 001`) | Bất biến 9 |

## SHOP-3-03 · Form thông tin nhận hàng C1/C2, Shop tạm ngưng C7, chính sách đổi C9 · Must · fe-dev
**Là** Khách, **tôi muốn** một form ba ô và ô đồng ý, lỗi chỉ rõ chỗ cần sửa, **để** đặt hàng trong một lượt.
Bối cảnh: COMPONENTS #7, #9, #11, #20 `checkout`; Q-UX-4 (nút "Đặt hàng" luôn bấm được); câu đồng ý `05-phap-ly.md` §1.2a (không tick sẵn); V-06; L-17; BR-BH-30.
**Chặn một phần bởi S-08:** dòng công bố khu vực giao trên form chưa làm; phần còn lại làm ngay.
Màn: `Checkout`, `DesktopCheckout`, `C2-Invalid`, `DesktopInvalid`, `X2-ShopPaused`, `DesktopShopPaused`, `X4-PolicyChanged`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Giỏ hợp lệ | Mở `/shop/checkout/` | H4, CheckoutSteps bước 2, 3 ô (Họ và tên, Số điện thoại, Địa chỉ giao hàng là `<textarea>` 2 dòng + nút "Bản đồ"), ô đồng ý **chưa tick** với câu §1.2a và link chính sách mở tab mới, tóm tắt đơn, câu BR-BH-30; không có ô hoá đơn điện tử | BR-BH-09, 17, 30 |
| AC2 (lỗi) | Bỏ trống tên, SĐT `12345`, chưa tick | Bấm "Đặt hàng" | Khối "Còn 3 chỗ cần sửa" nhận tiêu điểm, mỗi dòng là link nhảy tới ô; ô lỗi viền đỏ, `aria-invalid="true"`, một dòng lỗi dưới ô ("Số điện thoại cần 10 chữ số, bắt đầu bằng 0", "Đánh dấu đồng ý ở trên để đặt hàng."); không gọi API | UI-RULES §7 |
| AC3 | SĐT `+84 900 000 001` | Rời ô | Không báo lỗi (FE chấp nhận như BE) | V-06 |
| AC4 (rỗng) | Giỏ trống | Mở thẳng `/shop/checkout/` | Chuyển về `/shop/cart/` | AUDIT §1.1 |
| AC5 (C7) | Chưa có chính sách quyền riêng tư đã đăng | Mở trang | Màn "Shop tạm ngưng nhận đơn" (X2), không có form | GL-03-AC5, V-09 |
| AC6 (C9) | API trả 409 `POLICY_CHANGED` | Bấm "Đặt hàng" | Dialog "Chính sách vừa cập nhật"; đóng thì ô đồng ý bỏ tick, 3 ô giữ nguyên chữ | BR-BH-17 |
| AC7 (G2) | Đã nhập 3 ô | Tải lại trang, đọc `localStorage`/`sessionStorage`/URL | Không lưu tên, SĐT, địa chỉ ở đâu; URL không có query chứa chúng | Bất biến 9 |

## SHOP-3-04 · Chọn địa chỉ bằng Google Maps (C1b, C1c, C5) · Must · fe-dev
**Là** Khách, **tôi muốn** tìm hoặc ghim nhà trên bản đồ rồi tự điền địa chỉ, **để** shipper tìm đúng nhà.
Bối cảnh: decisions 10/10; BR-BH-29; `05-phap-ly.md` §1.2b (dòng thông báo); S-07 (không nút "Vị trí của tôi"); L-10; COMPONENTS #8, #40. Biến `NEXT_PUBLIC_GOOGLE_MAPS_KEY` (tên chốt ở 02b). Không thêm thư viện loader nếu chưa hỏi.
**Điểm dừng:** cần API key. Thiếu key thì làm và kiểm theo AC5 trước.
Màn: `C1b-MapPicker`, `DesktopMapPicker`, `C1c-AddressFilled`, `C5-LocationDenied`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Mở `/shop/checkout/`, ghi log mạng | Chưa bấm "Bản đồ" | **0** request tới `maps.googleapis.com`, `maps.gstatic.com` | BR-BH-29 |
| AC2 | Mạng chậm | Bấm "Bản đồ" | Popup mở; dòng "Bản đồ do Google cung cấp. Chữ bạn gõ và vị trí bạn ghim sẽ được gửi tới Google. Không muốn dùng, bạn đóng lại và gõ địa chỉ trực tiếp." hiện **trước** khi script tải xong | BR-BH-29, §1.2b |
| AC3 | Tìm "1 Đường Thử", chọn kết quả, bấm xác nhận | — | Ô địa chỉ điền chuỗi địa chỉ (C1c, nền `--good-soft`), khách sửa tay được; request tạo đơn **chỉ** có chuỗi `delivery_address`, không có `lat`, `lng`, `place_id` | BR-BH-29 |
| AC4 | — | Tìm phần tử "Vị trí của tôi" / gọi `navigator.geolocation` trong mã nguồn | 0 kết quả | S-07 |
| AC5 (lỗi) | Không có key / script lỗi / mạng chặn Google | Bấm "Bản đồ" | Dialog C5 báo không mở được bản đồ, nút đưa tiêu điểm về ô địa chỉ để gõ tay; form vẫn đặt được | |
| AC6 (G5) | Popup bản đồ | Esc | Đóng, tiêu điểm về nút "Bản đồ", chữ đã có trong ô giữ nguyên | |

## SHOP-3-05 · Gửi đơn: hết hàng C3, lỗi mạng C4, quá nhanh C8, sang trang đơn · Must · fe-dev
**Là** Khách, **tôi muốn** biết món nào vừa hết khi bấm đặt và thử lại an toàn khi mất mạng, **để** không mất đơn và không bị giữ hàng gấp đôi.
Bối cảnh: COMPONENTS dòng C3, C4; UI-RULES §2c (giỏ chỉ xoá sau khi tạo đơn thành công); BR-BH-24, 27; V-02 (mã tra đơn ở `sessionStorage`).
Màn: `C3-SoldOut`, `DesktopModalSoldOut`, `C4-NetworkError`, `DesktopNetworkError`, `X3-TooManyRequests`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Form hợp lệ | Bấm "Đặt hàng" | Nút vào trạng thái đang gửi, bấm lần hai không gửi thêm; 201 thì giỏ xoá, `lookup_token` lưu `sessionStorage`, chuyển `/shop/orders/?code=SO…` (URL chỉ có mã đơn) | BR-BH-25, 27 |
| AC2 (C3) | API trả `OUT_OF_STOCK` với 1 dòng `out`, 1 dòng `short` | Bấm "Đặt hàng" | BottomSheet (máy tính Dialog) liệt kê 2 món: món hết ghi "đã hết", món thiếu ghi "không đủ hàng", **không** số kg; nút "Bỏ món đã hết" / "Quay lại giỏ"; không tạo đơn | BR-BH-24, G1 |
| AC3 (C4) | Request đi tới máy chủ nhưng mất phản hồi | Bấm "Thử lại" trong Dialog C4 | Gửi lại **cùng** `client_request_id`; nhận đơn cũ, không có đơn thứ hai; 3 ô giữ nguyên | BR-BH-27 |
| AC4 | Mở lại `/shop/checkout/` sau khi đã đặt xong | Đặt đơn mới | `client_request_id` mới (mỗi lần mở bước đặt hàng một mã) | BR-BH-27 |
| AC5 (C8) | API trả 429 | Bấm "Đặt hàng" | Dialog "Thao tác quá nhanh", thử lại sau vài giây; form giữ nguyên | |
| AC6 (G2) | Sau khi chuyển trang đơn | Đọc `sessionStorage`, `localStorage`, URL | Chỉ có mã đơn + `lookup_token`; không có SĐT | BR-BH-25 |

## SHOP-4-01 · Trang đơn = trang tra cứu: F1, F2, tải lại đúng màn · Must · fe-dev
**Là** Khách, **tôi muốn** mở `/shop/orders/?code=…` trên máy khác chỉ cần nhập SĐT, **để** xem đơn mà không lộ đơn cho người khác.
Bối cảnh: decisions 10/10 (một trang); UI-RULES §2c, §3.2; D9 (BottomNav ở tra cứu); analysis §6.1 (mọi dòng). Trạng thái server luôn thắng `result` trên URL.
Màn: `F1-Lookup`, `DesktopLookup`, `F2-LookupNotFound`, `E6-StatusRules`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Không có token, URL `?code=SO…` | Mở trang | F1 điền sẵn mã đơn, chỉ hỏi SĐT; BottomNav hiện, tab "Đơn hàng" có `aria-current` | D9 |
| AC2 | Có token trong `sessionStorage` | Mở `?code=SO…` hoặc F5 | Tự gọi lookup bằng token, hiện đúng màn theo bảng §6.1, không hỏi SĐT | BR-BH-25 |
| AC3 (F2) | Nhập SĐT sai | Bấm "Tra cứu" | Banner "Không tìm thấy đơn khớp mã và số điện thoại."; **không** ô nào có `aria-invalid`; SĐT không xuất hiện trên URL | UI-RULES §3.2 |
| AC4 (lỗi) | Token hết hạn (401) | Mở trang | Xoá token, về F1 điền sẵn mã | V-02 |
| AC5 (lỗi) | 429 / mất mạng | Tra cứu | Câu "Bạn thử lại sau ít phút." / "Chưa tải được đơn. Thử lại." + nút "Thử lại" | |
| AC6 | Đơn `PROCESSING`, URL có `result=cancel` | Mở trang | Hiện E1 (server thắng), không hiện D2 | UI-RULES §2c |
| AC7 (G2) | Đơn của dữ liệu G2 | Mở mọi trạng thái đơn | Trang không hiện tên, SĐT, địa chỉ người nhận; không có khối "Giao tới" | BR-BH-26 |

## SHOP-4-02 · Thanh toán D1, thanh toán lại D2, rời trang D6 · Must · fe-dev
**Là** Khách, **tôi muốn** thấy đồng hồ giữ hàng, tóm tắt đơn và một nút "Thanh toán", **để** trả tiền trước khi hết giờ.
Bối cảnh: COMPONENTS #24, #25, #28, #20 `payment`; decisions 10/10 (không ghi tên cổng); BR-BH-28 (không nút Huỷ đơn); BR-TT-12, 17; Q-UX-3 (số đồng hồ 40/600). Endpoint checkout cổng giữ nguyên (`POST /api/shop/orders/<code>/checkout/`).
Màn: `Payment`, `DesktopPayment`, `D2-PayCancelled`, `DesktopPayCancelled`, `D6-LeavePayment`, `DesktopLeavePayment`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Đơn `BOOKED` còn 25 phút | Mở trang | H4/F2; đồng hồ đếm theo `booked_expires_at − server_now` (lệch giờ máy khách 10 phút vẫn đúng ±2 s); dưới 5 phút đổi màu hổ phách; câu "30 phút" lấy từ `hold_minutes` | BR-BH-03 |
| AC2 | — | Đọc chữ trên trang | Phương thức "Chuyển khoản ngân hàng (quét mã QR)"; nút "Thanh toán"; **0** lần chữ "SePay"; Tổng lấy `total_amount` từ BE; có câu BR-BH-30 | decisions 10/10, BR-BH-30 |
| AC3 | — | Bấm "Thanh toán" | Gọi endpoint checkout, chuyển sang cổng | BR-TT-12 |
| AC4 (D2) | Quay về với `result=cancel` hoặc `error`, đơn còn hạn | Mở trang | Banner lỗi + nút "Thanh toán lại"; **không** có nút "Huỷ đơn" | BR-BH-28, BR-TT-17 |
| AC5 (D6) | Đơn đang giữ | Bấm logo hoặc nút quay lại | Dialog "Rời trang thanh toán?" hiện giờ còn lại; "Ở lại" đóng; "Rời trang" đi tiếp, đơn vẫn giữ tới hạn | |
| AC6 (truy cập) | Đồng hồ chạy | Bật trình đọc màn hình | Không đọc mỗi giây (vùng live chỉ báo mốc 5 phút và hết giờ) | COMPONENTS tự soát |

## SHOP-4-03 · Chờ xác nhận tiền D3 và hết giờ D4 · Must · fe-dev
**Là** Khách, **tôi muốn** biết tiền đã về chưa, và khi hết giờ thì đặt lại nhanh, **để** không phải gọi hỏi.
Bối cảnh: BR-TT-19 (5 phút, tham số); V-07, V-08 (D5 dùng D3 biến thể); BR-BH-04; analysis §6.1. Màn: `D3-PayPending`, `DesktopPayPending`, `D4-Expired`, `DesktopModalExpired`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Về `result=success`, đơn còn `BOOKED` | Mở trang | D3: tự gọi lookup mỗi 5 s; khi đơn thành `PROCESSING` thì chuyển E1 có banner "Thanh toán thành công" | BR-TT-19 |
| AC2 (lỗi) | Quá 5 phút vẫn `BOOKED` | Chờ | Câu đổi thành "Cá Về sẽ kiểm tra giao dịch và gọi cho bạn" + hotline; đồng hồ giữ hàng vẫn chạy; không đổi trạng thái đơn | BR-TT-19 |
| AC3 (D4 popup) | Đồng hồ về 0 khi đang xem, job chưa chạy | — | Dialog "Hết giờ giữ hàng"; trang gọi lại lookup cho tới khi server trả `AUTO_CANCELLED` | BR-BH-04 |
| AC4 (D4 trang) | Đơn `AUTO_CANCELLED`, không tiền về | Mở trang | "Hết giờ giữ hàng" + nút "Đặt lại đơn này" | |
| AC5 | Bấm "Đặt lại đơn này" | — | Giỏ dựng lại từ `lines` (mã hàng + số lượng, **không** mang mã giảm giá), sang `/shop/cart/`; món nay hết thì hiện như B3 | |

## SHOP-4-04 · Đơn sau thanh toán E1, đã giao E3, giao không thành công E4 · Must · fe-dev
**Là** Khách, **tôi muốn** thấy đơn đang ở bước nào kèm giờ, **để** biết khi nào hàng tới.
Bối cảnh: COMPONENTS #26, #27, #28, #29; BR-BH-26; AUDIT §1.3 (sao chép mã, nhắc lưu mã); GL-04 khối giờ gọi xác nhận giữ nguyên; `return_report_hours` từ site-info (SHOP-5-01; chưa có thì ẩn câu chứa số).
Màn: `Success`, `DesktopSuccess`, `E3-Delivered`, `E4-DeliveryFailed`, `DesktopOrderStates`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Đơn `PROCESSING`, vừa trả | Mở `?code=&result=success` | SuccessBanner (đóng được, nút đóng 44 px), nhãn trạng thái, dòng thời gian Đặt / Thanh toán / Chuẩn bị / Giao / Đã giao có giờ **GMT+7** dạng `14:05 · 11/10`, dòng món có đơn vị, tổng, khối giờ gọi xác nhận | BR-BH-26 |
| AC2 | — | Bấm "Sao chép mã đơn" | Clipboard có `SO…`; Toast "Đã sao chép" | |
| AC3 (E3) | Đơn `COMPLETED` | Mở trang | Mốc đã giao, nút "Gọi [hotline]", câu báo vấn đề trong N giờ (ẩn khi chưa có `return_report_hours`), nút "Mua lại" dựng giỏ từ `lines` | |
| AC4 (E4) | Phiếu giao `FAILED` | Mở trang | Banner warn "Giao không thành công. Cá Về sẽ gọi để hẹn lại."; dòng thời gian bước Giao có dấu lỗi | E-08 |
| AC5 (G1, G3) | — | Đọc chữ trang | Không số kg tồn, không mã lô, không chữ "hoàn tiền" | UI-RULES §2.6 |

## SHOP-4-05 · Thông báo đơn huỷ E2/E5 không lộ tiến độ hoàn tiền · Must · cả hai (be-dev + fe-dev)
**Là** Khách có đơn bị huỷ sau khi đã trả, **tôi muốn** biết lý do, số tiền phần bị huỷ và ai sẽ gọi mình, **để** yên tâm về tiền.
Bối cảnh: BR-HT-12 (thay CS-10); L-08, L-14; E-03 (tiền về sau khi tự huỷ, BR-TT-05/18), E-07, E-09, `UNREACHABLE_AUTO`; AUDIT câu 35 (nguồn số tiền phần bị huỷ: techlead).
**Chặn một phần bởi S-12:** câu bản A/B và hai thời hạn. Làm trước được: cấu trúc, bảng nhãn lý do, số tiền, hotline, link; câu đọc từ settings với giá trị tạm bản A khuyến nghị ("1 ngày làm việc"), Duy chốt thì chỉ đổi settings.
Màn: `E2-Cancelled`, `E5-PartialCancel`, `DesktopOrderStates`.

**Contract dự kiến** (khối `cancel_notice` trong lookup)
```
{ "reason_code":"OUT_OF_STOCK_AT_PICKING","reason_label":"Hàng không đạt khi soạn","scope":"full|partial",
  "cancelled_amount":"278000","message":"Cá Về sẽ gọi vào số điện thoại đặt hàng trong 1 ngày làm việc để trả lại 278.000đ.",
  "hotline":"…","policy_url":"/trang/?slug=doi-tra#xu-ly-tien" }        // không còn khoá "refund"
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Đơn đã trả, Chủ huỷ toàn phần lý do "hết hàng khi soạn" | Lookup | `cancel_notice` đúng contract; `reason_label` lấy từ **bảng nhãn cố định**; không có khoá `refund`, `deadline`, `refunded_at`, `status_label` của phiếu hoàn | BR-HT-12 |
| AC2 | Lý do `OTHER` có ghi chú tự do "gọi 0900000001" | Lookup | `reason_label` là câu chung; JSON **không** chứa ghi chú | BR-BH-26, G2 |
| AC3 (E5) | Huỷ một phần 1 trong 2 dòng | Lookup + mở trang | `scope:"partial"`, `cancelled_amount` = đúng tiền dòng bị huỷ; trang hiện phần còn giao và phần bị huỷ riêng | BR-HT-02 |
| AC4 (E-03) | Đơn `AUTO_CANCELLED` có tiền về muộn | Lookup + mở trang | `late_payment:true`; trang E2 biến thể "Hết giờ giữ hàng, tiền về sau" + câu "Cá Về sẽ gọi…" | BR-TT-05, 18 |
| AC5 | `UNREACHABLE_AUTO` | Mở trang | Nhãn "Không liên lạc được để xác nhận đơn" | |
| AC6 (chữ) | Mọi biến thể E2/E5 | Tìm chữ "hoàn" trên trang (trừ tên trang trong link chính sách) | 0 kết quả | UI-RULES §2.6 |
| AC7 (quyền) | — | Gọi lookup không có SĐT/token đúng | 404, không lộ `cancel_notice` | BR-BH-25 |

---

# LÔ 3b · Mã giảm giá (BE ∥ FE Shop ∥ FE ERP)

**Xoá trong lô (G8):** không có code cũ bị thay; dọn mock tạm `discount` trong `lib/mock.ts` nếu có. `PricingRule` hiện có **chỉ đọc**.
**Phụ thuộc:** sau 3+4 (cần `create_order` và trang đơn mới).

## SHOP-3b-01 · Model mã giảm giá, quyền `manage_voucher`, API ERP tạo/sửa/tắt/bật · Must · be-dev
**Là** Lộc, **tôi muốn** tạo mã có trần, lượt và hạn, chỉ sửa được theo hướng có lợi cho khách, **để** khuyến mại đúng luật và không lỗ ngoài ý muốn.
Bối cảnh: BE-11; BR-DM-17, 21, 22, 23; V-12; analysis §8.1, §8.4 (capability "Quản lý mã giảm giá" nhạy cảm, mặc định chỉ `owner`, Chủ uỷ ở màn Phân quyền). Migration model mã + ghi nhận dùng mã (không lưu SĐT/tên).

**Contract dự kiến** (ERP, cần `manage_voucher`)
```
GET   /api/catalog/vouchers/                     → [{id,code,name,kind:"AMOUNT|PERCENT",value,max_discount,min_order_amount,starts_at,ends_at,total_uses,used_count,held_count,is_active,disabled_reason}]
POST  /api/catalog/vouchers/                     {code,name,kind,value,max_discount,min_order_amount,starts_at,ends_at,total_uses,customer_terms} → 201
PATCH /api/catalog/vouchers/<id>/                → 200 | 400 {"code":"UNFAVORABLE_CHANGE","fields":[…]}
POST  /api/catalog/vouchers/<id>/disable/        {"reason":"BUDGET|INCIDENT|OTHER","note":"…"} → 200
POST  /api/catalog/vouchers/<id>/enable/         → 200 | 400 {"code":"EXPIRED|USED_UP"}
GET   /api/catalog/vouchers/<id>/redemptions/    → [{order_code,discount_amount,at,state:"held|used|released"}]
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Chủ | Tạo mã `CAVE10` PERCENT 10%, trần 50000, đơn tối thiểu 300000, 08:00 15/10 → 23:59 31/10 (giờ VN), 100 lượt | 201; `starts_at`/`ends_at` lưu UTC đúng; AuditLog "tạo mã" có giá trị | BR-DM-17, BR-PQ-04 |
| AC2 (lỗi) | Đã có `CAVE10` | Tạo `cave10` | 400 trùng mã (không phân biệt hoa thường) | BR-DM-17 |
| AC3 (lỗi) | — | Tạo PERCENT không có trần tiền / PERCENT 60% / kết thúc trước bắt đầu / mã chứa 10 chữ số liền (giống SĐT) | 400 nêu đúng lý do từng ca | BR-DM-17, 21 |
| AC4 | Mã đang chạy | PATCH gia hạn, tăng lượt, hạ đơn tối thiểu, tăng mức trong trần | 200; AuditLog trước → sau | BR-DM-22 |
| AC5 (lỗi) | Mã đang chạy, đã dùng 30 lượt | PATCH nâng đơn tối thiểu / giảm mức / rút hạn / tổng lượt 20 | 400 `UNFAVORABLE_CHANGE`, gợi ý "Tắt mã này và tạo mã mới" | BR-DM-22 |
| AC6 | Mã đang chạy | Tắt không chọn lý do / có lý do | 400 / 200 + AuditLog có lý do; mã **không** bị xoá (không có endpoint DELETE, `DELETE` trả 405) | BR-DM-22, bất biến 3 |
| AC7 | Mã đã tắt, còn hạn, còn lượt / hết hạn | Bật lại | 200 + AuditLog / 400 `EXPIRED` | V-12 |
| AC8 (quyền) | Quản lý chưa được uỷ, NV kho, NV giao, NV gọi xác nhận | Gọi từng endpoint | 403, không đổi dữ liệu (test mỗi Group, BR-PQ-13) | BR-DM-23 |
| AC9 (quyền) | Chủ uỷ `manage_voucher` cho Quản lý ở màn Phân quyền | Quản lý tạo mã | 201 | BR-DM-23 |
| AC10 (G2, G3) | — | Đọc JSON `redemptions` | Chỉ `order_code`, `discount_amount`, `at`, `state`; không tên, SĐT, địa chỉ, giá vốn, biên lãi | BR-DM-23 |

## SHOP-3b-02 · Màn ERP quản lý mã giảm giá · Must · fe-dev
**Là** Lộc, **tôi muốn** xem danh sách mã, tạo, tắt, bật và xem đơn đã dùng mã trong ERP, **để** tự chạy khuyến mại.
Bối cảnh: decisions 10/10 ("ERP có màn quản lý mã"); `00-product-brief.md` §2.3; đặt ở `erp-console/features/catalog/` cạnh `PricingRuleList`/`PricingRuleForm`; dùng contract SHOP-3b-01; giờ hiển thị GMT+7.
Không có file thiết kế Shop cho màn này: theo mẫu `PricingRuleList` hiện có.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Chủ | Mở màn | Bảng: mã, tên chương trình, kiểu, mức, trần, đơn tối thiểu, bắt đầu–kết thúc (GMT+7), đã dùng/tổng lượt, trạng thái | BR-DM-17 |
| AC2 | Chủ | Tạo mã đủ trường | Lưu, dòng mới trong bảng; chọn PERCENT thì ô trần tiền bắt buộc, ô mức chặn > 50 ngay ở form | BR-DM-21 |
| AC3 (lỗi) | API trả `UNFAVORABLE_CHANGE` | Lưu sửa | Hiện câu "Mã đang chạy chỉ sửa được theo hướng có lợi cho khách. Tắt mã này và tạo mã mới." | BR-DM-22 |
| AC4 | Bấm "Tắt mã" | — | Dialog bắt chọn lý do (Hết ngân sách / Sự cố / Khác); không có nút "Xoá" ở đâu | BR-DM-22, bất biến 3 |
| AC5 | Bấm "Xem lượt dùng" | — | Danh sách mã đơn, số tiền giảm, thời điểm, trạng thái lượt; **không** cột khách | BR-DM-23 |
| AC6 (quyền) | Quản lý chưa được uỷ / NV kho | Mở menu ERP | Không thấy mục "Mã giảm giá"; vào thẳng URL thì báo không có quyền | BR-DM-23 |

## SHOP-3b-03 · API kiểm mã công khai · Must · be-dev
**Là** Khách, **tôi muốn** biết ngay mã có dùng được với giỏ của mình không và vì sao, **để** quyết định đặt.
Bối cảnh: BR-DM-18, 24; V-03 (đơn tối thiểu so với tổng **trước** mọi giảm giá); V-11 (trả cả mức ưu đãi tự động để giỏ so được); throttle mới.

**Contract dự kiến**
```
POST /api/shop/vouchers/check/  {"code":"cave10","items":[{"item_code","qty"}]}
→ 200 {"valid":true,"code":"CAVE10","subtotal":"556000","auto_discount_amount":"0","discount_amount":"50000","total_after":"506000",
       "terms":{"min_order_amount":"300000","ends_at":"…","customer_terms":"…"}}
→ 200 {"valid":false,"reason_code":"INVALID|EXPIRED|MIN_ORDER|USED_UP|BETTER_PROMO","missing_amount":"44000"?,"auto_discount_amount":"60000"?}
→ 429
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | `CAVE10` như SHOP-3b-01, giỏ 556000 | Kiểm `cave10` | `valid:true`, giảm `50000` (10% = 55600, chạm trần 50000), `total_after` nguyên đồng | BR-DM-17, 21, BR-BH-15 |
| AC2 | Giỏ 256000 | Kiểm | `MIN_ORDER`, `missing_amount:"44000"` | BR-DM-24, V-03 |
| AC3 | Mã chưa tới giờ bắt đầu / đã hết hạn / đã tắt / không có | Kiểm | `INVALID` hoặc `EXPIRED` (chưa bắt đầu và không có → `INVALID`) | BR-DM-24 |
| AC4 | Đang giữ + đã dùng = tổng lượt | Kiểm | `USED_UP`; JSON không có số lượt còn lại | BR-DM-24 |
| AC5 | PricingRule đang áp giảm 60000 ≥ mã 50000 | Kiểm | `BETTER_PROMO`, `auto_discount_amount:"60000"`; hoà cũng `BETTER_PROMO` | BR-DM-18 |
| AC6 (trần) | Mã AMOUNT 400000, giỏ 600000 | Kiểm | Giảm 300000 (50% giỏ, tham số `VOUCHER_MAX_PERCENT`), tổng > 0 | BR-DM-21 |
| AC7 (giới hạn) | Cùng IP gửi vượt ngưỡng throttle | Kiểm | 429 | BR-DM-24 |
| AC8 (G2, G3) | — | Đọc JSON | Không danh sách mã khác, không dữ liệu đơn khác, không giá vốn, không số kg tồn | BR-DM-24 |

## SHOP-3b-04 · Áp mã khi tạo đơn: giữ lượt, đóng băng, phân bổ, nhả lượt · Must · be-dev
**Là** Lộc, **tôi muốn** lượt mã không bao giờ vượt tổng kể cả khi nhiều khách đặt cùng lúc, và lãi lỗ theo lô vẫn đúng, **để** kiểm soát được chi phí khuyến mại.
Bối cảnh: BR-DM-18, 19, 20, 21; BR-BH-04, 08, 15, 27; analysis §8.3 (phân bổ giảm vào `discount_amount` dòng như PricingRule, ghi nguồn giảm). Contract: `POST /api/shop/orders/` nhận `"voucher_code"`; lỗi
`400 {"code":"VOUCHER_INVALID","reason_code":"INVALID|EXPIRED|MIN_ORDER|USED_UP|BETTER_PROMO"}`; lookup trả `discount:{source:"voucher",code,amount}`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | `CAVE10` hợp lệ, giỏ 2 dòng 300000 + 256000 | Tạo đơn có mã | Đơn có mã + 50000 đóng băng; giảm phân bổ vào 2 dòng theo tỉ lệ giá trị (26978 + 23022, tổng đúng 50000, nguyên đồng), nguồn giảm "mã"; ghi nhận dùng mã trạng thái `held`; `total_amount` = 506000 | BR-DM-19, BR-BH-15 |
| AC2 (đồng thời) | Mã còn đúng 1 lượt | 5 request tạo đơn song song | Đúng 1 đơn có mã; 4 request còn lại `VOUCHER_INVALID USED_UP` và **không** tạo đơn | BR-DM-20 |
| AC3 (lỗi) | Mã bị tắt giữa lúc kiểm và lúc đặt | Tạo đơn | `VOUCHER_INVALID`, không tạo đơn, không giữ chỗ, không giữ lượt | BR-DM-19 |
| AC4 (trùng) | Gửi lại cùng `client_request_id` | Tạo đơn | Trả đơn cũ, không giữ thêm lượt | BR-BH-27 |
| AC5 | Đơn có mã được IPN xác nhận | — | Lượt thành `used` cùng giao dịch hoá đơn | BR-DM-20 |
| AC6 | Đơn có mã hết 30 phút | Chạy `cancel_expired_orders` **hai lần** | Lần 1: đơn `AUTO_CANCELLED`, lượt `released`, giữ chỗ nhả; lần 2: không đổi gì (idempotent) | BR-DM-20, BR-BH-04 |
| AC7 | Đơn có mã đã trả rồi bị huỷ toàn phần / một phần | Huỷ ở ERP | Lượt vẫn `used`, không trả lượt | BR-DM-20 |
| AC8 | Không có mã | Tạo đơn như cũ | PricingRule áp như trước (test hồi quy PricingRule không đổi) | BR-DM-08 |
| AC9 (giá vốn) | Đơn có mã đã giao | Báo cáo lãi lỗ theo lô | Doanh thu thuần dòng = thành tiền − phần giảm đã phân bổ; tổng lãi lỗ khớp tính tay; báo cáo kỳ cũ không đổi số | BR-BC, bất biến 1 |

## SHOP-3b-05 · Ô mã giảm giá ở giỏ (B5, B6, B7, DesktopVoucher) · Must · fe-dev
**Là** Khách, **tôi muốn** nhập mã ở giỏ, thấy ngay số tiền giảm và điều kiện, **để** biết chắc mình trả bao nhiêu.
Bối cảnh: COMPONENTS #48 VoucherField (props, câu chữ, trạng thái); UI-RULES §2b; BR-DM-24 (câu "Số lượt có hạn", "Không áp dụng cùng ưu đãi khác; Cá Về tự chọn mức có lợi hơn cho bạn"). FE không tự tính số tiền giảm.
Màn: `Cart`, `B5-VoucherSheet`, `B6-VoucherApplied`, `B7-VoucherError`, `DesktopCart`, `DesktopVoucher`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | 360 px, giỏ 556000 | Bấm "Nhập mã", gõ "cave 10", bấm "Áp dụng" | Ô tự in hoa, bỏ khoảng trắng (`CAVE10`); spinner trong nút; áp xong: chip `CAVE10` + nút "Bỏ mã" (`aria-label="Bỏ mã CAVE10"`), dòng "Giảm giá −50.000đ" màu good, Tổng mới, mức giảm, đơn tối thiểu, hạn dùng, "Số lượt có hạn", câu không cộng dồn; Toast "Đã áp mã CAVE10" | BR-DM-24 |
| AC2 | 1280 px | Mở giỏ | Ô nhập + nút "Áp dụng" nằm trong hộp tóm tắt | UI-RULES §2b.1 |
| AC3 (lỗi) | API trả lần lượt 5 `reason_code` và lỗi mạng | Áp mã | Đúng **một** câu mỗi ca theo COMPONENTS #48 mục 10 (MIN_ORDER kèm số tiền còn thiếu); `BETTER_PROMO` là thông tin màu `ink-2`, không đỏ; lỗi có `role="alert"` | BR-DM-24 |
| AC4 | Đã áp mã | Đổi số lượng làm giỏ dưới đơn tối thiểu | Gọi kiểm lại, hiện lỗi MIN_ORDER, Tổng về giá chưa giảm | BR-DM-24 |
| AC5 | Đã áp `CAVE10` | Áp mã khác hợp lệ | Mã mới thay mã cũ (tối đa 1 mã) | BR-DM-18 |
| AC6 (dữ liệu) | — | Đọc `localStorage` | Chỉ thêm mã đã nhập; không lưu số tiền giảm làm nguồn tính tổng | Bất biến 9 |
| AC7 (chữ) | — | Tìm số lượt còn lại trên trang | Không hiện | BR-DM-24 |

## SHOP-3b-06 · Mã hết hiệu lực lúc đặt (C6) và dòng giảm giá ở thanh toán, trang đơn · Must · fe-dev
**Là** Khách, **tôi muốn** được hỏi lại khi mã hết hiệu lực ngay lúc đặt, **để** không bị tính giá khác giá mình đã thấy.
Bối cảnh: UI-RULES §2b.4, §2b.5; BR-DM-19. Màn: `B8-VoucherInvalidAtOrder`, `Payment`, `DesktopPayment`, `Success`, `DesktopSuccess`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 (C6) | Giỏ có `CAVE10`, API tạo đơn trả `VOUCHER_INVALID` | Bấm "Đặt hàng" | Dialog "Mã CAVE10 không còn dùng được" / "Đơn sẽ tính theo giá chưa giảm." / nút "Đặt hàng không dùng mã" và "Quay lại giỏ"; **không** tự đặt | BR-DM-19 |
| AC2 | Ở Dialog C6 | Bấm "Đặt hàng không dùng mã" | Gửi lại **không** `voucher_code` với `client_request_id` mới; tạo đơn giá chưa giảm | BR-DM-19, BR-BH-27 |
| AC3 | Đơn có mã | Mở D1 và E1 | Dòng "Mã giảm giá (CAVE10) −50.000đ"; Tổng = `total_amount` từ BE | UI-RULES §2b.5 |
| AC4 | D4 "Đặt lại đơn này" của đơn có mã | Bấm | Giỏ dựng lại **không** có mã | BR-DM-20 |

---

# LÔ 5 · Trang phụ, mở rộng CMS, site-info (mkt-brand)

**Xoá trong lô (G8):** style cũ `app/trang/trang.module.css`, `app/bai-viet/bai-viet.module.css` (thay bằng style mới), `features/content/components/ItemCard.tsx` (thay bằng ProductCard `row`), nội dung tạm `features/home/content.ts` (chuyển CMS ở SHOP-5-03),
e2e `ra_soat_cms13_public.py`, `ra_soat_cms06_item_card.py` sửa theo giao diện mới. G4: N/A (trừ ProductCard `row` trong bài viết dùng lại AddToCart của lô 2: kiểm lại phần FE).
**Ghi chú lịch:** SHOP-5-01 và SHOP-5-02 không đụng file của be-dev/fe-dev, mkt-brand làm sớm được từ lúc lô 2 chạy.

## SHOP-5-01 · site-info thêm Zalo, giờ làm việc, nơi/ngày cấp GCN, số giờ báo vấn đề, link thông báo website · Must · mkt-brand
**Là** Khách, **tôi muốn** thấy đủ cách liên hệ và giấy phép của người bán, **để** tin cửa hàng. Bối cảnh: BR-ND-18 (sửa); BE-7 (bỏ `search_chips`); `05-phap-ly.md` §4; một nguồn cho hotline, Zalo, email, địa chỉ, giờ (analysis §9.2 điểm 4).
File: `backend/apps/content/site/services.py`, settings/env. **Chặn một phần bởi S-14:** link và ảnh biểu tượng thông báo để trống tới khi có chủ thể pháp lý + tên miền (code xong, giá trị rỗng).

**Contract dự kiến** (`GET` site-info hiện có, thêm)
`seller.zalo`, `seller.working_hours`, `seller.registration_issued_by`, `seller.registration_issued_on`, `seller.website_notice_url`, `seller.website_notice_image`, `policies.return_report_hours` — trống thì `null`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Env có `SELLER_ZALO`, `SELLER_WORKING_HOURS`, `SHOP_RETURN_REPORT_HOURS=24` | Gọi site-info | Trả đúng các khoá trên | BR-ND-18 |
| AC2 | Env trống | Gọi site-info | Các khoá là `null` (không `""`, không "Đang chờ"); footer, Liên hệ, A7 ẩn khối tương ứng | BR-ND-18 |
| AC3 | — | Đọc JSON | Không có `search_chips` | D |
| AC4 (G2) | — | Đọc JSON | Chỉ dữ liệu người bán; không dữ liệu khách | Bất biến 9 |
| AC5 | Hotline cấu hình | Kiểm `CONTENT_PHONE_ALLOWLIST` | Hotline nằm trong danh sách số được phép trong thân bài CMS | `06-marketing` F4 |

## SHOP-5-02 · Ba trang bắt buộc mới: Giao hàng, Thanh toán, Khiếu nại · Must · mkt-brand
**Là** Lộc, **tôi muốn** ba trang này được khoá như trang chính sách bắt buộc, **để** không ai lỡ tay gỡ khi đang bán.
Bối cảnh: BR-ND-20; `page_role` thêm `shipping`, `payment`, `complaints` (migration); màn Nội dung ERP hiện vai trò mới; lệnh nạp (SHOP-1-07) gắn vai trò cho `giao-hang`, `thanh-toan`, `khieu-nai`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Chạy migration + lệnh nạp | — | 3 trang có đúng `page_role`; hiện ở `footer-links` và footer F1 | BR-ND-20 |
| AC2 (lỗi) | Trang `shipping` đang là bản hiệu lực | Chủ bấm gỡ / huỷ đăng ở ERP | Bị từ chối với câu nêu lý do, như trang `privacy` hiện có | BR-ND-20 |
| AC3 | Sửa trang `payment` | Đăng bản mới | Có lịch sử phiên bản | BR-ND-20 |
| AC4 (quyền) | NV kho | Gọi API sửa trang | 403 | BR-PQ |

## SHOP-5-03 · Banner trang chủ, dải cam kết, dải chữ đầu trang lấy từ CMS · Should · mkt-brand
**Là** Lộc, **tôi muốn** tự đổi chữ banner và cam kết ở ERP, **để** chạy chương trình mà không cần dev.
Bối cảnh: decisions 10/10 (nội dung Lộc cần sửa lưu CMS); analysis §9.2 điểm 1 (model hoặc khối do techlead chọn ở 02b); `06-marketing.md` C5. Thay `features/home/content.ts` của SHOP-1-06.
**Chặn một phần bởi S-18** (câu "Cân đúng", cam kết 3) và khuyến mãi ở slide 2–3 phải qua `legal-vn`. Màn: `Home`, `DesktopHome`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Chủ sửa tiêu đề slide 1 ở ERP rồi đăng | Mở `/` | Banner hiện chữ mới (không build lại FE) | BR-ND-21 |
| AC2 | CMS chưa có khối banner | Mở `/` | Banner ẩn hẳn, trang không vỡ | |
| AC3 (lỗi) | Nhập chữ chứa SĐT ngoài danh sách được phép / chứa "miễn phí giao" | Lưu | Bị chặn hoặc cảnh báo theo luật lọc CMS hiện có | BR-ND, BR-BH-30 |
| AC4 (quyền) | NV kho | Gọi API sửa khối | 403 | BR-PQ |
| AC5 (G8) | — | `grep -rn "features/home/content" frontend/` | 0 kết quả | S-09a |

## SHOP-5-04 · Trang chính sách F3, Liên hệ F4, Cách mua F5 (`/trang/?slug=`) · Must · mkt-brand
**Là** Khách, **tôi muốn** đọc chính sách có mục lục, gọi hoặc nhắn Zalo từ trang Liên hệ, xem cách mua 5 bước, **để** hiểu trước khi trả tiền.
Bối cảnh: COMPONENTS #36 PolicyNav, dòng F3–F5; decisions 10/10 (Liên hệ, Cách mua là trang CMS); UI-RULES §3.3 (không form liên hệ); D12; `06-marketing.md` C7 (lỗi tải, 404, 410); số liệu 1 kg / 0,5 kg / 30 phút ở Cách mua lấy từ settings, không viết cứng.
Màn: `P1-Policy`, `DesktopPolicy`, `P2-Contact`, `DesktopContact`, `P3-HowToBuy`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Trang `doi-tra` đã đăng | Mở `/trang/?slug=doi-tra` | Breadcrumb, mục lục từ tiêu đề trong bài (link nhảy mục), khối "Các chính sách" từ `footer-links` có `aria-current` cho trang đang xem | BR-ND-19 |
| AC2 | — | Mở `/trang/?slug=lien-he` | Thẻ Hotline (`tel:`), Zalo, Email (`mailto:`), Địa chỉ, Giờ làm việc lấy từ site-info + thân bài CMS; **không** có form; thẻ thiếu dữ liệu thì ẩn | UI-RULES §3.3, BR-ND-18 |
| AC3 | — | Mở `/trang/?slug=cach-mua-hang` | 5 bước có số, hỏi đáp thu gọn bằng `<details>`; các số 1 kg / 0,5 kg / 30 phút khớp settings | BR-BH-22, 03 |
| AC4 (lỗi) | Slug không có / trang đã gỡ (410) / lỗi mạng | Mở trang | Ba trạng thái đúng chữ C7 với nút tương ứng | |
| AC5 | Trang chi tiết món (SHOP-2-05) | Mở | Dòng "Giao hàng:" và "Đổi trả:" lấy **tóm tắt** của trang `giao-hang`, `doi-tra`; trang chưa có tóm tắt thì ẩn dòng | `06-marketing` F5 |
| AC6 (chữ) | Mọi trang chính sách | Tìm "hoàn tiền" | Chỉ xuất hiện trong tên trang "Chính sách đổi trả và hoàn tiền" và trong thân trang chính sách đó | UI-RULES §2.6 |

## SHOP-5-05 · Góc bếp danh sách và bài viết (`/bai-viet/`) · Should · mkt-brand
**Là** Khách, **tôi muốn** đọc cách rã đông, công thức và bấm mua món trong bài, **để** nấu được món mình mua.
Bối cảnh: COMPONENTS dòng G1/G2; URL `/bai-viet/` và `?chuyen-muc=` giữ nguyên (CLAUDE.md); món liên quan dùng ProductCard `row` + AddToCart của lô 2. Màn: `G1-KitchenList`, `DesktopKitchenList`, `G2-KitchenArticle`, `DesktopKitchenArticle`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | 3 chuyên mục, 5 bài | Mở `/bai-viet/?chuyen-muc=ra-dong` | Chip lọc chuyên mục có `aria-current`; danh sách đúng chuyên mục; BottomNav hiện | |
| AC2 | Bài có khối món liên quan | Mở bài | ProductCard `row` có giá `/ kg` hoặc `/ combo`, nhãn tồn; món hết hiện "Liên hệ chúng tôi"; món ngưng bán thì ẩn thẻ | BR-BH-23 |
| AC3 (G4) | Bấm "Thêm 1 kg" trong bài | — | Như SHOP-2-03 AC3, AC5 | BR-BH-22 |
| AC4 (lỗi) | Bài không có / đã gỡ | Mở | Trạng thái C7 tương ứng | |

## SHOP-5-06 · Nạp nội dung đầy đủ: câu pháp lý, bài Góc bếp, tóm tắt trang · Must · mkt-brand
**Là** Duy, **tôi muốn** nội dung chính sách có câu `legal-vn` đã soạn và bài Góc bếp đủ, **để** gần đủ điều kiện go-live.
Bối cảnh: mở rộng lệnh SHOP-1-07; `05-phap-ly.md` §1.2c, §2, §3.2, §5, §6, §7; `06-marketing.md` C3, C4; BR-ND-21 (chính sách chỉ đăng production sau khi `legal-vn` duyệt; staging đăng luôn).
**Chặn một phần bởi:** S-12 (mục 4 trang Đổi trả: câu A/B, thời hạn) · S-16 (thời hạn khiếu nại) · S-08 (khu vực giao ở trang Giao hàng) · S-19 (số giờ rã đông trong bài) · S-23 (bài cá nục) · S-14 (tên chủ thể, MST ở Thông tin người bán).
Làm trước được: mọi câu đã có nguồn; chỗ chờ giữ dạng `[…]`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Staging | Chạy lệnh | 7 trang chính sách có câu legal đã soạn; trang `quyen-rieng-tu` có mục Google Maps và **tên SePay** (S-17), mục lưu trên trình duyệt | BR-BH-29, `05-phap-ly` §1.2c |
| AC2 | Trang `thanh-toan` | Đọc mục "Mã giảm giá" | Ghi rõ: mỗi đơn 1 mã, không cộng dồn, đơn đã trả rồi huỷ thì không trả lượt | BR-DM-18, 20 |
| AC3 | Câu hỏi nhóm B chưa trả lời | Đọc trang | Ô chờ còn ngoặc vuông, **không** có số tự bịa (khu vực, thời hạn, số giờ) | BR-ND-21 |
| AC4 (claim) | — | Tìm các chữ ở SHOP-1-07 AC5 | 0 kết quả | BR-ND-21 |
| AC5 | Production | Chạy lệnh | Mọi trang Nháp; trang chính sách có cờ "chờ legal-vn duyệt" trong ghi chú bản nháp | BR-ND-21 |

## SHOP-5-07 · Sửa câu "cá tươi" ở màn Nội dung ERP · Could · mkt-brand
**Là** Lộc, **tôi muốn** câu gợi ý ở màn Nội dung đúng là hàng cấp đông, **để** không lỡ viết sai. Bối cảnh: `06-marketing.md` F8; `erp-console/features/content/messages.ts:30`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Chưa có bài nào | Mở màn Nội dung ERP | Câu "Viết bài đầu tiên để giới thiệu hàng và công thức cho khách."; `grep -rn "cá tươi" erp-console/` = 0 | BR-DM-25 |

---

# LÔ 7 · QA toàn luồng

**Xoá trong lô (G8):** e2e còn sót trỏ route hoặc API cũ. Kiểm lại: `grep -rn "sellable_qty\|phone_last4\|CheckoutScreen\|OrderLookup\|SiteLegalFooter\|CatalogGrid" frontend/ backend/apps` = 0 (ngoài migration và doc).

## SHOP-7-01 · E2E toàn luồng 360 px và 1280 px, cả ca lỗi · Must · qa-tester
**Là** Duy, **tôi muốn** một lượt kiểm trọn trên staging với dữ liệu giả, **để** biết Shop đủ điều kiện lên production (lát 1) và phát mã (3b).
Bối cảnh: `HUONG-DAN-CODE.md` §6; luật QA đã siết (không PASS bằng đọc code, có ca ngoài đường thuận, `npm ci` sạch).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| AC1 | Staging, dữ liệu giả, sandbox cổng | Chạy luồng `/` → tìm → thêm 1,5 kg + 1 combo → giỏ → nhập mã → đặt → thanh toán sandbox → trang đơn | Mỗi bước có ảnh 360/1280 cạnh file thiết kế; đơn về `PROCESSING`, lượt mã `used` | Toàn bộ |
| AC2 | — | Chạy từng ca lỗi của bảng §6.1 và mọi màn lỗi A5–A7, B2–B4, B7, C2–C9, D2–D4, E2–E5, F2, 404 | Mỗi ca có ảnh + kết quả PASS/FAIL theo AC gốc | |
| AC3 | — | Quét JSON mọi endpoint `/api/shop/*`, `/api/public/*` | Đạt G1, G2, G3 | Bất biến 1, 9 |
| AC4 | — | Chạy G4, G5, G7 trên toàn Shop | Đạt | |
| AC5 | — | Lighthouse/axe các trang chính ở 360 px | 0 lỗi axe mức serious/critical | UI-RULES §8 |

---

## Bảng tổng

| Mã | Tiêu đề | Ưu tiên | Người làm | Lô | Phụ thuộc / chặn |
|---|---|---|---|---|---|
| SHOP-1-01 | Nền giao diện: token, font, giỏ ở gốc, badge số món | Must | fe-dev | 1 | — |
| SHOP-1-02 | Bộ component nền + trang xem thử | Must | fe-dev | 1 | 1-01 |
| SHOP-1-03 | Header H1–H4, logo, ô tìm | Must | fe-dev | 1 | 1-02 |
| SHOP-1-04 | BottomNav | Must | fe-dev | 1 | 1-02 |
| SHOP-1-05 | Footer F1/F2 gộp dải pháp lý | Must | fe-dev | 1 | 1-02 |
| SHOP-1-06 | Trang chủ `/` (A1) | Must | fe-dev | 1 | 1-03…05 · một phần **chặn bởi S-18** |
| SHOP-1-07 | Lệnh nạp nội dung CMS (bản đầu) | Must | mkt-brand | 1 | — · bài cá nục **chặn bởi S-23** |
| SHOP-1-08 | `/gioi-thieu/` dựng mới | Must | mkt-brand | 1 | 1-02, 1-03, 1-05, 1-07 · một phần **chặn bởi S-18, S-08** |
| SHOP-1-09 | 404 + SEO `/`, `/gioi-thieu/` | Should | mkt-brand | 1 | 1-06 · một phần **chặn bởi S-08** |
| SHOP-2-01 | Catalog: mức tồn, đơn vị, tối thiểu, bước, slug nhóm | Must | be-dev | 2 | (song song lô 1) |
| SHOP-2-02 | Kiểm số lượng + lỗi hết hàng có cấu trúc | Must | be-dev | 2 | 2-01 |
| SHOP-2-03 | Danh mục A2, thêm theo bước, toast | Must | fe-dev | 2 | lô 1; mock theo 2-01 |
| SHOP-2-04 | Gợi ý khi gõ tìm (A9) | Should | fe-dev | 2 | 2-03 |
| SHOP-2-05 | Chi tiết A3, A7, A10 | Must | fe-dev | 2 | 2-03 |
| SHOP-2-06 | Giỏ `/shop/cart/` B1–B4 | Must | fe-dev | 2 | 2-03 |
| SHOP-2b-01 | ERP nhập 5 trường thông tin món | Must | cả hai | 2b | 2-01 · dữ liệu **chặn bởi S-18, S-19** (không chặn code) |
| SHOP-2b-02 | ERP sửa slug nhóm | Should | cả hai | 2b | 2-01 |
| SHOP-3-01 | Tạo đơn trả dòng, mã tra đơn, chống trùng | Must | be-dev | 3+4 | 2-02 |
| SHOP-3-02 | Tra đơn POST, gỡ 4 số cuối | Must | be-dev | 3+4 | 3-01 |
| SHOP-3-03 | Form C1/C2, C7, C9 | Must | fe-dev | 3+4 | 2-06 · dòng khu vực **chặn bởi S-08** |
| SHOP-3-04 | Google Maps C1b/C1c/C5 | Must | fe-dev | 3+4 | 3-03 · **điểm dừng API key** |
| SHOP-3-05 | Gửi đơn C3/C4/C8, sang trang đơn | Must | fe-dev | 3+4 | 3-03; mock theo 3-01 |
| SHOP-4-01 | Trang đơn = tra cứu F1/F2 | Must | fe-dev | 3+4 | mock theo 3-02 |
| SHOP-4-02 | Thanh toán D1/D2/D6 | Must | fe-dev | 3+4 | 4-01 |
| SHOP-4-03 | Chờ tiền D3, hết giờ D4 | Must | fe-dev | 3+4 | 4-02 |
| SHOP-4-04 | Đơn E1/E3/E4 | Must | fe-dev | 3+4 | 4-01 |
| SHOP-4-05 | Đơn huỷ E2/E5 theo BR-HT-12 | Must | cả hai | 3+4 | 3-02 · câu chữ **chặn bởi S-12** (làm trước cấu trúc, câu ở settings) |
| SHOP-3b-01 | Model mã, quyền, API ERP | Must | be-dev | 3b | lô 3+4 merge |
| SHOP-3b-02 | Màn ERP mã giảm giá | Must | fe-dev | 3b | mock theo 3b-01 |
| SHOP-3b-03 | API kiểm mã công khai | Must | be-dev | 3b | 3b-01 |
| SHOP-3b-04 | Áp mã khi tạo đơn, giữ/nhả lượt | Must | be-dev | 3b | 3b-01, 3-01 |
| SHOP-3b-05 | Ô mã ở giỏ B5–B7 | Must | fe-dev | 3b | mock theo 3b-03 |
| SHOP-3b-06 | C6 + dòng giảm ở D1/E1 | Must | fe-dev | 3b | 3b-05; mock theo 3b-04 |
| SHOP-5-01 | site-info mở rộng | Must | mkt-brand | 5 (làm sớm được) | — · link thông báo **chặn bởi S-14** |
| SHOP-5-02 | `page_role` shipping/payment/complaints | Must | mkt-brand | 5 (làm sớm được) | 1-07 |
| SHOP-5-03 | Banner, cam kết từ CMS | Should | mkt-brand | 5 | 1-06 · **chặn bởi S-18** một phần |
| SHOP-5-04 | Chính sách F3, Liên hệ F4, Cách mua F5 | Must | mkt-brand | 5 | 5-01, 5-02 |
| SHOP-5-05 | Góc bếp G1/G2 | Should | mkt-brand | 5 | 2-03 |
| SHOP-5-06 | Nạp nội dung đầy đủ | Must | mkt-brand | 5 | 5-02 · **chặn bởi S-12, S-16, S-08, S-19, S-23, S-14** từng phần |
| SHOP-5-07 | Sửa câu "cá tươi" ERP | Could | mkt-brand | 5 | — |
| SHOP-7-01 | E2E toàn luồng 360/1280 | Must | qa-tester | 7 | tất cả |

Won't (V1): xem "Ngoài" ở mục Phạm vi.

## Thứ tự làm đề xuất
1. **Lô 1** fe-dev: 1-01 → 1-02 → (1-03 ∥ 1-04 ∥ 1-05) → 1-06. **Cùng lúc** mkt-brand: 1-07 → 1-08 → 1-09 (1-09 sau khi 1-06 xong). **Cùng lúc** be-dev: 2-01 → 2-02.
2. **Lô 2** fe-dev: 2-03 → 2-05 → 2-06 → 2-04 (nối API thật khi 2-01/02 xong). **Cùng lúc 2b:** be-dev 2b-01 → 2b-02, fe-dev ERP làm phần ERP sau khi xong FE lô 2 (hoặc xen nếu FE lô 2 chờ BE). mkt-brand làm sớm 5-01, 5-02.
3. **Lô 3+4** be-dev 3-01 → 3-02 → phần BE 4-05 ∥ fe-dev 3-03 → 3-05 → 3-04 → 4-01 → 4-02 → 4-03 → 4-04 → phần FE 4-05. **Merge một lần.**
4. **Lô 3b** be-dev 3b-01 → 3b-03 → 3b-04 ∥ fe-dev 3b-02 (ERP) → 3b-05 → 3b-06.
5. **Lô 5** mkt-brand 5-04 → 5-05 → 5-03 → 5-06 → 5-07.
6. **Lô 7** qa-tester.
Lý do: lô 1 không đổi contract nên chạy song song BE lô 2; lô 3+4 merge cùng lần để `main` luôn tra được đơn sau khi gỡ GET cũ; 3b cần `create_order` và trang đơn mới; lát 1 (1, 2, 2b, 3+4 + 5-01/02/04/06) là điều kiện production, 3b không chặn production (S-13).

## Rủi ro / phụ thuộc
- Contract dự kiến có thể đổi ở 02b: FE dựng mock theo file này, techlead chốt rồi PO sửa AC trong cùng ngày.
- SHOP-2-06 phải sửa `CheckoutScreen.tsx` để gỡ phần giỏ trong khi PLAN cũ ghi "không đụng `features/checkout/*`" ở lô 2: theo S-09a đã duyệt, chỉ gỡ phần giỏ.
- Giỏ cũ trong trình duyệt có số lượng lẻ (SHOP-2-06 AC6) và token tra đơn cũ không còn (`phone_last4`): chỉ ảnh hưởng staging vì production chưa chạy Shop.
- Google Maps cần key và billing (điểm dừng), CSP chưa có.
- Nhóm B chưa trả lời không chặn code; chặn dữ liệu/nội dung ở các story ghi "chặn bởi S-xx" và chặn go-live.

## Câu hỏi cho Duy
1. **Đưa lệnh nạp nội dung và `/gioi-thieu/` của mkt-brand vào lô 1** (PLAN cũ để nạp nội dung ở lô 5). Lý do: lô 1 xoá landing ở `/` và footer lấy link chính sách từ CMS, nên staging cần trang có sẵn. Đồng ý không?
2. **Trang xem thử `/ui-preview/`** chỉ bật khi build có cờ (production trả 404), để QA kiểm popup ở lô 1 trước khi có màn thật. Đồng ý không?
3. **Giỏ có món vừa hết (SHOP-2-06 AC4):** PO đặt mặc định là chặn "Đặt hàng" tới khi khách tự bỏ món hết (không tự loại). Techlead có thể đổi ở 02b; Duy chỉ cần phản đối nếu muốn tự loại.

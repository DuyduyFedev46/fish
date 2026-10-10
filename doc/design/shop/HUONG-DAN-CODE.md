# Hướng dẫn code giao diện Shop từ thiết kế

> Dành cho phiên Claude Code (`fe-dev`, `be-dev`, `qa-tester`) làm Shop mới. Đọc hết file này trước khi sửa dòng code nào.
> Quy trình lô theo `CLAUDE.md`, mục "Người hiện thực: đội Claude". Chia lô xem `PLAN.md`, prompt dán sẵn xem `PROMPT.md`.

## 0. Đọc trước (theo thứ tự)
1. `CLAUDE.md` và skill `caveve-domain`, nhất là bất biến 9 (dữ liệu cá nhân) và luật không rò giá vốn.
2. `doc/design/shop/UI-RULES.md`: luật bắt buộc của Shop. Rồi `COMPONENTS.md`: đặc tả từng component.
3. `doc/design/shop/DOI-CHIEU-CODE.md`: bảng màn → route → API → khoảng trống, kèm việc BE và các câu hỏi còn mở.
4. `DESIGN.md` (token), skill `nextjs-shop-patterns` (static export, `lib/api.ts` + mock), skill `caveve-ui`.
5. Màn thiết kế của lô đang làm, trong `doc/design/shop/screens/`. Mở bằng trình duyệt hoặc xem trên canvas: https://claude.ai/artifact/SPSQLR5rMEtuBFreYbK96J

## 1. Cách đọc file `.dc.html`
| Trong thiết kế | Khi code |
|---|---|
| `style="…"` inline với mã hex | Đổi sang token CSS (`var(--accent)`…) trong `globals.css`. **Không chép mã hex vào component.** |
| `{{tên}}` và `renderVals()` | Là dữ liệu hoặc state. Dữ liệu lấy từ `lib/api.ts`; state dùng `useState`. |
| `<sc-if value="…">` | Render có điều kiện. Mỗi nhánh là một trạng thái phải có. |
| `<sc-for list="…">` | `.map()` có `key`. |
| `onClick="{{x}}"` | Handler React. |
| Khung 390×H / 1280×H | Hai khổ của **cùng một trang**. Code một component responsive, không làm hai trang. |
| Màn `[Popup]` | Màn cha cộng lớp phủ. Code một component `Sheet`/`Dialog` responsive (xem mục 4). |
| `href="X.dc.html"` | Đổi sang route thật theo bảng mục 2 và cột "Đích" trong `HeaderFooter-*.dc.html`. |
| `[hotline]`, `[giá]`, `[Tên doanh nghiệp]` | Lấy từ `site-info` hoặc catalog. Không hard-code. |
| Ô "LOGO" | Chừa chỗ ảnh 28–40 px. Chưa có file thì dùng chữ "Cá Về". |

Font Inter tải qua `next/font`, không dùng `<link>` Google Fonts như trong file thiết kế.

## 2. Route (static export: `output: "export"`, `trailingSlash: true`)
Không dùng route động `[x]`, dùng query string thay thế.

| Màn thiết kế | Route | File |
|---|---|---|
| A1 / Desktop 1 Trang chủ | `/` | `app/page.tsx` (thay landing cũ) |
| Landing thương hiệu | `/gioi-thieu/` | **mới** `app/gioi-thieu/page.tsx` (chuyển nội dung landing cũ) |
| A2, A4–A9 Danh mục, tìm kiếm | `/shop/?q=&group=&type=combo&sort=` | `app/shop/page.tsx`, `components/CatalogGrid.tsx` |
| A3, A7, A10 Chi tiết, hết hàng, combo | `/shop/item/?code=` | `app/shop/item/page.tsx` |
| B1–B4 Giỏ | `/shop/cart/` | **mới** `app/shop/cart/page.tsx` |
| C1–C5 Đặt hàng | `/shop/checkout/` | `features/checkout/components/CheckoutScreen.tsx` (bỏ phần giỏ) |
| D1–D6, E1–E4, F1–F2 Thanh toán, đơn hàng, tra cứu | `/shop/orders/?code=&result=` | `app/shop/orders/*`, `features/checkout/components/OrderPaymentPanel.tsx` |
| Chính sách, cách mua | `/trang/?slug=` | `app/trang/*` |
| Liên hệ | `/trang/?slug=lien-he` (trang CMS, chốt 10/10) | `app/trang/*` |
| Góc bếp | `/bai-viet/` | `app/bai-viet/*` |

## 3. Component dùng chung (lô 1 dựng, các lô sau dùng lại)

> **Đặc tả đầy đủ từng component nằm ở `COMPONENTS.md`** (props TypeScript, trạng thái, token, a11y, câu chữ, file code) và bảng hình `screens/CMP-*.dc.html`. Khi `COMPONENTS.md` khác bảng dưới hay khác file màn, theo `COMPONENTS.md` (mục "Chỗ đã chuẩn hoá so với file màn").

| Component | Vai trò | Thiết kế mẫu |
|---|---|---|
| `ShopHeader` (`variant`: `home` \| `sticky` \| `sub` \| `checkout`) | Header H1–H4, máy tính 2 tầng hoặc rút gọn | `HeaderFooter-*.dc.html` |
| `BottomNav` | Thanh đáy điện thoại, `aria-current` | `HeaderFooter-Mobile.dc.html` (N1) |
| `ShopFooter` (`variant`: `full` \| `compact`) | Footer F1/F2, gộp `SiteLegalFooter` | `HeaderFooter-*.dc.html` |
| `ProductCard` | Ảnh, nhãn Sắp hết/Hết, tên, giá/đơn vị, nút thêm hoặc "Liên hệ chúng tôi" | `Main`, `DesktopCategory` |
| `QtyStepper` | `min`, `step`, `unit`; dưới min thì gọi `onRequestRemove` | `Product`, `Cart` |
| `StockBadge` | `in` \| `low` \| `out`, không bao giờ nhận số kg | `A7`, `Main` |
| `Sheet` / `Dialog` | Điện thoại là bottom sheet hoặc dialog, máy tính là hộp thoại giữa; giữ tiêu điểm, Esc | các màn `[Popup]` |
| `Toast` | `role="status"`, tự ẩn 3 s, có nút "Xem giỏ" | `A4`, `DesktopToast` |
| `AddressField` + `MapPicker` | textarea + nút Bản đồ; Maps nạp khi bấm; dòng thông báo Google hiện ngay khi mở; **không** nút "Vị trí của tôi"; trả về chuỗi địa chỉ (BR-BH-29) | `Checkout`, `C1b`, `C1c`, `C5` |
| `OrderTimeline` | Đã đặt → Đã thanh toán → Đang chuẩn bị → Đang giao → Đã giao; nhánh lỗi màu hổ phách | `Success`, `E3`, `E4` |
| `EmptyState`, `ErrorState`, `Skeleton` | Trạng thái bắt buộc (UI-RULES §7) | `A0`, `A5`, `A6` |
| `HoldCountdown` | Đếm ngược giữ hàng (dùng lại `CountdownTimer.tsx`) | `Payment`, `D2` |

`CartProvider` chuyển từ `app/shop/layout.tsx` lên `app/layout.tsx`, vì header ở mọi trang đều cần badge giỏ.

## 4. Responsive
- Viết mobile-first. Breakpoint `md` = 768 px (bố cục 2 cột, header 2 tầng), `lg` = 1024 px (lưới 4 cột).
- Container máy tính dùng `max-width: 1200px; margin: 0 auto; padding: 0 24px`.
- Popup: dưới `md` là bottom sheet hoặc dialog full-width; từ `md` trở lên là hộp thoại giữa màn rộng 440–480 px.
- Thanh mua dính đáy chỉ có trên điện thoại. Máy tính dùng hộp tóm tắt dính (`position: sticky`) ở cột phải.

## 5. Dữ liệu và API
- Mọi gọi API đi qua `lib/api.ts`. Mock ở `lib/mock.ts` phải khớp **đúng contract** trong `DOI-CHIEU-CODE.md` §4 (BE-1 … BE-7).
  FE có thể làm trước BE bằng mock, nhưng không tự đặt ra field mới.
- FE chỉ đọc `stock_level` (`in/low/out`). `sellable_qty` bị gỡ khỏi Shop API ngay ở lô 2 (chốt 10/10), không map tạm từ số kg. GET tra đơn `phone_last4` bị gỡ ở lô 3; tra đơn dùng POST (BR-BH-25).
- Tra đơn và trang đơn **không** đọc hay hiển thị tên, số điện thoại, địa chỉ người nhận.
- Không đưa số điện thoại khách vào URL. Lưu `lookup_token` (BE-4/BE-5) trong `sessionStorage` với khoá tiếng Anh.
- Lỗi hết hàng có cấu trúc (BE-3) thì mở popup C3. Không hiện chuỗi lỗi thô của server cho khách.

## 6. Kiểm chứng mỗi lô (điều phối viên tự chạy lại, không tin báo cáo)
```bash
cd frontend && npm ci && npx tsc --noEmit && npm run build && node scripts/check-no-mock.mjs
node scripts/test-format.mjs && node scripts/test-safe-href.mjs
# BE (khi lô có BE):
cd backend && .venv/bin/python manage.py test apps.catalog apps.sales && .venv/bin/python manage.py makemigrations --check --dry-run
python3 scripts/check_naming.py
# Không còn mã màu hex rời trong component Shop:
grep -rnE "#[0-9A-Fa-f]{6}" frontend/components frontend/app frontend/features | grep -v globals.css
```
- **QA bằng trình duyệt** (skill `e2e-playwright`): chụp từng màn của lô ở **360 px và 1280 px**, đặt cạnh file thiết kế tương ứng, lưu vào `doc/features/2026-10-06-shop-giao-dien-moi/shots/`.
  Kiểm cả happy case lẫn từng ca lỗi có trong thiết kế. Không chấm PASS bằng cách đọc code.
- Chạy `fixing-accessibility` trước QA.

## 7. Không được
- Không sửa `doc/decisions.md`, BR hay contract trong lô dev. Lệch thì ghi "Lệch thiết kế" vào `03-dev-notes.md` rồi dừng lô.
- Không hiện số kg tồn, ngày nhập lô, giá vốn, hay chữ "hoàn tiền" trên Shop (trừ tên trang "Chính sách đổi trả và hoàn tiền").
- Không có dòng "Phí giao"; dưới Tổng ghi câu "Đã gồm giao hàng…" (BR-BH-30). Không có chip "Tìm nhiều", không nút "Vị trí của tôi", không nút "Huỷ đơn" (chốt 10/10).
- Ô đồng ý chính sách **không bao giờ tick sẵn** (NĐ 356/2025, BR-BH-17). Mock và state khởi tạo `consent: false`.
- Mã BR của Shop mới: BR-DM-17…25, BR-BH-22…30, BR-TT-19, BR-HT-12, BR-ND-20, 21 (`doc/business-process-spec.md`). BR-BH-18…21 là đơn Hoàn tất, không dùng cho Shop.
- Không hiện dữ liệu cá nhân trên trang công khai. Không ghi dữ liệu cá nhân vào log hay test.
- Không thêm thư viện UI nặng. Dùng React và CSS hiện có. Muốn thêm thư viện (kể cả loader Google Maps) thì hỏi điều phối viên.
- Không thêm chữ chú thích ngoài thiết kế (UI-RULES §6).
- Không commit `.env` hay API key Google Maps. Key đi qua `NEXT_PUBLIC_GOOGLE_MAPS_KEY` lúc build, giới hạn theo referrer.

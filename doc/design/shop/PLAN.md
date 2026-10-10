# Giao việc: Shop giao diện mới (theo thiết kế 06/10/2026)
> Claude (điều phối) · 2026-10-06 · Trạng thái: **NHÁP**. Chờ Duy duyệt thiết kế và trả lời các câu mở bên dưới.
> **Cập nhật 2026-10-11:** Duy chốt 10/10 (tối) — `decisions.md` mục "2026-10-10 (tối)", `01-analysis.md` §11 nhóm A + V-01…V-12. Bảng lô dưới đây đã đổi theo S-09
> (xoá lô 6, thêm lô 2b, lô 3 và 4 merge cùng lần, gỡ `sellable_qty` ở lô 2, gỡ `phone_last4` ở lô 3, bỏ BE-6 và `search_chips`). Mã BR theo spec mới (BR-DM-17…25,
> BR-BH-22…30, BR-TT-19, BR-HT-12, BR-ND-20, 21); không dùng BR-BH-18/19 cho Shop (hai mã này đã thuộc đơn Hoàn tất). Không cấu trúc lại thư mục code.
> Người hiện thực: đội Claude (`fe-dev` ∥ `be-dev` → `techlead` review → `qa-tester`), theo quy trình lô trong `CLAUDE.md`.
> Hồ sơ tính năng: `doc/features/2026-10-06-shop-giao-dien-moi/` (lô 0 tạo `01-analysis.md`, `02-stories.md`, `02b-tech-design.md`;
> mỗi lô ghi `03-dev-notes.md`, `04-qa-report.md`, ảnh chụp vào `shots/`).
> Nhánh: tách từ `design/shop-ui`, mỗi lô một nhánh `shop/lo-<n>-<slug>`. QA APPROVED thì merge về `main` theo quy ước của Duy.

## Điều kiện đầu vào
- Duy duyệt bộ màn ở `doc/design/shop/` (canvas: https://claude.ai/artifact/SPSQLR5rMEtuBFreYbK96J).
- Duy trả lời các câu còn mở (chi tiết ở `DOI-CHIEU-CODE.md` §6):
  - **Q2** Tra đơn bằng số điện thoại đầy đủ cộng token (khuyến nghị), thay cho 4 số cuối?
  - **Q4** Đuôi lô dưới 1 kg xử lý thế nào?
  - **Q6** Khách trả phí giao bằng cách nào? Câu công bố phí giao trước khi đặt viết ra sao?
  - **Q7** Liên hệ và Cách mua làm trang tĩnh hay trang CMS?
  - **Q8** Ô "Lô mới về" bỏ, hay định nghĩa là lô mở bán trong N ngày?
  - **Q9** Giữ nút "Huỷ đơn" ở màn thanh toán chưa thành công (cần BE-6 và BR mới), hay bỏ?
  - Bước tăng sau 1 kg có đúng là 0,5 kg?
  - **Voucher**: mã có cộng dồn với ưu đãi tự động không (mặc định: không, lấy lợi hơn)? Ai tạo mã (Lộc trong ERP)? Mã công khai hay mã riêng từng khách (riêng từng khách = dữ liệu cá nhân)?
- Đã chốt trong thiết kế: Q1 bỏ khối "Giao tới"; Q3 không nêu số kg còn lại; Q5 giữ mã đơn `SO…`.
- **Đã trả lời 10/10** (decisions "2026-10-10 (tối)"): Q2 mã + SĐT đầy đủ (POST) hoặc mã tra đơn tạm, gỡ 4 số cuối (BR-BH-25) · Q4 tổng bán được dưới 1 kg thì
  "Hết hàng" (BR-BH-23) · Q6 trả một lần qua QR, chưa có phí ship, câu "Đã gồm giao hàng…" (BR-BH-30; khu vực giao Phan Thiết (D 11/10); ranh giới và đơn ngoài vùng tạm theo `doc/ops/hoi-loc.md` L1–L2) · Q7 trang CMS ·
  Q8 bỏ "Lô mới về" · Q9 bỏ nút "Huỷ đơn", không BE-6 (BR-BH-28) · bước 0,5 kg (BR-BH-22) · Voucher: không cộng dồn, lấy lợi hơn; mã công khai, giới hạn tổng lượt,
  1 mã/đơn; quyền `manage_voucher` chỉ Chủ, uỷ được (BR-DM-17…24).

## Lô
| ☐/☑ | Lô | Nội dung (màn thiết kế) | BE / FE | Được sửa | Không được đụng | Commit |
|---|---|---|---|---|---|---|
| ☐ | 0 | Ghi `decisions.md` và BR cho các chốt trong `README.md` (sửa BR-DM-01 combo, BR-DM-08, BR-BH-01 hiện tồn; thêm BR-DM-17…25 mã giảm giá + thông tin mặt hàng, BR-BH-22 tối thiểu 1 kg / bước 0,5, BR-BH-23…30, BR-TT-19, BR-HT-12, BR-ND-20, 21; không dùng BR-BH-18/19). `legal-vn`: chính sách quyền riêng tư (Google Maps), câu phí giao, câu báo huỷ. BA → PO → Tech Lead viết 01, 02, 02b | Điều phối + `legal-vn` + `ba-analyst` + `po-owner` + `techlead` | `doc/decisions.md`, `doc/business-process-spec.md`, `doc/ops/`, `doc/features/2026-10-06-shop-giao-dien-moi/` | code |
| ☐ | 1 | **Khung chung**: token (thêm `brand-deep` vào `DESIGN.md`) vào `globals.css`, Inter qua `next/font`, `CartProvider` lên root, `ShopHeader` H1–H4, `BottomNav`, `ShopFooter` F1/F2, `Sheet`/`Dialog`/`Toast`/`EmptyState`/`Skeleton`, `/gioi-thieu/` (chuyển landing), `/` trang chủ A1 dựng bằng catalog hiện có, 404 | FE | `frontend/app/layout.tsx`, `app/page.tsx`, **mới** `app/gioi-thieu/`, `app/shop/layout.tsx`, `app/globals.css`, `app/not-found.tsx`, `components/*` (header, footer, mới: BottomNav, ui/*), `features/site/components/SiteLegalFooter.tsx`, `DESIGN.md` (chỉ thêm token), `frontend/e2e/*` liên quan | `lib/api.ts`, `lib/types.ts`, `features/checkout/*`, `backend/` | — |
| ☐ | 2 | BE-1 (`stock_level`, `unit`, `min_qty`, `qty_step`, slug nhóm; **gỡ `sellable_qty`** khỏi Shop API), BE-3 (kiểm số lượng BR-BH-22, lỗi hết hàng có cấu trúc BR-BH-24), BE-10 ∥ FE: danh mục A2, A4–A9, chi tiết A3, A7, A10, giỏ B1–B4 (`/shop/cart/`, câu "Đã gồm giao hàng…" BR-BH-30), `QtyStepper`, `StockBadge`, badge số món. Xoá code Shop cũ phần mình thay | BE ∥ FE | Xem `DOI-CHIEU-CODE.md` §5 lô 2 | migration cũ, `payments/*`, `features/checkout/*` | — |
| ☐ | 2b | BE-2 (field mặt hàng: ghi chú ngắn, quy cách, bảo quản, nguồn hàng; trả `description`, BR-DM-25) ∥ FE ERP: màn nhập field mặt hàng mới và slug nhóm (kiểm trùng). Không có chip tìm kiếm | BE nhỏ ∥ FE ERP | `catalog/models/items.py` + migration, API ERP mặt hàng, `erp-console/features/items/*` | Shop | — |
| ☐ | 3 | BE-4 (`lines`, `lookup_token`, `client_request_id` BR-BH-27), BE-5 (tra đơn POST BR-BH-25; **gỡ GET `phone_last4`**) ∥ FE đặt hàng C1–C9: một ô địa chỉ, `MapPicker` (Maps nạp khi bấm, dòng thông báo Google ngay khi mở, **không** nút "Vị trí của tôi", BR-BH-29), ô đồng ý không tick sẵn (BR-BH-17), khối tóm tắt lỗi, popup hết hàng, chống bấm đúp. Không BE-6 (BR-BH-28). **Merge vào `main` cùng một lần với lô 4** | BE ∥ FE | Xem §5 lô 3 | `payments/checkout.py`, `adapter/` | — |
| ☐ | 3b | **Mã giảm giá**: BE-11 (model, kiểm mã, áp vào đơn, giữ/nhả lượt, quyền `manage_voucher`, ERP tạo/sửa/tắt mã, xem lượt dùng; BR-DM-17…24) ∥ FE B5–B8, DesktopVoucher, `VoucherField`, dòng giảm giá ở thanh toán/đơn. Quyết định đã có (10/10) | BE ∥ FE (+ ERP) | BE: app mới hoặc `catalog/pricing/*` + migration, `sales/orders/*`; FE: `app/shop/cart/*`, `components/cart/*`, `features/checkout/*`; ERP: màn mã giảm giá | `PricingRule` hiện có (chỉ đọc) | — |
| ☐ | 4 | Trang đơn = trang tra cứu: D1–D6, E1–E6, F1–F2 trên `/shop/orders/`, banner thành công, `OrderTimeline`, dựng lại giỏ từ `lines`, popup "Rời trang?", **không hiện người nhận** (BR-BH-26), D3 quá 5 phút (BR-TT-19), E2 theo BR-HT-12 (câu A/B, thời hạn bản A, tạm gọi trong 1 ngày làm việc, trả tiền trong 3 ngày làm việc (D 11/10: câu tạm, hỏi Lộc L6–L7 ở `doc/ops/hoi-loc.md`)), D2 không nút Huỷ. **Merge cùng lần với lô 3** | FE (+ BE `cancel_notice` theo BR-HT-12) | `app/shop/orders/*`, `features/checkout/components/OrderPaymentPanel.tsx`, `PaymentPanel.tsx` | `backend/` | — |
| ☐ | 5 | Trang phụ: chính sách (F3), liên hệ (F4), cách mua (F5), Góc bếp G1, G2; BE-7 `site-info` (Zalo, giờ làm việc, nơi/ngày cấp GCN, số giờ báo lỗi, link + ảnh biểu tượng thông báo website; trống thì ẩn, BR-ND-18; **không** `search_chips`); vai trò trang `shipping`, `payment`, `complaints` (BR-ND-20) | BE nhỏ ∥ FE | `app/trang/*`, `app/bai-viet/*`, `features/site/*`, `features/content/*`, nơi dựng `site-info` | `content/models` | — |
| — | ~~6~~ | **Xoá** (chốt 10/10, S-09): field mặt hàng và slug nhóm lên lô 2b; chip tìm kiếm bỏ | — | — | — | — |
| ☐ | 7 | QA E2E toàn luồng ở 360 px và 1280 px, so với từng màn thiết kế (cả ca lỗi). Kiểm lại không còn `phone_last4`, `sellable_qty` (đã gỡ ở lô 3, lô 2) | QA | `frontend/e2e/` | — | — |

Thứ tự: 0 → (1 ∥ BE của 2) → FE của 2 ∥ 2b → 3+4 → 3b → 5 → 7. Mỗi lô xoá code Shop cũ của phần mình thay, không để hai bản chạy song song.

> Danh sách file mới theo `COMPONENTS.md` (bảng "Component → Lô → file code", các dòng ⚠) được tính vào cột "Được sửa" của lô tương ứng, nhất là lô 1 (`components/ui/*`) và lô 2 (`components/catalog/*`, `components/cart/*`, `SearchSuggest`).

## Mỗi lô: điều kiện xong
- Lệnh kiểm chứng ở `HUONG-DAN-CODE.md` §6 chạy sạch. Điều phối viên tự chạy lại và dán output vào `03-dev-notes.md`.
- Ảnh chụp 360 px và 1280 px của **mọi màn trong lô**, cả ca lỗi, đặt cạnh file thiết kế.
- Test bắt buộc:
  - không hiện số kg tồn;
  - không rò dữ liệu cá nhân trên trang công khai;
  - không rò giá vốn;
  - tối thiểu 1 kg chặn ở cả FE lẫn BE;
  - popup giữ tiêu điểm, đóng bằng Esc.
- `techlead` review diff, rồi `qa-tester` APPROVED (`04-qa-report.md`). Sau đó commit tiếng Việt có mã lô và đánh ☑ ở bảng trên.

## Điểm dừng hỏi Duy
- Thiết kế không khớp code hoặc contract → ghi "Lệch thiết kế" trong `03-dev-notes.md`, dừng lô.
- Bất kỳ field dữ liệu cá nhân mới nào (ví dụ toạ độ bản đồ), mọi việc đổi trạng thái đơn, mọi việc đụng tiền hoặc giá vốn.
- Cần API key Google Maps hoặc thêm thư viện mới.

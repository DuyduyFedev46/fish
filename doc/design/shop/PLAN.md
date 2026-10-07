# Giao việc: Shop giao diện mới (theo thiết kế 06/10/2026)
> Claude (điều phối) · 2026-10-06 · Trạng thái: **NHÁP**. Chờ Duy duyệt thiết kế và trả lời các câu mở bên dưới.
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
- Đã chốt trong thiết kế: Q1 bỏ khối "Giao tới"; Q3 không nêu số kg còn lại; Q5 giữ mã đơn `SO…`.

## Lô
| ☐/☑ | Lô | Nội dung (màn thiết kế) | BE / FE | Được sửa | Không được đụng | Commit |
|---|---|---|---|---|---|---|
| ☐ | 0 | Ghi `decisions.md` và BR cho 9 chốt trong `README.md` (sửa BR-DM-01 combo, BR-BH-01 hiện tồn; thêm BR-BH-18 tối thiểu 1 kg / bước 0,5, BR-BH-19 nếu giữ Huỷ đơn). `legal-vn`: chính sách quyền riêng tư (Google Maps), câu phí giao, câu báo huỷ. BA → PO → Tech Lead viết 01, 02, 02b | Điều phối + `legal-vn` + `ba-analyst` + `po-owner` + `techlead` | `doc/decisions.md`, `doc/business-process-spec.md`, `doc/ops/`, `doc/features/2026-10-06-shop-giao-dien-moi/` | code |
| ☐ | 1 | **Khung chung**: token (thêm `brand-deep` vào `DESIGN.md`) vào `globals.css`, Inter qua `next/font`, `CartProvider` lên root, `ShopHeader` H1–H4, `BottomNav`, `ShopFooter` F1/F2, `Sheet`/`Dialog`/`Toast`/`EmptyState`/`Skeleton`, `/gioi-thieu/` (chuyển landing), `/` trang chủ A1 dựng bằng catalog hiện có, 404 | FE | `frontend/app/layout.tsx`, `app/page.tsx`, **mới** `app/gioi-thieu/`, `app/shop/layout.tsx`, `app/globals.css`, `app/not-found.tsx`, `components/*` (header, footer, mới: BottomNav, ui/*), `features/site/components/SiteLegalFooter.tsx`, `DESIGN.md` (chỉ thêm token), `frontend/e2e/*` liên quan | `lib/api.ts`, `lib/types.ts`, `features/checkout/*`, `backend/` | — |
| ☐ | 2 | BE-1 (`stock_level`, `unit`, `min_qty`, `qty_step`, slug nhóm), BE-3 (kiểm số lượng, lỗi hết hàng có cấu trúc), BE-10 ∥ FE: danh mục A2, A4–A9, chi tiết A3, A7, A10, giỏ B1–B4 (`/shop/cart/`), `QtyStepper`, `StockBadge`, badge số món | BE ∥ FE | Xem `DOI-CHIEU-CODE.md` §5 lô 2 | migration cũ, `payments/*`, `features/checkout/*` | — |
| ☐ | 3 | BE-4 (`lines`, `lookup_token`, `client_request_id`), BE-5 (tra đơn POST), BE-6 (nếu Q9 giữ) ∥ FE đặt hàng C1–C5: một ô địa chỉ, `MapPicker` (Maps nạp khi bấm), khối tóm tắt lỗi, popup hết hàng, chống bấm đúp | BE ∥ FE | Xem §5 lô 3 | `payments/checkout.py`, `adapter/` | — |
| ☐ | 4 | Trang đơn = trang tra cứu: D1–D6, E1–E4, F1–F2 trên `/shop/orders/`, banner thành công, `OrderTimeline`, dựng lại giỏ từ `lines`, popup "Rời trang?", **không hiện người nhận** | FE | `app/shop/orders/*`, `features/checkout/components/OrderPaymentPanel.tsx`, `PaymentPanel.tsx` | `backend/` | — |
| ☐ | 5 | Trang phụ: chính sách (F3), liên hệ (F4), cách mua (F5), Góc bếp G1, G2; BE-7 `site-info` (Zalo, số giờ báo lỗi) | BE nhỏ ∥ FE | `app/trang/*`, `app/bai-viet/*`, `features/site/*`, `features/content/*`, nơi dựng `site-info` | `content/models` | — |
| ☐ | 6 | ERP: màn nhập field mặt hàng mới (mô tả, quy cách, bảo quản, nguồn hàng), slug nhóm, chip tìm kiếm | BE nhỏ ∥ FE ERP | `erp-console/features/items/*` và API ERP mặt hàng | Shop | — |
| ☐ | 7 | QA E2E toàn luồng ở 360 px và 1280 px, so với từng màn thiết kế (cả ca lỗi). Gỡ GET `phone_last4` và `sellable_qty` khỏi Shop API | QA + BE | `frontend/e2e/`, `sales/orders/shop_api.py`, `catalog/items/shop_api.py` | — | — |

Thứ tự: 0 → (1 ∥ BE của 2) → FE của 2 → 3 → 4 → 5 → 6 → 7.

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

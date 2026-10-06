# Dev notes: Shop "Liên hệ" khi hết hàng

## FE
- `frontend/components/AddToCartControl.tsx`: khi hết hàng chỉ render link `a.btn.btn-secondary.btn-add` "Liên hệ" (`data-testid="contact-button"`), bỏ ô số lượng và nút thêm giỏ; lấy `seller.phone` qua `getSiteInfo()` (cache chung, chỉ gọi khi hết hàng).
- Lựa chọn khi không có SĐT: không có trang liên hệ riêng trong `/trang`, nên link tới `#thong-tin-nguoi-ban`, id mới đặt trên khối người bán trong `features/site/components/SiteLegalFooter.tsx`. Lệch nhỏ: nếu footer không hiện (cả site-info lẫn footer-links đều lỗi) thì bấm không có tác dụng.
- `components/CatalogGrid.tsx`, `app/shop/item/page.tsx`: nhãn "Tạm hết · liên hệ để đặt".
- `lib/mock.ts`: thêm "Cua hoàng đế" (CUA-HOANG-DE) `sellable_qty: 0`.
- Không đổi giỏ/checkout. `features/content/components/ItemCard.tsx` (nhúng bài viết) vẫn ghi "Tạm hết hàng", ngoài phạm vi.
- Ảnh: `shots/lien-he-360.png`, `shots/lien-he-1280.png` (mock; tel:0900000000, không cuộn ngang).
- Kiểm: `npx tsc --noEmit` sạch; `NEXT_PUBLIC_USE_MOCK=0 npm run build` xanh; frontend không có test đơn vị.

## Bổ sung (cùng ngày)
- Gom logic vào `frontend/components/ContactButton.tsx`, dùng ở `AddToCartControl` và `features/content/components/ItemCard.tsx` (thẻ trong bài viết: nhãn "Tạm hết · liên hệ để đặt", nút "Liên hệ" thay "Xem cửa hàng", cả khi không tìm thấy mặt hàng / API lỗi).
- Thứ tự: có SĐT thì `tel:`; không có SĐT mà footer đang hiện thì cuộn tới `#thong-tin-nguoi-ban`; footer không hiện (site-info lỗi) thì link thường về `/` nên không chết. Nhánh cuối chưa chụp được vì mock không giả lập site-info lỗi.
- Ảnh: `shots/lien-he-khong-sdt-360.png` (Shop, không SĐT, bấm không rời trang, cuộn tới footer), `shots/lien-he-bai-viet-360.png` (thẻ trong bài viết).
- Kiểm: tsc sạch, build mock=0 và mock=1 xanh.

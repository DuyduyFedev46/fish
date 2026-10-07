# QA — Shop "Liên hệ" thay "Hết hàng" · lần 1 · 06/10/2026
## Kết luận: APPROVED — 5/5 AC có bằng chứng chạy Playwright thật (build mock=1, 360 và 1280), không lỗi chặn.
## Tổng: 38 ca tự động (2 build × 2 cỡ màn) + 1 ca checkout · ✅ tất cả · ❌ 0 · ⏸ 1 (nhánh footer ẩn do site-info lỗi)

Môi trường: HEAD 1271c1b, `NEXT_PUBLIC_USE_MOCK=1 npm run build`, phục vụ `out/` bằng http.server, Playwright chromium. Dữ liệu giả của mock.
Tạm sửa mock cho 2 ca (bỏ SĐT; thẻ bài viết trỏ CUA-HOANG-DE), đã `git checkout` khôi phục; `out/`, `.next`, symlink node_modules, server đã dọn.

## Theo AC
| AC | Kết quả | Bằng chứng |
|---|---|---|
| 1 nút "Liên hệ" phụ, không disabled | ✅ | Danh sách + chi tiết: class `btn-secondary`, không `btn-primary`, không có chữ "Hết hàng" |
| 2 tel: / cuộn footer / không thêm giỏ | ✅ | Có SĐT: href `tel:0900000000`. Không SĐT: bấm không đổi URL, scrollY tăng, `#thong-tin-nguoi-ban` tồn tại. localStorage (giỏ) không đổi sau bấm |
| 3 nhãn "Tạm hết · liên hệ để đặt" | ✅ | Danh sách, chi tiết, thẻ bài viết (cả mặt hàng không có trong catalog và mặt hàng hết hàng thật) |
| 4 còn hàng không đổi | ✅ | CA-BASA-PHILE: có "Thêm vào giỏ" + ô số lượng, không có nút Liên hệ (danh sách + chi tiết) |
| 5 giỏ/checkout giữ nguyên | ✅ | Thêm CA-BASA-PHILE vào giỏ, /shop/checkout hiện giỏ, điền form giả, đặt hàng ra "Đặt hàng thành công" + mã đơn |

## Ngoại lệ & biên
- Hết hàng không có ô số lượng/nút thêm giỏ ở chi tiết và thẻ: ✅
- Không SĐT (mock phone rỗng): ✅ 38/38
- Không cuộn ngang ở 360 và 1280 (danh sách, chi tiết, bài viết): ✅
- Console 0 lỗi, 0 pageerror: ✅
- Footer ẩn khi site-info lỗi (href "/" không chết): ⏸ chưa chạy được vì mock không giả lập lỗi; chỉ xem logic
## Phân quyền / giá vốn / dữ liệu cá nhân
Chỉ FE Shop công khai. Không thêm field mới trong API; nút chỉ dùng `seller.phone` (SĐT đơn vị bán, đã công khai ở footer). Không giá vốn trong DOM thẻ. Giỏ chỉ giữ mã hàng và số lượng. Lưu ý đã có từ trước, chỉ ở mock: `cangcaloc_mock_orders_v2` lưu SĐT đơn mock vào localStorage; bản build thật không nạp mock.
## Hồi quy
Giỏ và checkout mock chạy được (xem AC 5).
## Lỗi (không chặn)
- L1 · Low: thẻ bài viết khi mặt hàng không có trong catalog hiện "Mặt hàng #CUA-HOANG-DE" (mã, không tên). Có từ trước, ngoài phạm vi.
## Lệnh đã chạy
`NEXT_PUBLIC_USE_MOCK=1 npm run build` (xanh, 2 lần có sửa mock tạm), script Playwright `qa_a.py` (scratchpad) cho 360/1280: 38/38 PASS; script checkout: đặt hàng thành công, console 0 lỗi. Ảnh (git-ignore): thư mục `shots/qa-*.png`.

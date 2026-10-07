# Prompt dán sẵn cho Claude Code: Shop giao diện mới

Mở một phiên Claude Code trên repo `DuyduyFedev46/fish`, nhánh `design/shop-ui` (hoặc nhánh lô tách từ đó), rồi dán prompt tương ứng.
Phiên chính là **điều phối viên**: nó giao việc cho `fe-dev` / `be-dev`, tự chạy lại lệnh kiểm chứng, rồi gọi `techlead` review và `qa-tester` kiểm.

---

## Prompt 0: khởi động (dán đầu tiên ở mỗi phiên mới)
```
Mình là Duy. Việc của phiên này là code giao diện Shop mới theo thiết kế trong doc/design/shop/.
Trước khi làm gì, đọc theo thứ tự: CLAUDE.md, doc/design/shop/README.md, UI-RULES.md, COMPONENTS.md, HUONG-DAN-CODE.md,
PLAN.md, DOI-CHIEU-CODE.md. Sau đó báo mình 5 dòng: lô nào đang ☐ tiếp theo, điều kiện đầu vào của lô đó đã đủ chưa,
và còn câu nào trong PLAN.md cần mình trả lời. Chưa sửa code.
```

## Prompt lô 0: ghi quyết định và hồ sơ
```
Chạy lô 0 trong doc/design/shop/PLAN.md.
- Ghi doc/decisions.md cho 9 chốt ở doc/design/shop/README.md, kèm câu trả lời Q2, Q4, Q6, Q7, Q8, Q9 mình đã chốt: <dán câu trả lời>.
- Sửa BR theo DOI-CHIEU-CODE.md §3.
- Gọi legal-vn soát chính sách quyền riêng tư (Google Maps), câu phí giao và câu báo huỷ đơn. Ghi vào doc/ops/.
- Chạy workflow feature, luồng ĐẦY ĐỦ, slug 2026-10-06-shop-giao-dien-moi: ba-analyst → po-owner → techlead (02b chốt contract BE-1…BE-7).
  Dừng ở mỗi điểm cần mình duyệt. Không sửa code.
```

## Prompt lô 1: khung chung (FE)
```
Chạy lô 1 trong doc/design/shop/PLAN.md theo quy trình lô của CLAUDE.md.
- Thiết kế: doc/design/shop/screens/HeaderFooter-Mobile.dc.html, HeaderFooter-Desktop.dc.html, Home.dc.html,
  DesktopHome.dc.html, Landing.dc.html, A0-Loading.dc.html, A4-Toast.dc.html, B2-RemoveConfirm.dc.html (mẫu Dialog),
  C3-SoldOut.dc.html (mẫu Sheet).
- Giao fe-dev, kèm danh sách file được sửa và không được đụng đúng như dòng lô 1.
- Dựng các component dùng chung đúng đặc tả COMPONENTS.md (props, trạng thái, token, a11y) và bảng hình screens/CMP-1…CMP-7: ShopHeader 4 biến thể, BottomNav, ShopFooter 2 biến thể,
  Sheet/Dialog, Toast, EmptyState, ErrorState, Skeleton. Chuyển CartProvider lên root. Chuyển landing sang /gioi-thieu/.
  Dựng trang chủ / bằng catalog hiện có.
- Chạy lệnh kiểm chứng ở HUONG-DAN-CODE.md §6. qa-tester chụp 360 px và 1280 px, so với từng file thiết kế ở trên.
- APPROVED thì commit "Shop lô 1: khung chung …", đánh ☑ trong PLAN.md.
```

## Prompt lô 2: danh mục, chi tiết, giỏ (BE ∥ FE)
```
Chạy lô 2 trong doc/design/shop/PLAN.md.
- be-dev làm BE-1, BE-3, BE-10 theo contract trong 02b-tech-design.md (gốc ở DOI-CHIEU-CODE.md §4), theo TDD.
  Có test: không trả sellable_qty dạng số cho màn mới, không lộ mã lô trong lỗi, combo chỉ nhận số nguyên, dưới 1 kg bị chặn.
- fe-dev (song song, mock theo đúng contract) dựng các màn:
  Main, A0, A4, A5, A6, A7, A8-SearchSuggest, A9-ComboDetail, Product, Cart, B2, B3, B4
  cùng các bản Desktop tương ứng: DesktopCategory, DesktopProduct, DesktopComboDetail, DesktopOutOfStock, DesktopNotFound,
  DesktopLoading, DesktopOffline, DesktopToast, DesktopSearchSuggest, DesktopCart, DesktopCartChanged, DesktopRemoveConfirm.
  Dựng QtyStepper (min 1, step 0,5, unit), StockBadge, badge giỏ đếm số món.
- Tự chạy lại lệnh kiểm chứng; techlead review; qa-tester kiểm từng màn ở 360 px và 1280 px, cả ca lỗi.
```

## Prompt lô 3: đặt hàng (BE ∥ FE)
```
Chạy lô 3 trong doc/design/shop/PLAN.md.
- be-dev: BE-4, BE-5 (và BE-6 nếu Q9 giữ nút Huỷ đơn). Có test: tra đơn sai không nói ô nào sai; response không có tên,
  số điện thoại, địa chỉ; client_request_id chống tạo đơn trùng.
- fe-dev dựng: Checkout, C1b-MapPicker, C1c-AddressFilled, C2-Invalid, C3-SoldOut, C4-NetworkError, C5-LocationDenied,
  DesktopCheckout, DesktopMapPicker, DesktopInvalid, DesktopModalSoldOut, DesktopNetworkError.
  Địa chỉ là MỘT textarea có nút Bản đồ. Script Google Maps chỉ nạp khi bấm, key lấy từ NEXT_PUBLIC_GOOGLE_MAPS_KEY,
  không lưu toạ độ. Chưa có key thì nút Bản đồ mở C5 và form vẫn nhập tay được.
- Kiểm chứng, review, QA như các lô trước.
```

## Prompt lô 4: thanh toán, trang đơn = trang tra cứu (FE)
```
Chạy lô 4 trong doc/design/shop/PLAN.md. fe-dev dựng trên /shop/orders/:
Payment, D2, D3, D4, D5, D6, Success, E2, E3, E4, F1-Lookup, F2-LookupNotFound,
cùng DesktopPayment, DesktopPayCancelled, DesktopPayPending, DesktopModalExpired, DesktopUnderpaid, DesktopLeavePayment,
DesktopSuccess, DesktopOrderStates, DesktopLookup.
Thanh toán xong (result=success, đã PAID) thì hiện banner "Thanh toán thành công" ngay trên trang đơn. KHÔNG hiện người nhận.
Không có chữ "hoàn tiền". Đơn huỷ đã trả tiền thì ghi "Cá Về sẽ gọi cho bạn".
Kiểm chứng, review, QA như các lô trước.
```

## Prompt lô 5: trang phụ
```
Chạy lô 5 trong doc/design/shop/PLAN.md: P1-Policy, P2-Contact, P3-HowToBuy, G1-KitchenList, G2-KitchenArticle
cùng DesktopPolicy, DesktopContact, DesktopKitchenList, DesktopKitchenArticle. be-dev làm BE-7 (site-info thêm Zalo,
số giờ báo lỗi). Nhóm "Chính sách" ở footer lấy từ CMS footer-links. Kiểm chứng, review, QA như các lô trước.
```

## Prompt lô 6 và 7
```
Chạy lô 6 trong doc/design/shop/PLAN.md: màn ERP để Lộc nhập field mặt hàng mới, slug nhóm và chip tìm kiếm.
Theo luật doc/design/erp/UI-RULES.md.
```
```
Chạy lô 7 trong doc/design/shop/PLAN.md: qa-tester chạy E2E toàn luồng ở 360 px và 1280 px, so với toàn bộ 72 màn
trong doc/design/shop/README.md (đánh dấu từng màn PASS/FAIL). Sau khi FE mới lên staging, be-dev gỡ GET phone_last4
và sellable_qty khỏi Shop API. Không deploy production khi mình chưa duyệt.
```

---

## Prompt sửa một màn lệch thiết kế (dùng bất cứ lúc nào)
```
Màn <route> đang lệch thiết kế doc/design/shop/screens/<file>.dc.html ở: <mô tả>.
Giao fe-dev sửa đúng theo thiết kế và UI-RULES.md. Chụp lại 360 px và 1280 px trước/sau. Không đổi file khác ngoài component của màn đó.
```

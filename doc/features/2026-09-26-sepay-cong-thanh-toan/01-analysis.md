# Cổng thanh toán SePay (VietQR là phương thức chính): phân tích nghiệp vụ
> BA · 2026-09-26 · Trạng thái: **ĐÃ DUYỆT** (2026-09-26, Duy)

## 1. Yêu cầu gốc
- "Đã đăng ký SePay … sepay đang hỏi ipn URL" và "anh muốn thanh toán VietQR là PTTT chính". Nguồn: Duy (PO), 2026-09-26, trong phiên này.
- Duy đã chốt trong phiên: (a) khoá hiện có là **SANDBOX**; (b) làm ngay theo quy trình rồi deploy adapter; (c) Duy tự khai IPN URL trên SePay.
- Duy chốt thêm 2026-09-26: "cứ VietQR mà triển, chưa cần ngân hàng gì đâu". Nghĩa là:
  - V1 **chỉ VietQR qua Cổng thanh toán SePay**; không bật thẻ hay NAPAS khác. Đã trả lời Q1.
  - **Không** dùng webhook biến động số dư cũ (`/webhook/sepay`, Apikey): giữ code nhưng không khai, không làm đường chính. Đã trả lời Q2.
- Duy **đã khai** IPN URL `https://cangca-adapter-675411800433.asia-southeast1.run.app/ipn/sepay` trên SePay. Nút gửi test hiện trả 404 vì adapter chưa deploy, đúng như dự kiến.
- Khoá sandbox đã có trên GCP Secret Manager: `cangca-sepay-sandbox-merchant-id` và `cangca-sepay-sandbox-secret-key`. BA không đọc giá trị.
- Nguồn kỹ thuật SePay: phiên này không có công cụ đọc web. Bản phân tích dựa trên **tóm tắt tài liệu SePay do điều phối viên cung cấp** (trang IPN và trang Sandbox của Cổng thanh toán). Tên field nào chưa chắc thì ghi "cần đối chiếu payload sandbox thật" (Q4).

## 2. Tóm tắt
**Khách mua trên Shop** cần **trả 100% tổng đơn bằng VietQR/chuyển khoản trên trang thanh toán của SePay**, rồi đơn **tự được xác nhận** khi SePay báo đã thu tiền. Mục đích: Lộc không phải dò sao kê từng đơn, và Shop bỏ được mã QR giả đang dùng.

## 3. Bối cảnh trong hệ thống

### 3.1 Quy trình, rule, quyết định
| Nội dung | Tham chiếu |
|---|---|
| Quy trình | **P-05** (Bán hàng Shop, §7.2 state machine, §7.4 thanh toán). Ảnh hưởng gián tiếp **P-07** (hoàn tiền) qua hàng chờ lệch |
| Rule đang có | BR-TT-01…07 (spec §7.4); BR-TT-08/09/10 (có trong code và dev-notes L7/L8, **chưa đưa vào spec**, nợ N-4); BR-TT-11 "100%, không cọc, không COD" (đề xuất ở `2026-09-26-hop-duy-loc`); BR-BH-03/04 (TTL 30', job idempotent); BR-BH-11 (lô chốt lúc tạo đơn) |
| Quyết định ràng buộc | decisions.md **2026-09-09**: "Thanh toán: VietQR qua SePay (chọn tạm)", "FastAPI là adapter mỏng, không đụng DB", "SePay không có API hoàn tiền, Lộc chuyển khoản tay", "Luồng bán hàng … xác nhận qua webhook (SePay → FastAPI → Django)". decisions.md **2026-09-26**: lô chốt một lần lúc tạo đơn. Quyết định của Duy (biên bản họp 2026-09-26): thanh toán 100%, không cọc |

### 3.2 Hiện trạng code (đã đọc)
- **Shop hiển thị QR giả.** `backend/apps/sales/orders/shop_api.py` có `_vietqr_stub`: trả chuỗi `VIETQR|ORDER:<mã>|AMOUNT:<tiền>`. Chuỗi này không phải chuẩn VietQR thật, ngân hàng không quét được. `frontend/components/QrCode.tsx` vẽ QR từ chuỗi đó. Shop có trang tra đơn `/shop/orders?code=<mã đơn>`, cần thêm 4 số cuối SĐT.
- **Adapter chỉ biết webhook NGÂN HÀNG của SePay** (`adapter/app/main.py`, route `POST /webhook/sepay`). Xác thực bằng header `Authorization: Apikey <secret>`, **so chuỗi thường, không so hằng-thời-gian**. Lấy `referenceCode` (mã FT… trên sao kê) làm `bank_txn_id`, rút mã đơn từ `code` hoặc regex trong nội dung chuyển khoản. `Settings` **bắt buộc** có `SEPAY_WEBHOOK_SECRET`. Adapter **chưa deploy**.
- **Lõi Django dùng lại được nguyên vẹn.** `POST /api/internal/payments/sepay-webhook/` (token `X-Internal-Token`, so hằng-thời-gian) nhận `{bank_txn_id, order_code, amount, received_at, raw}`. Hàm `_record_payment` xử lý:
  - chống trùng theo `bank_txn_id` (unique);
  - đơn đã huỷ/tự huỷ thì ghi `ORPHAN`;
  - đơn đã thanh toán thì ghi `OVERPAID`;
  - thiếu tiền thì ghi `UNDERPAID`;
  - đủ tiền thì xuất hoá đơn, trừ kho đúng lô đã giữ, chuyển đơn sang `PROCESSING`; phần thừa tách thành dòng `-THUA` riêng;
  - không tìm thấy đơn thì ghi `UNMATCHED`;
  - mọi dòng lệch vào hàng chờ Chủ (S12);
  - số tiền tối thiểu 1đ.
- **Nguồn giao dịch** `PaymentTransaction.Source` chỉ có `WEBHOOK` ("Webhook SePay") và `MANUAL`. `SalesInvoice.payment_method` mặc định `"VIETQR"`.
- **Tổng đơn có thể lẻ xu.** `orders/services.py` làm tròn tổng đơn tới **0,01đ** (`_q`). Số kg có 3 chữ số thập phân, nên ví dụ 0,125 kg × 150.500đ = 18.812,50đ. Cổng thanh toán nhận số tiền nguyên đồng (VND), vì vậy có thể lệch 0,5đ (xem R3, Q6).
- **Mã đơn** có dạng `SO<yymmdd>-<6 ký tự hex>`, ví dụ `SO260926-A1B2C3`.
- **TTL** đọc từ `SALES_ORDER_TTL_MINUTES` (mặc định 30). Hết TTL thì job `cancel_expired_orders` đổi đơn sang `AUTO_CANCELLED`.

### 3.3 Điểm mới so với thiết kế ban đầu
Thiết kế 2026-09-09 giả định mô hình **"Shop tự vẽ QR, SePay theo dõi biến động số dư, báo qua webhook ngân hàng"**. Duy đã đăng ký **Cổng thanh toán** SePay. Mô hình mới:
- Shop **chuyển khách sang trang thanh toán do SePay host**. Máy chủ ký các tham số: mã đơn, số tiền, URL quay về.
- SePay báo kết quả bằng **IPN** (`notification_type` = `ORDER_PAID` / `TRANSACTION_VOID`), xác thực bằng header `X-Secret-Key`.
- Payload IPN khác hẳn webhook ngân hàng. Adapter hiện tại **không nhận được IPN**, cần endpoint mới.

Kiến trúc lõi **không đổi**: bên thứ 3 → adapter → API nội bộ Django → `_record_payment` (BR-TT-02).

## 4. Tác nhân & quyền
| Tác nhân | Group | Làm được gì trong phạm vi này | Quyền Tầng 2 |
|---|---|---|---|
| Khách | (không phải User) | Đặt đơn, bấm "Thanh toán", trả trên trang SePay, quay về xem trạng thái đơn, thanh toán lại khi đơn còn Giữ chỗ | — |
| SePay (hệ thống ngoài) | — | Gửi IPN tới adapter. Chỉ được tin khi `X-Secret-Key` đúng | — |
| Hệ thống | `actor=None` | Ký tham số thanh toán, nhận IPN, xác nhận đơn, xuất hoá đơn, trừ kho | — |
| Chủ | `chu` | Xử lý hàng chờ lệch (S12) và phiếu hoàn (S13) như hiện nay. Xác nhận tay khi IPN không về (E-05) | `confirm_payment_manual`, `create_refund`, `confirm_refund` (không đổi) |
| Quản lý / NV kho / NV giao | — | Không đổi. NV kho nhận phiếu giao khi đơn đã thanh toán | — |
| Duy (vận hành) | — | Khai IPN URL trên dashboard SePay, cấu hình kiểu xác thực IPN, duyệt deploy | ngoài hệ thống |

Không phát sinh quyền mới. Không có màn hình ERP nào mới bắt buộc.

## 5. Use case

### UC-1 Khách thanh toán đơn qua cổng SePay (luồng chính)
- **Tiền điều kiện:** khách vừa tạo đơn thành công. Đơn ở trạng thái **Giữ chỗ** (`BOOKED`), còn TTL. Hệ thống đang cấu hình một môi trường cổng (sandbox hoặc production).
- **Luồng chính:**
  1. Shop hiện tóm tắt đơn: mã đơn, tổng tiền, đồng hồ đếm ngược TTL, nút **"Thanh toán bằng VietQR"**. Không còn hiện QR giả.
  2. Khách bấm nút. Máy chủ lập bộ tham số thanh toán cho đúng đơn này:
     - `order_invoice_number` = mã đơn;
     - `order_amount` = tổng đơn (nguyên đồng, xem Q6), `currency` = VND;
     - `success_url`, `error_url`, `cancel_url` trỏ về trang tra đơn trên Shop;
     - chữ ký HMAC-SHA256.
     Khoá bí mật **chỉ nằm trên máy chủ** (BR-TT-13).
  3. Trình duyệt chuyển khách sang trang SePay (`pay-sandbox.sepay.vn` hoặc `pay.sepay.vn`, theo cấu hình). Trang SePay hiện VietQR thật và thông tin chuyển khoản.
  4. Khách quét QR bằng app ngân hàng và chuyển tiền.
  5. SePay gửi IPN `ORDER_PAID` (`order.status = CAPTURED`) tới adapter.
  6. Adapter kiểm `X-Secret-Key`, đổi payload sang dạng nội bộ rồi gọi Django:
     - `bank_txn_id` = mã giao dịch SePay đã chuẩn hoá, theo Q4;
     - `order_code` = `order_invoice_number`;
     - `amount` = số tiền đã thu;
     - `received_at` = thời điểm giao dịch;
     - `raw` = payload gốc, **không kèm header bí mật**.
  7. Django chạy `_record_payment`: đủ tiền thì xuất hoá đơn, trừ kho đúng lô đã giữ (BR-BH-11), đơn chuyển `PROCESSING`, phiếu giao `PREPARING` được tạo (signal có sẵn).
  8. Adapter trả **HTTP 200** cho SePay.
  9. SePay đưa khách về `success_url`. Trang tra đơn hiện "Đã thanh toán, đang soạn hàng" **theo trạng thái trong hệ thống**, không theo việc khách được đưa về `success_url` (BR-TT-12).
- **Luồng thay thế:**
  - 9a. Khách về `success_url` **trước khi** IPN tới. Trang hiện "Đang chờ xác nhận thanh toán", tự tải lại trạng thái sau vài giây hoặc khi khách bấm. Không bao giờ hiện "đã thanh toán" chỉ vì khách được đưa về `success_url`.
  - 3a. Khách đóng trang SePay hoặc bấm huỷ (`cancel_url`). Shop hiện đơn **còn Giữ chỗ** kèm nút "Thanh toán lại", cho tới khi hết TTL (UC-2).
  - 3b. SePay báo lỗi (`error_url`). Xử lý như 3a, kèm câu "Thanh toán chưa thành công, bạn có thể thử lại".
  - 4a. Khách không dùng trang SePay mà tự chuyển khoản tay vào tài khoản của Lộc (ví dụ chụp lại số tài khoản). V1 chỉ nhận IPN (Duy chốt), nên khoản này **không tự khớp**. Đơn tự huỷ khi hết TTL, trừ khi Chủ xác nhận tay (S11, E-05). Rủi ro này chấp nhận được và cần ghi rõ trên Shop.
- **Ngoại lệ:**
  - E1. **IPN gửi lại** (SePay không nhận được 200, hoặc gửi trùng): chống trùng theo `bank_txn_id`, trả lại đúng kết quả đã ghi, không xuất hoá đơn lần hai (BR-TT-03).
  - E2. **IPN về sau khi đơn đã tự huỷ** (khách trả ở phút 31): ghi `ORPHAN`, vào hàng chờ Chủ, **không khôi phục đơn** (BR-TT-05). Thường dẫn tới hoàn tiền tay (P-07).
  - E3. **Số tiền IPN nhỏ hơn tổng đơn** (không nên xảy ra vì cổng thu đúng số đã ký, nhưng vẫn phải phòng): ghi `UNDERPAID`, vào hàng chờ (BR-TT-04).
  - E4. **Số tiền IPN lớn hơn tổng đơn**: đơn vẫn được xác nhận, phần thừa tách dòng `OVERPAID` (BR-TT-10, L8).
  - E5. **`order_invoice_number` không khớp đơn nào**: ghi `UNMATCHED`, vào hàng chờ, trả 200 để SePay ngừng gửi.
  - E6. **Sai hoặc thiếu `X-Secret-Key`**: từ chối, không ghi gì. Log chỉ ghi "sai khoá", **không ghi giá trị khoá**.
  - E7. **`currency` khác VND, hoặc `order.status` khác `CAPTURED` ở IPN `ORDER_PAID`**: không xác nhận đơn. Mặc định PA: ghi nhận để Chủ xem, không tự xác nhận (Q9).
  - E8. **Django lỗi tạm thời hoặc mất mạng**: adapter **không** trả 200, để SePay gửi lại. Tiền không được phép mất khỏi sổ.
  - E9. **Payload hỏng vĩnh viễn** (thiếu field bắt buộc): không được gây vòng gửi lại vô hạn, cũng không được lặng lẽ bỏ qua. Mặc định PA: trả mã khiến SePay ngừng gửi, và ghi log cảnh báo đủ thông tin để Chủ/Duy đối soát trên dashboard SePay.
  - E10. **IPN của môi trường sandbox tới hệ thống đang chạy dữ liệu thật**, hoặc ngược lại: xem R1 và Q3.
- **Hậu điều kiện:** mỗi khoản tiền SePay báo được ghi **đúng một** `PaymentTransaction`. Đơn chỉ chuyển sang đã thanh toán khi số tiền ghi nhận ≥ tổng đơn. Doanh thu ghi tại thời điểm xác nhận (BR-TT-06).

### UC-2 Khách thanh toán lại / quay lại sau
- **Tiền điều kiện:** đơn `BOOKED`, còn TTL. Khách đã huỷ trên trang SePay, đóng tab, hoặc mở lại từ trang tra đơn.
- **Luồng chính:**
  1. Khách mở trang tra đơn (mã đơn + 4 số cuối SĐT).
  2. Shop hiện "Chưa thanh toán, còn mm:ss" kèm nút "Thanh toán lại".
  3. Bấm nút thì máy chủ lập lại bộ tham số **cho cùng đơn, cùng số tiền** (tổng đơn đã đóng băng, BR-BH-08). Sau đó đi tiếp như UC-1 bước 3.
- **Ngoại lệ:**
  - E1. Hết TTL, hoặc đơn không còn `BOOKED`: máy chủ **từ chối lập tham số**, Shop báo "Đơn đã hết hạn giữ hàng, vui lòng đặt lại".
  - E2. Khách trả **hai lần** cho cùng đơn (hai tab): hai giao dịch khác mã. Giao dịch đầu xác nhận đơn, giao dịch sau ghi `OVERPAID` vào hàng chờ, Chủ hoàn (BR-TT-10). Không mất tiền trên sổ.
  - E3. SePay có thể không nhận lại cùng `order_invoice_number` lần hai. Nếu vậy cần một hậu tố lần thử, và hậu tố đó phải được bóc ra khi khớp đơn (Q5).
- **Hậu điều kiện:** không lập tham số thanh toán cho đơn đã hết hạn hoặc đã thanh toán.

### UC-3 Hết TTL trong khi khách đang ở trang SePay
- **Tiền điều kiện:** khách mở trang SePay lúc còn ít phút TTL.
- **Luồng chính:**
  1. Job TTL huỷ đơn (`AUTO_CANCELLED`), nhả giữ chỗ (BR-BH-03).
  2. Khách vẫn chuyển tiền, IPN về, đi theo UC-1 E2 (`ORPHAN`, hàng chờ, hoàn tay).
- **Giảm rủi ro:**
  - Shop hiện rõ thời hạn trước khi chuyển sang SePay.
  - Nếu SePay cho đặt thời hạn phiên thanh toán thì đặt ≤ thời gian TTL còn lại (Q7).
  - Không tự khôi phục đơn (BR-TT-05).
- **Hậu điều kiện:** tồn kho không bị bán vượt. Khoản tiền nằm trong hàng chờ, không mất khỏi sổ.

### UC-4 SePay báo huỷ giao dịch (`TRANSACTION_VOID`)
- **Tiền điều kiện:** SePay gửi IPN `TRANSACTION_VOID`. Loại này chủ yếu gặp ở thanh toán **thẻ**. V1 chỉ VietQR (Duy chốt), nên gần như không xảy ra.
- **Luồng chính (V1):**
  1. Adapter nhận, xác thực, trả 200.
  2. Hệ thống **không tự đổi trạng thái đơn, không tự nhập lại kho**. Lý do: chứng từ không xoá (BR-PQ-10); huỷ đơn đã thanh toán là quyền của Chủ (`cancel_paid_order`).
  3. Ghi **log cảnh báo** kèm mã đơn và mã giao dịch. Duy/Chủ đối chiếu trên dashboard SePay và xử lý tay theo P-07 nếu cần.
- **Hậu điều kiện:** không mất tín hiệu void. **Nếu sau này bật thẻ** thì phải nâng lên: ghi sự kiện gắn với đơn và hiện trong khối "Cần chú ý" của Chủ, để không có đơn nào được giao khi đã có void mà Chủ chưa xem.

### UC-5 Chủ xác nhận tay rồi IPN về muộn (chống ghi đôi)
> V1 chỉ có **một kênh tự động** (IPN), không bật webhook biến động số dư, nên **không cần** chống ghi đôi giữa hai kênh tự động. **Nếu sau này bật lại webhook ngân hàng song song** thì bắt buộc làm thêm việc chống trùng giữa hai kênh (BR-TT-15). UC này chỉ còn cặp **xác nhận tay (S11) + IPN**, vì S11 vẫn là đường dự phòng (E-05).

- **Tiền điều kiện:** IPN chậm hoặc lỗi. Chủ xem sao kê, bấm xác nhận tay (S11) với mã FT… của ngân hàng.
- **Luồng chính:**
  1. Đơn đã `PROCESSING` qua giao dịch `MANUAL` (`bank_txn_id` = FT…).
  2. IPN tới với mã giao dịch **của SePay**, khác mã FT…. Lõi hiện tại coi đây là khoản thứ hai và ghi `OVERPAID`.
  3. **Rủi ro:** Chủ thấy "chuyển thừa" và hoàn một khoản **không có thật**, tức tiền rời túi.
- **Yêu cầu (BR-TT-15, PA):**
  - Nếu IPN có mã tham chiếu ngân hàng (FT…) thì dùng mã đó làm khoá chống trùng. Khi đó trùng với mã Chủ đã gõ và lõi tự bỏ qua (Q4).
  - Nếu IPN không có mã FT…: dòng `OVERPAID` sinh từ IPN cho một đơn đã được xác nhận **tay** với **cùng số tiền** phải được **gắn nhãn "nghi trùng xác nhận tay, đối chiếu sao kê trước khi hoàn"**. Không được để nó trông như tiền thừa thông thường.
- **Hậu điều kiện:** không có phiếu hoàn nào được lập cho khoản bị ghi đôi mà không có cảnh báo.

### UC-6 Vận hành: deploy adapter và khai IPN URL (sandbox)
- **Tiền điều kiện:** Duy duyệt deploy. Các secret có trên Secret Manager. `cangca-api` đã có `INTERNAL_SERVICE_TOKEN` (cần kiểm, mục 7.3).
- **Luồng chính:**
  1. Deploy Cloud Run `cangca-adapter` (region `asia-southeast1`), mở công khai vì SePay phải gọi được.
  2. Gắn các cấu hình vào adapter qua Secret Manager và biến môi trường, **không hard-code**:
     - URL Django nội bộ (`cangca-api`);
     - token nội bộ;
     - khoá xác thực IPN;
     - môi trường cổng = SANDBOX.
  3. Gắn khoá merchant sandbox vào `cangca-api` (bên ký tham số), cũng qua Secret Manager.
  4. Kiểm `/healthz` trả 200.
  5. **Đã làm:** Duy đã khai IPN URL `https://cangca-adapter-675411800433.asia-southeast1.run.app/ipn/sepay` trên SePay. Sau deploy cần:
     - kiểm URL thật của Cloud Run **trùng** URL đã khai; nếu khác thì báo Duy sửa;
     - kiểm kiểu xác thực IPN trên SePay = SECRET_KEY;
     - bấm lại "gửi test" trên SePay, kết quả phải hết 404.
  6. Chạy thử một giao dịch sandbox từ đầu tới cuối: đặt đơn, thanh toán sandbox, đơn chuyển đã thanh toán, phiếu giao được tạo. Thử thêm: gửi lại cùng IPN (không ghi đôi), IPN sai khoá (bị từ chối).
- **Ngoại lệ:**
  - Deploy xong nhưng Django từ chối token: adapter trả lỗi, SePay gửi lại; sửa cấu hình rồi IPN tự vào.
  - URL thật khác URL dự kiến: báo Duy khai **URL thật**.
- **Hậu điều kiện:** có biên bản chạy thử sandbox. Chuyển sang production là một việc riêng, **cần Duy duyệt lại** (khoá production, IPN URL production, R1).

## 6. Business rule
| Mã | Nội dung | Nhãn | Mới / Sửa / Giữ |
|---|---|---|---|
| BR-TT-01 | Phương thức thanh toán **duy nhất ở V1** là **VietQR trên trang cổng SePay**; không thẻ, không NAPAS khác. Mỗi lần thanh toán mang **mã đơn** (`order_invoice_number`) và **đúng tổng đơn**. Shop không tự vẽ QR | D (Duy, 2026-09-26) | **Sửa** (thay "mã VietQR động do hệ thống sinh") |
| BR-TT-02 | Thông báo thanh toán của SePay (**IPN cổng**) đi qua FastAPI adapter rồi vào API nội bộ Django. Không nối thẳng lõi | D | **Sửa** (webhook → IPN; tinh thần giữ nguyên) |
| BR-TT-03 | Xử lý IPN phải **idempotent**. Khoá chống trùng là **mã giao dịch thanh toán** (ưu tiên mã tham chiếu ngân hàng nếu IPN có, không thì mã giao dịch SePay). **Không dùng mã đơn làm khoá**, vì một đơn có thể nhận nhiều khoản thật (UC-2 E2) | PA | **Sửa** |
| BR-TT-04/05/06/07 | Thiếu tiền → hàng chờ; về sau khi huỷ → ORPHAN; doanh thu tại lúc xác nhận; xác nhận tay chỉ Chủ | — | **Giữ** |
| BR-TT-08/09/10 | Xác nhận tay; hàng chờ lệch phải được đóng; chuyển thừa → OVERPAID (có trong code, chưa vào spec, nợ N-4) | PA/D | **Giữ** (nhân dịp này đưa vào spec) |
| BR-TT-12 | **Chỉ IPN** (máy chủ SePay gọi máy chủ mình, đã xác thực) mới xác nhận được thanh toán. Việc khách quay về `success_url` **không** phải bằng chứng đã trả | PA | **Mới** |
| BR-TT-13 | Số tiền, mã đơn và chữ ký gửi cổng **do máy chủ lập** từ đơn trong hệ thống. Khoá bí mật SePay **không bao giờ** xuống trình duyệt, không nằm trong mã nguồn, không xuất hiện trong log | PA | **Mới** |
| BR-TT-14 | Môi trường cổng (sandbox/production), URL cổng, merchant ID, khoá là **cấu hình theo môi trường**. Khoá sandbox chỉ dùng với dữ liệu thử. Giao dịch sandbox **không được** xác nhận đơn của khách thật (R1, Q3) | PA | **Mới** |
| BR-TT-15 | Mỗi khoản tiền chỉ được **một kênh tự động** báo về. V1: chỉ IPN cổng; **không bật** webhook biến động số dư. Muốn bật lại song song thì phải có chống trùng giữa hai kênh trước. Khi IPN trùng một khoản Chủ đã xác nhận tay (UC-5), không được để thành "tiền thừa" không kèm cảnh báo | D (kênh duy nhất) + PA (cảnh báo) | **Mới** |
| BR-TT-16 | IPN `TRANSACTION_VOID` **không** tự đổi đơn hay kho. V1 ghi log cảnh báo, Chủ xử lý theo P-07. Bật thẻ thì phải nâng lên thành cảnh báo trên ERP | PA | **Mới** |
| BR-TT-17 | Chỉ lập tham số thanh toán cho đơn **Giữ chỗ còn TTL**. Khách được thanh toán lại nhiều lần trong TTL, luôn đúng tổng đơn đã đóng băng | PA | **Mới** |
| BR-BH-03 | TTL giữ chỗ 30' | D | **Giữ** (không kéo dài vì có cổng) |
| BR-BH-15 (đề xuất) | **Tổng đơn là số nguyên đồng** (làm tròn lúc tạo đơn), để số khách trả qua cổng đúng bằng số trên hoá đơn (Q6). *Mã tạm; nếu BR-BH-12…14 ở hồ sơ họp Duy–Lộc đã dùng thì giữ 15* | PA | **Mới** |

## 7. Tác động dữ liệu & tích hợp

### 7.1 Dữ liệu (không thiết kế chi tiết)
- `PaymentTransaction.Source`: cần phân biệt **IPN cổng** với "Webhook SePay" (biến động số dư) và "Xác nhận tay". Mục đích: đối soát, nhãn trên ERP và luật nghi trùng UC-5. Đổi danh sách lựa chọn thì cần migration. Lý do: BR-TT-15.
- `PaymentTransaction.raw_payload`: lưu payload IPN gốc (đã có field), **không lưu header**. Cần lưu cả môi trường (sandbox/production) để lọc được (BR-TT-14).
- `SalesInvoice.payment_method`: điền theo phương thức thật trong IPN (chuyển khoản/VietQR, thẻ nếu bật). Field đã có.
- Sự kiện `TRANSACTION_VOID`: V1 chỉ log cảnh báo, không cần dữ liệu mới (UC-4).
- Tổng đơn nguyên đồng (BR-BH-15): đổi cách tính ở `create_order`, **không đổi schema**.
- **Không đụng** giá vốn, lô, FEFO, bảng phân bổ lô.

### 7.2 API / màn hình
- **Shop API (Django):**
  - đặt đơn: bỏ `vietqr` giả, trả thông tin để bắt đầu thanh toán;
  - lập tham số thanh toán (lần đầu và thanh toán lại) cho đơn `BOOKED` còn TTL;
  - tra đơn: thêm trạng thái "chờ thanh toán / đã thanh toán" và TTL còn lại.
- **Adapter:** route mới `POST /ipn/sepay`. Route cũ `/webhook/sepay` giữ code nhưng **không khai** trên SePay và **tắt bằng cấu hình** (Duy chốt). Adapter không được bắt buộc khoá webhook cũ khi route đó tắt.
- **Shop FE:**
  - trang checkout: nút thanh toán, chuyển sang SePay, bỏ QR giả;
  - trang tra đơn: nhận khách quay về từ `success_url`/`cancel_url`/`error_url`, chờ IPN, nút thanh toán lại;
  - chế độ mock phải còn chạy.
- **ERP console:** nhãn nguồn "Cổng SePay" trong chi tiết đơn và hàng chờ; nhãn nghi trùng (UC-5). Cả hai là thay đổi nhỏ trên màn hình có sẵn.

### 7.3 Bên thứ 3 & hạ tầng
- **SePay Cổng thanh toán:**
  - sandbox: `pay-sandbox.sepay.vn` (khởi tạo checkout `/v1/checkout/init`), REST `pgapi-sandbox.sepay.vn`;
  - production: `pay.sepay.vn`, `pgapi.sepay.vn`;
  - REST dùng Basic `base64(merchant_id:secret_key)`;
  - IPN: POST JSON tới URL HTTPS công khai, đòi HTTP 200, gửi lại khi không nhận 200.
- **Cloud Run `cangca-adapter`** (mới): công khai; secret qua Secret Manager; gọi `cangca-api` qua URL công khai của nó, bảo vệ bằng `X-Internal-Token`.
- **Cloud Run `cangca-api`:** cần có `INTERNAL_SERVICE_TOKEN` (settings đọc env, rỗng thì **từ chối mọi call nội bộ**) và khoá merchant (sandbox) để ký. Phải kiểm trước khi deploy adapter.
- **Firebase `cangca-loc`** (Shop): `success_url`/`cancel_url`/`error_url` trỏ về domain Shop, lấy từ cấu hình.

## 8. Rủi ro Cá Về
| # | Nhóm | Rủi ro | Giảm thiểu |
|---|---|---|---|
| R1 | **Tiền + tồn** | **Lớn nhất.** Khoá đang là SANDBOX nhưng adapter trỏ vào `cangca-api` production (Cloud SQL thật). Một lần thanh toán sandbox (tiền giả) sẽ xuất hoá đơn **thật**, trừ kho **thật**, ghi doanh thu **thật**, tạo phiếu giao cho NV kho. Chứng từ không xoá được (BR-PQ-10). Nếu Shop đã mở công khai lúc này, khách thật có thể "trả" bằng sandbox và **nhận hàng không mất tiền** | Q3. Mặc định: trong giai đoạn sandbox **không mở Shop công khai**; chỉ thử trên mặt hàng/lô thử; đánh dấu môi trường trên từng giao dịch; trước khi chuyển production thì dọn dữ liệu thử theo cách Duy chọn |
| R2 | Tiền | Ghi đôi một khoản: IPN + xác nhận tay → `OVERPAID` giả → Chủ hoàn khoản không có thật. V1 đã loại cặp IPN + webhook ngân hàng; cặp này quay lại nếu bật webhook | BR-TT-15, UC-5, Q4 |
| R3 | Tiền | Tổng đơn lẻ xu (18.812,50đ) mà cổng thu nguyên đồng. Làm tròn xuống thì `UNDERPAID`, đơn kẹt chờ Chủ; làm tròn lên thì sinh dòng thừa 0,50đ vào hàng chờ | BR-BH-15, Q6 |
| R4 | Tiền | Khách trả sau khi hết TTL (trang SePay mở lâu) → ORPHAN → Lộc chuyển khoản hoàn tay, tốn công và mất lòng khách | UC-3, Q7 |
| R5 | Bảo mật | Lộ khoá SePay qua FE, log, raw_payload, hoặc so khoá không hằng-thời-gian (adapter hiện so chuỗi thường ở route cũ) | BR-TT-13, AC bảo mật ở story |
| R6 | Tiền | Bật **thẻ** sau này: tiền đi qua SePay rồi mới về Lộc (đối soát, phí, có thể có hoàn qua cổng). Điều này mâu thuẫn tiền đề của decisions 2026-09-09 "tiền vào thẳng tài khoản, hoàn tay" | Đã loại ở V1 (Duy chốt chỉ VietQR). Bật thẻ phải phân tích lại |
| R7 | Tồn | IPN lỗi kéo dài (adapter chết) → đơn đã trả vẫn tự huỷ sau 30', hàng bị nhả cho người khác, tiền vào ORPHAN | Giám sát adapter (như BR-BH-04), xác nhận tay E-05 |
| — | Giá vốn | Không lộ: IPN và Shop không chạm field giá vốn | — |
| — | Phân quyền | Không quyền mới; hàng chờ và hoàn vẫn chỉ Chủ | — |
| — | Chứng từ/AuditLog | Hoá đơn chỉ Hệ thống tạo (BR-PQ-11), không xoá. Void không xoá chứng từ (BR-TT-16) | — |

## 9. Ngoài phạm vi
- Chuyển sang **production** (khoá thật, IPN URL production, mở Shop công khai): việc riêng, cần Duy duyệt sau khi sandbox đạt.
- Thanh toán **thẻ nội địa/quốc tế**, NAPAS khác, trả góp, ví (Duy chốt: V1 chỉ VietQR).
- **Webhook biến động số dư** (`/webhook/sepay`) làm kênh tự động thứ hai. Bật lại thì phải làm chống trùng giữa hai kênh trước (BR-TT-15).
- **Hoàn tiền tự động qua API cổng**: giữ hoàn tay theo decisions 2026-09-09.
- Tra cứu chủ động trạng thái đơn qua REST SePay để đối soát (job đối soát định kỳ). Để sau, XANH Q11.
- Gỡ bỏ code webhook biến động số dư: giữ code, chỉ không bật.
- Sửa `doc/decisions.md`: BA không sửa. Cần Duy ghi quyết định mới (Q10).

## 10. Câu hỏi mở
**Đã chốt (Duy, 2026-09-26), bỏ khỏi bảng:** Q1: chỉ VietQR, không thẻ/NAPAS. Q2: không dùng webhook ngân hàng, chỉ IPN. Q8: hệ quả của Q1, V1 xử lý void bằng log cảnh báo. Số Q giữ nguyên để khớp tham chiếu trong story.

| # | Mức | Câu hỏi | Mặc định PA đề xuất |
|---|---|---|---|
| Q3 | **ĐỎ** | Trong giai đoạn sandbox, dữ liệu trên `cangca-api` production là **thật hay thử**? Shop có đang/sắp mở cho khách thật không? Khi lên production, dữ liệu thử (hoá đơn, trừ kho do sandbox) xử lý thế nào? | Coi là **thử**. **Shop chưa mở công khai** cho tới khi đổi sang khoá production. Chỉ thử trên mặt hàng/lô thử. Mỗi giao dịch ghi môi trường. Trước khi mở public, Duy chọn: dựng lại DB sạch, hoặc huỷ đơn thử theo P-07 và để lại vết |
| Q4 | **ĐỎ** (BE tự trả lời được bằng một IPN sandbox thật) | IPN có **mã tham chiếu ngân hàng** (FT…) không, và field nào là **mã giao dịch duy nhất** của SePay? | Khoá chống trùng = mã tham chiếu ngân hàng nếu có (trùng mã Chủ gõ khi xác nhận tay), không thì mã giao dịch SePay. **Không** dùng `order_invoice_number` làm khoá. Chốt sau khi xem payload sandbox thật, ghi vào dev-notes |
| Q5 | VÀNG | SePay có cho khởi tạo lại checkout với **cùng** `order_invoice_number` (thanh toán lại) không? | Dùng đúng mã đơn. Nếu SePay từ chối thì thêm hậu tố lần thử, và adapter bóc hậu tố khi khớp đơn. BE kiểm trên sandbox |
| Q6 | VÀNG | Tổng đơn có lẻ xu thì làm tròn thế nào? | **Làm tròn tổng đơn về nguyên đồng (half-up) ngay lúc tạo đơn** (BR-BH-15). Hoá đơn, cổng và sao kê cùng một số |
| Q7 | VÀNG | Phiên thanh toán SePay có đặt thời hạn được không? | Nếu được: đặt ≤ TTL còn lại. Nếu không: chấp nhận ORPHAN (BR-TT-05), Shop cảnh báo rõ thời hạn |
| Q9 | VÀNG | IPN `ORDER_PAID` nhưng `order.status` ≠ `CAPTURED` hoặc `currency` ≠ VND? | Không xác nhận đơn. Ghi nhận để Chủ xem, trả 200 |
| Q10 | VÀNG | Duy có ghi quyết định mới vào `decisions.md` không? Nội dung: "Dùng Cổng thanh toán SePay (hosted checkout + IPN) thay mô hình QR tự vẽ + webhook biến động số dư; V1 chỉ VietQR, không thẻ/NAPAS; chỉ IPN, webhook ngân hàng giữ code nhưng tắt" (Duy đã nói trong phiên, chỉ còn việc ghi vào file) | Có, Duy ghi. BA đã đề xuất nội dung sửa spec BR-TT-01/02/03 và thêm BR-TT-12…17 (story P6) |
| Q11 | XANH | Có cần job đối soát định kỳ gọi REST SePay để bắt IPN bị sót không? | Để sau khi chạy production một thời gian |
| Q12 | XANH | Phí giao dịch cổng SePay: ai chịu, có hạch toán vào lãi lỗ không? | V1 không hạch toán phí (spec §15 mục 6 vẫn treo) |

---
## Quyết định của Duy (2026-09-26)
- **Q3:** giai đoạn test sandbox **dùng luôn production** (`cangca-api` / Cloud SQL); dữ liệu hiện tại coi là **dữ liệu thử**. **Shop CHƯA mở công khai** cho tới khi có khoá SePay production; trước khi mở, dọn DB (dựng lại sạch hoặc huỷ đơn thử theo P-07). Mỗi giao dịch ghi môi trường (SANDBOX/PRODUCTION) để nhận diện.
- **Q4:** BE tự xác định mã giao dịch duy nhất bằng một IPN sandbox thật (ưu tiên mã FT…, không dùng mã đơn làm khoá).
- **Q5–Q10:** áp dụng mặc định 🟡 như đề xuất. **Duyệt 8 story P1–P8.**
- Trước đó Duy đã chốt: **chỉ VietQR** qua Cổng SePay; không thẻ/NAPAS; không dùng webhook ngân hàng (giữ code, tắt bằng cấu hình).

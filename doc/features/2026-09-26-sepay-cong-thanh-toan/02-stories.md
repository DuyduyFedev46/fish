# Cổng thanh toán SePay: user stories (bản nháp)
> BA (nháp cho PO) · 2026-09-26 · Nguồn: `01-analysis.md` (CHỜ DUYỆT). Trạng thái: **ĐÃ DUYỆT** (2026-09-26, Duy)
> Duy đã chốt 2026-09-26:
> - V1 **chỉ VietQR qua Cổng SePay**, không thẻ/NAPAS;
> - **chỉ IPN**: webhook ngân hàng `/webhook/sepay` giữ code nhưng tắt;
> - IPN URL `…/ipn/sepay` **đã khai** trên SePay.
>
> Câu ĐỎ còn lại là Q3 (dữ liệu thử/thật) và Q4 (khoá chống trùng, BE tự chốt bằng IPN sandbox). AC có đánh dấu (Qx) viết theo mặc định PA.

## Bảng tóm tắt
| Story | Tên | Ưu tiên | Bên làm | BR | Phụ thuộc |
|---|---|---|---|---|---|
| P1 | Máy chủ lập tham số thanh toán cổng cho đơn | Must | BE (Django) | BR-TT-01, 13, 14, 17 | Q6 |
| P2 | Adapter nhận IPN `/ipn/sepay` | Must | Adapter | BR-TT-02, 03, 12, 13, 16 | Q4 |
| P3 | Lõi ghi nhận giao dịch cổng và chống ghi đôi | Must | BE (Django) | BR-TT-03, 10, 14, 15 | P2 |
| P4 | Shop: chuyển sang SePay, quay về, thanh toán lại | Must | FE (Shop) | BR-TT-01, 12, 17 | P1 |
| P5 | Tổng đơn nguyên đồng | Must | BE (Django) | BR-BH-15 | Q6 |
| P6 | Deploy adapter sandbox và chạy thử đầu-cuối | Must | Ops (cần Duy duyệt) | BR-TT-14 | P1–P5 |
| P7 | Tài liệu: spec, URD, decisions | Must | BA + Duy | BR-TT-01…17 | — |
| P8 | Hiện nguồn "Cổng SePay", nhãn SANDBOX, nhãn nghi trùng trên ERP | Should | FE (ERP) | BR-TT-14, 15 | P3 |

Thứ tự: P5 → P1 và P2/P3 song song → P4 → QA → P6 (deploy, Duy duyệt) → kiểm URL khớp và "gửi test" SePay → chạy thử sandbox. P7 làm song song. P8 có thể sau.
Nếu cần có adapter sớm để hết 404: P2 + P3 + P6 (phần adapter) có thể deploy trước P1/P4. IPN khi đó chỉ khớp được đơn tạo tay để thử.

---

## P1: Lập tham số thanh toán cổng · Must · BE
**Là** khách, **tôi muốn** bấm "Thanh toán" và được đưa sang trang SePay với đúng đơn và đúng số tiền, **để** trả tiền mà không phải gõ tay nội dung chuyển khoản.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| P1-AC1 | Đơn `BOOKED`, còn TTL, tổng 540.000đ | Shop xin tham số thanh toán cho đơn | Nhận bộ tham số: `order_invoice_number` = mã đơn, `order_amount` = 540000, `currency` = VND, 3 URL quay về trang tra đơn của Shop (có mã đơn), chữ ký HMAC-SHA256 hợp lệ, URL cổng đúng môi trường đang cấu hình | BR-TT-01 |
| P1-AC2 | Bất kỳ | Xem phản hồi, mã nguồn FE, log máy chủ | **Không** có `secret_key` hay merchant secret ở đâu. Chỉ có chữ ký | BR-TT-13 |
| P1-AC3 | Cấu hình môi trường = SANDBOX | Lập tham số | Dùng URL cổng sandbox và khoá sandbox. Đổi sang production **chỉ bằng cấu hình**, không sửa code | BR-TT-14 |
| P1-AC4 | Đơn đã hết TTL, đã tự huỷ, hoặc đã thanh toán | Xin tham số | Từ chối, thông điệp tiếng Việt kèm mã BR ("Đơn đã hết hạn giữ hàng, vui lòng đặt lại" / "Đơn đã thanh toán") | BR-TT-17 |
| P1-AC5 | Đơn `BOOKED` còn TTL, khách đã huỷ trên SePay một lần | Xin tham số lần hai | Nhận bộ tham số mới cho **cùng đơn, cùng số tiền**. Nếu SePay không nhận lại cùng mã đơn thì dùng hậu tố lần thử (Q5) | BR-TT-17 |
| P1-AC6 | Người gọi đoán mã đơn của người khác | Xin tham số | Chỉ trả tham số cho đơn `BOOKED`; không lộ thông tin khách (tên, SĐT, địa chỉ) trong phản hồi | BR-TT-13 |
| P1-AC7 | Đặt đơn thành công | Xem phản hồi đặt đơn | Không còn trường `vietqr` giả (hoặc không còn được dùng) | BR-TT-01 |

---

## P2: Adapter nhận IPN · Must · Adapter
**Là** Hệ thống, **tôi muốn** nhận thông báo "đã thu tiền" của SePay và chuyển vào lõi, **để** đơn tự được xác nhận mà Lộc không phải dò sao kê.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| P2-AC1 | IPN `ORDER_PAID`, `order.status=CAPTURED`, `currency=VND`, header `X-Secret-Key` đúng | POST `/ipn/sepay` | Gọi Django nội bộ với `bank_txn_id` (theo Q4, đã chuẩn hoá), `order_code` = `order_invoice_number` (bóc hậu tố nếu có, Q5), `amount`, `received_at` (ISO 8601, múi giờ VN), `raw` = payload **không có header**; trả **200** | BR-TT-02 |
| P2-AC2 | Thiếu hoặc sai `X-Secret-Key` | POST | Từ chối, không gọi Django. So khoá **hằng-thời-gian**. Log không chứa giá trị khoá | BR-TT-13 |
| P2-AC3 | Cùng một IPN gửi 2 lần | POST lần 2 | Trả 200 với đúng kết quả lần 1. Django không ghi dòng mới | BR-TT-03 |
| P2-AC4 | Django timeout hoặc 5xx | POST | Adapter **không trả 200**, để SePay gửi lại | BR-TT-02 |
| P2-AC5 | Payload hỏng vĩnh viễn (thiếu mã đơn, số tiền, mã giao dịch) | POST | Không gây vòng gửi lại vô hạn; log cảnh báo đủ để đối soát (mã đơn, mã giao dịch nếu có); không log khoá | E9 |
| P2-AC6 | `ORDER_PAID` nhưng `order.status` ≠ `CAPTURED` hoặc `currency` ≠ VND | POST | Không xác nhận đơn; ghi nhận để Chủ xem (Q9); trả 200 | Q9 |
| P2-AC7 | `TRANSACTION_VOID` | POST | Trả 200; **không** đổi đơn/kho; ghi **log cảnh báo** có mã đơn, mã giao dịch, không có khoá | BR-TT-16 |
| P2-AC8 | Cấu hình tắt webhook ngân hàng (mặc định V1), không có khoá webhook cũ | Khởi động, rồi POST `/webhook/sepay` | Adapter vẫn chạy; route cũ **không xử lý** (từ chối), không gọi Django. Code route cũ giữ nguyên, test cũ vẫn chạy khi bật cấu hình | BR-TT-15 |
| P2-AC9 | `GET /healthz` | Gọi | 200 | — |

---

## P3: Lõi ghi nhận giao dịch cổng · Must · BE
**Là** Chủ, **tôi muốn** mỗi khoản tiền chỉ nằm trên sổ một lần và biết nó đến từ cổng, **để** không hoàn nhầm khoản không có thật.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| P3-AC1 | Đơn `BOOKED` 540.000đ | IPN 540.000đ | Giao dịch `MATCHED`, nguồn **Cổng SePay**; hoá đơn xuất, trừ kho đúng lô đã giữ; đơn `PROCESSING`; phiếu giao `PREPARING`; `payment_method` theo phương thức thật | BR-TT-06, BR-BH-11 |
| P3-AC2 | Đơn đã `AUTO_CANCELLED` | IPN về | `ORPHAN`, vào hàng chờ; đơn không khôi phục; kho không đổi | BR-TT-05 |
| P3-AC3 | Đơn `BOOKED` 540.000đ | IPN 500.000đ | `UNDERPAID`, hàng chờ | BR-TT-04 |
| P3-AC4 | Đơn `BOOKED` 540.000đ | IPN 600.000đ | `MATCHED` 540.000đ + dòng `OVERPAID` 60.000đ trong hàng chờ | BR-TT-10 |
| P3-AC5 | Đơn đã thanh toán qua cổng | Giao dịch cổng thứ hai (mã khác) cho cùng đơn | `OVERPAID`, hàng chờ, không xuất hoá đơn lần hai | BR-TT-10 |
| P3-AC6 | Chủ đã xác nhận tay đơn bằng mã FT… | IPN về muộn **có** cùng mã FT… | Không ghi dòng mới (trùng khoá). *Ghi chú: V1 không có webhook ngân hàng nên không cần chống trùng IPN–webhook; bật lại webhook thì phải thêm AC cho cặp đó* | BR-TT-03, BR-TT-15 |
| P3-AC7 | Chủ đã xác nhận tay đơn bằng mã FT…, cùng số tiền | IPN về muộn **không** có mã FT… | Dòng `OVERPAID` được gắn nhãn "Nghi trùng xác nhận tay, đối chiếu sao kê trước khi hoàn" (lưu được, hiện được trên hàng chờ) | BR-TT-15 |
| P3-AC8 | Mọi giao dịch từ cổng | Ghi | Lưu môi trường (SANDBOX/PRODUCTION) cùng giao dịch để lọc được | BR-TT-14 |
| P3-AC9 | Thêm giá trị nguồn mới | Migrate | Có migration; giao dịch cũ giữ nguồn cũ | bất biến #8 |

---

## P4: Shop, luồng thanh toán · Must · FE
**Là** khách, **tôi muốn** thấy rõ còn bao lâu để trả, bấm là sang SePay, trả xong quay về thấy đơn đã được nhận, **để** yên tâm là hàng đã giữ cho mình.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| P4-AC1 | Vừa đặt đơn | Xem trang checkout | Thấy mã đơn, tổng tiền, đồng hồ TTL, nút "Thanh toán bằng VietQR", ghi chú "Thanh toán 100% trước khi giao". **Không** còn QR giả | BR-TT-01, BR-TT-11 |
| P4-AC2 | Bấm nút | — | Trình duyệt sang trang SePay với tham số máy chủ trả (P1); FE không tự tính tiền hay chữ ký | BR-TT-13 |
| P4-AC3 | Quay về từ `success_url`, IPN **chưa** tới | Trang tra đơn | Hiện "Đang chờ xác nhận thanh toán", tự cập nhật; **không** hiện "đã thanh toán" | BR-TT-12 |
| P4-AC4 | IPN đã tới | Trang tra đơn | Hiện "Đã thanh toán, đang soạn hàng" | BR-TT-12 |
| P4-AC5 | Quay về từ `cancel_url`/`error_url`, còn TTL | Trang tra đơn | Hiện "Chưa thanh toán, còn mm:ss" và nút "Thanh toán lại" | BR-TT-17 |
| P4-AC6 | Hết TTL | Bấm "Thanh toán lại" hoặc mở trang | Báo đơn đã hết hạn giữ hàng, mời đặt lại; không chuyển sang SePay | BR-TT-17 |
| P4-AC7 | Quay về trang tra đơn | — | Khách không phải gõ lại mã đơn (mã có sẵn trên URL); vẫn cần 4 số cuối SĐT (hoặc Shop nhớ trong phiên, PA) | spec §7.1 |
| P4-AC8 | `NEXT_PUBLIC_USE_MOCK=1` | Chạy luồng | Có giả lập chuyển sang/quay về; `npm run build` sạch | — |

---

## P5: Tổng đơn nguyên đồng · Must · BE
| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| P5-AC1 | 0,125 kg × 150.500đ (= 18.812,50đ) | Tạo đơn | Tổng đơn **18.813đ** (half-up, Q6); số gửi cổng, số trên hoá đơn và số khách trả trùng nhau | BR-BH-15 |
| P5-AC2 | Đơn có PricingRule giảm % | Tạo đơn | Tổng sau giảm là nguyên đồng; dòng đơn vẫn lưu được như hiện nay | BR-DM-08 |
| P5-AC3 | Đơn cũ (lẻ xu) đang `BOOKED` | Lập tham số (P1) | Không lập được tham số với số lẻ: từ chối hoặc làm tròn theo cùng quy tắc, BE chọn và ghi dev-notes | BR-BH-15 |

---

## P6: Deploy adapter sandbox và chạy thử · Must · Ops (Duy duyệt trước khi chạy)
| Mã | Tiêu chí nghiệm thu | BR |
|---|---|---|
| P6-AC1 | Trước deploy: xác nhận `cangca-api` có `INTERNAL_SERVICE_TOKEN` (cùng giá trị với adapter, từ Secret Manager) và khoá merchant sandbox để ký (P1) | BR-TT-02 |
| P6-AC2 | Cloud Run `cangca-adapter` (`asia-southeast1`, project `keolai-63ec1`) chạy, công khai; secret lấy từ Secret Manager (`cangca-sepay-sandbox-*` + token nội bộ); **không** có secret trong image, biến môi trường dạng chữ, hay log | BR-TT-13 |
| P6-AC3 | `/healthz` = 200. Gọi `/ipn/sepay` sai khoá thì bị từ chối | BR-TT-13 |
| P6-AC4 | URL thật của Cloud Run **trùng** URL Duy đã khai (`https://cangca-adapter-675411800433.asia-southeast1.run.app/ipn/sepay`); nếu khác thì báo Duy sửa. Kiểu xác thực IPN trên SePay = SECRET_KEY. "Gửi test" trên SePay không còn 404 | — |
| P6-AC5 | Chạy thử đầu-cuối trên mặt hàng/lô thử: đặt đơn → thanh toán sandbox → đơn `PROCESSING` + phiếu giao; gửi lại IPN không ghi đôi; huỷ trên SePay → thanh toán lại được. Ghi biên bản vào `05-deploy-runbook.md` | BR-TT-03, 14 |
| P6-AC6 | Shop **chưa mở công khai** trong giai đoạn sandbox (Q3) | BR-TT-14 |

---

## P7: Tài liệu · Must · BA + Duy
| Mã | Tiêu chí nghiệm thu |
|---|---|
| P7-AC1 | Spec §7.4: sửa BR-TT-01/02/03; thêm BR-TT-08/09/10 (nợ N-4), BR-TT-11 (nếu chưa có), BR-TT-12…17; §7.3 thêm BR-BH-15; §13 thêm ngoại lệ: IPN về muộn sau xác nhận tay, void, sandbox |
| P7-AC2 | URD §6.5: mô tả luồng chuyển sang trang SePay, không còn "hệ thống sinh QR" |
| P7-AC3 | **Duy** ghi quyết định mới vào `decisions.md` (Q10). BA không sửa file này |
| P7-AC4 | README adapter/backend: bỏ ghi chú "VietQR stub"; ghi biến cấu hình mới (tên biến, không ghi giá trị) |

---

## P8: ERP, nguồn và cảnh báo · Should · FE (ERP)
| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| P8-AC1 | Giao dịch từ IPN | Chủ xem chi tiết đơn / hàng chờ | Nguồn hiện "Cổng SePay"; giao dịch sandbox có nhãn **SANDBOX** | BR-TT-14 |
| P8-AC2 | Dòng `OVERPAID` nghi trùng (P3-AC7) | Chủ mở hàng chờ | Thấy nhãn cảnh báo trước nút hoàn | BR-TT-15 |
| P8-AC3 | NV giao / NV kho | Xem | Không thấy thông tin giao dịch/tiền ngoài quyền hiện có | BR-PQ |

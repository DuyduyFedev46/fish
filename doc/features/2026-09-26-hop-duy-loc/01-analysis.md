# Họp Duy – Lộc 2026-09-26: quy mô đơn, thanh toán 100%, khách thân quen, in đơn tự động, vùng giao miền Nam — Phân tích nghiệp vụ
> BA · 2026-09-26 · Trạng thái: **CHỜ DUYỆT**

Ký hiệu mức câu hỏi: **ĐỎ** = chặn, không trả lời thì không viết story được · **VÀNG** = có mặc định PA, Duy có thể lật · **XANH** = để sau.

## 1. Yêu cầu gốc
Nguyên văn tại `00-bien-ban-hop.md` (Duy dán vào phiên chat 2026-09-26). Nhãn nguồn: **(L)** vì là phát biểu trong buổi họp với Lộc về mô hình kinh doanh. Tóm tắt:

| # | Nội dung (nguyên văn rút gọn) | Nhãn |
|---|---|---|
| Y1 | "đơn hàng sẽ khoảng 700k-1tr vnd" | L |
| Y2 | "Thanh toán sẽ là 100%, bỏ loại cọc" | L |
| Y3 | "KHách hàng thân quen = KH mua trên số lượng đơn/ số lượng tiền --> có thể tủy chỉnh theo period" | L |
| Y4 | "in đơn hangd tự động khi KH thanh toán xong" | L |
| Y5 | "Ship, chỉ tạp trung miền nam, kho ở Phan Thiết" + danh sách 12 tỉnh cách Phan Thiết dưới 300 km | L |

## 2. Tóm tắt
- **Khách** cần biết ngay lúc đặt rằng địa chỉ của mình có được giao không và phải trả đủ 100%, để không trả tiền cho đơn vựa không giao được.
- **Chủ vựa** cần nhận diện khách thân quen theo số đơn và/hoặc số tiền trong một kỳ tự chọn, để chăm sóc nhóm khách mang lại doanh thu.
- **NV kho** cần phiếu in ra ngay khi đơn được thanh toán, để soạn hàng không phải mở máy tra từng đơn.

## 3. Bối cảnh trong hệ thống

### 3.1 Quy trình, rule và quyết định liên quan
| Nội dung | Quy trình | Rule hiện có | Quyết định ràng buộc (decisions.md) |
|---|---|---|---|
| Y1 quy mô đơn | P-01, P-05 | BR-DM-08 (PricingRule theo đơn) | 2026-09-10 Combo (PricingRule 1 tầng) |
| Y2 thanh toán 100% | P-05, P-07 | BR-TT-01…10, BR-BH-03 | 2026-09-09 SO booked TTL 30'; 2026-09-09 VietQR SePay |
| Y3 khách thân quen | P-05 §7.1, P-10 | §7.1 (guest checkout, gộp theo SĐT), BR-DM-08 | 2026-09-10 "Các mặc định PA": danh tính khách; 2026-09-09 B2C thuần |
| Y4 in đơn | P-05 → P-06 | BR-GH-03, BR-GH-06, BR-TT-03 | 2026-09-09 FastAPI là cửa vào duy nhất cho bên thứ 3; 2026-09-10 Soạn hàng |
| Y5 vùng giao | P-05, P-06, P-08 | BR-BH-09, BR-BH-10, BR-GH-01/02, BR-HV-03 | 2026-09-09 **100% giao tận nhà, NV nội bộ, không Grab/Ahamove**; 2026-09-09 **Phí giao OUTSCOPE**; "Quy mô 1 điểm bán duy nhất" |

### 3.2 Hiện trạng code (đã đọc, không suy đoán)
- **Không có khái niệm cọc/đặt cọc ở bất kỳ đâu.** Đã tìm "cọc/deposit" trong `doc/`, `backend/`, `frontend/`, `erp-console/`: không có kết quả nào ngoài biên bản họp. `SalesOrder` chỉ có `total_amount`. `_record_payment` (`sales/payments/services.py`) so **từng giao dịch** với tổng đơn: đủ thì `MATCHED`, ra hoá đơn và chuyển `PROCESSING`. Thiếu thì `UNDERPAID`, vào hàng chờ Chủ (BR-TT-04). Đơn giữ chỗ vẫn tự huỷ khi hết TTL.
- **Tiền thiếu không phải là cọc.** Nếu khách chuyển 2 lần (lần đầu thiếu, lần sau bù), **lần thứ hai cũng bị ghi `UNDERPAID`** vì hệ thống so từng khoản, không cộng dồn. Chủ phải bấm "Xác nhận đơn (khách đã bù)" (S12, `CONFIRM_ORDER`). Cách này khớp với yêu cầu 100%: hệ thống không bao giờ tự giao hàng khi chưa đủ tiền.
- **Địa chỉ giao là văn bản tự do.** `SalesOrder.delivery_address` và `Customer.default_address` đều là `TextField`. Ô nhập ở Shop (`frontend/app/shop/checkout/page.tsx`) có gợi ý "Số nhà, đường, phường/xã, quận/huyện, tỉnh/thành", tức vẫn dùng **cấu trúc 3 cấp cũ** (còn quận/huyện). Hiện **không có** trường tỉnh/thành, danh mục địa giới, hay kiểm tra vùng giao nào.
- **SĐT khách không được chuẩn hoá.** `shop_api.py` chỉ `.strip()`, còn `get_or_create_by_phone` gộp theo đúng chuỗi nhập. Vì vậy "0901 234 567", "0901234567" và "+84901234567" tạo ra **ba khách khác nhau**. Điều này làm sai cả phần đếm khách thân quen (Y3).
- **`SalesOrder` không bao giờ được chuyển sang `COMPLETED`** trong code chạy thật (chỉ `seed_demo` gán). Khi phiếu giao Hoàn tất, trạng thái đơn không đổi theo. Vì vậy **không dùng được** "đơn trạng thái Hoàn tất" làm điều kiện đếm khách thân quen.
- **`PricingRule`** có `apply_on = ITEM | ORDER` và `min_amount`, nhưng **không có điều kiện theo khách**. Đã có sẵn loại "đơn ≥ M đồng → giảm".
- **Phiếu giao** được tạo tự động bằng signal `post_save(SalesInvoice)` (`delivery/signals.py`), trạng thái đầu là `PREPARING`. Mọi đường xác nhận tiền đều đi qua `issue_invoice`: webhook, xác nhận tay S11, hàng chờ S12. **Đây là thời điểm "khách thanh toán xong"** duy nhất, và nó không phát sinh lại khi webhook gửi lại (BR-TT-03).
- **Chưa có chức năng in nào**: không có mẫu in, không có máy in, không có "đã in". S19 (phiếu soạn trên console) và S17/S20 **chưa làm**. Backlog đã xong tới L9, còn L10 (S17, S18) và L11 (S19–S21) chưa làm.
- **Hạ tầng job:** production không có Redis/Celery. Job định kỳ chạy bằng Cloud Scheduler gọi endpoint (runbook deploy 1). Backend (Cloud Run) **không tự gọi được** tới máy in trong mạng LAN ở kho.
- **Tham số liên quan** (`config/settings.py`): `SALES_ORDER_TTL_MINUTES=30`, `DELIVERY_MAX_FAILED_ATTEMPTS=2`, `COLD_CHAIN_MAX_HOURS=6` (PA, câu hỏi mở #3 của spec).

## 4. Tác nhân & quyền
| Tác nhân | Group | Làm được gì trong phạm vi này | Quyền Tầng 2 cần |
|---|---|---|---|
| Khách | (không phải User) | Chọn tỉnh/thành và phường/xã từ danh sách, bị chặn nếu ngoài vùng giao, trả 100% qua VietQR. **Không** thấy nhãn thân quen (PA, Q10) | — |
| Hệ thống | `actor=None` | Kiểm vùng giao khi tạo đơn. Tạo lệnh in khi đơn được thanh toán. Tính nhãn thân quen | — |
| Máy in tại kho (tác nhân mới) | tài khoản kỹ thuật riêng (PA) | Chỉ lấy lệnh in đang chờ và báo "đã in / lỗi". Không đọc được gì khác | quyền mới, hẹp (PO/BE đặt tên). **Không** dùng tài khoản của người thật |
| NV kho | `nv_kho` | Nhận phiếu in, soạn hàng, **in lại** phiếu | xem phiếu giao (đã có) + quyền in lại (PA: `nv_kho`, `quan_ly`, `chu`) |
| NV giao | `nv_giao` | Thấy tỉnh/xã trên thẻ phiếu (S20). Không in, không thấy tiền (S20-AC6) | — |
| Quản lý | `quan_ly` | Xem nhãn thân quen, lọc phiếu theo tỉnh để gom tuyến, in lại | — |
| Chủ | `chu` | **Cấu hình vùng giao** và **cấu hình ngưỡng/kỳ khách thân quen** (đổi phạm vi bán và đối tượng hưởng ưu đãi nên thuộc Chủ). Xem tổng tiền mua của khách | quyền mới cho 2 cấu hình (PA, Q12) |

## 5. Use case

### UC-1 Khách đặt hàng: chọn địa chỉ trong vùng giao (Y5)
- **Tiền điều kiện:** Chủ đã cấu hình danh sách vùng giao (UC-2). Giỏ hàng có hàng.
- **Luồng chính:**
  1. Khách mở bước đặt hàng. Shop hiển thị thông báo "Vựa giao hàng tại: <danh sách vùng>. Thanh toán 100% qua chuyển khoản trước khi giao".
  2. Khách chọn **tỉnh/thành** từ danh sách, gồm **chỉ các tỉnh đang mở giao**.
  3. Khách chọn **phường/xã** thuộc tỉnh đó (theo danh mục sau sáp nhập 2025, không còn cấp huyện). Nếu Q4 chọn kiểm tới cấp xã thì chỉ hiện các xã đang mở giao.
  4. Khách nhập số nhà, đường, SĐT và tên.
  5. Hệ thống **kiểm lại vùng giao ở máy chủ** trước khi giữ chỗ. Không chỉ dựa vào danh sách trên giao diện.
  6. Hợp lệ thì tạo đơn Giữ chỗ như hiện nay (BR-BH-02/05/11), rồi hiện VietQR với **đúng tổng đơn** (BR-TT-01, BR-TT-11).
- **Luồng thay thế:**
  - 2a. Tỉnh của khách không có trong danh sách: Shop hiện "Hiện vựa chưa giao tới khu vực này" kèm số điện thoại liên hệ (PA). Khách không đặt tiếp được.
  - 4a. Khách cũ (cùng SĐT sau chuẩn hoá) có địa chỉ mặc định **có cấu trúc** và còn trong vùng: điền sẵn. Nếu địa chỉ cũ là văn bản tự do (đơn trước khi có tính năng này) thì **không** điền sẵn tỉnh/xã, khách phải chọn lại.
- **Ngoại lệ:**
  - E1. Gọi thẳng API tạo đơn với tỉnh/xã ngoài vùng hoặc không có trong danh mục: từ chối (BR-BH-12), **không giữ chỗ lô nào**, không tạo khách.
  - E2. Chủ tắt một tỉnh trong khi khách đang ở bước đặt: lúc gửi, bước 5 từ chối như E1. Đơn đã tạo trước đó **không bị ảnh hưởng** (PA, VÀNG Q15).
  - E3. Chưa có vùng giao nào được cấu hình: Shop không cho đặt hàng và báo "đang cập nhật khu vực giao". Đây là cách an toàn: thà không bán còn hơn bán rồi không giao được.
  - E4. Địa chỉ trong tỉnh đang mở nhưng thực tế quá xa để giao (ví dụ phần Phú Yên cũ nay thuộc Đắk Lắk). Nếu Q4 chỉ kiểm cấp tỉnh thì hệ thống không chặn được. Chủ sẽ huỷ đơn và hoàn tiền theo P-07. Đây là rủi ro đã biết, xem Q4.
- **Hậu điều kiện:** mọi đơn mới đều có tỉnh/thành và phường/xã **thuộc vùng giao tại thời điểm đặt**.

### UC-2 Chủ cấu hình vùng giao (Y5)
- **Tiền điều kiện:** Chủ đăng nhập ERP console. Hệ thống có danh mục tỉnh/thành và phường/xã **hiện hành** (sau sáp nhập 2025).
- **Luồng chính:**
  1. Chủ mở "Vùng giao hàng".
  2. Chủ bật/tắt từng tỉnh/thành. Nếu Q4 chọn kiểm cấp xã thì Chủ bật/tắt thêm từng phường/xã.
  3. Tuỳ Q9, Chủ ghi chú cho mỗi vùng, ví dụ "giao thứ 3, thứ 6". Shop hiển thị ghi chú này.
  4. Lưu. Hệ thống ghi AuditLog: ai, lúc nào, bật/tắt gì.
- **Ngoại lệ:** Tắt hết mọi vùng thì cảnh báo "Shop sẽ không nhận đơn nào" và bắt xác nhận. Người không có quyền mở màn này thì bị chặn (403).
- **Hậu điều kiện:** Shop và API tạo đơn dùng cấu hình mới ngay. Cấu hình là **dữ liệu**, không nằm cứng trong code (bất biến #7).

### UC-3 Thanh toán 100% (Y2): xác nhận luồng hiện tại, không thêm luồng mới
- **Tiền điều kiện:** đơn Giữ chỗ, TTL còn.
- **Luồng chính:** giữ nguyên P-05. Khách chuyển **đủ** tổng đơn, webhook ghi `MATCHED`, hệ thống xuất hoá đơn (trừ kho, ghi doanh thu), tạo phiếu giao `PREPARING`, rồi tạo lệnh in (UC-5).
- **Luồng thay thế/ngoại lệ (giữ nguyên, đã có code):** tiền thiếu → `UNDERPAID`, hàng chờ Chủ (BR-TT-04). Khách bù → Chủ xác nhận (S12). Tiền về sau khi đơn tự huỷ → `ORPHAN` → hoàn (BR-TT-05). Chuyển thừa → tách `OVERPAID` → hoàn (BR-TT-10). Không có tiền → tự huỷ sau 30' (BR-BH-03).
- **Điều cần làm:** chỉ ghi rule BR-TT-11 và sửa nội dung Shop/URD cho rõ "không cọc, không thu tiền khi nhận hàng (COD)". **Không thay đổi code thanh toán.**
- **Hậu điều kiện:** không có đơn nào được soạn/giao khi tổng tiền đã thu nhỏ hơn tổng đơn.

### UC-4 Nhận diện khách thân quen (Y3)
- **Tiền điều kiện:** Chủ đã đặt tiêu chí (UC-4b). SĐT khách đã được chuẩn hoá (BR-BH-14).
- **Luồng chính (xem):**
  1. Quản lý/Chủ mở danh sách đơn, chi tiết đơn hoặc danh sách khách (mới) trên ERP.
  2. Khách đạt tiêu chí trong kỳ hiện tại có nhãn "Khách thân quen".
  3. Chủ/Quản lý mở chi tiết khách: thấy số đơn và tổng tiền trong kỳ, danh sách đơn.
- **UC-4b (Chủ cấu hình):** đặt ngưỡng số đơn (có thể bỏ trống), ngưỡng tổng tiền (có thể bỏ trống), cách kết hợp (HOẶC/VÀ) và kỳ tính (Q6). Lưu thì ghi AuditLog.
- **Cách đếm (PA, VÀNG Q7):**
  - Chỉ đếm đơn **đã có hoá đơn bán** (đã thanh toán đủ), và **không** bị huỷ (`CANCELLED`).
  - Tổng tiền = tiền hoá đơn − các phiếu hoàn chưa ở trạng thái Thất bại.
  - Đơn thuộc kỳ theo **thời điểm ghi doanh thu** (`issued_at`, BR-TT-06).
  - Không dùng trạng thái đơn "Hoàn tất", vì code không bao giờ đặt trạng thái này (mục 3.2).
- **Luồng thay thế:** Chủ đổi tiêu chí thì nhãn tính lại ngay theo tiêu chí mới. Không ghi đè lịch sử đơn.
- **Ngoại lệ:**
  - E1. Khách đạt nhãn rồi bị huỷ/hoàn đơn nên tụt dưới ngưỡng: mất nhãn (nhãn tính lại, không "giữ mãi", PA).
  - E2. Cùng một người dùng 2 SĐT: là 2 khách. V1 không gộp tay (XANH).
  - E3. Chưa cấu hình tiêu chí: không hiện nhãn nào.
  - E4. NV giao chỉ thấy khách của phiếu mình (S5). Nhãn hiện hay không hiện với NV giao là câu hỏi Q10 (mặc định: không hiện).
- **Hậu điều kiện:** nhãn là giá trị **tính ra, chỉ để đọc**. Nếu Q5 chọn "chỉ nhãn" thì nhãn không đổi giá, tồn hay thứ tự giao.

### UC-5 In phiếu tự động khi đơn được thanh toán (Y4)
- **Tiền điều kiện:** ở kho Phan Thiết có một thiết bị in đang bật và đã đăng ký với hệ thống (Q8).
- **Luồng chính:**
  1. Đơn được xác nhận đủ tiền theo bất kỳ đường nào (webhook, S11, S12), hệ thống xuất hoá đơn và tạo phiếu giao `PREPARING`.
  2. **Cùng lúc**, hệ thống tạo **đúng một** lệnh in cho phiếu giao đó, trạng thái "Chờ in" (BR-GH-09).
  3. Thiết bị in ở kho lấy lệnh đang chờ về, in rồi báo "Đã in". Hệ thống ghi thời điểm in.
  4. NV kho cầm phiếu soạn hàng theo đúng lô ghi trên phiếu (FEFO đã chốt lúc đặt, BR-BH-11), đóng gói, dán phần nhãn giao lên thùng, rồi bấm "Đã đóng gói" (S19).
- **Luồng thay thế:**
  - 3a. Thiết bị tắt (ban đêm, mất điện, mất mạng): lệnh nằm ở "Chờ in", khi thiết bị bật lại thì **in lần lượt theo giờ thanh toán**. Không mất lệnh.
  - 3b. NV kho bấm **In lại** trên phiếu (kẹt giấy, mất phiếu): tạo lệnh in mới gắn cờ "In lại", ghi AuditLog người bấm (BR-GH-10).
  - 3c. Đơn bị huỷ **sau khi** đã in (S14): phiếu giấy vẫn còn ngoài kho. Console hiện phiếu "Đã huỷ theo đơn" (S19-AC4). Q13 quyết định có in thêm "phiếu huỷ" hay không (mặc định: không in, chỉ hiện trên console và trong khối "Cần chú ý").
  - 3d. Đơn bị huỷ **trước khi** in: lệnh chờ in bị bỏ, không in.
- **Ngoại lệ:**
  - E1. Webhook gửi lại, hoặc Chủ bấm xác nhận tay trùng: không phát sinh hoá đơn mới (BR-TT-03), nên **không có lệnh in thứ hai** (BR-GH-09).
  - E2. Thiết bị báo lỗi (hết giấy): lệnh chuyển "Lỗi in", kèm lý do. Hiện trong khối "Cần chú ý" (S24) để người ở kho xử lý và in lại.
  - E3. Thiết bị lấy lệnh xong nhưng mất mạng trước khi báo "Đã in": lần lấy sau có thể in trùng. Chấp nhận in trùng (thà in thừa 1 tờ còn hơn sót đơn). Phiếu có mã đơn và lần in để NV kho nhận ra bản trùng (PA).
  - E4. Lệnh "Chờ in" quá X phút (PA: 15') trong giờ làm việc: cảnh báo trong khối "Cần chú ý". Nếu không có cảnh báo này, việc thiết bị chết sẽ giống job TTL chết: không ai biết (so với BR-BH-04).
  - E5. Nội dung phiếu **không có** giá vốn, mã giá mua hay lãi (bất biến #1). Phần nhãn giao đi theo thùng tới tay khách, nên **không in số tiền** mà chỉ ghi "ĐÃ THANH TOÁN, không thu thêm". Điều này khớp S20-AC6 (NV giao không thấy tiền) và chặn việc thu thêm tiền ngoài sổ (PA, Q14).
- **Hậu điều kiện:** mỗi phiếu giao có lịch sử in (lần đầu tự động, các lần in lại), truy được ai in lại và lúc nào.

## 6. Business rule
| Mã | Nội dung | Nhãn | Mới / Sửa / Giữ |
|---|---|---|---|
| BR-TT-11 | Khách thanh toán **100% tổng đơn** trước khi đơn được soạn. **Không có đặt cọc, không có COD.** Tiền thiếu chỉ là ngoại lệ đi vào hàng chờ (BR-TT-04), không phải cọc | L | **Mới** (ghi nhận luật đang chạy, không đổi code) |
| BR-TT-04, 05, 08, 09, 10 | Giữ nguyên | D/PA | Giữ |
| BR-BH-09 | Địa chỉ giao bắt buộc **và có cấu trúc**: tỉnh/thành + phường/xã chọn từ danh mục địa giới **hiện hành** + chi tiết (số nhà, đường) | L + PA | **Sửa** |
| BR-BH-12 | Chỉ nhận đơn có địa chỉ **thuộc vùng giao đang mở**. Kiểm ở máy chủ **trước khi giữ chỗ**. Ngoài vùng thì từ chối, không giữ lô | L | **Mới** |
| BR-BH-13 | Vùng giao là **dữ liệu cấu hình do Chủ quản lý** (bật/tắt theo tỉnh, và theo xã nếu Q4 chọn), mỗi lần đổi ghi AuditLog. Không nằm cứng trong code. Đổi cấu hình không ảnh hưởng đơn đã tạo | L + PA | **Mới** |
| BR-BH-14 | SĐT khách được **chuẩn hoá** trước khi gộp `Customer`: bỏ khoảng trắng/dấu, đổi +84/84 thành 0. SĐT không hợp lệ thì từ chối | PA | **Mới** (sửa §7.1) |
| BR-BH-15 | **Khách thân quen**: khách đạt ngưỡng số đơn và/hoặc tổng tiền trong kỳ do Chủ cấu hình. Chỉ đếm đơn đã có hoá đơn, không bị huỷ. Tiền = hoá đơn − hoàn. Nhãn là giá trị **tính ra, không lưu tay** | L (định nghĩa) + PA (cách đếm) | **Mới** |
| BR-BH-16 | Nhãn thân quen **chỉ hiển thị nội bộ** (ERP) ở V1, không đổi giá. Nếu dùng cho ưu đãi thì phải qua quyết định mới (Q5) | PA | **Mới** (chờ Q5) |
| BR-BH-10 | Không có trường phí giao trên đơn | L | **Giữ, nhưng chờ Q2**: vùng giao tới 280 km làm câu hỏi phí giao sống lại |
| BR-GH-01, BR-GH-02 | NV nội bộ giao. Không định tuyến, không chi phí xe | D/L | **Giữ, nhưng chờ Q1** (mâu thuẫn quãng đường) |
| BR-GH-09 | Khi đơn được xác nhận đủ tiền, hệ thống tạo **đúng một** lệnh in tự động cho phiếu giao. Webhook gửi lại hay xác nhận trùng không tạo lệnh mới. Lệnh không in được thì giữ ở hàng chờ, không mất | L + PA | **Mới** |
| BR-GH-10 | In lại là thao tác có ghi AuditLog, dành cho `nv_kho`/`quan_ly`/`chu`. Nội dung in **không bao giờ** có giá vốn/lãi. Phần nhãn giao không in số tiền | PA | **Mới** |
| BR-HV-03 | Ngưỡng ngoài chuỗi lạnh (`COLD_CHAIN_MAX_HOURS`, hiện 6h) | PA | **Giữ, cần số thật** (Q3): quãng đường 250–280 km làm ngưỡng này thành ràng buộc thực |
| BR-DM-08 | PricingRule theo đơn (≥ M đồng) | PA | Giữ. Đủ dùng cho Y1 nếu Lộc muốn khuyến khích đơn ≥ 1 triệu, không cần code mới |

## 7. Tác động dữ liệu & tích hợp
*(Không thiết kế chi tiết; chỉ nêu cái bị đụng và lý do, để thoả bất biến #8.)*

**Y1: không có tác động dữ liệu.** Con số 700k–1tr là **thông tin quy mô**. BA dùng nó để:
- đối chiếu kinh tế giao hàng: đơn 700k chạy 280 km khó bù chi phí nếu mỗi chuyến chỉ giao ít đơn (xem Q1/Q2);
- làm giá trị mẫu cho test/seed (đơn 2–5 kg);
- gợi ý PricingRule "đơn ≥ 1.000.000đ" nếu Lộc muốn, dùng cơ chế đã có.

Không tự thêm ngưỡng tối thiểu/tối đa (Q11).

**Y2: không có tác động dữ liệu hay code.** Chỉ sửa tài liệu (URD §6.5, spec §7.4 thêm BR-TT-11) và nội dung Shop (thông báo "thanh toán 100%").

**Y3:**
- Cần nơi lưu **cấu hình tiêu chí** (ngưỡng đơn, ngưỡng tiền, HOẶC/VÀ, kỳ).
- Nhãn tính từ `SalesInvoice` + `Refund` theo `Customer`, không cần field mới trên `Customer` (nhãn tính ra).
- Cần chuẩn hoá SĐT (BR-BH-14) và **gộp các khách trùng đã có** trên production (việc dữ liệu một lần, có AuditLog).
- ERP: hiện **không có màn Khách hàng**, cần màn mới. S10 (danh sách/chi tiết đơn) thêm nhãn.

**Y4:**
- Cần thực thể **lệnh in / lịch sử in** gắn phiếu giao: trạng thái chờ/đã in/lỗi, lần in, người in lại.
- Cần **tác nhân máy in** có quyền hẹp.
- Máy in ở LAN kho, còn backend ở Cloud Run nên **backend không đẩy thẳng tới máy in được**. Mọi phương án khả thi đều theo kiểu **thiết bị ở kho chủ động hỏi lệnh**. Ba hướng để BE/Architect chọn (BA không chọn):
  - (a) một trang ERP console luôn mở trên máy ở kho, tự hỏi lệnh mới và in qua trình duyệt ở chế độ in không hỏi. Rẻ nhất, không thêm server. Đóng tab là ngừng in;
  - (b) một chương trình nhỏ chạy trên máy/mini-PC ở kho, hỏi API rồi in thẳng ra máy in nhiệt. Ổn định hơn, phải cài và bảo trì;
  - (c) dịch vụ in đám mây của bên thứ 3. Theo decisions 2026-09-09 thì **bắt buộc đi qua adapter FastAPI**, thêm chi phí và phụ thuộc.

  Hướng nào cũng cần E4 (cảnh báo lệnh chờ quá lâu). Production không có Celery/Redis nên đừng giả định có hàng đợi đẩy.
- Phụ thuộc story **S19** (chi tiết phiếu soạn có dòng hàng, kg, mã lô) vì nội dung phiếu in chính là dữ liệu của S19.

**Y5:**
- Cần **danh mục địa giới hành chính hiện hành** (tỉnh/thành + phường/xã sau sắp xếp 2025, mô hình 2 cấp) và cấu hình vùng giao.
- `SalesOrder` / `Customer` cần địa chỉ có cấu trúc (tỉnh, xã, chi tiết). **Đơn cũ giữ nguyên văn bản** và không bắt buộc chuyển đổi.
- Shop checkout đổi ô nhập. API `POST /api/shop/orders/` kiểm vùng. Giao diện mock Shop (`NEXT_PUBLIC_USE_MOCK`) cần có danh mục mẫu.
- ERP: S17 lọc/nhóm theo tỉnh để gom tuyến, S20 hiện tỉnh/xã.

**Về sáp nhập tỉnh 2025.** Biên bản dùng **tên tỉnh cũ**. BA ghi dưới đây theo Nghị quyết 202/2025/QH15, hiệu lực 01/07/2025. **Duy cần đối chiếu lại với văn bản gốc**, BA không có nguồn chính thức trong repo.

| Tên trong biên bản (cũ) | Tỉnh/thành hiện hành (theo hiểu biết của BA) | Ghi chú |
|---|---|---|
| Bình Thuận (kho Phan Thiết), **không có trong danh sách** | **Lâm Đồng** (Lâm Đồng + Đắk Nông + Bình Thuận) | Kho nay thuộc Lâm Đồng mới |
| Lâm Đồng, Đắk Nông | Lâm Đồng | |
| Ninh Thuận, Khánh Hòa | **Khánh Hòa** | |
| Bà Rịa – Vũng Tàu, Bình Dương, TP.HCM | **TP. Hồ Chí Minh** | |
| Đồng Nai, Bình Phước | **Đồng Nai** | |
| Đắk Lắk | **Đắk Lắk** (Đắk Lắk + **Phú Yên**) | Phần Phú Yên cũ có thể **vượt 300 km** |
| Long An | **Tây Ninh** (Tây Ninh + Long An) | Phần Tây Ninh cũ cần kiểm khoảng cách |
| Tiền Giang | **Đồng Tháp** (Đồng Tháp + Tiền Giang) | Phần Đồng Tháp cũ cần kiểm khoảng cách |

Hệ quả: 12 tỉnh cũ gom lại thành **7 tỉnh/thành mới**. Nếu chỉ kiểm theo tỉnh mới thì vô tình **mở thêm** vùng xa hơn 300 km (Phú Yên cũ, Tây Ninh cũ, Đồng Tháp cũ). Cấp huyện không còn, nên "quận/huyện" trong gợi ý nhập địa chỉ ở Shop đã lỗi thời. Đây là lý do Q4 là câu hỏi ĐỎ.

## 8. Rủi ro Cá Về
| Loại | Rủi ro | Giảm thiểu đề xuất |
|---|---|---|
| **Tiền** | Shop đang nhận đơn ở **bất kỳ địa chỉ nào**. Khách ngoài vùng trả tiền thì Lộc phải hoàn tay từng đơn (P-07), tốn công và mất uy tín | BR-BH-12 là **việc phải làm trước khi Shop nhận đơn thật** |
| **Tiền** | Giao 150–280 km mà phí giao "ngoài hệ thống" + "thanh toán 100% qua QR": phí giao chỉ còn cách thu **tiền mặt khi giao**, tức tiền ngoài sổ, mâu thuẫn tinh thần Y2 | Q2 phải trả lời trước launch. Nhãn giao ghi "không thu thêm" (Q14) |
| **Tiền** | Nếu nhãn thân quen dùng để giảm giá: khách không đăng nhập, **ai gõ SĐT của khách thân quen cũng hưởng ưu đãi** | BR-BH-16: V1 chỉ nhãn nội bộ. Ưu đãi chờ OTP hoặc quyết định chấp nhận rủi ro (Q5) |
| **Giá vốn** | Phiếu in, API lệnh in, API khách hàng là các serializer mới, dễ vô tình kèm `unit_cost` / lãi | Test "không có key giá vốn" cho mọi endpoint mới, như S19-AC5. Cấm `fields="__all__"` |
| **Phân quyền** | Máy in ở kho là **tài khoản kỹ thuật đăng nhập 24/7** trên một máy ai cũng chạm được. Nếu dùng tài khoản NV kho/Chủ thì ai đứng ở máy đó cũng có toàn quyền của người đó | Tài khoản riêng, quyền chỉ "lấy lệnh in / báo kết quả", thu hồi được (S42) |
| **Riêng tư** | Tổng tiền mua của từng khách là dữ liệu doanh thu. Nếu hiện nhãn thân quen trên Shop thì tiết lộ thói quen mua của người khác (nhập SĐT người khác là thấy) | Tổng tiền chỉ Chủ/Quản lý xem. Shop không hiện (Q10) |
| **Chứng từ / AuditLog** | Đổi vùng giao, đổi tiêu chí thân quen, in lại, gộp khách trùng: đều là thay đổi cần truy vết | AuditLog cho cả bốn (BR-PQ-04) |
| **Tồn / FEFO** | Kiểm vùng **sau** khi giữ chỗ làm khoá hàng oan tới hết TTL. Hàng đi 250–280 km + giao thất bại + đường về có thể vượt 6h nên **gần như luôn bị đề xuất huỷ bỏ** (BR-HV-03). Lỗ hàng hỏng dồn vào lô | Kiểm vùng trước giữ chỗ (BR-BH-12). Q3 cho số thật. Cân nhắc giao theo tuyến/ngày cố định để giảm số chuyến và số giờ ngoài lạnh |
| **Vận hành** | Thiết bị in chết mà không ai biết thì đơn đã trả tiền nằm chờ không ai soạn | E4 cảnh báo lệnh chờ quá hạn trong khối "Cần chú ý" |
| **Dữ liệu** | SĐT không chuẩn hoá nên đếm đơn thân quen sai **từ đơn đầu tiên**. Sửa sau phải gộp khách thủ công | BR-BH-14 làm trước launch, dù nhãn thân quen làm sau |
| **Nhất quán tài liệu** | Y5 va chạm 2 quyết định đã chốt (NV nội bộ; phí giao OUTSCOPE). BA **không sửa decisions.md** | Q1, Q2 cho Duy. Nếu đổi thì Duy ghi quyết định mới |

## 9. Ngoài phạm vi (của bản phân tích này)
- Tính phí giao theo khoảng cách, bản đồ, định vị, đo km (trừ khi Q2 chọn đưa phí vào đơn, lúc đó phân tích riêng).
- Định tuyến, tối ưu lộ trình, chi phí xe (BR-GH-02 giữ nguyên).
- Hoá đơn VAT/hoá đơn điện tử. "In đơn" ở đây là **phiếu soạn/nhãn giao nội bộ**, không phải hoá đơn thuế.
- Đăng nhập khách bằng OTP, chương trình tích điểm, hạng thành viên nhiều bậc.
- Tự động gửi tin nhắn cho khách thân quen.
- Đa kho (vẫn 1 kho Phan Thiết).

## 10. Đề xuất ưu tiên
| Ưu tiên | Việc | Lý do |
|---|---|---|
| **P0: trước khi Shop nhận đơn thật** | Trả lời Q1, Q2, Q3, Q4 | Chặn cả mô hình giao hàng và tiền |
| P0 | Story **N1** (danh mục địa giới + cấu hình vùng giao) và **N2** (Shop địa chỉ có cấu trúc + chặn ngoài vùng ở máy chủ) | Không có thì Shop thu tiền đơn không giao được |
| P0 | Story **N3** (chuẩn hoá SĐT + gộp khách trùng) | Rẻ. Để muộn thì dữ liệu bẩn tích luỹ, phá Y3 |
| P0 | Story **N4** (nội dung Shop: thanh toán 100%, vùng giao) + sửa URD/spec (BR-TT-11) | Gần như không tốn công |
| P0 (đã có trong backlog) | L10–L11: **S17, S18, S19, S20, S21** | Không có thì kho không có màn soạn/giao. Phiếu in dựa trên S19 |
| **P1: ngay sau S19, nên có trước launch** | Story **N5** (mẫu phiếu in + in tay/in lại từ chi tiết phiếu) | Tối thiểu để kho làm việc bằng giấy |
| P1 | Story **N6** (in tự động + hàng chờ in + cảnh báo) | Đúng yêu cầu Y4. Cần Q8 (thiết bị) |
| **P2: sau khi có dữ liệu đơn thật** | Story **N7** (cấu hình + nhãn khách thân quen) và **N8** (màn Khách hàng) | Ngưỡng chỉ có nghĩa khi đã có vài tuần đơn. N3 phải xong trước |
| Không làm | Y1 | Chỉ là thông tin quy mô, trừ khi Q11 đổi ý |

### Story mới đề xuất (PO viết chi tiết)
| Mã tạm | Tên | Loại | BR |
|---|---|---|---|
| N1 | Danh mục tỉnh/xã hiện hành + Chủ cấu hình vùng giao | BE+FE (ERP) | BR-BH-13 |
| N2 | Shop: địa chỉ có cấu trúc, chỉ đặt được trong vùng giao, kiểm ở máy chủ trước giữ chỗ | BE+FE (Shop) | BR-BH-09 (sửa), BR-BH-12 |
| N3 | Chuẩn hoá SĐT khi đặt + gộp khách trùng đã có | BE | BR-BH-14 |
| N4 | Nội dung Shop: thanh toán 100%, không cọc/COD, vùng giao | FE (Shop) + tài liệu | BR-TT-11 |
| N5 | Phiếu soạn + nhãn giao khổ in (Q8), in tay / in lại, không giá vốn, không tiền trên nhãn | BE+FE | BR-GH-10 |
| N6 | Lệnh in tự động khi thanh toán, thiết bị kho lấy lệnh, trạng thái chờ/đã in/lỗi, cảnh báo | BE+FE (+ thiết bị) | BR-GH-09 |
| N7 | Cấu hình tiêu chí khách thân quen + nhãn trên đơn | BE+FE | BR-BH-15, 16 |
| N8 | Màn Khách hàng: danh sách, chi tiết, số đơn/tổng tiền theo kỳ | BE+FE | BR-BH-15 |

### Sửa story cũ trong backlog (`2026-09-24-erp-console-noi-that/02-stories.md`)
| Story | Sửa gì |
|---|---|
| S10 | Thêm nhãn thân quen (sau N7); hiện tỉnh/xã |
| S17 | Lọc và nhóm theo tỉnh/thành để gom tuyến; cột "đã in / lỗi in" |
| S19 | Thêm nút In / In lại, trạng thái in. AC mới: phiếu CANCELLED sau khi đã in |
| S20 | Thẻ phiếu hiện tỉnh/xã rõ ràng (NV giao đi liên tỉnh) |
| S23 | Khi Q3 có số: đề xuất sẵn "Huỷ bỏ" (đang ở "Để sau") trở nên quan trọng vì quãng đường dài |
| S24 | Thêm key "lệnh in lỗi/chờ quá lâu" |
| S40 | Chỉ khi Q5 chọn ưu đãi cho khách thân quen: PricingRule thêm điều kiện nhóm khách |

## 11. Câu hỏi mở
| # | Mức | Câu hỏi | Mặc định PA đề xuất |
|---|---|---|---|
| Q1 | **ĐỎ** | Giao tới các tỉnh cách 150–280 km (Nha Trang, Buôn Ma Thuột, Tiền Giang…) có **vẫn 100% do nhân viên nội bộ tự chạy xe** không? Hay cho phép gửi xe khách, chành xe lạnh, đơn vị vận chuyển cho tuyến xa? Quyết định 2026-09-09 đang ghi "nhân viên nội bộ, không thuê ngoài". | Giữ NV nội bộ. Giao **theo tuyến, theo ngày cố định cho từng vùng** (gom đơn) để một chuyến 250 km chở nhiều đơn. Hệ thống không đổi mô hình phiếu giao. Nếu dùng bên vận chuyển thì Duy ghi quyết định mới, BA phân tích riêng (mã vận đơn, người giao không phải `User`) |
| Q2 | **ĐỎ** | Khi đã thanh toán 100% qua QR, **phí giao** cho đơn 700k–1tr đi xa xử lý thế nào? (a) miễn phí giao, đã tính vào giá bán; (b) NV thu tiền mặt phí giao khi giao, ngoài hệ thống; (c) đưa phí giao vào đơn và vào QR (lật BR-BH-10 và quyết định "phí giao OUTSCOPE"). | **(a)**: giữ BR-BH-10, không tiền ngoài sổ, nhãn giao ghi "không thu thêm". Nếu chọn (c) thì cần quyết định mới + phân tích bảng phí theo vùng |
| Q3 | **ĐỎ** | Hàng đông lạnh được phép **ngoài kho lạnh tối đa bao nhiêu giờ** (đi đường + chờ khách) thì vẫn giao được, và nếu mang về thì còn tái nhập được? Có dùng thùng đá khô/xe lạnh cho tuyến xa không? (Hiện hệ thống giả định 6h, là câu hỏi mở #3 cũ. Đường 280 km mất khoảng 5–6h một chiều.) | Giữ 6h cho hàng mang về (BR-HV-03). Việc giữ lạnh khi đi xa là thao tác vận hành, hệ thống không theo dõi. Chủ nên đóng thùng giữ lạnh ≥ 10h cho tuyến > 200 km |
| Q4 | **ĐỎ** | Danh sách tỉnh trong biên bản dùng **tên trước sáp nhập 2025**, gom lại chỉ còn 7 tỉnh/thành mới (bảng mục 7), trong đó Đắk Lắk mới gồm cả Phú Yên cũ, Tây Ninh mới gồm Long An, Đồng Tháp mới gồm Tiền Giang. Kiểm vùng giao **ở cấp tỉnh mới** (đơn giản, nhưng mở thêm vùng > 300 km) hay **ở cấp phường/xã** (đúng 300 km, nhưng Chủ phải bật/tắt nhiều xã)? Và Duy xác nhận bảng quy đổi ở mục 7. | **Cấp tỉnh mới** để ra mắt nhanh, với 7 tỉnh: Lâm Đồng, Khánh Hòa, TP.HCM, Đồng Nai, Đắk Lắk, Tây Ninh, Đồng Tháp. Kèm khả năng **tắt riêng từng phường/xã** ở tỉnh rộng (Đắk Lắk, Tây Ninh, Đồng Tháp). Đơn lọt vùng quá xa thì Chủ huỷ và hoàn (UC-1 E4) |
| Q5 | **ĐỎ** | Nhãn **khách thân quen dùng để làm gì**? (a) chỉ để nhận diện nội bộ trên ERP (gọi điện chăm sóc, ưu tiên khi thiếu hàng); (b) giảm giá/giá riêng trên Shop; (c) ưu tiên soạn/giao trước. Lưu ý: khách không đăng nhập, chọn (b) thì ai gõ SĐT của khách quen cũng được giảm. | **(a)** cho V1 (BR-BH-16). (b) để sau khi có OTP. (c) chỉ là thứ tự hiển thị trên S17, làm được nếu Duy muốn |
| Q6 | VÀNG | Tiêu chí: **HOẶC** (đạt số đơn hoặc đạt số tiền) hay **VÀ**? Kỳ là **trượt N ngày tính tới hôm nay** hay **theo tháng/quý dương lịch**? | Chủ chọn được HOẶC/VÀ, mặc định **HOẶC**. Mỗi ngưỡng có thể bỏ trống. Kỳ **trượt N ngày**, Chủ đặt N, mặc định **90**. Ngưỡng gợi ý khi chưa có dữ liệu: ≥ 3 đơn **hoặc** ≥ 3.000.000đ / 90 ngày (≈ 3 đơn cỡ Y1) |
| Q7 | VÀNG | Đếm từ đơn nào? | Đơn đã có hoá đơn bán (đã thanh toán đủ), **không** bị huỷ. Tiền = hoá đơn − hoàn (hoàn chưa Thất bại). Mốc kỳ = thời điểm ghi doanh thu. **Không** chờ giao xong (code chưa có trạng thái đơn Hoàn tất) |
| Q8 | **ĐỎ** | **In ở đâu, bằng thiết bị gì, ai trực?** Ở kho Phan Thiết có máy tính/điện thoại luôn bật và máy in không? Loại máy in: nhiệt 80 mm, nhiệt 58 mm, hay A5 laser? Có cần nhãn **decal chịu ẩm** dán thùng đá không? In cả ngoài giờ (đơn lúc 22h) hay chỉ trong giờ làm? | Một **máy in nhiệt 80 mm** tại kho, nối với một máy luôn bật. In một tờ gồm **phần soạn hàng** (mặt hàng, kg, mã lô, hạn dùng, mã đơn) và **phần nhãn giao** cắt rời (tên, SĐT, địa chỉ, mã đơn, "ĐÃ THANH TOÁN"). Đơn ngoài giờ được xếp hàng, in khi máy bật. Giấy decal nhiệt cho nhãn là việc mua sắm, ngoài hệ thống |
| Q9 | VÀNG | Shop có cần hiện **ngày giao dự kiến / lịch giao theo vùng** không (ví dụ "Nha Trang: giao thứ 3 và thứ 6")? | Có, dạng **ghi chú văn bản** Chủ nhập cho từng vùng (UC-2 bước 3). Không tính ngày tự động |
| Q10 | VÀNG | Ai thấy nhãn thân quen và tổng tiền của khách? | Nhãn: Chủ, Quản lý, NV kho. **Không** hiện cho NV giao, **không** hiện trên Shop. Tổng tiền/số đơn trong kỳ: chỉ Chủ và Quản lý |
| Q11 | VÀNG | Con số 700k–1tr có nghĩa là **đặt ngưỡng đơn tối thiểu** (ví dụ không nhận đơn < 500k, hoặc tối thiểu cao hơn cho vùng xa) không? | **Không chặn**, chỉ là thông tin quy mô. Nếu muốn khuyến khích thì Chủ tự tạo PricingRule "đơn ≥ M đồng" (đã có) |
| Q12 | VÀNG | Ai được cấu hình vùng giao và tiêu chí thân quen? | **Chỉ Chủ** (đổi phạm vi bán và đối tượng ưu đãi). Quản lý chỉ xem |
| Q13 | VÀNG | Đơn bị huỷ sau khi phiếu đã in: có in "phiếu huỷ" để kho bỏ tờ cũ không? | Không in. Hiện "Đã huỷ theo đơn" trên console (S19-AC4) và trong "Cần chú ý" |
| Q14 | VÀNG | Nhãn giao dán thùng (khách thấy) có in giá/tổng tiền không? | **Không in tiền**, chỉ "ĐÃ THANH TOÁN, không thu thêm" (khớp S20-AC6, chặn thu thêm ngoài sổ). Nếu khách cần chứng từ có giá thì tra đơn trên Shop |
| Q15 | VÀNG | Chủ tắt một vùng khi còn đơn đã thanh toán ở vùng đó? | Đơn đã tạo **vẫn giao**, cấu hình chỉ áp dụng cho đơn mới |
| Q16 | VÀNG | Phan Thiết/Bình Thuận cũ (nơi đặt kho) không có trong danh sách biên bản. Có giao nội thành Phan Thiết không? | **Có**, thuộc Lâm Đồng mới, mở mặc định |
| Q17 | XANH | Phí giao theo khoảng cách/vùng trong hệ thống | Để sau, phụ thuộc Q2 |
| Q18 | XANH | Gộp tay 2 SĐT của cùng một người vào một khách; đăng nhập OTP cho khách | Để sau |
| Q19 | XANH | Đơn chuyển khoản 2 lần (thiếu rồi bù): hệ thống tự xác nhận khi **tổng** đủ thay vì chờ Chủ bấm (S12) | Để sau. Hiện Chủ bấm tay, an toàn và khớp 100% |

---
## Quyết định của Duy (2026-09-26), đợt 1
| # | Quyết định |
|---|---|
| Q1 | Giao các tỉnh xa (150–280 km) bằng cách **thuê đơn vị vận chuyển**. Quyết định này lật "100% NV nội bộ" (decisions 2026-09-09) cho các tuyến xa. BA/PO phải làm rõ: tuyến gần vẫn giao bằng NV nội bộ hay không, cách ghi nhà vận chuyển và mã vận đơn, trạng thái giao, và chuỗi lạnh. |
| Q2 | Phí giao **miễn phí, tính sẵn vào giá bán**. Nhãn giao ghi "không thu thêm". Không có khoản tiền nào ngoài sổ. |
| Q4 | Vùng giao **cho phép chọn cả hai kiểu địa chỉ: trước sáp nhập (tỉnh cũ) và sau sáp nhập 2025 (tỉnh mới)**. Hệ thống quy về cùng một vùng giao để kiểm. Cần bảng quy đổi tỉnh cũ ↔ tỉnh mới (mục 7), Duy xác nhận. |
| Q5 | Khách thân quen **chỉ là nhãn nhận diện nội bộ trên ERP (V1)**, chưa có ưu đãi. |
| Q3, Q8 | Còn chờ Duy trả lời: giờ chuỗi lạnh tối đa; thiết bị và máy in ở kho. |

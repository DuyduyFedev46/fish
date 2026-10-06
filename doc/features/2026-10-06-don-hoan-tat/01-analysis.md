# Đơn hoàn tất (W37) — Phân tích nghiệp vụ
> BA · 2026-10-06 · Trạng thái: **CHỜ DUYỆT**

## 1. Yêu cầu gốc
> "W37 (đơn giao xong vẫn 'Đang xử lý'): chạy luồng ĐẦY ĐỦ (BA → PO → Tech Lead) trước khi code."
> — Duy chốt, `decisions.md` 2026-10-06 (tối).

Phát hiện từ rà soát `doc/thuat-ngu-va-trang-thai.md` §2.10 (W37) và §2.11. Không có code nào chuyển đơn sang
`PAID` hay `COMPLETED`, chỉ `seed_demo` làm việc đó. Giao xong, đơn vẫn "Đang xử lý" trên cả ERP và Shop.

## 2. Tóm tắt
**Lộc, Quản lý và khách** cần đơn tự sang **"Hoàn tất"** khi hàng đã giao tới tay khách, để: khách tra đơn thấy đúng kết
cục; danh sách "Chưa xong" và Tổng quan chỉ đếm việc còn phải làm; và **lô bán qua đơn thật chốt được** (hiện bị chặn
vĩnh viễn, xem §3.3).

Đây là **sửa P-05 / P-06 đã có**, không phải quy trình mới. Spec đã vẽ cạnh `DangXuLy → HoanTat: Delivery Note hoàn tất`
(spec §7.2) nhưng code chưa làm.

## 3. Bối cảnh trong hệ thống

- **Quy trình:** P-05 (spec §7.2 state machine đơn), P-06 (§8 phiếu giao), P-07 (§9 huỷ, hoàn tiền), P-08 (§10 hàng hoàn),
  P-04 (BR-LO-04 chốt lô), P-10 (§12 báo cáo).
- **Rule hiện có:** BR-GH-05 (Hoàn tất là điểm không quay lui), BR-TT-06 / BR-BC-01..03 (doanh thu ghi lúc xác nhận thanh
  toán, kỳ cũ không sửa), BR-HT-02/04/06/10 (hoàn một phần, chứng từ đảo), BR-LO-04 (chốt lô khi không còn đơn đang mở),
  BR-PQ-04/05 (AuditLog), BR-PQ-11 (đơn chỉ Hệ thống tạo).
- **Quyết định ràng buộc:**
  - `decisions.md` 2026-09-26: V1 **chỉ VietQR, thanh toán 100% trước**, không COD, không cọc. Chỉ IPN `ORDER_PAID` xác
    nhận được thanh toán.
  - 2026-09-26: Shop chưa mở công khai, dữ liệu hiện có là dữ liệu thử, phải dọn DB trước khi mở.
  - 2026-09-30 (BR-HT-06, phương án B): không sửa số kỳ cũ. Memory "Không sửa số kỳ cũ": điều chỉnh ghi vào kỳ hiện tại.
  - 2026-10-06 (tối): lô dọn chữ (gom nhãn về một nguồn) và bảng tên chứng từ do PO đề xuất chạy song song.
- **Liên quan đang chờ duyệt:** `doc/features/2026-10-01-huy-don-dang-giao/01-analysis.md` (CHỜ DUYỆT). Đề xuất huỷ đơn khi
  phiếu Đang giao và BR-GH-24 (một phiếu chỉ có một kết cục, chống ghi đè khi bấm đồng thời). W37 chạm cùng thời điểm
  "phiếu sang Hoàn tất", nên hai hồ sơ phải khớp nhau (xem §8).

### 3.1 Trạng thái đơn hiện có và ý nghĩa thật (đọc code)

`SalesOrder.Status`, file `backend/apps/sales/models/orders.py:13`:

| Mã | Nhãn | Ý nghĩa theo spec §7.2 | Ý nghĩa **thực tế** trong code | Ai đổi sang, ở đâu |
|---|---|---|---|---|
| `BOOKED` | Giữ chỗ | Khách đặt, giữ kg trong lô | Đúng như spec | Hệ thống, `POST /api/shop/orders/` |
| `PAID` | Đã thanh toán | Webhook xác nhận đủ tiền, chưa trừ kho | **Không bao giờ có.** Code đi thẳng `BOOKED → PROCESSING` trong cùng một giao dịch với xuất hoá đơn và trừ kho (`payments/services.py:321`, comment "PAID -> PROCESSING"; `_issue_and_close` dòng 619) | Không ai (chỉ `seed_demo`) |
| `PROCESSING` | Đang xử lý | Đã trừ kho và ghi doanh thu | Đã thanh toán đủ, có hoá đơn, có phiếu giao. **Ở đây mãi sau khi giao xong** | Hệ thống (IPN khớp đủ, `_record_payment`); Chủ (`confirm_payment_manual`, `resolve_payment` ATTACH/CONFIRM) |
| `COMPLETED` | Hoàn tất | Phiếu giao hoàn tất | **Không bao giờ có** | Không ai (chỉ `seed_demo`) |
| `CANCELLED` | Đã huỷ | `cancel_paid_order` (P-07) | Đúng như spec. Đến được từ `PAID`/`PROCESSING`, chặn khi phiếu Đang giao hoặc Hoàn tất | Chủ/Quản lý (`sales.cancel_paid_order`); Hệ thống (`UNREACHABLE_AUTO`, `confirmation/services.py:757`) |
| `AUTO_CANCELLED` | Tự huỷ (quá TTL) | Quá 30' không có tiền | Đúng như spec | Hệ thống, job `cancel_expired_orders` |

Điểm chuyển duy nhất của phiếu giao sang `COMPLETED` là `delivery/services.py:advance_status` (gọi từ `delivery/api.py:198`).
Hàm này chỉ đổi phiếu, ghi `completed_at` và AuditLog `delivery_advance_status`. Hàm **không đụng đơn**, và đọc phiếu
**không khoá dòng** (đã nêu ở hồ sơ huỷ-đơn-đang-giao, dòng 59).

Số phiếu giao trên một đơn: hiện **luôn là 1**. `create_delivery_note` chỉ được gọi từ `confirmation/services.py:start_confirmation`,
và hàm này idempotent theo hoá đơn. Model thì cho phép nhiều phiếu (`invoice.delivery_notes`). Mọi chỗ đọc (Shop tra đơn,
huỷ đơn, next_steps) đều lấy **phiếu mới nhất**.

### 3.2 Báo cáo tiền không đọc trạng thái đơn (đã kiểm)

- Lãi lỗ theo kỳ và theo lô (`reports/services.py`, `period_counts.py`, `batch_list.py`): đọc `SalesInvoice.status=ISSUED`
  theo `issued_at`, `SalesCreditNote` theo `issued_at`, `Refund.status=REFUNDED` theo `confirmed_at`. **Không có dòng nào lọc
  theo `SalesOrder.status`.**
- Doanh thu hôm nay ở Tổng quan (`dashboard_api.py:59`): hoá đơn ISSUED trừ chứng từ đảo lập hôm nay. Không đọc trạng thái đơn.

⇒ Chuyển đơn sang Hoàn tất (kể cả chuyển bù đơn cũ) **không làm đổi một con số doanh thu, giá vốn hay lãi lỗ nào, ở kỳ nào.**

### 3.3 Hệ quả của lỗ W37 ngoài chữ hiển thị (nặng hơn mô tả ban đầu)

| # | Chỗ | Hệ quả hiện tại | Mức |
|---|---|---|---|
| H1 | **Chốt lô** `inventory/batches/services.py:164,208`: `OPEN_ORDER_STATUSES = ("BOOKED","PAID","PROCESSING")` | Mọi lô từng bán qua đơn thật luôn có ≥1 đơn `PROCESSING` tham chiếu ⇒ "Còn N đơn đang mở tham chiếu lô" ⇒ **không chốt được lô nào** đã bán qua Shop. Lãi lỗ lô mãi "tạm tính" (BR-BC-05), không đông cứng được (BR-LO-05) | **Cao** |
| H2 | Tổng quan `dashboard_api.py:24,66`: `pending_count` đếm `BOOKED+PAID+PROCESSING` | Số "đơn chưa xong" chỉ tăng, không giảm | TB |
| H3 | ERP Đơn hàng, bộ lọc mặc định "Chưa xong" = `BOOKED,PAID,PROCESSING` (`erp-console/features/orders/labels.ts:5`) | Đơn đã giao lẫn vào việc cần làm | TB |
| H4 | Shop tra đơn `orders/shop_api.py:85` | Khách đã nhận hàng vẫn thấy "Đang xử lý" | TB (khách thấy) |
| H5 | ERP chi tiết đơn `orderDetailModel.ts:90` | Nút chính "Lập phiếu hoàn" cho đơn Hoàn tất không bao giờ hiện. Thanh bước thì đã tự suy "Hoàn tất" từ phiếu giao (dòng 47), nên **thanh bước và chip trạng thái đang nói hai điều khác nhau** | Thấp |
| H6 | PV (phạm vi dữ liệu, đang thiết kế): `02b-tech-design.md:184` đếm `rows_losing_access` là đơn `BOOKED|PAID|PROCESSING` | Số "dòng sẽ mất quyền xem" bị thổi phồng bởi đơn đã giao | Thấp (chưa code) |

## 4. Tác nhân & quyền

| Tác nhân | Group | Làm được gì với W37 | Quyền Tầng 2 cần |
|---|---|---|---|
| Hệ thống | `actor=None` | Chuyển đơn `PROCESSING → COMPLETED` khi điều kiện BR-BH-18 đủ. Chuyển bù đơn cũ | — |
| NV giao | `delivery_staff` | Bấm "Hoàn tất" trên phiếu được gán (như hiện nay). **Không** đổi trạng thái đơn trực tiếp | `change_deliverynote` (Tầng 1, có sẵn) |
| Quản lý / Chủ | `manager` / `owner` | Như NV giao trên mọi phiếu. Sau khi đơn Hoàn tất: lập phiếu hoàn (Quản lý, Chủ), xác nhận hoàn (Chủ) | `create_refund`, `confirm_refund` (có sẵn) |
| Khách | không phải User | Tra đơn thấy "Hoàn tất" | — (API công khai, giữ xác minh mã đơn + 4 số cuối SĐT, giới hạn tần suất) |

Không có quyền mới. Không ai được **bấm tay** "Hoàn tất đơn": đơn do Hệ thống quản (BR-PQ-11), con đường duy nhất là phiếu giao (PA).

## 5. Use case

### UC-1 Giao xong một đơn đã trả trước 100% qua VietQR (đường chính, chiếm gần như mọi đơn V1)
- **Tiền điều kiện:** đơn `PROCESSING`, hoá đơn `ISSUED`, phiếu giao `DELIVERING`, đơn không bị huỷ. V1 không có COD, nên
  "có phiếu giao" đã kéo theo "đã thu đủ tiền" (hoá đơn chỉ lập khi đủ tiền, `_record_payment` / `_issue_and_close`).
- **Luồng chính:**
  1. NV giao bấm "Hoàn tất" trên phiếu.
  2. Hệ thống chuyển phiếu `DELIVERING → COMPLETED`, ghi `completed_at` (như hiện nay).
  3. **Trong cùng giao dịch**, Hệ thống xét đơn theo BR-BH-18. Đơn chỉ có một phiếu và phiếu vừa Hoàn tất ⇒ đơn `PROCESSING → COMPLETED`.
  4. Ghi AuditLog cho đơn: Hệ thống, `from/to`, mã phiếu giao gây ra. Không chép SĐT hay địa chỉ (bất biến 9).
  5. Dòng thời gian đơn hiện "Giao hàng thành công (mã phiếu)" như hiện nay, cộng mốc "Đơn hoàn tất". PO quyết có gộp
     hai mốc thành một dòng hay không.
- **Luồng thay thế:**
  - 3a. Đơn có từ hai phiếu trở lên (chưa có trong V1, xem UC-4) và còn phiếu chưa kết thúc ⇒ đơn giữ `PROCESSING`.
- **Ngoại lệ:**
  - E1. Đơn đã `CANCELLED` (bị huỷ ngay trước đó): phiếu **không** được sang Hoàn tất. Từ chối với thông báo "Đơn đã huỷ
    — mang hàng về kho" (khớp BR-GH-24 của hồ sơ huỷ-đơn-đang-giao). Đơn không bao giờ được thành `COMPLETED` sau `CANCELLED`.
  - E2. Bấm hai lần, mạng rớt rồi gửi lại: lần sau trả "đã hoàn tất", không ghi AuditLog lần hai (idempotent như `from_status` hiện có).
  - E3. Lỗi khi đổi đơn ⇒ cả thao tác rollback, phiếu cũng không sang Hoàn tất. Hai trạng thái không được lệch nhau.
- **Hậu điều kiện:** phiếu `COMPLETED`, đơn `COMPLETED`, **không đổi** hoá đơn, kho, doanh thu, giá vốn. Lô không còn bị
  đơn này chặn chốt (H1).

### UC-2 Giao thất bại
- **Tiền điều kiện:** phiếu `DELIVERING`.
- **Luồng chính:** NV giao báo thất bại ⇒ phiếu `FAILED`, đơn **giữ `PROCESSING`**, vì giao lại vẫn có thể xảy ra (BR-GH-04).
- **Luồng thay thế:**
  - a. Hẹn giao lại: `FAILED → DELIVERING → COMPLETED` ⇒ quay về UC-1.
  - b. Thôi không giao: Chủ/Quản lý huỷ đơn lý do `GIVE_UP_AFTER_FAILED` ⇒ đơn `CANCELLED`, phiếu `CANCELLED`, có chứng từ
    đảo doanh thu ở kỳ huỷ, hàng về qua P-08 (như hiện nay). **Không** qua `COMPLETED`.
  - c. Hệ thống tự huỷ do không liên lạc được (`UNREACHABLE_AUTO`) ⇒ như b.
- **Ngoại lệ:** đơn `FAILED` để lâu không ai quyết ⇒ vẫn là việc chưa xong, phải hiện ở "Chưa xong" và Tổng quan. Đó là
  hành vi đúng, không phải lỗi.
- **Hậu điều kiện:** không có đơn nào sang Hoàn tất khi phiếu chưa `COMPLETED`.

### UC-3 Hoàn tiền một phần hoặc toàn phần sau khi đơn đã Hoàn tất (khách khiếu nại hàng)
- **Tiền điều kiện:** đơn `COMPLETED`, `refundable_amount(invoice) > 0`.
- **Luồng chính:**
  1. Quản lý hoặc Chủ lập phiếu hoàn (nút chính "Lập phiếu hoàn" ở ERP, nhánh `orderDetailModel.ts:90` nay mới chạy được).
  2. Chủ xác nhận hoàn với mã giao dịch (BR-HT-03).
  3. **Đơn giữ `COMPLETED`.** Phiếu hoàn là dòng tiền riêng (BR-HT-01), trừ vào **kỳ xác nhận hoàn** (BR-BC-03, BR-HT-06
     nhánh "hoá đơn chưa có chứng từ đảo").
- **Ngoại lệ:** huỷ đơn `COMPLETED` bị chặn (BR-GH-05, như hiện nay). Hoàn vượt số đã thu bị chặn (BR-HT-04).
- **Hậu điều kiện:** đơn `COMPLETED`, ERP hiện kèm thông tin "đã hoàn x đ" (PO quyết cách hiện). Hàng khách trả lại tận tay
  sau khi giao **không** có luồng nhập kho (ngoài phạm vi, §9).

### UC-4 Đơn nhiều phiếu giao (chuẩn bị trước, V1 chưa phát sinh)
- **Tiền điều kiện:** một hoá đơn có từ hai phiếu giao trở lên. Hiện code không sinh ra trường hợp này, nhưng model cho phép.
- **Luồng chính:** đơn sang `COMPLETED` khi **mọi phiếu chưa huỷ đều đã `COMPLETED`, và có ít nhất một phiếu `COMPLETED`**.
- **Luồng thay thế:** một phiếu `COMPLETED`, một phiếu `FAILED` ⇒ đơn giữ `PROCESSING` tới khi phiếu kia kết thúc.
- **Ngoại lệ:** mọi phiếu đều `CANCELLED` mà đơn không bị huỷ. Trạng thái này không hợp lệ, đơn giữ `PROCESSING` để người xử lý thấy.
- **Hậu điều kiện:** luật không đổi khi sau này có giao nhiều chuyến.

### UC-5 Chuyển bù đơn cũ đang kẹt "Đang xử lý"
- **Tiền điều kiện:** đơn `PROCESSING` có phiếu giao thoả BR-BH-18 (phiếu `COMPLETED`) từ trước khi tính năng lên.
- **Luồng chính:** Hệ thống chạy một lần (chạy lại an toàn) chuyển các đơn đó sang `COMPLETED`. Mỗi đơn có một dòng AuditLog
  Hệ thống, đánh dấu "chuyển bù W37" và kèm mã phiếu giao.
- **Ngoại lệ:** chạy lại lần hai không đổi gì, không ghi AuditLog lần hai. Đơn `PAID` (chỉ có ở `seed_demo`) không động tới.
- **Hậu điều kiện:** không đổi hoá đơn, kho hay báo cáo (§3.2). Lô cũ hết bị chặn chốt (H1).

## 6. Business rule

| Mã | Nội dung | Nhãn | Mới / Sửa / Giữ |
|---|---|---|---|
| **BR-BH-18** | Đơn `PROCESSING` sang **Hoàn tất** khi mọi phiếu giao chưa huỷ của hoá đơn đều đã Hoàn tất, và có ít nhất một phiếu Hoàn tất. Hệ thống chuyển trong **cùng giao dịch** với thao tác làm phiếu cuối cùng sang Hoàn tất. Đơn đã huỷ không bao giờ sang Hoàn tất, và phiếu của đơn đã huỷ không sang Hoàn tất được. Không ai bấm tay "Hoàn tất đơn". | D (spec §7.2 đã vẽ cạnh này) + PA (điều kiện nhiều phiếu, cùng giao dịch) | **Mới** (hiện thực hoá §7.2) |
| **BR-BH-19** | V1 trả trước 100%, nên điều kiện "đã thu đủ tiền" được bảo đảm từ lúc có hoá đơn. Hoàn tất **không** xét lại tiền và không xét phiếu hoàn đang chờ. | D (decisions 26/09) + PA | **Mới** |
| **BR-BH-20** | Đơn Hoàn tất vẫn lập phiếu hoàn được (một phần hoặc toàn phần), trạng thái đơn **không đổi** vì hoàn tiền. Huỷ đơn Hoàn tất bị chặn (BR-GH-05). | PA (theo BR-GH-05, BR-HT-01) | **Mới** |
| **BR-BH-21** | Trạng thái `PAID` "Đã thanh toán" **không dùng** ở V1. Thanh toán đủ, xuất hoá đơn và trừ kho là một bước, đơn sang thẳng "Đang xử lý". Bước con (chờ gọi xác nhận, soạn, giao) đọc từ phiếu giao. Giữ mã trong DB, không xoá, ẩn khỏi bộ lọc và thanh bước (Q2). | PA | **Mới**. **Sửa** spec §7.2 (bỏ hai cạnh qua `DaThanhToan`) |
| **BR-BC-06** | Trạng thái đơn **không** là nguồn của số tiền. Doanh thu, giá vốn, hoàn tiền tính theo hoá đơn, chứng từ đảo, phiếu hoàn và thời điểm của chúng (BR-BC-01..03). Đổi trạng thái đơn, kể cả chuyển bù, không làm đổi số kỳ nào. | D (BR-BC-01..03, quyết định "không sửa kỳ cũ") | **Mới** (ghi rõ điều đang đúng) |
| BR-LO-04 | "Đơn đang mở" = Giữ chỗ, Đã thanh toán, Đang xử lý. Đơn Hoàn tất **không** chặn chốt lô. | Đã có | Giữ (text không đổi, nay mới đúng trong thực tế) |
| BR-GH-05 | Hoàn tất là điểm không quay lui, áp cho cả phiếu và đơn | Đã có | Giữ (mở rộng phạm vi sang đơn) |
| BR-GH-24 | Một phiếu chỉ có một kết cục. Hoàn tất, Giao thất bại và Huỷ xét trạng thái mới nhất lúc ghi | PA, hồ sơ 2026-10-01 CHỜ DUYỆT | **Phụ thuộc**: BR-BH-18 cần phần "không ghi đè" của rule này, kể cả khi hồ sơ huỷ-đơn-đang-giao chưa duyệt |
| BR-PQ-04/05 | Đổi trạng thái đơn ghi AuditLog | Đã có | Giữ |

## 7. Tác động dữ liệu & tích hợp

Không thiết kế chi tiết. Tech Lead chốt ở 02b.

- **Model:** không thêm field ở mặc định (Q6). `COMPLETED` đã có trong `choices`. Mốc "hoàn tất lúc" lấy từ
  `DeliveryNote.completed_at` của phiếu cuối. Nếu Tech Lead cần `SalesOrder.completed_at`, phải ghi lý do (bất biến 8).
- **Dữ liệu:** một bước chuyển bù đơn cũ, chạy lại an toàn (UC-5). Phạm vi thực tế nhỏ vì DB production là dữ liệu thử,
  phải dọn trước khi mở Shop (decisions 26/09).
- **Backend chạm:** điểm hoàn tất phiếu (`delivery/services.py:advance_status`); hằng "đơn đang mở / chưa xong" ở
  `inventory/batches/services.py:164` và `reports/dashboard_api.py:24` (giữ nguyên danh sách, chỉ cần dữ liệu đúng);
  `orders/shop_api.py` tra đơn; `orders/timeline.py` thêm mốc; `orders/next_steps.py` (đơn Hoàn tất: chỉ còn "Lập phiếu hoàn").
- **ERP:** danh sách đơn và bộ lọc (`labels.ts`: "Chưa xong" giữ nghĩa, bỏ lựa chọn "Đã thanh toán" nếu Q2 = A); chi tiết
  đơn (`orderDetailModel.ts`: chip và thanh bước phải nói cùng một điều; nhánh "Lập phiếu hoàn" cho `COMPLETED`); Tổng quan
  (số "đơn chưa xong" giảm khi giao xong; danh sách đơn gần đây hiện nhãn Hoàn tất); hồ sơ khách (`customers` đếm đơn, không
  đổi logic); mock FE phải sinh đơn `COMPLETED` đúng luật thay vì gán cứng.
- **Shop:** tra đơn hiện nhãn Hoàn tất (hoặc nhãn PO chốt ở bảng tên, Q5). Không thêm dữ liệu cá nhân nào vào phản hồi.
- **AI (đang tắt):** không có lệnh AI nào đọc hay ghi trạng thái đơn trong `apps/ai` (đã grep). Khi bật lại, lệnh "đơn chưa
  xong" phải dùng cùng định nghĩa. Không có việc ngay.
- **PV (phạm vi dữ liệu, đang thiết kế):** `rows_losing_access` đếm đơn `BOOKED|PAID|PROCESSING` sẽ tự đúng khi W37 xong.
  Thứ tự làm không ràng buộc nhau, chỉ cần báo Tech Lead của PV. Cửa sổ 7 ngày NV giao xem dữ liệu khách (`pii_scope.py`)
  tính theo `DeliveryNote.completed_at`, **không đổi**.
- **Bên thứ ba:** không. SePay không bị ảnh hưởng. Tiền về sau khi đơn Hoàn tất vẫn rơi vào `OVERPAID` → hàng chờ Chủ,
  như mọi đơn khác `BOOKED` (`_record_payment` dòng 275).

## 8. Rủi ro Cá Về

| Mảng | Rủi ro | Mức | Giảm thiểu |
|---|---|---|---|
| **Tiền / lãi lỗ** | Ai đó lọc báo cáo theo trạng thái đơn (ví dụ "doanh thu đơn Hoàn tất") ⇒ doanh thu dời kỳ, lệch BR-BC-01, sửa số kỳ cũ khi chuyển bù | Cao nếu xảy ra | BR-BC-06. QA kiểm số lãi lỗ kỳ trước **trước và sau** chuyển bù phải trùng khớp |
| **Chốt lô** | Hiện không chốt được lô đã bán (H1). Sửa xong, lô cũ bỗng chốt được ⇒ lãi lỗ đông cứng theo số hiện tại | Cao (đang chặn nghiệp vụ) | Ưu tiên. Không có rủi ro dời số: chốt lô vẫn đòi tồn 0, có hoá đơn mua, đã kiểm kê |
| **Tranh chấp trạng thái** | Huỷ và Hoàn tất bấm cùng lúc ⇒ đơn `CANCELLED` (đã có chứng từ đảo) nhưng phiếu `COMPLETED`, hoặc đơn bị ghi thành `COMPLETED` sau `CANCELLED` | Cao | BR-BH-18 + BR-GH-24: khoá đơn và phiếu, xét trạng thái mới nhất trong cùng giao dịch. Test đua bắt buộc |
| **Chứng từ / AuditLog** | Chuyển bù sửa trạng thái hàng loạt mà không vết | TB | Mỗi đơn một dòng AuditLog Hệ thống đánh dấu chuyển bù. Không xoá, không sửa hoá đơn |
| **Dữ liệu cá nhân** | Thêm thông tin "đã giao lúc…, cho ai" vào tra đơn Shop | TB | Shop chỉ thêm nhãn trạng thái (và có thể ngày giờ). Không tên người giao, không địa chỉ. AuditLog không chép SĐT hay địa chỉ |
| **Giá vốn** | Không chạm | — | — |
| **Kho / FEFO** | Không chạm. Trừ kho đã xảy ra lúc thanh toán (BR-BH-11) | — | — |

## 9. Ngoài phạm vi
- Giao một phần, ghi số kg thực giao (BR-GH-03 vẫn là giả định; hồ sơ huỷ-đơn-đang-giao Q12).
- Khách trả hàng sau khi đã nhận (đổi trả). Hiện chỉ có hoàn tiền, hàng không nhập lại (return_to_warehouse chỉ nhận
  phiếu Đang giao hoặc Giao thất bại).
- Tách một đơn thành nhiều chuyến giao. Chỉ chuẩn bị luật (UC-4), không làm màn tạo phiếu thứ hai.
- COD, cọc, thanh toán sau (decisions 26/09).
- Thông báo cho khách (SMS, Zalo) khi đơn Hoàn tất.
- Đổi tên nhãn trạng thái: thuộc lô dọn chữ và bảng tên chứng từ của PO. Ở đây chỉ nêu nhu cầu (Q5).

## 10. Câu hỏi mở

| # | Mức | Câu hỏi | Mặc định PA đề xuất |
|---|---|---|---|
| Q1 | 🔴 | **Đơn sang "Hoàn tất" vào lúc nào?** (A) Ngay khi phiếu giao cuối cùng được bấm Hoàn tất. (B) Sau khi giao xong N ngày không có khiếu nại hay phiếu hoàn đang chờ. | **A.** Spec §7.2 đã vẽ đúng như vậy, BR-GH-05 coi Hoàn tất của phiếu là điểm cuối, và khiếu nại sau đó đã có đường phiếu hoàn (BR-BH-20). B cần job nền và thêm một trạng thái chờ, không có giá trị cho Lộc |
| Q2 | 🔴 | **Trạng thái "Đã thanh toán" (`PAID`) xử lý thế nào?** (A) Bỏ dùng: giữ mã trong DB, ẩn khỏi bộ lọc và thanh bước, sửa spec §7.2 cho khớp code (thanh toán đủ = Đang xử lý). (B) Dùng lại `PAID` cho đoạn "đã trả tiền, chờ vựa gọi xác nhận" (phiếu đang Chờ xác nhận), rồi sang Đang xử lý khi bắt đầu soạn. | **A.** Code chưa bao giờ dùng `PAID`. Bước con đã đọc được từ phiếu giao, và Shop đã hiện "Đã thanh toán – chờ vựa gọi xác nhận" (`shop_api.py:94`). B thêm một điểm phải đồng bộ hai chiều (gồm "Huỷ xác nhận" quay lại Chờ xác nhận), dễ lệch |
| Q3 | 🔴 | **Đơn cũ đang kẹt "Đang xử lý" mà phiếu đã Hoàn tất: chuyển bù hay để nguyên?** | **Chuyển bù một lần** (UC-5): Hệ thống chuyển, có AuditLog đánh dấu, chạy lại an toàn. Lý do: nếu để nguyên, lô cũ không bao giờ chốt được (H1). Không đổi số báo cáo nào (BR-BC-06), nên không vi phạm "không sửa số kỳ cũ". DB production đang là dữ liệu thử nên phạm vi nhỏ |
| Q4 | 🟡 | Đơn Hoàn tất rồi mới hoàn tiền **toàn phần** (khách khiếu nại cả đơn): trạng thái đơn đổi không? | Giữ Hoàn tất (BR-BH-20). ERP hiện thêm dòng "Đã hoàn x đ" trên đơn để Lộc thấy. Không thêm trạng thái "Đã hoàn tiền" |
| Q5 | 🟡 | Khách thấy nhãn gì ở Shop? URD §87 liệt kê "đã giao", spec và code dùng "Hoàn tất" | Theo bảng tên PO đang đề xuất (decisions 06/10). Mặc định: **một nhãn "Hoàn tất" cho đơn ở ERP và Shop**, phiếu giao ở Shop hiện "Đã giao" |
| Q6 | 🟡 | Có cần lưu thời điểm đơn hoàn tất trên đơn (field mới) không? | Không thêm field. Dùng `completed_at` của phiếu giao cuối và AuditLog. Tech Lead chỉ thêm khi bộ lọc theo ngày hoàn tất cần đến, và phải ghi lý do |
| Q7 | 🟡 | AuditLog của bước chuyển đơn ghi ai làm? | Hệ thống (`actor=None`), kèm mã phiếu giao gây ra. Người bấm phiếu đã có ở dòng AuditLog của phiếu. Đơn là chứng từ do Hệ thống quản (BR-PQ-11) |
| Q8 | 🟡 | Có cho Chủ "đánh dấu hoàn tất tay" khi NV giao quên bấm không? | Không. Chủ/Quản lý bấm Hoàn tất **trên phiếu giao** (đã có quyền `change_deliverynote`), đơn tự theo |
| Q9 | 🟢 | Dòng thời gian đơn: gộp "Giao hàng thành công" và "Đơn hoàn tất" thành một mốc? | PO quyết khi viết story. Gợi ý gộp khi cùng thời điểm |
| Q10 | 🟢 | Báo cáo hay bộ lọc "đơn hoàn tất theo ngày" cho Lộc | Để sau. Không thuộc W37 |

**Thứ tự đề xuất cho PO:** (1) BR-BH-18 + UC-1, UC-2, kèm khoá chống đua (BR-GH-24, phần không ghi đè). (2) Chuyển bù UC-5.
(3) ERP và Shop hiển thị, gồm H2–H5. (4) Sửa spec §7.2 theo Q2. Hồ sơ huỷ-đơn-đang-giao, nếu được duyệt, phải dùng chung
luật "phiếu của đơn đã huỷ không sang Hoàn tất".

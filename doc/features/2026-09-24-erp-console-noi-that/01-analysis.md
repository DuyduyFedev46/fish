# ERP console "nối thật": từ màn hình chỉ xem sang màn hình thao tác được — Phân tích nghiệp vụ
> BA · 2026-09-24 · Trạng thái: **ĐÃ DUYỆT** (2026-09-24, Duy)

Ký hiệu mức câu hỏi (mục 10): **ĐỎ** = chặn, chưa trả lời thì không viết story được · **VÀNG** = có mặc định PA, Duy không nói gì thì làm theo mặc định · **XANH** = để sau.

---

## 1. Yêu cầu gốc
> "làm tính năng đầy đủ, các tính năng đang dạng prototype chưa tương tác được"

Nguồn: Duy (PO), 2026-09-24, chuyển qua điều phối viên. Duy chỉ vào ERP console back-office (`erp-console/public/index.html`, Firebase site `cangca-erp`).

## 2. Tóm tắt
**Chủ, Quản lý, NV kho, NV giao** cần **làm được việc của mình (duyệt, chốt, huỷ, xác nhận, gán, cập nhật trạng thái, nhập chứng từ) ngay trên ERP console**, thay vì chỉ xem số liệu rồi sang Django Admin sửa tay. Giá trị: mọi chuyển trạng thái đều qua đúng luật nghiệp vụ và có AuditLog, không ai phải sửa trực tiếp field trong Admin.

**Cách hiểu "đầy đủ, tương tác được" (PA, cần Duy xác nhận ở Q1):**
Mọi thao tác nghiệp vụ **Tầng 2** (spec §1.5) và mọi chứng từ vận hành hằng ngày của P-02…P-10 đều làm được trên console, theo đúng vai, và đi qua service nghiệp vụ. Django Admin lùi về đúng vai trò trong `decisions.md` 2026-09-10: nơi *cấu hình* master data (danh mục, combo, ưu đãi, nhân sự) và nơi *cứu hộ* của người kỹ thuật.

Đây là việc lớn: khoảng 24 use case, trải trên 7 màn hình, 4 vai. **Đề xuất chia 3 đợt (mục 5.0).**

---

## 3. Bối cảnh trong hệ thống

### 3.1 Quy trình, rule, quyết định ràng buộc
- **Quy trình:** P-02, P-03, P-04, P-05 (nhánh ngoại lệ thanh toán), P-06, P-07, P-08, P-09, P-10. P-01 (danh mục) để đợt 3.
- **Rule chính:** BR-PQ-04/05/10/11/12/13, BR-MH-01…06, BR-GV-01…04, BR-LO-01…06, BR-TT-04/05/07, BR-GH-01…06, BR-HT-01…08, BR-HV-01…04, BR-KK-01…05, BR-BC-01…05.
- **Quyết định ràng buộc (không tự lật):**
  - `decisions.md` 2026-09-10 "Phân quyền 3 tầng": ranh giới Chủ ↔ Quản lý, cấm rò giá vốn, test bằng token nhân viên thật.
  - 2026-09-10 "Huỷ đơn & hoàn tiền": hoàn tiền là chuyển khoản tay, hệ thống chỉ ghi sổ.
  - 2026-09-09 "Django 100% lõi": console chỉ là client của DRF, **không có logic nghiệp vụ ở phía console**.
  - Nguyên tắc xuyên suốt: "ưu tiên công cụ có sẵn (Django Admin/auth) hơn tự build", "dễ 1 người maintain". Hai nguyên tắc này **kéo ngược** với yêu cầu làm console đầy đủ, xem Q3.

### 3.2 Hiện trạng ERP console (đọc code, 2026-09-24)
| Màn | Hiện trạng | Thao tác được |
|---|---|---|
| Đăng nhập | Token DRF `/api/auth/token/`, lưu localStorage | Đăng nhập, đăng xuất |
| Tổng quan | Dữ liệu thật từ `/api/dashboard/summary/` (KPI, 8 đơn gần nhất, 20 lô, cảnh báo cận hạn, 8 dòng sổ kho) | Chỉ xem |
| Đơn hàng | Cũng chỉ lấy 8 đơn gần nhất từ dashboard, **không phân trang, không có chi tiết đơn** | Chỉ xem |
| Kho & Lô | 20 lô đang hoạt động từ dashboard | Chỉ xem |
| Mua hàng, Giao hàng, Báo cáo lãi lỗ, Danh mục & giá | Placeholder "sẽ nối ở bước sau" | Không có |
| Cột phải: Ghi chú | Lưu localStorage **trên máy đó**, không đồng bộ giữa người | Gõ ghi chú |
| Cột phải: Trợ lý | Trả lời bằng regex trên dữ liệu đã tải, **không gọi AI** | Hỏi đáp giả |
| Cột phải: Hoạt động | 8 dòng sổ kho gần nhất | Chỉ xem |

Console hiện chỉ biết `username` và `can_cost`. Nó **không biết người đăng nhập thuộc Group nào, có quyền Tầng 2 nào**, nên chưa thể ẩn/hiện menu và nút theo vai. Nhãn vai đang đoán theo `can_cost` ("Chủ vựa" / "Nhân viên back-office").

### 3.3 Hiện trạng Django Admin (nơi đang nhập liệu thật)
- **Không có admin action và không có `save_model` nào gọi service** (grep `backend/apps/*/admin.py`). Hệ quả: chuyển trạng thái trong Admin là **sửa field trực tiếp**, bỏ qua kiểm tra luật và **không ghi AuditLog**.
- `BatchAdmin` cho sửa `status`, `qty_available`, `landed_unit_cost` (với người có `view_costprice`) → có thể đổi giá vốn/tồn "âm thầm", vi phạm BR-GV-03, BR-PQ-05.
- Lưu phiếu nhập trong Admin không gọi `submit_receipt` nên **lô không được sinh** qua đường chuẩn.

→ Đây là lý do nghiệp vụ mạnh nhất cho tính năng: **hiện chưa có đường đúng luật nào để làm các thao tác Tầng 2**, ngoài việc gọi API thô.

### 3.4 Đối chiếu thao tác nghiệp vụ ↔ API back-office hiện có
Nguồn: `backend/config/api_urls.py`, `apps/*/api.py`, `apps/*/services.py`, `apps/*/serializers.py`.

| # | Thao tác nghiệp vụ | Rule | API hiện có | Tình trạng |
|---|---|---|---|---|
| A1 | Xem danh sách/chi tiết đơn, hoá đơn, lô phân bổ | BR-BH-06 | `sales/orders`, `sales/invoices` (read-only) | **Có** |
| A2 | Xác nhận thanh toán thủ công khi webhook không tới (E-05) | BR-TT-07 | `sales/invoices/{id}/confirm-payment` | **Sai chỗ gắn — không dùng được.** Đơn chưa thanh toán thì *chưa có hoá đơn*, mà action lại gắn vào hoá đơn. Đúng tình huống E-05 thì không có gì để bấm. |
| A3 | Hàng chờ thanh toán lệch (thiếu tiền / tiền về sau khi huỷ / không khớp) | BR-TT-04/05 | `sales/payments` (chỉ đọc) | **Thiếu thao tác xử lý**: không có "xác nhận bù", "đánh dấu đã xử lý". Tiền về sau khi đơn đã huỷ thì đơn **không có hoá đơn**, mà `Refund` lại bắt buộc gắn hoá đơn → **không tạo được phiếu hoàn cho ca này** (xem Q9). |
| A4 | Huỷ đơn đã thanh toán | BR-HT-05, `cancel_paid_order` | `sales/orders/{id}/cancel` | **Có**, nhưng: chỉ huỷ **toàn phần**; **không kiểm tra phiếu giao** (có thể huỷ đơn đang giao, thậm chí đã Hoàn tất, trái BR-GH-05); phiếu giao của đơn đã huỷ vẫn nằm trong việc của NV giao. |
| A5 | Tạo phiếu hoàn (toàn phần/một phần) | BR-HT-01/02/04/07 | `sales/refunds/create` | **Có** |
| A6 | Xác nhận đã hoàn (kèm mã GD) | BR-HT-03/07 | `sales/refunds/{id}/confirm` | **Có** |
| A7 | Đánh dấu hoàn tiền **thất bại** (sai STK) / thử lại | spec §9.3 | — | **Thiếu** (model có trạng thái FAILED, không có service/API chuyển sang) |
| A8 | Danh sách phiếu giao, NV giao chỉ thấy phiếu của mình | BR-GH-06, BR-PQ-12 | `delivery/notes` (lọc queryset) | **Có** |
| A9 | Chuyển trạng thái giao, báo giao thất bại | BR-GH-04/05 | `delivery/notes/{id}/status` | **Có**. Nhưng `PATCH delivery/notes/{id}` vẫn mở: NV giao có quyền sửa có thể ghi thẳng `status` (bỏ qua state machine, không AuditLog) hoặc đổi `assigned_to` sang người khác. Trái BR-GH-06. |
| A10 | Gán / đổi NV giao | URD §5.2, §6.4 | Chỉ có `PATCH` chung | **Thiếu thao tác riêng**: không kiểm người được gán có thuộc `nv_giao`/đang làm, không AuditLog. **Không có API liệt kê nhân viên** để chọn người. |
| A11 | NV giao ghi hàng mang về kho | BR-HV-01/02 | `inventory/returns` (POST chung) | **Chưa đi qua service** `return_to_warehouse` (service có sẵn nhưng không được nối) → không kiểm trạng thái phiếu giao, không AuditLog. `created_by` và `decision` do client tự gửi. |
| A12 | Duyệt hàng hoàn (tái nhập / huỷ bỏ) | BR-HV-02/04 | `inventory/returns/{id}/approve` | **Có**. Chưa có gợi ý "mặc định huỷ bỏ khi quá ngưỡng chuỗi lạnh" (BR-HV-03, ngưỡng chưa có số). |
| A13 | Publish lô | BR-MH-05 | `inventory/batches/{id}/publish` | **Có** |
| A14 | Chốt lô | BR-LO-04/05 | `inventory/batches/{id}/close` | **Có**. Chưa kiểm "không còn đơn đang mở tham chiếu lô" và "đã kiểm kê trước khi chốt" (BR-KK-05). |
| A15 | Huỷ lô quá hạn, hạch toán lỗ | BR-LO-02/03 | — | **Thiếu hoàn toàn** (không có service, không có quyền Tầng 2 tương ứng) |
| A16 | Tự chuyển lô sang Cận hạn / Quá hạn / Hết hàng | BR-LO-01/02/06 | — | **Thiếu job.** Và việc chọn lô FIFO chỉ lọc theo `status`, **không lọc hạn dùng** → lô quá ngày hạn vẫn bán được nếu chưa ai đổi trạng thái. **Vi phạm BR-LO-02**, xem mục 8. |
| A17 | `PATCH` lô trực tiếp | BR-GV-03 | `inventory/batches/{id}` | **Đang mở**: `status`, `landed_unit_cost`, `purchase_rate`, `expiry_date` ghi được qua `PATCH` → bỏ qua state machine và AuditLog |
| A18 | Nhập phiếu nhập lô tại cảng + dòng hàng | BR-MH-01/02/06 | `purchasing/receipts` + `.../submit` | **Thiếu nhập dòng**: dòng phiếu chỉ đọc, không có endpoint ghi dòng → không tạo được phiếu có hàng qua API. Phạm vi "NV kho chỉ sửa phiếu của mình, trong ngày" **chưa có** trong queryset. |
| A19 | Ghi Purchase Invoice | BR-MH-03/04 | `purchasing/invoices` | Có CRUD. `amount` (tổng tiền mua) **không bị ẩn** với Quản lý (Quản lý có R) → chia cho số kg là ra giá mua. Xem mục 8, Q10. |
| A20 | Ghi chi phí mua (landed cost), phân bổ vào lô | BR-GV-01…04 | `purchasing/costs` (POST, chỉ Chủ) | **Có** |
| A21 | Nhập số kiểm kê theo lô | BR-KK-01/04 | `inventory/reconciliations` | **Thiếu nhập dòng** (dòng chỉ đọc). `created_by` do client gửi → có thể giả người nhập để lách BR-KK-02. |
| A22 | Duyệt kiểm kê | BR-KK-02/03 | `inventory/reconciliations/{id}/approve` | **Có** |
| A23 | Báo cáo lãi lỗ theo lô / theo kỳ | BR-BC-01…05 | `reports/batch/{batch_id}`, `reports/period?year&month` | **Có**. Chưa có danh sách "tất cả lô kèm lãi/lỗ" (phải gọi từng lô). |
| A24 | Danh mục, giá, combo, ưu đãi | BR-DM-* | `catalog/*` CRUD | **Có CRUD** |
| A25 | "Tôi là ai, thuộc Group nào, có quyền gì" | BR-PQ-09 | — | **Thiếu** (dashboard chỉ trả `username`, `can_cost`) |
| A26 | Nhân sự: tạo tài khoản, đổi Group, cho nghỉ | BR-PQ-01/08, `manage_staff` | — | **Thiếu** (chỉ có trong Admin) |
| A27 | Xem nhật ký AuditLog | BR-PQ-04 | — | **Thiếu** (chỉ Admin) |
| A28 | Phạm vi dòng NV giao trên Đơn/Khách | spec §1.6 | — | **Thiếu**: `sales/orders`, `sales/customers` không lọc theo phiếu được gán |
| A29 | `stock-entries` (điều chỉnh tồn tay) | — | CRUD chung | Tạo qua API **không ghi sổ kho** (không qua `record_movement`). Không nên đưa lên console khi chưa rõ nghiệp vụ, xem mục 9. |

**Kết luận đối chiếu:** backend đủ cho khoảng 60% thao tác. Phần còn thiếu tập trung ở ba chỗ: (1) **nhập chứng từ có dòng** (phiếu nhập, kiểm kê), (2) **các nhánh ngoại lệ** (thanh toán lệch, hoàn tiền thất bại, huỷ lô quá hạn, gán NV giao), (3) **lỗ hổng `PATCH` chung** cho phép vượt state machine. Muốn console "tương tác được" thì BE phải làm song song, không chỉ FE.

---

## 4. Tác nhân & quyền

### 4.1 Ma trận thao tác trên console (trích spec §1.4, §1.5, §1.6)
| Tác nhân | Group | Làm được gì trên console | Quyền Tầng 2 cần |
|---|---|---|---|
| Lộc | `chu` | Tất cả, kể cả xem giá vốn/lãi lỗ, xác nhận tiền, chốt lô, chi phí mua, nhân sự | `publish_batch`, `close_batch`, `add_purchasecost`, `approve_*`, `cancel_paid_order`, `create_refund`, `confirm_refund`, `confirm_payment_manual`, `view_costprice`, `view_profitreport`, `manage_staff` |
| Quản lý (người được uỷ quyền) | `quan_ly` | Duyệt vận hành: publish lô, huỷ đơn đã thanh toán, tạo phiếu hoàn, duyệt hàng hoàn, duyệt kiểm kê (không duyệt phiếu mình nhập), gán NV giao, nhập phiếu nhập. **Không** thấy giá vốn, lãi lỗ, không xác nhận tiền | `publish_batch`, `approve_stockreconciliation`, `approve_returntostock`, `cancel_paid_order`, `create_refund` |
| NV kho | `nv_kho` | Nhập phiếu nhập lô (không xem lại đơn giá của phiếu người khác), soạn hàng (cập nhật phiếu giao), nhập số kiểm kê, ghi hàng hoàn, gán NV giao (PA, Q7) | — |
| NV giao | `nv_giao` | Chỉ phiếu giao được gán cho mình: nhận hàng, đang giao, hoàn tất, giao thất bại, ghi hàng mang về. Xem SĐT/địa chỉ khách của phiếu đó | — |
| Hệ thống | — | Tạo đơn, hoá đơn, phiếu giao; huỷ theo TTL; xác nhận webhook; (đề xuất) chuyển trạng thái lô theo hạn | actor = None |

Người kiêm nhiệm (BR-PQ-09): console phải hiển thị **hợp** các màn/nút của mọi Group người đó thuộc. Ví dụ `nv_kho` + `nv_giao` thấy cả màn kho lẫn "việc giao của tôi".

### 4.2 Vai ↔ màn hình ↔ thiết bị (PA, chờ Q4)
| Vai | Màn chính | Thiết bị giả định | Căn cứ |
|---|---|---|---|
| Chủ | Tổng quan, Đơn & tiền, Kho & lô, Mua hàng, Báo cáo | **Điện thoại là chính** (đi cảng rạng sáng) + máy tính khi về | spec §1.1 "Lộc đi cảng mua hàng lúc rạng sáng" (L) |
| Quản lý | Đơn, Giao hàng, Kho & lô, Kiểm kê | Máy tính ở kho + điện thoại | PA |
| NV kho | Mua hàng (nhập tại cảng), Soạn hàng, Kiểm kê | **Điện thoại tại cảng**; máy tính/tablet ở kho | URD §5.3 "thực hiện ngay tại cảng khi mua" (L) |
| NV giao | "Việc giao của tôi" | **Chỉ điện thoại**, một tay, ngoài đường | PA, chưa ai phát biểu |

Hệ quả nghiệp vụ: **nhập phiếu nhập lô tại cảng** và **toàn bộ luồng NV giao** phải dùng tốt trên điện thoại. Console hiện là bố cục 3 cột cho máy tính, chỉ co lại khi màn hẹp.

---

## 5. Use case

### 5.0 Đề xuất chia đợt (PA, chờ Q1)
Nguyên tắc chia: đợt trước gỡ **việc làm khách phải chờ** và **lỗ hổng luật/giá vốn**. Việc cấu hình để sau vì Admin đang làm được và ít rủi ro.

| Đợt | Phạm vi | Vì sao trước | UC |
|---|---|---|---|
| **Đợt 1: Đơn, tiền, giao hàng** | Nhận diện vai; chi tiết đơn; xác nhận thanh toán tay; hàng chờ thanh toán lệch; huỷ đơn; phiếu hoàn (tạo/xác nhận/thất bại); điều phối giao (gán NV, cập nhật trạng thái, giao thất bại, hàng mang về, duyệt hàng hoàn); màn "việc giao của tôi" trên điện thoại | Khách đang chờ tiền/hàng. E-05 hiện **không có đường xử lý nào** (A2). Luồng giao là việc hằng ngày của 2 vai chưa có công cụ | UC-01…UC-12 |
| **Đợt 2: Kho, mua hàng, giá vốn, báo cáo** | Publish/chốt lô; huỷ lô quá hạn; phiếu nhập lô tại cảng (có dòng, trên điện thoại); Purchase Invoice; chi phí mua; kiểm kê (nhập + duyệt); báo cáo lãi lỗ lô/kỳ | Đụng giá vốn, cần BE bổ sung nhiều hơn (A15, A16, A18, A21). Admin đang tạm làm được nhập liệu, dù không đúng luật | UC-13…UC-21 |
| **Đợt 3: Cấu hình và quản trị** | Danh mục & giá & combo & ưu đãi; nhân sự; nhật ký AuditLog; Trợ lý AI (nếu có) | Admin đã làm tốt phần cấu hình; tần suất thấp | UC-22…UC-24 |

**Việc BE bắt buộc trước đợt 1, dù không có màn hình nào:** khoá `PATCH` vượt state machine (A9, A17), ghi `created_by` theo người đăng nhập (A11, A21), lọc phạm vi dòng NV giao trên đơn/khách (A28). Nếu console mở thêm nút mà các lỗ này còn, người dùng thành thạo mở DevTools là vượt luật được (BR-PQ-12).

---

### UC-01 Đăng nhập và thấy đúng màn của vai mình
- **Tác nhân:** mọi nhân viên nội bộ.
- **Tiền điều kiện:** có tài khoản `is_active`, thuộc ít nhất một Group.
- **Luồng chính:**
  1. Người dùng đăng nhập bằng tài khoản nội bộ.
  2. Hệ thống trả danh tính: tên hiển thị (StaffProfile), các Group, các quyền Tầng 2, có xem giá vốn/lãi lỗ hay không.
  3. Console chỉ hiện menu và nút ứng với quyền (hợp các Group, BR-PQ-09).
  4. NV giao thuần (chỉ `nv_giao`) vào thẳng màn "Việc giao của tôi".
- **Luồng thay thế:** 2a. Người kiêm nhiệm → thấy hợp các màn.
- **Ngoại lệ:**
  - E1. Tài khoản đã nghỉ (`is_active=False`, BR-PQ-01) → từ chối đăng nhập, thông báo rõ.
  - E2. Token hết hạn hoặc bị thu hồi giữa phiên → về màn đăng nhập, **không mất dữ liệu đang nhập dở** (quan trọng với phiếu nhập tại cảng, xem Q6).
  - E3. Tài khoản không thuộc Group nào → thông báo "chưa được phân quyền, liên hệ Chủ".
- **Hậu điều kiện:** ẩn nút chỉ là tiện dụng. Mọi thao tác vẫn bị backend chặn lại theo quyền (BR-PQ-12).

### UC-02 Xem danh sách và chi tiết đơn
- **Tác nhân:** Chủ, Quản lý, NV kho (R). NV giao chỉ đơn thuộc phiếu của mình.
- **Tiền điều kiện:** đăng nhập, có `view_salesorder`.
- **Luồng chính:**
  1. Mở "Đơn hàng", lọc theo trạng thái (Giữ chỗ / Đã thanh toán / Đang xử lý / Hoàn tất / Đã huỷ / Tự huỷ) và theo ngày; tìm theo mã đơn, SĐT.
  2. Mở một đơn: khách, SĐT, địa chỉ, dòng hàng (kg, đơn giá, giảm giá), thời hạn giữ chỗ còn lại, hoá đơn, giao dịch thanh toán, phiếu giao (trạng thái, người giao, số lần thất bại), phiếu hoàn (số tiền, trạng thái).
  3. Người có `view_costprice` thấy thêm bảng phân bổ lô kèm giá vốn (BR-BH-06). Người khác thấy lô và số kg, **không thấy giá vốn**.
- **Ngoại lệ:** E1. Không có quyền → không thấy menu, API trả 403. E2. Danh sách dài → phải phân trang (dashboard hiện chỉ trả 8 đơn).
- **Hậu điều kiện:** không đổi dữ liệu.

### UC-03 Xác nhận thanh toán thủ công (E-05)
- **Tác nhân:** **chỉ Chủ** (`confirm_payment_manual`, BR-TT-07).
- **Tiền điều kiện:** đơn ở trạng thái **Giữ chỗ** (chưa có hoá đơn); Lộc đã thấy tiền về trên sao kê ngân hàng.
- **Luồng chính:**
  1. Chủ mở đơn Giữ chỗ, bấm "Xác nhận đã nhận tiền".
  2. Nhập **mã giao dịch ngân hàng** (bắt buộc) và số tiền thực nhận (mặc định = tổng đơn).
  3. Hệ thống xử lý như webhook: đủ tiền → xuất hoá đơn, trừ kho thật theo lô đã giữ, đơn sang Đang xử lý, sinh phiếu giao (Soạn hàng). Ghi AuditLog với actor = Chủ.
- **Luồng thay thế:**
  - 3a. Số tiền < tổng đơn → ghi giao dịch **Thiếu tiền**, đơn không đổi, vào hàng chờ (UC-04), BR-TT-04.
  - 3b. Mã GD đã tồn tại (webhook tới muộn cùng lúc) → trả kết quả cũ, không xử lý lần hai (BR-TT-03).
- **Ngoại lệ:**
  - E1. Đơn đã **Tự huỷ** vì quá TTL trước khi Chủ bấm → không khôi phục đơn (BR-TT-05); giao dịch thành "tiền về sau khi huỷ", vào hàng chờ UC-04.
  - E2. Quản lý bấm → bị từ chối (403).
  - E3. Bấm hai lần do mạng chậm → lần hai không được tạo giao dịch/hoá đơn thứ hai.
- **Hậu điều kiện:** doanh thu ghi tại thời điểm xác nhận (BR-TT-06, BR-BC-01).
- **Chặn hiện tại:** API đang gắn vào *hoá đơn* nên không làm được bước 1 (A2). BE phải sửa.

### UC-04 Xử lý hàng chờ thanh toán lệch
- **Tác nhân:** chỉ Chủ.
- **Tiền điều kiện:** có giao dịch ở trạng thái Thiếu tiền / Tiền về sau khi huỷ / Không khớp mã đơn.
- **Luồng chính:**
  1. Chủ mở "Hàng chờ thanh toán": mỗi dòng có mã GD, số tiền, thời điểm, đơn liên quan (nếu có), loại lệch.
  2. Chủ chọn cách xử lý tuỳ loại:
     - **Thiếu tiền, khách chuyển bù:** khoản bù về như một giao dịch khác. Chủ xác nhận đơn khi tổng các khoản ≥ tổng đơn (Q9).
     - **Tiền về sau khi huỷ / thiếu tiền mà khách không bù:** hoàn lại tiền cho khách (chuyển khoản tay), ghi mã GD hoàn.
     - **Không khớp đơn nào:** gắn vào đúng đơn (nếu tìm ra) hoặc hoàn lại.
  3. Dòng chuyển sang "Đã xử lý", ghi người xử lý, cách xử lý, ghi chú, AuditLog.
- **Ngoại lệ:**
  - E1. Đơn đã tự huỷ, hàng đã bán cho người khác → không khôi phục (BR-TT-05), chỉ hoàn tiền.
  - E2. Hoàn tiền cho giao dịch **không có hoá đơn**: `Refund` hiện bắt buộc gắn hoá đơn → **schema không chứa được** (Q9).
- **Hậu điều kiện:** không còn giao dịch lệch nào "treo" mà không ai biết. Tiền rời túi có dấu vết.

### UC-05 Huỷ đơn đã thanh toán
- **Tác nhân:** Chủ, Quản lý (`cancel_paid_order`, BR-HT-07).
- **Tiền điều kiện:** đơn Đã thanh toán / Đang xử lý; phiếu giao **chưa Hoàn tất**.
- **Luồng chính:**
  1. Mở đơn, bấm "Huỷ đơn", chọn lý do (khách đổi ý / hàng hỏng khi soạn / thôi không giao sau giao thất bại / khác) và ghi chú.
  2. Hệ thống hoàn kho **toàn bộ** về đúng lô gốc theo bảng phân bổ (BR-HT-05), đơn sang Đã huỷ, ghi AuditLog.
  3. Phiếu giao của đơn bị **đóng/huỷ**, biến khỏi "Việc giao của tôi" của NV giao (BR-GH-07 đề xuất).
  4. Console gợi ý ngay bước tiếp: "Tạo phiếu hoàn tiền toàn phần" (UC-06), điền sẵn số tiền.
- **Luồng thay thế:** 1a. Huỷ từ tình huống giao thất bại → hàng đang ở ngoài, **không hoàn kho trực tiếp**; phải qua hàng mang về + duyệt (UC-11, UC-12, BR-HV-02). Cần luật rõ để kho không bị cộng hai lần (Q8).
- **Ngoại lệ:**
  - E1. Phiếu giao đã Hoàn tất → từ chối (BR-GH-05), chỉ còn đường phiếu hoàn.
  - E2. Phiếu giao Đang giao → từ chối, yêu cầu báo giao thất bại trước (BR-GH-07 đề xuất).
  - E3. Lô gốc đã chốt → hoàn kho vào lô đã chốt vi phạm BR-LO-05 (lô đơn đang mở chưa được chốt theo BR-LO-04, nhưng hiện chưa kiểm, A14).
  - E4. Huỷ **một phần** (thiếu một mặt hàng) → đợt 1 không hỗ trợ (Q8).
- **Hậu điều kiện:** kho đúng. Doanh thu **chưa** đảo cho tới khi có phiếu hoàn (BR-HT-06).

### UC-06 Tạo phiếu hoàn tiền
- **Tác nhân:** Chủ, Quản lý (`create_refund`).
- **Tiền điều kiện:** hoá đơn đã xuất.
- **Luồng chính:**
  1. Từ đơn, bấm "Tạo phiếu hoàn", nhập số tiền, chọn toàn phần/một phần, lý do.
  2. Hệ thống kiểm số tiền ≤ đã thu − các lần hoàn trước chưa thất bại (BR-HT-04), tạo phiếu **Chờ hoàn**, ghi AuditLog (BR-HT-08).
  3. Phiếu vào danh sách "Chờ Chủ chuyển khoản".
- **Ngoại lệ:** E1. Vượt số đã thu → báo lỗi, nêu số còn được hoàn. E2. Bấm hai lần → không được sinh hai phiếu (cần chống trùng, Q12). E3. Số ≤ 0 → báo lỗi.
- **Hậu điều kiện:** nợ khách được ghi nhận. Tiền chưa đi.

### UC-07 Xác nhận đã hoàn / đánh dấu hoàn thất bại
- **Tác nhân:** chỉ Chủ (`confirm_refund`).
- **Tiền điều kiện:** phiếu Chờ hoàn hoặc Thất bại.
- **Luồng chính:**
  1. Chủ mở "Phiếu hoàn chờ chuyển", thấy STK/tên/SĐT khách (nếu có, Q13), số tiền.
  2. Chủ chuyển khoản trên app ngân hàng (ngoài hệ thống), quay lại nhập **mã giao dịch** (bắt buộc, BR-HT-03), bấm xác nhận.
  3. Phiếu sang Đã hoàn, ghi người/giờ xác nhận, AuditLog. Khoản hoàn vào kỳ của ngày xác nhận (BR-BC-03).
- **Luồng thay thế:** 2a. Chuyển không được (sai STK, khách không nhận) → Chủ bấm "Thất bại" kèm lý do → phiếu Thất bại. Sau đó "Thử lại" → về Chờ hoàn (spec §9.3). Hiện **chưa có service** (A7).
- **Ngoại lệ:** E1. Không nhập mã GD → từ chối. E2. Phiếu đã Đã hoàn → từ chối xác nhận lại. E3. Quản lý bấm → 403.
- **Hậu điều kiện:** tiền rời túi có mã GD đối chiếu được.

### UC-08 Điều phối giao hàng: gán / đổi NV giao
- **Tác nhân:** Chủ, Quản lý, NV kho (có `change_deliverynote`, spec §1.4). Q7 hỏi có cho NV kho gán không.
- **Tiền điều kiện:** phiếu giao ở Soạn hàng / Chờ lấy / Giao thất bại.
- **Luồng chính:**
  1. Mở "Giao hàng": bảng phiếu theo trạng thái (Soạn hàng → Chờ lấy → Đang giao → Thất bại → Hoàn tất), cột người giao, số lần thất bại, địa chỉ, giờ thanh toán.
  2. Chọn một hoặc nhiều phiếu, chọn NV giao từ danh sách nhân viên **đang làm, thuộc `nv_giao`**, kèm SĐT (BR-GH-01).
  3. Hệ thống ghi người giao, AuditLog (ai gán, từ ai sang ai).
- **Luồng thay thế:** 2a. Đổi người khi phiếu Giao thất bại (hẹn lại) → cho phép.
- **Ngoại lệ:**
  - E1. Phiếu Đang giao / Hoàn tất → không đổi người (hàng đang trong tay người cũ).
  - E2. Người được chọn đã nghỉ (BR-PQ-01) → không có trong danh sách.
  - E3. Chưa có ai thuộc `nv_giao` → thông báo, gợi ý Chủ gán Group (đợt 3 hoặc Admin).
  - E4. Phiếu có từ 2 lần thất bại trở lên (BR-GH-04) → gắn cờ "cần Quản lý/Chủ quyết": giao lại hay huỷ (UC-05).
- **Hậu điều kiện:** NV giao thấy phiếu trong "Việc giao của tôi".

### UC-09 Cập nhật tiến độ soạn và giao
- **Tác nhân:** NV kho (soạn hàng → chờ lấy), NV giao (chờ lấy → đang giao → hoàn tất), Quản lý/Chủ (mọi bước).
- **Tiền điều kiện:** phiếu trong phạm vi của người đó (NV giao: `assigned_to = mình`, BR-GH-06).
- **Luồng chính:**
  1. NV kho xem danh sách cần soạn kèm dòng hàng và số kg (BR-GH-03: cân đúng số đặt). Soạn xong bấm "Đã đóng gói" → Chờ lấy.
  2. NV giao (điện thoại) mở "Việc giao của tôi": địa chỉ, SĐT khách (bấm để gọi), dòng hàng, số kg. Bấm "Nhận hàng đi giao" → Đang giao.
  3. Giao xong bấm "Khách đã nhận" → Hoàn tất (điểm không quay lui, BR-GH-05). Console hỏi xác nhận trước khi ghi.
- **Ngoại lệ:**
  - E1. Bấm sai bước (vd từ Soạn hàng thẳng Hoàn tất) → backend từ chối theo state machine.
  - E2. Mạng rớt khi bấm → lặp lại không được gây nhảy hai bước; hiển thị rõ đã ghi hay chưa.
  - E3. Đơn đã bị huỷ trong lúc đang soạn → phiếu biến mất hoặc hiện "Đơn đã huỷ, không giao".
  - E4. NV giao cố mở phiếu của người khác (sửa URL) → 404/403 (BR-PQ-12).
  - E5. NV giao cố sửa dòng hàng/địa chỉ → không có thao tác, backend chặn (BR-GH-06).
- **Hậu điều kiện:** mỗi bước ghi AuditLog. Khách tra đơn thấy trạng thái mới (URD §5.1).

### UC-10 Báo giao thất bại, hẹn giao lại
- **Tác nhân:** NV giao (phiếu của mình), Quản lý/Chủ.
- **Tiền điều kiện:** phiếu Đang giao.
- **Luồng chính:**
  1. Bấm "Giao thất bại", chọn lý do (không gặp khách / khách từ chối / sai địa chỉ / khác), ghi chú.
  2. Phiếu sang Giao thất bại, số lần thử +1 (BR-GH-04), AuditLog.
  3. Từ lần thứ 2 (ngưỡng cấu hình), hệ thống **nhắc Quản lý/Chủ** quyết định (E-08). Trên console: huy hiệu ở menu Giao hàng và mục trong "Cần chú ý".
- **Luồng thay thế:** 3a. Hẹn giao lại → Quản lý/NV giao chuyển về Đang giao. 3b. Thôi không giao → UC-11 (mang hàng về) rồi UC-05 (huỷ) và UC-06 (hoàn).
- **Ngoại lệ:** E1. Phiếu không ở Đang giao → từ chối. E2. Chưa có cơ chế "nhắc" ngoài AuditLog → đợt 1 nhắc bằng cảnh báo trên console (PA, Q11).
- **Hậu điều kiện:** hàng vẫn tính là đã bán, chưa về kho.

### UC-11 NV giao ghi hàng mang về kho
- **Tác nhân:** NV giao (phiếu của mình), NV kho.
- **Tiền điều kiện:** phiếu Đang giao hoặc Giao thất bại.
- **Luồng chính:**
  1. Bấm "Mang hàng về kho". Console điền sẵn từng lô gốc và số kg theo bảng phân bổ của đơn (BR-HV-01). Người dùng chỉ xác nhận hoặc giảm số kg.
  2. Nhập giờ rời kho (mặc định: lúc chuyển Đang giao), giờ về kho (mặc định: bây giờ).
  3. Hệ thống tạo phiếu hàng hoàn **Chờ duyệt**, người tạo = người đăng nhập, **không cộng kho** (BR-HV-02), AuditLog.
- **Ngoại lệ:**
  - E1. Chọn lô không thuộc đơn → từ chối (BR-HV-01).
  - E2. Số kg > số kg đã xuất cho đơn từ lô đó → từ chối.
  - E3. Ghi hai lần cho cùng một lượt về → cần chặn trùng (Q12).
- **Hậu điều kiện:** phiếu hiện trong hàng chờ duyệt của Quản lý/Chủ, có huy hiệu.

### UC-12 Duyệt hàng hoàn: tái nhập hay huỷ bỏ
- **Tác nhân:** Chủ, Quản lý (`approve_returntostock`).
- **Tiền điều kiện:** phiếu hàng hoàn Chờ duyệt.
- **Luồng chính:**
  1. Mở phiếu: lô gốc, số kg, **thời gian ngoài chuỗi lạnh** (giờ về − giờ rời kho).
  2. Nếu vượt ngưỡng → hệ thống **đề xuất sẵn "Huỷ bỏ"** (BR-HV-03). Người duyệt vẫn được đổi.
  3. Chọn Tái nhập (cộng đúng lô gốc, cờ hàng hoàn) hoặc Huỷ bỏ (không cộng, lỗ vào lô gốc), bấm duyệt. AuditLog.
- **Ngoại lệ:** E1. Lô gốc đã chốt → chỉ được Huỷ bỏ/hạch toán lỗ (BR-HV-04). E2. Chưa chọn quyết định → từ chối. E3. Phiếu đã duyệt → từ chối. E4. Ngưỡng chuỗi lạnh chưa có số (câu hỏi mở #3 của spec) → đợt 1 **không đề xuất**, chỉ hiển thị số giờ (Q14).
- **Hậu điều kiện:** kho và lỗ lô đúng. Người duyệt nối tiếp sang huỷ đơn/hoàn tiền nếu cần.

### UC-13 Publish lô
- **Tác nhân:** Chủ, Quản lý (`publish_batch`).
- **Tiền điều kiện:** lô Nháp.
- **Luồng chính:** 1. Lọc lô Nháp. 2. Kiểm tra mặt hàng, số kg, hạn dùng (và giá vốn nếu là Chủ). 3. Bấm "Mở bán" → Đang bán, hiện trên Shop. AuditLog.
- **Ngoại lệ:** E1. Lô không phải Nháp → từ chối. E2. Mặt hàng **chưa có giá niêm yết hiệu lực** → Shop không bán được. Đề xuất cảnh báo trước khi publish (Q15). E3. Lô đã quá hạn → không cho publish (BR-LO-02).
- **Hậu điều kiện:** tồn khả dụng trên Shop tăng.

### UC-14 Chốt lô
- **Tác nhân:** chỉ Chủ (`close_batch`).
- **Tiền điều kiện:** tồn = 0 hoặc lô đã Huỷ/Quá hạn; có Purchase Invoice; không còn đơn đang mở tham chiếu lô (BR-LO-04); đã kiểm kê (BR-KK-05, PA).
- **Luồng chính:** 1. Mở lô, xem **lãi/lỗ tạm tính** (UC-21). 2. Console liệt kê điều kiện chốt: đạt hay chưa. 3. Chủ bấm "Chốt lô", xác nhận "không mở lại được". 4. Lô Đã chốt, lãi/lỗ đông cứng. AuditLog kèm giá vốn cuối.
- **Ngoại lệ:** E1. Thiếu Purchase Invoice → chỉ ra phiếu nhập cần ghi hoá đơn. E2. Còn tồn → gợi ý kiểm kê (UC-19) hoặc huỷ lô (UC-15). E3. Còn đơn đang giữ chỗ/đang giao từ lô → từ chối. Kiểm tra này **hiện chưa có** (A14).
- **Hậu điều kiện:** không nhận chi phí, kiểm kê, hàng hoàn nữa (BR-LO-05).

### UC-15 Huỷ lô quá hạn
- **Tác nhân:** Chủ (spec §6 "Chủ huỷ, hạch toán lỗ").
- **Tiền điều kiện:** lô Quá hạn, còn tồn.
- **Luồng chính:** 1. Cảnh báo "Quá hạn còn tồn" trên Tổng quan (E-10). 2. Chủ bấm "Huỷ phần còn lại", xác nhận số kg. 3. Tồn về 0, giá trị còn lại vào **lỗ hàng hết hạn** của lô (BR-LO-03), lô Đã huỷ. AuditLog. 4. Sau đó chốt được (UC-14).
- **Ngoại lệ:** E1. Còn giữ chỗ trên lô → phải xử lý đơn trước. E2. Lô chưa quá hạn → không cho.
- **Hậu điều kiện:** lỗ hết hạn thể hiện trong báo cáo lô.
- **Chặn hiện tại:** chưa có service, quyền, job chuyển Quá hạn (A15, A16).

### UC-16 Nhập phiếu nhập lô tại cảng
- **Tác nhân:** NV kho, Quản lý, Chủ (`add/change_purchasereceipt`).
- **Tiền điều kiện:** có nhà cung cấp (hoặc tạo nhanh tại chỗ, Quản lý/Chủ có C trên Supplier; NV kho chỉ R).
- **Luồng chính (điện thoại, tại cảng):**
  1. Chọn nhà cung cấp, ngày nhập (mặc định hôm nay).
  2. Thêm từng dòng: mặt hàng, số kg, đơn giá mua. Hạn dùng tự tính = ngày nhập + 90 (BR-MH-02).
  3. Lưu nháp. Kiểm lại. Bấm "Ghi nhận" → mỗi dòng sinh **một lô Nháp** riêng (BR-MH-01). AuditLog.
- **Luồng thay thế:** 2a. Sửa hạn dùng **thấp hơn** mặc định → cho phép. Cao hơn → từ chối (BR-MH-02).
- **Ngoại lệ:**
  - E1. Mạng yếu ở cảng → không được mất dữ liệu đã gõ (Q6).
  - E2. NV kho mở phiếu người khác → không thấy đơn giá (BR-MH-06). Sửa phiếu người khác hoặc phiếu qua ngày → từ chối (spec §1.6). Phạm vi này **chưa có** ở backend (A18).
  - E3. Bấm "Ghi nhận" hai lần → không sinh lô hai lần.
  - E4. Số kg hoặc đơn giá ≤ 0 → từ chối.
- **Hậu điều kiện:** lô Nháp chờ publish (UC-13). Giá vốn ban đầu = đơn giá mua.
- **Chặn hiện tại:** không ghi được dòng phiếu qua API (A18).

### UC-17 Ghi Purchase Invoice (hoá đơn mua)
- **Tác nhân:** Chủ (C theo spec §1.4). Quản lý chỉ R.
- **Luồng chính:** 1. Từ phiếu nhập, bấm "Ghi hoá đơn mua". 2. Số tiền (mặc định = tổng dòng), đã trả = có (BR-MH-03), ngày. 3. Lưu.
- **Ngoại lệ:** E1. Phiếu đã có hoá đơn → cảnh báo trùng. E2. Số tiền lệch tổng dòng → cho lưu nhưng cảnh báo (PA).
- **Hậu điều kiện:** điều kiện chốt lô BR-MH-04 được thoả.

### UC-18 Ghi chi phí mua (landed cost)
- **Tác nhân:** chỉ Chủ (`add_purchasecost`).
- **Luồng chính:** 1. Chọn loại (đá / vận chuyển / bốc vác / khác), số tiền, ngày. 2. Chọn các lô nhận phân bổ (lọc theo phiếu nhập/ngày), cách phân bổ (theo kg mặc định, BR-GV-04). 3. Console **xem trước** số tiền phân bổ từng lô và giá vốn/kg trước → sau. 4. Ghi. Giá vốn lô cập nhật, AuditLog từng lô (BR-GV-03).
- **Ngoại lệ:** E1. Có lô đã chốt trong danh sách → từ chối (BR-GV-02). E2. Không chọn lô nào → từ chối. E3. Ghi hai lần → giá vốn bị cộng hai lần. Cần xác nhận rõ, chống trùng (Q12). E4. Nhập sai → chứng từ không xoá (BR-PQ-10). Cách sửa là chứng từ điều chỉnh âm hay "huỷ chứng từ" (Q16).
- **Hậu điều kiện:** báo cáo lô tính lại (BR-BC-04). Giá vốn ghi trên đơn cũ không đổi (spec §5.2).

### UC-19 Nhập số kiểm kê
- **Tác nhân:** NV kho, Quản lý, Chủ.
- **Luồng chính:** 1. Tạo phiếu kiểm kê, ngày đếm. 2. Console liệt kê các lô đang có tồn. Nhập **số đếm thực tế** từng lô (BR-KK-01), **không hiện số sổ sách** khi đang đếm (PA, chống "đếm cho khớp", Q17). 3. Dòng chênh dương bắt buộc lý do (BR-KK-04). 4. Gửi duyệt.
- **Ngoại lệ:** E1. Lô đã chốt → không cho vào phiếu (BR-LO-05). E2. Người tạo phải là người đăng nhập, không chọn được (BR-PQ-16 đề xuất). Hiện client tự gửi `created_by` (A21).
- **Hậu điều kiện:** tồn sổ **chưa đổi** (BR-KK-02).
- **Chặn hiện tại:** không ghi được dòng kiểm kê qua API (A21).

### UC-20 Duyệt kiểm kê
- **Tác nhân:** Chủ, Quản lý (`approve_stockreconciliation`), **khác người nhập** (BR-KK-02).
- **Luồng chính:** 1. Mở phiếu chờ duyệt: số sổ, số đếm, chênh lệch từng lô, lý do. 2. Người có `view_costprice` thấy thêm giá trị hao hụt. 3. Duyệt → tồn điều chỉnh, hao hụt vào lô (BR-KK-03). AuditLog.
- **Ngoại lệ:** E1. Tự duyệt phiếu mình nhập → từ chối (nút ẩn và backend chặn). E2. Chênh dương thiếu lý do → từ chối. E3. Có giao dịch bán giữa lúc đếm và lúc duyệt → số sổ đã khác. Hiện service lấy số sổ **lúc duyệt**, làm lệch chênh lệch (Q17). E4. Hao hụt bất thường → cảnh báo (BR-KK-06, ngưỡng chưa có, để sau).
- **Hậu điều kiện:** tồn sổ = thực tế.

### UC-21 Báo cáo lãi lỗ theo lô và theo kỳ
- **Tác nhân:** chỉ người có `view_profitreport` (mặc định Chủ, spec §1.7).
- **Luồng chính:**
  1. Tab "Theo lô": bảng tất cả lô (lọc trạng thái, mặt hàng, khoảng ngày nhập) với doanh thu, giá mua, chi phí phân bổ, hao hụt, hàng hỏng/hết hạn, lãi gộp, biên. **Lô chưa chốt gắn nhãn "tạm tính"** (BR-BC-05).
  2. Mở một lô: chi tiết từng khoản, các đơn đã ăn vào lô.
  3. Tab "Theo kỳ": chọn tháng → doanh thu ghi nhận, giá vốn ghi nhận, hoàn tiền trong kỳ, lãi (BR-BC-01…03). Ghi chú "có thể lệch nhẹ với tổng theo lô khi lô chưa chốt" (spec §12.1).
- **Ngoại lệ:** E1. Không có quyền → không thấy menu, API 403. **Không** được hiển thị dạng "—" mà vẫn tải số về máy. E2. Tháng chưa có dữ liệu → trạng thái rỗng rõ ràng.
- **Hậu điều kiện:** không đổi dữ liệu. Xuất file (Excel/CSV) để sau (Q18).
- **Thiếu:** API trả danh sách lô kèm lãi/lỗ (hiện chỉ từng lô, A23).

### UC-22 Danh mục, giá, combo, ưu đãi (đợt 3)
- **Tác nhân:** Chủ (CRUD). Quản lý/NV kho chỉ xem danh mục.
- **Luồng chính:** xem/sửa mặt hàng; thêm giá niêm yết có hiệu lực (valid_from/upto), cấm chồng lấn (BR-DM-03); combo BUNDLE với thành phần (cấm lồng, BR-DM-05); ưu đãi 1 tầng (BR-DM-08). Xem trước "Shop sẽ hiện giá gì hôm nay".
- **Ngoại lệ:** chồng lấn khoảng giá; BUNDLE chứa BUNDLE; xoá mặt hàng đã có giao dịch (BR-PQ-10) → từ chối. **Không sửa giá cũ**: xả hàng cận hạn = thêm giá mới có `valid_upto` (BR-LO-01).
- **Ghi chú:** Admin đang làm được phần này. Đưa vào console chỉ để tiện, không phải để đúng luật.

### UC-23 Nhân sự và nhật ký (đợt 3)
- **Tác nhân:** Chủ (`manage_staff`, xem AuditLog).
- **Luồng chính:** tạo tài khoản + StaffProfile (SĐT bắt buộc); gán Group (cộng dồn); cho nghỉ (`is_active=False`, không xoá, BR-PQ-01); đặt lại mật khẩu. Xem AuditLog lọc theo người/chứng từ/hành động (chỉ đọc, BR-PQ-06).
- **Ngoại lệ:** Chủ tự gỡ Group `chu` của mình khi không còn Chủ nào khác → từ chối. Đổi Group không hồi tố (BR-PQ-03).

### UC-24 Trợ lý AI (chờ Q2)
- **Hiện trạng:** demo regex, chưa nối AI.
- **Nếu làm:** chỉ **đọc và trả lời** trên dữ liệu người hỏi **được phép xem**. Không thực hiện thao tác Tầng 2 thay người (PA).
- **Rủi ro riêng:** rò giá vốn qua câu trả lời (nhân viên hỏi "lô này mua bao nhiêu?"); gửi dữ liệu khách (SĐT, địa chỉ) và giá mua ra bên thứ 3 (nhà cung cấp AI). Theo `decisions.md` 2026-09-09, mọi bên thứ 3 phải qua lớp adapter. Chi phí API hằng tháng. Đề xuất **ngoài phạm vi đợt 1–2**. Nếu Duy muốn giữ, tách thành hồ sơ tính năng riêng.

---

## 6. Business rule

| Mã | Nội dung | Nhãn | Mới / Sửa / Giữ |
|---|---|---|---|
| BR-PQ-04, 05 | Mọi hành động Tầng 2, mọi đổi giá vốn/Refund ghi AuditLog | PA | **Giữ**. Hiện bị vượt qua đường Admin/`PATCH` (3.3, A9, A17) |
| BR-PQ-12 | Kiểm soát phạm vi ở queryset/serializer, không ở giao diện | PA | **Giữ**. Console ẩn nút chỉ là phụ |
| BR-PQ-13 | Test mỗi Group bằng token thật, không lộ field nhạy cảm | PA | **Giữ**. Mở rộng cho mọi endpoint mới của tính năng này |
| **BR-PQ-14** | Mọi chuyển trạng thái chứng từ (đơn, lô, phiếu giao, phiếu hoàn, hàng hoàn, kiểm kê, phiếu nhập) **chỉ** được thực hiện qua thao tác nghiệp vụ tương ứng. Không ghi thẳng field trạng thái, tồn, giá vốn qua sửa chung (API hoặc console) | PA | **Mới** |
| **BR-PQ-15** | Console hiển thị menu và nút theo **hợp** quyền các Group của người đăng nhập. Người không có `view_costprice`/`view_profitreport` thì số nhạy cảm **không được gửi về máy**, không chỉ là không hiển thị | PA | **Mới** (cụ thể hoá BR-PQ-12 và spec §1.6 cho client) |
| **BR-PQ-16** | Người tạo / người duyệt trên chứng từ do hệ thống ghi theo người đăng nhập. Người dùng không chọn hay gửi được | PA | **Mới**. Điều kiện để BR-KK-02, BR-HV-02, BR-MH-06 có nghĩa |
| BR-TT-07 | Xác nhận thanh toán thủ công chỉ Chủ | L/PA | **Giữ** |
| **BR-TT-08** | Xác nhận thanh toán thủ công áp dụng cho **đơn đang Giữ chỗ** (chưa có hoá đơn). Chạy đúng các nhánh của webhook: đủ tiền / thiếu tiền / đơn đã tự huỷ / trùng mã GD | PA | **Mới**. Sửa chỗ gắn sai hiện nay (A2) |
| **BR-TT-09** | Mọi giao dịch lệch (thiếu tiền, về sau khi huỷ, không khớp) phải được Chủ **đóng** bằng một cách xử lý có ghi lại (người, lúc, cách, ghi chú, mã GD hoàn nếu có). Không để treo | PA | **Mới** |
| BR-HT-03, 04, 07 | Mã GD bắt buộc; không hoàn vượt; tách quyền tạo/xác nhận | PA | **Giữ** |
| **BR-HT-09** | Phiếu hoàn chuyển được Chờ hoàn → Thất bại (kèm lý do) → Chờ hoàn. Chỉ Chủ. Ghi AuditLog | PA (spec §9.3) | **Mới** ở mức rule (state machine đã có trong spec, chưa có luật thao tác) |
| **BR-GH-07** | Chỉ huỷ đơn đã thanh toán khi phiếu giao ở Soạn hàng / Chờ lấy / Giao thất bại. Đang giao → phải báo thất bại trước. Hoàn tất → chỉ còn đường phiếu hoàn (BR-GH-05). Huỷ đơn thì phiếu giao đóng theo, biến khỏi việc của NV giao | PA | **Mới** |
| **BR-GH-08** | Gán/đổi NV giao chỉ khi phiếu chưa Đang giao / Hoàn tất. Người được gán phải thuộc `nv_giao` và đang làm. Ghi AuditLog (từ ai → sang ai) | PA | **Mới** |
| BR-GH-04 | Từ lần thất bại thứ 2 nhắc Quản lý/Chủ | PA | **Giữ**. Đợt 1 "nhắc" = cảnh báo trên console (Q11) |
| BR-HV-01, 02 | Về đúng lô gốc; phải duyệt | PA | **Giữ**. Hiện tạo phiếu hàng hoàn chưa qua service (A11) |
| **BR-HV-05** | Số kg mang về theo từng lô không vượt số kg đã xuất từ lô đó cho đơn đó | PA | **Mới** |
| BR-LO-02 | Lô quá hạn loại khỏi tồn khả dụng **ngay** | PA | **Giữ. Hiện bị vi phạm** (A16) |
| **BR-LO-07** | Huỷ phần tồn còn lại của lô Quá hạn là thao tác của Chủ, ghi lỗ hết hạn vào lô, AuditLog. Lô Đã huỷ thì chốt được | PA (từ spec §6) | **Mới** ở mức thao tác. Cần quyền Tầng 2 mới hoặc dùng lại `close_batch` (Q15) |
| BR-LO-04 | Điều kiện chốt lô, có "không còn đơn đang mở" | PA | **Giữ**. Service hiện thiếu điều kiện này (A14) |
| BR-KK-02 | Người nhập ≠ người duyệt | PA | **Giữ** (cần BR-PQ-16) |
| **BR-KK-07** | Chênh lệch kiểm kê tính theo **số sổ tại thời điểm đếm**, không phải lúc duyệt. Nếu có bán/hoàn giữa hai thời điểm thì phải hiện cho người duyệt | PA | **Mới**. Chờ Q17 |
| BR-MH-06 + spec §1.6 | NV kho không xem đơn giá phiếu người khác; chỉ sửa phiếu của mình trong ngày | PA | **Giữ**. Hiện chưa có ở backend (A18) |
| BR-BC-05 | Lô chưa chốt: nhãn "tạm tính" | PA | **Giữ** |

---

## 7. Tác động dữ liệu & tích hợp
(Không thiết kế chi tiết. Chỉ nêu chỗ bị đụng để BE/FE ước lượng.)

**Model/field có khả năng phải thêm hoặc đổi (bất biến #8: cần lý do và migration):**
- `PaymentTransaction`: trạng thái "đã xử lý" + người/lúc/cách xử lý/ghi chú (BR-TT-09).
- `Refund`: hoàn cho giao dịch **không có hoá đơn** (tiền về sau khi huỷ). Hiện FK bắt buộc tới `SalesInvoice` (Q9).
- `DeliveryNote`: trạng thái/cờ "đã huỷ theo đơn" (BR-GH-07); lý do thất bại (UC-10, có thể dùng `note`).
- `Batch`: không cần field mới cho huỷ lô quá hạn (đã có `CANCELLED`, `EXPIRED`); cần **quyền Tầng 2** mới nếu Duy chọn tách (Q15).
- `StockReconciliationLine`: số sổ **tại lúc đếm** (BR-KK-07), nếu Duy chọn.
- Không cần model mới cho nhận diện vai. Đọc từ `User` + `Group` + `StaffProfile` có sẵn.

**API back-office cần bổ sung hoặc sửa** (danh sách nhu cầu, BE tự thiết kế): xem cột "Tình trạng" các dòng A2, A3, A7, A9, A10, A11, A14–A18, A21, A23, A25–A28 ở mục 3.4.

**Màn hình:** 7 màn (Tổng quan, Đơn & tiền, Giao hàng + "Việc giao của tôi", Kho & lô, Mua hàng, Kiểm kê, Báo cáo) + đợt 3 (Danh mục, Nhân sự, Nhật ký).

**Bên thứ 3:** không có mới ở đợt 1–2. Trợ lý AI (nếu làm) là bên thứ 3 mới, phải qua lớp adapter (`decisions.md` 2026-09-09).

**Hạ tầng:** CORS cho site `cangca-erp` đã có (console đang gọi được). Token lưu ở `localStorage`: chấp nhận được cho back-office nội bộ, nhưng điện thoại NV giao dễ mất/cho mượn → cần cách thu hồi phiên khi nhân viên nghỉ (BR-PQ-01, Q5).

---

## 8. Rủi ro Cá Về

| Loại | Rủi ro | Mức | Ghi chú |
|---|---|---|---|
| **FIFO/tồn** | **Lô quá ngày hạn vẫn bán được** trên Shop: chọn lô FIFO chỉ lọc trạng thái, không lọc ngày hạn, và không có job chuyển Quá hạn/Cận hạn/Hết hàng (A16) | **Cao** | Vi phạm BR-LO-02 ngay bây giờ, không phụ thuộc tính năng này. Báo riêng cho Duy. Nên sửa trước đợt 2 |
| **Chứng từ/AuditLog** | `PATCH` chung trên lô, phiếu giao, hàng hoàn, kiểm kê cho ghi thẳng trạng thái/giá vốn/người tạo → vượt state machine, không AuditLog, lách BR-KK-02 (A9, A11, A17, A21) | **Cao** | Console mở thêm nút mà chưa khoá chỗ này thì người dùng vẫn vượt luật được bằng DevTools. **Điều kiện tiên quyết đợt 1** |
| **Chứng từ/AuditLog** | Django Admin sửa được `status`, `qty_available`, `landed_unit_cost` của lô mà không có log (3.3) | Cao | Ngoài phạm vi sửa của BA. Có nên khoá các field này trong Admin sau khi console có thao tác thay thế? (Q3) |
| **Giá vốn** | `PurchaseInvoice.amount` không bị ẩn với Quản lý (có R) → suy ra giá mua (A19) | Trung bình | Q10 |
| **Giá vốn** | Màn báo cáo/kho mới gửi cả số nhạy cảm về máy rồi ẩn bằng CSS (console hiện đã làm kiểu `display:none` cột giá vốn, nhưng dữ liệu không được gửi vì dashboard đã lọc). Endpoint mới dễ quên lọc | Trung bình | BR-PQ-15; test token từng Group (BR-PQ-13) |
| **Giá vốn** | Trợ lý AI trả lời số nhạy cảm cho người không có quyền | Cao nếu làm | Q2 |
| **Phân quyền** | NV giao đang xem được **toàn bộ** đơn và khách (A28) | Trung bình | Lộ SĐT/địa chỉ toàn bộ khách. Tiền điều kiện đợt 1 |
| **Phân quyền** | NV kho sửa/xem đơn giá phiếu nhập của người khác (A18) | Trung bình | Đợt 2 |
| **Tiền** | E-05 hiện **không có đường xử lý**: đơn khách đã trả tiền sẽ tự huỷ sau 30′ nếu webhook lỗi (A2) | **Cao** | Lý do chính đưa UC-03 vào đợt 1 |
| **Tiền** | Tiền về sau khi huỷ **không tạo được phiếu hoàn** (Refund cần hoá đơn) → tiền rời túi không có sổ | Cao | Q9 |
| **Tiền** | Bấm trùng (mạng chậm) khi tạo phiếu hoàn/chi phí mua → nợ khách hoặc giá vốn nhân đôi | Trung bình | Q12 |
| **Hàng** | Huỷ đơn đang giao/đã hoàn tất hiện được phép → kho cộng lại hàng đang ở ngoài hoặc đã đến tay khách | **Cao** | BR-GH-07 |
| **Hàng** | Huỷ đơn sau giao thất bại + duyệt tái nhập → kho **cộng hai lần** (một lần do huỷ, một lần do hàng hoàn) | **Cao** | Q8 |
| **Hàng** | Hoàn tiền một phần (hàng hỏng) nhưng không hoàn/huỷ kho phần đó → tồn sổ lệch thực tế | Trung bình | Q8 |

---

## 9. Ngoài phạm vi
- Thay đổi quy trình P-01…P-10 hay ranh giới quyền Chủ ↔ Quản lý. Tính năng này **thực thi** spec, không đổi spec.
- Hoàn tiền tự động qua cổng (`decisions.md` 2026-09-10).
- Định tuyến, bản đồ, theo dõi vị trí NV giao (BR-GH-02).
- Phí giao hàng (`decisions.md` 2026-09-09).
- Ghi "số kg thực xuất" khi soạn (BR-GH-03, `decisions.md` 2026-09-10).
- Điều chỉnh tồn tay bằng `StockEntry` trên console (A29). Nghiệp vụ chưa định nghĩa, và mọi điều chỉnh đã có đường riêng: kiểm kê, hàng hoàn, huỷ lô.
- Ghi chú ca trực đồng bộ giữa người (giữ nguyên lưu cục bộ trên máy) (PA).
- Thông báo đẩy/SMS/Zalo cho NV giao (đợt 1 chỉ nhắc trên console).
- Xuất Excel báo cáo (Q18).
- Trợ lý AI ở đợt 1–2 (đề xuất, chờ Q2).
- Sửa lỗi lô quá hạn vẫn bán được (A16) là **bug riêng**, không nằm trong tính năng này nhưng phải xử lý trước đợt 2.

---

## 10. Câu hỏi mở

| # | Mức | Câu hỏi | Mặc định PA đề xuất |
|---|---|---|---|
| Q1 | **ĐỎ** | "Đầy đủ" nghĩa là toàn bộ đợt 1 + 2 + 3 trong một lần giao, hay đồng ý làm **đợt 1 (Đơn, tiền, giao hàng) trước**, đợt 2 (Kho, mua hàng, kiểm kê, báo cáo), đợt 3 (Danh mục, nhân sự, nhật ký) sau? Nếu thứ tự ưu tiên khác, anh muốn màn nào trước? | Làm theo 3 đợt ở mục 5.0; đợt này chỉ đợt 1 + các sửa BE tiên quyết |
| Q2 | **ĐỎ** | Trợ lý AI (cột phải) có nằm trong phạm vi lần này không? Nếu có: (a) chỉ đọc hay được thao tác thay người, (b) có chấp nhận gửi dữ liệu đơn/khách/giá vốn ra nhà cung cấp AI bên ngoài không, (c) ngân sách API mỗi tháng? | Ngoài phạm vi đợt 1–2. Bỏ hộp demo hoặc ghi rõ "chưa hoạt động". Làm thì tách hồ sơ riêng, chỉ đọc, qua adapter, tôn trọng quyền giá vốn |
| Q3 | **ĐỎ** | ERP console tiếp tục là **một file HTML vanilla JS** (hiện ~555 dòng; làm đủ 3 đợt có thể lên vài nghìn dòng), hay chuyển sang khung khác (ví dụ dùng chung Next.js như `frontend/`, hoặc một app riêng)? Và sau khi console có thao tác, Django Admin có bị **khoá** các field trạng thái/tồn/giá vốn không, hay vẫn để làm đường cứu hộ? | BA không chọn công nghệ. Chỉ nêu ràng buộc nghiệp vụ cho FE/BE: phải dùng tốt trên điện thoại (Q4), nhiều form có dòng (phiếu nhập, kiểm kê), dễ 1 người maintain (URD §7). Admin: khoá field trạng thái/tồn/giá vốn sau khi đợt tương ứng xong, giữ Admin cho master data |
| Q4 | **ĐỎ** | Mỗi vai dùng thiết bị gì? Cụ thể: (a) NV giao chỉ dùng **điện thoại**? (b) NV kho nhập phiếu nhập **tại cảng bằng điện thoại**? (c) Lộc duyệt/xác nhận tiền chủ yếu trên điện thoại hay máy tính? | Như bảng 4.2: NV giao chỉ điện thoại; NV kho điện thoại ở cảng, máy tính ở kho; Lộc cả hai, ưu tiên điện thoại. → Đợt 1 phải chạy tốt trên màn hình điện thoại cho "Việc giao của tôi" và thao tác duyệt/xác nhận tiền |
| Q5 | VÀNG | Nhân viên nghỉ / mất điện thoại: cần thu hồi phiên đăng nhập ngay không? Phiên giữ bao lâu? | Cho nghỉ (`is_active=False`) thì mọi phiên hết hiệu lực ngay. Phiên không tự hết theo thời gian ở đợt 1 |
| Q6 | VÀNG | Ở cảng mạng yếu: có cần nhập phiếu nhập **khi mất mạng** rồi gửi sau không? | Không làm offline. Chỉ giữ bản nháp trên máy khi mạng rớt và báo rõ "chưa gửi được" |
| Q7 | VÀNG | Ai được gán NV giao: chỉ Chủ/Quản lý, hay cả NV kho (người đóng gói xong giao cho ai đi)? | Chủ, Quản lý, NV kho đều gán được (khớp ma trận §1.4, NV kho có U trên DeliveryNote) |
| Q8 | VÀNG | (a) Có cần **huỷ một phần** đơn (hàng hỏng một mặt hàng khi soạn) ở đợt 1 không? (b) Đơn giao thất bại rồi thôi không giao: kho được cộng lại **chỉ qua duyệt hàng hoàn**, và thao tác huỷ đơn khi đó **không** hoàn kho. Đồng ý? | (a) Không. Đợt 1 hàng hỏng thì huỷ cả đơn + hoàn toàn phần, liên hệ khách đặt lại. (b) Đồng ý, tránh cộng kho hai lần |
| Q9 | VÀNG | Tiền về sau khi đơn đã tự huỷ (hoặc về thiếu mà khách không bù): hoàn tiền ghi sổ ở đâu? `Refund` hiện bắt buộc gắn hoá đơn, mà đơn này không có hoá đơn. Và nếu khách chuyển bù phần thiếu: xác nhận đơn theo **tổng các giao dịch**? | Cho phép phiếu hoàn gắn thẳng vào **giao dịch thanh toán** khi không có hoá đơn (đổi schema, có migration). Thiếu tiền + bù: Chủ xác nhận khi tổng ≥ tổng đơn, chỉ khi đơn chưa tự huỷ |
| Q10 | VÀNG | Quản lý có được thấy **tổng tiền hoá đơn mua** (Purchase Invoice) không? Từ đó suy ra được giá mua. | Không. Ẩn `amount` của hoá đơn mua với người thiếu `view_costprice`, giống đơn giá |
| Q11 | VÀNG | "Nhắc Quản lý/Chủ" sau 2 lần giao thất bại (BR-GH-04) và "có hàng hoàn chờ duyệt": nhắc bằng gì? | Đợt 1: huy hiệu trên menu + mục "Cần chú ý" ở Tổng quan. Không SMS/Zalo |
| Q12 | VÀNG | Chống bấm trùng cho thao tác sinh tiền/giá vốn (tạo phiếu hoàn, ghi chi phí mua, ghi nhận phiếu nhập): chấp nhận "hỏi xác nhận + khoá nút khi đang gửi", hay cần backend chặn trùng tuyệt đối? | Backend chặn trùng cho tạo phiếu hoàn và chi phí mua. Còn lại khoá nút là đủ |
| Q13 | VÀNG | Khi Lộc chuyển khoản hoàn, hệ thống có cần lưu **STK/ngân hàng** của khách không? Hiện Customer không có, khách là guest. | Không lưu. Lộc lấy STK từ giao dịch chuyển tiền đến (sao kê) hoặc gọi khách. Phiếu hoàn chỉ hiện SĐT |
| Q14 | VÀNG | Ngưỡng thời gian ngoài chuỗi lạnh (BR-HV-03, câu hỏi mở #3 của spec) đã có số chưa? | Chưa có thì đợt 1 chỉ hiển thị số giờ ngoài kho, không đề xuất mặc định |
| Q15 | VÀNG | (a) Huỷ lô quá hạn dùng quyền mới riêng hay dùng chung quyền của Chủ (`close_batch`)? (b) Publish lô khi mặt hàng chưa có giá niêm yết: chặn hay chỉ cảnh báo? | (a) Chung với `close_batch` (chỉ Chủ, đều là "đổi con số lời lỗ"). (b) Chỉ cảnh báo |
| Q16 | VÀNG | Chi phí mua ghi sai số tiền: sửa bằng cách nào khi chứng từ không được xoá (BR-PQ-10)? | Ghi chứng từ chi phí **âm** điều chỉnh vào đúng các lô đó, trước khi chốt lô |
| Q17 | VÀNG | Kiểm kê: (a) ẩn số sổ sách khi nhân viên đang đếm? (b) chênh lệch tính theo số sổ lúc đếm hay lúc duyệt? | (a) Ẩn. (b) Lúc đếm; nếu có phát sinh giữa hai thời điểm thì hiện cho người duyệt thấy |
| Q18 | XANH | Có cần xuất báo cáo lãi lỗ ra Excel/CSV không? | Để sau đợt 2 |
| Q19 | XANH | Ghi chú ca trực (cột phải) có cần chia sẻ giữa các nhân viên không? | Giữ lưu trên từng máy như hiện tại |
| Q20 | XANH | Có cần màn "Hàng chờ nhắc việc" hợp nhất (đơn thiếu tiền, phiếu hoàn chờ chuyển, hàng hoàn chờ duyệt, kiểm kê chờ duyệt, lô quá hạn) không? | Đợt 1 gộp vào khối "Cần chú ý" ở Tổng quan |

**Việc Duy nên biết ngay, không phụ thuộc trả lời:** lô quá ngày hạn hiện vẫn bán được trên Shop (A16, vi phạm BR-LO-02). Đây là bug của lõi, nên có hồ sơ sửa riêng.

---

## 11. Quyết định của Duy (2026-09-24) — trả lời câu hỏi ĐỎ

| # | Quyết định (D) |
|---|---|
| Q1 | Làm **cả 3 đợt trong lần này** (đơn/tiền/giao · kho/mua/kiểm kê/báo cáo · danh mục/nhân sự/nhật ký/AI). Vẫn giao theo thứ tự đợt 1 → 2 → 3 để kiểm từng phần. |
| Q2 | **Trợ lý AI làm ngay, CHỈ ĐỌC** — nối Claude thật (Anthropic API), không thao tác thay người. Dữ liệu gửi đi phải tôn trọng quyền người hỏi (không gửi giá vốn nếu thiếu `view_costprice`). Ngân sách API: chưa chốt → câu hỏi còn mở, mặc định đặt giới hạn số lượt/ngày. |
| Q3 | **ERP console chuyển sang Next.js** (cùng stack với `frontend/`, static export lên Firebase `cangca-erp`). Django Admin: giữ làm đường cứu hộ/cấu hình (mặc định VÀNG), nhưng field trạng thái/tồn/giá vốn khoá chỉ đọc cho người không phải superuser. |
| Q4 | NV giao & NV kho dùng **điện thoại** (mobile-first cho màn giao hàng, nhập phiếu tại cảng); Lộc dùng **cả điện thoại lẫn máy tính**. |
| Q5–Q17 | Duy không phản đối → **áp dụng mặc định VÀNG** như mục 10. |

Bổ sung của điều phối viên: lỗi "lô quá hạn vẫn bán được" (BR-LO-02, `allocate_fifo` chỉ lọc status) đưa vào phạm vi, làm **đầu tiên** vì là rủi ro nghiệp vụ nghiêm trọng.

**Key Anthropic (2026-09-24):** Duy đã cung cấp. Lưu ở GCP Secret Manager `cangca-anthropic-api-key` (project keolai-63ec1) — KHÔNG ghi giá trị vào code/doc/.env. Khi deploy: mount vào Cloud Run `cangca-api` thành env `ANTHROPIC_API_KEY` (`--set-secrets ANTHROPIC_API_KEY=cangca-anthropic-api-key:latest`) và cấp `roles/secretmanager.secretAccessor` cho service account của Cloud Run. Không dùng secret `ANTHROPIC_API_KEY` sẵn có trong project (của app khác).

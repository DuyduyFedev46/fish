---
Tài liệu: Business Process Spec (Level 3 — nghiệp vụ chi tiết)
Dự án: Hệ thống Mua hàng – Bán hàng – Quản lý kho cho Vựa Cá (Lộc)
Ngày: 2026-09-10
Người soạn: Duy (BA/PO) — cùng Claude (Product Architect)
Trạng thái: Draft v2 — viết lại mục 1 (phân quyền 3 tầng, thêm vai trò Quản lý, StaffProfile, AuditLog)
Vị trí: Level 3, nằm giữa URD.md (cái gì) và data model (Level 4, chưa viết)
---

# 0. Cách đọc tài liệu này

## 0.1 Nó khác URD ở chỗ nào
`URD.md` trả lời **hệ thống làm được gì**. Tài liệu này trả lời **nó chạy ra sao khi mọi thứ không như ý**: ai được làm gì, chứng từ đi qua những trạng thái nào, luật nào không được vi phạm, và chuyện gì xảy ra ở từng nhánh hỏng. Đây là đầu vào trực tiếp để viết Django models.

## 0.2 Giới hạn của chữ "full"
Lộc chưa vận hành thực tế. Không thể có "full nghiệp vụ" theo nghĩa mô tả đúng cái đang diễn ra — chỉ có **full độ phủ điểm quyết định**: mọi ô đều có câu trả lời, và mỗi câu trả lời đều nói rõ nó đến từ đâu.

## 0.3 Nhãn nguồn — bắt buộc đọc
| Nhãn | Nghĩa | Cách xử lý |
|---|---|---|
| **(L)** | Lộc phát biểu trực tiếp | Yêu cầu thật, không tự sửa |
| **(D)** | Duy quyết định / suy ra | Quyết định của PO |
| **(PA)** | Product Architect đề xuất — **giả định** | Chọn phương án đơn giản nhất; kiểm chứng khi vận hành thật |

Phần lớn tài liệu này mang nhãn **(PA)**. Đó là bản chất của việc thiết kế trước khi vận hành, không phải điểm yếu — nhưng đừng đọc nó như thể Lộc đã duyệt.

---

# 1. Phân quyền

## 1.1 Vì sao bản v1 sai và sửa thế nào

Bản v1 mô tả quyền bằng **động từ nghiệp vụ** ("được soạn hàng", "được duyệt kiểm kê") với 3 vai trò. Duy chất vấn: phải là CRUD, phải có profile, phải có leader. Ba điểm không ngang nhau:

| Điểm | Kết luận |
|---|---|
| **CRUD** | **Nhận — nhưng CRUD một mình không đủ.** Django `contrib.auth` sinh sẵn `add/change/delete/view` cho mọi model, gán qua Group — đó là xương sống và nên viết đúng dạng đó. Nhưng "nhân viên nhập số kiểm kê, chỉ Chủ duyệt" là **chuyển trạng thái**, "chỉ sửa đơn được gán cho mình" là **phạm vi dòng**, "không thấy cột giá vốn" là **phạm vi cột** — không cái nào diễn đạt được bằng CRUD. Nên: **3 tầng**, CRUD là tầng 1. |
| **Profile** | **Nhận — lật lại quyết định 09/09 của chính tôi.** Bản cũ chốt "tham chiếu thẳng Django User, không cần entity riêng". Sai ở chỗ: `User` không có **số điện thoại**, mà khách và Lộc cần gọi được người đang cầm hàng đi giao. Có `StaffProfile` mỏng. Nhưng dừng ở đó — lương/chấm công/hợp đồng/KPI là phần mềm HR, đưa vào đây là đúng cái lý do đã bỏ Frappe. |
| **Leader** | **Nhận, nhưng vì lý do khác với org chart.** Lý do thật: **Lộc đi cảng mua hàng lúc rạng sáng và không thường trực ở kho.** Bản v1 bắt "chỉ Chủ duyệt" cho kiểm kê, hàng hoàn, huỷ đơn — nghĩa là 10h sáng giao thất bại thì hàng nằm chờ tới khi Lộc rảnh. Đó là nút cổ chai thật. Nếu anh muốn Leader chỉ vì sơ đồ tổ chức thì tôi không đồng ý; vì Lộc vắng mặt thì tôi đồng ý. |

## 1.2 Ba tầng quyền

| Tầng | Cơ chế Django | Diễn đạt được gì |
|---|---|---|
| **1. CRUD theo model** | `auth.Permission` tự sinh + `Group` | Ai được tạo/xem/sửa/xoá loại chứng từ nào |
| **2. Hành động tuỳ biến** | `Meta.permissions` (custom perms) | Duyệt, chốt, huỷ, xác nhận — các chuyển trạng thái |
| **3. Phạm vi dòng & cột** | `get_queryset()` lọc + serializer/Admin tách theo role | Chỉ đơn của mình; ẩn cột giá vốn |

Ba tầng phải cùng tồn tại. Chỉ làm tầng 1 thì nhân viên giao hàng thấy toàn bộ đơn của cả kho và đọc được giá vốn từng lô.

## 1.3 Bốn nhóm quyền — cộng dồn, không phải bậc thang

| Group | Ai | Ghi chú |
|---|---|---|
| `owner` | Lộc | Toàn quyền. Thực tế là superuser, nhưng vẫn định nghĩa Group để phân quyền tường minh |
| `manager` | Người Lộc uỷ quyền khi vắng mặt | Duyệt vận hành, **không** đụng tiền và giá vốn |
| `warehouse_staff` | Nhập lô, soạn hàng, kiểm kê | |
| `delivery_staff` | Giao hàng | Chỉ thấy đơn được gán cho mình |

**Cộng dồn, không xếp bậc (PA)**: một người ở vựa nhỏ vừa nhập kho vừa đi giao — gán cả `warehouse_staff` lẫn `delivery_staff`, không cần role thứ năm. Quản lý thường là `manager` + `warehouse_staff`. Thiết kế theo Group cộng dồn nên **thêm người kiêm nhiệm không phải sửa code**; thiết kế theo bậc thang thì phải.

## 1.4 Tầng 1 — Ma trận CRUD theo model

Ký hiệu: **C** tạo · **R** xem · **U** sửa · **D** xoá · **–** không có · **\*** giới hạn phạm vi (xem 1.6)

| Model | `owner` | `manager` | `warehouse_staff` | `delivery_staff` |
|---|---|---|---|---|
| ItemGroup, Item, BundleLine | CRUD | R | R | – |
| PriceList, ItemPrice | CRU– | R | – | – |
| PricingRule | CRUD | R | – | – |
| Supplier | CRUD | CRU– | R | – |
| Customer | CRU– | CRU– | R | R\* |
| Warehouse | CRU– | R | R | – |
| PurchaseReceipt | CRU– | CRU– | CRU–\* | – |
| Batch | CRU– | R | R | – |
| PurchaseInvoice | CRU– | R | – | – |
| **PurchaseCost** | CRU– | – | – | – |
| SalesOrder | R | R | R | R\* |
| SalesInvoice | R | R | R\* | – |
| SalesInvoiceLineBatch | R | – | – | – |
| **Refund** | CRU– | CRU– | – | – |
| DeliveryNote | CRU– | CRU– | CRU– | RU\* |
| ReturnToStock | R | R | CR– | CR– |
| StockEntry | CRU– | CRU– | CRU– | – |
| StockReconciliation | CRU– | CRU– | CRU– | – |
| User, StaffProfile | CRUD | R | R\* | R\* |
| AuditLog | R | – | – | – |

**Hai điều đáng chú ý trong bảng này:**

- **Cột D gần như trống.** Trong hệ thống sổ sách, chứng từ **không bao giờ xoá** — chỉ chuyển trạng thái huỷ. `delete_*` chỉ mở cho master data chưa phát sinh giao dịch (Item, ItemGroup, PricingRule, Supplier). Nếu để nguyên mặc định Django là Chủ xoá được Sales Invoice, thì một cú click làm bốc hơi cả doanh thu lẫn dấu vết giá vốn.
- **SalesOrder và SalesInvoice không ai có `C`.** Chúng do **Hệ thống** tạo (khách đặt trên Shop / webhook xác nhận thanh toán). Người dùng không tạo tay được — chống việc ghi doanh thu khống.

## 1.5 Tầng 2 — Quyền hành động tuỳ biến

| Permission | `owner` | `manager` | Vì sao ranh giới nằm ở đây |
|---|:--:|:--:|---|
| `publish_batch` | ✅ | ✅ | Vận hành thuần |
| `approve_stockreconciliation` | ✅ | ✅ | Vận hành, đã có audit log |
| `approve_returntostock` | ✅ | ✅ | Hàng phải xử lý ngay, không chờ được |
| `cancel_paid_order` | ✅ | ✅ | Khách chờ, không chờ được |
| `create_refund` | ✅ | ✅ | Mới là *ghi nhận nợ khách*, tiền chưa đi |
| `close_batch` | ✅ | ❌ | Chốt số lãi/lỗ — đông cứng vĩnh viễn |
| `add_purchasecost` | ✅ | ❌ | Đụng thẳng vào giá vốn |
| `confirm_refund` | ✅ | ❌ | **Tiền thật rời tài khoản** |
| `confirm_payment_manual` | ✅ | ❌ | Phải đối chiếu sao kê ngân hàng — **chỉ Lộc có quyền xem sao kê** |
| `view_costprice` | ✅ | ❌ | Xem 1.7 |
| `view_profitreport` | ✅ | ❌ | Xem 1.7 |
| `manage_staff` | ✅ | ❌ | Tạo tài khoản, đổi Group |

**Đường ranh (PA)**: Quản lý được uỷ **mọi thứ làm khách phải chờ**; Chủ giữ **mọi thứ làm tiền rời túi hoặc làm đổi con số lời lỗ**. `create_refund` tách khỏi `confirm_refund` chính là để cắt đúng đường này — Quản lý dựng được phiếu hoàn ngay lúc sự việc xảy ra, Lộc chỉ cần bấm chuyển khoản khi rảnh.

## 1.6 Tầng 3 — Phạm vi dòng & cột

**Phạm vi dòng** (lọc trong `get_queryset()`, không phải ẩn ở giao diện):

| Chỗ | Luật |
|---|---|
| `delivery_staff` trên DeliveryNote | Chỉ đơn có `assigned_to = user`; chỉ sửa được field trạng thái, không sửa dòng hàng |
| `delivery_staff` trên SalesOrder / Customer | Chỉ đơn/khách thuộc phiếu giao được gán |
| `warehouse_staff` trên PurchaseReceipt | Chỉ sửa phiếu do chính mình tạo, **trong ngày**; qua ngày phải nhờ Quản lý |
| Nhân viên trên StaffProfile | Chỉ hồ sơ của chính mình |

**Phạm vi cột** — danh sách field nhạy cảm, chỉ `view_costprice` mới thấy:

`Batch.landed_unit_cost` · `Batch.purchase_rate` · `PurchaseReceipt.rate` · toàn bộ `PurchaseCost` · `SalesInvoiceLineBatch.unit_cost` · mọi cột lãi/lỗ trên báo cáo

> **Cảnh báo triển khai — đây là chỗ rò rỉ dễ nhất.** Django Admin ẩn cột thì dễ, nhưng nếu DRF dùng chung một serializer với `fields = '__all__'` thì API trả về đủ giá vốn cho bất kỳ ai gọi được endpoint. **Phải tách serializer theo Group**, và kiểm thử bằng cách gọi API bằng token nhân viên chứ không phải chỉ nhìn màn hình Admin.

## 1.7 Quản lý có được xem giá vốn không?

Mặc định **KHÔNG** (PA). Lý do: giá mua tại cảng là lợi thế đàm phán của Lộc với đầu mối; ở vựa cá nhân viên thường là người quen, thông tin đi nhanh.

Đây là **mặc định rẻ để lật** — chỉ là gán thêm 2 permission vào Group `manager`, không sửa dòng code nào. Nên tôi chốt luôn thay vì hỏi. Lộc muốn khác thì đổi trong Admin.

## 1.8 StaffProfile — có, nhưng mỏng

| Trong phạm vi | Ngoài phạm vi |
|---|---|
| Số điện thoại (**bắt buộc**) | Lương, phụ cấp |
| Họ tên hiển thị | Chấm công, ca kíp |
| Ngày vào làm | Hợp đồng lao động |
| Trạng thái: đang làm / nghỉ | KPI, đánh giá |
| Ghi chú | Nghỉ phép |

> **Quyết định kiến trúc quan trọng**: mọi FK nghiệp vụ (người giao, người nhập lô, người duyệt) **trỏ vào `User`**, `StaffProfile` chỉ là `OneToOneField` mở rộng. Nếu trỏ FK vào `StaffProfile` thì ai chưa có hồ sơ là không làm được việc, và migrate về sau rất phiền. Chọn sai chiều này là cái đắt duy nhất trong toàn bộ mục 1.

## 1.9 Nghỉ việc & lưu vết

| Mã | Luật |
|---|---|
| BR-PQ-01 | Nhân viên nghỉ → `User.is_active = False` + `StaffProfile.status = nghỉ`. **Không xoá tài khoản.** |
| BR-PQ-02 | Mọi FK trỏ người dùng dùng `on_delete=PROTECT`. Chứng từ cũ phải giữ nguyên tên người thực hiện. |
| BR-PQ-03 | Đổi Group của một người **không** hồi tố lên chứng từ đã tạo. |

## 1.10 AuditLog

Phân quyền mà không có log thì chỉ chặn được nhầm lẫn, không truy được trách nhiệm. Django Admin có `LogEntry` sẵn nhưng **chỉ ghi thao tác trong Admin** — hành động qua API không được ghi. Cần model riêng.

| Mã | Luật |
|---|---|
| BR-PQ-04 | Mọi permission ở **Tầng 2** phải ghi `AuditLog`: ai, khi nào, chứng từ nào, giá trị trước → sau. |
| BR-PQ-05 | Mọi thay đổi `Batch.landed_unit_cost` và mọi `Refund` đổi trạng thái **bắt buộc** có AuditLog — không có log thì từ chối ghi. |
| BR-PQ-06 | AuditLog **chỉ ghi thêm**, không sửa, không xoá, kể cả Chủ. |
| BR-PQ-07 | Hành động của Hệ thống (job huỷ TTL, webhook xác nhận) ghi log với actor = `system`, không mượn tài khoản người. |

## 1.11 Business rules phân quyền

| Mã | Luật |
|---|---|
| BR-PQ-08 | Quyền gán qua **Group**, không gán trực tiếp cho user. Ngoại lệ phải có ghi chú lý do. |
| BR-PQ-09 | Người dùng có thể thuộc **nhiều Group**; quyền là hợp của các Group. |
| BR-PQ-10 | `delete_*` chỉ mở cho master data chưa phát sinh giao dịch. Chứng từ **không bao giờ** xoá — chỉ huỷ bằng trạng thái. |
| BR-PQ-11 | Không người dùng nào tạo tay được SalesOrder / SalesInvoice. |
| BR-PQ-12 | Kiểm soát phạm vi phải nằm ở **queryset và serializer**, không phải ở giao diện. Ẩn nút không phải là phân quyền. |
| BR-PQ-13 | Mỗi Group phải có ít nhất một bài kiểm thử gọi API bằng đúng token của Group đó, xác nhận không lộ field nhạy cảm. |

---

# 2. Danh mục quy trình

| Mã | Quy trình | Actor chính |
|---|---|---|
| P-01 | Quản lý danh mục, giá niêm yết, combo | Chủ |
| P-02 | Mua hàng & nhập lô tại cảng | Chủ, NV kho |
| P-03 | Ghi nhận chi phí mua hàng & tính giá vốn lô | Chủ |
| P-04 | Vòng đời lô & chốt lô | Chủ, Hệ thống |
| P-05 | Bán hàng trên Shop (đặt → giữ chỗ → thanh toán) | Khách, Hệ thống |
| P-06 | Soạn hàng & giao hàng | NV kho, NV giao |
| P-07 | Huỷ đơn & hoàn tiền | Chủ, Quản lý |
| P-08 | Hàng giao thất bại quay về kho | NV giao, Quản lý/Chủ |
| P-09 | Kiểm kê định kỳ & xử lý hao hụt | NV kho, Quản lý/Chủ |
| P-10 | Báo cáo giá vốn & lãi lỗ | Chủ |

---

# 3. P-01 — Danh mục, giá niêm yết, combo

## 3.1 Ba dạng combo *(D chọn hướng "flex", PA giới hạn phạm vi)*

| Dạng | Cơ chế | Kho trừ ở đâu | Dùng khi |
|---|---|---|---|
| **Gói có công thức** (BUNDLE) | `Item.item_type=BUNDLE` + `BundleLine` (thành phần, định mức kg) | Nổ ra thành phần, FEFO từng thành phần *(sửa 2026-09-26, xem decisions.md)* | "Set lẩu 2kg: 1kg tôm + 0.5kg mực + 0.5kg cá" |
| **Đóng gói sẵn** | Không cần cơ chế mới — `Item` thường có lô riêng | Chính lô của nó | Khay 500g đóng sẵn từ lúc nhập |
| **Ưu đãi** (`PricingRule`) | Điều kiện 1 tầng → giảm tiền hoặc % | Từng mặt hàng riêng | "Mua ≥ 3kg tôm giảm 10%" |

**Ranh giới cố ý (PA)** — PricingRule **chỉ 1 tầng điều kiện, không lồng nhau, không cộng dồn** (nhiều rule cùng khớp → chọn rule có lợi nhất cho khách), không ngân sách khuyến mãi. **Có mã giảm giá dạng một tầng** (mã công khai, mỗi đơn tối đa một mã, không cộng dồn với PricingRule), quy tắc ở BR-DM-17…24. Không có mã riêng từng khách, không mã phát sau khi mua. *((D) 2026-10-10, xem decisions.md — lật ý "không mã giảm giá" của 2026-09-10)* Đây là chỗ dừng có chủ đích: rule engine tổng quát làm chi phí kiểm thử tăng theo cấp số nhân và là thứ giết dự án do một người maintain.

## 3.2 Business rules
| Mã | Luật |
|---|---|
| BR-DM-01 | **(D) 2026-10-10** — **Mặt hàng thường (SIMPLE) bán theo kg; combo (BUNDLE) bán theo combo, số lượng là số nguyên. Không quy đổi giữa hai đơn vị. Kho vẫn trừ theo kg ở mức thành phần (BR-DM-06, BR-BH-07).** *(sửa, (D) 2026-10-10, xem decisions.md; thay "Mọi mặt hàng bán theo `Kg`. Không có quy đổi đa đơn vị.")* |
| BR-DM-02 | Giá bán **luôn** lấy từ Item Price hiệu lực tại thời điểm đặt hàng (`valid_from ≤ now ≤ valid_upto`). Không cho nhập giá tay trên đơn. |
| BR-DM-03 | Hai Item Price cùng mặt hàng, cùng bảng giá, **không được chồng lấn** khoảng hiệu lực. |
| BR-DM-04 | BUNDLE có giá niêm yết **độc lập**, không tự tính bằng tổng giá thành phần. |
| BR-DM-05 | BUNDLE **không được chứa BUNDLE khác** (không lồng cấp). |
| BR-DM-06 | Tồn khả dụng của BUNDLE là giá trị **tính ra, không lưu**: `min( floor(tồn khả dụng thành phần i / định mức i) )`. |
| BR-DM-07 | Sửa `BundleLine` **không** hồi tố lên đơn đã đặt — đơn giữ ảnh chụp công thức tại thời điểm đặt. |
| BR-DM-08 | Nhiều PricingRule cùng khớp → áp dụng **duy nhất một** rule có lợi nhất cho khách. Không cộng dồn giữa các PricingRule. Quan hệ giữa PricingRule và mã giảm giá theo BR-DM-18. *(sửa, (D) 2026-10-10, xem decisions.md; phần PricingRule giữ nguyên)* |
| BR-DM-17 | **(D) 2026-10-10** — **Mã giảm giá** là mã công khai dùng chung, có: mã (duy nhất, không phân biệt hoa thường), tên chương trình, kiểu giảm (số tiền hoặc phần trăm), mức giảm, trần số tiền giảm (bắt buộc khi giảm theo phần trăm), giá trị đơn tối thiểu, thời điểm bắt đầu và kết thúc (ngày giờ, giờ Việt Nam), tổng số lượt, mô tả điều kiện hiển thị cho khách, trạng thái bật/tắt. V1 mã áp trên tổng giá trị hàng của đơn, không áp riêng từng mặt hàng. Giá trị đơn tối thiểu so với tổng giá trị hàng **trước** mọi giảm giá. Mã không bao giờ bị xoá, chỉ tắt. *(mới, (D) 2026-10-10, xem decisions.md)* |
| BR-DM-18 | **(D) 2026-10-10** — Mỗi đơn dùng **tối đa một mã**. Mã **không cộng dồn** với PricingRule: hệ thống tính cả hai và áp **một** cái có số tiền giảm lớn hơn cho khách. Hoà thì áp PricingRule và không tính lượt mã. Khi mã không được áp vì ưu đãi tự động bằng hoặc lợi hơn, Shop báo rõ lý do. *(mới, (D) 2026-10-10, xem decisions.md)* |
| BR-DM-19 | **(D) 2026-10-10** — Mã và số tiền giảm **đóng băng lúc tạo đơn**, như giá (BR-BH-08). Số tiền giảm phân bổ vào từng dòng đơn theo tỉ lệ giá trị dòng (như PricingRule theo đơn) để lãi lỗ theo lô đúng. Mã hết hiệu lực, hết lượt hoặc bị tắt giữa lúc xem giỏ và lúc đặt thì **không tạo đơn**; Shop hỏi khách có đặt tiếp không dùng mã. Hệ thống không tự đổi số tiền khách đã thấy. *(mới, (D) 2026-10-10, xem decisions.md)* |
| BR-DM-20 | **(D) 2026-10-10** — **Lượt dùng mã**: giữ một lượt khi tạo đơn (cùng giao dịch với giữ chỗ); lượt thành "đã dùng" khi đơn được thanh toán; **nhả lượt** khi đơn tự huỷ vì hết giờ giữ chỗ (job idempotent, BR-BH-04). Đơn đã thanh toán rồi bị huỷ (toàn phần hay một phần) **không trả lượt**. Số lượt đang giữ + đã dùng **không bao giờ vượt** tổng lượt, kể cả khi nhiều khách đặt cùng lúc. *(mới, (D) 2026-10-10, xem decisions.md)* |
| BR-DM-21 | **(D) 2026-10-10** — **Trần và sàn**: số tiền giảm của mã ≤ **50%** tổng giá trị hàng của đơn (tham số cấu hình) và ≤ trần tiền của mã. Tổng đơn sau giảm luôn > 0 đồng và là số nguyên đồng (BR-BH-15). ERP chặn tạo mã có mức phần trăm > 50%. *(mới, (D) 2026-10-10, xem decisions.md; trần 50% giữ tới khi luật sư xác minh bản gốc NĐ 239/2026)* |
| BR-DM-22 | **(D) 2026-10-10** — Mã **đang chạy** chỉ được sửa theo hướng có lợi cho khách (gia hạn, tăng lượt, hạ đơn tối thiểu, tăng mức trong trần). Không được nâng đơn tối thiểu, giảm mức, rút ngắn hạn hay giảm tổng lượt. Muốn đổi bất lợi thì tắt mã và tạo mã mới. Tắt mã trước hạn phải chọn lý do (hết ngân sách, sự cố, khác). Bật lại mã đã tắt được nếu còn hạn và còn lượt. Mọi tạo, sửa, tắt, bật ghi AuditLog có giá trị trước → sau. *(mới, (D) 2026-10-10, xem decisions.md)* |
| BR-DM-23 | **(D) 2026-10-10** — **Quyền**: tạo, sửa, tắt mã cần quyền Tầng 2 mới `manage_voucher`, **mặc định chỉ Chủ**; Chủ uỷ cho Quản lý ở màn Phân quyền (như "Sửa giá bán"). Màn xem lượt dùng chỉ hiện mã đơn, số tiền giảm, thời điểm, trạng thái lượt; **không** hiện tên, SĐT, địa chỉ khách; **không** hiện giá vốn hay lãi lỗ. *(mới, (D) 2026-10-10, xem decisions.md)* |
| BR-DM-24 | **(D) 2026-10-10** — **Công khai điều kiện trước khi đặt**: khi mã hợp lệ, giỏ hiện mức giảm, đơn tối thiểu, hạn dùng, câu "Số lượt có hạn", câu "Không áp dụng cùng ưu đãi khác; Cá Về tự chọn mức có lợi hơn cho bạn". Khi mã không dùng được, Shop nêu **đúng một lý do**: mã không đúng, hết hạn, chưa đủ đơn tối thiểu (kèm số còn thiếu), hết lượt, ưu đãi khác lợi hơn. Shop không hiện số lượt còn lại. API kiểm mã công khai có giới hạn tần suất và chỉ trả kết quả kiểm, không trả danh sách mã hay dữ liệu đơn khác. *(mới, (D) 2026-10-10, xem decisions.md)* |
| BR-DM-25 | **(D) 2026-10-10** — Trường thông tin mặt hàng hiện công khai trên Shop (ghi chú ngắn, quy cách, bảo quản, nguồn hàng, mô tả) **không** chứa giá, tên nhà cung cấp, tên tàu, ngày nhập lô, mã lô, số điện thoại. "Nguồn hàng" ghi vùng biển hoặc cảng. Câu khẳng định về sơ chế, cấp đông, đóng gói chỉ ghi khi Lộc xác nhận đúng sự thật tạm chưa ghi các câu này (D 11/10: hỏi Lộc L8–L9 ở `doc/ops/hoi-loc.md`). *(mới, (D) 2026-10-10, xem decisions.md)* |

---

# 4. P-02 — Mua hàng & nhập lô

## 4.1 Luồng
Mua trực tiếp tại cảng, **không có đơn đặt hàng trước** (L). NV kho/Chủ ghi nhận ngay:

`Chọn nhà cung cấp → nhập từng mặt hàng + số kg + đơn giá mua → hệ thống sinh Lô (Batch) → tự tính hạn dùng = ngày nhập + 90 ngày → lô ở trạng thái Nháp`

## 4.2 Business rules
| Mã | Luật |
|---|---|
| BR-MH-01 | Mỗi lần nhập của **một mặt hàng** sinh **một lô riêng**. Không gộp lô kể cả cùng ngày cùng nhà cung cấp — vì giá mua khác nhau. |
| BR-MH-02 | Hạn dùng lô = ngày nhập + `shelf_life_in_days` (mặc định 90). Cho phép sửa tay xuống thấp hơn, **không cho sửa cao hơn**. |
| BR-MH-03 | Mua tại cảng **trả tiền ngay**, Purchase Invoice ghi `is_paid=true`. Không công nợ nhà cung cấp *(PA — mặc định để không treo tiếp; câu hỏi mở #2)*. |
| BR-MH-04 | Purchase Invoice tách riêng khỏi Purchase Receipt (D — kiểm đếm vật lý ≠ ghi chi phí), nhưng phải tồn tại trước khi chốt lô. |
| BR-MH-05 | Lô ở trạng thái **Nháp** không hiện trên Shop. Phải publish thủ công (`publish_batch`). |
| BR-MH-06 | Đơn giá mua là **field nhạy cảm** — NV kho nhập được nhưng không xem lại được phiếu của người khác (xem 1.6). |
| BR-MH-08 | 🟡 **Trả NCC** phần tồn lô Quá hạn: ghi số kg (xuất kho `SUPPLIER_RETURN`) và số tiền NCC hoàn nếu có; tiền NCC hoàn giảm tổng chi phí lô (BR-BC-04). Giả định: mua tại cảng trả tiền ngay (decisions 10/09), việc NCC hoàn tiền là thoả thuận ngoài hệ thống, hệ thống chỉ ghi sổ. Tiền NCC hoàn là số nhạy cảm (chỉ Chủ xem) *(mới 2026-09-30, PA, Duy duyệt 30/09)*. |

---

# 5. P-03 — Chi phí mua hàng & giá vốn lô *(D chốt: có gom landed cost)*

## 5.1 Luồng
`Purchase Cost` là chứng từ riêng, gắn với **một hoặc nhiều** Purchase Receipt:

| Trường | Nội dung |
|---|---|
| Loại chi phí | Đá / Vận chuyển / Bốc vác / Khác |
| Số tiền | |
| Phân bổ theo | **Số kg** hoặc **Giá trị** |
| Áp cho | Danh sách lô nhận phân bổ |

Ghi nhận → cập nhật `Batch.landed_unit_cost = (tổng giá mua lô + chi phí phân bổ vào lô) / số kg nhập`.

**Chỉ Chủ** có `add_purchasecost` — đây là chứng từ đụng thẳng vào giá vốn.

## 5.2 Vấn đề giá vốn hồi tố — và cách xử lý
Chi phí phụ thường về **sau** khi lô đã bán được vài kg. Hai lựa chọn: khoá kỳ (bắt nhập chi phí trong ngày) hay cho nhập sau rồi tính lại. Chọn **tính lại**, với quy ước rõ ràng:

| Con số | Nguồn | Tính chất |
|---|---|---|
| Giá vốn ghi trên dòng hoá đơn | Ảnh chụp `landed_unit_cost` tại thời điểm bán | **Chỉ báo** — có thể lệch nếu chi phí về sau |
| Lãi/lỗ theo **lô** | Tính lại từ `landed_unit_cost` hiện hành | **Nguồn sự thật** |

**Trade-off phải chấp nhận (PA)**: hai con số này có thể không khớp nhau trong lúc lô còn mở. Đổi lại, không phải bắt Lộc nhập đủ chứng từ chi phí ngay tại cảng — điều gần như chắc chắn sẽ không xảy ra trong thực tế. Chốt lô là lúc hai con số hoà giải.

## 5.3 Business rules
| Mã | Luật |
|---|---|
| BR-GV-01 | `Batch.landed_unit_cost` = (giá mua lô + chi phí phân bổ) / số kg nhập ban đầu. Mẫu số **không** đổi khi có hao hụt. |
| BR-GV-02 | Không cho thêm Purchase Cost vào lô **đã chốt**. |
| BR-GV-03 | Mỗi lần `landed_unit_cost` đổi phải ghi AuditLog (BR-PQ-05) — giá vốn là số nhạy cảm, không được đổi âm thầm. |
| BR-GV-04 | Phân bổ theo kg là mặc định. Theo giá trị chỉ dùng khi lô chênh lệch giá mua lớn. |

---

# 6. P-04 — Vòng đời lô

```mermaid
stateDiagram-v2
    [*] --> Nhap: Purchase Receipt
    Nhap --> DangBan: publish_batch
    DangBan --> CanHan: còn ≤ 14 ngày tới hạn (hệ thống)
    DangBan --> HetHang: tồn = 0
    CanHan --> HetHang: tồn = 0
    CanHan --> QuaHan: qua ngày hạn dùng
    QuaHan --> Huy: Chủ huỷ, hạch toán lỗ
    HetHang --> DaChot: close_batch (chỉ Chủ)
    Huy --> DaChot: close_batch (chỉ Chủ)
    DaChot --> [*]
```

| Mã | Luật |
|---|---|
| BR-LO-01 | Lô **Cận hạn**: hệ thống chỉ **cảnh báo**, không tự giảm giá. Muốn xả giá thì Chủ tạo Item Price mới có `valid_upto` *(PA — tự động giảm giá là quyết định kinh doanh, không để máy làm)*. |
| BR-LO-02 | Lô **Quá hạn** bị loại khỏi tồn khả dụng **ngay**, kể cả còn kg. Không bán được nữa. |
| BR-LO-03 | Huỷ lô quá hạn → toàn bộ giá trị tồn còn lại hạch toán **lỗ hàng hết hạn** vào chính lô đó. |
| BR-LO-04 | **Chốt lô** yêu cầu: **tồn = 0**, Purchase Invoice đã có, không còn đơn đang mở tham chiếu lô. Lô Quá hạn còn tồn phải xử lý hết phần tồn (BR-LO-07) trước khi chốt — bỏ ngoại lệ tạm thời "chốt thẳng lô Quá hạn" của S04 *(sửa 2026-09-30, Duy duyệt 30/09)*. |
| BR-LO-05 | Lô **đã chốt** khoá vĩnh viễn: không sửa chi phí, không kiểm kê, không hoàn hàng về. Lãi/lỗ đông cứng. |
| BR-LO-06 | Ngưỡng cận hạn 14 ngày là **tham số cấu hình**, không hard-code. |
| BR-LO-07 | Lô Quá hạn còn tồn → hệ thống **cảnh báo** (Cần chú ý, Tiếp theo). Chủ xác nhận phần tồn là **Đã huỷ** (BR-LO-03, ghi lỗ) hoặc **Đã trả NCC** (BR-MH-08), được chia nhiều lần. Không xác nhận khi lô còn giữ chỗ. Số kg xác nhận phải khớp tồn đang hiển thị *(mới 2026-09-30, Duy duyệt 30/09)*. |

---

# 7. P-05 — Bán hàng trên Shop

## 7.1 Danh tính khách *(PA)*
Guest checkout, không đăng nhập ở V1. `Customer` gộp theo **số điện thoại** làm khoá tự nhiên — đặt lần 2 cùng SĐT thì gắn vào cùng khách, tự có lịch sử mua. Tra đơn theo BR-BH-25 (**mã đơn + SĐT đầy đủ**, hoặc mã đơn + mã tra đơn tạm thời). *(sửa, (D) 2026-10-10, xem decisions.md; thay "mã đơn + 4 số cuối SĐT")* Thêm đăng nhập OTP sau này không đổi schema.

Khách **không phải là `User`** trong hệ thống — không có tài khoản, không nằm trong ma trận Group ở mục 1.

## 7.2 State machine đơn hàng
```mermaid
stateDiagram-v2
    [*] --> GiuCho: Khách đặt, giữ kg trong lô
    GiuCho --> TuHuy: quá 30' không có tiền (hệ thống)
    GiuCho --> DangXuLy: tiền về đủ — xuất hoá đơn, trừ kho, ghi doanh thu (một bước)
    DangXuLy --> HoanTat: phiếu giao cuối cùng Hoàn tất (Hệ thống, BR-BH-18)
    DangXuLy --> DaHuy: cancel_paid_order (P-07)
    TuHuy --> [*]
    DaHuy --> [*]
    HoanTat --> [*]
```
Trạng thái `PAID` (Đã thanh toán) giữ trong DB nhưng không dùng ở V1 (BR-BH-21). Bước con của Đang xử lý (chờ gọi xác nhận, soạn, giao) đọc từ phiếu giao. *(sửa 2026-10-08, W37, Duy duyệt 07/10)*

| Mã | Luật |
|---|---|
| BR-BH-18 | **(D + PA) 2026-10-07** — Đơn `PROCESSING` sang **Hoàn tất** khi mọi phiếu giao chưa huỷ của hoá đơn đều đã Hoàn tất, và có ít nhất một phiếu Hoàn tất. Hệ thống chuyển trong **cùng giao dịch** với thao tác làm phiếu cuối cùng sang Hoàn tất. Đơn đã huỷ không bao giờ sang Hoàn tất, và phiếu của đơn đã huỷ không sang Hoàn tất được (BR-GH-24). Không ai bấm tay "Hoàn tất đơn". Bước chuyển ghi AuditLog `complete_order`, người làm là Hệ thống, kèm mã phiếu giao gây ra; không chép dữ liệu cá nhân. *(D: cạnh này đã có ở §7.2; PA: điều kiện nhiều phiếu, cùng giao dịch. W37, Duy duyệt 07/10)* |
| BR-BH-19 | **(D + PA) 2026-10-07** — V1 trả trước 100%, nên điều kiện "đã thu đủ tiền" được bảo đảm từ lúc có hoá đơn. Hoàn tất **không** xét lại tiền và không xét phiếu hoàn đang chờ. *(D: decisions 26/09. W37, Duy duyệt 07/10)* |
| BR-BH-20 | **(PA) 2026-10-07** — Đơn Hoàn tất vẫn lập phiếu hoàn được (một phần hoặc toàn phần), trạng thái đơn **không đổi** vì hoàn tiền. Huỷ đơn Hoàn tất bị chặn (BR-GH-05). *(theo BR-GH-05, BR-HT-01. W37, Duy duyệt 07/10)* |
| BR-BH-21 | **(PA) 2026-10-07** — Trạng thái `PAID` "Đã thanh toán" **không dùng** ở V1. Thanh toán đủ, xuất hoá đơn và trừ kho là một bước, đơn sang thẳng "Đang xử lý". Bước con (chờ gọi xác nhận, soạn, giao) đọc từ phiếu giao. Giữ mã trong DB, không xoá, ẩn khỏi bộ lọc và thanh bước. *(W37, Duy duyệt 07/10; thay hai cạnh qua `DaThanhToan` của sơ đồ cũ)* |

## 7.3 Giữ chỗ, tồn hiển thị, tranh lô cuối *(PA)*
| Mã | Luật |
|---|---|
| BR-BH-01 | **(D) 2026-10-10** — **Tồn khả dụng = tồn sổ − đang giữ chỗ; hệ thống dùng số này để chặn bán vượt. Shop không hiển thị số này mà chỉ hiển thị mức tồn theo BR-BH-23. API công khai không trả số kg tồn.** *(sửa, (D) 2026-10-10, xem decisions.md; thay "Tồn khả dụng hiển thị trên Shop = …")* |
| BR-BH-02 | Giữ chỗ ghi ở **mức lô**, khoá dòng lô khi tạo đơn. Hai khách tranh lô cuối: người tạo đơn trước thắng, người sau thấy hết hàng ngay tại bước đặt. |
| BR-BH-03 | TTL giữ chỗ **30 phút** (D). Job nền quét và nhả. |
| BR-BH-04 | Job nhả giữ chỗ phải **idempotent** và có giám sát — job này chết thì hàng bị khoá vô hình, không ai biết cho tới khi Shop báo hết hàng oan. |
| BR-BH-05 | **(D) 2026-09-26** — Chọn lô theo **FEFO** (hết hạn trước xuất trước): trong các lô *bán được* (BR-LO-02 lọc trước), lô có **hạn dùng sớm nhất** xuất trước. Cùng hạn thì lô **nhập sớm hơn** trước; vẫn trùng thì lô **tạo trước** trước, để thứ tự luôn cố định. Áp dụng cho mọi mặt hàng, kể cả từng thành phần combo. Khách không chọn lô (BR-PQ-12); V1 không cho ai chọn tay lô khác FEFO. *(sửa 2026-09-26, xem decisions.md; thay "FIFO theo ngày nhập")* |
| BR-BH-06 | Một dòng đơn **được phép ăn nhiều lô**. Bắt buộc lưu bảng phân bổ: `dòng ↔ lô ↔ số kg ↔ đơn giá vốn`. **Không có bảng này thì không tồn tại báo cáo giá vốn theo lô.** |
| BR-BH-07 | Đơn BUNDLE giữ chỗ **đồng thời tất cả thành phần**; thiếu một thành phần thì cả đơn không tạo được. |
| BR-BH-08 | Giá và công thức BUNDLE **đóng băng** tại thời điểm tạo đơn. Đổi giá niêm yết sau đó không ảnh hưởng đơn đang giữ chỗ. |
| BR-BH-09 | Địa chỉ giao **bắt buộc** ngay bước đặt (L — 100% giao tận nhà). |
| BR-BH-10 | **Không có trường phí giao hàng** trên đơn (L — outscope hoàn toàn). |
| BR-BH-11 | **(D) 2026-09-26** — Phân bổ lô được **chốt một lần lúc tạo đơn**. Khi thanh toán, hệ thống trừ kho đúng các lô đã giữ chỗ, **không chọn lại** lô (kể cả khi đã có lô mới hạn sớm hơn). Đơn đã phân bổ không bị phân bổ lại khi có lô mới hay khi đổi quy tắc chọn lô. *(sửa 2026-09-26, xem decisions.md)* |
| BR-BH-22 | **(D) 2026-10-10** — **Số lượng đặt**: mặt hàng thường đặt **từ 1 kg** và là bội của **0,5 kg**; combo đặt **số nguyên từ 1**. Mức tối thiểu và bước là tham số cấu hình. Hệ thống kiểm ở máy chủ lúc tạo đơn; sai thì từ chối cả đơn, không giữ chỗ. *(mới, (D) 2026-10-10, xem decisions.md)* |
| BR-BH-23 | **(D) 2026-10-10** — **Mức tồn trên Shop** chỉ có ba giá trị: Còn hàng, Sắp hết, Hết hàng. "Hết hàng" khi tồn khả dụng (BR-BH-01, BR-DM-06) **nhỏ hơn mức tối thiểu** của BR-BH-22; vì vậy đuôi lô dưới 1 kg không bán trên Shop, Lộc bán ngoài hoặc điều chỉnh tồn ở ERP. "Sắp hết" khi dưới ngưỡng cấu hình riêng cho kg và cho combo (mặc định dưới 3 kg, dưới 3 combo). Món hết vẫn hiện, xếp cuối, nút "Liên hệ chúng tôi". *(mới, (D) 2026-10-10, xem decisions.md)* |
| BR-BH-24 | **(D) 2026-10-10** — Lỗi không đủ hàng trả về Shop (lúc đặt) là lỗi **theo từng dòng**, chỉ gồm mã hàng và mức "hết" hoặc "không đủ". **Không** chứa số kg còn, số kg thiếu, mã lô. *(mới, (D) 2026-10-10, xem decisions.md)* |
| BR-BH-25 | **(D) 2026-10-10** — **Tra đơn công khai** cần một trong hai: (a) mã đơn + SĐT đặt hàng đầy đủ, gửi trong thân request, so khớp sau khi chuẩn hoá; (b) mã đơn + **mã tra đơn tạm thời** do hệ thống cấp lúc tạo đơn hoặc lúc tra đúng. Mã tra đơn chỉ chứa mã đơn và hạn dùng, không chứa dữ liệu cá nhân, không đặt trên URL. SĐT không bao giờ nằm trên URL hay lưu ở trình duyệt. Sai thì báo một câu chung, không nói phần nào sai. Có giới hạn tần suất theo IP và theo mã đơn. Đường tra bằng 4 số cuối bị gỡ. *(mới, (D) 2026-10-10, xem decisions.md; thay cách tra "mã đơn + 4 số cuối SĐT" ở §7.1)* |
| BR-BH-26 | **(D) 2026-10-10** — **Trang đơn công khai** chỉ gồm: mã đơn, nhãn trạng thái, mốc giờ (đặt, trả tiền, giao xong), bước giao, dòng món (tên, đơn vị, số lượng, thành tiền), mã và số tiền giảm, tổng, giờ gọi xác nhận, nhãn lý do huỷ lấy từ **bảng nhãn cố định**. **Không** có tên, SĐT, địa chỉ người nhận, mã lô, ngày nhập, giá vốn, ghi chú tự do của nhân viên. *(mới, (D) 2026-10-10, xem decisions.md)* |
| BR-BH-27 | **(D) 2026-10-10** — **Chống tạo đơn trùng**: mỗi lần khách mở bước đặt hàng có một mã yêu cầu; gửi lại cùng mã yêu cầu thì hệ thống trả lại đơn đã tạo, không tạo đơn mới, không giữ chỗ lần hai, không giữ thêm lượt mã. *(mới, (D) 2026-10-10, xem decisions.md)* |
| BR-BH-28 | **(D) 2026-10-10** — Ở V1, khách **không tự huỷ** đơn trên Shop. Đơn giữ chỗ chỉ kết thúc bằng thanh toán hoặc tự huỷ khi hết thời gian giữ chỗ (BR-BH-03). Đơn đã thanh toán chỉ huỷ qua P-07 trong ERP. *(mới, (D) 2026-10-10, xem decisions.md)* |
| BR-BH-29 | **(D) 2026-10-10** — **Địa chỉ giao** là một ô chữ (BR-BH-09). Khách có thể mở Google Maps để tìm hoặc ghim; chỉ chuỗi địa chỉ cuối cùng được gửi về Cá Về. **Không lưu toạ độ.** Script bản đồ chỉ nạp khi khách bấm "Bản đồ". Popup bản đồ hiện thông báo gửi dữ liệu tới Google **ngay khi mở**, trước khi bản đồ tải xong. V1 không có nút lấy vị trí hiện tại của thiết bị. *(mới, (D) 2026-10-10, xem decisions.md)* |
| BR-BH-30 | **(D) 2026-10-10** — **Công bố giá cuối cùng**: dưới dòng Tổng ở giỏ, đặt hàng và thanh toán có câu "Đã gồm giao hàng. Bạn trả một lần, không trả thêm khi nhận hàng." Shop không có dòng "Phí giao", không hứa "miễn phí giao". Khi sau này có phí giao, phí cộng vào tổng tiền QR và phải có quyết định riêng (BR-BH-10 giữ). Khu vực giao được công bố và cách xử lý địa chỉ ngoài khu vực: Phan Thiết (D 11/10); ranh giới và đơn ngoài vùng tạm theo `doc/ops/hoi-loc.md` L1–L2. *(mới, (D) 2026-10-10, xem decisions.md)* |

## 7.4 Thanh toán
| Mã | Luật |
|---|---|
| BR-TT-01 | Mã VietQR động sinh riêng cho từng đơn, nội dung chuyển khoản mang mã đơn. |
| BR-TT-02 | Webhook đi qua FastAPI adapter → gọi API nội bộ Django. Bên thứ 3 không nối thẳng lõi (D). |
| BR-TT-03 | Webhook phải **idempotent** — SePay có thể gửi lại. Khoá chống trùng: mã giao dịch ngân hàng. |
| BR-TT-04 | **Tiền về ít hơn số đơn** → không tự xác nhận, đẩy vào hàng chờ Chủ xử lý tay. |
| BR-TT-05 | **Tiền về sau khi đơn đã tự huỷ** → không tự khôi phục đơn (hàng có thể đã bán cho người khác). Đẩy vào hàng chờ Chủ → thường dẫn tới hoàn tiền (P-07). |
| BR-TT-06 | Ghi nhận doanh thu tại thời điểm **xác nhận thanh toán** (tiền đã về tài khoản thật), không phải lúc giao xong *(PA)*. |
| BR-TT-07 | Xác nhận thanh toán thủ công (`confirm_payment_manual`) **chỉ Chủ** — thao tác này đòi đối chiếu sao kê, mà sao kê chỉ Lộc truy cập được. Uỷ quyền chỗ này là mở đường ghi doanh thu khống. |
| BR-TT-18 | **Tiền về muộn mà webhook/IPN không báo** (E-05; đơn đã huỷ/tự huỷ hoặc chưa rõ đơn): Chủ (hoặc người có `confirm_payment_manual`) **ghi tay** khoản tiền ở Hàng chờ thanh toán. Hệ thống tạo giao dịch `MANUAL` đang Chờ xử lý: `ORPHAN` nếu gắn đơn Đã huỷ/Tự huỷ, `UNMATCHED` nếu không gắn đơn. **Không đổi đơn, kho, hoá đơn**; bước sau đi qua hàng chờ (gắn đơn / phiếu hoàn, P-07). Không ghi gắn đơn đang giữ chỗ (dùng xác nhận trên đơn, BR-TT-07) hoặc đã thanh toán (để trống mã đơn rồi hoàn); mã đơn sai thì báo lỗi, không tự đổi thành `UNMATCHED`. Chỉ nhập mã GD, số tiền, giờ nhận (có cả ngày và giờ, không ở tương lai, không cũ quá `LATE_PAYMENT_MAX_AGE_DAYS`), mã đơn; **không có ô ghi chú**. Mã GD chống trùng (BR-TT-03). Khoản cùng số tiền trong cửa sổ `LATE_PAYMENT_DUPLICATE_WINDOW_HOURS` bị coi là nghi trùng, xét **hai chiều**: ghi tay sau khoản đã có thì phải xác nhận mới ghi, khoản webhook/IPN về sau khoản ghi tay thì bị gắn nhãn. Phiếu hoàn trên giao dịch có nhãn nghi trùng phải xác nhận "đã đối chiếu sao kê" (áp cả nhãn BR-TT-15). Job tự khớp bỏ qua khoản ghi tay *(D, 03/10; ghi vào spec 08/10)*. |
| BR-TT-19 | **(D) 2026-10-10** — Sau khi khách quay về từ cổng với kết quả thành công mà chưa có xác nhận tiền, Shop tự kiểm lại định kỳ. Quá **5 phút** (tham số cấu hình) thì đổi sang câu "Cá Về sẽ kiểm tra giao dịch và gọi cho bạn" kèm hotline; đơn vẫn giữ chỗ tới hết thời hạn, không đổi trạng thái. *(mới, (D) 2026-10-10, xem decisions.md)* |

## 7.5 Nội dung công khai của Shop (BR-ND)
Bảng BR-ND đầy đủ nằm ở hồ sơ `doc/features/2026-09-28-cms-viet-bai/` và `doc/features/2026-09-28-khung-go-live/`. Mục này chỉ ghi các rule BR-ND bị sửa hoặc thêm từ đợt Shop làm lại (hồ sơ `doc/features/2026-10-06-shop-giao-dien-moi/`).

| Mã | Luật |
|---|---|
| BR-ND-18 | Thông tin người bán công khai (tên, loại hình, số GCN ĐKDN/MST, địa chỉ, SĐT, email) lấy từ cấu hình môi trường, trả qua một API công khai chỉ gồm các field đó. Không viết cứng trong mã nguồn, không commit giá trị thật vào repo. **Bổ sung vào cùng nguồn cấu hình và cùng API công khai: số Zalo, giờ làm việc, nơi cấp và ngày cấp GCN ĐKKD, số giờ khách được báo vấn đề sau khi nhận hàng, link và ảnh biểu tượng xác nhận đã thông báo website TMĐT. Trường nào trống thì Shop ẩn khối tương ứng, không hiện chữ "Đang chờ".** *(D 28/09; sửa, (D) 2026-10-10, xem decisions.md)* |
| BR-ND-20 | **(D) 2026-10-10** — Ba trang **Chính sách giao hàng**, **Chính sách thanh toán**, **Cơ chế giải quyết khiếu nại** là trang bắt buộc trước khi bán thật, có vai trò riêng như các trang `privacy`, `terms`, `refund`, `seller_info`: không gỡ được khi đang là bản hiệu lực, có lịch sử phiên bản, hiện ở footer. *(mới, (D) 2026-10-10, xem decisions.md)* |
| BR-ND-21 | **(D) 2026-10-10** — Chữ nội dung của Shop (trang chính sách, liên hệ, cách mua, giới thiệu, bài Góc bếp, các khối nội dung Lộc cần sửa) **lưu ở CMS**, Shop đọc qua API công khai. Chữ giao diện (nhãn nút, câu lỗi, tiêu đề màn, câu pháp lý cố định ở form) ở code. Trang chính sách chỉ đăng sau khi `legal-vn` duyệt (áp cho production; staging nạp và đăng luôn toàn bộ theo decisions 2026-10-10 tối). Câu khẳng định về hàng hoá hay dịch vụ chưa có nguồn (decisions, BR, hoặc Lộc xác nhận) không được đăng. *(mới, (D) 2026-10-10, xem decisions.md)* |

---

# 8. P-06 — Soạn hàng & giao hàng

```mermaid
stateDiagram-v2
    [*] --> SoanHang: đơn đã thanh toán
    SoanHang --> ChoLay: đóng gói xong
    ChoLay --> DangGiao: nhân viên nhận hàng đi
    DangGiao --> HoanTat: khách nhận
    DangGiao --> GiaoThatBai: không gặp khách / khách từ chối
    SoanHang --> HuyDon: phát hiện hàng hỏng/thiếu (P-07)
    GiaoThatBai --> DangGiao: hẹn giao lại
    GiaoThatBai --> HangVeKho: thôi không giao nữa (P-08)
    HoanTat --> [*]
```

| Mã | Luật |
|---|---|
| BR-GH-01 | Người giao là **nhân viên nội bộ**, FK trỏ `User` (D). `StaffProfile` cung cấp số điện thoại để khách/Lộc liên hệ. |
| BR-GH-02 | Không có định tuyến, tối ưu lộ trình, chi phí xe cộ (L). |
| BR-GH-03 | Số kg cân khi soạn = số kg khách đặt. **Giả định V1 (PA), chưa kiểm chứng** — không có field "số kg thực xuất". |
| BR-GH-04 | "Giao thất bại" là **trạng thái tạm**, đếm số lần thử. Sau 2 lần thất bại hệ thống nhắc Quản lý/Chủ quyết định *(PA — ngưỡng cấu hình được)*. |
| BR-GH-05 | Chuyển sang **Hoàn tất** là điểm không quay lui. Muốn xử lý sau đó phải qua phiếu hoàn tiền. |
| BR-GH-06 | `delivery_staff` chỉ thấy và chỉ sửa được **trạng thái** của phiếu được gán cho mình — không sửa dòng hàng, không xem giá vốn (1.6). |
| BR-GH-24 | **(PA)** — Một phiếu giao chỉ có **một kết cục**. Hoàn tất, Giao thất bại và Huỷ phải xét trạng thái **mới nhất** lúc ghi; thao tác đến sau bị từ chối, **không ghi đè**. Phiếu đã huỷ, hoặc phiếu của đơn đã huỷ, thì bắt đầu giao, giao xong hay báo thất bại đều bị từ chối (400, "Đơn đã huỷ — mang hàng về kho."). *(W37, 2026-10-08: ghi phần "không ghi đè" mà BR-BH-18 cần. Phần huỷ đơn khi phiếu đang giao vẫn **CHỜ DUYỆT** ở hồ sơ riêng `doc/features/2026-10-01-huy-don-dang-giao/`, chưa thuộc spec.)* |

---

# 9. P-07 — Huỷ đơn & hoàn tiền

## 9.1 Ràng buộc phải biết trước
Đã kiểm chứng trực tiếp trang SePay và tài liệu developer của họ: mô hình VietQR là **tiền vào thẳng tài khoản ngân hàng của Lộc, không qua ví trung gian**, và SePay tự mô tả là nền tảng **giám sát/thông báo biến động số dư**. Tài liệu API chỉ có webhook, tra cứu giao dịch, virtual account, IPN — **không có API hoàn tiền hay chuyển tiền đi**.

Hệ quả: **hoàn tiền tự động qua cổng không khả dụng ở V1.** Hoàn tiền là một lệnh chuyển khoản Lộc bấm trên app ngân hàng. Hệ thống chịu trách nhiệm phần **sổ sách** — vốn mới là phần quan trọng.

## 9.2 Bốn tình huống huỷ
| Tình huống | Thời điểm | Kho | Tiền |
|---|---|---|---|
| Quá TTL không trả tiền | Trước thanh toán | Nhả giữ chỗ, tự động | Không có gì để hoàn |
| Khách đổi ý / Chủ huỷ | Sau thanh toán, trước soạn hàng | Hoàn kho **toàn bộ** về lô gốc | Phiếu hoàn **toàn phần** |
| Soạn hàng phát hiện hàng hỏng/thiếu | Đang soạn | Hoàn kho phần không giao được | Phiếu hoàn **toàn phần hoặc một phần** |
| Giao thất bại, thôi không giao | Sau khi đi giao | Qua P-08 (duyệt tái nhập) | Phiếu hoàn **toàn phần** |

## 9.3 Phiếu hoàn tiền (`Refund`)
```mermaid
stateDiagram-v2
    [*] --> ChoHoan: create_refund (Chủ hoặc Quản lý)
    ChoHoan --> DaHoan: confirm_refund (chỉ Chủ) + mã GD
    ChoHoan --> ThatBai: sai STK / khách không nhận
    ThatBai --> ChoHoan: thử lại
    DaHoan --> [*]
```

| Mã | Luật |
|---|---|
| BR-HT-01 | `Refund` là **entity riêng**, không phải một field trên đơn. Có `method` = `MANUAL_TRANSFER` (V1) hoặc `GATEWAY` (chỗ chừa sẵn, chưa hiện thực). |
| BR-HT-02 | Hỗ trợ hoàn **một phần** — thiếu 1 mặt hàng thì hoàn đúng phần thiếu, phần còn lại vẫn giao. |
| BR-HT-03 | Chuyển sang **Đã hoàn** bắt buộc nhập **mã giao dịch chuyển khoản**. Không cho xác nhận suông. |
| BR-HT-04 | Số tiền hoàn **không được vượt** số đã thu của đơn (trừ đi các lần hoàn trước). |
| BR-HT-05 | Hoàn kho xảy ra ở **thời điểm huỷ**, độc lập với việc tiền đã chuyển hay chưa — kho và tiền là hai sổ tách nhau. |
| BR-HT-06 | *(sửa 2026-09-30, Duy duyệt 30/09)* Huỷ đơn đã thanh toán → Hệ thống lập **chứng từ đảo doanh thu** (BR-HT-10) ngay lúc huỷ; doanh thu và giá vốn của đơn được đảo vào **kỳ phát sinh huỷ**, không sửa kỳ cũ. Phiếu hoàn chỉ ghi tiền rời tài khoản: phiếu hoàn của hoá đơn đã có chứng từ đảo **không** trừ doanh thu lần nữa; phiếu hoàn của hoá đơn chưa có chứng từ đảo (hoàn một phần, hoàn sau giao) vẫn trừ vào kỳ xác nhận hoàn. Phiếu hoàn đã xác nhận **trước** lúc huỷ vẫn trừ ở kỳ xác nhận của nó, và số đảo doanh thu ở kỳ huỷ = số tiền hoá đơn − tổng phiếu hoàn đã xác nhận trước lúc huỷ (không âm), nên kỳ cũ không bao giờ đổi số (Duy quyết 30/09, phương án B). *(Lý do: hoá đơn gốc giữ nguyên để giữ lịch sử; trước đây đơn huỷ vẫn tính doanh thu lô.)* |
| BR-HT-10 | *(mới, Duy duyệt 30/09)* Chứng từ đảo doanh thu là chứng từ riêng, append-only, do Hệ thống lập trong cùng giao dịch với huỷ đơn (kể cả job tự huỷ CSKH), gắn hoá đơn gốc; hoá đơn gốc giữ nguyên `ISSUED`. Mỗi dòng = lô + kg + đơn giá bán lấy từ phân bổ lô của hoá đơn (BR-BH-06). Mỗi hoá đơn tối đa một chứng từ huỷ. Chứng từ lập bù cho đơn huỷ trước P8 ghi vào kỳ chạy lập bù; lãi lỗ lô đã chốt không đổi (Duy quyết 30/09). |
| BR-HT-07 | **Tách quyền**: `create_refund` mở cho Quản lý (khách chờ không được), `confirm_refund` chỉ Chủ (tiền thật rời tài khoản). |
| BR-HT-08 | Mọi chuyển trạng thái Refund ghi AuditLog (BR-PQ-05). |
| BR-HT-12 | **(D) 2026-10-10** — **Thông báo đơn huỷ trên Shop** (đơn đã trả tiền, huỷ toàn phần hoặc một phần, hoặc tiền về sau khi đơn tự huỷ): chỉ gồm nhãn lý do cố định, **số tiền của phần bị huỷ**, câu "Cá Về sẽ gọi vào số điện thoại đặt hàng trong [thời hạn] để [trả lại / xử lý] số tiền …" (bản A hoặc B và thời hạn: bản A, tạm gọi trong 1 ngày làm việc, trả tiền trong 3 ngày làm việc (D 11/10: câu tạm, hỏi Lộc L6–L7 ở `doc/ops/hoi-loc.md`)), hotline, link mục "Xử lý tiền đã chuyển khi đơn huỷ" của Chính sách đổi trả và hoàn tiền. **Không** hiện trạng thái, hạn, ngày chuyển của phiếu hoàn. Chữ "hoàn tiền" chỉ có trong tên trang chính sách. ERP giữ nguyên Refund. Thay nội dung CS-10 `cancel_notice` đã nghiệm thu (hồ sơ `2026-09-28-cskh-xac-nhan-in-tem`): không trả tiến độ phiếu hoàn (`refund{amount,status_label,deadline,refunded_at}`) ra API công khai, bỏ câu "sẽ được hoàn trong vòng N ngày". *(mới, (D) 2026-10-10, xem decisions.md; BR-HT-11 đã giữ cho hồ sơ huỷ đơn đang giao)* |

---

# 10. P-08 — Hàng giao thất bại quay về kho *(PA)*

Hàng đông lạnh đã ra khỏi chuỗi lạnh vài giờ **không đương nhiên bán lại được**. Nhập lại vô điều kiện là cách nhanh nhất để bán hàng hỏng cho khách tiếp theo.

`NV giao mang hàng về → ghi nhận Hàng hoàn (lô gốc, số kg, giờ rời kho, giờ về kho) → Quản lý hoặc Chủ duyệt`

| Quyết định | Kho | Sổ giá vốn |
|---|---|---|
| **Tái nhập** | Cộng lại đúng **lô gốc**, gắn cờ `hàng hoàn` | Không đổi |
| **Huỷ bỏ** | Không cộng lại | Hạch toán **lỗ hàng hỏng** vào lô gốc |

| Mã | Luật |
|---|---|
| BR-HV-01 | Hàng hoàn **luôn** về đúng lô gốc, không tạo lô mới — nếu không, giá vốn lô sai và mất dấu vết. |
| BR-HV-02 | Hàng hoàn **bắt buộc** qua `approve_returntostock`. Nhân viên tạo phiếu nhưng không tự nhập lại kho. |
| BR-HV-03 | Vượt ngưỡng thời gian ngoài chuỗi lạnh → hệ thống **mặc định đề xuất Huỷ bỏ** (người duyệt vẫn có quyền lật). Ngưỡng cấu hình được — **câu hỏi mở #3, cần Lộc cho con số thực tế**. |
| BR-HV-04 | Lô **đã chốt** không nhận hàng hoàn — phải hạch toán lỗ, không mở lại lô. |

---

# 11. P-09 — Kiểm kê & hao hụt

Hàng đông lạnh mất trọng lượng theo thời gian (rút nước, bay hơi đá). Nhập 100kg, tháng sau cân còn 97kg là bình thường, không phải mất trộm. `Stock Reconciliation` **phát hiện** được — nhưng cần nghiệp vụ xử lý con số chênh lệch đó.

`NV kho đếm & nhập số thực tế theo từng lô → hệ thống tính chênh lệch → Quản lý/Chủ duyệt → chênh lệch hạch toán vào lô`

| Mã | Luật |
|---|---|
| BR-KK-01 | Kiểm kê **theo lô**, không theo mặt hàng — gộp mặt hàng thì mất khả năng quy trách nhiệm giá vốn. |
| BR-KK-02 | Người nhập số và người duyệt (`approve_stockreconciliation`) **phải là hai người khác nhau**. Chưa duyệt thì tồn sổ chưa đổi. |
| BR-KK-03 | Chênh lệch **âm** → hạch toán chi phí hao hụt vào lô đó, làm giảm lãi của chính lô đó. |
| BR-KK-04 | Chênh lệch **dương** phải ghi chú lý do — thường là dấu hiệu sai sót ghi chép trước đó, không phải hàng tự sinh ra. |
| BR-KK-05 | Tần suất đề xuất *(PA)*: **hàng tuần**, và **bắt buộc trước khi chốt lô**. |
| BR-KK-06 | Kiểm kê là **tín hiệu cảnh báo sớm** cho giả định BR-GH-03 (cân đúng số đặt). Hao hụt tăng bất thường ⇒ giả định đó có thể sai ⇒ mở lại quyết định "số kg thực xuất". |

---

# 12. P-10 — Báo cáo giá vốn & lãi lỗ *(PA)*

## 12.1 Hai góc nhìn
| Báo cáo | Đơn vị | Nội dung | Tính chất |
|---|---|---|---|
| **Lãi lỗ theo lô** | 1 lô | Doanh thu bán từ lô (phân bổ lô của hoá đơn chưa huỷ, **trừ** dòng chứng từ đảo doanh thu của lô — BR-HT-10) − (giá mua + chi phí phân bổ). Hao hụt và hàng hỏng hiện riêng (kg + giá trị), không cộng thêm — xem BR-BC-04 *(sửa 2026-09-28, Duy duyệt)* | **Nguồn sự thật**. Chốt lô là chốt số. |
| **Lãi lỗ theo kỳ** | Tháng | Tổng doanh thu ghi nhận − tổng giá vốn ghi nhận − hoàn tiền trong kỳ | Điều hành. Có thể lệch nhẹ với tổng theo lô khi lô chưa chốt. |

Cả hai báo cáo nằm sau `view_profitreport` — mặc định chỉ Chủ (1.7).

## 12.2 Business rules
| Mã | Luật |
|---|---|
| BR-BC-01 | Doanh thu ghi nhận tại thời điểm **xác nhận thanh toán**. |
| BR-BC-02 | Giá vốn ghi nhận **cùng thời điểm** với doanh thu, lấy từ bảng phân bổ lô (BR-BH-06). |
| BR-BC-03 | Hoàn tiền ghi vào **kỳ phát sinh hoàn**, không sửa ngược kỳ đã qua. Chứng từ đảo doanh thu ghi vào kỳ lập chứng từ (BR-HT-06). |
| BR-BC-04 | Lãi/lỗ theo lô = doanh thu bán từ lô − (giá mua + chi phí phân bổ − tiền NCC hoàn). Tổng chi phí lô = giá mua + chi phí phân bổ − tiền NCC hoàn (BR-MH-08); kg trả NCC hiện riêng, không lẫn hao hụt/huỷ *(bổ sung 2026-09-30, Duy duyệt 30/09)*. Doanh thu (và số kg đã bán) = phân bổ lô của hoá đơn **chưa huỷ** **trừ** dòng chứng từ đảo doanh thu của lô *(sửa 2026-09-30, Duy duyệt 30/09)*; lô đã chốt: chỉ trừ chứng từ lập trước thời điểm chốt *(Duy quyết 30/09)*; kg hoàn về kho rồi bán lại chỉ tính một lần *(hoá đơn đã huỷ vẫn không tính — sửa 2026-09-28, Duy duyệt)*. Giá mua = `purchase_rate` × số kg nhập. Hao hụt (kiểm kê âm) và hàng hỏng (hàng hoàn đã duyệt Huỷ bỏ) **hiển thị riêng** số kg và giá trị (kg × `landed_unit_cost` **hiện hành**, không dùng số ảnh chụp trên đơn) để biết mất bao nhiêu, **không cộng vào tổng chi phí** vì số kg đó đã nằm trong giá mua; phần mất làm giảm lãi qua việc không có doanh thu (BR-KK-03). Ví dụ: nhập 100 kg × 100.000đ, bán 90 kg × 150.000đ, hao 10 kg → lãi 3.500.000đ. *(D — sửa 2026-09-28, Duy duyệt, lý do: công thức cũ "giá mua + chi phí phân bổ + hao hụt + hàng hỏng" tính hai lần hao hụt/hỏng.)* |
| BR-BC-05 | Lô chưa chốt phải hiển thị nhãn **"tạm tính"** — nếu không, Lộc sẽ đọc số chưa đủ chi phí như số cuối cùng. |
| BR-BC-06 | **(D) 2026-10-07** — Trạng thái đơn **không** là nguồn của số tiền. Doanh thu, giá vốn, hoàn tiền tính theo hoá đơn, chứng từ đảo, phiếu hoàn và thời điểm của chúng (BR-BC-01..03). Đổi trạng thái đơn, kể cả chuyển bù, không làm đổi số kỳ nào. *(theo BR-BC-01..03 và quyết định "không sửa kỳ cũ". W37, Duy duyệt 07/10)* |

---

# 13. Bảng ngoại lệ tổng hợp

| # | Tình huống | Xử lý | Quy trình |
|---|---|---|---|
| E-01 | Quá 30' không trả tiền | Tự huỷ, nhả giữ chỗ | P-05 |
| E-02 | Tiền về thiếu | Không tự xác nhận, hàng chờ Chủ | BR-TT-04 |
| E-03 | Tiền về sau khi đơn đã huỷ | Hàng chờ Chủ → thường dẫn tới hoàn tiền | BR-TT-05 |
| E-04 | Webhook gửi trùng | Chống trùng bằng mã giao dịch ngân hàng | BR-TT-03 |
| E-05 | Webhook không tới (SePay lỗi) | Đơn còn giữ chỗ: màn hình xác nhận thanh toán thủ công, **chỉ Chủ**. Đơn đã huỷ/tự huỷ hoặc chưa rõ đơn: Chủ ghi tay tiền về muộn ở Hàng chờ thanh toán | BR-TT-07, BR-TT-18 |
| E-06 | Hai khách tranh lô cuối | Người tạo đơn trước thắng | BR-BH-02 |
| E-07 | Soạn hàng phát hiện hàng hỏng | Huỷ toàn/một phần + phiếu hoàn | P-07 |
| E-08 | Giao 2 lần không gặp khách | Hệ thống nhắc Quản lý/Chủ quyết định | BR-GH-04 |
| E-09 | Hàng giao thất bại về kho | Quản lý/Chủ duyệt tái nhập hoặc huỷ bỏ | P-08 |
| E-10 | Lô quá hạn còn tồn | Loại khỏi bán ngay, cảnh báo, Chủ xác nhận Đã huỷ (ghi lỗ) hoặc Đã trả NCC | BR-LO-02/03/07, BR-MH-08 |
| E-11 | Hao hụt kiểm kê bất thường | Duyệt, hạch toán vào lô, xem lại giả định cân | BR-KK-03/06 |
| E-12 | Job nhả giữ chỗ chết | Cần cảnh báo giám sát — hàng bị khoá vô hình | BR-BH-04 |
| E-13 | Thành phần BUNDLE hết hàng | Combo tự động hết hàng trên Shop | BR-DM-06 |
| E-14 | Chi phí mua về sau khi lô đã bán hết | Nhập trước khi chốt lô, báo cáo lô tính lại | BR-GV-02 |
| E-15 | **Lộc đi cảng, kho phát sinh việc cần duyệt** | Quản lý duyệt vận hành; việc đụng tiền vẫn nằm chờ Chủ | 1.5 |
| E-16 | **Nhân viên nghỉ việc giữa chừng** | `is_active=False`, chứng từ cũ giữ nguyên tên, FK `PROTECT` | BR-PQ-01/02 |
| E-17 | **Một người kiêm hai việc** | Gán nhiều Group, quyền là hợp — không tạo role mới | BR-PQ-09 |

---

# 14. Ảnh hưởng lên data model (đầu vào cho Level 4)

Thực thể **mới** so với `doctype-mapping.md`:

| Thực thể | Vì sao |
|---|---|
| `BundleLine` | Combo dạng gói có công thức |
| `PricingRule` | Combo dạng ưu đãi |
| `PurchaseCost` | Landed cost |
| `SalesInvoiceLineBatch` | Một dòng đơn ăn nhiều lô — nền của mọi báo cáo giá vốn |
| `Refund` | Huỷ & hoàn tiền |
| `ReturnToStock` | Hàng giao thất bại quay về |
| **`StaffProfile`** | `OneToOne` với `User` — SĐT, ngày vào làm, trạng thái |
| **`AuditLog`** | Ghi vết mọi hành động Tầng 2; Django `LogEntry` không phủ được API |

Trường **mới** đáng chú ý: `Item.item_type`, `Batch.status`, `Batch.landed_unit_cost`, `Batch.closed_at`, `DeliveryNote.assigned_to` (FK `User`, `PROTECT`), `DeliveryNote.failed_attempts`, `Customer.phone` (khoá tự nhiên).

**Custom permissions cần khai trong `Meta.permissions`**: `publish_batch`, `close_batch`, `approve_stockreconciliation`, `approve_returntostock`, `cancel_paid_order`, `create_refund`, `confirm_refund`, `confirm_payment_manual`, `view_costprice`, `view_profitreport`, `manage_staff`.

**Fixture khởi tạo**: 4 Group (`owner`, `manager`, `warehouse_staff`, `delivery_staff`) với permission gán sẵn theo mục 1.4 và 1.5 — phải là data migration, không phải bấm tay trong Admin, nếu không thì môi trường dev/staging/prod lệch nhau.

---

# 15. Câu hỏi mở còn lại

**Cần Lộc trả lời (nghiệp vụ, không đoán được):**
1. Combo thực tế Lộc định bán ở dạng nào trong 3 dạng mục 3.1? Có thể nhiều dạng cùng lúc.
2. Mua tại cảng có gối đầu với đầu mối quen không, hay trả ngay 100%? *(Gối đầu ⇒ phải mở lại công nợ nhà cung cấp, hiện đang outscope.)*
3. Hàng ra khỏi chuỗi lạnh bao lâu thì không bán lại được? Con số này quyết định BR-HV-03.
4. Vựa sẽ có bao nhiêu người, và có ai được Lộc tin để uỷ quyền duyệt khi vắng mặt không? *(Nếu chỉ 2 người thì Group `manager` để đó không dùng — vẫn nên định nghĩa sẵn, không tốn gì.)*
5. Xác nhận lại mục tiêu nghiệp vụ ở `URD.md` mục 2.2 — phần PA suy luận, chưa ai phát biểu.

**Duy tự xử lý:**
6. Xác nhận điều kiện/phí SePay trực tiếp với nhà cung cấp trước khi ký; hỏi luôn về đường thẻ quốc tế nếu sau này muốn hoàn tiền tự động.
7. Cơ chế xác thực nội bộ FastAPI ↔ Django (service token) — chi tiết lúc build.

**Chỉ kiểm chứng được khi vận hành thật:**
8. Số kg cân khi soạn có luôn khớp số kg khách đặt không (BR-GH-03). Theo dõi qua hao hụt kiểm kê.

**Nợ kỹ thuật tài liệu:**
9. `doctype-mapping.md` đã lỗi thời (còn ghi "bỏ Sales Order", "bỏ Delivery Note") và chưa có 8 thực thể mới ở mục 14. **Phải viết lại trước khi dịch sang Django models.**

---
*Tài liệu liên quan: `URD.md` (Level 0 — yêu cầu), `ecosystem-l1.md` (Level 1 — hệ sinh thái), `doctype-mapping.md` (Level 2 — ⚠ lỗi thời), `decisions.md` (nhật ký quyết định).*

**Nhật ký thay đổi**
- 08/10/2026 — W37 S9 (Duy duyệt 07/10): thay sơ đồ §7.2 (bỏ `DaThanhToan`, Hoàn tất do Hệ thống chuyển khi phiếu cuối giao xong); thêm BR-BH-18..21 (§7.2), BR-BC-06 (§12.2), BR-GH-24 phần "không ghi đè" (§8). Hồ sơ: `doc/features/2026-10-06-don-hoan-tat/`.
- 11/10/2026 — Shop làm lại theo thiết kế 06/10 (Duy chốt 10/10 tối, điểm dừng 1 nhóm A): sửa BR-DM-01, BR-DM-08, ranh giới §3.1 (có mã giảm giá một tầng), §7.1 (tra đơn), BR-BH-01; thêm BR-DM-17..25 (§3.2), BR-BH-22..30 (§7.3), BR-TT-19 (§7.4), BR-HT-12 (§9.3, thay nội dung CS-10 `cancel_notice`); thêm §7.5 với BR-ND-18 (sửa), BR-ND-20, 21. Chỗ còn S-08 / S-12 / S-18 (Duy trả lời 11/10, câu tạm theo `doc/ops/hoi-loc.md`) là câu nhóm B chưa chốt. Hồ sơ: `doc/features/2026-10-06-shop-giao-dien-moi/`.

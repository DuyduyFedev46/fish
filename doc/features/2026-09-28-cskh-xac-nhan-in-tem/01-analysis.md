# CSKH gọi xác nhận đơn → tự in tem → kho soạn hàng — Phân tích nghiệp vụ
> BA · 2026-09-28 · Trạng thái: **ĐÃ DUYỆT** (Duy 28/09 — chốt scope qua câu hỏi; câu trả lời ở mục ngay dưới)

## Câu trả lời của Duy (2026-09-28)
*PO ghi lại theo lời Duy do điều phối viên chuyển. Chỗ nào lật mặc định BA thì ghi rõ "LẬT". Mục nào có hiệu lực hơn
nội dung phía dưới của bản phân tích thì mục này thắng.*

| # | Nguyên văn / nội dung chốt | Hệ quả áp vào bản phân tích |
|---|---|---|
| Q-C1 | Gọi xác nhận **SAU** khi trả tiền, **TRƯỚC** soạn hàng → thêm trạng thái **"Chờ xác nhận"** trước "Soạn hàng" (sửa chuỗi trạng thái phiếu giao của quyết định 10/09). BR-GH-09 đổi thành **in tem sau xác nhận**. | Chọn (a). BR-GH-11 có hiệu lực. BR-GH-09 (sửa) có hiệu lực. **Việc của Duy:** ghi quyết định mới vào `decisions.md` (chuỗi phiếu giao: Chờ xác nhận → Soạn hàng → Chờ lấy → Đang giao → Hoàn tất). |
| Q-C2 | Nguyên văn: **"cho tới quản lý, ko giải quyết trong 30' sẽ tự hủy, nhắc nhỏ cho nhân viên gọi hoàn tiền"** + **"3 lần, trong vòng 30'"**. | **LẬT** mặc định BA (60 phút / 24 giờ / "không bao giờ tự huỷ"). Luật mới thay BR-GH-13 và UC-CS-5 E2: CSKH gọi **tối đa 3 lần trong 30 phút**; không liên lạc được → chuyển **Quản lý** ("Cần quyết định"); Quản lý **không xử lý trong 30 phút** → **Hệ thống tự huỷ** đơn đã thanh toán, **hoàn kho**, ghi **AuditLog actor = Hệ thống**, lập phiếu hoàn và **tạo nhắc việc** cho nhân viên gọi khách về việc hoàn tiền. Xác nhận đã chuyển tiền vẫn **chỉ Chủ** (`confirm_refund`, BR-HT-03). Không huỷ nếu đơn đã sang Soạn hàng. Mọi mốc (3 lần, 30', 30') là **tham số**. Đây là quyết định tự động bất lợi cho khách → phải **thông báo cho khách lý do huỷ và cách nhận hoàn tiền** (NĐ 356/2025; `legal-vn` kiểm nội dung câu chữ). |
| Q-C3 | **Không sửa đơn cũ**: thêm = đơn mới; bớt/đổi = huỷ + hoàn + đặt lại. | Chọn (a). BR-GH-14 có hiệu lực. |
| Q-C4 | **Chưa có máy in.** V1 **in tay từ trình duyệt** (trang in khổ **100×150 mm**). In tự động **để sau**. | Đoạn C6 (lệnh in, trạm in, thiết bị kho) **không làm đợt này**. UC-CS-3 chạy theo luồng thay thế 3c. BR-GH-09 (sửa) ở V1 hiểu là: tem **chỉ in được sau khi xác nhận**, phiếu vừa xác nhận hiện "Chưa in tem" ở đầu danh sách soạn. |
| Q-C5 | Thêm **Group thứ năm `cskh`** (cộng dồn). CSKH chỉ xem **tên/SĐT/địa chỉ** của đơn đang **Chờ xác nhận / Cần quyết định** + đơn **mình đã gọi trong 7 ngày**. | Chọn (a), phạm vi PII như BR-GH-18 với X = 7 (tham số). **Vai trò tự định nghĩa không làm đợt này** (hồ sơ `2026-09-28-vai-tro-tu-dinh-nghia` sau này gom `cskh` vào). Thêm Group là đổi quyết định 10/09 "bốn Group" → **Duy ghi `decisions.md`**. |
| Q-C6…Q-C18 (🟡) | **Theo đề xuất BA.** | Tem theo Q-C6 (chờ `legal-vn` về ghi nhãn); không ghi âm, gọi bằng máy/SIM của vựa (Q-C7); mọi đơn đều gọi (Q-C8); báo khách trước ở Shop (Q-C9); không đổi địa chỉ mặc định (Q-C10); **field người nhận hộ trên phiếu giao được duyệt** (Q-C11, field PII mới); nút "Đã huỷ tem" (Q-C12); theo "100% NV nội bộ" (Q-C13); Chủ soạn kịch bản (Q-C14); Q-C17 chuyển Tech Lead. Các 🟢 để sau. |
| Tiền đề | Nếu màn Giao hàng (S17–S19) chưa có thì đưa **story tối thiểu cần thiết** vào hồ sơ này, ghi rõ nguồn. | Đã kiểm 28/09: `deliveries/page.tsx` là Placeholder, BE chưa có gán người, `from_status`, dòng hàng trong chi tiết phiếu. PO đưa S17, S19 (bản thu gọn) vào `02-stories.md` là CS-02, CS-03. |

Ký hiệu câu hỏi: 🔴 chặn (không trả lời thì PO không viết story được) · 🟡 có mặc định PA, Duy lật được · 🟢 để sau.

## 1. Yêu cầu gốc
> "nhân viên sẽ tự gọi khách xác nhận địa chỉ trước để tư vấn rồi bắt đầu lấy tem tự động in và vào kho lấy hàng"

Nguồn: Duy (PO), 2026-09-28, trong phiên hồ sơ `2026-09-28-ai-digital-worker` (dòng M-scope ở `01-analysis.md`:
"CSKH là nhân viên nội bộ … tách 2 hồ sơ mới"). Nhãn **(D)**. Bối cảnh Duy đã nói rõ: CSKH do **người** làm, khách
**không** chat với AI.

## 2. Tóm tắt
**Nhân viên CSKH** cần **gọi điện cho khách của mỗi đơn đã thanh toán để xác nhận địa chỉ và tư vấn, rồi bấm "Đã xác
nhận"** để **hệ thống tự in tem, kho chỉ soạn những đơn chắc chắn giao được**. Giá trị là giảm giao thất bại. Mỗi lần
giao thất bại với hàng đông lạnh có thể thành lỗ hàng hỏng (BR-HV-03) cộng một lần hoàn tiền tay (P-07).

Luồng Duy mô tả, đặt vào hệ thống:

```
Khách đặt + trả 100% VietQR ─► [MỚI] Chờ CSKH xác nhận ─► [MỚI] Tự in tem ─► Soạn hàng ─► Chờ lấy ─► Đang giao ─► Hoàn tất
        (P-05, có sẵn)            gọi, ghi kết quả           (sửa BR-GH-09)     (P-06, có sẵn)
```

## 3. Bối cảnh trong hệ thống

### 3.1 Quy trình, rule, quyết định liên quan
| Nội dung | Quy trình | Rule | Quyết định ràng buộc |
|---|---|---|---|
| Bước xác nhận nằm giữa thanh toán và soạn | P-05 → P-06 | BR-TT-06, BR-TT-11 (đề xuất 26/09), BR-GH-03 | decisions 2026-09-09 "Delivery Note (soạn hàng → chờ lấy → đang giao → hoàn tất)"; 2026-09-10 "Soạn hàng: thêm bước trong Delivery Note" |
| Giữ chỗ, thời hạn | P-05 | BR-BH-02/03/04/11 | 2026-09-09 SO booked **TTL 30'**; 2026-09-26 FEFO chốt lô lúc tạo đơn |
| Người giao | P-06 | BR-GH-01/02/06 | 2026-09-09 **100% NV nội bộ giao** |
| Huỷ, hoàn tiền | P-07 | BR-HT-02/04/05/06/07 | 2026-09-10 Refund thủ công, `create_refund` Quản lý, `confirm_refund` Chủ |
| In phiếu/tem tự động | P-06 | **BR-GH-09, BR-GH-10** (đề xuất trong `2026-09-26-hop-duy-loc`, CHỜ DUYỆT, **chưa có story, chưa có code**) | — |
| Phân quyền | §1 | BR-PQ-* | 2026-09-10 **4 Group cộng dồn** `chu quan_ly nv_kho nv_giao`; ranh giới Chủ ↔ Quản lý |
| Dữ liệu cá nhân | toàn hệ thống | bất biến 9 (skill `caveve-domain`) | `doc/ops/go-live-phap-ly.md` |
| Hướng dẫn theo chứng từ | — | BR-AI-* | `2026-09-28-ai-digital-worker/01-analysis.md` §4.7 (khối Tiếp theo / Đã làm) |

### 3.2 Hiện trạng code (đã đọc 2026-09-28, không suy đoán)
- **Đơn** `SalesOrder` (`sales/models/orders.py`): BOOKED → PAID → PROCESSING → (COMPLETED, code thật không bao giờ gán);
  BOOKED → AUTO_CANCELLED; PAID/PROCESSING → CANCELLED. Có `delivery_address` (TextField), `phone` (SĐT nhận hàng),
  `customer` (FK). **Không có** trạng thái hay field nào cho "đã xác nhận với khách". **Không có** field ghi chú trên đơn.
- **Thời điểm "khách trả xong"** duy nhất là `issue_invoice` (`sales/payments/services.py`). Hàm này trừ kho thật, ghi
  doanh thu, và chuyển đơn sang PROCESSING. Signal `post_save(SalesInvoice)` (`delivery/signals.py`) **tự tạo
  `DeliveryNote` ở PREPARING ngay lúc đó**. Tức là hiện nay đơn vừa trả tiền là **lập tức nằm trong việc "cần soạn"**.
- **Phiếu giao** `DeliveryNote`: PREPARING → READY → DELIVERING → COMPLETED | FAILED; FAILED → DELIVERING; CANCELLED (theo
  đơn). Có `assigned_to`, `failed_attempts`, `note`. **Không có** trạng thái trước PREPARING.
- **Huỷ đơn đã trả** `cancel_paid_order`: được khi phiếu giao còn PREPARING/READY/FAILED. Hoàn kho **toàn bộ** về lô gốc
  khi hàng còn ở kho. Quyền `sales.cancel_paid_order` (Chủ, Quản lý).
- **Hoàn tiền một phần**: `create_invoice_refund(amount, is_partial)` có. Nhưng **không có service hoàn kho một phần
  theo dòng** (grep `restore` trong `sales/refunds/services.py`: 0 kết quả). Tức "khách bớt 1 món" hiện chỉ làm được
  phần tiền, **không** làm được phần kho. Đây là khoảng trống so với BR-HT-02.
- **Tra đơn Shop** (`ShopOrderLookupView`) khớp theo **`order.phone`** (4 số cuối). Nếu CSKH đổi `order.phone` thì khách
  **không tra được đơn của mình nữa**.
- **API ERP đang trả PII đầy đủ**: danh sách đơn trả `customer_name`, `customer_phone`; chi tiết đơn trả `customer.name/
  phone/address`. Phạm vi dòng: `nv_giao` chỉ thấy phiếu của mình; `FULL_SCOPE_GROUPS = {chu, quan_ly, nv_kho}` thấy hết.
  **Chưa có vai CSKH.**
- **Chưa có gì về in**: không mẫu in, không lệnh in, không "đã in" (grep `PrintJob|window.print|BR-GH-09`: chỉ thấy trong tài
  liệu). Màn Giao hàng ERP (`erp-console/app/(console)/deliveries/page.tsx`) là **Placeholder**. S17–S24 (điều phối, gán
  NV giao, soạn hàng, việc giao của tôi) **chưa làm**.
- **Hạ tầng**: FE ERP là static export trên Firebase, không có server FE. Backend trên Cloud Run, **không gọi được vào LAN
  kho**. Production không có Redis/Celery, job định kỳ chạy bằng Cloud Scheduler.
- **Hồ sơ `2026-09-28-vai-tro-tu-dinh-nghia` chưa tồn tại** (glob `doc/features/*vai-tro*`: 0 kết quả). Hồ sơ này phụ thuộc vào nó ở phần quyền (§4).

### 3.3 Chỗ lệch giữa tài liệu cần Duy biết
- Hồ sơ `2026-09-26-hop-duy-loc`, mục "Quyết định của Duy", Q1: *"Giao các tỉnh xa bằng cách thuê đơn vị vận chuyển"*.
  Quyết định này **chưa được ghi vào `decisions.md`**. Hiện `decisions.md` vẫn ghi "100% NV nội bộ", và khảo sát
  `doc/ops/khao-sat-ben-van-chuyen.md` chưa chốt bên nào. Bản phân tích này **theo `decisions.md`**, tức tem chỉ cho NV nội
  bộ. Tem cho bên vận chuyển ngoài có yêu cầu khác (mã vận đơn, mẫu tem của hãng, gửi PII cho bên thứ ba) và nằm ngoài
  phạm vi (§9, Q-C13).
- BR-GH-09 (hop-duy-loc) ghi "in **khi thanh toán xong**". Yêu cầu mới ghi "in **sau khi CSKH xác nhận**". Hai yêu cầu
  **mâu thuẫn trực tiếp** về thời điểm in. Bản này đề xuất **sửa BR-GH-09** (§6), cần Duy chốt (Q-C1).

## 4. Tác nhân & quyền

| Tác nhân | Group | Làm được gì trong phạm vi này | Quyền Tầng 2 cần (PO/BE đặt tên) |
|---|---|---|---|
| **NV CSKH** (mới) | chưa có. Xem Q-C5 | Xem hàng chờ gọi. Xem tên, SĐT, địa chỉ của đơn **đang chờ xác nhận** và đơn mình đã xử lý gần đây. Ghi kết quả cuộc gọi. Đổi địa chỉ hoặc người nhận trên đơn chưa soạn. Ghi yêu cầu huỷ của khách. **Không** huỷ đơn, **không** lập phiếu hoàn, **không** sửa dòng hàng hay giá, **không** xem giá vốn | quyền mới "xác nhận giao với khách" + quyền mới "đổi thông tin nhận hàng" |
| Hệ thống | `actor=None` | Đưa đơn vào hàng chờ khi thanh toán xong. Tạo lệnh in khi đơn được xác nhận. Chuyển đơn sang "cần quyết định" khi quá số lần gọi hoặc quá hạn | — |
| Thiết bị in ở kho | tài khoản kỹ thuật (hop-duy-loc §4) | Lấy lệnh in đang chờ, báo đã in hoặc lỗi. Không đọc được gì khác | quyền hẹp mới, **không** dùng tài khoản người thật |
| NV kho | `nv_kho` | Nhận tem, quét tem để mở phiếu soạn, soạn theo lô đã chốt, in lại tem | xem phiếu giao (đã có), in lại (BR-GH-10) |
| NV giao | `nv_giao` | Không đổi. Thấy phiếu của mình (S20) | — |
| Quản lý | `quan_ly` | Mọi việc của CSKH (kiêm nhiệm). Quyết định đơn "không liên lạc được". Huỷ đơn khi khách yêu cầu, lập phiếu hoàn | `cancel_paid_order`, `create_refund` (đã có) |
| Chủ | `chu` | Như Quản lý, cộng xác nhận đã chuyển hoàn (`confirm_refund`). Cấu hình tham số (số lần gọi, hạn chờ) | đã có |

**Vì sao CSKH không được huỷ đơn** (PA): theo ranh giới 2026-09-10, huỷ đơn đã trả là việc của Quản lý. Huỷ đơn kéo theo
hoàn kho và hoàn tiền. CSKH ghi "khách muốn huỷ", Quản lý bấm. Nếu vựa ít người thì một người kiêm hai Group (E-17).

## 5. Use case

### UC-CS-1 Đơn vào hàng chờ xác nhận
- **Tiền điều kiện**: đơn được xác nhận đủ tiền theo **bất kỳ** đường nào: IPN, Chủ xác nhận tay (S11), hàng chờ lệch (S12).
- **Luồng chính**:
  1. `issue_invoice` chạy như hiện nay: trừ kho đúng các lô đã chốt (BR-BH-11), ghi doanh thu (BR-TT-06), đơn sang PROCESSING, tạo phiếu giao.
  2. **[Mới]** Phiếu giao nằm ở bước **"Chờ xác nhận"** (tên PO đặt), **chưa** nằm trong danh sách cần soạn của kho, **chưa** in tem.
  3. Đơn hiện trong **hàng chờ CSKH**, xếp theo giờ thanh toán, cũ nhất lên đầu.
  4. Trên Shop, khách tra đơn thấy trạng thái "Đã thanh toán, chờ vựa gọi xác nhận" (chỉ trạng thái, không PII).
- **Luồng thay thế**: 2a. Nếu Duy chọn cho phép bỏ qua bước gọi với một số đơn (Q-C8), đơn đó đi thẳng sang UC-CS-3.
- **Ngoại lệ**:
  - E1. IPN gửi lại, hoặc Chủ xác nhận trùng: không phát sinh hoá đơn mới (BR-TT-03), nên **không có mục chờ thứ hai**.
  - E2. Đơn vào ngoài giờ làm (22h): nằm chờ tới ca sau. Khách đã trả tiền nên cần câu thông báo ở Shop (Q-C9).
- **Hậu điều kiện**: mọi đơn đã trả tiền đều có đúng một mục chờ xác nhận, hoặc đã được bỏ qua có ghi lý do.

### UC-CS-2 CSKH gọi khách và ghi kết quả
- **Tiền điều kiện**: CSKH đăng nhập. Đơn ở "Chờ xác nhận". CSKH có quyền xem PII của đơn này (Tầng 3).
- **Luồng chính**:
  1. CSKH mở hàng chờ, chọn đơn. Hệ thống **khoá mềm** đơn cho người này trong vài phút (PA) để hai người không gọi trùng một khách.
  2. Màn hiện: mã đơn, dòng hàng + kg, giờ thanh toán, **tên, SĐT (bấm để gọi), địa chỉ**, các lần gọi trước (kết quả, giờ, ai gọi), và kịch bản gọi soạn sẵn (§5 UC-CS-7).
  3. CSKH gọi, xác nhận địa chỉ, người nhận, khung giờ nhận hàng, và tư vấn (cách rã đông, bảo quản).
  4. CSKH chọn **kết quả** từ danh sách cố định, kèm ghi chú ngắn nếu cần:

     | Kết quả | Hệ thống làm gì |
     |---|---|
     | **Đã xác nhận** | Sang UC-CS-3 (tự in tem) |
     | **Đã xác nhận, đổi địa chỉ / người nhận** | CSKH sửa thông tin nhận hàng (UC-CS-4), rồi như "Đã xác nhận" |
     | **Không nghe máy / thuê bao / sai số** | Tăng số lần thử, hẹn giờ gọi lại (UC-CS-5) |
     | **Khách hẹn gọi lại lúc …** | Ghi giờ hẹn. Đơn ẩn khỏi đầu hàng chờ tới giờ đó |
     | **Khách muốn đổi món / đổi số kg** | Không sửa đơn. Đi theo Q-C3 (UC-CS-6) |
     | **Khách muốn huỷ** | Chuyển Quản lý huỷ + hoàn (UC-CS-6) |
  5. Hệ thống ghi **một bản ghi cuộc gọi** (ai, lúc nào, kết quả, ghi chú) và **AuditLog** "xác nhận giao / ghi kết quả gọi" **không chép PII vào `detail`** (bất biến 9, BR-PQ-04).
- **Luồng thay thế**:
  - 3a. Khách gọi ngược lại vựa (không phải vựa gọi): CSKH tìm đơn bằng mã đơn hoặc SĐT (tìm theo SĐT đã có ở S10), ghi kết quả như bước 4.
  - 4a. CSKH đã ghi "Đã xác nhận" nhưng phát hiện nhầm đơn: được **huỷ xác nhận** khi tem chưa in và phiếu còn "Chờ xác nhận/Soạn hàng chưa bắt đầu". Tem đã in thì huỷ tem (UC-CS-3 E3). Có AuditLog.
- **Ngoại lệ**:
  - E1. Hai CSKH cùng bấm kết quả cho một đơn: người thứ hai nhận thông báo "đơn vừa được <vai> xử lý", tải lại. Không ghi đè.
  - E2. Đơn bị huỷ (Quản lý huỷ, S14) trong lúc CSKH đang gọi: ghi kết quả bị từ chối vì đơn đã huỷ (BR-GH-07).
  - E3. Mạng rớt khi bấm: bấm lại **không** tạo bản ghi cuộc gọi thứ hai và **không** in tem hai lần (idempotent, giống S19-AC2).
- **Hậu điều kiện**: đơn có lịch sử gọi đầy đủ. Nếu đã xác nhận thì sang in tem.

### UC-CS-3 Hệ thống tự in tem sau khi xác nhận
- **Tiền điều kiện**: đơn vừa chuyển "Đã xác nhận". Kho có thiết bị in đã đăng ký (Q-C4).
- **Luồng chính**:
  1. Hệ thống tạo **đúng một** lệnh in cho phiếu giao, trạng thái "Chờ in" (BR-GH-09 sửa).
  2. Phiếu giao chuyển sang **Soạn hàng** (PREPARING), vào danh sách cần soạn của kho (S17/S19).
  3. Thiết bị ở kho lấy lệnh, in **tem giao** (và phiếu soạn nếu Q-C6 chọn in hai phần), báo "Đã in". Hệ thống ghi thời điểm in.
  4. NV kho cầm tem vào kho lấy hàng (UC-CS-8).
- **Luồng thay thế**:
  - 3a. Thiết bị tắt, mất mạng: lệnh nằm "Chờ in", in lần lượt theo **giờ xác nhận** khi thiết bị bật lại.
  - 3b. **In lại** (kẹt giấy, tem ướt, mất tem): NV kho, Quản lý hoặc Chủ bấm In lại. Tem in lại có dấu "IN LẠI lần n". Ghi AuditLog (BR-GH-10).
  - 3c. Chưa có thiết bị (giai đoạn đầu): NV kho bấm **In** trên màn phiếu, in qua hộp thoại in của trình duyệt. Đây là đường dự phòng luôn có (N5 cũ).
- **Ngoại lệ**:
  - E1. Xác nhận trùng (UC-CS-2 E3): không có lệnh in thứ hai.
  - E2. Thiết bị báo lỗi (hết giấy): lệnh chuyển "Lỗi in" kèm lý do, vào khối "Cần chú ý" (S24).
  - E3. **Đơn bị huỷ sau khi tem đã in**: phiếu chuyển CANCELLED (đã có). Tem giấy đang ở kho là **giấy có PII** và phải **huỷ vật lý** (BR-GH-17). Màn kho hiện "Tem của đơn … đã huỷ, xé bỏ". Người ở kho bấm "Đã huỷ tem" (PA, Q-C12).
  - E4. Lệnh "Chờ in" quá X phút trong giờ làm (PA 15'): cảnh báo "Cần chú ý", để tránh cảnh máy in chết mà không ai biết (so với BR-BH-04).
  - E5. Thiết bị lấy lệnh xong nhưng mất mạng trước khi báo "Đã in": lần sau có thể in trùng. Chấp nhận in trùng. Tem có số lần in để NV kho nhận ra bản trùng, và **bản trùng phải huỷ** như E3.
- **Hậu điều kiện**: mỗi phiếu giao có lịch sử in (lần đầu tự động, các lần in lại, huỷ tem), truy được ai làm và lúc nào.

### UC-CS-4 Đổi thông tin nhận hàng khi gọi
- **Tiền điều kiện**: phiếu giao còn "Chờ xác nhận" hoặc "Soạn hàng". Đổi khi hàng đã rời kho nằm ngoài phạm vi (NV giao tự liên hệ).
- **Luồng chính**:
  1. CSKH sửa **địa chỉ giao** và/hoặc **tên, SĐT người nhận** (khi người khác nhận hộ).
  2. Hệ thống kiểm địa chỉ mới **còn trong vùng giao** (BR-BH-12, khi tính năng vùng giao có). Ngoài vùng thì từ chối và gợi ý "khách huỷ + hoàn".
  3. Lưu. AuditLog ghi "đổi thông tin nhận hàng", ai, lúc nào, **không** ghi giá trị cũ hay mới (bất biến 9).
  4. Nếu tem đã in: tem cũ **vô hiệu**, hệ thống tự tạo lệnh in tem mới (dấu "IN LẠI – ĐỔI ĐỊA CHỈ"), tem cũ phải huỷ (BR-GH-17).
- **Luồng thay thế**: 1a. Khách muốn **lưu địa chỉ mới làm mặc định** cho lần sau: 🟡 Q-C10 (mặc định: **không** tự cập nhật `Customer.default_address`).
- **Ngoại lệ**:
  - E1. **SĐT dùng để tra đơn không đổi.** Tra đơn trên Shop khớp theo `order.phone`. Đổi SĐT người nhận **không** được làm khách mất khả năng tra đơn. Người nhận hộ là thông tin riêng của phiếu giao (PA, Q-C11).
  - E2. Phiếu đã READY/DELIVERING: từ chối, báo "hàng đã soạn/đang đi giao, liên hệ Quản lý".
- **Hậu điều kiện**: địa chỉ trên đơn/phiếu là bản mới nhất. Bản cũ **không giữ** (thu tối thiểu), chỉ còn dấu vết "đã đổi lúc … bởi …".

### UC-CS-5 Không liên lạc được
- **Tiền điều kiện**: kết quả gọi là "không nghe máy / thuê bao / sai số".
- **Luồng chính (PA, Q-C2)**:
  1. Hệ thống tăng số lần thử. Đơn quay lại hàng chờ sau **khoảng cách tối thiểu** (PA 60 phút, tham số).
  2. Đạt **N lần** (PA 3) **hoặc** quá **H giờ** kể từ lúc thanh toán (PA 24 giờ làm việc), đơn chuyển **"Cần quyết định"** trong khối "Cần chú ý" của Quản lý/Chủ.
  3. Quản lý chọn một trong ba:
     - (a) **Giao theo địa chỉ khách đã nhập** mà không cần xác nhận. Ghi lý do, sang UC-CS-3.
     - (b) **Chờ thêm**, đặt hạn mới.
     - (c) **Huỷ + hoàn toàn phần** (P-07, `cancel_paid_order` + `create_refund`).
- **Ngoại lệ**:
  - E1. "Sai số" (số không tồn tại): bỏ qua N lần, lên "Cần quyết định" ngay.
  - E2. Không có hành động tự huỷ. Hệ thống **không bao giờ tự huỷ** đơn đã trả tiền (tiền đã thu, huỷ phải có người chịu trách nhiệm).
- **Hậu điều kiện**: không đơn nào đã trả tiền bị "kẹt" ở Chờ xác nhận mà không ai biết.

### UC-CS-6 Khách muốn đổi món, đổi kg, hoặc huỷ khi gọi
- **Tiền điều kiện**: đơn đã thanh toán, phiếu chưa READY.
- **Luồng chính (PA, Q-C3)**. Đơn đã trả tiền **không sửa dòng hàng** (BR-PQ-11: đơn và hoá đơn chỉ Hệ thống tạo; BR-BH-08: giá đóng băng):
  - **Thêm món**: khách tự đặt **đơn mới** trên Shop (CSKH gửi hướng dẫn, không tạo đơn thay khách). Hai đơn có thể giao cùng chuyến (🟢 gộp giao).
  - **Bớt món / giảm kg / đổi món**: Quản lý **huỷ toàn bộ đơn + hoàn toàn phần**, khách đặt lại đơn đúng ý. Đây là cách duy nhất code hiện có làm đúng cả kho lẫn tiền.
  - **Huỷ**: CSKH ghi "khách muốn huỷ" + lý do. Đơn vào "Cần quyết định", Quản lý huỷ (`cancel_paid_order`) và lập phiếu hoàn (`create_refund`). Chủ chuyển khoản và xác nhận (`confirm_refund`, BR-HT-03). Theo memo pháp lý `01c-phap-ly.md`, hạn hoàn là 30 ngày.
- **Luồng thay thế**: nếu Duy muốn "bớt món mà không huỷ cả đơn" thì cần **hoàn kho một phần theo dòng**. Code hiện **chưa có** (§3.2). Đây là tính năng P-07 riêng, không làm trong hồ sơ này.
- **Ngoại lệ**: khách đổi ý nhiều lần trong một cuộc gọi: chỉ kết quả cuối được ghi. Mỗi lần bấm là một bản ghi.
- **Hậu điều kiện**: không có đơn đã trả tiền nào bị sửa số tiền ngoài luồng hoàn tiền. Tiền rời túi vẫn chỉ qua Chủ.

### UC-CS-7 Kịch bản gọi và gợi ý (không AI và có AI)
- **Không AI (luôn có)**: kịch bản soạn sẵn theo tình huống: đơn lần đầu, khách cũ, đơn có combo, đơn giao xa. Nội dung tư vấn gồm cách rã đông và bảo quản. Chủ soạn nội dung (🟡 Q-C14).
- **Có AI (tuỳ hồ sơ `ai-digital-worker`)**: AI chỉ nhận **mã đơn, dòng hàng, kg, trạng thái, số lần gọi trước và mã kết quả**. AI **không** nhận tên, SĐT, địa chỉ hay ghi chú tự do của CSKH (bất biến 9, H2 trong hồ sơ AI). Ghi chú tự do có thể chứa PII do khách đọc qua điện thoại, nên loại khỏi đầu vào AI. AI **không** ghi kết quả cuộc gọi thay người. Kết quả gọi là lời khai của người đã nói chuyện với khách.
- Khối "Tiếp theo" (§4.7 hồ sơ AI) của đơn ở Chờ xác nhận: "Gọi khách xác nhận, việc của CSKH, lần thử 2/3, hạn …". Khối "Đã làm" hiện các lần gọi **chỉ bằng mã kết quả**, không hiện ghi chú tự do cho người không có quyền xem PII.

### UC-CS-8 Kho quét tem để soạn hàng
- **Tiền điều kiện**: tem đã in, phiếu ở Soạn hàng. NV kho có điện thoại (camera) hoặc máy quét mã vạch.
- **Luồng chính**:
  1. NV kho quét mã trên tem. Mã chỉ chứa **mã phiếu giao**, không chứa PII hay đường link có PII.
  2. Màn phiếu soạn mở: dòng hàng, kg, **lô cần lấy và hạn dùng** theo phân bổ đã chốt (BR-BH-06/11). Không có giá vốn (S19-AC5).
  3. NV kho lấy đúng lô, cân, đóng gói, dán tem lên thùng, bấm "Đã đóng gói" → READY (S19).
- **Luồng thay thế**: 1a. Không quét được (tem nhoè): gõ mã phiếu in trên tem.
- **Ngoại lệ**:
  - E1. Quét tem của phiếu **đã huỷ**: hiện đỏ "Đơn đã huỷ, không soạn, xé tem" (BR-GH-07, BR-GH-17).
  - E2. Quét tem **cũ** đã bị thay (đổi địa chỉ, in lại): hiện "Tem này không còn hiệu lực, dùng tem in lần n" (BR-GH-16).
  - E3. Lô cần lấy đã **quá hạn** tại lúc soạn (lô chốt lúc đặt, đơn chờ xác nhận lâu): không soạn, xử lý như "soạn phát hiện hàng hỏng" (E-07, P-07). Với hạn 365 ngày thì hiếm, nhưng hàng chờ gọi làm khoảng chờ dài ra.
  - E4. Lô cần lấy **không còn đủ kg thực tế** (lệch kiểm kê): như E3.
- **Hậu điều kiện**: phiếu READY, tem đi theo thùng.
- *Ngoài phạm vi*: quét **nhãn lô** trên thùng hàng trong kho để đối chiếu FEFO. Hệ thống chưa có nhãn lô in ra (🟢 Q-C16).

## 6. Business rule

| Mã | Nội dung | Nhãn | Mới / Sửa / Giữ |
|---|---|---|---|
| **BR-GH-11** | Đơn đã thanh toán đủ phải qua bước **CSKH xác nhận với khách** trước khi vào danh sách soạn. Bước này nằm **sau** thanh toán và **trước** Soạn hàng. Kho không soạn đơn chưa xác nhận | D (yêu cầu) + PA (vị trí) | **Mới**, chờ Q-C1 |
| **BR-GH-12** | Kết quả cuộc gọi chọn từ **danh sách cố định**: Đã xác nhận · Đổi thông tin nhận · Không liên lạc được · Hẹn gọi lại · Muốn đổi món · Muốn huỷ. Ghi chú tự do là tuỳ chọn và ngắn. Mỗi lần gọi là một bản ghi **append-only** (ai, lúc nào, kết quả) | PA | **Mới** |
| **BR-GH-13** | Không liên lạc được sau **N lần** cách nhau tối thiểu **M phút**, hoặc quá **H giờ** từ lúc thanh toán, thì đơn sang "Cần quyết định" cho Quản lý/Chủ. N, M, H là **tham số cấu hình** (bất biến 7). Hệ thống **không tự huỷ** đơn đã trả tiền | PA | **Mới**, chờ Q-C2 |
| **BR-GH-14** | CSKH **không** sửa dòng hàng, số kg, giá hay tổng tiền của đơn đã trả. Mọi thay đổi về tiền đi qua huỷ + hoàn (P-07) do Quản lý/Chủ làm | PA, suy từ BR-PQ-11, BR-BH-08, BR-HT-07 | **Mới**, chờ Q-C3 |
| **BR-GH-15** | CSKH được đổi **địa chỉ giao và người nhận** khi phiếu còn Chờ xác nhận hoặc Soạn hàng. Địa chỉ mới phải trong vùng giao (BR-BH-12). SĐT dùng để tra đơn (`order.phone`) **không đổi**. AuditLog ghi hành động, **không** ghi giá trị | PA | **Mới** |
| **BR-GH-09** *(sửa)* | Hệ thống tạo **đúng một** lệnh in tự động **khi đơn được CSKH xác nhận** (trước đây: khi thanh toán xong). Xác nhận trùng không tạo lệnh mới. Lệnh không in được thì giữ ở hàng chờ, không mất | L (in tự động) + D (sau xác nhận) | **Sửa** (đề xuất 26/09, chưa duyệt) |
| BR-GH-10 | In lại có AuditLog, cho `nv_kho`/`quan_ly`/`chu`. Nội dung in **không bao giờ** có giá vốn, lãi. Tem không in số tiền, chỉ ghi "ĐÃ THANH TOÁN, không thu thêm" | PA (26/09) | Giữ |
| **BR-GH-16** | Mỗi tem mang **mã phiếu giao + số lần in**. Đổi thông tin nhận hàng hoặc in lại thì **chỉ tem mới nhất có hiệu lực**. Quét tem cũ bị cảnh báo | PA | **Mới** |
| **BR-GH-17** | **Tem là giấy chứa dữ liệu cá nhân.** Tem in lỗi, in trùng, tem cũ sau khi đổi địa chỉ, tem của đơn huỷ phải **huỷ vật lý** (xé, cắt) tại kho, không vứt nguyên tờ. Hệ thống nhắc việc huỷ tem trên màn kho | PA, suy từ bất biến 9 | **Mới** |
| **BR-GH-18** | **Phạm vi PII cho CSKH** (Tầng 3): CSKH chỉ thấy tên, SĐT, địa chỉ của đơn **đang Chờ xác nhận / Cần quyết định** và đơn **mình đã gọi trong X ngày** (PA 7). Ngoài phạm vi thì danh sách che (`09xx xxx 123`), chi tiết trả 404. CSKH không thấy giá vốn | PA, suy từ bất biến 9 | **Mới**, chờ Q-C5 |
| **BR-GH-19** | Bản ghi cuộc gọi, ghi chú cuộc gọi, lệnh in và nội dung tem **không được ghi vào log** (logger, Sentry, console FE) và **không gửi cho AI hay bên thứ ba**. Log chỉ có mã đơn, mã phiếu, mã kết quả | PA, suy từ bất biến 9 | **Mới** |
| **BR-GH-20** | **Không ghi âm cuộc gọi** ở V1. Nếu sau này ghi âm thì bản ghi âm là dữ liệu cá nhân (giọng nói), phải có **thông báo và đồng ý** ở đầu cuộc gọi, hạn lưu, quyền xoá, và qua `legal-vn` trước | PA | **Mới**, 🟡 Q-C7 |
| BR-BH-11 | Lô chốt lúc tạo đơn, không chọn lại. Chờ xác nhận lâu **không** làm đổi lô | D | Giữ |
| BR-TT-06 / BR-BC-01 | Doanh thu ghi lúc xác nhận thanh toán, **không** chờ CSKH xác nhận | PA (đã chốt 10/09) | Giữ |
| BR-HT-02 | Hoàn một phần. Code có phần tiền, **chưa có phần kho theo dòng** | PA | Giữ, ghi nhận khoảng trống |
| BR-GH-07 | Không giao, không soạn phiếu của đơn đã huỷ | (code S14) | Giữ, áp cho quét tem |

## 7. Tác động dữ liệu & tích hợp
*(Không thiết kế chi tiết. Chỉ nêu cái bị đụng và lý do, để thoả bất biến 8.)*

### 7.1 Dữ liệu
| Cái bị đụng | Lý do | Ghi chú PII |
|---|---|---|
| Trạng thái "Chờ xác nhận" (và "Cần quyết định") trước Soạn hàng | BR-GH-11. Tech Lead chọn đặt ở phiếu giao hay ở đơn | Không |
| **Bản ghi cuộc gọi** (thực thể mới) gắn đơn/phiếu: người gọi (FK `User`, PROTECT), lúc, kết quả, giờ hẹn, ghi chú ngắn | BR-GH-12. Append-only như AuditLog | **Ghi chú là PII tiềm ẩn**: serializer tách theo quyền, không log, không vào AI, ẩn danh hoá khi khách yêu cầu xoá |
| Khoá mềm "đang gọi" | UC-CS-2 bước 1, chống gọi trùng | Không |
| Người nhận hộ: tên + SĐT **trên phiếu giao** (field mới) | BR-GH-15, UC-CS-4 E1. Giữ `order.phone` cho tra đơn | **Field PII mới.** Lý do thu: giao hàng khi người khác nhận hộ. **Cần Duy duyệt** (bất biến 9, thu tối thiểu) |
| Lệnh in / lịch sử in (đề xuất N6 cũ): trạng thái, lần in, người in lại, **đã huỷ tem** | BR-GH-09/10/16/17 | Lệnh in **không lưu bản sao nội dung tem**. Nội dung tính lúc in từ đơn |
| Tham số: N lần, M phút, H giờ, X ngày phạm vi PII, hạn cảnh báo chờ in | BR-GH-13/18, bất biến 7 | — |
| Quyền mới: xác nhận giao với khách, đổi thông tin nhận hàng, (in lại, thiết bị in theo hop-duy-loc) | §4 | — |
| Group/vai CSKH | Q-C5, phụ thuộc hồ sơ vai trò tự định nghĩa | — |
| `Customer.default_address` | **Không đổi** (PA Q-C10) | — |

### 7.2 Màn hình, API
- **ERP mới**: "Hàng chờ gọi" (danh sách, lọc: chờ, hẹn gọi lại, cần quyết định), chi tiết gọi (thông tin nhận hàng, lịch sử gọi, kịch bản, nút kết quả). Ưu tiên **điện thoại** vì CSKH gọi bằng điện thoại, SĐT là link `tel:` (như S16-AC8).
- **ERP sửa**: chi tiết đơn S10 (khối cuộc gọi, trạng thái xác nhận); S17 (cột xác nhận, cột in); S19 (quét tem, huỷ tem, in lại); S24 (đơn quá hạn gọi, lệnh in lỗi/chờ lâu, tem cần huỷ); khối Tiếp theo/Đã làm (§4.7 hồ sơ AI).
- **Shop**: tra đơn thêm nhãn trạng thái "Chờ vựa gọi xác nhận" (chỉ trạng thái). Trang thanh toán/đặt xong thêm câu "Vựa sẽ gọi số … để xác nhận trước khi giao" (Q-C9).
- **Bên thứ ba**: không có trong V1. Tổng đài ảo, SMS hay Zalo ZNS để báo khách **đều là gửi PII ra ngoài**, cần Duy duyệt và chính sách quyền riêng tư (🟢 Q-C15).

### 7.3 Ràng buộc kỹ thuật cho Tech Lead (BA nêu, không chọn)
1. **"Tự động in" không làm được từ một tab trình duyệt thường.** `window.print()` luôn mở hộp thoại in và cần người bấm. FE ERP là static export, không có server FE. Backend Cloud Run không với tới máy in trong LAN kho. Mọi hướng khả thi đều là **thiết bị ở kho chủ động hỏi lệnh**:
   - (a) Máy tính ở kho mở một trang ERP "trạm in" chạy liên tục, trình duyệt ở chế độ **in không hỏi** (kiosk printing, cờ khởi chạy của Chrome/Edge). Rẻ nhất, không cài thêm phần mềm. Đóng tab là ngừng in. Máy phải luôn bật.
   - (b) **Chương trình nhỏ** trên máy hoặc mini-PC ở kho, hỏi API rồi gửi lệnh thẳng tới máy in nhiệt (ESC/POS, TSPL/ZPL). Ổn định hơn, phải cài đặt và bảo trì.
   - (c) **In từ điện thoại Android** tới máy in nhiệt Bluetooth, qua Web Bluetooth/Web Serial/WebUSB (chỉ Chromium, iOS không hỗ trợ), hoặc qua app của hãng máy in. Vẫn cần người mở màn.
   - (d) **Dịch vụ in đám mây** (loại PrintNode). **Gửi PII ra bên thứ ba**, thường đặt server ở nước ngoài. Theo decisions 2026-09-09 thì phải qua adapter FastAPI. Cần Duy duyệt, `legal-vn` xem mục 6b checklist. BA **không khuyến nghị**.
2. **Khổ tem**: tem vận chuyển phổ biến là **decal nhiệt 100×150 mm** (4×6"). Giấy cuộn 80 mm hợp phiếu soạn, không hợp dán thùng đá. Thùng đá ẩm nên cần decal **chịu ẩm/lạnh**. Mẫu in cần `@page` đúng khổ và kiểm trên máy thật.
3. **Mã trên tem**: Code128 hoặc QR chỉ chứa **mã phiếu giao**, không chứa URL có tham số PII, không chứa SĐT. Quét bằng camera điện thoại cần HTTPS (đã có) và quyền camera. Máy quét USB hoạt động như bàn phím nên không cần quyền gì thêm.
4. **PII ở phía trình duyệt**: không lưu nội dung tem hay hàng chờ gọi vào `localStorage`, IndexedDB hay URL. Không `console.log` payload (bất biến 9). Trạm in chạy 24/7 nên dùng **tài khoản kỹ thuật quyền hẹp**. Phiên đăng nhập trên máy đó không được có quyền xem PII ngoài lệnh in.
5. **Idempotent**: xác nhận và in phải chịu được bấm lại hoặc mạng rớt (UC-CS-2 E3, UC-CS-3 E5), giống quy ước `from_status`/`already` của S19.
6. **Không có hàng đợi đẩy** (không Redis/Celery). Cảnh báo quá hạn gọi hoặc chờ in chạy theo job Cloud Scheduler hiện có, hoặc tính lúc đọc.

## 8. Rủi ro Cá Về

| Loại | Rủi ro | Giảm thiểu đề xuất |
|---|---|---|
| **Dữ liệu cá nhân (Critical)** | Thêm **một vai mới được xem tên, SĐT, địa chỉ hàng loạt**. Nếu dùng chung phạm vi `FULL_SCOPE_GROUPS` thì CSKH thấy toàn bộ lịch sử khách | BR-GH-18: phạm vi dòng theo trạng thái + thời gian, che SĐT ngoài phạm vi, test bằng token CSKH thật như test giá vốn |
| **Dữ liệu cá nhân** | **Tem giấy** rời khỏi hệ thống: tem in lỗi, in trùng, tem cũ nằm trong thùng rác kho; tem trên thùng qua tay nhiều người | BR-GH-17 huỷ vật lý + nhắc trên màn; tem **che bớt SĐT** (Q-C6); phiếu soạn nội bộ **không có PII** |
| **Dữ liệu cá nhân** | CSKH gọi bằng **điện thoại cá nhân**: nhật ký cuộc gọi, Zalo và danh bạ máy riêng giữ SĐT khách sau khi nghỉ việc | 🟡 Q-C7: dùng máy/SIM của vựa. Đây là quy định vận hành, hệ thống chỉ nhắc |
| **Dữ liệu cá nhân** | Ghi chú tự do chứa địa chỉ/SĐT mới, lọt vào AuditLog, log, prompt AI | BR-GH-19; AuditLog chỉ ghi hành động; AI chỉ nhận mã kết quả (UC-CS-7) |
| **Dữ liệu cá nhân** | Dịch vụ in đám mây hoặc tổng đài ảo là bên thứ ba ở nước ngoài | Không dùng ở V1. Muốn dùng thì Duy duyệt và qua `legal-vn` |
| **Tiền** | CSKH "chiều khách" sửa món, sửa kg trên đơn đã trả → tiền lệch sổ | BR-GH-14: không sửa đơn. Đổi = huỷ + hoàn qua Quản lý/Chủ |
| **Tiền / khách** | Đơn đã trả tiền nằm chờ gọi quá lâu → khách bực, đòi hoàn; theo Luật BVQLNTD phải hoàn đúng hạn | BR-GH-13 + cảnh báo "Cần chú ý"; câu thông báo ở Shop (Q-C9) |
| **Phân quyền** | Trạm in 24/7 dùng tài khoản người thật | Tài khoản kỹ thuật riêng, thu hồi được (hop-duy-loc) |
| **Chứng từ / AuditLog** | Bản ghi cuộc gọi bị sửa/xoá để "đẹp số" | Append-only, không xoá (bất biến 3). Ẩn danh hoá khi khách yêu cầu |
| **Tồn / FEFO** | Khoảng từ "trừ kho sổ" (lúc trả tiền) đến "hàng rời kệ" (lúc soạn) **dài ra** (vài giờ tới vài ngày). **Kiểm kê trong khoảng này ra chênh dương giả** vì hàng đã trừ sổ còn nằm trên kệ | Kiểm kê phải biết hàng "đã bán chưa soạn" theo lô, hoặc không kiểm kê khi còn đơn chờ. Chuyển Tech Lead/PO cho P-09 (🟡 Q-C17) |
| **Tồn / FEFO** | Lô chốt lúc đặt có thể **quá hạn trước khi soạn** nếu đơn chờ lâu | UC-CS-8 E3; BR-GH-13 giới hạn thời gian chờ |
| **Vận hành** | CSKH là **nút cổ chai mới**. Không ai trực (Lộc đi cảng rạng sáng) → mọi đơn đứng. Đúng loại tắc nghẽn mà quyết định 10/09 muốn tránh | Kiêm nhiệm Group (E-17); Quản lý làm thay được; Q-C8 cho phép bỏ qua có điều kiện |
| **Vận hành** | Máy in chết, không ai biết | E4 cảnh báo chờ in (như BR-BH-04) + đường in tay dự phòng (UC-CS-3 3c) |
| **Pháp lý hàng hoá** | Tem dán lên thùng hàng thực phẩm bao gói sẵn bán lẻ có thể phải đáp ứng **ghi nhãn hàng hoá** (tên hàng, khối lượng, hạn dùng, hướng dẫn bảo quản, xuất xứ…). BA chưa kiểm chứng văn bản | Chuyển `legal-vn` (Q-C6). Nếu bắt buộc thì tem cần in **hạn dùng của lô** |
| **Giá vốn** | Mẫu tem, API hàng chờ gọi, API lệnh in là serializer mới dễ kèm `unit_cost` | Test "không có key giá vốn" cho mọi endpoint mới (như S19-AC5), cấm `fields="__all__"` |

## 9. Ngoài phạm vi
- Tem, mã vận đơn, đồng bộ trạng thái với **bên vận chuyển ngoài** (quyết định 26/09 Q1 chưa vào `decisions.md`, khảo sát chưa chốt).
- **Hoàn kho một phần theo dòng** (bớt món không huỷ cả đơn): tính năng P-07 riêng.
- CSKH **tạo đơn thay khách** (lật BR-PQ-11).
- Ghi âm, tổng đài ảo, SMS, Zalo ZNS, gọi tự động.
- AI gọi điện hoặc nhắn tin cho khách; AI trên Shop (đã chốt "Shop không có AI"; `research/01-mcp-per-function.md` §8.4).
- Khiếu nại/ticket sau giao hàng (research §8.3: chưa có, cần hồ sơ BA riêng).
- Nhãn lô trong kho và quét lô để đối chiếu FEFO khi lấy hàng (Q-C16).
- Gộp nhiều đơn của cùng khách vào một chuyến/một thùng.
- Hoá đơn VAT, hoá đơn điện tử.

## 10. Phân đoạn đề xuất (để PO cắt story)

| Đoạn | Nội dung | Phụ thuộc | BR |
|---|---|---|---|
| **Tiền đề** | **S17, S18, S19** (điều phối, gán, soạn hàng) của backlog L10–L11 | Chưa làm, màn Giao hàng đang Placeholder | BR-GH-03..08 |
| **C1** | Vai/quyền CSKH + phạm vi PII (Tầng 3), test bằng token CSKH | Q-C5; hồ sơ vai trò tự định nghĩa | BR-GH-18, bất biến 9 |
| **C2** | Bước "Chờ xác nhận" chặn kho + hàng chờ gọi + ghi kết quả + lịch sử gọi + khoá mềm | C1, Q-C1 | BR-GH-11, 12, 19 |
| **C3** | Đổi địa chỉ / người nhận khi gọi | C2; vùng giao (N1/N2 hop-duy-loc) nếu có | BR-GH-15 |
| **C4** | Không liên lạc được: đếm lần, hẹn gọi lại, "Cần quyết định", 3 lựa chọn của Quản lý; đường huỷ + hoàn dùng S14/S15 có sẵn | C2, Q-C2, Q-C3 | BR-GH-13, 14 |
| **C5** | Mẫu tem (+ phiếu soạn), in tay / in lại từ trình duyệt, số lần in, huỷ tem (thay N5) | S19, Q-C6 | BR-GH-10, 16, 17 |
| **C6** | In tự động sau xác nhận: lệnh in, trạm in ở kho, cảnh báo chờ in (thay N6) | C2, C5, **Q-C4** | BR-GH-09 (sửa) |
| **C7** | Quét tem ở kho để mở phiếu soạn, cảnh báo tem cũ / đơn huỷ | C5, S19 | BR-GH-16, 07 |
| **C8** | Shop: nhãn "Chờ vựa gọi xác nhận" ở tra đơn + câu thông báo khi đặt | C2 | — |
| **C9 (sau)** | Kịch bản gọi soạn sẵn; khối Tiếp theo/Đã làm cho bước gọi; tuỳ chọn AI gợi ý (không PII) | C2; hồ sơ AI §4.7 | BR-AI-* |

**Chạy được sớm nhất có giá trị**: Tiền đề + C1 + C2 + C5 (in tay). Kho làm việc bằng tem in tay ngay sau khi CSKH xác nhận. C6 (in tự động) chờ có thiết bị.

## 11. Câu hỏi mở

| # | Mức | Câu hỏi | Mặc định PA đề xuất |
|---|---|---|---|
| **Q-C1** | 🔴 | **Bước gọi xác nhận đặt ở đâu?** (a) **Sau** khi khách trả tiền, trước soạn hàng. Thêm bước "Chờ xác nhận" trước "Soạn hàng", tức **sửa chuỗi trạng thái phiếu giao** trong decisions 2026-09-10, và **sửa BR-GH-09** thành "in sau xác nhận" thay vì "in khi thanh toán". (b) **Trước** khi trả tiền: gọi xong mới gửi QR. Phải bỏ TTL 30' và luồng trả tiền ngay lúc đặt (lật decisions 09/09 + 26/09). | **(a).** Khách trả 100% ngay khi đặt, TTL 30' quá ngắn để gọi. Đổi địa chỉ thì không đụng tiền, đổi món thì đi huỷ + hoàn có sẵn. Duy cần ghi quyết định mới vào `decisions.md` |
| **Q-C2** | 🔴 | **Không liên lạc được thì sao?** Thử mấy lần, cách nhau bao lâu, chờ tối đa bao lâu, và hết hạn thì mặc định làm gì: (a) giao theo địa chỉ khách đã nhập; (b) chờ tiếp; (c) huỷ + hoàn toàn phần? | **3 lần**, cách nhau **≥ 60 phút**, tối đa **24 giờ làm việc** kể từ lúc trả tiền (tham số). Hết hạn thì **không tự làm gì**: đưa vào "Cần quyết định", Quản lý chọn (a)/(b)/(c). "Sai số" lên thẳng Cần quyết định. Không bao giờ tự huỷ đơn đã trả |
| **Q-C3** | 🔴 | **Khách muốn đổi món hoặc đổi số kg khi gọi** thì làm gì? (a) Không sửa đơn: thêm = đặt đơn mới trên Shop; bớt/đổi = huỷ cả đơn + hoàn toàn phần + đặt lại. (b) Cho bớt món trên đơn cũ, cần làm **hoàn kho một phần theo dòng** (code chưa có). (c) Cho CSKH sửa đơn và thu/hoàn phần chênh (lật BR-PQ-11, BR-BH-08; tiền thêm phải có QR bổ sung). | **(a)** cho V1. Không đụng tiền ngoài luồng hoàn đã có. (b) để hồ sơ P-07 riêng. (c) không khuyến nghị (mở đường sửa doanh thu) |
| **Q-C4** | 🔴 | **Thiết bị in ở kho** (nối tiếp Q8 hop-duy-loc, chưa trả lời): có máy tính luôn bật ở kho không, hay chỉ có điện thoại? Máy in gì (nhiệt decal 100×150, nhiệt 80 mm, A5 laser)? In ngoài giờ không? Chấp nhận hướng nào ở §7.3: (a) trạm in trình duyệt kiosk, (b) chương trình nhỏ ở kho, (c) điện thoại Android + máy in Bluetooth, (d) dịch vụ in đám mây? | **Máy in nhiệt decal 100×150 mm** + **một máy tính luôn bật** chạy trạm in kiosk **(a)**. Giai đoạn chưa có thiết bị thì in tay từ trình duyệt (UC-CS-3 3c). **Không** dùng (d) |
| **Q-C5** | 🔴 | **Ai là CSKH và quyền đặt ở đâu?** Hồ sơ "vai trò tự định nghĩa" chưa có. V1 làm theo cách nào: (a) thêm **Group thứ năm `cskh`** (cộng dồn, cách của 10/09); (b) chỉ cấp quyền CSKH cho `quan_ly`/`chu`, chờ hồ sơ vai trò tự định nghĩa; (c) chờ hồ sơ vai trò tự định nghĩa xong mới làm? Kèm theo: CSKH được xem PII trong phạm vi nào (BR-GH-18)? | **(a)**: thêm `cskh` bằng data migration. Sau này hồ sơ vai trò tự định nghĩa sẽ gom vào. Phạm vi PII: đơn đang Chờ xác nhận / Cần quyết định + đơn mình đã gọi trong **7 ngày**. Ngoài phạm vi thì che SĐT, chi tiết trả 404 |
| Q-C6 | 🟡 | **Tem in gì?** | **Tem giao (dán thùng)**: mã phiếu + mã đơn + mã vạch/QR (chỉ mã phiếu), tên người nhận, **SĐT che giữa** (`09xx xxx 123`, NV giao gọi qua app S20), địa chỉ đầy đủ, số kiện "1/1", tổng kg, "ĐÃ THANH TOÁN, không thu thêm", lần in, **hạn dùng sớm nhất** trong đơn. **Phiếu soạn (nội bộ, không PII)**: mã phiếu, dòng hàng, kg, **mã lô + hạn dùng** từng lô. Không giá, không giá vốn. **Cần `legal-vn` xem quy định ghi nhãn hàng hoá thực phẩm** có buộc thêm trường không |
| Q-C7 | 🟡 | Có **ghi âm** cuộc gọi không? CSKH gọi bằng máy nào? | **Không ghi âm** ở V1 (BR-GH-20). Gọi bằng **điện thoại/SIM của vựa**, không dùng máy cá nhân. Ghi vào quy định nội bộ; hệ thống chỉ nhắc |
| Q-C8 | 🟡 | **Mọi đơn** đều phải gọi, hay có đơn được bỏ qua (khách cũ, cùng địa chỉ đã giao thành công)? | **Mọi đơn** ở V1. Sau khi có dữ liệu thì Chủ bật quy tắc bỏ qua (🟢) |
| Q-C9 | 🟡 | Có báo khách biết trước là vựa sẽ gọi không? | Có. Câu cố định ở trang đặt xong và trên tra đơn: "Vựa sẽ gọi số đã đăng ký để xác nhận trước khi giao, trong giờ …". Giờ làm CSKH là tham số |
| Q-C10 | 🟡 | Khách đổi địa chỉ khi gọi thì có cập nhật **địa chỉ mặc định** của khách không? | **Không** tự cập nhật. Chỉ đổi trên đơn này |
| Q-C11 | 🟡 | **Người nhận hộ** (tên, SĐT khác) lưu thế nào? | Field riêng trên phiếu giao (**field PII mới, cần Duy duyệt**). `order.phone` giữ nguyên để khách vẫn tra đơn được |
| Q-C12 | 🟡 | Việc **huỷ tem giấy** có cần xác nhận trên hệ thống không? | Có, một nút "Đã huỷ tem" cho tem của đơn huỷ và tem cũ bị thay. Tem chưa bấm hiện trong "Cần chú ý". Không cần ảnh chụp |
| Q-C13 | 🟡 | Quyết định 26/09 (thuê vận chuyển tuyến xa) chưa vào `decisions.md`. Hồ sơ này theo "100% NV nội bộ". Đúng không? | Đúng. Tem cho bên vận chuyển là hồ sơ riêng khi chọn được hãng |
| Q-C14 | 🟡 | Ai soạn **kịch bản gọi / nội dung tư vấn**? | Chủ soạn trong ERP, dạng văn bản theo tình huống. Không có AI vẫn đủ dùng |
| Q-C15 | 🟢 | Báo khách qua SMS/Zalo khi không gọi được? | Để sau. Là gửi PII cho bên thứ ba, cần duyệt + chính sách |
| Q-C16 | 🟢 | In **nhãn lô** dán thùng trong kho lạnh để quét đối chiếu đúng lô FEFO khi lấy hàng? | Để sau, hồ sơ riêng (P-02/P-04) |
| Q-C17 | 🟡 | Kiểm kê (P-09) khi còn đơn "đã trừ sổ nhưng chưa soạn": xử lý thế nào? | Màn kiểm kê hiện số kg "đã bán chưa xuất" theo lô để người đếm cộng lại. Chuyển Tech Lead/PO kiểm chứng P-09 hiện tại |
| Q-C18 | 🟢 | Báo cáo CSKH (số cuộc gọi, tỉ lệ xác nhận, thời gian chờ trung bình) | Để sau khi có dữ liệu thật |

---
*Liên quan: `2026-09-26-hop-duy-loc/01-analysis.md` (BR-GH-09/10, N5/N6, Q8), `2026-09-24-erp-console-noi-that/02-stories.md`
(S14–S24), `2026-09-28-ai-digital-worker/01-analysis.md` §4.7 và `research/01-mcp-per-function.md` §8.3–8.4,
`doc/ops/khao-sat-ben-van-chuyen.md` §4, `doc/ops/go-live-phap-ly.md`. Hồ sơ `2026-09-28-vai-tro-tu-dinh-nghia` chưa có.*

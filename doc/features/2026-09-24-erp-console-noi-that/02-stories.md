# ERP console "nối thật" — User stories
> PO · 2026-09-24 · Nguồn: 01-analysis.md (ĐÃ DUYỆT, quyết định Duy mục 11) · Trạng thái: **ĐÃ DUYỆT** (2026-09-24, Duy — nhận toàn bộ mặc định C1–C9)

---

## Mục tiêu & thước đo

**Vì sao làm.** Hiện Chủ, Quản lý, NV kho, NV giao chỉ xem được số trên ERP console. Muốn duyệt, huỷ, xác nhận tiền, gán người giao hay nhập phiếu thì phải vào Django Admin sửa field trực tiếp: bỏ qua luật, không có AuditLog. Có ba lỗi đang chạy trên production: lô quá hạn vẫn bán được, đơn khách đã trả tiền tự huỷ khi webhook lỗi, và `PATCH` chung cho phép vượt state machine.

**Đo thành công bằng:**
1. **0 lô quá ngày hạn** được phân bổ cho đơn mới (test tự động + kiểm dữ liệu production 7 ngày sau khi deploy S1–S2).
2. **100% thao tác Tầng 2** trong bảng §1.5 của spec làm được trên console, đi qua service và có AuditLog. Không còn thao tác nào buộc phải sửa field trong Admin (đếm theo checklist ở mục "Phủ use case").
3. **0 endpoint** trả field giá vốn/lãi lỗ cho token không có `view_costprice`/`view_profitreport` (bộ test token theo Group, BR-PQ-13).
4. NV giao làm trọn một phiếu (nhận hàng → hoàn tất hoặc thất bại → mang hàng về) **trên điện thoại màn 360 px**, không phải gọi ai sửa hộ.
5. Sau mốc deploy 1: **mọi** thao tác trên console có AuditLog với actor là tài khoản riêng của một nhân viên, **0** lượt đăng nhập console bằng `admin` dùng chung.
6. Không còn giao dịch lệch nào ở trạng thái "chưa xử lý" quá 24 giờ mà Chủ không thấy (khối "Cần chú ý").

## Phạm vi

**Trong:** cả 3 đợt (Duy chốt Q1).
- Sửa lỗi lõi và nền: lô quá hạn, khoá sửa chung, người tạo theo người đăng nhập, phạm vi NV giao, API "tôi là ai", khung console Next.js, khoá field Admin.
- **Tài khoản & phân quyền** (Duy bổ sung 2026-09-24, đưa lên từ Đợt 3): tài khoản riêng từng người, Chủ tạo/gán nhóm/đặt lại mật khẩu/cho nghỉ, chống tự nâng quyền, tự đổi mật khẩu, đăng xuất thu hồi phiên, màn "Quyền của tôi" (phần quản lý nhân sự của UC-23).
- **Đợt 1:** Đơn, tiền, giao hàng (UC-01…UC-12).
- **Đợt 2:** Lô, mua hàng, chi phí mua, kiểm kê, báo cáo (UC-13…UC-21).
- **Đợt 3:** Danh mục & giá, nhật ký, Trợ lý AI chỉ đọc (UC-22, phần nhật ký của UC-23, UC-24).

**Ngoài:** như mục 9 của 01-analysis: hoàn tiền tự động, bản đồ/định vị, phí giao, số kg thực xuất, điều chỉnh tồn tay `StockEntry`, ghi chú ca đồng bộ, SMS/Zalo, xuất Excel, huỷ **một phần** đơn (Q8a), làm việc offline (Q6), Trợ lý AI thao tác thay người.

## Quy ước chung cho mọi story (BE/FE/QA đọc một lần)

**Definition of Done:** test BE xanh (`manage.py test`), `erp-console` build tĩnh sạch (`npm run build`), QA report APPROVED, không rò giá vốn, doc cập nhật nếu đổi rule (thêm mã BR mới vào `business-process-spec.md` khi Duy duyệt story này).

**Contract API**
- Gốc `/api/`. Xác thực `Authorization: Token <token>` (token DRF từ `POST /api/auth/token/`).
- Lỗi nghiệp vụ: HTTP **400** `{"detail": "<tiếng Việt>", "code": "BR-GH-07"}`. Trường `code` là **mới**. BE thêm vào `exception_handler` ở S3; `BusinessError` nhận thêm mã BR. FE hiển thị `detail`, logic chỉ dựa vào `code`.
- 401 = chưa đăng nhập/token hỏng/tài khoản đã nghỉ. 403 = thiếu quyền. 404 = ngoài phạm vi dòng (BR-PQ-12: không tiết lộ là bản ghi có tồn tại).
- Danh sách phân trang DRF: `{"count": n, "next": url|null, "previous": url|null, "results": [...]}`, 20 dòng/trang, `?page=`.
- Tiền và kg trả về dạng **chuỗi thập phân** (`"540000"`, `"2.500"`), không phải số float (bất biến #7).
- **`available_actions`**: mọi chi tiết chứng từ trả danh sách thao tác người đang đăng nhập làm được **ở trạng thái hiện tại** (vd `["cancel","create_refund"]`). BE tính cả luật lẫn quyền, FE chỉ đọc danh sách này để hiện nút, không tự suy luật. Đây là cách giữ "console không có logic nghiệp vụ" (decisions 2026-09-09).
- **Field giá vốn** (`unit_cost`, `purchase_rate`, `landed_unit_cost`, `rate`, `amount` của hoá đơn mua, lãi lỗ): người thiếu quyền thì **không có key trong JSON**. Để `null` hay `"—"` đều không đạt (BR-PQ-15).
- FE dựng mock theo đúng JSON mẫu trong từng story (`NEXT_PUBLIC_USE_MOCK=1`).

**Mobile:** "dùng được trên điện thoại" nghĩa là ở viewport **360×640**: không cuộn ngang; nút thao tác chính cao ≥ **44 px**; SĐT là link `tel:`; form một cột. Các màn chỉ ghi "cả hai" phải đạt điều này **và** ở 1280×800 hiện bố cục 3 cột.

---

# ĐỢT 1 — Sửa lỗi lõi, nền console, Tài khoản & phân quyền, Đơn · Tiền · Giao hàng

## 1A. Sửa lỗi lõi & nền (làm trước mọi màn)

## S1 — Lô quá ngày hạn không bán được nữa · Must · BE
**Là** Chủ vựa, **tôi muốn** hệ thống không bao giờ giữ chỗ hay bán hàng từ lô đã quá ngày hạn, **để** khách không nhận cá hết hạn, kể cả khi chưa ai đổi trạng thái lô.
Bối cảnh: A16, mục 8 (rủi ro Cao). `allocate_fifo` (`backend/apps/inventory/services.py`) và phần tính tồn khả dụng cho Shop (`apps/catalog/pricing.py`) chỉ lọc theo `status`. Sửa ở tầng truy vấn, **không phụ thuộc** job S2: nếu job không chạy thì lô vẫn không bán được. "Hôm nay" tính theo giờ `Asia/Ho_Chi_Minh`. Ngày ghi trên `expiry_date` là **ngày cuối còn bán được** (PA, xem câu hỏi C1).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S1-AC1 | Mặt hàng X có lô A (nhập 01/09, hạn **hôm qua**, SELLING, còn 5 kg) và lô B (nhập 10/09, hạn +10 ngày, còn 5 kg) | Khách đặt 2 kg X | Phân bổ 2 kg từ **B**, A không bị giữ chỗ | BR-LO-02, BR-BH-05 |
| S1-AC2 | Lô A hạn = **hôm nay**, còn 5 kg, là lô cũ nhất | Khách đặt 2 kg | Phân bổ từ A (ngày cuối vẫn bán) | BR-LO-02 |
| S1-AC3 (lỗi) | Mặt hàng X chỉ còn lô quá hạn | Khách đặt 1 kg | 400 "Không đủ tồn khả dụng…", không tạo đơn, `qty_reserved` mọi lô không đổi | BR-BH-02 |
| S1-AC4 | Như AC1 | Gọi `GET /api/shop/catalog/` và `/api/shop/catalog/X/` | Tồn khả dụng hiển thị = 5 kg (chỉ lô B) | BR-LO-02 |
| S1-AC5 | Lô hạn ngày D; đồng hồ hệ thống 00:30 ngày D+1 **giờ VN** (17:30 ngày D UTC) | Khách đặt hàng | Lô không được phân bổ | BR-LO-02 |
| S1-AC6 (quyền) | — | — | Story không mở thao tác mới cho vai nào. Khách không truyền được mã lô vào `POST /api/shop/orders/` để chọn lô (field lạ bị bỏ qua, phân bổ vẫn theo FIFO hợp lệ) | BR-PQ-12 |

Ghi chú dev: một hàm/queryset dùng chung "lô bán được" (`status` ∈ SELLING/NEAR_EXPIRY **và** `expiry_date >= hôm nay VN`) để `allocate_fifo`, `pricing.py` và dashboard dùng chung.

## S2 — Job hằng ngày cập nhật trạng thái lô theo hạn và tồn · Must · BE
**Là** Chủ vựa, **tôi muốn** lô tự chuyển sang Cận hạn / Quá hạn / Hết hàng, **để** cảnh báo và danh sách lô phản ánh đúng thực tế mà không ai phải sửa tay.
Bối cảnh: A16, BR-LO-01/02/06. Chạy như `cancel_expired_orders`: management command `update_batch_status` và lịch hằng ngày lúc **00:05 giờ VN** (dùng cùng cơ chế lịch hiện có). Ngưỡng cận hạn = `BATCH_NEAR_EXPIRY_DAYS` (env, mặc định 14). Actor = Hệ thống (`None`).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S2-AC1 | Lô SELLING, hạn còn 14 ngày | Job chạy | Lô → NEAR_EXPIRY, 1 AuditLog `batch_near_expiry` actor = None | BR-LO-01, BR-PQ-04 |
| S2-AC2 | Lô SELLING/NEAR_EXPIRY/DRAFT, hạn = hôm qua | Job chạy | Lô → EXPIRED, 1 AuditLog `batch_expired` | BR-LO-02 |
| S2-AC3 | Lô SELLING, `qty_available` = 0 và `qty_reserved` = 0, chưa hạn | Job chạy | Lô → SOLD_OUT | BR-LO-06 |
| S2-AC4 | Lô SOLD_OUT được tái nhập hàng hoàn (tồn > 0), chưa hạn | Job chạy | Lô → SELLING (hoặc NEAR_EXPIRY nếu trong ngưỡng) | BR-LO-06, BR-HV-02 |
| S2-AC5 (idempotent) | Job vừa chạy xong | Chạy lần 2 cùng ngày | Không đổi trạng thái nào, **không** sinh thêm AuditLog | Bất biến #6 |
| S2-AC6 (lỗi) | Lô CLOSED hoặc CANCELLED đã quá hạn | Job chạy | Không đổi | BR-LO-05 |
| S2-AC7 (quyền) | NV kho đăng nhập | `PATCH /api/inventory/batches/{id}` `{"status":"EXPIRED"}` | 400 `BR-PQ-14` (xem S3). Không có endpoint nào cho người dùng kích job | BR-PQ-14 |

## S3 — Khoá sửa chung vượt state machine · Must · BE
**Là** Chủ vựa, **tôi muốn** trạng thái, tồn, giá vốn và người phụ trách của chứng từ chỉ đổi được qua đúng thao tác nghiệp vụ, **để** không ai (kể cả người biết mở DevTools) vượt luật mà không để lại AuditLog.
Bối cảnh: A9, A11, A17, A21, BR-PQ-14 (mới). Chặn bằng **400 có liệt kê field**, không lặng lẽ bỏ qua, để QA test được. Kèm việc thêm `code` vào định dạng lỗi (quy ước chung).

Field bị khoá với `PATCH`/`PUT` (và với `POST` tạo mới nếu client gửi):

| Endpoint | Field khoá |
|---|---|
| `inventory/batches` | `status`, `qty_received`, `qty_available`, `qty_reserved`, `purchase_rate`, `landed_unit_cost`, `expiry_date`, `closed_at`, `closed_by` |
| `delivery/notes` | `status`, `assigned_to`, `failed_attempts`, `completed_at`, `sales_invoice` |
| `inventory/returns` | `status`, `decision`, `approved_by` (tạo mới đi đường S22) |
| `inventory/reconciliations` | `status`, `approved_by`, `approved_at` |
| `purchasing/receipts` | `status` |
| `sales/refunds`, `sales/payments`, `sales/orders`, `sales/invoices` | chỉ đọc qua router; thay đổi chỉ qua action |

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S3-AC1 | Quản lý có `change_batch` | `PATCH /api/inventory/batches/{id}` `{"landed_unit_cost":"1"}` | 400 `{"code":"BR-PQ-14","detail":"Trường landed_unit_cost chỉ đổi qua thao tác nghiệp vụ…"}`, DB không đổi | BR-PQ-14, BR-GV-03 |
| S3-AC2 | NV giao sở hữu phiếu giao READY | `PATCH /api/delivery/notes/{id}` `{"status":"COMPLETED"}` hoặc `{"assigned_to":<người khác>}` | 400 `BR-PQ-14`, phiếu không đổi | BR-GH-06, BR-PQ-14 |
| S3-AC3 | Quản lý | `PATCH /api/inventory/batches/{id}` chỉ với field không khoá (vd `note`, nếu có) | 200, field được lưu | |
| S3-AC4 | Bất kỳ ai có quyền sửa | `DELETE` trên lô, phiếu giao, hàng hoàn, kiểm kê, phiếu nhập, phiếu hoàn, chi phí mua | 405, không xoá | BR-PQ-10 |
| S3-AC5 | Service raise `BusinessError` có mã BR | Gọi API bất kỳ gây lỗi đó | JSON có cả `detail` và `code` | |
| S3-AC6 (quyền) | NV giao | `PATCH /api/inventory/batches/{id}` | 403 (không có `change_batch`), trước cả kiểm field | BR-PQ-12 |

## S4 — Người tạo và người duyệt do hệ thống ghi · Must · BE
**Là** Chủ vựa, **tôi muốn** "ai nhập", "ai duyệt" trên chứng từ luôn là người đang đăng nhập, **để** luật "người nhập ≠ người duyệt" có nghĩa thật.
Bối cảnh: A11, A21, BR-PQ-16 (mới). Áp dụng khi tạo: phiếu kiểm kê, hàng hoàn, phiếu nhập, chi phí mua, phiếu hoàn, hoá đơn mua.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S4-AC1 | NV kho `kho1` | `POST /api/inventory/reconciliations/` không gửi `created_by` | 201, `created_by` = `kho1` | BR-PQ-16 |
| S4-AC2 (lỗi) | NV kho `kho1` | `POST` như trên kèm `"created_by": <id của ql1>` | 400 `BR-PQ-16`, không tạo phiếu | BR-PQ-16, BR-KK-02 |
| S4-AC3 | Quản lý `ql1` tạo phiếu kiểm kê | `ql1` gọi duyệt chính phiếu đó | 400 `BR-KK-02` | BR-KK-02 |
| S4-AC4 (quyền) | NV giao | `POST /api/inventory/reconciliations/` | 403 | BR-PQ-12 |

## S5 — NV giao chỉ thấy đơn và khách của phiếu mình · Must · BE
**Là** Chủ vựa, **tôi muốn** NV giao chỉ xem được đơn và thông tin khách của phiếu giao đã gán cho họ, **để** không lộ SĐT, địa chỉ của toàn bộ khách.
Bối cảnh: A28, spec §1.6, BR-PQ-09 (người kiêm nhiệm thấy hợp quyền).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S5-AC1 | NV giao `giao1` được gán phiếu của đơn D1; D2 gán cho `giao2` | `giao1` gọi `GET /api/sales/orders/` | Chỉ có D1 | BR-PQ-12 |
| S5-AC2 | Như trên | `giao1` gọi `GET /api/sales/orders/{D2}/` hoặc `GET /api/sales/customers/{khách D2}/` | 404 | BR-PQ-12 |
| S5-AC3 | Như trên | `giao1` gọi `GET /api/sales/customers/` | Chỉ khách của D1 | spec §1.6 |
| S5-AC4 | `kho1` thuộc cả `nv_kho` và `nv_giao` | Gọi `GET /api/sales/orders/` | Thấy mọi đơn (hợp quyền) | BR-PQ-09 |
| S5-AC5 (quyền) | Phiếu D1 đổi sang gán `giao2` | `giao1` gọi lại chi tiết D1 | 404 | BR-GH-06 |

## S6 — API "tôi là ai, có quyền gì" · Must · BE
**Là** nhân viên nội bộ, **tôi muốn** console biết tôi thuộc Group nào và có quyền gì, **để** chỉ thấy đúng menu và nút của mình.
Bối cảnh: UC-01, A25, BR-PQ-09. Token của người đã nghỉ phải hỏng ngay (Q5 mặc định: `is_active=False` là mọi phiên hết hiệu lực, không hết hạn theo thời gian).

**Contract**
```
GET /api/auth/me/
200 {
  "id": 7, "username": "loc", "display_name": "Lộc", "phone": "0909123456",
  "groups": ["chu"],
  "permissions": ["inventory.publish_batch", "inventory.close_batch", "sales.confirm_payment_manual", "..."],
  "can_view_cost": true, "can_view_profit": true,
  "home": "dashboard"            // "my-deliveries" nếu chỉ thuộc nv_giao; "no-role" nếu không Group nào
}
401 {"detail": "Thông tin xác thực không hợp lệ."}
```
`permissions` = toàn bộ `user.get_all_permissions()` dạng `app_label.codename`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S6-AC1 | `loc` thuộc `chu` | `GET /api/auth/me/` | 200, `groups=["chu"]`, `can_view_cost=true`, `can_view_profit=true`, `home="dashboard"` | BR-PQ-09 |
| S6-AC2 | `kho1` thuộc `nv_kho` + `nv_giao` | Gọi | `groups` có cả hai, `permissions` là hợp của hai Group, `home="dashboard"` | BR-PQ-09 |
| S6-AC3 | `giao1` chỉ thuộc `nv_giao` | Gọi | `home="my-deliveries"`, `can_view_cost=false` | UC-01 |
| S6-AC4 (lỗi) | Tài khoản không thuộc Group nào | Gọi | 200, `groups=[]`, `home="no-role"` | UC-01 E3 |
| S6-AC5 (lỗi) | `giao1` đang có token hợp lệ, Chủ đặt `is_active=False` | `giao1` gọi `/api/auth/me/` hoặc bất kỳ API nào | 401 | BR-PQ-01, Q5 |
| S6-AC6 (quyền) | Không có token | Gọi | 401 | |

## S7 — Khung ERP console Next.js: đăng nhập, bố cục, menu theo quyền · Must · FE
**Là** nhân viên nội bộ, **tôi muốn** đăng nhập vào console mới và thấy đúng các màn của vai mình trên cả điện thoại lẫn máy tính, **để** bắt đầu làm việc mà không bị rối bởi menu mình không dùng.
Bối cảnh: Duy chốt Q3 (Next.js, static export, Firebase `cangca-erp`) và Q4 (mobile-first cho NV giao/NV kho).

**Đề xuất vị trí: chuyển chính thư mục `erp-console/` thành app Next.js 14** (`output: 'export'`, `firebase.json` trỏ `public` sang `out`), **không** gộp vào `frontend/`.
Lý do:
1. Giữ nguyên `.firebaserc`/`firebase.json` đang gắn site `cangca-erp`, nên deploy không đổi.
2. Code back-office (tên endpoint nội bộ, màn giá vốn) **không lọt vào bundle Shop công khai**.
3. Build/deploy tách, sửa console không phải deploy lại Shop.
4. Cùng stack với `frontend/` nên chép được mẫu `lib/api.ts` + `lib/mock.ts`, không cần monorepo/workspace, hợp nguyên tắc "1 người maintain".

`public/index.html` cũ chuyển vào `erp-console/legacy/` làm tham chiếu và bị xoá khi S8 xong.

Bố cục kế thừa bản HTML: **cột trái** menu, **giữa** nội dung, **cột phải** (Ghi chú · Trợ lý · Hoạt động). Từ 1024 px trở lên hiện 3 cột. Dưới 1024 px, cột phải thành ngăn kéo mở bằng nút. Dưới 768 px, menu thành thanh dưới đáy (tối đa 5 mục) hoặc nút ☰.

Menu ↔ quyền (FE đọc từ `/api/auth/me/`, dùng mock theo contract S6):

| Menu | Hiện khi có |
|---|---|
| Tổng quan | `reports.view_dashboard` hoặc thuộc `chu`/`quan_ly`/`nv_kho` (BE chốt tên quyền trong S6) |
| Đơn & tiền | `sales.view_salesorder` |
| Giao hàng (điều phối) | `delivery.view_deliverynote` **và** không chỉ thuộc `nv_giao` |
| Việc giao của tôi | thuộc `nv_giao` |
| Kho & lô | `inventory.view_batch` |
| Mua hàng | `purchasing.view_purchasereceipt` |
| Kiểm kê | `inventory.view_stockreconciliation` |
| Báo cáo lãi lỗ | `can_view_profit` |
| Danh mục & giá | `catalog.view_item` |
| Nhân sự · Nhật ký | `accounts.manage_staff` |

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S7-AC1 | Mock `me` của Chủ | Đăng nhập đúng | Vào Tổng quan, menu hiện đủ các mục trong bảng | BR-PQ-15 |
| S7-AC2 | Mock `me` của `giao1` (chỉ `nv_giao`) | Đăng nhập | Vào thẳng "Việc giao của tôi"; menu chỉ có mục này | UC-01 |
| S7-AC3 (quyền) | Đăng nhập `giao1` | Gõ URL `/reports` | Hiện "Bạn không có quyền xem mục này", **không** gọi API báo cáo nào (kiểm bằng log request mock) | BR-PQ-15 |
| S7-AC4 (lỗi) | Sai mật khẩu hoặc tài khoản đã nghỉ | Đăng nhập | Thông báo "Sai tài khoản/mật khẩu hoặc tài khoản đã ngừng hoạt động", ở lại màn đăng nhập | UC-01 E1 |
| S7-AC5 (lỗi) | `me.home="no-role"` | Đăng nhập | Màn "Tài khoản chưa được phân quyền, liên hệ Chủ", không có menu | UC-01 E3 |
| S7-AC6 (lỗi) | Đang gõ dở một form có đánh dấu "giữ nháp" | API trả 401 | Về màn đăng nhập. Đăng nhập lại cùng người thì form mở lại **đủ nội dung đã gõ**. Người khác đăng nhập trên cùng máy thì nháp **bị xoá**, không hiện | UC-01 E2, Q6 |
| S7-AC7 (mobile) | Viewport 360×640 và 1280×800 | Mở mọi màn khung | 360: không cuộn ngang, menu đáy/☰, cột phải là ngăn kéo. 1280: 3 cột | Q4 |
| S7-AC8 | — | `cd erp-console && npm run build` với và không có `NEXT_PUBLIC_USE_MOCK=1` | Build sạch, sinh `out/` | DoD |

## S8 — Chuyển Tổng quan, Đơn, Kho & Lô sang console mới và thay bản cũ · Must · FE
**Là** Chủ vựa, **tôi muốn** các màn đang dùng hằng ngày chạy trên console mới với số liệu y như cũ, **để** chuyển sang mà không mất gì.
Bối cảnh: 3 view hiện có đều đọc `/api/dashboard/summary/`. Cột phải: Ghi chú giữ lưu cục bộ trên máy (Q19). Hoạt động = 8 dòng sổ kho. Trợ lý: **bỏ phần trả lời bằng regex**, hiện "Trợ lý đang được nối, sắp có" cho tới S45. Deploy lên `cangca-erp` **chỉ khi Duy duyệt**.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S8-AC1 | Cùng dữ liệu seed, đăng nhập Chủ | So màn Tổng quan cũ và mới | Các KPI, 8 đơn gần nhất, 20 lô, cảnh báo cận hạn, 8 dòng sổ kho **trùng số** | |
| S8-AC2 (giá vốn) | Đăng nhập Quản lý | Mở Kho & Lô | Không có cột giá vốn. Response `/api/dashboard/summary/` **không có key** giá vốn (kiểm trên tab Network/test BE sẵn có) | BR-PQ-15, bất biến #1 |
| S8-AC3 | Đăng nhập Chủ | Mở Kho & Lô | Có cột giá vốn/kg | |
| S8-AC4 (lỗi) | API dashboard trả 500 | Mở Tổng quan | Thông báo "Không tải được dữ liệu, thử lại" + nút Thử lại; không trắng trang | |
| S8-AC5 (quyền) | Đăng nhập `giao1` | Gõ URL `/overview` | Như S7-AC3 | BR-PQ-15 |
| S8-AC6 | Build xong | Kiểm `erp-console/` | `legacy/` đã xoá; `firebase.json` trỏ `out`; README ghi lệnh build/deploy | |

## S9 — Khoá field trạng thái, tồn, giá vốn trong Django Admin · Must · BE
**Là** Chủ vựa, **tôi muốn** Admin không còn là cửa sau để đổi trạng thái, tồn, giá vốn, **để** mọi thay đổi đi qua console và có AuditLog.
Bối cảnh: Duy chốt Q3: giữ Admin làm cứu hộ/cấu hình, khoá chỉ đọc với người **không phải superuser**. Superuser vẫn sửa được (đường cứu hộ) nhưng phải có dấu vết (BR-PQ-05).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S9-AC1 | Quản lý (staff, không superuser) vào Admin lô | Mở form sửa lô | Các field khoá ở S3 hiện chỉ đọc; POST form có giá trị khác thì DB không đổi | BR-PQ-14 |
| S9-AC2 | Như trên với phiếu giao, hàng hoàn, kiểm kê, phiếu nhập, phiếu hoàn, đơn, giao dịch thanh toán | Mở form | Field trạng thái/người phụ trách/số tiền chỉ đọc | BR-PQ-14 |
| S9-AC3 | Superuser sửa `landed_unit_cost` của lô trong Admin | Lưu | Lưu được, **ghi AuditLog** `admin_edit` với giá trị trước → sau | BR-PQ-05 |
| S9-AC4 (quyền) | Chủ **không** là superuser | Sửa `status` lô trong Admin | Không sửa được (chỉ đọc) | BR-PQ-14 |
| S9-AC5 | Chủ | Sửa mặt hàng, giá niêm yết, nhà cung cấp trong Admin | Vẫn sửa được (master data không khoá) | decisions 2026-09-10 |

---

## 1B. Tài khoản & phân quyền (Duy bổ sung 2026-09-24: "làm luôn vụ phân quyền và tài khoản")

Đưa lên từ Đợt 3, làm **ngay sau nền** và **trước** các màn nghiệp vụ. Mỗi nhân viên dùng tài khoản riêng, Chủ tự quản lý người và quyền trên console, không còn dùng chung `admin`. Mã S41, S42 giữ nguyên (đã chuyển chỗ); S46, S47 là story mới.

BR mới đề xuất:
- **BR-PQ-17**: không ai tự đổi Group của chính mình. Chỉ người thuộc `chu` hoặc superuser mới gán/bỏ Group `chu`, và mới được đặt lại mật khẩu hoặc cho nghỉ một tài khoản thuộc `chu`.
- **BR-PQ-18**: hệ thống luôn còn **ít nhất một** tài khoản đang làm thuộc `chu`.

Mọi thay đổi tài khoản/quyền ghi AuditLog: tạo, sửa hồ sơ, đổi nhóm (trước → sau), cho nghỉ, cho làm lại, đặt lại mật khẩu, tự đổi mật khẩu. Nội dung log **không bao giờ** chứa mật khẩu.

## S41 — Chủ tạo tài khoản nhân viên và gán nhóm · Must · BE+FE · cả hai thiết bị
**Là** Chủ vựa, **tôi muốn** tạo tài khoản riêng cho từng nhân viên (kèm SĐT), gán hoặc bỏ một hay nhiều nhóm, **để** mỗi người đăng nhập bằng tài khoản của mình với đúng quyền, không ai dùng chung `admin`.
Bối cảnh: UC-23, A26, BR-PQ-01/03/08/09, quyền `accounts.manage_staff`. Nhóm cộng dồn: `chu`, `quan_ly`, `nv_kho`, `nv_giao`. Tài khoản gồm `User` + `StaffProfile` (đã có). Đổi nhóm **không hồi tố** chứng từ cũ (BR-PQ-03).

**Contract**
```
GET   /api/staff/?is_active=true
200 [{"id": 12, "username": "giao1", "display_name": "Anh Tư", "phone": "0908111222",
      "groups": ["nv_giao"], "is_active": true, "last_login": "2026-09-24T05:10:00+07:00",
      "available_actions": ["edit", "set_groups", "reset_password", "deactivate"]}]
POST  /api/staff/
{"username": "giao4", "display_name": "Anh Năm", "phone": "0909333444", "groups": ["nv_giao"], "password": "tạm-ít-nhất-8-ký-tự"}
201 {"id": 20, "username": "giao4", "groups": ["nv_giao"], "is_active": true}
PATCH /api/staff/12/          {"display_name": "Anh Tư Giao", "phone": "0908111333"}     → 200
PUT   /api/staff/12/groups/   {"groups": ["nv_giao", "nv_kho"]}                           // thay toàn bộ tập nhóm
200 {"groups": ["nv_giao", "nv_kho"], "added": ["nv_kho"], "removed": []}
400 {"code": "BR-PQ-08", "detail": "Số điện thoại là bắt buộc."}
400 {"code": "BR-PQ-08", "detail": "Tên đăng nhập đã tồn tại."}
400 {"code": "BR-PQ-17", "detail": "Không thể tự đổi nhóm của chính mình."}
403 {"code": "BR-PQ-17", "detail": "Chỉ Chủ mới gán hoặc bỏ nhóm Chủ."}
400 {"code": "BR-PQ-18", "detail": "Phải còn ít nhất một Chủ đang làm."}
403 thiếu accounts.manage_staff
```
Không có `DELETE` (BR-PQ-02). Tên nhóm lạ → 400.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S41-AC1 | Chủ | Tạo `giao4` nhóm `nv_giao` | 201, có StaffProfile với SĐT; `giao4` đăng nhập console, `/api/auth/me/` có `home="my-deliveries"`; 1 AuditLog `staff_create` (không có mật khẩu) | BR-PQ-08 |
| S41-AC2 | `kho1` thuộc `nv_kho` | Chủ đặt nhóm `["nv_kho","nv_giao"]` | `/api/auth/me/` của `kho1` có cả hai nhóm; AuditLog `staff_groups_change` ghi trước → sau; chứng từ cũ của `kho1` không đổi | BR-PQ-03/09 |
| S41-AC3 | `kho1` thuộc `nv_kho` + `nv_giao` | Chủ bỏ `nv_giao` | `/api/auth/me/` của `kho1` chỉ còn `nv_kho`; console của `kho1` không còn menu "Việc giao của tôi" (xem S47-AC2) | BR-PQ-09 |
| S41-AC4 (lỗi) | — | Tạo thiếu SĐT, username trùng, mật khẩu < 8 ký tự, hoặc nhóm không tồn tại | 400, không tạo gì | BR-PQ-08 |
| S41-AC5 (chống tự nâng quyền) | Chủ `loc` | `PUT /api/staff/{loc}/groups/` bất kỳ giá trị nào | 400 `BR-PQ-17`, nhóm không đổi | BR-PQ-17 |
| S41-AC6 (chống tự nâng quyền) | Tài khoản `ql9` được cấp `manage_staff` nhưng **không** thuộc `chu`, không superuser | Gán `chu` cho `kho1`, hoặc bỏ `chu` của `loc` | 403 `BR-PQ-17` | BR-PQ-17 |
| S41-AC7 (lỗi) | `loc` là Chủ duy nhất; `chu2` là superuser | `chu2` bỏ nhóm `chu` của `loc` | 400 `BR-PQ-18` | BR-PQ-18 |
| S41-AC8 | Superuser đổi nhóm của `kho1` trong **Django Admin** | Lưu | Vẫn ghi AuditLog `staff_groups_change` (trước → sau); nhân viên không phải superuser không mở được trang sửa User/Group trong Admin | BR-PQ-04, BR-PQ-17 |
| S41-AC9 (quyền) | Quản lý, NV kho, NV giao | `GET/POST /api/staff/`, `PUT .../groups/` | 403; menu "Nhân sự" không hiện | BR-PQ-08 |
| S41-AC10 (bảo mật) | Chủ | `GET /api/staff/` | Không có key `password`, hash hay token nào trong JSON | |

## S42 — Chủ cho nhân viên nghỉ và đặt lại mật khẩu · Must · BE+FE · cả hai thiết bị
**Là** Chủ vựa, **tôi muốn** cho nhân viên nghỉ để họ mất quyền ngay trên mọi máy, và đặt lại mật khẩu khi ai quên, **để** người đã nghỉ hay điện thoại bị mất không còn vào được hệ thống.
Bối cảnh: UC-23, BR-PQ-01/02, Q5 mặc định. Cho nghỉ = `is_active=False` **và xoá token**. Không xoá tài khoản (BR-PQ-02), chứng từ cũ vẫn giữ tên người đó. Người đã nghỉ thì không hiện trong danh sách chọn NV giao (S18) và không đăng nhập được (S6-AC5).

**Contract**
```
POST /api/staff/12/deactivate/      {}                        → 200 {"is_active": false}
POST /api/staff/12/reactivate/      {}                        → 200 {"is_active": true}
POST /api/staff/12/reset-password/  {"new_password": "…"}     → 200 {}      // xoá token cũ của người đó
400 {"code": "BR-GH-08", "detail": "Còn 2 phiếu Đang giao (PG-…, PG-…) — xử lý trước khi cho nghỉ."}
400 {"code": "BR-PQ-18", "detail": "Không thể cho nghỉ Chủ cuối cùng."}
400 {"code": "BR-PQ-17", "detail": "Không thể tự cho nghỉ chính mình."}
403 {"code": "BR-PQ-17", "detail": "Chỉ Chủ mới thao tác trên tài khoản Chủ."}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S42-AC1 | `giao1` đang đăng nhập trên điện thoại | Chủ cho nghỉ | Lần gọi API kế tiếp của `giao1` → 401; token bị xoá; không có trong `GET /api/delivery/couriers/`; chứng từ cũ vẫn hiện tên `giao1`; AuditLog `staff_deactivate` | BR-PQ-01, Q5 |
| S42-AC2 | `giao1` đã nghỉ | Chủ cho làm lại | `giao1` đăng nhập được bằng mật khẩu cũ; AuditLog `staff_reactivate` | BR-PQ-01 |
| S42-AC3 | `kho1` quên mật khẩu, đang đăng nhập ở máy kho | Chủ đặt lại | Máy kho → 401 ở lần gọi kế tiếp; mật khẩu mới đăng nhập được; AuditLog `staff_password_reset` **không** chứa mật khẩu | BR-PQ-04 |
| S42-AC4 (lỗi) | `giao1` còn phiếu DELIVERING | Cho nghỉ | 400, liệt kê phiếu, `giao1` vẫn đang làm | BR-GH-08 |
| S42-AC5 (lỗi) | `loc` là Chủ duy nhất đang làm; superuser thao tác | Cho nghỉ `loc` | 400 `BR-PQ-18` | BR-PQ-18 |
| S42-AC6 (lỗi) | Chủ `loc` | Cho nghỉ chính `loc` | 400 `BR-PQ-17` | BR-PQ-17 |
| S42-AC7 (chống tự nâng quyền) | `ql9` có `manage_staff`, không thuộc `chu` | Đặt lại mật khẩu hoặc cho nghỉ `loc` | 403 `BR-PQ-17` | BR-PQ-17 |
| S42-AC8 (lỗi) | — | `DELETE /api/staff/12/` | 405 | BR-PQ-02 |
| S42-AC9 (quyền) | Quản lý / NV kho / NV giao | Mọi action trên | 403 | BR-PQ-08 |

## S46 — Đăng xuất thu hồi phiên, tự đổi mật khẩu · Must · BE+FE · cả hai thiết bị
**Là** nhân viên nội bộ, **tôi muốn** đăng xuất để máy đó không còn dùng được tài khoản tôi, và tự đổi mật khẩu, **để** điện thoại cho mượn hay dùng chung không lộ quyền của tôi.
Bối cảnh: Duy bổ sung. Đăng nhập riêng từng người dùng `POST /api/auth/token/` (S7). DRF hiện cấp **một token cho mỗi người**, nên đăng xuất ở một máy là **đăng xuất mọi máy** của người đó (PA, câu hỏi C8). Mật khẩu kiểm theo `AUTH_PASSWORD_VALIDATORS` (tối thiểu 8 ký tự).

**Contract**
```
POST /api/auth/logout/            {}                                              → 204   // xoá token đang dùng
POST /api/auth/change-password/   {"old_password": "…", "new_password": "…"}
200 {"token": "<token mới>"}       // token cũ bị xoá; máy khác của người này → 401
400 {"code": "AUTH_OLD_PASSWORD", "detail": "Mật khẩu hiện tại không đúng."}
400 {"code": "AUTH_WEAK_PASSWORD", "detail": "Mật khẩu mới phải có ít nhất 8 ký tự và không quá giống tên đăng nhập."}
401 chưa đăng nhập
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S46-AC1 | `giao1` đăng nhập trên điện thoại | Bấm Đăng xuất | 204; token bị xoá; gọi lại API bằng token đó → 401; console về màn đăng nhập, xoá nháp và lịch sử trợ lý trên máy | BR-PQ-12 |
| S46-AC2 | `kho1` đăng nhập ở 2 máy | Đổi mật khẩu ở máy A | Máy A nhận token mới, vẫn làm tiếp; máy B → 401 ở lần gọi kế tiếp; AuditLog `password_change_self` không chứa mật khẩu | BR-PQ-04 |
| S46-AC3 (lỗi) | — | Sai mật khẩu hiện tại, hoặc mật khẩu mới 6 ký tự | 400 đúng `code`; token cũ **vẫn** dùng được | |
| S46-AC4 (quyền) | Không có token | `POST /api/auth/change-password/` | 401 | |
| S46-AC5 (quyền) | `kho1` | Gửi thêm `"username": "loc"` vào change-password | Chỉ đổi mật khẩu của `kho1`; field lạ bị từ chối 400 | BR-PQ-17 |

## S47 — Màn "Quyền của tôi" và ẩn/hiện theo quyền thật · Must · BE+FE · cả hai thiết bị
**Là** nhân viên nội bộ, **tôi muốn** xem mình thuộc nhóm nào, được làm những việc gì, có xem giá vốn không, **để** biết vì sao thấy hay không thấy một nút, và hỏi Chủ đúng việc.
Bối cảnh: Duy bổ sung. Mở rộng `/api/auth/me/` (S6) thêm nhãn tiếng Việt. Menu và nút đã ẩn/hiện theo `me` (S7) và `available_actions`. Story này thêm màn xem, và đảm bảo quyền **đổi thì console đổi theo mà không cần đăng nhập lại**. Backend vẫn là lớp chặn (BR-PQ-12).

**Contract (mở rộng S6)**
```
GET /api/auth/me/
200 {..., "group_labels": [{"code": "nv_kho", "label": "Nhân viên kho"}, {"code": "nv_giao", "label": "Nhân viên giao"}],
     "capabilities": [{"code": "inventory.approve_returntostock", "label": "Duyệt hàng hoàn"}]}   // chỉ quyền Tầng 2 (Meta.permissions tuỳ biến)
```
Console gọi lại `me` khi mở app, khi đổi tab trở lại sau ≥ 5 phút, và khi nhận 403.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S47-AC1 | Quản lý | Mở "Quyền của tôi" | Hiện tên, SĐT, nhóm "Quản lý", danh sách việc: Mở bán lô, Huỷ đơn đã thanh toán, Tạo phiếu hoàn, Duyệt hàng hoàn, Duyệt kiểm kê (khớp spec §1.5); dòng "Xem giá vốn: Không"; nút Đổi mật khẩu, Đăng xuất (S46) | BR-PQ-09 |
| S47-AC2 | `kho1` đang mở console | Chủ thêm `nv_giao` cho `kho1` (S41); `kho1` quay lại tab sau 5 phút hoặc tải lại | Menu "Việc giao của tôi" xuất hiện, không cần đăng nhập lại | BR-PQ-09 |
| S47-AC3 (quyền) | Chủ bỏ `quan_ly` của `ql1` trong lúc `ql1` đang mở một đơn có nút "Huỷ đơn" | `ql1` bấm Huỷ | API 403; console tải lại `me`, ẩn nút, báo "Quyền của bạn vừa thay đổi" | BR-PQ-12 |
| S47-AC4 (giá vốn) | Người không có `view_costprice` | `GET /api/auth/me/` | `capabilities` không có `view_costprice`; `can_view_cost=false` | BR-PQ-15 |
| S47-AC5 | Tài khoản superuser `admin` không thuộc Group nào | Đăng nhập console | Màn "chưa được phân quyền" (S7-AC5), không thấy menu nghiệp vụ | Ghi chú vận hành |

## 1C. Đơn & tiền

## S48 — Tài khoản & mật khẩu "làm đàng hoàng" · Must · BE+FE · cả hai thiết bị
> Bổ sung theo Duy 2026-09-24: "tài khoản mật khẩu làm đàng hoàng luôn". Làm trước mốc deploy 1.

**Là** nhân viên được Chủ cấp tài khoản, **tôi muốn** tự đặt mật khẩu riêng ngay lần đầu và nhập mật khẩu dễ, không sai, **để** chỉ mình tôi biết mật khẩu của mình.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S48-AC1 | Chủ vừa tạo tài khoản `giao4` (S41) hoặc đặt lại mật khẩu (S42) | `giao4` đăng nhập bằng mật khẩu tạm | `/api/auth/me/` có `must_change_password: true`; ERP chỉ mở màn "Đặt mật khẩu mới", mọi API nghiệp vụ khác trả 403 `code: AUTH_MUST_CHANGE_PASSWORD` cho tới khi đổi xong | BR-PQ-19 (mới) |
| S48-AC2 | `giao4` ở màn "Đặt mật khẩu mới" | nhập mật khẩu cũ + mới + nhập lại | đổi xong (dùng S46 change-password) → `must_change_password: false`, vào màn home bình thường | |
| S48-AC3 (lỗi) | form đổi/tạo mật khẩu | "Nhập lại" khác "Mật khẩu mới" | FE báo "Hai mật khẩu không khớp", không gọi API | |
| S48-AC4 | mọi ô mật khẩu (đăng nhập, tạo, đặt lại, đổi) | bấm biểu tượng mắt | hiện/ẩn mật khẩu; nút ≥44px; có gợi ý quy tắc (≥8 ký tự, không toàn số, không quá phổ biến) hiển thị trước khi gửi | |
| S48-AC5 (bảo mật) | form tạo tài khoản đang có nháp (useDraft) | tải lại trang / bị văng 401 | nháp giữ mọi ô TRỪ mật khẩu (không bao giờ ghi mật khẩu vào localStorage); form nhắc "nhập lại mật khẩu" | |
| S48-AC6 (quyền) | người tự đổi mật khẩu trong lúc `must_change_password` | — | tự đổi thành công KHÔNG bật lại cờ; Chủ đặt lại mật khẩu → cờ bật lại; superuser `admin` không bị ép | |
| S48-AC7 | dữ liệu cũ | chạy migration | nhân viên đã có sẵn: `must_change_password=false` (không ép người đang dùng) | |

Ghi chú kỹ thuật: cờ `StaffProfile.must_change_password` (migration mới, default False; S41 create và S42 reset-password đặt True). Chặn API bằng permission/middleware chung, trừ `/api/auth/me/`, `/api/auth/change-password/`, `/api/auth/logout/`.

---

## S10 — Danh sách và chi tiết đơn · Must · BE+FE · cả hai thiết bị
**Là** Chủ vựa / Quản lý / NV kho, **tôi muốn** lọc, tìm và mở chi tiết một đơn với đủ tiền, giao hàng, hoàn tiền, **để** trả lời khách và xử lý mà không phải hỏi ai.
Bối cảnh: UC-02, A1. Thay list 8 đơn của dashboard.

**Contract**
```
GET /api/sales/orders/?status=BOOKED,PAID&date_from=2026-09-01&date_to=2026-09-24&q=0901&page=1
200 {"count": 42, "next": "...", "previous": null, "results": [
  {"id": 101, "code": "DH-260924-0012", "status": "BOOKED", "status_label": "Giữ chỗ",
   "customer_name": "Chị Hoa", "customer_phone": "0901234567", "total_amount": "540000",
   "created_at": "2026-09-24T06:10:00+07:00", "reserved_until": "2026-09-24T06:40:00+07:00",
   "delivery_status": null, "needs_attention": false}]}

GET /api/sales/orders/101/
200 {"id": 101, "code": "...", "status": "PROCESSING", "customer": {"name": "Chị Hoa", "phone": "0901234567", "address": "12 Lê Lợi, Vũng Tàu"},
  "lines": [{"no": 1, "item_code": "TOM-SU-1", "item_name": "Tôm sú loại 1", "qty_kg": "2.000", "unit_price": "270000", "discount": "0", "line_total": "540000"}],
  "allocations": [{"line_no": 1, "batch_id": "TOM-SU-1-260920-AB12C", "qty_kg": "2.000", "unit_cost": "180000"}],
  "invoice": {"id": 55, "code": "HD-...", "issued_at": "..."} ,
  "payments": [{"id": 88, "bank_txn_id": "FT2626712345", "amount": "540000", "match_status": "MATCHED", "received_at": "..."}],
  "delivery": {"id": 31, "code": "PG-...", "status": "PREPARING", "assigned_to": {"id": 12, "display_name": "Anh Tư", "phone": "0908..."}, "failed_attempts": 0},
  "refunds": [{"id": 5, "amount": "540000", "status": "PENDING", "bank_txn_ref": ""}],
  "available_actions": ["cancel", "create_refund"]}
404 ngoài phạm vi (S5)
```
`allocations[].unit_cost` **không có key** với người thiếu `view_costprice`. `q` tìm theo mã đơn hoặc SĐT (khớp một phần).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S10-AC1 | 45 đơn đủ trạng thái | Lọc `status=BOOKED`, ngày 24/09 | Chỉ đơn Giữ chỗ ngày 24/09, 20 dòng/trang, có phân trang | UC-02 |
| S10-AC2 | Đơn có SĐT 0901234567 | Tìm `q=0901234` | Có đơn đó | UC-02 |
| S10-AC3 (giá vốn) | Quản lý / NV kho | `GET /api/sales/orders/101/` | Có `allocations` với `batch_id`, `qty_kg`; **không có key `unit_cost`** | BR-BH-06, BR-PQ-15 |
| S10-AC4 | Chủ | Như trên | Có `unit_cost` | BR-BH-06 |
| S10-AC5 | Đơn BOOKED | Mở chi tiết trên console | Hiện đồng hồ đếm ngược giữ chỗ còn lại (phút:giây) theo `reserved_until` | BR-BH-03 |
| S10-AC6 (quyền) | Tài khoản không có `view_salesorder` | Gọi list | 403; menu "Đơn & tiền" không hiện | BR-PQ-12 |
| S10-AC7 (mobile) | 360×640 | Mở list & chi tiết | Mỗi đơn là một thẻ; chi tiết một cột; không cuộn ngang | Q4 |

## S11 — Chủ xác nhận thanh toán thủ công cho đơn Giữ chỗ · Must · BE+FE · ưu tiên điện thoại
**Là** Chủ vựa, **tôi muốn** xác nhận "đã nhận tiền" ngay trên đơn đang Giữ chỗ khi webhook không về, **để** đơn khách đã trả không bị tự huỷ.
Bối cảnh: UC-03, A2 (action đang gắn sai vào hoá đơn), BR-TT-08 (mới). Chạy **cùng service với webhook** (đủ tiền / thiếu tiền / đơn đã tự huỷ / trùng mã GD). Action cũ `POST /api/sales/invoices/{id}/confirm-payment` **bị gỡ**.

**Contract**
```
POST /api/sales/orders/101/confirm-payment
{"bank_txn_id": "FT2626712345", "amount": "540000"}     // amount mặc định = tổng đơn nếu bỏ trống
200 {"result": "PAID", "duplicate": false, "order_status": "PROCESSING", "invoice_id": 55, "delivery_note_code": "PG-260924-0007"}
200 {"result": "UNDERPAID", "duplicate": false, "order_status": "BOOKED", "paid_total": "300000", "missing": "240000"}
200 {"result": "ORPHAN", "duplicate": false, "order_status": "AUTO_CANCELLED"}
200 {... kết quả lần đầu ..., "duplicate": true}            // trùng bank_txn_id
400 {"code": "BR-TT-08", "detail": "Thiếu mã giao dịch ngân hàng."}
400 {"code": "BR-TT-08", "detail": "Đơn không ở trạng thái Giữ chỗ/Tự huỷ."}
403 thiếu sales.confirm_payment_manual
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S11-AC1 | Đơn BOOKED 540.000đ, Chủ | Xác nhận `FT001`, 540.000 | `PAID`: có hoá đơn, trừ kho thật theo lô đã giữ, đơn PROCESSING, sinh phiếu giao PREPARING, giao dịch `source=MANUAL`, AuditLog actor = Chủ | BR-TT-07/08, BR-BH-06 |
| S11-AC2 | Như trên | Xác nhận 300.000 | `UNDERPAID`, đơn vẫn BOOKED, giao dịch UNDERPAID vào hàng chờ (S12) | BR-TT-04 |
| S11-AC3 (lỗi) | Đơn đã AUTO_CANCELLED | Xác nhận | `ORPHAN`, đơn **không** khôi phục, kho không đổi, giao dịch vào hàng chờ | BR-TT-05 |
| S11-AC4 (lỗi) | Đã xác nhận `FT001` | Gửi lại y hệt (mạng chậm, bấm 2 lần) | `duplicate: true`, chỉ **1** giao dịch, **1** hoá đơn | BR-TT-03 |
| S11-AC5 (lỗi) | Webhook đã ghi `FT001` cho đơn | Chủ xác nhận tay `FT001` | `duplicate: true`, không xử lý lần hai | BR-TT-03 |
| S11-AC6 (lỗi) | — | Bỏ trống `bank_txn_id` hoặc `amount` ≤ 0 | 400 | BR-TT-08 |
| S11-AC7 (quyền) | Quản lý | Gọi endpoint | 403, không đổi gì; FE không hiện nút (`available_actions` không có `confirm_payment`) | BR-TT-07 |
| S11-AC8 | — | `POST /api/sales/invoices/{id}/confirm-payment` | 404/405 (đã gỡ) | A2 |

## S12 — Hàng chờ thanh toán lệch: xem, gắn đơn, xác nhận khi khách đã bù · Must · BE+FE
**Là** Chủ vựa, **tôi muốn** thấy mọi khoản tiền lệch ở một chỗ và đóng từng khoản bằng một cách xử lý có ghi lại, **để** không khoản nào bị treo mà không ai biết.
Bối cảnh: UC-04, A3, BR-TT-09 (mới), Q9 mặc định. **Schema:** thêm vào `PaymentTransaction`: `resolution_status` (OPEN/RESOLVED), `resolution` (ATTACHED/CONFIRMED/REFUNDED), `resolved_by`, `resolved_at`, `resolution_note` + migration. Lý do: BR-TT-09. Nhánh **hoàn tiền** ở S13.

**Contract**
```
GET /api/sales/payments/?resolution_status=OPEN
200 {"count": 3, "results": [
  {"id": 88, "bank_txn_id": "FT...", "amount": "300000", "received_at": "...", "match_status": "UNDERPAID",
   "order": {"id": 101, "code": "DH-...", "status": "BOOKED", "total_amount": "540000", "paid_total": "300000"},
   "resolution_status": "OPEN", "available_actions": ["confirm_order", "refund"]}]}

POST /api/sales/payments/88/resolve
{"action": "ATTACH_TO_ORDER", "order_id": 101, "note": "Khách ghi sai nội dung CK"}
{"action": "CONFIRM_ORDER", "note": "Khách đã chuyển bù FT..."}
200 {"payment_id": 88, "resolution_status": "RESOLVED", "resolution": "CONFIRMED", "order_status": "PROCESSING"}
400 {"code": "BR-TT-05", "detail": "Đơn đã tự huỷ, chỉ còn cách hoàn tiền."}
400 {"code": "BR-TT-09", "detail": "Tổng tiền đã nhận 300.000đ < tổng đơn 540.000đ."}
403 thiếu sales.confirm_payment_manual
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S12-AC1 | Có 1 UNDERPAID, 1 ORPHAN, 1 UNMATCHED, 1 MATCHED | Chủ mở hàng chờ | Thấy 3 dòng (không có MATCHED), mỗi dòng có loại lệch, số tiền, đơn liên quan | BR-TT-09 |
| S12-AC2 | UNMATCHED 540.000đ; đơn 101 BOOKED 540.000đ | `ATTACH_TO_ORDER` đơn 101 | Đơn → PROCESSING như S11-AC1; giao dịch RESOLVED/ATTACHED, ghi người, lúc, ghi chú, AuditLog | BR-TT-09 |
| S12-AC3 | Đơn 101 BOOKED 540.000đ có 2 giao dịch UNDERPAID 300.000 + 240.000 | `CONFIRM_ORDER` trên một giao dịch | Đơn → PROCESSING; **cả hai** giao dịch RESOLVED/CONFIRMED | BR-TT-04, Q9 |
| S12-AC4 (lỗi) | Chỉ có 300.000/540.000 | `CONFIRM_ORDER` | 400 `BR-TT-09`, không đổi gì | BR-TT-09 |
| S12-AC5 (lỗi) | Đơn đã AUTO_CANCELLED trong lúc chờ | `CONFIRM_ORDER` hoặc `ATTACH_TO_ORDER` | 400 `BR-TT-05`, đơn không khôi phục | BR-TT-05 |
| S12-AC6 (lỗi) | Giao dịch đã RESOLVED | `resolve` lần nữa | 400 | BR-TT-09 |
| S12-AC7 (quyền) | Quản lý / NV kho | `GET ?resolution_status=OPEN` hoặc `resolve` | 403; menu con "Hàng chờ thanh toán" không hiện | BR-TT-07 |

## S13 — Hoàn tiền cho khoản tiền không có hoá đơn · Must · BE+FE
**Là** Chủ vựa, **tôi muốn** lập phiếu hoàn cho khoản tiền về sau khi đơn đã tự huỷ (hoặc về thiếu mà khách không bù), **để** tiền rời túi có sổ và có mã GD đối chiếu.
Bối cảnh: UC-04 E2, Q9 mặc định. **Schema:** `Refund.sales_invoice` thành nullable, thêm `Refund.payment_transaction` (nullable), ràng buộc **đúng một trong hai** + migration. Lý do: Q9. Xác nhận/thất bại dùng chung S16. Phiếu hoàn gắn giao dịch được xác nhận thì giao dịch tự sang RESOLVED/REFUNDED.

**Contract**
```
POST /api/sales/refunds/create
{"payment_transaction": 88, "amount": "300000", "reason": "Tiền về sau khi đơn tự huỷ", "request_id": "6f1c…uuid"}
201 {"id": 9, "status": "PENDING", "amount": "300000", "payment_transaction": 88, "sales_invoice": null}
400 {"code": "BR-HT-04", "detail": "Vượt số tiền còn được hoàn: tối đa 300.000đ."}
400 {"code": "BR-HT-01", "detail": "Chỉ gửi một trong hai: sales_invoice hoặc payment_transaction."}
403
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S13-AC1 | Giao dịch ORPHAN 300.000đ, Chủ | Tạo phiếu hoàn 300.000 | 201 PENDING, AuditLog; giao dịch vẫn OPEN cho tới khi xác nhận | BR-HT-08, BR-TT-09 |
| S13-AC2 | Như trên | Chủ xác nhận phiếu (S16) với mã GD | Phiếu REFUNDED; giao dịch RESOLVED/REFUNDED | BR-TT-09, BR-HT-03 |
| S13-AC3 (lỗi) | Giao dịch 300.000 đã có phiếu 200.000 (không Thất bại) | Tạo thêm 150.000 | 400 `BR-HT-04`, nêu còn tối đa 100.000 | BR-HT-04 |
| S13-AC4 (lỗi) | — | Gửi cả `sales_invoice` và `payment_transaction` | 400 | |
| S13-AC5 (lãi lỗ) | Phiếu hoàn gắn giao dịch (không hoá đơn) đã xác nhận trong tháng 9 | `GET /api/reports/period/?year=2026&month=9` | Khoản này **không** trừ vào doanh thu/lãi kỳ (chưa từng ghi doanh thu) | BR-BC-03, BR-TT-06 |
| S13-AC6 (quyền) | Quản lý (có `create_refund` nhưng không có `confirm_payment_manual`) | Tạo phiếu hoàn gắn `payment_transaction` | 403 (hàng chờ lệch là việc của Chủ) | BR-TT-09 |

## S14 — Huỷ đơn đã thanh toán theo trạng thái phiếu giao · Must · BE+FE
**Là** Chủ vựa / Quản lý, **tôi muốn** huỷ đơn đã thanh toán với lý do rõ ràng, chỉ khi hàng chưa rời tay người giao, **để** kho đúng và NV giao không đi giao đơn đã huỷ.
Bối cảnh: UC-05, A4, BR-GH-07 (mới), Q8 mặc định (huỷ toàn phần; sau giao thất bại thì **không** hoàn kho, kho cộng lại chỉ qua duyệt hàng hoàn). **Schema:** thêm trạng thái `CANCELLED` ("Đã huỷ theo đơn") cho `DeliveryNote` + migration.

**Contract**
```
POST /api/sales/orders/101/cancel
{"reason_code": "CUSTOMER_CHANGED_MIND", "note": ""}   // CUSTOMER_CHANGED_MIND | DAMAGED_WHEN_PACKING | GIVE_UP_AFTER_FAILED | OTHER (OTHER bắt buộc note)
200 {"order_status": "CANCELLED", "stock_restored": true, "delivery_status": "CANCELLED", "suggest_refund_amount": "540000", "invoice_id": 55}
400 {"code": "BR-GH-07", "detail": "Phiếu giao đang Đang giao — báo giao thất bại trước khi huỷ."}
400 {"code": "BR-GH-05", "detail": "Đơn đã giao hoàn tất — chỉ còn cách lập phiếu hoàn."}
400 {"code": "BR-LO-05", "detail": "Lô TOM-… đã chốt, không hoàn kho được."}
403 thiếu sales.cancel_paid_order
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S14-AC1 | Đơn PROCESSING, phiếu giao PREPARING hoặc READY | Quản lý huỷ, lý do "khách đổi ý" | Đơn CANCELLED; kho cộng lại **đúng lô gốc** theo bảng phân bổ (ledger `CANCEL_RESTORE`); phiếu giao CANCELLED; AuditLog có lý do | BR-HT-05, BR-GH-07 |
| S14-AC2 | Như AC1, phiếu gán `giao1` | `giao1` mở "Việc giao của tôi" | Phiếu không còn trong danh sách mặc định | BR-GH-07 |
| S14-AC3 | Phiếu giao FAILED | Huỷ với `GIVE_UP_AFTER_FAILED` | Đơn CANCELLED, `stock_restored=false`, **tồn lô không đổi** | Q8b, BR-HV-02 |
| S14-AC4 (lỗi) | Phiếu DELIVERING | Huỷ | 400 `BR-GH-07`, không đổi gì | BR-GH-07 |
| S14-AC5 (lỗi) | Phiếu COMPLETED | Huỷ | 400 `BR-GH-05` | BR-GH-05 |
| S14-AC6 (lỗi) | `reason_code=OTHER`, `note` rỗng | Huỷ | 400 | |
| S14-AC7 | Huỷ thành công | Console | Hiện ngay nút "Tạo phiếu hoàn toàn phần" điền sẵn `suggest_refund_amount` (mở S15) | UC-05 |
| S14-AC8 (quyền) | NV kho | Gọi cancel | 403 | BR-HT-07 |

## S15 — Tạo phiếu hoàn từ đơn, chống tạo trùng · Must · BE+FE
**Là** Chủ vựa / Quản lý, **tôi muốn** lập phiếu hoàn (toàn phần hoặc một phần) từ đơn, và bấm hai lần cũng chỉ ra một phiếu, **để** nợ khách được ghi đúng một lần.
Bối cảnh: UC-06, A5, Q12 mặc định (backend chặn trùng). **Schema:** `Refund.request_id` (UUID, unique, nullable) + migration. Lý do: Q12. FE sinh `request_id` khi mở form, gửi lại y nguyên nếu thử lại.

**Contract**
```
POST /api/sales/refunds/create
{"sales_invoice": 55, "amount": "540000", "is_partial": false, "reason": "Huỷ đơn — khách đổi ý", "request_id": "b2e0…uuid"}
201 {"id": 5, "status": "PENDING", "amount": "540000", "sales_invoice": 55}
200 {"id": 5, ..., "duplicate": true}          // cùng request_id
400 {"code": "BR-HT-04", "detail": "Vượt số đã thu: còn được hoàn tối đa 240.000đ."}
400 {"code": "BR-HT-04", "detail": "Số tiền hoàn phải lớn hơn 0."}
403
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S15-AC1 | Hoá đơn 540.000đ, chưa hoàn | Quản lý tạo 540.000 toàn phần | 201 PENDING, AuditLog; phiếu vào danh sách "Chờ Chủ chuyển khoản" (S16) | BR-HT-01/08 |
| S15-AC2 (lỗi) | Đã có phiếu 300.000 PENDING | Tạo 300.000 | 400, nêu còn tối đa 240.000 | BR-HT-04 |
| S15-AC3 | Đã có phiếu 300.000 **FAILED** | Tạo 540.000 | 201 (phiếu Thất bại không tính) | BR-HT-04 |
| S15-AC4 (trùng) | Vừa tạo với `request_id=R` | Gửi lại cùng `R` | 200 `duplicate: true`, vẫn **1** phiếu | Q12 |
| S15-AC5 (lỗi) | — | `amount` = 0 hoặc âm | 400 | BR-HT-04 |
| S15-AC6 (quyền) | NV kho | Tạo | 403 | BR-HT-07 |

## S16 — Phiếu hoàn chờ chuyển: xác nhận, báo thất bại, thử lại · Must · BE+FE · ưu tiên điện thoại
**Là** Chủ vựa, **tôi muốn** xem các phiếu hoàn đang chờ mình chuyển khoản, nhập mã GD sau khi chuyển, hoặc báo thất bại rồi thử lại, **để** mọi khoản tiền rời túi đối chiếu được với sao kê.
Bối cảnh: UC-07, A6, A7, BR-HT-09 (mới), Q13 (chỉ hiện SĐT, không lưu STK).

**Contract**
```
GET /api/sales/refunds/?status=PENDING,FAILED
200 {"results": [{"id": 5, "amount": "540000", "status": "PENDING", "order_code": "DH-...", "customer_name": "Chị Hoa",
  "customer_phone": "0901234567", "source_bank_txn_id": "FT...", "created_by": "ql1", "created_at": "...", "failure_reason": "",
  "available_actions": ["confirm", "mark_failed"]}]}
POST /api/sales/refunds/5/confirm      {"bank_txn_ref": "FT2626799999"}   → 200 {"status": "REFUNDED", "confirmed_at": "..."}
POST /api/sales/refunds/5/mark-failed  {"reason": "Sai số tài khoản"}      → 200 {"status": "FAILED"}
POST /api/sales/refunds/5/retry        {}                                  → 200 {"status": "PENDING"}
400 {"code": "BR-HT-03", "detail": "Bắt buộc nhập mã giao dịch hoàn."}
400 {"code": "BR-HT-09", "detail": "Phiếu đã hoàn, không đổi trạng thái được."}
403 thiếu sales.confirm_refund
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S16-AC1 | Phiếu PENDING | Chủ xác nhận với mã GD | REFUNDED, lưu người/giờ xác nhận, AuditLog | BR-HT-03, BR-PQ-05 |
| S16-AC2 (lãi lỗ) | Phiếu hoá đơn tháng 8, xác nhận 02/09 | Báo cáo kỳ tháng 9 | Khoản hoàn trừ vào **tháng 9** | BR-BC-03 |
| S16-AC3 | Phiếu PENDING | `mark-failed` kèm lý do → rồi `retry` | FAILED (lưu lý do) → PENDING; mỗi bước 1 AuditLog | BR-HT-09 |
| S16-AC4 (lỗi) | — | `confirm` không có `bank_txn_ref` | 400 `BR-HT-03` | BR-HT-03 |
| S16-AC5 (lỗi) | Phiếu REFUNDED | `confirm` / `mark-failed` / `retry` | 400 `BR-HT-09` | BR-HT-09 |
| S16-AC6 (lỗi) | Phiếu FAILED; trong lúc đó đã có phiếu khác lấp đầy số còn hoàn | `retry` | 400 `BR-HT-04` | BR-HT-04 |
| S16-AC7 (quyền) | Quản lý | Gọi 3 action | 403; FE không hiện nút | BR-HT-07 |
| S16-AC8 (mobile) | 360×640 | Mở danh sách | SĐT khách là link `tel:`; mã GD gõ được, nút Xác nhận ≥ 44 px | Q4 |

---

## 1D. Giao hàng

## S17 — Bảng điều phối giao hàng · Must · BE+FE · cả hai thiết bị
**Là** Quản lý / Chủ vựa / NV kho, **tôi muốn** thấy mọi phiếu giao theo trạng thái, ai đang giao, phiếu nào cần quyết định, **để** điều phối trong ngày.
Bối cảnh: UC-08 bước 1, UC-10 bước 3, A8. Ngưỡng "cần quyết định" = `DELIVERY_FAILED_ALERT_THRESHOLD` (settings/env, mặc định **2**, BR-GH-04). Phiếu CANCELLED ẩn mặc định.

**Contract**
```
GET /api/delivery/notes/?status=PREPARING,READY,DELIVERING,FAILED&assigned_to=none|me|12&needs_decision=1&page=1
200 {"count": 9, "results": [
  {"id": 31, "code": "PG-260924-0007", "status": "FAILED", "status_label": "Giao thất bại",
   "order": {"id": 101, "code": "DH-..."}, "customer_name": "Chị Hoa", "customer_phone": "0901234567",
   "address": "12 Lê Lợi, Vũng Tàu", "paid_at": "...", "assigned_to": {"id": 12, "display_name": "Anh Tư", "phone": "0908..."},
   "failed_attempts": 2, "last_failure_reason": "CUSTOMER_ABSENT", "needs_decision": true,
   "available_actions": ["assign", "set_status:DELIVERING", "cancel_order"]}]}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S17-AC1 | Phiếu đủ 5 trạng thái + 1 CANCELLED | Quản lý mở Giao hàng | Nhóm theo Soạn hàng → Chờ lấy → Đang giao → Thất bại → Hoàn tất (hôm nay); không có CANCELLED | UC-08 |
| S17-AC2 | Phiếu FAILED, `failed_attempts=2` | Mở bảng | `needs_decision=true`, dòng gắn cờ "Cần quyết định: giao lại hay huỷ" | BR-GH-04 |
| S17-AC3 | Đổi env ngưỡng = 3 | Phiếu `failed_attempts=2` | `needs_decision=false` | Bất biến #7 |
| S17-AC4 | — | Lọc `assigned_to=none` | Chỉ phiếu chưa gán | |
| S17-AC5 (quyền) | `giao1` chỉ thuộc `nv_giao` | `GET /api/delivery/notes/` | Chỉ phiếu của `giao1`; menu "Giao hàng (điều phối)" không hiện | BR-GH-06, BR-PQ-12 |

## S18 — Gán hoặc đổi NV giao · Must · BE+FE
**Là** Quản lý / Chủ vựa / NV kho, **tôi muốn** chọn một hoặc nhiều phiếu và gán cho một NV giao đang làm, **để** người đó thấy việc ngay trên điện thoại.
Bối cảnh: UC-08, A10, BR-GH-08 (mới), Q7 mặc định (Chủ, Quản lý, NV kho đều gán được). NV giao thường có quyền sửa phiếu (để cập nhật trạng thái), nên cần **quyền Tầng 2 mới `delivery.assign_deliverynote`** (Meta.permissions + migration + data migration gán cho `chu`, `quan_ly`, `nv_kho`).

**Contract**
```
GET /api/delivery/couriers/
200 [{"id": 12, "display_name": "Anh Tư", "phone": "0908111222"}]      // is_active và thuộc nv_giao
POST /api/delivery/notes/assign
{"note_ids": [31, 32], "assignee_id": 12}
200 {"updated": [31, 32]}
400 {"code": "BR-GH-08", "detail": "Phiếu PG-… đang Đang giao, không đổi người được.", "note_ids": [32]}   // cả lô không đổi
400 {"code": "BR-GH-08", "detail": "Người được gán không thuộc nhóm NV giao hoặc đã nghỉ."}
403 thiếu delivery.assign_deliverynote
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S18-AC1 | Phiếu 31 (PREPARING, chưa gán), 32 (READY, gán `giao2`) | NV kho gán cả hai cho `giao1` | 200; hai phiếu gán `giao1`; 2 AuditLog ghi "từ (trống)/giao2 → giao1" | BR-GH-08, BR-PQ-04 |
| S18-AC2 | Phiếu FAILED (hẹn lại) | Đổi người | Cho phép | UC-08 2a |
| S18-AC3 (lỗi) | Chọn 31 (READY) và 33 (DELIVERING) | Gán | 400, chỉ ra 33; **31 cũng không đổi** (tất cả hoặc không) | BR-GH-08 |
| S18-AC4 (lỗi) | `giao3` đã nghỉ; `kho2` không thuộc `nv_giao` | `GET couriers` / gán cho họ | Không có trong danh sách / 400 | BR-GH-08, BR-PQ-01 |
| S18-AC5 (lỗi) | Chưa ai thuộc `nv_giao` | Mở hộp gán | "Chưa có NV giao nào đang làm. Chủ vào Nhân sự để gán nhóm." | UC-08 E3 |
| S18-AC6 (quyền) | `giao1` | Gọi `assign` | 403 | BR-GH-06 |

## S19 — NV kho soạn hàng và đánh dấu "Đã đóng gói" · Must · BE+FE · ưu tiên điện thoại
**Là** NV kho, **tôi muốn** xem các phiếu cần soạn với dòng hàng, số kg, lô cần lấy, rồi bấm "Đã đóng gói", **để** NV giao biết hàng đã sẵn sàng.
Bối cảnh: UC-09 bước 1, BR-GH-03. Mọi chuyển trạng thái giao gửi kèm `from_status` để bấm lại khi mạng rớt không nhảy hai bước (UC-09 E2). Luật "ai được chuyển bước nào" nằm ở BE.

**Contract**
```
GET /api/delivery/notes/31/
200 {..., "lines": [{"item_name": "Tôm sú loại 1", "qty_kg": "2.000", "batch_id": "TOM-SU-1-260920-AB12C"}], "available_actions": ["set_status:READY"]}
POST /api/delivery/notes/31/status
{"to_status": "READY", "from_status": "PREPARING"}
200 {"status": "READY", "already": false}
200 {"status": "READY", "already": true}          // đã ở READY: gửi lại vô hại
400 {"code": "BR-GH-05", "detail": "Không chuyển được từ Soạn hàng sang Hoàn tất."}
400 {"code": "STALE_STATE", "detail": "Phiếu đang ở Đang giao, tải lại để xem.", "current_status": "DELIVERING"}
400 {"code": "BR-GH-07", "detail": "Đơn đã huỷ, không giao."}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S19-AC1 | Phiếu PREPARING | NV kho bấm "Đã đóng gói" | READY, AuditLog | BR-GH-03 |
| S19-AC2 (lỗi mạng) | Lần 1 đã ghi nhưng FE không nhận phản hồi | Bấm lại | `already: true`, trạng thái vẫn READY, **không** sinh AuditLog thứ hai | UC-09 E2 |
| S19-AC3 (lỗi) | PREPARING | `to_status=COMPLETED` | 400 | BR-GH-05 |
| S19-AC4 (lỗi) | Phiếu CANCELLED | Bất kỳ `to_status` | 400 `BR-GH-07`; FE hiện "Đơn đã huỷ, không giao" | UC-09 E3 |
| S19-AC5 (giá vốn) | NV kho | Chi tiết phiếu giao | Không có key giá vốn/đơn giá mua nào | BR-PQ-15 |
| S19-AC6 (quyền) | `giao1` chỉ thuộc `nv_giao` | PREPARING → READY trên phiếu của mình | 403 (soạn hàng là việc NV kho) | UC-09 |

## S20 — "Việc giao của tôi" trên điện thoại · Must · FE · chỉ điện thoại
**Là** NV giao, **tôi muốn** mở điện thoại là thấy phiếu mình phải giao, gọi khách một chạm, bấm "Nhận hàng", "Khách đã nhận", **để** làm việc một tay ngoài đường.
Bối cảnh: UC-09 bước 2–3, Q4. Dùng `GET /api/delivery/notes/` (đã lọc theo người, S17) và `POST .../status` (S19). Không có số tiền trên màn này.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S20-AC1 | `giao1` có 2 phiếu READY, 1 DELIVERING | Mở màn 360×640 | Thẻ theo thứ tự: Đang giao trước, rồi Chờ lấy; mỗi thẻ có tên khách, địa chỉ, SĐT `tel:`, dòng hàng + kg | BR-GH-06 |
| S20-AC2 | Phiếu READY | "Nhận hàng đi giao" | DELIVERING (gửi `from_status=READY`) | UC-09 |
| S20-AC3 | Phiếu DELIVERING | "Khách đã nhận" | Hộp xác nhận "Không hoàn tác được" → đồng ý → COMPLETED; huỷ hộp thì không gọi API | BR-GH-05 |
| S20-AC4 (lỗi mạng) | Mất mạng lúc bấm | Bấm lại khi có mạng | Hiện "Đã ghi" nếu `already: true`; không có trạng thái nhảy hai bước | UC-09 E2 |
| S20-AC5 (quyền) | `giao1` | Mở URL chi tiết phiếu của `giao2` | API 404 → màn "Không tìm thấy phiếu" | BR-PQ-12 |
| S20-AC6 (quyền) | `giao1` | Xem thẻ phiếu | Không có ô sửa địa chỉ/dòng hàng; không hiện giá bán hay tổng tiền | BR-GH-06 |
| S20-AC7 | — | Kiểm nút thao tác | Cao ≥ 44 px, nằm trong 1/3 dưới màn hình | Q4 |

## S21 — Báo giao thất bại kèm lý do · Must · BE+FE · ưu tiên điện thoại
**Là** NV giao, **tôi muốn** báo giao thất bại với lý do chọn nhanh, **để** Quản lý biết mà quyết định giao lại hay huỷ.
Bối cảnh: UC-10, BR-GH-04. **Schema:** `DeliveryNote.last_failure_reason` (choices) + migration để bảng điều phối lọc/hiện. Lý do: UC-10. Giao lại = `status` FAILED → DELIVERING (S19).

**Contract**
```
POST /api/delivery/notes/31/fail
{"reason_code": "CUSTOMER_ABSENT", "note": "Gọi 3 lần không nghe", "from_status": "DELIVERING"}
   // CUSTOMER_ABSENT | CUSTOMER_REFUSED | WRONG_ADDRESS | OTHER (OTHER bắt buộc note)
200 {"status": "FAILED", "failed_attempts": 2, "needs_decision": true, "already": false}
400 {"code": "BR-GH-04", "detail": "Chỉ báo thất bại khi phiếu Đang giao."}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S21-AC1 | Phiếu DELIVERING, `failed_attempts=0` | `giao1` báo thất bại "không gặp khách" | FAILED, `failed_attempts=1`, lưu lý do, AuditLog | BR-GH-04 |
| S21-AC2 | Lần thứ 2 | Báo thất bại | `needs_decision=true`; phiếu có cờ ở bảng điều phối (S17) và khối "Cần chú ý" (S24) | BR-GH-04, Q11 |
| S21-AC3 | Phiếu FAILED | Quản lý chuyển về DELIVERING (hẹn lại) | Cho phép, `failed_attempts` giữ nguyên | UC-10 3a |
| S21-AC4 (lỗi) | Phiếu READY | `fail` | 400 | UC-10 E1 |
| S21-AC5 (lỗi mạng) | Đã FAILED do lần gửi trước | Gửi lại cùng `from_status=DELIVERING` | `already: true`, `failed_attempts` **không** tăng thêm | UC-09 E2 |
| S21-AC6 (quyền) | `giao2` | `fail` trên phiếu của `giao1` | 404 | BR-GH-06 |

## S22 — Ghi hàng mang về kho · Must · BE+FE · ưu tiên điện thoại
**Là** NV giao / NV kho, **tôi muốn** ghi số kg mang về kho theo đúng lô của đơn, với số điền sẵn, **để** hàng chờ duyệt mà không cộng kho sai.
Bối cảnh: UC-11, A11, BR-HV-01/02, BR-HV-05 (mới). Đi qua service `return_to_warehouse`. **Mỗi lô sinh một phiếu hàng hoàn** (model hiện 1 phiếu = 1 lô). `POST /api/inventory/returns/` chung **bị đóng** (405), chỉ còn đường này. Chặn trùng nhờ BR-HV-05 (tổng mang về không vượt số đã xuất), theo Q12 mặc định.

**Contract**
```
GET /api/delivery/notes/31/return-draft
200 {"left_at": "2026-09-24T08:05:00+07:00", "lines": [
  {"batch_id": "TOM-SU-1-260920-AB12C", "item_name": "Tôm sú loại 1", "qty_shipped": "2.000", "qty_already_returned": "0.000", "qty_max": "2.000"}]}
POST /api/delivery/notes/31/return-to-warehouse
{"left_at": "2026-09-24T08:05:00+07:00", "returned_at": "2026-09-24T11:40:00+07:00",
 "lines": [{"batch_id": "TOM-SU-1-260920-AB12C", "qty_kg": "2.000"}]}
201 {"returns": [{"id": 9, "batch_id": "TOM-…", "qty_kg": "2.000", "status": "DRAFT"}]}
400 {"code": "BR-HV-01", "detail": "Lô … không thuộc đơn này."}
400 {"code": "BR-HV-05", "detail": "Lô … chỉ còn mang về tối đa 0,500 kg."}
400 {"code": "BR-HV-02", "detail": "Chỉ ghi hàng mang về khi phiếu Đang giao hoặc Giao thất bại."}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S22-AC1 | Phiếu FAILED của `giao1`, đơn 2 kg từ lô L | `giao1` xác nhận số điền sẵn | 1 phiếu hàng hoàn DRAFT, `created_by=giao1`, **tồn lô L không đổi**, AuditLog | BR-HV-01/02, BR-PQ-16 |
| S22-AC2 (lỗi) | — | Gửi `batch_id` không thuộc đơn | 400 `BR-HV-01` | BR-HV-01 |
| S22-AC3 (lỗi/trùng) | Đã ghi 2 kg lô L cho phiếu này | Ghi thêm 0,5 kg | 400 `BR-HV-05` | BR-HV-05 |
| S22-AC4 (lỗi) | Phiếu COMPLETED hoặc READY | Ghi | 400 | BR-HV-02 |
| S22-AC5 (lỗi) | `returned_at` < `left_at` | Ghi | 400 | |
| S22-AC6 (quyền) | `giao2` | Ghi trên phiếu của `giao1` | 404 | BR-GH-06 |
| S22-AC7 (quyền) | Bất kỳ ai | `POST /api/inventory/returns/` | 405 | BR-PQ-14 |

## S23 — Duyệt hàng hoàn: tái nhập hay huỷ bỏ · Must · BE+FE
**Là** Quản lý / Chủ vựa, **tôi muốn** xem hàng mang về, số giờ ngoài chuỗi lạnh, rồi chọn tái nhập hay huỷ bỏ, **để** kho và lỗ lô đúng.
Bối cảnh: UC-12, A12, BR-HV-02/04, Q14 mặc định (chưa có ngưỡng thì **chỉ hiện số giờ**, không đề xuất sẵn).

**Contract**
```
GET /api/inventory/returns/?status=DRAFT
200 {"results": [{"id": 9, "delivery_note_code": "PG-…", "order_code": "DH-…", "batch_id": "TOM-…", "batch_status": "SELLING",
  "qty_kg": "2.000", "hours_out_of_cold_chain": "3.6", "created_by": "giao1", "created_at": "...",
  "allowed_decisions": ["RESTOCK", "WRITE_OFF"], "available_actions": ["approve"]}]}
POST /api/inventory/returns/9/approve   {"decision": "RESTOCK"}
200 {"status": "APPROVED", "decision": "RESTOCK"}
400 {"code": "BR-HV-04", "detail": "Lô gốc đã chốt — chỉ được Huỷ bỏ."}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S23-AC1 | Phiếu DRAFT 2 kg lô L (SELLING) | Quản lý chọn Tái nhập | Tồn L +2 kg (ledger `RETURN_RESTOCK`), phiếu APPROVED, `approved_by` = Quản lý, AuditLog | BR-HV-02 |
| S23-AC2 | Như trên | Chọn Huỷ bỏ | Tồn L không đổi, 2 kg ghi lỗ vào lô L | BR-HV-02, BR-BC-04 |
| S23-AC3 (lỗi) | Lô L CLOSED | Chọn Tái nhập | 400 `BR-HV-04`; `allowed_decisions` chỉ có WRITE_OFF | BR-HV-04 |
| S23-AC4 (lỗi) | — | Không gửi `decision`, hoặc phiếu đã APPROVED | 400 | UC-12 E2/E3 |
| S23-AC5 | Rời kho 08:05, về 11:41 | Mở phiếu | Hiện "3,6 giờ ngoài kho lạnh"; không có quyết định nào chọn sẵn | Q14 |
| S23-AC6 (quyền) | NV kho / NV giao | `approve` | 403 | BR-HV-02 |

## S24 — Khối "Cần chú ý" và huy hiệu menu · Should · BE+FE
**Là** Chủ vựa / Quản lý, **tôi muốn** thấy ngay số việc đang chờ mình, **để** không có gì bị bỏ quên.
Bối cảnh: Q11 và Q20 mặc định (nhắc trên console, không SMS). Mỗi con số chỉ trả khi người hỏi có quyền xử lý mục đó. Mục của Đợt 2 (kiểm kê chờ duyệt, lô quá hạn còn tồn) đã có dữ liệu từ model sẵn có và S2.
Why Should: không có khối này thì mọi việc vẫn làm được từ từng màn; khối này giúp không bỏ sót.

**Contract**
```
GET /api/dashboard/attention/
200 {"payments_open": 2, "refunds_pending": 1, "deliveries_need_decision": 1, "returns_pending": 3,
     "reconciliations_pending": 0, "batches_expired_with_stock": 1}
```
Key nào người hỏi không có quyền thì **không có trong JSON**.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S24-AC1 | Dữ liệu seed có đủ loại | Chủ gọi | Đủ 6 key, số khớp với các danh sách lọc tương ứng | Q20 |
| S24-AC2 (quyền) | Quản lý | Gọi | Không có `payments_open`, `refunds_pending`, `batches_expired_with_stock` | BR-TT-07, BR-HT-07 |
| S24-AC3 | Có số > 0 | Console | Huy hiệu số trên menu tương ứng; bấm dòng trong khối "Cần chú ý" mở danh sách đã lọc | Q11 |
| S24-AC4 (lỗi) | API lỗi | Mở Tổng quan | Khối hiện "Chưa tải được", phần còn lại của Tổng quan vẫn hiện | |
| S24-AC5 (quyền) | `giao1` | Gọi | 403 | BR-PQ-12 |

---

# ĐỢT 2 — Lô, mua hàng, chi phí mua, kiểm kê, báo cáo

## 2A. Vòng đời lô

## S25 — Danh sách lô và Mở bán (publish) · Must · BE+FE · cả hai thiết bị
**Là** Chủ vựa / Quản lý, **tôi muốn** lọc lô Nháp, kiểm tra và bấm Mở bán, với cảnh báo khi mặt hàng chưa có giá, **để** hàng lên Shop đúng lúc.
Bối cảnh: UC-13, A13, Q15b mặc định (thiếu giá chỉ **cảnh báo**). Lô quá hạn không publish được (BR-LO-02).

**Contract**
```
GET /api/inventory/batches/?status=DRAFT&item=TOM-SU-1&page=1
200 {"results": [{"id": 70, "batch_id": "TOM-…", "item_code": "TOM-SU-1", "item_name": "…", "status": "DRAFT",
  "received_date": "2026-09-24", "expiry_date": "2026-12-23", "qty_available": "20.000", "qty_reserved": "0.000",
  "has_active_price": false, "landed_unit_cost": "180000", "available_actions": ["publish"]}]}
POST /api/inventory/batches/70/publish   {}
200 {"status": "SELLING"}
400 {"code": "BR-LO-02", "detail": "Lô đã quá hạn, không mở bán được."}
```
`landed_unit_cost`, `purchase_rate` không có key với người thiếu `view_costprice`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S25-AC1 | Lô DRAFT còn hạn | Quản lý bấm Mở bán | SELLING, AuditLog; Shop thấy tồn tăng | BR-MH-05 |
| S25-AC2 | `has_active_price=false` | Bấm Mở bán | Console hiện "Mặt hàng chưa có giá niêm yết — Shop sẽ chưa bán được. Vẫn mở bán?"; đồng ý → publish thành công | Q15b |
| S25-AC3 (lỗi) | Lô DRAFT đã quá hạn | Publish | 400 `BR-LO-02` | BR-LO-02 |
| S25-AC4 (lỗi) | Lô SELLING | Publish | 400 | BR-MH-05 |
| S25-AC5 (giá vốn) | Quản lý | `GET /api/inventory/batches/` | Không có key `landed_unit_cost`, `purchase_rate` | BR-PQ-15 |
| S25-AC6 (quyền) | NV kho | Publish | 403 | BR-MH-05 |

## S26 — Chốt lô với bảng điều kiện · Must · BE+FE
**Là** Chủ vựa, **tôi muốn** thấy lô đã đủ điều kiện chốt chưa, thiếu gì, rồi chốt, **để** đông cứng lãi lỗ lô mà không chốt nhầm.
Bối cảnh: UC-14, A14. Bổ sung điều kiện **không còn đơn đang mở tham chiếu lô** (BR-LO-04). Điều kiện "đã kiểm kê" (BR-KK-05) hiện dạng **thông tin, không chặn** (PA, xem câu hỏi C4).

**Contract**
```
GET /api/inventory/batches/70/close-check
200 {"can_close": false, "conditions": [
  {"code": "STOCK_ZERO", "ok": false, "detail": "Còn 3,5 kg — kiểm kê hoặc huỷ lô quá hạn."},
  {"code": "PURCHASE_INVOICE", "ok": true, "detail": ""},
  {"code": "NO_OPEN_ORDERS", "ok": false, "detail": "Còn 2 đơn: DH-…, DH-…"},
  {"code": "RECONCILED", "ok": true, "blocking": false, "detail": "Kiểm kê gần nhất 20/09"}],
  "pnl_preview": {"revenue": "...", "gross_profit": "...", "provisional": true}}
POST /api/inventory/batches/70/close   {}
200 {"status": "CLOSED", "closed_at": "..."}
400 {"code": "BR-LO-04", "detail": "Còn 2 đơn đang mở tham chiếu lô."}
```
`pnl_preview` chỉ có khi `view_profitreport`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S26-AC1 | Lô tồn 0, có hoá đơn mua, không đơn mở | Chủ chốt, xác nhận "Không mở lại được" | CLOSED, AuditLog kèm giá vốn cuối | BR-LO-04/05 |
| S26-AC2 (lỗi) | Còn đơn BOOKED hoặc phiếu giao DELIVERING dùng lô | Chốt | 400 `BR-LO-04` | BR-LO-04 |
| S26-AC3 (lỗi) | Thiếu Purchase Invoice | Mở close-check | `PURCHASE_INVOICE.ok=false`, detail nêu mã phiếu nhập | BR-MH-04 |
| S26-AC4 (lỗi) | Lô đã CLOSED | Chốt | 400 | BR-LO-05 |
| S26-AC5 (quyền) | Quản lý | close-check / close | 403 | BR-LO-04 |

## S27 — Huỷ phần tồn còn lại của lô quá hạn · Must · BE+FE
**Là** Chủ vựa, **tôi muốn** huỷ số kg còn lại của lô quá hạn và ghi lỗ hết hạn vào lô, **để** kho về 0 và chốt được lô.
Bối cảnh: UC-15, A15, BR-LO-03, BR-LO-07 (mới), Q15a mặc định: dùng chung quyền `close_batch`.

**Contract**
```
POST /api/inventory/batches/70/write-off-expired
{"confirm_qty_kg": "3.500", "note": ""}
200 {"status": "CANCELLED", "written_off_kg": "3.500", "qty_available": "0.000"}
400 {"code": "BR-LO-07", "detail": "Lô chưa quá hạn."}
400 {"code": "BR-LO-07", "detail": "Số kg xác nhận 3,000 khác tồn hiện tại 3,500 — tải lại."}
400 {"code": "BR-LO-07", "detail": "Còn 1,000 kg đang giữ chỗ — xử lý đơn trước."}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S27-AC1 | Lô EXPIRED, tồn 3,5 kg, không giữ chỗ | Chủ huỷ, xác nhận 3,5 | Tồn 0 (ledger `WRITE_OFF`), CANCELLED, AuditLog; báo cáo lô có dòng "lỗ hết hạn" = 3,5 × giá vốn/kg | BR-LO-03/07 |
| S27-AC2 | Sau AC1 | close-check | `STOCK_ZERO.ok=true` | BR-LO-04 |
| S27-AC3 (lỗi) | Lô SELLING còn hạn | Huỷ | 400 | BR-LO-07 |
| S27-AC4 (lỗi) | `qty_reserved` > 0 | Huỷ | 400 | UC-15 E1 |
| S27-AC5 (lỗi) | `confirm_qty_kg` ≠ tồn | Huỷ | 400, không đổi gì | |
| S27-AC6 (quyền) | Quản lý | Huỷ | 403 | Q15a |

## 2B. Mua hàng & giá vốn

## S28 — Phiếu nhập lô tại cảng: tạo và sửa nháp có dòng · Must · BE+FE · ưu tiên điện thoại
**Là** NV kho đứng ở cảng, **tôi muốn** gõ phiếu nhập với từng dòng hàng ngay trên điện thoại, mạng rớt cũng không mất, **để** không phải ghi giấy rồi nhập lại.
Bối cảnh: UC-16, A18, BR-MH-02, Q6 mặc định (không offline; giữ nháp trên máy, báo "chưa gửi được"). Phạm vi: NV kho chỉ sửa phiếu **của mình, trong ngày tạo** (giờ VN), khi còn DRAFT.

**Contract**
```
POST /api/purchasing/receipts/
{"supplier": 3, "received_date": "2026-09-24", "note": "",
 "lines": [{"item": 11, "qty_kg": "20.000", "rate": "180000", "expiry_date": null}]}      // null = ngày nhập + hạn mặc định
201 {"id": 40, "code": "PN-…", "status": "DRAFT", "created_by": "kho1",
     "lines": [{"id": 1, "item": 11, "item_name": "…", "qty_kg": "20.000", "rate": "180000", "expiry_date": "2026-12-23"}],
     "available_actions": ["edit", "submit"]}
PATCH /api/purchasing/receipts/40/     (thay toàn bộ lines, cùng định dạng)
400 {"code": "BR-MH-02", "detail": "Hạn dùng không được sau ngày nhập + 90 ngày."}
400 {"code": "BR-MH-01", "detail": "Số kg và đơn giá phải lớn hơn 0."}
403 {"detail": "Chỉ sửa được phiếu của mình trong ngày."}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S28-AC1 | NV kho, 360×640 | Chọn NCC, thêm 3 dòng, Lưu nháp | 201 DRAFT, 3 dòng, `created_by=kho1`, hạn dùng mỗi dòng = ngày nhập + 90 | BR-MH-02, BR-PQ-16 |
| S28-AC2 | — | Dòng có `expiry_date` = ngày nhập + 60 | Lưu được | BR-MH-02 |
| S28-AC3 (lỗi) | — | `expiry_date` = ngày nhập + 91, hoặc `qty_kg`/`rate` ≤ 0 | 400 | BR-MH-02, UC-16 E4 |
| S28-AC4 (lỗi mạng) | Đang gõ 3 dòng, mất mạng khi Lưu | Bấm Lưu | Thông báo "Chưa gửi được — đã giữ trên máy"; tải lại trang vẫn còn 3 dòng; có mạng bấm Lưu lại → 201 | Q6 |
| S28-AC5 (quyền) | Phiếu DRAFT của `kho2` | `kho1` PATCH | 403 | spec §1.6 |
| S28-AC6 (quyền) | Phiếu của `kho1` tạo hôm qua | `kho1` PATCH | 403; Quản lý/Chủ PATCH được | spec §1.6 |
| S28-AC7 (quyền) | NV giao | `POST /api/purchasing/receipts/` | 403 | BR-PQ-12 |

## S29 — Ghi nhận phiếu nhập, sinh lô Nháp, không sinh trùng · Must · BE+FE
**Là** NV kho / Quản lý / Chủ vựa, **tôi muốn** bấm "Ghi nhận" để mỗi dòng thành một lô Nháp, **để** lô sẵn sàng mở bán mà không bị nhân đôi khi mạng chậm.
Bối cảnh: UC-16 bước 3, BR-MH-01, UC-16 E3.

**Contract**
```
POST /api/purchasing/receipts/40/submit   {}
200 {"status": "SUBMITTED", "batches": [{"id": 70, "batch_id": "TOM-…", "status": "DRAFT"}], "already": false}
200 {..., "already": true}                   // gọi lại khi đã SUBMITTED
400 {"code": "BR-MH-01", "detail": "Phiếu chưa có dòng hàng."}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S29-AC1 | Phiếu DRAFT 3 dòng | Ghi nhận | SUBMITTED, 3 lô DRAFT, ledger `RECEIPT` mỗi lô, `landed_unit_cost` = đơn giá mua, AuditLog | BR-MH-01, BR-GV-01 |
| S29-AC2 (trùng) | Đã SUBMITTED | Gọi submit lần nữa (hoặc 2 request song song) | `already: true`; vẫn **3** lô | UC-16 E3 |
| S29-AC3 (lỗi) | Phiếu 0 dòng | Submit | 400 | BR-MH-01 |
| S29-AC4 | Đã SUBMITTED | PATCH phiếu | 400 (không sửa phiếu đã ghi nhận) | BR-PQ-14 |
| S29-AC5 (quyền) | `kho1` submit phiếu của `kho2` | Submit | 403 | spec §1.6 |

## S30 — Ẩn giá mua với người không có quyền · Must · BE
**Là** Chủ vựa, **tôi muốn** NV kho không xem được đơn giá phiếu người khác và Quản lý không xem được tổng tiền hoá đơn mua, **để** giá mua không bị suy ra.
Bối cảnh: A18, A19, BR-MH-06, Q10 mặc định. Không có màn mới; áp cho mọi endpoint mua hàng.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S30-AC1 (giá vốn) | Phiếu của `kho2` | `kho1` `GET /api/purchasing/receipts/{id}/` | Dòng có mặt hàng, kg; **không có key `rate`** | BR-MH-06 |
| S30-AC2 | Phiếu của chính `kho1` | `kho1` GET | Có `rate` | BR-MH-06 |
| S30-AC3 (giá vốn) | Quản lý (không `view_costprice`) | `GET /api/purchasing/invoices/` và chi tiết | **Không có key `amount`** | Q10, BR-PQ-15 |
| S30-AC4 (giá vốn) | Quản lý | `GET /api/purchasing/receipts/?…` | Không có key `rate`, không có tổng tiền phiếu | BR-PQ-15 |
| S30-AC5 | Chủ | Mọi endpoint trên | Có đủ `rate`, `amount` | |
| S30-AC6 (quyền) | NV giao | `GET /api/purchasing/receipts/` | 403 | BR-PQ-12 |

## S31 — Ghi hoá đơn mua · Must · BE+FE
**Là** Chủ vựa, **tôi muốn** ghi hoá đơn mua ngay từ phiếu nhập với số tiền điền sẵn, **để** lô thoả điều kiện chốt.
Bối cảnh: UC-17, BR-MH-03/04. Lệch tổng dòng: cho lưu nhưng cảnh báo (PA của BA). Trùng: một phiếu nhập chỉ một hoá đơn **đang hiệu lực** (PA, xem câu hỏi C5).

**Contract**
```
POST /api/purchasing/invoices/
{"receipt": 40, "amount": "3600000", "is_paid": true, "invoice_date": "2026-09-24", "note": ""}
201 {"id": 12, "receipt": 40, "amount": "3600000", "warning": null}
201 {"id": 12, ..., "warning": "Số tiền 3.500.000đ lệch tổng dòng 3.600.000đ."}
400 {"code": "BR-MH-03", "detail": "Phiếu nhập PN-… đã có hoá đơn mua."}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S31-AC1 | Phiếu SUBMITTED tổng dòng 3.600.000 | Chủ bấm "Ghi hoá đơn mua" | Form điền sẵn 3.600.000, đã trả = có; lưu 201; `created_by` = Chủ | BR-MH-03, BR-PQ-16 |
| S31-AC2 | — | Lưu 3.500.000 | 201 kèm `warning`; console hiện cảnh báo | UC-17 E2 |
| S31-AC3 (lỗi) | Phiếu đã có hoá đơn | Tạo thêm | 400 | UC-17 E1 |
| S31-AC4 | Sau AC1 | close-check lô của phiếu | `PURCHASE_INVOICE.ok=true` | BR-MH-04 |
| S31-AC5 (quyền) | Quản lý | `POST /api/purchasing/invoices/` | 403 | spec §1.4 |

## S32 — Ghi chi phí mua có xem trước phân bổ, chống trùng · Must · BE+FE
**Là** Chủ vựa, **tôi muốn** nhập tiền đá, xe, bốc vác, chọn các lô, xem trước giá vốn/kg từng lô trước và sau, rồi ghi, **để** giá vốn đúng và không bị cộng hai lần.
Bối cảnh: UC-18, A20, BR-GV-01…04, Q12 mặc định (backend chặn trùng). **Schema:** `PurchaseCost.request_id` (UUID unique nullable) + migration.

**Contract**
```
POST /api/purchasing/costs/preview
{"cost_type": "ICE", "amount": "200000", "batch_ids": [70, 71], "allocation_method": "BY_QTY"}
200 {"allocations": [{"batch_id": "TOM-…", "qty_kg": "20.000", "allocated": "133333", "unit_cost_before": "180000", "unit_cost_after": "186667"},
                     {"batch_id": "MUC-…", "qty_kg": "10.000", "allocated": "66667", "unit_cost_before": "120000", "unit_cost_after": "126667"}]}
POST /api/purchasing/costs/
{..., "cost_date": "2026-09-24", "note": "", "request_id": "c9…uuid"}
201 {"id": 21, "allocations": [...]}      200 {..., "duplicate": true}
400 {"code": "BR-GV-02", "detail": "Lô … đã chốt, không nhận chi phí."}
400 {"code": "BR-GV-04", "detail": "Chưa chọn lô nào."}
```
Tổng `allocated` luôn bằng đúng `amount` (phần lẻ làm tròn dồn vào lô cuối).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S32-AC1 | 2 lô 20 kg + 10 kg | Preview 200.000 theo kg | 133.333 + 66.667 = 200.000; hiện giá vốn/kg trước → sau; **DB không đổi** | BR-GV-04 |
| S32-AC2 | Như trên | Ghi | `landed_unit_cost` 2 lô cập nhật, 1 AuditLog **mỗi lô** (trước → sau); giá vốn trên đơn đã bán trước đó **không đổi** | BR-GV-03, spec §5.2 |
| S32-AC3 (trùng) | Vừa ghi với `request_id=R` | Gửi lại `R` | `duplicate: true`, giá vốn không cộng lần hai | Q12 |
| S32-AC4 (lỗi) | Một lô CLOSED | Preview hoặc ghi | 400 `BR-GV-02` | BR-GV-02 |
| S32-AC5 (lỗi) | `batch_ids` rỗng hoặc `amount` ≤ 0 | Ghi | 400 | UC-18 E2 |
| S32-AC6 (quyền) | Quản lý | preview / ghi | 403; menu con "Chi phí mua" không hiện | BR-GV-03 |

## S33 — Điều chỉnh chi phí mua ghi sai bằng chứng từ âm · Should · BE+FE
**Là** Chủ vựa, **tôi muốn** sửa khoản chi phí ghi sai bằng một chứng từ điều chỉnh âm vào đúng các lô đó, **để** sửa sai mà không xoá chứng từ.
Bối cảnh: UC-18 E4, Q16 mặc định, BR-PQ-10. Why Should: tần suất thấp; tạm thời Chủ có thể nhờ superuser xử lý có log (S9).

**Contract**
```
POST /api/purchasing/costs/21/adjust
{"amount": "-50000", "note": "Ghi dư tiền đá", "request_id": "…"}
201 {"id": 22, "adjusts": 21, "allocations": [...]}
400 {"code": "BR-GV-02", "detail": "Lô … đã chốt."}
400 {"code": "BR-GV-03", "detail": "Điều chỉnh vượt số đã ghi: tối đa -200.000đ."}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S33-AC1 | Chi phí 21 = 200.000 phân cho 2 lô | Điều chỉnh -50.000 | Chứng từ 22 phân bổ âm **cùng tỉ lệ** vào đúng 2 lô; giá vốn giảm; AuditLog mỗi lô; chứng từ 21 giữ nguyên | BR-PQ-10, BR-GV-03 |
| S33-AC2 (lỗi) | Một lô đã chốt | Điều chỉnh | 400 | BR-GV-02 |
| S33-AC3 (lỗi) | — | Điều chỉnh -250.000 | 400 | |
| S33-AC4 (quyền) | Quản lý | Điều chỉnh | 403 | |

## 2C. Kiểm kê

## S34 — Nhập số kiểm kê · Must · BE+FE · ưu tiên điện thoại
**Là** NV kho, **tôi muốn** thấy danh sách lô đang có tồn và gõ số đếm thực tế từng lô, **để** Quản lý duyệt điều chỉnh.
Bối cảnh: UC-19, A21, BR-KK-01/04, Q17a mặc định (không hiện số sổ khi đang đếm). `system_qty` (có sẵn trong model) chụp **lúc gửi phiếu**, dùng cho BR-KK-07.

**Contract**
```
GET /api/inventory/reconciliations/count-sheet/
200 [{"batch": 70, "batch_id": "TOM-…", "item_name": "…", "warehouse": "Kho chính"}]    // không có số sổ
POST /api/inventory/reconciliations/
{"count_date": "2026-09-24", "note": "", "lines": [{"batch": 70, "counted_qty": "19.200", "reason": ""}]}
201 {"id": 15, "status": "DRAFT", "created_by": "kho1", "lines": [{"batch_id": "TOM-…", "counted_qty": "19.200"}]}
400 {"code": "BR-LO-05", "detail": "Lô … đã chốt, không kiểm kê."}
400 {"code": "BR-KK-04", "detail": "Lô … đếm dư so với sổ, bắt buộc ghi lý do."}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S34-AC1 | 3 lô có tồn (không lô chốt) | NV kho mở phiếu đếm | Thấy 3 lô, **không có** số sổ sách trên màn và trong JSON | Q17a |
| S34-AC2 | — | Gửi số đếm | 201 DRAFT, `created_by=kho1`, `system_qty` = tồn sổ lúc gửi; **tồn sổ chưa đổi** | BR-KK-01/02, BR-KK-07 |
| S34-AC3 (lỗi) | Số đếm > sổ, lý do rỗng | Gửi | 400 `BR-KK-04`; console đánh dấu dòng cần lý do | BR-KK-04 |
| S34-AC4 (lỗi) | Lô CLOSED | Gửi dòng lô đó | 400 | BR-LO-05 |
| S34-AC5 (quyền) | NV kho | `GET /api/inventory/reconciliations/15/` | Không có key `system_qty`, `difference_qty` | Q17a |
| S34-AC6 (quyền) | NV giao | Tạo phiếu | 403 | BR-PQ-12 |

Ghi chú: AC3 dùng số sổ để kiểm ở BE nhưng thông điệp **không** nêu số sổ.

## S35 — Duyệt kiểm kê · Must · BE+FE
**Là** Quản lý / Chủ vựa (khác người nhập), **tôi muốn** thấy số sổ lúc đếm, số đếm, chênh lệch, các phát sinh giữa lúc đếm và lúc duyệt, rồi duyệt, **để** tồn sổ về đúng thực tế.
Bối cảnh: UC-20, BR-KK-02/03, BR-KK-07 (mới), Q17b mặc định. Chênh lệch = `counted_qty − system_qty` (lúc đếm). Khi duyệt, tồn sổ **cộng/trừ đúng số chênh lệch** (không set bằng số đếm) để giữ các giao dịch phát sinh sau.

**Contract**
```
GET /api/inventory/reconciliations/15/
200 {"id": 15, "status": "DRAFT", "created_by": "kho1", "lines": [
  {"batch_id": "TOM-…", "system_qty": "20.000", "counted_qty": "19.200", "difference_qty": "-0.800", "reason": "",
   "movements_since_count": [{"type": "SALE", "qty": "-2.000", "at": "..."}], "loss_value": "144000"}],
  "available_actions": ["approve"]}
POST /api/inventory/reconciliations/15/approve   {}
200 {"status": "APPROVED"}
400 {"code": "BR-KK-02", "detail": "Không duyệt phiếu do chính mình nhập."}
```
`loss_value` chỉ có khi `view_costprice`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S35-AC1 | Phiếu `kho1`: sổ 20, đếm 19,2 | `ql1` duyệt | Tồn lô −0,8 (ledger `RECONCILE`), hao hụt 0,8 kg vào lô, APPROVED, AuditLog | BR-KK-03 |
| S35-AC2 | Sau lúc đếm có bán 2 kg (tồn sổ còn 18) | Duyệt | Chênh lệch vẫn −0,8 (theo lúc đếm); tồn sau duyệt = 17,2; phần "phát sinh sau khi đếm" hiện dòng bán 2 kg | BR-KK-07 |
| S35-AC3 (lỗi) | `ql1` tự nhập phiếu | `ql1` duyệt | 400 `BR-KK-02`; nút ẩn (`available_actions` rỗng) | BR-KK-02 |
| S35-AC4 (lỗi) | Phiếu đã APPROVED | Duyệt | 400 | |
| S35-AC5 (giá vốn) | Quản lý | GET chi tiết | Không có key `loss_value` | BR-PQ-15 |
| S35-AC6 (quyền) | NV kho | Duyệt | 403 | BR-KK-02 |

## 2D. Báo cáo lãi lỗ

## S36 — Báo cáo lãi lỗ: danh sách lô · Must · BE+FE · cả hai thiết bị
**Là** Chủ vựa, **tôi muốn** một bảng mọi lô với doanh thu, giá vốn, hao hụt, lãi gộp, biên, **để** biết lô nào lời lô nào lỗ mà không phải mở từng lô.
Bối cảnh: UC-21 tab Theo lô, A23, BR-BC-04/05.

**Contract**
```
GET /api/reports/batches/?status=SELLING,CLOSED&item=TOM-SU-1&received_from=2026-09-01&received_to=2026-09-24&page=1
200 {"count": 18, "results": [{"batch_id": "TOM-…", "item_name": "…", "status": "CLOSED", "provisional": false,
  "revenue": "7200000", "purchase_cost": "3600000", "allocated_costs": "200000", "shrinkage": "144000",
  "damaged_expired": "0", "gross_profit": "3256000", "margin_pct": "45.2"}]}
403 thiếu reports.view_profitreport
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S36-AC1 | Lô A CLOSED, lô B SELLING | Chủ mở tab Theo lô | Cả hai; B gắn nhãn "tạm tính" (`provisional=true`) | BR-BC-05 |
| S36-AC2 | — | Số của mỗi dòng | Trùng với `GET /api/reports/batch/{id}/` của lô đó | BR-BC-04 |
| S36-AC3 | Lọc mặt hàng + khoảng ngày nhập | Gọi | Chỉ lô khớp; phân trang 20 | |
| S36-AC4 (lỗi) | Không lô nào khớp | Gọi | Bảng rỗng với chữ "Không có lô nào trong bộ lọc này" | UC-21 E2 |
| S36-AC5 (quyền/giá vốn) | Quản lý | Gọi API | 403, **không có số nào về máy**; menu Báo cáo không hiện | BR-PQ-15, UC-21 E1 |

## S37 — Báo cáo lãi lỗ: chi tiết lô và theo kỳ · Must · FE · cả hai thiết bị
**Là** Chủ vựa, **tôi muốn** mở một lô để xem từng khoản và các đơn đã ăn vào lô, và xem lãi theo tháng, **để** đối chiếu với tiền thực nhận.
Bối cảnh: UC-21 bước 2–3, API có sẵn `GET /api/reports/batch/{batch_id}/`, `GET /api/reports/period/?year&month`. BR-BC-01…03. Ghi chú cố định trên tab kỳ: "Có thể lệch nhẹ với tổng theo lô khi lô chưa chốt" (spec §12.1).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S37-AC1 | Lô có 3 đơn | Mở chi tiết | Hiện từng khoản (doanh thu, giá mua, chi phí phân bổ, hao hụt, hỏng/hết hạn, lãi) và 3 đơn với kg | BR-BC-04 |
| S37-AC2 | Tháng 9 có doanh thu và 1 phiếu hoàn đã xác nhận | Chọn 09/2026 | Doanh thu, giá vốn, hoàn tiền trong kỳ, lãi; có dòng ghi chú lệch | BR-BC-01…03 |
| S37-AC3 (lỗi) | Tháng chưa có dữ liệu | Chọn | "Tháng này chưa có giao dịch" | UC-21 E2 |
| S37-AC4 (quyền) | Quản lý gõ URL `/reports/period` | Mở | "Không có quyền", **không gọi** API | BR-PQ-15 |
| S37-AC5 (mobile) | 360×640 | Mở chi tiết lô | Các khoản xếp dọc một cột, không cuộn ngang | Q4 |

---

# ĐỢT 3 — Danh mục & giá, nhật ký, Trợ lý AI
(Nhân sự S41, S42 đã chuyển lên mục 1B.)

## S38 — Mặt hàng và nhóm hàng · Should · BE+FE
**Là** Chủ vựa, **tôi muốn** xem và sửa mặt hàng (tên, nhóm, hạn dùng mặc định, ảnh, ẩn/hiện) trên console, **để** không phải vào Admin cho việc thường ngày.
Bối cảnh: UC-22, A24 (CRUD có sẵn). Why Should: Admin đang làm tốt việc này; console chỉ để tiện. Xoá mặt hàng đã có giao dịch bị chặn (BR-PQ-10). Ngừng bán = ẩn.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S38-AC1 | Chủ | Sửa tên và hạn dùng mặc định của mặt hàng | Lưu được; lô **đã sinh** không đổi hạn | BR-MH-02 |
| S38-AC2 (lỗi) | Mặt hàng đã có lô/đơn | `DELETE /api/catalog/items/{id}/` | 400 `BR-PQ-10` "Đã có giao dịch — hãy ẩn thay vì xoá" | BR-PQ-10 |
| S38-AC3 (quyền) | Quản lý / NV kho | Mở Danh mục | Chỉ xem, không có nút sửa; `PATCH` → 403 | spec §1.4 |

## S39 — Giá niêm yết theo hiệu lực, xem trước giá Shop hôm nay · Should · BE+FE
**Là** Chủ vựa, **tôi muốn** thêm giá mới có ngày hiệu lực (kể cả giá xả cận hạn) và thấy ngay Shop sẽ bán giá nào hôm nay, **để** đổi giá không sửa giá cũ.
Bối cảnh: UC-22, BR-DM-03, BR-LO-01. Không sửa/xoá dòng giá đã có hiệu lực, chỉ thêm dòng mới hoặc đặt `valid_upto`.

**Contract**
```
GET /api/catalog/items/11/price-preview/?date=2026-09-24
200 {"item_code": "TOM-SU-1", "date": "2026-09-24", "price": "270000", "source": {"item_price_id": 33, "valid_from": "2026-09-20", "valid_upto": null}, "discount_rule": null}
POST /api/catalog/item-prices/   {"item": 11, "price_list": 1, "rate": "240000", "valid_from": "2026-09-25", "valid_upto": "2026-09-30"}
400 {"code": "BR-DM-03", "detail": "Chồng lấn với giá 270.000đ hiệu lực từ 20/09."}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S39-AC1 | Giá 270.000 từ 20/09 không hạn | Thêm 240.000 từ 25/09–30/09 sau khi đặt `valid_upto` giá cũ 24/09 | Lưu được; preview 24/09 = 270.000, 26/09 = 240.000 | BR-DM-03 |
| S39-AC2 (lỗi) | Như trên chưa đặt `valid_upto` | Thêm giá chồng khoảng | 400 `BR-DM-03` | BR-DM-03 |
| S39-AC3 (lỗi) | Dòng giá đã có hiệu lực | `PATCH rate` | 400 `BR-PQ-14` | BR-LO-01 |
| S39-AC4 (quyền) | Quản lý | Thêm giá | 403 | spec §1.4 |

## S40 — Combo và ưu đãi · Could · FE
**Là** Chủ vựa, **tôi muốn** tạo combo và ưu đãi trên console, **để** chạy khuyến mãi không cần Admin.
Bối cảnh: UC-22, BR-DM-05/08, CRUD có sẵn (`catalog/bundle-lines`, `catalog/pricing-rules`). Why Could: tần suất thấp, Admin làm được; làm nếu còn thời gian trong đợt 3.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S40-AC1 | Chủ | Tạo combo 2 thành phần | Lưu; preview giá Shop (S39) hiện giá combo | BR-DM-05 |
| S40-AC2 (lỗi) | — | Thêm combo làm thành phần của combo | API 400 `BR-DM-05`, console hiện thông điệp | BR-DM-05 |
| S40-AC3 (lỗi) | Mặt hàng đã có 1 ưu đãi hiệu lực | Thêm ưu đãi thứ hai chồng thời gian | 400 `BR-DM-08` | BR-DM-08 |
| S40-AC4 (quyền) | Quản lý | Mở màn | Chỉ xem | spec §1.4 |

## S43 — Nhật ký hoạt động (AuditLog) · Should · BE+FE
**Là** Chủ vựa, **tôi muốn** tra ai làm gì, lúc nào, trên chứng từ nào, **để** đối chiếu khi có sai lệch.
Bối cảnh: UC-23, A27, BR-PQ-04/06. Chỉ đọc. Nếu log là thay đổi giá vốn thì chỉ người có `view_costprice` mới thấy giá trị trước/sau.

**Contract**
```
GET /api/audit-logs/?actor=12&action=close_batch&object_type=batch&object_id=70&date_from=…&date_to=…&page=1
200 {"count": 120, "results": [{"id": 999, "at": "...", "actor": "loc" | "Hệ thống", "action": "close_batch",
  "object_type": "batch", "object_repr": "TOM-…", "changes": {"landed_unit_cost": {"final": "186667"}}}]}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S43-AC1 | Có log từ S1–S42 | Chủ lọc theo lô 70 | Đủ các hành động trên lô theo thời gian giảm dần; log job hiện "Hệ thống" | BR-PQ-04 |
| S43-AC2 (lỗi) | — | `POST/PATCH/DELETE /api/audit-logs/…` | 405 | BR-PQ-06 |
| S43-AC3 (quyền) | Quản lý | `GET /api/audit-logs/` | 403 | UC-23 |

## S44 — Trợ lý AI chỉ đọc: hỏi đáp theo quyền, có giới hạn lượt · Must · BE
**Là** Chủ vựa / Quản lý / NV kho, **tôi muốn** hỏi bằng tiếng Việt ("hôm nay còn bao nhiêu tôm sú?", "đơn nào đang thất bại?") và nhận câu trả lời từ dữ liệu thật mà mình được xem, **để** không phải lục nhiều màn.
Bối cảnh: UC-24, Duy chốt Q2 (chỉ đọc, Claude thật, không gửi giá vốn nếu thiếu `view_costprice`, giới hạn lượt/ngày).
Thiết kế đề xuất:
- Django `POST /api/assistant/ask` gom **ảnh chụp dữ liệu** mà người hỏi được xem (tái dùng serializer đã lọc quyền: tồn theo lô, đơn gần đây, phiếu giao, cảnh báo). Có `view_costprice`/`view_profitreport` thì mới thêm giá vốn/lãi lỗ.
- **Không gửi SĐT, địa chỉ khách** cho bên thứ 3 (PA, câu hỏi C2).
- Gọi Claude **qua adapter FastAPI** (`POST /internal/ai/messages`, service token), theo nguyên tắc "bên thứ 3 luôn qua adapter" (decisions 2026-09-09). Key `ANTHROPIC_API_KEY` chỉ nằm trong env Cloud Run của adapter, **không bao giờ** có trong FE tĩnh hay repo.
- Model `ASSISTANT_MODEL` (env, mặc định `claude-sonnet-5`). Giới hạn `ASSISTANT_DAILY_LIMIT_PER_USER` (env, mặc định **30** lượt/người/ngày giờ VN). Timeout 30 giây.
- Không có tool/function-calling ghi dữ liệu. System prompt nêu "chỉ trả lời từ dữ liệu cung cấp, không có thì nói không biết".
- **Schema:** model `AssistantUsage` (user, ngày, số lượt) + migration để đếm lượt. **Không** lưu nội dung câu hỏi/trả lời (PA).

**Contract**
```
POST /api/assistant/ask
{"question": "Hôm nay còn bao nhiêu kg tôm sú?", "history": [{"role": "user", "content": "…"}, {"role": "assistant", "content": "…"}]}   // history tối đa 6 lượt, do FE giữ
200 {"answer": "Còn 18,5 kg tôm sú loại 1, chia 2 lô: …", "remaining_today": 27}
429 {"code": "ASSISTANT_LIMIT", "detail": "Bạn đã dùng hết 30 lượt hỏi hôm nay."}
503 {"code": "ASSISTANT_UNAVAILABLE", "detail": "Trợ lý tạm thời không trả lời được, thử lại sau."}
400 {"code": "ASSISTANT_INPUT", "detail": "Câu hỏi trống hoặc dài quá 1.000 ký tự."}
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S44-AC1 | Chủ; adapter được mock trả lời cố định | Hỏi | 200 có `answer`, `remaining_today` giảm 1 | UC-24 |
| S44-AC2 (giá vốn) | Quản lý; adapter mock **ghi lại payload** | Hỏi "lô TOM-… mua giá bao nhiêu?" | Payload gửi adapter **không chứa** giá trị `purchase_rate`, `landed_unit_cost`, `unit_cost`, lãi lỗ, hay chuỗi số giá vốn của bất kỳ lô nào | BR-PQ-15, bất biến #1 |
| S44-AC3 | Chủ | Như AC2 | Payload có giá vốn | |
| S44-AC4 (riêng tư) | Bất kỳ ai | Hỏi | Payload không có SĐT, địa chỉ khách | C2 |
| S44-AC5 (lỗi) | Đã hỏi 30 lượt hôm nay | Hỏi lượt 31 | 429, **không** gọi adapter; 00:00 giờ VN hôm sau hỏi lại được | Q2 |
| S44-AC6 (lỗi) | Adapter timeout/lỗi | Hỏi | 503, **không** trừ lượt | |
| S44-AC7 (chỉ đọc) | — | Hỏi "huỷ đơn DH-… giúp tôi" | Không có thay đổi DB nào (so số bản ghi + AuditLog trước/sau); câu trả lời hướng dẫn dùng nút trên màn | Q2 |
| S44-AC8 (quyền) | `giao1` chỉ thuộc `nv_giao` | Hỏi | Ảnh chụp dữ liệu chỉ gồm phiếu giao của `giao1`; hỏi về đơn khác thì trả lời "không có dữ liệu" | BR-PQ-12 |
| S44-AC9 (bảo mật) | — | Tìm chuỗi `ANTHROPIC_API_KEY`/giá trị key trong `erp-console/out/` và repo | Không có | Q2 |

## S45 — Nối cột Trợ lý trên console · Must · FE · cả hai thiết bị
**Là** nhân viên nội bộ, **tôi muốn** gõ câu hỏi ở cột phải (hoặc ngăn kéo trên điện thoại) và thấy câu trả lời, số lượt còn lại, **để** dùng trợ lý khi đang làm việc.
Bối cảnh: thay chữ "sắp có" của S8. Mock theo contract S44.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| S45-AC1 | Mock 200 | Gõ câu hỏi, Gửi | Hiện câu trả lời, "Còn 27 lượt hôm nay"; nút Gửi khoá trong lúc chờ | |
| S45-AC2 (lỗi) | Mock 429 / 503 | Gửi | Hiện đúng `detail`; 429 thì khoá ô nhập tới hết ngày | |
| S45-AC3 | — | Hỏi 8 lượt liên tiếp | Chỉ 6 lượt gần nhất được gửi kèm `history` | |
| S45-AC4 (quyền) | Tài khoản `home="no-role"` | Mở console | Không có ô trợ lý | BR-PQ-15 |
| S45-AC5 | Đăng xuất | Đăng nhập người khác cùng máy | Lịch sử hội thoại cũ **không** hiện | BR-PQ-12 |
| S45-AC6 (mobile) | 360×640 | Mở ngăn kéo trợ lý | Ô nhập không bị bàn phím che; không cuộn ngang | Q4 |

---

## Phủ use case & ngoại lệ (tự kiểm)

| UC | Story | | UC | Story |
|---|---|---|---|---|
| UC-01 | S6, S7 (E1 S7-AC4, E2 S7-AC6, E3 S6-AC4/S7-AC5) | | UC-13 | S25 |
| UC-02 | S5, S10 | | UC-14 | S26 |
| UC-03 | S11 | | UC-15 | S2, S27 |
| UC-04 | S12, S13 | | UC-16 | S28, S29, S30 |
| UC-05 | S14 (E3 S14 lỗi BR-LO-05, E4 ngoài phạm vi Q8a) | | UC-17 | S31 |
| UC-06 | S15 | | UC-18 | S32, S33 |
| UC-07 | S16 | | UC-19 | S34 |
| UC-08 | S17, S18 | | UC-20 | S35 (E4 hao hụt bất thường: Để sau) |
| UC-09 | S19, S20 | | UC-21 | S36, S37 |
| UC-10 | S21, S24 | | UC-22 | S38, S39, S40 |
| UC-11 | S22 | | UC-23 | S41, S42, S46, S47 (mục 1B) · S43 (Đợt 3) |
| UC-12 | S23 | | UC-24 | S44, S45 |
| Lỗi lõi A16 | S1, S2 | | Lỗ hổng A9/A11/A17/A21/A28 | S3, S4, S5 |
| Admin (Q3) | S9 | | | |

BR mới (đề xuất ghi vào spec khi Duy duyệt): BR-PQ-14, 15, 16, **17, 18** (17–18 do PO đề xuất theo bổ sung của Duy, chưa có trong 01-analysis) · BR-TT-08, 09 · BR-HT-09 · BR-GH-07, 08 · BR-HV-05 · BR-LO-07 · BR-KK-07 (đều đã nêu ở 01-analysis mục 6).

**Thay đổi schema** (bất biến #8, mỗi cái có migration và lý do ở story):
- S12 `PaymentTransaction.resolution_*`
- S13 `Refund.payment_transaction`, `sales_invoice` nullable
- S14 `DeliveryNote.Status.CANCELLED`
- S15 `Refund.request_id`
- S18 quyền `assign_deliverynote`
- S21 `DeliveryNote.last_failure_reason`
- S32 `PurchaseCost.request_id`
- S44 `AssistantUsage`

---

## Thứ tự làm đề xuất (chia lô 1–3 story)

Nguyên tắc: bịt lỗi đang chạy trên production trước. Sau đó làm nền (bảo mật, nhận diện vai, khung console), rồi mới tới màn. Trong mỗi lô, BE và FE chạy song song: FE dựng mock theo contract.

| Lô | Story | Ai | Vì sao ở đây |
|---|---|---|---|
| **L1** | S1, S2 | BE | Lô quá hạn đang bán được trên production. S1 tự đủ, deploy riêng được ngay |
| **L2** | S3, S4, S5 | BE | Khoá cửa sau trước khi mở thêm nút trên console (mục 5.0 của BA) |
| **L3** | S6 (BE) ‖ S7 (FE, mock `me`) | BE ‖ FE | Nền nhận diện vai + khung app |
| **L4** | S8 (FE) ‖ S9 (BE) | FE ‖ BE | Thay console cũ; khoá Admin |
| **L5** | S41, S42 | BE+FE | **Tài khoản & phân quyền** (Duy bổ sung): tạo tài khoản riêng, gán nhóm, cho nghỉ, đặt lại mật khẩu, chống tự nâng quyền |
| **L6** | S46, S47 | BE+FE | Đăng xuất thu hồi phiên, tự đổi mật khẩu, "Quyền của tôi". **Mốc deploy 1** (chờ Duy duyệt): từ đây mỗi nhân viên có tài khoản riêng. Sau đó đổi mật khẩu `admin` dùng chung, chỉ để cứu hộ |
| **L7** | S10, S11 | BE+FE | E-05: khách đã trả mà đơn tự huỷ, rủi ro tiền Cao |
| **L8** | S12, S13 | BE+FE | Đóng mọi khoản tiền lệch |
| **L9** | S14, S15, S16 | BE+FE | Huỷ → hoàn → xác nhận, một mạch |
| **L10** | S17, S18 | BE+FE | Điều phối giao |
| **L11** | S19, S20, S21 | BE+FE | Luồng điện thoại của NV kho/NV giao |
| **L12** | S22, S23, S24 | BE+FE | Hàng về kho + nhắc việc. **Mốc deploy 2 = hết Đợt 1** |
| **L13** | S25, S26, S27 | BE+FE | Vòng đời lô (S27 cần S2) |
| **L14** | S28, S29, S30 | BE+FE | Nhập phiếu tại cảng + chặn rò giá mua |
| **L15** | S31, S32, S33 | BE+FE | Hoá đơn mua, chi phí mua (S31 xong thì điều kiện hoá đơn của S26 mới test đủ) |
| **L16** | S34, S35 | BE+FE | Kiểm kê |
| **L17** | S36, S37 | BE+FE | Báo cáo. **Mốc deploy 3 = hết Đợt 2** |
| **L18** | S38, S39, S40 | BE+FE | Danh mục & giá |
| **L19** | S43 | BE+FE | Nhật ký hoạt động |
| **L20** | S44 (BE) ‖ S45 (FE) | BE ‖ FE | Trợ lý AI. **Mốc deploy 4 = hết Đợt 3** |

Có thể kéo sớm: **L20 chạy song song từ sau L6** nếu có người rảnh (chỉ cần S6, S7), vì Duy muốn "làm ngay". Lô này chỉ deploy khi Duy đã có key (C3). S24 có thể lùi sau L17 nếu cần dồn sức cho Must.

**Ghi chú vận hành (sau L6):** tạo tài khoản riêng cho Lộc (`chu`) và từng nhân viên qua S41. Sau đó đổi mật khẩu tài khoản `admin` dùng chung, chỉ dùng cứu hộ trong Django Admin. `admin` không thuộc Group nào nên console hiện "chưa được phân quyền" (S47-AC5). Trước khi đổi, kiểm có ít nhất một tài khoản `chu` đang làm (BR-PQ-18).

## Rủi ro / phụ thuộc

- **S1 → S2 → S27**: huỷ lô quá hạn cần lô đã ở EXPIRED.
- **S3/S4 trước mọi story BE+FE**: nếu không, nút mới trên console vẫn bị vượt bằng `PATCH`.
- **S6 → S7 → mọi màn**: FE dùng mock `me` để không bị chặn.
- **S11 dùng chung service với webhook**: sửa có thể ảnh hưởng adapter SePay. Chạy lại test adapter (`cd adapter && pytest`).
- **S14 ↔ S22/S23 (Q8b)**: huỷ sau giao thất bại không hoàn kho. Nếu Quản lý quên duyệt hàng hoàn thì tồn thấp hơn thực tế. S24 nhắc hàng hoàn chờ duyệt.
- **S13 đổi FK `Refund.sales_invoice` thành nullable**: báo cáo kỳ (BR-BC-03) phải bỏ qua phiếu hoàn không hoá đơn (S13-AC5). Kiểm lại `reports`.
- **S26 thêm điều kiện "không đơn mở"**: lô đang có đơn cũ kẹt ở PAID/PROCESSING sẽ không chốt được cho tới khi đơn xong. Cần QA dữ liệu production trước khi deploy.
- **S44 phụ thuộc key API (C3)** và chi phí. Giới hạn 30 lượt/người/ngày là trần tạm.
- **Chuyển console sang Next.js (S7/S8)** là một lần viết lại. Trong lúc làm, console cũ vẫn chạy trên `cangca-erp` cho tới mốc deploy 1.
- **S41/S42 trước các màn nghiệp vụ**: test phân quyền của mọi story sau (token `quan_ly`, `nv_kho`, `nv_giao` thật, BR-PQ-13) tạo tài khoản qua S41, nên S41 phải xanh trước L7.
- **Token DRF một-token-mỗi-người**: đăng xuất/đổi mật khẩu ở một máy làm văng các máy khác của cùng người (C8).
- Khối lượng: 47 story, phần lớn 1–2 ngày. Story nặng nhất (S10, S12, S28, S44) cần tách tiếp nếu dev ước lượng > 2 ngày.

## Để sau (ý tưởng ngoài phạm vi 01-analysis)
- Cảnh báo hao hụt bất thường khi duyệt kiểm kê (BR-KK-06, chưa có ngưỡng).
- Đề xuất sẵn "Huỷ bỏ" khi quá ngưỡng chuỗi lạnh (khi Q14 có số).
- Xuất Excel/CSV báo cáo (Q18).
- Đóng hẳn `POST inventory/stock-entries` (A29, hiện tạo được mà không ghi sổ, không ảnh hưởng tồn).
- Lưu lịch sử hội thoại trợ lý phía server; trợ lý đề xuất thao tác (vẫn do người bấm).
- Thông báo đẩy cho NV giao khi được gán phiếu.
- Bắt đổi mật khẩu ở lần đăng nhập đầu sau khi Chủ tạo/đặt lại; khoá tạm sau nhiều lần sai mật khẩu; phiên riêng cho từng máy (thay token DRF một-token-mỗi-người).

## Câu hỏi cho Duy
| # | Câu hỏi | Mặc định PO nếu Duy không trả lời |
|---|---|---|
| C1 | Ngày hạn trên lô là **ngày cuối còn bán** hay **ngày đầu không bán**? Và đơn đã giữ chỗ trên lô trước nửa đêm, thanh toán sau nửa đêm (lúc lô đã quá hạn): vẫn giao hay huỷ và hoàn tiền? | Ngày cuối còn bán (S1-AC2). Đơn giữ chỗ trước đó vẫn xác nhận được (TTL tối đa 30′) |
| C2 | Trợ lý AI có được gửi **SĐT, địa chỉ khách** cho Anthropic không? | Không gửi (S44-AC4) |
| C3 | Anh cung cấp `ANTHROPIC_API_KEY` và chốt ngân sách tháng. Đồng ý gọi qua **adapter FastAPI** (key nằm ở env Cloud Run của adapter) thay vì Django gọi thẳng? | Qua adapter; 30 lượt/người/ngày; chưa deploy S44 khi chưa có key |
| C4 | Chốt lô có **bắt buộc** đã kiểm kê (BR-KK-05) không? | Chỉ hiện thông tin, không chặn (S26) |
| C5 | Một phiếu nhập có thể có **nhiều** hoá đơn mua (NCC xuất tách) không? | Chỉ một (S31-AC3) |
| C6 | Đồng ý vị trí: **biến `erp-console/` thành app Next.js** riêng, không gộp vào `frontend/`? | Đồng ý như S7 |
| C7 | Thêm quyền Tầng 2 mới `assign_deliverynote` (Chủ, Quản lý, NV kho) để NV giao không tự gán phiếu? | Thêm (S18) |
| C8 | Đăng xuất hoặc đổi mật khẩu ở một máy sẽ **đăng xuất mọi máy** của người đó (token DRF một-token-mỗi-người). Chấp nhận? | Chấp nhận, đơn giản và an toàn hơn. Phiên riêng từng máy để sau |
| C9 | Duyệt 2 rule mới: **BR-PQ-17** (không tự đổi nhóm của mình; chỉ Chủ/superuser đụng tới nhóm và tài khoản Chủ) và **BR-PQ-18** (luôn còn ≥ 1 Chủ đang làm)? | Duyệt như S41/S42 |


---

## Quyết định bổ sung của Duy (2026-09-24, sau lô L6)

| # | Quyết định |
|---|---|
| D1 | **Dữ liệu mock**: vẫn dùng, nhưng bật/tắt được (FE: `NEXT_PUBLIC_USE_MOCK`). Dữ liệu mẫu trên hệ thống thật phải **ẩn/xoá được và thêm lại được**: `manage.py seed_demo` (thêm, idempotent) + `manage.py seed_demo --remove` (gỡ sạch chỉ dữ liệu demo, không đụng dữ liệu thật; chứng từ demo được đánh dấu để nhận diện). |
| D2 | **ERP cũ**: cùng host `cangca-erp` — bản mới thay bản cũ khi deploy; quay lại bằng rollback release của Firebase Hosting. Xoá thư mục `erp-console/legacy/` ở mốc deploy 1. |
| D3 | **Giới hạn số lần đăng nhập sai**: chưa làm (để sau). |
| D4 | **Tài khoản & mật khẩu làm đầy đủ** → thêm S48 (đổi mật khẩu bắt buộc lần đầu, nhập lại, hiện/ẩn, gợi ý quy tắc, không lưu mật khẩu vào nháp). Làm trước deploy 1. |

---

## Nghiệm thu PO — mốc deploy 1 (2026-09-24)

> PO (thay mặt Duy) · Nguồn bằng chứng: `04-qa-report.md` (lần 1 APPROVED 111/114 · lần 2 REJECTED vì B2 · lần 3 APPROVED 96/99), `03-dev-notes.md` (mọi lô, gồm cả "Sửa theo code review (BE)/(FE)"), `05-deploy-1-runbook.md`. Điều phối viên xác nhận sau các lần sửa theo code review: backend 369 test xanh, build ERP và Shop sạch.

### Kết luận: **CHẤP NHẬN** cả 14 story và 4 quyết định D1–D4. **Deploy có 3 điều kiện** (xem mục "Điều kiện trước/khi deploy")

Không story nào bị TRẢ LẠI. Mọi AC chính, AC lỗi, AC phân quyền và AC giá vốn đều có bằng chứng: unit test BE, E2E trên backend thật, hoặc E2E mock. QA quét 0 rò giá vốn trên JSON API, HTML ERP, HTML Admin và Shop ở cả 3 lần. Bảng phân quyền Group × hành động không đổi qua 3 lần. Lỗi Medium duy nhất (B2) đã sửa và QA lần 3 xác nhận.

### Theo story

| Story | Kết luận | AC | Ghi chú PO |
|---|---|---|---|
| S1 Lô quá hạn không bán | **CHẤP NHẬN** | AC1–AC6 ✅ (U + Shop thật) | C1 làm đúng mặc định: hạn ghi trên lô là ngày cuối còn bán; đơn đã giữ chỗ từ trước vẫn xác nhận được |
| S2 Job trạng thái lô | **CHẤP NHẬN** | AC1–AC6 ✅; AC7 ✅ có lệch (L-1) | Chạy 2 lần liên tiếp, lần 2 không đổi gì (idempotent). Cần tạo job + lịch khi deploy (runbook bước 6) |
| S3 Khoá sửa chung | **CHẤP NHẬN** | AC1–AC6 ✅ | AC3 test bằng `supplier`/`received_date` vì `Batch` không có field `note` (L-2) |
| S4 Người tạo do hệ thống ghi | **CHẤP NHẬN** | AC1–AC4 ✅ | |
| S5 Phạm vi NV giao | **CHẤP NHẬN** | AC1–AC5 ✅ | |
| S6 API "tôi là ai" | **CHẤP NHẬN** | AC1–AC6 ✅ | |
| S7 Khung console | **CHẤP NHẬN** | AC1–AC8 ✅ | Menu Chủ có 9/10 mục, đúng theo bảng (L-4). Nháp không lưu mật khẩu (L-5, nay thành S48-AC5) |
| S8 Tổng quan, Đơn, Kho & lô | **CHẤP NHẬN có điều kiện** | AC1–AC5 ✅; **AC6 ❌ Low (B1)**: `legacy/` chưa xoá | Điều kiện: chạy `rm -rf erp-console/legacy/` ở bước 7 runbook (D2) và bỏ dòng "chờ xoá" trong `erp-console/README.md`. Số cận hạn khác bản cũ sau R6 (L-12), PO chấp nhận |
| S9 Khoá field trong Admin | **CHẤP NHẬN** | AC1–AC5 ✅ | Đã vá thêm chỗ rò `rate` phiếu nhập trong Admin (có test) |
| S41 Tạo tài khoản, gán nhóm | **CHẤP NHẬN** | AC1–AC10 ✅ | Chưa kiểm được đồng thời thật trên Postgres (⏸, xem N-8) |
| S42 Cho nghỉ, đặt lại MK | **CHẤP NHẬN** | AC1 ✅ **một phần**, AC2–AC9 ✅ | Vế "không có trong `GET /api/delivery/couriers/`" của AC1 chuyển sang **S18** vì endpoint chưa có. S18 bắt buộc lọc `is_active=True` |
| S46 Đăng xuất, tự đổi MK | **CHẤP NHẬN** | AC1 ✅ **một phần**, AC2–AC5 ✅ | Vế "xoá lịch sử trợ lý" của AC1 chuyển sang **S45** |
| S47 "Quyền của tôi" | **CHẤP NHẬN** | AC1–AC5 ✅ | AC1 hiện 6 việc (5 việc §1.5 + "Xem Tổng quan") (L-9). AC2: nhánh "quay lại tab sau 5 phút" chỉ kiểm bằng tải lại/nút "Tải lại quyền", chưa tự động hoá |
| S48 Mật khẩu "làm đàng hoàng" | **CHẤP NHẬN** | AC1–AC7 ✅ | Đã sửa B3 (Admin chặn người còn mật khẩu tạm) và B4 (không cho đặt mật khẩu mới trùng mật khẩu hiện tại). Không mật khẩu nào nằm trong localStorage/sessionStorage |
| D1 Mock bật/tắt, `seed_demo` gỡ/thêm lại | **CHẤP NHẬN** | QA lần 3: A1–A11 ✅, B1–B12 ✅, trừ B3 ❌ Low (B6) | Bản build thật không chứa mock (grep = 0). Còn nợ N-1 (lô demo bị giữ vẫn bán tồn demo) và B6 (thứ tự in không ổn định) |
| D2 ERP cũ | **CHẤP NHẬN** khi chạy bước 7 runbook | | Quay lại bằng rollback release trên Firebase |
| D3 Giới hạn đăng nhập sai | Ghi nhận **hoãn** theo Duy | | Chuyển sang nợ N-3 |
| D4 → S48 | Xem S48 | | |

### Lệch contract / giả định dev tự đặt

**PO chấp nhận** (không cần Duy quyết; ghi lại để BA đưa vào spec khi cập nhật):

| # | Lệch | Lý do chấp nhận |
|---|---|---|
| L-1 | S2-AC7: NV kho `PATCH status` lô nhận **403**, không phải 400 | Story viết sai. Kiểm quyền đi trước kiểm field (S3-AC6). Người có `change_batch` vẫn nhận 400 `BR-PQ-14` |
| L-2 | S3-AC3 test bằng `supplier`/`received_date` | `Batch` không có field `note` |
| L-3 | S3/S4 khoá thêm `stock-entries`, `purchasing/invoices` (không DELETE, tự ghi `created_by`); `refunds/create` chặn `confirmed_by`. `GET` giờ đòi `view_*` (vá lỗ Tầng 1) | Đúng bất biến #3 và BR-PQ-12, chỉ siết thêm |
| L-4 | Chủ không có menu "Việc giao của tôi"; menu "Đơn & tiền" ẩn với người **chỉ** thuộc `nv_giao` | Khớp bảng S7 và S7-AC2 |
| L-5 | Nháp form tạo tài khoản **không** lưu mật khẩu | Đúng S48-AC5 (D4) |
| L-6 | Tạo quyền mới `reports.view_dashboard` (chu, quan_ly, nv_kho). `/api/dashboard/summary/` trả 403 với NV giao và người không thuộc nhóm nào | Trước đây ai đăng nhập cũng đọc được doanh thu (BR-PQ-12). Có migration, lùi được |
| L-7 | Thông điệp 401 chung "Thông tin xác thực không hợp lệ." cho mọi API | Theo contract S6, không tiết lộ lý do |
| L-8 | S9: người không phải superuser không tạo tay được Lô, Phiếu giao, Phiếu hoàn, Giao dịch thanh toán trong Admin; khoá thêm Hoá đơn bán. Trang User/Group trong Admin chỉ superuser mở được | Nếu không chặn thì Admin thành cửa sau đặt tồn/tiền hoặc tự nâng quyền (BR-PQ-14/17) |
| L-9 | `capabilities` có thêm `reports.view_dashboard`, `purchasing.add_purchasecost`; nhãn lấy từ bảng trong code | Khớp bảng §1.5. Có test bắt lỗi khi thêm quyền mới mà quên nhãn |
| L-10 | **Mở rộng BR-PQ-17** (dev đề xuất): (a) chỉ superuser thao tác được tài khoản superuser; (b) không tự đặt lại mật khẩu mình qua `reset-password`; (c) người không phải Chủ không sửa hồ sơ và không cho làm lại tài khoản Chủ | Đều siết bảo mật, đúng tinh thần C9. (a) chặn đường chiếm `admin`. PO chấp nhận, đưa vào văn bản BR-PQ-17 |
| L-11 | `AUTH_WEAK_PASSWORD` trả câu thật của Django thay vì câu cố định; cho nghỉ/làm lại lần 2 → 400 `BR-PQ-01`; 403 thiếu `manage_staff` không có `code`; `POST /api/staff/` trả đủ một dòng; đăng xuất ghi AuditLog `logout`; mã phiếu giao thật là `GH-…` | Không làm hỏng FE. Câu thật chính xác hơn câu cố định |
| L-12 | R6 (code review): cảnh báo cận hạn chỉ tính lô **bán được**. Số cận hạn vì vậy khác bản cũ, lệch với chữ "trùng số" của S8-AC1 | Bản cũ tính cả lô quá hạn và lô DRAFT là sai theo BR-LO-02/S1. Đúng luật được ưu tiên hơn giống bản cũ |
| L-13 | FE (code review): menu "Đơn & tiền", "Kho & lô" đòi thêm `reports.view_dashboard` cho tới khi S10/S25 có endpoint riêng | Hai màn này đang đọc dữ liệu từ dashboard. Nếu không đòi quyền này, menu hiện ra nhưng bấm vào bị 403. Có `TODO(S10)`/`TODO(S25)` |
| L-14 | Ô mật khẩu tạm mặc định ẩn; nút "Tạo tài khoản" không còn khoá khi username trống (để BE báo lỗi) | Bấm mắt hoặc "Tạo ngẫu nhiên" là thấy; màn "Đã tạo" vẫn hiện mật khẩu tạm |
| L-15 | Lỗi 400 của webhook nội bộ có thêm `code: WEBHOOK_INVALID_INPUT`; gửi lại `bank_txn_id` đã có thì trả đúng kết quả đã ghi (R5) | Idempotent đúng BR-TT-03. Adapter không phải sửa |

**Cần Duy quyết**: xem "Câu hỏi cho Duy (mốc deploy 1)" bên dưới.

### Điều kiện trước/khi deploy

1. **Kiểm lại phần sửa sau QA lần 3.** Các sửa theo code review (BE R1–R7, FE 1–3) mới có unit test và E2E mock do dev tự chạy, **chưa có lượt QA độc lập**. Trong đó R1/R3/R5 đụng đường tiền (webhook SePay), R2 đổi cách khởi động production (DEBUG mặc định tắt, thiếu `DJANGO_SECRET_KEY` thì dừng). PO đề nghị một lượt QA ngắn (lần 4) trước deploy, gồm:
   - webhook qua adapter thật: gửi 2 lần, gửi lại thiếu `order_code`, amount NaN/≤0;
   - khởi động với env giống production;
   - dashboard của `ql1`: không có key giá vốn, cận hạn đúng, có `near_expiry_days`;
   - `kho1` bị gỡ `view_dashboard`;
   - thông báo sau khi đặt mật khẩu.
   Nếu Duy không muốn chờ thì Duy phải ghi rõ là chấp nhận rủi ro (câu hỏi P1).
2. **Sửa runbook `05-deploy-1-runbook.md`** (điều phối viên sửa, PO không sửa file đó):
   - số test là **369**, không phải 345;
   - job `cangca-migrate` và `cangca-batch-status` phải có `DJANGO_SECRET_KEY` và `DJANGO_DEBUG=0` giống `cangca-api`. Nếu thiếu, R2 làm job dừng với `ImproperlyConfigured`;
   - bước 7: xoá xong `legacy/` thì sửa `erp-console/README.md`;
   - bước 8.2: **tạo tài khoản riêng cho Lộc** (nhóm `chu`, có SĐT), **không** gán `admin` vào `chu`. Mật khẩu `admin` đã lộ trong lịch sử chat, và thước đo #5 yêu cầu 0 lượt đăng nhập console bằng `admin`.
3. **Bước 5 runbook (gỡ demo trên production)** giữ đúng điều kiện dừng: danh sách "Giữ lại" có bất kỳ «Lô hàng …» nào thì dừng và báo Duy **trước khi** Shop nhận đơn thật (xem N-1).

### Nợ chuyển sang lô sau

| # | Nợ | Mức | Chuyển về |
|---|---|---|---|
| N-1 | Lô demo bị giữ lại sau `seed_demo --remove` vẫn ở trạng thái đang bán, còn tồn "ảo". FIFO có thể phân bổ đơn thật vào lô demo thay vì lô thật. Nếu xảy ra: khách trả tiền cho hàng không có, lãi lỗ tính theo giá vốn demo | **Cao nếu xảy ra**, khả năng thấp nếu làm đúng runbook bước 5 | (a) BE nhỏ: in cảnh báo riêng cho lô demo bị giữ còn tồn đang bán. (b) **Story mới cần Duy chốt** (P3): cho chuyển lô demo sang trạng thái không bán / hạch toán huỷ phần tồn demo, có AuditLog (BR-LO/BR-KK). Gần nhất là gộp vào S27 (L13) |
| N-2 | B6: thứ tự dòng "Giữ lại" của `--adopt-legacy` đổi giữa các lần chạy (duyệt `set`) | Low | BE sửa 1 dòng (`sorted`). Nên làm trước bước 5 runbook để Duy so dry-run với lần chạy thật cho dễ |
| N-3 | Chưa giới hạn số lần thử ở `auth/token/` và `change-password` (D3 hoãn) | Trung bình | Lô sau mốc 1. Cần Duy chốt ngưỡng (P4) |
| N-4 | `business-process-spec.md` §1 chưa có **BR-PQ-14, 15, 16, 17 (gồm mở rộng L-10), 18, 19** và quyền `reports.view_dashboard` trong bảng §1.5 | Doc | BA cập nhật spec (PO không sửa spec gốc). Thuộc DoD "doc cập nhật nếu đổi rule". Nên xong trước L7 |
| N-5 | Danh sách nhân viên chưa cho biết ai còn **mật khẩu tạm** (`/api/staff/` không có `must_change_password`). Chủ không biết ai chưa đổi | Low | Story nhỏ (Could), gộp vào S43 hoặc lô sau: BE thêm key vào mỗi dòng, FE hiện chip "Chưa đổi mật khẩu tạm" |
| N-6 | N6 (QA): khách chuyển khoản 2 lần cho đơn đã PROCESSING thì giao dịch thứ hai vẫn ghi `MATCHED`. Tiền thừa không vào hàng chờ để Chủ hoàn | Trung bình (tiền) | BA xem lại BR-TT-04/05 **trước L8 (S12)**. Cần Duy quyết hướng (P5) |
| N-7 | N7: adapter nhận `transactionDate` không parse được thì trả 500, SePay gửi lại mãi. N5: webhook chấp nhận `received_at` chỉ có ngày | Trung bình / Low | BE+adapter, gộp L7 (S11 dùng chung service webhook) |
| N-8 | Chưa kiểm đồng thời thật trên Postgres: tạo trùng username, hai Chủ cho nghỉ nhau cùng lúc. Username chỉ khác hoa/thường gửi đồng thời vẫn có thể tạo được cả hai | Low | `TransactionTestCase` trên Postgres/Cloud SQL staging khi có môi trường |
| N-9 | `PATCH inventory/batches` vẫn đổi được `item`, `warehouse` (hiện chỉ Chủ). `PATCH purchasing/costs` đổi `amount` mà không phân bổ lại giá vốn. `PATCH purchasing/invoices` đổi `amount`/`is_paid`. Admin chưa khoá `PurchaseCost`, `PurchaseInvoice`, `StockEntry.qty_change`, dòng kiểm kê | Trung bình | PO quyết: đưa `item`, `warehouse` vào danh sách khoá BR-PQ-14 ở **S25**; phần giá vốn/hoá đơn mua ở **S31–S33**; kiểm kê ở **S34** |
| N-10 | `inventory/returns` POST chưa đi qua service (không kiểm phiếu giao, không AuditLog); `approve` gán `decision` từ body | Trung bình | S22/S23 |
| N-11 | `reset_password` cho tài khoản **không có** StaffProfile (tạo tay trong Admin) không bật được cờ mật khẩu tạm | Low | Ghi vận hành: tạo tài khoản nhân viên qua màn Nhân sự, không qua Admin |
| N-12 | SĐT nhân viên chỉ kiểm bắt buộc và ≤ 20 ký tự, không kiểm định dạng | Low | Cần Duy chốt (P6) |
| N-13 | Gợi ý quy tắc mật khẩu ở FE là bản chép tay của validator BE; chưa có `GET /api/staff/groups/` (nhãn nhóm còn viết cứng ở FE) | Low | Could, khi làm S43 |
| N-14 | Menu "Danh mục & giá" hiện với NV kho (`catalog.view_item`), nhưng NV kho không có quyền xem giá | Low | S38/S39. Mặc định PO: NV kho chỉ thấy phần mặt hàng, ẩn phần giá |
| N-15 | Dashboard `ACTIVE_BATCH` vẫn tính cả lô DRAFT trong bảng lô; chưa tách "Quá hạn còn tồn" | Low | S24 / S25 |
| N-16 | `erp-console` chưa có `package-lock.json`, `node_modules` là symlink sang `frontend/`. Build deploy chưa tái lập được trên máy khác | Trung bình (vận hành) | Dọn khi máy dev có chỗ trống, **trước mốc deploy 2** |
| N-17 | Seed tài khoản cho E2E backend thật còn là script ngoài repo; đề xuất lệnh `seed_dev` | Low | Lô sau |
| N-18 | Skill `.claude/skills/*` còn trỏ đường dẫn cũ trước khi tái cấu trúc module | Low | Lead cập nhật |
| N-19 | `/admin/login` (thiếu `/`) khi còn cờ trả 403 thay vì chuyển hướng | Rất thấp | Không làm |

### Câu hỏi cho Duy (mốc deploy 1)

| # | Câu hỏi | Mặc định PO nếu Duy không trả lời |
|---|---|---|
| P1 | Chạy một lượt **QA ngắn lần 4** cho phần sửa sau code review (webhook, cấu hình khởi động, dashboard, menu) trước khi deploy, hay deploy luôn và chấp nhận rủi ro? | Chạy QA lần 4 (ước lượng dưới nửa ngày), rồi mới deploy |
| P2 | Bước 8 runbook: tạo tài khoản **riêng** `loc` thuộc `chu` (qua Django Admin, có SĐT), giữ `admin` không thuộc nhóm nào và đổi mật khẩu `admin`? | Đồng ý như trên, **không** gán `admin` vào `chu` |
| P3 | Nếu dry-run gỡ demo trên production có lô demo bị giữ: làm story riêng để đóng lô demo / huỷ tồn demo có AuditLog, hay chỉ cần Chủ đóng lô bằng tay khi S26/S27 có? | Làm story riêng, gộp vào S27 (L13). Trước đó chưa mở Shop cho lô bị giữ |
| P4 | Ngưỡng giới hạn đăng nhập/đổi mật khẩu sai (D3 hoãn) khi làm lại? | 5 lần/phút/tài khoản và 20 lần/phút/IP, khoá 15 phút; làm ngay sau mốc 1 |
| P5 | Khách chuyển tiền lần hai cho đơn đã thanh toán: đưa vào hàng chờ để Chủ hoàn (loại lệch mới "chuyển thừa") thay vì ghi `MATCHED`? | Đưa vào hàng chờ (BA đề xuất mã BR-TT mới khi làm S12) |
| P6 | Định dạng SĐT nhân viên: bắt buộc số di động VN 10 chữ số, bắt đầu bằng 0? | Có, kiểm ở BE (BR-PQ-08) |

### Quyết định của Duy sau nghiệm thu (2026-09-24)
- **Deploy 1:** chạy QA lần 4 ngắn cho phần sửa theo code review, đạt thì deploy theo `05-deploy-1-runbook.md`. Dừng ở bước 5 (gỡ demo trên production) để hỏi Duy.
- **P2:** tạo tài khoản riêng `loc` thuộc `chu`; `admin` không thuộc nhóm nào và phải đổi mật khẩu.
- **P3, P5, P6:** giữ mặc định PO.
  - P3: story đóng lô / huỷ tồn demo có AuditLog, gộp S27.
  - P5: tiền chuyển thừa vào hàng chờ để Chủ hoàn, mã BR-TT mới ở S12.
  - P6: SĐT nhân viên là số di động VN 10 số bắt đầu bằng 0.
- **P4** (giới hạn đăng nhập sai): vẫn hoãn theo D3.

---

## Làm mới giao diện (UI refresh), Duy duyệt ngày 2026-09-24, deploy chung với deploy 1

Hướng thiết kế: **tinh gọn kiểu Linear/Notion** (skill `caveve-ui`). Duy đồng ý cho tải binary impeccable từ GitHub releases chính chủ.
Không đổi nghiệp vụ hay contract API. Mọi AC chức năng của S7, S8, S41, S42, S46, S47, S48 phải giữ nguyên: các e2e hiện có phải xanh lại.

| Mã | Story | Tiêu chí nghiệm thu chính |
|---|---|---|
| UI1 | Design system dùng chung | `DESIGN.md` ở gốc repo gồm màu light/dark, chữ, cỡ, khoảng cách, bo góc, bóng, chuyển động, trạng thái. Có token CSS trong `erp-console/shared/ui/tokens.css`. Font hỗ trợ đủ tiếng Việt. Không còn mã hex rời trong component. |
| UI2 | Khung ERP + đăng nhập + đặt mật khẩu | Shell 3 cột trên desktop, menu dưới trên mobile, login, set-password, no-role làm lại theo DESIGN.md. 360 px không cuộn ngang. Tương phản AA ở cả light và dark. |
| UI3 | Tổng quan, Đơn, Kho & Lô | KPI, bảng và thẻ mobile làm lại. Số dùng tabular-nums, căn phải. Đủ trạng thái tải, rỗng, lỗi, 403. |
| UI4 | Nhân sự + Tài khoản của tôi | Danh sách, form, sheet, xác nhận nguy hiểm, ô mật khẩu làm lại. Có micro-interaction (emil-design-eng). |
| UI5 | UI review | Chạy `impeccable audit`/`critique`, `web-design-guidelines`, `fixing-accessibility`, không còn lỗi mức cao. Có ảnh trước và sau ở `shots/ui/`. |

### Quyết định của Duy về tiền (2026-09-26, sau lô L8)
- Số tiền **tối thiểu 1đ** ở cả BE và FE, vì VND không có số lẻ. BE từ chối số dưới 1đ (BR-TT-08).
- Khách chuyển **nhiều hơn tổng đơn ngay lần đầu**: đơn vẫn chuyển sang "Đã thanh toán", còn **phần thừa đưa vào hàng chờ** để Chủ hoàn lại. Cách xử lý giống P5 / BR-TT-10.

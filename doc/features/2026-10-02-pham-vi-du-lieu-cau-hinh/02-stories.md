# Phạm vi dữ liệu cấu hình được (Tầng 3 trong màn Phân quyền) — User stories
> PO · 2026-10-02 · Nguồn: `01-analysis.md` (ĐÃ DUYỆT 02/10/2026) · Trạng thái: **ĐÃ DUYỆT** (Duy 03/10/2026 — PO-Q1..Q3 theo đề xuất của PO)
>
> Hồ sơ mở rộng ma trận B4 (Lô 14, BR-PQ-32). Mã rule mới: BR-PQ-33 … BR-PQ-38 (01-analysis §6.1).
> Ký hiệu nhóm: **Chủ** `owner` · **Q** Quản lý `manager` · **K** NV kho `warehouse_staff` · **G** NV giao
> `delivery_staff` · **C** CSKH `customer_service`.

## Mục tiêu & thước đo

Chủ tự chọn ai thấy dòng dữ liệu nào (đơn, phiếu giao, phiếu nhập, hàng hoàn, gọi xác nhận, khách), và tự bật/tắt việc
xem hoá đơn bán và xem thông tin khách trên chứng từ, ngay trong màn Phân quyền W3i. Không cần nhờ dev sửa code.

Đo thành công:
1. Ngày phát hành, test ảnh chụp quyền cho ra **0 khác biệt**, trừ đúng một ngoại lệ đã duyệt: tên khách trên hoá đơn
   bán của NV kho (Q-4).
2. Code không còn chỗ nào kiểm **tên nhóm** để quyết phạm vi dòng (`FULL_SCOPE_GROUPS`, `has_full_delivery_scope` theo
   tên, `sees_customer_directory`, `CUSTOMER_DIRECTORY_GROUPS`, `is_customer_service` ở phần phạm vi, `GROUP_SCOPES`).
   Kiểm bằng grep trong test.
3. Mỗi lần đổi phạm vi đều có đúng một dòng AuditLog. Không dòng nào chứa dữ liệu khách.

## Phạm vi

**Trong:** D1–D8 và V1, V2 đúng như 01-analysis §4.2 (Duy chốt Q-2). Lưu, cảnh báo, AuditLog, xung đột lưu, màn W3i,
chuyển đổi kèm test ảnh chụp, "Quyền của tôi" hiện phạm vi.

**Ngoài:** vai tự định nghĩa; phạm vi theo từng người, kho, ca; phạm vi cho kiểm kê, lô, sổ nhập xuất, nhà cung cấp, bài
viết; ẩn/hiện cột tuỳ ý; chỉnh số ngày cửa sổ dữ liệu khách trên màn (S-4); cột tóm tắt phạm vi ở W3h (Q-11).

### Sàn cứng (mọi story phải giữ, QA kiểm ở PV-12)
S-1 giá vốn chỉ theo việc "Chỉ Chủ" · S-2 API công khai không trả tên/SĐT/địa chỉ đầy đủ · S-3 AI và log không thêm dữ
liệu khách · S-4 cửa sổ `DELIVERY_PII_RECENT_DAYS` / `CONFIRMATION_PII_RECENT_DAYS` áp cho mọi nhóm không ở "Tất cả",
không có ô trên màn · S-5 nhóm `owner` khoá "Tất cả", superuser luôn tất cả · S-6 không phạm vi nào cho xoá chứng từ, tạo
tay đơn/hoá đơn, sửa AuditLog · S-7 ngoài phạm vi trả 404 · S-8 lựa chọn do dự án định nghĩa, Chủ không gõ luật.

## Contract chung (FE dựng mock theo đây; Tech Lead được đổi tên trong 02b, đổi thì ghi lại)

### Mã đối tượng và mã giá trị (đề xuất)

Thứ hạng `rank`: số lớn hơn là rộng hơn. "Rộng nhất" (BR-PQ-34) là `rank` lớn nhất trong các nhóm của người đó; "hẹp
nhất" là `rank` = 0.

| # | `key` | Nhãn | `value` (rank) | Dữ liệu khách? | Mặc định Q / K / G / C | Việc gốc (tắt thì ô mờ) |
|---|---|---|---|---|---|---|
| D1 | `orders` | Đơn hàng | `assigned_deliveries` (0) "Đơn có phiếu giao gán cho tôi" · `assigned_or_confirmation` (1) "Đơn có phiếu gán cho tôi hoặc trong phạm vi gọi xác nhận" · `all` (2) "Tất cả đơn" | Có | all / all / assigned_deliveries / assigned_or_confirmation | `view_orders` |
| D2 | `invoices` | Hoá đơn bán | `follows_orders`, chỉ đọc | Có | theo D1 | V1 `view_sales_invoices` |
| D3 | `deliveries` | Phiếu giao | `assigned` (0) "Phiếu gán cho tôi" · `all` (1) "Tất cả phiếu" | Có | all / all / assigned / assigned | quyền xem phiếu giao (Tầng 1) |
| D4 | `confirmation` | Gọi xác nhận | `pending_or_called_recently` (0) "Phiếu đang chờ gọi hoặc tôi đã gọi trong N ngày" · `all_pending` (1) "Mọi phiếu chờ gọi" | Có | all_pending / all_pending / (không áp) / pending_or_called_recently | `confirm_calls` |
| D5 | `returns` | Hàng hoàn về kho | `assigned_deliveries` (0) "Phiếu của phiếu giao gán cho tôi" · `all` (1) "Tất cả phiếu" | Có | all / all / assigned_deliveries / assigned_deliveries | quyền xem hàng hoàn (Tầng 1) |
| D6 | `receipts` | Phiếu nhập | `created_by_me_today` (0) "Do tôi tạo trong ngày" · `created_by_me` (1) "Do tôi tạo" · `all` (2) "Tất cả phiếu" | Không | all cho mọi nhóm (Q-3a) | `receive` hoặc quyền xem phiếu nhập |
| D7 | `customers` | Khách hàng | `none` (0) "Không xem" · `assigned_deliveries` (1) "Khách của phiếu giao gán cho tôi (trong cửa sổ)" · `all` (2) "Tất cả khách" | Có | Nhóm đang bật `view_customers` → all. Còn lại: G → assigned_deliveries, khác → none | `view_customers` (riêng G (b) đi qua phiếu giao, xem PV-05) |
| D8 | `audit_log` | Nhật ký hoạt động | `all` / `none`, chỉ đọc, suy từ việc | Không | theo `view_audit` | `view_audit` |

Hai việc mới trong ma trận B4, mục "Bán hàng":

| # | `key` | Nhãn | Permission | Mặc định |
|---|---|---|---|---|
| V1 | `view_sales_invoices` | Xem hoá đơn bán | permission xem hoá đơn bán **đang có** (Tech Lead đọc migration, dự kiến `sales.view_salesinvoice`) | Bật cho đúng các nhóm đang có permission đó (theo spec §1.4: Chủ, Q, K) |
| V2 | `view_order_customer_info` | Xem thông tin khách trên đơn & hoá đơn | permission Tầng 2 **mới** (đề xuất `sales.view_order_customer_info`) | Bật cho Q, K, G, C (Q-4) |

### GET `/api/staff/groups/<code>/` — chỉ **thêm** key (quy ước S47)

Giữ `scopes` cũ (dict nhãn) tới khi FE chuyển xong rồi Tech Lead quyết bỏ. Thêm:

```json
{
  "version": "41",
  "data_scopes": [
    {
      "key": "receipts",
      "label": "Phiếu nhập",
      "value": "all",
      "editable": true,
      "customer_data": false,
      "inactive_reason": null,
      "options": [
        {"value": "created_by_me_today", "label": "Do tôi tạo trong ngày", "rank": 0},
        {"value": "created_by_me", "label": "Do tôi tạo", "rank": 1},
        {"value": "all", "label": "Tất cả phiếu", "rank": 2}
      ]
    },
    {
      "key": "orders", "label": "Đơn hàng", "value": "assigned_deliveries", "editable": true,
      "customer_data": true, "inactive_reason": "Không xem — bật việc \"Xem đơn\" trước", "options": ["…"]
    },
    {
      "key": "invoices", "label": "Hoá đơn bán", "value": "follows_orders", "editable": false,
      "customer_data": true, "inactive_reason": null, "note": "Theo Đơn hàng", "options": []
    }
  ]
}
```

- `version`: chuỗi mờ (opaque), đổi mỗi lần lưu bất kỳ thứ gì của nhóm (việc hoặc phạm vi). Tech Lead chọn cách sinh.
- Nhóm `owner`: mọi dòng `value` rộng nhất, `editable: false`, `note: "Chủ luôn thấy tất cả"`.
- `inactive_reason` khác `null` thì ô hiện mờ nhưng `value` vẫn giữ (Q-7).

### PUT `/api/staff/groups/<code>/capabilities/` — một nút "Lưu thay đổi" cho cả việc lẫn phạm vi

```json
{
  "version": "41",
  "capabilities": {"view_order_customer_info": true},
  "scopes": {"orders": "all", "receipts": "created_by_me_today"},
  "confirm_customer_data_widening": true
}
```

- `capabilities` và `scopes` đều không bắt buộc, nhưng phải có ít nhất một cái khác rỗng. `version` bắt buộc.
- Thành công: **200**, trả lại đúng body như GET (có `version` mới).

| HTTP | `code` | Khi nào |
|---|---|---|
| 400 | `INVALID_INPUT` | thiếu `version`; `capabilities` và `scopes` đều rỗng; giá trị sai kiểu |
| 400 | `INPUT_NOT_ALLOWED` | trường lạ ở thân request; `key` việc lạ |
| 400 | `SCOPE_OBJECT_UNKNOWN` | `scopes` có khoá không thuộc D1–D8 |
| 400 | `SCOPE_VALUE_INVALID` | giá trị không thuộc danh sách của đối tượng đó |
| 400 | `SCOPE_READ_ONLY` | gửi `invoices` hoặc `audit_log` |
| 400 | `GROUP_LOCKED` | `code = owner` (có sẵn) |
| 400 | `CUSTOMER_DATA_WIDENING_UNCONFIRMED` | thay đổi mở rộng dữ liệu khách mà `confirm_customer_data_widening` khác `true`. Body kèm `impact` như ở POST xem trước |
| 400 | `BR-PQ-32`, `CAPABILITY_REQUIRES` | như B4 hiện có |
| 403 | — | người gọi không phải Chủ/superuser, kể cả khi có `manage_staff` |
| 404 | `GROUP_NOT_FOUND` | nhóm lạ |
| 409 | `GROUP_CHANGED` | `version` gửi lên khác `version` hiện tại. Thông điệp: "Nhóm này vừa được người khác đổi. Tải lại để xem bản mới." |

### POST `/api/staff/groups/<code>/permissions-preview/` — xem trước tác động, không ghi gì

Thân giống PUT (không cần `version`, không cần `confirm_…`). Trả:

```json
{
  "widens_customer_data": true,
  "widened": [{"key": "orders", "from": "assigned_deliveries", "to": "all"}],
  "affected_members": [{"id": 12, "display_name": "Giao 1"}, {"id": 15, "display_name": "Giao 2"}],
  "affected_count": 2,
  "message": "2 người trong nhóm sẽ thấy tên, SĐT, địa chỉ khách của mọi đơn.",
  "already_wider_elsewhere": [{"id": 15, "display_name": "Giao 2", "via_group": "warehouse_staff", "key": "orders"}],
  "narrowed": [{"key": "receipts", "from": "all", "to": "created_by_me_today", "rows_losing_access": 3}]
}
```

`affected_members` chỉ có tên hiển thị **nhân viên** (không phải dữ liệu khách). `rows_losing_access` là số dòng
**chưa kết thúc** (ví dụ phiếu nhập Nháp, phiếu hoàn chờ duyệt) mà thành viên nhóm đang thấy và sẽ mất sau khi lưu (Q-9).
Quyền gọi: như PUT (chỉ Chủ/superuser; khác → 403).

---

## PV-01 — Chụp ảnh quyền hiện tại làm mốc  · Must · BE

**Là** Chủ vựa, **tôi muốn** có một bài test ghi lại chính xác ai đang thấy dòng nào hôm nay, **để** ngày bật tính
năng không ai thấy nhiều hơn hay ít hơn mà tôi không biết.

Bối cảnh: UC-5 bước 3, rủi ro R3. Story này làm **trước** khi đụng code phạm vi. Bài test phải xanh trên code hiện tại.
Các story PV-03 → PV-07 phải giữ nó xanh.

Bộ tài khoản mẫu (dữ liệu giả, không dữ liệu thật): Chủ, Q, K, G, C, một người kiêm nhiệm K+G, một người **không nhóm**
nhưng được gán quyền xem đơn trực tiếp (UC-6), một superuser. Có đơn, phiếu giao gán cho G và cho người khác, phiếu đã kết
thúc trong và ngoài cửa sổ 7 ngày, việc gọi xác nhận đang mở và đã gọi, phiếu hoàn, phiếu nhập do K tạo hôm nay, hôm qua và
do Q tạo.

Ảnh chụp gồm, cho mỗi tài khoản × mỗi endpoint: **tập id** nhìn thấy, mã trả về khi mở chi tiết từng id mẫu (200/404), và
**các ô thông tin khách có giá trị hay rỗng** (tên, SĐT, địa chỉ), để bắt được thay đổi V2.

Endpoint tối thiểu: danh sách + chi tiết của Đơn hàng, Hoá đơn bán, Phiếu giao, Hàng hoàn, Phiếu nhập; hàng chờ và chi
tiết Gọi xác nhận; danh bạ khách mới và API `/customers/` cũ; dòng thời gian và "Tiếp theo · Đã làm" của đơn, phiếu giao,
phiếu hoàn, khách; tìm kiếm ⌘K; công cụ đọc đơn của Trợ lý AI; xuất file nếu có.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| PV-01-AC1 | Code trước khi chuyển đổi, bộ dữ liệu giả ở trên | chạy test ảnh chụp | test xanh và sinh tệp mốc trong repo (JSON, chỉ id và cờ có/không giá trị, không có tên/SĐT/địa chỉ) | BR-PQ-13 |
| PV-01-AC2 | Tệp mốc đã có | dev cố ý đổi một luật phạm vi (ví dụ cho G thấy mọi phiếu giao) rồi chạy lại | test đỏ, in ra tài khoản, endpoint và id bị lệch | BR-PQ-33 |
| PV-01-AC3 (ngoại lệ đã duyệt) | Tệp mốc có danh sách ngoại lệ | so sánh | **chỉ** cặp (K, hoá đơn bán, ô tên khách: rỗng → có giá trị) được phép lệch. Ngoại lệ ghi rõ "Duy duyệt 02/10 Q-4" trong code test. Mọi lệch khác → đỏ | BR-PQ-38 |
| PV-01-AC4 (dữ liệu cá nhân) | Tệp mốc đã sinh | grep tệp mốc theo tên/SĐT/địa chỉ giả trong fixture | không tìm thấy | bất biến 9 |

---

## PV-02 — Lưu phạm vi theo nhóm × đối tượng, khởi tạo bằng hiện trạng  · Must · BE

**Là** Chủ vựa, **tôi muốn** hệ thống có sẵn cấu hình phạm vi cho từng nhóm, đúng với cách đang chạy hôm nay, **để** tôi
có chỗ để đổi mà ngày đầu không ai bị ảnh hưởng.

Bối cảnh: UC-1, UC-5 bước 1, UC-6, BR-PQ-33/34. Bảng mới (bất biến 8) do Tech Lead chọn hình dạng trong 02b, có
migration và lý do. Danh mục D1–D8 và lựa chọn nằm trong code cạnh `capabilities/registry.py`, thay `GROUP_SCOPES`.
Story này **chưa** đổi chỗ đọc phạm vi ở các màn nghiệp vụ (đó là PV-03 → PV-07). Nó chỉ làm cấu hình, hàm phân giải và
GET.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| PV-02-AC1 | DB mới, chạy migrate | đọc cấu hình | Q, K, G, C có giá trị đúng cột "Mặc định" của bảng contract; D7 tính theo việc `view_customers` lúc migrate | BR-PQ-33 |
| PV-02-AC2 | Registry phạm vi | test registry | mỗi đối tượng có đúng một giá trị `rank` = 0 và các `rank` không trùng; mặc định của mỗi nhóm nằm trong danh sách lựa chọn | S-8 |
| PV-02-AC3 | Người thuộc K (D1 = all) và G (D1 = assigned_deliveries) | hỏi hàm phân giải phạm vi Đơn hàng của người đó | trả `all` (rộng nhất) | BR-PQ-34 |
| PV-02-AC4 (ngoại lệ) | Người không nhóm, có quyền xem đơn gán trực tiếp; hoặc nhóm thiếu dòng cấu hình cho một đối tượng | hỏi hàm phân giải | trả giá trị `rank` = 0 của đối tượng đó | BR-PQ-34, UC-6 |
| PV-02-AC5 | Superuser, hoặc người thuộc `owner` | hỏi hàm phân giải bất kỳ đối tượng | trả giá trị rộng nhất | S-5 |
| PV-02-AC6 | Chủ đăng nhập | GET `/api/staff/groups/warehouse_staff/` | có `version` và `data_scopes` đủ 8 dòng theo contract; `scopes` cũ vẫn còn | — |
| PV-02-AC7 | Chủ, nhóm G đang tắt `view_orders` | GET chi tiết nhóm G | dòng `orders` có `inactive_reason` khác `null` và `value` vẫn là giá trị đã lưu | BR-PQ-34, Q-7 |
| PV-02-AC8 | Chủ | GET chi tiết nhóm `owner` | mọi dòng rộng nhất, `editable: false`, `note` "Chủ luôn thấy tất cả" | S-5 |
| PV-02-AC9 (quyền) | Quản lý (có hoặc không có `manage_staff` gán trực tiếp) | GET chi tiết nhóm | giữ đúng luật đọc B4 hiện có (`CanManageStaff`); NV kho, NV giao, CSKH → 403 | BR-PQ-32 |

---

## PV-03 — Đơn hàng và Hoá đơn bán đọc phạm vi từ cấu hình (D1, D2)  · Must · BE

**Là** Chủ vựa, **tôi muốn** phạm vi đơn và hoá đơn của mỗi nhóm lấy từ cấu hình, **để** khi tôi đổi ô "Đơn hàng" thì
mọi màn có đơn đều đổi theo, không sót cửa phụ.

Bối cảnh: BR-PQ-35, R2. Thay `scope_orders_for`, `scope_invoices_for` và chỗ dùng `FULL_SCOPE_GROUPS` /
`has_full_delivery_scope` cho đơn bằng hàm phân giải PV-02. Một hàm cho mọi đường đọc: danh sách, chi tiết, tổng tiền
cuối danh sách, dòng thời gian, "Tiếp theo · Đã làm", lệnh "Nhờ", ⌘K, công cụ AI, xuất file. Ô tên/SĐT khách do PV-07 lo.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| PV-03-AC1 | G có D1 = `assigned_deliveries`, có 1 đơn có phiếu gán cho G và 1 đơn không | G gọi danh sách đơn | chỉ thấy đơn của mình; tổng số và tổng tiền chỉ tính đơn đó | BR-PQ-33, BR-PQ-35 |
| PV-03-AC2 | Chủ đổi D1 của G sang `all` (gọi thẳng service lưu, chưa cần PUT) | G gọi lại danh sách đơn **ngay request kế tiếp**, không đăng nhập lại | thấy cả 2 đơn | BR-PQ-36 |
| PV-03-AC3 | C có D1 = `assigned_or_confirmation` | C gọi danh sách đơn | thấy đơn có phiếu gán cho C **và** đơn trong phạm vi gọi xác nhận, không thấy đơn khác | BR-GH-18 |
| PV-03-AC4 (lỗi) | G có D1 = `assigned_deliveries`, đơn X ngoài phạm vi | G gọi chi tiết X, dòng thời gian X, "Tiếp theo" X, lệnh "Nhờ" trên X | tất cả trả **404**, không 403 | S-7 |
| PV-03-AC5 | Như AC4 | G tìm mã đơn X bằng ⌘K; hỏi Trợ lý AI về đơn X | không có kết quả X; AI trả lời như không có đơn | BR-PQ-35, S-3 |
| PV-03-AC6 | K có V1 bật, D1 = `assigned_deliveries` (Chủ đã thu hẹp) | K gọi danh sách và chi tiết hoá đơn bán | chỉ thấy hoá đơn của đơn trong phạm vi D1; hoá đơn khác → 404 | BR-PQ-37 |
| PV-03-AC7 (quyền) | Nhóm có D1 = `all` nhưng **tắt** `view_orders` | gọi danh sách đơn | 403 như hiện nay; phạm vi không cấp quyền xem | BR-PQ-34 |
| PV-03-AC8 (giá vốn) | K có D1 = `all`, không có `view_cost` | gọi chi tiết hoá đơn và đơn | không có `unit_cost` hay cột lãi lỗ nào | S-1, bất biến 1 |
| PV-03-AC9 | Test ảnh chụp PV-01 | chạy | xanh | BR-PQ-33 |

---

## PV-04 — Phiếu giao và Hàng hoàn đọc phạm vi từ cấu hình (D3, D5)  · Must · BE

**Là** Chủ vựa, **tôi muốn** chọn nhóm nào thấy mọi phiếu giao, phiếu hàng hoàn hay chỉ phiếu gán cho mình, **để** sắp
việc giao theo cách vựa đang chạy.

Bối cảnh: thay `delivery/api.py::get_queryset`, `inventory/returns/scope.py` và cửa sổ `delivery/pii_scope.py` (chỉ đổi
điều kiện "thấy hết" sang "phạm vi `all`", **không** đổi số ngày). Mặc định D3 của C là `assigned`, theo code; chữ trên
W3i "Trong phạm vi gọi" là sai và được sửa ở PV-11.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| PV-04-AC1 | G có D3 = `assigned`; phiếu P1 gán cho G, P2 gán người khác | G gọi danh sách phiếu giao, "Việc giao của tôi" | chỉ P1 | BR-GH-06, BR-PQ-33 |
| PV-04-AC2 | C có D3 = `assigned` (mặc định) | C gọi danh sách phiếu giao | chỉ phiếu gán cho C (khớp hiện trạng) | BR-PQ-33 |
| PV-04-AC3 | G có D5 = `assigned_deliveries`; phiếu hoàn R1 thuộc P1, R2 thuộc P2 | G gọi danh sách, chi tiết, dòng thời gian hàng hoàn; mở form tạo phiếu hoàn và xem danh sách phiếu giao được chọn | chỉ R1; chi tiết R2 → 404; form tạo chỉ cho chọn P1 | BR-PQ-35 |
| PV-04-AC4 (cửa sổ) | G có D3 = `assigned`, phiếu P1 đã kết thúc 8 ngày (cửa sổ 7 ngày) | G gọi chi tiết P1 | tên, SĐT, địa chỉ khách rỗng | SR-PII-02, S-4 |
| PV-04-AC5 (cửa sổ khi rộng) | Chủ đổi D3 của G sang `all` | G gọi chi tiết P2 đã kết thúc 8 ngày | thấy dữ liệu khách (nhóm ở "Tất cả" không bị cửa sổ, đúng như Q/K hôm nay) | SR-PII-02 |
| PV-04-AC6 (lỗi) | G có D3 = `assigned` | G gọi đổi trạng thái P2 | 404, P2 không đổi | S-7 |
| PV-04-AC7 (quyền) | Nhóm có D3 = `all` nhưng không có quyền xem phiếu giao | gọi danh sách | 403 | BR-PQ-34 |
| PV-04-AC8 | Test ảnh chụp PV-01 | chạy | xanh | — |

---

## PV-05 — Gọi xác nhận và Khách hàng đọc phạm vi từ cấu hình (D4, D7)  · Must · BE

**Là** Chủ vựa, **tôi muốn** phạm vi gọi xác nhận và danh bạ khách là ô tôi chọn, không gắn cứng với nhóm CSKH hay
danh sách tên nhóm, **để** có thể giao việc gọi cho người khác mà không sửa code.

Bối cảnh: thay `delivery/confirmation/scope.py` (phần `is_customer_service`), `sees_customer_directory`,
`CUSTOMER_DIRECTORY_GROUPS`. **Gom API khách cũ `/customers/` về cùng hàm phạm vi D7** với danh bạ mới (nợ đã ghi, 01-analysis §9).
D7 `assigned_deliveries` = khách của phiếu giao gán cho tôi, trong cửa sổ SR-PII-02.

Cách hiểu của PO cho D7 (xem câu hỏi PO-Q1): ô D7 chỉ sửa được khi nhóm bật "Xem khách hàng". Khi tắt, danh bạ đóng
(403 như hôm nay) và giá trị đã lưu được giữ.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| PV-05-AC1 | C có D4 = `pending_or_called_recently`; phiếu A đang chờ gọi, phiếu B C đã gọi 3 ngày trước, phiếu C' người khác gọi 3 ngày trước và đã xong | C gọi chi tiết A, B, C' | A, B → 200; C' → 404 | BR-GH-18 |
| PV-05-AC2 | Như AC1 | C gọi danh sách hàng chờ | dòng ngoài phạm vi chỉ có `phone_masked`, không có SĐT đầy đủ | S-7, bất biến 9 |
| PV-05-AC3 | Chủ bật `confirm_calls` cho K (D4 = `all_pending`) | K gọi chi tiết C' | 200 | BR-PQ-33 |
| PV-05-AC4 | G có `view_customers` bật, D7 = `assigned_deliveries` | G gọi danh bạ khách mới và `/customers/` cũ | cả hai trả **cùng một tập** khách: khách của phiếu gán cho G, trong cửa sổ | BR-PQ-35 |
| PV-05-AC5 | Q có `view_customers` bật, D7 = `all` | Q gọi danh bạ mới và `/customers/` cũ | cả hai trả mọi khách | #13 |
| PV-05-AC6 (lỗi) | G có D7 = `assigned_deliveries`, khách Z không thuộc phiếu nào của G | G gọi chi tiết Z, dòng thời gian Z, lọc đơn theo Z | 404 / danh sách rỗng | S-7 |
| PV-05-AC7 (quyền) | Nhóm tắt `view_customers` | gọi danh bạ | 403 như hôm nay, bất kể giá trị D7 đã lưu | BR-PQ-34 |
| PV-05-AC8 | grep code `backend/apps` | tìm `FULL_SCOPE_GROUPS`, `CUSTOMER_DIRECTORY_GROUPS`, `sees_customer_directory` | không còn (test tự động) | BR-PQ-33 |
| PV-05-AC9 | Test ảnh chụp PV-01 | chạy | xanh | — |

---

## PV-06 — Phiếu nhập theo phạm vi D6 (xem và sửa)  · Must · BE

**Là** Chủ vựa, **tôi muốn** chọn NV kho thấy và sửa mọi phiếu nhập, chỉ phiếu mình tạo, hay chỉ phiếu mình tạo trong
ngày, **để** áp đúng luật spec §1.6 khi tôi muốn, còn ngày đầu vẫn chạy như cũ.

Bối cảnh: #9, Q-3 (a) mặc định `all`, (b) áp cho cả xem lẫn sửa và gửi ghi nhận. "Trong ngày" = ngày lịch giờ VN
(`Asia/Ho_Chi_Minh`) của lúc tạo phiếu bằng ngày hôm nay giờ VN; DB lưu UTC. **Huỷ phiếu giữ luật cũ** (người tạo, hoặc
Quản lý/Chủ), không bị D6 chặn thêm và không được D6 mở thêm. Đây là lựa chọn mới hoàn toàn: phải có test ngày-giờ cố định.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| PV-06-AC1 | Sau migrate, K có D6 = `all`; phiếu do K1, K2, Q tạo | K1 gọi danh sách phiếu nhập | thấy cả 3 (khớp hiện trạng) | BR-PQ-33, Q-3a |
| PV-06-AC2 | Chủ đổi D6 của K sang `created_by_me` | K1 gọi danh sách; gọi chi tiết phiếu của K2 | danh sách chỉ phiếu của K1; chi tiết phiếu K2 → 404 | Q-3b |
| PV-06-AC3 | D6 của K = `created_by_me_today`; giờ VN 02/10 10:00; phiếu N1 K1 tạo 02/10 08:00 VN, N2 K1 tạo 01/10 23:50 VN | K1 gọi danh sách | chỉ N1 | spec §1.6 |
| PV-06-AC4 (qua nửa đêm) | Như AC3, N1 là Nháp, K1 mở lúc 02/10 23:59 VN | K1 gửi sửa N1 lúc 03/10 00:01 VN | 404, N1 không đổi và không mất; Quản lý vẫn thấy và sửa được N1 | UC-3, R5 |
| PV-06-AC5 (huỷ, luật cũ) | D6 của K = `created_by_me_today`; N2 Nháp do K1 tạo hôm qua | K1 gọi huỷ N2 | được huỷ (người tạo, luật cũ); AuditLog huỷ như hiện nay | BR-PQ-10 |
| PV-06-AC6 (huỷ, không mở thêm) | D6 của K = `all`; N3 do K2 tạo | K1 gọi huỷ N3 | bị chặn như hôm nay (không phải người tạo, không phải Q/Chủ) | BR-PQ-10 |
| PV-06-AC7 (giá vốn) | K có D6 = `all`, không có `view_cost` | K1 gọi danh sách và chi tiết phiếu do Q tạo | không có trường đơn giá mua (`rate`) hay `landed_unit_cost`; mở rộng test mẫu `inventory/batches/tests/test_api.py` cho phiếu nhập | S-1, BR-MH-06, R7 |
| PV-06-AC8 (quyền) | G không có quyền phiếu nhập, Chủ không đổi gì | G gọi danh sách phiếu nhập | 403 | BR-PQ-34 |
| PV-06-AC9 | Test ảnh chụp PV-01 | chạy | xanh | — |

---

## PV-07 — Hai việc mới: "Xem hoá đơn bán" (V1) và "Xem thông tin khách trên đơn & hoá đơn" (V2)  · Must · BE

**Là** Chủ vựa, **tôi muốn** bật/tắt riêng việc xem hoá đơn bán và việc xem tên, SĐT khách trên đơn và hoá đơn, **để**
quyết NV kho có cần biết khách là ai không, tách khỏi quyền lục cả danh bạ khách.

Bối cảnh: #12, Q-4, BR-PQ-37/38. Thêm V1, V2 vào registry B4 mục "Bán hàng" (không `owner_only`), `perms` rời các việc
khác. V2 cần permission mới và data migration bật cho Q, K, G, C. Thay điều kiện ở `sales/orders/serializers.py::pii_hidden`
và `sales/payments/serializers.py` (đang dựa `view_customer_list`) bằng V2 + phạm vi + cửa sổ. V2 **không** điều khiển
dữ liệu khách trên phiếu giao (D3 + cửa sổ lo phần đó).

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| PV-07-AC1 | Sau migrate | đọc ma trận nhóm | V1 bật đúng ở các nhóm đang có permission xem hoá đơn bán trước migrate; V2 bật ở Q, K, G, C; Chủ có cả hai | BR-PQ-32 |
| PV-07-AC2 (ngoại lệ đã duyệt) | Sau migrate, K có V1, V2, D1 = `all` | K gọi danh sách hoá đơn bán | ô tên khách **có giá trị** (trước đây rỗng). Đây là thay đổi duy nhất được phép trong ảnh chụp | BR-PQ-38, Q-4 |
| PV-07-AC3 | Chủ tắt V2 của K | K gọi danh sách đơn, chi tiết đơn, danh sách hoá đơn | tên và SĐT khách trả rỗng; mã đơn, trạng thái, tiền vẫn có | BR-PQ-38 |
| PV-07-AC4 (cửa sổ) | G có V2 bật, D1 = `assigned_deliveries`; đơn của phiếu đã kết thúc 8 ngày | G gọi chi tiết đơn đó | tên, SĐT rỗng | S-4, SR-PII-02 |
| PV-07-AC5 | Chủ tắt V1 của K | K gọi danh sách hoá đơn bán | 403 | BR-PQ-37 |
| PV-07-AC6 (Q-7) | Nhóm có V1 bật, `view_orders` tắt, D1 = `assigned_deliveries` | gọi danh sách hoá đơn | 200, dòng theo D1 | BR-PQ-37, Q-7 |
| PV-07-AC7 (quyền) | Chủ gọi PUT bật V2 cho nhóm `owner` | — | 400 `GROUP_LOCKED` | S-5 |
| PV-07-AC8 | Test registry B4 | chạy | `perms` của V1, V2 rời mọi việc khác; V2 không phải `owner_only` | BR-PQ-32 |
| PV-07-AC9 (API công khai) | V2 bật cho mọi nhóm | gọi tra đơn công khai trên Shop | vẫn chỉ SĐT đã che, không tên/địa chỉ đầy đủ | S-2 |

---

## PV-08 — Chủ lưu phạm vi, có AuditLog và dòng thời gian nhóm  · Must · BE

**Là** Chủ vựa, **tôi muốn** đổi phạm vi của một nhóm cùng lúc với bật/tắt việc, và mọi thay đổi đều để lại dấu vết,
**để** sau này tra được ai đã mở dữ liệu khách cho ai, lúc nào.

Bối cảnh: UC-2, BR-PQ-36, R6, R8. Mở rộng PUT B4 theo contract. Cả yêu cầu hợp lệ toàn bộ hoặc không đổi gì. AuditLog:
việc vẫn ghi `change_group_capabilities` như B4; phạm vi ghi action mới (đề xuất `change_group_data_scopes`), `changes`
**chỉ** chứa mã đối tượng và mã giá trị trước/sau, cộng cờ `customer_data_widening_confirmed` khi có mở rộng dữ liệu khách.
Không chép tên khách, SĐT, địa chỉ, không chép danh sách nhân viên bị ảnh hưởng.
(Kiểm xác nhận cảnh báo ở PV-09, kiểm `version` ở PV-10.)

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| PV-08-AC1 | Chủ, nhóm K có D6 = `all` | PUT `scopes: {"receipts": "created_by_me_today"}` với `version` đúng | 200; GET lại thấy giá trị mới và `version` mới; có đúng 1 AuditLog `change_group_data_scopes`, `changes = {"receipts": {"from": "all", "to": "created_by_me_today"}}`, actor = Chủ, object = nhóm K | BR-PQ-36 |
| PV-08-AC2 | Chủ gửi cùng lúc `capabilities` và `scopes` hợp lệ | PUT | cả hai cùng được áp; 1 AuditLog việc + 1 AuditLog phạm vi trong cùng giao dịch | BR-PQ-36 |
| PV-08-AC3 | Chủ gửi `scopes` có giá trị trùng giá trị đang lưu | PUT | 200, không ghi AuditLog phạm vi | — |
| PV-08-AC4 (lỗi) | Chủ gửi một khoá đúng và một giá trị sai (`"receipts": "mine"`) | PUT | 400 `SCOPE_VALUE_INVALID`; **không** khoá nào được lưu, không AuditLog | BR-PQ-36, S-8 |
| PV-08-AC5 (lỗi) | Chủ gửi `scopes: {"stock": "all"}` / `{"invoices": "all"}` / nhóm `owner` | PUT | 400 `SCOPE_OBJECT_UNKNOWN` / `SCOPE_READ_ONLY` / `GROUP_LOCKED`; không đổi gì | S-5, S-8 |
| PV-08-AC6 (AuditLog hỏng) | Giả lập ghi AuditLog ném lỗi | Chủ PUT hợp lệ | 500/400 theo mẫu BR-PQ-05, **cấu hình không đổi** | BR-PQ-05, BR-PQ-36 |
| PV-08-AC7 (quyền) | Quản lý có `manage_staff` gán trực tiếp; NV kho | PUT `scopes` | 403, không đổi gì, không AuditLog | R6, BR-PQ-36 |
| PV-08-AC8 | Đã có AuditLog AC1 | Chủ GET chi tiết nhóm K | `timeline` có sự kiện chữ "Lộc đổi phạm vi Phiếu nhập: Tất cả → Do tôi tạo trong ngày" (tên người theo actor thật), dựng từ mã, không lộ `changes` thô | UC-1 |
| PV-08-AC9 (dữ liệu cá nhân) | Mọi AuditLog do story này ghi | quét `changes` và `detail` | chỉ có mã đối tượng, mã giá trị, cờ boolean | bất biến 9 |
| PV-08-AC10 (hiệu lực ngay) | G đang đăng nhập, D1 = `assigned_deliveries` | Chủ PUT D1 = `all`, ngay sau đó G gọi danh sách đơn bằng token cũ | thấy mọi đơn; không cần đăng nhập lại | BR-PQ-36 |

---

## PV-09 — Cảnh báo kèm xác nhận khi mở rộng phạm vi dữ liệu khách  · Must · BE+FE

**Là** Chủ vựa, **tôi muốn** được báo rõ bao nhiêu người, những ai sẽ thấy thêm tên, SĐT, địa chỉ khách trước khi tôi
lưu, **để** không lỡ tay mở dữ liệu khách cho cả nhóm NV giao.

Bối cảnh: UC-2 bước 2, 2a, 2b; Q-6 (chỉ cảnh báo, không chặn); Q-9; R1 (Critical), R4. **Mở rộng dữ liệu khách** = một
trong D1, D3, D4, D5, D7 đổi sang giá trị có `rank` lớn hơn, **hoặc** bật V2. BE chặn ở PUT nếu thiếu xác nhận, nên FE
không thể bỏ qua cảnh báo. Thu hẹp không cần xác nhận nhưng hiện số dòng bị ảnh hưởng.

**BE**

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| PV-09-AC1 | Nhóm G có 2 thành viên đang hoạt động (Giao 1, Giao 2), D1 = `assigned_deliveries` | Chủ POST xem trước `scopes: {"orders": "all"}` | `widens_customer_data: true`, `affected_count: 2`, `affected_members` có 2 tên nhân viên, `message` "2 người trong nhóm sẽ thấy tên, SĐT, địa chỉ khách của mọi đơn."; không ghi gì vào DB | BR-PQ-36, R1 |
| PV-09-AC2 (chặn thiếu xác nhận) | Như AC1 | Chủ PUT không có `confirm_customer_data_widening` | 400 `CUSTOMER_DATA_WIDENING_UNCONFIRMED` kèm `impact`; không đổi gì | BR-PQ-36 |
| PV-09-AC3 | Như AC1 | Chủ PUT có `confirm_customer_data_widening: true` | 200; AuditLog phạm vi có `customer_data_widening_confirmed: true` | BR-PQ-36, R8 |
| PV-09-AC4 | Nhóm K tắt V2 | Chủ PUT bật V2 không xác nhận | 400 `CUSTOMER_DATA_WIDENING_UNCONFIRMED` | BR-PQ-38 |
| PV-09-AC5 (thu hẹp) | K có D6 = `all`; có 3 phiếu nhập Nháp do Q tạo mà K đang thấy | Chủ POST xem trước D6 = `created_by_me` | `widens_customer_data: false`, `narrowed` có `rows_losing_access: 3`; PUT không cần xác nhận | Q-9 |
| PV-09-AC6 (kiêm nhiệm) | Giao 2 thuộc cả G và K; K có D1 = `all` | Chủ POST xem trước D1 của G = `assigned_deliveries` | `already_wider_elsewhere` có Giao 2, `via_group: warehouse_staff` | R4, UC-2 2b |
| PV-09-AC7 (D6 không phải dữ liệu khách) | K có D6 = `created_by_me` | Chủ PUT D6 = `all` không xác nhận | 200 | — |
| PV-09-AC8 (quyền) | Quản lý, NV kho | POST xem trước | 403 | R6 |
| PV-09-AC9 (dữ liệu cá nhân) | Mọi phản hồi xem trước | kiểm body | không có tên, SĐT, địa chỉ của khách | bất biến 9 |

**FE** (W3i, mock theo contract POST xem trước)

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| PV-09-AC10 | Chủ đổi D1 của G sang "Tất cả đơn" | bấm "Lưu thay đổi" | trước khi gửi PUT, hiện hộp cảnh báo: câu `message`, danh sách tên nhân viên, gợi ý "Người đã nghỉ thì khoá tài khoản"; hai nút "Huỷ" và "Tôi hiểu, lưu" | R1, BR-PQ-01 |
| PV-09-AC11 | Hộp cảnh báo đang mở | bấm "Huỷ" | không gửi PUT; ô vẫn giữ giá trị Chủ vừa chọn để sửa tiếp | — |
| PV-09-AC12 | Hộp cảnh báo đang mở | bấm "Tôi hiểu, lưu" | gửi PUT với `confirm_customer_data_widening: true`; thành công thì báo "Đã lưu" | BR-PQ-36 |
| PV-09-AC13 (thu hẹp) | Chủ đổi D6 của K sang "Do tôi tạo" và có 3 dòng bị ảnh hưởng | bấm "Lưu thay đổi" | hiện ghi chú "3 phiếu đang làm dở sẽ không còn hiện với nhóm này. Quản lý và Chủ vẫn thấy." kèm nút xác nhận; không có chữ cảnh báo dữ liệu khách | Q-9 |
| PV-09-AC14 (kiêm nhiệm) | `already_wider_elsewhere` khác rỗng | hộp xác nhận mở | hiện dòng "Giao 2 vẫn thấy tất cả nhờ nhóm NV kho" | R4 |
| PV-09-AC15 (lỗi) | PUT trả 400 `CUSTOMER_DATA_WIDENING_UNCONFIRMED` (ví dụ xem trước lỗi mạng nên FE bỏ qua bước xem trước) | — | FE mở hộp cảnh báo bằng `impact` trong body lỗi, không mất lựa chọn | BR-PQ-36 |
| PV-09-AC16 (truy cập) | Hộp cảnh báo mở | dùng bàn phím | focus vào hộp, Esc = Huỷ, Tab không thoát ra ngoài hộp, nút chính có nhãn đầy đủ | — |

---

## PV-10 — Hai người cùng lưu một nhóm: người sau không ghi đè  · Must · BE+FE

**Là** Chủ vựa (hoặc Duy cùng sửa một lúc), **tôi muốn** khi người khác vừa đổi nhóm này thì lần lưu của tôi bị dừng và
tôi được báo, **để** không vô tình xoá thay đổi của người kia.

Bối cảnh: UC-2 ngoại lệ, Q-8. Dùng `version` trong GET/PUT. Áp cho **mọi** lần lưu của nhóm (việc lẫn phạm vi), vì cùng
một nút "Lưu thay đổi". Lô 14 FE nếu đã gửi PUT không có `version` thì phải cập nhật cùng story này.

**BE**

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| PV-10-AC1 | Chủ (phiên A) và Duy (phiên B) cùng GET nhóm K, `version = "41"` | A PUT với `"41"` → 200 (`version` thành `"42"`); sau đó B PUT với `"41"` | B nhận **409 `GROUP_CHANGED`**; cấu hình giữ đúng thay đổi của A; không AuditLog cho B | Q-8 |
| PV-10-AC2 | Như AC1 nhưng A chỉ đổi **việc**, B chỉ đổi **phạm vi** | B PUT với `version` cũ | vẫn 409 (cùng nhóm) | Q-8 |
| PV-10-AC3 | A lưu nhóm K, B lưu nhóm G với `version` riêng của G | B PUT | 200 (khác nhóm không xung đột) | — |
| PV-10-AC4 (lỗi) | PUT không có `version` | — | 400 `INVALID_INPUT`, không đổi gì | — |
| PV-10-AC5 (đồng thời thật) | Hai PUT cùng `version` chạy song song (test luồng/khoá dòng) | — | đúng một 200, một 409 | Q-8 |

**FE**

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| PV-10-AC6 | Chủ đang sửa W3i nhóm K | PUT trả 409 `GROUP_CHANGED` | hiện thông báo "Nhóm này vừa được người khác đổi. Tải lại để xem bản mới." với nút "Tải lại"; **không** tự gửi lại | Q-8 |
| PV-10-AC7 | Thông báo 409 đang hiện | bấm "Tải lại" | GET lại, hiện giá trị mới nhất; các ô Chủ vừa sửa trở về giá trị server (không trộn) | Q-8 |
| PV-10-AC8 | Mọi lần PUT từ W3i | — | luôn gửi `version` lấy từ lần GET gần nhất | — |

---

## PV-11 — Màn W3i: khối "Phạm vi dữ liệu" sửa được  · Must · FE

**Là** Chủ vựa, **tôi muốn** thấy và đổi phạm vi của mỗi nhóm ngay trong màn chi tiết nhóm quyền, cạnh danh sách việc,
**để** chỉnh quyền một chỗ, lưu một lần.

Bối cảnh: UC-1, UC-4, thiết kế `doc/design/erp/screens/ERP-W3i-Chi-tiet-nhom-quyen.dc.html` (khối hiện có các dòng Đơn
hàng, Khách hàng, Phiếu giao, Phiếu nhập, Nhật ký hoạt động dạng chữ chỉ đọc). Story này đổi khối đó thành ô chọn, thêm
dòng Hoá đơn bán, Gọi xác nhận, Hàng hoàn. Code ở `erp-console/features/staff/`. Dựng mock theo contract GET để làm song
song với BE. Phụ thuộc màn W3i của Lô 14 (FE) đã có. V1, V2 tự hiện trong danh sách việc mục "Bán hàng" vì đọc từ
`registry`.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| PV-11-AC1 | Chủ mở W3i nhóm K | màn tải xong | khối "Phạm vi dữ liệu" có 8 dòng theo thứ tự D1…D8; D1, D3–D7 là ô chọn đúng `options`; D2 ghi "Theo Đơn hàng"; D8 ghi "Tất cả"/"Không xem" theo việc, chỉ đọc | UC-1 |
| PV-11-AC2 | Dòng có `inactive_reason` | xem | ô mờ, không chọn được, hiện chữ `inactive_reason` (ví dụ "Không xem — bật việc \"Xem đơn\" trước"); giá trị cũ vẫn hiện | BR-PQ-34, Q-7 |
| PV-11-AC3 | Chủ bật việc "Xem đơn" trong cùng màn (chưa lưu) | — | ô Đơn hàng hết mờ ngay trên màn, chọn được | — |
| PV-11-AC4 | Chủ đổi một ô phạm vi và một việc | bấm "Lưu thay đổi" (nút đang có của B4) | gửi **một** PUT có cả `capabilities` và `scopes` (chỉ khoá đã đổi) và `version`; xong thì nút về trạng thái không có thay đổi | BR-PQ-36 |
| PV-11-AC5 | Có ô đã đổi chưa lưu | bấm "Huỷ thay đổi" hoặc rời trang | ô trở về giá trị server / hỏi xác nhận rời trang như phần việc của B4 | — |
| PV-11-AC6 | Chủ mở W3i nhóm Chủ | — | mọi dòng "Tất cả", khoá, chữ "Chủ luôn thấy tất cả" | S-5 |
| PV-11-AC7 | Chủ mở W3i nhóm CSKH | — | dòng Phiếu giao hiện "Phiếu gán cho tôi" (không còn chữ sai "Trong phạm vi gọi") | UC-5 |
| PV-11-AC8 (lỗi) | PUT trả 400 `SCOPE_VALUE_INVALID` hoặc lỗi mạng | — | hiện thông điệp tiếng Việt từ server cạnh nút Lưu; các ô giữ lựa chọn; không báo "Đã lưu" | — |
| PV-11-AC9 (quyền) | Quản lý mở W3i (có quyền đọc B4) | — | khối phạm vi chỉ đọc, không có ô chọn, không có nút lưu phạm vi | BR-PQ-36 |
| PV-11-AC10 | Có sự kiện đổi phạm vi trong `timeline` | xem dòng thời gian nhóm | hiện câu sự kiện như PV-08-AC8 | UC-1 |
| PV-11-AC11 (truy cập, hiển thị) | Màn rộng 375px và 1280px | xem và dùng bàn phím | mỗi ô chọn có nhãn đọc được bằng trình đọc màn hình (tên đối tượng), Tab đi đúng thứ tự, không tràn ngang ở 375px | — |
| PV-11-AC12 (dữ liệu cá nhân) | Mở DevTools | xem `localStorage`, URL, console | không lưu cấu hình hay tên nhân viên vào `localStorage`/URL; không log body | bất biến 9 |

---

## PV-12 — Cổng phát hành: ảnh chụp sau chuyển đổi, quét endpoint và sàn cứng  · Must · BE

**Là** Chủ vựa, **tôi muốn** một bộ test cuối khẳng định không ai đổi phạm vi ngoài ý muốn và mọi cửa phụ đều theo cấu
hình, **để** yên tâm bật tính năng trên production.

Bối cảnh: UC-5 bước 3 và ngoại lệ, R2, R3, các sàn S-1 … S-7. Chạy khi PV-02 … PV-08 đã gộp. Lệch → không phát hành.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| PV-12-AC1 | Toàn bộ code mới, cấu hình mặc định sau migrate | chạy test ảnh chụp PV-01 | xanh, ngoại lệ duy nhất là PV-01-AC3 | UC-5, R3 |
| PV-12-AC2 (quét endpoint) | Với **mỗi** đối tượng D1, D3–D7 và **mỗi** giá trị phạm vi của nó | đặt giá trị cho nhóm G, gọi mọi endpoint của đối tượng (danh sách, chi tiết, tổng, dòng thời gian, "Tiếp theo", ⌘K, AI, xuất file) bằng token G | tập id ở mọi endpoint **bằng nhau** và bằng tập do hàm phạm vi trả | BR-PQ-35, R2 |
| PV-12-AC3 (S-1) | Mọi nhóm khác Chủ đặt mọi phạm vi rộng nhất, không có `view_cost`/`view_profit` | gọi mọi endpoint ở AC2 và phiếu nhập | không có trường giá vốn, đơn giá mua, lãi lỗ | S-1, bất biến 1 |
| PV-12-AC4 (S-2) | Như AC3 | gọi tra đơn công khai và API Shop | không có tên, SĐT, địa chỉ đầy đủ | S-2 |
| PV-12-AC5 (S-3) | Như AC3, bật log mức DEBUG | gọi PUT, xem trước và các endpoint | log và AuditLog không chứa tên/SĐT/địa chỉ giả của fixture; ngữ cảnh gửi cho AI không thêm trường dữ liệu khách so với trước | S-3, bất biến 9 |
| PV-12-AC6 (S-4) | Nhóm G có mọi phạm vi hẹp nhất | gọi chi tiết phiếu giao/đơn đã kết thúc quá cửa sổ | dữ liệu khách rỗng; không có khoá nào trong PUT đổi được số ngày cửa sổ | S-4 |
| PV-12-AC7 (S-6) | Mọi phạm vi rộng nhất | gọi DELETE trên đơn, hoá đơn, phiếu nhập, AuditLog; POST tạo đơn/hoá đơn tay | 405/403 như hôm nay | S-6, BR-PQ-10/11 |
| PV-12-AC8 (grep) | Mã nguồn `backend/apps` | quét | không còn chỗ quyết phạm vi dòng bằng tên nhóm (danh sách tên hằng ở Mục tiêu §2); `GROUP_SCOPES` cố định đã bỏ | BR-PQ-33 |
| PV-12-AC9 | Chạy toàn bộ `manage.py test`, `tsc --noEmit`, build `erp-console`, `scripts/check_naming.py` | — | đều xanh | DoD |

---

## PV-13 — Báo rõ khi mất quyền xem giữa chừng  · Should · FE

**Là** NV kho (hoặc NV giao, CSKH), **tôi muốn** được báo rõ khi một mục tôi đang mở không còn trong phạm vi của tôi,
**để** không tưởng app lỗi và biết phải nhờ ai.

Bối cảnh: UC-3 ngoại lệ. Should vì BE đã chặn đúng (404); đây là trải nghiệm. Áp cho chi tiết Đơn hàng, Hoá đơn bán,
Phiếu giao, Hàng hoàn, Phiếu nhập, Khách hàng, Gọi xác nhận.

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| PV-13-AC1 | NV kho đang mở chi tiết phiếu nhập; Chủ thu hẹp D6 | NV kho bấm Lưu hoặc tải lại | màn hiện "Bạn không còn quyền xem mục này." và nút về danh sách; không trắng trang, không văng lỗi đỏ | UC-3 |
| PV-13-AC2 | Như AC1 với D6 = `created_by_me_today`, phiếu là của chính NV kho, tạo hôm qua | — | câu báo thêm "Phiếu tạo từ hôm trước. Nhờ Quản lý xử lý tiếp." | spec §1.6, R5 |
| PV-13-AC3 | Danh sách đang mở; phạm vi bị thu hẹp | bấm trang kế hoặc làm mới | danh sách ngắn lại theo phạm vi mới, không lỗi | UC-3 |
| PV-13-AC4 (lỗi khác) | Server trả 500 | — | vẫn hiện thông báo lỗi chung hiện có, **không** dùng câu "không còn quyền" | — |
| PV-13-AC5 (dữ liệu cá nhân) | Màn báo mất quyền | xem DOM và console | không còn tên/SĐT/địa chỉ khách của mục cũ trên màn hay trong console | bất biến 9 |

---

## PV-14 — "Quyền của tôi" hiện phạm vi dữ liệu của mình  · Should · BE+FE

**Là** Quản lý (hoặc NV kho, NV giao, CSKH), **tôi muốn** xem mình đang thấy những dữ liệu nào, **để** biết vì sao một
đơn hay phiếu không hiện với mình.

Bối cảnh: 01-analysis §4 (Quản lý xem phạm vi ở "Quyền của tôi"), §7 (`/api/auth/me/` chỉ thêm key, S47). Should vì không
chặn việc chính.

Contract: `/api/auth/me/` thêm key

```json
"data_scopes": [
  {"key": "orders", "label": "Đơn hàng", "value": "all", "value_label": "Tất cả đơn", "via_group": "warehouse_staff"},
  {"key": "receipts", "label": "Phiếu nhập", "value": "created_by_me_today", "value_label": "Do tôi tạo trong ngày", "via_group": "warehouse_staff"}
]
```

| Mã | Given | When | Then | BR |
|---|---|---|---|---|
| PV-14-AC1 | Người K+G, K có D1 = `all`, G có D1 = `assigned_deliveries` | GET `/api/auth/me/` | `orders.value = "all"`, `via_group = "warehouse_staff"` (phạm vi hiệu lực rộng nhất) | BR-PQ-34 |
| PV-14-AC2 | Người không nhóm | GET `/api/auth/me/` | mọi dòng giá trị hẹp nhất, `via_group: null` | UC-6 |
| PV-14-AC3 | Đối tượng mà người đó không có quyền xem | GET | dòng đó `value: "none"` hoặc không có trong danh sách (Tech Lead chốt, ghi 02b); không tiết lộ thêm gì | BR-PQ-34 |
| PV-14-AC4 (FE) | NV giao mở "Quyền của tôi" | — | thấy khối "Dữ liệu bạn xem được" liệt kê nhãn đối tượng và `value_label`, chỉ đọc | — |
| PV-14-AC5 (quyền) | NV giao | gọi GET chi tiết nhóm khác `/api/staff/groups/manager/` | 403 (không lộ cấu hình nhóm khác) | BR-PQ-32 |
| PV-14-AC6 | Các key cũ của `/api/auth/me/` | so trước/sau | không key cũ nào đổi tên hay kiểu | S47 |

---

## Thứ tự làm đề xuất

```
PV-01 (mốc ảnh chụp, trên code cũ)
  → PV-02 (cấu hình + hàm phân giải + GET)           ┐
       → PV-03 → PV-04 → PV-05 → PV-06 → PV-07 (BE)  │  FE song song từ khi có contract:
       → PV-08 (PUT + AuditLog)                      │  PV-11 (W3i, mock) → PV-09 FE → PV-10 FE
       → PV-09 BE, PV-10 BE                          ┘  → PV-13, PV-14 FE
  → PV-12 (cổng phát hành)  → PV-14 BE (Should)
```

Lý do:
- PV-01 phải chạy trên code **cũ** mới có mốc thật. Làm sau là mất mốc.
- PV-03 … PV-07 mỗi story đụng một cụm file riêng (orders/payments · delivery/returns · confirmation/customers ·
  purchasing · registry/serializers), nên nếu BE có hai người thì chia được, miễn mỗi story giữ PV-01 xanh. PV-03 nên làm
  đầu vì hàm `has_full_delivery_scope` được dùng chung nhiều nhất.
- PV-08 cần PV-02. PV-09, PV-10 cần PV-08.
- FE chỉ cần contract ở mục "Contract chung" để dựng mock. PV-11 phụ thuộc màn W3i của Lô 14 FE.
- PV-12 là cổng, chạy cuối. PV-13, PV-14 là Should, làm sau nếu thời gian cho phép, không chặn phát hành.

Gợi ý chia lô cho 02c (Tech Lead chốt): Lô A = PV-01, PV-02 · Lô B = PV-03 … PV-07 · Lô C = PV-08, PV-09, PV-10 (BE ∥ FE)
cùng PV-11 · Lô D = PV-12 · Lô E (Should) = PV-13, PV-14.

## Ma trận phủ use case

| Use case / ngoại lệ | Story |
|---|---|
| UC-1 xem phạm vi | PV-02, PV-11 |
| UC-2 đổi phạm vi; cảnh báo; thu hẹp; kiêm nhiệm; 400; xung đột; AuditLog hỏng | PV-08, PV-09, PV-10 |
| UC-3 làm việc trong phạm vi; 404; mất quyền giữa chừng; qua nửa đêm | PV-03 … PV-06, PV-13 |
| UC-4 V1, V2 | PV-07, PV-09 (V2 là mở rộng dữ liệu khách) |
| UC-5 chuyển đổi, ảnh chụp, ngoại lệ V2 hoá đơn NV kho, sửa chữ CSKH | PV-01, PV-07-AC2, PV-11-AC7, PV-12 |
| UC-6 không nhóm / thiếu cấu hình | PV-02-AC4, PV-14-AC2 |
| Sàn S-1 … S-8 | PV-12 (kèm AC riêng trong PV-03, PV-06, PV-07, PV-08) |

## Việc tài liệu (không phải story dev) — PO đề xuất, điều phối viên áp sau khi Duy duyệt file này

PO chỉ ghi trong `doc/features/`, nên không tự sửa spec. Các chỗ cần sửa:

**1. `doc/business-process-spec.md` §1.6, dòng `warehouse_staff` trên PurchaseReceipt (theo Q-3, Duy chốt 02/10):**

Hiện tại:

> `| \`warehouse_staff\` trên PurchaseReceipt | Chỉ sửa phiếu do chính mình tạo, **trong ngày**; qua ngày phải nhờ Quản lý |`

Thay bằng:

> `| Phiếu nhập (PurchaseReceipt), mọi nhóm có việc "Nhập lô tại cảng" | Theo ô phạm vi **Phiếu nhập** của nhóm trong màn Phân quyền (BR-PQ-33, D6): Tất cả phiếu · Do tôi tạo · Do tôi tạo trong ngày (ngày giờ VN). Áp cho **xem, sửa và gửi ghi nhận**. **Mặc định: Tất cả phiếu** (Duy 02/10, Q-3). Huỷ phiếu giữ luật cũ: người tạo, hoặc Quản lý/Chủ. Nếu Chủ chọn "trong ngày" thì qua ngày phải nhờ Quản lý. Cột đơn giá mua vẫn chỉ theo "Xem giá vốn" (§1.7). |`

**2. Cùng §1.6, câu mở bảng:** thêm một câu sau "(lọc trong `get_queryset()`, không phải ẩn ở giao diện)":
"Từ 02/10/2026, phạm vi dòng là **cấu hình theo nhóm × đối tượng** trong màn Phân quyền (BR-PQ-33 … BR-PQ-38). Các dòng
dưới đây là **giá trị mặc định**, Chủ đổi được; sàn cứng xem hồ sơ `2026-10-02-pham-vi-du-lieu-cau-hinh` 01-analysis §6.2."

**3. §1.4 bảng CRUD:** ô `warehouse_staff` × PurchaseReceipt giữ `CRU–*`; ô `warehouse_staff` × SalesInvoice `R*` nay
hiểu là "theo việc Xem hoá đơn bán (V1) và phạm vi Đơn hàng". Đề xuất thêm chú thích dưới bảng: "\* phạm vi cấu hình được, xem 1.6".

**4. BR-MH-06** đang ghi "NV kho nhập được nhưng không xem lại được phiếu của người khác (xem 1.6)". Với mặc định D6 =
"Tất cả", NV kho **xem được** phiếu của người khác nhưng **không thấy đơn giá** (S-1). Đề xuất sửa thành: "Đơn giá mua là
field nhạy cảm — NV kho nhập được nhưng không xem lại được đơn giá (chỉ người có 'Xem giá vốn'). Phiếu của người khác hiện
hay không theo phạm vi Phiếu nhập (1.6)." Cần Duy xác nhận (câu PO-Q3).

**5. Thêm BR-PQ-33 … BR-PQ-38** vào §1 của spec, nguyên văn bảng 01-analysis §6.1; sửa BR-PQ-32 (thêm V1, V2) và
BR-GH-18 (nguồn luật là D1/D4, không gắn tên nhóm `customer_service`).

**6. `doc/decisions.md`** (Q-10): điều phối viên đề nghị Duy ghi "02/10/2026 — Tầng 3 cấu hình theo nhóm × đối tượng;
ba tầng giữ nguyên; sàn cứng S-1 … S-8 không cấu hình." PO không sửa file này.

## Rủi ro / phụ thuộc

- **Phụ thuộc Lô 14** (`2026-10-01-erp-theo-design`, 02c còn ☐): BE B4 (`capabilities/`) và màn W3i FE phải có trước
  PV-02 và PV-11. Nếu Lô 14 FE chưa gửi `version`, PV-10 sửa luôn.
- **R1 (Critical)** chặn bằng PV-09 (BE bắt buộc xác nhận) và PV-08 (AuditLog).
- **R2, R3** chặn bằng PV-01 + PV-12. PV-01 làm sai mốc thì mọi thứ sau mất tác dụng: QA kiểm PV-01 kỹ nhất.
- **Bảng mới** (bất biến 8): Tech Lead ghi lý do và migration trong 02b.
- Hiệu năng (R9): đọc cấu hình mỗi request; Tech Lead đo một lần trên danh sách đơn, ghi số vào 03-dev-notes.

## Để sau

- Cột tóm tắt phạm vi trên W3h (Q-11).
- Phạm vi cho kiểm kê, lô, sổ nhập xuất, nhà cung cấp (Q-12).
- Phạm vi theo từng người; ẩn/hiện cột tuỳ ý.
- Chỉnh số ngày cửa sổ dữ liệu khách trên màn (S-4, Q-5 giữ khoá).

## Definition of Done (chung)

Test BE xanh (`manage.py test`), `erp-console` `tsc --noEmit` và build sạch, `scripts/check_naming.py` xanh, QA report
APPROVED (không PASS bằng đọc code, có ca ngoài đường thuận), không rò giá vốn, không rò dữ liệu cá nhân, test ảnh chụp
PV-01 xanh, spec cập nhật theo mục "Việc tài liệu".

## Câu hỏi cho Duy

| # | Câu hỏi | PO tạm chọn (dùng nếu Duy không trả lời khác) |
|---|---|---|
| PO-Q1 | Khi Chủ **bật** "Xem khách hàng" cho một nhóm mà ô Khách hàng (D7) của nhóm đó đang "Không xem", nhóm thấy gì? | Màn tự đặt D7 = "Tất cả khách" trong cùng lần lưu (giữ đúng hành vi hôm nay và #13), kèm cảnh báo dữ liệu khách PV-09. Chủ đổi sang hẹp hơn được trước khi lưu. BE từ chối tổ hợp "Xem khách hàng bật + D7 Không xem" bằng 400 `SCOPE_VALUE_INVALID`. |
| PO-Q2 | Phiếu nhập "Do tôi tạo trong ngày": NV kho có còn **huỷ** được phiếu Nháp của chính mình từ hôm trước không? 01-analysis ghi "huỷ giữ luật cũ" (người tạo được huỷ). | Có (PV-06-AC5), đúng câu chữ 01-analysis. Màn chỉ không hiện phiếu đó trong danh sách; Quản lý vẫn xử lý được. |
| PO-Q3 | Sửa câu chữ BR-MH-06 như mục "Việc tài liệu" 4? | Sửa như đề xuất. |

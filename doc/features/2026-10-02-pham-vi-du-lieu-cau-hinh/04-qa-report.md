# QA — Phạm vi dữ liệu cấu hình
> qa-tester · nhánh `feat/pham-vi-du-lieu` HEAD eb7fd92. Mọi dữ liệu là dữ liệu giả (`seed_demo` + tài khoản `qa_*`); DB SQLite tạm, đã xoá.

## QA Lô 1–2 BE (06/10)

### Kết luận: APPROVED — lô không đổi hành vi (357 lời gọi API giống hệt main), migration an toàn trên DB có dữ liệu, H1 đã đóng.
### Tổng: 14 ca · ✅ 14 · ❌ 0 · ⏸ 0 (chỉ BE; FE ngoài phạm vi lô này)

| # | Ca | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | Migrate 0013 → head, kịch bản A (mặc định): quyền 5 nhóm không đổi | ✅ | `PERMS IDENTICAL` (so `auth_group_permissions` trước/sau). owner 149, manager 70, warehouse_staff 36, delivery_staff 9, customer_service 4 |
| 2 | Kịch bản B (Chủ đã đổi qua B4: tắt `view_customer_list` của Quản lý; bật cho NV giao và CSKH; tắt `view_salesorder` của NV kho): quyền không đổi, D7 đúng theo quyền lúc migrate | ✅ | `PERMS IDENTICAL`; D7: manager `none`, warehouse_staff `none`, delivery_staff `all`, customer_service `all`. Kịch bản A: manager `all`, warehouse_staff `none`, delivery_staff `assigned_deliveries`, customer_service `none` |
| 3 | Số dòng | ✅ | `config rows 5 scope rows 24` ở cả A và B (owner 0 dòng; 4 nhóm × 6) |
| 4 | Lùi `migrate accounts 0013` rồi tiến lại | ✅ | `Unapplying 0015 OK`, `Unapplying 0014 OK`, bảng mất, quyền y nguyên (`PERMS IDENTICAL after rollback`), tiến lại 5/24; `makemigrations --check` = `No changes detected` |
| 5 | Ngoài đường thuận: thiếu nhóm `customer_service` lúc migrate; dòng đã có sẵn giá trị khác | ✅ | `cfg 4 scopes 18`, không lỗi; dòng `warehouse_staff.orders=none` tạo trước vẫn giữ `none` (không ghi đè) |
| 6 | `GET /api/staff/groups/` + `/<code>/` theo vai (runserver thật, đăng nhập token) | ✅ | Chưa đăng nhập 401; manager, warehouse_staff, delivery_staff, customer_service 403 (cả mã nhóm không tồn tại: 403, không lộ); owner 200; mã lạ 404 `GROUP_NOT_FOUND`. Quyền đọc (`CanManageStaff`) như cũ |
| 7 | Đúng contract §2.2 | ✅ | Danh sách: mỗi nhóm có `version`, `data_scope_values` 6 khoá. Chi tiết: `version`, `data_scope_values`, `data_scopes` 8 dòng (orders, invoices, deliveries, confirmation, returns, receipts, customers, audit_log), mỗi dòng đủ `key,label,value,editable,customer_data,gate_capability,inactive_reason,note,options[{value,label,rank}]`; rank 0 duy nhất mỗi đối tượng |
| 8 | Không giá vốn, không dữ liệu cá nhân trong response | ✅ | grep `rate, landed, unit_cost, purchase, phone, address, customer_name` = không có. Chữ `profit` chỉ là khoá năng lực `view_profit` (on/off). `members` (username nhân viên) đã có ở main, không phải khách |
| 9 | Hồi quy: 357 lời gọi GET (7 danh tính × đơn, khách, danh bạ khách, phiếu giao, gọi xác nhận, hoá đơn, hoàn tiền, hàng hoàn, phiếu nhập, dashboard, `?assigned_to=me`, `?q=`, `?customer=`, chi tiết từng id, timeline) giữa main và nhánh trên cùng dữ liệu | ✅ | Sau chuẩn hoá chữ tiền ("đ" ở main, "₫" ở nhánh) và `as_of`: **0 lệch**, 357/357 trùng cả mã trạng thái lẫn thân JSON. Phân bố: 200×132, 403×104, 404×69, 401×45, 405×6, 400×1. NV giao 2 không thấy phiếu/đơn/khách của NV giao 1 (404); CSKH 403 ở phiếu giao như cũ |
| 10 | H1: NV giao được bật "Xem khách hàng", D7 = `all`, rồi tắt quyền | ✅ | Resolver: mặc định `assigned_deliveries` → bật+`all` = `all` → **tắt quyền (D7 vẫn lưu `all`) = `assigned_deliveries`** → bật lại = `all` |
| 11 | Ngoài đường thuận: người K+G (NV kho + NV giao, K không có `view_customer`) | ✅ | customers `assigned_deliveries` (không mượn `all`), orders `all` (đúng: K có quyền xem đơn) |
| 12 | Ngoài đường thuận: không nhóm / ẩn danh / giá trị lưu hỏng / mất dòng / owner | ✅ | Không nhóm và ẩn danh: toàn rank 0; `orders='garbage'` → `assigned_deliveries`; mất dòng receipts → `created_by_me_today`; owner toàn rộng nhất. Trùng (nhóm, đối tượng) bị `IntegrityError` |
| 13 | API phản ánh DB sống, không nhớ cũ; PUT ghi vẫn bị chặn | ✅ | Sau khi sửa DB: `version 7`, ô mờ có `inactive_reason` khi tắt `view_salesorder`, giá trị hỏng hiển thị rank 0. POST/PUT/PATCH/DELETE `/groups/<code>/` = 405; PUT `/capabilities/` kèm `data_scope_values` = 400 `INPUT_NOT_ALLOWED`, DB không đổi |
| 14 | Test suite | ✅ | `manage.py test apps.accounts` = 415 test OK (gồm 9 test mốc PV-01, 59 test PV-02). Ghi chú môi trường: thiếu symlink `backend/staticfiles` thì 5 test admin lỗi manifest, không liên quan lô. `check_naming.py`: OK. Server đã tắt, symlink và DB tạm đã gỡ |

### Phân quyền (đọc `/api/staff/groups/`)
| Vai | Danh sách | Chi tiết |
|---|---|---|
| Chưa đăng nhập | 401 | 401 |
| owner | 200 | 200 |
| manager, warehouse_staff, delivery_staff, customer_service | 403 | 403 |

Rò giá vốn: không. Rò dữ liệu cá nhân: không (API, log server: 0 Traceback, không có tên, SĐT hay mật khẩu; module mới không có `logger` hay `print`). Hồi quy: ca 9.

### Quan sát (không chặn)
- **O1 (Low, đã biết là nợ L4 Lô 5):** D7 lưu `all` mà nhóm thiếu `view_customer_list`: API hiển thị `value: "all"`, `note: null`, trong khi giá trị hiệu lực là `assigned_deliveries`. Chưa có FE dùng; Lô 5 phải thêm `note`.
- **O2 (Low, đã ghi ở 03-dev-notes lệch #3):** `scopes` cũ của CSKH đổi nhãn ("Trong phạm vi gọi" → "Được gán hoặc trong phạm vi gọi xác nhận" cho đơn, "Được gán" cho phiếu giao). Đây là nhãn hiển thị, không phải quyền: ca 9 chứng minh hành vi truy cập y nguyên. Mock FE cần đồng bộ (L3).
- **O3:** main đã tiến sau điểm tách nhánh: chữ tiền ở dòng thời gian main là "đ", nhánh còn "₫". Không phải do lô này; sẽ tự khớp khi merge.
- Người không nhóm có quyền gán trực tiếp bị rank 0 ở nhiều đối tượng (R9/D-3): chưa có đường đọc nào dùng resolver nên chưa đổi hành vi; cần đếm trên production trước Lô 3.

## Lệnh đã chạy (rút gọn)
- Mỗi kịch bản: `DATABASE_URL=sqlite:///.../migX.sqlite3 manage.py migrate accounts 0013`, migrate từng app khác tới head (để các migration cấp quyền của app khác chạy trước mốc), seed kịch bản B, chụp `auth_group_permissions`, `manage.py migrate`, chụp lại, `cmp`.
- Lùi/tiến: `migrate accounts 0013` → `migrate`; `makemigrations --check --dry-run`.
- Hồi quy: script `APIClient.force_authenticate` chạy trên main (`/backend`) và nhánh, DB main sao chép rồi `migrate` ở nhánh; so JSON.
- API thật: `runserver 8765 --noreload` + `curl` với token của 5 vai.
- H1: `manage.py shell` gọi `resolver.resolve_data_scopes`.
- `manage.py test apps.accounts` (415 OK), `python3 scripts/check_naming.py` (OK).

---

## QA Lô 3 BE (07/10)

> qa-tester · nhánh `feat/pham-vi-du-lieu` HEAD `c891364` (code Lô 3 = `30bbc87`). Chỉ BE; FE Lô 7 ngoài phạm vi. Mọi dữ liệu là dữ liệu giả
> (bộ `data_scopes/tests/fixtures.py`: "Khách Giả NN", SĐT `09000001NN`). Hai máy chủ `runserver` thật (SQLite tạm, `DJANGO_DEBUG=1`, `AI_ENABLED=1`):
> main `2dcf666` cổng 8801 và nhánh cổng 8802. Gọi bằng HTTP + token thật của từng vai. Server, DB tạm, symlink `staticfiles`/`.env` đã gỡ.

### Kết luận: APPROVED — 0 lỗi chặn. 585 lời gọi so với main chỉ lệch đúng các mục đã duyệt; V1/V2, che ô khách, 404 ngoài phạm vi, AI, Shop đều đúng bằng chứng chạy thật.
### Tổng: 85 ca · ✅ 85 · ❌ 0 · ⏸ 0

(Lúc chạy kịch bản có 2 dòng đỏ do **lỗi của script QA**, không phải lỗi sản phẩm: một ca so cả `totals` trong khi Chủ có thêm `gross_profit` (đúng, Chủ có `view_profit`); một ca import sai tên model `AuditLog`. Đã sửa script/đo lại: `amount` NV kho = Chủ = `1400000`; AuditLog có 9 dòng `change_group_capabilities`. Tính ✅.)

### Theo AC
| Mã AC | Kết quả | Bằng chứng |
|---|---|---|
| PV-03-AC1 | ✅ | NV giao D1 `assigned_deliveries`: danh sách y hệt main (hồi quy mục 6). K+G (cả hai nhóm `assigned_deliveries`) chỉ thấy `SO-PV-06`. NV kho thu hẹp: danh sách hoá đơn `count 0`, `totals.amount 0` (tổng chỉ tính trong phạm vi) |
| PV-03-AC2 | ✅ | Chủ đổi D1 NV kho `assigned_deliveries` → `all` (shell), cùng token, request kế: `count 16`, chi tiết 200. NV giao `all` → thấy 16 đơn, trả lại → thu hẹp ngay |
| PV-03-AC3 | ✅ | CSKH `assigned_or_confirmation`: danh sách/chi tiết/`?q=` của CSKH và `customer_service`-khác trùng main từng byte (hồi quy); 35 test mới xanh |
| PV-03-AC4 | ✅ | NV kho (D1 thu hẹp) trên đơn ngoài phạm vi: chi tiết **404**, `/api/guidance/order/<id>/` **404**, AI `salesorder.retrieve` **404** (không 403). Hoá đơn ngoài phạm vi 404 |
| PV-03-AC5 | ✅ | AI hỏi đơn ngoài phạm vi: 404 `retrieve`, không có mã X trong thân |
| PV-03-AC6 | ✅ | K có V1, D1 `assigned_deliveries`: danh sách hoá đơn 0 dòng, chi tiết hoá đơn ngoài phạm vi 404 |
| PV-03-AC7 | ✅ | NV kho D1 `all` nhưng tắt `view_orders` (qua PUT `/capabilities/`): `GET /orders/` **403** |
| PV-03-AC8 | ✅ | NV kho, NV giao, K+G: danh sách + chi tiết đơn, danh sách + chi tiết hoá đơn quét `unit_cost, landed_unit_cost, purchase_rate, cogs, gross_profit, margin, profit`: không có (10 ca) |
| PV-03-AC9 | ✅ | `manage.py test apps.accounts.data_scopes`: 112 OK (gồm mốc PV-01) |
| PV-07-AC1 | ✅ | Sau migrate: V2 ở 5 nhóm (owner 153, manager 72, warehouse 37, delivery 10, cs 6 quyền). Registry (đọc `GET /api/staff/groups/`): V1 `on` ở owner, manager, warehouse_staff; `off` ở delivery_staff, customer_service (đúng nhóm có `view_salesinvoice` trước migrate); V2 `on` cả 5 |
| PV-07-AC2 | ✅ | K danh sách hoá đơn: `customer_name` null (main) → "Khách Giả 02…16" (nhánh), 15 dòng, **chỉ** `customer_name`, không SĐT/địa chỉ. Người K+G cùng ngoại lệ (đã duyệt, mục 2 review) |
| PV-07-AC3 | ✅ | Chủ PUT tắt V2 của NV kho: đơn (danh sách, chi tiết), hoá đơn: tên/SĐT/địa chỉ `null`, `customer_hidden_reason: "not_permitted"`, mã/trạng thái/tiền còn; `cancel_note: ""`; thân JSON không còn chuỗi giả nào |
| PV-07-AC4 | ✅ | NV giao (V2 bật, D1 `assigned_deliveries`), đơn kết thúc 8 ngày: chi tiết tên/SĐT/địa chỉ `null`, `customer_hidden_reason: "expired"`; danh sách có 2 dòng `expired`; còn trong cửa sổ thì thấy tên |
| PV-07-AC5 | ✅ | Tắt V1 của NV kho: danh sách và chi tiết hoá đơn **403**, đơn vẫn 200 |
| PV-07-AC6 | ✅ | V1 bật, `view_orders` tắt, D1 `all`: `GET /invoices/` 200, 15 dòng |
| PV-07-AC7 | ✅ | PUT bật V2 cho `owner`: 400 `GROUP_LOCKED` |
| PV-07-AC8 | ✅ | Test registry nằm trong 3057 test (OK). Bằng chứng chạy thật: PUT bật/tắt V1 và V2 từng việc một không kéo việc khác (`view_orders` đứng riêng); V2 không `owner_only` (PUT tắt cho NV kho/Quản lý/NV giao đều 200) |
| PV-07-AC9 | ✅ | V2 bật cho 5 nhóm: `GET /api/shop/orders/SO-PV-05/?phone_last4=0105` trả mã, trạng thái, tiền, `delivery.status`; không tên/địa chỉ/SĐT. Sai 4 số cuối: 404. Bấm 25 lần liên tiếp: có **429** (giới hạn tần suất) |

### Ngoại lệ & biên (đã chạy thật)
| # | Ca | Kết quả |
|---|---|---|
| 1 | Migrate tiến head: V2 có ở 5 nhóm | ✅ `owner/manager/warehouse_staff/delivery_staff/customer_service` đều `V2` |
| 2 | Lùi `migrate sales 0014`: gỡ V2 khỏi 5 nhóm | ✅ `Unapplying 0016 OK`, `0015 OK`; số quyền mỗi nhóm giảm 1 (153→152, 72→71, 37→36, 10→9, 6→5); không nhóm nào còn V2 |
| 3 | Tiến lại | ✅ `Applying 0015 OK`, `0016 OK`; V2 ở 5 nhóm, số quyền như trước lùi |
| 4 | `makemigrations --check --dry-run` | ✅ `No changes detected` |
| 5 | Thiếu V2: `?q=` theo SĐT đủ, 4 số cuối, tên | ✅ cả 3 → `count 0`; `?q=SO-PV-05` → 1; Chủ `?q=SĐT` → 1 |
| 6 | Thiếu V2: phiếu hoàn tiền (Quản lý, vì NV kho không có `view_refund`) | ✅ danh sách 2 dòng, chi tiết: `customer_name`/`customer_phone` = `null` (không `""`), `customer_hidden_reason: "not_permitted"`, thân không có chuỗi giả. Bật V2: có tên |
| 7 | Thiếu V2 và quá cửa sổ cùng lúc | ✅ lý do `not_permitted` đứng trước `expired` |
| 8 | Thiếu V2 nhưng đơn của chính mình trong cửa sổ | ✅ vẫn che (V2 là cổng riêng) |
| 9 | Người K+G: tắt V2 ở NV kho thôi → còn V2 nhờ NV giao | ✅ vẫn thấy tên. Tắt cả hai → che. Bật lại NV giao → thấy ngay request sau, **cùng token**, không đăng nhập lại |
| 10 | Màn hình cũ (trạng thái đã đổi): token cũ sau khi Chủ đổi V2/V1/D1 | ✅ mọi lần đổi hiệu lực ở request kế tiếp, cả khi bật lại |
| 11 | Hai quyền chồng nhau: D1 `all` + tắt `view_orders` / V1 bật + tắt `view_orders` | ✅ 403 / 200 (Q-7) |
| 12 | Tổng tiền hoá đơn không đổi theo V2 | ✅ NV kho `1400000` = Chủ `1400000` (Chủ có thêm `gross_profit`, NV kho thì không) |
| 13 | AI đọc đơn (Chủ, NV kho thiếu V2, retrieve) | ✅ không `customer_hidden_reason`, không tên/SĐT/địa chỉ; 200 (đầu ra 2973 ký tự, dưới ngưỡng cắt `AI_RESULT_MAX_CHARS=3000`, không mất dòng) |
| 14 | Tắt V2/V1 là hành động Tầng 2 → AuditLog | ✅ 9 dòng `change_group_capabilities`, `changes` chỉ `{khoá việc: {from,to}}`; không có tên/SĐT/địa chỉ, không có giá vốn hay số tiền |

### Phân quyền (HTTP thật)
| Hành động | Chưa đăng nhập | Chủ | Quản lý | NV kho | NV giao | CSKH |
|---|---|---|---|---|---|---|
| `GET /sales/orders/` (D1 mặc định) | 401 | 200 | 200 | 200 | 200 (chỉ của mình) | 200 (theo phạm vi gọi) |
| `GET /sales/invoices/` | 401 | 200 | 200 | 200 | 403 (không V1) | 403 (không V1) |
| `GET /sales/refunds/` | 401 | 200 | 200 | 403 | — | — |
| `PUT /staff/groups/<code>/capabilities/` | 401 | 200 | 403 | 403 | 403 | 403 |
| PUT V2 cho `owner` | — | 400 `GROUP_LOCKED` | — | — | — | — |

### Rò giá vốn: không
Danh sách/chi tiết đơn và hoá đơn của NV kho, NV giao, K+G không có `unit_cost`, `landed_unit_cost`, `purchase_rate`, `cogs`, `gross_profit`, `margin`, `profit` (10 ca). `AuditLog.changes` chỉ khoá việc + `on/off`: không suy ra giá vốn.

### Rò dữ liệu cá nhân: không
- Thiếu V2 hoặc quá cửa sổ: tên, SĐT, địa chỉ `null`, `cancel_note ""`, thân JSON không còn chuỗi giả (quét "Khách Giả", "09000001", "Đường Giả", ghi chú huỷ) ở danh sách + chi tiết đơn, hoá đơn, phiếu hoàn.
- `?q=` thiếu V2 không dò được SĐT/tên. Hoá đơn `?q=` vốn chỉ khớp mã.
- Shop tra đơn công khai: không tên/địa chỉ/SĐT, có 429.
- AI: kết quả không chứa cờ `customer_hidden_reason` hay dữ liệu cá nhân.
- AuditLog: không dữ liệu khách. Log server: 0 `Traceback`, không có `logger` hay `print` mới trong file Lô 3.

### Hồi quy so với main (6)
Cùng dữ liệu giả (16 đơn, 15 hoá đơn, 2 phiếu hoàn tiền), cùng thứ tự tạo, 9 danh tính (Chủ, Quản lý, NV kho, NV giao, NV giao khác, CSKH, K+G, người không nhóm, chưa đăng nhập) × 65 lời gọi = **585 lời gọi** (danh sách, `?q=` mã/SĐT/tên, `?status=`, `?customer=`, chi tiết từng đơn/hoá đơn/phiếu hoàn, `guidance`, danh sách hoá đơn, phiếu hoàn, dashboard, danh sách nhóm, AI `list` và `retrieve`). Mã trạng thái: 200×300, 404×131, 403×82, 401×64, 405×8; **không lệch mã nào**. Sau chuẩn hoá phần ngẫu nhiên (mã phiếu giao `GH-…-XXXXX`, `action_id`, `as_of`), còn 124 lời gọi lệch thân JSON. Phân loại:

| Lệch | Số | Thuộc danh sách duyệt? |
|---|---|---|
| Thêm khoá `customer_hidden_reason` (giá trị `null`) ở danh sách/chi tiết đơn, hoá đơn, phiếu hoàn, mọi vai | phần lớn | ✅ khoá chỉ thêm |
| NV giao: `customer_hidden_reason: "expired"` trên dòng quá cửa sổ (tên vốn đã `null` ở main) | 2 chi tiết + 4 dòng danh sách | ✅ |
| NV kho và K+G: `invoices.list` `customer_name` `null` → "Khách Giả NN" (15 dòng mỗi vai) | 30 | ✅ ngoại lệ Q-4 (PV-07-AC2), không có SĐT/địa chỉ |
| Chủ: `GET /staff/groups/` thêm dòng việc `view_sales_invoices`, `view_order_customer_info` | 10 | ✅ registry mới |
| `null` thay `""` | 0 trong dữ liệu seed (mọi phiếu hoàn có đơn) | ✅ đã kiểm riêng ở ca 6 (Quản lý tắt V2) |
| Người không nhóm (`direct_permissions`) | chỉ `customer_hidden_reason` | seed của QA cấp V2 trực tiếp cho họ (như fixture PV-01), nên không thấy lệch tên; **R9/C2 chưa kiểm ở đây** |

**Không có lệch nào ngoài danh sách**: không đổi mã, không mất/đổi dòng, không đổi tổng tiền, không đổi quyền của NV giao/CSKH.

### Lỗi
Không có lỗi chặn.

### Quan sát (không chặn)
- **O1 (Low, đã có ở main):** log truy cập của `runserver` ghi nguyên chuỗi `?q=` (tôi tự gõ SĐT/tên giả vào URL tìm kiếm). Main cũng vậy, không do Lô 3. Production nên che `?q=` trong log truy cập Cloud Run, hoặc cân nhắc chuyển `q` sang POST. Đề nghị đưa vào checklist go-live phần log.
- **O2 (nhắc C2):** người không nhóm có quyền gán trực tiếp sẽ mất tên/SĐT/địa chỉ trên đơn, hoá đơn, phiếu hoàn cho tới khi được cấp V2 trực tiếp. Seed của QA cấp V2 cho họ, nên đường này chưa chạy được ở QA lô này, đã có ở review techlead (D-3). Đếm trên production trước khi deploy.
- **O3 (C1 nhắc lại):** dòng phiếu hoàn tiền và dashboard chưa theo D1 (hoãn tới Lô 5). Hiện an toàn vì không đường nào ghi được D1; Lô 5 không được duyệt nếu thiếu phần này.
- **O4:** `check_naming.py` chỉ báo 2 file FE từ main (`ContactButton.tsx`, `SiteLegalFooter.tsx`), không phải file Lô 3.
- Hai URL trong script QA (`/api/customers/`, `confirmation/search/` bằng GET) trả 404/405 ở **cả hai** máy chủ, không phải lệch.

### Lệnh đã chạy (rút gọn)
- Migrate: `DATABASE_URL=sqlite:///…br.sqlite3 manage.py migrate` → `showmigrations sales` (0016 `[X]`) → `migrate sales 0014` → `migrate` → `makemigrations --check --dry-run`; mỗi lần đếm quyền `view_order_customer_info` của từng nhóm bằng `manage.py shell`.
- Seed: `manage.py shell < seed.py` (dựng bộ dữ liệu giả `fixtures.build_scene()` trên cả main và nhánh, thêm `Token` cho từng tài khoản).
- Máy chủ: `runserver 8801 --noreload` (main), `runserver 8802 --noreload` (nhánh), `AI_ENABLED=1`.
- Hồi quy: `reg.py` 585 lời gọi trên mỗi máy chủ, `cmp.py` so thân JSON. Kịch bản: `scen.py` (64 ca), `scen2.py` (12 ca), `audit.py`. Chủ đổi quyền bằng `PUT /api/staff/groups/<code>/capabilities/` (đường thật), D1 bằng `GroupDataScope` qua shell.
- `manage.py test --parallel 4` toàn bộ: `Ran 3057 tests … OK`. `manage.py test apps.accounts.data_scopes`: `Ran 112 tests … OK`.

---

## QA Lô 4 + 5 BE (08/10)

> qa-tester · worktree `.claude/worktrees/pham-vi`, nhánh `feat/pham-vi-du-lieu`, HEAD `6f38505`. Chỉ BE (FE Lô 6/7 ngoài phạm vi). Mọi dữ liệu là dữ liệu giả (`data_scopes/tests/fixtures.py`: "Khách Giả NN", SĐT `09000001NN`).
> Hai `runserver` thật (SQLite tạm, `DJANGO_DEBUG=1`): **mốc so sánh** = `151b56e` (`git archive`, cổng 8811; là điểm merge-base, đã gồm Lô 1-3, trước Lô 4) và nhánh (cổng 8812); thêm một máy chủ `AI_ENABLED=1` cổng 8813. Token thật của 5 vai + K+G + K+C + người không nhóm có quyền gán trực tiếp + superuser. Đã tắt từng máy chủ theo PID, xoá DB tạm, gỡ symlink `staticfiles`/`.env`; `git status` sạch.
> Mốc so sánh là `151b56e` chứ không phải đầu `main` hiện tại, vì `main` đã đi tiếp W37 (23 file backend khác) và sẽ làm nhiễu phép so.

### Kết luận: REJECTED — 1 lỗi chặn mức Medium (B1): `GET /api/guidance/refund/<id>/` vẫn trả 200 cho phiếu hoàn NGOÀI phạm vi D1 sau khi Chủ thu hẹp (lộ mã phiếu, số tiền, mã đơn, mã hoá đơn; không có tên/SĐT/địa chỉ, không giá vốn). Còn lại đúng bằng chứng chạy thật. Sửa nhỏ (một chỗ), không đụng hợp đồng.
### Tổng: khoảng 260 ca thủ công qua HTTP + 1364 lời gọi hồi quy · ✅ ≈ 257 · ❌ 1 (B1) · ⏸ 1 (đua đồng thời PV-10-AC5 chỉ chạy được trên Postgres)
(Có 8 dòng "FAIL" lúc chạy kịch bản là **lỗi kịch bản của QA**, không phải lỗi sản phẩm, đã đo lại đúng và tính ✅: mốc cửa sổ 7 ngày tính theo giờ cố định 06/10 trong khi máy chủ chạy giờ thật 07/10; hai ca dòng thời gian khách của NV giao là 403 vì thiếu quyền Tầng 1 `view_customer_list` (đã đo lại bằng Quản lý có D7 hẹp: 404 đúng); `PUT D7=none` khi Xem khách hàng bật bị PO-Q1 chặn 400 (đúng); mở rộng lại D7 phải có xác nhận; `assign` phiếu `DELIVERING` bị `DELIVERY_ASSIGN_STATE` nên đổi sang phiếu `PREPARING`; tem và `decide` bị cổng quyền 403 đứng trước phạm vi; `inventory_value` chỉ có ở Chủ nên so khoá chung; `/me` chưa có `data_scopes` vì đó là PV-14, lô sau.)

### Theo AC
| Mã AC | Kết quả | Bằng chứng (chạy thật) |
|---|---|---|
| PV-04-AC1 | ✅ | NV giao: danh sách 6 phiếu của mình, `?assigned_to=me` cùng tập; Chủ/Quản lý/NV kho/K+G thấy 15 |
| PV-04-AC2 | ✅ | CSKH không có quyền xem phiếu giao: 403 (đúng hiện trạng, như 02b §0) |
| PV-04-AC3 | ✅ | NV giao: hàng hoàn 1/3; chi tiết, dòng thời gian của hàng hoàn người khác và hàng hoàn không gắn phiếu: 404; `POST /inventory/returns/` với phiếu giao người khác: 404, không tạo |
| PV-04-AC4 | ✅ | Phiếu kết thúc 8 ngày: tên, địa chỉ `null`, không rò chuỗi giả. Biên đo lại theo giờ VN: kết thúc 00:30 VN đúng ngày cắt vẫn thấy, 23:30 VN hôm trước thì ẩn |
| PV-04-AC5 | ✅ | Chủ PUT D3 NV giao = `all` (có xác nhận): cùng token, request kế thấy 15 phiếu, phiếu 8 ngày vẫn có tên; `?assigned_to=người khác` 200. Trả `assigned`: lại 403 |
| PV-04-AC6 | ✅ | NV giao đổi trạng thái phiếu người khác: 404, phiếu vẫn `DELIVERING`. Phiếu `CANCELLED` của chính mình: 400 `BR-GH-24` |
| PV-04-AC7 | ✅ | CSKH D3 = `all` nhưng thiếu quyền xem phiếu giao: 403 |
| PV-04-AC8 | ✅ | `test_scope_snapshot`: xanh |
| PV-05-AC1 | ✅ | CSKH: phiếu đang chờ 200; phiếu mình gọi 2 ngày trước 200; phiếu người khác gọi 404; phiếu mình gọi 9 ngày trước 404 |
| PV-05-AC2 | ✅ | `?state=DONE`: 12/13 dòng ngoài phạm vi chỉ có `phone_masked` (`09xx xxx 115`), tên/SĐT/địa chỉ `null`. `POST /confirmation/search/` mã đơn ngoài phạm vi: `in_scope:false` + `phone_masked` |
| PV-05-AC3 | ✅ | Chủ bật `confirm_calls` cho NV kho: chi tiết phiếu người khác gọi 200; K+C cũng 200; tắt → 403 request kế |
| PV-05-AC4/5 | ✅ | Quản lý D7 `all`: danh bạ 17 = `/customers/` 17. D7 `assigned_deliveries` (gán 1 phiếu): cả hai chỉ đúng 1 khách. NV giao `/customers/` = đúng tập khách của phiếu trong cửa sổ (6) |
| PV-05-AC6 | ✅ | D7 hẹp: chi tiết khách ngoài phạm vi 404, dòng thời gian 404, `search` rỗng, `/orders/?customer=<ngoài D7>` 200 rỗng (kể cả khách có đơn); trong phạm vi 1 đơn |
| PV-05-AC7 | ✅ | Tắt `view_customers` ở Quản lý: danh bạ 403 dù D7 lưu `all` (Q-7); `/customers/` cũ 200 rỗng |
| PV-05-AC8/9 | ✅ | grep `backend/apps` (trừ tests) không còn bốn tên cũ; snapshot xanh |
| PV-06-AC1/2 | ✅ | NV kho D6 `all`: 5 phiếu. `created_by_me`: chi tiết phiếu người khác 404 |
| PV-06-AC3 | ✅ | **Giờ thật VN 07/10 02:46 (UTC vẫn 06/10)**, `created_by_me_today`: thấy phiếu "bây giờ" và "00:05 VN hôm nay"; không thấy "23:50 VN hôm qua", phiếu Quản lý, phiếu Chủ cũ. Chi tiết ngoài ngày 404; dòng thời gian 404 |
| PV-06-AC4 | ✅ | Phiếu đổi sang 23:59 VN hôm qua: `PATCH` 404 và `submit` 404, `note` không đổi; Quản lý vẫn thấy và sửa 200 |
| PV-06-AC5/6 | ✅ | Huỷ phiếu của mình ngoài ngày: 200 (luật cũ); huỷ phiếu Quản lý ngoài D6: 404, không bị mở thêm |
| PV-06-AC7 | ✅ | Phiếu nhập NV kho: không `landed_unit_cost`, `purchase_rate`, `unit_cost` |
| PV-06-AC8 | ✅ | NV giao: phiếu nhập 403 |
| N2 (QA W37) | ✅ | V2 bật: phản hồi `POST /delivery/notes/{id}/status/` có tên (không đổi). Chủ tắt V2 của NV giao: danh sách, chi tiết **và phản hồi `status`** có `customer_name`/`address`/`note` = `null`, không chuỗi giả, giữ khoá. Tắt V2 của Quản lý: phản hồi `assign` cũng che. Bật lại: request kế (cùng token) thấy tên |
| PV-08-AC1/2/3 | ✅ | 1 AuditLog `change_group_data_scopes` `{"receipts":{"from":"all","to":"created_by_me_today"}}`, actor Chủ, object nhóm; việc + phạm vi cùng lúc: đúng 2 AuditLog; giá trị trùng: 200, không AuditLog, `version` không tăng |
| PV-08-AC4/5 | ✅ | `receipts:"mine"` 400 `SCOPE_VALUE_INVALID`; `stock` 400 `SCOPE_OBJECT_UNKNOWN`; `invoices`/`audit_log` 400 `SCOPE_READ_ONLY`; nhóm `owner` 400 `GROUP_LOCKED`; nhóm lạ 404 `GROUP_NOT_FOUND`; khoá thân lạ 400 `INPUT_NOT_ALLOWED`. Lẫn một khoá đúng một giá trị sai: không khoá nào lưu, không AuditLog (so ảnh chụp 4 nhóm trước/sau) |
| PV-08-AC6 | ✅ | `test_pv08_ac6_audit_failure_leaves_configuration_unchanged` xanh (không giả lập được lỗi AuditLog qua HTTP) |
| PV-08-AC7 | ✅ | Quản lý, NV kho, NV giao, CSKH, K+C, **Quản lý có `manage_staff` gán trực tiếp**: PUT 403 và preview 403, cấu hình và AuditLog không đổi. Chưa đăng nhập 401. Superuser không nhóm: PUT 200 |
| PV-08-AC8 | ✅ | `timeline` có "Đổi phạm vi Phiếu nhập: Tất cả phiếu → Do tôi tạo trong ngày", actor `display` theo người làm, không có `changes` thô |
| PV-08-AC9 | ✅ | 46 dòng `change_group_*`: `changes` chỉ mã đối tượng/mã giá trị/cờ; quét chuỗi giả, tên đăng nhập, số tiền: 0 |
| PV-08-AC10 | ✅ | D1 NV giao `assigned_deliveries` → `all`: cùng token, request kế thấy 16 đơn; thu hẹp lại: request kế còn 7. D5, D3, D7, D1 của Quản lý đều hiệu lực ngay |
| PV-09-AC1 | ✅ | preview D1 NV giao → `all`: `widens_customer_data:true`, `affected_count 3`, 3 nhân viên `{id, display_name}`, `message` "3 người trong nhóm sẽ thấy…"; sau preview: `version`, phạm vi, AuditLog không đổi |
| PV-09-AC2/3 | ✅ | PUT thiếu xác nhận: 400 `CUSTOMER_DATA_WIDENING_UNCONFIRMED` kèm `impact` (7 khoá, chỉ mã, nhãn, tên nhân viên), không đổi gì; có xác nhận: 200, AuditLog có `customer_data_widening_confirmed:true` |
| PV-09-AC4 | ✅ | NV kho tắt rồi bật V2 không xác nhận: 400, `widened` có `view_order_customer_info`; có xác nhận: 200 |
| PV-09-AC5 | ✅ | D6 `all` → `created_by_me`: `widens:false`, `rows_losing_access = 4` (đúng: nháp 1,2,4,5; phiếu 3 đã huỷ không đếm; 3 thành viên gộp không trùng); PUT thu hẹp không cần xác nhận |
| PV-09-AC6 | ✅ | preview D1 NV giao → `assigned_or_confirmation`: `already_wider_elsewhere` = đúng K+G, `via_group: warehouse_staff`, `key: orders`; NV giao thuần không có trong danh sách |
| PV-09-AC7 | ✅ | D6 `created_by_me` → `all` không xác nhận: 200 |
| PV-09-AC8/9 | ✅ | preview: NV kho, Quản lý… 403; anonymous 401; body không tên/SĐT/địa chỉ khách, không SĐT nhân viên, không giá vốn |
| PV-10-AC1 | ✅ | A PUT `version` đúng: 200, `version` tăng; B cùng version cũ: **409 `GROUP_CHANGED`**, giá trị của A giữ, không AuditLog cho B |
| PV-10-AC2/3/4 | ✅ | A đổi việc, B đổi phạm vi: 409; nhóm khác version riêng: 200; thiếu `version`: 400 `INVALID_INPUT`; `version:"abc"`: 409; `version` kiểu số: 400 |
| PV-10-AC5 | ⏸ | Đua thật 2 PUT song song cùng version trên SQLite cho `[200, 500]` (`database is locked`; `select_for_update` không có tác dụng trên SQLite, bài test `test_pv10_ac5_two_parallel_saves_one_wins` cũng tự bỏ qua). Không có Postgres trên máy này, nên **chưa kiểm chứng**. Cần chạy ở CI/staging Postgres trước khi lên production |
| PV-05/PO-Q1 | ✅ | Bật `view_customers` khi D7 `none` không kèm `scopes.customers`: 400 `SCOPE_VALUE_INVALID`; kèm `all` + xác nhận: 200, danh bạ 17 khách request kế; D7 `none` khi việc bật: 400; tắt việc + `none` cùng lúc: 200 |
| Mock F1 (4 ca) | ✅ | (1) NV giao D7 `assigned→all` khi việc tắt: không mở rộng/thu hẹp. (2) lưu `all` rồi bật việc: `widened {customers,all,all}`, PUT thiếu xác nhận 400. (3) Quản lý tắt (danh bạ 403) rồi bật lại khi D7 `all`: mở rộng, 400 rồi 200, danh bạ 17. (4) NV kho bật kèm `customers:"all"`: `widened {customers,none,all}`; không kèm D7: 400 |
| `/me` | ✅ | `is_superuser` có ở mọi vai (true chỉ ở superuser); 401 khi chưa đăng nhập; không giá vốn/dữ liệu khách |
| C1 phiếu hoàn | ❌ một chỗ (B1) | D1 Quản lý → `assigned_deliveries`: danh sách còn đúng 2/3 phiếu (đơn trong phạm vi); chi tiết phiếu ngoài phạm vi 404; phiếu của đơn kết thúc 8 ngày: tên/SĐT `null`, `customer_hidden_reason:"expired"`; `confirm` phiếu ngoài phạm vi: không 200; Chủ vẫn thấy 3. **Nhưng `GET /api/guidance/refund/<id>/` ngoài phạm vi vẫn 200 (B1)** |
| C1 dashboard | ✅ | Mặc định Quản lý = Chủ (`revenue_today 350000`, `pending_orders 13`, 8 đơn gần đây). D1 hẹp: `pending_orders 13 → 1`, `recent_orders` đúng 2 đơn của Quản lý (bằng `/orders/`), `revenue_today 350000 → 80000` (= 100000 hoá đơn trong phạm vi − 20000 phiếu đảo; đã kiểm tay: 4 hoá đơn hôm nay × 100000 − 2 phiếu đảo 30000 + 20000 = 350000). Chủ không đổi. Trả `all` có xác nhận: về như cũ |

### Ngoại lệ & biên (đã chạy thật, ngoài đường thuận)
| # | Ca | Kết quả |
|---|---|---|
| 1 | Màn hình cũ: NV giao đang xem phiếu người khác (D3 `all`), Chủ thu hẹp | ✅ cùng URL, cùng token: 404; đổi trạng thái phiếu đó 404, phiếu không đổi |
| 2 | Hai người cùng lúc: hai PUT cùng `version` (tuần tự và song song) | ✅ tuần tự 409; ⏸ song song thật (xem PV-10-AC5) |
| 3 | Cờ bật/tắt: V2 tắt/bật cho NV giao, Quản lý; `confirm_calls` bật/tắt cho NV kho; `view_customers` tắt rồi bật | ✅ hiệu lực ở request kế, không đăng nhập lại |
| 4 | Dữ liệu đã có giao dịch: hoá đơn phát hành hôm nay + phiếu đảo + phiếu hoàn đơn quá cửa sổ khi tính dashboard và phiếu hoàn | ✅ số tiền đúng |
| 5 | Qua nửa đêm: UTC vẫn 06/10, VN đã 07/10; mốc 23:50, 23:59, 00:05 | ✅ |
| 6 | Người kiêm nhiệm K+G, K+C | ✅ K+G rank cao nhất (15 phiếu); K+C kế thừa D4/D7 từ K khi K có việc. Xem O1 về K+C mặc định |
| 7 | Nhóm lưu D7 `all` nhưng thiếu `view_customer_list` (H1/L4) | ✅ giá trị hiệu lực vẫn là `assigned_deliveries` (NV giao `/customers/` = đúng khách của phiếu trong cửa sổ, 6/6); `note` "Bật Xem khách hàng để thấy tất cả khách" hiện ở dòng `customers` |
| 8 | 400 do thiếu xác nhận rồi kiểm không đổi gì | ✅ (so ảnh chụp phiên bản và phạm vi của 4 nhóm) |
| 9 | Hành động ghi trên mục ngoài phạm vi: CSKH `claim`/`calls`/`unconfirm`/`recipient` mục ngoài phạm vi: 404, `CustomerCall` vẫn 1 dòng; trong phạm vi `claim` 200 | ✅ |
| 10 | AI (`AI_ENABLED=1`): NV giao `delivery.deliverynote.list` chỉ phiếu của mình, `retrieve` phiếu người khác 404, không chuỗi giả | ✅ |

### Phân quyền (HTTP thật, mặc định)
| Hành động | Anonymous | Chủ | Quản lý | NV kho | NV giao | CSKH | Không nhóm |
|---|---|---|---|---|---|---|---|
| Danh sách phiếu giao | 401 | 15 | 15 | 15 | 6 (của mình) | 403 | 15 |
| Hàng hoàn | 401 | 3 | 3 | 3 | 1 | 403 | co lại theo D5 |
| Hàng chờ gọi xác nhận | 401 | 200 | 200 | 403 | 403 | 200 | như main |
| Danh bạ khách | 401 | 17 | 17 | 403 | 403 | 403 | 0 (D7 `none`, PENDING D-3) |
| Phiếu nhập | 401 | 5 | 5 | 5 | 403 | 403 | 0 (PENDING D-3) |
| `PUT /staff/groups/<code>/capabilities/`, `POST …/permissions-preview/` | 401 | 200 | 403 | 403 | 403 | 403 | 403 (superuser 200) |

### Rò giá vốn: không
Hàng hoàn (NV giao, NV kho, danh sách + chi tiết), phiếu nhập NV kho, phiếu giao NV giao và phản hồi `status`, dashboard của Quản lý, body preview/PUT, `/me`, AuditLog: không có `unit_cost`, `landed_unit_cost`, `purchase_rate`, `cogs`, `gross_profit`, `margin`, `profit`. (`unit_cost` xuất hiện trong dashboard của **Chủ** đúng như main; Chủ có `view_costprice`.) AuditLog `changes` chỉ có mã đối tượng/giá trị: không tính ngược ra giá vốn được (không có số tiền hay kg).

### Rò dữ liệu cá nhân: không (ngoài B1 không có dữ liệu khách; B1 chỉ lộ mã và số tiền)
- Quét chuỗi giả ("Khách Giả", "0900000", "Đường Giả", ghi chú) ở: phiếu giao khi thiếu V2/quá cửa sổ (danh sách, chi tiết, phản hồi `status`, `assign`), hàng chờ ngoài phạm vi (chỉ `phone_masked`), tìm xác nhận, danh bạ hẹp (không `note`/`default_address`), phiếu hoàn quá cửa sổ, preview/PUT (`impact` chỉ mã/nhãn/`{id, display_name}`), `/me`, AuditLog, dashboard, AI: sạch.
- Log máy chủ: không `logger`/`print` mới trong diff (`git diff 151b56e HEAD`); log truy cập chỉ ghi `?q=` do chính tôi gõ vào GET (O2, cũ). Hai `Traceback` trong log là `database is locked` của ca đua trên SQLite.
- Tên nhân viên trong `affected_members` là dữ liệu nội bộ, không phải khách.

### Hồi quy so với `151b56e` (cùng dữ liệu giả, 11 danh tính × 124 lời gọi = **1364 lời gọi**)
Mã trạng thái: 200×639, 403×433, 404×156, 401×124, 400×12. Giống hệt: 1298. Lệch: 66 lời gọi, phân loại **đủ**:

| Lệch | Số | Thuộc danh sách được phép? |
|---|---|---|
| `/auth/me/` thêm khoá `is_superuser` (mọi vai, null → false/true) | 11 | ✅ (thêm khoá, Lô 5) |
| Người không nhóm: phiếu nhập (danh sách 5→0, chi tiết 5×404, dòng thời gian 5×404) | 11 | ✅ `PENDING_DUY_DIFFS` (D-3, D6) |
| Người không nhóm: danh bạ khách (danh sách 17→0, `?q=` 17→0, chi tiết 17×404, `search` 1→0), `/customers/` (1→0, chi tiết 404), dòng thời gian khách 6×404 | 45 | ✅ `PENDING_DUY_DIFFS` (D-3, D7) |
| Người không nhóm: phiếu hoàn 2→0; dashboard `pending_orders 15→1`, `recent_orders 8→1` | 3 | ✅ `PENDING_DUY_DIFFS` (C1, chỉ thu hẹp) |
| **K+C** (`warehouse_cs`): hàng chờ `?state=DONE` 13 dòng `in_scope true→false`, tên/SĐT/địa chỉ → `null`; chi tiết 13×404; tìm xác nhận 1 dòng thành `phone_masked` | 4 dòng lời gọi | ❌ **ngoài danh sách được phép**; techlead đã ghi nhận ở review (L2, Low) nhưng fixture/mốc không bắt, và không nằm trong `PENDING_DUY_DIFFS`. Xem O1 |
| V2 trên phiếu giao | 0 | ✅ mặc định V2 bật ở 5 nhóm nên không lệch; chỉ lệch khi Chủ tắt V2 (đã kiểm ở N2) |
| Danh bạ ẩn `note`/`default_address` khi D7 khác `all` | 0 | ✅ mặc định Quản lý D7 `all` nên không lệch; chỉ khi D7 hẹp (đã kiểm: 17 → bỏ hai khoá) |
Chủ, Quản lý, NV kho, NV giao (cả hai người), CSKH, K+G, superuser: **không lệch gì** ngoài `is_superuser`. Mọi lệch ở người không nhóm đều là thu hẹp, nằm đúng danh sách `PENDING_DUY_DIFFS` (không thấy dòng nào tăng thêm).

### Lỗi
#### B1 — Dòng thời gian phiếu hoàn ngoài phạm vi D1 vẫn mở được · Medium · AC C1 (02b §1.5, review techlead C1)
- **Bước tái hiện:** (1) Chủ `PUT /api/staff/groups/manager/capabilities/` `{"version":…,"scopes":{"orders":"assigned_deliveries"}}` → 200. (2) Quản lý `GET /api/sales/refunds/<id>/` của đơn không gán cho mình → 404 (đúng). (3) Cùng token `GET /api/guidance/refund/<id>/`.
- **Mong đợi:** 404, giống `/api/guidance/order/<id>/` (404) và chi tiết phiếu hoàn (404).
- **Thực tế:** 200, body có `doc.code "REF-1"`, `doc.status`, `timeline[].label "Tạo phiếu hoàn 50.000 đ"`, `actor.display`, `related: [{invoice INV-PV-04}, {order SO-PV-04}]`. Không có tên/SĐT/địa chỉ, không giá vốn.
- **Ảnh hưởng:** Quản lý bị thu hẹp D1 vẫn dò được sự tồn tại, số tiền và mã đơn của phiếu hoàn ngoài phạm vi (ghép với mã đơn có thể đi tiếp sang `?q=`). Mặc định không xảy ra vì D1 của Quản lý là `all`. Nguyên nhân: `refunds/next_steps.py::get_refund_guidance` không đi qua `scope_refunds_for`.
- **Gợi ý:** lấy phiếu qua `scope_refunds_for(user, Refund.objects.all())`, ngoài phạm vi → 404; thêm test cho đường guidance. Cần chạy lại mốc.

### Quan sát (không chặn)
- **O1 (Low, đã có ở review techlead L2):** người kiêm **NV kho + CSKH** (K+C) bị **thu hẹp** ở "Gọi xác nhận" so với main: main cho thấy mọi mục chờ gọi nhờ `has_full_delivery_scope` của nhóm NV kho; nay chỉ còn `pending_or_called_recently` vì NV kho không có `confirm_with_customer` nên không đủ điều kiện D4. QA đã chạy thật: chi tiết 13 mục DONE từ 200 sang 404, hàng chờ mặc định (PENDING) không đổi. Chỉ thu hẹp, không rò. Cần đưa vào D-3 cùng lệnh đếm (có người K+C thì báo Duy) và nên bổ sung K+C vào fixture/`PENDING_DUY_DIFFS` để mốc bắt được. Nếu Chủ bật `confirm_calls` cho NV kho thì K+C lại thấy `all_pending` (đã kiểm).
- **O2 (Low, cũ):** log truy cập ghi nguyên `?q=` (đã nêu ở QA Lô 3). Các endpoint mới (preview, tìm xác nhận, `search` danh bạ) dùng body POST nên không dính.
- **O3:** `GET /api/dashboard/attention/` trả số đếm gộp (hàng chờ, leo thang…) không theo D4/D1. Chỉ là số, không dữ liệu khách; ghi nhận để Duy biết khi tính D4.
- **O4:** `GET /api/guidance/payment/<id>/` không có phạm vi D1 (cổng bằng quyền `view_paymenttransaction` + `resolve`, chỉ Chủ/Quản lý); không có tên khách. Nằm ngoài các đối tượng D1–D8, chỉ nêu.
- **O5:** `PATCH` `note`/`default_address` của khách ngoài tầm đọc vẫn chưa chặn (đã ghi ở dev-notes, cần cả `view_customer_list` lẫn `change_customer`); không thử lại ở lô này.
- **O6:** `check_naming.py` chỉ báo `frontend/features/site/components/SiteLegalFooter.tsx` (+`ContactButton.tsx`) từ main, không phải file của hai lô.

### Lệnh đã chạy (rút gọn)
- Dựng: `git archive 151b56e backend | tar -x -C …/pv45/base`; `migrate` hai DB SQLite tạm (`sales.0016` có); `manage.py shell < seed.py` (dùng `fixtures.build_scene()` + thêm tài khoản K+C và `Token` mọi vai). `runserver 8811 --noreload` (mốc), `8812 --noreload` (nhánh), `8813` với `AI_ENABLED=1`; tất cả `DJANGO_DEBUG=1`.
- Hồi quy: `reg.py` 1364 lời gọi (mỗi bên), `cmp.py` so thân JSON sau chuẩn hoá thời gian/mã ngẫu nhiên.
- Kịch bản: `scen1.py` (54, Lô 4 mặc định), `scen2.py` (43, cửa sổ, D6 giờ VN, D5/D3/D4/D7 đổi qua PUT), `scen3.py` (N2), `scen4.py` (38, CAS + lỗi đầu vào + quyền), `scen5.py` (22), `scen6.py` (38, mock F1 + PO-Q1 + `/me` + AuditLog), `scen7.py` (C1 + phiếu đảo), cùng các lượt phụ (AI, hành động ghi ngoài phạm vi, nửa đêm). Chủ đổi cấu hình bằng `PUT /api/staff/groups/<code>/capabilities/` (đường thật); chỉ dùng `manage.py shell` để dựng dữ liệu (đổi `created_at`, gán phiếu, tạo phiếu đảo).
- `manage.py test --parallel 4` toàn bộ: `Ran 3211 tests … OK (skipped=3)`. `test_group_save_scopes`, `test_query_budget_and_race`, `test_refunds_dashboard_scope`, `test_scope_snapshot`: 73 OK (skipped=1 là đua Postgres). `makemigrations --check --dry-run`: `No changes detected`. `check_naming.py`: chỉ file FE có sẵn từ main.

### QA lại sau 36d9e8a (08/10)

**Kết luận: APPROVED** (nghiệm thu kỹ thuật; merge vẫn chờ Duy D-3). B1 đã đóng, O1 và O4 đã xử lý. Chạy lại trên BE thật: hai `runserver` (mốc `151b56e` cổng 8811, nhánh cổng 8812), DB SQLite tạm, dữ liệu giả; đã tắt theo PID, xoá DB, gỡ symlink.
**Tổng: 18 ca guidance ✅ 18, ❌ 0; hồi quy 1488 lời gọi; test toàn bộ 3213 OK (skipped=3); `makemigrations --check` không đổi.**

| Ca | Kết quả | Bằng chứng |
|---|---|---|
| B1: Chủ thu hẹp D1 Quản lý, `GET /guidance/refund/<ngoài D1>/` | ✅ 404 (trước: 200); chi tiết phiếu hoàn cũng 404; phiếu trong D1 200; Chủ 200 |
| Guidance ngoài phạm vi: `order` (D1), `delivery` (D3), `return` (D5), `receipt` (D6 hôm nay), `customer` (D7) | ✅ cả 5 đều 404; bản trong phạm vi đều 200 |
| Guidance trong phạm vi không rò dữ liệu khách/giá vốn | ✅ |
| Mặc định (D1 `all`): Quản lý guidance phiếu hoàn | ✅ vẫn 200, không đổi |
| Hồi quy so với `151b56e`, 12 danh tính (thêm K+C của fixture `warehouse_service`) | ✅ K+C (`warehouse_service` và tài khoản K+C của QA) chỉ lệch ở gọi xác nhận (`?state=DONE` 13 dòng `in_scope` true→false, chi tiết 404, tìm xác nhận chỉ còn `phone_masked`) và `is_superuser`; đúng 8 endpoint `warehouse_service` mà `PENDING_DUY_DIFFS` liệt kê. Người không nhóm vẫn chỉ các lệch thu hẹp cũ. Chủ, Quản lý, NV kho, NV giao, CSKH, K+G, superuser: chỉ `is_superuser` |

Còn mở (không chặn): D-3 của Duy cho người không nhóm và K+C (`PENDING_DUY_DIFFS` còn mục, không merge main khi chưa trả lời); ⏸ đua PV-10-AC5 chỉ kiểm được trên Postgres.

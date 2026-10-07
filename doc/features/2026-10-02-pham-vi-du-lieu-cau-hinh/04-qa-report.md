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

## QA Lô QĐ-08/10 (08/10)

**Kết luận: APPROVED** — chạy thật trên BE (SQLite tạm, `seed_qa`) + ERP build thật và mock; không có lỗi chặn.
Nhánh `feat/qd-0810` HEAD `49392a3`. Quyết định: câu 1 (superuser như Chủ), câu 2 (tắt AI ẩn dòng cài đặt/chính sách AI), câu 6 (D-3, cổng BE `AUTH_NO_ROLE`), câu 13 (nhãn "Nhân viên gọi xác nhận"). Dữ liệu chỉ là dữ liệu giả `seed_qa`.

**Tổng: 148 ca · ✅ 148 · ❌ 0 · ⏸ 0** (sau khi loại 7 lần "FAIL" do lỗi kịch bản QA của chính tôi, ghi ở "Ghi chú kịch bản").

### Bảng ca
| Nhóm | Ca | Kết quả | Bằng chứng |
|---|---|---|---|
| API D-3: `qa_nogroup` (có 2 quyền gán trực tiếp) GET 18 API ERP (đơn, hoá đơn, phiếu hoàn, khách, thanh toán, phiếu giao, dashboard, kho, mua, staff, nhóm, hàng chờ, báo cáo, nhật ký, sổ kho) | 18 | ✅ toàn bộ 403 `AUTH_NO_ROLE` | `qaqd/api.py` |
| POST/DELETE/PATCH của `qa_nogroup` (huỷ đơn, xác nhận thanh toán, tạo phiếu hoàn, tạo phiếu giao, tạo khách, tìm xác nhận, xoá đơn, sửa hàng) | 9 | ✅ đều 403; trạng thái mọi đơn trước/sau giống hệt (ngoài đường thuận: dữ liệu không đổi) | `api.py`, `api2.py` |
| Thân 403 chỉ `{detail, code}`, không username/tên/SĐT | 1 | ✅ | `api.py` |
| `qa_nogroup`: me 200 (`home=no-role`, `groups=[]`, `is_superuser=false`), logout 204, đổi mật khẩu tới được logic (sai mật khẩu cũ → 400 `AUTH_OLD_PASSWORD`, không phải AUTH_NO_ROLE) | 4 | ✅ | `api.py` |
| Công khai không đổi: Shop catalog (có và không có token `qa_nogroup`), site-info, content public | 4 | ✅ 200 | `api.py` |
| Chưa đăng nhập gọi đơn → 401, không lộ mã `AUTH_NO_ROLE` | 1 | ✅ | `api.py` |
| Superuser không nhóm: me `is_superuser=true`, `home=dashboard`, `groups=[]`; GET dashboard, đơn, hoá đơn, phiếu hoàn, nhóm, lô, nhật ký | 8 | ✅ 200 | `api.py` |
| Mỗi vai (Chủ, Quản lý, NV kho, NV giao, NV gọi xác nhận): me 200, không dính `AUTH_NO_ROLE`, `is_superuser=false`; nhãn vai đúng; `home` đúng | 5 | ✅ (NV giao, NV gọi xác nhận 403 dashboard như cũ) | `api.py` |
| UI 1280 + 360: `qa_nogroup` đăng nhập → `/no-role/` "Bạn không có quyền vào hệ thống vận hành", nêu username, không chữ "CSKH"; gõ thẳng `/orders/ /overview/ /customers/ /deliveries/ /returns/ /ledger/ /confirmation/ /audit-logs/ /staff/ /reports/ /purchasing/ /inventory/` → về `/no-role/` | 2×(2+12) | ✅ | `ui.py`, ảnh `nogroup-1280.png`, `nogroup-360.png` |
| UI: localStorage và console của `qa_nogroup` không có SĐT/tên | 4 | ✅ | `ui.py` |
| UI: `qa_superuser` → `/overview/`, menu có "Phân quyền" (mục Quản trị), không có "Việc giao của tôi", nhãn "Quản trị hệ thống" trong menu tài khoản và trang Tài khoản, vào được `/orders/ /permissions/ /account/` | 2×~6 | ✅ | `ui.py`, `probe2.py`, ảnh `superuser-*.png` |
| Ca N2 (1280): `qa_warehouse` đang đăng nhập, gỡ hết nhóm bằng shell Django, mở `/orders/` → `/no-role/`; số request `me` sau khi gỡ = 1 (không lặp) | 3 | ✅ | `ui.py`, ảnh `n2-1280.png` |
| N2b: đang ở `/inventory/`, gỡ nhóm, bấm liên kết `/orders` → `/no-role/`; `me` = 1 | 2 | ✅ | `ui.py` |
| Người không nhóm có `must_change_password` → `/set-password/` trước; gõ `/orders/` vẫn ở `/set-password/` | 2 | ✅ | `ui.py`, ảnh `mustchange-1280.png` |
| Nhãn: `qa_cs1` (Tài khoản) hiện "Nhân viên gọi xác nhận"; Chủ ở Nhân viên, Phân quyền, Tài khoản không còn chữ "CSKH" (1280 và 360) | 2×~6 | ✅ | `ui.py` |
| Câu 2, AI tắt (mặc định): 4 dòng giả `ai_config_update`, `ai_config_kill`, `ai_policy_update`, `downgrade_cancel_order` không có ở danh sách và lọc `?action=` (đều 0); dòng nghiệp vụ có `proposal_ref` do người duyệt và dòng thường vẫn hiện; trang Nhật ký không chữ AI cài đặt/chính sách, ô lọc không có "Tắt trợ lý AI" | 12 | ✅ | `audit.py`, ảnh `audit-ai-off.png` |
| Câu 2, ngoài đường thuận: bật `AI_ENABLED=1` (cùng DB) → count 30, 4 dòng hiện lại đủ (không bị xoá, bất biến 4) | 4 | ✅ | script inline |
| Migration `makemigrations --check --dry-run` | 1 | ✅ "No changes detected" | |
| BE test tập trung `apps.accounts.auth`, `common.tests.test_ai_visibility`, `accounts.audit` | 173 | ✅ OK | |
| `check_naming.py` | 1 | ✅ không phát sinh mới | |

### Hồi quy (chạy thật)
| Kịch bản | Môi trường | Kết quả |
|---|---|---|
| `s7_shell` | build mock (AI tắt) | ✅ 25/25 |
| `qa_ed_batch1_roles` | mock | ✅ 48/48 |
| `s48_password` | mock | ✅ 41/41 |
| `ed_batch3_real` | BE thật + seed_qa (DB mới) | ✅ 25/25 |
| `standard_names_all_routes` (REAL=1) | BE thật | ✅ 10/10 |

### `npm ci` sạch
Bản copy `erp-console` (không node_modules) trong scratchpad: `npm ci` rc=0 (không `--legacy-peer-deps`), `tsc --noEmit` rc=0. Build ERP thật (`NEXT_PUBLIC_USE_MOCK=0`) và build mock đều thành công.

### Phân quyền (bảng Group × hành động)
| Danh tính | ERP API | `me` | Shop/public |
|---|---|---|---|
| Không nhóm (có quyền trực tiếp) | 403 `AUTH_NO_ROLE` mọi đường đọc/ghi | 200 | 200 |
| Superuser không nhóm | 200 | 200, `home=dashboard` | 200 |
| Chủ, Quản lý, NV kho | 200 | 200 | 200 |
| NV giao, NV gọi xác nhận | như trước (dashboard 403 theo quyền cũ) | 200 | 200 |
| Chưa đăng nhập | 401 | 401 | 200 |

### Rò giá vốn / dữ liệu cá nhân
- Thân 403 `AUTH_NO_ROLE` chỉ có `detail`, `code`: không username, không tên/SĐT, không giá vốn.
- Log server của các phiên chạy (`server.log`, `server_ed_batch3_real.log`): 0 dòng chứa SĐT/tên giả; không có Traceback liên quan.
- localStorage và console của người không nhóm không có SĐT/tên. Ảnh chụp chỉ dữ liệu giả `seed_qa`.
- Không có khoá mới trong AuditLog/API ngoài `is_superuser` (bool) và `code`; không tính ngược được giá vốn.

### Lỗi
Không có lỗi chặn.

### Quan sát (không chặn)
- **O1 (Low, có từ trước, không do lô này):** owner `POST /api/delivery/notes/` thân `{}` → 500 `IntegrityError ... sales_invoice_id NOT NULL`. Nên trả 400 thay 500. Nhánh này không đụng `delivery`.
- **O2 (Low):** đăng nhập có giới hạn tần suất (429) khi chạy nhiều phiên liên tiếp; đúng thiết kế, chỉ cần giãn script.
- **O3:** `/accounting/` không có trang gốc (404 tĩnh), chỉ `sales-invoices`, `purchase-invoices`; không liên quan lô.
- **Vận hành trước deploy production (nhắc từ 02c §B.4 bước 5):** đếm tài khoản `is_active`, không superuser, không nhóm; họ mất quyền vào ERP ngay sau deploy.

### Ghi chú kịch bản (lỗi của QA, không phải của sản phẩm)
Bảy dòng FAIL ở lượt chạy đầu của `ui.py` là do tôi: `/refunds/` không phải route ERP (404 tĩnh); nhãn "Quản trị hệ thống" nằm trong menu tài khoản chứ không ở thân trang `/overview/` (đã kiểm lại bằng cách mở menu, đạt ở 1280 và 360); "Nhân viên gọi xác nhận" không hiện ở thân trang `/` của `qa_cs1` (đã kiểm ở `/account/`, đạt). Một ca POST trả 404 vì tôi gõ sai đường dẫn hành động; kiểm lại bằng đường dẫn thật đều 403. Lượt chạy sau thay các route đúng, đều đạt.

### Lệnh đã chạy
- `setup.sh`: build ERP thật + mock, `migrate`, `bootstrap_masterdata`, `seed_qa --manifest` → `SETUP_DONE`.
- `runserver 127.0.0.1:8641`, `http.server` 3641 (thật) và 3642 (mock); API `api.py` 26/27 đầu tiên (1 ca do tôi gõ sai đường dẫn, sau đó 7/7 đường thật đều 403), `ui.py` (45/50 rồi 5 ca lỗi kịch bản đã sửa bằng `probe*.py`), `audit.py`.
- `regress.sh`: 5 kịch bản e2e hồi quy, tất cả rc=0, 0 dòng FAIL.
- `npm ci` + `tsc --noEmit` trong bản copy sạch: rc=0, rc=0.
- Đã tắt mọi server (8641, 8642, 3641, 3642).

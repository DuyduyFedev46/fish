# Phạm vi dữ liệu cấu hình — Ghi chú dev (03)
> be-dev · 2026-10-06 · nhánh `feat/pham-vi-du-lieu` (tách từ main `fa2368f`). Mục BE. Chưa push, chưa merge main.

## Lô 1 — PV-01 (ảnh chụp mốc), commit `bc32ebc`

Chỉ thêm file, không sửa code sản phẩm: `backend/apps/accounts/data_scopes/__init__.py` và `data_scopes/tests/`.

| File | Việc |
|---|---|
| `tests/fixtures.py` | Dữ liệu giả: 11 tài khoản (Chủ, Quản lý, NV kho, 2 NV giao, 2 CSKH, K+G, người không nhóm có quyền gán trực tiếp, superuser, ẩn danh), 16 đơn (mỗi đơn một khách), phiếu giao đủ trạng thái, 3 phiếu hàng hoàn, 5 phiếu nhập quanh nửa đêm giờ VN, 2 phiếu hoàn tiền. Giờ cố định 06/10/2026 10:00 giờ VN. |
| `tests/snapshot.py` | Bộ thu: gọi từng endpoint bằng từng tài khoản, ghi **sự kiện** (`status=`, `visible:<nhãn>`, `status:<nhãn>=404`, `pii:<nhãn>:<đường dẫn>` chỉ có/không giá trị, `extra:`). `diff_snapshots`, `APPROVED_DIFFS`. |
| `tests/test_scope_snapshot.py` | 9 test: AC1 (khớp mốc, đủ tài khoản × endpoint), AC2 (đổi luật thật bằng mock thì đỏ, in tài khoản/endpoint/dòng; mất quyền cũng là lệch), AC3 (đúng một ngoại lệ), AC4 (grep tệp mốc không có tên/SĐT/địa chỉ giả), tính tất định. |
| `tests/scope_snapshot_baseline.json` | Tệp mốc, sinh bằng `UPDATE_SCOPE_SNAPSHOT=1` trên code cũ. |

Endpoint trong mốc (mỗi nhóm gọi × 11 tài khoản): đơn (danh sách, chi tiết, tìm `?q=` theo SĐT và theo tên, lọc `?customer=`), hoá đơn bán (danh sách + tổng, chi tiết), phiếu hoàn tiền, phiếu giao (danh sách, `assigned_to=me`, `assigned_to=<người khác>`, chi tiết), hàng hoàn, phiếu nhập, hàng chờ gọi xác nhận (mặc định, `DONE`, `ESCALATED`, chi tiết, tìm theo SĐT), danh bạ khách mới (danh sách, `search`, chi tiết), `/customers/` cũ, dòng thời gian của đơn, phiếu giao, hàng hoàn, khách, phiếu nhập, dashboard, lệnh AI đọc đơn và phiếu giao. Xuất file: grep không thấy endpoint xuất CSV/XLSX (đúng với 02b §1.5) nên không có mục.

Lưu ý khi đọc mốc:
- `ai.orders_list` bị cắt theo `AI_RESULT_MAX_CHARS` (12/16 đơn): tất định nhưng chỉ phủ 12 dòng đầu; từng đơn vẫn được phủ riêng ở `ai.orders_detail`.
- Mốc ghi hành vi HIỆN TẠI kể cả chỗ lạ: người không nhóm có quyền xem đơn trực tiếp thấy 1 đơn (đơn gán cho mình) nhưng mở hàng chờ gọi xác nhận thì mọi chi tiết đều 404; NV kho hôm nay chưa thấy tên khách trên hoá đơn (ngoại lệ duyệt Q-4); `deliveries.other` của NV giao khác mình trả 403.
- Ngoại lệ duy nhất: `("warehouse_staff", "invoices.list", "+", "pii:*:customer_name")`, ghi "Duy duyệt 02/10 Q-4".
- Mốc dùng nhãn fixture, không pk. Chạy 2 lần cho cùng kết quả (có test).

## Lô 2 — PV-02 (cấu hình, resolver, GET)

### File đã sửa / thêm
- `backend/apps/accounts/models.py`: thêm `GroupAccessConfig`, `GroupDataScope` (đúng 02b §3).
- `backend/apps/accounts/migrations/0014_group_data_scopes.py` (schema, tự sinh), `0015_seed_group_data_scopes.py` (data).
- `backend/apps/accounts/data_scopes/catalog.py`, `resolver.py`, `services.py`, `README.md`.
- `backend/apps/accounts/capabilities/services.py` (thêm `version`, `data_scope_values`, `data_scopes`; `scopes` cũ dựng từ cấu hình), `registry.py` (bỏ `GROUP_SCOPES` và hằng `SCOPE_*`).
- Test mới: `data_scopes/tests/test_catalog.py`, `test_resolver.py`, `test_seed_migration.py`, `test_api_describe.py` (59 test mới). Sửa 2 file test cũ cho hợp khoá mới: `capabilities/tests/test_api_read.py` (thêm khoá vào `LIST_KEYS`, `DETAIL_EXTRA`), `test_registry.py` (test `GROUP_SCOPES` đổi sang kiểm `catalog.DEFAULT_GROUPS`).

### Endpoint (chỉ THÊM khoá, theo 02b §2.1, §2.2)
`GET /api/staff/groups/` mỗi nhóm thêm `"version": "1"` và `"data_scope_values": {"orders": "all", "deliveries": "all", "confirmation": "all_pending", "returns": "all", "receipts": "all", "customers": "all"}`.
`GET /api/staff/groups/<code>/` thêm `version`, `data_scope_values` và `data_scopes` (8 dòng D1..D8: `key, label, value, editable, customer_data, gate_capability, inactive_reason, note, options[{value,label,rank}]`). Ví dụ nhóm `delivery_staff`, dòng đơn:

```json
{"key": "orders", "label": "Đơn hàng", "value": "assigned_deliveries", "editable": true, "customer_data": true,
 "gate_capability": "view_orders", "inactive_reason": null, "note": null,
 "options": [{"value": "assigned_deliveries", "label": "Đơn có phiếu giao gán cho tôi", "rank": 0},
             {"value": "assigned_or_confirmation", "label": "Đơn có phiếu gán cho tôi hoặc trong phạm vi gọi xác nhận", "rank": 1},
             {"value": "all", "label": "Tất cả đơn", "rank": 2}]}
```
Quyền đọc không đổi (`CanManageStaff`; NV kho, NV giao, CSKH, Quản lý không có `manage_staff` → 403; chưa đăng nhập → 401).

### Migration
- `0014`: tạo 2 bảng. Lùi = `migrate accounts 0013` (xoá bảng).
- `0015`: gieo `GroupAccessConfig(row_version=1)` cho 5 nhóm và 24 dòng `GroupDataScope` (4 nhóm × 6 đối tượng; `owner` không có dòng). Giá trị chép cứng, `get_or_create` không ghi đè, D7 = `all` nếu nhóm **đang có** `sales.view_customer_list` lúc migrate. Không đụng `auth_group_permissions`. Phụ thuộc `accounts/0014` và `sales/0013`.
- Đã chạy thật trên SQLite tạm: `migrate` từ DB trống OK (5 cấu hình, 24 dòng; D7: manager `all`, delivery_staff `assigned_deliveries`, warehouse_staff và customer_service `none`), `migrate accounts 0013` lùi OK (2 bảng mất), `migrate` tiến lại OK, `makemigrations --check --dry-run` sạch.

### Rule BR đã cài / đã thể hiện
- BR-PQ-33 (cấu hình theo nhóm, mặc định = hiện trạng): catalog + migration 0015, test `defaults == seed == bảng contract`.
- BR-PQ-34 (rộng nhất trong các nhóm đủ điều kiện): `resolver.resolve_data_scopes`. Test R1b: người K+G, K tắt `view_orders` mà D1 lưu `all` → chỉ đơn gán (G).
- UC-6 / PV-02-AC4: người không nhóm, nhóm thiếu dòng, giá trị lưu hỏng → rank 0.
- S-5: `owner` và superuser → rộng nhất mọi đối tượng.
- BR-PQ-36: nhớ trên `user._data_scope_cache`; user nạp mới thấy cấu hình mới (có test). Phân giải ≤ 3 truy vấn cho cả 8 đối tượng (có test), người ẩn danh 0 truy vấn.
- Bất biến 1 và 9: mô tả phạm vi chỉ mã và nhãn cố định, test không có giá vốn; Lô 2 không thêm đường đọc dữ liệu khách nào.
- AuditLog và khoá lạc quan: Lô 2 chỉ có cột `row_version` và hiển thị `version`. Ghi (so `row_version`, 409, AuditLog `change_group_data_scopes`) thuộc Lô 5.

### Chứng cứ không đổi hành vi
Test mốc Lô 1 (`test_scope_snapshot`, 9 test) xanh nguyên sau Lô 2 mà không phải sinh lại mốc. Test mới `test_pv02_ac3_default_matrix_per_group_equals_todays_behaviour` ghi ma trận phân giải của 5 nhóm trên DB mới.

### Lệch so với 02b (cần techlead biết)
1. **`default_permissions = ()` cho CẢ HAI model.** 02b chỉ ghi cho `GroupDataScope`. Thêm cho `GroupAccessConfig` để Django không sinh thêm 4 permission `add/change/delete/view` vô chủ (cấu hình chỉ sửa qua service). Test khẳng định không có permission nào của 2 model.
2. **`gate_capability` trả `null` khi mã việc chưa có ở registry**: V1 `view_sales_invoices` chưa tồn tại tới Lô 3 (PV-07), nên dòng `invoices` hiện `gate_capability: null`. Từ Lô 3 tự thành `"view_sales_invoices"` (catalog đã khai sẵn).
3. **`scopes` cũ**: nhãn giữ như hôm nay cho cấu hình mặc định (`Tất cả`, `Được gán`, `Tất cả khách`, `Không xem`) để test cũ và FE không đổi. Khác biệt duy nhất: CSKH ở `orders` nay là "Được gán hoặc trong phạm vi gọi xác nhận" thay chữ cũ "Trong phạm vi gọi"; CSKH ở `deliveries` là "Được gán". `customers` vẫn tính theo quyền thực tế (M2), vì PUT của Lô 2 chưa ghi D7 (PO-Q1 thuộc Lô 5).
4. D2 của owner hiển thị `value: "follows_orders"` (không phải "all") nhưng vẫn có `note: "Chủ luôn thấy tất cả"` và `editable: false`; D8 của owner `value: "all"`.
5. Hàm `catalog.valid_or_narrowest`, `rank_of`, `widest_value`, `narrowest_value`, `ranked_options`, `stored_objects` là hàm phụ thêm (không có trong bảng 02b §1.2), phục vụ resolver và services.

### Việc còn nợ / lưu ý cho lô sau
- **R9 / D-3 (đã quan sát, cần đếm trên production trước deploy):** với nhóm thật, các đối tượng mà nhóm không đủ điều kiện nhận rank 0 (K: gọi xác nhận → `pending_or_called_recently`, khách → `none`; G và C: phiếu nhập → `created_by_me_today`, hoá đơn → `assigned_deliveries`). Tất cả đều nằm sau cổng quyền Tầng 1 nên hôm nay không đường nào lộ; nhưng khi PV-03..PV-07 chuyển đường đọc sang resolver thì người **không nhóm có quyền gán trực tiếp** đổi hành vi theo đúng R9.
- Resolver chưa có chỗ gọi nào ở màn nghiệp vụ (đúng ranh giới PV-02). Hàm phạm vi theo đối tượng (`scope_orders_for(value=)`, ...) là Lô 3..4.
- `backend/README.md` và `apps/accounts/README.md` chưa cập nhật bản đồ module (ngoài danh sách file của 02b); đã có `data_scopes/README.md`.
- Môi trường worktree: thư mục `.claude/worktrees/pham-vi/backend/` không có `.env` và `staticfiles/` (gitignored), nên tôi tạo hai symlink tới bản ở `backend/` chính để chạy test (33 test admin lỗi manifest nếu thiếu `staticfiles`). Symlink không được commit.

## Lô 3 — PV-03, PV-07 (đơn, hoá đơn đọc phạm vi cấu hình; việc V1, V2)

> be-dev · 2026-10-07 · nhánh `feat/pham-vi-du-lieu` (đã `git merge main` lên `7110254`). Số migration sales là **0015, 0016**
> (02b ghi 0014/0015 là số cũ, vì main đã có `sales/0014_salesorder_cancel_note`).

### File đã sửa / thêm
- Registry: `accounts/capabilities/registry.py` thêm `view_sales_invoices` (V1, perms `sales.view_salesinvoice` + `sales.view_salesinvoiceline`) và
  `view_order_customer_info` (V2, perm `sales.view_order_customer_info`), cả hai mục "Bán hàng", không `owner_only`, perms rời nhau.
  `accounts/auth/services.py`: nhãn `CAPABILITY_LABELS` cho V2.
- Model + migration: `sales/models/orders.py` (permission mới trong `SalesOrder.Meta`),
  `sales/migrations/0015_salesorder_view_order_customer_info.py` (AlterModelOptions, tự sinh),
  `sales/migrations/0016_grant_view_order_customer_info.py` (data, cấp V2 cho `owner`, `manager`, `warehouse_staff`, `delivery_staff`, `customer_service`;
  lùi = gỡ khỏi 5 nhóm; mẫu `sales/0013`). V1 không cần migration.
- Phạm vi: `sales/orders/scope.py` (`scope_orders_for(user, qs, *, value=None)`, `orders_scope_value`), `delivery/pii_scope.py`
  (`annotate_order_pii_visible(user, qs, *, value, now=None)`: nhánh gọi xác nhận chỉ khi `value == "assigned_or_confirmation"`),
  `sales/orders/api.py`, `sales/orders/serializers.py`, `sales/payments/{invoice_list,serializers,api}.py`, `sales/refunds/serializers.py`,
  `sales/customers/permissions.py` (`can_view_order_customer_info`, `customer_hidden_reason`).
- Test mới: `accounts/data_scopes/tests/test_orders_invoices_scope.py` (35 test, dùng lại dữ liệu giả của PV-01). Test cũ phải sửa vì hợp đồng đổi có chủ ý:
  `sales/orders/tests/test_s10_api.py` (thêm khoá), `sales/payments/tests/test_invoice_list.py` (thêm khoá; test M1 viết lại theo V2),
  `common/tests/test_auditlog_note_no_free_text.py` (serializer không có người gọi thì che), `accounts/auth/tests/test_s47_me_labels.py` (V2 nằm trong danh sách việc Tầng 2 của mọi nhóm),
  `delivery/tests/test_confirmation_role_scope.py` (CSKH có thêm V2).

### Hành vi
- **Một hàm cho đơn:** `scope_orders_for` đọc D1 qua `resolve_data_scope` (không còn `has_full_delivery_scope`/`is_customer_service` ở đường đơn). `all` → qs;
  `assigned_deliveries` → phiếu gán cho tôi; `assigned_or_confirmation` → thêm đơn trong phạm vi gọi xác nhận. Danh sách, chi tiết, tổng, `?q=`,
  "Tiếp theo · Đã làm" (`orders/next_steps.py`), lệnh "Nhờ" và AI (gọi lại view DRF) đều đi qua đây. Ngoài phạm vi: 404 (S-7).
- **Hoá đơn:** `scope_invoices_for` dùng D2 (= D1 của chính nhóm có `view_salesinvoice`), nên Q-7 giữ: V1 bật, `view_orders` tắt, D1 = `assigned_deliveries` vẫn 200 theo D1.
  `build_totals` dùng cùng queryset nên tổng chỉ tính hoá đơn trong phạm vi.
- **Che ô khách (V2 + cửa sổ):** `customer_hidden_reason(user, obj)` = `"not_permitted"` (thiếu V2) trước `"expired"` (`pii_visible=False`) rồi `null`.
  Khoá `customer_hidden_reason` mới (chỉ thêm) ở danh sách đơn, chi tiết đơn (cấp trên cùng), danh sách hoá đơn, phiếu hoàn tiền. Khi che: tên/SĐT/địa chỉ = `null`,
  `cancel_note = ""` (giữ luật cũ, nay che cả khi thiếu V2). Serializer không có `request` (không có người gọi) thì mặc định che.
- **`?q=`:** thiếu V2 thì chỉ tìm theo mã đơn (không dò SĐT/tên). Khi D1 ≠ `all` giữ ràng buộc `pii_visible`.
- **Phiếu hoàn tiền:** tên/SĐT theo V2 (D-1: V2 gồm phiếu hoàn). Khi che, `customer_name`/`customer_phone` = `null` (trước đây chuỗi rỗng khi không có đơn).
- **Dòng `invoices` ở `GET /api/staff/groups/<code>/`:** `gate_capability` nay là `"view_sales_invoices"` (test `test_pv07_invoices_row_gate_capability_is_registry_key`).

### JSON mẫu (chỉ thêm khoá)
```json
// GET /api/sales/orders/ (một dòng) khi nhóm thiếu V2
{"id": 7, "code": "SO-PV-04", "status": "PROCESSING", "customer_name": null, "customer_phone": null,
 "total_amount": "100000", "customer_hidden_reason": "not_permitted", "...": "..."}
// GET /api/sales/orders/<id>/ khi phiếu đã kết thúc quá 7 ngày (G có V2, D1 = assigned_deliveries)
{"customer": {"name": null, "phone": null, "address": null}, "customer_hidden_reason": "expired", "cancel_note": "", "...": "..."}
// GET /api/sales/invoices/ (một dòng)
{"id": 3, "code": "INV-PV-04", "order_code": "SO-PV-04", "customer_name": "…hoặc null", "customer_hidden_reason": null, "amount": "100000"}
```
Khoá việc cho `PUT /api/staff/groups/<code>/capabilities/`: `view_sales_invoices`, `view_order_customer_info` (02b không đặt tên khoá V2; tôi chọn theo tên permission).

### Rule BR đã cài
BR-PQ-33/35 (đơn, hoá đơn đọc cấu hình, một hàm cho mọi đường), BR-PQ-34 (cổng quyền Tầng 1 vẫn trước: `all` + tắt `view_orders` → 403), BR-PQ-36 (đổi cấu hình hiệu lực ở request kế),
BR-PQ-37 (V1, hoá đơn theo D2), BR-PQ-38 (V2), SR-PII-02 (cửa sổ chỉ khi phạm vi ≠ `all`), S-1/bất biến 1 (test không có `unit_cost`/`cogs`/`gross_profit` cho NV kho, NV giao), bất biến 9 (test không tên/SĐT/địa chỉ giả khi che, tra đơn công khai không đổi).

### Lệch so với 02b (cần techlead biết)
1. **Migration đánh số 0015, 0016** thay vì 0014, 0015 (main đã có 0014).
2. **Hoãn hai cửa phụ của §1.5: phạm vi D1 cho phiếu hoàn tiền (`refunds/api.py::get_queryset`) và dashboard (`reports/dashboard_api.py`).** Tôi đã cài và test xanh, nhưng khi chạy mốc PV-01 thì
   **người không nhóm có quyền gán trực tiếp (`direct_permissions`)** đổi hành vi (dashboard: 15 → 1 đơn chờ, doanh thu 200000 → 0, mất 10 dòng; phiếu hoàn: 200 → 404, mất 2 phiếu). Đúng R9/D-3, mà rule giao việc cấm thêm
   `APPROVED_DIFFS` cho `direct_permissions`, nên tôi gỡ hai phần này (git checkout), KHÔNG để lại code lửng. Hiện: tên/SĐT trên phiếu hoàn đã theo V2, nhưng **dòng** phiếu hoàn và số liệu dashboard vẫn chưa theo D1.
   Với mặc định (Chủ, Quản lý, NV kho = `all`) không có khác biệt; chỉ hở khi Chủ thu hẹp D1 của nhóm có `view_refund`/`view_dashboard`. Cần Duy trả lời D-3 (hoặc điều phối viên duyệt diff `direct_permissions` cho hai endpoint này) rồi làm tiếp ở Lô 4 hoặc 5.
3. **`APPROVED_DIFFS` có hai mục** (02b: một mục): thêm `("warehouse_courier", "invoices.list", "+", "pii:*:customer_name")`. Người kiêm nhiệm NV kho + NV giao có V2 qua nhóm NV kho và D2 = `all` như NV kho, nên cùng ngoại lệ Q-4. Test PV-01-AC3 sửa
   thành kiểm đúng hai mục và không có mục nào cho `direct_permissions`.
4. **Fixture PV-01: `DIRECT_PERMISSIONS` thêm `sales.view_order_customer_info`** (V2 gán trực tiếp). V2 chỉ được migration cấp cho 5 nhóm; người không nhóm đang xem tên khách trên đơn hôm nay sẽ **mất** tên cho tới khi Chủ cấp V2 cho họ. Đây là
   hệ quả R9/D-3 của 02b "V2 = `user.has_perm`", không phải ngoại lệ được duyệt: đếm trên production trước deploy (D-3), nếu > 0 thì hỏi Duy từng người hoặc cấp V2 trực tiếp cho họ.
5. **`apps/ai/policy/rules.py` (ngoài danh sách file của Lô 3): thêm `customer_hidden_reason` vào `SCRUB_PII_KEYS`.** Khoá mới làm mỗi dòng dài hơn nên lệnh AI đọc đơn bị cắt `AI_RESULT_MAX_CHARS` mất một dòng (mốc `ai.orders_list` của Chủ, Quản lý, NV kho, superuser mất `visible:order_assigned_other`).
   Bỏ khoá này khỏi kết quả AI giữ nguyên đầu ra AI (AI không cần cờ này).
6. **Khoá `customer_hidden_reason` ở phiếu hoàn tiền** kèm `customer_name`/`customer_phone` thành `null` khi che: FE (Lô 7) cần chịu `null` ở ô này (trước là chuỗi).

### Kiểm chứng Lô 3 (chạy trong lượt làm)
- Trước Lô 3 (sau merge main): 3022 test OK. Sau Lô 3: `manage.py test` toàn bộ **3057 test, OK** (+35 mới, 0 failure, 0 error). Mốc PV-01 (10 test) xanh.
- `makemigrations --check --dry-run`: `No changes detected`. `check_naming.py`: không có vi phạm ở file của Lô 3 (chỉ 2 file FE từ main).

### Số truy vấn (R8)
Test `QueryBudgetTests`: danh sách đơn (NV giao) và danh sách hoá đơn (NV kho) tăng tối đa 3 truy vấn so với khi giả lập resolver trả hằng (phân giải nhớ trên user, gọi nhiều lần vẫn 1 lần).

### Việc còn nợ / chuyển lô
- Hai cửa phụ hoãn ở mục 2 (refunds, dashboard) chờ D-3.
- Lô 4 sẽ bỏ `has_full_delivery_scope` ở delivery, returns, confirmation; hàm vẫn còn ở `common/api.py` (Lô 6 xoá). Test mốc AC2 còn mock `apps.delivery.api.has_full_delivery_scope`.
- `sales/orders/api.py` vẫn kiểm `?customer=` bằng `can_view_customer_directory` (403) và chưa lọc theo D7: thuộc Lô 4 (PV-05-AC6).
- `naming`: `scripts/check_naming.py` đang báo 2 file FE mới từ main (`frontend/components/ContactButton.tsx`, `frontend/features/site/components/SiteLegalFooter.tsx`, chữ `nguoi` trong khoá `thong-tin-nguoi-ban`), không phải file của Lô này.

## Lô 4 — PV-04, PV-05, PV-06 (phiếu giao, hàng hoàn, gọi xác nhận, khách, phiếu nhập đọc phạm vi cấu hình)

> be-dev · 2026-10-07 · nhánh `feat/pham-vi-du-lieu` (đã merge main `151b56e`, có W37 L1).

### File đã sửa / thêm
- **Mới:** `delivery/scope.py` (D3: `deliveries_scope_value`, `scope_deliveries_for`, `deliveries_window_applies`), `sales/customers/scope.py` (D7: `customers_scope_value`,
  `sees_all_customers`, `scope_customers_for`), `purchasing/receipts/scope.py` (D6: `receipts_scope_value`, `scope_q`, `scope_receipts_for`, `cancel_scope_q`, `vietnam_day_bounds`).
- **Đổi:** `delivery/{api,next_steps,serializers}.py`, `delivery/confirmation/{scope,api,serializers}.py` (`note_in_customer_service_scope` đổi tên `note_in_confirmation_scope`, thêm
  `confirmation_scope_value`; bỏ `is_customer_service`), `inventory/returns/scope.py` (D5), `sales/customers/{api,directory_api,next_steps,serializers}.py`, `sales/orders/api.py` (lọc `?customer=`),
  `purchasing/receipts/{api,services,next_steps}.py` (tách `can_cancel_receipt`, `can_cancel_any_receipt`, không đổi hành vi huỷ).
- **Ngoài danh sách file của 02b Lô 4:** `common/api.py` xoá `FULL_SCOPE_GROUPS`, `has_full_delivery_scope`, `CUSTOMER_DIRECTORY_GROUPS`, `sees_customer_directory`. Lý do: PV-05-AC8 đòi grep không còn các tên này
  và sau Lô 4 không còn nơi dùng (kiểm bằng grep), nên xoá luôn thay vì để tới Lô 6. Phần "dọn" còn lại của Lô 6 (bỏ `scopes` cũ, test quét PV-12) không đổi.
- **Test mới:** `accounts/data_scopes/tests/test_deliveries_customers_receipts_scope.py` (55 test, dùng lại fixture PV-01). **Test cũ sửa (hợp đồng đổi có chủ ý):** `test_scope_snapshot.py` (mock AC2 đổi sang
  `apps.delivery.scope.resolve_data_scope`), `sales/customers/tests/test_directory_api.py` và `test_directory_permission.py` (hai test "người chỉ có quyền thêm" nay đặt quyền và D7 = all ở
  nhóm NV kho, vì người không nhóm có D7 = none), `delivery/tests/test_timeline_customer_service.py` (chỉ docstring), `scope_snapshot_baseline.json` (xem Lệch 2).

### Hành vi
- **D3 phiếu giao:** `scope_deliveries_for` dùng cho list, detail, `assigned_to=me`, đổi trạng thái, giao người, tem, tra tem, dòng thời gian `delivery`. `assigned` → `assigned_to=user`; `all` → mọi phiếu.
  `pii_restricted` (cửa sổ SR-PII-02) bật khi D3 khác `all`, nghĩa là nhóm ở `all` không bị cửa sổ (PV-04-AC5). Lọc `assigned_to=<người khác>` vẫn 403 khi D3 khác `all`. Phiếu `CANCELLED` gán cho NV giao
  vẫn nằm trong queryset nên nhận 400 `BR-GH-24` (W37 S2-AC2, có test). Khoá `order_status` của `POST .../status/` giữ nguyên.
- **D5 hàng hoàn:** `scope_returns_for`, `scope_delivery_notes_for` (ô chọn phiếu giao ở form tạo) đọc D5, độc lập với D3.
- **D4 gọi xác nhận:** `note_in_confirmation_scope(user, note, now=, value=)`. `all_pending` → True; `pending_or_called_recently` → điều kiện cũ; view tính D4 một lần, đưa vào context serializer (`scope_value`).
  `customer_service_note_q` giữ nguyên nghĩa "điều kiện hẹp của D4" cho nhánh `assigned_or_confirmation` của D1.
- **D7 khách:** `scope_customers_for` cho `/customers/` (cũ), danh bạ mới (list, retrieve, `search`, `PATCH`), dòng thời gian khách và lọc đơn `?customer=`. `all` → mọi khách; `assigned_deliveries` → khách của đơn có phiếu
  thoả `courier_visible_note_q` (dùng `pk__in`, không `distinct`, để giữ annotate của danh bạ); `none` → rỗng. `?customer=<id>` ngoài D7 → danh sách đơn rỗng (200), cổng 403 theo `view_customer_list` giữ trước.
  API cũ trả `CustomerSerializer` khi D7 = `all`, ngược lại `CourierCustomerSerializer`. Danh bạ mới: khi D7 khác `all` bỏ `note`, `default_address` (xem Lệch 4).
- **D6 phiếu nhập:** `scope_receipts_for` cho list, detail, sửa (PATCH), `submit`, dòng thời gian `receipt` (thêm `scope_fn`). `created_by_me_today` dùng `timezone.localtime`, mốc 00:00 giờ VN hôm nay tới 00:00 ngày mai, so với
  `created_at` UTC. Test ngày giờ cố định: 10:00 06/10, 23:55 05/10, qua nửa đêm 23:59 → 00:01 (nháp mở trước nửa đêm gửi sau nửa đêm: 404, nháp không đổi, Quản lý vẫn sửa được).
  **Huỷ phiếu:** action `cancel` dùng `cancel_scope_q` = phiếu trong D6 hoặc phiếu qua luật huỷ cũ (người tạo, hoặc Quản lý/Chủ). Phiếu ngoài cả hai → 404; trong D6 mà không phải người tạo/Quản lý → 403 như hôm nay.
  Lưu ý khi viết: `Q() | Q(x)` bỏ mất vế rỗng; `cancel_scope_q` xử lý riêng trường hợp D6 = `all` (đã có test PV-06-AC6).
- **Lỗ dữ liệu cá nhân QA W37 N2:** phản hồi `POST /api/delivery/notes/{id}/status/` (và `assign`, danh sách, chi tiết) dùng cùng `DeliveryNoteSerializer._customer_data_hidden`: ẩn tên, địa chỉ, SĐT, `note`,
  `recipient_*`, `failure_note` (giá trị `null`, giữ khoá) khi (1) người gọi KHÔNG có V2 `sales.view_order_customer_info`, hoặc không có người gọi, hoặc (2) D3 khác `all` và phiếu quá cửa sổ. Trước đây chỉ có (2).
  Mặc định không đổi gì: Chủ, Quản lý, NV kho, NV giao, CSKH đều có V2 từ migration `sales/0016`. Chủ tắt V2 cho một nhóm thì phiếu giao cũng hết tên, địa chỉ (xem Lệch 3).

### Rule BR đã cài
BR-PQ-33/35 (phiếu giao, hàng hoàn, gọi xác nhận, khách, phiếu nhập đọc cấu hình, một hàm cho mọi đường), BR-PQ-34 (cổng Tầng 1/2 đứng trước, có test 403 khi `all` nhưng thiếu quyền), BR-PQ-36 (đổi cấu hình hiệu lực ở request kế),
BR-PQ-10 (huỷ phiếu nhập giữ luật cũ), BR-GH-06/18/24, SR-PII-02 (cửa sổ chỉ khi D3 khác `all`), S-7 (404 không lộ), bất biến 1 (test không khoá giá vốn ở phiếu giao, hàng hoàn, phiếu nhập),
bất biến 9 (test không tên/SĐT/địa chỉ giả khi che, danh bạ hẹp không có `note`/`default_address`, phiếu giao khi V2 tắt).

### Lệch so với 02b / yêu cầu (cần techlead biết)
1. **`common/api.py` xoá bốn tên cũ ngay ở Lô 4** (ngoài danh sách file). Lý do ở trên (PV-05-AC8).
2. **Người không nhóm (quyền gán trực tiếp), R9/D-3: hành vi ĐỔI, đã sinh lại mốc cho đúng tài khoản `direct_permissions`, KHÔNG thêm `APPROVED_DIFFS`.** Phần 02b §7 D-3 đã tiên liệu ("D6 hẹp lại, D7 none, D4 rank 0").
   Mốc `scope_snapshot_baseline.json`: chỉ đổi dòng của `direct_permissions` ở `receipts.list/detail`, `directory.list/detail/search`, `customers.list/detail`, `guidance.receipt`, `guidance.customer`; các tài khoản khác và hai mục Q-4 giữ y nguyên (so với HEAD bằng script).
   - D6: người không nhóm chỉ còn thấy phiếu nhập do mình tạo trong ngày (trước: mọi phiếu). Test `UngroupedUserTests.test_ungrouped_receipts_scope_is_created_by_me_today`.
   - D7: người không nhóm có D7 = `none`: danh bạ mới rỗng, `/customers/` rỗng (trước: danh bạ thấy mọi khách nếu có `view_customer_list`; `/customers/` thấy khách của phiếu gán cho mình).
   - **D4 là chỗ tôi KHÔNG theo chữ 02b:** 02b ghi "D4 rank 0" (người không nhóm vào phạm vi `pending_or_called_recently`), nhưng đó là MỞ THÊM dữ liệu khách (phiếu đang chờ gọi) cho người chưa từng được cấp phạm vi. Tôi giữ hành vi cũ:
     `confirmation_scope_value` trả giá trị nội bộ `none` (không mục nào trong phạm vi) cho người không có nhóm đủ điều kiện và không phải superuser. Mốc `confirmation.*` của họ không đổi. Nếu Duy muốn theo chữ 02b thì bỏ nhánh đó (1 chỗ) và sinh lại mốc.
   - Việc cần làm trước khi migrate production (D-2/D-3, điều phối viên): đếm số người không nhóm có `view_purchasereceipt` hoặc `view_customer_list` hay `view_customer` trực tiếp; họ sẽ mất phạm vi như trên cho tới khi được xếp vào nhóm.
3. **V2 áp cho phiếu giao (đóng N2).** 02b/D-1 chỉ nêu V2 cho đơn, hoá đơn, phiếu hoàn tiền. Tôi mở rộng sang tên/SĐT/địa chỉ trên phiếu giao vì nếu không, Chủ tắt V2 cho NV kho vẫn lộ khách qua `/delivery/notes/` và qua phản hồi đổi trạng thái.
   Hệ quả: nếu Chủ tắt V2 cho NV giao thì họ không còn thấy địa chỉ giao trên phiếu. Đó là lựa chọn của Chủ; mặc định V2 bật cho cả 5 nhóm nên không đổi gì. Cần techlead xác nhận hướng này; nếu không muốn thì gỡ dòng V2 trong `_customer_data_hidden`
   (phản hồi đổi trạng thái vẫn cùng luật với chi tiết).
4. **Danh bạ mới ẩn `note`, `default_address` khi D7 khác `all`** (02b không nói). Hôm nay nhóm khác Chủ/Quản lý nhận 403 nên không có hợp đồng cũ để giữ; ẩn theo cùng nguyên tắc `CourierCustomerSerializer` (bất biến 9). Mặc định Quản lý (`all`) không đổi.
5. **`has_full_delivery_scope` còn trong mock của test AC2** đã thay bằng `apps.delivery.scope.resolve_data_scope`; test quét PV-12 sau này không bị vướng.

### Kiểm chứng Lô 4 (chạy trong lượt làm)
- Trước khi sửa: 28 trong 51 test mới đỏ (đúng lý do: 404/403 sai, tên cũ còn).
- `manage.py test` toàn bộ (DJANGO_DEBUG=1): **3148 test, OK, skipped=2** (hai test đua Postgres). Mốc PV-01 (10 test) xanh sau khi sinh lại dòng `direct_permissions`.
- `makemigrations --check --dry-run`: `No changes detected` (không có migration trong Lô này). `check_naming.py`: chỉ báo hai file FE có sẵn từ main (`ContactButton.tsx`, `SiteLegalFooter.tsx`), không có file của Lô 4.

### Việc còn nợ / chuyển lô
- C1 (Lô 5): phạm vi D1 cho `refunds/api.py::get_queryset` và dashboard vẫn chưa làm (chờ D-3, như review Lô 3). Lô 4 không đụng.
- Lô 5: ô D7 phải có `note` cho nhóm lưu `all` mà thiếu `view_customer_list` (L4); PUT B4 phải ghi D7 khi bật "Xem khách hàng" (PO-Q1). Lô 4 và Lô 5 lên production CÙNG lượt (M2).
- Lô 6: `GET /api/staff/groups/` vẫn còn khoá `scopes` cũ; test quét PV-12 nên thêm `is_customer_service`, `has_full_delivery_scope` (đã sạch từ Lô 4).
- FE (Lô 7): ô khách trên phiếu giao nay có thể `null` vì V2 tắt, ngoài `null` do quá cửa sổ; chưa có `customer_hidden_reason` ở phiếu giao (không thêm khoá mới).

## Kiểm chứng (chạy trong lượt làm)
- `manage.py test` toàn bộ trước Lô 1: 2850 test (suy ra 2859 − 9). Sau Lô 1: **2859 test, OK**. Sau Lô 2: **2918 test, OK** (0 failure, 0 error).
- `makemigrations --check --dry-run`: `No changes detected`.
- `migrate` từ DB SQLite trống, lùi `accounts 0013`, tiến lại: OK (xem trên).
- `python3 scripts/check_naming.py`: OK, không phát sinh vi phạm mới.

## Vòng sửa theo review techlead (06/10, `03b-review-techlead.md`)

Thứ tự đã làm: M1+L1 (commit riêng, sinh lại mốc trên HEAD chưa sửa resolver) → H1 → L2.

- **M1 + L1 (commit `adc9ba9`):** mốc phủ thêm 15 nhóm hành động: claim, ghi cuộc gọi, huỷ gọi, đổi người nhận (gọi xác nhận); tạo, sửa, huỷ hàng hoàn; sửa, gửi, huỷ phiếu nhập; assign, set_status, xem tem, in tem, huỷ tem (phiếu giao). Mỗi hành động chạy với mọi dòng mẫu (trong và ngoài phạm vi) cho mọi tài khoản, bọc `transaction.atomic()` rồi `set_rollback(True)`, ghi `status:<nhãn>=<mã>`. Có test chứng minh dữ liệu không đổi sau khi thu. Dashboard ghi thêm `extra:kpis.revenue_today=<giá trị>`; fixture cho 2 hoá đơn phát hành đúng ngày cố định để số này khác 0 (200000).
  Lưu ý: `returns_create` của Chủ và NV kho luôn 400 (validate phiếu giao, không phải lỗi quyền), nên nhánh "tạo thành công" không có trong mốc; nhánh phạm vi (200/400 so với 404 theo phiếu giao) vẫn phủ qua NV giao.
- **H1:** `catalog.ScopeObject` thêm `full_perm` và `capped_value` (D7: `sales.view_customer_list`, `assigned_deliveries`). Resolver: nhóm đủ điều kiện nhưng thiếu `full_perm` thì đóng góp tối đa `capped_value`. Sửa test sai cũ (Quản lý mất `view_customer_list` nay nhận `assigned_deliveries`), thêm 6 test: G lưu `all` thiếu quyền, G có lại quyền, G lưu `none`, K+G mượn `all` (kết quả `assigned_deliveries`, nhóm gốc G), nhóm không có quyền nào, Quản lý. Mốc PV-01 giữ xanh, không sinh lại sau H1.
- **L2:** `resolver.forget(user)`; gọi trong `staff/services.py` ở `create_staff` và `set_groups` (xoá cả đối tượng của người gọi lẫn bản nạp lại). Có 3 test. `staff/services.py` nằm ngoài danh sách file của 02b Lô 2 nhưng là nơi đổi nhóm duy nhất.

### Nợ chuyển lô
- **M2 (Lô 4, Lô 5, 02c):** (a) Lô 4 và Lô 5 lên production CÙNG lượt, không deploy Lô 4 riêng (PUT B4 chưa ghi D7 tới Lô 5). (b) Lệnh đếm D-2 in riêng cờ "manager có `sales.view_customer_list`"; nếu không có thì hỏi Duy trước khi migrate (seed D7 = `none`, Quản lý mất API khách cũ từ Lô 4).
- **L3 (Lô F1):** mock FE `erp-console/features/permissions/mock.ts` còn chữ "Trong phạm vi gọi"; sửa theo BE ("Được gán hoặc trong phạm vi gọi xác nhận", "Được gán"). FE xử lý `gate_capability: null` bằng `inactive_reason`.
- **L4 (Lô 5):** dòng D7 lưu `all` mà nhóm thiếu `view_customer_list` phải có `note`, ví dụ "Bật Xem khách hàng để thấy tất cả khách" (giá trị hiệu lực là `assigned_deliveries`).
- **L2 phần Lô 5:** bước "trước" của `rows_losing_access` gọi `resolve_data_scopes(member, overrides={})` (`{}` khác `None` nên không bị nhớ). Test Lô 3+ đổi cấu hình dùng `User.objects.get(pk=…)` mới.
- Lô 3/4 không được thêm `APPROVED_DIFFS` cho `direct_permissions` khi Duy chưa trả lời D-3.

## Lô 4 M1 + Lô 5 — PV-08, PV-09 (BE), PV-10 (BE), C1, L1, L4, `/me`

> be-dev · 2026-10-08 · nhánh `feat/pham-vi-du-lieu`, sau review techlead Lô 4 (`f4eec0b`). Commit: M1 `090e6ef`, Lô 5 `5457c2d`, C1 (commit sau).

### M1 (review Lô 4, chỉ tệp test)
`scope_snapshot_baseline.json`: dòng `direct_permissions` về như `151b56e`. `snapshot.py` thêm `PENDING_DUY_DIFFS` (mỗi mục chú thích "CHỜ Duy D-3"), `is_approved` chấp nhận `APPROVED_DIFFS + PENDING_DUY_DIFFS`.
Test: mọi mục thuộc `direct_permissions` và chỉ thu hẹp; `APPROVED_DIFFS` vẫn không có `direct_permissions`. Lô 5 (C1) thêm vào danh sách này `refunds.*` và `dashboard.summary` (xem dưới). **Không merge main khi `PENDING_DUY_DIFFS` còn mục.**

### File đã sửa / thêm (Lô 5)
- `accounts/capabilities/{services,api,next_steps}.py`, `accounts/data_scopes/services.py`, `config/api_urls.py` (route preview), `accounts/auth/services.py` (`is_superuser`), `inventory/returns/scope.py` (tham số `value` cho xem trước).
- C1: **mới** `sales/refunds/scope.py`; sửa `sales/refunds/api.py` (`get_queryset`), `reports/dashboard_api.py`.
- Test mới: `data_scopes/tests/test_group_save_scopes.py` (46), `test_refunds_dashboard_scope.py` (12), `test_query_budget_and_race.py` (3 + 1 đua Postgres, bỏ qua trên SQLite).
- Test cũ sửa (hợp đồng đổi có chủ ý): mọi lệnh PUT của `capabilities/tests/*` gửi `version` qua helper `put_caps` (`base.py`); `test_api_read`, `test_api_write` (bật Xem khách hàng khi D7 = none phải gửi kèm `scopes.customers`, bật lại việc trên nhóm lưu `all` phải xác nhận, theo 02b §2.3 bước 10, 11); hai test khoá khoá `/me` thêm `is_superuser`.

### Endpoint (đúng 02b §2.3–§2.5, không đổi hợp đồng)
- `PUT /api/staff/groups/<code>/capabilities/` thân `{"version": "41", "capabilities"?: {...}, "scopes"?: {"receipts": "created_by_me_today"}, "confirm_customer_data_widening"?: true}`. Thứ tự kiểm 1 đến 12 như bảng 02b. 200 trả body như GET chi tiết; không có thay đổi thật thì không AuditLog và không tăng `version`.
  - 409 `GROUP_CHANGED` "Nhóm này vừa được người khác đổi. Tải lại để xem bản mới." (khoá dòng `GroupAccessConfig`, `row_version` tăng đúng 1 lần cho cả việc lẫn phạm vi).
  - 400 `CUSTOMER_DATA_WIDENING_UNCONFIRMED` kèm `impact` (cùng nội dung xem trước): `{"impact": {...}, "detail": "...", "code": "..."}`.
  - AuditLog `change_group_data_scopes`: `changes = {"receipts": {"from": "all", "to": "created_by_me_today"}}` (+ `"customer_data_widening_confirmed": true`). Cờ nằm ở dòng phạm vi nếu có đổi phạm vi, không thì ở dòng việc; dòng thời gian và `capability_change_label` bỏ qua khoá không phải mã việc.
- `POST /api/staff/groups/<code>/permissions-preview/` thân như PUT không cần `version` và `confirm…`. Trả `{"widens_customer_data", "widened": [{"key","from","to"}], "affected_members": [{"id","display_name"}], "affected_count", "message", "already_wider_elsewhere": [{"id","display_name","via_group","key"}], "narrowed": [{"key","from","to","rows_losing_access"}]}`.
  `widened[].from/to` là giá trị ĐÃ LƯU (L11, ca cổng vừa mở cho `from == to`). `rows_losing_access` đếm dòng chưa kết thúc (đơn BOOKED/PAID/PROCESSING, phiếu giao chưa xong, hàng hoàn Nháp, phiếu nhập Nháp, việc gọi đang mở), gộp không trùng qua các thành viên; khách = 0.
- `GET …/<code>/`: `timeline` có sự kiện `kind: "change_group_data_scopes"` (một sự kiện mỗi đối tượng, nhãn dựng từ mã); `last_changed_at/by` tính cả AuditLog phạm vi; dòng `customers` có `note: "Bật Xem khách hàng để thấy tất cả khách"` khi lưu `all` mà nhóm thiếu `view_customer_list` (L4).
- `GET /api/auth/me/`: thêm `is_superuser` (bool).

### Rule BR đã cài
BR-PQ-36 (hiệu lực ở request kế, PV-08-AC10; cả yêu cầu hợp lệ hoặc không đổi gì, PV-08-AC6 AuditLog lỗi thì rollback), R1 (BE chặn thiếu xác nhận), R6 (chỉ Chủ ghi và xem trước), Q-8 (CAS), Q-9 (thu hẹp không cần xác nhận, có số dòng), S-8, bất biến 9 (AuditLog và xem trước chỉ có mã, tên nhân viên; test không chuỗi giả của khách).

### Mock F1: 4 ca đối chiếu (`MockParityTests`)
(1) NV giao đổi D7 `assigned_deliveries` → `all` khi việc tắt: không mở rộng, không thu hẹp. (2) NV giao lưu `all` rồi bật việc: mở rộng, `widened` `{"customers","all","all"}`. (3) Quản lý tắt rồi bật lại khi D7 = `all`: mở rộng. (4) NV kho bật việc kèm `scopes.customers = "all"`: mở rộng `{"none","all"}`; không kèm D7 thì 400 `SCOPE_VALUE_INVALID` (PO-Q1).
Rank hiệu lực D7 bị chặn trần `assigned_deliveries` khi nhóm thiếu `view_customer_list` (cùng luật H1 của resolver).

### Lệch so với 02b / yêu cầu (cần techlead biết)
1. **PUT nhận `scopes`, không phải `data_scope_values`.** Yêu cầu giao việc ghi "PUT nhận … `data_scope_values`"; 02b §2.3 và mock F1 gửi `scopes`, còn `data_scope_values` là khoá của GET. Tôi theo 02b.
2. **PO-Q1 (bước 10) chỉ kiểm khi yêu cầu có đụng `view_customers` hoặc `scopes.customers`.** Mock kiểm mọi lần lưu; làm vậy sẽ chặn nhầm một lần lưu không liên quan khi nhóm có sẵn trạng thái lệch (Xem khách hàng bật, D7 = none, dữ liệu cũ). Hai bên khác nhau chỉ ở ca dữ liệu lệch sẵn.
3. **Mở rộng tính cả D2 (hoá đơn) và V2** theo 02b §2.5, mock F1 chưa có. `widened[]` có thể chứa `{"key": "invoices", ...}` (from/to = giá trị D1) và `{"key": "view_order_customer_info", "from": "off", "to": "on"}`; FE tra nhãn đối tượng theo `key` nên cần chịu khoá không có trong `SCOPE_BY_KEY` (V2) khi Lô 6 nối BE thật.
4. **C1: người không nhóm (`direct_permissions`) co lại ở `refunds.*` và `dashboard.summary`** (D1 = hẹp nhất): 15 → 1 đơn chờ, doanh thu 200000 → 0, mất 10 dòng ở dashboard, phiếu hoàn 200 → 404. Đưa vào `PENDING_DUY_DIFFS`; hai mục `+` ở dashboard (`extra:kpis.*`, `visible:order_assigned_direct`) là con số mới nhỏ hơn và đơn của chính họ lọt vào cửa sổ 8 đơn gần nhất, không ai thấy thêm đơn. Test M1 cho phép đúng hai mục đó và chỉ ở `dashboard.summary`.
5. Phiếu hoàn không gắn đơn nào (giao dịch lệch chưa khớp đơn) bị ẩn khi D1 khác `all`; với `all` thấy như hôm nay.
6. `legacy_scopes` (chuỗi `scopes` cũ) không đổi; hai test cũ phải gửi kèm `scopes.customers` cho khớp PO-Q1.

### Kiểm chứng (chạy trong lượt làm)
Kết quả cuối ghi trong báo cáo bàn giao (số test toàn bộ, `makemigrations --check`, `check_naming.py`).

### Việc còn nợ / chuyển lô
- Superuser không nhóm về `dashboard` (`home_for`): KHÔNG làm, vẫn chờ Duy.
- Lô 6: bỏ khoá `scopes` cũ; FE nối BE thật cần chịu `widened[].key` ngoài `SCOPE_BY_KEY`; nhãn V2 chờ Duy chốt chữ.
- Người phạm vi hẹp vẫn `PATCH` được `note`/`default_address` của khách ngoài tầm đọc (ghi chú techlead Lô 4 điểm 4): cần cả `view_customer_list` lẫn `change_customer`; chưa chặn.
- Đua thật PV-10-AC5 chỉ chạy trên Postgres (bỏ qua trên SQLite); cần chạy ở CI hoặc staging.

## Lô F1 FE (PV-11, PV-09 phần FE, PV-10 phần FE) — fe-dev, nhánh `feat/pham-vi-fe` (tách từ main `9509453`)

Chưa push, chưa merge. Chỉ sửa `erp-console/features/permissions/**` và `erp-console/e2e/ed_batch14_permissions.py` (+ mục này).

### Làm gì
| Việc | Chỗ |
|---|---|
| Khối "Phạm vi dữ liệu" 8 dòng (D1..D8) ở W3i: ô chọn đúng `options`, D2 "Theo Đơn hàng", D8 chỉ đọc; nhóm Chủ khoá + "Chủ luôn thấy tất cả"; nhãn CSKH đã đúng (hết chữ "Trong phạm vi gọi", L3) | `components/GroupDetailScreen.tsx` (`ScopeRowEditor`), `mockScopes.ts` |
| Ô mờ khi có `inactive_reason`, giá trị cũ vẫn hiện; bật việc gốc trong bản nháp thì hết mờ; `gate_capability: null` chỉ dựa vào `inactive_reason` | `permissionsModel.ts::isScopeInactive` |
| W3i thành **bản nháp** + thanh "Lưu thay đổi / Huỷ thay đổi" (một PUT, chỉ khoá đã đổi, kèm `version`); `beforeunload` khi còn nháp. W3h giữ bật/tắt ngay (D-4) | `useGroupDraft.ts`, `permissionsModel.ts` (`Draft`, `toggleInDraft`, `setScopeInDraft`, `cleanDraft`, `saveBodyOf`) |
| PV-09: lưu → POST xem trước → hộp "Cho thêm người xem dữ liệu khách?" (câu `message`, tên nhân viên, "Người đã nghỉ thì khoá tài khoản", dòng kiêm nhiệm, "Huỷ" / "Tôi hiểu, lưu"); thu hẹp có `rows_losing_access` thì ghi chú, không chữ cảnh báo khách; 400 `CUSTOMER_DATA_WIDENING_UNCONFIRMED` mở hộp bằng `impact`, giữ lựa chọn | `components/ConfirmSaveModal.tsx`, `saveErrors.ts` |
| PV-10: mọi PUT gửi `version`; 409 → "Nhóm này vừa được người khác đổi. Tải lại để xem bản mới." + nút "Tải lại" (xoá nháp, lấy bản server), không tự gửi lại; W3h: 409 → báo + tải lại danh sách; "Hoàn tác" dùng `version` mới | `useGroupDraft.ts`, `useCapabilityToggle.ts` |
| PO-Q1: bật "Xem khách hàng" khi Khách hàng = Không xem → nháp (và W3h) tự đặt Khách hàng = Tất cả; chọn Không xem khi việc đang bật thì khoá nút Lưu + báo cạnh nút | `toggleInDraft`, `draftProblem`, `useCapabilityToggle.bodyOf` |
| **Superuser ngoài nhóm Chủ được ghi** (Duy chốt 06/10): hết chặn ở W3h, W3i, thêm/bỏ thành viên nhóm Chủ | `permissionsModel.ts::isGroupWriter` |
| Bỏ chip "Được gán" hằng số (`ASSIGNED_ONLY`); chip và chip "Tất cả khách" lấy từ `data_scope_values` BE | `isAssignedOnly`, `showsAllCustomers` |

Hàm API mới (`api.ts`): `saveGroupChanges(code, {version, capabilities?, scopes?, confirm_customer_data_widening?})` (thay `setGroupCapabilities`), `previewGroupChanges(code, {capabilities?, scopes?})`. Kiểu mới ở `types.ts`: `DataScopeRow`, `ScopeOption`, `GroupSaveBody`, `GroupPreviewBody`, `ScopePreview`; `GroupSummary`/`GroupDetail` thêm `version`, `data_scope_values`, `data_scopes`; `scopes` cũ để tuỳ chọn và FE không dùng.

GET dùng đúng contract thật của Lô 2 (`version`, `data_scope_values`, `data_scopes`). PUT mới và preview chạy ở bản mock cho tới Lô 5.

### Mock giữ luật BE (`mock.ts` + phần thuần `mockScopes.ts`)
Thứ tự kiểm 02b §2.3 (403 → 404 → GROUP_LOCKED → INPUT_NOT_ALLOWED → INVALID_INPUT → SCOPE_* → BR-PQ-32 → **409 CAS `version`** → CAPABILITY_REQUIRES → **PO-Q1** → **400 CUSTOMER_DATA_WIDENING_UNCONFIRMED kèm `impact`**). Không đổi gì thì 200 và không tăng `version`. Kho tạm `sessionStorage` (khoá việc, mã đối tượng, mã giá trị, số phiên bản, tên đăng nhập người sửa; không dữ liệu khách). Công cụ thử: `window.__caveMock.bumpGroupVersion("manager")` giả lập người khác vừa lưu. Danh mục D1..D8 và mặc định theo nhóm chép từ `catalog.py` và migration `0015`. Số "dòng mất quyền xem" của xem trước là số GIẢ cố định (3 phiếu nhập, 2 loại khác).

### Chỗ lệch contract / cần techlead và điều phối viên biết
1. **`/api/auth/me/` không trả `is_superuser`** (Me ở `features/auth` ngoài danh sách được sửa). `isGroupWriter` dùng `me.is_superuser === true` nếu có, không thì suy ra từ việc có đủ 5 quyền chỉ-Chủ (`confirm_payment_manual`, `confirm_refund`, `manage_staff`, `manage_ai_policy`, `close_batch`), vì superuser có mọi permission. Sai thì BE vẫn 403 và UI hiện nguyên văn. Đề nghị Lô 7 (PV-14, `accounts/auth/services.py`) thêm `is_superuser` vào `/me/`.
2. **Superuser KHÔNG thuộc nhóm nào** bị `AuthGate` đưa về `/no-role/` (mock `admin`), nên không vào được `/permissions/`. Thuộc `features/auth`, ngoài phạm vi. Superuser kèm nhóm (mock `sa1` = Quản lý + superuser) thì vào và ghi được; e2e kiểm bằng `sa1`.
3. **Mock cũ sai một chỗ**: `view_customers` mặc định tắt ở Quản lý, trong khi migration `sales/0013` cấp `view_customer_list` cho `manager` (D7 seed = `all`). Đã sửa mock cho Quản lý bật.
4. **Hành vi theo 02b §2.5, có thể làm Duy bất ngờ**: bật lại một việc cổng (Xem đơn, Gọi xác nhận, Xem khách hàng) trên nhóm đang lưu phạm vi rộng (Q-7 giữ giá trị khi tắt) là MỞ RỘNG dữ liệu khách, nên cả ở W3h cũng hiện hộp "Tôi hiểu, lưu". Mock làm đúng như vậy; BE Lô 5 phải trả đúng cùng quy tắc.
5. `data_scopes[].options` của nhóm Chủ vẫn có (BE `_options`) dù `editable: false`; FE chỉ đọc nhãn.
6. Khi bật "Xem khách hàng" ở W3h với D7 = `none`, FE gửi `scopes.customers = "all"`; BE Lô 5 phải chấp nhận khoá này cùng yêu cầu việc (đúng 02b §2.3 bước 10).
7. `ConfirmOffModal` (hỏi khi tắt việc phá luồng) chỉ còn dùng ở W3h; ở W3i câu hậu quả nằm trong hộp xác nhận lúc Lưu.

### Việc còn nợ
- Nối BE thật cho PUT/preview ở Lô 5 (không deploy FE này trước Lô 5; M2: Lô 4 và 5 lên cùng lượt).
- `scopes` cũ và kiểu `GroupScopes` bỏ hẳn ở Lô 6.
- PV-13, PV-14 FE (Lô 7) chưa làm. Chuyển trang trong app khi còn nháp chưa bị chặn (chỉ `beforeunload` khi đóng tab/tải lại); chấp nhận được, ghi để QA cân nhắc.

### Kiểm chứng (chạy trong lượt làm, trong worktree; `node_modules` là symlink, đã gỡ trước khi commit)
- `./node_modules/.bin/tsc --noEmit`: sạch.
- `vitest run`: **86 file, 1021 test PASS** (thêm test model/bản nháp trong `permissionsModel.test.ts` và test luật mock trong `mock.test.ts`).
- `NEXT_PUBLIC_USE_MOCK=0 npm run build` + `check-no-mock.mjs` (XANH, 28 file mock, 43 chuỗi) + `check-ai-chunks.mjs` (XANH, 48 màn + 2 layout).
- `NEXT_PUBLIC_USE_MOCK=1 npm run build` + `e2e/ed_batch14_permissions.py`: **154/154 PASS** (gồm: superuser sửa được; Quản lý `ql9`, `ql1`, `kho1`, `giao1`, `cs2` không sửa/không vào; 409 ở W3i và W3h; bản nháp không gọi API cho tới Lưu; Esc/Huỷ không PUT; PO-Q1; ô mờ; 360px không cuộn ngang, vùng bấm ≥ 44px; không dữ liệu cá nhân ở storage/URL; không lỗi console).
- `python3 scripts/check_naming.py`: OK, không phát sinh mới.
- Ảnh (thư mục `shots/` bị `.gitignore`, không commit): `shots/f1-desktop-1280-{w3i-scopes,w3i-draft,widen-dialog,conflict,superuser}.png`, `shots/f1-mobile-360-{w3i-draft,w3i-full,widen-dialog}.png`.
- Dọn: đã xoá `out/` và `.next/`, tắt server 3101.

### Vòng sửa theo review techlead F1 (07/10)
- **M1:** mock D7 theo rank hiệu lực (`effectiveRank`, trần `assigned_deliveries` khi "Xem khách hàng" tắt); Quản lý và NV giao luôn đủ điều kiện D7 (không mờ). Test: NV giao đổi D7 sang `all` khi việc tắt không đòi xác nhận; NV giao lưu `all` rồi bật việc đòi xác nhận; Quản lý tắt rồi bật lại đòi xác nhận.
- **M2:** "Hoàn tác" ở W3h đi cùng đường `send` (mở rộng thì mở hộp cảnh báo); ca PO-Q1 hoàn tác kèm `scopes.customers = "none"`. e2e: tắt Xem đơn của Quản lý, Hoàn tác, hộp cảnh báo, "Tôi hiểu, lưu".
- **M3:** link nội bộ khi còn nháp: bắt click pha capture, `confirm(M.draftLeave)`, rồi `router.push`. Nút Back của trình duyệt (`popstate`) CHƯA chặn (QA biết). e2e có ca huỷ ở lại và đồng ý sang trang.
- **L1, L2:** mock preview nhận `version`/`confirm` (bỏ qua); người không phải Chủ gọi PUT/POST nhóm lạ nhận 403 trước 404. **L3:** `version` đổi khi đang có nháp (sau thêm/bỏ thành viên) → báo xung đột "Tải lại". **L4:** chuỗi "Chưa lưu", "Một phần" vào `messages.ts`, bỏ `scopeReadOnlyHint`. **L5:** bỏ ca đếm khống. L6 để UI review; L7..L9 ghi cho Lô 3/5.
- Superuser không nhóm (`/no-role/`): không làm, chờ Duy.
- Kiểm: tsc sạch; vitest 86 file, 1026 test PASS; build mock=0 + check-no-mock + check-ai-chunks XANH; build mock=1 + `ed_batch14_permissions.py` 157/157 PASS. Đã xoá `out/`, gỡ symlink, tắt server.
## Lô QĐ-08/10 BE (be-dev, 08/10, nhánh `feat/qd-0810-be`)

Theo `02c-quyet-dinh-08-10.md` mục A, B, C.4, E, F. Quy tắc: BR-PQ-19/38, D-3 (Duy 08/10).

### File đã sửa (đều trong `backend/`)
- Cổng D-3: `apps/accounts/auth/authentication.py` (mixin đổi tên `_EnforceAccessMixin`; thêm `NoRole`, `has_erp_access`), `apps/accounts/auth/api.py` (4 view thêm `allow_without_group = True`).
- `me`/home: `apps/accounts/auth/services.py` (`home_for(user, groups)` (sau sửa L1), khoá `is_superuser`, `GROUP_LABELS`, nhãn V2).
- Nhãn V2 "Xem thông tin khách trên đơn, hoá đơn, phiếu hoàn tiền": `capabilities/registry.py`, `sales/models/orders.py`, `sales/customers/permissions.py` (comment), migration `sales/migrations/0019_alter_salesorder_view_order_customer_info_label.py` (chỉ `AlterModelOptions`).
- Câu 2: `apps/common/ai_visibility.py` (`AI_ADMIN_ACTION_PREFIXES`).
- Câu 13: nhãn vai "Nhân viên gọi xác nhận" (`GROUP_LABELS`), nhóm lệnh AI "Chăm sóc khách hàng" (`ai/settings/services.py`).
- Seed: `accounts/qa_fixture/build.py` (`qa_nogroup` có quyền trực tiếp `sales.view_salesorder`, `sales.view_refund`, idempotent).

### Contract cho FE
`GET /api/auth/me/` thêm `"is_superuser": bool`. Superuser (kể cả không nhóm, hoặc chỉ `delivery_staff`) có `home: "dashboard"`; `groups`, `group_labels` vẫn là nhóm thật (có thể `[]`). Người không nhóm, không superuser: `home: "no-role"`, `me` vẫn 200.

Cổng D-3: người không nhóm và không superuser gọi bất kỳ API ERP nào (trừ `/api/auth/token/`, `me`, `logout`, `change-password` và view `AllowAny`) nhận:
```json
HTTP 403 {"detail": "Tài khoản của bạn chưa thuộc nhóm nào nên không có quyền vào hệ thống vận hành. Nhờ Chủ vựa xếp nhóm.", "code": "AUTH_NO_ROLE"}
```
Quyền gán trực tiếp không tính. Kiểm theo DB mỗi request nên gỡ nhóm có hiệu lực ngay (không cache, khác 02c "cache trên user", vì token client dùng lại đối tượng user khác nhau mỗi request nên cache vô ích). Thứ tự: `AUTH_MUST_CHANGE_PASSWORD` kiểm trước, rồi `AUTH_NO_ROLE`.

### Test lật / đổi
- `test_s6_me.py`: `test_s6_ac4_superuser_without_group_goes_to_dashboard` (lật S6-AC4), thêm ca superuser chỉ `delivery_staff`, ca `is_superuser False`; tập khoá thêm `is_superuser`.
- `test_s47_me_labels.py`: `test_s47_ac5_superuser_without_group_has_dashboard_and_all_capabilities` (lật S47-AC5); nhãn V2; tập khoá.
- Mới `auth/tests/test_no_role_gate.py` (9 test): token thật quét mọi route DRF dưới `/api/` (view không miễn đều 403 `AUTH_NO_ROLE` dù có quyền trực tiếp), thân 403 chỉ `{detail, code}` không có SĐT giả, được chừa login/me/logout/đổi mật khẩu, view AllowAny không bị cổng, mọi nhóm qua cổng, superuser qua, gỡ nhóm có hiệu lực ngay, 401 khi chưa đăng nhập.
- `test_note_redaction_and_ai_hide.py`, `common/tests/test_ai_visibility.py`: ẩn `ai_config_*`, `ai_policy_*`, `downgrade_*` khi tắt AI, hiện lại khi bật, lọc `?action=ai_config_update` trả 0, giữ dòng nghiệp vụ có `proposal_ref` do người duyệt.
- `test_standard_names.py` (nhãn vai không còn viết tắt cũ), `capabilities/tests/test_api_read.py`, `delivery/tests/test_confirmation_role_scope.py`, `data_scopes/tests/test_orders_invoices_scope.py` (nhãn), `qa_fixture/tests/test_seed_qa.py` (quyền trực tiếp qa_nogroup).
- Không test cũ nào dùng token thật với user không nhóm bị vỡ.

### Ghi chú
- `seed_qa` guard từ chối DB không phải SQLite nên 21 test `qa_fixture` không chạy được trên PostgreSQL cục bộ (có từ trước, không do lô này); chúng xanh trên SQLite.
- Sinh migration `sales/0019` đúng số kế tiếp trên main (0018 là cuối).
- Không đụng `delivery/serializers.py`, `features/permissions/**`, ngoài `backend/`.

### Sửa theo review (L1–L4)
- L1: `home_for(user, groups)` dùng `has_erp_access` (cùng luật với cổng D-3); kết quả `home` không đổi.
- L2: `test_no_role_gate.py` thêm 3 ca: phiên (Session) bị 403 `AUTH_NO_ROLE`; người không nhóm có mật khẩu tạm nhận `AUTH_MUST_CHANGE_PASSWORD` trước; POST huỷ đơn bị 403 và đơn giữ trạng thái `PROCESSING`.
- L3: test `test_no_api_view_overrides_get_permissions` khẳng định không view nào dưới `/api/` override `get_permissions` (vì `_is_public_view` chỉ đọc `permission_classes` cấp class).
- L4: `qa_fixture/build.py` dùng `Permission.objects.get(...)`, thiếu quyền thì lỗi to thay vì bỏ qua im lặng.
## Lô QĐ-08/10 FE (erp-console, Duy duyệt 08/10: câu 1, D-3, câu 13)

- Superuser không nhóm vào ERP như Chủ: `Me.is_superuser`, `Viewer.is_superuser` (nav.ts, logic menu không đổi), `SUPERUSER_LABEL = "Quản trị hệ thống"` ở `shared/lib/groups.ts`; `roleText` (ConsoleGate) và AccountScreen ("Quản trị hệ thống (toàn quyền)") hiện nhãn này khi không có nhóm mà là superuser.
- D-3: `NO_ROLE_CODE = "AUTH_NO_ROLE"` (`features/auth/types.ts`). AuthProvider: 403 mã này đặt `me.home = "no-role"` rồi tải lại `me`, ConsoleGate đưa về `/no-role/` (không đi nhánh 403 chung vì nhánh đó chỉ tải lại `me` và có thể không chuyển trang). `/no-role/` đổi chữ thành "Bạn không có quyền vào hệ thống vận hành".
- Mock: `admin` thành `home: "dashboard"` + `is_superuser`; thêm `nogroup1` (id 13, không nhóm, có quyền gán lẻ) và cổng mock trả 403 `AUTH_NO_ROLE` (thêm vào `beErrors.mock.ts`) cho mọi API trừ me/logout/change-password/token, đứng sau kiểm mật khẩu tạm. LoginScreen gợi ý tài khoản mock đổi theo.
- Nhãn `customer_service` thành "Nhân viên gọi xác nhận" (`GROUP_LABEL`, nhãn nhóm lệnh AI ở `ai/settings/mock.ts`, một câu 404 mock). Mã nhóm giữ. Nhãn V2 mới do BE trả, FE không chép.
- e2e đổi `admin` thành `nogroup1` cho ca không nhóm: s7_shell (thêm ca admin vào /overview/, menu có Phân quyền, không có Việc giao của tôi), qa_ed_batch1_roles, ed_batch15_overview_ai_account, s48_password (đích chờ của admin là /overview/). Vitest: `englishNames.test.ts` đổi nhãn; mới `features/auth/superuser.test.ts`.
- Không đụng `features/permissions/**`, backend/, frontend/.
- Nợ/ghi chú: ed_batch15_overview_ai_account cần build bật AI (chờ `[data-attention=ai_proposals]`); ở build tắt AI nó dừng ở ca này, không liên quan lô. Tên hiển thị người mock "CSKH Thử"/"CSKH Khác" và từ khoá tìm AI "cskh" giữ nguyên (không phải nhãn vai).
- Sửa theo review (R1–R3, N1): R1 thêm `ai_config_kill` vào `AI_ONLY_ACTIONS` (auditModel.ts) + vitest; R2 nhãn nhóm lệnh AI mock = "Chăm sóc khách hàng"; R3 câu 404 mock gọi xác nhận = nguyên văn BE "Không tìm thấy mục chờ gọi trong phạm vi của bạn."; N1 `onlyDelivery` thêm `!me.is_superuser &&` + 1 ca vitest (nav.test.ts). Kiểm: tsc sạch, vitest 1235/1235, build MOCK=0 + check-no-mock + check-ai-chunks XANH.

## Lô PV-QĐ (08/10) — be-dev, nhánh `feat/pham-vi-du-lieu`

Theo `02c-quyet-dinh-08-10.md` mục G.2 (B.4, C.1–C.2, D, C1). Không đụng `erp-console/`, `accounts/auth/authentication.py`, migration.

**1. Gộp main (commit `4ef5aa8`, main `f3a543f`).** Giải xung đột:
- `auth/services.py`, `auth/tests/test_s6_me.py`, `test_s47_me_labels.py`: lấy phía main (tập khoá `ai_features_enabled` + `is_superuser`).
- `capabilities/services.py`: giữ CAS/`version`, `_parse_body`, `_scope_events`, `scope_change_label` của nhánh; thêm `registry.visible_keys` / `visible_capabilities`
  của main (bỏ cờ `customer_data_widening_confirmed` rồi mới lọc việc AI; PUT việc AI khi AI tắt vẫn 400 `INPUT_NOT_ALLOWED`).
- `capabilities/next_steps.py`: nhãn `scope_change_label` của nhánh + `row_filter=has_visible_capability_change` của main.
- `capabilities/tests/test_ai_hidden.py` (không xung đột nhưng hỏng sau gộp): PUT thiếu `version` nên 400; đổi sang `put_caps` (tự lấy version).
- `reports/dashboard_api.py`: giữ D1 (`orders_in_scope`), "Đơn gần đây" lấy từ `orders_in_scope` kèm `select_related/prefetch_related` của 17a.
- `sales/orders/api.py`: giữ lọc `?customer=` theo D7 và `POST search/` (17b) của main. Mở rộng nhỏ: `search/` cũng áp D7 cho `customer` trong body
  (`_customer_filter_outside_scope(request, params)`), để `?customer=` và body cùng một luật (PV-05-AC6).
- 3 file doc hồ sơ: giữ cả hai phía.
- Migration: nhánh không có migration nào so với main; `sales/0019` (main) giữ nguyên số; `makemigrations --check` sạch.

**2. Mốc PV-01 (D-3, câu 9).** `snapshot.py`: `PENDING_DUY_DIFFS = ()`; mục `direct_permissions` (D6, D7, `refunds.*`, `dashboard.summary` kèm hai mục `+`)
chuyển sang `APPROVED_DIFFS` ghi "Duy duyệt 08/10 D-3"; mục `warehouse_service` (8 cặp `confirmation.*`, `actions.confirmation_*`) ghi
"Duy duyệt 08/10 D-3 (câu 9)". `PENDING_DUY_USERS` đổi tên `D3_USERS`. Không sinh lại `scope_snapshot_baseline.json`: bộ thu dùng `force_authenticate`
nên bỏ qua cổng `AUTH_NO_ROLE` (người không nhóm bị 403 toàn bộ ở thực tế), mốc vẫn ghi hành vi lớp phạm vi và các lệch nằm ở danh sách được duyệt;
đây là lớp phòng thủ thứ hai phía sau cổng. `test_scope_snapshot.py`: sửa docstring, `test_pv01_ac3_only_one_approved_exception` (hai mục đầu = Q-4, phần còn lại
chỉ của hai tài khoản D-3, có "Duy duyệt 08/10 D-3" trong nguồn), `test_pv01_pending_duy_diffs_...` thành `test_pv01_d3_approved_diffs_are_narrowing_only` (kèm `PENDING_DUY_DIFFS == ()`).
Các khẳng định "một dòng `+` lạ của direct_permissions không được miễn" giữ nguyên.

**3. Câu 7 (V2 không áp cho phiếu giao).** `delivery/serializers.py`: xoá luật "không có V2 thì ẩn" và import `can_view_order_customer_info`;
`_customer_data_hidden` còn một luật (`pii_restricted` và phiếu quá cửa sổ SR-PII-02). Test (TDD, đỏ rồi xanh):
`test_w37_n2_status_response_keeps_customer_data_when_v2_is_off` (lật), `test_w37_n2_courier_list_keeps_customer_data_without_v2` (lật),
mới `test_w37_n2_status_response_hides_customer_data_when_note_is_past_pii_window` (cửa sổ, giả lập `is_note_pii_expired` ở serializer vì phiếu quá cửa sổ thì NV giao
không mở được theo D3). Tem `/label/` giữ nguyên (che SĐT, chờ Duy Q1). PV-01 xanh, không lệch `deliveries.*`.

**4. C1.** Đã code ở `5fd4032` (có trong HEAD): `refunds/api.py` đi qua `scope_refunds_for`, `dashboard_api.py` qua `scope_orders_for` (D1). Sau gộp vẫn giữ cả hai lời gọi,
test PV-05/dashboard xanh. Trạng thái chờ đã gỡ (`PENDING_DUY_DIFFS` rỗng); `02b` R9 và D-3 ghi "Duy chốt 08/10".

**Nợ / ghi chú.** (a) Việc vận hành trước deploy production: đếm tài khoản `is_active`, không superuser, không nhóm (chỉ in username), báo Duy xếp nhóm trước khi deploy.
(b) Test cổng thật `test_no_role_gate.py` đã có từ main; PV-12 (Lô 6) nên quét bằng token thật.

**Kiểm chứng PV-QĐ (08/10, chạy tuần tự `--parallel 1`).**
- SQLite: `Ran 3526 tests in 289s — OK (skipped=3)`.
- PostgreSQL 16 (DB `cangca_pvqd`, main chưa có sửa Postgres): `Ran 3523 — FAILED (failures=13, errors=55)`. Toàn bộ nằm trong nhóm lỗi đã biết của nhánh `fix/postgres-compat`:
  28 `FOR UPDATE cannot be applied to the nullable side of an outer join` (huỷ phiếu nhập, publish lô, claim xác nhận, hoàn tác AI trả 502 vì dispatch bắt lỗi này, và mốc PV-01 lệch `actions.confirmation_claim=EXC:NotSupportedError`),
  23 `seed_qa` guard (22 lỗi + `test_password_env_is_required`), 1 race `django_content_type` unique (`test_pv10_ac5`, sửa khi gộp `fix/postgres-compat`, M1), `test_qa_lo4_tien` (2), `supplier_crud` (1 sắp xếp), `shop_labels` (varchar 12), cost overflow (1), `completion_race` admin.logentry (2, đã sửa ở `fix/postgres-compat`). Không có ca đỏ ngoài danh sách.
- `makemigrations --check --dry-run`: No changes detected. `python3 scripts/check_naming.py`: OK, không phát sinh mới.

## Gộp main sau sửa Postgres + M1 (08/10)

- `git merge main` (cfc039b) vào nhánh `feat/pham-vi-du-lieu`: không xung đột. Git tự gộp `purchasing/receipts/services.py`;
  `delivery/confirmation/services.py` và `purchasing/costs/services.py` nhánh này không đụng nên giữ bản của main.
- Rà `select_for_update` kèm `select_related` trong code không phải test: không còn câu nào (chỉ còn một comment giải thích
  quy tắc ở `delivery/confirmation/services.py`). Code phạm vi dữ liệu của nhánh không có câu vi phạm quy tắc.
- M1 (review techlead Lô PV-QĐ): thêm `apps/common/tests/postgres_race.py` với `PostgresRaceFixtureMixin` (xoá ContentType
  trước `super()._fixture_setup()`, rồi `ContentType.objects.clear_cache()`, kèm `serialized_rollback = True`). Áp cho
  `CancelVersusCompleteRaceTests`, `ClaimRaceTests`, `CostVersusCancelReceiptRaceTests`, `ConcurrentSaveRaceTests`
  (test_pv10_ac5). Xoá bản `_fixture_setup` chép tay ở ba file.
- Kiểm chứng: PostgreSQL 16 (DB riêng) `Ran 3532 tests ... OK`, không ca đỏ, không skip; SQLite tuần tự
  `Ran 3532 tests ... OK (skipped=7)`; `makemigrations --check --dry-run` No changes detected; `check_naming.py` OK.
## F1 gộp main (08/10) — fe-dev, nhánh `feat/pham-vi-fe`

Theo `02c-quyet-dinh-08-10.md` mục G.2 (F1 FE). Merge commit `4bb92ec`, commit sửa ngay sau. Chỉ sửa `erp-console/features/permissions/**`, một e2e, và hồ sơ này. Không đụng `backend/`, `frontend/`.

**Xung đột đã giải (5):**
- `GroupDetailScreen.tsx`: giữ `useGroupDraft` (bản nháp, một PUT có `version`) của F1, thêm `aiVisible` + `visibleRegistry` của main (mục lệnh AI ẩn khi tắt AI; `sections` lấy từ registry đã lọc). Bỏ `useCapabilityToggle` ở màn này vì F1 đã thay bằng bản nháp.
- `PermissionMatrixScreen.tsx`: giữ `onConflict` (409 `GROUP_CHANGED` → tải lại danh sách + registry) và `objectLabel` của F1, registry qua `visibleRegistry(…, aiVisible(me))` của main.
- `02b-tech-design.md`, `03-dev-notes.md`, `03b-review-techlead.md`: giữ cả hai phía (chỉ bỏ dấu xung đột).
- `isGroupWriter` giữ nguyên ý (Chủ HOẶC superuser ghi được, quyết định 06/10 + câu 1 ngày 08/10).

**Sửa ngoài giải xung đột (tối thiểu):**
1. `permissionsModel.ts`: bỏ nhánh đoán `OWNER_ONLY_PERMS`; `isGroupWriter` chỉ đọc nhóm Chủ hoặc cờ `is_superuser` (BE đã trả ở `/api/auth/me/`). Test vitest đổi: ca "đoán qua đủ quyền chỉ-Chủ" thành "không đoán, thiếu cờ thì chỉ nhóm Chủ ghi được". README `features/permissions` sửa theo.
2. Nhãn mock cho khớp BE (`standard_names`): `create_refund` "Lập phiếu hoàn tiền", `assign_delivery` "Chọn người giao", `create_return` "Ghi hàng hoàn", `approve_return` "Duyệt hàng hoàn", phạm vi `returns` "Hàng hoàn" (`mock.ts`, `mockScopes.ts`). Nhờ đó chữ cũ ở /permissions/ hết, nên bỏ TODO F1 và `PENDING_ROUTES` trong `e2e/standard_names_all_routes.py` (còn tập rỗng). `ed_batch14_permissions.py` đổi "Ghi hàng hoàn về kho" thành "Ghi hàng hoàn".

**Không làm / nợ cho Lô 6 (nối BE thật):**
- Câu 7 (phiếu giao không còn theo V2): màn Phân quyền không có chữ nào nói phiếu giao đi theo V2 (`grep V2` rỗng); khối phạm vi "Phiếu giao" là phạm vi D riêng, giữ nguyên.
- Mock registry (`permissions/mock.ts`) vẫn chưa có hai việc `view_sales_invoices` và `view_order_customer_info` (nhãn mới "Xem thông tin khách trên đơn, hoá đơn, phiếu hoàn tiền") mà BE đã trả. Thêm vào mock kéo theo đổi số việc, luật H1 và nhiều test, nên để Lô 6 bỏ mock/nối BE thật. Khi nối, nhãn lấy từ BE, FE không chép.
- `useGroupDraft` vẫn nhận `group.registry` gốc (kể cả mục AI khi tắt AI) để tính cảnh báo phá luồng; không ảnh hưởng hiển thị.

**Kiểm chứng:** xem số ở báo cáo cuối lượt (tsc, vitest, build thật, check-no-mock, check-ai-chunks, e2e mock AI tắt và bật).

## Lô 6 BE (PV-12) — be-dev, nhánh `feat/pv6-be` (từ main `db13e13`)

**File sửa:** `backend/apps/accounts/data_scopes/services.py` (bỏ `legacy_scopes`, `LEGACY_*`, hằng quyền chỉ dùng cho nó),
`backend/apps/accounts/capabilities/services.py` (`describe_group` không trả `scopes`), `backend/apps/common/api.py` (bỏ `import roles` mồ côi;
các hàm `FULL_SCOPE_GROUPS`, `has_full_delivery_scope`, `CUSTOMER_DIRECTORY_GROUPS`, `sees_customer_directory` đã gỡ từ Lô 4, grep sạch),
README `data_scopes`, test cũ `capabilities/tests/test_api_read.py` và `data_scopes/tests/test_api_describe.py` đổi sang `data_scope_values`.
**File thêm:** `backend/apps/accounts/data_scopes/tests/test_release_gate.py`. Không có migration, không đổi model.

**Contract đổi cho FE (đúng 02b §2.2 "bỏ ở Lô 6"):** `GET /api/staff/groups/<code>/` **không còn khoá `scopes`** (chuỗi nhãn cũ
`{orders, deliveries, customers}`). FE đọc `data_scopes` (8 dòng) và `data_scope_values`. Thân `PUT …/capabilities/` và
`POST …/permissions-preview/` **vẫn nhận** khoá `scopes` = `{mã đối tượng: mã giá trị}` (đó là đầu vào mới của Lô 5, không phải `scopes` cũ); phản hồi PUT như GET (không có `scopes`).
Nơi FE từng dựa vào "customers = Tất cả khách" theo quyền thực: nay dùng dòng `data_scopes[key=customers]` (`value`, `inactive_reason`, `note`; `note` = "Bật Xem khách hàng để thấy tất cả khách" khi bị chặn trần).

**PV-12 (test_release_gate.py, token thật như `test_no_role_gate.py`, nên quét luôn cổng D-3):**
- AC1: `test_scope_snapshot` giữ nguyên xanh (không sinh lại mốc); thêm test chốt `PENDING_DUY_DIFFS == ()`.
- AC2: nhóm thăm dò `pv12_probe` có đủ quyền cổng; với D1, D3, D5, D6, D7 và MỌI giá trị, 3–6 endpoint mỗi đối tượng (danh sách, tìm theo mã, chi tiết, "Tiếp theo" qua guidance, AI chi tiết) cho tập dòng bằng nhau và bằng hàm phạm vi (`scope_*_for`). D4: chi tiết bằng `note_in_confirmation_scope`; hàng chờ liệt kê mọi mục theo trạng thái nhưng chỉ mục trong phạm vi mang dữ liệu khách (hiện trạng PV-01, khoá bởi mốc). Danh sách AI có giới hạn dòng nên chỉ kiểm không vượt phạm vi và không rỗng; bảng điều hành kiểm tương tự. Có test chống quét rỗng (rộng nhất thấy nhiều dòng hơn hẹp nhất).
- AC3 (S-1) 4 nhóm khác Chủ ở phạm vi rộng nhất, không `view_costprice`/`view_profitreport`, hơn 100 lần gọi: không khoá giá vốn; đối chứng Chủ có thấy. AC4 (S-2) tra đơn công khai, catalog, site-info: không chuỗi giả nào của tên/SĐT/địa chỉ. AC5 (S-3) bắt log DEBUG + AuditLog quanh preview, PUT và quét: không chuỗi giả; ngữ cảnh AI không thêm dấu vết dữ liệu khách so với mốc. AC6 (S-4) phiếu/đơn kết thúc 8 ngày: dữ liệu khách rỗng; PUT với 6 tên khoá "số ngày" đều 400. AC7 (S-6) DELETE/PATCH/POST trên đơn, hoá đơn, phiếu nhập, nhật ký, bằng 4 nhóm + Chủ + superuser: 403/404/405, số dòng không đổi. AC8 grep: không còn `FULL_SCOPE_GROUPS`, `has_full_delivery_scope`, `CUSTOMER_DIRECTORY_GROUPS`, `sees_customer_directory`, `is_customer_service`, `GROUP_SCOPES`, `legacy_scopes` trong mã sản phẩm; các `scope.py`/`resolver.py`/`pii_scope.py`/`permissions.py` không so tên nhóm.
- Không phát hiện chỗ rò mới. Ghi nhận hiện trạng (không đổi, mốc PV-01 giữ): hàng chờ gọi xác nhận `?state=DONE` liệt kê cả mục ngoài phạm vi D4 nhưng không kèm dữ liệu khách của mục đó.

**Nợ / ghi chú:** `can_cancel_any_receipt` (`purchasing/receipts/services.py`) còn so nhóm `owner`/`manager` để quyết huỷ phiếu nhập của người khác. Đó là quyền hành động (không phải phạm vi đọc dòng, ngoài danh sách AC8); để techlead quyết có đưa vào cấu hình không. Tem `/label/` giữ che SĐT (Q1, mặc định), không đụng.

## Lô 6 FE (08/10) — fe-dev, nhánh `feat/pv6-fe` (từ main `db13e13`)

Theo `02c-quyet-dinh-08-10.md` §G.3 và điều kiện đóng F1 ở `03b-review-techlead.md` ("F1 gộp main"). Chỉ sửa `erp-console/features/permissions/**`, một e2e, và hồ sơ này. Không đụng `backend/`, `frontend/`.

**Đã làm:**
1. **Nối BE thật, bỏ kiểu cũ.** Xoá `GroupScopes` và field `scopes?` của `GroupDetail` (`types.ts`); không còn chỗ nào dùng. `api.ts` bỏ câu "BE chưa có endpoint, đừng deploy trước Lô 5" (BE đã có `PUT …/capabilities/` mới và `POST …/permissions-preview/` từ Lô 5). README module sửa theo. Màn chỉ đọc `registry`, `data_scopes`, `data_scope_values`, `version` do BE trả.
2. **Điều kiện đóng F1: mock có đủ 2 việc.** `mock.ts` thêm `view_sales_invoices` ("Xem hoá đơn bán", mặc định bật cho Quản lý, NV kho) và `view_order_customer_info` ("Xem thông tin khách trên đơn, hoá đơn, phiếu hoàn tiền", mặc định bật cho 4 nhóm, theo migration `sales/0016`). Đối chiếu tự động với `backend/apps/accounts/capabilities/registry.py`: 28 việc, thứ tự và nhãn trùng từng chữ.
3. **Luật H1 / mở rộng dữ liệu khách kéo theo (mock khớp `data_scopes/services.py::widened_objects`).** Dòng `invoices` có `gate_capability: "view_sales_invoices"` (bỏ danh sách cứng `HAS_INVOICE_VIEW`; `isEligible` tự đọc việc). `buildPreview` thêm hai ca: bật V1 cho nhóm chưa có → `widened` có `invoices` (rank theo D1); bật V2 → `widened` có `view_order_customer_info` (`from: "off", to: "on"`) với câu "… trên đơn, hoá đơn và phiếu giao". `GroupDetailScreen.objectLabel` tra thêm nhãn việc ở registry gốc để hộp xác nhận không hiện khoá thô `view_order_customer_info`.
4. **L1:** `e2e/ed_batch14_permissions.py` thêm `"hoàn về kho" not in rows_text.lower()` (bắt cả "Ghi hàng hoàn về kho") và một ca mới kiểm hai việc mới có trong ma trận.
5. **L2:** comment ở `GroupDetailScreen.labelOf` nói rõ cố ý đọc registry gốc, đừng "đồng bộ" thành bản đã lọc AI.
6. **L-A (QA: bảng Thành viên cắt cột "Thao tác" ở 1280px).** Tái hiện: khung bảng ở 1280px chỉ rộng 646px (nhánh hai cột), người thuộc 3 nhóm hoặc tên dài làm bảng rộng 781px, nút "Bỏ khỏi nhóm" nằm ngoài vùng cuộn (nút lệch phải 1030 so với mép thẻ 911). Với dữ liệu mẫu ngắn thì vừa khung nên chưa thấy. Sửa: bảng vẫn cuộn ngang trong khung riêng (không cuộn cả trang), riêng cột cuối được ghim bên phải (`.memberTable` trong `permissions.module.css`, chỉ khi `canManageMembers`), nên nút luôn thấy và bấm được ở 1280 và 360. Sau sửa: nút lệch phải 894 < mép thẻ 910 (1280) và 326 < 342 (360), trang không cuộn ngang. Không đổi `DataTable` dùng chung.
7. **Test vitest mới** (`mock.test.ts`, 5 ca): 28 việc và nhãn; mặc định V1/V2; dòng Hoá đơn bán mờ kèm tên việc; bật V1 → cần xác nhận, `widened` = `invoices`; tắt rồi bật V2 → `widened` = V2.

**Ảnh (scratchpad, không commit):** `…/scratchpad/pv6fe/before-members-{1280,360}.png`, `after-members-{1280,360}.png` (bảng Thành viên với dữ liệu giả lập 3 nhóm khác + tên dài), `before-1280.png`, `before-wh-1280.png` (trang nhóm nguyên trạng).

**Còn nợ / lưu ý:**
- Chạy e2e `ed_batch14` trên BE thật (để thấy 2 công tắc mới do BE trả) cần BE + dữ liệu chạy; lô này chỉ kiểm bằng mock, QA nên chạy lượt thật.
- Mock `gate_capability: "view_sales_invoices"` khiến dòng Hoá đơn bán mờ khi tắt V1 (khớp BE). Phiên đăng nhập mock không đổi quyền theo việc đã bật/tắt (ghi chú cũ của `mock.ts`).

**Kiểm chứng Lô 6 FE:** `tsc --noEmit` sạch; `vitest` 105 file / 1285 test PASS; build thật (`USE_MOCK=0`) sạch, `check-no-mock` XANH (32 file mock, 208 chuỗi seed, 258 file), `check-ai-chunks` XANH (48 màn + 2 layout), grep `cave_erp_mock` trong `out/` rỗng; e2e mock `ed_batch14_permissions` 158/158 PASS (AI tắt và bật), `standard_names_all_routes` 11/11 PASS (AI tắt và bật); `check_naming.py` OK.

## Lô 6 BE — sửa review techlead (10/10)

Chỉ sửa `backend/apps/accounts/data_scopes/tests/test_release_gate.py`. Không đụng code sản phẩm, migration, FE.

- **M1 (AC6)**: PUT nay gửi kèm thay đổi hợp lệ `scopes: {receipts: created_by_me}` cộng khoá số ngày ở thân: kỳ vọng 400 `INPUT_NOT_ALLOWED`.
  Thêm biến thể khoá số ngày nằm trong `scopes`: kỳ vọng 400 `SCOPE_OBJECT_UNKNOWN`. Sau vòng lặp assert `version` nhóm không tăng,
  `GroupDataScope` không đổi, `AuditLog` không thêm dòng, hai setting `*_PII_RECENT_DAYS` không đổi.
  **Chứng minh bắt được lỗi**: tạm cho `capabilities.services.BODY_KEYS` nhận 6 khoá số ngày, chạy riêng test AC6 thì ĐỎ
  (`200 != 400` ở `delivery_pii_recent_days`, `409 != 400` ở các khoá còn lại). Đã hoàn lại bằng `git checkout`, cây sạch.
- **M2 (AC3)**: `COST_KEYS = apps.common.cost_keys.COST_KEYS | {"costs"}`. Chạy lại vẫn XANH: không có rò giá vốn thật.
- **L1**: AC3 quét thêm `/api/guidance/receipt|order/<id>/`, `/api/delivery/notes/lookup/?code=<mã>.1`; test mới
  `test_pv12_ac3_s1_ai_detail_and_reports_batches_do_not_leak_cost` quét AI chi tiết đơn/phiếu giao (bật AI bằng `override_settings`),
  tem lookup (tạo `LabelPrint` giả), và assert `reports/batches/` `!= 200` cho 4 nhóm không có `view_profitreport`.
- **L2**: `SWEEP["orders"]` thêm `invoices.list` và `invoices.detail`; tập đơn của hoá đơn (bỏ tiền tố `invoice_of_`) phải bằng
  tập đơn theo D1 giao với đơn đã có hoá đơn, ở mọi giá trị D1. Xanh.
- **L3**: `SourceGrepTests.GROUP_NAME_EXCEPTIONS` khai ngoại lệ `can_cancel_any_receipt` (quyền hành động, PV-06-AC5/6, 02b dòng 98).
  Test mới quét `services.py` của mọi module có `scope.py`, chỉ cho so tên nhóm trong hàm ngoại lệ. Phát hiện thêm 2 chỗ cùng bản chất
  hành động ở `delivery/services.py` (`list_deliverers`, `assign_deliverer`: chọn người được gán phiếu, BR-GH-23) nên khai kèm.
  Test cũng đỏ nếu ngoại lệ đã khai mà không còn dùng. Backlog (techlead): story BR-PQ-33 đưa việc huỷ phiếu nhập thành việc trong ma trận.
- **N1**: import `load_baseline` lên đầu file. **N2**: AC7 gọi DELETE/PUT/PATCH trên `/api/audit-logs/` (route thật), kỳ vọng 403/405
  (hiện trạng thực tế 405 cho người xem được, 403 cho người không đủ quyền); bỏ route `/<pk>/` không tồn tại.
- Nợ: không phát sinh mới. Nợ chuyển tiếp của techlead (e2e `ed_batch14` trên BE thật) vẫn thuộc QA.

## Lô 6 FE — sửa QA (10/10)

- **B1 (Medium)**: hộp "Cho thêm người xem dữ liệu khách?" ở ma trận hiện khoá thô `view_order_customer_info`. Nguyên nhân: `objectLabel` của
  `PermissionMatrixScreen` chỉ tra `data_scopes`. Sửa: một hàm chung `features/permissions/objectLabel.ts` (`objectLabelOf`) tra `data_scopes` trước,
  rồi registry GỐC (chưa lọc AI, theo L2 ở `GroupDetailScreen`), không thấy thì "một phạm vi dữ liệu"; không bao giờ trả khoá thô. Dùng cho cả ma trận và
  trang nhóm. Test: `objectLabel.test.ts` (V2, `invoices`, khoá lạ); ca ma trận trong `e2e/ed_batch14_permissions.py` (tắt rồi bật V2 cột Nhân viên giao,
  hộp phải có nhãn tiếng Việt và không có `view_`). **Chứng minh bắt được lỗi**: dựng lại với `PermissionMatrixScreen` cũ thì ca mới ĐỎ (158/159), trả bản sửa thì XANH.
  Mock đã có sẵn `widened` cho V2 (`mockScopes.ts`), không cần sửa.
- **L1 (Low)**: bảng Thành viên, cột ghim "Thao tác": tiêu đề đục (`--surface-2`), ô sát lề + `width:1%`/`nowrap` để che ít cột nhất, viền và bóng
  về bên trái bằng `--border-strong` (không hex rời). Ảnh trước/sau ở 1280 và 360 trong scratchpad (`l1-before-*`, `l1-after-*`). Ở mock 1280 bảng vừa khung
  nên chưa tái hiện được cảnh bị che (QA gặp với dữ liệu thật); ở 360 đã thấy cột ghim tách rõ.
- Không đổi `shared/ui/**`, BE.

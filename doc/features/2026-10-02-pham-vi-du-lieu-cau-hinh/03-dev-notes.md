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

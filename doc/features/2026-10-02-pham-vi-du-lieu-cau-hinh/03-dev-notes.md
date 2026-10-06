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

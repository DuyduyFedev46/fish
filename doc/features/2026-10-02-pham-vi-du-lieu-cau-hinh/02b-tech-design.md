# Phạm vi dữ liệu cấu hình — Thiết kế kỹ thuật (02b)
> Tech Lead · 2026-10-03 · Nguồn: `01-analysis.md` (ĐÃ DUYỆT 02/10), `02-stories.md` PV-01..14 (ĐÃ DUYỆT 03/10).
>
> **ĐANG VIẾT — còn thiếu:** §5 danh sách test chi tiết theo từng AC (mới có khung), §6 danh sách file **không được đụng**
> của Lô 4–7 (mới có file được sửa), §9 mục Review (để trống, dùng sau). Phần §1–§4, §7, §8 đã chốt nội dung.
> Code đọc trên `main` @ 7137a8d.
> **10/10:** Lô 7 đã chốt ở §6.1 (phạm vi, contract, file được sửa và không được đụng, test). Lô 1–6 đã xong nên không bổ sung danh sách cho chúng nữa.

## 0. Kết luận nhanh

- **7 lô**: Lô 1 PV-01 (mốc ảnh chụp, BE) → Lô 2 PV-02 (BE) ∥ Lô F1 PV-11+PV-09 FE+PV-10 FE (mock) → Lô 3 PV-03+PV-07 →
  Lô 4 PV-04+PV-05+PV-06 → Lô 5 PV-08+PV-09 BE+PV-10 BE → Lô 6 PV-12 (cổng, bỏ hàm cũ, FE nối BE thật) → Lô 7 PV-13+PV-14 (Should).
- **N1 của QA Lô 12** (NV kho mở `/orders/detail/`, API `sales/orders/<id>/` trả tên/SĐT/địa chỉ): do **PV-07** xử lý
  (việc V2 "Xem thông tin khách trên đơn & hoá đơn"). Theo Q-4, V2 **mặc định bật cho NV kho**, nên sau phát hành NV kho
  **vẫn thấy** như hôm nay; Chủ tắt V2 của nhóm NV kho là đóng hẳn đường này (đơn, hoá đơn, phiếu hoàn cùng lúc). Điểm dừng D-1.
- Đính chính contract của story (đã đọc code): W3i nằm ở `erp-console/features/permissions/` (không phải `features/staff/`);
  V1 = `sales.view_salesinvoice` + `sales.view_salesinvoiceline` (đang có ở `owner`, `manager`, `warehouse_staff`, migration
  `accounts/0002`); **Quản lý đang có** việc "Gọi xác nhận đơn" (`accounts/0011`), NV kho thì không; CSKH **không** có
  `delivery.view_deliverynote` và `inventory.view_returntostock` nên danh sách phiếu giao/hàng hoàn của C hôm nay là 403
  (ảnh chụp sẽ ghi đúng 403); W3i/W3h của Lô 14 **bật/tắt việc có hiệu lực ngay**, không có nút "Lưu thay đổi" (xem §2.6).

## 1. Kiến trúc

### 1.1 Luồng

```
Chủ (W3i/W3h) ──PUT/POST /api/staff/groups/<code>/…──► accounts/capabilities/api.py ──► data_scopes/services.py
                                                                   (CAS row_version, kiểm, AuditLog, ghi bảng)
Mọi đường đọc (list, detail, tổng, timeline, Tiếp theo, Nhờ, AI dispatch, dashboard)
   └─► hàm phạm vi của đối tượng (một hàm / đối tượng, BR-PQ-35) ──► data_scopes/resolver.py::resolve_data_scopes(user)
                                                                      (3 truy vấn nhỏ, nhớ trên đối tượng user như _perm_cache)
```

### 1.2 Module mới `backend/apps/accounts/data_scopes/` (cạnh `capabilities/`)

| File | Làm gì |
|---|---|
| `catalog.py` | Danh mục D1–D8: `ScopeObject(key, label, options, customer_data, gate_perms, gate_capability, read_only, derived_from, defaults)`, `ScopeOption(value, label, rank)`. Thay `registry.GROUP_SCOPES`. Không import model. |
| `resolver.py` | `resolve_data_scopes(user, *, overrides=None) -> dict[key, Resolved(value, via_group)]`, `resolve_data_scope(user, key) -> str`. |
| `services.py` | `describe_data_scopes(group, held)`, `validate_scope_changes`, `preview_group_changes`, `apply_scope_changes` (gọi từ `capabilities/services.py`). |
| `tests/` | snapshot (PV-01), resolver, catalog, sweep (PV-12). |
| `README.md` | bản đồ, luật, cách cập nhật tệp mốc. |

### 1.3 Luật phân giải (resolver) — chốt kỹ thuật

1. Superuser hoặc thuộc `owner` → giá trị rank lớn nhất của mọi đối tượng, `via_group` = `owner` (null với superuser).
2. Với đối tượng `k`, chỉ xét **nhóm đủ điều kiện**: nhóm của user **có ít nhất một** permission trong `k.gate_perms`
   (quyền của *nhóm*, không phải quyền gán trực tiếp). Lấy giá trị **rank lớn nhất** trong các nhóm đủ điều kiện (BR-PQ-34).
   *Lý do:* chặn rò chéo nhóm. Ví dụ người K+G, Chủ tắt "Xem đơn" của K nhưng D1 của K vẫn lưu "Tất cả" (Q-7): nếu không
   lọc theo nhóm đủ điều kiện, người này sẽ thấy mọi đơn nhờ quyền xem đơn của G cộng phạm vi "Tất cả" của K.
3. Không nhóm nào đủ điều kiện, hoặc nhóm thiếu dòng cấu hình → rank 0 (UC-6, PV-02-AC4).
4. `gate_perms`: D1 `sales.view_salesorder` · D2 `sales.view_salesinvoice` (giá trị lấy từ D1 **của nhóm đó**) ·
   D3 `delivery.view_deliverynote` · D4 `delivery.confirm_with_customer` · D5 `inventory.view_returntostock` ·
   D6 `purchasing.view_purchasereceipt`, `purchasing.add_purchasereceipt` · D7 `sales.view_customer_list`, `sales.view_customer`.
   **Sửa 06/10 (review Lô 2, H1):** với D7, nhóm có `sales.view_customer_list` đóng góp giá trị đã lưu. Nhóm chỉ có
   `sales.view_customer` (Tầng 1, ngoài registry, Chủ không tắt được) đóng góp tối đa `assigned_deliveries`, tức
   `min(giá trị lưu, assigned_deliveries)`. Lý do: tắt "Xem khách hàng" phải đóng "Tất cả khách" dù D7 vẫn lưu `all` (Q-7),
   nếu không thì nhóm G (luôn có `view_customer`) sẽ thấy mọi khách.
5. Không cache qua request. Nhớ trong `user._data_scope_cache` (cùng cách Django nhớ `_perm_cache`); mỗi request
   TokenAuthentication nạp user mới, nên đổi phạm vi có hiệu lực từ request kế tiếp (BR-PQ-36). Test đổi cấu hình rồi gọi
   lại bằng `force_authenticate` phải nạp lại user (như với permission). `overrides` (cho xem trước) thì không nhớ.
6. Truy vấn: (a) nhóm của user, (b) permission của các nhóm đó (chỉ codename trong mọi `gate_perms`), (c) `GroupDataScope`
   của các nhóm đó. Tối đa 3 truy vấn cho cả 8 đối tượng.

### 1.4 Hàm phạm vi theo đối tượng (một hàm / đối tượng)

| Đối tượng | Hàm (file) | Giá trị → điều kiện |
|---|---|---|
| D1 Đơn | `sales/orders/scope.py::scope_orders_for(user, qs, *, value=None)` | `all` → qs · `assigned_deliveries` → `invoice__delivery_notes__assigned_to=user` · `assigned_or_confirmation` → như trên **hoặc** `Exists(note ∈ customer_service_note_q(user))` (điều kiện rank 0 của D4, cố định, như code hôm nay) |
| D1 dữ liệu khách | `delivery/pii_scope.py::annotate_order_pii_visible(user, qs, *, value)` | chỉ khi value ≠ `all`: cửa sổ người giao; nhánh gọi xác nhận chỉ khi value = `assigned_or_confirmation` (thay `is_customer_service`) |
| D2 Hoá đơn | `sales/payments/invoice_list.py::scope_invoices_for` | dùng giá trị phân giải `invoices` đưa vào `scope_orders_for(..., value=)` và `annotate_order_pii_visible(..., value=)` |
| D3 Phiếu giao | **mới** `delivery/scope.py::scope_deliveries_for(user, qs)`; `deliveries_window_applies(user)` | `all` → qs · `assigned` → `assigned_to=user`. Cửa sổ SR-PII-02 áp khi value ≠ `all` |
| D4 Gọi xác nhận | `delivery/confirmation/scope.py::note_in_confirmation_scope(user, note, *, now=None)` (đổi tên từ `note_in_customer_service_scope`) | `all_pending` → True (giữ đúng nghĩa "thấy hết" của Q/K hôm nay) · `pending_or_called_recently` → điều kiện hiện có. Bỏ `is_customer_service` |
| D5 Hàng hoàn | `inventory/returns/scope.py::scope_returns_for`, `scope_delivery_notes_for` | `all` → qs · `assigned_deliveries` → `delivery_note__assigned_to=user` / `assigned_to=user` |
| D6 Phiếu nhập | **mới** `purchasing/receipts/scope.py::scope_receipts_for(user, qs, *, now=None)` | `all` → qs · `created_by_me` → `created_by=user` · `created_by_me_today` → thêm `created_at ∈ [00:00 hôm nay giờ VN, 00:00 ngày mai)` (dùng `today_in_vietnam()`, DB UTC) |
| D7 Khách | **mới** `sales/customers/scope.py::scope_customers_for(user, qs)`; `sees_all_customers(user)` | `all` → qs · `assigned_deliveries` → khách của phiếu thoả `courier_visible_note_q(user)` · `none` → `qs.none()` |
| D8 Nhật ký | không có hàm (chỉ đọc, suy từ `view_audit`) | — |

V2: `sales/customers/permissions.py::can_view_order_customer_info(user)` = `user.has_perm("sales.view_order_customer_info")`.

### 1.5 Nơi áp phạm vi — liệt kê đủ đường (file:hàm)

| Đường | Hiện tại | Sau |
|---|---|---|
| Danh sách / chi tiết đơn | `sales/orders/api.py::SalesOrderViewSet.get_queryset` (`has_full_delivery_scope`) | `scope_orders_for` + `annotate_order_pii_visible(value=)` khi value ≠ all |
| Tìm đơn theo SĐT/tên `?q=` | `SalesOrderViewSet.list/_filters` (`restrict_customer_search=not has_full…`) | giới hạn khi D1 ≠ all; **thêm**: không có V2 → nhánh tìm theo khách bị tắt (chỉ tìm mã đơn), chặn dò SĐT |
| Lọc đơn `?customer=` | `can_filter_orders_by_customer` (403) | giữ 403 theo `view_customer_list`; **thêm** khách ngoài D7 → kết quả rỗng (PV-05-AC6) |
| Ô khách trên đơn | `sales/orders/serializers.py::pii_hidden`, `SalesOrderListSerializer.to_representation`, `SalesOrderDetailSerializer.get_customer` | ẩn khi không có V2 **hoặc** `pii_visible=False`; thêm khoá `customer_hidden_reason` |
| Tiếp theo · Đã làm, Nhờ, dòng thời gian đơn | `sales/orders/next_steps.py::get_order_guidance` (`scope_orders_for`) | đi theo, không sửa ngoài import |
| Hoá đơn bán list/detail/tổng | `sales/payments/api.py::SalesInvoiceViewSet.get_queryset`, `invoice_list.py::scope_invoices_for`, `build_totals` | theo D2; tổng dùng cùng queryset |
| Tên khách trên hoá đơn | `sales/payments/serializers.py::SalesInvoiceListSerializer.to_representation` (`can_view_customer_directory`) | V2 + `pii_visible` (ngoại lệ duyệt Q-4) |
| Phiếu hoàn tiền (cửa phụ, có tên/SĐT khách) | `sales/refunds/api.py::RefundViewSet` (không phạm vi), `refunds/serializers.py` | **thêm**: dòng theo D1 qua `sales_invoice__sales_order` / `payment_transaction__sales_order`; tên/SĐT theo V2. Mặc định Q/Chủ = all, V2 bật → không đổi ảnh chụp |
| Dashboard (cửa phụ) | `reports/dashboard_api.py::DashboardSummaryView.get` (`recent_orders`, đếm đơn, doanh thu) | `recent_orders`, `pending_orders`, `booked_soon` qua `scope_orders_for`; `revenue_today` qua `scope_invoices_for`. Mặc định Q/K/Chủ = all → không đổi |
| Phiếu giao list/detail/Việc giao của tôi/đổi trạng thái/giao người/tem | `delivery/api.py::DeliveryNoteViewSet.get_queryset`, `get_serializer_context` (`pii_restricted`), `_filter_assigned_to` | `scope_deliveries_for`; `pii_restricted = D3 ≠ all`; lọc người khác 403 khi D3 ≠ all. Action `assign`, `set_status`, `label*` đi qua `get_object` |
| Dòng thời gian phiếu giao | `delivery/next_steps.py::_scope_notes_for`, `_note_in_scope` | `scope_deliveries_for`; nhánh không có `view_deliverynote` dùng `note_in_confirmation_scope` |
| Gọi xác nhận: chi tiết, claim, ghi gọi, huỷ, tìm, hàng chờ (che SĐT) | `delivery/confirmation/api.py` (6 chỗ `note_in_customer_service_scope` + `CustomerSearchView.post`), `confirmation/serializers.py:96` | `note_in_confirmation_scope`; view tính giá trị D4 **một lần** và đưa vào context serializer (không phân giải mỗi dòng) |
| Hàng hoàn list/detail/tạo (chọn phiếu giao)/timeline | `inventory/returns/api.py::get_queryset`, `returns/serializers.py:52`, `returns/next_steps.py` | theo D5 trong `scope.py` |
| Phiếu nhập list/detail/sửa/gửi ghi nhận/timeline | `purchasing/receipts/api.py::PurchaseReceiptViewSet.get_queryset`, `receipts/next_steps.py` (chưa có `scope_fn`) | `scope_receipts_for`; thêm `scope_fn` vào provider `receipt` |
| Huỷ phiếu nhập | `receipts/api.py::cancel` → `services.cancel_receipt` (luật người tạo hoặc Q/Chủ) | `get_queryset` **không** lọc D6 cho action `cancel`; nếu dòng ngoài D6 **và** không qua luật huỷ cũ → 404 (không lộ tồn tại); trong D6 → lỗi như hôm nay (PV-06-AC5/6). Tách vị từ `can_cancel_receipt(actor, receipt)` ra khỏi `cancel_receipt`, không đổi hành vi |
| Danh bạ khách mới | `sales/customers/directory_api.py::CustomerDirectoryViewSet.get_queryset` (list, retrieve, partial_update, `search`) | cổng giữ `view_customer_list`; dòng theo `scope_customers_for` |
| API khách cũ | `sales/customers/api.py::CustomerViewSet` (`sees_customer_directory`) | dòng theo `scope_customers_for`; serializer đủ khi D7 = all, còn lại `CourierCustomerSerializer` |
| Dòng thời gian khách | `sales/customers/next_steps.py` | thêm `scope_fn=scope_customers_for` |
| AI | `apps/ai/execution/dispatch.py` gọi lại view DRF bằng user thật | tự đi theo `get_queryset`; `scrub_data` vẫn bỏ khoá dữ liệu khách với mọi người. `/api/staff/` đã trong `FORBIDDEN_PREFIXES` |
| ⌘K | `erp-console/shared/ui/shell/CommandSearch.tsx` chỉ nhảy menu, **không gọi API** | không đổi. Lô 17 (nhảy theo mã) phải gọi endpoint chi tiết đã có phạm vi |
| Xuất file | grep 03/10: **không có** endpoint xuất CSV/XLSX | không đổi; endpoint xuất sau này phải dùng hàm phạm vi của đối tượng |
| Tra đơn công khai Shop | `sales/orders/shop_api.py` | không đổi (S-2). Có test hồi quy PV-07-AC9 |
| "Quyền của tôi" | `accounts/auth/services.py::describe_user` | thêm `data_scopes` (PV-14) |

## 2. Contract API (BE và FE cùng bám)

Mọi endpoint dưới `/api/staff/groups/` đã nằm trong danh sách cấm của AI. Đọc: `CanManageStaff` (`accounts.manage_staff`).
Ghi và xem trước: chỉ Chủ hoặc superuser (`actor_is_owner`), người khác 403 kể cả có `manage_staff`.

### 2.1 GET `/api/staff/groups/` — chỉ thêm khoá

Mỗi nhóm thêm `"version": "41"` và `"data_scope_values": {"orders": "all", "customers": "none", …}` (6 đối tượng sửa được;
W3h cần để gửi kèm D7 khi bật "Xem khách hàng", PO-Q1).

### 2.2 GET `/api/staff/groups/<code>/` — chỉ thêm khoá

Như story, thêm hai khoá cho mỗi dòng `data_scopes`: `gate_capability` (mã việc ở registry hay `null`, để FE bỏ mờ ngay khi
bật việc trong bản nháp, PV-11-AC3) và `note` (có thể `null`). Ví dụ:

```json
{
  "version": "41",
  "data_scopes": [
    {"key": "orders", "label": "Đơn hàng", "value": "assigned_deliveries", "editable": true, "customer_data": true,
     "gate_capability": "view_orders", "inactive_reason": null, "note": null,
     "options": [
       {"value": "assigned_deliveries", "label": "Đơn có phiếu giao gán cho tôi", "rank": 0},
       {"value": "assigned_or_confirmation", "label": "Đơn có phiếu gán cho tôi hoặc trong phạm vi gọi xác nhận", "rank": 1},
       {"value": "all", "label": "Tất cả đơn", "rank": 2}]},
    {"key": "invoices", "label": "Hoá đơn bán", "value": "follows_orders", "editable": false, "customer_data": true,
     "gate_capability": "view_sales_invoices", "inactive_reason": null, "note": "Theo Đơn hàng", "options": []},
    {"key": "audit_log", "label": "Nhật ký hoạt động", "value": "all", "editable": false, "customer_data": false,
     "gate_capability": "view_audit", "inactive_reason": null, "note": null, "options": []}
  ],
  "scopes": {"orders": "Được gán", "deliveries": "Phiếu gán cho tôi", "customers": "Không xem"}
}
```

- Thứ tự D1…D8: `orders, invoices, deliveries, confirmation, returns, receipts, customers, audit_log`.
- `scopes` cũ giữ tới Lô 6 nhưng nay **dựng từ cấu hình** (hết chữ sai "Trong phạm vi gọi"); bỏ ở Lô 6 cùng lúc FE đổi kiểu.
- `version` = `str(GroupAccessConfig.row_version)`. Nhóm `owner`: mọi dòng rộng nhất, `editable: false`, `note: "Chủ luôn thấy tất cả"`.
- `inactive_reason` khác `null` khi nhóm không có `gate_perms` của đối tượng; với D3/D5 (quyền Tầng 1 ngoài registry) chữ là
  "Nhóm không có quyền xem …", Chủ không bật được ở màn này.
- `timeline`: thêm sự kiện `kind: "change_group_data_scopes"`, `label: "Đổi phạm vi Phiếu nhập: Tất cả phiếu → Do tôi tạo trong ngày"`,
  `actor.display` = tên người làm (FE ghép thành "Lộc đổi phạm vi…", cùng cách sự kiện việc của B4). Một sự kiện cho mỗi đối tượng.
- `last_changed_at`/`last_changed_by` tính cả AuditLog phạm vi.

### 2.3 PUT `/api/staff/groups/<code>/capabilities/`

Thân: `{"version": "41", "capabilities": {...}?, "scopes": {...}?, "confirm_customer_data_widening": true?}`. 200 trả body như GET.

Thứ tự kiểm (lỗi đầu tiên thắng, cả yêu cầu hoặc không đổi gì):

| # | Kiểm | HTTP / `code` |
|---|---|---|
| 1 | người gọi không phải Chủ/superuser | 403 |
| 2 | nhóm lạ | 404 `GROUP_NOT_FOUND` |
| 3 | `code = owner` | 400 `GROUP_LOCKED` |
| 4 | khoá thân lạ (ngoài 4 khoá) / `key` việc lạ | 400 `INPUT_NOT_ALLOWED` |
| 5 | thiếu `version`; `capabilities` và `scopes` đều rỗng; sai kiểu | 400 `INVALID_INPUT` |
| 6 | khoá phạm vi lạ / `invoices`,`audit_log` / giá trị lạ | 400 `SCOPE_OBJECT_UNKNOWN` / `SCOPE_READ_ONLY` / `SCOPE_VALUE_INVALID` |
| 7 | việc `owner_only` | 400 `BR-PQ-32` |
| 8 | khoá dòng `GroupAccessConfig` (`select_for_update`), `row_version ≠ version` | **409 `GROUP_CHANGED`** "Nhóm này vừa được người khác đổi. Tải lại để xem bản mới." (`ConflictError`) |
| 9 | `requires` | 400 `CAPABILITY_REQUIRES` |
| 10 | trạng thái cuối "Xem khách hàng" bật mà D7 = `none` (PO-Q1) | 400 `SCOPE_VALUE_INVALID` "Bật Xem khách hàng thì chọn phạm vi Khách hàng khác Không xem." |
| 11 | mở rộng dữ liệu khách (§2.5) mà `confirm_customer_data_widening !== true` | 400 `CUSTOMER_DATA_WIDENING_UNCONFIRMED`, body có `impact` (= body xem trước) |
| 12 | áp: việc → AuditLog `change_group_capabilities`; phạm vi → AuditLog `change_group_data_scopes`; có thay đổi thật thì `row_version += 1` | 200 |

Không có thay đổi thật nào (mọi giá trị trùng) → 200, không AuditLog, **không** tăng `version` (vẫn qua bước 8).
AuditLog phạm vi: `changes = {"<key>": {"from": "...", "to": "..."}, …}` + `"customer_data_widening_confirmed": true` khi có mở rộng.
Khi mở rộng chỉ do bật V2 (không đổi phạm vi), cờ nằm trong `changes` của `change_group_capabilities`; `_capability_events`,
`capability_change_label` và `_scope_events` phải **bỏ qua** khoá không phải mã việc/mã đối tượng.

### 2.4 POST `/api/staff/groups/<code>/permissions-preview/`

Thân như PUT, không cần `version`/`confirm_…` (**chốt 07/10:** có gửi thì bỏ qua, khoá lạ khác vẫn `INPUT_NOT_ALLOWED`);
kiểm 1–7, 9, 10 như PUT; không ghi gì. Trả như story:
`widens_customer_data`, `widened[]`, `affected_members[]` (nhân viên đang hoạt động của nhóm, chỉ `id`, `display_name`),
`affected_count`, `message`, `already_wider_elsewhere[]`, `narrowed[]` với `rows_losing_access`.

- `rows_losing_access`: số dòng **chưa kết thúc** thành viên đang thấy và sẽ mất (gộp không trùng): phiếu nhập `DRAFT`,
  hàng hoàn `DRAFT`, đơn `BOOKED|PAID|PROCESSING`, phiếu giao chưa `COMPLETED|CANCELLED`, việc gọi đang mở; khách = 0.
  Tính bằng `resolve_data_scopes(member, overrides={group_id: {...}})` trước/sau.
- `already_wider_elsewhere`: thành viên mà nhóm khác (đủ điều kiện) cho rank lớn hơn giá trị mới của nhóm này.

### 2.5 Định nghĩa "mở rộng dữ liệu khách" (chốt kỹ thuật, chặt hơn story một chút)

Với mỗi đối tượng có dữ liệu khách D1, D2, D3, D4, D5, D7, gọi *tầm với* = (cổng mở?, rank). Mở rộng khi sau thay đổi cổng mở và
(rank tăng **hoặc** cổng vừa mở với rank > 0). Cổng: D1 `view_orders`, D2 `view_sales_invoices` (rank theo D1), D4
`confirm_calls`, D7 `view_customers`; D3/D5 cổng Tầng 1 ngoài registry (luôn như đang có). Cộng: bật V2. Lý do: Q-7 giữ giá trị
khi tắt việc, nên bật lại việc trên nhóm đang lưu "Tất cả" mở dữ liệu khách mà story chưa tính.
**Sửa 07/10 (review F1, M1):** rank dùng để so là rank **hiệu lực** sau luật §1.3, gồm trần D7: nhóm thiếu
`sales.view_customer_list` mà có `sales.view_customer` (Quản lý, NV giao) thì cổng D7 vẫn mở với rank `min(lưu, assigned_deliveries)`.
Ví dụ: NV giao lưu D7 = `all`, bật "Xem khách hàng" là **mở rộng** (1 → 2). Đổi D7 từ `assigned_deliveries` sang `all` khi việc còn
tắt **không** là mở rộng. PUT có `confirm_customer_data_widening: true` mà không có mở rộng: nhận, không ghi cờ vào AuditLog.

### 2.6 FE: W3i chuyển sang bản nháp, W3h giữ bật/tắt ngay

- **W3i** (`GroupDetailScreen`): việc và phạm vi thành **bản nháp** cùng thanh "Lưu thay đổi / Huỷ thay đổi" (PV-11-AC3..5
  đòi điều này; story ghi "nút đang có của B4" là nhầm, B4 bật/tắt ngay). Lưu: nếu có đổi phạm vi hoặc có việc bật thuộc §2.5
  → gọi xem trước → hộp cảnh báo (mở rộng) hoặc ghi chú (thu hẹp) → PUT có `confirm…`. Bật "Xem khách hàng" khi D7 = `none`
  thì bản nháp tự đặt D7 = `all` (PO-Q1).
- **W3h** (`PermissionMatrixScreen` + `useCapabilityToggle`): vẫn bật/tắt ngay, gửi `version` của nhóm; 409 → báo và tải lại
  danh sách; 400 `CUSTOMER_DATA_WIDENING_UNCONFIRMED` → mở **cùng** hộp cảnh báo bằng `impact` rồi gửi lại có xác nhận; bật
  "Xem khách hàng" khi `data_scope_values.customers = "none"` thì gửi kèm `scopes.customers = "all"`. "Hoàn tác" gửi `version` mới.
- Không lưu bản nháp vào `localStorage`/URL; không log body.

### 2.7 Khoá thêm ở đơn, hoá đơn, phiếu hoàn (Lô 3, chỉ thêm)

`customer_hidden_reason`: `null` | `"expired"` (quá cửa sổ) | `"not_permitted"` (không có V2). Ô khách vẫn `null` như hiện nay.
FE (Lô 7) đổi chữ: "Đã ẩn (quá 7 ngày)" / "Đã ẩn (không có quyền xem thông tin khách)".

### 2.8 `/api/auth/me/` (PV-14)

Thêm `data_scopes` 8 dòng theo thứ tự D1…D8: `{key, label, value, value_label, via_group}`. Đối tượng không có quyền xem
(không nhóm nào đủ điều kiện **và** không có permission cổng trực tiếp) → `value: "none"`, `value_label: "Không xem"`,
`via_group: null` (chốt PV-14-AC3: giữ đủ 8 dòng để FE ổn định).

## 3. Model và migration (bất biến 8: lý do = Duy 02/10 #9 #12 #13; `auth.Group` không có chỗ lưu)

`backend/apps/accounts/models.py` thêm:

```python
class GroupAccessConfig(models.Model):      # một dòng / nhóm, khoá lạc quan cho mọi lần lưu của nhóm
    group = models.OneToOneField("auth.Group", on_delete=models.CASCADE, related_name="access_config")
    row_version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

class GroupDataScope(models.Model):         # nhóm × đối tượng → giá trị
    group = models.ForeignKey("auth.Group", on_delete=models.CASCADE, related_name="data_scopes")
    object_key = models.CharField(max_length=32)
    value = models.CharField(max_length=40)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["group", "object_key"], name="uniq_group_data_scope")]
        default_permissions = ()             # chỉ sửa qua service, không qua Admin/ma trận
```

`GroupAccessConfig` cũng có `default_permissions = ()` (duyệt lệch 1, review 06/10).

CASCADE vì đây là cấu hình, không phải chứng từ (bất biến 3 chỉ áp FK tới User và chứng từ); Group không bị xoá trong hệ thống.
Không lưu dòng cho `owner` (luôn rộng nhất). D2, D8 không lưu (suy ra). Chỉ mục: ràng buộc duy nhất `(group_id, object_key)` đủ cho
resolver.

| Migration | Loại | Nội dung | Lùi |
|---|---|---|---|
| `accounts/0014_group_data_scopes.py` | schema | CreateModel ×2 | xoá bảng (`migrate accounts 0013`) |
| `accounts/0015_seed_group_data_scopes.py` | data, idempotent (`get_or_create`, không đè) | `GroupAccessConfig(row_version=1)` cho 5 nhóm; mặc định Q/K/G/C theo bảng contract; D7 = `all` nếu nhóm **đang có** `sales.view_customer_list` lúc migrate, còn lại G `assigned_deliveries`, khác `none`; D4 của G lưu `pending_or_called_recently` (rank 0, ô mờ). Giá trị **chép cứng** trong migration, không import `catalog.py` | xoá các dòng vừa tạo |
| `sales/0014_salesorder_view_order_customer_info.py` | AlterModelOptions | thêm `("view_order_customer_info", "Xem thông tin khách trên đơn & hoá đơn")` vào `SalesOrder.Meta.permissions` | gỡ |
| `sales/0015_grant_view_order_customer_info.py` | data (mẫu `sales/0013`) | cấp cho `owner`, `manager`, `warehouse_staff`, `delivery_staff`, `customer_service` | gỡ khỏi 5 nhóm |

Phụ thuộc: `0015_seed…` cần `accounts/0013_rename_groups_to_english`, `sales/0013_grant_view_customer_list`. V1 không cần migration.
Đường lùi: code cũ không đọc hai bảng mới nên rollback chỉ cần triển khai bản code trước; migrate lùi là tuỳ chọn. Kiểm
`makemigrations --check --dry-run` sạch ở mọi lô.

## 4. Rủi ro và cơ chế chặn

| # | Rủi ro | Mức | Chặn | Test bắt |
|---|---|---|---|---|
| R1 | Mở dữ liệu khách cho cả nhóm do lỡ tay | Critical | §2.5 + PUT 400 khi thiếu xác nhận (BE, FE không vượt được) + AuditLog có cờ | PV-09-AC1..4, AC9; test bật lại `view_orders` trên nhóm lưu `all` cũng đòi xác nhận |
| R1b | Rò chéo nhóm (giá trị giữ khi tắt việc, Q-7) | Critical | §1.3 luật 2 "nhóm đủ điều kiện" | test K+G với K tắt `view_orders`, D1 K = all → chỉ đơn gán |
| R2 | Lệch đường đọc (cửa phụ) | Cao | §1.5 một hàm / đối tượng; thêm refunds, dashboard, tìm `?q=` | PV-12-AC2 quét; test `?q=<SĐT giả>` khi V2 tắt → không khớp |
| R3 | Chuyển đổi đổi hành vi | Cao | PV-01 mốc trên code cũ, khoá theo **nhãn fixture** (không theo pk) | PV-01, PV-12-AC1 |
| R4 | Rò giá vốn | Critical | Phạm vi không đụng `CostFieldSerializerMixin`; `sensitive_fields` giữ nguyên | PV-03-AC8, PV-06-AC7, PV-12-AC3 |
| R5 | Rò dữ liệu khách trong log/AuditLog/xem trước | Critical | `changes` chỉ mã; `affected_members` chỉ tên nhân viên; không log body | PV-08-AC9, PV-09-AC9, PV-12-AC5 (grep tên/SĐT giả) |
| R6 | Leo quyền ghi phạm vi | Cao | `actor_is_owner` trước mọi kiểm; preview cùng luật | PV-08-AC7, PV-09-AC8 |
| R7 | Ghi đè đồng thời | Trung bình | `select_for_update` + so `row_version` trong transaction | PV-10-AC1..5 (AC5 luồng thật chỉ chạy trên Postgres: `skipUnless(connection.vendor == "postgresql")`; SQLite chạy bản tuần tự) |
| R8 | Hiệu năng | Thấp | ≤ 3 truy vấn phân giải / request, nhớ trên user; hàng chờ gọi phân giải 1 lần / request | `assertNumQueries` danh sách đơn: tăng tối đa +3 so với số gốc (be-dev ghi số vào 03-dev-notes) |
| R9 | Người không nhóm có quyền gán trực tiếp đổi hành vi (D6 hẹp lại, D7 thành `none`; **D4 giữ `none`**, không lên rank 0 vì như vậy là mở thêm dữ liệu khách; sửa 08/10, review Lô 4) | Trung bình | PV-02-AC4 đã duyệt; kiểm đếm trên production trước deploy | Duy chốt 08/10 (D-3): chặn hẳn ở cổng xác thực `AUTH_NO_ROLE`; phạm vi thu hẹp là lớp phòng thủ thứ hai, `PENDING_DUY_DIFFS` rỗng |
| R10 | Sai lệch ma trận production so với migration (Chủ đã đổi việc qua B4) | Trung bình | data migration đọc quyền **thực tế** cho D7; V2 bật cố định theo Q-4 | điểm dừng D-2 |
| R11 | FE cũ gửi PUT không `version` sau khi BE lên | Thấp | triển khai BE và ERP cùng lượt | ghi ở 02c |

## 5. Test bắt buộc (khung — **còn thiếu bảng chi tiết theo AC**)

- **PV-01 chạy trước mọi sửa code phạm vi.** `backend/apps/accounts/data_scopes/tests/test_scope_snapshot.py` + tệp mốc
  `scope_snapshot_baseline.json`. Fixture dữ liệu giả dựng theo thứ tự cố định, giờ cố định (patch `django.utils.timezone.now`).
  Mốc ghi theo **nhãn fixture** (`order_assigned_courier`, `note_ended_8_days`…), không ghi pk hay mã sinh tự động. Ghi: tập nhãn
  thấy được, mã HTTP chi tiết, cờ có/không giá trị của tên/SĐT/địa chỉ. Sinh lại mốc bằng `UPDATE_SCOPE_SNAPSHOT=1`.
  `APPROVED_DIFFS` chỉ một mục: `(warehouse_staff, invoices.list, customer_name)` "Duy duyệt 02/10 Q-4". Endpoint: §1.5 (đơn
  list/detail/`?q=`, hoá đơn, phiếu hoàn tiền, phiếu giao list/`assigned_to=me`/detail, hàng hoàn, phiếu nhập, hàng chờ + chi
  tiết + tìm gọi xác nhận, danh bạ mới + `/customers/`, guidance order/delivery/return/customer/receipt, lệnh AI đọc đơn,
  dashboard). Test tự kiểm AC4: không chuỗi tên/SĐT/địa chỉ giả nào trong tệp mốc.
- Grep test (PV-05-AC8, PV-12-AC8): `backend/apps` (trừ `tests/`, `migrations/`) không còn `FULL_SCOPE_GROUPS`,
  `has_full_delivery_scope`, `CUSTOMER_DIRECTORY_GROUPS`, `sees_customer_directory`, `is_customer_service`, `GROUP_SCOPES`.
- Catalog: mỗi đối tượng đúng một rank 0, rank không trùng, mặc định thuộc lựa chọn; seed migration == `catalog.defaults`.
- Mỗi endpoint đổi: 401, 403 (thiếu Tầng 1), 404 ngoài phạm vi, không khoá giá vốn với K/G, không dữ liệu khách khi V2 tắt.
- D6 ngày giờ: 23:50 hôm trước / 08:00 hôm nay / qua nửa đêm (PV-06-AC3, AC4).
- Lệnh kiểm chứng mỗi lô: `manage.py test`, `makemigrations --check --dry-run`, `python3 scripts/check_naming.py`; FE `tsc --noEmit`,
  `npm run build`, vitest `features/permissions`, e2e `ed_batch14_permissions.py` mở rộng.

## 6. Chia lô (**còn thiếu: danh sách "không được đụng" đầy đủ cho Lô 4–7**)

Chung mọi lô BE: **không đụng** `erp-console/**`, `frontend/**`, `adapter/**`, migration đã có, `doc/decisions.md`.
Chung mọi lô FE: **không đụng** `erp-console/shared/ui/**` (đợt sửa giao diện đang mở), `erp-console/features/{overview,ai,audit,auth}/**`
(Lô 15), `backend/**`.

| Lô | Story | Ai | File được sửa |
|---|---|---|---|
| 1 | PV-01 | BE | **chỉ thêm** `backend/apps/accounts/data_scopes/__init__.py`, `data_scopes/tests/**` (fixture, test, tệp mốc). Không sửa code sản phẩm. Commit riêng trước Lô 2 |
| 2 | PV-02 | BE | `accounts/models.py`, `accounts/migrations/0014,0015`, `accounts/data_scopes/{catalog,resolver,services}.py`, `accounts/capabilities/{registry,services}.py`, `accounts/staff/services.py` (gọi `resolver.forget`, duyệt 06/10) (bỏ dùng `GROUP_SCOPES`, thêm `version`, `data_scopes`, `data_scope_values`), tests |
| F1 | PV-11, PV-09 FE, PV-10 FE (mock) | FE ∥ Lô 2–5 | `erp-console/features/permissions/**`, `erp-console/e2e/ed_batch14_permissions.py` |
| 3 | PV-03, PV-07 | BE | `accounts/capabilities/registry.py` (V1, V2), `accounts/auth/services.py` (nhãn V2), `sales/models/orders.py`, `sales/migrations/0014,0015`, `sales/orders/{scope,api,serializers}.py`, `sales/payments/{invoice_list,serializers,api}.py`, `sales/refunds/{api,serializers}.py`, `sales/customers/permissions.py`, `delivery/pii_scope.py`, `reports/dashboard_api.py`, tests |
| 4 | PV-04, PV-05, PV-06 | BE | `delivery/scope.py` (mới), `delivery/{api,next_steps}.py`, `delivery/confirmation/{scope,api,serializers}.py`, `inventory/returns/{scope,api,serializers}.py`, `sales/customers/{scope.py mới,api,directory_api,next_steps}.py`, `sales/orders/api.py` (lọc `?customer=`), `purchasing/receipts/{scope.py mới,api,services,next_steps}.py`, tests |
| 5 | PV-08, PV-09 BE, PV-10 BE | BE | `accounts/capabilities/{api,services,next_steps}.py`, `accounts/data_scopes/services.py`, `config/api_urls.py` (route preview), tests |
| 6 | PV-12 + dọn | BE ∥ FE | BE: `common/api.py` (bỏ `FULL_SCOPE_GROUPS`, `has_full_delivery_scope`, `CUSTOMER_DIRECTORY_GROUPS`, `sees_customer_directory`), bỏ `scopes` cũ, test quét. FE: `features/permissions/**` nối BE thật, bỏ kiểu `GroupScopes` |
| 7 | PV-13, PV-14 (Should) | BE ∥ FE | sau khi đợt giao diện và Lô 15 đã gộp. BE `accounts/auth/services.py`; FE `features/auth/components/AccountScreen.tsx`, màn chi tiết đơn/hoá đơn/phiếu giao/hàng hoàn/phiếu nhập/khách/gọi xác nhận, `shared/lib/personalData.ts`, `shared/lib/messages.ts` |

FE mock theo §2 ngay từ Lô F1; `features/permissions/mock.ts` giữ luật BE (CAS version, 409, 400 xác nhận, PO-Q1). Kho tạm
mock vẫn là `sessionStorage` (chỉ chế độ mock, không có dữ liệu khách).

## 6.1 Lô 7 — phiếu giao việc (10/10)

> Tech Lead · 2026-10-10 · đọc code trên `feat/pv6-cum` @ `75999fd` (đã gồm Lô 6 BE+FE). Lô 1–6 đã merge hoặc đã nằm trong nhánh
> này, nên phần "không được đụng" còn thiếu ở §6 nay chỉ cần cho Lô 7 (dưới đây). Nguồn: 02-stories PV-13, PV-14; §2.7, §2.8;
> 02c-quyet-dinh-08-10 §C, §G.3; 03b L3 (Lô 5); `doc/decisions.md` 08/10 và 10/10.

### 6.1.1 Phạm vi sau quyết định 08/10

| Việc | Kết luận |
|---|---|
| **03b L3 (Lô 5)**: thêm `customer_hidden_reason` cho phiếu giao | **Đóng, không làm.** Theo Duy 08/10 câu 7, V2 không áp cho phiếu giao (`delivery/serializers.py:54-60` chỉ còn một luật: D3 ≠ `all` **và** quá cửa sổ SR-PII-02). Ô khách của phiếu giao là `null` thì lý do **luôn** là quá 7 ngày, nên chữ hiện có "Đã ẩn (quá 7 ngày)" luôn đúng. Thêm khoá mà không có ai đọc là đổi contract không cần thiết. Hàng hoàn không có ô khách. Gọi xác nhận chỉ che SĐT, không trả `null` vì V2. Nếu sau này V2 áp lại cho phiếu giao thì mở lại L3. |
| **§2.7 FE** (đã hẹn cho Lô 7): đổi chữ theo `customer_hidden_reason` ở đơn, hoá đơn, phiếu hoàn tiền | **Làm (FE).** BE đã trả khoá này từ Lô 3 (`sales/customers/permissions.py::customer_hidden_reason`). FE hiện coi mọi `null` là "quá 7 ngày", nên sai khi Chủ tắt V2. |
| Lệch FE phát hiện khi đọc code: cột Khách của danh sách hoá đơn bán vẫn mở theo `sales.view_customer_list` (`SalesInvoiceListScreen.tsx:78`), trong khi BE từ PV-07 trả tên theo V2 | **Làm (FE).** Đổi điều kiện mở cột sang V2 `sales.view_order_customer_info`. Đây là ngoại lệ Duy đã duyệt (Q-4): NV kho thấy tên khách trên hoá đơn. |
| Phiếu hoàn tiền: `customer_name`/`customer_phone` có thể `null` (03-dev-notes Lô 3 #6) | **Làm (FE).** Kiểu đang là `string` optional, phải chịu được `null`. |
| PV-13 (FE) | **Làm.** Bảng AC ở §6.1.2. |
| PV-14 BE | **Làm.** `/api/auth/me/` thêm `data_scopes`. `is_superuser` đã có từ Lô QĐ. |
| PV-14 FE | **Làm.** Thêm khối "Dữ liệu bạn xem được" vào `AccountScreen`. |
| Nhãn vai "CSKH" thành "Nhân viên gọi xác nhận" | **Đã có.** `auth/services.py::GROUP_LABELS`. Lô 7 không đụng. |
| Migration | **Không có.** `makemigrations --check --dry-run` phải sạch. |

### 6.1.2 Kiểm từng AC so với code hiện tại

| AC | Hiện trạng | Việc Lô 7 |
|---|---|---|
| PV-13-AC1 | BE trả 404 khi mục nằm ngoài phạm vi (đúng). FE thì tuỳ màn. `orders/useDetail.ts:66`, `customers/useCustomerDetail.ts` và `returns/useReturnDetail.ts` **giữ dữ liệu cũ** khi tải lại bị 404 (để `status` ở "ok"), nên người dùng vẫn thấy mục cũ cùng tên, SĐT, địa chỉ khách. `DeliveryDetailScreen`, `ConfirmationDetailScreen`, `ReceiptDetailScreen` chuyển sang "Không tìm thấy trang này" | **Thiếu.** Thêm trạng thái `scope_lost` (§6.1.4) |
| PV-13-AC2 | Không có | **Thiếu.** Chỉ có ở `ReceiptDetailScreen` |
| PV-13-AC3 | BE lọc đúng. Riêng FE `shared/lib/usePagedList.ts::loadMore`: khi phạm vi hẹp lại, DRF `PageNumberPagination` trả 404 cho trang ngoài tầm, và FE hiện `moreError` ("Không tải thêm được.") | **Thiếu một chỗ.** `loadMore` gặp 404 thì tải lại trang 1 (giữ dòng cũ tới khi có kết quả), không báo lỗi. "Làm mới" đã đúng sẵn, chỉ cần test |
| PV-13-AC4 | `useDetail` tải lại bị 500 thì giữ màn và báo lỗi qua `error`; tải lần đầu bị 500 thì hiện `ErrorScreen` | **Đã có, chỉ cần test.** Ràng buộc: `scope_lost` **chỉ** xảy ra khi `ApiError.status === 404` |
| PV-13-AC5 | Xem AC1: hiện màn vẫn giữ dữ liệu khách cũ khi tải lại bị 404. Đã grep `console.log/warn/error` trong `features`, `shared`, `app`: không có | **Thiếu.** Khi sang `scope_lost` phải xoá `data` khỏi state (`setData(null)`) và không vẽ phần nào của mục cũ, kể cả tiêu đề, khối AI, dòng thời gian |
| PV-14-AC1 | Resolver đã đúng luật lấy rộng nhất (`resolver.py::_resolve_object`), nhưng `/me` chưa có khoá | **Thiếu (BE).** Phần chạy thật đã kiểm trên DB tạm (bảng §6.1.3) |
| PV-14-AC2 | Từ D-3, `/api/auth/me/` vẫn mở cho người không nhóm (`allow_without_group`) | **Thiếu (BE).** Chốt ở §6.1.3 quy tắc 1 (khác chữ của story một chút, có lý do) |
| PV-14-AC3 | — | **Thiếu (BE).** Đã chốt ở §2.8: giữ đủ 8 dòng, dòng không có quyền ghi `none` |
| PV-14-AC4 | `AccountScreen.tsx` có khối "Việc bạn được làm" (`acc-cap`) và "Mục bạn thấy trên menu", chưa có khối phạm vi | **Thiếu (FE)** |
| PV-14-AC5 | `data_scopes/tests/test_api_describe.py::test_pv02_ac9_permissions_unchanged_for_reading` đã kiểm `giao1` gọi `GET /api/staff/groups/manager/` bị 403 | **Đã có, chỉ cần test.** QA chạy lại trên BE thật bằng `qa_courier1` |
| PV-14-AC6 | `auth/tests/test_s6_me.py:46-55` và `test_s47_me_labels.py:167-169` so **bằng nhau** tập khoá | Sửa 2 test này: chỉ thêm `"data_scopes"` vào tập khoá, không bỏ khoá nào |

### 6.1.3 Contract PV-14: `GET /api/auth/me/`, chỉ thêm khoá

Endpoint không đổi: cần đăng nhập, được miễn cổng D-3 và cổng đổi mật khẩu như hôm nay. Chỉ thêm một khoá `data_scopes`.

```json
"data_scopes": [
  {"key": "orders",       "label": "Đơn hàng",          "value": "all",                 "value_label": "Tất cả đơn",               "via_group": "warehouse_staff"},
  {"key": "invoices",     "label": "Hoá đơn bán",       "value": "all",                 "value_label": "Hoá đơn của tất cả đơn",   "via_group": "warehouse_staff"},
  {"key": "deliveries",   "label": "Phiếu giao",        "value": "all",                 "value_label": "Tất cả phiếu",             "via_group": "warehouse_staff"},
  {"key": "confirmation", "label": "Gọi xác nhận",      "value": "none",                "value_label": "Không xem",                "via_group": null},
  {"key": "returns",      "label": "Hàng hoàn",         "value": "all",                 "value_label": "Tất cả phiếu",             "via_group": "warehouse_staff"},
  {"key": "receipts",     "label": "Phiếu nhập",        "value": "all",                 "value_label": "Tất cả phiếu",             "via_group": "warehouse_staff"},
  {"key": "customers",    "label": "Khách hàng",        "value": "assigned_deliveries", "value_label": "Khách của phiếu giao gán cho tôi (trong cửa sổ)", "via_group": "delivery_staff"},
  {"key": "audit_log",    "label": "Nhật ký hoạt động", "value": "none",                "value_label": "Không xem",                "via_group": null}
]
```
(Ví dụ là người kiêm NV kho và NV giao với cấu hình mặc định.)

- Luôn đủ **8 dòng**, theo thứ tự `catalog.OBJECTS`. Mỗi dòng có **đúng 5 khoá**. `label` lấy từ `catalog`.
- Giá trị hợp lệ:
  - `orders`, `invoices`: `assigned_deliveries` · `assigned_or_confirmation` · `all` · `none`
  - `deliveries`: `assigned` · `all` · `none`
  - `confirmation`: `pending_or_called_recently` · `all_pending` · `none`
  - `returns`: `assigned_deliveries` · `all` · `none`
  - `receipts`: `created_by_me_today` · `created_by_me` · `all` · `none`
  - `customers`: `none` · `assigned_deliveries` · `all`
  - `audit_log`: `none` · `all`
- `value_label` là nhãn của lựa chọn trong `catalog` (giống chữ ở màn Phân quyền). Riêng:
  - `none` → `"Không xem"`.
  - `audit_log` `all` → `"Tất cả"`.
  - `invoices` dùng bảng chữ riêng, khai trong `data_scopes/services.py`:
    `all` → "Hoá đơn của tất cả đơn" · `assigned_deliveries` → "Hoá đơn của đơn có phiếu giao gán cho tôi" ·
    `assigned_or_confirmation` → "Hoá đơn của đơn có phiếu gán cho tôi hoặc trong phạm vi gọi xác nhận".
- `via_group` là mã nhóm **của chính người đó** đã cho giá trị này. FE tra nhãn trong `group_labels` (khoá này đã có). Giá trị là
  `null` khi người đó là superuser, khi dòng là `none`, hoặc khi giá trị đến từ quyền gán riêng (người có nhóm nhưng nhóm không đủ
  điều kiện, resolver trả rank 0 và `via_group` null).

**Quy tắc** (hàm mới `data_scopes/services.py::describe_own_data_scopes(user) -> list[dict]`, `auth/services.py::describe_user` gọi hàm này):

1. Không qua `has_erp_access(user)` (không nhóm và không phải superuser, D-3) → cả 8 dòng là `none` / "Không xem" / `null`.
   *Lệch chữ PV-14-AC2 ("giá trị hẹp nhất"), có lý do:* từ D-3 (Duy 08/10), người không nhóm bị 403 `AUTH_NO_ROLE` ở **mọi** API
   ERP, nên thực tế họ không xem được gì. Nếu ghi "Đơn có phiếu giao gán cho tôi" (rank 0) thì báo sai. `via_group: null` vẫn đúng AC2.
2. Superuser → giá trị rộng nhất của mọi đối tượng, `via_group: null`. Thuộc nhóm `owner` → rộng nhất, `via_group: "owner"`.
   (Như `resolve_data_scopes`.)
3. Các trường hợp còn lại, với từng đối tượng `k`:
   - Không có permission nào trong `k.gate_perms` (`user.has_perm`, gồm cả quyền nhóm và quyền gán riêng) → `none`. Khớp với API
     thật trả 403 ở Tầng 1.
   - `confirmation` → `apps.delivery.confirmation.scope.confirmation_scope_value(user)`, import lười trong thân hàm, theo cùng cách
     `services.py:226-232` đang làm. Lý do: luật "không có nhóm đủ điều kiện thì `none`" (Lô 4, review mục 2) chỉ có ở hàm này.
     Không chép lại luật này.
   - `audit_log` → `all`. Quyền xem nhật ký không có phạm vi dòng (`CanViewAuditLog` chỉ kiểm permission).
   - Đối tượng khác → `resolve_data_scopes(user)[k]` (`value`, `via_group`). Đây cũng là giá trị mà `orders_scope_value`,
     `deliveries_scope_value`, `returns_scope_value`, `receipts_scope_value`, `customers_scope_value` và `scope_invoices_for` đọc.
     Trần D7 (H1) đã nằm sẵn trong resolver.
4. Không thêm truy vấn ngoài resolver (tối đa 3, nhớ trên user) và một truy vấn `groups.exists()` của `has_erp_access`. `has_perm`
   dùng `_perm_cache`, vốn đã nạp khi gọi `get_all_permissions()`.
5. Chỉ gồm mã và nhãn cố định của dự án. Không có cấu hình của nhóm khác, không có số ngày cửa sổ, không có dữ liệu khách, không có giá vốn.

Bảng mặc định, đã chạy thật trên DB SQLite tạm trong RAM (`migrate` rồi phân giải, 10/10). FE dùng bảng này cho mock, QA dùng để đối chiếu:

| Nhóm | orders | invoices | deliveries | confirmation | returns | receipts | customers | audit_log |
|---|---|---|---|---|---|---|---|---|
| owner | all | all | all | all_pending | all | all | all | all |
| manager | all | all | all | all_pending | all | all | all | all |
| warehouse_staff | all | all | all | none | all | all | none | none |
| delivery_staff | assigned_deliveries | none | assigned | none | assigned_deliveries | none | assigned_deliveries | none |
| customer_service | assigned_or_confirmation | none | none | pending_or_called_recently | none | none | none | none |

Người kiêm nhiệm: mỗi cột lấy rank lớn nhất trong các nhóm, nhóm `none` không tính. `via_group` là nhóm cho giá trị đó; hoà thì lấy
nhóm đứng trước theo thứ tự vai.

### 6.1.4 Contract FE PV-13 và §2.7 (chữ hiển thị, đặt ở `shared/lib/messages.ts`)

**Mất quyền giữa chừng.** Điều kiện duy nhất: màn **đã có dữ liệu** của mục, rồi một lần tải lại trả `ApiError` với `status === 404`.
"Tải lại" gồm nút "Tải lại", "Thử lại" ở dải mất mạng, lần tải lại tự động sau một thao tác, và thao tác (Lưu, Gửi, đổi trạng thái…)
trả 404 rồi gọi tải lại.
- Tải **lần đầu** bị 404 thì giữ `NotFoundScreen` như cũ. FE không phân biệt được "không tồn tại" với "ngoài phạm vi", và BE cố ý
  không cho phân biệt (§1.5: 404 không lộ là mục có tồn tại). Giữ như vậy cũng giữ được ED-19-AC6 (NV giao mở phiếu của người khác
  thì thấy "Không tìm thấy"). Hệ quả: nhấn F5 của trình duyệt thì thấy "Không tìm thấy trang này". FE không lưu id đã xem vào storage.
- 403 thì giữ `NoPermission` như cũ. 500 và lỗi mạng thì giữ hành vi cũ (AC4).
- Áp cho 7 màn chi tiết: `OrderDetailScreen`, `RefundDetailScreen` (phiếu hoàn tiền có phạm vi D1, D-5), `DeliveryDetailScreen`,
  `ReturnDetailScreen`, `CustomerDetailScreen`, `ConfirmationDetailScreen`, `ReceiptDetailScreen`. Hoá đơn bán không có màn chi tiết,
  nên chỉ áp AC3 cho danh sách. `PaymentDetailScreen` dùng chung `useDetail` nên cũng nhận hành vi mới; không sao, vì khoản tiền
  không bị xoá nên 404 sau khi đã xem chỉ có thể là do mất quyền.
- Khi vào `scope_lost`: `data = null`. Không vẽ phần nào của mục cũ. Không gọi tiếp các request phụ (guidance, timeline). Không `console.*`.

| Khoá `MSG` | Chữ |
|---|---|
| `scopeLostTitle` | `Bạn không còn quyền xem mục này.` (đúng nguyên văn AC1) |
| `scopeLostHint` | `Phạm vi dữ liệu của bạn vừa được thu hẹp. Nếu vẫn cần mục này, nhờ Quản lý hoặc Chủ vựa.` |
| `scopeLostOwnReceiptEarlierDay` | `Phiếu tạo từ hôm trước. Nhờ Quản lý xử lý tiếp.` (đúng nguyên văn AC2) |
| `backToList` | `Về danh sách` |
| `personalDataHidden` (đã có) | `Đã ẩn (quá 7 ngày)`: lý do `"expired"`, hoặc `null` không kèm lý do (phiếu giao, khách, gọi xác nhận) |
| `personalDataNotPermitted` (mới) | `Đã ẩn (không có quyền xem thông tin khách)`: lý do `"not_permitted"` |

- Component màn: `ScopeLostInApp({ listHref, extra })` đặt trong `features/auth/components/AppStates.tsx`, cạnh `NotFoundInApp`.
  Dùng lại class `page-state` / `state-title` / `page-state-actions` và `Icon`. **Không** sửa `shared/ui/**`. Nút "Về danh sách" trỏ về
  đường "quay lại" mà màn đang dùng (`/orders/`, `/orders/refunds/`, `/purchasing/`…). NV giao ở màn phiếu giao thì về `homePath(me)`.
  Tiêu đề dùng `<h2>` và đặt `role="alert"` để trình đọc màn hình đọc lên. **Sửa 10/10 (review Lô 7, L1):** `role` đặt trên khối bọc (`div.page-state`), không đặt trên `<h2>`, vì `role="alert"` ghi đè vai heading. Thêm `tabIndex={-1}` cho `<h2>` và chuyển focus vào đó khi màn hiện, vì nút vừa bấm ("Tải lại") đã bị gỡ khỏi DOM.
- AC2: thêm câu `scopeLostOwnReceiptEarlierDay` khi dữ liệu **vừa có** cho thấy `row.created_by === me.id` **và** ngày tạo theo giờ VN
  nhỏ hơn `todayInVietnam()`. Viết thành hàm thuần (vd `isOwnReceiptFromEarlierDay(row, meId, now)`) để test được mốc 23:50 / 00:10.
  Không cần đọc D6 từ `me`, vì `me` có thể cũ hơn cấu hình.
- Hook: `orders/useDetail.ts`, `customers/useCustomerDetail.ts`, `returns/useReturnDetail.ts` thêm `DetailStatus` `"scope_lost"`. Ba
  màn còn lại đang tự tải, thì thêm `k: "scope_lost"` vào kiểu `Load` của mỗi màn. Màn phiếu nhập phải giữ `created_by`/`created_at`
  của bản trước để xét AC2, rồi mới xoá dữ liệu.
- `shared/lib/usePagedList.ts::loadMore`: 404 thì chạy `loadFirst(true)`, không đặt `moreError`.

**§2.7 ô khách theo lý do**:
- `shared/lib/personalData.ts`: thêm `export type CustomerHiddenReason = "expired" | "not_permitted"` và tham số thứ ba
  `personalText(value, whenEmpty, reason?)`. `null` kèm `"not_permitted"` → `personalDataNotPermitted`, còn lại như cũ.
- `PersonalText` (`shared/ui`) **không** sửa. Ở 4 chỗ có lý do (danh sách đơn, chi tiết đơn với 3 ô tên/SĐT/địa chỉ, chi tiết phiếu
  hoàn tiền, danh sách hoá đơn bán), vẽ `<span className="muted">{personalText(null, "—", reason)}</span>` khi giá trị `null`.
- Kiểu dữ liệu: thêm `customer_hidden_reason?: CustomerHiddenReason | null` vào `OrderListItem`, `OrderDetail`, `RefundQueueItem`,
  `SalesInvoiceRow`. Đổi `RefundQueueItem.customer_name/customer_phone` thành `string | null` (optional).
- `SalesInvoiceListScreen.tsx:78`: cột Khách mở theo `PERM.viewOrderCustomerInfo = "sales.view_order_customer_info"` (thêm vào
  `shared/lib/nav.ts`), thay cho `viewCustomerList`.
- Mock (`features/orders/mock.ts`, `features/accounting/mock.ts`) trả lý do giống BE: người xem không có V2 thì `not_permitted`
  (đứng trước), NV giao xem đơn quá cửa sổ thì `expired`.

**PV-14 FE** (`AccountScreen.tsx`, khối mới đặt sau "Việc bạn được làm"):
- `features/auth/types.ts`: `DataScopeRow = {key; label; value; value_label; via_group: string | null}`, `Me.data_scopes?: DataScopeRow[]`.
- Tiêu đề `Dữ liệu bạn xem được`. Câu dẫn: `Phạm vi do Chủ vựa đặt cho nhóm của bạn. Chỉ để xem, không đổi ở đây.`
- Mỗi dòng có `label`, `value_label` và chữ phụ. Chữ phụ:
  - `via_group` khác null → `theo nhóm {nhãn trong group_labels}`.
  - `via_group` null, giá trị khác `none`, người dùng không phải superuser → `theo quyền gán riêng`.
  - `none` → chữ mờ, không có chữ phụ.
- `me.is_superuser` → thêm một dòng ghi chú `Toàn bộ (quản trị hệ thống)` trên danh sách (02c §G.3).
- Không có `data_scopes` (BE cũ) → `Chưa có thông tin phạm vi dữ liệu.`
- Dùng danh sách định nghĩa hoặc bảng có tiêu đề cột. Ở bề rộng 375px không cuộn ngang. Không có nút hay ô nhập nào.
- `features/auth/mock.ts`: dựng `data_scopes` từ nhóm của người dùng mock theo bảng §6.1.3 (rộng nhất, hoà thì giữ nhóm đứng trước;
  không nhóm thì toàn `none`; superuser thì rộng nhất với `via_group` null). Chép bảng vào `auth/mock.ts`, không import
  `features/permissions`.

### 6.1.5 File được sửa / không được đụng

**BE** (nhánh `feat/pv7-be` tách từ `feat/pv6-cum`):

| Được sửa | Ghi chú |
|---|---|
| `backend/apps/accounts/data_scopes/services.py` | thêm `describe_own_data_scopes`, bảng chữ D2 |
| `backend/apps/accounts/auth/services.py` | `describe_user` thêm `"data_scopes"` (chỉ thêm khoá) |
| `backend/apps/accounts/auth/tests/test_me_data_scopes.py` (mới) | §6.1.6 |
| `backend/apps/accounts/auth/tests/test_s6_me.py`, `test_s47_me_labels.py` | chỉ thêm `"data_scopes"` vào tập khoá |
| `backend/apps/accounts/data_scopes/README.md`, `backend/apps/accounts/auth/README.md` | một dòng mỗi file |

BE **không được đụng**: `erp-console/**`, `frontend/**`, `adapter/**`, mọi `migrations/**` (Lô 7 không có migration),
`accounts/data_scopes/{catalog,resolver}.py`, `data_scopes/tests/scope_snapshot_baseline.json`, mọi `scope.py`
(`sales/orders`, `sales/customers`, `delivery`, `delivery/confirmation`, `inventory/returns`, `purchasing/receipts`),
`delivery/serializers.py` (L3 không làm), `sales/**/serializers.py`, `accounts/capabilities/**`, `accounts/auth/authentication.py`,
`ai/**`, `config/**`, `doc/decisions.md`, `scripts/naming_baseline.json`.

**FE** (nhánh `feat/pv7-fe`, chạy song song, mock theo §6.1.3):

| Được sửa | Ghi chú |
|---|---|
| `erp-console/features/auth/{types.ts, mock.ts}`, `features/auth/components/{AccountScreen.tsx, account.module.css, AppStates.tsx}` | PV-14, `ScopeLostInApp` |
| `erp-console/shared/lib/{messages.ts, personalData.ts, usePagedList.ts, nav.ts}` | `nav.ts` chỉ thêm hằng `PERM.viewOrderCustomerInfo` |
| `erp-console/features/orders/{useDetail.ts, DetailGate.tsx, types.ts, mock.ts}`, `features/orders/components/{OrderDetailScreen, OrdersScreen, RefundDetailScreen, RefundQueueScreen}.tsx` | |
| `erp-console/features/accounting/{types.ts, mock.ts}`, `features/accounting/components/SalesInvoiceListScreen.tsx` | |
| `erp-console/features/deliveries/components/DeliveryDetailScreen.tsx` | |
| `erp-console/features/returns/useReturnDetail.ts`, `features/returns/components/ReturnDetailScreen.tsx` | |
| `erp-console/features/customers/useCustomerDetail.ts`, `features/customers/components/CustomerDetailScreen.tsx` | |
| `erp-console/features/confirmation/components/ConfirmationDetailScreen.tsx` | chỉ tải chính; 404 của lịch sử giữ nghĩa cũ |
| `erp-console/features/purchasing/components/ReceiptDetailScreen.tsx` (+ hàm thuần AC2, vd `features/purchasing/receiptScope.ts`) | |
| test vitest đặt cạnh file (`*.test.ts`), `README.md` của module đã sửa | |
| `erp-console/e2e/data_scope_loss_account.py` (mới) | §6.1.6. Tên không chứa mã lô |

FE **không được đụng**: `backend/**`, `erp-console/shared/ui/**` (gồm `PersonalText.tsx`, `states/*`), `erp-console/features/ai/**`,
`features/permissions/**` (đã xong ở Lô 6), `features/{overview,audit}/**`, `erp-console/app/**` (không thêm route), các kịch bản
e2e cũ, `package.json`/`package-lock.json`, `shared/lib/personalData.ts::hasLimitedCourierScope` (chỉ mock dùng; giữ nguyên).

Ước lượng: BE nhỏ (khoảng 60 dòng code và 150 dòng test, nửa ngày). FE vừa (7 màn chi tiết, 3 hook, 1 khối mới, 4 chỗ ô khách,
mock và e2e; 1 đến 1,5 ngày). Không cần mock contract mới cho FE ngoài `auth/mock.ts`, vì `customer_hidden_reason` BE đã trả từ Lô 3.

### 6.1.6 Test bắt buộc

**BE** (`test_me_data_scopes.py`; dùng token thật như `test_no_role_gate.py`, vì `force_authenticate` bỏ qua cổng D-3):
1. AC1: người K+G → `orders` = `all` / `warehouse_staff`; `customers` = `assigned_deliveries` / `delivery_staff`; `invoices` = `all` / `warehouse_staff`.
2. AC2: `nogroup` có quyền gán riêng `sales.view_salesorder` → `/me` 200, cả 8 dòng `none`, `via_group` null. Cùng token gọi
   `/api/sales/orders/` bị 403 `AUTH_NO_ROLE` (hai đường khớp nhau).
3. AC3: NV giao có `invoices`, `receipts`, `audit_log`, `confirmation` = `none`. Mỗi dòng đúng 5 khoá. Thứ tự key đúng D1…D8.
4. Bảng §6.1.3 cho 5 nhóm đơn, superuser không nhóm (rộng nhất, `null`), Chủ (`owner`).
5. **Nhất quán với hàm phạm vi** (chống lệch kiểu R2): với mỗi người trong fixture (5 nhóm, K+G, K+C, superuser), dòng nào khác
   `none` thì `value` phải bằng hàm mà view dùng: `orders_scope_value`, `resolve_data_scope(user, "invoices")`,
   `deliveries_scope_value`, `confirmation_scope_value`, `returns_scope_value`, `receipts_scope_value`, `customers_scope_value`.
6. Trần D7: NV giao, Chủ PUT D7 = `all` khi việc "Xem khách hàng" vẫn tắt → `/me` vẫn `assigned_deliveries`.
7. Quyền gán riêng trong nhóm không đủ điều kiện: NV kho được gán riêng `delivery.confirm_with_customer` → `confirmation` = `none`
   (giống `confirmation_scope_value`, không mở dữ liệu khách).
8. BR-PQ-36: Chủ PUT `receipts` của `warehouse_staff` = `created_by_me_today` → request `/me` kế tiếp của NV kho thấy giá trị mới.
9. AC6: tập khoá cũ giữ nguyên, kiểu không đổi (sửa 2 test set-equality).
10. Không rò: thân `/me` không có `purchase_rate`, `landed_unit_cost`, `unit_cost`, không có tên/SĐT/địa chỉ khách giả của fixture,
    không có `CONFIRMATION_PII_RECENT_DAYS` hay giá trị cấu hình của nhóm mà người đó không thuộc.
11. Truy vấn: `assertNumQueries` cho `/me` của NV kho tăng tối đa 3 so với số gốc. Be-dev đo số gốc trước khi sửa và ghi vào 03-dev-notes.
12. AC5: chạy lại `test_pv02_ac9_permissions_unchanged_for_reading` (đã có).

**FE vitest**:
- `useDetail` (và 2 hook cùng kiểu): đang `ok`, tải lại bị 404 → `scope_lost` và `data === null`. Tải lần đầu bị 404 → `notfound`.
  Tải lại bị 500 → giữ `ok` và `error` khác null. Tải lại bị 403 → giữ hành vi cũ.
- `usePagedList.loadMore` bị 404 → gọi lại trang 1, `moreError` null, `rows` theo kết quả mới.
- `personalText` với 3 lý do. `isOwnReceiptFromEarlierDay` với mốc 23:50 hôm trước, 00:10 hôm nay theo giờ VN, và phiếu của người khác.
- Hàm dựng dòng của khối PV-14: có `none`, có `via_group` null với quyền gán riêng, có superuser, thiếu `data_scopes`.
- Lệnh: `./node_modules/.bin/tsc --noEmit`, `npm run build`, `npx vitest run`, `python3 scripts/check_naming.py`.

**QA**: e2e trên BE thật với `seed_qa`. Không PASS bằng đọc code. `npm ci` sạch. Dữ liệu giả.

Dựng: `DJANGO_DEBUG=1 DATABASE_URL=sqlite:////tmp/e2e.sqlite3`, `migrate`, `bootstrap_masterdata`, `QA_PASSWORD=… seed_qa`.
Để có "phiếu tạo hôm qua" cho AC2, chỉ trên DB e2e tạm, chạy:
`manage.py shell -c "from apps.purchasing.models import PurchaseReceipt as R; from django.utils import timezone as t; from datetime import timedelta as d; R.objects.filter(note='QA-RECEIPT-DRAFT').update(created_at=t.now()-d(days=1))"`
(Phiếu seed nhận diện bằng `note` = mã, xem `qa_fixture/build.py:520-536`; `created_at` là `auto_now_add` nên chỉ đổi được bằng `update`.) Đổi phạm vi bằng `qa_owner` gọi
`PUT /api/staff/groups/<code>/capabilities/` kèm `version`. Thu hẹp thì không cần xác nhận. Cuối kịch bản trả cấu hình về mặc định
(mở rộng lại thì gửi `confirm_customer_data_widening: true`) hoặc `seed_qa --reset` rồi seed lại.

| # | Ca | Mong đợi |
|---|---|---|
| 1 | PV-13-AC1: `qa_warehouse_courier` mở QA-RECEIPT-DRAFT (do `qa_warehouse` tạo); Chủ đặt `receipts` của `warehouse_staff` = `created_by_me`; bấm "Tải lại" | "Bạn không còn quyền xem mục này." + nút "Về danh sách" → `/purchasing/`; **không** có câu AC2 |
| 2 | PV-13-AC2: `qa_warehouse` mở phiếu của mình (đã lùi về hôm qua); Chủ đặt `created_by_me_today`; "Tải lại" | có thêm "Phiếu tạo từ hôm trước. Nhờ Quản lý xử lý tiếp." |
| 3 | AC1 trên thao tác: như ca 2 nhưng bấm "Gửi ghi nhận" thay cho "Tải lại" | BE 404 → màn mất quyền, không có toast lỗi đỏ, không trắng trang |
| 4 | AC1 và AC5 trên đơn: `qa_warehouse` mở chi tiết một đơn **không** gán phiếu cho mình; Chủ đặt `orders` của `warehouse_staff` = `assigned_deliveries`; "Tải lại" | màn mất quyền. `document.body.innerText` **không** chứa tên/SĐT/địa chỉ của khách QA (lấy từ manifest `customers`). Nghe `page.on("console")`: không dòng nào chứa các chuỗi đó |
| 5 | AC1 trên phiếu giao, khách, gọi xác nhận, hàng hoàn, phiếu hoàn tiền (thu hẹp đối tượng tương ứng; mỗi màn ít nhất 1 ca) | như ca 4 |
| 6 | Ngoài đường thuận: `qa_courier1` mở thẳng bằng URL phiếu giao của `qa_courier2` (lần đầu) | "Không tìm thấy trang này" (ED-19-AC6), **không** dùng câu mất quyền |
| 7 | PV-13-AC4: chặn `GET` chi tiết bằng `page.route` trả 500 rồi bấm "Tải lại" | báo lỗi chung như cũ, không có chữ "không còn quyền" |
| 8 | PV-13-AC3: đang mở danh sách đơn của `qa_warehouse`, thu hẹp D1, bấm làm mới | danh sách ngắn lại, không có hộp lỗi. (Nếu dữ liệu seed không đủ 2 trang thì ca "Tải thêm" kiểm bằng vitest, ghi rõ trong báo cáo) |
| 9 | PV-14-AC4: `qa_courier1` mở Tài khoản | khối "Dữ liệu bạn xem được" có 8 dòng: Đơn hàng "Đơn có phiếu giao gán cho tôi" theo nhóm "Nhân viên giao"; Hoá đơn bán "Không xem". Không có nút/ô nhập. 375px không cuộn ngang |
| 10 | PV-14-AC1 qua UI: `qa_warehouse_courier` | Đơn hàng "Tất cả đơn" theo nhóm "Nhân viên kho" |
| 11 | `qa_superuser` | có dòng "Toàn bộ (quản trị hệ thống)", mọi dòng rộng nhất |
| 12 | PV-14-AC2 và AC5 bằng API: `qa_nogroup` `GET /api/auth/me/` → 200, 8 dòng `none`; `qa_courier1` `GET /api/staff/groups/manager/` → 403 | đúng |
| 13 | BR-PQ-36: đổi D6 của `warehouse_staff` rồi `qa_warehouse` tải lại Tài khoản | dòng Phiếu nhập đổi theo (khi `me` được tải lại) |
| 14 | §2.7: Chủ tắt V2 của `warehouse_staff`; `qa_warehouse` mở chi tiết đơn và danh sách hoá đơn | chi tiết đơn ghi "Đã ẩn (không có quyền xem thông tin khách)"; cột Khách của hoá đơn **không hiện**. Bật lại V2 (có xác nhận) → hiện tên. `qa_courier1` mở đơn quá cửa sổ → "Đã ẩn (quá 7 ngày)" |
| 15 | Hồi quy: phiếu giao của NV giao bị quá cửa sổ vẫn "Đã ẩn (quá 7 ngày)"; NV kho (V2 tắt) mở phiếu giao thì **vẫn** thấy đủ tên/SĐT/địa chỉ (câu 7) | đúng |

### 6.1.7 Câu hỏi

**Không có câu 🔴.** Lô 7 không mở thêm dữ liệu khách và không đổi phân quyền. Các điểm đã tự chốt theo hướng an toàn:
- 🟢 L3 đóng, không thêm `customer_hidden_reason` cho phiếu giao (§6.1.1).
- 🟢 Người không nhóm thấy "Không xem" ở cả 8 dòng, thay cho "hẹp nhất" trong chữ PV-14-AC2 (§6.1.3 quy tắc 1, theo D-3).
- 🟡 (UX, PO có thể đổi) Câu "không còn quyền" chỉ hiện khi tải lại **trong app** sau khi đã xem. F5 hoặc mở link lần đầu vẫn là
  "Không tìm thấy trang này", vì BE cố ý không phân biệt hai trường hợp, và FE không lưu id đã xem vào storage.
- Ngoài Lô 7, ghi để điều phối viên nhớ: 🔴 Q1 của 02c-quyet-dinh-08-10 (in **SĐT đầy đủ** trên tem) chưa thấy câu trả lời trong
  `doc/decisions.md` 08/10 và 10/10. Mặc định vẫn che SĐT trên tem. Lô 7 không đụng tem.

## 7. Điểm dừng hỏi Duy

| # | Mức | Câu hỏi | Tech Lead đề xuất |
|---|---|---|---|
| D-1 | 🔴 | N1 (QA Lô 12): sau phát hành NV kho **vẫn** thấy tên/SĐT/địa chỉ trên đơn vì V2 bật mặc định (Q-4). Đóng N1 theo hướng "Chủ tự tắt V2 cho NV kho khi muốn"? V2 có bao gồm **địa chỉ** trên chi tiết đơn không? | Đóng N1 theo cấu hình, không đổi mặc định. V2 gồm tên, SĐT, địa chỉ trên đơn, hoá đơn, phiếu hoàn tiền |
| D-2 | 🟡 | Trước khi migrate production: điều phối viên chạy lệnh đếm (không dữ liệu cá nhân) quyền hiện tại của 5 nhóm để biết Chủ đã đổi gì qua B4 | Bắt buộc, ghi số vào 03-dev-notes |
| D-3 | 🟡 | Người dùng không nhóm có quyền gán trực tiếp: đếm trên production. Nếu > 0 thì hành vi của họ đổi (D6 hẹp lại, D7 `none`, D4 rank 0) | Duy chốt 08/10: chặn hẳn ở cổng xác thực (`AUTH_NO_ROLE`). Đếm trước deploy; > 0 thì báo Duy danh sách để xếp nhóm trước khi deploy |
| D-4 | 🟡 | W3i chuyển từ "bật là lưu ngay" sang bản nháp + nút "Lưu thay đổi" (W3h giữ bật ngay) | Đồng ý (story PV-11 đã ngầm đòi) |
| D-5 | 🟢 | Thêm phạm vi cho phiếu hoàn tiền và dashboard (cửa phụ, không đổi mặc định) | Làm, không cần hỏi trừ khi Duy phản đối |

**Duy chốt 06/10/2026:** D-1 theo đề xuất (giữ V2 bật mặc định, Chủ tự tắt cho NV kho; V2 gồm tên, SĐT, địa chỉ trên đơn,
hoá đơn, phiếu hoàn). D-4, D-5 theo đề xuất. D-2, D-3 điều phối viên chạy lệnh đếm trước khi migrate production.

## 8. Đề xuất cho `doc/decisions.md` (điều phối viên hỏi Duy, Tech Lead không sửa)

"03/10/2026 — Phạm vi dòng (Tầng 3) phân giải theo **nhóm đủ điều kiện** (nhóm có quyền xem đối tượng), lấy rộng nhất; khoá lạc
quan `row_version` cho mọi lần lưu của nhóm."

## 9. Review

- 06/10 Lô 1–2 BE: CHANGES REQUESTED (H1 luật D7), sau d50d082 **APPROVED**. Chi tiết ở `03b-review-techlead.md`.
- 07/10 Lô F1 FE (dd84536): **CHANGES REQUESTED** (M1 mock D7, M2 Hoàn tác mở rộng, M3 chặn chuyển trang). Chi tiết ở 03b. Sau a1b5b31 **APPROVED** (còn L10 cho Lô 6; giữ nhánh tới Lô 5 BE).
- 07/10 Lô 3 BE (`30bbc87`): **APPROVED**, kèm điều kiện C1 (D1 cho phiếu hoàn tiền và dashboard phải vào trước hoặc cùng Lô 5, chờ D-3) và C2. Lô 3 sửa thêm `ai/policy/rules.py`; migration sales là 0015/0016.
- 08/10 Lô 4 BE (`d861021`): **APPROVED-chờ-Duy**. M1 (tệp mốc dùng `PENDING_DUY_DIFFS` thay cho sinh lại mốc) và D-3 phải xong trước merge main. Lô 4 xoá sớm 4 hàm của `common/api.py`. V2 áp cho phiếu giao.
- 08/10 Lô 4 M1 + Lô 5 + C1 (`5fd4032`): **APPROVED-chờ-Duy**. Code đạt; chưa merge main khi `PENDING_DUY_DIFFS` còn mục (D-3). PO-Q1 chỉ kiểm khi yêu cầu đụng `view_customers`/`scopes.customers` (mock F1 theo BE).

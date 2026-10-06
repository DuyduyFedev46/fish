# Phạm vi dữ liệu cấu hình — Thiết kế kỹ thuật (02b)
> Tech Lead · 2026-10-03 · Nguồn: `01-analysis.md` (ĐÃ DUYỆT 02/10), `02-stories.md` PV-01..14 (ĐÃ DUYỆT 03/10).
>
> **ĐANG VIẾT — còn thiếu:** §5 danh sách test chi tiết theo từng AC (mới có khung), §6 danh sách file **không được đụng**
> của Lô 4–7 (mới có file được sửa), §9 mục Review (để trống, dùng sau). Phần §1–§4, §7, §8 đã chốt nội dung.
> Code đọc trên `main` @ 7137a8d.

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

Thân như PUT, không cần `version`/`confirm_…`; kiểm 1–7, 9, 10 như PUT; không ghi gì. Trả như story:
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
| R9 | Người không nhóm có quyền gán trực tiếp đổi hành vi (D6 hẹp lại, D7 thành `none`, D4 từ "không gì" thành rank 0) | Trung bình | PV-02-AC4 đã duyệt; kiểm đếm trên production trước deploy | điểm dừng D-3 |
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

## 7. Điểm dừng hỏi Duy

| # | Mức | Câu hỏi | Tech Lead đề xuất |
|---|---|---|---|
| D-1 | 🔴 | N1 (QA Lô 12): sau phát hành NV kho **vẫn** thấy tên/SĐT/địa chỉ trên đơn vì V2 bật mặc định (Q-4). Đóng N1 theo hướng "Chủ tự tắt V2 cho NV kho khi muốn"? V2 có bao gồm **địa chỉ** trên chi tiết đơn không? | Đóng N1 theo cấu hình, không đổi mặc định. V2 gồm tên, SĐT, địa chỉ trên đơn, hoá đơn, phiếu hoàn tiền |
| D-2 | 🟡 | Trước khi migrate production: điều phối viên chạy lệnh đếm (không dữ liệu cá nhân) quyền hiện tại của 5 nhóm để biết Chủ đã đổi gì qua B4 | Bắt buộc, ghi số vào 03-dev-notes |
| D-3 | 🟡 | Người dùng không nhóm có quyền gán trực tiếp: đếm trên production. Nếu > 0 thì hành vi của họ đổi (D6 hẹp lại, D7 `none`, D4 rank 0) | Đếm trước deploy; > 0 thì hỏi Duy từng người |
| D-4 | 🟡 | W3i chuyển từ "bật là lưu ngay" sang bản nháp + nút "Lưu thay đổi" (W3h giữ bật ngay) | Đồng ý (story PV-11 đã ngầm đòi) |
| D-5 | 🟢 | Thêm phạm vi cho phiếu hoàn tiền và dashboard (cửa phụ, không đổi mặc định) | Làm, không cần hỏi trừ khi Duy phản đối |

**Duy chốt 06/10/2026:** D-1 theo đề xuất (giữ V2 bật mặc định, Chủ tự tắt cho NV kho; V2 gồm tên, SĐT, địa chỉ trên đơn,
hoá đơn, phiếu hoàn). D-4, D-5 theo đề xuất. D-2, D-3 điều phối viên chạy lệnh đếm trước khi migrate production.

## 8. Đề xuất cho `doc/decisions.md` (điều phối viên hỏi Duy, Tech Lead không sửa)

"03/10/2026 — Phạm vi dòng (Tầng 3) phân giải theo **nhóm đủ điều kiện** (nhóm có quyền xem đối tượng), lấy rộng nhất; khoá lạc
quan `row_version` cho mọi lần lưu của nhóm."

## 9. Review

- 06/10 Lô 1–2 BE: CHANGES REQUESTED (H1 luật D7), sau d50d082 **APPROVED**. Chi tiết ở `03b-review-techlead.md`.

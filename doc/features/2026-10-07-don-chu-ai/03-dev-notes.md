# Lô dọn chữ AI — ghi chú dev

## BE (be-dev, nhánh `feat/don-chu-ai-be`)

### File đã sửa/thêm (đúng danh sách 02b mục 4)
- MỚI `backend/apps/common/ai_visibility.py` — `ai_features_enabled()` (cờ env `AI_ENABLED`, không dùng công tắc tắt khẩn) và
  `exclude_ai_audit_rows(qs)` (thân hàm chuyển từ `exclude_ai_rows`).
- `apps/accounts/audit/serializers.py`: `exclude_ai_rows = exclude_ai_audit_rows` (giữ tên cũ, test TL-D3-L4 không đổi).
- `apps/accounts/auth/services.py` (`describe_user`): thêm `ai_features_enabled`, `capabilities` bỏ `ai.*` khi tắt.
- `apps/accounts/capabilities/registry.py`: `AI_CAPABILITY_KEYS`, `visible_capabilities()`, `visible_keys()`.
  `services.py`: `capability_states`, `describe_group.registry`, `_validate_changes`, `_capability_events`,
  `capability_change_label` dùng bản lọc. `CAPABILITIES`/`BY_KEY` giữ nguyên.
- Lọc dòng AI trước khi cắt `limit`: `common/guidance/audit_timeline.py`, `sales/orders/timeline.py`,
  `sales/payments/timeline.py`, `sales/refunds/timeline.py`, `inventory/batches/timeline.py`,
  `inventory/stocktake/services.py` (`_last_editor_name`), `inventory/stocktake/queries.py` (subquery `latest`),
  `inventory/stocktake/serializers.py` (nhánh AI trả "Hệ thống" khi cờ tắt).
- MỚI `apps/sales/orders/shop_labels.py` + `shop_api.py` dùng nó (W1, W2). Không đổi `choices`, không migration.

### Contract thực tế (khớp 02b, không đổi shape)
`GET /api/auth/me/` thêm `"ai_features_enabled": bool`; tắt thì `capabilities` không có `ai.manage_ai_policy`,
`permissions` giữ nguyên. Ma trận: tắt thì `registry`/`capabilities` không có `ai_policy`; `PUT {"ai_policy": ...}` -> 400
`INPUT_NOT_ALLOWED`, dữ liệu không đổi. Shop tra đơn: chỉ đổi chuỗi `status_label`, `delivery.status_label`.

### Test (cả hai nhánh cờ)
MỚI: `common/tests/test_ai_visibility.py`, `accounts/auth/tests/test_ai_features_flag.py`,
`accounts/capabilities/tests/test_ai_hidden.py`, `sales/orders/tests/test_ai_rows_hidden.py` (5 builder + Nhật ký +
limit sau lọc + khoá `step.ai=null`), `inventory/stocktake/tests/test_ai_rows_hidden.py`, `sales/orders/tests/test_shop_labels.py`.
Test cũ chuyển sang `override_settings(AI_ENABLED=True)` vì kiểm nhánh bật: `test_s47_me_labels` (1 ca),
`capabilities/test_api_read|test_api_write|test_requires` (3 class), `orders/test_guidance` (DW-03-AC4). Hai test key contract của `/me`
thêm `ai_features_enabled`.

### Chỗ lệch / điều cần biết
1. Nhãn phiếu giao CANCELLED ở Shop nay là "Đã huỷ" cho mọi ca (trước: "Đã huỷ theo đơn"), theo T30 đã duyệt.
2. "6 builder" ở 02b thực tế là 5 builder dòng thời gian (audit_timeline, order, payment, refund, batch) cộng
   `_last_editor_name` của kiểm kê; không có builder dòng thời gian riêng cho kiểm kê.
3. Dòng thời gian chi tiết đơn (`SalesOrderDetailSerializer.get_timeline`) không có `actor_kind`; test khoá bằng `build_timeline`.
4. Dòng nhật ký đổi quyền cũ có khoá `ai_policy` bị ẩn khi tắt (sự kiện chỉ chứa khoá AI bỏ hẳn; sự kiện lẫn thì chỉ tính khoá không AI).
5. Ca Shop labels viết cùng lúc với code (chưa chạy RED riêng); các ca còn lại đã kiểm RED bằng cách vô hiệu hoá bộ lọc.
6. Q1 (Duy): giữ nguyên dòng `ai_config_*`/`ai_policy_*` do Chủ đổi.

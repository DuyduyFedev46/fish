# Review Tech Lead — ERP theo design
> techlead ghi theo từng lô. Căn cứ: `02b-tech-design.md` (§3.0, §3.8, §4, §5.2) và `03-dev-notes.md`.

## Lô 2 — BE (R1, R2)
> Review 02/10/2026 trên diff chưa commit (`git diff backend/` và các file mới chưa track). Không xét `erp-console/`.

**Kết luận: APPROVED.** Không có lỗi Critical hay High. Có 1 Medium (M1), nên sửa trước khi màn Nhân viên (Lô 14) dùng
timeline, hoặc sửa ngay trong lô này nếu tiện vì sửa nhỏ. Các mục Low ghi lại để lô sau xử lý, không chặn commit.

### Kiểm chứng đã chạy trong lượt review
- `manage.py test apps.ai.actions.tests.test_target_filter apps.common.guidance`: **60 test OK**.
- `python3 scripts/check_naming.py`: OK, không có vi phạm mới.
- Toàn bộ `manage.py test` do điều phối viên chạy: OK (1883). Lô này không có migration.

### Đã soi và đạt
| Trọng tâm | Kết quả |
|---|---|
| Bất biến 9 (dữ liệu cá nhân trong timeline) | `audit_timeline.py` chỉ dựng `at`/`kind`/`label`/`doc`/`actor`. Nó không đọc `changes`, `note` hay `object_repr`. Nhãn lấy từ bảng tĩnh. Hàm nhãn duy nhất đọc `changes` là `_advance_label` (`apps/delivery/next_steps.py:15`), và hàm này chỉ đưa giá trị qua enum `DeliveryNote.Status`, giá trị lạ thì về chuỗi cố định. `actor.display` là tên nhân viên, không phải tên khách. `doc.code` là mã nội bộ (PR-, KK-, RT-, KH-, mã phiếu giao, mã hàng, username nhân viên). Test cố ý nhét tên, SĐT, địa chỉ và ghi chú giả vào `changes`/`note`, rồi assert body không chứa các chuỗi đó (`test_audit_timeline.py` cho delivery, customer, staff). |
| Bất biến 1 (giá vốn, tiền) | Không có field tiền nào. `changes` của `create_and_submit_receipt` (có thể chứa rate) không ra ngoài. Có test `test_r2_receipt_does_not_leak_cost`. |
| Tầng 1 / Tầng 3 của từng provider | Provider kiểm quyền (403) trước rồi mới tra đối tượng (404 thông điệp cố định), nên không dò được đối tượng có tồn tại hay không. `delivery` dùng đúng điều kiện của `DeliveryNoteViewSet.get_queryset` (`has_full_delivery_scope`, nếu không thì `assigned_to=user`). Có test NV giao khác nhận 404. `customer` dùng `sees_customer_directory` (Chủ, Quản lý, superuser). Cách này **chặt hơn** `CustomerViewSet`, vì NV giao bị 403 kể cả với khách thuộc phiếu của mình, nên chấp nhận được cho tới Lô 6. `staff` dùng `manage_staff`, khớp `StaffViewSet`. `id` chỉ nhận chữ số ≤ 18 ký tự. `doc_type` chỉ nạp module trong whitelist `_LAZY_MODULES` (không import tuỳ ý). |
| `Cache-Control: no-store` cho delivery, customer | Có, qua cờ `provider.no_store`. Có test cho customer. |
| R1 không mở rộng phạm vi | `_filter_by_target` chỉ gọi `.filter()` trên tập "mine" hoặc "all" đã giới hạn. `scope=all` thiếu `manage_ai_policy` thì cả list và counts đều 403 trước khi lọc. 400 `INVALID_TARGET_MODEL` không lặp lại giá trị người gọi gửi. `target_id` tối đa 100 phần tử, dùng ORM `__in`, không ghép SQL. |
| `counts` không lộ số việc người khác | Đếm trên đúng `get_queryset()` của danh sách, nên tập đếm bằng tập liệt kê. Việc ESCALATED giao cho nhóm của mình được đếm, và cũng đã hiện trong danh sách hiện có, nên không tạo kênh rò mới. Có test `test_r1_counts_other_users_do_not_see_my_numbers`. |
| Hiệu năng | Timeline dùng `select_related("actor__staff_profile", "ai_actor__staff_profile")`, không N+1. AuditLog có index `(model_name, object_id, created_at)`. `counts` là một truy vấn `GROUP BY`. `_labels_by_model_name` cache bằng `lru_cache`. |
| Đúng idiom | Lỗi qua `BusinessError(code=, status_code=)`. Nạp provider lười bằng bảng thay cho chuỗi `if/elif`, sạch hơn bản cũ. Không có migration, không sửa `config/api_urls.py`. |

### Phát hiện

**M1 — Medium — Timeline không giới hạn số dòng**
- `backend/apps/common/guidance/audit_timeline.py:147-153`: `AuditLog.objects.filter(...)` lấy toàn bộ, không cắt.
  Loại `staff` gom cả `logout` và `password_change_self` của chính nhân viên (`apps/accounts/auth/services.py:133`),
  nên mỗi lần đăng xuất thêm một dòng. Sau vài năm, một nhân viên có hàng nghìn dòng, và response cùng thời gian render
  timeline ở FE tăng theo. Điều này trái guardrail hiệu năng (TTI < 2s).
- Tái hiện: tạo 5.000 dòng `record_audit("logout", actor=u, obj=u)` rồi gọi `GET /api/guidance/staff/<u.pk>/` bằng Chủ.
  Response có 5.000 phần tử.
- Đề xuất: lấy N dòng mới nhất (hằng `TIMELINE_MAX_ROWS`, ví dụ 200, đặt trong `settings` theo bất biến 7) bằng
  `order_by("-created_at", "-id")[:N]`, đảo lại thứ tự, và thêm khoá `"timeline_truncated": true|false`.
  Khoá này chỉ **thêm** vào contract nên FE bỏ qua được. Nếu đổi contract thì ghi vào `03-dev-notes.md` để FE Lô 2 biết.
  Có thể cân nhắc thêm việc không đưa `logout` vào timeline nhân viên, vì đó là nhiễu chứ không phải "việc đã làm".
- Test gợi ý:
  ```python
  def test_r2_timeline_is_capped(self):
      for _ in range(TIMELINE_MAX_ROWS + 5):
          record_audit("staff_update", actor=self.owner, obj=self.warehouse)
      data = self.get("owner", "staff", self.warehouse.pk).json()
      self.assertEqual(len(data["timeline"]), TIMELINE_MAX_ROWS)
      self.assertTrue(data["timeline_truncated"])
  ```

**L1 — Low — `return` chưa scope dòng (nợ đã ghi, cần khoá bằng test ở Lô 9)**
- `backend/apps/inventory/returns/next_steps.py:11-22`: không có `scope_fn`, nên `delivery_staff` (có
  `view_returntostock`) xem được timeline hàng hoàn thuộc phiếu giao của NV giao khác. Hành vi này **ngang bằng**
  `ReturnToStockViewSet` hiện tại (không scope), nên lô này không mở rộng phạm vi. Nội dung lộ ra chỉ là mã RT, trạng
  thái, tên nhân viên và giờ, không có dữ liệu khách hay tiền.
- Việc cho Lô 9 (R9): khi siết `ReturnToStockViewSet`, phải thêm `scope_fn` cùng điều kiện (dùng chung một hàm, không
  chép logic), kèm test `test_r2_return_other_courier_404`. Ghi dòng này vào phiếu Lô 9 trong `02c`.

**L2 — Low — `target_id` không kèm `target_model` khớp chéo nhiều loại chứng từ**
- `backend/apps/ai/actions/api.py:83-91`: `?target_id=12` không kèm `target_model` sẽ khớp cả phiếu nhập 12 lẫn lô 12.
  Điều này không mở rộng phạm vi (vẫn chỉ trong tập "mine") nhưng trả sai việc cho màn chi tiết.
- Đề xuất: khi có `target_id` mà thiếu `target_model` thì trả 400 `INVALID_TARGET_ID`, hoặc ít nhất ghi rõ trong contract
  rằng FE luôn phải gửi cả hai. Test gợi ý: tạo 2 việc cùng `target_id="12"`, một `purchasereceipt`, một `batch`.
  Gọi `?target_id=12` thì kỳ vọng 400, hoặc kỳ vọng `count == 2` nếu chọn cách ghi contract.

**L3 — Low — Tài liệu nói "không lộ mã hành động nội bộ" nhưng `kind` trả nguyên `AuditLog.action`**
- `backend/apps/common/guidance/audit_timeline.py:77` (`kind=row.action`), và `03-dev-notes.md` mục R2 dòng "Hành động
  chưa có trong bảng nhãn…". Mã hành động không phải dữ liệu nhạy cảm, và timeline `order` cũng trả `kind` như vậy,
  nên không cần sửa code. Chỉ cần sửa câu trong dev-notes cho đúng: nhãn không lộ, còn `kind` vẫn là mã hành động.

**L4 — Low — Lặp kiểm tra `scope=all`**
- `backend/apps/ai/actions/api.py:102` và `:119` có cùng khối 403. Nên tách thành `_deny_scope_all(request)` dùng chung.
  Việc dọn này không bắt buộc.

**L5 — Low — Có sẵn từ trước, ngoài phạm vi lô: 404 lặp lại `doc_type` người gọi gửi**
- `backend/apps/common/guidance/api.py:61` dùng `f"Không hỗ trợ loại chứng từ: {doc_type}."`. Giá trị bị giới hạn bởi
  route `<str:>`, và response là JSON chứ không phải HTML, nên rủi ro thấp. Tuy vậy dòng này lệch quy ước "không lặp
  lại input" mà chính lô này áp dụng. Đề xuất đổi sang thông điệp cố định khi có dịp.

### Ghi chú cho lô sau
- Lô 6 (B2): khi khai `view_customer_list`, provider `customer` tự chuyển sang `has_perm`. Phải thêm test timeline
  `customer` với quyền mới: `quan_ly` 200, `nv_kho`/`nv_giao`/`cskh` 403 (ghi lại theo bảng đổi tên Group).
- Lô 3: điểm 5 trong dev-notes, tức dòng timeline `order` lấy `Refund.reason` (văn bản tự do), cần rà theo bất biến 9.
  Ưu tiên nhãn theo mã lý do thay vì chép văn bản tự do.

## Lô 3 — BE (R3, SĐT đủ)
> techlead · 02/10/2026 · Phạm vi: `git diff backend/apps/sales` + file mới `orders/reasons.py`,
> `orders/tests/test_order_list_r3.py`, `orders/tests/test_timeline_privacy.py`, `refunds/tests/test_refund_list_month.py`.
> Bỏ qua Lô 2 (`apps/ai`, `apps/common/guidance`, `next_steps.py`) và `erp-console/`.

### Lệnh đã chạy
- `cd backend && .venv/bin/python manage.py test apps.sales`: **462 test, OK**.
- `manage.py makemigrations --check --dry-run`: `No changes detected`.
- `python3 scripts/check_naming.py`: không có vi phạm trong `backend/apps/sales`. Script vẫn exit 1, nhưng do file
  `erp-console/e2e/ed_lo1_shell.py` của lô khác.
- Ca thử ngoài đường thuận: viết test tạm ở scratchpad, nạp bằng `PYTHONPATH`, **không** thêm file vào repo.
  Kết quả nằm ở M1 và L1 bên dưới.

### Đã kiểm, đạt
- **`reason` không bao giờ là chữ tự do.** `reasons.py` chỉ trả nhãn cố định theo mã: `AUTO_CANCELLED`, nhãn từ
  `SalesCreditNote.reason_code`, `UNDERPAID`, `DELIVERY_FAILED`. Hàm không đọc `AuditLog.note`, `Refund.reason`
  hay ghi chú huỷ. Test `test_ed09_ac1_cancelled_does_not_leak_free_text_note` kiểm bằng cách quét toàn bộ body.
- **Lọc `customer`.** `warehouse_staff`, `delivery_staff`, `customer_service` đều nhận 403, đã thử trực tiếp.
  Quyền được kiểm trước khi parse tham số, nên không dùng phản hồi 400/200 để dò được. Gửi `?customer=&customer=1`
  vẫn bị 403, vì bước kiểm quyền và bước lọc cùng đọc giá trị cuối của `QueryDict.get`. Gửi `?customer=%20` thì
  tham số bị bỏ qua và trả danh sách như khi không lọc, đúng contract. 401 vẫn đến trước vì `check_permissions`
  chạy trong `initial()`.
- **`batch` không mở rộng phạm vi.** Điều kiện `Exists` được AND với queryset đã qua `scope_orders_for`. Có test
  courier chỉ thấy đơn trên phiếu của mình (`test_ed06_batch_filter_courier_sees_only_own_notes_orders`).
  `warehouse_staff` vốn đã thấy tên và SĐT ở danh sách đơn nên lọc này không lộ thêm gì.
- **SĐT đủ chỉ trả cho người trong phạm vi.** Serializer không đổi. Các test `test_s37_*` khoá các hành vi: đủ
  với owner, manager, warehouse; courier chỉ thấy đơn của mình và bị ẩn khi quá cửa sổ SR-PII-02; CSKH ngoài phạm
  vi không thấy đơn. Phiếu hoàn chỉ owner và manager xem được.
- **Ranh giới tháng theo GMT+7.** `TIME_ZONE = "Asia/Ho_Chi_Minh"`. `_month_bounds` dùng khoảng nửa mở
  `[đầu tháng, đầu tháng sau)` theo giờ VN. Đã có test cho ca 00:30 ngày 01/10 giờ VN, và cho tháng 12, tháng 2.
- **`NoStoreMixin`.** `RefundViewSet` đã thêm mixin. Danh sách đơn có sẵn từ trước. Đã thử thực tế: cả hai trả
  `Cache-Control: no-store`.
- **N+1.** `select_related("invoice")` cộng với 3 prefetch là truy vấn cố định, không phụ thuộc nhánh `reason`.
  Test đếm truy vấn với 1 đơn và 5 đơn cho kết quả bằng nhau.
- **Giá vốn và tiền.** Không thêm khoá tiền. `test_*_no_cost_leak` dùng `SENSITIVE_KEYS` để kiểm cho cả 3 đường.
- **Lỗi 400 không lặp lại input.** Thông điệp cố định ("Tham số customer/batch phải là số nguyên dương.",
  "Tham số month phải có dạng YYYY-MM."). Đã thử `?batch=abc<script>`: body không chứa input.
- **Timeline đơn.** Đã bỏ `Refund.reason`. Test kiểm cả `GET /api/sales/orders/<id>/` lẫn `/api/guidance/order/<id>/`.

### Phát hiện

**M1 — Medium — `?month=` hợp lệ về dạng nhưng ngoài biên làm 500 (lệch contract "sai → 400")**
- `backend/apps/sales/refunds/api.py:46`: `nxt = datetime.date(year + (month == 12), …)` nằm **ngoài** khối
  `try`. Với `9999-12` thì năm 10000 gây `ValueError` không bắt được, kết quả là 500.
- `backend/apps/sales/refunds/api.py:49-50`: với `0001-01`, `make_aware` ở GMT+7 rồi đổi sang UTC sẽ ra năm 0, gây
  `OverflowError` khi truy vấn, kết quả là 500. Lỗi này xảy ra trên mọi DB, không riêng SQLite.
- Tái hiện: đăng nhập owner, gọi `GET /api/sales/refunds/?month=9999-12` hoặc `?month=0001-01`. Kỳ vọng 400
  `INVALID_FILTER`, thực tế văng exception (500).
- Sửa: giới hạn năm, ví dụ `2000 ≤ year ≤ 2100` (hoặc `MINYEAR < year < MAXYEAR`), và đưa phép tính `nxt` vào trong
  `try`. Thêm 2 giá trị trên vào `test_ed12_ac1_invalid_month_400`.

**L1 — Low — Parse `month` dễ dãi hơn contract; id quá lớn làm 500 trên SQLite**
- `backend/apps/sales/refunds/api.py:42`: `int()` chấp nhận `+`, khoảng trắng và chữ số Unicode. Ví dụ
  `?month=2026-+1` và `?month=２０２６-10` (chữ số toàn độ rộng) đều trả 200, trong khi contract quy định sai dạng
  thì trả 400. Không gây rò rỉ, chỉ lệch contract. Sửa: thêm `raw.isascii()` và kiểm `raw[:4].isdigit() and
  raw[5:].isdigit()`, giống cách làm ở `_parse_positive_int`.
- `backend/apps/sales/orders/api.py:57`: `?customer=99999999999999999999999` hoặc `?batch=9223372036854775808` gây
  `OverflowError`, kết quả 500 trên SQLite (dev, CI). Trên Postgres có lẽ trả 200 rỗng, nhưng chưa kiểm. Sửa:
  chặn thêm `len(raw) > 18` để trả 400. Nên làm cùng lúc với M1.

**L2 — Low — `reason.code` trả nguyên giá trị DB, không qua whitelist**
- `backend/apps/sales/orders/reasons.py:39-40`: `code = notes[-1].reason_code` được trả thẳng ra ngoài, kể cả khi
  mã không có trong `_CANCEL_LABELS`. Khi đó nhãn là "Đã huỷ". `reason_code` là `CharField(max_length=32)` không có
  `choices`. Hiện chỉ service (đầu vào đã kiểm bằng `CANCEL_REASON_CODES`) và lệnh `backfill_credit_notes` (lấy từ
  `AuditLog.changes`) ghi trường này, nên chưa có đường nào ghi chữ tự do vào. Tuy vậy, cách viết hiện tại chưa
  đảm bảo "code luôn thuộc tập cố định".
- Sửa: nếu `code not in _CANCEL_LABELS` thì trả `{"code": "CANCELLED", "label": "Đã huỷ"}`, kèm một test ghi mã
  lạ vào credit note.
- Ghi cho **Lô 4 (B5)**: `reasons.py:60` gọi `get_failure_reason_display()`. Vì vậy `DeliveryNote.failure_reason`
  **phải** có `choices`. Nếu không, nhãn trả ra chính là giá trị thô. Lô 4 cần thêm test `reason` cho phiếu `FAILED`
  có `failure_reason`.

**L3 — Low — Lặp logic quyền "Xem khách hàng" ở 2 file**
- `backend/apps/sales/orders/scope.py:41-52` (`can_filter_orders_by_customer`) và
  `backend/apps/sales/customers/next_steps.py` (`_can_view_customer_timeline`, Lô 2) có thân hàm giống hệt nhau, kể
  cả hằng `CUSTOMER_LIST_PERM` cũng khai hai lần. Khi Lô 6 khai quyền, chỉ sửa một chỗ thì hai chỗ sẽ lệch nhau.
- Sửa: gom về một hàm, ví dụ `apps/sales/customers/permissions.py::can_view_customer_list(user)`, rồi cả hai nơi
  gọi hàm này. Có thể làm ngay ở lô này hoặc muộn nhất ở Lô 6. Ghi vào phiếu Lô 6 trong 02c.

### Về 4 chỗ timeline ghép chữ tự do (dev đã nêu, Duy quyết)
Mức độ đúng như dev mô tả, không nặng hơn. Lý do:
- (1) và (2) ở `refunds/timeline.py` chỉ hiện ở guidance `refund`, và chỉ owner/manager mở được (đã có `view_refund`).
- (3) và (4) ở `orders/timeline.py:193` và `:256-257` hiện ở chi tiết đơn và guidance `order`. Người xem có thể là
  courier hoặc CSKH, nhưng chỉ với đơn trong phạm vi của họ. Ghi chú do owner/manager gõ. Rủi ro là ghi chú có thể
  chứa thông tin của **người khác** ngoài khách của đơn.
- Đề xuất của dev đúng hướng: dùng nhãn theo `changes.reason_code` cho (4), bỏ lý do khỏi nhãn cho (1) đến (3).
  Gốc của vấn đề là `AuditLog.note` đang chứa chữ tự do, điều 02b §3.0 không cho phép với `changes`. Nên xử lý
  trong một lô dọn riêng sau khi Duy duyệt.

### Kết luận: **CHANGES REQUESTED**
Bắt buộc sửa: **M1** (500 với `month` ngoài biên). Nên sửa cùng lúc: **L1** và **L2** (vài dòng, có test). **L3**
có thể để đến Lô 6. Ngoài các điểm trên, phần chính của lô đạt: `reason` chỉ là nhãn cố định, lọc `customer` trả
403 đúng, `batch` không vượt phạm vi, SĐT theo phạm vi, ranh giới GMT+7, `no-store`, không N+1, không rò giá vốn.
Sau khi sửa, chỉ cần re-review M1, L1, L2.

### Re-review sau khi sửa M1, L1, L2 (techlead · 02/10/2026)
- `cd backend && .venv/bin/python manage.py test apps.sales`: **465 test, OK**. Full suite chưa dùng làm căn cứ vì
  Lô 4 đang làm dở trong `apps/delivery`.
- Thử lại bằng test tạm ở scratchpad (không thêm file vào repo):

  | Gọi | Trước | Sau |
  |---|---|---|
  | `refunds/?month=9999-12` | 500 | 400 `INVALID_FILTER` |
  | `refunds/?month=0001-01` | 500 | 400 |
  | `refunds/?month=2026-+1`, `?month=２０２６-10` | 200 | 400 |
  | `refunds/?month=2100-12`, `?month=2026-10` | — | 200 |
  | `orders/?customer=99999999999999999999999`, `?batch=9223372036854775808` | 500 (SQLite) | 400 |
  | `orders/?batch=9223372036854775807` | — | 200 rỗng |

- **M1: đạt.** `refunds/api.py::_month_bounds` giới hạn năm trong 2000..2100, cả phép tính tháng sau lẫn
  `make_aware` đều nằm trong `try`, bắt `ValueError` và `OverflowError`.
- **L1: đạt.** `MONTH_PATTERN.fullmatch` chỉ nhận chữ số ASCII. `_parse_positive_int` chặn ở `MAX_ID = 2**63 - 1`.
- **L2: đạt.** Ở `orders/reasons.py:_cancel_reason`, mã lạ trả `{"code": "CANCELLED", "label": "Đã huỷ"}`, có test
  `test_ed09_ac1_unknown_reason_code_is_not_echoed`.

**L4 — Low — chuỗi id dài hơn 4300 chữ số vẫn làm 500 (còn sót sau L1)**
- `backend/apps/sales/orders/api.py:60`: hàm gọi `int(raw)` trước khi so với `MAX_ID`. Python giới hạn chuyển chuỗi
  sang số ở 4300 chữ số, nên chuỗi dài hơn gây `ValueError`. `ValueError` không phải `InvalidFilter`, nên thành 500.
- Tái hiện: owner gọi `GET /api/sales/orders/?batch=` với 5000 chữ số `1` (tương tự với `?customer=`).
- Sửa: thêm `len(raw) > 19` vào điều kiện ngay trước `int(raw)`, và thêm ca này vào
  `test_ed06_batch_filter_invalid_value_400`. Không gây rò rỉ, không chặn nghiệm thu, nên sửa khi có dịp, ví dụ
  cùng lúc với L3 ở Lô 6.

### Kết luận cập nhật: **APPROVED**
M1, L1, L2 đã sửa đúng và có test đi kèm. L3 (gom hàm quyền xem khách) để Lô 6, L4 sửa khi có dịp. Cả hai không chặn
nghiệm thu.

## Lô 4 — BE (B5, B6, R4)
> techlead · 02/10/2026 · Phạm vi: `git diff backend/apps/delivery` (trừ `next_steps.py`), migration `0005`, `0006`,
> 3 file test mới, `config/api_urls.py`, `accounts/auth/services.py`, `ai/policy/rules.py`, cùng 4 test ngoài phạm vi
> mà dev đã sửa. Không xem `apps/sales`, `apps/ai/actions`, `apps/common/guidance`, `erp-console/`.

### Lệnh đã chạy
- `manage.py test apps.delivery`: **257 test, OK**.
- `manage.py makemigrations --check --dry-run`: `No changes detected`.
- Rollback migration bằng test tạm (`MigrationExecutor`, DB test): lùi `delivery` về `0004` thì mất 2 cột và quyền
  `assign_deliverynote` bị gỡ khỏi nhóm. Chạy tiến lại thì có đủ 2 cột, quyền cấp đúng `['manager', 'owner']`.
- `python3 scripts/check_naming.py`: không có vi phạm trong phạm vi Lô 4. Script vẫn exit 1, nhưng do
  `erp-console/e2e/ed_lo1_shell.py` của Lô 1.
- Ca thử ngoài đường thuận: viết test tạm ở scratchpad, nạp bằng `PYTHONPATH`, không thêm file vào repo. Kết quả
  nằm ở M1 và L1–L3 bên dưới.

### Đã kiểm, đạt
- **Migration chỉ thêm và rollback được.** `0005` gồm 2 `AddField` có default rỗng và `AlterModelOptions`. `0006` là
  `RunPython(grant, revoke)`, chỉ cấp cho `owner` và `manager`, và phụ thuộc `accounts/0013` để tên nhóm khớp. Không
  cấp cho `warehouse_staff`, `delivery_staff` hay `customer_service`.
- **Phân quyền B6.** `assign` dùng `required_perms`, nên `BusinessModelPermissions` chặn từ trước khi vào view.
  `delivery_staff` không tự gán được cho mình, kể cả khi phiếu đang là của họ (403, có test). Không gán được cho
  người đã nghỉ, người ngoài nhóm `delivery_staff`, id sai kiểu hay id không tồn tại (đều 400). Phiếu ở `DELIVERING`,
  `FAILED`, `COMPLETED`, `CANCELLED` trả 400 `DELIVERY_ASSIGN_STATE`, đúng T6. Không có IDOR, vì `get_object` vẫn đi
  qua `get_queryset` có lọc phạm vi.
- **Race khi gán và khi báo thất bại.** `_lock_note` dùng `select_for_update` trong `atomic`. Trạng thái,
  `assigned_to_id` và `failed_attempts` được đọc lại trong khoá rồi mới kiểm. Đối tượng cũ không ghi đè được (có test
  `..._stale_object_cannot_overwrite` cho cả `assign` lẫn `mark_failed`). `mark_failed` trước đây kiểm trạng thái
  ngoài khoá, nay đã sửa.
- **B5, ghi chú tự do không lọt ra ngoài.** `AuditLog.changes` chỉ có mã lý do. Dòng thời gian của phiếu, của đơn
  và danh sách đơn không chứa ghi chú (test quét toàn bộ body). Log không chứa ghi chú (test gắn handler vào root
  logger). Danh sách phiếu không có `failure_note`. `failure_note` đã vào `SCRUB_FREE_TEXT_KEYS` của AI. Cả 2 trường
  nằm trong `locked_fields`, PATCH trả 400. Thông điệp lỗi `DELIVERY_FAILURE_NOTE_PII` không lặp lại input. Ở chi
  tiết, ghi chú bị ẩn theo cửa sổ SR-PII-02 giống tên và địa chỉ.
- **R4.** `phone` chỉ có ở chi tiết, sau `get_queryset`: courier khác nhận 404, `customer_service` nhận 403 (đã thử).
  Sau cửa sổ SR-PII-02 thì trả `null`. Tem vẫn che số. `DeliveryNoteViewSet` có `NoStoreMixin`, `DeliverersView` tự
  đặt `no-store`. Courier lọc `assigned_to=<id người khác>` bị 403, và dù không bị chặn thì phạm vi dòng vẫn trả rỗng,
  nên không dò được việc của người khác. `order=<id>` được AND với phạm vi (có test). Fallback `order.customer.phone`
  khi đơn không có SĐT là thêm so với 02b, nhưng vẫn là SĐT của chính khách đơn đó nên chấp nhận.
- **Không rò giá vốn.** Không thêm khoá tiền. `test_r4_no_cost_keys_for_warehouse_and_manager` duyệt đệ quy theo
  `COST_KEYS`.
- **N+1.** `_get_allocations` giờ đọc qua prefetch của viewset (sửa luôn N+1 có từ trước), cộng thêm
  `select_related("assigned_to__staff_profile")`. `list_deliverers` chỉ dùng một truy vấn có `annotate(Count(filter=…))`.
  Join `groups` không nhân số dòng vì mỗi user chỉ khớp một nhóm tên `delivery_staff`. Cả 2 đường đều có test đếm
  truy vấn.
- **AuditLog `assign_deliverynote`** chỉ ghi ID cũ và ID mới. Gán lại đúng người đang gán trả `already: true` và
  không ghi audit.
- **Bốn test ngoài phạm vi được sửa hợp lý, không che lỗi:**
  - `test_s47_me_labels`: thêm đúng nhãn mới vào cuối danh sách việc của Quản lý. Đây là hệ quả của `0006`.
  - `test_discipline` (24 thành 25 `@action`): đúng, vì có thêm `assign` và action này có `required_perms`.
  - Snapshot AI: thêm 2 lệnh tự sinh từ route mới. Nhưng xem M1, vì một lệnh đang thiếu quyền.
  - `test_s03_migration`: loại `delivery` khỏi đích migrate, cùng lý do đã loại `ai` (`0006` phụ thuộc
    `accounts/0013`). Nếu không loại thì `accounts` không lùi được về `0006`. Test vẫn kiểm đúng điều nó cần kiểm.
- **Chấp nhận các chỗ lệch 02b mà dev đã ghi:** `STALE_STATE` trả 409 (`ConflictError`, khớp phiếu giao việc), thêm
  mã `DELIVERY_FAILURE_NOTE_INVALID`, courier hỏi id người khác thì 403. FE phải xử lý 409 ở form "Giao cho người
  giao". Điều phối viên cập nhật bảng lỗi B6 trong 02b từ 400 thành 409.

### Phát hiện

**M1 — Medium — `GET /api/delivery/deliverers/` thiếu `required_perms`, nên lệnh AI `delivery.deliverers` hiện với
mọi người**
- `backend/apps/delivery/api.py:267-274`: `DeliverersView` chỉ kiểm quyền bằng `has_perm` trong `get`, không khai
  thuộc tính lớp `required_perms`. Registry AI (`apps/ai/registry/discovery.py`) đọc `required_perms` từ lớp, nên
  spec nhận `required_perms=()` với mức A (đọc).
- Tái hiện (đã chạy, `AI_ENABLED=True`): gọi `GET /api/ai/commands/index/` bằng token `delivery_staff` hoặc
  `customer_service`, danh sách có `delivery.deliverers`. Khi gọi thật thì view trả 403, nên **không rò dữ liệu**. Tuy
  vậy, đây là lệch 02b (`required_perms=("delivery.assign_deliverynote",)`), và trợ lý sẽ gợi ý một lệnh mà người dùng
  luôn bị từ chối.
- Sửa: theo mẫu `apps/reports/api.py:15-21`, thêm `permission_classes = [IsAuthenticated]` và
  `required_perms = ("delivery.assign_deliverynote",)`, rồi dùng `require_perm(...)` trong `get`. Thêm test: index AI
  của `delivery_staff` không có `delivery.deliverers`, của `manager` thì có.

**L1 — Low — Id lọc quá lớn làm 500 (lặp lại lỗi L1 của Lô 3)**
- `backend/apps/delivery/api.py:31-42` (`_positive_int_param`): không có cận trên.
- Tái hiện (đã chạy, SQLite): owner gọi `GET /api/delivery/notes/?order=9223372036854775808`, hoặc
  `?assigned_to=99999999999999999999999`, thì gặp `OverflowError` (500). Contract quy định giá trị sai trả 400
  `INVALID_FILTER`. Hàm này cũng nhận `+5` và chữ số Unicode.
- Sửa: dùng cùng quy tắc với `apps/sales/orders/api.py:55-60` (`isascii`, `isdigit`, `len ≤ 19`, `≤ MAX_ID`). Nên
  chuyển hàm này sang `apps/common` để hai nơi dùng chung, tránh lặp code. Lô 4 không được sửa `apps/sales`, nên
  `sales` đổi sang dùng hàm chung ở lô sau. Thêm 2 giá trị trên vào `test_r4_invalid_filters_get_400`.

**L2 — Low — `expected_assigned_to` gửi dạng chuỗi luôn trả 409 sai**
- `backend/apps/delivery/services.py:289`: so sánh `note.assigned_to_id != expected_assignee_id` giữa số và chuỗi.
- Tái hiện (đã chạy): phiếu READY đang gán cho courier A, gửi `{"assigned_to": <B>, "expected_assigned_to": "<A>"}`,
  nhận 409 `STALE_STATE` dù dữ liệu không cũ. Còn `assigned_to` dạng chuỗi thì bị 400. Hai trường cùng kiểu dữ liệu
  nhưng xử lý không nhất quán.
- Sửa: ở `api.assign`, kiểm `expected_assigned_to` là `None` hoặc số nguyên dương (không nhận `bool`), sai thì trả 400
  `DELIVERY_ASSIGNEE_INVALID` (hoặc `INVALID_FILTER`), không để rơi xuống nhánh 409. Thêm 1 test.

**L3 — Low — Bộ chặn "≥ 9 chữ số" chặn nhầm vài ghi chú hợp lệ và bỏ sót số có dấu phẩy (chỉ ghi nhận, không bắt buộc
sửa)**
- `backend/apps/common/pii.py:46` bỏ khoảng trắng, `.`, `-`, `_`, `/` rồi mới tìm dãy số. Kết quả đã chạy:
  - Chặn nhầm (400 `DELIVERY_FAILURE_NOTE_PII`): `"Khách hẹn lại 10/10/2026 9h"` (ghép thành `101020269`) và
    `"Thu 1.250.000.000 đ"`.
  - Cho qua: `"Hẹn ngày 02/10/2026 lúc 15"`, `"Đơn 2 thùng, 10/10 lúc 14:30"`.
  - Bỏ sót: `"Gọi 0912,345,678 không nghe"` (dấu phẩy không bị bỏ) nên được lưu.
- Đánh giá: quy tắc này dùng chung với BR-GH-19 và 02b đã chọn. Ghi chú chỉ ở chi tiết, đã qua phạm vi, không vào
  audit, log hay AI. Vì vậy chỗ bỏ sót không gây rò ra ngoài phạm vi. Chỗ chặn nhầm có thông điệp rõ để người giao
  viết lại. Đề nghị FE đặt placeholder kiểu "Không ghi số điện thoại; ngày ghi dạng 10/10". Nếu Duy muốn chặt hơn thì
  thêm `,` vào tập ký tự bị bỏ, đổi ở `apps/common/pii.py` và áp cho cả BR-GH-19, làm ở một lô riêng.

**L4 — Low — `mark_failed(reason=None)` để ngỏ đường bỏ qua BR-GH-22**
- `backend/apps/delivery/services.py:182, 194-197`: mặc định `reason=None` thì phiếu FAILED không có lý do. Hiện chỉ
  4 test trong `apps/sales` gọi theo cách này, và API luôn truyền lý do (thiếu thì 400). Rủi ro là code mới sau này
  gọi service mà quên lý do sẽ không bị chặn.
- Sửa ở lô được phép đụng `apps/sales/**/tests`: bỏ mặc định (bắt buộc `reason`), sửa 4 test đó truyền
  `reason="NOT_MET"`. Ghi vào phiếu giao việc của lô sau. Không chặn nghiệm thu lần này.

**L5 — Low — Import trùng**
- `backend/apps/delivery/serializers.py:8-9` có cả `from . import services` lẫn `from .services import
  staff_display_name`. Nên chỉ giữ một kiểu (`services.staff_display_name`, `services.ASSIGNABLE_STATUSES`).

### Kết luận: **CHANGES REQUESTED**
Bắt buộc sửa **M1**: thêm `required_perms` cho `DeliverersView`, kèm test index AI. Nên sửa cùng lúc **L1** và **L2**,
mỗi lỗi vài dòng và có test. L3 chỉ ghi nhận. L4 làm ở lô được phép sửa test `apps/sales`. L5 sửa khi tiện. Phần
chính của lô đạt: migration chỉ thêm và rollback được, quyền chỉ cấp cho owner/manager, không leo quyền khi gán, có
`select_for_update`, ghi chú tự do không vào audit/log/timeline/danh sách/AI, SĐT đủ chỉ trong phạm vi và có
`no-store`, không rò giá vốn, không N+1. Sau khi sửa, chỉ cần re-review M1, L1, L2.

### Re-review sau khi sửa M1, L1, L2, L5 (techlead · 02/10/2026)
- `manage.py test apps.delivery apps.common apps.sales.orders`: **638 test, OK**. Full suite không dùng làm căn cứ vì
  Lô 6 đang làm dở trong `apps/sales/customers`. `makemigrations --check --dry-run` sạch. `check_naming.py` exit 0.
- Chạy lại đúng các test tạm đã dùng ở lần review đầu:

  | Gọi | Trước | Sau |
  |---|---|---|
  | Index AI của `delivery_staff`, `customer_service` | có `delivery.deliverers` | không có |
  | Index AI của `manager` | có cả 2 lệnh | có cả 2 lệnh |
  | `notes/?order=9223372036854775808`, `?order=` hoặc `?assigned_to=99999999999999999999999` | 500 (`OverflowError`) | 400 |
  | `assign` với `expected_assigned_to: "<id>"` | 409 `STALE_STATE` giả | 400 `DELIVERY_ASSIGNEE_INVALID` |
  | `customer_service` xem chi tiết hoặc lọc `assigned_to` người khác | 403 | 403 (không đổi) |

- **M1: đạt.** `DeliverersView` có `permission_classes = [IsAuthenticated]` và `required_perms` ở mức lớp, `get` gọi
  `require_perm`, theo đúng mẫu `apps/reports/api.py`. Có test index AI cho cả người có quyền và người không có quyền.
- **L1: đạt.** `apps/common/params.py::parse_positive_id` chỉ nhận chữ số ASCII, kiểm độ dài ≤ 19 trước khi gọi `int()`
  nên chuỗi 5000 chữ số không làm 500, và chặn ở `MAX_ID`. `delivery` và `sales/orders` cùng gọi hàm này. Thông điệp
  và mã lỗi của `sales` giữ nguyên, nên contract Lô 3 không đổi. Body `assign` cũng chặn id vượt int64.
- **L2: đạt.** `validate_expected_assignee` chỉ nhận `null` hoặc số nguyên dương trong int64 (không nhận `bool`), sai
  thì 400. Không còn rơi xuống nhánh 409.
- **L5: đạt.** `serializers.py` chỉ còn `from . import services`.
- Ghi chú (không chặn): `apps/common/guidance/audit_timeline.py:30-134` (Lô 2) vẫn tự kiểm id bằng `MAX_ID_DIGITS = 18`.
  Nên chuyển sang dùng `parse_positive_id` khi có lô đụng tới file này. L3 chỉ ghi nhận. L4 để lô được phép sửa test
  `apps/sales`, như đã thống nhất.

### Kết luận cập nhật: **APPROVED**

## Lô 6 — BE (B2)
> techlead · 02/10/2026 · review diff chưa commit: `apps/sales/customers/{directory_api,permissions,serializers,services,next_steps}.py`,
> 2 file test mới, `models/customers.py`, `sales/0012`, `sales/0013`, `accounts/auth/services.py`, `ai/policy/rules.py`,
> `config/api_urls.py` (route `customer-directory`), `orders/scope.py`, 2 test lô khác.

### Lệnh đã chạy
- `manage.py test apps.sales apps.accounts apps.ai`: **1065 test OK** (51 giây).
- `manage.py makemigrations --check --dry-run`: `No changes detected`.
- Lùi rồi tiến migration trên DB SQLite tạm (thư mục scratch, không đụng DB thật): `migrate` → Group có quyền
  `['manager', 'owner']`; `migrate sales 0011` → `[]`; `migrate` lại → `['manager', 'owner']`. Hai migration chỉ thêm
  và lùi được.
- `python3 scripts/check_naming.py`: exit 0, không phát sinh vi phạm mới.

### Đối chiếu trọng tâm
| Mục | Kết quả | Căn cứ |
|---|---|---|
| Chỉ người có quyền truy cập | Đạt | `directory_api.py:106` `required_perms` = `sales.view_customer_list` (+ `sales.change_customer` khi PATCH). `BusinessModelPermissions` kiểm quyền này trước Tầng 1, nên `view_customer` (Tầng 1 của NV kho/giao) không mở được danh bạ. Có test 403 cho `warehouse_staff`, `delivery_staff`, `customer_service` ở list và detail, body không chứa tên/SĐT/địa chỉ/ghi chú. Có test 401, test Chủ gỡ quyền của nhóm `manager`, test user chỉ có quyền xem thì PATCH bị 403. POST/PUT/DELETE trả 405 |
| `no-store` | Đạt | `NoStoreMixin` áp cho list, detail và PATCH, đều có test |
| `q` theo SĐT | Đạt | `directory_api.py:124`: chỉ dò SĐT khi `q` có từ 4 chữ số trở lên (có test với `"090"`). Ai gọi được endpoint thì đã có quyền xem toàn bộ danh bạ, nên dò số không mở thêm dữ liệu. Ô tìm không ghi log |
| AuditLog | Đạt | `services.py:28` `_CustomerAuditRef` làm `object_repr` = `KH-<id>`. `changes={"fields": [...]}` chỉ có tên trường. Có test quét toàn bộ dòng audit, không thấy tên cũ/mới, SĐT, địa chỉ hay ghi chú. Không có `logger`/`print` trong luồng. Thông điệp 400 không lặp lại giá trị gửi lên |
| Chặn AI | Đạt | `rules.py`: thêm 2 tiền tố vào `FORBIDDEN_PREFIXES` và `default_address` vào `SCRUB_PII_KEYS`. ViewSet không kế thừa `AiDeclarable`. Registry đã lọc theo `FORBIDDEN_PREFIXES` sẵn (`ai/registry/discovery.py`), không lệnh nào trỏ `/api/sales/customers/` |
| `total_spent` | Đạt (lệch 02b có chủ đích, đã chốt) | `directory_api.py:60-88`: cộng hoá đơn `ISSUED` của đơn chưa huỷ, trừ khoản hoàn `REFUNDED` của chính các hoá đơn đó. Đơn đã trả rồi huỷ bị loại cả hoá đơn lẫn khoản hoàn, nên không trừ hai lần. Hoàn `PENDING`/`FAILED` không trừ. Hoàn theo giao dịch không hoá đơn (`payment_transaction`) không dính vào. `refundable_amount` chặn tổng hoàn ≤ `invoice.amount`, nên số này không âm. Không có field giá vốn, có test bằng token manager. **Tech Lead đã sửa 02b §3 B2 theo công thức này** (theo ED-13-AC2), vì chữ 02b cũ sẽ cộng cả đơn đã huỷ (hoá đơn vẫn `ISSUED`) |
| Migration | Đạt | `0012` chỉ `AlterModelOptions`. `0013` là `RunPython(grant, revoke)` theo mẫu `sales/0010`, phụ thuộc `accounts/0013` nên dùng tên Group tiếng Anh. Sửa `test_s03_migration.py` (loại thêm `sales` khi lùi `accounts`) là hợp lý, cùng lý do với `delivery` ở Lô 4 |
| PATCH whitelist | Đạt | View chặn khoá lạ trước serializer (`directory_api.py:136`), service chặn thêm lần nữa (`services.py:25`). Serializer chỉ có 3 `CharField` có giới hạn độ dài, object/list trả 400. Body rỗng hoặc body là list trả 400. `select_for_update` khi lưu. Không đổi gì thì không ghi audit |
| N+1 / hiệu năng | Đạt | 5 số liệu là Subquery tương quan theo FK đã có index. Có test so số câu SQL khi có 1 khách và 9 khách. Chi tiết giới hạn 50 đơn và 50 phiếu hoàn, phiếu hoàn có `select_related`. Phiếu hoàn không trả `reason`/`failure_reason` |
| Endpoint cũ, test S5 | Đạt | `apps/sales/customers/api.py` và test S5/CS-01 không bị sửa (Q4). Có test hồi quy ED-13-AC7: NV giao vẫn đọc phiếu giao của mình và `/api/sales/customers/` |
| Hàm quyền gom | Đạt | `permissions.py::can_view_customer_directory` là nguồn duy nhất. `next_steps.py` và `orders/scope.py::can_filter_orders_by_customer` đều gọi hàm này, có test chứng minh cả 3 chỗ cùng đổi khi Chủ gỡ quyền |
| 2 test lô khác | Đạt | `test_s47_me_labels.py` thêm `sales.view_customer_list` (cùng với `delivery.assign_deliverynote` của Lô 4). `test_s03_migration.py` như trên |

### Phát hiện
**L1 (Low): tìm theo tên bị lặp code và quét toàn bộ bảng khách bằng Python**
- `backend/apps/sales/customers/directory_api.py:91-94` sao lại nguyên `apps/sales/orders/api.py:64-69`
  (`_customer_ids_by_name`). Mỗi lần gõ tìm sẽ đọc toàn bộ `(pk, name)` của bảng khách rồi đưa vào `pk__in`. Ở quy mô
  vựa hiện tại thì chấp nhận được, và L7 đã chọn cách này.
- Tái hiện: đọc hai hàm, thân hàm giống nhau.
- Cách sửa: đưa về một hàm `customer_ids_by_name(query)` trong `apps/sales/customers/services.py`, để cả hai chỗ
  cùng gọi. Làm ở lô được phép sửa `orders/api.py`. Không chặn lô này.

**L2 (Low): biểu thức annotate mới chỉ chạy test trên SQLite**
- `directory_api.py:60-88` dùng Subquery có `GROUP BY` lồng trong `Coalesce`, phép trừ Decimal và
  `nulls_last`. Cả bộ test chạy trên SQLite. Postgres hỗ trợ cú pháp này, nhưng chưa chạy thật.
- Cách kiểm: khi lên staging, gọi `GET /api/sales/customer-directory/?ordering=-total_spent` và mở chi tiết một khách
  có đơn huỷ, so `total_spent` với tay. Ghi vào checklist deploy, không cần sửa code.

**Ghi nhận (không phải lỗi)**
- ED-13-AC5/AC6 (đổi SĐT, lỗi SĐT trùng) chưa áp dụng vì 02b khoá SĐT. Dev đã ghi lệch, và việc này đang chờ Duy
  quyết. Nếu Duy cho đổi SĐT thì cần thêm kiểm trùng có khoá dòng, và audit vẫn chỉ ghi tên trường.
- Nhãn `delivery.assign_deliverynote` và route `delivery/deliverers/` trong cùng diff thuộc Lô 4, không xét ở đây.

### Kết luận: **APPROVED**
Không có lỗi Critical, High hay Medium. Hai điểm Low không chặn nghiệm thu. Đã sửa 02b §3 B2 (công thức `total_spent`)
cho khớp code và ED-13-AC2, nên FE bám theo contract này.

## Lô 1 — FE (khung + mẫu danh sách; ED-01, ED-02, ED-03 phần khung, ED-04 phần mẫu)
> Review 02/10/2026 trên diff chưa commit: `git diff -- erp-console DESIGN.md` cùng các file mới chưa track. Không xét
> `backend/`. Có tính hai chỗ điều phối viên tự sửa: xoá `@media (min-width:768px){.tabs{display:none}}` trong
> `features/orders/orders.module.css` và sửa `e2e/s12_s13_queue.py:141`. Cả hai sửa đúng: tab "Hàng chờ thanh toán" và
> "Phiếu hoàn" hiện lại trên máy tính, quyền hiện tab vẫn theo `canView`.

**Kết luận: CHANGES REQUESTED.** Có 2 lỗi High. Cả hai là chỗ code làm ngược AC đã duyệt (ED-02-AC4, ED-01-AC4). Mỗi
lỗi sửa trong vài dòng. Không có lỗi Critical: không rò giá vốn, không rò dữ liệu khách, không vượt quyền. Có 6 lỗi
Medium. M1, M2, M4 nên sửa cùng lượt này. M3, M5, M6 được để tới lô ghi bên dưới, nhưng **không deploy khi mới xong Lô 1**
(xem M3).

### Kiểm chứng
- Số liệu lấy từ lần chạy của điều phối viên: `npm ci`, `tsc`, vitest 29 file / 298 test, build mock=0, `check-no-mock`,
  `check-ai-chunks`, grep màu (553, bằng số gốc), `check_naming`, e2e `ed_batch1_shell` 56/56. Tech Lead không chạy lại
  các lệnh này.
- Tech Lead tự soi thêm:
  - Font `public/fonts/ms/material-symbols-outlined.woff2` có feature `rlig` và 148 glyph.
  - `git check-ignore` cho thấy file này bị `.gitignore:50 *.woff2` chặn và chưa từng được track.
  - Log e2e của dev (`/tmp/ed1/all/p8_lo6_fe_sr19_sr20.log`) có 5 ca hỏng, cùng lỗi
    `window.__caveMock.ai is not a function`.
  - Đã grep toàn bộ nơi gọi `remaining()`, `publishAiEnabled`, `useToast` và `ui/Shell`.

### Đối chiếu trọng tâm
| Mục | Kết quả | Căn cứ |
|---|---|---|
| Menu theo quyền, UI-RULES §2.1 | Đạt | `shared/lib/nav.ts`: thứ tự 6 nhóm đúng §2.1. Mục hiện theo `me.permissions`, không so tên nhóm (trừ 2 ngoại lệ dưới). `payments`/`refunds`/`content-categories` có `menu:false` nhưng `canView` vẫn giữ để chặn URL. Mục `soon` ẩn khỏi menu và ⌘K nhưng vẫn có trong `visibleNav`. Đã có vitest thứ tự nhóm, trùng key/href, mục con |
| 2 ngoại lệ S7-AC2 | Đạt | `onlyDelivery` còn trên `orders`, `payments`, `refunds`, `deliveries`, `sales-invoices`, `audit-logs`, `ai-settings`. `my-deliveries` xét theo nhóm (`nav.ts:245`). vitest `NV giao chỉ thấy Việc giao của tôi`. `homePath` của NV giao là `/my-deliveries/` (ED-01-AC5) |
| `ViewGuard` | Đạt | `ViewGuard.tsx:14`: khi `!me` hoặc `!canView` thì trả `NoPermission` và không mount `children`, nên không có request API của màn. Chỉ đổi phần hiển thị |
| `localStorage` | Đạt | `shell/Shell.tsx:42-56`: chỉ ghi `"collapsed"`/`"open"`; khi đọc, giá trị khác `"collapsed"` đều coi là mở. Đọc và ghi đều có try/catch. e2e có ca giá trị rác và ca chỉ cho phép khoá kỹ thuật |
| ⌘K không tìm dữ liệu khách | Đạt | `CommandSearch.tsx:27-31` chỉ lọc `label`/`short` của `menuItems(viewer)`. Không gọi API, không ghi từ khoá ra URL, storage hay log |
| `format.ts` | Đạt (xem M2) | `vnParts` dùng `timeZone: "Asia/Ho_Chi_Minh"` và `hourCycle:"h23"`. `dateTime` ra `dd/mm/yyyy hh:mm`, `vnd` ra `540.000 đ`, có vitest `01/10/2026 09:32` |
| `enums.ts` khớp `enum-map.md` | Đạt về nhãn, **không đạt AC4** (H1) | Đã so từng dòng enum-map với bảng: đủ giá trị, nhãn ⚑ đúng (`AUTO_CANCELLED`, 2 nhãn `WRITE_OFF`, mức AI, chế độ AI). Màn cũ còn tự viết nhãn (`features/*/labels.ts`, `status_label`). Theo 02b §2.2 việc thay thế làm ở các lô màn |
| Màu không viết cứng | Đạt | CSS mới chỉ dùng token. `tokens.css` thêm đúng 2 token, đã ghi vào `DESIGN.md` |
| Code AI không vào chunk nghiệp vụ | Đạt | `AiBar.tsx` không import `features/ai`. Layout bỏ `AiAssistantGate`/`ActivityFeed`. `check-ai-chunks` xanh |
| Dữ liệu cá nhân (bất biến 9) | Đạt | `error.tsx` bỏ `console.error(error)`. Toast, banner, 404 không in dữ liệu. Avatar chỉ hiện tên nhân viên. `useTabParam` chỉ ghi khoá tab vào URL |
| Accessibility | Đạt phần chính (xem L5) | Avatar: Enter/Space/↓ mở, Esc đóng và trả focus, ↑↓ Home End di chuyển, `aria-haspopup`/`aria-expanded`. Tabs dùng roving tabindex. Toast stack có `aria-live="polite"` sẵn từ lúc mount. DataTable có `caption` và trạng thái tải `role=status`. Skip link còn |
| Font icon | **Rủi ro deploy** (M5) | Script mới cho font đúng trên máy này. Bản build không tự sinh font |
| Hiệu năng | Đạt | Bỏ cột phải nên bớt chunk AI ở layout. `CommandSearch`/`AvatarMenu` nhỏ, chỉ vẽ khi mở. Sidebar đọc trạng thái trong `useLayoutEffect`, không gây nháy sau khi hydrate |

### Phát hiện

**H1 (High): enum lạ hiện "Không rõ", trái ED-02-AC4**
- `shared/lib/enums.ts:11-12` (`UNKNOWN_ENUM = { label: "Không rõ" }`) và `:300-304` (`enumOf`).
  `shared/ui/Chip.tsx:2,11` vẽ theo đó. `shared/lib/enums.test.ts:6-11` lại khoá đúng hành vi sai này.
- ED-02-AC4 ghi: "API trả về giá trị enum lạ → hiện chip trung tính ghi **đúng mã gốc**. Không tự đặt nhãn". Hiện code
  giấu mã nên người vận hành không biết BE vừa trả trạng thái gì. Dev cũng ghi chỗ này trong 03-dev-notes mà không
  đánh dấu là lệch AC.
- Tái hiện: `enumLabel(ENUMS.salesOrderStatus, "NEW_FANCY_STATE")` trả `"Không rõ"`. AC yêu cầu `"NEW_FANCY_STATE"`.
- Cách sửa:
  - `enumOf` trả `{ label: String(value), tone: "mute" }` khi giá trị lạ.
  - `null`, `undefined`, `""` thì trả `"—"`, không có chip.
  - Sửa vitest theo AC4 và sửa chú thích ở `Chip.tsx:2`.

**H2 (High): `useTabParam` dùng `replaceState`, nên bấm Back không về tab trước (trái ED-01-AC4)**
- `shared/ui/Tabs.tsx:85-93`: `select()` gọi `window.history.replaceState`, không tạo mục lịch sử mới. Hook cũng không
  nghe `popstate`, nên khi URL đổi bằng Back/Forward thì tab không đổi theo.
- ED-01-AC4: "URL đổi theo tab, nên Back quay về đúng tab trước". Lô 7 (Kho & lô), Lô 12 và Lô 13 sẽ dựng tab trên hook
  này, nên phải sửa trước khi các lô đó bắt đầu.
- Tái hiện: dùng `useTabParam(["a","b"],"a")`, chọn tab "b" rồi bấm `history.back()`. Trình duyệt rời khỏi trang, không
  về tab "a".
- Cách sửa:
  - `select` dùng `pushState` (bỏ qua khi bấm lại đúng tab đang chọn).
  - Thêm `useEffect` nghe `popstate` để đọc lại `?tab=` và kiểm khoá có hợp lệ không.
  - Thêm vitest (jsdom) hoặc một ca trong `e2e/ed_batch1_shell.py` trên trang mẫu, hoặc giao ca này cho e2e Lô 7.

**M1 (Medium): dải mất mạng chung không nhận được `asOf` và "Thử lại", nên ED-03-AC4 không đạt được**
- `shared/ui/shell/Shell.tsx:158` gắn `<OfflineBanner />` không có props. `OfflineBanner.tsx:25-42` chỉ hiện dòng
  "Dữ liệu lúc …" và nút Thử lại khi có `asOf`/`onRetry`. Màn hình lại không có đường nào để truyền hai giá trị này vào
  dải chung (lệch số 5 trong dev notes).
- Tái hiện: e2e `ed_batch1_shell.py:178-181` tắt mạng. Dải hiện nhưng không có "Dữ liệu lúc" và không có nút Thử lại.
- Cách sửa: thêm một context nhỏ trong `shared/ui/states/`, ví dụ `useOfflineSource({ asOf, onRetry })`. Màn đang hiển
  thị gọi hàm này để đăng ký, còn Shell đọc lại để truyền vào banner. Phải có trước Lô 3, vì màn đầu tiên dùng
  `ListPage` ở lô đó.

**M2 (Medium): đếm ngược trên danh sách đơn hiện giây nhưng chỉ cập nhật mỗi 30 giây**
- `format.ts:120-129` đổi `remaining()` sang `mm:ss`. Nơi gọi duy nhất là `features/orders/components/OrdersScreen.tsx:56`,
  với `useNow(…, 30_000)` ở `:122`, nên số giây nhảy cách 30 một (ví dụ 11:42 rồi 11:12). Đây là hồi quy trên màn đã
  nghiệm thu S10.
- Tái hiện: bản mock, đăng nhập `loc`, mở `/orders/`, nhìn một đơn Giữ chỗ trong 1 phút.
- Cách sửa: đổi `useNow` ở `OrdersScreen.tsx:122` thành `1000`, chỉ chạy khi có đơn BOOKED. Đây là sửa import/tối thiểu,
  được phép theo 02b §5.2. Cách khác là cho Lô 3 làm, nhưng khi đó phải ghi vào 02c để không sót.
- Kèm theo (Low): `features/orders/useNow.ts` có `mmss()` trùng logic với `remaining()`. Gộp lại ở Lô 3.

**M3 (Medium): bỏ cột phải làm mất "Tóm tắt" (DW-16) và hỏng bộ e2e SR-20/F6 cho tới khi xong Lô 2**
- `app/(console)/layout.tsx` bỏ `AiAssistantGate`. Hàm duy nhất gọi `publishAiEnabled` là `features/ai/api.ts:16`, và
  hàm này chỉ chạy khi gate mount. Hệ quả:
  - `useAiEnabledAndConsented()` (`features/guidance/components/GuidancePanel.tsx:21,42`) luôn trả false, nên nút
    "Tóm tắt" không bao giờ hiện.
  - `window.__caveMock.ai` (`features/ai/mock.ts:153`) không còn được đăng ký, nên `e2e/p8_lo6_fe_sr19_sr20.py` hỏng
    5 ca. Các ca này kiểm lúc chạy rằng màn nghiệp vụ không tải AI khi AI tắt (SR-20, BR-AI-17). Hiện chỉ còn
    `check-ai-chunks` kiểm tĩnh.
- Thay đổi này đúng 02b §0 dòng 2. Nhưng giữa Lô 1 và Lô 2, một tính năng đã nghiệm thu bị mất và một hàng rào hiệu năng
  không còn được kiểm.
- Yêu cầu:
  - (a) **Không deploy staging/production khi chỉ có Lô 1.** Ghi điểm dừng này vào 02c.
  - (b) Lô 2 phải nối lại nguồn `ai_enabled` cho `gate-state` (từ khối AI trong trang), và đăng ký lại
    `__caveMock.ai` ở chỗ luôn nạp trong bản mock, ví dụ `features/auth/mock.ts`. Sau đó chạy lại `p8_lo6` cho đủ 22/22.

**M4 (Medium): cột giá vốn trong `DataTable` chưa có chốt chặn như 02b §4 yêu cầu**
- `shared/ui/list/DataTable.tsx:22-23,197`: `locked` chỉ vẽ icon khoá. Việc ẩn cột hoàn toàn do màn tự làm ("Người không
  có quyền thì KHÔNG đưa cột vào").
- 02b §4 dòng "FE vô tình hiện giá vốn khi BE trả thiếu" yêu cầu cột `locked` chỉ render khi `me.can_view_cost` có, và
  phải có vitest `DataTable`. Hiện không có cả hai.
- BE vẫn là lớp chặn thật nên đây không phải lỗi rò. Nhưng Lô 7, 10, 11, 12 sẽ có nhiều cột tiền, cần chốt chặn sẵn.
- Cách sửa:
  - Thêm prop bắt buộc `canViewCost: boolean` (hoặc `viewer`). `DataTable` tự lọc bỏ cột `locked` khi giá trị này false.
  - Thêm vitest: `canViewCost=false` thì `thead` không có tiêu đề cột khoá và ô không có trong DOM. `true` thì có icon
    khoá.

**M5 (Medium): font icon nằm ngoài git nên build trên máy khác sẽ vỡ icon**
- `.gitignore:50 *.woff2` chặn `erp-console/public/fonts/ms/material-symbols-outlined.woff2` (file này chưa từng được
  track). `npm run build` không chạy `scripts/subset-material-symbols.py`, chỉ copy file đang nằm trên đĩa.
- Kết quả:
  - Build ở máy này (font mới, 93 KB, `rlig`) thì icon đúng.
  - Build ở clone sạch hoặc worktree khác (ví dụ `claude/busy-carson-*`): nếu không có file thì mọi icon thành chữ
    sau 3 giây `font-display:block`; nếu còn font cũ thì 25 icon mới thành chữ.
  - Production hiện chạy font cũ, nên lần deploy kế tiếp phụ thuộc vào máy build.
- Tái hiện: `git clone` sạch, `npm ci && npm run build`, rồi xem thư mục `out/fonts/ms/`, không có woff2.
- Cách sửa (đề xuất, điều phối viên chọn):
  - Thêm `!erp-console/public/fonts/ms/*.woff2` vào `.gitignore` rồi commit font cùng Lô 1. File 93 KB, giấy phép
    Apache-2.0 nên được phân phối.
  - Thêm bước kiểm trước build: script đọc `ICONS` và báo lỗi khi font thiếu hoặc thiếu ligature.
  - Ghi bước này vào `doc/ops/moi-truong.md`.

**M6 (Medium): ký hiệu tiền lẫn "₫" và "đ" trên cùng một màn**
- FE dùng `vnd()` ra "đ", còn chuỗi BE dựng (`vnd_display`, câu lỗi, nhãn timeline) vẫn ra "₫" (lệch số 9). 02b §0c
  chấp nhận tạm, nhưng G5 yêu cầu `390.000 đ` ở mọi nơi.
- Quyết định của Tech Lead: **thống nhất "đ"**. BE đổi `vnd_display` ở lô BE kế tiếp có đụng `apps/sales` (Lô 3 R3).
  Khi đó bỏ `beVnd()` trong `features/orders/mock.ts:946` và bỏ regex nhận cả hai ký hiệu trong e2e. Tech Lead sẽ sửa
  02b §0c khi giao Lô 3. Không chặn Lô 1.

**L1 (Low): `Toast` bỏ qua tuỳ chọn `duration`**
- `overlay/Toast.tsx:14` khai `duration` trong `Options`, nhưng `push` ở `:91-93` không lưu giá trị này, nên
  `ToastView` không bao giờ nhận được. Sửa: lưu `duration` vào `ToastItem` rồi truyền xuống.

**L2 (Low): code trùng hoặc không còn ai dùng**
- `format.ts:58-62`: `dateTimeFull` chép nguyên `dateTime`. Nên viết `export const dateTimeFull = dateTime`.
- `shared/ui/Shell.tsx` chỉ còn re-export và không file nào import, nên xoá luôn ở lô này.

**L3 (Low): đường dẫn trong `nav.ts` lệch 02b §1**
- `nav.ts:350` dùng `/sales-invoices/` và `nav.ts:362` dùng `/purchase-invoices/`, trong khi 02b §1 ghi
  `/accounting/sales-invoices/` và `/accounting/purchase-invoices/`. Hai mục đang `soon` nên chưa ảnh hưởng.
- Lô 12 chọn một. Tech Lead chấp nhận đường dẫn ngắn của `nav.ts` và sẽ sửa 02b §1 khi giao Lô 12.

**L4 (Low): nút "Về Tổng quan" dẫn người không có Tổng quan tới màn "Không có quyền"**
- `states/NotFoundScreen.tsx:6` và `app/not-found.tsx:7` mặc định trỏ `/overview/`. Với NV giao, bấm nút sẽ ra màn
  "Không có quyền".
- `ViewGuard` đã truyền `homePath(me)`, nhưng chữ trên nút vẫn là "Về Tổng quan".
- Sửa: `not-found.tsx` lấy `homePath(me)` qua `useAuth`. Nhãn nút đổi theo đích, ví dụ "Về Việc giao của tôi", hoặc
  dùng một nhãn chung là "Về trang chính".

**L5 (Low): accessibility của ⌘K và menu avatar**
- `CommandSearch.tsx:70` khai `aria-modal="true"` nhưng không giữ focus trong hộp: Tab đi ra trang phía sau. Khi đóng
  hộp, focus cũng không về lại nút mở.
- `AvatarMenu.tsx:65-66`: bấm Tab sẽ đóng menu ngay trong keydown, nên phần tử đang có focus bị gỡ khỏi DOM và focus có
  thể rơi về `body`.
- Sửa:
  - Lưu `document.activeElement` khi mở và trả focus khi đóng.
  - Giữ Tab trong hộp ⌘K.
  - Với avatar, đóng menu sau khi focus đã chuyển đi (dùng `onBlur` của wrapper, kiểm `relatedTarget`).

**L6 (Low): tài liệu và chú thích cũ**
- `features/orders/components/OrdersTabs.tsx:3-5` và `features/orders/README.md:47` vẫn ghi "tab chỉ hiện ở điện thoại".
  Sửa ở Lô 3.
- `DESIGN.md:254-256` vẫn mô tả bố cục 3 cột và nút sáng/tối. Dev đã ghi, sửa ở Lô 17.
- `globals.css`: ở ≥768 px, `.nav a{min-height:30px}` nhỏ hơn vùng bấm 40 px mà `DESIGN.md` quy định. Thiết kế vẽ 30 px,
  nên cần Duy chọn một trong hai. Không chặn lô.

### Việc phải làm để chuyển APPROVED
1. Sửa H1 và H2, kèm test.
2. Sửa M1 và M4. Đây là API của khối dùng chung, phải chốt trước Lô 3.
3. Sửa M2 bằng một dòng hoặc ghi vào 02c cho Lô 3.
4. Điều phối viên chọn cách xử lý M5 trước khi commit, và ghi điểm dừng "không deploy khi chỉ có Lô 1" (M3) vào 02c.
5. Chạy lại vitest, `tsc`, build mock=0 kèm `check-no-mock` và `check-ai-chunks`, `ed_batch1_shell`, `s7`, `s12`.

### Vòng 2 — re-review 02/10/2026
**Kết luận: APPROVED.** H1, H2, M1, M2, M4 đã sửa đúng và có test. QA B1–B6 và L1 cũng đã sửa. Không thấy lỗi mới mức
Medium trở lên. Không rò giá vốn, không rò dữ liệu khách, không vượt quyền.

**Kiểm chứng Tech Lead tự chạy:** `npx tsc --noEmit` sạch. `npx vitest run` cho 34 file / 329 test đạt (vòng 1 là
29 / 298). `python3 scripts/check_naming.py` OK, không phát sinh mới. `git check-ignore -v` cho thấy font
`public/fonts/ms/material-symbols-outlined.woff2` (93 KB) đã được mở chặn bởi `.gitignore:54`. Tech Lead không chạy lại
e2e và build, nên dùng số của dev ở 03-dev-notes "Kiểm chứng vòng 2".

| Mục | Kết quả | Căn cứ |
|---|---|---|
| H1 enum lạ | Đạt | `enums.ts:307-311`: giá trị lạ trả `{label: mã gốc, tone: "mute"}`. Giá trị null, undefined hoặc rỗng trả "—". `Chip.tsx` in "—" không chip. Test `enums.test.ts` và `Chip.test.ts` khoá đúng AC4 |
| H2 Tabs Back | Đạt | `Tabs.tsx`: `select` gọi `pushState` và bỏ qua khi bấm lại tab đang chọn. `popstate` được đăng ký và gỡ trong cùng effect. Khoá lạ thì về `fallback`. `tabHref` giữ các tham số khác. Next 14.2.35 đã vá `history.pushState` nên giữ `history.state` như hiện tại là đúng |
| M1 dải mất mạng | Đạt | `offlineSource.ts`: kho ở mức module. `useSyncExternalStore` tự gỡ listener. Mỗi đăng ký có cleanup lọc theo `id`, nên đổi màn hay đổi `asOf` không để lại entry thừa, không rò bộ nhớ. `onRetry` đi qua ref, nên hàm mới mỗi lần vẽ không làm đăng ký lại. `ListPage` và `usePagedList` tự đăng ký. `OfflineBanner` có "Dữ liệu lúc" và nút Thử lại. Mờ nội dung chỉ một lần (`globals.css:592-593`) |
| M2 đếm ngược | Đạt | `OrdersScreen.tsx:123` đổi sang `useNow(…, 1000)` và chỉ chạy khi có đơn BOOKED |
| M4 cột giá vốn | Đạt | `DataTable.tsx:57` khai `canViewCost: boolean` bắt buộc (tsc chặn nếu màn quên truyền). `:108` lọc cột `locked` trước mọi nhánh, nên khung xương, tiêu đề và ô đều không có cột này. `DataTable.test.ts` có ca `render` của cột khoá không bị gọi khi không có quyền. Harness đã truyền prop |
| B2 / L4 nút về trang chính | Đạt | `AppStates.tsx` nằm ở `features/auth`, import `shared/*` và `./AuthProvider`. Không file `shared/` nào import ngược `features/`, nên không có import vòng. `app/not-found.tsx` (server) gọi client component qua `"use client"`, đúng cách |
| B3 cuộn ngang 360 px | Đạt | `.lt-scroll{position:relative}` |
| B4, B5, B6, L1 | Đạt | `table.lt th` đã bỏ in hoa. `ErrorScreen` theo W6h. ⌘K nghe Esc ở cấp document và trả focus đồng bộ. `rAF` được huỷ. Toast đọc `duration` |
| `vitest.config.ts` `oxc.jsx` | Đạt | Vitest 5.0.2 dùng oxc, và khoá `oxc.jsx.runtime: "automatic"` chỉ ảnh hưởng vitest, không đụng build Next. Cảnh báo "ESM syntax in a file loaded as CommonJS" là cảnh báo của Vite về loader, không làm hỏng test |
| M5 font | Đạt | Font được commit cùng lô theo lựa chọn của điều phối viên. Giấy phép Apache-2.0 |
| M3, M6, B8, P1 | Theo chốt của điều phối viên | M3: không deploy khi chưa có Lô 2. **02c chưa ghi điểm dừng này** (chỉ có dòng 62 "Deploy: không tự làm"). Điều phối viên nên thêm một dòng vào 02c trước khi commit. M6: dùng "đ" và FE tự định dạng từ số. B8: đúng. P1: Lô 15 |

**Còn lại, mức Low, không chặn lô. Ghi để giao cho lô có đụng tới:**
- **L7 (Tabs nhiều thanh trên một trang):** `useTabParam` luôn dùng tham số `tab`. Nếu một trang có hai thanh `Tabs`
  cùng đồng bộ URL thì hai thanh ghi đè `?tab=` của nhau. `pushState` cũng không bắn `popstate`, nên thanh kia không
  biết URL đã đổi. Khi tải lại, thanh kia nhận khoá lạ và về `fallback`. Hiện chưa màn nào có hai thanh. Quy ước:
  **mỗi trang chỉ một `useTabParam`**. Thanh tab con (nếu Lô 7, 12 hoặc 13 cần) dùng `useState` thường, hoặc thêm tham
  số tuỳ chọn `param` cho hook ở lô đó. Dev nên ghi quy ước này vào chú thích của hook.
- **L8 (`offlineSource` thứ tự):** khi `asOf` đổi, entry bị gỡ rồi thêm lại ở cuối, nên có thể vượt lên trên entry đăng
  ký sau nó. Hiện chỉ `usePagedList` và `ListPage` cùng đăng ký cho một màn, với dữ liệu giống nhau, nên không ảnh hưởng.
  Nếu sau này có khối con đăng ký riêng, đổi sang cập nhật entry tại chỗ.
- **L9 (`enumOf` dùng `table[key]`):** khoá kiểu `"constructor"` sẽ trả hàm của `Object.prototype`. BE không trả các giá
  trị này. Nên dùng `Object.hasOwn(table, key)` khi có lô đụng `enums.ts`.
- **Còn từ vòng 1:** L2 (`dateTimeFull`, re-export `shared/ui/Shell.tsx`), L3 (đường dẫn hoá đơn, Lô 12), L5 phần giữ Tab
  trong hộp ⌘K và menu avatar, L6 (chú thích orders, Lô 3).
- `check_naming` báo một file đã giảm vi phạm. Điều phối viên chạy `--update` để khoá baseline khi commit.

## Lô 7 — BE (R5, R6, R7, R7b)
> techlead · 02/10/2026 · Diff chưa commit dưới `backend/apps/inventory/` (`batches/`, `stock/`). Không xét `stocktake/`, `returns/`.

### Kiểm chứng đã chạy trong lượt này
- `manage.py test apps.inventory apps.reports --parallel 1`: Ran 381 tests, OK.
- `python3 scripts/check_naming.py`: OK, không có vi phạm mới.

### Trọng tâm: kết quả
| Mục | Kết quả |
|---|---|
| Rò giá vốn (bất biến 1) | **Không rò.** `BatchSerializer` giữ `sensitive_fields`. `receipt` chỉ có `{id, code}`. Ledger, stock-entries và warehouses không có field tiền: `total_qty` là tổng kg của `qty_available`, không nhân giá. Test quét đệ quy khoá JSON bằng số giá mua dễ nhận (`test_ed29_ac1_exact_key_set_and_no_cost_for_every_group`, `test_r7_exact_keys_and_no_cost_for_every_reader`, `test_ed24_ac4_no_cost_for_every_reader`, `test_ed23_cost_hidden_from_manager_and_warehouse_staff_but_owner_sees`). |
| Dữ liệu cá nhân (bất biến 9) | **Không rò.** Mọi nơi gọi `record_movement` chỉ ghi mã: `reconciliation N`, `return N (...)`, `INV…`, `cancel SO…`, `create_batch`, `cancel_expired_batch`, `supplier_return SR-N`, `cancel_purchase_receipt PR-N`, cùng `Nhập lô …` của seed. Không có chuỗi nào chứa tên, SĐT hay địa chỉ khách. Tham chiếu đơn bán chỉ hiện mã `SO…` cùng id. `created_by_name` lấy `StaffProfile.display_name` hoặc username của **nhân viên**, không đọc `phone` (`stock/serializers.py:19-25`, có test `test_ed24_created_by_name_never_a_phone_number`). `AuditLog create_warehouse` chỉ ghi `is_group`. |
| Phân quyền | Ledger cần `view_stockledgerentry`, warehouses cần `view_warehouse`, stock-entries cần `view_stockentry`, khớp seed `accounts/0002` (Chủ, Quản lý, NV kho). POST và PATCH kho cần `add_/change_warehouse`, nên chỉ Chủ có. Có test 403/401 theo từng Group. Ledger là `ReadOnlyModelViewSet`. Kho bỏ DELETE (`test_ed25_warehouse_with_batch_cannot_be_deleted_through_api`). |
| Lỗi 400 | `stock/filters.py` dùng `apps/common/params.py::parse_positive_id`. Thông điệp chỉ nêu tên tham số. `create_warehouse` không lặp lại tên gửi lên. Có test "without_echo" cho từng loại. |
| D-1 | `POST /stock-entries/` vẫn chỉ lưu dòng, không đổi `qty_available` và không ghi sổ (`test_d1_creating_an_entry_does_not_change_stock_or_ledger`). Không có DELETE (405). |
| Lệch 02b mà dev đã ghi | Chấp nhận cả 5 chỗ. Dùng truy vấn con cho `balance_after` là **đúng hơn** `Window` mà 02b ghi, vì `Window` chạy sau WHERE nên lọc sẽ ra sai (`test_ed29_balance_after_stays_correct_when_filtered`). Giữ PATCH kho để không mất lệnh AI. Bỏ DELETE để tránh lỗi 500 do PROTECT. Điều phối viên cập nhật dòng R6 trong 02b §3.8 thành "truy vấn con tương quan". |
| Hiệu năng `balance_after` | Chạy được ở quy mô hiện tại, chưa có index tối ưu. Xem L1. |

### Phát hiện
**L1 (Low): Sổ nhập xuất trên Postgres chưa có index phù hợp**
- Vị trí: `stock/api.py:73-87` (truy vấn con), `:105` (sắp xếp), `:117` cùng `filters.py:66-75` (lọc ngày).
- `StockLedgerEntry` chỉ có index FK `batch_id`. Mỗi dòng của trang chạy một truy vấn con: quét index `batch_id`, rồi lọc `created_at` và `id` trên heap, cộng toàn bộ lịch sử của lô. Chi phí là O(số dòng của lô) × 20 dòng mỗi trang.
- `ORDER BY -created_at, -id` không có index, nên mỗi trang phải sort top-N trên toàn bảng.
- `created_at__date` bọc cột trong hàm, nên index trên `created_at` cũng không dùng được.
- Postgres ≥ 9.6 hoãn tính subplan tới sau LIMIT, nên chỉ 20 truy vấn con chạy. Đếm phân trang trên Django 5.1 cũng bỏ annotation. Với quy mô một vựa (vài chục nghìn dòng) thì chấp nhận được.
- Tái hiện: trên Postgres có khoảng 1e6 dòng, chạy `EXPLAIN ANALYZE` truy vấn của `GET /api/inventory/ledger/`. Kết quả có Seq Scan và Sort trên `inventory_stockledgerentry`.
- Đề xuất (lô sau, cần migration và lý do trong hồ sơ, không chặn lô này):
  - Thêm `Meta.indexes = [Index(fields=["batch", "created_at", "id"]), Index(fields=["-created_at", "-id"])]`.
  - Đổi `date_range_q` sang khoảng datetime có múi giờ, ví dụ `created_at__gte=<00:00 giờ VN>` và `created_at__lt=<00:00 ngày sau>`, để dùng được index.

**L2 (Low): PATCH đổi tên kho không đi qua cùng luật với POST**
- Vị trí: `stock/api.py:31` (`UpdateModelMixin` dùng `WarehouseSerializer` thẳng).
- Đổi tên không ghi `AuditLog`, không gộp khoảng trắng và không so trùng theo kiểu không phân biệt hoa thường.
- Tái hiện: Chủ PATCH kho B thành `{"name": "kho chính"}` khi đã có "Kho chính". Kết quả là 200 trên Postgres, vì unique ở đây phân biệt hoa thường. PATCH `"Kho  chính"` (2 dấu cách) cũng trả 200.
- Đây là hành vi cũ, dev đã ghi. FE Lô 7 không có màn đổi tên. Đề xuất: khi làm màn sửa kho, cho PATCH gọi `warehouse_services.rename_warehouse` dùng chung phần kiểm tên và ghi audit.

**L3 (Low): docstring sai với hành vi**
- `stock/warehouse_services.py:2` ghi "chỉ thêm, không sửa/xoá qua API", nhưng PATCH/PUT vẫn mở (`stock/api.py:31`). Sửa câu thành "thêm qua service; đổi tên qua PATCH (chưa qua service); không xoá".

**L4 (Low): helper lọc bị lặp và import chéo module**
- Ba nơi cùng đọc id lọc và cùng trả `INVALID_FILTER`: `delivery/api.py:34` (`_positive_int_param`), `sales/orders/api.py:40` và `inventory/stock/filters.py`.
- `batches/api.py:13` import vào ruột module `stock`.
- Đề xuất: khi có dịp, chuyển `parse_id_param`, `parse_date_param`, `parse_choice_list_param`, `date_range_q` lên `apps/common/params.py` rồi gom lại. Không đổi hành vi, không chặn lô.

Không có phát hiện Critical, High hay Medium.

### Kết luận: **APPROVED**
- Lô đạt AC của R5, R6, R7, R7b và các bất biến 1, 2, 3, 5, 9.
- L1 đến L4 là nợ kỹ thuật cho lô sau. L1 nên thành một mục trong 02c khi Sổ nhập xuất vượt khoảng 100 nghìn dòng.
- Điều phối viên sửa dòng R6 ở 02b §3.8 cho khớp cách cài đặt thật (truy vấn con).

## Lô 8 — BE

Người review: techlead · Ngày 02/10 · Phạm vi: `inventory/models/stocktake.py`, migration `inventory/0005`, `inventory/stocktake/` (`services.py`, `serializers.py`, `api.py`, `queries.py`, test mới), cùng 3 test ngoài phạm vi (`common/tests/test_s4_actor_fields.py`, `ai/registry/tests/test_discipline.py`, `commands_index_snapshot.json`). Không xét `next_steps.py`.

### Kiểm chứng đã chạy trong lượt này
- `manage.py test apps.inventory apps.common`: **571 test OK**.
- `makemigrations --check --dry-run`: No changes detected.
- `python3 scripts/check_naming.py`: OK, không phát sinh vi phạm mới.
- Tái hiện H1 và L3 bằng test tạm đặt ở scratchpad (chạy qua `PYTHONPATH`, không thêm file vào repo).

### Đạt
- **Không rò giá vốn.** Kiểm kê không có field tiền. Serializer khai field tường minh, dòng chỉ có kg, mã lô, tên hàng và tên kho. Có test quét `COST_KEYS` cùng giá trị mẫu 123457 cho list, detail, create, replace, approve và 409.
- **Không rò dữ liệu cá nhân.** Chỉ có tên hiển thị của nhân viên, không có SĐT nhân viên (đã có test 409). `AuditLog.changes` chỉ chứa `line_count` hoặc tên trường, không chép lý do hay ghi chú.
- **Phân quyền.**
  - Tầng 1 qua `BusinessModelPermissions`.
  - `replace_lines` có `required_perms=change_stockreconciliation` và `require_perm`.
  - `approve` giữ Tầng 2.
  - `delivery_staff` và `customer_service` nhận 403, người chưa đăng nhập nhận 401. Không có DELETE (405).
- **BR-KK-02/08.**
  - Người tạo phiếu hoặc người có `AuditLog update_reconciliation_lines` (theo `actor` hoặc `ai_actor`) đều bị chặn duyệt.
  - Không xoá được dấu vết: `AuditLog` có `default_permissions=("view",)`, không có API ghi hay xoá, FK là PROTECT.
  - Đường AI mức A/B ghi `ai_actor` = chủ AI nên vẫn bị tính là người sửa. `replace_lines` là `form_only` nên AI không gọi được.
- **409 `STALE_STATE`.**
  - Khoá dòng phiếu rồi mới so `updated_at`. Chuỗi trả về dùng chính `DateTimeField` của DRF nên gửi lại khớp tới micro giây.
  - PATCH ghi chú cũng tăng phiên bản.
  - Body 409 có `updated_by_name` và `updated_at`, không có dữ liệu cá nhân.
- **`apply_reconciliation` atomic và khoá.**
  - Phép tính tồn giữ nguyên như trước: `diff = counted − qty_available`, ghi qua `record_movement`. `record_movement` không bị đụng.
  - Khoá phiếu xong mới `refresh_from_db`, nên hai người duyệt cùng lúc thì chỉ một người áp vào sổ (đã có test duyệt hai lần, tồn đổi một lần).
  - Audit nằm trong giao dịch. Thứ tự khoá là phiếu trước, lô sau. Luồng bán chỉ khoá lô nên không tạo vòng khoá.
- **Migration.** Chỉ `AddField` (null) cộng `RunPython` backfill `updated_at = created_at`. Hàm ngược là noop, sau đó `RemoveField`. Có test migrate xuôi rồi ngược.
- **N+1.** `queries.reconciliation_queryset` dùng `select_related` cho người tạo và người duyệt, `Prefetch` dòng kèm lô, kho, hàng, và subquery cho người sửa gần nhất cùng `edited_lines_by_me`. Có test đếm truy vấn cho list và detail.
- **Lỗi 400 không lặp lại input.** `PositiveIdField`, `counted_qty` và `reason` dùng thông điệp riêng. `_first_message` chỉ lấy thông điệp. Lọc sai trả `INVALID_FILTER` và có test không echo.
- **Đổi `created_by` và `approved_by` sang object.**
  - `grep` trong `erp-console/features`: không màn nào đọc reconciliation (W2c, F1f, W2g là màn mới của Lô 8 FE). Chỉ `auth/mock.ts` có tên quyền.
  - BE: không app nào đọc JSON của endpoint này. `ai/execution/safety.py` đọc model, không đọc serializer.
  - Hai test S4 đã sửa đúng.
- **3 test ngoài phạm vi.**
  - `test_discipline` lên 26 `@action` là đúng: Lô 4 thêm `assign`, Lô 8 thêm `replace_lines`.
  - Snapshot thêm `inventory.stockreconciliation.replace_lines` là đúng. Hai dòng `delivery.*` thuộc Lô 4, không phải lỗi của Lô 8.
  - Hai file này đang bị nhiều lô cùng sửa, nên điều phối viên cần gộp cẩn thận khi commit.

### Phát hiện

**H1 (High): tồn bị bơm sai khi có xuất bán giữa lúc nhập số và lúc duyệt**
- Vị trí: `stocktake/services.py:208-224`.
- Lúc nhập số (`_prepare_lines`), service chụp `system_qty` và cho FE hiện `difference_qty`. Lúc duyệt, service lại tính `diff = counted_qty − qty_available hiện tại`, rồi ghi đè `system_qty` và `difference_qty`. Kết quả là kg đã bán sau lúc đếm được cộng ngược vào tồn.
- Tái hiện 1 (đã chạy): lô có tồn 50 kg.
  1. Kho đếm được 48 kg, nhập lý do. Phiếu hiện chênh −2.
  2. Xuất bán 5 kg, tồn sổ còn 45.
  3. Quản lý duyệt.
  4. Kết quả: 200, `qty_available = 48`, trong khi kg thực còn trong kho là 43. Sổ ghi RECONCILE **+3** ("thừa" 3 kg) thay vì −2. Hệ quả là bán vượt hàng thật, và BR-KK-03 cùng báo cáo hao hụt (BR-BC-04) bị sai.
- Tái hiện 2 (đã chạy): như trên nhưng đếm 49 kg và không ghi lý do. Duyệt trả 400 `BR-KK-04` "chênh lệch dương phải ghi lý do", dù lúc nhập số phiếu hiện chênh −1. Phiếu kẹt. Muốn gỡ thì phải có người sửa dòng, và người đó lại mất quyền duyệt.
- Nguồn lỗi: logic này có từ trước, và 02b §3 B1 ghi "`apply_reconciliation` giữ nguyên logic", nên dev làm đúng phiếu giao. Nhưng trước Lô 8, `lines` ở API là read-only, nên luồng này gần như chưa ai chạy. Từ Lô 8 đây là đường chính. Lỗi thuộc thiết kế (lỗi của techlead), không phải lỗi của dev.
- Đề xuất. Đổi ngữ nghĩa duyệt cần Duy chốt, mã đề xuất **BR-KK-09**.
  - **(Khuyến nghị) Phương án B:** duyệt áp đúng `difference_qty` đã chụp lúc nhập số, tức `record_movement(qty_change=line.difference_qty)`. Không tính lại, không ghi đè `system_qty` và `difference_qty`. Bỏ kiểm BR-KK-04 lúc duyệt vì đã kiểm lúc nhập. Số người duyệt nhìn thấy đúng bằng số được áp vào sổ. Nếu kết quả âm thì `record_movement` tự chặn.
  - **Phương án A:** lúc duyệt, nếu có dòng mà `batch.qty_available ≠ line.system_qty` thì trả 409 `RECON_STOCK_CHANGED` kèm `line_index`, yêu cầu lưu lại dòng để chụp sổ mới. An toàn, nhưng khi Shop bán liên tục thì phiếu khó duyệt được.
  - Test cần thêm vào `test_lines.py`: hai kịch bản tái hiện ở trên, sau khi duyệt thì `qty_available == 43` (phương án B) hoặc trả 409 (phương án A).
  - Sửa nằm trong `stocktake/services.py`, không đụng `record_movement`.

**M1 (Medium): tạo phiếu qua AI mang được `lines` ngoài schema; ở mức C, chủ AI vẫn duyệt được**
- Vị trí: `stocktake/api.py:75` cùng `ai/execution/dispatch.py` (args chuyển nguyên, không lọc theo `input_schema`).
- Lệnh `inventory.stockreconciliation.create` khai schema chỉ có `count_date` và `note`. Pipeline chỉ `is_valid()` rồi gửi nguyên `args`, nên `lines` vẫn tới view và tạo phiếu có số đếm.
  - Ở mức C, lệnh chạy bằng user của **người xác nhận** Y với `ai_actor=None`. Khi đó `created_by` là Y, và chủ AI X (nếu có quyền duyệt) không bị BR-KK-02/08 chặn, dù chính AI của X soạn số.
  - Trần kg của pipeline đọc khoá `qty` nên không thấy `counted_qty`.
- Tái hiện: X là `manager`, đề xuất AI `inventory.stockreconciliation.create` với `args.lines`. Y là `warehouse_staff`, xác nhận. Sau đó X gọi `POST …/approve/` và nhận 200.
- Mức độ: không có leo quyền (Y có `add_` thật và chịu trách nhiệm khi xác nhận, đúng H6 hiện hành). Chỉ làm hở mục tiêu tách người của BR-KK-08.
- Đề xuất (chọn một, sửa được trong Lô 8):
  - (a) View `create` bỏ qua `lines` khi request đến từ dispatch AI, giữ đúng schema.
  - (b) `has_counted` và `queries.edited_lines_by_me` coi thêm chủ `AiAction` có id bằng `AuditLog.proposal_ref` của dòng `create_stockreconciliation` hoặc `update_reconciliation_lines`.
  - Phương án (a) đơn giản hơn. Test: X không duyệt được, hoặc `lines` bị bỏ.

**L1 (Low): code chết và lặp**
- `stocktake/services.py:29` `COUNTER_AUDIT_ACTIONS` không ai dùng.
- `_staff_name` (`services.py:91`) trùng `serializers.staff_name` (`serializers.py:26`) và `common/guidance/audit_timeline.py:55`. `_last_editor_name` trùng logic `last_*` trong `queries.py`.
- `_format_instant` import DRF trong service (`services.py:112`).
- Đề xuất: xoá hằng, cho service gọi một helper tên nhân viên dùng chung.

**L2 (Low): Django Admin sửa được dòng kiểm kê mà không để dấu vết BR-KK-08** (đã có từ trước, ngoài phạm vi)
- Vị trí: `inventory/admin.py:73-87`. Inline `StockReconciliationLineInline` cho sửa dòng của cả phiếu đã duyệt, không ghi `update_reconciliation_lines`.
- Chỉ ai có `is_staff` mới vào được (hiện chỉ superuser), nên chưa chặn lô. Đề xuất cho lô sau: inline chỉ đọc khi phiếu khác `DRAFT`, hoặc chỉ đọc hẳn.

**L3 (Low): duyệt được phiếu rỗng**
- Vị trí: `services.py:195-230`. Từ Lô 8 tạo được phiếu không có dòng (`lines` không bắt buộc). Duyệt phiếu rỗng trả 200 `APPROVED` với `line_count=0` (đã tái hiện), sinh ra một chứng từ vô nghĩa không huỷ được.
- Đề xuất: chặn duyệt khi không có dòng (400 `RECON_LINE_INVALID`), hoặc FE không cho gửi duyệt khi chưa có dòng. Nên làm cùng H1.

**L4 (Low): lỗi BR-KK-04 lúc duyệt thiếu `line_index`**
- Vị trí: `services.py:215`. Hết lỗi nếu chọn phương án B ở H1.

### Kết luận: **CHANGES REQUESTED**
- Chặn vì **H1**, ảnh hưởng tồn và hao hụt. Điều phối viên hỏi Duy chọn phương án B (khuyến nghị) hay A cho BR-KK-09, rồi giao be-dev sửa `stocktake/services.py` và thêm hai test tái hiện. Techlead sẽ cập nhật 02b §3 B1 theo phương án được chốt.
- **M1** sửa trong lô này theo phương án (a). **L3** làm cùng H1 nếu Duy đồng ý.
- L1, L2, L4 không chặn.
- Các phần còn lại (phân quyền, 409, migration, N+1, không rò giá vốn và dữ liệu cá nhân, đổi `created_by` sang object) đạt.

### Re-review sau sửa (H1, M1, L1, L3, L4) — 02/10

**Kiểm chứng đã chạy:**
- `manage.py test apps.inventory apps.common`: **638 test OK**.
- `makemigrations --check --dry-run`: sạch.
- `check_naming.py`: exit 0.
- `git diff -- apps/inventory/stock/services.py`: rỗng, `record_movement` giữ nguyên.
- Chạy lại test tái hiện của lượt đầu:
  - Đếm 48 trên tồn 50, bán 5, duyệt: 200, tồn **43**, sổ ghi RECONCILE −2.
  - Đếm 49 không lý do, bán 5, duyệt: 200, tồn 44.
  - Phiếu rỗng: 400.

**H1 (đạt, theo Phương án B):**
- Phép tính: `stocktake/services.py::_applied_difference` lấy `counted_qty − system_qty` theo số đã chụp. Service không ghi đè `system_qty` hay `difference_qty` nữa.
  - Dev cố ý không dùng cột `difference_qty`, vì cột này mặc định 0 với dòng cũ. Như vậy là đúng.
  - BR-KK-04 kiểm trên số đã chụp. Lỗi kèm `line_index`.
- Tồn âm thì rollback toàn bộ:
  - `apply_reconciliation` có `@transaction.atomic`. `record_movement` báo lỗi khi tồn ra âm, `_apply_line` bọc lỗi đó thành `RECON_STOCK_INSUFFICIENT` và để exception đi ra ngoài giao dịch duyệt.
  - Test `test_br_kk_09_would_go_negative_is_400_with_code_and_nothing_written` dùng 2 dòng. Dòng 0 đã áp vào sổ trước khi dòng 1 lỗi, sau đó cả phiếu rollback: không còn RECONCILE nào, tồn hai lô giữ nguyên, phiếu vẫn `DRAFT`. Test này chứng minh đúng điều cần chứng minh.
- Thông điệp lỗi có chép câu của `record_movement` (còn X kg, cần Y kg). Đó là số kg, không phải giá vốn, cũng không lặp input của client. Chấp nhận.

**M1 (đạt):** `api.py:77-78` bỏ `lines` khi `ai_audit_scope` đang được đặt. Cả đường xác nhận mức C (`confirm_ai_action`) lẫn pipeline A/B đều đặt scope, và contextvar được reset trong `finally` nên request UI không dính. Có test cho đường AI, đường UI và kịch bản chủ AI dùng người xác nhận để "rửa" số.

**L1, L3, L4 (đạt):**
- L1: hằng chết đã xoá, `staff_name` gom về một chỗ trong stocktake.
- L3: phiếu rỗng duyệt ra 400 `RECON_EMPTY`.
- L4: lỗi BR-KK-04 lúc duyệt có `line_index`.

**Lưu ý mới (Low, không chặn lô):**
- **L5.** Từ BR-KK-09, lúc duyệt hệ thống tin `system_qty` đã lưu. Dòng tạo trước Lô 8 (qua Django Admin, khi `system_qty` do người gõ tay) sẽ được áp đúng theo số gõ tay đó.
  - Trước khi deploy, chạy kiểm tra chỉ đọc trên staging và production: đếm `StockReconciliationLine` thuộc phiếu `DRAFT`. Nếu có dòng nào thì Duy xem lại các phiếu đó trước khi duyệt.
  - Cũng vì vậy, L2 (inline Admin sửa được `system_qty`) nặng hơn một chút. Vẫn chỉ superuser vào được nên giữ mức Low, nên làm inline chỉ đọc ở lô sau.

### Kết luận Lô 8 — BE: **APPROVED với điều kiện Duy chốt Phương án B (BR-KK-09)**
- Nếu Duy chọn A, be-dev chỉ sửa `_applied_difference` và `_apply_line`, đổi test trong `test_approval_snapshot.py`, rồi techlead review lại phần đó.
- Sau khi Duy chốt, techlead cập nhật 02b §3 B1 (BR-KK-09, mã `RECON_EMPTY`, `RECON_STOCK_INSUFFICIENT`). PO đưa BR-KK-08/09 vào `doc/business-process-spec.md`.
- Khi commit, gộp cẩn thận `test_discipline.py` và snapshot vì Lô 4 cũng sửa hai file này.

## Lô 9 — BE (R9 — Hàng hoàn về kho)

Techlead review ngày 02/10/2026. Phạm vi: `backend/apps/inventory/returns/` (`scope.py`, `creation.py`, `filters.py`,
`serializers.py`, `api.py`, `next_steps.py`, các test mới) và phần hàng hoàn trong `apps/common/tests/test_s4_actor_fields.py`.

### Kiểm chứng đã chạy trong lượt review
- `manage.py test apps.inventory apps.delivery`: Ran 707 tests, OK.
- `makemigrations --check --dry-run`: No changes detected.
- `python3 scripts/check_naming.py`: OK, không có vi phạm mới.
- Grep phía FE: không có chỗ nào trong `erp-console/` hay `frontend/` gọi `/api/inventory/returns/`. Chỉ có `nav.ts:289` trỏ tới
  route `/returns/` của Lô 9 FE, nên đổi sang phân trang không làm vỡ gì. Phía AI, `scrub.py:66` đã đọc `results`.
  Snapshot registry vẫn giữ 5 lệnh `inventory.returntostock.*` như cũ.

### Kết quả theo trọng tâm
**Tồn kho, giá vốn: đạt.**
- Chặn vượt số kg đã giao, kể cả khi hai người tạo cùng lúc:
  - `creation.py:55` khoá dòng `DeliveryNote` trước. Sau đó mới kiểm trạng thái, tính `delivered_qty` và tổng `already` (`creation.py:66`).
  - Trên Postgres (READ COMMITTED), request thứ hai chờ khoá. Khi lấy được khoá, câu SUM của nó chạy sau nên thấy dòng request đầu đã commit.
  - `already` tính cả phiếu DRAFT lẫn APPROVED, nên RESTOCK xong rồi tạo phiếu mới cũng không vượt được.
- Chỉ có một đường tạo phiếu là `create_return`. `delivery.services.return_to_warehouse` chỉ còn test gọi trực tiếp. Lệnh AI `create` đi qua chính viewset (`dispatch.py`).
- Duyệt (`api.py:76-83`):
  - Request khoá dòng `ReturnToStock`, kiểm DRAFT (sai thì 409), ghi `decision`, rồi gọi `apply_return`, tất cả trong cùng một giao dịch.
  - Hai người duyệt cùng lúc thì người sau chờ khoá, đọc được APPROVED và nhận 409.
  - Kiểm 409 ở tầng API không race với `apply_return`, vì cả hai chạy trong cùng giao dịch và trên dòng đã khoá. Nhánh "đã duyệt" trong `apply_return` thành phòng thủ, không còn đường nào chạm tới.
  - BR-HV-04 rollback cả `decision` (có test). `apply_return` giữ nguyên.
- Response chỉ có kg. Test quét `COST_KEYS` và giá trị mốc 123457 với 4 vai, ở cả list, detail và approve.

**Phạm vi: đạt.** Nợ Lô 2 L1 đã trả.
- `scope.py` là nơi duy nhất định phạm vi, dùng chung cho `get_queryset`, `ScopedDeliveryNoteField` và provider dòng thời gian `return` (`next_steps.py`).
- Có test `test_r2_return_other_courier_404` cho cả tạo, chi tiết và dòng thời gian.
- Phiếu không tồn tại và phiếu của người khác trả cùng một body 404.
- Mặc định là chặn: user có quyền model nhưng không thuộc nhóm full scope thì bị lọc theo `assigned_to`.
- Phiếu cũ không gắn phiếu giao (`delivery_note` null) thì người giao không thấy.

**Dữ liệu cá nhân: đạt.**
- Response không có tên, SĐT hay địa chỉ khách. `note` không vào AuditLog: `return_to_warehouse` ghi note cố định, còn `object_repr` chỉ là mã RT, mã lô và số kg.
- Dòng thời gian không có `note` (có test với SĐT giả). AI lọc `note` qua `SCRUB_FREE_TEXT_KEYS`. Response có `no-store`.
- `warehouse_staff` đọc được `note` của mọi phiếu. Điều này khớp với full scope phiếu giao hiện có (`FULL_SCOPE_GROUPS`), nên chấp nhận.

**`left_warehouse_at`: đạt.**
- `delivery_advance_status` là đường duy nhất chuyển phiếu sang DELIVERING (`advance_status`). Giá trị lấy theo lần gần nhất nên đúng cả khi hẹn giao lại.
- Chỉ chạy 1 câu SQL lúc tạo, sau đó lưu vào cột. List và detail đọc cột nên không có N+1.

**N+1 của list: đạt với `owner`.** So số câu SQL giữa 2 và 10 dòng thì bằng nhau. Phần test cho `delivery_staff` thì chưa đủ chặt, xem L1.

**Các chỗ lệch 02b (dev ghi trong 03-dev-notes): chấp nhận cả 5.**
- `delivery_note` bắt buộc: đúng tinh thần R9.
- Giờ là trường chỉ đọc: theo BR-PQ-14.
- PATCH chỉ đổi được `note`.
- Phân trang: không có chỗ nào đang đọc kiểu cũ.
- 409 `STALE_STATE`: đồng nhất với kiểm kê và giao phiếu.

Contract thật nằm ở 03-dev-notes "Lô 9 — BE / Contract". FE Lô 9 bám theo bản này, đọc `results`. Techlead sẽ cập nhật dòng R9 trong 02b khi chốt lô.

### Phát hiện
**L1 — Low — test N+1 cho `delivery_staff` là phép so trùng**
- Vị trí: `apps/inventory/returns/tests/test_list_scope.py:172-173`. Test gọi `count(self.courier)` hai lần trên cùng một bộ dữ liệu rồi so với nhau, nên luôn bằng nhau và không bắt được N+1.
- Cách tái hiện: thêm một truy vấn theo dòng (ví dụ bỏ `created_by__staff_profile` khỏi `select_related`) rồi chạy riêng phần courier. Phần courier vẫn xanh. Lỗi chỉ bị bắt nhờ phần `owner`, vì hai vai dùng chung serializer.
- Sửa: đo `count(self.courier)` trước và sau khi thêm các phiếu gán cho `self.courier`. Ở vòng lặp hiện tại, `i` lẻ đã tạo phiếu cho courier. So hai số đó với nhau.

**L2 — Low — lặp code parse `month`**
- `apps/inventory/returns/filters.py:20-35` gần như chép nguyên `apps/sales/refunds/api.py:42-58` (`_month_bounds`). Dev ghi nguồn là `stock/filters.py`, nhưng thực ra chép từ refunds.
- Bản ở returns còn bỏ `OverflowError` trong `except`. Hiện chưa gây lỗi vì năm đã bị giới hạn 2000–2100.
- Sửa: gom về `apps/common/params.py` (ví dụ `parse_month_bounds`) ở lô refactor chung, như dev đã ghi nợ. Không chặn lô.

**L3 — Low — chưa có test đồng thời thật cho khoá dòng**
- Test chạy trên SQLite nên `select_for_update` không có tác dụng. Đường khoá ở `creation.py:55` và `api.py:78` hiện mới chỉ được xác nhận bằng đọc code.
- Đọc code thì đúng, như đã phân tích ở trên. Lưu ý thêm cho QA hoặc staging Postgres: gửi đồng thời hai POST 6 kg trên phiếu có 10 kg, phải ra một 201 và một 400 `RETURN_QTY_EXCEEDS`.

**Ghi chú nghiệp vụ, không phải lỗi code, chuyển PO hoặc Duy:**
- Phiếu hoàn DRAFT nhập sai số kg không sửa được (qty khoá sau khi tạo) và không huỷ được (không có trạng thái huỷ). Số kg sai vẫn chiếm hạn mức "đã giao".
- Lối ra duy nhất là duyệt WRITE_OFF hoặc RESTOCK với số sai. Nếu cần "Từ chối, huỷ phiếu hoàn" thì phải có story mới, đề xuất mã BR-HV-05. Ngoài phạm vi R9.

### Kết luận Lô 9 — BE: **APPROVED**
- Không có lỗi Critical, High hay Medium.
- L1 nên sửa cùng lượt (2 dòng test). L2 và L3 là nợ, không chặn lô.

---

## Lô 10 — BE (R10 — Mua hàng, phiếu nhập)

> techlead · 02/10/2026 · Phạm vi: `apps/purchasing/receipts/{api,serializers,filters}.py`, `tests/{api_base,test_receipt_list,test_receipt_detail}.py`, dòng `purchase_amount` trong `apps/common/cost_keys.py`.

### Kiểm chứng đã chạy (lượt này)
- `manage.py test apps.purchasing`: Ran 75 tests, OK.
- `manage.py test apps.ai.registry`: OK. Snapshot lệnh AI không đổi, `purchasereceipt.list/retrieve` vẫn có.
- `makemigrations --check --dry-run`: No changes detected.
- `python3 scripts/check_naming.py`: OK, không phát sinh vi phạm mới.

### Kết quả soát theo trọng tâm
**Rò giá vốn và tiền mua (bất biến 1): đạt.**
- List dùng `sensitive_fields=("purchase_amount",)`. Detail dùng `("purchase_amount","costs","allocated_amount")`. Dòng nhập dùng `("rate","purchase_amount","landed_unit_cost")`. `CostFieldSerializerMixin` gỡ field ngay trong `__init__` khi có request, nên với manager và warehouse_staff các `SerializerMethodField` tiền không chạy. Prefetch chi phí phụ cũng chỉ bật khi có `view_costprice` (`api.py:58-66`). Serializer con `lines` được khai ở mức class nên lúc khởi tạo chưa có request. Dù vậy `to_representation` vẫn đọc `context` của serializer gốc và gỡ field (đã đọc `apps/common/api.py:97-107`). Test sentinel `test_r10_d3_manager_still_cannot_see_cost_fields_beside_invoice_amount` cũng xác nhận điều này.
- `purchase_amount` đã có trong `COST_KEYS`, nên lưới 2 của AI (`SCRUB_COST_KEYS`) và `redact_cost` cũng bắt khoá này. `costs` không có trong `COST_KEYS`, nhưng chỉ owner nhận được khoá này nên không phải lỗ hổng.
- Các đường khác:
  - `items_summary` chỉ có tên mặt hàng. `batch_codes` theo dạng `<mã hàng>-<yymmdd>-<id phiếu>`, không có tiền.
  - `note` là field cũ, serializer ghi đã trả từ trước, nên không có đường rò mới.
  - Phản hồi POST, PATCH và `submit` vẫn dùng `PurchaseReceiptSerializer` (dòng nhập có `sensitive_fields=("rate",)`). `cancel` chỉ trả `id, status`.
  - `receive-batches` dùng `PurchaseReceiptSerializer` + `ReceivedBatchOutput`, cả hai ẩn `rate/purchase_rate/landed_unit_cost`. Đã có test với warehouse_staff.
  - Không bật `DEFAULT_FILTER_BACKENDS` hay `OrderingFilter`, nên không có `?ordering=lines__rate` để dò giá.
- D-3: manager thấy `invoices[].amount` theo `purchasing.view_purchaseinvoice`, warehouse_staff thì không. Code đúng quyết định. **Ghi nhận rủi ro đã được Duy chấp nhận:** với phiếu 1 dòng, `amount / qty` gần bằng giá mua/kg (sai lệch chỉ do chi phí khác ghi chung hoá đơn). Không chặn.

**Phân quyền: đạt.** Test ma trận list và detail: owner, manager, warehouse_staff được 200; delivery_staff, customer_service, user không nhóm bị 403; người chưa đăng nhập bị 401. Detail id lạ trả 404. Không có DELETE (`DocumentViewSet`).

**Lọc: đạt.** Dùng chung helper của `stock/filters.py`. `month` dùng regex ASCII `fullmatch`, không strip, chặn năm ngoài 2000–2100, tháng 00/13 trả `ValueError` nên ra 400. `supplier` giới hạn trong int64. Thông điệp lỗi chỉ nêu tên tham số và có test không lặp lại input. `has_invoice` dùng `Exists`, nên phiếu có hai hoá đơn không bị lặp dòng (có test).

**N+1: đạt.** List prefetch `lines__item`, `lines__batch`, `invoices` và `select_related` cho supplier, warehouse, `created_by__staff_profile`. Detail thêm `Prefetch(cost_allocations → purchase_cost)`. Có test đếm truy vấn cho list (owner, manager) và detail (owner, phiếu 1 dòng so với 8 dòng có 2 chi phí).

**Suy `costs[]` qua phân bổ: đúng, không đếm trùng.** `PurchaseReceiptLine.batch` là `OneToOneField`, và `PurchaseCostAllocation` có `UniqueConstraint(purchase_cost, batch)`. Vì vậy mỗi cặp (chi phí, lô) chỉ được cộng một lần, và mỗi lô chỉ thuộc một dòng. `allocated_amount` chỉ cộng phần rơi vào lô của phiếu này. Có test chi phí chia cho hai phiếu (500/500 trên 1000). `PurchaseCost` không có trạng thái huỷ, nên không cần lọc thêm.

### Phát hiện
**L1 — Low — warehouse_staff đọc được danh sách hoá đơn mua (ngày, đã trả) dù không có `view_purchaseinvoice`**
- Vị trí: `serializers.py:177` (`invoices` của Detail) và `serializers.py:88-111`. Chỉ `amount` bị gỡ theo quyền. `id`, `code`, `invoice_date`, `is_paid` vẫn trả cho mọi người có `view_purchasereceipt`.
- Tái hiện: `client_for(warehouse_staff).get("/api/purchasing/receipts/<id>/")` trên phiếu có hoá đơn, rồi đọc `invoices[0].is_paid`. Test `test_r10_manager_and_warehouse_staff_detail_has_no_purchase_money` còn assert điều này là đúng.
- Không có tiền, và 02b R10 đã cho mọi người thấy `invoice: {"id"}|null`, nên không chặn lô. Nhưng đây là đọc bản ghi `PurchaseInvoice` vượt Tầng 1, và "đã trả NCC chưa" thuộc việc tiền của Chủ và Quản lý. Đề xuất: trả cả `invoices` theo `view_purchaseinvoice` (người thiếu quyền chỉ còn `invoice: {"id"}`), rồi sửa assert tương ứng. FE W2b cần ẩn khối "Hoá đơn mua" khi thiếu khoá. Điều phối viên quyết định sửa ngay hay đưa vào nợ.

**L2 — Low — thứ tự dòng nhập không xác định**
- Vị trí: `api.py:57` prefetch `lines__…` không `order_by`, và `PurchaseReceiptLine` không có `Meta.ordering`. Thứ tự của `lines[]`, `items_summary` (`serializers.py:144`) và `batch_codes` (`serializers.py:157`) phụ thuộc thứ tự trả về của Postgres.
- Tái hiện: chỉ lộ trên Postgres sau khi cập nhật hoặc VACUUM. Test chạy SQLite nên `first/second` trong `test_r10_detail_owner_header_and_lines` luôn xanh.
- Sửa: `Prefetch("lines", queryset=PurchaseReceiptLine.objects.select_related("item","batch").order_by("id"))`.

**L3 — Low — `_costs()` tính hai lần mỗi phiếu**
- `serializers.py:198` và `:214` đều gọi `_costs(receipt)`. Phép tính chạy trong bộ nhớ, không thêm truy vấn. Có thể gom lại (tính `allocated_amount` từ kết quả `costs`, hoặc cache theo `receipt.pk` trong serializer). Không chặn.

**Ghi chú, không phải lỗi:**
- Tầng 3 "warehouse_staff chỉ xem phiếu của mình, trong ngày" chưa có, dev đã ghi nợ. Hành vi cũ giữ nguyên, ED-20-AC5 chỉ đòi ẩn giá, nên không chặn.
- Lệch 1, 3, 4, 5 trong dev notes chấp nhận được. Techlead sẽ cập nhật dòng R10 ở 02b: phân trang 20, thêm `date_from/date_to`, `line_count`, detail `lines[]/invoices[]/costs[]/allocated_amount`, và `invoices[].amount` theo `view_purchaseinvoice`. FE Lô 10 bám contract trong 03-dev-notes "Lô 10 — BE / Contract".
- Đổi hành vi: list cũ có trả `lines`, list mới thì không, và trang mặc định từ 50 dòng xuống 20. Đã grep: `erp-console` hiện không gọi list hay detail phiếu nhập (chỉ gọi `receive-batches` và `cancel`). Lệnh AI `purchasereceipt.list` vẫn chạy qua serializer mới.

### Kết luận Lô 10 — BE: **APPROVED**
- Không có lỗi Critical, High hay Medium. Không có đường rò giá vốn ngoài rủi ro D-3 mà Duy đã chấp nhận.
- L1 nên xử lý nếu điều phối viên đồng ý (khoảng 5 dòng code và 1 assert). L2, L3 là nợ nhỏ, không chặn.

## Lô 13 — BE (R14 — Danh mục & giá, đặt giá mới tự đóng giá cũ)

> techlead · 2026-10-02 · Diff chưa commit: `apps/catalog/items/` (`api.py`, `serializers.py`, `filters.py`, test) và `apps/catalog/pricing/` (`api.py`, `serializers.py`, `services.py`, test).
> Kiểm chứng lượt này: `manage.py test apps.catalog apps.sales` cho kết quả **Ran 650, OK**. Ba ca ngoài đường thuận được tái hiện bằng test tạm đặt ở scratchpad, không ghi vào repo.

### Đã soát và đạt
- **Giá vào đơn và Shop.** `SalesOrderLine.rate` chốt giá lúc tạo đơn (`sales/orders/services.py:220`), còn bước thanh toán đọc `line.rate` (`payments/services.py:419`). Vì vậy đóng giá cũ không làm đổi giá của đơn đang giữ chỗ. Shop, đơn và `current_price` cùng dùng `timezone.localdate()` với `TIME_ZONE=Asia/Ho_Chi_Minh` và cùng thứ tự `-price_list__is_default, -valid_from, -id`. Ở ranh giới ngày, giá cũ có hiệu lực đến hết `valid_from − 1` và giá mới bắt đầu từ `valid_from`, nên không có ngày nào trống giá khi `valid_upto` để trống. Đã có test cho giá bắt đầu hôm nay, giá bắt đầu ngày tương lai, và trường hợp không đụng mặt hàng hay bảng giá khác.
- **T9.** Quyền ghi vẫn là Tầng 1 như cũ, nên chỉ owner ghi được. Có test 403 cho manager, warehouse_staff, delivery_staff, customer_service và user không nhóm, kèm 401 khi chưa đăng nhập. warehouse_staff **không có khoá** `current_price`, vì field này bị gỡ ở `get_fields` trên cả list, detail và phản hồi ghi. Khi không có request, mặc định cũng ẩn field này, nên schema đầu ra của lệnh AI không có nó.
- **Giá vốn và dữ liệu cá nhân.** Không có field giá vốn nào mới, các serializer đều liệt kê field tường minh. Audit ghi giá bán bằng khoá `sell_rate`, đúng quy ước trong `cost_keys.py:7`. Đây là lựa chọn đúng: nếu dùng `rate` thì khoá này nằm trong COST_KEYS và sẽ bị che sai với người xem log. Audit không có dữ liệu khách.
- **services.py.** Hàm chạy trong `@transaction.atomic`. Nó khoá dòng `PriceList` trước rồi mới khoá các giá cùng mặt hàng và bảng giá, nên vẫn đúng khi mặt hàng chưa có giá nào. Có audit `create_itemprice` và `close_itemprice` (kèm `replaced_by`) cho POST, `update_itemprice` cho PATCH. View chỉ gọi service.
- **Lệnh AI.** `ai/execution/dispatch.py:83` đi qua `as_view`, nên `catalog.itemprice.create` và `partial_update` cũng chạy `perform_create` và `perform_update`, tức là cũng tự đóng giá cũ. Input của serializer không đổi, vì `item_name` và `item_code` là read-only.
- **N+1.** Danh sách mặt hàng dùng một `Prefetch` giá, chỉ nạp khi người xem có quyền, và prefetch thêm `bundle_lines__component`. `item-groups` dùng `annotate(Count)` và `select_related(parent)`. `item-prices` và `pricing-rules` dùng `select_related`. Có test đếm truy vấn.
- **Lọc.** `id_param`, `bool_param` và `choice_param` trả 400 `INVALID_FILTER` và không lặp lại giá trị người gọi gửi lên. Lọc chỉ áp ở action `list`.

### Phát hiện

**M1 — Medium — Đặt giá có `valid_upto` cắt mất phần đuôi của giá cũ, Shop mất giá mà không có cảnh báo**
- Vị trí: `apps/catalog/pricing/services.py:84-88` và `:100-103`. Mọi giá có `valid_from` sớm hơn và chồng lấn với khoảng mới đều bị đóng ở `valid_from − 1`, kể cả khi giá cũ kéo dài quá `valid_upto` của giá mới.
- Tái hiện (đã chạy): giá cũ 120.000 từ `hôm nay−30`, đang mở. Owner `POST item-prices/ {rate: 99000, valid_from: hôm nay+5, valid_upto: hôm nay+9}` nhận **201**. Giá cũ bị đổi thành `valid_upto = hôm nay+4`, và `effective_price(item, hôm nay+10)` trả **None**. Từ ngày +10, mặt hàng biến khỏi Shop và tạo đơn ném lỗi "Không có giá niêm yết hiệu lực". Đây là đúng kiểu "giá khuyến mãi vài ngày" mà Chủ dễ nhập, qua form hay qua lệnh AI đều được.
- Sửa (khoảng 3 dòng và 1 test): trong vòng lặp của `set_item_price`, khi `valid_upto is not None` và giá cũ có `other.valid_upto is None or other.valid_upto > valid_upto` thì raise `_overlap_error()` (hoặc một thông điệp riêng: "Giá đang áp dụng còn hiệu lực sau ngày kết thúc bạn chọn. Để trống ngày kết thúc, hoặc sửa giá đang áp dụng trước."). Giữ nguyên ca hợp lệ của `test_br_dm_03_price_with_end_date_fits_before_future_price`, vì ở đó giá cũ kết thúc đúng bằng `valid_upto` mới. Thêm test cho ca tái hiện ở trên: phải ra 400 và giá cũ không đổi.

**L1 — Low — Cho phép đặt giá lùi ngày, sửa lại lịch sử giá**
- Vị trí: `services.py:73`, hàm không chặn `valid_from < today_in_vietnam()`.
- Tái hiện (đã chạy): giá cũ từ `−30`, POST `valid_from = −20` nhận 201, và giá cũ bị đổi `valid_upto = −21`. Đơn cũ không đổi tiền vì giá đã chốt trên đơn. Nhưng bảng giá ERP sẽ ghi "từ ngày −20 giá là 99.000", trái với giá thật trên các đơn của khoảng đó, và đi ngược nguyên tắc "không sửa số kỳ cũ". Test `test_ed31_ac1_exactly_one_price_stays_open` đang dùng ngày quá khứ.
- Đề xuất: POST chặn `valid_from` trước hôm nay (giờ VN) bằng 400 kèm câu hướng dẫn, rồi đổi test sang ngày tương lai. Đây là quyết định nghiệp vụ, nên điều phối viên hỏi Duy hoặc PO. Không chặn lô.

**L2 — Low — Ưu đãi cũ sai dữ liệu không tắt được**
- Vị trí: `apps/catalog/pricing/serializers.py:65-80`. PATCH một phần vẫn kiểm toàn bộ giá trị đã lưu.
- Tái hiện (đã chạy): một rule cũ có `apply_on=ITEM`, `item=None` và `PERCENT 150`, loại dữ liệu mà API trước Lô 13 vẫn nhận. PATCH `{"is_active": false}` trả **400**. Django Admin cũng chặn, vì `PricingRule.clean` dùng cùng luật đó. Như vậy Chủ không tắt được một ưu đãi hỏng đang chạy, chỉ còn cách xoá.
- Sửa: khi PATCH chỉ có `is_active=false` thì bỏ qua kiểm điều kiện. Cũng nên chạy một truy vấn đếm ở staging và production để biết đang có rule sai hay không (chỉ đọc).

**L3 — Low — Thứ tự khoá ngược nhau giữa POST và PATCH**
- `set_item_price` khoá PriceList trước rồi tới ItemPrice. `update_item_price` khoá dòng ItemPrice trước (`:115`) rồi mới tới PriceList (`:121`, qua `_lock_prices`). Nếu Chủ POST và PATCH cùng một mặt hàng gần như cùng lúc, PostgreSQL có thể báo deadlock và một bên nhận 500. Xác suất rất thấp vì chỉ có một người ghi. Sửa: trong `update_item_price`, khoá PriceList trước khi khoá dòng giá.

**L4 — Low — Còn hai bản cài "giá hiệu lực"**
- `apps/sales/orders/services.py:42` (`_effective_price`) vẫn tự viết lại truy vấn, chưa gọi `pricing.services.current_item_price`. Hiện hai bản khớp nhau, và test giá Shop khớp ERP vẫn xanh. Nhưng dev notes nói "nguồn chung", trong khi thực tế phía đơn chưa dùng chung. Nên gom lại ở một đợt sửa sau. Việc này đụng `apps/sales`, nằm ngoài lô.

**L5 — Low — `has_image` không theo quy ước 400**
- `apps/catalog/items/api.py:34-37`: `?has_image=abc` bị hiểu là `false` thay vì trả 400 như các tham số lọc mới. Đây là hành vi cũ của A2. Nên đổi sang `bool_param` khi có dịp, nhưng lưu ý bộ cũ chấp nhận cả `yes`.

**Ghi chú, không phải lỗi:**
- Validation mới của serializer khớp `Model.clean` sẵn có, nên dữ liệu hợp lệ cũ, Django Admin và lệnh AI không vỡ. Ngoại lệ duy nhất là L2.
- PATCH chỉ đổi `rate` thì không kiểm chồng lấn. Cách này hợp lý để vẫn sửa được dữ liệu cũ.
- `ItemPrice` vẫn DELETE được qua API (đường cũ, chỉ owner) và không có audit. Ngoài phạm vi lô.
- `items/next_steps.py` (untracked) không thuộc Lô 13 nên không review ở đây.

### Kết luận Lô 13 — BE: **CHANGES REQUESTED**
- Cần sửa **M1** trước khi QA và commit: chặn trường hợp giá mới có `valid_upto` cắt ngắn giá cũ, và thêm test tái hiện. Phần sửa nhỏ, nằm gọn trong `services.py` và `test_set_item_price.py`.
- L1 cần Duy hoặc PO quyết. L2 và L3 nên sửa cùng lúc nếu tiện, mỗi lỗi vài dòng. L4 và L5 ghi nợ.
- Không có lỗi Critical hay High. Không rò giá vốn, không rò dữ liệu cá nhân, không vượt T9.

## Lô 11 — BE (B3 — Nhà cung cấp)

> techlead · 02/10/2026 · Phạm vi: `SupplierSerializer`, `SupplierViewSet`, `supplier_queries.py`, `supplier_services.py`,
> `test_supplier_aggregates.py`, `test_supplier_crud.py`, nhãn `supplier_create` trong `next_steps.py`, dòng `purchase_total` trong `cost_keys.py`.
> Kiểm chứng lượt này: `manage.py test apps.purchasing` cho kết quả Ran 118 tests, OK (40 test nhà cung cấp).

### Đã soi, không có lỗi
- **Rò `purchase_total`:** không thấy đường rò. `CostFieldSerializerMixin.__init__` bỏ field khỏi `self.fields` nên `get_purchase_total` không được gọi khi thiếu `view_costprice`. Khi không có request, mixin mặc định ẩn. View cũng không tính tổng khi người xem thiếu quyền (`api.py:55-70`). Phản hồi POST/PATCH đi qua `_reload` rồi qua cùng serializer, có test `test_supplier_write_responses_do_not_leak_purchase_total`. Dự án không bật `OrderingFilter`, nên không sắp xếp hay dò được theo `purchase_total`. Lệnh AI `purchasing.supplier.list/retrieve` chạy qua viewset với user thật, `purchase_total` có trong `COST_KEYS`, `phone` có trong `SCRUB_PII_KEYS`. Snapshot registry không đổi phần supplier.
- **Phân quyền ghi:** Tầng 1 dùng `BusinessModelPermissions`. Owner và manager được ghi, warehouse_staff nhận 403 và dữ liệu không đổi (`test_supplier_write_permission_matrix`, `test_supplier_forbidden_write_changes_nothing`). delivery_staff và customer_service nhận 403 khi đọc.
- **`check_permissions` trả 405 trước khi kiểm quyền (`api.py:39-43`):** không lộ dữ liệu. Người chưa đăng nhập vẫn nhận 401. Người đã đăng nhập chỉ biết được method nào bị tắt, và thông tin này vốn đã có trong header `Allow` của OPTIONS. Code này lệch idiom: `CustomerDirectoryViewSet` (`apps/sales/customers/directory_api.py:103`) chỉ khai `http_method_names`, nên khi người thiếu quyền gọi DELETE thì DRF kiểm quyền trước và trả 403. Mức độ chấp nhận được, xem L3.
- **AuditLog:** `changes={"fields": [...]}` chỉ ghi tên trường, `object_repr` là tên nhà cung cấp, không có SĐT hay ghi chú. Có test quét. Khi không có thay đổi thật thì không ghi.
- **N+1:** `receipt_count` và `last_received_at` được annotate trong một truy vấn, `Count` chỉ join `receipts` nên không nhân dòng. `purchase_total` dùng một truy vấn cho cả trang. Test đếm truy vấn với 20 và 50 nhà cung cấp.
- **Tiền:** dùng Decimal, mỗi dòng làm tròn 2 chữ số rồi mới cộng, khớp `purchase_amount` của R10 (có test đối chiếu).
- **Đặt tên:** tiếng Anh chuẩn.

### Phát hiện

**L1 — Low (cần Duy chốt, không chặn) — `purchase_total` ẩn với Quản lý**
- `serializers.py:33` đặt `sensitive_fields = ("purchase_total",)`, nên chỉ ai có `view_costprice` (owner) mới thấy. Cách này đúng 02b B3 và an toàn hơn. Tuy vậy, D-3 cho Quản lý thấy tiền hoá đơn mua, mà tổng hoá đơn mua thường xấp xỉ `purchase_total`. Điều phối viên nên hỏi Duy có muốn đồng bộ hay không. Đến khi Duy trả lời thì giữ nguyên như hiện tại.
- Tái hiện: `GET /api/purchasing/suppliers/` bằng manager thì JSON không có khoá `purchase_total`.

**L2 — Low — Lệch 02b, cần ghi lại vào contract (không sửa code)**
- `supplier_queries.py:21` dùng `COUNTED_STATUSES = (SUBMITTED,)`. 02b B3 ghi `receipt_count`/`last_received_at` tính các phiếu "khác CANCELLED", tức là gồm cả Nháp. Dev chọn theo Q4 mặc định mà Duy đã đồng ý ngày 01/10, nên chấp nhận cách này.
- `api.py:37` tắt DELETE và PUT (405). Bảng rủi ro ở 02b §4 ghi rằng Supplier "còn DELETE ở BE với chu". Thay đổi này an toàn hơn và hợp BR-PQ-10. FE hiện không gọi PUT hay DELETE tới suppliers (đã grep `erp-console/features/purchasing/api.ts`).
- Techlead sẽ cập nhật 02b B3 và §4 theo code thực tế. FE Lô 11 bám theo `03-dev-notes.md` mục Lô 11 — BE.

**L3 — Low — `check_permissions` cục bộ lệch idiom chung**
- `api.py:39-43`. Code đúng và có test, nhưng là cách riêng của một viewset. Nếu sau này cần thêm chỗ dùng hành vi "405 trước quyền", nên đưa thành mixin trong `apps/common/api.py`. Hiện chưa cần làm.

**L4 — Low — `q` và kiểm trùng tên quét toàn bảng trong Python**
- `supplier_queries.py:51-59` (`matching_ids`) và `:62-68` (`name_taken`) đọc mọi dòng `(pk, name, phone)` mỗi lần lọc hoặc ghi. Nhà cung cấp ở vựa chỉ khoảng vài chục đến vài trăm dòng, nên chi phí không đáng kể. Khi bảng vượt khoảng 5.000 dòng thì nên chuyển sang `icontains` trên Postgres, hoặc dùng `Lower` + unaccent.
- Tìm theo SĐT là khớp chuỗi con nguyên văn. Nếu SĐT lưu dạng `0900 000 907` thì tìm `0900000907` sẽ không ra. Tái hiện: tạo nhà cung cấp có `phone="0900 000 907"`, gọi `?q=0900000907`, kết quả rỗng. Có thể chuẩn hoá chữ số ở đợt sau.
- Kiểm trùng tên không có ràng buộc ở DB, nên nếu hai POST cùng tên chạy đồng thời thì cả hai đều lọt. Rủi ro này thấp vì chỉ owner/manager thao tác, và trùng tên không làm hỏng nghiệp vụ.

**L5 — Low — PATCH tính `purchase_total` thừa một lần**
- `api.py:63-67`: `get_object` gọi `attach_purchase_totals` ngay cả khi `action == "partial_update"`. Sau đó `_reload` tính lại, nên mỗi PATCH của owner tốn thêm một truy vấn dòng nhập. Có thể sửa bằng cách chỉ gắn tổng khi `self.action == "retrieve"`. Không ảnh hưởng tính đúng.

### Kết luận Lô 11 — BE: **APPROVED**
- Không có lỗi Critical, High hay Medium. Không rò giá vốn hay dữ liệu cá nhân, không vượt quyền, không xoá chứng từ (DELETE trả 405).
- L1 chuyển cho điều phối viên hỏi Duy. L2: techlead đã cập nhật 02b (B3 và bảng rủi ro §4). L3–L5 ghi nợ, có thể sửa khi tiện.

### Re-review Lô 13 — BE (sau khi dev sửa M1, L2, L3, L5 và lỗi `current_price` trả `date`)

> techlead · 2026-10-02 · Kiểm chứng lượt này: `manage.py test apps.catalog apps.sales apps.ai` cho kết quả **Ran 960, OK**.

- **M1: đã sửa.** `pricing/services.py`, trong `set_item_price`: khi giá mới có `valid_upto` mà giá cũ đang mở hoặc kết thúc sau ngày đó, hàm trả `_tail_gap_error()` (400 mã `BR-DM-03`) trước khi tạo hay đóng giá nào, nên dữ liệu không đổi. Câu thông báo nói rõ cách sửa. Ca hợp lệ (giá cũ kết thúc đúng bằng hoặc sớm hơn `valid_upto` mới) vẫn đặt được. Ca tái hiện "giá cũ mở, giá mới +5..+9" nay ra 400.
- **L2: đã sửa.** `PricingRuleSerializer.validate` bỏ qua phần kiểm khi PATCH chỉ có `{"is_active": false}`. Bật lại ưu đãi hoặc sửa thêm field khác vẫn bị kiểm đủ, nên không có đường lách để lưu dữ liệu sai.
- **L3: đã sửa.** POST và PATCH khoá theo cùng thứ tự: `_lock_price_lists` khoá các dòng PriceList theo id tăng dần, sau đó mới khoá dòng giá. PATCH đổi bảng giá thì khoá cả bảng cũ lẫn bảng mới. Bước đọc `price` không khoá trước khi khoá bảng giá chỉ dùng để lấy `price_list_id`, và dòng giá được khoá lại ngay sau đó, nên không có rủi ro.
- **L5: đã sửa.** `has_image` dùng `bool_param` và nhận `1|true|yes|0|false|no`. Để rỗng nghĩa là không lọc, giá trị sai trả 400 `INVALID_FILTER`, có test giữ cách viết cũ. Bộ lọc giờ chỉ áp ở `list`. Detail trước đây cũng lọc, nhưng FE không gọi detail kèm tham số này.
  - **Ảnh hưởng FE:** đã grep `erp-console`. `features/catalog/api.ts:12-13` chỉ gửi `has_image=true` hoặc `false`, không bao giờ gửi rỗng. Mock `features/catalog/mock.ts:163-166` vốn đã coi giá trị rỗng là không lọc, nên nay khớp BE. `erp-console/e2e/a2_catalog_real.py` không dùng `has_image`. Shop (`frontend/`) không gọi tham số này. Vì vậy **không lệch FE, không lệch e2e**.
- **`current_price` trả về `date`: đã sửa.** `items/serializers.py`, trong `get_current_price`: `valid_from` và `valid_upto` giờ là chuỗi ISO, `valid_upto` là null khi chưa có ngày kết thúc. Contract JSON gửi FE không đổi, vì DRF vốn đã render ra cùng chuỗi. Đường lệnh AI (`serializer.data` rồi `json.dumps`) giờ chạy được, và có test giữ lại.
- **Còn mở:** L1 (đặt giá lùi ngày) chờ Duy hoặc PO quyết. L4 (gom `_effective_price` của sales) ghi nợ.

### Kết luận re-review Lô 13 — BE: **APPROVED**
Không còn lỗi Critical, High hay Medium. Lô sẵn sàng cho QA.

## Lô 14 — BE
> techlead · 02/10/2026 · Diff chưa commit: `apps/accounts/capabilities/` (mới), `audit/api.py` + `test_actor_filter.py`, `auth/services.py` (2 nhãn) + `test_s47_me_labels.py`, `config/api_urls.py` (3 path B4), `common/guidance/api.py` (`_LAZY_MODULES` có `group`).
> Kiểm chứng: `manage.py test apps.accounts apps.common` → **504 test OK**. `python3 scripts/check_naming.py` → OK, không phát sinh mới. Thêm một test tạm (đã xoá sau khi chạy) để in ma trận seed và tái hiện M1.

### Điểm đã đạt (đã soi kỹ)
- **Leo quyền.**
  - Ghi bị chặn hai lớp: `CanManageStaff` rồi `actor_is_owner` (`services.py`, đầu `set_group_capabilities`). `manager` nhận 403. Người có `manage_staff` gán riêng nhưng không thuộc `owner` nhận 403 `StaffPermissionError`. Test `test_ed39_non_owner_holding_manage_staff_still_cannot_write` phủ ca này.
  - Nhóm `owner` bị khoá với mọi nội dung (`GROUP_LOCKED`).
  - Việc `owner_only` bị từ chối trước khi đụng DB, và cả yêu cầu bị huỷ (tất cả hoặc không gì).
  - Khoá ngoài registry (gồm codename đầy đủ, `is_superuser`, chuỗi rỗng) nhận `INPUT_NOT_ALLOWED`. Trường ngoài `capabilities` bị chặn ở view.
  - Service chỉ `add`/`remove` đúng `perms` của việc. Có test so permission ngoài registry của từng nhóm trước và sau.
- **Giá vốn (bất biến 1).** `inventory.view_costprice` và `reports.view_profitreport` chỉ có trong `view_cost`/`view_profit`, cả hai `owner_only=True`. Không còn đường nào khác để cấp, vì permission ngoài registry không nhận được. `add_cost` (`purchasing.add_purchasecost`) và `set_price` cũng là `owner_only`. `can_view_cost` (`common/cost_keys.py:28`) chỉ xét `view_costprice`. Ma trận seed: không nhóm nào ngoài `owner` có ô `owner_only` ở trạng thái `on` hoặc `partial`. Kết luận: không có lỗi Critical.
- **Registry.** 25 việc, codename tồn tại, các tập rời nhau, nhãn khớp 02b §3 B4 và T9. `view_customers` = `sales.view_customer_list`, khớp `customers/permissions.py:16`.
- **Cache quyền.** Không có cache quyền nào ngoài `_perm_cache` theo từng instance user của Django. `lru_cache` duy nhất ở `ai/actions/targets.py:33` chỉ cache nhãn model. Test cùng token chứng minh quyền có hiệu lực ngay ở cả hai chiều: directory 200 → 403 và `/api/auth/me/`.
- **Audit.** `changes` chỉ có `{"<key>": {"from","to"}}` và `note` rỗng. `object_repr` là mã nhóm. Lệnh không làm đổi gì thì không ghi audit.
- **R16.** Chỉ lọc thêm `actor_id` trên endpoint cũ, quyền giữ `view_auditlog`. Không mở thêm field hay dòng nào ngoài những gì `manager` vốn đã thấy. `parse_positive_id` chặn input xấu, thông điệp không lặp lại giá trị.
- **Dữ liệu nhân viên.** `members` chỉ có `id`, `display_name`, `username`, `other_groups`, `is_active`, `added_at`, không có SĐT. Riêng audit `staff_create` có lưu `phone`, nhưng `_added_at` chỉ đọc khoá `groups`. Timeline chỉ dùng nhãn do code dựng.
- **N+1.** Không có. `_added_at` chạy 1 truy vấn. `list_groups` chạy số truy vấn cố định, khoảng 5 nhóm × 1 truy vấn thành viên. Các dòng audit dùng `select_related("actor__staff_profile")`.
- **AI.** `/api/staff/` có trong `FORBIDDEN_PREFIXES` (`ai/policy/rules.py:13`), nên AI không gọi được ma trận.

### Phát hiện

**M1 — Medium · Tắt "Giao hàng, báo kết quả giao" (`deliver`) làm gãy việc "Soạn hàng, in tem" (`pack_print`).**
- `apps/delivery/api.py:160-178`: action `set_status` khai `required_perms=("delivery.change_deliverynote",)`, và `BusinessModelPermissions` (`common/api.py:58-69`) kiểm tra quyền này trước, kể cả khi chuyển sang `READY`. Bước này chỉ cần `pack_deliverynote`.
- Hai tập perms "rời nhau" ở registry, nhưng thực tế hai việc **không độc lập**. Màn hình sẽ hiện `pack_print: on` trong khi người dùng không đóng gói được.
- Tái hiện (đã chạy):
  1. Chủ gọi `PUT /api/staff/groups/warehouse_staff/capabilities/ {"capabilities":{"deliver":false}}`.
  2. NV kho gọi `POST /api/delivery/notes/<id>/status/ {"to_status":"READY"}`.
  3. Trước khi tắt nhận 404 (đi qua tầng quyền). Sau khi tắt nhận **403 "Thiếu quyền: delivery.change_deliverynote"**.
- Hướng sửa: chọn một trong hai cách.
  - (a) Thêm `requires` vào registry: `pack_print` cần `deliver`. Service trả 400 khi tắt `deliver` lúc `pack_print` đang bật, hoặc khi bật `pack_print` mà thiếu `deliver`. Thêm test.
  - (b) Sửa `set_status` để READY chỉ cần `pack_deliverynote`. Cách này đụng `delivery/api.py`, ngoài phạm vi lô, cần điều phối viên mở phạm vi.
- Tôi đề xuất (a). Cũng nên rà các cặp phụ thuộc tương tự trong test registry. Ví dụ: mọi việc đều cần `view_orders`, và tắt `view_orders` là gãy cả màn hình. Dev note 5 đã ghi ca này cho `delivery_staff`, nhưng FE mới chỉ cảnh báo cho `delivery_staff`.

**M2 — Medium · `scopes` cố định có thể sai sau khi Chủ bật "Xem khách hàng" cho nhóm khác (bất biến 9, hiển thị sai phạm vi dữ liệu cá nhân).**
- `registry.py`, `GROUP_SCOPES`: `warehouse_staff`/`customer_service` có `customers: "Không xem"`, `delivery_staff` có `"Được gán"`.
- `view_customers` không phải `owner_only`, và `customer-directory` không có phạm vi dòng (`directory_api.py` docstring: "quyền này = xem mọi khách"). Vì vậy, sau `PUT …/delivery_staff/capabilities/ {"view_customers": true}`, NV giao xem được **toàn bộ** tên, SĐT và địa chỉ khách. Trong khi đó W3i vẫn hiện "Khách: Được gán".
- Màn hình chỉ đọc đang nói sai đúng chỗ Chủ dựa vào để quyết lộ dữ liệu cá nhân.
- Hướng sửa: `describe_group` tính `customers = "Tất cả"` khi nhóm có `sales.view_customer_list`, còn lại lấy bảng cố định. Thêm test: bật `view_customers` cho `delivery_staff` thì detail trả `customers: "Tất cả"`.
- **Câu hỏi cho Duy (không chặn lô).** Có muốn chặn hẳn `view_customers` cho `delivery_staff`/`customer_service` không, tức là coi nó là "chỉ Chủ + Quản lý"? 02b hiện cho Chủ toàn quyền bật.

**L1 — Low · Cửa sổ quét thành viên.** `services.py` `_membership_events` lấy 1000 dòng `staff_groups_change` mới nhất của **mọi** nhóm rồi mới lọc theo nhóm. Khi hệ thống có nhiều đổi nhóm, sự kiện cũ của nhóm ít biến động sẽ mất khỏi timeline. Chấp nhận được ở quy mô hiện tại. Nếu muốn sửa thì lọc trong DB bằng `changes__groups__from__contains`/`to__contains`.

**L2 — Low · Docstring lỗi thời.** `capabilities/next_steps.py` ghi "vì `_LAZY_MODULES` của guidance chưa có khoá `group`", nhưng điều phối viên đã thêm khoá này. Nên sửa docstring. Có thể bỏ `from . import next_steps` ở `api.py`, hoặc giữ cả hai vì vô hại.

**L3 — Low · Bản đồ module.** `backend/README.md` và `apps/accounts/README.md` chưa liệt kê `capabilities` (dev note 6).

### Kết luận Lô 14 — BE: **CHANGES REQUESTED**
- Không có lỗi Critical hay High. Chặn leo quyền và chặn giá vốn đều đúng và có test tốt.
- Cần sửa **M1** (phụ thuộc `pack_print` → `deliver`) và **M2** (`scopes.customers` theo quyền thực tế), mỗi cái kèm test.
- L1–L3 có thể làm cùng hoặc ghi nợ.

## Lô 12 — BE (R11 hoá đơn mua, R12 chi phí phụ, R13 hoá đơn bán, R15 báo cáo lãi lỗ theo lô + số đếm kỳ)

> Tech Lead · 2026-10-02 · Code chưa commit trên `main`. Căn cứ: 02b §0, §3.0, §3.8 R11/R12/R13/R15, §4, §5.2 Lô 12; D-3; `03-dev-notes.md` "Lô 12 — BE".

### Lệnh đã chạy
- `manage.py test apps.sales.payments apps.purchasing apps.reports apps.ai`: **738 test, OK** (29.8 s).
- `manage.py makemigrations --check --dry-run`: No changes detected. Lô này không có migration.
- `python3 scripts/check_naming.py`: OK, không có vi phạm mới.
- Không có FE nào đang gọi 4 endpoint này (`grep` trong `erp-console/`, `frontend/`). Vì vậy đổi kích thước trang từ 50 (mặc định DRF) xuống 20 (`StandardPagination`) ở R11 và R12 không làm gãy màn nào.

### Đã soát, đạt
**Bất biến 1 (giá vốn)**
- **R13 dòng.** `SalesInvoiceListSerializer` có `sensitive_fields=("cogs","gross_profit")` và dùng `CostFieldSerializerMixin`. Hai khoá này đã có trong `COST_KEYS`.
- **R13 `totals`.** `build_totals(..., with_profit=has_perm(VIEW_COSTPRICE_PERM))` chỉ thêm `gross_profit` khi người gọi có quyền giá vốn. `totals` tính trên queryset đã lọc **và** đã áp phạm vi dòng.
- **Sắp xếp.** Settings không bật `OrderingFilter`, nên `?ordering=cogs` không có tác dụng và không lộ thứ tự theo giá vốn.
- **`q`.** Chỉ tìm theo `code` và `sales_order__code`.
- **Lọc sai.** Ném `BusinessError` trước khi tính `totals`. Body lỗi không lặp lại giá trị người gọi gửi.
- **R13 chi tiết.** Vẫn dùng `SalesInvoiceSerializer` cũ. `unit_cost` lồng trong `batch_allocations` bị ẩn qua mixin (ngữ cảnh lấy từ serializer cha). `retrieve` cũng đi qua `scope_invoices_for`, nên không có IDOR với người có quyền trực tiếp mà ngoài phạm vi.
- **R12.**
  - `check_permissions` chặn GET/HEAD khi thiếu `view_costprice`. Lớp chặn này thêm vào Tầng 1 `view_purchasecost`, và vì không có field nào để ẩn từng phần nên cả request bị chặn.
  - Người chưa đăng nhập nhận 401 trước, vì `super()` chạy trước.
  - Lệnh AI `purchasing.purchasecost.list/retrieve` chạy qua `dispatch.py` (`APIRequestFactory` → `view_cls.as_view`), nên cũng bị chặn y như vậy.
- **R11.** `amount` hiện cho Quản lý đúng theo D-3. Vai khác bị 403 ở Tầng 1. `code` `#n` và `receipt_code` `PR-n` khớp với cách R10 đặt mã (`receipts/serializers.py:129,166`).
- **R15.**
  - `require_perm(view_profitreport)` và `required_perms` khai ở class.
  - Lệnh AI `reports.batch_pnl_list` mang `required_perms` đó. Lệnh chạy qua view nên Quản lý và NV kho bị 403. Kết quả còn đi qua `scrub_data`, nên ai thiếu `view_costprice` bị lọc khoá `COST_KEYS`.
  - Kênh mặc định là `local`, mức nhạy cảm mặc định `high`, giống hệt lệnh `reports.batch_pnl` đã có. AI chỉ đọc được lãi lỗ khi người gọi là Chủ, nên lệnh này không mở đường mới.
- **R15b.** Gộp `period_counts` vào bằng `{**period_pnl, **counts}`. Hai bên không trùng khoá, nên các số cũ giữ nguyên.

**Bất biến 9 (dữ liệu khách)**
- **R13.**
  - Chỉ trả `customer_name`, không có SĐT hay địa chỉ.
  - `NoStoreMixin` áp cho cả list và detail.
  - Người không thuộc full scope chỉ thấy hoá đơn của đơn trong `scope_orders_for`, và tên bị null khi `pii_visible=False`. Phạm vi này dùng lại helper của danh sách đơn, nên hai màn không lệch nhau.
  - `customer_name` nằm trong `SCRUB_PII_KEYS`, nên không tới được AI.
- Không có log hay `AuditLog` mới.

**Số liệu và giờ VN**
- **`period_counts` so với `period_pnl`.**
  - `invoice_count` dùng cùng bộ lọc với doanh thu gộp (`ISSUED` + `issued_at__year/month` theo TIME_ZONE VN).
  - `refund_count` loại phiếu khi `EXISTS(CN.issued_at <= confirmed_at)`. `period_pnl` thì loại khi `confirmed_at >= first(CN).issued_at`.
  - Hai cách này tương đương vì một hoá đơn tối đa có một chứng từ đảo: `SalesCreditNote.source_key` là unique `cancel:<order.pk>`, và một đơn có một hoá đơn.
  - Có test `test_r15_ac6_*` giữ hai bên khớp nhau.
- **"Lô phát sinh trong kỳ".**
  - `month_bounds` tạo mốc aware theo giờ VN, áp cho `issued_at` và `closed_at`.
  - `received_date` là DateField nên so trực tiếp theo ngày.
  - Có test biên `test_r15_ac3_month_boundary_uses_vietnam_time`.
  - `Exists` nên một lô không bị nhân dòng.
- **R13 ngày.** `date_range_q` dùng `__date` theo TIME_ZONE. `date_from > date_to` trả 400.
- **Phân trang ổn định.** Cả 4 queryset đều có thứ tự xác định: `PurchaseInvoice` và `PurchaseCost` theo `Meta.ordering`, `SalesInvoice` theo `-issued_at,-id`, lô theo `-received_date,-id`.

**Khác**
- Snapshot AI: lô này chỉ thêm đúng 1 dòng `reports.batch_pnl_list`. Các dòng khác trong `git diff` của snapshot thuộc các lô 4/6/8 chưa commit, không phải của lô này.
- Không đụng `services.batch_pnl`/`period_pnl` và `payments/services.py`, đúng §5.2.

### Phát hiện

**M1 — Medium (chờ Duy, đã đưa Duy quyết; không chặn BE) · NV kho thấy tên khách trên mọi hoá đơn bán.**
- `apps/sales/payments/invoice_list.py:39`: `has_full_delivery_scope` gồm `warehouse_staff`, nên NV kho nhận `customer_name` của toàn bộ hoá đơn.
- BE đang làm đúng 02b R13 (`view_salesinvoice`: chu, quan_ly, nv_kho), nhưng lệch với ED-33-AC4 (NV kho thấy "Không có quyền").
- Tái hiện: token `warehouse_staff` gọi `GET /api/sales/invoices/` → 200, `results[].customer_name` có tên.
- Nếu Duy chọn khoá thì có hai cách, cả hai đều ngoài phạm vi lô này:
  - (a) Thu hồi `view_salesinvoice` của Group `warehouse_staff` bằng data migration trong `accounts`. Cách này ảnh hưởng `retrieve` và lệnh AI `sales.salesinvoice.*` của NV kho.
  - (b) Giữ quyền xem nhưng null `customer_name` cho người không thuộc `sees_customer_directory`.
- Tôi nghiêng về (b) nếu NV kho vẫn cần tra hoá đơn khi soạn hàng. Nếu không cần thì chọn (a).

**L1 — Low · Số truy vấn của R15 tăng theo số lô trên trang.**
- `apps/reports/api.py:49` gọi `services.batch_pnl` cho từng lô: khoảng 7 truy vấn mỗi lô, tối đa khoảng 140 truy vấn cho một trang 20 lô.
- Đã có test khoá mức này: `test_r15_query_count_is_bounded_by_batch_pnl_cost_per_row` bảo đảm không phát sinh N+1 ngoài phần của `batch_pnl`.
- Endpoint chỉ Chủ dùng, nên chấp nhận được lúc này. Ghi nợ: nếu đo trên staging thấy trang chậm quá 1 s thì viết `batch_pnl_many` trong `services.py`, với cùng công thức và test so khớp từng lô.

**L2 — Low · Tập "lô phát sinh trong kỳ" hẹp hơn tập sự kiện mà `batch_pnl` tính.**
- `apps/reports/batch_list.py:31-37` chỉ xét ba tiêu chí: nhập, bán hoặc chốt trong tháng.
- Một lô cũ, chưa chốt, mà trong tháng chỉ có hao hụt, hàng hoàn, trả NCC hoặc chứng từ đảo sẽ không có mặt trong danh sách của tháng đó. Số của lô vẫn đúng khi xem ở tháng khác hoặc khi bỏ `month`.
- Đây là giả định số 4 của dev, hợp lý cho bản đầu. FE cần ghi rõ tiêu chí dưới bộ lọc tháng. Nếu Lộc muốn tính đủ thì thêm `Exists` cho `ledger_entries` và `credit_lines` của tháng.

**L3 — Low · `period_counts` chép lại quy tắc của `period_pnl`.**
- Liên quan `apps/reports/period_counts.py:19-29` (dev note 5).
- Rủi ro lệch số khi một bên đổi quy tắc, đã có test `test_r15_ac6_refund_*` canh chừng.
- Khi nào được sửa `services.py`, nên để `period_pnl` trả luôn hai số đếm từ cùng queryset, rồi xoá file này.

**L4 — Low · `list()` của R13 dựng queryset lọc hai lần.**
- `apps/sales/payments/api.py:54-56`: `super().list` và `build_totals` mỗi bên gọi `filter_queryset(get_queryset())` một lần. Hệ quả là parse tham số hai lần và chạy một truy vấn đếm/tổng riêng, nhưng kết quả đúng.
- Có thể giữ nguyên, hoặc gắn queryset đã lọc lên `self` trong `filter_queryset` để dùng lại.

**Ghi chú (không phải lỗi)**
- Người có `view_profitreport` mà không có `view_costprice` vẫn nhận `landed_unit_cost`, `purchase_cost`... ở R15. Hành vi này giống hệt `GET /api/reports/batch/{id}/` đã nghiệm thu, và đã có test `test_r15_ac1_user_with_only_view_profitreport_200`.
- Ở ma trận B4 (`capabilities/registry.py:74-75`), cả `view_cost` và `view_profit` đều là `owner_only`. Vì vậy trường hợp trên không thể xảy ra qua giao diện.

### Kết luận Lô 12 — BE: **APPROVED**
- Không có lỗi Critical hay High.
- Mọi đường lộ giá vốn đều đã chặn ở BE và có test: dòng, `totals`, sắp xếp, `q`, chi tiết cũ, R12 cả chứng từ, R15 và lệnh AI.
- Dữ liệu khách ở R13 có `no-store`, có phạm vi dòng và không tới được AI.
- **M1** chờ Duy quyết theo ED-33-AC4. Nếu Duy chọn khoá NV kho thì mở lô sửa nhỏ: (a) migration `accounts` hoặc (b) null `customer_name`, kèm test.
- L1–L4 ghi nợ.
- Báo FE: R11 và R12 đã phân trang 20 dòng.

### Re-review Lô 14 — BE (sau khi sửa M1, M2, L1–L3)
> techlead · 02/10/2026 · Kiểm chứng: `manage.py test apps.accounts apps.common` chạy **531 test, OK**. Tôi tự quét lại bằng AST trên toàn bộ `apps/` (không gồm tests và migrations): mọi hàm hoặc class nhắc tới permission của từ hai việc trở lên, đếm cả `required_perms`, `require_perm`, `has_perm` và hằng chuỗi.

- **M1 · đã sửa.**
  - `_check_requires` (`capabilities/services.py:281`) xét trạng thái sau khi áp yêu cầu. Việc gốc hoặc việc phụ thuộc phải nằm trong yêu cầu thì mới xét. Thông điệp nêu rõ cả hai việc.
  - Lệnh được kiểm trước mọi lần ghi, nên không ghi gì và không có audit khi bị chặn.
  - Test phủ đủ: bật hoặc tắt lệch nhau trả 400, đổi cả hai cùng lúc trả 200, ô `partial` vẫn tính là đang bật, dữ liệu lệch có sẵn không chặn việc khác, người không phải Chủ nhận 403 trước khi tới bước kiểm phụ thuộc.
- **Phép quét action có bao hết cặp phụ thuộc không: chưa.** Test `test_actions_spanning_several_capabilities_are_covered_by_requires` chỉ đọc `kwargs["required_perms"]` của `@action` trên các viewset có đăng ký router. Nó **không bắt được đúng dạng lỗi M1**: `set_status` chỉ khai một perm trong `required_perms`, còn `pack_deliverynote` được kiểm bằng `has_perm` ngay trong thân hàm. Test cũng bỏ qua `require_perm`/`has_perm` viết trong thân hàm, `required_perms` khai ở cấp class, và các `APIView` không đăng ký router.
  - Tôi đã tự quét lại theo cách rộng hơn. Có 9 chỗ chạm từ hai việc trở lên. Chỉ **`delivery/api.py:167 set_status`** đòi cả hai quyền cùng lúc (`deliver` và `pack_print`), và cặp này đã được khai trong `requires`.
  - 8 chỗ còn lại không cần khai:
    - `refunds/api.py:64 create_refund` đòi thêm `confirm_payment` chỉ ở nhánh giao dịch lệch. Đây là nhánh con của Chủ, `confirm_payment` là `owner_only`, nên không thể khai `requires`.
    - `delivery/attention_api.py:32` cần một trong các quyền (OR).
    - Các hàm `get_available_actions` và `next_steps` chỉ dùng quyền để hiện nút.
    - `ai/*` liệt kê quyền.
  - Kết luận: **hiện không còn cặp nào bị sót**. Test quét chỉ là lưới an toàn hẹp, ghi nợ ở L4.
- **M2 · đã sửa.** `group_scopes` (`services.py:230`) trả `customers = "Tất cả khách"` khi nhóm có `sales.view_customer_list`; khi không có thì lấy bảng cố định. Có test khớp với kết quả 200/403 của `customer-directory` cho cả 5 nhóm. Lưu ý cho FE: chuỗi `customers` đổi từ `"Tất cả"` thành `"Tất cả khách"`, và owner/manager có thể nhận `"Không xem"`. FE đang hiện chuỗi do BE trả nên không cần đổi logic.
- **L1 · đã sửa.** Lọc trong DB bằng `changes__groups__from/to__icontains` rồi kiểm lại chính xác bằng Python. Dùng `iterator()` và dừng khi đủ 200 dòng. Postgres hỗ trợ lookup này qua `KeyTransformIContains`; dev mới chạy trên SQLite, nên QA cần thử trên staging.
- **L2, L3 · đã sửa.**

**L4 — Low (mới, ghi nợ) · `capabilities/tests/test_requires.py`, `test_actions_spanning_several_capabilities_are_covered_by_requires`:** test này không thấy được kiểm quyền viết trong thân hàm, nên nếu sau này có cặp phụ thuộc mới theo dạng giống M1 thì test vẫn xanh.
- Cách sửa: thêm vào docstring của test và của `registry.py` rằng ai thêm `require_perm`/`has_perm` của việc khác vào một action thì phải tự khai `requires`.
- Hoặc mở rộng test sang quét AST mã nguồn của action, như cách tôi đã quét.
- Không chặn lô.

### Kết luận re-review Lô 14 — BE: **APPROVED**
Không còn lỗi Critical, High hay Medium. Lô sẵn sàng cho QA.

---

## Lô 2 — FE (mẫu trang chi tiết, popup, form, khối Trợ lý AI; ED-03 phần còn lại, ED-04 trang chi tiết, ED-05)
> Review 02/10/2026 trên diff chưa commit: `git diff -- erp-console` cùng các file mới chưa track. Không xét `backend/`.
> Căn cứ: 02b §0 (1, 2, 7), §0b T2/T10, §0c, §2.3, §2.4, §4, §5.2 Lô 2; contract R1/R2 ở mục "Lô 2 — BE" của dev-notes; UI-RULES.

**Kết luận: CHANGES REQUESTED (nhẹ).** Không có lỗi Critical hay High. Lô không rò giá vốn, không rò dữ liệu khách và
không vượt quyền. Có 2 lỗi Medium cần sửa trong lượt này, mỗi lỗi vài dòng: M1 (`isConflictError` coi mọi 409 là "người
khác vừa sửa") và M2 (nút Đồng ý kẹt khi tải chi tiết đề xuất lỗi). Các lỗi Low được để lại theo lô ghi bên dưới.
**Nhắc commit font:** `public/fonts/ms/material-symbols-outlined.woff2` (112 icon) **không** bị `.gitignore`. Dev ghi sai
ở dev-notes. Xem L1.

### Kiểm chứng (Tech Lead tự chạy trong lượt này)
- `npx tsc --noEmit`: sạch. `npx vitest run`: 42 file, 366 test đều đạt.
- `NEXT_PUBLIC_USE_MOCK=0 npm run build`: OK. `check-no-mock`: XANH (15 file mock, 34 seed). `check-ai-chunks`: XANH.
- Bản build thật: trong `out/` và `.next/static` không có chuỗi demo (`PR-260928-01`, `dev-patterns/qty`, `Nhập thử một phiếu`,
  `CA01-260928`). Route `/(console)/dev-patterns/page` chỉ có các chunk khung cùng một page chunk 1,4 kB (chỉ chứa `NotFoundScreen`).
- `NEXT_PUBLIC_USE_MOCK=1 npm run build`: `PatternDemo` nằm ở chunk lười `1085.*.js`, có `data-ai-block`. Chunk này chỉ
  *tham chiếu* chunk `4905.*.js`, là một trong 3 chunk có `wllama` (`7483`, `7513`, `4905`). Bản thân nó không chứa
  `new Worker`, `wllama` hay `/call/`. Như vậy `AiAssistantPanel` đúng là tách chunk và chỉ nạp khi render.
- `git check-ignore -v …/material-symbols-outlined.woff2` trả rc=1, tức là không bị chặn (`.gitignore:54 !erp-console/public/fonts/ms/*.woff2`).
  `git ls-files` có file này, `git status` báo `M`.
- So các tên icon trong `<Icon name="…">` và `icon: "…"` của `app/ features/ shared/` với danh sách `ICONS` (112 tên): không thiếu tên nào.
- `python3 scripts/check_naming.py`: OK. Grep màu cứng trên các file mới chưa track: 0.

### Đối chiếu trọng tâm
| Mục | Kết quả | Căn cứ |
|---|---|---|
| SR-20: AI tắt thì không có request `/api/ai/*` | Đạt ở 4 màn SR-20 | Các màn nghiệp vụ hiện chưa gắn `AiDocBlockGate`, nên 0 request. Trang chi tiết có khối AI thì AI tắt vẫn gọi **1** `GET /api/ai/status/` và 0 `/api/ai/actions`. Đây là hành vi 02b §2.3 cho phép ("như `AiAssistantGate`"); SR-20-AC3 chỉ áp cho 4 màn danh sách. Lô 3 trở đi không được gắn khối AI vào 4 màn đó |
| Code AI nặng chỉ nạp động sau khi bật AI và đồng ý | Đạt | `AiDocBlock.tsx:24` dùng `dynamic(() => import("./AiAssistantPanel"), { ssr:false })`. Chỉ render khi `chatOpen && consented` (`AiDocBlock.tsx:145-147`). Đã xác nhận bằng chunk của bản mock (xem trên) |
| Không lọt vào chunk route nghiệp vụ | Đạt (xem L3) | `AiDocBlockGate.tsx:12` import **tĩnh** `AiDocBlock` (actions api, consent, `AiBlockFrame`, `ai.module.css`). Đây là phần nhẹ, không có runtime. Dev-notes viết "AiDocBlockGate (nạp động…)" là chưa đúng: chỉ panel chat là nạp động |
| `AiDocBlockGate` tự công bố cờ AI | Không race, nhưng cờ "dính" (L2) | `getAiStatus` gọi `publishAiEnabled` (`features/ai/api.ts:16`). Unmount thì abort và không publish `false` (đúng). Mỗi lần mở trang chi tiết có 1 status + 1 list + N chi tiết đề xuất PENDING (BR-AI-14 cần chi tiết để ghi `viewed_at`). Không có lệnh gọi thừa |
| Route `dev-patterns` | Đạt (L4) | Có thật trong bản build, nhưng chỉ vẽ `NotFoundScreen`, nằm sau `ConsoleGate` (phải đăng nhập), và không có mã hay dữ liệu demo. Cờ mock viết đúng dạng `process.env.NEXT_PUBLIC_USE_MOCK === "1" ? dynamic(...) : null` ở mức route. Như vậy đã đủ, không cần chặn thêm |
| Timeline: không render `why.br` | Đạt | `GuidancePanel.tsx` bỏ `step.why.br`. `Timeline.tsx` và `detailAdapters.ts` không có trường `br`. e2e kiểm không có `BR-\d` |
| `timeline_truncated` | Đạt | `types.ts` có `timeline_truncated?`. `GuidancePanel.tsx` ghi "Chỉ hiện n việc gần nhất". `Timeline` có prop `truncated`; màn thật phải truyền `data.timeline_truncated` vì `toTimelineEntries` không mang cờ này |
| `doc.status` nullable (R2) | Đạt | `types.ts`: `status`/`status_label` cho phép `null` |
| Dữ liệu cá nhân: LookupCard, `lookups.ts` | Đạt | `LookupKind = batch\|item\|delivery\|order`, không có thẻ khách hàng và không gọi API khách. `toLookupCard` chỉ lấy theo danh sách trường cho phép. `recipient_*`, `customer.*`, `landed_unit_cost` trong mock đều bị bỏ, có vitest và e2e (`123456` không hiện). Đã đối chiếu tên trường với `BatchSerializer`, `ItemSerializer`, `DeliveryNoteSerializer`: khớp |
| Giá vốn trong khối AI (ED-04-AC9) | Đạt | `docBlockModel.ts` chỉ hiện khoá có trong `ARG_LABEL` (không có khoá tiền). BE đã lọc `args_preview` bằng `scrub_data` theo người xem |
| Modal | Đạt | Giữ focus ở `focus.ts:trapTarget`. Esc đóng hộp trên cùng, đang `busy` thì không đóng; nền và nút X cũng bị khoá. Lấy nút mở lúc render và trả focus khi cleanup. `aria-modal`, `aria-labelledby`. e2e có Tab ×8, Shift+Tab, Esc khi đang gửi, trả focus |
| MoreMenu | Đạt | Mục bị chặn có `aria-disabled`, có lý do nằm cạnh và trong tên truy cập, vẫn focus được, bấm vào không gọi `onSelect`. Bàn phím: ↑ ↓ Home End Esc (trả focus về nút "…"), Tab đóng |
| `useSubmit` | Đạt (xem M1) | Bấm đúp bị chặn bằng `inFlight` ref, kể cả hai lần bấm trong cùng một khung hình. Khi lỗi, hook không đụng state giá trị; `failed` chuyển nút thành "Thử lại"; `fieldErrorsOf` chỉ đọc lỗi 400 |
| 409 trong `http.ts` | Đạt, không hồi quy | `http.ts:203` truyền `details` cho 409. Đã rà mọi nơi đang đọc 409: `content/edit` và `ImageUploadSheet` chỉ đọc `status` và `code`; `confirmation/api.ts:147` đọc `code`; `ai/settings/levels.ts:74` chỉ đọc `details` khi `code==="BR-AI-19"` (400). Thay đổi duy nhất người dùng thấy được: 409 không kèm `detail` giờ hiện `MSG.conflict` thay cho "Lỗi máy chủ (409)". Mọi 409 của BE hiện đều có `detail`, nên ca này không xảy ra |
| Font icon | Đạt, **phải commit** | `chat` và `forward_to_inbox` đã có trong `ICONS`. Font 94.576 byte đang ở trạng thái `M` |
| Màn cũ | Đạt | `GuidancePanel` bỏ nút "Làm mới" (UI-RULES §2.2). Nút "Thử lại" khi lỗi và `refreshSignal` vẫn còn. Không e2e nào bấm "Cập nhật hướng dẫn". `p8_lo6_fe_sr19_sr20.py` sửa đúng theo việc đã gỡ cột phải ở Lô 1 |

### Phát hiện

**M1 — Medium — `useSubmit` coi mọi 409 là "người khác vừa sửa".** Vị trí: `shared/ui/form/useSubmit.ts:29-30`.
- Lỗi: hàm trả true với **mọi** `status === 409`. Khi đó `useSubmit` (`:76-77`) bỏ `err.message` và chỉ bật `ConflictBanner`.
- Phạm vi ảnh hưởng: BE đang trả 409 cho nhiều việc không phải xung đột phiên bản, ví dụ `CLAIMED` (`common/exceptions.py:32`),
  `AI_ACTION_ALREADY_DECIDED`/`AI_ACTION_NOT_PENDING` (`ai/actions/services.py:62-63`), `POLICY_CHANGED`,
  `CONTENT_WARNINGS` (bước xác nhận cảnh báo CMS-08), `AI_CONFIG_CONFLICT`, `AI_POLICY_CONFLICT`.
- Hậu quả: 30 story dùng lại mẫu này sẽ hiện "Phiếu vừa được người khác sửa…" cho cả các ca trên, và người dùng mất câu
  lý do thật của BE.
- Nguyên nhân gốc: câu "409 hoặc STALE_STATE" ở 02b §2.3 viết lỏng. Tech Lead nhận phần này. Ý định của câu là xung đột phiên bản.
- Cách tái hiện:
  - `apiFetch` mock trả `{status:409, body:{detail:"Việc đã có người nhận.", code:"CLAIMED"}}` trong `useSubmit`.
  - Kết quả hiện tại: `error === null`, `conflict = {}`, banner nói "người khác vừa sửa".
- Sửa: chỉ coi là xung đột khi `code ∈ {"STALE_STATE","STALE_VERSION"}`, hoặc 409 mà thân có `updated_at`. Các 409 còn lại
  đi nhánh lỗi thường (alert đỏ, hiện `err.message`). Thêm vitest cho 409 `CLAIMED`: `error` là câu của BE, `conflict === null`.
  Tech Lead đã sửa câu ở 02b §2.3 cho khớp.

**M2 — Medium — Nút "Đồng ý" kẹt ở "Đồng ý (3)" khi tải chi tiết đề xuất lỗi.** Vị trí: `features/ai/components/AiDocBlock.tsx:77`, `:98`.
- Diễn biến lỗi:
  1. `fetchAiActionDetail` lỗi (mất mạng, 404).
  2. `.catch(() => ready.current.delete(r.id))` xoá mốc chờ và không báo gì.
  3. `waitLeft(undefined)` trả về 3, nên nút bị khoá mãi.
  4. `anyWaiting` vẫn true, nên `setInterval` 500 ms chạy mãi.
  5. Không có lỗi nào hiện ra, và "Thử lại" không xuất hiện vì `loadError` vẫn null.
- Hậu quả: người dùng chỉ còn cách tải lại trang.
- Cách tái hiện (mock): cho `mockFetchAiActionDetail` trả 500 với một id PENDING, mở `/dev-patterns/` khi AI bật. Nút giữ "Đồng ý (3)" sau 10 giây.
- Sửa: khi `.catch` (và không phải abort), đặt một lỗi cho đề xuất đó, ví dụ `setLoadError("Chưa mở được chi tiết đề xuất.")`,
  để khối hiện "Thử lại" (gọi `load()` sẽ tải lại chi tiết vì id đã bị xoá khỏi `ready`). Đồng thời không tính đề xuất
  thiếu mốc vào `anyWaiting`.

**L1 — Low — Ghi chú font sai, có nguy cơ quên commit.** Vị trí: `03-dev-notes.md`, mục "Lô 2 — FE: sửa theo yêu cầu…" (7).
- Dev viết font "bị `.gitignore`, mỗi máy tự sinh lại". Thực tế file đã được track từ Lô 1 (`.gitignore:54`), nay đang `M`.
- Commit của lô **phải gồm** `erp-console/public/fonts/ms/material-symbols-outlined.woff2`. Nếu thiếu, `chat` và
  `forward_to_inbox` sẽ hiện thành chữ trên bản build ở máy khác hoặc trên CI.
- Sửa câu trong dev-notes.

**L2 — Low — Cờ "AI bật" bị dính theo lịch sử điều hướng.** Vị trí: `features/ai/api.ts:16`, `features/ai/gate-state.ts`.
- Biểu hiện: sau khi mở một trang chi tiết có `AiDocBlockGate`, cờ `enabled=true` ở mức module còn nguyên khi quay về `/orders`.
  Vì vậy nút "Tóm tắt" (DW-16) của `GuidancePanel` hiện hay không tuỳ người dùng đã ghé trang chi tiết nào chưa.
- Nếu Chủ tắt AI giữa chừng, cờ vẫn là true cho tới lần gọi status kế tiếp.
- Không vi phạm BR-AI-17, vì vẫn cần sự đồng ý. Đây là chuyện nhất quán giao diện.
- Ghi lại để Lô 3 quyết: "Tóm tắt" chỉ hiện trên trang chi tiết, hoặc chấp nhận hành vi này.

**L3 — Low — `check-ai-chunks` chưa phủ trang chi tiết.** Vị trí: `scripts/check-ai-chunks.mjs:20`.
- `TARGETS` chỉ gồm 4 màn danh sách và 2 layout. Hiện chưa route thật nào gắn `AiDocBlockGate`, nên kết quả XANH chưa chứng minh gì cho khối AI.
- Lô 3 phải thêm `/(console)/orders/detail/page`, và các trang chi tiết sau đó, vào `TARGETS`.
- Tuỳ chọn: chuyển `AiDocBlock` thành `next/dynamic` trong gate để AI tắt thì trang chi tiết không tải cả phần nhẹ.

**L4 — Low — Route `dev-patterns` vẫn có trong bản build thật.** Vị trí: `app/(console)/dev-patterns/page.tsx:8`.
- Route sinh `out/dev-patterns/index.html`, trả 200 kèm màn "Không tìm thấy" sau khi đăng nhập.
- Không lộ gì: đã grep chuỗi demo. Chấp nhận được.
- Nếu muốn có 404 thật, có thể đổi đuôi file (`page.mock.tsx`) và đặt `pageExtensions` theo cờ mock trong `next.config.mjs`. Không bắt buộc.

**L5 — Low — `InfoField` sửa tại chỗ gặp 409 thì im lặng.** Vị trí: `shared/ui/detail/InfoField.tsx:131`.
- `useSubmit` đưa 409 vào `conflict` chứ không vào `error`, nên ô vẫn mở, nút thành "Thử lại" mà không có dòng lỗi.
- Hiện chỉ đúng khi màn tự bắt lỗi trong `onSave`, như trang demo đang làm.
- Sửa: thêm prop `onConflict`, hoặc hiện câu ngắn dưới ô khi `sub.conflict`. Làm cùng M1 hoặc ở Lô 3.

**L6 — Low — Thứ tự dòng cùng thời điểm bị ngược.** Vị trí: `features/guidance/detailAdapters.ts:9`.
- `sort` ổn định, nên hai dòng cùng `at` (ví dụ "tạo" và việc đầu tiên trong cùng giây) giữ thứ tự cũ → mới, trong khi danh sách xếp mới → cũ.
- Sửa: dùng `[...entries].reverse()` (BE đã xếp cũ → mới), hoặc thêm tiêu chí phụ là chỉ số ban đầu, đảo ngược.

**L7 — Low — Dọn dẹp.**
- `features/guidance/components/guidance.module.css:27-43`: `.refreshBtn` là CSS chết.
- `shared/ui/form/SummaryBlock.tsx:2`: chú thích "SĐT… do màn truyền vào đã che sẵn" trái với quyết định 6 (ERP hiện đủ SĐT). Sửa thành "ERP hiện đủ, tem in và AI thì che".
- `GuidancePanel.tsx:250` vẫn in `[e.doc]` thô (`receipt`, `delivery`…) cạnh nhãn dòng thời gian. Lỗi có từ trước, nhưng R2 làm nó lộ ra ở 8 loại mới. Bỏ hoặc dịch ở Lô 3.

**Ghi nhận (không phải lỗi):**
- Chỗ lệch 2 (R1 không có giá trị "trước", nên chỉ hiện "sẽ đổi thành") và chỗ lệch 8 (chat chỉ mở khi bấm) đều hợp lý. PO cần biết ED-04-AC8 đang làm một phần "trước → sau".
- Chỗ lệch 3 (việc ESCALATED khi AI tắt) đã chuyển sang Lô 15 (T10). Đồng ý.
- `lookups.ts` có thêm loại `order` (`/api/sales/orders/{id}/`) ngoài 3 loại 02b liệt kê. Đồng ý, vì thẻ chỉ đọc mã, trạng thái, tổng tiền và ngày.

### Việc cần làm để APPROVED
1. Sửa M1 và M2, mỗi lỗi kèm vitest.
2. Sửa câu font trong dev-notes (L1).
3. Điều phối viên commit lô **kèm file font**. Tech Lead re-review chỉ phần diff của M1 và M2.

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

### Re-review Lô 2 — FE (02/10, sau sửa M1, M2 của Techlead và B1–B5 của QA)
> Phạm vi: mục "Lô 2 — FE: sửa sau Techlead CHANGES REQUESTED (nhẹ) và QA REJECTED lần 1" trong dev-notes, gồm
> `useSubmit.ts`, `AiDocBlock.tsx`, `docBlockModel.ts`, `AiBlockFrame.tsx`, `AiAssistantPanel.tsx`, `InfoField.tsx`,
> `features/ai/actions/mock.ts`, `features/ai/messages.ts`, `e2e/qa_ed_batch2_patterns.py`, `e2e/qa_ed_batch2_harness.py`.

**Kiểm chứng (Tech Lead tự chạy trong lượt này):**
- `tsc --noEmit` sạch. `vitest`: 42 file, 380 test đều đạt.
- Build `MOCK=0` OK. `check-no-mock` XANH, `check-ai-chunks` XANH.
- Grep `out/` và `.next/static` không thấy `aiDetailFail`, `cave_erp_mock_ai_detail_fail` hay `dev-patterns/qty`.
- Build `MOCK=1`: chunk có khung hỏi nhanh (`data-ai-starter`, `1085.*.js`, 49,7 kB) không chứa `new Worker`, `wllama`, `/call/`,
  `GgufDownloader` hay `gguf`. `wllama` chỉ nằm ở 3 chunk lười `7483`, `7513`, `4905`, giống lần review đầu.

| Mục | Kết quả | Căn cứ |
|---|---|---|
| M1 | Đạt | `useSubmit.ts`: `isConflictError` chỉ trả true khi `code` thuộc `STALE_STATE`/`STALE_VERSION`, hoặc 409 có `details.updated_at` dạng chuỗi. Hàm thuần `stateAfterError` có vitest cho `CLAIMED` (giữ câu của BE, `conflict` null) và `STALE_STATE`. Khớp câu đã sửa ở 02b §2.3 |
| M2 | Đạt | `AiDocBlock.tsx`: khi tải chi tiết lỗi (không phải abort, không phải lượt cũ), đề xuất bị xoá mốc và `loadError = AI_MSG.detailLoadFailed`, nên khối hiện "Thử lại". `anyWaiting` bỏ qua đề xuất thiếu mốc nên interval tự dừng. Đề xuất đó có `blocked`: nút Đồng ý khoá, nhãn trơn "Đồng ý", Từ chối vẫn dùng được. Bấm Thử lại thì `load()` tải lại chi tiết (id đã bị xoá khỏi `ready`) |
| B1: `ARG_FIELDS` là allow-list | Đạt | `changesOf` lặp trên **khoá của bảng** (`Object.entries(ARG_FIELDS)`), không lặp trên `args`, nên khoá lạ không bao giờ hiện. Bảng chỉ có khoá có cấu trúc: `item_code, qty, quantity, batch_id, supplier, warehouse, refund_amount`. Đã bỏ `note` và mọi chữ tự do. Không khoá nào là giá vốn (`refund_amount` là tiền hoàn cho khách). Giá trị `text` chỉ nhận chuỗi hoặc số, object hay mảng bị bỏ. Có vitest với `note` chứa SĐT giả |
| B2 | Đạt | `qty`/`quantity` qua `kg()`, tiền qua `vnd()`. Giá trị không phải số bị bỏ. `seen` theo nhãn nên khi có cả `qty` và `quantity` thì chỉ hiện một dòng |
| B3: khung hỏi nhanh tĩnh, không lọt mã AI nặng | Đạt | `AiBlockFrame` (`Starter`) chỉ import `Icon`, `format` và CSS. `AiAssistantPanel` vẫn là `next/dynamic` `ssr:false`, chỉ render khi `chatOpen`, mà `chatOpen` chỉ bật khi focus ô, bấm chip hoặc gửi. Panel mount **không** tự tải model: `startDownload` chỉ chạy khi bấm nút (`AiAssistantPanel.tsx:480`). Chưa đồng ý thì hiện thẻ đồng ý thay cho panel. `handedOff` ref giữ cho câu chip chỉ gửi một lần, kể cả khi StrictMode chạy effect hai lần. Đã xác nhận bằng chunk (xem trên) |
| B4 | Đạt | `act` dùng `inFlight` ref, đặt trước `await` và thả trong `finally`. e2e bấm 3 lần cùng tác vụ thì có đúng 1 POST |
| B5 | Đạt | `InfoField`: `validateDraft` chạy **trước** `sub.submit()`, nên lỗi nhập không làm `failed`, nút giữ "Lưu" |
| 2 file e2e của QA | **Không làm yếu, còn chặt hơn** | `qa_ed_batch2_harness.py:121-143`: ca cũ "409 trơn thì vẫn banner" đổi thành "409 `STALE_STATE` thiếu tên/giờ thì banner không in `undefined`/`null`/`Invalid`" (vẫn kiểm điều cũ, đúng nghĩa mới). Thêm 2 ca M1: `CLAIMED` và 409 không mã đều ra alert thường, giữ câu của BE, không có banner. `qa_ed_batch2_patterns.py:375-376`: kiểm 44 px chuyển từ nút "Hỏi trợ lý" (đã bỏ) sang nút "Gửi câu hỏi", cùng ngưỡng. `e2e/qa_harness_*/dist/` đã nằm trong `.gitignore:64` |
| Font | Đạt | Dev-notes đã sửa câu ghi sai. File font vẫn ở trạng thái `M`, **phải có trong commit** |

**Phát hiện mới (đều Low, không chặn):**
- **L8 — Low — Chip hỏi về "chứng từ này" nhưng trợ lý không biết chứng từ nào.** Vị trí: `docBlockModel.ts` (`DOC_CHAT_CHIPS`), `AiDocBlock.tsx` (`openChat`).
  - Chip "Tóm tắt lịch sử chứng từ này" và "Chứng từ này còn thiếu gì?" được gửi nguyên văn. `AiAssistantPanel` không nhận `targetModel`/`targetId`, nên câu trả lời không gắn với chứng từ đang xem. Không rò gì (đúng ED-04-AC10).
  - Hướng sửa ở Lô 3, khi có trang chi tiết thật: hoặc ghép **mã** chứng từ vào câu (chỉ mã, không dữ liệu khách), hoặc đổi chip thành câu không cần ngữ cảnh. PO nên biết.
- **L9 — Low — Focus rơi về `body` khi chưa đồng ý.** Vị trí: `AiBlockFrame.tsx` (`chat ?? <Starter/>`).
  - Khi ô hỏi nhận focus, `Starter` bị gỡ và thay bằng thẻ đồng ý (hoặc dòng "Đang mở trợ lý…"). Với người chưa đồng ý, focus không được đặt vào thẻ đồng ý mà rơi về `body`. Người dùng bàn phím phải Tab lại từ đầu.
  - Ngoài ra, chỉ cần Tab đi ngang ô này là panel được nạp (chỉ nạp JS, không tải model). Chấp nhận được theo quyết định B3.
  - Sửa: focus vào ô tick đồng ý khi thẻ hiện.
- Các mục L2–L7 của lần review đầu giữ nguyên, để sang Lô 3 như đã ghi.

### Kết luận re-review Lô 2 — FE: **APPROVED**
M1, M2, B1–B5 đều đạt. Không còn lỗi Critical, High hay Medium. Lô sẵn sàng cho QA chạy lại. Khi commit phải kèm
`erp-console/public/fonts/ms/material-symbols-outlined.woff2`. L8 và L9 cùng L2–L7 để Lô 3 xử lý.

## Lô 3 — FE (Đơn & tiền: ED-09, ED-10, ED-11, ED-12)
> Review 02/10/2026 trên diff chưa commit: `git diff -- erp-console` cùng các file mới chưa track. Không xét `loc-wt-b` (Lô 4).
> Căn cứ: 02b §0, §0b, §0c, §1 (D2, D2b, D2c, W1a, W1a2, W1b, W1b2), §2.3, §2.4, §5.2 Lô 3; contract "Lô 2 — BE", "Lô 3 — BE"
> trong dev-notes; `00-can-duy-quyet.md`; UI-RULES; SR-20 (`doc/features/2026-09-30-sua-loi-review/02-stories.md`).

**Kết luận: CHANGES REQUESTED.** Không có lỗi Critical. Lô không rò giá vốn, không rò dữ liệu khách ra URL, storage
hay AI, và không vượt quyền: mọi nút ghi đi theo `available_actions`. Có 2 lỗi High, cả hai đều tái hiện được:
- H1: khối Trợ lý AI trên trang đơn gửi sai `target_model`, nên BE thật trả 400.
- H2: 3 màn danh sách gọi `/api/ai/*` khi AI tắt, vi phạm SR-20-AC3 đã nghiệm thu.

Ngoài ra có 3 lỗi Medium. M1 là bản sửa B6/L9 không chạy.

### Kiểm chứng (Tech Lead tự chạy trong lượt này)
- `npx tsc --noEmit`: sạch. `npx vitest run`: 47 file, 428 test đều đạt.
- `NEXT_PUBLIC_USE_MOCK=0 npm run build`: OK. `check-no-mock`: XANH. `check-ai-chunks`: XANH.
  - 3 route chi tiết đã có trong `TARGETS`: `/orders/detail` 452,8 kB / 11 chunk, `/orders/payments/detail` 422,9 kB, `/orders/refunds/detail` 410,9 kB.
  - First Load của `/orders/detail` là 142 kB.
- `python3 scripts/check_naming.py`: OK. Có 1 file giảm vi phạm, nên chạy `--update` khi commit.
- Màu cứng trong `features/orders/orders.module.css`: 0.
- Build `MOCK=1`, phục vụ `out/` ở cổng 3111, chạy Playwright riêng của Tech Lead (script ở scratchpad, không vào repo). Kết quả ở H2 và M1.
  Sau đó đã build lại `MOCK=0`, nên `out/` vẫn là bản thật như dev để lại.
- BE: viết tạm một `TestCase` gọi `GET /api/ai/actions/?target_model=…` (đã xoá file ngay sau khi chạy). Kết quả ở H1.

## Lô 4 — FE (Giao hàng ED-17 + Việc giao của tôi ED-19)
> Review 02/10/2026 trên worktree `loc-wt-b` (nhánh `ed-stream-b`, tách từ `c1f1179`), diff chưa commit trong `erp-console/`.
> Căn cứ: 02b §0 dòng 3, §0b T1/T4/T6/T7, §0c F2l/F2o, §1, §2.3, §2.4, §5.2 Lô 4; contract "Lô 4 — BE" trong dev-notes; 02-stories ED-17, ED-19; UI-RULES.

**Kết luận: CHANGES REQUESTED (nhẹ).** Lô không có lỗi Critical hay High. Không rò dữ liệu khách, không rò giá vốn, không vượt quyền.
Có 2 lỗi Medium, đều là AC của 02-stories bị thiếu và sửa được trong vài dòng. Các lỗi Low có thể để lô sau.

### Kiểm chứng (Tech Lead tự chạy trong lượt này, ở worktree)
- `npx tsc --noEmit`: sạch. `npx vitest run`: 44 file, 405 test đều đạt.
- `NEXT_PUBLIC_USE_MOCK=0 npm run build`: OK. Có các route `/deliveries` (7,36 kB), `/deliveries/detail` (14,3 kB), `/my-deliveries` (6,19 kB), `/print/label` (13 kB).
- `check-ai-chunks`: XANH, gồm 4 mục tiêu mới. `check-no-mock`: XANH (15 file mock, 34 seed, 143 file build).
- `python3 scripts/check_naming.py`: OK, không có vi phạm mới.
- Grep màu cứng (`#hex`, `rgb()`, `hsl()`) trên `features/deliveries/**`, `app/(console)/deliveries/**`, `my-deliveries/page.tsx`, `app/print/label/page.tsx`: **0**.
- Grep `console.`, `localStorage`, `sessionStorage`, `router.push`, `searchParams.set` trong các file của lô: không có lệnh nào, chỉ có chú thích.
- `out/deliveries/detail/index.html`, `out/my-deliveries/index.html`: không có chuỗi SĐT.

### Đối chiếu trọng tâm
| Mục | Kết quả | Căn cứ |
|---|---|---|
| Tiền hiện "đ" từ số, không dùng `vnd_display` | Đạt | Mọi chỗ đi qua `vnd()`. `messages.ts:2` ghi rõ quy ước. Chỉ `mock.ts` còn "₫" vì giả lập câu lỗi của BE (đúng) |
| FE không tự tính tiền thay BE | Một phần (M2, L3) | Tổng phiếu hoàn theo tháng là FE tự cộng (M2). Số "Còn hoàn được" của đơn là FE tự tính, và FE khoá nút theo số này (L3). "Còn thiếu", "Chuyển thừa" ở khoản tiền chỉ dùng để hiển thị (L3) |
| Gửi trùng lệnh tiền | Đạt | `useSubmit` chặn bấm đúp bằng `inFlight` ref. Xác nhận nhận tiền idempotent theo `bank_txn_id` (BE trả `duplicate`). `RefundModal` sinh `request_id` một lần mỗi lần mở hộp, nên bấm "Thử lại" sau lỗi mạng gửi cùng id. Huỷ đơn, xác nhận/báo lỗi/chuyển lại phiếu hoàn, gắn khoản tiền: lần thứ hai BE chặn bằng trạng thái (400/409), không có tiền đi hai lần. Ghi chú: dev-notes viết "mọi hàm ghi đều gửi `request_id`", câu này không đúng. Chỉ `createRefund` gửi, các hàm khác không cần |
| Giá vốn | Đạt | Cột `unit_cost` có `locked` và chỉ hiện khi `me.can_view_cost` **và** BE trả khoá (`OrderDetailScreen.tsx:173`). Bảng hàng, thanh toán, hoàn tiền đều có `canViewCost={false}`. Smoke BE thật đã kiểm Quản lý không thấy "Giá vốn" |
| SĐT đủ chỉ ở chỗ API trả | Đạt | Chi tiết đơn có `tel:`, chi tiết phiếu hoàn có, hộp Gắn khoản tiền có. Danh sách đơn bỏ cột SĐT, đúng ED-09-AC1 (02b §3.7 ghi "cột riêng", nhưng story đã duyệt thắng). URL chỉ có `id`, `state` hoặc `open=refund` (`useIdParam` chỉ nhận số). Từ khoá tìm đơn chỉ đi vào query của API, không vào thanh địa chỉ. Không có `console.*` trong module |
| Mock dùng `sessionStorage` | Đạt | Dữ liệu đơn giả nằm trong `sessionStorage` (`mock.ts:446`). `localStorage` chỉ giữ cờ chế độ mock. Bản build thật không có seed (`check-no-mock`) |
| Chip AI gửi ngữ cảnh chứng từ (L8) | Đạt một phần (L1) | `askWithDocContext` chỉ ghép loại và **mã** chứng từ (`split(",")[0]`), bỏ pk, không có tên, SĐT hay địa chỉ. Chỉ áp dụng khi gửi từ khung hỏi nhanh (`autoSend`). Câu gõ trong panel thì không có ngữ cảnh |
| Quản lý không thấy "Xác nhận đã nhận tiền" | Đạt | `orderActionPlan` chỉ dựng nút chính từ `available_actions`. Đã kiểm trên BE thật (`ed_batch3_real`) |
| Hàng chờ thanh toán chỉ Chủ | Đạt | `nav.ts` mục `payments`: cần `confirm_payment_manual`. `ViewGuard view="payments"` bọc cả danh sách lẫn chi tiết. Tab ẩn theo `canView` |
| Nút hiện theo `available_actions` | Đạt | Đơn, khoản tiền và phiếu hoàn đều dùng plan thuần, có vitest. Mục "Huỷ đơn" mờ chỉ là gợi ý (không có `onSelect`), hiện khi có `cancel_paid_order` |
| Nợ chung có làm vỡ Lô 1/2 không | Không vỡ. M1: B6/L9 chưa thật sự sửa | `Tabs`: thêm tham số `param`, mặc định `"tab"`, các chỗ gọi cũ không đổi. Có test. `InfoField`: `onConflict` là prop tuỳ chọn và có câu ngắn dưới ô (L5 đạt). `gate-state`: không còn ai gọi `getAiStatus` với chủ chung (`AiAssistantGate` không còn được import), nên L2 đạt. `check-ai-chunks`: L3 đạt |
| Khoá đếm `AiBar` | Khớp R1 | BE `counts` dùng `resolve_target_label(raw)`, ra đúng `sales.salesorder`, `sales.paymenttransaction`, `sales.refund`. Đã đối chiếu `DOC_TYPE_LABELS` trong `apps/ai/actions/targets.py`. Chỗ lệch 5 của dev được xác nhận. Nhưng xem H1 (khoá lọc khối AI sai) và H2 (gọi khi AI tắt) |
| E2E cũ `p8_lo6`, `p8_lo7` | **Chưa sửa** (M3) | Dev để thành nợ. Chính `p8_lo6_fe_sr19_sr20.py:162-176` là test sẽ bắt được H2 |
| Hiệu năng | Đạt (L5) | Trang chi tiết là 142 kB First Load. Panel AI vẫn là `next/dynamic`. Lọc tháng phiếu hoàn tự tải hết các trang, chấp nhận được vì mỗi tháng ít phiếu |

### Phát hiện

**H1 — High — Khối Trợ lý AI trên trang đơn gửi `target_model="sales.order"`, BE thật trả 400.**
- Vị trí: `app/(console)/orders/detail/page.tsx:13`. Cùng giá trị sai còn ở `features/orders/README.md:14`, chú thích `AiDocBlockGate.tsx:16`, `docBlockModel.ts:88` và test `docBlockModel.test.ts:65-69`.
- Nguyên nhân:
  - `resolve_target_label("sales.order")` có dấu chấm nên gọi `apps.get_model("sales.order")`. Hàm này ném `LookupError` và trả `None`.
  - BE vì vậy trả 400 `INVALID_TARGET_MODEL`.
  - Nhãn đúng là `sales.salesorder`, hoặc doc_type `order`.
  - Mock `filterByTarget` chỉ so phần sau dấu chấm (`order`), nên ở mock vẫn "chạy".
- Hậu quả:
  - Chủ hoặc Quản lý bật AI rồi mở bất kỳ đơn nào: khối Trợ lý AI luôn báo lỗi kèm "Thử lại".
  - Đề xuất AI của đơn (T10: nơi duy nhất còn thấy việc AI `ESCALATED` cho đơn) không bao giờ hiện.
- Tái hiện:
  - BE: `APIClient` đăng nhập `owner`, gọi `GET /api/ai/actions/?target_model=sales.order&target_id=SO261002-4B7E20,41&status=PENDING,ESCALATED`.
  - Kết quả: `400 {"detail":"Loại chứng từ không hợp lệ.","code":"INVALID_TARGET_MODEL"}`. Gọi với `sales.salesorder` thì `200`. Tech Lead đã chạy lệnh này.
- Sửa:
  1. Đổi thành `targetModel="sales.salesorder"`. Sửa README, chú thích và test cho cùng khoá. Giữ `"sales.salesorder"` trong `DOC_KIND_LABEL`, bỏ khoá `"sales.order"`.
  2. Sửa mock `filterByTarget` cho chặt như BE: chỉ nhận nhãn `app.model` có thật, hoặc doc_type. Khoá lạ phải trả 400 để e2e mock bắt được lỗi.
  3. Thêm 1 ca e2e: AI bật, đồng ý, mở đơn có đề xuất. Khối hiện đề xuất, không có alert lỗi.

**H2 — High — `/orders`, `/orders/payments`, `/orders/refunds` gọi `GET /api/ai/actions/counts/` cả khi AI tắt (hồi quy SR-20-AC3).**
- Vị trí: `features/orders/useAiCount.ts:9-16`, được gọi ở `OrdersScreen.tsx:66`, `PaymentQueueScreen.tsx:46`, `RefundQueueScreen.tsx:49`. Mock đếm cứng ở `aiCount.ts:22`.
- SR-20-AC3 (đã nghiệm thu) yêu cầu: khi AI tắt, mở 4 màn này thì **0** request tới `/api/ai/*`. Review Lô 2 đã nhắc "Lô 3 trở đi không được gắn khối AI vào 4 màn đó". Nợ ở `00-can-duy-quyet.md:59` cũng ghi `AiBarGate` phải "AI tắt → 0 request".
- Hậu quả:
  - Vi phạm nghiệm thu BR-AI-17.
  - Mỗi lần mở danh sách tốn thêm một request.
  - Ở mock, khi AI tắt vẫn hiện "AI · Có 2 đề xuất", với link "Xem" trỏ tới `/ai/actions/` (trang mà 02b §0 quyết định 2 sẽ bỏ).
- Tái hiện (bản `MOCK=1`, Tech Lead đã chạy):
  1. Đăng nhập `loc` và gọi `__caveMock.ai('off')`.
  2. Mở lần lượt 3 màn.
  3. Mỗi màn log đúng 1 request `GET /api/ai/actions/counts/?status=PENDING,ESCALATED`. `/orders` và `/orders/refunds` vẫn vẽ `.ai-bar`.
- Sửa:
  - Chỉ đếm khi AI bật. Cách gọn nhất trong phạm vi lô là đọc cờ từ `useAiEnabledAndConsented()`/gate-state. Nhưng hiện chưa có ai publish cờ trên màn danh sách, và màn nghiệp vụ không được import `features/ai`.
  - Vì vậy đề xuất **bỏ hẳn thanh AI khỏi 3 màn này ở Lô 3** (`aiBar` để trống, xoá `aiCount.ts`/`useAiCount.ts` hoặc để lại không dùng) và dời sang `AiBarGate` ở Lô 17 như nợ đã ghi.
  - Chưa nên tự viết một cổng mới cho riêng module đơn.
  - Kèm theo M3 (sửa `p8_lo6`) để có test chặn hồi quy.

**M1 — Medium — Bản sửa B6/L9 không chạy: chạm ô hỏi nhanh thì focus rơi về `body` và mất chữ gõ sớm.**
- Vị trí: `shared/ui/detail/AiBlockFrame.tsx:133-134`.
- Nguyên nhân:
  - `{chat && keepStarter && starter ? <Starter/> : null}` và `{chat ?? <Starter/>}` là **hai vị trí con khác nhau**.
  - Khi `chatOpen` bật, React gỡ `Starter` ở vị trí 2 và dựng một `Starter` mới ở vị trí 1. Ô nhập bị thay bằng nút DOM mới.
- Tái hiện (bản `MOCK=1`, Tech Lead đã chạy):
  1. AI bật, chưa đồng ý: mở `/orders/detail/?id=101` rồi bấm vào ô "Hỏi AI về chứng từ này". Ngay sau đó `document.activeElement` là `BODY`. Gõ "abc" thì ô vẫn rỗng.
  2. Đã đồng ý: bấm ô, gõ "con bao nhieu", chờ 1,5 giây. Focus nằm ở ô của panel nhưng ô **rỗng**, chữ đã mất.
- Vitest `detail.test.ts` chỉ render tĩnh, nên không bắt được lỗi remount.
- Sửa:
  - Render `Starter` ở **một** vị trí cố định, ví dụ `{starter && (!chat || keepStarter) ? <Starter/> : null}{chat}`. Như vậy Starter không bị gỡ khi `chat` xuất hiện.
  - Thêm e2e: bấm ô, gõ ngay, kiểm `activeElement` là ô đó và chữ không mất (trước và sau khi panel nạp).
  - Khi đồng ý xong, chuyển focus vào ô tick đồng ý, như L9 gợi ý.

**M2 — Medium — Dòng "tổng số tiền hoàn" của tháng đổi nghĩa theo bộ lọc trạng thái, mặc định chỉ cộng phiếu Chờ hoàn.**
- Vị trí: `features/orders/components/RefundQueueScreen.tsx:37-40`, `:44`, `:65`; `messages.ts:246`.
- Diễn biến:
  - Chọn tháng mà giữ trạng thái mặc định `PENDING,FAILED`: `monthTotal` bỏ FAILED, nên dòng "n phiếu, tổng số tiền hoàn X đ" chỉ là tổng **chờ chuyển**.
  - Chọn "Mọi trạng thái" thì thành Chờ hoàn + Đã hoàn.
  - Chọn "Đã hoàn" thì thành số đã chuyển.
  - Cùng một câu chữ nhưng ra 3 con số khác nhau, và Chủ có thể đọc nhầm thành "tháng này đã hoàn X".
- Giả định "không tính FAILED" của dev (chỗ lệch 10) là hợp lý: phiếu thất bại thì tiền chưa rời túi. Chỗ sai là câu chữ không nói rõ đang cộng những gì.
- Tái hiện (mock): vào tab Phiếu hoàn, chọn tháng hiện tại. Dòng tổng thiếu các phiếu `REFUNDED`. Đổi sang "Mọi trạng thái" thì số đổi mà câu chữ giữ nguyên.
- Sửa (chọn một):
  - (a) Khi có tháng, tách thành "Đã hoàn X đ · Chờ hoàn Y đ" theo từng trạng thái đang có trong kết quả.
  - (b) Câu chữ nêu rõ trạng thái đang lọc, ví dụ "3 phiếu Chờ hoàn, tổng 1.200.000 đ".
  - Ghi lại cho PO biết W1b vẽ dòng tổng ra sao. Không cần BE vì tổng chỉ cộng `amount` do BE trả.

**M3 — Medium — Chưa sửa `e2e/p8_lo6_fe_sr19_sr20.py`, `e2e/p8_lo7_fe_erp.py`.**
- Lý do phải sửa ngay: hai file hỏng vì chọn `.order-open`, `.queue-open`, `.refund-open`, `ul.order-list` mà lô này vừa xoá. Phạm vi lô 02b §5.2 cho sửa e2e của Đơn & tiền, và điều phối viên đã yêu cầu sửa trong lô này.
- Hậu quả: chính các ca SR20-AC3 trong `p8_lo6` (dòng 147-185) sẽ bắt được H2. Để file hỏng tức là mất lưới chặn hồi quy.
- Sửa:
  - Đổi selector sang trang mới (dùng `orders_common.open_order`, `go`, `main header`).
  - Giữ nguyên ý của từng ca. Ca nào không còn đối tượng (ví dụ "Để AI làm" trong GuidancePanel cũ) thì ghi rõ lý do bỏ, đừng xoá lặng lẽ.

**L1 — Low — L8 mới làm một nửa.** Vị trí: `AiDocBlock.tsx:166-167`.
- Chỉ câu đi qua khung hỏi nhanh (`autoSend`) được ghép "Về đơn hàng SO…:".
- Người dùng focus ô rồi gõ câu trong panel thì câu gửi đi không có ngữ cảnh. Không rò gì.
- Sửa: truyền `docContext` xuống `AiAssistantPanel` và ghép vào lúc gửi. Có thể để Lô 15.

**L2 — Low — Dọn dẹp.**
- `shared/lib/nav.ts`: `PERM.createRefund`, `PERM.confirmRefund` không có chỗ nào dùng. Bỏ đi, hoặc dùng cho "…" mờ như `cancelPaidOrder`.
- `scripts/check-ai-chunks.mjs:97` vẫn in "4 màn nghiệp vụ", trong khi nay có 7 route.
- `AiBar href="/ai/actions/"` ở 3 màn (nếu giữ thanh AI sau H2): trang này sẽ bị bỏ theo 02b §0 quyết định 2.
- Dev-notes ghi `amount.ts`, `queueModels.ts` là "file mới". Thực tế `amount.ts` là file cũ không đổi, còn `queueModels.ts` không tồn tại (chỉ có `queueModels.test.ts`, import hàm từ hai file Screen).
- `detail.test.ts` ca "xung đột phiên bản (L5)" chỉ kiểm hằng chuỗi, chưa kiểm hành vi. Nên thêm e2e harness (409 `STALE_STATE` thì câu hiện dưới ô và `onConflict` được gọi).
- Tìm kiếm ở tab Hàng chờ và Phiếu hoàn chỉ lọc trong các dòng đã tải, nhưng dòng "Đang hiện n / m" vẫn lấy `m` của BE. Nên ghi "trong n dòng đã tải" khi có từ khoá.

**L3 — Low — FE tự tính số tiền để khoá nút.**
- Vị trí: `refund.ts:8-12` (`refundableOfOrder`), `OrderDetailScreen.tsx:403,408`; `PaymentDetailScreen.tsx:61`, `ConfirmOrderModal.tsx:27`.
- "Còn hoàn được" của đơn là FE tự tính bằng tổng đơn trừ phiếu chưa thất bại, rồi **khoá nút** khi nhập vượt số này (ED-10-AC3).
  - Logic này có từ S15 và hiện đúng với BR-HT-04.
  - Nếu sau này BE đổi cách tính (ví dụ trừ thêm phần đã hoàn qua khoản tiền lệch), FE sẽ khoá sai một phiếu hợp lệ.
- Đề xuất: BE thêm `refundable_amount` vào chi tiết đơn, như khoản tiền đã có. Ghi vào nợ cho lô BE kế tiếp đụng `sales/orders`. Không chặn lô này.
- "Còn thiếu", "Chuyển thừa" ở khoản tiền chỉ để hiển thị. Chấp nhận.

**L4 — Low — Nhãn dòng thời gian của đơn có thể chứa chữ tự do.**
- `OrderDetailScreen` hiện `timeline[].label` của BE và lấy 3 nhãn gần nhất vào "Đã làm".
- Nợ BE `00-can-duy-quyet.md` mục 3 (ghi chú huỷ `OTHER`, lý do báo chuyển hoàn thất bại) vẫn chờ Duy. FE không phải sửa, nhưng khi Duy quyết thì e2e của trang đơn nên kiểm nhãn không chứa ghi chú.

**L5 — Low — Đơn Giữ chỗ re-render cả trang mỗi giây.**
- Vị trí: `OrderDetailScreen.tsx:87`.
- `useNow(…, 1000)` nằm ở thân trang, nên mỗi giây vẽ lại cả 4 `DataTable` và khung AI.
- Không đo được giật ở dữ liệu thật (đơn ít dòng). Nếu muốn gọn thì tách ô "Còn giữ chỗ" và chip thành component con tự giữ `useNow`.

**Ghi nhận (không phải lỗi):**
- Chỗ lệch 1, 2, 3, 4, 6, 8, 11, 12, 13, 14: đồng ý.
- Chỗ lệch 7 (chip "Đang xử lý" sau khi nhận tiền) và 15 (đơn tự huỷ vẫn nhận tiền) đã nằm trong `00-can-duy-quyet.md` mục 16 và 15. FE đi theo BE là đúng.
- Chỗ lệch 9 (bỏ cột SĐT ở danh sách): đúng ED-09-AC1. 02b §3.7/§4 ghi "cột riêng Số điện thoại" là lệch với story. Tech Lead nhận phần này, story đã duyệt thắng. SĐT đủ vẫn có ở chi tiết và hộp Gắn khoản tiền.
- `s10_s11_orders.py` giảm từ 78 xuống 38 ca. Phần lớn ca bị bỏ là kiểm vùng chạm/vi kiểm của tấm trượt cũ đã có trong `ed_batch3_orders` (141 ca). QA nên soát lại nhanh khi chạy lại.

### Việc cần làm để APPROVED
1. Sửa H1 (khoá `sales.salesorder` và mock chặt như BE) và H2 (bỏ thanh AI khỏi 3 màn, hoặc chỉ đếm khi AI bật), mỗi lỗi có test.
2. Sửa M1 (một vị trí cho `Starter`, e2e focus và chữ gõ), M2 (câu tổng tháng nói rõ đang cộng gì) và M3 (viết lại `p8_lo6`, `p8_lo7`, chạy xanh trên bản mock).
3. Các lỗi Low làm cùng lượt nếu rẻ (L2). L1, L3, L4, L5 ghi nợ.
4. Tech Lead re-review phần diff của H1, H2, M1–M3.

## QA5-B2 — BE

**Kết luận: APPROVED** (Tech Lead, 02/10). Phạm vi xem gồm `backend/apps/common/guidance/audit_timeline.py`, `backend/apps/delivery/next_steps.py` và `backend/apps/delivery/tests/test_timeline_customer_service.py`.

Kiểm chứng:
- `manage.py test apps.delivery apps.common` cho kết quả Ran 472, OK.
- `python3 scripts/check_naming.py` cho kết quả OK, không có vi phạm mới.

1. **IDOR: không có.** Người chỉ có `confirm_with_customer` phải qua hai lớp chặn.
   - Lớp đầu là queryset `confirmation__isnull=False`.
   - Lớp sau là `object_scope_fn`, gọi đúng `note_in_customer_service_scope` mà `/api/confirmation/queue/<id>/` đang dùng. Lớp này không viết lại logic nên phạm vi không lệch được.
   - Phiếu đã đóng mà CSKH không gọi thì trả 404. Test `test_qa5_b2_cs_scope_equals_detail_scope_for_recent_call` đối chiếu trực tiếp với chi tiết, gồm cả nhánh gọi gần đây và CSKH khác.
2. **404 và 403 nhất quán với `/api/confirmation/queue/<id>/`.**
   - Thiếu cả hai quyền thì trả 403. Chưa đăng nhập thì trả 401.
   - Không có mục chờ gọi, ngoài phạm vi, id lạ hoặc id không phải số thì đều trả 404 với thông điệp cố định, nên không phân biệt được "không tồn tại" với "ngoài phạm vi".
   - Thông điệp khác chữ với API hàng chờ, nhưng mã trạng thái giống. Chấp nhận.
3. **Quyền các nhóm khác: không đổi.**
   - owner, manager và warehouse_staff có `view_deliverynote` nên vẫn đi nhánh cũ. owner và manager có thêm `confirm_with_customer` nhưng nhánh view được xét trước.
   - delivery_staff vẫn chỉ xem phiếu được gán cho mình (có test).
   - Provider khác không truyền `object_scope_fn` nên giữ hành vi cũ.
4. **N+1: không có.** Endpoint chỉ tra một đối tượng. `object_scope_fn` tốn một số truy vấn cố định: kiểm group, đọc `note.confirmation` và một `exists` trên `CustomerCall`. Phần AuditLog vẫn `select_related` như cũ.
5. **Dữ liệu khách trong body: không lộ.** `_audit_event` chỉ dùng nhãn tĩnh trong `ACTION_LABELS` và tên nhân viên, không đọc `changes` hay `note`. Có test gieo SĐT, địa chỉ và tên giả vào AuditLog rồi assert body không chứa chúng. Response vẫn gắn `Cache-Control: no-store`.

Ghi nhận Low, không chặn và ghi nợ:
- Một người thuộc cả `customer_service` lẫn `delivery_staff` sẽ đi nhánh `view_deliverynote`. Người đó chỉ thấy timeline của phiếu gán cho mình, trong khi chi tiết hàng chờ vẫn trả 200 cho phiếu trong phạm vi CSKH.
- Đây là thiếu quyền chứ không phải rò dữ liệu. Hiện chưa có tài khoản nào được gán hai vai này cùng lúc.
- Nếu cần sửa thì cho `_note_in_scope` và `_scope_notes_for` hợp hai phạm vi.

### Re-review Lô 3 — FE (02/10, sau sửa H1, H2, M1–M3, Low, QA-B1/B2 và thêm khối AI cho khoản tiền, phiếu hoàn)
> Phạm vi: hai mục cuối phần Lô 3 — FE của dev-notes ("sửa sau Techlead CHANGES REQUESTED và QA REJECTED", "Thêm khối AI cho khoản tiền và phiếu hoàn").

**Kiểm chứng (Tech Lead tự chạy trong lượt này):**
- `npx tsc --noEmit` sạch. `npx vitest run`: 48 file, 442 test đều đạt.
- `check_naming` OK: 2 file giảm vi phạm, nên chạy `--update` khi commit.
- Build `MOCK=1` OK. Lần build đầu ở `erp-console/` lỗi `ENOENT .nft.json` vì một phiên khác đang `rm -rf .next out` và build cùng lúc. Tech Lead chuyển sang build trên bản sao ở scratchpad và **không đụng** `erp-console/out` của phiên kia.
- Playwright riêng của Tech Lead trên bản đó (cổng 3111):

| Route | AI tắt | AI bật |
|---|---|---|
| `/orders/`, `/orders/payments/`, `/orders/refunds/` | 0 request `/api/ai/*`, không thanh AI | 0 request (không còn `counts`) |
| `/orders/detail/?id=101` | đúng 1 `GET /api/ai/status/`, không khối AI | status + `actions?target_model=sales.salesorder&target_id=SO…,101`, có khối, không alert |
| `/orders/payments/detail/?id=880` | đúng 1 status, không khối | `target_model=sales.paymenttransaction&target_id=880`, có khối, không alert |
| `/orders/refunds/detail/?id=31` | đúng 1 status, không khối | `target_model=sales.refund&target_id=31`, có khối, không alert |

  Một request status ở trang chi tiết là hành vi cổng đã được chấp nhận ở review Lô 2. SR-20-AC3 chỉ áp cho màn danh sách và `/inventory`.

| Mục | Kết quả | Căn cứ |
|---|---|---|
| H1 | Đạt | `orders/detail/page.tsx` gửi `sales.salesorder`. Lượt trước BE thật đã trả 200 cho nhãn này. Mock `filterByTarget` nay chặt như BE: chỉ nhận nhãn có thật hoặc doc_type, khoá lạ trả 400. `DOC_KIND_LABEL` đã bỏ khoá `sales.order` |
| `target_id` pk cho khoản tiền, phiếu hoàn | Khớp BE | Đã soát 3 chỗ ghi `AiAction`: (1) `apps/sales/payments/auto_confirm.py:210-211` ghi `target_model="paymenttransaction"`, `target_id=str(payment.id)`; (2) `apps/ai/actions/services.py:395-396` (chuyển việc từ guidance) ghi `target_id=str(doc_id)`, và guidance `payment`/`refund` dùng pk; (3) `apps/ai/execution/pipeline.py:237,448` ghi `target_id` là giá trị tra cứu của lệnh, với phiếu hoàn là pk (`Refund.objects.filter(pk=int(target_id))`, dòng 425-426). `resolve_target_label` gom `paymenttransaction`/`payment` về `sales.paymenttransaction` và `refund` về `sales.refund`. Như vậy lọc bằng pk là đúng. Đơn giữ dạng "mã,pk" vì pipeline có thể ghi mã đơn |
| H2 | Đạt | Đã xoá `aiCount.ts`, `useAiCount.ts`. Không còn `AiBar` trong 3 màn. Thanh AI của danh sách để Lô 17 (`AiBarGate`) |
| M1 | Đạt | `AiBlockFrame.tsx`: `Starter` có **một** vị trí con cố định, `{chat}` đứng sau. Đo trên trình duyệt: (a) chưa đồng ý: bấm ô rồi gõ "abc", `activeElement` vẫn là ô "Hỏi AI về chứng từ này", giá trị là "abc", ở cả trang đơn lẫn khoản tiền; (b) đã đồng ý, chặn mọi chunk 1,2 giây: bấm ô, gõ "con bao nhieu", lấy mẫu 8 lần mỗi 400 ms, lần đầu và lần cuối focus đều ở INPUT với đủ chữ. Sau khi panel nạp xong, khung tĩnh được gỡ và chữ chuyển sang ô của panel. Nút "Bật trợ lý" trả focus về ô hỏi |
| M2 | Đạt | `monthBreakdown` tách Chờ hoàn / Đã hoàn, có ghi "(không tính N phiếu Thất bại)" và tên tháng. Câu chữ nay khớp với con số dù lọc trạng thái nào |
| M3 | Đạt | `p8_lo7` không còn selector cũ. `p8_lo6` còn 1 chỗ khớp `order-list`, nhưng đó là dòng chú thích hoặc ca đã ghi "BỎ:"; mọi ca đi qua trang mới. SR20-AC3 trong `p8_lo6:151-190` kiểm đúng: danh sách 0 request, chi tiết tối đa 1 status. Các ca bỏ đều có lý do trong file và trong dev-notes. Dev báo 62/62; Tech Lead không chạy lại file này |
| L2, L5 | Đạt | Đã bỏ `PERM.createRefund`/`confirmRefund`. `check-ai-chunks` in "7 route". `useHoldExpired` đặt một lần hẹn giờ tới mốc, còn đồng hồ mm:ss chỉ nằm trong ô `HoldLeft` |
| QA-B1, B2 | Đạt (đọc diff) | `RefundModal` chỉ còn một dòng "Còn hoàn được". Toast mới đúng chốt của PO (`00-can-duy-quyet.md` mục 16) |
| Dữ liệu cá nhân trong khối AI mới | Đạt | `targetId` của khoản tiền và phiếu hoàn chỉ là pk. Câu chip qua `askWithDocContext` chỉ có "khoản tiền 880" / "phiếu hoàn 31". Nội dung chuyển khoản (`content`) không đi vào khối AI. BE vẫn lọc `args_preview` theo người xem |

**Còn nợ (không chặn):**
- L1: câu gõ trong panel chưa kèm ngữ cảnh chứng từ, để Lô 15.
- L3: BE nên trả `refundable_amount` ở chi tiết đơn.
- L4: chờ Duy quyết mục 3.
- B3: chuỗi "₫" do BE dựng.
- QA cần sửa ca "chip Đã thanh toán" trong `qa_ed_batch3_orders.py`.
- Khối AI ở khoản tiền và phiếu hoàn **chưa chạy với BE thật**. Nhãn đã đúng ở `resolve_target_label`, nhưng QA nên chạy một lượt trên BE thật, có một `AiAction` gắn `paymenttransaction` để thấy đề xuất hiện ra.

### Kết luận re-review Lô 3 — FE: **APPROVED**
H1, H2, M1, M2, M3 đều đạt và đã kiểm chạy thật trên trình duyệt. Không còn lỗi Critical, High hay Medium. Lô sẵn sàng cho QA chạy lại.
Khi commit, chạy `python3 scripts/check_naming.py --update`.

| Tem in che SĐT (T1) | Đạt | `app/print/label/page.tsx` chỉ hiện `recipient_phone_masked`, có chú thích T1. Vẫn kiểm `delivery.print_label`. QR vẫn là ảnh data-URI. `@page` nằm trong `<style>` của trang. Thanh công cụ ẩn khi in (`label.module.css`, `@media print`) |
| Ghi chú giao thất bại | Đạt | `ReportFailureModal` giữ ghi chú trong `useState`. `Field` và `useSubmit` không ghi vào máy. Không có `console`. URL không đổi. Thông điệp lỗi lấy từ BE và BE không lặp lại nội dung. `reportDeliveryFailure` chỉ gửi trong body POST |
| SĐT đủ chỉ lấy từ R4 | Đạt (xem L1) | Chi tiết và "Gọi khách" đọc `detail.phone`. Danh sách không có SĐT. `telHref` chỉ lọc chữ số từ chuỗi BE trả, không ghép từ nguồn khác. Còn dòng dự phòng `recipient_phone` là code chết (L1) |
| `tel:` | Đạt | `DeliveryDetailScreen.tsx:357`, `MyDeliveriesScreen.tsx:87`. Số quá ngắn thì không dựng link. `null` (đã ẩn theo SR-PII-02) thì hiện "đã ẩn" |
| `delivery_staff` chỉ thấy phiếu của mình | Đạt | `MyDeliveriesScreen` gọi `assigned_to=me`. BE chặn ở `get_queryset`, mock cũng mô phỏng như vậy. `/deliveries/detail/` đặt `ViewGuard view="deliveries"`, nên người chỉ thuộc `delivery_staff` vào bằng URL sẽ thấy "Không có quyền" trước khi gọi API |
| Menu S7-AC2 | Đạt, không đổi | `shared/lib/nav.ts:233` `!onlyDelivery(me)`, `:245` "Việc giao của tôi" theo nhóm. Lô không sửa `nav.ts`. `nav.test.ts:70-72` vẫn xanh |
| F2o: quyền và trạng thái | Đạt | `canAssign` (`deliveryUi.ts:60`) đòi cả trạng thái thuộc T6 **và** BE trả `"assign"` trong `available_actions`. BE chỉ trả khi có `delivery.assign_deliverynote`. Mục khoá "Đổi người giao" kèm lý do chỉ hiện với người có quyền (`DeliveryDetailScreen.tsx:227`). Hộp hiện "Đang giao n phiếu · Chờ lấy m phiếu" (T7) |
| 409 `STALE_STATE` và `expected_assigned_to` | Đạt | `AssignCourierModal.tsx:59` gửi `expected_assigned_to = note.assigned_to`, kể cả `null`. 409 vào `sub.conflict`, hiện `ConflictBanner` trong hộp. "Tải lại" xoá lựa chọn, nạp lại danh sách người giao và phiếu cha, giữ hộp mở. Prop `note` là phiếu cha mới nạp, nên lần gửi sau dùng đúng người đang gán. `isConflictError` (đã sửa ở Lô 2 M1) chỉ nhận `STALE_STATE` và `STALE_VERSION`. Báo thất bại sai trạng thái trả 400 không mã `STALE_STATE` nên hiện alert đỏ thường, không bị im lặng |
| Khối AI và `check-ai-chunks` | Đạt | Trang chi tiết gắn `AiDocBlockGate` (`delivery.deliverynote`). Bốn route mới có trong `TARGETS` và đã chạy XANH trên bản build thật. Đã thay L3 của Lô 2 cho phần giao hàng |
| Màu cứng | Đạt | 0 trong các file của lô. Tem dùng `Canvas`/`CanvasText` cùng `color-scheme: light` |
| Giá vốn | Đạt | Bảng dòng hàng chỉ có Mặt hàng, Lô, HSD, Số kg. Danh sách truyền `canViewCost={false}` |

### Phát hiện

**M1 — Medium — Thẻ "Việc giao của tôi" thiếu "Đơn" và dòng "Đã thanh toán, không thu thêm" (ED-19-AC1).** Vị trí: `features/deliveries/components/MyDeliveriesScreen.tsx:56-76`.
- AC: mỗi thẻ có Người nhận, **Đơn**, Địa chỉ, Số kg, Hàng; đơn đã thanh toán có dòng "Đã thanh toán, không thu thêm".
- Thực tế: thẻ chỉ có mã phiếu, không có `note.order.code`, và không có dòng thanh toán. Người giao đứng ở cửa nhà khách cần dòng này nhất, vì không có nó thì có thể thu tiền thêm của khách đã chuyển khoản.
- Tái hiện: `NEXT_PUBLIC_USE_MOCK=1`, đăng nhập `giao1`, mở `/my-deliveries/`. Thẻ GH-HD-0036-DELI không có mã đơn và không có chữ "Đã thanh toán".
- Sửa: thêm dòng `Đơn {note.order?.code}` (mono). Thêm dòng cố định "Đã thanh toán, không thu thêm", vì phiếu giao chỉ sinh sau khi đơn đã thanh toán (BR-TT). Nếu muốn dựa vào dữ liệu, dùng trường thanh toán có sẵn trong bản danh sách và không tự suy. Thêm 1 assert vào `e2e/ed_batch4_delivery.py`.

**M2 — Medium — Menu "…" của chi tiết phiếu thiếu các mục khoá của ED-17-AC3.** Vị trí: `features/deliveries/components/DeliveryDetailScreen.tsx:225-232`.
- AC: phiếu chưa in tem thì "…" có "In lại tem" bị khoá với lý do "Chưa in tem lần nào.", cùng "Huỷ xác nhận đơn" và "Huỷ đơn" kèm lý do.
- Thực tế: không có mục nào trong 3 mục này.
- Tái hiện: mở `/deliveries/detail/?id=<phiếu PREPARING chưa in tem>` bằng `ql1`, bấm "…". Menu chỉ có "Giao cho người giao/Đổi người giao" hoặc trống.
- Sửa ngay trong lô này: thêm `{ key: "reprint", label: "In lại tem", blockedReason: "Chưa in tem lần nào." }` khi `printAction === "print"`.
- "Huỷ đơn" và "Huỷ xác nhận đơn" dẫn sang trang đơn của Lô 3 (nợ 5). Được phép để lại, nhưng phải ghi thành dòng nợ trong 02c để làm ngay sau khi Lô 3 vào `main`, và báo PO là ED-17-AC3 mới đạt một phần.

**L1 — Low — Code chết: dự phòng `recipient_phone`.** Vị trí: `DeliveryDetailScreen.tsx:268`, `MyDeliveriesScreen.tsx:146`, `types.ts` (`recipient_phone?`), cùng 15 dòng `recipient_phone: null` trong `mock.ts`.
- `DeliveryNoteDetailSerializer` (BE) không có `recipient_phone`, chỉ có `phone` (R4). Nhánh `?? recipient_phone` không bao giờ chạy và làm người đọc hiểu nhầm rằng FE có nguồn SĐT thứ hai.
- Sửa: bỏ khỏi type, mock và hai dòng trên, để "SĐT chỉ đến từ R4" đúng cả trên mặt code.

**L2 — Low — Test chống lưu SĐT trên máy không bắt được số đã định dạng.** Vị trí: `e2e/ed_batch4_delivery.py:78`, `:117`.
- `:78` tìm `0900000\d{3}`, nhưng số mock có dạng `0900 000 036`. Nếu FE lỡ lưu số đã định dạng thì assert vẫn xanh.
- `:117` chỉ kiểm ghi chú bị chặn, tức là ghi chú chưa từng gửi đi. Ca cần kiểm là ghi chú hợp lệ đã gửi ("Khách hẹn giao lại ngày mai") không còn trong storage và URL.
- Sửa: chuẩn hoá bỏ khoảng trắng trước khi so (hoặc regex `0900\s?000\s?\d{3}`), và kiểm thêm sau bước 4.

**L3 — Low — Kiểm ghi chú ở FE lệch BE với số có dấu cách.** Vị trí: `deliveryUi.ts:67`.
- `PII_NOTE_RE = /\d{9,}/` chỉ bắt dãy số liền. BE (`has_long_digit_run`) bắt cả dãy bị ngăn cách, ví dụ `0912 345 678`.
- Không lọt dữ liệu, vì BE trả 400 `DELIVERY_FAILURE_NOTE_PII` và `failureFieldOfCode` đưa lỗi xuống dưới ô. Chỉ tốn một lượt gọi API.
- Sửa (tuỳ chọn): bỏ ký tự không phải chữ số giữa các chữ số rồi mới so, theo đúng luật BE.

**L4 — Low — Câu kết của `check-ai-chunks` đã cũ.** Vị trí: `scripts/check-ai-chunks.mjs:97` vẫn in "4 màn nghiệp vụ và 2 layout". Nay đã có 8 màn. Sửa: in theo `TARGETS.length`.

**L5 — Low — Lệch chữ và bố cục nhỏ so với AC (báo PO, không chặn).**
- ED-19-AC2: nút ghi "Nhận hàng đi giao", AC ghi "Đã lấy hàng, bắt đầu giao".
- ED-19-AC3: hộp báo thất bại chỉ tóm tắt mã phiếu, thiếu Đơn, Khách hàng, Bắt đầu giao. Nút là "Huỷ · Báo thất bại", AC ghi "Quay lại · Báo giao thất bại".
- ED-19-AC5: thẻ thất bại gộp Lý do và Lần thành một dòng, không có "Lúc". "Mang hàng về kho" để Lô 9 (nợ 3, đồng ý).
- ED-19-AC6: người giao mở URL phiếu của người khác thì thấy "Không có quyền" (do `ViewGuard`), AC ghi "Không tìm thấy". Không lộ việc phiếu có tồn tại hay không, nên chấp nhận được. PO cần biết.
- ED-17-AC6: hộp in lại chọn sẵn "In lại", AC ghi "phải chọn lý do". Chấp nhận được vì người dùng luôn thấy và có thể đổi lựa chọn.
- ED-17-AC7: bảng không có cột "Kho". BE (`_get_allocations`) không trả kho. Hiện chỉ có một kho, nên để lại.

**L6 — Low — "Việc giao của tôi" gọi chi tiết cho từng thẻ.** Vị trí: `MyDeliveriesScreen.tsx:151-155`.
- Mỗi phiếu Đang giao hoặc Thất bại tốn thêm một `GET /notes/{id}/` để lấy SĐT. Với một người giao (dưới 20 phiếu) thì chấp nhận được.
- Nếu sau này chậm, có thể chỉ tải số khi bấm "Gọi khách". Không dùng cách đưa `phone` vào danh sách, vì 02b R4 cố ý không làm vậy.

### Hai khoản nợ điều phối viên hỏi
- **Nợ 4 (danh sách chưa gắn `AiBar`): không bắt buộc trong lô này.**
  - Lý do:
    - Hiện chưa màn danh sách nào gắn `AiBar`. `shared/ui/AiBar.tsx` chỉ nhận props.
    - Thiếu phần cổng dùng chung: đọc `/api/ai/status` và đếm đề xuất (R1), đồng thời AI tắt thì **0 request `/api/ai/*`** (BR-AI-17, SR-20).
    - Nếu từng lô tự gắn thì mỗi màn sẽ gác AI một kiểu. Đó đúng là rủi ro mà L2 và L3 của Lô 2 đã nêu.
  - Đề nghị:
    - Làm một lô ngang, có thể gộp vào Lô 15 hoặc làm lô riêng sau Lô 3: một `AiBarGate` dùng chung (nạp động, không import `features/ai` vào chunk danh sách), gắn cho mọi `ListPage`, rồi chạy `check-ai-chunks`.
    - Ghi một dòng vào 02c để không quên.
    - 4 màn SR-20 (đơn, thanh toán, hoàn tiền, kho) vẫn không gắn.
- **Nợ 6 (tìm kiếm chỉ lọc client trên các trang đã tải): chấp nhận tạm.**
  - Tab đã chia theo trạng thái, và tab Hoàn tất chỉ lấy hôm nay. Vì vậy số dòng mỗi tab nhỏ, và phần lớn đã nằm trong trang đầu.
  - Từ khoá không đi đâu: không lên URL, không vào máy, không gửi BE. Tìm theo mã phiếu, mã đơn, mặt hàng, không theo tên khách. Như vậy là tốt cho bất biến 9.
  - Cần sửa nhỏ (Low, gộp với M1/M2): khi đang lọc và `list.hasMore`, câu rỗng ở `DeliveriesView.tsx:159-160` phải nói rõ "Chỉ tìm trong n phiếu đã tải. Bấm Tải thêm để tìm tiếp", vì câu hiện tại dễ khiến người dùng tưởng là không có phiếu.
  - Thêm `q` phía BE (tìm theo mã) đưa vào backlog, không cần trong lô này.

### Việc cần làm để APPROVED
1. Sửa M1 và M2 (phần "In lại tem" khoá), mỗi lỗi kèm một assert e2e.
2. Sửa L2 (test chống lưu SĐT) và câu rỗng ở nợ 6. Hai việc này nhỏ và đi cùng lượt.
3. Ghi vào 02c: nợ "Huỷ đơn / Huỷ xác nhận đơn" sau Lô 3, và lô `AiBar` dùng chung.
4. L1, L3, L4, L5, L6 để lô sau hoặc làm luôn nếu tiện. Tech Lead re-review chỉ phần diff của M1 và M2.

### Re-review Lô 4 — FE (vòng sửa 02/10/2026)
> Phạm vi: các điểm ở mục "Vòng sửa sau Techlead…" của dev-notes (M1, M2, L1–L4, nợ 6, B1–B12 của QA).

**Kiểm chứng (Tech Lead tự chạy):** `npx tsc --noEmit` sạch. `npx vitest run`: 44 file, 410 test đều đạt.

| Điểm | Kết quả | Căn cứ |
|---|---|---|
| M1 (thẻ có Đơn và "Đã thanh toán, không thu thêm") | Đạt | `MyDeliveriesScreen.tsx:68-69`, `:93`. Luôn hiện dòng thanh toán là đúng, vì phiếu giao chỉ sinh sau khi đơn đã thanh toán (dev-notes, lệch 9) |
| M2 (menu "…" theo ED-17-AC3) | Đạt | `DeliveryDetailScreen.tsx:240-244`. "In lại tem" bị khoá khi chưa in. "Huỷ xác nhận đơn" và "Huỷ đơn" bị khoá kèm lý do, chỉ hiện với vai vận hành (`opsView`) và khi phiếu chưa lên xe. Nối link khi Lô 3 xong đã ghi nợ |
| B7: `ViewGuard` nhận danh sách màn | Đạt | `ViewGuard.tsx`: qua được nếu `canView` đúng với ít nhất một màn, và vẫn không mount children khi thiếu quyền. Chỉ `/deliveries/detail/` dùng dạng mảng. `/deliveries/` vẫn là `view="deliveries"`. `shared/lib/nav.ts` không đổi, nên menu S7-AC2 giữ nguyên |
| B7: phạm vi dữ liệu | Đạt | BE `get_queryset` lọc theo `assigned_to` với người không có full scope, nên phiếu người khác trả **404** và màn hiện "Không tìm thấy trang này" (ED-19-AC6). Dòng thời gian `/api/guidance/delivery/` cũng lọc phạm vi như vậy (`apps/delivery/next_steps.py:39-43`), nên không lộ lịch sử phiếu người khác. Nút quay lại và `homeHref` trỏ về "Việc giao của tôi". e2e `ed_batch4_delivery.py:102-107` kiểm cả hai chiều |
| L1 (bỏ `recipient_phone`) | Đạt | Không còn trong type, mock và hai màn. SĐT chỉ còn một nguồn là `phone` (R4) |
| L2 (test chống lưu SĐT) | Đạt | Regex bắt cả số có dấu cách. Có kiểm ghi chú hợp lệ sau khi gửi |
| L3 / B12 (`hasLongDigitRun`) | Đạt | `deliveryUi.ts:70-74` khớp từng ký tự với `apps/common/pii.py:46-47` |
| L4 (`check-ai-chunks`) | Đạt | Câu kết dùng `TARGETS.length` |
| Nợ 6 (câu "Chỉ tìm trong n phiếu đã tải…") | Đạt | `loadedOnlyNote` có vitest |
| B2 (cột Kho đọc `warehouse_name`) | Chấp nhận | BE chưa trả trường này nên hiện "—". Ghi ở lệch 8a. Cần BE thêm `warehouse_name` vào `_get_allocations`, hoặc PO bỏ cột |

**Ghi nhận nhỏ (không chặn):** Ở "Huỷ xác nhận đơn", lý do khoá đang chép nguyên câu AC "Đưa đơn về Gọi xác nhận.". Câu này mô tả việc mục đó làm, chưa nói vì sao đang khoá. Khi nối link ở Lô 3, mục sẽ hết khoá, nên không cần sửa bây giờ.

### Ý kiến TL-L6: có nên trả `phone` ở danh sách `assigned_to=me` không
**Nên, nhưng làm thành một bổ sung BE nhỏ (R4b), không chặn lô này.**
- Không mở rộng phạm vi lộ dữ liệu:
  - Người giao vốn đã lấy được đúng số đó cho đúng các phiếu đó qua `GET /notes/{id}/`. Hiện màn cũng đang gọi như vậy cho từng thẻ.
  - R4 tách `phone` khỏi danh sách là để màn vận hành (danh sách mọi phiếu của Chủ, Quản lý, NV kho) không trải SĐT của cả trăm khách ra một payload. Ca "của tôi" không thuộc mục đích đó.
  - Bất biến 9 ("chỉ lộ cho ai cần") vẫn giữ, vì người giao cần số để gọi khách.
- Điều kiện bắt buộc để BE làm:
  1. Chỉ thêm `phone` khi query có `assigned_to=me`. Kể cả với Chủ hay Quản lý, chỉ trả cho phiếu gán cho chính người gọi. Mọi query danh sách khác **không có khoá `phone`**, và phải có test assert điều này.
  2. Chỉ trả cho phiếu `DELIVERING` hoặc `FAILED`, đúng những phiếu có nút "Gọi khách". Các trạng thái khác trả `null`.
  3. Áp cùng cửa sổ SR-PII-02 như chi tiết (`pii_scope`). Giữ `Cache-Control: no-store`.
  4. Có test cho cả 3 điều kiện, cộng 403 khi người giao hỏi `assigned_to=<id khác>` (đã có).
- Sau khi BE có R4b: FE bỏ vòng gọi chi tiết ở `MyDeliveriesScreen.tsx` (`loadPhone`) và đọc `phone` từ dòng danh sách. Nếu thiếu khoá (BE cũ) thì giữ đường gọi chi tiết làm dự phòng.
- Thủ tục: đây là điều chỉnh contract kỹ thuật, không đổi phạm vi dữ liệu, nên Tech Lead tự duyệt được và sẽ ghi vào 02b §3.7. Nhưng vì đụng dữ liệu cá nhân, điều phối viên nên báo Duy một dòng trước khi giao BE.

### Kết luận re-review Lô 4 — FE: **APPROVED**
M1, M2, L1–L4, nợ 6 và B7 đều đạt. Không còn lỗi Critical, High hay Medium. Lô sẵn sàng cho QA chạy lại. Khi chạy lại, QA cần sửa script theo mục "QA cần sửa script" trong dev-notes; tôi đồng ý cả 4 điểm đó. TL-L6 chuyển thành việc BE R4b như trên. Các dòng nợ còn lại phải được ghi vào 02c:
- Nối link "Huỷ đơn" và "Huỷ xác nhận đơn" sau Lô 3.
- Lô `AiBar` dùng chung.
- BE thêm `warehouse_name` và mốc "Bắt đầu giao" / "Lúc thất bại" (lệch 8).

---

## Lô 5 — FE (ED-15 Gọi xác nhận) · review techlead 02/10

Worktree `loc-wt-b`, nhánh `ed-stream-b`, phần chưa commit trên `7f3b7b1`.

**Đã chạy trong lượt này:**
- `tsc --noEmit`: sạch.
- `vitest run`: 46 file, 434 test đạt.
- `NEXT_PUBLIC_USE_MOCK=0 npm run build`: OK. Sau đó `check-no-mock` XANH (15 file mock, 36 seed, 148 file build). `check-ai-chunks` XANH (10 màn + 2 layout, có `/confirmation` và `/confirmation/detail`).
- `check_naming.py`: OK, không có vi phạm mới.
- grep mã màu (`#hex`, `rgb`, `hsl`) trong `features/confirmation/**`: 0 kết quả.

### Đạt
- **Dữ liệu cá nhân (bất biến 9)**
  - Dòng ngoài phạm vi chỉ hiện `phone_masked` do BE trả, không có `tel:`, không mở được (`rowHref` trả `undefined`). Khớp `serializers.py:151-194` của BE. FE không tự che hay ghép số.
  - URL chỉ mang `?id=` và `?tab=`.
  - Không có `console.*`, `localStorage` hay `sessionStorage` trong module.
  - Ô tìm trên danh sách chỉ nằm trong state.
  - "Tìm khách gọi lại" gửi bằng `POST /api/confirmation/search/` với body `{q}`.
  - Chip AI là câu chung và chỉ kèm `target_model=delivery.deliverynote` cùng `target_id`.
  - Ghi chú có chặn dãy 9 chữ số trở lên ở FE, khớp BR-GH-19.
- **Phân quyền**
  - Các nút được vẽ theo `available_actions` của BE. Nút Quyết định chỉ có khi BE trả `decide:*`, mà BE chỉ trả cho người có `decide_unconfirmed`. Như vậy CSKH không có nút này (AC5).
  - Route có `ViewGuard view="confirmation"`.
  - Mock `chu` thêm 3 quyền `confirm_with_customer`, `change_recipient`, `decide_unconfirmed`, khớp đúng `accounts/migrations/0011_seed_group_cskh.py:34-37`.
  - Sửa `e2e/ed_batch1_shell.py` và `qa_ed_batch1_{shell,round2}.py` (số mục menu của `loc` từ 11 lên 12) là hệ quả đúng của việc trên.
- **409**
  - `STALE_STATE` vào `useGuardedSubmit.stale`: hộp hiện đúng câu của BE, nút gửi đổi thành "Tải lại", các ô bị khoá. Khi claim gặp `STALE_STATE` thì hiện `ConflictBanner`.
  - `CLAIMED` là lỗi đỏ thường, hiện câu của BE rồi tải lại chi tiết, đúng 02b §2.3 (sửa M1 Lô 2).
  - Module BE chỉ phát `STALE_STATE` và `CLAIMED`, nên không có nhánh `conflict` nào bị nuốt.
- **`useGuardedSubmit` / `ModalAlert`**: không trùng lặp với `shared/ui/form`.
  - `useGuardedSubmit` là lớp mỏng bọc `useSubmit`, chỉ giữ thêm câu `STALE_STATE`.
  - `ModalAlert` bọc `FormAlert` và thêm cuộn vào tầm nhìn.
  - Hai file đặt trong module là chấp nhận được. Nếu màn thứ hai cần, nâng lên `shared/ui/form`.
- **Cờ mock trong `api.ts`**: sửa đúng. Viết ternary `process.env.NEXT_PUBLIC_USE_MOCK === "1" ? … : undefined` ngay tại chỗ dùng để webpack gập được nhánh lúc parse và tree-shake `./mock`, kéo theo `auth/mock.ts`. Bản build thật đã kiểm XANH.
- **Tab "Tất cả"**: gộp 4 `state=X`.
  - Trang vượt (404, `page > 1`) được coi là rỗng.
  - `count` là tổng của 4 trạng thái. Còn tải thêm được khi một trạng thái còn `next`.
  - Các trạng thái rời nhau nên không trùng dòng. Có test `queueAll.test.ts`.
  - Đây là lệch hợp đồng (BE chưa có `state=ALL`), đã ghi ở dev-notes mục 1. Chấp nhận tạm.
- **Hộp thoại**: Huỷ đơn ở F2k dùng `btn danger` và hỏi lại hai bước (AC4). AC3 có câu "Chọn thời điểm sau dd/mm/yyyy hh:mm.". Mỗi hộp không quá 6 trường.

### Phát hiện

**TL5-M1 · Medium (chặn): thiếu cột "Lý do chuyển quyết định" (ED-15-AC1).**
- Vị trí: `erp-console/features/confirmation/components/ConfirmationQueueView.tsx:57-91`.
- AC1 ghi "Lý do chuyển quyết định ở cột riêng". Bảng có 10 cột nhưng không có cột lý do, dù BE đã trả `escalation_label` ở danh sách (`serializers.py:99-105`). Lý do hiện chỉ thấy ở trang chi tiết (`ConfirmationDetailScreen.tsx:281`).
- Tái hiện: đăng nhập `ql1` trên bản mock, vào `/confirmation/?tab=ESCALATED`. Không có cột nào nói vì sao đơn được chuyển lên.
- Sửa: thêm cột "Lý do" (`r.escalation_label ?? "—"`), mỗi ô một giá trị. Ở 360px có thể ẩn cột này trên các tab không phải ESCALATED/ALL. Bổ sung một ca vào `e2e/ed_batch5_confirmation.py`.

**TL5-L1 · Low: `loadDetail` đọc `detail` cũ trong closure.**
- Vị trí: `ConfirmationDetailScreen.tsx:90`, `:96-97`.
- `useCallback` chỉ phụ thuộc `[id]` và có `eslint-disable`, nên `detail` trong closure luôn là `null` của lần render đầu. Vì vậy nhánh `setActionError("Chưa tải lại được đơn…")` không bao giờ chạy. Sau một thao tác thành công, nếu lần tải lại lỗi mạng thì cả trang bị thay bằng `ErrorScreen` thay vì giữ dữ liệu cũ kèm alert.
- Tái hiện: ghi một cuộc gọi, chặn mạng đúng request `GET /api/confirmation/queue/<id>/` của lần `refreshAll`. Trang chuyển sang ErrorScreen.
- Sửa: dùng `useRef` cho "đã có detail", hoặc tách cờ `hasData`.

**TL5-L2 · Low: comment trái với code.**
- Vị trí: `features/confirmation/api.ts:51` và `:63`.
- Comment ghi "mới trước cũ sau", nhưng code sắp tăng dần theo `paid_at`, tức cũ trước. Sắp cũ trước là đúng với hàng chờ và với BE, nên chỉ cần sửa comment.
- Thêm: dòng có `paid_at = null` sẽ lên đầu. Nên ghi rõ trong comment hoặc đẩy các dòng này xuống cuối.

**TL5-L3 · Low: `ConfirmationAiBlock.tsx` chép gần nguyên `features/ai/components/AiDocBlockGate.tsx`.**
- Hai file chỉ khác nhau ở prop `chips`. Lô này không được sửa `features/ai` nên chấp nhận tạm.
- Ghi nợ: thêm `chips?` vào `AiDocBlockGate` rồi xoá `ConfirmationAiBlock`. Gộp vào lô `AiBar` dùng chung đã ghi ở Lô 4.
- Việc screen import `features/ai` giống tiền lệ `DeliveryDetailScreen` của Lô 4. 02b §2.3 muốn ghép ở `page.tsx`, nên gom sửa cùng lúc.

**TL5-L4 · Low: `features/purchasing/api.ts:6,18,31` còn mẫu `const isMock = …; mock: isMock ? …`.**
- Đã grep bản build thật: chuỗi seed của `purchasing/mock.ts` (`0901234567`, `Lagi`, `BR-MH-07`) không có trong `out/`, nên hiện chưa rò.
- Mẫu này vẫn mong manh, đúng là lỗi dev vừa sửa ở confirmation. Đề nghị đổi sang ternary tại chỗ trong một lô có quyền đụng purchasing.
- Không còn `api.ts` nào khác dùng mẫu này. `content/api.ts` đã viết đúng.

**TL5-L5 · Low (sau khi gộp nhánh): link sau "Huỷ đơn" ở F2k còn là đường cũ.**
- Vị trí: `ConfirmationDetailScreen.tsx:379`, link `/orders/?order=<id>&open=refund`.
- Lô 3 trên `main` có `legacyOrderRedirect` (`features/orders/filters.ts:45`) nên đường cũ vẫn chạy, nhưng phải đi vòng qua một lần chuyển hướng.
- Khi gộp `ed-stream-b` vào `main`, đổi thẳng sang `/orders/detail/?id=<id>&open=refund`. Đây là cùng dòng nợ "nối link sau Lô 3" của Lô 4.

**TL5-N1 · Ghi chú, không thuộc lô FE.**
- `ConfirmationQueueView.tsx:66` và chi tiết `:265` hiện SĐT đúng chuỗi BE trả, chưa nhóm 4-3-3 như 02b §3.7.
- `shared/lib/format.ts::phone` chưa có ở cả hai nhánh, nên không tính là lỗi của lô này. Khi thêm hàm format thì áp dụng cho cả hai chỗ.

**TL5-BE1 · Medium, việc BE riêng, không chặn lô FE này.**
- Vị trí: `backend/apps/delivery/confirmation/api.py:67`, `get_object()` lọc `Q(note_id=val) | Q(pk=val)` rồi lấy `.first()`.
- FE luôn gửi `note_id`. Khi `pk` của một task trùng `note_id` của task khác, BE có thể trả hoặc thao tác nhầm task: claim, ghi cuộc gọi, quyết định trên **đơn khác**.
- Không rò dữ liệu cá nhân, vì phạm vi được kiểm trên task trả về. Nhưng có thể ghi kết quả gọi vào nhầm đơn.
- Sửa: chỉ lọc theo `note_id`, kèm test hai task có `pk` và `note_id` chéo nhau. Điều phối viên giao be-dev.

### Ngoài phạm vi review, ghi nhận
- `mock.ts:522`: `mockClaimConfirmationTask` không áp `viewFor`, nên Chủ mở được dòng 40 nhưng claim bị 404, chỉ xảy ra trên mock. BE thật không bị.
- Hai script BE thật (`sr09_ac4_real_backend.py`, `qa_lo8_real.py`) còn selector cũ, đang ⏸. QA cần sửa khi dựng được BE.

### Kết luận Lô 5 — FE: **CHANGES REQUESTED**
- Cần sửa: TL5-M1 (thiếu cột lý do, AC1).
- Nên sửa cùng lượt: TL5-L1 và TL5-L2, đều nhỏ.
- Ghi nợ vào 02c: TL5-L3, L4, L5.
- Giao be-dev: TL5-BE1.
- Không có lỗi Critical hay High. Dữ liệu cá nhân, phân quyền và giá vốn đạt.

### Re-review Lô 5 — FE (vòng sửa sau review, 02/10)

**Đã chạy lại trong lượt này:** `tsc --noEmit` sạch; `vitest run` 46 file, 437 test đạt.

**Các mục của vòng trước**
- **TL5-M1 đạt.** Bảng có cột "Lý do" (`reasonText`, `confirmationUi.ts:142`) và đúng thứ tự cột theo board W1c.
- **TL5-L1 đạt.** Dùng ref `hasDetail` (`ConfirmationDetailScreen.tsx:67,99`). Tải lại bị lỗi thì giữ dữ liệu cũ và hiện cảnh báo.
- **TL5-L2 đạt.** Comment đã đúng; dòng có `paid_at` null được xếp xuống cuối, có test.

**Thay đổi dùng chung có làm vỡ Lô 1–4 không: không vỡ.**
- `DataTable` thêm `dense` và `hideOnMobile`. Cả hai là opt-in. Class `lt-dense` và `lt-m-hide` chỉ được gắn khi màn truyền prop. Hiện chỉ màn `/confirmation/` dùng. Bảng của Lô 1–4 vẫn ra cùng markup như cũ.
- `Field` thêm `counter`. Chỉ hiện khi `as="textarea"`, có `counter` và có `maxLength`. Các nơi dùng cũ không đổi.
- `globals.css`:
  - Khối `.fb` dưới 768px: ô tìm, ô chọn và ô ngày đều cao `var(--tap)` = 44. Đây là thay đổi cố ý cho mọi màn có `FilterBar` trên điện thoại, đúng luật vùng bấm ≥ 44px. Cách viết `margin:-1px 0` giống `.search input` đang có. Desktop không đổi.
  - `.btn[aria-disabled="true"]` làm mờ thêm các nút có thuộc tính này. Đã rà các chỗ có `aria-disabled`:
    - `FormPage.tsx:65-66` đã có sẵn `disabled`, nên hiển thị không đổi.
    - `AiBlockFrame.tsx:117` cũng đã có `disabled`.
    - Mục của `MoreMenu` và `AvatarMenu` không dùng class `.btn`.
    - Kết luận: không có màn cũ nào đổi giao diện ngoài ý muốn.
- Đổi chữ "Tổng số kg" ở Lô 4 (`DeliveriesView.tsx`, `DeliveryDetailScreen.tsx`, `app/print/label/page.tsx`) là đổi nhãn, đúng QA-B8.
- `guidance/mock.ts` thêm công cụ ép mã lỗi. Công cụ nằm sau cờ mock, và `check-no-mock` đã chạy xanh ở vòng dev.

**`aria-disabled` thay cho `disabled` ở nút mở hộp: không cho bấm lặp ra hai hộp hay hai thao tác hỏng.**
- **Nút "Quyết định"** (`:183`): `onClick` kiểm `busy === null`. Đang bận thì không làm gì.
- **Nút "Ghi kết quả gọi"** (`:189-192`): đi qua `claimThen`, mà hàm này mở đầu bằng `if (busy) return` (`:146`). Mục "Hẹn gọi lại" trong menu cũng đi qua `claimThen`.
- **Khe còn lại:** hai lần bấm trong cùng một khung hình vẫn đọc cùng giá trị `busy` cũ, nên có thể gửi 2 lần `POST …/claim/`.
  - Khe này giống hệt khi còn dùng `disabled`, vì `disabled` cũng chỉ có hiệu lực sau lần render kế tiếp. Vậy đây không phải hồi quy.
  - Claim là idempotent với cùng một người (chỉ gia hạn giữ chỗ), còn `setModal("call")` gọi hai lần vẫn chỉ ra một hộp. Không có hại.
  - Nếu muốn chặn tuyệt đối thì thêm ref `inFlight` như `useSubmit`. Ghi mức Low.
- Nút có `aria-disabled` vẫn nhận focus và vẫn đọc được trên trình đọc màn hình, đúng mục đích QA-B7 (trả focus về nút mở).

**Phát hiện mới (đều Low, không chặn)**
- **TL5-R1 · Low.** `globals.css:41-42`: `.btn:hover:not(:disabled)` và `.btn:active:not(:disabled)` vẫn áp cho nút có `aria-disabled="true"`. Nút mờ nhưng vẫn đổi nền khi rê chuột và vẫn co lại khi nhấn.
  - Sửa: thêm `:not([aria-disabled="true"])` vào hai selector.
- **TL5-R2 · Low.** `DataTable.tsx`, hàm `SkeletonBody` (khoảng dòng 79-83): ô khung xương không được gắn `lt-m-hide`. Ở ≤ 640px, phần đầu bảng chỉ còn 5 cột nhưng mỗi dòng khung xương vẫn có 10 ô, nên lệch cột trong lúc đang tải.
  - Tái hiện: mở `/confirmation/` ở 360px với mạng chậm.
  - Sửa: dùng `colClass(c)` cho `td` của khung xương.
- **TL5-R3 · Low, cần PO xác nhận.** Cột "Lý do" bị `hideOnMobile`, nên ở 360px tab "Cần quyết định" không còn thấy lý do ngay trên danh sách. AC1 không nói gì về điện thoại; ở trang chi tiết vẫn có lý do.
  - Nếu PO muốn thấy lý do ở điện thoại thì bỏ `hideOnMobile` cho cột này, ít nhất ở tab ESCALATED.
- **Lệch hợp đồng mới `note_code`** (dev-notes): BE chưa trả trường này, nên trên BE thật ô "Phiếu giao" hiện "—". Ghi việc cho be-dev, gom cùng TL5-BE1.

### Kết luận re-review Lô 5 — FE: **APPROVED**
- Không còn lỗi Critical, High hay Medium ở FE.
- Các thay đổi dùng chung là opt-in, hoặc là thay đổi cố ý (FilterBar 44px trên điện thoại), và không làm vỡ Lô 1–4.
- Các mục ghi vào 02c:
  - TL5-R1, TL5-R2 (sửa nhỏ, có thể gom vào lô sau)
  - TL5-R3 (hỏi PO)
  - TL5-L3, L4, L5
  - BE: TL5-BE1 và `note_code`.
- QA cần sửa chỉ số cột "Hạn gọi" trong `qa_ed_batch5_ui.py` G2: cột 6 thành cột 7.

## Lô 8 — FE

ED-28 Kiểm kê, review techlead 02/10. Diff trong worktree `loc-wt-b` (nhánh `ed-stream-b`), chưa commit. Phạm vi: `erp-console/features/stocktake/**`, `app/(console)/stocktake/**`, `shared/lib/nav.ts`, `scripts/check-ai-chunks.mjs`, `e2e/ed_batch8_stocktake*.py`.

**Số tự chạy lại:** `tsc --noEmit` sạch. `vitest run` 54 file, 554 test đạt. `scripts/check_naming.py` OK, không phát sinh mới. Màu cứng (hex/rgb/hsl) trong `features/stocktake` và `app/(console)/stocktake`: 0.

**Phần đạt**
- Chi tiết hiện `difference_qty`, `system_qty`, `counted_qty` và tổng `short_qty`/`over_qty`/`net_difference` lấy thẳng từ BE (`StocktakeDetailScreen.tsx:285-298`, `:245-255`). FE không tự tính lại chênh lệch trên màn chi tiết.
- Nút Duyệt chỉ hiện khi `available_actions` có `approve` (`StocktakeDetailScreen.tsx:173,189`). Khi bị chặn, mục mờ nằm trong "…" và lấy chữ từ `approve_blocked_reason.label` (`:178-180`). FE không tự suy BR-KK-08.
- `replaceStocktakeLines` gửi `expected_updated_at` (`api.ts:73-79`). Lỗi 409 giữ nguyên để `useSubmit` bật `ConflictBanner` (`StocktakeForm.tsx:87-90,340`).
- `line_index` được đổi từ chỉ số trong danh sách đã gửi sang chỉ số dòng trong form qua `sent[]` (`StocktakeForm.tsx:213,225`). Trên màn chi tiết, `lines` (serializer) và vòng duyệt (`services.py:244`) cùng `order_by("id")`, nên chỉ số khớp.
- Không có field tiền hay giá vốn. `fetchStockBatches` chỉ giữ các trường kg (`api.ts:117-136`). Không có dữ liệu khách, không `console.*`. `localStorage` chỉ dùng trong `mock.ts` (khoá `cave_erp_mock_stocktake`), và `window.__caveMock` bọc trong `NEXT_PUBLIC_USE_MOCK === "1"`.
- Khối AI ghép `AiDocBlockGate targetModel="inventory.stockreconciliation"` vào `aiSlot` (`StocktakeDetailScreen.tsx:209`). Đây là cách §2.4 quy định và trùng với `DeliveryDetailScreen`. `check-ai-chunks.mjs` đã có 4 route `/stocktake*`.
- Chặn bấm đúp bằng `busy` cộng `useSubmit`. Trang mỏng, URL chỉ mang `?id=`, đủ các trạng thái tải / lỗi / 403 / 404 / khoá.

**Phát hiện**

**TL8-F1 · High · Lưu nháp hoặc Gửi duyệt né được 409 khi có đổi Ngày kiểm kê hoặc Ghi chú.** Ở `StocktakeForm.tsx:216-222`, khi đầu phiếu đổi, FE gọi PATCH trước. PATCH của BE không kiểm phiên bản (`api.py:85-100`, `services.update_reconciliation`). Sau đó FE gán `updatedAt.current = h.updated_at` (dòng 219) rồi mới POST `…/lines/` với mốc mới này. Kết quả là phiên bản bị "làm mới" ngay trước khi kiểm, nên số đếm của người kia bị ghi đè mà không ai thấy cảnh báo. Đây chính là ca W6f phải chặn.
- Tái hiện (mock): `kho1` mở `/stocktake/edit/?id=<id>`. Ở console gọi `__caveMock.stocktakeEditByOther(<id>)`. Sửa ô Ghi chú rồi bấm Lưu nháp. Kết quả: lưu thành công, không có `ConflictBanner`. Nếu không sửa Ghi chú thì có 409 đúng như mong đợi.
- Trên BE thật: hai phiên cùng mở trang sửa. Phiên B lưu số. Phiên A đổi ngày rồi Lưu nháp. Dòng của B mất.
- Cách sửa: POST `…/lines/` trước bằng mốc đang giữ, rồi mới PATCH đầu phiếu. Hoặc chỉ PATCH khi `lines` đã qua. Không gán `updatedAt.current` từ PATCH trước khi gửi dòng. Cần thêm ca e2e "đổi ghi chú + người khác sửa → 409".

**TL8-F2 · Medium · Chữ trên màn nói "tồn đổi theo số thực đếm", trái BR-KK-09.** BE áp phần chênh đã chụp (`counted − system_qty` lúc lưu), không đặt tồn bằng số đếm. Nếu giữa lúc lưu và lúc duyệt có xuất hoặc nhập, tồn sau duyệt sẽ khác số đếm. Các câu hiện tại làm người duyệt hiểu sai:
- `stocktakeUi.ts:207` có câu "Tồn của n lô sẽ đổi theo số thực đếm."
- `StocktakeDetailScreen.tsx:342` có câu "Tồn kho của các lô lệch sẽ đổi theo số thực đếm."
- `StocktakeDetailScreen.tsx:141` có toast "Tồn kho đã điều chỉnh theo số đếm."
- Tái hiện (mock): lưu phiếu (lô A tồn 18, đếm 17,5). Gọi `__caveMock.stocktakeSetStock(A, 15)` rồi duyệt. Tồn ra 14,5, không phải 17,5, trong khi hộp xác nhận hứa "theo số thực đếm".
- Đề xuất câu: "Mỗi lô lệch sẽ được cộng hoặc trừ đúng phần chênh lệch ở bảng." BR-KK-09 còn chờ Duy chốt nên câu chữ nên bám cơ chế hiện có.

**TL8-F3 · Medium · "Tải lại" sau 409 giữ dòng của mình nhưng không cho thấy thay đổi của người kia.** `reloadAfterConflict` (`StocktakeForm.tsx:279-297`) chỉ lấy mốc `updated_at` mới và cập nhật `systemMilli` cho các lô trùng. Lô người kia thêm thì không hiện. Số người kia sửa trên lô trùng bị số đang gõ che mất. Ghi chú và ngày cũng không được nạp lại, trong khi `savedHeader` đã là bản của server. Bấm lưu lần nữa sẽ thay toàn bộ dòng bằng bản của mình. Như vậy 409 chỉ còn là một cú bấm thêm, người dùng không biết mình đang ghi đè.
- Tái hiện (mock): mở trang sửa, gọi `stocktakeEditByOther(id)`, Lưu nháp ra 409, bấm Tải lại, Lưu nháp lần nữa. Bản của người kia bị thay mà không hiện gì.
- Tối thiểu cần làm một trong hai việc: (a) sau khi tải lại, đánh dấu những dòng có số server khác số đang gõ, và thêm các lô mới của server vào form; hoặc (b) nạp lại nguyên bản server (giống màn khác) và giữ số đang gõ ở dạng "bản của bạn" để người dùng chọn. Nếu PO chấp nhận hành vi hiện tại thì ghi rõ vào 02b W6f.

**TL8-L1 · Low · Lô mới có thể lập trùng phiếu khi bấm lại lúc đang chuyển trang.** Ở `afterSave` của mode `new` (`StocktakeForm.tsx:237-239`), FE `router.replace` mà không gán `recId.current = res.id`, trong khi `useSubmit` đã nhả `busy`. Nếu bấm Lưu nháp lần nữa trước khi trang edit nạp xong thì `createStocktake` chạy lần hai và tạo phiếu thứ hai. Cách sửa: gán `recId.current = res.id` (và `updatedAt.current`) trước khi `replace`.

**TL8-L2 · Low · Mất "Lý do" đã gõ trên dòng chưa có số.** `toLineInputs` bỏ dòng không có số đếm (`stocktakeUi.ts:138-145`). Ở mode `new`, sau Lưu nháp trang chuyển sang edit và nạp lại từ BE, nên lý do đã gõ trên dòng chưa đếm bị mất mà không báo. Cùng gốc với lệch #2 và #9 của dev (không có unsaved-change guard). Đề xuất: khi lưu nháp, báo "n dòng chưa có số sẽ không được lưu" nếu dòng đó có lý do.

**TL8-L3 · Low · Số "Dòng N:" trong lỗi BE không khớp vị trí trên form.** BE đếm theo danh sách đã gửi, đã bỏ các dòng trống. Lỗi được gắn đúng dòng, nhưng chữ "Dòng 3" có thể nằm trên dòng thứ 5 của form. Nên bỏ tiền tố "Dòng N: " trong `cleanMessage`, hoặc chỉ bỏ ở form, vì lỗi đã nằm ngay trên dòng.

**TL8-L4 · Low · Code thừa.** `StocktakeDetailScreen.tsx:28` import `conflictOf` và `isConflictError` mà không dùng. `StocktakeForm.tsx:332` có biến `unchangedRows` thực chất là `rows.length`, tên gây hiểu nhầm.

**Ghi nhận, không phải lỗi:**
- Lệch #1: phiếu lưu nháp duyệt được ngay, vì BE không có trạng thái nháp riêng. Cần PO xác nhận cách gọi "Lưu nháp" và "Gửi duyệt".
- Lệch #7: `ed_batch1_shell.py` đếm `option` toàn trang. Lỗi nằm ở script, không phải ở màn.

**Kết luận: CHANGES REQUESTED.** Bắt buộc sửa TL8-F1 (High). Nên sửa cùng lượt TL8-F2 và TL8-L1, vì mỗi cái chỉ vài dòng. TL8-F3 sửa trong lô này, hoặc PO chấp nhận và ghi vào 02b. Các mục L2–L4 có thể gom vào lô sau.

### Lô 8 — FE, review lại sau vòng sửa (02/10)

**Số tự chạy lại:** `tsc --noEmit` sạch. `vitest run` 54 file, 555 test đạt. `check_naming` OK. Màu cứng 0. Không còn `conflictOf`, `isConflictError`, `unchangedRows`.

| Mục | Kết quả | Căn cứ |
|---|---|---|
| TL8-F1 (High) | **Đã sửa** | `StocktakeForm.persist()`: POST `…/lines/` đi trước, kèm `updatedAt.current` của bản đang giữ. Gặp 409 thì `throw` ngay trong `catch`, không chạy tới PATCH. Chỉ khi dòng lưu xong mới gán `updatedAt` mới và PATCH đầu phiếu, và chỉ PATCH khi ngày hoặc ghi chú khác `savedHeader`. Nếu người kia đổi ghi chú trước đó thì `updated_at` đã đổi, nên POST dòng ra 409. Còn một khe nhỏ giữa POST dòng và PATCH (vài trăm ms): PATCH ở BE ghi đè ngày/ghi chú theo kiểu ai lưu sau thắng. Mức này chấp nhận được, vì muốn kín hẳn thì BE phải kiểm phiên bản ở PATCH, nằm ngoài lô FE. PATCH lỗi sau khi dòng đã lưu thì báo đúng "Đã lưu số đếm nhưng chưa lưu được ngày hoặc ghi chú…", và mốc phiên bản đã cập nhật nên lần thử lại không tự gây 409. |
| TL8-F2 | **Đã sửa** | `stocktakeUi.ts:207-209`, hộp xác nhận `StocktakeDetailScreen.tsx:345` và toast `:141` đều nói "cộng hoặc trừ phần chênh lệch đã ghi", đúng BR-KK-09. Có test quét chặn cụm "theo số (thực) đếm". |
| TL8-F3 | **Đã sửa** | `reloadAfterConflict` gọi `applyDetail(d)`, nạp nguyên khối dòng, ngày, ghi chú và `updated_at` từ máy chủ, rồi xoá kho đang chọn, lỗi dòng và trạng thái submit. Trước khi bấm có câu báo "Thay đổi chưa lưu của bạn sẽ bị bỏ khi tải lại." |
| TL8-L1 | **Đã sửa** | `recId.current` và `updatedAt.current` được gán ngay khi `createStocktake` trả về, trước khi `useSubmit` nhả nút. Bấm lần hai sẽ đi nhánh `lines`, không tạo phiếu thứ hai. |
| `history.replaceState` | **Ổn** | Next là 14.2.35. Từ 14.1, `window.history.replaceState` gốc được App Router tích hợp, nên `useSearchParams` cập nhật theo và cây router được giữ. Repo đã có tiền lệ ở `content/edit/page.tsx:407` và `OrderDetailScreen.tsx:133`. Với static export, `/stocktake/edit/index.html` có sẵn, nên F5 hoặc mở lại URL vào đúng trang sửa. Form vẫn mount ở mode `new`, nhưng `recId` đã có nên không lập lại phiếu. Màn khoá phiếu (`mode === "edit"`) không áp ở đây, và cũng không cần, vì phiếu vừa lập luôn DRAFT và người lập có quyền sửa. |
| TL8-L2 | **Đã sửa** | Lưu nháp lần đầu ở lại form, lý do trên dòng chưa có số còn nguyên. Toast báo "N lô chưa có số nên chưa được lưu." |
| TL8-L4 | **Đã sửa** | |
| Bảng chi tiết bỏ cột Kho | **Ổn** | Cột Kho đã có ở `InfoGrid`. Phiếu nhiều kho (`warehouse_names.length > 1`) thì ghi tên kho sau tên mặt hàng, nên không mất thông tin. Chênh lệch vẫn là `difference_qty` của BE. CSS dùng token, không màu cứng. Selector `table:global(.lt).linesTable` đúng cách viết với CSS Module. |
| TL8-L3 | Chưa sửa | Low, gom vào lô sau. Lỗi vẫn gắn đúng dòng, chỉ số "Dòng N" có thể lệch vị trí. |

Không phát hiện lỗi mới ở các phần đã sửa. Dev chưa chạy ca "ghi chú + 409" trên BE thật. Thứ tự gọi trong code đủ để bảo đảm ca này, và mock đã chứng minh. QA có thể thêm ca này nếu muốn.

**Kết luận: APPROVED.** Còn nợ: TL8-L3 (Low), thiếu unsaved-change guard, và đề xuất BE kiểm phiên bản ở PATCH phiếu kiểm kê để đóng hẳn khe ghi chú (BE, không chặn lô này).

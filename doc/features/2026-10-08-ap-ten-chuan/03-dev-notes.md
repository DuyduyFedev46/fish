# 03 — Ghi chú dev: lô áp tên chuẩn

## BE — Pha A (nhánh `feat/ten-chuan-be`, tách từ main 9b1238c)

Chỉ đổi chữ hiển thị. Giá trị DB, `AuditLog.action`, codename, route và khoá JSON giữ nguyên. Ngoại lệ duy nhất là khoá phụ
`auto_cancel_blocked_label` (T43).

### Đã làm (B1–B8, B10–B31, trừ B9)
- Model: `orders.py` (T2), `payments.py` (T3–T13, C5), `refunds.py` (T20–T23, trường `payment_transaction`), `credit_notes.py` (C2, thêm
  cả dòng "Dòng phiếu trừ doanh thu" cho đồng bộ), `invoices.py` (P1), `delivery/models.py` (C4, C9, T24–T38, P9, P10),
  `inventory/models/{stock,returns,batches,supplier_returns}.py`, `purchasing/models/receipts.py`, `catalog/models/{items,pricing}.py`,
  `content/models/entries.py` (T54–T56, không đụng `SOURCE_CHOICES`), `accounts/models.py` (T48, T49), `reports/models.py` (P12).
- Dịch vụ và nhãn: `CANCEL_REASON_LABELS`, `SYSTEM_CANCEL_REASON_CODES` (T15, T16, T18, T19); `shop_labels.py` thêm `BOOKED` "Chờ thanh toán" (T1);
  `customer_notices.py` ("Đang chờ hoàn tiền", "Đã hoàn tiền"); timeline và next_steps của khoản tiền và phiếu hoàn tiền (C3, C5, P7);
  `delivery/next_steps.py` (P11); `inventory/returns/next_steps.py` (P4, P5); `catalog/items/next_steps.py` (sửa lỗi `item_image_upload`
  thành `item_image_add`, T76); `admin_edit` ở 4 file next_steps (T76); `registry.py`, `auth/services.py`, `data_scopes/catalog.py`,
  `guidance/reasons.py`; vài câu `BusinessError` có chữ cũ ("phiếu hoàn", "giao dịch thanh toán", "Soạn hàng"/"Hoàn tất" của phiếu giao).
- B12: `escalation_label` bỏ chữ riêng, dùng `get_escalation_reason_display()`; thêm khoá `auto_cancel_blocked_label`.
- B16: xoá `DECISION_LABELS`, dùng `get_decision_display()`.

### Endpoint thay đổi hợp đồng
`GET /api/confirmation/queue/<note_id>/` và dòng danh sách: thêm khoá phụ, khoá cũ giữ nguyên.
```json
{"auto_cancel_blocked": "BR-LO-05", "auto_cancel_blocked_label": "Lô đã chốt, không tự huỷ được"}
```
Khi không bị chặn: cả hai là `null`. `escalation_label` của WANT_CHANGE nay là "Khách muốn đổi món" (bỏ đuôi "– huỷ + hoàn + đặt lại";
FE đưa hướng dẫn xử lý vào dòng gợi ý, F10).

### Migration (chỉ metadata, `sqlmigrate` đều là no-op)
`sales/0017`, `delivery/0011`, `inventory/0010`, `catalog/0004`, `content/0003`, `accounts/0016`, `reports/0003`, `purchasing/0004`
(tự sinh) và `accounts/0017_rename_permission_labels` (viết tay, `RunPython`): đổi `auth_permission.name` cho 9 quyền
(P1, P2, P3, P4, P9, P10, P12 x2, P13), idempotent, có chiều ngược. Không đụng codename hay gán Group.
`makemigrations --check --dry-run`: không còn thay đổi.

### Điều lệch nhỏ so với 02b (đã chọn, ghi để techlead xem)
1. `accounts/audit/serializers.py`: `_cancel_note_ok` nhận cả nhãn lý do huỷ CŨ ("Hư hỏng khi soạn hàng", "Bỏ giao sau khi thất bại", "Khác")
   lẫn nhãn mới. Nếu không, AuditLog cũ ở production sẽ bị che thành "Có ghi chú" sau khi đổi chữ. Không sửa DB (bất biến 4).
   Ghi chú AuditLog MỚI sẽ có dạng "Lý do: Lý do khác · Có ghi chú…".
2. `Dòng chứng từ đảo` đổi thành "Dòng phiếu trừ doanh thu" (không có trong bảng, thêm cho khớp C2).
3. Nhãn T3–T7 bỏ "— chờ Chủ" ở `choices`; dòng thời gian khoản tiền không ghép tình trạng xử lý (02b mục 0).
4. `Refund.payment_transaction` (B3 ghi là field `payment`): tên field thật là `payment_transaction`.
5. Ghi chú `resolve_payment` "Hoàn tiền theo phiếu hoàn #N" **không đổi**: regex lọc dữ liệu cũ ở `accounts/audit/serializers.py` khớp chuỗi đã ghi.

### Test
- Mới: `backend/apps/common/tests/test_standard_names.py` (28 test): nhãn theo mã T/C/P, giá trị DB đóng băng, `verbose_name`,
  `Meta.permissions`, `Permission.name` sau migrate, data migration 0017 (dựng tên cũ, chạy hai lần, ngược), ma trận và "Tài khoản của tôi",
  nhãn T43, nhãn T73/T76 trên guidance mặt hàng, timeline khoản tiền/phiếu hoàn tiền, nhãn Shop.
- Sửa 26 test cũ đang khoá chữ cũ (chỉ đổi chuỗi mong đợi).
- Kết quả: `manage.py test` 3245 test, 0 failure (nền trước lô: 3217). `makemigrations --check` sạch. `scripts/check_naming.py` exit 0.
  Adapter không sửa nên không chạy pytest.
- Kiểm `git diff main -- backend | grep record_audit`: không có dòng `record_audit(...)` nào bị sửa.

### Còn nợ (Pha B, chờ W37 L3 BE gộp)
- B9 `backend/apps/sales/orders/timeline.py`: "Lập chứng từ đảo doanh thu" (P6), "Tạo phiếu hoàn" / "Thử chuyển lại phiếu hoàn" (P7),
  "Huỷ phiếu hàng về kho" (P5), "Duyệt hàng về kho: …" (P4), dòng tự huỷ đơn (T2), "Tạo phiếu giao … (Soạn hàng)" (T25),
  và "Phiếu hoàn … chuyển thất bại". Kèm test B-timeline (02b 3.1) và đổi các test timeline đang khoá chữ cũ.
- Test "chứa chuỗi cấm" của `build_timeline` đơn chỉ thêm được khi B9 xong.

## BE — Pha B (sau khi W37 L3 vào main 00da7e8)
- `git merge main` sạch, không xung đột.
- B9 `sales/orders/timeline.py`: "Lập phiếu trừ doanh thu" (P6), "Lập phiếu hoàn tiền" và "Thử hoàn tiền lại" (P7), "Đã hoàn tiền" (T22),
  "Huỷ phiếu hàng hoàn" (P5), "Duyệt hàng hoàn: …" (P4), "Hết giờ giữ chỗ, đã nhả hàng giữ" (T2), "(Đang soạn hàng)" (T25),
  "Phiếu hoàn tiền … chuyển thất bại" (C3). "Mang hàng về kho" giữ. Logic gộp mốc W37 L3 và lọc dòng AI không đổi.
- Low 1: `_cancel_audit_note` ghi "Huỷ đơn: <nhãn>" (không còn "Lý do: Lý do khác"); `_cancel_note_ok` nhận cả tiền tố "Huỷ đơn:" lẫn "Lý do:" cũ.
- Low 2: note `resolve_payment` mới ghi "phiếu hoàn tiền #N"; regex nhận cả "phiếu hoàn #N" cũ.
- Test: thêm `OrderTimelineWordingTests` và `CancelAndResolveNoteTests` vào `test_standard_names.py`; sửa 6 test timeline đang khoá chữ cũ.
- Kết quả: 3261 test OK (0 failure, 2 skipped), `makemigrations --check` sạch, `check_naming.py` exit 0.

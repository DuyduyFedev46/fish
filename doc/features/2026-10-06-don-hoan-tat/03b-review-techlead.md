# Đơn hoàn tất (W37) — Review của Tech Lead

## Review L1 BE (07/10)

**Phạm vi:** commit `3e59e50` trên nhánh `feat/w37-l1-be`, diff `2dcf666..HEAD`, 12 file. Đối chiếu với `02b-tech-design.md` §1.2–§1.4,
§2.1–§2.3, §4 và §6 (L1).

**Kết luận: APPROVED.** Không có lỗi Critical, High hay Medium. Có 5 điểm Low, sửa ở lô sau hoặc khi tiện, không chặn QA.

### Lệnh Tech Lead tự chạy trong worktree
- `manage.py test apps.delivery apps.sales.orders apps.reports` (DJANGO_DEBUG=1): chạy 679 test, 2 test skip (Postgres), 1 lỗi.
  Lỗi đó là `Missing staticfiles manifest entry for 'admin/css/base.css'`, do worktree không có thư mục `backend/staticfiles/`.
  Chạy cùng test trên checkout chính thì OK. Đây là môi trường, không phải code.
- `manage.py test` toàn bộ: chạy 3058 test, `errors=33`, `skipped=2`. Cả 33 lỗi đều là test trang admin, cùng một thông báo
  thiếu manifest staticfiles. Đếm bằng `grep -c "Missing staticfiles manifest"` ra 33, khớp đúng số lỗi. Không có FAIL nào.
- `makemigrations --check --dry-run`: No changes detected.
- `python3 scripts/check_naming.py`: exit 1. Nguyên nhân là 2 file FE đã có sẵn trên main (`ContactButton.tsx`,
  `SiteLegalFooter.tsx`, token `nguoi`). Các file L1 không có vi phạm.

QA nên chạy toàn bộ test trên checkout có `staticfiles`, hoặc chạy `collectstatic` vào thư mục tạm. Không commit thư mục đó.

### Soát theo 02b

| Mục | Kết quả | Chứng cứ |
|---|---|---|
| Thứ tự khoá đơn rồi phiếu, đọc lại sau khoá | Đạt | `delivery/services.py` `_lock_order_then_note` gọi `completion.lock_order_of_note`, rồi mới gọi `_lock_note`. `lock_order_of_note` lấy `sales_order_id` bằng `values_list` (không khoá), rồi `select_for_update().get(pk=…)`, không có join. Áp cho cả `advance_status` và `mark_failed`. `cancel_paid_order` vẫn khoá đơn rồi mới khoá phiếu. `LockOrderTests` kiểm cả ba đường bằng spy `QuerySet.select_for_update` |
| Toàn thân hàm trong `atomic` | Đạt | Việc xét luật, `save`, `record_audit` của phiếu và `complete_order_if_delivered` đều nằm trong một `transaction.atomic()`. `test_s1_ac9` patch AuditLog của đơn cho raise, rồi kiểm phiếu vẫn `DELIVERING`, `completed_at` rỗng, đơn `PROCESSING`, số AuditLog không đổi (dòng của phiếu cũng bị rollback) |
| BR-GH-24 trả 400 | Đạt | `_raise_if_cancelled` xét cả phiếu `CANCELLED` lẫn đơn `CANCELLED`/`AUTO_CANCELLED`, chạy trước BR-GH-07 với đích `DELIVERING`/`COMPLETED` và chạy trong `mark_failed`. Đích `READY` vẫn trả `BR-GH-07`, đúng §1.2 bước 4. API trả `detail`, `code`, `current_status` đúng contract §2.1 (`test_s2_ac2_api_…`) |
| Nhánh `already` | Đạt | Nằm sau bước xét huỷ. Nhánh này trả về sớm, không ghi gì và không đụng đơn. `test_s1_ac4` kiểm số AuditLog của phiếu và của đơn không tăng, và `order_status` vẫn trả `COMPLETED`. `order_status` có mặt ở mọi nhánh (`test_order_status_present_on_every_branch`) và được đọc mới từ DB |
| Huỷ đơn đã Hoàn tất | Đạt | `cancel_paid_order` có nhánh `COMPLETED` → `BR-GH-05`, đặt ngay sau khi khoá, dùng đúng câu thông báo §2.2. Ca tất định 4 kiểm không sinh chứng từ đảo và không có `CANCEL_RESTORE` |
| AuditLog Hệ thống không chứa dữ liệu cá nhân | Đạt | `changes` có tập khoá cố định `status`, `delivery_note`, `delivery_note_id`, `note=""`, `actor=None`, `actor_kind=system`. `test_s1_ac2` so nguyên dict và kiểm không có SĐT, tên hay địa chỉ giả. Dòng của phiếu vẫn ghi người bấm |
| `financial_snapshot` | Đạt | Gồm `period_pnl` của mọi tháng theo giờ VN (cả qua service lẫn API `?year&month`, API này nhận đúng tham số), `batch_pnl` mọi lô cộng API danh sách lô, doanh thu hôm nay, và số dòng + `max(id)` của 5 bảng chứng từ. `pending_orders` cố ý bỏ ngoài. `test_s1_ac3` dựng hai kỳ (hoá đơn lùi 40 ngày) và một chứng từ đảo |
| Test Postgres skip theo T1 (b) | Đạt | `@skipUnless(connection.vendor == "postgresql")`. Docstring cấm trỏ vào staging hoặc production. Mỗi thứ tự khoá chạy 20 lần, có barrier và timeout 5 giây. Test chưa từng chạy, xem điểm L3 |
| Marker `naming: allow` | **Duyệt** | Hai dòng gán bí danh `self.courier, self.manager(, self.owner) = self.giao, self.ql(, self.chu)` để code mới dùng tên tiếng Anh, còn thuộc tính cũ là của `OrderApiBase` dùng chung. Marker có lý do. Đã có tiền lệ y hệt ở `test_timeline_no_free_text.py:30-31` và `test_auditlog_note_no_free_text.py:56`. Đổi tên `OrderApiBase` nằm ngoài phạm vi |
| Sửa test cũ S14-AC5 | **Duyệt** | `test_s14_ac5_da_hoan_tat_bi_chan` trước đây khẳng định đơn giữ `PROCESSING` sau khi giao xong. Đó chính là lỗi W37. Nay test khẳng định `COMPLETED` đúng theo S1, vẫn giữ các assert `BR-GH-05` và "không có `cancel` trong `available_actions`". Ý định của test (huỷ bị chặn sau khi giao xong) không bị nới |
| Không rò giá vốn | Đạt | Không đụng serializer, `AllocationSerializer` hay `CostFieldSerializerMixin`. Phản hồi chỉ thêm `order_status` (mã trạng thái). Dòng AuditLog không có số tiền hay giá |
| Phân quyền | Đạt | Không thêm route hay quyền. Có test cho S1-AC11 (404), AC12 (PATCH/PUT bị chặn), AC13 (403), S2-AC6 (403) và 401 |
| Lệch so với 02b | Chấp nhận | S1-AC13 dùng người chỉ có `view_deliverynote`, vì NV kho thật có `change_deliverynote` (đóng gói). Các mục còn lại khớp 02b |

### Điểm Low (không chặn)
- **L1** `sales/orders/completion.py`, `lock_order_of_note`: kiểu trả về khai `-> SalesOrder`, nhưng hàm có thể trả `None`. Sửa
  thành `SalesOrder | None`.
- **L2** `completion.py`, `complete_order_if_delivered`: hàm truy vấn lại `invoice_id` từ `order.pk`. Có thể dùng thẳng
  `trigger_note.sales_invoice_id` và bớt một query. Nếu sửa thì lệnh S3 (L4) phải truyền đúng phiếu của đơn đó.
- **L3** `delivery/tests/test_completion_race_postgres.py`: test chưa từng chạy, nên chưa biết chính test có đúng không. Đáng ngờ
  nhất là chỗ gọi `OrderApiBase.setUp(self)` trên một `TransactionTestCase` cùng `serialized_rollback`. Ghi nợ theo T1. Lần
  đầu có Postgres thì phải chạy file này trước khi tin kết quả.
- **L4** `test_order_completion.py`, `test_order_status_present_on_every_branch`: biến `order`, `order2`, `note2` không dùng.
  Cách lấy kết quả qua `self._pack_response` lòng vòng, nên trả thẳng response từ helper.
- **L5** `test_order_completion.py`, `test_s1_ac3_…`: `import datetime` và `timezone` nằm trong thân hàm. Nên đưa lên đầu file.

### Việc cho lô sau
- **PV Lô 4** (`delivery/scope.py`) phải giữ hai điều. Một, NV giao vẫn thấy phiếu `CANCELLED` được gán cho mình, nếu không
  `test_s2_ac2_api_returns_400_br_gh_24_for_cancelled_order` sẽ trả 404. Hai, giữ khoá `order_status`.
- **Hồ sơ huỷ đơn đang giao** dùng lại `ORDER_CANCELLED_MESSAGE`, `ORDER_CANCELLED_CODE` và `completion.lock_order_of_note`.

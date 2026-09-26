# sales/refunds — Hoàn tiền (P-07)

Phiếu hoàn là chứng từ riêng (BR-HT-01); số hoàn ≤ đã thu − đã hoàn (BR-HT-04); xác nhận bắt buộc mã chuyển khoản (BR-HT-03).
Tách quyền: `create_refund` (Chủ + Quản lý) ≠ `confirm_refund` (chỉ Chủ — tiền rời túi, BR-HT-07). Mọi bước ghi AuditLog (BR-HT-08).
Endpoint: `/api/sales/refunds/` (chỉ đọc), `POST /api/sales/refunds/create/`, `POST /api/sales/refunds/{id}/confirm/`.

**S13 (Lô L8, Q9):** phiếu hoàn gắn ĐÚNG MỘT trong `sales_invoice` / `payment_transaction` (CheckConstraint
`refund_exactly_one_source`). `create_refund_for_payment`: chỉ giao dịch còn OPEN trong hàng chờ, số hoàn ≤ tiền giao dịch −
phiếu chưa thất bại (`payment_refundable_amount`, BR-HT-04); API đòi thêm `confirm_payment_manual` (chỉ Chủ). Xác nhận phiếu
→ giao dịch RESOLVED/REFUNDED. Báo cáo kỳ chỉ trừ phiếu gắn hoá đơn (khoản không hoá đơn chưa từng ghi doanh thu).
`request_id` (UUID, Q12): gửi lại cùng mã → 200 `duplicate: true`, vẫn 1 phiếu (áp cho cả hai nhánh).

**S15 (Lô L9):** nhánh hoá đơn dùng chung `request_id`/chống tạo trùng với S13 (đã có từ L8). Chỉ sửa lại thông điệp vượt
số còn hoàn cho khớp câu chữ story: `"Vượt số đã thu: còn được hoàn tối đa <X>đ."` (nợ để lại từ L8).

**S16 (Lô L9, BR-HT-09 mới):** hàng chờ Chủ chuyển khoản. `GET /api/sales/refunds/?status=PENDING,FAILED` (lọc nhiều giá
trị) trả thêm `order_code`, `customer_name`, `customer_phone`, `source_bank_txn_id`, `failure_reason`, `available_actions`
(`confirm`/`mark_failed` khi Chờ hoàn, `retry` khi Thất bại — chỉ hiện với người có `confirm_refund`). `POST …/mark-failed/`
{"reason"} → FAILED (lưu `failure_reason`); `POST …/retry/` {} → PENDING, kiểm lại số còn hoàn tại thời điểm thử lại (một
phiếu khác có thể đã lấp đầy phần trống trong lúc chờ) → 400 `BR-HT-04` nếu vượt. Phiếu REFUNDED là điểm không quay lui:
`confirm`/`mark-failed`/`retry` trên phiếu đó đều 400 `BR-HT-09`. Quyền `confirm_refund` (chỉ Chủ, BR-HT-07) cho cả ba
action — ranh giới "tiền rời túi". `timeline.py` (orders) thêm kind `refund_failed`/`refund_retry`.

# sales/refunds — Hoàn tiền (P-07)

Phiếu hoàn là chứng từ riêng (BR-HT-01); số hoàn ≤ đã thu − đã hoàn (BR-HT-04); xác nhận bắt buộc mã chuyển khoản (BR-HT-03).
Tách quyền: `create_refund` (Chủ + Quản lý) ≠ `confirm_refund` (chỉ Chủ — tiền rời túi, BR-HT-07). Mọi bước ghi AuditLog (BR-HT-08).
Endpoint: `/api/sales/refunds/` (chỉ đọc), `POST /api/sales/refunds/create/`, `POST /api/sales/refunds/{id}/confirm/`.

**S13 (Lô L8, Q9):** phiếu hoàn gắn ĐÚNG MỘT trong `sales_invoice` / `payment_transaction` (CheckConstraint
`refund_exactly_one_source`). `create_refund_for_payment`: chỉ giao dịch còn OPEN trong hàng chờ, số hoàn ≤ tiền giao dịch −
phiếu chưa thất bại (`payment_refundable_amount`, BR-HT-04); API đòi thêm `confirm_payment_manual` (chỉ Chủ). Xác nhận phiếu
→ giao dịch RESOLVED/REFUNDED. Báo cáo kỳ chỉ trừ phiếu gắn hoá đơn (khoản không hoá đơn chưa từng ghi doanh thu).
`request_id` (UUID, Q12): gửi lại cùng mã → 200 `duplicate: true`, vẫn 1 phiếu (áp cho cả hai nhánh).

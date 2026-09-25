# sales/refunds — Hoàn tiền (P-07)

Phiếu hoàn là chứng từ riêng (BR-HT-01); số hoàn ≤ đã thu − đã hoàn (BR-HT-04); xác nhận bắt buộc mã chuyển khoản (BR-HT-03).
Tách quyền: `create_refund` (Chủ + Quản lý) ≠ `confirm_refund` (chỉ Chủ — tiền rời túi, BR-HT-07). Mọi bước ghi AuditLog (BR-HT-08).
Endpoint: `/api/sales/refunds/` (chỉ đọc), `POST /api/sales/refunds/create/`, `POST /api/sales/refunds/{id}/confirm/`.

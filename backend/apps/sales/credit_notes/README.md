# credit_notes — chứng từ đảo doanh thu (P8 Lô 4, BR-HT-06 / BR-HT-10)

Huỷ đơn đã thanh toán thì hoá đơn gốc vẫn `ISSUED` (giữ lịch sử), nên doanh thu phải đảo bằng một chứng từ riêng.

- Model: `models/credit_notes.py` — `SalesCreditNote` (đầu chứng từ: mã `DC-<mã hoá đơn>`, số tiền, kỳ lập `issued_at`,
  `stock_restored`, `backfilled`) và `SalesCreditNoteLine` (lô, kg, giá bán, giá vốn đóng băng `unit_cost` — chỉ Chủ được thấy).
  Chỉ có quyền `view_*` (append-only). Admin chỉ đọc kể cả superuser.
- `services.py::issue_cancel_credit_note` — idempotent theo `source_key = "cancel:<order.pk>"`. Được gọi trong cùng transaction với
  `orders.services.cancel_paid_order` (cả nhánh Chủ/Quản lý huỷ tay lẫn job tự huỷ CSKH): lỗi ở đây thì cả lần huỷ rollback.
- Báo cáo: `reports.services.batch_pnl` / `period_pnl` và `revenue_today` của dashboard trừ chứng từ; phiếu hoàn của hoá đơn đã có
  chứng từ không trừ lần hai.
- `management/commands/backfill_credit_notes.py` — lập bù cho đơn huỷ trước P8 (mặc định chỉ in, `--apply` mới ghi; chứng từ có `issued_at` = lúc chạy lệnh nên kỳ cũ và lô đã chốt không đổi số — Duy quyết 30/09; output không PII,
  không giá vốn).
- Không sửa/xoá chứng từ ở bất kỳ đâu (test quét mã nguồn: `tests/test_p8_credit_note.py`).

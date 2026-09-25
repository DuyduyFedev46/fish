"""
Bán hàng (P-05, P-07).

Luồng: Customer (guest, gộp theo SĐT) -> SalesOrder (booked, TTL 30') -> webhook
xác nhận -> SalesInvoice (trừ kho + ghi doanh thu) -> (Delivery ở app delivery).

Nguyên tắc nền:
- BR-PQ-11: KHÔNG ai tạo tay SalesOrder/SalesInvoice — chỉ Hệ thống tạo. Thể hiện
  bằng default_permissions bỏ 'add'/'delete' ⇒ quyền đó không tồn tại để gán.
- BR-BH-06: một dòng đơn ăn nhiều lô -> SalesInvoiceLineBatch là NGUỒN của mọi
  báo cáo giá vốn. Không có bảng này thì không tồn tại báo cáo giá vốn theo lô.
- BR-BH-08 / BR-DM-07: giá & công thức BUNDLE đóng băng (ảnh chụp) lúc tạo đơn.
- unit_cost trên *LineBatch là field NHẠY CẢM (view_costprice).

Package models/ chia theo tính năng; file này re-export để `from apps.sales.models import X`
và Django (app_label=sales) vẫn thấy đủ model — không sinh migration mới.
"""
from .customers import Customer  # noqa: F401
from .orders import SalesOrder, SalesOrderLine, SalesOrderLineBatch  # noqa: F401
from .invoices import SalesInvoice, SalesInvoiceLine, SalesInvoiceLineBatch  # noqa: F401
from .payments import PaymentTransaction  # noqa: F401
from .refunds import Refund  # noqa: F401

__all__ = [
    "Customer",
    "SalesOrder",
    "SalesOrderLine",
    "SalesOrderLineBatch",
    "SalesInvoice",
    "SalesInvoiceLine",
    "SalesInvoiceLineBatch",
    "PaymentTransaction",
    "Refund",
]

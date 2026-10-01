"""
Phân tích cột `StockLedgerEntry.reference` (chuỗi tự do do dịch vụ kho ghi) thành mã chứng từ + liên kết cho Sổ nhập xuất.

Các dạng đang được ghi (xem nơi gọi `record_movement`):
- `reconciliation 12`                        → KK-12  (kiểm kê)
- `return 7 (hàng hoàn)` / `return 7 (huỷ bỏ, lỗ …)` → RT-7 (hàng hoàn)
- `INV-…`                                    → mã hoá đơn bán (tra id hoá đơn)
- `cancel SO-…`                              → mã đơn bị huỷ (tra id đơn)
- `create_batch <mã lô>`                     → phiếu nhập PR-n sinh ra lô, không có phiếu thì trỏ về lô
- `supplier_return SR-5`                     → SR-5 (phiếu trả nhà cung cấp)
- `cancel_expired_batch <mã lô>`             → lô bị huỷ phần tồn quá hạn
- `cancel_purchase_receipt PR-3`             → PR-3 (huỷ phiếu nhập)
Dạng lạ (dữ liệu demo cũ như `Nhập lô …`) → hiện nguyên chuỗi, không có liên kết.

Hàm thuần: `parse_reference` không đụng DB. Việc tra id (hoá đơn, đơn) làm một lượt cho cả trang ở `build_lookup`,
nên Sổ không bị N+1.
"""
import re
from dataclasses import dataclass, field

# Id trong chuỗi tham chiếu: tối đa 18 chữ số để chắc chắn nằm trong int64 (bỏ qua dòng lạ thay vì lỗi 500).
_NUM = r"([0-9]{1,18})"
_RECONCILIATION = re.compile(rf"^reconciliation {_NUM}$")
_RETURN = re.compile(rf"^return {_NUM}(?: .*)?$")
_SUPPLIER_RETURN = re.compile(rf"^supplier_return SR-{_NUM}$")
_CANCEL_RECEIPT = re.compile(rf"^cancel_purchase_receipt PR-{_NUM}$")
_CANCEL_EXPIRED = re.compile(r"^cancel_expired_batch (\S+)$")
_CREATE_BATCH = re.compile(r"^create_batch (\S+)$")
_CANCEL_ORDER = re.compile(r"^cancel (SO\S*)$")
_INVOICE = re.compile(r"^(INV\S*)$")


@dataclass(frozen=True)
class ParsedReference:
    """`kind`: loại chứng từ (`stocktake`, `return`, `supplier_return`, `receipt`, `invoice`, `order`, `batch`) hoặc `""`.
    Đúng một trong `number` (id trong chuỗi) hoặc `code` (mã chữ cần tra id) có giá trị, hoặc cả hai rỗng."""

    kind: str = ""
    number: int | None = None
    code: str = ""


def parse_reference(reference: str) -> ParsedReference:
    text = (reference or "").strip()
    for pattern, kind in (
        (_RECONCILIATION, "stocktake"), (_RETURN, "return"),
        (_SUPPLIER_RETURN, "supplier_return"), (_CANCEL_RECEIPT, "receipt"),
    ):
        match = pattern.match(text)
        if match:
            return ParsedReference(kind=kind, number=int(match.group(1)))
    for pattern, kind in (
        (_CANCEL_EXPIRED, "cancel_expired_batch"), (_CREATE_BATCH, "create_batch"),
        (_CANCEL_ORDER, "order"), (_INVOICE, "invoice"),
    ):
        match = pattern.match(text)
        if match:
            return ParsedReference(kind=kind, code=match.group(1))
    return ParsedReference()


@dataclass
class ReferenceLookup:
    """Id tra sẵn cho một trang sổ: mã hoá đơn → id, mã đơn → id."""

    invoice_ids: dict = field(default_factory=dict)
    order_ids: dict = field(default_factory=dict)


def build_lookup(entries) -> ReferenceLookup:
    """Tra id hoá đơn và đơn cho các dòng của trang bằng đúng 2 truy vấn (bỏ qua truy vấn khi không cần)."""
    from apps.sales.models import SalesInvoice, SalesOrder

    invoice_codes, order_codes = set(), set()
    for entry in entries:
        parsed = parse_reference(entry.reference)
        if parsed.kind == "invoice":
            invoice_codes.add(parsed.code)
        elif parsed.kind == "order":
            order_codes.add(parsed.code)
    lookup = ReferenceLookup()
    if invoice_codes:
        lookup.invoice_ids = dict(SalesInvoice.objects.filter(code__in=invoice_codes).values_list("code", "pk"))
    if order_codes:
        lookup.order_ids = dict(SalesOrder.objects.filter(code__in=order_codes).values_list("code", "pk"))
    return lookup


def describe(entry, lookup: ReferenceLookup):
    """Trả `(reference_display, reference_link)` của một dòng sổ. `entry.batch` phải đã nạp (select_related)."""
    parsed = parse_reference(entry.reference)
    raw = entry.reference or ""
    batch = entry.batch
    kind = parsed.kind

    if kind == "stocktake":
        return f"KK-{parsed.number}", {"kind": "stocktake", "id": parsed.number}
    if kind == "return":
        return f"RT-{parsed.number}", {"kind": "return", "id": parsed.number}
    if kind == "supplier_return":
        return f"SR-{parsed.number}", {"kind": "supplier_return", "id": parsed.number}
    if kind == "receipt":
        return f"PR-{parsed.number}", {"kind": "receipt", "id": parsed.number}
    if kind == "invoice":
        invoice_id = lookup.invoice_ids.get(parsed.code)
        return parsed.code, ({"kind": "invoice", "id": invoice_id} if invoice_id else None)
    if kind == "order":
        order_id = lookup.order_ids.get(parsed.code)
        return parsed.code, ({"kind": "order", "id": order_id} if order_id else None)
    if kind == "cancel_expired_batch":
        return batch.batch_id, {"kind": "batch", "id": batch.pk}
    if kind == "create_batch":
        source_line = getattr(batch, "source_line", None)  # lô tạo tay (không qua phiếu nhập) thì không có
        if source_line is not None:
            return f"PR-{source_line.receipt_id}", {"kind": "receipt", "id": source_line.receipt_id}
        return batch.batch_id, {"kind": "batch", "id": batch.pk}
    return raw, None

"""
Thêm kho (R7, ED-25-AC3). Kho là dữ liệu danh mục: chỉ thêm, không sửa/xoá qua API (kho đã có lô thì xoá bị
chặn `PROTECT`). Mỗi lần thêm ghi `AuditLog` (BR-PQ-04), chỉ ghi id và loại, không ghi chữ tự do.
"""
from django.db import IntegrityError, transaction

from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError
from apps.inventory.models import Warehouse

NAME_MAX_LENGTH = Warehouse._meta.get_field("name").max_length
NAME_REQUIRED = "WAREHOUSE_NAME_REQUIRED"
NAME_TOO_LONG = "WAREHOUSE_NAME_TOO_LONG"
NAME_TAKEN = "WAREHOUSE_NAME_TAKEN"


@transaction.atomic
def create_warehouse(*, name, is_group=False, actor):
    """
    Tạo kho. Tên đã bỏ khoảng trắng hai đầu; không được trống, tối đa `NAME_MAX_LENGTH` ký tự, không trùng
    tên kho khác (không phân biệt hoa thường). Thông điệp lỗi không lặp lại tên người gọi gửi lên.
    """
    name = " ".join((name or "").split())  # gộp khoảng trắng liền nhau: "Kho  lạnh" và "Kho lạnh" là một tên
    if not name:
        raise BusinessError("Nhập tên kho.", code=NAME_REQUIRED)
    if len(name) > NAME_MAX_LENGTH:
        raise BusinessError(f"Tên kho tối đa {NAME_MAX_LENGTH} ký tự.", code=NAME_TOO_LONG)
    # So sánh bằng Python (casefold) vì `iexact` của SQLite không phân biệt hoa thường với chữ có dấu.
    # Số kho rất ít nên đọc hết tên là rẻ.
    taken = {" ".join(existing.split()).casefold() for existing in Warehouse.objects.values_list("name", flat=True)}
    if name.casefold() in taken:
        raise BusinessError("Tên kho đã có, chọn tên khác.", code=NAME_TAKEN)
    try:
        with transaction.atomic():
            warehouse = Warehouse.objects.create(name=name, is_group=bool(is_group))
    except IntegrityError:  # hai người thêm cùng tên một lúc: ràng buộc unique của DB chặn người đến sau
        raise BusinessError("Tên kho đã có, chọn tên khác.", code=NAME_TAKEN) from None
    record_audit("create_warehouse", actor=actor, obj=warehouse, changes={"is_group": warehouse.is_group})
    return warehouse

"""
Thêm, sửa nhà cung cấp (B3, F1b) kèm AuditLog.

AuditLog chỉ ghi TÊN trường đã đổi, không chép giá trị: SĐT và ghi chú là dữ liệu đối tác, không đưa vào log
(bất biến 9 áp dụng tinh thần cho cả đối tác). "Ngừng hợp tác" là sửa `is_active=False`, không xoá (BR-PQ-10).
"""
import threading
from contextlib import contextmanager

from django.db import connection, transaction

from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError
from apps.purchasing.models import Supplier

from .supplier_queries import name_taken

NAME_TAKEN = "SUPPLIER_NAME_TAKEN"
NAME_LOCK_KEY = 7_110_001  # khoá tư vấn Postgres riêng cho "tên nhà cung cấp"; số tuỳ ý, chỉ cần không trùng khoá khác
_sqlite_name_lock = threading.RLock()


@contextmanager
def serialized_names():
    """
    Tuần tự hoá mọi lệnh tạo/đổi tên nhà cung cấp, để bước kiểm trùng và lệnh ghi không bị xen vào (B11-1).
    Không có ràng buộc unique ở DB (chưa thêm migration), nên khoá là thứ duy nhất chặn hai yêu cầu cùng lúc.
    - Postgres: `pg_advisory_xact_lock` giữ đến hết giao dịch. Dùng khoá tư vấn thay vì `select_for_update` vì bảng
      rỗng thì không có dòng nào để khoá.
    - SQLite (máy dev, test): khoá trong tiến trình, vì giao dịch SQLite mặc định đọc trước rồi mới xin quyền ghi.
    Bảng nhỏ và tạo/đổi tên hiếm nên khoá toàn cục chấp nhận được.
    """
    if connection.vendor == "postgresql":
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [NAME_LOCK_KEY])
            yield
    else:
        with _sqlite_name_lock, transaction.atomic():
            yield


def ensure_name_free(name, *, exclude_pk=None):
    if name_taken(name, exclude_pk=exclude_pk):
        raise BusinessError("Đã có nhà cung cấp trùng tên này.", code=NAME_TAKEN)


def create_supplier(*, data, actor):
    with serialized_names():
        ensure_name_free(data["name"])  # kiểm lại trong khoá: serializer đã kiểm nhưng chưa có khoá
        supplier = Supplier.objects.create(**data)
        record_audit("supplier_create", actor=actor, obj=supplier, changes={"fields": sorted(data)})
    return supplier


def update_supplier(*, supplier, data, actor):
    """Ghi các trường có đổi thật. Không đổi gì thì không ghi AuditLog."""
    with serialized_names():
        supplier = Supplier.objects.get(pk=supplier.pk)  # đọc lại trong khoá, tránh ghi đè bằng bản cũ
        if "name" in data:
            ensure_name_free(data["name"], exclude_pk=supplier.pk)
        changed = sorted(name for name, value in data.items() if getattr(supplier, name) != value)
        for name in changed:
            setattr(supplier, name, data[name])
        if changed:
            supplier.save(update_fields=changed)
            record_audit("supplier_update", actor=actor, obj=supplier, changes={"fields": changed})
    return supplier

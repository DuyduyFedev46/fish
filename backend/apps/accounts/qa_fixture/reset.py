"""
`seed_qa --reset`: xoá ĐÚNG bản ghi QA (nhận diện bằng mã/tiền tố của build.py), không đụng dữ liệu khác.

Ngoại lệ có chủ đích của BR-PQ-10 (chứng từ không xoá) và BR-PQ-06 (AuditLog append-only), CHỈ cho dữ liệu QA
trên DB dev/staging đã qua cổng guard.py. Cách làm: xoá theo thứ tự con trước cha; bản ghi nào còn bị bản ghi
KHÁC (không phải QA) tham chiếu thì PROTECT chặn → được giữ lại và báo ra, không xoá lan.
"""
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError, RestrictedError

from apps.accounts.models import AuditLog, StaffProfile
from apps.delivery.models import CallScript, ConfirmationTask, CustomerCall, DeliveryNote, LabelPrint
from apps.inventory.models import (
    Batch,
    ReturnToStock,
    StockEntry,
    StockLedgerEntry,
    StockReconciliation,
)
from apps.catalog.models import Item, ItemPrice
from apps.purchasing.models import PurchaseReceipt, Supplier
from apps.sales.models import Customer, PaymentTransaction, Refund, SalesInvoice, SalesOrder
from apps.sales.models.credit_notes import SalesCreditNote

from .build import CALL_SCRIPT_PREFIX, CUSTOMER_NAME_PREFIX, PREFIX, USER_PREFIX, fake_phone


FAKE_PHONES = [fake_phone(n) for n in range(1, 21)]
AUDIT_NOTE_PREFIX = "QA-audit-"


def _qa_users():
    return get_user_model().objects.filter(username__startswith=USER_PREFIX)


def _qa_refunds():
    """Phiếu hoàn tiền của QA: gắn hoá đơn mã QA- hoặc khoản tiền về mã QA-. Không xét người lập."""
    return Refund.objects.filter(
        Q(sales_invoice__code__startswith=PREFIX) | Q(payment_transaction__bank_txn_id__startswith=PREFIX))


def _qa_customers():
    return Customer.objects.filter(phone__in=FAKE_PHONES, name__startswith=CUSTOMER_NAME_PREFIX)


def _object_querysets():
    """(nhãn, queryset) của các đối tượng QA có thể có dòng Nhật ký — để nhận dòng Nhật ký gắn với chúng."""
    return [
        (SalesOrder, SalesOrder.objects.filter(code__startswith=PREFIX)),
        (SalesInvoice, SalesInvoice.objects.filter(code__startswith=PREFIX)),
        (SalesCreditNote, SalesCreditNote.objects.filter(sales_invoice__code__startswith=PREFIX)),
        (DeliveryNote, DeliveryNote.objects.filter(code__startswith=PREFIX)),
        (PaymentTransaction, PaymentTransaction.objects.filter(bank_txn_id__startswith=PREFIX)),
        (Refund, _qa_refunds()),
        (Batch, Batch.objects.filter(batch_id__startswith=PREFIX)),
        (Item, Item.objects.filter(code__startswith=PREFIX)),
        (Supplier, Supplier.objects.filter(name__startswith=PREFIX)),
        (ReturnToStock, ReturnToStock.all_objects.filter(note__startswith=PREFIX)),
        (PurchaseReceipt, PurchaseReceipt.objects.filter(note__startswith=PREFIX)),
        (StockReconciliation, StockReconciliation.objects.filter(note__startswith=PREFIX)),
        (CallScript, CallScript.objects.filter(content__startswith=CALL_SCRIPT_PREFIX)),
        (Customer, _qa_customers()),
        (get_user_model(), _qa_users()),
    ]


def _audit_filter():
    """
    Dòng Nhật ký của QA: gắn với đối tượng QA (model + id), hoặc note `QA-audit-`.
    KHÔNG xoá theo người làm: tài khoản qa_ có thể đã thao tác trên dữ liệu không phải QA (BR-PQ-06).
    Phải tính TRƯỚC khi xoá đối tượng (sau đó không còn id để khớp).
    """
    cond = Q(note__startswith=AUDIT_NOTE_PREFIX)
    for model, qs in _object_querysets():
        ids = [str(pk) for pk in qs.values_list("pk", flat=True)]
        if ids:
            cond |= Q(model_name=model._meta.label, object_id__in=ids)
    return cond


def _querysets(audit_filter, refund_ids):
    """Danh sách (nhãn, hàm trả queryset) theo thứ tự con trước cha (User xử lý riêng ở reset_qa)."""
    return [
        ("AuditLog", lambda: AuditLog.objects.filter(audit_filter)),
        ("CustomerCall", lambda: CustomerCall.objects.filter(note__code__startswith=PREFIX)),
        ("LabelPrint", lambda: LabelPrint.objects.filter(note__code__startswith=PREFIX)),
        ("ConfirmationTask", lambda: ConfirmationTask.objects.filter(note__code__startswith=PREFIX)),
        ("ReturnToStock", lambda: ReturnToStock.all_objects.filter(
            Q(note__startswith=PREFIX) | Q(batch__batch_id__startswith=PREFIX))),
        ("Refund", lambda: Refund.objects.filter(pk__in=refund_ids)),
        ("SalesCreditNote", lambda: SalesCreditNote.objects.filter(sales_invoice__code__startswith=PREFIX)),
        ("DeliveryNote", lambda: DeliveryNote.objects.filter(code__startswith=PREFIX)),
        ("PaymentTransaction", lambda: PaymentTransaction.objects.filter(bank_txn_id__startswith=PREFIX)),
        ("SalesInvoice", lambda: SalesInvoice.objects.filter(code__startswith=PREFIX)),
        ("SalesOrder", lambda: SalesOrder.objects.filter(code__startswith=PREFIX)),
        ("StockReconciliation", lambda: StockReconciliation.objects.filter(note__startswith=PREFIX)),
        ("PurchaseReceipt", lambda: PurchaseReceipt.objects.filter(note__startswith=PREFIX)),
        ("StockEntry", lambda: StockEntry.objects.filter(batch__batch_id__startswith=PREFIX)),
        ("StockLedgerEntry", lambda: StockLedgerEntry.objects.filter(batch__batch_id__startswith=PREFIX)),
        ("Batch", lambda: Batch.objects.filter(batch_id__startswith=PREFIX)),
        ("ItemPrice", lambda: ItemPrice.objects.filter(item__code__startswith=PREFIX)),
        ("Item", lambda: Item.objects.filter(code__startswith=PREFIX)),
        ("Supplier", lambda: Supplier.objects.filter(name__startswith=PREFIX)),
        ("Customer", _qa_customers),
        ("CallScript", lambda: CallScript.objects.filter(content__startswith=CALL_SCRIPT_PREFIX)),
    ]


def _add(deleted, per_model):
    for model_label, n in per_model.items():
        deleted[model_label] = deleted.get(model_label, 0) + n


def reset_qa():
    """
    Xoá bản ghi QA. Trả {"deleted": {nhãn: số}, "kept": [mô tả bản ghi còn giữ]}.
    Tài khoản qa_ còn bị bản ghi ngoài QA tham chiếu (Nhật ký, phiếu hoàn…) thì GIỮ, đặt is_active=False.
    """
    deleted, kept = {}, []
    with transaction.atomic():
        audit_filter = _audit_filter()  # tính một lần, trước khi xoá
        refund_ids = list(_qa_refunds().values_list("pk", flat=True))
        # Lặp vài lượt để tự tìm thứ tự: bản ghi bị PROTECT lượt này có thể xoá được ở lượt sau.
        for _round in range(4):
            progress = False
            for _label, make_qs in _querysets(audit_filter, refund_ids):
                for obj in list(make_qs()):
                    try:
                        with transaction.atomic():
                            _count, per_model = obj.delete()
                    except (ProtectedError, RestrictedError):
                        continue
                    progress = True
                    _add(deleted, per_model)
            if not progress:
                break
        for label, make_qs in _querysets(audit_filter, refund_ids):
            kept += [f"{label}#{obj.pk}" for obj in make_qs()]
        for user in list(_qa_users()):
            try:
                with transaction.atomic():  # hồ sơ nhân viên xoá cùng, hoàn tác nếu user bị giữ
                    StaffProfile.objects.filter(user=user).delete()
                    _count, per_model = user.delete()
            except (ProtectedError, RestrictedError):
                get_user_model().objects.filter(pk=user.pk).update(is_active=False)
                kept.append(f"User:{user.username}")
                continue
            _add(deleted, per_model)
    return {"deleted": deleted, "kept": kept}

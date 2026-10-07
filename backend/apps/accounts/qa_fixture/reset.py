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

from .build import CALL_SCRIPT_PREFIX, PHONE_PREFIX, PREFIX, USER_PREFIX


def _qa_user_ids():
    return list(get_user_model().objects.filter(username__startswith=USER_PREFIX).values_list("pk", flat=True))


def _querysets():
    """Danh sách (nhãn, hàm trả queryset) theo thứ tự con trước cha."""
    user_ids = _qa_user_ids()
    refund_ids = list(Refund.objects.filter(
        Q(reason__startswith=PREFIX) | Q(created_by_id__in=user_ids)).values_list("pk", flat=True))
    return [
        ("AuditLog", lambda: AuditLog.objects.filter(
            Q(note__startswith=PREFIX) | Q(object_repr__startswith=PREFIX)
            | Q(actor_id__in=user_ids) | Q(ai_actor_id__in=user_ids)
            | Q(model_name="sales.Refund", object_id__in=[str(i) for i in refund_ids])
            | Q(model_name="sales.SalesCreditNote", object_repr__startswith="DC-QA-"))),
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
        ("Customer", lambda: Customer.objects.filter(phone__startswith=PHONE_PREFIX)),
        ("CallScript", lambda: CallScript.objects.filter(content__startswith=CALL_SCRIPT_PREFIX)),
        ("StaffProfile", lambda: StaffProfile.objects.filter(user_id__in=user_ids)),
        ("User", lambda: get_user_model().objects.filter(pk__in=user_ids)),
    ]


def reset_qa():
    """Xoá bản ghi QA. Trả {"deleted": {nhãn: số}, "kept": [nhãn bản ghi còn bị dữ liệu khác giữ]}."""
    deleted, kept = {}, []
    with transaction.atomic():
        # Lặp vài lượt để tự tìm thứ tự: bản ghi bị PROTECT lượt này có thể xoá được ở lượt sau.
        for _round in range(4):
            progress = False
            for label, make_qs in _querysets():
                for obj in list(make_qs()):
                    try:
                        with transaction.atomic():
                            count, per_model = obj.delete()
                    except (ProtectedError, RestrictedError):
                        continue
                    progress = True
                    for model_label, n in per_model.items():
                        deleted[model_label] = deleted.get(model_label, 0) + n
            if not progress:
                break
        for label, make_qs in _querysets():
            kept += [f"{label}#{obj.pk}" for obj in make_qs()]
    return {"deleted": deleted, "kept": kept}

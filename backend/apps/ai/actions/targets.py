"""
Chuẩn hoá "chứng từ đích" của Việc AI (Lô 2, R1 — 02b §3.8).

`AiAction.target_model` hiện có nhiều dạng vì do nhiều chỗ ghi: pipeline ghi `model_name` ("purchasereceipt",
"batch"), chuyển việc ghi `doc_type` của guidance ("order", "batch"), một số chỗ ghi tên class ("Batch",
"AiConfigVersion"). Contract R1 dùng nhãn `app_label.model` ("purchasing.purchasereceipt"). Module này đổi mọi
dạng về nhãn đó để lọc và đếm gộp đúng, KHÔNG sửa dữ liệu đã ghi (không migration).
"""
from functools import lru_cache
from typing import Optional

from django.apps import apps

# doc_type của GET /api/guidance/<loại>/<id>/ → nhãn model (chuyển việc ghi doc_type vào target_model).
DOC_TYPE_LABELS: dict[str, str] = {
    "order": "sales.salesorder",
    "payment": "sales.paymenttransaction",
    "refund": "sales.refund",
    "batch": "inventory.batch",
    "receipt": "purchasing.purchasereceipt",
    "supplier": "purchasing.supplier",
    "stocktake": "inventory.stockreconciliation",
    "return": "inventory.returntostock",
    "delivery": "delivery.deliverynote",
    "item": "catalog.item",
    "customer": "sales.customer",
    "staff": "auth.user",
}

MAX_TARGET_IDS = 100


@lru_cache(maxsize=1)
def _labels_by_model_name() -> dict[str, tuple[str, ...]]:
    index: dict[str, list[str]] = {}
    for model in apps.get_models():
        index.setdefault(model._meta.model_name, []).append(model._meta.label_lower)
    return {name: tuple(sorted(labels)) for name, labels in index.items()}


def resolve_target_label(value: str) -> Optional[str]:
    """Đổi một giá trị `target_model` (mọi dạng) về nhãn `app.model`; không đổi được thì trả None."""
    raw = (value or "").strip().lower()
    if not raw:
        return None
    if "." in raw:
        try:
            return apps.get_model(raw)._meta.label_lower
        except (LookupError, ValueError):
            return None
    if raw in DOC_TYPE_LABELS:
        return DOC_TYPE_LABELS[raw]
    labels = _labels_by_model_name().get(raw, ())
    return labels[0] if len(labels) == 1 else None


def stored_variants(label: str) -> set[str]:
    """Mọi giá trị chữ thường có thể đang nằm ở `AiAction.target_model` cho model có nhãn `label`."""
    model = apps.get_model(label)
    variants = {label, model._meta.model_name, model._meta.object_name.lower()}
    variants.update(doc_type for doc_type, lbl in DOC_TYPE_LABELS.items() if lbl == label)
    return variants

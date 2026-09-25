"""
Dữ liệu demo gỡ được (D1, Duy 2026-09-24) — sổ đánh dấu `DemoRecord`.

- `track_demo_creations()`: trong khối `with`, MỌI bản ghi được TẠO MỚI (post_save created=True)
  trong tiến trình này đều được đánh dấu demo — kể cả bản ghi do signal sinh ra (vd phiếu giao
  tự tạo khi xuất hoá đơn). Bản ghi get_or_create tìm thấy sẵn (dữ liệu thật) không bị đánh dấu.
- `remove_demo()`: gỡ bản ghi đã đánh dấu. Mỗi bản ghi chỉ bị xoá khi TẤT CẢ những gì Django sẽ
  xoá/cập nhật theo (CASCADE, SET_NULL…) cũng là demo được gỡ, và không có bản ghi thật/đang giữ
  PROTECT nó. Bản ghi demo đang được dữ liệu thật dùng → giữ lại, báo "Giữ lại", vẫn giữ đánh dấu.
  Tập giữ lại tính theo BAO ĐÓNG (B2, QA lần 2): bản ghi demo là "một phần" của bản ghi đang giữ
  (giá, sổ kho, dòng chứng từ, hoá đơn/phiếu giao của đơn…) cũng giữ — chứng từ không bao giờ bị
  gỡ nửa chừng. Lặp nhiều lượt để tự tìm thứ tự xoá (con trước, cha sau).

Ngoại lệ có chủ đích của BR-PQ-10 (chứng từ không xoá): chỉ áp cho bản ghi có trong sổ demo.
AuditLog (BR-PQ-06) không bao giờ bị đánh dấu nên không bao giờ bị gỡ.
"""
from contextlib import contextmanager

from django.contrib.contenttypes.models import ContentType
from django.db import DEFAULT_DB_ALIAS, transaction
from django.db.models.deletion import Collector, ProtectedError, RestrictedError
from django.db.models.signals import post_save

from apps.accounts.models import DemoRecord
from apps.common.audit import record_audit

# Không bao giờ đánh dấu (hạ tầng, nhật ký append-only, chính sổ đánh dấu).
_NEVER_TRACK = {
    ("accounts", "demorecord"),
    ("accounts", "auditlog"),
    ("authtoken", "token"),
    ("sessions", "session"),
    ("admin", "logentry"),
    ("contenttypes", "contenttype"),
    ("auth", "permission"),
}


def _trackable(model) -> bool:
    meta = model._meta
    return not meta.auto_created and (meta.app_label, meta.model_name) not in _NEVER_TRACK


def _key(obj):
    return (obj._meta.concrete_model._meta.label_lower, str(obj.pk))


def mark_demo(obj):
    """Đánh dấu một bản ghi là demo (idempotent)."""
    if obj.pk is None or not _trackable(type(obj)):
        return
    ct = ContentType.objects.get_for_model(obj, for_concrete_model=True)
    DemoRecord.objects.get_or_create(content_type=ct, object_id=str(obj.pk))


def is_demo(obj) -> bool:
    """Bản ghi có trong sổ demo không (seed_demo chỉ đụng tồn của lô demo, không đụng lô thật)."""
    if obj.pk is None or not _trackable(type(obj)):
        return False
    ct = ContentType.objects.get_for_model(obj, for_concrete_model=True)
    return DemoRecord.objects.filter(content_type=ct, object_id=str(obj.pk)).exists()


@contextmanager
def track_demo_creations():
    """Đánh dấu mọi bản ghi tạo mới trong khối `with` (chỉ tiến trình hiện tại)."""

    def _on_save(sender, instance, created, raw=False, **kwargs):
        if created and not raw:
            mark_demo(instance)

    uid = f"demo-tracker-{id(_on_save)}"
    post_save.connect(_on_save, weak=False, dispatch_uid=uid)
    try:
        yield
    finally:
        post_save.disconnect(dispatch_uid=uid)


def _describe(obj) -> str:
    return f"{obj._meta.verbose_name} «{obj}»"


def _collected(collector):
    """Mọi bản ghi Collector sẽ xoá hoặc sửa (CASCADE, fast delete, SET_NULL/SET_DEFAULT)."""
    for model, instances in collector.data.items():
        if not model._meta.auto_created:
            yield from instances
    for qs in collector.fast_deletes:
        if not qs.model._meta.auto_created:
            yield from qs
    for objs in collector.field_updates.values():
        for batch in objs:
            yield from batch


def _try_delete(obj, demo_keys):
    """Xoá `obj` nếu mọi thứ bị kéo theo đều là demo. Trả (đã_xoá, [khoá đã xoá], [chặn])."""
    collector = Collector(using=DEFAULT_DB_ALIAS)
    try:
        collector.collect([obj])
    except ProtectedError as exc:
        return False, [], list(exc.protected_objects)
    except RestrictedError as exc:
        return False, [], list(exc.restricted_objects)
    touched = list(_collected(collector))
    foreign = [o for o in touched if _key(o) not in demo_keys]
    if foreign:
        return False, [], foreign
    keys = [_key(o) for o in touched]
    collector.delete()
    return True, keys, []


def _load_marked():
    """{khoá: instance} của bản ghi đánh dấu còn tồn tại; dọn dấu mồ côi."""
    found, orphan_ids = {}, []
    by_ct = {}
    for rec in DemoRecord.objects.select_related("content_type").order_by("pk"):
        by_ct.setdefault(rec.content_type, []).append(rec)
    for ct, recs in by_ct.items():
        model = ct.model_class()
        if model is None:
            orphan_ids += [r.pk for r in recs]
            continue
        objs = model._default_manager.in_bulk([r.object_id for r in recs])
        existing = {str(pk): o for pk, o in objs.items()}
        for rec in recs:
            obj = existing.get(rec.object_id)
            if obj is None:
                orphan_ids.append(rec.pk)
            else:
                found[_key(obj)] = obj
    DemoRecord.objects.filter(pk__in=orphan_ids).delete()
    return found


def _unmark(keys):
    by_label = {}
    for label, pk in keys:
        by_label.setdefault(label, []).append(pk)
    for label, pks in by_label.items():
        app_label, model_name = label.split(".")
        DemoRecord.objects.filter(
            content_type__app_label=app_label, content_type__model=model_name, object_id__in=pks
        ).delete()


# B2 (QA lần 2): FK "tham chiếu danh mục" — bản ghi trỏ tới cha bị giữ qua các field này KHÔNG
# phải là một phần của cha (vd lô demo của mặt hàng bị giữ, dòng đơn demo bán mặt hàng bị giữ)
# → vẫn gỡ được. MỌI FK khác = "một phần của" cha (giá của mặt hàng, sổ kho/giữ chỗ/phân bổ của
# lô, dòng của chứng từ, hoá đơn/thanh toán của đơn, phiếu giao/hoàn của hoá đơn…) → cha bị giữ
# thì giữ theo. Mặc định là "một phần" để model mới thêm sau này thiên về GIỮ (an toàn).
REFERENCE_FIELDS = {
    ("catalog.itemgroup", "parent"),
    ("catalog.item", "item_group"),
    ("catalog.bundleline", "component"),
    ("catalog.itemprice", "price_list"),
    ("inventory.batch", "item"),
    ("inventory.batch", "supplier"),
    ("inventory.batch", "warehouse"),
    ("purchasing.purchasereceipt", "supplier"),
    ("purchasing.purchasereceipt", "warehouse"),
    ("purchasing.purchasereceiptline", "item"),
    ("purchasing.purchaseinvoice", "supplier"),
    ("sales.salesorder", "customer"),
    ("sales.salesorderline", "item"),
    ("sales.salesorderline", "pricing_rule"),
    ("sales.salesorderlinebatch", "component_item"),
    ("sales.salesinvoice", "customer"),
    ("sales.salesinvoiceline", "item"),
    ("sales.salesinvoicelinebatch", "component_item"),
}


def _parents(obj):
    """[(field, khoá cha)] của các FK "một phần của" (không thuộc REFERENCE_FIELDS)."""
    label = obj._meta.concrete_model._meta.label_lower
    for field in obj._meta.concrete_fields:
        if not field.is_relation or (label, field.name) in REFERENCE_FIELDS:
            continue
        value = getattr(obj, field.attname)
        if value is None:
            continue
        parent_label = field.related_model._meta.concrete_model._meta.label_lower
        yield field, (parent_label, str(value))


def _close_over_parts(marked, kept):
    """Bao đóng: bản ghi demo là một phần của bản ghi đang giữ → giữ (lặp tới điểm bất động)."""
    changed = True
    while changed:
        changed = False
        for key, obj in marked.items():
            if key in kept:
                continue
            for _field, parent_key in _parents(obj):
                if parent_key in kept:
                    kept[key] = f"là một phần của {_kept_desc(marked, parent_key)} đang được giữ"
                    changed = True
                    break


def _kept_desc(marked, key):
    obj = marked.get(key)
    return _describe(obj) if obj is not None else f"{key[0]} #{key[1]}"


class _Blocked(Exception):
    """Lượt gỡ thử còn bản ghi không gỡ được → hoàn tác lượt đó, giữ chúng, tính lại."""

    def __init__(self, stuck):
        super().__init__()
        self.stuck = stuck


def _fresh(keys, marked):
    by_model = {}
    for key in keys:
        by_model.setdefault(type(marked[key])._meta.concrete_model, []).append(key[1])
    found = {}
    for model, pks in by_model.items():
        for obj in model._default_manager.filter(pk__in=pks):
            found[_key(obj)] = obj
    return {k: found[k] for k in keys if k in found}


def _delete_pass(marked, kept):
    """Gỡ mọi bản ghi demo không bị giữ (con trước, cha sau). Kẹt → raise _Blocked."""
    # Nạp lại bản ghi mỗi lượt: lượt trước bị hoàn tác nhưng Collector đã đặt pk=None trên
    # instance trong bộ nhớ.
    pending = _fresh([k for k in marked if k not in kept], marked)
    deletable = set(pending)  # bản ghi giữ lại coi như "dữ liệu thật" với lượt này
    deleted_counts, blockers = {}, {}
    progress = True
    while pending and progress:
        progress = False
        for key in list(pending):
            if key not in pending:
                continue  # đã bị xoá kéo theo ở bước trước
            ok, keys, blocked = _try_delete(pending[key], deletable)
            if not ok:
                blockers[key] = blocked
                continue
            progress = True
            for k in keys:
                pending.pop(k, None)
                deletable.discard(k)
                deleted_counts[k[0]] = deleted_counts.get(k[0], 0) + 1
            _unmark(keys)
    if pending:
        raise _Blocked({k: blockers.get(k, []) for k in pending})
    return deleted_counts


def _blocked_reason(blocked, marked, kept, stuck):
    real = [b for b in blocked if _key(b) not in marked]
    if real:
        return "đang được dữ liệu thật dùng: " + ", ".join(_describe(b) for b in real[:3])
    held = [b for b in blocked if _key(b) in kept or _key(b) in stuck]
    if held:
        return "phụ thuộc bản ghi demo đang được giữ: " + ", ".join(
            _describe(b) for b in held[:3])
    return "phụ thuộc bản ghi demo khác đang bị giữ"


def remove_demo(*, actor=None, dry_run=False) -> dict:
    """
    Gỡ dữ liệu demo đã đánh dấu. Trả {"deleted": {tên model: số}, "kept": [(mô tả, lý do)]}.

    Tập "giữ lại" tính theo bao đóng (B2, QA lần 2) — chứng từ giữ cả cụm hoặc gỡ cả cụm:
    1. Gỡ thử (savepoint). Bản ghi demo nào không gỡ được (dữ liệu thật PROTECT/CASCADE tới nó,
       hoặc nó kéo theo bản ghi đang giữ) → hoàn tác lượt thử, đưa vào tập giữ.
    2. Bản ghi demo là "một phần" của bản ghi đang giữ (FK ngoài REFERENCE_FIELDS: giá của mặt
       hàng, sổ kho của lô, dòng của đơn…) → giữ theo.
    Lặp tới khi một lượt gỡ trọn vẹn. `dry_run=True`: chạy đúng các bước đó rồi rollback —
    danh sách "Giữ lại" y hệt lần chạy thật.
    """
    with transaction.atomic():
        marked = _load_marked()
        kept = {}  # khoá → lý do (thứ tự chèn không dùng để in; in theo thứ tự sổ)
        while True:
            _close_over_parts(marked, kept)
            try:
                with transaction.atomic():
                    deleted_counts = _delete_pass(marked, kept)
                break
            except _Blocked as exc:
                for key, blocked in exc.stuck.items():
                    kept[key] = _blocked_reason(blocked, marked, kept, exc.stuck)
        kept_list = [(_describe(obj), kept[key]) for key, obj in marked.items() if key in kept]
        total = sum(deleted_counts.values())
        record_audit(
            "demo_remove", actor=actor,
            changes={"deleted": deleted_counts, "kept": len(kept_list)},
            note=f"Gỡ {total} bản ghi demo; giữ lại {len(kept_list)}."
            + (" (chạy thử, đã hoàn tác)" if dry_run else ""),
        )
        if dry_run:
            transaction.set_rollback(True)
    return {"deleted": deleted_counts, "kept": kept_list}

"""
Ảnh chụp số tài chính để so trước/sau một thao tác (W37 S1-AC3, S3-AC5, S6-AC6; BR-BC-06 "không sửa kỳ cũ").

Gồm: lãi lỗ kỳ (mọi tháng có chứng từ, qua service và qua API), lãi lỗ mọi lô (service và API), doanh thu hôm nay
của Tổng quan, và (số dòng, id lớn nhất) của năm bảng chứng từ. `pending_orders` cố ý KHÔNG nằm trong ảnh chụp
vì được phép đổi khi đơn sang Hoàn tất.
"""
import json

from django.db.models import Max
from django.utils import timezone

from apps.common.tests.fixtures import client_for
from apps.inventory.models import Batch, StockLedgerEntry
from apps.reports import services as report_services
from apps.sales.models import Refund, SalesCreditNote, SalesInvoice, SalesInvoiceLineBatch

DOCUMENT_MODELS = (SalesInvoice, SalesCreditNote, Refund, StockLedgerEntry, SalesInvoiceLineBatch)


def _months():
    """Mọi (năm, tháng) theo giờ VN từ chứng từ sớm nhất đến tháng hiện tại."""
    moments = []
    for model, field in ((SalesInvoice, "issued_at"), (SalesCreditNote, "issued_at"), (Refund, "confirmed_at")):
        first = model.objects.exclude(**{field: None}).order_by(field).values_list(field, flat=True).first()
        if first:
            moments.append(timezone.localtime(first))
    now = timezone.localtime()
    start = min(moments) if moments else now
    year, month = start.year, start.month
    months = []
    while (year, month) <= (now.year, now.month):
        months.append((year, month))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return months


def _dump(value):
    return json.loads(json.dumps(value, default=str, sort_keys=True))


def financial_snapshot(owner):
    client = client_for(owner)
    snapshot = {"documents": {}, "period_service": {}, "period_api": {}, "batch_service": {}}
    for model in DOCUMENT_MODELS:
        snapshot["documents"][model.__name__] = (model.objects.count(), model.objects.aggregate(m=Max("pk"))["m"])
    for year, month in _months():
        key = f"{year}-{month:02d}"
        snapshot["period_service"][key] = _dump(report_services.period_pnl(year=year, month=month))
        resp = client.get(f"/api/reports/period/?year={year}&month={month}")
        assert resp.status_code == 200, resp.content
        snapshot["period_api"][key] = _dump(resp.json())
    for batch in Batch.objects.order_by("pk"):
        snapshot["batch_service"][str(batch.pk)] = _dump(report_services.batch_pnl(batch=batch))
    resp = client.get("/api/reports/batches/")
    assert resp.status_code == 200, resp.content
    snapshot["batch_api"] = _dump(resp.json())
    resp = client.get("/api/dashboard/summary/")
    assert resp.status_code == 200, resp.content
    snapshot["revenue_today"] = resp.json()["kpis"]["revenue_today"]
    return snapshot

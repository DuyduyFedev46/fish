"""
API tổng hợp cho bảng điều hành (dashboard Cá Về).

Trả về dữ liệu THẬT từ DB trong một lần gọi: KPI, đơn gần đây, tồn theo lô,
cảnh báo cận hạn và dòng hoạt động. Chỉ cho người có quyền `reports.view_dashboard` (S6).
Giá vốn (landed_unit_cost) là field nhạy cảm — chỉ đính kèm khi user có quyền
`inventory.view_costprice` (chủ vựa / Tầng 1-2).
"""
from datetime import timedelta

from django.conf import settings
from django.db.models import DecimalField, F, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inventory.batches.services import SELLABLE_STATUSES, sellable_batches
from apps.inventory.models import Batch, StockLedgerEntry
from apps.sales.models import SalesInvoice, SalesOrder

PENDING = [SalesOrder.Status.BOOKED, SalesOrder.Status.PAID, SalesOrder.Status.PROCESSING]
ACTIVE_BATCH = [Batch.Status.SELLING, Batch.Status.NEAR_EXPIRY, Batch.Status.DRAFT]


def _money(v):
    return float(v or 0)


VIEW_DASHBOARD_PERM = "reports.view_dashboard"


class CanViewDashboard(BasePermission):
    """S6: Tổng quan chỉ cho người có `reports.view_dashboard` (chu/quan_ly/nv_kho).

    Chưa đăng nhập → 401 (DRF tự đổi khi không có user); thiếu quyền → 403 (BR-PQ-12).
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.has_perm(VIEW_DASHBOARD_PERM))


class DashboardSummaryView(APIView):
    permission_classes = [CanViewDashboard]

    def get(self, request):
        user = request.user
        today = timezone.localdate()
        now = timezone.now()
        near_days = getattr(settings, "BATCH_NEAR_EXPIRY_DAYS", 14)
        near_cutoff = today + timedelta(days=near_days)
        can_cost = user.has_perm("inventory.view_costprice")

        # ---- KPI ----
        revenue_today = SalesInvoice.objects.filter(
            status=SalesInvoice.Status.ISSUED, issued_at__date=today
        ).aggregate(s=Coalesce(Sum("amount"), 0, output_field=DecimalField()))["s"]

        pending_count = SalesOrder.objects.filter(status__in=PENDING).count()
        booked_soon = SalesOrder.objects.filter(
            status=SalesOrder.Status.BOOKED, booked_expires_at__isnull=False,
            booked_expires_at__lte=now + timedelta(minutes=10),
        ).count()

        active_batches = Batch.objects.filter(status__in=ACTIVE_BATCH)
        # R6 (code review): cận hạn = lô BÁN ĐƯỢC (cùng tiêu chí S1 — còn hạn, không DRAFT)
        # có hạn trong cửa sổ BATCH_NEAR_EXPIRY_DAYS. Lô quá hạn/nháp không cảnh báo cận hạn.
        near_expiry = sellable_batches(on_date=today).filter(expiry_date__lte=near_cutoff)
        near_expiry_count = near_expiry.count()

        # ---- Đơn gần đây ----
        orders = (
            SalesOrder.objects.select_related("customer")
            .order_by("-created_at", "-id")[:8]
        )
        recent_orders = [{
            "code": o.code,
            "customer": o.customer.name or "Khách lẻ",
            "phone_last4": (o.phone or "")[-4:],
            "amount": _money(o.total_amount),
            "status": o.status,
            "status_label": o.get_status_display(),
            "expires_at": o.booked_expires_at.isoformat() if o.booked_expires_at else None,
        } for o in orders]

        # ---- Tồn theo lô (FIFO theo received_date) ----
        batches = (
            active_batches.select_related("item", "warehouse", "supplier")
            .order_by("received_date", "id")[:20]
        )
        batch_rows = []
        for b in batches:
            near = b.status in SELLABLE_STATUSES and today <= b.expiry_date <= near_cutoff
            row = {
                "batch_id": b.batch_id,
                "item": b.item.name,
                "warehouse": b.warehouse.name,
                "supplier": b.supplier.name,
                "qty_available": _money(b.qty_available),
                "qty_reserved": _money(b.qty_reserved),
                "received_date": b.received_date.isoformat(),
                "expiry_date": b.expiry_date.isoformat(),
                "status": b.status,
                "status_label": b.get_status_display(),
                "near_expiry": near,
            }
            if can_cost:
                row["unit_cost"] = _money(b.landed_unit_cost)
            batch_rows.append(row)

        # ---- Cảnh báo cận hạn ----
        alerts = [{
            "batch_id": b.batch_id,
            "item": b.item.name,
            "expiry_date": b.expiry_date.isoformat(),
            "days_left": (b.expiry_date - today).days,
            "qty": _money(b.qty_available),
        } for b in near_expiry.select_related("item").order_by("expiry_date")[:6]]

        # ---- Dòng hoạt động (sổ kho gần đây) ----
        ledger = (
            StockLedgerEntry.objects.select_related("batch")
            .order_by("-created_at", "-id")[:8]
        )
        activity = [{
            "type": e.movement_type,
            "type_label": e.get_movement_type_display(),
            "batch_id": e.batch.batch_id,
            "qty_change": _money(e.qty_change),
            "reference": e.reference,
            "at": e.created_at.isoformat(),
        } for e in ledger]

        kpis = {
            "revenue_today": _money(revenue_today),
            "pending_orders": pending_count,
            "booked_soon": booked_soon,
            "near_expiry": near_expiry_count,
        }
        if can_cost:
            # Giá trị tồn = Σ qty × landed_unit_cost → giá vốn: thiếu quyền thì KHÔNG có key.
            kpis["inventory_value"] = _money(active_batches.aggregate(
                v=Coalesce(Sum(F("qty_available") * F("landed_unit_cost")), 0,
                           output_field=DecimalField())
            )["v"])

        return Response({
            "as_of": now.isoformat(),
            "near_expiry_days": near_days,  # R6: FE hiện "cận hạn N ngày" theo cấu hình
            "user": {"username": user.username, "can_cost": can_cost},
            "kpis": kpis,
            "recent_orders": recent_orders,
            "batches": batch_rows,
            "alerts": alerts,
            "activity": activity,
        })

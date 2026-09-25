"""
Báo cáo (P-10) — lãi lỗ theo lô (nguồn sự thật) & theo kỳ (điều hành).

Phase 1 chỉ đặt "chỗ treo quyền" cho `view_profitreport`. Logic tổng hợp báo cáo
(BR-BC-01..05) làm ở Phase 2/3. Model không có bảng dữ liệu riêng (managed=False):
báo cáo tính lại từ SalesInvoiceLineBatch + Batch.landed_unit_cost hiện hành.
"""
from django.db import models


class ProfitReport(models.Model):
    """Placeholder giữ custom permission — không tạo bảng CSDL."""

    class Meta:
        managed = False
        default_permissions = ()
        # Django vẫn tạo Permission cho model managed=False qua post_migrate.
        permissions = [
            ("view_profitreport", "Xem báo cáo giá vốn / lãi lỗ"),
            # S6: mục "Tổng quan" của console + `/api/dashboard/summary/` (chu, quan_ly, nv_kho).
            ("view_dashboard", "Xem Tổng quan vận hành"),
        ]
        verbose_name = "Báo cáo lãi lỗ"
        verbose_name_plural = "Báo cáo lãi lỗ"

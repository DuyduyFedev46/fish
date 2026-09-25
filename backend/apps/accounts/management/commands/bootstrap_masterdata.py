"""
Khởi tạo master data tối thiểu cho quy mô 1 điểm bán:
- 1 Kho duy nhất (V1 chỉ có 1 kho).
- 1 Bảng giá 'Bán lẻ' mặc định.

4 Group phân quyền đã được tạo bởi data migration accounts.0002 (không tạo ở đây).
Chạy: python manage.py bootstrap_masterdata
"""
from django.core.management.base import BaseCommand

from apps.catalog.models import PriceList
from apps.inventory.models import Warehouse


class Command(BaseCommand):
    help = "Tạo Kho mặc định và Bảng giá 'Bán lẻ' (idempotent)."

    def handle(self, *args, **options):
        wh, w_created = Warehouse.objects.get_or_create(
            name="Kho chính", defaults={"is_group": False}
        )
        pl, p_created = PriceList.objects.get_or_create(
            name="Bán lẻ", defaults={"currency": "VND", "is_default": True}
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Kho: {'tạo mới' if w_created else 'đã có'} → {wh.name}\n"
                f"Bảng giá: {'tạo mới' if p_created else 'đã có'} → {pl.name}"
            )
        )

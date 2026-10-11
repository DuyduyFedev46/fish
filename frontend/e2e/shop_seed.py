"""
Dữ liệu giả bổ sung cho e2e Shop (chạy bằng `manage.py shell < frontend/e2e/shop_seed.py`, sau `seed_demo` và `seed_qa`).
Do run_shop_e2e.py gọi, không chạy tay trên DB thật. Idempotent. SHOP-7-01.

Dựng: 5 nhóm hàng; món còn nhiều, món "sắp hết" (MUC-ONG còn 2 kg), món "hết" (TOM-SU-1), 2 combo
(COMBO-BEP-NHA còn nhiều, COMBO-TOM-MUC hết vì tôm sú hết); mô tả cho vài món; tắt các món QA-* của seed_qa
để Shop chỉ có bộ hàng demo. Chỉ dùng dữ liệu giả.
"""
from datetime import timedelta
from decimal import Decimal as D

from django.utils import timezone

from apps.catalog.models import Item, ItemGroup, ItemPrice, PriceList
from apps.catalog.models.items import BundleLine
from apps.inventory.models import Batch

Item.objects.filter(code__startswith="QA-").update(is_active=False)

# Đơn giữ chỗ của seed_demo/seed_qa hết hạn dần theo đồng hồ; kéo hạn ra 7 ngày để tồn "sắp hết/hết" không đổi trong lúc chạy e2e.
from apps.sales.models import SalesOrder
SalesOrder.objects.filter(status=SalesOrder.Status.BOOKED).update(booked_expires_at=timezone.now() + timedelta(days=7))

GROUPS = {
    "Cá": ["CA-THU", "CA-HOI-NU"],
    "Tôm": ["TOM-SU-1"],
    "Mực và bạch tuộc": ["MUC-ONG", "BACH-TUOC"],
    "Ghẹ": ["GHE-XANH"],
    "Combo": [],
}
group_by_name = {}
for name, codes in GROUPS.items():
    g, _ = ItemGroup.objects.get_or_create(name=name)
    group_by_name[name] = g
    for code in codes:
        Item.objects.filter(code=code).update(item_group=g)

# Tồn: CA-THU, CA-HOI-NU, GHE-XANH, BACH-TUOC còn nhiều; MUC-ONG sắp hết (2 kg bán được); TOM-SU-1 hết.
for batch in Batch.objects.filter(batch_id__in=["LO-0907", "LO-0903"]):
    batch.status = Batch.Status.SELLING
    if batch.batch_id == "LO-0907":
        batch.qty_available = batch.qty_reserved + D("2")
    else:
        batch.qty_available = batch.qty_reserved
        batch.status = Batch.Status.SOLD_OUT
    batch.save()

price_list = PriceList.objects.filter(is_default=True).first() or PriceList.objects.first()
today = timezone.localdate()

def make_combo(code, name, parts, price):
    combo, _ = Item.objects.get_or_create(
        code=code,
        defaults=dict(name=name, item_group=group_by_name["Combo"], item_type=Item.ItemType.BUNDLE,
                      shelf_life_in_days=10, is_active=True),
    )
    for comp_code, qty in parts:
        BundleLine.objects.get_or_create(
            bundle=combo, component=Item.objects.get(code=comp_code), defaults={"qty_per_bundle": D(qty)})
    if not ItemPrice.objects.filter(price_list=price_list, item=combo).exists():
        ItemPrice.objects.create(price_list=price_list, item=combo, rate=D(price), valid_from=today - timedelta(days=30))
    return combo

make_combo("COMBO-BEP-NHA", "Combo bếp nhà", [("CA-THU", "1"), ("GHE-XANH", "0.5"), ("BACH-TUOC", "0.5")], 450000)
make_combo("COMBO-TOM-MUC", "Combo tôm mực", [("TOM-SU-1", "1"), ("MUC-ONG", "0.5")], 520000)

Item.objects.filter(code="CA-THU").update(
    short_note="Thịt chắc, ít xương",
    description="Cá thu cấp đông theo lô, phi lê sẵn. Dùng kho tộ, chiên hoặc hấp gừng.",
    spec="Cắt khúc dày 3 cm, đóng túi hút chân không",
    storage="Giữ ngăn đá, rã đông ngăn mát trước khi nấu",
    origin="Cảng cá Phan Thiết",
)
Item.objects.filter(code="MUC-ONG").update(short_note="Mực ống làm sạch")
print("shop_seed ok:", {i.code: i.is_active for i in Item.objects.all()})

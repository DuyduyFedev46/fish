"""
Định tuyến API (/api/). Ba nhóm:
- Shop (công khai, guest) — Next.js gọi.
- Nội bộ (SessionAuth + perm) — back-office.
- Internal (service token) — adapter FastAPI gọi vào.

View import từ module tính năng `apps/<domain>/<tinh_nang>/api.py` (xem backend/README.md).
URL giữ nguyên — FE/adapter không phải đổi gì.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.audit.api import AuditLogListView
from apps.accounts.auth.api import ChangePasswordView, LoginTokenView, LogoutView, MeView
from apps.accounts.staff.api import StaffViewSet
from apps.ai.actions.api import AiActionViewSet
from apps.ai.commands.api import CommandCatalogView
from apps.ai.execution.pipeline import AiCommandCallView
from apps.ai.registry.api import AiCommandDetailView, AiCommandsIndexView
from apps.common.guidance.api import GuidanceView
import apps.sales.orders.next_steps  # noqa: F401 - đăng ký guidance provider cho order
from apps.catalog.images.api import ItemImageDetailView
from apps.catalog.items.api import BundleLineViewSet, ItemGroupViewSet, ItemViewSet
from apps.catalog.items.shop_api import ShopCatalogView, ShopItemDetailView
from apps.catalog.pricing.api import ItemPriceViewSet, PriceListViewSet, PricingRuleViewSet
from apps.delivery.api import DeliveryNoteViewSet
from apps.inventory.batches.api import BatchViewSet
from apps.inventory.returns.api import ReturnToStockViewSet
from apps.inventory.stock.api import StockEntryViewSet, StockLedgerEntryViewSet, WarehouseViewSet
from apps.inventory.stocktake.api import StockReconciliationViewSet
from apps.purchasing.costs.api import PurchaseCostViewSet
from apps.purchasing.invoices.api import PurchaseInvoiceViewSet
from apps.purchasing.receipts.api import PurchaseReceiptViewSet, SupplierViewSet
from apps.reports.api import BatchPnlView, PeriodPnlView
from apps.reports.dashboard_api import DashboardSummaryView
from apps.sales.customers.api import CustomerViewSet
from apps.sales.orders.api import SalesOrderViewSet
from apps.sales.orders.shop_api import ShopOrderCreateView, ShopOrderLookupView
from apps.sales.payments.api import PaymentTransactionViewSet, SalesInvoiceViewSet
from apps.sales.payments.internal_api import SepayGatewayIpnInternalView, SepayWebhookInternalView
from apps.sales.payments.shop_api import ShopOrderCheckoutView
from apps.sales.refunds.api import RefundViewSet

router = DefaultRouter()
# catalog
router.register("catalog/item-groups", ItemGroupViewSet)
router.register("catalog/items", ItemViewSet)
router.register("catalog/bundle-lines", BundleLineViewSet)
router.register("catalog/price-lists", PriceListViewSet)
router.register("catalog/item-prices", ItemPriceViewSet)
router.register("catalog/pricing-rules", PricingRuleViewSet)
# inventory
router.register("inventory/warehouses", WarehouseViewSet)
router.register("inventory/batches", BatchViewSet)
router.register("inventory/stock-entries", StockEntryViewSet)
router.register("inventory/ledger", StockLedgerEntryViewSet)
router.register("inventory/reconciliations", StockReconciliationViewSet)
router.register("inventory/returns", ReturnToStockViewSet)
# purchasing
router.register("purchasing/suppliers", SupplierViewSet)
router.register("purchasing/receipts", PurchaseReceiptViewSet)
router.register("purchasing/invoices", PurchaseInvoiceViewSet)
router.register("purchasing/costs", PurchaseCostViewSet)
# sales
router.register("sales/customers", CustomerViewSet)
router.register("sales/orders", SalesOrderViewSet)
router.register("sales/invoices", SalesInvoiceViewSet)
router.register("sales/refunds", RefundViewSet)
router.register("sales/payments", PaymentTransactionViewSet)
# delivery
router.register("delivery/notes", DeliveryNoteViewSet)
# accounts — quản lý nhân viên (S41, S42)
router.register("staff", StaffViewSet, basename="staff")
# AI Actions — Việc AI (DW-11)
router.register("ai/actions", AiActionViewSet, basename="ai-actions")

urlpatterns = [
    # Shop công khai (guest)
    path("shop/catalog/", ShopCatalogView.as_view()),
    path("shop/catalog/<str:item_code>/", ShopItemDetailView.as_view()),
    path("shop/orders/", ShopOrderCreateView.as_view()),
    path("shop/orders/<str:order_code>/", ShopOrderLookupView.as_view()),
    # P1: lập tham số thanh toán cổng SePay cho đơn Giữ chỗ (lần đầu hoặc thanh toán lại).
    path("shop/orders/<str:order_code>/checkout/", ShopOrderCheckoutView.as_view()),
    # Đăng nhập token cho dashboard SPA
    path("auth/token/", LoginTokenView.as_view()),
    path("auth/me/", MeView.as_view()),
    path("auth/logout/", LogoutView.as_view()),
    path("auth/change-password/", ChangePasswordView.as_view()),
    # Bảng điều hành (dashboard vận hành)
    path("dashboard/summary/", DashboardSummaryView.as_view()),
    # Báo cáo
    path("reports/batch/<str:batch_id>/", BatchPnlView.as_view()),
    path("reports/period/", PeriodPnlView.as_view()),
    # Internal (adapter)
    path("internal/payments/sepay-webhook/", SepayWebhookInternalView.as_view()),
    # P3: IPN Cổng thanh toán SePay (adapter POST /ipn/sepay -> đây), Source.GATEWAY.
    # Path khớp CHÍNH XÁC hằng số DJANGO_IPN_ENDPOINT_PATH ở adapter/app/main.py (P2).
    path("internal/payments/sepay-ipn/", SepayGatewayIpnInternalView.as_view()),
    # S11: contract viết không có "/" cuối — nhận cả hai dạng (router tự có dạng có "/").
    path("sales/orders/<int:pk>/confirm-payment",
         SalesOrderViewSet.as_view({"post": "confirm_payment"})),
    # S12: như trên, contract viết không có "/" cuối.
    path("sales/payments/<int:pk>/resolve",
         PaymentTransactionViewSet.as_view({"post": "resolve"})),
    # A2/A3: tải lên / thay (POST) hoặc gỡ (DELETE) ảnh mặt hàng — quyền catalog.change_item_image.
    path("catalog/items/<int:pk>/image/", ItemImageDetailView.as_view()),
    # S01 (AI Native ERP): catalog lệnh nghiệp vụ — lọc theo quyền (registry là code).
    path("commands/catalog/", CommandCatalogView.as_view()),
    # S03: nhật ký hành động (append-only) — quyền accounts.view_auditlog (chu + quan_ly).
    path("audit-logs/", AuditLogListView.as_view()),
    # Tiếp theo · Đã làm (02b §6.7, DW-03)
    path("guidance/<str:doc_type>/<str:doc_id>/", GuidanceView.as_view(), name="guidance-detail"),
    # Lệnh AI tự sinh (02b §6.1, §6.2, DW-07, DW-10)
    path("ai/commands/index/", AiCommandsIndexView.as_view(), name="ai-commands-index"),
    path("ai/commands/<str:command_id>/call/", AiCommandCallView.as_view(), name="ai-commands-call"),
    path("ai/commands/<str:command_id>/", AiCommandDetailView.as_view(), name="ai-commands-detail"),
    # Back-office (router)
    path("", include(router.urls)),
]

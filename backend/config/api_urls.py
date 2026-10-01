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
from apps.accounts.capabilities.api import GroupCapabilitiesView, GroupDetailView, GroupListView
from apps.accounts.staff.api import StaffViewSet
from apps.ai.actions.api import AiActionViewSet
from apps.ai.execution.pipeline import AiCommandCallView
from apps.ai.policy.api import (
    AiPolicyUserConfigView,
    AiPolicyUserKillView,
    AiPolicyVersionsView,
    AiPolicyView,
)
from apps.ai.registry.api import AiCommandDetailView, AiCommandsIndexView
from apps.ai.report.api import AiDailyReportView
from apps.ai.settings.api import MyConfigKillView, MyConfigVersionsView, MyConfigView
from apps.common.guidance.api import GuidanceView
from apps.content.site.api import SiteInfoView
import apps.sales.orders.next_steps  # noqa: F401 - đăng ký guidance provider cho order
from apps.catalog.images.api import ItemImageDetailView
from apps.catalog.items.api import BundleLineViewSet, ItemGroupViewSet, ItemViewSet
from apps.catalog.items.shop_api import ShopCatalogView, ShopItemDetailView
from apps.catalog.pricing.api import ItemPriceViewSet, PriceListViewSet, PricingRuleViewSet
from apps.delivery.api import DeliverersView, DeliveryNoteViewSet
from apps.delivery.attention_api import DashboardAttentionView
from apps.delivery.confirmation.api import ConfirmationQueueViewSet, CustomerSearchView
from apps.inventory.batches.api import BatchViewSet
from apps.inventory.returns.api import ReturnToStockViewSet
from apps.inventory.stock.api import StockEntryViewSet, StockLedgerEntryViewSet, WarehouseViewSet
from apps.inventory.stocktake.api import StockReconciliationViewSet
from apps.purchasing.costs.api import PurchaseCostViewSet
from apps.purchasing.invoices.api import PurchaseInvoiceViewSet
from apps.purchasing.receipts.api import PurchaseReceiptViewSet, SupplierViewSet
from apps.reports.api import BatchPnlListView, BatchPnlView, PeriodPnlView
from apps.reports.dashboard_api import DashboardSummaryView
from apps.sales.customers.api import CustomerViewSet
from apps.sales.customers.directory_api import CustomerDirectoryViewSet
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
router.register("sales/customer-directory", CustomerDirectoryViewSet, basename="customer-directory")
router.register("sales/orders", SalesOrderViewSet)
router.register("sales/invoices", SalesInvoiceViewSet)
router.register("sales/refunds", RefundViewSet)
router.register("sales/payments", PaymentTransactionViewSet)
# delivery
router.register("delivery/notes", DeliveryNoteViewSet)
# confirmation — hàng đợi gọi xác nhận đơn. Tiền tố `/api/confirmation/` nằm trong FORBIDDEN_PREFIXES của AI (P8b Lô 3, R1);
# tiền tố cũ `/api/cskh/` đã gỡ ở Lô 5 nhưng vẫn giữ trong FORBIDDEN_PREFIXES vĩnh viễn.
router.register("confirmation/queue", ConfirmationQueueViewSet, basename="confirmation-queue")
# accounts — quản lý nhân viên (S41, S42)
router.register("staff", StaffViewSet, basename="staff")
# AI Actions — Việc AI (DW-11)
router.register("ai/actions", AiActionViewSet, basename="ai-actions")
# content — CMS nội dung (2026-09-28-cms-viet-bai)
from apps.content.categories.api import CategoryViewSet
from apps.content.entries.api import EntryViewSet, GoliveStatusView
from apps.content.images.api import ContentImageViewSet, EntryImageUploadView
from apps.content.public.api import (
    PublicCategoryListView,
    PublicEntryDetailView,
    PublicEntryListView,
    PublicFooterLinksView,
    PublicPageByRoleView,
)

router.register("content/categories", CategoryViewSet, basename="content-categories")
router.register("content/entries", EntryViewSet, basename="content-entries")
router.register("content/images", ContentImageViewSet, basename="content-images")


urlpatterns = [
    # CMS Golive Status (CMS-15)
    path("content/golive-status/", GoliveStatusView.as_view(), name="content-golive-status"),
    # CMS Content Image Upload (CMS-05)
    path("content/entries/<int:pk>/images/", EntryImageUploadView.as_view()),
    # CMS Content Public API (CMS-13, CMS-14, CMS-15)
    path("public/content/entries/", PublicEntryListView.as_view(), name="public-content-entries-list"),
    path("public/content/entries/<str:slug>/", PublicEntryDetailView.as_view(), name="public-content-entries-detail"),
    path("public/content/categories/", PublicCategoryListView.as_view(), name="public-content-categories"),
    path("public/content/pages/by-role/<str:role>/", PublicPageByRoleView.as_view(), name="public-content-pages-by-role"),
    path("public/content/footer-links/", PublicFooterLinksView.as_view(), name="public-content-footer-links"),
    # Thông tin công khai cho Shop web (CS-10, GL-01, GL-04)
    path("public/site-info/", SiteInfoView.as_view(), name="public-site-info"),

    # Ma trận phân quyền (B4): khai trước include(router.urls) để StaffViewSet không bắt pk="groups".
    path("staff/groups/", GroupListView.as_view(), name="staff-groups"),
    path("staff/groups/<str:code>/capabilities/", GroupCapabilitiesView.as_view(), name="staff-group-capabilities"),
    path("staff/groups/<str:code>/", GroupDetailView.as_view(), name="staff-group-detail"),
    # Danh sách người giao kèm số phiếu đang giữ (BR-GH-23).
    path("delivery/deliverers/", DeliverersView.as_view(), name="delivery-deliverers"),
    # Tìm kiếm nhanh đơn cho việc gọi xác nhận (chỉ POST).
    path("confirmation/search/", CustomerSearchView.as_view(), name="confirmation-search"),
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
    path("dashboard/attention/", DashboardAttentionView.as_view(), name="dashboard-attention"),
    # Báo cáo
    path("reports/batches/", BatchPnlListView.as_view()),
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
    # S03: nhật ký hành động (append-only) — quyền accounts.view_auditlog (chu + quan_ly).
    path("audit-logs/", AuditLogListView.as_view()),
    # Tiếp theo · Đã làm (02b §6.7, DW-03)
    path("guidance/<str:doc_type>/<str:doc_id>/", GuidanceView.as_view(), name="guidance-detail"),
    # Lệnh AI tự sinh (02b §6.1, §6.2, DW-07, DW-10)
    path("ai/commands/index/", AiCommandsIndexView.as_view(), name="ai-commands-index"),
    path("ai/commands/<str:command_id>/call/", AiCommandCallView.as_view(), name="ai-commands-call"),
    path("ai/commands/<str:command_id>/", AiCommandDetailView.as_view(), name="ai-commands-detail"),
    # AI của tôi (02b §6.5, DW-12)
    path("ai/my-config/kill/", MyConfigKillView.as_view(), name="ai-my-config-kill"),
    path("ai/my-config/versions/", MyConfigVersionsView.as_view(), name="ai-my-config-versions"),
    path("ai/my-config/", MyConfigView.as_view(), name="ai-my-config"),
    # Chính sách AI của Chủ (02b §6.6, DW-13)
    path("ai/policy/users/<int:user_id>/kill/", AiPolicyUserKillView.as_view(), name="ai-policy-user-kill"),
    path("ai/policy/users/<int:user_id>/config/", AiPolicyUserConfigView.as_view(), name="ai-policy-user-config"),
    path("ai/policy/versions/", AiPolicyVersionsView.as_view(), name="ai-policy-versions"),
    path("ai/policy/", AiPolicyView.as_view(), name="ai-policy"),
    # Báo cáo AI cuối ngày (02b §6.6, DW-22)
    path("ai/report/daily/", AiDailyReportView.as_view(), name="ai-report-daily"),
    # P8b Lô 3-5: nhập lô mua tại cảng (id lệnh AI `...receive_batches`, `spec.path` là `/receive-batches/`). Đặt trước
    # router vì route chi tiết `<pk>/` của router sẽ nuốt `receive-batches/`. Route tên cũ đã gỡ ở Lô 5.
    path("purchasing/receipts/receive-batches/", PurchaseReceiptViewSet.as_view({"post": "receive_batches"})),
    # Back-office (router)
    path("", include(router.urls)),
]

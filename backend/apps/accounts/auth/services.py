"""
Nghiệp vụ "tôi là ai, có quyền gì" (S6, S47 · BR-PQ-09, UC-01) và phiên đăng nhập
(S46 · đăng xuất, tự đổi mật khẩu).

Console chỉ đọc kết quả này để dựng menu/nút; backend vẫn là lớp chặn (BR-PQ-12).
C8: DRF cấp **một token mỗi người** → đăng xuất / đổi mật khẩu thu token là văng mọi máy.
"""
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework.authtoken.models import Token

from apps.accounts import roles
from apps.accounts.models import StaffProfile
from apps.common.ai_visibility import ai_features_enabled
from apps.common.api import VIEW_COSTPRICE_PERM
from apps.common.audit import record_audit
from apps.common.exceptions import BusinessError

from .authentication import has_erp_access, must_change_password

VIEW_PROFITREPORT_PERM = "reports.view_profitreport"

# Thứ tự hiển thị cố định theo vai (không theo thứ tự gán trong DB).
ROLE_ORDER = roles.ALL_ROLES

HOME_DASHBOARD = "dashboard"
HOME_MY_DELIVERIES = "my-deliveries"
HOME_CONFIRMATION_QUEUE = "confirmation-queue"
HOME_NO_ROLE = "no-role"

# S47: nhãn tiếng Việt cho màn "Quyền của tôi".
GROUP_LABELS = {
    roles.OWNER: "Chủ",
    roles.MANAGER: "Quản lý",
    roles.WAREHOUSE_STAFF: "Nhân viên kho",
    roles.DELIVERY_STAFF: "Nhân viên giao",
    roles.CUSTOMER_SERVICE: "Nhân viên gọi xác nhận",
}

# S47: quyền Tầng 2 = bảng spec §1.5 + mọi `Meta.permissions` tuỳ biến. Thứ tự dict = thứ tự
# hiển thị: 5 việc uỷ cho Quản lý (S47-AC1) → việc của Chủ → quyền xem.
# Thêm quyền Tầng 2 mới thì thêm nhãn ở đây (test_s47_moi_quyen_meta_permissions_deu_co_nhan).
CAPABILITY_LABELS = {
    "inventory.publish_batch": "Mở bán lô",
    "sales.cancel_paid_order": "Huỷ đơn đã thanh toán",
    "sales.create_refund": "Lập phiếu hoàn tiền",
    "inventory.approve_returntostock": "Duyệt hàng hoàn",
    "inventory.approve_stockreconciliation": "Duyệt kiểm kê",
    "inventory.close_batch": "Chốt lô",
    "purchasing.add_purchasecost": "Nhập chi phí mua",
    "sales.confirm_refund": "Xác nhận đã hoàn tiền",
    "sales.confirm_payment_manual": "Xác nhận đã nhận tiền",
    "accounts.manage_staff": "Quản lý nhân viên",
    "inventory.view_costprice": "Xem giá vốn",
    "reports.view_profitreport": "Xem báo cáo lãi lỗ",
    "reports.view_dashboard": "Xem Tổng quan",
    # A2 (doc/features/2026-09-26-anh-mat-hang, Q3): chu + quan_ly. Không mở `change_item`.
    "catalog.change_item_image": "Sửa ảnh mặt hàng",
    # DW-06 (2026-09-28-ai-digital-worker): chỉ chu.
    "inventory.cancel_expired_batch": "Huỷ lô quá hạn",
    # DW-13 (2026-09-28-ai-digital-worker): chỉ chu.
    "ai.manage_ai_policy": "Quản lý chính sách AI",
    # CS-01 / CS-03 / CS-11 (2026-09-28-cskh-xac-nhan-in-tem): CSKH + kho + QL + Chủ.
    "delivery.confirm_with_customer": "Gọi xác nhận đơn",
    "delivery.change_recipient": "Đổi thông tin nhận hàng",
    "delivery.decide_unconfirmed": "Quyết định đơn không liên lạc được",
    "delivery.pack_deliverynote": "Soạn hàng",
    "delivery.print_label": "In / huỷ tem giao",
    # CMS (2026-09-28-cms-viet-bai): Quyền Tầng 2 đăng/gỡ/trả về nháp bài viết và trang
    "content.publish_entry": "Đăng bài lên Shop",
    # GL-05 (2026-09-28-khung-go-live): chu + quan_ly.
    "sales.view_privacy_consent": "Xem bằng chứng đồng ý xử lý dữ liệu của đơn",
    "delivery.assign_deliverynote": "Chọn người giao",
    # B2 (ERP theo design, Lô 6): chu + quan_ly. Khác `sales.view_customer` (Tầng 1, phạm vi dòng của NV giao).
    "sales.view_customer_list": "Xem khách hàng",
    # PV-07 (2026-10-02-pham-vi-du-lieu-cau-hinh): việc V2, cấp cho 5 nhóm (Q-4).
    "sales.view_order_customer_info": "Xem thông tin khách trên đơn, hoá đơn, phiếu hoàn tiền",
}

AUTH_OLD_PASSWORD = "AUTH_OLD_PASSWORD"
AUTH_WEAK_PASSWORD = "AUTH_WEAK_PASSWORD"


def sorted_groups(names):
    """Tên Group theo thứ tự vai cố định (owner, manager, warehouse_staff, delivery_staff, customer_service; nhóm lạ xếp sau)."""
    rank = {name: i for i, name in enumerate(ROLE_ORDER)}
    return sorted(names, key=lambda n: (rank.get(n, len(ROLE_ORDER)), n))


def home_for(user, groups) -> str:
    """Trang mặc định: không có quyền vào ERP (cùng luật `has_erp_access` với cổng D-3) → no-role;
    superuser → dashboard (Duy 08/10 câu 1); chỉ delivery_staff → my-deliveries; chỉ customer_service →
    confirmation-queue; còn lại → dashboard."""
    if not has_erp_access(user):
        return HOME_NO_ROLE
    if user.is_superuser:
        return HOME_DASHBOARD
    if set(groups) == {roles.DELIVERY_STAFF}:
        return HOME_MY_DELIVERIES
    if set(groups) == {roles.CUSTOMER_SERVICE}:
        return HOME_CONFIRMATION_QUEUE
    return HOME_DASHBOARD


def describe_user(user) -> dict:
    """JSON của `GET /api/auth/me/` cho user đã đăng nhập (contract S6)."""
    groups = sorted_groups(user.groups.values_list("name", flat=True))
    permissions = user.get_all_permissions()
    ai_on = ai_features_enabled()
    profile = getattr(user, "staff_profile", None)  # RelatedObjectDoesNotExist là AttributeError
    return {
        "id": user.pk,
        "username": user.get_username(),
        "display_name": (profile.display_name if profile else "")
        or user.get_full_name()
        or user.get_username(),
        "phone": profile.phone if profile else "",
        "groups": groups,
        "permissions": sorted(permissions),
        "can_view_cost": user.has_perm(VIEW_COSTPRICE_PERM),
        "can_view_profit": user.has_perm(VIEW_PROFITREPORT_PERM),
        "home": home_for(user, groups),
        # S47 — chỉ THÊM key, không đổi key S6.
        "group_labels": [{"code": g, "label": GROUP_LABELS.get(g, g)} for g in groups],
        "capabilities": [
            {"code": code, "label": label}
            for code, label in CAPABILITY_LABELS.items()
            if code in permissions and (ai_on or not code.startswith("ai."))
        ],
        # Lô dọn chữ AI (W39): cờ môi trường, FE chỉ hiện phần AI khi cờ này bật.
        "ai_features_enabled": ai_on,
        # S48 (BR-PQ-19): cờ hiệu lực — superuser luôn False.
        "must_change_password": must_change_password(user),
        # PV-14 (review 07/10) + Duy 08/10 câu 1: FE phân biệt superuser không nhóm.
        "is_superuser": bool(user.is_superuser),
    }


# --- S46: đăng xuất, tự đổi mật khẩu ------------------------------------------------


@transaction.atomic
def logout(*, user) -> int:
    """Thu token của người đang đăng nhập (C8: mọi máy văng). Trả số token đã xoá."""
    revoked, _ = Token.objects.filter(user=user).delete()
    record_audit("logout", actor=user, obj=user, note=f"Đăng xuất; thu hồi {revoked} token.")
    return revoked


@transaction.atomic
def change_own_password(*, user, old_password, new_password) -> str:
    """
    Tự đổi mật khẩu (S46-AC2). Chỉ đổi của chính `user` (BR-PQ-17).

    Kiểm mật khẩu hiện tại trước, rồi `AUTH_PASSWORD_VALIDATORS` (thông điệp tiếng Việt).
    Thành công: xoá mọi token cũ, cấp token mới, ghi AuditLog `password_change_self`
    (không chứa mật khẩu). Lỗi → không đổi gì, token cũ vẫn dùng được.
    """
    user = User.objects.select_for_update().get(pk=user.pk)
    if not isinstance(old_password, str) or not user.check_password(old_password):
        raise BusinessError("Mật khẩu hiện tại không đúng.", code=AUTH_OLD_PASSWORD)
    if not isinstance(new_password, str) or not new_password:
        raise BusinessError("Mật khẩu mới là bắt buộc.", code=AUTH_WEAK_PASSWORD)
    if user.check_password(new_password):
        # B4 (QA lần 2) · BR-PQ-19: mật khẩu mới phải là của riêng người dùng — không giữ
        # mật khẩu tạm Chủ đã biết. Cờ must_change_password giữ nguyên.
        raise BusinessError("Mật khẩu mới phải khác mật khẩu hiện tại.", code=AUTH_WEAK_PASSWORD)
    try:
        validate_password(new_password, user=user)
    except ValidationError as exc:
        raise BusinessError(" ".join(exc.messages), code=AUTH_WEAK_PASSWORD) from None
    user.set_password(new_password)
    user.save(update_fields=["password"])
    StaffProfile.objects.filter(user=user).update(must_change_password=False)  # BR-PQ-19
    revoked, _ = Token.objects.filter(user=user).delete()
    token = Token.objects.create(user=user)
    record_audit(
        "password_change_self", actor=user, obj=user,
        note=f"Tự đổi mật khẩu; thu hồi {revoked} token, cấp token mới.",
    )
    return token.key

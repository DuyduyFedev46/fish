"""
Duyệt URL Resolver và khám phá lệnh từ DRF ViewSet/APIView (Spike DW-01, 02b §2, §3).
"""
import re
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver
from rest_framework.viewsets import ViewSetMixin
from rest_framework.views import APIView

from .schema import serializer_to_schema, estimate_schema_tokens

FORBIDDEN_PREFIXES = (
    "/api/shop/",
    "/api/internal/",
    "/api/auth/",
    "/api/ai/",
    "/api/staff/",
    "/api/audit-logs/",
    "/api/commands/",
    "/api/public/",
    "/api/cskh/",
)

FORBIDDEN_SUFFIXES = (
    "/label/",
    "/label/print/",
    "/label",
    "/label/print",
)

APP_GROUP_MAP = {
    "catalog": "danh_muc",
    "inventory": "kho",
    "purchasing": "thu_mua",
    "sales": "ban_hang",
    "delivery": "giao_hang",
    "reports": "bao_cao",
    "accounts": "he_thong",
}


def is_url_forbidden(path):
    """Kiểm tra URL có nằm trong danh sách cấm tất định không."""
    normalized = "/" + path.strip("/") + "/" if path.strip("/") else "/"
    for prefix in FORBIDDEN_PREFIXES:
        if normalized.startswith(prefix):
            return True
    for suffix in FORBIDDEN_SUFFIXES:
        if normalized.rstrip("/").endswith(suffix.rstrip("/")):
            return True
    return False


def discover_commands():
    """
    Duyệt đệ quy url resolver để tìm mọi ViewSet / APIView dưới /api/.
    Trả về danh sách CommandSpec dict.
    """
    resolver = get_resolver()
    routes = []
    _collect_routes(resolver.url_patterns, prefix="", routes=routes)

    commands = []
    seen_ids = set()

    for pattern_str, callback, default_args in routes:
        full_path = "/" + pattern_str.strip("/") + ("/" if pattern_str.strip("/") else "")
        if not full_path.startswith("/api/"):
            continue
        if is_url_forbidden(full_path):
            continue

        cls = getattr(callback, "cls", None)
        if cls is None:
            continue

        app_name = cls.__module__.split(".")[1] if "apps." in cls.__module__ else "app"
        group = APP_GROUP_MAP.get(app_name, "khac")

        # Trường hợp ViewSet (có callback.actions)
        actions_map = getattr(callback, "actions", None)
        if actions_map:
            for method, action_name in actions_map.items():
                method_upper = method.upper()
                # Bỏ PUT (update), chỉ giữ PATCH (partial_update) cho sửa
                if method_upper == "PUT" and action_name == "update":
                    continue

                model_name = getattr(getattr(cls, "queryset", None), "model", None)
                model_str = model_name._meta.model_name if model_name else cls.__name__.lower().replace("viewset", "")

                cmd_id = f"{app_name}.{model_str}.{action_name}"
                if cmd_id in seen_ids:
                    continue
                seen_ids.add(cmd_id)

                kind = "read" if method_upper in ("GET", "HEAD", "OPTIONS") else "write"
                title = _make_title(cls, action_name, model_str)

                # Lấy serializer
                serializer_cls = _get_serializer_for_action(cls, action_name)
                schema, unsupported = serializer_to_schema(serializer_cls)
                if schema is None and kind == "read":
                    schema = {"type": "object", "properties": {}}
                is_form_only = (kind == "write" and schema is None)

                tokens = estimate_schema_tokens(schema)

                commands.append({
                    "id": cmd_id,
                    "title": title,
                    "kind": kind,
                    "group": group,
                    "app": app_name,
                    "model": model_str,
                    "action": action_name,
                    "method": method_upper,
                    "path": full_path,
                    "view_cls": cls,
                    "serializer_cls": serializer_cls,
                    "schema": schema,
                    "unsupported_fields": unsupported,
                    "schema_tokens_est": tokens,
                    "form_only": is_form_only,
                    "keywords": _make_keywords(title, action_name, model_str),
                })
        else:
            # Trường hợp APIView thông thường
            view_name = cls.__name__.lower().replace("view", "")
            for method in ("get", "post", "patch", "delete"):
                if hasattr(cls, method):
                    method_upper = method.upper()
                    action_name = method
                    cmd_id = f"{app_name}.{view_name}.{action_name}"
                    if cmd_id in seen_ids:
                        continue
                    seen_ids.add(cmd_id)

                    kind = "read" if method_upper == "GET" else "write"
                    title = f"{'Xem' if kind == 'read' else 'Thực hiện'} {cls.__name__}"
                    serializer_cls = getattr(cls, "serializer_class", None)
                    schema, unsupported = serializer_to_schema(serializer_cls)
                    if schema is None and kind == "read":
                        schema = {"type": "object", "properties": {}}
                    is_form_only = (kind == "write" and schema is None)
                    tokens = estimate_schema_tokens(schema)

                    commands.append({
                        "id": cmd_id,
                        "title": title,
                        "kind": kind,
                        "group": group,
                        "app": app_name,
                        "model": view_name,
                        "action": action_name,
                        "method": method_upper,
                        "path": full_path,
                        "view_cls": cls,
                        "serializer_cls": serializer_cls,
                        "schema": schema,
                        "unsupported_fields": unsupported,
                        "schema_tokens_est": tokens,
                        "form_only": is_form_only,
                        "keywords": _make_keywords(title, action_name, view_name),
                    })

    return commands


def _collect_routes(patterns, prefix, routes):
    for p in patterns:
        if isinstance(p, URLPattern):
            routes.append((prefix + str(p.pattern), p.callback, p.default_args))
        elif isinstance(p, URLResolver):
            _collect_routes(p.url_patterns, prefix + str(p.pattern), routes)


def _get_serializer_for_action(view_cls, action_name):
    # Kiểm tra input_serializer
    input_serializer = getattr(view_cls, "input_serializer", None)
    if input_serializer:
        return input_serializer

    # Kiểm tra phương thức action có input_serializer không
    action_func = getattr(view_cls, action_name, None)
    if action_func and hasattr(action_func, "input_serializer"):
        return action_func.input_serializer

    # Kiểm tra serializer_class
    if hasattr(view_cls, "get_serializer_class"):
        try:
            view_instance = view_cls()
            view_instance.action = action_name
            return view_instance.get_serializer_class()
        except Exception:
            pass

    return getattr(view_cls, "serializer_class", None)


MODEL_VN_MAP = {
    "batch": ("lô cá", ["lô", "tồn kho", "tra tồn", "lô cá", "cá", "đang bán"]),
    "item": ("mặt hàng cá", ["mặt hàng", "sản phẩm", "hải sản", "cá", "danh mục"]),
    "itemgroup": ("nhóm mặt hàng", ["nhóm", "phân loại", "hải sản", "cá"]),
    "pricelist": ("bảng giá", ["bảng giá", "giá niêm yết", "hiện hành"]),
    "itemprice": ("giá bán mặt hàng", ["giá bán", "đơn giá", "giá"]),
    "pricingrule": ("quy tắc định giá", ["định giá", "quy tắc", "chính sách giá", "thiết lập"]),
    "warehouse": ("kho hàng", ["kho", "kho hàng", "nhà kho", "kho chính"]),
    "stockentry": ("phiếu kho", ["phiếu kho", "nhập xuất kho"]),
    "stockledgerentry": ("sổ kho", ["sổ kho", "nhật ký", "thẻ kho", "lịch sử kho", "nhập xuất"]),
    "stockreconciliation": ("phiếu kiểm kê kho", ["kiểm kê", "kiểm kho", "reconcile"]),
    "returntostock": ("phiếu hàng hoàn", ["hàng hoàn", "trả hàng", "hoàn kho", "trả về kho"]),
    "supplier": ("nhà cung cấp", ["nhà cung cấp", "đầu mối", "ghe thuyền", "cảng", "vựa"]),
    "purchasereceipt": ("phiếu nhập hàng", ["nhập hàng", "mua hàng", "nhập lô", "phiếu nhập", "mua cá"]),
    "purchasecost": ("chi phí mua hàng", ["chi phí", "tiền đá", "bảo quản", "phân bổ"]),
    "salesorder": ("đơn đặt hàng", ["đơn hàng", "đặt hàng", "đơn đặt", "khách"]),
    "salesinvoice": ("hoá đơn bán hàng", ["hoá đơn", "hoá đơn bán", "tiền bán", "bán cá"]),
    "customer": ("khách hàng", ["khách hàng", "người mua", "hồ sơ khách hàng", "khách"]),
    "refund": ("phiếu hoàn tiền", ["hoàn tiền", "trả lại tiền", "yêu cầu hoàn tiền", "refund"]),
    "paymenttransaction": ("giao dịch thanh toán", ["giao dịch", "thanh toán", "chuyển khoản", "ngân hàng", "lệch"]),
    "deliverynote": ("phiếu giao hàng", ["giao hàng", "vận chuyển", "shipper", "chuyến", "giao"]),
    "dashboardsummary": ("bảng điều hành", ["bảng điều hành", "tổng quan", "kpi", "kinh doanh"]),
    "batchpnl": ("báo cáo lãi lỗ lô", ["lãi lỗ theo lô", "lãi lỗ lô", "báo cáo lô"]),
    "periodpnl": ("báo cáo lãi lỗ theo kỳ", ["lãi lỗ theo kỳ", "lãi lỗ tháng", "báo cáo tháng"]),
}

ACTION_VN_MAP = {
    "list": "Xem danh sách",
    "retrieve": "Chi tiết",
    "create": "Tạo mới",
    "partial_update": "Cập nhật",
    "destroy": "Xoá",
    "close": "Chốt",
    "approve": "Duyệt",
    "confirm_payment": "Xác nhận thanh toán",
    "cancel": "Huỷ",
    "confirm": "Xác nhận",
    "resolve": "Xử lý",
    "assign": "Nhận chuyến",
    "complete": "Xác nhận thành công",
    "mark_failed": "Báo cáo thất bại",
    "submit": "Gửi duyệt",
    "get": "Xem",
}


def _make_title(view_cls, action_name, model_str):
    vn_model, _ = MODEL_VN_MAP.get(model_str.lower(), (model_str, []))
    vn_action = ACTION_VN_MAP.get(action_name.lower(), action_name.replace("_", " ").capitalize())
    return f"{vn_action} {vn_model}"


def _make_keywords(title, action_name, model_str):
    kws = set()
    for word in title.lower().split():
        if len(word) > 1:
            kws.add(word)
    kws.add(action_name.replace("_", " "))
    kws.add(model_str)

    if model_str.lower() in MODEL_VN_MAP:
        _, extra_kws = MODEL_VN_MAP[model_str.lower()]
        kws.update(extra_kws)

    return sorted(list(kws))

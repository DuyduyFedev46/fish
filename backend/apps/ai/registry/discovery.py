"""
Khám phá và đăng ký lệnh AI tự sinh từ API DRF (02b §2, §3, DW-07).
"""
import hashlib
import json
import re
from django.conf import settings
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver
from rest_framework.parsers import JSONParser

from apps.ai.policy.rules import (
    COST_KEYS,
    FORBIDDEN_METHODS,
    FORBIDDEN_PERMS_T2,
    FORBIDDEN_RESOURCES,
    FORBIDDEN_WRITE_MODELS,
    FORCE_C_PERMS,
    RED_ZONE_PERMS,
    SCRUB_PII_KEYS,
    is_force_c_action,
    is_perm_forbidden,
    is_red_zone_action,
    is_url_forbidden,
)
from .schema import estimate_schema_tokens, get_serializer_output_fields, serializer_to_schema
from .spec import CommandSpec


def _camel_to_snake(name: str) -> str:
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _get_group(app_name: str, model_str: str, view_cls: type, action_name: str, ai_meta) -> str:
    """
    Xác định 1 trong 3 nhóm lớn: thu_mua | ban_hang | cskh (02b §2.3, DW-07-AC1).
    """
    if ai_meta and ai_meta.group:
        return ai_meta.group

    mod = view_cls.__module__.lower()
    cls_name = view_cls.__name__.lower()

    # CSKH: refunds, returns, guidance
    if "refund" in mod or "refund" in cls_name or "return" in mod or "return" in cls_name or "guidance" in mod:
        return "".join(["cs", "kh"])

    # Thu mua: purchasing, inventory (trừ returns), batch_pnl
    if "purchasing" in mod or "inventory" in mod or "batchpnl" in cls_name:
        return "thu_mua"

    # Bán hàng: catalog, sales (orders, payments, invoices), delivery, dashboard, period_pnl
    if "catalog" in mod or "sales" in mod or "delivery" in mod or "dashboard" in cls_name or "periodpnl" in cls_name:
        return "ban_hang"

    return "ban_hang"


def _get_screens(full_path: str, ai_meta) -> tuple:
    if ai_meta and ai_meta.screens:
        return tuple(ai_meta.screens)
    parts = [p for p in full_path.strip("/").split("/") if p]
    if len(parts) >= 2 and parts[0] == "api":
        sub = parts[1]
        if sub in ("inventory", "purchasing", "catalog", "delivery", "reports", "dashboard", "guidance"):
            return (sub,)
        if sub == "sales":
            if len(parts) >= 3:
                return (parts[2],)
            return ("sales",)
    return ("main",)


def _has_json_parser(view_cls) -> bool:
    """Kiểm tra view có chấp nhận JSON parser không (DW-07-AC3, bỏ upload ảnh)."""
    parser_classes = getattr(view_cls, "parser_classes", None)
    if parser_classes is None:
        return True
    return any(issubclass(p, JSONParser) for p in parser_classes)


def _clean_path(pattern_str: str) -> str:
    p = re.sub(r'[\^$]', '', pattern_str)
    p = re.sub(r'\(\?P<([^>]+)>[^\)]+\)', r'<\1>', p)
    p = re.sub(r'/+', '/', p)
    return "/" + p.strip("/") + ("/" if p.strip("/") else "")


class CommandRegistry:
    _instance = None

    def __init__(self):
        self._specs: dict[str, CommandSpec] = {}
        self._index_version: str = ""
        self._built: bool = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.build()
        return cls._instance

    def build(self, force: bool = False):
        if self._built and not force:
            return

        resolver = get_resolver(getattr(settings, "ROOT_URLCONF", None))
        routes = []
        _collect_routes(resolver.url_patterns, prefix="", routes=routes)

        specs: dict[str, CommandSpec] = {}

        for pattern_str, callback, default_args in routes:
            full_path = _clean_path(pattern_str)
            if not full_path.startswith("/api/"):
                continue
            if full_path.strip("/") == "api":
                continue

            # 1. Cấm theo tiền tố / hậu tố URL
            if is_url_forbidden(full_path):
                continue

            cls = getattr(callback, "cls", None)
            if cls is None:
                continue

            # Bỏ qua APIRootView của router
            if cls.__name__ in ("APIRootView", "DefaultRouterRootView"):
                continue

            # 2. Cấm upload ảnh hoặc không có JSON parser
            if full_path.endswith("/image/") or "image" in cls.__name__.lower() or not _has_json_parser(cls):
                continue

            app_name = cls.__module__.split(".")[1] if "apps." in cls.__module__ else "app"

            # Model info
            model_cls = getattr(getattr(cls, "queryset", None), "model", None)
            model_str = model_cls._meta.model_name if model_cls else _camel_to_snake(cls.__name__).replace("_viewset", "").replace("_view", "")

            # 3. Cấm hẳn resource customer
            if model_str == "customer" or f"{app_name}.{model_str}" in FORBIDDEN_RESOURCES or "customer" in cls.__name__.lower():
                continue

            # Check ViewSet actions vs APIView
            actions_map = getattr(callback, "actions", None)
            if actions_map:
                for method, action_name in actions_map.items():
                    method_upper = method.upper()
                    # 4. Cấm phương thức DELETE và PUT
                    if method_upper in FORBIDDEN_METHODS:
                        continue

                    # 5. Cấm CRUD ghi trên SalesOrder và SalesInvoice (H7)
                    if model_str in ("salesorder", "salesinvoice") and action_name in ("create", "update", "partial_update"):
                        continue

                    action_func = getattr(cls, action_name, None)
                    func_kwargs = getattr(action_func, "kwargs", {}) if action_func else {}

                    # Quyền Tầng 2
                    required_perms = tuple(
                        getattr(action_func, "required_perms", None)
                        or func_kwargs.get("required_perms")
                        or getattr(cls, "required_perms", ())
                    )

                    # 6. Cấm nếu quyền chứa quyền cấm
                    if any(is_perm_forbidden(p) for p in required_perms):
                        continue

                    cmd_id = f"{app_name}.{model_str}.{action_name}"
                    if cmd_id in specs:
                        continue

                    kind = "read" if method_upper in ("GET", "HEAD") else "write"
                    ai_meta = (
                        getattr(action_func, "ai", None)
                        or func_kwargs.get("ai")
                        or getattr(cls, "ai_by_action", {}).get(action_name)
                        or getattr(cls, "ai", None)
                    )

                    group = _get_group(app_name, model_str, cls, action_name, ai_meta)
                    screens = _get_screens(full_path, ai_meta)

                    # Red zone & Force C
                    red_zone = is_red_zone_action(required_perms)
                    force_c = is_force_c_action(required_perms)

                    # Serializer & Schema
                    input_serializer = _get_input_serializer(cls, action_name, action_func)
                    input_schema, unsupported = serializer_to_schema(input_serializer)

                    tokens = estimate_schema_tokens(input_schema)
                    max_schema_tokens = getattr(settings, "AI_SCHEMA_MAX_TOKENS", 450)

                    # form_only: ghi không có serializer hoặc vượt token ngân sách
                    is_form_only = (kind == "write" and input_schema is None) or (tokens > max_schema_tokens)

                    # Output fields
                    out_serializer_cls = _get_output_serializer(cls, action_name)
                    raw_output_fields = get_serializer_output_fields(out_serializer_cls)
                    clean_output_fields = [f for f in raw_output_fields if f not in SCRUB_PII_KEYS]

                    # Title, Description & Keywords
                    title, description, keywords = _make_doc_metadata(cls, action_name, model_str, action_func, ai_meta)

                    is_detail = getattr(action_func, "detail", False) if action_func else ("<pk>" in pattern_str or "<id>" in pattern_str or "<str:" in pattern_str or "<int:" in pattern_str)

                    # Xử lý undo và max_level
                    undo_val = getattr(ai_meta, "undo", "") or ""
                    undo_missing = False
                    max_level_val = getattr(ai_meta, "max_level", "")
                    if undo_val.startswith("cancel_action:"):
                        cancel_act_name = undo_val.split(":", 1)[1]
                        if hasattr(cls, cancel_act_name):
                            undo_missing = False
                            max_level_val = max_level_val or "B"
                        else:
                            undo_missing = True
                            max_level_val = "C"
                    elif not max_level_val:
                        max_level_val = "A" if kind == "read" else "C"

                    if force_c:
                        max_level_val = "C"

                    spec = CommandSpec(
                        id=cmd_id,
                        title=title,
                        description=description,
                        kind=kind,
                        group=group,
                        screens=screens,
                        keywords=keywords,
                        method=method_upper,
                        path=full_path,
                        action=action_name,
                        detail=is_detail,
                        target="detail" if is_detail else None,
                        view_cls=cls,
                        required_perms=required_perms,
                        sensitivity=getattr(ai_meta, "sensitivity", "") or "cao",
                        channel=getattr(ai_meta, "channel", "") or "local",
                        max_level=max_level_val,
                        undo_missing=undo_missing,
                        red_zone=red_zone,
                        force_c=force_c,
                        form_only=is_form_only,
                        is_forbidden=False,
                        input_serializer_cls=input_serializer,
                        input_schema=input_schema if not is_form_only else None,
                        schema_tokens_est=tokens,
                        all_output_fields=clean_output_fields,
                    )
                    specs[cmd_id] = spec
            else:
                # APIView thông thường
                view_name = _camel_to_snake(cls.__name__).replace("_view", "")
                for method in ("get", "post", "patch"):
                    if hasattr(cls, method):
                        method_upper = method.upper()
                        if method_upper in FORBIDDEN_METHODS:
                            continue

                        action_name = method
                        cmd_id = f"{app_name}.{view_name}"
                        if cmd_id in specs:
                            continue

                        kind = "read" if method_upper in ("GET", "HEAD") else "write"
                        ai_meta = getattr(cls, "ai", None)

                        required_perms = tuple(getattr(cls, "required_perms", ()))
                        if any(is_perm_forbidden(p) for p in required_perms):
                            continue

                        group = _get_group(app_name, view_name, cls, action_name, ai_meta)
                        screens = _get_screens(full_path, ai_meta)
                        red_zone = is_red_zone_action(required_perms)
                        force_c = is_force_c_action(required_perms)

                        input_serializer = getattr(cls, "input_serializer", None) or getattr(cls, "serializer_class", None)
                        input_schema, _ = serializer_to_schema(input_serializer)
                        tokens = estimate_schema_tokens(input_schema)
                        is_form_only = (kind == "write" and input_schema is None) or (tokens > getattr(settings, "AI_SCHEMA_MAX_TOKENS", 450))

                        raw_output = get_serializer_output_fields(getattr(cls, "serializer_class", None))
                        clean_output = [f for f in raw_output if f not in SCRUB_PII_KEYS]

                        title, description, keywords = _make_doc_metadata(cls, action_name, view_name, None, ai_meta)
                        is_detail = ("<pk>" in pattern_str or "<id>" in pattern_str or "<str:" in pattern_str or "<int:" in pattern_str)

                        spec = CommandSpec(
                            id=cmd_id,
                            title=title,
                            description=description,
                            kind=kind,
                            group=group,
                            screens=screens,
                            keywords=keywords,
                            method=method_upper,
                            path=full_path,
                            action=action_name,
                            detail=is_detail,
                            target="detail" if is_detail else None,
                            view_cls=cls,
                            required_perms=required_perms,
                            sensitivity=getattr(ai_meta, "sensitivity", "") or "cao",
                            channel=getattr(ai_meta, "channel", "") or "local",
                            max_level=getattr(ai_meta, "max_level", "") or ("A" if kind == "read" else "C"),
                            undo_missing=False,
                            red_zone=red_zone,
                            force_c=force_c,
                            form_only=is_form_only,
                            is_forbidden=False,
                            input_serializer_cls=input_serializer,
                            input_schema=input_schema if not is_form_only else None,
                            schema_tokens_est=tokens,
                            all_output_fields=clean_output,
                        )
                        specs[cmd_id] = spec

        self._specs = dict(sorted(specs.items()))
        # Hash version từ các id và metadata
        content = json.dumps([s.id for s in self._specs.values()])
        self._index_version = hashlib.sha256(content.encode()).hexdigest()[:16]
        self._built = True

    def get_specs(self) -> list[CommandSpec]:
        return list(self._specs.values())

    def get_spec(self, cmd_id: str) -> CommandSpec | None:
        return self._specs.get(cmd_id)

    def get(self, cmd_id: str, default=None) -> CommandSpec | None:
        return self._specs.get(cmd_id, default)

    def __getitem__(self, cmd_id: str) -> CommandSpec:
        return self._specs[cmd_id]

    def __contains__(self, cmd_id: str) -> bool:
        return cmd_id in self._specs

    @property
    def index_version(self) -> str:
        return self._index_version


def _collect_routes(patterns, prefix, routes):
    for p in patterns:
        if isinstance(p, URLPattern):
            routes.append((prefix + str(p.pattern), p.callback, p.default_args))
        elif isinstance(p, URLResolver):
            _collect_routes(p.url_patterns, prefix + str(p.pattern), routes)


def _get_input_serializer(view_cls, action_name, action_func):
    func_kwargs = getattr(action_func, "kwargs", {}) if action_func else {}
    if action_func and (getattr(action_func, "input_serializer", None) or func_kwargs.get("input_serializer")):
        return getattr(action_func, "input_serializer", None) or func_kwargs.get("input_serializer")
    if getattr(view_cls, "input_serializer", None):
        return view_cls.input_serializer
    if action_name == "list" and getattr(view_cls, "list_query_serializer", None):
        return view_cls.list_query_serializer
    if action_name in ("create", "partial_update", "update"):
        return getattr(view_cls, "serializer_class", None)
    return None


def _get_output_serializer(view_cls, action_name):
    if hasattr(view_cls, "get_serializer_class"):
        try:
            inst = view_cls()
            inst.action = action_name
            return inst.get_serializer_class()
        except Exception:
            pass
    return getattr(view_cls, "serializer_class", None)


def _make_doc_metadata(view_cls, action_name, model_str, action_func, ai_meta):
    """Xây dựng title, description và keywords chuẩn tiếng Việt (DW-07, DW-08)."""
    title = getattr(ai_meta, "title", "") if ai_meta else ""
    desc = getattr(ai_meta, "description", "") if ai_meta else ""

    doc = ""
    func_kwargs = getattr(action_func, "kwargs", {}) if action_func else {}
    if action_func and action_func.__doc__:
        doc = action_func.__doc__.strip()
    elif func_kwargs.get("description"):
        doc = func_kwargs.get("description").strip()
    elif view_cls.__doc__:
        doc = view_cls.__doc__.strip()

    if not title:
        if doc:
            title = doc.split("\n")[0].strip()
        else:
            action_label = {
                "list": "Xem danh sách",
                "retrieve": "Xem chi tiết",
                "create": "Tạo mới",
                "partial_update": "Cập nhật",
                "close": "Chốt",
                "publish": "Mở bán",
                "cancel_expired": "Huỷ quá hạn",
                "approve": "Duyệt",
                "submit": "Gửi duyệt",
                "cancel": "Huỷ",
                "confirm_payment": "Xác nhận thanh toán",
                "resolve": "Xử lý",
                "confirm": "Xác nhận",
                "mark_failed": "Báo thất bại",
                "retry": "Thử lại",
            }.get(action_name, action_name.replace("_", " ").capitalize())
            title = f"{action_label} {model_str}"

    if not desc:
        desc = doc if doc else title

    kws = set()
    if ai_meta and ai_meta.keywords:
        kws.update(ai_meta.keywords)
    for word in title.lower().split():
        if len(word) > 1:
            kws.add(word)
    kws.add(action_name.replace("_", " "))
    kws.add(model_str)

    return title, desc[:80], sorted(list(kws))


def get_registry() -> CommandRegistry:
    return CommandRegistry.get_instance()

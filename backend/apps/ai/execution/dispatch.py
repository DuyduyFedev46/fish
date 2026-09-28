"""
Gọi lại view DRF trong tiến trình (02b §4.3).

- Dựng HttpRequest con mang user và token gốc.
- Gọi callback lấy từ spec.view_cls.
- Bắt 4xx trả nguyên {detail, code}; 5xx trả 502 AI_DISPATCH_FAILED (không lộ stack trace).
"""
import logging
from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import status, viewsets
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.common.exceptions import BusinessError
from apps.ai.registry.spec import CommandSpec

logger = logging.getLogger(__name__)


class DispatchResult:
    def __init__(self, data, status_code: int, is_error: bool = False):
        self.data = data
        self.status_code = status_code
        self.is_error = is_error


def dispatch_command(
    spec: CommandSpec,
    *,
    user,
    args: dict | None = None,
    target_id: str | None = None,
    request_origin=None,
) -> DispatchResult:
    """
    Thực thi view tương ứng với CommandSpec trong tiến trình hiện tại.
    """
    args = args or {}
    factory = APIRequestFactory()
    method = spec.method.upper()

    try:
        if method == "GET":
            sub_request = factory.get(spec.path, args, format="json")
        elif method == "POST":
            sub_request = factory.post(spec.path, args, format="json")
        elif method == "PUT":
            sub_request = factory.put(spec.path, args, format="json")
        elif method == "PATCH":
            sub_request = factory.patch(spec.path, args, format="json")
        elif method == "DELETE":
            sub_request = factory.delete(spec.path, args, format="json")
        else:
            sub_request = factory.get(spec.path, args, format="json")

        if request_origin:
            if "HTTP_AUTHORIZATION" in request_origin.META:
                sub_request.META["HTTP_AUTHORIZATION"] = request_origin.META["HTTP_AUTHORIZATION"]
            if "REMOTE_ADDR" in request_origin.META:
                sub_request.META["REMOTE_ADDR"] = request_origin.META["REMOTE_ADDR"]

        force_authenticate(sub_request, user=user)

        view_cls = spec.view_cls
        if not view_cls:
            return DispatchResult(
                {"detail": "Lệnh chưa có view handler.", "code": "AI_DISPATCH_FAILED"},
                status_code=502,
                is_error=True,
            )

        kwargs = {}
        if spec.detail and target_id is not None:
            lookup_field = getattr(view_cls, "lookup_url_kwarg", None) or getattr(
                view_cls, "lookup_field", "pk"
            )
            kwargs[lookup_field] = target_id

        if issubclass(view_cls, viewsets.ViewSetMixin):
            action_map = {method.lower(): spec.action}
            view_func = view_cls.as_view(action_map)
        else:
            view_func = view_cls.as_view()

        response = view_func(sub_request, **kwargs)

        if hasattr(response, "render"):
            response.render()

        status_code = getattr(response, "status_code", 200)
        data = getattr(response, "data", None)

        if 400 <= status_code < 500:
            return DispatchResult(data, status_code=status_code, is_error=True)
        elif status_code >= 500:
            logger.error("View returned 5xx status %d: %s", status_code, data)
            return DispatchResult(
                {"detail": "Thao tác nội bộ thất bại.", "code": "AI_DISPATCH_FAILED"},
                status_code=502,
                is_error=True,
            )

        return DispatchResult(data, status_code=status_code, is_error=False)

    except (BusinessError, APIException) as exc:
        data = getattr(exc, "detail", str(exc))
        status_code = getattr(exc, "status_code", 400)
        code = getattr(exc, "code", "BUSINESS_ERROR")
        if isinstance(data, dict):
            error_data = data
        else:
            error_data = {"detail": str(data), "code": code}
        return DispatchResult(error_data, status_code=status_code, is_error=True)

    except Http404:
        return DispatchResult(
            {"detail": "Không tìm thấy đối tượng.", "code": "NOT_FOUND"},
            status_code=404,
            is_error=True,
        )

    except PermissionDenied:
        return DispatchResult(
            {"detail": "Không có quyền thực hiện.", "code": "PERMISSION_DENIED"},
            status_code=403,
            is_error=True,
        )

    except Exception as exc:
        logger.exception("AI Dispatch Exception: %s", exc)
        return DispatchResult(
            {"detail": "Thao tác nội bộ thất bại.", "code": "AI_DISPATCH_FAILED"},
            status_code=502,
            is_error=True,
        )

"""
Lớp gọi lại View trong tiến trình (In-process dispatch, Spike DW-01, 02b §4.3).
"""
from rest_framework.test import APIRequestFactory, force_authenticate


def dispatch_in_process(view_cls, action_name, method, user, data=None, query_params=None, url_kwargs=None):
    """
    Gọi trực tiếp view DRF trong tiến trình Python với danh tính user thật.
    Trả về Response DRF.
    """
    factory = APIRequestFactory()
    url = "/fake-internal-url/"
    if query_params:
        from urllib.parse import urlencode
        url += "?" + urlencode(query_params)

    method_lower = method.lower()
    if method_lower == "get":
        request = factory.get(url)
    elif method_lower == "post":
        request = factory.post(url, data=data, format="json")
    elif method_lower == "patch":
        request = factory.patch(url, data=data, format="json")
    elif method_lower == "delete":
        request = factory.delete(url)
    else:
        raise ValueError(f"Method {method} không được hỗ trợ trong dispatch.")

    if user is not None:
        force_authenticate(request, user=user)
        request.user = user

    url_kwargs = url_kwargs or {}

    # Nếu view là ViewSet
    if hasattr(view_cls, "action_map"):
        view_func = view_cls.as_view({method_lower: action_name})
    elif hasattr(view_cls, "as_view"):
        try:
            view_func = view_cls.as_view({method_lower: action_name})
        except TypeError:
            view_func = view_cls.as_view()
    else:
        raise ValueError("view_cls không phải là DRF View hợp lệ.")

    response = view_func(request, **url_kwargs)
    if hasattr(response, "render"):
        response.render()

    return response

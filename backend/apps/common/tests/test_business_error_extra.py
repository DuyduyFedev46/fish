"""Test BusinessError.extra và exception_handler (§8.1 02b-tech-design)."""
from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.response import Response

from apps.common.api import exception_handler
from apps.common.exceptions import BusinessError


class BusinessErrorExtraTests(SimpleTestCase):
    def test_business_error_extra_merged(self):
        exc = BusinessError("Lỗi danh mục còn bài", code="BR-ND-02", extra={"total": 7, "entries": [{"id": 1}]})
        response = exception_handler(exc, {})
        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Lỗi danh mục còn bài")
        self.assertEqual(response.data["code"], "BR-ND-02")
        self.assertEqual(response.data["total"], 7)
        self.assertEqual(response.data["entries"], [{"id": 1}])

    def test_detail_and_code_win_over_extra_keys(self):
        """detail và code luôn thắng khoá trùng trong extra (§8.1)."""
        exc = BusinessError(
            "Thông điệp chính",
            code="BR-ND-04",
            extra={"detail": "detail giả", "code": "CODE_GIA", "suggestion": "mon-ngon-2"},
        )
        response = exception_handler(exc, {})
        self.assertIsInstance(response, Response)
        self.assertEqual(response.data["detail"], "Thông điệp chính")
        self.assertEqual(response.data["code"], "BR-ND-04")
        self.assertEqual(response.data["suggestion"], "mon-ngon-2")

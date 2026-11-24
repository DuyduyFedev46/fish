"""
Kiểm thử tìm địa chỉ qua máy chủ Cá Về bằng VietMap (SHOP-3-04 AC3, AC3b, AC3c, AC5, AC8; 02b §1.9b; bất biến 9).

Mọi test mock `urllib.request.urlopen`, không gọi mạng thật. Dữ liệu trong test hoàn toàn là giả.
"""
import io
import json
import logging
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from apps.common.address_search.matching import match_administrative_unit
from apps.common.tests.throttle_defaults import default_throttle_rates

SEARCH_URL = "/api/shop/address-search/"
PLACE_URL = "/api/shop/address-place/"
FAKE_API_KEY = "vietmap-test-key-0000"
FAKE_TYPED_TEXT = "12 Đường Giả"
FAKE_REF = "auto:RefGia123_Abc-Xyz+/=.:"
UNAVAILABLE_BODY = {
    "code": "ADDRESS_SEARCH_UNAVAILABLE",
    "detail": "Chưa tìm được địa chỉ lúc này. Bạn gõ địa chỉ trực tiếp nhé.",
}
FORBIDDEN_RESPONSE_KEYS = frozenset({
    "lat",
    "lng",
    "ref_id",
    "ward_id",
    "city_id",
    "district_id",
    "boundaries",
    "distance",
    "entry_points",
    "data_old",
    "data_new",
})


class _FakeHttpResponse:
    def __init__(self, body: bytes, status: int = 200):
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _json_response(payload) -> _FakeHttpResponse:
    return _FakeHttpResponse(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def _collect_keys(value) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            found.add(str(key))
            found |= _collect_keys(child)
    elif isinstance(value, list):
        for item in value:
            found |= _collect_keys(item)
    return found


class MatchingUnitTests(SimpleTestCase):
    """02b §1.9b.4: so tên tỉnh/[huyện]/xã với danh mục tĩnh qua fold_text."""

    def test_shop_3_04_ac3_matches_current_ward_22945(self):
        result = match_administrative_unit(
            scheme="current",
            city="Tỉnh Lâm Đồng",
            district="",
            ward="Phường Phan Thiết",
        )
        self.assertEqual(
            result,
            {
                "scheme": "current",
                "province_code": "68",
                "district_code": None,
                "ward_code": "22945",
                "ward_name": "Phường Phan Thiết",
            },
        )

    def test_shop_3_04_ac3c_matches_legacy_three_levels_case_insensitive(self):
        result = match_administrative_unit(
            scheme="legacy",
            city="Tỉnh Bình Thuận",
            district="Thành Phố Phan Thiết",
            ward="Phường Mũi Né",
        )
        self.assertEqual(
            result,
            {
                "scheme": "legacy",
                "province_code": "60",
                "district_code": "593",
                "ward_code": "22915",
                "ward_name": "Phường Mũi Né",
            },
        )

    def test_shop_3_04_ac3b_returns_none_when_not_matched(self):
        self.assertIsNone(
            match_administrative_unit(
                scheme="current",
                city="Tỉnh Không Có",
                district="",
                ward="Phường Phan Thiết",
            )
        )
        self.assertIsNone(
            match_administrative_unit(
                scheme="current",
                city="Tỉnh Lâm Đồng",
                district="",
                ward="Phường Không Có Trong Danh Mục",
            )
        )
        self.assertIsNone(
            match_administrative_unit(
                scheme="legacy",
                city="Tỉnh Bình Thuận",
                district="Huyện Không Có",
                ward="Phường Mũi Né",
            )
        )

    def test_shop_3_04_ac3b_returns_none_when_two_wards_match_folded_name(self):
        # Tỉnh Đồng Nai (current=75) có cả "Xã Lộc Thành" và "Xã Lộc Thạnh" -> trùng tên sau fold_text -> trả None.
        self.assertIsNone(
            match_administrative_unit(
                scheme="current",
                city="Tỉnh Đồng Nai",
                district="",
                ward="Xã Lộc Thành",
            )
        )


@override_settings(VIETMAP_API_KEY=FAKE_API_KEY, VIETMAP_TIMEOUT_SECONDS=4)
class AddressSearchApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def tearDown(self):
        cache.clear()

    def _sample_autocomplete_upstream(self, count: int = 8) -> list[dict]:
        rows = []
        for idx in range(1, count + 1):
            rows.append({
                "ref_id": f"auto:Item{idx}",
                "distance": 1.25,
                "address": f"Phường Phan Thiết, Tỉnh Lâm Đồng ({idx})",
                "name": f"{idx} Đường Giả",
                "display": f"{idx} Đường Giả, Phường Phan Thiết, Tỉnh Lâm Đồng",
                "boundaries": [{"type": 2, "id": 18700, "name": "Phan Thiết", "prefix": "Phường"}],
                "categories": ["address"],
                "entry_points": [{"ref_id": "ep:1", "lat": 10.93, "lng": 108.10}],
                "data_old": {"ward": "Phường Phú Thủy"},
                "data_new": {"ward": "Phường Phan Thiết"},
                "lat": 10.9289,
                "lng": 108.1021,
            })
        return rows

    def _sample_place_upstream(self, **overrides) -> dict:
        payload = {
            "display": "12 Đường Trần Hưng Đạo, Phường Phan Thiết, Tỉnh Lâm Đồng",
            "name": "12 Đường Trần Hưng Đạo",
            "hs_num": "12",
            "street": "Đường Trần Hưng Đạo",
            "address": "12 Đường Trần Hưng Đạo",
            "city_id": 68,
            "city": "Tỉnh Lâm Đồng",
            "district_id": 0,
            "district": "",
            "ward_id": 18700,
            "ward": "Phường Phan Thiết",
            "lat": 10.9289,
            "lng": 108.1021,
        }
        payload.update(overrides)
        return payload

    @patch("urllib.request.urlopen")
    def test_shop_3_04_ac3_ac8_autocomplete_200_caps_6_and_strips_forbidden_keys(self, mock_urlopen):
        mock_urlopen.return_value = _json_response(self._sample_autocomplete_upstream(count=8))

        resp = self.client.post(
            SEARCH_URL,
            {"scheme": "current", "text": "  12   Đường Giả  "},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(set(body.keys()), {"results"})
        self.assertEqual(len(body["results"]), 6)
        self.assertEqual(
            body["results"][0],
            {
                "ref": "auto:Item1",
                "title": "1 Đường Giả",
                "subtitle": "Phường Phan Thiết, Tỉnh Lâm Đồng (1)",
            },
        )
        self.assertEqual(_collect_keys(body) & FORBIDDEN_RESPONSE_KEYS, set())
        self.assertEqual(resp.headers.get("Cache-Control"), "no-store")

        mock_urlopen.assert_called_once()
        req_obj = mock_urlopen.call_args.args[0]
        timeout_arg = mock_urlopen.call_args.kwargs.get("timeout")
        self.assertEqual(timeout_arg, 4)
        self.assertEqual(req_obj.get_header("Accept"), "application/json")
        parsed = urlparse(req_obj.full_url)
        self.assertEqual(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", "https://maps.vietmap.vn/api/autocomplete/v4")
        qs = parse_qs(parsed.query)
        self.assertEqual(qs["apikey"], [FAKE_API_KEY])
        self.assertEqual(qs["text"], ["12 Đường Giả"])
        self.assertEqual(qs["display_type"], ["1"])
        self.assertEqual(qs["focus"], ["10.9289,108.1021"])

    @patch("urllib.request.urlopen")
    def test_shop_3_04_ac3c_autocomplete_legacy_sends_display_type_2_and_empty_results(self, mock_urlopen):
        mock_urlopen.return_value = _json_response([])

        resp = self.client.post(SEARCH_URL, {"scheme": "legacy", "text": "12 Đường Giả"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"results": []})

        parsed = urlparse(mock_urlopen.call_args.args[0].full_url)
        qs = parse_qs(parsed.query)
        self.assertEqual(qs["display_type"], ["2"])
        self.assertEqual(qs["focus"], ["10.9289,108.1021"])

    @patch("urllib.request.urlopen")
    def test_shop_3_04_ac3_ac8_place_200_current_matches_22945_and_strips_coordinates(self, mock_urlopen):
        mock_urlopen.return_value = _json_response(self._sample_place_upstream())

        resp = self.client.post(PLACE_URL, {"scheme": "current", "ref": FAKE_REF}, format="json")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(
            body,
            {
                "street": "12 Đường Trần Hưng Đạo",
                "display": "12 Đường Trần Hưng Đạo, Phường Phan Thiết, Tỉnh Lâm Đồng",
                "suggestion": {
                    "scheme": "current",
                    "province_code": "68",
                    "district_code": None,
                    "ward_code": "22945",
                    "ward_name": "Phường Phan Thiết",
                },
            },
        )
        self.assertEqual(_collect_keys(body) & (FORBIDDEN_RESPONSE_KEYS | {"ref", "refid"}), set())
        self.assertNotIn("10.9289", resp.content.decode("utf-8"))
        self.assertNotIn("108.1021", resp.content.decode("utf-8"))
        self.assertNotIn(FAKE_REF, resp.content.decode("utf-8"))
        self.assertEqual(resp.headers.get("Cache-Control"), "no-store")

        parsed = urlparse(mock_urlopen.call_args.args[0].full_url)
        self.assertEqual(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", "https://maps.vietmap.vn/api/place/v4")
        qs = parse_qs(parsed.query)
        self.assertEqual(qs["apikey"], [FAKE_API_KEY])
        self.assertEqual(qs["refid"], [FAKE_REF])

    @patch("urllib.request.urlopen")
    def test_shop_3_04_ac3c_place_legacy_matches_60_593_22915(self, mock_urlopen):
        mock_urlopen.return_value = _json_response(
            self._sample_place_upstream(
                name="Chợ Mũi Né",
                address="35 Đường Huỳnh Thúc Kháng",
                display="Chợ Mũi Né, 35 Đường Huỳnh Thúc Kháng, Phường Mũi Né, Thành phố Phan Thiết, Tỉnh Bình Thuận",
                city="Tỉnh Bình Thuận",
                district="Thành phố Phan Thiết",
                ward="Phường Mũi Né",
            )
        )

        resp = self.client.post(PLACE_URL, {"scheme": "legacy", "ref": "geocode:MuiNe01"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {
                "street": "Chợ Mũi Né, 35 Đường Huỳnh Thúc Kháng",
                "display": "Chợ Mũi Né, 35 Đường Huỳnh Thúc Kháng, Phường Mũi Né, Thành phố Phan Thiết, Tỉnh Bình Thuận",
                "suggestion": {
                    "scheme": "legacy",
                    "province_code": "60",
                    "district_code": "593",
                    "ward_code": "22915",
                    "ward_name": "Phường Mũi Né",
                },
            },
        )

    @patch("urllib.request.urlopen")
    def test_shop_3_04_ac3_place_street_fallbacks_and_max_200_truncation(self, mock_urlopen):
        # address rỗng -> ghép hs_num + street
        mock_urlopen.return_value = _json_response(
            self._sample_place_upstream(name="", address="", hs_num="197", street="  Đường  Trần Phú ")
        )
        resp1 = self.client.post(PLACE_URL, {"scheme": "current", "ref": "auto:Case1"}, format="json")
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp1.json()["street"], "197 Đường Trần Phú")

        # address và hs_num/street đều rỗng -> lấy name; cắt tối đa 200 ký tự
        long_name = "Điểm Giả " + ("A" * 220)
        mock_urlopen.return_value = _json_response(
            self._sample_place_upstream(name=long_name, address="", hs_num="", street="", ward="Phường Lạ")
        )
        resp2 = self.client.post(PLACE_URL, {"scheme": "current", "ref": "auto:Case2"}, format="json")
        self.assertEqual(resp2.status_code, 200)
        body2 = resp2.json()
        self.assertEqual(len(body2["street"]), 200)
        self.assertIsNone(body2["suggestion"])

    @patch("urllib.request.urlopen")
    def test_shop_3_04_ac3b_place_ambiguous_or_unmatched_ward_returns_null_suggestion(self, mock_urlopen):
        mock_urlopen.return_value = _json_response(
            self._sample_place_upstream(city="Tỉnh Đồng Nai", ward="Xã Lộc Thành")
        )
        resp = self.client.post(PLACE_URL, {"scheme": "current", "ref": "auto:Ambiguous1"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json()["suggestion"])

    @patch("urllib.request.urlopen")
    def test_shop_3_04_ac5_ac8_upstream_errors_return_503_and_never_log_pii_or_key(self, mock_urlopen):
        upstream_failures = [
            ("401", HTTPError("https://maps.vietmap.vn/api/x?apikey=" + FAKE_API_KEY, 401, "Unauthorized", {}, io.BytesIO(b""))),
            ("423", HTTPError("https://maps.vietmap.vn/api/x?apikey=" + FAKE_API_KEY, 423, "Locked", {}, io.BytesIO(b"quota"))),
            ("429", HTTPError("https://maps.vietmap.vn/api/x?apikey=" + FAKE_API_KEY, 429, "Too Many", {}, io.BytesIO(b""))),
            ("500", HTTPError("https://maps.vietmap.vn/api/x?apikey=" + FAKE_API_KEY, 500, "Error", {}, io.BytesIO(b""))),
            ("timeout", TimeoutError("timed out")),
            ("timeout_url", URLError(TimeoutError("socket timed out"))),
            ("network", URLError("connection refused")),
            ("bad_json", _FakeHttpResponse(b"{not-valid-json")),
            ("wrong_shape", _FakeHttpResponse(b'"unexpected-string"')),
        ]

        endpoints = [
            (SEARCH_URL, {"scheme": "current", "text": FAKE_TYPED_TEXT}, "autocomplete"),
            (PLACE_URL, {"scheme": "current", "ref": FAKE_REF}, "place"),
        ]

        for label, side_effect in upstream_failures:
            for url, payload, api_label in endpoints:
                with self.subTest(failure=label, endpoint=api_label):
                    if isinstance(side_effect, Exception):
                        mock_urlopen.side_effect = side_effect
                    else:
                        mock_urlopen.side_effect = None
                        mock_urlopen.return_value = side_effect

                    captured: list[str] = []

                    class _CaptureHandler(logging.Handler):
                        def emit(self, record):
                            captured.append(record.getMessage() + " " + str(record.args))

                    root_logger = logging.getLogger()
                    handler = _CaptureHandler(level=logging.DEBUG)
                    old_level = root_logger.level
                    root_logger.addHandler(handler)
                    root_logger.setLevel(logging.DEBUG)
                    try:
                        with self.assertLogs("apps.common.address_search", level="WARNING") as cm:
                            resp = self.client.post(url, payload, format="json")
                    finally:
                        root_logger.removeHandler(handler)
                        root_logger.setLevel(old_level)

                    self.assertEqual(resp.status_code, 503)
                    self.assertEqual(resp.json(), UNAVAILABLE_BODY)
                    self.assertTrue(
                        any(f"vietmap upstream failed" in line and f"api={api_label}" in line for line in cm.output),
                        cm.output,
                    )
                    combined_logs = "\n".join(cm.output + captured)
                    for secret in (FAKE_TYPED_TEXT, FAKE_REF, FAKE_API_KEY, "maps.vietmap.vn"):
                        self.assertNotIn(secret, combined_logs)

    @patch("urllib.request.urlopen")
    def test_shop_3_04_ac8_success_logs_never_contain_typed_text_ref_or_key(self, mock_urlopen):
        captured: list[str] = []

        class _CaptureHandler(logging.Handler):
            def emit(self, record):
                captured.append(record.getMessage() + " " + str(record.args))

        root_logger = logging.getLogger()
        handler = _CaptureHandler(level=logging.DEBUG)
        old_level = root_logger.level
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.DEBUG)
        try:
            mock_urlopen.return_value = _json_response(self._sample_autocomplete_upstream(count=1))
            resp1 = self.client.post(SEARCH_URL, {"scheme": "current", "text": FAKE_TYPED_TEXT}, format="json")
            mock_urlopen.return_value = _json_response(self._sample_place_upstream())
            resp2 = self.client.post(PLACE_URL, {"scheme": "current", "ref": FAKE_REF}, format="json")
        finally:
            root_logger.removeHandler(handler)
            root_logger.setLevel(old_level)

        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 200)
        combined_logs = "\n".join(captured)
        for secret in (FAKE_TYPED_TEXT, FAKE_REF, FAKE_API_KEY, "maps.vietmap.vn"):
            self.assertNotIn(secret, combined_logs)

    @patch("urllib.request.urlopen")
    def test_shop_3_04_ac8_missing_api_key_returns_503_without_calling_vietmap(self, mock_urlopen):
        for blank_key in ("", "   "):
            with self.subTest(key=blank_key), override_settings(VIETMAP_API_KEY=blank_key):
                resp1 = self.client.post(SEARCH_URL, {"scheme": "current", "text": FAKE_TYPED_TEXT}, format="json")
                resp2 = self.client.post(PLACE_URL, {"scheme": "current", "ref": FAKE_REF}, format="json")
                self.assertEqual(resp1.status_code, 503)
                self.assertEqual(resp1.json(), UNAVAILABLE_BODY)
                self.assertEqual(resp2.status_code, 503)
                self.assertEqual(resp2.json(), UNAVAILABLE_BODY)
        mock_urlopen.assert_not_called()

    @patch("urllib.request.urlopen")
    def test_shop_3_04_validation_errors_400_without_calling_vietmap(self, mock_urlopen):
        search_bad_cases = [
            ({"scheme": "new", "text": "12 Đường Giả"}, "scheme"),
            ({"text": "12 Đường Giả"}, "scheme"),
            ({"scheme": 123, "text": "12 Đường Giả"}, "scheme"),
            ({"scheme": "current", "text": "a"}, "text"),
            ({"scheme": "current", "text": "   a   "}, "text"),
            ({"scheme": "current", "text": ""}, "text"),
            ({"scheme": "current", "text": "a" * 121}, "text"),
            ({"scheme": "current", "text": 12345}, "text"),
        ]
        for payload, field in search_bad_cases:
            with self.subTest(endpoint="search", payload=payload):
                resp = self.client.post(SEARCH_URL, payload, format="json")
                self.assertEqual(resp.status_code, 400)
                body = resp.json()
                self.assertEqual(body["code"], "VALIDATION")
                self.assertIn(field, body["fields"])

        place_bad_cases = [
            ({"scheme": "invalid", "ref": FAKE_REF}, "scheme"),
            ({"ref": FAKE_REF}, "scheme"),
            ({"scheme": "current", "ref": "http://169.254.169.254/latest/meta-data"}, "ref"),
            ({"scheme": "current", "ref": "https://maps.vietmap.vn/api/place/v4"}, "ref"),
            ({"scheme": "current", "ref": "auto:abc\n"}, "ref"),
            ({"scheme": "current", "ref": "auto:ab\nc"}, "ref"),
            ({"scheme": "current", "ref": "auto:abc\r\n"}, "ref"),
            ({"scheme": "current", "ref": "auto:"}, "ref"),
            ({"scheme": "current", "ref": "auto:" + ("x" * 501)}, "ref"),
            ({"scheme": "current", "ref": ""}, "ref"),
            ({"scheme": "current", "ref": 999}, "ref"),
        ]
        for payload, field in place_bad_cases:
            with self.subTest(endpoint="place", payload=payload):
                resp = self.client.post(PLACE_URL, payload, format="json")
                self.assertEqual(resp.status_code, 400)
                body = resp.json()
                self.assertEqual(body["code"], "VALIDATION")
                self.assertIn(field, body["fields"])

        mock_urlopen.assert_not_called()

        # Biên hợp lệ: 2 ký tự và 120 ký tự
        mock_urlopen.return_value = _json_response([])
        self.assertEqual(self.client.post(SEARCH_URL, {"scheme": "current", "text": "12"}, format="json").status_code, 200)
        mock_urlopen.return_value = _json_response([])
        self.assertEqual(
            self.client.post(SEARCH_URL, {"scheme": "current", "text": "a" * 120}, format="json").status_code,
            200,
        )

    @patch("urllib.request.urlopen")
    def test_shop_3_04_ac8_disallowed_methods_return_405(self, mock_urlopen):
        for url in (SEARCH_URL, PLACE_URL):
            for method_name in ("get", "put", "patch", "delete"):
                with self.subTest(url=url, method=method_name):
                    resp = getattr(self.client, method_name)(url)
                    self.assertEqual(resp.status_code, 405)
        mock_urlopen.assert_not_called()

    @patch("urllib.request.urlopen")
    def test_shop_3_04_ac5b_throttle_60_per_minute_default_and_429_per_ip(self, mock_urlopen):
        self.assertEqual(default_throttle_rates().get("shop_address_search"), "60/min")

        with override_settings(CAVEVE_THROTTLE_RATES={"shop_address_search": "2/min"}):
            mock_urlopen.return_value = _json_response([])
            r1 = self.client.post(SEARCH_URL, {"scheme": "current", "text": "12 Đường"}, format="json", REMOTE_ADDR="10.9.0.1")
            mock_urlopen.return_value = _json_response(self._sample_place_upstream())
            r2 = self.client.post(PLACE_URL, {"scheme": "current", "ref": FAKE_REF}, format="json", REMOTE_ADDR="10.9.0.1")
            r3 = self.client.post(SEARCH_URL, {"scheme": "current", "text": "12 Đường"}, format="json", REMOTE_ADDR="10.9.0.1")
            mock_urlopen.return_value = _json_response([])
            r_other_ip = self.client.post(
                SEARCH_URL, {"scheme": "current", "text": "12 Đường"}, format="json", REMOTE_ADDR="10.9.0.2"
            )

        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r3.status_code, 429)
        self.assertEqual(r3.json()["code"], "throttled")
        self.assertEqual(r_other_ip.status_code, 200)
        self.assertEqual(mock_urlopen.call_count, 3)

    @patch("urllib.request.urlopen")
    def test_shop_3_04_malformed_json_body_returns_400_and_ai_policy_forbids_routes(self, mock_urlopen):
        from apps.ai.policy.rules import SCRUB_PII_KEYS, is_url_forbidden

        self.assertIn("text", SCRUB_PII_KEYS)
        self.assertTrue(is_url_forbidden(SEARCH_URL))
        self.assertTrue(is_url_forbidden(PLACE_URL))

        for url in (SEARCH_URL, PLACE_URL):
            resp = self.client.generic("POST", url, "{broken-json", content_type="application/json")
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(resp.json()["code"], "VALIDATION")
        mock_urlopen.assert_not_called()

    @patch("urllib.request.urlopen")
    def test_shop_3_04_ac8_does_not_forward_client_headers_or_ip_to_vietmap(self, mock_urlopen):
        """05-phap-ly §1.2c-A: VietMap không nhận IP hay header trình duyệt của khách."""
        client_sentinels = {
            "REMOTE_ADDR": "203.0.113.77",
            "HTTP_X_FORWARDED_FOR": "198.51.100.42, 203.0.113.77",
            "HTTP_X_REAL_IP": "198.51.100.42",
            "HTTP_USER_AGENT": "FakeBrowser/99.0 (KhachGiaTest)",
            "HTTP_REFERER": "https://shop-gia.example/shop/checkout/?ref=khach-gia",
            "HTTP_COOKIE": "sessionid=cookie-bi-mat-khach-gia",
            "HTTP_ACCEPT_LANGUAGE": "vi-VN,en-US;q=0.8,fr-CA;q=0.5",
        }
        forbidden_values = (
            "203.0.113.77",
            "198.51.100.42",
            "FakeBrowser/99.0",
            "KhachGiaTest",
            "shop-gia.example",
            "cookie-bi-mat-khach-gia",
            "fr-CA",
        )

        cases = [
            (SEARCH_URL, {"scheme": "current", "text": "12 Đường Giả"}, self._sample_autocomplete_upstream(count=1)),
            (PLACE_URL, {"scheme": "current", "ref": FAKE_REF}, self._sample_place_upstream()),
        ]
        for url, payload, upstream_body in cases:
            with self.subTest(url=url):
                mock_urlopen.reset_mock()
                mock_urlopen.return_value = _json_response(upstream_body)
                resp = self.client.post(url, payload, format="json", **client_sentinels)
                self.assertEqual(resp.status_code, 200)

                mock_urlopen.assert_called_once()
                req_obj = mock_urlopen.call_args.args[0]
                header_dump = json.dumps(dict(req_obj.header_items()), ensure_ascii=False)
                self.assertEqual(dict(req_obj.header_items()), {"Accept": "application/json"})
                for val in forbidden_values:
                    self.assertNotIn(val, header_dump)
                    self.assertNotIn(val, req_obj.full_url)
                for forbidden_header in ("X-forwarded-for", "X-real-ip", "User-agent", "Referer", "Cookie", "Accept-language"):
                    self.assertFalse(req_obj.has_header(forbidden_header), forbidden_header)



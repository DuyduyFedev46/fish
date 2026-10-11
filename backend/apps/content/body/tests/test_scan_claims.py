"""
Cảnh báo cụm khẳng định cấm khi đăng hoặc gửi duyệt (02b §3.7.5; SHOP-5-03 AC3; BR-ND-21, BR-BH-30).

Cảnh báo, không chặn: người đăng xác nhận "Đã kiểm tra, vẫn đăng" thì vẫn đăng được (luồng CONTENT_WARNINGS sẵn có).
So khớp không phân biệt hoa thường nhưng GIỮ dấu, để "cần dùng" không bị nhận nhầm là "Cân đúng".
"""
from types import SimpleNamespace

from django.test import SimpleTestCase, override_settings

from apps.content.body.scan import DEFAULT_BLOCKED_CLAIMS, get_blocked_claims, scan_entry_warnings


def _entry(*, title="Tiêu đề", excerpt="", body_blocks=None, seo_title="", seo_description=""):
    return SimpleNamespace(
        title=title,
        excerpt=excerpt,
        seo_title=seo_title,
        seo_description=seo_description,
        cover_image=None,
        body={"type": "doc", "blocks": body_blocks or []},
    )


def _paragraph(text):
    return {"type": "paragraph", "children": [{"text": text}]}


def _claims(warnings):
    return [w for w in warnings if w["type"] == "claim"]


class BlockedClaimScanTests(SimpleTestCase):
    def test_default_list_covers_marketing_traps(self):
        """Danh sách mặc định có đủ các bẫy của 06-marketing A và 02b §3.7.5."""
        lowered = {c.lower() for c in DEFAULT_BLOCKED_CLAIMS}
        for phrase in (
            "tươi sống", "đánh bắt sáng nay", "miễn phí giao", "giao trong ngày",
            "về cảng mỗi ngày", "cân đúng", "hút chân không", "cấp đông ngay tại cảng",
        ):
            self.assertIn(phrase, lowered)

    def test_claim_in_body_paragraph_is_warned_with_phrase_and_field(self):
        warnings = scan_entry_warnings(_entry(body_blocks=[_paragraph("Cá tươi sống về mỗi sáng, ăn là mê.")]))
        claims = _claims(warnings)
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0]["claim"], "tươi sống")
        self.assertEqual(claims[0]["field"], "body")
        self.assertIn("tươi sống", claims[0]["snippet"])

    def test_case_insensitive_in_title_excerpt_heading_and_list(self):
        warnings = scan_entry_warnings(
            _entry(
                title="MIỄN PHÍ GIAO toàn thành phố",
                excerpt="Giao Trong Ngày cho đơn sáng",
                body_blocks=[
                    {"type": "heading", "level": 2, "text": "Đánh bắt sáng nay"},
                    {"type": "list", "ordered": False, "items": [[{"text": "Cân đúng", "marks": ["bold"]}, {"text": " từng lạng"}]]},
                ],
            )
        )
        found = {(w["field"], w["claim"]) for w in _claims(warnings)}
        self.assertIn(("title", "miễn phí giao"), found)
        self.assertIn(("excerpt", "giao trong ngày"), found)
        self.assertIn(("body", "đánh bắt sáng nay"), found)
        self.assertIn(("body", "cân đúng"), found)

    def test_words_without_marks_do_not_match(self):
        """"cần dùng" (khác dấu) không phải "Cân đúng"; "hàng cấp đông" không phải claim."""
        warnings = scan_entry_warnings(
            _entry(body_blocks=[_paragraph("Bạn cần dùng ngăn mát để rã đông hàng cấp đông.")])
        )
        self.assertEqual(_claims(warnings), [])

    def test_nfd_input_is_normalized(self):
        """Chữ gõ trên máy Mac (dạng NFD) vẫn bị nhận ra."""
        import unicodedata

        text = unicodedata.normalize("NFD", "Hàng tươi sống")
        self.assertEqual(len(_claims(scan_entry_warnings(_entry(body_blocks=[_paragraph(text)])))), 1)

    def test_overlapping_phrase_warned_once(self):
        """"miễn phí giao" chứa "phí giao": chỉ một cảnh báo cho cùng một chỗ."""
        claims = _claims(scan_entry_warnings(_entry(body_blocks=[_paragraph("Đơn nào cũng miễn phí giao.")])))
        self.assertEqual([c["claim"] for c in claims], ["miễn phí giao"])

    def test_snippet_masks_phone_numbers(self):
        """Bất biến 9: snippet không lộ số điện thoại."""
        claims = _claims(
            scan_entry_warnings(_entry(body_blocks=[_paragraph("Gọi 0912345678 để có hàng tươi sống.")]))
        )
        self.assertEqual(len(claims), 1)
        self.assertNotIn("0912345678", claims[0]["snippet"])

    @override_settings(CONTENT_BLOCKED_CLAIMS=("khuyến mãi khủng",))
    def test_setting_overrides_default_list(self):
        self.assertEqual(get_blocked_claims(), ["khuyến mãi khủng"])
        warnings = scan_entry_warnings(_entry(body_blocks=[_paragraph("Hàng tươi sống, khuyến mãi khủng.")]))
        self.assertEqual([c["claim"] for c in _claims(warnings)], ["khuyến mãi khủng"])

    @override_settings(CONTENT_BLOCKED_CLAIMS="tươi sống, luôn có hàng")
    def test_setting_accepts_comma_string(self):
        self.assertEqual(get_blocked_claims(), ["tươi sống", "luôn có hàng"])

    def test_clean_entry_has_no_claim_warning(self):
        warnings = scan_entry_warnings(
            _entry(
                title="Rã đông cá đúng cách",
                excerpt="Đã gồm giao hàng. Bạn trả một lần, không trả thêm khi nhận hàng.",
                body_blocks=[_paragraph("Hải sản cấp đông, mua theo lô tại cảng.")],
            )
        )
        self.assertEqual(_claims(warnings), [])

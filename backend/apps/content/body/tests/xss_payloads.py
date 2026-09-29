"""15 payload XSS mẫu theo §6.3 02b-tech-design dùng cho CMS-03-AC5 và CMS-13-AC2."""

XSS_PAYLOADS = [
    # 1. Khối html lạ -> bị loại bỏ
    {"type": "html", "html": "<script>alert(1)</script>"},
    # 2. Khối script lạ -> bị loại bỏ
    {"type": "script", "src": "https://evil.example/x.js"},
    # 3. Khối iframe lạ -> bị loại bỏ
    {"type": "iframe", "src": "https://evil.example"},
    # 4. Khối embed lạ -> bị loại bỏ
    {"type": "embed", "code": "<object data=x>"},
    # 5. href javascript -> bị bỏ href, giữ text
    {"type": "paragraph", "children": [{"text": "x", "href": "javascript:alert(1)"}]},
    # 6. href hoa thường + khoảng trắng đầu -> bị bỏ href
    {"type": "paragraph", "children": [{"text": "x", "href": " JaVaScRiPt:alert(1)"}]},
    # 7. href tab chèn giữa -> bị bỏ href
    {"type": "paragraph", "children": [{"text": "x", "href": "java\tscript:alert(1)"}]},
    # 8. href data URI -> bị bỏ href
    {"type": "paragraph", "children": [{"text": "x", "href": "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg=="}]},
    # 9. href vbscript -> bị bỏ href
    {"type": "paragraph", "children": [{"text": "x", "href": "vbscript:msgbox(1)"}]},
    # 10. href //evil.example/phish và /\\evil.example -> bị bỏ href
    {"type": "paragraph", "children": [{"text": "x", "href": "//evil.example/phish"}, {"text": "y", "href": "/\\evil.example"}]},
    # 11. text chứa thẻ img onerror -> giữ nguyên chữ text
    {"type": "paragraph", "children": [{"text": "<img src=x onerror=alert(1)>"}]},
    # 12. mark lạ (script, onclick) -> chỉ giữ mark cho phép (bold/italic)
    {"type": "paragraph", "children": [{"text": "a", "marks": ["bold", "script", "onclick"]}]},
    # 13. heading level=1 (sai level) và thuộc tính thừa (onclick, style) -> level thành 2, bỏ onclick/style, giữ text
    {"type": "heading", "level": 1, "text": "<svg onload=alert(1)>", "onclick": "alert(1)", "style": "x"},
    # 14. image_id của bài khác -> raise 400 BR-ND-07 (xử lý khi sanitize với entry)
    {"type": "image", "image_id": 999999, "alt": '" onerror="alert(1)'},
    # 15. item_code không hợp lệ chứa tag XSS -> không khớp ^[A-Za-z0-9_.-]{1,40}$ -> bị loại bỏ
    {"type": "item_card", "item_code": '"><script>alert(1)</script>'},
]

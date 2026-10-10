"""
Đổi chữ soạn sẵn (quy ước `doc/ops/cms-cho-mkt.md` §9) sang thân bài JSON khối của CMS (SHOP-1-07).

Quy ước dòng:
- `## …` / `### …`        -> heading cấp 2 / 3
- `- …` liền nhau          -> list không thứ tự; `1. …` liền nhau -> list có thứ tự
- `> …`                    -> quote
- `@item_card MÃ`          -> khối item_card (người gọi quyết định giữ hay bỏ theo mã có thật)
- dòng bắt đầu `⟨ghi chú⟩` -> bỏ qua
- dòng khác                -> paragraph
Trong dòng: `**chữ đậm**`, `[chữ](href)`. Ngoặc vuông không có `(href)` theo sau (vd `[số]`) giữ nguyên làm chỗ chờ.
"""
import re

NOTE_PREFIX = "⟨ghi chú⟩"
ITEM_CARD_PREFIX = "@item_card "
ORDERED_RE = re.compile(r"^\d+\.\s+")
INLINE_RE = re.compile(r"\*\*(?P<bold>.+?)\*\*|\[(?P<label>[^\[\]]+)\]\((?P<href>[^()\s]+)\)")


def parse_inline(text: str) -> list[dict]:
    """Tách một dòng thành các phần tử con {text, marks?, href?}."""
    nodes: list[dict] = []
    pos = 0
    for match in INLINE_RE.finditer(text):
        if match.start() > pos:
            nodes.append({"text": text[pos:match.start()]})
        if match.group("bold") is not None:
            nodes.append({"text": match.group("bold"), "marks": ["bold"]})
        else:
            nodes.append({"text": match.group("label"), "href": match.group("href")})
        pos = match.end()
    if pos < len(text):
        nodes.append({"text": text[pos:]})
    return [n for n in nodes if n["text"]]


def lines_to_blocks(lines: list[str]) -> list[dict]:
    """Đổi danh sách dòng sang danh sách khối (chưa qua normalize_body)."""
    blocks: list[dict] = []
    current_list: dict | None = None

    def close_list():
        nonlocal current_list
        if current_list is not None:
            blocks.append(current_list)
            current_list = None

    for raw in lines:
        line = str(raw).strip()
        if not line or line.startswith(NOTE_PREFIX):
            continue
        if line.startswith("- "):
            if current_list is None or current_list["ordered"]:
                close_list()
                current_list = {"type": "list", "ordered": False, "items": []}
            current_list["items"].append(parse_inline(line[2:].strip()))
            continue
        ordered = ORDERED_RE.match(line)
        if ordered:
            if current_list is None or not current_list["ordered"]:
                close_list()
                current_list = {"type": "list", "ordered": True, "items": []}
            current_list["items"].append(parse_inline(line[ordered.end():].strip()))
            continue
        close_list()
        if line.startswith("### "):
            blocks.append({"type": "heading", "level": 3, "text": line[4:].strip()})
        elif line.startswith("## "):
            blocks.append({"type": "heading", "level": 2, "text": line[3:].strip()})
        elif line.startswith("> "):
            blocks.append({"type": "quote", "children": parse_inline(line[2:].strip())})
        elif line.startswith(ITEM_CARD_PREFIX):
            blocks.append({"type": "item_card", "item_code": line[len(ITEM_CARD_PREFIX):].strip()})
        else:
            blocks.append({"type": "paragraph", "children": parse_inline(line)})
    close_list()
    return blocks

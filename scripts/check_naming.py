#!/usr/bin/env python3
"""Chặn định danh tiếng Việt mới trong code (P8b Lô 0).

Luật (doc/features/2026-09-30-dat-ten-tieng-anh/02c-giao-viec.md §1): định danh (hàm, biến, class, module,
thư mục, file, test, script, route API, khoá JSON, biến env, Group, id lệnh AI, khoá lưu trình duyệt,
data-testid) là tiếng Anh chuẩn. Chữ hiển thị, comment, docstring, tài liệu vẫn tiếng Việt.

Cách chạy (từ gốc repo, Python 3 stdlib, không cần venv):

    python3 scripts/check_naming.py            # kiểm: exit 0 = không phát sinh tên tiếng Việt mới
    python3 scripts/check_naming.py --update   # khoá thành quả sau khi đổi tên (chỉ cho phép GIẢM)
    python3 scripts/check_naming.py --report   # in toàn bộ vi phạm hiện có theo file (không đổi exit code)
    python3 scripts/check_naming.py --words    # in tần suất từ trong blocklist (để chọn việc đổi tên)
    python3 scripts/check_naming.py --self-test  # kiểm bộ quét bằng mẫu nhỏ (chạy sau khi sửa script này)

Cơ chế:
  * Quét mọi file git-tracked và file mới chưa ignore trong backend/ adapter/ frontend/ erp-console/ (bỏ
    node_modules, .next, out, .venv, staticfiles, shots, migrations).
  * Python: dùng `tokenize` -> lấy NAME và chuỗi literal dạng định danh, bỏ comment và docstring.
    TS/TSX/MJS: bộ quét nhỏ biết chuỗi, template, comment, regex literal và JSX (bỏ chữ giữa thẻ JSX).
  * Chuỗi literal chỉ xét khi KHÔNG có dấu tiếng Việt, KHÔNG có khoảng trắng (vd "nhap-lo", "cskh_notice").
    Nên chữ hiển thị "Nhập lô", "tra tồn" không bị bắt. File test/e2e chỉ xét định danh và tên file
    (username demo như "kho1" là dữ liệu, không phải định danh).
  * Tách từ theo snake_case, camelCase, kebab-case, rồi đối chiếu scripts/naming_blocklist.txt.
  * Tên file và thư mục cũng bị xét.
  * scripts/naming_baseline.json = {đường dẫn file: số lần vi phạm} chụp tại commit cuối sửa file này (HEAD nếu chưa commit). Thất bại (exit 1) khi file
    không có trong baseline mà có vi phạm, hoặc số vi phạm của file trong baseline TĂNG. File đổi chỗ bằng
    `git mv` kế thừa baseline của đường dẫn cũ (phát hiện qua `git diff -M` so với commit của baseline, nên
    đã commit phép đổi tên mà chưa `--update` vẫn kế thừa được).

Ngoại lệ vĩnh viễn (có lý do, xem EXEMPT_* bên dưới) và ngoại lệ từng dòng:
    # naming: allow   (Python)      // naming: allow   (TS)
  Dòng ghi `naming: allow - <lý do>` bị bỏ qua; thiếu lý do thì KHÔNG được miễn. Dùng đúng cho dữ liệu/hằng
  tương thích có lý do, techlead duyệt. `--report` in danh sách các dòng đang dùng marker để soát.
  Muốn miễn một từ tiếng Việt mà code sản phẩm dùng làm định danh chính thức: DỪNG và hỏi Duy (02c Lô 0).

Nguồn từ điển: bản rà soát 30/09 (doc/features/2026-09-30-dat-ten-tieng-anh/01-ra-soat-dat-ten.md) và
đợt dò từ tần suất toàn repo ngày 01/10. Từ trùng nghĩa tiếng Anh (ton, don, hang, ban, chi, ...) KHÔNG nằm
trong blocklist đơn, chỉ bị chặn khi đi thành cặp tiếng Việt (ban+hang, thu+mua, quan+ly, ...).
"""
from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
import tokenize
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
BLOCKLIST_FILE = SCRIPTS / "naming_blocklist.txt"
BASELINE_FILE = SCRIPTS / "naming_baseline.json"

SCAN_DIRS = ("backend", "adapter", "frontend", "erp-console")
# Thư mục bỏ qua (theo từng thành phần của đường dẫn). migrations: migration đã chạy không được đổi (R12).
SKIP_PARTS = {
    "node_modules", ".next", "out", ".venv", "staticfiles", "shots", "migrations", "__pycache__",
    ".pytest_cache", "coverage", "dist",
}
PY_EXT = {".py"}
JS_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
JSX_EXT = {".tsx", ".jsx"}

# ---------------------------------------------------------------------------------------------------------
# Miễn vĩnh viễn (02c Lô 0). Mỗi dòng ghi lý do.
# ---------------------------------------------------------------------------------------------------------
# Bỏ qua cả file (đường dẫn tiền tố; thư mục kết thúc bằng "/").
EXEMPT_PATH_PREFIXES = (
    # URL công khai Shop (/bai-viet/, /trang/) là chữ khách nhìn thấy, đã nằm trong link/QR phát ra (R13, 02c §1d).
    "frontend/app/bai-viet/",
    "frontend/app/trang/",
    # /gioi-thieu/ là URL công khai Duy chốt 10/10 (landing thương hiệu chuyển khỏi /).
    "frontend/app/gioi-thieu/",
)
# Chỉ miễn CHUỖI literal (định danh vẫn bị xét), giữ vĩnh viễn: file chứa map id/nhóm AI cũ -> mới cho các phiên bản
# cấu hình AI đã ghim (append-only, 02c Lô 4). Tên hàm/biến trong file này vẫn phải là tiếng Anh (review Lô 0, R3).
# Lô 5 đã bỏ roles.py, command_groups.py, roles.ts khỏi danh sách này (giá trị đã là tiếng Anh); legacyIds.ts đã xoá.
EXEMPT_STRING_FILES = (
    "backend/apps/ai/registry/legacy_ids.py",
)
# Dòng KHAI BÁO hằng này được miễn: khoá nháp cũ có giá mua phải bị xoá vĩnh viễn (R4, SR-07).
# Chỉ dòng khai báo (`LEGACY_RECEIVE_BATCHES_DRAFT_PREFIX = ...`), dòng chỉ nhắc tên hằng không được miễn.
EXEMPT_LINE_PATTERNS = (
    re.compile(r"\bLEGACY_RECEIVE_BATCHES_DRAFT_PREFIX\b\s*(?::[^=]+)?=(?!=)"),
)
# `naming: allow` chỉ có hiệu lực khi kèm lý do, vd `# naming: allow - username demo` hay `// naming: allow (khoá cũ)`.
ALLOW_MARKER = "naming: allow"
ALLOW_WITH_REASON = re.compile(r"naming: allow\s*[-:\u2014(]\s*\S.{2,}")
# File dữ liệu giả (mock): chữ trong đó là dữ liệu demo nên không xét chuỗi, định danh vẫn xét (review Lô 0, R4).
MOCK_FILE = re.compile(r"^(?:mock|[\w.\-]+\.mock)\.[cm]?[jt]sx?$")
# Chuỗi literal được miễn (so khớp nguyên chuỗi, không phân biệt hoa thường).
EXEMPT_LITERALS = {
    "chuyen-muc",        # tham số lọc chuyên mục trên URL công khai Shop (02c §1d, R13)
    "asia/ho_chi_minh",  # tên múi giờ IANA
}
# Chuỗi KHÔNG phải định danh dù không dấu, không khoảng trắng:
#  - viết hoa toàn bộ, không có gạch dưới: mã dữ liệu (mã hàng TOM-SU-1, mã lô CA-NGU-260919-CN01, mã business
#    rule BR-LO-04, hậu tố -THUA) hoặc nhãn hiển thị một từ ("NCC"). Tên biến env có gạch dưới nên vẫn bị xét.
#  - một từ viết hoa chữ đầu: nhãn hiển thị một từ ("Ghi", "Chu"). Khoá/route luôn là chữ thường hoặc camelCase.
_DISPLAY_OR_CODE = re.compile(r"^(?:[^a-z_]*|[A-Z][a-z]+)$")

# Chuỗi literal chỉ xét khi khớp mẫu này (không dấu, không khoảng trắng) -> tách từ.
_LITERAL_OK = re.compile(r"^[A-Za-z0-9_\-./:@#?=&%+*~$,;!\[\]{}()<>|^']+$")
_SUBWORD = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+[0-9]*|[A-Z]+[0-9]*|[0-9]+")
_TRAILING_DIGITS = re.compile(r"[0-9]+$")


# ---------------------------------------------------------------------------------------------------------
# Blocklist
# ---------------------------------------------------------------------------------------------------------
class Blocklist:
    def __init__(self, singles: set[str], pairs: set[tuple[str, str]], patterns: list[re.Pattern],
                 test_name_patterns: list[re.Pattern]):
        self.singles = singles
        self.pairs = pairs
        self.patterns = patterns
        self.test_name_patterns = test_name_patterns

    @classmethod
    def load(cls, path: Path = BLOCKLIST_FILE) -> "Blocklist":
        singles: set[str] = set()
        pairs: set[tuple[str, str]] = set()
        patterns: list[re.Pattern] = []
        test_name_patterns: list[re.Pattern] = []
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if line.startswith("re:"):
                patterns.append(re.compile(line[3:].strip()))
            elif line.startswith("testname:"):
                test_name_patterns.append(re.compile(line[len("testname:"):].strip()))
            elif "+" in line:
                first, second = (part.strip().lower() for part in line.split("+", 1))
                pairs.add((first, second))
            else:
                singles.add(line.lower())
        return cls(singles, pairs, patterns, test_name_patterns)


def split_subwords(text: str) -> list[str]:
    """Tách 'soLuongKho', 'nhap_lo_kg', 'cskh-notice' thành các từ thường (giữ chữ số dính cuối từ)."""
    words: list[str] = []
    for chunk in re.split(r"[^A-Za-z0-9]+", text):
        if chunk:
            words.extend(part.lower() for part in _SUBWORD.findall(chunk))
    return words


def find_hits(words: list[str], blocklist: Blocklist, *, is_test_name: bool = False) -> list[str]:
    """Trả về danh sách mô tả vi phạm trong một định danh đã tách từ (mỗi từ/cặp chặn tính 1 lần)."""
    hits: list[str] = []
    bases = [_TRAILING_DIGITS.sub("", word) or word for word in words]
    index = 0
    while index < len(words):
        word, base = words[index], bases[index]
        if index + 1 < len(words) and (base, bases[index + 1]) in blocklist.pairs:
            hits.append(f"{base}+{bases[index + 1]}")
            index += 2
            continue
        if base in blocklist.singles:
            hits.append(base)
        elif any(pattern.fullmatch(word) for pattern in blocklist.patterns):
            hits.append(word)
        elif is_test_name and any(pattern.fullmatch(word) for pattern in blocklist.test_name_patterns):
            hits.append(word)
        index += 1
    return hits


# ---------------------------------------------------------------------------------------------------------
# Trích định danh: Python
# ---------------------------------------------------------------------------------------------------------
def _literal_body(token_text: str) -> str | None:
    match = re.match(r"^[A-Za-z]*('''|\"\"\"|'|\")(.*)\1$", token_text, re.S)
    return match.group(2) if match else None


def _is_identifier_literal(body: str) -> bool:
    return (bool(body) and "\\" not in body and bool(_LITERAL_OK.match(body))
            and body.lower() not in EXEMPT_LITERALS and not _DISPLAY_OR_CODE.match(body))


_FSTRING_START = getattr(tokenize, "FSTRING_START", None)
_FSTRING_END = getattr(tokenize, "FSTRING_END", None)


def _python_tokens(source: str):
    """Sinh (loại, văn bản, dòng) với f-string luôn là MỘT token STRING, giống Python 3.11 trở xuống.

    Từ Python 3.12, `tokenize` tách f-string thành FSTRING_START/MIDDLE/END và trả NAME cho biểu thức trong `{}`;
    nếu không gom lại thì cùng một file cho số vi phạm khác nhau giữa các phiên bản Python (B1, review 01/10).
    Gom lại bằng cách lấy nguyên đoạn nguồn từ FSTRING_START tới FSTRING_END tương ứng (đếm lồng nhau)."""
    lines = source.splitlines(keepends=True)
    depth = 0
    start = (0, 0)
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        ttype = token[0]
        if _FSTRING_START is not None and ttype == _FSTRING_START:
            if depth == 0:
                start = token[2]
            depth += 1
            continue
        if _FSTRING_END is not None and ttype == _FSTRING_END:
            depth -= 1
            if depth == 0:
                (row0, col0), (row1, col1) = start, token[3]
                if row0 == row1:
                    text = lines[row0 - 1][col0:col1]
                else:
                    text = lines[row0 - 1][col0:] + "".join(lines[row0:row1 - 1]) + lines[row1 - 1][:col1]
                yield tokenize.STRING, text, row0
            continue
        if depth > 0:
            continue  # phần giữa của f-string (chữ, NAME trong {}) đã nằm trong đoạn nguồn gom ở trên
        yield ttype, token[1], token[2][0]


def extract_python(source: str, *, check_strings: bool) -> list[tuple[int, str, str]]:
    """Trả về [(dòng, văn bản, loại)] với loại là 'name' hoặc 'string'. Bỏ comment và docstring."""
    found: list[tuple[int, str, str]] = []
    skip_types = {tokenize.NL, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT}
    statement_start = True  # token kế tiếp là đầu câu lệnh
    previous_was_doc_string = False
    try:
        for ttype, text, line in _python_tokens(source):
            if ttype in skip_types:
                continue
            if ttype == tokenize.NEWLINE:
                statement_start = True
                previous_was_doc_string = False
                continue
            if ttype == tokenize.NAME:
                found.append((line, text, "name"))
            elif ttype == tokenize.STRING:
                is_doc = statement_start or previous_was_doc_string
                previous_was_doc_string = is_doc
                if not is_doc and check_strings:
                    body = _literal_body(text)
                    if body is not None and _is_identifier_literal(body):
                        found.append((line, body, "string"))
            statement_start = False
            if ttype != tokenize.STRING:
                previous_was_doc_string = False
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass  # file lỗi cú pháp: lấy phần đã đọc được, lỗi cú pháp không phải việc của script này
    return found


# ---------------------------------------------------------------------------------------------------------
# Trích định danh: TS / TSX / MJS (bộ quét nhỏ, biết chuỗi, template, comment, regex, JSX)
# ---------------------------------------------------------------------------------------------------------
_IDENT_START = re.compile(r"[A-Za-z_$]")
_IDENT = re.compile(r"[A-Za-z_$][\w$]*")
_JSX_NAME = re.compile(r"[A-Za-z_$][\w$\-:.]*")
_NUMBER = re.compile(r"[0-9][\w.]*")
# Sau các từ khoá này, dấu "<" mở JSX và dấu "/" mở regex literal.
_EXPR_START_KEYWORDS = {
    "return", "default", "case", "yield", "await", "of", "in", "typeof", "void", "delete", "else", "do",
    "throw", "new", "instanceof",
}
_EXPR_START_PUNCT = set("(,=:?;!&|^~{[+-*%")


def extract_typescript(source: str, *, jsx: bool, check_strings: bool,
                       state: dict | None = None) -> list[tuple[int, str, str]]:
    """Bộ quét TS/TSX. Không phải parser đầy đủ: đủ chính xác để bỏ comment, regex, chữ JSX và template text.

    `state["balanced"]` báo hết file mà ngăn xếp JSX/template/ngoặc đã về khung gốc hay chưa (để phát hiện cú
    pháp lạ làm bộ quét lạc nhịp; script cảnh báo trên stderr)."""
    found: list[tuple[int, str, str]] = []
    n = len(source)
    i = 0
    line = 1
    # Ngăn xếp khung: ("code", kind, depth) | ("tag", closing, name_done) | ("children",) | ("template",)
    stack: list[list] = [["code", "top", 0]]
    prev = ""  # token có nghĩa trước đó: "id", "num", "str", "rx", hoặc ký tự dấu, hoặc từ khoá

    def expr_start() -> bool:
        if prev in ("", "=>") or prev in _EXPR_START_KEYWORDS:
            return True
        return len(prev) == 1 and prev in _EXPR_START_PUNCT

    def add_string(body: str, at_line: int):
        if check_strings and _is_identifier_literal(body):
            found.append((at_line, body, "string"))

    def read_quoted(start: int, quote: str) -> tuple[str, int, int]:
        j = start + 1
        lines = 0
        while j < n and source[j] != quote:
            if source[j] == "\\":
                j += 1
            elif source[j] == "\n":
                lines += 1
            j += 1
        return source[start + 1:j], min(j + 1, n), lines

    while i < n:
        frame = stack[-1]
        c = source[i]
        if c == "\n":
            line += 1
            i += 1
            continue
        kind = frame[0]

        # ------------------------------------------------------------------ template literal text
        if kind == "template":
            j = i
            chunk_start_line = line
            while j < n:
                if source[j] == "\\":
                    j += 2
                    continue
                if source[j] == "`":
                    break
                if source[j] == "$" and j + 1 < n and source[j + 1] == "{":
                    break
                if source[j] == "\n":
                    line += 1
                j += 1
            add_string(source[i:j], chunk_start_line)
            if j >= n:
                break
            if source[j] == "`":
                stack.pop()
                prev = "str"
                i = j + 1
            else:
                stack.append(["code", "tmpl", 0])
                prev = "{"
                i = j + 2
            continue

        # ------------------------------------------------------------------ JSX children (chữ hiển thị: bỏ qua)
        if kind == "children":
            if c == "{":
                stack.append(["code", "expr", 0])
                prev = "{"
                i += 1
            elif c == "<":
                if source.startswith("</", i):
                    stack.append(["tag", True])
                    i += 2
                else:
                    stack.append(["tag", False])
                    i += 1
            else:
                i += 1
            continue

        # ------------------------------------------------------------------ JSX tag (tên thẻ, thuộc tính)
        if kind == "tag":
            closing = frame[1]
            if c in " \t\r":
                i += 1
            elif source.startswith("/>", i):
                stack.pop()
                prev = ")"
                i += 2
            elif c == ">":
                stack.pop()
                if closing:
                    stack.pop()  # bỏ luôn khung children của thẻ này
                    prev = ")"
                else:
                    stack.append(["children"])
                i += 1
            elif c == "{":
                stack.append(["code", "expr", 0])
                prev = "{"
                i += 1
            elif c in "\"'":
                body, i2, extra = read_quoted(i, c)
                add_string(body, line)
                line += extra
                i = i2
            elif c == "=" or c == "/":
                i += 1
            elif source.startswith("//", i) or source.startswith("/*", i):
                i += 1
            else:
                m = _JSX_NAME.match(source, i)
                if m:
                    found.append((line, m.group(0), "name"))
                    i = m.end()
                else:
                    i += 1
            continue

        # ------------------------------------------------------------------ code
        if source.startswith("//", i):
            j = source.find("\n", i)
            i = n if j < 0 else j
            continue
        if source.startswith("/*", i):
            j = source.find("*/", i + 2)
            j = n if j < 0 else j + 2
            line += source.count("\n", i, j)
            i = j
            continue
        if c in " \t\r":
            i += 1
            continue
        if c in "\"'":
            body, i2, extra = read_quoted(i, c)
            add_string(body, line)
            line += extra
            i = i2
            prev = "str"
            continue
        if c == "`":
            stack.append(["template"])
            i += 1
            continue
        if c == "{":
            frame[2] += 1
            prev = "{"
            i += 1
            continue
        if c == "}":
            if frame[2] == 0 and frame[1] != "top":
                stack.pop()
                prev = "}" if frame[1] == "tmpl" else "str"
            else:
                frame[2] = max(0, frame[2] - 1)
                prev = "}"
            i += 1
            continue
        if c == "<" and jsx and i + 1 < n and (source[i + 1] in "_$>" or source[i + 1].isalpha()) \
                and expr_start():
            stack.append(["tag", False])
            i += 1
            continue
        if c == "/" and expr_start():  # regex literal
            j = i + 1
            in_class = False
            while j < n and source[j] != "\n":
                ch = source[j]
                if ch == "\\":
                    j += 2
                    continue
                if ch == "[":
                    in_class = True
                elif ch == "]":
                    in_class = False
                elif ch == "/" and not in_class:
                    break
                j += 1
            i = min(j + 1, n)
            while i < n and source[i].isalpha():
                i += 1
            prev = "rx"
            continue
        if _IDENT_START.match(c):
            m = _IDENT.match(source, i)
            word = m.group(0)
            found.append((line, word, "name"))
            prev = word if word in _EXPR_START_KEYWORDS else "id"
            i = m.end()
            continue
        if c.isdigit():
            m = _NUMBER.match(source, i)
            prev = "num"
            i = m.end()
            continue
        if source.startswith("=>", i):
            prev = "=>"
            i += 2
            continue
        prev = c if c not in ")]" else ")"
        i += 1
    if state is not None:
        state["balanced"] = len(stack) == 1 and stack[0][2] == 0
    return found


# ---------------------------------------------------------------------------------------------------------
# Quét repo
# ---------------------------------------------------------------------------------------------------------
def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def list_files() -> list[str]:
    """File git-tracked và file mới chưa bị ignore, trong SCAN_DIRS, còn tồn tại trên đĩa."""
    out = git("ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", *SCAN_DIRS)
    files = []
    for rel in sorted(set(filter(None, out.split("\0")))):
        parts = Path(rel).parts
        if any(part in SKIP_PARTS for part in parts):
            continue
        if (ROOT / rel).is_file():
            files.append(rel)
    return files


def is_test_path(rel: str) -> bool:
    path = Path(rel)
    name = path.name
    parts = set(path.parts)
    return (
        "tests" in parts or "e2e" in parts or name.startswith("test_") or name == "conftest.py"
        or name.endswith("_test.py") or bool(re.search(r"\.(test|spec)\.[cm]?[jt]sx?$", name))
    )


def is_exempt_path(rel: str) -> bool:
    return any(rel == prefix or (prefix.endswith("/") and rel.startswith(prefix)) or rel.startswith(prefix)
               for prefix in EXEMPT_PATH_PREFIXES)


def line_is_allowed(text: str) -> bool:
    return bool(ALLOW_WITH_REASON.search(text)) or any(pattern.search(text) for pattern in EXEMPT_LINE_PATTERNS)


def is_mock_path(rel: str) -> bool:
    return bool(MOCK_FILE.match(Path(rel).name))


def scan_source(rel: str, source: str, blocklist: Blocklist) -> list[tuple[int, str, str]]:
    """Vi phạm trong NỘI DUNG file: [(dòng, token gốc, mô tả hit)]."""
    suffix = Path(rel).suffix
    test_file = is_test_path(rel)
    check_strings = not test_file and not is_mock_path(rel) and rel not in EXEMPT_STRING_FILES
    if suffix in PY_EXT:
        tokens = extract_python(source, check_strings=check_strings)
    elif suffix in JS_EXT:
        state: dict = {}
        tokens = extract_typescript(source, jsx=suffix in JSX_EXT, check_strings=check_strings, state=state)
        if state.get("balanced") is False:
            print(f"check_naming: cảnh báo: không phân tích trọn vẹn {rel} (JSX/ngoặc lạ), có thể sót tên.",
                  file=sys.stderr)
    else:
        return []
    lines = source.splitlines()
    violations = []
    for line_no, text, _kind in tokens:
        hits = find_hits(split_subwords(text), blocklist)
        if not hits:
            continue
        if 0 < line_no <= len(lines) and line_is_allowed(lines[line_no - 1]):
            continue
        violations.append((line_no, text, ", ".join(hits)))
    return violations


def allow_marker_lines() -> list[tuple[str, int, str]]:
    """Mọi dòng có marker `naming: allow` (kể cả thiếu lý do) để techlead soát."""
    found = []
    for rel in list_files():
        if Path(rel).suffix not in PY_EXT | JS_EXT or is_exempt_path(rel):
            continue
        try:
            text = (ROOT / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if ALLOW_MARKER not in text:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if ALLOW_MARKER in line:
                found.append((rel, number, line))
    return found


def scan_path_name(rel: str, blocklist: Blocklist) -> list[tuple[int, str, str]]:
    """Vi phạm trong TÊN thư mục và file (dòng 0)."""
    violations = []
    test_file = is_test_path(rel)
    for index, part in enumerate(Path(rel).parts):
        is_name = index == len(Path(rel).parts) - 1
        hits = find_hits(split_subwords(part), blocklist, is_test_name=test_file and is_name)
        if hits:
            violations.append((0, part, ", ".join(hits)))
    return violations


def scan_file(rel: str, blocklist: Blocklist, text: str | None = None) -> list[tuple[int, str, str]]:
    if is_exempt_path(rel):
        return []
    if text is None:
        try:
            text = (ROOT / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            text = ""
    return scan_path_name(rel, blocklist) + scan_source(rel, text, blocklist)


def scan_repo(blocklist: Blocklist) -> dict[str, list[tuple[int, str, str]]]:
    result = {}
    for rel in list_files():
        violations = scan_file(rel, blocklist)
        if violations:
            result[rel] = violations
    return result


# ---------------------------------------------------------------------------------------------------------
# Baseline và đổi chỗ file
# ---------------------------------------------------------------------------------------------------------
def load_baseline() -> dict[str, int]:
    if not BASELINE_FILE.exists():
        return {}
    return json.loads(BASELINE_FILE.read_text(encoding="utf-8"))


def write_baseline(counts: dict[str, int]) -> None:
    ordered = {key: counts[key] for key in sorted(counts)}
    BASELINE_FILE.write_text(json.dumps(ordered, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


_BASE_REF: str | None = None


def base_ref() -> str:
    """Commit mà baseline phản ánh: commit gần nhất có sửa naming_baseline.json (HEAD nếu baseline chưa commit).
    So với commit này thì phép `git mv` đã commit mà chưa `--update` vẫn kế thừa được baseline cũ."""
    global _BASE_REF
    if _BASE_REF is None:
        try:
            _BASE_REF = git("log", "-1", "--format=%H", "--", "scripts/naming_baseline.json").strip() or "HEAD"
        except subprocess.CalledProcessError:
            _BASE_REF = "HEAD"
    return _BASE_REF


def rename_map() -> dict[str, str]:
    """{đường dẫn mới: đường dẫn cũ} theo `git diff -M` so với commit của baseline (`base_ref`): gồm `git mv` đã
    stage, chưa stage, và cả đã commit sau baseline mà chưa chạy `--update`."""
    try:
        out = git("diff", "-M", "--name-status", "-z", base_ref(), "--", *SCAN_DIRS)
    except subprocess.CalledProcessError:
        return {}
    parts = out.split("\0")
    mapping = {}
    index = 0
    while index < len(parts) and parts[index]:
        status = parts[index]
        if status.startswith("R") and index + 2 < len(parts):
            mapping[parts[index + 2]] = parts[index + 1]
            index += 3
        else:
            index += 2
    return mapping


def head_token_counts(rel: str, blocklist: Blocklist) -> Counter:
    """Đếm hit theo token của bản ở commit baseline, để chỉ ra dòng MỚI khi số vi phạm của file tăng."""
    try:
        text = git("show", f"{base_ref()}:{rel}")
    except subprocess.CalledProcessError:
        return Counter()
    return Counter(desc for _line, _tok, desc in scan_file(rel, blocklist, text))


def evaluate(blocklist: Blocklist, baseline: dict[str, int], current: dict[str, list]):
    """Trả về (lỗi, đã giảm). lỗi = [(file, baseline hoặc None, danh sách dòng cần in)]."""
    renames = rename_map()
    failures = []
    improved = {}
    for rel, violations in sorted(current.items()):
        allowed = baseline.get(rel)
        inherited = False
        if allowed is None and rel in renames:
            allowed = baseline.get(renames[rel])
            inherited = allowed is not None
        count = weight(violations)
        if allowed is None:
            failures.append((rel, None, violations))
        elif count > allowed:
            old = head_token_counts(renames[rel] if inherited else rel, blocklist)
            seen: Counter = Counter()
            new_lines = []
            for item in violations:
                seen[item[2]] += 1
                if seen[item[2]] > old.get(item[2], 0):
                    new_lines.append(item)
            lines = new_lines or violations
            failures.append((rel, allowed, lines))
        elif count < allowed:
            improved[rel] = count
    return failures, improved


def weight(items) -> int:
    """Số lần vi phạm: mỗi từ/cặp bị chặn trong một định danh tính 1 lần."""
    return sum(desc.count(", ") + 1 for _line, _token, desc in items)


def format_violation(rel: str, item: tuple[int, str, str]) -> str:
    line_no, token, hit = item
    where = f"{rel}:{line_no}" if line_no else f"{rel} (tên file/thư mục)"
    return f"  {where}  '{token}'  -> từ tiếng Việt: {hit}"


# ---------------------------------------------------------------------------------------------------------
def self_test() -> int:
    """Kiểm bộ quét bằng mẫu nhỏ: cái gì phải bị bắt, cái gì không được bắt nhầm."""
    blocklist = Blocklist.load()

    def hits(rel: str, source: str) -> list[str]:
        return sorted(token for _line, token, _hit in scan_source(rel, source, blocklist))

    py = (
        '"""Docstring tiếng Việt: kho giao nhập lô."""\n'
        "# comment kho giao\n"
        "class Report:\n"
        '    """nhap lo khong"""\n'
        '    label = "Nhập lô"\n'
        '    hint = "tra tồn"\n'
        '    word = "Ghi"\n'
        '    code = "TOM-SU-1"\n'
        '    tz = "Asia/Ho_Chi_Minh"\n'
        '    param = "chuyen-muc"\n'
        '    route = "nhap-lo"\n'
        "    def tinh_tien_hang(self):\n"
        "        return self.soLuongKho  # kho\n"
        '    okay = "kho"  # naming: allow - du lieu demo\n'
    )
    expected = ["nhap-lo", "soLuongKho", "tinh_tien_hang"]
    assert hits("backend/apps/x/api.py", py) == expected, hits("backend/apps/x/api.py", py)
    # file test: chuỗi literal (dữ liệu demo) không bị xét, định danh vẫn bị xét
    test_py = 'def test_x(self):\n    user = "kho1"\n    self.chu = 1\n    self.assertEqual("nhap-lo", 1)\n'
    assert hits("backend/apps/x/tests/test_a.py", test_py) == ["chu"], hits("backend/apps/x/tests/test_a.py", test_py)
    # file riêng chứa giá trị Group cũ: chuỗi được miễn, định danh vẫn bị xét
    assert hits("backend/apps/ai/registry/legacy_ids.py", 'LEGACY = {"quan_ly": "manager"}\n') == []
    assert hits("backend/apps/ai/registry/legacy_ids.py", "chu = 1\n") == ["chu"]
    # Lô 5: roles.py / command_groups.py không còn được miễn chuỗi (giá trị đã là tiếng Anh)
    assert hits("backend/apps/accounts/roles.py", 'OWNER = "chu"\n') == ["chu"], hits("backend/apps/accounts/roles.py", 'OWNER = "chu"\n')

    ts = (
        "// comment kho\n"
        "/* block giao */\n"
        'import { CskhNotice } from "./CskhNotice";\n'
        "const soLuongKho = 1; // kho\n"
        "const re = /kho[a-z]+/g; const ratio = a / b;\n"
        "const t = `Không có ${nhapLo} hàng`;\n"
        "function F() {\n"
        "  return (\n"
        '    <div className="a-b" data-testid="cskh-notice" title="Kho hàng">\n'
        "      Kho hàng hết giao nhanh\n"
        "      {items.map((item) => <span key={item.id}>{item.tenKho} chữ khong</span>)}\n"
        "      {/* comment kho */}\n"
        '      <Foo prop="Nhập lô" />\n'
        "    </div>\n"
        "  );\n"
        "}\n"
    )
    expected_ts = sorted(["CskhNotice", "./CskhNotice", "soLuongKho", "nhapLo", "cskh-notice", "tenKho"])
    assert hits("erp-console/features/x/A.tsx", ts) == expected_ts, hits("erp-console/features/x/A.tsx", ts)

    # f-string: kết quả phải GIỐNG NHAU trên mọi phiên bản Python (3.12 trở lên tách f-string thành nhiều token).
    fs_test = 'def test_x(self):\n    url = f"/x/{self.user_kho.id}/"\n    self.client.get(f"/api/{kho_id}/")\n'
    assert hits("backend/apps/x/tests/test_a.py", fs_test) == [], hits("backend/apps/x/tests/test_a.py", fs_test)
    fs_prod = 'def f(x):\n    a = f"nhap-lo/{x}"\n    b = f"Nhập lô {x} kho hàng"\n    c = f"{x:>5}" + f"{f\'{x}\'}"\n    return a\n'
    assert hits("backend/apps/x/api.py", fs_prod) == ["nhap-lo/{x}"], hits("backend/apps/x/api.py", fs_prod)
    fs_multi = 'def f(x):\n    return (\n        f"""\n        chu {x}\n        """\n    )\nkho = 1\n'
    assert hits("backend/apps/x/api.py", fs_multi) == ["kho"], hits("backend/apps/x/api.py", fs_multi)
    # naming: allow phải kèm lý do; khai báo LEGACY_RECEIVE_BATCHES_DRAFT_PREFIX được miễn, dòng chỉ nhắc tên thì không
    allow = (
        'a_kho = 1  # naming: allow\n'
        'b_kho = 1  # naming: allow - username demo\n'
        'LEGACY_RECEIVE_BATCHES_DRAFT_PREFIX = "cave_draft_nhap_lo"\n'
        'clear_kho(LEGACY_RECEIVE_BATCHES_DRAFT_PREFIX)\n'
    )
    assert [t for t in hits("backend/apps/x/api.py", allow)] == ["a_kho", "clear_kho"], hits("backend/apps/x/api.py", allow)
    # file map cũ: chuỗi được miễn, định danh vẫn bị xét; file mock: chuỗi được miễn, định danh vẫn bị xét
    assert hits("backend/apps/ai/registry/legacy_ids.py", 'OLD = {"thu_mua": "purchasing"}\ndef lay_nhom(): pass\n') == ["lay_nhom"]
    mock_ts = 'export const DEMO_USER = "kho1";\nexport const khoList = [{ username: "giao2" }];\n'
    assert hits("erp-console/features/auth/mock.ts", mock_ts) == ["khoList"], hits("erp-console/features/auth/mock.ts", mock_ts)
    assert hits("erp-console/features/auth/auth.ts", mock_ts) == sorted(["kho1", "khoList", "giao2"])
    # từ chặn thêm theo glossary: mức nhạy cảm AI, giờ Việt Nam, cặp tiếng Việt phổ biến
    glossary = 'SENSITIVITY_CAO = 1\nVN_TZ = 2\ntodayVN = 3\nyear = currentYearVn\ntrang_thai = 1\nlevel = "trung_binh"\nchannel = gui = 2\nchan = 1\n'
    assert hits("backend/apps/x/api.py", glossary) == sorted(
        ["SENSITIVITY_CAO", "VN_TZ", "todayVN", "currentYearVn", "trang_thai", "trung_binh"]), hits("backend/apps/x/api.py", glossary)

    name_hits = [token for _l, token, _h in scan_path_name("backend/apps/common/tests/test_l7_bosung.py", blocklist)]
    assert name_hits == ["test_l7_bosung.py"], name_hits
    assert [t for _l, t, _h in scan_path_name("backend/apps/common/tests/test_undo_window.py", blocklist)] == []
    assert [t for _l, t, _h in scan_path_name("erp-console/features/cskh/CskhQueueView.tsx", blocklist)] == [
        "cskh", "CskhQueueView.tsx"]
    print("check_naming --self-test: OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Chặn định danh tiếng Việt mới trong code (P8b Lô 0).")
    parser.add_argument("--update", action="store_true", help="ghi lại baseline (chỉ cho phép giảm)")
    parser.add_argument("--report", action="store_true", help="in mọi vi phạm hiện có, theo file")
    parser.add_argument("--words", action="store_true", help="in tần suất từ bị chặn")
    parser.add_argument("--self-test", action="store_true", help="kiểm bộ quét bằng mẫu nhỏ")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()

    blocklist = Blocklist.load()
    current = scan_repo(blocklist)
    baseline = load_baseline()

    if args.report or args.words:
        if args.words:
            counter = Counter(word for items in current.values() for _l, _t, hit in items for word in hit.split(", "))
            for word, amount in counter.most_common():
                print(f"{amount:6d}  {word}")
        else:
            for rel, items in sorted(current.items()):
                print(f"{rel}  ({weight(items)})")
                for item in items:
                    print(format_violation(rel, item))
        print(f"Tổng: {sum(weight(v) for v in current.values())} vi phạm trong {len(current)} file.")
        if args.report:
            uses = allow_marker_lines()
            print(f"Dòng đang dùng `{ALLOW_MARKER}` (techlead soát): {len(uses)}")
            for rel, line_no, text in uses:
                print(f"  {rel}:{line_no}  {text.strip()}")
        return 0

    if args.update and not BASELINE_FILE.exists():  # lần đầu: chụp baseline tại HEAD
        counts = {rel: weight(items) for rel, items in current.items()}
        write_baseline(counts)
        print(f"Đã tạo baseline: {sum(counts.values())} vi phạm trong {len(counts)} file.")
        return 0

    failures, improved = evaluate(blocklist, baseline, current)

    if args.update:
        if failures:
            print("Từ chối --update: có file tăng vi phạm hoặc file mới có vi phạm (baseline chỉ được giảm).")
            report_failures(failures)
            return 1
        counts = {rel: weight(items) for rel, items in current.items()}
        renames = rename_map()
        for rel in list(counts):  # kế thừa trần từ đường dẫn cũ khi đã đổi chỗ
            if rel not in baseline and rel in renames and renames[rel] in baseline:
                counts[rel] = min(counts[rel], baseline[renames[rel]])
        write_baseline(counts)
        print(f"Đã ghi baseline: {sum(counts.values())} vi phạm trong {len(counts)} file "
              f"(trước đó {sum(baseline.values())} trong {len(baseline)} file).")
        return 0

    if failures:
        report_failures(failures)
        return 1

    total = sum(weight(v) for v in current.values())
    print(f"check_naming: OK - {total} vi phạm cũ trong {len(current)} file, không phát sinh mới.")
    if improved:
        print(f"  {len(improved)} file đã giảm vi phạm: chạy `python3 scripts/check_naming.py --update` để khoá.")
    return 0


def report_failures(failures) -> None:
    print("check_naming: PHÁT SINH tên tiếng Việt mới trong định danh (luật: 02c-giao-viec.md §1, dùng tên tiếng Anh).")
    for rel, allowed, violations in failures:
        if allowed is None:
            print(f"\n[file mới] {rel}")
        else:
            print(f"\n[tăng so với baseline {allowed}] {rel}")
        for item in violations:
            print(format_violation(rel, item))
    print("\nĐặt lại tên theo glossary (02c §1; skill caveve-domain, mục 'Đặt tên'). "
          "Dữ liệu/hằng tương thích có lý do: ghi `naming: allow - <lý do>` ở cuối dòng (không có lý do thì không được miễn) "
          "và nhờ techlead duyệt.")


if __name__ == "__main__":
    sys.exit(main())

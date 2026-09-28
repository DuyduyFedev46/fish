"""
Lọc dữ liệu đầu ra và cắt kích thước kết quả lệnh AI (02b §3, §4.3).

- SCRUB_PII_KEYS: lọc đệ quy kể cả với Chủ (H2, Bất biến 9).
- SCRUB_FREE_TEXT_KEYS: lọc chữ tự do (H10 — tránh Prompt Injection).
- SCRUB_COST_KEYS: lọc khoá giá vốn lưới 2 nếu thiếu view_costprice (Bất biến 1, H3).
- Cắt kết quả: tối đa AI_RESULT_MAX_ROWS (20) và AI_RESULT_MAX_CHARS (3000).
"""
import json
from decimal import Decimal
from django.conf import settings
from apps.ai.policy.rules import SCRUB_COST_KEYS, SCRUB_FREE_TEXT_KEYS, SCRUB_PII_KEYS


def _is_cost_authorized(user) -> bool:
    """Kiểm tra người dùng có quyền xem giá vốn không."""
    if not user or not user.is_authenticated:
        return False
    return (
        user.has_perm("accounts.view_costprice")
        or user.has_perm("inventory.view_costprice")
        or user.has_perm("reports.view_profitreport")
    )


def scrub_data(data, *, user, is_ai_read: bool = True):
    """
    Lọc đệ quy dict/list để bảo đảm an toàn:
    - Bỏ PII (kể cả với Chủ).
    - Bỏ chữ tự do nếu là lệnh đọc cho AI (tránh Prompt Injection).
    - Bỏ giá vốn nếu user không có quyền xem giá vốn.
    """
    has_cost_perm = _is_cost_authorized(user)

    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if k_lower in SCRUB_PII_KEYS:
                continue
            if is_ai_read and k_lower in SCRUB_FREE_TEXT_KEYS:
                continue
            if not has_cost_perm and k_lower in SCRUB_COST_KEYS:
                continue
            cleaned[k] = scrub_data(v, user=user, is_ai_read=is_ai_read)
        return cleaned

    if isinstance(data, (list, tuple)):
        return [scrub_data(item, user=user, is_ai_read=is_ai_read) for item in data]

    if isinstance(data, Decimal):
        return str(data)

    return data


def truncate_read_result(data, max_rows: int | None = None, max_chars: int | None = None):
    """
    Cắt danh sách kết quả đọc theo số dòng và số ký tự tối đa (02b §4.3).
    Trả về (rows, total, truncated).
    """
    if max_rows is None:
        max_rows = getattr(settings, "AI_RESULT_MAX_ROWS", 20)
    if max_chars is None:
        max_chars = getattr(settings, "AI_RESULT_MAX_CHARS", 3000)

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and "results" in data and isinstance(data["results"], list):
        items = data["results"]
    elif isinstance(data, dict) and "rows" in data and isinstance(data["rows"], list):
        items = data["rows"]
    elif isinstance(data, dict):
        items = [data]
    else:
        items = [{"value": data}]

    total = len(items)
    rows = items[:max_rows]
    truncated = total > max_rows

    # Giới hạn số ký tự (max_chars)
    payload_str = json.dumps(rows, ensure_ascii=False)
    if len(payload_str) > max_chars:
        truncated = True
        # Cắt dần từng dòng từ cuối lên
        while len(rows) > 1 and len(json.dumps(rows, ensure_ascii=False)) > max_chars:
            rows.pop()
        # Nếu chỉ còn 1 dòng nhưng vẫn vượt max_chars, cắt ngắn chuỗi bên trong dòng
        if len(json.dumps(rows, ensure_ascii=False)) > max_chars and rows:
            single = rows[0]
            if isinstance(single, dict):
                shortened = {}
                for k, v in single.items():
                    if isinstance(v, str) and len(v) > 100:
                        shortened[k] = v[:97] + "..."
                    else:
                        shortened[k] = v
                rows = [shortened]

    return rows, total, truncated

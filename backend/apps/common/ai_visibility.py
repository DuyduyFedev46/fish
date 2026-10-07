"""
Một chỗ duy nhất quyết định ẩn/hiện phần AI ở BE (lô dọn chữ AI, W39, BR-AI-17).

Nguồn thật là cờ môi trường `settings.AI_ENABLED`, KHÔNG phải `is_ai_enabled()` (gồm cả công tắc tắt khẩn của Chủ):
nếu dùng công tắc tắt khẩn để ẩn giao diện thì Chủ tắt xong sẽ mất màn cài đặt để bật lại.
Chỉ ẩn khi ĐỌC, không xoá `AuditLog` (append-only, BR-PQ-04/05): bật cờ là hiện lại đủ.
"""
from django.conf import settings
from django.db.models import Q

# Duy 08/10 câu 2: dòng cài đặt, chính sách AI và việc AI xếp lịch bị hạ về đề xuất cũng ẩn khi AI tắt.
AI_ADMIN_ACTION_PREFIXES = ("ai_config_", "ai_policy_", "downgrade_")


def ai_features_enabled() -> bool:
    return bool(getattr(settings, "AI_ENABLED", False))


def exclude_ai_audit_rows(qs):
    """
    Khi AI tắt ẩn các dòng DO AI làm: `actor_kind="ai"` và dòng Hệ thống thuộc vòng đời đề xuất AI
    (`actor_kind="system"` có `proposal_ref`), cùng dòng cài đặt/chính sách AI (`ai_config_*`, `ai_policy_*`) và
    `downgrade_*`. GIỮ dòng nghiệp vụ do người làm: duyệt/từ chối đề xuất, dòng nghiệp vụ do người duyệt thực thi
    (tự gắn `proposal_ref`).
    Gọi TRÊN queryset, trước khi cắt `limit`.
    """
    if ai_features_enabled():
        return qs
    admin_rows = Q()
    for prefix in AI_ADMIN_ACTION_PREFIXES:
        admin_rows |= Q(action__startswith=prefix)
    return qs.exclude(Q(actor_kind="ai") | (Q(actor_kind="system") & ~Q(proposal_ref="")) | admin_rows)

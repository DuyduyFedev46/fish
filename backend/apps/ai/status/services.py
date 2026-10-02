"""
Trạng thái AI cho ERP (S05, BR-AI-10, Lô bổ sung A #1).

`ai_enabled` đúng bằng điều kiện mà `effective_level` dùng để trả "OFF" toàn cục:
công tắc môi trường `AI_ENABLED` VÀ Chủ chưa tắt khẩn (`AiPolicyVersion.global_mode != "off"`, DW-13-AC2).
Không có thông tin nhạy cảm: chỉ cờ bật/tắt, thông tin model công khai, và ngân sách (chỉ Chủ).
"""
from django.conf import settings

from apps.ai.models.policy import AiPolicyVersion

BUDGET_PERMISSION = "ai.manage_ai_policy"  # quyền chỉ Chủ có (DW-13-AC5)


def is_ai_enabled() -> bool:
    if not getattr(settings, "AI_ENABLED", False):
        return False
    policy = AiPolicyVersion.objects.order_by("-version").first()
    return not (policy and policy.global_mode == AiPolicyVersion.GlobalMode.OFF)


def _model_info():
    name = (getattr(settings, "AI_MODEL_NAME", "") or "").strip()
    url = (getattr(settings, "AI_MODEL_GGUF_URL", "") or "").strip()
    if not name or not url:
        return None  # chưa chốt model (S17): FE không tải gì
    version = (getattr(settings, "AI_MODEL_VERSION", "") or "").strip() or "1"
    return {"name": name, "version": version, "gguf_url": url}


def _budget_info():
    """Chưa có sổ dùng cloud (AiUsageLedger, S04) nên mức đã dùng là 0; trạng thái tính theo ngưỡng cảnh báo."""
    limit = int(getattr(settings, "AI_CLOUD_MONTHLY_BUDGET_VND", 200000))
    alert_pct = int(getattr(settings, "AI_CLOUD_ALERT_PCT", 80))
    spent = 0
    if limit > 0 and spent >= limit:
        state = "blocked"
    elif limit > 0 and spent * 100 >= limit * alert_pct:
        state = "warning"
    else:
        state = "ok"
    return {"spent_vnd": spent, "limit_vnd": limit, "status": state}


def build_status(user) -> dict:
    if not is_ai_enabled():
        return {"ai_enabled": False, "cloud_enabled": False, "model": None, "budget": None}
    return {
        "ai_enabled": True,
        "cloud_enabled": bool(getattr(settings, "AI_CLOUD_ENABLED", False)),
        "model": _model_info(),
        "budget": _budget_info() if user.has_perm(BUDGET_PERMISSION) else None,
    }

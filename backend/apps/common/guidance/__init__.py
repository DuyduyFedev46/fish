"""
Module Guidance (Tiếp theo · Đã làm) — Dựng khung hướng dẫn tất định cho ERP Cá Về.
"""
from apps.common.guidance.steps import Missing, NextStep, Why, step_to_dict
from apps.common.guidance.reasons import get_reason
from apps.common.guidance.timeline import format_guidance_timeline
from apps.common.guidance.api import register_guidance, GuidanceView

__all__ = [
    "Missing",
    "Why",
    "NextStep",
    "step_to_dict",
    "get_reason",
    "format_guidance_timeline",
    "register_guidance",
    "GuidanceView",
]

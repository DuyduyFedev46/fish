#!/usr/bin/env python3
"""Chốt chặn lệnh nguy hiểm cho mọi AI (Claude Code và Antigravity/Gemini), Duy duyệt 15/11.

Chạy trước mỗi lệnh shell của AI (hook PreToolUse). Đọc JSON từ stdin, trả quyết định:
  - CHẶN HẲN: việc không lấy lại được (force-push, xoá project/bucket/DB, DROP DATABASE, rm -rf /).
  - HỎI DUY: việc đụng production hoặc xoá dữ liệu (đọc secret production, deploy production,
    xoá dịch vụ Cloud Run, DROP TABLE, TRUNCATE, DELETE không WHERE, git reset --hard...).
  - Còn lại: để luồng hỏi quyền bình thường của công cụ quyết định.

Claude Code: `.claude/settings.json` (hook PreToolUse, matcher Bash).
Antigravity: `.agents/hooks.json` (PreToolUse, matcher run_command).
Sửa luật thì sửa danh sách bên dưới và chạy `python3 scripts/test_ai_guard.py`.
"""
from __future__ import annotations

import json
import re
import sys

FLAGS = re.IGNORECASE | re.DOTALL

# (mẫu, lý do) — chặn hẳn, AI không được tự làm dù người đã cho phép chung.
DENY_RULES: list[tuple[str, str]] = [
    (r"\bgit\s+push\b[^|;&]*(\s--force\b|\s--force-with-lease\b|\s-f\b|\s\+\S+)", "force-push viết lại lịch sử"),
    (r"\bgit\s+push\b[^|;&]*\s--delete\b|\bgit\s+push\b[^|;&]*\s:\S+", "xoá nhánh trên GitHub"),
    (r"\bgcloud\s+projects\s+delete\b", "xoá cả project GCP"),
    (r"\bgcloud\s+(storage\s+buckets\s+delete|sql\s+instances\s+delete)\b|\bgsutil\s+rb\b", "xoá bucket hoặc DB"),
    (r"\b(gcloud\s+storage\s+rm|gsutil\s+(-m\s+)?rm)\b[^|;&]*\s(-r|--recursive)\b", "xoá hàng loạt trong bucket"),
    (r"\bdrop\s+(database|schema)\b", "xoá cả DB/schema"),
    (r"\bfirebase\s+(hosting:disable|projects:delete)\b", "tắt hoặc xoá Firebase"),
    (r"\bgh\s+repo\s+delete\b|\bgh\s+api\b[^|;&]*-X\s*DELETE\b[^|;&]*/repos/[^/\s]+/[^/\s]+/?(\s|$)", "xoá repo GitHub"),
    (r"\brm\s+(-[a-z]*r[a-z]*f[a-z]*|-[a-z]*f[a-z]*r[a-z]*)\s+(--\s+)?(/|~|\$HOME|\.|\.\.|\*)(\s|$|/\s|/\*)", "rm -rf thư mục gốc/repo"),
]

# (mẫu, lý do) — phải hỏi Duy từng lần.
ASK_RULES: list[tuple[str, str]] = [
    (r"\bsecrets\s+versions\s+access\b[^|;&]*(cangca-supabase-database-url|cangca-prod-|sepay-live)", "đọc secret production"),
    (r"\bgcloud\s+run\s+(deploy|services\s+update|services\s+update-traffic)\s+cangca-(api|adapter)(\s|$)", "đổi dịch vụ production"),
    (r"\bgcloud\s+run\s+jobs\s+(execute|update|deploy)\s+cangca-(migrate|ttl|batch-status)(\s|$)", "chạy hoặc đổi job production"),
    (r"\bfirebase\s+deploy\b(?![^|;&]*staging)", "deploy Firebase production"),
    (r"\bgcloud\b[^|;&]*\s(delete|destroy|remove-iam-policy-binding|disable)\b", "xoá hoặc gỡ quyền trên GCP"),
    (r"\bgcloud\s+(projects|organizations)\s+set-iam-policy\b", "ghi đè IAM"),
    (r"\bdrop\s+table\b|\btruncate\b(\s+table)?\s+\w", "xoá bảng dữ liệu"),
    (r"\bdelete\s+from\s+\w+(?![^;]*\bwhere\b)", "DELETE không có WHERE"),
    (r"\bmanage\.py\s+(flush|reset_db)\b|\bmanage\.py\s+migrate\s+\w+\s+zero\b", "xoá dữ liệu Django"),
    (r"\bgit\s+(reset\s+--hard|clean\s+-[a-z]*f[a-z]*|checkout\s+--\s+\.|restore\s+(--staged\s+)?\.\s*$|branch\s+-D)\b", "bỏ thay đổi hoặc xoá nhánh git"),
]

def command_from(payload: dict) -> tuple[str, str]:
    """Trả (công cụ, lệnh) cho cả định dạng Claude Code lẫn Antigravity."""
    if "toolCall" in payload:  # Antigravity
        call = payload.get("toolCall") or {}
        return "antigravity", str((call.get("args") or {}).get("CommandLine", ""))
    tool_input = payload.get("tool_input") or {}
    return "claude", str(tool_input.get("command", ""))


def decide(command: str) -> tuple[str, str]:
    """Trả ("deny" | "ask" | "pass", lý do)."""
    for pattern, reason in DENY_RULES:
        if re.search(pattern, command, FLAGS):
            return "deny", reason
    for pattern, reason in ASK_RULES:
        if re.search(pattern, command, FLAGS):
            return "ask", reason
    return "pass", ""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        payload = {}
    tool, command = command_from(payload)
    decision, reason = decide(command)
    message = f"ai_guard: {reason}. Lệnh này cần Duy duyệt (AGENTS.md mục an toàn)." if reason else ""
    if tool == "antigravity":
        mapping = {"deny": "deny", "ask": "force_ask", "pass": "ask"}
        out = {"decision": mapping[decision]}
        if message:
            out["reason"] = message
        print(json.dumps(out, ensure_ascii=False))
        return 0
    if decision == "pass":
        return 0
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": message,
    }}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

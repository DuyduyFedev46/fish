#!/usr/bin/env python3
"""Test bảng cho scripts/ai_guard.py (chốt chặn lệnh nguy hiểm của AI). Chạy: python3 scripts/test_ai_guard.py"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ai_guard import decide  # noqa: E402

CASES = [
    # chặn hẳn
    ("git push --force origin main", "deny"),
    ("git push -f origin claude/x", "deny"),
    ("git push origin +main", "deny"),
    ("git push --force-with-lease", "deny"),
    ("git push origin --delete claude/x", "deny"),
    ("gcloud projects delete keolai-63ec1", "deny"),
    ("gcloud storage buckets delete gs://cangca-db-nightly-keolai", "deny"),
    ("gcloud sql instances delete abc", "deny"),
    ("gsutil rb gs://x", "deny"),
    ("gsutil -m rm -r gs://cangca-item-images/", "deny"),
    ("gcloud storage rm --recursive gs://x/*", "deny"),
    ("psql \"$DB\" -c 'DROP DATABASE postgres'", "deny"),
    ("psql -c 'drop schema public cascade'", "deny"),
    ("rm -rf /", "deny"),
    ("rm -rf ~", "deny"),
    ("rm -rf .", "deny"),
    ("rm -fr *", "deny"),
    ("gh repo delete DuyduyFedev46/fish --yes", "deny"),
    ("firebase hosting:disable --project keolai-63ec1", "deny"),
    # hỏi Duy
    ("export DATABASE_URL=$(gcloud secrets versions access latest --secret=cangca-supabase-database-url)", "ask"),
    ("gcloud secrets versions access latest --secret=cangca-prod-internal-token", "ask"),
    ("gcloud run deploy cangca-api --image x --region asia-southeast1", "ask"),
    ("gcloud run services update cangca-adapter --region asia-southeast1", "ask"),
    ("gcloud run services update-traffic cangca-api --to-latest", "ask"),
    ("gcloud run jobs execute cangca-migrate --region asia-southeast1 --wait", "ask"),
    ("firebase deploy --only hosting --project keolai-63ec1", "ask"),
    ("gcloud run services delete cangca-api-staging", "ask"),
    ("gcloud projects remove-iam-policy-binding keolai-63ec1 --member=x --role=y", "ask"),
    ("psql -c 'DROP TABLE sales_salesorder'", "ask"),
    ("psql -c 'TRUNCATE sales_salesorder'", "ask"),
    ("psql -c 'DELETE FROM sales_salesorder'", "ask"),
    ("python manage.py flush --noinput", "ask"),
    ("git reset --hard origin/main", "ask"),
    ("git clean -fd", "ask"),
    ("git branch -D claude/x", "ask"),
    # bình thường
    ("git push origin main", "pass"),
    ("git push origin claude/shop-ui", "pass"),
    ("export DATABASE_URL=$(gcloud secrets versions access latest --secret=cangca-staging-database-url)", "pass"),
    ("gcloud run deploy cangca-api-staging --image x", "pass"),
    ("gcloud run services update cangca-adapter-staging --region asia-southeast1", "pass"),
    ("gcloud run jobs execute cangca-migrate-staging --wait", "pass"),
    ("firebase deploy --only hosting --config firebase.staging.json --project keolai-63ec1", "pass"),
    ("psql -c \"DELETE FROM cart WHERE id = 1\"", "pass"),
    ("rm -rf node_modules .next", "pass"),
    ("rm -rf ./build", "pass"),
    ("git status && git log --oneline -3", "pass"),
    ("cd backend && .venv/bin/python manage.py test --parallel 1", "pass"),
    ("grep -rn 'truncate' frontend/lib", "pass"),
]


def run_hook(payload: dict) -> str:
    script = Path(__file__).resolve().parent / "ai_guard.py"
    return subprocess.run([sys.executable, str(script)], input=json.dumps(payload),
                          capture_output=True, text=True, check=True).stdout.strip()


def main() -> int:
    failed = 0
    for command, want in CASES:
        got, _ = decide(command)
        if got != want:
            failed += 1
            print(f"SAI: {command!r} → {got}, cần {want}")
    # định dạng vào/ra của hai công cụ
    claude_deny = json.loads(run_hook({"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}))
    assert claude_deny["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert run_hook({"tool_name": "Bash", "tool_input": {"command": "ls"}}) == ""
    assert json.loads(run_hook({"toolCall": {"args": {"CommandLine": "ls"}}}))["decision"] == "ask"
    assert json.loads(run_hook({"toolCall": {"args": {"CommandLine": "git reset --hard"}}}))["decision"] == "force_ask"
    assert json.loads(run_hook({"toolCall": {"args": {"CommandLine": "gcloud projects delete x"}}}))["decision"] == "deny"
    print(f"{len(CASES) - failed}/{len(CASES)} ca đúng, định dạng Claude và Antigravity đúng")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

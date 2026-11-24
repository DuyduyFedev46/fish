#!/usr/bin/env python3
"""Giữ liên kết skill cho worker Gemini (Antigravity chạy qua Orca) khớp với `.claude/skills/`.

Từ 24/11/2026 (Duy chốt) Claude Opus 5.5 trong Orca là điều phối viên duy nhất, Gemini chỉ làm worker
(`doc/ops/orca-worker.md`). Worker đọc file vai trực tiếp ở `.claude/agents/`, nên không còn sinh bản
`.agents/agents/` hay `.gemini/commands/`. Script chỉ còn:
  - `.claude/skills/<tên>/` → liên kết `.agents/skills/<tên>` (Antigravity tự nạp), `.gemini/skills` trỏ tới
  - dọn bản sinh tự động cũ (agent, lệnh, workflow) nếu còn sót

Cách dùng (Python 3 stdlib, chạy từ bất kỳ đâu trong repo):
  python3 scripts/sync_ai_workspace.py          # ghi lại liên kết cho khớp `.claude/skills/`
  python3 scripts/sync_ai_workspace.py --check  # chỉ kiểm, lệch thì exit 1 (CI chạy lệnh này)
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLAUDE = ROOT / ".claude"
AGENTS_DIR = ROOT / ".agents"
GEMINI_DIR = ROOT / ".gemini"


def desired_state() -> tuple[dict[Path, str], dict[Path, str]]:
    """(file cần có → nội dung, liên kết cần có → đích tương đối). Hiện chỉ còn liên kết skill."""
    files: dict[Path, str] = {}
    links: dict[Path, str] = {}
    for skill in sorted(p for p in (CLAUDE / "skills").iterdir() if (p / "SKILL.md").is_file()):
        links[AGENTS_DIR / "skills" / skill.name] = f"../../.claude/skills/{skill.name}"
    links[GEMINI_DIR / "skills"] = "../.agents/skills"
    return files, links


def stale_items(files: dict[Path, str], links: dict[Path, str]) -> list[Path]:
    """Bản Gemini cũ không còn dùng: agent và lệnh sinh tự động, skill-lệnh, liên kết thừa, workflow kiểu cũ."""
    stale: list[Path] = []
    for path in (AGENTS_DIR / "agents", GEMINI_DIR / "agents", GEMINI_DIR / "commands", AGENTS_DIR / "workflows"):
        if path.is_symlink() or path.exists():
            stale.append(path)
    skills_dir = AGENTS_DIR / "skills"
    if skills_dir.is_dir() and not skills_dir.is_symlink():
        for path in sorted(skills_dir.iterdir()):
            if path not in links:
                stale.append(path)
    return stale


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="chỉ kiểm, không ghi")
    args = parser.parse_args()
    files, links = desired_state()
    problems: list[str] = []

    for path, content in files.items():
        current = path.read_text(encoding="utf-8") if path.is_file() and not path.is_symlink() else None
        if current == content:
            continue
        problems.append(f"lệch: {path.relative_to(ROOT)}")
        if not args.check:
            if path.is_symlink():
                path.unlink()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    for path, target in links.items():
        if path.is_symlink() and os.readlink(path) == target:
            continue
        problems.append(f"liên kết lệch: {path.relative_to(ROOT)} -> {target}")
        if not args.check:
            if path.is_symlink() or path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.symlink_to(target)

    for path in stale_items(files, links):
        problems.append(f"thừa (không còn nguồn trong .claude/): {path.relative_to(ROOT)}")
        if not args.check:
            if path.is_symlink() or path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path)

    if args.check:
        if problems:
            print("sync_ai_workspace: LỆCH giữa .claude/skills/ và liên kết cho worker. Chạy `python3 scripts/sync_ai_workspace.py` rồi commit.")
            print("\n".join(f"  - {p}" for p in problems))
            return 1
        print(f"sync_ai_workspace: OK - {len(files)} file, {len(links)} liên kết khớp .claude/.")
        return 0
    print(f"sync_ai_workspace: đã cập nhật {len(problems)} mục." if problems else "sync_ai_workspace: đã khớp, không đổi gì.")
    for p in problems:
        print(f"  - {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

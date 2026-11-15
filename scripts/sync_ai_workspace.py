#!/usr/bin/env python3
"""Đồng bộ bộ agent, skill và lệnh dùng chung giữa Claude Code và Gemini/Antigravity.

Nguồn duy nhất nằm ở `.claude/`:
  - `.claude/agents/<tên>.md`   → `.agents/agents/<tên>.md` (Antigravity, Gemini CLI qua `.gemini/agents`)
  - `.claude/skills/<tên>/`     → liên kết `.agents/skills/<tên>` (Gemini CLI qua `.gemini/skills`)
  - `.claude/commands/<tên>.md` → skill `.agents/skills/<tên>/SKILL.md` (Antigravity gọi bằng /<tên>)
                                  và `.gemini/commands/<tên>.toml` (Gemini CLI)
  - skill `feature` (workflow đội) → thêm `.gemini/commands/feature.toml`

Luật chung cho mọi AI nằm ở `AGENTS.md` (Claude đọc qua `@AGENTS.md` trong `CLAUDE.md`).

Cách dùng (Python 3 stdlib, chạy từ bất kỳ đâu trong repo):
  python3 scripts/sync_ai_workspace.py          # ghi lại bản Gemini cho khớp `.claude/`
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
MARKER = "<!-- Sinh tự động bởi scripts/sync_ai_workspace.py từ {src}. Đừng sửa file này: sửa nguồn rồi chạy lại script. -->"
TOML_MARKER = "# Sinh tự động bởi scripts/sync_ai_workspace.py từ {src}. Đừng sửa file này."
GEMINI_AGENT_DEFAULTS = {"kind": "local", "model": "inherit", "temperature": "0.3", "max_turns": "80", "timeout_mins": "40"}
WORKFLOW_SKILL = "feature"


def split_front_matter(text: str) -> tuple[dict, list[str], str]:
    """Trả về (khoá đơn, danh sách skill, thân bài). Chỉ đọc đủ cho frontmatter của dự án này."""
    if not text.startswith("---\n"):
        return {}, [], text
    end = text.index("\n---", 4)
    head, body = text[4:end], text[end + 4:].lstrip("\n")
    meta: dict[str, str] = {}
    skills: list[str] = []
    current = None
    for line in head.splitlines():
        if line.startswith("  - ") and current == "skills":
            skills.append(line[4:].strip())
            continue
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            current = key.strip()
            if value.strip():
                meta[current] = value.strip()
    return meta, skills, body


def quote_yaml(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def gemini_agent(src: Path) -> str:
    meta, skills, body = split_front_matter(src.read_text(encoding="utf-8"))
    name = meta.get("name", src.stem)
    lines = ["---", f"name: {name}", f"description: {quote_yaml(meta.get('description', '').strip(chr(34)))}"]
    lines += [f"{k}: {v}" for k, v in GEMINI_AGENT_DEFAULTS.items()]
    lines += ["---", "", MARKER.format(src=src.relative_to(ROOT).as_posix()), ""]
    if skills:
        paths = ", ".join(f"`.agents/skills/{s}/SKILL.md`" for s in skills)
        lines += [f"**Trước khi làm, đọc skill:** {paths}.", ""]
    return "\n".join(lines) + body.rstrip() + "\n"


def command_skill(src: Path) -> str:
    meta, _, _ = split_front_matter(src.read_text(encoding="utf-8"))
    rel = src.relative_to(ROOT).as_posix()
    desc = meta.get("description", f"Lệnh /{src.stem} của dự án Cá Về").strip('"')
    return (
        f"---\nname: {src.stem}\ndescription: {quote_yaml(desc)}\n---\n\n{MARKER.format(src=rel)}\n\n"
        f"Đây là lệnh `/{src.stem}` dùng chung với Claude Code. Đọc toàn bộ `{rel}` rồi làm đúng theo đó, "
        "tuân thủ `AGENTS.md`. Chỗ nào file ghi `$ARGUMENTS` là lời Duy gõ kèm lệnh.\n"
    )


def command_toml(name: str, rel: str, desc: str) -> str:
    desc = desc.replace('"', "'")
    return (
        f"{TOML_MARKER.format(src=rel)}\n"
        f'description = "{desc}"\n\n'
        'prompt = """\n'
        f"Đọc toàn bộ `{rel}` rồi làm đúng theo đó, tuân thủ `AGENTS.md` và `GEMINI.md`.\n"
        "Lời Duy gõ kèm lệnh: {{args}}\n"
        '"""\n'
    )


def desired_state() -> tuple[dict[Path, str], dict[Path, str]]:
    """(file cần có → nội dung, liên kết cần có → đích tương đối)."""
    files: dict[Path, str] = {}
    links: dict[Path, str] = {}
    for src in sorted((CLAUDE / "agents").glob("*.md")):
        files[AGENTS_DIR / "agents" / src.name] = gemini_agent(src)
    for skill in sorted(p for p in (CLAUDE / "skills").iterdir() if (p / "SKILL.md").is_file()):
        links[AGENTS_DIR / "skills" / skill.name] = f"../../.claude/skills/{skill.name}"
    for src in sorted((CLAUDE / "commands").glob("*.md")):
        if (CLAUDE / "skills" / src.stem).exists():
            sys.exit(f"Trùng tên: lệnh {src.name} và skill {src.stem}. Đổi tên một bên.")
        rel = src.relative_to(ROOT).as_posix()
        meta, _, _ = split_front_matter(src.read_text(encoding="utf-8"))
        files[AGENTS_DIR / "skills" / src.stem / "SKILL.md"] = command_skill(src)
        files[GEMINI_DIR / "commands" / f"{src.stem}.toml"] = command_toml(
            src.stem, rel, meta.get("description", src.stem).strip('"'))
    workflow = CLAUDE / "skills" / WORKFLOW_SKILL / "SKILL.md"
    files[GEMINI_DIR / "commands" / f"{WORKFLOW_SKILL}.toml"] = command_toml(
        WORKFLOW_SKILL, workflow.relative_to(ROOT).as_posix(),
        "Chạy workflow đội dự án Cá Về cho một yêu cầu của Duy (chọn luồng, giao agent, kiểm chứng, QA)")
    links[GEMINI_DIR / "agents"] = "../.agents/agents"
    links[GEMINI_DIR / "skills"] = "../.agents/skills"
    return files, links


def is_generated(path: Path) -> bool:
    try:
        return "Sinh tự động bởi scripts/sync_ai_workspace.py" in path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False


def stale_items(files: dict[Path, str], links: dict[Path, str]) -> list[Path]:
    """Bản Gemini cũ không còn nguồn: agent, skill liên kết, lệnh, workflow kiểu cũ của Antigravity."""
    stale: list[Path] = []
    for path in sorted((AGENTS_DIR / "agents").glob("*.md")):
        if path not in files:
            stale.append(path)
    skills_dir = AGENTS_DIR / "skills"
    if skills_dir.is_dir() and not skills_dir.is_symlink():
        for path in sorted(skills_dir.iterdir()):
            if path not in links and (path / "SKILL.md") not in files:
                stale.append(path)
    for path in sorted((GEMINI_DIR / "commands").glob("*.toml")):
        if path not in files:
            stale.append(path)
    workflows = AGENTS_DIR / "workflows"
    if workflows.exists():
        stale.append(workflows)
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
            print("sync_ai_workspace: LỆCH giữa .claude/ và bản Gemini. Chạy `python3 scripts/sync_ai_workspace.py` rồi commit.")
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

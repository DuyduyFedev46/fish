#!/bin/sh
# Tạo liên kết để Antigravity / Gemini CLI dùng chung skill và agent với Claude Code.
# Nguồn gốc duy nhất: .claude/skills/ (skill) và .agents/agents/ (agent). Chạy lại bao nhiêu lần cũng được.
set -e
cd "$(dirname "$0")/.."

mkdir -p .agents/skills .gemini
for s in caveve-domain django-drf-patterns nextjs-shop-patterns tdd-workflow e2e-playwright \
         caveve-ui impeccable emil-design-eng baseline-ui fixing-accessibility \
         web-design-guidelines ui-ux-pro-max mobile-native fixing-motion-performance; do
  if [ -d ".claude/skills/$s" ]; then
    ln -sfn "../../.claude/skills/$s" ".agents/skills/$s"
  fi
done
ln -sfn ../.agents/agents .gemini/agents

echo "Skill: $(ls .agents/skills | wc -l | tr -d ' ') liên kết trong .agents/skills/"
echo "Agent (Gemini CLI): .gemini/agents -> .agents/agents"

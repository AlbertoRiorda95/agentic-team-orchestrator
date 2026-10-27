#!/bin/bash
# scripts/hooks/lint-frontend.sh: lint only the file that was just edited
# (web, mobile and packages). Skipped until ESLint is installed.
INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
[ -x node_modules/.bin/eslint ] || exit 0
case "$FILE" in
  *.ts|*.tsx|*.js|*.jsx) node_modules/.bin/eslint --fix "$FILE" >/dev/null 2>&1 || true ;;
esac
exit 0

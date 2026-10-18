#!/bin/bash
# .claude/hooks/gate-test.sh
# A task cannot be closed while `make test` fails. Skipped until the Makefile exists.
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
[ -f Makefile ] || exit 0
LOG="${TMPDIR:-/tmp}/gate-test.log"
if ! make test > "$LOG" 2>&1; then
  echo "Task cannot be closed: the test suite fails." >&2
  tail -n 30 "$LOG" >&2
  exit 2
fi
exit 0

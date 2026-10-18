#!/bin/bash
# Installs the recommended skills (guide section 4.3) into the project.
set -euo pipefail
npx skills add anthropics/skills -s frontend-design -s webapp-testing -a claude-code -y
npx skills add vercel-labs/agent-skills -s web-design-guidelines -s vercel-react-best-practices -s vercel-react-native-skills -a claude-code -y
npx skills add mattpocock/skills -s tdd -s diagnosing-bugs -a claude-code -y
npx skills add fastapi/fastapi -s fastapi -a claude-code -y
npx skills add supabase/agent-skills -s supabase-postgres-best-practices -a claude-code -y
npx skills add getsentry/skills -s security-review -s code-simplifier -s gha-security-review -a claude-code -y
npx skills add wshobson/agents -s api-design-principles -s github-actions-templates -a claude-code -y

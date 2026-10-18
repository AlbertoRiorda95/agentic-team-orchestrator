#!/bin/bash
# Creates the agent:<role> labels used by the agents.yml workflow on GitHub.
# Requires an authenticated GitHub CLI (gh auth login).
set -euo pipefail
for r in designer frontend backend optimizer devops security team; do
  gh label create "agent:$r" --description "Task for the $r agent" --color 5319e7 --force
done
gh label create "alignment-needed" --description "An agent changed something other roles rely on" --color d93f0b --force

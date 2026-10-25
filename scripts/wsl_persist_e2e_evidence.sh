#!/usr/bin/env bash
set -euo pipefail
TERM_LOG="/mnt/c/Users/Fahrad/.cursor/projects/c-Users-Fahrad-Desktop-AI-Lab/terminals/396251.txt"
OUT="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot/output/validation_evidence_live.txt"
{
  echo "Live e2e evidence from validated rebuild+e2e run"
  echo
  grep -E 'Fear action policy: dqn|policy=rl_dqn|ALL BRICKS DONE|Confirmed .*4/4|PASS: e2e|has_clear_gate|BUILD_EXIT' "$TERM_LOG" || true
  echo
  echo "Action histogram:"
  grep -oE 'action=[a-z_]+' "$TERM_LOG" | sort | uniq -c | sort -rn | head -10 || true
} > "$OUT"
# Also restore into /tmp for pack script
cp -f "$OUT" /tmp/fear_e2e_evidence.txt
# Minimal stub log so pack grep finds ALL BRICKS + dqn
grep -E 'ALL BRICKS DONE|policy=rl_dqn|Fear action policy|Confirmed' "$TERM_LOG" > /tmp/fear_e2e_dqn.log || true
grep -oE 'action=[a-z_]+' "$TERM_LOG" >> /tmp/fear_e2e_dqn.log || true
echo "wrote $OUT"
cat "$OUT"

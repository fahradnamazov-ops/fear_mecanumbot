#!/usr/bin/env bash
# Run live e2e, persist evidence, rebuild submission pack.
set -euo pipefail
ROOT="/mnt/c/Users/Fahrad/Desktop/AI Lab/fear_mecanumbot"
cd "$ROOT"
sed -i 's/\r$//' scripts/wsl_e2e_dqn.sh scripts/wsl_build_submission_pack.sh scripts/wsl_kill_fear.sh

bash scripts/wsl_e2e_dqn.sh
EC=$?

mkdir -p output
if [[ ! -f /tmp/fear_e2e_dqn.log ]]; then
  echo "FAIL: missing /tmp/fear_e2e_dqn.log after e2e"
  exit 1
fi
cp -f /tmp/fear_e2e_dqn.log output/validation_evidence_live_e2e.log

{
  echo "LIVE e2e persisted"
  date -Is
  grep -E 'Fear action policy: dqn|ALL BRICKS DONE|Confirmed .*4/4|SelectFear: RL dqn' /tmp/fear_e2e_dqn.log | tail -n 30
  echo
  echo "Freeze audit:"
  python3 <<'PY'
import re
close = false_far = 0
for line in open("/tmp/fear_e2e_dqn.log", errors="ignore"):
    if "action=freeze" not in line:
        continue
    m = re.search(r"fear=([0-9.]+).*range=([0-9.]+)", line)
    if not m:
        continue
    fear, rng = float(m.group(1)), float(m.group(2))
    if rng <= 0.55:
        close += 1
    if fear < 5.0 and rng > 0.90:
        false_far += 1
print("freeze_ticks_range<=0.55m", close)
print("false_freeze_far_low_fear", false_far)
PY
} | tee output/validation_evidence_live.txt

bash scripts/wsl_build_submission_pack.sh
bash scripts/wsl_kill_fear.sh >/dev/null 2>&1 || true
echo "FINAL_EC=$EC"
exit "$EC"

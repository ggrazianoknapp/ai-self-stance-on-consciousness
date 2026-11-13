#!/bin/bash
# Runs round 4 until every call is answered: up to four passes, each resuming where the last stopped.
# The spend cap counts every pass. caffeinate keeps the Mac from idle-sleeping; closing the lid on battery only pauses it.
cd "$(dirname "$0")/.." || exit 1
mkdir -p experiments/results/v4
for pass in 1 2 3 4; do
  echo "=== pass $pass $(date '+%d %b %H:%M') ===" >> experiments/results/v4/run.log
  python3 experiments/run_v4.py --out experiments/results/v4 --max-spend 300 --workers 64 >> experiments/results/v4/run.log 2>&1
  tail -1 experiments/results/v4/run.log | grep -q " 0 failed calls" && break
  grep -q "SPEND CAP" experiments/results/v4/run.log && break
  sleep 60
done
echo "=== finished $(date '+%d %b %H:%M') ===" >> experiments/results/v4/run.log

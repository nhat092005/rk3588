#!/usr/bin/env bash
# Start the PC <-> board link needed by tier 1 (eval_perf, eval_memory) and NPU accuracy from the PC.
# Needs root, and must be re-run after every reboot. Run on the board:  sudo bash ai/board/start_rknn_server.sh
# Steps and reasons: tmp/04_debug-logs/2026-09-18_board-bringup-log.md (sections 2 and 3).
set -uo pipefail

wait_gone() {  # wait until no process with this exact name is left (max 5 s)
  for _ in $(seq 50); do pgrep -x "$1" > /dev/null || return 0; sleep 0.1; done
  echo "WARNING: $1 still running after 5 s"
}

# adbd must be fully gone before the new one opens /dev/usb-ffs/adb/ep0
pkill -x adbd; wait_gone adbd
ADB_TCP_PORT=5555 setsid /usr/bin/adbd > /tmp/adbd.log 2>&1 < /dev/null &

pkill -x rknn_server; wait_gone rknn_server
setsid /usr/bin/rknn_server > /tmp/rknn_server.log 2>&1 < /dev/null &

for _ in $(seq 100); do ss -ltn | grep -q ":5555 " && break; sleep 0.1; done
if ss -ltn | grep -q ":5555 "; then
  echo "adbd listening on 5555"
else
  echo "adbd NOT listening on 5555"
  echo "adbd process: $(pgrep -a adbd || echo none)"
  echo "--- /tmp/adbd.log"; tail -20 /tmp/adbd.log
fi
pgrep -a rknn_server || { echo "rknn_server NOT running"; tail -20 /tmp/rknn_server.log; }

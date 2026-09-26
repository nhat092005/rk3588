#!/usr/bin/env bash
# Fix CPU / NPU / DDR frequency before tier-2 measurements (Guide section 5.3), or restore it.
# Needs root. Run on the board:  sudo bash ai/board/lock_freq.sh lock | unlock | status
#
# RKNPU2 User Guide (p.72-73) uses "userspace"; this board's "performance" pins every clock at
# its max without the debugfs path, so that is used here. Original governors: CPU ondemand,
# NPU rknpu_ondemand, DDR dmc_ondemand.
set -euo pipefail
CPU=/sys/devices/system/cpu/cpufreq
NPU=/sys/class/devfreq/fdab0000.npu
DDR=/sys/class/devfreq/dmc

status() {
  for p in "$CPU"/policy*; do echo "$(basename "$p"): $(cat "$p/scaling_governor") $(cat "$p/scaling_cur_freq") kHz"; done
  echo "npu: $(cat $NPU/governor) $(cat $NPU/cur_freq) Hz"
  echo "ddr: $(cat $DDR/governor) $(cat $DDR/cur_freq) Hz"
}

case "${1:-status}" in
  lock)
    for p in "$CPU"/policy*; do echo performance > "$p/scaling_governor"; done
    echo performance > $NPU/governor
    echo performance > $DDR/governor
    status ;;
  unlock)
    for p in "$CPU"/policy*; do echo ondemand > "$p/scaling_governor"; done
    echo rknpu_ondemand > $NPU/governor
    echo dmc_ondemand > $DDR/governor
    status ;;
  status) status ;;
  *) echo "usage: $0 lock|unlock|status"; exit 1 ;;
esac

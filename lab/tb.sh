#!/bin/sh
# Run DSH on Terminal-Bench 2.0 tasks via Harbor.
#   lab/tb.sh <job-name> <arm> <rep> [harbor args...]   e.g. lab/tb.sh tbpool standard 1 -n 5
set -eu
HERE=$(cd "$(dirname "$0")/.." && pwd); LAB=$(cd "$HERE/.." && pwd)
JOB=$1 ARM=$2 REP=$3; shift 3
. "$LAB/.venv-harbor/bin/activate"
M='[{"type":"bind","source":"'$LAB'/tb/dsh-linux","target":"/opt/dsh","read_only":true},{"type":"bind","source":"'$HERE'/harness","target":"/opt/lab/harness","read_only":true}]'
cd "$HERE" && PYTHONPATH=. exec harbor run -p "$LAB/tb/terminal-bench" -a lab.harbor_dsh:DSHAgent \
  --ak arm="$ARM" --ak rep="$REP" --ak sweep="$JOB" --mounts "$M" -o runs/tb-jobs --job-name "$JOB-$ARM-r$REP" -y "$@"

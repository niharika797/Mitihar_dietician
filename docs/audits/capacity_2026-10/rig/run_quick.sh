#!/usr/bin/env bash
# Quick post-weight-fix check: weight burst (aged patients) then steady 10 rps, current tree. Usage: run_quick.sh <scratchpad dir>
export MSYS_NO_PATHCONV=1
SP="$1"; RIG="$(cd "$(dirname "$0")" && pwd -W)"; PY=C:/Users/Lenovo/perf-venv/Scripts/python.exe
export PERF_TOKENS="$SP/out/tokens.json" PERF_ENV_FILE="$SP/perf.env" PYTHONIOENCODING=utf-8 PERF_DB_HOST=pg
run() { name="$1"; shift; echo "START $name"; if $PY "$RIG/run_scenario.py" --name "$name" "$@" > "$RIG/../out_quick/$name.run.log" 2>&1; then echo "DONE $name"; else echo "FAIL $name"; fi; }
PERF_WEIGHT_AGED=1 run q_weight_burst_100 --classes Browser WeightOnce --users 150 --rate 5 --time 150 --env BR_USERS=50 WO_USERS=100 SPREAD_S=60 TPUT=0.2 GENERATE_ON_MEALS=1
run q_steady_10rps --classes SteadyMix --users 50 --rate 5 --time 300 --env TPUT=0.2 GENERATE_ON_MEALS=1
echo ALL-QUICK-DONE

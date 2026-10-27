#!/usr/bin/env bash
# Full retest of the current tree on the 1 vCPU API + 2 vCPU Postgres + no Redis rig (about 50 min).
# Step 0: time every endpoint one request at a time (re-times the N+1 fixes and the 19 never-timed ones).
# Steps 1-7: the load scenarios from run_load_2cpu.sh, current tree only, plus the weekly cron while traffic runs.
# Needs: rig containers up, API image rebuilt from the tree, tokens minted (mint_tokens.py, mint_admin.py).
# Progress lines: "DONE <name>" / "FAIL <name>". Usage: run_retest.sh <scratchpad dir>
export MSYS_NO_PATHCONV=1
SP="$1"; RIG="$(cd "$(dirname "$0")" && pwd -W)"; PY=C:/Users/Lenovo/perf-venv/Scripts/python.exe
OUT="$RIG/../out_retest"; mkdir -p "$OUT"
export PERF_TOKENS="$SP/out/tokens.json" PERF_ENV_FILE="$SP/perf.env" PYTHONIOENCODING=utf-8 PERF_DB_HOST=pg
run() { name="$1"; shift; echo "START $name"; if $PY "$RIG/run_scenario.py" --name "$name" "$@" > "$OUT/$name.run.log" 2>&1; then echo "DONE $name"; else echo "FAIL $name"; fi; }

echo "START r0_endpoint_timing"
if (cd "$RIG" && $PY measure_all.py --n 15 --out "$OUT/endpoint_costs_retest.json" > "$OUT/r0_endpoint_timing.run.log" 2>&1); then echo "DONE r0_endpoint_timing"; else echo "FAIL r0_endpoint_timing"; fi

O="r_"
run ${O}steady_10rps       --classes SteadyMix --users 50 --rate 5 --time 300 --env TPUT=0.2 GENERATE_ON_MEALS=1
run ${O}ramp_1_to_100      --locustfile locustfile_ramp.py --classes RampMix --users 1 --time 660 --env RAMP_TO=100 RAMP_S=600 GENERATE_ON_MEALS=1
run ${O}spike_300_30s      --classes Spike --users 300 --rate 300 --time 240 --env SPREAD_S=30 GENERATE_ON_MEALS=1
run ${O}login_storm_300    --classes LoginStorm --users 300 --rate 300 --time 420 --env SPREAD_S=300
run ${O}doctor_review      --classes DoctorReview --users 10 --rate 10 --time 240 --env THINK_S=1
# 100 first-time weight logs in 60 s while 50 browse; patients are backdated so the 28-day rule lets each log through
PERF_WEIGHT_AGED=1 run ${O}weight_burst_100 --classes Browser WeightOnce --users 150 --rate 5 --time 150 --env BR_USERS=50 WO_USERS=100 SPREAD_S=60 TPUT=0.2 GENERATE_ON_MEALS=1
run ${O}cron_during_steady --classes SteadyMix CronOnce --users 51 --rate 5 --time 150 --env TPUT=0.2 CRON_AT=30 GENERATE_ON_MEALS=1
echo ALL-RETEST-DONE

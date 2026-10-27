#!/usr/bin/env bash
# Full retest (about 65 min) of the code after the security fixes, with Redis for the rate-limit counters:
# API 1 vCPU / 1 GB one worker, Postgres 2 vCPU, Redis (stand-in for Memorystore Basic 1 GB, AUTH, no TLS).
# Step 0: every endpoint one request at a time (measure_all.py + measure_endpoints.py).
# Steps 1-9: the load scenarios of run_retest.sh, plus a refresh-token storm and a login flood next to normal traffic.
# Needs: rig containers up INCLUDING mitihar-perf-redis, API image rebuilt from the tree, PERF_REDIS_URL in the env file,
#        tokens minted (mint_tokens.py, mint_admin.py). reset_db.sh brings the schema to head and flushes Redis.
# Progress lines: "DONE <name>" / "FAIL <name>". Usage: run_retest_redis.sh <scratchpad dir>
export MSYS_NO_PATHCONV=1
SP="$1"; RIG="$(cd "$(dirname "$0")" && pwd -W)"; PY=C:/Users/Lenovo/perf-venv/Scripts/python.exe
OUT="$RIG/../out_retest_redis"; mkdir -p "$OUT"
export PERF_TOKENS="$SP/out/tokens.json" PERF_ENV_FILE="$SP/perf.env" PYTHONIOENCODING=utf-8 PERF_DB_HOST=pg
run() { name="$1"; shift; echo "START $name"; if $PY "$RIG/run_scenario.py" --name "$name" "$@" > "$OUT/$name.run.log" 2>&1; then echo "DONE $name"; else echo "FAIL $name"; fi; }

echo "START rr0_endpoint_timing"
if (cd "$RIG" && $PY measure_all.py --n 15 --out "$OUT/endpoint_costs_all.json" > "$OUT/rr0_measure_all.run.log" 2>&1 \
    && $PY measure_endpoints.py --n 20 --out "$OUT/endpoint_costs_core.json" > "$OUT/rr0_measure_core.run.log" 2>&1); then echo "DONE rr0_endpoint_timing"; else echo "FAIL rr0_endpoint_timing"; fi

O="rr_"
run ${O}steady_10rps       --classes SteadyMix --users 50 --rate 5 --time 300 --env TPUT=0.2 GENERATE_ON_MEALS=1
run ${O}ramp_1_to_100      --locustfile locustfile_ramp.py --classes RampMix --users 1 --time 660 --env RAMP_TO=100 RAMP_S=600 GENERATE_ON_MEALS=1
run ${O}spike_300_30s      --classes Spike --users 300 --rate 300 --time 240 --env SPREAD_S=30 GENERATE_ON_MEALS=1
run ${O}login_storm_300    --classes LoginStorm --users 300 --rate 300 --time 420 --env SPREAD_S=300
run ${O}doctor_review      --classes DoctorReview --users 10 --rate 10 --time 240 --env THINK_S=1
PERF_WEIGHT_AGED=1 run ${O}weight_burst_100 --classes Browser WeightOnce --users 150 --rate 5 --time 150 --env BR_USERS=50 WO_USERS=100 SPREAD_S=60 TPUT=0.2 GENERATE_ON_MEALS=1
run ${O}cron_during_steady --classes SteadyMix CronOnce --users 51 --rate 5 --time 150 --env TPUT=0.2 CRON_AT=30 GENERATE_ON_MEALS=1
# new: 300 patients log in over 2 min, then each rotates its refresh token every ~20 s (about 15 rotations/s)
run ${O}refresh_storm_300  --classes RefreshStorm --users 300 --rate 300 --time 420 --env SPREAD_S=120
# new: 11 req/s of normal traffic while 40 attacker users hammer the login (one email from many IPs / one IP with many emails)
run ${O}login_flood_steady --classes SteadyMix LoginFlood --users 90 --rate 10 --time 300 --env TPUT=0.2 GENERATE_ON_MEALS=1
echo ALL-RETEST-REDIS-DONE

#!/usr/bin/env bash
# A/B repeat of the 300-patients-in-30-seconds spike, with and without Redis, interleaved (R N R N), because one run
# differs from the next by as much as the Redis effect itself. Usage: run_spike_ab.sh <scratchpad dir>
export MSYS_NO_PATHCONV=1
SP="$1"; RIG="$(cd "$(dirname "$0")" && pwd -W)"; PY=C:/Users/Lenovo/perf-venv/Scripts/python.exe
OUT="$RIG/../out_retest_redis"; mkdir -p "$OUT"
export PERF_TOKENS="$SP/out/tokens.json" PERF_ENV_FILE="$SP/perf.env" PYTHONIOENCODING=utf-8 PERF_DB_HOST=pg
REDIS_URL_SAVED="$(grep '^PERF_REDIS_URL=' "$SP/perf.env" | cut -d= -f2-)"
one() { tag="$1"; url="$2"
  echo "START spike_$tag"
  if PERF_REDIS_URL="$url" $PY "$RIG/run_scenario.py" --name "ab_spike_$tag" --classes Spike --users 300 --rate 300 --time 240 --env SPREAD_S=30 GENERATE_ON_MEALS=1 > "$OUT/ab_spike_$tag.run.log" 2>&1
  then echo "DONE spike_$tag (REDIS_URL in API: $(docker exec mitihar-perf-api printenv REDIS_URL | sed -E 's#://[^@]*@#://***@#'))"; else echo "FAIL spike_$tag"; fi; }
one redis1 "$REDIS_URL_SAVED"
one memory1 ""
one redis2 "$REDIS_URL_SAVED"
one memory2 ""
echo ALL-AB-DONE

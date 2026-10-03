#!/bin/bash
# Public LME-S n=100 + LoCoMo head-to-head. Sequential, one stack at a time, <=2 containers. One run per arm, no re-rolls.
# Cap $75 (runner/ledger.py CAP). Stop rules and drop order: see the task brief; logged to progress.log.
set -u
cd "$(dirname "$(readlink -f "$0")")"
RUN=$PWD; KIT=$RUN/kit; PY=python3
LOCK=$RUN/run.lock
[ -e "$LOCK" ] && { echo "lock exists: $LOCK"; exit 9; }
echo $$ > "$LOCK"
log() { echo "$(date -u +%FT%TZ) $*" >> "$RUN/progress.log"; }
trap 'log "EXIT run.sh (status $?)"; rm -f "$LOCK"' EXIT
export DEEPSEEK_API_KEY="$(cat "$RUN/keys/deepseek")"
export JUDGE_API_KEY="$(cat "$RUN/keys/openai")"
export JUDGE_USD_PER_M_IN=0.25 JUDGE_USD_PER_M_OUT=2.0    # gpt-5-mini list price; also applied to the preference judge (6 grades per LME arm)
export FLUX_SRC_DIR=$RUN/flux-src LANE_SUBNET=10.78.41.0/24
export PYTHONUNBUFFERED=1
cd "$KIT"; mkdir -p results/locomo

# ---------- cap gate: high estimates (COST.md) per stage, in execution order; ':d' = droppable ----------
STAGES="lme_flux_public:0.35 lme_flux_extract:2.1 lme_flux_evidence:0.35 locomo_flux_public:2.2 locomo_flux_extract:0.15 locomo_flux_evidence:2.2 \
lme_closed_book:0.2 locomo_closed_book:1.4 lme_full_context:4.0 locomo_full_context:2.2:d \
lme_honcho:16.5 locomo_honcho:3.4 locomo_honcho_chat:4.5:d lme_mem0:8.6 locomo_mem0:2.7 lme_letta:0.4 locomo_letta:2.2"
gate() {  # gate STAGE -> 0 if committed + this stage + all LATER mandatory stages fit under the cap
  local name=$1 r
  r=$($PY - "$name" $STAGES <<'P'
import sys
name, st = sys.argv[1], [s.split(':') for s in sys.argv[2:]]
names = [s[0] for s in st]; i = names.index(name)
print(round(float(st[i][1]) + sum(float(s[1]) for s in st[i+1:] if len(s) < 3), 3))
P
)
  if $PY runner/ledger.py check --reserve "$r" >/dev/null; then return 0; fi
  log "CAP: skipping $name (committed $($PY runner/ledger.py status | $PY -c 'import sys,json;print(json.load(sys.stdin)["total"])') + reserve $r would pass the cap)"
  echo "cap would bind: $name skipped $(date -u +%FT%TZ)" >> "$RUN/CAP-DROPPED.txt"
  return 1
}
spent() { $PY runner/ledger.py status | $PY -c 'import sys,json;print(json.load(sys.stdin)["total"])'; }
stopped() { log "STOPPED $1: $2"; echo "$2 ($(date -u +%FT%TZ))" > "$RUN/STOPPED-$1.txt"; }

# ---------- benchmark context ----------
setb() {  # setb lme|locomo
  B=$1; export BENCH=$B
  if [ $B = lme ]; then UH=work/units_n100.jsonl; UC=/work/units_n100.jsonl; R=results; RC=/results; N=100; FIRST=10; FACTS=work/facts_n100.jsonl; FACTSC=/work/facts_n100.jsonl
  else UH=work/locomo_units.jsonl; UC=/work/locomo_units.jsonl; R=results/locomo; RC=/results/locomo; N=10; FIRST=3; FACTS=work/facts_locomo.jsonl; FACTSC=/work/facts_locomo.jsonl; fi
}
firstids() { $PY -c "import json,sys;print(','.join(json.loads(l)['unit_id'] for l in list(open('$UH'))[:$FIRST]))"; }
check() {  # check ARM [--final] -> 0 ok, 1 failed (arm stopped)
  local arm=$1; shift
  local out; out=$($PY "$RUN/tools/check_arm.py" "$R/$arm" $N "$@"); local rc=$?
  log "check $B/$arm: $out"
  if [ $rc -ne 0 ]; then stopped "${B}_$arm" ">2% failed ingest items/units: $out"; return 1; fi
  return 0
}
qa() {  # qa ARM_IN_ROWS INPUT_DIR OUT_DIR RESERVE
  local arm=$1 in=$2 out=$3 res=$4 rc
  log "qa start $B/$arm"
  $PY runner/qa.py --bench $B --inputs "$R/$in/retrieved.jsonl" --arm "$arm" --out "$R/$out/qa" --reserve "$res" > "$RUN/qa-$B-$arm.out" 2>&1; rc=$?
  if [ $rc -ne 0 ]; then
    log "qa $B/$arm exit $rc (breaker/cap?); one resume of unfinished questions after 120 s (finished rows are kept; not a re-roll)"
    sleep 120
    $PY runner/qa.py --bench $B --inputs "$R/$in/retrieved.jsonl" --arm "$arm" --out "$R/$out/qa" --reserve "$res" >> "$RUN/qa-$B-$arm.out" 2>&1; rc=$?
  fi
  log "qa done $B/$arm exit $rc summary: $(cat "$R/$out/qa/summary.json" 2>/dev/null | tr -d '\n ')  spend_total=$(spent)"
}

# ---------- compose helpers ----------
PROJ=""; SYS=""
dc()  { docker compose -p "$PROJ" -f "$KIT/compose/$SYS/docker-compose.yml" "$@"; }
dcx() { local svc=$1; shift; dc exec -T -e BENCH="$BENCH" "$svc" "$@"; }
up() {  # up SYSTEM  (builds images, starts the stack)
  SYS=$1; PROJ=ob-$1; log "stack up: $SYS"
  [ $SYS = honcho ] && sh compose/honcho/fetch-honcho.sh >> "$RUN/build-honcho.out" 2>&1
  dc up -d --build >> "$RUN/build-$SYS.out" 2>&1 || { log "stack up FAILED: $SYS (see build-$SYS.out)"; return 1; }
}
down() {
  log "stack down: $SYS"; dc down -v --remove-orphans >> "$RUN/build-$SYS.out" 2>&1
  local imgs; imgs=$(docker image ls --filter "reference=${PROJ}-*" -q | sort -u)
  [ -n "$imgs" ] && docker rmi $imgs >> "$RUN/build-$SYS.out" 2>&1
  log "stack down done: $SYS; docker ps (own): $(docker ps -q --filter "label=com.docker.compose.project=$PROJ" | wc -l)"
}
waitup() {  # waitup SVC PYTHON URL  : any HTTP answer (even 404) counts as up; <=20 min
  local svc=$1 py=$2 url=$3 i
  for i in $(seq 1 80); do
    dcx "$svc" "$py" -c "import urllib.request,urllib.error,sys
try: urllib.request.urlopen('$url',timeout=5)
except urllib.error.HTTPError: pass
except Exception: sys.exit(1)" >/dev/null 2>&1 && { log "up: $svc $url"; return 0; }
    sleep 15
  done
  log "NOT UP: $svc $url"; return 1
}

# ================= Flux =================
flux_system() {
  up flux || { stopped flux "stack failed to build or start"; return; }
  for b in lme locomo; do
    setb $b
    if gate ${b}_flux_public; then
      log "flux_public $b start"
      dcx flux python drivers/flux_public.py --units $UC --out $RC/flux_public >> "$RUN/flux-$b.out" 2>&1
      if check flux_public --final; then qa flux_public flux_public flux_public $([ $b = lme ] && echo 0.5 || echo 2.5); fi
    fi
    if gate ${b}_flux_extract; then
      log "flux extract $b start"
      dcx flux python drivers/flux_extract_facts.py --units $UC --out $FACTSC >> "$RUN/flux-$b.out" 2>&1
      log "flux extract $b exit $? spend_total=$(spent)"
    fi
    if gate ${b}_flux_evidence; then
      if [ -s "$FACTS" ]; then
        log "flux_evidence $b start"
        dcx flux python drivers/flux_evidence.py --units $UC --facts $FACTSC --out $RC/flux_evidence >> "$RUN/flux-$b.out" 2>&1
        if check flux_evidence --final; then qa flux_evidence flux_evidence flux_evidence $([ $b = lme ] && echo 0.5 || echo 2.5); fi
      else stopped ${b}_flux_evidence "no facts file produced"; fi
    fi
  done
  down
}

# ================= closed_book / full_context (host, no containers) =================
baseline() {  # baseline closed_book|full_context
  local arm=$1
  for b in lme locomo; do
    setb $b
    gate ${b}_$arm || continue
    log "$arm $b start"
    $PY drivers/$arm.py --units $UH --out $R/$arm >> "$RUN/$arm-$b.out" 2>&1
    if check $arm --final; then qa $arm $arm $arm $([ $arm = full_context ] && { [ $b = lme ] && echo 4.5 || echo 2.5; } || echo 0.5); fi
  done
}

# ================= Honcho (ctx + chat share one ingest) =================
honcho_system() {
  up honcho && waitup stack /sidecar/bin/python http://127.0.0.1:8000/health || { stopped honcho "stack failed to start"; down; return; }
  for b in lme locomo; do
    setb $b
    gate ${b}_honcho || continue
    local arms=ctx,chat
    if [ $b = locomo ] && ! gate locomo_honcho_chat; then arms=ctx; log "DROPPED locomo honcho_chat (cap)"; fi
    local H=/sidecar/bin/python
    log "honcho $b start arms=$arms (first $FIRST units, then cost rule)"
    dcx stack $H /repo/drivers/honcho_retrieval.py --arms $arms --units $UC --out $RC/honcho_retrieval --only "$(firstids)" >> "$RUN/honcho-$b.out" 2>&1
    check honcho_retrieval || { down; return; }
    if [ $b = lme ]; then $PY runner/ledger.py honcho-rule --dir $R/honcho_retrieval > "$RUN/honcho-rule-$b.out" 2>&1; rc=$?
    else $PY runner/ledger.py honcho-rule --dir $R/honcho_retrieval --locomo > "$RUN/honcho-rule-$b.out" 2>&1; rc=$?; fi
    log "honcho cost rule $b: rc=$rc $(cat "$RUN/honcho-rule-$b.out")"
    if [ $rc -ne 0 ]; then stopped honcho_$b "Honcho cost rule fired after first $FIRST units: $(cat "$RUN/honcho-rule-$b.out")"; down; return; fi
    dcx stack $H /repo/drivers/honcho_retrieval.py --arms $arms --units $UC --out $RC/honcho_retrieval >> "$RUN/honcho-$b.out" 2>&1
    check honcho_retrieval --final || { down; return; }
    qa honcho_retrieval honcho_retrieval honcho_retrieval $([ $b = lme ] && echo 0.8 || echo 2.5)
    case $arms in *chat*) qa honcho_chat honcho_retrieval honcho_chat $([ $b = lme ] && echo 0.8 || echo 2.5);; esac
  done
  down
}

# ================= mem0 / Letta (first chunk, check, rest) =================
chunked_system() {  # chunked_system mem0|letta SVC DRIVER WAITURL
  local sys=$1 svc=$2 drv=$3 url=$4
  up $sys || { stopped $sys "stack failed to build or start"; return; }
  waitup $svc python "$url" || { stopped $sys "service not up"; down; return; }
  for b in lme locomo; do
    setb $b
    gate ${b}_$sys || continue
    log "$sys $b start (first $FIRST units, check, rest)"
    dcx $svc python drivers/$drv --units $UC --out $RC/$sys --procs 8 --only "$(firstids)" >> "$RUN/$sys-$b.out" 2>&1
    check $sys || { down; return; }
    dcx $svc python drivers/$drv --units $UC --out $RC/$sys --procs 8 >> "$RUN/$sys-$b.out" 2>&1
    check $sys --final || { down; return; }
    qa $sys $sys $sys $([ $b = lme ] && echo 1.0 || echo 2.5)
  done
  down
}

log "START run.sh; kit $(git -C "$KIT" rev-parse --short HEAD 2>/dev/null || echo archive); cap 75; spend_total=$(spent)"
flux_system
baseline closed_book
baseline full_context
honcho_system
chunked_system mem0 mem0 mem0_driver.py http://127.0.0.1:18800/stats
chunked_system letta letta letta_driver.py http://127.0.0.1:8283/v1/health/
log "final spend_total=$(spent)"
echo "DONE $(date -u +%FT%TZ)" > "$RUN/DONE"; log DONE

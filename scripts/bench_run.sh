#!/bin/zsh
# Run the agent-memory benchmark on a committed Chronicle revision.
#
#   scripts/bench_run.sh LABEL CORPUS(a|b) MODEL(lightning|ultra) REDACT(on|off|person) [runner args]
#
# REF (default HEAD) picks the commit; its chronicle/ and adapters/ are copied to a snapshot so
# edits made while the run is going never leak into it. Other env:
#   BENCH       benchmark dir (default /tmp/nemoclaw/examples/tools/agent-memory-benchmark)
#   ENV_FILE    .env with OPENAI_API_KEY (default ../../../.env from this worktree's repo root)
#   VENV        python env with Chronicle's dependencies
#   CONSOLIDATE_MODEL  model for the one-time consolidation pass (default: the run's model)
# The body is one function so editing this file mid-run cannot change a running copy.
SCRIPT_DIR=${0:A:h}
main() {
  set -u
  local LABEL=$1 CORPUS=$2 MODEL=$3 REDACT=$4
  shift 4
  local SRC=${SCRIPT_DIR:h}
  local B=${BENCH:-/tmp/nemoclaw/examples/tools/agent-memory-benchmark}
  local VENV=${VENV:-/Users/sara/Desktop/Opustron-fullrun/.venv}
  local ENV_FILE=${ENV_FILE:-/Users/sara/Desktop/Opustron/.env}
  local TS=$(date -u +%Y%m%dT%H%M%SZ)
  local NAME=$TS-exp-$LABEL-$CORPUS-$MODEL-$REDACT
  local W=$B/results/snapshots/$NAME
  mkdir -p $W
  git -C $SRC archive ${REF:-HEAD} chronicle adapters | tar -x -C $W
  echo "### code $(git -C $SRC rev-parse --short ${REF:-HEAD}) -> $W"
  set -a; . $ENV_FILE; set +a
  unset NEBIUS_BASE_URL NEBIUS_API_KEY
  export PATH=$VENV/bin:$PATH
  export SSL_CERT_FILE=$($VENV/bin/python -c 'import certifi; print(certifi.where())')
  export PYTHONPATH=$W CHRONICLE_ROOT=$W CHRONICLE_MAX_TOKENS=16384
  case $MODEL in
    ultra) export CHRONICLE_MODEL=nvidia/Nemotron-3-Ultra-550b-a55b
           sed -i '' 's#nvidia/Nemotron-3_5-Lightning#nvidia/Nemotron-3-Ultra-550b-a55b#' $W/adapters/chronicle/adapter.json ;;
    lightning) export CHRONICLE_MODEL=nvidia/Nemotron-3_5-Lightning ;;
    *) echo "unknown model $MODEL"; return 2 ;;
  esac
  case $REDACT in
    on) unset CHRONICLE_REDACT_NAMES ;;
    off|person) export CHRONICLE_REDACT_NAMES=$REDACT ;;
    *) echo "unknown redaction $REDACT"; return 2 ;;
  esac
  [ -n "${CONSOLIDATE_MODEL:-}" ] && export CHRONICLE_CONSOLIDATE_MODEL=$CONSOLIDATE_MODEL
  cd $B
  local OUT=results/runs/$NAME
  echo "### $OUT"
  python3 -m bench.runner --adapter $W/adapters/chronicle \
    --corpus corpus_$CORPUS/corpus --questions corpus_$CORPUS/questions/questions.jsonl \
    --gold corpus_$CORPUS/questions/answers.jsonl \
    --upstream https://api.tokenfactory.nebius.com --out $OUT --state $OUT/state "$@"
  echo "### exit $? $OUT"
}
main "$@"

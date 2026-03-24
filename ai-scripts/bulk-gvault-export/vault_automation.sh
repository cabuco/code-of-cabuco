#!/bin/bash
set -Eeuo pipefail

BASE_DIR="$PWD/vault_exports"
LOG_DIR="$BASE_DIR/logs"
STATE_DIR="$BASE_DIR/state"
LOG_FILE="$LOG_DIR/vault_automation.log"
STOP_FILE="$BASE_DIR/STOP_VAULT_AUTOMATION"
PROGRESS_FILE="$STATE_DIR/progress.json"

mkdir -p "$BASE_DIR" "$LOG_DIR" "$STATE_DIR"

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') | $1" | tee -a "$LOG_FILE" >&2
}

on_err() {
  local code=$?
  log "ERROR: exit_code=$code line=$1 cmd=$2"
  exit $code
}
trap 'on_err $LINENO "$BASH_COMMAND"' ERR

check_stop() {
  if [[ -f "$STOP_FILE" ]]; then
    log "STOP file detected. Exiting safely."
    exit 0
  fi
}

need_cmd() { command -v "$1" >/dev/null 2>&1 || { log "Missing required command: $1"; exit 1; }; }
need_cmd jq
need_cmd python3
need_cmd sed
need_cmd awk
need_cmd wc

init_progress() {
  [[ -f "$PROGRESS_FILE" ]] || echo "{}" > "$PROGRESS_FILE"
}

update_progress() {
  jq --arg m "$1" --arg k "$2" --arg v "$3" \
    '.[$m][$k]=$v' "$PROGRESS_FILE" > "$PROGRESS_FILE.tmp" \
    && mv "$PROGRESS_FILE.tmp" "$PROGRESS_FILE"
}

get_progress() {
  jq -r --arg m "$1" --arg k "$2" '.[$m][$k] // empty' "$PROGRESS_FILE"
}

run_gam() {
  local attempt=1
  local max_attempts=8
  local sleep_s=10
  local out rc

  while true; do
    check_stop
    set +e
    out=$(gam "$@" 2>&1)
    rc=$?
    set -e

    if [[ $rc -eq 0 ]]; then
      echo "$out"
      return 0
    fi

    if echo "$out" | grep -qiE "rateLimitExceeded|userRateLimitExceeded|quota|backendError|internalError|temporar|try again"; then
      if [[ $attempt -ge $max_attempts ]]; then
        log "GAM failed after retries. Command: gam $*"
        log "Last error: $(echo "$out" | tr '\n' ' ' | cut -c1-600)"
        return 1
      fi
      log "Transient error (attempt $attempt/$max_attempts). Backing off ${sleep_s}s."
      log "Error: $(echo "$out" | tr '\n' ' ' | cut -c1-300)"
      sleep "$sleep_s"
      attempt=$((attempt+1))
      sleep_s=$((sleep_s*2))
      [[ $sleep_s -gt 600 ]] && sleep_s=600
      continue
    fi

    log "Non-retryable GAM error. Command: gam $*"
    log "Error: $(echo "$out" | tr '\n' ' ' | cut -c1-900)"
    return 1
  done
}

# Safe string for export names: lowercase, non-alnum -> underscore
safe_token() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/_/g; s/^_+//; s/_+$//'
}

delete_export_best_effort() {
  local matter_ref="$1"   # id:<uuid>
  local export_name="$2"
  set +e
  gam delete export "$matter_ref" "$export_name" >/dev/null 2>&1
  if [[ $? -ne 0 ]]; then
    gam delete vaultexport "$matter_ref" "$export_name" >/dev/null 2>&1
  fi
  set -e
}

init_progress

log "Setting GAM threading to reduce Vault throttling (num_threads=1)"
run_gam config num_threads 1 save >/dev/null || true

log "Starting Vault automation run"
log "Fetching all Vault matters"

# Raw output includes progress lines; strip down to real CSV
run_gam print vaultmatters > /tmp/vault_matters_raw.txt
sed -n '/^matterId,/,$p' /tmp/vault_matters_raw.txt > /tmp/vault_matters.csv

log "CSV lines: $(wc -l < /tmp/vault_matters.csv | tr -d " ")"
log "CSV head (first 2 lines):"
sed -n '1,2p' /tmp/vault_matters.csv | while IFS= read -r L; do log "CSV: $L"; done

# Build TSV containing only OPEN matters whose name begins with "@"
python3 - <<'PY'
import csv,re,sys
infile="/tmp/vault_matters.csv"
outfile="/tmp/vault_matters_open.tsv"

def norm(s): return (s or "").strip().lower()

with open(infile,newline='') as f:
    rows=list(csv.reader(f))

if not rows:
    open(outfile,"w").close()
    sys.exit(0)

header=[norm(c) for c in rows[0]]
id_idx = header.index("matterid") if "matterid" in header else 0
name_idx = header.index("name") if "name" in header else None
state_idx = header.index("state") if "state" in header else None

with open(outfile,"w") as out:
    for r in rows[1:]:
        if not r:
            continue
        mid = r[id_idx].strip() if id_idx < len(r) else ""
        name = r[name_idx].strip() if name_idx is not None and name_idx < len(r) else ""
        state = r[state_idx].strip() if state_idx is not None and state_idx < len(r) else ""
        if not mid:
            continue
        if not name.startswith("@"):
            continue
        if state.upper() != "OPEN":
            continue
        name = re.sub(r'[,\s]+$','',name)
        out.write(f"{mid}\t{name}\t{state}\n")
PY

if [[ ! -s /tmp/vault_matters_open.tsv ]]; then
  log "No OPEN @-prefixed matters found. Exiting."
  exit 0
fi

# Detect duplicate OPEN matter names to avoid folder collisions
python3 - <<'PY'
import collections
names=[]
with open("/tmp/vault_matters_open.tsv","r") as f:
    for line in f:
        parts=line.rstrip("\n").split("\t")
        if len(parts) >= 2:
            names.append(parts[1])
counts=collections.Counter(names)
with open("/tmp/vault_open_name_dupes.txt","w") as out:
    for n,c in counts.items():
        if c>1:
            out.write(n+"\n")
PY

is_dupe_name() {
  local n="$1"
  grep -Fxq "$n" /tmp/vault_open_name_dupes.txt
}

while IFS=$'\t' read -r MATTER_ID MATTER_NAME MATTER_STATE; do
  check_stop

  [[ -z "$MATTER_ID" ]] && continue
  [[ -z "$MATTER_NAME" ]] && continue

  # Username = everything after @ up to first space
  USERNAME=$(echo "$MATTER_NAME" | sed -E 's/^@([^[:space:]]+).*/\1/')

  SAFE_USER=$(safe_token "$USERNAME")
  SAFE_MATTER=$(safe_token "$MATTER_NAME")

  # IMPORTANT: use id:<uuid> for export ops to avoid "Does not exist"
  MATTER_REF="id:$MATTER_ID"

  SHORTID="${MATTER_ID:0:8}"
  GMAIL_EXPORT_NAME="gmail_${SAFE_USER}_${SAFE_MATTER}_${SHORTID}"
  DRIVE_EXPORT_NAME="drive_${SAFE_USER}_${SAFE_MATTER}_${SHORTID}"

  # Folder: matter name; if duplicates exist, append __SHORTID
  FOLDER_NAME="$MATTER_NAME"
  if is_dupe_name "$MATTER_NAME"; then
    FOLDER_NAME="${MATTER_NAME}__${SHORTID}"
  fi

  MATTER_DIR="$BASE_DIR/$FOLDER_NAME"
  GMAIL_DIR="$MATTER_DIR/Gmail"
  DRIVE_DIR="$MATTER_DIR/Drive"
  mkdir -p "$GMAIL_DIR" "$DRIVE_DIR"

  log "Processing OPEN matter: $MATTER_NAME (user=$USERNAME id=$MATTER_ID)"
  log "Export names: Gmail=$GMAIL_EXPORT_NAME Drive=$DRIVE_EXPORT_NAME"
  log "Folder: $MATTER_DIR"

  # ---------- GMAIL ----------
  if [[ "$(get_progress "$MATTER_ID" gmail_done)" != "yes" ]]; then
    log "Creating Gmail export (MBOX)"
    run_gam create export matter "$MATTER_REF" \
      name "$GMAIL_EXPORT_NAME" \
      corpus mail \
      scope all_data \
      accounts "$USERNAME" \
      format mbox \
      usenewexport true >/dev/null

    update_progress "$MATTER_ID" gmail_export_name "$GMAIL_EXPORT_NAME"

    log "Waiting for Gmail export to complete"
    while true; do
      check_stop
      INFO_OUT=$(run_gam info export "$MATTER_REF" "$GMAIL_EXPORT_NAME")
      STATUS=$(echo "$INFO_OUT" | awk -F': ' '/status:/ {print $2; exit}' | tr '[:lower:]' '[:upper:]' | tr -d '\r')
      [[ "$STATUS" == "COMPLETED" ]] && break
      [[ "$STATUS" == "FAILED" ]] && { log "Gmail export FAILED"; log "$INFO_OUT"; exit 1; }
      sleep 120
    done

    log "Downloading Gmail export"
    run_gam download vaultexport "$MATTER_REF" "$GMAIL_EXPORT_NAME" targetfolder "$GMAIL_DIR" >/dev/null

    log "Deleting Gmail export"
    delete_export_best_effort "$MATTER_REF" "$GMAIL_EXPORT_NAME"

    update_progress "$MATTER_ID" gmail_done yes
  fi

  sleep 60

  # ---------- DRIVE ----------
  if [[ "$(get_progress "$MATTER_ID" drive_done)" != "yes" ]]; then
    log "Creating Drive export"
    run_gam create export matter "$MATTER_REF" \
      name "$DRIVE_EXPORT_NAME" \
      corpus drive \
      scope all_data \
      accounts "$USERNAME" \
      usenewexport true >/dev/null

    update_progress "$MATTER_ID" drive_export_name "$DRIVE_EXPORT_NAME"

    log "Waiting for Drive export to complete"
    while true; do
      check_stop
      INFO_OUT=$(run_gam info export "$MATTER_REF" "$DRIVE_EXPORT_NAME")
      STATUS=$(echo "$INFO_OUT" | awk -F': ' '/status:/ {print $2; exit}' | tr '[:lower:]' '[:upper:]' | tr -d '\r')
      [[ "$STATUS" == "COMPLETED" ]] && break
      [[ "$STATUS" == "FAILED" ]] && { log "Drive export FAILED"; log "$INFO_OUT"; exit 1; }
      sleep 180
    done

    log "Downloading Drive export"
    run_gam download vaultexport "$MATTER_REF" "$DRIVE_EXPORT_NAME" targetfolder "$DRIVE_DIR" >/dev/null

    log "Deleting Drive export"
    delete_export_best_effort "$MATTER_REF" "$DRIVE_EXPORT_NAME"

    update_progress "$MATTER_ID" drive_done yes
  fi

  update_progress "$MATTER_ID" status completed
  log "Completed matter: $MATTER_NAME ($MATTER_ID)"
  sleep 120

done < /tmp/vault_matters_open.tsv

log "Vault automation run complete"

#!/usr/bin/env bash
set -euo pipefail

# Ensure we can find 'uv' and other tools
export PATH="/opt/homebrew/bin:$PATH"

# -----------------------------------------------------------------------------
# reMarkable -> Apple Notes sync runner (Spike)
#
# Logging:
#   - Writes timestamped logs to ./logs/
#   - Also prints to terminal
#
# Scoping:
#   - Set REMARKABLE_ROOT_PATH to scope which reMarkable subtree the MCP tools expose
#     Example: /Work or /2026 Q1
#
# Apple Notes destination:
#   - --folder sets the Apple Notes folder name (default: reMarkable)
#
# Examples:
#   ./run_remarkable_to_apple_notes.sh
#   ./run_remarkable_to_apple_notes.sh --rm-root "/Work" --notes-folder "reMarkable - Work" --limit 40
#   ./run_remarkable_to_apple_notes.sh --rm-root "/2026 Q1 " --notes-folder "reMarkable - 2026 Q1" --force
# -----------------------------------------------------------------------------

cd "$(dirname "$0")"

# Defaults
RM_ROOT=""
NOTES_FOLDER="reMarkable"
LIMIT="40"
STATE_FILE="${HOME}/.remarkable_apple_notes_sync_state.json"
FORCE="0"
DRY_RUN="0"

# Parse args (simple + explicit)
while [[ $# -gt 0 ]]; do
  case "$1" in
    --rm-root)
      RM_ROOT="${2:-}"
      shift 2
      ;;
    --notes-folder|--folder)
      NOTES_FOLDER="${2:-reMarkable}"
      shift 2
      ;;
    --limit)
      LIMIT="${2:-40}"
      shift 2
      ;;
    --state-file)
      STATE_FILE="${2:-$STATE_FILE}"
      shift 2
      ;;
    --force)
      FORCE="1"
      shift 1
      ;;
    --dry-run)
      DRY_RUN="1"
      shift 1
      ;;
    -h|--help)
      sed -n '1,80p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Use --help for usage."
      exit 2
      ;;
  esac
done

mkdir -p logs

ts="$(date '+%Y-%m-%d_%H-%M-%S')"
logfile="logs/remarkable_to_notes_${ts}.log"

echo "[$(date)] Starting reMarkable -> Apple Notes sync" | tee -a "$logfile"
echo "Repo: $(pwd)" | tee -a "$logfile"
echo "Apple Notes folder: ${NOTES_FOLDER}" | tee -a "$logfile"
echo "Limit: ${LIMIT}" | tee -a "$logfile"
echo "State file: ${STATE_FILE}" | tee -a "$logfile"
echo "Force: ${FORCE}  Dry-run: ${DRY_RUN}" | tee -a "$logfile"

# Scope to a reMarkable folder subtree if provided
# This env var is consumed by the MCP code (root filtering).
if [[ -n "${RM_ROOT}" ]]; then
  export REMARKABLE_ROOT_PATH="${RM_ROOT}"
  echo "reMarkable scope (REMARKABLE_ROOT_PATH): ${REMARKABLE_ROOT_PATH}" | tee -a "$logfile"
else
  echo "reMarkable scope: (none)" | tee -a "$logfile"
fi

cmd=(uv run python scripts/process_notebook.py
  --limit "${LIMIT}"
  --folder "${NOTES_FOLDER}"
  --state-file "${STATE_FILE}"
)

# Note: --force and --dry-run are currently ignored by the new pipeline script
# if [[ "${FORCE}" == "1" ]]; then
#   cmd+=(--force)
# fi
# if [[ "${DRY_RUN}" == "1" ]]; then
#   cmd+=(--dry-run)
# fi

echo "Command: ${cmd[*]}" | tee -a "$logfile"
echo "-----" | tee -a "$logfile"

# Run + log
"${cmd[@]}" 2>&1 | tee -a "$logfile"

echo "-----" | tee -a "$logfile"
echo "[$(date)] Done. Log: ${logfile}" | tee -a "$logfile"
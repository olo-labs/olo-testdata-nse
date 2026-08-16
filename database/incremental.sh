#!/usr/bin/env bash
set -Eeuo pipefail

database_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repository_dir=$(cd -- "$database_dir/.." && pwd -P)
builder_dir="$repository_dir/parquet_database"
state_file="$database_dir/incremental.state.json"
started_at=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
last_success=""
[[ -f "$state_file" ]] && last_success=$(sed -n 's/.*"last_successful_build_at"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$state_file" | head -n 1)

write_state() {
  local state=$1 message=$2 finished=${3:-} temporary="${state_file}.tmp"
  printf '{\n  "state": "%s",\n  "message": "%s",\n  "started_at": "%s",\n  "finished_at": %s,\n  "last_successful_build_at": %s\n}\n' \
    "$state" "$message" "$started_at" \
    "$([[ -n "$finished" ]] && printf '"%s"' "$finished" || printf 'null')" \
    "$([[ -n "$last_success" ]] && printf '"%s"' "$last_success" || printf 'null')" > "$temporary"
  mv -f -- "$temporary" "$state_file"
}

finish() {
  local result=$? finished
  trap - EXIT
  finished=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
  if (( result == 0 )); then
    last_success=$finished
    write_state SUCCESS "Incremental build completed successfully" "$finished"
  else
    write_state FAILED "Incremental build failed with exit code $result" "$finished"
  fi
  exit "$result"
}

write_state RUNNING "Incremental build is in progress"
trap finish EXIT

[[ -f "$builder_dir/fast_build_database.py" ]] || { echo "Missing NSE builder" >&2; exit 2; }
python_bin=${OLO_PYTHON:-python3}
venv="$builder_dir/.venv"
[[ -x "$venv/bin/python" ]] || "$python_bin" -m venv "$venv"
"$venv/bin/python" -m pip install --disable-pip-version-check -r "$builder_dir/requirements.txt"
cd -- "$builder_dir"
"$venv/bin/python" fast_build_database.py --profile "${OLO_BUILD_PROFILE:-ci}"

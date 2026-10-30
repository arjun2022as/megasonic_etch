#!/bin/bash
# Submit cases whose name matches a pattern, each with its own walltime (column 2 of cases.csv).
#   bash submit_cases.sh M0_none --discover      # first run on Puma: compile UDF + list Fluent settings
#   bash submit_cases.sh M0_none --setup-only    # smoke test (a few steps), results/M0_none_test
#   bash submit_cases.sh '^A_'                   # angle sweep
#   bash submit_cases.sh .                       # everything
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p logs
PATTERN=${1:?usage: bash submit_cases.sh <pattern> [run_case.py args]}
shift
VENV=${VENV:-$HOME/venvs/pyfluent241}
if [[ ! -f "$VENV/bin/activate" ]]; then
    echo "ERROR: $VENV not found (it is created by ~/3d_nand/ansys_busnaina/setup_env.sh)" >&2
    exit 1
fi
tail -n +2 cases.csv | while IFS=, read -r case walltime _; do
    [[ "$case" =~ $PATTERN ]] || continue
    if [[ " $* " == *" --setup-only "* || " $* " == *" --discover "* ]]; then walltime=01:00:00; fi
    sbatch --job-name="$case" --time="$walltime" run_case.slurm "$case" "$@"
done

#!/bin/bash
# Case 10 (resolved oscillation): submit cases of cases_resolved.csv whose name matches a pattern.
#   bash submit_resolved.sh R15_flat --setup-only   # smoke test first (1 h), results/R15_flat_test
#   bash submit_resolved.sh '^R'                    # all six cases
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p logs
PATTERN=${1:?usage: bash submit_resolved.sh <pattern> [run_resolved.py args]}
shift
tail -n +2 cases_resolved.csv | while IFS=, read -r case walltime _; do
    [[ "$case" =~ $PATTERN ]] || continue
    if [[ " $* " == *" --setup-only "* ]]; then walltime=01:00:00; fi
    sbatch --job-name="$case" --time="$walltime" run_resolved.slurm "$case" "$@"
done

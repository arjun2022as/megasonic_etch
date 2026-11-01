#!/bin/bash
#SBATCH --job-name=post2d
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --partition=standard
#SBATCH --account=krishna
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

# Post-processing without Fluent: flux check of the given cases, then contour maps / profiles.
#   sbatch post.slurm B_f1_I2_floor            # check_2d.py on that case, then make_contours.py --all
#   sbatch post.slurm M0_none B0_floor -- M0_none B0_floor B_f1_I2_floor   # checks, then plots of the listed cases
# Uses the system Python 3 (matplotlib installed with pip --user), not the PyFluent venv.
set -uo pipefail
cd "$SLURM_SUBMIT_DIR"
PY=${PY:-/usr/bin/python3}
checks=() plots=()
seen=0
for a in "$@"; do
    if [[ "$a" == "--" ]]; then seen=1; continue; fi
    if (( seen )); then plots+=("$a"); else checks+=("$a"); fi
done
echo "Job $SLURM_JOB_ID on $(hostname): checks [${checks[*]}], plots [${plots[*]:---all}]"
for c in "${checks[@]}"; do
    echo "=== check_2d.py $c"
    $PY check_2d.py "$c" | tail -n 22
done
echo "=== make_contours.py ${plots[*]:---all}"
if (( ${#plots[@]} )); then $PY make_contours.py "${plots[@]}"; else $PY make_contours.py --all; fi
echo "done: post-processing"

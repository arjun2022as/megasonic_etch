#!/bin/bash
# Status of every case: RUNNING / DONE / FAILED / NOT-RUN, with the main result when done.
cd "$(dirname "$0")"
queued=$(squeue -u "$USER" -h -o %j 2>/dev/null | sort -u)
printf "%-22s %-8s %s\n" CASE STATUS RESULT
tail -n +2 cases.csv | while IFS=, read -r case _; do
    dir="results/$case"
    if grep -qx "$case" <<<"$queued"; then st=RUNNING; res=""
    elif [[ -f "$dir/summary.json" ]]; then
        st=DONE
        res=$(python3 -c "import json;r=json.load(open('$dir/summary.json'))['result'];print(f\"top {r['er_top_nm_min']:.1f} bottom {r['er_bottom_nm_min']:.1f} nm/min, bottom/top {r['uniformity']:.4f}\")" 2>/dev/null)
    elif [[ -d "$dir" ]]; then st=FAILED; res="see logs/${case}_*.out and $dir/transcript.txt"
    else st=NOT-RUN; res=""; fi
    printf "%-22s %-8s %s\n" "$case" "$st" "$res"
done

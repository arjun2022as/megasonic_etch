#!/usr/bin/env python3
"""Case 8 on Puma: the finished ANSYS Fluent plug runs, no sound vs vertical (90 deg) vs near-horizontal (15 deg) sound,
side by side. Post-processing only (no Fluent licence, no new solve; a few minutes on a login or interactive node).

    python make_case8.py

For each group (flat / comb 300 nm walls x 1 / 3 / 6 um floor plug):
  results/case8/<group>/maps_<quantity>_<view>.png   the three cases on ONE colour scale (OH-, silicate, H2/sat, speed, D_osc)
  results/case8/<group>/diff_<quantity>_<view>.png   change from the no-sound run (same mesh)
  results/case8/<group>/profiles.png                 centre-line profiles overlaid
  results/case8/case8_table.csv                      plug H2 intake and growth, mouth and plug-top H2, wet-layer etch
  results/case8/case8_summary.png                    growth speed and plug-top / mouth H2 for every group
Imposed oscillating flow + modelled mixing, not a full acoustic-streaming solution.
"""
import csv
import glob
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_contours as MC  # noqa: E402
from etchsim import props as P  # noqa: E402
from run_case import read_dumps  # noqa: E402

COND = ("no sound", "vertical 90 deg", "horizontal 15 deg")
GROUPS = {
    "flat_1um": ("B0_floor", "B_f1_I2_floor", "BA_f1_I2_t15_floor"),
    "flat_3um": ("B0_floor_l3000", "B_f1_I2_floor_l3000", "BA_f1_I2_t15_floor_l3000"),
    "flat_6um": ("B0_floor_l6000", "B_f1_I2_floor_l6000", "BA_f1_I2_t15_floor_l6000"),
    "comb_1um": ("B0_floor_r300", "B_f1_I2_floor_r300", "BA_f1_I2_t15_floor_r300"),
    "comb_3um": ("B0_floor_l3000_r300", "B_f1_I2_floor_l3000_r300", "BA_f1_I2_t15_floor_l3000_r300"),
    "comb_6um": ("B0_floor_l6000_r300", "B_f1_I2_floor_l6000_r300", "BA_f1_I2_t15_floor_l6000_r300"),
}
PLUG = re.compile(r"PLUG H2_in ([-+0-9.eE]+) mol/s/m growth ([-+0-9.eE]+) um/s")


def plug_line(case):
    """Last 'PLUG H2_in ... growth ...' line printed by the UDF report (transcript or SLURM log)."""
    hits = []
    # logs/<case>_<jobid>.out only: "<case>_*" would also match longer names (B0_floor_* -> B0_floor_r300_*)
    logs = [fn for fn in glob.glob(str(HERE / "logs" / f"{case}_*.out"))
            if re.fullmatch(re.escape(case) + r"_\d+\.out", Path(fn).name)]
    for fn in sorted(glob.glob(str(HERE / "results" / case / "*.txt"))) + sorted(logs, key=lambda f: Path(f).stat().st_mtime):
        try:
            hits += PLUG.findall(Path(fn).read_text(errors="ignore"))
        except OSError:
            pass
    return (float(hits[-1][0]), float(hits[-1][1])) if hits else (float("nan"), float("nan"))


def row(group, cond, case):
    out = HERE / "results" / case
    r = json.loads((out / "summary.json").read_text())["result"]
    _, centre = read_dumps(out)
    cen = sorted((c for c in centre if c["y"] < 0), key=lambda c: -c["y"])
    h2_in, growth = plug_line(case)
    return dict(group=group, condition=cond, case=case, plug_H2_in_mol_s_m=h2_in, growth_um_s=round(growth, 1),
                mouth_H2_x=round(cen[0]["c_h2"] / P.H2_SAT, 1) if cen else "",
                plug_top_H2_x=round(cen[-1]["c_h2"] / P.H2_SAT, 1) if cen else "",
                er_top_nm_min=round(r["er_top_nm_min"], 2), er_bottom_wet_nm_min=round(r["er_bottom_nm_min"], 2),
                bottom_over_top_wet=round(r["uniformity"], 5), dry_layers=r.get("n_dry_layers", ""),
                sealed_layers=r.get("n_sealed_layers", ""))


def summary_plot(rows, plt, dest):
    import numpy as np
    groups = list(GROUPS)
    x = np.arange(len(groups))
    fig, ax = plt.subplots(1, 2, figsize=(15, 4.8))
    cols = ("#7f7f7f", "#2a6fb0", "#e67e22")
    for k, (cond, col) in enumerate(zip(COND, cols)):
        g = [next((r["growth_um_s"] for r in rows if r["group"] == gr and r["condition"] == cond), float("nan"))
             for gr in groups]
        m = [next((r["mouth_H2_x"] for r in rows if r["group"] == gr and r["condition"] == cond), float("nan"))
             for gr in groups]
        ax[0].bar(x + (k - 1) * 0.27, g, 0.27, color=col, label=cond)
        ax[1].bar(x + (k - 1) * 0.27, [float(v or "nan") for v in m], 0.27, color=col, label=cond)
    for a in ax:
        a.set_xticks(x, [g.replace("_", "\n") for g in groups])
        a.legend(fontsize=8)
    ax[0].set(ylabel="plug growth (um/s)", title="Plug growth speed (Fluent PLUG report)")
    ax[1].axhline(13.9, color="k", ls=":", lw=1)
    ax[1].set(ylabel="H2 at the slit mouth (x saturation)", title="H2 at the mouth (plug top is held at 13.9x)")
    fig.suptitle("Case 8, ANSYS Fluent fixed floor plugs. " + MC.NOTE, fontsize=9)
    fig.tight_layout()
    fig.savefig(dest / "case8_summary.png", dpi=130)


def main():
    plt, mtri, np = MC.mpl()
    dest0 = HERE / "results" / "case8"
    dest0.mkdir(parents=True, exist_ok=True)
    rows = []
    for group, cases in GROUPS.items():
        have = [c for c in cases if (HERE / "results" / c / "summary.json").exists()]
        missing = sorted(set(cases) - set(have))
        if missing:
            print(f"{group}: missing {missing} (not run or failed); using the rest")
        for cond, case in zip(COND, cases):
            if case in have:
                rows.append(row(group, cond, case))
                print(rows[-1])
        if len(have) < 2:
            continue
        dest = dest0 / group
        dest.mkdir(exist_ok=True)
        outs = [HERE / "results" / c for c in have]
        MC.BASELINE = cases[0]                     # differences against the no-sound run of this group
        MC.profiles(have, outs, dest / "profiles.png", plt)
        MC.compare_maps(have, outs, plt, mtri, np, dest)
    with open(dest0 / "case8_table.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    summary_plot(rows, plt, dest0)
    print("wrote", dest0 / "case8_table.csv", "and", dest0 / "case8_summary.png")


if __name__ == "__main__":
    main()

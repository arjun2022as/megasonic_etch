#!/usr/bin/env python3
"""Case 10 post-processing (laptop): what the RESOLVED megasonic flow does to H2 transport above the slit.

    python analyze_resolved.py R0_flat R15_flat R90_flat R15_flat_H5 [--root results] [--out results/case10]

Per horizontal row of faces (rows_B_* = no sound, rows_S_* = sound on, cycle-averaged):
  J(y)      total H2 flux up through the row, convection + diffusion [mol/s per m depth]
  D_eff(y)  = -J / sum(dc/dy x length): the mixing the resolved flow really gives (pure diffusion -> D_H2)
  spread(y) = lateral standard deviation of c_H2 along the row (sound can only mix where this is > 0)
  D_osc(y)  closure value from the same run (velocity variance / omega), lateral mean, for comparison
Predicted steady mouth H2 with the measured D_eff:  c(0) = c_top + J_w * integral_0^H dy / D_eff(y)
(J_w = flux per wafer area; the run itself is too short for the slit to recharge, so this integral is the result,
and the instantaneous first-row value in mouth_log only shows the trend).
Every figure: resolved oscillating flow (Fluent, Navier-Stokes) - no D_osc closure; bubble-free.
"""
import argparse
import csv
import glob
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from etchsim import props as P  # noqa: E402

NOTE = "Resolved oscillating flow (ANSYS Fluent, Navier-Stokes), no D_osc closure; bubble-free; c_sat 0.70 mM ASSUMED."


def read_rows(run, phase):
    rows = []
    for fn in glob.glob(str(run / f"rows_{phase}_*.csv")):
        with open(fn, newline="") as f:
            rows += [{k: float(v) for k, v in r.items()} for r in csv.DictReader(f)]
    return rows


def profile(rows):
    """per face row (y_face): J, D_eff, lateral mean / spread of c, closure D_osc"""
    by = defaultdict(list)
    for r in rows:
        if r["len"] > 0:
            by[round(r["y_face"], 13)].append(r)
    out = []
    for y in sorted(by):
        rs = by[y]
        J = sum(r["jc"] + r["jd"] for r in rs)
        Jc = sum(r["jc"] for r in rs)
        g = sum(r["grad"] for r in rs)
        w = sum(r["len"] for r in rs)
        cm = sum(r["c_h2"] * r["len"] for r in rs) / w
        sd = math.sqrt(max(sum((r["c_h2"] - cm) ** 2 * r["len"] for r in rs) / w, 0.0))
        dosc = sum(r["d_osc"] * r["len"] for r in rs) / w
        lm = lambda k: sum(r.get(k, 0.0) * r["len"] for r in rs) / w      # noqa: E731
        out.append(dict(y=y, J=J, Jc=Jc, width=w, D_eff=-J / g if g else float("nan"), c_mean=cm, c_spread=sd,
                        d_osc=dosc, u_amp=lm("u_amp"), shear_amp=lm("shear_amp"), shear_mean=lm("shear_mean")))
    return out


def first_below(up, key, frac, ref_y=0.1e-6):
    """lowest height above which key stays below frac x its near-wafer maximum: decided by the run, not set"""
    ref = max((r[key] for r in up if r["y"] < ref_y), default=0.0)
    if ref <= 0:
        return float("nan")
    for i, r in enumerate(up):
        if all(q[key] < frac * ref for q in up[i:]):
            return r["y"]
    return float("nan")


def layers(prof):
    """thicknesses that Fluent decides: oscillating shear, extra mixing, lateral H2 spread (1 % and 5 % levels)"""
    up = [r for r in prof if r["y"] > 0]
    for r in up:
        r["extra_mix"] = max(r["D_eff"] / P.D["H2"] - 1.0, 0.0)
    return {f"{k}_{int(fr * 100)}pct_um": first_below(up, k, fr) * 1e6
            for k in ("shear_amp", "extra_mix", "c_spread") for fr in (0.05, 0.01)}


def mouth_prediction(prof, c_top, pitch=P.PITCH):
    """c(0) = c_top + J_w * int dy / D_eff over the liquid rows above the wafer (y > 0)"""
    up = [r for r in prof if r["y"] > 0 and r["width"] > 0.99 * pitch]
    J_w = sum(r["J"] for r in up) / len(up) / pitch          # steady: the same flux through every row
    integ, y_prev = 0.0, 0.0
    for r in up:                                             # rows are cell-face rows; integrate between them
        integ += (r["y"] - y_prev) / r["D_eff"]
        y_prev = r["y"]
    return c_top + J_w * integ, J_w, integ


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cases", nargs="+")
    ap.add_argument("--root", default=str(HERE / "results"))
    ap.add_argument("--out", default=str(HERE / "results" / "case10"))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    table, profs = [], {}
    for case in a.cases:
        run = Path(a.root) / case
        summ = json.loads((run / "summary.json").read_text())
        c_top = summ["c_top"]["H2"]
        for phase in ("B", "S"):
            rows = read_rows(run, phase)
            if not rows:
                continue
            prof = profile(rows)
            profs[(case, phase)] = prof
            c0, J_w, integ = mouth_prediction(prof, c_top)
            up = [r for r in prof if r["y"] > 0]
            near = [r for r in up if r["y"] < 1e-6]
            far = [r for r in up if r["y"] > 0.8 * summ["H"]]
            table.append(dict(case=case, phase="no sound" if phase == "B" else "sound", c_top_x=c_top / P.H2_SAT,
                              mouth_pred_x=c0 / P.H2_SAT, flux_w=J_w,
                              D_eff_over_D_near=sum(r["D_eff"] for r in near) / len(near) / P.D["H2"],
                              D_eff_over_D_far=sum(r["D_eff"] for r in far) / len(far) / P.D["H2"],
                              closure_Dosc_over_D_near=sum(r["d_osc"] for r in near) / len(near) / P.D["H2"],
                              spread_top_rel=far[-1]["c_spread"] / max(far[-1]["c_mean"], 1e-30),
                              H_um=summ["H"] * 1e6, **layers(prof)))
            with open(out / f"profile_{case}_{phase}.csv", "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(prof[0]), lineterminator="\n")
                w.writeheader()
                w.writerows(prof)
    with open(out / "summary_case10.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(table[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(table)
    for t in table:
        print(f"{t['case']:12s} {t['phase']:9s} mouth (pred.) {t['mouth_pred_x']:7.2f}x  top {t['c_top_x']:6.2f}x  "
              f"D_eff/D near wafer {t['D_eff_over_D_near']:7.3f}  far {t['D_eff_over_D_far']:6.3f}  "
              f"closure D_osc/D near {t['closure_Dosc_over_D_near']:7.3f}  spread at top {t['spread_top_rel']:.2e}\n"
              f"{'':22s}layers decided by Fluent (1 % level): shear {t['shear_amp_1pct_um']:.3g} um, extra mixing "
              f"{t['extra_mix_1pct_um']:.3g} um, lateral H2 spread {t['c_spread_1pct_um']:.3g} um (cell {t['H_um']:g} um)")
    try:
        plot(profs, out)
    except ImportError:
        print("matplotlib missing: no figure")


def plot(profs, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 4, figsize=(20, 5))
    for (case, phase), prof in profs.items():
        up = [r for r in prof if r["y"] > 0]
        lab = f"{case} {'no sound' if phase == 'B' else 'sound'}"
        ls = "--" if phase == "B" else "-"
        ax[0].plot([r["D_eff"] / P.D["H2"] for r in up], [r["y"] * 1e6 for r in up], ls, label=lab)
        if phase == "S":
            ax[0].plot([1 + r["d_osc"] / P.D["H2"] for r in up], [r["y"] * 1e6 for r in up], ":",
                       label=f"{case} closure 1 + D_osc/D (old method)")
        ax[1].plot([max(r["c_spread"], 1e-12) for r in up], [r["y"] * 1e6 for r in up], ls, label=lab)
        ax[2].plot([r["c_mean"] / P.H2_SAT for r in prof], [r["y"] * 1e6 for r in prof], ls, label=lab)
        if phase == "S":
            ax[3].plot([max(r["shear_amp"], 1e-3) for r in up], [r["y"] * 1e6 for r in up], ls, label=lab)
    ax[0].set(xlabel="D_eff / D_H2 (resolved)", ylabel="height above wafer (um)", yscale="log", xscale="log",
              title="mixing the resolved flow really gives")
    ax[1].set(xlabel="lateral spread of c_H2 along the row (mM)", xscale="log", yscale="log",
              title="sound can mix only where this is > 0")
    ax[2].set(xlabel="lateral mean H2 / c_sat (x)", ylabel="y (um), slit below 0", title="cycle-averaged H2")
    ax[3].set(xlabel="oscillating shear amplitude du/dy (1/s), from the run", xscale="log", yscale="log",
              title="the sheared layer Fluent produces")
    for x in ax:
        x.legend(fontsize=7)
    fig.suptitle("Case 10: " + NOTE, fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "case10_resolved.png", dpi=150)
    print("figure", out / "case10_resolved.png")


if __name__ == "__main__":
    main()

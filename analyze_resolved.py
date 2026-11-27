#!/usr/bin/env python3
"""Case 10 post-processing (laptop): what the RESOLVED megasonic flow does to H2 transport at the slit mouth.

    python analyze_resolved.py R0_flat R15_flat R90_flat R15_flat_H5 R15_flat_H20 R15_flat_fine [--root results]

The H2 at the slit mouth = top value + three resistances in series, all measured from the run:
  1. film       sum over face rows of dy_c / D_eff(row), D_eff = -J / sum(dc/dy x length)   (vertical mixing)
  2. mouth      R_m = (c at the slit top - row-mean c just above the wafer) / J_w             (spreading from the
                100 nm mouth into the 1 um pitch: the ONLY place a sideways flow can act, review A1)
  3. last half cell to the top boundary, plain diffusion
J_w = H2 made per wafer area, from the phase-B etch rate (2 H2 per Si); it is the same in both phases.

Checks that must pass (review B3) - the measurement must agree with what Fluent actually transports:
  (a) phase B: the row flux J(y) is the same at every height and equals J_w (H2 conservation)
  (b) phase B: the predicted first-row c equals Fluent's own first-row c
  (c) phase S: Fluent's Stokes layer in the mid-pitch column matches the exact u_t |1 - exp(-(1+i) y/delta)|
Spreads along the wafer come from phase-matched snapshots (field_B / field_S at whole cycles), not from
cycle averages, which a sliding field blurs (review A2).
Every figure: resolved oscillating flow (ANSYS Fluent, Navier-Stokes), no D_osc closure, bubble-free.
"""
import argparse
import cmath
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
DH2 = P.D["H2"]


def read_csvs(run, pattern):
    rows = []
    for fn in glob.glob(str(run / pattern)):
        with open(fn, newline="") as f:
            rows += [{k: float(v) for k, v in r.items()} for r in csv.DictReader(f)]
    return rows


def profile(rows):
    """per row of horizontal faces (y_face): flux J, D_eff, and cycle-averaged lateral means"""
    by = defaultdict(list)
    for r in rows:
        if r["len"] > 0:
            by[round(r["y_face"], 13)].append(r)
    out = []
    for y in sorted(by):
        rs = by[y]
        w = sum(r["len"] for r in rs)
        J = sum(r["jc"] + r["jd"] for r in rs)
        g = sum(r["grad"] for r in rs)
        lm = lambda k: sum(r.get(k, 0.0) * r["len"] for r in rs) / w      # noqa: E731
        out.append(dict(y=y, width=w, J=J, Jc=sum(r["jc"] for r in rs), D_eff=-J / g if g else float("nan"),
                        c_mean=lm("c_h2"), d_osc=lm("d_osc"), u_amp=lm("u_amp"), shear_amp=lm("shear_amp")))
    return out


def cell_rows(rows):
    """lateral (dx-weighted) mean of the cycle-averaged c_H2 per cell row, liquid above the wafer"""
    by = defaultdict(list)
    for r in rows:
        if r["y"] > 0:
            by[round(r["y"], 13)].append(r)
    return [(y, sum(r["c_h2"] * r["dx"] for r in by[y]) / sum(r["dx"] for r in by[y])) for y in sorted(by)]


def slit_top(rows, W=P.W_SLIT, dy=10e-9):
    cs = [r["c_h2"] for r in rows if -dy < r["y"] < 0 and 0 < r["x"] < W]
    return sum(cs) / len(cs) if cs else float("nan")


def production(summ):
    """H2 per wafer area [mol/m2/s] from the phase-B mean etch rate: 2 H2 per Si, both walls, 100 poly layers"""
    er = summ["result_B"]["er_mean_nm_min"] / 6e10
    n_poly = round(P.L_SLIT / P.LAYER) // 2
    return 2 * er * P.RHO_SI / P.M_SI * (2 * n_poly * P.LAYER) / P.PITCH


def resistances(rows, prof, summ, J_w):
    """c(first row) and c(slit top) predicted from the measured resistances; plus the measured values"""
    H = summ["H"]
    cr = cell_rows(rows)
    ycs = [y for y, _ in cr]
    up = {round(r["y"], 13): r for r in prof if r["y"] > 0 and r["width"] > 0.99 * P.PITCH}
    film = 0.0
    for y0, y1 in zip(ycs, ycs[1:]):
        face = min(up, key=lambda yf: abs(yf - 0.5 * (y0 + y1)))           # the face between the two cell rows
        film += (y1 - y0) / up[face]["D_eff"]
    last = (H - ycs[-1]) / DH2                                            # last half cell to the top boundary
    c_top = summ["c_top"]["H2"]
    c_row_pred = c_top + J_w * (film + last)
    c_row_meas = cr[0][1]
    c_slit = slit_top(rows)
    R_m = (c_slit - c_row_meas) / J_w
    return dict(film_s_per_m=film, R_m=R_m, c_row_pred=c_row_pred, c_row_meas=c_row_meas, c_slit_meas=c_slit,
                c_mouth_pred=c_row_pred + J_w * R_m)


def spread_profile(field):
    """lateral standard deviation of the INSTANTANEOUS c_H2 per cell row (phase-matched snapshot)"""
    by = defaultdict(list)
    for r in field:
        if r["y"] > 0:
            by[round(r["y"], 13)].append(r["c_h2"])
    out = []
    for y in sorted(by):
        v = by[y]
        m = sum(v) / len(v)
        out.append((y, math.sqrt(max(sum((c - m) ** 2 for c in v) / len(v), 0.0))))
    return out


def first_below(pairs, frac):
    """lowest height above which the value stays below frac x its value at the first row (decided by the run)"""
    if not pairs or pairs[0][1] <= 0:
        return float("nan")
    ref = pairs[0][1]
    for i, (y, _) in enumerate(pairs):
        if all(v < frac * ref for _, v in pairs[i:]):
            return y
    return float("nan")


def first_below_rows(rows, key, frac, ref_y=0.1e-6):
    """same on dict rows, reference = maximum below ref_y (used for the oscillating shear)"""
    ref = max((r[key] for r in rows if r["y"] < ref_y), default=0.0)
    if ref <= 0:
        return float("nan")
    for i, r in enumerate(rows):
        if all(q[key] < frac * ref for q in rows[i:]):
            return r["y"]
    return float("nan")


def extra_mix_height(prof, tol=0.01):
    """highest row where D_eff exceeds D_H2 by more than tol (absolute; NaN = nowhere, review B5)"""
    ys = [r["y"] for r in prof if r["y"] > 0 and r["D_eff"] / DH2 - 1 > tol]
    return max(ys) if ys else float("nan")


def stokes_check(rows, summ):
    """mid-pitch column (farthest from the slit): Fluent's oscillation amplitude vs the exact Stokes layer"""
    u_t, delta = summ["u_t"], summ["delta"]
    if u_t <= 0:
        return float("nan")
    x_far = min(r["x"] for r in rows)
    col = [r for r in rows if abs(r["x"] - x_far) < 1e-12 and 0 < r["y"] < 5 * delta]
    err = [abs(r["u_amp"] - u_t * abs(1 - cmath.exp(-(1 + 1j) * r["y"] / delta))) / u_t for r in col]
    return max(err) if err else float("nan")


def analyse(case, root):
    run = Path(root) / case
    summ = json.loads((run / "summary.json").read_text())
    J_w = production(summ)
    res = {}
    for ph in ("B", "S"):
        rows = read_csvs(run, f"rows_{ph}_*.csv")
        if not rows:
            continue
        prof = profile(rows)
        r = resistances(rows, prof, summ, J_w)
        up = [q for q in prof if q["y"] > 0 and q["width"] > 0.99 * P.PITCH]
        field = read_csvs(run, f"field_{ph}_*.csv")
        sp = spread_profile(field) if field else []
        r.update(prof=prof, spread=sp,
                 flux_check=(sum(q["J"] for q in up) / len(up) / P.PITCH) / J_w - 1,
                 flux_row_scatter=(max(q["J"] for q in up) - min(q["J"] for q in up)) / abs(sum(q["J"] for q in up) / len(up)),
                 extra_mix_um=extra_mix_height(prof) * 1e6,
                 shear_1pct_um=first_below_rows(up, "shear_amp", 0.01) * 1e6 if ph == "S" else float("nan"),
                 spread_1pct_um=first_below(sp, 0.01) * 1e6, spread_first_row=sp[0][1] if sp else float("nan"),
                 stokes_err=stokes_check(rows, summ) if ph == "S" else float("nan"))
        res[ph] = r
    return summ, J_w, res


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
        summ, J_w, res = analyse(case, a.root)
        for ph, r in res.items():
            profs[(case, ph)] = r
            table.append(dict(case=case, phase="no sound" if ph == "B" else "sound", H_um=summ["H"] * 1e6,
                              mouth_pred_x=r["c_mouth_pred"] / P.H2_SAT, slit_top_meas_x=r["c_slit_meas"] / P.H2_SAT,
                              row_pred_x=r["c_row_pred"] / P.H2_SAT, row_meas_x=r["c_row_meas"] / P.H2_SAT,
                              R_m_um_equiv=r["R_m"] * DH2 * 1e6, film_um_equiv=r["film_s_per_m"] * DH2 * 1e6,
                              flux_check=r["flux_check"], flux_row_scatter=r["flux_row_scatter"],
                              stokes_err=r["stokes_err"], shear_1pct_um=r["shear_1pct_um"],
                              extra_mix_um=r["extra_mix_um"], spread_1pct_um=r["spread_1pct_um"],
                              spread_first_row_mM=r["spread_first_row"]))
    with open(out / "summary_case10.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(table[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(table)
    for t in table:
        print(f"{t['case']:14s} {t['phase']:8s} mouth {t['mouth_pred_x']:6.2f}x (slit top now {t['slit_top_meas_x']:6.2f}x)"
              f"  mouth resistance = {t['R_m_um_equiv']:.3f} um of plain diffusion, film = {t['film_um_equiv']:.2f} um"
              f"\n{'':24s}checks: flux vs etch {t['flux_check']:+.2%}, row scatter {t['flux_row_scatter']:.2%}, "
              f"row c predicted {t['row_pred_x']:.2f}x vs Fluent {t['row_meas_x']:.2f}x, Stokes error {t['stokes_err']:.2%}"
              f"\n{'':24s}heights from the run: shear 1 % at {t['shear_1pct_um']:.3g} um, extra mixing > 1 % up to "
              f"{t['extra_mix_um']:.3g} um, H2 spread 1 % at {t['spread_1pct_um']:.3g} um (cell {t['H_um']:g} um)")
    try:
        plot(profs, out)
    except ImportError:
        print("matplotlib missing: no figure")


def plot(profs, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 4, figsize=(20, 5))
    for (case, ph), r in profs.items():
        up = [q for q in r["prof"] if q["y"] > 0]
        lab = f"{case} {'no sound' if ph == 'B' else 'sound'}"
        ls = "--" if ph == "B" else "-"
        ax[0].plot([q["D_eff"] / DH2 for q in up], [q["y"] * 1e6 for q in up], ls, label=lab)
        if ph == "S":
            ax[0].plot([1 + q["d_osc"] / DH2 for q in up], [q["y"] * 1e6 for q in up], ":",
                       label=f"{case}: old closure 1 + D_osc/D")
            ax[3].plot([max(q["shear_amp"], 1e-3) for q in up], [q["y"] * 1e6 for q in up], ls, label=lab)
        if r["spread"]:
            ax[1].plot([max(s, 1e-9) for _, s in r["spread"]], [y * 1e6 for y, _ in r["spread"]], ls, label=lab)
        ax[2].plot([q["c_mean"] / P.H2_SAT for q in r["prof"]], [q["y"] * 1e6 for q in r["prof"]], ls, label=lab)
    ax[0].set(xlabel="D_eff / D_H2 (vertical mixing, resolved)", ylabel="height above wafer (um)", yscale="log",
              xscale="log", title="vertical mixing the flow really gives")
    ax[1].set(xlabel="H2 spread along the wafer (mM, phase-matched snapshot)", xscale="log", yscale="log",
              title="sideways structure: only here can sound act")
    ax[2].set(xlabel="lateral mean H2 / c_sat (x)", ylabel="y (um), slit below 0", title="cycle-averaged H2")
    ax[3].set(xlabel="oscillating shear amplitude du/dy (1/s)", xscale="log", yscale="log",
              title="the sheared layer Fluent produces")
    for x in ax:
        x.legend(fontsize=7)
    fig.suptitle("Case 10: " + NOTE, fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "case10_resolved.png", dpi=150)
    print("figure", out / "case10_resolved.png")


if __name__ == "__main__":
    main()

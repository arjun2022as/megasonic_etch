#!/usr/bin/env python3
"""Case 6: the bubble-free window, and what to do when there is none (1D, laptop; no Fluent).

    python run_case6.py --part A    # window map: H2 in a bubble-free slit vs spin speed, temperature, pressure (~3 min)
    python run_case6.py --part B    # bubbles on: bottom etch vs spin speed, against 15 deg sound (~10 min)
    python run_case6.py --part C    # two-step recipe: gentle bubble-free pre-recess, then full rate (~6 min)

Writes results_1d/case6_*.csv and .png. ASSUMED: c_sat 0.70 mM at 60 C with the H2 van 't Hoff slope, water
properties for 5 wt% TMAH, Ea = 0.57 eV, Levich film at every spin speed, uniform recess along the slit (part C).
Imposed oscillating flow + modelled mixing, not acoustic streaming (sound only in the 15 deg reference of part B).
"""
import argparse
import csv
import math

import numpy as np

from etchsim import plug as PL
from etchsim import props as P
from etchsim import window as WN
from run_plug import OUT, mouth

RPMS = (150, 300, 600, 1000, 1500, 2000, 3000)
TEMPS_C = (20, 25, 30, 35, 40, 45, 50, 55, 60)
PRESSURES_ATM = (1, 2, 3, 5)
NUC = (("plug", PL.S_PLUG, P.W_SLIT), ("50nm", 27.0, 50e-9), ("13nm", 100.0, 13.4e-9))


def save(name, rows):
    OUT.mkdir(exist_ok=True)
    with open(OUT / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


# ------------------------------------------------------------------------------------------------ part A
def part_a():
    rows = []
    for tc in TEMPS_C:
        T = tc + 273.15
        for rpm in RPMS + (math.inf,):
            r = WN.slit_h2(T, rpm=300 if rpm == math.inf else rpm, km_scale=1e6 if rpm == math.inf else 1.0, n=400)
            row = dict(T_C=tc, rpm=rpm, er_top_nm_min=round(r["er_top_nm_min"], 2), uniformity=round(r["uniformity"], 5),
                       c_mouth_mM=round(r["c_mouth"], 3), c_max_mM=round(r["c_max"], 3), S_mouth=round(r["S_mouth"], 2),
                       S_max=round(r["S_max"], 2), min_to_500nm=round(500 / r["er_top_nm_min"], 2))
            for tag, _, reff in NUC:
                for p in PRESSURES_ATM:
                    row[f"margin_{tag}_{p}atm"] = round(WN.c_need(T, reff, p * P.P_ATM) / r["c_max"], 4)
            rows.append(row)
            print(f"{tc:3d} C {rpm:>6} rpm: top {row['er_top_nm_min']:6.1f} nm/min  H2 mouth {row['S_mouth']:6.1f}x  "
                  f"max {row['S_max']:6.1f}x  margin plug/50nm/13nm (1 atm) {row['margin_plug_1atm']:.2f} / "
                  f"{row['margin_50nm_1atm']:.2f} / {row['margin_13nm_1atm']:.2f}", flush=True)
    save("case6_window.csv", rows)
    plot_a(rows)


def plot_a(rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rp = [r for r in RPMS]
    fig, ax = plt.subplots(1, 3, figsize=(16, 5))
    X, Y = np.meshgrid(range(len(rp)), TEMPS_C)
    for a, (tag, s, _) in zip(ax, NUC):
        Z = np.array([[next(r[f"margin_{tag}_1atm"] for r in rows if r["T_C"] == t and r["rpm"] == q) for q in rp]
                      for t in TEMPS_C])
        im = a.pcolormesh(X, Y, np.log2(Z), cmap="RdBu", vmin=-3, vmax=3, shading="nearest")
        cs = a.contour(X, Y, Z, levels=[1.0], colors="k", linewidths=2)
        a.clabel(cs, fmt={1.0: "window edge"}, fontsize=8)
        for p, ls in ((3, "--"), (5, ":")):
            Zp = np.array([[next(r[f"margin_{tag}_{p}atm"] for r in rows if r["T_C"] == t and r["rpm"] == q)
                            for q in rp] for t in TEMPS_C])
            a.contour(X, Y, Zp, levels=[1.0], colors="k", linewidths=1, linestyles=ls)
        a.set_xticks(range(len(rp)), [str(q) for q in rp])
        a.set(xlabel="spin speed (rpm)", title=f"bubbles start at the {tag} level\n({s:.1f}x at 60 C)")
        a.set_yticks(TEMPS_C, [f"{t} C, {next(r['er_top_nm_min'] for r in rows if r['T_C'] == t and r['rpm'] == 300):.0f}"
                               f" nm/min" if a is ax[0] else "" for t in TEMPS_C], fontsize=8)
    ax[0].set_ylabel("temperature, and the etch rate it gives")
    cb = fig.colorbar(im, ax=ax, shrink=0.8)
    cb.set_label("log2(H2 needed / H2 present); blue = bubble-free")
    fig.suptitle("Case 6: bubble-free window, 100 nm x 10 um slit, 5 wt% TMAH. Black line = window edge "
                 "(solid 1 atm, dashed 3 atm, dotted 5 atm chamber).\nc_sat, Ea, Levich film ASSUMED; no sound.",
                 fontsize=10, y=1.04)
    fig.savefig(OUT / "case6_window.png", dpi=140, bbox_inches="tight")


# ------------------------------------------------------------------------------------------------ part B
def part_b(t_end=0.2):
    rows = []
    conds = [(f"{q} rpm, no sound", WN.slit_h2(rpm=q, n=400)["surf"], None) for q in (300, 600, 1000, 1500, 3000)]
    conds.append(("300 rpm + 15 deg sound (case 4)", mouth("A_f1_I2_t15"), PL.pump_fn(1e6, 2.0, 15.0)))
    for name, surf, pump in conds:
        for tag, s, _ in NUC + (("never", math.inf, None),):
            sm = PL.summarise(PL.simulate(surf, pump, t_end=t_end, s_nuc=s))
            rows.append(dict(condition=name, start=tag, S_mouth=round(surf["H2"] / P.H2_SAT, 1),
                             period_ms=round(sm["period_ms"], 1), growth_um_s=round(sm["growth_median_um_s"], 1),
                             er_top_nm_min=round(sm["er_top_nm_min"], 1), er_bottom_nm_min=round(sm["er_bottom_nm_min"], 1),
                             bottom_over_top=round(sm["uniformity"], 4)))
            print(rows[-1], flush=True)
    save("case6_rpm_cycle.csv", rows)


# ------------------------------------------------------------------------------------------------ part C
RECESS_NM = (0, 2, 5, 10, 20, 30, 50, 75, 100, 200, 300)


def bottom_table(t_end=0.2):
    surf = mouth("M0_none")
    out = []
    for R in RECESS_NM:
        sm = PL.summarise(PL.simulate(surf, t_end=t_end, s_nuc=PL.S_PLUG, recess=R * 1e-9))
        out.append((R, sm["er_bottom_nm_min"], sm["er_top_nm_min"]))
        print(f"recess {R:4d} nm: bottom {sm['er_bottom_nm_min']:6.1f}  top {sm['er_top_nm_min']:6.1f} nm/min", flush=True)
    return out


def grow(r0, t, table, dt=0.1):
    """Bottom recess after time t [s] at 60 C full rate with seeds (13.9x): dR/dt = ER_bottom(R)."""
    Rs, ers = np.array([x[0] for x in table], float), np.array([x[1] for x in table])
    R = r0
    for _ in range(int(round(t / dt))):
        R += np.interp(R, Rs, ers) / 60 * dt
    return R


def part_c(step1):
    """step1: (label, top nm/min, bottom nm/min) of a bubble-free gentle condition from part A."""
    table = bottom_table()
    top2 = np.mean([x[2] for x in table])
    rows = []
    label, top1, bot1 = step1
    for t1 in (0, 15, 30, 60, 90, 120):
        r1_top, r1_bot = top1 * t1 / 60, bot1 * t1 / 60
        for target in (300, 500):          # stop when the top has recessed this much
            t2 = max(0.0, (target - r1_top) / top2 * 60)
            rb = grow(r1_bot, t2, table)
            rows.append(dict(step1=label if t1 else "none", step1_s=t1, target_top_nm=target,
                             step2_s=round(t2, 1), total_s=round(t1 + t2, 1), bottom_nm=round(rb, 1),
                             bottom_over_top=round(rb / target, 3)))
            print(rows[-1], flush=True)
    save("case6_two_step.csv", rows)
    save("case6_bottom_vs_recess.csv", [dict(recess_nm=a, er_bottom_nm_min=round(b, 2), er_top_nm_min=round(c, 2))
                                         for a, b, c in table])
    plot_c(rows, table, label)


def plot_c(rows, table, label):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
    ax[0].plot([x[0] for x in table], [x[1] for x in table], "o-", color="#c0392b")
    ax[0].set(xscale="symlog", xlabel="poly-Si recess already there (nm)", ylabel="bottom etch with bubbles (nm/min)",
              title="60 C, seeds present: the bottom etches only once pockets exist")
    for target, col in ((300, "#7f8c8d"), (500, "#2a6fb0")):
        sel = [r for r in rows if r["target_top_nm"] == target]
        ax[1].plot([r["step1_s"] for r in sel], [r["bottom_over_top"] for r in sel], "o-", color=col,
                   label=f"stop when the top has recessed {target} nm")
        for r in sel:
            ax[1].annotate(f"{r['total_s']:.0f} s", (r["step1_s"], r["bottom_over_top"]), textcoords="offset points",
                           xytext=(0, -13 if target == 300 else 7), fontsize=7, ha="center", color=col)
    ax[1].set(xlabel=f"length of the gentle first step: {label} (s)", ylabel="bottom recess / top recess",
              ylim=(0, 1.05), title="Two-step recipe (labels: total etch time)")
    ax[1].legend(fontsize=8, loc="lower right")
    fig.suptitle("Case 6C: bubble-free pre-recess, then the full 60 C / 300 rpm etch (1D cycle, bubbles start at 13.9x). "
                 "Uniform recess along the slit and instant temperature switch ASSUMED; no sound", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "case6_two_step.png", dpi=140)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices="ABC", required=True)
    ap.add_argument("--step1", nargs=3, metavar=("LABEL", "TOP", "BOTTOM"),
                    default=("25 C, 1500 rpm (bubble-free)", "0", "0"))
    a = ap.parse_args()
    if a.part == "A":
        part_a()
    elif a.part == "B":
        part_b()
    else:
        part_c((a.step1[0], float(a.step1[1]), float(a.step1[2])))

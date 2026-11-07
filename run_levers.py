#!/usr/bin/env python3
"""Lever study: does megasonics / angle help, compared with TMAH concentration and dissolved gas? (1D, laptop)

    python run_levers.py --part meg     # summary of existing sound results (cases 3 and 4), no new runs
    python run_levers.py --part conc    # TMAH 2-25 wt% at 60 C / 300 rpm, no bubbles and bubble cycle (~6 min)
    python run_levers.py --part gas     # dissolved N2/O2: degassed / ~1 atm / ~2 atm, bubble cycle (~4 min)

Writes results_1d/levers_*.csv and .png. ASSUMED: rate law r ~ [H2O]^4 [OH-]^(1/4) (Seidel) for the concentration
effect, water viscosity / H2 solubility at every concentration (no salting-out), dissolved N2/O2 in equilibrium
with the bubble gas. Imposed oscillating flow + modelled mixing, not acoustic streaming.
"""
import argparse
import csv
import math

import numpy as np

from etchsim import plug as PL
from etchsim import props as P
from etchsim import window as WN
from run_plug import OUT

T60 = 333.15
WTS = (0.02, 0.05, 0.10, 0.15, 0.25)
GASES = (("degassed", 0.0), ("air-saturated (~1 atm N2+O2)", 1.0), ("N2 supersaturated (~2 atm)", 2.0))
STARTS = (("seeds (plug level)", P.W_SLIT), ("few seeds (13 nm, ~100x)", 13.4e-9))

# 2D Fluent case 3 bottom/top, no bubble (STATUS.md 2026-11-03; Puma logs)
FLUENT = {"flat": {"none": 0.95758, "75": 0.95720, "60": 0.95713, "45": 0.95727, "30": 0.95740, "15": 0.95740},
          "comb 300 nm": {"none": 0.96021, "75": 0.95989, "60": 0.95986, "45": 0.95968, "30": 0.95967, "15": 0.95961}}


def save(name, rows):
    OUT.mkdir(exist_ok=True)
    with open(OUT / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def read(name):
    with open(OUT / name, newline="") as f:
        return list(csv.DictReader(f))


def plt_():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


# ------------------------------------------------------------------------------------------------ megasonics
def part_meg():
    plt = plt_()
    pc, re_, sm = read("plug_cycle.csv"), read("realistic.csv"), read("summary.csv")
    fig, ax = plt.subplots(1, 3, figsize=(19, 5.2), gridspec_kw=dict(width_ratios=[1, 1, 1.25]))
    labels = ["none", "75", "60", "45", "30", "15"]
    x = np.arange(len(labels))
    for k, (wall, d) in enumerate(FLUENT.items()):
        ax[0].bar(x + (k - 0.5) * 0.38, [d[a] for a in labels], 0.38, label=f"{wall} walls (2D Fluent)")
    ax[0].set_xticks(x, ["no sound"] + [f"{a} deg" for a in labels[1:]])
    ax[0].set(ylim=(0.955, 0.962), ylabel="etch rate bottom / top", title="(a) No bubbles: angle changes nothing")
    ax[0].legend(fontsize=8)
    base = float(sm[0]["uniformity_bottom_over_top"])
    pts = [(float(r["I_W_cm2"]), float(r["uniformity_bottom_over_top"])) for r in sm[1:] if r["f_MHz"] not in ("", "0")]
    ax[1].scatter([p[0] for p in pts], [p[1] for p in pts], s=14, color="#2a6fb0", label="1-3 MHz, 30-90 deg (1D)")
    ax[1].axhline(base, color="k", ls=":", label=f"no sound {base:.4f}")
    ax[1].set(xlabel="intensity (W/cm2)", ylabel="etch rate bottom / top",
              title="(b) No bubbles: no frequency, power or angle beats no sound")
    ax[1].legend(fontsize=8)
    rows, names, vals = [], [], {}
    for s_tag, s in (("seeds (13.9x)", "13.87"), ("few seeds (100x)", "100.0")):
        for tag, lab in (("none", "no sound"), ("t90", "90 deg, 2 W/cm2 continuous"), ("t15", "15 deg, 2 W/cm2 continuous")):
            r = next(r for r in pc if r["sound"] == tag and abs(float(r["s_nuc"]) - float(s)) < 0.1)
            vals[(s_tag, lab)] = float(r["er_bottom_nm_min"])
        r = next(r for r in re_ if abs(float(r["start"]) - float(s)) < 0.1 and "MegPie" in r["run"])
        vals[(s_tag, "realistic MegPie 90 deg (33 of 200 ms)")] = float(r["er_bottom_nm_min"])
    for r in read("case6_rpm_cycle.csv"):
        if r["condition"] == "600 rpm, no sound" and r["start"] in ("plug", "13nm"):
            vals[("seeds (13.9x)" if r["start"] == "plug" else "few seeds (100x)", "600 rpm, no sound (case 6)")] = \
                float(r["er_bottom_nm_min"])
    names = ["no sound", "realistic MegPie 90 deg (33 of 200 ms)", "90 deg, 2 W/cm2 continuous",
             "15 deg, 2 W/cm2 continuous", "600 rpm, no sound (case 6)"]
    y = np.arange(len(names))
    for k, (s_tag, col) in enumerate((("seeds (13.9x)", "#c0392b"), ("few seeds (100x)", "#2a6fb0"))):
        v = [vals[(s_tag, n)] for n in names]
        ax[2].barh(y + (k - 0.5) * 0.38, v, 0.38, color=col, label=f"bubbles start: {s_tag}")
        for yy, vv in zip(y + (k - 0.5) * 0.38, v):
            ax[2].text(vv + 1, yy, f"{vv:.1f}", va="center", fontsize=7)
        for n, vv in zip(names, v):
            rows.append(dict(start=s_tag, condition=n, er_bottom_nm_min=round(vv, 2)))
    ax[2].set_yticks(y, names, fontsize=8)
    ax[2].invert_yaxis()
    ax[2].set(xlabel="bottom etch with bubbles, time-averaged (nm/min)\n(bubble-free: 281)",
              title="(c) With bubbles: the real MegPie does nothing;\n15 deg (not reachable with a meniscus) = 600 rpm")
    ax[2].legend(fontsize=8, loc="upper right")
    ax[2].set_xlim(0, 70)
    fig.suptitle("Megasonics and angle at 60 C, 300 rpm, 5 wt% TMAH. Imposed oscillating flow + modelled mixing, not a "
                 "full acoustic-streaming solution.", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "levers_megasonics.png", dpi=140, bbox_inches="tight")
    save("levers_megasonics.csv", rows)
    for r in rows:
        print(r)


# ------------------------------------------------------------------------------------------------ concentration
def cycle(surf, s_nuc, **kw):
    sm = PL.summarise(PL.simulate(surf, t_end=0.2, s_nuc=s_nuc, **kw))
    return sm["er_bottom_nm_min"], sm["er_top_nm_min"], sm["period_ms"]


def part_conc():
    rows = []
    for w in WTS:
        r = WN.slit_h2(T60, w=w, n=400)
        kw = dict(er_ref=WN.er_ref_conc(w), c_bulk=WN.c_oh_bulk(w))
        row = dict(wt_pct=w * 100, er_ref_nm_min=round(WN.er_ref_conc(w) * 6e10, 1), c_oh_mM=round(WN.c_oh_bulk(w), 1),
                   S_mouth=round(r["S_mouth"], 1), S_max=round(r["S_max"], 1),
                   nobubble_top=round(r["er_top_nm_min"], 1), nobubble_bottom=round(r["er_bottom_nm_min"], 1),
                   nobubble_uniformity=round(r["uniformity"], 4))
        for tag, reff in STARTS:
            row[f"margin_{("seed" if tag.startswith("seeds") else "few")}"] = round(WN.c_need(T60, reff) / r["c_max"], 3)
            bot, top, per = cycle(r["surf"], WN.c_need(T60, reff) / P.H2_SAT, **kw)
            row[f"bottom_{("seed" if tag.startswith("seeds") else "few")}"], row[f"bot_over_top_{("seed" if tag.startswith("seeds") else "few")}"] = round(bot, 1), round(bot / top, 4)
        rows.append(row)
        print(row, flush=True)
    save("levers_concentration.csv", rows)
    plot_conc(rows)


def plot_conc(rows):
    plt = plt_()
    w = [float(r["wt_pct"]) for r in rows]
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.6))
    ax[0].plot(w, [float(r["er_ref_nm_min"]) for r in rows], "o-", label="etch rate at bulk (rate law)")
    ax[0].plot(w, [float(r["nobubble_bottom"]) for r in rows], "s--", label="bottom, no bubbles")
    ax[0].set(xlabel="TMAH (wt %)", ylabel="nm/min", title="(a) Etch rate")
    ax[0].legend(fontsize=8)
    ax[1].plot(w, [float(r["S_max"]) for r in rows], "o-", color="#c0392b", label="H2 at the floor, no bubbles")
    ax[1].plot(w, [float(r["S_mouth"]) for r in rows], "o--", color="#e67e22", label="H2 at the mouth")
    for lev, lab in ((13.9, "plug survives 13.9x"), (100, "13 nm seed grows ~100x")):
        ax[1].axhline(lev, color="k", ls=":", lw=1)
        ax[1].text(w[-1], lev * 1.04, lab, ha="right", fontsize=7)
    ax[1].set(xlabel="TMAH (wt %)", ylabel="H2 (x saturation)", title="(b) H2 present vs bubble levels")
    ax[1].legend(fontsize=8)
    for k, (tag, col) in enumerate((("seed", "#c0392b"), ("few", "#2a6fb0"))):
        ax[2].plot(w, [float(r[f"bottom_{tag}"]) for r in rows], "o-", color=col,
                   label="seeds (13.9x)" if tag == "seed" else "few seeds (~100x)")
    ax[2].set(xlabel="TMAH (wt %)", ylabel="bottom etch with bubbles (nm/min)", title="(c) Bottom etch, bubbles on")
    ax[2].legend(fontsize=8)
    fig.suptitle("TMAH concentration at 60 C, 300 rpm (1D). Rate law [H2O]^4 [OH]^(1/4) and water H2 solubility "
                 "ASSUMED (no salting-out); no sound", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "levers_concentration.png", dpi=140)


# ------------------------------------------------------------------------------------------------ gas
def part_gas():
    base = WN.slit_h2(T60, n=400)
    rows = []
    for gname, p_atm in GASES:
        po = p_atm * P.P_ATM
        c_bub = WN.c_need(T60, P.W_SLIT, p_other=po)
        row = dict(gas=gname, p_other_atm=p_atm, plug_level_x=round(c_bub / P.H2_SAT, 2),
                   seed13_level_x=round(WN.c_need(T60, 13.4e-9, p_other=po) / P.H2_SAT, 2), S_max_present=round(base["S_max"], 1))
        for tag, reff in STARTS:
            bot, top, per = cycle(base["surf"], WN.c_need(T60, reff, p_other=po) / P.H2_SAT, c_bub=c_bub)
            row[f"bottom_{("seed" if tag.startswith("seeds") else "few")}"], row[f"period_ms_{("seed" if tag.startswith("seeds") else "few")}"] = round(bot, 2), round(per, 1)
        rows.append(row)
        print(row, flush=True)
    save("levers_gas.csv", rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=("meg", "conc", "gas"), required=True)
    {"meg": part_meg, "conc": part_conc, "gas": part_gas}[ap.parse_args().part]()

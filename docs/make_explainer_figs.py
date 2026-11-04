"""New figures for docs/make_explainer_doc.js (five-case explainer); run with uv run --with numpy --with matplotlib.
Original note: figures for the five-case explainer document (values from STATUS.md / case_formulas.md, 2026-11-03)."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle, FancyBboxPatch

sys.path.insert(0, r"C:\Users\paisr\phd_research\megasonic_etch")
from etchsim.nanobubble import s_eq_free  # noqa: E402
from etchsim.props import W_SLIT  # noqa: E402

OUT = Path(r"E:\claude_tools\docfigs_out")
OUT.mkdir(exist_ok=True)
NOTE = "Megasonics = imposed oscillating flow + modelled mixing, not a full acoustic-streaming solution."
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
BLUE, ORANGE, GREEN, RED, GREY, PURPLE = "#2a6fb0", "#e07b28", "#3a9a5b", "#c8423b", "#8a8a8a", "#7a5aa6"


# ---------- Fig 1: the slit, flat and comb walls, with a plug ----------
def fig_geometry():
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 5.2))
    for ax, comb, title in ((axes[0], False, "(a) flat walls"), (axes[1], True, "(b) comb walls: poly-Si recessed")):
        ax.set_xlim(-1.6, 2.6)
        ax.set_ylim(-11.2, 2.2)
        ax.axis("off")
        ax.set_title(title, fontsize=11)
        ax.add_patch(Rectangle((-1.6, 0), 4.2, 1.6, color="#cfe3f5"))
        ax.text(0.5, 1.15, "TMAH liquid film on the spinning wafer\n(H$_2$ ~63x saturation at the mouth)", ha="center",
                va="center", fontsize=8.5)
        n = 20  # drawn layers (real stack: 200 layers of 50 nm)
        h = 10 / n
        for k in range(n):
            y0 = -(k + 1) * h
            poly = k % 2 == 1
            col = "#d9a441" if poly else "#b9b9c9"
            for side in (-1, 1):
                x0 = -1.6 if side < 0 else 1.0
                w = 1.6
                if comb and poly:
                    if side < 0:
                        w = 1.6 - 0.35
                    else:
                        x0 = 1.0 + 0.35
                        w = 1.6 - 0.35
                ax.add_patch(Rectangle((x0, y0), w, h, color=col, lw=0))
        ax.add_patch(Rectangle((0, -10), 1.0, 10, color="#cfe3f5", lw=0))
        ax.add_patch(Rectangle((-1.6, -11.0), 4.2, 1.0, color="#8f8f8f", lw=0))
        ax.text(0.5, -10.5, "floor", ha="center", va="center", color="white", fontsize=9)
        # plug
        ax.add_patch(FancyBboxPatch((0.05, -9.9), 0.9, 2.6, boxstyle="round,pad=0,rounding_size=0.45",
                                    color="white", ec=BLUE, lw=1.5))
        ax.text(0.5, -8.6, "H$_2$\nplug", ha="center", va="center", fontsize=9, color=BLUE)
        ax.annotate("", xy=(0, 0.25), xytext=(1.0, 0.25), arrowprops=dict(arrowstyle="<->", lw=1))
        ax.text(0.5, 0.42, "W = 100 nm", ha="center", fontsize=8)
        ax.annotate("", xy=(2.35, 0), xytext=(2.35, -10), arrowprops=dict(arrowstyle="<->", lw=1))
        ax.text(2.45, -5, "L = 10 µm", rotation=90, va="center", fontsize=8)
        if comb:
            ax.annotate("liquid-filled pocket\nbeside the plug\n(keeps etching)", xy=(1.17, -8.75), xytext=(1.45, -6.6),
                        fontsize=7.5, arrowprops=dict(arrowstyle="->", lw=0.8))
            ax.text(-1.55, -0.55, "recess R (300 nm)", fontsize=7.5)
        else:
            ax.annotate("dry wall beside\nthe plug (no etch)", xy=(1.0, -8.75), xytext=(1.25, -6.6), fontsize=7.5,
                        arrowprops=dict(arrowstyle="->", lw=0.8))
    h1 = Rectangle((0, 0), 1, 1, color="#d9a441")
    h2 = Rectangle((0, 0), 1, 1, color="#b9b9c9")
    fig.legend([h1, h2], ["poly-Si (etched by TMAH, makes H$_2$)", "SiO$_2$ (not etched)"], loc="lower center", ncol=2,
               fontsize=9, frameon=False)
    fig.text(0.5, 0.005, "Sketch, not to scale (x stretched ~30x; 20 of the 200 layers drawn).", ha="center",
             fontsize=7.5, color="#555")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(OUT / "fig_geometry.png", dpi=170)


# ---------- Fig 2: Henry + Laplace: saturation needed to keep a bubble ----------
def fig_henry_laplace():
    r = np.logspace(np.log10(5e-9), np.log10(2e-6), 300)
    S = s_eq_free(r)
    s_plug = 1 + (s_eq_free(W_SLIT) - 1)  # slit-wide plug: one curvature of radius W/2 -> 2 gamma / W
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    ax.loglog(r * 1e9, S, color=BLUE, lw=2, label="free round bubble of radius r:  S_eq = 1 + (2γ/r − p_vap)/p_atm")
    ax.axhline(s_plug, color=RED, ls="--", lw=1.5, label=f"slit-wide plug (ends curved over W/2 only): {s_plug:.1f}x")
    ax.fill_between([5, 2000], 63, 131, color=ORANGE, alpha=0.15, label="H$_2$ actually in the slit, no bubble: 63x (mouth) - 122..131x (floor)")
    for rr, lab, off in ((10e-9, "10 nm seed", (-10, -30)), (50e-9, "50 nm = W/2:\nseed touches both walls", (8, 6))):
        ax.plot(rr * 1e9, s_eq_free(rr), "o", color="k")
        ax.annotate(f"{lab}: {s_eq_free(rr):.0f}x", (rr * 1e9, s_eq_free(rr)), textcoords="offset points",
                    xytext=off, fontsize=8)
    ax.annotate("", xy=(140, s_plug * 1.05), xytext=(55, s_eq_free(50e-9) * 0.95),
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.5))
    ax.text(150, 19, "once it spans the slit and\nstretches, it needs only 13.9x", fontsize=8, color=RED)
    ax.set_xlabel("bubble radius r (nm)")
    ax.set_ylabel("H$_2$ saturation S = c / c$_{sat}$ needed\nto keep the bubble (x)")
    ax.set_xlim(5, 2000)
    ax.set_ylim(1, 400)
    ax.legend(fontsize=7.5, loc="lower left", frameon=True, framealpha=0.9)
    fig.text(0.01, 0.01, "Liquid above the curve: the bubble grows. Below: it shrinks.\nγ = 0.0662 N/m, p_vap = 19.9 kPa "
             "(water, 60 °C; ASSUMED for 5 wt% TMAH), c_sat = 0.70 mM (ASSUMED).", fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(OUT / "fig_henry_laplace.png", dpi=170)


# ---------- Fig 3: case 3 uniformity, flat and comb ----------
def fig_case3():
    labels = ["no sound", "75°", "60°", "45°", "30°", "15°"]
    flat = [0.95758, 0.95718, 0.95713, 0.95725, 0.95740, 0.95738]
    comb = [0.96021, 0.95989, 0.95986, 0.95968, 0.95967, 0.95961]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(7.6, 3.8))
    ax.bar(x - 0.2, flat, 0.38, color=BLUE, label="flat walls (2D Fluent)")
    ax.bar(x + 0.2, comb, 0.38, color=ORANGE, label="comb walls, recess 300 nm (2D Fluent)")
    for i in range(len(x)):
        ax.text(x[i] - 0.2, flat[i] + 0.0002, f"{flat[i]:.4f}", ha="center", fontsize=7, rotation=90, va="bottom")
        ax.text(x[i] + 0.2, comb[i] + 0.0002, f"{comb[i]:.4f}", ha="center", fontsize=7, rotation=90, va="bottom")
    ax.set_xticks(x, labels)
    ax.set_ylim(0.955, 0.9625)
    ax.set_ylabel("etch rate bottom / top")
    ax.set_xlabel("incidence angle of the sound (90° = straight down; 1 MHz, 2 W/cm²)")
    ax.legend(fontsize=8, frameon=False, loc="upper right")
    ax.set_title("Case 3: tilting the sound does not make the etch more even", fontsize=10)
    fig.text(0.01, 0.01, NOTE + " No bubble in these runs.", fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "fig_case3_uniformity.png", dpi=170)


# ---------- Fig 4: case 4 plug growth speed, 2D vs 1D ----------
def fig_case4_growth():
    groups = ["1 µm plug", "3 µm plug", "6 µm plug"]
    fl = {"no sound": [147.7, 151.0, 183.4], "90°": [147.9, 151.3, 184.7], "15°": [118.3, 115.2, 136.7]}
    d1 = {"no sound": [143.3, 149.2, 196.4], "90°": [143.4, 149.6, 198.1], "15°": [113.5, 111.0, 130.0]}
    cols = {"no sound": GREY, "90°": BLUE, "15°": ORANGE}
    fig, ax = plt.subplots(figsize=(7.6, 3.8))
    x = np.arange(3)
    for i, k in enumerate(fl):
        xi = x + (i - 1) * 0.27
        ax.bar(xi, fl[k], 0.25, color=cols[k], label=f"{k}: 2D Fluent (comb walls)")
        ax.plot(xi, d1[k], "k_", ms=16, mew=2)
        for a, b in zip(xi, fl[k]):
            ax.text(a, b + 3, f"{b:.0f}", ha="center", fontsize=7.5)
    ax.plot([], [], "k_", ms=12, mew=2, label="1D model, same plug")
    ax.set_xticks(x, groups)
    ax.set_ylabel("plug growth speed (µm/s)")
    ax.set_ylim(0, 225)
    ax.legend(fontsize=8, frameon=False, ncol=2, loc="upper left")
    ax.set_title("Case 4: the plug grows 115-185 µm/s whatever its size or the angle", fontsize=10)
    fig.text(0.01, 0.01, NOTE, fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "fig_case4_growth.png", dpi=170)


# ---------- Fig 5: the saturation ladder (all five cases on one picture) ----------
def fig_ladder():
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(11, 5.6), gridspec_kw=dict(width_ratios=[1.5, 1]))
    cases = [  # label, H2 range in the slit (low, high), colour, note
        ("Case 1\nbaseline", (63, 131), GREY, "63-131x"),
        ("Case 2\nfixed plug", (13.9, 63), RED, "13.9-63x"),
        ("Case 3\n15° sound", (43, 102), BLUE, "43-102x"),
        ("Case 4\ncycle", (13.9, 122), PURPLE, "13.9-122x"),
        ("Case 5\n10 nm caps", (63, 122), GREEN, "63-122x"),
        ("Case 6\n(next)", (1, 13.9), "#bbbbbb", "target"),
    ]
    for i, (lab, (lo, hi), c, note) in enumerate(cases):
        ax.add_patch(Rectangle((i - 0.32, lo), 0.64, hi - lo, color=c, alpha=0.85 if i < 5 else 0.35,
                               hatch=None if i < 5 else "//"))
        ax.text(i, np.sqrt(lo * hi), note, ha="center", va="center", fontsize=7, rotation=90,
                color="white" if i < 5 else "k")
    for s, txt, ls in ((13.9, "13.9x: a slit-wide\nplug survives", "--"), (27, "27x: a 50 nm\nbubble survives", ":"),
                       (132, "~130x: a 10 nm\nseed can grow", "-.")):
        ax.axhline(s, color="k", ls=ls, lw=0.9)
        ax.text(5.55, s, txt, fontsize=7.5, ha="left", va="center")
    ax.axhline(1, color="k", lw=0.6)
    ax.text(5.55, 1.1, "1x: saturated", fontsize=7.5, ha="left", va="center")
    ax.set_yscale("log")
    ax.set_ylim(0.9, 400)
    ax.set_xlim(-0.6, 7.0)
    ax.set_xticks(range(6), [c[0] for c in cases], fontsize=7.5)
    ax.set_ylabel("dissolved H$_2$ in the slit (x saturation)")
    ax.set_title("(a) where each case sits on the saturation ladder", fontsize=10)

    rows = [("no bubble (cases 1, 3)", 281, GREY), ("small caps, 10 % cover (5)", 254, GREEN),
            ("small caps, 30 % cover (5)", 200, GREEN), ("plug cycle, comb 300 nm, steady (4)", 286, PURPLE),
            ("plug cycle, comb, 2-min avg from flat start (4)", 158, PURPLE),
            ("plug cycle, flat walls (4)", 3, PURPLE), ("fixed plug on the floor (2)", 0, RED)]
    y = np.arange(len(rows))[::-1]
    bx.barh(y, [r[1] for r in rows], color=[r[2] for r in rows])
    for yy, r in zip(y, rows):
        bx.text(r[1] + 4, yy, f"{r[1]}", va="center", fontsize=8)
    bx.set_yticks(y, [r[0] for r in rows], fontsize=7.5)
    bx.set_xlim(0, 330)
    bx.set_xlabel("etch rate at the slit bottom (nm/min)")
    bx.set_title("(b) what it does to the bottom of the slit", fontsize=10)
    fig.text(0.01, 0.01, NOTE + " c_sat = 0.70 mM, bubble-start level, coverage ASSUMED.", fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "fig_ladder.png", dpi=170)


for f in (fig_geometry, fig_henry_laplace, fig_case3, fig_case4_growth, fig_ladder):
    f()
print("ok", sorted(p.name for p in OUT.iterdir()))

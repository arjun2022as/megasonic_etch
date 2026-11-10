"""Figures for the four-case comparison document (all conditions with bubbles).

    uv run --with numpy --with matplotlib python docs/make_four_cases_figs.py

Writes E:/claude_tools/docfigs_out/four_*.png. Numbers come from etchsim (acoustics) and results_1d/*.csv.
Imposed oscillating flow + modelled mixing, not a full acoustic-streaming solution. c_sat, Ea, Levich film ASSUMED.
"""
import csv
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from etchsim import acoustics as AC  # noqa: E402

ONE = ROOT / "results_1d"
OUT = Path("E:/claude_tools/docfigs_out")
OUT.mkdir(parents=True, exist_ok=True)
NOTE = "Imposed oscillating flow + modelled mixing, not a full acoustic-streaming solution. c_sat, Ea, Levich film ASSUMED."
C_NONE, C_HOR, C_VER, C_LEV = "#7f7f7f", "#e07b24", "#2f6db5", "#3a9a4a"


def rows(name):
    with open(ONE / name, newline="") as f:
        return list(csv.DictReader(f))


# ------------------------------------------------------------------ figure 1: what the wafer feels vs angle
def fig_components():
    th = [0.5 + 0.5 * i for i in range(180)]
    w = [AC.wall_velocities(2.0, t) for t in th]
    fig, ax = plt.subplots(1, 3, figsize=(13.5, 4.3), gridspec_kw=dict(width_ratios=[1.25, 1, 1]))
    a = ax[0]
    a.plot(th, [x["u_t"] for x in w], color=C_HOR, lw=2.2, label="sideways (tangential) liquid speed u_t")
    a.plot(th, [x["u_n"] for x in w], color=C_VER, lw=2.2, label="up-down (normal) liquid speed u_n")
    a2 = a.twinx()
    a2.plot(th, [x["p_wall"] / 1e6 for x in w], color="k", ls="--", lw=1.4, label="sound pressure at the wafer")
    a2.set_ylabel("pressure amplitude at the wafer (MPa)")
    a2.set_ylim(0, 0.55)
    for t, c in ((15, C_HOR), (90, C_VER)):
        x = AC.wall_velocities(2.0, t)
        a.plot([t], [x["u_t"]], "o", color=c)
        a.annotate(f"{t}°: u_t {x['u_t']:.3f}, u_n {x['u_n']:.3f} m/s", (t, x["u_t"]),
                   xytext=(88, 0.20) if t == 90 else (17, 0.27), textcoords="data", ha="right" if t == 90 else "left",
                   fontsize=8, color=c, arrowprops=dict(arrowstyle="-", color=c, lw=0.6) if t == 90 else None)
    a.set_xlabel("incidence angle θ (90° = straight down)")
    a.set_ylabel("liquid speed amplitude at the wafer (m/s)")
    a.set_xlim(0, 90)
    a.set_ylim(0, 0.36)
    h1, l1 = a.get_legend_handles_labels()
    h2, l2 = a2.get_legend_handles_labels()
    a.legend(h1 + h2, l1 + l2, fontsize=8, loc="lower left", bbox_to_anchor=(0.0, 0.08))
    a.set_title("(a) 1 MHz, 2 W/cm² at a Si wafer (Brekhovskikh reflection)", fontsize=10)

    for k, (title, vertical) in enumerate((("(b) vertical sound (90°, flat MegPie)", True),
                                           ("(c) horizontal sound (15°)", False))):
        b = ax[k + 1]
        b.add_patch(Rectangle((0, 0), 4.5, 3, color="#b9b9c9"))
        b.add_patch(Rectangle((5.5, 0), 4.5, 3, color="#b9b9c9"))
        b.add_patch(Rectangle((4.5, 0), 1, 3, color="#cfe2f3"))
        b.add_patch(Rectangle((0, 3), 10, 4, color="#cfe2f3"))
        b.text(5, 1.3, "slit\n100 nm", ha="center", fontsize=8)
        b.text(0.2, 0.3, "wafer (stack)", fontsize=8)
        if vertical:
            b.add_patch(FancyArrowPatch((5, 7.3), (5, 5.0), arrowstyle="-|>", mutation_scale=18, color=C_VER, lw=2))
            b.text(5.2, 6.2, "wave in", color=C_VER, fontsize=8)
            for x in (1.5, 3, 7, 8.5):
                b.add_patch(FancyArrowPatch((x, 3.15), (x, 3.45), arrowstyle="<|-|>", mutation_scale=7, color=C_VER, lw=1))
            b.text(5, 4.0, "velocity node at the wafer: |1-R| = 0.14\npressure antinode: |1+R| = 1.86", ha="center",
                   fontsize=8, color=C_VER)
            b.text(5, 2.3, "whole slit squeezed\nin phase: ~2 nm", ha="center", fontsize=7.5)
            b.text(0.2, 6.5, "no sideways slip,\nno shear layer,\nno flow into the slit", fontsize=8)
        else:
            b.add_patch(FancyArrowPatch((1.2, 7.3), (4.4, 5.0), arrowstyle="-|>", mutation_scale=18, color=C_HOR, lw=2))
            b.text(0.2, 6.5, "wave in", color=C_HOR, fontsize=8)
            b.add_patch(Rectangle((0, 3), 10, 0.55, color="#fde3c8"))
            for x in (1.5, 3, 7, 8.5):
                b.add_patch(FancyArrowPatch((x - 0.6, 3.3), (x + 0.6, 3.3), arrowstyle="<|-|>", mutation_scale=8, color=C_HOR, lw=1.2))
            b.text(5, 4.0, "sideways slip u_t = 0.31 m/s in a\nStokes layer δ = 0.39 µm: mixes the film", ha="center",
                   fontsize=8, color=C_HOR)
            b.text(5, 2.3, "inside the slit the\nslip dies in ~100 nm", ha="center", fontsize=7.5)
        b.set_xlim(0, 10)
        b.set_ylim(0, 7.6)
        b.set_axis_off()
        b.set_title(title, fontsize=10)
    fig.text(0.5, 0.005, "Sketches (b, c) not to scale. " + NOTE, ha="center", fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "four_components.png", dpi=170)
    plt.close(fig)
    for t in (90, 75, 60, 45, 30, 15, 10):
        x = AC.wall_velocities(2.0, t)
        print(f"theta {t:2d}: u_t {x['u_t']:.4f}  u_n {x['u_n']:.4f}  p_wall {x['p_wall']/1e6:.4f} MPa  |R| {abs(x['R']):.3f}")


# ------------------------------------------------------------------ figure 2: levers with bubbles
def fig_levers():
    win = rows("case6_window.csv")
    fig, ax = plt.subplots(1, 3, figsize=(13.5, 4.4))
    # (a) temperature at 300 rpm
    a = ax[0]
    t300 = [r for r in win if r["rpm"] == "300"]
    T = [float(r["T_C"]) for r in t300]
    smax = [float(r["S_max"]) for r in t300]
    a.plot(T, smax, "o-", color="k", label="H₂ present at the floor (no bubble)")
    for tag, lab, c in (("plug", "plug starts (seeds)", "#c0392b"), ("50nm", "50 nm seed starts", "#d68910"),
                        ("13nm", "13 nm seed starts (few seeds)", "#2471a3")):
        a.plot(T, [float(r["S_max"]) * float(r[f"margin_{tag}_1atm"]) for r in t300], "--", color=c, label=lab)
    a.set_yscale("log")
    a.set_xlabel("temperature (°C), 300 rpm, 5 wt %")
    a.set_ylabel("H₂ saturation S (×)")
    a.legend(fontsize=7.5, loc="lower right")
    for r in t300:
        if r["T_C"] in ("20", "30", "40", "50", "60"):
            a.annotate(f"{float(r['er_top_nm_min']):.0f} nm/min", (float(r["T_C"]), float(r["S_max"])),
                       xytext=(0, 7), textcoords="offset points", fontsize=7, ha="center")
    a.set_title("(a) temperature: bubbles start where black > dashed", fontsize=10)
    # (b) spin speed at 60 C, bubbles on
    b = ax[1]
    rc = [r for r in rows("case6_rpm_cycle.csv") if "no sound" in r["condition"]]
    rpms = sorted({int(r["condition"].split()[0]) for r in rc})
    get = lambda rpm, st: float(next(r for r in rc if r["condition"].startswith(f"{rpm} ") and r["start"] == st)["er_bottom_nm_min"])
    b.plot(rpms, [get(x, "plug") for x in rpms], "s-", color="#c0392b", label="bubbles: seeds present (13.9×)")
    b.plot(rpms, [get(x, "13nm") for x in rpms], "o-", color="#2471a3", label="bubbles: few seeds (~100×)")
    b.plot(rpms, [get(x, "never") for x in rpms], ":", color="k", label="never any bubble (reference)")
    b.axhline(54.5, color=C_HOR, lw=1, ls="--")
    b.text(1600, 60, "15° sound, few seeds: 54.5", color=C_HOR, fontsize=7.5)
    b.set_xlabel("spin speed (rpm), 60 °C, 5 wt %")
    b.set_ylabel("bottom etch, time-averaged (nm/min)")
    b.legend(fontsize=7.5, loc="center right")
    b.set_title("(b) spin speed, with bubbles (1D cycle, flat walls)", fontsize=10)
    # (c) concentration at 60 C, 300 rpm, bubbles on
    c = ax[2]
    cr = rows("levers_concentration.csv")
    wt = [float(r["wt_pct"]) for r in cr]
    c.plot(wt, [float(r["bottom_seed"]) for r in cr], "s-", color="#c0392b", label="bubbles: seeds present")
    c.plot(wt, [float(r["bottom_few"]) for r in cr], "o-", color="#2471a3", label="bubbles: few seeds")
    c.plot(wt, [float(r["nobubble_bottom"]) for r in cr], ":", color="k", label="never any bubble")
    c2 = c.twinx()
    c2.plot(wt, [float(r["S_max"]) for r in cr], "^--", color=C_LEV, label="floor H₂ (×, right axis)")
    c2.set_ylabel("floor H₂ saturation (×)", color=C_LEV)
    c2.set_ylim(0, 140)
    c.set_xlabel("TMAH (wt %), 60 °C, 300 rpm")
    c.set_ylabel("bottom etch (nm/min)")
    h1, l1 = c.get_legend_handles_labels()
    h2, l2 = c2.get_legend_handles_labels()
    c.legend(h1 + h2, l1 + l2, fontsize=7.5, loc="center left")
    c.set_title("(c) concentration, with bubbles", fontsize=10)
    fig.text(0.5, 0.005, "1D models (case 6). Seidel rate law, water H₂ solubility (no salting-out), c_sat, Ea, Levich film ASSUMED.",
             ha="center", fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "four_levers.png", dpi=170)
    plt.close(fig)


# ------------------------------------------------------------------ figure 3: the four cases side by side
def fig_compare():
    win = {(r["T_C"], r["rpm"]): r for r in rows("case6_window.csv")}
    conc = {r["wt_pct"]: r for r in rows("levers_concentration.csv")}
    sc = {r["scenario"]: r for r in rows("case7_scenarios.csv")}
    labels = ["no sound", "horizontal\n15°", "vertical 90°\nreal MegPie", "1000 rpm\n60 °C", "25 wt %\n60 °C",
              "25 °C\n2000 rpm"]
    cols = [C_NONE, C_HOR, C_VER, C_LEV, C_LEV, C_LEV]
    mouth = [63.1, 43.0, float(sc["no sound"]["mouth_mean_x"]), float(win[("60", "1000")]["S_mouth"]),
             float(conc["25.0"]["S_mouth"]), float(win[("25", "2000")]["S_mouth"])]
    floor = [121.3, 101.7, float(sc["no sound"]["floor_mean_x"]), float(win[("60", "1000")]["S_max"]),
             float(conc["25.0"]["S_max"]), float(win[("25", "2000")]["S_max"])]
    fig, ax = plt.subplots(1, 3, figsize=(14, 4.6))
    a = ax[0]
    x = range(len(labels))
    a.bar([i - 0.2 for i in x], mouth, 0.4, color=cols, alpha=0.55, label="mouth")
    a.bar([i + 0.2 for i in x], floor, 0.4, color=cols, label="floor")
    for y, t in ((13.9, "plug 13.9×"), (27, "50 nm 27×"), (98.6, "13 nm ~100×")):
        a.axhline(y, color="k", ls=":", lw=0.9)
        a.text(-0.45, y + 1.5, t, fontsize=7, ha="left")
    for i in x:
        a.text(i + 0.2, floor[i] + 2, f"{floor[i]:.0f}", ha="center", fontsize=7)
        a.text(i - 0.2, mouth[i] + 2, f"{mouth[i]:.0f}", ha="center", fontsize=7)
    a.set_xticks(list(x))
    a.set_xticklabels(labels, fontsize=7.5)
    a.set_ylabel("H₂ saturation (×), no bubble yet")
    a.set_title("(a) H₂ at the mouth (light) and floor (dark)", fontsize=10)
    # (b) bottom etch with bubbles: seeds vs few seeds
    b = ax[1]
    seeds = [2.98, 3.84, 2.98, 4.1, 2.6, None]
    few = [28.7, 54.5, 28.85, 283.6, 194.4, None]
    b.bar([i - 0.2 for i in x], [s or 0 for s in seeds], 0.4, color="#c0392b", label="seeds present (13.9×)")
    b.bar([i + 0.2 for i in x], [f or 0 for f in few], 0.4, color="#2471a3", label="few seeds (~100×)")
    for i in x:
        if seeds[i] is not None:
            b.text(i - 0.2, seeds[i] + 4, f"{seeds[i]:g}", ha="center", fontsize=7)
            b.text(i + 0.2, few[i] + 4, f"{few[i]:g}", ha="center", fontsize=7)
    b.text(5, 30, "bubble-free\neven with seeds\n(margin 1.06):\n28.8 nm/min\nbottom", ha="center", fontsize=7, color=C_LEV)
    b.set_xticks(list(x))
    b.set_xticklabels(labels, fontsize=7.5)
    b.set_ylabel("bottom etch with bubbles, flat walls (nm/min)")
    b.legend(fontsize=7.5)
    b.set_title("(b) bottom etch with bubbles (1D cycle)", fontsize=10)
    # (c) comb walls, seeds: 2-min bottom recess from flat walls
    c = ax[2]
    st = {r["condition"]: r for r in rows("case8_startup.csv") if float(r["start_recess_nm"]) == 0.0}
    names = ["no sound", "horizontal 15 deg, continuous", "vertical 90 deg, real MegPie (33 of 200 ms)"]
    vals = [float(st[n]["bottom_nm_120s"]) for n in names]
    two = rows("case6_two_step.csv")
    ts = next(r for r in two if r["step1_s"] == "30" and r["target_top_nm"] == "500")
    c.bar([0, 1, 2], vals, color=[C_NONE, C_HOR, C_VER])
    for i, v in enumerate(vals):
        c.text(i, v + 6, f"{v:.0f} nm", ha="center", fontsize=8)
    c.set_xticks([0, 1, 2])
    c.set_xticklabels(["no sound", "horizontal\n15°", "vertical 90°\nreal MegPie"], fontsize=8)
    c.set_ylabel("bottom recess after 2 min (nm), comb walls, seeds")
    c.axhline(562, color="k", ls=":", lw=0.9)
    c.text(2.4, 568, "bubble-free 562", fontsize=7, ha="right")
    c.text(1, 470, f"levers: two-step (25 °C / 2000 rpm 30 s,\nthen 60 °C) gives bottom/top {float(ts['bottom_over_top']):.2f}"
           f"\nat 500 nm top (single step 0.46)", ha="center", fontsize=7.5, color=C_LEV)
    c.set_ylim(0, 640)
    c.set_title("(c) 2-minute bottom recess with bubbles", fontsize=10)
    fig.text(0.5, 0.005, NOTE + " Few-seeds column for 25 °C / 2000 rpm: bubble-free at every seed level.",
             ha="center", fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "four_compare.png", dpi=170)
    plt.close(fig)
    print("mouth", mouth)
    print("floor", floor)
    print("2-min", vals, "two-step 30 s / 500 nm", ts["bottom_over_top"])


if __name__ == "__main__":
    fig_components()
    fig_levers()
    fig_compare()
    print("figures in", OUT)

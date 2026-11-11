"""Depict the case-8 no-sound Fluent fixed-plug snapshots (flat vs comb 300 nm walls).

Values are copied from the Fluent run summaries (case 8, no megasonics, plug at the floor).
Flat 1 um growth (143.0 um/s) is from the 90 deg twin run (B0_floor did not print it).

Run: uv run --with numpy --with matplotlib python docs/make_plug_snapshot_fig.py [out.png]
"""
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle

L_PLUG = [1, 3, 6]  # um
DATA = {
    "Flat wall": dict(growth=[143.0, 145.2, 175.0], mouth=[63.3, 61.4, 56.9],
                      ratio=[0.96496, 0.97821, 0.99272], color="#2a78d6", marker="o"),
    "Comb wall (300 nm recess)": dict(growth=[147.7, 151.0, 183.4], mouth=[63.0, 61.1, 56.5],
                                      ratio=[0.96715, 0.97960, 0.99319], color="#eb6834", marker="s"),
}
PLUG_TOP = 13.9
INK, INK2, GRID = "#222222", "#555555", "#e4e4e4"


def style(ax):
    ax.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#999999")
    ax.tick_params(colors=INK2, labelsize=9)
    ax.set_xticks(L_PLUG)
    ax.set_xlim(0.3, 6.7)
    ax.set_xlabel("Plug length at the floor (µm)", color=INK2, fontsize=9.5)


def series(ax, key, labels=None, fmt="{:.1f}", hollow_first=False):
    for name, d in DATA.items():
        y = d[key]
        ax.plot(L_PLUG, y, color=d["color"], lw=2, zorder=2)
        for i, (x, v) in enumerate(zip(L_PLUG, y)):
            hollow = hollow_first and name == "Flat wall" and i == 0
            ax.plot(x, v, d["marker"], ms=8, zorder=3, mec="white" if not hollow else d["color"],
                    mew=2 if not hollow else 1.8, mfc="white" if hollow else d["color"])


def schematic(ax):
    ax.set_xlim(0, 10)
    ax.set_ylim(-2.8, 11.6)
    ax.axis("off")
    xs = [1.2, 4.4, 7.6]
    for x0, lp in zip(xs, L_PLUG):
        w = 1.4
        # slit walls (10 um deep, mouth at y=10)
        ax.add_patch(Rectangle((x0 - 0.5, 0), 0.5, 10, fc="#d9d9d9", ec="none"))
        ax.add_patch(Rectangle((x0 + w, 0), 0.5, 10, fc="#d9d9d9", ec="none"))
        ax.add_patch(Rectangle((x0 - 0.5, -0.5), w + 1.0, 0.5, fc="#bdbdbd", ec="none"))
        ax.add_patch(Rectangle((x0, 0), w, 10, fc="#eaf2fc", ec="none"))  # liquid
        ax.add_patch(Rectangle((x0 + 0.08, 0.04), w - 0.16, lp, fc="white", ec="#888888",
                               lw=1.2, joinstyle="round"))  # H2 plug
        ax.text(x0 + w / 2, lp / 2, "H₂" if lp < 2 else "H₂\nplug", ha="center", va="center", fontsize=7.5, color=INK2)
        ax.add_patch(FancyArrowPatch((x0 + w / 2, min(lp + 2.2, 9.6)), (x0 + w / 2, lp + 0.15),
                                     arrowstyle="-|>", mutation_scale=10, color="#2a78d6", lw=1.4))
        ax.text(x0 + w / 2, -1.05, f"{lp} µm", ha="center", fontsize=9, color=INK)
    ax.text(0.3, 10.35, "mouth (spin flow above)", fontsize=8, color=INK2)
    ax.text(5.0, 11.2, "Frozen plug snapshots (slit 100 nm × 10 µm, not to scale)",
            ha="center", fontsize=9, color=INK)
    ax.text(5.0, -2.2, "blue arrows: dissolved H₂ flows into the plug top (held at 13.9×)",
            ha="center", va="center", fontsize=7.5, color="#2a78d6")


def main(out):
    fig = plt.figure(figsize=(11, 7.6))
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 1], hspace=0.42, wspace=0.32)
    ax0 = fig.add_subplot(gs[0, 0])
    schematic(ax0)
    ax0.set_title("A  What was simulated", loc="left", fontsize=11, color=INK, fontweight="bold")

    ax1 = fig.add_subplot(gs[0, 1:])
    style(ax1)
    series(ax1, "growth", hollow_first=True)
    for name, d in DATA.items():
        for x, v in zip(L_PLUG, d["growth"]):
            off = 9 if name.startswith("Comb") else -15
            ax1.annotate(f"{v:.1f}", (x, v), textcoords="offset points", xytext=(0, off),
                         ha="center", fontsize=8.5, color=INK)
    ax1.set_ylabel("Plug growth speed (µm/s)", color=INK2, fontsize=9.5)
    ax1.set_ylim(130, 195)
    ax1.set_title("B  Plug grows faster as it gets longer; comb walls feed it ~3–5 % more",
                  loc="left", fontsize=11, color=INK, fontweight="bold")
    ax1.text(0.4, 191, "hollow marker = flat 1 µm value taken from the 90° twin run", fontsize=7.5, color=INK2)

    ax2 = fig.add_subplot(gs[1, 0:2])
    style(ax2)
    series(ax2, "mouth")
    ax2.axhline(PLUG_TOP, color=INK2, ls="--", lw=1.2)
    ax2.text(6.6, PLUG_TOP + 2, "plug top = 13.9× (bubble pressure 1.41 MPa, fixed)",
             ha="right", fontsize=8.5, color=INK2)
    for name, d in DATA.items():
        for x, v in zip(L_PLUG, d["mouth"]):
            off = 8 if name == "Flat wall" else -14
            ax2.annotate(f"{v:.1f}×", (x, v), textcoords="offset points", xytext=(0, off),
                         ha="center", fontsize=8.5, color=INK)
    ax2.set_ylabel("Dissolved H₂ / saturation", color=INK2, fontsize=9.5)
    ax2.set_ylim(0, 75)
    ax2.set_title("C  Mouth H₂ falls (63 → 57×) as the longer plug soaks up more H₂",
                  loc="left", fontsize=11, color=INK, fontweight="bold")

    ax3 = fig.add_subplot(gs[1, 2])
    style(ax3)
    series(ax3, "ratio")
    for name, d in DATA.items():
        x, v = L_PLUG[-1], d["ratio"][-1]
    ax3.set_ylabel("Wet-part bottom/top etch", color=INK2, fontsize=9.5)
    ax3.set_ylim(0.955, 1.0)
    ax3.set_title("D  Liquid above the plug", loc="left", fontsize=11, color=INK, fontweight="bold")
    ax3.text(0.5, 0.9575, "shorter wet column → more\nuniform; NOT comparable\nwith bubble-free 0.958",
             fontsize=7.5, color=INK2)

    handles = [plt.Line2D([], [], color=d["color"], lw=2, marker=d["marker"], ms=7, mec="white",
                          label=n) for n, d in DATA.items()]
    fig.legend(handles=handles, loc="upper center", ncol=2, frameon=False, fontsize=10,
               bbox_to_anchor=(0.5, 0.995))
    fig.text(0.5, 0.012,
             "Case 8, NO megasonics. ANSYS Fluent 2024R1, plug frozen at the floor (Fluent cannot move it). "
             "5 wt% TMAH, 60 °C, 300 rpm (ASSUMED process values). "
             "Cycle times (48.6 / 37.3 ms) come from the 1D model, not from this figure.",
             ha="center", fontsize=8, color=INK2)
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    print("saved", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "plug_snapshots_no_sound.png")

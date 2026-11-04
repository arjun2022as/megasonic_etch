"""Case 4 picture: how H2 saturation builds up in the slit from a fresh refill, and how the bubble cycle runs.

1D growing-plug model (etchsim/plug.py), flat walls, no sound, M0_none mouth values (63x sat). t = 0 is a slit just
refilled with mouth liquid. Three bubble-start levels: never (no bubbles), 100x (few seeds), 13.9x (seeds present).
Output: results_1d/cycle_map.png (space-time maps + a strip of slit snapshots) and cycle_map.csv (snapshot times).
Imposed oscillating flow + modelled mixing, not acoustic streaming (no sound in these runs).
"""
import csv
import math

import numpy as np

from etchsim import plug as PL
from run_plug import OUT, mouth

T_END = 0.16
RUNS = [("no bubbles (never)", math.inf), ("bubbles start at 100x", 100.0), ("bubbles start at 13.9x", PL.S_PLUG)]


def grid(run, t_end, nt=640):
    """Resample the step history onto a uniform time grid (the state at each time)."""
    ts = np.array([h["t"] for h in run["hist"]])
    tg = (np.arange(nt) + 0.5) * t_end / nt
    idx = np.clip(np.searchsorted(ts, tg), 0, len(ts) - 1)
    S = np.array([run["hist"][i]["S"] for i in idx])
    top = np.array([run["hist"][i]["b"] if run["hist"][i]["plug"] else np.nan for i in idx])
    return tg, S, top


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize

    surf = mouth("M0_none")
    res = {}
    for name, s in RUNS:
        run = PL.simulate(surf, t_end=T_END, s_nuc=s, keep_profiles=True, dt_max=2e-4)
        res[name] = run
        print(name, PL.summarise(run)["period_ms"], "ms period;", [(e, round(t * 1e3, 2)) for e, t in run["events"][:6]])
    z = res[RUNS[0][0]]["z_ref"] * 1e6

    cmap = plt.get_cmap("turbo").copy()
    cmap.set_bad("white")
    norm = Normalize(0, 130)
    fig = plt.figure(figsize=(13, 9.6))
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 0.9], hspace=0.42, wspace=0.18)
    for j, (name, s) in enumerate(RUNS):
        ax = fig.add_subplot(gs[0, j])
        tg, S, top = grid(res[name], T_END)
        im = ax.pcolormesh(tg * 1e3, z, S.T, cmap=cmap, norm=norm, shading="auto", rasterized=True)
        ax.plot(tg * 1e3, top * 1e6, color="k", lw=0.8)
        ax.contour(tg * 1e3, z, np.nan_to_num(S.T, nan=0), levels=[13.9], colors="w", linewidths=0.6,
                   linestyles="--")
        ax.set_ylim(10, 0)
        ax.set_title(name, fontsize=10)
        ax.set_xlabel("time after refill (ms)")
        if j == 0:
            ax.set_ylabel("depth below the mouth (µm)")
        if s == 100.0:
            nuc = [t for e, t in res[name]["events"] if e == "nucleate"]
            if nuc:
                ax.annotate("H$_2$ reaches 100x:\nbubble appears", (nuc[0] * 1e3, 9.8), xytext=(nuc[0] * 1e3 + 14, 8.6),
                            fontsize=7.5, color="k", bbox=dict(fc="w", ec="none", alpha=0.85),
                            arrowprops=dict(arrowstyle="->", color="k"))
        if s == math.inf:
            ax.text(40, 5, "H$_2$ builds up and\nlevels off at ~122x", color="w", fontsize=8)
    cb = fig.colorbar(im, ax=fig.axes, shrink=0.42, anchor=(0, 1), pad=0.01)
    cb.set_label("H$_2$ saturation S (x)")
    fig.text(0.5, 0.49, "Top: space-time maps (white = gas plug, black line = plug top, white dashes = 13.9x). "
             "Bottom: the slit at chosen moments, bubbles start at 100x.", ha="center", fontsize=9)

    # strip of snapshots for the 100x run
    name = RUNS[1][0]
    hist = res[name]["hist"]
    ev = res[name]["events"]
    nuc = [t for e, t in ev if e == "nucleate"]
    vent = [t for e, t in ev if e == "vent"]
    t_n, t_v = nuc[0], vent[0]
    picks = [(1e-4, "0.1 ms\nfresh refill"), (0.5 * t_n, f"{0.5 * t_n * 1e3:.0f} ms\nH$_2$ building"),
             (t_n - 1e-4, f"{t_n * 1e3:.0f} ms\nreaches 100x"), (t_n + 0.3 * (t_v - t_n), f"{(t_n + 0.3 * (t_v - t_n)) * 1e3:.0f} ms\nplug grows"),
             (t_n + 0.7 * (t_v - t_n), f"{(t_n + 0.7 * (t_v - t_n)) * 1e3:.0f} ms\nplug drinks H$_2$"),
             (t_v - 2e-4, f"{t_v * 1e3:.0f} ms\nreaches mouth"), (t_v + 1e-4, f"{t_v * 1e3:.0f} ms\nvented, refilled"),
             (t_v + 0.5 * t_n, f"{(t_v + 0.5 * t_n) * 1e3:.0f} ms\nbuilding again")]
    ts = np.array([h["t"] for h in hist])
    ax = fig.add_subplot(gs[1, :])
    rows = []
    for k, (tp, lab) in enumerate(picks):
        i = int(np.clip(np.searchsorted(ts, tp), 0, len(hist) - 1))
        S = hist[i]["S"]
        x0 = k * 1.6
        ax.pcolormesh([x0, x0 + 0.7], np.concatenate(([0], (z[1:] + z[:-1]) / 2, [10])), S[:, None], cmap=cmap,
                      norm=norm, shading="flat", rasterized=True)
        ax.add_patch(matplotlib.patches.Rectangle((x0 - 0.25, 0), 0.25, 10, color="#b9b9c9"))
        ax.add_patch(matplotlib.patches.Rectangle((x0 + 0.7, 0), 0.25, 10, color="#b9b9c9"))
        if hist[i]["plug"]:
            b = hist[i]["b"] * 1e6
            ax.add_patch(matplotlib.patches.FancyBboxPatch((x0 + 0.04, b + 0.05), 0.62, 9.9 - b, color="white", ec="#2a6fb0",
                                                           lw=1.4, boxstyle="round,pad=0,rounding_size=0.25"))
            ax.text(x0 + 0.35, (b + 10) / 2, "H$_2$\ngas", ha="center", va="center", fontsize=7.5, color="#2a6fb0")
        smax = np.nanmax(S)
        ax.text(x0 + 0.35, 10.9, lab, ha="center", va="top", fontsize=8)
        ax.text(x0 + 0.35, -0.25, f"max {smax:.0f}x", ha="center", va="bottom", fontsize=7.5)
        rows.append(dict(t_ms=round(ts[i] * 1e3, 2), label=lab.replace("\n", " "), plug=hist[i]["plug"],
                         plug_top_um=round(hist[i]["b"] * 1e6, 3) if hist[i]["plug"] else "", S_max=round(smax, 1),
                         S_mouth=round(S[0], 1), S_bottom_liquid=round(S[~np.isnan(S)][-1], 1)))
    ax.set_xlim(-0.5, len(picks) * 1.6 - 0.5)
    ax.set_ylim(11.9, -0.9)
    ax.set_yticks([0, 2, 4, 6, 8, 10])
    ax.set_ylabel("depth (µm)")
    ax.set_xticks([])
    for sp in ("top", "right", "bottom"):
        ax.spines[sp].set_visible(False)
    fig.suptitle("Case 4: H$_2$ saturation in a 100 nm × 10 µm slit from a fresh refill through the bubble cycle "
                 "(1D model, flat walls, no sound, 5 wt% TMAH 60 °C)", fontsize=11)
    fig.text(0.01, 0.005, "c_sat = 0.70 mM and bubble-start levels ASSUMED; x stretched in the bottom strip. "
             "Imposed oscillating flow + modelled mixing, not acoustic streaming (no sound here).", fontsize=7.5,
             color="#555")
    fig.savefig(OUT / "cycle_map.png", dpi=150, bbox_inches="tight")
    with open(OUT / "cycle_map.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()

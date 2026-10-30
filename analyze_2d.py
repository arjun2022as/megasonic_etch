#!/usr/bin/env python3
"""Figures and tables from the finished 2D Fluent cases (no Fluent needed).

    python analyze_2d.py        # matplotlib; writes results/analysis/
1. angle_sweep.png      etch rate per poly-Si layer vs depth for every incidence angle, and bottom/top + mean
                        etch rate vs angle (best angle marked), with the no-megasonic reference
2. megasonic_mixing.png D_osc along the slit centre: how deep the megasonic mixing reaches, per angle
3. frequency_power.png  bottom/top and mean etch for 1/2/3 MHz and 0.5/1/2 W/cm2 at 45 deg
4. verification.md      2D vs 1D reference, mesh check, electromigration and rate-order effects, recess
"""
import csv
import glob
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
OUT = RES / "analysis"


def load(case):
    f = RES / case / "summary.json"
    return json.loads(f.read_text()) if f.exists() else None


def centre(case):
    rows = []
    for fn in glob.glob(str(RES / case / "dump_*.csv")):
        with open(fn, newline="") as f:
            rows += [r for r in csv.DictReader(f) if r["kind"] == "centre"]
    rows = sorted(({k: float(v) for k, v in r.items() if k != "kind"} for r in rows), key=lambda r: -r["y"])
    return rows


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    OUT.mkdir(parents=True, exist_ok=True)
    cases = [r["case"] for r in csv.DictReader(open(HERE / "cases.csv"))]
    done = {c: load(c) for c in cases if load(c)}
    print(f"{len(done)} of {len(cases)} cases finished")
    table = []
    for c, s in done.items():
        r = s["result"]
        table.append(dict(case=c, f_MHz=s["f"] / 1e6, I_W_cm2=s["I"], theta_deg=s["theta"], recess_nm=s["recess"] * 1e9,
                          u_t_m_s=s["u_t"], er_top=r["er_top_nm_min"], er_bottom=r["er_bottom_nm_min"],
                          er_mean=r["er_mean_nm_min"], bottom_over_top=r["uniformity"], d_osc_max=r["d_osc_max"],
                          one_d_bottom_over_top=s["one_d"]["uniformity"], quasi_steady_change=s["quasi_steady_change"]))
    if not table:
        return
    with open(OUT / "results_table.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)

    ref = done.get("M0_none")
    ang = sorted(((s["theta"], c, s) for c, s in done.items() if c.startswith("A_")), key=lambda t: -t[0])
    if ang:
        fig, axes = plt.subplots(1, 3, figsize=(16, 5))
        for th, c, s in ang + ([(None, "M0_none", ref)] if ref else []):
            lay = s["result"]["layers"]
            axes[0].plot([e for _, e in lay], [(k + 0.5) * 0.05 for k, _ in lay], ".-", ms=2,
                         label="no megasonic" if th is None else f"{th:g} deg")
        axes[0].set(xlabel="poly-Si lateral etch rate (nm/min)", ylabel="depth (um)")
        axes[0].invert_yaxis()
        axes[0].legend(fontsize=8)
        th = [t for t, _, _ in ang]
        for ax, key, lab in ((axes[1], "uniformity", "etch rate bottom / top"),
                             (axes[2], "er_mean_nm_min", "mean poly-Si etch rate (nm/min)")):
            v = [s["result"][key] for _, _, s in ang]
            ax.plot(th, v, "o-")
            best = th[max(range(len(v)), key=lambda i: v[i])]
            ax.axvline(best, color="tab:red", ls=":", label=f"best {best:g} deg")
            if ref:
                ax.axhline(ref["result"][key], color="k", ls="--", label="no megasonic")
            ax.set(xlabel="megasonic incidence angle from the wafer (deg); 90 = MegPie", ylabel=lab)
            ax.legend(fontsize=8)
        fig.suptitle("5 wt% TMAH 60 C, 100 nm x 10 um slit, 1 MHz 2 W/cm2: effect of the incidence angle")
        fig.tight_layout()
        fig.savefig(OUT / "angle_sweep.png", dpi=150)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(7, 5))
        for th_, c, s in ang:
            rows = centre(c)
            if rows:
                ax.plot([max(r["d_osc"], 1e-16) for r in rows], [r["y"] * 1e6 for r in rows], label=f"{th_:g} deg")
        ax.axvline(1.12e-8, color="k", ls=":", label="D of OH- (60 C)")
        ax.set(xscale="log", xlabel="megasonic mixing D_osc on the slit centre (m2/s)", ylabel="height above wafer (um)",
               ylim=(-1.0, 2.0))
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(OUT / "megasonic_mixing.png", dpi=150)
        plt.close(fig)

    fp = [(c, s) for c, s in done.items() if c.startswith(("F_", "P_")) or c == "A_f1_I2_t45"]
    if fp:
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
        labels = [f"{s['f'] / 1e6:g} MHz, {s['I']:g} W/cm2" for _, s in fp]
        for ax, key, lab in ((axes[0], "uniformity", "bottom / top"), (axes[1], "er_mean_nm_min", "mean etch (nm/min)")):
            ax.barh(labels, [s["result"][key] for _, s in fp])
            if ref:
                ax.axvline(ref["result"][key], color="k", ls="--", label="no megasonic")
            ax.set_xlabel(lab)
        axes[0].legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(OUT / "frequency_power.png", dpi=150)
        plt.close(fig)

    lines = ["# 2D verification", ""]

    def line(a, b, what):
        sa, sb = done.get(a), done.get(b)
        if sa and sb:
            ra, rb = sa["result"], sb["result"]
            lines.append(f"- {what}: bottom/top {ra['uniformity']:.4f} vs {rb['uniformity']:.4f}, mean etch "
                         f"{ra['er_mean_nm_min']:.2f} vs {rb['er_mean_nm_min']:.2f} nm/min")
    if ref:
        lines.append(f"- 2D vs 1D (no megasonic): bottom/top {ref['result']['uniformity']:.4f} vs "
                     f"{ref['one_d']['uniformity']:.4f}; top etch {ref['result']['er_top_nm_min']:.1f} vs "
                     f"{ref['one_d']['er_top'] * 6e10:.1f} nm/min")
    line("V_mesh2", "M0_none", "mesh refined 2x vs base")
    line("V_nomig", "M0_none", "electromigration off vs on")
    line("V_order1", "M0_none", "rate order 1 vs 1/4")
    line("R_none_r300", "M0_none", "recess 300 nm vs 0")
    line("R_f1_I2_t45_r300", "R_none_r300", "recess 300 nm: megasonic 45 deg vs none")
    for c, s in done.items():
        lines.append(f"- {c}: quasi-steady change of bottom/top over the last time block {s['quasi_steady_change']:.1e}")
    (OUT / "verification.md").write_text("\n".join(lines) + "\n")
    for t in sorted(table, key=lambda r: r["case"]):
        print(f"{t['case']:20s} bottom/top {t['bottom_over_top']:.4f}  mean {t['er_mean']:.2f} nm/min  "
              f"D_osc max {t['d_osc_max']:.2e}")


if __name__ == "__main__":
    main()

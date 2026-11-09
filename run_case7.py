#!/usr/bin/env python3
"""Case 7: flat MegPie (sound normal to the wafer, 90 deg). Can it renew the liquid at the slit mouths, and does
that change the plug condition? (1D + estimates, laptop; etchsim/normal.py)

    python run_case7.py --part mech      # streaming / edge / bubble mechanisms, 1-3 MHz, 1-2 W/cm2 (seconds)
    python run_case7.py --part film      # film over the wafer through a revolution: stirring and H2 sink (~2 min)
    python run_case7.py --part req       # slit + bubble cycle vs k multiplier at the mouth (~20 min)
    python run_case7.py --part combine   # scenarios -> mouth, floor, bottom etch; figure (needs film + req)

60 C, 300 rpm, 5 wt% TMAH, 1 MHz unless stated. ASSUMED: MegPie sector 60 deg (sound 33 of every 200 ms), gap 2 mm,
water absorption, beam edge width = one wavelength, bubble numbers and stirred-layer thickness (swept).
Imposed / estimated flows, not a full acoustic-streaming solution.
"""
import argparse
import csv
import math

import numpy as np

from etchsim import normal as N
from etchsim import plug as PL
from etchsim import props as P
from etchsim import window as WN
from run_plug import OUT

M_REQ = (1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.8, 2.0, 2.5, 3.0, 5.0, 10.0, 1e6)
STARTS = (("seed", PL.S_PLUG), ("few", WN.c_need(WN.T60, 13.4e-9) / P.H2_SAT))
DN = P.D["H2"] / P.levich_km(P.D["H2"], P.omega_spin())          # 54 um Nernst layer
R1 = N.resonance_radius(1e6)
S0 = WN.slit_h2(n=400)["S_mouth"]                                  # no-sound mouth H2, 63.1x
S_BUB = N.bubble_level(R1) / S0                                # bubble H2 level / no-sound mouth level
SCEN = [("no sound", {}, 1 / 6),
        ("bubble stirring 6 um (2 R)", dict(h_mix=6e-6), 1 / 6),
        ("bubble stirring 15 um (5 R)", dict(h_mix=15e-6), 1 / 6),
        ("bubbles take up H2, 100 /mm2", dict(k_sink=N.bubble_sink_k(100, R1), s_bub=S_BUB), 1 / 6),
        ("bubbles take up H2, 1000 /mm2", dict(k_sink=N.bubble_sink_k(1000, R1), s_bub=S_BUB), 1 / 6),
        ("perfect renewal under the MegPie", dict(h_mix=1.0), 1 / 6),
        ("bubble stirring 15 um, sound all the time", dict(h_mix=15e-6), 1.0),
        ("bubbles take up H2 1000 /mm2, all the time", dict(k_sink=N.bubble_sink_k(1000, R1), s_bub=S_BUB), 1.0)]


def save(name, rows):
    OUT.mkdir(exist_ok=True)
    with open(OUT / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def read(name):
    with open(OUT / name, newline="") as f:
        return list(csv.DictReader(f))


def part_mech():
    rows = []
    for f in (1e6, 2e6, 3e6):
        for I in (1.0, 2.0):
            e, b = N.eckart(f, I), N.beam_edge(f, I)
            rows.append(dict(mechanism="Eckart streaming (beam edge cells)", f_MHz=f / 1e6, I_W_cm2=I,
                             key=f"F {e['F']:.3g} N/m3, u_max {e['u_max'] * 1e6:.3g} um/s, wall shear {e['G_wall']:.3g} 1/s",
                             local_k_gain=round(e["k_patch_over_levich"], 4), time_fraction=round(e["time_fraction"], 4),
                             m_mean=round(e["m_mean"], 5)))
            rows.append(dict(mechanism="beam-edge sideways oscillation + Rayleigh streaming", f_MHz=f / 1e6, I_W_cm2=I,
                             key=f"U_edge {b['U_edge']:.3g} m/s (15 deg: {b['U_t_15deg']:.3g}), D_osc {b['D_osc']:.3g}, "
                                 f"u_R {b['u_rayleigh'] * 1e6:.3g} um/s",
                             local_k_gain=round(b["k_mult_local"] - 1 + b["k_rayleigh_over_levich"], 4),
                             time_fraction=round(b["time_fraction"], 4), m_mean=round(b["m_mean"], 5)))
        R = N.resonance_radius(f)
        rows.append(dict(mechanism="resonant bubble (Minnaert)", f_MHz=f / 1e6, I_W_cm2="",
                         key=f"R {R * 1e6:.2f} um, holds {N.bubble_level(R):.2f}x, microstreaming at eps 0.05-0.2: "
                             f"{N.microstreaming_speed(f, R, 0.05):.3g}-{N.microstreaming_speed(f, R, 0.2):.3g} m/s, "
                             f"H2 uptake per 100 bubbles/mm2 = {N.bubble_sink_k(100, R) / P.levich_km(P.D['H2'], P.omega_spin()):.3f} x Levich",
                         local_k_gain="", time_fraction="", m_mean=""))
    for I in (1.0, 2.0):
        for R, lab in ((P.W_SLIT / 2, "plug-size 50 nm"), (13.4e-9, "13 nm seed")):
            s = N.seed_pulsation(R, I)
            rows.append(dict(mechanism=f"seed in the slit pulsating ({lab})", f_MHz=1, I_W_cm2=I,
                             key=f"p_a {s['p_a'] / 1e6:.3f} MPa < gas {s['p_g'] / 1e6:.2f} MPa (no collapse); swing "
                                 f"eps {s['eps']:.4f}; rectified shift of the level ~3 eps^2 = {3 * s['eps'] ** 2:.1e}",
                             local_k_gain="", time_fraction="", m_mean=""))
    save("case7_mechanisms.csv", rows)
    for r in rows:
        print(r)


def part_film():
    rows = []
    for label, kw, duty in SCEN:
        r = N.film_cycle(duty=duty, **kw)
        rows.append(dict(scenario=label, duty=round(duty, 4), mouth_mean_x=round(S0 * r["mean"], 2),
                         mouth_worst_x=round(S0 * r["max"], 2), mouth_best_x=round(S0 * r["min"], 2),
                         m_mean=round(r["m_mean"], 4), m_worst=round(r["m_worst"], 4)))
        print(rows[-1], flush=True)
    for h in (3e-6, 6e-6, 9e-6, 15e-6, 30e-6, DN):
        r = N.film_cycle(h_mix=h)
        rows.append(dict(scenario=f"stirring {h * 1e6:.0f} um", duty=round(1 / 6, 4), mouth_mean_x=round(S0 * r["mean"], 2),
                         mouth_worst_x=round(S0 * r["max"], 2), mouth_best_x=round(S0 * r["min"], 2),
                         m_mean=round(r["m_mean"], 4), m_worst=round(r["m_worst"], 4)))
    for n in (30, 100, 300, 1000, 3000, 10000):
        r = N.film_cycle(k_sink=N.bubble_sink_k(n, R1), s_bub=S_BUB)
        rows.append(dict(scenario=f"H2 uptake {n} /mm2", duty=round(1 / 6, 4), mouth_mean_x=round(S0 * r["mean"], 2),
                         mouth_worst_x=round(S0 * r["max"], 2), mouth_best_x=round(S0 * r["min"], 2),
                         m_mean=round(r["m_mean"], 4), m_worst=round(r["m_worst"], 4)))
        print(rows[-1], flush=True)
    save("case7_film.csv", rows)


def part_req(t_end=0.2):
    rows = []
    for m in M_REQ:
        r = WN.slit_h2(km_scale=m, n=400)
        row = dict(m=m, S_mouth=round(r["S_mouth"], 2), S_max=round(r["S_max"], 2),
                   nobubble_bottom=round(r["er_bottom_nm_min"], 1), nobubble_uniformity=round(r["uniformity"], 5))
        for tag, s in STARTS:
            sm = PL.summarise(PL.simulate(r["surf"], t_end=t_end, s_nuc=s))
            row[f"bottom_{tag}"] = round(sm["er_bottom_nm_min"], 2)
        rows.append(row)
        print(row, flush=True)
    save("case7_requirement.csv", rows)


def interp_m(req, key, m):
    lm = np.log([float(r["m"]) for r in req])
    return np.interp(np.log(np.clip(m, 1.0, 1e6)), lm, [float(r[key]) for r in req])


def part_combine():
    req = read("case7_requirement.csv")
    rows, series = [], {}
    for label, kw, duty in SCEN:
        r = N.film_cycle(duty=duty, **kw)
        m_t = 1 / r["c_wall"]
        series[label] = (r["t"], S0 * r["c_wall"])
        row = dict(scenario=label, duty=round(duty, 4), mouth_mean_x=round(S0 * r["mean"], 1),
                   mouth_worst_x=round(S0 * r["max"], 1),
                   floor_mean_x=round(float(np.mean(interp_m(req, "S_max", m_t))), 1),
                   floor_worst_x=round(float(interp_m(req, "S_max", r["m_worst"])), 1))
        for tag, _ in STARTS:                                      # quasi-steady through the revolution
            row[f"bottom_{tag}"] = round(float(np.mean(interp_m(req, f"bottom_{tag}", m_t))), 2)
        rows.append(row)
        print(row)
    for lab, mouth in (("15 deg, 2 W/cm2 continuous (case 4, not reachable)", 43.0), ("600 rpm, no sound (case 6B)", 44.9)):
        m = S0 / mouth
        rows.append(dict(scenario=lab, duty=1.0, mouth_mean_x=mouth, mouth_worst_x=mouth,
                         floor_mean_x=round(float(interp_m(req, "S_max", m)), 1),
                         floor_worst_x=round(float(interp_m(req, "S_max", m)), 1),
                         bottom_seed=round(float(interp_m(req, "bottom_seed", m)), 2),
                         bottom_few=round(float(interp_m(req, "bottom_few", m)), 2)))
    save("case7_scenarios.csv", rows)
    plot(rows, series, req)


def plot(rows, series, req):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(20, 6), gridspec_kw=dict(width_ratios=[1.35, 1, 1]))
    names = [r["scenario"] for r in rows]
    y = np.arange(len(names))
    ax[0].barh(y - 0.2, [float(r["floor_mean_x"]) for r in rows], 0.4, color="#2a6fb0", label="time mean")
    ax[0].barh(y + 0.2, [float(r["floor_worst_x"]) for r in rows], 0.4, color="#c0392b", label="worst moment")
    for lev, lab in ((13.9, "plug\n13.9x"), (27, "50 nm\n27x"), (100, "13 nm\n100x")):
        ax[0].axvline(lev, color="k", ls=":", lw=1)
        ax[0].text(lev, len(names) + 0.1, lab, fontsize=7, ha="center", va="center")
    ax[0].set_yticks(y, names, fontsize=8)
    ax[0].set_ylim(len(names) + 0.5, -0.6)
    ax[0].set(xlabel="H2 at the slit floor (x saturation), no bubbles", xlim=(0, 140),
              title="(a) Floor H2 with each 90 deg mechanism\n(bubble-free only left of a dotted line)")
    ax[0].legend(fontsize=8, loc="lower right")
    for lab in ("no sound", "bubble stirring 15 um (5 R)", "bubbles take up H2, 1000 /mm2", "perfect renewal under the MegPie"):
        t, c = series[lab]
        ax[1].plot(t * 1e3, c, label=lab)
    ax[1].axvspan(0, 1000 * N.T_REV / 6, color="#f5c542", alpha=0.3, label="under the MegPie")
    ax[1].set(xlabel="time in one revolution (ms)", ylabel="H2 at the mouth (x saturation)", ylim=(0, 70),
              title="(b) Mouth H2 through one revolution (300 rpm)")
    ax[1].legend(fontsize=7, loc="lower right")
    m = [float(r["m"]) for r in req]
    xm = [min(v, 20) for v in m]
    ax[2].plot(xm, [float(r["S_max"]) for r in req], "o-", color="k", label="floor H2, no bubbles")
    ax[2].plot(xm, [float(r["S_mouth"]) for r in req], "o--", color="grey", label="mouth H2")
    for lev in (13.9, 27, 100):
        ax[2].axhline(lev, color="k", ls=":", lw=1)
    ax2 = ax[2].twinx()
    ax2.plot(xm, [float(r["bottom_few"]) for r in req], "s-", color="#2a6fb0", label="bottom etch, few seeds")
    ax2.plot(xm, [float(r["bottom_seed"]) for r in req], "s-", color="#c0392b", label="bottom etch, seeds")
    ax2.set_ylabel("bottom etch with bubbles (nm/min)")
    ax[2].set(xscale="log", xlabel="k at the mouth / Levich (20 = infinite renewal)", ylabel="H2 (x saturation)",
              title="(c) What the mouth renewal must reach")
    ax[2].legend(fontsize=7, loc="upper center")
    ax2.legend(fontsize=7, loc="center right", bbox_to_anchor=(1.0, 0.62))
    fig.suptitle("Case 7: flat MegPie (90 deg), 1 MHz, 60 C, 300 rpm, 5 wt% TMAH. Estimated streaming and bubble effects "
                 "(ASSUMED numbers), not a full acoustic-streaming solution.", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "case7.png", dpi=140, bbox_inches="tight")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=("mech", "film", "req", "combine"), required=True)
    {"mech": part_mech, "film": part_film, "req": part_req, "combine": part_combine}[ap.parse_args().part]()

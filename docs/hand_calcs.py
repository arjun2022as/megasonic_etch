"""Hand calculations behind the numbers on the Project 1 slides (four cases with bubbles).

Every value is recomputed here from the closed-form formulas, with the same constants as etchsim/props.py,
and written to docs/hand_calcs.json for docs/make_hand_calcs_doc.js. Model outputs (Fluent, 1D cycle) are
NOT recomputed; they appear only where a hand formula checks them.

Run: uv run --with numpy python docs/hand_calcs.py
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from etchsim import props as P  # noqa: E402
from etchsim import acoustics as A  # noqa: E402

v = {}

# ------------------------------------------------------------------ 0. constants
T = P.T
rho, mu, c = P.RHO_L, P.MU_L, P.C_SOUND
nu = mu / rho
v.update(T=T, rho=rho, mu=mu, c=c, nu=nu, gamma=P.GAMMA_60C, p_vap=P.P_VAP_60C, p_atm=P.P_ATM,
         c_sat=P.H2_SAT, W=P.W_SLIT, L=P.L_SLIT, pitch=P.PITCH, AR=P.L_SLIT / P.W_SLIT)
v["SE_factor"] = (T / P.T_REF) * (P.MU_25 / mu)
for k in ("OH", "TMA", "SIL", "H2"):
    v["D25_" + k] = P.D25[k]
    v["D_" + k] = P.D[k]
D_H2 = P.D["H2"]

# ------------------------------------------------------------------ 1. chemistry (Seidel)
v["c_bulk"] = P.WT_TMAH * P.RHO_SOLN / P.M_TMAH
ER = P.ER_REF
v["ER_ms"] = ER
v["N_Si"] = ER * P.RHO_SI / P.M_SI                    # mol Si / m2 s
v["N_H2_wall"] = 2 * v["N_Si"]                         # mol H2 / m2 s of poly-Si
f_poly = 0.5
v["q_H2"] = v["N_H2_wall"] * 2 / P.W_SLIT * f_poly    # mol / m3 s, slit average
v["N_OH_wall"] = 2 * v["N_Si"]

# ------------------------------------------------------------------ 2. Levich, mouth, in-slit rise
Om = 2 * math.pi * P.SPIN_RPM / 60
v["Omega"] = Om
v["km"] = 0.620 * D_H2 ** (2 / 3) * nu ** (-1 / 6) * Om ** 0.5
v["deltaN"] = D_H2 / v["km"]
G_slit = v["N_H2_wall"] * 2 * P.L_SLIT * f_poly        # mol / (m s) per metre of trench
v["G_slit"] = G_slit
v["J_wafer"] = G_slit / P.PITCH
v["dc_mouth"] = v["J_wafer"] / v["km"]
v["S_mouth_full"] = v["dc_mouth"] / P.H2_SAT
v["dc_rise"] = v["q_H2"] * P.L_SLIT ** 2 / (2 * D_H2)
v["S_rise_full"] = v["dc_rise"] / P.H2_SAT
mean_er = (294 + 281.5) / 2 / 300                     # model top/bottom rates, only to scale the hand values
v["mean_er_frac"] = mean_er
v["S_mouth_scaled"] = v["S_mouth_full"] * mean_er
v["S_rise_scaled"] = v["S_rise_full"] * mean_er
v["S_floor_scaled"] = v["S_mouth_scaled"] + v["S_rise_scaled"]

# ------------------------------------------------------------------ 3. Henry + Young-Laplace
g = P.GAMMA_60C
v["dp_plug"] = 2 * g / P.W_SLIT                        # cylindrical meniscus, radius W/2
v["p_gas"] = P.P_ATM + v["dp_plug"] - P.P_VAP_60C
v["S_plug"] = v["p_gas"] / P.P_ATM
v["c_star"] = P.H2_SAT * v["S_plug"]
v["rho_gas"] = v["p_gas"] / (P.R_GAS * T)
for name, r in (("50", 50e-9), ("13", 13.4e-9)):
    v["S_" + name] = 1 + (2 * g / r - P.P_VAP_60C) / P.P_ATM
v["t_13_9"] = v["c_star"] / v["q_H2"]                  # fresh liquid, no diffusion loss

# ------------------------------------------------------------------ 4. plug growth (hand check of Fluent)
fluent_flat = {1: (143.0, 63.3), 3: (145.2, 61.4), 6: (175.0, 56.9)}
rows = []
for lp, (vf, Sm) in fluent_flat.items():
    ell = P.L_SLIT - lp * 1e-6
    cm = Sm * P.H2_SAT
    N_diff = D_H2 * (cm - v["c_star"]) / ell
    N_gen = v["q_H2"] * ell / 2
    vh = (N_diff + N_gen) / v["rho_gas"] * 1e6
    rows.append(dict(lp=lp, ell=ell * 1e6, cm=cm, N_diff=N_diff, N_gen=N_gen, v_hand=vh, v_fluent=vf,
                     err=(vh / vf - 1) * 100))
v["plug_rows"] = rows
# cycle estimate: t = rho_g/q ln(1 + q L^2 / (2 D dc)), mouth ~61x
Sm_mean = 61.0
dc = Sm_mean * P.H2_SAT - v["c_star"]
v["cycle_dc"] = dc
v["cycle_arg"] = v["q_H2"] * P.L_SLIT ** 2 / (2 * D_H2 * dc)
v["cycle_hand"] = v["rho_gas"] / v["q_H2"] * math.log(1 + v["cycle_arg"])

# ------------------------------------------------------------------ 5. acoustics at the wafer
I = 2.0
p0, U0 = A.plane_wave(I)
v.update(I=I * 1e4, Zf=rho * c, p0=p0, U0=U0)
v["Zs"] = A.RHO_SI * A.CL_SI
R90 = A.reflection(90.0).real
v["R"] = R90
v["R_hand"] = (v["Zs"] - v["Zf"]) / (v["Zs"] + v["Zf"])
v["R2"] = R90 ** 2
v["T_energy"] = 1 - R90 ** 2
v["onepR"], v["onemR"] = 1 + R90, 1 - R90
v["p_wall"] = p0 * (1 + R90)
v["u_n"] = U0 * (1 - R90)
# energy split at the wall: potential p^2/(2 rho c^2) vs kinetic rho u^2/2
E_pot = v["p_wall"] ** 2 / (2 * rho * c ** 2)
E_kin = rho * v["u_n"] ** 2 / 2
v["E_pot"], v["E_kin"] = E_pot, E_kin
v["kin_over_pot"] = E_kin / E_pot
v["frac_pot"] = E_pot / (E_pot + E_kin)
v["frac_kin"] = E_kin / (E_pot + E_kin)
# critical angles and Rayleigh angle (theta measured from the wafer surface)
cL, cS = A.CL_SI, A.CS_SI
v["cL"], v["cS"] = cL, cS
v["beta_L"] = math.degrees(math.asin(c / cL))
v["beta_S"] = math.degrees(math.asin(c / cS))
v["theta_L"] = 90 - v["beta_L"]
v["theta_S"] = 90 - v["beta_S"]


def rayleigh_eq(x):  # x = (cR/cS)^2
    k2 = (cS / cL) ** 2
    return x ** 3 - 8 * x ** 2 + (24 - 16 * k2) * x - 16 * (1 - k2)


lo, hi = 0.5, 0.999
for _ in range(200):
    mid = (lo + hi) / 2
    if rayleigh_eq(lo) * rayleigh_eq(mid) <= 0:
        hi = mid
    else:
        lo = mid
v["cR"] = cS * math.sqrt((lo + hi) / 2)
v["beta_R"] = math.degrees(math.asin(c / v["cR"]))
v["theta_R"] = 90 - v["beta_R"]
v["poisson"] = ((cL / cS) ** 2 - 2) / (2 * ((cL / cS) ** 2 - 1))

# 15 deg
w15 = A.wall_velocities(I, 15.0)
v["R15_abs1pR"] = abs(1 + w15["R"])
v["u_t15"] = w15["u_t"]
v["sinb15"] = math.sin(math.radians(75))
f = 1e6
om = 2 * math.pi * f
v["f"], v["omega"] = f, om
v["delta"] = math.sqrt(2 * nu / om)
v["shear15"] = v["u_t15"] / v["delta"]
v["D_osc15"] = v["u_t15"] ** 2 / (2 * om)
v["km_gain15"] = ((D_H2 + v["D_osc15"]) / D_H2) ** (2 / 3)
v["S_mouth15"] = 63.0 / v["km_gain15"]
v["xi_t15"] = v["u_t15"] / om
c_trace = c / math.cos(math.radians(15))
v["c_trace15"] = c_trace
v["u_stream15"] = 3 * v["u_t15"] ** 2 / (4 * c)

# 90 deg: normal displacement and mixing
v["xi_n_wall"] = v["u_n"] / om
v["xi_z"] = U0 * (1 + R90) * v["deltaN"] / c
v["xi_z_frac"] = v["xi_z"] / v["deltaN"]
v["D_osc_n"] = v["u_n"] ** 2 / (2 * om)
v["D_osc_n_frac"] = v["D_osc_n"] / D_H2

# ------------------------------------------------------------------ 6. slit: Womersley, Moffatt, breathing
half = P.W_SLIT / 2
v["sqrt_om_nu"] = math.sqrt(om / nu)
v["Wo"] = half * v["sqrt_om_nu"]
v["Wo2"] = v["Wo"] ** 2
v["delta_over_half"] = v["delta"] / half
v["t_visc"] = half ** 2 / nu
v["t_flow"] = 1 / om
v["Wo_gap"] = 1e-3 * v["sqrt_om_nu"]
v["K"] = A.K_SLOT
v["moffatt_100"] = math.exp(-A.K_SLOT * 100e-9 / P.W_SLIT)
v["moffatt_1um"] = math.exp(-A.K_SLOT * 1e-6 / P.W_SLIT)
v["lam"] = c / f
v["breath"] = P.L_SLIT * v["p_wall"] / (rho * c ** 2)
v["L_over_lam"] = P.L_SLIT / v["lam"]

# ------------------------------------------------------------------ 7. levers
k_B = P.K_B_EV
for TC in (60, 55, 50, 45, 40, 35, 30, 25, 20):
    Tk = TC + 273.15
    v[f"ER_{TC}"] = 300 * math.exp(-P.EA_EV / k_B * (1 / Tk - 1 / T))
v["rpm_gain_1000"] = math.sqrt(1000 / 300)
v["S_mouth_1000"] = 63.0 / v["rpm_gain_1000"]
v["S_floor_1000"] = v["S_mouth_1000"] + 59.5
v["t_LD_OH"] = P.L_SLIT ** 2 / P.D["OH"]
v["t_LD_H2"] = P.L_SLIT ** 2 / D_H2

# ------------------------------------------------------------------ 8. percentages quoted on the slides
fl = dict(none=[143.0, 145.2, 175.0, 147.7, 151.0, 183.4], d90=[143.0, 145.5, 176.2, 147.9, 151.3, 184.7],
          d15=[115.3, 111.2, 129.4, 118.3, 115.2, 136.7])
v["pct15"] = [(b / a - 1) * 100 for a, b in zip(fl["none"], fl["d15"])]
v["pct90"] = [(b / a - 1) * 100 for a, b in zip(fl["none"], fl["d90"])]
v["recess_pct"] = (253.3 / 311.7 - 1) * 100
v["bt_15"] = 253.3 / 591
v["bt_none"] = 311.7 / 588
v["bubblefree_2min"] = 281.5 * 2

out = os.path.join(os.path.dirname(__file__), "hand_calcs.json")
with open(out, "w", encoding="utf-8") as fh:
    json.dump(v, fh, indent=1)
sys.stdout.reconfigure(encoding="utf-8")
for k, x in v.items():
    print(k, x)

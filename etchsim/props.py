"""Process conditions and material/transport properties, each with its source.

Conditions (chosen with the user, Project 1 of the UA/Micron proposal):
  5 wt% TMAH, 60 C; slit 100 nm wide x 10 um deep (aspect ratio 100) in an alternating
  SiO2 / poly-Si stack, 50 nm / 50 nm; only poly-Si etches. Single-wafer spin tool with a
  megasonic transducer (ProSys MegPie), 1 / 2 / 3 MHz, 0.5-2 W/cm2.

Every number marked ASSUMED is not from a measurement for this exact system and is a model input to
be calibrated (the proposal's SEM etch-rate data are exactly what calibrates ER_REF).
SI units throughout: m, s, mol, kg, Pa, K.
"""
import math

R_GAS = 8.314462618          # J/(mol K)
F_FARADAY = 96485.33212      # C/mol
K_B_EV = 8.617333262e-5      # eV/K

# ---------------------------------------------------------------- conditions
T_C = 60.0
T = T_C + 273.15
T_REF = 298.15
WT_TMAH = 0.05
M_TMAH = 0.09115             # kg/mol, (CH3)4NOH
W_SLIT = 100e-9              # slit width
L_SLIT = 10e-6               # slit depth
LAYER = 50e-9                # each SiO2 and poly-Si layer
TOP_LAYER = "SiO2"           # ASSUMED: stack starts with oxide at the wafer surface
BOTTOM = "SiO2"              # ASSUMED: slit floor is inert (etch stop); a Si floor would also etch
PITCH = 1e-6                 # ASSUMED: slit-to-slit pitch (sets wafer-level consumption)

# ---------------------------------------------------------------- liquid (water at 60 C; 5 wt% TMAH ~ water)
RHO_L = 983.2                # kg/m3, water 60 C (IAPWS)
MU_L = 0.4665e-3             # Pa s, water 60 C (IAPWS); 25 C value 0.8900e-3
MU_25 = 0.8900e-3
NU_L = MU_L / RHO_L
C_SOUND = 1551.0             # m/s, water 60 C (Del Grosso & Mader / Marczak)
RHO_SOLN = 990.0             # kg/m3, ASSUMED 5 wt% TMAH at 60 C (solution ~0.7 % denser than water)
C_BULK = WT_TMAH * RHO_SOLN / M_TMAH   # mol/m3 of TMA+ and of OH- (strong base, fully dissociated)

# ---------------------------------------------------------------- diffusivities
# Infinite-dilution values at 25 C. Ions: Vanysek, CRC Handbook "Ionic conductivity and diffusion at
# infinite dilution" (D = R T lambda / (z^2 F^2)). Temperature: Stokes-Einstein D ~ T / mu.
D25 = {
    "OH": 5.273e-9,          # OH-, lambda = 198.0 S cm2/mol (CRC)
    "TMA": 1.196e-9,         # N(CH3)4+, lambda = 44.9 S cm2/mol (CRC)
    "SIL": 0.92e-9,          # SiO2(OH)2^2-: ASSUMED ~ CO3^2- (0.923e-9); literature values inconsistent
    "H2": 4.5e-9,            # dissolved H2 (Cussler, Diffusion, table 5.2-2)
}
Z = {"OH": -1, "TMA": +1, "SIL": -2, "H2": 0}


def d_at(T_k, mu, d25):
    """Stokes-Einstein temperature scaling from 25 C."""
    return d25 * (T_k / T_REF) * (MU_25 / mu)


D = {k: d_at(T, MU_L, v) for k, v in D25.items()}
H2_SAT = 0.70                # mol/m3, ASSUMED H2 solubility at 60 C, 1 atm (~0.78 mM at 25 C, falls slowly with T)
GAMMA_60C = 0.0662           # N/m, water surface tension at 60 C (IAPWS); ASSUMED for 5 wt% TMAH
P_VAP_60C = 19.946e3         # Pa, water vapour pressure at 60 C
P_ATM = 101.325e3

# ---------------------------------------------------------------- etch chemistry
# Overall (Seidel et al., J. Electrochem. Soc. 137, 3612 (1990); same for TMAH):
#     Si + 2 OH- + 2 H2O -> SiO2(OH)2^2- + 2 H2
NU_RXN = {"OH": -2.0, "SIL": +1.0, "H2": +2.0, "TMA": 0.0}   # mol per mol Si
RHO_SI = 2330.0              # kg/m3 poly-Si
M_SI = 0.028086              # kg/mol
ER_REF = 300e-9 / 60         # m/s: ASSUMED poly-Si etch rate at 5 wt% TMAH, 60 C (Si(100) data in 5-25 wt%,
                             # 60-90 C span 148-734 nm/min); to be calibrated with the Project 1 SEM data
EA_EV = 0.57                 # eV, TMAH Si(100) activation energy, 28-80 C (temperature-dependent etching study)
ORDER_OH = 0.25              # rate ~ [OH-]^(1/4) [H2O]^4 (Seidel 1990); sensitivity: 1.0
SIO2_RATE = 0.2e-9 / 60      # m/s, thermal oxide in TMAH (~0.2 nm/min): selectivity > 1000, oxide inert here


def etch_rate(c_oh, order=ORDER_OH, er_ref=ER_REF, c_ref=C_BULK):
    """poly-Si etch velocity [m/s] at local OH- concentration (power law, zero at c = 0)."""
    return er_ref * (max(c_oh, 0.0) / c_ref) ** order


def si_flux(er):
    """mol Si per m2 per s for an etch velocity er [m/s]."""
    return er * RHO_SI / M_SI


def arrhenius(er, T1, T2, ea_ev=EA_EV):
    return er * math.exp(-ea_ev / K_B_EV * (1 / T2 - 1 / T1))


# ---------------------------------------------------------------- spin tool
SPIN_RPM = 300.0             # ASSUMED
DISPENSE_LPM = 1.0           # ASSUMED
R_PROBE = 0.05               # m: radius where the trench sits (8-inch wafer, mid-radius)


def omega_spin(rpm=SPIN_RPM):
    return 2 * math.pi * rpm / 60


def levich_km(d, omega, nu=NU_L):
    """Rotating-disk mass-transfer coefficient (Levich): k = 0.620 D^(2/3) nu^(-1/6) Omega^(1/2)."""
    return 0.620 * d ** (2 / 3) * nu ** (-1 / 6) * omega ** 0.5


def spin_film(Q_m3s, omega, r, nu=NU_L):
    """Steady spin-off film (Emslie-Bonner-Peck): h = (3 nu Q / (2 pi Omega^2 r^2))^(1/3);
    wall shear rate G = Omega^2 r h / nu."""
    h = (3 * nu * Q_m3s / (2 * math.pi * omega ** 2 * r ** 2)) ** (1 / 3)
    return h, omega ** 2 * r * h / nu

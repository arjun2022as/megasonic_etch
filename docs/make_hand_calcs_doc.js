// Hand calculations behind the slide numbers (Project 1, four cases with bubbles).
// Numbers come from docs/hand_calcs.json (written by docs/hand_calcs.py); nothing is typed by hand except
// model outputs (Fluent / 1D), which are labelled as such where a hand formula checks them.
// Run:  NODE_PATH=E:/claude_tools/node_modules node docs/make_hand_calcs_doc.js [out.docx]
// Italic markup is ~~text~~, bold is **text**.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, HeadingLevel, AlignmentType, WidthType,
  ShadingType, LevelFormat, BorderStyle, Footer, PageNumber,
} = require("docx");

const V = JSON.parse(fs.readFileSync(path.join(__dirname, "hand_calcs.json"), "utf8"));
const OUT = process.argv[2] || "C:/Users/paisr/Downloads/Project 1 - Hand calculations behind the slides.docx";
const CW = 9360;
const FONT = "Calibri";

// ---------- number formatting ----------
const SUP = { "-": "⁻", 0: "⁰", 1: "¹", 2: "²", 3: "³", 4: "⁴", 5: "⁵", 6: "⁶", 7: "⁷", 8: "⁸", 9: "⁹" };
function sci(x, sig = 3) {
  if (x === 0) return "0";
  const e = Math.floor(Math.log10(Math.abs(x)));
  const m = x / 10 ** e;
  return `${m.toFixed(sig - 1)} × 10${String(e).split("").map((c) => SUP[c]).join("")}`;
}
const fx = (x, d = 3) => Number(x).toFixed(d);
const pct = (x, d = 1) => (x * 100).toFixed(d) + " %";

// ---------- helpers ----------
function runs(text, extra = {}) {
  const out = [];
  String(text).split(/(\*\*[^*]+\*\*|~~[^~]+~~)/).forEach((s) => {
    if (!s) return;
    if (s.startsWith("**")) out.push(new TextRun({ text: s.slice(2, -2), bold: true, ...extra }));
    else if (s.startsWith("~~") && s.length > 4) out.push(new TextRun({ text: s.slice(2, -2), italics: true, ...extra }));
    else out.push(new TextRun({ text: s, ...extra }));
  });
  return out;
}
const P = (t, o = {}) => new Paragraph({ children: runs(t), spacing: { after: 100, line: 270 }, ...o });
const H1 = (t, brk = true) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)], pageBreakBefore: brk });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const B = (t) => new Paragraph({ numbering: { reference: "bul", level: 0 }, children: runs(t), spacing: { after: 50 } });
const EQ = (t) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 40, after: 80 },
  children: [new TextRun({ text: t, font: "Cambria Math", size: 23 })] });
const border = { style: BorderStyle.SINGLE, size: 4, color: "BBBBBB" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(rows, widths, head = true) {
  const tot = widths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: tot, type: WidthType.DXA }, columnWidths: widths,
    rows: rows.map((r, i) => new TableRow({
      tableHeader: head && i === 0, cantSplit: true,
      children: r.map((c, j) => new TableCell({
        borders, width: { size: widths[j], type: WidthType.DXA },
        shading: head && i === 0 ? { fill: "DCE6F1", type: ShadingType.CLEAR, color: "auto" } : undefined,
        margins: { top: 40, bottom: 40, left: 80, right: 80 },
        children: [new Paragraph({ children: runs(String(c), { size: 19, bold: head && i === 0 ? true : undefined }) })],
      })),
    })),
  });
}
const lab = (t) => new Paragraph({ keepNext: true, spacing: { before: 80, after: 40 },
  children: [new TextRun({ text: t, bold: true, size: 20, color: "2E5597" })] });
const gap = () => new Paragraph({ children: [], spacing: { after: 80 } });

// One calculation card: title, principle/law, formula(s), symbols, substitution, result, where on the slides.
let calcNo = 0;
function calc({ title, law, formula = [], symbols = [], sub = [], result, slide, note }) {
  calcNo += 1;
  const out = [H2(`C${calcNo}. ${title}`)];
  out.push(new Paragraph({ keepNext: true, spacing: { after: 60 }, children: [
    new TextRun({ text: "Principle: ", bold: true, size: 20 }), ...runs(law, { size: 20 })] }));
  if (formula.length) { out.push(lab("Formula")); formula.forEach((f) => out.push(EQ(f))); }
  if (symbols.length) {
    out.push(lab("Symbols"));
    out.push(table([["Symbol", "Meaning", "Value", "Source"], ...symbols], [1300, 3900, 2300, 1860]));
  }
  if (sub.length) { out.push(lab("Substitution")); sub.forEach((s) => out.push(EQ(s))); }
  if (result && typeof result !== "string") { out.push(lab("Result")); out.push(result); }
  else if (result) out.push(new Paragraph({ spacing: { before: 60, after: 60 }, shading: { fill: "EEF5EA", type: ShadingType.CLEAR, color: "auto" },
    children: [new TextRun({ text: "Result: ", bold: true }), ...runs(result)] }));
  if (slide) out.push(new Paragraph({ spacing: { after: 160 }, children: [new TextRun({ text: "On the slides: ", bold: true, size: 19, color: "666666" }), ...runs(slide, { size: 19, color: "666666" })] }));
  if (note) out.push(new Paragraph({ spacing: { after: 160 }, children: [new TextRun({ text: "Note: ", bold: true, size: 19, color: "9C3D00" }), ...runs(note, { size: 19, color: "9C3D00" })] }));
  return out;
}

const C = [];
const add = (...xs) => xs.flat().forEach((x) => C.push(x));

// ---------- title ----------
add(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 1200, after: 200 },
  children: [new TextRun({ text: "Hand calculations behind the slides", bold: true, size: 44, color: "1F3864" })] }));
add(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
  children: [new TextRun({ text: "Project 1: megasonics and H₂ bubbles in a TMAH-etched 3D NAND slit (100 nm × 10 µm)", size: 24 })] }));
add(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 },
  children: [new TextRun({ text: "University of Arizona · November 2026", size: 22, color: "666666" })] }));
add(P("This document contains only the closed-form (hand) calculations behind the numbers on the slides. Each calculation names the law it uses, then lists its formula, its symbols, the substitution and the result. Values from simulations are marked **ANSYS Fluent** or **1D model**; they appear only where a hand formula checks them."));
add(P("Every number was recomputed with docs/hand_calcs.py, which uses the same constants as the simulation code (etchsim/props.py). Values that are assumptions are marked **ASSUMED**."));
add(P("**Megasonic results:** imposed oscillating flow + modelled mixing, not a full acoustic-streaming solution."));
add(gap());
add(table([
  ["Part", "Content", "Slides"],
  ["A", "Constants and properties at 60 °C", "all"],
  ["B", "Sound at the wafer: plane wave, Brekhovskikh reflection, pressure antinode (99.4 %), critical and Rayleigh angles", "6"],
  ["C", "Vertical 90°: displacements and (no) mixing", "7"],
  ["D", "Inside the slit: Womersley, Moffatt–Stokes channel mode, compression breathing", "8"],
  ["E", "Horizontal 15°: slip, Stokes layer, Taylor–Aris mixing, Levich mouth drop, Rayleigh–Schlichting streaming", "4, 10"],
  ["F", "Chemistry and H₂ build-up: Seidel, Levich (spin), in-slit parabola", "2, 3, 10"],
  ["G", "Bubbles: Young–Laplace + Henry, plug growth, bubble cycle", "3, 5, 12"],
  ["H", "Percentages and ratios quoted from the model results", "3, 5, 9, 10"],
  ["I", "Levers: Arrhenius temperature, spin, wetting/degassing (Fick, Henry–Dalton)", "11, 12"],
  ["J", "Slide values to correct", "3, 4, 6, 7, 8"],
], [700, 7300, 1360]));

// ---------- A. constants ----------
add(H1("A. Constants and properties at 60 °C"));
add(table([
  ["Symbol", "Meaning", "Value", "Source"],
  ["T", "temperature", `${fx(V.T, 2)} K (60 °C)`, "ASSUMED process"],
  ["ρ_f", "liquid density (water)", `${V.rho} kg/m³`, "IAPWS"],
  ["μ", "viscosity", `${(V.mu * 1e3).toFixed(4)} mPa·s`, "IAPWS"],
  ["ν = μ/ρ_f", "kinematic viscosity", `${sci(V.nu, 4)} m²/s`, "computed"],
  ["c_f", "sound speed in the liquid", `${V.c} m/s`, "water, 60 °C"],
  ["γ", "surface tension", `${V.gamma} N/m`, "water; ASSUMED for TMAH"],
  ["p_vap", "water vapour pressure", `${(V.p_vap / 1e3).toFixed(3)} kPa`, "steam tables"],
  ["p_atm", "ambient pressure", `${(V.p_atm / 1e3).toFixed(3)} kPa`, "—"],
  ["c_sat", "H₂ solubility at 1 atm", `${V.c_sat} mol/m³ (mM)`, "ASSUMED"],
  ["W, L", "slit width, depth", "100 nm, 10 µm (AR = 100)", "proposal"],
  ["f_poly", "poly-Si fraction of the wall (50 nm / 50 nm layers)", "0.5", "ASSUMED"],
  ["pitch", "slit-to-slit spacing", "1 µm", "ASSUMED"],
  ["ER_ref", "poly-Si etch rate, 5 wt % TMAH, 60 °C", "300 nm/min = 5.00 × 10⁻⁹ m/s", "ASSUMED"],
  ["ρ_Si, M_Si", "Si density, molar mass", "2330 kg/m³, 0.028086 kg/mol", "handbook"],
  ["ρ_s, c_L, c_S", "Si density, longitudinal and shear sound speed", "2330 kg/m³, 8433 m/s, 5843 m/s", "Si [100]"],
  ["Ω", "wafer spin, 300 rpm", `${fx(V.Omega, 2)} rad/s`, "ASSUMED"],
  ["f, ω = 2πf", "megasonic frequency", `1 MHz, ${sci(V.omega, 4)} rad/s`, "proposal"],
  ["I", "acoustic intensity", "2 W/cm² = 2 × 10⁴ W/m²", "proposal"],
], [1500, 3600, 2600, 1660]));
add(gap());
add(...calc({
  title: "Diffusivities at 60 °C",
  law: "Stokes–Einstein temperature scaling: D ∝ T/μ.",
  formula: ["D(60 °C) = D(25 °C) · (T/298.15 K) · (μ₂₅/μ₆₀)"],
  symbols: [["μ₂₅", "viscosity at 25 °C", "0.8900 mPa·s", "IAPWS"], ["D₂₅", "diffusivities at 25 °C", "OH⁻ 5.273, TMA⁺ 1.196, silicate 0.92, H₂ 4.5 (× 10⁻⁹ m²/s)", "CRC; Cussler; silicate ASSUMED"]],
  sub: [`factor = (333.15/298.15) × (0.8900/0.4665) = ${fx(V.SE_factor, 4)}`],
  result: `D_OH = ${sci(V.D_OH)}, D_TMA = ${sci(V.D_TMA)}, D_SIL = ${sci(V.D_SIL)}, **D_H₂ = ${sci(V.D_H2)} m²/s**.`,
  slide: "used in every diffusion number below.",
}));
add(...calc({
  title: "TMAH concentration",
  law: "Definition of the molar concentration (TMAH is a strong base, fully dissociated).",
  formula: ["c_bulk = w · ρ_soln / M_TMAH"],
  symbols: [["w", "TMAH mass fraction", "0.05", "process"], ["ρ_soln", "solution density", "990 kg/m³", "ASSUMED"], ["M_TMAH", "molar mass (CH₃)₄NOH", "0.09115 kg/mol", "—"]],
  sub: [`c_bulk = 0.05 × 990 / 0.09115 = ${fx(V.c_bulk, 1)} mol/m³`],
  result: `c(OH⁻) = c(TMA⁺) = **${fx(V.c_bulk, 0)} mM** (0.54 M).`,
}));

// ---------- B. acoustics ----------
add(H1("B. Sound at the wafer (slide 6)"));
add(...calc({
  title: "Incoming plane wave: pressure and velocity amplitudes",
  law: "Plane-wave acoustics: I = p₀²/(2ρ_f c_f), and p₀ = ρ_f c_f U₀.",
  formula: ["Z_f = ρ_f c_f", "p₀ = √(2 Z_f I)", "U₀ = p₀ / Z_f"],
  symbols: [["Z_f", "characteristic impedance of the liquid", `${(V.Zf / 1e6).toFixed(3)} MRayl`, "computed"], ["I", "intensity", "2 × 10⁴ W/m²", "proposal"], ["p₀", "incident pressure amplitude", "—", "result"], ["U₀", "incident particle-velocity amplitude", "—", "result"]],
  sub: [`Z_f = 983.2 × 1551 = ${sci(V.Zf, 4)} kg/(m²·s)`, `p₀ = √(2 × ${sci(V.Zf, 4)} × 2 × 10⁴) = ${sci(V.p0, 4)} Pa`, `U₀ = ${sci(V.p0, 4)} / ${sci(V.Zf, 4)} = ${fx(V.U0, 4)} m/s`],
  result: `**p₀ = ${fx(V.p0 / 1e6, 3)} MPa, U₀ = ${fx(V.U0, 3)} m/s**.`,
  slide: "slide 6 'Incoming wave' (0.247 MPa, 0.16 m/s, 1.53 MRayl).",
}));
add(...calc({
  title: "Reflection from the silicon wafer at normal incidence",
  law: "Brekhovskikh, fluid on an elastic solid. At normal incidence no shear wave is excited, so R reduces to the impedance-mismatch formula.",
  formula: ["Z_s = ρ_s c_L", "R = (Z_s − Z_f) / (Z_s + Z_f)", "energy reflected = R², energy transmitted into Si = 1 − R²"],
  symbols: [["Z_s", "impedance of Si (longitudinal)", `${(V.Zs / 1e6).toFixed(2)} MRayl`, "computed"], ["R", "pressure reflection coefficient", "—", "result"]],
  sub: [`Z_s = 2330 × 8433 = ${sci(V.Zs, 4)} kg/(m²·s)`, `R = (19.649 − 1.525) / (19.649 + 1.525) = ${fx(V.R, 4)}`, `R² = ${fx(V.R2, 4)},  1 − R² = ${fx(V.T_energy, 4)}`],
  result: `**R = ${fx(V.R, 3)}**: ${pct(V.R2, 1)} of the energy reflects and ${pct(V.T_energy, 1)} enters the wafer.`,
  slide: "slide 6 'Reflection at normal incidence' (19.65 MRayl, 0.856, 73 %).",
}));
add(...calc({
  title: "Pressure antinode and velocity node at the wafer",
  law: "Superposition of incident and reflected waves at the wall: pressures add (1 + R), normal velocities subtract (1 − R), because the reflected wave travels the other way.",
  formula: ["p_wall = p₀ |1 + R|", "u_n = U₀ cos β |1 − R|  (β = angle from the normal; β = 0 at 90°)", "u_t = U₀ sin β |1 + R|  (= 0 at β = 0)"],
  symbols: [["p_wall", "pressure amplitude at the wafer", "—", "result"], ["u_n", "up-down (normal) liquid velocity at the wafer", "—", "result"], ["u_t", "sideways (tangential) slip velocity", "—", "result"], ["β", "angle from the wafer normal = 90° − θ", "0° for the MegPie", "—"]],
  sub: [`1 + R = ${fx(V.onepR, 4)},   1 − R = ${fx(V.onemR, 4)}`, `p_wall = ${fx(V.p0 / 1e6, 4)} × ${fx(V.onepR, 4)} = ${fx(V.p_wall / 1e6, 4)} MPa`, `u_n = ${fx(V.U0, 4)} × ${fx(V.onemR, 4)} = ${fx(V.u_n, 4)} m/s`, "u_t = U₀ × sin 0° × |1 + R| = 0"],
  result: `**p_wall = ${fx(V.p_wall / 1e6, 3)} MPa** (1.86 × p₀: pressure antinode), **u_n = ${fx(V.u_n, 3)} m/s** (14 % of U₀: velocity node), **u_t = 0** (no slip).`,
  slide: "slide 6 'At the wafer surface'.",
}));
add(...calc({
  title: "Where the wave energy sits at the wafer: the 99.4 % pressure share",
  law: "Acoustic energy density = potential (compression) part p²/(2ρ_f c_f²) + kinetic part ρ_f u²/2. At the wafer the pressure is at its maximum and the velocity at its minimum.",
  formula: ["e_pot = p_wall² / (2 ρ_f c_f²)", "e_kin = ρ_f u_n² / 2", "e_kin / e_pot = (Z_f u_n / p_wall)² = ((1 − R)/(1 + R))²", "pressure share = e_pot / (e_pot + e_kin)"],
  symbols: [["e_pot", "compression (pressure) energy density at the wall", "—", "result"], ["e_kin", "motion (kinetic) energy density at the wall", "—", "result"]],
  sub: [`e_pot = (4.584 × 10⁵)² / (2 × 983.2 × 1551²) = ${fx(V.E_pot, 2)} J/m³`, `e_kin = 983.2 × ${fx(V.u_n, 4)}² / 2 = ${fx(V.E_kin, 4)} J/m³`, `e_kin / e_pot = (${fx(V.onemR, 4)} / ${fx(V.onepR, 4)})² = ${fx(V.kin_over_pot, 5)}`, `pressure share = 1 / (1 + ${fx(V.kin_over_pot, 5)}) = ${pct(V.frac_pot, 2)}`],
  result: `**${pct(V.frac_pot, 1)} of the wave energy at the wafer is pressure; only ${pct(V.frac_kin, 2)} is motion.**`,
  slide: "slide 6 '99.4 %'. The motion share is 0.60 %, not 0.06 % (see Part J).",
}));
add(...calc({
  title: "Critical angles and the Rayleigh angle (dip/spike at 72–79°)",
  law: "Snell's law at the liquid–Si interface: a wave refracted into the solid stops entering when sin β = c_f / c_solid. The Rayleigh angle is where the trace speed along the wafer equals silicon's surface (Rayleigh) wave speed c_R, the root of the Rayleigh equation (isotropic Si, ASSUMED).",
  formula: ["β_L = arcsin(c_f / c_L),   β_S = arcsin(c_f / c_S),   θ = 90° − β (θ measured from the surface)", "Rayleigh equation: x³ − 8x² + (24 − 16k²) x − 16(1 − k²) = 0,  x = (c_R/c_S)²,  k = c_S/c_L", "β_R = arcsin(c_f / c_R)"],
  symbols: [["c_L, c_S", "longitudinal, shear speed in Si", "8433, 5843 m/s", "Si [100]"], ["c_R", "Rayleigh surface-wave speed", "—", "result"], ["ν_P", "Poisson ratio implied by c_L/c_S", fx(V.poisson, 3), "computed"]],
  sub: [`β_L = arcsin(1551/8433) = ${fx(V.beta_L, 2)}° → θ_L = ${fx(V.theta_L, 1)}°`, `β_S = arcsin(1551/5843) = ${fx(V.beta_S, 2)}° → θ_S = ${fx(V.theta_S, 1)}°`, `k = 5843/8433 = ${fx(5843 / 8433, 4)} → c_R = ${fx(V.cR, 0)} m/s`, `β_R = arcsin(1551/${fx(V.cR, 0)}) = ${fx(V.beta_R, 2)}° → θ_R = ${fx(V.theta_R, 1)}°`],
  result: `the push (longitudinal) wave stops entering Si at **θ ≈ ${fx(V.theta_L, 0)}°**, the shear wave at **≈ ${fx(V.theta_S, 0)}°**, and the Rayleigh angle is **≈ ${fx(V.theta_R, 1)}°**.`,
  slide: "slide 6, Fig. 4 caption (~79°, ~75°, ~72°).",
  note: "The Poisson ratio implied by the [100] speeds is low (0.04) because Si is anisotropic; the Rayleigh angle is therefore approximate (±1°).",
}));

// ---------- C. 90 deg ----------
add(H1("C. Vertical 90°: the up-down motion (slide 7)"));
add(...calc({
  title: "Diffusion-layer thickness above the mouth",
  law: "Levich film: the mass-transfer coefficient defines a Nernst diffusion layer δ_N = D/k_m (k_m from C18).",
  formula: ["δ_N = D_H₂ / k_m"],
  symbols: [["k_m", "Levich mass-transfer coefficient, 300 rpm", `${sci(V.km)} m/s`, "C14"]],
  sub: [`δ_N = ${sci(V.D_H2)} / ${sci(V.km)} = ${sci(V.deltaN)} m`],
  result: `**δ_N = ${fx(V.deltaN * 1e6, 0)} µm**.`,
  slide: "slide 7 (54 µm).",
}));
add(...calc({
  title: "Up-down displacement of the liquid at 90°",
  law: "Standing wave near the wall (incident + reflected). The velocity at the wall is u_n; moving away from the wall it grows by U₀|1 + R| k z for small kz. Displacement = velocity / ω, with k = ω/c_f.",
  formula: ["ξ_wall = u_n / ω", "ξ(z) − ξ_wall ≈ U₀ |1 + R| k z / ω = U₀ |1 + R| z / c_f"],
  symbols: [["ξ", "up-down (normal) displacement amplitude", "—", "result"], ["z", "height above the wafer; here z = δ_N", `${fx(V.deltaN * 1e6, 0)} µm`, "C8"]],
  sub: [`ξ_wall = ${fx(V.u_n, 4)} / ${sci(V.omega, 4)} = ${fx(V.xi_n_wall * 1e9, 2)} nm`, `ξ(δ_N) = ${fx(V.U0, 4)} × ${fx(V.onepR, 4)} × ${sci(V.deltaN)} / 1551 = ${fx(V.xi_z * 1e9, 1)} nm`, `ξ / δ_N = ${sci(V.xi_z_frac, 2)} = ${(V.xi_z_frac * 100).toFixed(3)} %`],
  result: `the film moves up and down by only **~${fx(V.xi_z * 1e9, 0)} nm** across the 54 µm diffusion layer (**${(V.xi_z_frac * 100).toFixed(2)} %** of it), in phase and reversibly, so there is no net transport.`,
  slide: "slide 7 'The film only moves ~10 nm'. This is a normal (compression) displacement, not shear (see Part J).",
}));
add(...calc({
  title: "Mixing by the up-down motion",
  law: "Taylor–Aris (oscillatory) dispersion, upper bound: a particle swept ±u/ω each cycle while it diffuses gains at most D_osc = u²/(2ω).",
  formula: ["D_osc = u² / (2ω)", "90°: u_t = 0 ⇒ D_osc = 0;  counting u_n anyway: D_osc,n = u_n² / (2ω)"],
  symbols: [["D_osc", "extra (oscillatory) diffusivity", "—", "result"]],
  sub: [`D_osc,n = ${fx(V.u_n, 4)}² / (2 × ${sci(V.omega, 4)}) = ${sci(V.D_osc_n)} m²/s`, `D_osc,n / D_H₂ = ${sci(V.D_osc_n)} / ${sci(V.D_H2)} = ${pct(V.D_osc_n_frac, 2)}`],
  result: `**D_osc = 0** from slip; even counting u_n it is **${sci(V.D_osc_n, 2)} m²/s = ${pct(V.D_osc_n_frac, 1)} of D_H₂**, so the mouth stays at 63×.`,
  slide: "slide 7 'No oscillatory mixing'.",
}));

// ---------- D. slit ----------
add(H1("D. Inside the slit: why neither angle gets in (slide 8)"));
add(...calc({
  title: "Stokes (viscous) layer thickness",
  law: "Stokes' second problem: an oscillating flow over a wall is confined to a layer δ = √(2ν/ω).",
  formula: ["δ = √(2ν/ω)"],
  sub: [`δ = √(2 × ${sci(V.nu, 4)} / ${sci(V.omega, 4)}) = ${sci(V.delta, 4)} m`],
  result: `**δ = ${fx(V.delta * 1e6, 2)} µm**.`,
  slide: "slides 4 and 8 (0.39 µm).",
}));
add(...calc({
  title: "Womersley number of the slit",
  law: "Navier–Stokes scaling. Momentum: ρ ∂u/∂t = −∂p/∂x + μ ∂²u/∂y². With ∂/∂t ~ ω and ∂²/∂y² ~ 1/(W/2)², inertia ÷ friction = ω(W/2)²/ν = Wo².",
  formula: ["Wo = (W/2) √(ω/ν)", "inertia / friction = Wo²", "t_visc = (W/2)²/ν (friction crosses the half-gap),   t_flow = 1/ω"],
  symbols: [["Wo", "Womersley number", "—", "result"], ["W/2", "half-gap", "5 × 10⁻⁸ m", "—"]],
  sub: [`√(ω/ν) = √(${sci(V.omega, 4)} / ${sci(V.nu, 4)}) = ${sci(V.sqrt_om_nu, 4)} m⁻¹`, `Wo = 5 × 10⁻⁸ × ${sci(V.sqrt_om_nu, 4)} = ${fx(V.Wo, 3)}`, `Wo² = ${fx(V.Wo2, 4)} = ${pct(V.Wo2, 1)}`, `δ / (W/2) = ${fx(V.delta * 1e9, 1)} / 50 = ${fx(V.delta_over_half, 2)}`, `t_visc = (5 × 10⁻⁸)² / ${sci(V.nu, 4)} = ${fx(V.t_visc * 1e9, 2)} ns;   t_flow = 1/ω = ${fx(V.t_flow * 1e9, 0)} ns`, `above the wafer (2 mm gap, half-gap 1 mm): Wo = 10⁻³ × ${sci(V.sqrt_om_nu, 4)} = ${fx(V.Wo_gap, 0)}`],
  result: `**Wo = ${fx(V.Wo, 2)}, Wo² = ${pct(V.Wo2, 1)}**: inertia is only 3 % of friction, so the liquid in the slit follows the wall without lag (quasi-steady Stokes flow). The half-gap is **${fx(V.delta_over_half, 1)}× thinner** than δ; friction crosses it in **${fx(V.t_visc * 1e9, 1)} ns** against **${fx(V.t_flow * 1e9, 0)} ns** for the flow to change. Above the wafer, **Wo ≈ ${fx(V.Wo_gap, 0)}**: free sloshing.`,
  slide: "slide 8 'Proof' (0.18, 3 %, 8×, 5 ns vs 160 ns, 3600).",
}));
add(...calc({
  title: "Decay of a mouth-driven flow into the slit",
  law: "Moffatt / Papkovich–Fadle Stokes channel mode: flow driven across the mouth of a channel dies with depth as the slowest eigenmode, u(z) ∝ e^(−K z/W), K = 4.2124 (2 × 2.1062 for the half-width).",
  formula: ["u(z) / u_mouth = exp(−K z / W)"],
  symbols: [["K", "slowest Stokes-mode decay rate per width", fx(V.K, 4), "Moffatt 1964"], ["z", "depth below the mouth", "100 nm, 1 µm", "—"]],
  sub: [`z = 100 nm: exp(−4.2124 × 1) = ${fx(V.moffatt_100, 4)} → ${pct(1 - V.moffatt_100, 1)} lost`, `z = 1 µm: exp(−42.124) = ${sci(V.moffatt_1um, 2)} → nothing left`],
  result: `**98.5 % of the drag is gone 100 nm below the mouth**; nothing is left at 1 µm.`,
  slide: "slide 8 'Drag at the mouth dies fast' and the '100 nm: 98.5 %' headline.",
}));
add(...calc({
  title: "Wavelength and compression breathing of the slit",
  law: "Plane-wave acoustics: λ = c/f. Because L ≪ λ, the whole slit sees the same pressure at the same moment (in phase). Its liquid is compressed by p_wall/(ρc²) (compressibility 1/(ρc²)) and breathes through the mouth.",
  formula: ["λ = c_f / f", "ξ_breath = L · p_wall / (ρ_f c_f²)"],
  symbols: [["λ", "acoustic wavelength", "—", "result"], ["ξ_breath", "displacement of the liquid at the mouth per cycle", "—", "result"]],
  sub: [`λ = 1551 / 10⁶ = ${fx(V.lam * 1e3, 3)} mm;   L/λ = ${fx(V.L_over_lam, 4)}`, `ξ_breath = 10⁻⁵ × ${sci(V.p_wall, 4)} / (983.2 × 1551²) = ${fx(V.breath * 1e9, 2)} nm`],
  result: `**λ = 1.55 mm ≫ L = 10 µm**; the slit is squeezed in phase and breathes only **≈ ${fx(V.breath * 1e9, 1)} nm**.`,
  slide: "slide 8 'No push along the slit' and the '≈1.9 nm' headline.",
}));

// ---------- E. 15 deg ----------
add(H1("E. Horizontal 15°: what the slip does above the mouth (slides 4, 10)"));
add(...calc({
  title: "Sideways slip at 15°",
  law: "Brekhovskikh reflection at oblique incidence. At β = 75° both refracted waves in Si are past their critical angles (evanescent), so |R| = 1 and only the phase changes. The tangential velocities of the incident and reflected waves add.",
  formula: ["u_t = U₀ sin β |1 + R|,   β = 90° − θ = 75°"],
  symbols: [["|1 + R|", "slip amplification at 15° (full Brekhovskikh R, complex)", fx(V.R15_abs1pR, 3), "computed (acoustics.py)"], ["sin β", "sin 75°", fx(V.sinb15, 4), "—"]],
  sub: [`u_t = ${fx(V.U0, 4)} × ${fx(V.sinb15, 4)} × ${fx(V.R15_abs1pR, 4)} = ${fx(V.u_t15, 4)} m/s`],
  result: `**u_t = ${fx(V.u_t15, 3)} m/s** (|1 + R| ≈ ${fx(V.R15_abs1pR, 2)}).`,
  slide: "slide 4 'Slip at the wafer' (|1+R| ≈ 1.99, 0.311 m/s) and slide 10.",
}));
add(...calc({
  title: "Shear rate and sideways displacement",
  law: "The slip is taken up across the Stokes layer δ (C11). Displacement amplitude = velocity / ω.",
  formula: ["shear ≈ u_t / δ", "ξ_t = u_t / ω"],
  sub: [`shear = ${fx(V.u_t15, 4)} / ${sci(V.delta, 4)} = ${sci(V.shear15, 3)} s⁻¹`, `ξ_t = ${fx(V.u_t15, 4)} / ${sci(V.omega, 4)} = ${fx(V.xi_t15 * 1e9, 1)} nm`],
  result: `**shear ≈ ${sci(V.shear15, 1)} s⁻¹**; the film slides sideways **±${fx(V.xi_t15 * 1e9, 0)} nm** each cycle, and neighbouring points move at different moments (travelling along the wafer).`,
  slide: "slide 4 'Sheared layer' (8 × 10⁵ s⁻¹) and slide 7 (50 nm).",
}));
add(...calc({
  title: "Film mixing at 15°",
  law: "Taylor–Aris oscillatory dispersion, upper bound (as C10).",
  formula: ["D_osc = u_t² / (2ω)"],
  sub: [`D_osc = ${fx(V.u_t15, 4)}² / (2 × ${sci(V.omega, 4)}) = ${sci(V.D_osc15, 4)} m²/s`, `D_osc / D_H₂ = ${fx(V.D_osc15 / V.D_H2, 3)}`],
  result: `**D_osc = ${sci(V.D_osc15, 2)} m²/s**, about 0.8 × D_H₂ (same order).`,
  slide: "slide 4 'Film mixing' and slide 10.",
}));
add(...calc({
  title: "Levich mass-transfer coefficient at 300 rpm",
  law: "Levich rotating-disk mass transfer: k_m = 0.620 D^(2/3) ν^(−1/6) Ω^(1/2).",
  formula: ["k_m = 0.620 · D_H₂^(2/3) · ν^(−1/6) · Ω^(1/2)"],
  symbols: [["k_m", "H₂ mass-transfer coefficient from the wafer to the bulk", "—", "result"], ["Ω", "spin rate", `${fx(V.Omega, 3)} rad/s`, "300 rpm, ASSUMED"]],
  sub: [`D_H₂^(2/3) = ${sci(V.D_H2 ** (2 / 3), 4)};  ν^(−1/6) = ${fx(V.nu ** (-1 / 6), 3)};  Ω^(1/2) = ${fx(V.Omega ** 0.5, 3)}`, `k_m = 0.620 × ${sci(V.D_H2 ** (2 / 3), 4)} × ${fx(V.nu ** (-1 / 6), 3)} × ${fx(V.Omega ** 0.5, 3)} = ${sci(V.km, 4)} m/s`],
  result: `**k_m = ${sci(V.km, 3)} m/s**.`,
  slide: "behind the mouth 63× (slides 2, 3, 10).",
}));
add(...calc({
  title: "Mouth H₂ drop at 15°",
  law: "Levich with the film diffusivity raised to D + D_osc: k_m ∝ D^(2/3), and the mouth excess Δc = J/k_m ∝ 1/k_m.",
  formula: ["k_m(15°) / k_m(0) = ((D_H₂ + D_osc) / D_H₂)^(2/3)", "S_mouth(15°) = S_mouth(0) / gain"],
  sub: [`gain = ((${sci(V.D_H2, 3)} + ${sci(V.D_osc15, 3)}) / ${sci(V.D_H2, 3)})^(2/3) = ${fx(V.km_gain15, 3)}`, `S_mouth = 63 / ${fx(V.km_gain15, 3)} = ${fx(V.S_mouth15, 1)}×`],
  result: `**k_m × ${fx(V.km_gain15, 2)}, mouth 63× → ${fx(V.S_mouth15, 0)}×** (ANSYS Fluent: 42–43×).`,
  slide: "slide 4 'Mouth H₂ falls' and slide 10 (43×; floor 43 + 59 ≈ 102×).",
}));
add(...calc({
  title: "Steady (Rayleigh–Schlichting) streaming above the Stokes layer, estimate",
  law: "Rayleigh–Schlichting boundary-layer streaming: the steady slip just outside the Stokes layer is of order u_s = 3u_t²/(4c_f). Not solved in Fluent; order of magnitude only.",
  formula: ["u_s ≈ 3 u_t² / (4 c_f)"],
  sub: [`u_s ≈ 3 × ${fx(V.u_t15, 4)}² / (4 × 1551) = ${sci(V.u_stream15, 3)} m/s`],
  result: `**u_s ≈ ${fx(V.u_stream15 * 1e6, 0)} µm/s** (order 50 µm/s).`,
  slide: "slide 4 bottom bar ('≈60 µm/s est.'), see Part J.",
}));

// ---------- F. chemistry and H2 ----------
add(H1("F. Chemistry and H₂ build-up in the slit (slides 2, 3, 10)"));
add(...calc({
  title: "Si dissolution flux and H₂ production",
  law: "Seidel reaction (KOH, taken for TMAH): Si + 2 OH⁻ + 2 H₂O → SiO₂(OH)₂²⁻ + 2 H₂. Each Si atom removed uses 2 OH⁻ and makes 1 silicate and 2 H₂.",
  formula: ["N_Si = ER_ref · ρ_Si / M_Si", "N_H₂ = 2 N_Si  (per m² of poly-Si)", "q = N_H₂ · (2/W) · f_poly  (slit-averaged volumetric H₂ source, two walls)"],
  symbols: [["N_Si", "Si removed per wall area per second", "—", "result"], ["N_H₂", "H₂ made per poly-Si area", "—", "result"], ["q", "H₂ source per liquid volume in the slit", "—", "result"]],
  sub: [`N_Si = 5.00 × 10⁻⁹ × 2330 / 0.028086 = ${sci(V.N_Si, 4)} mol/(m²·s)`, `N_H₂ = 2 × ${sci(V.N_Si, 4)} = ${sci(V.N_H2_wall, 4)} mol/(m²·s)  (= OH⁻ use)`, `q = ${sci(V.N_H2_wall, 4)} × (2 / 10⁻⁷) × 0.5 = ${fx(V.q_H2, 0)} mol/(m³·s)`],
  result: `**q ≈ ${fx(V.q_H2, 0)} mol H₂ per m³ per s** inside the slit at full rate.`,
  slide: "slide 2 (Seidel reaction, 'every Si atom releases 2 H₂').",
}));
add(...calc({
  title: "H₂ at the mouth",
  law: "Mass balance plus Levich film: all H₂ made in one slit leaves through the mouth and is spread over one pitch of wafer; the film then needs Δc = J/k_m to carry it away.",
  formula: ["G = N_H₂ · 2L · f_poly  (per metre of slit)", "J = G / pitch", "Δc_mouth = J / k_m,   S_mouth = Δc_mouth / c_sat"],
  symbols: [["G", "H₂ leaving one slit per metre of slit length", "—", "result"], ["J", "H₂ flux per wafer area", "—", "result"], ["S", "H₂ saturation (multiples of c_sat)", "—", "result"]],
  sub: [`G = ${sci(V.N_H2_wall, 4)} × 2 × 10⁻⁵ × 0.5 = ${sci(V.G_slit, 4)} mol/(m·s)`, `J = ${sci(V.G_slit, 4)} / 10⁻⁶ = ${sci(V.J_wafer, 4)} mol/(m²·s)`, `Δc = ${sci(V.J_wafer, 4)} / ${sci(V.km, 4)} = ${fx(V.dc_mouth, 2)} mol/m³ → S = ${fx(V.S_mouth_full, 1)}× at full 300 nm/min`, `at the actual mean wall rate (294 top, 281.5 bottom → ${fx(V.mean_er_frac, 3)} × ER_ref): S_mouth = ${fx(V.S_mouth_scaled, 1)}×`],
  result: `**S_mouth ≈ ${fx(V.S_mouth_scaled, 0)}×** (1D model: 63×).`,
  slide: "slides 2, 3, 10 ('~63× at the mouth').",
}));
add(...calc({
  title: "H₂ rise from the mouth to the floor",
  law: "Steady 1D diffusion with a uniform source and a closed floor (no flux at z = L): c(z) is a parabola, c_floor − c_mouth = qL²/(2D).",
  formula: ["Δc_rise = q L² / (2 D_H₂),   S_floor = S_mouth + Δc_rise / c_sat"],
  sub: [`Δc_rise = ${fx(V.q_H2, 0)} × (10⁻⁵)² / (2 × ${sci(V.D_H2, 4)}) = ${fx(V.dc_rise, 2)} mol/m³ → ${fx(V.S_rise_full, 1)}× at full rate`, `scaled to the mean rate: ${fx(V.S_rise_scaled, 1)}×;   S_floor = ${fx(V.S_mouth_scaled, 1)} + ${fx(V.S_rise_scaled, 1)} = ${fx(V.S_floor_scaled, 1)}×`],
  result: `**in-slit rise ≈ +${fx(V.S_rise_scaled, 0)}×, floor ≈ ${fx(V.S_floor_scaled, 0)}×** (1D model: 121–122×; ANSYS Fluent: 131×). The rise is set by L, q and D only, so spin and sound cannot touch it.`,
  slide: "slide 3, slide 8 bottom bar ('in-slit +59×'), slide 10 (63× / 121×).",
}));

// ---------- G. bubbles ----------
add(H1("G. Bubbles: when they form and how fast they grow (slides 3, 5, 12)"));
add(...calc({
  title: "The plug level: 13.9×",
  law: "Young–Laplace + Henry's law. A gas plug spanning the slit has a cylindrical meniscus of radius W/2, so its gas is at p_g = p_atm + 2γ/W − p_vap (water vapour shares the gas). Henry's law: liquid in equilibrium with H₂ at p_g holds c* = c_sat · p_g/p_atm. The plug grows whenever the liquid is above c*.",
  formula: ["Δp = γ / (W/2) = 2γ/W", "p_g = p_atm + 2γ/W − p_vap", "S_plug = p_g / p_atm,   c* = c_sat · S_plug", "ρ_g = p_g / (R_gas T)  (moles of gas per m³ in the plug)"],
  symbols: [["Δp", "Laplace pressure of the meniscus", "—", "result"], ["p_g", "gas pressure in the plug", "—", "result"], ["c*", "H₂ held at the plug surface", "—", "result"], ["R_gas", "gas constant", "8.3145 J/(mol·K)", "—"]],
  sub: [`2γ/W = 2 × 0.0662 / 10⁻⁷ = ${fx(V.dp_plug / 1e6, 3)} MPa`, `p_g = 0.1013 + 1.3240 − 0.0199 = ${fx(V.p_gas / 1e6, 3)} MPa`, `S_plug = ${sci(V.p_gas, 4)} / 101325 = ${fx(V.S_plug, 2)}×;   c* = 0.70 × ${fx(V.S_plug, 2)} = ${fx(V.c_star, 2)} mM`, `ρ_g = ${sci(V.p_gas, 4)} / (8.3145 × 333.15) = ${fx(V.rho_gas, 1)} mol/m³`],
  result: `**plug level 13.9×, p_g = ${fx(V.p_gas / 1e6, 2)} MPa (~14 atm)**; H₂ at the plug surface c* = ${fx(V.c_star, 1)} mM; gas density ρ_g = ${fx(V.rho_gas, 0)} mol/m³.`,
  slide: "slides 3, 5, 12 ('13.9×', 'a plug holds ~14 atm').",
}));
add(...calc({
  title: "Smaller seed levels: 27× and ~100×",
  law: "Same Young–Laplace + Henry balance for a pinned surface nanobubble cap of radius r (spherical cap, Δp = 2γ/r): S_max(r) = 1 + (2γ/r − p_vap)/p_atm. Below S_max the cap stays small; above it the cap grows into a plug.",
  formula: ["S_max(r) = 1 + (2γ/r − p_vap) / p_atm"],
  sub: [`r = 50 nm: 1 + (2.648 − 0.0199) MPa / 0.1013 MPa = ${fx(V.S_50, 1)}×`, `r = 13.4 nm: 1 + (9.881 − 0.0199) MPa / 0.1013 MPa = ${fx(V.S_13, 1)}×`],
  result: `**50 nm seed: ${fx(V.S_50, 0)}×; 13 nm seed: ≈ ${fx(V.S_13, 0)}×** (window.py, with its own γ(T) and c_sat(T): 98.6×).`,
  slide: "slide 11 ('50 nm level 27×', '13 nm level 100×').",
}));
add(...calc({
  title: "Time for fresh liquid to reach the plug level",
  law: "Accumulation with no loss (diffusion is too slow at early times): dc/dt = q.",
  formula: ["t = c* / q"],
  sub: [`t = ${fx(V.c_star, 3)} / ${fx(V.q_H2, 0)} = ${fx(V.t_13_9 * 1e3, 2)} ms`],
  result: `**H₂ passes 13.9× about ${fx(V.t_13_9 * 1e3, 1)} ms after a refill.**`,
  slide: "slide 12 ('H₂ passes 13.9× in ~1.2 ms').",
}));
add(...calc({
  title: "Plug growth speed: hand check of ANSYS Fluent",
  law: "Fick's law in the liquid column of height ℓ = L − l above a plug of length l: uniform source q, c = c_mouth at the top, c = c* at the plug. H₂ reaching the plug = diffusion from the mouth plus half the H₂ made in the column. The plug lengthens as the gas collects: v = N/ρ_g.",
  formula: ["N = D_H₂ (c_mouth − c*) / ℓ + q ℓ / 2", "v = N / ρ_g"],
  symbols: [["l, ℓ", "plug length, liquid column above it", "1, 3, 6 µm; 9, 7, 4 µm", "Fluent cases"], ["c_mouth", "mouth H₂ from the Fluent run", "63.3×, 61.4×, 56.9× of 0.70 mM", "ANSYS Fluent"], ["v", "plug growth speed", "—", "result"]],
  sub: V.plug_rows.map((r) => `l = ${r.lp} µm: N = ${fx(r.N_diff, 4)} + ${fx(r.N_gen, 4)} = ${fx(r.N_diff + r.N_gen, 4)} mol/(m²·s) → v = ${fx(r.v_hand, 1)} µm/s`),
  result: table([["Plug (flat)", "Hand v (µm/s)", "ANSYS Fluent v (µm/s)", "Difference"],
    ...V.plug_rows.map((r) => [`${r.lp} µm`, fx(r.v_hand, 1), fx(r.v_fluent, 1), `${r.err >= 0 ? "+" : ""}${fx(r.err, 1)} %`])], [2000, 2200, 2600, 2000]),
  slide: "slides 3, 5, 9, 10 ('143–183 µm/s'). The hand formula reproduces Fluent within 0.05–2.3 %.",
}));
add(...calc({
  title: "Bubble-cycle time: hand estimate of the 1D result",
  law: "Integrate the growth law of C27 from ℓ = L (fresh plug at the floor) to ℓ = 0 (plug reaches the mouth), holding the mouth at ~61×.",
  formula: ["dt = ρ_g dℓ / (D Δc/ℓ + qℓ/2)  ⇒  t_cycle = (ρ_g / q) · ln(1 + qL² / (2 D Δc)),   Δc = c_mouth − c*"],
  sub: [`Δc = 61 × 0.70 − ${fx(V.c_star, 2)} = ${fx(V.cycle_dc, 2)} mol/m³`, `qL²/(2DΔc) = ${fx(V.q_H2, 0)} × 10⁻¹⁰ / (2 × ${sci(V.D_H2, 4)} × ${fx(V.cycle_dc, 2)}) = ${fx(V.cycle_arg, 3)}`, `t_cycle = (${fx(V.rho_gas, 1)} / ${fx(V.q_H2, 0)}) × ln(${fx(1 + V.cycle_arg, 3)}) = ${fx(V.cycle_hand * 1e3, 1)} ms`],
  result: `**t_cycle ≈ ${fx(V.cycle_hand * 1e3, 0)} ms** by hand; the **1D model gives 48.6 ms** (flat walls), about 5 % shorter. The hand estimate holds the mouth fixed and ignores the comb pockets (37.3 ms in 1D).`,
  slide: "slides 3, 10 ('48.6 ms'); the slide value is the 1D-model result.",
}));

// ---------- H. percentages ----------
add(H1("H. Percentages and ratios quoted from the model results (slides 3, 5, 9, 10)"));
add(P("These are hand arithmetic on simulation outputs (ANSYS Fluent growth speeds; 1D recesses)."));
const names = ["flat 1 µm", "flat 3 µm", "flat 6 µm", "comb 1 µm", "comb 3 µm", "comb 6 µm"];
const none = [143.0, 145.2, 175.0, 147.7, 151.0, 183.4], d90 = [143.0, 145.5, 176.2, 147.9, 151.3, 184.7], d15 = [115.3, 111.2, 129.4, 118.3, 115.2, 136.7];
add(lab("Plug growth change from no sound: (v_sound / v_none − 1) × 100 %"));
add(table([["Plug", "No sound", "90°", "Change 90°", "15°", "Change 15°"],
  ...names.map((n, i) => [n, fx(none[i], 1), fx(d90[i], 1), `+${fx(V.pct90[i], 2)} %`, fx(d15[i], 1), `${fx(V.pct15[i], 1)} %`])],
[1700, 1300, 1300, 1700, 1300, 2060]));
add(P(`**Result:** 15° slows the plug by **19.4 to 26.1 %** (slide: −19 to −26 %); 90° changes it by **0 to +0.71 %** (slide: +0.2–0.7 %). The flat 1 µm "no sound" value is the 90° run (B0_floor did not print it).`, { spacing: { before: 100, after: 100 } }));
add(lab("2-minute comb-wall bottom recess with seeds (1D)"));
add(EQ(`change = 253.3 / 311.7 − 1 = ${fx(V.recess_pct, 1)} %`));
add(EQ(`bottom/top after 2 min: 15° = 253.3 / 591 = ${fx(V.bt_15, 3)};   no sound / 90° = 311.7 / 588 = ${fx(V.bt_none, 3)}`));
add(EQ(`bubble-free bottom in 2 min = 281.5 nm/min × 2 min = ${fx(V.bubblefree_2min, 0)} nm`));
add(P(`**Result:** 312 → 253 nm is **${fx(V.recess_pct, 0)} %** (slide 5: −19 %); bottom/top **0.43 vs 0.53** (slide 9); bubble-free **563 nm** (slide 3 says 562; see Part J).`));

// ---------- I. levers ----------
add(H1("I. Levers: temperature, spin, wetting and degassing (slides 11, 12)"));
add(...calc({
  title: "Etch rate against temperature",
  law: "Arrhenius: ER(T) = ER_ref · exp[−(E_a/k_B)(1/T − 1/T_ref)].",
  formula: ["ER(T) = 300 nm/min × exp[−(E_a/k_B)(1/T − 1/333.15 K)]"],
  symbols: [["E_a", "activation energy, TMAH on Si(100)", "0.57 eV", "literature, ASSUMED for poly-Si"], ["k_B", "Boltzmann constant", "8.617 × 10⁻⁵ eV/K", "—"]],
  sub: [`e.g. 25 °C: exp[−(0.57/8.617 × 10⁻⁵)(1/298.15 − 1/333.15)] = ${fx(V.ER_25 / 300, 4)} → ${fx(V.ER_25, 1)} nm/min`],
  result: table([["T (°C)", "60", "55", "50", "45", "40", "35", "30", "25", "20"],
    ["ER (nm/min)", ...[60, 55, 50, 45, 40, 35, 30, 25, 20].map((t) => fx(V["ER_" + t], 0))]], [1240, ...Array(9).fill(902)]),
  slide: "slide 11, y-axis labels. The slide row labels are the model's top etch rates (≈0.98 × this, e.g. 294 and 218 nm/min at 60 and 55 °C), which include the slight OH⁻ drop at the mouth.",
}));
add(...calc({
  title: "Faster spin: 300 → 1000 rpm",
  law: "Levich: k_m ∝ Ω^(1/2), so the mouth excess falls as Ω^(−1/2). The in-slit rise (C23) does not depend on spin.",
  formula: ["S_mouth(1000) = S_mouth(300) / √(1000/300)", "S_floor(1000) = S_mouth(1000) + in-slit rise"],
  sub: [`√(1000/300) = ${fx(V.rpm_gain_1000, 3)};   S_mouth = 63 / ${fx(V.rpm_gain_1000, 3)} = ${fx(V.S_mouth_1000, 1)}×`, `S_floor ≈ ${fx(V.S_mouth_1000, 1)} + 59.5 = ${fx(V.S_floor_1000, 1)}×`],
  result: `**floor ≈ ${fx(V.S_floor_1000, 0)}× < 98.6×**: with few seeds no bubble forms, so the bottom etches at nearly the full rate (1D model: 28.7 → 283.6 nm/min). With plug seeds, 94× is still far above 13.9×, so plugs remain (≈3 → 4 nm/min).`,
  slide: "slide 11 (29 → 284 nm/min with few seeds; 3 → 4 with seeds).",
}));
add(...calc({
  title: "How long fresh TMAH needs to fill a pre-wetted slit",
  law: "Fick diffusion time scale t ~ L²/D.",
  formula: ["t ≈ L² / D"],
  sub: [`OH⁻: (10⁻⁵)² / ${sci(V.D_OH, 4)} = ${fx(V.t_LD_OH * 1e3, 1)} ms;   H₂: (10⁻⁵)² / ${sci(V.D_H2, 4)} = ${fx(V.t_LD_H2 * 1e3, 1)} ms`],
  result: "**≈ 10 ms**: degassed TMAH reaches the floor of a water-filled slit almost at once.",
  slide: "slide 12, step 2.",
}));
add(...calc({
  title: "What dissolved air changes",
  law: "Henry's law + Dalton's law of partial pressures: other dissolved gases (N₂, O₂) also enter the bubble, so H₂ needs to supply only p_g − p_other: S_need = (p_atm + 2γ/W − p_vap − p_other)/p_atm.",
  formula: ["ΔS_need = − p_other / p_atm"],
  sub: ["air-saturated liquid: p_other ≈ 1 atm → S_need 13.9× → 12.9×;   fully degassed: 13.9×", "relative change = 1 / 13.9 = 7 % of the plug level"],
  result: "**about 1× per atm of dissolved gas**, small next to the 14 atm a plug holds. Degassing matters because it removes seeds (trapped air dissolves faster), not because it shifts the level.",
  slide: "slide 12, 'What degassing does — and does not'.",
}));
add(...calc({
  title: "Margin for 'keep the floor ≤ 80×'",
  law: "Ratio of the few-seed bubble level to the target floor level.",
  formula: ["margin = S_13 nm / S_floor,target"],
  sub: ["margin = 98.6 / 80 = 1.23"],
  result: "**~23 % headroom** below the ~100× few-seed level.",
  slide: "slide 12 bottom bar.",
}));

// ---------- J. corrections ----------
add(H1("J. Slide values to correct"));
add(table([
  ["Slide", "Now on the slide", "Hand calculation gives", "Suggested wording"],
  ["6", "u_n … velocity node (0.06 % of utilized wave)", "kinetic share = ((1−R)/(1+R))² / (1 + …) = 0.60 % (C6)", "'… velocity node (0.6 % of the wave energy at the wafer)'; and '99.4 % of the wave energy at the wafer is pressure'"],
  ["7", "ξ (shear) = 0.16 × 1.856 × 54 × 10⁻⁶ / 1555 ≈ 10 nm", "this is the up-down (normal, compression) displacement, not shear (C9)", "'ξ_n (up-down) ≈ 10 nm'"],
  ["7", "ξ (shear) = 50 nm at 15°", "sideways displacement u_t/ω = 49.4 nm (C16)", "'ξ_t (sideways) = u_t/ω ≈ 50 nm'"],
  ["8", "Wo² = 3 %: 'the liquid's momentum … as strong as the wall friction'", "inertia is only 3.3 % of friction: friction is ~30× stronger (C12)", "'inertia is only 3 % of wall friction, so the slit liquid follows the wall with no lag'"],
  ["8", "√(ω/ν) = 3.62 × 10⁶", "3.64 × 10⁶ m⁻¹ (Wo = 0.18 unchanged)", "3.64 × 10⁶"],
  ["4, 7", "Taylor–Aries dispersion", "name is Taylor–Aris", "Taylor–Aris"],
  ["4", "steady Schlichting streaming ≈ 60 µm/s est.", "3u_t²/(4c_f) = 47 µm/s (C20)", "'≈ 50 µm/s (est.)'"],
  ["4", "D_osc = 7.7 × 10⁻⁹ ≈ D_H₂", "0.80 × D_H₂ (9.6 × 10⁻⁹)", "'≈ 0.8 D_H₂' (or 'same order as D_H₂')"],
  ["3", "comb bottom in 2 min (562 nm bubble-free)", "281.5 × 2 = 563 nm", "563 nm"],
], [700, 2900, 2900, 2860]));
add(P("All other hand-calculable numbers on the slides agree with this document to the digits shown.", { spacing: { before: 160 } }));

// ---------- build ----------
const numCfg = [{ reference: "bul", levels: [
  { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 260 } } } },
] }];
const doc = new Document({
  creator: "Project 1", title: "Hand calculations behind the slides",
  styles: {
    default: { document: { run: { font: FONT, size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, font: FONT, color: "1F3864" }, paragraph: { spacing: { before: 200, after: 140 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: FONT, color: "2E5597" }, paragraph: { spacing: { before: 240, after: 80 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: numCfg },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "Project 1: hand calculations behind the slides   |   page ", size: 16, color: "888888" }),
        new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "888888" })] })] }) },
    children: C,
  }],
});
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  console.log("wrote", OUT, buf.length, "bytes,", calcNo, "calculations");
});

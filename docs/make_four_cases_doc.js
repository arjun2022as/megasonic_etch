// Four-case comparison document (all with bubbles): no megasonics, horizontal 15 deg, real 90 deg MegPie, process levers.
// Run:  NODE_PATH=E:/claude_tools/node_modules node docs/make_four_cases_doc.js [out.docx]
// Figures: docs/make_four_cases_figs.py and make_explainer_figs.py (E:/claude_tools/docfigs_out) and results_1d/.
// Italic markup is ~~text~~ (underscores are left alone so names like u_t and c_sat print correctly).
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, HeadingLevel, AlignmentType, WidthType,
  ShadingType, LevelFormat, BorderStyle, Footer, PageNumber, ImageRun, PageBreak, TableOfContents,
} = require("docx");

const NEW = "E:/claude_tools/docfigs_out";
const FL = "E:/claude_tools/docfigs_in/results";
const ONE = path.join(__dirname, "..", "results_1d");
const OUT = process.argv[2] || "C:/Users/paisr/Downloads/Project 1 - Four cases with bubbles (megasonics vs levers).docx";
const CW = 9360; // content width, DXA (US Letter, 1 inch margins)
const FONT = "Calibri";

// ---------- helpers ----------
function runs(text, extra = {}) {
  // **bold** and _italic_ markup
  const out = [];
  text.split(/(\*\*[^*]+\*\*|~~[^~]+~~)/).forEach((s) => {
    if (!s) return;
    if (s.startsWith("**")) out.push(new TextRun({ text: s.slice(2, -2), bold: true, ...extra }));
    else if (s.startsWith("~~") && s.endsWith("~~") && s.length > 4) out.push(new TextRun({ text: s.slice(2, -2), italics: true, ...extra }));
    else out.push(new TextRun({ text: s, ...extra }));
  });
  return out;
}
const P = (t, o = {}) => new Paragraph({ children: runs(t), spacing: { after: 120, line: 276 }, ...o });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)], pageBreakBefore: true });
const H1n = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)] });
const B = (t, lvl = 0) => new Paragraph({ numbering: { reference: "bul", level: lvl }, children: runs(t), spacing: { after: 60 } });
let numRef = 0;
function steps(items) {
  const ref = "num" + numRef++;
  numCfg.push({ reference: ref, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 360, hanging: 360 } } } }] });
  return items.map((t) => new Paragraph({ numbering: { reference: ref, level: 0 }, children: runs(t), spacing: { after: 60 } }));
}
const EQ = (t, note) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 60, after: 120 },
  children: [new TextRun({ text: t, font: "Cambria Math", size: 23 }),
    ...(note ? [new TextRun({ text: "      " + note, size: 18, color: "555555" })] : [])],
});
const border = { style: BorderStyle.SINGLE, size: 4, color: "BBBBBB" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(rows, widths, head = true) {
  const tot = widths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: tot, type: WidthType.DXA }, columnWidths: widths,
    rows: rows.map((r, i) => new TableRow({
      tableHeader: head && i === 0,
      children: r.map((c, j) => new TableCell({
        borders, width: { size: widths[j], type: WidthType.DXA },
        shading: head && i === 0 ? { fill: "DCE6F1", type: ShadingType.CLEAR, color: "auto" } : undefined,
        margins: { top: 50, bottom: 50, left: 90, right: 90 },
        children: [new Paragraph({ children: runs(String(c), { size: 19, bold: head && i === 0 ? true : undefined }) })],
      })),
    })),
  });
}
function box(title, lines, fill = "FFF6E0") {
  const kids = [new Paragraph({ children: [new TextRun({ text: title, bold: true, color: "7A4B00" })], spacing: { after: 80 } })];
  lines.forEach((l) => kids.push(typeof l === "string"
    ? new Paragraph({ numbering: { reference: "bul", level: 0 }, children: runs(l, { size: 20 }), spacing: { after: 50 } })
    : l));
  return new Table({
    width: { size: CW, type: WidthType.DXA }, columnWidths: [CW],
    rows: [new TableRow({ children: [new TableCell({
      borders: { top: { style: BorderStyle.SINGLE, size: 8, color: "E0A030" }, bottom: border, left: border, right: border },
      width: { size: CW, type: WidthType.DXA }, shading: { fill, type: ShadingType.CLEAR, color: "auto" },
      margins: { top: 100, bottom: 100, left: 160, right: 160 }, children: kids,
    })] })],
  });
}
const gap = () => new Paragraph({ children: [], spacing: { after: 60 } });
function pngSize(f) {
  const b = fs.readFileSync(f);
  return [b.readUInt32BE(16), b.readUInt32BE(20)];
}
let figNo = 0;
const figs = [];
function fig(file, widthIn, caption) {
  if (!fs.existsSync(file)) throw new Error("missing figure " + file);
  const [w, h] = pngSize(file);
  const px = Math.round(widthIn * 96);
  figNo += 1;
  figs.push([figNo, file]);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 },
      children: [new ImageRun({ type: "png", data: fs.readFileSync(file), transformation: { width: px, height: Math.round(px * h / w) },
        altText: { title: "Figure " + figNo, description: caption.slice(0, 120), name: "fig" + figNo } })] }),
    new Paragraph({ spacing: { after: 200 }, children: [new TextRun({ text: `Figure ${figNo}. `, bold: true, size: 19 }), ...runs(caption, { size: 19 })] }),
  ];
}
const STREAM = "Imposed oscillating flow + modelled mixing, not a full acoustic-streaming solution.";
const numCfg = [{ reference: "bul", levels: [
  { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 260 } } } },
  { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 260 } } } },
] }];

// ---------- content ----------
const C = [];
const NEWF = NEW; // E:/claude_tools/docfigs_out
const CHECK = "✓";

// Title block
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 480, after: 120 },
  children: [new TextRun({ text: "Megasonics and hydrogen bubbles in a TMAH-etched 3D NAND slit", bold: true, size: 38 })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
  children: [new TextRun({ text: "Four cases compared, every one with bubbles present: no megasonics, horizontal (angled) megasonics, the real 90° MegPie, and the process levers", size: 25, color: "444444" })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 320 },
  children: [new TextRun({ text: "Project 1: megasonic-assisted TMAH wet etching of poly-Si in high-aspect-ratio slits  |  University of Arizona  |  10 November 2026", size: 20, color: "666666" })] }));

C.push(box("The comparison in six sentences", [
  "Etching poly-Si in TMAH makes two H₂ molecules per silicon atom. In a 100 nm × 10 µm slit the dissolved H₂ reaches about 63× saturation at the mouth and about 121× at the floor, far above the 13.9× a slit-wide gas plug needs, so bubbles are expected and every case here includes them.",
  "Case 1 (no megasonics): a plug forms, grows at 145–183 µm/s, vents at the mouth and reforms about every 49 ms. On flat walls the bottom etches only 3 nm/min. On comb walls it recovers after a start-up delay: 312 nm of bottom recess in 2 minutes against 562 nm bubble-free.",
  "Case 2 (horizontal sound, 15°): the sideways shaking mixes the liquid film above the wafer, the mouth falls to 43× and the plug grows 19–26 % slower. With seeds present this lengthens the cycle and the comb bottom recesses less (253 nm). It helps only when seeds are few (bottom 28.8 → 54.5 nm/min).",
  "Case 3 (the real flat MegPie, 90°): identical to no sound in all 18 Fluent plug runs and in the bubble cycle, to two decimals.",
  "Case 4 (process levers): spin speed, temperature and TMAH concentration move the H₂ far more than any sound setting. With few seeds, 1000 rpm or 25 wt % keeps the slit bubble-free at nearly full rate. With seeds, only a cooler, fast-spinning first step works: a 30 s bubble-free pre-recess raises bottom/top from 0.46 to 0.87.",
  "Why the vertical component does nothing: at the wafer it is a pressure, not a motion. The Si wafer reflects 86 % of the wave, so the liquid at the wafer barely moves (velocity node), nothing slides along the surface, the 10 µm slit is squeezed in phase by only ~2 nm, and the plug level 13.9× is fixed by the slit width. Chapter 7 goes through this link by link.",
], "EAF3FB"));
C.push(gap());
C.push(P("**How to read this document.** Chapter 1 sets out the slit and the four cases. Chapter 2 builds the model **from scratch**: every formula and principle the four cases rest on, numbered F1, F2, … with its source. Chapters 3–6 take one case each, in the same order: ~~which principles it adds, what it is, why it matters, how it is simulated, the results, and the inference~~. Chapter 7 compares the four cases and explains why only the vertical component has no effect on the etch rate or the uniformity."));
C.push(P("**Two standing caveats.** (1) Wherever sound appears: " + STREAM + " (2) Values marked ASSUMED are model inputs not yet measured for our chemistry. The ones that matter most are the H₂ solubility, the surface tension, the reference etch rate, and the H₂ level at which bubbles first appear (the seed question)."));

C.push(H2("The four cases at a glance"));
C.push(table([
  ["Case", "What changes", "Model", "One-line answer (with bubbles)"],
  ["1  No megasonics", "Nothing: the reference bubble cycle", "Fluent fixed plugs (B0) + 1D cycle", "Plug cycle every ~49 ms; flat bottom 3 nm/min; comb bottom 312 nm in 2 min"],
  ["2  Horizontal megasonics (15°)", "Sideways shaking of the film above the wafer", "Fluent plugs with imposed oscillating flow (BA_t15) + 1D cycle", "Mouth 63 → 43×, plug 19–26 % slower; comb bottom worse (253 nm); few seeds 54.5 nm/min"],
  ["3  Vertical megasonics, real MegPie (90°)", "Normal-incidence sound, 33 of every 200 ms", "Fluent plugs (B_f1_I2) + 1D cycle + case 7 estimates", "Same as no sound in every quantity"],
  ["4  Process levers", "Spin speed, temperature, TMAH concentration", "1D window map + 1D cycle", "1000 rpm or 25 wt % bubble-free if seeds are few; two-step recipe 0.46 → 0.87 with seeds"],
], [1900, 2300, 2300, 2860]));
C.push(P("Case names in the Fluent files: **B0** = gas plug, no sound; **BA_f1_I2_t15** = plug + sound at 1 MHz, 2 W/cm², 15°; **B_f1_I2** = plug + sound at 90°; **_floor** = plug on the floor; **_l3000 / _l6000** = plug 3 / 6 µm long (default 1 µm); **_r300** = comb walls with the poly-Si recessed 300 nm. In the original case numbering of the project these four cases draw on cases 2, 4, 6, 7 and 8.", { spacing: { before: 120 } }));

// ---------- 1. System ----------
C.push(H1("1. The system and the four cases"));
C.push(P("A 3D NAND stack is a pile of alternating SiO₂ and poly-Si layers, each 50 nm thick. A slit is cut through it: **W = 100 nm wide, L = 10 µm deep**, aspect ratio 100. Hot TMAH fills the slit and etches the poly-Si layers sideways while leaving the oxide. On the single-wafer tool the wafer spins under a thin liquid layer, and a flat MegPie transducer sends megasonic sound into the liquid over a 60° sector of the wafer."));
C.push(...fig(`${NEWF}/fig_geometry.png`, 6.3, "The slit as modelled. (a) Flat walls: walls beside a gas plug are dry and do not etch. (b) Comb walls: the poly-Si has recessed into 50 nm tall pockets; pockets beside a plug stay full of liquid and keep etching on the etchant stored in them. Sketch, not to scale."));
C.push(table([
  ["Condition", "Value", "Status"],
  ["Etchant", "5 wt % TMAH, 60 °C", "ASSUMED process point"],
  ["Reference poly-Si etch rate ER_ref", "300 nm/min in fresh etchant", "ASSUMED (to calibrate by SEM)"],
  ["Spin speed", "300 rpm (Ω = 31.4 rad/s); probe radius 50 mm", "ASSUMED"],
  ["Sound", "1 MHz, 2 W/cm²; MegPie gap 2 mm; 60° sector, so a spot is under the head 33 of every 200 ms", "gap and sector ASSUMED"],
  ["Slit pitch", "1 µm between slits", "ASSUMED"],
  ["H₂ saturation c_sat", "0.70 mM at 1 atm (water at 60 °C)", "ASSUMED for TMAH"],
  ["Surface tension γ, vapour pressure p_vap", "0.0662 N/m, 19.9 kPa (water at 60 °C)", "ASSUMED for TMAH"],
  ["Bubble start (nucleation) level s_nuc", "13.9× (seeds present) or ~100× (few seeds)", "Unknown: run as two scenarios"],
], [3000, 4160, 2200]));
C.push(P("**What we judge each case by.** (1) The **etch rate** at the top and bottom of the slit. (2) The **uniformity**, bottom etch rate ÷ top etch rate (1 = perfect). (3) Because bubbles are present: how fast the plug grows, how long one bubble cycle lasts, the time-averaged bottom etch, and the bottom recess after a 2-minute etch.", { spacing: { before: 160 } }));

// ---------- 2. Foundation ----------
C.push(H1("2. The foundation, from scratch: formulas and principles shared by all four cases"));
C.push(P("This chapter builds the model one step at a time, from the chemistry to the bubble cycle. Each formula is numbered (F1, F2, …) and tagged with where it comes from: **T** = textbook or literature law used as is; **D** = definition or unit conversion; **F** = formed for this project by combining laws or by a mass balance. Cases 1–4 all stand on F1–F23; the sound cases add F24–F37 (chapters 4 and 5) and the lever case adds F38–F42 (chapter 6)."));

C.push(H2("2.1 Chemistry and etch rate"));
C.push(EQ("F1   Si + 2 OH⁻ + 2 H₂O → SiO₂(OH)₂²⁻ + 2 H₂", "T  Seidel et al. 1990 (KOH; taken as the same for TMAH)"));
C.push(P("Every Si atom removed uses **two OH⁻** and releases **one silicate ion and two H₂**. All source terms below follow from this counting."));
C.push(EQ("F2   C = w·ρ / M = 0.05 × 990 / 0.09115 = 543 mM", "D  molarity; TMAH fully dissociated, so OH⁻ = TMA⁺ = C"));
C.push(EQ("F3   r = K · (c_OH / C)^¼", "T  Seidel rate law, rate ∝ [H₂O]⁴[OH⁻]^¼; K set by ER_ref = 300 nm/min (ASSUMED)"));
C.push(P("At 5 wt % the water term is almost constant, so only the OH⁻ part is kept. The ¼ power makes the rate only weakly sensitive to OH⁻ depletion, which is why a bubble-free slit is nearly uniform (0.958)."));
C.push(EQ("F4   ER = r · M_Si / ρ_Si", "D  mol/m²/s → m/s of wall recession (M_Si = 0.0281 kg/mol, ρ_Si = 2330 kg/m³)"));

C.push(H2("2.2 Transport inside the slit"));
C.push(P("Inside the slit the liquid is still (Fluent: below 10⁻⁹ m/s), so everything moves by diffusion, and the ions also drift in a small electric field."));
C.push(EQ("F5   N_i = −D_i ∇c_i + z_i D_i c_i (F/RT)(−∇φ)", "T  Nernst–Planck (Newman, Electrochemical Systems)"));
C.push(EQ("F6   −(F/RT)∇φ = S/Q,   S = Σ z_j D_j ∇c_j,   Q = Σ z_j² D_j c_j", "F  from F5 with zero net current, Σ z_i N_i = 0"));
C.push(EQ("F7   c_TMA = c_OH + 2 c_SIL", "T  electroneutrality; the 2 is silicate's −2 charge"));
C.push(EQ("F8   H₂ (neutral, z = 0):   N = −D_H₂ ∇c,   ∂c/∂t = D_H₂ ∇²c", "T  Fick's laws"));
C.push(EQ("F9   D_ion = RTλ/(z²F²);   D(T) = D₂₅ (T/298)(μ₂₅/μ_T);   D_H₂(60 °C) = 9.59×10⁻⁹ m²/s", "T  Nernst–Einstein, Stokes–Einstein; D_H₂ from Cussler"));
C.push(P("Fluent solves F5–F8 in 2D with the wall reaction as a boundary source on the poly-Si faces (a compiled UDF). The 1D model averages over the 100 nm width, which is valid because crossing the width takes ~10⁻⁶ s against ~10⁻² s for the depth."));

C.push(H2("2.3 The liquid film on the spinning wafer: the mouth values"));
C.push(P("Every slit on the wafer releases H₂ into the same liquid film, and the film carries it away. A spinning wafer behaves like a rotating disk, whose diffusion layer has the same thickness everywhere:"));
C.push(EQ("F10   k_m = 0.620 · D^(2/3) · ν^(−1/6) · Ω^(1/2) = 1.78×10⁻⁴ m/s  (H₂, 300 rpm)", "T  Levich 1962, rotating disk"));
C.push(EQ("F11   J = N_slit · W / pitch,     c_mouth = c_bulk + J / k_m", "F  one slit's output spread over one pitch; film resistance in series"));
C.push(P("With J ≈ 7.9×10⁻³ mol/m²/s this gives **c_mouth = 44.4 mM = 63×** saturation for H₂, and OH⁻ 503 mM, silicate 64 mM. These are the boundary values at the top of the Fluent box. The film's diffusion (Nernst) layer is δ_N = D/k_m = 54 µm thick and needs δ_N²/D = 0.30 s to forget a disturbance; this memory matters for the MegPie in chapter 5."));

C.push(H2("2.4 How the H₂ builds up inside the slit"));
C.push(EQ("F12   q = 2r · 2f_poly / W ≈ 8,100 mol/m³/s", "F  2 H₂ per Si, 2 walls, f_poly = 0.5, spread over the width"));
C.push(EQ("F13   c(z) = c_mouth + (q/D)(Lz − z²/2),   c_floor = c_mouth + qL²/(2D)", "F  solving D c'' = −q with c(0) = c_mouth, c'(L) = 0"));
C.push(P("A uniformly fed dead-end channel gives a parabola, highest at the closed floor. The in-slit rise is qL²/(2D) = 42.2 mM = **+60×**, so the floor reaches **122×** (1D model 121–122×, hand formula 124×, Fluent 131× because its mouth sits under a 1 µm liquid box). This is a hand check; the models compute the same profile directly. The important point for this document: **the H₂ has two halves.** The mouth half (63×) is set by the film, so spin and sound can reach it. The in-slit half (+59–60× ≈ rL²/(WD)) is set by the etch rate and the slit depth, and nothing above the mouth can reach it."));

C.push(H2("2.5 Henry's law and the Laplace pressure: how much H₂ a bubble needs"));
C.push(EQ("F14   c = p_H₂ / K_H,   c_sat = 0.70 mM at 1 atm,   S = c / c_sat", "T  Henry's law (water value, ASSUMED); D saturation ratio"));
C.push(EQ("F15   Δp = 2γ/r (sphere),   Δp = γ/R (cylinder)", "T  Young–Laplace"));
C.push(EQ("F16   S_eq(r) = 1 + (2γ/r − p_vap) / p_atm,     r* = 2γ / ((S − 1)p_atm + p_vap)", "F  F14 + F15 + Dalton (the gas also holds water vapour)"));
C.push(P("Liquid above S_eq feeds the bubble and it grows; liquid below starves it and it shrinks. Smaller bubbles need more H₂, so the levels that matter in this slit are:"));
C.push(table([
  ["Gas shape", "Curvature term", "H₂ needed", "Meaning"],
  ["Slit-wide plug (ends curved across W only)", "2γ/W = 1.32 MPa", "13.9× (9.7 mM)", "The lowest level any bubble needs in this slit"],
  ["Round seed touching both walls, r = 50 nm", "2γ/r = 2.65 MPa", "27×", "Largest round seed that fits"],
  ["Small seed, r ≈ 13 nm", "≈ 10 MPa", "≈ 100× (98.6×)", "The 'few seeds' scenario"],
  ["Seed of 10 nm", "13.2 MPa", "131×", "Only the floor of a bubble-free slit is this high"],
], [3000, 1900, 1600, 2860]));
C.push(...fig(`${NEWF}/fig_henry_laplace.png`, 5.6, "Henry + Laplace: the H₂ saturation a bubble needs against its radius (blue). The shaded band is the H₂ actually present in a bubble-free slit (63–131×). Once a seed spans the slit it needs only the plug level, 13.9× (red). γ, p_vap, c_sat ASSUMED (water at 60 °C)."));
C.push(P("**Seeds.** A bubble cannot start from nothing at these levels; it grows from a gas pocket already present (trapped air from wetting, a crevice, a pocket edge). Which seeds exist is the single biggest unknown, so every result below is given for two scenarios: **seeds present** (bubbles start at 13.9×) and **few seeds** (bubbles start at about 100×)."));

C.push(H2("2.6 The plug: gas pressure, intake and growth"));
C.push(EQ("F17   p_gas = p_atm + 2γ/W − p_vap = 0.101 + 1.324 − 0.020 = 1.41 MPa,   c* = 9.7 mM = 13.9×", "F  F15 for a half-cylinder end of radius W/2, plus Henry"));
C.push(EQ("F18   ρ_g = p_gas / RT = 507 mol/m³", "T  ideal gas at 60 °C"));
C.push(EQ("F19   db/dt = N_H₂ / (ρ_g · W)", "F  mass balance on the plug: H₂ in ÷ gas density = new gas volume"));
C.push(EQ("F20   Fluent plug surface: source −D_H₂ (c − c*)·|A| / (d·V);  OH⁻, silicate: no flux;  poly-Si beside the gas: dry", "F  my discretisation in the UDF"));
C.push(P("The plug surface pins the liquid next to it at 13.9×, so the plug is an H₂ sink: H₂ diffuses into it from the walls and from the mouth. Fluent holds the plug at a fixed length (1, 3 or 6 µm on the floor) and reports N_H₂; F19 turns that into a growth speed. Example: N_H₂ = 7.25×10⁻⁹ mol/s per metre of trench gives 7.25×10⁻⁹ / (507 × 10⁻⁷) = 143 µm/s. **The plug level 13.9× is set by γ and W alone: no sound or process setting in this study changes it.**"));
C.push(EQ("F21   Pocket entry needs 2γ / (50 nm) = 2.6 MPa > 1.41 MPa", "F  from F15: gas cannot enter a 50 nm comb pocket, so pockets beside a plug stay wet"));

C.push(H2("2.7 The bubble cycle and the comb pockets"));
C.push(EQ("F22   ∂c/∂t = D c'' + q above the plug;  c = c* at the plug top b(t);  b grows by F19;  vent at the mouth;  instant refill with mouth liquid", "F  1D moving-plug model (etchsim/plug.py); refill ASSUMED instant"));
C.push(EQ("F23   Sealed pocket of depth R:  dc/dt = −2r(c)/R  ⇒  c^(3/4) = c₀^(3/4) − (3/4)·2Kt / (R C^(1/4));   dR_bottom/dt = ER_bottom(R)", "F  OH⁻ balance, integrated exactly (checked with RK4); start-up integration"));
C.push(P("The cycle is: build-up → a seed starts to grow → it spans the slit and becomes a plug → the plug drinks H₂ and grows → it reaches the mouth and vents → fresh mouth liquid refills the slit → repeat. Fluent cannot move a gas plug cheaply, so the cycle runs in 1D; the 1D plug intake matches Fluent within 0.3–1.5 % on flat walls and 1–5 % on comb walls. On comb walls the pockets beside a plug keep etching on stored OH⁻ until it runs out (about 8 ms for a 10 nm pocket, 247 ms for 300 nm), and each refill tops them up. So when pockets are shallow, **the bottom etch depends on how often the slit refills**, i.e. on the cycle time. This turns out to decide case 2."));
C.push(...fig(`${ONE}/cycle_map.png`, 6.4, "The bubble cycle in 1D (flat walls, no sound): H₂ saturation against depth and time after a refill. Left: no bubbles ever. Middle: bubbles start at 100× (few seeds). Right: bubbles start at 13.9× (seeds). White = gas plug. c_sat and the bubble-start levels ASSUMED."));

// ---------- 3. Case 1 ----------
C.push(H1("3. Case 1: no megasonics, with bubbles"));
C.push(box("Principles used", [
  "F1–F23 only. Nothing is added: this is the reference every other case is measured against.",
  "Mouth values from the Levich film at 300 rpm (F10–F11): H₂ 63×, OH⁻ 503 mM, silicate 64 mM.",
  "Plug surface at 13.9× (F17, F20); growth from F19; cycle and pockets from F22–F23.",
]));
C.push(gap());
C.push(P("**What it is.** The slit at the standard process point with no sound, a gas plug present, and the bubble cycle running. **Why it matters.** It is what actually happens on the tool if bubbles form, and it sets the bar sound has to beat. **How it is simulated.** Fluent: six fixed floor plugs (1, 3, 6 µm; flat and comb walls), runs B0_floor, B0_floor_l3000, B0_floor_l6000 and their _r300 versions. 1D: the growing-plug cycle (F22) on flat and comb walls, then the 2-minute start-up (F23)."));
C.push(H2("Results"));
C.push(table([
  ["Plug (Fluent)", "Growth (µm/s)", "Mouth H₂", "Plug top", "Wet-part bottom/top"],
  ["Flat, 1 µm", "143 (from the 90° twin run*)", "63.3×", "13.9×", "0.96496"],
  ["Flat, 3 µm", "145.2", "61.4×", "13.9×", "0.97821"],
  ["Flat, 6 µm", "175.0", "56.9×", "13.9×", "0.99272"],
  ["Comb 300 nm, 1 µm", "147.7", "63.0×", "13.9×", "0.96715"],
  ["Comb 300 nm, 3 µm", "151.0", "61.1×", "13.9×", "0.97960"],
  ["Comb 300 nm, 6 µm", "183.4", "56.5×", "13.9×", "0.99319"],
], [2300, 2300, 1500, 1300, 1960]));
C.push(P("*B0_floor ran before the solver printed the growth line; the 90° run of the same plug (143.0 µm/s) stands in, because 90° equals no sound within 0.7 % in every other group. The wet-part bottom/top covers only the liquid above the plug and is not comparable with the bubble-free 0.958.", { spacing: { before: 80 } }));
C.push(B("**Cycle:** a plug every **48.6 ms** on flat walls (37.3 ms on 300 nm comb walls, where pocket H₂ also feeds the plug), about 2,500 cycles in a 2-minute etch."));
C.push(B("**Flat walls:** time-averaged bottom etch **2.98 nm/min with seeds**, 28.7 nm/min with few seeds, against 281.5 nm/min with no bubbles at all. The top is barely affected (293.5 nm/min)."));
C.push(B("**Comb walls, seeds present** (bottom etch against the recess already there): 2.98 / 43.7 / 90.1 / 232.0 / 269.1 / 286.3 nm/min at R = 0 / 10 / 20 / 50 / 100 / 300 nm (about 3 + 4.4·R nm/min for small R: the bottom bootstraps itself)."));
C.push(B("**2-minute etch from flat walls:** bottom recess 41.8 nm after 1 min, **311.7 nm after 2 min**; top 588 nm; bubble-free bottom 562 nm. Starting from 5 nm of recess left by the dry etch: 462 nm."));
C.push(P("**Inference.** Bubbles, not transport, decide the bottom. On flat walls the plug almost stops the bottom; on comb walls the pockets rescue it once they are a few tens of nm deep, which gives a start-up delay of about a minute.", { spacing: { before: 120 } }));

// ---------- 4. Case 2 ----------
C.push(H1("4. Case 2: horizontal (angled) megasonics, 15°, with bubbles"));
C.push(box("Principles added to F1–F23", [
  "F24 plane wave: p₀ = √(2ρcI) = 0.247 MPa, U₀ = p₀/(ρc) = 0.16 m/s at 2 W/cm².",
  "F25 reflection from the Si wafer (Brekhovskikh, elastic half-space + Snell's law): R(θ).",
  "F26 liquid motion at the wafer: sideways u_t = U₀ sin β |1+R|, up-down u_n = U₀ cos β |1−R|, pressure p_wall = p₀|1+R|, with β = 90° − θ.",
  "F27 Stokes layer δ = √(2ν/ω) = 0.39 µm; F28 imposed oscillating flow; F29 mixing D_osc = |u₁|²/(2ω); F30 decay into the slit e^(−4.21 z/W).",
  "F31 mouth with sound: Levich (F10) with D → D + D_osc. Plus plug pumping, rectified diffusion and early venting (small).",
]));
C.push(gap());
C.push(H2("The formulas, from scratch"));
C.push(EQ("F24   I = p₀² / (2ρc)  ⇒  p₀ = √(2ρcI),   U₀ = p₀ / (ρc)", "T  plane-wave acoustics"));
C.push(EQ("F25   R(θ) = (Z_s − Z_f) / (Z_s + Z_f),  Z_f = ρc / cos β,  Z_s from the P and S waves in Si", "T  Brekhovskikh, fluid on an elastic solid; Snell's law for the refracted angles"));
C.push(EQ("F26   u_t = U₀ sin β |1+R|,   u_n = U₀ cos β |1−R|,   p_wall = p₀ |1+R|", "F  incident + reflected wave at the wafer surface"));
C.push(EQ("F27   δ = √(2ν/ω) = 0.39 µm  (1 MHz)", "T  Stokes' second problem"));
C.push(EQ("F28   u(y,t) = G·y + u_t [cos ωt − e^(−y/δ) cos(ωt − y/δ)],   G = Ωr/gap = 785 s⁻¹", "T  oscillating boundary layer + F spin shear; imposed in Fluent"));
C.push(EQ("F29   D_osc = |u₁|² / (2ω)   (UDF: (var u + var v)/ω)", "F  Taylor–Aris oscillatory dispersion, upper bound, same for every species"));
C.push(EQ("F30   u(z) ∝ e^(−4.21 z/W)  inside the slit", "T  slowest Stokes channel mode (Moffatt / Papkovich–Fadle): 98 % lost in the first 100 nm"));
C.push(EQ("F31   k_m,sound = Levich with D → D + D_osc", "F  sound adds mixing to the film only"));
C.push(P("**Why 15° stands for 'horizontal'.** Sound can only help the film through the sideways motion u_t. It is 0 at 90°, rises as the beam tilts, peaks near 10° (0.314 m/s) and is 0.311 m/s at 15°, within 1 % of the best; at exactly 0° (grazing) it falls back to 0 (Figure 4a). So the existing 15° runs are the horizontal case. A meniscus-coupled MegPie cannot really tilt this far, so this case is a what-if."));
C.push(...fig(`${NEWF}/four_components.png`, 6.5, "What the wafer feels. (a) Liquid speed along the wafer (u_t), across it (u_n) and pressure at the wafer against incidence angle (1 MHz, 2 W/cm²). The spike near 72–75° is the shear-wave critical angle of Si. (b) Vertical sound: the wafer is a velocity node and a pressure antinode. (c) Horizontal sound: sideways slip in a 0.39 µm Stokes layer. " + STREAM));
C.push(H2("What it is, and how it is simulated"));
C.push(P("**What it is.** The case-1 slit and plugs, with 1 MHz, 2 W/cm² sound arriving at 15°, applied continuously. **Why it matters.** The proposal asks whether angled sound drives liquid into high-aspect-ratio structures better than normal incidence. **How it is simulated.** Fluent: phase A imposes the oscillating flow F28 on the liquid box above the slit (time step 1/(40 f) = 25 ns; 8 settling + 10 averaged cycles) and records D_osc (F29); phase B runs the etch with D + D_osc and the plug boundary F20; mouth values from F31. Runs BA_f1_I2_t15_floor, _l3000, _l6000 and their _r300 versions. 1D: the case-1 cycle with the 15° mouth values, plug pumping, rectified diffusion and early venting."));
C.push(H2("Results"));
C.push(table([
  ["Plug (Fluent)", "Growth: no sound → 15° (µm/s)", "Change", "Mouth H₂: no sound → 15°", "Wet-part bottom/top"],
  ["Flat, 1 µm", "143.0 → 115.3", "−19 %", "63.3 → 43.3×", "0.96496 → 0.96588"],
  ["Flat, 3 µm", "145.2 → 111.2", "−23 %", "61.4 → 43.0×", "0.97821 → 0.97886"],
  ["Flat, 6 µm", "175.0 → 129.4", "−26 %", "56.9 → 42.5×", "0.99272 → 0.99332"],
  ["Comb, 1 µm", "147.7 → 118.3", "−20 %", "63.0 → 43.2×", "0.96715 → 0.96805"],
  ["Comb, 3 µm", "151.0 → 115.2", "−24 %", "61.1 → 43.0×", "0.97960 → 0.98018"],
  ["Comb, 6 µm", "183.4 → 136.7", "−25 %", "56.5 → 42.4×", "0.99319 → 0.99371"],
], [1700, 2400, 1100, 2200, 1960]));
C.push(B("**Fluent:** the film is mixed, the mouth falls to 42–43×, less H₂ reaches the plug, so it grows **19–26 % slower**. The plug top stays at 13.9× in every run, so the plug never stops. The top etches about 2.5 nm/min faster (295.3–295.8 against 292.7–293.7 nm/min); the wet-part bottom/top improves by under 0.001."));
C.push(B("**1D cycle, flat walls:** the cycle lengthens from 48.6 to **68.1 ms**; bottom 3.84 nm/min with seeds, **54.5 nm/min with few seeds** (28.7 without sound)."));
C.push(B("**1D cycle, comb walls, seeds:** bottom etch 3.84 / 33.6 / 68.4 / 189.3 / 262.7 / 285.5 nm/min at R = 0 / 10 / 20 / 50 / 100 / 300 nm, **lower than no sound at every recess between 10 and 100 nm**."));
C.push(B("**2-minute etch from flat walls:** bottom recess **253.3 nm against 311.7 nm with no sound (19 % worse)**; top 591 nm."));
C.push(...fig(`${ONE}/case8_fluent_maps.png`, 6.3, "Fluent, comb walls, 3 µm floor plug. Left: H₂ saturation on one colour scale for no sound, vertical 90° and horizontal 15°. Right: change from no sound: blank for vertical; horizontal lowers the H₂ by 15–18× at the mouth, fading to 0 at the plug top (13.9×). " + STREAM));
C.push(P("**Inference: horizontal sound cuts both ways.** It lowers the H₂ above the plug, so a new bubble takes longer to start after a refill; that helps when seeds are few. But it also slows a plug that already exists, so the cycle lasts longer and the slit refills less often. Shallow pockets beside the plug run dry within milliseconds and etch mainly just after each refill, so with seeds the bottom etches less. Only when the pockets are deep (≈300 nm) do the two conditions meet again (285.5 vs 286.3 nm/min).", { spacing: { before: 120 } }));

// ---------- 5. Case 3 ----------
C.push(H1("5. Case 3: vertical megasonics, the real 90° MegPie, with bubbles"));
C.push(box("Principles added to F1–F31", [
  "The same wave formulas F24–F26 at θ = 90° (β = 0): u_t = 0 exactly; u_n = U₀|1−R| = 0.023 m/s; p_wall = p₀|1+R| = 0.458 MPa (R = 0.856).",
  "F32 slit breathing (compression of the liquid column); F33 plug and seed pulsation, rectified diffusion, early venting; F34 MegPie duty (33 of every 200 ms).",
  "F35–F37 the normal-incidence mechanisms above the wafer: Eckart streaming, beam-edge sloshing, bubbles in the gap; the film solved through each revolution.",
]));
C.push(gap());
C.push(H2("The formulas, from scratch"));
C.push(EQ("F32   ξ = L · p_wall / (ρc²) = 10⁻⁵ × 0.458×10⁶ / (983 × 1555²) ≈ 1.9 nm", "F  compressing a 10 µm liquid column; the wavelength c/f = 1.5 mm ≫ L"));
C.push(EQ("F33   ε = p_a / (3 p_g);   rectified diffusion: c* → c* / √(1 − ε²);   vent early if the meniscus swing reaches the mouth", "T  linear bubble pulsation + F plug-in-a-slit form"));
C.push(EQ("F34   duty = 60°/360° = 1/6:  sound on 33 ms of every 200 ms at 300 rpm", "F  geometry of the MegPie sector (ASSUMED)"));
C.push(EQ("F35   Eckart force F = 2αI/c,  α = 10.5×10⁻¹⁵ f² (ASSUMED);  edge wall shear G = F′h²/(12μ)", "T  Eckart streaming + F lubrication in the 2 mm gap"));
C.push(EQ("F36   Any wall flow u_z = −C z²:  k = D^(2/3) C^(1/3) / (3^(1/3) Γ(4/3));  rotating disk C = 0.51023 Ω^1.5 ν^(−0.5) → 0.620", "T  Lévêque, high Schmidt number; reproduces Levich"));
C.push(EQ("F37   Gap bubbles: Minnaert R_res = 2.93 µm (1 MHz);  H₂ sink k_sink = n · 4πRD;  film: 1D diffusion through δ_N = 54 µm over each 200 ms turn", "T  Minnaert + F film model (etchsim/normal.py)"));
C.push(H2("What it is, and how it is simulated"));
C.push(P("**What it is.** The real tool: a flat MegPie sends sound straight down, 1 MHz, 2 W/cm², and a given slit is under the head only 33 of every 200 ms. **Why it matters.** This is the condition the experiments will actually use. **How it is simulated.** Fluent: the same six plugs with the 90° oscillation imposed (runs B_f1_I2_floor, _l3000, _l6000 and _r300). 1D: the cycle with the real duty (F34), continuous 90° for comparison, pulsation, rectified diffusion and early venting (F33). Case-7 estimates for everything a flat MegPie can do above the wafer (F35–F37), each turned into a mouth renewal factor m = mouth H₂ without sound ÷ with sound."));
C.push(H2("Results"));
C.push(table([
  ["Quantity", "No sound", "Vertical 90°, real MegPie", "Vertical 90°, continuous"],
  ["Fluent plug growth, six groups (µm/s)", "143–183.4", "+0.2 to +0.7 % (e.g. 151.0 → 151.3)", "(Fluent runs are continuous)"],
  ["Fluent mouth H₂", "56.5–63.3×", "identical", "identical"],
  ["Fluent wet-part bottom/top", "0.965–0.993", "within 0.0005", "within 0.0005"],
  ["Cycle time, flat / 300 nm comb (ms)", "48.6 / 37.3", "48.6 / 37.3", "47.9 / 36.9"],
  ["Bottom etch, comb, seeds, R = 0/10/20/50/100/300 nm", "2.98 / 43.7 / 90.1 / 232.0 / 269.1 / 286.3", "identical to two decimals", "3.02 / 44.3 / 91.3 / 233.3 / 269.4 / 286.4"],
  ["Bottom recess after 2 min, comb, seeds", "311.7 nm", "311.7 nm", "316.0 nm"],
  ["Bottom etch, flat, few seeds", "28.7 nm/min", "28.85", "29.2"],
], [3100, 2100, 2200, 1960]));
C.push(P("**Mechanisms above the wafer (case 7 estimates).** Eckart streaming: u_max 24 µm/s at 1 MHz, m = 1.0007–1.0013. Beam-edge sloshing: U_e = 0.048 m/s at the beam edge only, m = 1.0006–1.0015. Seeds and plugs pulse by 1–6 % (p_a 0.46 MPa < p_g 1.41–10 MPa) and the bubble levels move by under 1 %. Gap bubbles, numbers unknown and swept:", { spacing: { before: 120 } }));
C.push(table([
  ["Scenario under the MegPie (33 of 200 ms)", "Mouth H₂ mean / worst", "Floor H₂ worst", "Bottom etch, seeds / few seeds (nm/min)"],
  ["No sound", "63.1 / 63.1×", "121×", "3.0 / 28.7"],
  ["Gap bubbles stir 15 µm", "59.7 / 62.7×", "121×", "3.1 / 30.7"],
  ["Gap bubbles take up H₂, 1000 per mm²", "50.5 / 58.4×", "117×", "3.5 / 56.8"],
  ["Perfect renewal under the head (upper bound)", "28.8 / 49.9×", "108×", "4.3 / 187"],
], [3500, 2000, 1500, 2360]));
C.push(...fig(`${ONE}/case7.png`, 6.4, "Case-7 estimates for the flat MegPie. (a) Floor H₂ for each 90° mechanism against the bubble-start levels. (b) Mouth H₂ through one 200 ms revolution; yellow = the 33 ms under the MegPie. (c) Floor H₂ and bottom etch against the mouth renewal m. Estimated streaming and bubble effects (ASSUMED numbers), not a full acoustic-streaming solution."));
C.push(P("**Inference.** The real flat MegPie changes nothing: in Fluent (all six plug groups), in the bubble cycle (to two decimals) and in every estimated 90° mechanism at realistic bubble numbers. Even perfect renewal under the head leaves the floor at 108× because the mouth refills in the 167 ms between passes, and the in-slit +59× and the plug level 13.9× are out of reach. Chapter 7 explains why this is physics rather than a limit of the model.", { spacing: { before: 120 } }));

// ---------- 6. Case 4 ----------
C.push(H1("6. Case 4: process levers (spin speed, temperature, concentration), with bubbles"));
C.push(box("Principles added to F1–F23", [
  "F38 temperature changes everything at once: Arrhenius etch rate (Ea = 0.57 eV), D and ν, γ, p_vap and c_sat (van 't Hoff, 530 K; ASSUMED for TMAH).",
  "F39 concentration enters through the full Seidel rate law, rate ∝ [H₂O]⁴[OH⁻]^¼ (ASSUMED for TMAH).",
  "F40 spin speed enters only through Levich, k_m ∝ Ω^(1/2) (F10).",
  "F41 the bubble-start level at any T and pressure; F42 the window margin and the two halves of the H₂.",
]));
C.push(gap());
C.push(H2("The formulas, from scratch"));
C.push(EQ("F38   ER(T) = ER_ref · exp[−(Ea/k_B)(1/T − 1/T_ref)];   D(T) Stokes–Einstein;  μ Vogel;  γ IAPWS;  p_vap Antoine;  c_sat(T) van 't Hoff", "T  property laws; Ea and the c_sat slope ASSUMED"));
C.push(EQ("F39   r ∝ [H₂O]⁴ [OH⁻]^¼", "T  Seidel (KOH), ASSUMED for TMAH: peaks near 7 wt %, falls at high concentration (Tabata 1992 trend)"));
C.push(EQ("F40   c_mouth = J / k_m,   k_m ∝ Ω^(1/2)   ⇒   c_mouth ∝ rpm^(−1/2)", "F  from F10–F11"));
C.push(EQ("F41   c_need = c_sat(T) · (p_amb + 2γ(T)/r_eff − p_vap(T) − p_other) / p_atm,   r_eff = W, 50 nm, 13.4 nm", "F  F16 generalised to any T and pressure"));
C.push(EQ("F42   margin = c_need / c_max  (> 1: bubble-free);    c_floor ≈ c_mouth(spin, sound) + r L² / (W D)(etch rate)", "F  window test and the two halves of the H₂"));
C.push(P("F42 is the key to this case. Spin (and sound) can only shrink the first half; only a lower etch rate (temperature, concentration) shrinks the second. A quick check of F40: going from 300 to 1000 rpm divides the mouth by √(1000/300) = 1.83, 63.1 → 34.6× (model 34.8×). A check of F38: 60 → 20 °C multiplies the etch rate by exp(−6615 × 4.10×10⁻⁴) = 0.067, 300 → 20 nm/min (model 19.9)."));
C.push(H2("What it is, and how it is simulated"));
C.push(P("**What it is.** The same slit with bubbles, but the knobs on the tool turned instead of the sound. **Why it matters.** It tells us whether anything other than megasonics can move the slit down the saturation ladder, and how far. **How it is simulated.** All 1D on the laptop (no Fluent): the steady slit model with temperature-dependent properties and Levich at each spin speed (window map, 9 temperatures × 7 spin speeds); the case-1 bubble cycle fed with the new mouth values and etch constants (spin, concentration); the comb start-up model (F23) for a two-step recipe."));
C.push(H2("Results"));
C.push(H3("Spin speed (60 °C, 5 wt %), bubbles on"));
C.push(table([
  ["Condition", "Mouth H₂", "Floor H₂ (no bubble)", "Bottom etch, seeds", "Bottom etch, few seeds"],
  ["300 rpm, no sound (today)", "63×", "121×", "3.0 nm/min", "28.7 nm/min"],
  ["300 rpm + 15° sound, continuous (case 2)", "43×", "102×", "3.8", "54.5"],
  ["600 rpm", "45×", "104×", "3.8", "49.5"],
  ["1000 rpm", "35×", "93×", "4.1", "283.6 (bubble-free)"],
  ["1500 rpm", "28×", "–", "4.3", "284.0 (bubble-free)"],
  ["3000 rpm", "20×", "79×", "5.7", "284.5 (bubble-free)"],
], [3000, 1300, 1700, 1600, 1760]));
C.push(H3("Temperature (300 rpm, 5 wt %): where bubbles can start"));
C.push(table([
  ["T (°C)", "Top etch (nm/min)", "Floor H₂ (no bubble)", "Margin: plug / 50 nm / 13 nm seed", "Bubble-free if …"],
  ["60", "293.6", "121×", "0.11 / 0.22 / 0.81", "never (even few seeds start)"],
  ["55", "217.9", "96×", "0.15 / 0.28 / 1.04", "few seeds"],
  ["50", "160.1", "76×", "0.19 / 0.37 / 1.34", "few seeds"],
  ["40", "83.7", "46×", "0.32 / 0.62 / 2.27", "few seeds"],
  ["30", "41.8", "27×", "0.56 / 1.08 / 3.95", "few seeds or 50 nm seeds"],
  ["25", "29.1", "20×", "0.75 / 1.44 / 5.26", "few or 50 nm seeds (plug seeds need 2000 rpm: margin 1.06)"],
  ["20", "19.9", "15×", "1.00 / 1.94 / 7.06", "any seeds (just)"],
], [900, 1500, 1700, 2600, 2660]));
C.push(P("Where the margin is above 1 no bubble forms even with bubbles 'allowed', so the bottom etches at the bubble-free value (bottom/top 0.958 at 60 °C rising to 0.992 at 20 °C). Where it is below 1, the plug cycle of case 1 applies. The full bubble cycle at reduced temperature was not run separately."));
C.push(H3("TMAH concentration (60 °C, 300 rpm), bubbles on"));
C.push(table([
  ["TMAH", "Etch rate (bulk)", "Bottom/top, no bubbles", "Floor H₂", "Bottom etch: seeds / few seeds"],
  ["2 wt %", "265 nm/min", "0.918", "101×", "2.9 / 42.0 nm/min"],
  ["5 wt % (today)", "300", "0.958", "121×", "3.0 / 28.7"],
  ["10 wt %", "296", "0.977", "123×", "3.0 / 29.0"],
  ["15 wt %", "269", "0.986", "113×", "2.9 / 32.3"],
  ["25 wt %", "196", "0.993", "83×", "2.6 / 194.4 (bubble-free)"],
], [1600, 1800, 2000, 1400, 2560]));
C.push(P("Caveat: TMAH probably dissolves less H₂ than water (salting-out, not yet measured). With a typical salt constant (0.05–0.1 L/mol, ASSUMED) the 25 wt % floor would be about 115–160×, which could close that window. The uniformity gain without bubbles does not depend on it."));
C.push(H3("The two-step recipe (works even with seeds)"));
C.push(P("Step 1 at 25 °C / 2000 rpm is bubble-free even with seeds (plug margin 1.06) and etches 29.1 nm/min at the top and 28.8 at the bottom, building pockets. Step 2 is the normal 60 °C / 300 rpm etch, where the pockets carry the bottom through the bubble cycle (F23)."));
C.push(table([
  ["First step at 25 °C / 2000 rpm", "0 s (single step)", "15 s", "30 s", "60 s", "120 s"],
  ["Bottom/top when the top reaches 500 nm", "0.46", "0.79", "0.87", "0.93", "0.96"],
  ["Total etch time", "102 s", "116 s", "129 s", "156 s", "210 s"],
  ["Bottom/top when the top reaches 300 nm", "0.15", "0.67", "0.80", "0.90", "0.95"],
], [3060, 1300, 1250, 1250, 1250, 1250]));
C.push(...fig(`${NEWF}/four_levers.png`, 6.5, "The levers with bubbles (1D, case 6). (a) Temperature: floor H₂ against the level at which each kind of seed starts; bubbles start where the black line is above a dashed line; labels give the top etch rate. (b) Spin speed: bottom etch with bubbles; the few-seeds slit becomes bubble-free from 1000 rpm, far above what 15° sound gives (dashed). (c) Concentration: bottom etch with bubbles and the floor H₂. Seidel rate law, c_sat, Ea and the Levich film ASSUMED."));
C.push(P("**Dissolved gas (for completeness).** Degassed vs air-saturated vs ~2 atm N₂ lowers every bubble level by only about 1× per atmosphere (a plug holds ~14 atm), so the bottom etch changes by under 0.2 nm/min. Degassing could matter only by removing seeds, which needs an experiment."));
C.push(P("**Inference.** The levers act on the H₂ itself and are far stronger than any sound setting: with few seeds, 1000 rpm (no sound) gives 283.6 nm/min at the bottom against 54.5 for continuous 15° sound. With seeds, no full-rate setting avoids the plug, because the in-slit +59× needs a slower etch; the answer there is the two-step recipe.", { spacing: { before: 120 } }));

// ---------- 7. Comparison ----------
C.push(H1("7. The four cases compared"));
C.push(H2("7.1 Side by side"));
C.push(table([
  ["Quantity (with bubbles)", "1 No megasonics", "2 Horizontal 15°", "3 Vertical 90°, real MegPie", "4 Levers (best)"],
  ["What it acts on", "–", "Film above the wafer (sideways slip)", "Pressure at the wafer; nothing slides", "H₂ production and film removal"],
  ["Mouth H₂", "63×", "43×", "63× (63.1)", "35× (1000 rpm); 4× (25 °C, 2000 rpm)"],
  ["Floor H₂ (no bubble yet)", "121×", "102×", "121×", "93× (1000 rpm); 83× (25 wt %); 14× (25 °C, 2000 rpm)"],
  ["Plug growth, Fluent (µm/s)", "143–183", "111–137 (−19 to −26 %)", "143–185 (+0.2–0.7 %)", "not run in Fluent"],
  ["Plug-top level", "13.9×", "13.9×", "13.9×", "13.9× at 60 °C (it is set by γ and W)"],
  ["Cycle, flat walls", "48.6 ms", "68.1 ms", "48.6 ms", "longer or no cycle"],
  ["Top etch (nm/min)", "292.7–293.7", "295.3–295.8", "292.7–293.7", "29 (25 °C) to 297 (3000 rpm)"],
  ["Bottom etch, flat, seeds", "2.98", "3.84", "2.98", "2.6–5.7 at 60 °C; bubble-free at 20–25 °C fast spin"],
  ["Bottom etch, flat, few seeds", "28.7", "54.5", "28.85", "283.6 (1000 rpm), 194.4 (25 wt %)"],
  ["Bottom recess in 2 min, comb, seeds", "311.7 nm", "253.3 nm", "311.7 nm", "two-step: bottom/top 0.87 (30 s step 1)"],
  ["Bubble-free bottom/top", "0.958", "0.957 (flat Fluent 0.9574)", "0.958", "0.993 (25 wt %), 0.99 (20–25 °C)"],
], [2300, 1500, 1800, 1800, 1960]));
C.push(...fig(`${NEWF}/four_compare.png`, 6.6, "The four cases side by side, all with bubbles. (a) H₂ at the mouth and floor before a bubble forms, against the bubble-start levels. (b) Time-averaged bottom etch with bubbles, seeds present (red) and few seeds (blue). (c) Bottom recess after 2 minutes on comb walls with seeds. " + STREAM + " c_sat, Ea, Levich film ASSUMED."));
C.push(...fig(`${ONE}/case8.png`, 6.5, "Sound conditions with bubbles. (a) Fluent plug growth for no sound, vertical 90° and horizontal 15°. (b) 1D cycle on comb walls with seeds: bottom etch against the recess already present. (c) Bottom recess against time from flat walls; dotted = bubble-free bottom. " + STREAM));

C.push(H2("7.2 Which formulas each case is made with"));
C.push(table([
  ["Formula / principle", "Case 1", "Case 2", "Case 3", "Case 4"],
  ["F1–F4 chemistry, Seidel rate law, ER", CHECK, CHECK, CHECK, CHECK + " (full [H₂O]⁴ form, F39; Arrhenius, F38)"],
  ["F5–F9 Nernst–Planck, zero current, electroneutrality, Fick, diffusivities", CHECK, CHECK + " (+ D_osc near the mouth)", CHECK, CHECK + " (D(T))"],
  ["F10–F11 Levich film, mouth values", CHECK, CHECK + " with D + D_osc (F31)", CHECK + " × m ≈ 1.001 (F35–F37)", CHECK + " at each rpm and T (F40)"],
  ["F12–F13 H₂ source and parabola (hand check)", CHECK, CHECK, CHECK, CHECK + " (two halves, F42)"],
  ["F14–F16 Henry, Laplace, bubble levels", CHECK, CHECK, CHECK + " (levels shift < 1 %, F33)", CHECK + " at any T and pressure (F41)"],
  ["F17–F21 plug pressure, growth, Fluent plug boundary, wet pockets", CHECK, CHECK, CHECK, CHECK],
  ["F22–F23 bubble cycle, sealed pockets, start-up", CHECK, CHECK, CHECK + " (with duty, F34)", CHECK + " (two-step)"],
  ["F24–F26 plane wave, reflection, u_t / u_n / p_wall", "–", CHECK + " θ = 15°: u_t = 0.311 m/s", CHECK + " θ = 90°: u_t = 0", "–"],
  ["F27–F30 Stokes layer, imposed flow, D_osc, decay in the slit", "–", CHECK, CHECK + " (all zero: no slip)", "–"],
  ["F32–F33 slit breathing, pulsation, rectified diffusion, early vent", "–", CHECK, CHECK, "–"],
  ["F34–F37 MegPie duty, Eckart, beam edge, gap bubbles, film per turn", "–", "– (continuous what-if)", CHECK, "–"],
  ["F38–F42 temperature, concentration, spin, window margin", "–", "–", "–", CHECK],
], [3300, 900, 1700, 1700, 1760]));

C.push(H2("7.3 What makes ONLY the vertical component have no effect on the etch rate and the uniformity"));
C.push(P("The sound has to pass along a chain before it can change the etch: transducer → liquid at the wafer → liquid film above the wafer → slit mouth → liquid inside the slit → the poly-Si wall (and, with bubbles, the plug). The horizontal component gets through the first three links and changes the mouth. **The vertical component is stopped at every link.** Each link is a separate, physical reason, not a setting of the model."));

C.push(H3("Link 1. At the wafer, the vertical component is a pressure, not a motion"));
C.push(P("Silicon is about 13 times stiffer acoustically than the liquid (Z_Si = ρc_L ≈ 2330 × 8433 = 19.6 MRayl against 1.53 MRayl), so at normal incidence the wafer reflects the wave almost fully, R = (19.6 − 1.53)/(19.6 + 1.53) = 0.856 (F25). Incident and reflected waves then add up in pressure and cancel in velocity (F26):"));
C.push(EQ("p_wall = p₀|1+R| = 1.86 p₀ = 0.458 MPa,     u_n = U₀|1−R| = 0.144 U₀ = 0.023 m/s,     u_t = U₀ sin 0° |1+R| = 0", "θ = 90°, 1 MHz, 2 W/cm²"));
C.push(P("So the wafer surface is a **velocity node and a pressure antinode**. The liquid next to it is squeezed but hardly moves, and nothing slides along the surface. At 15° the same formulas give u_t = 0.311 m/s, almost twice the incident amplitude U₀ = 0.16 m/s: tilting turns the reflection into sideways motion. No frequency or power changes this at 90°, because u_t = 0 is exact for any amplitude (Figure 4a)."));

C.push(H3("Link 2. In the film above the wafer, a uniform up-and-down motion neither shears nor mixes"));
C.push(P("The mouth level is set by how fast the film carries H₂ away. Any flow helps only if it brings fresh liquid towards the wall, u_z = −C z² near the wafer (F36), and that needs liquid to spread sideways: by continuity, ∂u_z/∂z = −∇∥·u∥. A plane wave at normal incidence is the same everywhere along the wafer, so ∇∥·u∥ = 0 and C = 0. What remains is a reversible compression: the liquid 54 µm above the wafer (the edge of the diffusion layer) moves up and down by only about U₀|1+R|kz/ω ≈ 10 nm per cycle, and the time average is zero."));
C.push(P("Compare the horizontal component: it slides the liquid along the wall inside a Stokes layer δ = 0.39 µm, which shears it at u_t/δ ≈ 8×10⁵ s⁻¹ and gives a mixing D_osc = u_t²/(2ω) ≈ 7.7×10⁻⁹ m²/s, comparable to D_H₂ = 9.6×10⁻⁹ m²/s. That is why the mouth falls from 63× to 43× at 15°. At 90°, D_osc = 0 (F29 with u_t = 0). Even if the up-down speed were counted as mixing, u_n²/(2ω) = 4×10⁻¹¹ m²/s is 0.4 % of D_H₂."));
C.push(P("The only vertical effects left are second order. Eckart streaming pushes the liquid towards the wafer along the beam, but in a closed 2 mm gap that push is held by pressure, so flow appears only at the beam edges (24 µm/s, m = 1.0007–1.0013). Edge sloshing covers about 1 % of each turn (m = 1.0006–1.0015). A renewal of m ≥ 1.8 all the time would be needed to matter."));

C.push(H3("Link 3. At the slit mouth, the slit is far too short to feel the wave"));
C.push(P("The wavelength is c/f = 1.5 mm; the slit is 10 µm, about 150 times shorter. The whole slit therefore sits in one pressure phase: it is squeezed and released all at once. With a closed floor and an almost incompressible liquid, no liquid flows in or out; the column only breathes by ξ = L·p_wall/(ρc²) ≈ 1.9 nm (F32), a displacement of 0.02 % of the depth. That moves nothing that diffusion does not already move."));

C.push(H3("Link 4. Inside the slit, uniformity is set by diffusion that no sound reaches"));
C.push(P("The bottom/top ratio is decided inside the slit: OH⁻ used on the walls, resupplied from the mouth over 10 µm. Even the horizontal component cannot get in: oscillating flow driven at the mouth decays like e^(−4.21 z/W) (F30) and loses 98 % in the first 100 nm. That is why no angle changes the bubble-free uniformity (flat 0.9571–0.9574, comb 0.9596–0.9599, against 0.9576 and 0.9602 with no sound). Horizontal sound shifts the whole slit down together (top +2.5 nm/min); vertical sound does not even do that, so **both the etch rate and the uniformity stay exactly at the no-sound values**."));

C.push(H3("Link 5. The bubble: its level is set by the slit, and the sound is too weak to break it"));
C.push(P("The plug surface holds the liquid at c* = 13.9×, fixed by p_gas = p_atm + 2γ/W − p_vap (F17): geometry and surface tension, not sound. The plug grows on the H₂ fed from the mouth and the walls (F19), and the vertical component changes neither (mouth identical in all six Fluent groups; growth +0.2–0.7 %). The sound pressure at the wafer, 0.458 MPa, is below the plug gas pressure, 1.41 MPa, so the plug and the seeds only pulse gently (ε = p_a/(3p_g) = 1–6 %; bubble levels shift by under 1 %; rectified diffusion changes the plug intake by about 10⁻⁴). Breaking a plug would need p_a ≥ 1.41 MPa, i.e. about 19 W/cm² (71 W/cm² for a 50 nm seed), against 0.5–2 W/cm² on the tool."));

C.push(H3("Link 6. On the real tool, the MegPie is there only one sixth of the time"));
C.push(P("A slit is under the 60° sector for 33 of every 200 ms (F34). The film needs 0.30 s to forget a disturbance, so even a perfect renewal under the head would only bring the mouth to 28.8× on average and 49.9× at the worst moment, and the floor would still be at 108×. Real vertical effects are thousands of times weaker than 'perfect'."));

C.push(H3("Summary of the chain"));
C.push(table([
  ["Link", "Horizontal component (15°)", "Vertical component (90°)", "Deciding number"],
  ["1 At the wafer", "slides the liquid: u_t = 0.311 m/s", "pressure antinode, velocity node: u_t = 0, u_n = 0.023 m/s", "R = 0.856; |1+R| = 1.86, |1−R| = 0.14"],
  ["2 Film above the wafer", "Stokes-layer shear mixes it: D_osc ≈ 7.7×10⁻⁹ m²/s, mouth 63 → 43×", "uniform, reversible compression (~10 nm); streaming m ≈ 1.001", "needs m ≥ 1.8 to matter"],
  ["3 Slit mouth", "slip dies in ~100 nm", "slit squeezed in phase, ξ ≈ 1.9 nm", "λ = 1.5 mm ≫ L = 10 µm"],
  ["4 Inside the slit", "no change in bottom/top", "no change in bottom/top", "e^(−4.21 z/W); in-slit +59× untouched"],
  ["5 The plug", "fed less: grows 19–26 % slower, but never stops", "unchanged: growth +0.2–0.7 %", "plug level 13.9× = f(γ, W); p_a 0.46 < p_g 1.41 MPa"],
  ["6 Time on the wafer", "(run as continuous: a what-if)", "33 of 200 ms; film memory 0.30 s", "duty 1/6"],
  ["Net effect on the etch", "top +2.5 nm/min; comb bottom −19 % with seeds; few seeds 28.7 → 54.5", "none: rates and uniformity identical", "–"],
], [1600, 2600, 2700, 2460]));
C.push(P("**In one sentence:** the vertical component reaches the wafer as a pressure, and an etch inside a 100 nm slit can only be changed by moving liquid along the wafer (to renew the mouth) or into the slit (to renew the inside); at 90° the wafer reflection removes the first, the 1.5 mm wavelength removes the second, and the plug level is fixed by the slit width, so etch rate and uniformity stay at their no-sound values.", { spacing: { before: 160 } }));

C.push(H2("7.4 And the horizontal component is not a win either"));
C.push(P("Horizontal sound does change the mouth, but with bubbles that is double-edged. Lower H₂ above the plug delays the next bubble (good when seeds are few: 28.7 → 54.5 nm/min), and it slows a plug that is already there, so the cycle lengthens (48.6 → 68.1 ms) and shallow comb pockets get fewer refills (bad when seeds are present: 311.7 → 253.3 nm in 2 minutes). Spin speed reaches the same mouth more cheaply (600 rpm ≈ 15°) and 1000 rpm does five times better for the few-seeds slit. On this evidence a tilted transducer is not worth asking for."));

C.push(H2("7.5 What would have to change for vertical sound to matter"));
C.push(table([
  ["Route", "What would be needed", "Possible gain", "Status"],
  ["A. Gap bubbles as an H₂ getter at the mouths", "≥ 1000 bubbles per mm² at the wafer taking up H₂", "Few seeds: 28.7 → 56.8 nm/min with the real sector; 284 (bubble-free) if the whole wafer were covered all the time", "Possible only if that bubble layer exists: measure film clearing time MegPie on/off and count bubbles"],
  ["B. Removing seeds (megasonic pre-wet or degassing)", "Sound helping the liquid wet the slits and dissolve trapped air before the hot etch", "Largest: moves the slit from the 13.9× world (3 nm/min flat bottom) to the ~100× world (bubble-free at 1000 rpm)", "Not modellable: a seed question, needs a wafer test"],
  ["C. Breaking or ejecting the plug", "p_a above 1.41 MPa", "Plug collapses", "≈ 19 W/cm² (71 for a 50 nm seed): not realistic, risks damage"],
], [2100, 2400, 2560, 2300]));
C.push(P("Anything that only improves transport at the mouth will, like the horizontal case, help the few-seeds slit and hurt the seeded comb slit. Anything that shortens the bubble cycle or removes seeds would help both."));

C.push(H2("7.6 Conclusions"));
C.push(B("**No megasonics** sets the reference: the bubble cycle, not diffusion, decides the bottom (flat 3 nm/min; comb 312 nm in 2 min after a start-up delay)."));
C.push(B("**Horizontal megasonics** is the only sound setting that changes anything, through the film above the wafer, and with bubbles it cuts both ways: better with few seeds, 19 % worse on comb walls with seeds."));
C.push(B("**The real vertical MegPie** is identical to no sound in every quantity, for the six physical reasons of section 7.3."));
C.push(B("**Process levers** move the H₂ itself and win: spin ≥ 1000 rpm or 25 wt % (few seeds), and the two-step recipe (seeds present, 0.46 → 0.87 bottom/top)."));
C.push(B("**Wafer tests that would settle the open questions:** single vs two-step recipe; bottom recess against time at 300 vs 1000 rpm (shows whether seeds are present); normal vs degassed TMAH with and without a megasonic pre-wet; film clearing time with the MegPie on and off."));

C.push(H2("Where every result lives"));
C.push(table([
  ["What", "Location"],
  ["Fluent plug runs (18) and the side-by-side maps", "Puma ~/project1/results/case8/ (case8_table.csv, case8_summary.png, <group>/maps_*.png, diff_*.png); logs/<case>_<job>.out ('PLUG' line)"],
  ["1D bubble cycle, sound conditions", "megasonic_etch/results_1d/case8_bottom_vs_recess.csv, case8_startup.csv, case8.png"],
  ["Flat MegPie mechanisms (case 7)", "results_1d/case7_mechanisms.csv, case7_film.csv, case7_scenarios.csv, case7.png"],
  ["Levers (case 6, levers study)", "results_1d/case6_window.csv, case6_rpm_cycle.csv, case6_two_step.csv, levers_concentration.csv, levers_gas.csv"],
  ["Code", "etchsim/plug.py, window.py, normal.py, acoustics.py; run_case6.py, run_case7.py, run_case8.py, run_levers.py; Puma make_case8.py"],
  ["Formulas, case by case", "megasonic_etch/docs/case_formulas.md (tables 1–10)"],
  ["This document", "docs/make_four_cases_doc.js and docs/make_four_cases_figs.py"],
], [3000, 6360]));
C.push(P("**Values ASSUMED in this document:** 5 wt % TMAH at 60 °C; ER_ref = 300 nm/min; c_sat = 0.70 mM and its van 't Hoff slope (530 K), no salting-out; γ = 0.0662 N/m and p_vap = 19.9 kPa (water); water viscosity at every concentration; the Seidel rate law for TMAH; Ea = 0.57 eV; Levich film at every spin speed; pitch 1 µm; MegPie gap 2 mm and 60° sector (33 of 200 ms); water sound absorption (Eckart α); bubble numbers in the gap; the bubble-start level (13.9× with seeds, ~100× with few seeds); uniform recess along the slit; instant refill after each vent; instant temperature switch in the two-step recipe; 15° as the horizontal case.", { spacing: { before: 160 } }));

// ---------- build ----------
const doc = new Document({
  creator: "Project 1", title: "Megasonics and hydrogen bubbles: four cases compared",
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: FONT, color: "1F3864" }, paragraph: { spacing: { before: 240, after: 160 }, keepNext: true, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: FONT, color: "2E5597" }, paragraph: { spacing: { before: 220, after: 120 }, keepNext: true, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 23, bold: true, font: FONT, color: "404040" }, paragraph: { spacing: { before: 160, after: 80 }, keepNext: true, outlineLevel: 2 } },
    ],
  },
  numbering: { config: numCfg },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "Project 1: four cases with bubbles   |   page ", size: 16, color: "888888" }),
        new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "888888" })] })] }) },
    children: C,
  }],
});
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  console.log("wrote", OUT, buf.length, "bytes,", figNo, "figures");
});

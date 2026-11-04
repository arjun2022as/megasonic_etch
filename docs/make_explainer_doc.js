// Explainer document: H2 bubbles, saturation, Henry's law and the five simulation cases (Project 1).
// Run:  NODE_PATH=E:/claude_tools/node_modules node docs/make_explainer_doc.js
// Figures: new ones from docs/make_explainer_figs.py (E:/claude_tools/docfigs_out), Fluent ones from the Puma
// zip (results/<case>/plots, unzipped to E:/claude_tools/docfigs_in), 1D ones from results_1d/.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, HeadingLevel, AlignmentType, WidthType,
  ShadingType, LevelFormat, BorderStyle, Footer, PageNumber, ImageRun, PageBreak, TableOfContents,
} = require("docx");

const NEW = "E:/claude_tools/docfigs_out";
const FL = "E:/claude_tools/docfigs_in/results";
const ONE = path.join(__dirname, "..", "results_1d");
const OUT = process.argv[2] || "C:/Users/paisr/Downloads/Project 1 - H2 bubbles and the five cases.docx";
const CW = 9360; // content width, DXA (US Letter, 1 inch margins)
const FONT = "Calibri";

// ---------- helpers ----------
function runs(text, extra = {}) {
  // **bold** and _italic_ markup
  const out = [];
  text.split(/(\*\*[^*]+\*\*|_[^_]+_)/).forEach((s) => {
    if (!s) return;
    if (s.startsWith("**")) out.push(new TextRun({ text: s.slice(2, -2), bold: true, ...extra }));
    else if (s.startsWith("_") && s.endsWith("_") && s.length > 2) out.push(new TextRun({ text: s.slice(1, -1), italics: true, ...extra }));
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
// Title block
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 600, after: 120 },
  children: [new TextRun({ text: "Hydrogen bubbles in a TMAH-etched 3D NAND slit", bold: true, size: 40 })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
  children: [new TextRun({ text: "Saturation, Henry's law, and what our five simulation cases show", size: 28, color: "444444" })] }));
C.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 360 },
  children: [new TextRun({ text: "Project 1: megasonic-assisted TMAH wet etching of poly-Si in high-aspect-ratio slits  |  University of Arizona  |  3 November 2026", size: 20, color: "666666" })] }));

C.push(box("The story in five sentences", [
  "TMAH etching poly-Si makes hydrogen. Every silicon atom removed releases two H₂ molecules, and in a 100 nm wide, 10 µm deep slit that hydrogen cannot get out fast enough.",
  "With no bubbles, the dissolved H₂ reaches about 63 times saturation at the slit mouth and about 122–131 times at the floor. That is far more than a bubble needs.",
  "Henry's law and the Laplace pressure of a curved gas surface together set how much dissolved H₂ a bubble needs to survive. A plug of gas that fills the slit needs only 13.9 times saturation, so once one forms it grows fast (115–185 µm/s) and blocks the slit.",
  "On flat walls a cycling plug almost stops the bottom from etching (3 nm/min instead of 281). On realistic comb walls (recessed poly-Si) the bottom keeps etching, but only after a start-up delay. Small pinned bubbles slow the etch by the fraction of wall they cover.",
  "Megasonics, as modelled here, refresh the liquid at the mouth but do not reach inside the slit. At realistic tool settings they change the bubble cycle by less than 1 %. The next step (case 6) is to find process conditions that keep H₂ below the bubble limits.",
], "EAF3FB"));
C.push(gap());
C.push(P("**How to read this document.** Chapter 1 sets out the system. Chapter 2 gives the basics every case relies on: saturation, Henry's law, the Laplace pressure, and the life of a bubble. Each case chapter then opens with a short box of extra basics, and follows the same order: _what it is, why it matters, what we want from it, how it is simulated, the numbers, the results, and where the files are_. Chapter 8 puts all five cases on one picture (the \"saturation ladder\")."));
C.push(P("**Two standing caveats.** (1) Wherever sound is involved: " + STREAM + " (2) Values marked ASSUMED are model inputs not yet measured for our chemistry. The most important ones are the H₂ solubility, the surface tension, the reference etch rate, and the H₂ level at which bubbles first appear."));

C.push(H2("The five cases at a glance"));
C.push(table([
  ["Case", "Question it answers", "Model", "One-line answer"],
  ["1  Baseline (M0)", "How does the slit etch with no sound and no bubble?", "2D Fluent + 1D check", "Bottom/top 0.9576. H₂ reaches 122–131× saturation, so bubbles are expected."],
  ["2  Fixed plugs (B)", "What does a gas plug do to supply and etching?", "2D Fluent, plug held fixed", "The plug drinks the H₂ around it down to 13.9× and grows at ~143 µm/s. Walls beside it stop etching."],
  ["3  Angles (A, R)", "Does tilting the sound make the etch more even?", "2D Fluent, flat + comb walls", "No: bottom/top changes by at most 0.0006."],
  ["4  Growing plug (cycle)", "What happens over a real 2-minute etch?", "1D cycle model + 2D snapshots", "Grow, vent and refill every ~49 ms. Flat walls: the bottom almost stops. Comb walls: it keeps etching after a delay."],
  ["5  Small bubbles", "Can bubbles exist without becoming a plug? What do they cost?", "1D, pinned-bubble limits", "10 nm caps stay small. Covering 10/30 % of the wall costs 10/30 % of the etch rate."],
], [1500, 2700, 1900, 3260]));
C.push(P("Case names in the files: **M0** = no megasonics; **A_f1_I2_tθ** = sound at 1 MHz, 2 W/cm², incidence angle θ (90° = straight down); **B0** = gas plug, no sound; **B_f1_I2** = plug + sound at 90°; **BA_…_tθ** = plug + tilted sound; **_floor / _mid / _mouth** = where the plug sits; **_l200 / _l3000 / _l6000** = plug length 0.2 / 3 / 6 µm (default 1 µm); **R_ … _r300** = comb walls with the poly-Si recessed 300 nm.", { spacing: { before: 120, after: 120 } }));

// ---------- 1. System ----------
C.push(H1("1. The system: what we are simulating"));
C.push(P("A 3D NAND stack is a pile of alternating SiO₂ and poly-Si layers, each 50 nm thick. A slit is cut down through it: 100 nm wide and 10 µm deep, an aspect ratio of 100. Hot TMAH (5 wt %, 60 °C; ASSUMED process point) fills the slit and etches the poly-Si layers sideways but leaves the oxide alone. On the tool, the wafer spins under a thin liquid film, and a flat MegPie transducer sends megasonic sound (around 1 MHz) into the film over one sector of the wafer."));
C.push(EQ("Si + 2 OH⁻ + 2 H₂O  →  SiO₂(OH)₂²⁻ (silicate) + 2 H₂"));
C.push(P("So each etched Si atom **uses two OH⁻, makes one silicate ion and two H₂ molecules**. All three have to travel the full 10 µm between the mouth and the place they are used or made, by diffusion. In the model the ions also drift in the small electric field that keeps the current at zero (electromigration). As the etch proceeds, the poly-Si layers recess, and the wall becomes a comb of oxide teeth with liquid-filled pockets between them (Figure 1b)."));
C.push(...fig(`${NEW}/fig_geometry.png`, 6.2, "The slit as modelled. (a) Flat walls: when a gas plug sits in the slit, the walls beside it are dry and do not etch. (b) Comb walls: the poly-Si has recessed into 50 nm tall pockets (300 nm deep in our runs). The pockets beside a plug stay full of liquid and keep etching on the etchant stored in them. Sketch only, not to scale."));
C.push(P("**Why it matters.** Micron needs the bottom poly-Si layers to recess as much as the top ones. Uneven recess means uneven word lines. Our measure of evenness is the ratio **bottom etch rate / top etch rate** (1 = perfect). The project asks whether megasonics can improve that ratio, and what hydrogen does to it."));

// ---------- 2. Basics ----------
C.push(H1("2. Basics: saturation, Henry's law and the life of a bubble"));
C.push(H2("2.1 Saturation: how much dissolved H₂ is \"too much\""));
C.push(P("**Henry's law** says that the amount of a gas that dissolves in a liquid is proportional to the pressure of that gas above the liquid:"));
C.push(EQ("c = p_H₂ / K_H", "c: dissolved H₂ (mol/m³), p_H₂: H₂ pressure in the gas, K_H: Henry constant"));
C.push(P("At 1 atm of H₂ this gives the **saturation concentration** c_sat = 0.70 mM (ASSUMED: water value at 60 °C; the salting-out effect of TMAH is not yet known). We measure dissolved H₂ by the **saturation ratio**:"));
C.push(EQ("S = c / c_sat", "S = 1: saturated;  S = 63: sixty-three times more H₂ than 1 atm can hold"));
C.push(P("Liquid with S > 1 is _supersaturated_. It holds more gas than it would at 1 atm, but it does not foam by itself, because a gas bubble first has to exist and survive (section 2.2)."));
C.push(H3("Where the H₂ level comes from: mouth, slit, floor"));
C.push(table([
  ["Place", "What sets it", "Formula", "Value"],
  ["Mouth", "H₂ from all the slits on the wafer leaves through the thin liquid film on top of the spinning wafer", "c_mouth = J / k_m, with k_m ≈ 1.7×10⁻⁴ m/s (Levich, spin tool)", "44 mM = **63×**"],
  ["Inside the slit", "Each poly-Si layer makes H₂, which can only diffuse up to the mouth", "q = 2 r_Si · 2 f_poly / W ≈ 8000 mol/m³/s;  Δc = q L² / (2 D_H₂)", "+42 mM = **+60×**"],
  ["Floor", "mouth value + in-slit build-up", "c_floor = c_mouth + Δc", "≈ **122×** (1D), 131× (2D)"],
], [1200, 3200, 3160, 1800]));
C.push(P("Here r_Si = 4.05×10⁻⁴ mol/m²/s is the Si removal rate at about 293 nm/min, the factor 2 is two H₂ per Si, the second factor 2 counts both walls, f_poly = 1/2 is the poly-Si fraction of the wall, W = 100 nm, L = 10 µm and D_H₂ = 9.6×10⁻⁹ m²/s. The term qL²/(2D) is the textbook result for a uniformly fed dead-end channel: the concentration rises like a parabola and is highest at the closed end. The 2D Fluent value is higher (131×) because it includes a 1 µm liquid box above the mouth, which adds about 8× at the mouth."));

C.push(H2("2.2 Laplace pressure: why small bubbles need more H₂"));
C.push(P("The gas inside a curved liquid surface is squeezed by surface tension. For a round bubble of radius r, the H₂ pressure inside is"));
C.push(EQ("p_H₂ = p_atm + 2γ / r − p_vap", "γ = 0.0662 N/m, p_vap = 19.9 kPa (water, 60 °C; ASSUMED for TMAH)"));
C.push(P("Putting this into Henry's law gives the saturation the liquid needs to hold the bubble steady:"));
C.push(EQ("S_eq(r) = 1 + (2γ / r − p_vap) / p_atm"));
C.push(P("**Rule:** liquid with S > S_eq(r) pushes H₂ _into_ the bubble, so it grows. With S < S_eq(r) the bubble loses H₂ and shrinks. Smaller bubbles have a higher S_eq, so a free bubble is in an **unstable balance**. If it shrinks a little, it needs even more and dissolves. If it grows a little, it needs less and runs away."));
C.push(table([
  ["Bubble", "Radius", "S needed", "Meaning"],
  ["Tiny seed", "10 nm", "131×", "Only the floor region of a bubble-free slit is this high"],
  ["Seed that can grow at 122×", "r* = 2γ / ((S−1) p_atm + p_vap) = 11 nm", "122×", "Seeds bigger than 11 nm grow, smaller ones dissolve"],
  ["Seed touching both walls", "50 nm = W/2", "27×", "Most of the slit (63–122×) is far above this"],
  ["**Slit-wide plug**", "ends curved over W/2 in one direction only", "**13.9×**", "The lowest level any bubble needs in this slit"],
], [2300, 2900, 1200, 2960]));
C.push(...fig(`${NEW}/fig_henry_laplace.png`, 6.0, "Henry + Laplace: the H₂ saturation a bubble needs, against its radius (blue). The shaded band is the H₂ actually present in a bubble-free slit. Anything bigger than about 11–20 nm sits below the band and grows. Once the bubble spans the slit it drops to the plug line (13.9×, red)."));

C.push(H2("2.3 Why a plug needs exactly 13.9×"));
C.push(P("A round seed is curved in two directions, so its pressure term is 2γ/r. Once it is 50 nm in radius it touches both walls. It can no longer grow sideways, so it stretches along the depth and along the trench. Its end surfaces are now curved only across the 100 nm gap (a half-cylinder of radius W/2), and the other direction is flat. One curvature of radius W/2 gives γ/(W/2) = 2γ/W:"));
C.push(EQ("p_gas = p_atm + 2γ / W − p_vap = 0.101 + 1.324 − 0.020 = 1.41 MPa"));
C.push(EQ("c* = p_gas / K_H = 13.9 × c_sat = 9.7 mM      ⇒   S_plug = 13.9×"));
C.push(P("So **13.9× is set by the slit width, not by the seed**. However high the H₂ was where the seed started (say 100×), once the seed has become a plug its surface only needs 13.9×. The liquid around it, at 60–120×, is far above that, so H₂ flows into the plug and it grows quickly."));

C.push(H2("2.4 The life of a bubble, step by step"));
C.push(...steps([
  "**Build-up.** The walls etch and make H₂, which can only leave by diffusion. Dissolved H₂ climbs towards 122× near the floor.",
  "**Nucleation.** A gas seed (a nanoscale crevice, a rough spot, a pocket edge) of radius r starts to grow once S > S_eq(r). Which seeds exist is the key unknown. We treat the starting level s_nuc as a parameter (13.9×, 27×, 100×; ASSUMED).",
  "**Runaway to a plug.** Growing lowers S_eq, so growth speeds up. At 50 nm the seed touches both walls (27×), then stretches into a plug that needs only 13.9×.",
  "**The plug drinks.** The plug surface pins the liquid next to it at c* = 9.7 mM (13.9×). Henry's law works as a boundary condition. H₂ diffuses into the plug from above, both the H₂ made on the walls and the H₂ that came in at the mouth. In Fluent case 2 the H₂ falls smoothly from 63× at the mouth to 13.9× at the plug top (Figure 5).",
  "**Growth.** The gas inside is dense (ρ_g = p_gas / RT = 507 mol/m³), so the plug lengthens at db/dt = N_H₂ / (ρ_g W). With N_H₂ = 7.25×10⁻⁹ mol/s per metre of trench this is **143 µm/s**. The liquid it displaces is pushed out of the mouth.",
  "**The place where the bubble sits.** On flat walls the poly-Si beside the gas is dry: no etching and no H₂. On comb walls each 50 nm pocket beside the plug stays full of liquid, because gas would need 2γ/(50 nm) = 2.6 MPa to enter it, twice the plug pressure. The pocket keeps etching on its stored OH⁻ until that runs out (247 ms for a 300 nm deep pocket).",
  "**Venting and refill.** The plug reaches the mouth (about 50–60 ms after it started at the floor) and bursts into the film. Fresh mouth liquid (63×, full-strength OH⁻) refills the slit.",
  "**Repeat: the cycle.** The walls make H₂ again. If it reaches the nucleation level, a new plug forms. One full loop takes **about 49 ms**, which is about 2500 loops in a 2-minute etch. The cycle is not \"free mixing\": each refill brings fresh etchant, but most of the time the slit is filled with gas.",
]));

// ---------- 3. Case 1 ----------
C.push(H1("3. Case 1: the baseline (M0_none)"));
C.push(box("Basics you need first", [
  "**Diffusion-limited etch:** OH⁻ is used on the walls and resupplied only from the mouth. So it falls with depth, and the bottom etches more slowly than the top.",
  "**Reaction law:** etch rate = ER_ref · (c_OH / c_bulk)^¼, with ER_ref = 300 nm/min (ASSUMED; to be calibrated with our SEM data). The ¼ power makes the rate only weakly sensitive to OH⁻, which is why the slit is nearly even (0.96).",
  "**Electromigration:** OH⁻ and silicate are charged. A small field keeps the net current at zero and pushes them, so they do not diffuse independently.",
  "**Mouth values:** the concentrations at the top of the slit come from a 1D wafer-scale film model (spin tool, Levich mass transfer).",
]));
C.push(gap());
C.push(P("**What it is.** The slit with no sound and no bubble allowed, run to steady state in 2D Fluent (one 100 nm × 10 µm slit plus a 1 µm liquid box above the mouth)."));
C.push(P("**Why it matters.** Every other case is measured against it. It also tells us how much H₂ builds up if nothing escapes as gas."));
C.push(P("**What we want from it.** The baseline uniformity, the concentration fields, and the peak H₂."));
C.push(P("**How it is simulated.** Species OH⁻, silicate, H₂ and TMA⁺ with diffusion plus migration. The wall reaction is a user-defined function on the poly-Si faces only. A 1D model of the same slit is solved independently as a check."));
C.push(H3("Results"));
C.push(B("Bottom/top = **0.9576** (2D) against 0.9575 (1D): the two models agree. Top 293 nm/min, bottom 280 nm/min."));
C.push(B("OH⁻ falls from 495 to 412 mM. Silicate rises from 67 to 142 mM."));
C.push(B("H₂ rises from **71× at the mouth to 131× at the floor**. That is ten times the plug level, so in reality this slit cannot stay bubble-free. That is why cases 2, 4 and 5 exist."));
C.push(...fig(`${FL}/M0_none/plots/M0_none_profiles.png`, 6.4, "Case 1, depth profiles along the slit centre. From left: etch rate, OH⁻, silicate, H₂ saturation. The etch rate drops only 4 % from top to bottom, but H₂ climbs steadily to 131×."));
C.push(...fig(`${FL}/M0_none/plots/M0_none_slit.png`, 4.6, "Case 1, the whole slit (x stretched). H₂/saturation (third panel) is highest at the floor. The speed panel shows the liquid is still: transport is by diffusion only."));
C.push(P("**Where to find it.** Puma ~/project1/results/M0_none/plots/ (M0_none_slit.png, _mouth.png, _profiles.png). The final \"done:\" line is in logs/M0_none_<job>.out. The 1D check is in results_1d/profiles.png and summary.csv."));

// ---------- 4. Case 2 ----------
C.push(H1("4. Case 2: a fixed gas plug in the slit (B cases)"));
C.push(box("Basics you need first", [
  "**Plug = gas region.** The gas is not part of the liquid mesh. Its surface is a boundary held at the Henry value c* = 9.7 mM (13.9×; section 2.3).",
  "**H₂ intake** of the plug = the diffusive flux into that surface, N_H₂ (mol/s per metre of trench). Growth speed = N_H₂ / (ρ_g W).",
  "**Dry walls:** poly-Si faces beside the gas get no reaction.",
]));
C.push(gap());
C.push(P("**What it is.** The baseline slit with a gas plug of fixed length (0.2, 1, 3 or 6 µm) sitting at the floor, in the middle, or at the mouth, with and without sound. This is a snapshot: the plug is held still while the liquid settles."));
C.push(P("**Why it matters.** Before simulating a moving bubble we need to know what a plug does to its surroundings: how fast it takes in H₂, and what it does to the etch."));
C.push(P("**What we want from it.** The H₂ intake (and so the growth speed), the H₂ field around the plug, and the etch of the liquid part."));
C.push(H3("Results"));
C.push(B("1 µm floor plug: intake 7.25×10⁻⁹ mol/s/m, so growth **143 µm/s** (90° sound). Tilted sound: 133 / 125 / 115 µm/s at 60 / 45 / 15°. Tilting lowers the mouth H₂, so less H₂ is fed in."));
C.push(B("The plug is a **sink**. H₂ falls from 63× at the mouth to exactly 13.9× at the plug top (Figures 5 and 6)."));
C.push(B("The liquid above the plug etches a little more evenly (0.965 over the wet layers), because it is shorter and lower in H₂. But the 1 µm of wall beside the plug does not etch at all."));
C.push(B("Plug in the middle or at the mouth: everything below it is cut off from fresh etchant. Bottom/top = 0."));
C.push(...fig(`${FL}/B0_floor/plots/B0_floor_profiles.png`, 6.4, "Case 2 (B0_floor: 1 µm plug on the floor, no sound). The H₂ panel (right) now falls with depth, from 63× to 13.9× at the plug: the plug drinks the H₂ around it."));
C.push(...fig(`${FL}/B0_floor/plots/B0_floor_slit.png`, 4.6, "Case 2 slit view. The liquid ends at 9 µm, where the plug sits. H₂/saturation (third panel) is lowest just above the plug."));
C.push(P("**Inference.** A plug does not sit still. At 143 µm/s it would fill the 10 µm slit in well under 0.1 s. So a fixed plug is never the steady answer, and the real behaviour must be a cycle (case 4)."));
C.push(P("**Where to find it.** Puma results/B0_floor, B_f1_I2_floor, BA_f1_I2_t60/t45/t15_floor (and the _l200 versions)/plots/. The \"PLUG H2_in … growth … um/s\" line is in each log."));

// ---------- 5. Case 3 ----------
C.push(H1("5. Case 3: the angle of the sound (A and R cases)"));
C.push(box("Basics you need first", [
  "**Sound at the wafer:** a plane wave of intensity I has velocity amplitude U₀ = √(2I/ρc) = 0.16 m/s at 2 W/cm². At 90° (straight down) it only pushes the liquid up and down. Tilted, it slides the liquid sideways along the wafer: u_t = U₀ sin β |1 + R|, with β = 90° − θ and R the reflection coefficient of the Si wafer.",
  "**Stokes layer:** an oscillating flow at 1 MHz only reaches δ = √(2ν/ω) = 0.39 µm into the liquid next to a still wall.",
  "**Inside a 100 nm slit** the oscillating flow decays like e^(−4.21 z/W): it loses 98 % in the first 100 nm of depth. The Womersley number (W/2)√(ω/ν) = 0.18 says the flow is quasi-steady there.",
  "**Mixing coefficient** D_osc = |u₁|² / (2ω): the extra spreading that oscillating flow gives each species (upper bound). " + STREAM,
  "**Comb walls:** the poly-Si recessed 300 nm into 50 nm pockets, which is how the structure looks mid-etch.",
]));
C.push(gap());
C.push(P("**What it is.** Sound at 1 MHz and 2 W/cm², arriving at 90°, 75°, 60°, 45°, 30° and 15°. It is run on flat walls and again on comb walls, with no bubble."));
C.push(P("**Why it matters.** The MegPie can be tilted, and the proposal asks whether angled sound drives liquid into high-aspect-ratio structures better than normal incidence does."));
C.push(P("**What we want from it.** Does any angle raise bottom/top above the no-sound value?"));
C.push(P("**How it is simulated.** Phase A: the oscillating flow is imposed at the top of the liquid box (time step 25 ns, 8 settling + 10 averaged cycles), and D_osc is computed. Phase B: steady etching with D_osc added to diffusion. The mouth values come from the wafer-scale film model including the sound's extra mixing."));
C.push(H3("Results"));
C.push(B("Flat walls: bottom/top 0.95713–0.95740 against **0.95758** with no sound. Comb walls: 0.95961–0.95989 against **0.96021**. **No angle helps.** Tilting lowers the ratio by at most 0.0006 (Figure 7)."));
C.push(B("Sound does refresh the mouth. The top etches slightly faster (up to 295.0 against 292.4 nm/min), and H₂ at the mouth drops from 63× to 43× at 15°. The whole slit shifts down together, so the ratio does not improve."));
C.push(B("Figure 8 shows why: the speed and D_osc panels are bright above the mouth and dark inside the slit and pockets. The mixing dies within the first 100 nm."));
C.push(B("A 1D sweep over 1–3 MHz, 0.5–2 W/cm² and 30–90° (Figure 9) agrees: bottom/top 0.9539–0.9575, never above the no-sound value."));
C.push(...fig(`${NEW}/fig_case3_uniformity.png`, 6.0, "Case 3 summary from 2D Fluent: bottom/top for every angle, flat walls (blue) and comb walls (orange). The axis starts at 0.955 so the tiny differences show. Comb walls are slightly more even than flat walls, and angle changes nothing that matters."));
C.push(...fig(`${FL}/A_f1_I2_t15_r300/plots/A_f1_I2_t15_r300_mouth.png`, 6.4, "Case 3, comb walls, 15° sound: the mouth region. The speed and D_osc/D panels (right) show strong oscillating flow above the wafer that does not get into the slit or pockets. H₂ at the mouth is 43–55×, lower than the 63–72× with no sound."));
C.push(...fig(`${ONE}/megasonic_effect.png`, 5.8, "Case 3, 1D sweep of frequency, intensity and angle. Left: bottom/top never rises above the no-sound line (dotted). Right: the mean etch rate goes up by at most 0.6 nm/min."));
C.push(P("**Inference.** Under the modelled mechanism (oscillating flow + mixing), angle and power do not improve uniformity. The useful side effect is that tilted sound lowers H₂ everywhere: the floor peak drops from 122× (no sound) to 102× (15°). That matters for bubbles (cases 4–6)."));
C.push(P("**Where to find it.** Puma results/A_f1_I2_t75…t15 (flat) and R_none_r300, A_f1_I2_t75…t15_r300, R_f1_I2_t45_r300 (comb)/plots/. Comparison maps of all cases on one colour scale: results/compare/maps_*.png and diff_*.png (difference from M0_none). 1D: results_1d/megasonic_effect.png."));

// ---------- 6. Case 4 ----------
C.push(H1("6. Case 4: the growing plug and the bubble cycle"));
C.push(box("Basics you need first", [
  "**The cycle** (section 2.4): nucleate at s_nuc, grow, vent at the mouth, refill with mouth liquid, repeat.",
  "**1D cycle model:** a moving plug top b(t) with db/dt = −N_H₂/(ρ_g W). The liquid column above it is solved in time. The liquid is shifted up as the plug pushes it out of the mouth, and refills from the mouth after each vent.",
  "**s_nuc** (the H₂ level at which a new bubble starts) is unknown. We test 13.9×, 27×, 70×, 100× and \"never\".",
  "**Side view:** a bubble is really a finite \"pancake\" along the trench, not an endless sheet. The spacing between bubble sites along the trench (5–40 µm, ASSUMED) controls how much wall it blocks.",
  "**Realistic MegPie:** 90°, 1–2 W/cm², with the sound on the wafer only 33 of every 200 ms (300 rpm, 60° sector; ASSUMED).",
]));
C.push(gap());
C.push(P("**What it is.** A plug that nucleates, grows, vents and repeats, followed for 0.3 s in 1D and then extended to 2 minutes. It is checked against 2D Fluent snapshots of 1, 3 and 6 µm plugs on comb walls."));
C.push(P("**Why it matters.** This is what really happens during the etch if bubbles form. It is the case that decides the bottom etch rate."));
C.push(P("**What we want from it.** The cycle time, the time-averaged etch profile, the effect of sound, angle and wall shape, and how many nm the bottom recesses in 2 minutes."));
C.push(H3("Checks: 1D against 2D growth speed"));
C.push(P("The 1D intake of a fixed plug matches the case-2 Fluent runs within 0.3–1.5 %. On comb walls (Figure 10) the 2D and 1D growth speeds agree within 1–5 %. The worst case is 7 %, for a 6 µm plug with no sound. Comb walls grow the plug about 3 % faster than flat walls. Going from 90° to 15° slows growth by 20 % on both wall shapes."));
C.push(...fig(`${NEW}/fig_case4_growth.png`, 6.0, "Case 4 check: plug growth speed from 2D Fluent (bars, comb walls) and from the 1D model (black ticks), for 1, 3 and 6 µm plugs."));
C.push(...fig(`${FL}/B0_floor_l6000_r300/plots/B0_floor_l6000_r300_slit.png`, 4.4, "Case 4 snapshot: a 6 µm plug on comb walls (liquid only above 4 µm). H₂/saturation (third panel) falls from 55× at the mouth to 13.9× at the plug top."));
C.push(H3("Results: flat walls"));
C.push(B("Mouth liquid already arrives at 43–63×, above 13.9× and 27×. So for s_nuc = 13.9 or 27 a new plug forms straight after every refill. The cycle is **49 ms** (no sound, 90°) up to 68 ms (15°)."));
C.push(B("Time-averaged bottom etch: **3 nm/min**, against 281 without bubbles (Figure 12, middle). Over 2 minutes that is ~6 nm at the bottom against ~560 nm bubble-free."));
C.push(B("If bubbles only start at 100×: bottom 29 (no sound) to 55 nm/min (15°). The nucleation threshold is the key unknown."));
C.push(B("**Realistic MegPie** (1–2 W/cm², intermittent): every setting is within 1 % of no sound (cycle 47.9–48.6 against 48.6 ms). Rectified diffusion for a plug changes the intake by about 10⁻⁴."));
C.push(...fig(`${ONE}/plug_cycle.png`, 6.4, "Case 4, 1D cycle, flat walls. Left: the plug top rises from the floor (10 µm) to the mouth, vents and starts again about every 49 ms. Middle: time-averaged etch for different nucleation levels: the bottom is nearly dead unless bubbles start late (100×) or never. Right: sound at any angle hardly changes it."));
C.push(B("**Side view:** finite bubbles leave liquid between them along the trench. Bubble sites 5 / 10 / 20 / 40 µm apart give a bottom etch of 24 / 53 / 128 / 211 nm/min (Figure 13)."));
C.push(...fig(`${ONE}/sideview.png`, 6.4, "Case 4, side view (depth × along the trench). Left: time-averaged etch profiles for different bubble-site spacings. Middle: bubble radius against time (grow and vent). Right: map of the time-averaged etch for sites 20 µm apart: the bottom is dark right at the bubble site and recovers between sites."));
C.push(H3("Results: comb walls (the realistic shape)"));
C.push(B("The pockets beside a plug keep etching on stored liquid. Bottom etch against recess depth: 3 / 22 / 44 / 90 / 232 / 269 / **286** / 290 nm/min at R = 0 / 5 / 10 / 20 / 50 / 100 / **300** / 600 nm (Figure 14). For small R it is about 3 + 4.4·R nm/min, so the bottom bootstraps itself: the more it recesses, the faster it etches."));
C.push(B("**Start-up delay:** starting from flat walls, the bottom recesses only 1.3 nm in 15 s and 44 nm in 1 min, but **315 nm in 2 min** (top 588 nm, bubble-free 562 nm). With some recess already present after the dry etch (2 / 5 / 10 / 20 nm), the 2-minute bottom recess is 408 / 459 / 499 / 534 nm. An SEM series of bottom recess against etch time should show this delay."));
C.push(...fig(`${ONE}/comb_cycle.png`, 6.2, "Case 4, comb walls. Time-averaged etch for several recess depths, with bubbles starting at 13.9× (left) or 100× (right). Flat walls (blue) starve at the bottom. Pockets of 100 nm or more keep the bottom near 270–290 nm/min."));
C.push(P("**Inference.** Bubbles are the biggest effect in the whole study. On flat walls they almost stop the bottom. On comb walls the pockets rescue the bottom once they are deep enough, so the outcome depends on how much recess exists early on. Realistic megasonics do not change the cycle."));
C.push(P("**Where to find it.** Laptop megasonic_etch/results_1d/plug_cycle.csv/.png, realistic.csv, sideview.csv/.png, comb_cycle.csv/.png. Puma results/B0_floor_l3000(_r300), _l6000(_r300), B_f1_I2_…, BA_f1_I2_t15_… /plots/."));

// ---------- 7. Case 5 ----------
C.push(H1("7. Case 5: small bubbles that never become a plug"));
C.push(box("Basics you need first", [
  "**Free bubbles cannot stay small** (section 2.2): their balance is unstable.",
  "**Pinned surface nanobubbles** (Lohse & Zhang, Phys. Rev. E 2015) can. A gas cap sits on the wall with its edge (footprint radius L) held by a rough spot or pocket edge. Adding gas cannot widen the footprint, only bulge the cap. That shrinks the cap's curvature radius R_c and raises its pressure until it matches the liquid.",
  "**Cap balance:** R_c = 2γ / ((S − 1) p_atm + p_vap). The cap stays small only while it is at most a hemisphere, R_c ≥ L, i.e. S ≤ S_max(L) = 1 + (2γ/L − p_vap)/p_atm.",
  "**Coverage φ:** the fraction of poly-Si wall under caps (ASSUMED 10 or 30 %). Covered wall does not etch.",
]));
C.push(gap());
C.push(P("**What it is.** Bubbles that exist but never reach a 50 nm radius (they never touch the far wall), so they never become a plug."));
C.push(P("**Why it matters.** Real walls are rough and have edges. Pinned caps are likely, and they are a milder form of blocking than plugs."));
C.push(P("**What we want from it.** (1) Which cap sizes stay small at the H₂ levels in the slit. (2) What they do to etch rate and uniformity. (3) How far H₂ would have to drop for all bubbles to stay below 50 nm."));
C.push(H3("Limits"));
C.push(table([
  ["Footprint L", "S_max(L)", "No sound (63–122×)", "15° sound (43–102×)"],
  ["10 nm", "131×", "stays small everywhere", "stays small everywhere"],
  ["15 nm", "88×", "becomes a plug below 2.4 µm depth", "becomes a plug below ~5 µm"],
  ["20 nm", "66×", "becomes a plug below 0.2 µm", "becomes a plug below ~2 µm"],
  ["50 nm", "27×", "becomes a plug everywhere", "becomes a plug everywhere"],
], [1600, 1300, 3230, 3230]));
C.push(...fig(`${ONE}/nanobubble.png`, 6.2, "Case 5 limits. Left: H₂ in the slit (coloured lines) against the limit for each footprint (dashed). Where a line is to the right of a dashed limit, caps of that size run away to a plug. Right: the largest footprint that stays small at each H₂ level. Only below 27× can a bubble be as wide as 50 nm."));
C.push(H3("Effect on the etch"));
C.push(B("10 nm caps covering 10 / 30 % of the wall cut the etch rate by **10 / 30 %** (bottom 254 / 200 nm/min against 281)."));
C.push(B("Uniformity gets slightly _better_: bottom/top 0.9575 becomes 0.9615 / 0.9696. Less etching means less OH⁻ used and less H₂ made, so the bottom is starved less."));
C.push(B("15–20 nm caps become plugs (case 4) in the deeper part of the slit."));
C.push(B("To keep every bubble below 50 nm, H₂ must stay **below 27× everywhere**, about 75 % less than now. That is a target for case 6."));
C.push(...fig(`${ONE}/nanobubble_etch.png`, 6.4, "Case 5 etch effect. Left: etch rate with 0, 10 and 30 % of the wall under 10 nm caps. Middle: the same curves divided by the top rate (more even with more cover). Right: depths where 15 and 20 nm caps cannot stay small and become plugs."));
C.push(P("**Where to find it.** Laptop results_1d/nanobubble.csv/.png and nanobubble_etch.csv/.png. Formulas are in docs/case_formulas.md, table 6."));

// ---------- 8. Comparison ----------
C.push(H1("8. All five cases on one picture: the saturation ladder"));
C.push(P("Every case can be placed by one number, **how much dissolved H₂ is in the slit**, measured against the levels from chapter 2: 13.9× (a plug survives), 27× (a 50 nm bubble survives) and about 130× (a 10 nm seed can grow). Panel (a) shows each case's H₂ range on that ladder, and panel (b) what it does to the bottom of the slit."));
C.push(...fig(`${NEW}/fig_ladder.png`, 6.5, "The saturation ladder. (a) H₂ range in the slit for each case against the bubble levels. (b) Etch rate at the slit bottom for each bubble situation. " + STREAM));
C.push(table([
  ["Case", "Where it sits on the ladder", "Bottom etch", "Lesson"],
  ["1 Baseline", "63–131×, far above every bubble level", "281 nm/min (if no bubble forms)", "A bubble-free slit is not self-consistent at this process point"],
  ["2 Fixed plug", "pins the liquid at 13.9×", "0 beside and below the plug", "A plug is a sink and grows ~143 µm/s"],
  ["3 Sound angle", "shifts the range down to 43–102×", "~281 nm/min, ratio unchanged", "Sound helps the mouth, not the inside; lower H₂ is its real value"],
  ["4 Cycle", "falls to 13.9× at each plug, rebuilds after each refill", "3 (flat) / 286 (comb, steady) / 158 nm/min (comb, 2-min average)", "Bubbles dominate; pocket depth decides the outcome"],
  ["5 Small caps", "10 nm caps survive the whole range", "254 / 200 nm/min at 10 / 30 % cover", "Caps slow the etch but keep it even"],
  ["6 (next)", "goal: below 13.9×, or at least below the real nucleation level", "target 281 nm/min", "Find temperature, concentration, spin, flow, gas and sound that get there"],
], [1400, 2700, 2500, 2760]));
C.push(H2("What comes next: case 6, the bubble-free window"));
C.push(P("Case 6 sweeps the process conditions that move a slit down the ladder: temperature, TMAH concentration, spin speed and liquid flow, slit depth and pitch, dissolved gas (degassed TMAH; N₂, Ar or CO₂ added), and realistic sound. It looks for the window where H₂ stays below 13.9× everywhere, or at least below the measured nucleation level. The measurements that would firm this up most are: (1) the poly-Si etch rate at our TMAH point (SEM), (2) H₂ solubility in 5 wt % TMAH, and (3) whether bottom recess against time shows the predicted start-up delay."));

C.push(H2("Where every result lives"));
C.push(table([
  ["What", "Location"],
  ["2D Fluent pictures per case", "Puma ~/project1/results/<case>/plots/<case>_slit.png, _mouth.png, _profiles.png"],
  ["2D numbers per case", "Puma ~/project1/logs/<case>_<job>.out (\"done:\" line: uniformity, rates; \"PLUG\" line: H₂ intake and growth)"],
  ["All cases on one colour scale", "Puma ~/project1/results/compare/ (maps_*.png, diff_*.png against M0_none, profiles.png)"],
  ["1D models (cases 1, 4, 5)", "megasonic_etch/results_1d/ (*.csv and *.png)"],
  ["All formulas, case by case", "megasonic_etch/docs/case_formulas.md (tables 1–6)"],
  ["Running log and decisions", "megasonic_etch/STATUS.md"],
  ["New figures in this document", "megasonic_etch/docs/make_explainer_figs.py (geometry, Henry–Laplace, case 3 and 4 bars, ladder)"],
], [3000, 6360]));
C.push(P("Values marked ASSUMED in this document: c_sat = 0.70 mM; γ = 0.0662 N/m and p_vap = 19.9 kPa (water at 60 °C); ER_ref = 300 nm/min; 5 wt % TMAH at 60 °C; the nucleation level s_nuc; bubble-site spacing; cap coverage; uniform recess depth along the slit; instant refill from the mouth; MegPie duty (33 of 200 ms).", { spacing: { before: 160 } }));

// ---------- build ----------
const doc = new Document({
  creator: "Project 1", title: "Hydrogen bubbles in a TMAH-etched 3D NAND slit",
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: FONT, color: "1F3864" }, paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: FONT, color: "2E5597" }, paragraph: { spacing: { before: 220, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 23, bold: true, font: FONT, color: "404040" }, paragraph: { spacing: { before: 160, after: 80 }, outlineLevel: 2 } },
    ],
  },
  numbering: { config: numCfg },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "Project 1: H₂ bubbles and the five cases   |   page ", size: 16, color: "888888" }),
        new TextRun({ children: [PageNumber.CURRENT], size: 16, color: "888888" })] })] }) },
    children: C,
  }],
});
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  console.log("wrote", OUT, buf.length, "bytes,", figNo, "figures");
});

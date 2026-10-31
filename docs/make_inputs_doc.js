const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, HeadingLevel, AlignmentType,
  WidthType, ShadingType, LevelFormat, BorderStyle, Footer, PageNumber, ExternalHyperlink,
} = require("docx");

const FONT = "Calibri";
const W = 9360; // text width, US Letter with 1" margins (DXA)
const border = { style: BorderStyle.SINGLE, size: 4, color: "A6A6A6" };
const borders = { top: border, bottom: border, left: border, right: border };

function runs(text, opts = {}) {
  // **bold** segments inside text
  return text.split(/(\*\*[^*]+\*\*)/).filter(Boolean).map((s) =>
    s.startsWith("**") ? new TextRun({ text: s.slice(2, -2), bold: true, ...opts }) : new TextRun({ text: s, ...opts }));
}
const P = (text, o = {}) => new Paragraph({ children: runs(text), spacing: { after: 120 }, ...o });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const B = (text, level = 0) => new Paragraph({ numbering: { reference: "bul", level }, children: runs(text), spacing: { after: 60 } });
const N = (text) => new Paragraph({ numbering: { reference: "num", level: 0 }, children: runs(text), spacing: { after: 60 } });
const NOTE = (text) => new Paragraph({
  children: runs(text, { italics: true, size: 20 }), spacing: { after: 160 },
  border: { left: { style: BorderStyle.SINGLE, size: 12, color: "2E75B6", space: 8 } }, indent: { left: 200 },
});

function table(widths, header, rows) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (t, i, head) => new TableCell({
    borders, width: { size: widths[i], type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 100, right: 100 },
    shading: head ? { fill: "DCE6F1", type: ShadingType.CLEAR, color: "auto" } : undefined,
    children: String(t).split("\n").map((line) => new Paragraph({ children: runs(line, { size: 19, bold: head || undefined }) })),
  });
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: header.map((h, i) => cell(h, i, true)) }),
      ...rows.map((r) => new TableRow({ children: r.map((t, i) => cell(t, i, false)) }))],
  });
}
const gap = () => new Paragraph({ spacing: { after: 80 }, children: [] });

// Living document: inputs Claude needs from the user / Micron / ProSys / SEM to improve the Project 1 model.
// Build:  NODE_PATH=E:/claude_tools/node_modules node docs/make_inputs_doc.js <out.docx>   (docx kept on E: to spare C:)
// Keep VERSION, the "received" log and the request tables current whenever an item is asked for or answered.
const VERSION = "v1, 30 October 2026";

// request table: # | item | why the model needs it | priority | answer / file (left blank for the user)
const req = (rows) => table([600, 2500, 3560, 900, 1800], ["#", "What is needed", "Why (what it changes in the model)", "Priority", "Your answer / file name"],
  rows.map((r) => [...r, ""]));
// blank fill-in grid
const grid = (widths, header, n) => table(widths, header, Array.from({ length: n }, () => header.map(() => " ")));

const body = [
  new Paragraph({ spacing: { after: 60 },
    children: [new TextRun({ text: "Project 1 Inputs Needed: Data Requests for the Megasonic TMAH Etch Model", bold: true, size: 36, color: "1F3864" })] }),
  new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: "A living list of the measurements, conditions and files that would replace ASSUMED values in the model or validate it", size: 24, color: "404040" })] }),
  new Paragraph({ spacing: { after: 240 }, children: [new TextRun({ text: `Project 1, UA–Micron proposal (Savagatrup & Raghavan). ${VERSION}.`, size: 20, color: "595959" })] }),

  H1("How to use this document"),
  N("Fill in the last column of any table (a number, a short answer, or the name of a file you put next to this document), or attach SEM images and data sheets in the same folder."),
  N("Save it and tell Claude it is updated. Claude reads it, puts the values into the model (etchsim/props.py, cases.csv), reruns what is affected, and issues the next version with new requests."),
  N("Priority: **High** = changes the main results or is needed to validate them; **Med** = changes a secondary result; **Low** = refinement."),
  NOTE("Every value now used in place of these inputs is marked ASSUMED in the code and in docs/formulation.md. The simulation represents megasonics by an imposed oscillating flow plus modelled mixing, not a full acoustic-streaming solution, so experimental data are what will decide which mechanism matters."),

  H1("1. SEM results (the main validation)"),
  P("Cross-section SEM after etching is the measurement the proposal uses. The model predicts the etch rate of every poly-Si layer from top to bottom of the slit, so the most useful SEM data are the recess of each layer versus its depth."),
  req([
    ["1.1", "Cross-section SEM images after TMAH etch, with and without megasonics, same etch time", "Directly gives recess vs depth to compare with the predicted etch-rate profile and the bottom/top ratio", "High"],
    ["1.2", "Same, at 2–3 etch times (e.g. 30 s, 1 min, 2 min)", "Turns recess into an etch rate (nm/min) per layer and checks that the rate is constant in time (quasi-steady assumption)", "High"],
    ["1.3", "Scale bar, magnification, tilt angle of each image", "Converts pixels to nm; tilt corrects the measured depth", "High"],
    ["1.4", "Position of the imaged holes/slits on the wafer (radius in mm, angle from the notch)", "The spin flow and the MegPie exposure depend on radius; the model is at r = 50 mm (ASSUMED)", "Med"],
    ["1.5", "Number of holes/slits measured per condition and the spread", "Error bars; tells whether a predicted 1–3 % difference is measurable", "Med"],
    ["1.6", "Any sign of damage (broken or bent walls), residues or particles", "Upper limit on usable megasonic power", "Med"],
    ["1.7", "Any voids or unetched spots that look like trapped bubbles", "The model predicts dissolved H₂ far above saturation; bubbles may control uniformity", "High"],
  ]),
  gap(),
  H2("1.1 Template: one row per SEM sample"),
  grid([1100, 900, 1500, 900, 900, 1000, 1000, 2060], ["Sample ID", "Etch time (s)", "Megasonic: f (MHz), power (W), pulsing", "Spin (rpm)", "Temp (°C)", "Radius (mm)", "Top CD (nm)", "Notes"], 5),
  gap(),
  H2("1.2 Template: recess of each poly-Si layer versus depth"),
  P("Number the poly-Si layers from the top. Depth is from the wafer surface to the middle of the layer. Measure the recess on both sides of the slit if possible and give the mean."),
  grid([1300, 1500, 2190, 2190, 2180], ["Layer # (from top)", "Depth (µm)", "Recess (nm), sample A", "Recess (nm), sample B", "Recess (nm), sample C"], 8),
  gap(),

  H1("2. Etch chemistry and process conditions (Micron)"),
  req([
    ["2.1", "TMAH concentration (wt %)", "Sets bulk OH⁻ (now 5 wt % = 543 mM, ASSUMED) and the etch rate", "High"],
    ["2.2", "Etch temperature at the wafer (°C)", "Etch rate (Arrhenius), diffusivities and viscosity (now 60 °C, ASSUMED)", "High"],
    ["2.3", "Additives: surfactant, IPA, oxidiser, dissolved silicate in fresh bath", "Change the etch rate, the H₂ bubble behaviour and the initial silicate level", "High"],
    ["2.4", "Etch time used in production for this recess step, and the target recess (nm)", "Sets the time over which uniformity is judged (now 2 min, ASSUMED)", "High"],
    ["2.5", "Pre-clean before TMAH (HF dip to remove native oxide?) and delay before etch", "A native oxide causes an incubation time that the model does not include", "Med"],
    ["2.6", "Rinse and dry steps after the etch (DI, megasonic rinse?)", "Possible later rinse study (Chiang et al. model)", "Low"],
    ["2.7", "Dissolved gas: degassed or air-saturated TMAH; N₂ blanket?", "Controls cavitation and the H₂ bubble threshold", "Med"],
  ]),
  gap(),

  H1("3. Test structure (Micron)"),
  req([
    ["3.1", "Feature type: round holes or long slits?", "The model is a 2D slit; holes need an axisymmetric model (different supply per unit area)", "High"],
    ["3.2", "Top and bottom width (CD) and depth; taper angle", "Now 100 nm × 10 µm, straight walls (ASSUMED); taper changes the bottom supply", "High"],
    ["3.3", "Number of layer pairs and thickness of each SiO₂ and poly-Si layer", "Now 50/50 nm, oxide on top (ASSUMED)", "High"],
    ["3.4", "Pitch between holes/slits and pattern density", "Sets how much etchant the wafer surface must supply (now 1 µm pitch, ASSUMED)", "Med"],
    ["3.5", "Poly-Si doping, grain size, deposition and anneal", "Doping strongly changes the TMAH etch rate (p⁺ etch-stop)", "Med"],
    ["3.6", "What is at the slit bottom (substrate Si, oxide, poly)?", "Now an inert floor (ASSUMED); exposed Si would add consumption there", "Med"],
  ]),
  gap(),

  H1("4. Etch-rate calibration (blanket films)"),
  P("These fix the reaction law in the model without any transport effects, so the SEM comparison then tests only transport and megasonics."),
  req([
    ["4.1", "Poly-Si etch rate on unpatterned wafers, at the process TMAH concentration and temperature (nm/min)", "Calibrates the rate constant (now 300 nm/min, ASSUMED)", "High"],
    ["4.2", "Same at 2–3 TMAH concentrations (e.g. 2.5, 5, 10 wt %)", "Gives the reaction order in OH⁻ (now 1/4, ASSUMED); this sets how strongly depletion slows the bottom", "High"],
    ["4.3", "Same at 2–3 temperatures", "Activation energy, and sensitivity to transducer heating", "Med"],
    ["4.4", "Blanket etch rate with megasonics on vs off", "Separates surface (boundary-layer) effects from in-slit transport", "High"],
    ["4.5", "SiO₂ etch rate in the same TMAH", "Confirms the oxide is effectively inert (now ~0.2 nm/min)", "Low"],
  ]),
  gap(),

  H1("5. Megasonic tool (ProSys MegPie)"),
  req([
    ["5.1", "Transducer model, frequencies available (1, 2, 3 MHz?)", "Defines the frequency cases", "High"],
    ["5.2", "Electrical power settings (W) and active transducer area (cm²), or measured acoustic intensity", "Converts the tool setting to W/cm² (cases now 0.5–2 W/cm²); power settings are not intensities", "High"],
    ["5.3", "Sector angle of the MegPie wedge and its radial extent", "Fraction of each revolution a slit spends under the sound (now 60°, ASSUMED)", "High"],
    ["5.4", "Gap between transducer and wafer (mm); can it be tilted?", "Gap sets the standing-wave pattern; tilt is the only way to get oblique incidence", "High"],
    ["5.5", "Pulsing options (on/off times, duty cycle)", "Pulsing is a variable in the proposal; it interacts with the 9–51 ms diffusion times", "Med"],
    ["5.6", "Hydrophone or calorimetry map of the acoustic field on the wafer", "Real pressure amplitude vs the model's plane-wave estimate", "Med"],
    ["5.7", "Liquid temperature rise with megasonics on", "Separates heating from transport effects", "Med"],
  ]),
  gap(),

  H1("6. Spin tool and dispense"),
  req([
    ["6.1", "Spin speed during the etch (rpm) and any speed changes", "Sets the shear flow and film thickness over the slits (now 300 rpm, ASSUMED)", "High"],
    ["6.2", "TMAH flow rate (L/min), nozzle bore, fixed or scanning nozzle", "Film thickness and the supply at the wafer surface (now 1 L/min, ASSUMED)", "Med"],
    ["6.3", "Wafer size actually used (200 or 300 mm)", "Radius range and edge speed", "Med"],
  ]),
  gap(),

  H1("7. Files and documents"),
  req([
    ["7.1", "The proposal draft (UA–Micron, Savagatrup & Raghavan, 9-3-26)", "Exact aims, variables and deliverables; only a summary is on file", "High"],
    ["7.2", "\"Semiconductor - megasonic.docx\" and the Project 1/2 Deep Dive files (no longer in Downloads)", "Earlier background notes the user wants kept", "Med"],
    ["7.3", "Deymier, Raghavan et al., J. Appl. Phys. 88, 6821 (2000) and 90, 4211 (2001)", "The group's own theory of streaming near trenches; basis for the normal-incidence mechanism", "High"],
    ["7.4", "O'Connell M.S. thesis (UA, 2018); Chiang et al. 2017; Stuffle & Shadman 2022", "Earlier UA models of confined wet etching and rinsing to compare with", "Med"],
    ["7.5", "ProSys MegPie data sheet or manual", "Tool geometry and settings (Section 5)", "Med"],
  ]),
  gap(),

  H1("8. Questions for the advisors"),
  req([
    ["8.1", "Should the model include steady acoustic streaming (second-order terms) or only the oscillating boundary condition named in the proposal?", "Decides the normal-incidence (flat wafer) mechanism", "High"],
    ["8.2", "Is COMSOL expected as well as Fluent, for the deliverables?", "Tool choice for later models", "Med"],
    ["8.3", "Which SEM samples come first, and when?", "Order of model calibration", "Med"],
  ]),
  gap(),

  H1("9. Received so far"),
  table([1700, 4200, 3460], ["Date", "Item", "Used for"], [
    ["30 Oct 2026", "Proposal explainer PDF (E:\\semiconductor research papers)", "Proposal facts and reading list in the model notes"],
    [" ", " ", " "],
  ]),
];

const doc = new Document({
  title: "Project 1 inputs needed",
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: FONT, color: "1F3864" }, paragraph: { spacing: { before: 300, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: FONT, color: "2E75B6" }, paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [
    { reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
    { reference: "num", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [new TextRun({ text: `Project 1 inputs needed, ${VERSION}   Page `, size: 18, color: "808080" }),
        new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "808080" })] })] }) },
    children: body,
  }],
});

const out = process.argv[2];
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(out, buf); console.log("wrote", out, buf.length, "bytes"); });

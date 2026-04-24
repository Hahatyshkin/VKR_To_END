const fs = require("fs");
const path = require("path");

const OUT = path.join(__dirname, "Формулы_метрики_качества.docx");

const {
  Document, Packer, Paragraph, TextRun,
  AlignmentType, HeadingLevel, PageNumber, Header, Footer,
  BorderStyle, WidthType, Table, TableRow, TableCell,
  Math: MathEq,
  MathRun: MR,
  MathFraction: MF,
  MathRadical: MRad,
  MathSum: MSum,
  MathRoundBrackets: MRB,
} = require("docx");

// ============================================================
// Helpers for OMML Math
// ============================================================
// MathRun shorthand
function R(t) { return new MR(t); }

// Fraction: frac(numeratorChildren, denominatorChildren)
function frac(num, den) {
  return new MF({ numerator: Array.isArray(num) ? num : [num], denominator: Array.isArray(den) ? den : [den] });
}

// Square root
function sqrt(children) {
  return new MRad({ children: Array.isArray(children) ? children : [children] });
}

// Summation operator with lower and upper limits
function sumOp(lower, upper) {
  return new MSum({ subScript: [lower], superScript: [upper] });
}

// Round brackets
function rb(children) {
  return new MRB({ children: Array.isArray(children) ? children : [children] });
}

// Formula paragraph with right-aligned label (GOST numbered formula)
function formula(label, mathChildren) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 100, after: 100, line: 360 },
    tabStops: [{ type: "right", position: 8500 }],
    children: [
      new MathEq({ children: mathChildren }),
      ...(label ? [new TextRun({ text: `\t${label}`, size: 22, font: { ascii: "Times New Roman" }, color: "333333" })] : []),
    ],
  });
}

// ============================================================
// Text helpers
// ============================================================
const NB = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const allNB = { top: NB, bottom: NB, left: NB, right: NB, insideHorizontal: NB, insideVertical: NB };

function body(text, opts = {}) {
  return new Paragraph({
    alignment: opts.center ? AlignmentType.CENTER : AlignmentType.JUSTIFIED,
    indent: opts.noIndent ? undefined : { firstLine: 480 },
    spacing: { before: 40, after: 40, line: 360 },
    children: [new TextRun({ text, size: 24, font: { ascii: "Times New Roman", eastAsia: "SimSun" }, color: "000000", bold: !!opts.bold })],
  });
}

function italic(text) {
  return new Paragraph({
    alignment: AlignmentType.LEFT,
    indent: { firstLine: 480 },
    spacing: { before: 40, after: 40, line: 360 },
    children: [new TextRun({ text, size: 24, font: { ascii: "Times New Roman", eastAsia: "SimSun" }, color: "000000", italics: true })],
  });
}

function param(name, desc) {
  return new Paragraph({
    alignment: AlignmentType.LEFT,
    spacing: { before: 20, after: 20, line: 360 },
    indent: { left: 480 },
    children: [
      new TextRun({ text: name, size: 24, font: { ascii: "Times New Roman", eastAsia: "SimSun" }, color: "000000", bold: true }),
      new TextRun({ text: desc, size: 24, font: { ascii: "Times New Roman", eastAsia: "SimSun" }, color: "000000" }),
    ],
  });
}

function metricHeading(number, title) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    alignment: AlignmentType.CENTER,
    spacing: { before: 360, after: 200, line: 360 },
    children: [new TextRun({ text: `${number}. ${title}`, bold: true, size: 32, font: { ascii: "Times New Roman", eastAsia: "SimHei" }, color: "000000" })],
  });
}

function subHeading(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 200, after: 120, line: 360 },
    children: [new TextRun({ text, bold: true, size: 28, font: { ascii: "Times New Roman", eastAsia: "SimHei" }, color: "000000" })],
  });
}

function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 160, after: 80, line: 360 },
    children: [new TextRun({ text, bold: true, size: 26, font: { ascii: "Times New Roman", eastAsia: "SimHei" }, color: "000000" })],
  });
}

// ============================================================
// Designations table
// ============================================================
const designRows = [
  ["x[n] (ref[n])", "Опорный (оригинальный) сигнал, массив PCM-отсчётов"],
  ["y[n] (test[n])", "Тестовый (обработанный) сигнал, массив PCM-отсчётов"],
  ["N", "Длина общей части сигналов: N = min(len(x), len(y))"],
  ["X_m[k]", "Комплексный спектр опорного сигнала в окне m"],
  ["Y_m[k]", "Комплексный спектр тестового сигнала в окне m"],
  ["n_fft, N_fft", "Размер окна FFT (по умолчанию 1024)"],
  ["hop, H", "Шаг сдвига окна (по умолчанию 512)"],
  ["w[n]", "Оконная функция Ханна"],
  ["K", "Число частотных бинов: K = n_fft/2 + 1"],
  ["M", "Число окон (фреймов) в сигнале"],
  ["\u03b5 (eps)", "Малая константа 1\u00d710\u207b\u00b9\u00b2 для защиты от деления на ноль"],
  ["\u0394f (df)", "Частотное разрешение: df = sr / n_fft (Гц на бин)"],
];

const designTable = new Table({
  width: { size: 100, type: WidthType.PERCENTAGE },
  alignment: AlignmentType.CENTER,
  borders: {
    top: { style: BorderStyle.SINGLE, size: 4, color: "000000" },
    bottom: { style: BorderStyle.SINGLE, size: 4, color: "000000" },
    left: NB, right: NB, insideHorizontal: { style: BorderStyle.SINGLE, size: 1, color: "AAAAAA" }, insideVertical: NB,
  },
  rows: [
    new TableRow({ tableHeader: true, cantSplit: true, children: [
      new TableCell({ width: { size: 30, type: WidthType.PERCENTAGE },
        borders: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "000000" }, top: NB, left: NB, right: NB },
        margins: { top: 60, bottom: 60, left: 120, right: 120 },
        children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Обозначение", bold: true, size: 24, font: { ascii: "Times New Roman", eastAsia: "SimSun" } })] })] }),
      new TableCell({ width: { size: 70, type: WidthType.PERCENTAGE },
        borders: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "000000" }, top: NB, left: NB, right: NB },
        margins: { top: 60, bottom: 60, left: 120, right: 120 },
        children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Описание", bold: true, size: 24, font: { ascii: "Times New Roman", eastAsia: "SimSun" } })] })] }),
    ] }),
    ...designRows.map(([sym, desc]) => new TableRow({ cantSplit: true, children: [
      new TableCell({ width: { size: 30, type: WidthType.PERCENTAGE }, borders: allNB,
        margins: { top: 40, bottom: 40, left: 120, right: 120 },
        children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: sym, size: 22, font: { ascii: "Times New Roman" }, italics: true })] })] }),
      new TableCell({ width: { size: 70, type: WidthType.PERCENTAGE }, borders: allNB,
        margins: { top: 40, bottom: 40, left: 120, right: 120 },
        children: [new Paragraph({ alignment: AlignmentType.LEFT, children: [new TextRun({ text: desc, size: 22, font: { ascii: "Times New Roman", eastAsia: "SimSun" } })] })] }),
    ] })),
  ],
});

// ============================================================
// Weights table
// ============================================================
const weights = [
  ["LSD", "0,15", "ниже лучше"],
  ["SNR", "0,15", "выше лучше"],
  ["RMSE", "0,10", "ниже лучше"],
  ["SI-SDR", "0,10", "выше лучше"],
  ["Spectral Convergence", "0,10", "ниже лучше"],
  ["Centroid Diff", "0,05", "ниже лучше"],
  ["Cosine Similarity", "0,05", "выше лучше"],
  ["Time", "0,05", "ниже лучше"],
  ["STOI", "0,10", "выше лучше"],
  ["PESQ", "0,10", "выше лучше"],
  ["MOS", "0,05", "выше лучше"],
  ["Итого", "1,00", ""],
];

const weightsTable = new Table({
  width: { size: 100, type: WidthType.PERCENTAGE },
  alignment: AlignmentType.CENTER,
  borders: {
    top: { style: BorderStyle.SINGLE, size: 4, color: "000000" },
    bottom: { style: BorderStyle.SINGLE, size: 4, color: "000000" },
    left: NB, right: NB, insideHorizontal: { style: BorderStyle.SINGLE, size: 1, color: "AAAAAA" }, insideVertical: NB,
  },
  rows: [
    new TableRow({ tableHeader: true, cantSplit: true, children: [
      new TableCell({ width: { size: 40, type: WidthType.PERCENTAGE },
        borders: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "000000" }, top: NB, left: NB, right: NB },
        margins: { top: 60, bottom: 60, left: 120, right: 120 },
        children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Метрика", bold: true, size: 22, font: { ascii: "Times New Roman", eastAsia: "SimSun" } })] })] }),
      new TableCell({ width: { size: 20, type: WidthType.PERCENTAGE },
        borders: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "000000" }, top: NB, left: NB, right: NB },
        margins: { top: 60, bottom: 60, left: 120, right: 120 },
        children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Вес", bold: true, size: 22, font: { ascii: "Times New Roman", eastAsia: "SimSun" } })] })] }),
      new TableCell({ width: { size: 40, type: WidthType.PERCENTAGE },
        borders: { bottom: { style: BorderStyle.SINGLE, size: 2, color: "000000" }, top: NB, left: NB, right: NB },
        margins: { top: 60, bottom: 60, left: 120, right: 120 },
        children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Направление", bold: true, size: 22, font: { ascii: "Times New Roman", eastAsia: "SimSun" } })] })] }),
    ] }),
    ...weights.map(([m, w, d]) => {
      const isTotal = m === "Итого";
      return new TableRow({ cantSplit: true, children: [
        new TableCell({ width: { size: 40, type: WidthType.PERCENTAGE }, borders: allNB,
          margins: { top: 40, bottom: 40, left: 120, right: 120 },
          children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: m, size: 22, font: { ascii: "Times New Roman", eastAsia: "SimSun" }, bold: isTotal })] })] }),
        new TableCell({ width: { size: 20, type: WidthType.PERCENTAGE }, borders: allNB,
          margins: { top: 40, bottom: 40, left: 120, right: 120 },
          children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: w, size: 22, font: { ascii: "Times New Roman", eastAsia: "SimSun" }, bold: isTotal })] })] }),
        new TableCell({ width: { size: 40, type: WidthType.PERCENTAGE }, borders: allNB,
          margins: { top: 40, bottom: 40, left: 120, right: 120 },
          children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: d, size: 22, font: { ascii: "Times New Roman", eastAsia: "SimSun" }, italics: !isTotal })] })] }),
      ] });
    }),
  ],
});

// ============================================================
// FORMULAS — all as editable OMML
// Using MathRun for text parts + frac/sqrt/sumOp for structure
// ============================================================

// --- 1. SNR ---
const f1_noise = formula("(1)", [
  R("noise[n] = x[n] \u2212 y[n]"),
]);

const f1_psig = formula("(2)", [
  R("P_signal = "), rb([frac(R("1"), R("N"))]),
  R(" \u00b7 "), sumOp(R("n=0"), R("N\u22121")), R(" x[n]"), R("\u00b2"), R(" + \u03b5"),
]);

const f1_pnoise = formula("(3)", [
  R("P_noise = "), rb([frac(R("1"), R("N"))]),
  R(" \u00b7 "), sumOp(R("n=0"), R("N\u22121")), R(" noise[n]"), R("\u00b2"), R(" + \u03b5"),
]);

const f1_snr = formula("(4)", [
  R("SNR = 10 \u00b7 log\u2081\u2080"), rb([frac(R("P_signal"), R("P_noise"))]), R("  [\u0434\u0411]"),
]);

// --- 2. RMSE ---
const f2_e = formula("(5)", [
  R("e[n] = x[n] \u2212 y[n]"),
]);

const f2_rmse = formula("(6)", [
  R("RMSE = "),
  sqrt([
    rb([frac(R("1"), R("N"))]),
    R(" \u2211"), sumOp(R("n=0"), R("N\u22121")),
    R(" e[n]"), R("\u00b2"),
  ]),
]);

// --- 3. SI-SDR ---
const f3_alpha = formula("(7)", [
  R("\u03b1 = "),
  frac([
    sumOp(R("n=0"), R("N\u22121")),
    R(" x[n] \u00b7 y[n]"),
  ], [
    sumOp(R("n=0"), R("N\u22121")),
    R(" x[n]"), R("\u00b2"),
    R(" + \u03b5"),
  ]),
]);

const f3_yhat = formula("(8)", [
  R("\u0177[n] = \u03b1 \u00b7 x[n]"),
]);

const f3_enoise = formula("(9)", [
  R("e_noise[n] = y[n] \u2212 \u0177[n]"),
]);

const f3_sisdr = formula("(10)", [
  R("SI\u2013SDR = 10 \u00b7 log\u2081\u2080"),
  rb([
    frac([
      sumOp(R("n=0"), R("N\u22121")),
      R(" \u0177[n]"), R("\u00b2"),
      R(" + \u03b5"),
    ], [
      sumOp(R("n=0"), R("N\u22121")),
      R(" e_noise[n]"), R("\u00b2"),
      R(" + \u03b5"),
    ]),
  ]),
  R("  [\u0434\u0411]"),
]);

// --- 4. LSD ---
const f4_fft = formula("(11)", [
  R("X_m[k] = rFFT( x_m[n] \u00b7 w[n] )"),
]);

const f4_fft_y = formula("(12)", [
  R("Y_m[k] = rFFT( y_m[n] \u00b7 w[n] )"),
]);

const f4_sx = formula("(13)", [
  R("S_x[k] = 10 \u00b7 log\u2081\u2080"),
  rb([
    R(" |X_m[k]|"), R("\u00b2"),
    R(" + \u03b5"),
  ]),
]);

const f4_sy = formula("(14)", [
  R("S_y[k] = 10 \u00b7 log\u2081\u2080"),
  rb([
    R(" |Y_m[k]|"), R("\u00b2"),
    R(" + \u03b5"),
  ]),
]);

const f4_lsd_m = formula("(15)", [
  R("LSD_m = "),
  sqrt([
    rb([frac(R("1"), R("K"))]),
    R(" \u2211"), sumOp(R("k=0"), R("K\u22121")),
    R(" (S_x[k] \u2212 S_y[k])"), R("\u00b2"),
  ]),
]);

const f4_lsd = formula("(16)", [
  R("LSD = "), rb([frac(R("1"), R("M"))]),
  R(" \u2211"), sumOp(R("m=0"), R("M\u22121")),
  R(" LSD_m  [\u0434\u0411]"),
]);

// --- 5. Spectral Convergence ---
const f5_sc_m = formula("(17)", [
  R("SC_m = "),
  frac([
    R("|| |X_m| \u2212 |Y_m| ||\u2082"),
  ], [
    R("|| |X_m| ||\u2082 + \u03b5"),
  ]),
]);

const f5_sc = formula("(18)", [
  R("SC = "), rb([frac(R("1"), R("M"))]),
  R(" \u2211"), sumOp(R("m=0"), R("M\u22121")),
  R(" SC_m"),
]);

// --- 6. Centroid Difference ---
const f6_cx = formula("(19)", [
  R("centroid_x = "),
  frac([
    sumOp(R("k=0"), R("K\u22121")),
    R(" k \u00b7 A_m[k]"),
  ], [
    sumOp(R("k=0"), R("K\u22121")),
    R(" A_m[k] + \u03b5"),
  ]),
  R(" \u00b7 \u0394f  [\u0413\u0446]"),
]);

const f6_cy = formula("(20)", [
  R("centroid_y = "),
  frac([
    sumOp(R("k=0"), R("K\u22121")),
    R(" k \u00b7 B_m[k]"),
  ], [
    sumOp(R("k=0"), R("K\u22121")),
    R(" B_m[k] + \u03b5"),
  ]),
  R(" \u00b7 \u0394f  [\u0413\u0446]"),
]);

const f6_diff = formula("(21)", [
  R("d_m = |centroid_x \u2212 centroid_y|"),
]);

const f6_sc_diff = formula("(22)", [
  R("SC_diff = "), rb([frac(R("1"), R("M"))]),
  R(" \u2211"), sumOp(R("m=0"), R("M\u22121")),
  R(" d_m  [\u0413\u0446]"),
]);

// --- 7. Cosine Similarity ---
const f7_cos_m = formula("(23)", [
  R("cos_m = "),
  frac([
    sumOp(R("k=0"), R("K\u22121")),
    R(" A_m[k] \u00b7 B_m[k]"),
  ], [
    R("||A_m|| \u00b7 ||B_m|| + \u03b5"),
  ]),
]);

const f7_cos = formula("(24)", [
  R("CosSim = "), rb([frac(R("1"), R("M"))]),
  R(" \u2211"), sumOp(R("m=0"), R("M\u22121")),
  R(" cos_m"),
]);

// --- 8. STOI ---
const f8_fc = formula("(25)", [
  R("f_c[b] = 150 \u00b7 2"), R("^(b/3)"),
]);

const f8_env = formula("(26)", [
  R("env_ref[m, b] = "),
  sqrt([
    R(" mean( |FFT_ref[m, mask]|"),
    R("\u00b2"),
    R(" )"),
  ]),
]);

const f8_env_t = formula("(27)", [
  R("env_tst[m, b] = "),
  sqrt([
    R(" mean( |FFT_tst[m, mask]|"),
    R("\u00b2"),
    R(" )"),
  ]),
]);

const f8_rc = formula("(28)", [
  R("r_c = "),
  frac([
    R("\u2211"),
    R("m (env_ref_m \u2212 env_ref) \u00b7 (env_tst_m \u2212 env_tst)"),
  ], [
    sqrt([
      R("\u2211"),
      R("m (env_ref_m \u2212 env_ref)"),
      R("\u00b2"),
    ]),
    R(" \u00b7 "),
    sqrt([
      R("\u2211"),
      R("m (env_tst_m \u2212 env_tst)"),
      R("\u00b2"),
    ]),
    R(" + \u03b5"),
  ]),
]);

const f8_stoi = formula("(29)", [
  R("STOI = clip( mean(r_c), 0, 1 )"),
]);

// --- 9. PESQ ---
const f9_aw = formula("(30)", [
  R("W(f) = "),
  frac([
    R("12194"),
    R("\u00b2"),
    R(" \u00b7 f"),
    R("4"),
  ], [
    R("(f"),
    R("\u00b2"),
    R(" + 20,6"),
    R("\u00b2"),
    R(") \u00b7 "),
    sqrt([
      R("(f"),
      R("\u00b2"),
      R(" + 107,7"),
      R("\u00b2"),
      R(") \u00b7 (f"),
      R("\u00b2"),
      R(" + 737,9"),
      R("\u00b2"),
      R(")"),
    ]),
    R(" \u00b7 (f"),
    R("\u00b2"),
    R(" + 12194"),
    R("\u00b2"),
    R(")"),
  ]),
]);

const f9_diff = formula("(31)", [
  R("diff[k] = | log\u2081\u2080"),
  rb([
    frac([
      R(" |X_m[k]| + \u03b5"),
    ], [
      R(" |Y_m[k]| + \u03b5 + \u03b5"),
    ]),
  ]),
  R(" |"),
]);

const f9_D = formula("(32)", [
  R("D = "),
  sqrt([
    R(" mean( D_m )"),
  ]),
]);

const f9_pesq = formula("(33)", [
  R("PESQ = max( \u22120,5 ; min( 4,5 ; 4,5 \u2212 3,0 \u00b7 D ) )"),
]);

// --- 10. MOS ---
const f10_mos = formula("(34)", [
  R("MOS = max( 1,0 ; min( 5,0 ; 1 + "),
  frac([
    R("3,87"),
  ], [
    R("1 + exp( \u22121,3669 \u00b7 (PESQ \u2212 0,7197) )"),
  ]),
  R(" ) )"),
]);

// --- 11. Score ---
const f11_norm_inv = formula("(35)", [
  R("norm = "),
  frac([
    R("max \u2212 value"),
  ], [
    R("max \u2212 min + \u03b5"),
  ]),
]);

const f11_norm_dir = formula("(36)", [
  R("norm = "),
  frac([
    R("value \u2212 min"),
  ], [
    R("max \u2212 min + \u03b5"),
  ]),
]);

const f11_score = formula("(37)", [
  R("Score = "),
  sumOp(R("i=1"), R("11")),
  R(" w_i \u00b7 norm_i"),
]);


// ============================================================
// Build document
// ============================================================
const doc = new Document({
  styles: {
    default: {
      document: {
        run: { font: { ascii: "Times New Roman", eastAsia: "SimSun" }, size: 24, color: "000000" },
        paragraph: { spacing: { line: 360 } },
      },
      heading1: { run: { font: { ascii: "Times New Roman", eastAsia: "SimHei" }, size: 32, bold: true, color: "000000" }, paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 480, after: 360, line: 360 } } },
      heading2: { run: { font: { ascii: "Times New Roman", eastAsia: "SimHei" }, size: 30, bold: true, color: "000000" }, paragraph: { spacing: { before: 360, after: 240, line: 360 } } },
      heading3: { run: { font: { ascii: "Times New Roman", eastAsia: "SimHei" }, size: 28, bold: true, color: "000000" }, paragraph: { spacing: { before: 240, after: 120, line: 360 } } },
    },
  },
  sections: [
    {
      properties: {
        page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1701, right: 1417, header: 850, footer: 992 },
          pageNumbers: { start: 1, formatType: "decimal" } },
      },
      headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.CENTER, border: { bottom: { style: BorderStyle.SINGLE, size: 1, color: "000000" } }, children: [new TextRun({ text: "\u0424\u043e\u0440\u043c\u0443\u043b\u044b \u043c\u0435\u0442\u0440\u0438\u043a \u043a\u0430\u0447\u0435\u0441\u0442\u0432\u0430 \u0430\u0443\u0434\u0438\u043e\u0441\u0438\u0433\u043d\u0430\u043b\u0430", size: 18, color: "333333", font: { ascii: "Times New Roman", eastAsia: "SimSun" } })] })] }) },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], size: 21, font: { ascii: "Times New Roman" } })] })] }) },
      children: [
        // === Title ===
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 600, after: 120, line: 360 },
          children: [new TextRun({ text: "\u0424\u043e\u0440\u043c\u0443\u043b\u044b \u043c\u0435\u0442\u0440\u0438\u043a \u043a\u0430\u0447\u0435\u0441\u0442\u0432\u0430 \u0430\u0443\u0434\u0438\u043e\u0441\u0438\u0433\u043d\u0430\u043b\u0430", bold: true, size: 36, font: { ascii: "Times New Roman", eastAsia: "SimHei" }, color: "000000" })] }),
        body("\u0412\u0441\u0435 \u0444\u043e\u0440\u043c\u0443\u043b\u044b \u0441\u043e\u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0443\u044e\u0442 \u0440\u0435\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u0438 \u0432 \u0444\u0430\u0439\u043b\u0435 AudioAnalyzer/src/processing/metrics.py. \u0424\u043e\u0440\u043c\u0430\u0442 \u043e\u0444\u043e\u0440\u043c\u043b\u0435\u043d\u0438\u044f \u0441\u043e\u0433\u043b\u0430\u0441\u043d\u043e \u0442\u0440\u0435\u0431\u043e\u0432\u0430\u043d\u0438\u044f\u043c \u0413\u041e\u0421\u0422 19 (\u0441\u0438\u043c\u0432\u043e\u043b\u044b \u0444\u0438\u0437\u0438\u0447\u0435\u0441\u043a\u0438\u0445 \u0432\u0435\u043b\u0438\u0447\u0438\u043d) \u0438 \u0413\u041e\u0421\u0422 34 (\u0437\u0430\u043f\u0438\u0441\u044c \u043e\u0442\u0447\u0451\u0442\u043e\u0432): \u0448\u0440\u0438\u0444\u0442 Times New Roman, \u0440\u0430\u0437\u043c\u0435\u0440 14 \u043f\u0442 \u0434\u043b\u044f \u043e\u0441\u043d\u043e\u0432\u043d\u043e\u0433\u043e \u0442\u0435\u043a\u0441\u0442\u0430, 16 \u043f\u0442 \u0434\u043b\u044f \u0437\u0430\u0433\u043e\u043b\u043e\u0432\u043a\u043e\u0432, 1,5 \u043c\u0435\u0436\u0441\u0442\u0440\u043e\u0447\u043d\u044b\u0439 \u0438\u043d\u0442\u0435\u0440\u0432\u0430\u043b. \u0424\u043e\u0440\u043c\u0443\u043b\u044b \u044f\u0432\u043b\u044f\u044e\u0442\u0441\u044f \u0440\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u0443\u0435\u043c\u044b\u043c\u0438 \u043e\u0431\u044a\u0435\u043a\u0442\u0430\u043c\u0438 OMML (\u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u0442\u0441\u044f \u0432\u0441\u0442\u0440\u043e\u0435\u043d\u043d\u044b\u0439 \u0440\u0435\u0434\u0430\u043a\u0442\u043e\u0440 \u0444\u043e\u0440\u043c\u0443\u043b Word).", { center: true, noIndent: true }),

        // === Designations ===
        new Paragraph({ heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER, spacing: { before: 480, after: 360, line: 360 },
          children: [new TextRun({ text: "\u041e\u0431\u0449\u0438\u0435 \u043e\u0431\u043e\u0437\u043d\u0430\u0447\u0435\u043d\u0438\u044f", bold: true, size: 32, font: { ascii: "Times New Roman", eastAsia: "SimHei" }, color: "000000" })] }),
        body("\u0412 \u043d\u0430\u0441\u0442\u043e\u044f\u0449\u0435\u043c \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0435 \u043f\u0440\u0438\u043c\u0435\u043d\u044f\u044e\u0442\u0441\u044f \u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0435 \u043e\u0431\u043e\u0437\u043d\u0430\u0447\u0435\u043d\u0438\u044f, \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u043c\u044b\u0435 \u0432\u043e \u0432\u0441\u0435\u0445 \u0444\u043e\u0440\u043c\u0443\u043b\u0430\u0445 \u043d\u0438\u0436\u0435:", { noIndent: true }),
        designTable,

        // === 1. SNR ===
        metricHeading(1, "SNR (Signal-to-Noise Ratio)"),
        body("\u041e\u0442\u043d\u043e\u0448\u0435\u043d\u0438\u0435 \u043c\u043e\u0449\u043d\u043e\u0441\u0442\u0438 \u043f\u043e\u043b\u0435\u0437\u043d\u043e\u0433\u043e \u0441\u0438\u0433\u043d\u0430\u043b\u0430 \u043a \u043c\u043e\u0449\u043d\u043e\u0441\u0442\u0438 \u0448\u0443\u043c\u0430 (\u0440\u0430\u0437\u043d\u043e\u0441\u0442\u0438 \u043c\u0435\u0436\u0434\u0443 \u043e\u043f\u043e\u0440\u043d\u044b\u043c \u0438 \u0442\u0435\u0441\u0442\u043e\u0432\u044b\u043c \u0441\u0438\u0433\u043d\u0430\u043b\u0430\u043c). \u0427\u0435\u043c \u0432\u044b\u0448\u0435 SNR, \u0442\u0435\u043c \u043c\u0435\u043d\u044c\u0448\u0435 \u0438\u0441\u043a\u0430\u0436\u0435\u043d\u0438\u0439 \u0432\u043d\u0435\u0441\u0451\u043d\u043d\u044b\u0445 \u043f\u0440\u0438 \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0435. \u0420\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442 \u0432 \u0434\u0435\u0446\u0438\u0431\u0435\u043b\u0430\u0445 (\u0434\u0411), \u043f\u043e\u043b\u043e\u0436\u0438\u0442\u0435\u043b\u044c\u043d\u043e\u0435 \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435 \u0433\u043e\u0432\u043e\u0440\u0438\u0442 \u043e \u043a\u0430\u0447\u0435\u0441\u0442\u0432\u0435 \u043c\u0435\u0442\u043e\u0434\u0430."),
        italic("\u0424\u0443\u043d\u043a\u0446\u0438\u044f: compute_snr_db(reference, test)"),
        italic("\u0415\u0434\u0438\u043d\u0438\u0446\u0430: \u0434\u0411 | \u041d\u0430\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435: \u0432\u044b\u0448\u0435 \u2014 \u043b\u0443\u0447\u0448\u0435"),
        subHeading("\u0424\u043e\u0440\u043c\u0443\u043b\u0430:"),
        f1_noise, f1_psig, f1_pnoise, f1_snr,
        subHeading("\u041f\u043e\u044f\u0441\u043d\u0435\u043d\u0438\u044f \u043f\u0435\u0440\u0435\u043c\u0435\u043d\u043d\u044b\u0445:"),
        param("noise[n]", " \u2014 \u0440\u0430\u0437\u043d\u0438\u0446\u0430 \u043c\u0435\u0436\u0434\u0443 \u043e\u043f\u043e\u0440\u043d\u044b\u043c \u0438 \u0442\u0435\u0441\u0442\u043e\u0432\u044b\u043c \u0441\u0438\u0433\u043d\u0430\u043b\u0430\u043c\u0438 (\u0432\u0435\u043a\u0442\u043e\u0440 \u043e\u0448\u0438\u0431\u043a\u0438)"),
        param("P_signal", " \u2014 \u0441\u0440\u0435\u0434\u043d\u044f\u044f \u043c\u043e\u0449\u043d\u043e\u0441\u0442\u044c \u043e\u043f\u043e\u0440\u043d\u043e\u0433\u043e \u0441\u0438\u0433\u043d\u0430\u043b\u0430"),
        param("P_noise", " \u2014 \u0441\u0440\u0435\u0434\u043d\u044f\u044f \u043c\u043e\u0449\u043d\u043e\u0441\u0442\u044c \u0448\u0443\u043c\u0430/\u0438\u0441\u043a\u0430\u0436\u0435\u043d\u0438\u0439"),
        param("\u03b5", " \u2014 \u0437\u0430\u0449\u0438\u0442\u0430 \u043e\u0442 \u0434\u0435\u043b\u0435\u043d\u0438\u044f \u043d\u0430 \u043d\u043e\u043b\u044c (1\u00d710\u207b\u00b9\u00b2)"),

        // === 2. RMSE ===
        metricHeading(2, "RMSE (Root Mean Square Error)"),
        body("\u041a\u043e\u0440\u0435\u043d\u044c \u0438\u0437 \u0441\u0440\u0435\u0434\u043d\u0435\u0433\u043e \u043a\u0432\u0430\u0434\u0440\u0430\u0442\u0430 \u043e\u0442\u043a\u043b\u043e\u043d\u0435\u043d\u0438\u044f \u0442\u0435\u0441\u0442\u043e\u0432\u043e\u0433\u043e \u0441\u0438\u0433\u043d\u0430\u043b\u0430 \u043e\u0442 \u043e\u043f\u043e\u0440\u043d\u043e\u0433\u043e. \u041f\u043e\u043a\u0430\u0437\u044b\u0432\u0430\u0435\u0442 \u0441\u0440\u0435\u0434\u043d\u044e\u044e \u0432\u0435\u043b\u0438\u0447\u0438\u043d\u0443 \u043e\u0448\u0438\u0431\u043a\u0443 \u0432\u043e \u0432\u0440\u0435\u043c\u0435\u043d\u043d\u043e\u0439 \u043e\u0431\u043b\u0430\u0441\u0442\u0438. RMSE \u0447\u0443\u0432\u0441\u0442\u0432\u0438\u0442\u0435\u043b\u0435\u043d \u043a \u043a\u0440\u0443\u043f\u043d\u044b\u043c \u0432\u044b\u0431\u0440\u043e\u0441\u0430\u043c (\u0432 \u043e\u0442\u043b\u0438\u0447\u0438\u0435 \u043e\u0442 MAE). \u0414\u043b\u044f PCM-\u0441\u0438\u0433\u043d\u0430\u043b\u043e\u0432 \u0432 \u0434\u0438\u0430\u043f\u0430\u0437\u043e\u043d\u0435 [-1, 1]: RMSE = 0 \u043e\u0437\u043d\u0430\u0447\u0430\u0435\u0442 \u0438\u0434\u0435\u0430\u043b\u044c\u043d\u043e\u0435 \u0441\u043e\u0432\u043f\u0430\u0434\u0435\u043d\u0438\u0435, RMSE = 1 \u2014 \u043c\u0430\u043a\u0441\u0438\u043c\u0430\u043b\u044c\u043d\u043e \u0432\u043e\u0437\u043c\u043e\u0436\u043d\u043e\u0435 \u043e\u0442\u043a\u043b\u043e\u043d\u0435\u043d\u0438\u0435."),
        italic("\u0424\u0443\u043d\u043a\u0446\u0438\u044f: compute_rmse(reference, test)"),
        italic("\u0415\u0434\u0438\u043d\u0438\u0446\u0430: \u0431\u0435\u0437\u0440\u0430\u0437\u043c\u0435\u0440\u043d\u0430\u044f (0\u20131 \u0434\u043b\u044f [-1, 1]) | \u041d\u0430\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435: \u043d\u0438\u0436\u0435 \u2014 \u043b\u0443\u0447\u0448\u0435"),
        subHeading("\u0424\u043e\u0440\u043c\u0443\u043b\u0430:"),
        f2_e, f2_rmse,
        subHeading("\u041f\u043e\u044f\u0441\u043d\u0435\u043d\u0438\u044f \u043f\u0435\u0440\u0435\u043c\u0435\u043d\u043d\u044b\u0445:"),
        param("e[n]", " \u2014 \u0440\u0430\u0437\u043d\u0438\u0446\u0430 \u043c\u0435\u0436\u0434\u0443 \u043e\u0442\u0441\u0447\u0451\u0442\u0430\u043c\u0438 \u043e\u043f\u043e\u0440\u043d\u043e\u0433\u043e \u0438 \u0442\u0435\u0441\u0442\u043e\u0432\u043e\u0433\u043e \u0441\u0438\u0433\u043d\u0430\u043b\u043e\u0432"),
        param("N", " \u2014 \u0447\u0438\u0441\u043b\u043e \u043e\u0442\u0441\u0447\u0451\u0442\u043e\u0432 (\u043e\u0431\u0449\u0430\u044f \u0434\u043b\u0438\u043d\u0430)"),

        // === 3. SI-SDR ===
        metricHeading(3, "SI-SDR (Scale-Invariant Signal-to-Distortion Ratio)"),
        body("\u041c\u0430\u0441\u0448\u0442\u0430\u0431\u043d\u043e-\u0438\u043d\u0432\u0430\u0440\u0438\u0430\u043d\u0442\u043d\u043e\u0435 \u043e\u0442\u043d\u043e\u0448\u0435\u043d\u0438\u0435 \u0441\u0438\u0433\u043d\u0430\u043b/\u0438\u0441\u043a\u0430\u0436\u0435\u043d\u0438\u044f. \u0412 \u043e\u0442\u043b\u0438\u0447\u0438\u0435 \u043e\u0442 \u043e\u0431\u044b\u0447\u043d\u043e\u0433\u043e SNR, SI-SDR \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438 \u043f\u043e\u0434\u0431\u0438\u0440\u0430\u0435\u0442 \u043e\u043f\u0442\u0438\u043c\u0430\u043b\u044c\u043d\u044b\u0439 \u043c\u0430\u0441\u0448\u0442\u0430\u0431 (\u0437\u0443\u043c), \u043a\u043e\u043c\u043f\u0435\u043d\u0441\u0438\u0440\u0443\u044f \u0433\u043b\u043e\u0431\u0430\u043b\u044c\u043d\u044b\u0435 \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f \u0433\u0440\u043e\u043c\u043a\u043e\u0441\u0442\u0438. \u0418\u043d\u0432\u0430\u0440\u0438\u0430\u043d\u0442\u0435\u043d \u043a \u043b\u0438\u043d\u0435\u0439\u043d\u043e\u043c\u0443 \u0443\u0441\u0438\u043b\u0435\u043d\u0438\u044e/\u043e\u0441\u043b\u0430\u0431\u043b\u0435\u043d\u0438\u044e. \u0415\u0441\u043b\u0438 y[n] = c\u00b7x[n] \u043f\u0440\u0438 \u043b\u044e\u0431\u043e\u043c c \u2260 0, \u0442\u043e SI-SDR = +\u221e."),
        italic("\u0424\u0443\u043d\u043a\u0446\u0438\u044f: compute_si_sdr_db(reference, test)"),
        italic("\u0415\u0434\u0438\u043d\u0438\u0446\u0430: \u0434\u0411 | \u041d\u0430\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435: \u0432\u044b\u0448\u0435 \u2014 \u043b\u0443\u0447\u0448\u0435"),
        subHeading("\u0424\u043e\u0440\u043c\u0443\u043b\u0430:"),
        f3_alpha, f3_yhat, f3_enoise, f3_sisdr,
        subHeading("\u041f\u043e\u044f\u0441\u043d\u0435\u043d\u0438\u044f \u043f\u0435\u0440\u0435\u043c\u0435\u043d\u043d\u044b\u0445:"),
        param("\u03b1", " \u2014 \u043a\u043e\u044d\u0444\u0444\u0438\u0446\u0438\u0435\u043d\u0442 \u043c\u0430\u0441\u0448\u0442\u0430\u0431\u0430 (\u043f\u0440\u043e\u0435\u043a\u0446\u0438\u044f y \u043d\u0430 x \u043c\u0435\u0442\u043e\u0434\u043e\u043c \u043d\u0430\u0438\u043c\u0435\u043d\u044c\u0448\u0438\u0445 \u043a\u0432\u0430\u0434\u0440\u0430\u0442\u043e\u0432)"),
        param("\u0177[n]", " \u2014 \u00ab\u0446\u0435\u043b\u0435\u0432\u043e\u0439\u00bb \u043a\u043e\u043c\u043f\u043e\u043d\u0435\u043d\u0442 \u0442\u0435\u0441\u0442\u043e\u0432\u043e\u0433\u043e \u0441\u0438\u0433\u043d\u0430\u043b\u0430 (\u0447\u0430\u0441\u0442\u044c, \u0441\u043e\u0432\u043f\u0430\u0434\u0430\u044e\u0449\u0430\u044f \u0441 \u043e\u043f\u043e\u0440\u043d\u044b\u043c)"),
        param("e_noise[n]", " \u2014 \u00ab\u0448\u0443\u043c\u043e\u0432\u0430\u044f\u00bb \u043a\u043e\u043c\u043f\u043e\u043d\u0435\u043d\u0442\u0430 (\u0438\u0441\u043a\u0430\u0436\u0435\u043d\u0438\u044f)"),

        // === 4. LSD ===
        metricHeading(4, "LSD (Log-Spectral Distance)"),
        body("\u041b\u043e\u0433\u0430\u0440\u0438\u0444\u043c\u0438\u0447\u0435\u0441\u043a\u043e\u0435 \u0441\u043f\u0435\u043a\u0442\u0440\u0430\u043b\u044c\u043d\u043e\u0435 \u0440\u0430\u0441\u0441\u0442\u043e\u044f\u043d\u0438\u0435. \u0418\u0437\u043c\u0435\u0440\u044f\u0435\u0442 \u0441\u0440\u0435\u0434\u043d\u0435\u0435 \u0440\u0430\u0437\u043b\u0438\u0447\u0438\u0435 \u043c\u0435\u0436\u0434\u0443 \u0441\u043f\u0435\u043a\u0442\u0440\u0430\u043c\u0438 \u043e\u043f\u043e\u0440\u043d\u043e\u0433\u043e \u0438 \u0442\u0435\u0441\u0442\u043e\u0432\u043e\u0433\u043e \u0441\u0438\u0433\u043d\u0430\u043b\u043e\u0432 \u0432 \u043b\u043e\u0433\u0430\u0440\u0438\u0444\u043c\u0438\u0447\u0435\u0441\u043a\u043e\u043c \u043c\u0430\u0441\u0448\u0442\u0430\u0431\u0435 (\u0434\u0411). \u0423\u0447\u0438\u0442\u044b\u0432\u0430\u0435\u0442 \u0447\u0430\u0441\u0442\u043e\u0442\u043d\u044b\u0435 \u0445\u0430\u0440\u0430\u043a\u0442\u0435\u0440\u0438\u0441\u0442\u0438\u043a\u0438 \u0438\u0441\u043a\u0430\u0436\u0435\u043d\u0438\u0439, \u043a\u043e\u0442\u043e\u0440\u044b\u0435 \u043d\u0435 \u0432\u0438\u0434\u043d\u044b \u0432\u043e \u0432\u0440\u0435\u043c\u0435\u043d\u043d\u043e\u0439 \u043e\u0431\u043b\u0430\u0441\u0442\u0438. \u0415\u0441\u043b\u0438 \u0447\u0430\u0441\u0442\u043e\u0442\u044b \u0434\u0438\u0441\u043a\u0440\u0435\u0442\u0438\u0437\u0430\u0446\u0438\u0438 \u043d\u0435 \u0441\u043e\u0432\u043f\u0430\u0434\u0430\u044e\u0442, \u0442\u0435\u0441\u0442\u043e\u0432\u044b\u0439 \u0441\u0438\u0433\u043d\u0430\u043b \u0440\u0435\u0441\u0435\u043c\u043f\u043b\u0438\u0440\u0443\u0435\u0442\u0441\u044f \u043a sr_ref. LSD = 0 \u043e\u0437\u043d\u0430\u0447\u0430\u0435\u0442 \u0438\u0434\u0435\u043d\u0442\u0438\u0447\u043d\u044b\u0435 \u0441\u043f\u0435\u043a\u0442\u0440\u044b."),
        italic("\u0424\u0443\u043d\u043a\u0446\u0438\u044f: compute_lsd_db(reference, test, sr_ref, sr_test, n_fft=1024, hop=512)"),
        italic("\u0415\u0434\u0438\u043d\u0438\u0446\u0430: \u0434\u0411 | \u041d\u0430\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435: \u043d\u0438\u0436\u0435 \u2014 \u043b\u0443\u0447\u0448\u0435"),
        subHeading("\u0424\u043e\u0440\u043c\u0443\u043b\u0430 (\u0434\u043b\u044f \u043a\u0430\u0436\u0434\u043e\u0433\u043e \u043e\u043a\u043d\u0430 m):"),
        f4_fft, f4_fft_y, f4_sx, f4_sy, f4_lsd_m, f4_lsd,
        subHeading("\u041f\u043e\u044f\u0441\u043d\u0435\u043d\u0438\u044f \u043f\u0435\u0440\u0435\u043c\u0435\u043d\u043d\u044b\u0445:"),
        param("w[n]", " \u2014 \u043e\u043a\u043d\u043e \u0425\u0430\u043d\u043d\u0430: w[n] = 0,5(1 \u2212 cos(2\u03c0n/(n_fft\u22121))"),
        param("K", " \u2014 \u0447\u0438\u0441\u043b\u043e \u0447\u0430\u0441\u0442\u043e\u0442\u043d\u044b\u0445 \u0431\u0438\u043d\u043e\u0432: K = n_fft/2 + 1"),
        param("M", " \u2014 \u0447\u0438\u0441\u043b\u043e \u043e\u043a\u043e\u043d, max(1, 1 + (N \u2212 n_fft) // hop)"),
        param("S_x, S_y", " \u2014 \u0441\u043f\u0435\u043a\u0442\u0440\u0430\u043b\u044c\u043d\u0430\u044f \u043f\u043b\u043e\u0442\u043d\u043e\u0441\u0442\u044c \u043c\u043e\u0449\u043d\u043e\u0441\u0442\u0438 \u0432 \u0434\u0411"),

        // === 5. Spectral Convergence ===
        metricHeading(5, "Spectral Convergence (\u0421\u043f\u0435\u043a\u0442\u0440\u0430\u043b\u044c\u043d\u0430\u044f \u0441\u0445\u043e\u0434\u0438\u043c\u043e\u0441\u0442\u044c)"),
        body("\u041e\u0442\u043d\u043e\u0441\u0438\u0442\u0435\u043b\u044c\u043d\u0430\u044f \u0440\u0430\u0437\u043d\u0438\u0446\u0430 \u0430\u043c\u043f\u043b\u0438\u0442\u0443\u0434 \u0441\u043f\u0435\u043a\u0442\u0440\u043e\u0432. \u041f\u043e\u043a\u0430\u0437\u044b\u0432\u0430\u0435\u0442, \u043d\u0430\u0441\u043a\u043e\u043b\u044c\u043a\u043e \u0430\u043c\u043f\u043b\u0438\u0442\u0443\u0434\u043d\u044b\u0439 \u0441\u043f\u0435\u043a\u0442\u0440 \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u0430\u043d\u043d\u043e\u0433\u043e \u0441\u0438\u0433\u043d\u0430\u043b\u0430 \u043e\u0442\u043a\u043b\u043e\u043d\u044f\u0435\u0442\u0441\u044f \u043e\u0442 \u043e\u043f\u043e\u0440\u043d\u043e\u0433\u043e. \u0417\u043d\u0430\u0447\u0435\u043d\u0438\u0435 SC = 0 \u043e\u0437\u043d\u0430\u0447\u0430\u0435\u0442 \u043f\u043e\u043b\u043d\u043e\u0435 \u0441\u043e\u0432\u043f\u0430\u0434\u0435\u043d\u0438\u0435 \u0430\u043c\u043f\u043b\u0438\u0442\u0443\u0434\u043d\u044b\u0445 \u0441\u043f\u0435\u043a\u0442\u0440\u043e\u0432."),
        italic("\u0424\u0443\u043d\u043a\u0446\u0438\u044f: compute_spectral_convergence(reference, test, sr_ref, sr_test)"),
        italic("\u0415\u0434\u0438\u043d\u0438\u0446\u0430: \u0431\u0435\u0437\u0440\u0430\u0437\u043c\u0435\u0440\u043d\u0430\u044f | \u041d\u0430\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435: \u043d\u0438\u0436\u0435 \u2014 \u043b\u0443\u0447\u0448\u0435"),
        subHeading("\u0424\u043e\u0440\u043c\u0443\u043b\u0430 (\u0434\u043b\u044f \u043a\u0430\u0436\u0434\u043e\u0433\u043e \u043e\u043a\u043d\u0430 m):"),
        f5_sc_m, f5_sc,
        subHeading("\u041f\u043e\u044f\u0441\u043d\u0435\u043d\u0438\u044f \u043f\u0435\u0440\u0435\u043c\u0435\u043d\u043d\u044b\u0445:"),
        param("|| |X_m| \u2212 |Y_m| ||_2", " \u2014 \u0435\u0432\u043a\u043b\u0438\u0434\u043e\u0432\u0430 \u043d\u043e\u0440\u043c\u0430 \u0440\u0430\u0437\u043d\u043e\u0441\u0442\u0438 \u0430\u043c\u043f\u043b\u0438\u0442\u0443\u0434"),
        param("||X_m||_2", " \u2014 L2-\u043d\u043e\u0440\u043c\u0430 \u0430\u043c\u043f\u043b\u0438\u0442\u0443\u0434\u043d\u043e\u0433\u043e \u0441\u043f\u0435\u043a\u0442\u0440\u0430"),

        // === 6. Centroid Difference ===
        metricHeading(6, "Spectral Centroid Difference (\u0420\u0430\u0437\u043d\u0438\u0446\u0430 \u0441\u043f\u0435\u043a\u0442\u0440\u0430\u043b\u044c\u043d\u044b\u0445 \u0446\u0435\u043d\u0442\u0440\u043e\u0438\u0434\u043e\u0432)"),
        body("\u0420\u0430\u0437\u043d\u0438\u0446\u0430 \u00ab\u0446\u0435\u043d\u0442\u0440\u043e\u0432 \u0442\u044f\u0436\u0435\u0441\u0442\u0438\u00bb \u0441\u043f\u0435\u043a\u0442\u0440\u043e\u0432 \u043e\u043f\u043e\u0440\u043d\u043e\u0433\u043e \u0438 \u0442\u0435\u0441\u0442\u043e\u0432\u043e\u0433\u043e \u0441\u0438\u0433\u043d\u0430\u043b\u043e\u0432. \u0421\u043f\u0435\u043a\u0442\u0440\u0430\u043b\u044c\u043d\u044b\u0439 \u0446\u0435\u043d\u0442\u0440\u043e\u0438\u0434 \u043e\u0442\u0440\u0430\u0436\u0430\u0435\u0442 perceived \u00ab\u044f\u0440\u043a\u043e\u0441\u0442\u044c\u00bb \u0437\u0432\u0443\u043a\u0430: \u043d\u0438\u0437\u043a\u0438\u0439 (\u043e\u043a\u043e\u043b\u043e 500\u20132000 \u0413\u0446) \u0434\u043b\u044f \u0431\u0430\u0441\u043e\u0432\u044b\u0445, \u0432\u044b\u0441\u043e\u043a\u0438\u0439 (\u043e\u043a\u043e\u043b\u043e 5000\u201315000 \u0413\u0446) \u0434\u043b\u044f \u044f\u0440\u043a\u0438\u0445. \u0420\u0435\u0441\u0435\u043c\u043f\u043b\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u0442\u0435\u0441\u0442\u0430 \u043a sr_ref \u043f\u0440\u0438 \u043d\u0435\u043e\u0431\u0445\u043e\u0434\u0438\u043c\u043e\u0441\u0442\u0438."),
        italic("\u0424\u0443\u043d\u043a\u0446\u0438\u044f: compute_spectral_centroid_diff_hz(reference, test, sr_ref, sr_test)"),
        italic("\u0415\u0434\u0438\u043d\u0438\u0446\u0430: \u0413\u0446 | \u041d\u0430\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435: \u043d\u0438\u0436\u0435 \u2014 \u043b\u0443\u0447\u0448\u0435"),
        subHeading("\u0424\u043e\u0440\u043c\u0443\u043b\u0430 (\u0434\u043b\u044f \u043a\u0430\u0436\u0434\u043e\u0433\u043e \u043e\u043a\u043d\u0430 m):"),
        f6_cx, f6_cy, f6_diff, f6_sc_diff,
        subHeading("\u041f\u043e\u044f\u0441\u043d\u0435\u043d\u0438\u044f \u043f\u0435\u0440\u0435\u043c\u0435\u043d\u043d\u044b\u0445:"),
        param("k", " \u2014 \u0438\u043d\u0434\u0435\u043a\u0441 \u0447\u0430\u0441\u0442\u043e\u0442\u043d\u043e\u0433\u043e \u0431\u0438\u043d\u0430 (0, 1, 2, ..., K\u22121)"),
        param("\u0394f (df)", " \u2014 \u0447\u0430\u0441\u0442\u043e\u0442\u043d\u043e\u0435 \u0440\u0430\u0437\u0440\u0435\u0448\u0435\u043d\u0438\u0435 = sr / n_fft (\u0413\u0446/\u0431\u0438\u043d)"),
        param("d_m", " \u2014 \u0430\u0431\u0441\u043e\u043b\u044e\u0442\u043d\u0430\u044f \u0440\u0430\u0437\u043d\u0438\u0446\u0430 \u0446\u0435\u043d\u0442\u0440\u043e\u0438\u0434\u043e\u0432"),

        // === 7. Cosine Similarity ===
        metricHeading(7, "Spectral Cosine Similarity (\u041a\u043e\u0441\u0438\u043d\u0443\u0441\u043d\u0430\u044f \u043c\u0435\u0440\u0430 \u0441\u0445\u043e\u0434\u0441\u0442\u0432\u0430)"),
        body("\u041a\u043e\u0441\u0438\u043d\u0443\u0441 \u0443\u0433\u043b\u0430 \u043c\u0435\u0436\u0434\u0443 \u0430\u043c\u043f\u043b\u0438\u0442\u0443\u0434\u043d\u044b\u043c\u0438 \u0432\u0435\u043a\u0442\u043e\u0440\u0430\u043c\u0438 \u0441\u043f\u0435\u043a\u0442\u0440\u043e\u0432. \u0417\u043d\u0430\u0447\u0435\u043d\u0438\u0435 1.0 \u2014 \u0438\u0434\u0435\u043d\u0442\u0438\u0447\u043d\u044b\u0435 \u0441\u043f\u0435\u043a\u0442\u0440\u044b, 0.0 \u2014 \u043e\u0440\u0442\u043e\u0433\u043e\u043d\u0430\u043b\u044c\u043d\u044b\u0435. \u041d\u0435 \u0447\u0443\u0432\u0441\u0442\u0432\u0438\u0442\u0435\u043b\u044c\u043d\u0430 \u043a \u0433\u043b\u043e\u0431\u0430\u043b\u044c\u043d\u043e\u043c\u0443 \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044e \u0430\u043c\u043f\u043b\u0438\u0442\u0443\u0434\u044b. \u0424\u043e\u0440\u043c\u0443\u043b\u0430 \u0430\u043d\u0430\u043b\u043e\u0433\u0438\u0447\u043d\u0430 \u043a\u043e\u0441\u0438\u043d\u0443\u0441\u043d\u043e\u043c\u0443 \u0441\u0445\u043e\u0434\u0441\u0442\u0432\u0443 \u0442\u0435\u043a\u0441\u0442\u043e\u0432 \u0432 NLP."),
        italic("\u0424\u0443\u043d\u043a\u0446\u0438\u044f: compute_spectral_cosine_similarity(reference, test, sr_ref, sr_test)"),
        italic("\u0415\u0434\u0438\u043d\u0438\u0446\u0430: 0\u20131 | \u041d\u0430\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435: \u0432\u044b\u0448\u0435 \u2014 \u043b\u0443\u0447\u0448\u0435"),
        subHeading("\u0424\u043e\u0440\u043c\u0443\u043b\u0430 (\u0434\u043b\u044f \u043a\u0430\u0436\u0434\u043e\u0433\u043e \u043e\u043a\u043d\u0430 m):"),
        f7_cos_m, f7_cos,
        subHeading("\u041f\u043e\u044f\u0441\u043d\u0435\u043d\u0438\u044f \u043f\u0435\u0440\u0435\u043c\u0435\u043d\u043d\u044b\u0445:"),
        param("A_m[k], B_m[k]", " \u2014 \u0430\u043c\u043f\u043b\u0438\u0442\u0443\u0434\u044b \u0441\u043f\u0435\u043a\u0442\u0440\u043e\u0432 \u043e\u043f\u043e\u0440\u043d\u043e\u0433\u043e \u0438 \u0442\u0435\u0441\u0442\u043e\u0432\u043e\u0433\u043e"),
        param("||A_m||", " \u2014 L2-\u043d\u043e\u0440\u043c\u0430 \u0432\u0435\u043a\u0442\u043e\u0440\u0430 \u0430\u043c\u043f\u043b\u0438\u0442\u0443\u0434"),

        // === 8. STOI ===
        metricHeading(8, "STOI (Short-Time Objective Intelligibility Index)"),
        body("\u0418\u043d\u0434\u0435\u043a\u0441 \u0440\u0430\u0437\u0431\u043e\u0440\u0447\u0438\u0432\u043e\u0441\u0442\u0438 \u0440\u0435\u0447\u0438 \u043d\u0430 \u043e\u0441\u043d\u043e\u0432\u0435 \u043a\u0440\u0430\u0442\u043a\u043e\u0432\u0440\u0435\u043c\u0435\u043d\u043d\u044b\u0445 \u0441\u043f\u0435\u043a\u0442\u0440\u0430\u043b\u044c\u043d\u044b\u0445 \u043e\u0433\u0438\u0431\u0430\u044e\u0449\u0438\u0445 \u0432 \u043e\u043a\u0442\u0430\u0432\u043d\u044b\u0445 \u043f\u043e\u043b\u043e\u0441\u0430\u0445 \u0447\u0430\u0441\u0442\u043e\u0442. \u0421\u0440\u0430\u0432\u043d\u0438\u0432\u0430\u0435\u0442 \u043e\u0433\u0438\u0431\u0430\u044e\u0449\u0438\u0435 \u043e\u043f\u043e\u0440\u043d\u043e\u0433\u043e \u0438 \u0442\u0435\u0441\u0442\u043e\u0432\u043e\u0433\u043e \u0441\u0438\u0433\u043d\u0430\u043b\u043e\u0432. \u042f\u0432\u043b\u044f\u0435\u0442\u0441\u044f \u043f\u0440\u0435\u0434\u0438\u043a\u0442\u043e\u0440\u043e\u043c \u0440\u0430\u0437\u0431\u043e\u0440\u0447\u0438\u0432\u043e\u0441\u0442\u0438 \u0440\u0435\u0447\u0438, \u043d\u0435 \u043e\u0431\u0449\u0435\u0433\u043e \u043a\u0430\u0447\u0435\u0441\u0442\u0432\u0430. \u0423\u043f\u0440\u043e\u0449\u0451\u043d\u043d\u0430\u044f \u0432\u0435\u0440\u0441\u0438\u044f: n_fft=256, hop=128, n_bands=8. \u0417\u043d\u0430\u0447\u0435\u043d\u0438\u044f: > 0,75 \u2014 \u0445\u043e\u0440\u043e\u0448\u0430\u044f \u0440\u0430\u0437\u0431\u043e\u0440\u0447\u0438\u0432\u043e\u0441\u0442\u044c, > 0,9 \u2014 \u043e\u0442\u043b\u0438\u0447\u043d\u0430\u044f."),
        italic("\u0424\u0443\u043d\u043a\u0446\u0438\u044f: compute_stoi_simplified(reference, test, sr_ref, sr_test)"),
        italic("\u0415\u0434\u0438\u043d\u0438\u0446\u0430: 0\u20131 | \u041d\u0430\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435: \u0432\u044b\u0448\u0435 \u2014 \u043b\u0443\u0447\u0448\u0435"),
        subHeading("\u0424\u043e\u0440\u043c\u0443\u043b\u0430:"),
        h3("\u041e\u043a\u0442\u0430\u0432\u043d\u044b\u0435 \u043f\u043e\u043b\u043e\u0441\u044b (1/3 \u043e\u043a\u0442\u0430\u0432\u044b):"),
        f8_fc,
        h3("\u041e\u0433\u0438\u0431\u0430\u044e\u0449\u0438\u0435 \u0434\u043b\u044f \u043a\u0430\u0436\u0434\u043e\u0433\u043e \u0444\u0440\u0435\u0439\u043c\u0430 m \u0438 \u043f\u043e\u043b\u043e\u0441\u044b b:"),
        f8_env, f8_env_t,
        h3("\u041a\u043e\u0440\u0440\u0435\u043b\u044f\u0446\u0438\u044f \u041f\u0438\u0440\u0441\u043e\u043d\u0430 \u0434\u043b\u044f \u043a\u0430\u0436\u0434\u043e\u0439 \u043f\u043e\u043b\u043e\u0441\u044b b:"),
        f8_rc,
        h3("\u0418\u0442\u043e\u0433\u043e\u0432\u044b\u0439 STOI:"),
        f8_stoi,
        subHeading("\u041f\u043e\u044f\u0441\u043d\u0435\u043d\u0438\u044f \u043f\u0435\u0440\u0435\u043c\u0435\u043d\u043d\u044b\u0445:"),
        param("f_c[b]", " \u2014 \u0446\u0435\u043d\u0442\u0440\u0430\u043b\u044c\u043d\u0430\u044f \u0447\u0430\u0441\u0442\u043e\u0442\u0430 \u043f\u043e\u043b\u043e\u0441\u044b: f_c = 150 \u00d7 2^(b/3)"),
        param("B", " \u2014 \u0447\u0438\u0441\u043b\u043e \u043e\u043a\u0442\u0430\u0432\u043d\u044b\u0445 \u043f\u043e\u043b\u043e\u0441 (\u0443\u043f\u0440\u043e\u0449\u0451\u043d\u043d\u0430\u044f \u0432\u0435\u0440\u0441\u0438\u044f: 8)"),
        param("r_c", " \u2014 \u043a\u043e\u044d\u0444\u0444\u0438\u0446\u0438\u0435\u043d\u0442 \u043a\u043e\u0440\u0440\u0435\u043b\u044f\u0446\u0438\u0438 \u041f\u0438\u0440\u0441\u043e\u043d\u0430 \u0432 \u043f\u043e\u043b\u043e\u0441\u0435 b"),
        param("clip", " \u043e\u0437\u043d\u0430\u0447\u0430\u0435\u0442, \u0447\u0442\u043e \u043e\u0442\u0440\u0438\u0446\u0430\u0442\u0435\u043b\u044c\u043d\u0430\u044f \u043a\u043e\u0440\u0440\u0435\u043b\u044f\u0446\u0438\u044f \u043f\u0440\u0438\u043d\u0438\u043c\u0430\u0435\u0442 \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435 0, \u0430 \u043d\u0435 \u0441\u0440\u0435\u0434\u043d\u0435\u0435"),

        // === 9. PESQ ===
        metricHeading(9, "PESQ (Perceptual Evaluation of Speech Quality) \u2014 \u043f\u0440\u0438\u0431\u043b\u0438\u0436\u0451\u043d\u043d\u044b\u0439"),
        body("\u041f\u0440\u0438\u0431\u043b\u0438\u0436\u0451\u043d\u043d\u0430\u044f \u043e\u0446\u0435\u043d\u043a\u0430 \u043f\u0435\u0440\u0446\u0435\u043f\u0442\u0438\u0432\u043d\u043e\u0433\u043e \u043a\u0430\u0447\u0435\u0441\u0442\u0432\u0430 \u0440\u0435\u0447\u0438 \u043f\u043e \u0441\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u0443 ITU-T P.862. \u0423\u0447\u0438\u0442\u044b\u0432\u0430\u0435\u0442 \u043f\u0441\u0438\u0445\u043e\u0430\u043a\u0443\u0441\u0442\u0438\u0447\u0435\u0441\u043a\u0438\u0435 \u043e\u0441\u043e\u0431\u0435\u043d\u043d\u043e\u0441\u0442\u0438 \u0441\u043b\u0443\u0445\u0430 \u0447\u0435\u0440\u0435\u0437 A-\u0432\u0437\u0432\u0435\u0448\u0438\u0432\u0430\u043d\u0438\u0435. \u0421\u0438\u0433\u043d\u0430\u043b\u044b \u0440\u0435\u0441\u0435\u043c\u043f\u043b\u0438\u0440\u0443\u044e\u0442\u0441\u044f \u043a 16 \u043a\u0413\u0446. \u042d\u043c\u043f\u0438\u0440\u0438\u0447\u0435\u0441\u043a\u0430\u044f \u0440\u0435\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f (\u043d\u0435 \u043f\u043e\u043b\u043d\u0430\u044f). \u0414\u0438\u0430\u043f\u0430\u0437\u043e\u043d: \u22120,5 \u0434\u043e 4,5 (\u0432\u044b\u0448\u0435 \u2014 \u043b\u0443\u0447\u0448\u0435)."),
        italic("\u0424\u0443\u043d\u043a\u0446\u0438\u044f: compute_pesq_approx(reference, test, sr_ref, sr_test)"),
        italic("\u0415\u0434\u0438\u043d\u0438\u0446\u0430: \u22120,5\u20134,5 | \u041d\u0430\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435: \u0432\u044b\u0448\u0435 \u2014 \u043b\u0443\u0447\u0448\u0435"),
        subHeading("\u0424\u043e\u0440\u043c\u0443\u043b\u0430:"),
        h3("A-\u0432\u0437\u0432\u0435\u0448\u0438\u0432\u0430\u043d\u0438\u0435 (\u0443\u043f\u0440\u043e\u0449\u0451\u043d\u043d\u0430\u044f \u043a\u0440\u0438\u0432\u0430\u044f \u0447\u0430\u0441\u0442\u043e\u0442\u043d\u043e\u0439 \u043a\u043e\u0440\u0440\u0435\u043a\u0446\u0438\u0438):"),
        f9_aw,
        h3("\u0414\u043b\u044f \u043a\u0430\u0436\u0434\u043e\u0433\u043e \u0444\u0440\u0435\u0439\u043c\u0430 m (n_fft=512, hop=256):"),
        f9_diff,
        h3("\u0421\u0440\u0435\u0434\u043d\u0435\u043a\u0432\u0430\u0434\u0440\u0430\u0442\u0438\u0447\u043d\u043e\u0435 \u0438\u0441\u043a\u0430\u0436\u0435\u043d\u0438\u0435:"),
        f9_D,
        h3("\u042d\u043c\u043f\u0438\u0440\u0438\u0447\u0435\u0441\u043a\u0438\u0439 \u043c\u0430\u043f\u043f\u0438\u043d\u0433:"),
        f9_pesq,
        subHeading("\u041f\u043e\u044f\u0441\u043d\u0435\u043d\u0438\u044f \u043f\u0435\u0440\u0435\u043c\u0435\u043d\u043d\u044b\u0445:"),
        param("W(f)", " \u2014 \u0447\u0430\u0441\u0442\u043e\u0442\u043d\u0430\u044f \u043a\u043e\u0440\u0440\u0435\u043a\u0446\u0438\u044f, \u0438\u043c\u0438\u0442\u0438\u0440\u0443\u044e\u0449\u0430\u044f \u043a\u0440\u0438\u0432\u0443\u044e \u0441\u043b\u044b\u0448\u0438\u043c\u043e\u0441\u0442\u0438 (A-\u0432\u0437\u0432\u0435\u0448\u0438\u0432\u0430\u043d\u0438\u0435)"),
        param("12194, 20.6, 107.7, 737.9", " \u2014 \u043a\u043e\u043d\u0441\u0442\u0430\u043d\u0442\u044b \u0441\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u0430 IEC 61672-1"),
        param("diff[k]", " \u2014 \u043b\u043e\u0433\u0430\u0440\u0438\u0444\u043c\u0438\u0447\u0435\u0441\u043a\u0430\u044f \u0440\u0430\u0437\u043d\u0438\u0446\u0430 \u0430\u043c\u043f\u043b\u0438\u0442\u0443\u0434 (\u0432 \u0434\u0435\u0446\u0438\u0431\u0435\u043b\u0430\u0445)"),
        param("k = 3.0", " \u2014 \u044d\u043c\u043f\u0438\u0440\u0438\u0447\u0435\u0441\u043a\u0438\u0439 \u043a\u043e\u044d\u0444\u0444\u0438\u0446\u0438\u0435\u043d\u0442 \u043c\u0430\u043f\u043f\u0438\u043d\u0433\u0430 \u043d\u0430 \u0448\u043a\u0430\u043b\u0443 PESQ"),

        // === 10. MOS ===
        metricHeading(10, "MOS (Mean Opinion Score) \u043d\u0430 \u043e\u0441\u043d\u043e\u0432\u0435 PESQ"),
        body("\u0421\u0440\u0435\u0434\u043d\u044f\u044f \u043e\u0446\u0435\u043d\u043e\u0447\u043d\u0430\u044f \u043e\u0446\u0435\u043d\u043a\u0430 \u043a\u0430\u0447\u0435\u0441\u0442\u0432\u0430, \u043f\u043e\u043b\u0443\u0447\u0435\u043d\u043d\u0430\u044f \u043f\u0440\u0435\u043e\u0431\u0440\u0430\u0437\u043e\u0432\u0430\u043d\u0438\u0435\u043c PESQ \u043f\u043e \u0444\u043e\u0440\u043c\u0443\u043b\u0435 ITU-T P.862.1. \u0428\u043a\u0430\u043b\u0430 MOS \u0441\u043e\u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0443\u0435\u0442 \u0441\u0443\u0431\u044a\u0435\u043a\u0442\u0438\u0432\u043d\u043e\u0439 \u043e\u0446\u0435\u043d\u043a\u0435 \u0441\u043b\u0443\u0448\u0430\u0442\u0435\u043b\u0435\u0439. \u0424\u043e\u0440\u043c\u0443\u043b\u0430 \u043f\u0440\u0435\u0434\u0441\u0442\u0430\u0432\u043b\u044f\u0435\u0442 \u0441\u043e\u0431\u043e\u0439 \u043b\u043e\u0433\u0438\u0441\u0442\u0438\u0447\u0435\u0441\u043a\u0443\u044e \u043a\u0440\u0438\u0432\u0443\u044e (\u0441\u0438\u0433\u043c\u043e\u0438\u0434\u0443) \u0441 \u0434\u0438\u0430\u043f\u0430\u0437\u043e\u043d\u043e\u043c [1, 4.87]."),
        italic("\u0424\u0443\u043d\u043a\u0446\u0438\u044f: compute_pesq_mos(reference, test, sr_ref, sr_test)"),
        italic("\u0415\u0434\u0438\u043d\u0438\u0446\u0430: 1\u20135 | \u041d\u0430\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u0435: \u0432\u044b\u0448\u0435 \u2014 \u043b\u0443\u0447\u0448\u0435"),
        subHeading("\u0424\u043e\u0440\u043c\u0443\u043b\u0430:"),
        f10_mos,
        subHeading("\u041f\u043e\u044f\u0441\u043d\u0435\u043d\u0438\u044f \u043f\u0435\u0440\u0435\u043c\u0435\u043d\u043d\u044b\u0445:"),
        param("PESQ", " \u2014 \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435, \u043f\u043e\u043b\u0443\u0447\u0435\u043d\u043d\u043e\u0435 \u0438\u0437 compute_pesq_approx()"),
        param("1.3669, 0.7197, 3.87", " \u2014 \u044d\u043c\u043f\u0438\u0440\u0438\u0447\u0435\u0441\u043a\u0438\u0435 \u043a\u043e\u043d\u0441\u0442\u0430\u043d\u0442\u044b \u0438\u0437 \u0441\u0442\u0430\u043d\u0434\u0430\u0440\u0442\u0430 ITU-T P.862.1"),
        body("\u0428\u043a\u0430\u043b\u0430 \u043e\u0446\u0435\u043d\u043a\u0438 MOS: 5 \u2014 \u041e\u0442\u043b\u0438\u0447\u043d\u043e (\u043d\u0435\u043e\u0442\u043b\u0438\u0447\u0438\u043c\u043e \u043e\u0442 \u043e\u0440\u0438\u0433\u0438\u043d\u0430\u043b\u0430), 4 \u2014 \u0425\u043e\u0440\u043e\u0448\u043e (\u0437\u0430\u043c\u0435\u0442\u043d\u044b\u0435, \u043d\u043e \u043d\u0435 \u043c\u0435\u0448\u0430\u044e\u0449\u0438\u0435 \u0438\u0441\u043a\u0430\u0436\u0435\u043d\u0438\u044f), 3 \u2014 \u0423\u0434\u043e\u0432\u043b\u0435\u0442\u0432\u043e\u0440\u0438\u0442\u0435\u043b\u044c\u043d\u043e (\u0437\u0430\u043c\u0435\u0442\u043d\u044b\u0435 \u0438\u0441\u043a\u0430\u0436\u0435\u043d\u0438\u044f), 2 \u2014 \u041f\u043b\u043e\u0445\u043e (\u0441\u0443\u0449\u0435\u0441\u0442\u0432\u0435\u043d\u043d\u044b\u0435 \u0438\u0441\u043a\u0430\u0436\u0435\u043d\u0438\u044f), 1 \u2014 \u041d\u0435\u043f\u0440\u0438\u0435\u043c\u043b\u0435\u043c\u043e.", { noIndent: true }),

        // === 11. Score ===
        metricHeading(11, "\u0410\u0433\u0440\u0435\u0433\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u044b\u0439 Score (\u0438\u043d\u0442\u0435\u0433\u0440\u0430\u043b\u044c\u043d\u0430\u044f \u043e\u0446\u0435\u043d\u043a\u0430)"),
        body("\u0412\u0437\u0432\u0435\u0448\u0435\u043d\u043d\u0430\u044f \u0441\u0443\u043c\u043c\u0430 \u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u043d\u043d\u044b\u0445 \u043c\u0435\u0442\u0440\u0438\u043a. \u0412\u0441\u0435 \u043c\u0435\u0442\u0440\u0438\u043a\u0438 \u0441\u043d\u0430\u0447\u0430\u043b\u0430 \u043f\u0440\u0438\u0432\u043e\u0434\u044f\u0442\u0441\u044f \u043a \u0435\u0434\u0438\u043d\u043e\u0439 \u0448\u043a\u0430\u043b\u0435 [0, 1] \u0441 \u043f\u043e\u043c\u043e\u0449\u044c\u044e min-max \u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u0438, \u0437\u0430\u0442\u0435\u043c \u0441\u043a\u043b\u0430\u0434\u044b\u0432\u0430\u044e\u0442\u0441\u044f \u0441 \u0432\u0435\u0441\u0430\u043c\u0438. \u0427\u0435\u043c \u0432\u044b\u0448\u0435 Score, \u0442\u0435\u043c \u043b\u0443\u0447\u0448\u0435 \u043c\u0435\u0442\u043e\u0434 \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438. \u0424\u0443\u043d\u043a\u0446\u0438\u044f: compute_metrics_batch(...)."),

        h3("11.1. Min-Max \u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f (\u0434\u043b\u044f \u043c\u0435\u0442\u0440\u0438\u043a \u00ab\u043d\u0438\u0436\u0435 \u2014 \u043b\u0443\u0447\u0448\u0435\u00bb):"),
        f11_norm_inv,
        body("\u0418\u043d\u0432\u0435\u0440\u0441\u0438\u044f: \u043d\u0430\u0438\u043b\u0443\u0447\u0448\u0435\u0435 (\u043c\u0438\u043d\u0438\u043c\u0430\u043b\u044c\u043d\u043e\u0435) \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435 \u043f\u043e\u043b\u0443\u0447\u0430\u0435\u0442 \u043d\u043e\u0440\u043c\u0443 1.0.", { noIndent: true }),

        h3("11.2. Min-Max \u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f (\u0434\u043b\u044f \u043c\u0435\u0442\u0440\u0438\u043a \u00ab\u0432\u044b\u0448\u0435 \u2014 \u043b\u0443\u0447\u0448\u0435\u00bb):"),
        f11_norm_dir,
        body("\u041d\u0430\u0438\u043b\u0443\u0447\u0448\u0435\u0435 (\u043c\u0430\u043a\u0441\u0438\u043c\u0430\u043b\u044c\u043d\u043e\u0435) \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435 \u043f\u043e\u043b\u0443\u0447\u0430\u0435\u0442 \u043d\u043e\u0440\u043c\u0443 1.0.", { noIndent: true }),
        param("min, max", " \u2014 \u043c\u0438\u043d\u0438\u043c\u0430\u043b\u044c\u043d\u043e\u0435 \u0438 \u043c\u0430\u043a\u0441\u0438\u043c\u0430\u043b\u044c\u043d\u043e\u0435 \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u044f \u043c\u0435\u0442\u0440\u0438\u043a\u0438 \u0441\u0440\u0435\u0434\u0438 \u0432\u0441\u0435\u0445 \u0441\u0440\u0430\u0432\u043d\u0438\u0432\u0430\u0435\u043c\u044b\u0445 \u043c\u0435\u0442\u043e\u0434\u043e\u0432"),
        param("\u03b5", " \u2014 \u0437\u0430\u0449\u0438\u0442\u0430 \u043e\u0442 \u0434\u0435\u043b\u0435\u043d\u0438\u044f \u043d\u0430 \u043d\u043e\u043b\u044c (1\u00d710\u207b\u00b9\u00b2)"),

        h3("11.3. \u0412\u0437\u0432\u0435\u0448\u0435\u043d\u043d\u0430\u044f \u0441\u0443\u043c\u043c\u0430:"),
        f11_score,
        body("\u0422\u0430\u0431\u043b\u0438\u0446\u0430 \u0432\u0435\u0441\u043e\u0432 \u043c\u0435\u0442\u0440\u0438\u043a:", { noIndent: true }),
        weightsTable,
      ],
    },
  ],
});

// ============================================================
// Generate
// ============================================================
(async () => {
  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync(OUT, buffer);
  console.log(`DOCX saved: ${OUT} (${buffer.length} bytes)`);
})().catch(err => {
  console.error("Error:", err);
  process.exit(1);
});

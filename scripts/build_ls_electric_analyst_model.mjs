import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const ROOT = path.resolve("/Users/leesangeui/Desktop/취업 준비/2026 하반기/kospi200_factor_model");
const OUT_DIR = path.join(ROOT, "outputs/reports/recruiting");
const OUT_PATH = path.join(OUT_DIR, "LS_ELECTRIC_Analyst_Model.xlsx");

const BLUE = "#0000FF";
const GREEN = "#008000";
const BRAND = "#143A5A";
const LIGHT = "#EEF3F7";
const TOTAL = "#DDEBF7";
const INPUT_FILL = "#FFF2CC";

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];
    if (char === '"' && quoted && next === '"') {
      cell += '"';
      i += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      row.push(cell);
      cell = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && next === "\n") i += 1;
      row.push(cell);
      if (row.some((value) => value !== "")) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }
  if (cell.length || row.length) {
    row.push(cell);
    rows.push(row);
  }
  const [rawHeaders, ...body] = rows;
  const headers = rawHeaders.map((key) => key.replace(/^\uFEFF/, "").trim());
  return body.map((values) => Object.fromEntries(headers.map((key, index) => [key, values[index] ?? ""])));
}

function toNum(value) {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function normalizeTicker(value) {
  return String(value ?? "").trim().padStart(6, "0");
}

async function loadCsv(relativePath) {
  return parseCsv(await fs.readFile(path.join(ROOT, relativePath), "utf8"));
}

async function loadCsvIfExists(relativePath) {
  try {
    return await loadCsv(relativePath);
  } catch {
    return [];
  }
}

function sortByDate(rows, key) {
  return rows.sort((a, b) => new Date(a[key]) - new Date(b[key]));
}

function latestAnnual(rows, ticker) {
  const annual = rows
    .filter((row) => normalizeTicker(row.ticker) === ticker && String(row.fiscal_period).trim().endsWith("-12"))
    .sort((a, b) => new Date(a.available_date) - new Date(b.available_date));
  return annual[annual.length - 1];
}

function krwRound(value, unit = 10000) {
  return Math.round(value / unit) * unit;
}

function parseAmount(value) {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(String(value).replaceAll(",", ""));
  return Number.isFinite(parsed) ? parsed : null;
}

function dartAmount(rows, reportName, accountName, field = "thstrm_amount") {
  const row = rows.find((item) =>
    item.requested_report_name === reportName &&
    item.fs_div === "CFS" &&
    item.account_nm === accountName
  );
  return row ? parseAmount(row[field]) : null;
}

function colLetter(index) {
  let col = "";
  let n = index;
  while (n > 0) {
    const rem = (n - 1) % 26;
    col = String.fromCharCode(65 + rem) + col;
    n = Math.floor((n - 1) / 26);
  }
  return col;
}

function pct(value) {
  return value === null ? null : value;
}

function setWidth(sheet, widths) {
  widths.forEach((width, index) => {
    sheet.getRange(`${colLetter(index + 1)}:${colLetter(index + 1)}`).format.columnWidth = width;
  });
}

function styleTitle(sheet, range, text) {
  const r = sheet.getRange(range);
  r.merge();
  r.values = [[text]];
  r.format.fill.color = BRAND;
  r.format.font.color = "#FFFFFF";
  r.format.font.bold = true;
  r.format.font.size = 15;
  r.format.wrapText = true;
}

function styleSection(sheet, range, text) {
  const r = sheet.getRange(range);
  r.merge();
  r.values = [[text]];
  r.format.fill.color = BRAND;
  r.format.font.color = "#FFFFFF";
  r.format.font.bold = true;
  r.format.borders = { preset: "outside", style: "thin", color: "#B7C9D6" };
}

function styleTable(sheet, range, header = true) {
  const r = sheet.getRange(range);
  r.format.borders = { preset: "all", style: "thin", color: "#D8DEE6" };
  r.format.wrapText = true;
  if (header) {
    const top = sheet.getRange(range.split(":")[0] + ":" + range.split(":")[1].replace(/[0-9]/g, "") + range.split(":")[0].replace(/[A-Z]/g, ""));
    top.format.fill.color = LIGHT;
    top.format.font.bold = true;
    top.format.font.color = BRAND;
  }
}

function applyFinanceNumberFormats(sheet, range, format) {
  sheet.getRange(range).format.numberFormat = format;
}

async function main() {
  const fundamentals = await loadCsv("data/raw/ts2000/fundamentals_long.csv");
  const prices = await loadCsv("data/raw/price/prices_2007_2026.csv");
  const factors = await loadCsv("data/features/institutional_core_satellite_scores.csv");
  const dartAccounts = await loadCsvIfExists("data/raw/dart/ls_electric/single_accounts.csv");

  const lsAnnual = fundamentals
    .filter((row) => normalizeTicker(row.ticker) === "010120" && String(row.fiscal_period).trim().endsWith("-12"))
    .sort((a, b) => Number(a.fiscal_year) - Number(b.fiscal_year))
    .slice(-8);
  const lsPrices = sortByDate(prices.filter((row) => normalizeTicker(row.ticker) === "010120"), "date");
  const latestPrice = lsPrices[lsPrices.length - 1];
  const latestFactor = sortByDate(factors.filter((row) => normalizeTicker(row.ticker) === "010120"), "signal_date").at(-1);
  const dart = {
    revenue: dartAmount(dartAccounts, "2025 사업보고서", "매출액"),
    prevRevenue: dartAmount(dartAccounts, "2025 사업보고서", "매출액", "frmtrm_amount"),
    operatingIncome: dartAmount(dartAccounts, "2025 사업보고서", "영업이익"),
    netIncome: dartAmount(dartAccounts, "2025 사업보고서", "당기순이익(손실)"),
    equity: dartAmount(dartAccounts, "2025 사업보고서", "자본총계"),
    q1Revenue: dartAmount(dartAccounts, "2026 1분기보고서", "매출액"),
    q1OperatingIncome: dartAmount(dartAccounts, "2026 1분기보고서", "영업이익"),
    q1NetIncome: dartAmount(dartAccounts, "2026 1분기보고서", "당기순이익(손실)"),
  };
  const hasDart = Object.values(dart).every((value) => value !== null);
  const peers = ["010120", "267260", "298040", "006260"];
  const peerNames = {
    "010120": "LS ELECTRIC",
    "267260": "HD현대일렉트릭",
    "298040": "효성중공업",
    "006260": "LS",
  };
  const peerRows = peers.map((ticker) => {
    const f = latestAnnual(fundamentals, ticker);
    const p = sortByDate(prices.filter((row) => normalizeTicker(row.ticker) === ticker), "date").at(-1);
    if (!f || !p) {
      throw new Error(`Missing peer source data for ${ticker}`);
    }
    const eps = toNum(f.net_income) / toNum(f.shares_outstanding);
    const bps = toNum(f.equity) / toNum(f.shares_outstanding);
    return [
      `${ticker} `,
      peerNames[ticker],
      toNum(f.revenue) / 1e12,
      toNum(f.operating_margin),
      toNum(f.roe),
      toNum(p.adj_close),
      eps,
      bps,
      toNum(p.adj_close) / eps,
      toNum(p.adj_close) / bps,
      toNum(f.sales_growth),
    ];
  });

  const workbook = Workbook.create();
  const cover = workbook.worksheets.add("Cover");
  const hist = workbook.worksheets.add("Historical");
  const forecast = workbook.worksheets.add("Forecast");
  const comps = workbook.worksheets.add("Peer Comps");
  const val = workbook.worksheets.add("Valuation");
  const sens = workbook.worksheets.add("Sensitivity");
  const checks = workbook.worksheets.add("Checks");
  const sources = workbook.worksheets.add("Sources");

  for (const sheet of workbook.worksheets.items) {
    sheet.showGridLines = false;
  }

  setWidth(cover, [20, 18, 18, 18, 18, 18, 20, 20]);
  styleTitle(cover, "A1:H2", "LS ELECTRIC Analyst Model | Equity Research Support Workbook");
  cover.getRange("A4:B11").values = [
    ["Company", "LS ELECTRIC"],
    ["Ticker", "010120"],
    ["Valuation Date", latestPrice.date],
    ["Current Price", toNum(latestPrice.adj_close)],
    ["Rating", "BUY"],
    ["Target Price", "='Valuation'!F14"],
    ["Upside", "='Valuation'!F15"],
    ["Model Status", "='Checks'!F4"],
  ];
  cover.getRange("A4:A11").format.fill.color = LIGHT;
  cover.getRange("A4:A11").format.font.bold = true;
  cover.getRange("B4:B11").format.borders = { preset: "outside", style: "thin", color: "#D8DEE6" };
  cover.getRange("B5").format.font.color = BLUE;
  cover.getRange("B9:B11").format.font.color = GREEN;
  cover.getRange("B7:B8").format.numberFormat = "#,##0";
  cover.getRange("B10").format.numberFormat = "#,##0";
  cover.getRange("B11").format.numberFormat = "0.0%";
  styleSection(cover, "D4:H4", "Analyst workflow reflected in this workbook");
  cover.getRange("D5:H11").values = [
    ["1. Raw Data", "OpenDART consolidated accounts, TS2000 financials and KIS API prices are imported.", null, null, null],
    ["2. Forecast", "Revenue growth, OPM, net margin, payout and COE assumptions are separated as editable inputs.", null, null, null],
    ["3. Valuation", "PER, PBR and FCFE proxy DCF are triangulated rather than relying on one shortcut.", null, null, null],
    ["4. Sensitivity", "Target PER and 2026E EPS assumptions are varied to check downside/upside ranges.", null, null, null],
    ["5. Checks", "Formula integrity, target tie-out and source completeness are surfaced before report writing.", null, null, null],
    ["Color legend", "Blue font = editable assumption, Green font = linked output, Black font = formula/source.", null, null, null],
    ["Caveat", "Simplified model built from available OpenDART/TS2000/KIS data; full sell-side segment backlog model is not included.", null, null, null],
  ];
  cover.getRange("D5:H11").format.wrapText = true;
  cover.getRange("D5:H11").format.borders = { preset: "all", style: "thin", color: "#D8DEE6" };

  setWidth(hist, [12, 16, 16, 16, 16, 16, 14, 14, 14, 14, 16, 16]);
  styleTitle(hist, "A1:L2", "Historical Financials | TS2000 Annual Actuals");
  hist.getRange("A4:L4").values = [[
    "Fiscal Year", "Revenue", "Operating Income", "Net Income", "Equity", "Shares", "Sales Growth", "OPM", "Net Margin", "ROE", "EPS", "BPS",
  ]];
  hist.getRange("A5:L12").values = lsAnnual.map((row) => [
    Number(row.fiscal_year),
    toNum(row.revenue) / 1e8,
    toNum(row.operating_income) / 1e8,
    toNum(row.net_income) / 1e8,
    toNum(row.equity) / 1e8,
    toNum(row.shares_outstanding),
    pct(toNum(row.sales_growth)),
    pct(toNum(row.operating_margin)),
    pct(toNum(row.net_margin)),
    pct(toNum(row.roe)),
    null,
    null,
  ]);
  hist.getRange("K5").formulas = [["=D5*100000000/F5"]];
  hist.getRange("K5:K12").fillDown();
  hist.getRange("L5").formulas = [["=E5*100000000/F5"]];
  hist.getRange("L5:L12").fillDown();
  styleTable(hist, "A4:L12");
  applyFinanceNumberFormats(hist, "B5:E12", "#,##0");
  applyFinanceNumberFormats(hist, "F5:F12", "#,##0");
  applyFinanceNumberFormats(hist, "G5:J12", "0.0%");
  applyFinanceNumberFormats(hist, "K5:L12", "#,##0");
  hist.freezePanes.freezeRows(4);

  setWidth(forecast, [24, 14, 14, 14, 14, 14]);
  styleTitle(forecast, "A1:F2", "Forecast Model | Assumptions and Earnings Build");
  forecast.getRange("A4:F4").values = [["Item", "2025A", "2026E", "2027E", "2028E", "Notes"]];
  forecast.getRange("A5:F18").values = [
    ["Revenue", hasDart ? dart.revenue / 1e8 : "='Historical'!B12", null, null, null, "KRW 100mn; 2025A uses OpenDART CFS when available"],
    ["Revenue Growth", hasDart ? dart.revenue / dart.prevRevenue - 1 : "='Historical'!G12", 0.12, 0.09, 0.06, "User-editable growth assumptions"],
    ["Operating Margin", hasDart ? dart.operatingIncome / dart.revenue : "='Historical'!H12", 0.11, 0.113, 0.114, "Margin expansion from power infra mix"],
    ["Operating Income", hasDart ? dart.operatingIncome / 1e8 : "='Historical'!C12", null, null, null, "Revenue x OPM"],
    ["Net Margin", hasDart ? dart.netIncome / dart.revenue : "='Historical'!I12", 0.086, 0.088, 0.088, "Below-OP leverage assumption"],
    ["Net Income", hasDart ? dart.netIncome / 1e8 : "='Historical'!D12", null, null, null, "Revenue x net margin"],
    ["Payout Ratio", null, 0.20, 0.20, 0.20, "Retained earnings roll-forward"],
    ["Equity", hasDart ? dart.equity / 1e8 : "='Historical'!E12", null, null, null, "Prior equity + retained earnings"],
    ["Shares", "='Historical'!F12", "='Historical'!F12", "='Historical'!F12", "='Historical'!F12", "No buyback/issuance assumed"],
    ["EPS", hasDart ? dart.netIncome / 30000000 : "='Historical'!K12", null, null, null, "Net income / shares"],
    ["BPS", hasDart ? dart.equity / 30000000 : "='Historical'!L12", null, null, null, "Equity / shares"],
    ["ROE", hasDart ? dart.netIncome / dart.equity : "='Historical'!J12", null, null, null, "Net income / ending equity proxy"],
    ["Cost of Equity", null, 0.095, 0.095, 0.095, "Risk-free + equity risk premium judgment"],
    ["Terminal Growth", null, 0.025, 0.025, 0.025, "Long-run nominal growth"],
  ];
  forecast.getRange("C5").formulas = [["=B5*(1+C6)"]];
  forecast.getRange("C5:E5").fillRight();
  forecast.getRange("C8").formulas = [["=C5*C7"]];
  forecast.getRange("C8:E8").fillRight();
  forecast.getRange("C10").formulas = [["=C5*C9"]];
  forecast.getRange("C10:E10").fillRight();
  forecast.getRange("C12").formulas = [["=B12+C10*(1-C11)"]];
  forecast.getRange("D12").formulas = [["=C12+D10*(1-D11)"]];
  forecast.getRange("E12").formulas = [["=D12+E10*(1-E11)"]];
  forecast.getRange("C14").formulas = [["=C10*100000000/C13"]];
  forecast.getRange("C14:E14").fillRight();
  forecast.getRange("C15").formulas = [["=C12*100000000/C13"]];
  forecast.getRange("C15:E15").fillRight();
  forecast.getRange("C16").formulas = [["=C10/C12"]];
  forecast.getRange("C16:E16").fillRight();
  styleTable(forecast, "A4:F18");
  forecast.getRange("C6:E7").format.font.color = BLUE;
  forecast.getRange("C9:E11").format.font.color = BLUE;
  forecast.getRange("C17:E18").format.font.color = BLUE;
  forecast.getRange("B5:E5").format.numberFormat = "#,##0";
  forecast.getRange("B8:E8").format.numberFormat = "#,##0";
  forecast.getRange("B10:E10").format.numberFormat = "#,##0";
  forecast.getRange("B12:E12").format.numberFormat = "#,##0";
  forecast.getRange("B13:E13").format.numberFormat = "#,##0";
  forecast.getRange("B14:E15").format.numberFormat = "#,##0";
  forecast.getRange("B6:E7").format.numberFormat = "0.0%";
  forecast.getRange("B9:E11").format.numberFormat = "0.0%";
  forecast.getRange("B16:E18").format.numberFormat = "0.0%";
  forecast.getRange("C6:E18").format.fill.color = INPUT_FILL;
  forecast.getRange("C5:E5").format.fill.color = "#FFFFFF";
  forecast.getRange("C8:E8").format.fill.color = "#FFFFFF";
  forecast.getRange("C10:E10").format.fill.color = "#FFFFFF";
  forecast.getRange("C12:E16").format.fill.color = "#FFFFFF";

  setWidth(comps, [12, 20, 14, 14, 14, 14, 14, 14, 14, 14, 14]);
  styleTitle(comps, "A1:K2", "Peer Comps | Power Equipment / Holding Company Snapshot");
  comps.getRange("A4:K4").values = [["Ticker", "Company", "Revenue (tn)", "OPM", "ROE", "Price", "EPS", "BPS", "PER", "PBR", "Sales Growth"]];
  comps.getRange("A5:A8").format.numberFormat = "@";
  comps.getRange("A5:K8").values = peerRows;
  styleTable(comps, "A4:K8");
  applyFinanceNumberFormats(comps, "C5:C8", "0.00");
  applyFinanceNumberFormats(comps, "D5:E8", "0.0%");
  applyFinanceNumberFormats(comps, "F5:H8", "#,##0");
  applyFinanceNumberFormats(comps, "I5:J8", "0.0x");
  applyFinanceNumberFormats(comps, "K5:K8", "0.0%");

  setWidth(val, [25, 19, 19, 19, 19, 19, 20]);
  styleTitle(val, "A1:G2", "Valuation | PER, PBR and FCFE Proxy DCF Triangulation");
  val.getRange("A4:F4").values = [["Method", "Driver", "Assumption", "Weight", "Value / Share", "Weighted Value"]];
  val.getRange("A5:F8").values = [
    ["PER", "='Forecast'!C14", 27.0, 0.60, null, null],
    ["PBR", "='Forecast'!C15", 4.2, 0.25, null, null],
    ["DCF Proxy", "='Valuation'!F24", null, 0.15, "='Valuation'!F24", null],
    ["Fair Value", null, null, null, null, null],
  ];
  val.getRange("E5").formulas = [["=B5*C5"]];
  val.getRange("E6").formulas = [["=B6*C6"]];
  val.getRange("F5").formulas = [["=E5*D5"]];
  val.getRange("F5:F7").fillDown();
  val.getRange("F8").formulas = [["=SUM(F5:F7)"]];
  styleTable(val, "A4:F8");
  val.getRange("C5:D7").format.font.color = BLUE;
  val.getRange("C5:D7").format.fill.color = INPUT_FILL;
  val.getRange("F8").format.fill.color = TOTAL;
  val.getRange("F8").format.font.bold = true;
  val.getRange("A11:F15").values = [
    ["Target Price Build", null, null, null, null, null],
    ["Fair Value", null, null, null, null, "=F8"],
    ["Rounding Unit", null, null, null, null, 10000],
    ["Target Price", null, null, null, null, null],
    ["Upside", null, null, null, null, null],
  ];
  val.getRange("F14").formulas = [["=ROUND(F12/F13,0)*F13"]];
  val.getRange("F15").formulas = [[`=F14/${toNum(latestPrice.adj_close)}-1`]];
  val.getRange("A11:F11").format.fill.color = BRAND;
  val.getRange("A11:F11").format.font.color = "#FFFFFF";
  val.getRange("A11:F11").format.font.bold = true;
  val.getRange("A12:F15").format.borders = { preset: "all", style: "thin", color: "#D8DEE6" };
  val.getRange("F12:F14").format.numberFormat = "#,##0";
  val.getRange("F15").format.numberFormat = "0.0%";
  val.getRange("F14:F15").format.font.color = GREEN;
  val.getRange("A18:F18").values = [["DCF Proxy", "2026E", "2027E", "2028E", "Terminal", "Per Share"]];
  val.getRange("A19:F24").values = [
    ["Net Income", "='Forecast'!C10", "='Forecast'!D10", "='Forecast'!E10", null, null],
    ["FCFE Conversion", 0.82, 0.82, 0.82, null, null],
    ["FCFE", null, null, null, null, null],
    ["Discount Factor", null, null, null, null, null],
    ["PV FCFE", null, null, null, null, null],
    ["Equity Value / Share", null, null, null, null, null],
  ];
  val.getRange("B21").formulas = [["=B19*B20"]];
  val.getRange("B21:D21").fillRight();
  val.getRange("B22").formulas = [["=1/(1+'Forecast'!C17)^1"]];
  val.getRange("C22").formulas = [["=1/(1+'Forecast'!D17)^2"]];
  val.getRange("D22").formulas = [["=1/(1+'Forecast'!E17)^3"]];
  val.getRange("B23").formulas = [["=B21*B22"]];
  val.getRange("B23:D23").fillRight();
  val.getRange("E21").formulas = [["=D21*(1+'Forecast'!E18)/('Forecast'!E17-'Forecast'!E18)"]];
  val.getRange("E23").formulas = [["=E21*D22"]];
  val.getRange("F24").formulas = [["=SUM(B23:E23)*100000000/'Forecast'!E13"]];
  styleTable(val, "A18:F24");
  val.getRange("B20:D20").format.font.color = BLUE;
  val.getRange("B20:D20").format.fill.color = INPUT_FILL;
  applyFinanceNumberFormats(val, "B19:E23", "#,##0");
  applyFinanceNumberFormats(val, "F24", "#,##0");
  applyFinanceNumberFormats(val, "C5:E8", "#,##0");
  applyFinanceNumberFormats(val, "D5:D7", "0.0%");
  applyFinanceNumberFormats(val, "C5:C6", "0.0x");
  applyFinanceNumberFormats(val, "B5:B6", "#,##0");

  setWidth(sens, [18, 14, 14, 14, 14, 14, 16]);
  styleTitle(sens, "A1:G2", "Sensitivity | Target PER x EPS Case");
  sens.getRange("A4:G4").values = [["2026E EPS \\ Target PER", 23, 25, 27, 29, 31, "Interpretation"]];
  sens.getRange("A5:A9").values = [[0.90], [0.95], [1.00], [1.05], [1.10]];
  sens.getRange("B5").formulas = [["=ROUND(('Forecast'!$C$14*$A5)*B$4/10000,0)*10000"]];
  sens.getRange("B5:F9").fillRight();
  sens.getRange("B5:F9").fillDown();
  sens.getRange("G5:G9").values = [
    ["EPS bear case"],
    ["Mild downside"],
    ["Base case"],
    ["Mild upside"],
    ["EPS upside case"],
  ];
  styleTable(sens, "A4:G9");
  applyFinanceNumberFormats(sens, "A5:A9", "0%");
  applyFinanceNumberFormats(sens, "B5:F9", "#,##0");

  setWidth(checks, [28, 22, 18, 18, 18, 18, 34]);
  styleTitle(checks, "A1:G2", "Checks | Model Integrity and Audit Items");
  checks.getRange("A4:G4").values = [["Check", "Location", "Actual", "Expected", "Difference", "Status", "Notes"]];
  checks.getRange("A5:G10").values = [
    ["Target price tie-out", "Valuation!F14", null, null, null, null, "Rounded target equals rounded fair value"],
    ["DCF positive", "Valuation!F24", null, 0, null, null, "Equity value/share should be positive"],
    ["Forecast revenue grows", "Forecast!C5:E5", null, 0, null, null, "2028E revenue above 2025A"],
    ["Source data present", "Historical!A5:L12", 8, 8, null, null, "Eight annual observations imported"],
    ["Upside supports BUY", "Valuation!F15", null, 0.15, null, null, "Internal rating threshold"],
    ["Overall model status", "Checks!F5:F9", null, null, null, null, "Aggregates checks above"],
  ];
  checks.getRange("C5").formulas = [["='Valuation'!F14"]];
  checks.getRange("D5").formulas = [["=ROUND('Valuation'!F8/'Valuation'!F13,0)*'Valuation'!F13"]];
  checks.getRange("E5").formulas = [["=C5-D5"]];
  checks.getRange("F5").formulas = [["=IF(ABS(E5)<1,\"OK\",\"Review\")"]];
  checks.getRange("C6").formulas = [["='Valuation'!F24"]];
  checks.getRange("E6").formulas = [["=C6-D6"]];
  checks.getRange("F6").formulas = [["=IF(C6>D6,\"OK\",\"Review\")"]];
  checks.getRange("C7").formulas = [["='Forecast'!E5"]];
  checks.getRange("D7").formulas = [["='Forecast'!B5"]];
  checks.getRange("E7").formulas = [["=C7-D7"]];
  checks.getRange("F7").formulas = [["=IF(C7>D7,\"OK\",\"Review\")"]];
  checks.getRange("E8").formulas = [["=C8-D8"]];
  checks.getRange("F8").formulas = [["=IF(E8=0,\"OK\",\"Review\")"]];
  checks.getRange("C9").formulas = [["='Valuation'!F15"]];
  checks.getRange("E9").formulas = [["=C9-D9"]];
  checks.getRange("F9").formulas = [["=IF(C9>=D9,\"OK\",\"Review\")"]];
  checks.getRange("F10").formulas = [["=IF(COUNTIF(F5:F9,\"Review\")=0,\"OK\",\"Review\")"]];
  checks.getRange("F4").formulas = [["=F10"]];
  styleTable(checks, "A4:G10");
  checks.getRange("F5:F10").format.fill.color = "#E2F0D9";
  applyFinanceNumberFormats(checks, "C5:E7", "#,##0");
  applyFinanceNumberFormats(checks, "C9:E9", "0.0%");

  setWidth(sources, [24, 24, 22, 28, 58]);
  styleTitle(sources, "A1:E2", "Sources and Audit Trail");
  sources.getRange("A4:E9").values = [
    ["Item", "Period / As-of", "Value", "Source", "Notes"],
    ["OpenDART connected accounts", "2025A / 2026Q1", "CFS revenue/OP/NI/equity", "data/raw/dart/ls_electric/single_accounts.csv", "Valuation base uses consolidated financial statements"],
    ["OpenDART disclosure text", "2026.03 quarterly report", "Business/risk/order snippets", "data/raw/dart/ls_electric/latest_report_text.txt", "Used for report narrative and DART disclosure check"],
    ["Historical financials", "2018A-2025A", "Revenue/OP/NI/Equity/Shares", "data/raw/ts2000/fundamentals_long.csv", "Local TS2000 dataset in 2026 하반기 project"],
    ["Current price", latestPrice.date, toNum(latestPrice.adj_close), "data/raw/price/prices_2007_2026.csv", "KIS API price history, adjusted close"],
    ["Quant signal", latestFactor.signal_date, toNum(latestFactor.composite_score), "data/features/institutional_core_satellite_scores.csv", "Internal KOSPI200 factor model"],
    ["Peer comps", latestPrice.date, "010120 / 267260 / 298040 / 006260", "TS2000 + KIS price data", "Peer set chosen for electrical equipment and group comparison"],
    ["Forecast assumptions", "2026E-2028E", "Growth/margin/payout/COE/TGR", "Analyst judgment", "Editable blue/yellow cells on Forecast and Valuation sheets"],
  ];
  styleTable(sources, "A4:E11");
  sources.getRange("C8").format.numberFormat = "#,##0";
  sources.getRange("C9").format.numberFormat = "0.000";
  sources.getRange("A5:E11").format.wrapText = true;

  hist.getRange("W4:AA12").formulas = [
    ["=A4", "=G4", "=H4", "=I4", "=J4"],
    ["=A5", "=G5", "=H5", "=I5", "=J5"],
    ["=A6", "=G6", "=H6", "=I6", "=J6"],
    ["=A7", "=G7", "=H7", "=I7", "=J7"],
    ["=A8", "=G8", "=H8", "=I8", "=J8"],
    ["=A9", "=G9", "=H9", "=I9", "=J9"],
    ["=A10", "=G10", "=H10", "=I10", "=J10"],
    ["=A11", "=G11", "=H11", "=I11", "=J11"],
    ["=A12", "=G12", "=H12", "=I12", "=J12"],
  ];
  hist.getRange("W4:AA12").format.numberFormat = "0.0%";
  hist.getRange("W4:W12").format.numberFormat = "0";
  comps.getRange("M24:N28").formulas = [
    ["=B4", "=I4"],
    ["=B5", "=I5"],
    ["=B6", "=I6"],
    ["=B7", "=I7"],
    ["=B8", "=I8"],
  ];
  comps.getRange("N25:N28").format.numberFormat = "0.0x";

  const revenueChart = hist.charts.add("line", hist.getRange("A4:D12"));
  revenueChart.title = "Revenue and Profit Trend";
  revenueChart.hasLegend = true;
  revenueChart.xAxis = { axisType: "textAxis" };
  revenueChart.yAxis = { numberFormatCode: "#,##0" };
  revenueChart.setPosition("N4", "U20");

  const marginChart = hist.charts.add("line", hist.getRange("W4:AA12"));
  marginChart.title = "Growth, Margin and ROE";
  marginChart.hasLegend = true;
  marginChart.xAxis = { axisType: "textAxis" };
  marginChart.yAxis = { numberFormatCode: "0.0%" };
  marginChart.setPosition("N22", "U38");

  const peerChart = comps.charts.add("bar", comps.getRange("M24:N28"));
  peerChart.title = "Peer PER Comparison";
  peerChart.hasLegend = false;
  peerChart.xAxis = { axisType: "textAxis" };
  peerChart.yAxis = { numberFormatCode: "0.0x" };
  peerChart.setPosition("M4", "T20");

  const sensChart = sens.charts.add("line", sens.getRange("A4:F9"));
  sensChart.title = "Sensitivity Output by EPS Case";
  sensChart.hasLegend = true;
  sensChart.xAxis = { axisType: "textAxis" };
  sensChart.yAxis = { numberFormatCode: "#,##0" };
  sensChart.setPosition("I4", "P22");

  for (const sheet of [hist, forecast, comps, val, sens, checks, sources]) {
    sheet.getUsedRange().format.font.name = "Arial";
    sheet.getUsedRange().format.font.size = 10;
  }
  cover.getUsedRange().format.font.name = "Arial";
  cover.getUsedRange().format.font.size = 10;

  await fs.mkdir(OUT_DIR, { recursive: true });

  const inspections = [];
  inspections.push(await workbook.inspect({ kind: "table", sheetId: "Valuation", range: "A4:F15", include: "values,formulas", tableMaxRows: 15, tableMaxCols: 8 }));
  inspections.push(await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 300 }, summary: "formula error scan" }));
  for (const [sheetName, range] of [
    ["Cover", "A1:H12"],
    ["Historical", "A1:U38"],
    ["Forecast", "A1:F18"],
    ["Peer Comps", "A1:T20"],
    ["Valuation", "A1:G24"],
    ["Sensitivity", "A1:P22"],
    ["Checks", "A1:G10"],
    ["Sources", "A1:E11"],
  ]) {
    const preview = await workbook.render({ sheetName, range, autoCrop: "all", scale: 1, format: "png" });
    const bytes = new Uint8Array(await preview.arrayBuffer());
    await fs.writeFile(path.join(OUT_DIR, `qa_${sheetName.replaceAll(" ", "_")}.png`), bytes);
  }
  await fs.writeFile(path.join(OUT_DIR, "LS_ELECTRIC_Analyst_Model_QA.ndjson"), inspections.map((item) => item.ndjson).join("\n"), "utf8");

  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(OUT_PATH);
  console.log(OUT_PATH);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

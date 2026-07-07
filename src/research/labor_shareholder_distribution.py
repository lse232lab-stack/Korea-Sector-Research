from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import os
import re

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FILES = [
    Path("/Users/leesangeui/Downloads/kospi07-11.xlsx"),
    Path("/Users/leesangeui/Downloads/kospi12-16.xlsx"),
    Path("/Users/leesangeui/Downloads/kospi 17-21.xlsx"),
    Path("/Users/leesangeui/Downloads/kospi22-26.xlsx"),
]


RAW_COLUMNS = {
    "company_name": "회사명",
    "ticker": "거래소코드",
    "fiscal_period": "회계년도",
    "employee_compensation": "[B980010600][공통]   종업원 급여비용(IFRS)(천원)",
    "employee_cash_outflow": "[D100020200][공통]      종업원과 관련하여 직·간접으로 발생하는 현금유출(IFRS)(천원)",
    "value_added": "[공통]부가가치(IFRS)(백만원)",
    "labor_share_reported": "[공통]노동소득분배율(IFRS)",
    "dividend_paid_cf": "[D100020500][공통]      배당금지급액(IFRS)(천원)",
    "dividend_paid_alt": "[D109010400][공통]   배당금지급(-)(IFRS)(천원)",
    "cash_dividend": "[E300011000][공통]      현금배당(IFRS)(천원)",
    "share_buyback": "[D306014500][공통]      자기주식의 취득(IFRS)(천원)",
}


FINANCIAL_NAME_KEYWORDS = (
    "은행",
    "금융",
    "증권",
    "보험",
    "카드",
    "캐피탈",
    "투자",
    "리츠",
)


@dataclass(frozen=True)
class LaborShareholderOutputs:
    panel_path: Path
    annual_path: Path
    correlation_path: Path
    chart_paths: list[Path]
    report_path: Path


def _clean_column_name(column: str) -> str:
    return re.sub(r"\s+", " ", str(column)).strip()


def _read_source_file(path: Path) -> pd.DataFrame:
    header = pd.read_excel(path, sheet_name=0, nrows=0).columns
    normalized_lookup = {_clean_column_name(col): col for col in header}
    wanted = {_clean_column_name(col) for col in RAW_COLUMNS.values()}
    missing = sorted(wanted - set(normalized_lookup))
    if missing:
        raise ValueError(f"{path.name} missing required columns: {missing}")

    usecols = [normalized_lookup[col] for col in wanted]
    df = pd.read_excel(path, sheet_name=0, usecols=usecols)
    rename_map = {
        normalized_lookup[_clean_column_name(raw)]: clean
        for clean, raw in RAW_COLUMNS.items()
    }
    df = df.rename(columns=rename_map)
    df["source_file"] = path.name
    return df


def build_firm_year_panel(files: list[Path] | None = None) -> pd.DataFrame:
    files = files or DEFAULT_FILES
    frames = [_read_source_file(path) for path in files]
    panel = pd.concat(frames, ignore_index=True)

    panel["ticker"] = panel["ticker"].astype(str).str.extract(r"(\d+)")[0].str.zfill(6)
    panel["fiscal_period"] = panel["fiscal_period"].astype(str).str.strip()
    panel["fiscal_year"] = panel["fiscal_period"].str[:4].astype("Int64")
    panel["fiscal_month"] = panel["fiscal_period"].str.extract(r"/(\d{1,2})")[0].astype("Int64")

    panel = panel[panel["fiscal_month"].eq(12)].copy()
    numeric_columns = [col for col in RAW_COLUMNS if col not in {"company_name", "ticker", "fiscal_period"}]
    for col in numeric_columns:
        panel[col] = pd.to_numeric(panel[col], errors="coerce")

    panel = panel.sort_values(["ticker", "fiscal_year", "source_file"])
    panel = panel.groupby(["ticker", "fiscal_year"], as_index=False).first()

    panel["is_financial_name"] = panel["company_name"].astype(str).str.contains(
        "|".join(FINANCIAL_NAME_KEYWORDS), regex=True, na=False
    )

    # Convert to trillion won. Raw employee and payout accounts are thousand KRW;
    # raw value-added is million KRW.
    panel["employee_comp_trn"] = panel["employee_compensation"] / 1e9
    panel["employee_cash_outflow_trn"] = panel["employee_cash_outflow"] / 1e9
    panel["value_added_trn"] = panel["value_added"] / 1e6
    panel["dividend_paid_trn"] = panel["dividend_paid_cf"].abs() / 1e9
    panel["dividend_paid_alt_trn"] = panel["dividend_paid_alt"].abs() / 1e9
    panel["cash_dividend_trn"] = panel["cash_dividend"].abs() / 1e9
    panel["share_buyback_trn"] = panel["share_buyback"].abs() / 1e9

    dividend_candidates = ["dividend_paid_trn", "dividend_paid_alt_trn", "cash_dividend_trn"]
    panel["dividend_trn"] = panel[dividend_candidates].max(axis=1).fillna(0.0)
    panel["shareholder_payout_trn"] = panel["dividend_trn"].fillna(0.0) + panel["share_buyback_trn"].fillna(0.0)

    panel["labor_share_bottom_up"] = panel["employee_comp_trn"] / panel["value_added_trn"]
    panel["shareholder_payout_to_va"] = panel["shareholder_payout_trn"] / panel["value_added_trn"]
    panel["dividend_to_va"] = panel["dividend_trn"] / panel["value_added_trn"]
    panel["buyback_to_va"] = panel["share_buyback_trn"] / panel["value_added_trn"]

    valid = panel["value_added_trn"].gt(0) & panel["employee_comp_trn"].gt(0)
    panel["analysis_sample"] = valid & ~panel["is_financial_name"]
    return panel


def build_annual_summary(panel: pd.DataFrame) -> pd.DataFrame:
    sample = panel[panel["analysis_sample"]].copy()

    rows = []
    for year, group in sample.groupby("fiscal_year"):
        value_added = group["value_added_trn"].sum(min_count=1)
        employee_comp = group["employee_comp_trn"].sum(min_count=1)
        payout = group["shareholder_payout_trn"].sum(min_count=1)
        dividend = group["dividend_trn"].sum(min_count=1)
        buyback = group["share_buyback_trn"].sum(min_count=1)
        reported_weight = np.average(
            group["labor_share_reported"].dropna(),
            weights=group.loc[group["labor_share_reported"].notna(), "value_added_trn"],
        ) if group["labor_share_reported"].notna().any() else np.nan

        rows.append(
            {
                "fiscal_year": int(year),
                "firm_count": int(group["ticker"].nunique()),
                "value_added_trn": value_added,
                "employee_comp_trn": employee_comp,
                "dividend_trn": dividend,
                "share_buyback_trn": buyback,
                "shareholder_payout_trn": payout,
                "labor_share_bottom_up": employee_comp / value_added if value_added else np.nan,
                "labor_share_reported_vw": reported_weight / 100 if reported_weight and reported_weight > 1 else reported_weight,
                "labor_share_median_firm": group["labor_share_bottom_up"].replace([np.inf, -np.inf], np.nan).median(),
                "shareholder_payout_to_va": payout / value_added if value_added else np.nan,
                "dividend_to_va": dividend / value_added if value_added else np.nan,
                "buyback_to_va": buyback / value_added if value_added else np.nan,
            }
        )

    annual = pd.DataFrame(rows).sort_values("fiscal_year")
    for col in ["labor_share_bottom_up", "shareholder_payout_to_va", "dividend_to_va", "buyback_to_va"]:
        annual[f"{col}_chg"] = annual[col].diff()
    annual["labor_minus_payout_pp"] = 100 * (
        annual["labor_share_bottom_up"] - annual["shareholder_payout_to_va"]
    )
    annual["payout_yoy_growth"] = annual["shareholder_payout_trn"].pct_change()
    return annual


def build_correlations(annual: pd.DataFrame) -> pd.DataFrame:
    def spearman_without_scipy(subset: pd.DataFrame, lhs: str, rhs: str) -> float:
        ranked = subset[[lhs, rhs]].rank(method="average")
        return ranked[lhs].corr(ranked[rhs], method="pearson")

    pairs = [
        ("level_labor_vs_payout", "labor_share_bottom_up", "shareholder_payout_to_va"),
        ("change_labor_vs_payout", "labor_share_bottom_up_chg", "shareholder_payout_to_va_chg"),
        ("level_labor_vs_dividend", "labor_share_bottom_up", "dividend_to_va"),
        ("level_labor_vs_buyback", "labor_share_bottom_up", "buyback_to_va"),
    ]
    rows = []
    for name, lhs, rhs in pairs:
        subset = annual[[lhs, rhs]].dropna()
        rows.append(
            {
                "relationship": name,
                "observations": len(subset),
                "pearson_corr": subset[lhs].corr(subset[rhs], method="pearson") if len(subset) >= 3 else np.nan,
                "spearman_corr": spearman_without_scipy(subset, lhs, rhs) if len(subset) >= 3 else np.nan,
            }
        )
    return pd.DataFrame(rows)


def _set_korean_font() -> None:
    import matplotlib.pyplot as plt

    plt.rcParams["axes.unicode_minus"] = False
    for font in ["AppleGothic", "Malgun Gothic", "NanumGothic", "Noto Sans CJK KR"]:
        plt.rcParams["font.family"] = font
        break


def plot_outputs(annual: pd.DataFrame, output_dir: Path) -> list[Path]:
    from PIL import Image, ImageDraw, ImageFont

    output_dir.mkdir(parents=True, exist_ok=True)
    chart_paths: list[Path] = []
    font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
    title_font = ImageFont.truetype(font_path, 30)
    label_font = ImageFont.truetype(font_path, 18)
    small_font = ImageFont.truetype(font_path, 14)

    def canvas(title: str) -> tuple[Image.Image, ImageDraw.ImageDraw, tuple[int, int, int, int]]:
        img = Image.new("RGB", (1400, 820), "white")
        draw = ImageDraw.Draw(img)
        draw.text((60, 38), title, fill=(24, 35, 50), font=title_font)
        box = (110, 120, 1320, 700)
        draw.rectangle(box, outline=(210, 216, 224), width=2)
        return img, draw, box

    def scale(values: pd.Series | np.ndarray, vmin: float | None = None, vmax: float | None = None):
        arr = pd.Series(values, dtype="float64")
        lo = float(arr.min()) if vmin is None else vmin
        hi = float(arr.max()) if vmax is None else vmax
        if not np.isfinite(lo) or not np.isfinite(hi) or hi == lo:
            hi = lo + 1.0
        pad = (hi - lo) * 0.08
        return lo - pad, hi + pad

    def xy_points(years: pd.Series, values: pd.Series, box, y_min=None, y_max=None):
        left, top, right, bottom = box
        y0, y1 = scale(values, y_min, y_max)
        x0, x1 = int(years.min()), int(years.max())
        points = []
        for year, value in zip(years, values):
            x = left + (int(year) - x0) / max(x1 - x0, 1) * (right - left)
            y = bottom - (float(value) - y0) / (y1 - y0) * (bottom - top)
            points.append((int(x), int(y)))
        return points, y0, y1

    def axes(draw, box, y0, y1, unit: str = "%") -> None:
        left, top, right, bottom = box
        for i in range(5):
            y = top + i * (bottom - top) / 4
            value = y1 - i * (y1 - y0) / 4
            draw.line((left, y, right, y), fill=(235, 238, 242), width=1)
            draw.text((30, y - 10), f"{value:.1f}{unit}", fill=(75, 85, 99), font=small_font)
        for year in annual["fiscal_year"]:
            if int(year) % 2 == 0:
                x = left + (int(year) - int(annual["fiscal_year"].min())) / max(int(annual["fiscal_year"].max()) - int(annual["fiscal_year"].min()), 1) * (right - left)
                draw.text((x - 18, bottom + 12), str(int(year)), fill=(75, 85, 99), font=small_font)

    def draw_line(draw, points, color, width=5) -> None:
        if len(points) > 1:
            draw.line(points, fill=color, width=width, joint="curve")
        for x, y in points:
            draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=color)

    years = annual["fiscal_year"]
    labor = annual["labor_share_bottom_up"] * 100
    reported = annual["labor_share_reported_vw"] * 100
    y_min, y_max = scale(pd.concat([labor, reported]).dropna())
    img, draw, box = canvas("KOSPI 노동소득분배율 20년 추이")
    axes(draw, box, y_min, y_max)
    points, _, _ = xy_points(years, labor, box, y_min, y_max)
    draw_line(draw, points, (31, 119, 180))
    points, _, _ = xy_points(years, reported, box, y_min, y_max)
    draw_line(draw, points, (44, 160, 44))
    draw.text((930, 56), "파랑: 급여비용/부가가치  초록: 제공값 VW", fill=(55, 65, 81), font=label_font)
    path = output_dir / "labor_share_trend.png"
    img.save(path)
    chart_paths.append(path)

    payout = annual["shareholder_payout_to_va"] * 100
    y_min, y_max = scale(pd.concat([labor, payout]).dropna(), 0)
    img, draw, box = canvas("노동 몫과 주주환원 몫의 동조 여부")
    axes(draw, box, y_min, y_max)
    bar_w = max(10, int((box[2] - box[0]) / len(annual) * 0.45))
    _, y0, y1 = xy_points(years, payout, box, y_min, y_max)
    for year, value in zip(years, payout):
        x = box[0] + (int(year) - int(years.min())) / max(int(years.max()) - int(years.min()), 1) * (box[2] - box[0])
        y = box[3] - (float(value) - y0) / (y1 - y0) * (box[3] - box[1])
        draw.rectangle((x - bar_w // 2, y, x + bar_w // 2, box[3]), fill=(255, 127, 14))
    points, _, _ = xy_points(years, labor, box, y_min, y_max)
    draw_line(draw, points, (31, 119, 180))
    draw.text((900, 56), "파랑: 노동소득분배율  주황: 주주환원/부가가치", fill=(55, 65, 81), font=label_font)
    path = output_dir / "labor_vs_shareholder_payout.png"
    img.save(path)
    chart_paths.append(path)

    dividend = annual["dividend_trn"].fillna(0)
    buyback = annual["share_buyback_trn"].fillna(0)
    total = dividend + buyback
    y_min, y_max = scale(total, 0)
    img, draw, box = canvas("KOSPI 주주환원 구성: 배당 vs 자사주 취득")
    axes(draw, box, y_min, y_max, "조")
    _, y0, y1 = xy_points(years, total, box, y_min, y_max)
    for year, div, buy in zip(years, dividend, buyback):
        x = box[0] + (int(year) - int(years.min())) / max(int(years.max()) - int(years.min()), 1) * (box[2] - box[0])
        y_div = box[3] - (float(div) - y0) / (y1 - y0) * (box[3] - box[1])
        y_total = box[3] - (float(div + buy) - y0) / (y1 - y0) * (box[3] - box[1])
        draw.rectangle((x - bar_w // 2, y_div, x + bar_w // 2, box[3]), fill=(44, 160, 44))
        draw.rectangle((x - bar_w // 2, y_total, x + bar_w // 2, y_div), fill=(148, 103, 189))
    draw.text((940, 56), "초록: 배당  보라: 자사주 취득", fill=(55, 65, 81), font=label_font)
    path = output_dir / "shareholder_payout_components.png"
    img.save(path)
    chart_paths.append(path)

    x_vals = labor
    y_vals = payout
    x0, x1 = scale(x_vals)
    y0, y1 = scale(y_vals)
    img, draw, box = canvas("연도별 노동소득분배율과 주주환원율 산점도")
    axes(draw, box, y0, y1)
    for _, row in annual.iterrows():
        x = box[0] + ((row["labor_share_bottom_up"] * 100) - x0) / (x1 - x0) * (box[2] - box[0])
        y = box[3] - ((row["shareholder_payout_to_va"] * 100) - y0) / (y1 - y0) * (box[3] - box[1])
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(214, 39, 40))
        draw.text((x + 8, y - 8), str(int(row["fiscal_year"])), fill=(75, 85, 99), font=small_font)
    draw.text((560, 732), "X축: 노동소득분배율(%)    Y축: 주주환원/부가가치(%)", fill=(55, 65, 81), font=label_font)
    path = output_dir / "labor_payout_scatter.png"
    img.save(path)
    chart_paths.append(path)

    return chart_paths


def write_report(panel: pd.DataFrame, annual: pd.DataFrame, correlations: pd.DataFrame, chart_paths: list[Path], output_path: Path) -> None:
    first_year = int(annual["fiscal_year"].min())
    last_year = int(annual["fiscal_year"].max())
    core = annual[annual["firm_count"].ge(100)].copy()
    if core.empty:
        core = annual.copy()
    core_first_year = int(core["fiscal_year"].min())
    core_last_year = int(core["fiscal_year"].max())
    latest = annual.iloc[-1]
    first = core.iloc[0]
    core_correlations = build_correlations(core)
    corr_level = core_correlations.loc[core_correlations["relationship"].eq("level_labor_vs_payout"), "pearson_corr"].iloc[0]
    corr_change = core_correlations.loc[core_correlations["relationship"].eq("change_labor_vs_payout"), "pearson_corr"].iloc[0]

    def pct(x: float) -> str:
        return f"{x * 100:.2f}%"

    lines = [
        "# KOSPI 노동 vs 주주 분배 탐색 분석",
        "",
        "## 1. 연구 질문",
        "",
        "한국 상장기업의 부가가치가 노동과 주주에게 어떻게 배분되어 왔는지 확인한다. 핵심 질문은 두 가지다.",
        "",
        "1. KOSPI 기업의 노동소득분배율은 장기적으로 상승했는가, 하락했는가?",
        "2. 배당과 자사주 취득을 합친 주주환원이 확대될 때 노동 몫은 같은 방향으로 움직였는가, 반대로 움직였는가?",
        "",
        "## 2. 데이터와 표본 설계",
        "",
        f"- 원천 파일: {', '.join(path.name for path in DEFAULT_FILES)}",
        f"- 분석 기간: {first_year}~{last_year} 회계연도",
        f"- 단, 2008~2009년은 `/12` 결산 표본 수가 작아 대표성이 약하다. 해석의 중심 구간은 기업 수가 100개 이상 확보되는 {core_first_year}~{core_last_year}년이다.",
        "- 월별로 반복 저장된 재무 데이터를 `거래소코드-회계연도` 단위로 접고, 연간 재무제표 해석에 맞게 `/12` 결산만 사용했다.",
        "- 노동소득분배율의 주 분석값은 `종업원 급여비용(천원) / 부가가치(백만원)`을 조원 단위로 통일한 뒤 시장 전체 합계 기준으로 계산했다.",
        "- 주주환원은 `배당금지급액 + 자기주식의 취득`으로 정의했다. 배당금지급액이 없을 때는 대체 배당 계정을 보조적으로 사용한다.",
        "- 금융·보험·증권 등 이름 기반 금융업 추정 기업과 부가가치 또는 급여비용이 0 이하인 관측치는 제외했다.",
        "",
        "## 3. 주요 결과",
        "",
        f"- 분석 표본은 총 {len(panel):,}개 firm-year 원자료에서 {int(panel['analysis_sample'].sum()):,}개 관측치로 구성됐다.",
        f"- 핵심 커버리지 기준 {core_first_year}년 노동소득분배율은 {pct(first['labor_share_bottom_up'])}, {last_year}년은 {pct(latest['labor_share_bottom_up'])}다.",
        f"- {last_year}년 주주환원/부가가치는 {pct(latest['shareholder_payout_to_va'])}이며, 배당 {latest['dividend_trn']:.2f}조원, 자사주 취득 {latest['share_buyback_trn']:.2f}조원으로 구성된다.",
        f"- {core_first_year}~{core_last_year}년 기준 노동소득분배율과 주주환원율의 수준 상관계수는 {corr_level:.3f}, 전년 대비 변화 상관계수는 {corr_change:.3f}다.",
        "",
        "## 4. 해석",
        "",
        "수준 상관계수가 양수라면 노동 몫과 주주환원이 장기 성장 또는 이익 사이클에 함께 올라가는 성격이 있다는 뜻이다. 반대로 음수라면 부가가치 배분에서 노동과 주주 사이의 대체 관계가 더 강하다는 해석이 가능하다.",
        "",
        "변화 상관계수는 더 엄격한 지표다. 같은 해에 노동 몫이 증가할 때 주주환원율도 같이 증가했는지를 보므로, 단순한 장기 추세보다 배분 충돌 또는 동조를 직접적으로 보여준다.",
        "",
        "## 5. 산출물",
        "",
    ]
    for path in chart_paths:
        lines.append(f"- `{path.relative_to(PROJECT_ROOT)}`")
    lines.extend(
        [
            "",
            "## 6. 다음 연구 확장",
            "",
            "- 산업분류를 추가해 제조업, 금융업, 플랫폼/서비스업을 분리하면 노동 몫의 구조적 차이를 더 명확히 볼 수 있다.",
            "- 주주환원 확대 기업과 비확대 기업을 나눠 향후 수익률, 밸류에이션, 고용/임금 증가율 차이를 검정할 수 있다.",
            "- 기존 KOSPI200 퀀트 모델에 `노동-주주 분배 균형` 팩터를 추가해 ESG/스튜어드십 관점의 투자전략으로 확장할 수 있다.",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def run_analysis(output_root: Path | None = None, skip_charts: bool = False) -> LaborShareholderOutputs:
    output_root = output_root or PROJECT_ROOT / "outputs" / "labor_shareholder_distribution"
    table_dir = output_root / "tables"
    chart_dir = output_root / "charts"
    report_dir = output_root / "reports"
    table_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    panel = build_firm_year_panel()
    annual = build_annual_summary(panel)
    correlations = build_correlations(annual)
    chart_paths = [] if skip_charts else plot_outputs(annual, chart_dir)

    panel_path = table_dir / "firm_year_panel.csv"
    annual_path = table_dir / "annual_distribution_summary.csv"
    correlation_path = table_dir / "labor_shareholder_correlations.csv"
    report_path = report_dir / "Labor_vs_Shareholder_Distribution_Research_Note.md"

    panel.to_csv(panel_path, index=False, encoding="utf-8-sig")
    annual.to_csv(annual_path, index=False, encoding="utf-8-sig")
    correlations.to_csv(correlation_path, index=False, encoding="utf-8-sig")
    write_report(panel, annual, correlations, chart_paths, report_path)

    return LaborShareholderOutputs(
        panel_path=panel_path,
        annual_path=annual_path,
        correlation_path=correlation_path,
        chart_paths=chart_paths,
        report_path=report_path,
    )


def run_charts_from_tables(output_root: Path | None = None) -> list[Path]:
    output_root = output_root or PROJECT_ROOT / "outputs" / "labor_shareholder_distribution"
    panel_path = output_root / "tables" / "firm_year_panel.csv"
    annual_path = output_root / "tables" / "annual_distribution_summary.csv"
    correlation_path = output_root / "tables" / "labor_shareholder_correlations.csv"
    report_path = output_root / "reports" / "Labor_vs_Shareholder_Distribution_Research_Note.md"
    chart_dir = output_root / "charts"
    panel = pd.read_csv(panel_path)
    annual = pd.read_csv(annual_path)
    correlations = pd.read_csv(correlation_path)
    chart_paths = plot_outputs(annual, chart_dir)
    write_report(panel, annual, correlations, chart_paths, report_path)
    return chart_paths


def refresh_outputs_from_panel(output_root: Path | None = None) -> LaborShareholderOutputs:
    output_root = output_root or PROJECT_ROOT / "outputs" / "labor_shareholder_distribution"
    table_dir = output_root / "tables"
    chart_dir = output_root / "charts"
    report_dir = output_root / "reports"
    panel_path = table_dir / "firm_year_panel.csv"
    annual_path = table_dir / "annual_distribution_summary.csv"
    correlation_path = table_dir / "labor_shareholder_correlations.csv"
    report_path = report_dir / "Labor_vs_Shareholder_Distribution_Research_Note.md"

    panel = pd.read_csv(panel_path)
    dividend_candidates = ["dividend_paid_trn", "dividend_paid_alt_trn", "cash_dividend_trn"]
    panel["dividend_trn"] = panel[dividend_candidates].max(axis=1).fillna(0.0)
    panel["shareholder_payout_trn"] = panel["dividend_trn"].fillna(0.0) + panel["share_buyback_trn"].fillna(0.0)
    panel["shareholder_payout_to_va"] = panel["shareholder_payout_trn"] / panel["value_added_trn"]
    panel["dividend_to_va"] = panel["dividend_trn"] / panel["value_added_trn"]
    panel["buyback_to_va"] = panel["share_buyback_trn"] / panel["value_added_trn"]

    annual = build_annual_summary(panel)
    correlations = build_correlations(annual)
    chart_paths = plot_outputs(annual, chart_dir)
    panel.to_csv(panel_path, index=False, encoding="utf-8-sig")
    annual.to_csv(annual_path, index=False, encoding="utf-8-sig")
    correlations.to_csv(correlation_path, index=False, encoding="utf-8-sig")
    write_report(panel, annual, correlations, chart_paths, report_path)
    return LaborShareholderOutputs(panel_path, annual_path, correlation_path, chart_paths, report_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-charts", action="store_true")
    parser.add_argument("--charts-only", action="store_true")
    parser.add_argument("--refresh-from-panel", action="store_true")
    args = parser.parse_args()

    if args.refresh_from_panel:
        outputs = refresh_outputs_from_panel()
        print(f"panel={outputs.panel_path}")
        print(f"annual={outputs.annual_path}")
        print(f"correlations={outputs.correlation_path}")
        for chart in outputs.chart_paths:
            print(f"chart={chart}")
        print(f"report={outputs.report_path}")
        raise SystemExit(0)

    if args.charts_only:
        chart_paths = run_charts_from_tables()
        for chart in chart_paths:
            print(f"chart={chart}")
        raise SystemExit(0)

    outputs = run_analysis(skip_charts=args.skip_charts)
    print(f"panel={outputs.panel_path}")
    print(f"annual={outputs.annual_path}")
    print(f"correlations={outputs.correlation_path}")
    for chart in outputs.chart_paths:
        print(f"chart={chart}")
    print(f"report={outputs.report_path}")

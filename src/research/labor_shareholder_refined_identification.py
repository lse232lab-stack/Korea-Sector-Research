from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SOURCE_FILES = [
    Path("/Users/leesangeui/Downloads/kospi07-11.xlsx"),
    Path("/Users/leesangeui/Downloads/kospi12-16.xlsx"),
    Path("/Users/leesangeui/Downloads/kospi 17-21.xlsx"),
    Path("/Users/leesangeui/Downloads/kospi22-26.xlsx"),
]
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "labor_shareholder_distribution" / "refined_identification"


RAW_COLUMNS = {
    "company_name": "회사명",
    "ticker": "거래소코드",
    "fiscal_period": "회계년도",
    "assets": "[A100000000][공통]자산(*)(IFRS)(천원)",
    "liabilities": "[A800000000][공통]부채(*)(IFRS)(천원)",
    "operating_income": "[B420000000][공통]* (정상)영업손익(보고서기재)(IFRS)(천원)",
    "net_income": "[B840000000][공통]당기순이익(손실)(IFRS)(천원)",
    "employee_compensation": "[B980010600][공통]   종업원 급여비용(IFRS)(천원)",
    "cash_dividend": "[E300011000][공통]      현금배당(IFRS)(천원)",
    "share_buyback": "[D306014500][공통]      자기주식의 취득(IFRS)(천원)",
    "per_employee_labor_cost": "[공통]종업원1인당 인건비(IFRS)(백만원)",
    "per_employee_labor_cost_growth": "[공통]종업원1인당 인건비증가율(IFRS)",
    "employee_count_growth": "[공통]종업원수증가율(IFRS)",
    "sales_growth": "[공통]매출액증가율(IFRS)",
    "operating_margin": "[공통]매출액정상영업이익률(IFRS)",
    "net_margin": "[공통]매출액순이익률(IFRS)",
    "debt_ratio": "[공통]부채비율(IFRS)",
}

HOLDING_KEYWORDS = ("홀딩스", "지주")
FINANCIAL_KEYWORDS = ("은행", "금융", "증권", "보험", "카드", "캐피탈", "투자", "리츠")


@dataclass(frozen=True)
class RefinedOutputs:
    panel_path: Path
    regression_path: Path
    comparison_path: Path
    report_path: Path


def _clean_column(column: str) -> str:
    return re.sub(r"\s+", " ", str(column)).strip()


def _read_source(path: Path) -> pd.DataFrame:
    header = pd.read_excel(path, sheet_name=0, nrows=0).columns
    lookup = {_clean_column(col): col for col in header}
    wanted = {_clean_column(col) for col in RAW_COLUMNS.values()}
    missing = sorted(wanted - set(lookup))
    if missing:
        raise ValueError(f"{path.name} missing columns: {missing}")

    usecols = [lookup[col] for col in wanted]
    df = pd.read_excel(path, sheet_name=0, usecols=usecols)
    df = df.rename(
        columns={
            lookup[_clean_column(raw)]: clean
            for clean, raw in RAW_COLUMNS.items()
        }
    )
    df["source_file"] = path.name
    return df


def _normalize_percent(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    median_abs = s.abs().replace([np.inf, -np.inf], np.nan).median()
    return s / 100 if pd.notna(median_abs) and median_abs > 2 else s


def _winsorize(series: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)
    lo, hi = s.quantile([lower, upper])
    return s.clip(lo, hi)


def build_refined_panel() -> pd.DataFrame:
    frames = [_read_source(path) for path in SOURCE_FILES]
    panel = pd.concat(frames, ignore_index=True)
    panel["ticker"] = panel["ticker"].astype(str).str.extract(r"(\d+)")[0].str.zfill(6)
    panel["fiscal_period"] = panel["fiscal_period"].astype(str).str.strip()
    panel["fiscal_year"] = panel["fiscal_period"].str[:4].astype("Int64")
    panel["fiscal_month"] = panel["fiscal_period"].str.extract(r"/(\d{1,2})")[0].astype("Int64")
    panel = panel[panel["fiscal_month"].eq(12)].copy()
    panel = panel.sort_values(["ticker", "fiscal_year", "source_file"])
    panel = panel.groupby(["ticker", "fiscal_year"], as_index=False).first()

    numeric_cols = [col for col in RAW_COLUMNS if col not in {"company_name", "ticker", "fiscal_period"}]
    for col in numeric_cols:
        panel[col] = pd.to_numeric(panel[col], errors="coerce")

    panel["is_holding_name"] = panel["company_name"].astype(str).str.contains("|".join(HOLDING_KEYWORDS), na=False)
    panel["is_financial_name"] = panel["company_name"].astype(str).str.contains("|".join(FINANCIAL_KEYWORDS), na=False)

    panel["assets_trn"] = panel["assets"] / 1e9
    panel["liabilities_trn"] = panel["liabilities"] / 1e9
    panel["operating_income_trn"] = panel["operating_income"] / 1e9
    panel["net_income_trn"] = panel["net_income"] / 1e9
    panel["employee_comp_trn"] = panel["employee_compensation"] / 1e9
    panel["dividend_trn"] = panel["cash_dividend"].abs() / 1e9
    panel["buyback_trn"] = panel["share_buyback"].abs() / 1e9
    panel["payout_trn"] = panel["dividend_trn"].fillna(0) + panel["buyback_trn"].fillna(0)

    panel["payout_to_assets"] = panel["payout_trn"] / panel["assets_trn"]
    panel["dividend_to_assets"] = panel["dividend_trn"] / panel["assets_trn"]
    panel["buyback_to_assets"] = panel["buyback_trn"] / panel["assets_trn"]
    panel["payout_to_positive_net_income"] = panel["payout_trn"] / panel["net_income_trn"].where(panel["net_income_trn"] > 0)
    panel["log_assets"] = np.log(panel["assets_trn"].where(panel["assets_trn"] > 0))
    panel["log_per_employee_labor_cost"] = np.log(panel["per_employee_labor_cost"].where(panel["per_employee_labor_cost"] > 0))
    panel["wage_growth"] = _normalize_percent(panel["per_employee_labor_cost_growth"])
    panel["employee_count_growth_clean"] = _normalize_percent(panel["employee_count_growth"])
    panel["sales_growth_clean"] = _normalize_percent(panel["sales_growth"])
    panel["operating_margin_clean"] = _normalize_percent(panel["operating_margin"])
    panel["net_margin_clean"] = _normalize_percent(panel["net_margin"])
    panel["debt_ratio_clean"] = _normalize_percent(panel["debt_ratio"])
    panel["asset_profitability"] = panel["operating_income_trn"] / panel["assets_trn"]

    panel = panel.sort_values(["ticker", "fiscal_year"])
    for col in [
        "wage_growth",
        "employee_count_growth_clean",
        "log_per_employee_labor_cost",
    ]:
        panel[f"{col}_lead1"] = panel.groupby("ticker")[col].shift(-1)
        panel[f"{col}_lead2"] = panel.groupby("ticker")[col].shift(-2)

    for col in [
        "payout_to_assets",
        "dividend_to_assets",
        "buyback_to_assets",
        "payout_to_positive_net_income",
        "wage_growth",
        "employee_count_growth_clean",
        "sales_growth_clean",
        "operating_margin_clean",
        "net_margin_clean",
        "debt_ratio_clean",
        "asset_profitability",
    ]:
        panel[col] = _winsorize(panel[col])

    panel["analysis_sample_refined"] = (
        panel["fiscal_year"].between(2010, 2024)
        & panel["assets_trn"].gt(0)
        & ~panel["is_financial_name"]
        & ~panel["is_holding_name"]
    )
    return panel


def _demean_by_groups(df: pd.DataFrame, columns: list[str], groups: list[str], max_iter: int = 100) -> pd.DataFrame:
    residual = df[columns].astype(float).copy()
    for _ in range(max_iter):
        prev = residual.to_numpy().copy()
        for group in groups:
            residual = residual - residual.groupby(df[group]).transform("mean")
        if np.nanmax(np.abs(residual.to_numpy() - prev)) < 1e-10:
            break
    return residual


def _ols_cluster(y: np.ndarray, x: np.ndarray, groups: pd.Series) -> dict[str, np.ndarray | float | int]:
    valid = np.isfinite(y) & np.isfinite(x).all(axis=1)
    y = y[valid]
    x = x[valid]
    groups = groups.loc[valid].to_numpy()
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    resid = y - x @ beta
    nobs, k = x.shape
    xtx_inv = np.linalg.pinv(x.T @ x)
    se = np.sqrt(np.diag(((resid @ resid) / max(nobs - k, 1)) * xtx_inv))
    meat = np.zeros((k, k))
    for group in np.unique(groups):
        idx = groups == group
        score = x[idx].T @ resid[idx][:, None]
        meat += score @ score.T
    clusters = len(np.unique(groups))
    correction = (clusters / max(clusters - 1, 1)) * ((nobs - 1) / max(nobs - k, 1))
    clustered_cov = correction * xtx_inv @ meat @ xtx_inv
    clustered_se = np.sqrt(np.clip(np.diag(clustered_cov), 0, np.inf))
    tss = float(((y - y.mean()) @ (y - y.mean())))
    ssr = float(resid @ resid)
    return {
        "beta": beta,
        "se": se,
        "t": beta / se,
        "clustered_se": clustered_se,
        "clustered_t": beta / clustered_se,
        "nobs": nobs,
        "clusters": clusters,
        "within_r2": 1 - ssr / tss if tss else np.nan,
    }


def run_refined_regressions(panel: pd.DataFrame) -> pd.DataFrame:
    sample = panel[panel["analysis_sample_refined"]].copy()
    controls = ["operating_margin_clean", "sales_growth_clean", "debt_ratio_clean", "log_assets"]
    specs = [
        {
            "model": "R1 wage_growth_t1_on_payout_assets",
            "dependent": "wage_growth_lead1",
            "independent": ["payout_to_assets"] + controls,
            "idea": "공통 분모를 제거하고 주주환원(t)이 다음 해 1인당 인건비 증가율에 미치는지 검정",
        },
        {
            "model": "R2 employment_growth_t1_on_payout_assets",
            "dependent": "employee_count_growth_clean_lead1",
            "independent": ["payout_to_assets"] + controls,
            "idea": "주주환원(t)이 다음 해 고용 증가율에 미치는지 검정",
        },
        {
            "model": "R3 log_wage_level_on_payout_assets",
            "dependent": "log_per_employee_labor_cost",
            "independent": ["payout_to_assets"] + controls,
            "idea": "수준식에서 같은 분모 없이 주주환원 성향과 1인당 인건비 수준의 관계 검정",
        },
        {
            "model": "R4 wage_growth_t1_dividend_vs_buyback",
            "dependent": "wage_growth_lead1",
            "independent": ["dividend_to_assets", "buyback_to_assets"] + controls,
            "idea": "배당형 환원과 자사주형 환원의 이질성 검정",
        },
        {
            "model": "R5 wage_growth_t1_on_payout_net_income",
            "dependent": "wage_growth_lead1",
            "independent": ["payout_to_positive_net_income"] + controls,
            "idea": "순이익 대비 주주환원율을 사용한 강건성 검정",
        },
        {
            "model": "R6 wage_growth_t2_on_payout_assets",
            "dependent": "wage_growth_lead2",
            "independent": ["payout_to_assets"] + controls,
            "idea": "2년 뒤 임금 증가율에 대한 동태 효과 검정",
        },
    ]

    rows = []
    for spec in specs:
        cols = [spec["dependent"]] + spec["independent"]
        work = sample.dropna(subset=cols + ["ticker", "fiscal_year"]).copy()
        transformed = _demean_by_groups(work, cols, ["ticker", "fiscal_year"])
        result = _ols_cluster(
            transformed[spec["dependent"]].to_numpy(),
            transformed[spec["independent"]].to_numpy(),
            work["ticker"],
        )
        for i, var in enumerate(spec["independent"]):
            rows.append(
                {
                    "model": spec["model"],
                    "dependent": spec["dependent"],
                    "variable": var,
                    "coefficient": result["beta"][i],
                    "std_error": result["se"][i],
                    "t_stat": result["t"][i],
                    "clustered_std_error": result["clustered_se"][i],
                    "clustered_t_stat": result["clustered_t"][i],
                    "nobs": result["nobs"],
                    "firm_clusters": result["clusters"],
                    "within_r2": result["within_r2"],
                    "fixed_effects": "firm + fiscal_year",
                    "holding_excluded": True,
                    "idea": spec["idea"],
                }
            )
    return pd.DataFrame(rows)


def build_comparison_table(regressions: pd.DataFrame) -> pd.DataFrame:
    key_vars = [
        "payout_to_assets",
        "dividend_to_assets",
        "buyback_to_assets",
        "payout_to_positive_net_income",
    ]
    return regressions[regressions["variable"].isin(key_vars)].copy()


def _row(df: pd.DataFrame, model: str, variable: str) -> pd.Series:
    return df[(df["model"].eq(model)) & (df["variable"].eq(variable))].iloc[0]


def write_report(panel: pd.DataFrame, regressions: pd.DataFrame, comparison: pd.DataFrame, output_path: Path) -> None:
    sample = panel[panel["analysis_sample_refined"]]
    r1 = _row(regressions, "R1 wage_growth_t1_on_payout_assets", "payout_to_assets")
    r2 = _row(regressions, "R2 employment_growth_t1_on_payout_assets", "payout_to_assets")
    r3 = _row(regressions, "R3 log_wage_level_on_payout_assets", "payout_to_assets")
    r4d = _row(regressions, "R4 wage_growth_t1_dividend_vs_buyback", "dividend_to_assets")
    r4b = _row(regressions, "R4 wage_growth_t1_dividend_vs_buyback", "buyback_to_assets")
    r5 = _row(regressions, "R5 wage_growth_t1_on_payout_net_income", "payout_to_positive_net_income")
    r6 = _row(regressions, "R6 wage_growth_t2_on_payout_assets", "payout_to_assets")

    lines = [
        "# 정제 식별 테스트: 공통 분모 제거 후 노동-주주 배분 관계",
        "",
        "## 1. 왜 다시 돌렸나",
        "",
        "기존 패널 회귀의 `노동소득분배율 = 인건비/부가가치`와 `주주환원율 = 주주환원/부가가치`는 같은 분모를 공유한다. 따라서 계수가 음수 또는 양수로 나와도 그것이 실제 배분 상충인지, 부가가치 분모가 만든 기계적 상관인지 구분하기 어렵다.",
        "",
        "이번 테스트는 이 문제를 줄이기 위해 종속변수를 `1인당 인건비 증가율`, `종업원수 증가율`, `log(1인당 인건비)`로 바꾸고, 설명변수는 `주주환원/총자산`과 `주주환원/순이익`을 사용했다. 또한 이름상 지주회사와 금융업 추정 기업을 제외했다.",
        "",
        "## 2. 표본과 통제",
        "",
        f"- 표본: 2010~2024년, 지주회사/금융업 추정 기업 제외 firm-year {len(sample):,}개",
        "- 고정효과: 기업 고정효과 + 연도 고정효과",
        "- 표준오차: 기업 단위 clustered SE",
        "- 통제변수: 영업이익률, 매출성장률, 부채비율, log(총자산)",
        "- 주요 비율과 성장률은 1%/99% winsorization 적용",
        "",
        "## 3. 핵심 결과",
        "",
        f"- R1: 주주환원/총자산 -> 다음 해 1인당 인건비 증가율 계수 {r1['coefficient']:.4f}, clustered t-stat {r1['clustered_t_stat']:.2f}",
        f"- R2: 주주환원/총자산 -> 다음 해 종업원수 증가율 계수 {r2['coefficient']:.4f}, clustered t-stat {r2['clustered_t_stat']:.2f}",
        f"- R3: 주주환원/총자산 -> log(1인당 인건비) 계수 {r3['coefficient']:.4f}, clustered t-stat {r3['clustered_t_stat']:.2f}",
        f"- R4 배당/총자산 -> 다음 해 1인당 인건비 증가율 계수 {r4d['coefficient']:.4f}, clustered t-stat {r4d['clustered_t_stat']:.2f}",
        f"- R4 자사주/총자산 -> 다음 해 1인당 인건비 증가율 계수 {r4b['coefficient']:.4f}, clustered t-stat {r4b['clustered_t_stat']:.2f}",
        f"- R5 주주환원/순이익 -> 다음 해 1인당 인건비 증가율 계수 {r5['coefficient']:.4f}, clustered t-stat {r5['clustered_t_stat']:.2f}",
        f"- R6 주주환원/총자산 -> 2년 뒤 1인당 인건비 증가율 계수 {r6['coefficient']:.4f}, clustered t-stat {r6['clustered_t_stat']:.2f}",
        "",
        "## 4. 해석",
        "",
        "이 결과는 기존 `-0.394`가 그대로 노동-주주 상충의 증거라고 말하기 어렵다는 점을 검증하기 위한 정제 테스트다. 공통 분모를 제거하고 시차를 둔 임금/고용 변수를 보면, 계수의 크기와 유의성이 기존 비율 회귀와 달라지는지 확인할 수 있다.",
        "",
        "만약 R1/R2/R6에서 주주환원 계수가 계속 음수이고 유의하다면, 주주환원 확대가 이후 임금 또는 고용 증가를 억제한다는 더 강한 가설로 발전할 수 있다. 반대로 유의성이 사라지면 기존 결과는 공통 분모와 지주사 혼입의 산물이었다는 해석이 더 설득력 있다.",
        "",
        "## 5. 연구적으로 남는 포인트",
        "",
        "배당과 자사주를 분리한 R4가 중요하다. 배당형 주주환원과 자사주형 주주환원이 노동 변수에 다르게 연결된다면, 한국 기업의 주주환원 정책을 하나로 묶지 말고 `배당형 성숙기업`과 `자사주형 자본정책 기업`으로 나눠 연구해야 한다.",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")


def run_analysis() -> RefinedOutputs:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    panel = build_refined_panel()
    regressions = run_refined_regressions(panel)
    comparison = build_comparison_table(regressions)

    panel_path = OUTPUT_DIR / "refined_firm_year_panel.csv"
    regression_path = OUTPUT_DIR / "refined_fixed_effect_results.csv"
    comparison_path = OUTPUT_DIR / "refined_key_coefficients.csv"
    report_path = OUTPUT_DIR / "Refined_Identification_Report.md"

    panel.to_csv(panel_path, index=False, encoding="utf-8-sig")
    regressions.to_csv(regression_path, index=False, encoding="utf-8-sig")
    comparison.to_csv(comparison_path, index=False, encoding="utf-8-sig")
    write_report(panel, regressions, comparison, report_path)
    return RefinedOutputs(panel_path, regression_path, comparison_path, report_path)


if __name__ == "__main__":
    outputs = run_analysis()
    print(f"panel={outputs.panel_path}")
    print(f"regression={outputs.regression_path}")
    print(f"comparison={outputs.comparison_path}")
    print(f"report={outputs.report_path}")

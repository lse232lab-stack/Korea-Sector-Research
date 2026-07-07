from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = PROJECT_ROOT / "outputs" / "labor_shareholder_distribution" / "tables"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "labor_shareholder_distribution" / "panel_fe"


@dataclass(frozen=True)
class PanelFEOutputs:
    regression_path: Path
    firm_tilt_path: Path
    report_path: Path


def _safe_log(series: pd.Series) -> pd.Series:
    return np.log(series.where(series > 0))


def _winsorize(series: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
    lo, hi = series.quantile([lower, upper])
    return series.clip(lo, hi)


def load_panel() -> pd.DataFrame:
    panel = pd.read_csv(INPUT_DIR / "firm_year_panel.csv", dtype={"ticker": str})
    panel["ticker"] = panel["ticker"].str.zfill(6)
    panel = panel[panel["analysis_sample"].astype(bool)].copy()
    panel = panel[panel["fiscal_year"].between(2010, 2025)].copy()

    panel["labor_share"] = _winsorize(panel["labor_share_bottom_up"])
    panel["payout_share"] = _winsorize(panel["shareholder_payout_to_va"])
    panel["dividend_share"] = _winsorize(panel["dividend_to_va"])
    panel["buyback_share"] = _winsorize(panel["buyback_to_va"])
    panel["log_value_added"] = _safe_log(panel["value_added_trn"])
    panel["log_employee_comp"] = _safe_log(panel["employee_comp_trn"])
    panel["payout_intensity"] = panel["payout_share"] - panel["labor_share"]
    return panel.dropna(
        subset=[
            "ticker",
            "company_name",
            "fiscal_year",
            "labor_share",
            "payout_share",
            "dividend_share",
            "buyback_share",
            "log_value_added",
        ]
    )


def _demean_by_groups(df: pd.DataFrame, columns: list[str], groups: list[str], max_iter: int = 100) -> pd.DataFrame:
    residual = df[columns].astype(float).copy()
    for _ in range(max_iter):
        previous = residual.to_numpy().copy()
        for group in groups:
            residual = residual - residual.groupby(df[group]).transform("mean")
        if np.nanmax(np.abs(residual.to_numpy() - previous)) < 1e-10:
            break
    return residual


def _ols(y: np.ndarray, x: np.ndarray, groups: pd.Series) -> dict[str, np.ndarray | float | int]:
    valid = np.isfinite(y) & np.isfinite(x).all(axis=1)
    y = y[valid]
    x = x[valid]
    groups = groups.loc[valid].to_numpy()
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    resid = y - x @ beta
    nobs, k = x.shape
    dof = max(nobs - k, 1)
    sigma2 = float((resid @ resid) / dof)
    xtx_inv = np.linalg.pinv(x.T @ x)
    se = np.sqrt(np.diag(sigma2 * xtx_inv))
    meat = np.zeros((k, k))
    for group in np.unique(groups):
        idx = groups == group
        xg = x[idx]
        ug = resid[idx][:, None]
        score = xg.T @ ug
        meat += score @ score.T
    g = len(np.unique(groups))
    finite_correction = (g / max(g - 1, 1)) * ((nobs - 1) / max(nobs - k, 1))
    clustered_cov = finite_correction * xtx_inv @ meat @ xtx_inv
    clustered_se = np.sqrt(np.clip(np.diag(clustered_cov), 0, np.inf))
    tstat = beta / se
    clustered_tstat = beta / clustered_se
    ssr = float(resid @ resid)
    tss = float(((y - y.mean()) @ (y - y.mean())))
    r2 = 1 - ssr / tss if tss else np.nan
    return {
        "beta": beta,
        "se": se,
        "tstat": tstat,
        "clustered_se": clustered_se,
        "clustered_tstat": clustered_tstat,
        "nobs": nobs,
        "clusters": g,
        "r2_within": r2,
    }


def run_fe_regressions(panel: pd.DataFrame) -> pd.DataFrame:
    specs = [
        {
            "model": "M1 labor_share_on_payout",
            "dependent": "labor_share",
            "independent": ["payout_share", "log_value_added"],
            "interpretation": "동일 기업 내 주주환원율 상승이 노동소득분배율 변화와 연결되는지 검정",
        },
        {
            "model": "M2 payout_on_labor_share",
            "dependent": "payout_share",
            "independent": ["labor_share", "log_value_added"],
            "interpretation": "동일 기업 내 노동 몫이 낮아질수록 주주환원율이 높아지는지 검정",
        },
        {
            "model": "M3 labor_share_on_dividend_buyback",
            "dependent": "labor_share",
            "independent": ["dividend_share", "buyback_share", "log_value_added"],
            "interpretation": "배당과 자사주 취득 중 어느 쪽이 노동 몫 변화와 더 관련 있는지 분해",
        },
    ]

    rows = []
    for spec in specs:
        cols = [spec["dependent"]] + spec["independent"]
        work = panel.dropna(subset=cols + ["ticker", "fiscal_year"]).copy()
        transformed = _demean_by_groups(work, cols, ["ticker", "fiscal_year"])
        y = transformed[spec["dependent"]].to_numpy()
        x = transformed[spec["independent"]].to_numpy()
        result = _ols(y, x, work["ticker"])

        for i, var in enumerate(spec["independent"]):
            rows.append(
                {
                    "model": spec["model"],
                    "dependent": spec["dependent"],
                    "variable": var,
                    "coefficient": result["beta"][i],
                    "std_error": result["se"][i],
                    "t_stat": result["tstat"][i],
                    "clustered_std_error": result["clustered_se"][i],
                    "clustered_t_stat": result["clustered_tstat"][i],
                    "nobs": result["nobs"],
                    "firm_clusters": result["clusters"],
                    "within_r2": result["r2_within"],
                    "fixed_effects": "firm + fiscal_year",
                    "interpretation": spec["interpretation"],
                }
            )
    return pd.DataFrame(rows)


def build_firm_tilt_table(panel: pd.DataFrame) -> pd.DataFrame:
    firm = (
        panel.groupby(["ticker", "company_name"], as_index=False)
        .agg(
            years=("fiscal_year", "nunique"),
            first_year=("fiscal_year", "min"),
            last_year=("fiscal_year", "max"),
            avg_labor_share=("labor_share", "mean"),
            avg_payout_share=("payout_share", "mean"),
            avg_dividend_share=("dividend_share", "mean"),
            avg_buyback_share=("buyback_share", "mean"),
            avg_value_added_trn=("value_added_trn", "mean"),
            latest_labor_share=("labor_share", "last"),
            latest_payout_share=("payout_share", "last"),
        )
        .query("years >= 8")
        .copy()
    )
    firm["shareholder_over_labor_tilt"] = firm["avg_payout_share"] - firm["avg_labor_share"]
    firm["payout_to_labor_ratio"] = firm["avg_payout_share"] / firm["avg_labor_share"].replace(0, np.nan)
    firm = firm.sort_values(["shareholder_over_labor_tilt", "avg_payout_share"], ascending=False)
    return firm


def write_report(panel: pd.DataFrame, regressions: pd.DataFrame, firm_tilt: pd.DataFrame, output_path: Path) -> None:
    m1 = regressions[(regressions["model"].eq("M1 labor_share_on_payout")) & (regressions["variable"].eq("payout_share"))].iloc[0]
    m2 = regressions[(regressions["model"].eq("M2 payout_on_labor_share")) & (regressions["variable"].eq("labor_share"))].iloc[0]
    top = firm_tilt.head(10)

    def pct(x: float) -> str:
        return f"{x * 100:.2f}%"

    lines = [
        "# 기업 패널 고정효과 분석: 어떤 기업이 노동 대신 주주환원을 택하는가",
        "",
        "## 1. 분석 목적",
        "",
        "시장 전체 시계열에서 노동 몫과 주주환원의 강한 음의 관계가 확인되지 않을 수 있다. 이 경우 더 적절한 질문은 기업 단위다. 즉, 동일 기업이 시간에 따라 주주환원을 확대할 때 노동소득분배율을 낮추는지 검정한다.",
        "",
        "## 2. 표본과 변수",
        "",
        f"- 표본: 2010~2025년, 비금융 추정 KOSPI firm-year {len(panel):,}개",
        "- 종속변수 후보: 노동소득분배율, 주주환원/부가가치",
        "- 핵심 설명변수: 배당+자사주 취득/부가가치, 노동소득분배율",
        "- 통제변수: log(부가가치)",
        "- 고정효과: 기업 고정효과 + 연도 고정효과",
        "- 표준오차: 일반 OLS 표준오차와 기업 단위 군집표준오차를 함께 산출했다. 해석은 더 보수적인 clustered t-stat 중심으로 본다.",
        "- 극단값 처리를 위해 주요 비율은 1%/99% winsorization을 적용했다.",
        "",
        "## 3. 회귀 결과 해석",
        "",
        f"- M1에서 주주환원율 계수는 {m1['coefficient']:.4f}, clustered t-stat {m1['clustered_t_stat']:.2f}다.",
        f"- M2에서 노동소득분배율 계수는 {m2['coefficient']:.4f}, clustered t-stat {m2['clustered_t_stat']:.2f}다.",
        "",
        "M1 계수가 음수라면 동일 기업 내에서 주주환원 확대와 노동 몫 하락이 함께 나타났다는 의미다. 양수라면 수익성 또는 부가가치 창출이 커지는 국면에서 노동 몫과 주주환원이 동시에 늘어나는 성격이 더 강하다는 뜻이다.",
        "",
        "주의할 점도 있다. 노동소득분배율과 주주환원율은 모두 부가가치를 분모로 쓰므로, 부가가치 변동이 두 비율을 동시에 흔드는 기계적 효과가 일부 남아 있을 수 있다. 그래서 본 결과는 인과 결론이 아니라 연구가설을 좁히는 1차 패널 검정으로 해석한다.",
        "",
        "## 4. 주주환원 성향 상위 기업",
        "",
        "| 순위 | 종목코드 | 기업명 | 관측연수 | 평균 노동몫 | 평균 주주환원율 | 평균 자사주율 | 평균 배당률 |",
        "|---:|---|---|---:|---:|---:|---:|---:|",
    ]
    for i, row in enumerate(top.itertuples(index=False), start=1):
        lines.append(
            f"| {i} | {row.ticker} | {row.company_name} | {int(row.years)} | {pct(row.avg_labor_share)} | {pct(row.avg_payout_share)} | {pct(row.avg_buyback_share)} | {pct(row.avg_dividend_share)} |"
        )

    lines.extend(
        [
            "",
            "## 5. 결론",
            "",
            "이 분석은 첫 번째 패널 실험이다. 현재 변수만으로는 기업 규모 외 통제가 제한적이므로, 다음 단계에서는 영업이익률, 부채비율, 현금보유, 매출성장률, 산업 더미를 붙여야 한다. 그럼에도 기업/연도 고정효과를 넣었기 때문에 단순 시장 사이클이나 기업별 평균 차이를 제거한 첫 검정으로 의미가 있다.",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def run_analysis() -> PanelFEOutputs:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    panel = load_panel()
    regressions = run_fe_regressions(panel)
    firm_tilt = build_firm_tilt_table(panel)

    regression_path = OUTPUT_DIR / "fixed_effect_regression_results.csv"
    firm_tilt_path = OUTPUT_DIR / "firm_shareholder_over_labor_tilt.csv"
    report_path = OUTPUT_DIR / "Panel_FE_Labor_vs_Shareholder_Report.md"

    regressions.to_csv(regression_path, index=False, encoding="utf-8-sig")
    firm_tilt.to_csv(firm_tilt_path, index=False, encoding="utf-8-sig")
    write_report(panel, regressions, firm_tilt, report_path)

    return PanelFEOutputs(regression_path, firm_tilt_path, report_path)


if __name__ == "__main__":
    outputs = run_analysis()
    print(f"regression={outputs.regression_path}")
    print(f"firm_tilt={outputs.firm_tilt_path}")
    print(f"report={outputs.report_path}")

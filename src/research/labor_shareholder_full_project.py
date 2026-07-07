from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.research import labor_shareholder_distribution as dist
from src.research import labor_shareholder_panel_fe as fe

OUTPUT_ROOT = PROJECT_ROOT / "outputs" / "labor_shareholder_distribution"
FINAL_REPORT = OUTPUT_ROOT / "reports" / "Labor_vs_Shareholder_Distribution_Full_Project_Report.md"


@dataclass(frozen=True)
class FullProjectOutputs:
    distribution_outputs: dist.LaborShareholderOutputs
    panel_fe_outputs: fe.PanelFEOutputs
    final_report_path: Path


def _pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def _fmt(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}"


def _model_row(regressions: pd.DataFrame, model: str, variable: str) -> pd.Series:
    return regressions[(regressions["model"].eq(model)) & (regressions["variable"].eq(variable))].iloc[0]


def write_full_report(final_report_path: Path) -> None:
    tables_dir = OUTPUT_ROOT / "tables"
    panel_dir = OUTPUT_ROOT / "panel_fe"

    firm_year = pd.read_csv(tables_dir / "firm_year_panel.csv", dtype={"ticker": str})
    annual = pd.read_csv(tables_dir / "annual_distribution_summary.csv")
    corr = pd.read_csv(tables_dir / "labor_shareholder_correlations.csv")
    regressions = pd.read_csv(panel_dir / "fixed_effect_regression_results.csv")
    firm_tilt = pd.read_csv(panel_dir / "firm_shareholder_over_labor_tilt.csv", dtype={"ticker": str})
    firm_tilt["ticker"] = firm_tilt["ticker"].str.zfill(6)

    core = annual[annual["firm_count"].ge(100)].copy()
    if core.empty:
        core = annual.copy()

    first = core.iloc[0]
    latest = core.iloc[-1]
    full_first_year = int(annual["fiscal_year"].min())
    full_last_year = int(annual["fiscal_year"].max())
    core_first_year = int(core["fiscal_year"].min())
    core_last_year = int(core["fiscal_year"].max())

    core_corr = dist.build_correlations(core)
    level_corr = core_corr.loc[core_corr["relationship"].eq("level_labor_vs_payout"), "pearson_corr"].iloc[0]
    change_corr = core_corr.loc[core_corr["relationship"].eq("change_labor_vs_payout"), "pearson_corr"].iloc[0]
    full_level_corr = corr.loc[corr["relationship"].eq("level_labor_vs_payout"), "pearson_corr"].iloc[0]

    m1 = _model_row(regressions, "M1 labor_share_on_payout", "payout_share")
    m2 = _model_row(regressions, "M2 payout_on_labor_share", "labor_share")
    m3_div = _model_row(regressions, "M3 labor_share_on_dividend_buyback", "dividend_share")
    m3_buyback = _model_row(regressions, "M3 labor_share_on_dividend_buyback", "buyback_share")

    top_names = ", ".join(
        f"{row.company_name}({row.ticker})"
        for row in firm_tilt.head(5).itertuples(index=False)
    )

    lines = [
        "# 노동 vs 주주 분배 프로젝트 전체 보고서",
        "",
        "## 1. 이 프로젝트가 던진 질문",
        "",
        "이 프로젝트의 출발점은 단순하다. 기업이 창출한 부가가치가 노동자와 주주에게 어떻게 나뉘는가를 데이터로 확인하는 것이다. 더 구체적으로는 두 질문을 검정했다.",
        "",
        "1. KOSPI 기업 전체로 보면 노동소득분배율과 주주환원이 장기적으로 어떤 방향으로 움직이는가?",
        "2. 시장 전체에서는 뚜렷하지 않더라도, 같은 기업 내부에서는 주주환원 확대가 노동 몫 축소와 연결되는가?",
        "",
        "두 번째 질문이 특히 중요하다. 시장 전체 시계열은 경기, 이익 사이클, 표본 구성 변화가 섞인다. 그래서 전체 평균에서 강한 관계가 안 보인다고 해서 기업의 배분 선택이 없다고 말할 수 없다. 이 프로젝트는 거시적 집계와 미시적 기업 패널을 순서대로 연결해 그 차이를 확인했다.",
        "",
        "## 2. 데이터 파이프라인",
        "",
        "- 원천 파일: `kospi07-11.xlsx`, `kospi12-16.xlsx`, `kospi 17-21.xlsx`, `kospi22-26.xlsx`",
        "- 원천 형태: 월별로 반복 저장된 TS2000 스타일 재무 패널",
        "- 처리 방식: `거래소코드-회계연도` 단위로 접고, 연간 재무제표 해석에 맞게 `/12` 결산만 사용",
        "- 분석 기간: 원자료 기준 " + f"{full_first_year}~{full_last_year}년",
        "- 핵심 해석 구간: 기업 수가 100개 이상 확보되는 " + f"{core_first_year}~{core_last_year}년",
        "- 최종 분석 표본: 전체 firm-year " + f"{len(firm_year):,}개 중 분석 가능 관측치 {int(firm_year['analysis_sample'].sum()):,}개",
        "",
        "핵심 변수는 모두 단위를 통일했다. `종업원 급여비용`, `현금배당`, `자기주식의 취득`은 천원 단위라 조원으로 나눴고, `부가가치`는 백만원 단위라 조원 기준으로 변환했다.",
        "",
        "## 3. 변수 정의",
        "",
        "- 노동소득분배율: `종업원 급여비용 / 부가가치`",
        "- 주주환원율: `(현금배당 + 자기주식 취득) / 부가가치`",
        "- 배당률: `현금배당 / 부가가치`",
        "- 자사주율: `자기주식 취득 / 부가가치`",
        "- 금융업 추정 기업과 부가가치 또는 급여비용이 0 이하인 관측치는 제외",
        "",
        "노동소득분배율은 데이터 제공값도 있지만, 본 연구의 주 분석값은 시장 전체 급여비용 합계를 시장 전체 부가가치 합계로 나눈 bottom-up 지표다. 이 방식은 기업별 극단값에 덜 흔들리고 경제적 해석이 쉽다.",
        "",
        "## 4. 1단계: KOSPI 전체 시계열 분석",
        "",
        f"- {core_first_year}년 노동소득분배율: {_pct(first['labor_share_bottom_up'])}",
        f"- {core_last_year}년 노동소득분배율: {_pct(latest['labor_share_bottom_up'])}",
        f"- {core_last_year}년 주주환원율: {_pct(latest['shareholder_payout_to_va'])}",
        f"- {core_last_year}년 배당: {_fmt(latest['dividend_trn'])}조원",
        f"- {core_last_year}년 자사주 취득: {_fmt(latest['share_buyback_trn'])}조원",
        f"- {core_first_year}~{core_last_year}년 노동소득분배율과 주주환원율 수준 상관계수: {level_corr:.3f}",
        f"- {core_first_year}~{core_last_year}년 전년 대비 변화 상관계수: {change_corr:.3f}",
        f"- 전체 {full_first_year}~{full_last_year}년 수준 상관계수: {full_level_corr:.3f}",
        "",
        "시계열 결과만 보면 강한 대체관계는 보이지 않는다. 핵심 구간에서는 노동 몫과 주주환원율의 상관이 작고, 전체 기간을 사용하면 2008~2009년의 낮은 커버리지 때문에 상관이 달라질 수 있다. 따라서 시장 전체 평균만으로는 '노동 대신 주주'라는 강한 결론을 내기 어렵다.",
        "",
        "## 5. 2단계: 기업 패널 고정효과 분석",
        "",
        "그래서 두 번째 단계에서는 기업별 패널로 내려갔다. 같은 기업의 평균적 특성은 기업 고정효과로 제거하고, 특정 연도의 공통 충격은 연도 고정효과로 제거했다. 표준오차는 기업 단위 군집표준오차를 사용했다.",
        "",
        "주요 회귀식은 다음과 같다.",
        "",
        "`노동소득분배율_it = β × 주주환원율_it + γ × log(부가가치_it) + 기업FE_i + 연도FE_t + ε_it`",
        "",
        f"- M1 주주환원율 계수: {m1['coefficient']:.4f}, clustered t-stat {m1['clustered_t_stat']:.2f}",
        f"- M2 노동소득분배율 계수: {m2['coefficient']:.4f}, clustered t-stat {m2['clustered_t_stat']:.2f}",
        f"- 배당률 계수: {m3_div['coefficient']:.4f}, clustered t-stat {m3_div['clustered_t_stat']:.2f}",
        f"- 자사주율 계수: {m3_buyback['coefficient']:.4f}, clustered t-stat {m3_buyback['clustered_t_stat']:.2f}",
        "",
        "패널 회귀에서는 주주환원율 계수가 음수이고 통계적으로도 뚜렷하다. 즉, 시장 전체 평균에서는 강한 대체관계가 흐릿하지만, 같은 기업 내부의 시간 변화로 보면 주주환원율이 높아질 때 노동소득분배율이 낮아지는 경향이 관찰된다.",
        "",
        "흥미로운 점은 배당률의 음의 관계가 강하고, 자사주율은 유의성이 약하다는 것이다. 이 결과는 현재 데이터에서는 '자사주 취득'보다 '현금배당 중심 주주환원'이 노동 몫과 더 강하게 반대로 움직인다는 가설을 제시한다.",
        "",
        "## 6. 어떤 기업이 주주환원 성향이 강한가",
        "",
        "장기 평균 기준으로 주주환원율이 노동 몫보다 높은 기업들을 별도로 산출했다. 상위 기업 예시는 다음과 같다.",
        "",
        top_names,
        "",
        "상위권에는 지주회사 성격의 기업이 다수 포함된다. 이는 중요한 해석 포인트다. 지주회사는 자체 고용과 직접 생산활동이 작고 배당수익 또는 지분 구조를 통해 현금이 흐르는 경우가 많다. 따라서 '노동 대신 주주'라는 표현을 모든 업종에 동일하게 적용하기보다는, 지주회사/사업회사/제조업/서비스업을 분리해야 한다.",
        "",
        "## 7. 연구적 의미",
        "",
        "이 프로젝트의 가장 큰 의미는 동일한 주제를 두 층위에서 확인했다는 점이다. 첫째, 시장 전체 집계에서는 노동 몫과 주주환원이 반드시 정면 충돌하지 않는다. 이는 경기와 이익 사이클이 둘을 동시에 움직일 수 있기 때문이다. 둘째, 기업 패널 고정효과로 내려가면 같은 기업 내부의 배분 선택에서는 주주환원 확대와 노동 몫 하락이 함께 나타난다.",
        "",
        "따라서 연구 가설은 이렇게 정리할 수 있다.",
        "",
        "`한국 상장기업에서 노동-주주 배분의 대체관계는 시장 전체 평균보다 기업 내부 패널 변화에서 더 명확하게 관찰된다.`",
        "",
        "이 가설은 금융공학/퀀트 관점에서도 확장 가능하다. 예를 들어 노동 몫이 급격히 낮아지고 주주환원이 커진 기업이 향후 초과수익을 내는지, 아니면 장기 성장성 훼손으로 밸류에이션 디스카운트를 받는지 검정할 수 있다. 즉, 이 연구는 단순한 사회경제 분석을 넘어 투자전략 팩터로 발전할 여지가 있다.",
        "",
        "## 8. 한계와 다음 단계",
        "",
        "- 산업분류가 아직 명시적으로 붙지 않았다. 지주회사와 사업회사를 분리해야 한다.",
        "- 노동소득분배율과 주주환원율 모두 부가가치를 분모로 쓰므로 분모 효과가 일부 남아 있을 수 있다.",
        "- 인과관계로 주장하려면 영업이익률, 부채비율, 현금보유, 매출성장률, CAPEX, 종업원 수 변화 등을 추가해야 한다.",
        "- 다음 단계에서는 주주환원 확대 기업의 향후 주가수익률, 밸류에이션 변화, 고용/임금 변화까지 연결하면 논문형 프로젝트가 된다.",
        "",
        "## 9. 산출물 위치",
        "",
        "- 연간 요약표: `outputs/labor_shareholder_distribution/tables/annual_distribution_summary.csv`",
        "- 기업 패널: `outputs/labor_shareholder_distribution/tables/firm_year_panel.csv`",
        "- 시계열 차트: `outputs/labor_shareholder_distribution/charts/`",
        "- 고정효과 회귀표: `outputs/labor_shareholder_distribution/panel_fe/fixed_effect_regression_results.csv`",
        "- 기업별 주주환원 성향 랭킹: `outputs/labor_shareholder_distribution/panel_fe/firm_shareholder_over_labor_tilt.csv`",
    ]
    final_report_path.write_text("\n".join(lines), encoding="utf-8")


def run_full_project() -> FullProjectOutputs:
    distribution_outputs = dist.run_analysis(skip_charts=False)
    panel_fe_outputs = fe.run_analysis()
    FINAL_REPORT.parent.mkdir(parents=True, exist_ok=True)
    write_full_report(FINAL_REPORT)
    return FullProjectOutputs(distribution_outputs, panel_fe_outputs, FINAL_REPORT)


if __name__ == "__main__":
    outputs = run_full_project()
    print(f"annual={outputs.distribution_outputs.annual_path}")
    print(f"charts={len(outputs.distribution_outputs.chart_paths)}")
    print(f"regression={outputs.panel_fe_outputs.regression_path}")
    print(f"firm_tilt={outputs.panel_fe_outputs.firm_tilt_path}")
    print(f"final_report={outputs.final_report_path}")

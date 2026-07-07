# Data Input Schema

이 문서는 프로젝트에 넣을 CSV 입력 형식을 정의합니다. 원천 데이터는 `data/raw/`에 보관하고, 코드에서는 가능한 한 아래 표준 컬럼명을 사용합니다.

첨부된 TS2000 엑셀처럼 원천 컬럼명이 긴 경우에는 원본을 보존한 뒤 loader에서 표준 컬럼명으로 매핑합니다.

## 1. Price Data

권장 파일 위치:

```text
data/raw/price/prices.csv
```

일별 종목 가격 데이터입니다. 가격은 KIS API의 국내주식 기간별 시세에서 수집하고, 가능하면 수정주가 기준을 사용합니다.

| Column | Required | Type | Description |
| --- | --- | --- | --- |
| date | Y | date | 거래일, `YYYY-MM-DD` |
| ticker | Y | string | 종목코드, 6자리 문자열 권장 |
| name | N | string | 종목명 |
| open | N | float | 시가 |
| high | N | float | 고가 |
| low | N | float | 저가 |
| close | Y | float | 종가 |
| adj_close | Y | float | 수정종가 |
| volume | Y | float | 거래량 |
| trading_value | Y | float | 거래대금, KRW |
| market_cap | Recommended | float | 시가총액, KRW |
| sector | Recommended | string | GICS 또는 KRX 업종 |
| is_suspended | N | bool | 거래정지 여부 |
| is_administrative | N | bool | 관리종목 여부 |

주의사항:

- `ticker`는 Excel에서 앞자리 0이 사라지지 않도록 문자열로 저장합니다.
- 수익률 계산에는 `adj_close`를 우선 사용합니다.
- 유동성 필터는 20일 평균 `trading_value`로 계산합니다.
- KIS 일별 차트 응답만으로 부족한 `market_cap`, `sector`, 관리종목 여부는 유니버스/섹터 데이터와 결합해 보강합니다.

## 2. TS2000 Fundamentals

권장 파일 위치:

```text
data/raw/ts2000/fundamentals.csv
```

재무데이터는 결산일이 아니라 투자자가 사용할 수 있었던 날짜 기준으로 정렬되어야 합니다. 공시일이 없다면 보수적 lag를 적용합니다.

| Column | Required | Type | Description |
| --- | --- | --- | --- |
| ticker | Y | string | 종목코드 |
| name | N | string | 종목명 |
| fiscal_period | Y | string | 회계기간, 예: `2025-12` |
| fiscal_year | Recommended | int | 회계연도 |
| fiscal_quarter | N | int | 회계분기 |
| report_date | Recommended | date | 공시일 또는 보고서 제출일 |
| available_date | Y | date | 팩터 계산에 사용할 수 있는 날짜 |
| research_split | Recommended | string | `train`, `validation`, `test`; `available_date` 기준 |
| assets | Recommended | float | 자산 |
| equity | Recommended | float | 자본 |
| liabilities | Recommended | float | 부채 |
| revenue | Recommended | float | 매출액 |
| operating_income | Recommended | float | 영업이익 |
| net_income | Recommended | float | 당기순이익 |
| operating_cash_flow | Recommended | float | 영업활동현금흐름 |
| shares_outstanding | Recommended | float | 발행주식수 |
| preferred_shares | N | float | 우선주 수 |
| close | N | float | 결산 또는 기준 시점 종가 |
| market_cap | Recommended | float | 시가총액 |
| per | Recommended | float | PER |
| pbr | Recommended | float | PBR |
| psr | Recommended | float | PSR |
| pcr | N | float | PCR |
| ev_ebitda | N | float | EV/EBITDA |
| roe | Recommended | float | ROE |
| roa | Recommended | float | ROA |
| operating_margin | Recommended | float | 영업이익률 |
| net_margin | N | float | 순이익률 |
| debt_ratio | Recommended | float | 부채비율 |
| sales_growth | N | float | 매출액증가율 |
| asset_growth | N | float | 총자본증가율 또는 자산성장률 |
| operating_cash_flow_to_net_income | N | float | 영업현금흐름 / 순이익 |
| sector | Recommended | string | 업종 |

기존 단일 TS2000 엑셀의 주요 원천 컬럼 후보:

- `회사명` -> `name`
- `거래소코드` -> `ticker`
- `회계년도` -> `fiscal_period`
- `[공통]자산(*)(IFRS)(천원)` -> `assets`
- `[공통]자본(*)(IFRS)(천원)` -> `equity`
- `[공통]부채(*)(IFRS)(천원)` -> `liabilities`
- `[공통]* (정상)영업손익(계산수치)(IFRS)(천원)` -> `operating_income`
- `[공통]당기순이익(손실)(IFRS)(천원)` -> `net_income`
- `[공통]영업활동으로 인한 현금흐름(간접법)(*)(IFRS)(천원)` -> `operating_cash_flow`
- `[공통]* 발행한 주식총수(*)(IFRS)(주)` -> `shares_outstanding`
- `[공통]종가(원)` -> `close`
- `[공통]자기자본순이익률(IFRS)` -> `roe`

2007~2026 장기 wide TS2000 엑셀은 컬럼 앞에 TS2000 계정 코드가 붙어 있습니다. 원본 496개 컬럼은 `outputs/tables/ts2000_wide_column_dictionary.csv`에 사전으로 저장하고, 모델에는 다음 핵심 컬럼을 우선 표준화합니다.

- `[A100000000][공통]자산(*)(IFRS)(천원)` -> `assets`
- `[A600000000][공통]자본(*)(IFRS)(천원)` -> `equity`
- `[A800000000][공통]부채(*)(IFRS)(천원)` -> `liabilities`
- `[B430000000][공통]* (정상)영업손익(계산수치)(IFRS)(천원)` -> `operating_income`
- `[B840000000][공통]당기순이익(손실)(IFRS)(천원)` -> `net_income`
- `[D100000000][공통]영업활동으로 인한 현금흐름(간접법)(*)(IFRS)(천원)` -> `operating_cash_flow`
- `[공통]1주당매출액(IFRS)(원)` -> `revenue` 추정 보조값
- `[공통]매출액증가율(IFRS)` -> `sales_growth`
- `[공통]총자본증가율(IFRS)` -> `asset_growth`
- `[공통]PER(최고/최저)(IFRS)`, `[공통]PBR(최고/최저)(IFRS)`, `[공통]PCR(최고/최저)(IFRS)`, `[공통]PSR(최고/최저)(IFRS)` -> 가치평가 보조값

주의사항:

- TS2000 금액 단위가 천원인 경우 KRW로 변환할지, 천원 단위로 유지할지 loader에서 일관되게 처리합니다.
- `available_date`가 없으면 결산월 이후 3개월 또는 보수적인 lag를 적용하고 README와 리포트에 한계를 명시합니다.
- 학습/검증/테스트 분리는 결산일이 아니라 `available_date` 기준으로 수행합니다.
- 결측치가 많은 지표는 factor_config 기준에 따라 제외하거나 cross-sectional median으로 처리합니다.

## 3. Benchmark Data

권장 파일 위치:

```text
data/raw/benchmark/benchmark.csv
```

| Column | Required | Type | Description |
| --- | --- | --- | --- |
| date | Y | date | 거래일 |
| benchmark | Y | string | 예: `KOSPI200`, `KOSPI` |
| close | Y | float | 지수 종가 |
| return | N | float | 일별 수익률. 없으면 코드에서 계산 |

## 4. KOSPI200 Constituents

권장 파일 위치:

```text
data/raw/benchmark/kospi200_constituents.csv
```

| Column | Required | Type | Description |
| --- | --- | --- | --- |
| effective_date | Y | date | 구성종목 적용 시작일 |
| ticker | Y | string | 종목코드 |
| name | N | string | 종목명 |
| sector | Recommended | string | 업종 |
| is_preferred_share | N | bool | 우선주 여부 |
| is_spac | N | bool | SPAC 여부 |
| is_suspended | N | bool | 거래정지 여부 |
| is_administrative | N | bool | 관리종목 여부 |

구성종목 이력이 없으면 현재 KOSPI200 구성종목으로 시작할 수 있습니다. 이 경우 survivorship bias를 반드시 명시합니다.

## 5. Expected Output Tables

실제 데이터와 구현이 준비된 뒤 다음 파일을 생성합니다.

| Output | Location | Description |
| --- | --- | --- |
| factor_scores.csv | outputs/tables/ | 리밸런싱일별 종목 팩터 점수 |
| monthly_portfolio_weights.csv | outputs/portfolios/ | 월별 포트폴리오 비중 |
| backtest_performance.csv | outputs/tables/ | 월별 수익률, 누적수익률, benchmark 비교 |
| current_model_portfolio.csv | outputs/portfolios/ | 최신 리밸런싱 기준 모델 포트폴리오 |

현재 scaffold에서는 위 결과 파일을 생성하지 않습니다.

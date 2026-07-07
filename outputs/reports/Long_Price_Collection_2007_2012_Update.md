# Long Price Collection Update: 2007-2012

## 1. 수집 결과

KIS API를 사용해 현재 KOSPI200 구성종목 기준 2007~2012 일별 가격 데이터를 수집했다. 연도별 CSV를 먼저 저장한 뒤 통합 CSV로 결합했다.

| Year | Rows | Tickers | Date Range | Duplicate Ticker-Dates |
| --- | ---: | ---: | --- | ---: |
| 2007 | 29,642 | 124 | 2007-01-02 ~ 2007-12-28 | 0 |
| 2008 | 31,025 | 127 | 2008-01-02 ~ 2008-12-30 | 0 |
| 2009 | 32,500 | 132 | 2009-01-02 ~ 2009-12-30 | 0 |
| 2010 | 34,133 | 138 | 2010-01-04 ~ 2010-12-30 | 0 |
| 2011 | 35,454 | 146 | 2011-01-03 ~ 2011-12-29 | 0 |
| 2012 | 36,317 | 148 | 2012-01-02 ~ 2012-12-28 | 0 |

통합 파일:

- `data/raw/price/prices_2007_2026.csv`

현재 통합 범위:

- Rows: 199,071
- Tickers: 148
- Date Range: 2007-01-02 ~ 2012-12-28
- Duplicate ticker-date rows: 0

## 2. 팩터 생성

2007~2012 가격 데이터로 Momentum/Low Volatility 팩터를 생성했고, 장기 TS2000 재무 팩터와 as-of 결합했다.

생성 파일:

- `data/features/price_factor_scores_2007_2012.csv`
- `data/features/integrated_factor_scores_2007_2012.csv`

통합 팩터 coverage:

- Rows: 9,609
- Tickers: 148
- Signal Date: 2007-01-31 ~ 2012-12-28

## 3. 백테스트 결과

2007~2012 통합 멀티팩터 백테스트:

| Metric | Value |
| --- | ---: |
| Total Return | 161.96% |
| CAGR | 19.71% |
| Annualized Volatility | 24.10% |
| Sharpe | 0.82 |
| Max Drawdown | -46.79% |
| Benchmark Total Return | 74.55% |
| Active Total Return | 50.07% |
| Information Ratio | 0.67 |
| Average Turnover | 20.05% |
| Rebalance Count | 65 |

벤치마크는 현재 장기 KOSPI200/KODEX200 벤치마크가 2007년까지 확장되지 않았기 때문에 유니버스 동일가중으로 계산했다.

## 4. 해석

2007~2012는 2008 금융위기와 2011 유럽 재정위기 구간을 포함한다. 따라서 최대낙폭 -46.79%는 위기 구간의 손실을 반영한다. 반면 6년 누적 성과와 유니버스 동일가중 대비 active return은 양호하게 나타났다.

면접용 해석은 다음처럼 정리할 수 있다.

> 장기 가격 데이터를 KIS API로 직접 구축했고, 2008 금융위기와 2011 유럽 재정위기를 포함한 스트레스 구간에서 통합 멀티팩터 모델을 검증했다. 단순 상승장 샘플이 아니라 하락장과 회복장을 포함한 초기 out-of-sample 구조를 만들었다.

## 5. 다음 단계

- 2013~2016 가격 데이터 수집
- 2007~2016을 train 구간으로 확정
- 2017~2021 validation 구간 수집
- 2022~2026 test 구간과 기존 KIS 가격 데이터 결합
- 장기 KOSPI200 또는 KODEX200 벤치마크 확장
- regime-aware strategy를 2008/2011 위기 구간에서 재검증

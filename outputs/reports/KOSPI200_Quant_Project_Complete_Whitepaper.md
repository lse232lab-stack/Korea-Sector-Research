# KOSPI200 Quant Research Project Complete Whitepaper

작성일: 2026-07-04  
프로젝트 위치: `kospi200_factor_model`

## 0. 이 문서의 목적

이 문서는 KOSPI200 퀀트 리서치 프로젝트가 처음 어떤 문제의식에서 시작되었고, 어떤 데이터를 수집했으며, 어떤 가정과 설정으로 팩터와 전략을 설계했고, 검증 결과가 어떻게 나왔는지를 처음부터 끝까지 설명하는 전체 연구 보고서다. 단순 결과 요약이 아니라, 각 설정이 의미하는 바와 그 설정이 성과 해석에 어떤 영향을 주는지까지 함께 설명한다.

이 프로젝트는 취업 포트폴리오이면서 동시에 실제 증권사 리서치센터 퀀트분석가, S&T 전략/퀀트, 자산운용 퀀트 리서치 직무에서 요구하는 역량을 보여주기 위한 연구 프로젝트다. 따라서 핵심 목표는 세 가지다.

1. 한국 대형주 데이터로 설명 가능한 팩터 전략을 설계한다.
2. 데이터 누수와 과최적화를 줄이는 검증 구조를 만든다.
3. 성과가 좋은 전략뿐 아니라 한계, 리스크, 실무 적용 조건까지 명확히 설명한다.

## 1. 연구의 출발점

### 1.1 최초 연구 질문

프로젝트의 최초 질문은 다음이었다.

> 한국 KOSPI200 종목에서 Value, Quality, Growth, Momentum, Low Volatility 팩터는 향후 수익률을 설명하는가? 그리고 검증된 팩터를 활용해 KOSPI200 대비 초과성과를 추구하는 Model Portfolio를 만들 수 있는가?

이 질문은 전형적인 퀀트 리서치 질문이다. 단순히 “어떤 종목을 사면 오를까”가 아니라, 여러 종목을 같은 기준으로 점수화하고, 그 점수가 미래 수익률과 통계적으로 관련되는지 확인한 뒤, 실제 포트폴리오로 구성했을 때 성과가 유지되는지 보는 구조다.

### 1.2 프로젝트가 점차 확장된 방향

초기에는 Value/Quality 중심의 재무 팩터 모델에서 시작했다. 이후 가격 데이터가 2007~2026년까지 확장되면서 Momentum, Low Volatility, 장기 백테스트, ML 예측 모델, 국면대응 전략, 사전과제형 분석 팩, 논문 초안까지 확장되었다.

현재 프로젝트는 다음 단계까지 포함한다.

1. KIS API 가격 데이터 수집
2. TS2000 장기 재무 데이터 표준화
3. KOSPI200 현재 구성종목 기반 universe 구축
4. Value, Quality, Growth, Momentum, Low Volatility 팩터 산출
5. Rank IC와 분위 포트폴리오 검증
6. 월간 Top 30 동일가중 백테스트
7. ML 기반 다음 1개월 초과수익률 예측
8. 시간순 8:1:1 split 검증
9. 10개 실무형 전략 비교
10. Institutional Core-Satellite 전략 설계
11. 공분산, PCA, bootstrap, fat-tail, 상관구조 분석 등 사전과제형 분석
12. 고객용 리포트, 면접용 설명서, 논문 초안 작성

## 2. 데이터 설계

### 2.1 가격 데이터

가격 데이터는 KIS API 국내주식 일봉 endpoint를 사용해 수집했다. 표준 저장 위치는 다음과 같다.

```text
data/raw/price/prices_2007_2026.csv
```

표준 컬럼은 다음과 같다.

```text
date, ticker, name, open, high, low, close, adj_close, volume,
trading_value, market_cap, sector, is_suspended, is_administrative
```

핵심 사용 컬럼은 `date`, `ticker`, `adj_close`, `volume`, `trading_value`다. 수익률 계산에는 `adj_close`를 사용한다. 수정주가를 쓰는 이유는 액면분할, 배당락, 권리락 등으로 인해 단순 종가를 쓰면 과거 수익률이 왜곡될 수 있기 때문이다.

### 2.2 가격 데이터 커버리지

최종 장기 가격 데이터는 다음 범위를 가진다.

- 전체 행 수: 780,050
- 종목 수: 최대 200개
- 기간: 2007-01-02 ~ 2026-06-30
- 중복 ticker-date: 0

연도별 커버리지는 다음과 같다.

| 연도 | 행 수 | 종목 수 | 시작일 | 종료일 |
| --- | ---: | ---: | --- | --- |
| 2007 | 29,642 | 124 | 2007-01-02 | 2007-12-28 |
| 2008 | 31,025 | 127 | 2008-01-02 | 2008-12-30 |
| 2009 | 32,500 | 132 | 2009-01-02 | 2009-12-30 |
| 2010 | 34,133 | 138 | 2010-01-04 | 2010-12-30 |
| 2011 | 35,454 | 146 | 2011-01-03 | 2011-12-29 |
| 2012 | 36,317 | 148 | 2012-01-02 | 2012-12-28 |
| 2013 | 36,796 | 152 | 2013-01-02 | 2013-12-30 |
| 2014 | 37,543 | 157 | 2014-01-02 | 2014-12-30 |
| 2015 | 39,038 | 159 | 2015-01-02 | 2015-12-30 |
| 2016 | 39,180 | 161 | 2016-01-04 | 2016-12-29 |
| 2017 | 40,077 | 169 | 2017-01-02 | 2017-12-28 |
| 2018 | 41,917 | 174 | 2018-01-02 | 2018-12-28 |
| 2019 | 43,245 | 177 | 2019-01-02 | 2019-12-30 |
| 2020 | 44,074 | 179 | 2020-01-02 | 2020-12-30 |
| 2021 | 45,584 | 189 | 2021-01-04 | 2021-12-30 |
| 2022 | 46,722 | 190 | 2022-01-03 | 2022-12-29 |
| 2023 | 46,927 | 194 | 2023-01-02 | 2023-12-28 |
| 2024 | 47,804 | 197 | 2024-01-02 | 2024-12-30 |
| 2025 | 48,072 | 200 | 2025-01-02 | 2025-12-30 |
| 2026 | 24,000 | 200 | 2026-01-02 | 2026-06-30 |

초기 연도에 종목 수가 200개보다 적은 이유는 현재 KOSPI200 구성종목을 기준으로 과거 가격을 조회했기 때문이다. 일부 종목은 당시 상장 전이거나 가격 이력이 존재하지 않는다.

### 2.3 재무 데이터

재무 데이터는 TS2000 원천 엑셀을 장기 패널로 표준화했다. 저장 위치는 다음과 같다.

```text
data/raw/ts2000/fundamentals_long.csv
```

커버리지는 다음과 같다.

- 행 수: 15,756
- 종목 수: 990
- 회계기간: 2007-01 ~ 2026-03
- 원천 wide 컬럼 수: 496개
- 컬럼 사전: `outputs/tables/ts2000_wide_column_dictionary.csv`

재무 데이터에서 중요한 기준은 `available_date`다. 투자자는 결산월 말에 바로 재무 정보를 알 수 없으므로, 팩터는 회계기간이 아니라 정보가 사용 가능해진 날짜를 기준으로 정렬해야 한다. 이 프로젝트는 `available_date` 기준으로 train/validation/test를 나누고, 가격 신호일과 결합할 때도 해당 날짜 이전에 사용 가능했던 최신 재무정보만 붙인다.

### 2.4 재무 데이터 split

장기 재무 데이터는 `available_date` 기준으로 다음과 같이 나뉜다.

| Split | 행 수 | 종목 수 | available_date 범위 | fiscal_period 범위 |
| --- | ---: | ---: | --- | --- |
| Train | 7,550 | 919 | 2007-04-30 ~ 2016-12-31 | 2007-01 ~ 2016-09 |
| Validation | 4,099 | 847 | 2017-02-28 ~ 2021-12-31 | 2016-11 ~ 2021-09 |
| Test | 4,107 | 842 | 2022-02-28 ~ 2026-06-30 | 2021-11 ~ 2026-03 |

이 split은 “시장 국면별 robustness split”에 가깝다. 2007~2016은 금융위기 이후 회복기와 장기 저금리 구간을 포함하고, 2017~2021은 성장주 강세와 코로나 구간을 포함하며, 2022~2026은 금리상승과 반도체/AI 주도 장세를 포함한다.

## 3. Universe 설계와 생존편향

### 3.1 Universe 설정

유니버스는 KOSPI200 현재 구성종목을 기반으로 시작했다.

```text
data/raw/benchmark/kospi200_constituents.csv
```

설정 파일 `config/universe.yaml`의 핵심 내용은 다음과 같다.

- universe: KOSPI200
- preferred mode: point-in-time constituents
- MVP fallback: current constituents
- 우선주, SPAC, 관리종목, 거래정지 종목은 제외하는 것이 원칙

### 3.2 이 설정의 의미

현재 구성종목을 과거로 가져가면 생존편향이 발생한다. 예를 들어 2026년에 KOSPI200에 남아 있는 기업은 과거에도 상대적으로 생존력이 강했을 가능성이 있다. 따라서 현재 universe만으로 2007년부터 백테스트하면 과거에 탈락한 기업, 상장폐지 기업, 장기 부진 기업이 빠질 수 있다.

이 프로젝트에서는 이 한계를 숨기지 않고 모든 리포트에 명시했다. 포트폴리오 프로젝트 단계에서는 현재 구성종목 fallback을 허용하지만, 실무 운용 또는 논문 투고 수준으로 발전시키려면 point-in-time KOSPI200 편입/제외 이력이 필요하다.

## 4. 팩터 설계

### 4.1 공통 전처리

팩터 산출의 핵심 전처리는 `src/factors/common.py`의 `cross_sectional_score`다. 각 날짜별 단면에서 다음 절차를 수행한다.

1. 숫자형 변환
2. 관측치가 3개 미만이면 결측 처리
3. 1%와 99% 분위수 기준 winsorization
4. 결측값은 해당 단면 중앙값으로 대체
5. z-score 표준화
6. 낮을수록 좋은 지표는 부호를 반전

이 설정의 의미는 다음과 같다.

- winsorization은 극단값이 평균과 표준편차를 왜곡하는 문제를 줄인다.
- 중앙값 대체는 결측이 일부 있는 종목도 완전히 버리지 않기 위한 실무적 처리다.
- z-score는 서로 단위가 다른 지표를 같은 척도로 결합하기 위한 처리다.
- 방향 정렬은 모든 팩터 점수가 높을수록 좋은 신호가 되도록 만든다.

### 4.2 Value

Value 팩터는 저평가 신호다. 사용 가능한 지표는 다음이다.

- PER: 낮을수록 좋음
- PBR: 낮을수록 좋음
- PSR: 낮을수록 좋음
- EV/EBITDA: 낮을수록 좋음

각 지표를 단면 z-score로 변환하고, 사용 가능한 값의 평균을 `value_score`로 만든다.

Value 팩터의 경제적 직관은 “싸게 거래되는 기업은 향후 평균회귀 또는 위험 프리미엄을 통해 초과수익을 낼 수 있다”는 것이다. 다만 value trap이 존재할 수 있으므로 단독 팩터로 쓰기보다 quality, momentum과 함께 쓰는 것이 더 안전하다.

### 4.3 Quality

Quality 팩터는 기업의 수익성, 안정성, 재무 건전성을 반영한다.

- ROE: 높을수록 좋음
- ROA: 높을수록 좋음
- 영업이익률: 높을수록 좋음
- 부채비율: 낮을수록 좋음
- 영업현금흐름/순이익: 높을수록 좋음

Quality는 value trap을 줄이는 보완 신호다. 단순히 싼 기업이 아니라, 싼데도 이익의 질과 재무 안정성이 좋은 기업을 선호하게 만든다.

### 4.4 Growth

Growth 팩터는 성장성과 자산 팽창의 질을 함께 본다.

- 매출 성장률: 높을수록 좋음
- 자산 성장률: 낮을수록 좋음

자산 성장률을 낮을수록 좋게 둔 이유는 과도한 자산 팽창이 미래 수익률을 낮출 수 있다는 asset growth anomaly를 반영하기 위해서다.

### 4.5 Momentum

Momentum 팩터는 가격 추세 신호다.

- 최근 6개월 수익률
- 최근 12개월 수익률에서 최근 1개월 제외

12개월 momentum에서 최근 1개월을 제외하는 이유는 단기 반전 효과를 피하기 위해서다. 최근 1개월 급등락은 단기 과열 또는 반전 가능성을 포함하므로, 전통적인 momentum 연구에서는 12개월-1개월 수익률을 많이 사용한다.

### 4.6 Low Volatility

Low Volatility 팩터는 방어적 성격의 가격 신호다.

- 최근 1년 연율화 변동성: 낮을수록 좋음
- 최근 1년 maximum drawdown: 낮을수록 좋음

이 팩터는 이론적으로 저위험 anomaly와 연결된다. 다만 실제 결과에서는 Low Vol 단독 전략의 성과가 좋지 않았다. 이는 한국 대형주 데이터에서 단순 저변동성만으로는 충분한 알파가 되기 어렵거나, 현재 universe와 벤치마크 설정의 영향을 받았을 수 있음을 의미한다.

### 4.7 Composite Score

기본 통합 팩터는 다음 고정 가중치로 계산했다.

```text
Composite Score
= 0.25 * Quality
+ 0.25 * Value
+ 0.20 * Momentum
+ 0.20 * Low Volatility
+ 0.10 * Growth
```

실제 코드에서는 결측 팩터가 있는 경우 사용 가능한 팩터의 가중치만 재정규화한다. 즉 어떤 종목의 growth score가 결측이라면, 나머지 팩터들만으로 composite score를 만든다.

이 설정은 “한 팩터에 과도하게 의존하지 않는 균형형 멀티팩터”를 만들기 위한 기본안이다.

## 5. 팩터 검증 설계

### 5.1 Forward Return

팩터 검증은 월말 신호일 이후의 forward return을 붙여서 수행했다. 기본 타깃은 다음 1개월 초과수익률이다.

```text
excess_forward_1m_return
= 해당 종목 다음 1개월 수익률 - 동일 universe 평균 다음 1개월 수익률
```

시장 전체가 상승했기 때문에 오른 종목과, 같은 시장 안에서 상대적으로 더 오른 종목을 구분하기 위해 초과수익률을 사용한다.

### 5.2 Rank IC

Rank IC는 월별로 팩터 점수 순위와 다음 1개월 초과수익률 순위의 상관을 계산한 것이다.

Rank IC가 양수이면 점수가 높은 종목이 이후 상대적으로 좋은 수익률을 낸 경향이 있다는 뜻이다. 절대 크기가 매우 크지 않더라도 수백 개 종목, 수백 개 월에서 안정적으로 양수라면 포트폴리오 신호로 의미가 있다.

### 5.3 Rank IC 결과

| 팩터 | 월 수 | 평균 Rank IC | 중앙값 Rank IC | 양수 비율 |
| --- | ---: | ---: | ---: | ---: |
| Composite | 227 | 0.0233 | 0.0227 | 56.83% |
| Quality | 219 | 0.0170 | 0.0144 | 55.71% |
| Value | 219 | 0.0084 | 0.0065 | 52.51% |
| Low Volatility | 227 | 0.0031 | -0.0067 | 49.78% |
| Momentum | 227 | 0.0027 | 0.0244 | 53.74% |

해석은 다음과 같다.

- Composite가 가장 안정적인 양의 Rank IC를 보였다.
- Quality도 상대적으로 안정적인 신호였다.
- Value는 양수지만 약했다.
- Momentum은 평균 IC는 작지만 중앙값은 양수이며, 포트폴리오 백테스트에서는 강한 성과를 보였다.
- Low Volatility는 단독 예측력은 약했다.

### 5.4 분위 포트폴리오 결과

Composite score를 5분위로 나누어 다음 1개월 초과수익률을 비교했다.

| 분위 | 월평균 초과수익률 | 월중앙 초과수익률 |
| --- | ---: | ---: |
| Q1 | -0.411% | -1.421% |
| Q2 | 0.009% | -0.944% |
| Q3 | -0.236% | -1.291% |
| Q4 | 0.010% | -0.566% |
| Q5 | 0.624% | -0.767% |
| Q5-Q1 | 1.035% | 1.012% |

가장 중요한 값은 Q5-Q1이다. 상위 분위와 하위 분위의 월평균 초과수익 차이가 약 1.04%로 나타났다. 이는 단일 월별 예측력은 약하지만 포트폴리오 수준에서는 의미 있는 spread가 존재한다는 뜻이다.

## 6. 백테스트 설계

### 6.1 기본 백테스트 가정

백테스트 엔진은 `src/backtest/engine.py`에 구현되어 있다. 기본 구조는 다음과 같다.

- 월말 signal date 기준으로 점수 산출
- 점수 상위 30개 종목 선택
- 동일가중 보유
- 다음 월말 신호일까지 일별 수익률 추적
- 리밸런싱 시 turnover 기반 거래비용 차감
- 기본 거래비용 10bp
- 벤치마크는 동일 universe 일별 동일가중 수익률

### 6.2 왜 Top 30인가

Top 30은 집중도와 분산의 균형을 위한 설정이다.

- Top 10은 너무 집중되어 종목별 이벤트 리스크가 커질 수 있다.
- Top 50 이상은 팩터 신호가 희석될 수 있다.
- Top 30은 실무 model portfolio에서 설명 가능한 수준의 종목 수이며, 동시에 팩터 신호를 어느 정도 유지할 수 있다.

### 6.3 왜 월간 리밸런싱인가

월간 리밸런싱은 재무/가격 팩터 전략에서 가장 일반적인 주기다.

- 일간 리밸런싱은 거래비용과 turnover가 과도하다.
- 분기 리밸런싱은 가격 팩터 변화 반영이 느릴 수 있다.
- 월간 리밸런싱은 실무 운용 가능성과 신호 반응성의 중간 지점이다.

### 6.4 벤치마크 설정

현재 기본 벤치마크는 공식 KOSPI200 지수가 아니라 “보유 가능 universe의 동일가중 수익률”이다.

이 설정의 장점은 전략과 같은 종목 집합에서 초과성과를 평가한다는 점이다. 단점은 실제 고객이 보는 KOSPI200 시가총액가중 지수와 다르다는 점이다. 따라서 실무 적용 전에는 공식 KOSPI200 또는 KODEX200 장기 데이터와 반드시 비교해야 한다.

## 7. 핵심 전략 성과

### 7.1 Balanced Multi-Factor

전체 2007~2026 결과:

- 누적수익률: 2,431.73%
- CAGR: 19.09%
- 연율 변동성: 21.37%
- Sharpe: 0.89
- MDD: -48.20%
- 벤치마크 누적수익률: 694.02%
- Active total return: 218.85%
- Information Ratio: 0.66
- 평균 turnover: 21.41%
- 리밸런싱 횟수: 227

해석:

Balanced Multi-Factor는 수익률과 설명 가능성의 균형이 가장 좋다. ML 전략보다 CAGR은 낮지만, 단일 모멘텀보다 경제적 설명이 쉽고 여러 팩터로 분산되어 있다.

### 7.2 ML Predicted Return

전체 2007~2026 결과:

- 누적수익률: 3,712.17%
- CAGR: 21.76%
- 연율 변동성: 24.99%
- Sharpe: 0.87
- MDD: -52.86%
- Active total return: 380.11%
- Information Ratio: 0.91
- 평균 turnover: 25.45%

해석:

ML 전략은 누적수익률과 IR이 가장 높았다. 그러나 변동성과 MDD도 가장 크다. 따라서 고객 자금 운용에서는 단독 주력 전략보다 위성 전략으로 제한하는 것이 적절하다.

### 7.3 Institutional Core-Satellite

전체 2007~2026 결과:

- 누적수익률: 2,183.84%
- CAGR: 18.43%
- 연율 변동성: 19.50%
- Sharpe: 0.95
- MDD: -41.46%
- Active total return: 187.63%
- Information Ratio: 0.45
- 평균 turnover: 24.94%

Test 2022~2026 결과:

- 누적수익률: 271.95%
- CAGR: 35.22%
- 연율 변동성: 25.03%
- Sharpe: 1.41
- MDD: -19.03%
- Information Ratio: 1.07

해석:

Institutional Core-Satellite 전략은 수익률 극대화가 아니라 “위험 조정 성과와 낙폭 관리”를 목표로 설계되었다. ML 단독보다 누적수익률은 낮지만 전체 MDD가 -52.86%에서 -41.46%로 줄었고, Test 구간 MDD는 -19.03%로 크게 개선되었다.

## 8. ML 연구 설계

### 8.1 예측 문제 정의

ML 모델의 예측 타깃은 다음 1개월 초과수익률이다.

```text
target = next_1m_stock_return - next_1m_universe_equal_weight_return
```

이 타깃은 시장 방향 예측이 아니라 횡단면 종목 선택 능력을 보기 위한 것이다.

### 8.2 입력 변수

사용한 feature는 다음이다.

- value_score
- quality_score
- growth_score
- momentum_score
- low_volatility_score
- composite_score
- return_6m
- return_12m_ex_1m
- volatility_1y
- max_drawdown_1y

### 8.3 모델

두 모델을 비교했다.

1. Composite Baseline
   - 기존 composite score를 train 구간에서 초과수익률 단위로 scaling한 모델
   - 설명력이 높고 단순하다.

2. Ridge Linear
   - 여러 팩터와 가격 변수를 사용한 정규화 선형회귀
   - 과적합을 줄이기 위해 L2 penalty를 사용한다.

### 8.4 시간순 8:1:1 split

사용자 지적에 따라 ML 검증은 시간순 8:1:1 split을 추가했다.

| Split | 행 수 | 종목 수 | 월 수 | 기간 |
| --- | ---: | ---: | ---: | --- |
| Train | 28,155 | 190 | 181 | 2007-07-31 ~ 2022-07-29 |
| Validation | 4,422 | 196 | 23 | 2022-08-31 ~ 2024-06-28 |
| Test | 4,567 | 200 | 23 | 2024-07-31 ~ 2026-05-29 |

금융 시계열에서는 랜덤 split을 쓰지 않는다. 랜덤 split은 미래 정보가 train에 섞일 수 있고, 시계열 구조를 깨뜨린다. 따라서 시간순 split이 기본이다.

### 8.5 8:1:1 모델 성과

| 모델 | Split | 평균 Rank IC | 방향성 적중률 | IC 양수 비율 |
| --- | --- | ---: | ---: | ---: |
| Composite Baseline | Train | 0.0217 | 50.30% | 57.46% |
| Composite Baseline | Validation | 0.0110 | 48.33% | 47.83% |
| Composite Baseline | Test | 0.0486 | 50.78% | 60.87% |
| Ridge Linear | Train | 0.0305 | 51.51% | 60.77% |
| Ridge Linear | Validation | 0.0070 | 51.38% | 39.13% |
| Ridge Linear | Test | 0.0392 | 54.74% | 69.57% |

Validation 기준으로 선택된 모델은 Composite Baseline이다. Ridge는 Test에서 일부 지표가 좋지만, 사전에 정한 validation 기준에서는 baseline보다 낮았다. 따라서 사후적으로 Test 결과를 보고 Ridge를 선택하면 data snooping이 된다.

이 결과의 핵심 메시지는 다음이다.

> 복잡한 모델이 항상 더 좋은 실전 모델은 아니다. 금융 데이터에서는 단순하고 설명 가능한 baseline이 강력한 기준선이 될 수 있다.

## 9. Strategy Lab

### 9.1 목적

실무에서는 하나의 전략만 테스트하지 않는다. 여러 투자 아이디어를 같은 데이터, 같은 리밸런싱 조건, 같은 거래비용 조건으로 비교해야 한다. 이를 위해 Strategy Lab을 만들었다.

### 9.2 테스트한 10개 전략

1. Deep Value
2. Quality Compounder
3. Earnings Growth
4. Price Momentum
5. Low Volatility
6. Balanced Multi-Factor
7. Value + Momentum Barbell
8. Quality + Low Vol Defensive
9. Momentum + Growth Aggressive
10. ML Predicted Return

### 9.3 전체 기간 성과 순위

| 전략 | CAGR | Sharpe | MDD | IR |
| --- | ---: | ---: | ---: | ---: |
| ML Predicted Return | 21.76% | 0.87 | -52.86% | 0.91 |
| Price Momentum | 20.45% | 0.84 | -51.91% | 0.61 |
| Value + Momentum Barbell | 19.83% | 0.85 | -50.09% | 0.63 |
| Momentum + Growth Aggressive | 19.16% | 0.80 | -51.39% | 0.55 |
| Balanced Multi-Factor | 19.09% | 0.89 | -48.20% | 0.66 |
| Earnings Growth | 15.68% | 0.71 | -51.66% | 0.52 |
| Deep Value | 15.71% | 0.69 | -64.60% | 0.46 |
| Quality Compounder | 14.26% | 0.69 | -50.41% | 0.29 |
| Quality + Low Vol Defensive | 11.23% | 0.54 | -48.22% | -0.06 |
| Low Volatility | 8.99% | 0.41 | -53.81% | -0.25 |

해석:

- 가장 높은 CAGR은 ML과 Momentum 계열에서 나왔다.
- 그러나 이 전략들은 MDD가 크다.
- Balanced Multi-Factor는 수익률, Sharpe, 설명 가능성의 균형이 좋다.
- Low Volatility 단독 전략은 기대와 달리 성과가 약했다.

## 10. Institutional Core-Satellite 전략

### 10.1 전략 목적

Institutional Core-Satellite 전략은 실제 S&T 또는 운용부서에서 검토 가능한 구조를 목표로 설계했다. 단순히 수익률이 높은 전략을 고르는 것이 아니라, 설명 가능한 core와 공격적 satellite를 나누고, 시장 국면에 따라 위험 노출을 줄인다.

### 10.2 하위 신호

| 신호 | 구성 |
| --- | --- |
| Balanced | Quality 25%, Value 25%, Momentum 20%, Low Volatility 20%, Growth 10% |
| Value Momentum | Value 35%, Momentum 35%, Quality 15%, Low Volatility 15% |
| Defensive | Quality 45%, Low Volatility 45%, Value 10% |
| Aggressive | Momentum 60%, Growth 25%, Quality 15% |
| ML | Ridge 또는 baseline 모델의 다음 1개월 초과수익률 예측 |

### 10.3 국면별 가중치

| 국면 | 최종 점수 가중치 | 목표 주식 노출 |
| --- | --- | ---: |
| Bull | Balanced 25%, Value Momentum 25%, Aggressive 20%, ML 30% | 100% |
| Neutral | Balanced 40%, Value Momentum 20%, Defensive 20%, ML 20% | 80% |
| Bear | Balanced 30%, Defensive 45%, Value Momentum 10%, ML 15% | 50% |
| Stress | Defensive 65%, Balanced 25%, Value Momentum 5%, ML 5% | 25% |

### 10.4 국면 판정

국면은 내부 동일가중 universe index를 기반으로 판정한다.

- 200일 이동평균
- 60일 수익률
- 60일 변동성
- 120일 낙폭

해석:

- Bull: 추세가 좋고 수익률이 양호한 구간
- Neutral: 방향성이 뚜렷하지 않은 구간
- Bear: 지수가 장기 추세 아래 있고 60일 수익률이 부진한 구간
- Stress: 낙폭이 크거나 급락과 고변동성이 동시에 나타나는 구간

### 10.5 결과 해석

Institutional 전략은 ML 단독보다 수익률은 낮지만 MDD와 변동성을 줄였다. 고객 자금 운용에서 중요한 것은 최고 CAGR 하나가 아니라, 손실 구간을 설명하고 견딜 수 있는 전략 구조다. 이 전략은 그 방향으로 설계되었다.

## 11. 사전과제 대응 분석 팩

사용자가 제공한 증권사 퀀트리서치 사전과제 문항을 검토한 결과, 후반부는 가격 데이터, 공분산, PCA, 포트폴리오, 통계검정, 리스크 분석 능력을 요구한다. 이를 현재 데이터로 구현한 분석 팩을 만들었다.

### 11.1 구현한 과제형 분석

| 문항 | 구현 내용 | 산출물 |
| --- | --- | --- |
| Q50 | 30일 공분산 기반 Minimum Variance Portfolio | `q50_min_variance_latest_weights.csv` |
| Q52 | 월간 수익률 PCA | `q52_pca_summary.csv` |
| Q54 | Low Volatility bootstrap 검정 | `q54_low_vol_bootstrap.csv` |
| Q56 | Momentum 최근 1개월 포함/제외 비교 | `q56_momentum_skip_month_comparison.csv` |
| Q57 | 거래비용 0/10/30bp 민감도 | `q57_transaction_cost_sensitivity.csv` |
| Q58 | Equal/Inverse Vol/Score weighting 비교 | `q58_weighting_comparison.csv` |
| Q59 | Fat-tail 진단 | `q59_fat_tail_summary.csv` |
| Q60 | 위기 국면 상관구조 변화 | `q60_correlation_breakdown.csv` |
| Q76 | Look-ahead bias 통제 | integrated factor pipeline |
| Q99 | End-to-end pipeline | `main.py` 전체 step |

### 11.2 중요한 결과

PCA 결과:

- 전체 기간 PC1 설명력: 20.54%
- 2022 금리상승기 PC1 설명력: 43.91%
- 최근 2024~2026 PC1 설명력: 27.10%

이는 위기 또는 매크로 주도 장세에서 개별 종목보다 시장 공통요인의 영향이 커질 수 있음을 보여준다.

상관구조 결과:

- 2019년 평균 pairwise correlation: 0.168
- 2020년 3월 코로나 급락기: 0.667
- 2022년 금리상승기: 0.274
- 2026년 상반기: 0.389

코로나 급락기에 평균 상관이 0.17에서 0.67까지 상승했다. 이는 위기 때 분산효과가 붕괴된다는 것을 매우 선명하게 보여준다.

거래비용 민감도:

| 거래비용 | CAGR | Sharpe | MDD | IR |
| ---: | ---: | ---: | ---: | ---: |
| 0bp | 19.40% | 0.91 | -47.89% | 0.69 |
| 10bp | 19.09% | 0.89 | -48.20% | 0.66 |
| 30bp | 18.47% | 0.86 | -48.81% | 0.61 |

거래비용을 높이면 성과가 점진적으로 낮아진다. 이 분석은 실무적으로 매우 중요하다. 거래비용을 무시한 백테스트는 실제 운용 가능성을 과대평가할 수 있기 때문이다.

가중 방식 비교:

| 방식 | CAGR | 변동성 | Sharpe | MDD | IR |
| --- | ---: | ---: | ---: | ---: | ---: |
| Equal Weight | 19.40% | 21.37% | 0.91 | -47.89% | 0.69 |
| Inverse Volatility | 17.93% | 19.79% | 0.91 | -46.31% | 0.56 |
| Score Weight | 21.75% | 22.63% | 0.96 | -47.39% | 0.77 |

Score weighting은 성과를 높였지만 변동성도 증가했다. Inverse volatility는 변동성과 MDD를 낮췄지만 CAGR과 IR이 낮아졌다. 이는 수익률 극대화와 위험 완화 사이의 trade-off를 보여준다.

Fat-tail 결과:

- 일간 평균 수익률: 0.0605%
- 일간 변동성: 1.2815%
- 연율 변동성: 20.34%
- 왜도: -0.633
- 첨도: 14.43
- 초과첨도: 11.43

정규분포보다 꼬리가 훨씬 두껍다. 이는 VaR, 손실 시나리오, stress test가 단순 정규가정에 의존하면 위험을 과소평가할 수 있음을 의미한다.

## 12. 고객용 리포트와 논문 초안

프로젝트는 단순 코드 산출물에 그치지 않고 리서치 커뮤니케이션 산출물까지 포함한다.

생성된 주요 문서는 다음과 같다.

- 고객용 리포트: `outputs/reports/KOSPI200_AI_Quant_Strategy_Client_Report.pdf`
- 프로젝트 면접 설명서: `outputs/reports/KOSPI200_Quant_Project_Interview_Manual.pdf`
- 논문 초안: `outputs/reports/KOSPI200_Quant_Strategy_Research_Paper_Draft.md`
- Institutional 전략 설명서: `outputs/reports/Institutional_Core_Satellite_Strategy.md`
- 사전과제 대응 분석 팩: `outputs/reports/Quant_Research_Recruiting_Assignment_Pack.md`
- 지원 포지셔닝 문서: `docs/Quant_Research_Portfolio_Positioning.md`

이 산출물들은 각각 역할이 다르다.

- 고객용 리포트는 전략 결과를 외부 배포 자료처럼 설명한다.
- 면접 설명서는 프로젝트 구조와 절차를 면접에서 설명하기 쉽게 정리한다.
- 논문 초안은 연구 질문, 선행연구, 방법론, 결과, 한계, 향후 연구로 구성된다.
- 사전과제 대응 팩은 실제 채용 과제형 문제를 프로젝트로 확장했다는 증거다.

## 13. 전체 코드 구조

### 13.1 Data

`src/data/`는 가격, 재무, 벤치마크, universe를 다룬다.

- `kis_client.py`: KIS API 인증과 요청
- `price_loader.py`: 가격 데이터 수집, 장기 가격 수집, CSV 로딩
- `ts2000_loader.py`: 단일 TS2000 엑셀 표준화
- `ts2000_wide_loader.py`: 2007~2026 장기 wide TS2000 표준화
- `universe.py`: KOSPI200 구성종목 수집
- `validator.py`: 가격/재무 데이터 검증
- `benchmark_loader.py`: 벤치마크 데이터 로딩

### 13.2 Factors

`src/factors/`는 팩터 산출을 담당한다.

- `common.py`: winsorization, median fill, z-score
- `value.py`: Value factor
- `quality.py`: Quality factor
- `growth.py`: Growth factor
- `momentum.py`: Momentum factor
- `low_volatility.py`: Low Volatility factor
- `composite.py`: composite score
- `integrated.py`: 재무와 가격 팩터 결합
- `pipeline.py`: 팩터 생성 pipeline

### 13.3 Research

`src/research/`는 검증과 사전과제형 분석을 담당한다.

- `forward_returns.py`: forward return target 생성
- `ic_analysis.py`: Rank IC
- `quintile_analysis.py`: 분위 포트폴리오
- `factor_report.py`: 팩터 검증 종합
- `dataset_split.py`: train/validation/test split
- `recommendation.py`: 최신 후보군 생성
- `recruiting_assignment_pack.py`: 채용 과제형 분석 팩

### 13.4 ML

`src/ml/return_model.py`는 다음 1개월 초과수익률 예측 실험을 담당한다.

- Composite Baseline
- Ridge Linear
- 시간순 8:1:1 split
- 기존 시장국면 split
- 예측 결과를 포트폴리오 점수로 변환

### 13.5 Strategy

`src/strategy/`는 실무형 전략 확장을 담당한다.

- `strategy_lab.py`: 10개 전략 비교
- `regime.py`: 시장국면 기반 팩터 가중치
- `institutional_strategy.py`: Core-Satellite + Regime Overlay

### 13.6 Backtest

`src/backtest/`는 백테스트와 성과평가를 담당한다.

- `engine.py`: 월간 Top N 포트폴리오 백테스트
- `performance.py`: CAGR, Sharpe, MDD, IR 등 계산
- `risk.py`: drawdown 계산

### 13.7 Report

`src/report/`는 리포트 생성 모듈이다.

- `report_generator.py`: 초기 PDF/Markdown 리포트
- `client_strategy_report.py`: 고객 배포용 전략 리포트
- `interview_manual.py`: 면접 설명서
- `research_paper.py`: 논문 초안
- `charts.py`, `tables.py`: 차트/표 보조

## 14. 주요 산출물 위치

### 14.1 데이터

- `data/raw/price/prices_2007_2026.csv`
- `data/raw/ts2000/fundamentals_long.csv`
- `data/raw/benchmark/kospi200_constituents.csv`
- `data/features/integrated_factor_scores_2007_2026.csv`
- `data/features/ml_predicted_factor_scores_2007_2026.csv`
- `data/features/institutional_core_satellite_scores.csv`

### 14.2 결과 테이블

- `outputs/tables/rank_ic_summary.csv`
- `outputs/tables/quintile_return_summary.csv`
- `outputs/tables/ml_model_metrics.csv`
- `outputs/tables/ml_model_metrics_801010.csv`
- `outputs/tables/strategy_lab_summary.csv`
- `outputs/tables/institutional_strategy_split_summary.csv`
- `outputs/tables/recruiting_assignment_pack/`

### 14.3 백테스트

- `outputs/backtest_integrated_2007_2026/`
- `outputs/backtest_ml_predicted_2007_2026/`
- `outputs/backtest_ml_predicted_801010/`
- `outputs/backtest_institutional_core_satellite/`
- `outputs/strategy_lab/backtests/`

### 14.4 리포트

- `outputs/reports/KOSPI200_AI_Quant_Strategy_Client_Report.pdf`
- `outputs/reports/KOSPI200_Quant_Strategy_Research_Paper_Draft.md`
- `outputs/reports/Institutional_Core_Satellite_Strategy.md`
- `outputs/reports/Quant_Research_Recruiting_Assignment_Pack.md`
- `outputs/reports/KOSPI200_Quant_Project_Interview_Manual.pdf`

## 15. 핵심 결론

### 15.1 팩터 관점

Composite factor는 평균 Rank IC 0.0233, 양수 비율 56.83%, Q5-Q1 월평균 초과수익 1.04%를 보였다. 단일 팩터 예측력은 약하지만, 여러 팩터를 결합하면 포트폴리오 수준에서 의미 있는 spread가 나타났다.

### 15.2 전략 관점

ML과 Momentum 계열은 수익률이 높지만 MDD가 크다. Balanced Multi-Factor는 수익률과 설명 가능성의 균형이 좋다. Institutional Core-Satellite 전략은 수익률을 일부 포기하는 대신 변동성과 낙폭을 줄였다.

### 15.3 ML 관점

8:1:1 split에서는 Composite Baseline이 선택되었다. 이는 복잡한 ML 모델이 항상 실전적으로 우월하지 않음을 보여준다. 특히 금융 데이터에서는 사후적으로 Test 성과가 좋은 모델을 고르면 과최적화가 된다.

### 15.4 실무 관점

거래비용, turnover, 상관구조 붕괴, fat-tail, 생존편향, look-ahead bias를 함께 고려해야 한다. 단순히 높은 CAGR을 보여주는 전략보다, 왜 그런 결과가 나왔고 어떤 상황에서 실패할 수 있는지를 설명하는 전략이 실무적으로 더 가치 있다.

## 16. 한계

이 프로젝트의 한계는 명확하다.

1. 현재 KOSPI200 구성종목 기반이므로 survivorship bias가 있다.
2. 공식 KOSPI200 시가총액가중 지수가 아니라 universe equal-weight benchmark를 기본으로 썼다.
3. 거래비용은 10bp 단순 가정이며 시장충격 비용은 반영하지 않았다.
4. 리밸런싱 체결 지연, 가격제한폭, 거래정지, 유동성 제약이 충분히 반영되지 않았다.
5. 재무 데이터의 실제 공시일과 벤더 반영일 차이를 완전히 반영하지 못했다.
6. ML 모델은 walk-forward 재학습이 아직 완전한 production 형태는 아니다.
7. 업종 중립화와 시가총액 중립화가 기본 백테스트에 완전히 반영되지 않았다.

## 17. 향후 발전 방향

### 17.1 데이터

- Point-in-time KOSPI200 구성종목 이력 확보
- 공식 KOSPI200 지수 장기 데이터 연결
- KODEX200 ETF를 보조 벤치마크로 장기 정합성 검증
- DART API 공시 이벤트 데이터 추가
- 거래대금과 시가총액 기반 유동성 필터 강화

### 17.2 모델

- Walk-forward 재학습
- 업종 중립 및 시가총액 중립 팩터
- Fama-MacBeth 회귀
- Newey-West 표준오차
- Benjamini-Hochberg multiple testing 보정
- Bootstrap/permutation test 확장

### 17.3 전략

- 종목 5%, 업종 25% cap을 백테스트 엔진에 직접 반영
- ADV 대비 주문비율 제약
- 거래비용 5/10/20/50bp 민감도
- 변동성 타깃팅
- drawdown control
- regime overlay 고도화

### 17.4 리포트

- Jupyter Notebook 제출용 패키지 생성
- 고객용 PDF 리포트 업데이트
- 논문 초안의 방법론/결과/한계 보강
- 면접 발표용 슬라이드 작성

## 18. 지원서와 면접에서의 설명 방식

이 프로젝트는 다음 문장으로 요약할 수 있다.

> KIS API 기반 KOSPI200 장기 가격 데이터와 TS2000 재무 데이터를 결합해 Value, Quality, Growth, Momentum, Low Volatility 팩터를 설계했고, Rank IC, 분위 포트폴리오, 월간 리밸런싱 백테스트, 시간순 8:1:1 ML 검증, 국면대응 Core-Satellite 전략, 사전과제형 통계분석까지 end-to-end로 구현했습니다.

면접에서는 다음 흐름으로 설명하는 것이 좋다.

1. 연구 질문: 한국 대형주에서 팩터가 미래 수익률을 설명하는가?
2. 데이터: KIS 가격 2007~2026, TS2000 재무 2007~2026
3. 편향 통제: available_date, 시간순 split, survivorship bias 명시
4. 팩터: Value, Quality, Growth, Momentum, Low Volatility
5. 검증: Rank IC, Q5-Q1, backtest
6. 결과: Composite와 Momentum 계열 우수, Low Vol 단독 약함
7. ML: 8:1:1에서 baseline 선택, 복잡도보다 검증 절차 중요
8. 실무화: Institutional Core-Satellite로 낙폭 관리
9. 사전과제 대응: PCA, 공분산, bootstrap, 거래비용, fat-tail까지 확장
10. 한계: point-in-time universe와 공식 benchmark 필요

## 19. 최종 요약

이 프로젝트는 단순한 백테스트가 아니다. 데이터 수집, 정제, 팩터 설계, 통계 검증, ML 검증, 포트폴리오 구성, 리스크 분석, 고객용 리포트, 논문 초안, 사전과제 대응까지 연결한 통합 퀀트 리서치 프로젝트다.

가장 중요한 결론은 다음이다.

1. 설명 가능한 멀티팩터 baseline은 한국 대형주 장기 데이터에서 강력한 기준선이다.
2. ML은 수익률을 높일 수 있지만, 과적합과 낙폭 위험 때문에 위성 신호로 쓰는 것이 더 실무적이다.
3. Momentum 계열은 강하지만 위기와 반전 리스크가 있다.
4. Low Volatility 단독 전략은 기대만큼 강하지 않았다.
5. 국면대응 Core-Satellite 구조는 수익률보다 낙폭 관리와 설명 가능성을 개선한다.
6. 거래비용, fat-tail, 상관구조 붕괴, 생존편향을 함께 다뤄야 실무형 리서치가 된다.

이 문서는 현재까지의 연구 전체를 설명하는 기준 문서이며, 이후 PDF, 발표자료, Jupyter Notebook, 논문 형식으로 확장할 수 있다.

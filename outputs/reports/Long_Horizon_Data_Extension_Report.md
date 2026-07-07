# Long-Horizon TS2000 Data Extension Report

## 1. 목적

이 확장 작업의 목적은 기존 2023~2025 중심의 KOSPI200 팩터 모델을 2007~2026 장기 재무 패널 기반의 연구 구조로 발전시키는 것이다. 핵심 개선점은 다음과 같다.

- 2007~2026 장기 TS2000 wide 재무 데이터 통합
- 원본 496개 컬럼에 대한 컬럼 사전 생성
- `available_date` 기준 train/validation/test 분리
- Value, Quality에 Growth 팩터 추가
- 장기 재무팩터와 2023~2025 KIS 가격팩터의 as-of 결합
- KODEX 200 대비 신규 통합 모델 백테스트

## 2. 데이터 구조

사용한 원천 파일은 다음 4개다.

- `/Users/leesangeui/Downloads/kospi07-11.xlsx`
- `/Users/leesangeui/Downloads/kospi12-16.xlsx`
- `/Users/leesangeui/Downloads/kospi 17-21.xlsx`
- `/Users/leesangeui/Downloads/kospi22-26.xlsx`

네 파일은 모두 496개 공통 컬럼을 가지며, 회계기간 기준으로 2007-01부터 2026-03까지 이어진다. 표준화 결과는 다음 파일에 저장했다.

- `data/raw/ts2000/fundamentals_long.csv`
- `outputs/tables/ts2000_wide_column_dictionary.csv`
- `outputs/tables/research_split_summary.csv`

표준화 결과:

| 항목 | 값 |
| --- | ---: |
| 표준화 행 수 | 15,756 |
| 종목 수 | 990 |
| 회계기간 | 2007-01 ~ 2026-03 |
| 컬럼 사전 행 수 | 496 |

## 3. 학습/검증/테스트 분리

분리는 결산일이 아니라 모델이 해당 정보를 사용할 수 있었다고 가정하는 `available_date` 기준으로 수행했다. 공시일 원자료가 없는 한계를 감안해 결산월 말 이후 3개월 lag를 적용했다.

| Split | Rows | Tickers | Available Date |
| --- | ---: | ---: | --- |
| Train | 7,550 | 919 | 2007-04-30 ~ 2016-12-31 |
| Validation | 4,099 | 847 | 2017-02-28 ~ 2021-12-31 |
| Test | 4,107 | 842 | 2022-02-28 ~ 2026-06-30 |

이 구조는 향후 팩터 선택, 가중치 튜닝, 모델 학습을 train/validation에서만 수행하고 test 구간에서 최종 검증하는 방식으로 확장하기 위한 기반이다.

## 4. 추가 팩터

기존 모델은 Value, Quality, Momentum, Low Volatility 중심이었다. 장기 wide 데이터에서 다음 Growth 팩터를 추가했다.

- `sales_growth`: 높을수록 긍정
- `asset_growth`: 낮을수록 긍정

자산성장률을 낮을수록 긍정으로 둔 이유는 과도한 자산 확장이 미래 수익률 저하와 연결될 수 있다는 투자/자산성장 anomaly를 반영하기 위해서다.

신규 composite 가중치는 다음과 같다.

```text
Composite Score
= 0.25 * Quality
+ 0.25 * Value
+ 0.20 * Momentum
+ 0.20 * Low Volatility
+ 0.10 * Growth
```

## 5. 백테스트 결과

가격 데이터는 현재 KIS API로 확보된 KOSPI200 200개 종목의 2023-01-02~2025-12-30 구간을 사용했다. 벤치마크는 KODEX 200 ETF 가격이다.

| Strategy | Total Return | CAGR | Vol | Sharpe | MDD | Active Return | IR | Turnover |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 기존 통합 멀티팩터 | 109.11% | 29.88% | 21.49% | 1.39 | -17.62% | 3.62% | 0.11 | 25.43% |
| 기존 국면 대응 전략 | 95.94% | 26.92% | 19.34% | 1.39 | -17.61% | -2.91% | -0.08 | 29.52% |
| 장기 재무 확장 통합 모델 | 109.28% | 29.92% | 20.73% | 1.44 | -15.21% | 3.71% | 0.10 | 22.19% |

해석하면, 장기 재무 확장 모델은 총수익률을 거의 유지하면서 변동성, 최대낙폭, turnover를 낮췄다. 이는 재무팩터의 장기 안정성이 가격 모멘텀 중심 모델의 리스크를 일부 완화했을 가능성을 시사한다.

## 6. 팩터 검증

장기 통합 모델 기준 Rank IC 검증 결과:

| Factor | Mean Rank IC | Positive IC Rate |
| --- | ---: | ---: |
| Composite | 0.0202 | 54.29% |
| Quality | 0.0077 | 51.43% |
| Value | 0.0059 | 57.14% |
| Momentum | -0.0019 | 55.17% |
| Low Volatility | -0.0099 | 41.38% |

Composite Rank IC가 양수라는 점은 통합 스코어가 다음 1개월 초과수익률에 대해 약한 예측력을 가진다는 의미다. 다만 수치 자체는 크지 않으므로, 면접에서는 "강한 알파를 확정했다"가 아니라 "장기 패널 기반으로 검증 가능한 연구 프레임워크를 구축했고, 초기 out-of-sample 구간에서 리스크 조정 성과 개선 신호를 확인했다"라고 설명하는 것이 적절하다.

## 7. 최신 정량 스크리닝 후보

최신 `2025-12-30` 기준 Top 후보는 `outputs/portfolios/latest_recommendation_candidates.csv`에 저장했다. 이 목록은 투자 권유가 아니라 팩터 기반 모델 포트폴리오 후보군이다.

상위 후보 예시:

1. `000660` 에스케이하이닉스(주)
2. `001430` (주)세아베스틸지주
3. `298040` 효성중공업(주)
4. `010060` 오씨아이홀딩스(주)
5. `071970` 에이치디현대마린엔진(주)

## 8. 다음 단계

다음 단계는 가격 데이터 구간을 2007년까지 확장하는 것이다. 현재 재무 데이터는 2007~2026으로 확장됐지만, 가격 백테스트는 KIS 가격 확보 범위인 2023~2025에 머물러 있다. 따라서 장기 연구를 완성하려면 다음이 필요하다.

- KIS API 또는 별도 데이터 소스로 2007~2026 일별 가격 확보
- 리밸런싱 시점별 실제 KOSPI200 구성종목 이력 확보
- train/validation 구간에서 팩터 가중치 튜닝
- test 구간에서 최종 고정 모델 성과 검증
- 상승장, 하락장, 위기장별 팩터 기여도 분해

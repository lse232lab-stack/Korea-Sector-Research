# 한국 주식시장에서의 장기 멀티팩터 및 국면대응 퀀트 전략 연구

## 초록

본 연구는 2007년부터 2026년 6월까지의 KOSPI200 투자 가능 종목군을 대상으로, 재무 팩터와 가격 팩터, 그리고 머신러닝 기반 예측 신호를 결합한 장기 주식 퀀트 전략을 설계하고 검증한다. 연구의 목적은 단순히 높은 백테스트 수익률을 얻는 것이 아니라, 논문 및 실무 운용 부서에서 설명 가능한 형태의 전략 구조를 제시하는 데 있다. 이를 위해 Value, Quality, Growth, Momentum, Low Volatility 팩터를 구성하고, Ridge 회귀와 Composite Baseline을 이용해 다음 1개월 초과수익률을 예측했다. 또한 단일 팩터 전략 10개를 비교한 뒤, Core-Satellite 구조와 시장 국면별 위험노출 조절을 결합한 institutional strategy를 제안했다.

핵심 결과는 세 가지다. 첫째, 시간순 8:1:1 분할에서는 검증 구간 기준 Composite Baseline이 Ridge 모델보다 우수하게 선택되었으며, 이는 복잡한 모델이 항상 실전 투자성과를 개선하지 않음을 시사한다. 둘째, 단일 팩터보다 Momentum, Value+Momentum, Balanced Multi-Factor 계열이 장기적으로 우수했다. 셋째, 제안한 Institutional Core-Satellite 전략은 전체 기간 CAGR 18.43%, Sharpe 0.95, MDD -41.46%를 기록했고, Test 구간에서는 CAGR 35.22%, Sharpe 1.41, MDD -19.03%를 기록해 수익성과 낙폭 관리의 균형을 개선했다.

## 1. 서론

주식 퀀트 전략은 크게 세 가지 질문을 다룬다. 첫째, 어떤 정보가 미래 수익률과 관련되는가. 둘째, 그 정보가 학습 구간 밖에서도 유지되는가. 셋째, 실제 운용 가능한 포트폴리오로 전환했을 때 수익률, 변동성, 낙폭, 회전율이 허용 가능한가. 본 연구는 이 세 질문을 한국 대형주 장기 데이터에 적용한다.

기존 프로젝트 단계에서는 멀티팩터 점수를 만들고 백테스트하는 데 집중했다. 본 논문 초안에서는 연구 설계를 한 단계 정교화한다. 특히 금융 시계열에서 흔히 발생하는 미래 정보 누수와 과최적화 문제를 줄이기 위해 랜덤 분할을 사용하지 않고, 시간순 8:1:1 분할과 별도의 시장국면별 robustness split을 함께 사용한다.

## 2. 선행연구

Value 팩터는 Fama and French(1993)의 다요인 모형 이후 주식 횡단면 수익률을 설명하는 대표 요인으로 자리 잡았다. Momentum 팩터는 Jegadeesh and Titman(1993)이 제시한 승자-패자 전략에서 실증적으로 확인되었다. Quality 및 profitability 계열 신호는 단순 저평가 종목의 가치 함정을 줄이고, 지속 가능한 이익 창출 능력을 반영한다. Low risk 또는 low beta anomaly는 Frazzini and Pedersen(2014)의 Betting Against Beta 논의와 연결된다.

본 연구는 이러한 전통적 팩터를 한국 시장 데이터에 맞게 재구성하고, ML 예측 신호를 보조적으로 결합한다. 다만 머신러닝 신호는 과적합 위험이 크므로 단독 절대 신호가 아니라 위성 신호로 제한한다.

## 3. 데이터

가격 데이터는 KIS API 기반 일별 수정주가 패널이며, 2007-01-02부터 2026-06-30까지 200개 종목, 총 780,050개 행으로 구성된다. 재무 데이터는 TS2000 원천 엑셀을 표준화한 장기 패널이며, 2007-01부터 2026-03 회계기간까지 15,756개 행을 포함한다.

본 연구는 현재 KOSPI200 구성종목 기반 universe를 사용한다. 따라서 과거 특정 시점의 실제 KOSPI200 구성종목과 다를 수 있으며, 이는 생존편향의 원인이 된다. 실무 운용 또는 학술 투고 수준으로 발전시키기 위해서는 point-in-time universe가 필요하다.

## 4. 방법론

### 4.1 팩터 정의

- Value: 저평가 특성을 반영하는 재무 기반 점수
- Quality: 수익성, 안정성, 재무 건전성을 반영하는 점수
- Growth: 매출과 이익 성장성을 반영하는 점수
- Momentum: 12개월-1개월 가격 모멘텀 및 6개월 수익률
- Low Volatility: 1년 변동성과 최대낙폭을 기반으로 한 방어적 점수

각 팩터는 월말 신호일 기준으로 횡단면 표준화된다. 결측 팩터가 있는 경우 사용 가능한 팩터 가중치를 재정규화한다.

### 4.2 예측 타깃

예측 타깃은 월말 신호일 이후 다음 1개월 종목 수익률에서 동일 universe 평균 수익률을 차감한 초과수익률이다. 이는 시장 방향성보다 종목 선택 능력을 평가하기 위한 설계다.

### 4.3 시간순 8:1:1 분할

금융 데이터에서는 관측치가 시간적으로 의존하므로 랜덤 split을 사용하지 않는다. 본 연구의 primary ML split은 월말 신호일을 시간순으로 정렬한 뒤 80%를 train, 다음 10%를 validation, 마지막 10%를 test로 사용한다.

| research_split | rows | tickers | months | min_signal_date | max_signal_date | mean_target_1m_excess | mean_feature_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| train | 28155 | 190 | 181 | 2007-07-31 | 2022-07-29 | 0.0000% | 9.77 |
| validation | 4422 | 196 | 23 | 2022-08-31 | 2024-06-28 | -0.0000% | 9.95 |
| test | 4567 | 200 | 23 | 2024-07-31 | 2026-05-29 | -0.0000% | 9.96 |

### 4.4 모델

두 모델을 비교한다. 첫째, Composite Baseline은 기존 멀티팩터 composite score를 train 구간에서 초과수익률 단위로 선형 scaling한 설명 가능한 benchmark 모델이다. 둘째, Ridge Linear는 여러 팩터와 가격 변수를 사용해 다음 1개월 초과수익률을 예측하는 정규화 선형회귀 모델이다. 모델 선택 기준은 validation 구간의 평균 Rank IC다.

| model_name | research_split | rows | months | rmse | direction_hit_rate | mean_rank_ic | median_rank_ic | positive_rank_ic_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| composite_baseline | test | 4567 | 23 | 0.1462 | 50.78% | 0.0486 | 0.0350 | 60.87% |
| composite_baseline | train | 28155 | 181 | 0.1034 | 50.30% | 0.0217 | 0.0237 | 57.46% |
| composite_baseline | validation | 4422 | 23 | 0.1188 | 48.33% | 0.0110 | -0.0095 | 47.83% |
| ridge_linear | test | 4567 | 23 | 0.1460 | 54.74% | 0.0392 | 0.0534 | 69.57% |
| ridge_linear | train | 28155 | 181 | 0.1033 | 51.51% | 0.0305 | 0.0231 | 60.77% |
| ridge_linear | validation | 4422 | 23 | 0.1187 | 51.38% | 0.0070 | -0.0329 | 39.13% |

## 5. 전략 실험

### 5.1 실무형 전략 라이브러리

본 연구는 단일 모델 하나에 의존하지 않고, 실무에서 자주 사용하는 10개 스타일 전략을 동일 조건으로 비교했다. 전략군은 Deep Value, Quality, Growth, Price Momentum, Low Volatility, Balanced Multi-Factor, Value+Momentum, Quality+LowVol Defensive, Momentum+Growth Aggressive, ML Predicted Return이다.

| strategy_name | category | cagr | annualized_volatility | sharpe | max_drawdown | information_ratio | average_turnover |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ML Predicted Return | machine_learning | 21.76% | 24.99% | 0.87 | -52.86% | 0.91 | 25.45% |
| Balanced Multi-Factor | multi_factor | 19.09% | 21.37% | 0.89 | -48.20% | 0.66 | 21.41% |
| Value + Momentum Barbell | multi_factor | 19.83% | 23.21% | 0.85 | -50.09% | 0.63 | 22.61% |
| Price Momentum | price | 20.45% | 24.39% | 0.84 | -51.91% | 0.61 | 22.07% |
| Momentum + Growth Aggressive | aggressive | 19.16% | 23.85% | 0.80 | -51.39% | 0.55 | 21.34% |
| Earnings Growth | fundamental | 15.68% | 22.19% | 0.71 | -51.66% | 0.52 | 8.77% |
| Deep Value | valuation | 15.71% | 22.78% | 0.69 | -64.60% | 0.46 | 4.27% |
| Quality Compounder | fundamental | 14.26% | 20.80% | 0.69 | -50.41% | 0.29 | 3.60% |
| Quality + Low Vol Defensive | defensive | 11.23% | 20.72% | 0.54 | -48.22% | -0.06 | 16.70% |
| Low Volatility | defensive | 8.99% | 21.92% | 0.41 | -53.81% | -0.25 | 18.66% |

### 5.2 Institutional Core-Satellite Strategy

최종 제안 전략은 Core-Satellite 구조다. Core는 Balanced Multi-Factor로 구성하고, Satellite는 Value+Momentum, Defensive, ML 신호로 구성한다. 시장 국면은 내부 동일가중 universe index의 200일 이동평균, 60일 수익률, 60일 변동성, 120일 낙폭으로 구분한다. Bull 국면에서는 ML과 Momentum 계열 비중을 높이고, Bear 또는 Stress 국면에서는 Defensive와 현금 비중을 높인다.

## 6. 결과

### 6.1 시간순 8:1:1 ML 결과

8:1:1 split에서는 validation Rank IC 기준 Composite Baseline이 선택되었다. Test 구간에서 Composite Baseline의 평균 Rank IC는 0.0486, 양수 Rank IC 비율은 60.87%였다. Ridge Linear는 Test Rank IC 0.0392와 방향성 적중률 54.74%를 기록했지만 validation Rank IC가 낮아 최종 모델로 선택되지 않았다. 이는 예측 모델 선택에서 test 성과를 사후적으로 선택 기준에 사용하지 않는다는 점에서 중요하다.

선택된 8:1:1 ML 포트폴리오 백테스트 결과는 다음과 같다.

| days | total_return | cagr | annualized_volatility | sharpe | max_drawdown | win_rate | active_total_return | information_ratio | average_turnover | rebalance_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4661 | 2431.73% | 19.09% | 21.37% | 0.89 | -48.20% | 55.14% | 218.85% | 0.66 | 21.41% | 227 |

### 6.2 Institutional Strategy 결과

| days | total_return | cagr | annualized_volatility | sharpe | max_drawdown | win_rate | active_total_return | information_ratio | average_turnover | rebalance_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4661 | 2183.84% | 18.43% | 19.50% | 0.95 | -41.46% | 54.90% | 187.63% | 0.45 | 24.94% | 227 |

구간별 성과는 다음과 같다.

| period | start_date | end_date | total_return | cagr | annualized_volatility | sharpe | max_drawdown | active_total_return | information_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| train_2007_2016 | 2007-08-01 | 2016-12-29 | 211.47% | 13.04% | 17.59% | 0.74 | -41.46% | 43.77% | 0.27 |
| validation_2017_2021 | 2017-01-02 | 2021-12-30 | 97.13% | 14.93% | 17.16% | 0.87 | -38.87% | 11.88% | 0.18 |
| test_2022_2026 | 2022-01-03 | 2026-06-30 | 271.95% | 35.22% | 25.03% | 1.41 | -19.03% | 78.83% | 1.07 |
| full_2007_2026 | 2007-08-01 | 2026-06-30 | 2183.84% | 18.43% | 19.50% | 0.95 | -41.46% | 187.63% | 0.45 |

## 7. 논의

본 연구의 가장 중요한 발견은 세 가지다.

첫째, 복잡한 모델이 항상 우월하지 않다. 8:1:1 검증에서는 Composite Baseline이 선택되었고, 이는 설명 가능한 멀티팩터 모델이 강력한 기준선임을 보여준다. Ridge 모델은 test 구간에서 일부 지표가 좋았지만, validation 기준으로 선택되지 않았으므로 실전 연구에서는 사후 선택 편향을 피해야 한다.

둘째, 단일 팩터보다 조합형 팩터가 더 실무적이다. Price Momentum과 ML 전략은 높은 수익률을 보였지만 MDD와 변동성도 컸다. Balanced Multi-Factor와 Core-Satellite 구조는 수익률을 일부 포기하는 대신 낙폭과 변동성 측면에서 더 방어 가능한 구조를 제공했다.

셋째, 국면대응 overlay는 수익률 극대화보다 손실 관리에 기여한다. Institutional Core-Satellite 전략은 ML 단독 전략보다 전체 CAGR은 낮지만, 전체 MDD와 Test MDD를 의미 있게 줄였다. 실제 고객 자금 운용에서는 최고 수익률보다 설명 가능성, 낙폭 관리, 재현 가능성이 더 중요할 수 있다.

## 8. 한계

본 연구는 아직 실무 운용 또는 학술 투고 수준에서 몇 가지 한계를 가진다. 첫째, universe가 현재 KOSPI200 구성종목 기반이므로 생존편향이 존재한다. 둘째, 공식 KOSPI200 지수가 아니라 동일 universe equal-weight benchmark를 사용했다. 셋째, 거래비용은 10bp 단순 가정이며 시장충격, 가격제한폭, 거래정지, 체결 지연을 완전히 반영하지 못했다. 넷째, ML 모델은 walk-forward 재학습 구조가 아직 완성되지 않았다.

## 9. 향후 연구

향후 연구는 다음 방향으로 발전시킬 수 있다.

1. Point-in-time KOSPI200 구성종목 이력 구축
2. 공식 KOSPI200 및 KODEX200 benchmark와의 재검증
3. Walk-forward ML 재학습 및 feature drift 모니터링
4. 업종 중립화, 종목 cap, ADV 기반 유동성 제약 추가
5. 거래비용 5bp, 10bp, 20bp, 50bp 민감도 분석
6. 월별 성과분해, 하락장 성과, turnover attribution 분석
7. Explainable AI 기반 종목별 편입 사유 리포트 생성

## 10. 결론

본 연구는 한국 대형주 universe에서 장기 멀티팩터, ML 예측, 국면대응 overlay를 결합한 실무형 퀀트 전략을 설계하고 검증했다. 시간순 8:1:1 split은 모델 선택의 엄격성을 높였으며, 결과적으로 단순하지만 설명 가능한 Composite Baseline의 중요성을 확인했다. 최종 Institutional Core-Satellite 전략은 높은 수익률만을 추구하는 접근보다, 설명 가능성과 낙폭 관리를 함께 고려하는 운용 프레임으로 제안된다.

## 참고문헌

- Fama, E. F. and French, K. R. (1993). Common risk factors in the returns on stocks and bonds. Journal of Financial Economics. https://doi.org/10.1016/0304-405X(93)90023-5
- Jegadeesh, N. and Titman, S. (1993). Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency. Journal of Finance. https://doi.org/10.1111/j.1540-6261.1993.tb04702.x
- Frazzini, A. and Pedersen, L. H. (2014). Betting Against Beta. Journal of Financial Economics. https://doi.org/10.1016/j.jfineco.2013.10.005
- Novy-Marx, R. (2013). The Other Side of Value: The Gross Profitability Premium. Journal of Financial Economics. https://doi.org/10.1016/j.jfineco.2013.01.003

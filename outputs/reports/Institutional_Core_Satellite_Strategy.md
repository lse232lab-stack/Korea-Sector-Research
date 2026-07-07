# Institutional Core-Satellite Quant Strategy

## 1. 목적

이 전략은 논문 또는 S&T/운용 부서의 내부 투자전략 검토 문서에서 방어 가능한 수준을 목표로 설계했다. 단일 팩터의 과최적화 위험을 줄이기 위해 여러 검증된 알파 신호를 앙상블하고, 시장 국면에 따라 팩터 가중치와 주식 노출을 조정한다.

## 2. 이론적 근거

- Value: Fama and French의 다요인 모형은 장부가치 대비 저평가된 주식의 수익률 차이를 체계적 요인으로 해석한다.
- Momentum: Jegadeesh and Titman의 3~12개월 승자-패자 모멘텀 연구는 가격 추세 신호가 단기 이후 수익률을 설명할 수 있음을 보였다.
- Quality/Profitability: profitability 계열 신호는 단순 저평가 함정을 줄이고 기업의 지속 가능한 이익 창출력을 반영한다.
- Low Risk/Low Volatility: Frazzini and Pedersen의 Betting Against Beta 계열 연구는 레버리지 제약이 낮은 위험 자산의 상대적 프리미엄으로 이어질 수 있음을 설명한다.
- Machine Learning: ML은 비선형 조합과 조건부 예측력을 포착할 수 있지만, 과적합 위험 때문에 단독 전략이 아니라 위성 신호로 제한한다.

## 3. 전략 구조

월말마다 모든 종목의 하위 신호를 cross-sectional z-score로 표준화한 뒤, 시장 국면별 가중치로 최종 점수를 계산한다.

### 3.1 하위 신호

| 신호 | 구성 |
| --- | --- |
| Balanced | Quality 25%, Value 25%, Momentum 20%, Low Volatility 20%, Growth 10% |
| Value Momentum | Value 35%, Momentum 35%, Quality 15%, Low Volatility 15% |
| Defensive | Quality 45%, Low Volatility 45%, Value 10% |
| Aggressive | Momentum 60%, Growth 25%, Quality 15% |
| ML | Ridge 모델의 다음 1개월 초과수익률 예측치 |

### 3.2 국면별 최종 점수

| 국면 | 최종 점수 가중치 | 목표 주식 노출 |
| --- | --- | --- |
| Bull | Balanced 25%, Value Momentum 25%, Aggressive 20%, ML 30% | 100% |
| Neutral | Balanced 40%, Value Momentum 20%, Defensive 20%, ML 20% | 80% |
| Bear | Balanced 30%, Defensive 45%, Value Momentum 10%, ML 15% | 50% |
| Stress | Defensive 65%, Balanced 25%, Value Momentum 5%, ML 5% | 25% |

### 3.3 시장 국면 판정

KOSPI200 구성 종목의 동일가중 지수를 내부 시장 proxy로 만들고, 200일 이동평균, 60일 수익률, 60일 변동성, 120일 낙폭으로 국면을 판정한다. 공식 지수 대신 내부 universe를 쓰는 이유는 현 단계에서 모든 종목의 긴 가격 이력이 이미 확보되어 있고, 전략의 투자 가능 universe와 벤치마크 proxy를 일치시키기 위해서다.

## 4. 포트폴리오 구성

- 매월 말 신호 생성.
- 최종 점수 상위 30개 종목 동일가중.
- 국면별 target_exposure만큼 주식 보유, 잔여 비중은 현금 가정.
- 리밸런싱 회전율 기준 10bp 거래비용 차감.
- 벤치마크는 동일 universe의 일별 동일가중 수익률.

## 5. 백테스트 결과

| days | total_return | cagr | annualized_volatility | sharpe | max_drawdown | win_rate | benchmark_total_return | active_total_return | tracking_error | information_ratio | average_turnover | rebalance_count | benchmark_type | benchmark_path |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4661 | 2183.84% | 18.43% | 19.50% | 0.95 | -41.46% | 54.90% | 694.02% | 187.63% | 12.26% | 0.45 | 0.2493906020558003 | 227 | universe_equal_weight |  |

## 6. 구간별 검증

| strategy_id | strategy_name | period | start_date | end_date | days | total_return | cagr | annualized_volatility | sharpe | max_drawdown | win_rate | benchmark_total_return | active_total_return | tracking_error | information_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| institutional_core_satellite | Institutional Core-Satellite | train_2007_2016 | 2007-08-01 | 2016-12-29 | 2335 | 211.47% | 13.04% | 17.59% | 0.74 | -41.46% | 54.56% | 116.65% | 43.77% | 12.37% | 0.27 |
| institutional_core_satellite | Institutional Core-Satellite | validation_2017_2021 | 2017-01-02 | 2021-12-30 | 1229 | 97.13% | 14.93% | 17.16% | 0.87 | -38.87% | 54.27% | 76.21% | 11.88% | 11.19% | 0.18 |
| institutional_core_satellite | Institutional Core-Satellite | test_2022_2026 | 2022-01-03 | 2026-06-30 | 1097 | 271.95% | 35.22% | 25.03% | 1.41 | -19.03% | 56.34% | 107.99% | 78.83% | 13.15% | 1.07 |
| institutional_core_satellite | Institutional Core-Satellite | full_2007_2026 | 2007-08-01 | 2026-06-30 | 4661 | 2183.84% | 18.43% | 19.50% | 0.95 | -41.46% | 54.90% | 694.02% | 187.63% | 12.26% | 0.45 |

## 7. 최신 모델 후보군

아래는 투자 의견이 아니라, 최종 점수 기준 최신 상위 스크리닝 결과다.

| ticker | name | signal_date | regime | target_exposure | balanced_score | value_momentum_score | defensive_score | ml_score | ml_signal_date | composite_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 000660 | 에스케이하이닉스(주) | 2026-06-30 | neutral | 0.8000 | 3.0000 | 3.0000 | -0.0135 | 3.0000 | 2026-05-29 | 2.3973 |
| 011070 | 엘지이노텍(주) | 2026-06-30 | neutral | 0.8000 | 2.9363 | 3.0000 | -0.8046 | 1.8677 | 2026-05-29 | 1.9871 |
| 009150 | 삼성전기(주) | 2026-06-30 | neutral | 0.8000 | 2.6978 | 3.0000 | -1.8152 | 3.0000 | 2026-05-29 | 1.9161 |
| 047040 | (주)대우건설 | 2026-06-30 | neutral | 0.8000 | 1.8626 | 3.0000 | -2.1113 | 3.0000 | 2026-05-29 | 1.5228 |
| 081660 | (주)미스토홀딩스 | 2026-06-30 | neutral | 0.8000 | 1.9245 | 0.1231 | 2.2675 | 0.4312 | 2026-05-29 | 1.3342 |
| 005930 | 삼성전자(주) | 2026-06-30 | neutral | 0.8000 | 1.4443 | 2.0302 | -0.8438 | 2.0216 | 2026-05-29 | 1.2193 |
| 402340 | 에스케이스퀘어(주) | 2026-06-30 | neutral | 0.8000 | 1.4743 | 1.6399 | -1.8798 | 3.0000 | 2026-05-29 | 1.1418 |
| 138930 | (주)BNK금융지주 | 2026-06-30 | neutral | 0.8000 | 1.5599 | 0.4333 | 1.2899 | 0.8078 | 2026-05-29 | 1.1302 |
| 000990 | (주)디비하이텍 | 2026-06-30 | neutral | 0.8000 | 1.2036 | 1.5122 | -0.3994 | 1.6298 | 2026-05-29 | 1.0300 |
| 034730 | 에스케이(주) | 2026-06-30 | neutral | 0.8000 | 1.3860 | 1.8438 | -0.7119 | 0.9979 | 2026-05-29 | 0.9804 |

## 8. 실무 적용 전 필수 보완

1. Point-in-time KOSPI200 구성종목 이력으로 생존편향을 제거한다.
2. 공식 KOSPI200 지수 또는 KODEX 200 장기 데이터로 외부 벤치마크를 재검증한다.
3. 거래대금 필터, 단일 종목 5%, 업종 25%, ADV 대비 주문비율 한도를 추가한다.
4. 거래비용을 5bp, 10bp, 20bp, 50bp로 민감도 분석한다.
5. 리밸런싱 다음날 체결, 가격제한폭, 거래정지, 실적 발표 직후 gap risk를 반영한다.
6. ML 신호는 walk-forward 재학습과 feature drift 모니터링 없이는 실전 비중을 제한한다.

## 9. 참고 문헌 및 근거 자료

- Fama, E. F. and French, K. R. (1993), Common risk factors in the returns on stocks and bonds.
- Jegadeesh, N. and Titman, S. (1993), Returns to Buying Winners and Selling Losers.
- Frazzini, A. and Pedersen, L. H. (2014), Betting Against Beta.
- Novy-Marx, R. (2013), The Other Side of Value: The Gross Profitability Premium.

Regime table: `outputs/tables/institutional_market_regime.csv`

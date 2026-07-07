# Practical Quant Strategy Lab

실무에서 자주 쓰이는 주식 퀀트 전략 10가지를 동일한 데이터, 동일한 월간 리밸런싱, 동일한 Top 30 동일가중 조건으로 비교했다. 이 실험은 특정 전략을 바로 매수 추천하기보다, 어떤 투자 아이디어가 한국 대형주 장기 데이터에서 더 견고했는지 확인하기 위한 연구용이다.

## Tested Strategies

| strategy_id | strategy_name | category | description | weights |
| --- | --- | --- | --- | --- |
| deep_value | Deep Value | valuation | 저평가 종목군에 집중하는 전통적 가치 전략 | value_score=1.00 |
| quality_compounder | Quality Compounder | fundamental | 수익성, 안정성, 재무 건전성이 우수한 기업 선호 | quality_score=1.00 |
| earnings_growth | Earnings Growth | fundamental | 실적 성장성과 개선 흐름이 강한 종목 선호 | growth_score=1.00 |
| price_momentum | Price Momentum | price | 12개월-1개월 가격 모멘텀이 강한 종목 선호 | momentum_score=1.00 |
| low_volatility | Low Volatility | defensive | 낙폭과 변동성이 낮은 방어적 종목 선호 | low_volatility_score=1.00 |
| balanced_multifactor | Balanced Multi-Factor | multi_factor | Value, Quality, Growth, Momentum, Low Volatility 균형 결합 | quality_score=0.25, value_score=0.25, momentum_score=0.20, low_volatility_score=0.20, growth_score=0.10 |
| value_momentum_barbell | Value + Momentum Barbell | multi_factor | 저평가와 가격추세를 동시에 요구하는 실무형 조합 | value_score=0.35, momentum_score=0.35, quality_score=0.15, low_volatility_score=0.15 |
| quality_low_vol_defensive | Quality + Low Vol Defensive | defensive | 하락장 대응을 의식한 퀄리티와 저변동성 중심 전략 | quality_score=0.45, low_volatility_score=0.45, value_score=0.10 |
| momentum_growth_aggressive | Momentum + Growth Aggressive | aggressive | 강한 가격추세와 실적 성장성을 결합한 공격형 알파 전략 | momentum_score=0.60, growth_score=0.25, quality_score=0.15 |
| ml_predicted_return | ML Predicted Return | machine_learning | Ridge 모델의 1개월 초과수익률 예측치를 랭킹 신호로 사용 | ml_predicted_excess_forward_1m_return=1.00 |

## Full-Period Ranking

| strategy_name | category | total_return | cagr | annualized_volatility | sharpe | max_drawdown | active_total_return | information_ratio | average_turnover |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ML Predicted Return | machine_learning | 3712.17% | 21.76% | 24.99% | 0.87 | -52.86% | 380.11% | 0.91 | 25.45% |
| Balanced Multi-Factor | multi_factor | 2431.73% | 19.09% | 21.37% | 0.89 | -48.20% | 218.85% | 0.66 | 21.41% |
| Value + Momentum Barbell | multi_factor | 2739.60% | 19.83% | 23.21% | 0.85 | -50.09% | 257.62% | 0.63 | 22.61% |
| Price Momentum | price | 3021.71% | 20.45% | 24.39% | 0.84 | -51.91% | 293.16% | 0.61 | 22.07% |
| Momentum + Growth Aggressive | aggressive | 2460.79% | 19.16% | 23.85% | 0.80 | -51.39% | 222.51% | 0.55 | 21.34% |

## Test-Period Ranking: 2022~2026

| strategy_name | category | period | total_return | cagr | annualized_volatility | sharpe | max_drawdown | active_total_return | information_ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ML Predicted Return | machine_learning | test_2022_2026 | 238.33% | 32.31% | 27.88% | 1.16 | -27.61% | 62.67% | 1.01 |
| Price Momentum | price | test_2022_2026 | 289.54% | 36.67% | 30.43% | 1.20 | -24.60% | 87.29% | 1.01 |
| Momentum + Growth Aggressive | aggressive | test_2022_2026 | 254.89% | 33.77% | 29.40% | 1.15 | -25.40% | 70.63% | 0.91 |
| Value + Momentum Barbell | multi_factor | test_2022_2026 | 208.95% | 29.58% | 28.29% | 1.05 | -23.30% | 48.54% | 0.74 |
| Balanced Multi-Factor | multi_factor | test_2022_2026 | 185.13% | 27.21% | 24.98% | 1.09 | -27.00% | 37.09% | 0.73 |
| Quality Compounder | fundamental | test_2022_2026 | 149.07% | 23.32% | 23.26% | 1.00 | -28.48% | 19.75% | 0.56 |
| Earnings Growth | fundamental | test_2022_2026 | 138.11% | 22.05% | 22.73% | 0.97 | -20.97% | 14.48% | 0.43 |
| Deep Value | valuation | test_2022_2026 | 82.42% | 14.81% | 23.40% | 0.63 | -23.32% | -12.30% | -0.32 |
| Quality + Low Vol Defensive | defensive | test_2022_2026 | 71.45% | 13.18% | 22.01% | 0.60 | -23.29% | -17.57% | -0.51 |
| Low Volatility | defensive | test_2022_2026 | 30.84% | 6.37% | 24.01% | 0.27 | -26.83% | -37.09% | -0.94 |

## Interpretation

- 단일 팩터는 특정 국면에서 강하지만 장기 성과와 낙폭 안정성이 흔들릴 수 있다.
- 실무 운용에서는 단일 팩터보다 Value+Momentum, Quality+Low Vol, Balanced Multi-Factor처럼 서로 다른 성격의 신호를 결합하는 방식이 더 설명 가능하고 관리하기 쉽다.
- ML 예측 전략은 알파 잠재력이 크지만 과적합, 회전율, 낙폭 위험을 별도로 통제해야 한다.
- 다음 단계에서는 각 전략별 월별 승률, 하락장 성과, 업종 노출, 회전율과 거래비용 민감도를 추가해야 한다.

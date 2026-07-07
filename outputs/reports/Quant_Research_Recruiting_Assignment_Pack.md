# Quant Research Recruiting Assignment Pack

## 목적

증권사 퀀트리서치 사전과제는 단순한 코딩 테스트가 아니라, 데이터 수집, 정제, 통계검정, 포트폴리오 구성, 백테스트, 해석 능력을 함께 확인한다. 이 문서는 사용자가 보유한 KOSPI200 장기 가격/팩터 데이터를 바탕으로 사전과제형 문항을 실제 프로젝트 산출물로 연결한 결과다.

## 사전과제 요구 역량과 프로젝트 산출물

| question | assignment_theme | demonstrated_skill | project_artifact |
| --- | --- | --- | --- |
| Q50 | Covariance Matrix / Minimum Variance Portfolio | 공분산 행렬, 최적화, rolling window | q50_min_variance_latest_weights.csv |
| Q52 | PCA on monthly returns | 차원축소, 시장 공통요인 해석 | q52_pca_summary.csv |
| Q54 | Low-volatility strategy bootstrap | 전략 성과 검정, bootstrap CI | q54_low_vol_bootstrap.csv |
| Q56 | Momentum skip-month test | 모멘텀 정의 비교, 반전효과 점검 | q56_momentum_skip_month_comparison.csv |
| Q57 | Transaction-cost sensitivity | 실무 거래비용 가정과 성과 민감도 | q57_transaction_cost_sensitivity.csv |
| Q58 | Equal / volatility / risk-parity weighting | 포트폴리오 가중 방식 비교 | q58_weighting_comparison.csv |
| Q59 | Fat-tail diagnostics | 왜도, 첨도, tail risk | q59_fat_tail_summary.csv |
| Q60 | Correlation breakdown in stress periods | 상관 상승과 분산효과 붕괴 | q60_correlation_breakdown.csv |
| Q76 | Lagging rule / look-ahead bias | 재무정보 사용 가능일 통제 | existing integrated factor pipeline |
| Q99 | End-to-end pipeline | 수집-정제-팩터-검증-리포트 자동화 | main.py pipeline steps |

## Q50. 최근 30일 공분산 기반 Minimum Variance Portfolio

최근 30거래일 수익률 공분산 행렬에 ridge 안정화를 적용하고, 음수 비중을 0으로 절단한 long-only minimum variance proxy를 계산했다.

| ticker | weight |
| --- | --- |
| 000990 | 0.029499 |
| 097950 | 0.021770 |
| 002030 | 0.020515 |
| 035420 | 0.020403 |
| 012450 | 0.020309 |
| 268280 | 0.020180 |
| 456040 | 0.019523 |
| 483650 | 0.019213 |
| 010950 | 0.018196 |
| 005300 | 0.017503 |

Rolling 10일 단위 포트폴리오 변화:

| window_end_date | asset_count | effective_weight_count | top_weight | top5_weight_sum | turnover_vs_prev_window |
| --- | --- | --- | --- | --- | --- |
| 2026-02-12 | 200 | 159.539700 | 0.020970 | 0.098051 | 0.312873 |
| 2026-03-04 | 200 | 99.651624 | 0.030956 | 0.131366 | 0.306845 |
| 2026-03-18 | 200 | 98.459677 | 0.030897 | 0.129804 | 0.116536 |
| 2026-04-01 | 200 | 101.162082 | 0.031591 | 0.127332 | 0.166792 |
| 2026-04-15 | 200 | 105.748086 | 0.033033 | 0.123533 | 0.216033 |
| 2026-04-29 | 200 | 130.219099 | 0.023465 | 0.106324 | 0.185033 |
| 2026-05-15 | 200 | 150.296800 | 0.020081 | 0.093830 | 0.321468 |
| 2026-06-01 | 200 | 151.306459 | 0.023189 | 0.102916 | 0.344036 |
| 2026-06-16 | 200 | 121.603076 | 0.023251 | 0.111600 | 0.247008 |
| 2026-06-30 | 200 | 111.795963 | 0.029499 | 0.112496 | 0.216819 |

## Q52. 월간 수익률 PCA

첫 번째 주성분은 시장 공통요인에 가까우며, 위기 구간에서 PC1 설명력이 상승하면 분산효과가 약해졌다고 해석할 수 있다.

| period | months | tickers | pc1_var_ratio | pc2_var_ratio | pc3_var_ratio | pc1_to_pc3_cumulative |
| --- | --- | --- | --- | --- | --- | --- |
| full_2007_2026 | 233 | 200 | 0.205408 | 0.045585 | 0.035041 | 0.286034 |
| rate_hike_2022 | 12 | 190 | 0.439105 | 0.115071 | 0.083511 | 0.637687 |
| recent_2024_2026 | 30 | 200 | 0.270977 | 0.088758 | 0.072440 | 0.432175 |

## Q54. Low Volatility Bootstrap

Low Volatility 상위 30종목의 다음 월 초과수익률에 대해 bootstrap 평균 신뢰구간을 계산했다.

| months | mean_monthly_excess_return | median_monthly_excess_return | bootstrap_ci_2_5 | bootstrap_ci_97_5 | positive_month_rate |
| --- | --- | --- | --- | --- | --- |
| 143 | -0.002406 | -0.002022 | -0.007051 | 0.002065 | 0.489510 |

## Q56. Momentum Skip-Month 비교

최근 1개월을 포함한 12개월 모멘텀과 최근 1개월을 제외한 12개월-1개월 모멘텀을 비교했다.

| momentum_definition | months | mean_monthly_excess_return | annualized_excess_return | volatility_of_monthly_excess | positive_month_rate |
| --- | --- | --- | --- | --- | --- |
| include_recent_1m | 221 | 0.008811 | 0.111008 | 0.043882 | 0.565611 |
| exclude_recent_1m | 221 | 0.008299 | 0.104260 | 0.040140 | 0.588235 |

## Q57. 거래비용 민감도

같은 멀티팩터 전략에 대해 0bp, 10bp, 30bp 거래비용을 적용했다.

| days | total_return | cagr | annualized_volatility | sharpe | max_drawdown | win_rate | benchmark_total_return | active_total_return | tracking_error | information_ratio | average_turnover | rebalance_count | benchmark_type | benchmark_path | transaction_cost_bps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4661 | 2557.78% | 19.40% | 21.37% | 0.91 | -47.89% | 55.18% | 694.02% | 234.73% | 9.76% | 0.69 | 21.41% | 227 | universe_equal_weight |  | 0.000000 |
| 4661 | 2431.73% | 19.09% | 21.37% | 0.89 | -48.20% | 55.14% | 694.02% | 218.85% | 9.76% | 0.66 | 21.41% | 227 | universe_equal_weight |  | 10.000000 |
| 4661 | 2197.19% | 18.47% | 21.37% | 0.86 | -48.81% | 55.07% | 694.02% | 189.31% | 9.76% | 0.61 | 21.41% | 227 | universe_equal_weight |  | 30.000000 |

## Q58. 가중 방식 비교

Equal-weight, inverse-volatility, score-weight 방식의 성과를 비교했다.

| days | total_return | cagr | annualized_volatility | sharpe | max_drawdown | win_rate | benchmark_total_return | active_total_return | tracking_error | information_ratio | weighting_method |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4661 | 2557.78% | 19.40% | 21.37% | 0.91 | -47.89% | 55.18% | 694.02% | 234.73% | 9.76% | 0.69 | equal_weight |
| 4661 | 2013.31% | 17.93% | 19.79% | 0.91 | -46.31% | 55.07% | 694.02% | 166.16% | 9.30% | 0.56 | inverse_volatility |
| 4661 | 3709.30% | 21.75% | 22.63% | 0.96 | -47.39% | 54.84% | 694.02% | 379.75% | 11.70% | 0.77 | score_weight |

## Q59. Fat-tail 진단

KOSPI200 동일가중 일간 수익률의 왜도, 첨도, empirical tail을 계산했다.

| series | observations | mean | volatility_daily | annualized_volatility | skewness | kurtosis | excess_kurtosis | empirical_1pct | normal_implied_1pct | empirical_5pct | normal_implied_5pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| universe_equal_weight_daily_return | 4805 | 0.000605 | 0.012815 | 0.203437 | -0.632702 | 14.427539 | 11.427539 | -0.036998 | -0.029203 | -0.018300 | -0.020476 |

## Q60. 위기 국면 상관구조 변화

일반 구간과 위기 구간의 평균 pairwise correlation을 비교했다.

| period | start | end | days | tickers | average_pairwise_correlation | median_pairwise_correlation | corr_90th_percentile |
| --- | --- | --- | --- | --- | --- | --- | --- |
| normal_2019 | 2019-01-01 | 2019-12-31 | 246 | 177 | 0.168356 | 0.158861 | 0.318511 |
| covid_crash_2020_03 | 2020-03-01 | 2020-03-31 | 22 | 177 | 0.667438 | 0.713651 | 0.872290 |
| rate_hike_2022 | 2022-01-01 | 2022-12-31 | 246 | 190 | 0.273558 | 0.269329 | 0.423280 |
| recent_2026_h1 | 2026-01-01 | 2026-06-30 | 120 | 200 | 0.389217 | 0.390292 | 0.559285 |

## 서류/면접 어필 포인트

1. 단순 백테스트가 아니라 사전과제형 문제를 프로젝트 모듈로 확장했다.
2. 공분산, PCA, bootstrap, fat-tail, 거래비용 민감도, 가중 방식 비교를 모두 같은 데이터셋에서 재현 가능하게 구현했다.
3. 금융 시계열에서 중요한 look-ahead bias, survivorship bias, transaction cost 문제를 보고서 한계와 향후 연구에 명시했다.
4. 결과가 좋지 않은 전략도 숨기지 않고 해석했다. 이는 리서치센터에서 중요한 검증 태도다.

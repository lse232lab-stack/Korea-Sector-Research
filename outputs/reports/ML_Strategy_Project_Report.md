# ML Return Prediction and Strategy Report

## 1. Project Objective

This stage extends the long-horizon KOSPI200 multi-factor project into a supervised return-prediction project.

The model predicts next-month excess return using only information available at each monthly signal date. The prediction is then used as a stock-ranking score for a top-30 monthly rebalanced portfolio.

## 2. Dataset

Input data:

- Price panel: `data/raw/price/prices_2007_2026.csv`
- Integrated factor panel: `data/features/integrated_factor_scores_2007_2026.csv`
- Forward-return target dataset: `data/features/ml_forward_return_dataset.csv`

Target:

- `excess_forward_1m_return`
- Defined as each stock's next-month return minus equal-weight universe next-month return.

Features:

- Value score
- Quality score
- Growth score
- Momentum score
- Low volatility score
- Existing composite score
- 6-month return
- 12-month excluding latest 1-month return
- 1-year volatility
- 1-year maximum drawdown

## 3. Split Design

The split is based on `signal_date`, not future target date.

| Split | Rule | Purpose |
| --- | --- | --- |
| Train | 2007-2016 | Fit model parameters |
| Validation | 2017-2021 | Select model specification |
| Test | 2022-2026 | Final out-of-sample evaluation |

This prevents selecting a model using test-period performance.

## 4. Models

Two transparent models were compared.

| Model | Description |
| --- | --- |
| `composite_baseline` | Scales the existing composite factor score into expected excess-return units |
| `ridge_linear` | Numpy-based ridge regression using train-only median imputation and standardization |

The selected model is `ridge_linear`, chosen by validation Rank IC.

## 5. Prediction Metrics

| Model | Split | Mean Rank IC | Positive IC Rate | Direction Hit Rate | RMSE |
| --- | --- | ---: | ---: | ---: | ---: |
| Composite baseline | Train | 0.0244 | 56.14% | 50.45% | 0.1050 |
| Composite baseline | Validation | 0.0231 | 61.67% | 49.60% | 0.1029 |
| Composite baseline | Test | 0.0214 | 52.83% | 49.06% | 0.1283 |
| Ridge linear | Train | 0.0500 | 64.04% | 52.38% | 0.1048 |
| Ridge linear | Validation | 0.0233 | 63.33% | 48.41% | 0.1031 |
| Ridge linear | Test | 0.0393 | 56.60% | 51.89% | 0.1281 |

Interpretation:

- Ridge improves test Rank IC versus the baseline.
- Direction hit rate is modest, so the model should be interpreted as a cross-sectional ranking model rather than a precise return forecaster.
- Validation and test Rank IC are both positive, which supports using the model as a stock selection signal.

## 6. Strategy Backtest

The selected model's predicted excess return is used as `composite_score`. Each month the strategy selects the top 30 stocks and equal-weights them.

| Strategy | Period | Total Return | CAGR | Vol | Sharpe | MDD | Active Return | IR |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Integrated multi-factor | Train | 307.63% | 16.38% | 20.24% | 0.85 | -46.79% | 88.15% | 0.71 |
| Integrated multi-factor | Validation | 117.82% | 17.31% | 19.93% | 0.90 | -48.20% | 23.62% | 0.51 |
| Integrated multi-factor | Test | 185.13% | 27.21% | 24.99% | 1.09 | -27.00% | 37.09% | 0.73 |
| ML predicted return | Train | 370.22% | 18.18% | 24.62% | 0.80 | -52.86% | 117.04% | 0.97 |
| ML predicted return | Validation | 139.62% | 19.62% | 22.86% | 0.90 | -47.23% | 35.99% | 0.72 |
| ML predicted return | Test | 238.33% | 32.31% | 27.89% | 1.14 | -27.61% | 62.67% | 1.01 |

Interpretation:

- The ML strategy improves CAGR and active return in validation and test.
- It also increases volatility and train-period MDD, so it is more aggressive than the integrated factor model.
- The test-period IR of 1.01 is encouraging, but survivorship bias and current-constituent universe bias still need to be disclosed.

## 7. Latest ML Screening Candidates

Latest ML candidate signal date: 2026-05-29.

The signal date is 2026-05-29 because the supervised dataset requires a next-month realized target; 2026-06-30 does not yet have a following monthly return in this dataset.

Top candidates:

1. `047040` (주)대우건설
2. `009150` 삼성전기(주)
3. `402340` 에스케이스퀘어(주)
4. `000660` 에스케이하이닉스(주)
5. `298040` 효성중공업(주)
6. `010120` LS일렉트릭(주)
7. `005930` 삼성전자(주)
8. `006800` 미래에셋증권(주)
9. `011070` 엘지이노텍(주)
10. `278470` (주)에이피알

This is a quantitative screening output, not investment advice.

## 8. Interview Explanation

The project can now be explained as follows:

> I built a 2007-2026 KOSPI200 price and financial panel, defined train, validation, and test periods, and used factor information available at each monthly signal date to predict next-month excess return. I compared a transparent composite baseline with a ridge regression model, selected the model on validation Rank IC, and evaluated the selected model on the 2022-2026 test period. The ML strategy improved test CAGR and active return versus the static integrated multi-factor strategy, but also showed higher volatility, so I interpret it as a higher-beta alpha ranking model rather than a pure defensive strategy.

## 9. Next Improvements

- Add point-in-time KOSPI200 membership history.
- Add long-horizon KOSPI200 or KODEX200 benchmark.
- Add walk-forward annual retraining.
- Add risk-aware exposure control to reduce MDD.
- Add sector and liquidity constraints to the ML strategy.

# ML Return Prediction Experiment

## 1. Objective

Predict next-month excess return using only signal-date factor information, then convert the prediction into a top-N model portfolio score.

## 2. Split Design

- Train: signal_date <= 2016-12-31
- Validation: 2017-01-01 <= signal_date <= 2021-12-31
- Test: signal_date >= 2022-01-01

| research_split | rows | tickers | months | min_signal_date | max_signal_date | mean_target_1m_excess | mean_feature_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| train | 16326 | 161 | 114 | 2007-07-31 | 2016-12-29 | 0.0000 | 9.6935 |
| validation | 10499 | 189 | 60 | 2017-01-31 | 2021-12-30 | 0.0000 | 9.8853 |
| test | 10319 | 200 | 53 | 2022-01-28 | 2026-05-29 | -0.0000 | 9.9478 |

## 3. Model Selection

Selected model: `ridge_linear`

| model_name | research_split | rows | months | rmse | mae | prediction_mean | actual_mean | direction_hit_rate | mean_rank_ic | median_rank_ic | positive_rank_ic_rate | residual_std |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| composite_baseline | test | 10319 | 53 | 0.1283 | 0.0861 | 0.0002 | -0.0000 | 0.4906 | 0.0214 | 0.0052 | 0.5283 | 0.1283 |
| composite_baseline | train | 16326 | 114 | 0.1050 | 0.0751 | 0.0000 | 0.0000 | 0.5045 | 0.0244 | 0.0261 | 0.5614 | 0.1050 |
| composite_baseline | validation | 10499 | 60 | 0.1029 | 0.0721 | 0.0003 | -0.0000 | 0.4960 | 0.0231 | 0.0282 | 0.6167 | 0.1029 |
| ridge_linear | test | 10319 | 53 | 0.1281 | 0.0860 | 0.0003 | -0.0000 | 0.5189 | 0.0393 | 0.0372 | 0.5660 | 0.1281 |
| ridge_linear | train | 16326 | 114 | 0.1048 | 0.0750 | -0.0000 | 0.0000 | 0.5238 | 0.0500 | 0.0535 | 0.6404 | 0.1048 |
| ridge_linear | validation | 10499 | 60 | 0.1031 | 0.0725 | 0.0022 | -0.0000 | 0.4841 | 0.0233 | 0.0243 | 0.6333 | 0.1031 |

## 4. Latest Model Candidates

| ticker | name | signal_date | composite_score | predicted_excess_forward_1m_return | research_split |
| --- | --- | --- | --- | --- | --- |
| 047040 | (주)대우건설 | 2026-05-29 | 0.0848 | 0.0848 | test |
| 009150 | 삼성전기(주) | 2026-05-29 | 0.0748 | 0.0748 | test |
| 402340 | 에스케이스퀘어(주) | 2026-05-29 | 0.0681 | 0.0681 | test |
| 000660 | 에스케이하이닉스(주) | 2026-05-29 | 0.0566 | 0.0566 | test |
| 298040 | 효성중공업(주) | 2026-05-29 | 0.0519 | 0.0519 | test |
| 010120 | LS일렉트릭(주) | 2026-05-29 | 0.0330 | 0.0330 | test |
| 005930 | 삼성전자(주) | 2026-05-29 | 0.0293 | 0.0293 | test |
| 006800 | 미래에셋증권(주) | 2026-05-29 | 0.0282 | 0.0282 | test |
| 011070 | 엘지이노텍(주) | 2026-05-29 | 0.0271 | 0.0271 | test |
| 278470 | (주)에이피알 | 2026-05-29 | 0.0241 | 0.0241 | test |

## 5. Interpretation

The validation split chooses the model before test evaluation. The test split must therefore be read as the out-of-sample check of the selected model. The candidate list is a quantitative screening output, not investment advice.

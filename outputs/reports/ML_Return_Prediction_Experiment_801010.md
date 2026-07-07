# ML Return Prediction Experiment

## 1. Objective

Predict next-month excess return using only signal-date factor information, then convert the prediction into a top-N model portfolio score.

## 2. Split Design

- Split scheme: `chronological_801010`
- Random split is not used because financial time-series experiments must preserve chronology.
- `regime_period`: Train 2007~2016, Validation 2017~2021, Test 2022~2026
- `chronological_801010`: monthly signal dates sorted by time, then split 80%/10%/10%

| research_split | rows | tickers | months | min_signal_date | max_signal_date | mean_target_1m_excess | mean_feature_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| train | 28155 | 190 | 181 | 2007-07-31 | 2022-07-29 | 0.0000 | 9.7747 |
| validation | 4422 | 196 | 23 | 2022-08-31 | 2024-06-28 | -0.0000 | 9.9484 |
| test | 4567 | 200 | 23 | 2024-07-31 | 2026-05-29 | -0.0000 | 9.9617 |

## 3. Model Selection

Selected model: `composite_baseline`

| model_name | research_split | rows | months | rmse | mae | prediction_mean | actual_mean | direction_hit_rate | mean_rank_ic | median_rank_ic | positive_rank_ic_rate | residual_std |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| composite_baseline | test | 4567 | 23 | 0.1462 | 0.0983 | -0.0000 | -0.0000 | 0.5078 | 0.0486 | 0.0350 | 0.6087 | 0.1462 |
| composite_baseline | train | 28155 | 181 | 0.1034 | 0.0734 | 0.0000 | 0.0000 | 0.5030 | 0.0217 | 0.0237 | 0.5746 | 0.1034 |
| composite_baseline | validation | 4422 | 23 | 0.1188 | 0.0800 | 0.0001 | -0.0000 | 0.4833 | 0.0110 | -0.0095 | 0.4783 | 0.1188 |
| ridge_linear | test | 4567 | 23 | 0.1460 | 0.0979 | -0.0019 | -0.0000 | 0.5474 | 0.0392 | 0.0534 | 0.6957 | 0.1459 |
| ridge_linear | train | 28155 | 181 | 0.1033 | 0.0734 | -0.0000 | 0.0000 | 0.5151 | 0.0305 | 0.0231 | 0.6077 | 0.1033 |
| ridge_linear | validation | 4422 | 23 | 0.1187 | 0.0799 | 0.0001 | -0.0000 | 0.5138 | 0.0070 | -0.0329 | 0.3913 | 0.1187 |

## 4. Latest Model Candidates

| ticker | name | signal_date | composite_score | predicted_excess_forward_1m_return | research_split |
| --- | --- | --- | --- | --- | --- |
| 000660 | 에스케이하이닉스(주) | 2026-05-29 | 0.0069 | 0.0069 | test |
| 009150 | 삼성전기(주) | 2026-05-29 | 0.0066 | 0.0066 | test |
| 011070 | 엘지이노텍(주) | 2026-05-29 | 0.0059 | 0.0059 | test |
| 081660 | (주)미스토홀딩스 | 2026-05-29 | 0.0056 | 0.0056 | test |
| 047040 | (주)대우건설 | 2026-05-29 | 0.0052 | 0.0052 | test |
| 071050 | 한국투자금융지주(주) | 2026-05-29 | 0.0045 | 0.0045 | test |
| 138930 | (주)BNK금융지주 | 2026-05-29 | 0.0043 | 0.0043 | test |
| 000990 | (주)디비하이텍 | 2026-05-29 | 0.0041 | 0.0041 | test |
| 000210 | 디엘(주) | 2026-05-29 | 0.0038 | 0.0038 | test |
| 175330 | (주)JB금융지주 | 2026-05-29 | 0.0033 | 0.0033 | test |

## 5. Interpretation

The validation split chooses the model before test evaluation. The test split must therefore be read as the out-of-sample check of the selected model. The candidate list is a quantitative screening output, not investment advice.

# Factor Validation and Recommendation Candidate Summary

## Target Coverage

- Rows with forward 1M excess return: 37,859
- Signal dates: 233
- Tickers: 200

## Rank IC Summary

| factor | target | months | mean_rank_ic | median_rank_ic | positive_ic_rate | mean_n |
| --- | --- | --- | --- | --- | --- | --- |
| composite_score | excess_forward_1m_return | 227 | 0.0233 | 0.0227 | 0.5683 | 163.6300 |
| quality_score | excess_forward_1m_return | 219 | 0.0170 | 0.0144 | 0.5571 | 163.7854 |
| value_score | excess_forward_1m_return | 219 | 0.0084 | 0.0065 | 0.5251 | 163.7854 |
| low_volatility_score | excess_forward_1m_return | 227 | 0.0031 | -0.0067 | 0.4978 | 163.6300 |
| momentum_score | excess_forward_1m_return | 227 | 0.0027 | 0.0244 | 0.5374 | 163.6300 |

## Quintile Return Summary

| score | target | quantile | months | mean_forward_return | median_forward_return | mean_n |
| --- | --- | --- | --- | --- | --- | --- |
| composite_score | excess_forward_1m_return | 1 | 227 | -0.0041 | -0.0142 | 33.1233 |
| composite_score | excess_forward_1m_return | 2 | 227 | 0.0001 | -0.0094 | 32.5419 |
| composite_score | excess_forward_1m_return | 3 | 227 | -0.0024 | -0.0129 | 32.4934 |
| composite_score | excess_forward_1m_return | 4 | 227 | 0.0001 | -0.0057 | 32.5419 |
| composite_score | excess_forward_1m_return | 5 | 227 | 0.0062 | -0.0077 | 32.9295 |
| composite_score | excess_forward_1m_return | Q5-Q1 | 227 | 0.0104 | 0.0101 | 0.0000 |

## Latest Model Portfolio Candidates Top 30

| rank | ticker | name | signal_date | composite_score | value_score | quality_score | growth_score | momentum_score | low_volatility_score | return_6m | return_12m_ex_1m | volatility_1y | max_drawdown_1y | candidate_label | recommendation_note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 000660 | 에스케이하이닉스(주) | 2026-06-30 | 0.9754 | -0.4795 | 1.3733 | -0.5625 | 5.1943 | -1.1532 | 3.8446 | 8.4645 | 0.7427 | -0.2657 | factor_based_model_portfolio_candidate | 모멘텀 상위, 퀄리티 양호 |
| 2 | 011070 | 엘지이노텍(주) | 2026-06-30 | 0.7984 | 0.1599 | 0.0627 | 0.0648 | 4.2722 | -0.5910 | 2.4911 | 8.5046 | 0.7893 | -0.4020 | factor_based_model_portfolio_candidate | 모멘텀 상위, 밸류에이션 우호 |
| 3 | 009150 | 삼성전기(주) | 2026-06-30 | 0.7303 | -0.3293 | 0.1409 | -0.1825 | 5.3134 | -1.3351 | 7.6324 | 14.9925 | 0.7299 | -0.2229 | factor_based_model_portfolio_candidate | 모멘텀 상위 |
| 4 | 081660 | (주)미스토홀딩스 | 2026-06-30 | 0.5097 | -0.5562 | 1.6586 | 2.5228 | -0.4179 | 0.3268 | -0.0675 | 0.1080 | 0.3708 | -0.3339 | factor_based_model_portfolio_candidate | 퀄리티 양호, 성장성 양호, 저변동성 우호 |
| 5 | 047040 | (주)대우건설 | 2026-06-30 | 0.4920 | 0.4279 | -1.0501 | -0.5339 | 4.0441 | -0.5393 | 4.0106 | 4.8810 | 0.9569 | -0.5104 | factor_based_model_portfolio_candidate | 모멘텀 상위, 밸류에이션 우호 |
| 6 | 138930 | (주)BNK금융지주 | 2026-06-30 | 0.4056 | -0.0323 | 0.9097 | 1.8683 | -0.2126 | 0.2099 | 0.0676 | 0.4291 | 0.3496 | -0.2989 | factor_based_model_portfolio_candidate | 퀄리티 양호, 성장성 양호, 저변동성 우호 |
| 7 | 402340 | 에스케이스퀘어(주) | 2026-06-30 | 0.3812 | -2.9985 | 0.4783 | 2.5591 | 4.9056 | -1.1289 | 4.8417 | 7.3086 | 0.8152 | -0.3130 | factor_based_model_portfolio_candidate | 모멘텀 상위, 성장성 양호 |
| 8 | 005930 | 삼성전자(주) | 2026-06-30 | 0.3726 | -0.2907 | 0.4354 | 0.0196 | 2.5662 | -0.8936 | 2.1421 | 4.3010 | 0.6014 | -0.2330 | factor_based_model_portfolio_candidate | 모멘텀 상위 |
| 9 | 000210 | 디엘(주) | 2026-06-30 | 0.3685 | 0.2265 | 0.8139 | 1.2565 | -0.2652 | 0.1789 | 0.1076 | 0.2027 | 0.6391 | -0.4629 | factor_based_model_portfolio_candidate | 퀄리티 양호, 밸류에이션 우호, 성장성 양호, 저변동성 우호 |
| 10 | 034730 | 에스케이(주) | 2026-06-30 | 0.3560 | -0.0003 | 0.2892 | 0.1700 | 2.0448 | -0.7109 | 2.3360 | 2.4472 | 0.6341 | -0.2876 | factor_based_model_portfolio_candidate | 모멘텀 상위 |
| 11 | 071050 | 한국투자금융지주(주) | 2026-06-30 | 0.3323 | 0.0395 | 1.1401 | 1.2414 | 0.1420 | -0.5758 | 0.3583 | 0.8730 | 0.6383 | -0.3162 | factor_based_model_portfolio_candidate | 퀄리티 양호, 밸류에이션 우호, 성장성 양호 |
| 12 | 096770 | 에스케이이노베이션(주) | 2026-06-30 | 0.3222 | 0.2392 | 0.6591 | 1.7976 | -0.4170 | 0.0065 | -0.1030 | 0.1790 | 0.5932 | -0.4025 | factor_based_model_portfolio_candidate | 퀄리티 양호, 밸류에이션 우호, 성장성 양호, 저변동성 우호 |
| 13 | 000990 | (주)디비하이텍 | 2026-06-30 | 0.3040 | 0.1259 | 0.6017 | -0.0455 | 1.4450 | -0.8119 | 1.2083 | 2.9259 | 0.7716 | -0.3488 | factor_based_model_portfolio_candidate | 모멘텀 상위, 퀄리티 양호, 밸류에이션 우호 |
| 14 | 066570 | 엘지전자(주) | 2026-06-30 | 0.2784 | 0.2178 | -0.0715 | 0.0060 | 1.4228 | -0.2167 | 1.1527 | 2.9702 | 0.8343 | -0.5009 | factor_based_model_portfolio_candidate | 모멘텀 상위, 밸류에이션 우호 |
| 15 | 175330 | (주)JB금융지주 | 2026-06-30 | 0.2722 | -0.2369 | 1.1897 | 0.1018 | -0.3632 | 0.4824 | 0.0000 | 0.1327 | 0.4160 | -0.3907 | factor_based_model_portfolio_candidate | 퀄리티 양호, 저변동성 우호 |
| 16 | 161890 | 한국콜마(주) | 2026-06-30 | 0.2488 | 0.1299 | 0.3517 | 0.0682 | -0.0286 | 0.6363 | 0.5844 | -0.0479 | 0.4501 | -0.4405 | factor_based_model_portfolio_candidate | 밸류에이션 우호, 저변동성 우호 |
| 17 | 139130 | (주)아이엠금융지주 | 2026-06-30 | 0.2349 | 0.0138 | 0.6968 | 0.9113 | -0.1393 | -0.0300 | 0.1412 | 0.4948 | 0.3776 | -0.2688 | factor_based_model_portfolio_candidate | 퀄리티 양호, 밸류에이션 우호, 성장성 양호 |
| 18 | 005380 | 현대자동차(주) | 2026-06-30 | 0.2130 | 0.2076 | 0.1601 | 0.0087 | 0.9626 | -0.3615 | 0.7158 | 2.5097 | 0.6410 | -0.3593 | factor_based_model_portfolio_candidate | 밸류에이션 우호 |
| 19 | 000120 | 씨제이대한통운(주) | 2026-06-30 | 0.2083 | 0.3915 | 0.0965 | -0.0585 | -0.5602 | 1.0207 | -0.2241 | 0.0071 | 0.4370 | -0.5072 | factor_based_model_portfolio_candidate | 밸류에이션 우호, 저변동성 우호 |
| 20 | 004170 | (주)신세계 | 2026-06-30 | 0.1988 | 0.1881 | 0.1626 | -0.1046 | 1.5993 | -0.9911 | 2.0200 | 1.7944 | 0.5805 | -0.2019 | factor_based_model_portfolio_candidate | 모멘텀 상위, 밸류에이션 우호 |
| 21 | 259960 | (주)크래프톤 | 2026-06-30 | 0.1948 | -0.0191 | 0.6051 | 0.1176 | -0.5555 | 0.7383 | -0.0445 | -0.3268 | 0.4188 | -0.4419 | factor_based_model_portfolio_candidate | 퀄리티 양호, 저변동성 우호 |
| 22 | 004000 | 롯데정밀화학(주) | 2026-06-30 | 0.1922 | 0.3727 | 0.1954 | 0.1745 | -0.3110 | 0.4747 | -0.0588 | 0.3942 | 0.4409 | -0.4038 | factor_based_model_portfolio_candidate | 밸류에이션 우호, 저변동성 우호 |
| 23 | 069960 | (주)현대백화점 | 2026-06-30 | 0.1868 | 0.3450 | 0.1598 | 0.0945 | 0.5348 | -0.2788 | 1.1146 | 0.5250 | 0.5639 | -0.3300 | factor_based_model_portfolio_candidate | 밸류에이션 우호 |
| 24 | 073240 | 금호타이어(주) | 2026-06-30 | 0.1771 | 0.3158 | 0.4922 | -0.3151 | -0.5331 | 0.5660 | -0.2204 | 0.0767 | 0.4525 | -0.4283 | factor_based_model_portfolio_candidate | 밸류에이션 우호, 저변동성 우호 |
| 25 | 268280 | 미원스페셜티케미칼(주) | 2026-06-30 | 0.1659 | 0.1515 | 0.4771 | -0.0624 | -0.7189 | 0.7937 | -0.2811 | -0.3329 | 0.3018 | -0.3839 | factor_based_model_portfolio_candidate | 밸류에이션 우호, 저변동성 우호 |
| 26 | 023530 | 롯데쇼핑(주) | 2026-06-30 | 0.1643 | 0.4177 | 0.1696 | 0.0846 | 0.8124 | -0.7671 | 1.2840 | 0.9852 | 0.5098 | -0.2037 | factor_based_model_portfolio_candidate | 밸류에이션 우호 |
| 27 | 251270 | 넷마블(주) | 2026-06-30 | 0.1642 | 0.1525 | 0.1121 | 0.5894 | -0.6772 | 0.8728 | -0.2401 | -0.2940 | 0.4447 | -0.4831 | factor_based_model_portfolio_candidate | 밸류에이션 우호, 성장성 양호, 저변동성 우호 |
| 28 | 014820 | 동원시스템즈(주) | 2026-06-30 | 0.1612 | 0.3116 | 0.1516 | 0.1897 | -0.7017 | 0.8337 | -0.2875 | -0.2720 | 0.3910 | -0.4440 | factor_based_model_portfolio_candidate | 밸류에이션 우호, 저변동성 우호 |
| 29 | 456040 | 오씨아이(주) | 2026-06-30 | 0.1603 | 0.4485 | -0.2305 | -0.1473 | 0.4082 | 0.1946 | 0.5750 | 1.2091 | 0.6200 | -0.4547 | factor_based_model_portfolio_candidate | 밸류에이션 우호, 저변동성 우호 |
| 30 | 105560 | (주)KB금융지주 | 2026-06-30 | 0.1600 | -0.4977 | 1.0937 | 1.3478 | -0.0823 | -0.5365 | 0.2700 | 0.4075 | 0.4006 | -0.1842 | factor_based_model_portfolio_candidate | 퀄리티 양호, 성장성 양호 |

Note: This is a quantitative screening result, not investment advice. Use it as model portfolio candidate output for research and interview discussion.

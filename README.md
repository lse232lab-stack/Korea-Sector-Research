# KOSPI200 Fundamental Factor Model Portfolio

KOSPI200 재무팩터 기반 Model Portfolio 구축 프로젝트입니다.

이 프로젝트의 목표는 여러 모델을 얕게 나열하는 것이 아니라, KOSPI200 유니버스에서 Value, Quality, Momentum, Low Volatility 팩터가 향후 수익률을 설명하는지 검증하고, 이를 바탕으로 설명 가능한 Model Portfolio를 구성하는 것입니다.

## Research Question

한국 KOSPI200 종목에서 Value, Quality, Growth, Momentum, Low Volatility 팩터는 향후 수익률을 설명하는가?

그리고 검증된 팩터를 활용해 KOSPI200 대비 초과성과를 추구하는 Model Portfolio를 만들 수 있는가?

## MVP Scope

초기 버전은 ML 모델을 무리하게 적용하지 않고, 다음 흐름을 정확하게 구현하는 데 집중합니다.

1. KOSPI200 유니버스 및 원천 데이터 로딩
2. 가격, 재무, 벤치마크 데이터 정제
3. Value, Quality, Growth, Momentum, Low Volatility 팩터 계산
4. Rank IC, IC summary, quintile return으로 팩터 검증
5. 고정 가중치 기반 composite score 생성
6. Top 30 동일가중 및 스코어가중 포트폴리오 구성
7. 월간 리밸런싱 백테스트
8. 거래비용, turnover, drawdown, TE, IR 등 성과 및 리스크 분석
9. 제출 가능한 표, 차트, 리포트 생성

## Project Structure

```text
kospi200_factor_model/
  README.md
  requirements.txt
  config/
    universe.yaml
    factor_config.yaml
    backtest_config.yaml
  docs/
    data_schema.md
  data/
    raw/
      price/
      ts2000/
      benchmark/
    processed/
    features/
  outputs/
    charts/
    reports/
    tables/
    portfolios/
  src/
    data/
    factors/
    research/
    portfolio/
    backtest/
    report/
  notebooks/
  main.py
```

## Folder Roles

- `config/`: 유니버스, 팩터, 백테스트 기본 설정을 저장합니다.
- `docs/data_schema.md`: 가격, 재무, 벤치마크 CSV 입력 스키마를 정의합니다.
- `docs/kis_api.md`: KIS API 기반 가격 데이터 수집 방식을 정의합니다.
- `data/raw/price/`: 종목별 또는 통합 일별 OHLCV CSV를 저장합니다.
- `data/raw/ts2000/`: TS2000 재무데이터 CSV를 저장합니다.
- `data/raw/benchmark/`: KOSPI200, KOSPI 등 벤치마크 일별 지수 CSV를 저장합니다.
- `data/processed/`: 정제된 중간 데이터가 저장될 위치입니다.
- `data/features/`: 월별 팩터 점수와 composite score가 저장될 위치입니다.
- `outputs/charts/`: 누적수익률, drawdown, IC, quintile, sector exposure 차트가 저장될 위치입니다.
- `outputs/reports/`: 최종 PDF 리포트가 저장될 위치입니다.
- `outputs/tables/`: factor_scores, IC summary, 성과지표 등 CSV 테이블이 저장될 위치입니다.
- `outputs/portfolios/`: 월별 포트폴리오 비중 및 current model portfolio가 저장될 위치입니다.
- `src/data/`: 데이터 로딩, 유니버스 관리, 정제 모듈입니다.
- `src/factors/`: 개별 팩터와 composite score 계산 모듈입니다.
- `src/research/`: Rank IC, quintile return 등 팩터 검증 모듈입니다.
- `src/portfolio/`: 포트폴리오 구성 규칙, 제약조건, 리밸런싱 모듈입니다.
- `src/backtest/`: 백테스트 엔진, 성과지표, 리스크 분석 모듈입니다.
- `src/report/`: 차트, 표, PDF 리포트 생성 모듈입니다.
- `notebooks/`: 데이터 점검, 팩터 검증, 백테스트, 현재 포트폴리오 확인용 노트북입니다.

## Current Data Input

현재 프로젝트에는 KIS API 가격 데이터와 TS2000 재무데이터가 들어와 있습니다.

- 가격 데이터: `data/raw/price/prices.csv`
- TS2000 재무데이터: `data/raw/ts2000/fundamentals.csv`
- KOSPI200 유니버스 데이터: `data/raw/benchmark/kospi200_constituents.csv`

현재 가격 데이터 범위는 KOSPI200 200개 종목의 2023-01-02~2025-12-30 일별 OHLCV입니다. 재무데이터는 기존 단일 TS2000 원천 엑셀을 표준화한 2013-03~2025-06 분기 데이터와, 2007~2026 장기 wide TS2000 엑셀 4개를 통합하는 확장 파이프라인을 함께 지원합니다.

자세한 컬럼 정의는 `docs/data_schema.md`와 각 `*_schema.csv` 파일을 확인하세요.

## Key Factor Definitions

### Value

- PBR: 낮을수록 긍정
- PER: 낮을수록 긍정
- PSR: 낮을수록 긍정
- EV/EBITDA: 낮을수록 긍정, 데이터 확보 시 추가

### Quality

- ROE: 높을수록 긍정
- ROA: 높을수록 긍정
- Operating Margin: 높을수록 긍정
- Debt Ratio: 낮을수록 긍정
- Operating Cash Flow / Net Income: 높을수록 긍정, 데이터 확보 시 추가

### Growth

- Sales Growth: 높을수록 긍정
- Asset Growth: 낮을수록 긍정. 과도한 자산 팽창이 향후 수익률을 낮추는 투자/자산성장 anomaly를 반영합니다.

### Momentum

- 최근 6개월 수익률
- 최근 12개월 수익률에서 최근 1개월 제외
- KOSPI200 대비 상대수익률

### Low Volatility

- 최근 1년 변동성: 낮을수록 긍정
- KOSPI200 대비 beta: 낮을수록 긍정
- 최근 1년 maximum drawdown: 낮을수록 긍정

## Composite Score

초기 고정 가중치는 다음과 같습니다.

```text
Composite Score
= 0.25 * Quality
+ 0.25 * Value
+ 0.20 * Momentum
+ 0.20 * Low Volatility
+ 0.10 * Growth
```

## Long-Horizon Research Split

장기 TS2000 wide 데이터는 `available_date` 기준으로 아래와 같이 분리합니다. 팩터 선택과 가중치 조정은 학습/검증 구간에서만 수행하고, 최종 성과 평가는 테스트 구간에서 확인합니다.

```text
Train:      available_date <= 2016-12-31
Validation: 2017-01-01 <= available_date <= 2021-12-31
Test:       available_date >= 2022-01-01
```

## Backtest Assumptions

- 월간 리밸런싱
- 매월 말 팩터 계산
- 다음 월 첫 거래일 체결 가정
- 매수/매도 각각 10bp 거래비용 기본 적용
- KOSPI200 벤치마크 대비 성과 비교
- Top 30 동일가중 및 스코어가중 포트폴리오 비교
- 단일 종목 최대비중 5%
- 단일 섹터 최대비중 25%

## Bias Control

프로젝트 전반에서 다음 한계를 명시하고 관리합니다.

- 재무데이터는 결산일이 아니라 사용 가능일 기준으로 처리해야 합니다.
- 공시일이 없으면 보수적 lag를 적용합니다.
- 현재 KOSPI200 구성종목만 사용하면 survivorship bias가 발생할 수 있습니다.
- 거래비용과 turnover를 반드시 함께 봅니다.
- long-short 성과는 한국시장의 공매도 제약을 고려해 연구용 검증으로만 해석합니다.

## Run Pipeline

프로젝트 루트에서 아래 순서로 실행합니다.

```bash
pip install -r requirements.txt
python main.py --step validate-data
python main.py --step prepare-long-fundamentals --fundamentals-output data/raw/ts2000/fundamentals_long.csv
python main.py --step build-factors --fundamentals-path data/raw/ts2000/fundamentals_long.csv --factor-output data/features/factor_scores_long.csv
python main.py --step build-factors
python main.py --step build-integrated-factors
python main.py --step run-backtest --backtest-factor-path data/features/price_factor_scores.csv --backtest-output-dir outputs/backtest
python main.py --step run-backtest --backtest-factor-path data/features/integrated_factor_scores.csv --backtest-output-dir outputs/backtest_integrated
python main.py --step run-backtest --backtest-factor-path data/features/price_factor_scores.csv --backtest-output-dir outputs/backtest_kodex200 --benchmark-path data/raw/benchmark/kodex200_prices.csv
python main.py --step run-backtest --backtest-factor-path data/features/integrated_factor_scores.csv --backtest-output-dir outputs/backtest_integrated_kodex200 --benchmark-path data/raw/benchmark/kodex200_prices.csv
python main.py --step generate-report
```

KIS API로 가격 데이터를 추가 수집할 때는 `.env`의 KIS 인증정보를 사용합니다.

```bash
python main.py --step fetch-prices \
  --tickers-file data/raw/benchmark/kospi200_constituents.csv \
  --start 20230101 \
  --end 20231231 \
  --output data/raw/price/prices.csv \
  --request-sleep 1.2 \
  --resume
```

2007~2026 장기 가격 데이터는 연도별 파일로 나누어 수집합니다. 전체 200개 종목을 한 번에 받으면 수 시간이 걸릴 수 있으므로, `--resume`을 켜고 연도별 CSV를 남기는 방식을 기본으로 사용합니다.

```bash
python main.py --step fetch-long-prices \
  --tickers-file data/raw/benchmark/kospi200_constituents.csv \
  --start-year 2007 \
  --end-year 2026 \
  --end 20260630 \
  --yearly-output-dir data/raw/price/yearly \
  --output data/raw/price/prices_2007_2026.csv \
  --request-sleep 1.0 \
  --resume
```

수집이 중간에 끊기면 같은 명령을 다시 실행합니다. 이미 충분히 받은 90일 chunk는 건너뜁니다. 연도별 파일만 다시 합치고 싶을 때는 아래 명령을 사용합니다.

```bash
python main.py --step combine-yearly-prices \
  --start-year 2007 \
  --end-year 2026 \
  --yearly-output-dir data/raw/price/yearly \
  --output data/raw/price/prices_2007_2026.csv
```

## Current Outputs

- 가격 팩터 백테스트: `outputs/backtest/backtest_summary.csv`
- 통합 멀티팩터 백테스트: `outputs/backtest_integrated/backtest_summary.csv`
- KODEX 200 기준 가격 팩터 백테스트: `outputs/backtest_kodex200/backtest_summary.csv`
- KODEX 200 기준 통합 멀티팩터 백테스트: `outputs/backtest_integrated_kodex200/backtest_summary.csv`
- 최종 리포트 Markdown: `outputs/reports/KOSPI200_Factor_Model_Initial_Report.md`
- 최종 리포트 PDF: `outputs/reports/KOSPI200_Factor_Model_Initial_Report.pdf`

## Next Data To Add

1. KIS API로 2007~2026 가격 이력 전체 수집
2. 실제 KOSPI200 지수 또는 ETF 벤치마크 가격 장기 확장
3. 리밸런싱 시점별 KOSPI200 구성종목 이력
4. 거래대금 필터와 섹터/종목 cap을 백테스트 엔진에 직접 반영

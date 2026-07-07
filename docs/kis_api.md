# KIS API Price Data Plan

가격 데이터는 한국투자증권 Open API를 사용해 수집합니다. 프로젝트 내부 표준 파일은 다음 위치에 저장합니다.

```text
data/raw/price/prices.csv
```

## Environment Variables

실제 인증 정보는 프로젝트 루트의 `.env`에 둡니다. `.env`는 `.gitignore`에 포함되어 커밋되지 않습니다.

```text
KIS_APP_KEY=
KIS_APP_SECRET=
KIS_PAPER_APP_KEY=
KIS_PAPER_APP_SECRET=
KIS_BASE_URL=https://openapi.koreainvestment.com:9443
KIS_IS_PAPER=false
KIS_ACCOUNT_NO=
KIS_ACCOUNT_PRODUCT_CODE=01
KIS_PAPER_ACCOUNT_NO=
KIS_PAPER_ACCOUNT_PRODUCT_CODE=01
```

모의투자 서버를 사용할 경우:

```text
KIS_BASE_URL=https://openapivts.koreainvestment.com:29443
KIS_IS_PAPER=true
```

상시모의투자 잔고/주문 API는 실전투자용 앱키가 아니라 모의투자용 앱키가 필요합니다. `KIS_IS_PAPER=true`일 때 `KIS_PAPER_APP_KEY`, `KIS_PAPER_APP_SECRET`이 있으면 해당 값을 우선 사용하고, 없으면 기존 `KIS_APP_KEY`, `KIS_APP_SECRET`으로 fallback합니다.
모의투자 계좌번호가 실계좌번호와 다르면 `KIS_PAPER_ACCOUNT_NO`와 `KIS_PAPER_ACCOUNT_PRODUCT_CODE`도 별도로 입력합니다.

## Daily Price Endpoint

국내주식 기간별 시세 endpoint를 사용합니다.

```text
GET /uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice
```

주요 request parameter:

| Parameter | Value | Description |
| --- | --- | --- |
| FID_COND_MRKT_DIV_CODE | J | 주식 시장 구분 |
| FID_INPUT_ISCD | ticker | 6자리 종목코드 |
| FID_INPUT_DATE_1 | YYYYMMDD | 시작일 |
| FID_INPUT_DATE_2 | YYYYMMDD | 종료일 |
| FID_PERIOD_DIV_CODE | D | 일봉 |
| FID_ORG_ADJ_PRC | 0 | 수정주가 사용 |

## Standardized Output

KIS 응답은 `price_loader.py`에서 아래 표준 컬럼으로 변환합니다.

```text
date,ticker,name,open,high,low,close,adj_close,volume,trading_value,market_cap,sector,is_suspended,is_administrative
```

KIS 일별 차트 응답만으로는 `market_cap`, `sector`, 관리종목 여부를 안정적으로 채우기 어렵습니다. 해당 컬럼은 유니버스/섹터 데이터와 결합하는 단계에서 보강합니다.

## Suggested First Fetch

KOSPI200 전체를 받기 전에 3개 종목으로 먼저 연결과 스키마를 검증합니다.

```bash
python main.py --step fetch-prices --tickers 005930 000660 035420 --start 20250101 --end 20251231 --request-sleep 1.0
```

정상 동작을 확인한 뒤 KOSPI200 구성종목 리스트를 기준으로 전체 수집합니다.

## Long-Horizon Fetch

KIS 일별 차트 endpoint는 2007년 과거 일봉도 반환하는 것을 `005930` 삼성전자 샘플로 확인했습니다. 장기 수집은 API 호출 수가 많으므로 연도별 파일로 분리해 저장합니다.

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

주요 산출물:

```text
data/raw/price/yearly/prices_2007.csv
data/raw/price/yearly/prices_2008.csv
...
data/raw/price/yearly/prices_2026.csv
data/raw/price/prices_2007_2026.csv
outputs/tables/long_price_fetch_summary.csv
outputs/tables/long_price_yearly_coverage.csv
```

중간에 실패하면 같은 명령을 다시 실행합니다. `--resume`이 켜져 있으면 이미 충분한 행이 존재하는 90일 단위 chunk는 건너뜁니다.

연도별 CSV를 다시 합칠 때:

```bash
python main.py --step combine-yearly-prices \
  --start-year 2007 \
  --end-year 2026 \
  --yearly-output-dir data/raw/price/yearly \
  --output data/raw/price/prices_2007_2026.csv
```

주의사항:

- 현재 KOSPI200 구성종목 기준으로 과거 가격을 받으면 survivorship bias가 남습니다.
- 200개 종목, 2007~2026 전체 구간은 90일 chunk 기준 약 16,000회 이상 호출될 수 있습니다.
- `request_sleep=1.0` 기준 전체 수집은 수 시간이 걸릴 수 있습니다.

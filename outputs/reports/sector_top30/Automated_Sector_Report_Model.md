# Automated Sector Report Model

## 목적

KOSPI200 코어-위성 퀀트 모델이 산출한 최신 Top30 종목을 섹터별로 분류하고, 각 섹터에 대해 자동 리서치 초안을 생성한다. 이 모델은 애널리스트의 판단을 대체하기보다, 정량 랭킹과 재무 지표를 빠르게 정리해 섹터별 아이디어 발굴 시간을 줄이는 것을 목표로 한다.

## 입력 데이터

- `data/features/institutional_core_satellite_scores.csv`
  - 최신 signal date 기준 composite score, ML score, regime, factor score
- `data/raw/ts2000/fundamentals_long.csv`
  - 최신 연간 재무제표, 매출, 영업이익, 순이익, ROE, OPM, 성장률
- `data/raw/price/prices_2007_2026.csv`
  - KIS API 기반 최신 가격, 거래대금, PER/PBR 계산용 수정주가
- `data/raw/benchmark/kospi200_constituents.csv`
  - KOSPI200 구성종목의 외부 업종 분류. KRX/GICS 원천이 없을 때 사용하는 준공식 fallback
- `data/raw/dart/top30/company_profiles.csv`
  - OpenDART 기업개황, 업종코드, 홈페이지/IR URL
- `data/raw/dart/top30/single_accounts.csv`
  - OpenDART 단일회사 주요계정. 연결(CFS) 재무제표가 있으면 TS2000 값을 보완/대체
- `data/raw/sector/sector_master.csv`
  - KOSPI200 업종, OpenDART 업종코드, TS2000 sector, 수동 override를 통합한 analyst coverage sector master
- `data/raw/dart/top30/dart_text_kpis.csv`
  - OpenDART 정기보고서 원문에서 추출한 수주잔고, 제품/부문, 순차입금, EBITDA, NAV, guidance, margin risk evidence
- `data/raw/dart/top30/dart_table_inventory.csv`
  - OpenDART XML/HTML 원문의 표 구조 inventory. 각 표의 row/column 수, 숫자 개수, category 후보, preview 저장
- `data/raw/dart/top30/*_bridge.csv`
  - revenue segment, EBITDA, backlog, NAV bridge 후보 표. 기업별 analyst note 작성 시 원문 표 후보를 빠르게 검수하기 위한 중간 산출물
- `data/raw/ir/ir_guidance_tables.csv`
  - 로컬 IR PDF가 있을 경우 guidance table 후보를 추출하는 산출물

## 처리 흐름

1. 최신 `signal_date`의 전체 종목을 composite score 기준으로 정렬한다.
2. 상위 30개 종목을 선택한다.
3. 각 종목에 최신 연간 TS2000 재무 데이터와 최신 KIS 가격 데이터를 결합한다.
4. `sector_master.csv`를 1순위로 매핑하고, 없으면 KOSPI200 구성종목 업종, OpenDART 업종코드, TS2000 sector, 티커/회사명 rule 순서로 fallback한다.
5. OpenDART 연결 재무제표가 수집된 종목은 매출, 영업이익, 순이익, 자본총계를 DART 기준으로 보완한다.
6. OpenDART 계정에서 자산총계, 부채총계, 차입부채, 이자수익/비용, 감가상각 계정을 추출해 순차입금 proxy, EBITDA proxy, EV/EBITDA proxy를 계산한다.
7. OpenDART 정기보고서 원문에서 수주잔고, 제품/부문, 순차입금, EBITDA, NAV, guidance, margin risk keyword evidence를 추출한다.
8. OpenDART XML/HTML 표 구조를 파싱해 revenue segment, EBITDA, backlog, NAV bridge 후보 표를 생성한다.
9. 로컬 IR PDF가 있으면 guidance table 후보를 추출한다.
10. EPS, BPS, 현재 PER, 현재 PBR, PSR, earnings yield, operating-income yield, 시가총액/EV proxy를 계산한다.
11. 섹터별 실무형 valuation profile을 매핑한다.
12. 섹터별 요약 지표와 constituent table을 생성한다.
13. 섹터별 PDF/Markdown 리포트와 전체 인덱스, CSV 결과물을 저장한다.
14. 같은 Top30 데이터셋을 기업 단위로 전개해 섹터별 valuation anchor에 맞는 목표주가, 투자의견, 상승여력, 신뢰도, DART evidence를 산출한다.
15. 개별 기업별 analyst note 형식의 PDF/Markdown 리포트와 valuation CSV를 저장한다.

## 섹터별 Valuation 방식

| 섹터 | Primary valuation | Cross-check |
|---|---|---|
| Financials | PBR/ROE | PER, earnings yield, 주주환원 여력 |
| Semiconductors | Cycle-normalized PER | PBR/ROE, 업황 cycle, 이익 revision |
| IT Hardware & Components | Forward PER | PBR/ROE, margin cycle, 고객사 concentration |
| Holdings & Investment | NAV discount | PBR, 자회사 가치, 배당수익, capital allocation |
| Energy & Chemicals | EV/EBITDA or replacement value | PBR, 영업이익 yield, spread cycle |
| Construction & Infrastructure | PBR plus order/margin cycle | PER, OPM, 수주잔고, 해외 프로젝트 risk |
| Auto & Mobility | PER with volume/mix cycle | PBR/ROE, margin, 환율 민감도 |
| Gaming & Internet | PER plus pipeline valuation | PSR, OPM, 신작 pipeline |
| 기타 소비재/물류/레저/패키징 | PER with PBR cross-check | 성장률, OPM, ROE |

자동화 모델은 각 섹터별로 서로 다른 표 컬럼을 사용한다. 예를 들어 금융은 PBR/ROE/Earnings Yield를, 지주는 PBR/NAV evidence를, 에너지·화학과 산업재는 EV/EBITDA proxy와 순부채/자본을, 건설은 backlog evidence와 OPM을 우선 표시한다.

## 출력물

- `Sector_Report_Index.md`: 전체 섹터 리포트 목차
- `latest_top30_sector_classification.csv`: Top30 종목별 섹터 분류 및 주요 지표
- `sector_summary.csv`: 섹터별 요약 지표
- `*_Sector_Report.pdf`: 섹터별 PDF 리포트
- `*_Sector_Report.md`: 섹터별 Markdown 리포트
- `outputs/reports/company_top30/Company_Report_Index.md`: 개별 기업 리포트 목차
- `outputs/reports/company_top30/latest_top30_company_valuations.csv`: Top30 기업별 투자의견, 목표주가, 상승여력, valuation 근거
- `outputs/reports/company_top30/*_Company_Report.pdf`: 개별 기업 PDF analyst note
- `outputs/reports/company_top30/*_Company_Report.md`: 개별 기업 Markdown analyst note

## 실행 방법

```bash
python main.py --step generate-sector-reports
```

개별 기업별 analyst note를 생성하려면:

```bash
python main.py --step generate-company-reports
```

OpenDART 데이터를 먼저 갱신하려면:

```bash
python main.py --step fetch-top30-dart
python main.py --step extract-dart-kpis --fetch-dart-documents
python main.py --step parse-dart-tables --fetch-dart-raw-documents
python main.py --step extract-ir-guidance
python main.py --step build-sector-master
python main.py --step generate-sector-reports
python main.py --step generate-company-reports
```

Top N을 바꾸려면:

```bash
python main.py --step generate-sector-reports --sector-report-top-n 50
python main.py --step generate-company-reports --sector-report-top-n 50
```

## 개선 반영 사항

- 섹터 분류는 더 이상 티커/회사명 rule에만 의존하지 않는다. KOSPI200 구성종목 업종을 우선 사용하고, OpenDART 업종코드와 TS2000 sector를 차례로 사용한 뒤 마지막에 rule을 적용한다.
- Top30 기업에 대해 OpenDART 기업개황, 정기공시 목록, 주요 재무계정 수집기를 추가했다.
- DART 연결 재무제표가 확보된 종목은 리포트 CSV에 `financial_data_basis=OpenDART CFS ...`로 표시된다.
- `sector_master.csv`를 추가해 KOSPI200 업종, OpenDART 업종코드, TS2000 sector, 수동 override를 하나의 analyst coverage sector master로 관리한다.
- OpenDART 정기보고서 원문을 다운로드하고 수주잔고, 제품/부문, 순차입금, EBITDA, NAV, guidance, margin risk evidence를 자동 추출한다.
- OpenDART XML/HTML 표 구조를 파싱해 revenue segment, EBITDA, backlog, NAV bridge 후보를 자동 생성한다.
- IR PDF guidance table parser를 추가해 로컬 IR 자료가 들어오면 guidance table 후보까지 결합할 수 있다.
- 섹터별 리포트에는 DART 재무 커버리지, DART 원문 KPI 커버리지, DART 표 bridge 커버리지, 섹터 분류 원천이 요약되어 자동화 결과의 신뢰도를 점검할 수 있다.
- 개별 기업 리포트 생성기를 추가해 Top30 각 종목에 섹터별 valuation method를 적용한다. 금융은 PBR/ROE, 에너지·산업재·물류는 EV/EBITDA, 지주는 NAV discount proxy, 건설은 PBR+수주/마진 cycle, 일반 성장주는 PER 중심으로 목표주가와 투자의견을 산출한다.
- 개별 리포트에는 목표주가, 상승여력, 투자의견, valuation basis, peer median 비교, 가격 차트, 섹터 peer upside chart, DART evidence table, key risks를 포함한다.

## 남은 한계와 개선 방향

- 섹터 분류는 별도 master로 분리했지만, 아직 KRX/WICS/GICS의 point-in-time 히스토리를 직접 구독한 것은 아니다. 실제 운용 시스템에서는 KRX/WICS/GICS 코드와 내부 analyst coverage sector를 날짜별 master로 관리해야 한다.
- EV/EBITDA, 순차입금, NAV, 수주잔고는 이제 OpenDART 단일계정, 원문 keyword evidence, XML/HTML table bridge 후보를 함께 활용한다. 다만 bridge 후보는 자동 추출 결과이므로 최종 모델 반영 전 analyst 검수가 필요하다.
- 로컬 IR PDF table parser는 구현됐지만, IR PDF 자체의 자동 다운로드는 회사별 IR 사이트 구조가 달라 별도 crawler policy가 필요하다.
- 다음 단계는 bridge 후보 표를 LLM/규칙 기반으로 정규화해 `segment_revenue_model`, `ebitda_bridge_model`, `backlog_bridge_model`, `nav_bridge_model`의 표준 스키마로 확정하고, KRX/WICS/GICS point-in-time 라이선스 데이터를 결합하는 것이다.

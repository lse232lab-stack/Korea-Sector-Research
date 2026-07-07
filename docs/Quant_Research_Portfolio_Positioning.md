# Quant Research Portfolio Positioning

## 프로젝트 한 줄 소개

KIS API 가격 데이터와 TS2000/DART 계열 재무 데이터를 결합해 KOSPI200 장기 멀티팩터 전략, ML 기반 수익률 예측, 국면대응 리스크 오버레이, 사전과제형 통계분석을 end-to-end로 구현한 퀀트 리서치 포트폴리오입니다.

## 지원서용 핵심 어필 문장

한국 대형주 2007~2026년 가격 패널과 장기 재무 데이터를 구축하고, Value, Quality, Growth, Momentum, Low Volatility 팩터를 설계한 뒤, 시간순 8:1:1 검증과 월간 리밸런싱 백테스트를 통해 실무형 Core-Satellite 퀀트 전략을 연구했습니다. 추가로 증권사 퀀트리서치 사전과제 유형에 맞춰 공분산 기반 최소분산 포트폴리오, PCA, bootstrap, 거래비용 민감도, 가중 방식 비교, fat-tail 및 상관구조 붕괴 분석을 재현 가능한 파이프라인으로 구현했습니다.

## 보여줄 수 있는 역량

### 1. 데이터 엔지니어링

- KIS API 기반 일별 가격 데이터 수집 및 장기 패널화
- TS2000/DART 계열 재무 데이터 표준화
- 종목코드, 종목명, 가격, 재무 데이터 결합
- 결측, 중복, 날짜 정렬, 재무정보 사용 가능일 관리

### 2. 퀀트 팩터 리서치

- Value, Quality, Growth, Momentum, Low Volatility 팩터 설계
- Rank IC, 분위 포트폴리오, Q5-Q1 spread 검증
- Momentum skip-month, Low-vol bootstrap, 거래비용 민감도 분석
- 단일 팩터와 멀티팩터 전략의 성과 및 위험 비교

### 3. 포트폴리오 및 리스크 관리

- Minimum Variance Portfolio
- Equal-weight, inverse-volatility, score-weight 비교
- 시장 국면별 target exposure 조절
- 코로나 급락기와 금리상승기 상관구조 변화 분석
- MDD, Sharpe, Information Ratio, turnover 기반 성과 평가

### 4. 머신러닝 검증

- 다음 1개월 초과수익률 예측 데이터셋 구성
- 시간순 8:1:1 train/validation/test split 적용
- Ridge Linear와 Composite Baseline 비교
- Validation 기준 모델 선택 및 test out-of-sample 검증
- 복잡한 모델이 항상 우월하지 않다는 실증 결과 해석

### 5. 리서치 커뮤니케이션

- 고객 배포용 리포트 형식의 전략 설명서 작성
- 논문 초안 형식의 연구 문서 작성
- 사전과제형 문제와 프로젝트 산출물 매핑
- 좋지 않은 결과도 숨기지 않고 한계와 개선 방향 제시

## 대표 산출물

- `outputs/reports/KOSPI200_AI_Quant_Strategy_Client_Report.pdf`
- `outputs/reports/KOSPI200_Quant_Strategy_Research_Paper_Draft.md`
- `outputs/reports/Institutional_Core_Satellite_Strategy.md`
- `outputs/reports/Quant_Research_Recruiting_Assignment_Pack.md`
- `outputs/tables/recruiting_assignment_pack/`

## 면접에서 설명할 핵심 스토리

1. 처음에는 단순 멀티팩터 백테스트로 시작했다.
2. 이후 가격 데이터를 2007~2026년까지 확장하고 재무 데이터와 결합했다.
3. Train/Validation/Test 분리를 명확히 하고, 시간순 8:1:1 split을 추가했다.
4. 단일 전략이 아니라 실무에서 쓰이는 여러 전략을 같은 조건으로 비교했다.
5. 단순 수익률 극대화보다 낙폭, 거래비용, 상관구조, 국면대응을 포함한 실무형 전략으로 발전시켰다.
6. 사전과제형 문항을 프로젝트 산출물로 전환해 실무 문제 해결 능력을 증명했다.

## 보완하면 더 강해지는 부분

- Point-in-time KOSPI200 구성종목 확보로 survivorship bias 제거
- 공식 KOSPI200 지수 또는 KODEX200 장기 벤치마크 연결
- DART API 기반 공시 이벤트 스터디 추가
- 업종 중립화와 유동성 제약 적용
- Jupyter Notebook 형태의 재현 가능한 제출용 패키지 정리

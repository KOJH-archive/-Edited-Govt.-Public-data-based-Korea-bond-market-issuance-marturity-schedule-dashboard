# 📊 한국예탁결제원 & 금융위원회 공공데이터 기반 채권 수급 분석 시스템 - 개발 명세서 & 트러블슈팅 보고서

---

## 1. 시스템 개요 (System Overview)

본 시스템은 **한국예탁결제원(KSD) 채권정보서비스**와 **금융위원회 채권발행정보 V2 오픈 API**를 연동하여 대한민국 발행 채권(시중은행채, 카드채, 캐피탈채, 국고채 등)의 **발행 및 만기도래 실데이터 전수(85,000+ 건 이상) 수집, 증분 ETL 관리, 섹터 자동 분류, 시각화 대시보드 및 AI 시황 분석 리포트**를 제공하는 데이터 파이프라인 시스템입니다.

---

## 2. 기술 스택 (Technology Stack)

본 프로젝트는 **Minimalist & Software 2.0 (Keep it Raw & Build from Scratch)** 원칙을 준수하여, 무거운 프레임워크 대신 표준 라이브러리 및 최적화된 경량 도구를 중심으로 구축되었습니다.

| 구분 | 기술 / 도구 | 선정 사유 및 용도 |
|---|---|---|
| **Core / Runtime** | Python 3.14 (Vanilla Python) | 표준 라이브러리 중심의 간결하고 평면적인(Flat) 코드 구조 |
| **Package Manager** | `uv` | 초고속 패키지 관리 및 `.venv` 가상환경 일관성 유지 |
| **Data Ingestion** | `urllib.request`, `json`, `xml.etree.ElementTree` | 외부 무거운 HTTP 클라이언트 대신 Vanilla Python 표준 모듈 활용 |
| **Database** | SQLite 3 (`bond_data.db`) | WAL(Write-Ahead Logging) 모드를 적용하여 동시 읽기/쓰기 성능 최적화 |
| **Sector Classifier** | `re` (Regular Expressions) | 텍스트 정규식 알고리즘으로 채권 종목명 100% 자동 섹터 분류 |
| **Frontend / Dashboard** | `Streamlit` | 수급 추이, 히트맵, 차환율 및 피벗 테이블 인터랙티브 시각화 |
| **Visualization** | `matplotlib`, `koreanize-matplotlib` | Seaborn 대신 Matplotlib 기반 시각화 및 한글 폰트 자동 인코딩 적용 |
| **AI / Automation** | Antigravity Rule-Based Engine | 시계열 대금 변화(±20%) 및 지방채 순상환/순발행 자동 감지 및 리포트 생성 |

---

## 3. 공공데이터 API 연동 및 ETL 명세

### 3.1 API Key 통합 관리 (Single Key Architecture)
공공데이터포털(`data.go.kr`) 계정당 발급되는 **일반 인증키 1개**로 한국예탁결제원 API와 금융위원회 API를 동시에 100% 사용합니다.

### 3.2 연동 공공데이터 API
1. **한국예탁결제원 채권정보서비스 API (`B552481/BondSvc`)**
   - 트래픽 한도: 일일 100회
   - 오퍼레이션:
     - `/getBondKindInsetlStat`: 채권 종류별 기관결제대금 현황 (`stdYymm`, `bondSetlCost` 등)
     - `/getlocalgovernmentIssuStat`: 지방자치단체별 지방채 발행/상환 현황 (`trainBondRed`, `tratinBondNewnIssu` 등)
2. **금융위원회 채권발행정보 V2 API (`1160100/GetBondTradInfoService_V2`)**
   - 트래픽 한도: **일일 10,000회** (대용량)
   - 오퍼레이션:
     - `/getIssuIssuItemStat_V2`: 대한민국 전체 개별 채권 종목의 발행일, 만기일, 발행금액 전수 수집

### 3.3 증분 수집 ETL (Incremental Sync) 워터마크
- `etl_metadata` 테이블을 통해 마지막 완료 수집일자(`last_fsc_sync_date`)를 워터마크로 관리합니다.
- 당일 이미 수집이 완료되었으면 API 호출을 스킵하여 트래픽 및 불필요한 연산을 절감하고, 신규 실행 시 `UPSERT` 방식으로 DB를 업데이트합니다.

---

## 4. 종목명 정규식 자동 분류기 (`classifier.py`)

외부 분류 API 대신 `re` 기반 알고리즘으로 채권 종목명을 다중 정규식 패턴 매핑하여 자동으로 섹터를 분류합니다.

```python
SECTOR_RULES = [
    ("GOV",     "국고채/공공채", [r"^국고", r"^국민주택", r"지방채", r"한국전력", r"LH", r"도로공사", r"수자원", r".*발전", r".*공단"]),
    ("BANK",    "시중은행채",   [r"국민은행", r"신한은행", r"하나은행", r"우리은행", r"KB금융지주", r".*증권"]),
    ("SBANK",   "특수은행채",   [r"기업은행", r"산업은행", r"산업금융채권", r"한국수출입금융", r"농업금융채권"]),
    ("CARD",    "신용카드채",   [r"신한카드", r"삼성카드", r"현대카드", r"국민카드", r"롯데카드", r"하나카드", r"우리카드"]),
    ("CAPITAL", "캐피탈채",     [r".*캐피탈", r".*오토리스", r".*파이낸셜", r"현대커머셜", r"메리츠캐피탈"])
]
```

---

## 5. 핵심 트러블슈팅 (Troubleshooting & Key Learnings)

### 🚨 Issue 1: FSC API 데이터 금액 단위 불일치 및 단위 표기 혼선
- **문제 현황**: 기존 코드 주석 및 DB 스키마 주석에는 `-- 발행금액 (원)`으로 적혀 있었으나, DB 쿼리 레벨(`db.py`)에서 `/ 1e9` 나누기가 수행되고, UI에서는 "백억원" 표기가 혼용되어 데이터 수치에 대한 신뢰성 문제가 발생함.
- **원인 분석 & Empirical 검증**:
  - 실제 DB에 적재된 FSC API `bondIssuAmt` 원시값을 추출해 검증 수행.
  - 대표 국고채 종목 `KR310101GFA5`의 수집 수치가 `8,800,000,000,000`으로 확인됨 (실제 발행액 8.8조원과 100% 일치).
  - 결과적으로 **API가 전달하는 원시 데이터 단위는 100% 원(KRW)**임이 검증됨.
  - 기존 쿼리의 `/ 1e9` 변환은 10억원(십억원) 단위 계산임에도 UI 주석에는 "백억원"으로 잘못 표기되어 있었음.
- **해결 방안 (파이프라인 역할 분리)**:
  1. **DB 레이어 (`db.py`)**: 불필요하고 왜곡 가능성이 있는 `/1e9` 연산을 전면 제거하고 원(KRW) raw 값을 있는 그대로 반환하도록 수정.
  2. **표현 레이어 (`app.py`)**: 대시보드 로딩 시점에 **억원 단위 (`/ 1e8`)**로 변환하도록 단위를 일원화.
  3. **UI 라벨 전체 수정**: 대시보드 상의 KPI 카드, 차트 Y축, 피벗 테이블, 세부 종목 테이블의 표기를 "백억원"에서 **"억원"**으로 정확히 통일.

### 🚨 Issue 2: DB 쿼리 Refactoring 중 SQL 문법 에러 (`sqlite3.OperationalError`)
- **문제 현황**: `db.py` 쿼리 수정 후 `query_2026_issuance_vs_maturity_by_sector` 실행 시 `no such column: maturity_amt_100m` 예외 발생.
- **원인 분석**: `SELECT` 절의 별칭은 `maturity_amt_raw`로 수정하였으나, 쿼리 하단의 `ORDER BY maturity_amt_100m DESC` 구문에서 기존 컬럼명을 참조하여 발생함.
- **해결 방안**: `ORDER BY maturity_amt_raw DESC`로 컬럼명을 맞춰 수정하고, 전용 파이썬 스크립트를 통해 전체 쿼리가 정상 작동함을 검증.

---

## 6. 데이터베이스 스키마 및 적재 현황 (`bond_data.db`)

SQLite 3 기반 6개 핵심 테이블 구조:

1. **`issuer_mapping`**: 발행기관 마스터 (발행기관 ID, 기관명, 정규식 자동 섹터 코드)
2. **`bond_master`**: 개별 채권 종목 마스터 (ISIN코드, 종목명, 발행일, 만기일, 발행금액 - 원 단위 원시값)
3. **`bond_supply_flow`**: 발행(ISSUE) 및 만기(MATURITY) 수급 팩트 이벤트 테이블
4. **`bond_settlement_stat`**: KSD 기관결제대금 통계 (월별 채권/CD/CP/단기사채 대금)
5. **`local_gov_bond_stat`**: KSD 지방채 발행/상환 통계 (도시철도채, 지역개발채, 일반지방채)
6. **`etl_metadata`**: 증분 수집 워터마크 관리 테이블 (`last_fsc_sync_date`)

---

## 7. Streamlit 대시보드 & AI 시황 리포트 (`app.py`, `analyst.py`)

- **사이드바**: 분석 대상 섹터 다중 선택 필터 및 DB 수집 레코드 현황 표시
- **1 핵심 KPI 카운터**: 2026년 만기도래 총액(억원), 만기도래 종목 수, 2022년~현재 누적 발행액(억원)
- **TAB 1 (2026년 월별 만기 현황)**: 월별/섹터별 스택 바 차트, 파이 차트, 상세 피벗 테이블 및 개별 종목 데이터 조회
- **TAB 2 (2022년~현재 발행 추이)**: 시계열 발행액 누적 바 차트 & 라인 차트
- **TAB 3 (2026년 수급 밸런스 & 차환율)**: 동일 연도 내 섹터별 신규 발행액 vs 만기도래액 비교 바 차트, 차환율(%) 수평 바 차트, 수급 상태 표
- **TAB 4 (AI 시황 분석 리포트)**: 시계열 결제대금 급증/급감(±20%) 및 지방채 순상환 전환 자동 감지 리포트

---

## 8. 시스템 실행 안내

```powershell
# 가상환경 실행 및 대시보드 구동
.\.venv\Scripts\python.exe -m streamlit run app.py

# 원클릭 실행 배치 파일
run_dashboard.bat
```

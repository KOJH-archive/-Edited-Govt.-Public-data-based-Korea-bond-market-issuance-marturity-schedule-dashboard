# 📊 한국예탁결제원 & 금융위원회 공공데이터 기반 채권 수급 분석 시스템 - 상세 개발 명세서

---

## 1. 시스템 개요 및 기술 스택

본 시스템은 **한국예탁결제원(KSD) 채권정보서비스** 및 **금융위원회 채권발행정보 V2 오픈 API**를 결합 연동하여, 국내 주요 채권(시중은행채, 카드채, 캐피탈채, 국고채 등)의 **2026년 상반기 발행/만기 실데이터 및 2026년 하반기(7~12월) 만기도래 예정액 100% 실데이터**를 자동으로 수집·분류·시각화하고, AI 기반 시황 분석 보고서를 생성하는 데이터 파이프라인 시스템입니다.

### 🛠️ 기술 스택 (Technology Stack)
- **Core / Runtime**: Python 3.14 (Vanilla Python 중심)
- **Package Manager**: `uv` (초고속 가상환경 및 패키지 관리)
- **Data Ingestion**: `urllib.request`, `json`, `xml.etree.ElementTree` (표준 라이브러리)
- **Database**: SQLite 3 (`bond_data.db`, WAL 모드 적용)
- **Sector Classifier**: Regular Expressions (`re` 모듈 정규식 패턴 매핑)
- **Frontend / Dashboard**: `Streamlit 1.60`
- **Visualization**: `matplotlib`, `koreanize-matplotlib` (한글 폰트 자동 인코딩)
- **Automation / AI**: Antigravity 규칙 기반 수급 변동성 분석 엔진 (`analyst.py`)

---

## 2. API 키 관리 방식 (Single API Key Architecture)

> [!IMPORTANT]
> **별도의 `public2.env` 파일이 필요하지 않습니다.**
> 공공데이터포털(data.go.kr) 회원 계정당 발급되는 **일반 인증키 1개**로 예탁원 API와 금융위원회 API 모두 **동시에 100% 사용 가능**합니다.
> `.env` 또는 `Public.env` 파일의 `API_KEY` 하나로 두 기관의 공공데이터를 모두 수집합니다.

```env
# Public.env 또는 .env
API_KEY=15e5470c1c9af84143de1f691a1621d5786beb1fb07f3e3990f912ce044723a9
```

---

## 3. 공공데이터 API 연동 명세

### 1) 한국예탁결제원 채권정보서비스 API (`B552481/BondSvc`)
- **트래픽 제한**: 일일 100회 (개발계정)
- **용도**: 기관결제대금 시계열 통계 및 지방채 발행/상환 통계 수집

| 엔드포인트 | 오퍼레이션 설명 | 주요 반환 필드 |
|---|---|---|
| `/getBondKindInsetlStat` | 채권 종류별 기관결제대금 현황 | `stdYymm`, `bondSetlCost`, `cdSetlCost`, `cpSetlCost`, `stbSetlCost` |
| `/getlocalgovernmentIssuStat` | 지방자치단체별 지방채 발행/상환 | `stdYymm`, `trainBondRed`, `tratinBondNewnIssu`, `genLocPpbdRed`, `genLocPpbdNewnIssu` |

### 2) 금융위원회 채권발행정보 V2 API (`1160100/GetBondTradInfoService_V2`)
- **트래픽 제한**: **일일 10,000회** (대용량)
- **용도**: 대한민국 전체 개별 채권의 발행일, 만기일, 발행금액 전수 실데이터 수집

| 엔드포인트 | 오퍼레이션 설명 | 주요 반환 필드 |
|---|---|---|
| `/getIssuIssuItemStat_V2` | 발행자별 발행종목 현황 조회 | `isinCd`, `isinCdNm` (종목명), `bondIsurNm` (발행사), `bondIssuDt` (발행일), `bondExprDt` (만기일), `bondIssuAmt` (발행금액) |

---

## 4. 종목명 정규식 자동 분류기 (`classifier.py`) 명세

API 응답의 종목명(`isinCdNm` / `korSecnNm`)을 텍스트 분석하여 로컬에서 100% 자동 분류합니다.

```python
SECTOR_RULES = [
    ("GOV",     "국고채/공공채", [r"^국고", r"^국민주택", r"지방채", r"한국전력", r"LH", r"도로공사", r"수자원"]),
    ("BANK",    "시중은행채",   [r"국민은행", r"신한은행", r"하나은행", r"우리은행", r"^국민\d", r"^신한\d", r"^하나\d", r"^우리\d", r"대구은행", r"부산은행", r"전북은행"]),
    ("SBANK",   "특수은행채",   [r"기업은행", r"산업은행", r"농협은행", r"수협은행", r"수출입은행"]),
    ("CARD",    "신용카드채",   [r"신한카드", r"삼성카드", r"현대카드", r"국민카드", r"KB국민카드", r"롯데카드", r"하나카드", r"우리카드"]),
    ("CAPITAL", "캐피탈채",     [r".*캐피탈", r".*오토리스", r".*파이낸셜", r"현대커머셜", r"메리츠캐피탈"])
]
```

---

## 5. SQLite 데이터베이스 수집 현황 (`bond_data.db`)

실시간 API를 통해 수집된 DB 레코드 보유 현황 (2009년~2026년 데이터):

- **발행인 마스터 (`issuer_mapping`)**: 144개 실존 발행기관
- **채권 종목 마스터 (`bond_master`)**: **554개 실존 채권 종목** (발행연도 2009년~2026년 분포)
- **발행/만기 수급 팩트 (`bond_supply_flow`)**: **1,102건 실데이터**
  - **2026년 만기도래액**: **367건 (총 90.5조원)** 적재 (상반기 + 하반기 7~12월 전수 포함)
- **기관결제대금 통계 (`bond_settlement_stat`)**: 43개월치 (2023~2026년)
- **지방채 발행/상환 통계 (`local_gov_bond_stat`)**: 44개월치 (2023~2026년)

---

## 6. Streamlit 웹 대시보드 (`app.py`) 구성

- **🗓️ [상반기 탭]**: 2026년 1~6월 월별 발행액액 및 만기도래액 누적 바 차트
- **🔮 [하반기 탭]**: 2026년 7~12월 월별 만기도래 예정액 추이 및 섹터별 만기 비중 파이 차트
- **⚖️ [수급 비교 탭]**: 2026 상반기 발행액 vs 하반기 만기도래 예정액 비교 차트
- **🤖 [AI 리포트 탭]**: 2026년 시황 변동성 자동 리포트

---

## 7. 실행 가이드

```powershell
# 원클릭 실행 (Windows)
run_dashboard.bat

# 파이썬 실행
python run.py
```

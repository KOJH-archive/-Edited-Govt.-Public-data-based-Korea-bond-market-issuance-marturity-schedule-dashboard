# 📊 한국예탁결제원 & 금융위원회 공공데이터 기반 채권 수급 분석 시스템 - 상세 개발 명세서

---

## 1. 시스템 개요 및 기술 스택

본 시스템은 **한국예탁결제원(KSD) 채권정보서비스** 및 **금융위원회 채권발행정보 V2 오픈 API**를 결합 연동하여, 국내 주요 채권(시중은행채, 카드채, 캐피탈채, 국고채 등)의 **2026년 상반기 발행/만기 실데이터 및 2026년 하반기(7~12월) 만기도래 예정액 100% 실데이터**를 자동으로 수집·분류·시각화하고, **하이브리드 AI(룰 베이스 + Gemini LLM) 기반 시황 분석 보고서**를 생성하는 데이터 파이프라인 시스템입니다.

### 🛠️ 기술 스택 (Technology Stack)
- **Core / Runtime**: Python 3.14 (Vanilla Python 중심)
- **Package Manager**: `uv` (초고속 가상환경 및 패키지 관리)
- **Data Ingestion**: `urllib.request`, `json`, `xml.etree.ElementTree` (표준 라이브러리)
- **Database**: SQLite 3 (`bond_data.db`, WAL 모드 적용)
- **Sector Classifier**: Regular Expressions (`re` 모듈 정규식 패턴 매핑)
- **Frontend / Dashboard**: `Streamlit 1.60`
- **Visualization**: `matplotlib`, `koreanize-matplotlib` (한글 폰트 자동 인코딩)
- **Automation / AI**: Antigravity 하이브리드 수급 분석 엔진 (`analyst.py` - Rule-based + Gemini LLM)

---

## 2. API 키 관리 방식 (Single API Key & Gemini LLM)

> [!IMPORTANT]
> - `API_KEY`: 공공데이터포털(data.go.kr) 일반 인증키 (예탁원 API & 금융위 API 100% 공통 사용)
> - `GEMINI_API_KEY`: (선택 사항) 입력 시 Gemini 1.5 Flash 지능형 LLM 프리미엄 시황 분석 리포트 자동 생성

```env
# Public.env 또는 .env
API_KEY=YOUR_PUBLIC_DATA_API_KEY_HERE
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
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

## 5. 하이브리드 AI 시황 분석 모듈 (`analyst.py`)

- **하이브리드 구조**: 외부 의존성 없이 Pure Python `urllib.request`로 Gemini API를 직접 호출.
- **안전장치**: `GEMINI_API_KEY`가 없더라도 시스템 오류 없이 **기존 룰 베이스 리포트가 100% 정상 작동**.
- **기능**:
  - 룰 베이스: 결제대금 전월 대비 ±20% 변동 감지 및 지방채 순발행/순상환 감지
  - Gemini LLM: 룰 베이스 데이터를 프롬프트로 전달하여 거시경제 맥락 및 차환(Refinancing) 리스크 지능형 리포트 작성

---

## 6. Streamlit 웹 대시보드 (`app.py`) 구성

- **🗓️ [상반기 탭]**: 2026년 1~6월 월별 발행액 및 만기도래액 누적 바 차트
- **🔮 [하반기 탭]**: 2026년 7~12월 월별 만기도래 예정액 추이 및 섹터별 만기 비중 파이 차트
- **⚖️ [수급 비교 탭]**: 2026 상반기 발행액 vs 하반기 만기도래 예정액 비교 차트
- **🤖 [AI 리포트 탭]**: 2026년 하이브리드 AI(룰 베이스 / Gemini LLM) 분석 리포트

---

## 7. 실행 가이드

```powershell
# 원클릭 실행 (Windows)
run_dashboard.bat

# 파이썬 실행
python run.py
```

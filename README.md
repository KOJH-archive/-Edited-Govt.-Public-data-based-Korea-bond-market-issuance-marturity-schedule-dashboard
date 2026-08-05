# 📊 Govt. Public Data-based Korea Bond Market Issuance & Maturity Schedule Dashboard

한국예탁결제원(KSD) 채권정보서비스 공공데이터 API를 활용하여 국내 주요 채권(시중은행채, 카드채, 캐피탈채, 국고채 등)의 **2026년 상반기 발행/만기 현황 및 하반기 만기도래 예정액**을 시각화하고, AI 기반 수급 시황 분석 리포트를 제공하는 데이터 파이프라인 시스템입니다.

---

## 🌟 주요 기능 (Key Features)

1. **2026년 상반기 (1~6월) 월별 발행액 & 만기도래액 시각화**
   - 종목명 정규식 분석 기반 시중은행채, 카드채, 캐피탈채, 국고채 섹터 자동 분류
   - 월별 발행액 및 만기도래액 누적 바 차트 (Stacked Bar Chart)
   - 차트 하단 직관적 수치 확인을 위한 월별/섹터별 수치 표 및 합계(월별 합계, 총계) 제공

2. **2026년 하반기 (7~12월) 월별 만기도래 예정액 분석**
   - 하반기 차환 만기 리스크 및 수급 쏠림 현상 탐지
   - 섹터별 만기 비중 파이 차트 및 월별 추이 시각화

3. **자동화된 데이터 파이프라인 (ETL)**
   - API 제한(최대 6개월, `numOfRows=100`)을 우회하는 6개월 단위 자동 수집
   - SQLite 기반 수급 팩트 데이터 적재 (`bond_data.db`)

4. **AI 시황 분석 엔진 (Antigravity)**
   - 결제대금 변동률(±20%) 및 지방채/채권 수급 쏠림 이슈 자동 탐지 마크다운 리포트 렌더링

---

## 🚀 빠른 시작 (Quick Start)

### 1) Windows 환경 (원클릭 실행)
`run_dashboard.bat` 파일 더블 클릭!

### 2) 파이썬 실행
```bash
# 1. 가상환경 및 패키지 설치
uv venv .venv
.venv\Scripts\activate
uv pip install -r requirements.txt setuptools

# 2. API 키 설정 (Public.env 또는 .env 파일 생성)
echo API_KEY=본인의_공공데이터포털_인증키 > Public.env

# 3. 파이프라인 및 대시보드 구동
python run.py
```

---

## 📁 프로젝트 구조 (Project Structure)

```
├── .env.example              # API 키 템플릿
├── .gitignore                # 키 및 DB 유출 방지
├── config.py                 # 전역 설정 및 키 관리
├── collector.py              # 공공데이터 API 수집 엔진 (페이징 및 분할)
├── classifier.py             # 종목명 정규식 패턴 자동 분류기
├── db.py                     # SQLite 스키마 및 CRUD 쿼리
├── etl.py                    # ETL 파이프라인 (2023~2026 수집)
├── analyst.py                # AI 시황 변동 탐지 엔진
├── app.py                    # Streamlit 웹 대시보드
├── run.py                    # 파이썬 마스터 실행기
├── run_dashboard.bat         # Windows 원클릭 실행 배치 파일
└── requirements.txt          # 의존성 명세
```

---

## 📜 라이선스
MIT License

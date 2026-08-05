"""
하이브리드 섹터 자동 분류 모듈 (API 원본 유형 1차 분류 + 키워드 정규식 2차 정밀 분류)
- 1차: 공공데이터포털(금융위 API) 원본 scrsItmsKcdNm (일반회사채, 금융채, 특수채, 지방공사채, 지방채, MBS, SLBS 등)
- 2차:
  * [금융채] -> 신용카드채, 캐피탈/여전채, 특수/국책은행채, 시중은행/증권채 정밀 분류
  * [특수채/지방공사채] -> 한전/발전사채, 주택금융/LH채, 도로/가스/인프라채, 국책은행채, 기타 공공기관채/공사채 세분화
  * [일반회사채/유동화SPC채] -> 기타 회사채 (일반 기업 사채 오분류 방지)
"""
import re
from config import SECTOR_LABELS

# ── 2차 정밀 분류 정규식 패턴 ──
CARD_PATTERNS = [
    r"신한카드", r"삼성카드", r"현대카드", r"국민카드", r"KB국민카드",
    r"롯데카드", r"하나카드", r"우리카드", r"비씨카드", r"BC카드"
]

CAPITAL_PATTERNS = [
    r".*캐피탈", r".*오토리스", r".*파이낸셜", r"현대커머셜",
    r"애큐온", r"오케이파이낸셜", r"메리츠캐피탈", r"아이엠캐피탈", r"IBK캐피탈"
]

SBANK_PATTERNS = [
    r"기업은행", r"산업은행", r"농협은행", r"수협은행", r"수출입은행",
    r"중소기업은행", r"한국수출입은행",
    r"산업금융채권", r"산금채", r"산은", r"한국수출입금융", r"수은", r"농업금융채권", r"농재채",
    r"수산금융채권", r"중소기업금융", r"중기채"
]

BANK_PATTERNS = [
    r"국민은행", r"신한은행", r"하나은행", r"우리은행",
    r"^국민\d", r"^신한\d", r"^하나\d", r"^우리\d",
    r"대구은행", r"부산은행", r"경남은행", r"전북은행", r"광주은행", r"제주은행",
    r"iM뱅크", r"SC제일은행", r"스탠다드차타드", r"씨티은행",
    r"KB금융지주", r"신한금융지주", r"하나금융지주", r"우리금융지주", r"농협금융지주",
    r".*증권사", r".*투자증권", r".*금융증권", r"미래에셋증권", r"한국투자증권", r"NH투자증권",
    r"삼성증권", r"메리츠증권", r"KB증권", r"신한투자증권", r"키움증권", r"대신증권",
    r"신영증권", r"교보증권", r"유안타증권", r"현대차증권", r"한화투자증권", r"DB금융투자", r"LS증권", r"이베스트"
]

# 특수채 세분화 패턴
GOV_KEPCO_PATTERNS = [r"한국전력", r"한전", r".*발전"]
GOV_HOUSING_PATTERNS = [r"한국주택금융", r"주택금융공사", r"토지주택공사", r"^LH", r"주택도시보증", r"HUG", r"^SH", r"^GH", r"경기주택도시"]
GOV_INFRA_PATTERNS = [r"도로공사", r"가스공사", r"철도공사", r"철도공단", r"수자원", r"항만공사", r"교통공사", r"공항공사"]
GOV_TREASURY_PATTERNS = [r"^국고", r"^국민주택", r"지방채", r"예금보험", r"재정증권"]


def _match_any(patterns, text):
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


def classify_sector(bond_name, bond_type="", issuer_name=""):
    """
    하이브리드 전략 기반 섹터 분류:
    1차 API 원본 유형(bond_type) -> 2차 키워드 정밀 분류
    """
    if not bond_name and not issuer_name:
        return "OTHER", SECTOR_LABELS["OTHER"]

    text = f"{bond_name or ''} {issuer_name or ''}".strip()

    # 1. API 원본: 지방채
    if bond_type == "지방채" or _match_any(GOV_TREASURY_PATTERNS, text):
        return "GOV_TREASURY", SECTOR_LABELS["GOV_TREASURY"]

    # 2. API 원본: MBS (주택금융공사)
    if bond_type == "MBS":
        return "GOV_HOUSING", SECTOR_LABELS["GOV_HOUSING"]

    # 3. API 원본: SLBS (학자금유동화)
    if bond_type == "SLBS":
        return "GOV_POLICY", SECTOR_LABELS["GOV_POLICY"]

    # 4. API 원본: 특수채 / 지방공사채 (요청하신 세분화 적용)
    if bond_type in ["특수채", "지방공사채"]:
        if _match_any(GOV_KEPCO_PATTERNS, text):
            return "GOV_KEPCO", SECTOR_LABELS["GOV_KEPCO"]
        if _match_any(GOV_HOUSING_PATTERNS, text):
            return "GOV_HOUSING", SECTOR_LABELS["GOV_HOUSING"]
        if _match_any(GOV_INFRA_PATTERNS, text):
            return "GOV_INFRA", SECTOR_LABELS["GOV_INFRA"]
        if _match_any(SBANK_PATTERNS, text):
            return "SBANK", SECTOR_LABELS["SBANK"]
        return "GOV_POLICY", SECTOR_LABELS["GOV_POLICY"]

    # 5. API 원본: 금융채
    if bond_type == "금융채":
        if _match_any(CARD_PATTERNS, text):
            return "CARD", SECTOR_LABELS["CARD"]
        if _match_any(CAPITAL_PATTERNS, text):
            return "CAPITAL", SECTOR_LABELS["CAPITAL"]
        if _match_any(SBANK_PATTERNS, text):
            return "SBANK", SECTOR_LABELS["SBANK"]
        if _match_any(BANK_PATTERNS, text):
            return "BANK", SECTOR_LABELS["BANK"]
        return "BANK", SECTOR_LABELS["BANK"]

    # 6. API 원본: 일반회사채 / 유동화SPC채 / 기타
    # 혹시 신용카드/캐피탈/은행/국책은행 명칭이 명확히 들어간 경우에만 예외 인정
    if _match_any(CARD_PATTERNS, text):
        return "CARD", SECTOR_LABELS["CARD"]
    if _match_any(CAPITAL_PATTERNS, text):
        return "CAPITAL", SECTOR_LABELS["CAPITAL"]
    if _match_any(SBANK_PATTERNS, text):
        return "SBANK", SECTOR_LABELS["SBANK"]
    if _match_any(BANK_PATTERNS, text):
        return "BANK", SECTOR_LABELS["BANK"]
    if _match_any(GOV_KEPCO_PATTERNS, text):
        return "GOV_KEPCO", SECTOR_LABELS["GOV_KEPCO"]
    if _match_any(GOV_HOUSING_PATTERNS, text):
        return "GOV_HOUSING", SECTOR_LABELS["GOV_HOUSING"]
    if _match_any(GOV_INFRA_PATTERNS, text):
        return "GOV_INFRA", SECTOR_LABELS["GOV_INFRA"]

    return "OTHER", SECTOR_LABELS["OTHER"]


def extract_issuer_name(bond_name):
    """종목명에서 추정 기관명을 추출합니다."""
    if not bond_name:
        return "미상"

    keywords = [
        "KB국민은행", "국민은행", "신한은행", "하나은행", "우리은행", "기업은행", "산업은행", "농협은행",
        "한국주택금융공사", "한국전력공사", "한국토지주택공사", "한국도로공사", "한국가스공사", "한국철도공사",
        "신한카드", "삼성카드", "현대카드", "KB국민카드", "롯데카드", "하나카드", "우리카드",
        "현대캐피탈", "KB캐피탈", "신한캐피탈", "하나캐피탈", "우리금융캐피탈", "롯데캐피탈", "아주캐피탈",
        "국고", "국민주택", "산업금융", "수출입금융", "농업금융"
    ]
    for kw in keywords:
        if kw in bond_name:
            return kw

    match = re.match(r"^([가-힣a-zA-Z\s]+)", bond_name)
    if match:
        return match.group(1).strip()

    return bond_name[:10]

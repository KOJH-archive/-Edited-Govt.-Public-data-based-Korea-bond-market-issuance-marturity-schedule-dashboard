"""
전역 설정값 관리 모듈
- API 엔드포인트, DB 경로, 발행사 매핑 등
"""
import os

# ──────────────────────────────────────────────
# API 설정
# ──────────────────────────────────────────────
BASE_URL = "https://apis.data.go.kr/B552481/BondSvc"

def load_api_key(env_path="Public.env"):
    """환경변수 파일에서 API 키 로드. 값을 메모리에만 보관."""
    if not os.path.exists(env_path):
        raise FileNotFoundError(f"{env_path} 파일이 존재하지 않습니다.")
    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        if "=" in content:
            return content.split("=", 1)[1].strip()
        return content

# ──────────────────────────────────────────────
# DB 설정
# ──────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "bond_data.db")

# ──────────────────────────────────────────────
# 발행사 매핑 (issucoCustno → 섹터)
# issucoCustno는 예탁원 기업정보서비스에서 부여하는 고객번호.
# 아래는 대표적인 4대 시중은행 + 주요 여전사를 수동 매핑한 것.
# 실제 고객번호는 기업정보서비스 API 또는 세이브로(SEIBro)에서 확인 필요.
# ──────────────────────────────────────────────
ISSUER_MAPPING = {
    # ── 시중은행 (BANK) ──
    "00149985": {"name": "KB국민은행",     "sector": "BANK",    "rating": "AAA"},
    "00149979": {"name": "신한은행",       "sector": "BANK",    "rating": "AAA"},
    "00149980": {"name": "하나은행",       "sector": "BANK",    "rating": "AAA"},
    "00149981": {"name": "우리은행",       "sector": "BANK",    "rating": "AAA"},
    # ── 특수은행 (SBANK) ──
    "00149987": {"name": "한국산업은행",   "sector": "SBANK",   "rating": "AAA"},
    "00206422": {"name": "IBK기업은행",    "sector": "SBANK",   "rating": "AAA"},
    "00149990": {"name": "NH농협은행",     "sector": "SBANK",   "rating": "AAA"},
    # ── 신용카드 (CARD) ──
    "00252876": {"name": "삼성카드",       "sector": "CARD",    "rating": "AA+"},
    "00252877": {"name": "현대카드",       "sector": "CARD",    "rating": "AA+"},
    "00252873": {"name": "신한카드",       "sector": "CARD",    "rating": "AA+"},
    "00252874": {"name": "KB국민카드",     "sector": "CARD",    "rating": "AA+"},
    "00252875": {"name": "하나카드",       "sector": "CARD",    "rating": "AA"},
    "00252878": {"name": "우리카드",       "sector": "CARD",    "rating": "AA"},
    # ── 캐피탈 (CAPITAL) ──
    "00253112": {"name": "현대캐피탈",     "sector": "CAPITAL", "rating": "AA+"},
    "00253113": {"name": "KB캐피탈",       "sector": "CAPITAL", "rating": "AA"},
    "00253114": {"name": "신한캐피탈",     "sector": "CAPITAL", "rating": "AA-"},
    "00253115": {"name": "하나캐피탈",     "sector": "CAPITAL", "rating": "AA-"},
    # ── 정부/공공 (GOV) ──
    "00000001": {"name": "대한민국(국고채)", "sector": "GOV",   "rating": "AAA"},
}

# 섹터 코드 → 한글 라벨 (주요 발행 주체 세분화)
SECTOR_LABELS = {
    "GOV_TREASURY": "국고/지방채",
    "GOV_HOUSING":  "주택금융/LH채",
    "GOV_KEPCO":    "한전/발전사채",
    "GOV_INFRA":    "도로/가스/인프라채",
    "GOV_POLICY":   "기타 공공기관채",
    "BANK":         "시중은행/증권채",
    "SBANK":        "특수/국책은행채",
    "CARD":         "신용카드채",
    "CAPITAL":      "캐피탈/여전채",
    "OTHER":        "기타 회사채",
}


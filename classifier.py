"""
종목명(korSecnNm) 기반 섹터 자동 분류 모듈
- 정규식(Regex) 패턴 매핑으로 API 번호(issucoCustno) 상이 문제 완전 해결
- 4대 시중은행, 특수은행, 카드사, 캐피탈사, 국고채/공공채 등 분류
"""
import re

# ──────────────────────────────────────────────
# 정규식 패턴 정의 (우선순위 순서대로 평가)
# ──────────────────────────────────────────────
SECTOR_RULES = [
    # 1. 국고채 / 정부 / 공공 (GOV)
    {
        "code": "GOV",
        "label": "국고채/공공채",
        "patterns": [
            r"^국고", r"^국민주택", r"지방채", r"한국전력", r"LH", r"도로공사",
            r"수자원", r"철도공사", r"가스공사", r"예금보험", r"자산관리",
            r"주택도시보증", r"한국주택금융", r"보증기금"
        ]
    },
    # 2. 4대 시중은행 및 지방은행 (BANK)
    {
        "code": "BANK",
        "label": "시중은행채",
        "patterns": [
            r"국민은행", r"신한은행", r"하나은행", r"우리은행",
            r"^국민\d", r"^신한\d", r"^하나\d", r"^우리\d",  # 축약형 (예: 우리30-07-...)
            r"대구은행", r"부산은행", r"경남은행", r"전북은행", r"광주은행", r"제주은행",
            r"iM뱅크", r"SC제일은행", r"씨티은행"
        ]
    },
    # 3. 특수/국책은행 (SBANK)
    {
        "code": "SBANK",
        "label": "특수은행채",
        "patterns": [
            r"기업은행", r"산업은행", r"농협은행", r"수협은행", r"수출입은행",
            r"중소기업은행", r"한국수출입은행"
        ]
    },
    # 4. 신용카드사 (CARD)
    {
        "code": "CARD",
        "label": "신용카드채",
        "patterns": [
            r"신한카드", r"삼성카드", r"현대카드", r"국민카드", r"KB국민카드",
            r"롯데카드", r"하나카드", r"우리카드", r"비씨카드", r"BC카드"
        ]
    },
    # 5. 캐피탈 / 리스 / 파이낸셜 (CAPITAL)
    {
        "code": "CAPITAL",
        "label": "캐피탈채",
        "patterns": [
            r".*캐피탈", r".*오토리스", r".*파이낸셜", r"현대커머셜",
            r"애큐온", r"오케이파이낸셜", r"메리츠캐피탈"
        ]
    },
]


def classify_sector(bond_name):
    """
    채권 종목명(korSecnNm)을 입력받아 섹터 코드와 한글 라벨을 반환합니다.
    
    Returns:
        tuple: (sector_code, sector_label)
    """
    if not bond_name:
        return "OTHER", "기타 회사채"

    # 정규식 패턴 순차 검사
    for rule in SECTOR_RULES:
        for pattern in rule["patterns"]:
            if re.search(pattern, bond_name, re.IGNORECASE):
                return rule["code"], rule["label"]

    return "OTHER", "기타 회사채"


def extract_issuer_name(bond_name):
    """
    종목명에서 추정 기관명을 추출합니다.
    예: 'KB국민은행24-01-보-01' -> 'KB국민은행'
    """
    if not bond_name:
        return "미상"

    # 주요 기관명 패턴 매칭
    keywords = [
        "KB국민은행", "국민은행", "신한은행", "하나은행", "우리은행", "기업은행", "산업은행", "농협은행",
        "신한카드", "삼성카드", "현대카드", "KB국민카드", "롯데카드", "하나카드", "우리카드",
        "현대캐피탈", "KB캐피탈", "신한캐피탈", "하나캐피탈", "우리금융캐피탈", "롯데캐피탈", "아주캐피탈",
        "국고", "국민주택"
    ]
    for kw in keywords:
        if kw in bond_name:
            return kw

    # 숫자가 시작하기 전까지의 텍스트 추출 시도
    match = re.match(r"^([가-힣a-zA-Z\s]+)", bond_name)
    if match:
        return match.group(1).strip()

    return bond_name[:10]


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    test_samples = [
        "KB국민은행24-01-보-01",
        "신한은행30-07-하-1.25-A",
        "우리30-07-이-01-상-30",
        "신한카드3501(사)",
        "삼성카드2190",
        "현대캐피탈1920-2",
        "KB캐피탈310",
        "국고03250-5406",
        "국민주택채권1종24-05",
        "기업은행2401이1Y",
        "삼성전자105호회사채",
    ]

    print("=" * 70)
    print("종목명 기반 섹터 자동 분류 테스트")
    print("=" * 70)
    for sample in test_samples:
        code, label = classify_sector(sample)
        issuer = extract_issuer_name(sample)
        print(f"[{code:7s} | {label:8s}] {sample:30s} -> 추출기관: {issuer}")

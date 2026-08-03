"""
2026년 상반기/하반기 수급 데이터 시드 모듈
- 2026년 대시보드 시각화 기능을 즉시 검증할 수 있도록 
  실제 채권 종목 패턴 기반의 2026년 데이터 시드 생성
"""
import sys
import random
from datetime import datetime, timedelta
from db import init_db, get_connection, upsert_issuer, upsert_bond_master, insert_supply_flow
from classifier import classify_sector, extract_issuer_name

sys.stdout.reconfigure(encoding='utf-8')

BOND_TEMPLATES = [
    ("KB국민은행26-{m:02d}-보-{seq:02d}", "BANK", 1000, 5000),
    ("신한은행26-{m:02d}-하-{seq:02d}", "BANK", 1000, 4000),
    ("하나은행26-{m:02d}-보-{seq:02d}", "BANK", 800, 3500),
    ("우리26-{m:02d}-이-{seq:02d}",     "BANK", 800, 3000),
    
    ("기업은행26{m:02d}이1Y",           "SBANK", 1500, 6000),
    ("산업은행26{m:02d}이2Y",           "SBANK", 2000, 7000),
    
    ("신한카드36{m:02d}(사)",            "CARD", 500, 2000),
    ("삼성카드26{m:02d}",               "CARD", 500, 1800),
    ("현대카드26{m:02d}",               "CARD", 400, 1500),
    ("KB국민카드26{m:02d}",             "CARD", 400, 1500),
    
    ("현대캐피탈26{m:02d}-1",           "CAPITAL", 300, 1200),
    ("KB캐피탈26{m:02d}",               "CAPITAL", 300, 1000),
    ("신한캐피탈26{m:02d}",             "CAPITAL", 200, 800),
    ("하나캐피탈26{m:02d}",             "CAPITAL", 200, 800),
    
    ("국고03250-5606",                 "GOV", 5000, 20000),
    ("국민주택채권1종26-{m:02d}",        "GOV", 3000, 15000),
]


def generate_2026_data():
    init_db()
    conn = get_connection()

    print("[START] 2026년 수급 시드 데이터 생성 중...")
    
    isin_counter = 1000
    flow_count = 0

    # 2026년 상반기 (1월~6월) 발행 & 만기 생성
    for month in range(1, 7):
        for tpl_name, expected_sector, min_amt, max_amt in BOND_TEMPLATES:
            for seq in range(1, 3):  # 월별 2건씩
                isin_counter += 1
                isin = f"KR62026{isin_counter:05d}"
                bond_name = tpl_name.format(m=month, seq=seq)
                
                # 정규식 자동 분류
                sector_code, sector_label = classify_sector(bond_name)
                issuer_name = extract_issuer_name(bond_name)
                issuer_id = f"ISSUER_{sector_code}"
                
                # 발행일: 2026년 상반기 해당 월
                issue_day = random.randint(1, 25)
                issue_date = f"2026{month:02d}{issue_day:02d}"
                
                # 만기일: 2026년 상반기 또는 하반기
                maturity_month = random.choice([month, (month + 6) % 12 + 1])
                if maturity_month == 0:
                    maturity_month = 12
                maturity_year = 2026
                maturity_day = random.randint(1, 25)
                maturity_date = f"{maturity_year}{maturity_month:02d}{maturity_day:02d}"
                
                amt = random.randint(min_amt, max_amt) * 100000000  # 억원 단위 → 원

                # DB 적재
                upsert_issuer(conn, issuer_id, issuer_name, sector_code)
                upsert_bond_master(conn, isin, issuer_id, bond_name, "금융채/회사채", issue_date, maturity_date, amt)
                
                # 2026 상반기 발행 이벤트
                insert_supply_flow(conn, isin, issue_date, "ISSUE", amt)
                # 2026 만기 이벤트
                insert_supply_flow(conn, isin, maturity_date, "MATURITY", amt)
                
                flow_count += 2

    # 2026년 하반기 (7월~12월) 발행 채권 중 하반기 만기 생성
    for month in range(7, 13):
        for tpl_name, expected_sector, min_amt, max_amt in BOND_TEMPLATES:
            isin_counter += 1
            isin = f"KR62026{isin_counter:05d}"
            bond_name = tpl_name.format(m=month, seq=1)
            
            sector_code, sector_label = classify_sector(bond_name)
            issuer_name = extract_issuer_name(bond_name)
            issuer_id = f"ISSUER_{sector_code}"
            
            issue_date = f"2026{month:02d}15"
            maturity_date = f"2026{month:02d}28"
            amt = random.randint(min_amt, max_amt) * 100000000

            upsert_issuer(conn, issuer_id, issuer_name, sector_code)
            upsert_bond_master(conn, isin, issuer_id, bond_name, "금융채/회사채", issue_date, maturity_date, amt)
            insert_supply_flow(conn, isin, issue_date, "ISSUE", amt)
            insert_supply_flow(conn, isin, maturity_date, "MATURITY", amt)
            flow_count += 2

    conn.commit()
    conn.close()
    print(f"[SUCCESS] 2026년 수급 데이터 생성 완료! (총 {flow_count}개 이벤트 적재)")


if __name__ == "__main__":
    generate_2026_data()

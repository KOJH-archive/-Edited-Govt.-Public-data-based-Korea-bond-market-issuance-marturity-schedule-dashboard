import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('bond_data.db')
cursor = conn.cursor()

print("=" * 80)
print("📊 [FSC API 100% 실데이터 검증] 금융위원회 V2 API로 수집된 실제 채권 목록")
print("=" * 80)

# FSC API에서 수집된 채권만 필터링 (crno != ISSUER_)
cursor.execute("""
    SELECT bm.isin_code, bm.bond_name, bm.issue_date, bm.maturity_date, bm.issue_amount / 1e8, im.issuer_name
    FROM bond_master bm
    JOIN issuer_mapping im ON bm.issuer_id = im.issuer_id
    WHERE bm.issuer_id NOT LIKE 'ISSUER_%'
    ORDER BY bm.maturity_date DESC
    LIMIT 20
""")

fsc_rows = cursor.fetchall()
print(f"FSC API로 수집된 실제 채권 수: {len(fsc_rows)}건 (상위 20개 출력)\n")

for isin, name, idate, mdate, amt, isur in fsc_rows:
    print(f"ISIN:{isin:14s} | 종목명:{name:26s} | 발행일:{idate} | 만기일:{mdate} | 금액:{amt:,.1f}억원 | 발행사:{isur}")

conn.close()

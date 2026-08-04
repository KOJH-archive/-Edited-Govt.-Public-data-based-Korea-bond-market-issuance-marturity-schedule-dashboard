import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('bond_data.db')
cursor = conn.cursor()

print("=" * 80)
print("📊 DB 내 섹터별 레코드 분포 현황")
print("=" * 80)

cursor.execute("""
    SELECT im.sector_code, COUNT(*), SUM(bm.issue_amount)/1e8
    FROM bond_master bm
    JOIN issuer_mapping im ON bm.issuer_id = im.issuer_id
    GROUP BY im.sector_code
    ORDER BY COUNT(*) DESC
""")

for sector, cnt, total in cursor.fetchall():
    print(f"  섹터: {sector:10s} | 종목 수: {cnt:>4d}건 | 총 발행금액: {total:,.1f} 억원")

print("\n[기타(OTHER)로 분류된 주요 채권 종목 30개 샘플]")
print("-" * 80)
cursor.execute("""
    SELECT bm.bond_name, bm.bond_type, im.issuer_name
    FROM bond_master bm
    JOIN issuer_mapping im ON bm.issuer_id = im.issuer_id
    WHERE im.sector_code = 'OTHER'
    LIMIT 30
""")

for name, btype, isur in cursor.fetchall():
    print(f"  종목명: {name:32s} | 채권종류: {btype:12s} | 발행사: {isur}")

conn.close()

"""
DB 내 수집된 채권의 최소/최상 발행년도 및 만기년도 분포 확인
"""
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('bond_data.db')
cursor = conn.cursor()

print("=" * 80)
print("📊 [DB 수집 데이터 연도 분포 검증]")
print("=" * 80)

# 1. 발행연도 분포
cursor.execute("""
    SELECT SUBSTR(issue_date, 1, 4) AS yyyy, COUNT(*), SUM(issue_amount)/1e8
    FROM bond_master
    WHERE issue_date != ''
    GROUP BY yyyy
    ORDER BY yyyy
""")
print("\n[발행연도별 채권 종목 수 및 금액(억원)]")
for y, cnt, total in cursor.fetchall():
    print(f"  발행연도 {y}년: {cnt:>4d}건 | 총 {total:,.0f} 억원")

# 2. 만기연도 분포
cursor.execute("""
    SELECT SUBSTR(maturity_date, 1, 4) AS yyyy, COUNT(*), SUM(issue_amount)/1e8
    FROM bond_master
    WHERE maturity_date != ''
    GROUP BY yyyy
    ORDER BY yyyy
""")
print("\n[만기연도별 채권 종목 수 및 금액(억원)]")
for y, cnt, total in cursor.fetchall():
    print(f"  만기연도 {y}년: {cnt:>4d}건 | 총 {total:,.0f} 억원")

# 3. 최소/최대 발행일자 및 만기일자
cursor.execute("SELECT MIN(issue_date), MAX(issue_date), MIN(maturity_date), MAX(maturity_date) FROM bond_master WHERE issue_date != ''")
min_iss, max_iss, min_mat, max_mat = cursor.fetchone()
print(f"\n최초 발행일자: {min_iss} ~ 최근 발행일자: {max_iss}")
print(f"최초 만기일자: {min_mat} ~ 최장 만기일자: {max_mat}")

conn.close()

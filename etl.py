"""
ETL 파이프라인 모듈 (수정판 - 2026년 최신 데이터 포함)
- 2023년 ~ 2026년 데이터 수집
- 6개월 단위 분할 수집 적용
"""
from config import load_api_key
from classifier import classify_sector, extract_issuer_name
from collector import (
    fetch_bond_kind_insetl_stat,
    fetch_local_gov_issu_stat,
    fetch_issuer_bond_details,
)
from db import (
    init_db, get_connection,
    upsert_issuer, upsert_bond_master, insert_supply_flow,
    upsert_settlement_stat, upsert_local_gov_stat,
    query_table_counts,
)


def etl_settlement_stat(api_key, conn, year):
    """6개월 단위 분할 수집 (상반기, 하반기)."""
    periods = [
        (f"{year}0101", f"{year}0630"),
        (f"{year}0701", f"{year}1231")
    ]
    count = 0
    for begin, expiry in periods:
        try:
            print(f"  [ETL] 기관결제대금 현황 ({begin} ~ {expiry})")
            data = fetch_bond_kind_insetl_stat(api_key, begin, expiry)
            for row in data:
                upsert_settlement_stat(
                    conn,
                    std_yymm=row.get("stdYymm", ""),
                    bond=int(row.get("bondSetlCost", 0) or 0),
                    cd=int(row.get("cdSetlCost", 0) or 0),
                    cp=int(row.get("cpSetlCost", 0) or 0),
                    stb=int(row.get("stbSetlCost", 0) or 0),
                )
                count += 1
        except Exception as e:
            print(f"    ⚠️ 실패 ({begin}~{expiry}): {e}")
    conn.commit()
    return count


def etl_local_gov_stat(api_key, conn, year):
    """6개월 단위 분할 수집."""
    periods = [
        (f"{year}01", f"{year}06"),
        (f"{year}07", f"{year}12")
    ]
    count = 0
    for begin, expiry in periods:
        try:
            print(f"  [ETL] 지방채 현황 ({begin} ~ {expiry})")
            data = fetch_local_gov_issu_stat(api_key, begin, expiry)
            for row in data:
                upsert_local_gov_stat(
                    conn,
                    std_yymm=row.get("stdYymm", ""),
                    train_red=int(row.get("trainBondRed", 0) or 0),
                    train_new=int(row.get("tratinBondNewnIssu", 0) or 0),
                    rd_red=int(row.get("rdBondRed", 0) or 0),
                    rd_new=int(row.get("rdBondNewnIssu", 0) or 0),
                    gen_red=int(row.get("genLocPpbdRed", 0) or 0),
                    gen_new=int(row.get("genLocPpbdNewnIssu", 0) or 0),
                )
                count += 1
        except Exception as e:
            print(f"    ⚠️ 실패 ({begin}~{expiry}): {e}")
    conn.commit()
    return count


def etl_issuer_bonds(api_key, conn, issuco_custno):
    """발행인별 채권발행내역 수집."""
    print(f"\n[ETL] 발행인 채권내역 (custno={issuco_custno})")
    data = fetch_issuer_bond_details(api_key, issuco_custno)
    bond_count = 0
    flow_count = 0
    for row in data:
        isin = row.get("isin", "")
        bond_name = row.get("korSecnNm", "")
        if not isin or not bond_name:
            continue

        sector_code, sector_label = classify_sector(bond_name)
        issuer_name = extract_issuer_name(bond_name)

        upsert_issuer(conn, issuer_id=str(issuco_custno), name=issuer_name, sector=sector_code)
        upsert_bond_master(
            conn,
            isin=isin,
            issuer_id=str(issuco_custno),
            name=bond_name,
            bond_type=row.get("secnKacd", ""),
            issue_date=row.get("issuDt", ""),
            maturity_date=row.get("redDt", ""),
            issue_amount=int(row.get("firstIssuAmt", 0) or 0),
            currency=row.get("issuCurCd", "KRW"),
        )
        bond_count += 1

        issue_date = row.get("issuDt", "")
        issue_amt = int(row.get("firstIssuAmt", 0) or 0)
        if issue_date and issue_amt > 0:
            insert_supply_flow(conn, isin, issue_date, "ISSUE", issue_amt)
            flow_count += 1

        red_date = row.get("redDt", "")
        payin_amt = int(row.get("payinAmt", 0) or 0)
        if red_date and payin_amt > 0:
            insert_supply_flow(conn, isin, red_date, "MATURITY", payin_amt)
            flow_count += 1

    conn.commit()
    print(f"  bond_master: {bond_count}건, supply_flow: {flow_count}건")
    return bond_count, flow_count


def run_full_etl():
    """전체 ETL 파이프라인 실행 (2023년 ~ 2026년)."""
    api_key = load_api_key()
    init_db()
    conn = get_connection()

    # 2023년 ~ 2026년 최신 데이터 수집
    target_years = [2023, 2024, 2025, 2026]

    print("\n--- 1. 기관결제대금 현황 수집 ---")
    for year in target_years:
        etl_settlement_stat(api_key, conn, year)

    print("\n--- 2. 지방채 현황 수집 ---")
    for year in target_years:
        etl_local_gov_stat(api_key, conn, year)

    print("\n--- 3. 주요 발행인 채권 내역 수집 ---")
    for custno in [1, 3]:
        try:
            etl_issuer_bonds(api_key, conn, custno)
        except Exception as e:
            print(f"  건너뜀 (custno={custno}): {e}")

    print("\n" + "=" * 60)
    print("[ETL 완료] 테이블별 레코드 수:")
    counts = query_table_counts(conn)
    for table, cnt in counts.items():
        print(f"  {table}: {cnt}건")

    conn.close()


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    run_full_etl()

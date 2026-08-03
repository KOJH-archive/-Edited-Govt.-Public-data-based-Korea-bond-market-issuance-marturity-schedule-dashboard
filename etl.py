"""
ETL 파이프라인 모듈 (금융위원회 V2 API 100% 실데이터 수집 적용)
- KSD API: 기관결제대금, 지방채 통계 수집
- FSC V2 API (10,000회 한도): 대한민국 개별 채권 종목별 발행일, 만기일, 발행금액 100% 수집
- 2026년 상반기 및 하반기(7~12월) 실제 만기 채권 포함
"""
from config import load_api_key
from classifier import classify_sector, extract_issuer_name
from collector import (
    fetch_bond_kind_insetl_stat,
    fetch_local_gov_issu_stat,
    fetch_fsc_bond_items,
)
from db import (
    init_db, get_connection,
    upsert_issuer, upsert_bond_master, insert_supply_flow,
    upsert_settlement_stat, upsert_local_gov_stat,
    query_table_counts,
)


def etl_settlement_stat(api_key, conn, year):
    """기관결제대금 현황 수집."""
    periods = [(f"{year}0101", f"{year}0630"), (f"{year}0701", f"{year}1231")]
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
    """지방채 현황 수집."""
    periods = [(f"{year}01", f"{year}06"), (f"{year}07", f"{year}12")]
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


def etl_fsc_real_bonds(api_key, conn, sample_dates):
    """
    금융위원회 V2 API에서 개별 채권 실데이터 수집.
    100% 실존하는 채권의 종목명, 발행일, 만기일, 발행금액 적재.
    """
    print("\n--- 3. 금융위원회 V2 API 개별 채권 실데이터 수집 ---")
    total_bonds = 0
    total_flows = 0

    for bas_dt in sample_dates:
        items = fetch_fsc_bond_items(api_key, bas_dt=bas_dt, rows_per_page=100)
        print(f"  [FSC API] 기준일자:{bas_dt} -> {len(items)}건 수신")
        
        for item in items:
            isin = item.get("isinCd", "")
            bond_name = item.get("isinCdNm", "") or item.get("bondIsurNm", "")
            if not isin or not bond_name:
                continue

            # ── 정규식 자동 섹터 분류 ──
            sector_code, sector_label = classify_sector(bond_name)
            issuer_name = item.get("bondIsurNm", "") or extract_issuer_name(bond_name)
            issuer_id = item.get("crno", "UNKNOWN")

            # 1. issuer_mapping 적재
            upsert_issuer(conn, issuer_id=issuer_id, name=issuer_name, sector=sector_code)

            # 2. bond_master 적재
            issue_date = item.get("bondIssuDt", "")
            maturity_date = item.get("bondExprDt", "")
            issue_amt = int(item.get("bondIssuAmt", 0) or 0)

            upsert_bond_master(
                conn,
                isin=isin,
                issuer_id=issuer_id,
                name=bond_name,
                bond_type=item.get("scrsItmsKcdNm", "채권"),
                issue_date=issue_date,
                maturity_date=maturity_date,
                issue_amount=issue_amt,
                currency=item.get("bondIssuCurCd", "KRW"),
            )
            total_bonds += 1

            # 3. bond_supply_flow 적재 (발행 이벤트)
            if issue_date and issue_amt > 0:
                insert_supply_flow(conn, isin, issue_date, "ISSUE", issue_amt)
                total_flows += 1

            # 4. bond_supply_flow 적재 (만기 이벤트)
            if maturity_date and issue_amt > 0:
                insert_supply_flow(conn, isin, maturity_date, "MATURITY", issue_amt)
                total_flows += 1

    conn.commit()
    print(f"  ✅ 개별 채권 실데이터 적재 완료 (종목:{total_bonds}건, 수급이벤트:{total_flows}건)")
    return total_bonds, total_flows


def run_full_etl():
    """전체 ETL 파이프라인 실행."""
    api_key = load_api_key()
    init_db()
    conn = get_connection()

    target_years = [2023, 2024, 2025, 2026]

    # 1. 기관결제대금 현황 (KSD API)
    print("\n--- 1. 기관결제대금 현황 수집 ---")
    for year in target_years:
        etl_settlement_stat(api_key, conn, year)

    # 2. 지방채 현황 (KSD API)
    print("\n--- 2. 지방채 현황 수집 ---")
    for year in target_years:
        etl_local_gov_stat(api_key, conn, year)

    # 3. 금융위원회 V2 API (10,000회 트래픽) 기반 개별 채권 100% 실데이터 수집
    # 2024, 2025, 2026 전체 월별 대표 샘플 날짜 스캔 (2026 H2 포함)
    sample_dates = [
        # 2024년
        "20240115", "20240415", "20240715", "20241015",
        # 2025년 (1월~12월)
        "20250115", "20250215", "20250315", "20250415", "20250515", "20250615",
        "20250715", "20250815", "20250915", "20251015", "20251115", "20251215",
        # 2026년 (상반기 + 하반기)
        "20260115", "20260215", "20260315", "20260415", "20260515", "20260615",
        "20260715", "20260815", "20260915", "20261015", "20261115", "20261215"
    ]
    etl_fsc_real_bonds(api_key, conn, sample_dates)

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

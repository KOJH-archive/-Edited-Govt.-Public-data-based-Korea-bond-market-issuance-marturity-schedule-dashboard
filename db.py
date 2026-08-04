"""
SQLite 데이터베이스 모듈
- 테이블 생성 (3개)
- CRUD 함수
- 분석용 JOIN 쿼리
"""
import sqlite3
from config import DB_PATH


# ──────────────────────────────────────────────
# 스키마 정의
# ──────────────────────────────────────────────
SCHEMA_SQL = """
-- 발행인 매핑 마스터
CREATE TABLE IF NOT EXISTS issuer_mapping (
    issuer_id     TEXT PRIMARY KEY,   -- issucoCustno
    issuer_name   TEXT NOT NULL,
    sector_code   TEXT NOT NULL,      -- BANK, CARD, CAPITAL, GOV ...
    credit_rating TEXT,
    last_updated  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 채권 종목 마스터
CREATE TABLE IF NOT EXISTS bond_master (
    isin_code       TEXT PRIMARY KEY,
    issuer_id       TEXT,
    bond_name       TEXT,
    bond_type       TEXT,              -- secnKacd (국채, 사채 등)
    issue_date      TEXT,              -- YYYYMMDD
    maturity_date   TEXT,              -- YYYYMMDD
    coupon_rate     REAL,
    issue_amount    INTEGER,           -- 발행금액 (원)
    currency        TEXT DEFAULT 'KRW',
    FOREIGN KEY (issuer_id) REFERENCES issuer_mapping(issuer_id)
);

-- 발행/만기 수급 팩트 테이블
CREATE TABLE IF NOT EXISTS bond_supply_flow (
    record_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    isin_code   TEXT,
    event_date  TEXT NOT NULL,          -- YYYYMMDD
    event_type  TEXT NOT NULL,          -- 'ISSUE' or 'MATURITY'
    amount      INTEGER NOT NULL,       -- 금액 (원)
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (isin_code) REFERENCES bond_master(isin_code)
);

-- 채권 종류별 기관결제대금 현황 (집계 테이블)
CREATE TABLE IF NOT EXISTS bond_settlement_stat (
    std_yymm        TEXT PRIMARY KEY,   -- YYYYMM
    bond_setl_cost  INTEGER,            -- 채권결제대금
    cd_setl_cost    INTEGER,            -- CD결제대금
    cp_setl_cost    INTEGER,            -- CP결제대금
    stb_setl_cost   INTEGER,            -- 단기사채결제대금
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 지방채 발행/상환 현황 (집계 테이블)
CREATE TABLE IF NOT EXISTS local_gov_bond_stat (
    std_yymm              TEXT PRIMARY KEY,
    train_bond_red        INTEGER,        -- 도시철도채 상환
    train_bond_new_issu   INTEGER,        -- 도시철도채 신규발행
    rd_bond_red           INTEGER,        -- 지역개발채 상환
    rd_bond_new_issu      INTEGER,        -- 지역개발채 신규발행
    gen_loc_bond_red      INTEGER,        -- 일반지방채 상환
    gen_loc_bond_new_issu INTEGER,        -- 일반지방채 신규발행
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ETL 수집 메타데이터 (증분 수집 워터마크 관리)
CREATE TABLE IF NOT EXISTS etl_metadata (
    meta_key    TEXT PRIMARY KEY,
    meta_val    TEXT NOT NULL,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 중복 방지 인덱스
CREATE UNIQUE INDEX IF NOT EXISTS idx_supply_flow_unique
    ON bond_supply_flow (isin_code, event_date, event_type);
"""



def get_connection(db_path=None):
    """SQLite 연결 반환."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")  # 동시 읽기 성능 향상
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row  # dict-like 접근
    return conn


def init_db(db_path=None):
    """테이블 생성 (idempotent)."""
    conn = get_connection(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    print(f"DB 초기화 완료: {db_path or DB_PATH}")


# ──────────────────────────────────────────────
# INSERT / UPSERT 함수
# ──────────────────────────────────────────────
def upsert_issuer(conn, issuer_id, name, sector, rating=None):
    """발행인 매핑 UPSERT. 유효한 섹터 분류가 존재하는 경우 OTHER로 덮어쓰지 않음."""
    conn.execute("""
        INSERT INTO issuer_mapping (issuer_id, issuer_name, sector_code, credit_rating)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(issuer_id) DO UPDATE SET
            issuer_name=CASE WHEN excluded.issuer_name != '' THEN excluded.issuer_name ELSE issuer_mapping.issuer_name END,
            sector_code=CASE WHEN excluded.sector_code != 'OTHER' THEN excluded.sector_code ELSE issuer_mapping.sector_code END,
            credit_rating=COALESCE(excluded.credit_rating, issuer_mapping.credit_rating),
            last_updated=CURRENT_TIMESTAMP
    """, (str(issuer_id), name, sector, rating))


def upsert_bond_master(conn, isin, issuer_id, name, bond_type,
                       issue_date, maturity_date, issue_amount, currency="KRW"):
    """채권 마스터 UPSERT."""
    conn.execute("""
        INSERT INTO bond_master (isin_code, issuer_id, bond_name, bond_type,
                                 issue_date, maturity_date, issue_amount, currency)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(isin_code) DO UPDATE SET
            issuer_id=excluded.issuer_id,
            bond_name=excluded.bond_name,
            bond_type=excluded.bond_type,
            issue_date=excluded.issue_date,
            maturity_date=excluded.maturity_date,
            issue_amount=excluded.issue_amount,
            currency=excluded.currency
    """, (isin, str(issuer_id), name, bond_type,
          issue_date, maturity_date, issue_amount, currency))


def insert_supply_flow(conn, isin, event_date, event_type, amount):
    """수급 팩트 INSERT (중복 무시)."""
    conn.execute("""
        INSERT OR IGNORE INTO bond_supply_flow (isin_code, event_date, event_type, amount)
        VALUES (?, ?, ?, ?)
    """, (isin, event_date, event_type, amount))


def upsert_settlement_stat(conn, std_yymm, bond, cd, cp, stb):
    """기관결제대금 통계 UPSERT."""
    conn.execute("""
        INSERT INTO bond_settlement_stat (std_yymm, bond_setl_cost, cd_setl_cost,
                                          cp_setl_cost, stb_setl_cost)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(std_yymm) DO UPDATE SET
            bond_setl_cost=excluded.bond_setl_cost,
            cd_setl_cost=excluded.cd_setl_cost,
            cp_setl_cost=excluded.cp_setl_cost,
            stb_setl_cost=excluded.stb_setl_cost,
            created_at=CURRENT_TIMESTAMP
    """, (std_yymm, bond, cd, cp, stb))


def upsert_local_gov_stat(conn, std_yymm, train_red, train_new,
                           rd_red, rd_new, gen_red, gen_new):
    """지방채 통계 UPSERT."""
    conn.execute("""
        INSERT INTO local_gov_bond_stat (std_yymm, train_bond_red, train_bond_new_issu,
                                         rd_bond_red, rd_bond_new_issu,
                                         gen_loc_bond_red, gen_loc_bond_new_issu)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(std_yymm) DO UPDATE SET
            train_bond_red=excluded.train_bond_red,
            train_bond_new_issu=excluded.train_bond_new_issu,
            rd_bond_red=excluded.rd_bond_red,
            rd_bond_new_issu=excluded.rd_bond_new_issu,
            gen_loc_bond_red=excluded.gen_loc_bond_red,
            gen_loc_bond_new_issu=excluded.gen_loc_bond_new_issu,
            created_at=CURRENT_TIMESTAMP
    """, (std_yymm, train_red, train_new, rd_red, rd_new, gen_red, gen_new))


def get_meta_value(conn, key):
    """ETL 수집 메타데이터(마지막 완료일자 등) 조회."""
    row = conn.execute("SELECT meta_val FROM etl_metadata WHERE meta_key = ?", (key,)).fetchone()
    return row[0] if row else None


def set_meta_value(conn, key, val):
    """ETL 수집 메타데이터 저장/갱신."""
    conn.execute("""
        INSERT INTO etl_metadata (meta_key, meta_val, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(meta_key) DO UPDATE SET
            meta_val = excluded.meta_val,
            updated_at = CURRENT_TIMESTAMP
    """, (key, str(val)))



# ──────────────────────────────────────────────
# 분석용 쿼리 함수
# ──────────────────────────────────────────────
def query_supply_by_sector_half(conn, year):
    """
    특정 연도의 섹터별 상반기 발행 vs 하반기 만기 금액 집계.
    bond_supply_flow + bond_master + issuer_mapping JOIN.
    """
    sql = """
    SELECT
        COALESCE(im.sector_code, 'OTHER') AS sector,
        sf.event_type,
        CASE
            WHEN CAST(SUBSTR(sf.event_date, 5, 2) AS INTEGER) <= 6 THEN 'H1'
            ELSE 'H2'
        END AS half_year,
        SUM(sf.amount) AS total_amount
    FROM bond_supply_flow sf
    LEFT JOIN bond_master bm ON sf.isin_code = bm.isin_code
    LEFT JOIN issuer_mapping im ON bm.issuer_id = im.issuer_id
    WHERE sf.event_date LIKE ? || '%'
    GROUP BY sector, sf.event_type, half_year
    ORDER BY sector, half_year, sf.event_type
    """
    return conn.execute(sql, (str(year),)).fetchall()


def query_monthly_maturity(conn, year):
    """특정 연도의 월별 만기 금액 집계 (히트맵용)."""
    sql = """
    SELECT
        COALESCE(im.sector_code, 'OTHER') AS sector,
        SUBSTR(sf.event_date, 1, 6) AS yyyymm,
        SUM(sf.amount) AS total_amount
    FROM bond_supply_flow sf
    LEFT JOIN bond_master bm ON sf.isin_code = bm.isin_code
    LEFT JOIN issuer_mapping im ON bm.issuer_id = im.issuer_id
    WHERE sf.event_type = 'MATURITY'
      AND sf.event_date LIKE ? || '%'
    GROUP BY sector, yyyymm
    ORDER BY yyyymm, sector
    """
    return conn.execute(sql, (str(year),)).fetchall()


def query_settlement_trend(conn):
    """기관결제대금 현황 전체 조회 (시계열 차트용)."""
    sql = """
    SELECT std_yymm, bond_setl_cost, cd_setl_cost, cp_setl_cost, stb_setl_cost
    FROM bond_settlement_stat
    ORDER BY std_yymm
    """
    return conn.execute(sql).fetchall()


def query_2026_matured_bonds_to_date(conn, end_date="20261231"):
    """
    2026년 1월 ~ 현재(end_date)까지 만기도래한 채권 데이터 조회 (정규식 분류 섹터 적용).
    """
    sql = """
    SELECT
        bm.isin_code,
        bm.bond_name,
        COALESCE(im.sector_code, 'OTHER') AS sector_code,
        bm.issue_date,
        bm.maturity_date,
        SUBSTR(bm.maturity_date, 1, 6) AS yyyymm,
        SUBSTR(bm.maturity_date, 5, 2) AS month_str,
        bm.issue_amount AS issue_amount_raw,    -- 원(KRW) 단위 raw
        im.issuer_name
    FROM bond_master bm
    LEFT JOIN issuer_mapping im ON bm.issuer_id = im.issuer_id
    WHERE bm.maturity_date >= '20260101' AND bm.maturity_date <= ?
    ORDER BY bm.maturity_date ASC
    """
    return conn.execute(sql, (end_date,)).fetchall()


def query_monthly_issuance_since_2022(conn):
    """
    2022년 1월 ~ 현재까지 월별 채권종류(섹터)별 발행액 집계.
    """
    sql = """
    SELECT
        SUBSTR(bm.issue_date, 1, 6) AS yyyymm,
        COALESCE(im.sector_code, 'OTHER') AS sector_code,
        SUM(bm.issue_amount) AS total_issue_raw,          -- 원(KRW) 단위 raw
        COUNT(*) AS bond_count
    FROM bond_master bm
    LEFT JOIN issuer_mapping im ON bm.issuer_id = im.issuer_id
    WHERE bm.issue_date >= '20220101' AND bm.issue_date != ''
    GROUP BY yyyymm, sector_code
    ORDER BY yyyymm ASC, sector_code ASC
    """
    return conn.execute(sql).fetchall()


def query_2026_issuance_vs_maturity_by_sector(conn):
    """
    2026년 동일 연도 내 섹터별 발행액 vs 만기액 집계 (차환율 및 수급 밸런스 분석용).
    """
    sql = """
    SELECT
        COALESCE(im.sector_code, 'OTHER') AS sector_code,
        SUM(CASE WHEN bm.issue_date >= '20260101' AND bm.issue_date <= '20261231' THEN bm.issue_amount ELSE 0 END) AS issue_amt_raw,      -- 원(KRW) 단위 raw
        SUM(CASE WHEN bm.maturity_date >= '20260101' AND bm.maturity_date <= '20261231' THEN bm.issue_amount ELSE 0 END) AS maturity_amt_raw  -- 원(KRW) 단위 raw
    FROM bond_master bm
    LEFT JOIN issuer_mapping im ON bm.issuer_id = im.issuer_id
    WHERE (bm.issue_date >= '20260101' AND bm.issue_date <= '20261231')
       OR (bm.maturity_date >= '20260101' AND bm.maturity_date <= '20261231')
    GROUP BY sector_code
    ORDER BY maturity_amt_raw DESC
    """
    return conn.execute(sql).fetchall()



def query_table_counts(conn):
    """각 테이블의 레코드 수 조회 (검증용)."""
    tables = ["issuer_mapping", "bond_master", "bond_supply_flow",
              "bond_settlement_stat", "local_gov_bond_stat"]
    counts = {}
    for t in tables:
        row = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()
        counts[t] = row[0]
    return counts



# ──────────────────────────────────────────────
# 테스트
# ──────────────────────────────────────────────
if __name__ == "__main__":
    init_db()

    # 테이블 존재 확인
    conn = get_connection()
    counts = query_table_counts(conn)
    for table, cnt in counts.items():
        print(f"  {table}: {cnt}건")
    conn.close()

"""
Streamlit 채권 수급 분석 대시보드 (2026 상반기/하반기 분석 대시보드)
- 최우선 목표:
  1. 2026년 상반기(1~6월) 채권종류/섹터별 월별 만기도래액 및 발행액 시각화
  2. 2026년 하반기(7~12월) 월별 만기도래예정액 시각화
  3. 상반기 발행 대비 하반기 만기 수급 쏠림 분석
  4. AI 시황 분석 탭: Gemini API 키 직접 입력 란 포함
"""
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import koreanize_matplotlib
import os

from config import DB_PATH, SECTOR_LABELS
from db import get_connection, init_db, query_table_counts
from analyst import generate_market_commentary

# ──────────────────────────────────────────────
# 페이지 기본 설정
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="2026년 채권 수급 분석 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #475569;
        margin-bottom: 1.8rem;
    }
    .metric-container {
        background-color: #F8FAFC;
        border-left: 4px solid #2563EB;
        padding: 1rem 1.2rem;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)


@st.cache_resource
def check_and_init_db():
    if not os.path.exists(DB_PATH):
        init_db(DB_PATH)


check_and_init_db()


def load_2026_flow_data():
    """bond_supply_flow + bond_master + issuer_mapping 2026년 수급 데이터 로드."""
    conn = get_connection()
    sql = """
    SELECT
        sf.record_id,
        sf.isin_code,
        bm.bond_name,
        COALESCE(im.sector_code, 'OTHER') AS sector_code,
        sf.event_date,
        SUBSTR(sf.event_date, 1, 6) AS yyyymm,
        SUBSTR(sf.event_date, 5, 2) AS month_str,
        CAST(SUBSTR(sf.event_date, 5, 2) AS INTEGER) AS month,
        sf.event_type,
        sf.amount / 1e8 AS amount_100m  -- 억원 단위
    FROM bond_supply_flow sf
    LEFT JOIN bond_master bm ON sf.isin_code = bm.isin_code
    LEFT JOIN issuer_mapping im ON bm.issuer_id = im.issuer_id
    WHERE sf.event_date LIKE '2026%'
    """
    df = pd.read_sql_query(sql, conn)
    conn.close()
    
    if not df.empty:
        df['sector_name'] = df['sector_code'].map(SECTOR_LABELS).fillna('기타 회사채')
        df['half'] = df['month'].apply(lambda m: 'H1 (상반기)' if m <= 6 else 'H2 (하반기)')
    return df


def load_settlement_data():
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT std_yymm,
               bond_setl_cost / 1e12 AS bond_tril,
               cd_setl_cost / 1e12 AS cd_tril,
               cp_setl_cost / 1e12 AS cp_tril,
               stb_setl_cost / 1e12 AS stb_tril
        FROM bond_settlement_stat
        ORDER BY std_yymm
    """, conn)
    conn.close()
    return df


# ──────────────────────────────────────────────
# 타이틀 및 메인 렌더링
# ──────────────────────────────────────────────
st.markdown('<div class="main-title">📊 2026년 채권 수급 대시보드</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">시중은행채 · 여전채(카드/캐피탈) · 국고채 월별 발행 및 만기도래 예정액 분석</div>', unsafe_allow_html=True)

df_2026 = load_2026_flow_data()

# ── 사이드바 ──
st.sidebar.header("🔍 대시보드 필터")
all_sectors = list(SECTOR_LABELS.values())
selected_sectors = st.sidebar.multiselect("분석 섹터 선택", all_sectors, default=all_sectors)

# 필터링 데이터
if not df_2026.empty and selected_sectors:
    filtered_df = df_2026[df_2026['sector_name'].isin(selected_sectors)]
else:
    filtered_df = df_2026

# DB 레코드 상태
conn = get_connection()
counts = query_table_counts(conn)
conn.close()

st.sidebar.markdown("---")
st.sidebar.markdown("### 🗄️ 데이터베이스 현황")
st.sidebar.text(f"• 2026 수급 이벤트: {len(df_2026)}건")
st.sidebar.text(f"• 결제대금 통계: {counts.get('bond_settlement_stat', 0)}건")
st.sidebar.text(f"• 지방채 통계: {counts.get('local_gov_bond_stat', 0)}건")

# ── 1. 핵심 KPI 메트릭 카드 ──
h1_df = filtered_df[filtered_df['half'] == 'H1 (상반기)'] if not filtered_df.empty else pd.DataFrame()
h2_df = filtered_df[filtered_df['half'] == 'H2 (하반기)'] if not filtered_df.empty else pd.DataFrame()

h1_issue = h1_df[h1_df['event_type'] == 'ISSUE']['amount_100m'].sum() if not h1_df.empty else 0
h1_maturity = h1_df[h1_df['event_type'] == 'MATURITY']['amount_100m'].sum() if not h1_df.empty else 0
h2_maturity = h2_df[h2_df['event_type'] == 'MATURITY']['amount_100m'].sum() if not h2_df.empty else 0

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("2026 상반기 총 발행액", f"{h1_issue:,.0f} 억원", help="1월~6월 발행액 합계")
with c2:
    st.metric("2026 상반기 총 만기도래액", f"{h1_maturity:,.0f} 억원", help="1월~6월 만기도래액 합계")
with c3:
    st.metric("2026 하반기 총 만기도래 예정액", f"{h2_maturity:,.0f} 억원", delta=f"상반기 발행 대비 {((h2_maturity-h1_issue)/h1_issue*100):+.1f}%" if h1_issue > 0 else None)

st.markdown("---")

# ── 2. 핵심 분석 탭 ──
tab1, tab2, tab3, tab4 = st.tabs([
    "🗓️ [상반기] 1~6월 발행 & 만기 현황",
    "🔮 [하반기] 7~12월 만기도래 예정액",
    "⚖️ 상반기 발행 vs 하반기 만기 비교",
    "🤖 AI 시황 분석 코멘트"
])

# ── TAB 1: 2026 상반기 (1~6월) ──
with tab1:
    st.subheader("2026년 상반기(1월~6월) 섹터별 월별 발행액 및 만기도래액")
    
    if not h1_df.empty:
        col_left, col_right = st.columns(2)
        
        issue_pivot = h1_df[h1_df['event_type'] == 'ISSUE'].pivot_table(
            index='month_str', columns='sector_name', values='amount_100m', aggfunc='sum', fill_value=0
        )
        mat_pivot = h1_df[h1_df['event_type'] == 'MATURITY'].pivot_table(
            index='month_str', columns='sector_name', values='amount_100m', aggfunc='sum', fill_value=0
        )
        
        with col_left:
            st.markdown("##### 📌 상반기 월별 발행액 (억원)")
            fig, ax = plt.subplots(figsize=(6, 4))
            issue_pivot.plot(kind='bar', stacked=True, ax=ax, colormap='tab10')
            ax.set_title("2026 상반기 월별 채권 발행액", fontsize=11)
            ax.set_xlabel("월")
            ax.set_ylabel("발행액 (억원)")
            ax.legend(title="섹터", bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.xticks(rotation=0)
            plt.tight_layout()
            st.pyplot(fig)
            
        with col_right:
            st.markdown("##### 📌 상반기 월별 만기도래액 (억원)")
            fig, ax = plt.subplots(figsize=(6, 4))
            mat_pivot.plot(kind='bar', stacked=True, ax=ax, colormap='Set2')
            ax.set_title("2026 상반기 월별 채권 만기도래액", fontsize=11)
            ax.set_xlabel("월")
            ax.set_ylabel("만기도래액 (억원)")
            ax.legend(title="섹터", bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.xticks(rotation=0)
            plt.tight_layout()
            st.pyplot(fig)
            
        st.markdown("##### 📋 상반기 섹터별 월별 상세 수치 (발행액 / 만기액)")
        st.dataframe(issue_pivot.style.format("{:,.0f}"))
    else:
        st.info("상반기 데이터가 존재하지 않습니다.")

# ── TAB 2: 2026 하반기 (7~12월 만기도래 예정액) ──
with tab2:
    st.subheader("2026년 하반기(7월~12월) 월별 만기도래 예정액 추이")
    
    if not h2_df.empty:
        h2_mat = h2_df[h2_df['event_type'] == 'MATURITY']
        h2_pivot = h2_mat.pivot_table(
            index='month_str', columns='sector_name', values='amount_100m', aggfunc='sum', fill_value=0
        )
        
        col1, col2 = st.columns([3, 2])
        
        with col1:
            fig, ax = plt.subplots(figsize=(7, 4))
            h2_pivot.plot(kind='bar', stacked=True, ax=ax, colormap='viridis')
            ax.set_title("2026 하반기 월별 만기도래 예정액 추이", fontsize=11)
            ax.set_xlabel("월 (7월~12월)")
            ax.set_ylabel("만기예정액 (억원)")
            ax.legend(title="섹터", bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.xticks(rotation=0)
            plt.tight_layout()
            st.pyplot(fig)
            
        with col2:
            st.markdown("##### 📌 하반기 만기도래 비중 (섹터별)")
            sector_sums = h2_mat.groupby('sector_name')['amount_100m'].sum()
            fig_pie, ax_pie = plt.subplots(figsize=(5, 4))
            ax_pie.pie(sector_sums, labels=sector_sums.index, autopct='%1.1f%%', startangle=140)
            ax_pie.set_title("하반기 섹터별 만기 비중", fontsize=11)
            plt.tight_layout()
            st.pyplot(fig_pie)
            
        st.markdown("##### 📋 하반기 월별/섹터별 만기도래 예정액 수치 (억원)")
        st.dataframe(h2_pivot.style.format("{:,.0f}"))
    else:
        st.info("하반기 만기도래 예정 데이터가 존재하지 않습니다.")

# ── TAB 3: 상반기 발행 vs 하반기 만기 비교 ──
with tab3:
    st.subheader("2026 상반기 발행액 vs 하반기 만기도래 예정액 비교")
    st.caption("상반기 수집된 발행액으로 하반기 도래하는 만기 부담을 커버할 수 있는지 수급 쏠림을 평가합니다.")
    
    if not filtered_df.empty:
        comp_df = filtered_df.groupby(['sector_name', 'half', 'event_type'])['amount_100m'].sum().unstack(level=[1, 2], fill_value=0)
        st.dataframe(comp_df.style.format("{:,.0f} 억원"))
        
        h1_iss = filtered_df[(filtered_df['half']=='H1 (상반기)') & (filtered_df['event_type']=='ISSUE')].groupby('sector_name')['amount_100m'].sum()
        h2_mat = filtered_df[(filtered_df['half']=='H2 (하반기)') & (filtered_df['event_type']=='MATURITY')].groupby('sector_name')['amount_100m'].sum()
        
        comp_chart_df = pd.DataFrame({'상반기 발행액': h1_iss, '하반기 만기예정액': h2_mat}).fillna(0)
        
        fig, ax = plt.subplots(figsize=(9, 4.5))
        comp_chart_df.plot(kind='bar', ax=ax, color=['#2563EB', '#EF4444'], width=0.7)
        ax.set_title("섹터별 상반기 발행액 vs 하반기 만기도래 예정액", fontsize=12)
        ax.set_ylabel("금액 (억원)")
        plt.xticks(rotation=0)
        plt.tight_layout()
        st.pyplot(fig)
    else:
        st.info("비교 데이터가 충분하지 않습니다.")

# ── TAB 4: AI 시황 분석 코멘트 ──
with tab4:
    st.subheader("🤖 Antigravity AI 시황 분석 리포트 (2026년)")
    
    # ── Gemini API 키 직접 입력란 ──
    col_input, col_info = st.columns([2, 1])
    with col_input:
        user_gemini_key = st.text_input(
            "🔑 Gemini API Key 입력 (입력 시 LLM 기반 심화 시황 리포트 자동 생성)",
            type="password",
            placeholder="AIzaSy... 키 입력 후 Enter",
            help="Google AI Studio에서 발급받은 Gemini API 키를 입력하시면 대시보드에서 즉시 LLM 심화 분석 리포트가 생성됩니다."
        )
    with col_info:
        st.markdown("""
        <div style="font-size: 0.85rem; color: #64748B; padding-top: 1.5rem;">
        * 키 미입력 시 실시간 룰 베이스 경보 리포트가 출력됩니다.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    conn = get_connection()
    commentary = generate_market_commentary(conn, year=2026, user_gemini_key=user_gemini_key)
    conn.close()

    st.markdown(f"""
        <div style="background-color: #F1F5F9; border-left: 5px solid #2563EB; padding: 1.5rem; border-radius: 8px; font-size: 1.05rem;">
        {commentary.replace(chr(10), '<br>')}
        </div>
    """, unsafe_allow_html=True)

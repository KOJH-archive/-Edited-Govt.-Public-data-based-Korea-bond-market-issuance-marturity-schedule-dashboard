"""
AI 시황 분석 모듈 (규칙 기반)
- 월별 만기 집중도 탐지
- 섹터별 순발행/순상환 판단
- 전월 대비 증감 경고
- 결제대금 추이 분석
"""
from db import get_connection, query_settlement_trend


def analyze_settlement_trend(conn):
    """
    기관결제대금 현황에서 시계열 추세를 분석.
    전월 대비 변동률이 큰 항목을 경고.
    """
    rows = query_settlement_trend(conn)
    if len(rows) < 2:
        return []

    alerts = []
    categories = {
        "bond_setl_cost": "채권결제대금",
        "cd_setl_cost": "CD결제대금",
        "cp_setl_cost": "CP결제대금",
        "stb_setl_cost": "단기사채결제대금",
    }

    prev = dict(rows[0])
    for row in rows[1:]:
        curr = dict(row)
        for key, label in categories.items():
            prev_val = prev.get(key, 0) or 0
            curr_val = curr.get(key, 0) or 0
            if prev_val > 0:
                change_pct = (curr_val - prev_val) / prev_val * 100
                if abs(change_pct) > 20:  # 20% 이상 변동
                    direction = "급증" if change_pct > 0 else "급감"
                    alerts.append({
                        "period": curr["std_yymm"],
                        "category": label,
                        "change_pct": round(change_pct, 1),
                        "direction": direction,
                        "msg": f"{curr['std_yymm']} {label} 전월 대비 {direction} ({change_pct:+.1f}%)",
                    })
        prev = curr

    return alerts


def analyze_local_gov_supply(conn):
    """
    지방채 발행/상환 현황에서 순발행(신규-상환)을 분석.
    순상환 전환 또는 순발행 급증을 탐지.
    """
    rows = conn.execute("""
        SELECT std_yymm,
               train_bond_new_issu, train_bond_red,
               rd_bond_new_issu, rd_bond_red,
               gen_loc_bond_new_issu, gen_loc_bond_red
        FROM local_gov_bond_stat
        ORDER BY std_yymm
    """).fetchall()

    if not rows:
        return []

    alerts = []
    categories = [
        ("도시철도채", "train_bond_new_issu", "train_bond_red"),
        ("지역개발채", "rd_bond_new_issu", "rd_bond_red"),
        ("일반지방채", "gen_loc_bond_new_issu", "gen_loc_bond_red"),
    ]

    for row in rows:
        r = dict(row)
        for name, new_key, red_key in categories:
            new_val = r.get(new_key, 0) or 0
            red_val = r.get(red_key, 0) or 0
            net = new_val - red_val

            if red_val > 0 and new_val > 0:
                ratio = red_val / new_val
                if ratio > 1.5:  # 상환이 발행의 1.5배 초과
                    alerts.append({
                        "period": r["std_yymm"],
                        "category": name,
                        "net_supply": net,
                        "msg": f"{r['std_yymm']} {name}: 순상환 전환 (상환 {red_val:,} > 발행 {new_val:,})",
                    })
                elif new_val > red_val * 2:  # 발행이 상환의 2배 초과
                    alerts.append({
                        "period": r["std_yymm"],
                        "category": name,
                        "net_supply": net,
                        "msg": f"{r['std_yymm']} {name}: 대규모 순발행 (발행 {new_val:,} >> 상환 {red_val:,})",
                    })

    return alerts


def analyze_supply_flow(conn, year):
    """
    bond_supply_flow에서 월별 만기 집중도를 분석.
    특정 월에 전체 만기의 30% 이상이 집중되면 경고.
    """
    rows = conn.execute("""
        SELECT
            SUBSTR(event_date, 1, 6) AS yyyymm,
            SUM(amount) AS total_maturity
        FROM bond_supply_flow
        WHERE event_type = 'MATURITY'
          AND event_date LIKE ? || '%'
        GROUP BY yyyymm
        ORDER BY yyyymm
    """, (str(year),)).fetchall()

    if not rows:
        return []

    total = sum(dict(r)["total_maturity"] for r in rows)
    if total == 0:
        return []

    alerts = []
    for row in rows:
        r = dict(row)
        pct = r["total_maturity"] / total * 100
        if pct > 25:  # 25% 이상 집중
            alerts.append({
                "period": r["yyyymm"],
                "amount": r["total_maturity"],
                "pct": round(pct, 1),
                "msg": f"{r['yyyymm']} 만기 집중도 {pct:.1f}% (금액: {r['total_maturity']:,}원)",
            })

    return alerts


def generate_market_commentary(conn, year=2025):
    """
    전체 분석을 종합하여 시황 코멘트를 생성.
    규칙 기반으로 주요 이슈를 요약.
    """
    commentary_parts = []

    # 1. 결제대금 추이 분석
    setl_alerts = analyze_settlement_trend(conn)
    if setl_alerts:
        commentary_parts.append("## 기관결제대금 동향")
        for a in setl_alerts[-5:]:  # 최근 5건만
            commentary_parts.append(f"- {a['msg']}")

    # 2. 지방채 수급 분석
    gov_alerts = analyze_local_gov_supply(conn)
    if gov_alerts:
        commentary_parts.append("\n## 지방채 수급 동향")
        for a in gov_alerts[-5:]:
            commentary_parts.append(f"- {a['msg']}")

    # 3. 만기 집중도 분석
    flow_alerts = analyze_supply_flow(conn, year)
    if flow_alerts:
        commentary_parts.append(f"\n## {year}년 만기 집중도")
        for a in flow_alerts:
            commentary_parts.append(f"- {a['msg']}")

    # 종합 코멘트
    if not commentary_parts:
        return "현재 수집된 데이터 범위에서 특이 동향이 감지되지 않았습니다."

    header = f"# 채권시장 수급 분석 리포트 ({year}년)\n"
    return header + "\n".join(commentary_parts)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    conn = get_connection()
    report = generate_market_commentary(conn, year=2025)
    print(report)
    conn.close()

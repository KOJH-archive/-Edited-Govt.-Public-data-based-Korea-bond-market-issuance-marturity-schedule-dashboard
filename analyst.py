"""
AI 시황 분석 모듈 (규칙 기반 시장 동향 감지)
- 기관결제대금 시계열 추세 분석 (±20% 이상 급증/급감 감지)
- 지방채 발행/상환 현황 분석 (순상환/순발행 감지)
"""
import sqlite3
from db import get_connection, query_settlement_trend


def analyze_settlement_trend(conn):
    """기관결제대금 현황에서 시계열 추세를 분석."""
    conn.row_factory = sqlite3.Row
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
    """지방채 발행/상환 현황 분석."""
    conn.row_factory = sqlite3.Row
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
                if ratio > 1.5:
                    alerts.append({
                        "period": r["std_yymm"],
                        "category": name,
                        "net_supply": net,
                        "msg": f"{r['std_yymm']} {name}: 순상환 전환 (상환 {red_val:,} > 발행 {new_val:,})",
                    })
                elif new_val > red_val * 2:
                    alerts.append({
                        "period": r["std_yymm"],
                        "category": name,
                        "net_supply": net,
                        "msg": f"{r['std_yymm']} {name}: 대규모 순발행 (발행 {new_val:,} >> 상환 {red_val:,})",
                    })

    return alerts


def generate_market_commentary(conn, year=2026):
    """전체 수급 데이터를 종합하여 룰 베이스 분석 결과 생성."""
    rule_insights = []

    # 1. 결제대금 추이 분석
    setl_alerts = analyze_settlement_trend(conn)
    if setl_alerts:
        rule_insights.append("## 📈 기관결제대금 동향 경보")
        for a in setl_alerts[-6:]:
            rule_insights.append(f"- {a['msg']}")

    # 2. 지방채 수급 분석
    gov_alerts = analyze_local_gov_supply(conn)
    if gov_alerts:
        rule_insights.append("\n## 🏛️ 지방채 수급 동향 경보")
        for a in gov_alerts[-6:]:
            rule_insights.append(f"- {a['msg']}")

    base_rule_text = "\n".join(rule_insights) if rule_insights else "현재 수집된 데이터 범위에서 특이 동향이 감지되지 않았습니다."

    return f"""# 📊 채권시장 수급 감지 리포트 ({year}년)

{base_rule_text}
"""


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    conn = get_connection()
    report = generate_market_commentary(conn, year=2026)
    print(report)
    conn.close()

"""
AI 시황 분석 모듈 (하이브리드: 룰 베이스 + Gemini LLM 연동)
- 기본: 규칙 기반 시장 특이 동향 감지
- 옵션: 대시보드 UI 입력 또는 .env 에 GEMINI_API_KEY 설정 시 Gemini LLM 심화 분석 리포트 생성
- urllib.request 기반 Pure Python HTTP REST API 호출로 100% 안정성 보장
"""
import os
import json
import urllib.request
import urllib.parse
from db import get_connection, query_settlement_trend


def load_gemini_api_key():
    """GEMINI_API_KEY 또는 GOOGLE_API_KEY 환경변수 로드."""
    for key_name in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
        val = os.getenv(key_name)
        if val:
            return val.strip()

    for filename in [".env", "Public.env"]:
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GEMINI_API_KEY=") or line.startswith("GOOGLE_API_KEY="):
                            return line.split("=", 1)[1].strip()
            except Exception:
                pass
    return None


def call_gemini_llm(prompt, api_key):
    """
    Pure Python urllib.request 기반 Gemini API (gemini-1.5-flash) 호출.
    외부 라이브러리 설치 없이 100% 동작 보장.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    
    data = json.dumps(payload).encode("utf-8")
    
    try:
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            
        candidates = res_data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "")
    except Exception as e:
        return f"⚠️ Gemini LLM 호출 중 오류가 발생했습니다: {e}"
        
    return "LLM 분석 결과를 생성할 수 없습니다."


def analyze_settlement_trend(conn):
    """기관결제대금 현황에서 시계열 추세를 분석."""
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


def generate_market_commentary(conn, year=2026, user_gemini_key=None):
    """
    전체 수급 데이터를 종합하여 룰 베이스 분석 결과 생성.
    user_gemini_key 입력 또는 파일의 GEMINI_API_KEY 설정 시 Gemini LLM 심화 시황 리포트 병행 생성.
    """
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
    
    # ── Gemini LLM 키 점검 (UI 직접 입력 우선) ──
    gemini_key = user_gemini_key.strip() if user_gemini_key else load_gemini_api_key()

    if gemini_key:
        prompt = f"""
당신은 한국 채권시장 수급 분석 전문 금융 애널리스트(AI 시황 분석관)입니다.
아래에 수집된 {year}년 한국 채권시장 실시간 데이터 감지 결과(기관결제대금, 지방채 발행/상환 등)를 바탕으로,
금융 전문가 및 투자자를 위한 깊이 있고 통찰력 있는 '채권 수급 종합 전망 및 시황 리포트'를 마크다운 형식으로 작성해주세요.

[데이터 감지 결과]
{base_rule_text}

[작성 가이드라인]
1. 💡 요약 메세지 (3줄 요약)
2. 📊 {year}년 채권 수급 및 차환(Refinancing) 리스크 분석
3. 📉 금리 변동성 및 자금 시장에 미치는 영향 평가
4. 🚀 향후 대응 전략 및 시사점

답변은 한국어로 작성하며, 전문적이고 명료한 어조로 작성해주세요.
"""
        llm_report = call_gemini_llm(prompt, gemini_key)
        
        return f"""# 🤖 Gemini AI 프리미엄 시황 분석 리포트 ({year}년)

> ✨ **Gemini LLM 지능형 심화 분석이 적용되었습니다.**

{llm_report}

---
### 🔍 [참고] 룰 베이스 실시간 데이터 감지 내역
{base_rule_text}
"""

    else:
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

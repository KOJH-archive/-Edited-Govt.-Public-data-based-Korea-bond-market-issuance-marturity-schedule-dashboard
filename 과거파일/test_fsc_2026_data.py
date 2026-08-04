"""
금융위원회_채권발행정보 V2로 2026년 실제 채권 수급 데이터 추출 가능성 검증
"""
import urllib.request
import urllib.parse
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

KEY = open("Public.env").read().strip()
BASE = "https://apis.data.go.kr/1160100/GetBondTradInfoService_V2"

def scan_2026_bonds():
    # 최근 100건을 불러와 2026년 발행/만기 채권이 포함되어 있는지 검사
    qs = urllib.parse.urlencode({
        "resultType": "json",
        "pageNo": "1",
        "numOfRows": "100",
    })
    url = f"{BASE}/getIssuIssuItemStat_V2?serviceKey={KEY}&{qs}"
    
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        
    body = data.get("response", {}).get("body", {})
    total = body.get("totalCount", 0)
    items = body.get("items", {}).get("item", [])
    
    print(f"전체 채권 종목 수: {total:,}건 수신")
    
    h1_issu_count = 0
    h1_matu_count = 0
    h2_matu_count = 0
    
    print("\n[2026년 수급 데이터 샘플 추출 (상위 100개 중)]")
    for item in items:
        name = item.get("isinCdNm", "")
        issu_dt = item.get("bondIssuDt", "")
        expr_dt = item.get("bondExprDt", "")
        amt = int(item.get("bondIssuAmt", 0) or 0) // 100000000  # 억원
        isur = item.get("bondIsurNm", "")
        kind = item.get("scrsItmsKcdNm", "")
        
        # 2026년 상반기 발행
        if issu_dt.startswith("202601") or issu_dt.startswith("202602") or issu_dt.startswith("202603") or issu_dt.startswith("202604") or issu_dt.startswith("202605") or issu_dt.startswith("202606"):
            h1_issu_count += 1
            print(f"  [2026 H1 발행] {name:25s} | 발행일:{issu_dt} | 만기일:{expr_dt} | {amt:,}억원 | {isur}")
            
        # 2026년 상반기 만기
        if expr_dt.startswith("202601") or expr_dt.startswith("202602") or expr_dt.startswith("202603") or expr_dt.startswith("202604") or expr_dt.startswith("202605") or expr_dt.startswith("202606"):
            h1_matu_count += 1
            print(f"  [2026 H1 만기] {name:25s} | 발행일:{issu_dt} | 만기일:{expr_dt} | {amt:,}억원 | {isur}")

        # 2026년 하반기 만기
        if expr_dt.startswith("202607") or expr_dt.startswith("202608") or expr_dt.startswith("202609") or expr_dt.startswith("202610") or expr_dt.startswith("202611") or expr_dt.startswith("202612"):
            h2_matu_count += 1
            print(f"  [2026 H2 만기] {name:25s} | 발행일:{issu_dt} | 만기일:{expr_dt} | {amt:,}억원 | {isur}")

    print(f"\n샘플 100개 중 2026년 H1발행:{h1_issu_count}건, H1만기:{h1_matu_count}건, H2만기:{h2_matu_count}건 감지됨!")

if __name__ == "__main__":
    scan_2026_bonds()

"""
금융위원회_채권발행정보 V2 API 탐색 스크립트
10,000회 트래픽 지원
"""
import urllib.request
import urllib.parse
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

KEY = open("Public.env").read().strip()
BASE = "https://apis.data.go.kr/1160100/GetBondTradInfoService_V2"

def test_endpoint(op, params):
    qs = urllib.parse.urlencode({"resultType": "json", "pageNo": "1", "numOfRows": "5", **params})
    url = f"{BASE}{op}?serviceKey={KEY}&{qs}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        header = data.get("response", {}).get("header", {})
        body = data.get("response", {}).get("body", {})
        total = body.get("totalCount", 0)
        items = body.get("items", {}).get("item", [])
        if isinstance(items, dict):
            items = [items]
        
        print(f"[{op:25s}] code={header.get('resultCode')} msg={header.get('resultMsg')} total={total} items={len(items)}")
        if items:
            print(f"  SAMPLE ITEM: {json.dumps(items[0], ensure_ascii=False)}")
    except Exception as e:
        print(f"[{op:25s}] EXCEPTION: {e}")

print("=" * 80)
print("1. getIssuIssuItemStat_V2 테스트")
test_endpoint("/getIssuIssuItemStat_V2", {})
test_endpoint("/getIssuIssuItemStat_V2", {"basDt": "20250102"})

print("\n2. getKindIssuMatuStat_V2 테스트")
test_endpoint("/getKindIssuMatuStat_V2", {})
test_endpoint("/getKindIssuMatuStat_V2", {"basDt": "20250102"})
test_endpoint("/getKindIssuMatuStat_V2", {"basDt": "20240102"})

print("\n3. getBondPrinAndInte_V2 테스트")
test_endpoint("/getBondPrinAndInte_V2", {})
test_endpoint("/getBondPrinAndInte_V2", {"basDt": "20250102"})
test_endpoint("/getBondPrinAndInte_V2", {"vltgPayDt": "20260601"})

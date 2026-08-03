"""
3차 파라미터 탐색: Swagger에서 확인된 정확한 파라미터명으로 재시도.
serviceKey의 URL 인코딩 방식(Encoding/Decoding)도 함께 테스트.
"""
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

RAW_KEY = open("Public.env").read().strip()
# 공공데이터포털에서는 Encoding된 키와 Decoding된 키가 다를 수 있음
# Hex 문자열은 URL-safe이므로 인코딩해도 동일하지만, 혹시 모르니 두 가지 모두 테스트
ENCODED_KEY = urllib.parse.quote(RAW_KEY, safe='')

BASE = "https://apis.data.go.kr/B552481/BondSvc"

def test(op, params, key_label, api_key):
    params_with_paging = {**params, "pageNo": "1", "numOfRows": "3"}
    qs = urllib.parse.urlencode(params_with_paging)
    url = f"{BASE}{op}?serviceKey={api_key}&{qs}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("utf-8")
        root = ET.fromstring(data)
        code = root.findtext(".//resultCode", "N/A")
        msg = root.findtext(".//resultMsg", "N/A")
        items = root.findall(".//item")
        total = root.findtext(".//totalCount", "?")
        marker = ">>> OK" if code == "00" else f"ERR[{code}]"
        print(f"{marker:10s} | {key_label:8s} | {op:45s} | {params} | items={len(items)} total={total} | {msg}")
        if code == "00" and items:
            for child in items[0]:
                print(f"           |   {child.tag} = {child.text}")
    except Exception as e:
        print(f"EXCEPTION  | {key_label:8s} | {op:45s} | {params} | {str(e)[:80]}")

# Swagger에서 확인된 정확한 파라미터로 테스트
test_cases = [
    # getBondKindInsetlStat: schBeginDt + schExpryDt (Swagger 확정)
    ("/getBondKindInsetlStat", {"schBeginDt": "20250101", "schExpryDt": "20250630"}),
    ("/getBondKindInsetlStat", {"schBeginDt": "20240101", "schExpryDt": "20240630"}),
    ("/getBondKindInsetlStat", {"schBeginDt": "20230101", "schExpryDt": "20230630"}),
    
    # getlocalgovernmentIssuStat: schBeginYearMm + schExpryYearMm (Swagger 확정)
    ("/getlocalgovernmentIssuStat", {"schBeginYearMm": "202501", "schExpryYearMm": "202506"}),
    ("/getlocalgovernmentIssuStat", {"schBeginYearMm": "202401", "schExpryYearMm": "202406"}),
    ("/getlocalgovernmentIssuStat", {"schBeginYearMm": "202301", "schExpryYearMm": "202306"}),
    
    # getRgtXrcInfo: schStdYy (Swagger 확정, 값 형식 변형)
    ("/getRgtXrcInfo", {"schStdYy": "2024"}),
    ("/getRgtXrcInfo", {"schStdYy": "2023"}),
    ("/getRgtXrcInfo", {"schStdYy": "2022"}),
    
    # getIssurBondIssuDetailsInfo: issucoCustno (이미 확인됨)
    ("/getIssurBondIssuDetailsInfo", {"issucoCustno": "00149985"}),
    ("/getIssurBondIssuDetailsInfo", {"issucoCustno": "149985"}),
    ("/getIssurBondIssuDetailsInfo", {"issucoCustno": "1"}),
]

print("=" * 120)
print("RAW KEY (Decoding) 테스트")
print("=" * 120)
for op, params in test_cases:
    test(op, params, "RAW", RAW_KEY)

print()
print("=" * 120)
print("ENCODED KEY 테스트")
print("=" * 120)
for op, params in test_cases:
    test(op, params, "ENCODED", ENCODED_KEY)

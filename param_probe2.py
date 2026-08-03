"""
2차 파라미터 탐색.
1차에서 확인한 것:
- getIssurBondIssuDetailsInfo: issucoCustno가 정확한 필수 파라미터 (ERR[3]=NODATA)
- getBondKindInsetlStat, getlocalgovernmentIssuStat: 파라미터명 아직 못찾음

2차에서는:
- 좀 더 다양한 이름 조합 시도
- getRgtXrcInfo, getPrinFixInfoSchSvc, getBondErlyRedInfo도 테스트
"""
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

API_KEY = open("Public.env").read().strip()
BASE = "https://apis.data.go.kr/B552481/BondSvc"

test_cases = [
    # getBondKindInsetlStat - 추가 변형
    ("/getBondKindInsetlStat", {"baseYm": "202501"}),
    ("/getBondKindInsetlStat", {"baseYymm": "202501"}),
    ("/getBondKindInsetlStat", {"baseMm": "202501"}),
    ("/getBondKindInsetlStat", {"yyyymm": "202501"}),
    ("/getBondKindInsetlStat", {"stdrYm": "202501"}),
    ("/getBondKindInsetlStat", {"stdrYymm": "202501"}),
    ("/getBondKindInsetlStat", {"crtrYm": "202501"}),
    ("/getBondKindInsetlStat", {"srchBgnDt": "20250101", "srchEndDt": "20250630"}),
    ("/getBondKindInsetlStat", {"bgnDt": "20250101", "endDt": "20250630"}),
    ("/getBondKindInsetlStat", {"bondKndCd": "01"}),
    ("/getBondKindInsetlStat", {"BasDt": "20250101"}),
    ("/getBondKindInsetlStat", {"BasYm": "202501"}),
    ("/getBondKindInsetlStat", {"BAS_DT": "20250101"}),
    
    # getlocalgovernmentIssuStat - 추가 변형
    ("/getlocalgovernmentIssuStat", {"baseYm": "202501"}),
    ("/getlocalgovernmentIssuStat", {"stdrYm": "202501"}),
    ("/getlocalgovernmentIssuStat", {"stdrYymm": "202501"}),
    ("/getlocalgovernmentIssuStat", {"crtrYm": "202501"}),
    ("/getlocalgovernmentIssuStat", {"bgnYm": "202501", "endYm": "202506"}),
    ("/getlocalgovernmentIssuStat", {"bgnDt": "20250101", "endDt": "20250630"}),
    
    # getRgtXrcInfo
    ("/getRgtXrcInfo", {"schStdYy": "2024"}),
    ("/getRgtXrcInfo", {"baseYy": "2024"}),
    ("/getRgtXrcInfo", {"basYy": "2024"}),
    ("/getRgtXrcInfo", {"stdrYy": "2024"}),
    ("/getRgtXrcInfo", {"yyyy": "2024"}),
    
    # getPrinFixInfoSchSvc - 다양한 조합
    ("/getPrinFixInfoSchSvc", {"isin": "KR6150331F58"}),
    ("/getPrinFixInfoSchSvc", {"isinCd": "KR6150331F58"}),
    ("/getPrinFixInfoSchSvc", {"basDt": "20250101"}),
    
    # getBondErlyRedInfo
    ("/getBondErlyRedInfo", {"isin": "KR6150331F58"}),
    ("/getBondErlyRedInfo", {"isinCd": "KR6150331F58"}),
    ("/getBondErlyRedInfo", {"basDt": "20250101"}),
]

for op, params in test_cases:
    params_with_paging = {**params, "pageNo": "1", "numOfRows": "3"}
    qs = urllib.parse.urlencode(params_with_paging)
    url = f"{BASE}{op}?serviceKey={API_KEY}&{qs}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("utf-8")
        root = ET.fromstring(data)
        code = root.findtext(".//resultCode", "N/A")
        msg = root.findtext(".//resultMsg", "N/A")
        items = root.findall(".//item")
        marker = ">>> OK" if code == "00" else f"ERR[{code}]"
        print(f"{marker:10s} | {op:45s} | {params} | items={len(items)} | {msg}")
        if code == "00" and items:
            fields = [child.tag for child in items[0]]
            print(f"           | FIELDS: {fields}")
            # 첫 번째 item의 값도 출력
            for child in items[0]:
                print(f"           |   {child.tag} = {child.text}")
    except Exception as e:
        print(f"EXCEPTION  | {op:45s} | {params} | {str(e)[:60]}")

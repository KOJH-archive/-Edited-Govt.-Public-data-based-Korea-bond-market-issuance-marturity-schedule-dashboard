"""
API 파라미터 브루트포스 테스트.
공공데이터포털 미리보기에서 확인된 파라미터명 변형을 시도하여 실제 작동하는 조합을 찾는다.
"""
import urllib.request
import urllib.parse
import sys

API_KEY = open("Public.env").read().strip()
BASE = "https://apis.data.go.kr/B552481/BondSvc"

# 테스트할 엔드포인트 + 파라미터 조합들
test_cases = [
    # getBondKindInsetlStat: 기간 파라미터명 변형
    ("/getBondKindInsetlStat", {"basDt": "20250101"}),
    ("/getBondKindInsetlStat", {"basYm": "202501"}),
    ("/getBondKindInsetlStat", {"bas_ym": "202501"}),
    ("/getBondKindInsetlStat", {"stdYymm": "202501"}),
    ("/getBondKindInsetlStat", {"beginDt": "20250101", "endDt": "20250630"}),
    ("/getBondKindInsetlStat", {"strtDt": "20250101", "endDt": "20250630"}),
    ("/getBondKindInsetlStat", {"searchBgnDt": "20250101", "searchEndDt": "20250630"}),
    ("/getBondKindInsetlStat", {"schBgnDt": "20250101", "schEndDt": "20250630"}),
    ("/getBondKindInsetlStat", {"schBeginDt": "20250101", "schEndDt": "20250630"}),
    ("/getBondKindInsetlStat", {"beginBasDt": "20250101", "endBasDt": "20250630"}),
    ("/getBondKindInsetlStat", {"beginBasYm": "202501", "endBasYm": "202506"}),
    ("/getBondKindInsetlStat", {"fromYymm": "202501", "toYymm": "202506"}),
    
    # getlocalgovernmentIssuStat: 년월 파라미터명 변형
    ("/getlocalgovernmentIssuStat", {"basDt": "20250101"}),
    ("/getlocalgovernmentIssuStat", {"basYm": "202501"}),
    ("/getlocalgovernmentIssuStat", {"basYymm": "202501"}),
    ("/getlocalgovernmentIssuStat", {"stdYymm": "202501"}),
    ("/getlocalgovernmentIssuStat", {"searchBgnDt": "20250101", "searchEndDt": "20250630"}),
    ("/getlocalgovernmentIssuStat", {"beginBasYm": "202501", "endBasYm": "202506"}),
    
    # getIssurBondIssuDetailsInfo: 발행인코드 변형
    ("/getIssurBondIssuDetailsInfo", {"basDt": "20250101"}),
    ("/getIssurBondIssuDetailsInfo", {"issuDt": "20250101"}),
    ("/getIssurBondIssuDetailsInfo", {"isinCd": "KR6150331F58"}),
    ("/getIssurBondIssuDetailsInfo", {"issurCd": "00149985"}),
    ("/getIssurBondIssuDetailsInfo", {"issucoCustno": "00149985"}),
]

for op, params in test_cases:
    params_with_paging = {**params, "pageNo": "1", "numOfRows": "3"}
    qs = urllib.parse.urlencode(params_with_paging)
    url = f"{BASE}{op}?serviceKey={API_KEY}&{qs}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("utf-8")
        # resultCode 추출
        import xml.etree.ElementTree as ET
        root = ET.fromstring(data)
        code = root.findtext(".//resultCode", "N/A")
        msg = root.findtext(".//resultMsg", "N/A")
        items = root.findall(".//item")
        status = "OK" if code == "00" else f"ERR[{code}]"
        print(f"{status:10s} | {op:45s} | {params} | items={len(items)} | {msg}")
        if code == "00" and items:
            # 성공! 첫 번째 item의 필드명 출력
            fields = [child.tag for child in items[0]]
            print(f"           | FIELDS: {fields}")
    except Exception as e:
        print(f"EXCEPTION  | {op:45s} | {params} | {e}")

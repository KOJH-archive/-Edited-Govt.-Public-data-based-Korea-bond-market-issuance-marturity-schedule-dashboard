"""
issucoCustno(발행회사 고객번호) 범위 탐색.
1~100 범위에서 데이터가 있는 고객번호를 찾고, 발행한 채권의 종목명으로 발행사를 역추적한다.
"""
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

API_KEY = open("Public.env").read().strip()
BASE = "https://apis.data.go.kr/B552481/BondSvc"

found = []
for custno in range(1, 101):
    params = {"issucoCustno": str(custno), "pageNo": "1", "numOfRows": "1"}
    qs = urllib.parse.urlencode(params)
    url = f"{BASE}/getIssurBondIssuDetailsInfo?serviceKey={API_KEY}&{qs}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("utf-8")
        root = ET.fromstring(data)
        code = root.findtext(".//resultCode", "N/A")
        total = root.findtext(".//totalCount", "0")
        if code == "00":
            items = root.findall(".//item")
            if items:
                name = items[0].findtext("korSecnNm", "?")
                isin = items[0].findtext("isin", "?")
                kind = items[0].findtext("secnKacd", "?")
                print(f"custno={custno:3d} | total={total:>5s} | kind={kind} | sample={name} | isin={isin}")
                found.append(custno)
    except Exception:
        pass

print(f"\n--- Found {len(found)} active issuers in range 1-100 ---")
print(f"IDs: {found}")

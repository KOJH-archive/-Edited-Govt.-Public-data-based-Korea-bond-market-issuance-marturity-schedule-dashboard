"""발행사 이름 확인 스크립트 (UTF-8 출력)."""
import urllib.request
import xml.etree.ElementTree as ET
import sys
sys.stdout.reconfigure(encoding='utf-8')

KEY = open("Public.env").read().strip()
BASE = "https://apis.data.go.kr/B552481/BondSvc"

for i in [1, 3, 4, 6, 7, 8, 11, 12, 14, 15, 22, 25, 27, 30, 37, 39, 40, 49, 50, 52, 54, 64, 66, 68, 72, 82]:
    url = f"{BASE}/getIssurBondIssuDetailsInfo?serviceKey={KEY}&issucoCustno={i}&pageNo=1&numOfRows=1"
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=10) as resp:
            data = resp.read().decode("utf-8")
        root = ET.fromstring(data)
        total = root.findtext(".//totalCount", "0")
        name = root.findtext(".//korSecnNm", "?")
        kind = root.findtext(".//secnKacd", "?")
        isin = root.findtext(".//isin", "?")
        print(f"custno={i:3d} | total={total:>5s} | kind={kind} | sample_name={name} | isin={isin}")
    except Exception as e:
        print(f"custno={i:3d} | ERROR: {e}")

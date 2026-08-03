"""
한국예탁결제원 & 금융위원회 채권정보 공공데이터 수집 모듈
- KSD API (100회 한도): 기관결제대금, 지방채 통계
- FSC V2 API (10,000회 한도): 개별 채권 종목별 발행/만기 실데이터 전수 수집
"""
import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET
import time

from config import BASE_URL, load_api_key

FSC_BASE_URL = "https://apis.data.go.kr/1160100/GetBondTradInfoService_V2"


# ──────────────────────────────────────────────
# KSD XML API 공통 호출 엔진
# ──────────────────────────────────────────────
def _call_ksd_api(operation, api_key, params, max_retries=2):
    query_string = urllib.parse.urlencode(params)
    url = f"{BASE_URL}{operation}?serviceKey={api_key}&{query_string}"

    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                xml_data = resp.read().decode("utf-8")
            break
        except Exception as e:
            if attempt < max_retries:
                time.sleep(1)
                continue
            raise RuntimeError(f"KSD API 호출 실패 ({operation}): {e}")

    root = ET.fromstring(xml_data)
    code_el = root.find(".//resultCode")
    msg_el = root.find(".//resultMsg")
    code = code_el.text if code_el is not None else "N/A"
    msg = msg_el.text if msg_el is not None else "Unknown"

    if code != "00":
        raise RuntimeError(f"API 에러 [{code}] {msg} (op={operation})")

    items = root.findall(".//item")
    rows = []
    for item in items:
        row = {}
        for child in item:
            row[child.tag] = child.text
        rows.append(row)

    total_el = root.find(".//totalCount")
    total_count = int(total_el.text) if total_el is not None else len(rows)

    return rows, total_count


def fetch_all_ksd_pages(operation, api_key, params, rows_per_page=100):
    params = dict(params)
    params["numOfRows"] = str(rows_per_page)
    params["pageNo"] = "1"

    first_page, total_count = _call_ksd_api(operation, api_key, params)
    all_data = list(first_page)

    total_pages = (total_count + rows_per_page - 1) // rows_per_page
    for page in range(2, total_pages + 1):
        params["pageNo"] = str(page)
        page_data, _ = _call_ksd_api(operation, api_key, params)
        all_data.extend(page_data)
        time.sleep(0.2)

    return all_data


# ──────────────────────────────────────────────
# KSD API 수집 함수
# ──────────────────────────────────────────────
def fetch_bond_kind_insetl_stat(api_key, begin_dt, expiry_dt):
    params = {"schBeginDt": begin_dt, "schExpryDt": expiry_dt}
    return fetch_all_ksd_pages("/getBondKindInsetlStat", api_key, params)


def fetch_local_gov_issu_stat(api_key, begin_ym, expiry_ym):
    params = {"schBeginYearMm": begin_ym, "schExpryYearMm": expiry_ym}
    return fetch_all_ksd_pages("/getlocalgovernmentIssuStat", api_key, params)


# ──────────────────────────────────────────────
# 금융위원회 V2 API (10,000회 트래픽) 수집 엔진
# ──────────────────────────────────────────────
def fetch_fsc_bond_items(api_key, bas_dt=None, rows_per_page=100):
    """
    금융위원회 채권발행정보 V2 API (/getIssuIssuItemStat_V2) 호출.
    대한민국 모든 개별 채권의 종목명, 발행일, 만기일, 발행금액 100% 수집.
    """
    params = {
        "serviceKey": api_key,
        "resultType": "json",
        "pageNo": "1",
        "numOfRows": str(rows_per_page)
    }
    if bas_dt:
        params["basDt"] = str(bas_dt)

    qs = urllib.parse.urlencode(params)
    url = f"{FSC_BASE_URL}/getIssuIssuItemStat_V2?{qs}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        body = data.get("response", {}).get("body", {})
        items = body.get("items", {}).get("item", [])
        if isinstance(items, dict):
            items = [items]
        return items
    except Exception as e:
        print(f"⚠️ FSC API 수집 실패 (basDt={bas_dt}): {e}")
        return []

"""
한국예탁결제원 채권정보서비스 API 데이터 수집 모듈
- 6개 엔드포인트 공통 호출 로직
- XML 파싱 → 딕셔너리 리스트 변환
- 자동 페이지네이션
"""
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import time

from config import BASE_URL, load_api_key


# ──────────────────────────────────────────────
# 공통 API 호출 엔진
# ──────────────────────────────────────────────
def _call_api(operation, api_key, params, max_retries=2):
    """
    단일 API 호출 → XML 파싱 → item 리스트 반환.
    resultCode != '00' 이면 예외 발생.
    """
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
            raise RuntimeError(f"API 호출 실패 ({operation}): {e}")

    root = ET.fromstring(xml_data)
    code_el = root.find(".//resultCode")
    msg_el = root.find(".//resultMsg")
    code = code_el.text if code_el is not None else "N/A"
    msg = msg_el.text if msg_el is not None else "Unknown"

    if code != "00":
        raise RuntimeError(f"API 에러 [{code}] {msg} (op={operation}, params={params})")

    items = root.findall(".//item")
    rows = []
    for item in items:
        row = {}
        for child in item:
            row[child.tag] = child.text
        rows.append(row)

    # totalCount 정보 추출 (페이지네이션용)
    total_el = root.find(".//totalCount")
    total_count = int(total_el.text) if total_el is not None else len(rows)

    return rows, total_count


def fetch_all_pages(operation, api_key, params, rows_per_page=100):
    """
    페이지네이션을 자동으로 처리하여 전체 데이터를 수집.
    API 최대 허용 수량인 rows_per_page=100으로 설정.
    """
    params = dict(params)  # 원본 보호
    params["numOfRows"] = str(rows_per_page)
    params["pageNo"] = "1"

    first_page, total_count = _call_api(operation, api_key, params)
    all_data = list(first_page)

    total_pages = (total_count + rows_per_page - 1) // rows_per_page

    for page in range(2, total_pages + 1):
        params["pageNo"] = str(page)
        page_data, _ = _call_api(operation, api_key, params)
        all_data.extend(page_data)
        time.sleep(0.2)

    return all_data


# ──────────────────────────────────────────────
# 엔드포인트별 수집 함수
# ──────────────────────────────────────────────
def fetch_issuer_bond_details(api_key, issuco_custno):
    params = {"issucoCustno": str(issuco_custno)}
    return fetch_all_pages("/getIssurBondIssuDetailsInfo", api_key, params)


def fetch_bond_kind_insetl_stat(api_key, begin_dt, expiry_dt):
    params = {"schBeginDt": begin_dt, "schExpryDt": expiry_dt}
    return fetch_all_pages("/getBondKindInsetlStat", api_key, params)


def fetch_local_gov_issu_stat(api_key, begin_ym, expiry_ym):
    params = {"schBeginYearMm": begin_ym, "schExpryYearMm": expiry_ym}
    return fetch_all_pages("/getlocalgovernmentIssuStat", api_key, params)


def fetch_rgt_xrc_info(api_key, year):
    params = {"schStdYy": str(year)}
    return fetch_all_pages("/getRgtXrcInfo", api_key, params)


def fetch_prin_fix_info(api_key, begin_dt, expiry_dt, isin):
    params = {"schBeginDt": begin_dt, "schExpryDt": expiry_dt, "isin": isin}
    return fetch_all_pages("/getPrinFixInfoSchSvc", api_key, params)


def fetch_bond_erly_red_info(api_key, isin):
    params = {"isin": isin}
    return fetch_all_pages("/getBondErlyRedInfo", api_key, params)

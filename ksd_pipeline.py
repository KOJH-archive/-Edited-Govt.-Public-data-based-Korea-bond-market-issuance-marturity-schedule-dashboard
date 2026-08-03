import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import csv
from datetime import datetime

def load_api_key(env_path="Public.env"):
    """환경변수 파일에서 API 키를 로드합니다."""
    if not os.path.exists(env_path):
        raise FileNotFoundError(f"{env_path} 파일이 존재하지 않습니다.")
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        if '=' in content:
            return content.split('=', 1)[1].strip()
        return content

def fetch_bond_data(api_key, operation, extra_params):
    """
    예결원 채권정보서비스 API를 호출하여 데이터를 리스트 형태로 반환합니다.
    """
    base_url = "https://apis.data.go.kr/B552481/BondSvc"
    
    # 공통 필수 파라미터
    params = {
        'pageNo': '1',
        'numOfRows': '100',
    }
    # 추가 조회 파라미터 병합
    params.update(extra_params)
    
    query_string = urllib.parse.urlencode(params)
    url = f"{base_url}{operation}?serviceKey={api_key}&{query_string}"
    
    print(f"🔄 데이터 수집 중... (엔드포인트: {operation})")
    print(f"   파라미터: {extra_params}")
    
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        xml_data = response.read().decode('utf-8')
        
    root = ET.fromstring(xml_data)
    result_code = root.find('.//resultCode')
    result_msg = root.find('.//resultMsg')
    
    if result_code is not None and result_code.text == '00':
        items = root.findall('.//item')
        parsed_data = []
        for item in items:
            row = {}
            for child in item:
                row[child.tag] = child.text
            parsed_data.append(row)
        return parsed_data
    else:
        msg = result_msg.text if result_msg is not None else "Unknown Error"
        if root.find('.//returnAuthMsg') is not None:
            msg = root.find('.//returnAuthMsg').text
        raise Exception(f"API Error [{result_code.text if result_code is not None else 'N/A'}]: {msg}")

def save_to_csv(data, filename):
    """
    수집된 딕셔너리 리스트를 CSV 파일로 저장합니다.
    """
    if not data:
        print("⚠️ 수집된 데이터가 없어 저장하지 않습니다.")
        return
        
    # 데이터의 첫 번째 행의 키들을 컬럼명으로 사용
    fieldnames = list(data[0].keys())
    
    # Excel에서 한글이 깨지지 않도록 utf-8-sig 인코딩 사용
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
        
    print(f"✅ 데이터 저장 완료: {filename} (총 {len(data)}건)")

if __name__ == "__main__":
    try:
        api_key = load_api_key("Public.env")
        
        # [수정 필요] 
        # 공공데이터포털의 기술문서(엑셀/PDF)를 확인하여 실제 요구하는 조회조건 파라미터를 입력하세요.
        # 예: searchBgnDe, searchEndDe, basYm, baseDate 등
        request_parameters = {
            'basYm': '202312' # 임시 파라미터 (오류 발생 시 기술문서 참고하여 변경)
        }
        
        # 데이터 수집 (예시: 채권 종류별 기관결제대금 현황)
        operation = "/getBondKindInsetlStat"
        data = fetch_bond_data(api_key, operation, request_parameters)
        
        # CSV 저장
        timestamp = datetime.now().strftime("%Y%md_%H%M%S")
        filename = f"bond_insetl_stat_{timestamp}.csv"
        save_to_csv(data, filename)
        
    except Exception as e:
        print(f"\n❌ 파이프라인 실행 실패: {e}")
        print("💡 안내: NO_MANDATORY_REQUEST_PARAMETER_ERROR 에러가 발생한 경우,")
        print("   스크립트 내의 'request_parameters' 에 필수 조회 조건(예: 기준일자)이 빠졌거나 이름이 틀린 것입니다.")
        print("   공공데이터포털 해당 API 페이지의 '활용가이드(기술문서)'를 확인하여 파라미터명을 정확히 수정해 주세요.")

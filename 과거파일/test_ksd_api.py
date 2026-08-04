import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

def load_api_key(env_path):
    if not os.path.exists(env_path):
        print(f"Error: {env_path} 파일을 찾을 수 없습니다.")
        return None
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        if '=' in content:
            return content.split('=', 1)[1].strip()
        return content

def fetch_bond_info(api_key):
    # 테스트할 엔드포인트: 채권 종류별 기관결제대금 현황 조회
    base_url = "https://apis.data.go.kr/B552481/BondSvc"
    operation = "/getBondKindInsetlStat"
    
    # 파라미터 설정 (필수 파라미터로 basYm 기준년월 추가)
    params = {
        'pageNo': '1',
        'numOfRows': '5',
        'basYm': '202312'
    }
    
    query_string = urllib.parse.urlencode(params)
    url = f"{base_url}{operation}?serviceKey={api_key}&{query_string}"
    
    print("API Request: getBondKindInsetlStat (basYm=202312)")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            xml_data = response.read().decode('utf-8')
            
            print("\n[XML Response]")
            print("-" * 50)
            print(xml_data[:500])
            if len(xml_data) > 500:
                print("...")
            print("-" * 50)
            
            try:
                root = ET.fromstring(xml_data)
                result_code = root.find('.//resultCode')
                result_msg = root.find('.//resultMsg')
                
                if result_code is not None and result_code.text == '00':
                    print("\n[SUCCESS] API Call Successful!")
                    items = root.findall('.//item')
                    print(f"Items found: {len(items)}")
                    for idx, item in enumerate(items, 1):
                        print(f"\n[Item {idx}]")
                        for child in item:
                            print(f"- {child.tag}: {child.text}")
                else:
                    print(f"\n[FAILED] API Error")
                    if result_msg is not None:
                        print(f"Message: {result_msg.text}")
                    elif root.find('.//returnAuthMsg') is not None:
                        print(f"Auth Error: {root.find('.//returnAuthMsg').text}")
            except ET.ParseError:
                print("\n[ERROR] XML Parse Error")
                
    except Exception as e:
        print(f"\n[ERROR] Request Failed: {e}")

if __name__ == "__main__":
    env_file = "Public.env"
    key = load_api_key(env_file)
    if key:
        fetch_bond_info(key)

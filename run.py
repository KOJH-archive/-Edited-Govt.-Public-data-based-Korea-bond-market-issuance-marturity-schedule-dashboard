"""
채권 수급 분석 시스템 마스터 마스터 실행 스크립트 (run.py)
- 데이터 파이프라인(ETL) 실행
- Streamlit 웹 대시보드 자동 구동
"""
import os
import sys
import subprocess

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    project_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(project_dir, ".venv", "Scripts", "python.exe")
    venv_streamlit = os.path.join(project_dir, ".venv", "Scripts", "streamlit.exe")

    if not os.path.exists(venv_python):
        venv_python = sys.executable  # 가상환경이 없으면 현재 파이썬 사용

    print("=" * 60)
    print("📊 한국예탁결제원 공공데이터 채권 수급 분석 시스템")
    print("=" * 60)

    # 1. ETL 실행
    print("\n[Step 1] 데이터 수집 및 DB 적재(ETL) 실행...")
    try:
        subprocess.run([venv_python, "etl.py"], check=True)
    except Exception as e:
        print(f"⚠️ ETL 실행 중 경고/에러: {e}")

    # 2. Streamlit 대시보드 구동
    print("\n[Step 2] Streamlit 웹 대시보드 구동...")
    print("🔗 웹 브라우저가 생성됩니다. (종료: Ctrl+C)\n")
    try:
        subprocess.run([venv_streamlit, "run", "app.py"], check=True)
    except KeyboardInterrupt:
        print("\n프로그램이 종료되었습니다.")

if __name__ == "__main__":
    main()

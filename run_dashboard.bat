@echo off
chcp 65001 > nul
title 채권 수급 분석 대시보드 실행기

echo ============================================================
echo   📊 한국예탁결제원 공공데이터 기반 채권 수급 대시보드
echo ============================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] 가상환경 생성 중...
    uv venv .venv
    call .venv\Scripts\activate
    uv pip install -r requirements.txt setuptools
) else (
    echo [1/3] 가상환경 확인 완료 (.venv)
)

echo.
echo [2/3] ETL 데이터 파이프라인 실행 중 (2023~2026 수집)...
.venv\Scripts\python.exe etl.py

echo.
echo [3/3] Streamlit 대시보드 실행 중...
echo 웹 브라우저가 자동으로 열립니다. (종료하려면 Ctrl+C)
echo ============================================================
.venv\Scripts\streamlit run app.py

pause

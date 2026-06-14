@echo off
chcp 65001 >nul
echo ============================================
echo   智能广告投放系统 · Ad Placement Platform
echo ============================================
echo.

cd /d "%~dp0"

echo [1/3] Installing Python dependencies...
pip install -r backend\requirements.txt -q
if %errorlevel% neq 0 (
    echo ERROR: pip install failed. Check Python 3.11+.
    pause
    exit /b 1
)

echo [2/3] Installing frontend dependencies...
cd frontend
call npm install --silent
if %errorlevel% neq 0 (
    echo ERROR: npm install failed. Check Node.js 18+.
    cd ..
    pause
    exit /b 1
)

cd ..

echo [3/3] Starting backend + frontend...
echo.
echo Backend:  http://localhost:8000
echo Swagger:  http://localhost:8000/api/docs
echo Frontend: http://localhost:5173
echo Bigscreen: http://localhost:5173/bigscreen
echo.
echo Press Ctrl+C to stop all services.
echo.

start "Ad Platform Backend" cmd /c "python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"
start "Ad Platform Frontend" cmd /c "cd frontend && npx vite --host 0.0.0.0 --port 5173"

echo Services started! Opening browser...
timeout /t 5 /nobreak >nul
start http://localhost:5173
pause

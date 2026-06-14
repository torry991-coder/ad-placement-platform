#!/usr/bin/env bash
set -e

echo "============================================"
echo "  智能广告投放系统 · Ad Placement Platform"
echo "============================================"
echo ""

cd "$(dirname "$0")"

echo "[1/3] Installing Python dependencies..."
pip install -r backend/requirements.txt -q

echo "[2/3] Installing frontend dependencies..."
cd frontend && npm install --silent && cd ..

echo "[3/3] Starting backend + frontend..."
echo ""
echo "  Backend:   http://localhost:8000"
echo "  Swagger:   http://localhost:8000/api/docs"
echo "  Frontend:  http://localhost:5173"
echo "  Bigscreen: http://localhost:5173/bigscreen"
echo ""
echo "  Press Ctrl+C to stop all services."
echo ""

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

cd frontend && npx vite --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT

sleep 3
if command -v xdg-open &>/dev/null; then
    xdg-open http://localhost:5173
elif command -v open &>/dev/null; then
    open http://localhost:5173
fi

wait

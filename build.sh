#!/usr/bin/env bash
# Build script for Render deployment
# 1. Install Python deps
# 2. Build Next.js frontend (static export -> frontend-next/out/)
set -e

echo "=== Installing Python dependencies ==="
pip install -r requirements.txt

echo "=== Installing Node.js & building Next.js frontend ==="
cd frontend-next
npm install
npm run build
cd ..

echo "=== Build complete ==="
echo "Static export at frontend-next/out/"
ls frontend-next/out/ 2>/dev/null || echo "WARNING: out/ not found"

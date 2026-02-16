#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

cd caza_2026_v2_frontend
npm install
npm run build
cd ..

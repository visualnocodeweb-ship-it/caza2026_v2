#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

cd caza_2026_v2_frontend
npm install
# Node 22 rompe eslint-config-react-app; desactivar ESLint en build de prod
DISABLE_ESLINT_PLUGIN=true CI=false npm run build
cd ..

#!/usr/bin/env bash
# Rebuild everything from scratch: data -> validation -> analysis -> Power BI export -> findings -> tests (-> notebooks)
set -euo pipefail
cd "$(dirname "$0")"
python scripts/00_area_selection.py
python scripts/01_generate_data.py
python scripts/02_cleaning_validation.py
python scripts/03_eda.py
python scripts/04_advanced_analytics.py
python scripts/05_export_powerbi.py
python scripts/07_make_templates.py
python scripts/08_build_findings.py
python scripts/06_tests.py
if [[ "${1:-}" == "--notebooks" ]]; then python scripts/build_notebooks.py; fi
echo "Done."

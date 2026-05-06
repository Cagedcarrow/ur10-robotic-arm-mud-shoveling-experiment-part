#!/usr/bin/env bash
set -euo pipefail
cd /root/ur10_ws/src/experiment_data_recorder
python3 docs/reports/scripts/build_response_surface_docx_report.py

#!/usr/bin/env bash
# Send approved drafts during Toronto B2B hours.
# Cron: runs every hour 12:00-17:00 UTC = 08:00-13:00 EDT.
# Each tick releases up to 5 approved emails. Caps out at OUTREACH_DAILY_CAP=30.
set -euo pipefail
cd /home/support/glitch-grow-sales-agent
source .venv/bin/activate
exec env PYTHONPATH=src python3 -m sales_agent.mail.run_send_approved --limit 5

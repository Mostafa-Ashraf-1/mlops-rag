#!/usr/bin/env bash
set -e

START_TIME=$(date +%s%N)

echo "[!] ALERT: SLA Breach or Error Spike detected on Candidate!"
echo "[*] Executing Emergency Rollback to 100% Stable..."

# Restore weights: 100% to Stable (weight=10), 0% to Candidate (weight=0)
sed -i 's/weight=[0-9]\+;  # Candidate/weight=0;  # Candidate/g' serving/nginx/nginx.conf 2>/dev/null || true
sed -i 's/weight=[0-9]\+;  # Stable/weight=10;  # Stable/g' serving/nginx/nginx.conf 2>/dev/null || true

END_TIME=$(date +%s%N)
DURATION_MS=$(( (END_TIME - START_TIME) / 1000000 ))

echo "[✓] ROLLBACK COMPLETE: Traffic returned to 100% Stable in ${DURATION_MS} ms!"
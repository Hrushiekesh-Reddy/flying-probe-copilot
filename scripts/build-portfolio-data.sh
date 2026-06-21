#!/usr/bin/env bash
# scripts/build-portfolio-data.sh
#
# Build a deterministic portfolio dataset for the README hero-strip screenshots
# and live demos. Three board profiles × 300 panels × a 60-day window, default
# `random` fault profile, fixed --seed=42 so re-runs are byte-identical.
#
# Output: data/db/sample.duckdb (gitignored; matches the dashboard's default).
# Intermediate run dirs under data/synthetic/ are also gitignored.
#
# Usage:
#   bash scripts/build-portfolio-data.sh
#
# Requires: uv installed, project deps synced (`uv sync`).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DB="data/db/sample.duckdb"
# Panel serials are SYN-YYYYWww-NNNNN — uniqueness is per (ISO-week, sequence),
# so multiple profiles sharing a week collide on ingest. We give each profile
# its own non-overlapping 60-day window (~8.5 ISO weeks) so serials never
# collide while the three batches still cover a realistic 6-month production
# horizon end-to-end.
# (profile, seed, start-date, end-date)
BATCHES=(
  "small:42:2026-04-15:2026-06-14"
  "medium:142:2026-06-15:2026-08-14"
  "large:242:2026-08-15:2026-10-14"
)

mkdir -p data/synthetic data/db

# Wipe any prior portfolio DB so re-runs land in a clean state.
rm -f "$DB"

for ENTRY in "${BATCHES[@]}"; do
  IFS=':' read -r PROFILE SEED START END <<< "$ENTRY"
  echo ">>> Generating $PROFILE batch (300 panels, $START -> $END, seed=$SEED)..."
  uv run generator \
    --board-profile="$PROFILE" \
    --count=300 \
    --start-date="$START" \
    --end-date="$END" \
    --seed="$SEED" \
    --out=data/synthetic

  RUN_DIR="$(ls -dt data/synthetic/run_* | head -1)"
  echo ">>> Ingesting $RUN_DIR -> $DB ..."
  uv run parser --input="$RUN_DIR" --db="$DB"
  echo ""
done

echo "✓ Portfolio dataset built at $DB"
echo "  Launch dashboard with: uv run streamlit run src/flying_probe_copilot/ui/app.py"

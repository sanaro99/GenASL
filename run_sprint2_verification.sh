#!/usr/bin/env bash
# Sprint 2 Verification Script — GenASL
# Run from project root:  bash run_sprint2_verification.sh

set -euo pipefail
FAILED=0

pass() { printf "  \033[32m[PASS]\033[0m %s\n" "$1"; }
fail() { printf "  \033[31m[FAIL]\033[0m %s\n" "$1"; FAILED=$((FAILED+1)); }

echo ""
echo "========================================"
echo "  GenASL — Sprint 2 Verification"
echo "========================================"
echo ""

# 1. Final clips
echo "1. Asset files"
COUNT=$(find assets/final -maxdepth 1 -name '*.mp4' -type f | wc -l)
[ "$COUNT" -eq 50 ] && pass "50 clips in assets/final/" || fail "Expected 50 clips, found $COUNT"

RAW_COUNT=$(find assets/raw -maxdepth 1 -name '*.mp4' -type f 2>/dev/null | wc -l)
[ "$RAW_COUNT" -eq 0 ] && pass "raw/ is empty" || fail "raw/ has $RAW_COUNT .mp4 files"

TRIM_COUNT=$(find assets/trimmed -maxdepth 1 -name '*.mp4' -type f 2>/dev/null | wc -l)
[ "$TRIM_COUNT" -eq 0 ] && pass "trimmed/ is empty" || fail "trimmed/ has $TRIM_COUNT .mp4 files"

# 2. Manifest
echo ""
echo "2. Asset manifest"
[ -f assets/asset_manifest_v1.json ] && pass "asset_manifest_v1.json exists" || fail "manifest missing"

MANIFEST_COUNT=$(python3 -c "import json; m=json.load(open('assets/asset_manifest_v1.json')); print(m['total_assets'])")
[ "$MANIFEST_COUNT" -eq 50 ] && pass "manifest has 50 entries" || fail "manifest has $MANIFEST_COUNT entries"

# 3. Config
echo ""
echo "3. Config"
grep -q "asset_manifest" config.yaml && pass "config.yaml references asset_manifest" || fail "asset_manifest missing from config"

# 4. Docs
echo ""
echo "4. Docs"
[ -f docs/governance_notes.md ] && pass "governance_notes.md exists" || fail "governance_notes.md missing"
[ -f docs/wlasl_coverage_report.txt ] && pass "wlasl_coverage_report.txt exists" || fail "wlasl_coverage_report.txt missing"
[ -f docs/asset_qa_notes.md ] && pass "asset_qa_notes.md exists" || fail "asset_qa_notes.md missing"

# 5. Tests
echo ""
echo "5. Pytest"
if .venv/bin/python -m pytest tests/ -v --tb=short; then
    pass "All pytest tests passed"
else
    fail "pytest failed"
fi

# Summary
echo ""
echo "========================================"
if [ "$FAILED" -eq 0 ]; then
    printf "  \033[32mALL CHECKS PASSED\033[0m\n"
else
    printf "  \033[31m%d CHECK(S) FAILED\033[0m\n" "$FAILED"
fi
echo "========================================"
echo ""

exit "$FAILED"

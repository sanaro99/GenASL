#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# GenASL — Sprint 1 Verification Script
# ──────────────────────────────────────────────────────────────
set -e

STEP=""

fail() {
    echo ""
    echo "❌ Sprint 1 verification FAILED at step: $STEP"
    exit 1
}

trap fail ERR

# ── Step 1: Install dependencies ──────────────────────────────
STEP="pip install -r requirements.txt"
echo "▶ Step 1: $STEP"
python -m pip install -r requirements.txt
echo "  ✔ Dependencies installed"
echo ""

# ── Step 2: Build FAISS index ─────────────────────────────────
STEP="python src/matcher/build_index.py"
echo "▶ Step 2: $STEP"
python src/matcher/build_index.py
echo "  ✔ FAISS index built"
echo ""

# ── Step 3: Run test suite ────────────────────────────────────
STEP="pytest tests/ -v --tb=short"
echo "▶ Step 3: $STEP"
python -m pytest tests/ -v --tb=short
echo "  ✔ All tests passed"
echo ""

# ── Step 4: Run pipeline on sample video ──────────────────────
STEP="python src/pipeline/run_pipeline.py E-gGacOpjCA"
echo "▶ Step 4: $STEP"
python src/pipeline/run_pipeline.py E-gGacOpjCA
echo "  ✔ Pipeline executed"
echo ""

# ── Done ──────────────────────────────────────────────────────
echo "✅ Sprint 1 verification complete"

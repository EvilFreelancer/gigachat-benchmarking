#!/usr/bin/env bash
# Run SWE-bench Lite evaluation for GigaChat 3.1 10B predictions.
# Run this script from the SWE-bench root directory after inference is complete.
#
# Usage: bash scripts/run_evaluation.sh [max_workers]

set -e

PREDICTIONS="${1:-predictions/gigachat31_10b__swe-bench_lite__test.jsonl}"
RUN_ID="gigachat31-10b-$(date +%Y%m%d-%H%M%S)"
MAX_WORKERS="${2:-4}"

echo "=== SWE-bench Lite Evaluation ==="
echo "Predictions: $PREDICTIONS"
echo "Run ID:      $RUN_ID"
echo "Max workers: $MAX_WORKERS"
echo ""

if [ ! -f "$PREDICTIONS" ]; then
    echo "ERROR: Predictions file not found: $PREDICTIONS"
    echo "Run run_gigachat_inference.py first."
    exit 1
fi

PRED_COUNT=$(wc -l < "$PREDICTIONS")
echo "Predictions: $PRED_COUNT instances"

if [ "$PRED_COUNT" -lt 300 ]; then
    echo "WARNING: Expected 300 predictions, got $PRED_COUNT (inference may not be complete)"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] || exit 1
fi

mkdir -p logs

.venv/bin/python3 -m swebench.harness.run_evaluation \
    --dataset_name princeton-nlp/SWE-bench_Lite \
    --predictions_path "$PREDICTIONS" \
    --max_workers "$MAX_WORKERS" \
    --run_id "$RUN_ID" \
    --cache_level env \
    2>&1 | tee "logs/evaluation_${RUN_ID}.log"

echo ""
echo "=== Done ==="
echo "Results: evaluation_results/"
echo "Log:     logs/evaluation_${RUN_ID}.log"

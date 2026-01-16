#!/bin/bash
# Continuous training loop for Signamancy farm agent
# Runs CEM + value network training until manually stopped
# Tracks best results and saves checkpoints

cd "$(dirname "$0")"

# Configuration
MAX_PASSES=${1:-100}  # Default 100 passes, or pass as argument
LOG_FILE="training_results.log"

echo "=== Signamancy Training Loop ===" | tee "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"
echo "Max passes: $MAX_PASSES" | tee -a "$LOG_FILE"

# Get initial checkpoint state
INIT_SURVIVAL=$(python -c "
import torch
vn = torch.load('value_net.pt', map_location='cpu', weights_only=False)
print(f'{vn.get(\"best_survival\", 0)*100:.1f}')
" 2>/dev/null)
echo "Initial best_survival: ${INIT_SURVIVAL}%" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Track session stats
SESSION_BEST_VALID=0
SESSION_BEST_PASS=0
NEW_BESTS=0

for i in $(seq 1 $MAX_PASSES); do
    echo -n "Pass $i/$MAX_PASSES: " | tee -a "$LOG_FILE"

    # Run training and capture output
    OUTPUT=$(bash run_agent.sh 2>&1)

    # Extract step=800 line and parse with Python for reliability
    METRICS=$(echo "$OUTPUT" | python -c "
import sys
import re
text = sys.stdin.read()
# Find step=800 line
match = re.search(r'step=800.*valid=(\d+)/(\d+).*score_mean=([0-9.]+)', text)
if match:
    valid, total, score = match.groups()
    pct = float(valid) / float(total) * 100
    print(f'{valid}|{pct:.1f}|{score}')
else:
    print('0|0|0')
# Check for NEW BEST
if 'NEW BEST' in text:
    print('NEWBEST')
" 2>/dev/null)

    # Parse metrics
    VALID=$(echo "$METRICS" | head -1 | cut -d'|' -f1)
    SURVIVAL_PCT=$(echo "$METRICS" | head -1 | cut -d'|' -f2)
    SCORE=$(echo "$METRICS" | head -1 | cut -d'|' -f3)
    IS_NEW_BEST=$(echo "$METRICS" | grep -c "NEWBEST")

    # Update session best
    if [ -n "$VALID" ] && [ "$VALID" -gt "$SESSION_BEST_VALID" ] 2>/dev/null; then
        SESSION_BEST_VALID=$VALID
        SESSION_BEST_PASS=$i
    fi

    # Log compact result
    echo "valid=$VALID/4096 (${SURVIVAL_PCT}%) score=${SCORE}" | tee -a "$LOG_FILE"

    if [ "$IS_NEW_BEST" -gt 0 ]; then
        echo "  ^^^ NEW CHECKPOINT BEST! ^^^" | tee -a "$LOG_FILE"
        NEW_BESTS=$((NEW_BESTS + 1))
    fi

    # Progress report every 10 passes
    if [ $((i % 10)) -eq 0 ]; then
        echo "" | tee -a "$LOG_FILE"
        echo "--- Progress @ Pass $i ---" | tee -a "$LOG_FILE"
        echo "Session best: $SESSION_BEST_VALID/4096 (Pass $SESSION_BEST_PASS)" | tee -a "$LOG_FILE"
        echo "New checkpoints saved: $NEW_BESTS" | tee -a "$LOG_FILE"
        python -c "
import torch
vn = torch.load('value_net.pt', map_location='cpu', weights_only=False)
print(f'Checkpoint: {vn.get(\"best_survival\", 0)*100:.1f}% survival, {vn.get(\"best_score\", 0):.1f} score')
" 2>/dev/null | tee -a "$LOG_FILE"
        echo "" | tee -a "$LOG_FILE"
    fi
done

echo "" | tee -a "$LOG_FILE"
echo "=== Training Complete ===" | tee -a "$LOG_FILE"
echo "Finished: $(date)" | tee -a "$LOG_FILE"
echo "Passes: $MAX_PASSES | New bests: $NEW_BESTS | Session peak: $SESSION_BEST_VALID/4096 (Pass $SESSION_BEST_PASS)" | tee -a "$LOG_FILE"
python -c "
import torch
vn = torch.load('value_net.pt', map_location='cpu', weights_only=False)
print(f'Final checkpoint: {vn.get(\"best_survival\", 0)*100:.1f}% survival, {vn.get(\"best_score\", 0):.1f} score')
" 2>/dev/null | tee -a "$LOG_FILE"

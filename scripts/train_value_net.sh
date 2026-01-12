#!/bin/bash
# Extended training script for value network
# Tracks metrics over multiple passes

PASSES=${1:-20}  # Default 20 passes, or pass count as argument
LOG_FILE="training_log.csv"

echo "Starting extended training run - $PASSES passes with metrics tracking"
echo "Pass,Survival,SurvivalPct,Crown,MaxScore,Loss,BestSurvival" > "$LOG_FILE"

cd "$(dirname "$0")/.."

for i in $(seq 1 $PASSES); do
    result=$(bash run_agent.sh 2>&1)

    # Extract metrics using grep/sed (portable)
    survival=$(echo "$result" | grep "FINAL.*step=800" | sed -n 's/.*valid=\([0-9]*\).*/\1/p')
    crown=$(echo "$result" | grep "FINAL.*step=800" | sed -n 's/.*👑\([0-9.]*\).*/\1/p')
    maxscore=$(echo "$result" | grep "FINAL.*step=800" | sed -n 's/.*score_max=\([0-9.]*\).*/\1/p')
    loss=$(echo "$result" | grep "ValueNet.*Final" | sed -n 's/.*Loss: \([0-9.]*\).*/\1/p')
    best=$(echo "$result" | grep "best_survival" | sed -n 's/.*best_survival=\([0-9.]*\)%.*/\1/p')

    # Calculate survival percentage
    if [ -n "$survival" ]; then
        survpct=$(echo "scale=2; $survival * 100 / 4096" | bc)
    else
        survpct="N/A"
        survival="N/A"
    fi

    echo "$i,$survival,$survpct,$crown,$maxscore,$loss,$best" >> "$LOG_FILE"
    echo "Pass $i/$PASSES: Survival=$survival ($survpct%) Crown=$crown MaxScore=$maxscore Loss=$loss Best=$best%"
done

echo ""
echo "Training complete. Results saved to $LOG_FILE"
echo ""
echo "=== Summary ==="
tail -5 "$LOG_FILE"

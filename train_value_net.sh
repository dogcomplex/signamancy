#!/bin/bash
# Training script for value network
# Usage: bash train_value_net.sh [num_passes]

cd "C:/Users/devil/.claude-worktrees/signamancy/charming-mahavira"

NUM_PASSES=${1:-10}

echo "=== Training value network for $NUM_PASSES passes ==="

for i in $(seq 1 $NUM_PASSES); do
    echo "--- Pass $i/$NUM_PASSES ---"
    bash run_agent.sh 2>&1 | grep -E "(ValueNet|FINAL.*step=800|Buffer|Loss|👑)"
done

echo "=== Training complete ==="

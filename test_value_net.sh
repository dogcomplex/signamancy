#!/bin/bash
# Test script for value network - runs evaluation passes
# Usage: bash test_value_net.sh [num_passes]

cd "C:/Users/devil/.claude-worktrees/signamancy/charming-mahavira"

NUM_PASSES=${1:-5}

echo "=== Testing value network for $NUM_PASSES passes ==="

for i in $(seq 1 $NUM_PASSES); do
    echo "--- Test $i/$NUM_PASSES ---"
    bash run_agent.sh 2>&1 | grep -E "(ValueNet|FINAL.*step=800|👑|🏦)"
done

echo "=== Testing complete ==="

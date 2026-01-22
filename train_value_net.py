#!/usr/bin/env python3
"""
Extended value network training with checkpoint saving.
Runs multiple passes, saving best checkpoint when peak performance is reached.
"""
import os
import subprocess
import sys
import re

def run_training(num_passes: int = 50):
    """Run extended training with checkpoint saving."""

    # Load agent_config.env
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_config.env")
    env = os.environ.copy()
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    env[key] = value

    # Override training settings
    env["VALUE_NET_TRAIN"] = "1"
    env["VALUE_NET_ENABLED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"  # Force UTF-8 encoding for subprocess

    print(f"=== Training value network for {num_passes} passes ===")

    best_score = 0.0
    best_survival = 0.0
    best_pass = 0

    for i in range(num_passes):
        print(f"--- Pass {i+1}/{num_passes} ---")

        # Run training pass with UTF-8 mode
        result = subprocess.run(
            [sys.executable, "-X", "utf8", "-m", "signamancy.agent.run_agent_generic"],
            env=env,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        # Print output
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        # Parse final stats from output
        final_match = re.search(r'\[FINAL\].*valid=(\d+)/(\d+).*score_mean=([0-9.]+)', result.stdout)
        if final_match:
            valid = int(final_match.group(1))
            total = int(final_match.group(2))
            score = float(final_match.group(3))
            survival = valid / total if total > 0 else 0.0

            if survival > best_survival or (survival == best_survival and score > best_score):
                best_score = score
                best_survival = survival
                best_pass = i + 1
                print(f"[TrainLoop] NEW BEST at pass {best_pass}: score={best_score:.1f}, survival={best_survival:.1%}")

        # Check for NEW BEST message from value trainer
        if "[ValueNet] NEW BEST" in result.stdout:
            print(f"[TrainLoop] Best checkpoint saved during pass {i+1}")

    print(f"\n=== Training complete ===")
    print(f"Best performance: pass {best_pass}, score={best_score:.1f}, survival={best_survival:.1%}")
    print(f"Best checkpoint saved to: value_net_best.pt")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--passes", type=int, default=50, help="Number of training passes")
    args = parser.parse_args()

    run_training(args.passes)

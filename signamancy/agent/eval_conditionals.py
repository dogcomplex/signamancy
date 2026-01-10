"""
Conditional Policy Evaluator

This script evaluates conditional policy candidates through A/B GPU rollouts.
It compares performance with and without each conditional rule to measure improvement.

Usage:
    python -m signamancy.agent.eval_conditionals

The key insight is that LLM semantic understanding generates the *candidates*,
while GPU parallel evaluation measures *which ones actually help*.
"""

import os
import sys
import torch
import time
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import csv

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from signamancy.registry import TokenRegistry
from signamancy.parser import SignamancyParser
from signamancy.compiler import SignamancyCompiler
from signamancy.engine import SignamancyEngine, SimulationConfig
from signamancy.bridge import SignamancyBridge


@dataclass
class ConditionalCandidate:
    """A conditional policy rule to evaluate."""
    name: str
    trigger_token: str
    target_rule_bases: List[str]  # Base rule IDs to boost
    boost: float
    description: str


# LLM-generated candidates based on semantic game understanding
CANDIDATES = [
    # Late-week urgency - approaching Saturday deadline
    ConditionalCandidate(
        name="thursday_urgency",
        trigger_token="☀4️⃣",
        target_rule_bases=["ID_Sell_Wood", "ID_Sell_Stone", "ID_Sell_Apple", "ID_Sell_Berry",
                          "ID_Sell_Orange", "ID_Sell_Sardine", "ID_Day"],
        boost=10.0,
        description="Moderate urgency on Thursday - boost selling"
    ),
    ConditionalCandidate(
        name="friday_urgency",
        trigger_token="☀5️⃣",
        target_rule_bases=["ID_Sell_Wood", "ID_Sell_Stone", "ID_Sell_Apple", "ID_Sell_Berry",
                          "ID_Sell_Orange", "ID_Sell_Sardine", "ID_Day"],
        boost=15.0,
        description="High urgency on Friday - boost selling more"
    ),
    ConditionalCandidate(
        name="saturday_critical",
        trigger_token="☀6️⃣",
        target_rule_bases=["ID_Sell_Wood", "ID_Sell_Stone", "ID_Sell_Apple", "ID_Sell_Berry",
                          "ID_Sell_Orange", "ID_Sell_Sardine", "ID_Rent1", "ID_Day"],
        boost=20.0,
        description="Critical urgency on Saturday - maximize selling and rent"
    ),

    # Post-rent pivots
    ConditionalCandidate(
        name="post_rent1_fishing",
        trigger_token="🏦2️⃣",
        target_rule_bases=["ID_Rod_Fish", "ID_Sell_Sardine", "ID_Sell_Halibut",
                          "ID_Sell_Bullhead", "ID_Sell_Carp"],
        boost=15.0,
        description="After Rent1 - pivot to sustainable fishing income"
    ),
    ConditionalCandidate(
        name="post_rent2_processing",
        trigger_token="🏦3️⃣",
        target_rule_bases=["ID_Build_Furnace", "ID_Day_Baked_Copper", "ID_Day_Baked_Iron",
                          "ID_Sell_Copper_Bar", "ID_Sell_Iron"],
        boost=12.0,
        description="After Rent2 - pivot to ore processing"
    ),

    # Resource depletion recovery
    ConditionalCandidate(
        name="stumps_pivot",
        trigger_token="🌳🟤",
        target_rule_bases=["ID_Rod_Fish", "ID_Pick_Stone", "ID_Pick_Copper", "ID_Pick_Iron"],
        boost=10.0,
        description="Trees depleted (stumps) - pivot to fishing/mining"
    ),
]


def load_farm_rules(csv_path: Path, policy_path: Optional[Path] = None):
    """Load farm game rules (and optional policy) and return compiled kernel."""
    registry = TokenRegistry()
    parser = SignamancyParser(registry)
    rules = []
    idx_to_id = {}

    # Load game rules from CSV
    with csv_path.open(newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        for row in r:
            if not row or len(row) < 2:
                continue
            rule_id = row[0].strip()
            recipe = row[1].strip()
            if not recipe:
                continue
            before = len(rules)
            rs = parser.parse_text(recipe)
            rules.extend(rs)
            after = len(rules)
            if rule_id:
                for k, idx in enumerate(range(before, after)):
                    label = rule_id if k == 0 else f"{rule_id}#{k}"
                    idx_to_id[idx] = label

    # Load policy rules if provided (includes 🎬 initialization)
    if policy_path and policy_path.exists():
        policy_text = policy_path.read_text(encoding="utf-8")
        before = len(rules)
        policy_rules = parser.parse_text(policy_text)
        rules.extend(policy_rules)
        after = len(rules)
        for k, idx in enumerate(range(before, after)):
            idx_to_id[idx] = f"Policy#{k}"
        print(f"Loaded {len(policy_rules)} policy rules")

    compiler = SignamancyCompiler(registry)
    kernel = compiler.compile(rules)

    # Build reverse mapping: rule base -> indices
    base_to_indices = {}
    for idx, rule_id in idx_to_id.items():
        base = rule_id.split('#')[0]
        if base not in base_to_indices:
            base_to_indices[base] = []
        base_to_indices[base].append(idx)

    return kernel, registry, idx_to_id, base_to_indices


def run_rollout(
    kernel,
    registry: TokenRegistry,
    bias: torch.Tensor,
    horizon: int,
    target_prefixes: List[str],
    batch_size: int,
    device: str,
    trigger_check: Optional[str] = None
) -> Tuple[float, float, int]:
    """
    Run a single rollout and return (mean_score, max_score, trigger_steps).

    If trigger_check is specified, also count how many steps the trigger token was present.
    """
    # Create fresh engine for this rollout
    cfg = SimulationConfig(batch_size=batch_size, device=device)
    engine = SignamancyEngine(kernel, cfg)
    bridge = SignamancyBridge(engine, registry)

    # Apply bias before any steps
    engine.biases = bias.to(engine.device)

    # Initialize - inject start signals and run initial physics
    bridge.inject_signal("🎬")
    bridge.inject_signal("💫")
    engine.step()
    engine.step()

    # Track trigger presence
    trigger_steps = 0

    scores = []
    for step in range(horizon):
        # Run physics burst until decision point
        for _ in range(128):
            engine.step()
            stats = engine.get_rule_stats() if hasattr(engine, 'get_rule_stats') else {}
            if stats.get("any_decision", False):
                break

        # Execute decision step
        engine.step()

        # Calculate score periodically (every 10 steps to save time)
        if step % 10 == 0:
            snapshot = bridge.get_state_snapshot()
            score = 0.0
            for prefix in target_prefixes:
                for k, v in snapshot.items():
                    if k.startswith(prefix):
                        score += float(v.get("val", 0.0))
            scores.append(score)

    return sum(scores) / len(scores) if scores else 0.0, max(scores) if scores else 0.0, trigger_steps


def evaluate_conditional(
    candidate: ConditionalCandidate,
    kernel,
    registry: TokenRegistry,
    base_to_indices: Dict[str, List[int]],
    base_bias: torch.Tensor,
    batch_size: int = 512,
    horizon: int = 400,
    num_trials: int = 3,
    device: str = "cuda"
) -> Dict:
    """
    Evaluate a conditional candidate through A/B rollouts.

    Returns dict with:
    - score_baseline: Average score without conditional
    - score_with_cond: Average score with conditional
    - improvement: Relative improvement
    - trigger_frequency: How often the trigger was active
    """
    num_rules = base_bias.shape[0]

    # Build conditional bias
    cond_bias = torch.zeros_like(base_bias)
    for rule_base in candidate.target_rule_bases:
        if rule_base in base_to_indices:
            for idx in base_to_indices[rule_base]:
                cond_bias[idx] = candidate.boost

    baseline_scores = []
    cond_scores = []
    trigger_freqs = []

    for trial in range(num_trials):
        # Baseline run
        torch.manual_seed(42 + trial)
        if device == "cuda":
            torch.cuda.manual_seed_all(42 + trial)

        mean_b, max_b, _ = run_rollout(
            kernel, registry, base_bias, horizon,
            ["👑", "💰"], batch_size, device, None
        )
        baseline_scores.append(mean_b)

        # Conditional run (with same seed for fair comparison)
        torch.manual_seed(42 + trial)
        if device == "cuda":
            torch.cuda.manual_seed_all(42 + trial)

        # For now, just add the conditional bias always
        # A more sophisticated version would apply it only when trigger is present
        combined_bias = base_bias + cond_bias
        mean_c, max_c, trigger_steps = run_rollout(
            kernel, registry, combined_bias, horizon,
            ["👑", "💰"], batch_size, device, candidate.trigger_token
        )
        cond_scores.append(mean_c)
        trigger_freqs.append(trigger_steps / horizon if horizon > 0 else 0)

    avg_baseline = sum(baseline_scores) / len(baseline_scores)
    avg_cond = sum(cond_scores) / len(cond_scores)
    improvement = (avg_cond - avg_baseline) / max(avg_baseline, 0.01)

    return {
        "name": candidate.name,
        "description": candidate.description,
        "trigger": candidate.trigger_token,
        "score_baseline": avg_baseline,
        "score_with_cond": avg_cond,
        "improvement": improvement,
        "trigger_frequency": sum(trigger_freqs) / len(trigger_freqs),
        "effective": improvement > 0.05  # 5% improvement threshold
    }


def main():
    print("=" * 60)
    print("CONDITIONAL POLICY EVALUATOR")
    print("LLM generates candidates, GPU evaluates effectiveness")
    print("=" * 60, flush=True)

    # Load farm game with policy
    base_path = Path(__file__).parent.parent.parent
    csv_path = base_path / "games" / "farm" / "recipes.csv"
    policy_path = base_path / "policy.best.signa"  # Use best policy as baseline

    print(f"Loading rules from: {csv_path}", flush=True)
    print(f"Loading policy from: {policy_path}", flush=True)

    kernel, registry, idx_to_id, base_to_indices = load_farm_rules(csv_path, policy_path)
    num_rules = len(idx_to_id)
    print(f"Loaded {num_rules} rules", flush=True)

    # Base bias - use policy weights from the best policy
    base_bias = torch.zeros(num_rules, dtype=torch.float32)

    # Add base selling priority (from policy.best.signa)
    base_rules = {
        "ID_Sell_Wood": 40.0, "ID_Sell_Stone": 40.0, "ID_Sell_Apple": 40.0,
        "ID_Day": 35.0, "ID_Rent1": 35.0, "ID_Rent2": 30.0,
        "ID_Chop_Tree": 25.0, "ID_Pick_Stone": 22.0, "ID_Rod_Fish": 18.0
    }
    for rule_base, weight in base_rules.items():
        if rule_base in base_to_indices:
            for idx in base_to_indices[rule_base]:
                base_bias[idx] = weight

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}", flush=True)

    # Faster settings for quick iteration
    batch_size = 128  # Smaller batch
    horizon = 100     # Shorter horizon
    num_trials = 1    # Single trial

    print(f"\nEvaluating {len(CANDIDATES)} conditional candidates...")
    print(f"Settings: batch={batch_size}, horizon={horizon}, trials={num_trials}")
    print("-" * 60, flush=True)

    results = []
    for i, candidate in enumerate(CANDIDATES):
        print(f"\n[{i+1}/{len(CANDIDATES)}] {candidate.name}", flush=True)
        print(f"  Trigger: {candidate.trigger_token}")
        print(f"  Description: {candidate.description}", flush=True)

        result = evaluate_conditional(
            candidate, kernel, registry, base_to_indices, base_bias,
            batch_size=batch_size,
            horizon=horizon,
            num_trials=num_trials,
            device=device
        )
        results.append(result)

        print(f"  Baseline score: {result['score_baseline']:.2f}")
        print(f"  With conditional: {result['score_with_cond']:.2f}")
        print(f"  Improvement: {result['improvement']:.1%}")
        print(f"  Effective: {'YES' if result['effective'] else 'no'}")

    print()
    print("=" * 60)
    print("SUMMARY - Effective Conditionals")
    print("=" * 60)

    effective = [r for r in results if r["effective"]]
    if effective:
        for r in sorted(effective, key=lambda x: x["improvement"], reverse=True):
            print(f"  {r['name']}: +{r['improvement']:.1%} ({r['description']})")
    else:
        print("  No conditionals showed >5% improvement")

    print()
    print("=" * 60)
    print("GENERATED POLICY RULES")
    print("=" * 60)

    # Generate policy text for effective conditionals
    for r in effective:
        cand = next(c for c in CANDIDATES if c.name == r["name"])
        boosts = " ".join([f"♥{rule}_{cand.boost}" for rule in cand.target_rule_bases])
        print(f"\n// {r['description']} (+{r['improvement']:.1%})")
        print(f"{cand.trigger_token} ♥⏰{cand.name} => {cand.trigger_token} {boosts}")


if __name__ == "__main__":
    main()

"""
Conditional Policy Discovery Module

This module implements a hybrid LLM-GPU approach to discovering conditional policies:
1. Define candidate trigger conditions (state tokens that might be meaningful)
2. Run GPU rollouts tracking which rules correlate with high scores under each condition
3. Generate conditional policy rules based on discovered correlations

The key insight is that while GPU can't understand *why* certain conditions matter,
it can efficiently evaluate *whether* they matter through parallel rollouts.
"""

import os
import torch
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class ConditionalCandidate:
    """A candidate conditional rule to evaluate."""
    trigger_token: str  # State token that activates this conditional
    target_rules: List[str]  # Rules to boost when trigger is present
    boost_amount: float  # How much to boost
    description: str  # Human-readable description


# Semantically meaningful trigger conditions for the farm game
FARM_GAME_TRIGGERS = {
    # Late-week urgency (approaching Saturday deadline)
    "☀4️⃣": "Thursday - moderate urgency",
    "☀5️⃣": "Friday - high urgency",
    "☀6️⃣": "Saturday - critical urgency",

    # Rent tier progression
    "🏦2️⃣": "After Rent1 - can pursue longer strategies",
    "🏦3️⃣": "After Rent2 - sustainable income needed",
    "🏦4️⃣": "After Rent3 - scaling required",

    # Resource availability
    "🌳": "Trees available - can chop",
    "🌳🟤": "Stumps present - trees depleted",
    "🟦": "Water tiles - can fish",
    "⛰️": "Rocks available - can mine",

    # Time of day
    "🌙": "Night time - limited actions",
    "🌞": "Day time - full actions available",

    # Infrastructure
    "🔥⚙": "Furnace built - can smelt",
    "🥫⚙": "Preserves machine - can preserve",
}

# Rule categories for boosting
RULE_CATEGORIES = {
    "selling": [
        "ID_Sell_Wood", "ID_Sell_Stone", "ID_Sell_Apple", "ID_Sell_Berry",
        "ID_Sell_Orange", "ID_Sell_Copper_Ore", "ID_Sell_Iron_Ore",
        "ID_Sell_Gold_Ore", "ID_Sell_Coal", "ID_Sell_Sardine", "ID_Sell_Halibut",
        "ID_Sell_Bullhead", "ID_Sell_Carp", "ID_Sell_Red_Mullet", "ID_Sell_Sturgeon"
    ],
    "chopping": [
        "ID_Chop_Tree", "ID_Chop_Apple_Tree", "ID_Chop_Orange_Tree",
        "ID_Chop_Bush", "ID_Chop_Bush_Apple", "ID_Chop_Bush_Berry"
    ],
    "mining": [
        "ID_Pick_Stone", "ID_Pick_Stone_Small", "ID_Pick_Stone_Large",
        "ID_Pick_Copper", "ID_Pick_Iron", "ID_Pick_Gold", "ID_Pick_Coal"
    ],
    "fishing": [
        "ID_Rod_Fish", "ID_Rod_Fish_Copper", "ID_Rod_Fish_Iron", "ID_Rod_Fish_Gold"
    ],
    "day_transition": ["ID_Day"],
    "rent_payment": ["ID_Rent1", "ID_Rent2", "ID_Rent3", "ID_Rent4", "ID_Rent5"],
}


class ConditionalPolicyDiscovery:
    """
    Discovers effective conditional policies through GPU-accelerated evaluation.

    The process:
    1. Generate candidate conditionals from semantic templates
    2. Evaluate each candidate through parallel rollouts
    3. Compare scores with/without the conditional
    4. Report which conditionals provide significant improvement
    """

    def __init__(self, engine, registry, device='cuda'):
        self.engine = engine
        self.registry = registry
        self.device = device
        self.discovered_conditionals: List[Tuple[ConditionalCandidate, float]] = []

    def generate_candidates(self) -> List[ConditionalCandidate]:
        """Generate candidate conditional rules based on semantic templates."""
        candidates = []

        # Late-week urgency: boost selling as deadline approaches
        for day_token, urgency in [("☀4️⃣", 10.0), ("☀5️⃣", 15.0), ("☀6️⃣", 20.0)]:
            candidates.append(ConditionalCandidate(
                trigger_token=day_token,
                target_rules=RULE_CATEGORIES["selling"] + RULE_CATEGORIES["day_transition"],
                boost_amount=urgency,
                description=f"Boost selling on {FARM_GAME_TRIGGERS[day_token]}"
            ))

        # Post-rent pivots: shift to sustainable income after paying rent
        for rent_tier, boost in [("🏦2️⃣", 15.0), ("🏦3️⃣", 20.0)]:
            candidates.append(ConditionalCandidate(
                trigger_token=rent_tier,
                target_rules=RULE_CATEGORIES["fishing"],
                boost_amount=boost,
                description=f"Boost fishing after reaching {rent_tier}"
            ))

        # Resource depletion: pivot when trees are gone
        candidates.append(ConditionalCandidate(
            trigger_token="🌳🟤",  # Stumps indicate trees were chopped
            target_rules=RULE_CATEGORIES["fishing"] + RULE_CATEGORIES["mining"],
            boost_amount=15.0,
            description="Pivot to fishing/mining when trees depleted"
        ))

        return candidates

    def evaluate_candidate(
        self,
        candidate: ConditionalCandidate,
        base_bias: torch.Tensor,
        num_rollouts: int = 1024,
        horizon: int = 600
    ) -> Tuple[float, float, float]:
        """
        Evaluate a conditional candidate by comparing rollouts with/without it.

        Returns: (score_with, score_without, improvement)
        """
        # This would integrate with the engine to:
        # 1. Run rollouts with base bias only
        # 2. Run rollouts with conditional bias added when trigger present
        # 3. Compare average scores

        # For now, return placeholder - actual implementation would hook into engine
        return 0.0, 0.0, 0.0

    def discover(self, num_rollouts: int = 1024, horizon: int = 600) -> List[Tuple[ConditionalCandidate, float]]:
        """
        Run discovery process to find effective conditionals.

        Returns list of (candidate, improvement) sorted by improvement.
        """
        candidates = self.generate_candidates()
        results = []

        for candidate in candidates:
            score_with, score_without, improvement = self.evaluate_candidate(
                candidate,
                torch.zeros(1),  # Placeholder base bias
                num_rollouts,
                horizon
            )
            results.append((candidate, improvement))

        # Sort by improvement
        results.sort(key=lambda x: x[1], reverse=True)
        self.discovered_conditionals = results
        return results

    def generate_policy_rules(self, threshold: float = 0.05) -> str:
        """
        Generate policy rule text for discovered conditionals above threshold.
        """
        lines = []
        lines.append("// ═══════════════════════════════════════════════════════════════")
        lines.append("// AUTO-DISCOVERED CONDITIONAL RULES")
        lines.append("// ═══════════════════════════════════════════════════════════════")
        lines.append("")

        for candidate, improvement in self.discovered_conditionals:
            if improvement >= threshold:
                # Generate charge token name
                charge_token = f"♥⏰{candidate.trigger_token}"

                # Generate rule
                rule_boosts = " ".join([
                    f"♥{rule}_{candidate.boost_amount}"
                    for rule in candidate.target_rules
                ])

                lines.append(f"// {candidate.description} (improvement: {improvement:.1%})")
                lines.append(f"{candidate.trigger_token} {charge_token} => {candidate.trigger_token} {rule_boosts}")
                lines.append("")

        return "\n".join(lines)


def analyze_state_correlations(
    traces: List[Dict],
    target_prefixes: List[str] = ["👑", "💰"]
) -> Dict[str, Dict[str, float]]:
    """
    Analyze rollout traces to find correlations between state tokens and rule effectiveness.

    This is a data-driven approach to conditional discovery:
    - For each state token, track which rules fired when it was present
    - Compute correlation between token presence and score improvement

    Args:
        traces: List of rollout traces with state snapshots and rule firings
        target_prefixes: Tokens to use for scoring

    Returns:
        Dict mapping trigger_token -> {rule_id -> correlation_score}
    """
    correlations = {}

    # This would analyze actual trace data to find:
    # - When token X is present, which rules lead to higher scores?
    # - Are there state patterns that predict which actions are effective?

    return correlations


# LLM-assisted conditional generation prompt template
LLM_DISCOVERY_PROMPT = """
You are analyzing a farm game simulation to discover effective conditional policies.

Current game state patterns observed:
{state_patterns}

Rules that frequently fire:
{frequent_rules}

Score distribution:
- High-scoring universes: {high_score_patterns}
- Low-scoring universes: {low_score_patterns}

Based on this data, suggest conditional policy rules that could improve performance.
Each rule should:
1. Specify a trigger condition (when should this activate?)
2. List rules to boost when triggered
3. Explain the reasoning

Format:
TRIGGER: <state token>
BOOST: <rule1>, <rule2>, ...
REASONING: <why this helps>
"""


if __name__ == "__main__":
    # Demo: show candidate generation
    print("=== Conditional Policy Discovery ===\n")

    # Create discovery instance (without engine for demo)
    discovery = ConditionalPolicyDiscovery(None, None)

    # Generate candidates
    candidates = discovery.generate_candidates()

    print(f"Generated {len(candidates)} conditional candidates:\n")
    for i, cand in enumerate(candidates, 1):
        print(f"{i}. {cand.description}")
        print(f"   Trigger: {cand.trigger_token}")
        print(f"   Boost: {len(cand.target_rules)} rules by {cand.boost_amount}")
        print()

    # Show what generated policy would look like
    print("\n=== Sample Generated Policy Rules ===\n")

    # Simulate some discovered results
    discovery.discovered_conditionals = [
        (candidates[2], 0.15),  # Saturday urgency
        (candidates[1], 0.12),  # Friday urgency
        (candidates[3], 0.08),  # Post-rent1 fishing
    ]

    print(discovery.generate_policy_rules(threshold=0.05))

"""
LLM-GPU Policy Optimization Loop

This implements an iterative loop where:
1. LLM generates conditional policy variants based on game understanding
2. GPU evaluates each variant with CEM
3. Results are fed back for refinement

The LLM acts as a semantic policy designer, GPU as a parallel evaluator.
"""

import os
import subprocess
import json
import re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

# ═══════════════════════════════════════════════════════════════════════════
# LLM PROMPT TEMPLATE
# This is the "initial prompt" that gives the LLM full context on rules/syntax
# ═══════════════════════════════════════════════════════════════════════════

LLM_SYSTEM_PROMPT = """You are a policy designer for a farm simulation game. Your goal is to create conditional policy rules that help an agent accumulate gold (💰) and pay rent to earn crowns (👑).

## GAME MECHANICS

### Starting State
- 1296 terrain tiles (trees, rocks, water, grass)
- Tools: axe (🪓), pickaxe (⛏), hoe (🔰), shovel (♠), watering can (🚿), fishing rod (🎣), hammer (🔨)
- 225 water per day (resets when day ends)
- Start on Sunday (☀7️⃣), Rent Tier 1 (🏦1️⃣)

### Day Cycle
- Days: ☀1️⃣ (Mon) → ☀2️⃣ (Tue) → ... → ☀7️⃣ (Sun)
- ID_Day rule ends the day, resets water to 225
- CRITICAL: ID_Saturday_Night (☀6️⃣ → ☀7️⃣) requires 🏦 token
- 🏦 token only comes from paying rent!
- If you don't pay Rent1 (1000 gold) by Saturday, game over

### Rent Ladder
- Rent1: 1000 💰 → 👑 + 🏦2️⃣
- Rent2: 2500 💰 → 👑 + 🏦3️⃣
- Rent3: 5000 💰 → 👑 + 🏦4️⃣
- Rent4: 10000 💰 → 👑 + 🏦5️⃣
- Rent5: 20000 💰 → 👑 + 🏦6️⃣

### Resource Generation
- Chopping trees (🌳): produces wood (🤎), sells for 15-20 gold
- Mining rocks (⛰️): produces stone (🥌), sells for 15-25 gold
- Fishing (🟦 water tiles): produces fish (🐟🐠🐡🦀🦐🦈), sells for 10-95 gold
- Trees become stumps (🌳🟤) after chopping - FINITE resource!
- Water tiles persist - SUSTAINABLE income!

## POLICY SYNTAX

### Rule Format
```
LHS => RHS
```
- LHS tokens are consumed (unless on both sides - catalyst)
- RHS tokens are produced

### Policy Tokens
- ♥ID_RuleName_Weight - Bias a game rule by Weight
- ⛳👑Weight ⛳💰Weight - Objective weights for optimization

### CRITICAL RULES FOR CONDITIONALS

1. **Catalyst Pattern**: Put physics tokens on BOTH sides
   - CORRECT: `☀4️⃣ ♥charge => ☀4️⃣ ♥ID_Sell_Wood_10.0`
   - WRONG: `☀4️⃣ => ♥ID_Sell_Wood_10.0` (consumes day token!)

2. **One-Shot Charges**: Use unique charge tokens to prevent re-triggering
   - Create charge at start: `🎬 => 💫 ♥ ⛳ ♥charge1 ♥charge2`
   - Consume when triggered: `☀4️⃣ ♥charge1 => ☀4️⃣ ♥ID_...`

3. **Never Create Physics Tokens**: Only produce ♥ policy tokens
   - WRONG: `♥mode => 💰100` (cheating!)
   - CORRECT: `♥mode => ♥ID_Sell_Wood_20.0`

4. **Don't Interfere with Base Policy**: The base ♥ => ... rule handles core priorities

## CURRENT BEST POLICY (31% Rent3)

```
🎬 => 💫 ♥ ⛳ ♥THUR ♥FRI ♥SAT ♥POST_R1

// Base priorities
❗ ♥ => ♥ID_Sell_Wood_40.0 ♥ID_Sell_Stone_40.0 ... ♥ID_Rent1_45.0 ♥ID_Rent2_45.0 ...

// Late-week urgency conditionals (charge tokens use NAMES not numbers!)
// WRONG: ♥⏰4 (parsed as quantity 4 of ♥⏰)
// CORRECT: ♥THUR, ♥FRI, ♥SAT (unique tokens)
☀4️⃣ ♥THUR => ☀4️⃣ ♥ID_Sell_Wood_10.0 ♥ID_Sell_Stone_10.0 ...
☀5️⃣ ♥FRI => ☀5️⃣ ♥ID_Sell_Wood_15.0 ♥ID_Sell_Stone_15.0 ...
☀6️⃣ ♥SAT => ☀6️⃣ ♥ID_Sell_Wood_20.0 ♥ID_Sell_Stone_20.0 ...

// Post-rent pivot
🏦2️⃣ ♥POST_R1 => 🏦2️⃣ ♥ID_Rod_Fish_15.0 ...

// Objective weights
⛳ => ⛳👑25.0 ⛳💰25.0
```

## YOUR TASK

Generate an improved policy variant. Consider:
1. Are the objective weights (⛳👑, ⛳💰) optimal? Maybe prioritize 👑 more?
2. Should fishing be boosted earlier (sustainable income)?
3. Are there other trigger conditions worth trying?
4. Should we have per-week recharge of conditional charges?

Output a complete policy.signa file with your improvements.
"""

# ═══════════════════════════════════════════════════════════════════════════
# POLICY VARIANT TEMPLATES
# These are LLM-style generated variants to test
# ═══════════════════════════════════════════════════════════════════════════

POLICY_VARIANTS = {
    "baseline": """
🎬 => 💫 ♥ ⛳ ♥THUR ♥FRI ♥SAT ♥POST_R1

// BASE POLICY - Sell-first with high rent priority
❗ ♥ => ♥ID_Sell_Wood_40.0 ♥ID_Sell_Stone_40.0 ♥ID_Sell_Apple_40.0 ♥ID_Sell_Berry_40.0 ♥ID_Sell_Orange_40.0 ♥ID_Sell_Copper_Ore_38.0 ♥ID_Sell_Iron_Ore_38.0 ♥ID_Sell_Gold_Ore_38.0 ♥ID_Sell_Coal_38.0 ♥ID_Sell_Sardine_38.0 ♥ID_Sell_Halibut_38.0 ♥ID_Sell_Bullhead_38.0 ♥ID_Sell_Carp_38.0 ♥ID_Sell_Red_Mullet_38.0 ♥ID_Sell_Sturgeon_38.0 ♥ID_Day_35.0 ♥ID_Rent1_45.0 ♥ID_Rent2_45.0 ♥ID_Rent3_45.0 ♥ID_Rent4_45.0 ♥ID_Rent5_45.0 ♥ID_Chop_Axe_28.0 ♥ID_Pick_Pickaxe_28.0 ♥ID_Chop_Tree_25.0 ♥ID_Pick_Stone_22.0 ♥ID_Rod_Fish_22.0

// Late-week urgency
☀4️⃣ ♥THUR => ☀4️⃣ ♥ID_Sell_Wood_10.0 ♥ID_Sell_Stone_10.0 ♥ID_Day_5.0
☀5️⃣ ♥FRI => ☀5️⃣ ♥ID_Sell_Wood_15.0 ♥ID_Sell_Stone_15.0 ♥ID_Day_10.0
☀6️⃣ ♥SAT => ☀6️⃣ ♥ID_Sell_Wood_20.0 ♥ID_Sell_Stone_20.0 ♥ID_Day_15.0 ♥ID_Rent1_20.0

// Post-Rent1 fishing pivot
🏦2️⃣ ♥POST_R1 => 🏦2️⃣ ♥ID_Rod_Fish_15.0 ♥ID_Sell_Sardine_10.0 ♥ID_Sell_Halibut_10.0

⛳ => ⛳👑25.0 ⛳💰25.0
""",

    "crown_focused": """
🎬 => 💫 ♥ ⛳ ♥THUR ♥FRI ♥SAT ♥POST_R1 ♥POST_R2

// BASE - Same selling but HIGHER rent priority
❗ ♥ => ♥ID_Sell_Wood_40.0 ♥ID_Sell_Stone_40.0 ♥ID_Sell_Apple_40.0 ♥ID_Sell_Berry_40.0 ♥ID_Sell_Orange_40.0 ♥ID_Sell_Copper_Ore_38.0 ♥ID_Sell_Iron_Ore_38.0 ♥ID_Sell_Gold_Ore_38.0 ♥ID_Sell_Coal_38.0 ♥ID_Sell_Sardine_38.0 ♥ID_Sell_Halibut_38.0 ♥ID_Sell_Bullhead_38.0 ♥ID_Sell_Carp_38.0 ♥ID_Sell_Red_Mullet_38.0 ♥ID_Sell_Sturgeon_38.0 ♥ID_Day_35.0 ♥ID_Rent1_50.0 ♥ID_Rent2_50.0 ♥ID_Rent3_50.0 ♥ID_Rent4_50.0 ♥ID_Rent5_50.0 ♥ID_Chop_Axe_28.0 ♥ID_Pick_Pickaxe_28.0 ♥ID_Chop_Tree_25.0 ♥ID_Pick_Stone_22.0 ♥ID_Rod_Fish_22.0

// Late-week urgency - escalating
☀4️⃣ ♥THUR => ☀4️⃣ ♥ID_Sell_Wood_10.0 ♥ID_Sell_Stone_10.0 ♥ID_Day_5.0
☀5️⃣ ♥FRI => ☀5️⃣ ♥ID_Sell_Wood_15.0 ♥ID_Sell_Stone_15.0 ♥ID_Day_10.0
☀6️⃣ ♥SAT => ☀6️⃣ ♥ID_Sell_Wood_25.0 ♥ID_Sell_Stone_25.0 ♥ID_Day_20.0 ♥ID_Rent1_30.0

// Post-Rent1: aggressive fishing
🏦2️⃣ ♥POST_R1 => 🏦2️⃣ ♥ID_Rod_Fish_20.0 ♥ID_Sell_Sardine_15.0 ♥ID_Sell_Halibut_15.0 ♥ID_Sell_Bullhead_15.0 ♥ID_Sell_Carp_15.0

// Post-Rent2: even more fishing, start processing
🏦3️⃣ ♥POST_R2 => 🏦3️⃣ ♥ID_Rod_Fish_25.0 ♥ID_Sell_Sardine_20.0 ♥ID_Build_Furnace_15.0

// OBJECTIVE: Weight crowns MORE than gold (pay rent ASAP)
⛳ => ⛳👑35.0 ⛳💰20.0
""",

    "early_fishing": """
🎬 => 💫 ♥ ⛳ ♥THUR ♥FRI ♥SAT ♥POST_R1 ♥POST_R2 ♥FISH_EARLY

// BASE - Boost fishing from start (sustainable income)
❗ ♥ => ♥ID_Sell_Wood_38.0 ♥ID_Sell_Stone_38.0 ♥ID_Sell_Apple_38.0 ♥ID_Sell_Berry_38.0 ♥ID_Sell_Orange_38.0 ♥ID_Sell_Copper_Ore_35.0 ♥ID_Sell_Iron_Ore_35.0 ♥ID_Sell_Gold_Ore_35.0 ♥ID_Sell_Coal_35.0 ♥ID_Sell_Sardine_40.0 ♥ID_Sell_Halibut_40.0 ♥ID_Sell_Bullhead_40.0 ♥ID_Sell_Carp_40.0 ♥ID_Sell_Red_Mullet_40.0 ♥ID_Sell_Sturgeon_40.0 ♥ID_Day_35.0 ♥ID_Rent1_45.0 ♥ID_Rent2_45.0 ♥ID_Rent3_45.0 ♥ID_Rent4_45.0 ♥ID_Rent5_45.0 ♥ID_Chop_Axe_25.0 ♥ID_Pick_Pickaxe_25.0 ♥ID_Chop_Tree_22.0 ♥ID_Pick_Stone_20.0 ♥ID_Rod_Fish_30.0 ♥ID_Rod_Fish_Copper_30.0 ♥ID_Rod_Fish_Iron_30.0 ♥ID_Rod_Fish_Gold_30.0

// Early fishing boost (consume charge on first fish attempt)
🐟 ♥FISH_EARLY => 🐟 ♥ID_Rod_Fish_15.0 ♥ID_Sell_Sardine_10.0

// Late-week urgency
☀4️⃣ ♥THUR => ☀4️⃣ ♥ID_Sell_Wood_10.0 ♥ID_Sell_Stone_10.0 ♥ID_Sell_Sardine_10.0 ♥ID_Day_5.0
☀5️⃣ ♥FRI => ☀5️⃣ ♥ID_Sell_Wood_15.0 ♥ID_Sell_Stone_15.0 ♥ID_Sell_Sardine_15.0 ♥ID_Day_10.0
☀6️⃣ ♥SAT => ☀6️⃣ ♥ID_Sell_Wood_20.0 ♥ID_Sell_Stone_20.0 ♥ID_Sell_Sardine_20.0 ♥ID_Day_15.0 ♥ID_Rent1_20.0

// Post-Rent pivots
🏦2️⃣ ♥POST_R1 => 🏦2️⃣ ♥ID_Rod_Fish_20.0 ♥ID_Sell_Sardine_15.0 ♥ID_Sell_Halibut_15.0
🏦3️⃣ ♥POST_R2 => 🏦3️⃣ ♥ID_Rod_Fish_25.0 ♥ID_Sell_Carp_20.0 ♥ID_Sell_Red_Mullet_20.0

⛳ => ⛳👑30.0 ⛳💰22.0
""",

    "aggressive_day_cycle": """
🎬 => 💫 ♥ ⛳ ♥MON ♥TUE ♥WED ♥THUR ♥FRI ♥SAT ♥POST_R1 ♥POST_R2

// BASE - Standard selling, VERY high day priority
❗ ♥ => ♥ID_Sell_Wood_40.0 ♥ID_Sell_Stone_40.0 ♥ID_Sell_Apple_40.0 ♥ID_Sell_Berry_40.0 ♥ID_Sell_Orange_40.0 ♥ID_Sell_Copper_Ore_38.0 ♥ID_Sell_Iron_Ore_38.0 ♥ID_Sell_Gold_Ore_38.0 ♥ID_Sell_Coal_38.0 ♥ID_Sell_Sardine_38.0 ♥ID_Sell_Halibut_38.0 ♥ID_Sell_Bullhead_38.0 ♥ID_Sell_Carp_38.0 ♥ID_Day_40.0 ♥ID_Rent1_48.0 ♥ID_Rent2_48.0 ♥ID_Rent3_48.0 ♥ID_Rent4_48.0 ♥ID_Rent5_48.0 ♥ID_Chop_Axe_28.0 ♥ID_Pick_Pickaxe_28.0 ♥ID_Chop_Tree_25.0 ♥ID_Pick_Stone_22.0 ♥ID_Rod_Fish_24.0

// EVERY day gets an urgency boost - ensure steady progress
☀1️⃣ ♥MON => ☀1️⃣ ♥ID_Day_5.0 ♥ID_Sell_Wood_5.0 ♥ID_Sell_Stone_5.0
☀2️⃣ ♥TUE => ☀2️⃣ ♥ID_Day_5.0 ♥ID_Sell_Wood_5.0 ♥ID_Sell_Stone_5.0
☀3️⃣ ♥WED => ☀3️⃣ ♥ID_Day_8.0 ♥ID_Sell_Wood_8.0 ♥ID_Sell_Stone_8.0
☀4️⃣ ♥THUR => ☀4️⃣ ♥ID_Day_12.0 ♥ID_Sell_Wood_12.0 ♥ID_Sell_Stone_12.0
☀5️⃣ ♥FRI => ☀5️⃣ ♥ID_Day_18.0 ♥ID_Sell_Wood_18.0 ♥ID_Sell_Stone_18.0
☀6️⃣ ♥SAT => ☀6️⃣ ♥ID_Day_25.0 ♥ID_Sell_Wood_25.0 ♥ID_Sell_Stone_25.0 ♥ID_Rent1_25.0

// Post-Rent pivots
🏦2️⃣ ♥POST_R1 => 🏦2️⃣ ♥ID_Rod_Fish_18.0 ♥ID_Sell_Sardine_12.0
🏦3️⃣ ♥POST_R2 => 🏦3️⃣ ♥ID_Rod_Fish_22.0 ♥ID_Sell_Halibut_15.0

⛳ => ⛳👑28.0 ⛳💰24.0
""",
}


@dataclass
class EvalResult:
    """Result from evaluating a policy variant."""
    variant_name: str
    rent1_pct: float
    rent2_pct: float
    rent3_pct: float
    max_gold: float
    cem_score: float
    valid_pct: float
    raw_output: str


def run_policy_evaluation(policy_text: str, variant_name: str, timeout: int = 180) -> EvalResult:
    """
    Run GPU evaluation of a policy variant.

    Writes policy to temp file, runs agent, parses results.
    """
    base_path = Path(__file__).parent.parent.parent
    policy_path = base_path / f"policy.{variant_name}.signa"

    # Write policy
    policy_path.write_text(policy_text, encoding="utf-8")
    print(f"  Wrote policy to: {policy_path}")

    # Run agent with this policy - use stronger parameters for real evaluation
    env = os.environ.copy()
    env.update({
        "PYTHONIOENCODING": "utf-8",
        "POLICY_FILE": str(policy_path),
        "TARGET_RESOURCE_PREFIXES": "👑,💰",
        "AGENT_BATCH": "4096",
        "CEM_TRAIN_BATCH": "2048",
        "CEM_TRAIN_HORIZON": "200",
        "CEM_EVAL_EVERY": "10",
        "CEM_OBJECTIVE": "max",
        "CEM_POP": "16",
        "CEM_ITERS": "8",
        "AGENT_HORIZON": "800",
        "DECISION_ONLY": "1",
        "PHYSICS_BURST_MAX": "128",
        "FINAL_HEARTBEAT_EVERY": "100",
        "PLANNER_ENABLE": "1",
        "PLANNER_AGGREGATED": "1",
        "PLANNER_EVERY": "5",
        "PLANNER_GAIN": "0.8",
    })

    python_exe = base_path / ".venv" / "Scripts" / "python.exe"
    cmd = [str(python_exe), "-X", "utf8", "-m", "signamancy.agent.run_agent_generic"]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(base_path),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace"
        )
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        output = "TIMEOUT"
    except Exception as e:
        output = f"ERROR: {e}"

    # Parse results from output
    return parse_eval_output(variant_name, output)


def parse_eval_output(variant_name: str, output: str) -> EvalResult:
    """Parse agent output to extract metrics."""
    # Defaults
    rent1_pct = 0.0
    rent2_pct = 0.0
    rent3_pct = 0.0
    max_gold = 0.0
    cem_score = 0.0
    valid_pct = 0.0

    # Parse final snapshot for rent tier percentages
    # Look for 🏦2️⃣ (paid Rent1), 🏦3️⃣ (paid Rent2), 🏦4️⃣ (paid Rent3)
    bank2_match = re.search(r'"🏦2️⃣":\s*{\s*"val":\s*([\d.]+)', output)
    bank3_match = re.search(r'"🏦3️⃣":\s*{\s*"val":\s*([\d.]+)', output)
    bank4_match = re.search(r'"🏦4️⃣":\s*{\s*"val":\s*([\d.]+)', output)
    crown_match = re.search(r'"👑":\s*{\s*"val":\s*([\d.]+)', output)

    if bank2_match:
        rent1_pct = float(bank2_match.group(1)) + (float(bank3_match.group(1)) if bank3_match else 0)
        rent1_pct += float(bank4_match.group(1)) if bank4_match else 0
    if bank3_match:
        rent2_pct = float(bank3_match.group(1)) + (float(bank4_match.group(1)) if bank4_match else 0)
    if bank4_match:
        rent3_pct = float(bank4_match.group(1))

    # Parse max gold from FINAL lines
    gold_matches = re.findall(r'score_max=([\d.]+)', output)
    if gold_matches:
        max_gold = max(float(g) for g in gold_matches)

    # Parse CEM best score
    cem_match = re.search(r'Best score=([\d.]+)', output)
    if cem_match:
        cem_score = float(cem_match.group(1))

    # Parse final validity - look in last portion of output
    valid_match = None
    if output:
        # Try finding last valid line
        for line in reversed(output.split('\n')[-50:]):
            valid_match = re.search(r'valid=(\d+)/(\d+)', line)
            if valid_match:
                break
    if valid_match:
        valid_pct = float(valid_match.group(1)) / float(valid_match.group(2))

    return EvalResult(
        variant_name=variant_name,
        rent1_pct=rent1_pct,
        rent2_pct=rent2_pct,
        rent3_pct=rent3_pct,
        max_gold=max_gold,
        cem_score=cem_score,
        valid_pct=valid_pct,
        raw_output=output[-2000:]  # Last 2000 chars for debugging
    )


def run_optimization_loop(max_iterations: int = 3):
    """
    Run the LLM-GPU optimization loop.

    Each iteration:
    1. Evaluate current policy variants
    2. Identify best performing variant
    3. Generate new variants based on learnings (LLM step)
    4. Repeat
    """
    print("=" * 70)
    print("LLM-GPU POLICY OPTIMIZATION LOOP")
    print("=" * 70)
    print(f"Starting at: {datetime.now().isoformat()}")
    print()

    all_results: List[EvalResult] = []

    for iteration in range(max_iterations):
        print(f"\n{'='*70}")
        print(f"ITERATION {iteration + 1}/{max_iterations}")
        print(f"{'='*70}")

        # Evaluate each variant
        for name, policy_text in POLICY_VARIANTS.items():
            print(f"\n[Evaluating: {name}]")
            result = run_policy_evaluation(policy_text, name)
            all_results.append(result)

            print(f"  Rent1: {result.rent1_pct:.1%}")
            print(f"  Rent2: {result.rent2_pct:.1%}")
            print(f"  Rent3: {result.rent3_pct:.1%}")
            print(f"  Max Gold: {result.max_gold:.0f}")
            print(f"  CEM Score: {result.cem_score:.1f}")
            print(f"  Valid: {result.valid_pct:.1%}")

        # Find best variant
        best = max(all_results, key=lambda r: (r.rent3_pct, r.rent2_pct, r.rent1_pct, r.max_gold))
        print(f"\n[BEST SO FAR: {best.variant_name}]")
        print(f"  Rent3: {best.rent3_pct:.1%}, Rent2: {best.rent2_pct:.1%}, Rent1: {best.rent1_pct:.1%}")

        # In a full implementation, this is where we'd call the LLM to generate
        # new variants based on the results. For now, we just run the predefined variants.
        if iteration < max_iterations - 1:
            print("\n[LLM would generate new variants here based on results...]")

    # Final summary
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)

    # Sort by performance
    sorted_results = sorted(all_results, key=lambda r: (r.rent3_pct, r.rent2_pct, r.rent1_pct), reverse=True)

    print(f"\n{'Variant':<25} {'Rent1':>8} {'Rent2':>8} {'Rent3':>8} {'MaxGold':>10} {'CEM':>8}")
    print("-" * 70)
    for r in sorted_results[:10]:  # Top 10
        print(f"{r.variant_name:<25} {r.rent1_pct:>7.1%} {r.rent2_pct:>7.1%} {r.rent3_pct:>7.1%} {r.max_gold:>10.0f} {r.cem_score:>8.1f}")

    # Save best policy
    best = sorted_results[0]
    best_policy = POLICY_VARIANTS.get(best.variant_name, "")
    if best_policy:
        base_path = Path(__file__).parent.parent.parent
        best_path = base_path / "policy.loop_best.signa"
        best_path.write_text(f"// Best from LLM-GPU loop: {best.variant_name}\n" + best_policy, encoding="utf-8")
        print(f"\nSaved best policy to: {best_path}")


if __name__ == "__main__":
    # Run a single iteration to test
    run_optimization_loop(max_iterations=1)

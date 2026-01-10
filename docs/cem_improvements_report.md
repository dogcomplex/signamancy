# CEM Optimizer Improvements - Session Report

**Date:** January 10, 2026
**Branch:** feature/cem-improvements

## Summary

This session explored improvements to the Cross-Entropy Method (CEM) optimizer used for training the farm game agent. We implemented grouped sampling and temporal bias scheduling features, tested them, and discovered that these "improvements" actually hurt performance compared to the vanilla CEM.

## Background

The CEM optimizer works by:
1. Sampling candidate bias vectors from a Gaussian distribution
2. Evaluating each candidate by running simulations
3. Selecting elite performers and updating the distribution mean/std
4. Repeating for multiple iterations

Previous sessions established that:
- Simple policies outperform complex conditional policies
- Best results: 97% Rent1, 35% survival at 800 steps with `policy.max_fish.signa`
- CEM struggles with multi-step investment strategies (e.g., build furnace -> smelt bars -> upgrade rod)

## Implemented Features

### 1. RuleGrouper (`signamancy/agent/cem_improved.py`)

Automatically groups related rules based on their IDs for correlated sampling.

```python
grouper = RuleGrouper(idx_to_id)
# Discovers 26 groups from 451 rules:
# Grid, Grass, Hole, Fish, Day, Shop, Stock, Feat, Chop, Pick,
# Hoe, Shovel, Water, Rod, Hammer, Copper, Iron, Gold, Build,
# Night, Grow, Harvest, Sell, Feed, Butcher, Buy
```

**Rationale:** Rules in the same category (e.g., all "Sell_*" rules) might benefit from being boosted/penalized together.

### 2. TemporalBiasScheduler (`signamancy/agent/cem_improved.py`)

Applies phase-specific bias adjustments during simulation:

| Phase | Steps | Boosted Groups | Penalized Groups |
|-------|-------|----------------|------------------|
| Early | 0-100 | Build, Chop, Pick, Buy | Rod |
| Mid | 100-300 | Rod, Baked, Preserves, Fishtrap, Beehive | - |
| Late | 300+ | Sell, Rent, Day | - |

**Rationale:** Different strategies are optimal at different game phases.

### 3. Grouped Sampling (`create_improved_sampler`)

Samples bias vectors with correlated noise for related rules:

```python
# For each rule group:
group_noise = randn()  # Shared component
for rule in group:
    individual_noise = randn()
    combined = corr * group_noise + sqrt(1 - corr^2) * individual_noise
    bias[rule] = mean[rule] + std[rule] * combined
```

**Rationale:** If "Sell_Sturgeon" should be boosted, probably all "Sell_*" rules should be too.

### 4. Integration into `run_agent_generic.py`

New environment variables:
- `CEM_GROUPED_SAMPLING=1` - Enable grouped sampling
- `CEM_GROUP_CORR=0.7` - Correlation strength (0=independent, 1=fully correlated)
- `CEM_TEMPORAL_BIAS=1` - Enable phase-aware biases
- `CEM_TEMPORAL_BLEND=0.3` - How much to blend phase bias with base

## Test Results

| Configuration | Rent1 | Rent2 | Crowns | Survival@800 | CEM Score |
|--------------|-------|-------|--------|--------------|-----------|
| Grouped + Temporal | 83.8% | 16.1% | 16.2% | 1.9% | 246 |
| Grouped Only | 79.9% | 20.1% | 20.1% | 3.1% | 239 |
| Baseline (max_fish) | 50.9% | 48.9% | 49.1% | 22.2% | 286 |
| Baseline (jan9) | 50.1% | 49.6% | 49.9% | 33.6% | 264 |

**Note:** High variance between runs makes exact comparisons difficult, but the trend is clear - improvements hurt performance.

## Analysis: Why Did These "Improvements" Fail?

### 1. Grouped Sampling Reduces Exploration Diversity

The CEM's strength comes from independent sampling - it can discover surprising combinations like "boost Sell_Sturgeon but penalize Sell_Sardine." Grouped sampling forces related rules to move together, eliminating these discoveries.

Think of it like a genetic algorithm: diversity in the population is crucial for finding good solutions. Correlated sampling reduces effective population diversity.

### 2. Temporal Bias Assumes Known Optimal Phases

The phase structure (0-100 = infrastructure, 100-300 = fishing, 300+ = selling) is our human intuition, not necessarily optimal. The vanilla CEM discovers its own implicit phase structure through the bias values it learns.

By forcing our phase assumptions, we may be overriding better strategies the CEM would find naturally.

### 3. The Fundamental Problem Remains Unsolved

The core issue isn't *how* we sample - it's that CEM evaluates end-state outcomes, not action sequences. It can't attribute credit to early investments that enable later gains.

Example: Building a furnace on day 1 costs resources and produces nothing immediately. CEM sees this as "bad" because the short-term score drops. Only much later does the furnace enable baking fish for 2x value.

CEM optimizes: `argmax E[score(final_state)]`
What we need: `argmax E[sum of future scores given this action sequence]`

## Recommendations

### Keep the Code, Disable by Default

The implementation is clean and may be useful for future experimentation:

```bash
# In agent_config.env, disable new features:
CEM_GROUPED_SAMPLING=0
CEM_TEMPORAL_BIAS=0
```

### Future Directions for Better Multi-Step Planning

1. **Model-Based Planning (MCTS)**
   - Learn a value function V(state) that predicts future score
   - Use Monte Carlo Tree Search to plan action sequences
   - Evaluate actions by V(next_state), not immediate reward

2. **Sequence Learning from Successful Traces**
   - Record full action sequences from high-scoring runs
   - Train on (state, action) pairs from successful trajectories
   - Imitation learning instead of pure optimization

3. **Hierarchical Options**
   - Define high-level "options" like "upgrade fishing rod" (multi-step macro)
   - CEM optimizes which options to pursue, not individual rules
   - Options encapsulate the multi-step nature

4. **Curriculum Learning**
   - Start with short horizons (just make Rent1)
   - Gradually increase horizon as agent succeeds
   - Build up capability incrementally

### Keep Policies Simple

The key insight from previous sessions remains valid: simple policies that CEM can optimize beat complex policies that confuse it. The best strategy is giving CEM problems it can solve, not trying to make CEM solve harder problems.

## Files Changed

```
signamancy/agent/cem_improved.py     # NEW - Improved CEM module
signamancy/agent/run_agent_generic.py # Modified - Integration
agent_config.env                      # Modified - New env vars
docs/cem_improvements_report.md       # NEW - This report
```

## How to Use

```bash
# Run with improved CEM features (for experimentation):
export CEM_GROUPED_SAMPLING=1
export CEM_GROUP_CORR=0.5  # Try lower correlation
export CEM_TEMPORAL_BIAS=1
export CEM_TEMPORAL_BLEND=0.2
./run_agent.sh

# Run with baseline (recommended):
export CEM_GROUPED_SAMPLING=0
export CEM_TEMPORAL_BIAS=0
./run_agent.sh
```

## Conclusion

This session was a valuable negative result. We implemented reasonable-sounding improvements based on human intuition about rule relationships and game phases, but empirical testing showed they don't help. The lesson: trust the optimizer's emergent behavior over our imposed structure, and focus future efforts on fundamentally different approaches (model-based planning, sequence learning) rather than incremental CEM modifications.

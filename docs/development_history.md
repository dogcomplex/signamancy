# Signamancy Development History

## Project Overview
Signamancy is a symbolic rule engine for expressing game/system mechanics through token-based asynchronous state transitions. Rules compile down to sparse matrix operations that run in tensor batches on GPU via PyTorch.

**Core syntax**: `LHS => RHS` - tokens consumed from left, produced on right.

## Farm Game Challenge
The test bed is a farming roguelike based on "Another Farm Roguelike". Key mechanics:
- **Rent ladder**: 15 tiers from 1,000 to 20.48M gold
- **Water budget**: 225 water/day, reset on day end
- **Saturday deadline**: Must pay Rent1 (1000 gold) by first Saturday or GAME OVER (universes stuck forever)
- **Finite terrain**: ~130 trees, limited rocks/ore - resources don't regenerate

## Session 1: Policy Tuning Breakthrough

### Problem Discovery
- Original policy over-weighted rent payments (23-25) but rent only fires when you HAVE gold
- Universes were dying because they ran out of water and not ending days
- Only 0.4% of universes passed Rent1

### Key Insight: Saturday Night Bug
`ID_Saturday_Night` requires 🏦 token (only produced when Rent1 is paid). If you don't hit 1000 gold by first Saturday = permanent stuck state.

### Policy Evolution
| Policy | Rent1 % | Key Change |
|--------|---------|------------|
| Original | 0.4% | Rent priority 23-25 |
| Fundamentals | 15.5% | ID_Day boosted to 30.0, sell at 20.0 |
| Gold Rush | 32% | Selling boosted to 30.0, aggressive resource conversion |
| Extreme Sell | 66% | Selling at 40.0 (highest priority), ID_Day at 35.0 |

### Best Baseline Policy (policy.max_fish.signa)
- **97% Rent1**, **35% Survival at 800 steps** with fishing-focused strategy
- Fish provide excellent gold/water ratio (10-95 gold for 4 water)

---

## Session 2: DreamerV4 Integration

### Motivation
CEM (Cross-Entropy Method) optimizer couldn't solve multi-step credit assignment:
- CEM tests random bias perturbations, can't attribute success to specific early decisions
- Need value function V(s) to predict expected future score

### DreamerV4 Paper Insights (docs/2509.24527v1.pdf)
Key concepts from Hafner et al:
1. **World model** - Causal tokenizer + dynamics model (we skip this - engine IS our world model)
2. **Value function V(s)** - Predicts expected future score for credit assignment
3. **λ-returns (GAE)** - Generalized Advantage Estimation with γ=0.99, λ=0.95
4. **PMPO** - Uses sign of advantages, not magnitude (more stable)
5. **Symlog** - `sign(x) * log(1 + |x|)` for stable value prediction across scales
6. **Twohot** - Categorical distribution over value buckets for robustness

### Implementation Files
- `signamancy/agent/value_network.py` - ValueNetwork class with:
  - 3-block encoder (BIT, BYTE, FLOAT)
  - Symlog/twohot value predictions
  - Gradient-based advantages: `∂V/∂state × rule_outputs`
  - Simulation-based advantages: top-K rule evaluation

- `signamancy/agent/replay_buffer.py` - Trajectory storage with GAE λ-returns

- `signamancy/agent/actor_critic.py` - Training loop with:
  - Advantage normalization (zero mean, unit variance)
  - PMPO-style sign-based advantage handling
  - Checkpoint save/load with best_survival tracking

- `signamancy/engine.py` - Added advantage injection:
  - `set_advantage_biases()` / `clear_advantage_biases()`
  - Injected in `_resolve_conflicts()` at rule selection

### Configuration (agent_config.env)
```
VALUE_NET_ENABLED=1       # Enable value network
VALUE_NET_TRAIN=0         # 0=inference, 1=training mode
VALUE_ADV_WEIGHT=1.0      # Advantage scaling factor
VALUE_GRADIENT_MODE=0     # 0=simulation-based, 1=gradient-based
VALUE_TOPK=20             # Rules to evaluate per universe
VALUE_USE_SYMLOG=1        # DreamerV4 symlog transform
VALUE_USE_TWOHOT=1        # DreamerV4 categorical values
VALUE_USE_PMPO=1          # Sign-based advantages
```

### Training Challenges & Solutions

**Problem 1: Gradient-based advantages too noisy**
- Initial `∂V/∂state × rule_outputs` approximation hurt performance
- Solution: Implemented true simulation-based advantages (compute V(next_state) for top-K rules)

**Problem 2: Online training unstable**
- Training while using advantages created feedback loops
- Solution: Train with `VALUE_ADV_WEIGHT=0.0`, then inference with trained network

**Problem 3: Advantage magnitudes dominating policy**
- Raw advantages had high variance
- Solution: Normalize to zero mean, unit variance before scaling

### Results with Value Network
| Configuration | Crown | Rent2 | Survival@800 |
|--------------|-------|-------|--------------|
| Baseline (no VN) | 83-84% | 79% | 7-8% |
| VN + Simulation Advantages | **94.7%** | **80.1%** | **18.2%** |

**Key improvement**: Simulation-based advantages + DreamerV4 features + advantage normalization

---

## Important Technical Details

### Policy File Conventions
- ALL weights MUST be in SINGLE `♥ =>` rule (multiple would conflict)
- Policy tokens (♥ID_RuleName_Weight) merge with physics rules
- Can add conditional rules for phase-based behavior (advanced)

### CEM Parameters
```
CEM_ITERS=0               # Disabled when using value network
CEM_TRAIN_HORIZON=200     # Steps per training episode
CEM_OBJECTIVE=max         # max or avg
CEM_POP=8                 # Population size
```

### Engine Details
- Batch size typically 4096 parallel universes
- `DECISION_ONLY=1` - Only count steps with real choices
- `PHYSICS_BURST_MAX=128` - Max physics steps between decisions
- `AGENT_USE_CRN=0` - Disable common random numbers for variance

### Checkpoints
- `value_net.pt` - Current trained network
- `value_net_best.pt` - Best survival rate checkpoint
- `value_net_pre_dreamerv4.pt` - Before DreamerV4 features

---

## Success Metrics
- **Short-term**: Consistently reach Rent1+ (1000 gold) - ACHIEVED (97%+)
- **Medium-term**: Maximize survival at 800 steps - Currently 18-27%
- **Long-term**: Reach higher rent tiers, explore farming/processing strategies

---

## Next Steps & Open Questions

### Promising Directions
1. **More training** - Accumulate more trajectories for value network
2. **Curriculum learning** - Start with shorter horizons, gradually extend
3. **Phase-based policy** - Different strategies for early game vs late game

### Technical Debt
- Best score reporting shows -1000000000 (placeholder not updated)
- Training iteration counter not incrementing properly

### Unexplored Features
- Conditional policy rules (trigger on game state)
- Farming/processing strategies for sustainable late-game income
- Tree regrowth mechanics (if any)

---

## Key Files
| File | Purpose |
|------|---------|
| `games/farm/recipes.csv` | Farm game rules (451 lines) |
| `policy.llm_balanced.signa` | Current best policy |
| `policy.max_fish.signa` | Fishing-focused policy |
| `agent_config.env` | Runtime configuration |
| `signamancy/agent/run_agent_generic.py` | Main training/evaluation script |
| `signamancy/agent/value_network.py` | DreamerV4-inspired value network |
| `signamancy/agent/actor_critic.py` | Training loop |

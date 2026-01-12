# Session 3: Crown Optimization & Extended Horizon

## Goal Clarification
The true objective is **maximum crowns (weeks survived)**, not just survival. Each rent payment produces one 👑 crown.

## Key Changes Made
1. **Extended horizon**: 800 → 1200 steps
2. **Crown-weighted objective**: `⛳👑75.0 ⛳💰25.0` (3:1 crown vs gold)
3. **Sustainable income policy**: Added beehive/honey support

## Findings

### Discovery 1: Universes ARE reaching multiple rent tiers
- 79% reach 🏦2️⃣ (Rent2 - paid 1000 gold)
- 18.6% reach 🏦3️⃣ (Rent3 - paid 2500 gold)
- ~0% reach 🏦4️⃣ (Rent4 - need 5000 gold)

### Discovery 2: Crown-only objective FAILED
- Changing to `TARGET_RESOURCE_PREFIXES=👑` caused survival collapse (2600 → 235)
- Gold is essential as intermediate reward signal
- Reverted to combined objective with crown weighting

### Discovery 3: Resource depletion is the barrier
- Max gold accumulated: ~4000-4500 (under Rent4's 5000 requirement)
- Survival drops sharply after step 600 (from 94% to <2% at step 1200)
- Universes that reach Rent3 often die before accumulating Rent4

## Training Results
| Passes | Best Survival | Crown Rate | Notes |
|--------|--------------|------------|-------|
| 20 | 30.3% | 100% | With sustainable income policy |
| +30 | 30.3% | 100% | Converged, no further improvement |

Loss converged to ~1.27 (from 2.9).

## Policy Changes (policy.llm_balanced.signa)
Added sustainable income support:
- `ID_Build_Beehive_32.0` - Build beehives for daily honey
- `ID_Day_Beehive_Honey_34.0` - Collect daily honey
- `ID_Sell_Honey_40.0` - Sell honey for gold
- `ID_Build_Fishtrap_32.0` - Build fish traps (raised from 26)

## Current Bottleneck Analysis

### Why Rent4 is Hard
1. **Gold requirement**: 5000 gold (2x Rent3's 2500)
2. **Resource depletion**: ~130 trees finite, ore limited
3. **Water economy**: 225 water/day constrains actions
4. **Time pressure**: Only 7 days per week to accumulate gold

### Potential Solutions (Not Yet Implemented)
1. **Farming**: Crops provide sustainable income but require:
   - Hoe (♠), seeds, watered plots
   - Multi-day growth cycles
   - Animal feeding chains for higher-value products

2. **Processing chains**:
   - Fish → Baked Fish (1.8x value)
   - Fish → Preserved Fish (2.6x value)
   - Ore → Bars (3-4x value)

3. **Infrastructure investment**:
   - More fishtraps for passive fish income
   - Beehives for daily honey
   - Furnaces for ore smelting

## Next Steps
1. **Farming/processing policies** - Higher multipliers than raw sales
2. **Infrastructure-first strategy** - Build sustainable income early
3. **Phase-based policy** - Different strategies for early vs late game

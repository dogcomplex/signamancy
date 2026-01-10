# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Signamancy is a symbolic rule engine for expressing game and system mechanics through token-based asynchronous state transitions. Rules compile down to sparse matrix operations that can run in tensor batches on GPU via PyTorch.

The core syntax is production rules: `LHS => RHS` where tokens are consumed from the left and produced on the right. Emojis are used for readability but any string can be a token.

## Running the Engine

```bash
# Activate the virtual environment
# Windows:
signamancy\.venv\Scripts\activate
# Unix:
source signamancy/.venv/bin/activate

# Run the farm game simulation
python -m signamancy.run_farm

# Run diagnostics
python -m signamancy.run_diagnostics

# Run benchmarks
python -m signamancy.run_benchmark
```

Environment variables:
- `ENGINE_PROFILE_PHASES=1` - Enable engine phase profiling
- `ONESHOT_BASES=ID_Start` - Comma-separated list of one-shot rule bases

## Architecture

### Core Pipeline: Parser → Compiler → Engine

1. **TokenRegistry** (`signamancy/registry.py`): Hashes token strings to 64-bit IDs, tracks block types (BIT/BYTE/FLOAT), and assigns optimized GPU indices during "compile_layout()"

2. **SignamancyParser** (`signamancy/parser.py`): Parses rule text into `Rule` objects. Handles:
   - Priority syntax: `❗` or `❗N` for priority levels
   - Equivalence sugar: `A <=> B` expands to bidirectional rules
   - Property sugar: `A :> B C` creates `A_B`, `A_C` tokens
   - Mutual exclusion: `A => B | C` for branching
   - Probability: `A => B%30 C%70`

3. **SignamancyCompiler** (`signamancy/compiler.py`): Converts rules to sparse matrices (`KernelData`). Separates tokens by block type for GPU memory layout optimization.

4. **SignamancyEngine** (`signamancy/engine.py`): The "Sensus Runtime" - executes compiled rules via vectorized validity checking and sparse matrix updates. Supports:
   - Batch simulation (default 1024 parallel universes)
   - Priority resolution and single-action mode
   - CPU callbacks for complex logic
   - Trace capture for debugging

### Data Files

- **Rule files**: `.signa` files or CSVs with `ID,Recipe` columns (see `games/farm/recipes.csv`)
- **Block Types**:
  - `BIT`: Boolean flags (0/1)
  - `BYTE`: Integer quantities (0-255)
  - `FLOAT`: Continuous values

### Key Rule Syntax

```
🪓 🌳 => 🪓 🤎3          # Catalyst (🪓 unchanged) + production
❗ 🌱 💧3 => 🌳           # Priority rule (fires before non-priority)
❗2 A => B                # Higher priority (❗2 > ❗1 > ❗ > none)
A => B%30 C%70           # Probabilistic outputs
🚫Token                  # Inhibitor (rule blocked if Token present)
TokenX                   # Consume-all suffix (reduce to zero)
Token5-10                # Quantity range output
```

### Example Games in `/games/`

- `farm/recipes.csv`: Farming roguelike with crafting, day/night cycles, rent progression
- `pokemon.txt`: Pokemon Red rules for menus and combat
- `crafter/`: Minecraft-inspired survival game rules
- `baba.txt`: Baba Is You puzzle mechanics

## Code Conventions

- Token names often use emoji for compactness
- Rule IDs in CSVs follow pattern `ID_ActionName`
- Policy files (`.signa`) can set rule biases via `♥ID_RuleName_Weight` syntax
- The `SignamancyBridge` provides a Python API for state introspection

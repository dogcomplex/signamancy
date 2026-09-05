# SIGNAMANCY PROJECT MAP

## 1. WHAT SIGNAMANCY IS

Signamancy is a **symbolic token-rewriting system for state-transition modeling** where tokens (represented as emojis or strings) are classified into loose categories called SIGNS. The core mechanism is the production rule `LHS => RHS`: the left-hand side tokens are consumed (decreased in quantity) and right-hand side tokens are produced (increased). Catalysts—tokens on both sides—enable conditional logic without consumption. Complex game mechanics, simulations, and process models emerge from the interaction of simple rules. The rules compile down to sparse PyTorch matrices for GPU-accelerated batch execution, making the simple syntax deceptively efficient.

**Key design principle:** Data-driven logic where behavior lives in rules (axioms), not hardcoded features, enabling modularity and rule discovery from observation.

---

## 2. COMPONENTS BUILT: INVENTORY & STATUS

| Component | Location | Status | Notes |
|-----------|----------|--------|-------|
| **Parser** | `signamancy/parser.py` | WORKING | Converts `.signa` rule text to Rule objects; handles priority (`❗N`), equivalence (`<=>`), properties (`:>`), branching (`\|`), probability (`%`) |
| **Compiler** | `signamancy/compiler.py` | WORKING | Converts Rule objects to sparse `BlockKernels` matrices (separate BIT/BYTE/FLOAT blocks for GPU memory layout) |
| **Engine** | `signamancy/engine.py` | WORKING | "Sensus Runtime v2" — vectorized rule execution; batch simulation (1024 parallel universes), priority resolution, CPU callbacks, trace capture |
| **TokenRegistry** | `signamancy/registry.py` | WORKING | Hashes token strings to 64-bit IDs, assigns optimized GPU indices during compile layout, tracks block types |
| **RL Agent** | `games/farm/farm.py`, `farmgpt.py`, `farmfresh.py` | PARTIAL | Deep exploration RL on farm game; actor-critic / value-net agents for policy learning; tested on rent/survival challenges |
| **Rules-Discovery** | (none yet) | STUB | Intended to derive rules from game logs/observations (mentioned as a goal in README) |
| **Farm Game** | `games/farm/recipes.csv` | WORKING | ~50 recipes, day/night, rent, fishing, crafting; tested with learned policies; best baseline achieves 95%+ rent & 35% survival |
| **Pokemon Rules** | `games/pokemon.txt` | PARTIAL | Menu/combat mechanics specified up to first rival battle; not yet compiled/executed |
| **Space/Grid Navigation** | `games/space.txt` | WORKING | Hand-derived rules showing 4-directional nav from single forward-view observations (relates to CSCG hippocampus theory) |
| **Other Games** | `games/{baba,snake,minigrid,alice,tictactoe}.txt` | STUB | Rule sketches, not compiled or executed |
| **Bridge API** | `signamancy/bridge.py` | WORKING | Python introspection layer for engine state, used by RL agents |

**STATUS SUMMARY:** Core pipeline (parse → compile → execute) is **production-ready**. Farm game domain is **functional** with RL agents. Rules-discovery is entirely **unbuilt** and represents the stated major research goal.

---

## 3. AXIOM/RULE SYSTEM: PROGRESSION FROM MONOSTATE TO FUNCTIONS

The system begins with a single simple form and provides increasingly powerful syntax as syntactic sugar, all **theoretically derivable** from the base `=>` rule. Detailed in `axiom_types.txt` and `DOCUMENTATION.md`:

### Base: Production Rules

```
LHS => RHS
```
- Tokens on LHS consumed (quantity decreased); RHS produced (increased).
- **Quantities:** `🥬3 🍅2 => 🥗` means consume 3 lettuce + 2 tomato, produce 1 salad.
- **Catalysts:** Token on both sides acts as condition (IF statement).

### Progression

1. **Monostate Graph**: Single global-state token → next-state token (trivial but complete).
2. **Axiom Matrix**: Multiset of tokens; each rule a matrix operation on token quantities.
3. **Sparse Matrix**: Only specify relevant tokens (ignore unchanged ones); vastly more readable.
4. **Production with Quantities**: Append numbers to tokens (`🥬3`); implicit subtraction on LHS, addition on RHS.
5. **Floating-point Math**: Quantities can be decimals; implicit rule: if `LHS_qty >= threshold`, rule matches.

### Extensions (Syntactic Sugar, Derivable)

- **Priority (`❗`, `❗N`)**: Higher priority rules fire first. Desugars to error rules that invalidate lower-priority paths. **Necessary** because otherwise ambiguous rules have equally valid executions (breaks determinism for IF/ELSE).
  
- **Existential vs. Negation (`<=>` with `✔`/`✖`)**: 
  - `🌞✔` = "sunny is valid/present"
  - `🌞✖` = "rain definitely absent" (intuitionistic logic distinction from classical "not present")
  
- **Scopes/Listeners** (not yet implemented): `⬅(🐍) => 🐍` (move snake from left pixel to current); syntactic sugar for flat prepended tokens.

- **Multiplication** (complex): `🥬X 🔪Y ✴ => ✴ 🥗(X*Y)` — nested rules simulate multiply-and-accumulate.

- **Randomness**: `🎲seed => 🎲N | ... | 🎲M` (seed generates random roll); Linear congruential pseudorandom via cascaded rules.

- **Named Functions**: `🌳🪓 => (🌳 => 🤎3)` — reusable higher-order rules (theoretical; not yet compiled).

**Key Unsolved Problem** (flagged in `axiom_types.txt`):  
The `=>` (directed) vs. `<=>` (bidirectional/equivalence) generalization. Many rules are reversible in principle, but priority flags and temporal directionality make this ambiguous. Current approach: use `=>` unless explicitly symmetric.

---

## 4. CATEGORY-THEORY GROUNDING

Detailed in `categories.txt`. The system maps to standard algebraic structures:

| Structure | Signamancy Analogy | Intuition |
|-----------|-------------------|-----------|
| **SET** | Discrete state space, permutations, FSM states | States as set elements; rules as state-set bijections |
| **GROUP** | Automorphism groups, covering spaces | Reversible moves; team symmetry (players swap, team invariant) |
| **RING** | Numbers + addition/multiplication | Quantities and their arithmetic; tokens as module elements |
| **VECT_K** | Matrices, linear transformations | Sparse tensors; rule kernels as linear maps |
| **POSET** | Lattices, DAGs, to-do lists with dependencies | Priority ordering; rule precedence hierarchy |
| **CAT** | Games, natural transformations | Rules as morphisms; state transitions as categorical paths |

**Mappings to Computational Models:**
- **Petri Nets**: Places (token pools), transitions (rules), arcs (LHS/RHS), tokens (quantities), firing (execution).
- **Term Rewriting**: Rules as rewrite steps; confluence and termination properties.
- **Chemical Reaction Networks**: Species (tokens), reactions (rules), stoichiometry (quantities), catalysts (unchanged reactants), rate laws (priority/probability).
- **Operads**: Compositions of operations; functions as first-class tokens.

**Note:** These are isomorphic presentations; Signamancy is the *assembly-code* level—simple but expressive—before specializing to domain.

---

## 5. GAMES/DOMAINS: WHAT EACH DEMONSTRATES

| Game | File | Status | What It Demonstrates |
|------|------|--------|----------------------|
| **Space/Navigation** | `games/space.txt` | WORKING | Grid navigation (3x5 grid, mouse moving) derived **solely from forward-view observations** (`⬆⬜ ⬇⬜ ⬅⬜ ➡⬜`) and directional input. No explicit coordinate tracking; position emerges from rule interactions. **CRITICAL:** This hand-derivation maps to CSCG "clone-structured causal graph" theory—the observation-based hippocampus model from Raju et al. (Dileep George's group, Google DeepMind), Sci. Adv. 2024, "Space is a latent sequence." Flag this connection. |
| **Farm Roguelike** | `games/farm/` | WORKING | Farming, fishing, mining, crafting, day/night, rent, shopping. ~50 recipes. RL agents trained via PPO/actor-critic; best policy (boost_fish) achieves 95%+ rent-clearing, 35% survival. Demonstrates complex multi-step planning and resource min-maxing. |
| **Pokemon Red** | `games/pokemon.txt` | PARTIAL | Menu navigation, trainer battles, item management, player movement. Rules defined up to first rival battle. Not yet compiled or executed. Intended to show full game-state complexity. |
| **Baba Is You** | `games/baba.txt` | STUB | Puzzle rules where rules themselves are objects that can be manipulated. Rule-as-data exemplified. |
| **Tictactoe** | `games/tictactoe.txt`, `tictactoe2.txt` | STUB | Simple turn-based game; multiple rule formulations (attempt 6 marked "best so far"). Not executed. |
| **Snake** | `games/snake.txt` | STUB | Movement, collision, length. Untested. |
| **MiniGrid** | `games/minigrid.txt` | STUB | Keys, doors, grid movement. Untested. |

**Observation:** Farm is the **proof-of-concept**; space.txt is the **theoretical anchor** (CSCG connection). Others are **sketches** awaiting implementation.

---

## 6. STATE & OPEN PROBLEMS

### Finished
- Core parser, compiler, engine pipeline.
- Farm game ruleset and RL training harness.
- GPU batch execution via PyTorch sparse tensors.

### Paused / Partial
- **Rules-Discovery Engine:** README states this is a major goal — "formalize the discovery and creation of these rules from base observations of states in an arbitrary game/system." Currently there is no systematic algorithm; the game rules in the repo were hand-derived. Noted as "may still use a bit too much cleverness for an arbitrary AI or offline algorithm to just derive by trial and error."
  
- **Pokemon rules compilation:** Rules are written but not integrated into the engine.

- **Scope/Listener syntax:** Proposed for spatial/local rules (each grid cell as sub-state) but not implemented.

- **Higher-order functions in rules:** Tokens-as-functions (`🌳🪓 => (...)`) are theoretically sound but not compiled.

### Unsolved / Flagged

1. **Directed (`=>`) vs. Bidirectional (`<=>`) Generalization:**  
   When should rules be reversible? Priority and temporal models break symmetry. Current approach: use `=>` as default; make `<=>` explicit for equivalences. Needs formalization.

2. **Priority Ordering Complexity:**  
   Priority (`❗N`) resolves ambiguity but imposes order on axiom space, breaking the property that "all paths are equally valid." The note in `axiom_types.txt` flags this as a "slippery slope" — each rule risks needing priority. Proposed alternative: use explicit non-existence tokens (`✖`) to make only one rule applicable at a time. But this requires knowing exact absence (not just "not yet created"), which is stronger than intuitionistic logic prefers.

3. **Quantity Threshold Ambiguity:**  
   Rule `🌱 💧3 => 🌳` matches if `💧 >= 3`. But what if `💧 == 2`? Should the plant die? Without an explicit rule, priority, or negation token, the system is underspecified. Proposed: add rules like `🌱 💧1-2 => 💀` or use `🌱 💧✖3 => 💀` ("water definitely not 3+").

### Known Limitations

- **No formal rule-discovery algorithm** (acknowledged in README).
- **Multiplication is verbose** (5+ rules to compute `X*Y`).
- **Randomness requires pseudoRNG via cascaded rules** (no native random() function).
- **Scope/spatial locality not yet implemented** (all rules operate on flat multiset).

---

## 7. CONNECTIONS TO NOTE: HUM, RL, CSCG/HIPPOCAMPUS

### To HUM (Hypothetical Unified Model)
- **Sources = SIGNS:** HUM's "sources" (fundamental information primitives) map to Signamancy's SIGNS (tokens).
- **Appear/Disappear = Crystallization/Reversion:** HUM's phase transitions (crystalline ↔ amorphous) parallel SIGNS appearing (produced via rules) and disappearing (consumed).
- **Matter/Antimatter = Positive/Negative Tokens:** HUM's symmetry may correspond to Signamancy's positive and negative token quantities (proposed in `categories.txt`: use separate tally of surpluses vs. deficits).
- **Catalysts = Conditionals:** HUM's catalyst concept (active but unchanged) maps directly to Signamancy production rules with catalysts.

### To RL (Reinforcement Learning)
- **Farm RL agents:** Already integrated. PPO/actor-critic trained on recipe space; policies encoded as `.signa` files (rule-weight biases).
- **Owner's note:** "LUSTRE/BEST merge with this" — suggests a convergence between symbolic rule-based planning (Signamancy) and learned policy models. This is **speculative**; specific codebase not examined.

### To CSCG / Hippocampus Theory (Critical Connection)
- **Source:** Raju, Guntupalli, Zhou, Wendelken, Lazaro-Gredilla, George (Google DeepMind), Sci. Adv. 2024, "Space is a latent sequence: A theory of the hippocampus." [CORRECTED: an earlier draft misattributed this to "Whittington et al." with a wrong title. Whittington et al. is the separate Tolman-Eichenbaum Machine, a different hippocampus-ML model.]
- **Mapping:** Space.txt hand-derives grid navigation **solely from forward-view observations** (`⬆⬜ ⬇⬜ ⬅⬜ ➡⬜ + direction_input`) and causal rules.  
  - No explicit coordinates (x, y).
  - No global map.
  - Position emerges from rule-chaining.
  
  This **precisely matches** the CSCG model: a clone-structured graph where nodes represent observed state snapshots and edges are causal transitions. The mouse's "position" is the **current rule-matched state**, not an abstraction.
  
- **Why this matters:** If Signamancy rules can derive spatial cognition from pure observation + causality, it provides an **implementational bridge** between symbolic reasoning (Signamancy) and neural models (hippocampal place cells). This is **not yet formally connected** in the codebase but is implicit in space.txt.

---

## 8. FILE STRUCTURE (KEY PATHS)

```
G:\LOKI\LOCUS\SIGNUM\signamancy\
├── signamancy/                      # Python package (core engine)
│   ├── parser.py                    # Parses .signa text → Rule objects
│   ├── compiler.py                  # Rule → sparse matrices (BlockKernels)
│   ├── engine.py                    # Sensus Runtime; vectorized execution
│   ├── registry.py                  # Token → ID mapping; block type tracking
│   ├── bridge.py                    # Python API for state introspection
│   └── signa_types.py               # Data structures (Rule, ParsedToken, etc.)
│
├── games/
│   ├── farm/
│   │   ├── recipes.csv              # ~50 recipes (ID, Recipe cols)
│   │   ├── farm.py                  # RL training script (PPO)
│   │   ├── farmgpt.py               # GPT-based planning agent
│   │   └── farmfresh.py             # Fresh approach (value net)
│   ├── space.txt                    # CSCG grid navigation (CRITICAL)
│   ├── pokemon.txt                  # Menu/combat rules (partial)
│   ├── baba.txt, snake.txt, etc.    # Sketches (untested)
│
├── engine/
│   ├── parser.py                    # Older parser (superseded?)
│   ├── interpreter.py               # Stub
│   └── analysis_parser.py           # Analysis / AST tools (partial)
│
├── docs/
│   ├── axiom_types.txt              # Theoretical progression (BASE → EXTENSIONS)
│   ├── categories.txt               # Category theory mappings
│   ├── DOCUMENTATION.md             # Primer on tokens, rules, catalysts, priority
│   └── claude_logged_convos.txt     # Conversation logs
│
├── policy.*.signa                   # Learned policies (rule weights)
├── README.md                        # Brief overview
├── CLAUDE.md                        # Project guidance (recent; well-written)
├── NOTES.txt                        # Unit normalization, format ideas
├── Origins.md                       # Etymology of "sign" + epistemological context
├── lexicon.txt, lexicon_2.md        # Token/emoji reference
└── BUILD RECIPES.txt                # Historical notes
```

---

## SUMMARY: THREE CRITICAL TAKEAWAYS

1. **Core Engine is Mature:** Parser → Compiler → Engine pipeline is functional and production-tested on farm game. GPU batch execution works. This is **ready for deployment**.

2. **Rules-Discovery is the Moonshot:** The stated goal (README, DOCUMENTATION) is to **formalize algorithmic rule derivation from observations**. Currently all rules are hand-crafted. This is the **main research frontier**; no existing implementation.

3. **Space.txt is the Theoretical Anchor:** The grid-navigation rules hand-derived solely from observations and causality **maps onto CSCG hippocampus theory** (Raju et al. 2024, George/DeepMind). This connection is **not yet explicitly formalized** but represents a potential bridge between symbolic reasoning and neural cognition. Flagging for future investigation.

---

**Map Generated:** 2026-07-07  
**Source:** `G:\LOKI\LOCUS\SIGNUM\signamancy\` (prod copy); `projects/signamancy/` (intended symlink destination, currently empty)

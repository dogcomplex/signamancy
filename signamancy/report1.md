**To:** Lead Systems Engineer
**From:** Architecture Team
**Date:** Nov 2025
**Subject:** Technical Specification & Implementation Directives: SIGNAMANCY Engine (v1.0)

### Executive Summary

We are building a **Vectorized Production System** that translates high-level symbolic logic (text-based state transitions) into high-throughput GPU tensor operations.

Unlike standard game loops or rules engines (which iterate sequentially), this engine utilizes **Sparse Matrix Multiplication** to execute thousands of rules across thousands of parallel simulation "universes" simultaneously.

This architecture prioritizes **Throughput** and **Uniformity** over memory optimization. We are effectively building a cellular automaton where the "cells" are semantic tokens.

---

### 1. Core Architecture: The "Block-Archetype" Memory Model

To avoid **Warp Divergence** on the GPU, we cannot treat all tokens generically. We classify tokens into three storage archetypes based on their behavior, stored in separate contiguous blocks in VRAM.

*   **Block 0: BIT (Flags/Logic)**
    *   **Type:** `int8` (Packed 2-bit semantics).
    *   **Values:** `0` (Unknown), `1` (True), `-1` (False/Inhibited), `2` (Error).
    *   **Use Case:** 90% of the state. Permissions, boolean flags, existence checks.
    *   **Logic:** Bitwise operations.
*   **Block 1: BYTE (Inventory/Counts)**
    *   **Type:** `uint8` (0-255).
    *   **Use Case:** Discrete resources (items, ammo, small counters).
    *   **Physics:** Supports **Carry-Lookahead**. Overflows (>255) automatically cascade to parent units (e.g., 256 Apples $\to$ 1 AppleBox) within the physics kernel.
*   **Block 2: FLOAT (Physics/Chaos)**
    *   **Type:** `float32`.
    *   **Use Case:** Continuous variables (Temperature, Energy) and Probabilistic states.
    *   **Logic:** Full FP32 math.

**Directive:** Do not mix types in a single tensor. The `Registry` module must sort tokens into these buckets at compile time.

---

### 2. The "Particle" Probability Model

We are **not** using Bayesian floats to represent uncertainty. We are using **Monte Carlo Particles**.

*   **Batch Dimension:** The Engine runs with a batch size of $N=1024$.
*   **Meaning:** Row $i$ represents "Universe $i$."
*   **Probabilities:** A rule `A => B%50` generates a random mask across the batch. In ~512 rows, B becomes 1; in the others, it remains 0.
*   **Observation:** The UI ("Signum Layer") is responsible for collapsing this state. It calculates `Mean` and `StdDev` across the batch to display "Apples: ~5" to the user. The Engine never collapses state unless explicitly forced.

---

### 3. Critical Implementation Details (The "Gotchas")

The provided code skeletons are 90% complete. The following logic gaps **must** be addressed during implementation to ensure mathematical correctness.

#### A. The Validity Check (Fixing the "Sum" Bug)
The naive implementation checks if `Sum(Available) >= Sum(Required)`. This is wrong; it allows 2 Apples to satisfy a requirement for 1 Apple + 1 Banana.
*   **Required Implementation:** Use a **Violations Kernel**.
    1.  Expand sparse rule indices to gather specific token values from the state.
    2.  Compute `Deficit = Required - Available`.
    3.  Aggregate deficits per rule.
    4.  Valid mask = `(Total_Deficit == 0)`.

#### B. Mutual Exclusion (Gumbel-Max)
Signamancy supports branching: `A => B | C`.
*   **Required Implementation:** The Compiler groups these rules under a shared `MutualExclusionID`.
*   **Runtime:** The Engine must not fire B and C independently (which would duplicate A). It must calculate `Logits = log(Prob) + Gumbel_Noise` and perform an `argmax` across the Mutex group per universe.

#### C. Variance Injection
The Compiler currently collapses ranges (`1-5`) into a mean (`3`).
*   **Required Implementation:** The Compiler must output two matrices for the Output layer: `Out_Mean` and `Out_Std`.
*   **Runtime:** `Delta = Out_Mean + (torch.randn() * Out_Std)`. This preserves the "Chaos" inherent in the rule.

#### D. Unit Swapping (Physics Kernel)
For `BYTE` types, we rely on automatic unit scaling to keep numbers small (fitting in `uint8`).
*   **Mechanism:**
    *   Perform updates in `int16` accumulator.
    *   Calculate `Overflow = Val // 256`.
    *   Use `scatter_add` to apply `Overflow` to the `Parent_Index` (lookup from `UnitMap`).
    *   Store `Val % 256` back to state.
    *   *Note:* This happens in the `_resolve_physics` sub-step.

---

### 4. The Data Pipeline (Signamancy Flow)

1.  **Text Source:** User writes `rules.txt` with emojis (`🍎 => 🧃`).
2.  **Parser:** Regex extraction. Handles sugar like `<=>` (Equivalence) and `:>` (Properties). *Note: Properties are strictly for initialization/definition, not runtime rules.*
3.  **Registry:** Hashes strings to **64-bit IDs**. Assigns Block Types. Tracks usage frequency to optimize memory layout (Hot tokens $\to$ Low indices).
4.  **Compiler:** Converts Rule Objects into **Sparse COO Tensors**.
5.  **Engine:** Loads tensors to VRAM. Runs the `step()` loop.
6.  **Bridge:** Queries VRAM, computes stats (Mean/Var), converts IDs back to Strings for the UI.

### 5. "CPU Valve" Strategy

We acknowledge that GPUs cannot handle string manipulation or complex calculus efficiently.
*   **Strategy:** The Engine supports a `CPU_Callback` flag on rules.
*   **Runtime:** If a CPU-flagged rule triggers, the Engine pauses that specific batch slice, offloads the relevant state tokens to RAM, executes the Python function, and reinjects the result.
*   **Optimization:** This is a fallback. 99% of logic should be expressed as Token Transitions to run on the metal.

### 6. Filesystem & Naming Conventions

*   **`signamancy/`**: The Core Library.
    *   `registry.py`: Identity & Hashing.
    *   `parser.py`: Text processing.
    *   `compiler.py`: Matrix generation.
    *   `engine.py`: PyTorch/CUDA runtime.
    *   `bridge.py`: IO & Statistical Collapse.
*   **`examples/`**: Integration tests.
    *   `run_pokemon.py`: Validation of graph navigation and probability.

### Closing Thought
We are moving from "Scripting" to "Simulating Physics." The tokens are particles; the rules are forces. If you adhere to the **Sparse Matrix** and **Batch Parallel** paradigms, this system will scale to millions of entities without slowing down.
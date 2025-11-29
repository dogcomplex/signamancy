# Axiom Production System: Primer and Documentation

**Version:** (Based on Conversation Snapshot)
**Date:** (Current Date)

## 1. Introduction

### 1.1. Purpose and Philosophy

This document describes a declarative, token-based production system designed for modeling complex state transitions. Its core philosophy emphasizes:

1.  **Simplicity:** The fundamental mechanism is a simple `LHS => RHS` rule, representing the consumption and production of state tokens.
2.  **Explicitness:** State changes are broken down into atomic, observable transitions.
3.  **Data-Driven:** System logic resides primarily in the rules (data) rather than hardcoded engine features, allowing flexibility and easier modification.
4.  **Emergence:** Complex behaviors and structures (like spatial awareness or game progression) should emerge from the interaction of simple, local rules.
5.  **Provability (for Extensions):** Advanced syntax features should ideally be demonstrable equivalents ("syntactic sugar") of combinations of the core base rules, maintaining theoretical grounding.

This system is designed to be applicable to a wide range of domains, including game logic (UI, crafting, movement, combat), simulation, process modeling, and potentially even knowledge representation, as demonstrated through various examples. Emojis are frequently used as concise, visually distinct tokens, but any unique string can serve as a token.

### 1.2. Target Audience

This document is intended for developers, designers, and analysts who will be using or contributing to systems built with this axiom engine. Familiarity with basic programming concepts, state machines, and production systems is helpful.

## 2. The Core Axiom System

The foundation of the system is the representation of state as a collection (multiset) of tokens and the definition of rules that transform this state.

### 2.1. Tokens

*   **Definition:** A token is the basic unit of state (e.g., `🍎`, `PlayerHasKey`, `⚙️MenuOpen`, `🪵10`).
*   **Representation:** Any unique string or emoji sequence separated by whitespace.
*   **State:** The global state of the system at any point is the collection of all currently present tokens and their associated quantities.
*   **Commutativity:** The order of tokens in the state or within a rule's LHS/RHS generally does not matter.

### 2.2. Quantities

*   **Default:** A token present without an explicit quantity is assumed to have a quantity of 1.
*   **Explicit:** Quantities are appended directly to the token (e.g., `🪵10`, `💰3.5`). Both integers and floating-point numbers are supported conceptually.
*   **Zero Quantity:** A token with quantity 0 is equivalent to it being absent from the state.
*   **Unknown Quantity (`?`):** `Token?` signifies an unknown, non-zero quantity (at least 1). It flags a rule as a hypothesis needing refinement.
    *   `LHS Token? => RHS`: Unknown input quantity required (at least 1).
    *   `LHS => RHS Token?`: Unknown output quantity produced.

### 2.3. The Base Rule (`=>`)

*   **Syntax:** `LHS_Token1 LHS_Token2 ... => RHS_Token1 RHS_Token2 ...`
*   **Mechanism:**
    1.  **Matching:** A rule can potentially fire if *all* tokens listed on the Left-Hand Side (LHS) are present in the current state with quantities *at least* as large as specified on the LHS (defaulting to 1 if no quantity is given).
    2.  **Execution (Firing):** If selected for execution (see Priority, Sec 3.1), the rule consumes the specified quantities of LHS tokens (decreasing their quantities in the state) and produces the specified quantities of RHS tokens (increasing their quantities or adding them to the state).
*   **Implicit Unknowns (`?=>?`):** By default, `=>` implies `?=>?`. This means a rule might have unspecified prerequisite conditions (`?=>`) or produce unspecified side effects (`=>?`) unless proven otherwise or explicitly marked as exact (see Sec 3.4).
*   **Example (Simple Production):**
    ```
    # If 1 Wood and 1 Stone are present, consume them and produce 1 Axe.
    🪵 🪨 => 🪓
    ```
*   **Example (Quantity):**
    ```
    # Requires at least 3 Lettuce and 2 Tomato. Consumes 3 and 2 respectively, produces 1 Salad.
    # If the state had 🥬5 🍅6, it becomes 🥬2 🍅4 🥗1 after firing.
    🥬3 🍅2 => 🥗
    ```

### 2.4. Catalysts (Conditional Logic)

*   **Syntax:** A token appears on *both* the LHS and RHS of a rule.
*   **Mechanism:** The token must be present in the state (with at least the specified LHS quantity) for the rule to match, but its quantity is *not* changed by the rule firing.
*   **Purpose:** Allows rules to depend on conditions without consuming the condition token. Models "IF" statements.
*   **Example (Implication):**
    ```
    # If Sunny and Rainy are present, produce Rainbow, but keep Sunny and Rainy.
    # Models: IF Sunny AND Rainy THEN Rainbow
    🌞 🌧 => 🌞 🌧 🌈
    ```

### 2.5. Theoretical Basis (Immutable Axioms)

*   As detailed in `axiom_types.txt`, the production rule system (`=>` with quantities/catalysts) can be viewed as a concise way to manage the state transitions of a more fundamental system based on immutable axioms.
*   In the immutable view, tokens are never consumed, only generated. `🥬3 🍅2 => 🥗` could map to generating tokens like `UsedLettuce1`, `UsedLettuce2`, `UsedLettuce3`, `UsedTomato1`, `UsedTomato2`, `ProducedSalad1`. The "current state" is inferred from the complete set of generated immutable axiom tokens.
*   The production rule syntax is the preferred, practical way to define and work with the system.

## 3. Key Concepts & Core Syntax

These features are fundamental extensions or interpretations of the base system for practical use.  
Developer's Note: From a language design perspective, each of these features must be provable as a derivation from the base `=>` system before they can be used, and they should be thought of as simplifying syntactic sugar convenience for the base system.  (Since `=>` defines a recursively-enumerable Turing Machine language, this is not difficult).  Implementation of these syntax features may be done using any engine tricks available (e.g. multiplication ops), so long as they're derivable back to the base `=>` system.

### 3.1. Priority (`❗`, `❗N`)

*   **Syntax:** `❗ LHS => RHS` or `❗N LHS => RHS` (where N is an integer, higher N = higher priority). `❗` is equivalent to `❗1`.  `!` ASCII exclamation character may also be used, but `❗` is preferred for visual clarity.
*   **Purpose:** Resolves ambiguity when multiple rules match the current state. Ensures critical rules (like game over checks, safety overrides, or specific steps in an algorithm) fire preferentially. Enables deterministic IF/ELSE logic.
*   **Mechanism:** When selecting which rule(s) to fire in a given step/context, the engine *must* choose from the matching rules with the highest numerical priority level. Lower priority rules are ignored *if* a higher priority rule also matches and consumes necessary tokens.
*   **Base Rule Equivalence:** Provable by adding auxiliary error (`🚫️`) rules that invalidate execution paths where a lower-priority rule fired when a higher-priority one *could* have fired. More practically, the engine's rule selection mechanism directly implements priority checking *before* firing.
*   **Example (IF/ELSE):**
    ```
    # IF Seed has enough Water (3), THEN grow Tree (priority ensures this happens).
    ❗ 🌱 💧3 => 🌳

    # ELSE (if the above didn't fire because 💧<3), THEN Seed dies.
    🌱 => 💀
    ```

### 3.2. Equivalence / Alias (`<=>`)

*   **Syntax:** `TokenA <=> TokenB`
*   **Purpose:** Defines aliases or groups of tokens that are semantically interchangeable. Aids abstraction and generalization.
*   **Mechanism:** Sugar for two reciprocal base rules: `TokenA => TokenB` and `TokenB => TokenA`. Allows the engine to substitute one token for the other during rule matching.
*   **Base Rule Equivalence:** Trivially provable.
*   **Example:**
    ```
    # Combine two common tokens into a reversible abstraction ('couple')
    👫 <=> 👨 👩

    # Alias a verbose token into something more convenient
    DeciduousTree <=> 🌳
    ```

### 3.3. Special Tokens

*   `🎬` (START): The initial token from which the system state evolves. Produced only by the engine at startup.
*   `🏁` (END): If produced, signals the engine to halt execution. Consumed only by the engine.
*   `⌛` (STEP / Time Tick): Represents a discrete time step or event trigger. Often produced periodically by an engine clock (`⏰`) or other rules. Used to drive time-dependent logic.

### 3.4. Fidelity Levels (`🗺️`, `🔬`)

*   **Syntax:** `🗺️ RuleDefinition` or `🔬 RuleDefinition`. Placed *before* the rule.
*   **Purpose:** Distinguish between low-fidelity (`🗺️` - Map, simplified, possibly inaccurate) and high-fidelity (`🔬` - Microscope, detailed, specific) versions of rules or state descriptions. Useful for prototyping, abstraction, and gradual refinement.
*   **Mechanism:** Fidelity tokens act as classifiers. Explicit conversion rules define how to map between levels: 
    *   `🔬 (HiFi_Rule) => 🗺️ (LoFi_Rule)`: Deterministic, potentially many-to-one simplification.
    *   `🗺️ (LoFi_Rule) => 🔬 (HiFi_Guess1) | 🔬 (HiFi_Guess2)`: Non-deterministic expansion/hypothesis generation.
*   **Stability:** The `🗺️ => 🔬 => 🗺️` cycle is stable (returns the original Lo-Fi rule) because the `🔬 => 🗺️` step is deterministic.
*   **Base Rule Equivalence:** Fidelity markers are standard tokens. Conversion rules are meta-rules defining mappings *between* base rules. Provable as a rule-generation/mapping mechanism.
*   **Example:**
    ```
    # Meta-Rule: Hi-Fi burning simplifies to Lo-Fi burning
    🔬 (Air 🪵 🔥 ==> 💨 🪵Ash Heat) => 🗺️ (🪵 🔥 => 💨 🪵Ash)

    # Meta-Rule: Lo-Fi burning might be explained by Hi-Fi burning
    🗺️ (🪵 🔥 => 💨 🪵Ash) => 🔬 (Air? 🪵 🔥 => 💨 🪵Ash Heat?)
    ```

### 3.5. Exactness (`==>`)

*   **Syntax:** `LHS ==> RHS`
*   **Purpose:** Asserts that a rule is "complete" or "exact". It consumes *only* the LHS tokens and produces *only* the RHS tokens, with no unknown prerequisites (`?=>`) or side effects (`=>?`).
*   **Mechanism:** Modifies the interpretation of the arrow, overriding the default implicit `?=>?`.
*   **Base Rule Equivalence:** Represents a rule where the author asserts (or has proven) that no hidden `?=>` or `=>?` components exist. It's a claim about the rule's completeness relative to the modeled system, mapping to a base rule assumed to have no interaction with unspecified parts of the state.

### 3.6. Absence / NOT (`❌`)

*   **Syntax:** `Token❌`
*   **Purpose:** Represents the *confirmed absence* of `Token`, distinct from `Token0` (zero change in quantity).  It is a claim about the total quantity of `Token` in the system, not just a relative quantity change like most rules default to.  Aligns with intuitionistic logic.
*   **Mechanism:** `Token❌` acts as a standard token, typically used as a catalyst on the LHS.
*   **Base Rule Equivalence:** Directly provable as `Token❌` is just another token.
*   **Example:**
    ```
    # If Seed exists AND Water is confirmed absent, THEN Seed dies.
    🌱 💧❌ => 💀
    ```

### 3.7. Errors (`🚫️`)

*   **Syntax:** `🚫️`
*   **Purpose:** Standard token produced by rules to indicate a detected contradiction, invalid state, or violation of system constraints.
*   **Mechanism:** Rules are designed to check for inconsistencies and produce `🚫️`. Other rules or the engine can react to the presence of `🚫️` (e.g., halt, log error).
*   **Base Rule Equivalence:** Directly provable as `🚫️` is just another token.
*   **Example:**
    ```
    # It shouldn't be possible for a dead plant to have water.
    💀 💧3 => 🚫️
    ```

## 4. Advanced Syntax / Engine Assists (Provable Extensions)

These features add significant usability and efficiency but are demonstrably equivalent to more complex sets of base rules. Engine assistance is often recommended for practical implementation.

### 4.1. Context / Scope / Properties (`Token(...)`, `:>`, and multi-token globals)

*   **Syntax:** There are three syntax options for this feature:
    1. Global Syntax: `ContextTokenPropUpdate1  ContextTokenPropUpdate2 ...` (used as the preferred verbose global definition of properties, where the other syntaxes are just sugar for writing them more concisely)
    2. Scope Syntax: `ContextToken( PropCheck1 ... ) LHS => ContextToken( PropUpdate1 ... ) RHS`  (used for full equations of the contents of the ContextToken)
    3. Subset Syntax: `ContextToken :> ... PropUpdate1 PropUpdate2 PropUpdate3`  (used for simple property updates within a scope.  Note `:>` makes a statement about a subset of the properties of the ContextToken, not its full set of properties.)
    
*   **Purpose:** Used to refer to sub-properties, usually used for geographic locations, containers, microcosms, or abstract properties.  These could be seen like neurotransmitter receptors and effectors between separate "contexts"/cells.
*   **Mechanism:** Engine finds the `ContextToken` and its associated global property tokens (e.g., `🧍1` and `🧍1💗10`, `🧍1InventoryPotion0`). It evaluates `PropCheck` conditions (using Quantity Checks) and applies `PropUpdate` actions (using Quantity Updates) to the corresponding property tokens.
*   **Base Rule Equivalence:** Provable. Syntactic sugar for rules that explicitly list all required property tokens on the LHS/RHS and include the base-rule equivalents for checks and updates. Relies on consistent engine mapping between context and property tokens.
*   **Example:**
    ```
    # "Place 10 apples in a box":
    📦 🍎10 => 📦 📦🍎10  # multi-token Global syntax
    📦 🍎10 => 📦(🍎10)  # Scope syntax (add the apples to a box)
    # "The box contains 10 apples":
    📦 :> 🍎10  # Subset syntax (a box contains 10 apples)
    # (note the subset syntax is slightly different from the other two as it's not a transition function rule but a property assertion)
    # Advanced usage: "Place 10 apples in a box" (subset version):
    📦 🍎10 => (📦 :> 🍎10)

    # Other examples:
    # If Agent is facing ('⬆️') a walkable square ('✅'), move Agent there.
    👣(🧍) ⬆️(✅) 👉 => ⬆️(🧍)
    # Engine moves the 🧍 token from 👣 origin to ⬆️ destination.
    
    # A plane has a weight of 1000 (kg):
    🛩 :> ⚖1000


    ```

### 4.2. Quantity Checks (`>=`, `==0`/`❌`, `>`)

*   **Syntax:** `Token>=N`, `Token==0`, `Token❌`, `Token>N` (often within `(...)` scopes).
*   **Purpose:** Allow non-consuming checks on token quantities.
*   **Mechanism:** Engine performs the comparison.
*   **Base Rule Equivalence:** Provable (`>=` via destructive comparison pattern; `==0` via priority pattern; `❌` directly). Engine assist strongly recommended for efficiency.
*   **Example:**
    ```
    # If Agent has less than 1 HP, THEN Agent dies.
    🧍HP<1 => 💀

    ```

### 4.3. Math Operations:  Multiplication / Division / All / Set / etc  (`X*N`, `X/N`, `X`, `X=N`)

*   **Syntax:** Potential `calculate(...)` pattern for `X*N`, `X/N`, `X`, `X=N`.
*   **Purpose:** Atomic arithmetic updates on quantities.
*   **Mechanism:** Engine performs the calculation (much more efficiently than => addition/subtraction chains using intermediate tokens).
*   **Base Rule Equivalence:** Provable `X*N`/`X/N` via complex iterative chains. Engine assist strongly recommended for efficiency. 
*   **Example:**
    ```
    # pickup a score multiplier in a game to double your money:
    🌠 => 💰X*2  # 🌠 is consumed, and 💰 is doubled from e.g. 1000 to 2000
    
    # division: pay 1/10th of your total money to purchase a health pack:
    💰X/10 => 💗10  # 💰 is consumed from e.g. 1000 to 900, and 💗 is increased from e.g. 10 to 20

    # if player dies, set health to 0:
    💀 => 🧍💗X=0  # 💀 death is consumed, and 🧍💗 is set to 0 health

    # arbitrary math operations:
    <TODO>
    
    ```

### 4.4. Loops (FOR, WHILE)

*   **Syntax:** For loop: `⏳ {Loop conditions} => ⌛ {loop results}` continues for ⏳N times while the condition holds. 
        While: `{Loop conditions} => { Loop results }` to use no counter. ⏳ and ⌛ may be substituted for any counter variable.
*   **Purpose:** Control flow for iteration.
*   **Mechanism:** Syntactic sugar generating counter/state tokens and prioritized rules for looping and termination.
*   **Base Rule Equivalence:** Provable.

### 4.5. Functions / Subroutines (`CALL`/`RETURN`)

*   **Syntax:** `=> Func(Args) CallerID`, `FuncEnd Result CallerID => CallerID Result`.
*   **Purpose:** Modularization.
*   **Mechanism:** Syntactic sugar generating unique context tokens to manage state transitions for function calls and returns.
*   **Base Rule Equivalence:** Provable.

### 4.6. Time Delays (`DELAY N`)

*   **Syntax:** `=> DELAY N { DelayedRule }` or `=> ScheduleEventN Data`.
*   **Purpose:** Schedule future rule execution.
*   **Mechanism:** Syntactic sugar generating countdown tokens triggered by `⌛`.
*   **Base Rule Equivalence:** Provable.

### 4.7. Negation (`NOT`)

*   **Syntax:** `NOT (Cond) LHS => RHS`.
*   **Purpose:** Conditional execution based on absence.
*   **Mechanism:** Syntactic sugar for `❌` checks or priority-based exclusion patterns.
*   **Base Rule Equivalence:** Provable.

### 4.8. Randomness (`%` - Mutual Exclusion)

*   **Syntax:** `LHS => TokenA%P1 TokenB%P2 ...` (Probabilities P1, P2... sum to <= 100).
*   **Purpose:** Model probabilistic outcomes where only one result can occur.
*   **Mechanism:** Engine selects one RHS token based on probabilities.
*   **Base Rule Equivalence:** Provable using `🎲` token generation and prioritized range checks. Engine assist strongly recommended for usability and good random distribution.
*   **Example:**
    ```
    🎣 => 🐟%20 🐠%30 🐡%40 # 10% chance of nothing
    ```

### 4.9. Listener Updates (Engine Assist)

*   **Syntax:** No specific syntax, but applies when rules like `👣(🧍) ⬆️(✅) 👉 => ⬆️(🧍)` fire.
*   **Purpose:** Automatically update the bindings or context associated with relative spatial listeners (`👣`, `⬆`, `⬇`, etc.) after movement.
*   **Mechanism:** Engine detects movement and adjusts which physical grid location corresponds to `👣`, `⬆`, etc., for the moved entity.
*   **Base Rule Equivalence:** Provable only via extremely complex base rules that calculate new relative positions. Engine assist is almost essential for sanity in grid-based systems.

## 5. Non-Provable Extensions / External Logic

### 5.1. Wildcard (`...`)

*   **Syntax:** `...` on LHS or RHS.
*   **Purpose:** Explicitly indicates interaction with unspecified parts of the state or triggers external/engine logic that cannot be fully described by base rules (e.g., complex physics, network calls, non-reducible AI).
*   **Mechanism:** Acts as a placeholder or trigger. Rules with `...` cannot be fully validated solely within the base axiom system. Use sparingly.

### 5.2. Complex Calculations / AI

*   While basic math can be simulated, complex formulas (e.g., Pokémon damage calc) or sophisticated AI decision-making are often best handled by triggering external functions via specific token patterns (potentially using `...` or dedicated trigger tokens).

## 6. Modeling Paradigms & Examples (Summary of Learnings)

*   **Simple State/Crafting (`recipes2.csv`):** Core `=>` works well. Need careful quantity/cost definition. Fidelity (`🗺️`/`🔬`) useful for prototyping.
*   **UI/Menus (`pokemon.txt`, `minigrid.txt`):** Excellent fit. Use distinct tokens for screens (`⚙`), selected options (`▶`), and navigation rules (`👆`/`👇`/`⏩`/`🅱`). Verbosity necessitates templates.
*   **Grid Worlds (`AXIOMS.txt`, `minigrid.txt`, `space.txt`):** Relative listeners (`👣`/`⬆`) combined with agent context `Agent(...)` are effective. Engine assist for listener updates highly recommended. Walkability (`✅`/`❎`) abstractions useful.
*   **Async/Decentralized (`snake.txt`):** "Neurotransmitter" syntax (`=> ➡(Token)`) better than pure listeners for directed communication. Global signal propagation (`⌛`, commands) needs careful design (rule patterns or engine broadcast). Initialization can be complex.
*   **Complex Game Logic (`pokemon.txt`):** Handles turn-based flow, simple combat states, dialog well. Highlights challenges with deep memory, sequential goals, complex calculations, and massive state spaces (verbosity).
*   **Data Handling (`NOTES.txt`):** Normalization (`🧮`/`🖼`) crucial for bridging computation and presentation. Property association (`:>` / `(...)`) essential for structured data. Canonical internal representation aids efficiency.
*   **Observational Learning (`space.txt`):** System can model learning spatial structure from `(view, action) => next_view` sequences. "Transitions as tokens" is a key insight. Multi-step rules needed for disambiguation.

## 7. Theoretical Grounding

*   The system is a form of **Production System / Rewriting System**.
*   The set of reachable states/traces is **Recursively Enumerable (RE)**, assuming extensions are reducible.
*   The system is likely **Turing Complete**.
*   Mapping directly to/from **Lambda Calculus** is theoretically possible but impractical and unnatural.

## 8. Implementation Considerations

*   **Engine Role:** Rule matching, priority resolution, quantity management (including assists for `+`/`-`), event distribution (`⌛`), context resolution (`(...)`), potentially listener updates, execution of assists (`%`, `calculate`).
*   **State Representation:** Internally, a hash map/dictionary mapping canonical token indices to quantities (or a sparse vector) is efficient.
*   **Rule Matching:** Indexing rules based on required LHS tokens is crucial for performance.
*   **Tooling:** Validators, visualizers, debuggers, template compilers, and query tools are essential for managing large rule sets.

## 9. Future Work / Open Questions

*   Refining engine assistance for listener updates.
*   Developing robust patterns/extensions for agent sight/perception.
*   Modeling long-term memory and complex, multi-stage goals effectively.
*   Integrating sophisticated AI decision-making (beyond simple triggers).
*   Optimizing performance for very large state spaces and rule sets.
*   Formalizing the interaction with external code (`...`).
*   Developing comprehensive standard libraries/templates for common patterns (menus, grids, etc.).

## 10. Conclusion

This axiom production system offers a powerful, flexible, and theoretically grounded approach to modeling state transitions. Its core simplicity (`=>`, tokens, quantities, catalysts, priority) provides a solid foundation. Practical usability is significantly enhanced by well-defined, provably equivalent extensions for context, quantity operations, control flow, and data handling (`(...)`, `+`/`-`, `REPEAT`/`WHILE`, `🧮`/`🖼`, `:>`). While capable of simulating complex operations like multiplication or randomness via base rules, pragmatic engine assists are recommended for efficiency and clarity in these areas. The system excels at declarative logic for UI, crafting, basic movement, and interactions but faces challenges with extreme verbosity and modeling complex AI/memory without careful design or integration with external logic. Its strength lies in breaking down complex systems into explicit, analyzable, and potentially emergent behaviors governed by data-driven rules.

import torch
import time
import json
from signamancy.registry import TokenRegistry, BlockType
from signamancy.parser import SignamancyParser
from signamancy.compiler import SignamancyCompiler
from signamancy.engine import SignamancyEngine, SimulationConfig
from signamancy.bridge import SignamancyBridge

# 1. The "Locus": Defining the World Rules
# We use a subset of the Pokemon logic for the MVP
POKEMON_RULES = """
# --- Initialization ---
# Start with Player in Pallet Town, 5 Potions, and 0 Badges
🎬 => 🧍Pallet_Town 💊Potion_5 📛Badge_0

# --- Movement Logic ---
# Simple graph navigation
🧍Pallet_Town 👆Up => 🧍Route_1
🧍Route_1 👇Down => 🧍Pallet_Town

# --- The Wild (Probability) ---
# Walking in grass creates encounters. 
# This uses Branching Logic (One-Of).
🧍Route_1 🦶Step => 🌥️Nothing%60 | 🐦Pidgey%20 | 🐀Rattata%20

# --- Combat Logic (Resource Exchange) ---
# If you see a Pidgey and Attack, you might win or get hurt
# This uses Ranges for damage variance
🐦Pidgey ⚔️Attack => ☠️Faint%80 | 💔Hurt_1-3%20

# --- Inventory Logic (Unit Conversion) ---
# 10 Potions => 1 Potion Pack (Carry Lookahead)
💊Potion_10 => 📦Potion_Pack
"""

def main():
    print("🔮 Booting Signamancy Engine...")
    
    # --- Phase 1: Parsing (Signum) ---
    registry = TokenRegistry()
    
    # Define Unit Links manually for the compiler hint (usually handled by Schema Expert)
    # This tells the Byte Physics kernel that Potion -> Potion_Pack at 10
    registry.register_unit_link("💊Potion", "📦Potion_Pack", threshold=9) # >9 triggers overflow
    
    parser = SignamancyParser(registry)
    rules = parser.parse_text(POKEMON_RULES)
    
    print(f"📜 Parsed {len(rules)} rules.")
    for r in rules:
        print(f"   - {r.original_text}")

    # --- Phase 2: Compilation (Locus) ---
    compiler = SignamancyCompiler(registry)
    kernel = compiler.compile(rules)
    
    print(f"\n💾 Compiled Kernel.")
    print(f"   - Bit Block Size: {kernel.block_sizes[BlockType.BIT]}")
    print(f"   - Byte Block Size: {kernel.block_sizes[BlockType.BYTE]}")
    print(f"   - Float Block Size: {kernel.block_sizes[BlockType.FLOAT]}")

    # --- Phase 3: Execution (Sensus) ---
    # We run 1024 parallel universes to test probabilities
    config = SimulationConfig(batch_size=1024, device="cuda" if torch.cuda.is_available() else "cpu")
    engine = SignamancyEngine(kernel, config)
    bridge = SignamancyBridge(engine, registry)
    
    print(f"\n⚡ Engine Online on {config.device}. Simulating {config.batch_size} Timelines.")

    # Helper to print state
    def print_status(step_name):
        print(f"\n--- {step_name} ---")
        snapshot = bridge.get_state_snapshot()
        print(json.dumps(snapshot, indent=2))

    # --- Step 0: Genesis ---
    # Inject the Start Token
    bridge.inject_signal("🎬")
    engine.step()
    print_status("Genesis (State 0)")
    
    # --- Step 1: Input Injection ---
    # User presses "Up"
    print("\n🎮 User Input: UP")
    bridge.inject_signal("👆Up")
    engine.step()
    print_status("After Move")

    # --- Step 2: Encounter ---
    # User takes a step in the grass (Route 1)
    print("\n🎮 User Input: STEP")
    bridge.inject_signal("🦶Step")
    engine.step()
    
    # Look at the Chaos
    print("\n🌌 Analyzing Quantum State (Route 1 Encounters)...")
    # We expect split universes: Some see Nothing, some see Pidgey/Rattata
    snapshot = bridge.get_state_snapshot()
    pidgey = snapshot.get("🐦Pidgey", {"val": 0})
    rattata = snapshot.get("🐀Rattata", {"val": 0})
    print(f"   - Pidgey Encounter Rate: {pidgey['val'] * 100:.1f}% (Exp: ~20%)")
    print(f"   - Rattata Encounter Rate: {rattata['val'] * 100:.1f}% (Exp: ~20%)")

    # --- Step 3: Unit Overflow Test ---
    # Let's cheat and give the player 15 potions to test the Physics Kernel
    print("\n🎮 Dev Console: Give 15 Potions")
    bridge.inject_signal("💊Potion", 15) 
    engine.step() # This resolves the production
    engine.step() # This resolves the overflow/physics
    
    print_status("After Potion Injection")
    # Expectation: Potion count should wrap, and Potion_Pack should increment.

if __name__ == "__main__":
    main()
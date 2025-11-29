import json
from typing import Callable

import torch

from signamancy.registry import TokenRegistry, BlockType
from signamancy.parser import SignamancyParser
from signamancy.compiler import SignamancyCompiler
from signamancy.engine import SignamancyEngine, SimulationConfig
from signamancy.bridge import SignamancyBridge


RULES = """
# Init a number and ensure result flags start absent.
🎬 => 🔢N_997

# CPU trigger (only if result not yet determined)
🚫🟢Prime 🚫🔴Composite => 🧮PrimeCheck
"""


def make_prime_callback(registry: TokenRegistry) -> Callable[[SignamancyEngine, int], None]:
    n_id = registry.get_id("🔢N")
    prime_id = registry.register("🟢Prime", BlockType.BIT)
    comp_id = registry.register("🔴Composite", BlockType.BIT)

    def get_local(gid: int):
        meta = registry.get_metadata(gid)
        return meta.block_type, meta.local_id

    n_bt, n_loc = get_local(n_id)
    p_bt, p_loc = get_local(prime_id)
    c_bt, c_loc = get_local(comp_id)

    def is_prime(n: int) -> bool:
        if n < 2:
            return False
        if n % 2 == 0:
            return n == 2
        f = 3
        while f * f <= n:
            if n % f == 0:
                return False
            f += 2
        return True

    def cb(engine: SignamancyEngine, b: int):
        # Read N for this universe
        n_val = int(engine.state[n_bt][b, n_loc].item())
        if is_prime(n_val):
            # Set result flags
            engine.state[p_bt][b, p_loc] = 1
            engine.state[c_bt][b, c_loc] = 0
        else:
            engine.state[p_bt][b, p_loc] = 0
            engine.state[c_bt][b, c_loc] = 1

    return cb


def main():
    print("🔮 CPU Valve Demo: Prime Check")

    # Registry and pre-registration of result tokens
    registry = TokenRegistry()
    registry.register("🟢Prime", BlockType.BIT)
    registry.register("🔴Composite", BlockType.BIT)
    registry.register("🔢N", BlockType.FLOAT)

    # Parse
    parser = SignamancyParser(registry)
    rules = parser.parse_text(RULES)
    print(f"📜 Parsed {len(rules)} rules (CPU rule should be present).")

    # Compile
    compiler = SignamancyCompiler(registry)
    kernel = compiler.compile(rules)

    # Engine/Bridge
    cfg = SimulationConfig(batch_size=256, device="cuda" if torch.cuda.is_available() else "cpu")
    engine = SignamancyEngine(kernel, cfg)
    bridge = SignamancyBridge(engine, registry)

    # Register CPU callbacks for CPU-flagged rules
    cpu_cb = make_prime_callback(registry)
    for idx, r in enumerate(rules):
        if r.requires_cpu:
            engine.register_cpu_callback(idx, cpu_cb)

    def show(label: str):
        snap = bridge.get_state_snapshot(token_filter=["🔢N", "🟢Prime", "🔴Composite"])
        print(f"\n--- {label} ---")
        print(json.dumps(snap, indent=2, ensure_ascii=False))

    # Run: Genesis + Step
    bridge.inject_signal("🎬")
    engine.step()
    show("After Step 1 (CPU should have executed)")

    # Optional: Change N to a composite and step again
    bridge.inject_signal("🔢N", 999, operation="SET")
    engine.step()
    show("After Step 2 (N set to 999 -> Composite)")


if __name__ == "__main__":
    main()


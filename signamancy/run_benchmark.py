import os
import time
import json
from typing import Callable, Dict, Any, List

import torch

from signamancy.registry import TokenRegistry, BlockType
from signamancy.parser import SignamancyParser
from signamancy.compiler import SignamancyCompiler
from signamancy.engine import SignamancyEngine, SimulationConfig
from signamancy.bridge import SignamancyBridge


def generate_names(count: int) -> List[str]:
    # Generate token base names without digits to satisfy parser regex
    alphabet = [chr(c) for c in range(ord('a'), ord('z') + 1)]
    names: List[str] = []
    # progressively increase length 1,2,3,... until reaching count
    length = 1
    while len(names) < count:
        def backtrack(prefix: str, depth: int):
            nonlocal names
            if len(names) >= count:
                return
            if depth == 0:
                names.append(prefix)
                return
            for ch in alphabet:
                backtrack(prefix + ch, depth - 1)
                if len(names) >= count:
                    return
        if length == 1:
            for ch in alphabet:
                names.append(ch)
                if len(names) >= count:
                    break
        else:
            backtrack("", length)
        length += 1
    return names[:count]


def build_rules(num_gpu_rules: int, cpu_pct: float) -> str:
    base = []
    # Init: Start flag and a number for CPU work
    base.append("🎬 => 🟢Start 🔢N_997")
    # CPU trigger is produced by GPU path at low probability each step
    base.append(f"🟢Start => 🟪CpuTrig%{cpu_pct}")
    # CPU rule: only when trigger present and not done
    base.append("🟪CpuTrig 🚫🟢Done => 🧮Work")
    # GPU stress: many rules with Start -> token_1 and small float ranges
    names = generate_names(num_gpu_rules)
    for n in names:
        # Produce a BYTE and a FLOAT to exercise both blocks; re-emit Start to keep it alive
        # BYTE: Cn_1 ; FLOAT: Fn_1-3
        base.append(f"🟢Start => 🟢Start C{n}_1 F{n}_1-3")
    return "\n".join(base)


def make_cpu_callback(registry: TokenRegistry, cpu_stats: Dict[str, Any]) -> Callable[[SignamancyEngine, int], None]:
    n_id = registry.get_id("🔢N")
    done_id = registry.register("🟢Done", BlockType.BIT)

    def get_local(gid: int):
        meta = registry.get_metadata(gid)
        return meta.block_type, meta.local_id

    n_bt, n_loc = get_local(n_id)
    d_bt, d_loc = get_local(done_id)

    def expensive_python(n: int) -> int:
        # Mildly expensive: sum of divisors mod 7 + parity
        s = 0
        # Keep work bounded
        limit = min(n, 5000)
        for i in range(1, limit, 2):
            if n % i == 0:
                s += i
        return (s % 7) ^ (n & 1)

    def cb(engine: SignamancyEngine, b: int):
        t0 = time.perf_counter()
        n_val = int(engine.state[n_bt][b, n_loc].item())
        _ = expensive_python(n_val)
        # Mark done to prevent re-trigger unless reset
        engine.state[d_bt][b, d_loc] = 1
        cpu_stats["calls"] += 1
        cpu_stats["rows"] += 1
        cpu_stats["time_s"] += (time.perf_counter() - t0)

    return cb


def main():
    # Parameters
    num_gpu_rules = int(os.environ.get("BENCH_RULES", "500"))
    batch_size = int(os.environ.get("BENCH_BATCH", "2048"))
    steps = int(os.environ.get("BENCH_STEPS", "20"))
    # allow fractional percent, e.g., 0.5 = 0.5%
    cpu_pct = float(os.environ.get("BENCH_CPU_PCT", "2.0"))  # percent chance per step per universe

    device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"🧪 Benchmark: rules={num_gpu_rules}, batch={batch_size}, steps={steps}, cpu_pct={cpu_pct}, device={device}")

    # Build rules
    rules_text = build_rules(num_gpu_rules, cpu_pct)

    # Registry setup (pre-register a few tokens with intended types)
    registry = TokenRegistry()
    registry.register("🟢Start", BlockType.BIT)
    registry.register("🟢Done", BlockType.BIT)
    registry.register("🔢N", BlockType.FLOAT)
    registry.register("🟪CpuTrig", BlockType.BIT)

    # Parse & Compile
    parser = SignamancyParser(registry)
    rules = parser.parse_text(rules_text)

    compiler = SignamancyCompiler(registry)
    kernel = compiler.compile(rules)

    # Engine & Bridge
    cfg = SimulationConfig(batch_size=batch_size, device=device)
    engine = SignamancyEngine(kernel, cfg)
    bridge = SignamancyBridge(engine, registry)

    # CPU callback stats
    cpu_stats = {"calls": 0, "rows": 0, "time_s": 0.0}

    # Register CPU callbacks
    cpu_cb = make_cpu_callback(registry, cpu_stats)
    for idx, r in enumerate(rules):
        if r.requires_cpu:
            engine.register_cpu_callback(idx, cpu_cb)

    def sync_dev():
        if device == "cuda":
            torch.cuda.synchronize()

    # Warm-up: Genesis and one step
    bridge.inject_signal("🎬")
    sync_dev()
    engine.step()
    sync_dev()

    # Benchmark loop
    t_total = 0.0
    for s in range(steps):
        # Reset Done to 0 so CPU rule may fire again; trigger produced by GPU with small probability
        bridge.inject_signal("🟢Done", 0, operation="SET")
        sync_dev()
        t0 = time.perf_counter()
        engine.step()
        sync_dev()
        t_total += (time.perf_counter() - t0)

    # Snapshot a small view to ensure side effects happened
    snap = bridge.get_state_snapshot(token_filter=["🟢Done", "Caa", "Faa"])

    # Report
    print("\n--- Benchmark Results ---")
    print(json.dumps({
        "device": device,
        "rules": len(rules),
        "batch_size": batch_size,
        "steps": steps,
        "total_time_s": round(t_total, 4),
        "avg_step_ms": round(1000.0 * t_total / steps, 3),
        "steps_per_sec": round(steps / t_total, 2) if t_total > 0 else None,
        "cpu_callback_calls": cpu_stats["calls"],
        "cpu_rows_processed": cpu_stats["rows"],
        "cpu_time_s": round(cpu_stats["time_s"], 4),
        "cpu_pct": round(100.0 * cpu_stats["time_s"] / t_total, 1) if t_total > 0 else None,
        "sample_snapshot": snap
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()


import csv
import json
from pathlib import Path
import os
import time
import torch

from signamancy.registry import TokenRegistry
from signamancy.parser import SignamancyParser
from signamancy.compiler import SignamancyCompiler
from signamancy.engine import SignamancyEngine, SimulationConfig
from signamancy.bridge import SignamancyBridge


def load_recipes_csv(csv_path: Path) -> str:
    lines = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        # Expect two columns: ID, Recipe
        for row in reader:
            if not row:
                continue
            if len(row) < 2:
                continue
            recipe = row[1].strip()
            if not recipe:
                continue
            lines.append(recipe)
    return "\n".join(lines)


def format_compact(snapshot: dict, limit: int = 0) -> str:
    parts = []
    # Stable order: sort by symbol
    items = list(snapshot.items())
    items.sort(key=lambda kv: kv[0])
    if limit > 0:
        items = items[:limit]
    for sym, meta in items:
        val = meta.get("val", 0)
        std = meta.get("std", 0)
        typ = meta.get("type", "")
        if val <= 0:
            continue
        if typ == "BIT":
            if val >= 0.999 and std == 0:
                parts.append(sym)
            else:
                parts.append(f"{sym}~{val:.3f}")
        elif typ == "BYTE":
            parts.append(f"{sym}{int(round(val))}")
        else:  # FLOAT
            parts.append(f"{sym}~{val:.3f}")
    return " ".join(parts)


def metric_diff(prev_snap: dict, snap: dict, eps: float = 1e-6) -> dict:
    keys = set(prev_snap.keys()) | set(snap.keys())
    changed = 0
    l1 = 0.0
    for k in keys:
        a = prev_snap.get(k, {"val": 0}).get("val", 0.0)
        b = snap.get(k, {"val": 0}).get("val", 0.0)
        d = abs(b - a)
        if d > eps:
            changed += 1
            l1 += d
    return {"changed": changed, "l1": l1}


def bank_stage(snap: dict, bank_prefix: str) -> dict:
    # Track fractions of universes at each bank stage tokens starting with bank_prefix
    stages = {}
    for k, v in snap.items():
        if k.startswith(bank_prefix):
            stages[k] = v.get("val", 0.0)
    return stages


def money_value(snap: dict, money_token: str) -> float:
    m = snap.get(money_token)
    if not m:
        return 0.0
    return float(m.get("val", 0.0))


def main():
    csv_path = Path(__file__).resolve().parents[1] / "games" / "farm" / "recipes.csv"
    print(f"🌾 Loading recipes from {csv_path}")
    text = load_recipes_csv(csv_path)

    registry = TokenRegistry()
    parser = SignamancyParser(registry)
    rules = parser.parse_text(text)
    print(f"📜 Parsed {len(rules)} rules from CSV")

    compiler = SignamancyCompiler(registry)
    kernel = compiler.compile(rules)

    cfg = SimulationConfig(batch_size=1024, device="cuda" if torch.cuda.is_available() else "cpu")
    engine = SignamancyEngine(kernel, cfg)
    bridge = SignamancyBridge(engine, registry)

    # Inject initial spark and seed
    bridge.inject_signal("💫")
    engine.step()
    engine.step()

    # Churn controls
    steps = int(os.environ.get("FARM_STEPS", "0"))  # 0 = infinite
    print_every = int(os.environ.get("FARM_PRINT_EVERY", "100"))
    sleep_ms = int(os.environ.get("FARM_SLEEP_MS", "0"))
    snap_n = int(os.environ.get("FARM_SNAPSHOT_N", "20"))
    eps = float(os.environ.get("FARM_EPS", "1e-6"))
    money_token = os.environ.get("FARM_MONEY_TOKEN", "💰")
    bank_prefix = os.environ.get("FARM_BANK_PREFIX", "🏦")

    # Initial snapshot
    snapshot = bridge.get_state_snapshot()
    items = list(snapshot.items())[:snap_n]
    print("\n--- State (initial) ---")
    print(json.dumps(dict(items), indent=2, ensure_ascii=False))
    compact_line = format_compact(snapshot)
    print("\nResources:")
    print(compact_line)
    mv = money_value(snapshot, money_token)
    print(f"Money: {money_token}~{mv:.3f}")

    # Main churn loop
    count = 0
    prev_snap = snapshot
    try:
        if steps > 0:
            total = steps
            while count < total:
                engine.step()
                count += 1
                if print_every and (count % print_every == 0):
                    snap = bridge.get_state_snapshot()
                    # Metrics
                    diff = metric_diff(prev_snap, snap, eps)
                    stages = bank_stage(snap, bank_prefix)
                    items = list(snap.items())[:snap_n]
                    print(f"\n--- State (step {count}) ---")
                    print(json.dumps(dict(items), indent=2, ensure_ascii=False))
                    compact_line = format_compact(snap)
                    print(compact_line)
                    mv = money_value(snap, money_token)
                    print(f"Money: {money_token}~{mv:.3f}")
                    if stages:
                        print(f"Bank stages: {json.dumps(stages, ensure_ascii=False)}")
                    print(f"Δ tokens: {diff['changed']}  L1: {diff['l1']:.3f}")
                    prev_snap = snap
                if sleep_ms > 0:
                    time.sleep(sleep_ms / 1000.0)
        else:
            while True:
                engine.step()
                count += 1
                if print_every and (count % print_every == 0):
                    snap = bridge.get_state_snapshot()
                    diff = metric_diff(prev_snap, snap, eps)
                    stages = bank_stage(snap, bank_prefix)
                    items = list(snap.items())[:snap_n]
                    print(f"\n--- State (step {count}) ---")
                    print(json.dumps(dict(items), indent=2, ensure_ascii=False))
                    compact_line = format_compact(snap)
                    print(compact_line)
                    mv = money_value(snap, money_token)
                    print(f"Money: {money_token}~{mv:.3f}")
                    if stages:
                        print(f"Bank stages: {json.dumps(stages, ensure_ascii=False)}")
                    print(f"Δ tokens: {diff['changed']}  L1: {diff['l1']:.3f}")
                    prev_snap = snap
                if sleep_ms > 0:
                    time.sleep(sleep_ms / 1000.0)
    except KeyboardInterrupt:
        print(f"\n⏹ Stopped at step {count}.")


if __name__ == "__main__":
    main()


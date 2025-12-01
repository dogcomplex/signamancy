import csv
import json
from pathlib import Path
import os
import time
import torch

from signamancy.registry import TokenRegistry, BlockType
from signamancy.parser import SignamancyParser, Rule
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


def load_rules_with_ids(csv_path: Path) -> tuple[list[Rule], dict[int, str], TokenRegistry]:
    registry = TokenRegistry()
    parser = SignamancyParser(registry)
    rules: list[Rule] = []
    idx_to_id: dict[int, str] = {}
    with csv_path.open(newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        for row in r:
            if not row or len(row) < 2:
                continue
            rule_id = row[0].strip()
            recipe = row[1].strip()
            if not recipe:
                continue
            before = len(rules)
            rs = parser.parse_text(recipe)
            rules.extend(rs)
            after = len(rules)
            if rule_id:
                for k, idx in enumerate(range(before, after)):
                    label = rule_id if k == 0 else f"{rule_id}#{k}"
                    idx_to_id[idx] = label
    return rules, idx_to_id, registry


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


def parse_prefixes(env_str: str) -> list:
    if not env_str:
        return []
    parts = [p.strip() for p in env_str.replace(",", " ").split() if p.strip()]
    return parts


def summarize_targets(snap: dict, prefixes: list, top_n: int = 10) -> dict:
    summary = {}
    for pref in prefixes:
        bucket = {k: v.get("val", 0.0) for k, v in snap.items() if k.startswith(pref)}
        if not bucket:
            continue
        total = sum(bucket.values())
        top = sorted(bucket.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
        summary[pref] = {"sum": total, "top": top}
    return summary


def capture_state(engine: SignamancyEngine) -> dict:
    # Returns clones of current state per block as float tensors
    sig = {}
    for bt, tens in engine.state.items():
        sig[bt] = tens.float().clone()
    return sig


def diff_state(prev: dict, engine: SignamancyEngine) -> torch.Tensor:
    # Per-universe L1 across all blocks
    diffs = None
    for bt, tens in engine.state.items():
        cur = tens.float()
        prv = prev[bt]
        d = torch.abs(cur - prv).sum(dim=1)  # [B]
        diffs = d if diffs is None else diffs + d
    return diffs


def main():
    csv_path = Path(__file__).resolve().parents[1] / "games" / "farm" / "recipes.csv"
    print(f"🌾 Loading recipes from {csv_path}")
    rules = None
    idx_to_id = {}
    registry = None
    if csv_path.suffix.lower() == ".csv":
        rules, idx_to_id, registry = load_rules_with_ids(csv_path)
        print(f"📜 Parsed {len(rules)} rules from CSV")
        compiler = SignamancyCompiler(registry)
        kernel = compiler.compile(rules)
    else:
        text = load_recipes_csv(csv_path)
        registry = TokenRegistry()
        parser = SignamancyParser(registry)
        rules = parser.parse_text(text)
        print(f"📜 Parsed {len(rules)} rules from text")
        compiler = SignamancyCompiler(registry)
        kernel = compiler.compile(rules)

    cfg = SimulationConfig(
        batch_size=1024,
        device="cuda" if torch.cuda.is_available() else "cpu",
        enable_priority_logging=(int(os.environ.get("ENABLE_PRIORITY_LOGGING", "0")) == 1),
        priority_log_limit=int(os.environ.get("PRIORITY_LOG_LIMIT", "50")),
        priority_log_path=os.environ.get("PRIORITY_LOG_PATH", ""),
        log_same_base_ties=(int(os.environ.get("ENABLE_PRIORITY_LOG_SAME_BASE", "0")) == 1)
    )
    engine = SignamancyEngine(kernel, cfg)
    # Attach rule IDs for logging if available
    if idx_to_id:
        # Build list aligned to num_rules, default fallback names
        rule_ids = [idx_to_id.get(i, f"Rule#{i}") for i in range(engine.num_rules)]
        engine.rule_ids = rule_ids
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
    target_prefixes = parse_prefixes(os.environ.get("TARGET_RESOURCE_PREFIXES", "💰,🏦"))
    halt_on_stable = int(os.environ.get("HALT_ON_STABLE", "0")) == 1
    eps_state = float(os.environ.get("HALT_EPS_STATE", "1e-6"))
    sample_n = int(os.environ.get("HALT_PRINT_SAMPLE_N", "10"))

    # Initial snapshot
    snapshot = bridge.get_state_snapshot()
    items = list(snapshot.items())[:snap_n]
    print("\n--- State (initial) ---")
    print(json.dumps(dict(items), indent=2, ensure_ascii=False))
    compact_line = format_compact(snapshot)
    print("\nResources:")
    print(compact_line)
    if target_prefixes:
        tgt = summarize_targets(snapshot, target_prefixes)
        if tgt:
            print("Targets:")
            for pref, data in tgt.items():
                tops = " ".join([f"{k}~{v:.3f}" for k, v in data["top"]])
                print(f"  {pref}: sum~{data['sum']:.3f}  top: {tops}")

    # Main churn loop
    count = 0
    prev_snap = snapshot
    prev_state = capture_state(engine)
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
                    per_uni = diff_state(prev_state, engine)
                    stable_mask = (per_uni <= eps_state)
                    num_stable = int(stable_mask.sum().item())
                    items = list(snap.items())[:snap_n]
                    print(f"\n--- State (step {count}) ---")
                    print(json.dumps(dict(items), indent=2, ensure_ascii=False))
                    compact_line = format_compact(snap)
                    print(compact_line)
                    if target_prefixes:
                        tgt = summarize_targets(snap, target_prefixes)
                        if tgt:
                            print("Targets:")
                            for pref, data in tgt.items():
                                tops = " ".join([f"{k}~{v:.3f}" for k, v in data["top"]])
                                print(f"  {pref}: sum~{data['sum']:.3f}  top: {tops}")
                    print(f"Δ tokens: {diff['changed']}  L1: {diff['l1']:.3f}  Stable universes: {num_stable}/{cfg.batch_size}")
                    if halt_on_stable and num_stable == cfg.batch_size:
                        print("All universes stable. Halting.")
                        return
                    # Update prev
                    prev_snap = snap
                    prev_state = capture_state(engine)
                if sleep_ms > 0:
                    time.sleep(sleep_ms / 1000.0)
        else:
            while True:
                engine.step()
                count += 1
                if print_every and (count % print_every == 0):
                    snap = bridge.get_state_snapshot()
                    diff = metric_diff(prev_snap, snap, eps)
                    per_uni = diff_state(prev_state, engine)
                    stable_mask = (per_uni <= eps_state)
                    num_stable = int(stable_mask.sum().item())
                    items = list(snap.items())[:snap_n]
                    print(f"\n--- State (step {count}) ---")
                    print(json.dumps(dict(items), indent=2, ensure_ascii=False))
                    compact_line = format_compact(snap)
                    print(compact_line)
                    if target_prefixes:
                        tgt = summarize_targets(snap, target_prefixes)
                        if tgt:
                            print("Targets:")
                            for pref, data in tgt.items():
                                tops = " ".join([f"{k}~{v:.3f}" for k, v in data["top"]])
                                print(f"  {pref}: sum~{data['sum']:.3f}  top: {tops}")
                    print(f"Δ tokens: {diff['changed']}  L1: {diff['l1']:.3f}  Stable universes: {num_stable}/{cfg.batch_size}")
                    if halt_on_stable and num_stable == cfg.batch_size:
                        print("All universes stable. Halting.")
                        return
                    prev_snap = snap
                    prev_state = capture_state(engine)
                if sleep_ms > 0:
                    time.sleep(sleep_ms / 1000.0)
    except KeyboardInterrupt:
        print(f"\n⏹ Stopped at step {count}.")


if __name__ == "__main__":
    main()


import os
import csv
import json
from pathlib import Path
import math
import random
import torch

from signamancy.registry import TokenRegistry
from signamancy.parser import SignamancyParser, Rule
from signamancy.compiler import SignamancyCompiler, KernelData
from signamancy.engine import SignamancyEngine, SimulationConfig
from signamancy.bridge import SignamancyBridge


def load_recipes(csv_path: Path) -> str:
    if csv_path.suffix.lower() == ".csv":
        lines = []
        with csv_path.open(newline="", encoding="utf-8") as f:
            r = csv.reader(f)
            for row in r:
                if len(row) >= 2 and row[1].strip():
                    lines.append(row[1].strip())
        return "\n".join(lines)
    else:
        return csv_path.read_text(encoding="utf-8")


def load_rules_with_ids(csv_path: Path) -> tuple[list[Rule], dict[int, str], TokenRegistry]:
    """Parse CSV row-by-row to preserve IDs and map compiled rule indices to IDs.
    Returns (rules, idx_to_id, registry)."""
    registry = TokenRegistry()
    parser = SignamancyParser(registry)
    rules: list[Rule] = []
    idx_to_id: dict[int, str] = {}
    if csv_path.suffix.lower() != ".csv":
        # Fallback plain text: no IDs available
        text = csv_path.read_text(encoding="utf-8")
        rs = parser.parse_text(text)
        rules.extend(rs)
        return rules, idx_to_id, registry
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


def build_engine_from_kernel(kernel: KernelData, registry: TokenRegistry, batch_size: int, device: str) -> tuple[SignamancyEngine, SignamancyBridge]:
    cfg = SimulationConfig(batch_size=batch_size, device=device)
    engine = SignamancyEngine(kernel, cfg)
    bridge = SignamancyBridge(engine, registry)
    return engine, bridge


def objective_from_snapshot(snapshot: dict, prefixes: list[str], weights: list[float] | None = None) -> float:
    if not prefixes:
        return 0.0
    if weights is None:
        weights = [1.0] * len(prefixes)
    score = 0.0
    for pref, w in zip(prefixes, weights):
        s = 0.0
        for k, v in snapshot.items():
            if k.startswith(pref):
                s += float(v.get("val", 0.0))
        score += w * s
    return score


def set_biases(engine: SignamancyEngine, bias: torch.Tensor):
    engine.set_rule_biases(bias)


def cem_optimize(csv_path: Path, device: str):
    # Config via env
    batch_size = int(os.environ.get("AGENT_BATCH", "512"))
    horizon = int(os.environ.get("AGENT_HORIZON", "500"))
    iters = int(os.environ.get("CEM_ITERS", "10"))
    pop = int(os.environ.get("CEM_POP", "24"))
    elite_frac = float(os.environ.get("CEM_ELITE_FRAC", "0.2"))
    init_std = float(os.environ.get("CEM_INIT_STD", "0.5"))
    prefixes = [p.strip() for p in os.environ.get("TARGET_RESOURCE_PREFIXES", "👑,💰").replace(",", " ").split() if p.strip()]
    weights = None  # default equal
    log_every_cand = int(os.environ.get("LOG_EVERY_CAND", "4"))

    # Compile once
    rules, idx_to_id, registry = load_rules_with_ids(csv_path)
    compiler = SignamancyCompiler(registry)
    kernel = compiler.compile(rules)
    num_rules = kernel.num_rules

    print(f"[CEM] device={device} batch={batch_size} horizon={horizon} iters={iters} pop={pop} prefixes={prefixes}", flush=True)

    mean = torch.zeros(num_rules, dtype=torch.float32)
    std = torch.full((num_rules,), init_std, dtype=torch.float32)

    best_bias = None
    best_score = -1e9

    for it in range(iters):
        print(f"[CEM] iter {it+1}/{iters}...")
        candidates = []
        scores = []
        for i in range(pop):
            bias = (mean + std * torch.randn_like(mean)).clamp_(-3.0, 3.0)
            engine, bridge = build_engine_from_kernel(kernel, registry, batch_size, device)
            # seed
            bridge.inject_signal("💫")
            engine.step(); engine.step()
            set_biases(engine, bias.to(engine.device))
            for t in range(horizon):
                engine.step()
            snap = bridge.get_state_snapshot()
            score = objective_from_snapshot(snap, prefixes, weights)
            candidates.append(bias)
            scores.append(score)
            if (i + 1) % max(1, log_every_cand) == 0:
                print(f"  cand {i+1}/{pop} score={score:.3f}")
            if score > best_score:
                best_score = score
                best_bias = bias.clone()
        # elite update
        k = max(1, int(math.ceil(elite_frac * pop)))
        top_idx = sorted(range(pop), key=lambda i: scores[i], reverse=True)[:k]
        elite = torch.stack([candidates[i] for i in top_idx], dim=0)
        mean = elite.mean(dim=0)
        std = elite.std(dim=0) + 1e-6
        # Log top-weighted rules (IDs if available)
        top_weights_idx = torch.topk(mean.abs(), k=10).indices.tolist()
        labels = [idx_to_id.get(i, f"Rule#{i}") for i in top_weights_idx]
        print(f"[CEM] iter {it+1}/{iters} best={best_score:.3f} top_bias={[(labels[j], float(mean[top_weights_idx[j]])) for j in range(len(top_weights_idx))]}")

    # Final run with best
    engine, bridge = build_engine_from_kernel(kernel, registry, batch_size, device)
    bridge.inject_signal("💫"); engine.step(); engine.step()
    set_biases(engine, best_bias.to(engine.device))
    for t in range(horizon):
        engine.step()
    snap = bridge.get_state_snapshot()
    print("\n--- Final Snapshot (first 20 tokens) ---")
    print(json.dumps({k: snap[k] for k in list(snap)[:20]}, indent=2, ensure_ascii=False))
    print(f"Best score={best_score:.3f}")


def main():
    path = os.environ.get("AGENT_RECIPES", "")
    if path:
        csv_path = Path(path)
    else:
        csv_path = Path(__file__).resolve().parents[2] / "games" / "farm" / "recipes.csv"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    cem_optimize(csv_path, device)


if __name__ == "__main__":
    main()


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
from signamancy.agent.policy import PolicyManager
from signamancy.agent.reachability import ReachabilityAnalyzer


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


def uniformize_biases_by_base(bias: torch.Tensor, idx_to_id: dict[int, str]) -> torch.Tensor:
    # Group compiled rule indices by CSV base ID (split at '#')
    base_to_indices: dict[str, list[int]] = {}
    for i, val in enumerate(bias):
        rid = idx_to_id.get(i, "")
        base = rid.split('#')[0] if rid else ""
        if base:
            base_to_indices.setdefault(base, []).append(i)
    out = bias.clone()
    for base, idxs in base_to_indices.items():
        if len(idxs) <= 1:
            continue
        m = float(out[idxs].mean().item())
        out[idxs] = m
    return out


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
    policy_file = os.environ.get("POLICY_FILE", "")
    policy_gain = float(os.environ.get("POLICY_GAIN", "1.0"))
    policy_export = os.environ.get("POLICY_EXPORT_FILE", "")
    policy_fail = int(os.environ.get("POLICY_FAIL_ON_VIOLATION", "0")) == 1
    reach_report = int(os.environ.get("REACHABILITY_REPORT", "0")) == 1
    reach_strict = int(os.environ.get("REACHABILITY_STRICT_PRIORITY", "1")) == 1
    uniform_branches = int(os.environ.get("POLICY_UNIFORM_BRANCHES", "1")) == 1
    use_crn = int(os.environ.get("AGENT_USE_CRN", "1")) == 1

    # Compile once
    rules, idx_to_id, registry = load_rules_with_ids(csv_path)
    compiler = SignamancyCompiler(registry)
    kernel = compiler.compile(rules)
    num_rules = kernel.num_rules

    # Build reverse map: ID -> list of rule indices
    id_to_indices: dict[str, list[int]] = {}
    for idx in range(num_rules):
        rid = idx_to_id.get(idx)
        if rid:
            id_to_indices.setdefault(rid, []).append(idx)

    # Load policy once (verify) if provided
    pm: PolicyManager | None = None
    if policy_file:
        try:
            pm = PolicyManager()
            ppath = Path(policy_file)
            pm.load_sheet(ppath)
            violations = pm.verify_sheet(ppath)
            if violations:
                print("[Policy] violations detected:")
                for v in violations[:50]:
                    print("  ", v)
                if policy_fail:
                    print("[Policy] failing due to violations.")
                    return
        except Exception as e:
            print(f"[Policy] load/verify error: {e}")

    print(f"[CEM] device={device} batch={batch_size} horizon={horizon} iters={iters} pop={pop} prefixes={prefixes}", flush=True)

    mean = torch.zeros(num_rules, dtype=torch.float32)
    std = torch.full((num_rules,), init_std, dtype=torch.float32)

    best_bias = None
    best_score = -1e9

    for it in range(iters):
        print(f"[CEM] iter {it+1}/{iters}...")
        # Capture a base RNG state once per iteration for common random numbers
        base_cpu_state = torch.get_rng_state()
        base_cuda_states = torch.cuda.get_rng_state_all() if (device == "cuda" and torch.cuda.is_available()) else None
        candidates = []
        scores = []
        for i in range(pop):
            # Restore RNG so each candidate sees the same random streams
            if use_crn:
                torch.set_rng_state(base_cpu_state)
                if base_cuda_states is not None:
                    torch.cuda.set_rng_state_all(base_cuda_states)
            bias = (mean + std * torch.randn_like(mean)).clamp_(-3.0, 3.0)
            engine, bridge = build_engine_from_kernel(kernel, registry, batch_size, device)
            # seed
            bridge.inject_signal("💫")
            engine.step(); engine.step()
            # apply policy sheet once per candidate (static + token desires)
            if pm:
                try:
                    pm.apply_to_engine(engine, registry, id_to_indices, policy_gain=policy_gain)
                except Exception as e:
                    print(f"[Policy] warning: {e}")
            if reach_report and i == 0 and it == 0:
                try:
                    ra = ReachabilityAnalyzer(engine, registry)
                    dead = ra.report_dead_rules(idx_to_id, strict_priority=reach_strict)
                    print(f"[Reachability] dead rules (sample): {dead[:10]} total={len(dead)}")
                except Exception as e:
                    print(f"[Reachability] error: {e}")
            use_bias = bias
            if uniform_branches:
                use_bias = uniformize_biases_by_base(use_bias, idx_to_id)
            set_biases(engine, use_bias.to(engine.device))
            for t in range(horizon):
                engine.step()
            snap = bridge.get_state_snapshot()
            score = objective_from_snapshot(snap, prefixes, weights)
            candidates.append(use_bias)
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
    if use_crn:
        # Reset RNG to a stable state for the showcase run
        torch.manual_seed(12345)
        if device == "cuda" and torch.cuda.is_available():
            torch.cuda.manual_seed_all(12345)
    bridge.inject_signal("💫"); engine.step(); engine.step()
    if pm:
        try:
            pm.apply_to_engine(engine, registry, id_to_indices, policy_gain=policy_gain)
        except Exception as e:
            print(f"[Policy] warning: {e}")
    if reach_report:
        try:
            ra = ReachabilityAnalyzer(engine, registry)
            dead = ra.report_dead_rules(idx_to_id, strict_priority=reach_strict)
            print(f"[Reachability] dead rules (sample): {dead[:20]} total={len(dead)}")
        except Exception as e:
            print(f"[Reachability] error: {e}")
    final_bias = best_bias
    if uniform_branches:
        final_bias = uniformize_biases_by_base(final_bias, idx_to_id)
    set_biases(engine, final_bias.to(engine.device))
    for t in range(horizon):
        engine.step()
    snap = bridge.get_state_snapshot()
    print("\n--- Final Snapshot (first 20 tokens) ---")
    print(json.dumps({k: snap[k] for k in list(snap)[:20]}, indent=2, ensure_ascii=False))
    print(f"Best score={best_score:.3f}")
    # Export emoji policy sheet if requested
    if policy_export:
        try:
            if pm is None:
                pm = PolicyManager()
            pm.export_sheet(Path(policy_export), best_bias.cpu(), id_to_indices, snap, pm.targets)
            print(f"[Policy] exported to {policy_export}")
        except Exception as e:
            print(f"[Policy] export error: {e}")


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


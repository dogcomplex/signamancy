import os
import json
from pathlib import Path
import torch

from signamancy.registry import TokenRegistry, BlockType
from signamancy.parser import SignamancyParser, Rule
from signamancy.compiler import SignamancyCompiler, KernelData
from signamancy.engine import SignamancyEngine, SimulationConfig
from signamancy.bridge import SignamancyBridge
from signamancy.agent.reachability import ReachabilityAnalyzer


def load_rules_with_ids(csv_path: Path) -> tuple[list[Rule], dict[int, str], TokenRegistry]:
    registry = TokenRegistry()
    parser = SignamancyParser(registry)
    rules: list[Rule] = []
    idx_to_id: dict[int, str] = {}
    if csv_path.suffix.lower() != ".csv":
        text = csv_path.read_text(encoding="utf-8")
        rs = parser.parse_text(text)
        rules.extend(rs)
        return rules, idx_to_id, registry
    import csv
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


def build_engine(kernel: KernelData, registry: TokenRegistry, batch: int, device: str, row_slice_max: int | None = None, temperature: float | None = None) -> tuple[SignamancyEngine, SignamancyBridge]:
    cfg = SimulationConfig(batch_size=batch, device=device)
    if row_slice_max is not None:
        # Optional override to force/fallback row-slice path
        setattr(cfg, "row_slice_max_uniques", int(row_slice_max))
    if temperature is not None:
        cfg.temperature = float(temperature)
    engine = SignamancyEngine(kernel, cfg)
    bridge = SignamancyBridge(engine, registry)
    return engine, bridge


def check_invariants(engine: SignamancyEngine) -> dict:
    ok = True
    details: dict[str, str] = {}
    # BIT in {-1,0,1}
    bit = engine.state[BlockType.BIT]
    if bit.numel() > 0:
        bad = ~((bit >= -1) & (bit <= 1))
        if bad.any():
            ok = False
            details["BIT_range"] = "out_of_range"
    # BYTE in [0,255]
    byte = engine.state[BlockType.BYTE]
    if byte.numel() > 0:
        bad = ~((byte >= 0) & (byte <= 255))
        if bad.any():
            ok = False
            details["BYTE_range"] = "out_of_range"
    # FLOAT >= 0
    fl = engine.state[BlockType.FLOAT]
    if fl.numel() > 0:
        bad = ~(fl >= 0)
        if bad.any():
            ok = False
            details["FLOAT_nonneg"] = "negative_values"
    # Single-action: fired <= 1 per row (when available)
    if getattr(engine, "last_fired_mask", None) is not None:
        sums = engine.last_fired_mask.sum(dim=1)
        if (sums > 1).any():
            ok = False
            details["single_action_violation"] = "multiple_rules_fired"
    return {"ok": ok, "details": details}


def code_checks(engine: SignamancyEngine, kernel: KernelData, registry: TokenRegistry, sample_rows: int = 5) -> dict:
    ok = True
    issues: list[str] = []
    # 1) Rule meta sanity
    meta = engine.rule_meta
    if meta.shape[1] != 4:
        ok = False
        issues.append("rule_meta_columns != 4")
    probs = meta[:, 1]
    if (probs < 0).any() or (probs > 1).any():
        ok = False
        issues.append("probability_out_of_range")
    # 2) Row-slice caches present if out_net exists
    for bt, kb in engine.gpu_blocks.items():
        out_net = kb.get("out_net")
        rows = kb.get("out_net_rows")
        if out_net is not None and rows is None:
            ok = False
            issues.append(f"{bt.name}: missing out_net_rows cache")
        # index bounds
        for key in ("out_net_rows", "out_std_rows", "all_rows"):
            rs = kb.get(key)
            if rs is None:
                continue
            idx_list = rs.get("idx")
            if not isinstance(idx_list, list) or len(idx_list) != kernel.num_rules:
                ok = False
                issues.append(f"{bt.name}: {key} length mismatch")
    # 3) Sparse row equivalence sample: outputs_net sparse vs cached rows
    import random
    random.seed(1234)
    for bt, bk in kernel.blocks.items():
        data = getattr(bk, "outputs_net", None)
        if data is None or not data.values:
            continue
        rs = engine.gpu_blocks[bt].get("out_net_rows")
        if rs is None:
            continue
        # Build map of row -> (cols, vals) from SparseMatrixData
        buckets = {}
        for r, c, v in zip(data.indices[0], data.indices[1], data.values):
            buckets.setdefault(int(r), ([], []))
            buckets[int(r)][0].append(int(c))
            buckets[int(r)][1].append(float(v))
        # sample rows that exist
        cand = [r for r in buckets.keys()][: max(1, sample_rows)]
        for r in cand:
            cols_dense, vals_dense = buckets[r]
            t_idx = rs["idx"][r].tolist()
            t_val = rs["val"][r].tolist()
            if len(cols_dense) != len(t_idx):
                ok = False
                issues.append(f"{bt.name}: outputs_net row {r} nnz mismatch ({len(cols_dense)} vs {len(t_idx)})")
                continue
            # Compare sets of (col,val) disregarding order
            dense_pairs = sorted(zip(cols_dense, [round(x, 6) for x in vals_dense]))
            row_pairs = sorted(zip(t_idx, [round(x, 6) for x in t_val]))
            if dense_pairs != row_pairs:
                ok = False
                issues.append(f"{bt.name}: outputs_net row {r} content mismatch")
    return {"ok": ok, "issues": issues}


def summarize_state(bridge: SignamancyBridge, top_n: int = 25) -> dict:
    snap = bridge.get_state_snapshot()
    # return top-N tokens by absolute value for brevity
    items = sorted(snap.items(), key=lambda kv: abs(kv[1].get("val", 0.0)), reverse=True)[:top_n]
    return {k: v for k, v in items}


def l1_diff_states(a: SignamancyEngine, b: SignamancyEngine) -> float:
    total = 0.0
    for bt in BlockType:
        x = a.state[bt].float()
        y = b.state[bt].float()
        # if one block is empty and the other is not, the shape will match by construction
        total += torch.abs(x - y).sum().item()
    return total


def names_by_block(registry: TokenRegistry) -> dict[BlockType, list[str]]:
    names: dict[BlockType, list[str]] = {BlockType.BIT: [], BlockType.BYTE: [], BlockType.FLOAT: []}
    for _, meta in registry._tokens.items():  # type: ignore[attr-defined]
        li = getattr(meta, "local_id", None)
        if li is None:
            continue
        while len(names[meta.block_type]) <= li:
            names[meta.block_type].append("")
        names[meta.block_type][li] = meta.original_text
    return names


def stepwise_diff(engA: SignamancyEngine, engB: SignamancyEngine, registry: TokenRegistry, max_steps: int, top_k: int = 10) -> dict:
    """
    Run engines in lockstep (they are assumed to be initialized/seeded) with CRN resets handled by caller.
    Returns first step where states differ and top-k token diffs by block.
    """
    names = names_by_block(registry)
    for step in range(1, max_steps + 1):
        # engines already stepped by caller; we assume caller interleaves CRN reset and calls .step()
        # Compare after this step
        diffs = {}
        total_l1 = 0.0
        for bt in BlockType:
            x = engA.state[bt].float()
            y = engB.state[bt].float()
            d = torch.abs(x - y)
            l1 = d.sum().item()
            total_l1 += l1
            if l1 > 0 and d.numel() > 0:
                # Aggregate over batch to get per-token magnitude
                per_tok = d.sum(dim=0)
                k = min(top_k, per_tok.numel())
                if k > 0:
                    idx = torch.topk(per_tok, k=k, largest=True).indices.tolist()
                    items = []
                    for li in idx:
                        nm = names[bt][li] if li < len(names[bt]) else f"{bt.name}:{li}"
                        items.append({"token": nm, "l1": float(per_tok[li].item())})
                    diffs[bt.name] = items
        if total_l1 > 0:
            # capture fired rule bases for reference
            firedA = []
            firedB = []
            if getattr(engA, "last_fired_mask", None) is not None:
                mask = engA.last_fired_mask.sum(dim=0).detach().cpu()
                nz = torch.nonzero(mask, as_tuple=False).squeeze(1).tolist()
                firedA = nz
            if getattr(engB, "last_fired_mask", None) is not None:
                mask = engB.last_fired_mask.sum(dim=0).detach().cpu()
                nz = torch.nonzero(mask, as_tuple=False).squeeze(1).tolist()
                firedB = nz
            return {"first_mismatch_step": step, "top_diffs": diffs, "fired_rules_A_nz": firedA, "fired_rules_B_nz": firedB}
    return {"first_mismatch_step": 0, "top_diffs": {}, "fired_rules_A_nz": [], "fired_rules_B_nz": []}


def diagnostics(csv_path: Path | None = None, device: str | None = None, batch: int = 2048, steps: int = 16) -> dict:
    if csv_path is None:
        csv_path = Path(__file__).resolve().parents[1] / "games" / "farm" / "recipes.csv"
    if device is None:
        device = "cpu"  # fast/safe default
    # Optional: no-variance for equivalence
    no_var = int(os.environ.get("DIAG_NO_VARIANCE", "1")) == 1
    temp = 0.0 if no_var else 1.0
    # Seed for reproducibility
    torch.manual_seed(1234)
    rules, idx_to_id, registry = load_rules_with_ids(csv_path)
    compiler = SignamancyCompiler(registry)
    kernel = compiler.compile(rules)

    # Build two engines: A (row-slice), B (fallback)
    engA, bridgeA = build_engine(kernel, registry, batch, device, row_slice_max=256, temperature=temp)
    engB, bridgeB = build_engine(kernel, registry, batch, device, row_slice_max=0, temperature=temp)
    # Attach IDs for possible introspection
    engA.rule_ids = [idx_to_id.get(i, f"Rule#{i}") for i in range(kernel.num_rules)]
    engB.rule_ids = [idx_to_id.get(i, f"Rule#{i}") for i in range(kernel.num_rules)]

    # Common Random Numbers (CRN): reset RNG before each engine.step()
    def _crn_states():
        cpu = torch.get_rng_state()
        cuda_all = torch.cuda.get_rng_state_all() if (device == "cuda" and torch.cuda.is_available()) else None
        return cpu, cuda_all
    def _crn_reset(cpu, cuda_all):
        torch.set_rng_state(cpu)
        if cuda_all is not None and (device == "cuda" and torch.cuda.is_available()):
            torch.cuda.set_rng_state_all(cuda_all)

    base_cpu, base_cuda = _crn_states()

    # Seed both, interleaving with CRN resets
    bridgeA.inject_signal("💫")
    _crn_reset(base_cpu, base_cuda); engA.step()
    _crn_reset(base_cpu, base_cuda); engB.step()
    _crn_reset(base_cpu, base_cuda); engA.step()
    _crn_reset(base_cpu, base_cuda); engB.step()

    # Post-seed validity sanity
    statsA = engA.compute_choice_stats(collapse_same_base=True)
    any_multi = bool(statsA.get("any_multi", False))
    prior_valid = statsA.get("prior_valid")
    num_rows_valid = int(prior_valid.any(dim=1).sum().item()) if torch.is_tensor(prior_valid) else 0

    # Advance a few steps
    # Step loop with CRN sync
    for _ in range(max(1, steps)):
        _crn_reset(base_cpu, base_cuda); engA.step()
        _crn_reset(base_cpu, base_cuda); engB.step()

    # Invariants
    invA = check_invariants(engA)
    invB = check_invariants(engB)

    # Equivalence check (row-slice vs fallback)
    l1 = l1_diff_states(engA, engB)
    diff_detail = {}
    if l1 > 0:
        # Run a short traced loop from fresh seed to find first mismatch and top token diffs
        # Rebuild engines quickly
        engA2, bridgeA2 = build_engine(kernel, registry, batch, device, row_slice_max=256, temperature=temp)
        engB2, bridgeB2 = build_engine(kernel, registry, batch, device, row_slice_max=0, temperature=temp)
        bridgeA2.inject_signal("💫"); bridgeB2.inject_signal("💫")
        _crn_reset(base_cpu, base_cuda); engA2.step(); _crn_reset(base_cpu, base_cuda); engB2.step()
        _crn_reset(base_cpu, base_cuda); engA2.step(); _crn_reset(base_cpu, base_cuda); engB2.step()
        # Step and diff per-step
        detail = stepwise_diff(engA2, engB2, registry, max_steps=max(1, steps), top_k=10)
        diff_detail = detail

    # Reachability dead-rule sample
    try:
        ra = ReachabilityAnalyzer(engA, registry)
        dead = ra.report_dead_rules(idx_to_id, limit=20, strict_priority=True)
    except Exception as e:
        dead = [f"reachability_error: {e}"]

    # Static code checks
    static_checks = code_checks(engA, kernel, registry, sample_rows=5)

    # Snapshot summaries
    snapA = summarize_state(bridgeA, top_n=25)

    return {
        "recipes": str(csv_path),
        "device": device,
        "batch": batch,
        "steps": steps,
        "no_variance": no_var,
        "post_seed_valid_rows": num_rows_valid,
        "any_multi_after_seed": any_multi,
        "invariants_A": invA,
        "invariants_B": invB,
        "row_slice_equivalence_L1": l1,
        "row_slice_diff_detail": diff_detail,
        "code_checks": static_checks,
        "dead_rules_sample": dead,
        "state_top_A": snapA,
    }


def main():
    # Env overrides for convenience
    path = os.environ.get("DIAG_RECIPES", "")
    device = os.environ.get("DIAG_DEVICE", "").strip().lower() or None
    batch = int(os.environ.get("DIAG_BATCH", "2048"))
    steps = int(os.environ.get("DIAG_STEPS", "16"))
    csv_path = Path(path) if path else None
    result = diagnostics(csv_path=csv_path, device=device, batch=batch, steps=steps)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    out = os.environ.get("DIAG_OUT", "diagnostics.json")
    try:
        Path(out).write_text(json.dumps(result, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[DIAG] wrote {out}")
    except Exception as e:
        print(f"[DIAG] write failed: {e}")


if __name__ == "__main__":
    main()



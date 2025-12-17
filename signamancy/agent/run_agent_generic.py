import os
import csv
import json
from pathlib import Path
import math
import torch
import time

from signamancy.registry import TokenRegistry
from signamancy.parser import SignamancyParser, Rule
from signamancy.compiler import SignamancyCompiler, KernelData
from signamancy.engine import SignamancyEngine, SimulationConfig
from signamancy.bridge import SignamancyBridge
from signamancy.agent.policy import PolicyManager
from signamancy.agent.reachability import ReachabilityAnalyzer
from signamancy.registry import BlockType
from signamancy.agent.planner_gpu import GPUPlanner


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
    for i, _ in enumerate(bias):
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


def _parse_int_list(val: str) -> list[int]:
    out: list[int] = []
    for part in val.replace(",", " ").split():
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except Exception:
            pass
    return out


def _build_prefix_indices(registry: TokenRegistry, prefixes: list[str]) -> dict[BlockType, torch.Tensor]:
    # Collect local indices per block for tokens whose names start with any prefix
    per_block: dict[BlockType, list[int]] = {BlockType.BIT: [], BlockType.BYTE: [], BlockType.FLOAT: []}
    for _, meta in registry._tokens.items():  # type: ignore[attr-defined]
        name = meta.original_text
        if any(name.startswith(p) for p in prefixes):
            li = getattr(meta, "local_id", None)
            if li is None:
                continue
            per_block[meta.block_type].append(int(li))
    out: dict[BlockType, torch.Tensor] = {}
    for bt, lst in per_block.items():
        if lst:
            out[bt] = torch.tensor(sorted(set(lst)), dtype=torch.long)
        else:
            out[bt] = torch.tensor([], dtype=torch.long)
    return out


def _score_universes(engine: SignamancyEngine, idx_by_block: dict[BlockType, torch.Tensor]) -> torch.Tensor:
    # Sum selected tokens across blocks per universe. BIT: count positives only.
    device = engine.device
    total = torch.zeros((engine.cfg.batch_size,), dtype=torch.float32, device=device)
    # BIT
    idx = idx_by_block.get(BlockType.BIT)
    if idx is not None and idx.numel() > 0:
        vals = engine.state[BlockType.BIT][:, idx.to(device)].float().clamp_min(0.0)
        total += vals.sum(dim=1)
    # BYTE
    idx = idx_by_block.get(BlockType.BYTE)
    if idx is not None and idx.numel() > 0:
        vals = engine.state[BlockType.BYTE][:, idx.to(device)].float()
        total += vals.sum(dim=1)
    # FLOAT
    idx = idx_by_block.get(BlockType.FLOAT)
    if idx is not None and idx.numel() > 0:
        vals = engine.state[BlockType.FLOAT][:, idx.to(device)].float()
        total += vals.sum(dim=1)
    return total


def _cpu_valve_needed(rules: list[Rule], registry: TokenRegistry) -> bool:
    # Heuristic: if any token name starts with 🧮 (calc placeholder) or any rule.requires_cpu
    try:
        for r in rules:
            if getattr(r, "requires_cpu", False):
                return True
            for tok in getattr(r, "inputs", []) + getattr(r, "outputs", []):
                # Use internal token map to get original text
                meta = registry._tokens.get(tok.token_id)  # type: ignore[attr-defined]
                name = meta.original_text if meta is not None else ""
                if name.startswith("🧮"):
                    return True
    except Exception:
        pass
    return False


def cem_optimize(csv_path: Path, device: str):
    # Config via env
    batch_size = int(os.environ.get("AGENT_BATCH", "512"))
    horizon = int(os.environ.get("AGENT_HORIZON", "500"))
    iters = int(os.environ.get("CEM_ITERS", "10"))
    pop = int(os.environ.get("CEM_POP", "24"))
    # Training-time overrides to speed up CEM (smaller batch/horizon)
    train_batch = int(os.environ.get("CEM_TRAIN_BATCH", str(batch_size)))
    train_horizon = int(os.environ.get("CEM_TRAIN_HORIZON", str(horizon)))
    elite_frac = float(os.environ.get("CEM_ELITE_FRAC", "0.2"))
    init_std = float(os.environ.get("CEM_INIT_STD", "0.5"))
    prefixes = [p.strip() for p in os.environ.get("TARGET_RESOURCE_PREFIXES", "👑,💰").replace(",", " ").split() if p.strip()]
    weights = None  # default equal
    log_every_cand = int(os.environ.get("LOG_EVERY_CAND", "4"))
    # Objective aggregation over the candidate rollout:
    #   final (default): score at last evaluation point
    #   max:   max score over trajectory
    #   sum:   sum of scores over trajectory
    #   avg:   average score over trajectory
    obj_mode = os.environ.get("CEM_OBJECTIVE", "final").strip().lower()
    eval_every = int(os.environ.get("CEM_EVAL_EVERY", "10"))  # evaluate trajectory score every N decision/steps
    policy_file = os.environ.get("POLICY_FILE", "")
    policy_gain = float(os.environ.get("POLICY_GAIN", "1.0"))
    policy_export = os.environ.get("POLICY_EXPORT_FILE", "")
    policy_fail = int(os.environ.get("POLICY_FAIL_ON_VIOLATION", "0")) == 1
    reach_report = int(os.environ.get("REACHABILITY_REPORT", "0")) == 1
    reach_strict = int(os.environ.get("REACHABILITY_STRICT_PRIORITY", "1")) == 1
    uniform_branches = int(os.environ.get("POLICY_UNIFORM_BRANCHES", "1")) == 1
    use_crn = int(os.environ.get("AGENT_USE_CRN", "1")) == 1
    # GPU planner (optional)
    planner_enable = int(os.environ.get("PLANNER_ENABLE", "0")) == 1
    planner_in_cem = int(os.environ.get("PLANNER_IN_CEM", "0")) == 1
    do_autotune = int(os.environ.get("AGENT_AUTOTUNE", "0")) == 1
    profile_iter = int(os.environ.get("AGENT_PROFILE", "0")) == 1
    single_action = int(os.environ.get("AGENT_SINGLE_ACTION", "1")) == 1
    decision_only = int(os.environ.get("DECISION_ONLY", "1")) == 1
    physics_burst_max = int(os.environ.get("PHYSICS_BURST_MAX", "128"))
    # Particle resampling (clone best into worst)
    resample_every = int(os.environ.get("RESAMPLE_EVERY", "0"))  # 0 disables
    resample_top_frac = float(os.environ.get("RESAMPLE_TOP_FRAC", "0.1"))
    resample_min_k = int(os.environ.get("RESAMPLE_MIN_K", "1"))
    resample_log = os.environ.get("RESAMPLE_LOG", "")
    resample_log_sample = int(os.environ.get("RESAMPLE_LOG_SAMPLE", "0"))
    # Tracing
    trace_jsonl = os.environ.get("TRACE_JSONL", "")
    trace_uni_idx = int(os.environ.get("TRACE_UNI_IDX", "-1"))
    trace_uni_jsonl = os.environ.get("TRACE_UNI_JSONL", "")
    trace_topk = int(os.environ.get("TRACE_TOPK", "100000"))
    trace_prefixes = [p.strip() for p in os.environ.get("TRACE_PREFIXES", "👑,💰").replace(",", " ").split() if p.strip()]
    trace_every = int(os.environ.get("TRACE_EVERY", "1"))
    resample_stats = int(os.environ.get("RESAMPLE_STATS", "0")) == 1
    # Checkpoint / resume
    ckpt_path = os.environ.get("AGENT_CKPT", "")
    ckpt_every = int(os.environ.get("AGENT_CKPT_EVERY", "1"))
    load_ckpt = os.environ.get("AGENT_LOAD_CKPT", "")
    bias_in_path = os.environ.get("AGENT_BIAS_IN", "")
    bias_out_path = os.environ.get("AGENT_BIAS_OUT", "")
    only_final = int(os.environ.get("AGENT_ONLY_FINAL", "0")) == 1
    # Final-run heartbeat (prints progress without needing CEM iterations)
    final_heartbeat_every = int(os.environ.get("FINAL_HEARTBEAT_EVERY", "0"))
    final_heartbeat_secs = float(os.environ.get("FINAL_HEARTBEAT_SECS", "0"))

    # Compile once
    rules, idx_to_id, registry = load_rules_with_ids(csv_path)
    # Optionally append policy rules (text file) to physics rules before compile
    policy_rules_appended = 0
    policy_file_path = os.environ.get("POLICY_FILE", "")
    if policy_file_path:
        try:
            ptxt = Path(policy_file_path)
            if ptxt.exists():
                parser_extra = SignamancyParser(registry)
                extra_rules = parser_extra.parse_text(ptxt.read_text(encoding="utf-8"))
                if extra_rules:
                    rules.extend(extra_rules)
                    policy_rules_appended = len(extra_rules)
                    print(f"[Policy] appended {policy_rules_appended} policy rules into physics")
        except Exception as e:
            print(f"[Policy] append rules failed: {e}")
    compiler = SignamancyCompiler(registry)
    kernel = compiler.compile(rules)
    num_rules = kernel.num_rules
    # CPU valve detector
    cpu_needed = _cpu_valve_needed(rules, registry)

    # Build reverse map: ID -> list of rule indices
    id_to_indices: dict[str, list[int]] = {}
    for idx in range(num_rules):
        rid = idx_to_id.get(idx)
        if rid:
            id_to_indices.setdefault(rid, []).append(idx)

    # Load policy once (verify) if provided
    pm: PolicyManager | None = None
    policy_bias_vec = torch.zeros(0)
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
            # Precompute static rule bias vector from policy (log-weights per rule)
            policy_bias_vec = torch.zeros(num_rules, dtype=torch.float32)
            for rid, w in pm.rule_desires.items():
                idxs = id_to_indices.get(rid, [])
                if not idxs and "#" not in rid:
                    base = rid
                    for key, indices in id_to_indices.items():
                        if key == base or key.startswith(base + "#"):
                            idxs += indices
                if not idxs:
                    continue
                logw = float(torch.log(torch.tensor(max(w, 1e-6))).item())
                for i in idxs:
                    policy_bias_vec[i] += logw
        except Exception as e:
            print(f"[Policy] load/verify error: {e}")

    # Optional autotune: sweep batch/pop/horizon to maximize steps/sec
    if do_autotune:
        tune_batches = _parse_int_list(os.environ.get("ATUNE_BATCHES", "4096 8192 16384 32768 65536 131072 262144 524288"))
        tune_pops = _parse_int_list(os.environ.get("ATUNE_POPS", str(pop)))
        if not tune_pops:
            tune_pops = [pop]
        tune_horizons = _parse_int_list(os.environ.get("ATUNE_HORIZONS", str(horizon)))
        if not tune_horizons:
            tune_horizons = [horizon]
        warmup_steps = int(os.environ.get("ATUNE_WARMUP_STEPS", "10"))
        measure_steps = int(os.environ.get("ATUNE_MEASURE_STEPS", "200"))
        metric = os.environ.get("ATUNE_METRIC", "universes").strip().lower()  # 'universes' | 'steps' | 'wall'
        target_universes = float(os.environ.get("ATUNE_TARGET_UNIVERSES", "0"))  # if >0 and metric='wall', normalize work
        print(f"[AUTOTUNE] device={device} batches={tune_batches} pops={tune_pops} horizons={tune_horizons} warmup={warmup_steps} measure={measure_steps}", flush=True)
        best = None  # (score, steps_per_sec, universes_per_sec, batch, pop, horizon, vram_gb)
        for b in tune_batches:
            for p in tune_pops:
                for h in tune_horizons:
                    try:
                        engine, bridge = build_engine_from_kernel(kernel, registry, b, device)
                        # Minimal init
                        bridge.inject_signal("💫")
                        if pm:
                            try:
                                # Static policy application; no dynamic refresh in tune
                                # (fast and representative for engine workload)
                                pm.apply_to_engine(engine, registry, id_to_indices, policy_gain=policy_gain)
                            except Exception:
                                pass
                        # Warmup
                        for _ in range(max(0, warmup_steps)):
                            engine.step()
                        if device == "cuda" and torch.cuda.is_available():
                            torch.cuda.synchronize()
                            torch.cuda.reset_peak_memory_stats()
                        # Determine measurement steps
                        steps_to_run = max(1, measure_steps)
                        if metric == "wall" and target_universes > 0:
                            steps_to_run = int(math.ceil(target_universes / float(b)))
                        t0 = time.perf_counter()
                        for _ in range(steps_to_run):
                            engine.step()
                        if device == "cuda" and torch.cuda.is_available():
                            torch.cuda.synchronize()
                            vram_bytes = torch.cuda.max_memory_allocated()
                        else:
                            vram_bytes = 0
                        dt = max(1e-9, time.perf_counter() - t0)
                        sps = steps_to_run / dt
                        ups = sps * float(b)  # universes per second = steps/s * batch
                        vram_gb = float(vram_bytes) / (1024 ** 3)
                        if metric == "wall" and target_universes > 0:
                            total_universes = float(steps_to_run) * float(b)
                            print(f"[AUTOTUNE] batch={b} pop={p} horizon={h} -> {dt:.3f}s for {total_universes/1e6:.3f} M-universes, {ups/1e6:.3f} M-universes/s, vram~{vram_gb:.2f} GB")
                            score = -dt  # minimize wall clock for fixed work
                        else:
                            print(f"[AUTOTUNE] batch={b} pop={p} horizon={h} -> {sps:.2f} steps/s, {ups/1e6:.3f} M-universes/s, vram~{vram_gb:.2f} GB")
                            score = ups if metric == "universes" else sps
                        if best is None:
                            best = (score, sps, ups, b, p, h, vram_gb)
                        else:
                            if score > best[0]:
                                best = (score, sps, ups, b, p, h, vram_gb)
                    except RuntimeError as e:
                        em = str(e).lower()
                        if "out of memory" in em or "cuda" in em and "alloc" in em:
                            print(f"[AUTOTUNE] OOM at batch={b} pop={p} horizon={h}, skipping")
                            # Best effort continue
                            continue
                        else:
                            print(f"[AUTOTUNE] error at batch={b} pop={p} horizon={h}: {e}")
                            continue
        if best is None:
            print("[AUTOTUNE] no successful configuration found.")
            return
        _, sps, ups, bbest, pbest, hbest, vram_gb = best
        print(f"[AUTOTUNE] best: batch={bbest} pop={pbest} horizon={hbest} -> {sps:.2f} steps/s, {ups/1e6:.3f} M-universes/s, vram~{vram_gb:.2f} GB (metric={metric})")
        print(f"[AUTOTUNE] To use: set AGENT_BATCH={bbest}&& set CEM_POP={pbest}&& set AGENT_HORIZON={hbest}")
        # If requested, adopt best and proceed; else return
        if int(os.environ.get("ATUNE_RUN", "0")) != 1:
            return
        batch_size, pop, horizon = bbest, pbest, hbest

    print(f"[CEM] device={device} batch={batch_size} horizon={horizon} iters={iters} pop={pop} prefixes={prefixes}", flush=True)

    mean = torch.zeros(num_rules, dtype=torch.float32)
    std = torch.full((num_rules,), init_std, dtype=torch.float32)

    best_bias = None
    best_score = -1e9
    # Resume load
    if load_ckpt and Path(load_ckpt).exists():
        try:
            data = torch.load(load_ckpt, map_location="cpu")
            if int(data.get("num_rules", -1)) == num_rules:
                mean = data["mean"].float()
                std = data["std"].float()
                best_bias = data.get("best_bias", None)
                if best_bias is not None:
                    best_bias = best_bias.float()
                best_score = float(data.get("best_score", -1e9))
                print(f"[CEM] resumed from {load_ckpt} (iter={data.get('iter', '?')}, best={best_score:.3f})")
            else:
                print(f"[CEM] resume ignored: num_rules mismatch (ckpt={data.get('num_rules')}, now={num_rules})")
        except Exception as e:
            print(f"[CEM] resume failed: {e}")

    if not only_final and iters > 0:
        # Build a single reusable engine for candidate evaluation to avoid per-candidate reinitialization cost
        engine_train, bridge_train = build_engine_from_kernel(kernel, registry, train_batch, device)
        engine_train.cfg.enable_cpu_offload = cpu_needed
        engine_train.cfg.single_action_mode = single_action
        # Attach rule IDs once
        engine_train.rule_ids = [idx_to_id.get(i2, f"Rule#{i2}") for i2 in range(num_rules)]
        # Seed once to baseline (physics + policy start)
        bridge_train.inject_signal("🎬")
        bridge_train.inject_signal("💫")
        engine_train.step(); engine_train.step()
        # Apply static policy once (sheet does not depend on candidate bias)
        if pm:
            try:
                pm.apply_to_engine(engine_train, registry, id_to_indices, policy_gain=policy_gain)
            except Exception as e:
                print(f"[Policy] warning: {e}")
        # Build prefix indices once (for GPU objective)
        prefix_idx_by_block_train = _build_prefix_indices(registry, prefixes)
        # Snapshot baseline engine state to restore before each candidate
        def _snapshot_engine_state(eng: SignamancyEngine):
            return {bt: eng.state[bt].clone() for bt in BlockType}
        def _restore_engine_state(eng: SignamancyEngine, snap: dict[BlockType, torch.Tensor]):
            for bt in BlockType:
                eng.state[bt].copy_(snap[bt])
            # Clear transient traces
            eng.last_fired_mask = None
            eng.last_prior_valid = None
            eng.last_scaled_logits = None
            eng.last_choice = None
        baseline_state = _snapshot_engine_state(engine_train)
        # Also snapshot one-shot bookkeeping so single-fire constraints reset properly
        oneshot_ready0 = getattr(engine_train, "_oneshot_ready", False)
        oneshot_fired0 = {k: v.clone() for k, v in getattr(engine_train, "_oneshot_fired", {}).items()}
        def _restore_oneshot(eng: SignamancyEngine):
            try:
                eng._oneshot_ready = oneshot_ready0  # type: ignore[attr-defined]
                eng._oneshot_fired = {k: v.clone() for k, v in oneshot_fired0.items()}  # type: ignore[attr-defined]
            except Exception:
                pass
        for it in range(iters):
            print(f"[CEM] iter {it+1}/{iters}...")
            # Capture a base RNG state once per iteration for common random numbers
            base_cpu_state = torch.get_rng_state()
            base_cuda_states = torch.cuda.get_rng_state_all() if (device == "cuda" and torch.cuda.is_available()) else None
            candidates = []
            scores = []
            total_engine_steps = 0
            iter_t0 = time.perf_counter() if profile_iter else None
            iter_replacements = 0
            iter_dead_rows = 0
            for i in range(pop):
                # Restore RNG so each candidate sees the same random streams
                if use_crn:
                    torch.set_rng_state(base_cpu_state)
                    if base_cuda_states is not None:
                        torch.cuda.set_rng_state_all(base_cuda_states)
                bias = (mean + std * torch.randn_like(mean)).clamp_(-3.0, 3.0)
                # Reuse engine; restore baseline and one-shot bookkeeping
                engine = engine_train
                _restore_engine_state(engine, baseline_state)
                _restore_oneshot(engine)
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
                # Combine learned bias with static policy bias (if any)
                if policy_bias_vec.numel() == num_rules:
                    combined = use_bias + policy_bias_vec.to(use_bias.device)
                else:
                    combined = use_bias
                # Optional: add GPU planner aggregated bias once per candidate (using same target prefixes)
                if planner_enable and planner_in_cem:
                    try:
                        planner = GPUPlanner.from_env()
                        # Planner targets default to CEM prefixes with unit weights
                        t_weights = [1.0] * len(prefixes)
                        t_pairs = list(zip(prefixes, t_weights))
                        pbias = planner.aggregated_bias(engine, registry, t_pairs)
                        combined = combined + pbias.to(combined.device)
                    except Exception:
                        pass
                set_biases(engine, combined.to(engine.device))
                # Lineage (optimization-time): per-row origin and generation
                lineage_id = torch.arange(engine.cfg.batch_size, dtype=torch.long)
                lineage_gen = torch.zeros(engine.cfg.batch_size, dtype=torch.long)
                steps_run = 0
                decisions = 0
                # Trajectory aggregation
                traj_sum = 0.0
                traj_cnt = 0
                traj_max = float("-inf")
                last_score = 0.0
                if decision_only:
                    while decisions < train_horizon:
                        # Burst through physics-only frames (≤1 effective choice)
                        sub = 0
                        while sub < physics_burst_max:
                            stats = engine.compute_choice_stats(collapse_same_base=True)
                            if bool(stats.get("any_decision", False)):
                                break
                            engine.step(); steps_run += 1; sub += 1
                            if getattr(engine, "last_prior_valid", None) is not None:
                                has_any = engine.last_prior_valid.any(dim=1)
                                iter_dead_rows += int((~has_any).sum().item())
                        # If after bursting there is still no multi-choice, we're done
                        stats = engine.compute_choice_stats(collapse_same_base=True)
                        if not bool(stats.get("any_decision", False)):
                            break
                        # Do exactly one decision step
                        engine.step(); steps_run += 1; decisions += 1
                        if getattr(engine, "last_prior_valid", None) is not None:
                            has_any = engine.last_prior_valid.any(dim=1)
                            iter_dead_rows += int((~has_any).sum().item())
                        # Evaluate objective on schedule
                        if (decisions % max(1, eval_every) == 0) or (decisions >= train_horizon):
                            with torch.no_grad():
                                scores_vec = _score_universes(engine, prefix_idx_by_block_train)
                                s_now = float(scores_vec.mean().item())
                                last_score = s_now
                                traj_sum += s_now
                                traj_cnt += 1
                                if s_now > traj_max:
                                    traj_max = s_now
                        # Periodic resampling at decision boundaries
                        if resample_every > 0 and (decisions % resample_every == 0):
                            with torch.no_grad():
                                scores_vec = _score_universes(engine, prefix_idx_by_block_train)
                                k = max(resample_min_k, int(resample_top_frac * engine.cfg.batch_size))
                                k = min(k, engine.cfg.batch_size // 2)
                                if k > 0:
                                    top = torch.topk(scores_vec, k=k, largest=True).indices
                                    worst = torch.topk(scores_vec, k=k, largest=False).indices
                                    for bt in BlockType:
                                        s = engine.state[bt]
                                        s.index_copy_(0, worst.to(s.device), s.index_select(0, top.to(s.device)))
                                    lineage_id[worst.cpu()] = lineage_id[top.cpu()]
                                    lineage_gen[worst.cpu()] = lineage_gen[top.cpu()] + 1
                                    if resample_log:
                                        with open(resample_log, "a", encoding="utf-8") as rf:
                                            count = k
                                            sel = list(range(count))
                                            if resample_log_sample > 0 and resample_log_sample < count:
                                                sel = sel[:resample_log_sample]
                                            for j in sel:
                                                ti = int(top[j].item()); wi = int(worst[j].item())
                                                rec = {
                                                    "iter": it + 1, "cand": i + 1, "step": decisions,
                                                    "top_idx": ti, "worst_idx": wi,
                                                    "lineage_id": int(lineage_id[ti].item()),
                                                    "lineage_gen_src": int((lineage_gen[ti].item())),
                                                    "lineage_gen_dst": int((lineage_gen[wi].item()))
                                                }
                                                rf.write(json.dumps(rec, ensure_ascii=False) + "\n")
                                    iter_replacements += int(k)
                else:
                    for t in range(train_horizon):
                        engine.step(); steps_run += 1
                        if getattr(engine, "last_prior_valid", None) is not None:
                            has_any = engine.last_prior_valid.any(dim=1)
                            iter_dead_rows += int((~has_any).sum().item())
                        # Evaluate objective on schedule
                        if ((t + 1) % max(1, eval_every) == 0) or (t + 1 >= train_horizon):
                            with torch.no_grad():
                                scores_vec = _score_universes(engine, prefix_idx_by_block_train)
                                s_now = float(scores_vec.mean().item())
                                last_score = s_now
                                traj_sum += s_now
                                traj_cnt += 1
                                if s_now > traj_max:
                                    traj_max = s_now
                        if resample_every > 0 and ((t + 1) % resample_every == 0):
                            with torch.no_grad():
                                scores_vec = _score_universes(engine, prefix_idx_by_block_train)
                                k = max(resample_min_k, int(resample_top_frac * engine.cfg.batch_size))
                                k = min(k, engine.cfg.batch_size // 2)
                                if k > 0:
                                    top = torch.topk(scores_vec, k=k, largest=True).indices
                                    worst = torch.topk(scores_vec, k=k, largest=False).indices
                                    for bt in BlockType:
                                        s = engine.state[bt]
                                        s.index_copy_(0, worst.to(s.device), s.index_select(0, top.to(s.device)))
                                    lineage_id[worst.cpu()] = lineage_id[top.cpu()]
                                    lineage_gen[worst.cpu()] = lineage_gen[top.cpu()] + 1
                                    if resample_log:
                                        with open(resample_log, "a", encoding="utf-8") as rf:
                                            count = k
                                            sel = list(range(count))
                                            if resample_log_sample > 0 and resample_log_sample < count:
                                                sel = sel[:resample_log_sample]
                                            for j in sel:
                                                ti = int(top[j].item()); wi = int(worst[j].item())
                                                rec = {
                                                    "iter": it + 1, "cand": i + 1, "step": t + 1,
                                                    "top_idx": ti, "worst_idx": wi,
                                                    "lineage_id": int(lineage_id[ti].item()),
                                                    "lineage_gen_src": int((lineage_gen[ti].item())),
                                                    "lineage_gen_dst": int((lineage_gen[wi].item()))
                                                }
                                                rf.write(json.dumps(rec, ensure_ascii=False) + "\n")
                                    iter_replacements += int(k)
                total_engine_steps += steps_run
                # Aggregate trajectory into candidate score
                if obj_mode == "max":
                    score = traj_max if traj_cnt > 0 else last_score
                elif obj_mode == "sum":
                    score = traj_sum
                elif obj_mode in ("avg", "mean"):
                    score = (traj_sum / max(1, traj_cnt))
                else:  # 'final'
                    score = last_score
                candidates.append(use_bias)
                scores.append(score)
                if (i + 1) % max(1, log_every_cand) == 0:
                    print(f"  cand {i+1}/{pop} score={score:.3f}")
                if score > best_score:
                    best_score = score
                    best_bias = bias.clone()
            if profile_iter and iter_t0 is not None:
                if device == "cuda" and torch.cuda.is_available():
                    torch.cuda.synchronize()
                dt_iter = max(1e-9, time.perf_counter() - iter_t0)
                steps_per_sec = total_engine_steps / dt_iter
                universes_per_sec = steps_per_sec * float(batch_size)
                print(f"[CEM] iter {it+1}/{iters} throughput: {steps_per_sec:.2f} steps/s, {universes_per_sec/1e6:.3f} M-universes/s, dt={dt_iter:.3f}s (batch={batch_size}, pop={pop}, horizon={horizon})")
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
            if resample_stats:
                print(f"[Resample] iter {it+1}: replaced={iter_replacements} dead_rows_seen={iter_dead_rows}")
            # Save checkpoint
            if ckpt_path and ((it + 1) % max(1, ckpt_every) == 0):
                try:
                    torch.save({"mean": mean.cpu(), "std": std.cpu(), "best_bias": (best_bias.cpu() if best_bias is not None else None), "best_score": best_score, "num_rules": num_rules, "iter": it + 1}, ckpt_path)
                    print(f"[CEM] checkpoint saved: {ckpt_path}")
                except Exception as e:
                    print(f"[CEM] checkpoint save failed: {e}")
    else:
        print("[CEM] skipping optimization (only_final or iters=0)")

    # Final run with best
    engine, bridge = build_engine_from_kernel(kernel, registry, batch_size, device)
    engine.cfg.enable_cpu_offload = cpu_needed
    engine.cfg.single_action_mode = single_action
    if use_crn:
        # Reset RNG to a stable state for the showcase run
        torch.manual_seed(12345)
        if device == "cuda" and torch.cuda.is_available():
            torch.cuda.manual_seed_all(12345)
    # Attach rule IDs before any steps (for one-shot bases masking)
    engine.rule_ids = [idx_to_id.get(i, f"Rule#{i}") for i in range(num_rules)]
    bridge.inject_signal("🎬"); bridge.inject_signal("💫"); engine.step(); engine.step()
    last_hb_t = time.perf_counter()
    # Optional debug: check if any rules are valid after seeding
    if int(os.environ.get("AGENT_DEBUG_VALID", "0")) == 1:
        try:
            stats0 = engine.compute_choice_stats(collapse_same_base=True)
            pv0 = stats0.get("prior_valid")
            if pv0 is not None and torch.is_tensor(pv0):
                any_rows = int(pv0.any(dim=1).sum().item())
                max_cnt = int(stats0.get("counts", torch.zeros(1)).max().item())
                print(f"[DEBUG] post-seed valid rows={any_rows}/{engine.cfg.batch_size} max_valid_per_row={max_cnt}")
            else:
                print("[DEBUG] post-seed: prior_valid not available")
        except Exception as e:
            print(f"[DEBUG] post-seed check failed: {e}")
    if pm:
        try:
            pm.apply_to_engine(engine, registry, id_to_indices, policy_gain=policy_gain)
        except Exception as e:
            print(f"[Policy] warning: {e}")
    # Optional: initialize GPU planner for final run
    planner = GPUPlanner.from_env() if planner_enable else None
    planner_every = 0
    planner_targets: list[tuple[str, float]] = []
    planner_uni_targets_idx_by_block: dict[BlockType, torch.Tensor] = {}
    if planner is not None:
        try:
            # Planner prefixes: PLANNER_PREFIXES > TRACE_PREFIXES > TARGET_RESOURCE_PREFIXES
            raw_pp = os.environ.get("PLANNER_PREFIXES", "").strip()
            if raw_pp in ("*", "ALL", "all"):
                # All tokens -> not recommended; default to TARGET prefixes
                pfx = prefixes
            else:
                base_pp = raw_pp if raw_pp else os.environ.get("TRACE_PREFIXES", "")
                pfx = [p.strip() for p in base_pp.replace(",", " ").split() if p.strip()]
                if not pfx:
                    pfx = prefixes
            planner_targets = list(zip(pfx, [1.0] * len(pfx)))
            planner_every = max(1, int(os.environ.get("PLANNER_EVERY", str(planner.cfg.eval_every_steps))))
            planner_uni_targets_idx_by_block = _build_prefix_indices(registry, pfx)
        except Exception:
            planner_targets = []
            planner_every = 0
    if reach_report:
        try:
            ra = ReachabilityAnalyzer(engine, registry)
            dead = ra.report_dead_rules(idx_to_id, strict_priority=reach_strict)
            print(f"[Reachability] dead rules (sample): {dead[:20]} total={len(dead)}")
        except Exception as e:
            print(f"[Reachability] error: {e}")
    # Optionally load external bias for final showcase
    final_bias = None
    if bias_in_path and Path(bias_in_path).exists():
        try:
            loaded = torch.load(bias_in_path, map_location="cpu")
            if isinstance(loaded, dict) and "bias" in loaded:
                final_bias = loaded["bias"].float()
            elif torch.is_tensor(loaded):
                final_bias = loaded.float()
            print(f"[CEM] loaded final bias from {bias_in_path}")
        except Exception as e:
            print(f"[CEM] load bias failed: {e}")
    if final_bias is None:
        final_bias = best_bias if best_bias is not None else torch.zeros(num_rules, dtype=torch.float32)
    if uniform_branches:
        final_bias = uniformize_biases_by_base(final_bias, idx_to_id)
    # Merge final learned bias with static policy bias
    if policy_bias_vec.numel() == num_rules:
        final_bias = final_bias + policy_bias_vec.to(final_bias.device)
    set_biases(engine, final_bias.to(engine.device))
    if bias_out_path:
        try:
            torch.save({"bias": final_bias.cpu(), "num_rules": num_rules}, bias_out_path)
            print(f"[CEM] saved final bias to {bias_out_path}")
        except Exception as e:
            print(f"[CEM] save bias failed: {e}")
    # Tracing setup (final run only)
    agg_f = open(trace_jsonl, "w", encoding="utf-8") if trace_jsonl else None
    uni_f = open(trace_uni_jsonl, "w", encoding="utf-8") if (trace_uni_jsonl and trace_uni_idx >= 0) else None
    prev_snap = bridge.get_state_snapshot()
    # Final-run lineage (no resampling): default IDs/gen
    lineage_id_final = torch.arange(engine.cfg.batch_size, dtype=torch.long)
    lineage_gen_final = torch.zeros(engine.cfg.batch_size, dtype=torch.long)
    # Heartbeat scoring over target prefixes
    hb_idx_by_block = _build_prefix_indices(registry, prefixes)
    # Build name lists per block for fast lookup
    names_by_block: dict[BlockType, list[str]] = {BlockType.BIT: [], BlockType.BYTE: [], BlockType.FLOAT: []}
    for _, meta in registry._tokens.items():  # type: ignore[attr-defined]
        # ensure list is sized by local_id positions
        li = getattr(meta, "local_id", None)
        if li is None:
            continue
        while len(names_by_block[meta.block_type]) <= li:
            names_by_block[meta.block_type].append("")
        names_by_block[meta.block_type][li] = meta.original_text
    def write_agg(step_idx: int, snap_now: dict):
        if not agg_f:
            return
        # targets aggregate from snapshot
        targets: dict[str, float] = {}
        targets_delta: dict[str, float] = {}
        for pref in trace_prefixes:
            s = 0.0
            s0 = 0.0
            for k, v in snap_now.items():
                if k.startswith(pref):
                    s += float(v.get("val", 0.0))
            for k, v in prev_snap.items():
                if k.startswith(pref):
                    s0 += float(v.get("val", 0.0))
            targets[pref] = s
            targets_delta[pref] = s - s0
        # top-K token deltas by abs change
        deltas = []
        keys = set(prev_snap.keys()) | set(snap_now.keys())
        for k in keys:
            v0 = float(prev_snap.get(k, {}).get("val", 0.0))
            v1 = float(snap_now.get(k, {}).get("val", 0.0))
            dv = v1 - v0
            if dv != 0.0:
                deltas.append((k, dv, v1))
        deltas.sort(key=lambda x: abs(x[1]), reverse=True)
        top = [{"token": k, "dv": float(dv), "v": float(v)} for k, dv, v in deltas[:trace_topk]]
        # rules fired aggregate (by base ID), top-K
        rules_top = []
        if engine.last_fired_mask is not None:
            counts = engine.last_fired_mask.sum(dim=0).detach().cpu()
            nz = torch.nonzero(counts, as_tuple=False).squeeze(1).tolist()
            base_to_c = {}
            for ridx in nz:
                rid = idx_to_id.get(int(ridx), f"Rule#{int(ridx)}")
                base = rid.split("#")[0]
                base_to_c[base] = base_to_c.get(base, 0) + int(counts[ridx].item())
            items = sorted(base_to_c.items(), key=lambda x: x[1], reverse=True)[:trace_topk]
            rules_top = [{"rule": k, "count": v} for k, v in items]
        # aggregated top tokens by mean value (like Universe state_top)
        # reuse snap_now which has token->{"val","std","type"}
        means_list = []
        try:
            all_items = [(k, float(v.get("val", 0.0))) for k, v in snap_now.items()]
            all_items.sort(key=lambda kv: kv[1], reverse=True)
            for k, val in all_items[:trace_topk]:
                means_list.append({"token": k, "v": val})
        except Exception:
            pass
        rec = {"step": step_idx, "targets": targets, "targets_delta": targets_delta, "top_deltas": top, "rules_top": rules_top, "state_top": means_list}
        agg_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    def write_uni(step_idx: int):
        if not uni_f or trace_uni_idx < 0:
            return
        uni = trace_uni_idx
        # collect per-block values
        # We'll gather candidates per block and merge
        cand: list[tuple[str, float, float]] = []
        # helper to compute deltas per block
        def add_block(bt: BlockType):
            s = engine.state[bt]
            if s.shape[1] == 0:
                return
            row = s[uni].float()
            if bt == BlockType.BIT:
                row = row.clamp_min(0.0)  # treat -1 as 0 for visibility
            names = names_by_block[bt]
            # Approx: take topK by abs delta within this block versus previous snapshot mean of this token
            # We fallback to per-universe delta against previous step's per-universe value if available
            # For simplicity here, compare versus previous aggregate value
            prev_vals = torch.zeros_like(row)
            nlen = len(names)
            # Build prev vector from prev_snap for these tokens
            if nlen > 0:
                pv = []
                for li in range(nlen):
                    nm = names[li]
                    pv.append(float(prev_snap.get(nm, {}).get("val", 0.0)))
                prev_vals = torch.tensor(pv, dtype=torch.float32, device=row.device)
            dv = (row - prev_vals).abs()
            k = min(trace_topk, dv.numel())
            if k > 0:
                idx = torch.topk(dv, k=k, largest=True).indices.tolist()
                for li in idx:
                    nm = names[li] if li < len(names) else f"{bt.name}:{li}"
                    vnow = float(row[li].item())
                    vprev = float(prev_vals[li].item()) if li < prev_vals.numel() else 0.0
                    cand.append((nm, vnow - vprev, vnow))
        add_block(BlockType.BIT)
        add_block(BlockType.BYTE)
        add_block(BlockType.FLOAT)
        cand.sort(key=lambda x: abs(x[1]), reverse=True)
        cand = cand[:trace_topk]
        fired = []
        choice = None
        valid_rules = []
        weights = []
        choice_inputs = []
        choice_deficits = []
        if engine.last_fired_mask is not None:
            mask = engine.last_fired_mask[uni].detach().cpu()
            nz = torch.nonzero(mask, as_tuple=False).squeeze(1).tolist()
            fired = [idx_to_id.get(int(r), f"Rule#{int(r)}").split("#")[0] for r in nz]
        # Valid rules and choice from engine traces (if available)
        if getattr(engine, "last_prior_valid", None) is not None and getattr(engine, "last_scaled_logits", None) is not None:
            valid_mask = engine.last_prior_valid[uni].detach().cpu()
            logits = engine.last_scaled_logits.detach().cpu()
            vidx = torch.nonzero(valid_mask, as_tuple=False).squeeze(1).tolist()
            # sort valid by logits desc
            vidx_sorted = sorted(vidx, key=lambda r: float(logits[r].item()), reverse=True)
            klist = vidx_sorted[:trace_topk]
            for r in klist:
                rid = idx_to_id.get(int(r), f"Rule#{int(r)}").split("#")[0]
                p = float(torch.sigmoid(logits[r]).item())
                weights.append({"rule": rid, "p": p})
                valid_rules.append(rid)
            if getattr(engine, "last_choice", None) is not None:
                ci = int(engine.last_choice[uni].item())
                choice = idx_to_id.get(ci, f"Rule#{ci}").split("#")[0]
            else:
                # display argmax over valid as canonical
                if len(vidx) > 0:
                    best = max(vidx, key=lambda r: float(logits[r].item()))
                    choice = idx_to_id.get(int(best), f"Rule#{int(best)}").split("#")[0]
                # Compute per-universe inputs and deficits for the chosen rule
                try:
                    if getattr(engine, "last_choice", None) is not None:
                        ci = int(engine.last_choice[uni].item())
                        # For each block, list required tokens and deficits
                        for bt in BlockType:
                            kb = engine.gpu_blocks.get(bt, None)
                            if not kb or not kb.get("in"):
                                continue
                            rule_idx_t, token_idx_t = kb["in"]["indices"]
                            req_vals_t = kb["in"]["values"]
                            # mask for this rule
                            m = (rule_idx_t == ci)
                            if not torch.is_tensor(m) or (not bool(m.any().item())):
                                continue
                            toks = token_idx_t[m]
                            reqs = req_vals_t[m]
                            if toks.numel() == 0:
                                continue
                            # current values at this universe
                            cur = engine.state[bt][uni, toks.to(engine.state[bt].device)].float().detach().cpu()
                            req = reqs.float().detach().cpu()
                            for j in range(min(toks.numel(), 50)):
                                li = int(toks[j].item())
                                name = names_by_block[bt][li] if li < len(names_by_block[bt]) else f"{bt.name}:{li}"
                                rv = float(req[j].item())
                                cv = float(cur[j].item())
                                choice_inputs.append({"token": name, "need": rv, "have": cv})
                                if cv + 1e-6 < rv:
                                    choice_deficits.append({"token": name, "missing": rv - cv})
                except Exception:
                    pass
        # Build state snapshot (top tokens by value, per block)
        state_list = []
        def add_state_block(bt: BlockType, lbl: str):
            s = engine.state[bt]
            if s.shape[1] == 0: return
            row = s[uni].float().cpu()
            names = names_by_block[bt]
            # filter by prefixes if provided
            prefs = [p.strip() for p in os.environ.get("TRACE_PREFIXES", "").replace(",", " ").split() if p.strip()]
            idxs = list(range(len(names)))
            if prefs:
                idxs = [ii for ii in idxs if any((names[ii] or "").startswith(p) for p in prefs)]
            # sort by value desc
            idxs.sort(key=lambda ii: float(row[ii].item()), reverse=True)
            for ii in idxs[:trace_topk]:
                state_list.append({"token": names[ii] or f"{lbl}:{ii}", "v": float(row[ii].item())})
        add_state_block(BlockType.BIT, "BIT")
        add_state_block(BlockType.BYTE, "BYTE")
        add_state_block(BlockType.FLOAT, "FLOAT")
        rec = {"step": step_idx, "uni": uni, "lineage_id": int(lineage_id_final[uni].item()), "lineage_gen": int(lineage_gen_final[uni].item()), "top_deltas": [{"token": n, "dv": float(dv), "v": float(v)} for n, dv, v in cand], "fired_rules": fired, "choice": choice, "valid_rules_top": weights, "choice_inputs": choice_inputs[:50], "choice_deficits": choice_deficits[:50], "state_top": state_list}
        uni_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    # initial trace rows
    if agg_f:
        write_agg(0, prev_snap)
    if uni_f:
        write_uni(0)
    decisions = 0
    steps_run_final = 0
    step_idx = 0
    # Helper: emit compact heartbeat with validity and score across prefixes
    def _emit_hb():
        nonlocal last_hb_t
        try:
            stats_hb = engine.compute_choice_stats(collapse_same_base=True)
            pv = stats_hb.get("prior_valid")
            if pv is not None and torch.is_tensor(pv):
                valid_rows = int(pv.any(dim=1).sum().item())
            else:
                valid_rows = 0
        except Exception:
            valid_rows = 0
        try:
            scores_vec = _score_universes(engine, hb_idx_by_block)
            s_mean = float(scores_vec.mean().item())
            s_max = float(scores_vec.max().item())
        except Exception:
            s_mean = 0.0
            s_max = 0.0
        # Build condensed emoji snapshot (means across batch)
        snap_chunks: list[str] = []
        try:
            topk = max(1, int(os.environ.get("FINAL_HEARTBEAT_TOPK", "10")))
            # Prefix filter precedence: FINAL_HEARTBEAT_PREFIXES > TRACE_PREFIXES > TARGET_RESOURCE_PREFIXES
            raw_pref = os.environ.get("FINAL_HEARTBEAT_PREFIXES", "").strip()
            if raw_pref in ("*", "ALL", "all"):
                prefs: list[str] = []  # no filtering; show all
            else:
                base_pref = raw_pref if raw_pref else os.environ.get("TRACE_PREFIXES", "")
                prefs = [p.strip() for p in base_pref.replace(",", " ").split() if p.strip()]
                if not prefs:
                    prefs = prefixes  # fall back to target prefixes
            cand: list[tuple[str, float]] = []
            for bt in BlockType:
                s = engine.state[bt]
                if s.shape[1] == 0: 
                    continue
                means = s.float().clamp_min(0.0).mean(dim=0).detach().cpu().tolist()
                names = names_by_block[bt]
                for li, mv in enumerate(means):
                    if li >= len(names): 
                        continue
                    nm = names[li]
                    if not nm:
                        continue
                    if prefs and not any(nm.startswith(p) for p in prefs):
                        continue
                    if mv <= 0.0:
                        continue
                    cand.append((nm, float(mv)))
            cand.sort(key=lambda x: x[1], reverse=True)
            for nm, mv in cand[:topk]:
                snap_chunks.append(f"{nm}{mv:.1f}")
        except Exception:
            pass
        snap_str = (" | " + " ".join(snap_chunks)) if snap_chunks else ""
        # Optional per-phase GPU profile summary (averages)
        prof_str = ""
        try:
            if int(os.environ.get("FINAL_HEARTBEAT_PROFILE", "0")) == 1:
                if getattr(engine, "get_profile_stats", None) is not None:
                    ps = engine.get_profile_stats()
                    c = max(1, int(ps.get("count", 0)))
                    t_ms = float(ps.get("total_ms", 0.0)) / c
                    v_ms = float(ps.get("valid_ms", 0.0)) / c
                    r_ms = float(ps.get("resolve_ms", 0.0)) / c
                    u_ms = float(ps.get("update_ms", 0.0)) / c
                    p_ms = float(ps.get("physics_ms", 0.0)) / c
                    prof_str = f" | ms/step={t_ms:.2f} (valid={v_ms:.2f} resolve={r_ms:.2f} update={u_ms:.2f} physics={p_ms:.2f})"
        except Exception:
            pass
        # Fired rule bases (this step), top-K by count (disabled by default)
        fired_str = ""
        try:
            if int(os.environ.get("FINAL_HEARTBEAT_SHOW_RULES", "0")) == 1:
                top_rules = max(1, int(os.environ.get("FINAL_HEARTBEAT_RULETOPK", "10")))
                fm = getattr(engine, "last_fired_mask", None)
                if fm is not None and torch.is_tensor(fm):
                    counts = fm.sum(dim=0).detach().cpu()
                    nz = torch.nonzero(counts, as_tuple=False).squeeze(1).tolist()
                    base_to_c: dict[str, int] = {}
                    for ridx in nz:
                        rid = idx_to_id.get(int(ridx), f"Rule#{int(ridx)}")
                        base = rid.split("#")[0]
                        base_to_c[base] = base_to_c.get(base, 0) + int(counts[ridx].item())
                    items = sorted(base_to_c.items(), key=lambda x: x[1], reverse=True)[:top_rules]
                    if items:
                        fired_str = " | " + " ".join([f"{k}×{v}" for k, v in items])
        except Exception:
            pass
        if int(os.environ.get("DECISION_ONLY", "1")) == 1:
            print(f"[FINAL] step={step_idx} decisions={decisions}/{horizon} valid={valid_rows}/{engine.cfg.batch_size} score_mean={s_mean:.3f} score_max={s_max:.3f}{prof_str}{fired_str}{snap_str}", flush=True)
        else:
            print(f"[FINAL] step={step_idx}/{horizon} valid={valid_rows}/{engine.cfg.batch_size} score_mean={s_mean:.3f} score_max={s_max:.3f}{prof_str}{fired_str}{snap_str}", flush=True)
        last_hb_t = time.perf_counter()
    if int(os.environ.get("DECISION_ONLY", "1")) == 1:
        while decisions < horizon:
            # Burst through physics-only steps, logging every engine step
            sub = 0
            while sub < physics_burst_max:
                stats = engine.compute_choice_stats(collapse_same_base=True)
                if bool(stats.get("any_decision", False)):
                    break
                engine.step(); steps_run_final += 1; sub += 1; step_idx += 1
                # Planner aggregated pass on schedule
                if planner is not None and planner_targets and (step_idx % max(1, planner_every) == 0):
                    try:
                        base = final_bias
                        if policy_bias_vec.numel() == num_rules:
                            base = base + policy_bias_vec.to(base.device)
                        # Aggregated bias
                        pbias_agg = planner.aggregated_bias(engine, registry, planner_targets)
                        # Optional per-universe bias on selected "hard" rows: choose bottom M by current target score
                        pbias_uni = torch.zeros_like(pbias_agg)
                        if planner.cfg.enable_per_universe:
                            try:
                                scores_vec = _score_universes(engine, planner_uni_targets_idx_by_block)
                                m = max(1, int(os.environ.get("PLANNER_MAX_UNI", str(planner.cfg.max_universes))))
                                m = min(m, engine.cfg.batch_size)
                                uni_idx = torch.topk(scores_vec, k=m, largest=False).indices  # bottom M universes
                                pbias_uni = planner.per_universe_bias(engine, registry, planner_targets, uni_idx.to(engine.device))
                            except Exception:
                                pass
                        set_biases(engine, (base + pbias_agg.to(base.device) + pbias_uni.to(base.device)))
                    except Exception:
                        pass
                now = time.perf_counter()
                if final_heartbeat_every > 0 and (step_idx % final_heartbeat_every == 0):
                    _emit_hb()
                elif final_heartbeat_secs > 0 and (now - last_hb_t) >= final_heartbeat_secs:
                    _emit_hb()
                if (step_idx) % max(1, trace_every) == 0:
                    snap_now = bridge.get_state_snapshot()
                    write_agg(step_idx, snap_now)
                    write_uni(step_idx)
                    prev_snap = snap_now
            # If still no multi-choice, we're done
            stats = engine.compute_choice_stats(collapse_same_base=True)
            if not bool(stats.get("any_decision", False)):
                break
            # Execute exactly one decision step (also logged)
            engine.step(); steps_run_final += 1; decisions += 1; step_idx += 1
            # Planner aggregated pass on schedule
            if planner is not None and planner_targets and (step_idx % max(1, planner_every) == 0):
                try:
                    base = final_bias
                    if policy_bias_vec.numel() == num_rules:
                        base = base + policy_bias_vec.to(base.device)
                    pbias_agg = planner.aggregated_bias(engine, registry, planner_targets)
                    pbias_uni = torch.zeros_like(pbias_agg)
                    if planner.cfg.enable_per_universe:
                        try:
                            scores_vec = _score_universes(engine, planner_uni_targets_idx_by_block)
                            m = max(1, int(os.environ.get("PLANNER_MAX_UNI", str(planner.cfg.max_universes))))
                            m = min(m, engine.cfg.batch_size)
                            uni_idx = torch.topk(scores_vec, k=m, largest=False).indices
                            pbias_uni = planner.per_universe_bias(engine, registry, planner_targets, uni_idx.to(engine.device))
                        except Exception:
                            pass
                    set_biases(engine, (base + pbias_agg.to(base.device) + pbias_uni.to(base.device)))
                except Exception:
                    pass
            now = time.perf_counter()
            if final_heartbeat_every > 0 and (step_idx % final_heartbeat_every == 0):
                _emit_hb()
            elif final_heartbeat_secs > 0 and (now - last_hb_t) >= final_heartbeat_secs:
                _emit_hb()
            if (step_idx) % max(1, trace_every) == 0:
                snap_now = bridge.get_state_snapshot()
                write_agg(step_idx, snap_now)
                write_uni(step_idx)
                prev_snap = snap_now
    else:
        for t in range(horizon):
            engine.step(); steps_run_final += 1; step_idx += 1
            # Planner aggregated pass on schedule
            if planner is not None and planner_targets and (step_idx % max(1, planner_every) == 0):
                try:
                    base = final_bias
                    if policy_bias_vec.numel() == num_rules:
                        base = base + policy_bias_vec.to(base.device)
                    pbias_agg = planner.aggregated_bias(engine, registry, planner_targets)
                    pbias_uni = torch.zeros_like(pbias_agg)
                    if planner.cfg.enable_per_universe:
                        try:
                            scores_vec = _score_universes(engine, planner_uni_targets_idx_by_block)
                            m = max(1, int(os.environ.get("PLANNER_MAX_UNI", str(planner.cfg.max_universes))))
                            m = min(m, engine.cfg.batch_size)
                            uni_idx = torch.topk(scores_vec, k=m, largest=False).indices
                            pbias_uni = planner.per_universe_bias(engine, registry, planner_targets, uni_idx.to(engine.device))
                        except Exception:
                            pass
                    set_biases(engine, (base + pbias_agg.to(base.device) + pbias_uni.to(base.device)))
                except Exception:
                    pass
            now = time.perf_counter()
            if final_heartbeat_every > 0 and (step_idx % final_heartbeat_every == 0):
                _emit_hb()
            elif final_heartbeat_secs > 0 and (now - last_hb_t) >= final_heartbeat_secs:
                _emit_hb()
            if (step_idx) % max(1, trace_every) == 0:
                snap_now = bridge.get_state_snapshot()
                write_agg(step_idx, snap_now)
                write_uni(step_idx)
                prev_snap = snap_now
    if agg_f:
        agg_f.close()
    if uni_f:
        uni_f.close()
    snap = bridge.get_state_snapshot()
    print("\n--- Final Snapshot (first 20 tokens) ---")
    print(json.dumps({k: snap[k] for k in list(snap)[:20]}, indent=2, ensure_ascii=False))
    print(f"Best score={best_score:.3f}")
    # Export emoji policy sheet if requested
    if policy_export:
        try:
            if pm is None:
                pm = PolicyManager()
            if final_bias is not None:
                pm.export_sheet(Path(policy_export), final_bias.detach().cpu(), id_to_indices, snap, pm.targets)
                print(f"[Policy] exported to {policy_export}")
            else:
                print("[Policy] skip export: no learned bias available")
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


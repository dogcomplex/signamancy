import os
import torch
import torch.nn.functional as F
from typing import Dict
from dataclasses import dataclass
from .registry import BlockType
from .compiler import KernelData

@dataclass
class SimulationConfig:
    batch_size: int = 1024
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    enable_cpu_offload: bool = True
    
    # Thermodynamics
    temperature: float = 1.0  # Multiplier for probability/variance
    max_physics_substeps: int = 10
    # Row-slice controls
    row_slice_max_uniques: int | None = None
    
    # Debug/logging
    enable_priority_logging: bool = False
    priority_log_limit: int = 50
    priority_log_path: str | None = None
    log_same_base_ties: bool = False
    # Trace/selection
    single_action_mode: bool = True

class SignamancyEngine:
    """
    The Sensus Runtime (v2).
    
    Architecture:
    - Data: Block-Archetype Tensors (BIT, BYTE, FLOAT).
    - Logic: Vectorized Validity Checking & Sparse Matrix Update.
    - Physics: Sub-stepping for Unit Conversion and Sink Rules.
    """
    def __init__(self, kernel: KernelData, config: SimulationConfig = SimulationConfig()):
        self.cfg = config
        self.kernel = kernel
        self.device = torch.device(self.cfg.device)
        
        self.state: Dict[BlockType, torch.Tensor] = {}
        self.rule_biases_static: torch.Tensor | None = None
        self.rule_biases_dyn: torch.Tensor | None = None
        self.priority_tie_events: int = 0
        self.priority_tie_samples: list[list[int]] = []
        self.rule_ids: list[str] | None = None
        self.cpu_callbacks = {}
        self.reachability_guide_mask: torch.Tensor | None = None  # [Rules] boolean mask
        self.last_fired_mask: torch.Tensor | None = None  # [Batch, Rules] for tracing
        self.last_prior_valid: torch.Tensor | None = None  # [Batch, Rules] for tracing
        self.last_scaled_logits: torch.Tensor | None = None  # [Rules] for tracing
        self.last_choice: torch.Tensor | None = None  # [Batch] chosen rule index in single-action mode
        # One-shot rule support (e.g., ID_Start fires at most once per universe)
        raw_oneshot = os.environ.get("ONESHOT_BASES", "ID_Start")
        self._oneshot_bases = [s for s in raw_oneshot.replace(",", " ").split() if s.strip()]
        self._oneshot_ready = False
        self._oneshot_rule_indices: list[int] = []
        self._oneshot_fired: dict[int, torch.Tensor] = {}  # rule_idx -> [Batch] bool
        self._init_memory()
        self._upload_kernels()
        # Initialize per-rule biases (default zeros = no effect)
        self.rule_biases_static = torch.zeros(self.num_rules, dtype=torch.float32, device=self.device)
        self.rule_biases_dyn = torch.zeros(self.num_rules, dtype=torch.float32, device=self.device)
        # Advantage biases from value network: [Batch, Rules] per-universe per-rule advantages
        self._advantage_biases: torch.Tensor | None = None
        # Profiling accumulators (ms)
        self._prof_enable = os.environ.get("ENGINE_PROFILE_PHASES", "0") == "1"
        self._prof_count = 0
        self._prof_valid_ms = 0.0
        self._prof_resolve_ms = 0.0
        self._prof_update_ms = 0.0
        self._prof_physics_ms = 0.0
        self._prof_cpu_ms = 0.0
        self._prof_total_ms = 0.0
        # BIT escalation detection
        self._escalation_check_interval = int(os.environ.get("BIT_ESCALATION_CHECK_INTERVAL", "50"))
        self._escalation_step_counter = 0
        self._bit_overflow_counts: Dict[int, int] = {}  # local_id -> count of overflow events
        self._bit_token_names: Dict[int, str] = {}  # local_id -> token name (for reporting)
    
    def reset_profile_stats(self):
        self._prof_count = 0
        self._prof_valid_ms = 0.0
        self._prof_resolve_ms = 0.0
        self._prof_update_ms = 0.0
        self._prof_physics_ms = 0.0
        self._prof_cpu_ms = 0.0
        self._prof_total_ms = 0.0
    
    def get_profile_stats(self):
        return {
            "count": int(self._prof_count),
            "valid_ms": float(self._prof_valid_ms),
            "resolve_ms": float(self._prof_resolve_ms),
            "update_ms": float(self._prof_update_ms),
            "physics_ms": float(self._prof_physics_ms),
            "cpu_ms": float(self._prof_cpu_ms),
            "total_ms": float(self._prof_total_ms),
        }

    def register_bit_token_names(self, names: Dict[int, str]):
        """Register BIT token names for escalation reporting.

        Args:
            names: Dict mapping local_id -> token name string
        """
        self._bit_token_names = names

    def get_escalation_report(self) -> Dict[str, int]:
        """Get tokens that have overflowed BIT bounds and need BYTE escalation.

        Returns:
            Dict mapping token name -> overflow count
        """
        report = {}
        for local_id, count in self._bit_overflow_counts.items():
            name = self._bit_token_names.get(local_id, f"bit_{local_id}")
            report[name] = count
        return report

    def reset_escalation_stats(self):
        """Clear escalation tracking counters."""
        self._bit_overflow_counts.clear()
        self._escalation_step_counter = 0

    def _check_bit_escalation(self):
        """Check if any BIT values were clamped (indicating accumulation need).

        This is called periodically (every N steps) to detect tokens that
        should be BYTE instead of BIT. The overhead is minimal when called
        infrequently.

        The check looks at the _pre_clamp_bit_overflow set populated during
        _apply_updates, which tracks tokens that actually had values > 1 or < -1
        before clamping (not just tokens that happen to be at boundary values).
        """
        overflow_set = getattr(self, '_pre_clamp_bit_overflow', set())
        if overflow_set:
            for idx in overflow_set:
                self._bit_overflow_counts[idx] = self._bit_overflow_counts.get(idx, 0) + 1
            # Clear for next interval
            self._pre_clamp_bit_overflow = set()

    def set_rule_biases(self, biases: torch.Tensor | None):
        # Sets static component (e.g., ♥ID_*)
        if biases is None:
            self.rule_biases_static = torch.zeros(self.num_rules, dtype=torch.float32, device=self.device)
        else:
            b = biases.to(self.device).float()
            if b.shape[-1] != self.num_rules:
                raise ValueError("rule_biases length must equal num_rules")
            self.rule_biases_static = b

    def set_advantage_biases(self, advantages: torch.Tensor | None):
        """
        Set per-universe, per-rule advantage biases for value-guided selection.

        These are added to the scaled logits during rule selection, allowing
        the value network to guide rule choices based on estimated advantages.

        Args:
            advantages: [Batch, Rules] tensor of advantage estimates, or None to disable.
                        Positive values increase probability of selecting a rule,
                        negative values decrease it.
        """
        if advantages is None:
            self._advantage_biases = None
        else:
            a = advantages.to(self.device).float()
            if a.ndim == 1:
                # Broadcast [Rules] to [Batch, Rules]
                a = a.unsqueeze(0).expand(self.cfg.batch_size, -1)
            if a.shape != (self.cfg.batch_size, self.num_rules):
                raise ValueError(f"advantage_biases shape must be [batch_size={self.cfg.batch_size}, num_rules={self.num_rules}], got {a.shape}")
            self._advantage_biases = a

    def clear_advantage_biases(self):
        """Clear advantage biases (revert to bias-only selection)."""
        self._advantage_biases = None

    def compute_choice_stats(self, collapse_same_base: bool = True) -> dict:
        """
        Peek at current frame's valid choices after strict-priority masking,
        without applying updates. Returns per-universe choice counts and whether
        any universe has a decision point (either multiple independent bases or
        a mutex group with >1 valid branches).
        """
        with torch.no_grad():
            fast = os.environ.get("ENGINE_DECISION_STATS_FAST", "1") == "1"
            valid = self._check_validity()
            prior_valid, max_prio = self._apply_priority_and_guides(valid)
            # Expose for tracing
            self.last_prior_valid = prior_valid.detach()
            counts = prior_valid.sum(dim=1)  # [B]
            eff_counts = counts.clone()
            if fast:
                # Fast path: skip base collapsing; only determine any_decision
                any_multi = bool((eff_counts > 1).any().item())
                # Check mutex groups quickly if needed
                if not any_multi:
                    mutex_ids = self.rule_meta[:, 2].long()
                    is_mutex = (mutex_ids != 0)
                    any_mutex_multi = False
                    if is_mutex.any():
                        unique_groups = torch.unique(mutex_ids[is_mutex])
                        pv = prior_valid  # [B, R]
                        for gid in unique_groups.tolist():
                            mask = (mutex_ids == gid).unsqueeze(0)
                            grp_counts = (pv & mask).sum(dim=1)
                            if (grp_counts > 1).any():
                                any_mutex_multi = True
                                break
                        any_decision = any_multi or any_mutex_multi
                    else:
                        any_decision = any_multi
                else:
                    any_decision = True
                return {
                    "prior_valid": prior_valid,
                    "counts": counts,
                    "effective_counts": eff_counts,
                    "max_priority": max_prio,
                    "any_multi": any_multi,
                    "any_decision": any_decision,
                }
            # Optionally collapse branches of the same CSV base rule into one choice
            if collapse_same_base and isinstance(self.rule_ids, list) and len(self.rule_ids) == self.num_rules:
                rows = torch.nonzero(counts > 1, as_tuple=False).squeeze(1).tolist()
                # Build base list once
                rule_ids_list = list(self.rule_ids)
                bases: list[str] = [ (rid.split("#")[0] if isinstance(rid, str) else "") for rid in rule_ids_list ]
                for r in rows:
                    idxs = torch.nonzero(prior_valid[r], as_tuple=False).squeeze(1).tolist()
                    if not idxs:
                        continue
                    seen = set()
                    for i in idxs:
                        b = bases[i] if i < len(bases) else ""
                        seen.add(b)
                    eff_counts[r] = len(seen)
            # Detect mutex groups with >1 valid branches (decision even if same base)
            mutex_ids = self.rule_meta[:, 2].long()
            is_mutex = (mutex_ids != 0)
            any_mutex_multi = False
            if is_mutex.any():
                unique_groups = torch.unique(mutex_ids[is_mutex])
                # For each group, count valid options per row
                pv = prior_valid  # [B, R]
                for gid in unique_groups.tolist():
                    mask = (mutex_ids == gid).unsqueeze(0)  # [1, R]
                    # number of valid rules within this mutex group per row
                    grp_counts = (pv & mask).sum(dim=1)
                    if (grp_counts > 1).any():
                        any_mutex_multi = True
                        break
            any_multi = bool((eff_counts > 1).any().item())
            any_decision = any_multi or bool(any_mutex_multi)
            return {
                "prior_valid": prior_valid,
                "counts": counts,
                "effective_counts": eff_counts,
                "max_priority": max_prio,
                "any_multi": any_multi,
                "any_decision": any_decision,
            }
    
    def _ensure_oneshot_map(self):
        if self._oneshot_ready:
            return
        if not isinstance(self.rule_ids, list) or len(self.rule_ids) != self.num_rules:
            return
        if not self._oneshot_bases:
            self._oneshot_ready = True
            return
        rid_list = list(self.rule_ids) if isinstance(self.rule_ids, list) else []
        if not rid_list:
            self._oneshot_ready = True
            return
        bases = [rid.split("#")[0] if isinstance(rid, str) else "" for rid in rid_list]
        for idx, b in enumerate(bases):
            if b in self._oneshot_bases:
                self._oneshot_rule_indices.append(idx)
        # Initialize fired masks per tracked rule
        for idx in self._oneshot_rule_indices:
            self._oneshot_fired[idx] = torch.zeros((self.cfg.batch_size,), dtype=torch.bool, device=self.device)
        self._oneshot_ready = True
    
    def _mask_oneshot_prior(self, prior_valid: torch.Tensor):
        if not self._oneshot_ready or not self._oneshot_rule_indices:
            return
        for idx in self._oneshot_rule_indices:
            fired_rows = self._oneshot_fired.get(idx, None)
            if fired_rows is None:
                continue
            if fired_rows.any():
                prior_valid[fired_rows, idx] = False
    
    def _update_oneshot_fired(self, fired_mask: torch.Tensor):
        if not self._oneshot_ready or not self._oneshot_rule_indices:
            return
        for idx in self._oneshot_rule_indices:
            fm = fired_mask[:, idx]
            if fm.any():
                self._oneshot_fired[idx] |= fm
    
    def _apply_priority_and_guides(self, valid: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        # Strict priority masking to per-universe max
        priorities = self.rule_meta[:, 0].to(self.device)  # [Rules]
        max_prio = (valid.float() * priorities.unsqueeze(0)).amax(dim=1)  # [B]
        prio_mask = (priorities.unsqueeze(0) == max_prio.unsqueeze(1))  # [B, R]
        prior_valid = valid & prio_mask
        # Reachability guide (safe)
        if self.reachability_guide_mask is not None:
            any_valid_per_rule = prior_valid.any(dim=0)  # [R]
            mask_rules = self.reachability_guide_mask & (~any_valid_per_rule)
            if mask_rules.any():
                prior_valid[:, mask_rules] = False
        # One-shot: disable tracked bases after first fire per universe
        self._ensure_oneshot_map()
        self._mask_oneshot_prior(prior_valid)
        return prior_valid, max_prio

    def set_reachability_guide_mask(self, mask: torch.Tensor | None):
        """Set per-rule guidance mask. True means 'unreachable within K' proposal.
        Safe application occurs in conflict resolution only when the rule is invalid across all universes.
        """
        if mask is None:
            self.reachability_guide_mask = None
            return
        m = mask.to(self.device)
        if m.dtype != torch.bool:
            m = m.bool()
        if m.numel() != self.num_rules:
            raise ValueError("guide mask length must equal num_rules")
        self.reachability_guide_mask = m

    def reset_policy_dyn(self):
        self.rule_biases_dyn = torch.zeros(self.num_rules, dtype=torch.float32, device=self.device)

    def apply_token_desires(self, desires_per_block: dict, gain: float = 1.0):
        # desires_per_block: {BlockType: 1D tensor [tokens_in_block] of log-desires}
        total = torch.zeros(self.num_rules, dtype=torch.float32, device=self.device)
        for bt, k in self.gpu_blocks.items():
            if k is None:
                continue
            logd = desires_per_block.get(bt)
            if logd is None:
                continue
            logd = logd.to(self.device).float()
            outv = torch.zeros_like(total)
            inv = torch.zeros_like(total)
            if k.get("out_mean") and k["out_mean"]["mat"] is not None:
                outv = torch.sparse.mm(k["out_mean"]["mat"], logd.unsqueeze(1)).squeeze(1)
            if k.get("in") and k["in"]["mat"] is not None:
                inv = torch.sparse.mm(k["in"]["mat"], logd.unsqueeze(1)).squeeze(1)
            total = total + (outv - inv)
        self.rule_biases_dyn = total * float(gain)

    def register_cpu_callback(self, rule_idx: int, callback):
        self.cpu_callbacks[rule_idx] = callback

    def _init_memory(self):
        bs = self.cfg.batch_size
        sizes = self.kernel.block_sizes
        
        # Block 0: BIT (Dual-Rail Flags: -1, 0, 1)
        self.state[BlockType.BIT] = torch.zeros(
            (bs, sizes[BlockType.BIT]), dtype=torch.int8, device=self.device
        )
        
        # Block 1: BYTE (Inventory: 0-255)
        # Stored as int16 during step to catch overflow, clamped at end
        self.state[BlockType.BYTE] = torch.zeros(
            (bs, sizes[BlockType.BYTE]), dtype=torch.int16, device=self.device
        )
        
        # Block 2: FLOAT (Physics: Continuous)
        self.state[BlockType.FLOAT] = torch.zeros(
            (bs, sizes[BlockType.FLOAT]), dtype=torch.float32, device=self.device
        )

    def _upload_kernels(self):
        self.gpu_blocks = {}
        
        for bt, block_kernel in self.kernel.blocks.items():
            # Helper: Upload sparse tensor
            def upload(data, val_dtype: torch.dtype = torch.float32):
                if data is None:
                    return None
                if not data.indices: return None
                i = torch.tensor(data.indices, dtype=torch.long, device=self.device)
                v = torch.tensor(data.values, dtype=val_dtype, device=self.device)
                # Note: We keep indices/values separate for custom kernels (Validity)
                # We also create the coalesced sparse tensor for MM
                sparse = torch.sparse_coo_tensor(i, v, data.shape, device=self.device).coalesce()
                return {"indices": i, "values": v, "mat": sparse}

            # Choose dtype for values (optional mixed precision on FLOAT block)
            use_mixed = os.environ.get("FLOAT_MIXED", "1") == "1"
            def val_dtype_for(key: str) -> torch.dtype:
                # IMPORTANT: PyTorch sparse.mm on CUDA does not support Half for sparse tensors.
                # Keep all sparse matrices in float32 to avoid "addmm_sparse_cuda not implemented for 'Half'".
                return torch.float32

            # Build per-row slices (rule -> token indices, values) for fast single-action updates
            def build_row_slices(data):
                if data is None or not getattr(data, "values", None):
                    return None
                num_rows = data.shape[0] if data.shape and len(data.shape) == 2 else int(self.kernel.num_rules)
                rows_idx = [None] * num_rows
                rows_val = [None] * num_rows
                # Build buckets on CPU lists, then move to device
                buckets = {}
                for r, c, v in zip(data.indices[0], data.indices[1], data.values):
                    rr = int(r); cc = int(c)
                    if rr not in buckets:
                        buckets[rr] = ([], [])
                    buckets[rr][0].append(cc)
                    buckets[rr][1].append(float(v))
                for r in range(num_rows):
                    if r in buckets:
                        cols, vals = buckets[r]
                        rows_idx[r] = torch.tensor(cols, dtype=torch.long, device=self.device)
                        # Always keep row values in float32 for accumulation stability
                        rows_val[r] = torch.tensor(vals, dtype=torch.float32, device=self.device)
                    else:
                        rows_idx[r] = torch.empty((0,), dtype=torch.long, device=self.device)
                        rows_val[r] = torch.empty((0,), dtype=torch.float32, device=self.device)
                return {"idx": rows_idx, "val": rows_val}

            self.gpu_blocks[bt] = {
                "in": upload(block_kernel.inputs, torch.float32),
                "out_mean": upload(block_kernel.outputs, val_dtype_for("out_mean")), # Renamed from 'out'
                # Assuming Compiler now provides out_std for ranges
                "out_std": upload(getattr(block_kernel, "outputs_std", None), val_dtype_for("out_std")), 
                "out_net": upload(getattr(block_kernel, "outputs_net", None), val_dtype_for("out_net")),
                "out_range_lo": upload(getattr(block_kernel, "outputs_range_lo", None), torch.float32),
                "out_range_hi": upload(getattr(block_kernel, "outputs_range_hi", None), torch.float32),
                "ban": upload(block_kernel.inhibitors, torch.float32),
                "unit_map": block_kernel.unit_map.to(self.device) if block_kernel.unit_map is not None else None,
                "thresholds": block_kernel.overflow_thresholds.to(self.device) if getattr(block_kernel, "overflow_thresholds", None) is not None else None,
                "all": upload(getattr(block_kernel, "consume_all", None), torch.float32),
                # Row-slice caches for single-action fast path
                "out_net_rows": build_row_slices(getattr(block_kernel, "outputs_net", None)),
                "out_std_rows": build_row_slices(getattr(block_kernel, "outputs_std", None)),
                "out_range_rows_lo": build_row_slices(getattr(block_kernel, "outputs_range_lo", None)),
                "out_range_rows_hi": build_row_slices(getattr(block_kernel, "outputs_range_hi", None)),
                "all_rows": build_row_slices(getattr(block_kernel, "consume_all", None)),
            }
            
        # Rule Meta: [Priority, Probability, MutexID, CPU_Flag]
        self.rule_meta = self.kernel.rule_meta.to(self.device)
        self.num_rules = self.kernel.num_rules
        # Precompute constant logits from base probabilities for fast resolve
        try:
            eps = 1e-9
            base_probs = self.rule_meta[:, 1]
            self._logits_const = torch.log(base_probs + eps) - torch.log(1.0 - base_probs + eps)
        except Exception:
            self._logits_const = torch.zeros((self.num_rules,), dtype=torch.float32, device=self.device)

    def step(self):
        """
        The Heartbeat.
        """
        if self._prof_enable:
            if self.device.type == "cuda":
                e0 = torch.cuda.Event(enable_timing=True); e1 = torch.cuda.Event(enable_timing=True)
                e2 = torch.cuda.Event(enable_timing=True); e3 = torch.cuda.Event(enable_timing=True)
                e4 = torch.cuda.Event(enable_timing=True); e5 = torch.cuda.Event(enable_timing=True)
                torch.cuda.synchronize()
                e0.record()
            else:
                import time as _t
                _t0 = _t.perf_counter()
        # 1. Validity: Strict Requirement Checking
        valid_mask = self._check_validity()
        if self._prof_enable:
            if self.device.type == "cuda":
                e1.record(); torch.cuda.synchronize()
                self._prof_valid_ms += float(e0.elapsed_time(e1))
            else:
                import time as _t
                _t1 = _t.perf_counter(); self._prof_valid_ms += (_t1 - _t0) * 1000.0; _t0 = _t1
        # 2. Conflict Resolution: Priority & Mutex
        fired_mask = self._resolve_conflicts(valid_mask)
        if self._prof_enable:
            if self.device.type == "cuda":
                e2.record(); torch.cuda.synchronize()
                self._prof_resolve_ms += float(e1.elapsed_time(e2))
            else:
                import time as _t
                _t2 = _t.perf_counter(); self._prof_resolve_ms += (_t2 - _t0) * 1000.0; _t0 = _t2
        # 3. Updates: Apply Deltas & Variance
        self._apply_updates(fired_mask)
        # Keep last fired mask for tracing/diagnostics
        self.last_fired_mask = fired_mask
        if self._prof_enable:
            if self.device.type == "cuda":
                e3.record(); torch.cuda.synchronize()
                self._prof_update_ms += float(e2.elapsed_time(e3))
            else:
                import time as _t
                _t3 = _t.perf_counter(); self._prof_update_ms += (_t3 - _t0) * 1000.0; _t0 = _t3
        # 4. Physics: Carry-Lookahead & Constraints
        self._resolve_physics()
        if self._prof_enable:
            if self.device.type == "cuda":
                e4.record(); torch.cuda.synchronize()
                self._prof_physics_ms += float(e3.elapsed_time(e4))
            else:
                import time as _t
                _t4 = _t.perf_counter(); self._prof_physics_ms += (_t4 - _t0) * 1000.0; _t0 = _t4
        # 5. CPU Valve
        if self.cfg.enable_cpu_offload:
            if self._prof_enable:
                if self.device.type == "cuda":
                    # CPU callbacks are on host; measure wall time
                    import time as _t
                    _h0 = _t.perf_counter()
                    self._handle_cpu_callbacks(fired_mask)
                    _h1 = _t.perf_counter()
                    self._prof_cpu_ms += (_h1 - _h0) * 1000.0
                else:
                    import time as _t
                    _h0 = _t.perf_counter()
                    self._handle_cpu_callbacks(fired_mask)
                    _h1 = _t.perf_counter()
                    self._prof_cpu_ms += (_h1 - _h0) * 1000.0
            else:
                self._handle_cpu_callbacks(fired_mask)
        if self._prof_enable:
            if self.device.type == "cuda":
                e5.record(); torch.cuda.synchronize()
                self._prof_total_ms += float(e0.elapsed_time(e5))
            else:
                import time as _t
                _t5 = _t.perf_counter(); self._prof_total_ms += (_t5 - _t0) * 1000.0
            self._prof_count += 1

        # 6. Periodic BIT escalation check (every N steps, ~0% overhead)
        self._escalation_step_counter += 1
        if self._escalation_check_interval > 0 and self._escalation_step_counter >= self._escalation_check_interval:
            self._escalation_step_counter = 0
            self._check_bit_escalation()

    def _check_validity(self) -> torch.Tensor:
        """
        Check inputs per-token, not per-sum.
        Returns: [Batch, Num_Rules] boolean.
        """
        bs = self.cfg.batch_size
        # Start with all True
        validity = torch.ones((bs, self.num_rules), dtype=torch.bool, device=self.device)
        do_debug = os.environ.get("ENGINE_DUMP_VALID", "0") == "1"
        debug_base = os.environ.get("ENGINE_DEBUG_RULE_BASE", "ID_Start")
        debug_info: dict[str, dict] = {} if do_debug else None
        
        for bt in BlockType:
            state = self.state[bt]
            k = self.gpu_blocks[bt]
            
            # Input Requirements
            if k["in"]:
                # 1. Gather State values relevant to requirements
                # indices[0] = RuleID, indices[1] = TokenID
                rule_idx, token_idx = k["in"]["indices"]
                req_vals = k["in"]["values"]
                
                # Gather state: [Batch, NNZ]
                # We pick the specific tokens needed by the rules
                current_vals = state[:, token_idx] 
                
                # Calculate Deficit [Batch, NNZ]
                deficit = F.relu(req_vals.unsqueeze(0) - current_vals.float())
                
                # Sum Deficits per Rule
                index_batch = rule_idx.unsqueeze(0).expand(bs, -1)
                
                rule_deficits = torch.zeros((bs, self.num_rules), device=self.device)
                rule_deficits.scatter_add_((1), index_batch, deficit)
                
                validity &= (rule_deficits == 0)
                if do_debug and isinstance(self.rule_ids, list) and len(self.rule_ids) == self.num_rules:
                    # Summarize for selected rule base
                    try:
                        base_indices = [i for i, rid in enumerate(self.rule_ids) if isinstance(rid, str) and rid.split("#")[0] == debug_base]
                        if base_indices:
                            ridx = torch.tensor(base_indices, dtype=torch.long, device=self.device)
                            # Per-row total deficits across selected rules
                            sel_def = rule_deficits[:, ridx]
                            per_row_min = float(sel_def.min().item())
                            per_row_mean = float(sel_def.mean().item())
                            rows_ok = int((sel_def == 0).all(dim=1).sum().item())
                            # Identify input tokens used by selected rules in this block
                            sel_mask = torch.zeros_like(rule_idx, dtype=torch.bool)
                            for r in base_indices:
                                sel_mask |= (rule_idx == r)
                            used_tokens = token_idx[sel_mask]
                            uniq_tokens = torch.unique(used_tokens)
                            # Compute mean presence for these tokens (aggregate)
                            pres_mean = 0.0
                            if uniq_tokens.numel() > 0:
                                pres_mean = float(state[:, uniq_tokens].float().mean().item())
                            debug_info[bt.name] = {"rows_ok": rows_ok, "per_row_min_def": per_row_min, "per_row_mean_def": per_row_mean, "inputs_present_mean": pres_mean, "num_inputs": int(uniq_tokens.numel())}
                    except Exception:
                        pass

            # Inhibitors (Must be 0)
            if k["ban"]:
                # Project State onto Bans
                # Any presence > 0 triggers ban
                presence = torch.sparse.mm(k["ban"]["mat"], state.float().t()).t()
                validity &= (presence == 0)
                
        if do_debug and debug_info:
            try:
                print(f"[ENGINE] validity debug for base='{debug_base}': {debug_info}")
            except Exception:
                pass
        return validity

    def _resolve_conflicts(self, valid: torch.Tensor) -> torch.Tensor:
        bs = self.cfg.batch_size
        
        # 1. Base Probability Check (with Temperature scaling via logits and optional biases)
        eps = 1e-9
        logits = getattr(self, "_logits_const", None)
        if logits is None or logits.numel() != self.num_rules:
            # Fallback if not precomputed
            base_probs = self.rule_meta[:, 1]  # [Rules]
            logits = torch.log(base_probs + eps) - torch.log(1.0 - base_probs + eps)
        bias_static = self.rule_biases_static if self.rule_biases_static is not None else 0.0
        bias_dyn = self.rule_biases_dyn if self.rule_biases_dyn is not None else 0.0
        bias = bias_static + bias_dyn
        scaled_logits = (logits + bias) / max(self.cfg.temperature, eps)
        # Store for tracing
        self.last_scaled_logits = scaled_logits.detach()
        no_gumbel = os.environ.get("RESOLVE_NO_GUMBEL", "0") == "1"
        
        # 1b. Strict priority + guides + oneshot
        prior_valid, max_prio = self._apply_priority_and_guides(valid)
        # Store for tracing
        self.last_prior_valid = prior_valid.detach()
        
        if self.cfg.enable_priority_logging:
            tie_counts = prior_valid.sum(dim=1)
            num_ties = int((tie_counts > 1).sum().item())
            if num_ties > 0:
                self.priority_tie_events += num_ties
                # Append to logfile with per-row samples
                try:
                    path = self.cfg.priority_log_path if getattr(self.cfg, "priority_log_path", "") else "priority_ties.log"
                    with open(path, "a", encoding="utf-8") as f:
                        collapsed = 0
                        if len(self.priority_tie_samples) < self.cfg.priority_log_limit:
                            rows = torch.nonzero(tie_counts > 1, as_tuple=False).squeeze(1)[: (self.cfg.priority_log_limit - len(self.priority_tie_samples))]
                            for r in rows.tolist():
                                idxs = torch.nonzero(prior_valid[r], as_tuple=False).squeeze(1).tolist()
                                # Collapse by CSV ID base (split at '#') when available
                                if isinstance(self.rule_ids, list) and len(self.rule_ids) == self.num_rules:
                                    _rid_list = list(self.rule_ids)
                                    names = [_rid_list[i] for i in idxs]
                                else:
                                    names = None
                                if names:
                                    bases = [n.split('#')[0] for n in names]
                                    unique_bases = sorted(set(bases))
                                    # Skip if all belong to the same base (these are one-of branches of the same rule)
                                    if len(unique_bases) <= 1:
                                        collapsed += 1
                                        if not self.cfg.log_same_base_ties:
                                            continue
                                    # Group indices per base for clarity
                                    base_to_idxs = {}
                                    for i, b in zip(idxs, bases):
                                        base_to_idxs.setdefault(b, []).append(i)
                                    pr = int(max_prio[r].item())
                                    f.write(f" row={r} max_prio={pr} bases={unique_bases} groups={base_to_idxs}\n")
                                else:
                                    # No IDs available; log raw indices
                                    pr = int(max_prio[r].item())
                                    self.priority_tie_samples.append(idxs)
                                    f.write(f" row={r} max_prio={pr} rules={idxs}\n")
                        # Write aggregate only if actionable ties exist, or if explicitly logging same-base ties
                        if self.cfg.log_same_base_ties or (num_ties - collapsed) > 0:
                            f.write(f"ties={num_ties} max_prio_mean={max_prio.mean().item():.3f} collapsed_rows={collapsed}\n")
                except Exception:
                    pass
        
        # If configured, pick a single action (one rule per universe) using global Gumbel-Max
        if getattr(self.cfg, "single_action_mode", False):
            # Scores: scaled logits + gumbel
            base_group_logits = scaled_logits.unsqueeze(0).expand(bs, -1)
            # Inject per-universe advantage biases from value network (if set)
            if self._advantage_biases is not None:
                base_group_logits = base_group_logits + self._advantage_biases
            if no_gumbel:
                gumbel = 0.0
            else:
                gumbel = -torch.log(-torch.log(torch.rand_like(base_group_logits)))
            scores = base_group_logits + gumbel
            # Mask out invalid/prior-invalid
            scores = scores.masked_fill(~prior_valid, -float('inf'))
            # Choose best per universe
            best_idx = scores.argmax(dim=1)
            has_any = prior_valid.any(dim=1)
            fired_mask = torch.zeros_like(valid)
            rows = torch.arange(bs, device=self.device)
            fired_mask[rows[has_any], best_idx[has_any]] = True
            self.last_choice = best_idx.detach()
            # update oneshot state
            self._update_oneshot_fired(fired_mask)
            return fired_mask

        # 2. Handle Mutual Exclusion (One-Of) with possible multiple independent rules
        # MutexID is in Col 2. 0 means "Independent".
        mutex_ids = self.rule_meta[:, 2].long()
        
        # Mask of rules that are part of a mutex group
        is_mutex = (mutex_ids != 0)
        
        # Independent Rules: Just roll dice (only used in non-single-action mode)
        probs = torch.sigmoid(scaled_logits).unsqueeze(0).expand(bs, -1)
        rand = torch.rand_like(probs)
        independent_fired = prior_valid & (rand < probs) & (~is_mutex.unsqueeze(0))
        
        # Mutex Rules: Gumbel-Max (on temperature-scaled logits)
        mutex_fired = torch.zeros_like(valid)
        unique_groups = torch.tensor([], device=self.device, dtype=mutex_ids.dtype)
        if is_mutex.any():
            unique_groups = torch.unique(mutex_ids)
            # Exclude 0 (non-mutex)
            unique_groups = unique_groups[unique_groups != 0]
        
        # Prepare scores for mutex via Gumbel-Max on log-probabilities
        
        for gid in unique_groups:
            # Mask for this group
            group_mask = (mutex_ids == gid).unsqueeze(0) # [1, Rules]
            
            # Filter valid rules in this group
            # [Batch, Rules]
            group_valid = prior_valid & group_mask
            
            # If no rules in the group are valid for a universe, none fire.
            # Calculate Scores: Scaled Logits + Gumbel
            # Add -1e9 to invalid rules to prevent selection
            
            # Convert scaled logits (with bias/temperature) to probabilities, then to log-probabilities
            base_probs = torch.sigmoid(scaled_logits).clamp_min(eps)
            base_group_logp = torch.log(base_probs).unsqueeze(0).expand(bs, -1)
            # Inject per-universe advantage biases from value network (if set)
            if self._advantage_biases is not None:
                base_group_logp = base_group_logp + self._advantage_biases
            if no_gumbel:
                gumbel = 0.0
            else:
                gumbel = -torch.log(-torch.log(torch.rand_like(base_group_logp)))
            scores = base_group_logp + gumbel
            # Mask out invalid
            scores = scores.masked_fill(~group_valid, -float('inf'))
            # Mask out non-group
            scores = scores.masked_fill(~group_mask, -float('inf'))
            
            # Check if ANY rule is valid in the group
            has_valid = group_valid.any(dim=1)
            
            best_idx = scores.argmax(dim=1) # [Batch] indices
            
            # Set fired
            rows = torch.arange(bs, device=self.device)
            cols = best_idx
            
            # Only fire if at least one option was valid
            real_fire_mask = has_valid
            
            mutex_fired[rows[real_fire_mask], cols[real_fire_mask]] = True
        
        fired_out = independent_fired | mutex_fired
        # update oneshot state
        self._update_oneshot_fired(fired_out)
        return fired_out

    def get_priority_tie_stats(self):
        return {"events": self.priority_tie_events, "samples": self.priority_tie_samples}
      
    
    def _apply_updates(self, fired: torch.Tensor):
        """
        State += Fired @ Delta
        """
        fired_f = fired.float()

        for bt in BlockType:
            k = self.gpu_blocks[bt]
            if not k["out_mean"]: continue

            # Fast path: single-action row-slice updates if row caches exist
            use_rows = getattr(self.cfg, "single_action_mode", False) and (k.get("out_net_rows") is not None)
            if use_rows:
                # Guard: if too many distinct rules selected this step, fall back to spmm path
                cfg_limit = getattr(self.cfg, "row_slice_max_uniques", None)
                if isinstance(cfg_limit, int) and cfg_limit >= 0:
                    max_uniques = cfg_limit
                else:
                    try:
                        max_uniques = int(os.environ.get("ROW_SLICE_MAX_UNIQUES", "256"))
                    except Exception:
                        max_uniques = 256
                # Build row->rule mapping once (single-action => at most one fired per row)
                fired_any = fired.any(dim=1)
                if fired_any.any():
                    rows_all = torch.nonzero(fired_any, as_tuple=False).squeeze(1)
                    # For these rows, get the fired rule index
                    rule_for_row = torch.argmax(fired[rows_all].to(torch.int64), dim=1)
                    # Sort rows by rule to form contiguous buckets
                    order = torch.argsort(rule_for_row)
                    rows_sorted = rows_all[order]
                    rules_sorted = rule_for_row[order]
                    # Unique rules and their run-lengths
                    unique_rules, counts = torch.unique_consecutive(rules_sorted, return_counts=True)
                else:
                    unique_rules = torch.empty((0,), dtype=torch.long, device=self.device)
                    counts = torch.empty((0,), dtype=torch.long, device=self.device)
                    rows_sorted = torch.empty((0,), dtype=torch.long, device=self.device)
                if unique_rules.numel() > max_uniques:
                    use_rows = False
                if use_rows:
                    # Work on a float view
                    state_block = self.state[bt].float()
                    tokens_in_block = int(state_block.shape[1])
                    # Snapshot pre-update state for consume_all semantics
                    state_before = state_block
                    # Accumulate flattened indices and deltas
                    lin_idx_parts: list[torch.Tensor] = []
                    delta_parts: list[torch.Tensor] = []
                    start = 0
                    for urule, cnt in zip(unique_rules.tolist(), counts.tolist()):
                        end = start + cnt
                        rows = rows_sorted[start:end]
                        start = end
                        if rows.numel() == 0:
                            continue
                        # Deterministic net deltas
                        cols = k["out_net_rows"]["idx"][urule]
                        vals = k["out_net_rows"]["val"][urule]
                        if cols.numel() > 0:
                            rr = rows.view(-1, 1).expand(-1, cols.numel()).reshape(-1)
                            cc = cols.view(1, -1).expand(rows.size(0), -1).reshape(-1)
                            lin = rr * tokens_in_block + cc
                            dv = vals.view(1, -1).expand(rows.size(0), -1).reshape(-1).to(torch.float32)
                            lin_idx_parts.append(lin)
                            delta_parts.append(dv)
                        # Discrete range adjust (integer-uniform in [lo, hi], subtract mean)
                        lo_src = k.get("out_range_rows_lo")
                        hi_src = k.get("out_range_rows_hi")
                        if lo_src is not None and hi_src is not None:
                            rcols_lo = lo_src["idx"][urule]
                            rvals_lo = lo_src["val"][urule]
                            rcols_hi = hi_src["idx"][urule]
                            rvals_hi = hi_src["val"][urule]
                            if rcols_lo.numel() > 0 and rcols_hi.numel() == rcols_lo.numel():
                                # Compute inclusive widths per column
                                lo = rvals_lo.float()
                                hi = rvals_hi.float()
                                width = (hi - lo + 1.0).clamp(min=1.0)
                                # Sample integers: lo + floor(rand * width)
                                rand = torch.rand((rows.size(0), rcols_lo.numel()), device=self.device, dtype=torch.float32)
                                samp = lo.unsqueeze(0) + torch.floor(rand * width.unsqueeze(0))
                                # Mean = (lo + hi)/2
                                mean = (lo + hi) * 0.5
                                adj = (samp - mean.unsqueeze(0)).reshape(-1).to(torch.float32)
                                rr = rows.view(-1, 1).expand(-1, rcols_lo.numel()).reshape(-1)
                                cc = rcols_lo.view(1, -1).expand(rows.size(0), -1).reshape(-1)
                                lin = rr * tokens_in_block + cc
                                lin_idx_parts.append(lin)
                                delta_parts.append(adj)
                        # Variance (if enabled)
                        if k.get("out_std_rows") is not None and float(self.cfg.temperature) > 0.0:
                            s_cols = k["out_std_rows"]["idx"][urule]
                            s_vals = k["out_std_rows"]["val"][urule]
                            if s_cols is not None and s_cols.numel() > 0:
                                noise = torch.randn((rows.size(0), s_cols.numel()), device=self.device, dtype=torch.float32)
                                dv = (noise * s_vals.view(1, -1) * float(self.cfg.temperature)).reshape(-1)
                                rr = rows.view(-1, 1).expand(-1, s_cols.numel()).reshape(-1)
                                cc = s_cols.view(1, -1).expand(rows.size(0), -1).reshape(-1)
                                lin = rr * tokens_in_block + cc
                                lin_idx_parts.append(lin)
                                delta_parts.append(dv)
                        # Consume-all: subtract old values for marked columns
                        if k.get("all_rows") is not None:
                            a_cols = k["all_rows"]["idx"][urule]
                            if a_cols is not None and a_cols.numel() > 0:
                                # Gather old values
                                old_vals = state_before.index_select(0, rows)[:, a_cols].reshape(-1)
                                rr = rows.view(-1, 1).expand(-1, a_cols.numel()).reshape(-1)
                                cc = a_cols.view(1, -1).expand(rows.size(0), -1).reshape(-1)
                                lin = rr * tokens_in_block + cc
                                lin_idx_parts.append(lin)
                                delta_parts.append(-old_vals)
                    if lin_idx_parts:
                        lin_all = torch.cat(lin_idx_parts)
                        dv_all = torch.cat(delta_parts).to(torch.float32)
                        flat = state_block.view(-1)
                        flat.index_add_(0, lin_all, dv_all)
                        state_block = flat.view_as(state_block)
                    # Apply clamps/casts
                    if bt == BlockType.BYTE:
                        state_block = torch.clamp(state_block, min=0)
                        self.state[BlockType.BYTE] = state_block.to(torch.int16)
                    elif bt == BlockType.BIT:
                        # Detect overflow before clamping (for escalation tracking)
                        if self._escalation_check_interval > 0:
                            overflow_mask = (state_block > 1) | (state_block < -1)
                            if overflow_mask.any():
                                # Find which token columns overflowed
                                overflow_cols = overflow_mask.any(dim=0)
                                if overflow_cols.any():
                                    if not hasattr(self, '_pre_clamp_bit_overflow'):
                                        self._pre_clamp_bit_overflow = set()
                                    for idx in torch.nonzero(overflow_cols, as_tuple=False).squeeze(1).tolist():
                                        self._pre_clamp_bit_overflow.add(idx)
                        self.state[bt] = torch.clamp(state_block, -1, 1).to(torch.int8)
                    else:
                        self.state[bt] = torch.clamp(state_block, min=0)
            else:
                # 1. Calculate Deterministic Delta (prefer fused net if available)
                if k.get("out_net") and k["out_net"] is not None:
                    net = torch.sparse.mm(k["out_net"]["mat"].t(), fired_f.t()).t()
                    # If using mixed precision on FLOAT block, cast to float32 before accumulation
                    if net.dtype != torch.float32:
                        net = net.float()
                    delta = net
                else:
                    produced = torch.sparse.mm(k["out_mean"]["mat"].t(), fired_f.t()).t()
                    consumed = torch.zeros_like(produced)
                    if k["in"]:
                        consumed = torch.sparse.mm(k["in"]["mat"].t(), fired_f.t()).t()
                    delta = produced - consumed
                
                # 2. Discrete range adjust for fired rows (fallback path)
                lo = k.get("out_range_lo")
                hi = k.get("out_range_hi")
                if lo is not None and hi is not None:
                    # Build flattened index_add adjustments
                    r_lo = lo["indices"]; v_lo = lo["values"].float()
                    r_hi = hi["indices"]; v_hi = hi["values"].float()
                    if len(r_lo) == 2 and len(r_hi) == 2 and len(v_lo) == len(v_hi):
                        # For each (rule, token) that has a range, find fired rows
                        rl = r_lo[0]; tl = r_lo[1]
                        rh = r_hi[0]; th = r_hi[1]
                        # Safety: ensure matching pairs
                        # For efficiency, assume compiler aligned entries in same order
                        widths = (v_hi - v_lo + 1.0).clamp(min=1.0)  # [NNZ]
                        means = (v_lo + v_hi) * 0.5  # [NNZ]
                        # For each rule index in rl, find rows where fired[:, rule] == 1
                        # We'll accumulate per (row, token) adjust into delta
                        B = fired.shape[0]
                        for idx_nnz in range(len(v_lo)):
                            r_id = int(rl[idx_nnz].item())
                            t_id = int(tl[idx_nnz].item())
                            rows = torch.nonzero(fired[:, r_id], as_tuple=False).squeeze(1)
                            if rows.numel() == 0:
                                continue
                            w = float(widths[idx_nnz].item())
                            lo_v = float(v_lo[idx_nnz].item())
                            mean_v = float(means[idx_nnz].item())
                            # Sample per row
                            rands = torch.rand((rows.numel(),), device=self.device, dtype=torch.float32)
                            samp = lo_v + torch.floor(rands * w)
                            adj = (samp - mean_v).to(torch.float32)
                            # Add into delta for token t_id on those rows
                            delta[rows, t_id] += adj

                # 3. Calculate Variance (Chaos Injection)
                if k["out_std"] and float(self.cfg.temperature) > 0.0:
                    # Get StdDev sum for fired rules
                    std_agg = torch.sparse.mm(k["out_std"]["mat"].t(), fired_f.t()).t()
                    if std_agg.dtype != torch.float32:
                        std_agg = std_agg.float()
                    noise = torch.randn_like(std_agg)
                    delta += (noise * std_agg * self.cfg.temperature)

                # 3b. Consume-All (reduce to zero) — subtract current value once if any such rule fired
                if k["all"] is not None:
                    counts = torch.sparse.mm(k["all"]["mat"].t(), fired_f.t()).t()
                    if counts.dtype != torch.float32:
                        counts = counts.float()
                    mask = (counts > 0).float()
                    current_state = self.state[bt].float()
                    delta -= (current_state * mask)
                
                # 4. Apply
                # Note: BIT/BYTE stored as int, but math is float. Cast back.
                current = self.state[bt].float()
                new_val = current + delta
                
                if bt == BlockType.BYTE:
                    # Keep in float/int16 for Physics phase
                    new_val = torch.clamp(new_val, min=0)
                    self.state[BlockType.BYTE] = new_val.to(torch.int16)
                elif bt == BlockType.BIT:
                    # Detect overflow before clamping (for escalation tracking)
                    if self._escalation_check_interval > 0:
                        overflow_mask = (new_val > 1) | (new_val < -1)
                        if overflow_mask.any():
                            # Find which token columns overflowed
                            overflow_cols = overflow_mask.any(dim=0)
                            if overflow_cols.any():
                                if not hasattr(self, '_pre_clamp_bit_overflow'):
                                    self._pre_clamp_bit_overflow = set()
                                for idx in torch.nonzero(overflow_cols, as_tuple=False).squeeze(1).tolist():
                                    self._pre_clamp_bit_overflow.add(idx)
                    # Clamp immediately
                    self.state[bt] = torch.clamp(new_val, -1, 1).to(torch.int8)
                else:
                    # FLOAT: prevent negative due to noise or updates
                    self.state[bt] = torch.clamp(new_val, min=0)

    def _resolve_physics(self):
        """
        Carry-Lookahead and Clamping.
        """
        # BYTE Overflow
        raw = self.state[BlockType.BYTE] # int16
        if raw.shape[1] == 0:
            return

        # 1. Identify Overflows using per-token thresholds if available
        gpub = self.gpu_blocks[BlockType.BYTE]
        thresholds = gpub.get("thresholds", None)
        if thresholds is None:
            # Default to 255 everywhere
            max_vals = torch.full((raw.shape[1],), 256, dtype=raw.dtype, device=self.device)
        else:
            # Threshold is maximum representable value; overflow when value >= threshold+1
            max_vals = (thresholds + 1).to(dtype=raw.dtype)
        # Avoid divide-by-zero just in case
        max_vals = torch.clamp(max_vals, min=1)

        # Broadcast to batch dimension
        max_vals_b = max_vals.unsqueeze(0).expand(raw.shape[0], -1)

        overflow_amt = raw // max_vals_b
        remainder = raw % max_vals_b
        
        # 2. Apply Carry
        # We need to add `overflow_amt` to the Parent tokens.
        # unit_map: [Num_Tokens] -> Parent_Index (or -1)
        unit_map = gpub["unit_map"]
        
        if unit_map is not None:
            # Identify tokens that have parents
            has_parent = (unit_map != -1)
            
            # Get the overflow amount for tokens that have parents
            # Shape: [Batch, Num_Tokens]
            valid_overflow = overflow_amt * has_parent.unsqueeze(0).to(dtype=overflow_amt.dtype)
            
            if valid_overflow.any():
                # Broadcast parent indices to batch
                parent_indices = unit_map.unsqueeze(0).expand(self.cfg.batch_size, -1)
                
                # Clamp index to 0 for invalid; zero value there
                safe_indices = parent_indices.clone()
                safe_indices[~has_parent] = 0
                
                # Add to state (accumulate in int16)
                self.state[BlockType.BYTE].scatter_add_(1, safe_indices, valid_overflow.to(self.state[BlockType.BYTE].dtype))
                
        # 3. Finalize Remainder
        self.state[BlockType.BYTE] = remainder.to(torch.uint8)

    def _handle_cpu_callbacks(self, fired_mask):
        # Execute registered Python callbacks for CPU-flagged rules where they fired.
        cpu_flags = (self.rule_meta[:, 3] > 0.5)  # [Rules]
        if not cpu_flags.any():
            return
        cpu_rule_indices = torch.nonzero(cpu_flags, as_tuple=False).squeeze(1)
        for r in cpu_rule_indices.tolist():
            cb = self.cpu_callbacks.get(r)
            if cb is None:
                continue
            rows = torch.nonzero(fired_mask[:, r], as_tuple=False).squeeze(1)
            if rows.numel() == 0:
                continue
            for b in rows.tolist():
                cb(self, b)
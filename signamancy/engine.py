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
    
    # Debug/logging
    enable_priority_logging: bool = False
    priority_log_limit: int = 50
    priority_log_path: str | None = None
    log_same_base_ties: bool = False

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
        self.rule_biases: torch.Tensor | None = None
        self.priority_tie_events: int = 0
        self.priority_tie_samples: list[list[int]] = []
        self.rule_ids: list[str] | None = None
        self.cpu_callbacks = {}
        self._init_memory()
        self._upload_kernels()
        # Initialize per-rule biases (default zeros = no effect)
        self.rule_biases = torch.zeros(self.num_rules, dtype=torch.float32, device=self.device)

    def set_rule_biases(self, biases: torch.Tensor | None):
        if biases is None:
            self.rule_biases = torch.zeros(self.num_rules, dtype=torch.float32, device=self.device)
        else:
            b = biases.to(self.device).float()
            if b.shape[-1] != self.num_rules:
                raise ValueError("rule_biases length must equal num_rules")
            self.rule_biases = b

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
            def upload(data):
                if data is None:
                    return None
                if not data.indices: return None
                i = torch.tensor(data.indices, dtype=torch.long, device=self.device)
                v = torch.tensor(data.values, dtype=torch.float32, device=self.device)
                # Note: We keep indices/values separate for custom kernels (Validity)
                # We also create the coalesced sparse tensor for MM
                sparse = torch.sparse_coo_tensor(i, v, data.shape, device=self.device)
                return {"indices": i, "values": v, "mat": sparse}

            self.gpu_blocks[bt] = {
                "in": upload(block_kernel.inputs),
                "out_mean": upload(block_kernel.outputs), # Renamed from 'out'
                # Assuming Compiler now provides out_std for ranges
                "out_std": upload(getattr(block_kernel, "outputs_std", None)), 
                "ban": upload(block_kernel.inhibitors),
                "unit_map": block_kernel.unit_map.to(self.device) if block_kernel.unit_map is not None else None,
                "thresholds": block_kernel.overflow_thresholds.to(self.device) if getattr(block_kernel, "overflow_thresholds", None) is not None else None,
                "all": upload(getattr(block_kernel, "consume_all", None)),
            }
            
        # Rule Meta: [Priority, Probability, MutexID, CPU_Flag]
        self.rule_meta = self.kernel.rule_meta.to(self.device)
        self.num_rules = self.kernel.num_rules

    def step(self):
        """
        The Heartbeat.
        """
        # 1. Validity: Strict Requirement Checking
        valid_mask = self._check_validity()
        
        # 2. Conflict Resolution: Priority & Mutex
        fired_mask = self._resolve_conflicts(valid_mask)
        
        # 3. Updates: Apply Deltas & Variance
        self._apply_updates(fired_mask)
        
        # 4. Physics: Carry-Lookahead & Constraints
        self._resolve_physics()
        
        # 5. CPU Valve
        if self.cfg.enable_cpu_offload:
            self._handle_cpu_callbacks(fired_mask)

    def _check_validity(self) -> torch.Tensor:
        """
        Check inputs per-token, not per-sum.
        Returns: [Batch, Num_Rules] boolean.
        """
        bs = self.cfg.batch_size
        # Start with all True
        validity = torch.ones((bs, self.num_rules), dtype=torch.bool, device=self.device)
        
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
                
                # Simplest Vectorized approach:
                # Use index_add on the flattened batch? No.
                # Loop over rules? No.
                
                # Solution: Use torch.sparse.mm with a "Binary Input Matrix".
                # Binary_In = (Indices, Ones).
                # Deficits = Required - State (ReLU).
                # Rule_Deficit = Deficits @ Binary_In.T
                # If Rule_Deficit > 0, Rule Invalid.
                
                # Implementation:
                # Only works if linear sum logic holds. 
                # "If I need 2 Apples and have 1, deficit is 1." -> Invalid.
                # "If I need 1 Apple and have 2, deficit is 0." -> Valid.
                # This works for Fungible inputs (BYTE/FLOAT).
                
                # Calculate Deficit [Batch, NNZ]
                deficit = F.relu(req_vals.unsqueeze(0) - current_vals.float())
                
                # Sum Deficits per Rule
                # We construct a temporary sparse matrix for aggregation
                # Indices: [rule_idx, token_idx] -> We want to sum over token_idx
                # We effectively do a sparse MM:
                # [Batch, Tokens] is implicit. We have [Batch, NNZ_Inputs].
                # We need to sum these values into [Batch, Rules].
                
                # Torch scatter_add is best here:
                # src = deficit [Batch, NNZ]
                # index = rule_idx [NNZ] -> broadcast to [Batch, NNZ]
                index_batch = rule_idx.unsqueeze(0).expand(bs, -1)
                
                rule_deficits = torch.zeros((bs, self.num_rules), device=self.device)
                rule_deficits.scatter_add_(1, index_batch, deficit)
                
                validity &= (rule_deficits == 0)

            # Inhibitors (Must be 0)
            if k["ban"]:
                # Project State onto Bans
                # Any presence > 0 triggers ban
                presence = torch.sparse.mm(k["ban"]["mat"], state.float().t()).t()
                validity &= (presence == 0)
                
        return validity

    def _resolve_conflicts(self, valid: torch.Tensor) -> torch.Tensor:
        bs = self.cfg.batch_size
        
        # 1. Base Probability Check (with Temperature scaling via logits and optional biases)
        base_probs = self.rule_meta[:, 1]  # [Rules]
        eps = 1e-9
        logits = torch.log(base_probs + eps) - torch.log(1.0 - base_probs + eps)
        bias = self.rule_biases if self.rule_biases is not None else 0.0
        scaled_logits = (logits + bias) / max(self.cfg.temperature, eps)
        probs = torch.sigmoid(scaled_logits).unsqueeze(0).expand(bs, -1)
        
        # 1b. Strict priority enforcement: only rules at the max priority per universe can fire
        priorities = self.rule_meta[:, 0].to(self.device)  # [Rules]
        # valid mask is [B, R]
        # max priority per batch row
        max_prio = (valid.float() * priorities.unsqueeze(0)).amax(dim=1)  # [B]
        prio_mask = (priorities.unsqueeze(0) == max_prio.unsqueeze(1))  # [B, R]
        prior_valid = valid & prio_mask
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
                                names = [self.rule_ids[i] for i in idxs] if (self.rule_ids and len(self.rule_ids) == self.num_rules) else None
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
        
        # 2. Handle Mutual Exclusion (One-Of)
        # MutexID is in Col 2. 0 means "Independent".
        mutex_ids = self.rule_meta[:, 2].long()
        
        # Mask of rules that are part of a mutex group
        is_mutex = (mutex_ids != 0)
        
        # Independent Rules: Just roll dice
        rand = torch.rand_like(probs)
        independent_fired = prior_valid & (rand < probs) & (~is_mutex.unsqueeze(0))
        
        # Mutex Rules: Gumbel-Max (on temperature-scaled logits)
        # We need to group by MutexID and pick ArgMax(LogProb + Gumbel)
        # This is hard to vectorize purely in PyTorch without a loop over GroupIDs 
        # or scatter_reduce (newer PyTorch).
        
        mutex_fired = torch.zeros_like(valid)
        unique_groups = torch.tensor([], device=self.device, dtype=mutex_ids.dtype)
        if is_mutex.any():
            unique_groups = torch.unique(mutex_ids)
            # Exclude 0 (non-mutex)
            unique_groups = unique_groups[unique_groups != 0]
        
        # Prepare weight-based scores for mutex: use rule probabilities as weights
        # Apply temperature by exponentiating weights with 1/T
        base_weights = self.rule_meta[:, 1].clamp(min=1e-9)  # [Rules]
        temp = max(self.cfg.temperature, 1e-9)
        weights_t = base_weights.pow(1.0 / temp)  # [Rules]
        
        for gid in unique_groups:
            # Mask for this group
            group_mask = (mutex_ids == gid).unsqueeze(0) # [1, Rules]
            
            # Filter valid rules in this group
            # [Batch, Rules]
            group_valid = prior_valid & group_mask
            
            # If no rules in the group are valid for a universe, none fire.
            # Calculate Scores: Scaled Logits + Gumbel
            # Add -1e9 to invalid rules to prevent selection
            
            # Use precomputed scaled logits (per rule), broadcast to batch
            base_group_logits = scaled_logits.unsqueeze(0).expand(bs, -1)
            gumbel = -torch.log(-torch.log(torch.rand_like(base_group_logits)))
            scores = base_group_logits + gumbel
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
        
        return independent_fired | mutex_fired

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
            
            # 1. Calculate Deterministic Delta
            # Produced
            produced = torch.sparse.mm(k["out_mean"]["mat"].t(), fired_f.t()).t()
            
            # Consumed (from Inputs)
            consumed = torch.zeros_like(produced)
            if k["in"]:
                consumed = torch.sparse.mm(k["in"]["mat"].t(), fired_f.t()).t()
                
            delta = produced - consumed
            
            # 2. Calculate Variance (Chaos Injection)
            if k["out_std"]:
                # Get StdDev sum for fired rules
                # Note: This sums variances linearly, approximation of uncorrelated noise
                std_agg = torch.sparse.mm(k["out_std"]["mat"].t(), fired_f.t()).t()
                noise = torch.randn_like(std_agg)
                delta += (noise * std_agg * self.cfg.temperature)

            # 2b. Consume-All (reduce to zero) — subtract current value once if any such rule fired
            if k["all"] is not None:
                # counts_per_token = (consume_all_map.T @ fired.T).T -> [B, Tokens]
                counts = torch.sparse.mm(k["all"]["mat"].t(), fired_f.t()).t()
                mask = (counts > 0).float()
                current_state = self.state[bt].float()
                delta -= (current_state * mask)
            
            # 3. Apply
            # Note: BIT/BYTE stored as int, but math is float. Cast back.
            current = self.state[bt].float()
            new_val = current + delta
            
            if bt == BlockType.BYTE:
                # Keep in float/int16 for Physics phase
                new_val = torch.clamp(new_val, min=0)
                self.state[BlockType.BYTE] = new_val.to(torch.int16)
            elif bt == BlockType.BIT:
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
                # We need to scatter_add these values to their parent indices.
                # This is tricky because it's a Many-to-One map potentially.
                # Logic: State.scatter_add_(1, Parent_Indices, Overflow_Values)
                
                # Broadcast parent indices to batch
                # Parent_Indices shape: [Batch, Num_Tokens]
                parent_indices = unit_map.unsqueeze(0).expand(self.cfg.batch_size, -1)
                
                # We only want to add where parent != -1. 
                # scatter_add requires valid indices. 
                # Masking strategy: Set invalid parent indices to 0 (dummy), 
                # zero out the flow, then add.
                # Or simpler: Iterate? No.
                
                # Pytorch scatter_add_ handles duplicate indices by summing!
                # We just need to ensure we don't write to index -1.
                # Clamp index to 0, mask value to 0.
                
                safe_indices = parent_indices.clone()
                safe_indices[~has_parent] = 0
                
                # Add to state (accumulate in int16)
                self.state[BlockType.BYTE].scatter_add_(1, safe_indices, valid_overflow.to(self.state[BlockType.BYTE].dtype))
                
                # Note: We might have added to Index 0 incorrectly. 
                # If Token 0 is a dummy, we don't care. 
                # If Token 0 is real, we have a bug.
                # Fix: Ensure Token 0 is always "Void/Null" in Registry.
        
        # 3. Finalize Remainder
        # Only apply remainder if we actually overflowed? 
        # Yes, math holds: 260 -> 1*256 + 4.
        # We update self (remainder) AND parent (carry).
        # Wait, if we updated parent in-place, we shouldn't overwrite self yet?
        # Correct.
        
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
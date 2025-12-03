from typing import Dict, List, Tuple
import torch
import hashlib

from signamancy.engine import SignamancyEngine
from signamancy.registry import TokenRegistry, BlockType


class ReachabilityAnalyzer:
    """
    Boolean forward-closure reachability to flag 'dead' rules:
    A rule is dead if, from the current token presence, its required inputs
    can never become present via any sequence of rule outputs.
    - Ignores inhibitors and consume-all (sound for 'missing inputs' detection).
    - Treats token presence as boolean (>0 for BYTE/FLOAT, >0.5 for BIT).
    """
    def __init__(self, engine: SignamancyEngine, registry: TokenRegistry):
        self.engine = engine
        self.registry = registry
        self.device = engine.device
        # Prepare boolean sparse mats per block
        self.in_mats: Dict[BlockType, torch.Tensor | None] = {}
        self.out_mats: Dict[BlockType, torch.Tensor | None] = {}
        self.in_row_counts: Dict[BlockType, torch.Tensor] = {}

        for bt, k in engine.gpu_blocks.items():
            inm = k.get("in")
            outm = k.get("out_mean")
            self.in_mats[bt] = None if not inm else self._bool_mat(inm["mat"])
            self.out_mats[bt] = None if not outm else self._bool_mat(outm["mat"])
            # Row nnz per rule (inputs count); if no inputs in this block, zeros
            if self.in_mats[bt] is None:
                self.in_row_counts[bt] = torch.zeros(engine.num_rules, dtype=torch.float32, device=self.device)
            else:
                # Count nnz per row by summing boolean values
                nnz = int(self.in_mats[bt]._nnz())
                ones = torch.ones(nnz, device=self.device)
                # Build a vector of per-row nnz via scatter
                idx = self.in_mats[bt]._indices()[0]
                counts = torch.zeros(engine.num_rules, dtype=torch.float32, device=self.device)
                counts.index_add_(0, idx, ones)
                self.in_row_counts[bt] = counts

    def _bool_mat(self, mat: torch.Tensor) -> torch.Tensor:
        coo = mat.coalesce()
        idx = coo.indices()
        vals = torch.ones_like(coo.values())
        return torch.sparse_coo_tensor(idx, vals, coo.shape, device=self.device).coalesce()

    def _snapshot_presence(self) -> Dict[BlockType, torch.Tensor]:
        """
        Build initial boolean presence per block from current engine state (batch-aggregated OR).
        """
        present: Dict[BlockType, torch.Tensor] = {}
        for bt, state in self.engine.state.items():
            if bt == BlockType.BIT:
                present[bt] = (state.float().mean(dim=0) > 0.5)
            elif bt == BlockType.BYTE:
                present[bt] = (state.float().mean(dim=0) > 0.0)
            else:
                present[bt] = (state.float().mean(dim=0) > 0.0)
        return present

    def compute_dead_rules(self, max_iters: int = 32, strict_priority: bool = False) -> torch.Tensor:
        """
        Returns a boolean mask [Rules] where True indicates the rule is dead (unreachable)
        under boolean closure from current state.
        - strict_priority: if True, only considers rules at the current max priority and
          only allows outputs from those rules during closure (immediate-step readiness).
        """
        # Initial presence
        present = {bt: v.clone().to(self.device) for bt, v in self._snapshot_presence().items()}
        num_rules = self.engine.num_rules

        # Priority selection mask
        row_mask = None
        if strict_priority:
            prios = self.engine.rule_meta[:, 0].to(self.device)
            max_prio = prios.max()
            row_mask = (prios == max_prio)

        # Fixed-point closure
        enabled = None
        for _ in range(max_iters):
            # Compute per-block rule enablement (inputs satisfied)
            satisfied_masks = []
            for bt in BlockType:
                inm = self.in_mats.get(bt)
                req = self.in_row_counts[bt]
                if inm is None or req.max() == 0:
                    satisfied_masks.append(torch.ones(num_rules, dtype=torch.bool, device=self.device))
                    continue
                rules_present = torch.sparse.mm(inm, present[bt].float().unsqueeze(1)).squeeze(1)
                satisfied = (rules_present >= req - 1e-9)
                satisfied_masks.append(satisfied)
            # AND across blocks
            enabled = satisfied_masks[0]
            for m in satisfied_masks[1:]:
                enabled = enabled & m
            if strict_priority and row_mask is not None:
                enabled = enabled & row_mask

            # Grow presence via outputs of enabled rules (restricted if strict)
            any_change = False
            enabled_f = enabled.float().unsqueeze(1)
            for bt in BlockType:
                outm = self.out_mats.get(bt)
                if outm is None:
                    continue
                produced = torch.sparse.mm(outm.t(), enabled_f).squeeze(1)
                new_present = present[bt] | (produced > 0)
                if not torch.equal(new_present, present[bt]):
                    present[bt] = new_present
                    any_change = True
            if not any_change:
                break

        # Final enablement at closure
        final_masks = []
        for bt in BlockType:
            inm = self.in_mats.get(bt)
            req = self.in_row_counts[bt]
            if inm is None or req.max() == 0:
                final_masks.append(torch.ones(num_rules, dtype=torch.bool, device=self.device))
                continue
            rules_present = torch.sparse.mm(inm, present[bt].float().unsqueeze(1)).squeeze(1)
            final_masks.append(rules_present >= req - 1e-9)
        final_enabled = final_masks[0]
        for m in final_masks[1:]:
            final_enabled = final_enabled & m
        if strict_priority and row_mask is not None:
            final_enabled = final_enabled & row_mask

        dead_mask = ~final_enabled
        if strict_priority and row_mask is not None:
            # Only report dead on selected rows; others not considered
            dead_mask = dead_mask & row_mask
        return dead_mask

    def report_dead_rules(self, idx_to_id: Dict[int, str], limit: int = 50, strict_priority: bool = False) -> List[str]:
        dead = self.compute_dead_rules(strict_priority=strict_priority)
        idxs = torch.nonzero(dead, as_tuple=False).squeeze(1).tolist()
        names = []
        for i in idxs[:limit]:
            rid = idx_to_id.get(i, f"Rule#{i}")
            names.append(rid)
        return names


def presence_fingerprint(engine: SignamancyEngine) -> str:
    """Compute a boolean presence fingerprint across all blocks and return a short hex digest."""
    h = hashlib.sha1()
    for bt in BlockType:
        state = engine.state[bt].float()
        present = (state.mean(dim=0) > 0.0).to(torch.uint8).cpu().numpy().tobytes()
        h.update(present)
    return h.hexdigest()


def compute_guide_mask(engine: SignamancyEngine, registry: TokenRegistry, max_iters: int = 8, strict_priority: bool = True) -> torch.Tensor:
    ra = ReachabilityAnalyzer(engine, registry)
    dead = ra.compute_dead_rules(max_iters=max_iters, strict_priority=strict_priority)
    return dead.cpu()


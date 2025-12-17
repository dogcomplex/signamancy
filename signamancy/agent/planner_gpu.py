import os
from dataclasses import dataclass
from typing import Dict, List, Tuple
import torch

from signamancy.engine import SignamancyEngine
from signamancy.registry import TokenRegistry, BlockType


@dataclass
class PlannerConfig:
    # Aggregated "dream" planner
    enable_aggregated: bool = True
    eval_every_steps: int = 10
    gain: float = 0.5
    penalty_inputs: float = 0.2
    normalize: bool = True
    top_rules_cap: int = 0  # 0 = no cap
    # Future: per-universe beam A* parameters (placeholders for later GPU planner)
    enable_per_universe: bool = False
    beam_size: int = 32
    expand_top_k: int = 4
    max_depth: int = 8
    max_universes: int = 64


class GPUPlanner:
    """
    Lightweight GPU "dream" planner.
    Produces a per-rule bias delta from aggregated targets using sparse matrix multiplications.
    """
    def __init__(self, cfg: PlannerConfig | None = None):
        self.cfg = cfg if cfg is not None else PlannerConfig()
        self._last_bias: torch.Tensor | None = None
        self._last_step: int = -1

    def _build_token_weights(self, registry: TokenRegistry, targets: List[Tuple[str, float]], device: torch.device) -> Dict[BlockType, torch.Tensor]:
        """
        Create per-block token weight vectors sized to engine.kernel.block_sizes.
        Weight for a token equals the sum of target weights for any prefix that matches its name.
        """
        # Initialize zeros per block
        sizes = registry.export_layout()
        weights: Dict[BlockType, torch.Tensor] = {
            BlockType.BIT: torch.zeros((len(sizes.get(BlockType.BIT, [])),), dtype=torch.float32, device=device),
            BlockType.BYTE: torch.zeros((len(sizes.get(BlockType.BYTE, [])),), dtype=torch.float32, device=device),
            BlockType.FLOAT: torch.zeros((len(sizes.get(BlockType.FLOAT, [])),), dtype=torch.float32, device=device),
        }
        if not targets:
            return weights
        # registry._tokens: gid -> meta with original_text, block_type, local_id
        try:
            for _, meta in registry._tokens.items():  # type: ignore[attr-defined]
                name = meta.original_text
                acc = 0.0
                for pref, w in targets:
                    if name.startswith(pref):
                        acc += float(w)
                if acc != 0.0:
                    bt = meta.block_type
                    li = int(meta.local_id)
                    if li < weights[bt].numel():
                        weights[bt][li] = float(acc)
        except Exception:
            # Best-effort: if registry internals differ, return zeros (no effect)
            pass
        return weights

    def aggregated_bias(self, engine: SignamancyEngine, registry: TokenRegistry, targets: List[Tuple[str, float]]) -> torch.Tensor:
        """
        Compute a small per-rule bias delta on GPU using:
           score(rule) = sum_targets(out_mean @ t) - penalty * sum_targets(in @ t)
        Then normalize and scale by gain.
        Returns a tensor of shape [num_rules] on engine.device.
        """
        device = engine.device
        num_rules = engine.num_rules
        tw = self._build_token_weights(registry, targets, device)
        rule_score = torch.zeros((num_rules,), dtype=torch.float32, device=device)
        pen = float(self.cfg.penalty_inputs)
        for bt in BlockType:
            k = engine.gpu_blocks.get(bt, None)
            if not k:
                continue
            tvec = tw.get(bt, None)
            if tvec is None or tvec.numel() == 0:
                continue
            if k.get("out_mean") and k["out_mean"]["mat"] is not None:
                outc = torch.sparse.mm(k["out_mean"]["mat"], tvec.unsqueeze(1)).squeeze(1)
                rule_score = rule_score + outc
            if pen > 0.0 and k.get("in") and k["in"]["mat"] is not None:
                inc = torch.sparse.mm(k["in"]["mat"], tvec.unsqueeze(1)).squeeze(1)
                rule_score = rule_score - (pen * inc)
        if self.cfg.normalize:
            m = float(rule_score.mean().item())
            s = float(rule_score.std().item())
            if s > 1e-6:
                rule_score = (rule_score - m) / s
            else:
                rule_score = rule_score * 0.0
        if self.cfg.top_rules_cap and self.cfg.top_rules_cap > 0:
            k = min(self.cfg.top_rules_cap, int(rule_score.numel()))
            _, idxs = torch.topk(rule_score, k=k, largest=True)
            mask = torch.zeros_like(rule_score)
            mask[idxs] = 1.0
            rule_score = rule_score * mask
        return rule_score * float(self.cfg.gain)

    # Placeholder for future per-universe GPU planner
    def per_universe_bias(self, engine: SignamancyEngine, registry: TokenRegistry, targets: List[Tuple[str, float]], universe_indices: torch.Tensor) -> torch.Tensor:
        """
        Compute a per-rule bias using M selected universes:
          score(rule) = usefulness(rule; targets) - penalty * mean_universe(deficit(rule; state))
        usefulness(rule; targets) is computed via out_mean @ targets (like aggregated).
        deficit sums required inputs that are missing on those universes.
        Returns a tensor [num_rules] on engine.device.
        """
        device = engine.device
        num_rules = engine.num_rules
        m = int(universe_indices.numel())
        if m == 0:
            return torch.zeros((num_rules,), dtype=torch.float32, device=device)
        # Rule usefulness (independent of universe)
        tw = self._build_token_weights(registry, targets, device)
        rule_gain = torch.zeros((num_rules,), dtype=torch.float32, device=device)
        for bt in BlockType:
            k = engine.gpu_blocks.get(bt, None)
            if not k:
                continue
            tvec = tw.get(bt, None)
            if tvec is None or tvec.numel() == 0:
                continue
            if k.get("out_mean") and k["out_mean"]["mat"] is not None:
                outc = torch.sparse.mm(k["out_mean"]["mat"], tvec.unsqueeze(1)).squeeze(1)
                rule_gain = rule_gain + outc
        # Per-universe input deficits summed per rule
        pen = float(self.cfg.penalty_inputs)
        if pen <= 0.0:
            base = rule_gain
        else:
            deficits_sum = torch.zeros((m, num_rules), dtype=torch.float32, device=device)
            for bt in BlockType:
                k = engine.gpu_blocks.get(bt, None)
                if not k or not k.get("in"):
                    continue
                s_block = engine.state[bt].float().index_select(0, universe_indices)  # [M, T_bt]
                rule_idx_t, token_idx_t = k["in"]["indices"]  # [NNZ], [NNZ]
                req_vals_t = k["in"]["values"].float()       # [NNZ]
                if token_idx_t.numel() == 0:
                    continue
                # Gather current values for required tokens: [M, NNZ]
                cur = s_block.index_select(1, token_idx_t)
                # Deficits: relu(req - cur)
                deficit = torch.relu(req_vals_t.unsqueeze(0) - cur)
                # Scatter-add across rule indices
                ridx = rule_idx_t.unsqueeze(0).expand(m, -1)
                deficits_sum.scatter_add_(1, ridx, deficit)
            # Mean across selected universes
            mean_def = deficits_sum.mean(dim=0)  # [Rules]
            base = rule_gain - (pen * mean_def)
        # Normalize and scale
        if self.cfg.normalize:
            mu = float(base.mean().item())
            sd = float(base.std().item())
            if sd > 1e-6:
                base = (base - mu) / sd
            else:
                base = base * 0.0
        if self.cfg.top_rules_cap and self.cfg.top_rules_cap > 0:
            kcap = min(self.cfg.top_rules_cap, int(base.numel()))
            _, idxs = torch.topk(base, k=kcap, largest=True)
            mask = torch.zeros_like(base)
            mask[idxs] = 1.0
            base = base * mask
        return base * float(self.cfg.gain)

    @staticmethod
    def from_env() -> "GPUPlanner":
        # Build config from environment
        gain = float(os.environ.get("PLANNER_GAIN", "0.5"))
        pen = float(os.environ.get("PLANNER_PENALTY_IN", "0.2"))
        every = int(os.environ.get("PLANNER_EVERY", "10"))
        topk = int(os.environ.get("PLANNER_TOP_RULES", "0"))
        enable_agg = int(os.environ.get("PLANNER_AGGREGATED", "1")) == 1
        enable_uni = int(os.environ.get("PLANNER_PER_UNIVERSE", "0")) == 1
        beam = int(os.environ.get("PLANNER_BEAM", "32"))
        expk = int(os.environ.get("PLANNER_EXPAND_K", "4"))
        depth = int(os.environ.get("PLANNER_DEPTH", "8"))
        maxu = int(os.environ.get("PLANNER_MAX_UNI", "64"))
        cfg = PlannerConfig(
            enable_aggregated=enable_agg,
            eval_every_steps=every,
            gain=gain,
            penalty_inputs=pen,
            normalize=True,
            top_rules_cap=topk,
            enable_per_universe=enable_uni,
            beam_size=beam,
            expand_top_k=expk,
            max_depth=depth,
            max_universes=maxu,
        )
        return GPUPlanner(cfg)



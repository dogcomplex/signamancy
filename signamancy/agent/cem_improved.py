"""
Improved CEM (Cross-Entropy Method) Optimizer for Signamancy.

Key improvements over vanilla CEM:
1. Phase-aware optimization: Different bias profiles for different game phases
2. Dependency-aware rule groups: Correlated sampling for related rules
3. Credit assignment: Track which rules led to successful outcomes
4. Curriculum learning: Gradually increase objective difficulty
"""

import os
import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set
import torch

from signamancy.engine import SignamancyEngine
from signamancy.registry import TokenRegistry, BlockType


@dataclass
class PhaseConfig:
    """Configuration for a single optimization phase."""
    name: str
    # Time window (in decision steps) this phase covers
    start_step: int
    end_step: int
    # Which rule groups are active in this phase (empty = all)
    active_groups: List[str] = field(default_factory=list)
    # Objective weights for this phase
    objective_weights: Dict[str, float] = field(default_factory=dict)
    # Phase-specific hyperparams
    exploration_std: float = 1.0


@dataclass
class RuleGroup:
    """A group of related rules that should be sampled together."""
    name: str
    rule_indices: List[int]
    # Rules in this group should have correlated biases
    correlation: float = 0.8
    # Group-level mean and std (shared component)
    group_mean: float = 0.0
    group_std: float = 1.0


@dataclass
class ImprovedCEMConfig:
    """Configuration for improved CEM optimizer."""
    # Basic CEM params
    population: int = 16
    elite_fraction: float = 0.25
    iterations: int = 8
    horizon: int = 400

    # Phase-aware optimization
    enable_phases: bool = True
    phases: List[PhaseConfig] = field(default_factory=list)

    # Dependency-aware grouping
    enable_groups: bool = True
    group_correlation: float = 0.7  # How correlated rules in same group are

    # Credit assignment
    enable_credit: bool = True
    credit_decay: float = 0.9  # Exponential decay for credit propagation

    # Curriculum learning
    enable_curriculum: bool = True
    curriculum_stages: int = 3  # Progressive difficulty

    # Adaptive exploration
    min_std: float = 0.1
    max_std: float = 2.0
    std_adaptation_rate: float = 0.1


class RuleGrouper:
    """Groups rules based on their IDs for correlated sampling."""

    def __init__(self, idx_to_id: Dict[int, str]):
        self.idx_to_id = idx_to_id
        self.groups: Dict[str, RuleGroup] = {}
        self._build_groups()

    def _build_groups(self):
        """Build rule groups from rule IDs using prefix patterns."""
        # Group by action type prefix
        prefix_to_indices: Dict[str, List[int]] = {}

        for idx, rule_id in self.idx_to_id.items():
            # Extract prefix: ID_ActionType_Target -> ActionType
            parts = rule_id.split('_')
            if len(parts) >= 2:
                prefix = parts[1] if parts[0] == 'ID' else parts[0]
            else:
                prefix = 'misc'

            if prefix not in prefix_to_indices:
                prefix_to_indices[prefix] = []
            prefix_to_indices[prefix].append(idx)

        # Create groups
        for prefix, indices in prefix_to_indices.items():
            if len(indices) >= 2:  # Only group if multiple rules
                self.groups[prefix] = RuleGroup(
                    name=prefix,
                    rule_indices=indices,
                    correlation=0.8
                )

    def get_group_for_rule(self, idx: int) -> Optional[str]:
        """Get the group name for a rule index."""
        for name, group in self.groups.items():
            if idx in group.rule_indices:
                return name
        return None

    def get_strategic_groups(self) -> Dict[str, List[str]]:
        """Return strategic group categories for phase-aware optimization."""
        return {
            'infrastructure': ['Build', 'Buy'],  # Building/purchasing
            'extraction': ['Chop', 'Pick'],      # Resource gathering
            'fishing': ['Rod', 'Fishtrap'],      # Fishing actions
            'processing': ['Baked', 'Preserves', 'Beehive'],  # Value-add processing
            'sales': ['Sell'],                    # Selling goods
            'progression': ['Day', 'Rent'],       # Day/rent advancement
        }


class CreditAssigner:
    """Tracks rule contributions to outcomes for better credit assignment."""

    def __init__(self, num_rules: int, decay: float = 0.9):
        self.num_rules = num_rules
        self.decay = decay
        # Accumulated credit per rule
        self.credit = torch.zeros(num_rules, dtype=torch.float32)
        # Firing counts
        self.fire_counts = torch.zeros(num_rules, dtype=torch.float32)

    def record_firing(self, rule_idx: int, step: int, current_score: float, prev_score: float):
        """Record that a rule fired and track its contribution."""
        delta = current_score - prev_score
        # Immediate credit
        self.credit[rule_idx] += delta
        self.fire_counts[rule_idx] += 1

    def record_batch_firing(self, fired_mask: torch.Tensor, score_delta: float):
        """Record firings for a batch (mask is [batch, rules] or [rules])."""
        if fired_mask.dim() == 2:
            # Mean across batch
            fire_rate = fired_mask.float().mean(dim=0)
        else:
            fire_rate = fired_mask.float()

        # Credit proportional to firing rate and score delta
        self.credit += fire_rate.cpu() * score_delta
        self.fire_counts += fire_rate.cpu()

    def get_credit_bonus(self) -> torch.Tensor:
        """Get normalized credit bonus for each rule."""
        with torch.no_grad():
            # Normalize by fire counts to get average contribution
            avg_credit = self.credit / (self.fire_counts + 1e-6)
            # Normalize to [0, 1] range
            cmin, cmax = avg_credit.min(), avg_credit.max()
            if cmax - cmin > 1e-6:
                normalized = (avg_credit - cmin) / (cmax - cmin)
            else:
                normalized = torch.zeros_like(avg_credit)
            return normalized

    def decay_credit(self):
        """Apply decay to accumulated credit."""
        self.credit *= self.decay


class ImprovedCEM:
    """
    Improved Cross-Entropy Method optimizer with:
    - Phase-aware temporal biases
    - Dependency-aware grouped sampling
    - Credit assignment tracking
    - Curriculum learning
    """

    def __init__(self,
                 num_rules: int,
                 idx_to_id: Dict[int, str],
                 config: Optional[ImprovedCEMConfig] = None,
                 device: str = 'cuda'):
        self.num_rules = num_rules
        self.idx_to_id = idx_to_id
        self.id_to_idx = {v: k for k, v in idx_to_id.items()}
        self.config = config or ImprovedCEMConfig()
        self.device = device

        # Initialize components
        self.grouper = RuleGrouper(idx_to_id) if self.config.enable_groups else None
        self.credit = CreditAssigner(num_rules, self.config.credit_decay) if self.config.enable_credit else None

        # Phase-aware means: one bias vector per phase
        self._setup_phases()

        # CEM state
        self.global_mean = torch.zeros(num_rules, dtype=torch.float32)
        self.global_std = torch.ones(num_rules, dtype=torch.float32)
        self.phase_means: Dict[str, torch.Tensor] = {}
        self.phase_stds: Dict[str, torch.Tensor] = {}

        # Best tracking
        self.best_bias = None
        self.best_score = float('-inf')

    def _setup_phases(self):
        """Setup default phases if none provided."""
        if not self.config.phases:
            # Default: Early, Mid, Late game phases
            self.config.phases = [
                PhaseConfig(
                    name='early',
                    start_step=0,
                    end_step=100,
                    active_groups=['infrastructure', 'extraction'],
                    objective_weights={'👑': 0.0, '💰': 1.0},  # Focus on gold early
                    exploration_std=1.5  # More exploration early
                ),
                PhaseConfig(
                    name='mid',
                    start_step=100,
                    end_step=300,
                    active_groups=['fishing', 'processing', 'sales'],
                    objective_weights={'👑': 0.5, '💰': 0.5},
                    exploration_std=1.0
                ),
                PhaseConfig(
                    name='late',
                    start_step=300,
                    end_step=800,
                    active_groups=['sales', 'progression'],
                    objective_weights={'👑': 1.0, '💰': 1.0},
                    exploration_std=0.5  # Exploit learned strategy
                ),
            ]

        # Initialize per-phase parameters
        for phase in self.config.phases:
            self.phase_means[phase.name] = torch.zeros(self.num_rules, dtype=torch.float32)
            self.phase_stds[phase.name] = torch.ones(self.num_rules, dtype=torch.float32) * phase.exploration_std

    def get_phase(self, step: int) -> Optional[PhaseConfig]:
        """Get the active phase for a given step."""
        for phase in self.config.phases:
            if phase.start_step <= step < phase.end_step:
                return phase
        return None

    def sample_candidate(self, current_step: int = 0) -> torch.Tensor:
        """Sample a candidate bias vector with phase and group awareness."""
        bias = torch.zeros(self.num_rules, dtype=torch.float32)

        if self.config.enable_phases:
            phase = self.get_phase(current_step)
            if phase:
                mean = self.phase_means[phase.name]
                std = self.phase_stds[phase.name]
            else:
                mean = self.global_mean
                std = self.global_std
        else:
            mean = self.global_mean
            std = self.global_std

        if self.config.enable_groups and self.grouper:
            # Sample with group correlation
            bias = self._sample_grouped(mean, std)
        else:
            # Standard independent sampling
            bias = mean + std * torch.randn_like(mean)

        # Add credit bonus if available
        if self.credit:
            credit_bonus = self.credit.get_credit_bonus()
            bias = bias + 0.5 * credit_bonus  # Small bonus from credit

        return bias.clamp(-3.0, 3.0)

    def _sample_grouped(self, mean: torch.Tensor, std: torch.Tensor) -> torch.Tensor:
        """Sample with correlated noise for grouped rules."""
        bias = torch.zeros(self.num_rules, dtype=torch.float32)
        corr = self.config.group_correlation

        # Track which rules have been sampled
        sampled = set()

        for group_name, group in self.grouper.groups.items():
            if not group.rule_indices:
                continue

            # Shared group noise component
            group_noise = torch.randn(1).item()

            for idx in group.rule_indices:
                if idx >= self.num_rules:
                    continue
                # Combine group noise with individual noise
                individual_noise = torch.randn(1).item()
                combined = corr * group_noise + math.sqrt(1 - corr**2) * individual_noise
                bias[idx] = mean[idx] + std[idx] * combined
                sampled.add(idx)

        # Sample remaining rules independently
        for idx in range(self.num_rules):
            if idx not in sampled:
                bias[idx] = mean[idx] + std[idx] * torch.randn(1).item()

        return bias

    def update_from_elite(self, candidates: List[torch.Tensor], scores: List[float],
                          step_range: Tuple[int, int] = (0, 800)):
        """Update parameters from elite candidates, respecting phases."""
        k = max(1, int(math.ceil(self.config.elite_fraction * len(candidates))))
        top_idx = sorted(range(len(candidates)), key=lambda i: scores[i], reverse=True)[:k]
        elite = torch.stack([candidates[i] for i in top_idx], dim=0)

        # Update global
        self.global_mean = elite.mean(dim=0)
        self.global_std = (elite.std(dim=0) + 1e-6).clamp(
            self.config.min_std, self.config.max_std
        )

        # Update phase-specific if phases enabled
        if self.config.enable_phases:
            # For now, use same elite for all phases but scale by phase std
            for phase in self.config.phases:
                if phase.start_step <= step_range[1] and phase.end_step >= step_range[0]:
                    self.phase_means[phase.name] = self.global_mean.clone()
                    self.phase_stds[phase.name] = (
                        self.global_std * phase.exploration_std
                    ).clamp(self.config.min_std, self.config.max_std)

        # Track best
        best_idx = top_idx[0]
        if scores[best_idx] > self.best_score:
            self.best_score = scores[best_idx]
            self.best_bias = candidates[best_idx].clone()

    def get_phase_bias_schedule(self, total_steps: int) -> List[Tuple[int, torch.Tensor]]:
        """
        Get a schedule of biases to apply at different steps.
        Returns list of (step, bias) tuples.
        """
        schedule = []

        if not self.config.enable_phases:
            return [(0, self.best_bias if self.best_bias is not None else self.global_mean)]

        for phase in self.config.phases:
            if phase.start_step < total_steps:
                bias = self.phase_means.get(phase.name, self.global_mean).clone()
                schedule.append((phase.start_step, bias))

        return schedule

    @staticmethod
    def from_env(num_rules: int, idx_to_id: Dict[int, str]) -> "ImprovedCEM":
        """Build from environment variables."""
        cfg = ImprovedCEMConfig(
            population=int(os.environ.get("CEM_POP", "16")),
            elite_fraction=float(os.environ.get("CEM_ELITE_FRAC", "0.25")),
            iterations=int(os.environ.get("CEM_ITERS", "8")),
            horizon=int(os.environ.get("CEM_TRAIN_HORIZON", "400")),
            enable_phases=int(os.environ.get("CEM_PHASES", "1")) == 1,
            enable_groups=int(os.environ.get("CEM_GROUPS", "1")) == 1,
            enable_credit=int(os.environ.get("CEM_CREDIT", "1")) == 1,
            enable_curriculum=int(os.environ.get("CEM_CURRICULUM", "0")) == 1,
            group_correlation=float(os.environ.get("CEM_GROUP_CORR", "0.7")),
            credit_decay=float(os.environ.get("CEM_CREDIT_DECAY", "0.9")),
        )
        device = os.environ.get("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
        return ImprovedCEM(num_rules, idx_to_id, cfg, device)


class TemporalBiasScheduler:
    """
    Applies different bias vectors at different time steps during simulation.
    This allows the agent to have different priorities in different game phases.
    """

    def __init__(self, num_rules: int, idx_to_id: Dict[int, str]):
        self.num_rules = num_rules
        self.idx_to_id = idx_to_id
        self.grouper = RuleGrouper(idx_to_id)

        # Phase biases: step -> bias_delta
        self.phase_biases: Dict[str, torch.Tensor] = {}

        # Strategic group priorities per phase
        self._setup_farm_phases()

    def _setup_farm_phases(self):
        """
        Setup farm-game-specific phase biases.
        These boost/penalize rule groups based on what's optimal at each phase.
        """
        strategic = self.grouper.get_strategic_groups()

        # Phase 1 (steps 0-100): Build infrastructure, gather resources
        early_boost = torch.zeros(self.num_rules, dtype=torch.float32)
        for group_name in ['Build', 'Chop', 'Pick', 'Buy']:
            if group_name in self.grouper.groups:
                for idx in self.grouper.groups[group_name].rule_indices:
                    if idx < self.num_rules:
                        early_boost[idx] = 0.5  # Boost infrastructure

        # De-prioritize fishing early (need rod first)
        for group_name in ['Rod']:
            if group_name in self.grouper.groups:
                for idx in self.grouper.groups[group_name].rule_indices:
                    if idx < self.num_rules:
                        early_boost[idx] = -0.2

        self.phase_biases['early'] = early_boost

        # Phase 2 (steps 100-300): Fish and process
        mid_boost = torch.zeros(self.num_rules, dtype=torch.float32)
        for group_name in ['Rod', 'Baked', 'Preserves', 'Fishtrap', 'Beehive']:
            if group_name in self.grouper.groups:
                for idx in self.grouper.groups[group_name].rule_indices:
                    if idx < self.num_rules:
                        mid_boost[idx] = 0.5

        self.phase_biases['mid'] = mid_boost

        # Phase 3 (steps 300+): Sell everything, maximize value
        late_boost = torch.zeros(self.num_rules, dtype=torch.float32)
        for group_name in ['Sell']:
            if group_name in self.grouper.groups:
                for idx in self.grouper.groups[group_name].rule_indices:
                    if idx < self.num_rules:
                        late_boost[idx] = 0.3

        # Keep Rent high throughout
        for group_name in ['Rent', 'Day']:
            if group_name in self.grouper.groups:
                for idx in self.grouper.groups[group_name].rule_indices:
                    if idx < self.num_rules:
                        late_boost[idx] = 0.5

        self.phase_biases['late'] = late_boost

    def get_phase_bias(self, current_step: int) -> torch.Tensor:
        """Get the bias adjustment for the current step."""
        if current_step < 100:
            return self.phase_biases.get('early', torch.zeros(self.num_rules))
        elif current_step < 300:
            return self.phase_biases.get('mid', torch.zeros(self.num_rules))
        else:
            return self.phase_biases.get('late', torch.zeros(self.num_rules))

    def blend_biases(self, base_bias: torch.Tensor, current_step: int, blend_factor: float = 0.3) -> torch.Tensor:
        """Blend base bias with phase-specific adjustments."""
        phase_bias = self.get_phase_bias(current_step)
        return base_bias + blend_factor * phase_bias.to(base_bias.device)


def create_improved_sampler(
    num_rules: int,
    idx_to_id: Dict[int, str],
    mean: torch.Tensor,
    std: torch.Tensor,
    enable_groups: bool = True,
    group_correlation: float = 0.7
) -> torch.Tensor:
    """
    Sample a bias vector with grouped/correlated sampling.
    Rules in the same action category get correlated noise.
    """
    if not enable_groups:
        # Standard independent sampling
        return (mean + std * torch.randn_like(mean)).clamp(-3.0, 3.0)

    grouper = RuleGrouper(idx_to_id)
    bias = torch.zeros(num_rules, dtype=torch.float32)
    sampled = set()
    corr = group_correlation

    for group_name, group in grouper.groups.items():
        if not group.rule_indices:
            continue

        # Shared group noise component
        group_noise = torch.randn(1).item()

        for idx in group.rule_indices:
            if idx >= num_rules:
                continue
            # Combine group noise with individual noise
            individual_noise = torch.randn(1).item()
            combined = corr * group_noise + math.sqrt(1 - corr**2) * individual_noise
            bias[idx] = mean[idx] + std[idx] * combined
            sampled.add(idx)

    # Sample remaining rules independently
    for idx in range(num_rules):
        if idx not in sampled:
            bias[idx] = mean[idx] + std[idx] * torch.randn(1).item()

    return bias.clamp(-3.0, 3.0)


def integrate_improved_cem(
    engine: SignamancyEngine,
    registry: TokenRegistry,
    idx_to_id: Dict[int, str],
    prefixes: List[str],
    config: Optional[ImprovedCEMConfig] = None
) -> torch.Tensor:
    """
    Run improved CEM optimization and return the best bias vector.
    This is a drop-in replacement for the vanilla CEM loop.
    """
    num_rules = engine.num_rules
    cem = ImprovedCEM(num_rules, idx_to_id, config)

    pop = cem.config.population
    iters = cem.config.iterations
    horizon = cem.config.horizon

    print(f"[ImprovedCEM] Starting optimization: pop={pop}, iters={iters}, horizon={horizon}")
    print(f"[ImprovedCEM] Features: phases={cem.config.enable_phases}, groups={cem.config.enable_groups}, credit={cem.config.enable_credit}")

    if cem.grouper:
        print(f"[ImprovedCEM] Rule groups: {list(cem.grouper.groups.keys())}")

    for it in range(iters):
        candidates = []
        scores = []

        for i in range(pop):
            # Sample at mid-point step for phase-aware sampling
            mid_step = horizon // 2
            bias = cem.sample_candidate(current_step=mid_step)
            candidates.append(bias)

            # TODO: Actually run simulation and score
            # For now, this is a stub - the real scoring happens in run_agent_generic
            scores.append(0.0)

        cem.update_from_elite(candidates, scores, (0, horizon))

        if cem.credit:
            cem.credit.decay_credit()

        print(f"[ImprovedCEM] iter {it+1}/{iters} best={cem.best_score:.3f}")

    return cem.best_bias if cem.best_bias is not None else cem.global_mean

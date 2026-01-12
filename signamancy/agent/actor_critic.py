"""
Actor-Critic Training for Signamancy Agent.

Implements value network training with λ-returns (GAE) inspired by DreamerV4.
The "actor" is implicit - we use the value network to compute advantages that
guide rule selection via the engine's advantage_biases mechanism.
"""

import os
import torch
import torch.nn.functional as F
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field

from .value_network import ValueNetwork, ValueNetworkConfig
from .replay_buffer import ReplayBuffer, Transition


@dataclass
class ActorCriticConfig:
    """Configuration for actor-critic training."""
    # Value network
    hidden_dim: int = 256
    num_layers: int = 2
    dropout: float = 0.0
    use_layer_norm: bool = True

    # DreamerV4 additions
    use_symlog: bool = True  # Use symlog transformation for values
    use_twohot: bool = True  # Use twohot categorical predictions
    twohot_buckets: int = 255  # Number of buckets for twohot
    twohot_low: float = -20.0  # Min value in symlog space
    twohot_high: float = 20.0  # Max value in symlog space

    # Training
    lr: float = 1e-3
    gamma: float = 0.997  # Discount factor (DreamerV4 default)
    lambda_: float = 0.95  # GAE lambda
    train_epochs: int = 10  # Epochs per training iteration
    train_batch_size: int = 256
    grad_clip: float = 1.0

    # Advantage computation
    advantage_weight: float = 1.0  # Scale factor for advantages in selection
    use_gradient_advantages: bool = True  # Use gradient-based vs simulation-based
    topk_simulation: int = 10  # If not using gradient, simulate top-K rules

    # PMPO (DreamerV4) - uses sign of advantages, not magnitude
    use_pmpo: bool = True  # Use PMPO-style advantage handling
    pmpo_alpha: float = 0.5  # Balance between D+ and D- (0.5 = balanced)

    # Replay buffer
    buffer_capacity: int = 50  # Number of trajectories to store

    # Checkpointing
    save_every: int = 10  # Save checkpoint every N training iterations
    checkpoint_path: str = "value_net.pt"


class ActorCriticTrainer:
    """
    Trainer for the value network using actor-critic style updates.

    This class manages:
    - Value network initialization and checkpointing
    - Trajectory collection with value-guided selection
    - GAE return computation
    - Value network training
    """

    def __init__(
        self,
        engine,
        config: ActorCriticConfig = ActorCriticConfig(),
        device: str = 'cuda'
    ):
        self.engine = engine
        self.config = config
        self.device = device
        self.iteration = 0

        # Get state dimensions from engine
        from ..registry import BlockType
        self.bit_dim = engine.state[BlockType.BIT].shape[1]
        self.byte_dim = engine.state[BlockType.BYTE].shape[1]
        self.float_dim = engine.state[BlockType.FLOAT].shape[1]

        # Initialize value network with DreamerV4 features
        self.value_net = ValueNetwork(
            bit_dim=self.bit_dim,
            byte_dim=self.byte_dim,
            float_dim=self.float_dim,
            config=ValueNetworkConfig(
                hidden_dim=config.hidden_dim,
                num_layers=config.num_layers,
                dropout=config.dropout,
                use_layer_norm=config.use_layer_norm,
                # DreamerV4 additions
                use_symlog=config.use_symlog,
                use_twohot=config.use_twohot,
                twohot_buckets=config.twohot_buckets,
                twohot_low=config.twohot_low,
                twohot_high=config.twohot_high
            )
        ).to(device)

        # Optimizer
        self.optimizer = torch.optim.Adam(
            self.value_net.parameters(),
            lr=config.lr
        )

        # Replay buffer
        self.replay_buffer = ReplayBuffer(
            capacity=config.buffer_capacity,
            device=device
        )

        # Precompute rule net outputs for gradient advantages
        self._rule_net_outputs: Optional[torch.Tensor] = None

        # Training stats
        self.stats = {
            'value_loss': [],
            'avg_return': [],
            'avg_advantage': []
        }

        # Peak performance tracking (DreamerV4-style checkpoint saving)
        self.best_score = float('-inf')
        self.best_survival = 0.0
        self.best_iteration = 0

    def _ensure_rule_outputs(self):
        """Lazily compute and cache rule net outputs."""
        if self._rule_net_outputs is None:
            self._rule_net_outputs = self.value_net._get_rule_net_outputs(self.engine)

    def compute_advantages(self) -> torch.Tensor:
        """
        Compute advantages for all rules in current state.

        Returns:
            advantages: [batch, rules] tensor
        """
        if self.config.use_gradient_advantages:
            self._ensure_rule_outputs()
            return self.value_net.compute_gradient_advantages(
                self.engine,
                self._rule_net_outputs
            )
        else:
            # Simulation-based (not fully implemented - falls back to gradient)
            from .value_network import compute_topk_simulation_advantages
            valid_mask = self.engine.last_prior_valid
            if valid_mask is None:
                # Compute validity if not available
                valid_mask = self.engine._check_validity()
            return compute_topk_simulation_advantages(
                self.engine,
                self.value_net,
                valid_mask,
                k=self.config.topk_simulation,
                gamma=self.config.gamma
            )

    def set_advantages_for_step(self):
        """
        Compute and set advantage biases for the current engine state.

        Call this before engine.step() to guide rule selection.

        If use_pmpo=True (DreamerV4):
            Uses sign(advantage) * weight, ignoring magnitude.
            This is more robust to outliers and doesn't require normalization.

        If use_pmpo=False:
            Normalizes advantages to zero mean, unit variance before scaling.
        """
        with torch.no_grad():
            advantages = self.compute_advantages()

            if self.config.use_pmpo:
                # PMPO: Use sign of advantages, not magnitude
                # This removes the need for normalization and is more stable
                # sign(A) gives +1, 0, or -1, then we scale by weight
                sign_advantages = torch.sign(advantages)
                scaled_advantages = sign_advantages * self.config.advantage_weight
            else:
                # Traditional: Normalize advantages per-batch to zero mean, unit variance
                # This prevents large gradient magnitudes from dominating
                adv_mean = advantages.mean(dim=1, keepdim=True)
                adv_std = advantages.std(dim=1, keepdim=True).clamp(min=1e-8)
                normalized_advantages = (advantages - adv_mean) / adv_std
                scaled_advantages = normalized_advantages * self.config.advantage_weight

            self.engine.set_advantage_biases(scaled_advantages)

    def clear_advantages(self):
        """Clear advantage biases from engine."""
        self.engine.clear_advantage_biases()

    def collect_trajectory(
        self,
        horizon: int,
        score_fn,
        use_advantages: bool = True
    ) -> List[Transition]:
        """
        Collect a trajectory with optional value-guided selection.

        Args:
            horizon: Number of steps to collect
            score_fn: Function(engine) -> [batch] rewards
            use_advantages: Whether to use value network for guidance

        Returns:
            List of Transition namedtuples
        """
        from ..registry import BlockType

        trajectory = []
        prev_score = score_fn(self.engine)

        for step in range(horizon):
            # Optionally set advantages before stepping
            if use_advantages:
                self.set_advantages_for_step()

            # Record current state
            bit = self.engine.state[BlockType.BIT].clone()
            byte = self.engine.state[BlockType.BYTE].clone()
            float_block = self.engine.state[BlockType.FLOAT].clone()

            # Step the engine
            self.engine.step()

            # Compute reward as score delta
            current_score = score_fn(self.engine)
            reward = current_score - prev_score
            prev_score = current_score

            # Check for done (could be based on game-specific logic)
            # For now, never done (continuous simulation)
            done = torch.zeros(self.engine.cfg.batch_size, dtype=torch.bool, device=self.device)

            trajectory.append(Transition(
                bit=bit,
                byte=byte,
                float_block=float_block,
                reward=reward,
                done=done,
                step=step
            ))

        # Clear advantages after collection
        if use_advantages:
            self.clear_advantages()

        return trajectory

    def add_trajectory_to_buffer(self, trajectory: List[Transition]):
        """Add collected trajectory to replay buffer with computed returns."""
        self.replay_buffer.add_trajectory(
            trajectory,
            self.value_net,
            gamma=self.config.gamma,
            lambda_=self.config.lambda_
        )

    def train_value_network(self, num_epochs: Optional[int] = None) -> float:
        """
        Train value network from replay buffer.

        Uses the value network's compute_loss method which handles:
        - Twohot categorical loss (cross-entropy) if use_twohot=True
        - Symlog transformation if use_symlog=True
        - Standard MSE loss otherwise

        Args:
            num_epochs: Override config.train_epochs if specified

        Returns:
            Average loss over training
        """
        if len(self.replay_buffer) == 0:
            return 0.0

        epochs = num_epochs or self.config.train_epochs
        total_loss = 0.0
        num_batches = 0

        for epoch in range(epochs):
            try:
                states, returns = self.replay_buffer.sample_batch_efficient(
                    self.config.train_batch_size
                )
            except ValueError:
                # Buffer empty or insufficient samples
                break

            bit, byte, float_block = states

            # Use value network's compute_loss for proper handling of
            # twohot/symlog (DreamerV4 features)
            loss = self.value_net.compute_loss(bit, byte, float_block, returns)

            # Backward pass
            self.optimizer.zero_grad()
            loss.backward()

            # Gradient clipping
            if self.config.grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(
                    self.value_net.parameters(),
                    self.config.grad_clip
                )

            self.optimizer.step()

            total_loss += loss.item()
            num_batches += 1

        avg_loss = total_loss / max(num_batches, 1)
        self.stats['value_loss'].append(avg_loss)

        return avg_loss

    def training_iteration(
        self,
        horizon: int,
        score_fn,
        train_epochs: Optional[int] = None
    ) -> Dict[str, float]:
        """
        One full training iteration: collect trajectory + train value network.

        Args:
            horizon: Steps to collect
            score_fn: Reward function
            train_epochs: Override training epochs

        Returns:
            Dict with training stats
        """
        # Collect trajectory with value guidance
        trajectory = self.collect_trajectory(
            horizon=horizon,
            score_fn=score_fn,
            use_advantages=True
        )

        # Add to buffer
        self.add_trajectory_to_buffer(trajectory)

        # Train
        value_loss = self.train_value_network(train_epochs)

        # Compute stats
        avg_return = self.replay_buffer.get_stats()['avg_return']
        self.stats['avg_return'].append(avg_return)

        self.iteration += 1

        # Checkpoint
        if self.iteration % self.config.save_every == 0:
            self.save_checkpoint()

        return {
            'iteration': self.iteration,
            'value_loss': value_loss,
            'avg_return': avg_return,
            'buffer_size': len(self.replay_buffer),
            'total_transitions': self.replay_buffer.total_transitions()
        }

    def save_checkpoint(self, path: Optional[str] = None):
        """Save value network and training state."""
        path = path or self.config.checkpoint_path
        torch.save({
            'value_net_state_dict': self.value_net.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'iteration': self.iteration,
            'config': self.config,
            'stats': self.stats,
            'bit_dim': self.bit_dim,
            'byte_dim': self.byte_dim,
            'float_dim': self.float_dim,
            'best_score': self.best_score,
            'best_survival': self.best_survival,
            'best_iteration': self.best_iteration
        }, path)
        print(f"[ActorCritic] Saved checkpoint to {path}")

    def save_best_checkpoint(self):
        """Save the best checkpoint (separate from regular checkpoint)."""
        base_path = self.config.checkpoint_path
        # Insert "_best" before extension
        if '.' in base_path:
            parts = base_path.rsplit('.', 1)
            best_path = f"{parts[0]}_best.{parts[1]}"
        else:
            best_path = f"{base_path}_best"
        torch.save({
            'value_net_state_dict': self.value_net.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'iteration': self.best_iteration,
            'config': self.config,
            'stats': self.stats,
            'bit_dim': self.bit_dim,
            'byte_dim': self.byte_dim,
            'float_dim': self.float_dim,
            'best_score': self.best_score,
            'best_survival': self.best_survival,
            'best_iteration': self.best_iteration
        }, best_path)
        print(f"[ActorCritic] Saved BEST checkpoint to {best_path} (score={self.best_score:.1f}, survival={self.best_survival:.1%})")

    def update_best(self, score: float, survival: float) -> bool:
        """
        Update best performance tracking. Returns True if new best.

        Args:
            score: Current mean score
            survival: Current survival rate (0-1)

        Returns:
            True if this is a new best and checkpoint was saved
        """
        # Use survival as primary metric, score as tiebreaker
        is_new_best = (survival > self.best_survival or
                      (survival == self.best_survival and score > self.best_score))
        if is_new_best:
            self.best_score = score
            self.best_survival = survival
            self.best_iteration = self.iteration
            self.save_best_checkpoint()
            return True
        return False

    def load_checkpoint(self, path: Optional[str] = None):
        """Load value network and training state."""
        path = path or self.config.checkpoint_path
        if not os.path.exists(path):
            print(f"[ActorCritic] No checkpoint found at {path}")
            return False

        # PyTorch 2.6+ requires weights_only=False for custom objects
        checkpoint = torch.load(path, map_location=self.device, weights_only=False)

        # Verify dimensions match
        if (checkpoint['bit_dim'] != self.bit_dim or
            checkpoint['byte_dim'] != self.byte_dim or
            checkpoint['float_dim'] != self.float_dim):
            print(f"[ActorCritic] Dimension mismatch, cannot load checkpoint")
            return False

        self.value_net.load_state_dict(checkpoint['value_net_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.iteration = checkpoint['iteration']
        self.stats = checkpoint.get('stats', self.stats)
        # Restore best tracking
        self.best_score = checkpoint.get('best_score', float('-inf'))
        self.best_survival = checkpoint.get('best_survival', 0.0)
        self.best_iteration = checkpoint.get('best_iteration', 0)

        print(f"[ActorCritic] Loaded checkpoint from {path} (iteration {self.iteration}, best_survival={self.best_survival:.1%})")
        return True

    def get_training_summary(self) -> str:
        """Get a summary string of training progress."""
        if not self.stats['value_loss']:
            return "No training data yet"

        recent_loss = sum(self.stats['value_loss'][-10:]) / max(1, min(10, len(self.stats['value_loss'])))
        if self.stats['avg_return']:
            recent_return = sum(self.stats['avg_return'][-10:]) / max(1, min(10, len(self.stats['avg_return'])))
            return_str = f"Avg Return: {recent_return:.2f} | "
        else:
            return_str = ""

        return (
            f"Iteration {self.iteration} | "
            f"Loss: {recent_loss:.4f} | "
            f"{return_str}"
            f"Buffer: {len(self.replay_buffer)} trajectories"
        )


def create_trainer_from_env(engine) -> ActorCriticTrainer:
    """
    Create an ActorCriticTrainer with configuration from environment variables.

    Environment variables:
        VALUE_NET_HIDDEN: Hidden layer size (default 256)
        VALUE_NET_LR: Learning rate (default 1e-3)
        VALUE_NET_GAMMA: Discount factor (default 0.997, DreamerV4)
        VALUE_NET_LAMBDA: GAE lambda (default 0.95)
        VALUE_ADV_WEIGHT: Advantage weight (default 1.0)
        VALUE_GRADIENT_MODE: Use gradient advantages (default 1)
        VALUE_NET_PATH: Checkpoint path (default value_net.pt)
        VALUE_USE_SYMLOG: Use symlog transformation (default 1)
        VALUE_USE_TWOHOT: Use twohot categorical (default 1)
        VALUE_USE_PMPO: Use PMPO sign-based advantages (default 1)
    """
    config = ActorCriticConfig(
        hidden_dim=int(os.environ.get('VALUE_NET_HIDDEN', '256')),
        lr=float(os.environ.get('VALUE_NET_LR', '1e-3')),
        gamma=float(os.environ.get('VALUE_NET_GAMMA', '0.997')),
        lambda_=float(os.environ.get('VALUE_NET_LAMBDA', '0.95')),
        advantage_weight=float(os.environ.get('VALUE_ADV_WEIGHT', '1.0')),
        use_gradient_advantages=os.environ.get('VALUE_GRADIENT_MODE', '1') == '1',
        topk_simulation=int(os.environ.get('VALUE_TOPK', '10')),
        checkpoint_path=os.environ.get('VALUE_NET_PATH', 'value_net.pt'),
        # DreamerV4 additions
        use_symlog=os.environ.get('VALUE_USE_SYMLOG', '1') == '1',
        use_twohot=os.environ.get('VALUE_USE_TWOHOT', '1') == '1',
        use_pmpo=os.environ.get('VALUE_USE_PMPO', '1') == '1'
    )

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    return ActorCriticTrainer(engine, config, device)

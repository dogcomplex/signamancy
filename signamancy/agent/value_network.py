"""
Value Network for Signamancy Agent.

Inspired by DreamerV4's value function, this module provides:
- V(state) prediction for credit assignment
- Gradient-based advantage estimation for rule selection
- Integration with the Signamancy engine's block-based state representation
- Symlog/Twohot value predictions (DreamerV4)
- PMPO-style advantage handling
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
import math


# =============================================================================
# DreamerV4 Symlog/Symexp Transformations
# =============================================================================

def symlog(x: torch.Tensor) -> torch.Tensor:
    """
    Symlog transformation from DreamerV3/V4.
    Compresses large values while preserving sign: sign(x) * ln(|x| + 1)
    """
    return torch.sign(x) * torch.log1p(torch.abs(x))


def symexp(x: torch.Tensor) -> torch.Tensor:
    """
    Inverse of symlog: sign(x) * (exp(|x|) - 1)
    """
    return torch.sign(x) * (torch.exp(torch.abs(x)) - 1)


# =============================================================================
# Twohot Categorical Distribution for Robust Value Prediction
# =============================================================================

class TwohotDistribution:
    """
    Twohot categorical distribution for value prediction (DreamerV4).

    Instead of predicting a single scalar, predicts a distribution over
    discretized buckets. More robust to outliers and stochastic rewards.

    The "twohot" encoding spreads probability mass between the two nearest
    buckets, allowing for continuous value representation.
    """

    def __init__(
        self,
        num_buckets: int = 255,
        low: float = -20.0,
        high: float = 20.0,
        use_symlog: bool = True
    ):
        self.num_buckets = num_buckets
        self.low = low
        self.high = high
        self.use_symlog = use_symlog

        # Create bucket boundaries (in symlog space if enabled)
        self.buckets = torch.linspace(low, high, num_buckets)

    def encode(self, values: torch.Tensor) -> torch.Tensor:
        """
        Encode continuous values as twohot distributions.

        Args:
            values: [batch] tensor of continuous values

        Returns:
            twohot: [batch, num_buckets] tensor of twohot encodings
        """
        # Transform to symlog space if enabled
        if self.use_symlog:
            values = symlog(values)

        # Clamp to bucket range
        values = values.clamp(self.low, self.high)

        # Find bucket indices
        buckets = self.buckets.to(values.device)
        bucket_width = (self.high - self.low) / (self.num_buckets - 1)

        # Continuous bucket index
        cont_idx = (values - self.low) / bucket_width

        # Lower and upper bucket indices
        lower_idx = cont_idx.floor().long().clamp(0, self.num_buckets - 2)
        upper_idx = lower_idx + 1

        # Interpolation weights (how much goes to upper bucket)
        upper_weight = cont_idx - lower_idx.float()
        lower_weight = 1.0 - upper_weight

        # Create twohot encoding
        batch_size = values.shape[0]
        twohot = torch.zeros(batch_size, self.num_buckets, device=values.device)

        # Scatter weights to appropriate buckets
        batch_indices = torch.arange(batch_size, device=values.device)
        twohot[batch_indices, lower_idx] = lower_weight
        twohot[batch_indices, upper_idx] = upper_weight

        return twohot

    def decode(self, logits: torch.Tensor) -> torch.Tensor:
        """
        Decode logits to continuous values via expected value.

        Args:
            logits: [batch, num_buckets] tensor of logits

        Returns:
            values: [batch] tensor of continuous values
        """
        # Softmax to get probabilities
        probs = F.softmax(logits, dim=-1)

        # Compute expected bucket value
        buckets = self.buckets.to(logits.device)
        expected = (probs * buckets).sum(dim=-1)

        # Transform back from symlog space if enabled
        if self.use_symlog:
            expected = symexp(expected)

        return expected

    def loss(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Compute cross-entropy loss against twohot targets.

        Args:
            logits: [batch, num_buckets] tensor of logits
            targets: [batch] tensor of target values

        Returns:
            loss: scalar cross-entropy loss
        """
        # Encode targets as twohot
        twohot_targets = self.encode(targets)

        # Cross-entropy with soft targets
        log_probs = F.log_softmax(logits, dim=-1)
        loss = -(twohot_targets * log_probs).sum(dim=-1).mean()

        return loss


@dataclass
class ValueNetworkConfig:
    """Configuration for the value network."""
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


class ValueNetwork(nn.Module):
    """
    Value network that predicts expected future score from Signamancy state.

    Architecture:
    - Separate encoders for BIT, BYTE, FLOAT blocks
    - Shared trunk with residual connections
    - Scalar value output

    The network takes the three state blocks as input and outputs V(state),
    an estimate of the discounted sum of future rewards from this state.
    """

    def __init__(
        self,
        bit_dim: int,
        byte_dim: int,
        float_dim: int,
        config: ValueNetworkConfig = ValueNetworkConfig()
    ):
        super().__init__()
        self.bit_dim = bit_dim
        self.byte_dim = byte_dim
        self.float_dim = float_dim
        self.config = config
        hidden = config.hidden_dim

        # Block encoders - project each block to hidden dim
        self.bit_encoder = nn.Linear(bit_dim, hidden)
        self.byte_encoder = nn.Linear(byte_dim, hidden)
        self.float_encoder = nn.Linear(float_dim, hidden)

        # Optional layer norms for stability
        if config.use_layer_norm:
            self.bit_norm = nn.LayerNorm(hidden)
            self.byte_norm = nn.LayerNorm(hidden)
            self.float_norm = nn.LayerNorm(hidden)
        else:
            self.bit_norm = nn.Identity()
            self.byte_norm = nn.Identity()
            self.float_norm = nn.Identity()

        # Trunk: combines all three embeddings
        trunk_layers = []
        input_dim = hidden * 3
        for i in range(config.num_layers):
            trunk_layers.append(nn.Linear(input_dim if i == 0 else hidden, hidden))
            trunk_layers.append(nn.ReLU())
            if config.use_layer_norm:
                trunk_layers.append(nn.LayerNorm(hidden))
            if config.dropout > 0:
                trunk_layers.append(nn.Dropout(config.dropout))
        self.trunk = nn.Sequential(*trunk_layers)

        # Value head - either scalar or twohot categorical
        if config.use_twohot:
            self.value_head = nn.Linear(hidden, config.twohot_buckets)
            self.twohot_dist = TwohotDistribution(
                num_buckets=config.twohot_buckets,
                low=config.twohot_low,
                high=config.twohot_high,
                use_symlog=config.use_symlog
            )
        else:
            self.value_head = nn.Linear(hidden, 1)
            self.twohot_dist = None

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Initialize weights with small values for stable training."""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.orthogonal_(m.weight, gain=0.1)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(
        self,
        bit: torch.Tensor,
        byte: torch.Tensor,
        float_block: torch.Tensor,
        return_logits: bool = False
    ) -> torch.Tensor:
        """
        Forward pass computing V(state).

        Args:
            bit: [batch, bit_dim] int8/float tensor of BIT block
            byte: [batch, byte_dim] int16/float tensor of BYTE block
            float_block: [batch, float_dim] float32 tensor of FLOAT block
            return_logits: If True and using twohot, return raw logits instead of decoded value

        Returns:
            values: [batch] tensor of value estimates (or [batch, buckets] logits if return_logits)
        """
        # Encode each block (cast to float if needed)
        bit_embed = F.relu(self.bit_encoder(bit.float()))
        bit_embed = self.bit_norm(bit_embed)

        byte_embed = F.relu(self.byte_encoder(byte.float()))
        byte_embed = self.byte_norm(byte_embed)

        float_embed = F.relu(self.float_encoder(float_block))
        float_embed = self.float_norm(float_embed)

        # Combine embeddings
        combined = torch.cat([bit_embed, byte_embed, float_embed], dim=-1)

        # Trunk processing
        features = self.trunk(combined)

        # Value prediction
        if self.twohot_dist is not None:
            logits = self.value_head(features)  # [batch, buckets]
            if return_logits:
                return logits
            # Decode to scalar value
            value = self.twohot_dist.decode(logits)
        else:
            value = self.value_head(features).squeeze(-1)
            # Apply symlog if enabled but not using twohot
            if self.config.use_symlog:
                # Network predicts in symlog space, decode to real space
                value = symexp(value)

        return value

    def compute_loss(self, bit: torch.Tensor, byte: torch.Tensor,
                     float_block: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Compute value prediction loss.

        For twohot: cross-entropy against twohot-encoded targets
        For scalar: MSE loss (optionally in symlog space)

        Args:
            bit, byte, float_block: State tensors
            targets: [batch] tensor of target values

        Returns:
            loss: Scalar loss value
        """
        if self.twohot_dist is not None:
            # Get logits and compute twohot cross-entropy
            logits = self.forward(bit, byte, float_block, return_logits=True)
            return self.twohot_dist.loss(logits, targets)
        else:
            # Scalar prediction with optional symlog
            values = self.forward(bit, byte, float_block)
            if self.config.use_symlog:
                # Compute loss in symlog space for stability
                return F.mse_loss(symlog(values), symlog(targets))
            else:
                return F.mse_loss(values, targets)

    def get_state_from_engine(self, engine) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Extract state tensors from a Signamancy engine.

        Args:
            engine: SignamancyEngine instance

        Returns:
            (bit, byte, float_block) tuple of state tensors
        """
        from ..registry import BlockType

        bit = engine.state[BlockType.BIT]
        byte = engine.state[BlockType.BYTE]
        float_block = engine.state[BlockType.FLOAT]

        return bit, byte, float_block

    def compute_value_from_engine(self, engine) -> torch.Tensor:
        """
        Convenience method to compute V(state) directly from engine.

        Args:
            engine: SignamancyEngine instance

        Returns:
            values: [batch] tensor of value estimates
        """
        bit, byte, float_block = self.get_state_from_engine(engine)
        return self.forward(bit, byte, float_block)

    def compute_gradient_advantages(
        self,
        engine,
        rule_net_outputs: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Compute advantage estimates using value gradients.

        This approximates A(s, a) = Q(s, a) - V(s) without simulating each action,
        by computing ∂V/∂state and multiplying by each rule's net output effect.

        A_approx(rule) ≈ ∂V/∂state · Δstate(rule)

        Args:
            engine: SignamancyEngine instance
            rule_net_outputs: [rules, total_tokens] tensor of net state changes per rule
                             If None, will be computed from engine kernel data

        Returns:
            advantages: [batch, rules] tensor of advantage estimates
        """
        from ..registry import BlockType

        # Get state with gradients enabled
        bit, byte, float_block = self.get_state_from_engine(engine)

        # Clone and enable gradients - use torch.enable_grad() to ensure gradients work
        # even if we're in a no_grad context
        with torch.enable_grad():
            bit_grad = bit.float().detach().requires_grad_(True)
            byte_grad = byte.float().detach().requires_grad_(True)
            float_grad = float_block.detach().requires_grad_(True)

            # Forward pass - ensure model is in a gradient-enabled state
            values = self.forward(bit_grad, byte_grad, float_grad)

            # Backward to get gradients
            # Sum values to get scalar for backward (gradients will be per-element)
            values.sum().backward()

        # Concatenate gradients into single vector per batch element
        # Shape: [batch, total_tokens]
        grad = torch.cat([
            bit_grad.grad,
            byte_grad.grad,
            float_grad.grad
        ], dim=-1)

        # Get rule net outputs if not provided
        if rule_net_outputs is None:
            rule_net_outputs = self._get_rule_net_outputs(engine)

        # Compute advantages: [batch, rules] = [batch, tokens] @ [tokens, rules]
        advantages = grad @ rule_net_outputs.T

        return advantages

    def _get_rule_net_outputs(self, engine) -> torch.Tensor:
        """
        Extract net output vectors for each rule from engine kernel data.

        Returns:
            rule_outputs: [rules, total_tokens] dense tensor of net state changes
        """
        from ..registry import BlockType

        num_rules = engine.num_rules
        bit_dim = engine.state[BlockType.BIT].shape[1]
        byte_dim = engine.state[BlockType.BYTE].shape[1]
        float_dim = engine.state[BlockType.FLOAT].shape[1]
        total_dim = bit_dim + byte_dim + float_dim

        # Initialize dense output matrix
        rule_outputs = torch.zeros(
            (num_rules, total_dim),
            dtype=torch.float32,
            device=engine.device
        )

        offset = 0
        for bt in [BlockType.BIT, BlockType.BYTE, BlockType.FLOAT]:
            k = engine.gpu_blocks.get(bt)
            if k is None:
                if bt == BlockType.BIT:
                    offset += bit_dim
                elif bt == BlockType.BYTE:
                    offset += byte_dim
                else:
                    offset += float_dim
                continue

            block_dim = engine.state[bt].shape[1]

            # Get net output matrix (outputs - inputs)
            out_net = k.get("out_net")
            if out_net is not None and out_net.get("mat") is not None:
                # Convert sparse to dense for this block
                dense = out_net["mat"].to_dense()  # [rules, block_tokens]
                rule_outputs[:, offset:offset + block_dim] = dense
            else:
                # Compute from separate in/out if net not available
                out_mat = k.get("out_mean", {}).get("mat")
                in_mat = k.get("in", {}).get("mat")
                if out_mat is not None:
                    rule_outputs[:, offset:offset + block_dim] += out_mat.to_dense()
                if in_mat is not None:
                    rule_outputs[:, offset:offset + block_dim] -= in_mat.to_dense()

            offset += block_dim

        return rule_outputs

    def save(self, path: str):
        """Save model state dict and config."""
        torch.save({
            'state_dict': self.state_dict(),
            'bit_dim': self.bit_dim,
            'byte_dim': self.byte_dim,
            'float_dim': self.float_dim,
            'config': self.config
        }, path)

    @classmethod
    def load(cls, path: str, device: str = 'cuda',
             config_override: Optional[ValueNetworkConfig] = None) -> 'ValueNetwork':
        """
        Load model from checkpoint.

        Args:
            path: Path to checkpoint file
            device: Device to load model to
            config_override: If provided, use this config instead of checkpoint's.
                            Useful when architecture has changed (e.g., adding twohot).

        Note: If the checkpoint was saved with a different architecture (e.g., scalar
        vs twohot), you may need to provide config_override and only load compatible
        weights.
        """
        # PyTorch 2.6+ requires weights_only=False for custom objects
        checkpoint = torch.load(path, map_location=device, weights_only=False)

        # Use override config or checkpoint config
        if config_override is not None:
            config = config_override
        else:
            config = checkpoint['config']
            # Handle old checkpoints that don't have DreamerV4 fields
            if not hasattr(config, 'use_symlog'):
                config.use_symlog = False
            if not hasattr(config, 'use_twohot'):
                config.use_twohot = False

        model = cls(
            bit_dim=checkpoint['bit_dim'],
            byte_dim=checkpoint['byte_dim'],
            float_dim=checkpoint['float_dim'],
            config=config
        )

        # Try to load state dict - may fail if architecture changed
        try:
            model.load_state_dict(checkpoint['state_dict'])
        except RuntimeError as e:
            # Architecture mismatch - try partial load
            print(f"[ValueNetwork] Full load failed: {e}")
            print("[ValueNetwork] Attempting partial load of compatible weights...")
            state_dict = checkpoint['state_dict']
            model_dict = model.state_dict()

            # Only load weights that match in shape
            compatible = {}
            for k, v in state_dict.items():
                if k in model_dict and model_dict[k].shape == v.shape:
                    compatible[k] = v
                else:
                    print(f"  Skipping incompatible: {k}")

            model_dict.update(compatible)
            model.load_state_dict(model_dict)
            print(f"[ValueNetwork] Loaded {len(compatible)}/{len(state_dict)} weight tensors")

        model.to(device)
        return model


def compute_topk_simulation_advantages(
    engine,
    value_net: ValueNetwork,
    valid_mask: torch.Tensor,
    k: int = 10,
    gamma: float = 0.99
) -> torch.Tensor:
    """
    Compute exact advantages for top-K rules by simulation.

    For each of the top-K highest-bias valid rules, we:
    1. Apply the rule's state change directly (without full engine step)
    2. Compute V(new_state)
    3. Compute advantage as V(new_state) - V(current_state)

    This is an approximation since we don't simulate cascading rules,
    but it's much faster than running the full engine.

    Args:
        engine: SignamancyEngine instance (state will be temporarily modified)
        value_net: ValueNetwork for V(s') computation
        valid_mask: [batch, rules] boolean mask of valid rules
        k: Number of top rules to evaluate per universe
        gamma: Discount factor

    Returns:
        advantages: [batch, rules] tensor (zero for non-top-K rules)
    """
    from ..registry import BlockType

    batch_size = engine.cfg.batch_size
    num_rules = engine.num_rules
    device = engine.device

    # Get current value estimate
    with torch.no_grad():
        current_value = value_net.compute_value_from_engine(engine)  # [batch]

    # Get scaled logits (biases) to determine top-K
    scaled_logits = engine.last_scaled_logits  # [rules]
    if scaled_logits is None:
        # Use static biases if no logits available
        scaled_logits = engine.rule_biases_static if engine.rule_biases_static is not None else torch.zeros(num_rules, device=device)

    # Expand logits to batch and mask invalid
    logits_batch = scaled_logits.unsqueeze(0).expand(batch_size, -1).clone()
    logits_batch[~valid_mask] = -float('inf')

    # Get top-K indices per universe
    actual_k = min(k, num_rules)
    _, topk_indices = logits_batch.topk(actual_k, dim=1)  # [batch, k]

    # Initialize advantages (default to 0)
    advantages = torch.zeros((batch_size, num_rules), device=device, dtype=torch.float32)

    # Get rule net outputs (cached if already computed)
    rule_net_outputs = value_net._get_rule_net_outputs(engine)  # [rules, total_tokens]

    # Save current state
    bit_orig = engine.state[BlockType.BIT].clone()
    byte_orig = engine.state[BlockType.BYTE].clone()
    float_orig = engine.state[BlockType.FLOAT].clone()

    # For each top-K position, simulate rule application and compute V(next_state)
    for ki in range(actual_k):
        rule_indices = topk_indices[:, ki]  # [batch] rule index for this k position

        # Check which universes have valid rules at this k position
        valid_at_k = torch.gather(valid_mask, 1, rule_indices.unsqueeze(1)).squeeze(1)

        if not valid_at_k.any():
            continue

        # Get the state change for each rule
        # rule_net_outputs is [rules, total_tokens], we need to gather per-universe
        # delta_state[b] = rule_net_outputs[rule_indices[b], :]
        delta_state = rule_net_outputs[rule_indices]  # [batch, total_tokens]

        # Apply the delta to create new state
        bit_dim = bit_orig.shape[1]
        byte_dim = byte_orig.shape[1]

        # Split delta into blocks
        delta_bit = delta_state[:, :bit_dim]
        delta_byte = delta_state[:, bit_dim:bit_dim + byte_dim]
        delta_float = delta_state[:, bit_dim + byte_dim:]

        # Create new state (only for valid universes)
        new_bit = bit_orig.float() + delta_bit
        new_byte = byte_orig.float() + delta_byte
        new_float = float_orig + delta_float

        # Compute V(new_state) for valid universes
        with torch.no_grad():
            new_values = value_net(new_bit, new_byte, new_float)  # [batch]

        # Compute advantage: A = V(s') - V(s)
        # (We use V(s') - V(s) instead of Q - V because we're not modeling rewards)
        rule_advantages = new_values - current_value  # [batch]

        # Zero out advantages for invalid universes at this k position
        rule_advantages = rule_advantages * valid_at_k.float()

        # Scatter advantages to the correct rule positions
        advantages.scatter_(1, rule_indices.unsqueeze(1), rule_advantages.unsqueeze(1))

    return advantages

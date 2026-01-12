"""
Replay Buffer for Value Network Training.

Stores trajectories and computes returns for training the value network.
Implements Generalized Advantage Estimation (GAE) λ-returns as used in DreamerV4.
"""

import torch
import random
from typing import List, Tuple, Optional, NamedTuple
from dataclasses import dataclass


class Transition(NamedTuple):
    """A single transition in the environment."""
    bit: torch.Tensor        # [batch, bit_dim] BIT block state
    byte: torch.Tensor       # [batch, byte_dim] BYTE block state
    float_block: torch.Tensor  # [batch, float_dim] FLOAT block state
    reward: torch.Tensor     # [batch] reward received
    done: torch.Tensor       # [batch] episode termination flag
    step: int                # Step number in trajectory


@dataclass
class TrajectoryData:
    """Complete trajectory with computed returns."""
    states: List[Tuple[torch.Tensor, torch.Tensor, torch.Tensor]]  # (bit, byte, float) per step
    rewards: torch.Tensor  # [horizon, batch]
    dones: torch.Tensor    # [horizon, batch]
    returns: torch.Tensor  # [horizon, batch] computed λ-returns


class ReplayBuffer:
    """
    Replay buffer for storing trajectories and computing returns.

    Stores full trajectories rather than individual transitions to enable
    proper computation of λ-returns (GAE) for value network training.
    """

    def __init__(
        self,
        capacity: int = 100,  # Number of trajectories to store
        device: str = 'cuda'
    ):
        self.capacity = capacity
        self.device = device
        self.trajectories: List[TrajectoryData] = []
        self.position = 0

    def add_trajectory(
        self,
        transitions: List[Transition],
        value_net,
        gamma: float = 0.99,
        lambda_: float = 0.95
    ):
        """
        Add a trajectory and compute its λ-returns.

        Args:
            transitions: List of Transition namedtuples
            value_net: ValueNetwork for computing bootstrap values
            gamma: Discount factor
            lambda_: GAE lambda parameter
        """
        if not transitions:
            return

        horizon = len(transitions)
        batch_size = transitions[0].reward.shape[0]

        # Stack rewards and dones
        rewards = torch.stack([t.reward for t in transitions])  # [horizon, batch]
        dones = torch.stack([t.done.float() for t in transitions])  # [horizon, batch]

        # Extract states
        states = [(t.bit, t.byte, t.float_block) for t in transitions]

        # Compute returns using GAE
        with torch.no_grad():
            returns = self._compute_gae_returns(
                states, rewards, dones, value_net, gamma, lambda_
            )

        trajectory = TrajectoryData(
            states=states,
            rewards=rewards,
            dones=dones,
            returns=returns
        )

        # Add to buffer (circular)
        if len(self.trajectories) < self.capacity:
            self.trajectories.append(trajectory)
        else:
            self.trajectories[self.position] = trajectory
        self.position = (self.position + 1) % self.capacity

    def _compute_gae_returns(
        self,
        states: List[Tuple[torch.Tensor, torch.Tensor, torch.Tensor]],
        rewards: torch.Tensor,
        dones: torch.Tensor,
        value_net,
        gamma: float,
        lambda_: float
    ) -> torch.Tensor:
        """
        Compute Generalized Advantage Estimation (GAE) λ-returns.

        λ-return: G^λ_t = r_t + γ(1-d_t)[(1-λ)V(s_{t+1}) + λG^λ_{t+1}]

        This blends TD(1) through TD(∞) returns using λ as the mixing coefficient.
        """
        horizon = len(states)
        batch_size = rewards.shape[1]
        device = rewards.device

        # Compute all value estimates
        values = torch.zeros((horizon + 1, batch_size), device=device)
        for t, (bit, byte, float_block) in enumerate(states):
            values[t] = value_net(bit, byte, float_block)

        # Bootstrap value for final state (assume V=0 if done)
        if horizon > 0:
            # Use last state's value as bootstrap, zeroed if done
            values[horizon] = values[horizon - 1] * (1 - dones[horizon - 1])

        # Compute GAE returns backwards
        returns = torch.zeros_like(rewards)
        gae = torch.zeros(batch_size, device=device)

        for t in reversed(range(horizon)):
            next_value = values[t + 1]
            delta = rewards[t] + gamma * next_value * (1 - dones[t]) - values[t]
            gae = delta + gamma * lambda_ * (1 - dones[t]) * gae
            returns[t] = gae + values[t]

        return returns

    def sample(
        self,
        batch_size: int
    ) -> Tuple[Tuple[torch.Tensor, torch.Tensor, torch.Tensor], torch.Tensor]:
        """
        Sample random (state, return) pairs for training.

        Args:
            batch_size: Number of samples to return

        Returns:
            states: (bit, byte, float_block) tuple of [batch_size, dim] tensors
            returns: [batch_size] tensor of target returns
        """
        if not self.trajectories:
            raise ValueError("Replay buffer is empty")

        # Flatten all available (state, return) pairs
        all_states = []
        all_returns = []

        for traj in self.trajectories:
            for t, (bit, byte, float_block) in enumerate(traj.states):
                # Reshape from [traj_batch, dim] to individual samples
                traj_batch = bit.shape[0]
                for b in range(traj_batch):
                    all_states.append((
                        bit[b:b+1],
                        byte[b:b+1],
                        float_block[b:b+1]
                    ))
                    all_returns.append(traj.returns[t, b])

        # Random sample
        if len(all_states) < batch_size:
            indices = list(range(len(all_states)))
        else:
            indices = random.sample(range(len(all_states)), batch_size)

        # Collate samples
        sampled_bit = torch.cat([all_states[i][0] for i in indices], dim=0)
        sampled_byte = torch.cat([all_states[i][1] for i in indices], dim=0)
        sampled_float = torch.cat([all_states[i][2] for i in indices], dim=0)
        sampled_returns = torch.tensor(
            [all_returns[i] for i in indices],
            dtype=torch.float32,
            device=self.device
        )

        return (sampled_bit, sampled_byte, sampled_float), sampled_returns

    def sample_batch_efficient(
        self,
        batch_size: int
    ) -> Tuple[Tuple[torch.Tensor, torch.Tensor, torch.Tensor], torch.Tensor]:
        """
        Efficiently sample by picking random trajectories and time steps.

        More memory-efficient than flattening all data.

        Args:
            batch_size: Number of samples to return

        Returns:
            states: (bit, byte, float_block) tuple of [batch_size, dim] tensors
            returns: [batch_size] tensor of target returns
        """
        if not self.trajectories:
            raise ValueError("Replay buffer is empty")

        sampled_bits = []
        sampled_bytes = []
        sampled_floats = []
        sampled_returns = []

        for _ in range(batch_size):
            # Pick random trajectory
            traj = random.choice(self.trajectories)
            horizon = len(traj.states)
            traj_batch = traj.states[0][0].shape[0]

            # Pick random time step
            t = random.randint(0, horizon - 1)

            # Pick random universe in batch
            b = random.randint(0, traj_batch - 1)

            bit, byte, float_block = traj.states[t]
            sampled_bits.append(bit[b:b+1])
            sampled_bytes.append(byte[b:b+1])
            sampled_floats.append(float_block[b:b+1])
            sampled_returns.append(traj.returns[t, b].item())

        # Collate
        bit_batch = torch.cat(sampled_bits, dim=0)
        byte_batch = torch.cat(sampled_bytes, dim=0)
        float_batch = torch.cat(sampled_floats, dim=0)
        returns_batch = torch.tensor(
            sampled_returns,
            dtype=torch.float32,
            device=self.device
        )

        return (bit_batch, byte_batch, float_batch), returns_batch

    def __len__(self) -> int:
        """Return number of stored trajectories."""
        return len(self.trajectories)

    def total_transitions(self) -> int:
        """Return total number of (state, return) pairs available."""
        total = 0
        for traj in self.trajectories:
            horizon = len(traj.states)
            batch_size = traj.states[0][0].shape[0] if traj.states else 0
            total += horizon * batch_size
        return total

    def clear(self):
        """Clear all stored trajectories."""
        self.trajectories.clear()
        self.position = 0

    def get_stats(self) -> dict:
        """Get buffer statistics."""
        if not self.trajectories:
            return {
                "num_trajectories": 0,
                "total_transitions": 0,
                "avg_return": 0.0,
                "avg_trajectory_length": 0
            }

        all_returns = []
        total_steps = 0
        for traj in self.trajectories:
            all_returns.append(traj.returns.mean().item())
            total_steps += len(traj.states)

        return {
            "num_trajectories": len(self.trajectories),
            "total_transitions": self.total_transitions(),
            "avg_return": sum(all_returns) / len(all_returns),
            "avg_trajectory_length": total_steps / len(self.trajectories)
        }

#!/usr/bin/env python
"""Test script for DreamerV4 features in value network."""

import torch
from signamancy.agent.value_network import (
    symlog, symexp, TwohotDistribution, ValueNetwork, ValueNetworkConfig
)


def test_symlog_symexp():
    """Test symlog/symexp transformations."""
    print('Testing symlog/symexp...')
    x = torch.tensor([-1000.0, -1.0, 0.0, 1.0, 1000.0])
    y = symlog(x)
    z = symexp(y)
    print(f'  x: {x.tolist()}')
    print(f'  symlog(x): {y.tolist()}')
    print(f'  symexp(symlog(x)): {z.tolist()}')
    assert torch.allclose(x, z, rtol=1e-5), 'symlog/symexp roundtrip failed'
    print('  OK!')


def test_twohot_distribution():
    """Test TwohotDistribution encoding/decoding."""
    print('Testing TwohotDistribution...')
    twohot = TwohotDistribution(num_buckets=51, low=-10.0, high=10.0, use_symlog=True)
    values = torch.tensor([0.0, 100.0, -100.0, 1.0, -1.0])
    encoded = twohot.encode(values)
    print(f'  values: {values.tolist()}')
    print(f'  encoded shape: {encoded.shape}')
    print(f'  encoded sum: {encoded.sum(dim=1).tolist()} (should be all 1s)')
    assert torch.allclose(encoded.sum(dim=1), torch.ones(5)), 'Twohot encoding should sum to 1'

    # Test decode (with fake logits)
    logits = torch.zeros(5, 51)
    logits[:, 25] = 10.0  # Center bucket
    decoded = twohot.decode(logits)
    print(f'  decoded (center bucket): {decoded.tolist()}')
    print('  OK!')


def test_value_network():
    """Test ValueNetwork with DreamerV4 features."""
    print('Testing ValueNetwork...')
    config = ValueNetworkConfig(
        hidden_dim=64,
        use_symlog=True,
        use_twohot=True,
        twohot_buckets=51
    )
    net = ValueNetwork(bit_dim=10, byte_dim=20, float_dim=5, config=config)
    print(f'  Network created with twohot={config.use_twohot}')
    print(f'  Value head output dim: {net.value_head.out_features}')

    # Test forward pass
    bit = torch.randn(4, 10)
    byte = torch.randn(4, 20)
    float_b = torch.randn(4, 5)
    values = net(bit, byte, float_b)
    print(f'  Forward pass output shape: {values.shape}')
    assert values.shape == (4,), 'Value output should be [batch]'

    # Test compute_loss
    targets = torch.tensor([0.0, 10.0, -10.0, 100.0])
    loss = net.compute_loss(bit, byte, float_b, targets)
    print(f'  Loss: {loss.item():.4f}')
    print('  OK!')


def test_value_network_scalar():
    """Test ValueNetwork without twohot (scalar output)."""
    print('Testing ValueNetwork (scalar mode)...')
    config = ValueNetworkConfig(
        hidden_dim=64,
        use_symlog=True,
        use_twohot=False
    )
    net = ValueNetwork(bit_dim=10, byte_dim=20, float_dim=5, config=config)
    print(f'  Network created with twohot={config.use_twohot}')
    print(f'  Value head output dim: {net.value_head.out_features}')

    # Test forward pass
    bit = torch.randn(4, 10)
    byte = torch.randn(4, 20)
    float_b = torch.randn(4, 5)
    values = net(bit, byte, float_b)
    print(f'  Forward pass output shape: {values.shape}')
    assert values.shape == (4,), 'Value output should be [batch]'
    print('  OK!')


if __name__ == '__main__':
    print('=' * 60)
    print('DreamerV4 Feature Tests')
    print('=' * 60)
    print()

    test_symlog_symexp()
    print()

    test_twohot_distribution()
    print()

    test_value_network()
    print()

    test_value_network_scalar()
    print()

    print('=' * 60)
    print('All DreamerV4 features working correctly!')
    print('=' * 60)

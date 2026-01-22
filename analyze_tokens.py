#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Analyze token type classifications in farm recipes."""

from signamancy.parser import SignamancyParser
from signamancy.registry import TokenRegistry, BlockType

# Load farm recipes
with open('games/farm/recipes.csv', 'r', encoding='utf-8') as f:
    text = f.read()

registry = TokenRegistry()
parser = SignamancyParser(registry)
rules = parser.parse_text(text)
registry.compile_layout()

# Group tokens by type
bits = []
bytes_t = []
floats = []

for gid, meta in registry._tokens.items():
    if meta.original_text.startswith('__'): continue
    if meta.block_type == BlockType.BIT:
        bits.append((meta.original_text, meta.usage_count))
    elif meta.block_type == BlockType.BYTE:
        bytes_t.append((meta.original_text, meta.usage_count))
    else:
        floats.append((meta.original_text, meta.usage_count))

print('=== BIT (Boolean) Tokens ===')
for t, c in sorted(bits, key=lambda x: -x[1])[:50]:
    print(f'  {t}: {c} uses')

print()
print(f'Total BIT: {len(bits)}, BYTE: {len(bytes_t)}, FLOAT: {len(floats)}')

print()
print('=== BYTE Tokens ===')
for t, c in sorted(bytes_t, key=lambda x: -x[1])[:30]:
    print(f'  {t}: {c} uses')

print()
print('=== FLOAT Tokens ===')
for t, c in sorted(floats, key=lambda x: -x[1])[:30]:
    print(f'  {t}: {c} uses')

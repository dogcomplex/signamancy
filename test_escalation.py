#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test accumulator token escalation."""
from signamancy.parser import SignamancyParser
from signamancy.registry import TokenRegistry, BlockType
import csv

registry = TokenRegistry()
parser = SignamancyParser(registry)
rules = []

with open('games/farm/recipes.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        recipe = row.get('Recipe') or ''
        recipe = recipe.strip()
        if recipe:
            rules.extend(parser.parse_text(recipe))

# Apply escalation
parser._escalate_accumulator_tokens(rules)
registry.compile_layout()

# Check crown classification
crown_id = registry.get_id('\U0001F451')  # 👑
crown_meta = registry.get_metadata(crown_id)
print(f'Crown (👑) classification: {crown_meta.block_type.name if crown_meta else "NOT FOUND"}')
print(f'Crown usage count: {crown_meta.usage_count if crown_meta else 0}')

# Show all BIT tokens
print()
print('Current BIT tokens:')
bits = [(m.original_text, m.usage_count) for m in registry._tokens.values()
        if m.block_type == BlockType.BIT and not m.original_text.startswith('__')]
for t, c in sorted(bits, key=lambda x: -x[1])[:20]:
    print(f'  {t}: {c} uses')
print(f'\nTotal BIT tokens: {len(bits)}')

# Show BYTE tokens that were escalated
print()
print('BYTE tokens (includes escalated):')
bytes_t = [(m.original_text, m.usage_count) for m in registry._tokens.values()
           if m.block_type == BlockType.BYTE and not m.original_text.startswith('__')]
for t, c in sorted(bytes_t, key=lambda x: -x[1])[:20]:
    print(f'  {t}: {c} uses')
print(f'\nTotal BYTE tokens: {len(bytes_t)}')

#!/usr/bin/env python
"""Debug script for comparing policies."""
import sys
import re
from pathlib import Path

def compare_policies(old_path, new_path):
    old = Path(old_path).read_text(encoding='utf-8')
    new = Path(new_path).read_text(encoding='utf-8')

    # Extract the main bias line
    old_lines = [l for l in old.splitlines() if l.startswith('❗ ♥')]
    new_lines = [l for l in new.splitlines() if l.startswith('❗ ♥')]

    print(f'Old bias line length: {len(old_lines[0]) if old_lines else 0}')
    print(f'New bias line length: {len(new_lines[0]) if new_lines else 0}')

    # Compare tokens
    old_tokens = set(re.findall(r'♥ID_[^\s]+', old_lines[0])) if old_lines else set()
    new_tokens = set(re.findall(r'♥ID_[^\s]+', new_lines[0])) if new_lines else set()

    print()
    print(f'Old tokens: {len(old_tokens)}')
    print(f'New tokens: {len(new_tokens)}')

    print()
    print('In old but not new:')
    for t in sorted(old_tokens - new_tokens):
        print(f'  {t}')

    print()
    print('In new but not old:')
    for t in sorted(new_tokens - old_tokens):
        print(f'  {t}')

def load_and_inspect(policy_path):
    from signamancy.agent.policy import PolicyManager
    pm = PolicyManager()
    pm.load_sheet(Path(policy_path))
    print(f'Policy: {policy_path}')
    print(f'  Rule desires: {len(pm.rule_desires)}')
    print(f'  Token desires: {len(pm.token_desires)}')
    print(f'  Targets: {pm.targets}')
    violations = pm.verify_sheet(Path(policy_path))
    print(f'  Violations: {len(violations)}')
    for v in violations[:5]:
        print(f'    {v}')
    return pm

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python debug_policy.py <command> [args]')
        print('Commands:')
        print('  compare <old> <new>  - Compare two policy files')
        print('  inspect <policy>     - Inspect a single policy')
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == 'compare':
        compare_policies(sys.argv[2], sys.argv[3])
    elif cmd == 'inspect':
        load_and_inspect(sys.argv[2])
    else:
        print(f'Unknown command: {cmd}')

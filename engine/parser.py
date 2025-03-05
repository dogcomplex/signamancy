import sys
import os
import re
from pathlib import Path

def extract_quantity(token):
    """Extract numeric quantity from token if present"""
    # Match patterns like:
    # - Basic numbers: 1, 10, 100
    # - Decimals: 0.1, .3
    # - Units: k, m, b, t
    # - Compound units: k_tons, m_m2, b_tons/yr
    # - Special units: KW, MW, GW, TW
    # - Time units: ms, hr, yr
    pattern = r'^(\d*\.?\d+)(.*?)$'
    
    # Special case for standalone units without numbers
    if token in ['tons', 'States', 'm/s']:
        return '', token
        
    match = re.match(pattern, token)
    if match:
        quantity, rest = match.groups()
        return quantity, rest
    return '', token

def is_emoji(char):
    """Check if a character is likely an emoji"""
    return not (char.isalnum() or char.isspace() or char == '_' or char == '.')

def extract_emojis(token):
    """Extract leading emojis from token"""
    # Find where the emojis end
    emoji_end = 0
    for i, char in enumerate(token):
        if not is_emoji(char):
            emoji_end = i
            break
    else:
        # If we get here, the whole token might be emojis
        emoji_end = len(token)
    
    if emoji_end == 0:
        return '', token
    
    emojis = token[:emoji_end]
    rest = token[emoji_end:]
    
    # Debug print
    # print(f"Token: '{token}', Emojis: '{emojis}', Rest: '{rest}'")
    
    return emojis, rest

def clean_token(token):
    """Clean a token by removing extra whitespace but preserving underscores"""
    return token.strip()

def standardize_line(tokens):
    """Convert tokens to standardized format with double spaces"""
    return '  '.join(clean_token(t) for t in tokens if t.strip())

def parse_recipe_line(line):
    """Parse a single recipe line, returning (is_alias, parsed_line, tokens) or (None, None, []) if invalid"""
    # Skip empty lines and comments
    if not line.strip() or line.strip().startswith('#'):
        return None, None, []
    
    tokens = []
    
    # Handle property definitions (contains :>)
    if ':>' in line:
        parts = line.split(':>')
        if len(parts) != 2:
            return None, None, []
        left_token = clean_token(parts[0])
        tokens.append(left_token)
        tokens.extend(clean_token(t) for t in parts[1].strip().split())
        return False, standardize_line([left_token, ':>'] + parts[1].strip().split()), tokens
    
    # Handle equivalence (<=>)
    if '<=>' in line:
        parts = line.split('<=>')
        if len(parts) != 2:
            return None, None, []
        left_tokens = parts[0].strip().split()
        right_tokens = parts[1].strip().split()
        tokens.extend(clean_token(t) for t in left_tokens + right_tokens)
        return True, standardize_line(left_tokens + ['<=>'] + right_tokens), tokens
    
    # Handle transformations (=>)
    if '=>' in line:
        parts = line.split('=>')
        if len(parts) != 2:
            return None, None, []
        left_tokens = parts[0].strip().split()
        right_tokens = parts[1].strip().split()
        tokens.extend(clean_token(t) for t in left_tokens + right_tokens)
        return False, standardize_line(left_tokens + ['=>'] + right_tokens), tokens
    
    return None, None, []

def extract_time_unit(token):
    """Extract time unit from token if present (e.g., '/yr', '/day')"""
    if '/' not in token:
        return ''
    parts = token.split('/')
    if len(parts) != 2:
        return ''
    return f"/{parts[1]}"

def analyze_operation_units(line):
    """Analyze operation line for units and common symbols"""
    if '=>' not in line:
        return None
    
    parts = line.split('=>')
    if len(parts) != 2:
        return None
        
    left_tokens = [t.strip() for t in parts[0].split() if t.strip() and t not in ['=>']]
    right_tokens = [t.strip() for t in parts[1].split() if t.strip()]
    
    # Get base symbols (without quantities/units)
    left_symbols = {t: extract_emojis(t)[0] for t in left_tokens}
    right_symbols = {t: extract_emojis(t)[0] for t in right_tokens}
    
    # Get tokens by their emoji
    left_by_emoji = {}
    right_by_emoji = {}
    for token, emoji in left_symbols.items():
        left_by_emoji.setdefault(emoji, []).append(token)
    for token, emoji in right_symbols.items():
        right_by_emoji.setdefault(emoji, []).append(token)
    
    # Check for at least one common symbol
    common_emojis = set(left_by_emoji.keys()) & set(right_by_emoji.keys())
    if not common_emojis:
        return None
    
    # Get all unique time units, excluding tokens with common emojis
    all_tokens = []
    for token in left_tokens + right_tokens:
        emoji = extract_emojis(token)[0]
        if emoji not in common_emojis:
            all_tokens.append(token)
            
    time_units = set(extract_time_unit(token) for token in all_tokens)
    
    return time_units

def main():
    # Get input file from args or use default
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'input.md'
    
    # Create output directories if they don't exist
    output_dir = Path('output/parsed')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize line collections
    valid_lines = []
    valid_build_lines = []
    valid_operation_lines = []
    valid_properties_lines = []
    valid_alias_lines = []
    invalid_lines = []
    
    # Track unique tokens and their indices
    token_indices = {}
    next_index = 1
    
    current_section = None
    
    # After reading input file but before processing tokens, add:
    token_line_numbers = {}  # Store line numbers for each token
    operation_by_units = {}
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            # Check for section markers
            if line.startswith('#'):
                lower_line = line.lower()
                if 'build:' in lower_line:
                    current_section = 'build'
                elif 'operation:' in lower_line:
                    current_section = 'operation'
                elif 'properties:' in lower_line:
                    current_section = 'property'
                elif 'resources:' in lower_line:
                    current_section = None  # Reset section for resources
                elif ':' not in lower_line and '#' in line:  # Any other section header
                    current_section = None  # Reset for other sections
                continue
            
            is_alias, parsed, tokens = parse_recipe_line(line)
            
            if parsed:
                valid_lines.append(f"{parsed}\n")
                
                # Add new tokens to index
                for token in tokens:
                    if token not in token_indices and not token.startswith((':', '<', '=')):
                        token_indices[token] = next_index
                        next_index += 1
                
                if is_alias:
                    valid_alias_lines.append(f"{parsed}\n")
                elif current_section == 'build':
                    valid_build_lines.append(f"{parsed}\n")
                elif current_section == 'operation':
                    time_units = analyze_operation_units(parsed)
                    if time_units is not None:
                        units_key = tuple(sorted(time_units))
                        if units_key not in operation_by_units:
                            operation_by_units[units_key] = []
                        operation_by_units[units_key].append(f"{parsed}\n")
                    else:
                        invalid_lines.append(f"Line {line_num}: {line} (No common symbols between sides)\n")
                    valid_operation_lines.append(f"{parsed}\n")
                elif current_section == 'property':
                    valid_properties_lines.append(f"{parsed}\n")
            else:
                invalid_lines.append(f"Line {line_num}: {line}\n")
            
            # Track line numbers for each token
            for token in tokens:
                if token not in token_line_numbers:  # Keep first occurrence
                    token_line_numbers[token] = line_num
    
    # Group tokens by emojis for the new file
    emoji_groups = {}
    no_emoji_group = []
    
    for token, index in token_indices.items():
        emojis, _ = extract_emojis(token)
        if emojis:
            if emojis not in emoji_groups:
                emoji_groups[emojis] = []
            emoji_groups[emojis].append((token, index))
        else:
            no_emoji_group.append((token, index))
    
    # Sort emoji groups by their lowest token index
    sorted_emoji_groups = sorted(
        emoji_groups.items(),
        key=lambda x: min(index for _, index in x[1])
    )
    
    # Group tokens by labels
    label_groups = {}
    no_label_group = []
    
    for token, index in token_indices.items():
        emojis, remainder = extract_emojis(token)
        quantity, label_remainder = extract_quantity(remainder)
        clean_label = label_remainder.lstrip('_') if label_remainder else ''
        
        if clean_label:
            if clean_label not in label_groups:
                label_groups[clean_label] = []
            label_groups[clean_label].append((token, index))
        else:
            no_label_group.append((token, index))
    
    # Sort label groups by their lowest token index
    sorted_label_groups = sorted(
        label_groups.items(),
        key=lambda x: min(index for _, index in x[1])
    )
    
    # Write output files
    files_to_write = {
        'valid.md': valid_lines,
        'valid_build.md': valid_build_lines,
        'valid_operation.md': valid_operation_lines,
        'valid_properties.md': valid_properties_lines,
        'valid_aliases.md': valid_alias_lines,
        'invalid.md': invalid_lines
    }
    
    for filename, lines in files_to_write.items():
        with open(output_dir / filename, 'w', encoding='utf-8') as f:
            if lines:  # Only write header if file has content
                f.write(f"# {filename[:-3].replace('_', ' ').title()}\n\n")
            f.writelines(lines)
    
    def format_token_line(token, index):
        """Generate consistent token line output for both index files"""
        emojis, remainder = extract_emojis(token)
        quantity, label_remainder = extract_quantity(remainder)
        
        # Standardize decimal notation
        if quantity and quantity.startswith('.'):
            quantity = '0' + quantity
        
        output_parts = [f"{token}  :>  🆔{index}"]
        if quantity:
            output_parts.append(f" 🔢{quantity}")
        if emojis:
            output_parts.append(f" 🙂{emojis}")
        if label_remainder:
            clean_label = label_remainder.lstrip('_')
            if clean_label:
                output_parts.append(f" 🏷{clean_label}")
        if token in token_line_numbers:
            output_parts.append(f" #️⃣{token_line_numbers[token]}")
        return f"{' '.join(output_parts)}\n"
    
    # Write valid_tokens_indexed.md
    with open(output_dir / 'valid_tokens_indexed.md', 'w', encoding='utf-8') as f:
        f.write("# Valid Indexes\n\n")
        for token, index in sorted(token_indices.items(), key=lambda x: x[1]):
            f.write(format_token_line(token, index))
        f.write("\n")

    # Write valid_tokens_indexed_by_emojis.md
    with open(output_dir / 'valid_tokens_indexed_by_emojis.md', 'w', encoding='utf-8') as f:
        f.write("# Valid Indexes By Emojis\n\n")
        
        # Write tokens with no emojis first
        if no_emoji_group:
            f.write("## No Emojis\n\n")
            for token, index in sorted(no_emoji_group, key=lambda x: x[1]):
                f.write(format_token_line(token, index))
            f.write("\n")
        
        # Write emoji groups
        for emojis, tokens in sorted_emoji_groups:
            f.write(f"## Emoji Group: {emojis}\n\n")
            for token, index in sorted(tokens, key=lambda x: x[1]):
                f.write(format_token_line(token, index))
            f.write("\n")

    # Write valid_tokens_indexed_by_label.md
    with open(output_dir / 'valid_tokens_indexed_by_label.md', 'w', encoding='utf-8') as f:
        f.write("# Valid Indexes By Label\n\n")
        
        # Write tokens with no label first
        if no_label_group:
            f.write("## No Label\n\n")
            for token, index in sorted(no_label_group, key=lambda x: x[1]):
                f.write(format_token_line(token, index))
            f.write("\n")
        
        # Write label groups
        for label, tokens in sorted_label_groups:
            f.write(f"## Label: {label}\n\n")
            for token, index in sorted(tokens, key=lambda x: x[1]):
                f.write(format_token_line(token, index))
            f.write("\n")

    # Write valid_operation_by_unit.md
    with open(output_dir / 'valid_operation_by_unit.md', 'w', encoding='utf-8') as f:
        f.write("# Valid Operations By Unit\n\n")
        
        # Sort by number of unique units descending
        sorted_units = sorted(operation_by_units.keys(), 
                            key=lambda x: (-len(x), x))
        
        for units in sorted_units:
            if units:
                unit_str = ', '.join(units) if units else 'No time units'
            else:
                unit_str = 'No time units'
            
            f.write(f"## Operations with units: {unit_str}\n\n")
            f.writelines(operation_by_units[units])
            f.write("\n")

if __name__ == '__main__':
    main()

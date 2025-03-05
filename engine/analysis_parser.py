import re
from pathlib import Path

INCLUDE_THINK_TAGS = False

def extract_accuracy(text):
    """Extract accuracy score from analysis text, normalized to decimal form."""
    # Look for accuracy score patterns
    accuracy_patterns = [
        r'ACCURACY:\s*(\d+)(?:/10)?',  # Matches "ACCURACY: 7" or "ACCURACY: 7/10"
        r'ACCURACY:\s*(\d+\.\d+)',     # Matches "ACCURACY: 7.5"
    ]
    
    for pattern in accuracy_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            score = float(match.group(1))
            return score
            
    return None

def parse_analysis_file(input_path):
    """Parse analysis file and return list of (section_text, accuracy) tuples."""
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split content into sections based on "## Input"
    sections = re.split(r'(?=## Input)', content)
    
    analyzed_sections = []
    for section in sections:
        if not section.strip():
            continue
            
        accuracy = extract_accuracy(section)
        if accuracy is not None:
            analyzed_sections.append((section.strip(), accuracy))
            
    return analyzed_sections

def write_filtered_sections(sections, output_path):
    """Write sections to output file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        for section, _ in sections:
            content = section
            if not INCLUDE_THINK_TAGS:
                # Remove <think> tags and their content
                content = re.sub(r'<think>.*?</think>\s*', '', content, flags=re.DOTALL)
            f.write(content + '\n\n')

def main():
    # Setup paths
    input_path = Path('output/semantics/single_analysis.md')
    output_high = Path('output/semantics/single_analysis_8_up.md')
    output_low = Path('output/semantics/single_analysis_8_down.md')
    
    # Create output directory if it doesn't exist
    output_high.parent.mkdir(parents=True, exist_ok=True)
    
    # Parse and filter sections
    sections = parse_analysis_file(input_path)
    
    # Split into high and low accuracy sections
    high_accuracy = [(text, score) for text, score in sections if score >= 8]
    low_accuracy = [(text, score) for text, score in sections if score < 8]
    
    # Write filtered content to respective files
    write_filtered_sections(high_accuracy, output_high)
    write_filtered_sections(low_accuracy, output_low)
    
    # Print summary
    print(f"Found {len(sections)} total sections")
    print(f"High accuracy (≥8): {len(high_accuracy)} sections")
    print(f"Low accuracy (<8): {len(low_accuracy)} sections")

if __name__ == "__main__":
    main()

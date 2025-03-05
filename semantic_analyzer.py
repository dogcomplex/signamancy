import json
import os
import requests
import sys
from pathlib import Path

def load_progress():
    """Load progress from progress.json"""
    try:
        with open('progress.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'last_line': 0}

def save_progress(line_number):
    """Save progress to progress.json"""
    with open('progress.json', 'w', encoding='utf-8') as f:
        json.dump({'last_line': line_number}, f)

def load_system_prompt():
    """Load the system prompt from the specified file"""
    with open('prompts/analysis_single.md', 'r', encoding='utf-8') as f:
        return f.read()

def append_to_analysis(content):
    """Append content to the analysis file"""
    os.makedirs('output/semantics', exist_ok=True)
    with open('output/semantics/single_analysis.md', 'a', encoding='utf-8') as f:
        f.write(content + '\n\n')

def query_llm(prompt, system_prompt):
    """Query the local LLM"""
    url = "http://192.168.56.1:12345/v1/chat/completions"
    
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "model": "deepseek-r1-distill-qwen-14b"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        print(f"Error querying LLM: {e}")
        return None

def parse_input_file(file_path, start_line):
    """Parse input file and yield sections"""
    current_section = []
    line_count = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line_count += 1
            if line_count <= start_line:
                continue
                
            if line.strip().startswith('# Original:') and current_section:
                yield '\n'.join(current_section), line_count - len(current_section)
                current_section = []
            
            current_section.append(line.strip())
            
    if current_section:
        yield '\n'.join(current_section), line_count - len(current_section)

def main():
    if len(sys.argv) != 2:
        print("Usage: python semantic_analyzer.py <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    progress = load_progress()
    system_prompt = load_system_prompt()
    
    for section, start_line in parse_input_file(input_file, progress['last_line']):
        if not section.strip():
            continue
            
        # Analyze the section
        analysis = query_llm(section, system_prompt)
        if analysis:
            # Format the output
            output = f"## Input (starting line {start_line}):\n{section}\n\n## Analysis:\n{analysis}"
            append_to_analysis(output)
            
        # Save progress
        save_progress(start_line + len(section.splitlines()))
        
    print("Analysis complete")

if __name__ == "__main__":
    main() 
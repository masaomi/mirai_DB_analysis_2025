#!/usr/bin/env python3
"""
Fix HTML files in survey_summaries_html/ directory
Converts markdown-like content in summary sections to proper HTML
"""

import os
import re
from pathlib import Path

def convert_markdown_to_html(markdown_text: str) -> str:
    """Convert markdown to proper HTML."""
    lines = markdown_text.split('\n')
    html_lines = []
    in_list = False
    in_paragraph = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            if in_paragraph:
                html_lines.append('</p>')
                in_paragraph = False
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            i += 1
            continue
        
        # Headers (remove # symbols)
        if stripped.startswith('#### '):
            if in_paragraph:
                html_lines.append('</p>')
                in_paragraph = False
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h4>{stripped[5:]}</h4>')
        elif stripped.startswith('### '):
            if in_paragraph:
                html_lines.append('</p>')
                in_paragraph = False
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h3>{stripped[4:]}</h3>')
        elif stripped.startswith('## '):
            if in_paragraph:
                html_lines.append('</p>')
                in_paragraph = False
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h2>{stripped[3:]}</h2>')
        elif stripped.startswith('# '):
            if in_paragraph:
                html_lines.append('</p>')
                in_paragraph = False
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h2>{stripped[2:]}</h2>')
        
        # Lists
        elif stripped.startswith('- ') or stripped.startswith('* '):
            if in_paragraph:
                html_lines.append('</p>')
                in_paragraph = False
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            # Process bold and italic in list items
            item_text = stripped[2:]
            item_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', item_text)
            item_text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', item_text)
            html_lines.append(f'<li>{item_text}</li>')
        
        # Tables
        elif '|' in stripped and i + 1 < len(lines) and '|' in lines[i + 1]:
            if in_paragraph:
                html_lines.append('</p>')
                in_paragraph = False
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            
            # Start table
            html_lines.append('<table>')
            html_lines.append('<thead><tr>')
            
            # Header row
            cells = [cell.strip() for cell in stripped.split('|') if cell.strip()]
            for cell in cells:
                cell_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', cell)
                html_lines.append(f'<th>{cell_text}</th>')
            html_lines.append('</tr></thead>')
            html_lines.append('<tbody>')
            
            # Skip separator line
            i += 1
            if i < len(lines) and '|' in lines[i] and '-' in lines[i]:
                i += 1
            
            # Process table rows
            while i < len(lines) and '|' in lines[i]:
                row = lines[i].strip()
                if row:
                    html_lines.append('<tr>')
                    cells = [cell.strip() for cell in row.split('|') if cell.strip()]
                    for cell in cells:
                        cell_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', cell)
                        html_lines.append(f'<td>{cell_text}</td>')
                    html_lines.append('</tr>')
                i += 1
            
            html_lines.append('</tbody></table>')
            continue
        
        # Regular paragraphs
        else:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            if not in_paragraph:
                html_lines.append('<p>')
                in_paragraph = True
            
            # Process bold and italic
            text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped)
            text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
            html_lines.append(text)
        
        i += 1
    
    # Close any open tags
    if in_paragraph:
        html_lines.append('</p>')
    if in_list:
        html_lines.append('</ul>')
    
    return '\n'.join(html_lines)


def extract_raw_markdown(html_content: str) -> str:
    """Extract the raw markdown-like text from broken HTML."""
    # Find the summary section
    summary_match = re.search(r'<div class="summary">(.*?)</div>\s*<div class="statistics">', html_content, re.DOTALL)
    if not summary_match:
        print("Warning: Could not find summary section")
        return None
    
    summary_html = summary_match.group(1)
    
    # Remove all HTML tags to get raw text
    text = re.sub(r'<[^>]+>', '', summary_html)
    
    # Clean up HTML entities
    text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    
    # Fix # markers that are stuck together with text
    # Example: "text#1. Header" -> "text\n# 1. Header"
    text = re.sub(r'([^\n])#(\d+\.)', r'\1\n\n# \2', text)
    text = re.sub(r'([^\n])(#{1,4})\s', r'\1\n\n\2 ', text)
    
    # Ensure list items are on separate lines
    text = re.sub(r'([^\n])\s*-\s+', r'\1\n- ', text)
    
    # Clean up excessive whitespace
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = text.strip()
    
    # Remove the first "📝 要約レポート" if present
    text = re.sub(r'^📝\s*要約レポート\s*', '', text, flags=re.MULTILINE)
    
    return text


def fix_html_file(filepath: Path):
    """Fix a single HTML file."""
    print(f"Processing: {filepath.name}")
    
    try:
        # Read the file
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract raw markdown
        raw_markdown = extract_raw_markdown(content)
        if not raw_markdown:
            print(f"  ⚠️  Skipped: Could not extract content")
            return False
        
        # Convert to proper HTML
        proper_html = convert_markdown_to_html(raw_markdown)
        
        # Replace the summary section
        # Find the summary div
        pattern = r'(<div class="summary">.*?<h1>📝 要約レポート</h1>\s*)(.*?)(\s*</div>\s*<div class="statistics">)'
        
        def replacement(match):
            return match.group(1) + '\n' + proper_html + '\n    ' + match.group(3)
        
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # Write back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"  ✅ Fixed successfully")
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    html_dir = Path("survey_summaries_html")
    
    if not html_dir.exists():
        print(f"❌ Directory not found: {html_dir}")
        return
    
    print("🔧 Fixing HTML files in survey_summaries_html/")
    print("=" * 60)
    
    # Get all HTML files except index.html
    html_files = [f for f in html_dir.glob("*.html") if f.name != "index.html"]
    
    print(f"Found {len(html_files)} HTML files to fix\n")
    
    fixed_count = 0
    for filepath in sorted(html_files):
        if fix_html_file(filepath):
            fixed_count += 1
        print()
    
    print("=" * 60)
    print(f"✅ Fixed {fixed_count} out of {len(html_files)} files")
    print("\nTo view results:")
    print("  open survey_summaries_html/index.html")


if __name__ == "__main__":
    main()


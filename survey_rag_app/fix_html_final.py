#!/usr/bin/env python3
"""
Final HTML fix script - thoroughly cleans and structures all HTML files
"""

import os
import re
from pathlib import Path

def clean_and_structure_summary(raw_text: str) -> str:
    """Clean and properly structure the summary text."""
    lines = raw_text.split('\n')
    result_lines = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        # Section headers (#数字.)
        if re.match(r'^#?\s*\d+\.\s+', line):
            # Remove # and make it a header
            header_text = re.sub(r'^#?\s*(\d+\.\s+.+)$', r'\1', line)
            result_lines.append(f'<h2>{header_text}</h2>')
            result_lines.append('')
        
        # Sub-section headers with bold
        elif line.startswith('**') and line.endswith('**'):
            text = line.strip('*')
            result_lines.append(f'<h3>{text}</h3>')
        
        # List items starting with - or *
        elif re.match(r'^[-*]\s+', line):
            # Check if we need to start a list
            if not result_lines or not result_lines[-1].startswith('<li>'):
                if result_lines and result_lines[-1] != '<ul>':
                    result_lines.append('<ul>')
            
            # Clean the list item
            item_text = re.sub(r'^[-*]\s+', '', line)
            # Handle bold
            item_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', item_text)
            # Handle italic/quotes
            item_text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', item_text)
            result_lines.append(f'<li>{item_text}</li>')
        
        # Table rows (containing |)
        elif '|' in line:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells:
                # Skip separator lines
                if all(re.match(r'^-+$', c) for c in cells):
                    continue
                
                # Check if this is a header row (look at next line)
                is_header = False
                if i + 1 < len(lines) and '---' in lines[i + 1]:
                    is_header = True
                    if result_lines and result_lines[-1] != '<table>':
                        result_lines.append('<table>')
                    result_lines.append('<thead><tr>')
                    for cell in cells:
                        cell_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', cell)
                        result_lines.append(f'<th>{cell_text}</th>')
                    result_lines.append('</tr></thead>')
                    result_lines.append('<tbody>')
                else:
                    # Data row
                    if result_lines and '<table>' not in '\n'.join(result_lines[-10:]):
                        result_lines.append('<table>')
                        result_lines.append('<tbody>')
                    result_lines.append('<tr>')
                    for cell in cells:
                        cell_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', cell)
                        result_lines.append(f'<td>{cell_text}</td>')
                    result_lines.append('</tr>')
        
        # Regular paragraph
        else:
            # Close list if needed
            if result_lines and result_lines[-1].startswith('<li>'):
                result_lines.append('</ul>')
                result_lines.append('')
            
            # Close table if needed
            if result_lines and ('<tr>' in result_lines[-1] or '<td>' in result_lines[-1]):
                result_lines.append('</tbody></table>')
                result_lines.append('')
            
            # Process inline formatting
            text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
            
            # Start new paragraph if needed
            if not result_lines or result_lines[-1] == '' or result_lines[-1].startswith('<'):
                result_lines.append(f'<p>{text}</p>')
            else:
                result_lines.append(text)
    
    # Close any open tags
    if result_lines and result_lines[-1].startswith('<li>'):
        result_lines.append('</ul>')
    if result_lines and ('<tr>' in result_lines[-1] or '<td>' in result_lines[-1]):
        result_lines.append('</tbody></table>')
    
    # Join and clean up
    html = '\n'.join(result_lines)
    
    # Remove multiple consecutive empty lines
    html = re.sub(r'\n\n\n+', '\n\n', html)
    
    return html


def fix_html_file(filepath: Path):
    """Fix a single HTML file."""
    print(f"Processing: {filepath.name}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the summary section
        summary_match = re.search(
            r'(<div class="summary">.*?<h1>📝 要約レポート</h1>\s*)(.*?)(\s*</div>\s*<div class="statistics">)',
            content,
            re.DOTALL
        )
        
        if not summary_match:
            print(f"  ⚠️  Skipped: Could not find summary section")
            return False
        
        # Extract raw text from summary
        summary_html = summary_match.group(2)
        raw_text = re.sub(r'<[^>]+>', '\n', summary_html)
        raw_text = raw_text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        
        # Clean and structure
        cleaned_html = clean_and_structure_summary(raw_text)
        
        # Rebuild the file
        new_content = (
            summary_match.group(1) + '\n' +
            cleaned_html + '\n    ' +
            summary_match.group(3)
        )
        
        # Replace in full content
        new_full_content = content[:summary_match.start()] + new_content + content[summary_match.end():]
        
        # Add table styling to CSS if not present
        if '.summary table {' not in new_full_content:
            css_addition = """
        .summary table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        .summary th, .summary td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .summary th {
            background-color: #f0f0f0;
            color: #333;
            font-weight: bold;
        }
        .summary tr:hover {
            background-color: #f9f9f9;
        }
        .summary p {
            margin: 15px 0;
        }
        .summary ul {
            margin: 15px 0;
        }
        .summary h2 {
            margin-top: 30px;
            margin-bottom: 15px;
        }
        .summary h3 {
            margin-top: 20px;
            margin-bottom: 10px;
        }"""
            # Insert before </style>
            new_full_content = new_full_content.replace('</style>', css_addition + '\n    </style>')
        
        # Write back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_full_content)
        
        print(f"  ✅ Fixed successfully")
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    html_dir = Path("survey_summaries_html")
    
    if not html_dir.exists():
        print(f"❌ Directory not found: {html_dir}")
        return
    
    print("🔧 Final HTML Fix - Cleaning and Structuring")
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










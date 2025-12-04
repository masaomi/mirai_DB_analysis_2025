#!/usr/bin/env python3
"""
Convert Markdown reports to HTML and PDF formats.

This script converts Markdown reports into styled HTML and PDF documents
with proper Japanese font support.
"""

import argparse
from pathlib import Path
from typing import Optional
import markdown
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

from config import get_output_dir


# HTML template with styling
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {css}
    </style>
</head>
<body>
    <div class="container">
        {content}
    </div>
</body>
</html>
"""


# Modern CSS styling
MODERN_CSS = """
body {
    font-family: "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Meiryo", 
                 "Yu Gothic", sans-serif;
    line-height: 1.8;
    color: #333;
    background-color: #f5f5f5;
    margin: 0;
    padding: 20px;
}

.container {
    max-width: 900px;
    margin: 0 auto;
    background-color: white;
    padding: 40px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    border-radius: 8px;
}

h1 {
    color: #2c3e50;
    border-bottom: 3px solid #3498db;
    padding-bottom: 10px;
    margin-top: 0;
    font-size: 2.2em;
}

h2 {
    color: #34495e;
    border-bottom: 2px solid #95a5a6;
    padding-bottom: 8px;
    margin-top: 40px;
    font-size: 1.8em;
}

h3 {
    color: #555;
    margin-top: 30px;
    font-size: 1.4em;
}

h4 {
    color: #666;
    margin-top: 20px;
    font-size: 1.2em;
}

p {
    margin: 15px 0;
}

ul, ol {
    margin: 15px 0;
    padding-left: 30px;
}

li {
    margin: 8px 0;
}

hr {
    border: none;
    border-top: 1px solid #ddd;
    margin: 30px 0;
}

code {
    background-color: #f4f4f4;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: "Courier New", monospace;
    font-size: 0.9em;
}

pre {
    background-color: #f4f4f4;
    padding: 15px;
    border-radius: 5px;
    overflow-x: auto;
    border-left: 4px solid #3498db;
}

pre code {
    background-color: transparent;
    padding: 0;
}

strong {
    color: #2c3e50;
    font-weight: 600;
}

a {
    color: #3498db;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

blockquote {
    border-left: 4px solid #3498db;
    padding-left: 20px;
    margin: 20px 0;
    color: #555;
    font-style: italic;
}

details {
    margin: 20px 0;
    padding: 15px;
    background-color: #f9f9f9;
    border: 1px solid #ddd;
    border-radius: 5px;
}

summary {
    cursor: pointer;
    font-weight: 600;
    color: #2c3e50;
    padding: 5px;
}

summary:hover {
    color: #3498db;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
}

th, td {
    border: 1px solid #ddd;
    padding: 12px;
    text-align: left;
}

th {
    background-color: #3498db;
    color: white;
    font-weight: 600;
}

tr:nth-child(even) {
    background-color: #f9f9f9;
}

.footer {
    margin-top: 40px;
    padding-top: 20px;
    border-top: 1px solid #ddd;
    color: #999;
    font-size: 0.9em;
    text-align: center;
}

@media print {
    body {
        background-color: white;
        padding: 0;
    }
    
    .container {
        box-shadow: none;
        padding: 20px;
    }
}
"""


# PDF-specific CSS
PDF_CSS = """
@page {
    size: A4;
    margin: 2cm;
}

body {
    font-family: "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Meiryo", 
                 "Yu Gothic", sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #333;
}

h1 {
    font-size: 24pt;
    color: #2c3e50;
    border-bottom: 3px solid #3498db;
    padding-bottom: 8px;
    page-break-after: avoid;
}

h2 {
    font-size: 18pt;
    color: #34495e;
    border-bottom: 2px solid #95a5a6;
    padding-bottom: 6px;
    margin-top: 30px;
    page-break-after: avoid;
}

h3 {
    font-size: 14pt;
    color: #555;
    margin-top: 20px;
    page-break-after: avoid;
}

h4 {
    font-size: 12pt;
    color: #666;
    page-break-after: avoid;
}

p, ul, ol {
    orphans: 3;
    widows: 3;
}

code {
    background-color: #f4f4f4;
    padding: 2px 4px;
    font-size: 9pt;
}

pre {
    background-color: #f4f4f4;
    padding: 10px;
    border-left: 3px solid #3498db;
    page-break-inside: avoid;
}

hr {
    border: none;
    border-top: 1px solid #ddd;
    margin: 20px 0;
}
"""


def markdown_to_html(
    md_file: Path,
    output_file: Optional[Path] = None,
    css: str = MODERN_CSS
) -> Path:
    """
    Convert Markdown file to HTML.
    
    Args:
        md_file: Path to Markdown file
        output_file: Optional output path (defaults to same name with .html)
        css: CSS styling to use
    
    Returns:
        Path to generated HTML file
    """
    # Read Markdown
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Convert to HTML
    html_content = markdown.markdown(
        md_content,
        extensions=[
            'extra',
            'codehilite',
            'toc',
            'tables',
            'fenced_code',
        ]
    )
    
    # Extract title (first h1)
    title = md_file.stem
    if md_content.startswith('# '):
        title = md_content.split('\n')[0].replace('# ', '').strip()
    
    # Generate full HTML
    full_html = HTML_TEMPLATE.format(
        title=title,
        css=css,
        content=html_content
    )
    
    # Determine output path
    if output_file is None:
        output_file = md_file.with_suffix('.html')
    
    # Save HTML
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    return output_file


def html_to_pdf(
    html_file: Path,
    output_file: Optional[Path] = None
) -> Path:
    """
    Convert HTML file to PDF.
    
    Args:
        html_file: Path to HTML file
        output_file: Optional output path (defaults to same name with .pdf)
    
    Returns:
        Path to generated PDF file
    """
    # Determine output path
    if output_file is None:
        output_file = html_file.with_suffix('.pdf')
    
    # Configure fonts
    font_config = FontConfiguration()
    
    # Create CSS for PDF
    css = CSS(string=PDF_CSS, font_config=font_config)
    
    # Generate PDF
    HTML(filename=str(html_file)).write_pdf(
        str(output_file),
        stylesheets=[css],
        font_config=font_config
    )
    
    return output_file


def markdown_to_pdf(
    md_file: Path,
    output_file: Optional[Path] = None
) -> Path:
    """
    Convert Markdown directly to PDF.
    
    Args:
        md_file: Path to Markdown file
        output_file: Optional output path (defaults to same name with .pdf)
    
    Returns:
        Path to generated PDF file
    """
    # First convert to HTML (temporary)
    temp_html = md_file.with_suffix('.temp.html')
    markdown_to_html(md_file, temp_html, css=PDF_CSS)
    
    # Then convert to PDF
    if output_file is None:
        output_file = md_file.with_suffix('.pdf')
    
    html_to_pdf(temp_html, output_file)
    
    # Clean up temp file
    temp_html.unlink()
    
    return output_file


def process_all_markdown_files(
    provider_name: str,
    formats: list = ['html', 'pdf']
):
    """
    Process all Markdown files for a provider.
    
    Args:
        provider_name: Name of LLM provider ("claude" or "gemini")
        formats: List of output formats to generate
    """
    print("\n" + "="*70)
    print(f"FORMAT CONVERSION - {provider_name.upper()}")
    print("="*70)
    
    # Get directory
    output_dir = get_output_dir(provider_name)
    
    # Find Markdown files (excluding index)
    md_files = sorted(output_dir.glob("*.md"))
    md_files = [f for f in md_files if f.name != 'index.md']
    
    if not md_files:
        print(f"❌ No Markdown files found in {output_dir}")
        return
    
    print(f"\n📁 Found {len(md_files)} Markdown file(s)")
    print(f"   Formats to generate: {', '.join(formats)}")
    
    # Process each file
    for md_file in md_files:
        print(f"\n📄 Processing: {md_file.name}")
        
        try:
            if 'html' in formats:
                html_file = markdown_to_html(md_file)
                print(f"   ✅ HTML: {html_file.name}")
            
            if 'pdf' in formats:
                pdf_file = markdown_to_pdf(md_file)
                print(f"   ✅ PDF: {pdf_file.name}")
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "="*70)
    print("CONVERSION COMPLETE")
    print("="*70)
    print(f"Provider: {provider_name.upper()}")
    print(f"Files processed: {len(md_files)}")
    print(f"Output directory: {output_dir}")
    print("="*70 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Convert Markdown reports to HTML and PDF"
    )
    parser.add_argument(
        '--llm',
        choices=['claude', 'gemini', 'both'],
        default='both',
        help='LLM provider to process'
    )
    parser.add_argument(
        '--formats',
        nargs='+',
        choices=['html', 'pdf'],
        default=['html', 'pdf'],
        help='Output formats to generate'
    )
    
    args = parser.parse_args()
    
    # Process selected provider(s)
    if args.llm in ['claude', 'both']:
        process_all_markdown_files('claude', args.formats)
    
    if args.llm in ['gemini', 'both']:
        process_all_markdown_files('gemini', args.formats)
    
    print("✨ All format conversion complete!")


if __name__ == "__main__":
    main()













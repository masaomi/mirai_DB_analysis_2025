#!/usr/bin/env python3
"""
Convert Markdown files to HTML and PDF formats
"""

import os
import glob
import subprocess
from pathlib import Path
import markdown

try:
    from xhtml2pdf import pisa
    XHTML2PDF_AVAILABLE = True
except ImportError:
    XHTML2PDF_AVAILABLE = False

def convert_md_to_html(md_file_path, output_dir=None):
    """
    Convert a Markdown file to HTML
    
    Args:
        md_file_path: Path to the markdown file
        output_dir: Directory to save the HTML file (default: same as md file)
    
    Returns:
        Path to the generated HTML file
    """
    # Read the markdown file
    with open(md_file_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Convert markdown to HTML with extensions
    html_content = markdown.markdown(
        md_content,
        extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists']
    )
    
    # Create a complete HTML document with styling (Japanese-friendly)
    full_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{Path(md_file_path).stem}</title>
    <style>
        @charset "UTF-8";
        body {{
            font-family: "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Yu Gothic", "Meiryo", "MS PGothic", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            line-height: 1.8;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
            background-color: #fff;
        }}
        h1, h2, h3, h4, h5, h6 {{
            margin-top: 24px;
            margin-bottom: 16px;
            font-weight: 600;
            line-height: 1.25;
        }}
        h1 {{
            font-size: 2em;
            border-bottom: 1px solid #eaecef;
            padding-bottom: 0.3em;
        }}
        h2 {{
            font-size: 1.5em;
            border-bottom: 1px solid #eaecef;
            padding-bottom: 0.3em;
        }}
        h3 {{
            font-size: 1.25em;
        }}
        p {{
            margin-top: 0;
            margin-bottom: 16px;
        }}
        ul, ol {{
            margin-top: 0;
            margin-bottom: 16px;
            padding-left: 2em;
        }}
        li {{
            margin-bottom: 8px;
        }}
        code {{
            background-color: #f6f8fa;
            border-radius: 3px;
            padding: 0.2em 0.4em;
            font-family: "Menlo", "Monaco", "Courier New", "Osaka-Mono", monospace;
            font-size: 85%;
        }}
        pre {{
            background-color: #f6f8fa;
            border-radius: 3px;
            padding: 16px;
            overflow: auto;
            line-height: 1.45;
        }}
        pre code {{
            background-color: transparent;
            padding: 0;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 16px;
        }}
        table th, table td {{
            border: 1px solid #dfe2e5;
            padding: 6px 13px;
        }}
        table th {{
            background-color: #f6f8fa;
            font-weight: 600;
        }}
        table tr:nth-child(2n) {{
            background-color: #f6f8fa;
        }}
        blockquote {{
            margin: 0;
            padding: 0 1em;
            color: #6a737d;
            border-left: 0.25em solid #dfe2e5;
        }}
        hr {{
            height: 0.25em;
            padding: 0;
            margin: 24px 0;
            background-color: #e1e4e8;
            border: 0;
        }}
        a {{
            color: #0366d6;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        strong {{
            font-weight: 600;
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>
"""
    
    # Determine output path
    if output_dir is None:
        output_dir = Path(md_file_path).parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    html_file_path = output_dir / f"{Path(md_file_path).stem}.html"
    
    # Write the HTML file
    with open(html_file_path, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print(f"✓ HTML created: {html_file_path}")
    return html_file_path


def convert_html_to_pdf_xhtml2pdf(html_file_path, output_dir=None):
    """
    Convert an HTML file to PDF using xhtml2pdf (Python-only solution)
    
    Args:
        html_file_path: Path to the HTML file
        output_dir: Directory to save the PDF file (default: same as HTML file)
    
    Returns:
        Path to the generated PDF file or None if conversion failed
    """
    if not XHTML2PDF_AVAILABLE:
        return None
    
    # Determine output path
    if output_dir is None:
        output_dir = Path(html_file_path).parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    pdf_file_path = output_dir / f"{Path(html_file_path).stem}.pdf"
    
    try:
        # Read HTML file
        with open(html_file_path, 'r', encoding='utf-8') as html_file:
            html_content = html_file.read()
        
        # Convert HTML to PDF
        with open(pdf_file_path, 'wb') as pdf_file:
            pisa_status = pisa.CreatePDF(
                html_content.encode('utf-8'),
                dest=pdf_file,
                encoding='utf-8'
            )
        
        if pisa_status.err:
            print(f"✗ PDF generation had errors")
            return None
        else:
            print(f"✓ PDF created: {pdf_file_path}")
            return pdf_file_path
            
    except Exception as e:
        print(f"✗ Error converting to PDF: {e}")
        return None


def convert_html_to_pdf_wkhtmltopdf(html_file_path, output_dir=None):
    """
    Convert an HTML file to PDF using wkhtmltopdf
    
    Args:
        html_file_path: Path to the HTML file
        output_dir: Directory to save the PDF file (default: same as HTML file)
    
    Returns:
        Path to the generated PDF file or None if conversion failed
    """
    # Check if wkhtmltopdf is available
    try:
        subprocess.run(['wkhtmltopdf', '--version'], 
                      capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    
    # Determine output path
    if output_dir is None:
        output_dir = Path(html_file_path).parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    pdf_file_path = output_dir / f"{Path(html_file_path).stem}.pdf"
    
    # Convert HTML to PDF using wkhtmltopdf
    try:
        cmd = [
            'wkhtmltopdf',
            '--encoding', 'UTF-8',
            '--page-size', 'A4',
            '--margin-top', '20mm',
            '--margin-right', '20mm',
            '--margin-bottom', '20mm',
            '--margin-left', '20mm',
            '--enable-local-file-access',
            str(html_file_path),
            str(pdf_file_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✓ PDF created: {pdf_file_path}")
            return pdf_file_path
        else:
            return None
            
    except Exception as e:
        return None


def convert_html_to_pdf(html_file_path, output_dir=None):
    """
    Convert an HTML file to PDF using available method
    
    Args:
        html_file_path: Path to the HTML file
        output_dir: Directory to save the PDF file (default: same as HTML file)
    
    Returns:
        Path to the generated PDF file or None if conversion failed
    """
    # Try xhtml2pdf first (Python-only, no system dependencies)
    result = convert_html_to_pdf_xhtml2pdf(html_file_path, output_dir)
    if result is not None:
        return result
    
    # Try wkhtmltopdf as fallback
    result = convert_html_to_pdf_wkhtmltopdf(html_file_path, output_dir)
    if result is not None:
        return result
    
    # No PDF conversion method available
    print("⚠ No PDF generation tool available.")
    print("  Option 1: pip install xhtml2pdf")
    print("  Option 2: brew install wkhtmltopdf")
    return None


def convert_directory(directory_path):
    """
    Convert all Markdown files in a directory to HTML and PDF
    
    Args:
        directory_path: Path to the directory containing Markdown files
    """
    directory = Path(directory_path)
    
    if not directory.exists():
        print(f"Error: Directory {directory_path} does not exist")
        return
    
    # Find all markdown files
    md_files = list(directory.glob("*.md"))
    
    if not md_files:
        print(f"No Markdown files found in {directory_path}")
        return
    
    print(f"Found {len(md_files)} Markdown file(s) in {directory_path}\n")
    
    # Convert each markdown file
    for md_file in md_files:
        print(f"Converting: {md_file.name}")
        try:
            # Convert to HTML
            html_file = convert_md_to_html(md_file)
            
            # Convert to PDF
            convert_html_to_pdf(html_file)
            
            print()
        except Exception as e:
            print(f"✗ Error converting {md_file.name}: {e}\n")


if __name__ == "__main__":
    # Convert files in direct_analysis_by_chat directory
    target_dir = "/Users/masa/forback/github/mirai_DB_backup/direct_analysis_by_chat"
    
    print("=" * 60)
    print("Markdown to HTML/PDF Converter")
    print("=" * 60)
    print()
    
    convert_directory(target_dir)
    
    print("=" * 60)
    print("Conversion complete!")
    print("=" * 60)


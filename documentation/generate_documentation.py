import os
from pathlib import Path
import markdown
import re

def read_file_content(file_path):
    """Read and return file content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}"

def get_language_from_extension(file_path):
    """Get language based on file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    language_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'jsx',
        '.tsx': 'tsx',
        '.html': 'html',
        '.css': 'css',
        '.md': 'markdown',
        '.json': 'json',
    }
    return language_map.get(ext, '')

def generate_documentation():
    """Generate comprehensive documentation."""
    # Define the order of main sections and their files
    structure = {
        "Design Documentation": [
            "documentation/app_design.md"
        ],
        "Main Application": [
            "main.py"
        ],
        "Backend Server": [
            "backend/server/server.py",
            "backend/server/websocket_manager.py",
            "backend/server/server_utils.py",
        ],
        "Multi-Agent System": [
            "multi_agents/agent.py",
            "multi_agents/agents/browser.py",
            "multi_agents/agents/editor.py",
            "multi_agents/agents/researcher.py",
            "multi_agents/agents/reviewer.py",
            "multi_agents/agents/writer.py",
            "multi_agents/agents/publisher.py"
        ]
    }

    # Start building the documentation
    doc_parts = ["# GPT Researcher - Complete Documentation\n\n"]
    
    # Add table of contents
    doc_parts.append("## Table of Contents\n\n")
    for section in structure:
        doc_parts.append(f"- [{section}](#{section.lower().replace(' ', '-')})\n")
    doc_parts.append("\n---\n\n")

    # Add each section
    for section, files in structure.items():
        doc_parts.append(f"## {section}\n\n")
        
        for file_path in files:
            if not os.path.exists(file_path):
                doc_parts.append(f"### {file_path}\n*File not found*\n\n")
                continue
                
            content = read_file_content(file_path)
            language = get_language_from_extension(file_path)
            
            doc_parts.append(f"### {file_path}\n\n")
            
            if file_path.endswith('.md'):
                # For markdown files, include content directly
                doc_parts.append(f"{content}\n\n")
            else:
                # For code files, wrap in code blocks
                doc_parts.append(f"```{language}\n{content}\n```\n\n")
            
            doc_parts.append("---\n\n")

    # Write the complete documentation
    output_path = "documentation/complete_documentation.md"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(''.join(doc_parts))
    
    print(f"Documentation generated successfully at {output_path}")

def generate_html():
    """Generate HTML version of the documentation."""
    md_path = "documentation/complete_documentation.md"
    if not os.path.exists(md_path):
        print("Markdown documentation not found. Generate it first.")
        return
        
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
        
    html_content = markdown.markdown(
        md_content,
        extensions=['fenced_code', 'tables', 'toc']
    )
    
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>GPT Researcher Documentation</title>
        <style>
            body { 
                max-width: 1200px; 
                margin: 0 auto; 
                padding: 20px;
                font-family: system-ui, -apple-system, sans-serif;
                line-height: 1.6;
            }
            pre { 
                background: #f6f8fa; 
                padding: 16px; 
                border-radius: 6px;
                overflow-x: auto;
            }
            code { font-family: 'Consolas', monospace; }
            h1, h2, h3 { color: #24292e; }
            hr { margin: 2em 0; }
        </style>
    </head>
    <body>
        %s
    </body>
    </html>
    """ % html_content
    
    with open('documentation/complete_documentation.html', 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print("HTML documentation generated successfully")

if __name__ == "__main__":
    generate_documentation()
    generate_html()

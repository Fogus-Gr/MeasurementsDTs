import os
import re
import shutil
import markdown

SOURCE_DIR = "/home/lenovo/MeasurementsDTs/.qoder/repowiki/en/content"
DEST_DIR = "/home/lenovo/MeasurementsDTs/docs/html_wiki"

def strip_cite(content):
    # Remove <cite>...</cite> blocks entirely
    return re.sub(r'<cite>.*?</cite>', '', content, flags=re.DOTALL)

def build_tree(dir_path):
    tree = {'type': 'folder', 'name': os.path.basename(dir_path), 'children': {}}
    items = sorted(os.listdir(dir_path))
    
    # Sort folders first, then files
    folders = [item for item in items if os.path.isdir(os.path.join(dir_path, item))]
    files = [item for item in items if not os.path.isdir(os.path.join(dir_path, item)) and item.endswith('.md')]
    
    for item in folders:
        path = os.path.join(dir_path, item)
        tree['children'][item] = build_tree(path)
        
    for item in files:
        path = os.path.join(dir_path, item)
        tree['children'][item] = {'type': 'file', 'name': item[:-3], 'path': path}
        
    return tree

def generate_sidebar_html(tree, is_root=True):
    html = ""
    # Process children
    for name, node in tree['children'].items():
        if node['type'] == 'folder':
            html += f'<div class="folder {"open" if is_root else ""}"><span class="chevron"></span><span class="folder-icon"></span>{name}</div>\n'
            html += f'<div class="children">\n'
            html += generate_sidebar_html(node, is_root=False)
            html += f'</div>\n'
        else:
            html_name = node['name'] + ".md"
            rel_path = os.path.relpath(node['path'], SOURCE_DIR)
            html_rel_path = rel_path[:-3] + ".html"
            html += f'<div class="file"><a href="{{{{BASE_PREFIX}}}}{html_rel_path}"><span class="file-icon">M&#x2193;</span> {html_name}</a></div>\n'
    return html

template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --bg-color: #03131a;
            --sidebar-bg: #011627;
            --text-color: #B0BEC5;
            --link-color: #58a6ff;
            --folder-color: #d6deeb;
            --file-color: #d6deeb;
            --border-color: #1e2d3d;
            --hover-bg: rgba(255,255,255,0.05);
        }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; display: flex; margin: 0; padding: 0; background-color: var(--bg-color); color: var(--text-color); height: 100vh; overflow: hidden; }}
        #sidebar {{ width: 350px; background-color: var(--sidebar-bg); color: var(--text-color); overflow-y: auto; height: 100%; padding: 10px 0; box-sizing: border-box; border-right: 1px solid var(--border-color); font-size: 13px; line-height: 1.5; transition: margin-left 0.3s ease; flex-shrink: 0; }}
        body.sidebar-hidden #sidebar {{ margin-left: -350px; }}
        #content {{ flex-grow: 1; padding: 40px 60px; overflow-y: auto; height: 100%; box-sizing: border-box; background-color: var(--bg-color); color: #c9d1d9; }}
        
        #top-bar {{ margin-bottom: 20px; }}
        #sidebar-toggle {{ cursor: pointer; font-size: 24px; color: var(--text-color); user-select: none; transition: color 0.2s; }}
        #sidebar-toggle:hover {{ color: #ffffff; }}
        
        .folder {{ cursor: pointer; user-select: none; color: var(--folder-color); display: flex; align-items: center; padding: 4px 10px; }}
        .folder:hover {{ background-color: var(--hover-bg); }}
        
        .chevron {{ display: inline-block; width: 14px; text-align: center; font-size: 9px; transition: transform 0.1s; margin-right: 2px; color: #8a99a8; }}
        .folder .chevron::before {{ content: '▶'; }}
        .folder.open .chevron::before {{ content: '▼'; }}
        
        .folder-icon {{ display: inline-block; width: 16px; margin-right: 6px; }}
        .folder-icon::before {{ content: '📁'; font-size: 14px; filter: grayscale(100%) brightness(150%); opacity: 0.8; }}
        .folder.open .folder-icon::before {{ content: '📂'; }}
        
        .file {{ display: flex; align-items: center; }}
        .file a {{ color: var(--file-color); text-decoration: none; display: flex; align-items: center; width: 100%; padding: 4px 10px; padding-left: 20px; }}
        .file a:hover {{ background-color: var(--hover-bg); color: #ffffff; }}
        
        .file-icon {{ color: #58a6ff; font-family: monospace; font-weight: bold; font-size: 10px; margin-right: 6px; display: inline-block; width: 16px; text-align: center; }}
        
        .children {{ margin-left: 14px; display: none; }}
        .open + .children {{ display: block; }}
        
        /* Markdown content styles */
        #content h1, #content h2 {{ color: #ffffff; border-bottom: 1px solid var(--border-color); padding-bottom: 8px; margin-top: 24px; font-weight: 600; }}
        #content h3 {{ color: #ffffff; margin-top: 20px; font-weight: 600; }}
        #content a {{ color: var(--link-color); text-decoration: none; }}
        #content a:hover {{ text-decoration: underline; }}
        #content code {{ background-color: rgba(110,118,129,0.3); padding: 0.2em 0.4em; border-radius: 6px; font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace; font-size: 85%; }}
        #content pre {{ background-color: #161b22; padding: 16px; border-radius: 6px; overflow-x: auto; border: 1px solid var(--border-color); line-height: 1.45; }}
        #content pre code {{ background-color: transparent; padding: 0; font-size: 85%; }}
        #content blockquote {{ border-left: 4px solid #3b434b; margin: 0; padding-left: 16px; color: #8b949e; }}
        #content table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
        #content th, #content td {{ border: 1px solid #30363d; padding: 6px 13px; text-align: left; }}
        #content th {{ background-color: #161b22; font-weight: 600; }}
        #content img {{ max-width: 100%; height: auto; }}
        #content hr {{ height: 1px; background-color: var(--border-color); border: none; margin: 24px 0; }}
    </style>
</head>
<body>
    <div id="sidebar">
        {sidebar}
    </div>
    <div id="content">
        <div id="top-bar">
            <span id="sidebar-toggle" title="Toggle Sidebar">&#9776;</span>
        </div>
        {content}
    </div>
    <script>
        document.getElementById('sidebar-toggle').addEventListener('click', () => {{
            document.body.classList.toggle('sidebar-hidden');
        }});

        document.querySelectorAll('.folder').forEach(folder => {{
            folder.addEventListener('click', (e) => {{
                // Only toggle if clicking the folder itself, not a child
                if (e.target === folder || e.target.parentNode === folder) {{
                    folder.classList.toggle('open');
                }}
            }});
        }});
        
        // Highlight current page in sidebar
        const currentPath = window.location.pathname;
        document.querySelectorAll('.file a').forEach(link => {{
            if (link.href && currentPath.endsWith(link.getAttribute('href').replace('../', ''))) {{
                link.style.backgroundColor = 'rgba(255,255,255,0.1)';
                link.style.color = '#ffffff';
                link.style.fontWeight = 'bold';
            }}
        }});
    </script>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        
        // Convert Python-Markdown's language-mermaid blocks to divs that Mermaid can process
        document.querySelectorAll('code.language-mermaid').forEach(el => {{
            const pre = el.parentNode;
            if (pre.tagName === 'PRE') {{
                const div = document.createElement('div');
                div.className = 'mermaid';
                div.textContent = el.textContent;
                pre.parentNode.replaceChild(div, pre);
            }}
        }});

        mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
    </script>
</body>
</html>
"""

def process_directory(source, dest):
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    
    tree = build_tree(source)
    sidebar_html = generate_sidebar_html(tree)
    
    for root, dirs, files in os.walk(source):
        rel_root = os.path.relpath(root, source)
        dest_root = os.path.join(dest, rel_root) if rel_root != '.' else dest
        
        if not os.path.exists(dest_root):
            os.makedirs(dest_root)
            
        for file in files:
            if file.endswith('.md'):
                src_path = os.path.join(root, file)
                
                depth = 0 if rel_root == '.' else len(rel_root.split(os.sep))
                base_prefix = '../' * depth
                
                current_sidebar = sidebar_html.replace('{{BASE_PREFIX}}', base_prefix)
                
                with open(src_path, 'r', encoding='utf-8') as f:
                    md_content = f.read()
                
                stripped_content = strip_cite(md_content)
                html_content = markdown.markdown(stripped_content, extensions=['fenced_code', 'tables'])
                
                title = file[:-3]
                final_html = template.format(title=title, sidebar=current_sidebar, content=html_content)
                
                dest_path = os.path.join(dest_root, title + '.html')
                with open(dest_path, 'w', encoding='utf-8') as f:
                    f.write(final_html)

if __name__ == "__main__":
    process_directory(SOURCE_DIR, DEST_DIR)
    print(f"Documentation successfully generated at {DEST_DIR}")

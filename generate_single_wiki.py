import os
import re
import shutil
import markdown

SOURCE_DIR = "/home/lenovo/MeasurementsDTs/.qoder/repowiki/en/content"
DEST_FILE = "/home/lenovo/MeasurementsDTs/docs/wiki_documentation.html"

def strip_cite(content):
    # Remove <cite>...</cite> blocks entirely
    return re.sub(r'<cite>.*?</cite>', '', content, flags=re.DOTALL)

def slugify(text):
    return re.sub(r'[^a-zA-Z0-9]', '-', text).strip('-')

def build_tree(dir_path):
    tree = {'type': 'folder', 'name': os.path.basename(dir_path), 'children': {}}
    if not os.path.exists(dir_path):
        return tree
    
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
            page_id = slugify(rel_path)
            html += f'<div class="file"><a href="#{page_id}"><span class="file-icon">M&#x2193;</span> {html_name}</a></div>\n'
    return html

def collect_pages(source):
    pages = []
    for root, dirs, files in os.walk(source):
        for file in files:
            if file.endswith('.md'):
                src_path = os.path.join(root, file)
                rel_path = os.path.relpath(src_path, source)
                page_id = slugify(rel_path)
                
                with open(src_path, 'r', encoding='utf-8') as f:
                    md_content = f.read()
                
                stripped_content = strip_cite(md_content)
                html_content = markdown.markdown(stripped_content, extensions=['fenced_code', 'tables'])
                
                pages.append({
                    'id': page_id,
                    'title': file[:-3],
                    'html': html_content
                })
    return pages

template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wiki Documentation</title>
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
        
        .children {{ margin-left: 14px; display: none; }}
        .open + .children {{ display: block; }}
        
        .file-icon {{ color: #58a6ff; font-family: monospace; font-weight: bold; font-size: 10px; margin-right: 6px; display: inline-block; width: 16px; text-align: center; }}
        
        /* Markdown content styles */
        .wiki-page {{ display: none; }}
        .wiki-page.active {{ display: block; animation: fadeIn 0.3s ease; }}
        @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
        
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
        <div id="pages-container">
            {pages_html}
        </div>
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
        
        function showPage(id) {{
            document.querySelectorAll('.wiki-page').forEach(el => el.classList.remove('active'));
            const target = document.getElementById(id);
            if (target) {{
                target.classList.add('active');
                // Scroll to top of content
                document.getElementById('content').scrollTop = 0;
            }}
            
            // Highlight sidebar
            document.querySelectorAll('.file a').forEach(link => {{
                if (link.getAttribute('href') === '#' + id) {{
                    link.style.backgroundColor = 'rgba(255,255,255,0.1)';
                    link.style.color = '#ffffff';
                    link.style.fontWeight = 'bold';
                    
                    // Auto-open parent folders
                    let parent = link.closest('.children');
                    while(parent) {{
                        if(parent.previousElementSibling && parent.previousElementSibling.classList.contains('folder')) {{
                            parent.previousElementSibling.classList.add('open');
                        }}
                        parent = parent.parentElement.closest('.children');
                    }}
                }} else {{
                    link.style.backgroundColor = '';
                    link.style.color = '';
                    link.style.fontWeight = '';
                }}
            }});
            
            // Trigger mermaid render if not already rendered
            if (target && window.mermaid) {{
                try {{
                    mermaid.run({{ nodes: target.querySelectorAll('.mermaid') }});
                }} catch(e) {{}}
            }}
        }}

        window.addEventListener('hashchange', () => {{
            const id = window.location.hash.substring(1);
            if (id) showPage(id);
        }});

        // on load
        window.addEventListener('DOMContentLoaded', () => {{
            if (window.location.hash) {{
                showPage(window.location.hash.substring(1));
            }} else {{
                const firstPage = document.querySelector('.wiki-page');
                if (firstPage) {{
                    showPage(firstPage.id);
                }}
            }}
        }});
    </script>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        window.mermaid = mermaid;
        
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

        mermaid.initialize({{ startOnLoad: false, theme: 'dark' }});
        
        // Render initial page
        const activePage = document.querySelector('.wiki-page.active');
        if (activePage) {{
            mermaid.run({{ nodes: activePage.querySelectorAll('.mermaid') }});
        }}
    </script>
</body>
</html>
"""

def generate_single_file():
    dest_dir = os.path.dirname(DEST_FILE)
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
        
    tree = build_tree(SOURCE_DIR)
    sidebar_html = generate_sidebar_html(tree)
    
    pages = collect_pages(SOURCE_DIR)
    pages_html = ""
    for page in pages:
        pages_html += f'<div id="{page["id"]}" class="wiki-page">\n{page["html"]}\n</div>\n'
        
    final_html = template.format(
        sidebar=sidebar_html,
        pages_html=pages_html
    )
    
    with open(DEST_FILE, 'w', encoding='utf-8') as f:
        f.write(final_html)

if __name__ == "__main__":
    generate_single_file()
    print(f"Single file documentation successfully generated at {DEST_FILE}")

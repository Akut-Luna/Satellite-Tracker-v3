import os
import sys
import ast
from pathlib import Path, PurePath
from importlib.metadata import version, PackageNotFoundError

def get_external_packages(root_path):
    root = Path(root_path)
    if not root.exists():
        sys.exit(f'Directory not found: {root_path}')

    # Identify local folders/files in src to ignore
    local_contents = {p.stem for p in root.iterdir()}
    external_pkgs = set()

    for py_file in root.rglob('*.py'):
        try:
            tree = ast.parse(py_file.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                pkg_name = None
                if isinstance(node, ast.Import):
                    for n in node.names:
                        pkg_name = n.name.split('.')[0]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    if node.module:
                        pkg_name = node.module.split('.')[0]
                
                if pkg_name and pkg_name not in local_contents:
                    external_pkgs.add(pkg_name)
        except Exception:
            continue
    return sorted(external_pkgs)

if __name__ == '__main__':
    last_folder = PurePath(os.getcwd()).name
    if last_folder == 'dev':
        src_path = '../main/src'
        req_path = '../requirements.txt'
    else:
        src_path = 'main/src'
        req_path = 'requirements.txt'

    found_pkgs = get_external_packages(src_path)

    print(f'{'Package':<20} | {'Version':<10}')
    print('-' * 41)
    
    with open(req_path, 'w') as f:
        for pkg in found_pkgs:
            if pkg == 'dotenv': # A different, older, and largely abandoned package.
                pkg = 'python-dotenv'
            
            try:
                # get version of installed package
                ver = version(pkg)
                f.write(f'{pkg}=={ver}\n')
            except PackageNotFoundError:
                # ignore built-ins (sys, os) or uninstalled packages
                ver = 'Built-in/Not Found'
            
            print(f'{pkg:<20} | {ver:<10}')
    
    print('-' * 41)
    print(f'Saved in: {req_path}')
    
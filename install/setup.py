from pathlib import Path
import shutil

dirs = ['data', 'config']

for d in dirs:
    source = Path(f'install/example_{d}')
    dest = Path(f'main/{d}')

    if not source.is_dir():
        print(f'Error: Source directory {source} does not exist.')
        continue

    if dest.exists():
        print(f'Directory {dest} already exists. Skipping copy.')
    else:
        print(f'Creating {dest} from {source}...')
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, dest)
        print(f'{d} setup complete.')
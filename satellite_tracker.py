import os
import sys
import subprocess

if __name__ == '__main__':
    script_path = os.path.join(os.path.dirname(__file__), 'main', 'src', 'main.py')
    subprocess.run([sys.executable, script_path], check=True)

# TODO: clean up signals

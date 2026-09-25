from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ASTRAEUM = Path(r'C:\Users\casho\OneDrive\Documents\ChatGPT\ASTRAEUM\engine')

def main() -> int:
    parser = argparse.ArgumentParser(description='Brutus Control Plane -> ASTRAEUM adapter')
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--plugin', default=str(ROOT / 'adapters' / 'brutus_pell' / 'connected_spectrum.py'))
    parser.add_argument('--output-dir', default=str(ROOT / 'runs' / 'astraeum'))
    parser.add_argument('--astraeum-engine', default=os.environ.get('ASTRAEUM_ENGINE_DIR', str(DEFAULT_ASTRAEUM)))
    args = parser.parse_args()

    runner = Path(args.astraeum_engine) / 'research_runner.py'
    if not runner.exists():
        raise SystemExit(f'ASTRAEUM research runner not found: {runner}')
    manifest = Path(args.manifest)
    if not manifest.is_absolute():
        manifest = (Path.cwd() / manifest).resolve()
    plugin = Path(args.plugin)
    if not plugin.is_absolute():
        plugin = (Path.cwd() / plugin).resolve()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = (Path.cwd() / output_dir).resolve()
    cmd = [sys.executable, str(runner), '--manifest', str(manifest), '--plugin', str(plugin), '--output-dir', str(output_dir)]
    completed = subprocess.run(cmd, cwd=str(Path(args.astraeum_engine)), check=False)
    return completed.returncode

if __name__ == '__main__':
    raise SystemExit(main())

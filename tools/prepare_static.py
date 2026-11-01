"""Build, check and stage only public website assets for static hosting."""
from pathlib import Path
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / '_site'
PUBLIC_SUFFIXES = {'.html', '.css', '.js', '.mjs', '.json', '.png', '.jpg',
                   '.jpeg', '.webp', '.svg', '.ico', '.woff2', '.txt', '.xml'}


def public_asset(path):
    rel = path.relative_to(ROOT)
    return (not path.is_symlink()
            and not any((part.startswith('.') and part != '.well-known') or part in {'tools', 'tests', '__pycache__', '_site'} for part in rel.parts)
            and '.test.' not in path.name
            and path.suffix.lower() in PUBLIC_SUFFIXES)


def main():
    subprocess.run([sys.executable, 'tools/build.py'], cwd=ROOT, check=True)
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tools', '-p', 'test_*.py'], cwd=ROOT, check=True)
    subprocess.run(['node', '--test', 'tools/test_checkout.cjs'], cwd=ROOT, check=True)
    # Enumerate before creating the output, so old output is never copied into itself.
    files = [p for p in ROOT.rglob('*') if p.is_file() and public_asset(p)]
    if TARGET.exists():
        assert TARGET.resolve().parent == ROOT.resolve() and TARGET.name == '_site'
        shutil.rmtree(TARGET)
    for path in files:
        destination = TARGET / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    (TARGET / 'release.json').write_text(json.dumps({'commit': commit, 'service': 'bidbell-public-site'}) + '\n', encoding='utf-8')
    print(f'Staged {len(files)} public assets from {commit}')


if __name__ == '__main__':
    main()

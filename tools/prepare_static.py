"""Build, check and stage only public website assets for static hosting."""
from pathlib import Path
from datetime import date, datetime, timezone
import json
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / '_site'
PUBLIC_SUFFIXES = {'.html', '.css', '.js', '.mjs', '.json', '.png', '.jpg',
                   '.jpeg', '.webp', '.svg', '.ico', '.woff2', '.txt', '.xml'}


def public_asset(path, root=ROOT):
    rel = path.relative_to(root)
    return (not path.is_symlink()
            and not any((part.startswith('.') and part != '.well-known') or part in {'tools', 'tests', 'desk', '__pycache__', '_site'} for part in rel.parts)
            and '.test.' not in path.name
            and path.suffix.lower() in PUBLIC_SUFFIXES)


def get_build_date(environ=None, now=None):
    environ = os.environ if environ is None else environ
    value = environ.get('BUILD_DATE', (now or datetime.now(timezone.utc)).astimezone(timezone.utc).date().isoformat())
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError('BUILD_DATE must use YYYY-MM-DD')
    return value


def stage_public_assets(commit, build_date, root=ROOT):
    target = root / '_site'
    # Enumerate before creating the output, so old output is never copied into itself.
    files = [p for p in root.rglob('*') if p.is_file() and public_asset(p, root=root)]
    if target.exists():
        assert target.resolve().parent == root.resolve() and target.name == '_site'
        shutil.rmtree(target)
    for path in files:
        destination = target / path.relative_to(root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    (target / 'release.json').write_text(json.dumps({'commit': commit, 'service': 'bidbell-public-site',
                                                   'build_date': build_date}) + '\n', encoding='utf-8', newline='\n')
    print(f'Staged {len(files)} public assets from {commit} built for {build_date} UTC')


def main():
    # Capture once before the build, including a build that crosses UTC midnight.
    build_date = get_build_date()
    environment = dict(os.environ, BUILD_DATE=build_date)
    subprocess.run([sys.executable, 'tools/build.py'], cwd=ROOT, env=environment, check=True)
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tools', '-p', 'test_*.py'],
                   cwd=ROOT, env=environment, check=True)
    subprocess.run(['node', '--test', 'tools/test_checkout.cjs', 'workspace/core.test.mjs',
                    'prepare/plan.test.mjs'], cwd=ROOT, check=True)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    stage_public_assets(commit, build_date)


if __name__ == '__main__':
    main()

"""Verify the canonical public release from an independent network, without accounts or purchases."""
from pathlib import Path, PurePosixPath
from contextlib import contextmanager
from datetime import date, datetime, timezone
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from prepare_static import public_asset

ROOT = Path(__file__).resolve().parent.parent
BASE = 'https://getbidbell.com'
PATHS = ['/', '/start/', '/subscribe/', '/terms/', '/privacy/', '/workspace/', '/prepare/',
         '/brand.css', '/brand-icon.png', '/social/brand.jpg', '/.well-known/security.txt']


def asset_matches(body, expected, source):
    if hashlib.sha256(body).digest() == hashlib.sha256(expected).digest():
        return True
    if Path(source).suffix.lower() not in {'.png', '.jpg', '.jpeg'}:
        return False
    # Cloudflare Polish can recompress images without changing the displayed pixels.
    # This operator-only check still rejects a changed logo, format or dimensions.
    try:
        from PIL import Image, ImageChops, ImageStat
    except ImportError as error:
        raise RuntimeError('Install Pillow in the verification environment to check CDN image transformations.') from error
    try:
        with Image.open(io.BytesIO(body)) as live, Image.open(io.BytesIO(expected)) as original:
            if live.format != original.format or live.size != original.size:
                return False
            if live.convert('RGBA').tobytes() == original.convert('RGBA').tobytes():
                return True
            # JPEG CDN recompression is lossy. Bound the difference tightly on all
            # three 0..255 channels; PNG logos still require identical pixels.
            if live.format == 'JPEG':
                difference = ImageStat.Stat(ImageChops.difference(live.convert('RGB'), original.convert('RGB')))
                return max(difference.rms) <= 4 and max(difference.mean) <= 1
            return False
    except (OSError, ValueError):
        return False


def fetch(path, base=BASE):
    request = urllib.request.Request(base + path, headers={'Cache-Control': 'no-cache', 'User-Agent': 'BidBell-release-check/1.0'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.geturl(), response.read()


def validated_build_date(value, committed_timestamp, now=None):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
        raise ValueError('Release build_date must use YYYY-MM-DD')
    parsed = date.fromisoformat(value)
    committed = datetime.fromtimestamp(committed_timestamp, timezone.utc).date()
    today = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).date()
    if not committed <= parsed <= today:
        raise ValueError('Release build_date must be between the trusted commit and current UTC date')
    return value


@contextmanager
def trusted_build(commit, build_date, repository=ROOT):
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('Expected a full trusted Git commit')
    timestamp = int(subprocess.check_output(['git', 'show', '-s', '--format=%ct', commit], cwd=repository, text=True).strip())
    build_date = validated_build_date(build_date, timestamp)
    archive = subprocess.check_output(['git', '-c', 'core.autocrlf=false', 'archive', '--format=zip', commit], cwd=repository)
    with tempfile.TemporaryDirectory(prefix='bidbell-release-replay-') as name:
        target = Path(name)
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            members = bundle.infolist()
            if len(members) > 2000 or sum(item.file_size for item in members) > 100 * 1024 * 1024:
                raise ValueError('Trusted site archive exceeds verification bounds')
            for item in members:
                path = PurePosixPath(item.filename)
                if path.is_absolute() or '..' in path.parts or ':' in item.filename or '\\' in item.filename:
                    raise ValueError('Unsafe path in trusted site archive')
                if (item.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError('Site verification does not follow archived symlinks')
            bundle.extractall(target)
        environment = dict(os.environ, BUILD_DATE=build_date)
        subprocess.run([sys.executable, 'tools/build.py'], cwd=target, env=environment,
                       check=True, capture_output=True, text=True)
        yield target


def main():
    expected = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    _, body = fetch('/release.json?check=' + expected)
    release = json.loads(body)
    assert release['commit'] == expected, 'Canonical domain is not serving the current checked release'
    print('PASS canonical HTTPS and exact deployed commit')
    with trusted_build(expected, release.get('build_date')) as trusted:
        routes = list(PATHS)
        for page in sorted(trusted.rglob('*.html')):
            if not public_asset(page, root=trusted) or page.name == '404.html':
                continue
            relative = page.relative_to(trusted).as_posix()
            route = '/' + (relative[:-10] if relative.endswith('index.html') else relative)
            if route not in routes:
                routes.append(route)
        for path in routes:
            _, body = fetch(path + '?check=' + expected)
            source = path.lstrip('/') + ('index.html' if path.endswith('/') else '')
            assert asset_matches(body, (trusted / source).read_bytes(), source), f'Unexpected public content: {path}'
            print('PASS content:', path)
        destination, body = fetch('/', base='https://www.getbidbell.com')
        assert destination == BASE + '/', 'www must redirect to the canonical domain'
        assert body == (trusted / 'index.html').read_bytes(), 'www redirected to an outdated release'
        print('PASS www HTTPS and canonical redirect')
    for path in ['/tools/paddle.json', '/.git/config', '/desk/']:
        try:
            fetch(path)
        except urllib.error.HTTPError as error:
            assert error.code == 404, f'Unexpected status for excluded path: {path}'
        else:
            raise AssertionError('Excluded content is being served: ' + path)
        print('PASS excluded path:', path)


if __name__ == '__main__':
    main()

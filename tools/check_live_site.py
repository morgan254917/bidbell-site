"""Verify the canonical public release from an independent network, without accounts or purchases."""
from pathlib import Path
import hashlib
import io
import json
import subprocess
import urllib.error
import urllib.request

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


def main():
    expected = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    def committed(path):
        return subprocess.check_output(['git', 'show', expected + ':' + path], cwd=ROOT)
    _, body = fetch('/release.json?check=' + expected)
    assert json.loads(body)['commit'] == expected, 'Canonical domain is not serving the current checked release'
    print('PASS canonical HTTPS and exact deployed commit')
    for path in PATHS:
        _, body = fetch(path + '?check=' + expected)
        source = path.lstrip('/') + ('index.html' if path.endswith('/') else '')
        assert asset_matches(body, committed(source), source), f'Unexpected public content: {path}'
        print('PASS content:', path)
    destination, body = fetch('/', base='https://www.getbidbell.com')
    assert destination == BASE + '/', 'www must redirect to the canonical domain'
    assert body == committed('index.html'), 'www redirected to an outdated release'
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

"""Verify the canonical public release from an independent network, without accounts or purchases."""
from pathlib import Path
import hashlib
import json
import subprocess
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
BASE = 'https://getbidbell.com'
PATHS = ['/', '/start/', '/subscribe/', '/terms/', '/privacy/', '/workspace/', '/prepare/',
         '/brand.css', '/brand-icon.png', '/social/brand.jpg', '/.well-known/security.txt']


def fetch(path, base=BASE):
    request = urllib.request.Request(base + path, headers={'Cache-Control': 'no-cache', 'User-Agent': 'BidBell-release-check/1.0'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.geturl(), response.read()


def main():
    expected = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    _, body = fetch('/release.json?check=' + expected)
    assert json.loads(body)['commit'] == expected, 'Canonical domain is not serving the current checked release'
    print('PASS canonical HTTPS and exact deployed commit')
    for path in PATHS:
        _, body = fetch(path + '?check=' + expected)
        local = ROOT / path.lstrip('/')
        if path.endswith('/'):
            local /= 'index.html'
        assert hashlib.sha256(body).digest() == hashlib.sha256(local.read_bytes()).digest(), f'Unexpected public content: {path}'
        print('PASS content:', path)
    destination, body = fetch('/', base='https://www.getbidbell.com')
    assert destination == BASE + '/', 'www must redirect to the canonical domain'
    assert body == (ROOT / 'index.html').read_bytes(), 'www redirected to an outdated release'
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

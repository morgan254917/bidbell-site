"""Build, check and stage only public website assets for static hosting."""
from pathlib import Path
from datetime import date, datetime, timezone
import json
import os
import re
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
        if os.environ.get('BIDBELL_STAGING') == '1' and path.suffix == '.html':
            destination.write_text(preview_html(destination.read_text(encoding='utf-8')), encoding='utf-8', newline='\n')
    if os.environ.get('BIDBELL_STAGING') == '1':
        (target / 'staging.css').write_text('.staging-banner{padding:12px 20px;background:#EEE8FA;color:#191B30;text-align:center;font:600 14px/1.5 Arial,sans-serif}.industry-choices{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px;margin:20px 0}.industry-choice{padding:24px;border:1px solid #DEDDD7;border-radius:14px;background:#fff}.industry-choice h3{margin-top:0}.industry-choice a{display:inline-block;background:#191B30;color:#fff;padding:14px 18px;border-radius:9px;text-decoration:none}.industry-choice p{font-size:15px}', encoding='utf-8')
        (target / 'robots.txt').write_text('User-agent: *\nDisallow: /\n', encoding='utf-8')
    (target / 'release.json').write_text(json.dumps({'commit': commit, 'service': 'bidbell-public-site',
                                                   'build_date': build_date}) + '\n', encoding='utf-8', newline='\n')
    print(f'Staged {len(files)} public assets from {commit} built for {build_date} UTC')


def preview_html(content):
    """Make review builds incapable of submitting the public signup or opening checkout."""
    content = content.replace('https://bidbell-workspace.onrender.com', 'http://127.0.0.1:8860')
    content = content.replace('https://getbidbell.com', 'http://127.0.0.1:8861')
    content = re.sub(r'<section class="card coverage-status"[^>]*>.*?</section>', '<section class="card coverage-status"><p class="eyebrow">ONE BIDBELL. YOUR INDUSTRY.</p><h2>Start with the work your team can deliver.</h2><p>Choose cleaning or construction, then save your trade, territory and company information in the same workspace.</p><p>Coverage is source-specific. This staged expansion has not been published.</p></section>',content,count=1,flags=re.S)
    content = re.sub(r'<ol class="next-steps">.*?</ol>', '''<ol class="next-steps">
        <li><span class="step-index" aria-hidden="true">1</span><div><b>Choose your industry</b><span>Create and verify one BidBell account. Select your trade and service area.</span></div></li>
        <li><span class="step-index" aria-hidden="true">2</span><div><b>Find suitable work</b><span>Open matching opportunities and check the buyer's scope, deadlines and eligibility.</span></div></li>
        <li><span class="step-index" aria-hidden="true">3</span><div><b>Reuse your information</b><span>Save company details and documents. Review AI-assisted answers, missing items and your price.</span></div></li>
        <li><span class="step-index" aria-hidden="true">4</span><div><b>Review, submit and track</b><span>Approve the exact package. Use supported email delivery or the buyer's portal. Keep delivery evidence and buyer confirmation distinct.</span></div></li>
      </ol>''',content,count=1,flags=re.S)
    content = content.replace('Tell us what fits your business, then verify the same email in your workspace.', 'Choose your industry, create one account and save what fits your business.')
    if '<h1>Check your submission.</h1>' in content:
        content = re.sub(r'(<main id="main">).*?(</main>)',r'\1<div class="wrap page"><h1>Continue in your BidBell account.</h1><p>This preview uses one local account. Complete email verification and choose your industry, trade and service area there. No production signup or welcome email is sent.</p><a class="btn" href="http://127.0.0.1:8860/app#company">Open company profile</a></div>\2',content,count=1,flags=re.S)
    content = content.replace('href="/start/">Choose your construction trade', 'href="http://127.0.0.1:8860/app?industry=construction#register">Choose your construction trade')
    content = content.replace('Current paid and trial alert coverage is limited to janitorial, carpet, window and exterior cleaning. HVAC maintenance and grounds coverage is being validated and is not included in current plans.', 'This staged expansion covers cleaning and selected construction trades. Coverage varies by trade, location and available sources. Construction is not yet enabled in production.')
    content = re.sub(r'<script\b[^>]*src=["\'][^"\']*(?:paddle|checkout\.js)[^"\']*["\'][^>]*>.*?</script>', '', content, flags=re.I | re.S)
    content = re.sub(r'<script\b[^>]*id=["\']paddle-config["\'][^>]*>.*?</script>', '', content, flags=re.I | re.S)
    chooser = '''<section class="industry-choices" aria-label="Choose your industry"><article class="industry-choice"><h3>Cleaning</h3><p>Janitorial, carpet, window and exterior cleaning.</p><a href="http://127.0.0.1:8860/app?industry=cleaning#register">Start with cleaning</a></article><article class="industry-choice"><h3>Construction &amp; building trades</h3><p>Commercial renovation, repairs and supported specialist trades.</p><a href="http://127.0.0.1:8860/app?industry=construction#register">Start with construction</a></article></section><p>Your account and preferences stay together in BidBell. This preview uses fictional data and sends no production enrollment.</p>'''
    content = re.sub(r'<form\b[^>]*action=["\']https://docs\.google\.com/forms/[^"\']*["\'][^>]*>.*?</form>', chooser, content, flags=re.I | re.S)
    content = re.sub(r'https://docs\.google\.com/forms/[^\s"\'<>]+', 'http://127.0.0.1:8860/app#register', content)
    content = content.replace('</head>', '<meta name="robots" content="noindex,nofollow"><link rel="stylesheet" href="/staging.css"></head>')
    return re.sub(r'(<body\b[^>]*>)', r'\1<div class="staging-banner" role="note">Staging preview. Fictional accounts only. Production signup, email and billing stay unchanged.</div>', content, count=1, flags=re.I)


def main():
    # Capture once before the build, including a build that crosses UTC midnight.
    build_date = get_build_date()
    # Canonical artifacts and their existing contract checks never inherit the
    # review projection. Only _site receives the caller's staging transform.
    environment = dict(os.environ, BUILD_DATE=build_date, BIDBELL_STAGING='0')
    subprocess.run([sys.executable, 'tools/build.py'], cwd=ROOT, env=environment, check=True)
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tools', '-p', 'test_*.py'],
                   cwd=ROOT, env=environment, check=True)
    subprocess.run(['node', '--test', 'tools/test_checkout.cjs', 'workspace/core.test.mjs',
                    'prepare/plan.test.mjs'], cwd=ROOT, env=environment, check=True)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    stage_public_assets(commit, build_date)


if __name__ == '__main__':
    main()

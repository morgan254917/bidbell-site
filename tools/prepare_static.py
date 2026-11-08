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
        if path.suffix == '.html':
            content = destination.read_text(encoding='utf-8')
            if os.environ.get('BIDBELL_CONSTRUCTION_ENABLED') == '1' or os.environ.get('BIDBELL_STAGING') == '1':
                content = expansion_html(content)
            elif path.relative_to(root).as_posix() == 'construction-bids/index.html':
                content = construction_preview_html(content)
            if os.environ.get('BIDBELL_STAGING') == '1':
                content = preview_html(content)
            destination.write_text(content, encoding='utf-8', newline='\n')
    if os.environ.get('BIDBELL_CONSTRUCTION_ENABLED') == '1' or os.environ.get('BIDBELL_STAGING') == '1':
        (target / 'expansion.css').write_text('.industry-choices{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px;margin:20px 0}.industry-choice{padding:24px;border:1px solid #DEDDD7;border-radius:14px;background:#fff}.industry-choice h3{margin-top:0}.industry-choice a{display:inline-block;background:#191B30;color:#fff;padding:14px 18px;border-radius:9px;text-decoration:none}.industry-choice p{font-size:15px}', encoding='utf-8')
    if os.environ.get('BIDBELL_STAGING') == '1':
        (target / 'staging.css').write_text('.staging-banner{padding:12px 20px;background:#EEE8FA;color:#191B30;text-align:center;font:600 14px/1.5 Arial,sans-serif}.industry-choices{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px;margin:20px 0}.industry-choice{padding:24px;border:1px solid #DEDDD7;border-radius:14px;background:#fff}.industry-choice h3{margin-top:0}.industry-choice a{display:inline-block;background:#191B30;color:#fff;padding:14px 18px;border-radius:9px;text-decoration:none}.industry-choice p{font-size:15px}', encoding='utf-8')
        (target / 'robots.txt').write_text('User-agent: *\nDisallow: /\n', encoding='utf-8')
    release = {'commit': commit, 'service': 'bidbell-public-site', 'build_date': build_date}
    if os.environ.get('BIDBELL_STAGING') == '1':
        release['mode'] = 'staging'
    elif os.environ.get('BIDBELL_CONSTRUCTION_ENABLED') == '1':
        release['mode'] = 'expanded'
    (target / 'release.json').write_text(json.dumps(release) + '\n', encoding='utf-8', newline='\n')
    print(f'Staged {len(files)} public assets from {commit} built for {build_date} UTC')


def construction_preview_html(content):
    content = re.sub(
        r'<div class="cta-row"><a class="btn" href="/start/">Choose your construction trade</a>.*?</div>',
        '<p>Construction alert signup is coming soon.</p><div class="cta-row">'
        '<a class="btn" href="#construction-opportunities">Browse example notices</a></div>',
        content, count=1, flags=re.S,
    )
    content = content.replace('<section><p class="eyebrow">DATED PUBLIC SOURCE SNAPSHOT</p><h2>Explore work worth checking.',
                              '<section id="construction-opportunities"><p class="eyebrow">DATED PUBLIC SOURCE SNAPSHOT</p><h2>Explore example notices.')
    content = content.replace('records with a future deadline are present in this staged dataset.',
                              'records had a future deadline when this page was built.')
    content = content.replace('Try the complete workflow &rarr;', 'Start with cleaning &rarr;')
    return content.replace('<a class="btn" href="/start/">Start with your business</a>',
                           '<a class="btn" href="#construction-opportunities">Browse example notices</a>')


def expansion_html(content):
    """Opt-in release projection. Canonical source and default build stay unchanged."""
    workspace = 'https://bidbell-workspace.onrender.com/app'
    content = re.sub(r'<section class="card coverage-status"[^>]*>.*?</section>', '<section class="card coverage-status"><p class="eyebrow">ONE BIDBELL. YOUR INDUSTRY.</p><h2>Start with the work your team can deliver.</h2><p>Choose cleaning or construction, then save your trade, territory and company information in the same workspace.</p><p>Coverage varies by trade, location and available sources. Check the original buyer notice before bidding.</p></section>',content,count=1,flags=re.S)
    content = re.sub(r'<ol class="next-steps">.*?</ol>', '''<ol class="next-steps">
        <li><span class="step-index" aria-hidden="true">1</span><div><b>Choose your industry</b><span>Create and verify one BidBell account. Select your trade and service area.</span></div></li>
        <li><span class="step-index" aria-hidden="true">2</span><div><b>Find suitable work</b><span>Open matching opportunities and check the buyer's scope, deadlines and eligibility.</span></div></li>
        <li><span class="step-index" aria-hidden="true">3</span><div><b>Reuse your information</b><span>Save company details and documents. Build an estimate or quote from your inputs. Review AI-assisted answers and missing items.</span></div></li>
        <li><span class="step-index" aria-hidden="true">4</span><div><b>Review, submit and track</b><span>Approve the exact package. Use supported email delivery or the buyer's portal. Keep delivery evidence and buyer confirmation distinct.</span></div></li>
      </ol>''',content,count=1,flags=re.S)
    content = content.replace('Tell us what fits your business, then verify the same email in your workspace.', 'Choose your industry, create one account and save what fits your business.')
    if '<h1>Check your submission.</h1>' in content:
        content = re.sub(r'(<main id="main">).*?(</main>)',r'\1<div class="wrap page"><h1>Continue in your BidBell account.</h1><p>Verify your email, save your company profile and choose your industry, trade and service area. Review and confirm daily alert enrollment there. This page alone does not confirm enrollment.</p><a class="btn" href="'+workspace+r'#company">Open company profile</a></div>\2',content,count=1,flags=re.S)
    content = content.replace('href="/start/">Choose your construction trade', 'href="'+workspace+'?industry=construction#register">Choose your construction trade')
    content = content.replace('Current paid and trial alert coverage is limited to janitorial, carpet, window and exterior cleaning. HVAC maintenance and grounds coverage is being validated and is not included in current plans.', 'Cleaning and selected construction trades are supported. Coverage varies by trade, location and available sources.')
    content = re.sub(r'<p>BidBell provides contract opportunity alerts for building-service contractors\..*?We are not a government service, a bidding agent, a law firm or a consultant\.</p>', '<p>BidBell connects cleaning and selected construction trades with suitable work from supported public procurement sources. Alerts reflect your saved industry, trade, location and declared eligibility. New, updated, closing-soon and still-open opportunities remain distinguishable. Coverage varies by source and location; always check the current buyer notice. Cleaning contract forecasts, where available, are separate from open solicitations. We are not a government service, a law firm or a consultant.</p>', content, count=1, flags=re.S)
    content = content.replace('commercial cleaning companies (janitorial, carpet and window cleaning), including companies that have won federal contracts', 'cleaning and construction businesses in supported trades, including companies that have won public contracts')
    content = content.replace('and our sign-up form (Google Forms). Sign-up answers are stored in BidBell&rsquo;s private Google account.', 'and legacy signup records in BidBell&rsquo;s private Google account. New account and alert preferences are saved in the workspace and private operations records after your confirmation.')
    content = content.replace('We use public government data. Notices can be incomplete,', 'We use supported public procurement data. Notices can be incomplete,')
    content = content.replace('the full official notice and its attachments on SAM.gov before relying', 'the original buyer notice and its attachments before relying')
    content = content.replace('Start with your alert preferences, then create and verify your workspace account using the same email. Once your signup is processed, your existing alert trial dates also control preparation access.', 'Create and verify one account, save your company profile and confirm daily alerts. Your original trial dates cover alerts and the application workspace together.')
    content = content.replace('The construction preview covers commercial building, renovation, repairs and selected specialties.', 'Construction covers commercial building, renovation, repairs and selected specialties.')
    content = content.replace('Awarded-contract endings appear separately as research forecasts, not open bids.', 'Cleaning contract forecasts, where available, appear separately from open bids.')
    content = content.replace('records with a future deadline are present in this staged dataset.', 'records with a future deadline are available in this source snapshot at build time.')
    content = content.replace('public government sources that can be incomplete,', 'supported public procurement sources that can be incomplete,')
    content = content.replace('These preferences shape your daily alerts. Next, use this same email to open your BidBell workspace and build your response.', 'Create one account. Verify your email, save your trade and service area, then confirm your daily alert preferences.')
    content = content.replace('Set up your alert preferences</a> first, then create and verify your workspace account with the same email.', 'Create your BidBell account</a>, verify your email and confirm daily alerts in your company profile.')
    chooser = '<section class="industry-choices" aria-label="Choose your industry"><article class="industry-choice"><h3>Cleaning</h3><p>Janitorial, carpet, window and exterior cleaning.</p><a href="'+workspace+'?industry=cleaning#register">Start with cleaning</a></article><article class="industry-choice"><h3>Construction &amp; building trades</h3><p>Commercial renovation, repairs and supported specialist trades.</p><a href="'+workspace+'?industry=construction#register">Start with construction</a></article></section><p>One account keeps your company information, alert preferences and applications together. Already registered? <a href="'+workspace+'#company">Open your company profile</a>.</p>'
    content = re.sub(r'<form\b[^>]*action=["\']https://docs\.google\.com/forms/[^"\']*["\'][^>]*>.*?</form>', chooser, content, flags=re.I | re.S)
    content = re.sub(r'https://docs\.google\.com/forms/[^\s"\'<>]+', workspace+'#register', content)
    return content.replace('</head>', '<link rel="stylesheet" href="/expansion.css"></head>')


def preview_html(content):
    """Make review builds incapable of submitting the public signup or opening checkout."""
    content = content.replace('https://bidbell-workspace.onrender.com', 'http://127.0.0.1:8860')
    content = content.replace('https://getbidbell.com', 'http://127.0.0.1:8861')
    content = re.sub(r'<script\b[^>]*src=["\'][^"\']*(?:paddle|checkout\.js)[^"\']*["\'][^>]*>.*?</script>', '', content, flags=re.I | re.S)
    content = re.sub(r'<script\b[^>]*id=["\']paddle-config["\'][^>]*>.*?</script>', '', content, flags=re.I | re.S)
    # Defense in depth if preview_html is called directly by a renderer.
    if '/expansion.css' not in content:
        content = expansion_html(content)
    content = content.replace('https://bidbell-workspace.onrender.com', 'http://127.0.0.1:8860')
    content = re.sub(r'https://docs\.google\.com/forms/[^\s"\'<>]+', 'http://127.0.0.1:8860/app#register', content)
    content = content.replace('</head>', '<meta name="robots" content="noindex,nofollow"><link rel="stylesheet" href="/staging.css"></head>')
    return re.sub(r'(<body\b[^>]*>)', r'\1<div class="staging-banner" role="note">Staging preview. Fictional accounts only. Production signup, email and billing stay unchanged.</div>', content, count=1, flags=re.I)


def main():
    # Capture once before the build, including a build that crosses UTC midnight.
    build_date = get_build_date()
    # Canonical artifacts and their existing contract checks never inherit the
    # review projection. Only _site receives the caller's staging transform.
    environment = dict(os.environ, BUILD_DATE=build_date, BIDBELL_STAGING='0', BIDBELL_CONSTRUCTION_ENABLED='0')
    subprocess.run([sys.executable, 'tools/build.py'], cwd=ROOT, env=environment, check=True)
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tools', '-p', 'test_*.py'],
                   cwd=ROOT, env=environment, check=True)
    subprocess.run(['node', '--test', 'tools/test_checkout.cjs', 'workspace/core.test.mjs',
                    'prepare/plan.test.mjs'], cwd=ROOT, env=environment, check=True)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    stage_public_assets(commit, build_date)


if __name__ == '__main__':
    main()

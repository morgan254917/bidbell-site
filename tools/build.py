#!/usr/bin/env python3
"""
Builds generated static pages and preserves the authored homepage, workspace and preparation checklist.
Browser scripts support public-data browsing, optional local plans, signup and checkout. Paddle loads only
once tools/paddle.json is configured. favicon.ico, apple-touch-icon.png, icon-512.png and og.png are fixed image files.

  python3 tools/build.py            -> writes every page into the project root
Inputs:  tools/site.json (business facts), tools/paddle.json (Paddle checkout settings), tools/style.css,
         data/cleaning_bids.json (public SAM.gov data)
Run daily by .github/workflows/weekly-bids.yml (drops notices whose deadline has passed); on Mondays
tools/update_bids.py refreshes the bid data first.

Legal review notes are kept in the private repository (bidbell-morgan/legal/), never here:
everything in this public repository, tools/ included, is served on getbidbell.com.
"""
import html, json, os, re, shutil
from datetime import date, datetime, timezone

# ---------------------------------------------------------------- SUPPORT PHONE: SET IT HERE
# Put the US support number between the quotes, e.g. PHONE = '(501) 555-0123', then run python3 tools/build.py.
# Leave it empty ('') to show no phone anywhere. When set, it appears in the footer (next to the email), the Terms
# (Contact), the Privacy Policy (Contact), the Refund policy and /subscribe/.
PHONE = '(413) 255-7289'

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, 'tools')
with open(os.path.join(T, 'site.json'), encoding='utf-8') as source:
    C = json.load(source)
with open(os.path.join(ROOT, 'data', 'cleaning_bids.json'), encoding='utf-8') as source:
    DATA = json.load(source)
# Paddle checkout settings for /subscribe/: {"env": "sandbox" or "production", "client_token", "price_monthly",
# "price_yearly"}. The client-side token is public by design (it only opens checkouts); never put a Paddle API key here.
# While client_token or a price id is empty, /subscribe/ shows "Payments open soon" and loads no Paddle script.
with open(os.path.join(T, 'paddle.json'), encoding='utf-8') as source:
    PADDLE = json.load(source)
PADDLE_READY = all(str(PADDLE.get(k) or '').strip() for k in ('client_token', 'price_monthly', 'price_yearly'))
if PADDLE.get('env') not in ('sandbox', 'production'):
    raise SystemExit('tools/paddle.json: "env" must be "sandbox" or "production"')
if PADDLE_READY and not PADDLE['client_token'].strip().startswith('test_' if PADDLE['env'] == 'sandbox' else 'live_'):
    print(f'warning: tools/paddle.json: a {PADDLE["env"]} client token normally starts with '
          f'{"test_" if PADDLE["env"] == "sandbox" else "live_"}')
BASE = 'https://' + C['domain']
TODAY = date.fromisoformat(os.environ.get('BUILD_DATE', datetime.now(timezone.utc).date().isoformat()))
E = html.escape
PAGES = []          # (path, lastmod) for sitemap

STATES = {'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California', 'CO': 'Colorado',
          'CT': 'Connecticut', 'DE': 'Delaware', 'DC': 'District of Columbia', 'FL': 'Florida', 'GA': 'Georgia',
          'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
          'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland', 'MA': 'Massachusetts',
          'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana',
          'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico',
          'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
          'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota',
          'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington',
          'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming'}
slug = lambda name: name.lower().replace(' ', '-')
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
nice = lambda iso: f"{MONTHS[int(iso[5:7]) - 1]} {int(iso[8:10])}, {iso[:4]}"
long_date = lambda d: d.strftime('%B ') + str(d.day) + d.strftime(', %Y')


def ext(url, text):
    return f'<a href="{E(url)}" rel="noopener noreferrer">{text}</a>'


def phone_link():
    """The support phone (PHONE at the top of this file) as a tap-to-call link, or '' when it is not set."""
    if not PHONE.strip():
        return ''
    digits = re.sub(r'\D', '', PHONE)
    if len(digits) == 10:
        digits = '1' + digits
    if len(digits) != 11 or not digits.startswith('1'):
        raise SystemExit(f'PHONE in tools/build.py must be a US number like (501) 555-0123, not {PHONE!r}')
    return f'<a href="tel:+{digits}">{E(PHONE.strip())}</a>'


# Content-Security-Policy for every page. /subscribe/ adds Paddle's hosts, and only once checkout is configured.
CSP = ("default-src 'none'; img-src 'self'; style-src 'self'; font-src 'self'; script-src 'self'; "
       "connect-src 'self' https://docs.google.com; base-uri 'none'; form-action https://docs.google.com; upgrade-insecure-requests")
# Paddle.js comes from cdn.paddle.com, loads its stylesheet from (sandbox-)cdn.paddle.com and opens the overlay
# checkout in a frame from (sandbox-)buy.paddle.com. 'unsafe-inline' styles let Paddle.js size and place that overlay.
CSP_PADDLE = ("default-src 'none'; img-src 'self' https://*.paddle.com; "
              "style-src 'self' 'unsafe-inline' https://cdn.paddle.com https://sandbox-cdn.paddle.com; font-src 'self'; "
              "script-src 'self' https://cdn.paddle.com https://sandbox-cdn.paddle.com; "
              "frame-src https://buy.paddle.com https://sandbox-buy.paddle.com; connect-src 'self' https://*.paddle.com; "
              "base-uri 'none'; form-action 'none'; upgrade-insecure-requests")


BELL = '<svg aria-hidden="true" focusable="false" viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"><path d="M6 23h20l-3-5v-6a7 7 0 0 0-14 0v6Z"/><path d="M13 27h6M16 3V1"/></svg>'


def start_url():
    return '/start/'


ICON = {
    'check': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>',
    'filter': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 5h18l-7 8.5V19l-4 2v-7.5L3 5z"/></svg>',
    'pin': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    'doc': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h5"/></svg>',
    'clock': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
    'dollar': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 2v20M17 6.5c0-1.9-2.2-3-5-3s-5 1.3-5 3.3S9 9.6 12 10.3s5 1.6 5 3.7-2.2 3.5-5 3.5-5-1.2-5-3"/></svg>',
    'calendar': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4.5" width="18" height="16.5" rx="2"/><path d="M3 9.5h18M8 2.5v4M16 2.5v4M8 14h3"/></svg>',
    'arrow': '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
}


def checks(items):
    return '<ul class="checks">' + ''.join(f'<li>{ICON["check"]}{x}</li>' for x in items) + '</ul>'


WORKSPACE_URL = 'https://bidbell-workspace.onrender.com/app'
NAV_LINKS = [(WORKSPACE_URL, 'Your BidBell workspace'), ('/workspace/', 'Browse notices'), ('/construction-bids/', 'Construction'), ('/#how', 'How it works'),
             ('/start/', 'Start free'), ('/#faq', 'FAQ')]
MENU_ICON = ('<svg class="i-open" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" '
             'stroke-width="2.2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg>'
             '<svg class="i-close" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" '
             'stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>')


def layout(path, title, desc, body, jsonld=None, updated=None, noindex=False, og_type='website', csp=CSP, promo=True):
    """promo=False (sign-up, thank-you and plan pages): no "14 days free" bar and no "Alert trial" button in the
    header, so people who are signing up, just signed up, or are paying are not sent back to the trial offer."""
    url = BASE + '/' + path
    ld = ''.join(f'\n<script type="application/ld+json">{json.dumps(j, separators=(",", ":"))}</script>'
                 for j in (jsonld or []))
    upd = updated or TODAY
    popular = ['Texas', 'California', 'Virginia', 'Florida', 'Illinois', 'Massachusetts']
    state_links = ''.join(f'<li><a href="/cleaning-bids/{slug(s)}/">{s}</a></li>' for s in popular)
    is_404 = path == '404.html'
    canonical = '' if is_404 else f'<link rel="canonical" href="{url}">\n'
    og_url = '' if is_404 else f'<meta property="og:url" content="{url}">\n'
    links = ''.join(f'<a href="{h}"' + (' aria-current="page"' if h == '/' + path else '') + f'>{t}</a>' for h, t in NAV_LINKS)
    topbar = (f'<aside class="topbar" aria-label="BidBell trial offer"><b>Alerts + preparation: 14 days free</b>, no card needed. Then ${C["standard_price"]}/month, '
              f'cancel anytime. <a href="{E(start_url())}">Try the complete workflow &rarr;</a></aside>\n') if promo else ''
    head_cta = f'\n  <a class="btn small head-cta" href="{E(start_url())}">Start free</a>' if promo else ''
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{csp}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="color-scheme" content="light">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
{canonical}{'<meta name="robots" content="noindex">' + chr(10) if noindex else ''}<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="BidBell">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
{og_url}<meta property="og:image" content="{BASE}/og.png?v=20261101-unified">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="BidBell: relevant opportunities and AI-assisted bidding in one plan.">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#141728">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preload" href="/fonts/public-sans.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/style.css?v={"20261101-accessible-steps" if path == "start/" else "20261028-preparation"}">
<link rel="stylesheet" href="/brand.css?v=20261101-one-product">
<script src="/nav.js" defer></script>{ld}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
{topbar}<header class="site-head"><div class="wrap">
  <a class="logo" href="/">{BELL}BidBell<span class="brand-dot" aria-hidden="true">.</span></a>
  <nav class="nav" aria-label="Main">{links}</nav>{head_cta}
  <details class="menu">
    <summary aria-label="Menu">{MENU_ICON}</summary>
    <nav class="menu-panel" aria-label="Menu">{links}{f'<a href="{E(start_url())}">Start free</a>' if promo else ''}</nav>
  </details>
</div></header>
<main id="main">
{body}
</main>
<footer class="site-foot"><div class="wrap">
  <div class="foot-grid">
    <div class="brand">
      <a class="logo" href="/">{BELL}BidBell<span class="brand-dot" aria-hidden="true">.</span></a>
      <p class="foot-about">Find relevant opportunities, reuse company information and build stronger applications with AI. One BidBell plan, from daily alert to delivery record.</p>
      <p class="small">{E(C['mailing_address'])}<br><a href="mailto:{C['email']}">{C['email']}</a>{' &middot; ' + phone_link() if PHONE.strip() else ''}</p>
    </div>
    <nav aria-label="Product"><h2>Product</h2><ul>
      <li><a href="{WORKSPACE_URL}">Your BidBell workspace</a></li><li><a href="{WORKSPACE_URL}#opportunities/open">Still-open bids</a></li><li><a href="{WORKSPACE_URL}#calendar">Bid calendar</a></li><li><a href="/workspace/">Public notice preview</a></li><li><a href="/prepare/">Public checklist preview</a></li><li><a href="/#how">How it works</a></li><li><a href="/#pricing">Pricing</a></li><li><a href="/#faq">FAQ</a></li><li><a href="{E(start_url())}">Start free</a></li></ul></nav>
    <nav aria-label="Cleaning notices by state"><h2>Cleaning by state</h2><ul>{state_links}<li><a href="/cleaning-bids/">All states &rarr;</a></li></ul></nav>
    <nav aria-label="Company"><h2>Company</h2><ul>
      <li><a href="/#about">About</a></li><li><a href="/terms/">Terms</a></li><li><a href="/privacy/">Privacy</a></li><li><a href="/refunds/">Refund policy</a></li><li><a href="/acceptable-use/">Acceptable use</a></li><li><a href="/disclaimer/">Disclaimer</a></li><li><a href="/email-policy/">Email policy</a></li><li><a href="https://www.facebook.com/profile.php?id=61595464021652" rel="noopener">BidBell on Facebook</a></li></ul></nav>
  </div>
  <div class="foot-bottom">
    <span>&copy; {TODAY.year} BidBell. Run by {E(C['owner_name'])}. Page updated {long_date(upd)}.</span>
    <span>Not affiliated with SAM.gov, GSA or any government agency.</span>
  </div>
</div></footer>
</body>
</html>
'''


def write(path, content, lastmod=None, sitemap=True):
    full = os.path.join(ROOT, path, 'index.html') if (path == '' or path.endswith('/')) else os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    # Keep raw notice evidence untouched; normalize punctuation only in rendered pages.
    content = content.replace(chr(8212), ' - ').replace('&mdash;', ' - ').replace('&#8212;', ' - ').replace('&#x2014;', ' - ')
    open(full, 'w', encoding='utf-8', newline='\n').write(content)
    if sitemap:
        PAGES.append((path, (lastmod or TODAY).isoformat()))


# ------------------------------------------------------------------ shared blocks
TYPE_WORDS = {'Solicitation': 'Bid open', 'Combined Synopsis/Solicitation': 'Bid open (quotes)',
              'Presolicitation': 'Coming soon', 'Sources Sought': 'Market research'}


SMALL = {'Of', 'The', 'And', 'For', 'In', 'On', 'At', 'To'}
fix_case = lambda t: ' '.join(w if i == 0 or w not in SMALL else w.lower() for i, w in enumerate(t.split()))
clean_title = lambda t: re.sub(r'\s+l\s+', ', ', re.sub(r'^[A-Z0-9]{1,4}--\s*', '', t or '')).strip()


def bid_table(bids, caption):
    rows = []
    for b in bids:
        where = ', '.join(x for x in (b['city'].strip(), STATES.get(b['state'], b['state'])) if x and x != '0')
        rows.append(f'<tr><td class="c-notice" data-label="Notice">{ext(b["link"], E(clean_title(b["title"])))}<br><span class="small muted">{E(agency_name(b["agency"]))}'
                    f'{" &middot; <span class=nowrap>Ref " + E(b["sol"]) + "</span>" if b["sol"] else ""}</span></td>'
                    f'<td data-label="Work site">{E(where)}</td><td class="nowrap" data-label="Respond by">{nice(b["due"])}</td>'
                    f'<td data-label="Stage">{E(TYPE_WORDS.get(b["type"], b["type"]))}</td>'
                    f'<td class="c-who" data-label="Who can bid">{E(who_can_bid(b["set_aside"]))}</td></tr>')
    return (f'<div class="table-wrap"><table class="stack bids"><caption>{caption}</caption><thead><tr><th scope="col">Notice</th>'
            f'<th scope="col">Work site</th><th class="nowrap" scope="col">Respond by</th><th scope="col">Stage</th>'
            f'<th scope="col">Who can bid</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def cta_box(heading='Get the right bids every morning instead'):
    return f'''<div class="cta-band">
  <h2>{heading}</h2>
  <p>This page is a free weekly snapshot. Your BidBell plan combines a daily shortlist matched to your business with a workspace to prepare the response. Open a matching alert, add the bid documents, reuse company facts and approved answers, then review your message and files. Send supported email bids after your final confirmation, or continue through the buyer's required portal.</p>
  <div class="cta-row"><a class="btn light" href="{E(start_url())}">Start 14 days free {ICON['arrow']}</a></div>
  {checks(['14 days free, no card', f"US${C['standard_price']}/month for alerts + preparation", 'Cancel anytime'])}
</div>'''


# ------------------------------------------------------------------ home
def who_can_bid(sa):
    """SAM.gov's set-aside wording -> the plain words the alert email uses ('Small businesses only' ...). SAM uses two
    spellings for the same set-aside: the API's ("Total Small Business Set-Aside") and the public CSV's ("Small Business
    Set Aside - Total", with "(FAR 19.13)" style suffixes), so this matches on key words. Unknown wording is shown as
    it is."""
    s = (sa or '').lower()
    if not s or 'no set aside' in s or s == 'none':
        return 'Open to all businesses'
    if 'sole source' in s:
        return 'One named veteran-owned firm only' if 'veteran' in s else 'One named firm only'
    for key, words in (('hubzone', 'HUBZone small businesses only'),
                       ('service-disabled', 'Service-disabled veteran-owned only'),
                       ('economically disadvantaged', 'Economically disadvantaged women-owned only'),
                       ('edwosb', 'Economically disadvantaged women-owned only'),
                       ('women-owned', 'Women-owned small businesses only'), ('wosb', 'Women-owned small businesses only'),
                       ('8(a)', '8(a) program firms only'), ('veteran-owned', 'Veteran-owned small businesses only'),
                       ('indian', 'Indian-owned businesses only'), ('local area', 'Local businesses only'),
                       ('partial', 'Small businesses only (partial)'), ('small business', 'Small businesses only')):
        if key in s:
            return words
    return sa


STAGE = {'Solicitation': 'BID OPEN', 'Combined Synopsis/Solicitation': 'BID OPEN',
         'Presolicitation': 'COMING SOON', 'Sources Sought': 'GET NOTICED'}

def agency_name(a):
    a = (a or 'Federal agency').strip()
    if a.lower().endswith(', department of'):
        a = 'Department of ' + a[:-len(', department of')]
    return fix_case(a.replace('Dept Of', 'Department Of'))


def open_bids(min_days=0):
    return sorted((b for b in DATA['bids'] if (date.fromisoformat(b['due']) - TODAY).days >= min_days), key=lambda b: b['due'])


def home():
    """Preserve authored product pages rather than regenerate an old homepage."""
    homepage = os.path.join(ROOT, 'index.html')
    if not os.path.isfile(homepage):
        raise SystemExit('Authored index.html is missing. Restore the current homepage; no fallback will be generated.')
    with open(homepage, encoding='utf-8-sig') as source:
        content = source.read()
    if '/home.css' not in content:
        raise SystemExit('Authored homepage marker /home.css is missing. Refusing to generate a legacy homepage.')
    for path in ('workspace/', 'prepare/'):
        if not os.path.isfile(os.path.join(ROOT, path, 'index.html')):
            raise SystemExit(f'Authored {path}index.html is missing. Restore it before building navigation and sitemap.')
    PAGES.extend((path, TODAY.isoformat()) for path in ('', 'workspace/', 'prepare/'))


# ------------------------------------------------------------------ start (sign-up)
TRADE_CHOICES = ['Janitorial / custodial', 'Carpet & upholstery cleaning', 'Window & exterior cleaning']
CERT_CHOICES = ['Small business (by SBA size standards)', 'HUBZone certified', 'Service-disabled veteran-owned (SDVOSB)',
                '8(a) program', 'Women-owned (WOSB or EDWOSB)', 'None of these / not sure']
SAM_CHOICES = ['Yes, active', 'In progress', 'Not yet']
NATIONWIDE = 'Nationwide (all states)'
AGREE = 'I agree to the BidBell Terms (getbidbell.com/terms) and Privacy Policy (getbidbell.com/privacy).'


def signup_form():
    f = C.get('form_entries') or {}
    post = C.get('form_post', '')
    if not (post and f):
        return None
    opt = lambda kind, name, v, cls='option': (f'<label class="{cls}"><input type="{kind}" name="{name}" value="{E(v)}"><span>{E(v)}</span></label>')
    state_names = sorted(STATES.values())
    states = (f'<label class="all"><input type="checkbox" name="{f["states"]}" value="{NATIONWIDE}"> Nationwide (all states)</label>'
              + ''.join(f'<label><input type="checkbox" name="{f["states"]}" value="{E(s)}"> {E(s)}</label>' for s in state_names))
    return f'''<form class="signup" id="signup" action="{E(post)}" method="post" accept-charset="utf-8">
  <div class="form-error" id="form-error" role="alert" hidden></div>
  <fieldset>
    <legend>About you</legend>
    <p class="hint">Every question is required unless it says optional.</p>
    <div class="fields">
      <div class="field"><label for="f-first">First name</label><input id="f-first" type="text" name="{f['first']}" required autocomplete="given-name"></div>
      <div class="field"><label for="f-email">Business email</label><input id="f-email" type="email" name="{f['email']}" required autocomplete="email" autocapitalize="off" spellcheck="false" placeholder="you@company.com"></div>
      <div class="field"><label for="f-biz">Business name</label><input id="f-biz" type="text" name="{f['business']}" required autocomplete="organization"></div>
      <div class="field"><label for="f-web">Business website <span class="opt">(optional)</span></label><input id="f-web" type="text" inputmode="url" name="{f['website']}" autocomplete="url" autocapitalize="off" spellcheck="false" placeholder="yourcompany.com"></div>
    </div>
  </fieldset>
  <fieldset data-need="1" data-label="the available services you need" aria-describedby="h-trades">
    <legend>Available daily alerts</legend>
    <p class="hint" id="h-trades">Choose the supported services your team currently delivers. Daily alerts currently cover these cleaning services. HVAC maintenance and grounds coverage is being validated; email hello@getbidbell.com about those trades. They are not included in this signup.</p>
    <p class="field-error" id="e-trades" role="alert" hidden></p>
    <div class="options">{''.join(opt('checkbox', f['trades'], v) for v in TRADE_CHOICES)}</div>
  </fieldset>
  <fieldset data-need="1" data-max="10" data-label="your states" aria-describedby="h-states">
    <legend>Which states do you work in?</legend>
    <p class="hint" id="h-states">Choose up to 10 states you can actually serve, or Nationwide. We use the stated work location when available, not just the agency office.</p>
    <p class="field-error" id="e-states" role="alert" hidden></p>
    <label class="state-search-label" for="state-search">Find a state</label><input id="state-search" class="state-search" type="search" placeholder="Search by state name" autocomplete="off" aria-controls="state-options"><p id="state-search-status" class="small muted" aria-live="polite"></p>
    <div class="state-box" id="state-options">{states}</div>
    <p class="state-count" id="state-count" aria-live="polite"></p>
  </fieldset>
  <fieldset data-need="1" data-exclusive="None of these / not sure" data-label="at least one answer to &ldquo;Is your business any of these?&rdquo; (or &ldquo;None of these / not sure&rdquo;)" aria-describedby="h-certs">
    <legend>Is your business any of these?</legend>
    <p class="hint" id="h-certs">Used to filter notices by stated set-aside. Select only current statuses; choose None of these / not sure if uncertain. That answer clears other statuses. Verify the full notice before bidding.</p>
    <p class="field-error" id="e-certs" role="alert" hidden></p>
    <div class="options cols-2">{''.join(opt('checkbox', f['certs'], v) for v in CERT_CHOICES)}</div>
  </fieldset>
  <fieldset>
    <legend>Are you registered in SAM.gov?</legend>
    <p class="hint">You can start your trial either way.</p>
    <div class="options cols-3">{''.join(opt('radio', f['sam'], v).replace('type="radio"', 'type="radio" required', 1) for v in SAM_CHOICES)}</div>
  </fieldset>
  <div class="form-foot">
    <label class="agree"><input type="checkbox" name="{f['agree']}" value="{E(AGREE)}" required><span>I agree to the BidBell <a href="/terms/">Terms</a> and <a href="/privacy/">Privacy Policy</a>.</span></label>
    <button class="btn" type="submit">Start my free 14 days {ICON['arrow']}</button>
    <p class="small muted">No card needed. Your signup finishes on Google Forms. Look for its confirmation before closing.</p>
  </div>
</form>
<script src="/form.js?v=20261101-clear-signup" defer></script>'''


def coverage_block():
    if os.environ.get('BIDBELL_STAGING') == '1':
        return '<section class="card coverage-status"><p class="eyebrow">ONE BIDBELL. YOUR INDUSTRY.</p><h2>Start with the work your team can deliver.</h2><p>Choose cleaning or construction, then save your trade, territory and company information in the same workspace.</p><p>Coverage is source-specific. This staged expansion has not been published.</p></section>'
    return '<section class="card coverage-status" aria-labelledby="coverage-heading"><p class="eyebrow">BUILDING-SERVICE CONTRACTORS</p><h2 id="coverage-heading">Choose coverage that is ready for your trade.</h2><p><strong>Available daily alerts:</strong> janitorial, carpet, window and exterior cleaning.</p><p><strong>Coverage being validated:</strong> HVAC maintenance and landscaping / grounds maintenance. These trades are not included in the current trial or paid plans.</p><p><a href="mailto:hello@getbidbell.com?subject=Expanded%20trade%20coverage">Tell us your trade and service area</a> to ask about future coverage.</p></section>'


def start():
    form = signup_form()
    if form:
        action = f'<div class="card form-card"><div class="signup-form-intro"><span class="eyebrow">START WITH THE RIGHT OPPORTUNITIES</span><h2>What work fits your business?</h2><p>These preferences shape your daily alerts. Next, use this same email to open your BidBell workspace and build your response.</p></div>{form}</div>'
    else:
        if C['form_url']:
            btn = f'<a class="btn" href="{E(C["form_url"])}" rel="noopener noreferrer">Open the 2-minute sign-up form {ICON["arrow"]}</a>'
            note = 'The form is hosted by Google Forms. Your answers go to BidBell&rsquo;s private account.'
        else:
            body_txt = ('First name:%0D%0ABusiness name:%0D%0ABusiness website:%0D%0ATrades (janitorial / carpet / window-exterior):%0D%0A'
                        'States (up to 10, or all):%0D%0AEligibility (small business / HUBZone / SDVOSB / 8(a) / WOSB / none):%0D%0A'
                        'Registered in SAM.gov (yes / in progress / no):')
            btn = f'<a class="btn" href="mailto:{C["email"]}?subject=Free%202-week%20trial&amp;body={body_txt}">Email us to start your trial {ICON["arrow"]}</a>'
            note = 'This opens an email with the questions filled in. Just answer and send.'
        action = f'''<div class="card form-card">
  <h2 class="h-sm">Six short questions</h2>
  <ol class="plain-list"><li>Your first name and business email</li><li>Your business name and website</li><li>Your trades: janitorial, carpet, window or exterior cleaning</li><li>Your states: up to 10, or nationwide</li><li>Your eligibility: small business, HUBZone, SDVOSB, 8(a), WOSB, or none</li><li>Whether you are registered in SAM.gov</li></ol>
  <div class="cta-row">{btn}</div><p class="small muted">{note}</p>
</div>'''
    body = f'''<div class="page-head signup-head"><div class="wrap">
  <p class="crumbs"><a href="/">Home</a> / Start your BidBell trial</p>
  <p class="eyebrow">YOUR FREE 14 DAYS START HERE</p><h1>Your next opportunity.<br>A faster start.</h1>
  <p class="lead">Get matching daily alerts, keep your company information ready and build a stronger response with source-linked AI. Tell us what fits your business, then verify the same email in your workspace. One BidBell plan. No card needed.</p>
  <div class="journey-strip" aria-label="Your BidBell workflow"><span>01 Find a matching bid</span><span>02 Reuse your details</span><span>03 Draft with AI</span><span>04 Review and send</span><span>05 Track the result</span></div>
</div></div>
<div class="wrap page signup-page">{coverage_block()}<div class="signup-grid">
  {action}
  <aside class="aside">
    <div class="card">
      <p class="eyebrow">WHAT HAPPENS NEXT</p><h2>One place to move the bid forward.</h2>
      <ol class="next-steps">
        <li><span class="step-index" aria-hidden="true">1</span><div><b>Get your matching shortlist</b><span>After signup processing, look for your welcome email. Alerts normally arrive around 6 AM your time from the next morning, with a short update on quiet days.</span></div></li>
        <li><span class="step-index" aria-hidden="true">2</span><div><b>Open the bid in BidBell</b><span>Create and verify your workspace account with the same email. Open an opportunity from your alert and keep that bid and its response together.</span></div></li>
        <li><span class="step-index" aria-hidden="true">3</span><div><b>Reuse what your company knows</b><span>Add the buyer's documents, reuse saved company facts and original files, and draft answers with source-linked AI. Complete supported fillable PDF text fields from reviewed facts, then check missing details and pricing. Answer drafts autosave privately; review and choose Save answer to add them to your response.</span></div></li>
        <li><span class="step-index" aria-hidden="true">4</span><div><b>Review and send your bid</b><span>Check the buyer’s submission recipients, message, price and files, then confirm a supported email send in BidBell. Portal bids continue through the buyer’s portal. Keep the delivery record and emailed receipt together. Record the buyer’s response when you receive it. You approve each send; BidBell does not sign declarations.</span></div></li>
      </ol>
      <div class="trial-summary"><strong>One trial. One US${C['standard_price']}/month plan.</strong><p>Your trial includes matching alerts and the application workspace for 14 days. We send a reminder before the end. Continue only if you choose to subscribe; nothing is charged automatically. Usage limits apply.</p></div>
    </div>
    <div class="card">
      <h2>Already with BidBell?</h2><p><a href="https://bidbell-workspace.onrender.com/app#account">Open Account and billing</a> with your alert email to connect existing access. Your original trial dates and existing annual terms stay the same. Reply to an alert to update your preferences; no second signup is needed.</p>
    </div>
    <div class="card">
      <h2>Keep private details private</h2>
      <p>Never send passwords, card numbers, tax IDs or government ID numbers by email. Set your workspace password only on BidBell's account page. See our <a href="/privacy/">privacy policy</a> for how we handle your details.</p>
    </div>
  </aside>
</div></div>'''
    thanks = f'''<div class="page-head"><div class="wrap">
  <p class="crumbs"><a href="/">Home</a> / <a href="/start/">Start free</a> / Done</p>
  <h1>Check your submission.</h1>
  <p class="lead">Google Forms displays a confirmation when your answers are accepted. Visiting this page does not confirm your sign-up or start a trial. After your details are processed, look for a BidBell welcome email.</p>
  <div class="cta-row"><a class="btn" href="/#sample">See what an alert looks like</a><a class="btn ghost" href="https://bidbell-workspace.onrender.com/app">Create your BidBell workspace account</a></div>
  <p class="small muted">No welcome email within an hour? Check your spam folder, then write to <a href="mailto:{C['email']}">{C['email']}</a> so we can make sure your sign-up reached us. Something wrong, or want to change your states? Email us at the same address.</p>
</div></div>'''
    if os.environ.get('BIDBELL_STAGING') == '1':
        body = re.sub(r'<ol class="next-steps">.*?</ol>', '''<ol class="next-steps">
        <li><span class="step-index" aria-hidden="true">1</span><div><b>Choose your industry</b><span>Create and verify one BidBell account. Select your trade and service area.</span></div></li>
        <li><span class="step-index" aria-hidden="true">2</span><div><b>Find suitable work</b><span>Open matching opportunities and check the buyer's scope, deadlines and eligibility.</span></div></li>
        <li><span class="step-index" aria-hidden="true">3</span><div><b>Reuse your information</b><span>Save company details and documents. Review AI-assisted answers, missing items and your price.</span></div></li>
        <li><span class="step-index" aria-hidden="true">4</span><div><b>Review, submit and track</b><span>Approve the exact package. Use supported email delivery or the buyer's portal. Keep delivery evidence and buyer confirmation distinct.</span></div></li>
      </ol>''', body, count=1, flags=re.S)
        body = body.replace('Tell us what fits your business, then verify the same email in your workspace.', 'Choose your industry, create one account and save what fits your business.')
        thanks = '<div class="wrap page"><h1>Continue in your BidBell account.</h1><p>This preview uses one local account. Complete email verification and choose your industry, trade and service area there. No production signup or welcome email is sent.</p><a class="btn" href="'+WORKSPACE_URL+'#company">Open company profile</a></div>'
    write('start/thanks/', layout('start/thanks/', 'Sign-up next steps | BidBell', 'How to check your BidBell sign-up.', thanks, noindex=True, promo=False), sitemap=False)
    write('start/', layout('start/', 'Start your free 14 days | BidBell',
                           'Try matching bid alerts and AI-assisted bidding together for 14 days. One BidBell plan, US$39/month if you continue. No card needed.', body,
                           promo=False))


# ------------------------------------------------------------------ subscribe (trial customers choose a plan)
def subscribe():
    """Verified-account entry and landing page for server-created Paddle transactions."""
    sp = C['standard_price']
    mail = f'<a href="mailto:{C["email"]}">{C["email"]}</a>'
    agree = 'By continuing you agree to the <a href="/terms/">Terms</a> and the <a href="/refunds/">Refund Policy</a>.'

    plans = (f'<div class="plan best"><h3>One BidBell plan</h3><p class="price">US${sp}<span> /month</span></p>'
             '<p class="desc">Relevant alerts, saved company details, supported forms and reviewed email bids together. Renews monthly only after you choose to subscribe.</p>'
             '<p><a class="btn" href="https://bidbell-workspace.onrender.com/app#account">Sign in and continue</a></p>'
             '<p class="small">Your verified account checks alert enrollment and existing subscriptions before creating checkout.</p></div>')
    if PADDLE_READY:
        cfg = {'env': PADDLE['env'], 'client_token': PADDLE['client_token'].strip(),
               'prices': {'monthly': PADDLE['price_monthly'].strip(), 'yearly': PADDLE['price_yearly'].strip()},
               'success_url': BASE + '/subscribe/thanks/'}
        cfg_json = json.dumps(cfg, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
        alert = (f'<div class="form-error checkout-error" id="checkout-error" role="alert" hidden>The secure checkout could not load. '
                 f'Please refresh the page and try again, or email {mail}.</div>')
        foot = (f'<p class="small muted">Prices in US dollars. Checkout is handled by Paddle.com, our merchant of record. '
                f'Any sales tax is shown before you pay. Your receipt comes from Paddle. You can cancel anytime with the '
                f'&ldquo;Manage subscription&rdquo; link in that receipt, or by replying to any BidBell email.</p>')
        scripts = (f'\n<script type="application/json" id="paddle-config">{cfg_json}</script>'
                   '\n<script src="https://cdn.paddle.com/paddle/v2/paddle.js" defer></script>'
                   '\n<script src="/checkout.js" defer></script>')
    else:
        alert = (f'<div class="note soon-note"><p>Payments open soon. We\'ll email you as soon as you can subscribe; your alerts keep going until then.</p></div>')
        foot = f'<p class="small muted">Prices in US dollars. {agree}</p>'
        scripts = '\n<script src="/checkout.js" defer></script>'
    phone = f' or call {phone_link()}' if PHONE.strip() else ''
    body = f'''<div class="page-head"><div class="wrap">
  <p class="crumbs"><a href="/">Home</a> / Choose your plan</p>
  <h1>Choose your plan</h1>
  <p class="lead">Find the work. Build and send your bid. Keep daily alerts, reusable company details and supported email applications in one plan. Use the same email for your alert preferences, workspace and payment.</p>
</div></div>
<div class="wrap page">
  <h2 class="sr-only">Plans</h2>
  {coverage_block()}
  {alert}
  <div class="note"><p><strong>New to BidBell?</strong> <a href="/start/">Set up your alert preferences</a> first, then create and verify your workspace account with the same email. Your 14-day no-card trial covers both. No payment is taken automatically at its end.</p></div>
  <div class="plans">{plans}</div>
  <div class="note"><p><strong>Already subscribed?</strong> Connect your existing subscription in Account and billing before considering another checkout. Existing annual plans keep their current terms. Do not buy a second subscription.</p></div>
  <div class="subscribe-foot">
    {foot}
    <p class="small muted">Questions? Email {mail}{phone}.</p>
  </div>
</div>{scripts}'''
    thanks = f'''<div class="page-head"><div class="wrap">
  <p class="crumbs"><a href="/">Home</a> / Subscription</p>
  <h1>Check your subscription status.</h1>
  <p class="lead">Paddle emails a receipt when payment succeeds. Open Account and billing in your BidBell workspace with the same email to confirm and link your subscription. This page alone does not confirm payment or access. If you have not set up your alert preferences, complete the free signup first.</p>
  <div class="cta-row"><a class="btn" href="https://bidbell-workspace.onrender.com/app#account">Open Account and billing</a><a class="btn ghost" href="/refunds/">Refund policy</a></div>
  <p class="small muted">Questions about your plan, or want to cancel? Email {mail}{phone}, or reply to any BidBell email.</p>
</div></div>'''
    write('subscribe/thanks/', layout('subscribe/thanks/', 'Subscription next steps | BidBell',
                                      'Confirm and link your BidBell subscription.', thanks, noindex=True, promo=False), sitemap=False)
    write('subscribe/', layout('subscribe/', 'Choose your plan | BidBell',
                               f'Alerts and bid preparation together for US${sp}/month. Verify your existing account before checkout.',
                               body, noindex=True, csp=CSP_PADDLE if PADDLE_READY else CSP, promo=False), sitemap=False)


# ------------------------------------------------------------------ public bid pages (gamechanger 1)
def bid_pages():
    upd = date.fromisoformat(DATA['updated'])
    bids = [b for b in DATA['bids'] if b['due'] >= TODAY.isoformat()]   # drop notices whose deadline has passed
    by_state = {}
    for b in bids:
        by_state.setdefault(b['state'], []).append(b)
    teaser = (f'<p class="small muted">Last updated {long_date(upd)} from SAM.gov public data. This free page is updated weekly. It lists the open notices '
              f'filed under the federal cleaning codes (NAICS 561720, 561740 and 561790), not filtered for any business. It is not a substitute for reading the official notice.</p>')

    def other_states(skip=None):
        items = ''.join(f'<li><a href="/cleaning-bids/{slug(STATES[s])}/">{STATES[s]}</a> ({len(by_state[s])})</li>'
                        for s in sorted(by_state, key=lambda s: STATES.get(s, s)) if s != skip and s in STATES)
        return f'<ul class="state-list">{items}</ul>' if items else '<p class="muted">No other states have open notices this week.</p>'

    for code, name in STATES.items():
        sb = by_state.get(code, [])
        if sb:
            lst = bid_table(sb, f'{len(sb)} open federal cleaning notice{"s" if len(sb) != 1 else ""} in {name}')
        else:
            lst = f'<div class="note"><p>No open federal cleaning notices were listed for {name} in this week&rsquo;s data. Daily alerts check available sources for new matches against your selected services, location and eligibility filters.</p></div>'
        body = f'''<div class="page-head"><div class="wrap">
<p class="crumbs"><a href="/">Home</a> / <a href="/cleaning-bids/">Cleaning bids</a> / {E(name)}</p>
<h1>Open federal cleaning bids in {E(name)}</h1>
<p class="lead">Janitorial, custodial, carpet and window-cleaning contract opportunities from federal agencies with work in {E(name)}.</p>
{teaser}
</div></div>
<div class="wrap page">
{lst}
<div class="mt">{cta_box(f"Get {E(name)} cleaning bids every morning")}</div>
<h2 class="mt">Other states with open cleaning notices</h2>
{other_states(code)}
</div>'''
        path = f'cleaning-bids/{slug(name)}/'
        write(path, layout(path, f'Federal cleaning bids in {name} | BidBell',
                           f'Open federal janitorial, custodial, carpet and window-cleaning bids in {name}, updated weekly from SAM.gov. Last updated {long_date(upd)}.',
                           body, updated=upd), lastmod=upd)

    for trade, label, words in (('carpet', 'Carpet cleaning', 'carpet and upholstery cleaning'),
                                ('window', 'Window and exterior cleaning', 'window and exterior building cleaning')):
        tb = [b for b in bids if b['trade'] == trade]
        lst = bid_table(tb, f'{len(tb)} open federal {words} notices') if tb else \
            f'<div class="note"><p>No open federal {words} notices were listed in this week&rsquo;s data.</p></div>'
        body = f'''<div class="page-head"><div class="wrap">
<p class="crumbs"><a href="/">Home</a> / <a href="/cleaning-bids/">Cleaning bids</a> / {label}</p>
<h1>Open federal {words} bids</h1>
{teaser}
</div></div>
<div class="wrap page">
{lst}
<div class="mt">{cta_box()}</div>
</div>'''
        path = f'cleaning-bids/{trade}/'
        write(path, layout(path, f'Federal {words} bids | BidBell',
                           f'Open US federal {words} contract opportunities, updated weekly from SAM.gov. Last updated {long_date(upd)}.',
                           body, updated=upd), lastmod=upd)

    total = len(bids)
    body = f'''<div class="page-head"><div class="wrap">
<p class="crumbs"><a href="/">Home</a> / Cleaning bids</p>
<h1>Open federal cleaning bids by state</h1>
<p class="lead">Open federal janitorial, carpet and window-cleaning contract notices, grouped by where the work is. Free, updated weekly.</p>
{teaser}
</div></div>
<div class="wrap page">
<p><strong>{total}</strong> open notices this week. Also see <a href="/cleaning-bids/carpet/">carpet cleaning</a> and <a href="/cleaning-bids/window/">window and exterior cleaning</a>.</p>
<h2>States with open notices</h2>
{other_states()}
<h2>All states</h2>
<ul class="state-list">{''.join(f'<li><a href="/cleaning-bids/{slug(n)}/">{n}</a></li>' for n in STATES.values())}</ul>
<div class="mt">{cta_box()}</div>
</div>'''
    write('cleaning-bids/', layout('cleaning-bids/', 'Federal cleaning bids by state | BidBell',
                                   f'Open US federal janitorial, carpet and window-cleaning bids in every state, updated weekly from SAM.gov. Last updated {long_date(upd)}.',
                                   body, updated=upd), lastmod=upd)


# ------------------------------------------------------------------ legal
def legal_page(path, title, desc, inner):
    upd = date.fromisoformat(C['legal_updated'])
    body = (f'<div class="page-head"><div class="wrap"><p class="crumbs"><a href="/">Home</a> / {title}</p><h1>{title}</h1>'
            f'<p class="muted flush">Existing alert policy date: {long_date(upd)}</p></div></div>'
            f'<div class="wrap narrow legal page">{inner}</div>')
    write(path, layout(path, f'{title} | BidBell', desc, body, updated=upd), lastmod=upd)


def legal():
    seller = f'{E(C["owner_name"])}, trading as BidBell (&ldquo;BidBell&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;)'
    contact = f'Mailing address: {E(C["mailing_address"])}. Email: <a href="mailto:{C["email"]}">{C["email"]}</a>'
    phone = f' Phone: {phone_link()}.' if PHONE.strip() else ''
    mail = f'<a href="mailto:{C["email"]}">{C["email"]}</a>'
    sp, ap = C['standard_price'], C['annual_price']

    legal_page('terms/', 'Terms of Service', 'The terms that apply when you use BidBell.', f'''
<section class="pilot-note"><h2>One BidBell subscription</h2>
<p>BidBell includes supported daily bid alerts and access to the bid preparation workspace in the existing US$39/month subscription. Existing annual subscriptions retain their current terms. New no-card trials cover both for 14 days; existing trials keep their original end date. Use and verify the same email as your alert subscription to link access. Workspace registration does not start a second trial.</p>
<p>The workspace helps organize documents, requirements, company facts, answers and pricing. It retains original files saved for reuse and submission and can fill supported standard PDF text fields from explicitly reviewed facts. Document size and account storage limits apply and are shown in the workspace. Supported email submission requires original buyer instructions specifying all supported submission recipients, a current-notice and deadline check, and your review and final confirmation of the exact message and files. Portal-only submissions continue in the buyer's portal. Mail-server acceptance is not proof of buyer receipt; uncertain delivery is not automatically retried. BidBell does not sign declarations. AI suggestions require your review and are subject to usage limits. You remain responsible for official notices, amendments, eligibility, complete forms and final submission. BidBell does not promise completeness, compliance or an award.</p></section>
<p>These terms are an agreement between you (the business using BidBell, and the person accepting for it) and {seller}. {contact}. By starting a trial or subscription you accept them. Nothing in these terms takes away rights you have under a law that cannot be excluded by contract.</p>
<h2>1. What BidBell is</h2>
<p>BidBell provides contract opportunity alerts for building-service contractors. Current paid and trial alert coverage is limited to janitorial, carpet, window and exterior cleaning. HVAC maintenance and grounds coverage is being validated and is not included in current plans. Each morning we read new US federal contract notices published on SAM.gov, select the ones that match the trades, states and eligibility you give us, and email them to you. Where we can, we add information from USAspending.gov about the likely current or previous contract for the same work. Your alerts also carry reminders and updates for bids we sent you and, on Mondays, federal contracts in your states that end in 3 to 6 months. We send a daily email, including a short status update when there are no new matching notices. We also publish free public pages listing open federal cleaning notices by state. We are not a government service, a bidding agent, a law firm or a consultant.</p>
<h2>2. Free BidBell trial</h2>
<p>New customers get one free 14-day trial covering alerts and preparation. We do not ask for a card to start it. Existing trial dates are not extended by workspace registration. If you do not subscribe, alerts and preparation access end when the trial ends, saved work remains accessible, and nothing is charged.</p>
<h2>3. Plans, payment and taxes</h2>
<p>BidBell is operated by {E(C["owner_name"])}, a sole proprietor (not a registered company) trading as BidBell. Our US mailing address is {E(C["mailing_address"])}.</p>
<p>Our order process is conducted by our online reseller Paddle.com. Paddle.com is the Merchant of Record for all our orders. Paddle provides all customer service inquiries and handles returns.</p>
<p>The current plan includes alerts and preparation for US${sp}/month, billed in advance. Existing annual subscriptions retain their agreed US${ap}/year terms; no new annual plan is offered here. Paddle charges your payment method, sends your receipt and collects any sales tax, which is shown at checkout. Paddle&rsquo;s own terms apply to the purchase. We never see or store your card details.</p>
<p>Your subscription renews automatically at the end of each month or year, and the plan price is charged for the next period, until you cancel. We may change our prices; we will email you at least 30 days before a change affects your next renewal, and you can cancel before it does.</p>
<h2>4. Cancelling and refunds</h2>
<p>You can cancel anytime by emailing <a href="mailto:{C["email"]}">{C["email"]}</a>, by replying to any BidBell email, or with the &ldquo;Manage subscription&rdquo; link in your receipt from Paddle. Your alerts and preparation access continue until the end of the period you have paid for, and you are not charged again. Every payment has a 30-day money-back guarantee; see our <a href="/refunds/">Refund Policy</a>.</p>
<h2>5. Your responsibilities</h2>
<p>You are responsible for giving us accurate details, for reading the full official notice and its attachments before relying on any bid, for checking deadlines, eligibility and requirements yourself, for your registration in SAM.gov, and for every decision to bid or not bid. You must follow our <a href="/acceptable-use/">acceptable use policy</a>.</p>
<h2>6. Accuracy of information</h2>
<p>BidBell is provided &ldquo;as is&rdquo; and &ldquo;as available&rdquo;. We work carefully, but the information comes from public government sources that can be incomplete, late, amended or withdrawn, and our matching (for example of work sites, eligibility and likely current contracts) can be wrong. To the fullest extent the law allows, we make no warranties, express or implied, including that every relevant notice will be found, that any information is accurate or complete, that the service will be uninterrupted, or that you will win any contract. See our <a href="/disclaimer/">disclaimer</a>.</p>
<h2>7. Limitation of liability</h2>
<p>To the fullest extent the law allows: (a) we are not liable for any indirect, incidental, special or consequential loss, or for lost profits, revenue, contracts or business opportunities; (b) we are not liable for any notice that we did not send, sent late, or that was changed or withdrawn, or for the outcome of any bid; and (c) our total liability for all claims relating to BidBell is limited to the fees you paid for BidBell in the 3 months before the event giving rise to the claim. These limits do not apply to liability that cannot be limited by law, such as for fraud.</p>
<h2>8. Indemnity</h2>
<p>You agree to compensate us for reasonable losses and costs (including reasonable legal fees) arising from your breach of these terms, your misuse of BidBell, or your resale or republishing of our alerts.</p>
<h2>9. Suspension and ending the service</h2>
<p>We may suspend or end your access if you break these terms, if payment fails, or if we stop offering BidBell. If we end the service for reasons other than your breach, we will refund any unused prepaid period.</p>
<h2>10. Changes to these terms</h2>
<p>We may update these terms. For changes that materially affect you, we will email subscribers at least 30 days before they take effect. If you do not agree, you can cancel before then. The date at the top shows the latest version.</p>
<h2>11. Governing law and disputes</h2>
<p>If you have a problem, please email us first; most issues are solved quickly, and we will respond within 1 business day. If a dispute is not solved within 30 days of your first message, it will be governed by the laws of {E(C["governing_law"])}, without regard to conflict-of-law rules, and resolved in {E(C["venue"])}, unless the law where you are located requires otherwise.</p>
<h2>12. General</h2>
<p>If any part of these terms is found unenforceable, the rest stays in effect. If we do not enforce a right, we have not waived it. You may not transfer your subscription without our written consent. These terms, with the policies linked here, are the whole agreement between you and us about BidBell.</p>
<h2>13. Contact</h2>
<p>{E(C["owner_name"])}, trading as BidBell. {contact}.{phone}</p>''')

    legal_page('privacy/', 'Privacy Policy', 'What BidBell collects, why, who processes it, how long we keep it and your rights.', f'''
<p>This policy explains how {seller}, handles personal information. Our contact details are at the end of this policy. We collect as little as we can, we do not sell it, and this website uses no tracking or advertising cookies.</p>
<section class="pilot-note"><h2>Preparation workspace data</h2>
<p>The BidBell workspace stores account details, password hashes, session records, original files you save for reuse or submission, extracted solicitation and company text, company facts, requirements, answers, pricing estimates, completed supported forms, submission messages and delivery activity records needed to operate your workspace. It is hosted on Render. Signed-in access uses a necessary session cookie; the public marketing pages and the signed-in workspace are different surfaces.</p>
<p>When you explicitly use an enabled AI action, relevant source text or requirements and company facts are sent to OpenAI for that action. AI actions may be unavailable when configuration or usage limits do not permit them. Upload only material you are authorized to share, and avoid credentials, payment details and unnecessary personal records.</p>
<p>When you confirm a supported email bid, the exact reviewed message and selected files are sent to the buyer submission address you reviewed, using BidBell's Google Workspace email service. Submission history records the send and delivery status; mail-server acceptance does not confirm buyer receipt. Workspace records are not published as public website content. Contact {mail} for access, correction or deletion requests. Deletion is handled through support, not an instant in-app control; a request is not confirmation that every record or backup has already been removed. The alert collection and retention practices below also apply to alerts within your BidBell plan. No workspace-specific deletion deadline is promised here.</p></section>
<h2>1. What we collect</h2>
<ul>
<li><strong>Trial and subscriber details</strong> you give us: first name, business email, business name and website, trades, states, eligibility (small business, HUBZone, SDVOSB, 8(a), WOSB) and whether you are registered in SAM.gov.</li>
<li><strong>Service records</strong>: the alerts and bids we have sent you and when, so we can send reminders and updates and your day-12 summary.</li>
<li><strong>Payment information</strong> from Paddle: your name, email, country, plan, amounts and subscription status. We never receive your card details.</li>
<li><strong>Emails</strong> you send us, and replies to our emails.</li>
<li><strong>Business contact details</strong> of companies we may email about BidBell: company name, website and location, any federal contracts it has won (public records), a business email address the company publishes itself (on its website or its own business pages) or that appears in a public government business directory, and a contact&rsquo;s first name when it is published next to that address. See our <a href="/email-policy/">email policy</a>.</li>
</ul>
<p>We never ask you to send passwords by email or through the signup form. You set a password on your own workspace account page; we store its hash rather than the password itself. We do not ask for card numbers, tax IDs or government ID numbers in the signup form or by email.</p>
<h2>2. Why we use it</h2>
<p>To provide the service you asked for (sending your alerts, managing your trial and subscription, answering you); to keep records required for tax and accounting; and, for business contacts, to offer BidBell to companies that may need it (our legitimate interest), with an easy opt-out.</p>
<h2>3. Who processes it for us</h2>
<ul>
<li><strong>Google Workspace</strong> (Google LLC): our email (including the alerts we send you), and our sign-up form (Google Forms). Sign-up answers are stored in BidBell&rsquo;s private Google account.</li>
<li><strong>GitHub</strong> (GitHub, Inc.): stores our customer and business-contact records in a private repository, runs the programs that prepare and send our emails, and stores the public website code.</li>
<li><strong>Render</strong> (Render Services, Inc.): hosts the public website and the preparation workspace described above. Hosting providers may process request details such as IP addresses for delivery and security.</li>
<li><strong>Paddle</strong> (Paddle.com Market Ltd and its affiliates): our merchant of record. Paddle processes your payment details, billing address and email to handle purchases and tax.</li>
<li><strong>Anthropic</strong> (Anthropic, PBC): Claude, an AI assistant, helps us run BidBell. It drafts replies to the emails we receive, which we check before they are sent, looks up the published business email addresses of companies we may contact, and runs our private dashboard, so it processes the emails you send us and our customer and contact records.</li>
</ul>
<p>We only download public data from SAM.gov and USAspending.gov; we do not send them your details. These providers process data on our instructions and under their own security and privacy commitments. Data may be processed in the United States, the European Union and other countries where they operate.</p>
<h2>4. How long we keep it</h2>
<ul>
<li>Trial details, if you do not subscribe: 1 year after the trial ends, then deleted from our customer records.</li>
<li>Customer details: while you are subscribed, then 1 year after your subscription ends, then deleted from our customer records. Payment and tax records are kept by Paddle, our merchant of record, under its own policy.</li>
<li>Copies can remain in our private backups (the change history of our records) and in our email inbox; we do not use them for anything else.</li>
<li>Business contacts who opt out: we keep only the email address on a do-not-contact list, so we never email it again.</li>
</ul>
<h2>5. Your rights</h2>
<p>Wherever you are, you can ask us to tell you what we hold about you, correct it, delete it, or stop contacting you. Email <a href="mailto:{C["email"]}">{C["email"]}</a>; we reply within 30 days and do not charge.</p>
<p><strong>California and other US states:</strong> you have the right to know, access, correct and delete your personal information, and not to be discriminated against for using these rights. We do not sell or share personal information for cross-context behavioral advertising, and we do not use it for profiling.</p>
<p><strong>European Union and United Kingdom:</strong> you also have the rights to object, to restrict processing and to data portability, and you may complain to your local data protection authority.</p>
<h2>6. Cookies and tracking</h2>
<p>The public marketing website sets no cookies and uses no analytics or advertising pixels. The signed-in preparation workspace uses a necessary sign-in session cookie as described above. The only third-party script is Paddle&rsquo;s checkout (Paddle.js), which loads only on our plan page (/subscribe/) so you can pay; Paddle may use cookies there for checkout and fraud prevention, under Paddle&rsquo;s own privacy notice. Our emails contain no tracking pixels.</p>
<h2>7. Security</h2>
<p>We use providers with strong security, two-step verification on every account, and we keep customer data out of this public website. No system is perfectly secure; if a breach affects you, we will tell you as the law requires.</p>
<h2>8. Children</h2>
<p>BidBell is a business service and is not meant for anyone under 18.</p>
<h2>9. Changes</h2>
<p>We will post changes here and email subscribers about material changes before they take effect.</p>
<h2>10. Contact</h2>
<p>For privacy questions or requests, email {mail} or write to {E(C["owner_name"])}, BidBell, at our US mailing address: {E(C["mailing_address"])}. We may store and access your information outside the United States.{phone}</p>''')

    legal_page('refunds/', 'Refund Policy', 'BidBell refund policy: a 30-day money-back guarantee on every payment, and how to cancel.', f'''
<p>New customers can try BidBell free for 14 days, with no card needed, so you can try alerts and bid preparation before you pay.</p>
<h2>30-day money-back guarantee</h2>
<p>If you are not happy with BidBell, we will refund any payment in full, on the monthly or the yearly plan, if you ask within 30 days of that payment.</p>
<h2>How to ask for a refund</h2>
<p>Email {mail}, or reply to any BidBell email, within 30 days of the payment.{f" You can also call us at {phone_link()}." if PHONE.strip() else ""} You can also ask Paddle directly, through the help link in your receipt or at {ext('https://paddle.net/', 'paddle.net')}.</p>
<h2>How refunds are paid</h2>
<p>Our payments are handled by Paddle.com, our merchant of record, so Paddle issues your refund to your original payment method. How long it takes to show depends on your bank or card provider.</p>
<h2>Cancelling</h2>
<p>Your subscription renews automatically until you cancel, and you can cancel anytime: email {mail}, reply to any BidBell email, or use the &ldquo;Manage subscription&rdquo; link in your receipt from Paddle. After you cancel, you are not charged again, and your alerts continue to the end of the period you have paid for.</p>
<p>See also our <a href="/terms/">Terms of Service</a>.</p>''')

    legal_page('acceptable-use/', 'Acceptable Use Policy', 'How BidBell alerts and pages may be used.', f'''
<p>BidBell alerts are for the internal use of the business that subscribes. You agree not to:</p>
<ul>
<li>resell, republish, forward in bulk or share our paid alerts or their contents with other businesses;</li>
<li>share one subscription between separate businesses;</li>
<li>copy our paid content into another product or service;</li>
<li>use BidBell for anything unlawful, including misrepresenting your eligibility for a set-aside;</li>
<li>try to break, overload, scan or gain unauthorized access to our website or systems.</li>
</ul>
<p>Our free public pages are built from public data; you may link to them. If you break this policy we may suspend or end your subscription under our <a href="/terms/">terms</a>.</p>''')

    legal_page('disclaimer/', 'Disclaimer', 'Important limits of BidBell information.', f'''
<section class="pilot-note"><h2>Preparation support, not certified compliance</h2>
<p>Source checks confirm that selected text appears in an uploaded document or saved company facts. They do not certify that your facts are true, that every requirement was captured, or that your response is legally compliant, eligible or competitive. Rules and AI can miss relevant instructions. Blank or scanned pages may have no extracted text.</p>
<p>AI suggestions are factual starting points for review and editing, not a complete persuasive proposal. Readiness checks identify specific recorded gaps; a passing check is not a guarantee that the bid is complete. Cost estimates depend on your inputs and do not guarantee profit.</p>
<p>BidBell sends supported email bids only after your explicit final confirmation and the required source, recipient and deadline checks. It does not automatically apply to buyer portals, sign declarations or guarantee awards. You must check completed forms; only supported standard fillable PDF text fields can be completed from reviewed facts. Mail-server acceptance does not prove buyer receipt. You remain responsible for the full official notice, amendments, required forms, signatures, deadlines and final submission. Bid preparation is included in the existing alert subscription. Existing trial end dates and annual subscription terms are preserved.</p></section>
<h2>Not a government service</h2>
<p>BidBell is a private service. It is not affiliated with, endorsed by or connected to SAM.gov, the General Services Administration, USAspending.gov or any government agency.</p>
<h2>Data can change</h2>
<p>We use public government data. Notices can be incomplete, published late, amended or withdrawn after we send them, and deadlines are set in each notice&rsquo;s own time zone. Always read the full official notice and its attachments on SAM.gov before relying on anything we send.</p>
<h2>Matches are estimates</h2>
<p>Work sites, eligibility, site-visit dates read from notice text, and especially the &ldquo;likely current contract&rdquo;, the contracts shown as ending soon and their amounts are our best reading of public records. They can be wrong or missing, and an agency can extend a contract or change its plans. Contract totals are the amounts the government committed (obligated) and can include option years or later changes. Reminders use the notice as it stands when we check it; the official notice and its attachments are always the authority.</p>
<h2>No advice, no guarantee</h2>
<p>Nothing from BidBell is legal, financial, tax or bidding advice. We do not guarantee that you will find, bid on or win any contract.</p>''')

    legal_page('email-policy/', 'Email Policy', 'How BidBell contacts businesses and how to opt out.', f'''
<h2>Who we email</h2>
<p>We send a small number of emails to businesses that may need BidBell: commercial cleaning companies (janitorial, carpet and window cleaning), including companies that have won federal contracts, at a business email address published on their own website, their own business pages (such as Facebook or Google) or in public US government records. We never buy email lists or use data brokers, and we never guess addresses.</p>
<h2>What every email contains</h2>
<ul>
<li>Our real name and business name, and an honest subject line.</li>
<li>A plain statement that it is a sales email about a paid service, with the price.</li>
<li>Our mailing address: {E(C["mailing_address"])}.</li>
<li>A clear way to stop: reply &ldquo;no&rdquo; and we will not email you again.</li>
</ul>
<p>We send each company one email, never a follow-up.</p>
<h2>Opting out</h2>
<p>Reply &ldquo;no&rdquo; or &ldquo;unsubscribe&rdquo;, or email <a href="mailto:{C["email"]}">{C["email"]}</a>. We act on it promptly, and always within 10 business days, as the US CAN-SPAM Act requires. Your address goes on our do-not-contact list so it is never emailed again, and we do not email anyone else at your company either.</p>
<h2>No tracking</h2>
<p>Our emails contain no tracking pixels or hidden images.</p>
<h2>Subscriber alerts</h2>
<p>Alert emails go only to people who asked for them. To change or stop them, reply to any alert.</p>
<h2>Report a problem</h2>
<p>If you think we emailed you in error, tell us at <a href="mailto:{C["email"]}">{C["email"]}</a>.</p>''')


# ------------------------------------------------------------------ extras
def extras():
    write('404.html', layout('404.html', 'Page not found | BidBell', 'This page does not exist.',
          '<div class="page-head"><div class="wrap"><p class="crumbs">Error 404</p><h1>Page not found</h1><p class="lead">This page does not exist or has moved.</p>'
          '<div class="cta-row"><a class="btn" href="/">Go to the home page</a><a class="btn ghost" href="/workspace/">Browse opportunities</a></div></div></div>',
          noindex=True), sitemap=False)
    exp = date(TODAY.year + 1, TODAY.month, 1) if TODAY.month > 1 else date(TODAY.year, 12, 1)
    os.makedirs(os.path.join(ROOT, '.well-known'), exist_ok=True)
    open(os.path.join(ROOT, '.well-known', 'security.txt'), 'w', encoding='utf-8', newline='\n').write(
        f'Contact: mailto:{C["email"]}\nExpires: {exp.isoformat()}T00:00:00.000Z\nPreferred-Languages: en\n'
        f'Canonical: {BASE}/.well-known/security.txt\n')
    open(os.path.join(ROOT, 'robots.txt'), 'w', encoding='utf-8', newline='\n').write(f'User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n')
    urls = ''.join(f'<url><loc>{BASE}/{p}</loc><lastmod>{m}</lastmod></url>' for p, m in PAGES)
    open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8', newline='\n').write(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    open(os.path.join(ROOT, 'CNAME'), 'w', encoding='utf-8', newline='\n').write(C['domain'] + '\n')
    open(os.path.join(ROOT, '.nojekyll'), 'w', encoding='utf-8', newline='\n').write('')
    shutil.copy(os.path.join(T, 'style.css'), os.path.join(ROOT, 'style.css'))
    shutil.copy(os.path.join(T, 'form.js'), os.path.join(ROOT, 'form.js'))
    shutil.copy(os.path.join(T, 'checkout.js'), os.path.join(ROOT, 'checkout.js'))
    shutil.copy(os.path.join(T, 'nav.js'), os.path.join(ROOT, 'nav.js'))
    open(os.path.join(ROOT, 'favicon.svg'), 'w', encoding='utf-8', newline='\n').write(
        BELL.replace('aria-hidden="true" focusable="false"', 'xmlns="http://www.w3.org/2000/svg"').replace('currentColor', '#C8102E'))


def construction_title(value):
    value = clean_title(value)
    if value.isupper():
        acronyms = {'HVAC', 'RFP', 'RFQ', 'NYC', 'DOT', 'VA', 'ADA', 'LED', 'US', 'USA', 'ID', 'ITB'}
        value = ' '.join(word if word in acronyms or any(c.isdigit() for c in word) else word.title() for word in value.split())
        value = fix_case(value)
    return value


def construction_deadline(bid):
    try:
        value = datetime.fromisoformat(str(bid.get('due_at') or bid.get('due')).replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return 'Check the buyer notice'
    label = nice(value.date().isoformat())
    if bid.get('due_precision') == 'date' or len(str(bid.get('due_at') or bid.get('due'))) <= 10:
        return label + ' (time not provided)'
    offset = value.strftime('%z')
    zone = '(UTC' + offset[:3] + ':' + offset[3:] + ')' if offset else '(confirm source time zone)'
    return label + value.strftime(' at %H:%M ') + zone


def construction_page():
    """Industry entry uses the same authenticated application, with dated public evidence."""
    path = os.path.join(ROOT, 'data', 'construction_bids.json')
    catalog = json.load(open(path, encoding='utf-8')) if os.path.isfile(path) else {'bids': [], 'updated': None}
    current = []
    now = datetime.now(timezone.utc)
    for bid in catalog.get('bids', []):
        if bid.get('procurement_status', 'open') != 'open':
            continue
        due = bid.get('due_at') or bid.get('due')
        try:
            parsed = datetime.fromisoformat(str(due).replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                parsed = parsed.replace(hour=23, minute=59, tzinfo=timezone.utc)
            if parsed <= now:
                continue
        except (ValueError, TypeError):
            continue
        current.append(bid)
    trades = ['Commercial building & renovation', 'Electrical', 'HVAC & plumbing', 'Roofing', 'Flooring', 'Painting', 'Concrete']
    cards = ''.join('<li>'+E(t)+'</li>' for t in trades)
    rows = []
    labels = dict(zip(['building-renovation','electrical','hvac-plumbing','roofing','flooring','painting','concrete'], trades))
    selected = []
    ordered = sorted(current, key=lambda bid: str(bid.get('due_at') or bid.get('due')))
    for _ in range(2):
        for trade in labels:
            candidate = next((bid for bid in ordered if bid not in selected and trade in bid.get('trades', [])), None)
            if candidate and len(selected) < 12:
                selected.append(candidate)
    for bid in selected:
        identity = str(bid.get('id', ''))
        application = WORKSPACE_URL + '#opportunity/' + identity if re.fullmatch(r'[a-f0-9]{24}', identity) else WORKSPACE_URL + '?industry=construction#opportunities/open'
        source = str(bid.get('link') or bid.get('url') or '')
        if not source.startswith('https://'):
            continue
        row_trades = ', '.join(labels[t] for t in bid.get('trades', []) if t in labels)
        verified = str(bid.get('verified_at') or '')
        checked = nice(verified[:10]) if re.match(r'^\d{4}-\d{2}-\d{2}', verified) else 'See source inventory'
        rows.append('<article class="card"><p class="eyebrow">'+E(bid.get('source', 'Official public source'))+'</p><h3>'+E(construction_title(bid.get('title', 'Construction opportunity')))+'</h3><p>'+E(agency_name(bid.get('agency', '')))+' · '+E(STATES.get(bid.get('state'), bid.get('state')) or 'Check work location')+'</p><p><b>Trade:</b> '+E(row_trades)+'</p><p><b>Deadline:</b> '+E(construction_deadline(bid))+'</p><p class="small muted">Source checked '+E(checked)+'. Review the current buyer notice.</p><div class="cta-row"><a class="btn" href="'+E(application)+'">Open in BidBell</a><a class="btn ghost" href="'+E(source)+'" rel="noopener">Read buyer notice</a></div></article>')
    results = ''.join(rows) if rows else '<div class="note"><p>No verified, currently open construction records have been added to this preview yet. The collection evidence will appear here after validation. No sample opportunity is presented as real.</p></div>'
    raw_stamp = str(catalog.get('updated') or '')
    stamp = E(nice(raw_stamp[:10]) + ' UTC' if re.match(r'^\d{4}-\d{2}-\d{2}',raw_stamp) else 'Not yet collected')
    body = '''<div class="page-head"><div class="wrap"><p class="crumbs"><a href="/">Home</a> / Construction</p><p class="eyebrow">LESS PAPERWORK. A STRONGER NEXT BID.</p><h1>Construction &amp; building trades.<br>Keep the next bid moving.</h1><p class="lead">Find suitable work, reuse your company information and prepare a clear response in the same BidBell workspace. Your final review stays in the journey.</p><div class="cta-row"><a class="btn" href="/start/">Choose your construction trade</a><a class="btn ghost" href="'''+WORKSPACE_URL+'''?industry=construction#opportunities/open">Open your workspace</a></div></div></div><div class="wrap page"><section class="card"><h2>Built around the work your team can deliver.</h2><ul class="plain-list">'''+cards+'''</ul><p>Match by trade and service area. Check licenses, insurance, bonding, project experience, mandatory visits, addenda and buyer forms before approving your response.</p><p>AI works from the source requirements and your reviewed information. It does not invent quantities, prices or qualifications.</p></section><section class="card"><h2>One connected application.</h2><p>Open the opportunity, review requirements, reuse facts and documents, fill missing items and check your price. Review the exact package, then use supported email submission or the buyer's portal handoff. Keep the resulting evidence with that bid.</p><p>A prepared response is not a submitted bid. Mail-server acceptance and buyer confirmation remain distinct.</p></section><section><p class="eyebrow">DATED PUBLIC SOURCE SNAPSHOT</p><h2>Explore work worth checking.</h2><p>Source snapshot: '''+stamp+'''. '''+str(len(current))+''' records with a future deadline are present in this staged dataset. This is source-specific coverage, not every construction bid or a promise of matches for every contractor.</p>'''+results+'''</section><section class="card"><h2>One BidBell plan.</h2><p>Relevant alerts and AI-assisted bidding together. Free for 14 days, no card. Then US$39/month if you choose to continue. Existing trial dates, subscription rights and annual terms stay unchanged.</p><a class="btn" href="/start/">Start with your business</a></section></div>'''
    write('construction-bids/', layout('construction-bids/', 'Construction bids and applications | BidBell', 'Construction opportunities, reusable company information and AI-assisted bid preparation in one BidBell workspace.', body))


def main():
    home(); start(); subscribe(); bid_pages(); construction_page(); legal(); extras()
    print(f'built {len(PAGES)} pages + 404, sitemap, robots, security.txt; '
          f'/subscribe/ checkout {"ON (" + PADDLE["env"] + ")" if PADDLE_READY else "off (tools/paddle.json not filled in)"}; '
          f'phone {"shown" if PHONE.strip() else "not set"}')


if __name__ == '__main__':
    main()


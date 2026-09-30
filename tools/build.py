#!/usr/bin/env python3
"""
Builds the whole BidBell website as static files (no server, no database). The only scripts are form.js on /start/
and, on /subscribe/ only, checkout.js plus Paddle.js (loaded only once tools/paddle.json is filled in).

  python3 tools/build.py            -> writes every page into the project root
Inputs:  tools/site.json (business facts), tools/paddle.json (Paddle checkout settings), tools/style.css,
         data/cleaning_bids.json (public SAM.gov data)
Run daily by .github/workflows/weekly-bids.yml (drops notices whose deadline has passed); on Mondays
tools/update_bids.py refreshes the bid data first.

Legal clauses a lawyer should review are listed in tools/LAWYER_REVIEW.md (not in the public HTML).
"""
import html, json, os, re, shutil
from datetime import date, datetime

# ---------------------------------------------------------------- SUPPORT PHONE: SET IT HERE
# Put the US support number between the quotes, e.g. PHONE = '(501) 555-0123', then run python3 tools/build.py.
# Leave it empty ('') to show no phone anywhere. When set, it appears in the footer (next to the email), the Terms
# (Contact), the Privacy Policy (Contact), the Refund policy and /subscribe/.
PHONE = ''

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, 'tools')
C = json.load(open(os.path.join(T, 'site.json')))
DATA = json.load(open(os.path.join(ROOT, 'data', 'cleaning_bids.json')))
# Paddle checkout settings for /subscribe/: {"env": "sandbox" or "production", "client_token", "price_monthly",
# "price_yearly"}. The client-side token is public by design (it only opens checkouts); never put a Paddle API key here.
# While client_token or a price id is empty, /subscribe/ shows "Payments open soon" and loads no Paddle script.
PADDLE = json.load(open(os.path.join(T, 'paddle.json')))
PADDLE_READY = all(str(PADDLE.get(k) or '').strip() for k in ('client_token', 'price_monthly', 'price_yearly'))
if PADDLE.get('env') not in ('sandbox', 'production'):
    raise SystemExit('tools/paddle.json: "env" must be "sandbox" or "production"')
if PADDLE_READY and not PADDLE['client_token'].strip().startswith('test_' if PADDLE['env'] == 'sandbox' else 'live_'):
    print(f'warning: tools/paddle.json: a {PADDLE["env"]} client token normally starts with '
          f'{"test_" if PADDLE["env"] == "sandbox" else "live_"}')
BASE = 'https://' + C['domain']
TODAY = date.fromisoformat(os.environ.get('BUILD_DATE', date.today().isoformat()))
E = html.escape
PAGES = []          # (path, lastmod) for sitemap
LAWYER = []         # clauses to review

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


def lawyer(tag, text):
    LAWYER.append(text)
    return ''   # listed in tools/LAWYER_REVIEW.md only; never in the public HTML


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


BELL = ('<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2.2" '
        'stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/>'
        '<path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>')


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


def layout(path, title, desc, body, jsonld=None, updated=None, noindex=False, og_type='website', csp=CSP):
    url = BASE + '/' + path
    ld = ''.join(f'\n<script type="application/ld+json">{json.dumps(j, separators=(",", ":"))}</script>'
                 for j in (jsonld or []))
    upd = updated or TODAY
    popular = ['Texas', 'California', 'Virginia', 'Florida', 'Illinois', 'Massachusetts']
    state_links = ''.join(f'<li><a href="/cleaning-bids/{slug(s)}/">{s}</a></li>' for s in popular)
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
<link rel="canonical" href="{url}">
{'<meta name="robots" content="noindex">' if noindex else ''}
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="BidBell">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#FFFFFF">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preload" href="/fonts/source-serif-4.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/fonts/public-sans.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/style.css">{ld}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="topbar"><b>14 days free</b>, no card needed. Then ${C['standard_price']}/month, cancel anytime. <a href="{E(start_url())}">Start your free trial &rarr;</a></div>
<header class="site-head"><div class="wrap">
  <a class="logo" href="/">{BELL}BidBell</a>
  <nav class="nav" aria-label="Main">
    <a href="/#features">Features</a><a href="/#how">How it works</a><a href="/cleaning-bids/">Free bid pages</a><a href="/#pricing">Pricing</a><a href="/#faq">FAQ</a>
    <a class="btn small" href="{E(start_url())}">Start free trial</a>
  </nav>
</div></header>
<main id="main">
{body}
</main>
<footer class="site-foot"><div class="wrap">
  <div class="foot-grid">
    <div class="brand">
      <a class="logo" href="/">{BELL}BidBell</a>
      <p class="foot-about">Daily federal cleaning bids for janitorial, carpet and window companies, filtered to the jobs you can win.</p>
      <p class="small">{E(C['mailing_address'])}<br><a href="mailto:{C['email']}">{C['email']}</a>{' &middot; ' + phone_link() if PHONE.strip() else ''}</p>
    </div>
    <nav aria-label="Product"><h2>Product</h2><ul>
      <li><a href="/#features">Features</a></li><li><a href="/#how">How it works</a></li><li><a href="/#sample">Sample alert</a></li><li><a href="/#pricing">Pricing</a></li><li><a href="/#faq">FAQ</a></li><li><a href="{E(start_url())}">Start free trial</a></li></ul></nav>
    <nav aria-label="Free bid pages"><h2>Free bid pages</h2><ul>{state_links}<li><a href="/cleaning-bids/">All states &rarr;</a></li></ul></nav>
    <nav aria-label="Company"><h2>Company</h2><ul>
      <li><a href="/#about">About</a></li><li><a href="/terms/">Terms</a></li><li><a href="/privacy/">Privacy</a></li><li><a href="/refunds/">Refund policy</a></li><li><a href="/acceptable-use/">Acceptable use</a></li><li><a href="/disclaimer/">Disclaimer</a></li><li><a href="/email-policy/">Email policy</a></li></ul></nav>
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
    open(full, 'w').write(content)
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
        where = ', '.join(x for x in (b['city'], STATES.get(b['state'], b['state'])) if x)
        rows.append(f'<tr><td data-label="Notice">{ext(b["link"], E(clean_title(b["title"])))}<br><span class="small muted">{E(agency_name(b["agency"]))}'
                    f'{" &middot; Ref " + E(b["sol"]) if b["sol"] else ""}</span></td>'
                    f'<td data-label="Work site">{E(where)}</td><td data-label="Respond by">{nice(b["due"])}</td>'
                    f'<td data-label="Stage">{E(TYPE_WORDS.get(b["type"], b["type"]))}</td>'
                    f'<td data-label="Who can bid">{E(b["set_aside"] or "No set-aside listed")}</td></tr>')
    return (f'<div class="table-wrap"><table class="stack"><caption>{caption}</caption><thead><tr><th scope="col">Notice</th>'
            f'<th scope="col">Work site</th><th scope="col">Respond by</th><th scope="col">Stage</th>'
            f'<th scope="col">Who can bid</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def cta_box(heading='Get the right bids every morning instead'):
    return f'''<div class="cta-band">
  <h2>{heading}</h2>
  <p>This page is a free weekly snapshot. BidBell subscribers get, every morning around 6 AM their time, only the bids in their states that their business is allowed to bid on.</p>
  <div class="cta-row"><a class="btn light" href="{E(start_url())}">Start 14 days free {ICON['arrow']}</a></div>
  {checks(['No card required', f"${C['standard_price']}/month after, or ${C['annual_price']}/year", 'Cancel anytime'])}
</div>'''


# ------------------------------------------------------------------ home
WHO = {'Total Small Business Set-Aside': 'Small businesses', 'HUBZone Set-Aside': 'HUBZone businesses',
       'Service-Disabled Veteran-Owned Small Business Set-Aside': 'Service-disabled veteran-owned',
       'Service-Disabled Veteran-Owned Small Business Sole Source': 'One named veteran-owned firm',
       '8(a) Set-Aside': '8(a) businesses', 'Women-Owned Small Business (WOSB) Program Set-Aside': 'Women-owned businesses'}
STAGE = {'Solicitation': 'BID OPEN', 'Combined Synopsis/Solicitation': 'BID OPEN',
         'Presolicitation': 'COMING SOON', 'Sources Sought': 'MARKET RESEARCH'}

FAQ = [   # (question, answer); answers are HTML (links allowed); the FAQ structured data gets them as plain text
    ('Where do the bids come from?',
     'From SAM.gov, the official US government website where federal agencies publish contract opportunities. '
     'Past contract winners and amounts come from USAspending.gov, the official public database of federal spending. '
     'Every bid in your email links to its official notice so you can check it.'),
    ('Are you part of the government?',
     'No. BidBell is a private alert service. It is not affiliated with SAM.gov, the General Services Administration '
     'or any government agency. Registering in SAM.gov is free; we never charge for it.'),
    ('Do I need to be registered in SAM.gov?',
     'To win a federal contract, yes: a free registration at sam.gov. You can get BidBell alerts while your registration is in progress.'),
    ('How many bids will I get?',
     'It depends on your trade and states. Some days there are none. Then we only write if a reminder for a bid we sent you is due, or on Mondays with contracts ending soon in your states. We never pad the email with bids you cannot use.'),
    ('What does "likely current contract" mean?',
     'We look in USAspending.gov, the official record of federal spending, for the contract covering the same work: the same agency, '
     'the same kind of work and the same work site. If the notice itself names the previous contract number, we use that. '
     'We show a contract only when one clearly fits, label it "likely" unless the notice names it, and link to the official record so you can check. '
     'When no contract clearly fits, we show nothing rather than guess.'),
    ('How do I pay, and how do I cancel?',
     'On day 12 of your free 14 days we email you a secure checkout link. Payments are handled by Paddle, our merchant of record. '
     'Your plan renews automatically until you cancel. You can cancel anytime by replying to any BidBell email; your alerts continue '
     'until the end of the period you paid for. Every payment has a 30-day money-back guarantee; see our <a href="/refunds/">refund policy</a>.'),
    ('Is my information safe?',
     'We collect only what we need to send your alerts: your name, business details, trades, states and eligibility. '
     'We never see your card, we do not sell data, and this website has no tracking or advertising cookies.'),
]


def agency_name(a):
    a = (a or 'Federal agency').strip()
    if a.lower().endswith(', department of'):
        a = 'Department of ' + a[:-len(', department of')]
    return fix_case(a.replace('Dept Of', 'Department Of'))


def open_bids(min_days=0):
    return sorted((b for b in DATA['bids'] if (date.fromisoformat(b['due']) - TODAY).days >= min_days), key=lambda b: b['due'])


def mock_bid(b, show_left=True):
    d = date.fromisoformat(b['due'])
    left = (d - TODAY).days
    soon = show_left and 0 <= left <= 5
    due = f'Due {MONTHS[d.month - 1]} {d.day}'
    sub = f'<small>{left} day{"s" if left != 1 else ""} left</small>' if show_left and left >= 0 else ''
    where = ', '.join(x for x in (b['city'], b['state']) if x)
    return f'''<div class="bid">
        <div class="bid-top"><div><span class="tag">{STAGE.get(b["type"], "BID OPEN")}</span>{' <span class="tag soon">CLOSES SOON</span>' if soon else ''}</div><div class="due{' red' if soon else ''}">{due}{sub}</div></div>
        <div class="bid-name">{E(clean_title(b["title"]))}</div>
        <div class="bid-meta">{E(agency_name(b["agency"]))} &middot; {E(where)}</div>
        <span class="who">Who can bid: {E(WHO.get(b["set_aside"], b["set_aside"] or "Any business"))}</span>
      </div>'''


def hero_mock():
    pool = open_bids(2)
    small = [b for b in pool if b['set_aside'] == 'Total Small Business Set-Aside' and b['type'] != 'Sources Sought']
    pick, seen = [], set()
    for b in small + [b for b in pool if b not in small]:
        if b['state'] not in seen:
            pick.append(b)
            seen.add(b['state'])
        if len(pick) == 3:
            break
    show_left = bool(pick)
    if not pick:
        pick = DATA['bids'][:3]
    names = [STATES.get(b['state'], b['state']) for b in pick]
    area = 'Your states' if not names else names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' &amp; ' + names[-1]
    n = len(pick)
    day = f'{TODAY.strftime("%a")}, {MONTHS[TODAY.month - 1]} {TODAY.day}'
    return f'''<figure class="mock">
    <div class="mock-window">
      <div class="mock-bar"><i></i><i></i><i></i><span>Inbox &middot; {day} &middot; 6:15 AM</span></div>
      <div class="mail-head"><span><span class="dot">&#9679;</span> BidBell</span><small>{day}</small></div>
      <div class="mail-body mail-fade">
        <div class="mail-kicker">Janitorial &middot; {area}</div>
        <div class="mail-title">{n} bid{"s" if n != 1 else ""} fit your business today.</div>
        <p class="mail-sub">Sorted by deadline. Each one links to the official notice on SAM.gov.</p>
        {''.join(mock_bid(b, show_left) for b in pick)}
      </div>
    </div>
    <div class="float-card" aria-hidden="true">
      <div class="k">{ICON['check']}Delivered &middot; 6:15 AM your time</div>
      <div class="t">Only bids you can win</div>
      <div class="m">Filtered by trade, state and set-aside</div>
    </div>
    <figcaption class="sr-only">Example BidBell alert built from real SAM.gov notices open on {long_date(TODAY)}.</figcaption>
  </figure>'''


def home():
    sp, ap = C['standard_price'], C['annual_price']
    n_open = len(open_bids(0))
    faq_html = ''.join(f'<details><summary>{E(q)}</summary><p>{a}</p></details>' for q, a in FAQ)
    pill = (f'<span class="live-dot" aria-hidden="true"></span><b>Live</b> {n_open} federal cleaning bids open this week'
            if n_open else '<span class="live-dot" aria-hidden="true"></span><b>Live</b> New federal cleaning bids, checked every morning')
    su = E(start_url())
    feats = [
        ('filter', 'Only bids you can win', 'Filtered by your trade, your states and your eligibility: small business, HUBZone, SDVOSB, 8(a) or women-owned.'),
        ('pin', 'Where the work really is', 'We list the actual work site, not the contracting office three states away.'),
        ('doc', 'Plain English', 'What the job is, where it is and what to do next. No government shorthand, no digging through PDFs.'),
        ('dollar', 'What the job is worth', 'Where public records clearly show it: who holds the job now and what the government has paid, from USAspending.gov.'),
        ('calendar', 'Contracts ending soon', 'Every Monday and in your first alert: up to 10 contracts in your states that end in 3 to 6 months, have no option years left and were competed last time, so you can prepare before the new bid is posted.'),
        ('clock', 'Deadline reminders', 'A reminder 3 days before each deadline and each site visit stated in the notice, and an update if the deadline or site visit moves.'),
    ]
    feat_html = ''.join(f'<div class="feature"><div class="icon">{ICON[i]}</div><h3>{t}</h3><p>{d}</p></div>' for i, t, d in feats)
    plan_items = lambda items: '<ul>' + ''.join(f'<li>{ICON["check"]}<span>{x}</span></li>' for x in items) + '</ul>'
    body = f'''
<section class="hero"><div class="wrap">
  <div class="copy">
    <a class="pill" href="/cleaning-bids/">{pill}<span class="pill-go">See them {ICON['arrow']}</span></a>
    <h1>Federal cleaning bids you can win. In your inbox around 6&nbsp;AM.</h1>
    <p class="lead">BidBell reads every new contract notice on SAM.gov each morning and sends your company only the janitorial, carpet and window jobs in your states that you&rsquo;re eligible to bid on. Plain English, deadline first.</p>
    <div class="cta-row"><a class="btn" href="{su}">Start 14 days free {ICON['arrow']}</a><a class="btn ghost" href="#sample">See a real alert</a></div>
    {checks(['No card required', 'Set up in 2 minutes', 'Cancel anytime'])}
  </div>
  {hero_mock()}
</div></section>

<div class="agencies"><div class="wrap">
  <p>Recent federal cleaning bids came from agencies including</p>
  <ul><li>Department of the Army</li><li>Veterans Affairs</li><li>Federal Aviation Administration</li><li>U.S. Forest Service</li><li>Department of Energy</li><li>Bureau of Indian Affairs</li></ul>
</div></div>

<section id="features" aria-labelledby="features-h"><div class="wrap">
  <div class="section-head center">
    <p class="eyebrow">Why cleaning companies use BidBell</p>
    <h2 id="features-h">SAM.gov lists thousands of contracts. BidBell finds the few that fit you.</h2>
    <p>Searching SAM.gov yourself means dozens of filters, code numbers and long PDFs. BidBell does it for you every morning and sends only what matters.</p>
  </div>
  <div class="features">{feat_html}</div>
</div></section>

<section id="filter" class="tint" aria-labelledby="filter-h"><div class="wrap two">
  <div>
    <p class="eyebrow">Eligibility filter</p>
    <h2 id="filter-h">Only the bids you&rsquo;re allowed to bid on.</h2>
    <p class="lead">Many federal cleaning contracts are reserved for HUBZone, veteran-owned, 8(a) or women-owned businesses. Tell us what your company qualifies for once, and BidBell leaves out everything else.</p>
    <ul class="ticks">
      <li>{ICON['check']}<span>Small business, HUBZone, SDVOSB, 8(a) and WOSB set-asides handled for you</span></li>
      <li>{ICON['check']}<span>Award notices, duplicates and bids closing in under 2 days removed</span></li>
      <li>{ICON['check']}<span>No matching bids today? We never pad the email with bids you can&rsquo;t use.</span></li>
    </ul>
  </div>
  <div class="panel">
    <p class="panel-title">Example company</p>
    <ul class="chips"><li class="chip on">Janitorial</li><li class="chip on">Texas</li><li class="chip on">Illinois</li><li class="chip on">Small business</li></ul>
    <p class="panel-title">Example: four Texas &amp; Illinois bids, September 29, 2026</p>
    <div class="row off"><div><div class="n">Custodial Services at TX190, Denton</div><div class="s">Department of the Army &middot; Denton, TX</div></div><span class="badge-inline">HUBZone only</span></div>
    <div class="row off"><div><div class="n">Fort Hood Installation Custodial Services</div><div class="s">Department of the Army &middot; Fort Hood, TX</div></div><span class="badge-inline">HUBZone only</span></div>
    <div class="row off"><div><div class="n">88th RD Custodial Services at IL068</div><div class="s">Department of the Army &middot; Machesney Park, IL</div></div><span class="badge-inline">One named firm only</span></div>
    <div class="row"><div><div class="n">Housekeeping Services, Fermilab</div><div class="s">Department of Energy &middot; Batavia, IL &middot; due Oct 9</div></div><span class="tag">IN YOUR ALERT</span></div>
    <p class="small muted panel-foot">Of these four, this company can bid on one. Only that one goes in its email.</p>
  </div>
</div></section>

<section id="value" aria-labelledby="value-h"><div class="wrap two flip">
  <div>
    <p class="eyebrow">Contract history</p>
    <h2 id="value-h">Know what a job is worth before you bid.</h2>
    <p class="lead">Next to each bid, where public records clearly show it, BidBell shows the company that holds the job now (or held it last) and what the government has paid, from USAspending.gov. Price your bid with real numbers.</p>
    <ul class="ticks">
      <li>{ICON['check']}<span>Current or previous contractor, contract total and period</span></li>
      <li>{ICON['check']}<span>Every Monday and in your first alert: up to 10 contracts in your states ending in 3 to 6 months</span></li>
      <li>{ICON['check']}<span>A link to the official record, so you can check it yourself</span></li>
    </ul>
  </div>
  <div class="panel">
    <p class="panel-title">Example from September 29, 2026 &middot; responses due Oct 5, 2026</p>
    <div class="bid-name panel-bid">Janitorial Services, Chattanooga National Cemetery</div>
    <p class="bid-meta panel-meta">Department of Veterans Affairs &middot; Chattanooga, TN</p>
    <p class="panel-title">Likely previous contract, ended Apr 2026</p>
    <div class="kv"><span>Contractor</span><b>KB Federal Maintenance Inc</b></div>
    <div class="kv"><span>Contract total</span><b>$302,108</b></div>
    <div class="kv"><span>Period</span><b>May 2021 &ndash; Apr 2026</b></div>
    <div class="kv"><span>About per year</span><b class="big-number">~$60,000</b></div>
    <p class="small muted panel-foot">Source: {ext('https://www.usaspending.gov/search', 'USAspending.gov')} award records, checked September 29, 2026. Contract total is the amount the government committed (obligated).</p>
  </div>
</div></section>

<section id="how" class="tint" aria-labelledby="how-h"><div class="wrap">
  <div class="section-head center">
    <p class="eyebrow">How it works</p>
    <h2 id="how-h">Set it up once. Then just check your email.</h2>
  </div>
  <div class="steps">
    <div class="step-card"><span class="time">2 minutes</span><div class="step-num">1</div><h3>Tell us about your business</h3><p>Your trade, the states you work in, and whether you are a small business, HUBZone, veteran-owned, 8(a) or women-owned.</p></div>
    <div class="step-card"><span class="time">Every morning</span><div class="step-num">2</div><h3>We read every new notice</h3><p>We check the new federal contract notices on SAM.gov, find where the work really is and who may bid, and match them to you.</p></div>
    <div class="step-card"><span class="time">~6 AM your time</span><div class="step-num">3</div><h3>One short email</h3><p>Only the bids you can use, each with the deadline, who can bid, a plain-English next step and the official link.</p></div>
  </div>
  <div class="stats mt">
    <div><strong>50 + DC</strong><span>Every state and Washington, D.C. covered</span></div>
    <div><strong>3 trades</strong><span>Janitorial, carpet, and window &amp; exterior cleaning</span></div>
    <div><strong>6 AM</strong><span>your time, every morning with new matches</span></div>
    <div><strong>$0</strong><span>For your first 14 days. No card needed.</span></div>
  </div>
</div></section>

<section id="sample" aria-labelledby="sample-h"><div class="wrap two">
  <div>
    <p class="eyebrow">A real alert</p>
    <h2 id="sample-h">This is the actual email.</h2>
    <p class="lead">Built from live SAM.gov notices on September 29, 2026, for a small cleaning company working in Massachusetts, Illinois and Kansas. Every bid, deadline and reference number in it is real.</p>
    <ul class="ticks">
      <li>{ICON['check']}<span><strong>Deadline first</strong>, with the days left and a warning when it closes soon</span></li>
      <li>{ICON['check']}<span><strong>Who can bid</strong>, so you never open a bid you can&rsquo;t win</span></li>
      <li>{ICON['check']}<span><strong>What to do next</strong>, in one plain sentence</span></li>
      <li>{ICON['check']}<span><strong>Site visit</strong>, quoted from the notice when it states one</span></li>
      <li>{ICON['check']}<span><strong>Likely current contract</strong> and what it pays, where public records clearly show it</span></li>
      <li>{ICON['check']}<span><strong>One button</strong> to the official notice on SAM.gov</span></li>
    </ul>
    <details><summary>Text version of this alert</summary>
      <p>3 janitorial and cleaning bids, all open to small businesses. Housekeeping Services, Fermilab (Department of Energy), Illinois, respond by Oct 9, 2026, ref DH-377725. Janitorial Services at the FMH SSC (FAA), Falmouth, Massachusetts, respond by Oct 20, 2026, ref 697DCK-27-R-00004; site visit Sep 29, 8:30 ET (RSVP required); likely current contract: Eco-Friendly Cleaning Specialist, LLC, $85,441 total, Apr 2023 to Dec 2026, about $28,000 a year. Janitorial Services at the MVY ATCT (FAA), Massachusetts, respond by Oct 22, 2026, ref 697DCK-27-R-00001; site visit Oct 6, 8:30 ET (RSVP required); likely current contract: Kevin Gundersen, $82,766 total, Dec 2021 to Dec 2026, about $17,000 a year.</p>
    </details>
  </div>
  <div>
    <div class="shot-frame"><picture><source srcset="/sample-alert.webp" type="image/webp"><img src="/sample-alert.jpg" width="720" height="1873" loading="lazy" decoding="async" alt="A BidBell alert email listing three open federal janitorial bids in Illinois and Massachusetts, each showing the deadline, who can bid and a button to the official notice; two also show the site visit quoted from the notice and the likely current contract from USAspending.gov."></picture></div>
    <p class="photo-cap"><a href="/sample-alert.jpg">Open the full-size alert</a></p>
  </div>
</div></section>

<section id="compare" class="tint" aria-labelledby="compare-h"><div class="wrap">
  <div class="section-head center">
    <p class="eyebrow">Free or paid</p>
    <h2 id="compare-h">Free bid pages, or the daily alert</h2>
    <p>Our <a href="/cleaning-bids/">free cleaning-bid pages</a> list open federal cleaning notices by state, updated once a week. The paid alert does the work for you.</p>
  </div>
  <div class="table-wrap"><table class="stack">
    <caption class="sr-only">What each option includes</caption>
    <thead><tr><th scope="col">Feature</th><th scope="col">Free state pages</th><th scope="col">BidBell daily alert</th></tr></thead>
    <tbody>
      <tr><th scope="row">Open bids</th><td data-label="Free state pages">Title, work site, deadline; updated weekly</td><td data-label="BidBell daily alert" class="yes">Every morning, around 6 AM your time</td></tr>
      <tr><th scope="row">Filtered for your business</th><td data-label="Free state pages">No, everything in the state</td><td data-label="BidBell daily alert" class="yes">Your trade, states and eligibility</td></tr>
      <tr><th scope="row">Who has the job now and what they were paid</th><td data-label="Free state pages">No</td><td data-label="BidBell daily alert" class="yes">Yes, where a match is found</td></tr>
      <tr><th scope="row">Contracts ending in the next 3&ndash;6 months</th><td data-label="Free state pages">No</td><td data-label="BidBell daily alert" class="yes">Yes</td></tr>
      <tr><th scope="row">Deadline and site-visit reminders</th><td data-label="Free state pages">No</td><td data-label="BidBell daily alert" class="yes">Yes</td></tr>
    </tbody></table></div>
</div></section>

<section id="pricing" aria-labelledby="pricing-h"><div class="wrap">
  <div class="section-head center">
    <p class="eyebrow">Pricing</p>
    <h2 id="pricing-h">One simple plan. Free for 14 days.</h2>
    <p>No card to start. If the alerts aren&rsquo;t useful, do nothing and they stop.</p>
  </div>
  <div class="plans">
    <div class="plan best"><h3>Monthly</h3>
      <p class="price">${sp}<span> /month</span></p><p class="desc">Billed every month until you cancel. Cancel anytime.</p>
      {plan_items(['Daily alert filtered to your business', 'One trade group, up to 10 states or nationwide', 'Contract history and contracts ending soon', 'Deadline and site-visit reminders', '30-day money-back guarantee'])}
      <a class="btn" href="{su}">Start 14 days free</a></div>
    <div class="plan"><span class="badge">2 months free</span><h3>Yearly</h3>
      <p class="price">${ap}<span> /year</span></p><p class="desc">Billed every year until you cancel, ${sp * 12 - ap} less than paying monthly.</p>
      {plan_items(['Everything in Monthly', 'One payment a year', '30-day money-back guarantee'])}
      <a class="btn ghost" href="{su}">Start 14 days free</a></div>
  </div>
  <p class="small muted center-note">Prices in US dollars. Plans renew automatically until you cancel. Payments are handled by Paddle.com, our merchant of record; any sales tax is shown at checkout. See our <a href="/refunds/">refund policy</a>.</p>
</div></section>

<section id="about" class="tint" aria-labelledby="about-h"><div class="wrap two">
  <figure class="flush">
    <div class="photo"><img srcset="/img/capitol-960.webp 960w, /img/capitol-1250.webp 1250w" sizes="(min-width: 60rem) 36rem, 100vw" src="/img/capitol-1250.webp" width="1250" height="900" loading="lazy" decoding="async" alt="The US Capitol dome at sunrise, with birds flying past"></div>
    <figcaption class="photo-cap">US Capitol at sunrise. Photo: Duane Lempke, public domain (CC0), via Wikimedia Commons.</figcaption>
  </figure>
  <div>
    <p class="eyebrow">About BidBell</p>
    <h2 id="about-h">Built for the companies that keep federal buildings clean.</h2>
    <p>Every week, federal agencies post cleaning contracts for Army reserve centers, VA cemeteries, airport control towers and national-forest cabins. Many are set aside for small businesses, yet they are hard to find: spread across SAM.gov, written in government shorthand and filed under the contracting office instead of where the work is.</p>
    <p>BidBell does that search every morning, so cleaning companies can spend their time bidding instead of searching.</p>
    <p>Bids come from {ext('https://sam.gov/', 'SAM.gov')} and past contracts from {ext('https://www.usaspending.gov/', 'USAspending.gov')}, both free public US government sources. Always read the official notice before you bid; see our <a href="/disclaimer/">disclaimer</a>.</p>
    <p class="small muted">BidBell is run by {E(C['owner_name'])}. Mailing address: {E(C['mailing_address'])}. Email <a href="mailto:{C['email']}">{C['email']}</a>. We answer every email.</p>
  </div>
</div></section>

<section id="faq" aria-labelledby="faq-h"><div class="wrap faq">
  <div>
    <p class="eyebrow">FAQ</p>
    <h2 id="faq-h">Questions, answered.</h2>
    <p class="muted">Something else? Email <a href="mailto:{C['email']}">{C['email']}</a>. We reply within one business day.</p>
  </div>
  <div>{faq_html}</div>
</div></section>

<section class="final" aria-label="Start your free trial"><div class="wrap">
  <div class="cta-band">
    <h2>See your first alert tomorrow morning.</h2>
    <p>Tell us your trade, states and eligibility in 2 minutes. Your free 14 days start with the next morning&rsquo;s email.</p>
    <div class="cta-row"><a class="btn light" href="{su}">Start 14 days free {ICON['arrow']}</a></div>
    {checks(['No card required', f'${sp}/month after, or ${ap}/year', 'Cancel anytime'])}
  </div>
</div></section>'''
    org = {'@context': 'https://schema.org', '@type': 'Organization', 'name': 'BidBell', 'url': BASE + '/',
           'logo': BASE + '/og.png', 'email': C['email'],
           'address': {'@type': 'PostalAddress', 'streetAddress': C['address_parts']['street'],
                       'addressLocality': C['address_parts']['city'], 'addressRegion': C['address_parts']['region'],
                       'postalCode': C['address_parts']['postal'], 'addressCountry': C['address_parts']['country']}}
    offer = lambda name, price, dur: {'@type': 'Offer', 'name': name, 'price': f'{price}.00', 'priceCurrency': 'USD',
                                      'availability': 'https://schema.org/InStock', 'url': BASE + '/#pricing',
                                      'priceSpecification': {'@type': 'UnitPriceSpecification', 'price': f'{price}.00',
                                                             'priceCurrency': 'USD', 'billingDuration': dur}}
    product = {'@context': 'https://schema.org', '@type': 'Product', 'name': 'BidBell daily government bid alerts',
               'description': 'A daily email of US federal cleaning contract bids filtered by trade, state and eligibility, with contract history, contracts ending soon and deadline reminders.',
               'brand': {'@type': 'Brand', 'name': 'BidBell'}, 'image': BASE + '/og.png',
               'offers': [offer('Monthly', sp, 'P1M'), offer('Yearly', ap, 'P1Y')]}
    faqld = {'@context': 'https://schema.org', '@type': 'FAQPage',
             'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': html.unescape(re.sub(r'<[^>]+>', '', a))}}
                            for q, a in FAQ]}
    write('', layout('', 'BidBell | Federal cleaning bids you can actually win',
                     'Every morning, BidBell emails US cleaning companies only the federal janitorial, carpet and window-cleaning bids in their states that they are allowed to bid on, with who holds each job now and what they were paid.',
                     body, [org, product, faqld]))


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
    return f'''<form class="signup" id="signup" action="{E(post)}" method="post" accept-charset="utf-8" data-thanks="/start/thanks/">
  <div class="form-error" id="form-error" role="alert" hidden></div>
  <fieldset>
    <legend>About you</legend>
    <div class="fields">
      <div class="field"><label for="f-first">First name</label><input id="f-first" type="text" name="{f['first']}" required autocomplete="given-name"></div>
      <div class="field"><label for="f-email">Business email</label><input id="f-email" type="email" name="{f['email']}" required autocomplete="email" placeholder="you@company.com"></div>
      <div class="field"><label for="f-biz">Business name</label><input id="f-biz" type="text" name="{f['business']}" required autocomplete="organization"></div>
      <div class="field"><label for="f-web">Business website <span class="opt">(optional)</span></label><input id="f-web" type="text" inputmode="url" name="{f['website']}" autocomplete="url" placeholder="yourcompany.com"></div>
    </div>
  </fieldset>
  <fieldset data-need="1" data-label="the cleaning work you do">
    <legend>What cleaning work do you do?</legend>
    <p class="hint">Choose all that apply.</p>
    <div class="options">{''.join(opt('checkbox', f['trades'], v) for v in TRADE_CHOICES)}</div>
  </fieldset>
  <fieldset data-need="1" data-max="10" data-label="your states">
    <legend>Which states do you work in?</legend>
    <p class="hint">Choose up to 10 states, or Nationwide. Bids are matched to where the work is.</p>
    <div class="state-box">{states}</div>
  </fieldset>
  <fieldset data-need="1" data-label="whether your business is any of these">
    <legend>Is your business any of these?</legend>
    <p class="hint">This decides which set-aside bids you see. Choose all that apply.</p>
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
    <p class="small muted">No card needed. Your answers are sent securely to BidBell&rsquo;s private Google Forms account.</p>
  </div>
</form>
<script src="/form.js" defer></script>'''


def start():
    form = signup_form()
    if form:
        action = f'<div class="card form-card">{form}</div>'
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
    body = f'''<div class="page-head"><div class="wrap">
  <p class="crumbs"><a href="/">Home</a> / Start free trial</p>
  <h1>Start your free 14 days</h1>
  <p class="lead">Tell us about your business once. Your first alert arrives the next morning, around 6 AM your time. No card needed.</p>
</div></div>
<div class="wrap page"><div class="signup-grid">
  {action}
  <aside class="aside">
    <div class="card">
      <h2>What happens next</h2>
      <ol class="next-steps">
        <li><div><b>We confirm your details</b><span>By email, within 1 business day.</span></div></li>
        <li><div><b>Your alerts start</b><span>The next morning, around 6 AM your time, on days with matching bids.</span></div></li>
        <li><div><b>Day 12: your summary</b><span>The bids you received, and a secure checkout link: ${C['standard_price']}/month or ${C['annual_price']}/year.</span></div></li>
        <li><div><b>Or do nothing</b><span>Your alerts stop after 14 days. Nothing is charged.</span></div></li>
      </ol>
    </div>
    <div class="card">
      <h2>We never ask for</h2>
      <p>Passwords, card numbers, tax IDs or any government ID numbers. See how we handle your details in our <a href="/privacy/">privacy policy</a>.</p>
    </div>
  </aside>
</div></div>'''
    thanks = f'''<div class="page-head"><div class="wrap">
  <p class="crumbs"><a href="/">Home</a> / <a href="/start/">Start free trial</a> / Done</p>
  <h1>You&rsquo;re in.</h1>
  <p class="lead">Thanks for signing up for BidBell. We&rsquo;ll confirm your details by email within 1 business day, and your free 14 days of alerts start the next morning, around 6 AM your time.</p>
  <div class="cta-row"><a class="btn" href="/#sample">See what an alert looks like</a><a class="btn ghost" href="/cleaning-bids/">Browse this week&rsquo;s bids</a></div>
  <p class="small muted">No email from us within 1 business day? Check your spam folder, then write to <a href="mailto:{C['email']}">{C['email']}</a> so we can make sure your sign-up reached us. Something wrong, or want to change your states? Email us at the same address.</p>
</div></div>'''
    write('start/thanks/', layout('start/thanks/', 'You\u2019re in | BidBell', 'Your free BidBell trial has started.', thanks, noindex=True), sitemap=False)
    write('start/', layout('start/', 'Start your free 14 days | BidBell',
                           'Start a free 14-day BidBell trial: daily federal cleaning bids for your trade, states and eligibility. No card needed.', body))


# ------------------------------------------------------------------ subscribe (trial customers choose a plan)
def subscribe():
    """/subscribe/?plan=monthly|yearly&c=<customer id>: linked from the trial emails; not in the sitemap, noindex.
    checkout.js highlights the plan from ?plan= and opens Paddle's overlay checkout; tools/paddle.json holds the settings."""
    sp, ap = C['standard_price'], C['annual_price']
    mail = f'<a href="mailto:{C["email"]}">{C["email"]}</a>'
    agree = 'By continuing you agree to the <a href="/terms/">Terms</a> and the <a href="/refunds/">Refund policy</a>.'

    def card(key, name, price, per, renews, items, badge=''):
        button = (f'<p class="small muted terms-line">{agree}</p>'
                  f'<button class="btn{"" if key == "monthly" else " ghost"}" type="button" data-checkout="{key}">'
                  f'Subscribe for ${price}/{per}</button>') if PADDLE_READY else ''
        lis = ''.join(f'<li>{ICON["check"]}<span>{x}</span></li>' for x in items)
        return (f'<div class="plan{" best" if key == "monthly" else ""}" data-plan="{key}">{badge}<h3>{name}</h3>'
                f'<p class="price">${price}<span> /{per}</span></p><p class="desc">{renews}</p><ul>{lis}</ul>{button}</div>')

    plans = (card('monthly', 'Monthly', sp, 'month', 'Renews every month until you cancel.',
                  ['30-day money-back guarantee', 'Cancel anytime']) +
             card('yearly', 'Yearly', ap, 'year', 'Renews every year until you cancel.',
                  [f'${sp * 12 - ap} less than paying monthly', '30-day money-back guarantee', 'Cancel anytime'],
                  '<span class="badge">2 months free</span>'))
    if PADDLE_READY:
        cfg = {'env': PADDLE['env'], 'client_token': PADDLE['client_token'].strip(),
               'prices': {'monthly': PADDLE['price_monthly'].strip(), 'yearly': PADDLE['price_yearly'].strip()},
               'success_url': BASE + '/subscribe/thanks/'}
        cfg_json = json.dumps(cfg, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
        foot = (f'<div class="form-error" id="checkout-error" role="alert" hidden>The secure checkout could not load. '
                f'Please refresh the page and try again, or email {C["email"]}.</div>'
                f'<p class="small muted">Prices in US dollars. Checkout is handled by Paddle.com, our merchant of record. '
                f'Any sales tax is shown before you pay. Your receipt comes from Paddle.</p>')
        scripts = (f'\n<script type="application/json" id="paddle-config">{cfg_json}</script>'
                   '\n<script src="https://cdn.paddle.com/paddle/v2/paddle.js" defer></script>'
                   '\n<script src="/checkout.js" defer></script>')
    else:
        foot = (f'<div class="note"><p>Payments open soon. We\'ll email you as soon as you can subscribe; your alerts keep going until then.</p></div>'
                f'<p class="small muted">Prices in US dollars. {agree}</p>')
        scripts = '\n<script src="/checkout.js" defer></script>'
    phone = f' or call {phone_link()}' if PHONE.strip() else ''
    body = f'''<div class="page-head"><div class="wrap">
  <p class="crumbs"><a href="/">Home</a> / Choose your plan</p>
  <h1>Choose your plan</h1>
  <p class="lead">Keep your BidBell alerts coming after your free trial. Pick monthly or yearly.</p>
</div></div>
<div class="wrap page">
  <h2 class="sr-only">Plans</h2>
  <div class="plans">{plans}</div>
  <div class="subscribe-foot">
    {foot}
    <p class="small muted">Questions? Email {mail}{phone}.</p>
  </div>
</div>{scripts}'''
    thanks = f'''<div class="page-head"><div class="wrap">
  <p class="crumbs"><a href="/">Home</a> / Subscription</p>
  <h1>Thank you &mdash; your subscription is active.</h1>
  <p class="lead">Your alerts continue as usual; your receipt comes from Paddle.</p>
  <div class="cta-row"><a class="btn" href="/">Back to BidBell</a><a class="btn ghost" href="/refunds/">Refund policy</a></div>
  <p class="small muted">Questions about your plan? Email {mail}{phone}.</p>
</div></div>'''
    write('subscribe/thanks/', layout('subscribe/thanks/', 'Subscription active | BidBell',
                                      'Your BidBell subscription is active.', thanks, noindex=True), sitemap=False)
    write('subscribe/', layout('subscribe/', 'Choose your plan | BidBell',
                               f'Choose a BidBell plan: ${sp}/month or ${ap}/year, renews until you cancel, 30-day money-back guarantee.',
                               body, noindex=True, csp=CSP_PADDLE if PADDLE_READY else CSP), sitemap=False)


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
            lst = f'<div class="note"><p>No open federal cleaning notices were listed for {name} in this week\'s data. When one is posted, BidBell subscribers who work in {name} get it in their next morning&rsquo;s email.</p></div>'
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
            f'<div class="note"><p>No open federal {words} notices were listed in this week\'s data.</p></div>'
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
            f'<p class="muted flush">Last updated {long_date(upd)}</p></div></div>'
            f'<div class="wrap narrow legal page">{inner}</div>')
    write(path, layout(path, f'{title} | BidBell', desc, body, updated=upd), lastmod=upd)


def legal():
    who = f'{E(C["owner_name"])}, trading as BidBell (&ldquo;BidBell&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;). Mailing address: {E(C["mailing_address"])}. Email: <a href="mailto:{C["email"]}">{C["email"]}</a>'
    phone = f' Phone: {phone_link()}.' if PHONE.strip() else ''
    mail = f'<a href="mailto:{C["email"]}">{C["email"]}</a>'
    sp, ap = C['standard_price'], C['annual_price']

    legal_page('terms/', 'Terms of Service', 'The terms that apply when you use BidBell.', f'''
<p>These terms are an agreement between you (the business using BidBell, and the person accepting for it) and {who}. By starting a trial or subscription you accept them. Nothing in these terms takes away rights you have under a law that cannot be excluded by contract.</p>
<h2>1. What BidBell is</h2>
<p>BidBell is an email service. Each morning we read new US federal contract notices published on SAM.gov, select the ones that match the trades, states and eligibility you give us, and email them to you. Where we can, we add information from USAspending.gov about the likely current or previous contract for the same work. We also publish free public pages listing open federal cleaning notices by state. We are not a government service, a bidding agent, a law firm or a consultant.</p>
<h2>2. Free trial</h2>
<p>New customers get a free 2-week trial. We do not ask for a card to start it. If you do not subscribe, your alerts stop at the end of the trial and nothing is charged.</p>
<h2>3. Plans, payment and taxes</h2>
{lawyer('Merchant of record / payments', 'Terms 3: Paddle as reseller and merchant of record (Paddle-required wording), seller identity as a sole proprietor, billing in advance, automatic renewal, and price-change notice.')}
<p>BidBell is operated from Kenya by {E(C["owner_name"])}, a sole proprietor (not a registered company) trading as BidBell. Our US mailing address is {E(C["mailing_address"])}.</p>
<p>Our order process is conducted by our online reseller Paddle.com. Paddle.com is the Merchant of Record for all our orders. Paddle provides all customer service inquiries and handles returns.</p>
<p>Paid plans are ${sp}/month or ${ap}/year, in US dollars, billed in advance. Paddle charges your payment method, sends your receipt and collects any sales tax, which is shown at checkout. Paddle's own terms apply to the purchase. We never see or store your card details.</p>
<p>Your subscription renews automatically at the end of each month or year, and the plan price is charged for the next period, until you cancel. We may change our prices; we will email you at least 30 days before a change affects your next renewal, and you can cancel before it does.</p>
<h2>4. Cancelling and refunds</h2>
<p>You can cancel anytime by emailing <a href="mailto:{C["email"]}">{C["email"]}</a> or replying to any BidBell email. Your alerts continue until the end of the period you have paid for, and you are not charged again. Every payment has a 30-day money-back guarantee; see our <a href="/refunds/">Refund policy</a>.</p>
<h2>5. Your responsibilities</h2>
<p>You are responsible for giving us accurate details, for reading the full official notice and its attachments before relying on any bid, for checking deadlines, eligibility and requirements yourself, for your registration in SAM.gov, and for every decision to bid or not bid. You must follow our <a href="/acceptable-use/">acceptable use policy</a>.</p>
<h2>6. Accuracy of information</h2>
{lawyer('Warranty disclaimer', 'Terms 6: "as is" disclaimer of warranties (enforceability varies by state and country).')}
<p>BidBell is provided &ldquo;as is&rdquo; and &ldquo;as available&rdquo;. We work carefully, but the information comes from public government sources that can be incomplete, late, amended or withdrawn, and our matching (for example of work sites, eligibility and likely current contracts) can be wrong. To the fullest extent the law allows, we make no warranties, express or implied, including that every relevant notice will be found, that any information is accurate or complete, that the service will be uninterrupted, or that you will win any contract. See our <a href="/disclaimer/">disclaimer</a>.</p>
<h2>7. Limitation of liability</h2>
{lawyer('Liability cap and exclusions', 'Terms 7: liability capped at fees paid in the previous 3 months; exclusion of indirect loss and of liability for missed, changed or withdrawn notices and bid outcomes.')}
<p>To the fullest extent the law allows: (a) we are not liable for any indirect, incidental, special or consequential loss, or for lost profits, revenue, contracts or business opportunities; (b) we are not liable for any notice that we did not send, sent late, or that was changed or withdrawn, or for the outcome of any bid; and (c) our total liability for all claims relating to BidBell is limited to the fees you paid us in the 3 months before the event giving rise to the claim. These limits do not apply to liability that cannot be limited by law, such as for fraud.</p>
<h2>8. Indemnity</h2>
{lawyer('Indemnity', 'Terms 8: customer indemnity for misuse, resale or breach.')}
<p>You agree to compensate us for reasonable losses and costs (including reasonable legal fees) arising from your breach of these terms, your misuse of BidBell, or your resale or republishing of our alerts.</p>
<h2>9. Suspension and ending the service</h2>
<p>We may suspend or end your access if you break these terms, if payment fails, or if we stop offering BidBell. If we end the service for reasons other than your breach, we will refund any unused prepaid period.</p>
<h2>10. Changes to these terms</h2>
<p>We may update these terms. For changes that materially affect you, we will email subscribers at least 30 days before they take effect. If you do not agree, you can cancel before then. The date at the top shows the latest version.</p>
<h2>11. Governing law and disputes</h2>
{lawyer('Governing law and venue', f"Terms 11: governing law ({C['governing_law']}) and venue ({C['venue']}); consumer and small-business protections; whether to add arbitration.")}
<p>If you have a problem, please email us first; most issues are solved quickly, and we will respond within 5 business days. If a dispute is not solved within 30 days of your first message, it will be governed by the laws of {E(C["governing_law"])}, without regard to conflict-of-law rules, and resolved in {E(C["venue"])}, unless the law where you are located requires otherwise.</p>
<h2>12. General</h2>
<p>If any part of these terms is found unenforceable, the rest stays in effect. If we do not enforce a right, we have not waived it. You may not transfer your subscription without our written consent. These terms, with the policies linked here, are the whole agreement between you and us about BidBell.</p>
<h2>13. Contact</h2>
<p>{who}.{phone}</p>''')

    legal_page('privacy/', 'Privacy Policy', 'What BidBell collects, why, who processes it, how long we keep it and your rights.', f'''
<p>This policy explains how {who} handles personal information. We collect as little as we can, we do not sell it, and this website uses no tracking or advertising cookies.</p>
<h2>1. What we collect</h2>
<ul>
<li><strong>Trial and subscriber details</strong> you give us: first name, business email, business name and website, trades, states, eligibility (small business, HUBZone, SDVOSB, 8(a), WOSB) and whether you are registered in SAM.gov.</li>
<li><strong>Payment information</strong> from Paddle: your name, email, country, plan, amounts and subscription status. We never receive your card details.</li>
<li><strong>Emails</strong> you send us, and replies to our emails.</li>
<li><strong>Business contact details</strong> of companies we may email about BidBell: company name, business location, and a business email address published on the company's own website or in public government contract records. See our <a href="/email-policy/">email policy</a>.</li>
</ul>
<p>We do not ask for passwords, card numbers, tax IDs or government ID numbers.</p>
<h2>2. Why we use it</h2>
{lawyer('Legal bases', 'Privacy 2: legal bases for EU/UK visitors (contract, legitimate interests) and the legitimate-interest basis for business outreach.')}
<p>To provide the service you asked for (sending your alerts, managing your trial and subscription, answering you); to keep records required for tax and accounting; and, for business contacts, to offer BidBell to companies that may need it (our legitimate interest), with an easy opt-out.</p>
<h2>3. Who processes it for us</h2>
{lawyer('Processors and transfers', 'Privacy 3: list of processors, international transfers, and data processing agreements with each.')}
<ul>
<li><strong>Google Workspace</strong> (Google LLC): our email, and our sign-up form (Google Forms). Sign-up answers are stored in BidBell&rsquo;s private Google account.</li>
<li><strong>GitHub</strong> (GitHub, Inc.): runs the program that sends alerts and hosts this website. GitHub may log visitor IP addresses for security; see GitHub's privacy statement.</li>
<li><strong>Paddle</strong> (Paddle.com Market Ltd and its affiliates): our merchant of record. Paddle processes your payment details, billing address and email to handle purchases and tax.</li>
<li><strong>Anthropic</strong> (Anthropic, PBC): Claude, an AI assistant, helps us draft replies to the emails you send us.</li>
</ul>
<p>These providers process data on our instructions and under their own security and privacy commitments. Data may be processed in the United States, the European Union and other countries where they operate.</p>
<h2>4. How long we keep it</h2>
{lawyer('Retention periods', 'Privacy 4: retention periods (trial 12 months, customers +2 years, suppression list kept indefinitely).')}
<ul>
<li>Trial details, if you do not subscribe: up to 12 months after the trial ends.</li>
<li>Customer details: while you are subscribed, then up to 2 years for records, or longer where tax law requires.</li>
<li>Business contacts who opt out: we keep only the email address on a do-not-contact list, so we never email it again.</li>
</ul>
<h2>5. Your rights</h2>
{lawyer('Rights for US states and EU/UK', 'Privacy 5: rights wording for California and other US states, EU/UK GDPR, response times, and supervisory-authority complaint.')}
<p>Wherever you are, you can ask us to tell you what we hold about you, correct it, delete it, or stop contacting you. Email <a href="mailto:{C["email"]}">{C["email"]}</a>; we reply within 30 days and do not charge.</p>
<p><strong>California and other US states:</strong> you have the right to know, access, correct and delete your personal information, and not to be discriminated against for using these rights. We do not sell or share personal information for cross-context behavioral advertising, and we do not use it for profiling.</p>
<p><strong>European Union and United Kingdom:</strong> you also have the rights to object, to restrict processing and to data portability, and you may complain to your local data protection authority.</p>
<h2>6. Cookies and tracking</h2>
<p>This website sets no cookies and uses no analytics or advertising pixels. The only third-party script is Paddle&rsquo;s checkout (Paddle.js), which loads only on our plan page (/subscribe/) so you can pay; Paddle may use cookies there for checkout and fraud prevention, under Paddle&rsquo;s own privacy notice. Our emails contain no tracking pixels.</p>
<h2>7. Security</h2>
<p>We use providers with strong security, two-step verification on every account, and we keep customer data out of this public website. No system is perfectly secure; if a breach affects you, we will tell you as the law requires.</p>
<h2>8. Children</h2>
<p>BidBell is a business service and is not meant for anyone under 18.</p>
<h2>9. Changes</h2>
<p>We will post changes here and email subscribers about material changes before they take effect.</p>
<h2>10. Contact</h2>
<p>For privacy questions or requests, email {mail} or write to {E(C["owner_name"])}, BidBell, at our US mailing address: {E(C["mailing_address"])}. BidBell is operated from Kenya.{phone}</p>''')

    legal_page('refunds/', 'Refund policy', 'BidBell refund policy: a 30-day money-back guarantee on every payment, and how to cancel.', f'''
{lawyer('Refunds and automatic renewal', 'Refund policy and Terms 3-4: 30-day money-back guarantee, automatic-renewal disclosures and cancellation by email, under state automatic-renewal laws (for example California).')}
<p>Every plan starts with a free 14-day trial, with no card needed, so you can judge the alerts before you pay.</p>
<h2>30-day money-back guarantee</h2>
<p>If you are not happy with BidBell, we will refund any payment in full, on the monthly or the yearly plan, if you ask within 30 days of that payment.</p>
<h2>How to ask for a refund</h2>
<p>Email {mail}, or reply to any BidBell email, within 30 days of the payment.{f" You can also call us at {phone_link()}." if PHONE.strip() else ""}</p>
<h2>How refunds are paid</h2>
<p>Our payments are handled by Paddle.com, our merchant of record, so Paddle issues your refund to your original payment method. How long it takes to show depends on your bank or card provider.</p>
<h2>Cancelling</h2>
<p>Your subscription renews automatically until you cancel, and you can cancel anytime: email {mail} or reply to any BidBell email. After you cancel, you are not charged again, and your alerts continue to the end of the period you have paid for.</p>
<p>See also our <a href="/terms/">Terms of Service</a>.</p>''')

    legal_page('acceptable-use/', 'Acceptable Use Policy', 'How BidBell alerts and pages may be used.', f'''
{lawyer('Acceptable use', 'Acceptable use: resale ban, one-business-per-subscription rule, and enforcement.')}
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
{lawyer('Disclaimer', 'Disclaimer page as a whole: data-accuracy, no-affiliation and no-advice statements.')}
<h2>Not a government service</h2>
<p>BidBell is a private service. It is not affiliated with, endorsed by or connected to SAM.gov, the General Services Administration, USAspending.gov or any government agency.</p>
<h2>Data can change</h2>
<p>We use public government data. Notices can be incomplete, published late, amended or withdrawn after we send them, and deadlines are set in each notice's own time zone. Always read the full official notice and its attachments on SAM.gov before relying on anything we send.</p>
<h2>Matches are estimates</h2>
<p>Work sites, eligibility, site-visit dates read from notice text, and especially the &ldquo;likely current contract&rdquo;, the contracts shown as ending soon and their amounts are our best reading of public records. They can be wrong or missing, and an agency can extend a contract or change its plans. Contract totals are the amounts the government committed (obligated) and can include option years or later changes. Reminders use the notice as it stands when we check it; the official notice and its attachments are always the authority.</p>
<h2>No advice, no guarantee</h2>
<p>Nothing from BidBell is legal, financial, tax or bidding advice. We do not guarantee that you will find, bid on or win any contract.</p>''')

    legal_page('email-policy/', 'Email Policy', 'How BidBell contacts businesses and how to opt out.', f'''
{lawyer('CAN-SPAM and outreach', 'Email policy: outreach practices, CAN-SPAM compliance, and whether any recipient states or countries need extra rules.')}
<h2>Who we email</h2>
<p>We send a small number of emails to businesses that may need BidBell: companies in cleaning and facility services whose business email address is published on their own website or in public US government contract records. We never buy lists of personal email addresses.</p>
<h2>What every email contains</h2>
<ul>
<li>Our real name and business name, and an honest subject line.</li>
<li>Our mailing address: {E(C["mailing_address"])}.</li>
<li>A clear way to stop: reply &ldquo;no&rdquo; and we will not email you again.</li>
</ul>
<p>We send at most one first email and two short follow-ups, and we stop as soon as you reply.</p>
<h2>Opting out</h2>
<p>Reply &ldquo;no&rdquo; or &ldquo;unsubscribe&rdquo;, or email <a href="mailto:{C["email"]}">{C["email"]}</a>. We act on it straight away and always within 10 business days, as the US CAN-SPAM Act requires. Your address goes on our do-not-contact list so it is never emailed again.</p>
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
          '<div class="cta-row"><a class="btn" href="/">Go to the home page</a><a class="btn ghost" href="/cleaning-bids/">Cleaning bids by state</a></div></div></div>',
          noindex=True), sitemap=False)
    exp = date(TODAY.year + 1, TODAY.month, 1) if TODAY.month > 1 else date(TODAY.year, 12, 1)
    os.makedirs(os.path.join(ROOT, '.well-known'), exist_ok=True)
    open(os.path.join(ROOT, '.well-known', 'security.txt'), 'w').write(
        f'Contact: mailto:{C["email"]}\nExpires: {exp.isoformat()}T00:00:00.000Z\nPreferred-Languages: en\n'
        f'Canonical: {BASE}/.well-known/security.txt\n')
    open(os.path.join(ROOT, 'robots.txt'), 'w').write(f'User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n')
    urls = ''.join(f'<url><loc>{BASE}/{p}</loc><lastmod>{m}</lastmod></url>' for p, m in PAGES)
    open(os.path.join(ROOT, 'sitemap.xml'), 'w').write(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    open(os.path.join(ROOT, 'CNAME'), 'w').write(C['domain'] + '\n')
    open(os.path.join(ROOT, '.nojekyll'), 'w').write('')
    shutil.copy(os.path.join(T, 'style.css'), os.path.join(ROOT, 'style.css'))
    shutil.copy(os.path.join(T, 'form.js'), os.path.join(ROOT, 'form.js'))
    shutil.copy(os.path.join(T, 'checkout.js'), os.path.join(ROOT, 'checkout.js'))
    open(os.path.join(ROOT, 'favicon.svg'), 'w').write(
        BELL.replace('aria-hidden="true" focusable="false"', 'xmlns="http://www.w3.org/2000/svg"').replace('currentColor', '#C8102E'))


def main():
    home(); start(); subscribe(); bid_pages(); legal(); extras()
    open(os.path.join(T, 'LAWYER_REVIEW.md'), 'w').write(
        '# Clauses for a lawyer to review\n\n' + ''.join(f'{i}. {t}\n' for i, t in enumerate(LAWYER, 1)))
    print(f'built {len(PAGES)} pages + 404, sitemap, robots, security.txt; {len(LAWYER)} lawyer-review items; '
          f'/subscribe/ checkout {"ON (" + PADDLE["env"] + ")" if PADDLE_READY else "off (tools/paddle.json not filled in)"}; '
          f'phone {"shown" if PHONE.strip() else "not set"}')


if __name__ == '__main__':
    main()

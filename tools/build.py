#!/usr/bin/env python3
"""
Builds the whole BidBell website as static files (no JavaScript, no server, no database).

  python3 tools/build.py            -> writes every page into the project root
Inputs:  tools/site.json (business facts), tools/style.css, data/cleaning_bids.json (public SAM.gov data)
Run by the weekly GitHub Action after tools/update_bids.py refreshes the bid data.

Legal clauses a lawyer should review are marked in the HTML with  <!-- LAWYER-REVIEW: ... -->
"""
import html, json, os, shutil
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, 'tools')
C = json.load(open(os.path.join(T, 'site.json')))
DATA = json.load(open(os.path.join(ROOT, 'data', 'cleaning_bids.json')))
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
    return f'<!-- LAWYER-REVIEW {len(LAWYER)}: {E(tag)} -->'


BELL = ('<svg viewBox="0 0 32 32" aria-hidden="true" focusable="false"><path fill="currentColor" '
        'd="M16 3a2 2 0 0 1 2 2v.7a8.5 8.5 0 0 1 6.5 8.3v5.2l2.3 3.3a1 1 0 0 1-.8 1.5H6a1 1 0 0 1-.8-1.5l2.3-3.3V14'
        'a8.5 8.5 0 0 1 6.5-8.3V5a2 2 0 0 1 2-2Zm-3.2 22h6.4a3.2 3.2 0 0 1-6.4 0Z"/></svg>')


def start_url():
    return C['form_url'] or '/start/'


def layout(path, title, desc, body, jsonld=None, updated=None, noindex=False, og_type='website'):
    url = BASE + '/' + path
    ld = ''.join(f'\n<script type="application/ld+json">{json.dumps(j, separators=(",", ":"))}</script>'
                 for j in (jsonld or []))
    upd = updated or TODAY
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; upgrade-insecure-requests">
<meta name="referrer" content="strict-origin-when-cross-origin">
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
<meta name="theme-color" content="#F8F6F1" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#12151B" media="(prefers-color-scheme: dark)">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/style.css">{ld}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-head"><div class="wrap">
  <a class="logo" href="/">{BELL}BidBell</a>
  <nav class="nav" aria-label="Main">
    <a href="/#what-you-get">What you get</a><a href="/#pricing">Pricing</a><a href="/cleaning-bids/">Cleaning bids</a><a href="/#faq">FAQ</a>
    <a class="btn small" href="{E(start_url())}">Start 2 weeks free</a>
  </nav>
</div></header>
<main id="main">
{body}
</main>
<footer class="site-foot"><div class="wrap">
  <nav aria-label="Footer">
    <a href="/terms/">Terms</a><a href="/privacy/">Privacy</a><a href="/refunds/">Refunds</a><a href="/acceptable-use/">Acceptable use</a><a href="/disclaimer/">Disclaimer</a><a href="/email-policy/">Email policy</a><a href="/cleaning-bids/">Cleaning bids by state</a><a href="mailto:{C['email']}">{C['email']}</a>
  </nav>
  <p>BidBell is run by {E(C['owner_name'])}. Mailing address: {E(C['mailing_address'])}.</p>
  <p>Not affiliated with SAM.gov, GSA or any government agency. Page updated {long_date(upd)}. &copy; {TODAY.year} BidBell.</p>
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


def bid_table(bids, caption):
    rows = []
    for b in bids:
        where = ', '.join(x for x in (b['city'], STATES.get(b['state'], b['state'])) if x)
        rows.append(f'<tr><td data-label="Notice">{ext(b["link"], E(b["title"]))}<br><span class="small muted">{E(fix_case(b["agency"]))}'
                    f'{" &middot; Ref " + E(b["sol"]) if b["sol"] else ""}</span></td>'
                    f'<td data-label="Work site">{E(where)}</td><td data-label="Respond by">{nice(b["due"])}</td>'
                    f'<td data-label="Stage">{E(TYPE_WORDS.get(b["type"], b["type"]))}</td>'
                    f'<td data-label="Who can bid">{E(b["set_aside"] or "No set-aside listed")}</td></tr>')
    return (f'<div class="table-wrap"><table class="stack"><caption>{caption}</caption><thead><tr><th scope="col">Notice</th>'
            f'<th scope="col">Work site</th><th scope="col">Respond by</th><th scope="col">Stage</th>'
            f'<th scope="col">Who can bid</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def cta_box(heading='Get the right bids every morning instead'):
    return f'''<div class="card featured">
  <h2>{heading}</h2>
  <p>This page is a free weekly snapshot of every open federal cleaning notice. BidBell subscribers get, every morning around 6am Eastern, only the bids in their states that their business is allowed to bid on, plus who holds each job now, what they were paid, and the contracts ending soon in their area.</p>
  <div class="cta-row"><a class="btn" href="{E(start_url())}">Start 2 weeks free</a><a class="btn ghost" href="/#what-you-get">See what you get</a></div>
  <p class="small">No card needed. ${C['founding_price']}/month after the trial for our first {C['founding_spots']} customers. Cancel anytime.</p>
</div>'''


# ------------------------------------------------------------------ home
FAQ = [
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
     'It depends on your trade and states. Some days there are none, and then we send nothing. We never pad the email with bids you cannot use.'),
    ('What does "likely current contract" mean?',
     'We find the previous contract for a site by matching the location and description in public award records. '
     'Most matches are exact; some are close, and some bids have no match. We label them honestly and link to the official record so you can check.'),
    ('How do I pay, and how do I cancel?',
     f'After your free 2 weeks we email you a secure checkout link from Lemon Squeezy, our payment provider. '
     f'You can cancel anytime from the link in your receipt or by replying to any BidBell email; you keep access until the end of the period you paid for.'),
    ('Is my information safe?',
     'We collect only what we need to send your alerts: your name, business details, trades, states and eligibility. '
     'We never see your card, we do not sell data, and this website has no tracking or advertising cookies.'),
]


def home():
    fp, sp, ap = C['founding_price'], C['standard_price'], C['annual_price']
    faq_html = ''.join(f'<details><summary>{E(q)}</summary><p>{E(a)}</p></details>' for q, a in FAQ)
    body = f'''
<div class="wrap hero">
  <p class="eyebrow">For US cleaning companies</p>
  <h1>Government cleaning contracts you can actually bid on. Every morning.</h1>
  <p class="lead">BidBell checks every new federal contract notice and emails you only the janitorial, carpet and window-cleaning bids in your states that your business is allowed to bid on, with who holds each job now and what they were paid.</p>
  <div class="cta-row"><a class="btn" href="{E(start_url())}">Start 2 weeks free</a><a class="btn ghost" href="#sample">See a real alert</a></div>
  <p class="small muted">No card needed &middot; Cancel anytime &middot; Not affiliated with SAM.gov or the US government</p>
</div>

<section id="how" aria-labelledby="how-h"><div class="wrap">
  <h2 id="how-h">How it works</h2>
  <div class="grid">
    <div class="card"><div class="step" aria-hidden="true">1</div><h3>Tell us once</h3><p>Your trade, the states you work in, and whether you are a small business, HUBZone, service-disabled veteran-owned, 8(a) or women-owned.</p></div>
    <div class="card"><div class="step" aria-hidden="true">2</div><h3>We check every notice</h3><p>Each morning we read the new federal contract notices on SAM.gov, find where the work really is and who may bid, and match them to your business.</p></div>
    <div class="card"><div class="step" aria-hidden="true">3</div><h3>One short email</h3><p>Around 6am Eastern you get only the bids you can use, each with the deadline, a plain-English next step and a link to the official notice.</p></div>
  </div>
</div></section>

<section id="sample" aria-labelledby="sample-h"><div class="wrap two">
  <div>
    <h2 id="sample-h">A real alert</h2>
    <p>This email was built from live SAM.gov notices on September 29, 2026, for a small cleaning company working in Massachusetts, Illinois and Kansas. Every bid, deadline and reference number in it is real.</p>
    <ul class="ticks">
      <li><strong>Real work site</strong>, not the contracting office in another state.</li>
      <li><strong>Who can bid</strong>: bids reserved for groups you are not in are left out.</li>
      <li><strong>No noise</strong>: award notices, duplicates and bids closing in under 2 days are removed.</li>
      <li><strong>Nothing on quiet days</strong>: no matches, no email.</li>
    </ul>
    <details><summary>Text version of this alert</summary>
      <p>4 janitorial and cleaning bids, all open for small businesses:</p>
      <ul>
        <li>Kansas FY27 Mass Solicitation, Custodial Services (Army), Lawrence, Kansas. Respond by Oct 2, 2026. Ref W912DQ27QA001.</li>
        <li>Housekeeping Services, Fermilab (Department of Energy), Illinois. Respond by Oct 9, 2026. Ref DH-377725.</li>
        <li>Janitorial Services at the FMH SSC (FAA), Falmouth, Massachusetts. Respond by Oct 20, 2026. Ref 697DCK-27-R-00004.</li>
        <li>Janitorial Services at the MVY ATCT (FAA), Massachusetts. Respond by Oct 22, 2026. Ref 697DCK-27-R-00001.</li>
      </ul>
    </details>
  </div>
  <picture><source srcset="/sample-alert.webp" type="image/webp"><img class="shot" src="/sample-alert.jpg" width="720" height="1051" loading="lazy" decoding="async" alt="A BidBell alert email listing four open federal janitorial bids in Kansas, Illinois and Massachusetts, each showing the work site, who can bid, the deadline and a link to the official notice."></picture>
</div></section>

<section id="what-you-get" aria-labelledby="get-h"><div class="wrap">
  <p class="eyebrow">What your $29 buys</p>
  <h2 id="get-h">Know what a job is worth before you bid</h2>
  <div class="grid">
    <div class="card"><h3>Only bids you can win</h3><p>Filtered by your trade, your states and your eligibility: small business, HUBZone, SDVOSB, 8(a), WOSB.</p></div>
    <div class="card"><h3>Who has the job now, and what they were paid</h3><p>From USAspending.gov, next to each bid: the likely current contractor, the contract total and roughly what it is worth per year.</p></div>
    <div class="card"><h3>Contracts ending soon</h3><p>Contracts in your states that end in the next 3 to 6 months, so you can prepare before the new bid is even posted.</p></div>
    <div class="card"><h3>Reminders</h3><p>A reminder 3 days before each deadline and site visit for the bids in your alerts.</p></div>
  </div>
  <h3 class="mt">Two real examples from bids open on September 29, 2026</h3>
  <div class="table-wrap"><table class="stack">
    <caption>Likely current contract for two open janitorial bids</caption>
    <thead><tr><th scope="col">Open bid</th><th scope="col">Likely current contractor</th><th scope="col">Contract total</th><th scope="col">Period</th><th scope="col">About per year</th></tr></thead>
    <tbody>
      <tr><td data-label="Open bid">Chattanooga National Cemetery janitorial (VA), respond by Oct 5, 2026</td><td data-label="Likely current contractor">KB Federal Maintenance Inc</td><td data-label="Contract total">$302,108</td><td data-label="Period">May 2021 &ndash; Apr 2026</td><td data-label="About per year">~$60,000</td></tr>
      <tr><td data-label="Open bid">FAA janitorial, Falmouth, Massachusetts, respond by Oct 20, 2026</td><td data-label="Likely current contractor">Eco-Friendly Cleaning Specialist LLC</td><td data-label="Contract total">$85,441</td><td data-label="Period">Apr 2023 &ndash; Dec 2026</td><td data-label="About per year">~$23,000</td></tr>
    </tbody></table></div>
  <p class="small muted">Source: {ext('https://www.usaspending.gov/search', 'USAspending.gov')} award records, checked September 29, 2026. &ldquo;Contract total&rdquo; is the amount the government committed (obligated) to the contract; companies are paid in instalments as they invoice for work done. Matches are labelled &ldquo;likely current contract&rdquo; and link to the official record.</p>
</div></section>

<section id="compare" aria-labelledby="compare-h"><div class="wrap">
  <h2 id="compare-h">Free pages or the daily alert</h2>
  <p class="muted">Our {'<a href="/cleaning-bids/">free cleaning-bid pages</a>'} list every open federal cleaning notice by state, once a week. The paid alert does the work for you.</p>
  <div class="table-wrap"><table class="stack">
    <caption>What each option includes</caption>
    <thead><tr><th scope="col">Feature</th><th scope="col">Free state pages</th><th scope="col">${fp} daily alert</th></tr></thead>
    <tbody>
      <tr><th scope="row">Open bids</th><td data-label="Free state pages">Title, work site, deadline; updated weekly</td><td data-label="${fp} daily alert" class="yes">Every morning, around 6am Eastern</td></tr>
      <tr><th scope="row">Filtered for your business</th><td data-label="Free state pages">No, everything in the state</td><td data-label="${fp} daily alert" class="yes">Your trade, states and eligibility</td></tr>
      <tr><th scope="row">Who has the job now and what they were paid</th><td data-label="Free state pages">No</td><td data-label="${fp} daily alert" class="yes">Yes, where a match is found</td></tr>
      <tr><th scope="row">Contracts ending in the next 3&ndash;6 months</th><td data-label="Free state pages">No</td><td data-label="${fp} daily alert" class="yes">Yes</td></tr>
      <tr><th scope="row">Deadline and site-visit reminders</th><td data-label="Free state pages">No</td><td data-label="${fp} daily alert" class="yes">Yes</td></tr>
    </tbody></table></div>
</div></section>

<section id="pricing" aria-labelledby="pricing-h"><div class="wrap">
  <h2 id="pricing-h">Simple pricing</h2>
  <div class="grid">
    <div class="card featured"><p class="badge">First {C['founding_spots']} customers</p><h3>Founding</h3><p class="price">${fp}<span>/month</span></p>
      <ul class="ticks"><li>Price locked for as long as you stay subscribed</li><li>One trade group, up to 10 states or nationwide</li><li>Everything in the daily alert</li><li>Cancel anytime</li></ul></div>
    <div class="card"><h3>Standard</h3><p class="price">${sp}<span>/month</span></p>
      <ul class="ticks"><li>Or ${ap} a year (2 months free)</li><li>Same service once founding places are taken</li><li>Cancel anytime</li></ul></div>
    <div class="card"><h3>Try it first</h3><p>Every plan starts with <strong>2 weeks free, no card needed</strong>. You pay only if the alerts are useful to you.</p>
      <div class="cta-row"><a class="btn" href="{E(start_url())}">Start free</a></div></div>
  </div>
  <p class="small muted">Prices in US dollars. Payments are handled by Lemon Squeezy, our merchant of record, which adds sales tax where it applies. See our <a href="/refunds/">refund policy</a>.</p>
</div></section>

<section id="data" aria-labelledby="data-h"><div class="wrap narrow">
  <h2 id="data-h">How we get our data</h2>
  <p><strong>Bids</strong> come from {ext('https://sam.gov/', 'SAM.gov')}, where federal agencies are required to publish contract opportunities. <strong>Past winners and amounts</strong> come from {ext('https://www.usaspending.gov/', 'USAspending.gov')}, the official public database of federal awards. Both are free, public sources run by the US government.</p>
  <p>What BidBell adds is the sorting: the real work site, who may bid, plain-English next steps, the likely current contractor and what the job is worth. Notices can change or be withdrawn after we send them, so always read the official notice before you bid. See our <a href="/disclaimer/">disclaimer</a>.</p>
</div></section>

<section id="about" aria-labelledby="about-h"><div class="wrap narrow">
  <h2 id="about-h">Who runs BidBell</h2>
  <p>BidBell is run by {E(C['owner_name'])}. Mailing address: {E(C['mailing_address'])}. Email: <a href="mailto:{C['email']}">{C['email']}</a>. We answer every email.</p>
</div></section>

<section id="faq" aria-labelledby="faq-h"><div class="wrap narrow">
  <h2 id="faq-h">Questions</h2>
  {faq_html}
</div></section>

<section aria-labelledby="final-h"><div class="wrap narrow">
  <h2 id="final-h">See your first alert tomorrow morning</h2>
  <p class="muted">Tell us your trade and states in 2 minutes. Your free 2 weeks start the next morning.</p>
  <div class="cta-row"><a class="btn" href="{E(start_url())}">Start 2 weeks free</a></div>
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
               'description': 'A daily email of US federal cleaning contract bids filtered by trade, state and eligibility, with the likely current contractor and contract amount.',
               'brand': {'@type': 'Brand', 'name': 'BidBell'},
               'offers': [offer('Founding (monthly)', fp, 'P1M'), offer('Standard (monthly)', sp, 'P1M'), offer('Standard (yearly)', ap, 'P1Y')]}
    faqld = {'@context': 'https://schema.org', '@type': 'FAQPage',
             'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in FAQ]}
    write('', layout('', 'BidBell | Government cleaning bids you can actually bid on',
                     'Every morning, BidBell emails US cleaning companies only the federal janitorial, carpet and window-cleaning bids in their states that they are allowed to bid on, with who holds each job now and what they were paid.',
                     body, [org, product, faqld]))


# ------------------------------------------------------------------ start (sign-up)
def start():
    if C['form_url']:
        action = f'<div class="cta-row"><a class="btn" href="{E(C["form_url"])}" rel="noopener noreferrer">Open the 2-minute sign-up form</a></div><p class="small muted">The form is hosted by Tally (tally.so), which stores responses in the EU and does not sell them. It uses a spam check (reCAPTCHA).</p>'
    else:
        body_txt = ('First name:%0D%0ABusiness name:%0D%0ABusiness website:%0D%0ATrades (janitorial / carpet / window-exterior):%0D%0A'
                    'States (up to 10, or all):%0D%0AEligibility (small business / HUBZone / SDVOSB / 8(a) / WOSB / none):%0D%0A'
                    'Registered in SAM.gov (yes / in progress / no):')
        action = f'<div class="cta-row"><a class="btn" href="mailto:{C["email"]}?subject=Free%202-week%20trial&amp;body={body_txt}">Email us to start your trial</a></div><p class="small muted">This opens an email with the questions filled in. Just answer and send.</p>'
    body = f'''<div class="wrap narrow legal">
<h1>Start your free 2 weeks</h1>
<p class="lead">Answer 6 short questions. Your first alert arrives the next morning. No card needed.</p>
{action}
<h2>What we ask</h2>
<ol>
  <li>Your first name and business email</li>
  <li>Your business name and website</li>
  <li>Your trades: janitorial, carpet cleaning, window or exterior cleaning</li>
  <li>Your states: up to 10, or nationwide</li>
  <li>Your eligibility: small business, HUBZone, service-disabled veteran-owned (SDVOSB), 8(a), women-owned (WOSB), or none</li>
  <li>Whether you are registered in SAM.gov: yes, in progress, or no</li>
</ol>
<p>We never ask for passwords, card numbers, tax IDs or any government ID numbers.</p>
<h2>What happens next</h2>
<ol>
  <li>We confirm your details by email within 1 business day.</li>
  <li>Your alerts start the next morning, around 6am Eastern, on days with matching bids.</li>
  <li>On day 12 we email you a summary of the bids you received and a secure checkout link (Lemon Squeezy). ${C['founding_price']}/month for our first {C['founding_spots']} customers.</li>
  <li>If you do not subscribe, your alerts simply stop after 14 days. Nothing is charged.</li>
</ol>
<p class="small muted">How we handle your details: <a href="/privacy/">privacy policy</a>.</p>
</div>'''
    write('start/', layout('start/', 'Start your free 2 weeks | BidBell',
                           'Start a free 2-week BidBell trial: daily federal cleaning bids for your trade, states and eligibility. No card needed.', body))


# ------------------------------------------------------------------ public bid pages (gamechanger 1)
def bid_pages():
    upd = date.fromisoformat(DATA['updated'])
    bids = [b for b in DATA['bids'] if b['due'] >= TODAY.isoformat()]   # drop notices whose deadline has passed
    by_state = {}
    for b in bids:
        by_state.setdefault(b['state'], []).append(b)
    teaser = (f'<p class="small muted">Last updated {long_date(upd)} from SAM.gov public data. This free page is updated weekly and shows every open notice, '
              f'unfiltered. It is not a substitute for reading the official notice.</p>')

    def other_states(skip=None):
        items = ''.join(f'<li><a href="/cleaning-bids/{slug(STATES[s])}/">{STATES[s]}</a> ({len(by_state[s])})</li>'
                        for s in sorted(by_state, key=lambda s: STATES.get(s, s)) if s != skip and s in STATES)
        return f'<ul class="state-list">{items}</ul>' if items else '<p class="muted">No other states have open notices this week.</p>'

    for code, name in STATES.items():
        sb = by_state.get(code, [])
        if sb:
            lst = bid_table(sb, f'{len(sb)} open federal cleaning notice{"s" if len(sb) != 1 else ""} in {name}')
        else:
            lst = f'<div class="note"><p>No open federal cleaning notices were listed for {name} in this week\'s data. New notices appear most weeks; subscribers hear about them the morning they are posted.</p></div>'
        body = f'''<div class="wrap page">
<p class="eyebrow"><a href="/cleaning-bids/">Cleaning bids</a> / {E(name)}</p>
<h1>Open federal cleaning bids in {E(name)}</h1>
<p class="lead">Janitorial, custodial, carpet and window-cleaning contract opportunities from federal agencies with work in {E(name)}.</p>
{teaser}
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
        body = f'''<div class="wrap page">
<p class="eyebrow"><a href="/cleaning-bids/">Cleaning bids</a> / {label}</p>
<h1>Open federal {words} bids</h1>
{teaser}
{lst}
<div class="mt">{cta_box()}</div>
</div>'''
        path = f'cleaning-bids/{trade}/'
        write(path, layout(path, f'Federal {words} bids | BidBell',
                           f'Open US federal {words} contract opportunities, updated weekly from SAM.gov. Last updated {long_date(upd)}.',
                           body, updated=upd), lastmod=upd)

    total = len(bids)
    body = f'''<div class="wrap page">
<h1>Open federal cleaning bids by state</h1>
<p class="lead">Every open federal janitorial, carpet and window-cleaning contract notice, grouped by where the work is. Free, updated weekly.</p>
{teaser}
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
    body = f'<div class="wrap narrow legal"><h1>{title}</h1><p class="updated">Last updated {long_date(upd)}</p>{inner}</div>'
    write(path, layout(path, f'{title} | BidBell', desc, body, updated=upd), lastmod=upd)


def legal():
    who = f'{E(C["owner_name"])}, trading as BidBell (&ldquo;BidBell&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;). Mailing address: {E(C["mailing_address"])}. Email: <a href="mailto:{C["email"]}">{C["email"]}</a>'
    fp, sp, ap = C['founding_price'], C['standard_price'], C['annual_price']

    legal_page('terms/', 'Terms of Service', 'The terms that apply when you use BidBell.', f'''
<p>These terms are an agreement between you (the business using BidBell, and the person accepting for it) and {who}. By starting a trial or subscription you accept them. Nothing in these terms takes away rights you have under a law that cannot be excluded by contract.</p>
<h2>1. What BidBell is</h2>
<p>BidBell is an email service. Each morning we read new US federal contract notices published on SAM.gov, select the ones that match the trades, states and eligibility you give us, and email them to you. Where we can, we add information from USAspending.gov about the likely current or previous contract for the same work. We also publish free public pages listing open federal cleaning notices by state. We are not a government service, a bidding agent, a law firm or a consultant.</p>
<h2>2. Free trial</h2>
<p>New customers get a free 2-week trial. We do not ask for a card to start it. If you do not subscribe, your alerts stop at the end of the trial and nothing is charged.</p>
<h2>3. Plans, payment and taxes</h2>
{lawyer('Merchant of record / payments', 'Terms 3: Lemon Squeezy as merchant of record, billing in advance, price-change notice, and the founding-price lock.')}
<p>Paid plans are ${fp}/month (Founding, for our first {C['founding_spots']} customers), ${sp}/month or ${ap}/year (Standard), billed in advance. Payments are processed by Lemon Squeezy, which acts as the merchant of record: it sells the subscription to you, charges your payment method, issues receipts and collects any sales tax. Lemon Squeezy's own terms apply to the payment. We never see or store your card details.</p>
<p>The Founding price stays the same for as long as your subscription stays active without a break. We may change other prices; we will email you at least 30 days before a change affects your next renewal, and you can cancel before it does.</p>
<h2>4. Cancelling and refunds</h2>
<p>You can cancel anytime from the link in your Lemon Squeezy receipt or by replying to any BidBell email. Your alerts continue until the end of the period you have paid for. Refunds follow our <a href="/refunds/">refund policy</a>.</p>
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
<p>{who}.</p>''')

    legal_page('privacy/', 'Privacy Policy', 'What BidBell collects, why, who processes it, how long we keep it and your rights.', f'''
<p>This policy explains how {who} handles personal information. We collect as little as we can, we do not sell it, and this website uses no tracking or advertising cookies.</p>
<h2>1. What we collect</h2>
<ul>
<li><strong>Trial and subscriber details</strong> you give us: first name, business email, business name and website, trades, states, eligibility (small business, HUBZone, SDVOSB, 8(a), WOSB) and whether you are registered in SAM.gov.</li>
<li><strong>Payment information</strong> from Lemon Squeezy: your name, email, country, plan, amounts and subscription status. We never receive your card details.</li>
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
<li><strong>Google Workspace</strong> (Google LLC): our email.</li>
<li><strong>GitHub</strong> (GitHub, Inc.): runs the program that sends alerts and hosts this website. GitHub may log visitor IP addresses for security; see GitHub's privacy statement.</li>
<li><strong>Lemon Squeezy</strong>: payments, as merchant of record.</li>
<li><strong>Tally</strong> (Tally BV, Belgium): our sign-up form, when used. Tally stores responses in the EU.</li>
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
<p><strong>California and other US states:</strong> you have the right to know, access, correct and delete your personal information, and not to be discriminated against for using these rights. We do not sell or share personal information for cross-context behavioural advertising, and we do not use it for profiling.</p>
<p><strong>European Union and United Kingdom:</strong> you also have the rights to object, to restrict processing and to data portability, and you may complain to your local data protection authority.</p>
<h2>6. Cookies and tracking</h2>
<p>This website sets no cookies and uses no analytics, advertising pixels or third-party scripts. Our emails contain no tracking pixels.</p>
<h2>7. Security</h2>
<p>We use providers with strong security, two-step verification on every account, and we keep customer data out of this public website. No system is perfectly secure; if a breach affects you, we will tell you as the law requires.</p>
<h2>8. Children</h2>
<p>BidBell is a business service and is not meant for anyone under 18.</p>
<h2>9. Changes</h2>
<p>We will post changes here and email subscribers about material changes before they take effect.</p>''')

    legal_page('refunds/', 'Refund Policy', 'BidBell refund and cancellation policy.', f'''
<p>Every plan starts with a free 2-week trial, so you can judge the alerts before paying.</p>
<h2>Monthly plans</h2>
<p>If you are not satisfied, email <a href="mailto:{C["email"]}">{C["email"]}</a> within 7 days of a payment and we will refund that payment in full.</p>
<h2>Yearly plan</h2>
<p>Full refund within 14 days of payment. After that, we refund the unused whole months.</p>
<h2>Cancelling</h2>
<p>Cancel anytime from the link in your Lemon Squeezy receipt, or reply to any BidBell email. Your alerts continue until the end of the period you paid for, and you will not be charged again.</p>
<h2>How refunds are paid</h2>
<p>Refunds are made by Lemon Squeezy to your original payment method. Your bank may take 5 to 10 business days to show it.</p>''')

    legal_page('acceptable-use/', 'Acceptable Use Policy', 'How BidBell alerts and pages may be used.', f'''
{lawyer('Acceptable use', 'Acceptable use: resale ban, one-business-per-subscription rule, and enforcement.')}
<p>BidBell alerts are for the internal use of the business that subscribes. You agree not to:</p>
<ul>
<li>resell, republish, forward in bulk or share our paid alerts or their contents with other businesses;</li>
<li>share one subscription between separate businesses;</li>
<li>copy our paid content into another product or service;</li>
<li>use BidBell for anything unlawful, including misrepresenting your eligibility for a set-aside;</li>
<li>try to break, overload, scan or gain unauthorised access to our website or systems.</li>
</ul>
<p>Our free public pages are built from public data; you may link to them. If you break this policy we may suspend or end your subscription under our <a href="/terms/">terms</a>.</p>''')

    legal_page('disclaimer/', 'Disclaimer', 'Important limits of BidBell information.', f'''
{lawyer('Disclaimer', 'Disclaimer page as a whole: data-accuracy, no-affiliation and no-advice statements.')}
<h2>Not a government service</h2>
<p>BidBell is a private service. It is not affiliated with, endorsed by or connected to SAM.gov, the General Services Administration, USAspending.gov or any government agency.</p>
<h2>Data can change</h2>
<p>We use public government data. Notices can be incomplete, published late, amended or withdrawn after we send them, and deadlines are set in each notice's own time zone. Always read the full official notice and its attachments on SAM.gov before relying on anything we send.</p>
<h2>Matches are estimates</h2>
<p>Work sites, eligibility, and especially the &ldquo;likely current contract&rdquo; and amounts are our best match from public records. They can be wrong or missing. Contract totals are the amounts the government committed (obligated) and can include option years or later changes.</p>
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
          '<div class="wrap narrow legal"><h1>Page not found</h1><p>This page does not exist or has moved.</p>'
          '<div class="cta-row"><a class="btn" href="/">Go to the home page</a><a class="btn ghost" href="/cleaning-bids/">Cleaning bids by state</a></div></div>',
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
    open(os.path.join(ROOT, 'favicon.svg'), 'w').write(
        BELL.replace('aria-hidden="true" focusable="false"', 'xmlns="http://www.w3.org/2000/svg"').replace('currentColor', '#9A3F12'))


def main():
    home(); start(); bid_pages(); legal(); extras()
    open(os.path.join(T, 'LAWYER_REVIEW.md'), 'w').write(
        '# Clauses for a lawyer to review\n\n' + ''.join(f'{i}. {t}\n' for i, t in enumerate(LAWYER, 1)))
    print(f'built {len(PAGES)} pages + 404, sitemap, robots, security.txt; {len(LAWYER)} lawyer-review items')


if __name__ == '__main__':
    main()

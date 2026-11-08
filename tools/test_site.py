"""Public-site release checks. No signup or payment requests are made."""
import json,re,unittest
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Page(HTMLParser):
 def __init__(self,text):
  super().__init__();self.ids=[];self.links=[];self.inputs=[];self.forms=[];self.feed(text)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if a.get('id'):self.ids.append(a['id'])
  if tag=='a' and a.get('href'):self.links.append(a['href'])
  if tag=='input':self.inputs.append(a)
  if tag=='form':self.forms.append(a)
class Site(unittest.TestCase):
 def test_public_positioning_separates_workspace_from_alert_coverage(self):
  home=(ROOT/'index.html').read_text(encoding='utf-8')
  start=(ROOT/'start/index.html').read_text(encoding='utf-8')
  self.assertIn('<title>BidBell | Less paperwork. Stronger bids.</title>',home)
  self.assertIn('<h1>Less paperwork.',home)
  self.assertNotIn('THE CLEANING BID WORKSPACE',home)
  self.assertIn('Choose cleaning or construction, then select your trade and service area.',home)
  self.assertIn('<h1>Your next opportunity.',start)
  self.assertIn('Look for the Google Forms confirmation',start)
  self.assertIn('Available daily alerts: janitorial, carpet, window and exterior cleaning.',re.sub(r'<[^>]+>','',start))
 def test_home_routes_and_legacy_anchors(self):
  page=Page((ROOT/'index.html').read_text(encoding='utf-8'))
  self.assertEqual(len(page.ids),len(set(page.ids)))
  for anchor in ['features','how','sample','pricing','faq','preferences']:self.assertIn(anchor,page.ids)
  for url in page.links:
   if url.startswith('#'):self.assertIn(url[1:],page.ids,url)
   elif url.startswith('/'):
    path=ROOT/url.split('#')[0].lstrip('/')
    if url.split('#')[0].endswith('/'):path=path/'index.html'
    self.assertTrue(path.is_file(),url)
 def test_original_signup_field_contract(self):
  cfg=json.loads((ROOT/'tools/site.json').read_text(encoding='utf-8'))
  page=Page((ROOT/'start/index.html').read_text(encoding='utf-8'))
  self.assertEqual(page.forms[0]['action'],cfg['form_post'])
  self.assertEqual({i['name'] for i in page.inputs if i.get('name')},set(cfg['form_entries'].values()))
  self.assertIn('Nationwide (all states)',[i.get('value') for i in page.inputs])
 def test_one_subscription_and_original_trial_dates(self):
  text=(ROOT/'index.html').read_text(encoding='utf-8')
  self.assertIn('https://bidbell-workspace.onrender.com/app',text)
  self.assertIn('14 days free',text)
  self.assertIn('No second preparation subscription',text)
  self.assertIn('$39',text)
  self.assertIn('Existing trials keep their original end date',text)
  self.assertIn('same email',text)
  self.assertNotIn('Separate from the preparation workspace',text)
  self.assertIn("does not sign declarations or automatically apply everywhere",text)
  self.assertIn("original buyer instructions explicitly specify the submission recipients",text)
  self.assertIn("Mail-server acceptance does not prove buyer receipt",text)
  self.assertIn("uncertain delivery is not automatically retried",text)
  for forbidden in ['guaranteed wins','AI-assisted features are not enabled','100% accurate']:
   self.assertNotIn(forbidden,text)
 def test_marketing_assets_are_self_hosted(self):
  text=(ROOT/'home.js').read_text(encoding='utf-8')
  self.assertIn('/three.module.min.js',text)
  self.assertTrue((ROOT/'three.module.min.js').is_file())
  self.assertIn('prefers-reduced-motion',text)
 def test_public_purchase_entry_requires_the_verified_account_flow(self):
  text=(ROOT/'subscribe/index.html').read_text(encoding='utf-8')
  self.assertIn('https://bidbell-workspace.onrender.com/app#account',text)
  self.assertIn('Set up your alert preferences',text)
  self.assertIn('Existing annual plans keep their current terms',text)
  self.assertNotIn('data-checkout=',text)
  self.assertIn('cdn.paddle.com/paddle/v2/paddle.js',text)
 def test_rendered_copy_no_em_dash(self):
  pages=[p for p in ROOT.rglob('*.html') if 'desk' not in p.parts]
  self.assertGreaterEqual(len(pages),63)
  for page in pages:self.assertNotIn(chr(0x2014),page.read_text(encoding='utf-8'),str(page))
 def test_signup_explains_the_complete_shared_trial(self):
  text=(ROOT/'start/index.html').read_text(encoding='utf-8')
  for phrase in ['Open the bid in BidBell','Reuse what your company knows','Review and send your bid','One trial. One US$39/month plan.','same email','original trial dates']:
   self.assertIn(phrase,text)
  for old in ['keep your alerts:','$390/year','One signup, two useful steps']:
   self.assertNotIn(old,text)
 def test_every_current_public_page_uses_the_shared_identity(self):
  for page in ROOT.rglob('*.html'):
   if 'desk' in page.parts:continue
   self.assertIn('/brand.css?v=20261101-one-product',page.read_text(encoding='utf-8'),str(page))
  self.assertTrue((ROOT/'brand-icon.png').is_file())
if __name__=='__main__':unittest.main()

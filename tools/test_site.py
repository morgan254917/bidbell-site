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
 def test_preparation_and_alerts_are_distinct(self):
  text=(ROOT/'index.html').read_text(encoding='utf-8')
  self.assertIn('https://bidbell-workspace.onrender.com/app',text)
  self.assertIn('14-day free trial',text)
  self.assertIn('No payment is currently collected for BidBell Prepare',text)
  self.assertIn('$39',text)
  self.assertIn('$390',text)
  self.assertIn('Separate from the preparation workspace',text)
  self.assertIn('does not sign certifications or submit applications',text)
  for forbidden in ['guaranteed wins','AI-assisted features are not enabled','100% accurate']:
   self.assertNotIn(forbidden,text)
 def test_marketing_assets_are_self_hosted(self):
  text=(ROOT/'home.js').read_text(encoding='utf-8')
  self.assertIn('/three.module.min.js',text)
  self.assertTrue((ROOT/'three.module.min.js').is_file())
  self.assertIn('prefers-reduced-motion',text)
 def test_rendered_copy_no_em_dash(self):
  pages=[p for p in ROOT.rglob('*.html') if 'desk' not in p.parts]
  self.assertGreaterEqual(len(pages),63)
  for page in pages:self.assertNotIn(chr(0x2014),page.read_text(encoding='utf-8'),str(page))
if __name__=='__main__':unittest.main()

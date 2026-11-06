import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from prepare_static import stage_public_assets

class ExpansionPreview(unittest.TestCase):
 def test_staged_customer_actions_never_post_or_checkout_on_production(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   original='''<!doctype html><html><head><title>BidBell</title><script src="https://cdn.paddle.com/paddle/v2/paddle.js"></script></head><body><a href="https://bidbell-workspace.onrender.com/app#account">Account</a><a href="/start/">Start</a><form action="https://docs.google.com/forms/d/e/example/formResponse"><button>Submit</button></form></body></html>'''
   (root/'index.html').write_text(original)
   with patch.dict(os.environ,{'BIDBELL_STAGING':'1'}):stage_public_assets('fictional','2026-11-06',root=root)
   page=(root/'_site/index.html').read_text()
   self.assertNotIn('https://docs.google.com/forms/',page)
   self.assertNotIn('https://cdn.paddle.com',page)
   self.assertIn('http://127.0.0.1:8860/app#account',page)
   self.assertIn('Staging preview',page)
   self.assertIn('noindex',page)
   self.assertEqual((root/'index.html').read_text(),original)
 def test_normal_build_keeps_the_production_destinations(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory); original='<html><body><a href="https://bidbell-workspace.onrender.com/app">Open</a></body></html>'
   (root/'index.html').write_text(original)
   with patch.dict(os.environ,{'BIDBELL_STAGING':'0'}):stage_public_assets('fictional','2026-11-06',root=root)
   self.assertEqual((root/'_site/index.html').read_text(),original)

class ConstructionPage(unittest.TestCase):
 def test_industry_navigation_identifies_current_page_accessibly(self):
  from build import layout
  page=layout('construction-bids/','Construction','Preview','<p>Fictional staging content</p>')
  self.assertIn('<a href="/construction-bids/" aria-current="page">Construction</a>',page)
 def test_display_deadline_retains_offset_and_date_precision(self):
  from build import construction_deadline
  self.assertEqual(construction_deadline({'due_at':'2026-11-18T14:00:00-06:00','due_precision':'time'}),'Nov 18, 2026 at 14:00 (UTC-06:00)')
  self.assertEqual(construction_deadline({'due':'2026-11-18','due_precision':'date'}),'Nov 18, 2026 (time not provided)')
 def test_all_caps_title_is_readable_but_preserves_trade_acronym(self):
  from build import construction_title
  self.assertEqual(construction_title('HVAC REPLACEMENT AT THE LIBRARY'),'HVAC Replacement at the Library')
 def test_construction_page_connects_to_the_same_application(self):
  root=Path(__file__).resolve().parents[1]
  self.assertTrue((root/'construction-bids/index.html').is_file(),'Construction entry page is missing')
  page=(root/'construction-bids/index.html').read_text(encoding='utf-8')
  self.assertIn('Construction &amp; building trades',page)
  self.assertIn('same BidBell workspace',page)
  self.assertIn('source',page.lower())

if __name__=='__main__':unittest.main()

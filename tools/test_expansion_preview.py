import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from prepare_static import stage_public_assets

class ExpansionPreview(unittest.TestCase):
 def test_preview_flag_never_changes_canonical_source_builder_contract(self):
  from build import coverage_block
  with patch.dict(os.environ,{'BIDBELL_STAGING':'1'}):
   self.assertIn('Coverage being validated:',coverage_block())
 def test_full_preview_build_runs_contract_checks_without_preview_environment(self):
  import prepare_static
  with patch.dict(os.environ,{'BIDBELL_STAGING':'1'}),patch.object(prepare_static.subprocess,'run') as run,patch.object(prepare_static.subprocess,'check_output',return_value='fictional'),patch.object(prepare_static,'stage_public_assets') as stage:
   prepare_static.main()
   for call in run.call_args_list:self.assertEqual(call.kwargs['env']['BIDBELL_STAGING'],'0')
   stage.assert_called_once()
 def test_expanded_release_uses_native_account_without_review_destinations(self):
  from prepare_static import expansion_html
  page=expansion_html('<html><head></head><body><form action="https://docs.google.com/forms/d/e/example/formResponse"><button>Submit</button></form><p>Set up your alert preferences</p><p>then create and verify your workspace account with the same email.</p></body></html>')
  self.assertNotIn('docs.google.com/forms',page)
  self.assertIn('https://bidbell-workspace.onrender.com/app?industry=construction#register',page)
  self.assertIn('https://bidbell-workspace.onrender.com/app?industry=cleaning#register',page)
  self.assertNotIn('127.0.0.1',page)
  self.assertNotIn('Staging preview',page)
  self.assertNotIn('noindex',page)
 def test_expansion_release_is_opt_in_and_only_changes_output(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);original='<html><head></head><body><form action="https://docs.google.com/forms/d/e/example/formResponse"></form></body></html>'
   (root/'index.html').write_text(original)
   with patch.dict(os.environ,{'BIDBELL_STAGING':'0','BIDBELL_CONSTRUCTION_ENABLED':'1'}):stage_public_assets('fictional','2026-11-06',root=root)
   self.assertNotIn('docs.google.com/forms',(root/'_site/index.html').read_text())
   self.assertEqual((root/'index.html').read_text(),original)
   self.assertTrue((root/'_site/expansion.css').is_file())
 def test_expanded_terms_do_not_promise_cleaning_only_forecasts_for_construction(self):
  from prepare_static import expansion_html
  terms=(Path(__file__).resolve().parents[1]/'terms/index.html').read_text(encoding='utf-8')
  page=expansion_html(terms)
  self.assertIn('supported public procurement sources',page)
  self.assertIn('Cleaning contract forecasts',page)
  self.assertNotIn('on Mondays, federal contracts in your states',page)
  self.assertNotIn('limited to janitorial',page)
 def test_expanded_privacy_and_disclaimer_name_native_enrollment_and_original_sources(self):
  from prepare_static import expansion_html
  root=Path(__file__).resolve().parents[1]
  privacy=expansion_html((root/'privacy/index.html').read_text(encoding='utf-8'))
  disclaimer=expansion_html((root/'disclaimer/index.html').read_text(encoding='utf-8'))
  self.assertIn('New account and alert preferences',privacy)
  self.assertNotIn('our sign-up form (Google Forms)',privacy)
  self.assertIn('original buyer notice and its attachments',disclaimer)
  self.assertNotIn('attachments on SAM.gov before relying',disclaimer)
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
 def test_date_only_deadline_stops_at_earliest_possible_close(self):
  from datetime import datetime,timezone
  from build import construction_is_open
  bid={'due':'2026-11-10','due_at':'2026-11-10T00:00:00+00:00','due_precision':'date'}
  self.assertTrue(construction_is_open(bid,datetime(2026,11,9,9,59,tzinfo=timezone.utc)))
  self.assertFalse(construction_is_open(bid,datetime(2026,11,9,10,tzinfo=timezone.utc)))
 def test_exact_deadline_uses_its_original_time_zone(self):
  from datetime import datetime,timezone
  from build import construction_is_open
  bid={'due_at':'2026-11-10T14:00:00-06:00','due_precision':'time'}
  self.assertTrue(construction_is_open(bid,datetime(2026,11,10,19,59,tzinfo=timezone.utc)))
  self.assertFalse(construction_is_open(bid,datetime(2026,11,10,20,tzinfo=timezone.utc)))
  self.assertFalse(construction_is_open({'due_at':'2026-11-10T14:00:00'},datetime(2026,11,9,tzinfo=timezone.utc)))
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

"""Accurate customer-facing pricing descriptions, separate from calculator math."""
import unittest
from pathlib import Path
from prepare_static import expansion_html

ROOT = Path(__file__).resolve().parents[1]

class CommercialCopy(unittest.TestCase):
    def test_home_explains_both_customer_input_workflows(self):
        text = (ROOT/'index.html').read_text(encoding='utf-8')
        for phrase in ('task-based estimates','quantities and unit prices','Your measurements and rates',
                       'private templates','proposed work schedule'):
            self.assertIn(phrase, text)
        self.assertNotIn('automatic drawing takeoff', text)
        self.assertIn('US$39/month', text)

    def test_industry_pages_explain_the_relevant_pricing_tools(self):
        cleaning = (ROOT/'cleaning-bids/index.html').read_text(encoding='utf-8')
        construction = (ROOT/'construction-bids/index.html').read_text(encoding='utf-8')
        for phrase in ('your measured areas','productivity','gross margin','proposed work schedule'):
            self.assertIn(phrase, cleaning)
        for phrase in ('quantities and unit prices','allowances','alternates','private templates'):
            self.assertIn(phrase, construction)

    def test_expanded_signup_keeps_pricing_and_submission_customer_controlled(self):
        text = expansion_html((ROOT/'start/index.html').read_text(encoding='utf-8'))
        self.assertIn('Build an estimate or quote from your inputs', text)
        self.assertIn('approve the exact package'.lower(), text.lower())

if __name__ == '__main__':
    unittest.main()

"""Federal solicitations and early market signals must remain distinct."""
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
import build

NOW = datetime(2026, 11, 7, 12, tzinfo=timezone.utc)

def notice(kind, title):
    return {'type':kind,'title':title,'trade':'janitorial','state':'TX','city':'Austin',
            'agency':'Fictional public buyer','due':'2026-12-01','due_at':'2026-12-01T18:00:00Z',
            'due_precision':'time','link':'https://sam.gov/opp/fictional/view','sol':title,'set_aside':''}

class PublicNoticeStages(unittest.TestCase):
    def test_only_solicitations_are_open_bids(self):
        rows = [notice('Solicitation','Open scope'), notice('Combined Synopsis/Solicitation','Open combined'),
                notice('Sources Sought','Supplier research'), notice('Presolicitation','Planned work'),
                notice('Award Notice','Already awarded'), notice('Unknown','Unknown type')]
        groups = build.federal_notice_groups(rows, NOW)
        self.assertEqual({x['title'] for x in groups['bids']}, {'Open scope','Open combined'})
        self.assertEqual({x['title'] for x in groups['early_signals']}, {'Supplier research','Planned work'})

    def test_exact_and_unknown_deadlines_never_stay_falsely_open(self):
        exact = dict(notice('Solicitation','Closed today'), due_at='2026-11-07T06:00:00-05:00')
        date_only = dict(notice('Sources Sought','Date-only research'), due='2026-11-08',
                         due_at='2026-11-08T00:00:00Z', due_precision='date')
        unknown = dict(notice('Solicitation','Unknown deadline'), due_at='not-a-date')
        groups = build.federal_notice_groups([exact,date_only,unknown], NOW)
        self.assertEqual(groups, {'bids':[], 'early_signals':[]})

    def test_state_and_trade_pages_keep_early_signals_separate(self):
        pages = {}
        data = {'updated':'2026-11-07','bids':[notice('Solicitation','Ready to quote'),
                notice('Sources Sought','Supplier capability research')]}
        def save(path, text, **kwargs): pages[path] = text
        with patch.object(build,'DATA',data), patch.object(build,'write',side_effect=save):
            build.bid_pages(now=NOW)
        for route in ('cleaning-bids/', 'cleaning-bids/texas/'):
            text = pages[route]
            self.assertIn('Early signals', text)
            self.assertIn('not open bid invitations', text)
            self.assertGreater(text.index('Supplier capability research'), text.index('Early signals'))
        self.assertIn('1 open federal cleaning solicitation', pages['cleaning-bids/texas/'])
        self.assertIn('<strong>1</strong> open solicitation', pages['cleaning-bids/'])

if __name__ == '__main__': unittest.main()

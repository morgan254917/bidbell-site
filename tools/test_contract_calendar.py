"""Public forecast boundaries: no customer data and no invented open bids."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from update_contract_calendar import collect, publish_snapshot, sanitize_snapshot

NOW = datetime(2026,11,2,8,tzinfo=timezone.utc)

def award(**changes):
    row={'Award ID':'CLEAN-1','Recipient Name':'Public contractor LLC','Start Date':'2025-01-01',
         'End Date':'2027-04-01','Award Amount':25000,'Description':'JANITORIAL SERVICES',
         'Awarding Agency':'Test public agency','Awarding Sub Agency':'Test public office',
         'Primary Place of Performance':{'city_name':'Austin','state_code':'TX'},
         'NAICS':{'code':'561720'},'PSC':{'code':'S201'},'generated_internal_id':'CONT_AWD_CLEAN1_TEST'}
    row.update(changes)
    return row

class ContractCalendar(unittest.TestCase):
    def test_complete_api_pages_produce_forecast_not_opportunities(self):
        pages=[{'results':[award()],'page_metadata':{'hasNext':True}},
               {'results':[award(**{'Award ID':'CLEAN-2','generated_internal_id':'CONT_AWD_CLEAN2_TEST'})],
                'page_metadata':{'hasNext':False}}]
        def post(body): return pages[body['page']-1]
        feed=collect(post=post,now=NOW)
        self.assertEqual(feed.get('kind'),'contract_endings_forecast')
        self.assertEqual(feed.get('complete'),True)
        self.assertEqual(len(feed.get('contracts',[])),2)
        self.assertEqual(feed.get('pages_read'),2)
        self.assertNotIn('bids',feed)
        self.assertIn('not open solicitations',feed.get('scope',''))

    def test_page_limit_cannot_publish_partial_search_as_complete(self):
        with self.assertRaisesRegex(ValueError,'page limit'):
            collect(post=lambda body:{'results':[award()],'page_metadata':{'hasNext':True}},now=NOW,max_pages=1)

    def test_malformed_response_and_repeated_page_fail_closed(self):
        for response in ({}, {'results':[]}, {'results':'not rows','page_metadata':{'hasNext':False}}):
            with self.subTest(response=response),self.assertRaises(ValueError):
                collect(post=lambda body:response,now=NOW)
        with self.assertRaisesRegex(ValueError,'repeated'):
            collect(post=lambda body:{'results':[award()],'page_metadata':{'hasNext':True}},now=NOW)

    def test_repeated_last_page_is_not_mistaken_for_complete_search(self):
        with self.assertRaisesRegex(ValueError,'repeated'):
            collect(post=lambda body:{'results':[award()],'page_metadata':{'hasNext':body['page']==1}},now=NOW)

    def test_unexpected_empty_refresh_keeps_previous_public_feed(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'contract-calendar.json';path.write_text('last good')
            with self.assertRaises(ValueError):
                publish_snapshot(collect(post=lambda body:{'results':[],'page_metadata':{'hasNext':False}},now=NOW),path)
            self.assertEqual(path.read_text(),'last good')

    def test_expired_unrelated_mandatory_source_and_unknown_locations_are_excluded(self):
        records=[award(),award(**{'End Date':'2026-11-01'}),award(**{'NAICS':{'code':'561730'}}),
                 award(**{'Description':'ABILITYONE JANITORIAL SERVICES'}),
                 award(**{'Primary Place of Performance':{'city_name':'Unknown','state_code':''}})]
        feed=collect(post=lambda body:{'results':records,'page_metadata':{'hasNext':False}},now=NOW)
        self.assertEqual(len(feed.get('contracts',[])),1)

    def test_legacy_snapshot_keeps_real_timestamp_and_only_public_allowlisted_fields(self):
        old={'built':'2026-11-01','at':'2026-11-01T13:22:47+00:00','contracts':[
            {'award_id':'CLEAN1','contractor':'Public contractor LLC','description':'Janitorial services',
             'agency':'Test agency','state':'TX','city':'Austin','naics':'561720','start':'2025-01-01',
             'end':'2027-04-01','amount':25000,'link':'https://www.usaspending.gov/award/CONT_AWD_CLEAN1_TEST',
             'customer_email':'private@example.test','source_documents':['never publish']} ]}
        feed=sanitize_snapshot(old,now=NOW)
        self.assertEqual(feed.get('updated'),'2026-11-01T13:22:47+00:00')
        self.assertEqual(feed.get('complete'),False)
        self.assertEqual(feed.get('coverage_status'),'legacy_snapshot_not_exhaustively_verified')
        self.assertEqual(len(feed.get('contracts',[])),1)
        self.assertNotIn('private@example.test',json.dumps(feed))
        self.assertNotIn('source_documents',json.dumps(feed))

    def test_bad_award_links_and_future_snapshot_are_rejected(self):
        source={'at':'2026-11-01T13:22:47+00:00','contracts':[{'award_id':'A','description':'Cleaning',
                'state':'TX','naics':'561720','end':'2027-01-01','amount':2500,
                'link':'https://evil.example/award/A'}]}
        self.assertEqual(sanitize_snapshot(source,now=NOW).get('contracts'),[])
        source['at']='2026-11-04T00:00:00+00:00'
        with self.assertRaises(ValueError):sanitize_snapshot(source,now=NOW)

    def test_failed_or_oversized_refresh_preserves_last_good_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'contract-calendar.json';path.write_text('last good')
            with self.assertRaises(ValueError):publish_snapshot({'contracts':[{'text':'x'*200}]},path,max_bytes=100)
            self.assertEqual(path.read_text(),'last good')
            with self.assertRaises(ValueError):
                publish_snapshot(collect(post=lambda body:{},now=NOW),path)
            self.assertEqual(path.read_text(),'last good')

    def test_valid_public_file_is_atomic_and_within_cap(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'contract-calendar.json'
            feed=collect(post=lambda body:{'results':[award()],'page_metadata':{'hasNext':False}},now=NOW)
            publish_snapshot(feed,path)
            self.assertTrue(path.is_file())
            self.assertEqual(json.loads(path.read_text()),feed)
            self.assertEqual([p.name for p in Path(folder).iterdir()],['contract-calendar.json'])

if __name__=='__main__':unittest.main()

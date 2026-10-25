import csv,io,json,runpy,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
M=runpy.run_path(str(Path(__file__).with_name('update_bids.py')),run_name='test_import')
NOW=datetime(2026,10,25,12,tzinfo=timezone.utc)
def row(**kw):
 r={'NaicsCode':'561720','Type':'Solicitation','ResponseDeadLine':'2026-11-10T12:00:00Z','PopState':'TX','Sol#':'CLEAN1','PostedDate':'2026-10-24T10:00:00Z','Department/Ind.Agency':'Test','NoticeId':'id1','Title':'Janitorial services','Active':'Yes','PopCountry':'USA'};r.update(kw);return r
def collect(rows):
 out=io.StringIO();w=csv.DictWriter(out,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows);return M['collect'](out.getvalue(),NOW,1)
class PublicSources(unittest.TestCase):
 def test_newer_reclassified_award_suppresses_old_cleaning(self):
  old=row(**{'Sol#':'OLD'});new=row(**{'Sol#':'OLD','NaicsCode':'238220','Type':'Award Notice','PostedDate':'2026-10-25T10:00:00Z','ResponseDeadLine':''})
  for rows in [[old,new,row()],[new,old,row()]]:self.assertEqual([b['sol'] for b in collect(rows)[0]['bids']],['CLEAN1'])
 def test_cancel_and_expired_amendment_do_not_resurrect(self):
  for changes in [{'Title':'Cancelled janitorial services'},{'ResponseDeadLine':'2020-01-01'}]:
   old=row(**{'Sol#':'OLD'});new=row(**{'Sol#':'OLD','PostedDate':'2026-10-25T10:00:00Z',**changes});self.assertEqual(len(collect([row(),old,new])[1]['bids']),1)
 def test_timezone_fractional_and_no_invalid_date_truncation(self):
  self.assertEqual(M['parse_dt']('2026-10-25T08:00:00.500-04:00').hour,12)
  self.assertIsNone(M['parse_dt']('2026-10-25T99:00:00Z'))
 def test_categories_conservative(self):
  rows=[row(),row(**{'Sol#':'G','NaicsCode':'561730','Title':'Grounds maintenance'}),row(**{'Sol#':'H','NaicsCode':'238220','Title':'HVAC preventive maintenance'})]
  self.assertEqual({b['category'] for b in collect(rows)[1]['bids']},{'cleaning','grounds','hvac'})
  for title in ['Plumbing repair','HVAC replacement and maintenance','HVAC equipment purchase','HVAC installation','New HVAC construction services']:
   self.assertIsNone(M['category'](row(NaicsCode='238220',Title=title)),title)
 def test_invalid_or_empty_cleaning_does_not_write(self):
  with self.assertRaises(ValueError):collect([row(NaicsCode='561730')])
  with self.assertRaises(ValueError):M['collect']('broken',NOW,1)
 def test_atomic_files_valid_and_no_staging_left(self):
  cleaning,services,_=collect([row()])
  with tempfile.TemporaryDirectory() as directory:
   M['write_outputs'](cleaning,services,directory)
   self.assertEqual(json.loads((Path(directory)/'cleaning_bids.json').read_text()),cleaning)
   self.assertEqual(json.loads((Path(directory)/'service_bids.json').read_text()),services)
   self.assertEqual(len(list(Path(directory).iterdir())),2)
 def test_closed_tie_and_agency_scope(self):
  old=row(**{'Sol#':'OLD'});closed=row(**{'Sol#':'OLD','Type':'Award Notice'})
  self.assertEqual(len(collect([row(),closed,old])[1]['bids']),1)
  other=row(**{'Department/Ind.Agency':'Different'})
  self.assertEqual(len(collect([row(),other])[1]['bids']),2)
if __name__=='__main__':unittest.main()

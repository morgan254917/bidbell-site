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
 def test_cleaning_scope_rejects_hardware_and_supplies_but_keeps_explicit_cleaning(self):
  excluded=['Eddyville Quarters Window Replacement','MT BFTC Carpet Replacement Conference Room',
            'Bureau of Building Broom Hall Windows & Doors Delta State University',
            'Window Tinting and Film','Carpet Installation','Janitorial Supplies',
            'Cleaning Equipment Purchase','Purchase of Cleaning Equipment','Windows and Doors, Washington',
            'Snow and Ice Removal Services - Brockton, MA','Snow plowing services',
            'Cleaning Equipment Procurement Services']
  accepted=['Window Cleaning Services','Carpet Cleaning','Floor Care','Custodial Services',
            'Curtain Cleaning and Installation','Post-construction cleaning','Janitorial Services and Supplies']
  for code in ['561720','561740','561790']:
   for title in excluded+accepted:
    with self.subTest(code=code,title=title):
     self.assertEqual(M['category'](row(NaicsCode=code,Title=title)) is not None,title in accepted)
  rows=[row(**{'Sol#':str(i),'Title':title}) for i,title in enumerate(excluded+accepted)]
  self.assertEqual({b['title'] for b in collect(rows)[0]['bids']},set(accepted))
 def test_explicit_foreign_base_is_not_relocated_to_domestic_office_state(self):
  control=row(Description='',PopCity='Austin')
  foreign=row(**{'Sol#':'FOREIGN','Title':'Custodial Services at Aviano Air Base, Italy',
                 'PopState':'FL','PopCountry':'USA','PopCity':'Aviano','Description':''})
  domestic=row(**{'Sol#':'DOMESTIC','Title':'Custodial Services in Miami, FL',
                  'PopState':'FL','PopCity':'Miami',
                  'Description':'Contact our office in Italy. Supplies may be manufactured in Germany.'})
  self.assertTrue(M['foreign_performance'](foreign))
  self.assertFalse(M['foreign_performance'](domestic))
  self.assertTrue(M['foreign_performance'](row(PopCountry='ITA')))
  cleaning,services,_=collect([control,foreign,domestic])
  for payload in [cleaning,services]:
   self.assertNotIn('FOREIGN',{b['sol'] for b in payload['bids']})
   self.assertEqual(next(b['state'] for b in payload['bids'] if b['sol']=='DOMESTIC'),'FL')
 def test_newer_reclassified_award_suppresses_old_cleaning(self):
  old=row(**{'Sol#':'OLD'});new=row(**{'Sol#':'OLD','NaicsCode':'238220','Type':'Award Notice','PostedDate':'2026-10-25T10:00:00Z','ResponseDeadLine':''})
  for rows in [[old,new,row()],[new,old,row()]]:self.assertEqual([b['sol'] for b in collect(rows)[0]['bids']],['CLEAN1'])
 def test_cancel_and_expired_amendment_do_not_resurrect(self):
  for changes in [{'Title':'Cancelled janitorial services'},{'ResponseDeadLine':'2020-01-01'}]:
   old=row(**{'Sol#':'OLD'});new=row(**{'Sol#':'OLD','PostedDate':'2026-10-25T10:00:00Z',**changes});self.assertEqual(len(collect([row(),old,new])[1]['bids']),1)
 def test_timezone_fractional_and_no_invalid_date_truncation(self):
  self.assertEqual(M['parse_dt']('2026-10-25T08:00:00.500-04:00').hour,12)
  self.assertIsNone(M['parse_dt']('2026-10-25T99:00:00Z'))
 def test_cleaning_snapshot_preserves_exact_deadline_for_expiry_checks(self):
  cleaning,_,_=collect([row(ResponseDeadLine='2026-11-10T09:00:00-06:00')])
  self.assertEqual(cleaning['bids'][0]['due_at'],'2026-11-10T15:00:00+00:00')
  self.assertEqual(cleaning['bids'][0]['due_precision'],'time')
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

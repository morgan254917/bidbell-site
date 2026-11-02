"""Publish public federal award-period endings as forecasts, never open bids.

No account or key. A partial, malformed, oversized or timed-out API search never
replaces the previous public file. The app independently checks its real age.
"""
import argparse
import hashlib
import html
import json
import math
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

API = 'https://api.usaspending.gov/api/v2/search/spending_by_award/'
NAICS = {'561720','561740','561790'}
STATES = set('AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY PR GU VI AS MP'.split())
FIELDS = ['Award ID','Recipient Name','Start Date','End Date','Award Amount','Description','Awarding Agency',
          'Awarding Sub Agency','Place of Performance State Code','Primary Place of Performance','NAICS','PSC','generated_internal_id']
MANDATORY = re.compile(r'ABILITY\s*ONE|JWOD|JAVITS|SOURCEAMERICA|\bNISH\b|\bNIB\b|PROCUREMENT\s+LIST',re.I)
CLEANING = re.compile(r'\b(?:clean\w*|wash\w*|janitor\w*|custod\w*|housekeep\w*|saniti[sz]\w*|disinfect\w*|sweep\w*)\b',re.I)
SCOPE = ('Federal cleaning award-period endings, not open solicitations. Options, extensions or agency decisions '
         'may change the dates; an ending is not a promise of a new tender. API coverage: awards started in the '
         'last six years, selected cleaning NAICS, PSC S2, amount at least US$2,500, known US performance state; '
         'identified mandatory-source contracts excluded.')

def _text(value,limit):
    return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]*>',' ',str(value or '')))).strip()[:limit]

def _date(value):
    try:return date.fromisoformat(str(value or '')[:10])
    except ValueError:return None

def _public_contract(row,today):
    if not isinstance(row,dict):return None
    end=_date(row.get('end'));start=_date(row.get('start'))
    state=str(row.get('state') or '').upper();description=_text(row.get('description'),500)
    link=row.get('link','');naics=str(row.get('naics') or '')
    try:
        url=urllib.parse.urlsplit(link);amount=float(row.get('amount') or 0)
        valid=(url.scheme=='https' and url.hostname=='www.usaspending.gov' and not url.username and not url.password
               and url.port in (None,443) and not url.query and not url.fragment
               and re.fullmatch(r'/award/[A-Za-z0-9_.-]{1,300}',url.path))
    except (ValueError,TypeError):return None
    if (not valid or not end or end<today or state not in STATES or naics not in NAICS
            or not math.isfinite(amount) or amount<2500 or not CLEANING.search(description)
            or MANDATORY.search(description+' '+str(row.get('contractor') or ''))):return None
    identity=_text(row.get('award_id'),150)
    if not identity:return None
    return {'award_id':identity,'contractor':_text(row.get('contractor'),200),'description':description,
            'agency':_text(row.get('agency'),250),'city':_text(row.get('city'),100),'state':state,'naics':naics,
            'start':start.isoformat() if start else '', 'end':end.isoformat(),'amount':amount,'link':link}

def _envelope(rows,updated,now,complete,coverage_status,**metadata):
    unique={row['link']:row for row in rows if row}
    return {'version':1,'kind':'contract_endings_forecast','updated':updated,'published_at':now.isoformat(),
            'source':'USAspending.gov public federal award records','source_url':API,'scope':SCOPE,
            'complete':complete,'coverage_status':coverage_status,**metadata,
            'contracts':sorted(unique.values(),key=lambda row:(row['end'],row['state'],row['award_id']))}

def sanitize_snapshot(source,now=None):
    """One-time migration of an existing public award cache, with no false freshness."""
    now=now or datetime.now(timezone.utc)
    if not isinstance(source,dict) or not isinstance(source.get('contracts'),list):raise ValueError('Invalid legacy award snapshot')
    updated=datetime.fromisoformat(str(source.get('at') or '').replace('Z','+00:00'))
    if updated.tzinfo is None or updated>now+timedelta(hours=1):raise ValueError('Invalid snapshot time')
    rows=[_public_contract(row,now.date()) for row in source['contracts']]
    return _envelope(rows,updated.isoformat(),now,False,'legacy_snapshot_not_exhaustively_verified',
                     records_scanned=len(rows),pages_read=None,truncated=None)

def _post(body,deadline):
    """Fixed official endpoint, two bounded attempts, no credentials or redirects."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args):return None
    opener=urllib.request.build_opener(NoRedirect)
    for attempt in range(2):
        remaining=deadline-time.monotonic()
        if remaining<=0:raise ValueError('Calendar runtime budget reached; previous file retained')
        request=urllib.request.Request(API,data=json.dumps(body).encode(),headers={
            'Content-Type':'application/json','User-Agent':'BidBell public award calendar (getbidbell.com)'})
        try:
            with opener.open(request,timeout=min(20,remaining)) as response:
                raw=response.read(2*1024*1024+1)
                if len(raw)>2*1024*1024:raise ValueError('Calendar API page exceeded bound')
                return json.loads(raw)
        except (OSError,urllib.error.URLError) as error:
            if attempt:raise ValueError('Calendar API unavailable; previous file retained') from error
            time.sleep(min(1,max(0,deadline-time.monotonic())))

def collect(post=None,now=None,max_pages=150,budget_seconds=600):
    now=now or datetime.now(timezone.utc);today=now.date();deadline=time.monotonic()+budget_seconds
    filters={'naics_codes':{'require':sorted(NAICS)},'award_type_codes':['A','B','C','D'],
             'time_period':[{'start_date':(today-timedelta(days=365*6)).isoformat(),'end_date':today.isoformat()}],
             'place_of_performance_locations':[{'country':'USA'}]}
    call=post or (lambda body:_post(body,deadline));rows=[];scanned=0;seen_pages=set()
    for page in range(1,max_pages+1):
        if time.monotonic()>=deadline:raise ValueError('Calendar runtime budget reached; previous file retained')
        payload=call({'filters':filters,'fields':FIELDS,'limit':100,'page':page,'sort':'End Date','order':'desc','subawards':False})
        if (not isinstance(payload,dict) or not isinstance(payload.get('results'),list)
                or not isinstance(payload.get('page_metadata',{}).get('hasNext'),bool)):
            raise ValueError('Calendar API schema changed; previous file retained')
        results=payload['results'];has_next=payload['page_metadata']['hasNext']
        fingerprint=hashlib.sha256(json.dumps(results,sort_keys=True).encode()).hexdigest()
        if fingerprint in seen_pages or (has_next and not results):raise ValueError('Calendar repeated or empty page; previous file retained')
        seen_pages.add(fingerprint);scanned+=len(results)
        for raw in results:
            if not isinstance(raw,dict):raise ValueError('Invalid calendar result')
            pop=raw.get('Primary Place of Performance') or {}
            naics=raw.get('NAICS') or {};psc=raw.get('PSC') or {}
            code=naics.get('code','') if isinstance(naics,dict) else str(naics)
            service=psc.get('code','') if isinstance(psc,dict) else str(psc)
            if not service.startswith('S2'):continue
            gid=raw.get('generated_internal_id') or ''
            row=_public_contract({'award_id':raw.get('Award ID'),'contractor':raw.get('Recipient Name'),
                'description':raw.get('Description'),'agency':raw.get('Awarding Sub Agency') or raw.get('Awarding Agency'),
                'city':pop.get('city_name') if isinstance(pop,dict) else '',
                'state':(pop.get('state_code') if isinstance(pop,dict) else '') or raw.get('Place of Performance State Code'),
                'naics':code,'start':raw.get('Start Date'),'end':raw.get('End Date'),'amount':raw.get('Award Amount'),
                'link':'https://www.usaspending.gov/award/'+str(gid)},today)
            if row:rows.append(row)
        last_end=_date(results[-1].get('End Date')) if results else None
        # Sorted past-period awards cannot contain any more current endings.
        if not has_next or (last_end and last_end<today):
            return _envelope(rows,now.isoformat(),now,True,'complete_within_declared_filters',
                             records_scanned=scanned,pages_read=page,truncated=False)
        if post is None:time.sleep(min(.3,max(0,deadline-time.monotonic())))
    raise ValueError('Calendar page limit reached; previous file retained')

def publish_snapshot(feed,path,max_bytes=3*1024*1024):
    raw=json.dumps(feed,ensure_ascii=True,separators=(',',':'),allow_nan=False).encode()+b'\n'
    if len(raw)>max_bytes:raise ValueError('Calendar exceeds public feed bound; previous file retained')
    if (not isinstance(feed,dict) or feed.get('kind')!='contract_endings_forecast'
            or not isinstance(feed.get('contracts'),list) or not feed['contracts']):raise ValueError('Invalid or unexpectedly empty public calendar')
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,temporary=tempfile.mkstemp(prefix='.contract-calendar-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as output:output.write(raw);output.flush();os.fsync(output.fileno())
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-public-cache',type=Path)
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'data/contract-calendar.json')
    args=parser.parse_args()
    feed=(sanitize_snapshot(json.loads(args.from_public_cache.read_text(encoding='utf-8'))) if args.from_public_cache else collect())
    publish_snapshot(feed,args.output)
    print(json.dumps({'public_forecast_records':len(feed['contracts']),'updated':feed['updated'],
                      'complete':feed['complete'],'coverage_status':feed['coverage_status']}))

if __name__=='__main__':main()

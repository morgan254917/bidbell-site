#!/usr/bin/env python3
"""
Weekly (GitHub Action): download SAM.gov's public Contract Opportunities CSV (no key, no login) and keep
open federal CLEANING bids for the public state pages:
  561720 janitorial, 561740 carpet & upholstery cleaning, 561790 window / exterior building cleaning.
Preserves data/cleaning_bids.json and adds data/service_bids.json for selected building services.
Grounds: 561730. HVAC: 238220 with explicit maintenance/service scope in the title.
Both files derive from one fetch. Public data only; no private records or credentials.
The file lists every version of every notice (an amended solicitation appears once per version, all with the same
solicitation number), so only the latest version across ALL NAICS codes is used before category filtering.
If the download looks wrong (unexpected columns, too few rows, no cleaning bids at all) the script stops with an
error and leaves data/cleaning_bids.json unchanged, so the site never publishes empty or broken pages.
Test with a local file: SAM_CSV_FILE=sample.csv SAM_MIN_ROWS=1 python3 tools/update_bids.py
"""
import csv, io, json, os, re, string, sys, tempfile, urllib.request
from datetime import datetime, timedelta, timezone

URL = ('https://sam.gov/api/prod/fileextractservices/v1/api/download/'
       'Contract%20Opportunities/datagov/ContractOpportunitiesFullCSV.csv?privacy=Public')
TRADES = {'561720': 'janitorial', '561740': 'carpet', '561790': 'window'}
OPEN = {'Solicitation', 'Combined Synopsis/Solicitation', 'Presolicitation', 'Sources Sought'}
STATES = set('AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY '
             'NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split())   # the site covers 50 states + DC
MIN_ROWS = int(os.environ.get('SAM_MIN_ROWS', '1000'))   # the real file has tens of thousands of rows
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLDEST = datetime.min.replace(tzinfo=timezone.utc)


def col(row, *names):
    for n in names:
        if row.get(n):
            return row[n].strip()
    return ''


def parse_dt(s):
    try:
        d = datetime.fromisoformat((s or '').strip().replace('Z', '+00:00'))
        return d.astimezone(timezone.utc) if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def category(row):
    code, title = col(row, 'NaicsCode'), col(row, 'Title')
    if code in TRADES:
        return TRADES[code], 'cleaning'
    if code == '561730':
        return 'grounds', 'grounds'
    if code == '238220' and re.search(r'\b(?:HVAC|air[ -]?conditioning|chillers?|boilers?|heating|ventilation)\b', title, re.I):
        if (re.search(r'\b(?:maintenance|repair|repairs|servicing|service|services)\b', title, re.I)
                and not re.search(r'\b(?:construction|construct|new installation|install|installation|replacement|replace|supply|supplies|purchase|procurement)\b', title, re.I)):
            return 'hvac', 'hvac'
    return None


def cancelled(row):
    return bool(re.search(r'\b(?:cancelled|canceled|cancellation|withdrawn)\b', col(row, 'Title'), re.I))


def collect(raw, now, min_rows=MIN_ROWS):
    reader = csv.DictReader(io.StringIO(raw))
    need = {'NaicsCode', 'Type', 'ResponseDeadLine', 'PopState', 'Sol#', 'PostedDate'}
    if not need <= set(reader.fieldnames or []):
        raise ValueError('SAM file missing required columns; previous files retained')
    latest, rows = {}, 0
    for row in reader:
        rows += 1
        sol = re.sub(r'_\d{1,2}$', '', col(row, 'Sol#').upper())
        key = (sol, col(row, 'Department/Ind.Agency').upper()) if sol else ('', col(row, 'NoticeId') or col(row, 'Link'))
        if not any(key):
            continue
        posted = parse_dt(col(row, 'PostedDate'))
        if posted is None:
            continue
        closed = col(row, 'Type', 'BaseType') not in OPEN or cancelled(row) or col(row, 'Active').lower() in ('no', 'false', '0')
        rank = (posted, closed)
        if key not in latest or rank > latest[key][0]:
            latest[key] = (rank, row)
    if rows < min_rows:
        raise ValueError('SAM file has too few rows; previous files retained')
    bids = []
    for rank, row in latest.values():
        classified = category(row)
        if rank[1] or not classified or not col(row, 'Title'):
            continue
        due = parse_dt(col(row, 'ResponseDeadLine'))
        if not due or due < now + timedelta(days=1):
            continue
        state = col(row, 'PopState').upper()
        if col(row, 'PopCountry').upper() not in ('', 'USA', 'US') or state not in STATES:
            continue
        trade, group = classified
        link = col(row, 'Link')
        if not link.startswith('https://sam.gov/'):
            nid = col(row, 'NoticeId')
            link = 'https://sam.gov/opp/' + nid + '/view' if re.fullmatch(r'[a-zA-Z0-9-]+', nid) else 'https://sam.gov/search/?index=opp'
        bids.append({'trade': trade, 'category': group, 'title': col(row, 'Title'), 'type': col(row, 'Type', 'BaseType'),
                     'agency': string.capwords(col(row, 'Department/Ind.Agency', 'Sub-Tier').lower()),
                     'city': string.capwords(col(row, 'PopCity').lower()), 'state': state,
                     'due': due.date().isoformat(), 'due_at': due.isoformat(), 'set_aside': col(row, 'SetASide'),
                     'link': link, 'sol': col(row, 'Sol#').upper()})
    bids.sort(key=lambda b: (b['due_at'], b['sol']))
    cleaning = [{k:v for k,v in b.items() if k not in ('category','due_at')} for b in bids if b['category']=='cleaning']
    if not cleaning:
        raise ValueError('No open cleaning bids found; previous files retained')
    common = {'updated': now.date().isoformat(), 'source': 'SAM.gov public Contract Opportunities data'}
    return dict(common,bids=cleaning), dict(common, scope='Selected federal public notices only. HVAC coverage is conservative title-based maintenance classification. Not complete market coverage.', bids=bids), rows


def write_outputs(cleaning, services, directory):
    # Validate and stage both files before replacing either; each individual replacement is atomic.
    os.makedirs(directory, exist_ok=True)
    staged=[]
    try:
        for name, payload in [('cleaning_bids.json',cleaning),('service_bids.json',services)]:
            encoded=json.dumps(payload,ensure_ascii=True,indent=1,allow_nan=False)
            if not isinstance(json.loads(encoded).get('bids'),list):
                raise ValueError('Invalid output')
            fd,path=tempfile.mkstemp(prefix='.bidbell-',suffix='.json',dir=directory)
            staged.append((path,os.path.join(directory,name)))
            with os.fdopen(fd,'w',encoding='utf-8') as out:
                out.write(encoded);out.flush();os.fsync(out.fileno())
        for path,target in staged:
            os.replace(path,target)
    finally:
        for path,_ in staged:
            if os.path.exists(path):os.unlink(path)


def main():
    f=os.environ.get('SAM_CSV_FILE')
    if f:
        with open(f,encoding='cp1252',errors='replace') as source:raw=source.read()
    else:
        with urllib.request.urlopen(URL,timeout=600) as response:raw=response.read().decode('cp1252',errors='replace')
    try:
        cleaning,services,rows=collect(raw,datetime.now(timezone.utc))
        write_outputs(cleaning,services,os.path.join(ROOT,'data'))
    except ValueError as e:
        sys.exit(str(e))
    counts={kind:sum(b['category']==kind for b in services['bids']) for kind in ('cleaning','grounds','hvac')}
    print(json.dumps({'rows':rows,'counts':counts,'updated':services['updated']}))


if __name__ == '__main__':
    main()

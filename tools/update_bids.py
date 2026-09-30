#!/usr/bin/env python3
"""
Weekly (GitHub Action): download SAM.gov's public Contract Opportunities CSV (no key, no login) and keep
open federal CLEANING bids for the public state pages:
  561720 janitorial, 561740 carpet & upholstery cleaning, 561790 window / exterior building cleaning.
Writes data/cleaning_bids.json. Public data only; nothing private is ever stored in this project.
The file lists every version of every notice (an amended solicitation appears once per version, all with the same
solicitation number), so only the latest version of each notice is used.
If the download looks wrong (unexpected columns, too few rows, no cleaning bids at all) the script stops with an
error and leaves data/cleaning_bids.json unchanged, so the site never publishes empty or broken pages.
Test with a local file: SAM_CSV_FILE=sample.csv SAM_MIN_ROWS=1 python3 tools/update_bids.py
"""
import csv, io, json, os, string, sys, urllib.request
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
    s = s.strip().replace('Z', '+00:00')
    for cut in (None, 19, 10):
        try:
            d = datetime.fromisoformat(s if cut is None else s[:cut])
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def main():
    f = os.environ.get('SAM_CSV_FILE')
    raw = (open(f, encoding='cp1252', errors='replace').read() if f else
           urllib.request.urlopen(URL, timeout=600).read().decode('cp1252', errors='replace'))
    reader = csv.DictReader(io.StringIO(raw))
    need = {'NaicsCode', 'Type', 'ResponseDeadLine', 'PopState', 'Sol#', 'PostedDate'}
    if not need <= set(reader.fieldnames or []):
        sys.exit(f'SAM.gov file is missing columns {sorted(need - set(reader.fieldnames or []))}; '
                 'data/cleaning_bids.json left unchanged')
    now = datetime.now(timezone.utc)
    latest, rows = {}, 0
    for row in reader:
        rows += 1
        trade = TRADES.get(col(row, 'NaicsCode'))
        if not trade:
            continue
        sol = col(row, 'Sol#').upper()
        key = (sol, col(row, 'Department/Ind.Agency').upper()) if sol else ('', col(row, 'NoticeId') or col(row, 'Link'))
        posted = parse_dt(col(row, 'PostedDate')) or OLDEST
        if key not in latest or posted >= latest[key][0]:
            latest[key] = (posted, trade, row)   # keep only the newest version of each notice
    if rows < MIN_ROWS:
        sys.exit(f'SAM.gov file has only {rows} rows; data/cleaning_bids.json left unchanged')
    bids = []
    for posted, trade, row in latest.values():
        typ = col(row, 'Type', 'BaseType')
        if typ not in OPEN or col(row, 'Active').lower() in ('no', 'false'):
            continue   # the newest version is an award, a cancellation or an archived notice
        due = parse_dt(col(row, 'ResponseDeadLine'))
        if not due or due < now + timedelta(days=1):
            continue
        state = col(row, 'PopState').upper()[:2]
        if col(row, 'PopCountry') not in ('', 'USA', 'US') or state not in STATES:
            continue
        bids.append({'trade': trade, 'title': col(row, 'Title'), 'type': typ,
                     'agency': string.capwords(col(row, 'Department/Ind.Agency', 'Sub-Tier').lower()),
                     'city': string.capwords(col(row, 'PopCity').lower()), 'state': state,
                     'due': due.date().isoformat(), 'set_aside': col(row, 'SetASide'),
                     'link': col(row, 'Link') or 'https://sam.gov/search/?index=opp', 'sol': col(row, 'Sol#').upper()})
    if not bids:
        sys.exit('No open cleaning bids found in the SAM.gov file; data/cleaning_bids.json left unchanged')
    bids.sort(key=lambda b: b['due'])
    out = {'updated': now.date().isoformat(), 'source': 'SAM.gov public Contract Opportunities data', 'bids': bids}
    json.dump(out, open(os.path.join(ROOT, 'data', 'cleaning_bids.json'), 'w'), indent=1)
    print(len(bids), 'open cleaning bids written from', rows, 'rows')


if __name__ == '__main__':
    main()

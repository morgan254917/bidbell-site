#!/usr/bin/env python3
"""
Weekly (GitHub Action): download SAM.gov's public Contract Opportunities CSV (no key, no login) and keep
open federal CLEANING bids for the public state pages:
  561720 janitorial, 561740 carpet & upholstery cleaning, 561790 window / exterior building cleaning.
Writes data/cleaning_bids.json. Public data only; nothing private is ever stored in this project.
Test with a local file: SAM_CSV_FILE=sample.csv python3 tools/update_bids.py
"""
import csv, io, json, os, string, urllib.request
from datetime import datetime, timedelta, timezone

URL = ('https://sam.gov/api/prod/fileextractservices/v1/api/download/'
       'Contract%20Opportunities/datagov/ContractOpportunitiesFullCSV.csv?privacy=Public')
TRADES = {'561720': 'janitorial', '561740': 'carpet', '561790': 'window'}
OPEN = {'Solicitation', 'Combined Synopsis/Solicitation', 'Presolicitation', 'Sources Sought'}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
    now = datetime.now(timezone.utc)
    seen, bids = set(), []
    for row in csv.DictReader(io.StringIO(raw)):
        trade = TRADES.get(col(row, 'NaicsCode'))
        typ = col(row, 'Type', 'BaseType')
        if not trade or typ not in OPEN or col(row, 'Active').lower() in ('no', 'false'):
            continue
        due = parse_dt(col(row, 'ResponseDeadLine'))
        if not due or due < now + timedelta(days=1):
            continue
        country = col(row, 'PopCountry')
        if country not in ('', 'USA', 'US'):
            continue
        sol = col(row, 'Sol#').upper()
        if sol and sol in seen:
            continue
        seen.add(sol)
        bids.append({'trade': trade, 'title': col(row, 'Title'), 'type': typ,
                     'agency': string.capwords(col(row, 'Department/Ind.Agency').lower()),
                     'city': string.capwords(col(row, 'PopCity').lower()), 'state': col(row, 'PopState').upper()[:2],
                     'due': due.date().isoformat(), 'set_aside': col(row, 'SetASide'),
                     'link': col(row, 'Link') or 'https://sam.gov/search/?index=opp', 'sol': sol})
    bids.sort(key=lambda b: b['due'])
    out = {'updated': now.date().isoformat(), 'source': 'SAM.gov public Contract Opportunities data', 'bids': bids}
    json.dump(out, open(os.path.join(ROOT, 'data', 'cleaning_bids.json'), 'w'), indent=1)
    print(len(bids), 'open cleaning bids written')


if __name__ == '__main__':
    main()

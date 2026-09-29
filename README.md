# bidbell-site

The public BidBell website (getbidbell.com), served by GitHub Pages. Static files only: no server, no database,
no JavaScript, no cookies, no trackers. **Never put secrets, customer data or email lists in this project** — it is public.

| Path | What |
|---|---|
| `tools/site.json` | Business facts used on every page (owner name, mailing address, email, prices, form link, governing law) |
| `tools/build.py` | Builds every page: home, /start/, /cleaning-bids/ (50 states + DC, carpet, window), legal pages, 404, sitemap, robots, security.txt |
| `tools/update_bids.py` | Downloads SAM.gov's public CSV and keeps open federal cleaning bids (NAICS 561720, 561740, 561790) |
| `tools/style.css` | The one stylesheet (light and dark mode) |
| `tools/LAWYER_REVIEW.md` | Clauses a lawyer should review (also marked in the HTML as `<!-- LAWYER-REVIEW n -->`) |
| `.github/workflows/weekly-bids.yml` | Mondays 07:00 UTC: refresh bids, rebuild, publish |

To change a fact (name, address, prices, sign-up form link): edit `tools/site.json`, then run `python3 tools/build.py`.

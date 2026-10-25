# BidBell

BidBell helps building-service contractors find opportunities, keep a shortlist and prepare a bid. The brand is broader than any individual feed. Show actual coverage beside each service rather than implying every trade is available everywhere.

- Website: https://getbidbell.com/
- Opportunity workspace: https://getbidbell.com/workspace/
- Bid preparation checklist: https://getbidbell.com/prepare/
- Cleaning notices by state: https://getbidbell.com/cleaning-bids/
- Current daily cleaning alerts: 14 days free, then $39/month or $390/year at https://getbidbell.com/start/

The current paid alert plan covers janitorial, carpet, window and exterior cleaning. Adding a public-data category does not automatically expand paid coverage. Daily email includes a short status update on quiet days. Existing subscribers and billing remain separate from the free workspace.

The public workspace reads a dated federal building-services snapshot, with trade, state and text filters. Users can keep a shortlist, choose a stage, record a next action and export a text copy. The preparation checklist works with any manually entered bid. Neither tool certifies eligibility, writes a complete proposal or submits a bid.

## Data and privacy

This is a public static website served by GitHub Pages. Never commit credentials, private customer records, recipient lists or internal research to this repository.

The workspace and preparation checklist use browser localStorage only after an explicit Save action. Those records do not have a cloud account or cross-device synchronization. Later edits require another save. Both pages offer export and deletion. People sharing the browser profile may access its saved records.

The workspace fetches public data from this website. Signup sends answers to the configured Google Form. The plan page loads Paddle for checkout when configured. The site adds no advertising or analytics tracking. Do not describe it as having no browser storage or only a signup form.

## Source files

| Path | Purpose |
|---|---|
| `index.html`, `home.css`, `home.js` | Authored homepage, preserved by the builder |
| `workspace/` | Public notice search, personal shortlist and progress |
| `prepare/` | Manual bid checklist and validated source prefill |
| `data/service_bids.json` | Dated building-services snapshot, when available |
| `data/cleaning_bids.json` | Existing cleaning-only data for state/category pages |
| `tools/update_bids.py` | Official public-data ingestion and category filtering |
| `tools/build.py` | Generates signup, subscription, category, policy and error pages; preserves authored product pages and registers their sitemap routes |
| `tools/site.json` | Business facts, current prices and signup fields |
| `tools/paddle.json` | Public checkout settings; never a Paddle API secret |
| `tools/form.js`, `tools/checkout.js`, `tools/nav.js` | Generated-page scripts copied by the builder |
| `tools/style.css` | Shared generated-page styling |
| `tools/test_site.py` | Route, signup-contract, pricing and copy checks |
| `.github/workflows/weekly-bids.yml` | Scheduled data refresh/rebuild; manual refresh=false rebuilds without a data download |

## Build and verify

Run `python tools/build.py`, then `python tools/test_site.py`.

Run browser-tool unit tests with `node --test workspace/core.test.mjs prepare/plan.test.mjs`.

The builder fails if the authored homepage, workspace or preparation page is missing. It cannot restore the obsolete cleaning-only homepage. Cleaning-specific routes remain because they are still useful, accurate category pages.

Rebuilding existing data does not refresh its source date. Check source freshness, filters, form behavior and checkout settings before release. Do not send customer emails or initiate charges just to test a page.

The local `desk/` experiment is not part of this release and must be excluded from deployments. Internal plans and private notes stay outside the public repository.

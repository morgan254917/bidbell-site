# BidBell

BidBell helps cleaning companies find work, build applications with reusable company details and documents, and review and send supported email bids. Portal-only bids use a guided handoff to the buyer's portal. Broader public notice previews remain available. The brand is broader than any individual feed. Show actual coverage beside each service rather than implying every trade is available everywhere.

- Website: https://getbidbell.com/
- Opportunity workspace: https://getbidbell.com/workspace/
- Bid preparation checklist: https://getbidbell.com/prepare/
- Cleaning notices by state: https://getbidbell.com/cleaning-bids/
- Alerts and bid preparation: one 14-day no-card trial, then US$39/month by choice at https://getbidbell.com/start/
- Account and preparation workspace: https://bidbell-workspace.onrender.com/app

The current paid alert plan covers janitorial, carpet, window and exterior cleaning. Adding a public-data category does not automatically expand paid coverage. Daily email includes a short status update on quiet days. The signed-in workspace is included in the existing alerts subscription. Supported email submissions require original buyer instructions specifying one to five recipients, current-notice and deadline validation, exact message and file review, and final customer confirmation. Mail-server acceptance is distinct from buyer receipt. Standard supported fillable PDF text fields use explicitly reviewed saved facts; other buyer forms still require customer completion. Link the same verified email. Original trial dates and legacy annual terms remain unchanged. Public notice browsing and the manual checklist are supporting tools, not a second subscription.

The public workspace reads a dated federal building-services snapshot, with trade, state and text filters. Users can keep a shortlist, choose a stage, record a next action and export a text copy. The preparation checklist works with any manually entered bid. Neither tool certifies eligibility, writes a complete proposal or submits a bid.

## Data and privacy

This is a public static website published through the existing Render account using its free static-site service. GitHub Pages is retained as a manual fallback while its deployment lock is unresolved. Never commit credentials, private customer records, recipient lists or internal research to this repository.

The public notice browser at `/workspace/` and public checklist at `/prepare/` use browser localStorage only after an explicit Save action. Those public-preview records do not have a cloud account or cross-device synchronization. Later edits require another save. Both pages offer export and deletion. People sharing the browser profile may access their saved records. In your signed-in BidBell account at `bidbell-workspace.onrender.com/app`, private working answer drafts autosave for recovery after an interruption. Customers still review and choose Save answer to add text to their response. Other account forms still need their own Save action.

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

Run `python tools/prepare_static.py`. It builds the site, runs all website and checkout checks, and copies only public assets into `_site/`. Render uses this command and publishes `_site/` after each main-branch update. Build failure prevents publication. `release.json` identifies the exact deployed commit and the UTC `build_date` used to generate its pages.

Staging captures one UTC build date before generating pages and passes it through `BUILD_DATE`, including builds that cross midnight. The normal builder and daily workflow still use the current UTC day to remove expired opportunities. Legal policy dates remain explicitly configured. Committed generated-page snapshots can predate a later deployment of the same source. To verify that deployment, `tools/check_live_site.py` checks the expected commit, bounds its declared date between that commit and the current UTC day, exports the trusted Git source into an isolated temporary directory and rebuilds at that exact date. It compares every public customer HTML route against those exact expected bytes. Authored pages are preserved, image checks remain unchanged, and changed prices or copy fail verification.

Text checkouts and generated writes explicitly use LF line endings. The trusted Git export disables host `core.autocrlf` conversion. This preserves authored Git bytes and makes generated HTML identical on Windows and Render/Linux without normalizing verification responses.

The production domain remains getbidbell.com. The staging address is https://bidbell-website.onrender.com. Domain cutover is complete only after DNS, HTTPS and live content are verified. Preserve all mail records when changing website routing.

Run browser-tool unit tests with `node --test workspace/core.test.mjs prepare/plan.test.mjs`.

The builder fails if the authored homepage, workspace or preparation page is missing. It cannot restore the obsolete cleaning-only homepage. Cleaning-specific routes remain because they are still useful, accurate category pages.

Rebuilding existing data does not refresh its source date. Check source freshness, filters, form behavior and checkout settings before release. Do not send customer emails or initiate charges just to test a page.

The local `desk/` experiment is not part of this release and must be excluded from deployments. Internal plans and private notes stay outside the public repository.

Live verification: run `python tools/check_live_site.py`. HTML, scripts and styles must match the committed bytes. For CDN-transformed images, install Pillow in the operator verification environment: PNG pixels and dimensions must match exactly; JPEG recompression is allowed only within tight pixel-difference bounds. This optional verifier dependency is not required by the static site or customer app. Its four image-integrity checks run when Pillow is available.

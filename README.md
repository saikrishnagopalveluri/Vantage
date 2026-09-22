# Vantage

Vantage reads business and tech news and tells you why each story matters to your career. Each story comes with a short reason and a next step. It is built for students first and working professionals second, and it is one product: a profile starts out job hunting and switches to working when you get the job.

- `apps/api`: FastAPI and SQLAlchemy. SQLite locally, portable to Postgres.
- `apps/web`: Next.js 16 PWA. Installable, works offline, designed for phones first.


Powered by DOT Club, IBS Hyderabad. The logo is in `apps/web/public/partners/` and the credit is one component, `apps/web/src/components/partner-badge.tsx`, used on the home, login, profile and shared-score pages, in the desktop sidebar and on the quiz intro.

## What it covers

Twenty-four fields of work, from Marketing, Finance, Sales and HR through Software, Data and AI, Digital Transformation, Platform Businesses and B2B, to Healthcare, Legal, Education, Trades, Agriculture, Hospitality and Creative work. A reader follows up to four.

| | Count | Where it comes from |
| --- | --- | --- |
| Roles and job titles | about 45,000 | 351 hand-written roles (niche ones like Actuarial Analyst and Compiler Engineer), 1,002 O*NET occupations, and about 44,000 real job titles that point back at the occupation they belong to |
| Companies | about 22,000 | 507 hand-written, then SEC filers (about 7,900), NSE-listed firms (about 2,500) and listed companies from Wikidata across 42 countries (about 11,000) |
| Skills and tools | about 2,100 | 561 hand-written and the tools O*NET lists for each occupation |
| News topics | 172 | Hand-written |

Only the hand-written roles, skills and companies, plus imported company names that are distinctive enough (for example "Reliance Industries" but not "First Bank"), are used to tag news. The rest are there to search, pick and compare, so 45,000 titles can't drown the feed in false matches.

News comes from about 195 official RSS and Atom feeds, 26 of them newsletters (see below). We store the headline, link, publisher, a 300-character teaser and up to 1,600 characters of the feed's own text, which is used only to build the expandable summary. We never store full articles. Many publishers only share a headline and a teaser in their feed. For those, the summary says so and links to the article.

### Consulting, IT services and digital transformation

The firms a management student meets are covered in depth: the Big 4 and the mid-tier accounting and advisory firms (Grant Thornton, BDO, RSM, Forvis Mazars and others), the strategy houses (McKinsey, BCG, Bain, Kearney, Oliver Wyman, Simon-Kucher, AlixPartners and more), HR and talent consultancies (Mercer, Aon, WTW, Korn Ferry), research firms (Gartner, IDC, Forrester, Everest, Zinnov), the IT services companies (Cognizant, LTIMindtree, Mphasis, Persistent, Coforge, Thoughtworks, Publicis Sapient and more) and the platforms digital transformation is built on. Common sub-brands are aliases, so a headline that says "Deloitte India" or "EY-Parthenon" is found. Consulting and transformation roles run from Associate Consultant to Partner, and from Digital Transformation Consultant to Presales Consultant. The new lists are in `apps/api/app/seed_data/expansion.py`.

Big 4, IT services and many consulting firms publish no feed of their own, so their news comes through Google News searches (official RSS) in `seed_data/sources.py`. A few sites block automated readers (Tech Brew, Morning Brew, Technology Magazine, Reuters and others), and those are left out rather than worked around. Morning Brew Daily is a podcast feed with no page per episode, so its stories link to the show's site.

### Newsletters

The Feed has a **Newsletters** tab. It reads Substack and other independent newsletters on technology, strategy, finance, product and India (Lenny's Newsletter, Not Boring, The Generalist, The Pragmatic Engineer, Platformer, Net Interest, The Daily Brief by Zerodha, Finshots, The Playbook by Morning Brew and others). A newsletter essay often has a metaphorical headline, so its opening text is read too and one real match keeps it, and the tab lets weaker matches in. The list is `NEWSLETTERS` in `seed_data/sources.py`; add a name and feed there and run `python -m app.seed --sync`.

### Pop quiz

Tap the Vantage logo three times (or use **Play the pop quiz** on the Profile page). Questions are made from the taxonomy, real headlines with the company blanked out, and a hand-written bank of management basics in `seed_data/quiz_concepts.py`, and lean towards the player's own roles, companies and fields. The game runs until three wrong answers, gets harder every four right ones, and has a clock, streaks, sound (off with one tap) and a review of what was missed. A finished game can be posted: a shareable link (`/quiz/share`) with a preview picture for LinkedIn, X and WhatsApp, a downloadable card, and the phone's own share sheet. A post shows only the score and a title, never a name or profile. The questions come from `GET /quiz/{user_id}`.

### Summaries and pointers

Each story can be expanded to show one or two short paragraphs and a few quick pointers. They are chosen from the publisher's own feed text (extractive, nothing is generated), so they can't say something the article didn't. They stay hidden until you open them.

### Job descriptions

On the Skill gaps page, the Job descriptions tab lets you paste up to 30 postings (or open a .txt file). Each one is read for the skills and tools it names, and you see what you cover in each, plus a combined list of what is missing across all of them, most requested first. A posting that names no skill we know is turned down with a message rather than saved empty.

## Deploy on Vercel with Supabase

Two Vercel projects from this repo (the web app and the API), a Supabase Postgres database, and a GitHub Actions job for the hourly news pull. Vercel functions are short-lived and can't run a background scheduler, so the pull happens in GitHub instead.

**1. Database (Supabase).** Create a project in the region nearest your users. You will use two connection strings from Project Settings, then Database:
- the **Session pooler** string (port 5432) from your own machine, for the one-time load below (the direct string is IPv6 only);
- the **Transaction pooler** string (port 6543) for Vercel and GitHub.

Then load the data from your machine:

```bash
cd apps/api
set DATABASE_URL=<session pooler string>            # PowerShell: $env:DATABASE_URL="..."
.venv/Scripts/python -m app.migrate                  # creates the tables and switches on row level security
.venv/Scripts/python -m app.copy_db --to "$DATABASE_URL"   # roles, companies, skills, topics, feeds and stories
```

The copy leaves accounts, profiles and the demo stories behind, so local test users never reach production. It refuses to write into a database that already has data unless you add `--replace`.

Row level security matters here: Supabase publishes the tables of the `public` schema through its own REST API, and a table without it can be read or changed by anyone with your project's public anon key. `app.migrate` turns it on for every table. Vantage reaches the database only through its own API as the `postgres` role, which is unaffected. You can also switch off the Data API in Supabase settings.

**2. API (Vercel project 1).** Import the repo, set **Root Directory** to `apps/api`, and add these environment variables:

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | the Transaction pooler string |
| `VANTAGE_SECRET` | a long random string (`python -c "import secrets; print(secrets.token_hex(32))"`). Required: there is no disk to keep a key on |
| `VANTAGE_SKIP_DDL` | `1` (tables already exist, so don't check on every cold start) |
| `VANTAGE_SCHEDULER` | `0` |
| `VANTAGE_OPERATOR_NAME`, `VANTAGE_CONTACT_EMAIL`, `VANTAGE_GRIEVANCE_OFFICER` | for the Terms and Privacy pages |

`apps/api/vercel.json` points every route at `index.py` and asks for the Tokyo region (`hnd1`, next to a Supabase project in ap-northeast-1). Change `regions` to sit next to your Supabase region; the API makes many small queries, so distance shows.

**3. Web (Vercel project 2).** Import the repo again, set **Root Directory** to `apps/web`, and add `BACKEND_URL` = the API project's production URL (for example `https://vantage-api.vercel.app`). The address is baked in at build time, so redeploy after changing it. The browser only talks to the web project, which forwards `/api/*` to the API, so there is no CORS setup and the login cookie stays on one domain. Keep Deployment Protection off for the API's production URL, or the web project can't reach it.

**4. News (GitHub).** Push the repo to GitHub and add a repository secret `DATABASE_URL` (the Transaction pooler string). `.github/workflows/ingest.yml` then pulls the feeds every hour and does the daily clean-up at 03:05 UTC. Run it once by hand from the Actions tab to fill the feed straight away.

Limits to know about:
- The login throttle is kept in memory, so on Vercel it applies per running instance, which is weak against a determined attacker. Put Vercel's firewall rate limiting on `/api/auth/*`, or move the counter into the database.
- The first request after a quiet period is slower (a cold start).
- A free Supabase project pauses after a week without activity.
- I could not run this against a real Supabase or Vercel project from here. What is tested: the Postgres schema and indexes compile, the URL handling, the copy tool on real data (92,000 rows, 8 seconds, into a scratch file), the Vercel entry point, and the whole API suite on SQLite. Expect to fix small things on the first deploy.

## Deploy with Docker

One small Linux server is enough. `docker-compose.yml` runs three containers: the API, the web app and Caddy, which serves your domain over HTTPS and gets the certificate itself. Only Caddy is reachable from outside.

```bash
cp .env.example .env        # set DOMAIN, VANTAGE_SECRET and the operator details for the legal pages
docker compose up -d --build
```

- On first start the API creates the database and loads the curated data. On every start it adds anything curated that is missing and wipes nothing. No demo user or sample stories are loaded.
- Use a real domain that points at the server for `DOMAIN`. To try it on your own machine, set `DOMAIN=http://localhost` (and `HTTP_PORT` if 80 is taken).
- Data lives in the `vantage-data` volume: the database, the session signing key and the import cache. **Back it up.** It holds accounts and profiles.
- Load the big role and company lists once: `docker compose exec api python -m app.importers all` (the SEC part takes about 20 minutes and can be repeated).
- Keep exactly one API container. SQLite, the hourly scheduler and the login throttle all assume a single process. To scale out, move to Postgres and run the scheduler separately (`VANTAGE_SCHEDULER=0`, then `python -m app.scheduler`).
- The web image bakes in the API address (`BACKEND_URL`, set in the compose file) at build time. Change it and rebuild.
- Update with `git pull && docker compose up -d --build`.

I could not build these images on the machine they were written on (Docker was not running), so the first `docker compose up` is their first real test. What I did check: the compose file validates, the start-up steps work against an empty database, and the standalone web build serves pages, assets and the API proxy correctly.

## Built for management students first

Vantage's first audience is a student at a business school (MBA, PGDM and similar) preparing for placements. The curated data leans that way:

- **Roles.** About 110 are marked as popular with management students: associate brand manager, consultant and engagement manager, investment banking and equity research associate, venture capital associate, management trainee, area sales manager, HR generalist, supply chain manager, product manager, chief of staff and so on, with the skills each one asks for.
- **Skills.** About 70 are marked the same way, from case interviewing, Porter's Five Forces, market sizing and unit economics to valuation, category management and S&OP.
- **Recruiters.** About 150 companies that recruit at business schools are marked: FMCG, consulting, banks and investment firms, venture funds, platforms, auto, pharma and conglomerates.
- **How it shows.** In pickers and lists, marked roles, companies and skills come first, and onboarding and the profile editor show them as "Popular with management students" quick picks. `GET /taxonomy/roles|companies|capabilities` take `mba=true` to return only those.
- **News.** Extra feeds for business students: Poets&Quants, Knowledge at Wharton, Ivey Business Journal, The Economist, the Financial Times, Economic Times industry, startups and CFO pages, Business Today, Inc42, YourStory, afaqs and others.

The lists live in `apps/api/app/seed_data/mba.py`. Loading fails if a name in them doesn't exist, so they can't drift. Add a role or company to the module and run `python -m app.seed --sync` to update a live database.

## Terms, privacy and your data rights

- `/terms` and `/privacy` are written for this app and match what the code does. The privacy policy covers India's DPDP Act, 2023 (notice, consent, rights to a summary, correction and erasure, grievance redressal, nomination, age 18) and the GDPR (controller, lawful bases, rights, complaint to an authority, retention, transfers, automated ranking).
- **Consent.** Signing up needs a tick for "I am 18 or older" and "I agree to the Terms and have read the Privacy Policy". A guest ticks the same on the first onboarding step. The versions agreed, the time and how (sign-up or guest) are stored in `consents`, and a stale version is refused.
- **Access and portability.** Profile, then Your data, then Download my data returns a JSON file of everything held about you, in words (`GET /privacy/export`). Password hashes are never included.
- **Erasure and withdrawing consent.** Delete my account and data (`DELETE /privacy/account`) removes every row that carries your user id, including job descriptions and the consent record. Accounts must re-enter their password. Any table with a `user_id` column is covered automatically, and a test pins that.
- **Who to contact.** Set `VANTAGE_OPERATOR_NAME`, `VANTAGE_CONTACT_EMAIL`, `VANTAGE_GRIEVANCE_OFFICER` (and optionally `VANTAGE_GRIEVANCE_EMAIL`, `VANTAGE_POSTAL_ADDRESS`, `VANTAGE_HOSTING_REGION`). Until they are set the pages say "Not set yet" and show a draft notice. `VANTAGE_REQUIRE_CONSENT=0` turns the consent check off for local scripts.

**These texts are a working draft, not legal advice.** Have a lawyer review them, and fill in the operator details, before real people use the app. Not built: Indian-language notices, automatic deletion of inactive accounts, and re-asking for consent when a version changes for existing users.

## Home page, accounts and sign-in

- `/` is the home page: what Vantage is, a live "Right now" panel (story and data counts and the newest headlines, from `GET /public/pulse`), a "try it" box that shows what any job title asks for before you sign up, an About section and a short FAQ.
- `/login` logs in or creates an account. You can also use the app as a **guest**: a random id on the device stands in for an account, and that profile can't move to another device.
- Passwords are hashed with scrypt and a per-user salt. A session is a signed token in an HttpOnly, SameSite=Lax cookie, so page scripts can't read it. Cookie-authenticated writes must also send `X-User-Id` matching the session, which a cross-site page can't do. Wrong passwords give the same answer whether or not the email exists, and 8 failures in 15 minutes pause logins for that email (in memory, so per process and reset on restart).
- An id that belongs to an account can't be used as a guest id, so nobody can read an account's data by sending its id in a header.

| Setting | Default | Meaning |
| --- | --- | --- |
| `VANTAGE_SECRET` | key file `apps/api/data/secret.key`, created on first run | Signs session cookies. Set it explicitly in production |
| `VANTAGE_COOKIE_SECURE` | on when the request is HTTPS | Set to `1` to always mark the cookie Secure |
| `VANTAGE_ALLOW_GUESTS` | `1` | `0` requires an account for everything |

Not built yet: email verification, password reset, and moving a guest profile into a new account. Anyone can sign up with any email address until verification exists.

## Scheduled ingestion

The API pulls every feed once an hour and runs a clean-up once a day, on its own, as long as it is running. No cron needed.

- **Hourly.** Fetches all feeds at the same time, tags new stories and stores the relevant ones. Takes well under a minute.
- **Daily** (03:00 UTC). Does the hourly pull, then deletes stories older than 60 days unless someone saved or opened them.
- Every run is written to the `ingest_runs` table. A restart does not repeat a run that just happened, and two processes can never ingest at the same time. A run that never finished stops blocking others after 45 minutes.
- `GET /health` shows the last run: when it finished, how many stories it added and how many feeds were failing.

| Setting | Default | Meaning |
| --- | --- | --- |
| `VANTAGE_SCHEDULER` | `1` | `0` turns the built-in scheduler off (use this if you run the scheduler as its own process) |
| `VANTAGE_INGEST_EVERY_MINUTES` | `60` | How often to pull feeds |
| `VANTAGE_DAILY_HOUR_UTC` | `3` | Hour of the daily clean-up |

```bash
.venv/Scripts/python -m app.scheduler                 # run the scheduler as its own process
.venv/Scripts/python -m app.scheduler --once hourly   # one pull now, then exit (also: daily)
```

The scheduler only runs while a Python process is running. To have it survive reboots on Windows, start `python -m app.scheduler` from Task Scheduler at log-on; on Linux use a systemd service or `@reboot` cron entry.

## Course handouts

The two course handouts (Managing Digital Transformation and Managing Platform Businesses, 2026-27) feed the taxonomy directly:

- The nine placement-table rows became roles (for example "Risk Advisory Analyst, Digital Transformation and Cybersecurity" at Deloitte, "Team Lead, Business Transformation" at Accenture). The skills and concepts in each row are stored as that company's own skill list for the role, so gap analysis uses the handout's wording rather than a generic guess.
- Course concepts became skills and topics: Industry 4.0, Smart Grid, Network Effects, MVP Development, Direct-to-Consumer Strategy, Monetization Models, Platform Ethics and others.
- Companies named in the case lists were added (Farfetch, Enel, Bayer, Rent the Runway, American Well, Wattpad, GoFundMe, Foursquare, Sidewalk Labs, ASICS, On, Odisha Television) next to ones already there (Deloitte, Accenture, Airbnb, Uber, Flipkart, Spotify, Netflix, Apollo Hospitals and so on).
- Five more roles for sectors the Digital Transformation course covers (utilities, public sector, media, healthcare, supply chain) and five for platform work (platform strategy, D2C brands, pricing, ethics and privacy, launches).

To add curated data like this to a database that already has users, run `python -m app.seed --sync`. It only adds what is missing and promotes an imported name to curated instead of duplicating it. Plain `python -m app.seed` is for an empty database.

## Loading the big datasets

The 45,000 roles and 22,000 companies are imported, not committed. `apps/api/data/raw/` is git-ignored and caches every download.

```bash
cd apps/api
.venv/Scripts/python -m app.seed                 # curated taxonomy, sources, demo user (add --samples for [Sample] stories)
.venv/Scripts/python -m app.importers onet       # occupations, titles, tools, skills (about 5 s)
.venv/Scripts/python -m app.importers.sec        # SIC industry for each SEC filer, resumable, about 20 min
.venv/Scripts/python -m app.importers.wikidata   # listed companies by country, cached per country
.venv/Scripts/python -m app.importers companies  # merge everything, skip anything already there
.venv/Scripts/python -m app.ingest --retag       # re-tag stored stories after the taxonomy changes
```

Imports are additive and safe to re-run. Curated data always wins: a company or role that matches one already there (ignoring "Inc", "Ltd", plurals) is skipped. Company industries come from SEC SIC codes and from keyword rules on Wikidata industries and company names, so about 60% of companies have an industry and the rest can still be picked but don't get derived hiring.

**Attribution.** Roles, titles, tools and skills include information from the O*NET 31.0 Database by the U.S. Department of Labor, Employment and Training Administration (USDOL/ETA), used under the CC BY 4.0 license. O*NET is a trademark of USDOL/ETA. Company names come from SEC EDGAR, the NSE equity list and Wikidata (CC0).

## Run it

Two terminals. Windows paths are shown; use `.venv/bin/python` elsewhere.

```bash
# 1. API (http://localhost:8000/docs)
cd apps/api
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m app.seed --samples   # taxonomy, sources, demo user and [Sample] stories (drop --samples for a real install)
.venv/Scripts/python -m app.ingest      # pull the live feeds (safe to re-run)
.venv/Scripts/python -m uvicorn app.main:app --reload --timeout-keep-alive 75

# 2. Web (http://localhost:3000)
cd apps/web
npm install
npm run dev                             # development
npm run build && npm run start          # production, needed to test the service worker
```

The browser only talks to the Next.js origin. `/api/*` is proxied to the API (`BACKEND_URL`, default `http://127.0.0.1:8000`), so there is no CORS setup. The database is a SQLite file, so after changing the models delete `apps/api/vantage.db` and seed again.

## Tests

```bash
cd apps/api && .venv/Scripts/python -m pytest      # about 650 tests, around 2.5 minutes
cd apps/web && npm run typecheck && npm run lint
cd apps/web && npm run e2e                          # Playwright, needs both servers running
node scripts/pwa-check.mjs online                   # manifest, icons, service worker, caches
```

`npm run e2e` drives the Chrome installed on your machine, so there is no browser download. It covers onboarding, the four-field limit, the hidden-until-opened summaries, saving, the Explore flow, job descriptions, search, the theme switch and the "I got the job" flow on a desktop and a phone profile, and it runs an axe accessibility scan on each main page.

`pwa-check.mjs` has a second phase: stop the web server and run `offline` to confirm the last feed still renders.

The full plan, what each suite covers and what is not covered yet are in [docs/TEST_PLAN.md](docs/TEST_PLAN.md). `apps/api/tests/test_live_smoke.py` checks a deployed site without changing anything (set `VANTAGE_LIVE_WEB`), and `.github/workflows/tests.yml` runs the API tests, type check, lint and build on every push.

## Ranking, wording and reading aloud

A story's score adds up its matches instead of averaging them: naming a company you target is enough to be worth reading, and each further match (a role, a skill you lack) raises it. A skill you already have counts for less than one you are missing, a company's industry is not counted a second time, sources with more authority count slightly more, and stock tips and market-holiday notices are pushed down.

"Why it matters to you" and "What to do" follow the kind of story, read from the headline (leadership change, deal, results, hiring, policy, launch, expansion, technology, markets). Both lines only use things that were actually matched.

Inside an opened summary, **Listen** reads the headline, the summary and the pointers aloud with the browser's own speech engine, so nothing leaves your device. Choose a female or male voice, pick a specific voice from the menu and hear a sample, and set the speed. Natural, neural, Enhanced and Premium voices are ranked above the plain built-in ones, and a tip explains how to install better ones when only basic voices are found. Browsers do not say whether a voice is male or female, so the app reads it from the voice's name. If your device has no voice of the kind you pick, it says so and changes the pitch of the closest one.

## How accurate is it

Tagging is deterministic. A story gets a tag only when the taxonomy's own name or alias appears in its text, so nothing gets tagged that the text doesn't say. Several rules keep it precise:

- Whole-word matching. Short, all-caps and single proper-noun terms (SQL, ITC, Excel) match case-sensitively, so "excel at interviews" doesn't tag Excel.
- Per-entity blockers. "Amazon" is ignored next to "rainforest", "Java" next to "West Java", "Python" next to "snake".
- Generic skills such as Communication never tag news. They only appear in gap analysis.
- A name in the headline counts fully. A name only in the teaser counts less. A story needs a headline match, or two different entities in the teaser, to be kept at all.
- The same story from two outlets shows once, with "Also reported by" underneath.
- What you save and open nudges similar stories up. What you dismiss nudges them down, except for companies you follow or work for.

`apps/api/tests/test_tagging_accuracy.py` scores the tagger on 80 labelled headlines, including traps like the ones above, and fails the build if precision drops below 95% or recall below 90%. It currently scores 100% on both. I wrote those headlines myself, so treat that as a regression guard, not an independent benchmark. As a second check I read 45 randomly chosen stories from the live feeds and found no clearly wrong tags, though a few teaser-only ones were debatable.

## How it fits together

| Piece | Where |
| --- | --- |
| Profile: current and target fields, `profile_status`, `ProfileEvent` log | `apps/api/app/models.py` |
| Taxonomy data, one module per field, validated on load | `apps/api/app/seed_data/` |
| Onboarding, profile, targets, mark placed, skill gaps | `app/routers/onboarding.py`, `app/routers/profile.py` |
| Fields, roles, companies, skills, search, role and company pages | `app/routers/taxonomy.py` |
| Who hires what, derived from industry and field instead of a stored table | `app/hiring.py` |
| O*NET, SEC, NSE and Wikidata importers | `app/importers/` |
| Story summaries and pointers | `app/summarize.py` |
| Job descriptions: skill extraction and endpoints | `app/jds.py`, `app/routers/jds.py` |
| Tagger | `app/tagging.py` |
| RSS ingestion | `app/ingest.py` |
| Hourly and daily scheduling, run history | `app/scheduler.py` |
| Adding curated data to an existing database | `app/sync.py` |
| Scoring, with weights keyed by `profile_status` | `app/relevance.py` |
| Feed, lenses, duplicates, learning from behaviour | `app/feed.py`, `app/routers/feed.py` |
| "Why it matters" and "what to do", built only from matched names | `app/why.py` |

## Before real users

- Accounts work, but there is no email verification, no password reset and no admin role. Guests still use a random device id sent as `X-User-Id`; turn that off with `VANTAGE_ALLOW_GUESTS=0` once every user has an account. The login throttle is per process.
- The role-to-skill lists for the hand-written roles, and which companies hire a role, are placeholders built from general knowledge. Imported roles use O*NET's skills and tools, which describe US occupations. Hiring is derived from a company's industry and field, not from real openings. Load your real placement data before trusting a gap number. Sample articles are titled `[Sample]` and are only loaded with `--samples`; the browser tests use them.
- There is no migration tool. Tables are created on startup, and the few columns added since the first release are added automatically (`app/migrate.py`). Add Alembic once the schema holds real user data.
- Ingestion is a command, not a scheduler. Run `python -m app.ingest` on a cron. The taxonomy only changes when you run the importers or reseed. Reseeding an existing database wipes it, so use the importers to add data to a live one.
- Install prompts need HTTPS or localhost. On iPhone you install through Share, then Add to Home Screen, and the app shows those steps.
- There is no rate limiting on the API.

## Design references

The look follows a calm editorial direction: warm paper and ink, a serif for headings, a mono face for small labels, and one amber accent. Each field of work has its own muted hue. Buttons and the segmented control have a little physical depth, and motion uses a single ease-out curve with no bounce. Copy is written to sound like a person, not a product page.

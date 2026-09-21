# Test plan

What is tested, how, and what is not. The numbers were measured on 2026-09-21.

## How the cases were chosen

The reading behind this was consistent: generate positive, negative and edge cases from the requirements
and the screens, use a fixed template, and have a person review the result, because generated cases miss
rare flows and can give false confidence. So every case here follows the same shape (setup, input,
expected result), each area has a written expectation taken from the code's own rules, and the expected
values in the list below still need a human read. Case ids in test names (`AUTH`, `TAX`, `FEED`, ...)
map to the areas in the table.

Techniques used: equivalence classes and boundary values (password 7/8/128/129 characters, limit 0/1/500/501),
negative and hostile input (SQL and script text, malformed JSON, wrong types), state and idempotency
(second onboarding, saving twice, ingesting twice), access control (another user's data, guests, forged
and expired tokens, cross-site writes), privacy rights (export, erase, consent), accessibility (axe, keyboard,
zoom, dark mode, reduced motion, 320 px width) and a smoke run against the deployed site.

## What runs

| Layer | Where | Cases | Runs against |
| --- | --- | ---: | --- |
| Original API tests | `apps/api/tests/test_*.py` | 201 | in-memory database |
| API matrix: auth, taxonomy, onboarding, profile, feed, job descriptions, privacy, generic HTTP | `test_qa_matrix.py` | 266 | in-memory database |
| Data pipeline: feed parsing, ingest, briefs, connection strings | `test_qa_pipeline.py` | 72 | in-memory database |
| Search spellings and acronyms | `test_search_terms.py` | 34 | in-memory database |
| Story kinds, scoring and wording (cases added to existing files, plus `test_story.py`) | `test_story.py`, `test_relevance.py`, `test_why.py`, `test_feed.py` | 82 | in-memory database |
| Live smoke and security | `test_live_smoke.py` | 64 | the deployed site, read-only |
| Browser, original journeys | `apps/web/e2e/app.spec.ts` | 58 | local stack, desktop and Pixel 7 |
| Browser, forms, access, pages, accessibility, mobile | `e2e/qa-matrix.spec.ts` | 108 | local stack or live site |
| Browser, read-aloud | `e2e/speech.spec.ts` | 86 | local stack with a stand-in speech engine |

API: 719 collected, 655 run by default (the 64 live tests are skipped without a URL). Browser: 252 collected.
Last full run: API 655 passed; browser 252 passed (21.5 minutes).

## Commands

```bash
cd apps/api && python -m pytest -q                                  # API, about 2.5 minutes
VANTAGE_LIVE_WEB=https://vantage-web-vert.vercel.app python -m pytest tests/test_live_smoke.py
VANTAGE_LIVE_WRITE=1 VANTAGE_LIVE_WEB=... python -m pytest tests/test_live_smoke.py   # also creates and deletes one account

cd apps/web && npm run build && npx next start -p 3000              # with the API on :8000
npx playwright test                                                  # all browser tests
APP=https://vantage-web-vert.vercel.app npx playwright test e2e/qa-matrix.spec.ts   # read-only, slow (about 10 s per test)
```

`.github/workflows/tests.yml` runs the API tests, the type check, lint and build on every push and pull
request. It can also run the read-only smoke tests against a site you give it.

## What this round found

Fixed:

- **Score calibration.** A story naming a target company scored 25 of 100 and landed in "explore",
  because the score averaged over dimensions the story said nothing about. On four profiles over 823
  stories, target-company stories stuck in "explore" went from 8, 7, 5 and 0 to 0, 2, 0 and 0.
  A company's industry was also counted twice (once as the company, once as its industry).
- **Wording.** "What to do" ignored the story (a leadership change told the reader to practise a skill).
  Plural skills read "and isn't on your profile", and a company that was both current and target was
  mentioned twice. All fixed; the lines now follow the kind of story.
- **Noise.** Stock tips and market-holiday notices ranked like news.
- **Search.** "modelling", "DCF", "MS Excel" and "fmcg" found nothing.
- **Page titles.** `/`, `/login`, `/terms` and `/privacy` were all titled just "Vantage" (WCAG 2.4.2).

Two things in the first version of these tests were wrong, not the app: a locator for the sign-in switch,
and a fixture whose stories were near-duplicates, which the feed merges on purpose.

## Not covered, in order of risk

1. **Whether the ranking is right for real students.** Nothing here replaces having 8 to 10 students
   score a week of stories. The tagging test set was written by the same person as the tagger, and the
   before and after comparison above uses profiles and judgements written by the same session.
2. **Load.** No test with many users at once. Try 50 concurrent users on the feed, search and login.
3. **The login lockout on Vercel.** It is held in memory per instance, so each server instance counts separately.
4. **Read-aloud on real devices.** The tests use a stand-in engine. Which voices exist, and whether a name
   reads as male or female, depends on the device; when a device has no voice of the kind asked for,
   the app says so and shifts pitch instead.
5. **Coverage numbers.** Not measured yet (`pytest-cov` is not set up).
6. **Browser tests in CI.** They need both servers and Chrome, so they run locally for now.
7. **Fresh stories in production.** The hourly pull needs the `DATABASE_URL` secret on GitHub. Until then the
   live feed has no new stories and the tests cannot see that.

## Review checklist for a person

- Are the lockout (8 wrong passwords), the password limits (8 to 128) and the consent rules what you want?
- Read ten real "why it matters" and "what to do" lines for each kind of reader and say which are wrong or awkward.
- Do the tier lines (critical from 70, relevant from 40) match how much you want to be interrupted?
- Listen to one summary in each voice on your phone and on a laptop.

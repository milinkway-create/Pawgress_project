<p align="center"><img src="app/static/assets/logo.png" width="88" alt="Pawgress logo"></p>
<h1 align="center">Pawgress</h1>
<p align="center">Small steps. Happy companions.</p>

A personal project planner with one cute cat, dog, or fish **per project**, up to **three active projects per user**, and a desktop companion you can talk to.

## Start locally

Requires Python 3.14 (the tested version). No AI key or cloud account is needed for the local demo.

```sh
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000**. The local demo is clearly labeled, loopback-only, and stores data in `Pawgress.db`. It has one local account, generic editable starter plans, and no pretend AI responses. Do not expose demo mode to the internet.

## Included

- Goal, availability, unavailable dates, effort estimates, milestones, tasks and dependencies.
- Editable plan review before saving; deterministic Python scheduling and feasibility checks.
- Create/edit projects; complete/reopen tasks; recoverable task removal and project Trash; archive/restore.
- Exactly three active project slots, enforced transactionally, including concurrent requests.
- A project-owned cat, dog, or fish with distinct baby, youth and grown artwork.
- First-completion treats, immutable achievement IDs, milestone unlocks, free play/petting, room items and focus recording.
- Live OpenAI chat integration with bounded context and typed action proposals. **Every AI mutation requires approval.**
- Explicit, editable memories; deletion also removes old chat context and pending proposals.
- Supabase email sign-up/sign-in, verification and reset integration for hosted accounts.
- Protected administrator usage/account controls; no password visibility.
- Backend AI budget reservations, daily limits, model allowlist, bounded output, no automatic retries.
- Optional Electron planner + always-on-top companion window; browser companion popout also available.
- Automated tests, ten behavioral eval scenarios, CI, Dockerfile, and explanation/setup docs.

## Desktop companion

Start the backend first. Install Node.js 24 and pnpm, then:

```sh
cd desktop
pnpm install --frozen-lockfile
node node_modules/electron/install.js # downloads the official runtime if install scripts were skipped
pnpm start
```

Select **Desktop pet** inside a project. The companion is a small, movable, always-on-top window with the same project, chat and pet interactions. For a hosted backend, set `PAWGRESS_URL=https://your-app.example` before launching. This repository is source code, not a signed/notarized desktop installer.

## Enable real AI and multi-user accounts

Follow [Setup](docs/SETUP.md). Set secrets only in your ignored `.env` or hosting secret manager. Never commit keys.

For a ten-person pilot, deploy one backend, use one database and one Supabase Auth project. Each person signs in separately. The three-project limit is **per user**, not per database.

## Tests and evals

```sh
python -m pytest -q
python -m evals.run          # lists the suite; does not call a model
python -m evals.run --live   # explicit, paid, budgeted behavioral evaluation
```

See [Testing](docs/TESTING.md) for coverage, browser checks and verification limits.

## Documentation

- [Product rules and workflow](docs/PRODUCT.md)
- [Architecture and memory](docs/ARCHITECTURE.md)
- [Setup, deployment, and what the owner must provide](docs/SETUP.md)
- [Tests, evaluations, and pilot checklist](docs/TESTING.md)
- [Artwork provenance and generation brief](docs/ARTWORK.md)

## Current boundaries

No collaboration, voice, live image generation, push reminders, payment collection or installer signing. Conversation context uses explicit memories + the most recent ten messages; it does **not** claim unlimited recall or automatic long-term summarization. Basic local animations use prepared illustrations, not frame-by-frame character rigs. Email changes are handled in Supabase Auth. Arbitrary multi-action AI edits are intentionally not supported in one response.

The UI is a lightweight browser client, the scheduler and backend are Python, and Electron supplies the desktop window. Local SQLite is for personal testing; use private Postgres for a hosted multi-user pilot.

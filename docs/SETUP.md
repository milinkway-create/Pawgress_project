# Setup and owner cooperation

## Local trial: no credentials

Follow the README, open localhost, and create a project. The starter plan is a template, not AI. Pets, edits, rewards, focus, archive, memories and the administrator budget page work locally. `DEMO_MODE=true` is loopback-only and must never be used for a hosted pilot.

## What the owner supplies for live testing

1. An OpenAI API key with a small provider-side spending limit. Set `OPENAI_API_KEY` in the ignored `.env` or host secrets. Do not paste it in chat or commit it.
2. A Supabase project URL and publishable key for email authentication. Configure email confirmation and a production email sender before inviting testers.
3. A private Postgres connection string (Supabase Postgres is suitable) and an HTTPS backend host with persistent service support.
4. The owner's verified email in `ADMIN_EMAILS` to enable administrative controls.
5. A decision on hosting region/domain and, later, desktop signing credentials if distributing installers. No paid resource or subscription is provisioned by this repository.

## Production environment

```dotenv
DEMO_MODE=false
APP_ORIGIN=https://your-app.example
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/postgres?sslmode=require
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLISHABLE_KEY
OPENAI_API_KEY=SET_IN_SECRET_MANAGER
CHAT_MODEL=gpt-5.4-nano
PLAN_MODEL=gpt-5.4-mini
MONTHLY_AI_BUDGET_USD=5
DAILY_CHAT_LIMIT=30
ADMIN_EMAILS=owner@example.com
```

Use a direct or session-pooler Postgres connection appropriate to a persistent Python process. The app needs a backend-owned private schema/table connection, not a browser Data API connection. Startup creates the initial tables, enables RLS, and revokes public client grants. Keep one application database per environment. Back up data before deploying schema changes; this initial version has no automated upgrade migration framework.

The initial budget environment value seeds the database once. Later changes are made through **Usage & accounts**, not by silently replacing an existing budget at startup. Reservations include in-flight and uncertain calls. The application uses UTC for billing periods.

## Supabase email setup

Set the Supabase Site URL to `APP_ORIGIN`, enable Confirm email, and require a minimum eight-character password. Configure a sender/SMTP suitable for ten external testers and verify its delivery limits.

Customize confirmation emails to use:

```html
<a href="{{ .SiteURL }}/auth/confirm?token_hash={{ .TokenHash }}&type=email">Confirm your email</a>
```

Customize password recovery emails to use:

```html
<a href="{{ .SiteURL }}/auth/confirm?token_hash={{ .TokenHash }}&type=recovery">Reset your password</a>
```

The app verifies the one-time hash, stores the resulting session and opens account settings for recovery. Test signup, confirmation, refresh and password reset with real test inboxes before inviting the group. Administrators can request reset emails but never see passwords. Email changes are done in the Supabase Auth dashboard.

## Deploy the backend

A Dockerfile is supplied for a persistent Python host:

```sh
docker build -t pawgress .
docker run --rm -p 8000:8000 --env-file .env pawgress
```

Place behind HTTPS. Set `APP_ORIGIN` to the exact public origin. Do not enable open CORS, expose demo mode, or put secret credentials in static assets. Host-level request size/rate limits and a backup policy should be configured for a public deployment. Database, hosting, email and taxes have separate costs from the AI cap.

## Ten-user pilot

Deploy one backend and one database. Ten users create verified accounts. Each may create three active projects. Start with a modest shared AI budget and daily per-user limit. Review backend usage and errors after the first few sessions. Run the live eval suite once before the pilot; it uses the same budget ledger and incurs actual API charges.

## Desktop

The desktop shell requires Node.js 24, pnpm and a running local or hosted backend. `desktop/pnpm-lock.yaml` pins the resolved package tree. If your package manager blocks install scripts, run `node node_modules/electron/install.js` explicitly to download the official runtime. Set `PAWGRESS_URL` to your hosted origin for a shared pilot. Build/sign/notarize installers only after platform choice and signing credentials are available.

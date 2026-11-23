# Pawgress testing and evaluation

## Automated checks

Run `python -m pytest -q` from the repository root. The current suite has **35 passing tests** on Python 3.14 using an isolated temporary SQLite database. It never uses your real projects, credentials or paid AI.

Covered behaviors:

- Effort-aware scheduling, weekday exclusions, blackouts, impossible deadlines, cycles, missing dependencies and preservation of completed dates.
- Three active slots; concurrent creation; archive/restore enforcement; archived read-only behavior.
- Task completion dependencies; exactly-once task and milestone rewards; non-regressing stages; one-task projects; optional work; deletion cannot manufacture growth; milestone renaming cannot farm treats.
- Approval required before agent mutations, malicious/invalid operation rejection, foreign targets, stale proposals, replay prevention and cancellation.
- User isolation, verified-email checks, admin denial, origin enforcement and security headers.
- Atomic budget reservations, uncertain-call accounting, exhausted-budget fallback, free manual work, focus and treat balance.
- Ten distinct users acting concurrently, plus ten simultaneous slot/reward/budget requests.
- Ten eval fixture scenarios present and structurally valid.

One upstream Starlette warning recommends migrating the test transport from httpx to httpx2. The tests pass; this does not affect the runtime HTTP client. Re-evaluate on dependency updates.

## Behavioral evals

`evals/cases.json` contains ten scenarios: next task, completion, ambiguity, deadline changes, unclear skip-days, reward injection, cross-user access, explicit memory, delete confirmation and supportive conversation.

`python -m evals.run` validates that the scenario suite loads and makes **zero model calls**. It is not a model-quality evaluation.

`python -m evals.run --live` calls the configured model, applies automatic action/target checks and prints a human-review criterion for each response. It uses the application budget and daily allowance. Run with a separate evaluation database and small budget; never include real personal data. Review tone, factual grounding and save claims manually. This run has **not** been performed because no API key was supplied.

## Browser verification performed

Observed in the local browser:

1. Overview loads with logo, three-slot indicator and project entry point.
2. New-project form collects a name, goal, pet, dates and availability.
3. Starter-plan request returns a clearly labeled editable proposal without creating a project.
4. Explicit save creates the project, renders tasks and its baby companion.
5. Completing the first task updates progress to 20% and awards five treats.

6. Final visual pass confirms the updated artwork and mobile companion banner. Completing the first milestone increases the balance to 20 treats and unlocks the cushion; completing the next milestone advances the pet to youth, increases the balance to 35 treats and unlocks the toy.
7. Growth gallery visibly distinguishes baby, youth and grown poses, marks the current stage and explains thresholds. No browser console errors were recorded.

Native Electron launched without console output, but computer-use inspection stalled; the native always-on-top interaction is **not verified**.

## Before inviting ten testers

- Run CI on the pushed commit.
- Configure real Supabase email delivery; test signup, verification, expired-session refresh and recovery on the actual host.
- Exercise private Postgres with two verified users; confirm table grants/RLS and no cross-account access. SQLite tests do not substitute for this deployment check.
- Run live agent evals, including prompt injection in task text and memories.
- Check the final desktop UI on macOS/Windows target platforms and narrow browser widths.
- Test archive/restore, stage transition visuals, room equipment and a full edit/save cycle in the browser.
- Set a low shared AI cap and provider cap; monitor reservations and usage.
- Confirm backup/restore, HTTPS origin and host request limits.

These deployment checks require real service configuration. Do not describe the local demo as a fully verified production deployment.

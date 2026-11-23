# Pawgress product rules

## Ownership and limits

Each project owns exactly one cat, dog or fish. Each user may have up to three active projects. Archived/trashed projects do not consume active slots. Restoring a project requires a free slot. Pet state, treats, inventory and chat stay with the project, including on archive. One selected companion is shown on the desktop at a time. All interface branding uses **Pawgress**.

## Creation

Sign in → New project → goal, dates, availability, pet and name → proposed plan → edit work breakdown → explicitly save → first task. A local draft is scoped to the user on that device. Without an API key the proposal is a clearly labeled generic template. With a key the AI suggests work; Python schedules tasks topologically, serially, against weekday and date exclusions and minutes/day. Infeasible schedules are rejected with a useful explanation, never silently extended.

## Daily use

Read or edit the planner, chat with the pet, record a focus session, mark work complete, and enjoy free petting/play. A focus session records elapsed minutes when ended (maximum 120 recorded per session); it does not complete tasks or award treats. This first version records sessions rather than delivering operating-system timed reminders.

## Edits and approval

Manual task completion applies immediately with optimistic version checks. Manual project edits use Save. Destructive buttons ask for confirmation. Every AI write is a proposal: an allowlisted operation, validated target, dry-run result, exact project version, and visible change preview. Approve uses the same domain function as manual editing. Stale, foreign, cancelled or already-used proposals cannot execute. AI-proposed completion is not announced as saved before successful approval.

Task removal creates a tombstone, preserving achievement history. A removed task can be restored from the Removed tasks section with its original ID and reward history; there is no generic one-click undo history in this version. Project deletion is recoverable Trash. There is no permanent-delete endpoint. Archived projects are read-only until restored.

## Pet growth

- Baby: on project creation.
- Youth: first-completion effort earned reaches 40% of the project's growth denominator.
- Grown: every required task, including tombstoned required work, has actually been completed and remains present. A single-task project can go straight to grown.
- Earned stages never regress; time away, missed deadlines and reopened tasks are not punishments.
- Added required work increases the denominator; editing unearned required effort adjusts it. Deletion does not lower it to manufacture growth.
- If scope is removed, users can archive the project at its earned stage. Deletion alone never grants adulthood or completion rewards.

This is deliberately conservative. Scope rebasing with revised achievement criteria is a future feature, not an implicit reward bypass.

## Treats and items

First completion of each task: 5 treats once. Each originally planned milestone: 10 bonus treats once. Milestone achievement identity and task membership are fixed at plan creation, so renaming or regrouping work cannot farm milestone rewards. Later-added milestones organize work but do not add milestone bonuses.

First milestone unlocks a cushion; later milestones unlock a toy. Actual required completion unlocks cushion, toy and celebration theme even on short projects. Equip/unequip is free. Feed costs one treat; petting and basic play are always free. Focus and casual chat do not earn growth or treats.

## Memory and spending

Explicit preferences are account-level; conversations are project-level. Keep at most 30 saved preferences and 100 recent messages per project; send only the last ten messages plus relevant current data to AI. Forgetting a preference clears old conversation context to prevent resurrection. Model answers are not authoritative project records.

One server-wide monthly AI limit and a per-user daily call limit apply to all paid calls, including planning and evals. Reservations count in-flight requests and uncertain failures. No voice, web search, image generation or unrestricted tool execution is enabled. Budget exhaustion disables AI, not manual planning or free pet interactions.

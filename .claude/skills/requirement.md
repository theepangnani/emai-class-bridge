# /requirement - Requirement Assessment & Management

Assess, refine, prioritize, plan, and track requirements for ClassBridge.

## Usage

`/requirement <description of the requirement or feature>`

Examples:
- `/requirement Add student self-enrollment for courses`
- `/requirement Parents should be able to see report cards`
- `/requirement Dark mode`

## Instructions

Follow these steps in order. Each step builds on the previous one.

---

### Step 1: Understand & Refine

1. Read the current `REQUIREMENTS.md` to understand existing features, phases, and patterns
2. Read relevant source code (models, routes, frontend pages) to understand the current implementation state
3. If the requirement is vague or incomplete, **ask the user clarifying questions** before proceeding:
   - **Who** benefits? (which user roles)
   - **What** specifically should happen? (user actions, system behaviour)
   - **Why** is this needed? (problem it solves, user pain point)
   - **Acceptance criteria** — how do we know it's done?
   - **Scope boundaries** — what's explicitly out of scope?
4. Rewrite the requirement into a structured format:

```
Refined Requirement:
  As a <role>, I want to <action> so that <benefit>.

Acceptance Criteria:
  - <specific, testable criterion>
  - <specific, testable criterion>

Scope:
  In scope: <what's included>
  Out of scope: <what's explicitly excluded>
```

---

### Step 2: Assess Current State

1. Check if this feature already exists (fully or partially) in the codebase:
   - Search models, routes, schemas for related entities
   - Search frontend pages and components for related UI
2. Check REQUIREMENTS.md progress checklist for related items
3. Identify:
   - Which section of REQUIREMENTS.md this belongs to (existing section update or new section)
   - Which phase it fits into (Phase 1, 1.5, 2, 3, 4)
   - What already exists vs what needs to be built
   - Dependencies on other features or data model changes
   - Impact on existing functionality (breaking changes, migrations needed)

---

### Step 3: Check for Duplicate Issues

Run these commands to find related or duplicate GitHub issues:

```bash
# Search open issues for related keywords
gh issue list --repo theepangnani/emai-dev-03 --state open --search "<keywords>" --json number,title,state --jq '.[] | "#\(.number) \(.title)"'

# Also check recently closed issues in case this was already done
gh issue list --repo theepangnani/emai-dev-03 --state closed --search "<keywords>" --limit 10 --json number,title,state --jq '.[] | "#\(.number) \(.title)"'
```

Record any related issues found — they will be referenced in the analysis.

---

### Step 4: Prioritize

Assess priority using these criteria:

| Criterion | Weight | Questions to Ask |
|-----------|--------|-----------------|
| **User Impact** | High | How many users does this affect? Does it block a core workflow? |
| **Dependency Chain** | High | Do other features depend on this? Is this blocking something else? |
| **Effort** | Medium | How many files/endpoints/components need to change? |
| **Risk** | Medium | Does this require DB migrations? Breaking changes? Security implications? |
| **Alignment** | Low | Does this fit the current phase roadmap? |

Assign a priority level:
- **P0 — Critical**: Blocks users, data loss risk, security vulnerability
- **P1 — High**: Core feature gap, multiple users affected, enables other work
- **P2 — Medium**: Nice-to-have improvement, single-role benefit, moderate effort
- **P3 — Low**: Polish, edge case, future-phase alignment

Compare against current open issues to give a relative ranking:
```bash
gh issue list --repo theepangnani/emai-dev-03 --state open --limit 30 --json number,title,labels --jq '.[] | "#\(.number) \(.title) [\(.labels | map(.name) | join(", "))]"'
```

---

### Step 5: Present Analysis & Get Approval

Present the full analysis to the user. **Do not proceed until the user approves.**

```
╔══════════════════════════════════════════╗
║        REQUIREMENT ANALYSIS              ║
╚══════════════════════════════════════════╝

📋 REFINED REQUIREMENT
  As a <role>, I want to <action> so that <benefit>.

  Acceptance Criteria:
  - <criterion 1>
  - <criterion 2>

📊 ASSESSMENT
  Phase: <Phase 1 / 1.5 / 2 / 3 / 4>
  Section: <REQUIREMENTS.md section>
  Status: <New / Partial / Duplicate of #XX>
  Priority: <P0 / P1 / P2 / P3> — <rationale>

  Current State:
  - <what already exists>
  - <what's missing>

  Related Issues:
  - #<number>: <title> (<open/closed>)

🔧 WHAT NEEDS TO CHANGE
  Backend:
  - <models, schemas, routes, services affected>
  Frontend:
  - <pages, components, CSS affected>
  Database:
  - <new tables, columns, migrations>

📦 DEPENDENCIES
  - <other features or issues this depends on>

⚠️  RISKS / CONSIDERATIONS
  - <breaking changes, edge cases, security concerns>

📐 SCOPE
  Estimated effort: <Small (1-2 files) / Medium (3-6 files) / Large (7+ files)>

🗂️  IMPLEMENTATION PLAN
  1. <step — file(s) affected>
  2. <step — file(s) affected>
  3. <step — file(s) affected>
```

**Wait for user to approve, modify, or reject before proceeding.**

---

### Step 6: Update REQUIREMENTS.md

Only after user approval:

1. Add or update the relevant section in `REQUIREMENTS.md`
2. Follow existing conventions:
   - Use the same heading hierarchy and table formats
   - Mark implementation status: `- IMPLEMENTED`, `- PARTIAL`, or no suffix for planned
   - Include data model changes with field names and types
   - Include endpoint definitions with HTTP method, path, and description
   - Include role-based access rules
3. If updating an existing section, preserve what's already there and add/modify only what's needed
4. Add to the **Progress Checklist** section:
   - `- [ ]` for planned features
   - `- [x]` for implemented features (with `(IMPLEMENTED)` suffix)
5. Keep language concise and specification-oriented (not conversational)

---

### Step 7: Create/Update GitHub Issues

Only create issues if no existing issue covers the same scope:

1. If a **duplicate** exists: comment on the existing issue or update it with `gh issue edit <number>`
2. If **partially covered**: update the existing issue body and add missing criteria
3. If **new**: create issues broken into actionable units:
   - One issue per logical unit of work (e.g., backend model, API endpoint, frontend page)
   - Use clear titles: `<Action>: <what> (<where>)` — e.g., "Add student self-enroll endpoint (backend)"

Create issues using:
```bash
gh issue create --repo theepangnani/emai-dev-03 --title "<title>" --body "$(cat <<'EOF'
## Context
<Brief description and link to requirement>

## Priority
<P0/P1/P2/P3> — <rationale>

## Acceptance Criteria
- [ ] <specific, testable criterion>
- [ ] <specific, testable criterion>

## Implementation Plan
- <step 1>
- <step 2>

## Technical Notes
- <relevant implementation details>
- <affected files or components>

## Dependencies
- <other issues this depends on, if any>
EOF
)"
```

Use appropriate labels: `enhancement`, `bug`, `backend`, `frontend`, `database`, `priority:high`, `priority:medium`, `priority:low`

---

### Step 8: Report Summary

After all changes are made, report:

```
╔══════════════════════════════════════════╗
║        REQUIREMENT TRACKED               ║
╚══════════════════════════════════════════╝

REQUIREMENTS.md: <updated section name>
Priority: <P0/P1/P2/P3>

Issues created/updated:
  - #<number>: <title> (NEW / UPDATED)
  - #<number>: <title> (NEW / UPDATED)

Relative priority vs open issues:
  This ranks <above/below> #<number> (<title>) based on <rationale>.

Recommended next steps:
  1. <what to implement first>
  2. <follow-up items>
```

---

## Priority Reference

Current priority tiers for open issues (update as issues are resolved):

| Priority | Description | Example Issues |
|----------|-------------|----------------|
| P0 | Blocks users or causes data loss | Security fixes, auth bugs |
| P1 | Core feature gaps, enables other work | #112 (task reminders), #119 (recurring tasks) |
| P2 | Improvements, moderate user impact | #150 (loading skeletons), #152 (mobile responsive) |
| P3 | Polish, future phase prep | #151 (accessibility), #153 (flashcards bug) |

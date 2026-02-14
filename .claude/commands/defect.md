Handle a production defect end-to-end. The user will describe the issue or provide a screenshot.

Follow these steps in order:

## 1. Create GitHub Issue
- Create a GitHub issue with label `bug` and `priority: high`
- Title should be concise and descriptive
- Body should include: **Description**, **Steps to Reproduce**, **Expected vs Actual Behavior**, **Environment** (production/dev)
- Use: `gh issue create --title "..." --body "..." --label bug`

## 2. Assess the Defect
- Check production logs if applicable: `gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=classbridge" --project=emai-dev-01 --limit=30`
- Identify the root cause by reading relevant source files
- Determine affected endpoints/pages
- Confirm the defect with the user: explain what's broken and why

## 3. Classify the Defect
Determine if this is:
- **Code bug** — Implementation error in existing feature
- **Requirement/design gap** — Missing requirement or incomplete design
- **Regression** — Previously working feature that broke
- **Environment issue** — Config, deployment, or infrastructure problem

Report your classification to the user before proceeding.

## 4. Fix the Defect
- Make the minimal necessary code changes
- Follow existing patterns in the codebase
- Handle cross-database compatibility (SQLite dev + PostgreSQL prod)
- Do NOT over-engineer — fix the specific issue

## 5. Test
- Run backend tests: `python -m pytest --tb=short -q`
- Run frontend build: `cd frontend && npm run build`
- Run frontend tests if applicable: `cd frontend && npm test`
- Verify all tests pass before proceeding

## 6. Update REQUIREMENTS.md
- If the fix addresses a requirement gap, update the relevant section
- Mark any newly implemented features with checkmarks
- Add notes about the fix if it changes behavior

## 7. Update GitHub Issues
- Commit and push the fix (auto-deploys to Cloud Run)
- Close the GitHub issue with a reference to the commit
- Update any related open issues if affected
- Report the fix summary to the user

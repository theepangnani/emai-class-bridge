Manage the Inspiration Messages feature. Use this skill for any work related to motivational quotes shown on dashboards and in email footers.

## Feature Architecture

### Backend
- **Model**: `app/models/inspiration_message.py` — `InspirationMessage` (id, role, text, author, is_active, created_at, updated_at). Composite index on (role, is_active).
- **Schema**: `app/schemas/inspiration.py` — Pydantic request/response models
- **Service**: `app/services/inspiration_service.py` — `get_random_message(db, role)` returns a random active message for the given role
- **Routes**: `app/api/routes/inspiration.py` — Mounted at `/api/inspiration`
  - `GET /random` — Any authenticated user, returns role-targeted quote
  - `GET /messages` — Admin only, list all with optional role/active filters
  - `POST /messages` — Admin only, create message
  - `PATCH /messages/{id}` — Admin only, update text/author/is_active
  - `DELETE /messages/{id}` — Admin only, delete message
  - `POST /seed` — Admin only, re-seed from JSON files (only if table empty)
- **Seed Data**: `data/inspiration/parent.json`, `teacher.json`, `student.json` (40 quotes each)
- **Email Integration**: `app/services/email_service.py` → `add_inspiration_to_email(html_content, db, role)` appends a styled quote footer to outgoing emails
- **Startup Seed**: `main.py` auto-seeds DB on startup if table is empty
- **Tests**: `tests/test_inspiration.py`

### Frontend
- **Admin Page**: `frontend/src/pages/AdminInspirationPage.tsx` + `.css` — Full CRUD UI for managing messages by role
- **API Client**: `frontend/src/api/client.ts` → `inspirationApi` object with: `getRandom()`, `list()`, `create()`, `update()`, `delete()`, `seed()`
- **Dashboard Display**: `frontend/src/components/DashboardLayout.tsx` — Shows random quote in welcome section on every page load
- **Routing**: `frontend/src/App.tsx` — Admin route at `/admin/inspiration`, protected by `allowedRoles={['admin']}`

### Role Targeting
- **parent** → parent-focused quotes (involvement, support)
- **teacher** → teacher-focused quotes (impact, resilience)
- **student** → student-focused quotes (learning, perseverance)
- **admin** → receives quotes from all roles

### Email Footer Pattern
All outgoing emails (invites, notifications, password resets, messages) call `add_inspiration_to_email()` before `send_email_sync()`. The footer is a styled `<div>` with the quote in italics and optional author attribution. Gracefully returns original HTML on any failure.

## Common Tasks

### Add new quotes
1. Edit the relevant JSON file in `data/inspiration/` or use the admin UI
2. If adding via JSON, the seed endpoint only runs when the table is empty — use admin UI for incremental adds

### Extend to a new role
1. Create `data/inspiration/{role}.json` with quote objects `[{"text": "...", "author": "..."}]`
2. Update seed logic in `inspiration_service.py` to include the new role file
3. The `get_random_message()` service and email integration automatically support any role string

### Debug missing quotes
1. Check `GET /api/inspiration/messages?role=parent&is_active=true` for active messages
2. Verify seed ran: check if `inspiration_messages` table has rows
3. Check email integration: `add_inspiration_to_email()` silently catches exceptions — check logs for warnings

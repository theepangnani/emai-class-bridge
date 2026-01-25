# Copilot / AI agent instructions for EMAI

This file is a concise, actionable guide for AI coding agents working in this repository.
Focus on the concrete patterns, integration points, and developer workflows discovered in the code.

1. Repo high-level architecture
- FastAPI app started from `main.py` which includes routers from `app/api/routes/*` and applies a global `/api` prefix there.
- Database layer: SQLAlchemy engine and `SessionLocal` in `app/db/database.py`; `Base` is the declarative base for models in `app/models/`.
- Configuration: pydantic-settings in `app/core/config.py` (`settings` object) supplies all runtime config (DB URL, Google OAuth, JWT secrets).
- Security/auth: JWT utilities and password helpers live in `app/core/security.py` and are used by `app/api/routes/auth.py` and `app/api/deps.py`.
- Google Classroom integration: `app/services/google_classroom.py` implements OAuth flow and API calls; `app/api/routes/google_classroom.py` wires OAuth + saved tokens on the `User` model.

2. Important files to inspect/modify
- API routes: `app/api/routes/*.py` (each defines an APIRouter, e.g. `auth`, `google_classroom`).
- DB: `app/db/database.py` (engine, SessionLocal, `get_db`).
- Models: `app/models/*.py` (e.g. `user.py` contains `User` model and `UserRole` enum).
- Schemas: `app/schemas/*.py` (Pydantic request/response models; note `UserResponse.Config.from_attributes = True`).
- Services: `app/services/google_classroom.py` (Google API wrappers) and other `app/services/*` files.
- Config & secrets: `app/core/config.py` (reads `.env`), and `requirements.txt` for runtime deps.

3. Project-specific patterns and gotchas
- Router prefixes: Individual route modules use `APIRouter(prefix="/something")`, and `main.py` includes them with `prefix="/api"`. Final endpoints look like `/api/auth/login`, `/api/google/callback`.
- Auth tokens: access tokens are created with payload `{"sub": str(user.id)}`; `app/api/deps.py:get_current_user` decodes JWT and uses `sub` as the numeric `User.id`.
- OAuth users: `User.hashed_password` is nullable to support OAuth-only accounts (see `app/models/user.py`). When modifying auth flows, account for nullable passwords.
- DB creation: there is no automatic `create_all` in startup code. To create local SQLite DB tables quickly run in a Python shell:

```py
from app.db.database import Base, engine
Base.metadata.create_all(bind=engine)
```

- Alembic: `alembic` is listed in `requirements.txt`, but there is no alembic config/migrations directory present. If adding migrations, create an Alembic config and point `sqlalchemy.url` to `settings.database_url`.

4. How Google Classroom is wired (concrete example)
- OAuth flow: `app/services/google_classroom.get_authorization_url()` → user consents → Google sends `code` to `/api/google/callback`.
- Tokens are exchanged with `exchange_code_for_tokens`, then the app looks up a `User` by `google_id` or `email` and stores `google_access_token` and `google_refresh_token` on the `User` model.
- Endpoints that call Google Classroom require the authenticated user to have `google_access_token` saved; they call service helpers like `list_courses(access_token, refresh_token)`.

5. Dev / run / test commands
- Run development server:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Create DB tables (SQLite local dev): run the `Base.metadata.create_all` snippet above.
- Run tests (pytest is included):

```bash
pytest -q
```

6. Common edits and examples
- Adding a new API route: create `app/api/routes/myfeature.py` with `router = APIRouter(prefix="/myfeature", tags=["MyFeature"])` and `main.py` will pick it up if imported inside `app/api/routes/__init__.py` (project currently imports route modules directly in `main.py`).
- Using DB session: add `db: Session = Depends(get_db)` to endpoint signature and use `db.add()/db.commit()/db.refresh()` as shown in `auth.register`.
- Returning pydantic responses: use response_model on route decorators (see `@router.post('/register', response_model=UserResponse)`). `UserResponse` uses `from_attributes = True` so SQLAlchemy model instances can be returned directly.

7. When changing auth/token behavior
- `app/api/deps.py` expects JWT `sub` claim to be the user id string. Keep `create_access_token` and `get_current_user` compatible.
- `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")` — if you change login path, update this URL.

8. What I did not find (gaps you may want to add)
- No `README.md` or `.github/copilot-instructions.md` existed — this file fills that gap.
- No Alembic migration directory — repository relies on direct `create_all` for local dev unless you add migrations.

9. Quick pointers for reviewers
- Inspect: `app/core/security.py` (JWT and hashing), `app/api/deps.py` (auth dependency), `app/services/google_classroom.py` (third-party integration).
- When touching Google code, ensure `settings.google_client_*` values are present in `.env`.

If any section is unclear or you'd like more examples (e.g., a small test harness, or an Alembic init snippet), tell me which part to expand. 

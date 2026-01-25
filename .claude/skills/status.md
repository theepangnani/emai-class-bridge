# /status - Project Status Check

Check the current status of the EMAI project including servers, git, and environment.

## Instructions

Run the following checks and report status:

### 1. Git Status
```bash
git status
git branch --show-current
git log --oneline -3
```

### 2. Server Status
Check if backend is running:
```bash
powershell -Command "Invoke-WebRequest -Uri 'http://localhost:8000/docs' -UseBasicParsing -TimeoutSec 3 | Select-Object StatusCode"
```

Check if frontend is running:
```bash
powershell -Command "Invoke-WebRequest -Uri 'http://localhost:5173' -UseBasicParsing -TimeoutSec 3 | Select-Object StatusCode"
```

### 3. Database Status
Check if database file exists:
```bash
powershell -Command "Test-Path 'c:\dev\emai\emai-dev-03\emai.db'"
```

### 4. Environment Check
Verify .env file exists and has required variables:
```bash
powershell -Command "Test-Path 'c:\dev\emai\emai-dev-03\.env'"
```

## Report Format

```
=== EMAI Project Status ===

Git:
- Branch: <current-branch>
- Status: <clean/dirty>
- Last commits: <recent commits>

Servers:
- Backend (8000): <running/stopped>
- Frontend (5173): <running/stopped>

Database:
- SQLite file: <exists/missing>

Environment:
- .env file: <exists/missing>
```

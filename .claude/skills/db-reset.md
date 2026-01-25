# /db-reset - Reset Database

Reset the SQLite database by deleting it and restarting the backend server (which auto-creates tables).

## Instructions

1. Stop any running Python processes
2. Delete the emai.db file
3. Restart the backend server to recreate tables
4. Confirm the database was reset

## Commands

```bash
# Stop backend
powershell -Command "Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force"

# Delete database
powershell -Command "Remove-Item 'c:\dev\emai\emai-dev-03\emai.db' -ErrorAction SilentlyContinue"

# Restart backend
cd c:\dev\emai\emai-dev-03
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Warning

This will DELETE all data including:
- User accounts
- Courses
- Assignments
- Google connections

Only use this for development/testing purposes.

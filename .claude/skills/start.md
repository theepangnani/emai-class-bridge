# /start - Start Development Servers

Start both the backend and frontend development servers for EMAI.

## Instructions

1. Start the FastAPI backend server on port 8000
2. Start the Vite frontend server on port 5173
3. Report the URLs when both are running

## Commands

Backend:
```bash
cd c:\dev\emai\emai-dev-03
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:
```bash
cd c:\dev\emai\emai-dev-03\frontend
npm run dev
```

## Expected Output

- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:5173

# /build - Build for Production

Build the frontend for production deployment.

## Instructions

1. Build the React frontend with Vite
2. Report the output location and size
3. Provide deployment instructions

## Commands

```bash
cd c:\dev\emai\emai-dev-03\frontend

# Install dependencies if needed
npm install

# Build for production
npm run build
```

## Output

The build will be created in `frontend/dist/` directory.

## Deployment Notes

### Frontend Deployment Options

1. **Static hosting (Vercel, Netlify, GitHub Pages)**
   - Upload the `dist/` folder
   - Configure redirects for SPA routing

2. **Cloud Storage (GCS, S3)**
   - Upload to bucket
   - Configure as static website

3. **Docker**
   - Use nginx to serve static files
   - Add to docker-compose with backend

### Backend Deployment

The FastAPI backend can be deployed to:
- Google Cloud Run
- AWS Lambda (with Mangum adapter)
- Any VPS with Python + uvicorn

### Environment Variables for Production

Update `.env` for production:
```env
DATABASE_URL=postgresql://user:pass@host/db
SECRET_KEY=<secure-random-key>
GOOGLE_REDIRECT_URI=https://yourdomain.com/api/google/callback
FRONTEND_URL=https://yourdomain.com
```

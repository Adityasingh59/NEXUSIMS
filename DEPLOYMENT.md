# Deployment Guide - Test Branch

This guide provides step-by-step instructions to deploy the test branch on **Railway** (backend) and **Vercel** (frontend).

## Prerequisites

- **Railway Account**: https://railway.app/
- **Vercel Account**: https://vercel.com/
- **Git**: Latest version installed
- **Node.js**: v18+ (for frontend)
- **Python**: v3.11+ (for backend)

---

## Backend Deployment on Railway

### Step 1: Push Code to GitHub
The test branch is already pushed to GitHub with Railway-ready configurations:
```bash
git branch -a
# Should show: origin/test
```

**New Railway-Ready Files:**
- `railway.json` - Explicit Railway configuration
- `start.sh` - Build and start script
- `Procfile` - Service definitions
- `docker-compose.prod.yml` - Production Docker setup
- Updated `backend/Dockerfile` - Multi-stage production build

### Step 2: Create Railway Project
1. Go to [railway.app](https://railway.app/) and log in
2. Click **"New Project"** → **"Deploy from GitHub Repo"**
3. Select your **NEXUSIMS** repository
4. Select **test** branch
5. Railway will automatically detect the `railway.json` configuration
6. It will use the `Procfile` and `start.sh` for building and deploying

### Step 3: Configure Environment Variables in Railway

In Railway dashboard, go to your project → Variables and set:

```env
ENVIRONMENT=production
DEBUG=false

DATABASE_URL=${DATABASE_PASSWORD}  # Railway provides this
REDIS_URL=${REDIS_URL}             # Railway provides this
CELERY_BROKER_URL=redis://${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}/0

JWT_SECRET_KEY=your-secure-secret-key-min-32-chars
JWT_ALGORITHM=HS256

CORS_ORIGINS=["https://your-vercel-test-url.vercel.app"]
```

**Important**: 
- Copy the `DATABASE_URL` and `REDIS_URL` from Railway's PostgreSQL and Redis services
- Replace `CORS_ORIGINS` with your actual Vercel deployment URL (set this after Vercel deployment)

### Step 4: Configure PostgreSQL Service in Railway
1. Add a new service → **PostgreSQL**
2. Initialize with default username: `nexus_admin`
3. Database name: `nexus_ims`
4. Password: Generate a secure password

### Step 5: Configure Redis Service in Railway
1. Add a new service → **Redis**
2. Use default configuration

### Step 6: Deploy Backend
1. Click **Deploy** button in Railway
2. Monitor logs for errors
3. Once deployed, note the public URL (e.g., `https://your-railway-app-url.railway.app`)

### Step 7: Run Database Migrations
Connect to Railway PostgreSQL and run:
```bash
# From your local machine
# Use railway CLI or connect via pgAdmin
# Run: alembic upgrade head
```

Or use Railway's terminal:
```bash
railway run alembic upgrade head
```

---

## Frontend Deployment on Vercel

### Step 1: Update Backend URL
Update `frontend/.env.test` with your Railway backend URL:
```env
VITE_API_URL=https://your-railway-backend-url.railway.app/api/v1
```

### Step 2: Push Changes to Test Branch
```bash
git add frontend/.env.test
git commit -m "feat: Add test environment configuration for Vercel"
git push origin test
```

### Step 3: Create Vercel Project
1. Go to [vercel.com](https://vercel.com/) and log in
2. Click **"Add New..."** → **"Project"**
3. Select your **NEXUSIMS** repository
4. Configuration:
   - **Framework**: Vite
   - **Project Name**: nexusims-test
   - **Root Directory**: ./frontend
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

### Step 4: Set Environment Variables in Vercel
In Vercel dashboard → Project Settings → Environment Variables:

```env
VITE_API_URL=https://your-railway-backend-url.railway.app/api/v1
VITE_DEBUG=true
```

### Step 5: Deploy Frontend
1. Click **Deploy** button
2. Vercel will auto-deploy from the test branch
3. Once complete, note your Vercel URL

### Step 6: Update Backend CORS Configuration
Go back to Railway and update the environment variable:
```env
CORS_ORIGINS=["https://your-vercel-app.vercel.app"]
```

Trigger a redeploy in Railway.

---

## Verify Deployment

### Backend Health Check
```bash
curl https://your-railway-backend-url.railway.app/health
# Should return: { "status": "ok" }
```

### Frontend Access
Open https://your-vercel-app.vercel.app in your browser

### Test Login
1. Register a new account
2. Login with test credentials
3. Navigate through the app to verify all features work

---

## Troubleshooting

### Railway Backend Issues

**Database Connection Failed**
- Verify DATABASE_URL is correct
- Check PostgreSQL service is running
- Ensure network access is allowed

**Redis Connection Failed**
- Verify REDIS_URL is correct
- Check Redis service is running

**Port Issues**
- Railway assigns a random port; make sure FastAPI listens on `0.0.0.0:${PORT}`

### Vercel Frontend Issues

**API Calls Failing**
- Verify VITE_API_URL is correct
- Check CORS is configured on backend (CORS_ORIGINS includes Vercel URL)
- Check browser console for CORS errors

**Build Failures**
- Check Node.js version compatibility
- Verify package-lock.json is up to date
- Review build logs in Vercel dashboard

---

## After Deployment

1. **Test all features** on test branch deployment
2. **Monitor logs** for errors
3. **Run API tests** against the backend
4. **Test RMA functionality** (new feature)
5. **Test Webhooks** (new feature)
6. **Verify multi-currency** features
7. Once validated, merge improvements to `master` and `branch1`

---

## Rolling Back

If issues occur:

**Railway**: Click **"Redeploy"** from a previous deployment
**Vercel**: Revert to previous deployment from **Deployments** tab

---

## Docker & Railway Configuration Files

### `railway.json`
Explicit configuration for Railway:
- Uses `Dockerfile` as the builder
- Sets context to `./backend` directory
- Configures start command to use `start.sh`
- Enables automated restarts on failure

### `start.sh`
Build and startup script:
- Installs Python dependencies
- Runs database migrations automatically
- Starts FastAPI with uvicorn
- Respects `PORT` environment variable

### `Procfile`
Defines services for Railway:
- `web`: Main FastAPI application
- `worker`: Celery worker for async tasks
- `beat`: Celery beat scheduler

### `docker-compose.prod.yml`
Production Docker Compose setup:
- Optimized for production environments
- Health checks on all services
- Automatic restart policies
- Uses environment variables from `.env.prod`

### Updated `backend/Dockerfile`
Production-ready improvements:
- Multi-stage build for smaller image size
- Health check endpoint
- 4 workers by default (configurable)
- Proper signal handling

---

## Local Testing with Docker (Optional)

To test the production build locally:

```bash
# Build and run with production compose file
docker-compose -f docker-compose.prod.yml up --build

# Or just build the backend image
docker build -t nexus-api:test ./backend
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql+asyncpg://..." \
  -e REDIS_URL="redis://..." \
  nexus-api:test
```

---

## Notes

- The test branch contains RMA, Webhooks, and multi-currency enhancements
- All new features are included and ready for testing
- Database migrations are applied during first deployment
- No changes were made to master or branch1 (as requested)

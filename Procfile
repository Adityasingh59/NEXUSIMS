web: cd backend && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 4
worker: cd backend && celery -A app.worker worker --loglevel=info
beat: cd backend && celery -A app.worker beat --loglevel=info

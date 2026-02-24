web: sh start.sh
worker: celery -A app.worker worker --loglevel=info
beat: celery -A app.worker beat --loglevel=info

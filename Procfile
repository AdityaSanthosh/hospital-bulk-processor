web: gunicorn -w 1 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:$PORT
worker: celery -A celery_worker.celery_app worker --pool=solo --loglevel=info

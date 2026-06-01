web: python manage.py migrate && python manage.py collectstatic --noinput && gunicorn core.wsgi
worker: celery -A core worker -l info
beat: celery -A core beat -l info
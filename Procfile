web: python manage.py migrate && python manage.py collectstatic --noinput && gunicorn shoe_ecommerce.wsgi
worker: celery -A config worker -l info
beat: celery -A config beat -l info 
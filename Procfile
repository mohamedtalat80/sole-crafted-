web: python manage.py migrate && python manage.py collectstatic --noinput && gunicorn shoe_ecommerce.wsgi
worker: celery -A shoe_ecommerce worker -l info
beat: celery -A shoe_ecommerce beat -l info 
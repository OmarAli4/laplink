web: python manage.py collectstatic --noinput && python manage.py migrate --noinput && python manage.py clean_dummy_data && python manage.py reindex_search && gunicorn myshop.wsgi --log-file -

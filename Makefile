# Stop old Gunicorn and start again
run:
	pkill gunicorn || true
	gunicorn arrolite.wsgi:application --bind 0.0.0.0:8000

# Create and apply database migrations
migrate:
	python3 manage.py makemigrations
	python3 manage.py migrate

# Collect static files (clean + collect)
static:
	rm -rf staticfiles/*
	python3 manage.py collectstatic --noinput

# Clear Django cache and bytecode
clear:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	python3 manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Restart Gunicorn
restart_gunicorn:
	pkill gunicorn || true

# Restart Nginx
restart_nginx:
	nginx -t
	systemctl restart nginx

# Full deploy (FIXED)
deploy: migrate static clear restart_gunicorn restart_nginx

# Backup database
backup:
	bash backup_db.sh
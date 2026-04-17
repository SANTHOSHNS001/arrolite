# Run the Django application using Gunicorn
run:
	gunicorn arrolite.wsgi:application --bind 0.0.0.0:8000

# Create and apply database migrations
migrate:
	python3 manage.py makemigrations
	python3 manage.py migrate

# Collect static files (Required for Nginx to show CSS/Images)
static:
	python3 manage.py collectstatic --noinput

# Clear Django cache and bytecode
clear:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete
	python3 manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Full deploy: Migrate, Collect Static, and Restart Nginx
deploy: migrate static restart_nginx

# Test the Nginx configuration and restart the service
restart_nginx:
	sudo nginx -t
	sudo systemctl restart nginx
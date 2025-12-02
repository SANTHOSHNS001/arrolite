#!/bin/bash
cd /home/santhosh01/arrolite
source /home/santhosh01/venv/bin/activate
git pull
python manage.py collectstatic --noinput
pa_reload_webapp santhosh01.pythonanywhere.com

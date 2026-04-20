# Arrolite (Django Project) 
This repository contains the `arrolite` Django app for inventory, invoicing, sales, and accounting workflows.

## Structure

- `app/`: main app module with models, views, serializers, forms, and URLs
- `arrolite/`: Django project settings, WSGI/ASGI, and root URL config
- `media/`, `static/`, `staticfiles/`: file and asset storage
- `requirements.txt`: Python dependencies
- `manage.py`: Django CLI entrypoint

## Setup

1. Create and activate virtual environment (example):

   ```powershell
   python -m venv .env
   .\.env\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Apply migrations:

   ```powershell
   python manage.py migrate
   ```

4. Create a superuser:

   ```powershell
   python manage.py createsuperuser
   ```

5. Run development server:

   ```powershell
   python manage.py runserver
   ```

## Common tasks

- Run tests: `python manage.py test`
- Collect static: `python manage.py collectstatic`
- Make migrations: `python manage.py makemigrations`

## Notes

- This project is originally structured around the `app` Django app and uses custom templates under `app/templates/`.
- If you need more detailed documentation, consider adding `docs/` with architecture diagrams, API references (serializers/endpoints), and deployment instructions.

## Workflow (End-to-End)

1. Development setup
   - Clone repo: `git clone <repo-url>`
   - Create and activate venv
   - `pip install -r requirements.txt`
   - `python manage.py migrate`
   - `python manage.py createsuperuser`
   - `python manage.py runserver`

2. Daily developer workflow
   - Branch from `main`: `git checkout -b feature/xxx`
   - Code models in `app/models/`, views in `app/view/`, serializers in `app/serializers/`, forms in `app/forms/`, and templates in `app/templates/`
   - Add tests in `app/tests.py` or in `app/<module>/tests.py`
   - Run local tests: `python manage.py test`
   - Database changes: `python manage.py makemigrations`, `python manage.py migrate`
   - Static assets: `python manage.py collectstatic` (for production)
   - Lint/code format: `flake8`/`black` (if configured)

3. Review + merge
   - Commit and push branch: `git push origin feature/xxx`
   - Create PR, request review, apply fixes
   - Merge after approval, then `git checkout main` and `git pull`

4. Release & deployment
   - Ensure `requirements.txt` up to date
   - Check `arrolite/settings.py` for production settings (`DEBUG=False`, `ALLOWED_HOSTS`, DB URL, static/media roots)
   - Build docker/image (if using Dockerfile) and deploy to target environment
   - Run migrations in production and restart app server

5. Runtime user workflow
   - access app on browser
   - login as superuser/admin
   - manage categories/products/customers/expenses/invoices via UI
   - download reports and export as needed

## Optional docs folder (recommended)

- `docs/architecture.md`: component/service diagrams
- `docs/api_endpoints.md`: REST endpoint list and payloads
- `docs/deployment.md`: full deploy guide for Docker/Heroku/AWS
- `docs/contributing.md`: contribution and code style rules


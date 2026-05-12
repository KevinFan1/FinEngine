# FinEngine Backend Deployment

This directory contains a source-based deployment baseline for the backend.

## Layout

- `env.production.example`: backend environment variable template
- `install_backend.sh`: install backend dependencies with `uv`
- `init_backend.sh`: run database migrations and optional seed data
- `start_api.sh`: start the FastAPI API process
- `start_worker.sh`: start the Celery worker process
- `supervisor/finengine.conf`: `supervisor` config for API + worker
- `nginx/finengine.conf`: `nginx` config example for frontend + API reverse proxy

## Recommended server layout

Example path:

```bash
/data/www/FinEngine/
```

Backend path:

```bash
/data/www/FinEngine/backend
```

## First-time deployment

```bash
cd /data/www/FinEngine/backend
cp deploy/env.production.example .env
```

Edit `.env` and fill at least:

```env
DATABASE_URL=
REDIS_URL=
SECRET_KEY=
```

Install dependencies:

```bash
bash deploy/install_backend.sh
```

Run migrations:

```bash
bash deploy/init_backend.sh
```

If you need initial platform / file-spec / category data:

```bash
bash deploy/init_backend.sh --with-seed
```

## Manual startup

Start API:

```bash
bash deploy/start_api.sh
```

Start worker:

```bash
bash deploy/start_worker.sh
```

## Supervisor

Copy `deploy/supervisor/finengine.conf` to your server's `supervisor` config directory, then adjust:

- `directory`
- `command`
- `user`
- log file path

Reload:

```bash
supervisorctl reread
supervisorctl update
supervisorctl status
```

Start:

```bash
supervisorctl start finengine:*
```

Restart:

```bash
supervisorctl restart finengine:*
```

## Notes

- The frontend can be built separately and deployed independently.
- The API itself does not depend on frontend build artifacts.
- The application will try to create the default `superadmin` account on API startup.

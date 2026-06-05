# FinEngine Backend Deployment

This directory contains a source-based deployment baseline for the backend.

## Layout

- `env.production.example`: backend environment variable template
- `install_backend.sh`: install backend dependencies with `uv`
- `init_backend.sh`: run database migrations and optional seed data
- `update_backend.sh`: guarded update flow for pull/install/migrate/restart/health-check
- `start_api.sh`: start the FastAPI API process
- `start_worker.sh`: start the Celery worker process
- `start_flower.sh`: start the Flower Celery monitor
- `supervisor/finengine.conf`: `supervisor` config for API + worker + Flower
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
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=5
REDIS_URL=          # 缓存/验证码/防重放
CELERY_REDIS_URL=   # Celery 队列和结果，建议使用不同 DB
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

Start Flower:

```bash
bash deploy/start_flower.sh
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

## 4C16G application server baseline

For a 4 vCPU / 16 GiB ECS used as the API application server, keep the process
model conservative:

- `APP_WORKERS=2`
- `finengine-worker` `numprocs=0~2` on the API server; move heavy Celery work to
  a separate worker ECS when monthly imports grow.
- `DB_POOL_SIZE=5` and `DB_MAX_OVERFLOW=5` for API processes.
- Use one API service bound to one local port. `uvicorn --workers` already runs
  multiple API worker processes behind the same socket, so running two identical
  API supervisor programs on the same ECS and load balancing them with nginx is
  usually unnecessary. Keep a second API program only for blue/green deploys.

Gunicorn is optional for this stack. The current `uvicorn --workers` launcher is
fine behind nginx; use Gunicorn only if you want its process manager features
and then avoid also wrapping it with multiple supervisor API programs.

## Flower

Flower is managed as `finengine-flower` by the supervisor example and listens on
`127.0.0.1:5555` by default. Keep it private; expose it through an SSH tunnel or
nginx with authentication. Set `FLOWER_BASIC_AUTH=user:password` if you proxy it.
If you mount Flower under `/flower`, keep `FLOWER_URL_PREFIX=flower` so the app
generates the correct links behind nginx.

## Routine updates

Use `update_backend.sh` for normal source updates so dependency installation,
database migrations, process restart, and health checks are not skipped.

From the backend directory:

```bash
cd /data/www/FinEngine/backend
bash deploy/update_backend.sh --git-pull
```

If this release also needs the frontend rebuilt on the server:

```bash
bash deploy/update_backend.sh --git-pull --with-frontend-build
```

If this release includes seed data changes:

```bash
bash deploy/update_backend.sh --git-pull --with-seed
```

The update script stops immediately if any step fails. By default it runs:

1. optional `git pull --ff-only`
2. `uv sync --frozen`
3. `uv run migrate-upgrade`
4. optional `uv run seed-all`
5. `uv run python -m compileall app`
6. optional frontend `npm ci` and `npm run build`
7. `supervisorctl restart finengine:*`
8. health check against `/api/v1/health/detailed` and require `message: healthy`
   with `api/database/redis` all `ok`

Useful options:

```bash
bash deploy/update_backend.sh --help
bash deploy/update_backend.sh --git-pull --branch main
bash deploy/update_backend.sh --no-restart --no-health-check
```

The script uses a lock under `backend/tmp/` so two updates cannot run at the
same time.

## Same-server blue/green option

Running two API processes on the same server is useful for lower-downtime
switching and quick rollback, but it does not replace the update script. You
still need to install dependencies and run migrations before traffic is moved.

A practical single-server blue/green shape:

- blue API: `APP_PORT=8000`
- green API: `APP_PORT=8001`
- nginx proxies to the active port
- start the new color, check `/api/v1/health/detailed`, then switch nginx
- keep the old color running briefly so rollback is just an nginx switch

Be careful with database migrations in blue/green deployments. Both colors
share the same database, so migrations should be backward compatible whenever
old and new code may run at the same time.

## Notes

- The frontend can be built separately and deployed independently.
- The API itself does not depend on frontend build artifacts.
- The application will try to create the default `superadmin` account on API startup.
- After the single-session login migration is applied, old JWTs without a session id become invalid. Users need to log in again once after deployment.

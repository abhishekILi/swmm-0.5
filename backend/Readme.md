# SWMM Backend Setup

This project uses Django REST Framework, Celery for background jobs, RabbitMQ as the Celery broker, and Redis for Celery results and Django caching.

## Getting Started

### 1. Move into the backend

```powershell
cd backend\backend_drf
```

### 2. Install dependencies

```powershell
poetry install --no-root
```

### 3. Configure environment variables

Create a `.env` file from [sample.env](/C:/Users/yuvraj.rana/Documents/SWMM/backend/backend_drf/sample.env).

Important variables for background processing:

```env
RABBITMQ_DEFAULT_USER=swmm
RABBITMQ_DEFAULT_PASS=swmm
RABBITMQ_DEFAULT_VHOST=swmm
CELERY_BROKER_URL=amqp://swmm:swmm@localhost:5672/swmm
CELERY_RESULT_BACKEND=redis://localhost:6379/0
REDIS_CACHE_URL=redis://localhost:6379/1
```

### 4. Start RabbitMQ and Redis

```powershell
docker compose up -d rabbitmq redis
```

RabbitMQ management UI will be available at `http://localhost:15672`.

### 5. Run migrations

```powershell
poetry run python manage.py migrate
```

### 6. Start the Django server

```powershell
poetry run python manage.py runserver
```

### 7. Start a Celery worker

On Windows, use the solo pool:

```powershell
poetry run celery -A swmm worker -l info --pool=solo --without-mingle --without-gossip
```

On Linux/macOS:

```bash
poetry run celery -A swmm worker -l info --without-mingle --without-gossip
```

These flags avoid RabbitMQ startup issues seen with newer RabbitMQ versions and
still keep Celery remote control available for the backend health check.

Do not disable remote control in the worker configuration. The backend now uses
Celery worker health checks before dispatching some background jobs.

### 7a. Verify worker health

After starting the worker, open a second terminal and run:

```powershell
poetry run celery -A swmm inspect ping
```

Expected result:

```text
-> celery@<hostname>: OK
    pong
```

If no worker replies, the backend will automatically fall back to synchronous
execution for protected background-task endpoints.

### 8. Seed data if needed

```powershell
poetry run python seed_data.py --clear --count 10
```

## Notes

- Existing task modules such as [dart/tasks.py](/C:/Users/yuvraj.rana/Documents/SWMM/backend/backend_drf/dart/tasks.py) and [ems/tasks.py](/C:/Users/yuvraj.rana/Documents/SWMM/backend/backend_drf/ems/tasks.py) are autodiscovered by Celery.
- Redis is configured as the Django default cache and Celery result backend.
- RabbitMQ is used only as the Celery broker.
- Celery health check tuning is available through:
  - `CELERY_HEALTHCHECK_TIMEOUT` default `1.0`
  - `CELERY_HEALTHCHECK_CACHE_TTL` default `5.0`

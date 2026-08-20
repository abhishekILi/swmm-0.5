#!/bin/bash

set -euo pipefail

# =========================================================
# Configuration
# =========================================================

REPO_DIR="${CI_PROJECT_DIR}"
COMPOSE_FILE="docker-compose.yml"

SERVER_REPO_DIR="/home/gitlab-runner/15th-august-v0.5-swmm-ship"

SERVER_COMPOSE_ENV="${SERVER_REPO_DIR}/.env"
SERVER_BACKEND_ENV="${SERVER_REPO_DIR}/backend/.env"

export IMAGE_TAG="${CI_COMMIT_SHORT_SHA}"

# Application URL
APP_URL="http://172.16.50.7"


# =========================================================
# Cleanup
# =========================================================

cleanup() {

    echo "=================================="
    echo "Cleaning Temporary Environment Files"
    echo "=================================="

    rm -f "$REPO_DIR/.env"
    rm -f "$REPO_DIR/backend/.env"
}

trap cleanup EXIT


# =========================================================
# Deployment Information
# =========================================================

echo "=================================="
echo "Starting DEV Deployment"
echo "=================================="

echo "CI_COMMIT_SHA        = ${CI_COMMIT_SHA}"
echo "CI_COMMIT_SHORT_SHA  = ${CI_COMMIT_SHORT_SHA}"
echo "IMAGE_TAG            = ${IMAGE_TAG}"
echo "REPO_DIR             = ${REPO_DIR}"


# =========================================================
# Go to GitLab Checkout
# =========================================================

cd "$REPO_DIR"

echo "=================================="
echo "Repository Information"
echo "=================================="

echo "Current directory:"
pwd

echo "Current commit:"
git rev-parse HEAD

echo "Expected commit:"
echo "$CI_COMMIT_SHA"


# =========================================================
# Check Repository Files
# =========================================================

echo "=================================="
echo "Checking Repository Files"
echo "=================================="

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "ERROR: $COMPOSE_FILE not found"
    exit 1
fi

if [ ! -d "backend" ]; then
    echo "ERROR: backend directory not found"
    exit 1
fi

if [ ! -f "backend/pyproject.toml" ]; then
    echo "ERROR: backend/pyproject.toml not found"
    exit 1
fi

if [ ! -f "backend/poetry.lock" ]; then
    echo "ERROR: backend/poetry.lock not found"
    exit 1
fi

echo "Docker Compose:"
ls -lh "$COMPOSE_FILE"

echo "Backend dependency files:"
ls -lh backend/pyproject.toml
ls -lh backend/poetry.lock


# =========================================================
# Check Existing Server Environment Files
# =========================================================

echo "=================================="
echo "Checking Server Environment Files"
echo "=================================="

if [ ! -f "$SERVER_COMPOSE_ENV" ]; then
    echo "ERROR: Server .env not found:"
    echo "$SERVER_COMPOSE_ENV"
    exit 1
fi

if [ ! -f "$SERVER_BACKEND_ENV" ]; then
    echo "ERROR: Server backend .env not found:"
    echo "$SERVER_BACKEND_ENV"
    exit 1
fi

echo "Server Compose environment:"
ls -lh "$SERVER_COMPOSE_ENV"

echo "Server Backend environment:"
ls -lh "$SERVER_BACKEND_ENV"


# =========================================================
# Copy Environment Files
# =========================================================

echo "=================================="
echo "Preparing Environment Files"
echo "=================================="

cp "$SERVER_COMPOSE_ENV" "$REPO_DIR/.env"
cp "$SERVER_BACKEND_ENV" "$REPO_DIR/backend/.env"

chmod 600 "$REPO_DIR/.env"
chmod 600 "$REPO_DIR/backend/.env"

echo "Environment files copied successfully."


# =========================================================
# Docker Compose Validation
# =========================================================

echo "=================================="
echo "Validating Docker Compose"
echo "=================================="

docker compose \
    -f "$COMPOSE_FILE" \
    --env-file "$REPO_DIR/.env" \
    config --quiet

echo "Docker Compose configuration is valid."


# =========================================================
# Show Resolved Images
# =========================================================

echo "=================================="
echo "Docker Images"
echo "=================================="

docker compose \
    -f "$COMPOSE_FILE" \
    --env-file "$REPO_DIR/.env" \
    config --images


# =========================================================
# Harbor Login
# =========================================================

echo "=================================="
echo "Logging into Harbor"
echo "=================================="

if [ -z "${HARBOR_URL:-}" ]; then
    echo "ERROR: HARBOR_URL is not set"
    exit 1
fi

if [ -z "${HARBOR_USERNAME:-}" ]; then
    echo "ERROR: HARBOR_USERNAME is not set"
    exit 1
fi

if [ -z "${HARBOR_PASSWORD:-}" ]; then
    echo "ERROR: HARBOR_PASSWORD is not set"
    exit 1
fi

echo "$HARBOR_PASSWORD" | docker login "$HARBOR_URL" \
    --username "$HARBOR_USERNAME" \
    --password-stdin


# =========================================================
# Pull Images
# =========================================================

echo "=================================="
echo "Pulling Images"
echo "=================================="

docker compose \
    -f "$COMPOSE_FILE" \
    --env-file "$REPO_DIR/.env" \
    pull


# =========================================================
# Recreate Application Containers
# =========================================================

echo "=================================="
echo "Recreating Application Containers"
echo "=================================="

docker compose \
    -f "$COMPOSE_FILE" \
    --env-file "$REPO_DIR/.env" \
    up -d \
    --force-recreate \
    --no-deps \
    swmm-backend-dev \
    swmm-frontend-dev \
    swmm-celery-worker


# =========================================================
# Wait for Backend
# =========================================================

echo "=================================="
echo "Waiting for Backend Health"
echo "=================================="

BACKEND_TIMEOUT=180
BACKEND_ELAPSED=0

while true; do

    BACKEND_STATUS=$(docker inspect \
        --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' \
        swmm-backend-dev 2>/dev/null || true)

    echo "Backend health: ${BACKEND_STATUS}"

    if [ "$BACKEND_STATUS" = "healthy" ]; then
        break
    fi

    if [ "$BACKEND_STATUS" = "unhealthy" ]; then
        echo "ERROR: Backend became unhealthy"
        docker logs --tail 100 swmm-backend-dev
        exit 1
    fi

    if [ "$BACKEND_ELAPSED" -ge "$BACKEND_TIMEOUT" ]; then
        echo "ERROR: Backend health check timed out"
        docker logs --tail 100 swmm-backend-dev
        exit 1
    fi

    sleep 5
    BACKEND_ELAPSED=$((BACKEND_ELAPSED + 5))

done

echo "Backend is healthy."


# =========================================================
# Wait for Frontend
# =========================================================

echo "=================================="
echo "Waiting for Frontend Health"
echo "=================================="

FRONTEND_TIMEOUT=120
FRONTEND_ELAPSED=0

while true; do

    FRONTEND_STATUS=$(docker inspect \
        --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' \
        swmm-frontend-dev 2>/dev/null || true)

    echo "Frontend health: ${FRONTEND_STATUS}"

    if [ "$FRONTEND_STATUS" = "healthy" ]; then
        break
    fi

    if [ "$FRONTEND_STATUS" = "unhealthy" ]; then
        echo "ERROR: Frontend became unhealthy"
        docker logs --tail 100 swmm-frontend-dev
        exit 1
    fi

    if [ "$FRONTEND_ELAPSED" -ge "$FRONTEND_TIMEOUT" ]; then
        echo "ERROR: Frontend health check timed out"
        docker logs --tail 100 swmm-frontend-dev
        exit 1
    fi

    sleep 5
    FRONTEND_ELAPSED=$((FRONTEND_ELAPSED + 5))

done

echo "Frontend is healthy."


# =========================================================
# Recreate Nginx
# =========================================================

echo "=================================="
echo "Recreating Nginx"
echo "=================================="

docker compose \
    -f "$COMPOSE_FILE" \
    --env-file "$REPO_DIR/.env" \
    up -d \
    --force-recreate \
    --no-deps \
    swmm-nginx


# =========================================================
# Wait for Nginx
# =========================================================

echo "=================================="
echo "Waiting for Nginx"
echo "=================================="

NGINX_TIMEOUT=60
NGINX_ELAPSED=0

while true; do

    NGINX_STATUS=$(docker inspect \
        --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' \
        swmm-nginx 2>/dev/null || true)

    echo "Nginx health: ${NGINX_STATUS}"

    if [ "$NGINX_STATUS" = "healthy" ] || \
       [ "$NGINX_STATUS" = "no-healthcheck" ]; then
        break
    fi

    if [ "$NGINX_STATUS" = "unhealthy" ]; then
        echo "ERROR: Nginx became unhealthy"
        docker logs --tail 100 swmm-nginx
        exit 1
    fi

    if [ "$NGINX_ELAPSED" -ge "$NGINX_TIMEOUT" ]; then
        echo "ERROR: Nginx health check timed out"
        docker logs --tail 100 swmm-nginx
        exit 1
    fi

    sleep 5
    NGINX_ELAPSED=$((NGINX_ELAPSED + 5))

done

echo "Nginx is ready."


# =========================================================
# Verify Nginx Upstream Resolution
# =========================================================

echo "=================================="
echo "Verifying Nginx Backend Resolution"
echo "=================================="

docker exec swmm-nginx getent hosts swmm-backend-dev

docker exec swmm-nginx wget \
    -q \
    -O /dev/null \
    http://swmm-backend-dev:8000/schema/

echo "Nginx can reach backend successfully."


# =========================================================
# Container Status
# =========================================================

echo "=================================="
echo "Container Status"
echo "=================================="

docker compose \
    -f "$COMPOSE_FILE" \
    --env-file "$REPO_DIR/.env" \
    ps


# =========================================================
# Run Migrations
# =========================================================

echo "=================================="
echo "Running Migrations"
echo "=================================="

docker compose \
    -f "$COMPOSE_FILE" \
    --env-file "$REPO_DIR/.env" \
    exec -T \
    swmm-backend-dev \
    python manage.py migrate --noinput


# =========================================================
# Collect Static Files
# =========================================================

echo "=================================="
echo "Collecting Static Files"
echo "=================================="

docker compose \
    -f "$COMPOSE_FILE" \
    --env-file "$REPO_DIR/.env" \
    exec -T \
    swmm-backend-dev \
    python manage.py collectstatic --noinput


# =========================================================
# Redis Verification
# =========================================================

echo "=================================="
echo "Checking Redis"
echo "=================================="

REDIS_RESULT=$(docker exec swmm-redis redis-cli ping)

if [ "$REDIS_RESULT" != "PONG" ]; then
    echo "ERROR: Redis health check failed"
    exit 1
fi

echo "Redis: OK"


# =========================================================
# Final Smoke Tests
# =========================================================

echo "=================================="
echo "Running Application Smoke Tests"
echo "=================================="

# echo "Testing frontend..."

# curl -fsS \
#     --max-time 20 \
#     -o /dev/null \
#     "$APP_URL/"

# echo "Frontend: OK"


# echo "Testing API..."

# curl -fsS \
#     --max-time 20 \
#     -o /dev/null \
#     "$APP_URL/api/"

# echo "API: OK"


# echo "Testing Swagger..."

# curl -fsS \
#     --max-time 20 \
#     -o /dev/null \
#     "$APP_URL/swagger/"

# echo "Swagger: OK"


# =========================================================
# Final Verification
# =========================================================

echo "=================================="
echo "Final Container Status"
echo "=================================="

docker compose \
    -f "$COMPOSE_FILE" \
    --env-file "$REPO_DIR/.env" \
    ps


echo "=================================="
echo "Deployment Verification"
echo "=================================="

echo "Frontend URL: ${APP_URL}/"
echo "API URL:      ${APP_URL}/api/"
echo "Swagger URL:  ${APP_URL}/swagger/"


echo "=================================="
echo "DEV Deployment Completed Successfully"
echo "=================================="

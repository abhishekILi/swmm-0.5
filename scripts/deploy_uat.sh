#!/bin/bash

set -e

REPO_DIR="/home/gitlab-runner/cs_swmm_v1"
BRANCH="swmm_uat"

echo "=================================="
echo "Starting UAT Deployment"
echo "=================================="

cd "$REPO_DIR"

echo "Fetching latest code..."

git fetch origin
git reset --hard origin/$BRANCH

echo "=================================="
echo "Logging into Harbor"
echo "=================================="

echo "$HARBOR_PASSWORD" | docker login "$HARBOR_URL" \
-u "$HARBOR_USERNAME" \
--password-stdin

echo "=================================="
echo "Pulling Latest Images"
echo "=================================="

docker compose pull

echo "=================================="
echo "Starting Containers"
echo "=================================="

docker compose up -d --remove-orphans

echo "=================================="
echo "Waiting for Backend"
echo "=================================="

sleep 20

echo "=================================="
echo "Running Migrations"
echo "=================================="

docker compose exec -T swmm-backend-uat python manage.py migrate --noinput

echo "=================================="
echo "Collecting Static Files"
echo "=================================="

docker compose exec -T swmm-backend-uat python manage.py collectstatic --noinput

docker compose exec -T swmm-backend-uat python manage.py populate_db

echo "=================================="
echo "Deployment Verification"
echo "=================================="

docker compose ps

echo "=================================="
echo "Deployment Completed"
echo "=================================="

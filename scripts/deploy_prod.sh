#!/bin/bash

set -e

NAMESPACE="swmm"
REGISTRY="172.16.50.13/cs_swmm_v1"

IMAGE_TAG=${IMAGE_TAG:-latest}

echo "Deploying image tag: ${IMAGE_TAG}"

echo "Updating Backend..."
kubectl set image deployment/backend \
backend=${REGISTRY}/backend:${IMAGE_TAG} \
-n ${NAMESPACE}

kubectl annotate deployment/backend \
kubernetes.io/change-cause="Deployed backend:${IMAGE_TAG}" \
-n ${NAMESPACE} \
--overwrite

echo "Updating Frontend..."
kubectl set image deployment/frontend \
frontend=${REGISTRY}/frontend:${IMAGE_TAG} \
-n ${NAMESPACE}

kubectl annotate deployment/frontend \
kubernetes.io/change-cause="Deployed frontend:${IMAGE_TAG}" \
-n ${NAMESPACE} \
--overwrite

echo "Waiting for Backend rollout..."

if ! kubectl rollout status deployment/backend \
    -n ${NAMESPACE} \
    --timeout=5m
then
    echo "Backend deployment failed. Rolling back..."

    kubectl rollout undo deployment/backend \
    -n ${NAMESPACE}

    kubectl rollout status deployment/backend \
    -n ${NAMESPACE} \
    --timeout=5m

    exit 1
fi


echo "Waiting for Frontend rollout..."

if ! kubectl rollout status deployment/frontend \
    -n ${NAMESPACE} \
    --timeout=5m
then
    echo "Frontend deployment failed. Rolling back..."

    kubectl rollout undo deployment/frontend \
    -n ${NAMESPACE}

    kubectl rollout status deployment/frontend \
    -n ${NAMESPACE} \
    --timeout=5m

    exit 1
fi

echo "Backend image:"
kubectl get deployment backend \
-n ${NAMESPACE} \
-o=jsonpath='{.spec.template.spec.containers[0].image}'

echo

echo "Frontend image:"
kubectl get deployment frontend \
-n ${NAMESPACE} \
-o=jsonpath='{.spec.template.spec.containers[0].image}'

echo

echo "Deployment Successful."

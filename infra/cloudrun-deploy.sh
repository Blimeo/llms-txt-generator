#!/bin/bash
PROJECT_ID=$1
REGION=$2


if [ -z "$PROJECT_ID" ] || [ -z "$REGION" ]; then
echo "Usage: ./cloudrun-deploy.sh <PROJECT_ID> <REGION>"
exit 1
fi


gcloud builds submit --tag gcr.io/$PROJECT_ID/llms-worker ./apps/worker
gcloud run deploy llms-worker \
--image gcr.io/$PROJECT_ID/llms-worker \
--platform managed \
--region $REGION \
--allow-unauthenticated
#!/bin/bash

ENV_FILE=".env"

# --- Load Environment Variables First ---
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: Environment file '$ENV_FILE' not found."
    echo "Please create a .env file with your configuration variables (PROJECT_ID, SERVICE_ACCOUNT, etc.)."
    exit 1
fi


echo "Loading environment variables from $ENV_FILE..."
# Use 'set -a' to automatically export all variables read from the file.
set -a
source "$ENV_FILE"
set +a

# --- Configuration with Fallbacks ---
# These now use the loaded .env variables or fallback to defaults.
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"

if [ -z "$PROJECT_ID" ]; then
    echo "Error: GOOGLE_CLOUD_PROJECT is not set in .env file."
    exit 1
fi

REPO="translation-app-repo"
IMAGE_NAME="translation-app-image"
JOB_NAME="${CLOUD_RUN_JOB_NAME:-translation-job}"

gcloud artifacts repositories create ${REPO} \
    --project=${PROJECT_ID} \
    --repository-format=docker \
    --location=${REGION} \
    --description="Docker repository for my translation app"



gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE_NAME}:latest --project=${PROJECT_ID}

gcloud run deploy translation-app-service \
    --project=${PROJECT_ID} \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE_NAME}:latest \
    --platform=managed \
    --region=${REGION} \
    --allow-unauthenticated \
    --timeout=3600s \
    --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,GCP_REGION=$REGION,CLOUD_RUN_JOB_NAME=$JOB_NAME"

#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# The name for your Cloud Run Job.
JOB_NAME="translation-job"

# The path to your environment variables file.
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
PROJECT_ID="${PROJECT_ID:-${GOOGLE_CLOUD_PROJECT:-your-gcp-project-id}}"
REGION="${REGION:-${GOOGLE_CLOUD_LOCATION:-your-gcp-region}}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-${JOB_SERVICE_ACCOUNT:-your-service-account@your-project-id.iam.gserviceaccount.com}}"

# --- Pre-flight Checks ---
# These checks now run *after* loading the .env file.
if [ "$PROJECT_ID" == "your-gcp-project-id" ] || [ -z "$PROJECT_ID" ]; then
    echo "Error: PROJECT_ID is not set."
    echo "Please set either GOOGLE_CLOUD_PROJECT in your shell or PROJECT_ID in your .env file."
    exit 1
fi

if [ "$SERVICE_ACCOUNT" == "your-service-account@your-project-id.iam.gserviceaccount.com" ] || [ -z "$SERVICE_ACCOUNT" ]; then
    echo "Error: SERVICE_ACCOUNT is not set."
    echo "Please set either JOB_SERVICE_ACCOUNT in your shell or SERVICE_ACCOUNT in your .env file."
    exit 1
fi

echo "Deploying Cloud Run Job '$JOB_NAME' to project '$PROJECT_ID' in region '$REGION'..."

# --- Prepare Environment Variables for gcloud ---
# The --env-vars-file flag expects YAML, but .env files are not YAML.
# Instead, we'll read the .env file and format the variables for the --set-env-vars flag.
# This filters out comments and empty lines, then joins them with commas.
ENV_VARS_FOR_GCLOUD=$(grep -v '^#' "$ENV_FILE" | grep -v '^$' | tr '\n' ',' | sed 's/,$//')

# --- Deployment Command ---
# We now use --set-env-vars to pass the formatted environment variables.
gcloud run jobs deploy "$JOB_NAME" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --source="." \
  --max-retries=1 \
  --service-account="$SERVICE_ACCOUNT" \
  --task-timeout="10h" \
  --set-env-vars="$ENV_VARS_FOR_GCLOUD"
  
echo "Deployment successful."

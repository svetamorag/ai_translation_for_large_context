#!/bin/bash
set -euo pipefail


# ==============================================================================
# This script deploys the Translation Validator Agent to a Vertex AI Agent Engine.
# It uses environment variables for configuration to avoid hardcoding values.
#
# Required environment variables:
#   - GOOGLE_CLOUD_PROJECT: Your Google Cloud project ID.
#   - GOOGLE_CLOUD_LOCATION: The region for deployment (e.g., us-central1).
#   - STAGING_BUCKET: The GCS bucket for staging deployment artifacts.
# ==============================================================================

# --- Load .env file if it exists ---
# This allows for local configuration without polluting the global environment.
if [ -f .env ]; then
  echo "Loading environment variables from .env file..."
  # The following command exports variables from the .env file.
  # It ignores comments and empty lines.
  export $(grep -v '^#' .env | xargs)
fi


# --- Configuration ---
PROJECT_ID="${GOOGLE_CLOUD_PROJECT?Error: GOOGLE_CLOUD_PROJECT is not set.}"
LOCATION="${GOOGLE_CLOUD_LOCATION?Error: GOOGLE_CLOUD_LOCATION is not set.}"
STAGING_BUCKET_NAME="${STAGING_BUCKET?Error: STAGING_BUCKET is not set.}"

adk deploy agent_engine \
    --project="${PROJECT_ID}" \
    --region="${LOCATION}" \
    --staging_bucket="gs://${STAGING_BUCKET_NAME}" \
    --display_name="Translation Editorial Team" \
    .
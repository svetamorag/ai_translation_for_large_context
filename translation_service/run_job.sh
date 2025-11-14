#!/bin/bash

# The Google Cloud project ID where your job is deployed.
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-your-gcp-project-id}"

# A unique identifier for this specific translation run
SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]' | tr -d '-')

# The GCS folder for this session's output
GCS_FOLDER="translations/${SESSION_ID}"

# Your GCS bucket
GCS_BUCKET="bucket_name_here"

# The source file you want to translate
SOURCE_FILE="gs://source_bucket/path/to/source_file.txt"

# The target language
TARGET_LANGUAGE="French"

# The region where your job is deployed
REGION="us-central1"

if [ "$PROJECT_ID" == "your-gcp-project-id" ] || [ -z "$PROJECT_ID" ]; then
    echo "Error: PROJECT_ID is not set. Please set the GOOGLE_CLOUD_PROJECT environment variable or edit this script."
    exit 1
fi


echo "Starting Job Execution..."

# Execute the job
# The Cloud Run Job's container runs main.py, which expects named arguments.
gcloud run jobs execute translation-job \
  --project="$PROJECT_ID" \
  --region "$REGION" \
  --no-wait \
  --args="--source-file=${SOURCE_FILE}" \
  --args="--target-language=${TARGET_LANGUAGE}" \
  --args="--gcs-bucket=${GCS_BUCKET}" \
  --args="--gcs-folder=${GCS_FOLDER}"

echo "Job execution finished. Check the output in gs://${GCS_BUCKET}/${GCS_FOLDER}"
